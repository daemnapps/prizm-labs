"""Our work into a Higgsfield preset.

  hf_pack.py ready [--brand B]            what of ours each built door can take now (JSON)
  hf_pack.py pack singing-ads <brief>     gather one song hand-off's inputs into
                                          runs/higgsfield/<brand>/singing-ads-<brief>/ (pack.json + REQUEST.md)
  hf_pack.py pack singing-ads <production label> [--writing <writing run>]
                                          the same from a song production run (runs/video-production/<brand>/<label>/)

A session runs the preset through the Higgsfield connection with REQUEST.md and uploads the files pack.json lists.
Nothing here spends credits or calls Higgsfield.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def repo():
    for d in [HERE, *HERE.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError("no workspace found upward of " + str(HERE))


WS = repo()
HANDOFFS = WS / "runs" / "handoffs" / "video-editor"


def rel(p):
    return str(Path(p).resolve().relative_to(WS))


def song_of(ho):
    for pat in ("assets/kit/song/*.mp3", "song/*.mp3"):
        hits = sorted(x for x in ho.glob(pat) if "14lufs" not in x.name)
        if hits:
            return hits[0]
    return None


def song_handoffs(brand=None):
    out = []
    for ho in sorted(HANDOFFS.glob("*/*")):
        if brand and ho.parent.name != brand:
            continue
        s = song_of(ho)
        if not s:
            continue
        m = re.search(r"brief-\d+", ho.name)
        kit = ho / "assets" / "kit"
        title = ""
        lt = kit / "song" / "lyrics-timed.json"
        if lt.is_file():
            try:
                title = json.loads(lt.read_text()).get("title", "")
            except ValueError:
                pass
        out.append({"brief": m.group(0) if m else ho.name, "brand": ho.parent.name, "title": title or s.stem,
                    "handoff": rel(ho), "song": rel(s), "say": "singing ad %s" % (m.group(0) if m else ho.name)})
    return out


def find_handoff(brief):
    for ho in HANDOFFS.glob("*/*"):
        if ho.name.endswith(brief) or ho.name == brief:
            return ho
    raise SystemExit("no video-editor hand-off for " + brief)


def first_pic(d):
    for ext in ("*.jpg", "*.png", "*.webp"):
        hits = sorted(d.rglob(ext))
        if hits:
            return hits[0]
    return None


def pack_singing(brief):
    ho = find_handoff(brief)
    brand = ho.parent.name
    kit = ho / "assets" / "kit"
    song = song_of(ho)
    if not song:
        raise SystemExit("that hand-off carries no song")
    lt = kit / "song" / "lyrics-timed.json"
    lyrics = kit / "song" / "LYRICS.md"
    shots = json.loads((kit / "shot-list.json").read_text()) if (kit / "shot-list.json").is_file() else {}
    cast, missing = [], []
    for c in shots.get("cast", []):
        m = kit / "cast" / str(c.get("use", "")) / "master.jpg"
        if c.get("use") and m.is_file():
            cast.append({"role": c.get("role"), "who": c.get("who"), "sheet": rel(m)})
        else:
            missing.append({"role": c.get("role"), "who": c.get("who")})
    if not shots.get("cast"):
        for m in sorted((kit / "cast").glob("*/master.jpg")):
            cast.append({"role": m.parent.name, "who": "", "sheet": rel(m)})
    places = []
    for s in sorted(p for p in (kit / "sets").glob("*") if p.is_dir()):
        pic = first_pic(s)
        if pic:
            places.append({"place": s.name, "sheet": rel(pic)})
    product = [rel(p) for p in (kit / "product" / "reference-front.png", kit / "product" / "reference-34.png") if p.is_file()]
    if not product:
        product = [rel(p) for p in sorted((kit / "product").glob("*.png"))[:2]]
    title = json.loads(lt.read_text()).get("title", song.stem) if lt.is_file() else song.stem
    label = "singing-ads-" + brief
    out = WS / "runs" / "higgsfield" / brand / label
    out.mkdir(parents=True, exist_ok=True)
    pack = {"door": "singing-ads", "preset": "/singing-ads", "brand": brand, "brief": brief, "title": title,
            "handoff": rel(ho), "song": rel(song), "lyrics_timed": rel(lt) if lt.is_file() else None,
            "lyrics": rel(lyrics) if lyrics.is_file() else None, "cast": cast, "cast_new": missing,
            "places": places[:8], "product": product,
            "uploads": [rel(song)] + [c["sheet"] for c in cast] + [p["sheet"] for p in places[:8]] + product}
    (out / "pack.json").write_text(json.dumps(pack, indent=1))
    lines = ["# Singing Ads · %s · %s" % (brief, title), "",
             "Run Higgsfield's /singing-ads on this song with OUR inputs. Price it and get the go before any paid step.", "",
             "## Our inputs replace these recipe steps",
             "- Step 2 (transcribe): use our timed lyrics `%s` for lines.tsv. Do not transcribe." % pack["lyrics_timed"],
             "- Step 4.2 (character sheets): use our cast boards below as the sheets. Make a sheet only for a role listed under 'New roles'.",
             "- Step 4.4 (location sheets): use our set boards below. Make one only for a place the lyrics need that is not here.",
             "- Step 4.5 (product sheet): use our product references below, the only product pictures allowed.",
             "- Step 4.1 (master): build it from our lead's cast board and our first set, in the feature-3d style.", "",
             "## Song", "- `%s`" % pack["song"], "", "## Cast"]
    lines += ["- %s · %s · `%s`" % (c["role"], c["who"], c["sheet"]) for c in cast]
    if missing:
        lines += ["", "## New roles (no banked board)"] + ["- %s · %s" % (c["role"], c["who"]) for c in missing]
    lines += ["", "## Places"] + ["- %s · `%s`" % (p["place"], p["sheet"]) for p in places[:8]]
    lines += ["", "## Product"] + ["- `%s`" % p for p in product]
    lines += ["", "## House rules", "- No disclaimers, no offer, price or call-to-action on screen.",
              "- Men never kiss or hug men; nobody kisses a mirror.", "- Clothed cast, no brands but ours."]
    (out / "REQUEST.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"pack": rel(out / "pack.json"), "request": rel(out / "REQUEST.md"), "uploads": len(pack["uploads"]),
                      "cast": len(cast), "new_roles": len(missing), "places": len(pack["places"])}, indent=1))


def phrases(words):
    """lines.tsv rows (start, end, phrase): 2–4 words, split at punctuation or a gap over 0.4 s (the preset's rule)."""
    rows, cur = [], []
    clean = []
    for w in words:
        if w.get("type", "word") != "word":
            continue
        if not re.search(r"\w", w.get("text", "")):     # a lone punctuation mark joins the word before it
            if clean:
                clean[-1] = dict(clean[-1], text=clean[-1]["text"].rstrip() + w["text"].strip())
            continue
        clean.append(dict(w))
    words = clean
    for i, w in enumerate(words):
        cur.append(w)
        nxt = next((x for x in words[i + 1:] if x.get("type", "word") == "word"), None)
        gap = (nxt["start"] - w["end"]) if nxt else 9
        if len(cur) >= 4 or (len(cur) >= 2 and (re.search(r"[.,!?;:)]$", w["text"].strip()) or gap > 0.4)) or not nxt:
            rows.append((cur[0]["start"], cur[-1]["end"], " ".join(x["text"].strip() for x in cur)))
            cur = []
    return rows


def pack_singing_run(label, writing=None):
    """A song production run (runs/video-production/<brand>/<label>/) as the source: its song, its words on the clock,
    the banked cast and product it already uses, and the cast its writing run asks for."""
    hits = list((WS / "runs" / "video-production").glob("*/" + label))
    if not hits:
        raise SystemExit("no production run " + label)
    run = hits[0]
    brand = run.parent.name
    song = run / "song" / "song.mp3"
    if not song.is_file():
        raise SystemExit("that production has no song")
    meta = json.loads((run / "song" / "song.json").read_text()) if (run / "song" / "song.json").is_file() else {}
    title = re.sub(r"[-_]+", " ", Path(meta.get("source_file") or song.stem).stem).strip()
    out = WS / "runs" / "higgsfield" / brand / ("singing-ads-" + label)
    out.mkdir(parents=True, exist_ok=True)
    tr = run / "song" / "transcript.json"
    lines_tsv = None
    if tr.is_file():
        rows = phrases(json.loads(tr.read_text()).get("words") or [])
        lines_tsv = out / "lines.tsv"
        lines_tsv.write_text("".join("%.2f\t%.2f\t%s\n" % r for r in rows))
    cast, looks, product = [], [], []
    refs = run / "element-refs.json"
    if refs.is_file():
        seen = set()
        for items in json.loads(refs.read_text()).values():
            for r in items:
                what, f = r.get("what", ""), Path(r.get("file", ""))
                if what in seen or not f.is_file() or "swipe composition" in what:
                    continue
                seen.add(what)
                if what.endswith(" master"):
                    cast.append({"role": what[:-7], "who": "", "sheet": rel(f)})
                elif " look " in what:
                    looks.append({"role": what.split(" look ")[0], "look": what.split(" look ")[1], "sheet": rel(f)})
                elif what.startswith("product"):
                    product.append(rel(f))
    styled = [p for p in sorted((WS / "runs" / "ai-elements" / brand / "products").glob("*/styles/*/sheet.png"))
              if p.parents[2].name in label]
    if styled:          # the product's styled all-angles sheet (3D print queue) wins: the plain sheet trips the content filter
        product = [rel(styled[0])]
    if not product:
        sheets = sorted((WS / "runs" / "ai-elements" / brand / "products").glob("*/model/product-sheet.png"))
        named = [p for p in sheets if p.parent.parent.name in label]      # the product the label names, else none guessed
        product = [rel(p) for p in named[:1]]
    roles = []
    wr = WS / "runs" / "video-teardown" / "_work" / writing if writing else None
    spec = wr / "production-spec.answer.json" if wr else None
    if spec and spec.is_file():
        for c in json.loads(spec.read_text()).get("casting", []):
            roles.append({"role": c.get("role"), "count": c.get("count"), "reads_as": c.get("reads_as"), "does": c.get("function")})
    pack = {"door": "singing-ads", "preset": "/singing-ads", "brand": brand, "production": rel(run), "writing": rel(wr) if wr else None,
            "title": title, "seconds": meta.get("seconds"), "song": rel(song), "lines_tsv": rel(lines_tsv) if lines_tsv else None,
            "cast": cast, "looks": looks, "roles": roles, "product": product,
            "uploads": [rel(song)] + ([rel(lines_tsv)] if lines_tsv else []) + [c["sheet"] for c in cast] + [l["sheet"] for l in looks] + product}
    (out / "pack.json").write_text(json.dumps(pack, indent=1))
    L = ["# Singing Ads · %s · %s" % (brand, title), "",
         "Run Higgsfield's /singing-ads on this song with OUR inputs. Price it and get the go before any paid step.", "",
         "## Our inputs replace these recipe steps"]
    if lines_tsv:
        L.append("- Step 2 (transcribe): use our `lines.tsv` (words on the song's clock, from our transcript). Do not transcribe.")
    if cast:
        L.append("- Step 4.2 (character sheets): use our banked cast below as the sheets, and their looks for a change of look. Make a sheet only for a role with no banked board.")
    else:
        L.append("- Step 4.2 (character sheets): no banked faces yet. Design the cast from the roles below, then bank the sheets back with us.")
    L += ["- Step 4.5 (product sheet): use our product picture below, the only product picture allowed.", "", "## Song", "- `%s` · %ss" % (pack["song"], meta.get("seconds"))]
    if cast:
        L += ["", "## Banked cast"] + ["- %s · `%s`" % (c["role"], c["sheet"]) for c in cast]
    if looks:
        L += ["", "## Looks"] + ["- %s · %s · `%s`" % (l["role"], l["look"], l["sheet"]) for l in looks]
    if roles:
        L += ["", "## Roles the story needs (from our writing)"] + ["- %s ×%s · %s · %s" % (r["role"], r["count"], r["reads_as"], r["does"]) for r in roles]
    L += ["", "## Product"] + ["- `%s`" % p for p in product]
    L += ["", "## House rules", "- No disclaimers, no offer, price or call-to-action on screen.",
          "- Men never kiss or hug men; nobody kisses a mirror.", "- Clothed cast, no brands but ours.",
          "- Characters match their real-world race and the voice; never default a voice."]
    (out / "REQUEST.md").write_text("\n".join(L) + "\n")
    print(json.dumps({"pack": rel(out / "pack.json"), "title": title, "lines": len(rows) if tr.is_file() else 0,
                      "cast": len(cast), "looks": len(looks), "roles": len(roles), "product": product}, indent=1))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "ready":
        brand = argv[argv.index("--brand") + 1] if "--brand" in argv else None
        doors = json.loads((HERE / "doors.json").read_text())["doors"]
        print(json.dumps({"doors": doors, "ready": {"singing-ads": song_handoffs(brand)}}, indent=1))
        return 0
    if argv[0] == "pack" and len(argv) >= 3 and argv[1] == "singing-ads":
        if (WS / "runs" / "video-production").glob("*/" + argv[2]) and list((WS / "runs" / "video-production").glob("*/" + argv[2])):
            pack_singing_run(argv[2], argv[argv.index("--writing") + 1] if "--writing" in argv else None)
        else:
            pack_singing(argv[2])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
