"""PICTURE SETS — a picture ad's scene built in 3D, at true sizes, before the picture is made (owner, 2026-10-28).

owner, on a flat-lay whose FLEX looked stuck on: "you're missing depth ... in the video work ... we built like a depth
map ... before we went into video production ... probably should do the same thing for just image ads ... the depth
model is inside of Higgsfield ... we've already done the work and established the stuff back through chains. So when
we run future workflows, stuff is faster."

The video line's way (video-production `machine/shot_sets.py`), for a still: the swipe's scene is laid out in Higgsfield
3D Jutsu with the product at its TRUE size (the product's own Jutsu build, recorded in its kit's
`model/sheet/jutsu/angles.json`), the swipe's camera and its light; the render is printed into a real photo with
`scene_builder_3d_generate_angles`, the product's casting sheet as the reference. The print is the picture's depth plate:
the board's picture call takes it as the layout, so sizes, depth, contact and light are programmed, not prompted.

One set per swipe, kept beside the run:

    runs/image-production/<brand>/sets/<set>/
        render-vN.png     the 3D render from the swipe's camera (sizes, depth, light)
        print-vN.png      the render printed into a real photo (the depth plate)
        set.json          the Jutsu project, the collection, the camera, the light, every render and print, and why

The scene code runs in the session's Higgsfield 3D Jutsu tools (scene_builder_3d_run_python on the product's project, a
collection `SET_<set>` whose objects are hidden from the product's own renders); this file records it and says what is
missing. Commands:

    python3 picture_sets.py show <brand> <set>          what the set has, and what it still needs
    python3 picture_sets.py print-words <brand> <run> [--set <set>] [--kind <kind>] [--bundle]     the first print's words, the prop's words read in;
                                                                        --kind adds the brand's product picture standard (picture_standard.py)
    python3 picture_sets.py put <brand> <set> --render F | --print F [--note "..."] [--run <run>] [--cast-board B.json]
    python3 picture_sets.py put <brand> <set> --original F --note "approved: <where it is live>"   (the edit lane's base)
    python3 picture_sets.py picture-from <brand> <set>                  the casting files a people set's print came from

THE 3D PRINT QUEUE (image_production/set_queue.py, 2026-11-10): every picture the set gate refuses is filed as a request;
the 3d-print skill (.claude/skills/3d-print/SKILL.md) clears it.
    python3 picture_sets.py queue [--brand <brand>]                     the requests waiting for a print
    python3 picture_sets.py plan <brand> <request>                      what to build and print for one, nothing spent
    python3 picture_sets.py request <brand> "<what>" [--name N] [--product P ...] [--cast ELEMENT ...]
    python3 picture_sets.py done <brand> <request> --set <set>          mark it printed; prints the step to run again
    python3 picture_sets.py signage <brand>                             write the prop's words into every set that lacks them
    python3 picture_sets.py put-change <set-request.json> --render F --print F --note "kept: ..."

A variation of a picture with a kept set is that set changed (2026-10-30; stage 5 v9 writes each row as a set change:
object, real size, place, material): `kept` finds the run's set, `change_request` turns the row into what a session
needs to build and print it, nothing spent, and the print is filed as its own small set `<set>--<variation>` with
`put_change`. That set never names the run in `runs`, so the run's own print stays the run's picture; `kept_change`
hands image-edit the print once it is there.

The words on a prop travel on their own (2026-10-30): `signage_for` reads them from the run, so nobody types them and the
print's no-writing line never wipes a flag. THE SET block of the brief (stage 6 v12, `props[].signage`) wins; a run made
before it has them in its swap rows or stage 3's art direction ("printed BLACK FRIDAY"). A run filed with `put --run` keeps
them in its set.json.

A print carries the set's people and none of the board's type (2026-11-07). A kept set that shows a person (a `cast` swap
row, the record's `people`, the row's `person`) keeps that person in every print of it: "No people, no hands" is said only
when the set has none, or the print drops the person or turns her legs into grey tubes. The drawn rows that are the
overlay's own type and graphics (a wordmark, a badge, the rules, a headline) are the board's type layer, set on top after
the print; printed too, they show twice. Only the words on a real prop (`signage`) are printed.
"""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
from image_production import paths as P  # noqa: E402

def _pv():
    from image_production import provenance
    return provenance


def stamp_kept(brand):
    """Every kept print of the brand's sets gets the tool's record (for prints filed before `put` stamped them,
    2026-11-24). A print already on record is left as it is. Returns the files stamped."""
    pv, done = _pv(), []
    base = P.repo() / "runs" / "image-production" / brand / "sets"
    for sj in sorted(base.glob("*/set.json")) if base.is_dir() else []:
        try:
            r = json.loads(sj.read_text())
        except ValueError:
            continue
        for row in r.get("prints") or []:
            f = sj.parent / row.get("file", "")
            if str(row.get("note", "")).startswith("kept") and f.is_file() and not pv.known(f):
                pv.set_print(f, brand=brand, set_name=sj.parent.name)
                done.append(str(f))
    return done


PRINT_CREDITS = 1.25    # one print, scene_builder_3d_generate_angles at 1.5k; the set and its renders are free
STORE_PRINT_CREDITS = 2.5   # a store picture (a kind of the brand's picture standard) is printed at 2k


def print_size(kind=None):
    """(resolution, credits) of one print (2026-11-25). Everything delivered at 1080x1920 is printed at 1.5k, half the
    credits of 2k and still larger than the finished file; a store picture keeps 2k."""
    return ("2k", STORE_PRINT_CREDITS) if kind else ("1.5k", PRINT_CREDITS)



def home(brand, name):
    return P.repo() / "runs" / "image-production" / brand / "sets" / name


def record(brand, name):
    f = home(brand, name) / "set.json"
    return json.loads(f.read_text()) if f.is_file() else {}


def needs(brand, name):
    """What the set is missing before a picture may use it, in plain words."""
    r, d = record(brand, name), home(brand, name)
    out = []
    if not r.get("project"):
        out.append("no 3D Jutsu project recorded")
    if not sorted(d.glob("render-v*.png")):
        out.append("no render from the swipe's camera")
    if not sorted(d.glob("print-v*.png")):
        out.append("no print (the render printed into a real photo with the product's casting sheet)")
    return out


def print_prompt(scene):
    """The print step's words, built the same way every time (research/diffusion-fundamentals.md rule 9: keep structure,
    change materials). `scene`: {shot, light, objects: [what each object really is, its material], product: the product's
    look line from its casting sheet, size_cm, people_none: True, signage: [{prop, words}] — the moment's name on a real
    prop, the only writing besides the product's label}. The render owns the layout; the words only say what each
    grey shape really is."""
    second = ("the second is a sheet of real studio photographs of the product in it, which supplies the product's materials "
              "and details" if scene.get("product") and not scene.get("reference_says") else (scene.get("reference_says") or "the second is the reference picture, "
              "which supplies only the photo quality, skin, hair and material textures, never its faces, layout or writing"))
    lines = [f"Two inputs: the first is a clean 3D blockout of {scene['shot']}; {second}. Keep the blockout's camera, layout, "
             "framing, sizes, depth and light exactly; nothing of the blockout's grey materials carries over.",
             f"The light: {scene['light']}."]
    lines += [o.rstrip(".") + "." for o in scene.get("objects") or []]
    # the set's people (2026-11-07): a kept set that shows a person keeps her; without this line the print's no-people
    # rule dropped her or drew her legs as the blockout's grey tubes (brand_b buzzfeed v2, v5)
    people = [str(x).rstrip(".") for x in scene.get("people") or [] if x]
    has_people = bool(people) or scene.get("people_none") is False
    if has_people:
        lines.append("The people are real people, each exactly where the blockout places the figure, in its pose and at its size, "
                     "no bigger: " + ("; ".join(people) + ". " if people else "") +
                     "Real skin and real anatomy; the blockout's grey figure shapes are only their place and size, never their form.")
    lines += scene.get("creative") or []
    # real skin on every print that shows skin (owner, 2026-11-26): the skin bank's patches ride on the reference board
    if scene.get("skin"):
        from image_production import skin_bank
        lines.append(skin_bank.PRINT_WORDS)
    if scene.get("product"):
        size = f", {scene['size_cm']} cm long" if scene.get("size_cm") else ""
        lines.append(f"The product is exactly as the reference sheet shows it: {scene['product']}{size}, its own printed label "
                     "and marks exactly as on the sheet, on every one of them. The product in the blockout is its own true 3D build: keep "
                     "its shape, pose, size and how it rests exactly; its materials, colours, label and marks come from the sheet.")
        lines += [f"Always: the product with {str(a).rstrip('.')}." for a in scene.get("product_always") or []]
        never = [str(x.get("what") if isinstance(x, dict) else x).rstrip(".") for x in scene.get("product_never") or [] if x]
        if never:
            lines.append("Never: " + "; ".join(never) + ".")
    # the set's own signage (2026-10-30): the moment's name printed on a real prop (a flag, a sign, a tag), built into
    # the set and printed with it, so it sits on the prop's surface with its light. `signage`: [{prop, words}]
    signs = [s for s in scene.get("signage") or [] if s.get("prop") and s.get("words")]
    for s in signs:
        lines.append(f"The {s['prop'].rstrip('.')} carries the printed words \"{s['words']}\", letter for letter, in plain "
                     "bold letters printed on its surface, lit and shadowed like the prop itself.")
    # "no logos" here wiped the product's own label off every tube (2026-10-28): only OTHER writing is barred
    allowed = "the product's own label" + (" and the words named on the props above" if signs else "")
    # THE AD'S STYLE (owner ruling, 12 Nov 2026; video-production styles/style_chain.py): a print for an ad in a
    # non-photoreal style is rendered in that style, its formula verbatim; identity still comes from the references
    look = ("A real, unretouched photograph, natural grain." if not scene.get("style_formula") else
            f"Rendered entirely in this style: {scene['style_formula']}. Never photoreal; who each person is, what they "
            "wear and every mark, and what the product looks like, still come exactly from the references.")
    lines.append(look + ("" if has_people or scene.get("people_none") is False else " No people, no hands.")
                 + f" No writing anywhere except {allowed}.")
    return " ".join(lines)


# the overlay's own type and graphics (2026-11-07): the board sets these on top of the print (its type layer, the set's
# `design.fixed`), so a print that draws them shows them twice (buzzfeed v1, v3, v4: a second wordmark, an "EA·ASK" badge).
# "no logo" is a material, not a mark; a row that prints words on a real prop is signage and stays.
OVERLAY = re.compile(r"(?<!\bno )(?<!\bwithout )\b(?:word ?marks?|logos?|logotypes?|lock-?ups?|monograms?|badges?|mastheads?|"
                     r"headlines?|sub-?head(?:line)?s?|captions?|bylines?|stickers?|text box(?:es)?|link rows?|nav(?:igation)? (?:bar|row)s?|"
                     r"hamburger(?: icon)?|watermarks?|hashtags?|(?:horizontal|vertical|hairline|divider) rules?|dividers?|"
                     r"\d+(?:\.\d+)? ?px)\b", re.I)


def overlay_type(row):
    """True when a drawn swap row is the overlay's own type or graphics (a wordmark, a badge, a rule, a headline), not a
    thing in the photographed scene. Read off the row's `to`: what the print would be told to draw."""
    to = str(row.get("to") or "")
    return bool(OVERLAY.search(to)) and not _words_in(to)


def scene_rows(rows):
    """The drawn swap rows a print draws: every drawn row except the overlay's type. Returns (kept, left_out)."""
    drawn = [x for x in rows or [] if x.get("kind") == "drawn" and x.get("to")]
    return [x for x in drawn if not overlay_type(x)], [x for x in drawn if overlay_type(x)]


def people_in(rows, *more):
    """The people the set shows, as the print's words: each `cast` swap row's `to`, then any other description given
    (`more`: the record's `people`, the brief's, a row's `person`). Strings and lists both count; a bare flag such as
    "made-up" or True means people with no words of their own and gives an empty description."""
    out = [str(x["to"]) for x in rows or [] if x.get("kind") == "cast" and x.get("to")]
    for m in more:
        if isinstance(m, dict):
            m = ", ".join(str(v) for v in m.values() if v)
        for x in (m if isinstance(m, (list, tuple)) else [m]):
            if isinstance(x, str) and len(x.split()) > 2 and x not in out:
                out.append(x)
    return out


def run_home(brand, run):
    """The run's out folder: its one home, else the old one a run made before 2026-10-28 sits in."""
    for d in (P.repo() / "runs" / "image-teardown" / brand / run / "out", P.repo() / "components" / "image-teardown" / "runs" / run / "out"):
        if d.is_dir():
            return d
    return None


def the_set(brand, run):
    """THE SET block of the run's brief (stage 6 v12: the json block with one key, `set`), or None."""
    d = run_home(brand, run) if run else None
    f = d / "06-brief.md" if d else None
    if not f or not f.is_file():
        return None
    for m in re.finditer(r"```json\s*(.*?)```", f.read_text(), re.S):
        try:
            block = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(block, dict) and isinstance(block.get("set"), dict):
            return block["set"]
    return None


PRINTED = re.compile(r"(?:printed|lettered|stencil(?:l)?ed|reading|reads|says)(?:\s+with|\s+in|\s+the\s+words)?[\s:]+[\"“]?"
                     r"([A-Z0-9][A-Z0-9%$&'’.!-]*(?:\s+[A-Z0-9%$&'’.!-]+)*)")


def _words_in(text):
    """A prop's name and its words out of a line of prose ("a black desk flag on the dowel, printed BLACK FRIDAY in big
    plain letters"), or None. Only capitals count: "printed in soft ink" is a material, not a sign."""
    m = PRINTED.search(text or "")
    words = m.group(1).strip() if m else ""
    if len(words) < 2:
        return None
    prop = re.split(r",|\s+(?:on|with|in|at|lying|printed|lettered|reading|reads|says)\s", text[:m.start()].strip(" -*•\t"))[0]
    return {"prop": re.sub(r"^(?:an?|the)\s+", "", prop.strip(), flags=re.I) or "prop", "words": words}


def signage_for(brand, run, rows=None):
    """The words printed on the run's props: [{prop, words}]. `rows` are swap rows when the caller already has them."""
    block = the_set(brand, run)
    if block is not None:
        return [{"prop": str(p.get("what") or "prop"), "words": str(p["signage"])} for p in block.get("props") or [] if p.get("signage")]
    d = run_home(brand, run) if run else None
    if rows is None and d and (d / "swaps.json").is_file():
        rows = json.loads((d / "swaps.json").read_text()).get("swaps")
    found = [_words_in(x.get("to")) for x in rows or [] if x.get("kind") == "drawn"]
    if not any(found) and d and (d / "03-injection.md").is_file():
        text = (d / "03-injection.md").read_text()
        art = re.search(r"THE ART DIRECTION(.*?)(?:\n\*\*\d+\.|\Z)", text, re.S)
        found = [_words_in(line) for line in (art.group(1).splitlines() if art else [])]
    return [x for x in found if x]


def creative(brand, run):
    """The brief's concept and its dial levels as print lines, so a print carries what the writing asked for (2026-10-31:
    a print is made outside the board's prompt builder, so the dials never reached it). The picture words are the dials'
    own, from model-inputs picture-dials.json: a dial's `set` words at that level, else its `levels` words."""
    d = run_home(brand, run)
    f = d / "03-injection.md" if d else None
    if not f or not f.is_file():
        return []
    t = f.read_text()
    out = []
    for label, say in (("THE CONCEPT", "The concept of this picture"), ("HOW IT DRESSES THE FRAME", "How the concept dresses the scene")):
        m = re.search(rf"\*\*{label}:\*\*\s*(.+)", t)
        if m:
            out.append(f"{say}: {m.group(1).strip()}")
    dials = json.loads((HERE.parent / "model-inputs" / "picture-dials.json").read_text())["dials"]
    look = []
    for dial, level in re.findall(r"(?m)^[-*]\s*`?([a-z_]+):[^\n]*?ours (\d)", t):
        row = dials.get(dial) or {}
        if row.get("send") == "picture" and level != "0":
            word = (row.get("set") or {}).get(level) or (row.get("levels") or {}).get(level)
            if word and word not in look:
                look.append(word)
    return out + look


def first_print(brand, run, name=None, kind=None, bundle=False):
    """The first print's words, built from the run's own brief: THE SET block when it has one, else the set's record and
    the swap rows. Spends nothing, files nothing. `kind` (a product picture kind in the brand's picture standard,
    picture_standard.py: shop-card, gallery, offer-icon) adds the standard's lines; the set's record may name it as
    `picture_kind`."""
    block = the_set(brand, run) or {}
    r = record(brand, name) if name else {}
    d = run_home(brand, run)
    sw = json.loads((d / "swaps.json").read_text()) if d and (d / "swaps.json").is_file() else {}
    rows = sw.get("swaps") or []
    cam = block.get("camera") or {}
    camera = ", ".join(x for x in (f"{cam['lens_mm']} mm" if cam.get("lens_mm") else "", f"{cam['height_cm']} cm high" if cam.get("height_cm") else "",
                                   f"{cam['distance_cm']} cm away" if cam.get("distance_cm") else "", str(cam.get("angle") or "")) if x)
    light = "; ".join(", ".join(str(v) for v in x.values() if v) for x in block.get("light") or [] if isinstance(x, dict))
    objects = [", ".join(str(x[k]) for k in ("what", "material") if x.get(k)) for x in (block.get("surfaces") or []) + (block.get("props") or [])]
    objects = [x for x in objects if x] or [str(x["to"]) for x in scene_rows(rows)[0]]
    if block.get("print"):
        objects.append(str(block["print"]))
    # the block may carry the product's display name, not its kit slug (2026-11-26: the FLEX lost its kit lines that way)
    product = next((p for p in (_product(brand, k) for k in ((block.get("product") or {}).get("kit"), sw.get("product_kit")) if k) if p), {})
    signage = r.get("signage") or signage_for(brand, run, rows)
    people = people_in(rows, block.get("people"), r.get("people"))
    scene = {"shot": camera or r.get("camera") or r.get("what") or "the swipe's scene", "light": light or r.get("light") or "exactly as the blockout shows it",
             "objects": objects, "creative": creative(brand, run), "product": product.get("what"), "size_cm": product.get("size_cm"), "signage": signage,
             "people": people, "people_none": not people,
             # how the owner always wants the product shown, never shown and never able to do (kit.json; 2026-11-26: the
             # FLEX's ring light always glowing, and it never stands on its own) — on every first print, not only variations
             "product_always": product.get("always") or [], "product_never": (product.get("never_show") or []) + (product.get("cannot") or [])}
    # the brand's product picture standard (2026-11-07): a product picture names its kind and carries the standard's lines
    kind = kind or r.get("picture_kind") or block.get("picture_kind")
    if kind:
        import picture_standard
        scene["creative"] = list(scene["creative"] or []) + picture_standard.lines(brand, kind, bundle or bool(r.get("bundle")))
    scene["skin"] = shows_skin(people, scene_rows(rows)[0], {k: block.get(k) for k in ("surfaces", "props", "people", "print")})
    skin = skin_pick(rows, block) if scene["skin"] else []
    return {"run": run, "set": name, "signage": signage, "people": people, "product": product, "creative": scene["creative"],
            "skin": skin, "print_words": print_prompt(scene)}


# bare skin in the scene; people are caught by people_in, and a product name ("face brush") is not skin
SKIN_SHOWN = re.compile(r"(?i)\b(?:bare skin|his skin|her skin|cheeks?|necks?|jaw|jawline|forehead|chin|scalp|pores?|acne|"
                        r"pimples?|bumps|breakouts?|dark (?:marks?|spots?)|stubble)\b")


def shows_skin(people=None, *more):
    """True when the set shows a person or bare skin: then the print and its filing need the skin bank."""
    return bool(people) or bool(SKIN_SHOWN.search(json.dumps([m for m in more if m], ensure_ascii=False, default=str)))


def skin_pick(*more):
    """The skin bank rows (a customer crop + a macro shot) for this set, as {file, kind, condition}; put them on the
    reference board beside the casting sheet or cast board (cast_board.py refs) and name them in `put`'s trail as `skin`."""
    from image_production import skin_bank
    text = json.dumps([m for m in more if m], ensure_ascii=False, default=str).lower()
    # the condition the scene names most, and the skin tone it names (a set may say "razor" in passing about acne)
    conds = {"acne": r"\bacne|pimples?|breakouts?", "razor bumps": r"razor bumps?|ingrown|bumps on (?:his|the) neck",
             "dark marks": r"dark (?:marks?|spots?)|post-acne", "pores": r"\bpores?\b|blackheads?|oily"}
    hits = sorted(((len(re.findall(rx, text)), c) for c, rx in conds.items()), reverse=True)
    cond = hits[0][1] if hits and hits[0][0] else "clear"
    tones = [("deep-brown", r"deep (?:dark )?brown|very deep skin|\bblack man|african.american"), ("dark-brown", r"dark brown"),
             ("medium-brown", r"medium.brown"), ("light-brown", r"light.brown"), ("olive", r"\bolive"), ("fair", r"\bfair|pale|white\b skin")]
    tone = next((t for t, rx in tones if re.search(rx, text)), None)
    return [{"file": "runs/ai-elements/_texture-refs/" + x["file"], "kind": x.get("kind"), "condition": x.get("condition")}
            for x in skin_bank.pick(cond, tone)]


def _nothing_to_cast(brand, name):
    """True when this set's own request names no product and no person: its print has no casting sheet to take."""
    try:
        from image_production import set_queue as Q
        req = Q.read(brand, str(name)) or {}
    except Exception:
        return False
    return bool(req) and "products" in req and not req.get("products") and not req.get("cast")


def put(brand, name, render=None, printed=None, note="", run=None, cast_board=None, original=None, trail=None):
    d = home(brand, name)
    d.mkdir(parents=True, exist_ok=True)
    r = record(brand, name)
    if cast_board:
        _put_board(brand, d, r, Path(cast_board))
    # the one reference a print takes is the whole casting sheet; a crop of it or a photo pasted on is a side path (2026-10-31)
    # a people or style print's one reference is the board its plan builds (cast_board.py build / refs), never a crop
    ref = str((trail or {}).get("reference") or (r.get("print") or {}).get("reference") or "")
    board = bool(re.search(r"(-cast-board|-reference|skin-board)\.png$", ref))   # skin-board: the skin bank's reference (2026-11-26)
    # a prop print has no product in it, so no product casting sheet to name (2026-11-20: a kept prop print was refused);
    # nor has a set whose request names no product and no person (2026-11-21: a right print of an empty column was refused)
    if printed and note.startswith("kept") and r.get("print") and "casting sheet" not in ref and not board \
            and not str(name).startswith("prop-") and not _nothing_to_cast(brand, name):
        raise ValueError(f"{name}: a kept print needs the product casting sheet as its reference, not: {r['print'].get('reference')}")
    if printed and note.startswith("kept"):
        own_build(brand, name, r, trail, run)
        real_skin(brand, name, r, trail, run, note)
    if run:
        r["runs"] = sorted(set(r.get("runs") or []) | {run})
        r["signage"] = r.get("signage") or signage_for(brand, run)
    # an approved original: a picture already approved or live, filed so the edit lane can edit it (set_gate.py, 2026-11-10)
    if original and not note.startswith("approved"):
        raise ValueError(f"{name}: an original is filed with a note starting \"approved\" (where it is approved or live)")
    for kind, src in (("render", render), ("print", printed), ("original", original)):
        if not src:
            continue
        ext = Path(src).suffix.lower() if kind == "original" else ".png"
        n = len(sorted(d.glob(f"{kind}-v*.*"))) + 1
        dst = d / f"{kind}-v{n}{ext}"
        shutil.copy(src, dst)
        row = {"file": dst.name, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "note": note}
        if kind == "print" and trail:              # where the print came from: Jutsu project, generation, reference, words
            row.update({k: v for k, v in trail.items() if v})
            if trail.get("project"):
                r.setdefault("project", {"id": trail["project"], "url": "https://higgsfield.ai/3d-jutsu/" + trail["project"]})
            if trail.get("reference"):
                r.setdefault("print", {})["reference"] = r.get("print", {}).get("reference") or trail["reference"]
        r.setdefault(kind + "s", []).append(row)
        if kind == "print" and note.startswith("kept"):   # the kept print IS the picture (GATE-4): the tool's record
            row["sha256"] = _pv().set_print(dst, brand=brand, set_name=name)
    (d / "set.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
    if printed and not note.startswith("kept"):
        _release(brand, name, note)
    return d


def set_product(brand, r, run=None):
    """The product a set shows, from its runs' THE SET block or swaps, or {}."""
    for rn in [run] + list(r.get("runs") or []):
        if not rn:
            continue
        block = the_set(brand, rn) or {}
        d = run_home(brand, rn)
        sw = json.loads((d / "swaps.json").read_text()) if d and (d / "swaps.json").is_file() else {}
        for slug in ((block.get("product") or {}).get("kit"), sw.get("product_kit")):   # the block may carry a display name
            p = _product(brand, slug) if slug else {}
            if p:
                return p
    return {}


def real_skin(brand, name, r, trail=None, run=None, note=""):
    """A kept print that shows a person or bare skin names the skin bank rows it was printed with (`trail["skin"]`)
    (owner, 2026-11-26: plastic skin on every acne and razor-bump print). Refuses otherwise."""
    if (trail or {}).get("skin"):
        return True
    rows, block = [], {}
    for rn in [run] + list(r.get("runs") or []):
        if rn:
            block = the_set(brand, rn) or {}
            d = run_home(brand, rn)
            rows = (json.loads((d / "swaps.json").read_text()).get("swaps") or []) if d and (d / "swaps.json").is_file() else []
            break
    if shows_skin(people_in(rows, block.get("people"), r.get("people")), scene_rows(rows)[0],
                  {k: block.get(k) for k in ("surfaces", "props", "people", "print")}, note):
        raise ValueError(f"{name}: this print shows skin, so it is printed with the skin bank's real texture on its "
                         "reference (picture_sets first_print gives the rows) and filed with trail skin=[those files]")
    return True


def own_build(brand, name, r, trail=None, run=None):
    """A kept print showing a product is printed in the product's OWN 3D Jutsu project, where its true build lives
    (2026-11-26: a set built in a new project with a hand-made egg and an invented stand printed a FLEX that did not look
    like the FLEX; brand_b never hit it because a jar or a tube hand-built reads the same). Refuses otherwise."""
    p = set_product(brand, r, run)
    want = p.get("jutsu_project")
    # never a hand-made product, any brand (owner, 2026-11-26): a product with no true 3D build gets one first
    if p and not want:
        raise ValueError(f"{name}: {p.get('kit')} has no true 3D build yet (model/sheet/jutsu/angles.json); build it first, "
                         "never a hand-made stand-in")
    got = (trail or {}).get("project") or (r.get("project") or {}).get("id") if isinstance(r.get("project"), dict) \
        else (trail or {}).get("project") or r.get("project")
    if want and got and got != want:
        raise ValueError(f"{name}: the {p.get('kit')} print was made in 3D project {got}, not the product's own build "
                         f"project {want}; build the set there with the real product (never a hand-made stand-in)")
    return True


def _release(brand, name, note):
    """A print filed as wrong has been read back and filed: its request's printing hold is cleared, so the request waits
    for its next round (set or words fixed) instead of being read back again and again (2026-11-21: three wrong prints
    of brief-0380 kept their holds, and the runner could only read them back, never print the fixed set)."""
    try:
        from image_production import set_queue as Q
        if (Q.read(brand, str(name)) or {}).get("printing"):
            Q.printing(brand, str(name), clear="filed not kept: " + str(note)[:160])
    except (Exception, SystemExit):  # noqa: BLE001 -- no request of that name: nothing to release
        pass


def _put_board(brand, d, r, board_json):
    """A people set's print reference is its cast board (cast_board.py, 2026-11-10): the board and its record are copied
    in, the print's reference names it, and `picture_from` (every casting file on it, with sha256) goes into set.json for
    the Video Studio's old-element check. A board whose casting files changed since it was built is refused."""
    import cast_board as CB
    rec = json.loads(board_json.read_text())
    stale = CB.check(rec, brand)
    if stale:
        raise ValueError(f"{d.name}: the cast board is out of date ({'; '.join(stale)}); rebuild it with cast_board.py build")
    png = board_json.with_name(rec["board"])
    shutil.copy(png, d / "cast-board.png")
    (d / "cast-board.json").write_text(json.dumps(dict(rec, board="cast-board.png"), indent=1, ensure_ascii=False))
    r["cast_board"] = {"file": "cast-board.png", "sha256": rec["board_sha256"], "order": rec["order"]}
    r["picture_from"] = rec["picture_from"]
    r.setdefault("print", {})["reference"] = rec["print_reference"]


def picture_from(brand, name):
    """The casting files a people set's print was made from ([{element, file, sha256}]): a take's `params.picture_from`."""
    return record(brand, name).get("picture_from") or []


def kept(brand, run):
    """The run's set and its newest kept print: {set, print, record}, or None. The same find as model-inputs
    `preview.set_print`, which the board's first picture uses."""
    base = home(brand, "x").parent
    for sj in sorted(base.glob("*/set.json")) if run and base.is_dir() else []:
        try:
            d = json.loads(sj.read_text())
        except ValueError:
            continue
        if run in (d.get("runs") or []):
            prints = [p for p in d.get("prints") or [] if str(p.get("note", "")).startswith("kept") and (sj.parent / p["file"]).is_file()]
            if prints:
                return {"set": sj.parent.name, "print": sj.parent / prints[-1]["file"], "record": d,
                        "words": prints[-1].get("words")}
    return None


def fill_signage(brand):
    """Write the prop's words into every set of the brand that names a run and has none recorded. Returns the sets changed."""
    base = home(brand, "x").parent
    changed = []
    for sj in sorted(base.glob("*/set.json")) if base.is_dir() else []:
        d = json.loads(sj.read_text())
        found = [x for run in d.get("runs") or [] for x in signage_for(brand, run)]
        if found and not d.get("signage"):
            d["signage"] = found
            sj.write_text(json.dumps(d, indent=1, ensure_ascii=False))
            changed.append(sj.parent.name)
    return changed


def change_words(change):
    """The row's one change as one sentence: its `picture`, else its swap rows, else the person it brings."""
    one = (change.get("picture") or "").strip().rstrip(".")
    rows = "; ".join(f"{r.get('from')} becomes {r.get('to')}" for r in change.get("swap") or [])
    who = ", ".join(str(x) for x in (change.get("person") or {}).values() if x)
    return one or rows or who


def _product(brand, slug):
    """What the print needs from the product's kit, or {} when this brief has no kit on this machine."""
    from image_production import product3d
    kit = product3d.find_kit(brand, slug) if slug else None
    if not kit:
        return {}
    k = json.loads((kit / "kit.json").read_text())
    size = k.get("size_cm")
    longest = max([v for v in size.values() if isinstance(v, (int, float))] or [0]) if isinstance(size, dict) else size
    jutsu = kit / "model" / "sheet" / "jutsu" / "angles.json"
    proj = (json.loads(jutsu.read_text()).get("project") or {}) if jutsu.is_file() else {}
    sheet = kit / str((k.get("sheet") or {}).get("file") or "model/product-sheet.png")
    return {"kit": kit.name, "what": k.get("what"), "size_cm": longest or None, "jutsu_project": proj.get("id"),
            "sheet": P.rel(sheet) if sheet.is_file() else None,
            "rests": (k.get("behaviour") or {}).get("rests"), "never_show": (k.get("behaviour") or {}).get("never_show"),
            "cannot": (k.get("behaviour") or {}).get("cannot"), "label_words": k.get("label_words"),
            "always": [x.get("line") if isinstance(x, dict) else x for x in (k.get("always") or [])]}


def change_request(brand, found, variation, change, brief):
    """One variation row as a set change: what a session building it in Higgsfield 3D Jutsu needs and the print's words.
    Spends nothing and files nothing. `found` is `kept`'s answer; `brief` the variation's brief, its swap list already
    carrying the row's swaps, so each object in the print's words is what it is after the change."""
    r, name = found["record"], found["set"]
    project = r.get("project") if isinstance(r.get("project"), dict) else {"id": r.get("project")}
    the_change = change_words(change)
    product = _product(brand, brief.get("product") or brief.get("product_slug"))
    rows = (brief.get("swap_list") or {}).get("swaps") or []
    flag = change.get("people") or brief.get("people") or change.get("person") or r.get("people")
    people = people_in(rows, r.get("people"), brief.get("people"), change.get("people"), change.get("person"))
    signage = r.get("signage") or signage_for(brand, brief.get("run"), rows or None)
    drawn, overlay = scene_rows(rows)
    # a row that changes the set's own lettering: a swap line that still names the old words would fight it
    if signage and change.get("picture") and "lettering" in change.get("picture"):
        olds = re.findall(r'"([^"]+)" now reads', change.get("picture"))
        drawn = [x for x in drawn if not any(o.lower() in str(x.get("to") or "").lower() for o in olds)]
    # what the product's kit says it always is, never does and never carries, as the main print plan says it (set_queue)
    pname = product.get("what") or "the product"
    creative = [f"Always: {pname}, {a}." for a in product.get("always") or []]
    creative += [f"Never: {pname}, {c}." for c in (product.get("cannot") or []) + (product.get("never_show") or [])]
    if product.get("label_words") == []:
        creative.append(f"{pname[:1].upper() + pname[1:]} carries no printed words or wordmark anywhere the reference sheet "
                        "does not show them; never add letters to it.")
    # the winner's own set as its first print described it (2026-11-23: from the record's short summary alone, a
    # variation lost the winner's foreground glass and wall): THE SET block's camera, light, surfaces and props, and the
    # brief's creative lines, then the drawn swaps and the one change
    block = (the_set(brand, brief.get("run")) or {}) if brief.get("run") else {}
    cam = block.get("camera") or {}
    camera = ", ".join(x for x in (f"{cam['lens_mm']} mm" if cam.get("lens_mm") else "", f"{cam['height_cm']} cm high" if cam.get("height_cm") else "",
                                   f"{cam['distance_cm']} cm away" if cam.get("distance_cm") else "", str(cam.get("angle") or "")) if x)
    light = "; ".join(", ".join(str(v) for v in x.values() if v) for x in block.get("light") or [] if isinstance(x, dict))
    set_objects = [", ".join(str(x[k]) for k in ("what", "material") if x.get(k)) for x in (block.get("surfaces") or []) + (block.get("props") or [])]
    if block.get("print"):
        set_objects.append(str(block["print"]))
    if block and brief.get("run"):
        try:
            creative = list(globals()["creative"](brand, brief["run"]) or []) + creative
        except (OSError, ValueError, KeyError, TypeError):
            pass
    scene = {"shot": camera or r.get("camera") or r.get("what") or "the kept set", "light": light or r.get("light") or "exactly as the blockout shows it",
             "objects": [x for x in set_objects if x] + [str(x["to"]) for x in drawn] + [the_change],
             "product": product.get("what"), "size_cm": product.get("size_cm"), "signage": signage,
             "people": people, "people_none": not (people or flag), "creative": creative}
    flags = []
    if not re.search(r"\d\s*(cm|centimet)", the_change, re.I):
        flags.append("the change names no real size in centimetres: read it off the swipe or the set before building")
    if not signage:
        flags.append("no signage found in the set, the brief or the swaps: if the kept print has words on a prop, name them "
                     "in the set's `signage`, or the print's no-writing line takes them off")
    if not product.get("sheet"):
        flags.append("no product casting sheet found: a product in this set is never printed from words")
    child = f"{name}--{variation}"
    base = project.get("collection") or f"SET_{name}"
    return {"set": child, "variation_of": name, "run": brief.get("run"), "variation": variation, "brand": brand,
            "change": the_change, "project": project, "collection": re.sub(r"\W+", "_", f"{base}_{variation}"),
            "base_collection": base, "camera": r.get("camera"), "light": r.get("light"), "sizes": r.get("sizes"),
            "signage": signage, "people": people, "overlay_left_out": [str(x["to"]) for x in overlay],
            "kept_print": P.rel(found["print"]), "product": product,
            "print_words": from_kept(found.get("words"), change.get("picture") or the_change, creative) or print_prompt(scene),
            "words_from": "the kept print's own words, one change" if found.get("words") else "the set described",
            "credits": PRINT_CREDITS, "flags": flags,
            "steps": [f"Copy the collection {base} to the new collection and leave the original as it is.",
                      "Make only the change, at its real size and place, and hide the original collection.",
                      "Render inside a scene edit, from the same camera and light, with only this set's collection on and "
                      "the project's loose root objects hidden (2026-11-23: a shared project's raised room light and a "
                      "leftover product model changed the blockout); put the render beside the kept render and match it "
                      "before printing.",
                      "Upload the product casting sheet fresh, then print with scene_builder_3d_generate_angles at 9:16, 1.5k, "
                      "using print_words.",
                      "File it: picture_sets.py put-change <this file> --render R --print P --note 'kept: ...'"]}


def from_kept(words, change, creative=()):
    """A variation's print words when the winner's kept print has its own words on record (2026-11-23: words rebuilt from
    the run's first concept gave a different setting than the picture that ran). The kept print's words exactly, the one
    change applied: a lettering change swaps the old words for the new where the words spell them out; any other change is
    named once at the end. The product's `Always` lines missing from the old words are added. None when there are none."""
    if not words:
        return None
    out = str(words).rstrip()
    swaps = re.findall(r'"([^"]+)" now reads "([^"]+)"', change or "")
    done = False
    for old, new in swaps:
        # where the words spell the lettering out ("exactly BLACK FRIDAY", "reads \"...\""), only there: the concept
        # line naming the moment is not lettering
        for hit in (re.compile(r'((?:exactly|reads|words)\s+["\u201c]?)' + re.escape(old), re.I),
                    re.compile(r'(["\u201c])' + re.escape(old) + r'(?=["\u201d])', re.I)):
            if hit.search(out):
                out, done = hit.sub(lambda m: m.group(1) + new, out), True
                break
    if not done:
        out += f" The one change from this picture as it was made: {str(change).strip().rstrip('.')}. Everything else stays exactly as it was."
    for line in creative:
        if line.startswith("Always:") and line not in out:
            out += " " + line
    return out


def put_change(request, render=None, printed=None, note=""):
    """File a variation's print as its own set, `<set>--<variation>`. It never names the run in `runs`."""
    brand, name = request["brand"], request["set"]
    d = home(brand, name)
    d.mkdir(parents=True, exist_ok=True)
    r = {**record(brand, name), **{k: request.get(k) for k in ("variation_of", "run", "variation", "change", "project", "collection", "signage")}}
    r.pop("runs", None)
    (d / "set.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
    return put(brand, name, render, printed, note)


def kept_change(brand, name, variation, the_change):
    """The kept print of this variation's own set, or None. A print made for different words is not this row's print."""
    child = f"{name}--{variation}"
    r, d = record(brand, child), home(brand, child)
    if r.get("change") != the_change:
        return None
    prints = [p for p in r.get("prints") or [] if str(p.get("note", "")).startswith("kept") and (d / p["file"]).is_file()]
    return d / prints[-1]["file"] if prints else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("brand"); s.add_argument("set")
    p = sub.add_parser("put"); p.add_argument("brand"); p.add_argument("set")
    p.add_argument("--render"); p.add_argument("--print", dest="printed"); p.add_argument("--note", default=""); p.add_argument("--run")
    p.add_argument("--cast-board", dest="cast_board", help="a people set: the cast_board.py board.json the print was made from")
    p.add_argument("--project", help="the 3D Jutsu project the set is built in"); p.add_argument("--generation", help="the print's generation id")
    p.add_argument("--reference", help="the one reference picture the print took"); p.add_argument("--skin", nargs="*", help="the skin bank files on the print's reference (a print that shows skin)"); p.add_argument("--words", help="the print's words, or @file")
    p.add_argument("--original", help="an approved or live picture, filed as the edit lane's base (note starts \"approved\")")
    f = sub.add_parser("picture-from"); f.add_argument("brand"); f.add_argument("set")
    q = sub.add_parser("queue"); q.add_argument("--brand")
    pl = sub.add_parser("plan"); pl.add_argument("brand"); pl.add_argument("request")
    rq = sub.add_parser("request"); rq.add_argument("brand"); rq.add_argument("what"); rq.add_argument("--name")
    rq.add_argument("--product", action="append", default=[]); rq.add_argument("--cast", action="append", default=[])
    dn = sub.add_parser("done"); dn.add_argument("brand"); dn.add_argument("request"); dn.add_argument("--set", dest="set_name", required=True)
    ro = sub.add_parser("reopen", help="open done requests again for a new print; their kept prints are retired")
    ro.add_argument("brand"); ro.add_argument("request", nargs="+"); ro.add_argument("--why", required=True)
    pr = sub.add_parser("printing", help="record a print as sent (no second print of the request), or --clear it")
    pr.add_argument("brand"); pr.add_argument("request"); pr.add_argument("--project"); pr.add_argument("--generation")
    pr.add_argument("--account"); pr.add_argument("--credits-before", dest="credits_before", type=float)
    pr.add_argument("--clear", help="the reason the print was not taken (frees the request to print again)")
    sub.add_parser("ready", help="is this machine ready for the 3D route? (Higgsfield command line found + signed in)")
    w = sub.add_parser("print-words"); w.add_argument("brand"); w.add_argument("run"); w.add_argument("--set")
    w.add_argument("--kind", help="product picture kind from the brand's picture standard"); w.add_argument("--bundle", action="store_true")
    g = sub.add_parser("signage"); g.add_argument("brand")
    sk = sub.add_parser("stamp-kept", help="give every kept print the tool's record (prints filed before put stamped them)")
    sk.add_argument("brand")
    c = sub.add_parser("put-change"); c.add_argument("request")
    c.add_argument("--render"); c.add_argument("--print", dest="printed"); c.add_argument("--note", default="")
    a = ap.parse_args(argv)
    if a.cmd == "print-words":
        print(json.dumps(first_print(a.brand, a.run, a.set, a.kind, a.bundle), indent=1, ensure_ascii=False))
    elif a.cmd == "stamp-kept":
        got = stamp_kept(a.brand)
        print("\n".join(got) or "every kept print is already on record")
    elif a.cmd == "signage":
        print("\n".join(fill_signage(a.brand)) or "nothing to fill")
    elif a.cmd == "put-change":
        print(put_change(json.loads(Path(a.request).read_text()), a.render, a.printed, a.note))
    elif a.cmd == "show":
        print(json.dumps(record(a.brand, a.set), indent=1, ensure_ascii=False))
        for n in needs(a.brand, a.set):
            print("MISSING:", n)
    elif a.cmd == "ready":
        from image_production import providers as PV
        hf = PV._HfShell()
        print(f"command line: {hf.which() or 'NOT FOUND'}")
        try:
            acct = PV.higgsfield_ready(hf)
            print(f"signed in: {acct.get('email')} · {acct.get('credits')} credits · {acct.get('plan')}")
            print("READY: the 3D route makes pictures on this machine (no API key is needed)")
        except PV.ProviderError as ex:
            print(f"NOT READY: {ex}")
            return 1
    elif a.cmd == "printing":
        from image_production import set_queue as Q
        r = Q.printing(a.brand, a.request, a.project, a.generation, a.account, a.credits_before, a.clear)
        print(json.dumps(r.get("printing") or {"cleared": a.clear}, indent=1, ensure_ascii=False))
    elif a.cmd in ("queue", "plan", "request", "done"):
        from image_production import set_queue as Q
        if a.cmd == "queue":
            rows = Q.open_requests(a.brand)
            for r in rows:
                busy = f"PRINTING since {r['printing'].get('sent_at')} · " if r.get("printing") else ""
                print(f"  {r['brand']:<8} {r['id']:<48} {busy}{r.get('source') or ''} · {str(r.get('what'))[:70]}")
            print(f"{len(rows)} waiting for a 3D print" if rows else "nothing waiting for a 3D print")
        elif a.cmd == "plan":
            print(json.dumps(Q.plan(a.brand, a.request), indent=1, ensure_ascii=False, default=str))
        elif a.cmd == "request":
            print(Q.file(a.brand, a.what, name=a.name, products=a.product, cast=a.cast, source="by hand"))
        else:
            res = Q.done(a.brand, a.request, a.set_name)
            print(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    elif a.cmd == "reopen":
        from image_production import set_queue as Q
        for rid in a.request:
            r = Q.reopen(a.brand, rid, a.why)
            print(f"reopened {r['id']}: its kept print retired; the next print round prints it")
    elif a.cmd == "picture-from":
        print(json.dumps(picture_from(a.brand, a.set), indent=1, ensure_ascii=False))
    else:
        words = Path(a.words[1:]).read_text() if (a.words or "").startswith("@") else a.words
        print(put(a.brand, a.set, a.render, a.printed, a.note, a.run, a.cast_board, a.original,
                  {"project": a.project, "generation": a.generation, "reference": a.reference, "words": words, "skin": a.skin}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
