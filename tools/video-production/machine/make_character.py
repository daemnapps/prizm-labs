"""Make a character to the standard — from a REAL reference, with named
adjustments, every picture documented (the owner, 2026-09-23: "we always need
realistic references so we can build for real … all characters need to follow
this principle when generating"; "seriously every element documented").

    python3 make_character.py <spec.json> [--out DIR] [--only NAME ...] [--dry-run]

The spec says who the person is and what they were built from:

    {"id": "expert1", "brand": "<brand>",
     "who": "the identity words — the person AFTER the adjustments",
     "adjustments": ["what we change from the real person", ...],
     "real_references": [{"file": "/abs/or/relative.jpg", "kind": "real photo",
                          "from": "where it came from (URL, swipe, post)",
                          "use": "what it is the reference for"}],
     "production_references": [...optional, e.g. approved frames of this person],
     "base": "the neutral sheet outfit",
     "details": "the four detail panels",
     "looks": {"look-1-x": {"outfit": "...", "from": "...", "continuity": "...",
                            "refs": ["extra real refs for this outfit"]}},
     "character": {"title", "why", "role", "age", "lane", "sub",
                   "loadbearing": [...], "movement", "voice"}}

REAL FRAMES OF THE SWIPE (2026-10-08): a spec with no `real_references` takes
the swipe frames the elements sheet attached to this person — `swipe_frames`
in the spec, or `--sheet <run>/elements.json` (matched by the spec's id) —
as references of kind "real video frame": the best frame, the frames at the
times the brief names, then one per shot, at most four, each recorded `from`
"<teardown run>/source.mp4 at <t> s (frame map <K##>, <element folder>)".

It REFUSES when there is no real reference, a reference file is missing or is
not a real kind, or no adjustment is named. Then, in order: the master (an edit
of the real references), the turnaround, angles + expressions, details, light
test and one sheet per look (edits of the master), a colour key sampled from
the pictures, and the record — character.md, looks.json, provenance.json, the
prompts as sent, the real references copied in. Output goes to --out (default
`runs/ai-elements/<brand>/casting/<id>/` — the person's home, element_paths.py); the
full-size pictures land in its `full/` (kept out of git) and are mirrored to the
same path under `Shared Assets/runs/` on the Drive.

Prompts: `prompts/stage-0f-cast/`, newest version wins. Image door:
`direct_openai.py`. Rate-limited calls wait and retry.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
import importlib.util as _ilu
_sp = _ilu.spec_from_file_location("vm_element_paths", Path(__file__).resolve().parent / "element_paths.py")
EP = _ilu.module_from_spec(_sp); _sp.loader.exec_module(EP)


def _door():
    """The image door, loaded by file — never HERE first on sys.path (it has a platform.py)."""
    import importlib.util as ilu
    sp = ilu.spec_from_file_location("vm_direct_openai", HERE / "direct_openai.py")
    m = ilu.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def _workspace() -> Path:
    p = HERE
    while p != p.parent:
        if (p / "brands").is_dir() and (p / "components").is_dir():
            return p
        p = p.parent
    raise SystemExit("no workspace root above this file")


def prompts() -> tuple[dict, str]:
    folder = COMPONENT / "prompts" / "stage-0f-cast"
    files = sorted(folder.glob("cast-sheets-v*-damon.md"),
                   key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    f = files[-1]
    secs, cur = {}, None
    for line in f.read_text().splitlines():
        m = re.match(r"^## (\S+)\s*$", line)
        if m:
            cur = m.group(1); secs[cur] = []
        elif cur:
            secs[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in secs.items()}, f.name


def standard() -> dict:
    return json.loads((COMPONENT / "elements-standard.json").read_text())


def refuse(spec: dict, base: Path) -> list[str]:
    """The principle, enforced before a single call is paid for."""
    kinds = standard()["provenance_rules"]["real_kinds"]
    out = []
    refs = spec.get("real_references") or []
    if not refs:
        out.append("no real reference — every character starts from a real photo or real video frame")
    for r in refs:
        f = Path(r.get("file", ""))
        f = f if f.is_absolute() else base / f
        if not f.is_file():
            out.append(f"real reference not found: {r.get('file')}")
        if r.get("kind") not in kinds:
            out.append(f"{r.get('file')}: kind `{r.get('kind')}` is not a real source ({', '.join(kinds)})")
        if not r.get("from"):
            out.append(f"{r.get('file')}: no `from` — where it came from must be recorded")
    if not spec.get("adjustments"):
        out.append("no adjustments named — our characters are built FROM a real person and made our own, never a copy")
    out += shared_with_cast(spec, base)
    # NO PRODUCT IN A CAST SHEET (the owner, 2026-09-23: "you slopped an image of
    # product with <her> holding it. that's not our bottle"). A product is
    # never drawn from words; it enters a frame only from its real packshot, at
    # production. Cast sheets carry people, clothes and skin — nothing sold.
    words = re.compile(r"\b(tube|bottle|jar|packshot|product|serum|lotion|skincare box|pump|scrub tube|cream tube)\b", re.I)
    for k in ("who", "base", "details"):
        m = words.search(spec.get(k) or "")
        if m:
            out.append(f"`{k}` mentions a product (\"{m.group(0)}\") — cast sheets never draw a product; it enters frames only from the real packshot")
    for lk, v in (spec.get("looks") or {}).items():
        m = words.search(v.get("outfit") or "")
        if m:
            out.append(f"look `{lk}` mentions a product (\"{m.group(0)}\") — remove it")
    for k in ("id", "brand", "who", "base", "details", "looks", "character"):
        if not spec.get(k):
            out.append(f"spec has no `{k}`")
    return out


def shared_with_cast(spec: dict, base: Path) -> list[str]:
    """NO BORROWED FACES (the owner, 2026-09-23: "you used the same <presenter> frame for
    the person at the counter, you need to pick someone completely different").
    A reference may not be the same picture as another banked person's, nor a
    frame of the same video within 15 s of one — a swipe frame of a clinician's
    hands still has the lead's face in it.

    One narrow way past the 15 s half (never the identical-picture half): a
    spec that carries `same_video_ruling` — {"by", "date", "ruling", "video"}
    — naming the owner's ruling for THAT swipe only (first used: the owner,
    2026-10-08, sq-01 × Dbmik5RNWQV, where all three people share 12.6 s).
    The ruling is copied into provenance.json; the default is unchanged."""
    import hashlib
    out = []
    ruling = spec.get("same_video_ruling") or {}
    lifted = bool(ruling.get("by") and ruling.get("date") and ruling.get("ruling") and ruling.get("video"))
    cast = base.parent
    mine = {}
    for r in spec.get("real_references") or []:
        f = _abs(r.get("file", ""), base)
        if f.is_file():
            mine[hashlib.sha256(f.read_bytes()).hexdigest()] = r
    def stamp(r):
        src = re.search(r"(source\.mp4|/video/\d+|\.mp4)", r.get("from", ""))
        at = re.search(r"at ([\d.]+) s", r.get("from", ""))
        return (src.group(0) if src else None), (float(at.group(1)) if at else -999.0)
    for other in sorted(cast.iterdir()) if cast.is_dir() else []:
        if other == base or other.name.startswith("_") or not (other / "provenance.json").is_file():
            continue
        try:
            prov = json.loads((other / "provenance.json").read_text())
        except Exception:
            continue
        for r in prov.get("real_references") or []:
            f = other / r.get("file", "")
            if f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest() in mine:
                out.append(f"reference {r['file']} is also {other.name}'s — a new person never shares a picture with a banked one")
            (src, at) = stamp(r)
            for m in mine.values():
                (s2, a2) = stamp(m)
                if src and s2 == src and at >= 0 and a2 >= 0 and abs(at - a2) <= 15 and \
                        r.get("from", "").split(" at ")[0] == m.get("from", "").split(" at ")[0] and \
                        not (lifted and ruling["video"] in m.get("from", "")):
                    out.append(f"{m['file']} is a frame of the same video within 15 s of {other.name}'s reference — their face is likely in it")
    return out


SWIPE_FRAME_REFS = 4


def adopt_swipe_frames(spec: dict, sheet: Path | None = None, ws: Path | None = None) -> dict:
    """A spec with no real reference takes the sheet's swipe frames as "real
    video frame" references (see the docstring). Returns the spec, unchanged
    when it already names references or no swipe frames are found."""
    if spec.get("real_references"):
        return spec
    sf = spec.get("swipe_frames")
    if not sf and sheet and Path(sheet).is_file():
        body = json.loads(Path(sheet).read_text())
        sid = str(spec.get("id") or "")
        it = next((i for i in body.get("items") or [] if i.get("swipe_frames") and
                   sid in (i.get("bank_id"), i.get("id"), re.sub(r"[^a-z0-9]+", "-", str(i.get("id", "")).lower()).strip("-"))), None)
        sf = (it or {}).get("swipe_frames")
    if not sf:
        return spec
    ws = ws or _workspace()
    picks = []
    for p in [sf.get("best")] + list(sf.get("at_times") or []) + list(sf.get("crops") or []):
        if p and p.get("file") and p["file"] not in [x["file"] for x in picks]:
            picks.append(p)
    refs = [{"file": str(_abs(p["file"], ws)), "kind": "real video frame",
             "from": f"{sf.get('run')}/source.mp4 at {float(p.get('t') or 0):.2f} s "
                     f"(frame map {p.get('shot')}, {sf.get('element')})",
             "use": f"the swipe's {sf.get('name')} — who we build from, then adjust"}
            for p in picks[:SWIPE_FRAME_REFS]]
    return {**spec, "real_references": refs, "real_references_from": "swipe_frames"}


# THE SWIPE'S STYLE (the owner, 2026-10-09: a 3D-animated swipe came back as a
# photoreal cast — "the creative format itself is supposed to look like Pixar
# … this should be in the process … so we're not wasting time on credits").
# A spec (or the elements sheet it was made from) names a `style_id` from
# styles/bank.json; that row's formula replaces the photoreal realism line and
# leads every prompt. No style, or the real-footage look, keeps the realism line.
STYLES = COMPONENT / "styles" / "bank.json"
REAL_LOOKS = ("phone-ugc",)


def style_of(spec: dict, sheet=None):
    sid = spec.get("style_id")
    if not sid and sheet and Path(sheet).is_file():
        sid = (json.loads(Path(sheet).read_text()) or {}).get("style_id")
    return sid or None


def style_lock(sid):
    """The STYLE LOCK line for a style id, or None for no style / real footage.
    A style the bank does not hold is refused by name."""
    if not sid or sid in REAL_LOOKS:
        return None
    rows = (json.loads(STYLES.read_text()) or {}).get("styles") or []
    row = next((r for r in rows if r.get("id") == sid), None)
    if not row:
        raise SystemExit(f"style {sid!r} is not a row of styles/bank.json — name a real style id, or add the row "
                         f"(written from the swipe's frames) before making anything")
    return (f"STYLE LOCK — {row['formula']}. Every picture is made in this style, never photoreal; who the person is, "
            f"what they wear and every skin mark still come from the references.")


def _abs(p: str, base: Path) -> Path:
    q = Path(p)
    return q if q.is_absolute() else base / q


def _generate(d, prompt: str, refs: list[Path], out: Path, wide: bool):
    cfg0 = d.cfg
    if wide:
        d.cfg = lambda: {**cfg0(), "params": {**cfg0()["params"], "size": "1536x1024"}}
    try:
        for _ in range(15):
            try:
                return d.generate(prompt, refs, out)
            except RuntimeError as e:
                if "429" not in str(e):
                    raise
                time.sleep(20)
        raise RuntimeError("still rate-limited after 5 minutes")
    finally:
        d.cfg = cfg0


def colour_key(pictures: list[Path], out: Path, title: str) -> dict:
    from PIL import Image, ImageDraw, ImageFont
    rows = []
    for p in pictures:
        im = Image.open(p).convert("RGB"); im.thumbnail((300, 300))
        q = im.quantize(8)
        pal = q.getpalette()
        cols = []
        for _, i in sorted(q.getcolors(), reverse=True):
            c = tuple(pal[i * 3:i * 3 + 3])
            if sum(c) < 705:                      # the white backdrop is not a colour of the person
                cols.append(c)
        rows.append((p.stem, cols[:6]))
    try:
        fb = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
        fs = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    except OSError:
        fb = fs = ImageFont.load_default()
    img = Image.new("RGB", (1400, 90 + 110 * len(rows)), "white"); dr = ImageDraw.Draw(img)
    dr.text((24, 24), f"COLOUR KEY — {title}", fill="black", font=fb)
    for r, (name, cols) in enumerate(rows):
        y = 80 + r * 110; dr.text((24, y + 35), name, fill="black", font=fb)
        for i, c in enumerate(cols):
            x = 380 + i * 165; dr.rectangle([x, y, x + 150, y + 80], fill=c)
            dr.text((x, y + 84), "#%02x%02x%02x" % c, fill="black", font=fs)
    img.save(out)
    return {n: ["#%02x%02x%02x" % c for c in cols] for n, cols in rows}


def small(src: Path, dst: Path, w: int = 1600):
    from PIL import Image
    im = Image.open(src).convert("RGB"); im.thumbnail((w, w))
    dst.parent.mkdir(parents=True, exist_ok=True); im.save(dst, quality=85)


def jobs(spec: dict, P: dict, real: list[Path], prod: list[Path], out: Path, base: Path) -> list[tuple]:
    lock = style_lock(spec.get("style_id"))
    fill = lambda t, **kw: (lock + "\n\n" if lock else "") + t.format(
        who=spec["who"], adjustments="; ".join(spec["adjustments"]), base=spec["base"], details=spec["details"],
        real=lock or P["realism"], outfit=kw.get("outfit", ""))
    master = out / "full" / "master.png"
    # REAL BODY (the owner, 2026-09-23: "<she> is a lot taller, you need to index
    # her body directly from her tiktok and ig"): full-body frames of the real
    # person ride with the master on every full-body sheet, so height and
    # proportions come from footage, never from an average body.
    body = [_abs(r["file"], base) for r in spec.get("body_references") or []][:3]
    J = [("master", fill(P["master"]), real + prod, master, False)]
    for name in ("turnaround", "angles-expressions", "light-test"):
        J.append((name, fill(P[name]), [master] + (body if name == "turnaround" else []),
                  out / "full" / "sheets" / f"{name}.png", True))
    J.append(("details", fill(P["details"]), [master] + real[:1], out / "full" / "sheets" / "details.png", True))
    for lk, v in spec["looks"].items():
        extra = [_abs(r, base) for r in v.get("refs", [])]
        J.append((lk, fill(P["look"], outfit=v["outfit"]), [master] + extra + (body[:2] or real[:2]),
                  out / "full" / "sheets" / f"{lk}.png", True))
    return J


def build(spec_path: Path, out: Path | None = None, only: list[str] | None = None, dry_run: bool = False,
          sheet: Path | None = None) -> Path:
    spec = adopt_swipe_frames(json.loads(spec_path.read_text()), sheet)
    spec["style_id"] = style_of(spec, sheet)
    base = spec_path.parent
    gaps = refuse(spec, base)
    if gaps:
        raise SystemExit("REFUSED — " + "\n  ".join([""] + gaps))
    ws = _workspace()
    out = out or EP.casting_root(spec["brand"], ws) / spec["id"]
    out.mkdir(parents=True, exist_ok=True)
    P, pfile = prompts()
    real = [_abs(r["file"], base) for r in spec["real_references"]]
    prod = [_abs(r["file"], base) for r in spec.get("production_references") or []]
    d = _door()
    sent = out / "sheets" / "prompts"; sent.mkdir(parents=True, exist_ok=True)
    for name, prompt, refs, dest, wide in jobs(spec, P, real, prod, out, base):
        if only and name not in only:
            continue
        (sent / f"{name}.prompt.md").write_text(
            f"{prompt}\n\nReferences, in order: " + ", ".join(r.name for r in refs) + f"\nPrompt file: {pfile}\n")
        if dry_run:
            print(f"[dry run] {name}: {len(refs)} refs → {dest.relative_to(out)}")
            continue
        if dest.exists():
            print(f"kept {name}"); continue
        _generate(d, prompt, refs, dest, wide)
        print(f"made {name}", flush=True)
    if dry_run or only:
        return out     # a partial run (--only) writes no record — the record is of a whole set
    (out / "full" / "sheets").mkdir(parents=True, exist_ok=True)
    # the record — small copies for the repo, the full size stays in full/ for the Drive
    small(out / "full" / "master.png", out / "master.jpg", 1024)
    for p in sorted((out / "full" / "sheets").glob("*.png")):
        small(p, out / "sheets" / f"{p.stem}.jpg")
    ck = colour_key([out / "full" / "master.png"] + sorted((out / "full" / "sheets").glob("look-*.png")),
                    out / "full" / "sheets" / "colour-key.png", spec["id"])
    small(out / "full" / "sheets" / "colour-key.png", out / "sheets" / "colour-key.jpg")
    (out / "sheets" / "colour-key.json").write_text(json.dumps({"colour_key": ck}, indent=1))
    (out / "reference").mkdir(exist_ok=True)
    recs = []
    for r, f in zip(spec["real_references"], real):
        dst = out / "reference" / f.name
        if f.resolve() != dst.resolve():   # the reference may already sit in reference/
            shutil.copy2(f, dst)
        recs.append({**r, "file": f"reference/{f.name}"})
    prod_recs = []
    for r, f in zip(spec.get("production_references") or [], prod):
        dst = out / "reference" / f.name
        if f.resolve() != dst.resolve():   # the reference may already sit in reference/
            shutil.copy2(f, dst)
        prod_recs.append({**r, "file": f"reference/{f.name}"})
    (out / "looks.json").write_text(json.dumps({
        "_what": f"The looks a brief may name for {spec['id']}. A scene's `looks` names one of these ids; anything else is refused by the elements check.",
        "looks": {k: {kk: vv for kk, vv in v.items() if kk != "refs"} | {"sheet": f"sheets/{k}.jpg"}
                  for k, v in spec["looks"].items()}}, indent=1))
    ch = spec["character"]
    (out / "provenance.json").write_text(json.dumps({
        "_what": "Where every picture of this person came from. Every element is made FROM A REAL REFERENCE and every element is documented (the owner, 2026-09-23).",
        "element": spec["id"], "kind": "person", "made": time.strftime("%Y-%m-%d"),
        "real_references": recs, "production_references": prod_recs,
        "body_references": spec.get("body_references") or [],
        "adjustments": spec["adjustments"],
        "rights": spec.get("rights") or "Original character built from real references with the adjustments above — never a copy of the real person's face.",
        "made_with": {"model": d.cfg()["model"], "door": "tools/video-production/machine/direct_openai.py",
                      "tool": "tools/video-production/machine/make_character.py", "prompt_file": f"prompts/stage-0f-cast/{pfile}",
                      "master_from": "the real references (+ production references, if any)",
                      "sheets_from": "the master (+ real references for details and looks)",
                      "prompts_as_sent": "sheets/prompts/"},
        "drive": f"Shared Assets/runs/ai-elements/{spec['brand']}/casting/{spec['id']}/ (full-size: full/master.png, full/sheets/*.png, reference/)",
        "voice": "TO MAKE — designed from the Voice line below; 3 options, the owner picks by ear",
        "motion": "TO MAKE when real motion lands — performance references into motion/",
        "runs": spec.get("runs") or []}
        | ({"same_video_ruling": spec["same_video_ruling"]} if spec.get("same_video_ruling") else {}), indent=1))
    (out / "character.md").write_text(character_md(spec, recs, prod_recs))
    print(f"record written: {out}")
    return out


SHEETS = [("master.jpg", "Master — front, flat light, plain wall. The ONE identity image every generation starts from."),
          ("sheets/turnaround.jpg", "Turnaround — front · three-quarter · profile · back, full body."),
          ("sheets/angles-expressions.jpg", "Angles + expressions — 5 angles; neutral, smile, 'ah', 'oo', concern, laugh (the mouth shapes lip-sync needs)."),
          ("sheets/details.jpg", "Details — hands, load-bearing skin, jewellery, at their exact age."),
          ("sheets/light-test.jpg", "Light test — daylight · warm indoor · overcast. Same face, only the light changes."),
          ("sheets/colour-key.jpg", "Colour key — swatches sampled from the master and each look (`sheets/colour-key.json`).")]


def character_md(spec: dict, recs: list, prod: list) -> str:
    c = spec["character"]
    looks = "\n".join(f"- **`{k}`** — {v['outfit']}. *From:* {v.get('from','')}. *Continuity:* {v.get('continuity','')}. "
                      f"Sheet: [sheets/{k}.jpg](sheets/{k}.jpg)" for k, v in spec["looks"].items())
    refs = "\n".join(f"- [{r['file']}]({r['file']}) — {r['kind']} · {r['from']}" + (f" · for {r['use']}" if r.get("use") else "")
                     for r in recs + prod)
    return f"""# {c['title']}

{c['why']}

## Basics
- Status: active (banked {time.strftime('%Y-%m-%d')})
- Role: {c['role']}
- Age: {c['age']}
- Avatar link: lane `{c.get('lane','')}`{(', sub `' + c['sub'] + '`') if c.get('sub') else ''}

## Built from a real reference, then adjusted
Real references (what this person was built from):
{refs}

Adjustments (what makes them ours, not the real person):
""" + "\n".join(f"- {a}" for a in spec["adjustments"]) + f"""

## Identity block (paste-ready — runs paste THIS, never re-describe)
> {spec['who']}

## Load-bearing details
""" + "\n".join(f"- {x}" for x in c.get("loadbearing", [])) + f"""

## Looks (a brief names one per scene, by id — `looks.json`)
{looks}

Neutral sheet outfit (turnaround, angles, light test only): {spec['base']}.

## Movement (how they move — the brief for any motion or performance reference)
{c.get('movement','')}

## Voice
- Persona: {c.get('voice','')}
- Voice id: **not made yet** — `voice.json` is written when the owner picks one of three designed options by ear.
- Rule: a character is only ever read in their own voice.

## Masters and sheets (repo: small copies · Drive: full size)
""" + "\n".join(f"- [{f}]({f}) — {w}" for f, w in SHEETS) + f"""

Every picture's exact prompt: [sheets/prompts/](sheets/prompts/). Full size on the Drive: `Shared Assets/runs/ai-elements/{spec['brand']}/casting/{spec['id']}/`.

## Swap record
- Formats run: —
- Results: — (grows with every run)

## Provenance
- Full record: [provenance.json](provenance.json)
""" + "".join(f"- {r}\n" for r in spec.get("runs") or [])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sheet", help="the run's elements.json — its swipe_frames stand in for missing real_references")
    a = ap.parse_args(argv)
    build(Path(a.spec).resolve(), Path(a.out) if a.out else None, a.only, a.dry_run,
          Path(a.sheet) if a.sheet else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
