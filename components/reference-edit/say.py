#!/usr/bin/env python3
"""Say the change in your own words; the library finds the row and fills it.

    say.py "the tube is in the wrong hand" --picture <png> --brand <brand>
    say.py "make the headline say SIXTY DAYS instead" --picture … --brand … --go
    say.py "…" --picture … --brand … --rows          what it matched, and why

the owner, 2026-09-25: *"I want to literally describe changes with natural voice
then your system indexes what I mean and interprets it for the tool to write
the appropriate prompt so that it understands in its language clearly so
that we get the exact changes we want without slop."*

The two languages already exist in every library row: `what` is the change
as a person says it, `delta` is the same change in the words the image model
needs. Nothing here writes a new instruction — **it chooses a row and fills
its slots**, so every edit still goes through the discipline that makes the
judge able to police it.

**It refuses rather than guesses.** No row matched, or two matched equally
well, and it stops and says so; a sentence that matches nothing is written
to `unmatched.json`, which is the list of rows the library is missing. That
file is how the library grows — from what was actually asked for, never from
what somebody imagined might be asked.

`--go` runs the edit. Without it, nothing is spent: it prints the row, the
filled slots and the exact instruction the tool will hear, so a wrong match
is caught before it costs anything.
"""
import argparse, json, os, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from reference_edit import paths as P                      # noqa: E402

LIB = HERE / "library"
UNMATCHED = LIB / "unmatched.json"

ASK = """A person has asked for ONE change to a picture, in their own words:

> {said}

Below is every change this system knows how to make. Each row has an id,
what it is for, and the slots it needs filled.

{rows}

Pick the ONE row that matches what they asked for, and fill every slot it
needs from their words.

Rules:
- **Only these rows exist.** Never invent a row, never rename one.
- **Fill slots from what they said**, not from what you would like them to
  have said. A slot you cannot fill from their words is `null`.
- If NOTHING fits, answer `"row": null` and write one line proposing the row
  that would have fitted — that is how this list grows.
- If TWO rows fit equally well, answer `"row": null` and name both in
  `ambiguous`, because guessing is how the wrong thing gets changed.

Reply as JSON only:
{{"row": "<id or null>", "args": {{"<slot>": "<value or null>"}},
  "why": "one line — what in their words picked this row",
  "ambiguous": ["<id>", "<id>"] or [],
  "proposed": "<one line, only when row is null and nothing fit>"}}
"""


def rows():
    """Every fix and every variation the library holds, as one list."""
    out = []
    for f in sorted(LIB.glob("fixes-v*.json")) + sorted(LIB.glob("variations-v*.json")):
        d = json.loads(f.read_text())
        got = d.get("fixes") or d.get("variations") or d
        for r in (got if isinstance(got, list) else got.values()):
            if isinstance(r, dict) and r.get("id"):
                out.append({**r, "_kind": "fix" if "fixes" in f.name else "variation",
                            "_file": f.name})
    keep, seen = [], set()
    for r in reversed(out):                 # the highest version of an id wins
        if r["id"] not in seen:
            seen.add(r["id"]); keep.append(r)
    return list(reversed(keep))


def render_rows(rs):
    return "\n".join(
        f"- `{r['id']}` ({r['_kind']}) — {r.get('what', r.get('name', ''))}"
        + (f"  ·  slots: {', '.join(r['needs'])}" if r.get("needs") else "  ·  no slots")
        for r in rs)


def match(said, rs, model=None):
    sys.path.insert(0, str(P.repo() / "components/reference-edit"))
    from reference_edit import compare as C
    entry = C.entry() if hasattr(C, "entry") else None
    prompt = ASK.format(said=said, rows=render_rows(rs))
    try:
        out = C.google_caller(prompt, [], entry)
    except Exception as e:                                  # noqa: BLE001
        raise SystemExit(f"could not reach the matcher: {type(e).__name__}: {e}")
    if isinstance(out, str):
        t = out.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        out = json.loads(t)
    return out


def record_unmatched(said, proposed):
    got = json.loads(UNMATCHED.read_text()) if UNMATCHED.is_file() else {"unmatched": []}
    got["_what"] = ("Sentences the library had no row for. This is the list of rows to "
                    "add, written from what was actually asked for.")
    got["unmatched"].append({"said": said, "proposed": proposed,
                             "at": date.today().isoformat()})
    UNMATCHED.write_text(json.dumps(got, indent=1, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("said")
    ap.add_argument("--picture")
    ap.add_argument("--brand")
    ap.add_argument("--label")
    ap.add_argument("--go", action="store_true", help="run the edit; without it, nothing is spent")
    ap.add_argument("--rows", action="store_true", help="print the library and stop")
    ap.add_argument("--model")
    a = ap.parse_args()

    rs = rows()
    if a.rows:
        print(render_rows(rs)); return

    m = match(a.said, rs, a.model)
    rid = m.get("row")

    if not rid:
        print(f'REFUSED — "{a.said}"\n')
        if m.get("ambiguous"):
            print("  two rows fit equally well: " + ", ".join(m["ambiguous"]))
            print("  say which one, or say it more precisely.")
        else:
            print("  no row in the library makes this change.")
            if m.get("proposed"):
                print(f"  it would need a new row: {m['proposed']}")
                record_unmatched(a.said, m["proposed"])
                print(f"  written to {UNMATCHED.name} — the owner signs a new row")
        sys.exit(1)

    row = next((r for r in rs if r["id"] == rid), None)
    if not row:
        sys.exit(f"the matcher named a row that does not exist: {rid}")
    args = {k: v for k, v in (m.get("args") or {}).items() if v is not None}
    missing = [s for s in (row.get("needs") or []) if not args.get(s)]

    delta = row.get("delta", "")
    for k, v in args.items():
        delta = delta.replace("{" + k + "}", str(v))

    print(f'"{a.said}"\n')
    print(f"  row     {row['id']} · {row.get('name')} ({row['_kind']})")
    print(f"  why     {m.get('why', '')}")
    for k, v in args.items():
        print(f"  {k:<8}{v}")
    if missing:
        print(f"\nREFUSED — {row['id']} needs {', '.join(missing)} and your words do not say it.")
        print("  say it with the missing part in, and it will run.")
        sys.exit(1)
    print(f"\n  the tool will hear:\n    {delta}")

    if not a.go:
        print("\n  nothing spent. add --go to run it.")
        return
    if not (a.picture and a.brand):
        sys.exit("--picture and --brand are needed to run it")

    flag = "--fix" if row["_kind"] == "fix" else "--v"
    val = row["id"] if row["_kind"] == "fix" else \
        row["id"] + ":" + ",".join(f"{k}={v}" for k, v in args.items())
    cmd = [sys.executable, str(HERE / "edit.py" if row["_kind"] == "fix" else HERE / "vary.py"),
           a.picture, "--brand", a.brand, flag, val]
    if row["_kind"] == "fix":
        for k, v in args.items():
            cmd += ["--arg", f"{k}={v}"]
    if a.label:
        cmd += ["--label", a.label]
    print()
    subprocess.run(cmd, cwd=str(P.repo()))


if __name__ == "__main__":
    main()
