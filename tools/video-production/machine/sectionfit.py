#!/usr/bin/env python3
"""sectionfit.py — does each scene do its section's job? Checked before anything is made.

the owner, 2026-09-23: "you have all 15 sections on the thing but are they actually
aligned with the script of this video? … make sure it's wired to work through the
next round of production briefs." On Nova's proof run the brief labelled a surgeon's
pitch that the ad then beats "solution" (it is failed-solutions) and a receipt for a
rival's price "proof". Production already refuses a label that is not one of the 15;
this is the second half — the label must match what the words DO, because a wrong
label breaks every section swap made from it.

    python3 machine/sectionfit.py <brief.md | plan.json> [--dry-run]

One model call (prompts/stage-0c-section-fit/, the "checks" tier through
components/run-kit), fed the doctrine's own sections slice and every scene's
section, kind and words. Returns per scene {id, given, fits, should_be, why} plus any
order problems. A misfit is a STOP before the voice or a frame is paid for — named,
with the section it should be — so the brief is corrected at its source (stage 5),
never patched here. The prompt as sent and the reply are kept in <run>/section-fit/.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = next(p for p in [HERE, *HERE.parents] if (p / "components").is_dir() and (p / "brands").is_dir())
PROMPTS = HERE.parent / "prompts" / "stage-0c-section-fit"


def doctrine_ids() -> list[str]:
    d = json.loads((WS / "components/marketing-doctrine/frameworks.json").read_text())
    return [r["id"] for r in d.get("sections") or [] if isinstance(r, dict) and r.get("id")]


def plan_of(src: Path) -> dict:
    """The brief's machine block (or a plan.json) — the scenes as production reads them."""
    if src.suffix == ".json":
        return json.loads(src.read_text())
    best = None
    for body in re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", src.read_text(), flags=re.S):
        try:
            d = json.loads(body)
        except Exception:
            continue
        if isinstance(d, dict) and "scenes" in d:
            best = d
    if best is None:
        raise SystemExit(f"{src}: no scene block to check")
    return best


def scenes_text(plan: dict) -> str:
    rows = []
    for s in plan.get("scenes") or []:
        words = s.get("voice") or s.get("line") or ""
        shows = s.get("happens") or s.get("outcome") or ""
        extra = ""
        for k in ("card", "screen", "endcard", "split", "greenscreen"):
            if isinstance(s.get(k), dict):
                extra = f" · {k}: {json.dumps({x: s[k].get(x) for x in ('lines', 'offer_lines', 'cta', 'surface', 'labels') if s[k].get(x)}, ensure_ascii=False)}"
        if s.get("lines") and not extra:
            extra = f" · on-screen lines: {json.dumps(s['lines'], ensure_ascii=False)}"
        rows.append(f"- {s.get('id')} · section `{s.get('section')}` · {s.get('kind') or ('talking' if s.get('to_camera') else 'broll')}"
                    f" · SAYS: \"{words}\" · SHOWS: {shows}{extra}")
    return "\n".join(rows)


def check(plan: dict, out_dir: Path | None = None, call=None, dry_run: bool = False) -> dict:
    """{"pass": bool, "scenes": [...], "order": [...], "misfits": [...]}. `call(prompt)` is
    the model seam (tests pass a fake); the default is run-kit's `claude -p` on the
    checks tier."""
    sys.path.insert(0, str(WS / "components" / "run-kit"))
    from run_kit import prompts as P
    tpl = P.latest(PROMPTS, "stage0c-section-fit")
    piece = plan.get("piece") or {}
    sent = P.fill(Path(tpl).read_text(), {
        "sections": (WS / "components/marketing-doctrine/slices/sections.md").read_text(),
        "framework": plan.get("framework") or piece.get("framework") or "not named",
        "awareness": json.dumps(plan.get("awareness") or piece.get("awareness") or "not named", ensure_ascii=False),
        "scenes": scenes_text(plan)})
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "sent.md").write_text(sent)
    if dry_run:
        print(sent)
        return {"pass": True, "dry_run": True, "scenes": [], "order": [], "misfits": []}
    if call is None:
        from run_kit import model as M
        mdl, _ = M.pick("checks", len(sent))
        call = lambda p: M.call(p, mdl, label="section fit")
    # THREE READS, MAJORITY RULES, KEPT PER BRIEF (2026-10-07): one read flipped
    # on the same words run to run — S10, then S8, then S5 on the the athlete brief —
    # so a start could never pass twice. Like the swipe match's vote, a scene is a
    # misfit only when most reads say so, and the verdict is kept against the exact
    # prompt sent, so the same brief is judged once.
    import hashlib
    h = hashlib.sha256(sent.encode()).hexdigest()[:16]
    if out_dir and (out_dir / "result.json").exists():
        old = json.loads((out_dir / "result.json").read_text())
        if old.get("sent_hash") == h:
            return old
    reads = []
    for n in range(3):
        reply = call(sent)
        if out_dir:
            (out_dir / f"reply-{n + 1}.md").write_text(reply)
        reads.append(json.loads(reply[reply.index("{"): reply.rindex("}") + 1]))
    d = reads[0]
    ids = set(doctrine_ids())
    by_id: dict = {}
    for rd in reads:
        for r in rd.get("scenes") or []:
            by_id.setdefault(r.get("id"), []).append(r)
    misfits = []
    for sid, rs in by_id.items():
        bad = [r for r in rs if not r.get("fits") or (r.get("should_be") and r["should_be"] not in ids)]
        # a misfit needs most reads naming the SAME other section — reads that
        # agree it is off but split on what it is (S5: solution / hook /
        # root-cause) mean the scene honestly does both jobs, and the label stands
        from collections import Counter
        top = Counter(r.get("should_be") for r in bad).most_common(1)
        if top and top[0][1] * 2 > len(reads):
            bad = [r for r in bad if r.get("should_be") == top[0][0]]
            r = bad[0]
            if r.get("should_be") and r["should_be"] not in ids:
                misfits.append({**r, "why": f"(the checker named `{r['should_be']}`, which is not a doctrine section) " + str(r.get("why", ""))})
            else:
                misfits.append({**r, "votes": f"{len(bad)} of {len(reads)}"})
    bad_ids = {m.get("id") for m in misfits}
    d = {"scenes": [next((m for m in misfits if m.get("id") == s), None) if s in bad_ids
                    else next((r for r in by_id[s] if r.get("fits")), by_id[s][0]) for s in by_id],
         "order": reads[0].get("order") or []}
    # Order problems are WARNINGS: the order usually follows the swipe on purpose,
    # so they are reported, never a stop (2026-09-23).
    res = {"pass": not misfits, "scenes": d.get("scenes") or [], "order": d.get("order") or [], "misfits": misfits,
           "sent_hash": h, "reads": len(reads)}
    if out_dir:
        (out_dir / "result.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    return res


def relabel(brief: Path, res: dict) -> list[str]:
    """Fix the labels AT THE SOURCE: the brief's machine block gets each misfit
    scene's `section` set to what the check says it should be. The words, the
    order and everything else stay exactly as written; a note under the block
    records every change and why. Returns the change lines."""
    text = brief.read_text()
    fix = {m["id"]: m for m in res.get("misfits") or [] if m.get("should_be") in set(doctrine_ids())}
    if not fix:
        return []
    changes, out, pos = [], [], 0
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S):
        body = m.group(1)
        try:
            d = json.loads(body)
        except Exception:
            continue
        if not (isinstance(d, dict) and "scenes" in d):
            continue
        for sc in d["scenes"]:
            f = fix.get(sc.get("id"))
            if f and sc.get("section") != f["should_be"]:
                changes.append(f"{sc['id']}: {sc.get('section')} → {f['should_be']} — {f.get('why', '')}")
                sc["section"] = f["should_be"]
        new_body = json.dumps(d, indent=1, ensure_ascii=False)
        out.append(text[pos:m.start(1)] + new_body)
        pos = m.end(1)
    out.append(text[pos:])
    if changes:
        note = ("\n\n## Section check (automatic, " + __import__("datetime").date.today().isoformat() + ")\n\n"
                "Each scene's section was checked against what its words do (the marketing doctrine's sections). "
                "These labels were corrected; no word, scene or order changed:\n\n" + "\n".join(f"- {c}" for c in changes)
                + ("\n\nOrder notes (not changed): \n" + "\n".join(f"- {o}" for o in res.get("order") or []) if res.get("order") else "") + "\n")
        brief.write_text("".join(out) + note)
    return changes


def report(res: dict) -> None:
    for r in res.get("scenes") or []:
        tag = "FITS" if r.get("fits") else "WRONG"
        print(f"{tag:5}  {r.get('id'):>4}  {r.get('given')}" + ("" if r.get("fits") else f" → should be {r.get('should_be')}") + f" — {r.get('why')}")
    for o in res.get("order") or []:
        print(f"ORDER  (warning) {o}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = check(plan_of(Path(a.src)), Path(a.out) if a.out else None, dry_run=a.dry_run)
    report(res)
    return 0 if res["pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
