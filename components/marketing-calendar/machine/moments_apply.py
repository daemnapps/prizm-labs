#!/usr/bin/env python3
"""File what the record proves into the brand's moments — no human in the loop.

    python3 moments_apply.py --brand <brand>            # show what would change
    python3 moments_apply.py --brand <brand> --write    # a proposal under runs/marketing-calendar/<brand>/

the owner, 2026-09-13: *"That is not a decision for me."* He is right, and the
distinction is worth stating because it governs what this file may touch:

  **Research is a judgement and needs him. The record is arithmetic and does
  not.** A moment the brand has already sent into, more than once, whose
  receipts are its own emails and whose performance is its own number, is not
  an opinion anybody has to sign. Leaving it in a report for a person to retype
  is how `cyber-monday` — the brand's best-earning moment at 7x its median —
  stayed unknown to the calendar.

So this proposes. With `--write` it files a PROPOSAL under
runs/marketing-calendar/<brand>/moments-<YYYY-MM-DD>/ — never into brands/
(K2 (brands write wall), SI-22 (calendar months home), 2026-10-07). A person
reads it, copies it with the one guarded command in PROPOSAL.md, and commits
it as their own. What it may propose is fenced:

  **A public holiday is `all` by definition** (the brand's own README: `all` =
  a holiday every avatar knows), so a holiday the record proves is filed under
  every avatar, graded `proven`, carrying the emails that prove it.

  **A recurring brand theme is NOT filed.** The record cannot say which avatar
  a send was for, and a theme that really belongs to one avatar, filed as
  `all`, puts it in front of people it was never about. Those are listed for
  him with everything needed to place them — one field, one decision.

It also CORRECTS. An entry already in the file whose grade the record
contradicts is upgraded and its stale note retired: `black-friday` sat as
`territory` with a note reading "not yet run under its own name" while the
record held nine Black Friday sends earning 1.7x the median. A claim written
once and never re-checked is the thing this file exists to stop.

The proposal records the sha256 of the brand file it was made from, so its
copy command refuses once that file has changed; every entry it proposes
carries `mined` provenance so its origin is never in doubt.
"""
import argparse
import datetime
import hashlib
import json
import shlex
import sys
from pathlib import Path

from paths import COMPONENTS, WORKSPACE, brand_root, month_dir, rel
sys.path.append(str(COMPONENTS / "brandpath"))      # appended, never ahead of this tool
import brandpath as BP                                # noqa: E402
import moments_mine as M

STREAM = {"holiday": "fixed", "recurring": "seasonal"}

# `proven` means the brand built a HABIT, not that it once mentioned something.
# The miner's own definition is two or more sends; without this the first run
# offered `small-business-saturday` — one email, earning 0.7x the median — as
# proven alongside Cyber Monday's 7x. One send is a brand touching a date.
PROVEN_SENDS = 2
STALE = ("not yet run", "never run", "no prior send", "not yet used",
         "the record only shows")


def receipts(f, cap=6):
    return [f"{d.isoformat()} {r.get('subject', '(no subject)')}"
            for d, r in f["sends"][:cap]]


def window_text(f):
    """The window in words, for a person.

    `when` describes the EVIDENCE — "once, in 2025". `window` has always
    described the MOMENT. Writing one into the other made the file read as
    though Cyber Monday happens once ever.
    """
    if f["how"] != "holiday":
        return f["when"]
    import holidays as H
    for r in H.table(datetime.date.today().year):
        if r["key"] == f["key"]:
            d = datetime.date.fromisoformat(r["start"])
            return (f"{d:%-d %B}" if r["span"] == 1
                    else f"{d:%-d %B} and the {r['span'] - 1} days after")
    return f["key"].replace("-", " ")


def entry(f, today):
    """One moment, as the brand's own file shapes them."""
    e = {"key": f["key"], "stream": STREAM[f["how"]],
         "window": window_text(f), "evidence": "proven",
         "sent": receipts(f), "anchor": json.loads(f["anchor"]),
         "audience": "all",
         "mined": {"on": today, "how": f["how"], "sends": len(f["sends"])}}
    if f.get("ratio"):
        e["mined"]["earned"] = f"{f['ratio']:.1f}x the brand's median per recipient"
    return e


def plan(brand):
    """What would change, without changing it."""
    found, known, median, ledger = M.mine(brand)
    root = brand_root(brand)
    doc = json.loads(BP.brand_path(root.name, "strategy", "moments.json", root=root.parent).read_text())
    today = datetime.date.today().isoformat()

    adds, fixes, held, thin = [], [], [], []
    for f in found:
        if f["how"] != "holiday":
            # the record cannot say whose it is — one field, his call
            if not f["known"]:
                held.append(f)
            continue
        if len(f["sends"]) < PROVEN_SENDS:
            # touched once. Worth seeing, never worth filing as a habit.
            if not f["known"]:
                thin.append(f)
            continue
        if not f["known"]:
            adds.append(entry(f, today))
            continue
        # already there: does the record contradict what it says?
        for av, block in doc["avatars"].items():
            for m in block["moments"]:
                if m["key"] != f["key"]:
                    continue
                why = []
                if m.get("evidence") != "proven":
                    why.append(f'{m.get("evidence")} -> proven')
                else:
                    why = []
                note = (m.get("note") or "").lower()
                if any(x in note for x in STALE):
                    why.append("stale note retired")
                if not m.get("sent"):
                    why.append("receipts attached")
                if why:
                    fixes.append({"avatar": av, "key": f["key"], "why": why,
                                  "find": f})
    return doc, adds, fixes, held, thin, found, median, today


def apply(doc, adds, fixes, today):
    for f in fixes:
        for m in doc["avatars"][f["avatar"]]["moments"]:
            if m["key"] != f["key"]:
                continue
            m["evidence"] = "proven"
            m["sent"] = receipts(f["find"])
            if any(x in (m.get("note") or "").lower() for x in STALE):
                m["note"] = ("Corrected " + today + " from the brand's own record: "
                             f"{len(f['find']['sends'])} send(s) name this moment. "
                             "The previous note claimed it had never been run.")
            m["mined"] = entry(f["find"], today)["mined"]
    # a public holiday belongs to every avatar, the way the file already holds them
    for e in adds:
        for block in doc["avatars"].values():
            block["moments"].append(dict(e))
    doc["generated"] = today
    return doc


def report(brand, adds, fixes, held, thin, found, median):
    L = [f"# Moments filed from the record — {brand}", "",
         f"{len(found)} moment(s) the record proves. "
         f"**{len(adds)} added · {len(fixes)} corrected · "
         f"{len(held)} held for a decision · {len(thin)} too thin to file.**", ""]
    if median:
        L += [f"Measured against a median of ${median:.4f} per recipient.", ""]
    if adds:
        L += ["## Added — filed under every avatar, graded `proven`", ""]
        for e in adds:
            got = e["mined"].get("earned", "no performance joined")
            L += [f"- **`{e['key']}`** — {got} · {e['mined']['sends']} send(s) · "
                  f"anchor `{json.dumps(e['anchor'])}`"]
            L += [f"    - {s}" for s in e["sent"][:3]]
        L.append("")
    if fixes:
        L += ["## Corrected — the file said one thing, the record says another", ""]
        for f in fixes:
            L.append(f"- **`{f['key']}`** ({f['avatar']}) — {', '.join(f['why'])}")
        L.append("")
    if held:
        L += ["## Held — the record cannot say whose these are", "",
              "A recurring brand theme, unlike a public holiday, is not "
              "automatically everybody's. Each needs one field — the avatar — "
              "and then it files itself.", ""]
        for f in held:
            L += [f"- **`{f['key']}`** — {f['when']} · {len(f['sends'])} send(s)"]
            L += [f"    - {d.isoformat()} {r.get('subject', '')}" for d, r in f["sends"][:3]]
        L.append("")
    if thin:
        L += ["## Too thin to file — one send each", "",
              f"The brand has touched these once. `proven` means a habit — "
              f"{PROVEN_SENDS} sends or more — so they wait for a second one "
              "rather than being filed as something the brand does.", ""]
        for f in thin:
            got = (f"{f['ratio']:.1f}x" if f.get("ratio") else "no performance")
            L.append(f"- **`{f['key']}`** — {got} · "
                     f"{f['sends'][0][0].isoformat()} {f['sends'][0][1].get('subject','')}")
        L.append("")
    if not (adds or fixes or held or thin):
        L += ["Nothing to file — the moments file already matches the record.", ""]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    doc, adds, fixes, held, thin, found, median, today = plan(a.brand)
    print(report(a.brand, adds, fixes, held, thin, found, median))
    if not a.write:
        print("_Nothing written. Re-run with --write to file it._")
        return
    if not (adds or fixes):
        print("nothing to write")
        return
    f = BP.brand_path(a.brand, "strategy", "moments.json", root=brand_root(a.brand).parent)
    note = propose(a.brand, f, apply(doc, adds, fixes, today),
                   report(a.brand, adds, fixes, held, thin, found, median),
                   today, len(adds), len(fixes))
    print(f"-> {rel(note)}  ({len(adds)} added, {len(fixes)} corrected; "
          f"a proposal — nothing written under brands/)")


def _sha(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def propose(brand, target, new_doc, report_text, today, n_add, n_fix):
    """The proposal folder — moments.json, report.md, run.json, PROPOSAL.md —
    under runs/marketing-calendar/<brand>/moments-<today>/. -> PROPOSAL.md.
    Writes nothing under brands/."""
    label = f"moments-{today}"
    out = month_dir(brand, label)
    brands = (WORKSPACE / "brands").resolve()
    if brands == out.resolve() or brands in out.resolve().parents:
        raise SystemExit(f"refused: {out} is under brands/")
    out.mkdir(parents=True, exist_ok=True)
    base = _sha(target)
    (out / "moments.json").write_text(json.dumps(new_doc, indent=1) + "\n")
    (out / "report.md").write_text(report_text)
    (out / "run.json").write_text(json.dumps({
        "machine": "marketing-calendar", "brand": brand, "label": label,
        "made": datetime.datetime.now().isoformat(timespec="seconds"),
        "files": {"moments.json": base}, "target": rel(target)}, indent=1) + "\n")
    t, mine = shlex.quote(rel(target)), shlex.quote(rel(out / "moments.json"))
    if base is None:
        guard, state = f"test ! -e {t}", "new"
    else:
        guard, state = f'test "$(shasum -a 256 < {t} | cut -c1-64)" = {base}', "replaces"
    lines = [
        f"# Moments proposal — {brand} · {label}", "",
        f"Made {today} by components/marketing-calendar (moments_apply.py --write).",
        "Nothing here is in brands/ yet: the calendar never writes there (K2",
        "(brands write wall), SI-22 (calendar months home)). Read report.md, copy",
        "moments.json with the command below, and commit it as your own.", "",
        "| File in this run | Target | State | Added | Corrected |",
        "|---|---|---|---|---|",
        f"| moments.json | {rel(target)} | {state} | {n_add} | {n_fix} |", "",
        "Copy, from the workspace root. It acts only while the target is still what",
        "this run saw, and prints STALE otherwise:", "", "```sh",
        f'{guard} && cp {mine} {t} '
        f'|| echo "STALE: {rel(target)} changed since this run; re-run moments_apply.py"',
        "```", "",
        f"Then commit as yourself: `git add {t} && git commit`",
    ]
    note = out / "PROPOSAL.md"
    note.write_text("\n".join(lines) + "\n")
    return note


if __name__ == "__main__":
    main()
