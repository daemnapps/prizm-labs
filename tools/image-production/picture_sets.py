"""PICTURE SETS — a picture ad's scene built in 3D, at true sizes, before the picture is made (the owner, 2026-10-28).

the owner, on a flat-lay whose WIDGET looked stuck on: "you're missing depth ... in the video work ... we built like a depth
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
    python3 picture_sets.py print-words <brand> <run> [--set <set>]     the first print's words, the prop's words read in
    python3 picture_sets.py put <brand> <set> --render F | --print F [--note "..."] [--run <run>]
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

PRINT_CREDITS = 2.5     # one print, scene_builder_3d_generate_angles at 9:16 2k; the set and its renders are free


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
    lines = [f"Two inputs: the first is a clean 3D blockout of {scene['shot']}; the second is a sheet of real studio photographs "
             "of the product in it, which supplies the product's materials and details. Keep the blockout's camera, layout, "
             "framing, sizes, depth and light exactly; nothing of the blockout's grey materials carries over.",
             f"The light: {scene['light']}."]
    lines += [o.rstrip(".") + "." for o in scene.get("objects") or []]
    lines += scene.get("creative") or []
    if scene.get("product"):
        size = f", {scene['size_cm']} cm long" if scene.get("size_cm") else ""
        lines.append(f"The product is exactly as the reference sheet shows it: {scene['product']}{size}, its own printed label "
                     "and marks exactly as on the sheet, on every one of them. The product in the blockout is only a plain placeholder for "
                     "its place and size: none of its stripes, bands or base shapes are real, and every detail comes from the sheet.")
    # the set's own signage (2026-10-30): the moment's name printed on a real prop (a flag, a sign, a tag), built into
    # the set and printed with it, so it sits on the prop's surface with its light. `signage`: [{prop, words}]
    signs = [s for s in scene.get("signage") or [] if s.get("prop") and s.get("words")]
    for s in signs:
        lines.append(f"The {s['prop'].rstrip('.')} carries the printed words \"{s['words']}\", letter for letter, in plain "
                     "bold letters printed on its surface, lit and shadowed like the prop itself.")
    # "no logos" here wiped the product's own label off every tube (2026-10-28): only OTHER writing is barred
    allowed = "the product's own label" + (" and the words named on the props above" if signs else "")
    lines.append("A real, unretouched photograph, natural grain." + (" No people, no hands." if scene.get("people_none", True) else "")
                 + f" No writing anywhere except {allowed}.")
    return " ".join(lines)


def run_home(brand, run):
    """The run's out folder: its one home, else the old one a run made before 2026-10-28 sits in."""
    for d in (P.repo() / "runs" / "image-teardown" / brand / run / "out", P.repo() / "tools" / "image-teardown" / "runs" / run / "out"):
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


def first_print(brand, run, name=None):
    """The first print's words, built from the run's own brief: THE SET block when it has one, else the set's record and
    the swap rows. Spends nothing, files nothing."""
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
    objects = [x for x in objects if x] or [str(x["to"]) for x in rows if x.get("kind") == "drawn" and x.get("to")]
    if block.get("print"):
        objects.append(str(block["print"]))
    product = _product(brand, (block.get("product") or {}).get("kit") or sw.get("product_kit"))
    signage = r.get("signage") or signage_for(brand, run, rows)
    scene = {"shot": camera or r.get("camera") or r.get("what") or "the swipe's scene", "light": light or r.get("light") or "exactly as the blockout shows it",
             "objects": objects, "creative": creative(brand, run), "product": product.get("what"), "size_cm": product.get("size_cm"), "signage": signage}
    return {"run": run, "set": name, "signage": signage, "product": product, "creative": scene["creative"], "print_words": print_prompt(scene)}


def put(brand, name, render=None, printed=None, note="", run=None):
    d = home(brand, name)
    d.mkdir(parents=True, exist_ok=True)
    r = record(brand, name)
    # the one reference a print takes is the whole casting sheet; a crop of it or a photo pasted on is a side path (2026-10-31)
    if printed and note.startswith("kept") and r.get("print") and "casting sheet" not in str(r["print"].get("reference")):
        raise ValueError(f"{name}: a kept print needs the product casting sheet as its reference, not: {r['print'].get('reference')}")
    if run:
        r["runs"] = sorted(set(r.get("runs") or []) | {run})
        r["signage"] = r.get("signage") or signage_for(brand, run)
    for kind, src in (("render", render), ("print", printed)):
        if not src:
            continue
        n = len(sorted(d.glob(f"{kind}-v*.png"))) + 1
        dst = d / f"{kind}-v{n}.png"
        shutil.copy(src, dst)
        r.setdefault(kind + "s", []).append({"file": dst.name, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "note": note})
    (d / "set.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
    return d


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
                return {"set": sj.parent.name, "print": sj.parent / prints[-1]["file"], "record": d}
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
            "rests": (k.get("behaviour") or {}).get("rests"), "never_show": (k.get("behaviour") or {}).get("never_show")}


def change_request(brand, found, variation, change, brief):
    """One variation row as a set change: what a session building it in Higgsfield 3D Jutsu needs and the print's words.
    Spends nothing and files nothing. `found` is `kept`'s answer; `brief` the variation's brief, its swap list already
    carrying the row's swaps, so each object in the print's words is what it is after the change."""
    r, name = found["record"], found["set"]
    project = r.get("project") if isinstance(r.get("project"), dict) else {"id": r.get("project")}
    the_change = change_words(change)
    product = _product(brand, brief.get("product") or brief.get("product_slug"))
    rows = (brief.get("swap_list") or {}).get("swaps") or []
    people = change.get("people") or brief.get("people")
    signage = r.get("signage") or signage_for(brand, brief.get("run"), rows or None)
    scene = {"shot": r.get("camera") or r.get("what") or "the kept set", "light": r.get("light") or "exactly as the blockout shows it",
             "objects": [str(x["to"]) for x in rows if x.get("kind") == "drawn" and x.get("to")] + [the_change],
             "product": product.get("what"), "size_cm": product.get("size_cm"), "signage": signage,
             "people_none": not (people or change.get("person"))}
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
            "signage": signage, "kept_print": P.rel(found["print"]), "product": product, "print_words": print_prompt(scene),
            "credits": PRINT_CREDITS, "flags": flags,
            "steps": [f"Copy the collection {base} to the new collection and leave the original as it is.",
                      "Make only the change, at its real size and place, and hide the original collection.",
                      "Render inside a scene edit, from the same camera and light.",
                      "Upload the product casting sheet fresh, then print with scene_builder_3d_generate_angles at 9:16, 2k, "
                      "using print_words.",
                      "File it: picture_sets.py put-change <this file> --render R --print P --note 'kept: ...'"]}


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
    w = sub.add_parser("print-words"); w.add_argument("brand"); w.add_argument("run"); w.add_argument("--set")
    g = sub.add_parser("signage"); g.add_argument("brand")
    c = sub.add_parser("put-change"); c.add_argument("request")
    c.add_argument("--render"); c.add_argument("--print", dest="printed"); c.add_argument("--note", default="")
    a = ap.parse_args(argv)
    if a.cmd == "print-words":
        print(json.dumps(first_print(a.brand, a.run, a.set), indent=1, ensure_ascii=False))
    elif a.cmd == "signage":
        print("\n".join(fill_signage(a.brand)) or "nothing to fill")
    elif a.cmd == "put-change":
        print(put_change(json.loads(Path(a.request).read_text()), a.render, a.printed, a.note))
    elif a.cmd == "show":
        print(json.dumps(record(a.brand, a.set), indent=1, ensure_ascii=False))
        for n in needs(a.brand, a.set):
            print("MISSING:", n)
    else:
        print(put(a.brand, a.set, a.render, a.printed, a.note, a.run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
