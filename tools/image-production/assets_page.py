#!/usr/bin/env python3
"""python3 assets_page.py <brand> — the move list. What comes over, and what is out.

It got complicated and it should not be. Every folder the owner has ruled out is
gone; what is left is the short list of what to copy into the home folder.
"""
import base64, collections, io, json, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
WS = next(d for d in HERE.parents if (d / "brands").is_dir())
if len(sys.argv) < 2:
    sys.exit("name a brand: python3 assets_page.py <brand>")
brand = sys.argv[1]
inv = json.loads((HERE / "inventory" / f"{brand}-inventory.json").read_text())
scope = json.loads(next(c for c in (WS / "brands" / brand / "assets.json",
                                   WS / "brands" / brand / "archive" / "retired-2026-09-30" / "assets.json")
                         if c.is_file()).read_text())
KILL = [n.lower() for n in scope.get("excluded_by_name", {}).get("names", [])]
KILLP = [x["path"].lower() for x in scope["excluded"]]
PIC = {".png", ".jpg", ".jpeg", ".webp"}


def link(p):
    try:
        i = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", str(p)],
                           capture_output=True, text=True, timeout=45).stdout.strip()
        return f"https://drive.google.com/drive/folders/{i}" if i else None
    except Exception:
        return None


def thumbs(rows, n=6, px=230):
    from PIL import Image
    out, pics = [], [r for r in rows if r["ext"] in PIC and 40_000 < r["bytes"] < 12_000_000]
    step = max(1, len(pics) // (n * 3)) if pics else 1
    for r in pics[::step]:
        if len(out) >= n:
            break
        try:
            im = Image.open(r["path"]).convert("RGB"); im.thumbnail((px, px))
            b = io.BytesIO(); im.save(b, "JPEG", quality=72, optimize=True)
            out.append("data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode())
        except Exception:
            continue
    return out


def alive(f):
    low = f["folder"].lower()
    return not any(x in low for x in KILL) and not any(x in low for x in KILLP)


home_key = next(k for k in inv["roots"] if "Team Drive" in k)
gm = next(k for k in inv["roots"] if "Shared drives/the company" in k)
root = pathlib.Path(gm)

MOVE = [
 ("Creators", "Content/Creative Assets/2. Content/1. Creators",
  "Every creator piece — video and images both. The cleanest read on the "
  "avatars and the market's own language, and the one that scales.", "moving"),
 ("Branded", "Content/Creative Assets/2. Content/2. Branded",
  "Finished branded stills — but 91% of it is 2022 work.", "some"),
 ("Brand", "Content/Creative Assets/1. Brand",
  "The 2021 kit. The logo and fonts are already in home.", "skip"),
]

cards = []
for label, rel, note, verdict in MOVE:
    base = str(root / rel)
    rows = [f for f in inv["roots"][gm]["files"] if f["folder"].startswith(base) and alive(f)]
    imgs = [f for f in rows if f["kind"] == "image"]
    yrs = collections.Counter(f["modified"][:4] for f in imgs)
    recent = sum(n for y, n in yrs.items() if y >= "2023")
    cards.append({"title": label, "note": note, "verdict": verdict,
                  "imgs": len(imgs), "gb": sum(f["bytes"] for f in imgs) / 1e9,
                  "recent": recent, "years": dict(sorted(yrs.items(), reverse=True)),
                  "url": link(root / rel), "thumbs": thumbs(imgs)})

# WHAT THE HOME FOLDER LOOKS LIKE RIGHT NOW, read off the mount rather than
# the inventory, because it changed today: products cleaned, identity copied
# in, creators arriving.
def live(path):
    p = pathlib.Path(path)
    if not p.is_dir():
        return 0, 0
    n = b = 0
    for f in p.rglob("*"):
        try:
            if f.is_file() and not f.name.startswith("."):
                n += 1; b += f.stat().st_size
        except OSError:
            continue
    return n, b


HOMEDIR = pathlib.Path(home_key)
STATE = []
for name, note in (("products", "the product page only — everything older archived"),
                   ("identity", "the logo, both typefaces, the icon set"),
                   ("creators", "the creator library — copying in now"),
                   ("elements", "the cast, the places, the props"),
                   ("core-avatars", "who we sell to"),
                   ("archive", "not live. Nothing reads it unless you ask.")):
    n, b = live(HOMEDIR / name)
    if n:
        STATE.append({"name": name, "note": note, "n": n, "gb": b / 1e9,
                      "url": link(HOMEDIR / name)})

home_rows = inv["roots"][home_key]["files"]
HOME = {"n": len(home_rows),
        "imgs": sum(1 for f in home_rows if f["kind"] == "image"),
        "url": link(pathlib.Path(home_key)), "thumbs": thumbs(home_rows)}

OUT = ([{"name": pathlib.Path(x["path"]).name, "why": x["why"]} for x in scope["excluded"]]
       + [{"name": n, "why": "ruled out wherever it appears"} for n in
          scope.get("excluded_by_name", {}).get("names", [])])

json.dump({"brand": brand, "home": HOME, "state": STATE, "move": cards, "out": OUT,
           "order": scope.get("_order_of_work", [])},
          open(HERE / "assets-page-data.json", "w"), indent=1)
print(f"move {len(cards)} · out {len(OUT)} · "
      f"take now {sum(c['imgs'] for c in cards if c['verdict']=='take'):,} images")
