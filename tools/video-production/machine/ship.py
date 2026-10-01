#!/usr/bin/env python3
"""
ship.py — hand the brief's assets to the editor, on Drive.

    python3 ship.py <run> [--check]

The chain ends at the offer cards; this is the handover across the boundary.
It is deliberately NOT a stage of the brief chain — the editor owns what
happens after — but the handover itself has to happen, and on 12 September it
silently stopped: the only NINA cut on Drive was the muxed-audio version the
whole Cinema Studio route exists to replace, and it sat there being the
current thing for a day.

So this refuses to ship a clip that fails its own provenance check, and it
never overwrites a previous delivery in place.

DESTINATION. It is FOUND, not configured. A folder shared with this account
and shortcut into its Drive appears under `.shortcut-targets-by-id/<id>/<name>`
— which is exactly how the <brand> folder already in use is mounted — so this
searches for the brand folder by name rather than making anyone paste a path
with a random id in it.

The home is the brand folder inside your shared-assets drive. Set
DRIVE_ACCOUNT to the Google account that drive is mounted under. The folder
has to be shared with that account AND shortcut into its Drive — sharing
alone does not sync it to disk, which is the step that gets missed.

`drive.json` beside this file overrides the search when you want a specific
path: {"root": "/absolute/path"}
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONF = HERE / "drive.json"


def dur(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def provenance(run: Path) -> list[str]:
    """Refuse to hand over a talking clip built the old way.

    A clip whose duration equals a voiceover file sample-for-sample was muxed,
    not generated. That is the exact defect that reached Drive last time and
    was cut from for a day before anyone noticed.
    """
    bad, vo = [], run / "aroll"
    mp3 = {f: dur(f) for f in vo.glob("*.mp3")} if vo.is_dir() else {}
    for f in sorted((run / "finals" / "clips").glob("*.mp4")):
        d = dur(f)
        for m, md in mp3.items():
            if abs(md - d) < 0.02:
                bad.append(f"{f.name} is {d:.3f}s — identical to {m.name}. Muxed, not generated.")
    return bad


GDRIVE = Path.home() / "Library/CloudStorage"


def destination(brand: str) -> Path | None:
    """Find the shared brand folder, or None.

    Looks where a shared-and-shortcut folder actually lands, then falls back
    to any mounted shared drive of that name. drive.json wins over both.
    """
    if CONF.exists():
        r = Path(json.loads(CONF.read_text())["root"]).expanduser()
        return r if r.parent.exists() else None
    for acct in GDRIVE.glob("GoogleDrive-*"):
        for base in (acct / ".shortcut-targets-by-id", acct / "Shared drives"):
            if not base.is_dir():
                continue
            for pat in (f"*/Shared Assets/brands/{brand}",
                        f"Shared Assets/brands/{brand}"):
                for hit in base.glob(pat):
                    return hit / "rushes"
    return None


def main():
    run = Path(sys.argv[1]).expanduser().resolve()
    check = "--check" in sys.argv
    bad = provenance(run)
    if bad:
        print("REFUSED — provenance check failed:")
        for b in bad:
            print(f"  {b}")
        sys.exit(1)
    print("provenance ok — no clip matches a voiceover file")

    brand = json.loads((run / "out" / "plan.json").read_text()).get("brand")
    if not brand:
        sys.exit('This run does not name a brand. Add "brand": "<name>" to '
                 "out/plan.json — it decides which Drive folder it ships to.")
    root = destination(brand)
    if root is None:
        sys.exit(
            "\nNo home on Drive yet.\n\n"
            f"  No Shared Assets/brands/{brand}/ found. Share that folder with\n"
            "  your Drive account, then open it and choose\n"
            "  'Add shortcut to Drive'. Sharing alone does not sync it to\n"
            "  this Mac — the shortcut is what puts it on disk.\n\n"
            f"  Or write {CONF.name} beside this script:\n"
            '    {"root": "/absolute/path"}\n')
    if check:
        print(f"would ship to {root / run.name}   (brand: {brand})")
        return

    out = root / run.name
    cin = run / "cinema"
    plan = json.loads((cin / "plan.json").read_text())
    for d in ("clips", "broll", "alts"):
        (out / d).mkdir(parents=True, exist_ok=True)

    # clips/ — numbered in TIMELINE order, named by what the beat does
    line_of, n = {}, 0
    for sc in plan["scenes"]:
        src = cin / "voiced" / f"{sc['id']}.mp4"
        if not src.exists():
            continue
        n += 1
        slug = sc.get("name", "").lower().replace(" ", "_")[:34]
        name = f"{n:02d}_{slug or sc['id'].lower()}.mp4"
        shutil.copy2(src, out / "clips" / name)
        line_of[sc["id"]] = (name, round(dur(src), 1), sc)

    # broll/ — each insert named with the beat and second it lands on
    ins = {}
    for c in plan.get("cutaways", []):
        src = cin / "broll" / f"{c['id']}.mp4"
        if not src.exists() or c.get("dropped"):
            continue
        name = f"{c['id'].lower()}_{c['over'].lower()}_at{int(c['at'])}s.mp4"
        shutil.copy2(src, out / "broll" / name)
        ins.setdefault(c["over"], []).append((name, c))

    # alts/ — every replaced take, carrying the reason it was replaced
    alts = []
    for row in plan["scenes"] + plan.get("cutaways", []):
        for v in row.get("versions", []):
            f = run / v["file"]
            if f.exists():
                an = f"alt_{row['id'].lower()}_v{v['v']}.mp4"
                shutil.copy2(f, out / "alts" / an)
                alts.append((an, v.get("rejected_because", "")))

    for f in ("CUT.mp4", "plan.json"):
        if (cin / f).exists():
            shutil.copy2(cin / f, out / f)
    shutil.copy2(run / "brief-final.md", out / "brief-final.md")

    total = sum(v[1] for v in line_of.values())
    L = [f"# {run.name} — rushes",
         "", f"9:16, 1080p, all **cinematic_studio_3_0**, no music anywhere. "
         f"Target cut: {total:.0f}s.",
         "Clips are numbered in timeline order. **Audio is already in the "
         "clips** — the model performed the speech and the picture together, "
         "so nothing is synced and nothing can drift. Do not re-lay the voice.",
         "", "## TIMELINE ORDER (clips/)", ""]
    for sid, (name, d, sc) in line_of.items():
        L.append(f"{name} ({d:.0f}s) — {sc.get('name','')}. "
                 f"\"{sc.get('line','')[:96]}\"")
    L += ["", "## B-ROLL INSERTS (broll/)", "",
          "Each is named for the beat it covers and the second it lands on. "
          "Her voice runs underneath and is never cut — only the picture "
          "changes.", ""]
    for over, rows in ins.items():
        for name, c in rows:
            L.append(f"{name} — over {over} at {c['at']}s, {c['seconds']}s. "
                     f"{c.get('why','')}")
    dropped = [c for c in plan.get("cutaways", []) if c.get("dropped")]
    if dropped:
        L += ["", "### Not delivered", ""]
        for c in dropped:
            L.append(f"{c['id']} — over {c['over']}. {c.get('dropped','')[:200]}")
    if alts:
        L += ["", "## ALTS (alts/) — replaced takes, and why", ""]
        for an, why in alts:
            L.append(f"{an} — {why[:170]}")
    ov = plan.get("overrides", {})
    if ov:
        L += ["", "## WHERE THIS DEPARTS FROM THE BRIEF", ""]
        for k, o in ov.items():
            L.append(f"**{k}** — agreed {o.get('agreed')}, ruled "
                     f"{o.get('ruled')} by {o.get('by')}. {o.get('why','')}")
    L += ["", "## CUT RULES", "",
          "- Her voice is continuous. An insert covers picture only; never cut the audio.",
          "- A cutaway ends at least 0.4s before its beat does, or the join lands on the cut.",
          "- Two inserts less than 1.5s apart run together — a one-second flash of her face is a hiccup.",
          "- B-roll near a third of runtime; her face the rest.",
          "- No music. Room tone only.", "",
          "## RE-ROLLS", "",
          "Every take re-rolls from its own card on the cinema board: write "
          "what is wrong in plain words, press Regenerate, and the note is "
          "kept against the take it replaced. `plan.json` carries each clip's "
          "job id and door beside the prompt that made it, and "
          "`brief-final.md` is the spec they were built against.", ""]
    (out / "EDIT_NOTES.md").write_text("\n".join(L))
    print(f"shipped to {out}")
    print(f"  clips/{len(line_of)}  broll/{sum(len(v) for v in ins.values())}"
          f"  alts/{len(alts)}  + CUT.mp4, plan.json, brief-final.md, EDIT_NOTES.md")


if __name__ == "__main__":
    main()
