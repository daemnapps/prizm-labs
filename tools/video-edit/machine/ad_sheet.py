#!/usr/bin/env python3
"""ad_sheet.py — the finished ad, written down for the copy tool: who is in it, what is seen and said, its openings.
The copy tool (tools/copywriter, `copy.py --ad`) keeps a PROVEN piece of copy as its template and takes this
sheet as the nuance, so the words fit this exact ad without re-telling it (the owner, 4 Oct 2026).

    python3 ad_sheet.py <video-production-run> [--out <edit run dir>]

Reads the edit run's edit maps (the control and every hook version), decisions.json (`story.lead`, `ad_sheet`), the
production run's plan.json (hooks, cast) and brief, and writes <edit run>/the-ad.md. Nothing about one ad lives here:
a person's name, age and situation come from the brief / decisions, and an AI-made person is always marked as one.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def mmss(s: float) -> str:
    return f"{int(s // 60)}:{int(s % 60):02d}"


def sheet(vm: Path, out: Path) -> str:
    m = json.loads((out / "edit-map.json").read_text())
    dec = json.loads((out / "decisions.json").read_text()) if (out / "decisions.json").exists() else {}
    plan = json.loads((vm / "plan.json").read_text()) if (vm / "plan.json").exists() else {}
    run = json.loads((vm / "run.json").read_text()) if (vm / "run.json").exists() else {}
    me = dec.get("ad_sheet") or {}
    lead = (dec.get("story") or {}).get("lead") or m.get("lead") or ""
    made = me.get("made") or ("AI-made video: every person in it is AI-made and dramatised — not a real customer, "
                               "never a review, interview or testimonial" if run.get("format", "").startswith("ai") or
                              "video-production" in str(vm) else "")
    lines = [f"# The ad: {me.get('title') or m.get('label') or vm.name}", ""]
    if made:
        lines += [f"**How it was made:** {made}", ""]
    lines += [f"**Length:** {mmss(m['total'])} · 9:16 video · {len(m['voice'])} lines spoken"]
    if lead:
        lines += [f"**The lead (the person the story is about):** {lead}" + (f" — {me['lead_is']}" if me.get("lead_is") else "")]
    if me.get("concept"):
        lines += [f"**The concept:** {me['concept']}"]
    others = sorted({l["who"] for l in m["voice"] if l["who"] != lead})
    if others:
        lines += [f"**Others who speak:** {', '.join(others)}"]
    lines += ["", "## What the viewer sees and hears, in order", ""]
    for s in m.get("sections") or []:
        said = [l for l in m["voice"] + m.get("sounds", []) if l.get("section") == s["id"]]
        if not said:
            continue
        lines.append(f"**{mmss(s['a'])} · {s.get('name') or s['id']}**")
        for l in said:
            lines.append(f"- {l['who']}: \"{l['text']}\"")
    words = [w for w in m.get("text") or [] if w.get("kind") in ("hook headline", "option card", "card", "endcard text")]
    if words:
        lines += ["", "## Words on screen", ""]
        for w in words:
            lines.append(f"- {mmss(w['a'])} ({w['kind']}): " + " / ".join(" ".join(x.split()) for x in w["words"]))
    hooks = plan.get("hooks") or []
    if hooks:
        lines += ["", "## The openings (each is its own version of the ad, and gets its own thumbnail)", ""]
        versions = ["control"] + [f.stem[len("edit-map-"):] for f in sorted(out.glob("edit-map-*.json"))]
        for i, h in enumerate(hooks):
            v = versions[i] if i < len(versions) else "?"
            lines.append(f"- `{v}` — {h['id']}: \"{h.get('text', '')}\"")
    if me.get("notes"):
        lines += ["", "## Notes", "", me["notes"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out")
    a = ap.parse_args(argv)
    vm = Path(a.run)
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out) if a.out else HERE.parents[2] / "runs" / "video-edit" / rj["brand"] / rj["label"]
    (out / "the-ad.md").write_text(sheet(vm, out))
    print(f"ad sheet: {out / 'the-ad.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
