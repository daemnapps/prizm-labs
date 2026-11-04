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


def packshot_names() -> list:
    """Which file in a product's images/ folder is its packshot, in order (model-inputs.json frame_rules.packshot_names —
    data, so no product's file name is written here)."""
    fr = (json.loads((HERE / "model-inputs.json").read_text()).get("frame_rules") or {})
    return list(fr.get("packshot_names") or ["packshot-hero.*", "packshot*"])


PRODUCT_IN_GENERATION = False
PRODUCT_NONE = ("draw no product, container or packaging; where the person holds one, the hands stay where they "
                "are, empty.")
PRODUCT_HELD = ("the ONLY product is the brand's own, exactly as the 'real product' reference shows it — its shape, "
                "colour, cap and label, at its real size{size} — held in the person's hands as the scene says, label "
                "toward the lens; no other product, container or packaging anywhere. (Its pixels are replaced with the "
                "real photograph right after, so match its pose and size, not its print.)")
# THE REAL PRODUCT IN THE HANDS (P68 add, the owner 2026-10-21: the cast member was holding the wrong product): a scene where a person holds or shows the product gets the brand's REAL packshot as a
# reference so the hands hold it at its true pose and size; product_paste.py then replaces every pixel of it with the
# real photograph (the kit's real cut-outs) before any clip. Any other scene draws no product at all.
NO_PRODUCT = (" Draw no product, container or packaging in this picture: the real product is laid on in the "
              "edit from its own photograph, so where it is held or set down, leave that hand or surface clear.")

COMPOSITION = "swipe composition"
COMPOSITION_RULE = ("The swipe composition reference ({k}) is for composition only: match its framing, "
                    "camera, angle and where every person and thing stands; replace its people, product "
                    "and brand with ours from the other references.")

# FRAMES BY EDIT OF THE SWIPE (the owner, 2026-10-20: "we should be using the swipe as the frame references the entire
# way through and just swapping in our elements"; "you are putting in the elements like the flowers, bottles and
# stuff on the images themselves … those elements should be printed on top"). A brief whose piece says
# `"frames": "swipe-edit"` gets every first frame as an EDIT of the swipe's own frame: image 1 is the swipe frame,
# then only our people's masters and looks — no item, prop, plate or packshot pictures — and the words say what
# changes, never what the frame already shows. Items are laid on in the edit as cut-outs.
SWIPE_EDIT = ("Edit image 1, a real frame from a phone video. Change these and nothing else: "
              "(1) THE PERSON: replace them with {who} — face, hair, skin, age and build exactly as the {people} "
              "image{s} show{verb} (the same person, never younger or smoother), wearing {worn}. "
              "(2) THE PROPS: every object in image 1 that is not in our list goes — {props} "
              "(3) THE WORDS: remove every word, caption, headline, label and sign in image 1. "
              "(4) THE PRODUCT: {product} "
              "(5) THE SET: {dressing} "
              "Fill every removed area with what is naturally behind it. Keep everything else exactly as image 1: the "
              "framing, pose, head angle, expression, camera, lens, light, colour and the plain phone-camera quality "
              "with its softness and grain — do not make it look more polished or higher quality than image 1.")
# TWO OR MORE PEOPLE (2026-10-24, the pastor barber's S22B): "replace them with A and B" put the pastor's blazer on the
# man at the car window in all three versions — the model blended the two. Each swipe person is named by where they
# are in image 1 (the first frame's own words) and given only their own reference images.
PERSON_MANY = ("(1) THE PEOPLE: image 1 has {n} people, and each becomes ONE of ours — never a blend, never one's "
               "clothes on the other: {each} Face, hair, skin, age and build exactly as their own images show (the same "
               "person, never younger or smoother); {worn} ")


def person_clauses(who_ids: list, people: list, cast: dict, subject: str) -> str:
    """'(a) THE MAN AT THE WINDOW — at the left leaning on the door — is …, images 2–5 only; (b) …' for PERSON_MANY.
    `people` is the (label, file) list in send order; image 1 is the swipe frame, so theirs start at 2."""
    parts = [x.strip() for x in str(subject or "").split(";") if x.strip()]
    out = []
    for k, pid in enumerate(who_ids):
        idx = [i + 2 for i, (w, _) in enumerate(people) if w == f"{pid} master" or w.startswith(f"{pid} ")]
        where = next((x for x in parts if pid.lower() in x.lower()), "")
        where = where.replace(pid, "").strip(" ,") if where else ""
        ident = (cast.get(pid) or {}).get("identity_block") or pid
        span = (f"images {idx[0]}–{idx[-1]}" if len(idx) > 1 else f"image {idx[0]}") if idx else "their images"
        out.append(f"({chr(97 + k)}) {pid}" + (f" — the one {where} —" if where else "") + f" becomes {ident}, "
                   f"as {span} show and no other.")
    return " ".join(out)


# P68 (2026-10-21, the first real v2 pictures carried the swipe's ingredients, words, a drawn jar, a younger woman and the
# swipe's flags): the change list names all five. The props and the set come from the brief's own props[] and world[].
NO_ITEMS = (" Add no product, cut-out, sticker, badge or words to the picture; keep the plain phone-camera quality "
            "of the first frame.")


def swipe_props(scene: dict, doc: dict, brand: str, ws: Path | None = None) -> tuple:
    """(the prop sentence, [(what, banked picture)]) for a swipe-edit frame (P68): the brief's own props for this scene,
    each as it is defined once (props[]: name, size, look) with its banked picture as a reference — the swipe's props
    are swapped for these, never kept."""
    EP = _load("element_paths"); EC = _load("elements_check")
    ws = ws or EP.WS
    defs = {str(p.get("name")).lower(): p for p in (doc.get("props") or []) if isinstance(p, dict) and p.get("name")}
    words, refs = [], []
    for name in scene.get("props") or []:
        d = defs.get(str(name).lower()) or {}
        words.append(f"{name}" + (f" ({d['size']})" if d.get("size") else "") + (f": {d['look']}" if d.get("look") else ""))
        f = next((x for x in (EP.elements_home(brand, "props", EC.slug(name), ws) / n for n in ("picture.png", "picture.jpg"))
                  if x.is_file()), None)
        if f:
            refs.append((f"prop {name}", f))
    if not words:
        return "our list is empty: remove every object the person holds or that sits in front of them.", refs
    return ("our list: " + "; ".join(words) + " — each exactly as its own picture among the references shows it, at its "
            "real size, in the place image 1's object was."), refs


def set_words(scene: dict, doc: dict) -> str:
    """The set sentence for a swipe-edit frame (P68): the room keeps image 1's layout, its dressing becomes ours."""
    w = next((x for x in doc.get("world") or [] if x.get("id") == scene.get("setting_id")), {})
    dressing = "; ".join(map(str, w.get("dressing") or []))
    return ("keep the room's layout, but its decoration is only ours" + (f" — {dressing}" if dressing else "")
            + "; remove any flag, poster, sign or decoration image 1 has that our set does not.")


def real_packshot(brand: str, doc: dict, ws: Path | None = None) -> Path | None:
    """The brand's REAL product photograph for the piece's product: the kit's own packshot, else the product's images,
    else the Drive's packshot folder. None when there is none on this machine."""
    EP = _load("element_paths")
    ws = ws or EP.WS
    pid = (doc.get("piece") or {}).get("product") or ""
    if not pid:
        return None
    kit = EP.product_kit(brand, pid, ws)
    shot = None
    if kit and (kit / "sources").is_dir():
        shot = _first(kit / "sources", ["*packshot_white*", "*packshot*", "turntable-sheet.png"])
    shot = shot or _first(EP.product_home(brand, pid, ws) / "images", packshot_names())
    if not shot:
        try:
            got, _why = _load("brandfiles").packshot_of(brand, pid)
            shot = got if isinstance(got, Path) and got.is_file() else None
        except Exception:                               # noqa: BLE001
            shot = None
    return shot


def in_use_of(brand: str, doc: dict, ws: Path | None = None):
    """THE PRODUCT IN USE, DRAWN FROM ITS REAL PICTURES (the owner, 2026-10-25, on the carousels made this way: "literally
    1000000x better than any flex implementation we had in the past ... not just statics but also video scenes as
    well"): the kit's `in_use` pictures (the side the camera sees in use, a real hold) and its line, or None when the
    kit has none. A still that gets them is drawn from them and never pasted over afterwards."""
    try:
        EP = _load("element_paths")
        kit = EP.product_kit(brand, (doc.get("piece") or {}).get("product") or "", ws or EP.WS)
        use = (json.loads((kit / "kit.json").read_text()).get("in_use") or {}) if kit else {}
    except (OSError, ValueError, TypeError):
        return None
    refs = [kit / r for r in use.get("refs") or [] if (kit / r).is_file()] if use else []
    return (refs, use.get("line") or "") if refs else None


def held_product(scene: dict, doc: dict) -> bool:
    """Does a person hold or show the product in this scene?"""
    return product_scene(scene, doc) and scene_holds_product(scene)


def product_words(scene: dict, doc: dict, brand: str, ws: Path | None = None) -> str:
    """(4) of the swipe-edit change list: the real product in the hands where the scene holds it, else none."""
    if not held_product(scene, doc):
        return PRODUCT_NONE
    iu = in_use_of(brand, doc, ws)
    if iu:
        return ("the ONLY product is the brand's own, exactly as its real in-use pictures among the references show it; "
                "no other product, jar, bottle or packaging anywhere. " + iu[1]).strip()
    size = ""
    try:
        EP = _load("element_paths")
        kit = EP.product_kit(brand, (doc.get("piece") or {}).get("product") or "", ws or EP.WS)
        cm = json.loads((kit / "kit.json").read_text()).get("size_cm") or {} if kit else {}
        if cm.get("height"):
            size = f", {cm['height']:g} cm tall"
    except (OSError, ValueError, TypeError):
        size = ""
    return PRODUCT_HELD.format(size=size)


def swipe_edit_on(doc: dict) -> bool:
    return str((doc.get("piece") or {}).get("frames") or "").lower() == "swipe-edit"


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
    # the brief tagged (2026-10-07: LeBron's S8 drew "NOVA" as an energy-drink can
    # because only the endcard carried `product`)
    # THE PRODUCT IS NEVER DRAWN (VIDEO-RULINGS V16, CHANGES.md C5 + P34, 2026-10-21): no packshot, turntable or
    # product-in-hand picture is attached to a GENERATION any more — the picture model drew the product from them.
    # The product is laid on in the edit from its real photograph; the endcard is still an edit OF that photograph
    # (run.py's packshot item), which is not this path. PRODUCT_IN_GENERATION is the record of the old behaviour.
    if PRODUCT_IN_GENERATION and (scene.get("product") or scene.get("id") in locked
                                  or scene.get("id") in (doc.get("_product_scenes") or ())):
        pid_ = (doc.get("piece") or {}).get("product") or ""
        kit = EP.product_kit(brand, pid_, ws)
        # the product's real turntable (front, three-quarter, side, back — cut from the store's own 360°
        # video, 2026-10-08) outranks a single packshot: one front photo let NOVA be drawn as a can, a
        # disc and 40% too small; four real angles leave the shape nothing to guess
        shot = _first(kit / "sources", ["turntable-sheet.png", "*packshot*"]) if kit and (kit / "sources").is_dir() else None
        shot = shot or _first(EP.product_home(brand, pid_, ws) / "images", packshot_names())
        if not shot:
            # not in this repo copy: the Drive's packshot folder (reorganized 2026-10-01)
            _BF = _load("brandfiles")
            got, _why = _BF.packshot_of(brand, pid_)
            shot = got if isinstance(got, Path) and got.is_file() else None
        if shot:
            out.append(("real packshot", shot))
        # HOW IT BEHAVES (2026-10-07, restored 2026-10-09 after the 10-08 turntable change dropped it):
        # how the product rests when nobody holds it goes in as a picture too (NOVA in its cradle or case)
        if kit and (kit / "kit.json").is_file():
            PB = _load("product_behaviour")
            beh = json.loads((kit / "kit.json").read_text()).get("behaviour")
            # held in the scene: a real photo of it in a hand; nobody holding it: how it rests
            h = held_ref(kit, scene_words(scene)) if scene_holds_product(scene) else None
            if h:
                out.append(("product in hand", h))
            else:
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
    """'CREATOR-A wears …' for every person in the scene who has a look — read from
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
    # the MEASURED size from the product kit, in centimetres (2026-10-09, the owner: "the dimensions, what the
    # product looks like in hand … there should be no guessing" — the words above say "real size" without one)
    size = ""
    try:
        kit = EP.product_kit(brand, pid, ws)
        cm = json.loads((kit / "kit.json").read_text()).get("size_cm") or {} if kit else {}
        if cm.get("height") and cm.get("width"):
            size = (f"Measured size: {cm['height']:g} cm tall, {cm['width']:g} cm wide"
                    + (f", {cm['depth']:g} cm deep" if cm.get("depth") else "")
                    + " — against an adult's hand that is " + _hand_scale(float(cm["height"])) + ".")
    except (OSError, ValueError, TypeError):
        size = ""
    return " ".join(x for x in (label, scale, size) if x)


def _hand_scale(h_cm: float) -> str:
    """The height said against a hand, so a picture model can see it (an adult palm is ~10 cm, a hand ~19 cm)."""
    if h_cm < 6:
        return "smaller than the palm, held in the fingers"
    if h_cm < 9:
        return "a little shorter than the palm"
    if h_cm < 13:
        return "about the length of the palm: it fills the palm, its top reaching the base of the fingers"
    if h_cm < 18:
        return "longer than the palm, most of the hand's length"
    return "longer than the whole hand"


def held_ref(kit: Path | None, scene_text: str = "") -> Path | None:
    """A REAL photo of the product in a hand (2026-10-09): words alone drew it pinched at the fingertips,
    two-handed and too small. First choice: the frame of the brand's own footage of a real person using it
    that is closest to what the scene does (the usage bank, product_usage.py); then the store's own photo."""
    if not kit:
        return None
    try:
        got = _load("product_usage").pick(kit, scene_text)
        if got:
            return got
    except Exception:                                   # noqa: BLE001 — a bank that cannot be read falls back
        pass
    if not (kit / "sources").is_dir():
        return None
    return _first(kit / "sources", ["*in-hand-water*", "*in-hand*", "*model-using*"])


def scene_words(scene: dict) -> str:
    ff = scene.get("first_frame") or {}
    return " ".join(str(x) for x in (scene.get("happens"), scene.get("setting"), ff.get("subject"),
                                     ff.get("action"), ff.get("composition"), ff.get("location")) if x)


_HELD = re.compile(r"\b(hand|hands|holds?|holding|held|palm|grip|grips|gripping|scrub|scrubs|scrubbing|"
                   r"brush(?:es|ing)?|presses|pressing|glides?|gliding|circles?)\b", re.I)


def scene_holds_product(scene: dict) -> bool:
    ff = scene.get("first_frame") or {}
    text = " ".join(str(x) for x in (scene.get("who"), scene.get("action"), scene.get("what"), scene.get("happens"),
                                     ff.get("action"), ff.get("subject"), ff.get("description"), ff.get("prompt")) if x)
    return bool(_HELD.search(text))


def behaviour_words(doc: dict, brand: str, motion: bool = False) -> str:
    """How the product physically behaves, from its kit (product_behaviour.py): for a
    still, what it cannot do, how it rests and how it is held; for a clip, what may
    happen to it while it moves (the owner, 2026-10-09: NOVA is never left on its own)."""
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
    last_sw = None
    for it in items:
        # THE CLIP KEEPS THE PHYSICS TOO (2026-10-09): a clip of a product scene says what may
        # happen to the product while it moves — NOVA is never set down loose, never stood up
        if it.get("kind") == "motion" and isinstance(it.get("params"), dict):
            sc = scenes.get(it.get("for") or it.get("id"))
            if sc and product_scene(sc, doc):
                mw = behaviour_words(doc, brand, motion=True)
                if mw and mw not in it["params"].get("prompt", ""):
                    it["params"]["prompt"] = (it["params"].get("prompt", "").rstrip() + " " + mw).strip()
                    notes.append(f"{it['id']}: product physics on the clip")
            continue
        if swipe_edit_on(doc) and it.get("frame_role") == "last" and isinstance(it.get("params"), dict) \
                and NO_ITEMS.strip() not in it["params"].get("prompt", ""):
            it["params"]["prompt"] = (it["params"].get("prompt", "").rstrip() + NO_ITEMS).strip()
        if it.get("frame_role") != "first" or it.get("kind") not in ("still", "cast"):
            continue
        sc = scenes.get(it.get("for"))
        if not sc:
            continue
        sw = swipe_frame(sc, run, it)
        if swipe_edit_on(doc):
            # a scene the swipe has no shot for (our offer / guarantee turns of the same loop) is an edit of the
            # last swipe frame used: same room, same camera, our person (2026-10-20)
            sw = sw or last_sw
            last_sw = sw or last_sw
        refs = refs_for_scene(sc, doc, brand, swipe=sw)
        if not refs:
            continue
        if swipe_edit_on(doc) and sw:
            people = []
            for w, p in refs:
                if w.endswith(" master"):
                    # the person's FULL casting sheet, never the master alone (video-production CLAUDE.md, "a swap is
                    # the whole character"; the owner 2026-10-20: "this is why we apply full casting sheets")
                    people.append((w, p))
                    sheets = Path(p).parent / "sheets" if Path(p).parent.name == "full" else Path(p).parent / "full" / "sheets"
                    for s in ("turnaround", "angles-expressions", "details"):
                        f = next((x for x in (sheets / f"{s}.png", sheets / f"{s}.jpg") if x.is_file()), None)
                        if f:
                            people.append((f"{w.rsplit(' master', 1)[0]} {s}", f))
                elif " look " in f" {w} ":
                    people.append((w, p))
            if people and isinstance(it.get("params"), dict):
                cast = {c.get("id"): c for c in doc.get("cast") or []}
                who_ids = [w.rsplit(" master", 1)[0] for w, _ in people if w.endswith(" master")]
                who = " and ".join((cast.get(i) or {}).get("identity_block") or i for i in who_ids) or "our person"
                worn = wardrobe_words(sc, doc, brand) or "the outfit in the look image"
                refs = [(f"swipe frame {sw[0]}", sw[1])] + people
                keep = [m for m in it.get("medias") or [] if m.get("role") != "image_references"]
                it["medias"] = [{"role": "image_references", "value": str(p)} for _, p in refs] + keep
                p_words, p_refs = swipe_props(sc, doc, brand)
                refs = refs + p_refs
                if held_product(sc, doc):
                    iu = in_use_of(brand, doc)
                    if iu:                                  # drawn from its real in-use pictures, never pasted (2026-10-25)
                        refs = refs + [("real product in use", p) for p in iu[0]]
                        it["in_use"] = True
                    else:
                        real = real_packshot(brand, doc)
                        if real:
                            refs = refs + [("real product", real)]
                it["medias"] = [{"role": "image_references", "value": str(p)} for _, p in refs] + keep
                prompt = SWIPE_EDIT.format(who=who, worn=worn, s="s" if len(people) > 1 else "",
                                           verb="" if len(people) > 1 else "s",
                                           people=f"next {len(people)}", props=p_words,
                                           dressing=set_words(sc, doc),
                                           product=product_words(sc, doc, brand))
                if len(who_ids) > 1:
                    subject = (sc.get("first_frame") or {}).get("subject") or sc.get("who") or ""
                    one = prompt[prompt.index("(1) THE PERSON:"):prompt.index("(2) THE PROPS:")]
                    prompt = prompt.replace(one, PERSON_MANY.format(
                        n=len(who_ids), each=person_clauses(who_ids, people, cast, subject),
                        worn=f"wearing: {worn}" if worn else ""))
                it["params"]["prompt"] = prompt
                it["swipe_edit"] = sw[0]
                record[it["id"]] = [{"what": w, "file": str(p)} for w, p in refs]
                notes.append(f"{it['id']}: SWIPE EDIT · " + " · ".join(w for w, _ in refs))
                continue
        keep = [m for m in it.get("medias") or [] if m.get("role") != "image_references"]
        it["medias"] = [{"role": "image_references", "value": str(p)} for _, p in refs] + keep
        # THE OUTFIT IS SAID IN WORDS (2026-10-02, kzn03 QC): with only the look
        # sheet attached, 8 of 22 pictures put CREATOR-A in her master's plain
        # T-shirt. Each person's look is named from their looks.json, and the
        # master is said to be for the face only.
        worn = wardrobe_words(sc, doc, brand)
        iu = in_use_of(brand, doc) if held_product(sc, doc) else None
        if iu:                                              # drawn from its real in-use pictures, never pasted (2026-10-25)
            have = [m.get("value") for m in it.get("medias") or []]
            for p in iu[0]:
                if str(p) not in have:
                    it["medias"].insert(0, {"role": "image_references", "value": str(p)})
                    refs = refs + [("real product in use", p)]
            it["in_use"] = True
            worn = (worn + " " + product_words(sc, doc, brand)).strip()
        elif held_product(sc, doc):
            real = real_packshot(brand, doc)
            if real and str(real) not in [m.get("value") for m in it.get("medias") or []]:
                it["medias"].insert(0, {"role": "image_references", "value": str(real)})
                refs = refs + [("real product", real)]
            worn = (worn + " " + product_words(sc, doc, brand)).strip()
        elif not PRODUCT_IN_GENERATION and product_scene(sc, doc):
            worn = (worn + NO_PRODUCT).strip()
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
