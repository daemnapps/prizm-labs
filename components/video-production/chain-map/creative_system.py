#!/usr/bin/env python3
"""Decision logic along the video chain as whiteboard elements. Stage by stage down the real chain: each decision,
what decides it today and the reasoning the chain gives it, the reasoning filled in from the owner's older material
where the chain is silent or thin (marked with its source), and where a reason is written but stops at the hand-over.
Reads chains/video-decision-logic.json. Writes one JSON file per element plus board-meta.json to
runs/stage-handoff/creative-system/, ready to load into a Whiteboard artifact's store.

    python3 components/video-production/chain-map/creative_system.py
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = REPO / "components" / "stage-handoff"          # the chain data stays there (folded 2026-11-19)
sys.path.insert(0, str(HERE))
from format_map import fit  # noqa: E402

W_NAME, W_CHAIN, W_FILL, W_CARRY, GAP = 300, 560, 640, 420, 24
X_CHAIN = W_NAME + GAP
X_FILL = X_CHAIN + W_CHAIN + GAP
X_CARRY = X_FILL + W_FILL + GAP
WIDE = X_CARRY + W_CARRY


def build():
    d = json.loads((DATA / "chains" / "video-decision-logic.json").read_text(encoding="utf-8"))
    els, order, n = {}, [], [0]

    def add(el):
        n[0] += 1
        els["e%d" % n[0]] = el
        order.append("e%d" % n[0])

    def block(x, y, w, h, text, color):
        add({"type": "shape", "kind": "rect", "x": x, "y": y, "w": w, "h": h, "size": "body", "textAlign": "left",
             "color": color, "text": text})

    rows = [r for s in d["stages"] for r in s["decisions"]]
    c = collections.Counter(r["state"] for r in rows)
    add({"type": "text", "x": 0, "y": 0, "size": "title", "text": "Decision logic along the chain"})
    add({"type": "text", "x": 0, "y": 76, "size": "large", "wrap": WIDE,
         "text": "Where the chain says how it decides, it stands. Where it is silent or thin, the older material fills it, with its source."})
    add({"type": "link", "x": 0, "y": 132, "href": d["links"]["canvas"], "title": "Video Chain Canvas", "kind": "whiteboard"})
    add({"type": "link", "x": 344, "y": 132, "href": d["links"]["format_map"], "title": "Format Map", "kind": "whiteboard"})
    y = 228
    add({"type": "text", "x": 0, "y": y, "size": "large",
         "text": "%d decisions · %d the chain says how · %d filled from the older material · %d where the reason stops at the hand-over" % (
             len(rows), c["stands"], sum(1 for r in rows if r.get("fill")), sum(1 for r in rows if r.get("carry")))})
    y += 64
    kx = 0
    for color, label, w in (("blue", "The chain says how: it stands", 300), ("white", "Thin, silent or a person's call today", 340),
                            ("yellow", "Filled from the older material", 300), ("pink", "The reason stops here", 240)):
        block(kx, y, w, 48, label, color)
        kx += w + GAP
    y += 80
    pw = (WIDE - 2 * GAP) // 3
    ph = max(fit(p, pw) for p in d["pattern"])
    for i, p in enumerate(d["pattern"]):
        block(i * (pw + GAP), y, pw, ph, p, "white")
    y += ph + 72

    lab = d["states"]
    for s in d["stages"]:
        add({"type": "text", "x": 0, "y": y, "size": "title", "text": s["name"]})
        add({"type": "text", "x": 0, "y": y + 72, "size": "body", "wrap": WIDE,
             "text": "In the chain: %s   ·   Hands on: %s" % (s["pieces"], s["hands"])})
        y += 116
        for r in s["decisions"]:
            name = "**%s**\n*%s*" % (r["name"], r["by"])
            chain = ("" if r["state"] == "stands" else "**%s.** " % lab[r["state"]]) + r["chain"]
            fill = ("**Filled from the older material:** %s\n*Source: %s*" % (r["fill"], r["src"])) if r.get("fill") else ""
            carry = ("**The reason stops here:** " + r["carry"]) if r.get("carry") else ""
            h = max(fit(name, W_NAME), fit(chain, W_CHAIN), fit(fill, W_FILL) if fill else 0,
                    fit(carry, W_CARRY) if carry else 0)
            block(0, y, W_NAME, h, name, "white")
            block(X_CHAIN, y, W_CHAIN, h, chain, "blue" if r["state"] == "stands" else "white")
            if fill:
                block(X_FILL, y, W_FILL, h, fill, "yellow")
            if carry:
                block(X_CARRY, y, W_CARRY, h, carry, "pink")
            y += h + 16
        y += 64

    out = REPO / "runs" / "stage-handoff" / "creative-system"
    (out / "elements").mkdir(parents=True, exist_ok=True)       # rewritten in place; nothing deleted
    for eid, el in els.items():
        (out / "elements" / (eid + ".json")).write_text(json.dumps(el, ensure_ascii=False), encoding="utf-8")
    (out / "board-meta.json").write_text(json.dumps({"v": 1, "title": "Decision Logic", "order": order},
                                                    ensure_ascii=False), encoding="utf-8")
    return out, len(els), y


if __name__ == "__main__":
    o, k, y = build()
    print(o, k, "elements, height", y)
