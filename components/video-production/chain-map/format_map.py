#!/usr/bin/env python3
"""The format map as whiteboard elements: what an ad is made of, what each layer is, every format-like name sorted
into its layer, the names that are one thing, and the owner's calls. Reads chains/<chain>-format-map.json (a proposal)
and chains/<chain>-formats.json (the definition). Writes one JSON file per element plus board-meta.json to
runs/stage-handoff/<chain>/format-map/, ready to load into a Whiteboard artifact's store.

    python3 components/video-production/chain-map/format_map.py [video]
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = REPO / "components" / "stage-handoff"          # the chain data stays there (folded 2026-11-19)
sys.path.insert(0, str(HERE))

CPL = {"body": 10.2, "small": 8.2}            # pixels a character takes, counted generously
LH = {"body": 30, "small": 25}


def fit(text, w, size="body", pad=44):
    """The height a block needs so its words are not drawn over its neighbours."""
    per = max(8, int((w - 36) / CPL[size]))
    lines = sum(1 + len(l.replace("**", "").replace("_", "")) // per for l in str(text).split("\n"))
    return lines * LH[size] + pad


def it(text):
    """The board's italic mark is *…*; the definition file writes _…_ ."""
    return "\n".join(("*" + l[1:-1] + "*") if l.startswith("_") and l.endswith("_") else l for l in str(text).split("\n"))


def build(chain="video"):
    d = json.loads((DATA / "chains" / ("%s-format-map.json" % chain)).read_text(encoding="utf-8"))
    df = (json.loads((DATA / "chains" / ("%s-formats.json" % chain)).read_text(encoding="utf-8")).get("definition")
          or {})
    els, order, n = {}, [], [0]

    def add(el):
        n[0] += 1
        els["e%d" % n[0]] = el
        order.append("e%d" % n[0])
        return "e%d" % n[0]

    def block(x, y, w, text, color="white", size="body", kind="rect", h=None, align="left"):
        h = h or fit(text, w, size)
        add({"type": "shape", "kind": kind, "x": x, "y": y, "w": w, "h": h, "size": size, "textAlign": align,
             "color": color, "text": text})
        return h

    def head(y, text):
        add({"type": "text", "x": 0, "y": y, "size": "large", "text": text})
        return y + 64

    def row(y, items, w, gap=24, per=None, **kw):
        """Blocks left to right, each row as tall as its tallest block. Returns the next y."""
        per = per or len(items)
        for r0 in range(0, len(items), per):
            chunk = items[r0:r0 + per]
            h = max(fit(t, w, kw.get("size", "body")) for t in chunk)
            for i, t in enumerate(chunk):
                block(i * (w + gap), y, w, t, h=h, **kw)
            y += h + gap
        return y

    WIDE = 2184
    add({"type": "text", "x": 0, "y": 0, "size": "title", "text": "The format map: what is what"})
    add({"type": "text", "x": 0, "y": 76, "size": "large",
         "text": "Every format-like name in the video chain, sorted into what it really is. A proposal: nothing in any bank has changed."})
    add({"type": "link", "x": 0, "y": 132, "href": d["canvas"], "title": "Video Chain Canvas", "kind": "whiteboard"})
    y = 230

    # the owner's calls first: what needs him
    y = head(y, "Your calls: say yes or correct each one")
    y = row(y, ["**%d** %s\n*If yes: %s*" % (c["n"], c["q"], c["yes"]) for c in d["calls"]], 712, per=3, color="pink")
    y += 40

    # one ad, taken apart
    y = head(y, "One ad, taken apart")
    pw = 600
    ph = max(fit("**%s**\n%s\n%s" % (p["name"], p["what"], p["choices"]), pw) for p in d["parts"])
    ids = []
    for i, p in enumerate(d["parts"]):
        ids.append(add({"type": "shape", "kind": "rounded", "x": i * (pw + 96), "y": y, "w": pw, "h": ph, "size": "body",
                        "textAlign": "left", "color": "blue",
                        "text": "**%s**\n%s\n%s" % (p["name"], p["what"], p["choices"])}))
    for a, b in zip(ids, ids[1:]):
        add({"type": "arrow", "from": a, "to": b, "fromSide": "right", "toSide": "left"})
    y += ph + 24
    y += block(0, y, 3 * pw + 2 * 96, d["around"], "white") + 64

    # what a format is (the definition, from the owner's rulings)
    if df:
        y = head(y, "What a format is")
        half = (WIDE - 24) // 2
        h = max(fit(df["what"], half), fit(df["example"], half))
        block(0, y, half, it(df["what"]), "blue", h=h)
        block(half + 24, y, half, it(df["example"]), "yellow", h=h)
        y += h + 64

    # every layer: the question it answers, the test, an example, where it lives today
    y = head(y, "Every layer: the question it answers and the test for it")
    y = row(y, ["**%s**\n%s\n**Test:** %s\n**Like:** %s\n*Today: %s*" % (l["name"], l["q"], l["test"], l["eg"], l["today"])
                for l in d["layers"]], 528, per=4, color="white")
    y += 40

    # production formats
    y = head(y, "Production formats: six, proposed")
    y = row(y, ["**%s**\n%s%s\n*%s*\n%s" % (p["name"], p["what"], ("\n**Takes in:** " + p["folds"]) if p["folds"] else "",
                                          p["runs"], p["note"]) for p in d["production"]], 712, per=3, color="yellow")
    y += 40

    # hook formats
    y = head(y, "Hook formats: how the opening is made when it differs from the body")
    y = row(y, ["**%s**\n%s\n*Today: %s*" % (h["name"], h["what"], h["now"]) for h in d["hook_formats"]], 528, color="yellow")
    y += 40

    # script formats
    y = head(y, "Script formats: where the names sit today")
    y = row(y, ["**%s**\n%s\n*%s*" % (g["name"], g["names"], g["note"]) for g in d["script_groups"]], 712, per=3,
            color="white")
    y += 16
    y = head(y, "Names that look like one thing")
    y = row(y, d["same_thing"], 712, per=3, color="yellow")
    y += 40

    # not formats
    y = head(y, "Not formats")
    y = row(y, ["**%s**\n%s" % (x["name"], x["is"]) for x in d["not_formats"]], 418, color="white")

    if d.get("creative_system"):       # added last, so every earlier element keeps its id
        add({"type": "link", "x": 344, "y": 132, "href": d["creative_system"], "title": "Creative System",
             "kind": "whiteboard"})
    out = REPO / "runs" / "stage-handoff" / chain / "format-map"
    (out / "elements").mkdir(parents=True, exist_ok=True)       # rewritten in place; nothing deleted
    for eid, el in els.items():
        (out / "elements" / (eid + ".json")).write_text(json.dumps(el, ensure_ascii=False), encoding="utf-8")
    (out / "board-meta.json").write_text(json.dumps({"v": 1, "title": "Format Map", "order": order},
                                                    ensure_ascii=False), encoding="utf-8")
    return out, len(els), y


if __name__ == "__main__":
    o, k, y = build(sys.argv[1] if len(sys.argv) > 1 else "video")
    print(o, k, "elements, height", y)
