#!/usr/bin/env python3
"""print_runner.py — the 3D print step with no session in the loop (owner, 2026-11-20: the pictures must not be "done by
hand"; the 3D print was the one step of the chain with no runner).

Every open set request (image_production/set_queue.py) is cleared by the 3d-print skill (.claude/skills/3d-print), the
same process a session follows, run headless through the chain's one Claude door (run_kit/claude_door.py) on a Claude
login, the only kind that carries the account's connected 3D builder. One request at a time, one print each: a wrong
print is filed with what is wrong and never printed again (the one-paid-take rule). The prints are the one spend here;
the run needs the owner's go (`--yes`) and a cap in credits, and stops before a request whose print would pass the cap,
read off the account's own spend transactions (a top-up never hides spend).

    python3 components/image-production/print_runner.py --brand <brand> [--run <production run>] [--only <id> …]
                                                         [--cap <credits> --yes] [--dry-run]

Writes runs/image-production/<brand>/print-runner/<stamp>.json: each request, what the skill reported, the credits
spent. Brand-agnostic.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[1]
PRINT_CREDITS = 2.5          # the most one 3D Jutsu print costs (1.25 at 1.5k, 2.5 for a store picture at 2k): the cap never under-counts
TOOLS = "Bash,Read,Write,Edit,Glob,Grep,mcp__claude_ai_Higgsfield"
PROMPT = """You are the 3D print runner. Follow .claude/skills/3d-print/SKILL.md for exactly ONE request and nothing else:
brand {brand}, request {rid}. Its plan: `python3 components/image-production/picture_sets.py plan {brand} {rid}`.
Rules for this run:
- ONE print only (one take). If the print is wrong, file it with the plan's file_it command and a note saying exactly
  what is wrong (no "kept"), and stop: never print it again.
- If the plan says stop or the request is already printing, do what the plan says; never print again.
- Spend nothing but that one print. Never touch another request.
- THE REAL PRODUCT, PASTED, before you look at the print or file it (the print never reproduces a label): for each
  product in the plan (`products[].kit`), keep the print as it came back beside it as <name>-before-paste.png, then run
  `python3 components/video-production/machine/product_paste.py <print> --kit runs/ai-elements/{brand}/products/<kit>
  --out <print>`, and judge and file the pasted print. A drawn label that the paste replaced is not a fault.
- When the print is right, file it with "kept: <what makes it right>" and run the plan's `then` command.
- Stay until the print is filed: when it is still generating, wait and read it again inside this same run (poll every
  30 seconds, up to 20 minutes). Never end your reply while a print is out and not filed.
End your reply with one line of JSON and nothing after it:
{{"request": "{rid}", "printed": true|false, "kept": true|false, "note": "<one line>"}}"""
FINISH = """You are the 3D print runner, finishing ONE request whose print was already sent: brand {brand}, request {rid}.
Its plan: `python3 components/image-production/picture_sets.py plan {brand} {rid}`; the request's `printing` record names
the generation that was sent. Follow .claude/skills/3d-print/SKILL.md from step 5's read-back on:
- NEVER print again and never submit anything new. Read the sent generation back (poll every 30 seconds, up to 20
  minutes, inside this run). A submission that stays unconfirmed is handled as the skill's "Submission unconfirmed" says.
- Then paste the real product (the same product_paste step as a new print), look at it, and file it with the plan's
  file_it command: "kept: …" when right (then the plan's `then`), else a note saying what is wrong.
End your reply with one line of JSON and nothing after it:
{{"request": "{rid}", "printed": true|false, "kept": true|false, "note": "<one line>"}}"""


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def door():
    return _load(WS / "components" / "run-kit" / "run_kit" / "claude_door.py", "pr_claude_door")


def queue():
    sys.path.insert(0, str(HERE))
    from image_production import set_queue
    return set_queue


def spent_since(since_iso: str):
    """Credits the signed-in Higgsfield account spent since a moment, from its own transactions; None when unread."""
    total, cursor = 0.0, None
    for _ in range(10):
        args = ["/opt/homebrew/bin/higgsfield", "account", "transactions", "--size", "100", "--json"] + \
               (["--cursor", cursor] if cursor else [])
        try:
            d = json.loads(subprocess.run(args, capture_output=True, text=True, timeout=120).stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            return None
        items = d.get("items") or [] if isinstance(d, dict) else []
        for t in items:
            if str(t.get("created_at") or "") < since_iso:
                return round(total, 2)
            if t.get("action") == "spend":
                total += -float(t.get("credits") or 0)
        cursor = d.get("cursor") if isinstance(d, dict) else None
        if not cursor or not items:
            break
    return round(total, 2)


def mine(r: dict, run: str | None, only) -> bool:
    if only and r["id"] not in only:
        return False
    return not run or (r.get("resume") or {}).get("run") == run or str(r["id"]).startswith(str(run).replace("_", "-").lower())


def sent(brand: str, run: str | None = None, only=()) -> list:
    """The open requests whose print was already sent and is not filed yet: read back and filed, never sent again."""
    return [r for r in queue().open_requests(brand) if r.get("printing") and mine(r, run, only)]


def waiting(brand: str, run: str | None = None, only=()) -> list:
    """The open requests to clear: not already printing; this production run's only, or the ones named."""
    out = []
    for r in queue().open_requests(brand):
        if r.get("printing"):
            continue
        if only and r["id"] not in only:
            continue
        if run and (r.get("resume") or {}).get("run") != run and not str(r["id"]).startswith(str(run).replace("_", "-").lower()):
            continue
        out.append(r)
    return out


def report_of(text: str) -> dict:
    """The skill's last line of JSON, or what it said when there is none."""
    for line in reversed((text or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return {"printed": None, "kept": False, "note": "no report: " + re.sub(r"\s+", " ", (text or "")[-200:])}


def printed_now(brand: str, rid: str, before: dict) -> bool:
    """True when this request gained a print record (a new generation) while this runner had it: one print spent."""
    now = (queue().read(brand, rid) or {}).get("printing") or {}
    return bool(now) and now.get("generation") != (before or {}).get("generation")


def clear(brand: str, reqs: list, cap: float, ask=None, spent=None, timeout=3600, finish=(), save=None) -> dict:
    """Finish the prints already sent (read back, never re-sent, nothing spent), then clear each new request through the
    skill until the cap. THE CAP COUNTS THIS RUNNER'S OWN PRINTS (2026-11-21: on a shared account the whole account's
    spend stopped a run after 4 prints of its own): each request that gained a print record while this runner had it
    is one print. {request: report}, plus `spent` (this runner's), `account_spent` (said only) and `stopped`."""
    start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ask = ask or (lambda prompt: door().run(["--output-format", "text", "--allowedTools", TOOLS,
                                             "--permission-mode", "acceptEdits"], prompt, timeout=timeout,
                                            cwd=str(WS), connectors=True))
    out = {"requests": {}, "spent": 0.0, "stopped": None, "cap": cap}

    def one(r, prompt):
        res = ask(prompt.format(brand=brand, rid=r["id"]))
        text = getattr(res, "stdout", res) if not isinstance(res, str) else res
        out["requests"][r["id"]] = dict(report_of(text), credential=getattr(res, "credential", None))
        if save:                           # the record after every request, so a long run shows its progress
            save(out)

    for r in finish:                       # already sent: no new spend
        one(r, FINISH)
    for r in reqs:
        if out["spent"] + PRINT_CREDITS > cap:
            out["stopped"] = f"the cap: {out['spent']} of {cap} credits spent by this runner; {r['id']} would pass it"
            break
        before = (queue().read(brand, r["id"]) or {}).get("printing") or r.get("printing")
        one(r, PROMPT)
        if printed_now(brand, r["id"], before):
            out["spent"] = round(out["spent"] + PRINT_CREDITS, 2)
            out["requests"][r["id"]]["credits"] = PRINT_CREDITS
            if save:
                save(out)
    acct = (spent or spent_since)(start)
    if acct is not None:
        out["account_spent"] = acct        # the whole account in this window (other sessions included): said, not counted
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--run", help="a production run: only its requests")
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--cap", type=float, help="the most credits these prints may spend")
    ap.add_argument("--yes", action="store_true", help="the owner's go for the prints")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    reqs = waiting(a.brand, a.run, a.only)
    out_now = sent(a.brand, a.run, a.only)
    print(f"{len(out_now)} print(s) already sent, to read back and file (nothing spent):")
    for r in out_now:
        print("  " + r["id"])
    print(f"{len(reqs)} request(s) to print, about {len(reqs) * PRINT_CREDITS} credits at one print each:")
    for r in reqs:
        print("  " + r["id"])
    if a.dry_run or not (reqs or out_now):
        return 0
    if not a.yes or a.cap is None:
        print("REFUSED: the prints spend credits — run with the owner's go (--yes) and a cap (--cap <credits>)")
        return 2
    d = WS / "runs" / "image-production" / a.brand / "print-runner"
    d.mkdir(parents=True, exist_ok=True)
    f = d / (time.strftime("%Y%m%d-%H%M%S") + ".json")

    def save(res):
        f.write_text(json.dumps(dict(res, state="running"), indent=1, ensure_ascii=False) + "\n")
    res = clear(a.brand, reqs, a.cap, finish=out_now, save=save)
    f.write_text(json.dumps(dict(res, state="finished"), indent=1, ensure_ascii=False) + "\n")
    for rid, rep in res["requests"].items():
        print(f"{rid}: {'kept' if rep.get('kept') else 'printed, not kept' if rep.get('printed') else 'not printed'}"
              f" — {rep.get('note') or ''}")
    print((f"STOPPED: {res['stopped']}\n" if res["stopped"] else "") + f"this runner spent {res['spent']} credits"
          + (f" (the whole account: {res['account_spent']})" if res.get("account_spent") is not None else "") + f" — {f}")
    return 0 if not res["stopped"] else 3


if __name__ == "__main__":
    sys.exit(main())
