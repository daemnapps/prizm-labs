#!/usr/bin/env python3
"""The chain map as whiteboard elements: every piece a block in run order, arrows between them, each component a
section, each seam a hand-off block with its gaps. Writes one JSON file per element plus board-meta.json to
runs/stage-handoff/<chain>/canvas/, ready to load into a Whiteboard artifact's store (ArtifactData batch, file_path).

    python3 components/video-production/chain-map/canvas.py [video]
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = REPO / "components" / "stage-handoff"          # the chain data stays there (folded 2026-11-19)
sys.path.insert(0, str(HERE))

W, H, GX, GY, PER, PAD = 200, 152, 64, 80, 6, 24
ROW_W = PER * W + (PER - 1) * GX
COLOR = {"stage": "blue", "station": "blue", "step": "blue"}
SH_, SG = 104, 8                      # a stop card's height and the gap between cards
CANT = ("builder", "nobody", "owner")   # the holder cannot clear these alone


def stops_for(chain):
    """chains/<chain>-stops.json: {component: [stop, ...]}, each stop keyed to a piece id (or new:<name>)."""
    f = DATA / "chains" / ("%s-stops.json" % chain)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def allstops_pre(chain, cid):
    return stops_for(chain).get(cid, [])


def stop_card(st):
    who = {"holder": "the holder clears it", "owner": "needs owner", "builder": "needs a build",
           "nobody": "dead end today"}.get(st.get("clears"), st.get("clears", ""))
    mark = ("✂ " if st.get("breaks_handoff") else "") + ("silent · " if st.get("kind") == "silent-pass" else "")
    return {"type": "shape", "kind": "rect", "w": W, "h": SH_, "size": "small", "textAlign": "left",
            "color": "pink" if st.get("clears") in CANT else "yellow",
            "text": mark + short(st.get("when"), 70) + "\n_" + who + "_"}


def short(s, n):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1].rstrip(" ,;:") + "…"


def detail(p):
    k = (p.get("kind") or "").split("+")[0]
    if k in ("stage", "station", "step") and p.get("model"):
        pr = Path(str(p.get("prompt") or "")).name.replace(".md", "")
        return short(p["model"], 24) + ("\n" + short(pr, 24) if pr else "")
    if k in ("gate", "repair") and p.get("holds") and p["holds"] != "never":
        return "holds: " + short(p["holds"], 40)
    if k == "owner-stop":
        return "waits for a person"
    if p.get("subs"):
        return "calls: " + short(", ".join(p["subs"]), 40)
    return short(p.get("runs") or p.get("writes") or k, 44)


def panels(add, st, d, al):
    """The path from an idea to a live ad, then the root causes of every stop with the one fix for each."""
    y = 220
    path, causes = st.get("_path") or [], st.get("_causes") or []
    if path:
        add({"type": "text", "x": 0, "y": y, "size": "large", "text": "The path: an idea in, a live ad out"})
        y += 56
        pw, ph, pg = 236, 208, 40
        prev = None
        for i, b in enumerate(path):
            cs = st.get(b.get("comp") or "", [])
            lines = ["**" + b["name"] + "**"]
            if b.get("comp"):
                lines.append("%d stops, %d the holder can't clear" % (len(cs), sum(1 for t in cs if t.get("clears") in CANT)))
                lines.append(short(b.get("roads"), 110))
                if b.get("propose"):
                    lines.append("_Proposed: " + short(b["propose"], 80) + "_")
            else:
                lines += ["_" + b.get("state", "") + "_", short(b.get("note"), 60)]
            eid = add({"type": "shape", "kind": "rounded", "x": i * (pw + pg), "y": y, "w": pw, "h": ph, "size": "small",
                       "color": "blue" if b.get("comp") else "white", "text": "\n".join(lines)})
            if prev:
                add({"type": "arrow", "from": prev, "to": eid, "fromSide": "right", "toSide": "left"})
            prev = eid
        y += ph + 72
    if causes:
        add({"type": "text", "x": 0, "y": y, "size": "large",
             "text": "Why it stops: %d stops come down to %d causes, one fix each" % (len(al), len(causes))})
        y += 56
        cw, ch, cg, per = 510, 150, 28, 4
        rows = sorted(causes, key=lambda c: -sum(1 for t in al if t.get("cause") == c["id"]))
        for i, c in enumerate(rows):
            mine = [t for t in al if t.get("cause") == c["id"]]
            r, col = divmod(i, per)
            add({"type": "shape", "kind": "rect", "x": col * (cw + cg), "y": y + r * (ch + cg), "w": cw, "h": ch,
                 "size": "body", "textAlign": "left", "color": "yellow" if c.get("holder") else "pink",
                 "text": "**%d · %s**\n%d break a hand-off\n**Fix:** %s" % (
                     len(mine), c["name"], sum(1 for t in mine if t.get("breaks_handoff")), short(c["fix"], 150))})
        y += ((len(rows) + per - 1) // per) * (ch + cg) + 44
    return y


def format_grid(add, chain, x0=2320, y0=0):
    """Each ad format against the stages: runs alone, needs a person, or not built. Drawn to the right of the path."""
    f = DATA / "chains" / ("%s-formats.json" % chain)
    if not f.exists():
        return
    g = json.loads(f.read_text(encoding="utf-8"))
    lw, cw, ch, gp = 280, 300, 116, 12
    add({"type": "text", "x": x0, "y": y0, "size": "title", "text": "Format by format: how far the chain gets alone"})
    add({"type": "shape", "kind": "rect", "x": x0, "y": y0 + 76, "w": lw + 5 * (cw + gp), "h": 136, "size": "body",
         "textAlign": "left", "color": "white", "text": "**What the trace found:** " + g.get("finding", "")})
    y = y0 + 236
    for i, c in enumerate(["Format, and proof it has run"] + g["columns"][:5]):
        add({"type": "shape", "kind": "rect", "x": x0 + (0 if i == 0 else lw + gp + (i - 1) * (cw + gp)), "y": y,
             "w": lw if i == 0 else cw, "h": 48, "size": "body", "color": "white", "text": "**" + c + "**"})
    y += 60
    col = {"alone": "blue", "person": "yellow", "no": "pink", "na": "white"}
    word = {"alone": "Runs alone", "person": "Needs a person", "no": "Not built", "na": "—"}
    for r in g["rows"]:
        add({"type": "shape", "kind": "rounded", "x": x0, "y": y, "w": lw, "h": ch, "size": "body", "color": "white",
             "text": "**" + r["format"] + "**\n" + short(r.get("proof"), 60)})
        for i, c in enumerate(r["cells"]):
            add({"type": "shape", "kind": "rect", "x": x0 + lw + gp + i * (cw + gp), "y": y, "w": cw, "h": ch,
                 "size": "small", "textAlign": "left", "color": col[c["state"]],
                 "text": "**" + word[c["state"]] + "**" + ("\n" + short(c["note"], 110) if c.get("note") else "")})
        y += ch + gp
    if g.get("format_map"):            # the definition and the full sort live on the Format Map board
        y += 40
        add({"type": "text", "x": x0, "y": y, "size": "title", "text": "What a format is"})
        add({"type": "link", "x": x0, "y": y + 84, "href": g["format_map"], "title": "Format Map", "kind": "whiteboard"})
        if g.get("creative_system"):
            add({"type": "link", "x": x0 + 344, "y": y + 84, "href": g["creative_system"], "title": "Creative System",
                 "kind": "whiteboard"})


def build(chain="video"):
    d = json.loads((DATA / "chains" / ("%s-map.json" % chain)).read_text(encoding="utf-8"))
    els, order, n = {}, [], [0]

    def add(el, back=False):
        n[0] += 1
        eid = "e%d" % n[0]
        els[eid] = el
        (order.insert(0, eid) if back else order.append(eid))
        return eid

    add({"type": "text", "x": 0, "y": 0, "text": "The video chain, piece by piece", "size": "title"})
    add({"type": "text", "x": 0, "y": 72, "size": "large",
         "text": "Four components, every piece, and where hand-offs break"})
    kx = 0
    for c, lab in (("blue", "Model step"), ("white", "Check, file, call, pack"),
                   ("yellow", "Stop the holder clears"), ("pink", "Stop the holder can't clear alone")):
        add({"type": "shape", "kind": "rounded", "x": kx, "y": 136, "w": 180, "h": 44, "color": c, "size": "small",
             "text": lab})
        kx += 204
    add({"type": "text", "x": kx + 16, "y": 144, "size": "body",
         "text": "✂ = breaks the hand-off   ·   silent = lets a bad result through without stopping"})
    al = [t for c in d["components"] for t in allstops_pre(chain, c["id"])]
    top = panels(add, stops_for(chain), d, al)
    add({"type": "text", "x": 0, "y": top, "size": "large",
         "text": "%d stops across the chain · %d break a hand-off · %d the holder can't clear alone · %d pass a bad result silently" % (
             len(al), sum(1 for t in al if t.get("breaks_handoff")), sum(1 for t in al if t.get("clears") in CANT),
             sum(1 for t in al if t.get("kind") == "silent-pass"))})
    y = top + 100
    seams = {s["from"]: s for s in d["seams"]}
    allstops = stops_for(chain)
    containers = []
    for c in d["components"]:
        lanes = ([("", "", c["pieces"])] if c.get("pieces") else
                 [(l["name"], l["id"], l["pieces"]) for l in (c.get("lines") or c.get("roads") or [])])
        cst = allstops.get(c["id"], [])
        top = y
        inner = y + PAD
        body = []
        for name, lid, pieces in lanes:
            if name:
                body.append({"type": "text", "x": PAD, "y": inner, "text": "**" + name + "**", "size": "body"})
                inner += 40
            lst = [st for st in cst if not lid or (st.get("line") or st.get("road") or lid) == lid]
            known = {p["id"] for p in pieces}
            extra = []
            for st in lst:
                pid = st.get("piece") or ""
                if pid not in known and pid not in [e["id"] for e in extra]:
                    extra.append({"id": pid, "name": pid.replace("new:", "").replace("-", " "),
                                  "kind": "not on the map yet", "runs": st.get("at")})
            pieces = list(pieces) + extra
            per = {p["id"]: [st for st in lst if st.get("piece") == p["id"]] for p in pieces}
            for r0 in range(0, len(pieces), PER):
                row = pieces[r0:r0 + PER]
                deep = max(len(per[p["id"]]) for p in row)
                for col, p in enumerate(row):
                    x = PAD + col * (W + GX)
                    ns = len(per[p["id"]]); nb = sum(1 for st in per[p["id"]] if st.get("breaks_handoff"))
                    tag = ("\n**%d stop%s%s**" % (ns, "" if ns == 1 else "s", (", %d break the hand-off" % nb) if nb else "")) if ns else ""
                    body.append(("piece", {"type": "shape", "kind": "rounded", "x": x, "y": inner, "w": W, "h": H,
                                           "size": "small",
                                           "color": COLOR.get((p.get("kind") or "").split("+")[0], "white"),
                                           "text": "**" + short(p["name"], 44) + "**\n" + detail(p) + tag}))
                    for k, st in enumerate(per[p["id"]]):
                        el = stop_card(st); el["x"] = x; el["y"] = inner + H + SG + k * (SH_ + SG)
                        body.append(el)
                inner += H + (deep * (SH_ + SG) + SG if deep else 0) + GY
            inner += 40 - GY
        h = inner - y - 40 + PAD + 16
        cid = add({"type": "container", "x": 0, "y": top, "w": ROW_W + 2 * PAD, "h": h,
                   "text": "%s · skill: %s · %d stops, %d break the hand-off, %d the holder can't clear alone" % (
                       c["id"], c.get("skill", ""), len(cst), sum(1 for t in cst if t.get("breaks_handoff")),
                       sum(1 for t in cst if t.get("clears") in CANT))}, back=True)
        containers.append(cid)
        prev, lane_first = None, True
        for item in body:
            if isinstance(item, tuple):
                el = dict(item[1])
                el["y"] += 0
                eid = add(el)
                if prev and not lane_first:
                    pr = els[prev]
                    if pr["y"] == el["y"]:
                        add({"type": "arrow", "from": prev, "to": eid, "fromSide": "right", "toSide": "left"})
                    else:
                        add({"type": "arrow", "from": prev, "to": eid, "fromSide": "bottom", "toSide": "top"})
                prev, lane_first = eid, False
            elif item.get("type") == "shape":
                add(item)                      # a stop card: hangs under its piece, no arrow
            else:
                add(item)
                prev, lane_first = None, True
        y = top + h + 40
        s = seams.get(c["id"])
        if s:
            lines = ["**Hand-off: %s → %s**%s" % (s["from"], s["to"], ("   ·   " + s["hand_off"]) if s.get("hand_off") else ""),
                     "**Hands over:** " + short(s["handed"], 330),
                     "**Next door reads:** " + short(s["door_reads"], 330)]
            lines += ["✗ " + short(g, 200) for g in s.get("gaps") or []] or ["✓ meets cleanly"]
            nl = sum(1 + len(l) // 190 for l in lines)
            add({"type": "shape", "kind": "rect", "x": 0, "y": y, "w": ROW_W + 2 * PAD, "h": 24 * nl + 40,
                 "color": "white", "size": "body", "textAlign": "left", "text": "\n".join(lines)})
            y += 24 * nl + 40 + 80
    format_grid(add, chain)            # added last, so every earlier element keeps its id
    out = REPO / "runs" / "stage-handoff" / chain / "canvas"
    (out / "elements").mkdir(parents=True, exist_ok=True)      # rewritten in place; nothing deleted
    for eid, el in els.items():
        (out / "elements" / (eid + ".json")).write_text(json.dumps(el, ensure_ascii=False), encoding="utf-8")
    meta = {"v": 1, "title": "Video Chain Canvas", "order": order}
    (out / "board-meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return out, len(els), y


if __name__ == "__main__":
    o, k, y = build(sys.argv[1] if len(sys.argv) > 1 else "video")
    print(o, k, "elements, height", y)
