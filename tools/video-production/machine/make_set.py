"""Make a SETTING to the standard — from a REAL reference, adjusted, every
plate documented (the owner, 2026-09-23). The twin of make_character.py.

    python3 make_set.py <spec.json> [--out DIR] [--only NAME ...] [--dry-run]

    {"id": "kitchen-table", "brand": "<brand>",
     "place": "the place AFTER the adjustments",
     "adjustments": ["what we change from the real place", ...],
     "time": "late morning", "light": "window on the left, soft",
     "dressing": ["what must be in it", ...],
     "resets": "what goes back between takes", "room_tone": "what it sounds like",
     "angles": {"angle-a-to-camera": "where the to-camera shot stands",
                "angle-b-cutaway": "where the cutaway stands"},
     "real_references": [{"file", "kind", "from", "use"}], "rights": "…"}

With no `real_references`, the swipe frames the elements sheet attached to
this set (`swipe_frames` in the spec, or `--sheet <run>/elements.json`) are
taken as "real video frame" references — make_character.adopt_swipe_frames.

Refuses with no real reference, a non-real kind, no adjustments, or fewer
than two angles. Writes plates/wide + plates/angle-*, set.md,
provenance.json, the prompts as sent and the references, into --out (default
runs/ai-elements/<brand>/sets/<id>/ — element_paths.py); full-size plates in
its full/ (out of git), mirrored under Shared Assets/runs/ on the Drive. Prompts: prompts/stage-0g-sets/, newest wins.
"""
from __future__ import annotations

import argparse, json, re, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
import importlib.util as _ilu
_sp = _ilu.spec_from_file_location("vm_make_character", HERE / "make_character.py")
MC = _ilu.module_from_spec(_sp); _sp.loader.exec_module(MC)


PERSONISH = re.compile(r"\b(speaker|presenter|person|people|she|he|her|his|him|woman|man|creator|face|hand|hands)\b", re.I)


def _person_in(img) -> str:
    """'' when the plate holds no person; otherwise what was seen. Uses the
    video teardown's listening/looking model on the picture itself."""
    try:
        sp = _ilu.spec_from_file_location("vt_deepen", HERE.parents[1] / "video-teardown" / "machine" / "deepen.py")
        dp = _ilu.module_from_spec(sp); sp.loader.exec_module(dp)
        a = dp.ask(str(img), "Is there any person in this picture — a face, a body, hands, or a person reflected in glass? "
                             "Answer YES or NO, then up to 6 words saying what you see.").strip()
    except Exception as e:
        print(f"  (the people check could not run: {e}) — look at this plate yourself", flush=True)
        return ""
    return a if a.upper().startswith("YES") else ""


def prompts() -> tuple[dict, str]:
    folder = COMPONENT / "prompts" / "stage-0g-sets"
    f = sorted(folder.glob("set-plates-v*-damon.md"), key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))[-1]
    secs, cur = {}, None
    for line in f.read_text().splitlines():
        m = re.match(r"^## (\S+)\s*$", line)
        if m:
            cur = m.group(1); secs[cur] = []
        elif cur:
            secs[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in secs.items()}, f.name


def refuse(spec: dict, base: Path) -> list[str]:
    kinds = MC.standard()["provenance_rules"]["real_kinds"]
    out = []
    if not spec.get("real_references"):
        out.append("no real reference — every place starts from a real photo or real video frame")
    for r in spec.get("real_references") or []:
        f = MC._abs(r.get("file", ""), base)
        if not f.is_file():
            out.append(f"real reference not found: {r.get('file')}")
        if r.get("kind") not in kinds:
            out.append(f"{r.get('file')}: kind `{r.get('kind')}` is not a real source")
        if not r.get("from"):
            out.append(f"{r.get('file')}: no `from`")
    if not spec.get("adjustments"):
        out.append("no adjustments named — our places are built FROM a real place and made our own")
    if len(spec.get("angles") or {}) < 2:
        out.append("fewer than two camera angles — the standard needs the to-camera and the cutaway position")
    for k in ("id", "brand", "place", "time", "light", "dressing"):
        if not spec.get(k):
            out.append(f"spec has no `{k}`")
    return out


def build(spec_path: Path, out: Path | None = None, only=None, dry_run=False, sheet=None) -> Path:
    spec = MC.adopt_swipe_frames(json.loads(spec_path.read_text()), sheet); base = spec_path.parent
    spec["style_id"] = MC.style_of(spec, sheet)
    lock = MC.style_lock(spec["style_id"])          # the swipe's style leads every plate (2026-10-09)
    gaps = refuse(spec, base)
    if gaps:
        raise SystemExit("REFUSED — " + "\n  ".join([""] + gaps))
    out = out or MC.EP.elements_home(spec["brand"], "sets", spec["id"])
    P, pfile = prompts()
    real = [MC._abs(r["file"], base) for r in spec["real_references"]]
    fill = lambda t, angle="": (lock + "\n\n" if lock else "") + t.format(
        place=spec["place"], adjustments="; ".join(spec["adjustments"]), time=spec["time"], light=spec["light"],
        dressing="; ".join(spec["dressing"]), angle=angle, real=lock or P["realism"])
    wide = out / "full" / "plates" / "wide.png"
    jobs = [("wide", fill(P["wide"]), real, wide)]
    for name, where in spec["angles"].items():
        if PERSONISH.search(where):
            raise SystemExit(f"angle {name!r} names a person ({PERSONISH.search(where).group(0)!r}) — describe the "
                             f"camera position only (a plate is an empty place; naming someone draws them in)")
        n = name if name.startswith("angle-") else f"angle-{name}"
        jobs.append((n, fill(P["angle"], where), [wide], out / "full" / "plates" / f"{n}.png"))
    d = MC._door()
    sent = out / "plates" / "prompts"; sent.mkdir(parents=True, exist_ok=True)
    for name, prompt, refs, dest in jobs:
        if only and name not in only:
            continue
        (sent / f"{name}.prompt.md").write_text(f"{prompt}\n\nReferences, in order: " + ", ".join(r.name for r in refs) + f"\nPrompt file: {pfile}\n")
        if dry_run:
            print(f"[dry run] {name}: {len(refs)} refs"); continue
        if dest.exists():
            print(f"kept {name}"); continue
        MC._generate(d, prompt, refs, dest, wide=False)
        # A PLATE IS EMPTY (2026-10-01): the sidewalk's selfie plate came back
        # with a stand-in woman in it, despite "no people" in the prompt. Every
        # plate is looked at; one with a person is made again once, then refused.
        for attempt in (1, 2):
            who = _person_in(dest)
            if not who:
                break
            if attempt == 2:
                dest.unlink(missing_ok=True)
                raise SystemExit(f"{name}: a person is in the plate twice ({who}) — refused; nothing kept")
            print(f"  {name}: a person is in the plate ({who}) — made again", flush=True)
            dest.unlink(missing_ok=True)
            MC._generate(d, prompt, refs, dest, wide=False)
        print(f"made {name}", flush=True)
    if dry_run or only:
        return out
    for p in sorted((out / "full" / "plates").glob("*.png")):
        MC.small(p, out / "plates" / f"{p.stem}.jpg")
    (out / "reference").mkdir(exist_ok=True)
    recs = []
    for r, f in zip(spec["real_references"], real):
        if f.resolve() != (out / "reference" / f.name).resolve():   # the reference may already sit in reference/
            shutil.copy2(f, out / "reference" / f.name)
        recs.append({**r, "file": f"reference/{f.name}"})
    (out / "provenance.json").write_text(json.dumps({
        "_what": "Where every plate of this place came from — made FROM A REAL REFERENCE, documented (the owner, 2026-09-23).",
        "element": spec["id"], "kind": "setting", "made": time.strftime("%Y-%m-%d"),
        "real_references": recs, "adjustments": spec["adjustments"],
        "rights": spec.get("rights") or "An original place built from real references with the adjustments above.",
        "made_with": {"model": d.cfg()["model"], "door": "tools/video-production/machine/direct_openai.py",
                      "tool": "tools/video-production/machine/make_set.py", "prompt_file": f"prompts/stage-0g-sets/{pfile}",
                      "wide_from": "the real references", "angles_from": "the wide plate", "prompts_as_sent": "plates/prompts/"},
        "drive": f"Shared Assets/runs/ai-elements/{spec['brand']}/sets/{spec['id']}/ (full-size plates in full/, reference/)",
        "runs": spec.get("runs") or []}, indent=1))
    refs_md = "\n".join(f"- [{r['file']}]({r['file']}) — {r['kind']} · {r['from']}" + (f" · for {r['use']}" if r.get('use') else "") for r in recs)
    (out / "set.md").write_text(f"""# {spec.get('title') or spec['id']}

{spec['place']}

## Built from a real reference, then adjusted
{refs_md}

Adjustments:
""" + "\n".join(f"- {a}" for a in spec["adjustments"]) + f"""

## Shooting facts
- Time of day: {spec['time']}
- Light: {spec['light']}
- Dressing (must be in frame where it shows): {'; '.join(spec['dressing'])}
- Resets between takes: {spec.get('resets','—')}
- Room tone: {spec.get('room_tone','—')}

## Plates (repo: small copies · Drive: full size) — empty, no people, no readable words
- [plates/wide.jpg](plates/wide.jpg) — establishing
""" + "\n".join(f"- [plates/{(n if n.startswith('angle-') else 'angle-'+n)}.jpg](plates/{(n if n.startswith('angle-') else 'angle-'+n)}.jpg) — {w}" for n, w in spec["angles"].items()) + """

Every plate's exact prompt: [plates/prompts/](plates/prompts/). Full record: [provenance.json](provenance.json)
""")
    print(f"record written: {out}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec"); ap.add_argument("--out"); ap.add_argument("--only", nargs="*"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sheet", help="the run's elements.json — its swipe_frames stand in for missing real_references")
    a = ap.parse_args(argv)
    build(Path(a.spec).resolve(), Path(a.out) if a.out else None, a.only, a.dry_run, Path(a.sheet) if a.sheet else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
