"""Make a character to the standard — from a REAL reference, with named
adjustments, every picture documented (owner, 2026-09-23: "we always need
realistic references so we can build for real … all characters need to follow
this principle when generating"; "seriously every element documented").

    python3 make_character.py <spec.json> [--out DIR] [--only NAME ...] [--dry-run]
    python3 make_character.py <spec.json> --pick-deslop b     # the other de-slop take becomes the master

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
                   "loadbearing": [...], "movement", "voice"},
     "texture": {"skin": {"file": "skin/<row>.jpg", "shows": "what the photo shows"},
                 "hair": {"file": "hair/<row>.jpg", "shows": "...", "on": "the hair/beard words"},
                 "keep": ", keeping his own <marks> (optional)"}}

TEXTURE (de-slop): `file` is a row of `runs/ai-elements/_texture-refs/index.json`
(relative to that bank) or an absolute path. A type the bank lacks is added to the
bank first (free stock macro photo, cropped to texture only, with its source).

REAL FRAMES OF THE SWIPE (2026-10-08): a spec with no `real_references` takes
the swipe frames the elements sheet attached to this person — `swipe_frames`
in the spec, or `--sheet <run>/elements.json` (matched by the spec's id) —
as references of kind "real video frame": the best frame, the frames at the
times the brief names, then one per shot, at most four, each recorded `from`
"<teardown run>/source.mp4 at <t> s (frame map <K##>, <element folder>)".

It REFUSES when there is no real reference, a reference file is missing or is
not a real kind, no adjustment is named, or no texture photos are named. Then, in
order: the master (an edit of the real references, kept as `full/master-raw.png`),
the DE-SLOP (owner ruling 2026-11-10: step 2, inside the process — the raw master
re-textured from two real texture photos, skin and hair, out of
`runs/ai-elements/_texture-refs/`; two takes in `deslop/`, take a becomes
`full/master.png` unless `--pick-deslop b`), the headshot (from the de-slopped
master, the skin photo as its texture reference), the turnaround, angles + expressions, details, light
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
    files = sorted(folder.glob("cast-sheets-v*-owner.md"),
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
    if not spec.get("variant_of"):     # a style variant IS its master's person (style_chain): its references are hers
        out += shared_with_cast(spec, base)
    # NO PRODUCT IN A CAST SHEET (owner, 2026-09-23: "you slopped an image of
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
    """NO BORROWED FACES (owner, 2026-09-23: "you used the same <presenter> frame for
    the person at the counter, you need to pick someone completely different").
    A reference may not be the same picture as another banked person's, nor a
    frame of the same video within 15 s of one — a swipe frame of a clinician's
    hands still has the lead's face in it.

    One narrow way past the 15 s half (never the identical-picture half): a
    spec that carries `same_video_ruling` — {"by", "date", "ruling", "video"}
    — naming the owner's ruling for THAT swipe only (first used: owner,
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
        if other == base or other.name.startswith(("_", ".")):
            continue
        try:                       # an unreadable folder is skipped, never a crash (review, 19 Oct)
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


# THE SWIPE'S STYLE (owner, 2026-10-09: a 3D-animated swipe came back as a
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
    if str(sid).strip().lower() == "unknown":
        # the writing could not name a style: never set, like "unfilled" (library_check passes it the same way,
        # 2026-11-20); the brief's own style sentence carries the look. A `new:` name is still refused below.
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


def texture_bank(ws: Path | None = None) -> Path:
    return (ws or _workspace()) / "runs" / "ai-elements" / "_texture-refs"


def textures(spec: dict, ws: Path | None = None) -> tuple:
    """The skin and hair texture photos the de-slop step sends, or (None, None) when the spec names none."""
    tx = spec.get("texture") or {}
    if not tx.get("skin") or not tx.get("hair"):
        return None, None
    bank = texture_bank(ws)
    return _abs(tx["skin"]["file"], bank), _abs(tx["hair"]["file"], bank)


def refuse_texture(spec: dict, ws: Path | None = None) -> list[str]:
    """De-slop is step 2 of every build (owner ruling 2026-11-10): no texture photos, no build."""
    tx = spec.get("texture") or {}
    out = []
    for k in ("skin", "hair"):
        row = tx.get(k) or {}
        if not row.get("file") or not row.get("shows"):
            out.append(f"no `texture.{k}` {{file, shows}} — de-slop is step 2 of every casting sheet; "
                       f"pick a row from {texture_bank(ws)}/index.json (add one if the type is missing)")
    if (tx.get("hair") or {}) and not tx["hair"].get("on"):
        out.append("no `texture.hair.on` — the hair or beard words the hair texture is applied to")
    s, h = textures(spec, ws)
    for f in (s, h):
        if f is not None and not f.is_file():
            out.append(f"texture photo not found: {f}")
    return out


def deslop_prompt(spec: dict, P: dict) -> str:
    tx = spec["texture"]
    return P["deslop"].format(skin=tx["skin"]["shows"], hair=tx["hair"]["shows"], hair_on=tx["hair"]["on"],
                              keep=tx.get("keep") or "")


def pick_deslop(out: Path, take: str) -> None:
    rec_f = out / "deslop" / "deslop.json"
    rec = json.loads(rec_f.read_text())
    shutil.copy2(out / "deslop" / f"take-{take}.png", out / "full" / "master.png")
    rec["picked"] = take
    rec_f.write_text(json.dumps(rec, indent=1))
    print(f"master = deslop/take-{take}.png — remake the sheets made from the other take")


def print_for(spec: dict, name: str):
    """GATE-4 (2026-11-10, no exceptions): a cast sheet is made from a filed 3D set print too. The spec names the person's
    set (`"set"`, or per sheet `"sets": {"turnaround": "<set>", ...}`: the 3D figure posed for that sheet, printed with the
    real person's frames as the reference, filed with image-production picture_sets.py put). Its kept print goes in first.
    None when the spec names no set (the door then refuses, naming the process, unless the cast lane is rolled back)."""
    s = (spec.get("sets") or {}).get(name) or spec.get("set")
    if not s:
        return None
    root = Path(__file__).resolve().parents[2] / "image-production"
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from image_production import set_gate
    kp = set_gate.kept_print(spec["brand"], set_gate.set_name(s))
    if kp is None:
        raise SystemExit(f"{name}: set {s} has no kept print on this machine (image-production picture_sets.py put)")
    return kp


def cast_set_needed(spec: dict, spec_path: Path, name: str, real: list):
    """A cast sheet with no set print: filed into the 3D print queue, then stopped (GATE-4; a rolled-back cast lane
    carries on as before)."""
    root = Path(__file__).resolve().parents[2] / "image-production"
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from image_production import set_gate
    if not set_gate.lane_on("cast"):
        return
    rid = f"cast-{spec['id']}-{name}"
    note = set_gate.queue_refusal(
        spec["brand"], f"cast sheet '{name}' of {spec['id']}: a 3D figure at the person's true build, posed for this sheet",
        name=rid, real_references=[str(r) for r in real], source="video-production make_character",
        resume={"tool": "make_character", "spec": str(spec_path), "sheet": name,
                "note": f"add \"sets\": {{\"{name}\": \"{rid}\"}} to the spec, then run make_character.py again"})
    raise SystemExit(f"{spec['id']}: sheet {name} needs its 3D set print first (GATE-4).{note}")


def _generate(d, prompt: str, refs: list[Path], out: Path, wide: bool):
    cfg0 = d.cfg
    if wide:
        d.cfg = lambda: {**cfg0(), "params": {**cfg0()["params"], "size": "1536x1024"}}
    try:
        for _ in range(15):
            try:
                return d.generate(prompt, refs, out, cast_sheet=True)   # GATE-4's written exception: a cast sheet
            except RuntimeError as e:
                if "429" not in str(e):
                    raise
                time.sleep(20)
        raise RuntimeError("still rate-limited after 5 minutes")
    finally:
        d.cfg = cfg0


def deslop(d, prompt: str, refs: list[Path], out: Path, spec: dict) -> None:
    """Step 2: two takes of the raw master re-textured from the skin and hair photos; take a becomes the master."""
    dd = out / "deslop"
    if (dd / "deslop.json").exists():
        print("kept deslop"); return
    raw, skin, hair = refs
    if not raw.exists() and (out / "full" / "master.png").exists():
        shutil.copy2(out / "full" / "master.png", raw)      # a master made before this step: keep it as the raw one
        print("  note: the existing master is kept as master-raw.png and de-slopped; remake any sheets made before")
    (dd / "refs").mkdir(parents=True, exist_ok=True)
    for f, k in ((skin, "skin"), (hair, "hair")):
        shutil.copy2(f, dd / "refs" / f"{k}-{f.name}")
    (dd / "prompt.md").write_text(f"{prompt}\n\nReferences, in order: {raw.name}, {skin.name}, {hair.name}\n")
    for t in ("a", "b"):
        if not (dd / f"take-{t}.png").exists():
            kp = print_for(spec, "deslop")
            if kp is None:
                cast_set_needed(spec, out / "spec.json", "deslop", list(refs))
            _generate(d, prompt, ([kp] if kp else []) + list(refs), dd / f"take-{t}.png", False)
    shutil.copy2(dd / "take-a.png", out / "full" / "master.png")
    tx = spec["texture"]
    (dd / "deslop.json").write_text(json.dumps({
        "_what": "Step 2 of the casting sheet: the raw master re-textured from real skin and hair photos. "
                 "The picked take is full/master.png; every sheet is made from it.",
        "made": time.strftime("%Y-%m-%d"), "raw_master": "full/master-raw.png",
        "skin": {**tx["skin"], "copy": f"deslop/refs/skin-{skin.name}"},
        "hair": {**tx["hair"], "copy": f"deslop/refs/hair-{hair.name}"},
        "keep": tx.get("keep") or "", "prompt": "deslop/prompt.md",
        "takes": ["deslop/take-a.png", "deslop/take-b.png"], "picked": "a",
        "check": "100% crop of nose, cheeks, mouth: real pores, same face, no reference person; "
                 "`--pick-deslop b` switches before the sheets are made"}, indent=1))
    print("made deslop (take a is the master)", flush=True)


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
    skin, hair = textures(spec) if not lock else (None, None)
    raw = out / "full" / "master-raw.png" if skin else master
    # REAL BODY (owner, 2026-09-23: "<she> is a lot taller, you need to index
    # her body directly from her tiktok and ig"): full-body frames of the real
    # person ride with the master on every full-body sheet, so height and
    # proportions come from footage, never from an average body.
    body = [_abs(r["file"], base) for r in spec.get("body_references") or []][:3]
    # A STYLE VARIANT (style_chain): its identity is already in the kept 3D print in the ad's style, which goes in first
    # (print_for). Real photos and the photoreal master pull the drawing back to photoreal (12 Nov: a half-stylised
    # variant in a 3D-animated ad), so the variant's sheets take only the print, the style's look picture and the master.
    if lock and spec.get("variant_of"):
        look = [_abs(r["file"], base) for r in spec.get("production_references") or [] if "look only" in str(r.get("use", ""))]
        real, prod, body = [], look, []
    J = [("master", fill(P["master"]), real + prod, raw, False)]
    # DE-SLOP, STEP 2 (owner ruling 2026-11-10): every sheet after this is made from the re-textured master
    if skin and "deslop" in P:
        J.append(("deslop", deslop_prompt(spec, P), [raw, skin, hair], master, False))
    # TRULY REAL, IN EVERY SHEET : the skin close-up is made right after the
    # master, in order, and rides as the texture reference on every sheet after it; close-ups per body part on top.
    # ONE REAL FACE : the headshot IS the macro-detail real face
    head = out / "full" / "sheets" / "headshot.png"
    tex = [head] if "headshot" in P else []
    if tex:
        # the face comes from the master only; the real frame is not sent (it let a hidden-eyed master take
        # the real person's face, 2026-11-10) — the skin photo is the texture reference instead
        # in a style lock there is no skin photo; the real frame then took the headshot over and was copied whole
        # (20 Nov 2026, a 3D-animated ad's narrator), so a locked headshot is drawn from the master alone
        J.append(("headshot", fill(P["headshot"]), [master] + ([skin] if skin else ([] if lock else real[:1])), head, False))
    for name in ("turnaround", "angles-expressions", "light-test"):
        J.append((name, fill(P[name]), [master] + (body if name == "turnaround" else []) + tex,
                  out / "full" / "sheets" / f"{name}.png", True))
    J.append(("details", fill(P["details"]), [master] + real[:1] + tex, out / "full" / "sheets" / "details.png", True))
    if "hands-closeup" in P:
        J.append(("hands-closeup", fill(P["hands-closeup"]), [out / "full" / "sheets" / "details.png"] + tex,
                  out / "full" / "sheets" / "hands-closeup.png", False))
    for lk, v in spec["looks"].items():
        # a variant's look refs are pictures of the person in another look (the photoreal or another style's): words only
        extra = [] if (lock and spec.get("variant_of")) else [_abs(r, base) for r in v.get("refs", [])]
        face = str(v.get("face") or "").strip()
        lhead = out / "full" / "sheets" / f"{lk}-headshot.png"
        if face and "headshot" in P:
            # A LOOK THAT CHANGES THE FACE (21 Nov 2026: a beard the brief shaves in S19 stayed on every later print,
            # because every board carried the one bearded headshot): its own headshot, the face words on top, and its
            # look sheet drawn from that headshot instead of the person's usual one
            J.append((f"{lk}-headshot", fill(P["headshot"]) + f"\n\nIn this look the face is: {face}. Everything else "
                      "about the face stays exactly as the master shows it.", [master], lhead, False))
        J.append((lk, fill(P["look"], outfit=v["outfit"] + (f"; the face: {face}" if face else "")),
                  [master] + extra + (body[:2] or real[:2]) + ([lhead] if face else tex),
                  out / "full" / "sheets" / f"{lk}.png", True))
    return J


def build(spec_path: Path, out: Path | None = None, only: list[str] | None = None, dry_run: bool = False,
          sheet: Path | None = None) -> Path:
    spec = adopt_swipe_frames(json.loads(spec_path.read_text()), sheet)
    spec["style_id"] = style_of(spec, sheet)
    base = spec_path.parent
    # a styled person (not photoreal): the style's own surface is the texture, so no real-skin de-slop (style_chain)
    gaps = refuse(spec, base) + ([] if style_lock(spec["style_id"]) else refuse_texture(spec))
    if gaps:
        raise SystemExit("REFUSED — " + "\n  ".join([""] + gaps))
    ws = _workspace()
    # a variant of a banked person in another style files beside its master: casting/<id>/styles/<style-id>/
    if out is None and spec.get("variant_of") and spec.get("style_id"):
        out = EP.casting_root(spec["brand"], ws) / spec["id"] / "styles" / spec["style_id"]
    out = out or EP.casting_root(spec["brand"], ws) / spec["id"]
    out.mkdir(parents=True, exist_ok=True)
    P, pfile = prompts()
    real = [_abs(r["file"], base) for r in spec["real_references"]]
    EP.new_only().refuse_pictures(real, spec["brand"])     # a new person is never built off an old one (2026-11-02)
    prod = [_abs(r["file"], base) for r in spec.get("production_references") or []]
    d = _door()
    sent = out / "sheets" / "prompts"; sent.mkdir(parents=True, exist_ok=True)
    for name, prompt, refs, dest, wide in jobs(spec, P, real, prod, out, base):
        # the de-slop rides with any sheet asked for: nothing is made from a raw master; a missing master is made first
        first = name == "master" and not (out / "full" / "master.png").exists() and not dest.exists()
        if only and name not in only and not first and not (name == "deslop" and set(only) - {"master"}):
            continue
        (sent / f"{name}.prompt.md").write_text(
            f"{prompt}\n\nReferences, in order: " + ", ".join(r.name for r in refs) + f"\nPrompt file: {pfile}\n")
        if dry_run:
            print(f"[dry run] {name}: {len(refs)} refs → {dest.relative_to(out)}")
            continue
        if name == "master" and (dest.exists() or (out / "full" / "master.png").exists()):
            print(f"kept {name}"); continue
        if name == "deslop":
            deslop(d, prompt, refs, out, spec); continue
        if dest.exists():
            print(f"kept {name}"); continue
        kp = print_for(spec, name)                 # the sheet's 3D set print goes in first (GATE-4)
        if kp is None:
            cast_set_needed(spec, spec_path, name, real)
        _generate(d, prompt, ([kp] if kp else []) + list(refs), dest, wide)
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
        "_what": "Where every picture of this person came from. Every element is made FROM A REAL REFERENCE and every element is documented (owner, 2026-09-23).",
        "element": spec["id"], "kind": "person", "made": time.strftime("%Y-%m-%d"),
        "real_references": recs, "production_references": prod_recs,
        "body_references": spec.get("body_references") or [],
        "adjustments": spec["adjustments"],
        "rights": spec.get("rights") or "Original character built from real references with the adjustments above — never a copy of the real person's face.",
        "made_with": {"model": d.cfg()["model"], "door": "components/video-production/machine/direct_openai.py",
                      "tool": "components/video-production/machine/make_character.py", "prompt_file": f"prompts/stage-0f-cast/{pfile}",
                      "master_from": "the real references (+ production references, if any), then de-slopped (deslop/deslop.json)",
                      "sheets_from": "the de-slopped master (+ real references for details and looks; the skin photo for the headshot)",
                      "prompts_as_sent": "sheets/prompts/"},
        "drive": f"Shared Assets/runs/ai-elements/{spec['brand']}/casting/{spec['id']}/ (full-size: full/master.png, full/sheets/*.png, reference/)",
        "voice": "TO MAKE — designed from the Voice line below; 3 options, owner picks by ear",
        "motion": "TO MAKE when real motion lands — performance references into motion/",
        "runs": spec.get("runs") or []}
        | ({"same_video_ruling": spec["same_video_ruling"]} if spec.get("same_video_ruling") else {}), indent=1))
    (out / "character.md").write_text(character_md(spec, recs, prod_recs))
    print(f"record written: {out}")
    return out


SHEETS = [("master.jpg", "Master — front, flat light, plain wall. The ONE identity image every generation starts from."),
          ("deslop/deslop.json", "De-slop — the raw master (`full/master-raw.png`) re-textured from real skin and hair photos; the picked take is the master."),
          ("sheets/turnaround.jpg", "Turnaround — front · three-quarter · profile · back, full body."),
          ("sheets/angles-expressions.jpg", "Angles + expressions — 5 angles; neutral, smile, 'ah', 'oo', concern, laugh (the mouth shapes lip-sync needs)."),
          ("sheets/details.jpg", "Details — hands, load-bearing skin, jewellery, at their exact age."),
          ("sheets/headshot.jpg", "Headshot — the ONE face reference, a real macro-detail photograph: pores, peach fuzz, real eyes. Keeps the face identical in every picture."),
          ("sheets/hands-closeup.jpg", "Hands close-up — macro: pores, veins, knuckle creases, nails, their own marks."),
          ("sheets/outfit-<name>.jpg", "Outfits — each stored with NO face; the face goes onto the body at picture time."),
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
- Voice id: **not made yet** — `voice.json` is written when owner picks one of three designed options by ear.
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
    ap.add_argument("--pick-deslop", choices=["a", "b"], help="make this de-slop take the master, then stop")
    a = ap.parse_args(argv)
    if a.pick_deslop:
        spec = json.loads(Path(a.spec).read_text())
        pick_deslop(Path(a.out) if a.out else EP.casting_root(spec["brand"], _workspace()) / spec["id"], a.pick_deslop)
        return 0
    build(Path(a.spec).resolve(), Path(a.out) if a.out else None, a.only, a.dry_run,
          Path(a.sheet) if a.sheet else None)
    if not a.dry_run:                                         # the elements index follows every change
        try:                                                  # (components/casting/elements_index.py)
            sys.path.append(str(Path(__file__).resolve().parents[2] / "casting")); import elements_index; elements_index.build()
        except Exception as e:  # noqa: BLE001 — an index that cannot rebuild never stops the make
            print(f"  elements index not rebuilt: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
