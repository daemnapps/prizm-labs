"""Bind a harness session to a brief and collect only post-pickup usage.

Hook input is the authority for session IDs/transcript paths. Local cursors never
leave this checkout; shared receipts contain counts and IDs, never chat text.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import sys
import tempfile
import uuid
from pathlib import Path

import usage


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=str(path.parent), delete=False) as f:
        json.dump(value, f, indent=2)
        f.write("\n")
    os.replace(f.name, str(path))


def local(root):
    return Path(root) / "runs/brief-usage/local"


def state_path(root, provider, sid):
    return local(root) / (digest(provider + ":" + sid) + ".json")


def number(value, field):
    if type(value) is not int or value < 0:
        raise ValueError("Missing/invalid token count: " + field)
    return value


def scan(path, provider):
    """Read recognized transcript shapes, discarding all content immediately.

    Version families are explicit. A changed usage shape refuses collection.
    Codex totals include cached input and reasoning output; neither is added twice.
    """
    rows, model, effort, previous, version = {}, None, None, None, None
    if not path or not Path(path).is_file():
        raise ValueError("Harness transcript not available yet")
    with Path(path).open() as f:
        for line in f:
            if not line.endswith("\n"):
                break  # Writer may still be flushing this record.
            r = json.loads(line)
            if provider == "anthropic":
                m = r.get("message") or {}
                if r.get("type") != "assistant" or not m.get("usage") or m.get("model") == "<synthetic>":
                    continue
                version = r.get("version", "")
                if not version.startswith("2.1."):
                    raise ValueError("Unsupported Claude transcript version")
                u = m["usage"]
                rid = r.get("requestId") or m.get("id")
                if not rid or not m.get("model"):
                    raise ValueError("Claude response missing request/model ID")
                tokens = {k: number(u.get(v), v) for k, v in {
                    "input": "input_tokens", "output": "output_tokens",
                    "cache_read": "cache_read_input_tokens", "cache_write": "cache_creation_input_tokens"}.items()}
                ttl = u.get("cache_creation") or {}
                row = {"request_id": rid, "model": m["model"], "effort": r.get("effort"),
                       "tokens": tokens, "cache_write_by_ttl": {"5m": ttl.get("ephemeral_5m_input_tokens"), "1h": ttl.get("ephemeral_1h_input_tokens")},
                       "speed": "normal" if u.get("speed") == "standard" else u.get("speed"), "at": r.get("timestamp"), "harness_version": version}
                # A response can appear once per content block. Keep final counts.
                if rid in rows and any(tokens[k] < rows[rid]["tokens"][k] for k in tokens):
                    continue
                rows[rid] = row
            else:
                p = r.get("payload") or {}
                if r.get("type") == "session_meta":
                    version = p.get("cli_version", "")
                    if not re.match(r"0\.(166|167)\.", version):
                        raise ValueError("Unsupported Codex transcript version: " + version)
                elif r.get("type") == "turn_context":
                    model, effort = p.get("model"), p.get("effort")
                elif r.get("type") == "event_msg" and p.get("type") == "token_count" and p.get("info"):
                    u = p["info"].get("total_token_usage")
                    if not isinstance(u, dict) or not version or not model:
                        raise ValueError("Codex usage missing cumulative counts/model/version")
                    totals = {k: number(u.get(k), k) for k in ("input_tokens", "cached_input_tokens", "output_tokens")}
                    # The older 0.166 format has no cache-write field (OpenAI cache writes are not separately metered).
                    totals["cache_write_input_tokens"] = number(u.get("cache_write_input_tokens", 0), "cache_write_input_tokens")
                    delta = {k: v - (previous or {}).get(k, 0) for k, v in totals.items()}
                    previous = totals
                    if not any(delta.values()):
                        continue  # Rate-limit-only updates repeat cumulative totals.
                    if min(delta.values()) < 0 or delta["cached_input_tokens"] + delta["cache_write_input_tokens"] > delta["input_tokens"]:
                        raise ValueError("Codex cumulative usage reset or invalid cache counts")
                    rid = "codex-total:" + digest(json.dumps(totals, sort_keys=True))
                    rows[rid] = {"request_id": rid, "model": model, "effort": effort,
                        "tokens": {"input": delta["input_tokens"] - delta["cached_input_tokens"] - delta["cache_write_input_tokens"],
                                   "output": delta["output_tokens"], "cache_read": delta["cached_input_tokens"], "cache_write": delta["cache_write_input_tokens"]},
                        "cache_write_by_ttl": {"5m": None, "1h": None}, "speed": None,
                        "at": r.get("timestamp"), "harness_version": version}
    return rows


def receipt(root, binding, row):
    event = {"schema": "brief-usage/2", **{k: binding[k] for k in ("brief_key", "stage", "revision_id", "session_id", "provider")},
             "person": None, "account_ref": None, "identity_sources": {"person": None, "account_ref": None},
             "continued_from_session_id": binding.get("continued_from_session_id"),
             "continuation_basis": "explicit-pickup" if binding.get("continued_from_session_id") else None,
             "source": "harness-transcript", "billing_basis": "api-equivalent-not-subscription-charge", **row}
    # Codex cumulative IDs are scoped to the actual session. Claude uses provider request IDs.
    identity = row["request_id"] if binding["provider"] == "anthropic" else binding["session_id"] + ":" + row["request_id"]
    path = Path(root) / "runs/brief-usage/requests" / (digest(binding["provider"] + ":" + identity) + ".json")
    old = usage.read(path, None)
    if old:
        fixed = ("brief_key", "stage", "revision_id", "session_id", "model", "provider", "source")
        if any(old.get(k) != event.get(k) for k in fixed):
            raise ValueError("Conflicting request attribution")
        if any(event["tokens"][k] < old["tokens"][k] for k in event["tokens"]):
            raise ValueError("Token counts decreased")
    write(path, event)


def session_file(root, binding):
    return Path(root) / "runs/brief-usage/sessions" / (binding["binding_id"] + ".json")


def collect(root, state):
    b = state.get("binding")
    if not b:
        return
    report = usage.read(session_file(root, b), {})
    try:
        rows = scan(state.get("transcript_path"), state["provider"])
        for rid, row in rows.items():
            if rid not in state["excluded"]:
                receipt(root, b, row)
        observed = sum(rid not in state["excluded"] for rid in rows)
        report.update(state="collecting" if observed else "awaiting-events", observed_requests=observed,
                      last_collected_at=usage.stamp(), collection_errors=[])
    except (ValueError, OSError, KeyError) as e:
        report.update(state="collection-error", collection_errors=[str(e)])
        write(session_file(root, b), report)
        raise
    write(session_file(root, b), report)


def resolve(root, brief):
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", brief):
        raise ValueError("Invalid brief identifier")
    suffix = "brief-%04d" % int(brief) if brief.isdigit() else brief
    matches = [p for p in (Path(root) / "runs/handoffs").glob("*/*/*/delivery-state.json")
               if p.parent.name == suffix or (brief.isdigit() and p.parent.name.endswith("_" + suffix))]
    if len(matches) != 1:
        raise ValueError("Pickup requires one issued brief; use its full key")
    return matches[0].parent.name, usage.read(matches[0], {})["revision_id"]


def bind(root, state, brief, stage="production", continued=None):
    key, revision = resolve(root, brief)
    attr = {"brief_key": key, "stage": stage, "revision_id": revision, "continued_from_session_id": continued}
    usage.valid_attribution(attr, Path(root))
    old = state.get("binding")
    if old and all(old.get(k) == v for k, v in attr.items()):
        collect(root, state)
        return old
    collect(root, state)
    # Claude creates a brand-new transcript only after UserPromptSubmit. A
    # runtime startup event proves this is new; a missing resumed file refuses.
    if state.get("start_source") == "startup" and not old and state.get("transcript_path") and not Path(state["transcript_path"]).exists():
        rows = {}
    else:
        rows = scan(state.get("transcript_path"), state["provider"])
    if old:
        report = usage.read(session_file(root, old), {})
        report.update(state="released", ended_at=usage.stamp())
        write(session_file(root, old), report)
    b = {**attr, "provider": state["provider"], "session_id": state["session_id"], "started_at": usage.stamp()}
    b["binding_id"] = uuid.uuid4().hex
    state.update(binding=b, excluded=list(rows))
    write(session_file(root, b), {"schema": "brief-usage-session/2", **b, "state": "awaiting-events",
          "person": None, "account_ref": None, "collection_errors": [],
          "coverage": "Responses after pickup in this session; earlier history excluded"})
    return b


def parse_pickup(prompt):
    # Only an explicit leading pickup command changes attribution, never a mention in prose.
    m = re.match(r"^\s*(?:/brief-pickup|pick\s+up(?:\s+brief)?|pickup(?:\s+brief)?)\s+([\w.-]+)(.*)$", prompt, re.I | re.S)
    if not m:
        return None
    tail = shlex.split(m[2])
    result = {"brief": m[1], "stage": "production", "continued": None}
    for flag, key in (("--stage", "stage"), ("--continued-from", "continued")):
        if flag in tail:
            i = tail.index(flag)
            if i + 1 == len(tail):
                raise ValueError("Missing value for " + flag)
            result[key] = tail[i + 1]
    return result


def handle(root, provider, payload):
    sid = payload.get("session_id")
    if not sid or not re.fullmatch(r"[\w.-]+", sid):
        raise ValueError("Hook missing actual session ID")
    path = state_path(root, provider, sid)
    state = usage.read(path, {"provider": provider, "session_id": sid})
    if payload.get("transcript_path"):
        state["transcript_path"] = payload["transcript_path"]
    event = payload.get("hook_event_name")
    if event == "SessionStart":
        state["start_source"] = payload.get("source")
    if event == "SessionStart" and provider == "anthropic" and os.environ.get("CLAUDE_ENV_FILE"):
        with open(os.environ["CLAUDE_ENV_FILE"], "a") as f:
            f.write("\nexport BRIEF_USAGE_SESSION_ID=" + shlex.quote(sid) + "\nexport BRIEF_USAGE_PROVIDER=anthropic\n")
    message = None
    try:
        pickup = parse_pickup(payload.get("prompt", "")) if event == "UserPromptSubmit" else None
        if pickup:
            b = bind(root, state, **pickup)
            message = "Brief tracking active: {brief_key}, {revision_id}, {stage}; actual session {session_id}.".format(**b)
        elif event == "UserPromptSubmit" and payload.get("prompt", "").strip() == "/brief-release":
            collect(root, state)
            b = state.pop("binding", None)
            if b:
                report = usage.read(session_file(root, b), {})
                report.update(state="released", ended_at=usage.stamp())
                write(session_file(root, b), report)
            message = "Brief tracking released for this session."
        else:
            collect(root, state)
        if event == "SessionEnd" and state.get("binding"):
            report = usage.read(session_file(root, state["binding"]), {})
            report.update(state="session-ended", ended_at=usage.stamp())
            write(session_file(root, state["binding"]), report)
    finally:
        write(path, state)
    return message


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    h = sub.add_parser("hook")
    h.add_argument("--provider", choices=("anthropic", "openai"), required=True)
    b = sub.add_parser("pickup")
    b.add_argument("brief")
    b.add_argument("--stage", default="production")
    b.add_argument("--continued-from", dest="continued")
    a = p.parse_args(argv)
    root = usage.workspace()
    local(root).mkdir(parents=True, exist_ok=True)
    with (local(root) / "collector.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if a.command == "hook":
            if os.environ.get("BRIEF_USAGE_MODE") == "otel":
                return 0
            payload = json.load(sys.stdin)
            try:
                message = handle(root, a.provider, payload)
            except (ValueError, OSError, KeyError) as exc:
                if payload.get("hook_event_name") == "UserPromptSubmit":
                    raise  # A refused pickup must not pretend work is tracked.
                # Collection errors stay in the ledger and hook diagnostics.
                # Exit 2 on Stop would ask the model to keep working indefinitely.
                print("Brief tracking: " + str(exc), file=sys.stderr)
                return 1
            if message:
                print(json.dumps({"hookSpecificOutput": {"hookEventName": payload["hook_event_name"], "additionalContext": message}}))
        else:
            provider = os.environ.get("BRIEF_USAGE_PROVIDER") or ("openai" if os.environ.get("CODEX_THREAD_ID") else None)
            sid = os.environ.get("BRIEF_USAGE_SESSION_ID") or os.environ.get("CODEX_THREAD_ID")
            if not provider or not sid:
                raise ValueError("No harness session context. Start in this repo with hooks enabled, then pick up the brief.")
            path = state_path(root, provider, sid)
            state = usage.read(path, None)
            if not state:
                raise ValueError("Session hook has not run. Review/trust project hooks and restart the session.")
            result = bind(root, state, a.brief, a.stage, a.continued)
            write(path, state)
            print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError) as exc:
        print("Brief tracking: " + str(exc), file=sys.stderr)
        sys.exit(2)
