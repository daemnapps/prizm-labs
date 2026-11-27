"""Per-brief token receipts from Claude Code OTLP API-request events.

Public: record_otlp(payload, attribution, root), summarize(brief_key, root).
CLI run launches a dedicated brief/stage session with a loopback collector.
No prompts, responses, emails, credentials, or raw telemetry are persisted.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import tempfile
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TOKEN_MAP = {"input_tokens": "input", "output_tokens": "output",
             "cache_read_tokens": "cache_read", "cache_creation_tokens": "cache_write"}


def workspace():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run-kit"))
    from run_kit import paths
    return paths.repo()


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read(path, fallback):
    return json.loads(path.read_text()) if path.exists() else fallback


def attrs(values):
    return {a["key"]: next(iter(a.get("value", {}).values()), None) for a in values}


def valid_attribution(a, root):
    for key in ("brief_key", "stage", "revision_id"):
        if not isinstance(a.get(key), str) or not re.fullmatch(r"[a-zA-Z0-9_.-]+", a[key]):
            raise ValueError("Required identifier: " + key)
    for key in ("person", "account_ref", "continued_from_session_id"):
        if a.get(key) is not None and (not isinstance(a[key], str) or not re.fullmatch(r"[a-zA-Z0-9_.:-]+", a[key])):
            raise ValueError("Invalid optional identifier: " + key)
    if a.get("person") and not (root / "team/people" / a["person"] / "identity.json").is_file():
        raise ValueError("Unknown person")
    if not a["revision_id"].startswith(a["brief_key"] + "-R"):
        raise ValueError("Revision must belong to the brief")
    states = list((root / "runs/handoffs").glob("*/*/" + a["brief_key"] + "/delivery-state.json"))
    if not states:
        raise ValueError("Brief has no issued delivery state")
    if len(states) != 1 or read(states[0], {}).get("revision_id") != a["revision_id"]:
        raise ValueError("Use the brief's current, unambiguous revision")
    if a.get("continued_from_session_id"):
        prior = load_context(root)["requests"].get(a["brief_key"], [])
        if not any(x.get("session_id") == a["continued_from_session_id"] for x in prior):
            raise ValueError("Continuation must name a recorded session on this brief")
    return a


def observed_identity(attributes, root):
    """Resolve only provider-reported identity through the existing org map.

    No email-local-part guessing, assignment fallback or presumed account plan.
    Account references are stable hashes; raw provider IDs/emails are not stored.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run-kit"))
    from run_kit import people
    person = people.try_person_of(root, attributes.get("user.email"))
    field = next((k for k in ("user.account_uuid", "user.account_id") if attributes.get(k)), None)
    account = "anthropic:" + hashlib.sha256((field + ":" + str(attributes[field])).encode()).hexdigest() if field else None
    return {"person": person, "account_ref": account,
            "identity_sources": {"person": "provider-email+team-identity" if person else None, "account_ref": field}}


def record_otlp(payload, attribution, root):
    """Filter OTLP/HTTP JSON logs to completed API requests, and deduplicate.

    Work context is set by the launcher; actor/account identity comes from events.
    Partial/missing counts refuse that receipt and surface a collection error.
    """
    root = Path(root)
    valid_attribution(attribution, root)
    accepted = 0
    for resource in payload.get("resourceLogs", []):
        common = attrs(resource.get("resource", {}).get("attributes", []))
        for scope in resource.get("scopeLogs", []):
            for log in scope.get("logRecords", []):
                a = dict(common, **attrs(log.get("attributes", [])))
                name = a.get("event.name") or log.get("body", {}).get("stringValue")
                if name not in ("api_request", "claude_code.api_request"):
                    continue
                for field in ("request_id", "session.id", "model"):
                    if not a.get(field):
                        raise ValueError("API request missing " + field)
                counts = {}
                for field, column in TOKEN_MAP.items():
                    n = a.get(field)
                    if isinstance(n, str) and n.isdigit():
                        n = int(n)
                    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
                        raise ValueError("API request missing/invalid " + field)
                    counts[column] = n
                ttl = {}
                for name in ("5m", "1h"):
                    value = a.get("cache_creation_" + name + "_tokens")
                    if isinstance(value, str) and value.isdigit():
                        value = int(value)
                    ttl[name] = value if type(value) is int and value >= 0 else None
                if all(v is not None for v in ttl.values()) and sum(ttl.values()) > counts["cache_write"]:
                    raise ValueError("Cache lifetime counts exceed total cache writes")
                identity = observed_identity(a, root)
                event = {"schema": "brief-usage/2",
                         **{k: attribution[k] for k in ("brief_key", "stage", "revision_id")},
                         **identity, "declared_person": attribution.get("person"),
                         "declared_account_ref": attribution.get("account_ref"),
                         "continued_from_session_id": attribution.get("continued_from_session_id"),
                         "continuation_basis": "launcher-declared" if attribution.get("continued_from_session_id") else None,
                         "provider": "anthropic",
                         "source": "claude-code-otel", "request_id": a["request_id"],
                         "session_id": a["session.id"], "model": a["model"], "tokens": counts, "cache_write_by_ttl": ttl,
                         "at": a.get("event.timestamp") or str(log.get("timeUnixNano") or ""),
                         "query_source": a.get("query_source"), "prompt_id": a.get("prompt.id"), "speed": a.get("speed"),
                         "effort": a.get("effort"), "event_sequence": a.get("event.sequence"), "billing_basis": "api-equivalent-not-subscription-charge"}
                key = hashlib.sha256((event["provider"] + ":" + event["request_id"]).encode()).hexdigest()
                dest = root / "runs/brief-usage/requests" / (key + ".json")
                dest.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", dir=str(dest.parent), suffix=".tmp", delete=False) as f:
                    json.dump(event, f, indent=2)
                    f.write("\n")
                    temp = Path(f.name)
                try:
                    # Link only complete bytes; exclusive destination deduplicates collectors.
                    os.link(str(temp), str(dest))
                    accepted += 1
                except FileExistsError:
                    if read(dest, {}) != event:
                        raise ValueError("Conflicting attribution or counts for request " + event["request_id"])
                finally:
                    temp.unlink()
    return accepted


def load_context(root):
    """Load shared price data and usage receipts once for a multi-brief view."""
    root = Path(root)
    context = {"prices": read(root / "platform/data/model-prices.json", {}), "requests": {}, "sessions": {}, "errors": []}
    for kind in ("requests", "sessions"):
        for path in (root / "runs/brief-usage" / kind).glob("*.json"):
            try:
                item = read(path, {})
                context[kind].setdefault(item["brief_key"], []).append(item)
            except (OSError, ValueError, KeyError):
                context["errors"].append("Unreadable usage receipt: " + path.name)
    return context


def summarize(brief_key, root, context=None):
    context = context or load_context(root)
    prices = context["prices"]
    rows = context["requests"].get(brief_key, [])
    sessions = context["sessions"].get(brief_key, [])
    errors = context["errors"]
    totals, groups, dollars, uncovered = {k: 0 for k in TOKEN_MAP.values()}, {}, 0.0, 0
    for row in rows:
        key = (row["person"], row["stage"], row["revision_id"], row["model"], row["account_ref"], row["session_id"], row.get("effort"), row["provider"])
        group = groups.setdefault(key, {"person": key[0], "stage": key[1], "revision_id": key[2],
                                        "model": key[3], "account_ref": key[4], "session_id": key[5], "effort": key[6], "provider": key[7], "tokens": 0, "calls": 0, "priced_portion_usd": 0.0, "unpriced_tokens": 0})
        group["calls"] += 1
        rates = prices.get("models", {}).get(row["model"], {})
        for category, n in row["tokens"].items():
            totals[category] += n
            group["tokens"] += n
            portions = {category: n}
            ttl = row.get("cache_write_by_ttl") or {}
            if category == "cache_write" and all(ttl.get(k) is not None for k in ("5m", "1h")):
                portions = {"cache_write_5m": ttl["5m"], "cache_write_1h": ttl["1h"],
                            "cache_write": n - ttl["5m"] - ttl["1h"]}
            for price_key, count in portions.items():
                rate = rates.get(price_key)
                # This table is standard-tier only. Unknown/fast modes are unpriced.
                if row.get("speed") != "normal" or rate is None:
                    uncovered += count
                    group["unpriced_tokens"] += count
                else:
                    dollars += count * rate / 1e6
                    group["priced_portion_usd"] += count * rate / 1e6
    for group in groups.values():
        group["priced_portion_usd"] = round(group["priced_portion_usd"], 6)
        group["api_equivalent_usd"] = None if group["unpriced_tokens"] else group["priced_portion_usd"]
    collection_errors = sum(len(s.get("collection_errors", [])) for s in sessions)
    return {"state": "collection-error" if collection_errors else "observed" if rows else "awaiting-events" if sessions else "not-connected",
            "tokens": sum(totals.values()) if rows else None, "token_classes": totals if rows else None,
            "requests": len(rows), "breakdown": list(groups.values()), "sessions": len(sessions),
            "session_ids": sorted({row["session_id"] for row in rows} | {s["session_id"] for s in sessions if s.get("session_id")}),
            "tracking": [{k: s.get(k) for k in ("session_id", "provider", "stage", "revision_id", "state", "started_at", "last_collected_at", "ended_at", "coverage", "collection_errors")} for s in sessions],
            "attempts": [{k: row.get(k) for k in ("at", "request_id", "session_id", "prompt_id", "provider", "model", "effort", "stage", "revision_id", "person", "account_ref", "identity_sources", "continued_from_session_id", "query_source", "event_sequence", "tokens")} for row in sorted(rows, key=lambda r: r.get("at") or "")],
            "api_equivalent_usd": round(dollars, 6) if rows and not uncovered else None,
            "priced_portion_usd": round(dollars, 6) if rows else None,
            "unpriced_tokens": uncovered, "price_source": prices.get("_source"),
            "billing_basis": "API-equivalent comparison; not a subscription charge",
            "coverage": "Observed instrumented sessions only; historical/uninstrumented work is unknown",
            "collection_errors": collection_errors, "errors": errors}


def run_session(command, attribution, root):
    root = Path(root)
    valid_attribution(attribution, root)
    lock = threading.Lock()
    errors = []
    secret = uuid.uuid4().hex
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass
        def do_POST(self):
            if self.path != "/v1/logs" or self.headers.get("Authorization") != "Bearer " + secret:
                self.send_error(403)
                return
            size = int(self.headers.get("Content-Length", "0"))
            if size > 4000000:
                self.send_error(413)
                return
            try:
                payload = json.loads(self.rfile.read(size))
                with lock:
                    record_otlp(payload, attribution, root)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
                self.send_error(400, "Usage receipt rejected")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    identifier = uuid.uuid4().hex
    path = root / "runs/brief-usage/sessions" / (identifier + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    session = {"schema": "brief-usage-session/1", **attribution, "started_at": stamp(),
               "attribution_basis": "launcher-declared; actual identity is recorded per request",
               "state": "collecting", "coverage": "this launched process and inheriting subprocesses"}
    path.write_text(json.dumps(session, indent=2) + "\n")
    env = dict(os.environ)
    env.update({"BRIEF_USAGE_MODE": "otel", "CLAUDE_CODE_ENABLE_TELEMETRY": "1", "OTEL_LOGS_EXPORTER": "otlp", "OTEL_METRICS_INCLUDE_SESSION_ID": "true", "OTEL_LOGS_EXPORT_INTERVAL": "1000",
                "OTEL_EXPORTER_OTLP_LOGS_PROTOCOL": "http/json",
                "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT": "http://127.0.0.1:%d/v1/logs" % server.server_port,
                "OTEL_EXPORTER_OTLP_LOGS_HEADERS": "Authorization=Bearer " + secret,
                "OTEL_LOG_USER_PROMPTS": "0", "OTEL_LOG_ASSISTANT_RESPONSES": "0",
                "OTEL_LOG_TOOL_DETAILS": "0", "OTEL_LOG_RAW_API_BODIES": "0"})
    code = None
    try:
        code = subprocess.call(command, env=env, cwd=str(root))
    finally:
        server.shutdown()
        server.server_close()
        session.update(state="process-ended", ended_at=stamp(), exit_code=code, collection_errors=errors)
        path.write_text(json.dumps(session, indent=2) + "\n")
        print(json.dumps(summarize(attribution["brief_key"], root), indent=2))
    return code


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="verb", required=True)
    show = sub.add_parser("show")
    show.add_argument("brief_key")
    run = sub.add_parser("run")
    for arg in ("brief-key", "stage", "revision-id"):
        run.add_argument("--" + arg, required=True)
    for arg in ("person", "account-ref", "continued-from-session-id"):
        run.add_argument("--" + arg)
    run.add_argument("command", nargs=argparse.REMAINDER)
    args = p.parse_args()
    root = workspace()
    if args.verb == "show":
        print(json.dumps(summarize(args.brief_key, root), indent=2))
        return 0
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        p.error("Supply the Claude Code command after --")
    attribution = {k: getattr(args, k) for k in ("brief_key", "person", "stage", "revision_id", "account_ref", "continued_from_session_id")}
    return run_session(command, attribution, root)


if __name__ == "__main__":
    sys.exit(main())
