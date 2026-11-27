"""The brief picks how the ad is made (routes.json), and everything that route needs is gathered before anything is paid.

  hf_route.py route <brief.md | run folder> [--brand B] [--creator]     the route, why, what is here, what is missing, the cost
  hf_route.py pack  <brief.md | run folder> [--brand B] [--label L]      the same, written to
                                                                        runs/higgsfield/<brand>/<route>-<label>/ (pack.json, REQUEST.md)

A pack with anything missing says NOT READY, names it, and exits 1. A person or a place the bank does not hold is not
missing: it is listed to be made once (one sheet), and priced. The product is never made here: its own sheet or stop.
Spends nothing, calls nothing. Brand-agnostic; Python 3.9, standard library.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIC = (".png", ".jpg", ".jpeg", ".webp")


def repo():
    for d in [HERE, *HERE.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError("no workspace found upward of " + str(HERE))


def _slug(x):
    return re.sub(r"[^a-z0-9]+", "-", str(x or "").lower()).strip("-")


def brief_of(path):
    """(the brief's own JSON block, the file it came from)."""
    p = Path(path)
    if p.is_dir():
        hits = [f for f in [p / "deliverable" / "5-brief.md", p / "stages" / "5-brief.md"] if f.is_file()] or sorted(p.rglob("*brief*.md"))
        if not hits:
            raise SystemExit("no brief in " + str(p))
        p = hits[0]
    for m in re.finditer(r"```json\n(.*?)\n```", p.read_text(encoding="utf-8", errors="ignore"), re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("scenes"), list) and d["scenes"]:
            return d, p
    raise SystemExit("that brief carries no scenes to read: " + p.name)


def brand_of(doc, path, given=None, ws=None):
    ws = ws or repo()
    brands = [b.name for b in (ws / "brands").iterdir() if b.is_dir()]
    if given:
        return given
    for b in brands:
        if re.search(r"(?:^|[/_-])%s(?:[/_-]|$)" % re.escape(b), str(path)):
            return b
    raise SystemExit("which brand? name it with --brand")


def said(scene):
    """The scene's own words: spoken, or sung."""
    for k in ("voice", "say", "lyrics", "lyric", "sung"):
        v = scene.get(k)
        if isinstance(v, (list, tuple)):
            v = " ".join(str(x.get("text") or x.get("line") or "") if isinstance(x, dict) else str(x) for x in v)
        if str(v or "").strip():
            return str(v).strip()
    return ""


def facts(doc):
    """What the brief itself says, read once."""
    scenes = doc["scenes"]
    piece = doc.get("piece") or {}
    fmt = re.sub(r"^new:", "", str(piece.get("format") or "")).strip().lower()
    words = " ".join(said(s) for s in scenes)
    who = {str(x).strip().upper() for s in scenes if s.get("to_camera") is not False
           for x in ([s.get("speaker")] if s.get("speaker") not in (None, "", "several") else (s.get("speakers") or [])) if x}
    song = doc.get("song") or {}
    sung = bool(song.get("sections") if isinstance(song, dict) else song)
    on = sum(1 for s in scenes if s.get("to_camera") and str(s.get("voice") or "").strip())
    return {"format": fmt, "words": len(words.split()), "speakers": sorted(who), "sung": sung, "talking_scenes": on, "scenes": len(scenes)}


def choose(f, routes=None, creator=False):
    """(route, why). The format's own row first; a format with no row is decided by what the brief does."""
    rows = (routes or json.loads((HERE / "routes.json").read_text()))["routes"]
    by = {r["id"]: r for r in rows}
    if creator:
        return by["creators"], "a creator films it"
    for r in rows:
        if f["format"] in r["formats"]:
            return r, "its format is %s" % f["format"]
    if f["sung"]:
        return by["singing-ads"], "it is sung"
    if len(f["speakers"]) > 1:
        return by["drama-ads"], "%d people speak on camera" % len(f["speakers"])
    if f["talking_scenes"]:
        return by["ugc-video"], "one person talks to camera"
    return by["own-footage"], "nobody speaks on camera"


def _first(*paths):
    return next((p for p in paths if p.is_file()), None)


def _in_scene(text):
    """The brief's old "laid on in the edit" words read as the product in the shot (V59)."""
    f = repo() / "components" / "video-edit" / "maker" / "scene_packet.py"
    s = importlib.util.spec_from_file_location("hfr_scene_packet", str(f))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m.in_scene_words(text)


def gather(doc, brand, route, ws=None):
    ws = ws or repo()
    bank = ws / "runs" / "ai-elements" / brand
    rel = lambda p: str(Path(p).relative_to(ws))                                   # noqa: E731
    here, make, missing = {"people": [], "places": [], "product": [], "props": []}, [], []
    text = json.dumps(doc)
    if "people" in route["needs"]:
        for c in doc.get("cast") or []:
            name, bid = c.get("name") or c.get("id"), _slug(c.get("bank_id"))
            home = bank / "casting" / bid if bid and bid != "new" else None
            pic = home and _first(*[home / "sheets" / ("headshot" + e) for e in PIC], *[home / ("master" + e) for e in PIC])
            if pic:
                body = _first(*[home / "sheets" / ("core-body" + e) for e in PIC], *[home / ("master" + e) for e in PIC])
                here["people"].append({"name": name, "files": [rel(x) for x in dict.fromkeys([pic, body or pic])]})
            elif str(c.get("identity_block") or "").strip():
                make.append({"what": "person", "name": name, "from": c["identity_block"][:400]})
            else:
                missing.append("%s: no picture and no description" % name)
        if not doc.get("cast"):
            missing.append("the brief names no people")
    for pl in dict.fromkeys(str(s.get("setting_id") or "") for s in doc["scenes"]):
        if not pl or route["cost"] == "none":
            continue
        s = re.sub(r"^the-", "", _slug(pl))
        pic = _first(*[bank / "sets" / x / "plates" / ("wide" + e) for x in (s, "the-" + s) for e in PIC])
        (here["places"].append({"name": pl, "files": [rel(pic)]}) if pic else make.append({"what": "place", "name": pl, "from": "the brief's words"}))
    for pr in dict.fromkeys(str((p if isinstance(p, str) else p.get("id") or p.get("name")) or "") for s in doc["scenes"] for p in s.get("props") or []):
        pic = pr and _first(*[bank / "props" / x / ("picture" + e) for x in (_slug(pr), re.sub(r"^(the|a|an)-", "", _slug(pr))) for e in PIC])
        if pic:
            here["props"].append({"name": pr, "files": [rel(pic)]})
    if "product" in route["needs"]:
        home = bank / "products"
        kits = sorted(d for d in home.iterdir() if (d / "model" / "product-sheet.png").is_file()) if home.is_dir() else []
        named = [d for d in kits if re.search(r"\b%s\b" % re.escape(d.name.replace("-", " ")), text.replace("-", " "), re.I)]
        if not named:
            for d in kits:
                try:
                    al = [a for a in json.loads((d / "kit.json").read_text()).get("aliases") or [] if len(a) > 2]
                except (OSError, ValueError):
                    al = []
                if any(re.search(r"\b%s\b" % re.escape(a), text) for a in al):
                    named.append(d)
        here["product"] = [{"name": d.name, "files": [rel(d / "model" / "product-sheet.png")]} for d in named]
        if not named:
            missing.append("the product: no casting sheet on file for any product this brief names")
    if "song" in route["needs"] and not (doc.get("song") or {}):
        missing.append("the song")
    if "source ad" in route["needs"]:
        missing.append("the source ad's video file")
    return here, make, missing


def have_already(brand, make, ws=None):
    """Beside every picture a brief would make: the ones we already made that fit (asset-index made.py). Shown, never swapped in."""
    try:
        f = repo() / "components" / "asset-index" / "machine" / "made.py"
        s = importlib.util.spec_from_file_location("hfr_made", str(f))
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        rows = m.build(brand, ws) if ws is None else m.read(brand, ws)
        for x in make:
            hit = m.close(brand, x["what"], "%s %s" % (x["name"], "" if x["from"] == "the brief's words" else x["from"]), floor=0.6, n=2, rows=rows)
            if hit:
                x["have"] = [{"name": h.get("name") or h["id"], "file": h["file"], "fits": h["score"]} for h in hit]
    except (OSError, ValueError, KeyError):
        pass
    return make


def plan(path, brand=None, creator=False, ws=None):
    doc, f = brief_of(path)
    ws = ws or repo()
    cfg = json.loads((HERE / "routes.json").read_text())
    fx = facts(doc)
    route, why = choose(fx, cfg, creator)
    brand = brand_of(doc, f, brand, ws)
    here, make, missing = gather(doc, brand, route, ws)
    make = have_already(brand, make, ws)
    if not fx["words"]:
        missing.append("the script: no scene says anything")
    cr, secs = cfg["credits"], round(fx["words"] / cfg["credits"]["words_a_second"])
    if route["cost"] == "seconds":
        best, cheap = secs * cr["seedance_s"], secs * cr["wan_s"]
        sheets = len(make) * cr["sheet"]
        cost = {"seconds": secs, "sheets_to_make": len(make), "seedance": round(best + sheets), "wan": round(cheap + sheets)}
    else:
        cost = {"seconds": secs, "note": route["cost"], "seedance": 0 if route["cost"] == "none" else None}
    return {"brief": f.name, "brand": brand, "title": (doc.get("piece") or {}).get("title"), "route": route["id"], "engine": route["engine"],
            "why": why, "facts": fx, "here": here, "to_make_once": make, "missing": missing, "ready": not missing, "credits": cost}, doc, f


def request(r, doc):
    L = ["# %s · %s" % (r["engine"], r["title"] or r["brief"]), "",
         "Made from our own brief with our own files. Price it and get the go before any paid step. One paid try per piece.", ""]
    if not r["ready"]:
        L += ["**NOT READY.** " + "; ".join(r["missing"]), ""]
    L += ["Cost: about %s credits on Seedance 480p%s." % (r["credits"].get("seedance"), ", %s on Wan" % r["credits"]["wan"] if r["credits"].get("wan") else ""), ""]
    for k, head in (("product", "Product (the only product pictures allowed)"), ("people", "People (use these as the character sheets)"),
                    ("places", "Places (use these as the location sheets)"), ("props", "Props")):
        if r["here"][k]:
            L += ["## " + head] + ["- %s · %s" % (x["name"], " · ".join("`%s`" % f for f in x["files"])) for x in r["here"][k]] + [""]
    if r["to_make_once"]:
        L += ["## Make one sheet each, once, from these words"] + ["- %s %s: %s%s" % (x["what"], x["name"], x["from"], "".join("\n  - WE ALREADY HAVE ONE THAT FITS, use it unless it is wrong for the scene: `%s`" % h["file"] for h in x.get("have") or []))
                                                                                            for x in r["to_make_once"]] + [""]
    L += ["## Script, word for word"]
    for s in doc["scenes"]:
        v = said(s)
        L.append("- %s · %s · %s" % (s.get("id"), s.get("speaker") or s.get("who") or "", v or "no words"))
        h = _in_scene(str(s.get("happens") or "")).strip()
        if h:
            L.append("  - What happens: " + h[:600])
    L += ["", "## Rules", "- The product is in the shot from its own sheet wherever the script shows or uses it. Never an empty hand, never another product.",
          "- Our people, our places, our words. Nothing from the swipe's brand.", "- 480p, sharpened after. No disclaimers on screen. Men never kiss or hug men; nobody kisses a mirror.",
          "- Characters keep their real-world race and the voice matches it.",
          "- A clip that comes back wrong is fixed, not made again: clip_tools.py fix buys only the broken seconds. Relight, new camera and carry-on go through the same door."]
    return "\n".join(L) + "\n"


def main(argv):
    if len(argv) < 2 or argv[0] not in ("route", "pack"):
        print(__doc__)
        return 2
    opt = lambda k: argv[argv.index(k) + 1] if k in argv else None               # noqa: E731
    r, doc, f = plan(argv[1], opt("--brand"), "--creator" in argv)
    if argv[0] == "pack":
        label = opt("--label") or _slug(r["title"] or f.parents[1].name)
        out = repo() / "runs" / "higgsfield" / r["brand"] / ("%s-%s" % (r["route"], label))
        out.mkdir(parents=True, exist_ok=True)
        (out / "pack.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
        (out / "REQUEST.md").write_text(request(r, doc))
        r = dict(r, pack=str((out / "pack.json").relative_to(repo())))
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0 if r["ready"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
