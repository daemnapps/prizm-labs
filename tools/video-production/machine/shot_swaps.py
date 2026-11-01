"""A SHOT'S START PICTURE TAKES ITS SWAPS FROM THE VIDEO BRIEF (2026-10-27).

The picture chain writes its own ad (its injection picks a cast member and invents swaps) because a picture ad has no
brief before it. A video shot does: the brief and the scene plan already say who is in the shot, in which look, in
which place, holding which props. So the start picture of a shot is built from the swipe's own frame (IMAGE 1) with
ONLY those swapped in, each tied to its banked picture — never a new concept:

    the swipe's person      → our cast member (cast row, their bank id) + their look picture (library row)
    the swipe's room        → our place's banked picture (library row)
    the swipe's objects     → the shot's props from the brief, each with its banked picture (library rows),
                              or nothing (a bare counter) where the brief has none
    a product in the shot   → the real product (product row)

The judge reads the swipe frame to name what each swipe item IS (the `from` side); the `to` side and every picture
come from the brief and the banks, never from the judge. Everything the rows do not name stays exactly as IMAGE 1.

    python3 shot_swaps.py <production run> <section id> [--write <picture run>]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]


def _teardown_run(repo, run, brand=None):
    """A picture run's folder on the image-teardown plane: runs/image-teardown/<brand>/<run>/, its one home since
    2026-10-28 (components/naming/WHERE-EVERYTHING-GOES-damon.md item 4). The old lane folder
    tools/image-teardown/runs/<run>/ is read for one release, for a checkout that has not moved its runs."""
    root = Path(repo) / "runs" / "image-teardown"
    run = Path(str(run)).name
    hits = ([root / str(brand).lower() / run] if brand else []) + sorted(root.glob(f"*/{run}"))
    work = [d for d in hits if (d / "out").is_dir() or (d / "vars").is_dir()]
    old = Path(repo) / "tools" / "image-teardown" / "runs" / run
    if work:
        return work[0]
    if old.is_dir():
        return old
    return next((d for d in hits if d.is_dir()), hits[0] if hits else root / "_unfiled" / run)


def _load(name):
    spec = importlib.util.spec_from_file_location(f"vm_ss_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HERE))
    spec.loader.exec_module(mod)
    return mod


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def _first_pic(folder: Path):
    for name in ("picture.jpg", "picture.png", "master.jpg", "master.png"):
        if (folder / name).is_file():
            return folder / name
    for sub in ("plates", "full", ""):
        d = folder / sub if sub else folder
        pics = sorted(d.glob("*.jpg")) + sorted(d.glob("*.png")) if d.is_dir() else []
        # the room printed from its 3D model at the swipe's camera beats a flat wide plate (2026-10-28)
        cam = [p for p in pics if "swipe-cam" in p.name]
        wide = [p for p in pics if "wide" in p.name]
        if cam or wide or pics:
            return (cam or wide or pics)[0]
    return None


def _rel(p: Path) -> str:
    return str(p.relative_to(WS)) if p and WS in p.parents else str(p)


def accessory_sheet(accs) -> Path:
    """The chosen accessories as ONE labelled picture (each panel named), kept beside them as accessories/_set-<ids>.jpg."""
    from PIL import Image, ImageDraw, ImageFont
    home = Path(accs[0]["pic"]).parent
    out = home / ("_set-" + "-".join(sorted(a["id"].split("-")[0] for a in accs)) + ".jpg")
    if out.is_file() and all(out.stat().st_mtime >= Path(a["pic"]).stat().st_mtime for a in accs):
        return out
    H, pad = 520, 16
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
    except OSError:
        font = ImageFont.load_default()
    tiles = []
    for a in accs:
        im = Image.open(a["pic"]).convert("RGB")
        im = im.resize((int(im.width * H / im.height), H))
        t = Image.new("RGB", (im.width, H + 44), "white")
        t.paste(im, (0, 44))
        ImageDraw.Draw(t).text((10, 8), str(a.get("label", "")).replace("Accessory: ", ""), fill="black", font=font)
        tiles.append(t)
    W = sum(t.width for t in tiles) + pad * (len(tiles) + 1)
    sheet = Image.new("RGB", (W, H + 44 + 2 * pad), "white")
    x = pad
    for t in tiles:
        sheet.paste(t, (x, pad)); x += t.width + pad
    sheet.save(out, quality=90)
    return out


# THE PERSON'S OWN PRONOUNS (agnostic, 2026-10-28): the words name the cast member as their bank says they are — the
# spec's `gender`, else the words of their spec and the brief's cast line — never a pronoun written into the code
_SHE = re.compile(r"\b(woman|female|she|her|girl|lady|grandmother|grandma|mother|aunt|auntie)\b", re.I)
_HE = re.compile(r"\b(man|male|he|his|boy|guy|grandfather|grandpa|father|uncle)\b", re.I)
PRONOUNS = {"f": ("she", "her", "her"), "m": ("he", "him", "his"), "x": ("they", "them", "their")}


def pronouns(home: Path, says: str = "") -> tuple:
    """(subject, object, possessive) for one cast member, read from their bank folder and the brief's line."""
    spec = {}
    try:
        spec = json.loads((Path(home) / "spec.json").read_text())
    except (OSError, ValueError):
        pass
    g = str(spec.get("gender") or "").lower()
    if g:
        return PRONOUNS["f" if _SHE.search(g) else "m" if _HE.search(g) else "x"]
    text = " ".join(str(x) for x in (spec.get("who"), says) if x)
    f, m = _SHE.search(text), _HE.search(text)
    return PRONOUNS["f" if f and (not m or f.start() < m.start()) else "m" if m else "x"]


def _object_key(words: str) -> str:
    """The object's own noun phrase, singular: "two oversized cheek models on black bases" → "cheek model"."""
    w = re.findall(r"[a-z]+", re.split(r",| on | in | from | at | with ", str(words).lower())[0])
    w = [x[:-1] if x.endswith("s") and len(x) > 3 else x for x in w]
    return " ".join(w[-2:])


def earlier_picture(run: Path, gid: str, words: str):
    """The approved start picture of the first EARLIER scene whose start frame names the same object, or None."""
    key = _object_key(words)
    if not key or " " not in key:
        return None
    sb = json.loads((Path(run) / "storyboard.json").read_text())
    ok = json.loads((Path(run) / "shot-approvals.json").read_text()) if (Path(run) / "shot-approvals.json").is_file() else {}
    for g in sb.get("sections") or []:
        if g["id"] == gid:
            return None
        said = json.dumps(g.get("start_frame") or {}).lower()
        if key in said or key + "s" in said:
            pic = (ok.get(g["id"]) or {}).get("picture")
            f = Path(pic) if pic and Path(pic).is_absolute() else WS / str(pic or "")
            if pic and f.is_file():
                return f
    return None


def _scenes_of(run: Path, g: dict) -> list:
    """The plan's scenes (with their beats) that this section shows."""
    p = Path(run) / "plan.json"
    scenes = {x.get("id"): x for x in (json.loads(p.read_text()).get("scenes") or [])} if p.is_file() else {}
    return [scenes[s] for s in g.get("scenes") or [] if s in scenes]


def brief_parts(run: Path, gid: str) -> dict:
    """Who, which look, which place, which props and whether the product is in this shot — from the run's own files."""
    sb = json.loads((run / "storyboard.json").read_text())
    g = next(x for x in sb["sections"] if x["id"] == gid)
    rj = json.loads((run / "run.json").read_text()) if (run / "run.json").is_file() else {}
    plan = _load("storyboard_plan").brief_doc(rj.get("brief_from") or run / "brief.md")
    brand = run.parent.name
    world = {w.get("id"): w for w in plan.get("world") or []}
    cast = {c.get("id"): c for c in plan.get("cast") or []}
    people, places, props = [], [], []
    for el in g.get("elements") or []:
        parts = [p.strip() for p in str(el).split("·")]
        if parts[0] == "person" and len(parts) >= 2:
            cid = parts[1]
            c = cast.get(cid) or {}
            bank = str(c.get("bank_id") or cid).lower()
            home = WS / "runs" / "ai-elements" / brand / "casting" / bank
            look = parts[2] if len(parts) > 2 else ""
            # the run's own pick wins over the brief's (a person picks the outfit on the page; choices.json `looks`)
            picks = json.loads((run / "choices.json").read_text()).get("looks", {}) if (run / "choices.json").is_file() else {}
            look = picks.get(cid) or picks.get(bank) or look
            # THE LABELLED WARDROBE (2026-10-28):
            # the outfit and each accessory come from the person's wardrobe.json with their own label and words
            wd = json.loads((home / "wardrobe.json").read_text()) if (home / "wardrobe.json").is_file() else {}
            fit = (wd.get("outfits") or {}).get(look) or {}
            lp = home / fit["file"] if fit.get("file") else next(
                (home / d / f"{look}{ext}" for d in ("outfits", "sheets") for ext in (".jpg", ".png") if (home / d / f"{look}{ext}").is_file()),
                home / "sheets" / f"{look}.jpg")
            acc_ids = (json.loads((run / "choices.json").read_text()).get("accessories", {}) if (run / "choices.json").is_file() else {}
                       ).get(cid) or []
            accs = [dict(id=a, **(wd.get("accessories") or {})[a]) for a in acc_ids if a in (wd.get("accessories") or {})]
            says = c.get("look") or c.get("description") or ""
            people.append({"id": cid, "bank": bank, "says": says, "pron": pronouns(home, " ".join(str(c.get(k) or "") for k in ("name", "description", "look"))),
                           "look": look, "look_pic": lp if lp.is_file() else None, "fit": fit,
                           "accessories": [dict(x, pic=home / x["file"]) for x in accs if (home / x["file"]).is_file()]})
        elif parts[0] == "place" and len(parts) >= 2:
            w = world.get(parts[1]) or {}
            bank = str(w.get("bank_id") or _slug(parts[1]))
            pic = _first_pic(WS / "runs" / "ai-elements" / brand / "sets" / bank)
            places.append({"id": parts[1], "bank": bank, "pic": pic, "name": str(w.get("name") or parts[1])})
        elif parts[0] == "prop" and len(parts) >= 2:
            # a graphic pasted over the frame is the edit's layer, never an object in the start picture (2026-10-31)
            pd = next((x for x in plan.get("props") or [] if isinstance(x, dict) and str(x.get("name")).lower() == parts[1].lower()), {})
            if re.search(r"\b(pasted|graphic|cartoon|cross-section|overlay)\b", f"{parts[1]} {pd.get('look') or ''}", re.I):
                continue
            folder = WS / "runs" / "ai-elements" / brand / "props" / _slug(parts[1])
            props.append({"name": parts[1], "pic": _first_pic(folder)})
    sf = g.get("start_frame") or {}
    text = json.dumps(sf).lower()
    # the props the start frame shows, AND every prop the person picks up later in the scene: it is already in the
    # picture, within reach, so it never appears from nowhere (2026-10-28: props make physical sense —
    # "how did she scoop turmeric out of a jar that still has a cap on it?")
    later = " ".join(str(b.get("do") or "") for s in _scenes_of(run, g) for b in s.get("beats") or []
                     if isinstance(b, dict) and re.search(r"\b(holds?|lifts?|picks? up|raises?|takes?|grabs?|sets?)\b",
                                                          str(b.get("do") or ""), re.I)).lower()
    shown = [x for x in props if x["name"].lower() in text or x["name"].lower().split()[-1] in text.split(" (")[0]]
    for x in props:
        if x not in shown and (x["name"].lower() in later or x["name"].lower().split()[-1] in later):
            shown.append({**x, "later": True})
    props = shown
    lock = plan.get("product_lock")
    product = (lock.get("product") or lock.get("id") or "") if isinstance(lock, dict) else ""
    if not product:
        td = Path(rj.get("brief_from") or "").parent.parent
        product = (json.loads((td / "run.json").read_text()).get("product") or "") if (td / "run.json").is_file() else ""
    # the product is in the shot when the start frame names it: "product", "tube", or the product's own noun (the last
    # word of its id, "<name>-face-scrub" → "scrub"), never a product word written into the code
    noun = re.split(r"[-_ ]+", str(product).strip().lower())[-1] if product else ""
    in_shot = bool(re.search(r"\btube\b|\bproduct\b" + (r"|\b" + re.escape(noun) if noun else ""), text))
    return {"brand": brand, "section": g, "people": people, "places": places, "props": props,
            "start_frame": sf, "product": product if in_shot else ""}


ASK = """You are looking at IMAGE 1, one frame of a video ad (the swipe). We remake this exact frame with our own person,
place and props; everything else stays as it is. Name, in the frame's own plain words, what is there now:

- "person": the person in the frame (who they look like, what they wear), one line
- "room": the room or set behind them, one line
- "objects": every object they hold or that sits in front of them, each one line

Then, for our shot, map each object to ONE of ours or to nothing. Our shot shows:
{ours}
Our props: {props}

The swipe had it, we swap it: an object maps to one of our props, or to the object our shot puts in its place (say it
in our shot's own words), and to NONE only when our shot has nothing there.

Answer JSON only: {{"person": "...", "room": "...", "objects": [{{"swipe": "...", "ours": "<one of our props, our shot's object in its words, or NONE>"}}]}}"""


def swap_list(run: Path, gid: str, swipe_frame: Path, ask=None) -> dict:
    p = brief_parts(Path(run), gid)
    sf = p["start_frame"]
    ours = "; ".join(str(sf.get(k)) for k in ("subject", "composition", "location") if sf.get(k))
    V = _load("v2_checks")
    if ask is None:
        text, _info = V.ask(Path(run), f"shot-swaps-{gid}", ASK.format(ours=ours, props=", ".join(x["name"] for x in p["props"]) or "none"),
                            [swipe_frame], model=V.model_of("house:behind.judge"))
        seen = V.json_of(text) or {}
    else:
        seen = ask
    swaps, stays = [], []
    lead = (p["people"][0].get("pron") if p["people"] else None) or PRONOUNS["x"]
    subj, obj, poss = lead
    for who in p["people"]:
        _s, _o, hp = who.get("pron") or PRONOUNS["x"]
        swaps.append({"from": seen.get("person") or "the person in the frame", "kind": "cast", "ref": who["bank"],
                      "to": f"{who['id'].title()}, our banked cast member: {hp} face is exactly {hp} headshot's — the same face "
                            f"shape, eyes, nose, mouth, skin, age and marks, {hp} face exactly as wide and round as in the headshot, never "
                            f"narrower, longer or slimmer — and nothing of the swipe person's face shape, glasses or hair carries over; in the swipe's exact pose and gesture — "
                            f"{sf.get('subject') or ''}".strip(" —")})
        if who["look_pic"]:
            fit = who.get("fit") or {}
            swaps.append({"from": "what the person in the frame wears", "kind": "library", "ref": _rel(who["look_pic"]),
                          "to": f"{fit.get('label') or who['id'].title() + chr(39) + 's outfit'} — {fit.get('words') or 'exactly as the outfit picture shows'}; "
                                f"worn by {who['id'].title()}, on {hp} own body (the outfit picture has no face: the face is the headshot's)"})
        accs = who.get("accessories") or []
        if accs:
            # ONE LABELLED PICTURE FOR ALL HER ACCESSORIES (the picture model takes 16 images; five accessories as five
            # pictures pushed a prop-heavy shot over it): each one tiled with its own label, and every label in the words
            sheet = accessory_sheet(accs)
            swaps.append({"from": "whatever the person in the frame wears as jewellery, headwear or belt", "kind": "library",
                          "ref": _rel(sheet), "to": f"{hp} accessories, each exactly as its labelled panel shows: " + "; ".join(
                              f"{a.get('label')} ({a.get('words')}) worn on {hp} {a.get('slot')}" for a in accs)})
    # THE SHOT'S OWN 3D PRINT (2026-10-28): when the place's 3D room has
    # this shot built (worlds/rooms-3d/<room>/shots/<shot>/: plate.jpg printed from the swipe's camera, standin.png the
    # grey stand-in render, light.json the light as facts), the room IS that plate, the stand-in guides the light, and
    # the light goes into the prompt as facts
    shot_dir, light = None, {}
    for who in p["people"]:
        for pl in p["places"]:
            d = WS / "runs" / "ai-elements" / p["brand"] / "casting" / who["bank"] / "worlds" / "rooms-3d" / pl["bank"] / "shots" / gid
            if (d / "plate.jpg").is_file():
                shot_dir = d
    if shot_dir is not None:
        for pl in p["places"]:
            pl["pic"] = shot_dir / "plate.jpg"
        light = json.loads((shot_dir / "light.json").read_text()) if (shot_dir / "light.json").is_file() else {}
    for pl in p["places"]:
        if pl["pic"]:
            swaps.append({"from": seen.get("room") or f"the room behind {obj}", "kind": "library", "ref": _rel(pl["pic"]), "own_light": shot_dir is not None,
                          "to": f"{pl.get('name') or 'our place'} exactly as the room picture shows it — the room picture is this shot's room, already "
                                f"photographed from IMAGE 1's camera, with its own light, haze and depth; {subj} {'stand' if subj == 'they' else 'stands'} in it and {'are' if subj == 'they' else 'is'} lit by it"
                                + ("" if shot_dir is not None else f" ({sf.get('location') or ''})".rstrip(" ()"))})
    names = {x["name"].lower(): x for x in p["props"]}
    used, prod_from = set(), None
    for o in seen.get("objects") or []:
        mine = str(o.get("ours") or "").strip()
        hit = names.get(mine.lower())
        if hit and hit["pic"] and hit["name"] not in used:
            used.add(hit["name"])
            swaps.append({"from": o.get("swipe"), "kind": "library", "ref": _rel(hit["pic"]),
                          "to": f"the {hit['name']} from its picture, at its real size, where the swipe's object is"})
        elif p["product"] and not prod_from and re.search(r"\btube\b|\bproduct\b|\bhold\b", mine, re.I):
            # what she holds in the swipe's place becomes the real product, in that object's exact place
            prod_from = o.get("swipe")
        elif mine and mine.upper() != "NONE" and not hit and earlier_picture(run, gid, mine):
            # THE SAME OBJECT ALL THE WAY THROUGH (2026-10-28): an object an earlier approved scene already drew is taken from that scene's picture
            pic = earlier_picture(run, gid, mine)
            swaps.append({"from": o.get("swipe"), "kind": "library", "ref": _rel(pic),
                          "to": f"{mine}: the very same one this picture shows (the earlier scene's), with the same shape, "
                                f"skin, marks and stand, at its real size, in the swipe object's place; take only that "
                                f"object from the picture"})
        elif mine and mine.upper() != "NONE" and not hit:
            # our shot's own object in the swipe object's place (the swipe's foot models → our cheek models)
            swaps.append({"from": o.get("swipe"), "kind": "drawn", "ref": None,
                          "to": f"{mine}, in the swipe object's exact place, size and position"})
        else:
            swaps.append({"from": o.get("swipe"), "kind": "drawn", "ref": None,
                          "to": "nothing: that spot is bare, as the surface around it"})
    for x in p["props"]:
        if x["name"] not in used and x["pic"]:
            swaps.append({"from": f"the surface in front of {obj}", "kind": "library", "ref": _rel(x["pic"]),
                          "to": (f"the {x['name']} from its picture, at its real size, lying within {poss} reach, "
                                 f"ready to pick up later; {poss} hands do not hold it yet" if x.get("later") else
                                 f"the {x['name']} from its picture, at its real size, placed as: {sf.get('subject') or ''}")})
    if p["product"]:
        swaps.append({"from": prod_from or f"what {poss} hands hold", "kind": "product", "ref": p["product"],
                      "to": "the one real product, true size, front face to camera, held as the brief's shot says"})
    if shot_dir is not None and (shot_dir / "standin.png").is_file():
        swaps.append({"from": "where the light and shadow fall on the person in IMAGE 1", "kind": "library",
                      "ref": _rel(shot_dir / "standin.png"),
                      "to": "exactly where the light-and-shadow guide shows it: that picture is a grey 3D stand-in in this same room "
                            f"and light, ONLY a guide to which side of {obj} is lit, which falls into shadow and where {poss} shadow lands; "
                            "draw nothing from it, no grey shapes"})
    # the swipe's own captions are the edit's layer, never the picture's: they are named and removed, or the model copies them
    swaps.append({"from": "every caption, word, sticker and watermark written on IMAGE 1", "kind": "drawn", "ref": None,
                  "to": "nothing: no writing anywhere in the picture"})
    stays = ["the camera: its height, distance, angle and framing, exactly as IMAGE 1",
             ("the grain and phone-photo quality of IMAGE 1; the LIGHT is the room picture's own light, never IMAGE 1's"
              if shot_dir is not None else "the light, colour, grain and quality of IMAGE 1"),
             f"the person's pose, gesture and where {poss} hands are, exactly as IMAGE 1",
             "9:16 vertical, full bleed, no words, no captions, no logos"]
    # THE MOOD IS THE BRIEF'S (2026-10-27):
    # the face and feeling of the shot's first moment, as the brief directs it, never the picture chain's own guess
    doc = _load("storyboard_plan").brief_doc((json.loads((Path(run) / "run.json").read_text()) if (Path(run) / "run.json").is_file() else {}).get("brief_from") or Path(run) / "brief.md")
    # the swipe's frame shows her face, so the first scene of the shot where the brief directs her face sets it
    ids = p["section"].get("scenes") or []
    scs = [s for i in ids for s in doc.get("scenes") or [] if s.get("id") == i]
    first = next((s for s in scs if not re.match(r"(?i)n/?a\b", str(((s.get("shots") or [{}])[0]).get("face") or "n/a"))),
                 scs[0] if scs else {})
    shot0 = (first.get("shots") or [{}])[0]
    feeling = {"emotion": shot0.get("emotion") or first.get("emotion") or "",
               "face": shot0.get("face") or "", "gesture": (shot0.get("gestures") or [""])[0]}
    # a person's feedback on this shot from the board (shot-notes.json): it stays on the shot through every remake
    notes = []
    try:
        notes = json.loads((Path(run) / "shot-notes.json").read_text()).get(gid) or []
    except (OSError, ValueError):
        pass
    return {"swaps": swaps, "stays": stays, "kept_back": [], "words": "drawn", "feeling": feeling, "light": light, "notes": notes,
            "product_in_frame": bool(p["product"]), "product_where": f"in {poss} hands" if p["product"] else "",
            "product_sides": ["front"] if p["product"] else [], "from_brief": True, "section": gid,
            # where the made picture goes: the video run and the id its clip plan asks for (travels with the shot)
            "for_video": {"run": f"{Path(run).parent.name}/{Path(run).name}",
                          "picture": _load("clips_plan").picture_ids(p["section"]).get("start")}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run"); ap.add_argument("section"); ap.add_argument("--frame", required=True)
    ap.add_argument("--write", help="a picture run: write the list to its out/swaps.json")
    a = ap.parse_args(argv)
    sl = swap_list(Path(a.run), a.section, Path(a.frame))
    if a.write:
        out = _teardown_run(WS, a.write) / "out" / "swaps.json"
        out.write_text(json.dumps(sl, indent=1))
        # the picture sheet's "who it is for" and "the angle" are the video brief's, never re-asked
        rj = json.loads((Path(a.run) / "run.json").read_text()) if (Path(a.run) / "run.json").is_file() else {}
        bf = Path(rj.get("brief_from") or "")
        td = bf.parent.parent
        aud = (json.loads((td / "run.json").read_text()).get("audience") or {}) if (td / "run.json").is_file() else {}
        core = next((ln.split(":", 1)[1].strip() for ln in (bf.read_text().splitlines() if bf.is_file() else [])
                     if ln.startswith("Core message:")), "")
        who = " · ".join(x for x in (aud.get("_avatar"), aud.get("_sub_avatar")) if x)
        (out.parent / "06-brief.md").write_text(
            f"# Shot {a.section} start picture — from the video brief\n\n| | |\n|---|---|\n"
            f"| **For** | {who or 'the video brief audience'} |\n| **Core message** | {core or 'the video brief'} |\n")
        inj = out.parent / "03-injection.md"
        if not inj.is_file():   # the picture side asks for its brand step; a shot's swaps are the brief's, so this holds none
            feel = str((sl.get("feeling") or {}).get("emotion") or "").strip().lower()
            inj.write_text(f"# Shot {a.section} start picture — the swaps are the video brief's (swaps.json)\n\n"
                           f"**THE EMOTION:** `{feel}`\n\n**THE TECHNIQUES:** `true-scale-set`\n")
        print(f"written {out}")
    print(json.dumps(sl, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
