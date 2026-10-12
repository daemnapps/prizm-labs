"""The banked elements become the frames' references (the owner, 2026-09-23: every
element built, documented and approved — now the frames must actually USE them).

Before any still is made, each scene's FIRST FRAME gets, in this order and at
most five (the image door's per-minute input limit): the master of every
person in the scene · the brand's real packshot when the product is in frame ·
THE SWIPE FRAME it recreates, as a COMPOSITION reference · the set plate
nearest the scene's camera · the look sheet each wears in that scene · the
props.

THE SWIPE FRAME (the owner, 2026-10-08: "when we get to the frame generation … we
can actually work with the real frames … use those as the references"): the
swipe shot the scene copies (the item's own `copies_swipe_shot` /
`swipe_camera`, else its storyboard section's first swipe shot, else the
brief's "K03: …" source) → the storyboard's usable still of it (first, else
middle, else last — never a black transition) → the full-resolution frame of
`framemap/frames/` at that moment, SHARP, people included (the owner, 2026-10-08:
"we're always using our swipes in their entirety … I don't know why you would
blur a frame"). Our people come from the cast masters ahead of it. The prompt says what it is for:
match framing, camera, positions; replace the people, product and brand with ours. The LAST frame is an edit of the first, so it inherits them.
Everything is read from the brief's block and the element homes
(element_paths.py) — nothing is described in words that a picture can carry.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_REFS = 5


def _load(name):
    import importlib.util as ilu
    sp = ilu.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    m = ilu.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def _first(folder: Path, names: list[str]) -> Path | None:
    for n in names:
        for f in sorted(folder.glob(n)):
            if f.is_file():
                return f
    return None


def person_master(folder: Path) -> Path | None:
    return _first(folder, ["full/master.png", "master.jpg", "master-sheet.png", "master-sheet.webp"])


def look_sheet(folder: Path, look: str) -> Path | None:
    return _first(folder, [f"full/sheets/{look}.png", f"sheets/{look}.jpg"]) if look else None


def set_plate(folder: Path, camera: str, to_camera: bool) -> Path | None:
    cam = (camera or "").lower()
    plates = sorted((folder / "full" / "plates").glob("*.png")) or sorted((folder / "plates").glob("*.jpg"))
    want = []
    if "above" in cam or "down" in cam or "top" in cam:
        want.append("top-down")
    if "over the shoulder" in cam or "over-shoulder" in cam:
        want.append("over-shoulder")
    if "across" in cam:
        want.append("across")
    # a straight-on, eye-level shot wants the front plate even when nobody talks
    # to the lens (2026-10-02: a front close-up was given the side angle)
    if to_camera or "straight" in cam or "eye level" in cam or "facing the lens" in cam or "set still" in cam:
        want += ["to-camera", "propped", "front"]
    want.append("side")
    for w in want:
        hit = next((p for p in plates if w in p.stem), None)
        if hit:
            return hit
    return next((p for p in plates if p.stem == "wide"), plates[0] if plates else None)


COMPOSITION = "swipe composition"
COMPOSITION_RULE = ("The swipe composition reference ({k}) is for composition only: match its framing, "
                    "camera, angle and where every person and thing stands; replace its people, product "
                    "and brand with ours from the other references.")


def swipe_frame(scene: dict, run: Path | None, item: dict | None = None) -> tuple[str, Path] | None:
    """(K##, the full-resolution swipe frame this scene recreates) or None."""
    if run is None:
        return None
    try:
        sb = json.loads((Path(run) / "storyboard.json").read_text())
    except (OSError, ValueError):
        return None
    td = _load("elements_check").resolve_teardown(sb.get("teardown"))
    if not td:
        return None
    SP = _load("storyboard_plan")
    item = item or {}
    k = item.get("copies_swipe_shot") or item.get("swipe_camera")
    if not k:
        sid = scene.get("id")
        for g in sb.get("sections") or []:
            if sid in (g.get("scenes") or []) or (g.get("start_frame") or {}).get("from_scene") == sid:
                shots = (g.get("swipe") or {}).get("shots") or []
                k = shots[0].get("id") if shots else None
                break
    if not k:
        ks = SP.cites_of(scene)
        k = ks[0] if ks else None
    if not k:
        return None
    still = SP.usable_frame(td / "framemap" / "shots", k)
    if still is None:
        return None
    # the owner, 2026-10-08: the swipe is used whole ("cutting the meat off the bone") — the SHARP
    # frame, people included; our people come from the cast masters ahead of it in the list
    return k, full_frame(td, k, still) or still


def full_frame(td: Path, k: str, still: Path) -> Path | None:
    """The original-resolution frame of framemap/frames/ at the still's moment."""
    try:
        rows = [r for r in json.loads((td / "framemap" / "frames" / "index.json").read_text())["frames"]
                if r["shot"] == k]
    except (OSError, ValueError, KeyError):
        return None
    if not rows:
        return None
    which = still.stem.rsplit("-", 1)[-1]
    r = rows[0] if which == "first" else rows[-1] if which == "last" else rows[len(rows) // 2]
    f = td / "framemap" / r["file"]
    return f if f.is_file() else None


def refs_for_scene(scene: dict, doc: dict, brand: str, ws: Path | None = None,
                   swipe: tuple[str, Path] | None = None) -> list[tuple[str, Path]]:
    EP = _load("element_paths"); EC = _load("elements_check")
    ws = ws or EP.WS
    cast = doc.get("cast") or []
    ids = [c.get("id") for c in cast if c.get("id")]
    bank = {c["id"]: (c.get("bank_id") if (c.get("bank_id") or "").upper() != "NEW" else EC.slug(c["id"])) or EC.slug(c["id"]) for c in cast if c.get("id")}
    people = EC._people_in(scene.get("who", ""), ids)
    looks = scene.get("looks") or {}
    for pid in looks:
        if pid in bank and pid not in people:
            people.append(pid)
    out: list[tuple[str, Path]] = []
    for pid in people:
        m = person_master(EP.casting_home(brand, bank[pid], ws))
        if m:
            out.append((f"{pid} master", m))
    # the REAL packshot outranks everything but the faces: a product left out
    # of the references is a product drawn from words (the invented tube)
    locked = {str(l).split(" ")[0].strip("—-·:") for l in doc.get("product_lock") or []}
    # the element manifest knows every scene the product is in, not just the one
    # the brief tagged (2026-10-07: the athlete's S8 drew "the device" as an energy-drink can
    # because only the endcard carried `product`)
    if scene.get("product") or scene.get("id") in locked or scene.get("id") in (doc.get("_product_scenes") or ()):
        pid_ = (doc.get("piece") or {}).get("product") or ""
        kit = EP.product_kit(brand, pid_, ws)
        # the product's real turntable (front, three-quarter, side, back — cut from the store's own 360°
        # video, 2026-10-08) outranks a single packshot: one front photo let the device be drawn as a can, a
        # disc and 40% too small; four real angles leave the shape nothing to guess
        shot = _first(kit / "sources", ["turntable-sheet.png", "*packshot*"]) if kit and (kit / "sources").is_dir() else None
        shot = shot or _first(EP.product_home(brand, pid_, ws) / "images", ["packshot-tube.png", "packshot-hero.*", "packshot*"])
        if not shot:
            # not in this repo copy: the Drive's packshot folder (reorganized 2026-10-01)
            _BF = _load("brandfiles")
            got, _why = _BF.packshot_of(brand, pid_)
            shot = got if isinstance(got, Path) and got.is_file() else None
        if shot:
            out.append(("real packshot", shot))
        # HOW IT BEHAVES (2026-10-07, restored 2026-10-09 after the 10-08 turntable change dropped it):
        # how the product rests when nobody holds it goes in as a picture too (the device in its cradle or case)
        if kit and (kit / "kit.json").is_file():
            PB = _load("product_behaviour")
            beh = json.loads((kit / "kit.json").read_text()).get("behaviour")
            for r in PB.rest_refs(brand, kit.name, beh)[:1]:
                out.append(("product at rest", r))
    # the swipe frame it recreates — framing, camera, positions — before the
    # set plate (2026-10-08); with a full house the props and outfits go first
    if swipe:
        out.append((f"{COMPOSITION} {swipe[0]}", swipe[1]))
    # the place goes in before the outfits: with two people and the product the
    # five slots ran out and the room was dropped (2026-10-02, QC B3)
    sid = scene.get("setting_id")
    world = {w.get("id"): w for w in doc.get("world") or []}
    if sid:
        w = world.get(sid, {})
        sb = w.get("bank_id") if (w.get("bank_id") or "").upper() not in ("", "NEW") else EC.slug(sid)
        ff = scene.get("first_frame") or {}
        p = set_plate(EP.elements_home(brand, "sets", sb, ws), ff.get("camera", ""), bool(scene.get("to_camera")))
        if p:
            out.append((f"set {sid} · {p.stem}", p))
    who = (scene.get("who") or "").lower()
    for pid in people:
        # someone shown only as hands shows a sleeve, said in words — their look
        # sheet would take the slot a face or the room needs
        if re.search(rf"{re.escape(pid.lower())}'s hands?\b", who):
            continue
        s = look_sheet(EP.casting_home(brand, bank[pid], ws), looks.get(pid, ""))
        if s:
            out.append((f"{pid} look {looks.get(pid)}", s))
    for prop in scene.get("props") or []:
        f = EP.elements_home(brand, "props", EC.slug(prop), ws) / "picture.jpg"
        if f.is_file():
            out.append((f"prop {prop}", f))
    return out[:MAX_REFS]


def wardrobe_words(scene: dict, doc: dict, brand: str, ws: Path | None = None) -> str:
    """'NOVA wears …' for every person in the scene who has a look — read from
    the person's own looks.json, never written here."""
    EP = _load("element_paths"); EC = _load("elements_check")
    ws = ws or EP.WS
    cast = doc.get("cast") or []
    bank = {c["id"]: (c.get("bank_id") if (c.get("bank_id") or "").upper() != "NEW" else EC.slug(c["id"])) or EC.slug(c["id"]) for c in cast if c.get("id")}
    out = []
    for pid, look in (scene.get("looks") or {}).items():
        if pid not in bank or not look:
            continue
        f = EP.casting_home(brand, bank[pid], ws) / "looks.json"
        try:
            rec = (json.loads(f.read_text()).get("looks") or {}).get(look) or {}
        except (OSError, ValueError):
            rec = {}
        if rec.get("outfit"):
            cont = f" ({rec['continuity']})" if rec.get("continuity") else ""
            out.append(f"{pid} wears {rec['outfit']}{cont}, exactly as in the outfit reference "
                       f"— their face reference is for the face only, not the clothes.")
    return " ".join(out)


def label_words(doc: dict, brand: str, ws: Path | None = None) -> str:
    """The real label, letter for letter, from the product's provenance.json
    label_lock (model-inputs.json frame_rules.product_label)."""
    EP = _load("element_paths")
    ws = ws or EP.WS
    pid = (doc.get("piece") or {}).get("product") or ""
    try:
        lock = json.loads((EP.product_home(brand, pid, ws) / "provenance.json").read_text()).get("label_lock")
    except (OSError, ValueError):
        lock = None
    label = f"The product's label reads exactly as the packshot, letter for letter: {lock}." if lock else ""
    # model-inputs.json frame_rules.product_scale (2026-10-02, Section 21's tube)
    try:
        scale = (json.loads((HERE / "model-inputs.json").read_text()).get("frame_rules") or {}).get("product_scale", {}).get("says", "")
    except (OSError, ValueError):
        scale = ""
    return " ".join(x for x in (label, scale) if x)


def behaviour_words(doc: dict, brand: str, motion: bool = False) -> str:
    """How the product physically behaves, from its kit (product_behaviour.py): for a
    still, what it cannot do, how it rests and how it is held; for a clip, what may
    happen to it while it moves (the owner, 2026-10-09: the device is never left on its own)."""
    EP = _load("element_paths")
    pid = (doc.get("piece") or {}).get("product") or ""
    kit = EP.product_kit(brand, pid, EP.WS) if pid else None
    if not kit or not (kit / "kit.json").is_file():
        return ""
    beh = json.loads((kit / "kit.json").read_text()).get("behaviour")
    PB = _load("product_behaviour")
    name = pid.upper() if len(pid) <= 6 else "the product"
    return PB.motion_words(beh, name) if motion else PB.words(beh, name)


def product_scene(sc: dict, doc: dict) -> bool:
    locked = {str(l).split(" ")[0].strip("—-·:") for l in doc.get("product_lock") or []}
    return bool(sc.get("product") or sc.get("id") in locked or sc.get("id") in (doc.get("_product_scenes") or ()))


def bind(items: list[dict], brief_text: str, brand: str, run: Path | None = None) -> list[str]:
    """Put each scene's element pictures on its first-frame still. Returns a
    line per scene saying what went in (written to <run>/element-refs.json)."""
    EC = _load("elements_check")
    doc = EC._json_block(brief_text)
    scenes = {s.get("id"): s for s in doc.get("scenes") or []}
    if run is not None and (Path(run) / "elements.json").is_file():
        man = json.loads((Path(run) / "elements.json").read_text())
        doc["_product_scenes"] = {sid for i in man.get("items") or [] if i.get("kind") == "product"
                                  for sid in i.get("scenes") or []}
    notes, record = [], {}
    for it in items:
        # THE CLIP KEEPS THE PHYSICS TOO (2026-10-09): a clip of a product scene says what may
        # happen to the product while it moves — the device is never set down loose, never stood up
        if it.get("kind") == "motion" and isinstance(it.get("params"), dict):
            sc = scenes.get(it.get("for") or it.get("id"))
            if sc and product_scene(sc, doc):
                mw = behaviour_words(doc, brand, motion=True)
                if mw and mw not in it["params"].get("prompt", ""):
                    it["params"]["prompt"] = (it["params"].get("prompt", "").rstrip() + " " + mw).strip()
                    notes.append(f"{it['id']}: product physics on the clip")
            continue
        if it.get("frame_role") != "first" or it.get("kind") not in ("still", "cast"):
            continue
        sc = scenes.get(it.get("for"))
        if not sc:
            continue
        sw = swipe_frame(sc, run, it)
        refs = refs_for_scene(sc, doc, brand, swipe=sw)
        if not refs:
            continue
        keep = [m for m in it.get("medias") or [] if m.get("role") != "image_references"]
        it["medias"] = [{"role": "image_references", "value": str(p)} for _, p in refs] + keep
        # THE OUTFIT IS SAID IN WORDS (2026-10-02, the three-doctors run QC): with only the look
        # sheet attached, 8 of 22 pictures put NOVA in her master's plain
        # T-shirt. Each person's look is named from their looks.json, and the
        # master is said to be for the face only.
        worn = wardrobe_words(sc, doc, brand)
        if any(w == "real packshot" for w, _ in refs):
            worn = (worn + " " + label_words(doc, brand) + " " + behaviour_words(doc, brand)).strip()
        comp = next((w for w, _ in refs if w.startswith(COMPOSITION)), None)
        if comp:
            it["swipe_composition"] = comp.split()[-1]
            worn = (COMPOSITION_RULE.format(k=it["swipe_composition"]) + " " + worn).strip()
        if worn and isinstance(it.get("params"), dict) and worn not in it["params"].get("prompt", ""):
            it["params"]["prompt"] = (it["params"].get("prompt", "").rstrip() + " " + worn).strip()
        record[it["id"]] = [{"what": w, "file": str(p)} for w, p in refs]
        notes.append(f"{it['id']}: " + " · ".join(w for w, _ in refs))
    if run:
        (run / "element-refs.json").write_text(json.dumps(record, indent=1))
    return notes
