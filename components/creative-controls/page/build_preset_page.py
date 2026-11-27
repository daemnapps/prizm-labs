#!/usr/bin/python3
"""The Preset Library page: every shelf of story_presets.json drawn for the owner, plus its Markdown copy.

    python3 components/creative-controls/page/build_preset_page.py

Writes page/preset-library.html (no pictures, kept in git), context/PRESET-LIBRARY-owner.md and, when the preview
pictures are on this machine (runs/creative-controls/options-thumbs/thumbs/, Higgsfield's public previews made small),
runs/creative-controls/options-page/creative-options.html: the Creative Options artifact is published from that one.
Reads the bank and, for each Higgsfield card, its example video link from the capture (data only). Spends nothing.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CC = HERE.parent
WS = CC.parents[1]
CAT = WS / "components/workflow-teardown/sources/higgsfield/drama-ads/catalog"


def _json_block(f):
    return json.loads(re.search(r"```json\n(.*?)\n```", f.read_text(), re.S).group(1))


def example_links():
    """card file stem -> Higgsfield's example video for that card (the catalog's preview)."""
    by_id = {c["id"]: (c.get("preview") or {}).get("video_url") for c in _json_block(CAT / "_cards.md")["cards"]}
    out = {}
    for f in CAT.glob("*.md"):
        if not f.name.startswith("_"):
            out[f.stem] = by_id.get(_json_block(f).get("id"))
    return out


MODEL = {"seedance_2_5": "Seedance 2.5", "seedance_2_0": "Seedance 2.0", "gpt_image_2_6": "GPT Image 2.6",
         "gpt_image_2_6_flare": "GPT Image 2.6", "seedream_5_5": "Seedream 5.5", "seedream_v5_pro": "Seedream 5 Pro",
         "soul_2": "Soul 2", "soul_cinematic": "Soul Cinema", "nano_banana_pro": "Nano Banana Pro", "kling4_0": "Kling 4",
         "minimax_h3": "MiniMax H3", "elevenlabs_music_v2_5": "ElevenLabs Music", "elevenlabs_music_v2": "ElevenLabs Music",
         "elevenlabs_v4": "ElevenLabs v4", "text2speech_v2": "Text to speech", "ad_multiplier": "Ad Multiplier",
         "ad_multiplier_v2": "Ad Multiplier", "hf_mult_motion_control": "Motion control", "sync_so": "Sync lipsync",
         "audio_dubbing": "Dubbing"}


def tools():
    """The Studio's Higgsfield menu, each tool in plain words: menu.json (ours) + catalog.json + the breakdowns."""
    hf = WS / "components/video-studio/higgsfield"
    cat = json.loads((hf / "catalog.json").read_text())["items"]
    menu = {r["name"]: r for r in json.loads((hf / "menu.json").read_text())["rows"]}
    doors = {d["id"]: d.get("state") for d in json.loads((hf / "doors.json").read_text())["doors"]}
    out = []
    for i in cat:
        m = menu.get(i["name"], {})
        bd, models, price, makes = m.get("breakdown"), [], "", ""
        f = WS / "components/workflow-teardown/breakdowns" / ("%s.json" % bd) if bd else None
        if f and f.is_file():
            b = json.loads(f.read_text())
            makes = b.get("makes", "")
            for st in b.get("steps") or []:
                for raw in re.split(r"[ ,/()]+", str(st.get("model") or "")):
                    if raw in MODEL and MODEL[raw] not in models:
                        models.append(MODEL[raw])
            price = re.split(r"(?<=[.;])\s", str(b.get("price") or ""))[0][:110]
            price = price if re.search(r"\d+\s*(credits|per)", price) else ""
        out.append({"n": i["name"], "sec": i["section"], "line": i["line"], "makes": makes, "give": m.get("give", ""),
                    "script": m.get("script", "none"), "use": m.get("use", ""), "ours": m.get("ours") or "",
                    "fits": m.get("fits") or [], "models": models[:3], "price": price,
                    "door": doors.get(bd) if bd else None,
                    "watch": i.get("video") or i.get("link") or ""})
    return out


def names():
    n = json.loads((WS / "components/video-production/formats/names.json").read_text())
    return {k: [[x["id"], x["name"]] for x in n[k]["names"]]
            for k in ("production_format", "script_format", "hook_format", "style", "length")}


def sources():
    """Our side: teardowns by brand and format, winners, the swipe pools. Counts read from the run folders."""
    td, swipes = {}, []
    lab = WS / "runs/creative-controls/format-labels/labels.json"      # machine-read labels (script format), if made
    lab = json.loads(lab.read_text())["labels"] if lab.is_file() else {}
    sids = {x["id"] for x in json.loads((WS / "components/video-production/formats/names.json").read_text())
            ["script_format"]["names"]}
    for f in (WS / "runs/video-teardown/_work").glob("*/run.json"):
        try:
            st = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        b = st.get("brand")
        if b not in ("brand_a", "brand_b"):
            continue
        cur = (st.get("layers") or {}).get("format") or st.get("format_id")
        got = (lab.get(f.parent.name) or {})
        if cur in sids:
            fm = cur
        elif f.parent.name in lab:
            fm = got.get("script_format") or "no fit"
        else:
            fm = "unlabelled"
        lane = (st.get("writing_lane") or {}).get("lane") or st.get("lane") or "swipe"
        if not f.parent.name.startswith("order-") and (st.get("lane") or "") != "scratch":
            tri = f.parent / "stages" / "0-triage.md"
            one = re.search(r"^ONE LINE:\s*(.+)$", tri.read_text(errors="replace"), re.M) if tri.is_file() else None
            swipes.append({"id": f.parent.name, "brand": b, "script": fm, "line": (one.group(1) if one else "")[:140],
                           "lane": (st.get("triage_lane") or lane or "").lower(), "url": st.get("post_url") or "",
                           "pic": (f.parent / "poster.jpg").exists(), "opened": st.get("opened") or ""})
        row = td.setdefault(b, {"total": 0, "formats": {}, "lanes": {}})
        row["total"] += 1
        row["formats"][fm] = row["formats"].get(fm, 0) + 1
        row["lanes"][lane] = row["lanes"].get(lane, 0) + 1
    win = {}
    for b in ("brand_a", "brand_b"):
        f = WS / "runs/winners" / b / "bank.json"
        if f.is_file():
            rows = json.loads(f.read_text()).get("rows") or []
            win[b] = {"total": len(rows), "video": sum(r.get("format") == "Video" for r in rows),
                      "image": sum(r.get("format") == "Image" for r in rows)}
    paid = [p.name for p in (WS / "components/swipe-paid").iterdir()
            if p.is_dir() and (p / "blocks.json").is_file()]
    org = json.loads((WS / "components/swipe-organic/formats.json").read_text())
    org = org if isinstance(org, list) else org.get("formats") or []
    swipes.sort(key=lambda x: x["opened"], reverse=True)
    return {"teardowns": td, "swipes": swipes, "winners": win, "paid_advertisers": len(paid),
            "organic": [o.get("name") or o.get("id") for o in org]}


def brands():
    out = {}
    for b in ("brand_a", "brand_b"):
        root = WS / "brands" / b
        av = sorted(p.name for p in (root / "core-avatars").iterdir() if p.is_dir() and (p / "profile.md").is_file())
        prod = sorted(f.stem for f in (root / "products").glob("*.md") if "· live" in f.read_text()[:400])
        prod += sorted(p.name for p in (root / "products").iterdir() if (p / "product.md").is_file())
        out[b] = {"avatars": av, "products": prod}
    return out


def our_briefs():
    """Every brief in each brand's register, with its script format: the writing run's own label when it is a script
    format, else the machine-read label, else the register's word when it is one. Our briefs are shapes too."""
    names_ = json.loads((WS / "components/video-production/formats/names.json").read_text())
    sids = {x["id"] for x in names_["script_format"]["names"]}
    lf = WS / "runs/creative-controls/format-labels/labels.json"
    lab = json.loads(lf.read_text())["labels"] if lf.is_file() else {}
    bf = lf.parent / "brief-labels.json"
    blab = json.loads(bf.read_text())["labels"] if bf.is_file() else {}
    out = []
    for b in ("brand_a", "brand_b"):
        f = WS / "brands" / b / "briefs" / "briefs.json"
        if not f.is_file():
            continue
        for r in json.loads(f.read_text()).get("briefs") or []:
            run = re.search(r"runs/video-teardown/_work/([^/\s]+)", json.dumps(r))
            script = None
            if run:
                rj = WS / "runs/video-teardown/_work" / run.group(1) / "run.json"
                try:
                    cur = (json.loads(rj.read_text()).get("layers") or {}).get("format") if rj.is_file() else None
                except ValueError:
                    cur = None
                script = cur if cur in sids else (lab.get(run.group(1)) or {}).get("script_format")
            if not script:
                script = (blab.get(r.get("brief")) or {}).get("script_format")
            if not script and r.get("format") in sids:
                script = r["format"]
            out.append({"id": r.get("brief"), "brand": b, "title": r.get("title") or r.get("concept") or r.get("angle") or "",
                        "concept": r.get("concept") or "", "angle": r.get("angle") or "", "avatar": r.get("avatar") or "",
                        "product": r.get("product") or "", "media": r.get("media") or "", "script": script or "",
                        "made": r.get("format") or "", "run": run.group(1) if run else "",
                        "look": ((r.get("moves") or {}).get("look") or (blab.get(r.get("brief")) or {}).get("style") or "")})
    return out


def arc_rows():
    c = json.loads((CC / "controls.json").read_text())
    return [{"id": a["id"], "name": a["name"], "what": a["what"], "best": a.get("best_for") or [],
             "beats": [b["beat"] for b in a["beats"]]} for a in c["arcs"]]


def data():
    d = json.loads((CC / "story_presets.json").read_text())
    links = example_links()
    arcs = {a["id"]: a["name"] for a in json.loads((CC / "controls.json").read_text())["arcs"]}
    presets = []
    for p in d["presets"]:
        f = p["format"]
        presets.append({
            "id": p["id"], "name": p["name"], "family": p["hf_style"], "sec": p["seconds"], "len": p["length"],
            "logline": re.sub(r"^Make an? (roughly )?", "", p["logline"]).replace("the user's product", "our product"),
            "beats": [[b["from_pct"], b["to_pct"], b["beat"]] for b in p["beats"]],
            "entry": p["product"]["enters_pct"], "how": p["product"]["how"], "cast": p["cast"], "tone": p["tone"],
            "arc": arcs.get(p.get("arc") or "", ""), "look": f.get("style") or f.get("element_style") or "",
            "lookgap": bool(not f.get("style")), "script": f.get("script_format") or "",
            "prod": f.get("production_format") or "", "video": links.get(p["id"]), "song": p["hf_style"] == "singing"})
    return {
        "tools": tools(), "names": names(), "sources": sources(), "brands": brands(), "briefs": our_briefs(),
        "arcs": arc_rows(),
        "presets": presets,
        "shots": [{"n": s["name"], "f": s["family"], "o": s["output"], "w": s["what"]} for s in d["shots"]],
        "formats": [{"n": x["name"], "k": x["kind"], "s": x["state"], "w": x["what"],
                     "o": x["ours"]["production_format"] or x["ours"]["script_format"] or x["ours"]["tool"] or ""}
                    for x in d["formats"]],
        "looks": [{"n": l["name"], "fr": l["from"].split("/")[0], "s": l["state"],
                   "o": l["ours"] or l.get("element_style") or ""} for l in d["looks"]],
        "galleries": d["galleries"],
        "checks": [c["id"] for c in d["checks"]],
    }


def markdown(D):
    P = D["presets"]
    T = D["tools"]
    L = ["# Creative Options (2026-11-21)", "",
         "Every way we can make an ad: the combo builder (brand, avatar, product, start from, script format, story preset, "
         "look, hook, length, tool), the Higgsfield menu in plain words, our own teardowns, winners and swipe pools, and "
         "the preset bank. Tool rows: `components/video-studio/higgsfield/menu.json` (ours) over `catalog.json`.", "",
         "## The Higgsfield menu", "", "| Tool | Section | Script | Give it | For us | Model | Ours |", "|---|---|---|---|---|---|---|"]
    L += ["| %s | %s | %s | %s | %s | %s | %s |" % (t["n"], t["sec"], {"ours": "our script drives it", "own": "writes its own, takes ours",
          "none": "no script"}[t["script"]], t["give"], t["use"], ", ".join(t["models"]) or "—", t["ours"] or "—") for t in T]
    L += ["", "## Preset Library", "",
         "The preset layer between formats and writing: Higgsfield's shelves banked brand-free in "
         "`components/creative-controls/story_presets.json`, each row marked ours or gap. A run names a preset with "
         "`--preset <id>` (or `auto`); every writing pass gets its shape on top and fills it with the brand's research.",
         "", "Page: built by `components/creative-controls/page/build_preset_page.py`.", "",
         "## Shelves", "",
         "| Shelf | Count | Ours | Gap |", "|---|---|---|---|",
         "| Story presets | %d | %d drama + %d song-line | arcs session-picked |" % (
             len(P), sum(1 for p in P if not p["song"]), sum(1 for p in P if p["song"])),
         "| Shot and still recipes | %d | stills %d · product motion %d | person effects %d |" % (
             len(D["shots"]), sum(s["f"] == "still" for s in D["shots"]),
             sum(s["f"] == "product-motion" for s in D["shots"]), sum(s["f"] == "person-effect" for s in D["shots"])),
         "| Their formats | %d | %d | %d |" % (len(D["formats"]), sum(f["s"] == "covered" for f in D["formats"]),
                                              sum(f["s"] == "gap" for f in D["formats"])),
         "| Looks | %d | %d named + %d element bank | %d |" % (
             len(D["looks"]), sum(l["s"] == "covered" for l in D["looks"]),
             sum(l["s"] == "element-only" for l in D["looks"]), sum(l["s"] == "gap" for l in D["looks"])),
         "| Live galleries (not pulled) | %s | — | all |" % " · ".join(
             "%s %s" % (g["name"], g["count"] or "?") for g in D["galleries"]), "",
         "## Story presets", "", "| Preset | Look family | Seconds | Product in at | Arc | Our look |",
         "|---|---|---|---|---|---|"]
    L += ["| %s | %s | %s | %s | %s | %s |" % (p["name"], p["family"], p["sec"] or "—",
                                                 "%s%%" % p["entry"] if p["entry"] is not None else "—", p["arc"] or "—",
                                                 p["look"] or "—") for p in P]
    L += ["", "## Formats we have nothing for", ""] + ["- %s — %s" % (f["n"], f["w"]) for f in D["formats"]
                                                        if f["s"] == "gap"]
    L += ["", "## Looks with no match", ""] + ["- %s (%s)" % (l["n"], l["fr"]) for l in D["looks"] if l["s"] == "gap"]
    L += ["", "## Our nine checks on every preset", "", ", ".join(D["checks"]), "",
          "## Next", "", "- Done 2026-11-21: Claymation, Needle felt, Art toy and Cinematic live action added to the "
          "locked names list on the owner's word.",
          "- Pull the live galleries item by item (Marketing Studio 649, Viral 87, Soul 33, Genjutsu 20).",
          "- Our winners as presets: 196 brand_a and 68 brand_b winners, none linked to a teardown yet.", ""]
    return "\n".join(L)


THUMBS = WS / "runs/creative-controls/options-thumbs/thumbs"        # Higgsfield preview pictures, made small (not in git)
PICTURED = WS / "runs/creative-controls/options-page/creative-options.html"   # the published page, pictures inside


def thumbs():
    import base64
    if not THUMBS.is_dir():
        return {}
    return {f.stem: "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode() for f in sorted(THUMBS.glob("*.jpg"))}


def page_html(pictures=True):
    """The whole board as one HTML string, built fresh from the files (the Video Studio serves this at /options)."""
    D = data()
    D["thumbs"] = thumbs() if pictures else {}
    return (HERE / "preset-library.template.html").read_text().replace("/*DATA*/null", json.dumps(D, ensure_ascii=False))


def main():
    D = data()
    tpl = (HERE / "preset-library.template.html").read_text()
    D["thumbs"] = {}
    html = tpl.replace("/*DATA*/null", json.dumps(D, ensure_ascii=False))
    (HERE / "preset-library.html").write_text(html)            # the copy in git: no pictures (media stays out of git)
    D["thumbs"] = thumbs()
    if D["thumbs"]:
        PICTURED.parent.mkdir(parents=True, exist_ok=True)
        PICTURED.write_text(tpl.replace("/*DATA*/null", json.dumps(D, ensure_ascii=False)))
        print("wrote %s with %d pictures (the one to publish)" % (PICTURED.relative_to(WS), len(D["thumbs"])))
    (CC / "context" / "PRESET-LIBRARY-owner.md").write_text(markdown(D))
    print("wrote page/preset-library.html (%d KB) and context/PRESET-LIBRARY-owner.md" % (len(html) // 1024))


if __name__ == "__main__":
    main()
