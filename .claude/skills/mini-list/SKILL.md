---
name: mini-list
description: List what the shared Mac mini can run for you right now — every component with a mini door, the arguments it takes, and whether it has actually worked on the mini (its last run's result). Use when someone asks "what can the mini run", "what's ready on the mini", "can I run X on the mini", "which components work on the mini", "mini list", "/mini-list". Reads your pulled clone; files nothing, needs no key.
---

# mini-list — what the mini can run, and what has proven it works

> **Activates component:** `components/run-kit` — lists what the mini can run.


the developer, 2026-10-19: "Pull the list what is ready" — the first of three `mini-` skills
(mini-list → mini-run → mini-status). Read-only.

External dependencies (rules file: pointers outside this folder are listed here):
- `components/run-kit/mini_run.py` — `list` subcommand (LD-9 (mini run filer)).
- `team/dispatch-grants.json` — read by mini_run.py; who may file each component.
- `platform/data/records/lab-runs/<person>/*.json` — every mini lab run's result record.

## Do this

1. Freshen the clone so the list is today's: `git pull --no-rebase -q origin main`
   (if the pull is refused, say so and continue on what is there — mark the answer
   "not refreshed").
2. Run `python3 components/run-kit/mini_run.py list`. It prints every component the
   mini has a door for: owner, who may file it, the script, and the arguments the
   door takes (`--name <value>`; file them later as `name=value`).
3. Add "has it worked on the mini?" from the result records — run this and fold its
   lines into the list:

   ```
   python3 - <<'EOF'
   import json, glob, os
   last = {}
   for f in glob.glob("platform/data/records/lab-runs/*/*.json"):
       try: d = json.load(open(f))
       except Exception: continue
       parts = (d.get("script") or "").split("/")
       c = d.get("component") or (parts[1] if len(parts) > 1 and parts[0] == "components" else "?")
       t = d.get("finished") or d.get("started") or ""
       if c != "?" and t >= last.get(c, ("",))[0]:
           last[c] = (t, d.get("status"), d.get("requester"), os.path.basename(f)[:-5],
                      (d.get("args") or {}).get("dry_run") == "yes")
   for c, (t, s, who, label, dry) in sorted(last.items()):
       print(f"{c:22} last {s:7} {t[:16]}Z  by {who}  ({label}{', dry' if dry else ''})")
   EOF
   ```

4. Answer as ONE table — component · what it does (one line, from the list) · last
   result on the mini (done / failed, when, dry or real) · who may file. Mark a
   component READY only when its last run is `done`; a `failed` last run or no run at
   all is "not proven" — never call it ready.
5. End with the next step: "say which one to run and I'll use mini-run" — and the
   arguments that component needs, from step 2.

## Never

- Never file, change or delete anything — this skill only reads.
- Never call a component ready from the list alone: the door existing is not the
  machine working.
