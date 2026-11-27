#!/usr/bin/env python3
"""THE CAST BOARD: every cast member of a scene on ONE reference picture, for the 3D print (2026-11-10).

`scene_builder_3d_generate_angles` takes one reference picture. A scene with one product uses the product's casting sheet;
a scene with several people needs all of them on that one picture. The board is built from each member's own casting
files (runs/ai-elements/<brand>/casting/<element>/): the headshot on top, the look sheet the scene names below it, one
column per member, numbered left to right in the order they stand in the scene. Nothing is generated: the casting files
are laid out as they are.

Every file on the board is recorded with its sha256, in the format the Video Studio's old-element check reads
(`params.picture_from` on a take: [{element, file, sha256}], file relative to the element's folder). `picture_sets.py put
--cast-board <board.json>` copies the board into the set and writes the same list into set.json, so the start picture
printed from it names exactly which casting files it was made from, and goes stale the moment one of them changes.

    python3 cast_board.py build <brand> <out.png> <element>[:<look>] <element>[:<look>] ...   (standing order, left to right)
    python3 cast_board.py check <board.json>        the files on the board that changed since it was built (exit 1 if any)
    python3 cast_board.py refs <out.png> <picture> <picture> ...   any reference pictures on one board (the print takes one)

A member with no headshot or no look sheet is refused by name: the board never carries a gap.

A real person kept as themselves (their spec.json says "none to his face" / "none to her face": our own creator, never
an invented face) also gets their real video frames (reference/*.jpg, up to two) under the look sheet, labelled "real
face". A print drawn from the casting sheet alone drifts on a real creator's face in a two-shot; with the real frames
on the board the face gate passed (12 Nov 2026). The print words say so (`print_words_add`).
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))                                   # APPEND, never insert at 0
from image_production import paths as P  # noqa: E402

HEADSHOT = "sheets/headshot.jpg"
COL_W = 640                    # one member's column, in pixels
LOOK_H = 1100                  # the look sheet's box under the headshot
LABEL_H = 90
GAP = 24
REAL_H = 520                   # the real-face strip under a real creator's look sheet


class BoardRefused(ValueError):
    """A member's casting files are missing: no board was made."""


def casting_home(brand, element):
    rel = Path("runs") / "ai-elements" / brand / "casting" / element
    for root in [P.repo()] + list(Path.home().glob("Library/CloudStorage/*/Shared drives/Shared Assets")):
        if (root / rel).is_dir():
            return root / rel
    return P.repo() / rel


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def look_sheet(home, look=None):
    """The look sheet file (relative to the element's folder) for `look`, else the element's first look."""
    lj = home / "looks.json"
    looks = (json.loads(lj.read_text()).get("looks") or {}) if lj.is_file() else {}
    if look:
        row = looks.get(look)
        if row and row.get("sheet"):
            return row["sheet"], look
        guess = f"sheets/{look}.jpg"
        return guess, look
    for lid, row in looks.items():
        if row.get("sheet"):
            return row["sheet"], lid
    found = sorted(home.glob("sheets/look-*.jpg"))
    return (str(found[0].relative_to(home)), found[0].stem) if found else ("sheets/look-1.jpg", None)


def member_files(brand, spec):
    """`element` or `element:look` -> {element, look, files: [{element, file, sha256}], paths}. Refuses a missing file."""
    element, _, look = str(spec).partition(":")
    home = casting_home(brand, element)
    if not home.is_dir():
        raise BoardRefused(f"{element}: no casting element at runs/ai-elements/{brand}/casting/{element}")
    sheet, look_id = look_sheet(home, look or None)
    files, paths = [], []
    head = HEADSHOT
    sp = home / "spec.json"
    shown = (json.loads(sp.read_text()).get("shown") if sp.is_file() else None)
    if shown == "character" and not (home / HEADSHOT).is_file() and (home / "master.jpg").is_file():
        head = "master.jpg"          # a non-human character (gloves, a mascot) has no headshot: its master is its face
    if look_id and (home / f"sheets/{look_id}-headshot.jpg").is_file():
        head = f"sheets/{look_id}-headshot.jpg"   # a look that changes the face (shaved, healed) has its own headshot
    for rel in (head, sheet):
        f = home / rel
        if not f.is_file():
            raise BoardRefused(f"{element}: casting file {rel} not found; the board never carries a gap")
        files.append({"element": element, "file": rel, "sha256": sha(f)})
        paths.append(f)
    real = []
    sp = home / "spec.json"
    adj = (json.loads(sp.read_text()).get("adjustments") or [""]) if sp.is_file() else [""]
    if str(adj[0]).lower().startswith("none to"):      # a real person kept as themselves
        real = sorted((home / "reference").glob("*.jpg"))[:2]
    return {"element": element, "look": look_id, "files": files, "paths": paths, "real": real}


def _font(size):
    from PIL import ImageFont
    for f in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except (OSError, IOError):
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _fit(im, w, h):
    from PIL import Image
    im = im.convert("RGB")
    s = min(w / im.width, h / im.height)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)


def build(brand, specs, out_png):
    """Lay the members out, write <out>.png and <out>.json (the record), return the record."""
    from PIL import Image, ImageDraw
    if not specs:
        raise BoardRefused("no members named: name each cast member in the order they stand, left to right")
    members = [member_files(brand, s) for s in specs]
    W = GAP + len(members) * (COL_W + GAP)
    H = GAP + LABEL_H + COL_W + GAP + LOOK_H + GAP + (REAL_H + LABEL_H + GAP if any(m["real"] for m in members) else 0)
    board = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(board)
    font = _font(44)
    for i, m in enumerate(members):
        x = GAP + i * (COL_W + GAP)
        draw.text((x + 8, GAP + 18), f"{i + 1}  {m['element']}", fill="black", font=font)
        y = GAP + LABEL_H
        with Image.open(m["paths"][0]) as hs:
            h = _fit(hs, COL_W, COL_W)
        board.paste(h, (x + (COL_W - h.width) // 2, y))
        y += COL_W + GAP
        with Image.open(m["paths"][1]) as lk:
            lo = _fit(lk, COL_W, LOOK_H)
        board.paste(lo, (x + (COL_W - lo.width) // 2, y))
        end = y + lo.height + GAP
        if m["real"]:                                    # the real person's own frames, labelled
            ry = end
            draw.text((x + 8, ry + 18), "real face", fill="black", font=font)
            ry += LABEL_H
            cw = (COL_W - GAP * (len(m["real"]) - 1)) // len(m["real"])
            for k, rf in enumerate(m["real"]):
                with Image.open(rf) as im:
                    r = _fit(im, cw, REAL_H)
                board.paste(r, (x + k * (cw + GAP) + (cw - r.width) // 2, ry))
            end = ry + REAL_H + GAP
        bottom = max(bottom, end) if i else end
    board = board.crop((0, 0, W, min(H, bottom)))      # wide look sheets leave no empty band under the board
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    board.save(out_png)
    rec = {
        "what": "the cast board: one reference picture for the 3D print, every cast member's headshot and look sheet, "
                "numbered left to right in standing order",
        "brand": brand, "board": out_png.name, "board_sha256": sha(out_png),
        "made": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "order": [m["element"] for m in members],
        "members": [{"n": i + 1, "element": m["element"], "look": m["look"], "files": m["files"]} for i, m in enumerate(members)],
        "picture_from": [f for m in members for f in m["files"]],
        "print_reference": "the cast board " + out_png.name + " (each member's casting sheet files: headshot and look "
                           "sheet, in standing order " + ", ".join(m["element"] for m in members) + ")",
        "real_faces": {m["element"]: [str(p) for p in m["real"]] for m in members if m["real"]},
        "print_words_add": "The people are exactly the numbered people on the reference board, left to right in that "
                           "order: " + "; ".join(f"{i + 1} {m['element']}" for i, m in enumerate(members)) + "."
                           + "".join(f" {m['element']} is a real person: his or her face is the 'real face' frames under "
                                     "the look sheet, never slimmer, younger or changed, framed large enough to read."
                                     for m in members if m["real"]),
    }
    out_png.with_suffix(".json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


def check(rec, brand=None):
    """The board's files that are not their casting element's current file any more, in plain words. [] = current."""
    brand = brand or rec.get("brand")
    out = []
    for f in rec.get("picture_from") or []:
        cur = casting_home(brand, f["element"]) / f["file"]
        if not cur.is_file():
            out.append(f"{f['element']}/{f['file']} is gone")
        elif sha(cur) != f["sha256"]:
            out.append(f"{f['element']}/{f['file']} changed since the board was built")
    return out


def ref_board(pictures, out_png, labels=None):
    """Several reference pictures on ONE picture (the print takes one reference): side by side, the same height, numbered,
    nothing generated. Writes <out>.png and <out>.json ({from: [{file, sha256}]}); returns the record."""
    from PIL import Image, ImageDraw
    pics = [Path(p) for p in pictures]
    missing = [str(p) for p in pics if not p.is_file()]
    if missing:
        raise BoardRefused("reference picture not found: " + ", ".join(missing))
    H = 1400
    ims = []
    for p in pics:
        with Image.open(p) as im:
            im = im.convert("RGB")
            ims.append(im.resize((max(1, int(im.width * H / im.height)), H), Image.LANCZOS))
    W = GAP + sum(i.width + GAP for i in ims)
    board = Image.new("RGB", (W, GAP + LABEL_H + H + GAP), "white")
    draw, font, x = ImageDraw.Draw(board), _font(40), GAP
    for n, (im, p) in enumerate(zip(ims, pics), 1):
        # a skin bank patch is labelled "skin": the print words name the 'skin' pictures (2026-11-26)
        label = (labels or [])[n - 1] if labels and n <= len(labels) else ("skin" if "_texture-refs" in str(p) else p.stem)
        draw.text((x + 6, GAP + 22), f"{n}  {label}", fill="black", font=font)
        board.paste(im, (x, GAP + LABEL_H))
        x += im.width + GAP
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    board.save(out_png)
    rec = {"what": "one reference picture for the 3D print: the pictures below, numbered left to right",
           "board": out_png.name, "board_sha256": sha(out_png),
           "from": [{"file": P.rel(p) if str(p).startswith(str(P.repo())) else str(p), "sha256": sha(p)} for p in pics]}
    out_png.with_suffix(".json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("brand"); b.add_argument("out"); b.add_argument("members", nargs="+")
    c = sub.add_parser("check"); c.add_argument("board")
    r = sub.add_parser("refs"); r.add_argument("out"); r.add_argument("pictures", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        try:
            rec = build(a.brand, a.members, a.out)
        except BoardRefused as e:
            print(str(e), file=sys.stderr)
            return 2
        print(json.dumps({k: rec[k] for k in ("board", "order", "print_reference")}, indent=1, ensure_ascii=False))
        return 0
    if a.cmd == "refs":
        try:
            rec = ref_board(a.pictures, a.out)
        except BoardRefused as e:
            print(str(e), file=sys.stderr)
            return 2
        print(json.dumps({k: rec[k] for k in ("board", "from")}, indent=1, ensure_ascii=False))
        return 0
    bad = check(json.loads(Path(a.board).read_text()))
    print("\n".join(bad) or "current: every file on the board is its element's current casting file")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
