"""The component picture, to the component page standard (COMPONENT-PAGE-STANDARD.md in the atlas build).

Columns left to right: what comes in → where it lives → the recipe → the engine → what goes out → who uses it
(only those the flow fills). Groups that live somewhere are titled boxes by home; items are a short name and
one short line; four states (runs · proposed/waiting · legacy · worth a look). Bands run full width below.
Pure function of the flow file and the claim states: deterministic, no model, no network.
"""
import html

e = lambda s: html.escape(str(s if s is not None else ""))
ORDER = ["in", "lives", "recipe", "engine", "out", "use"]
COLUMNS = {"in": "Sources", "lives": "Data warehouse", "recipe": "Inputs", "engine": "Engine", "out": "Outputs", "use": "Used by"}
HOME = {"supabase": ("🗄", "Supabase"), "repo": ("📁", "the repo"), "drive": ("☁", "Drive"), "mini": ("⚙", "the mini"),
        "dashboard": ("🖥", "the dashboard host"), "session": ("⌨", "a session"), "browser": ("🌐", "the browser")}


def wrap(t, w):
    words, lines, cur = str(t or "").split(), [], ""
    for x in words:
        if cur and len(cur) + 1 + len(x) > w:
            lines.append(cur)
            cur = x
        else:
            cur = (cur + " " + x).strip()
    if cur:
        lines.append(cur)
    return lines


def item_state(it, states):
    worst = ""
    for c in it.get("covers") or []:
        s = states.get(c)
        if s in ("conflicts", "draft-error"):
            return "bad"
        if s == "stale":
            worst = "stale"
    return worst


def svg(F, states, ann=None):
    P = F["picture"]
    cols = [c for c in ORDER if any(g["col"] == c for g in P["groups"])]
    n = len(cols)
    W = 196 if n <= 5 else 178
    GAP = 40 if n <= 5 else 30
    PAD, TOP, IP, VG = 14, 40, 8, 10
    IW = W - 2 * IP
    CH = max(14, int(IW / 7.9))  # characters per line for names at 12.5px bold
    SH = max(16, int(IW / 6.7))  # sub-lines at 11px
    GH = max(18, int(W / 6.9))   # group headers at 10.5px bold
    refuses = [r.get("code") for r in F.get("refuses") or [] if r.get("code") and not r.get("proposed")]
    out, pos, gbox = [], {}, []
    anchors = {}
    colx = {c: PAD + i * (W + GAP) for i, c in enumerate(cols)}
    bottom = 0
    for c in cols:
        x, y = colx[c], TOP
        for gi, g in enumerate([g for g in P["groups"] if g["col"] == c]):
            boxed = bool(g.get("home") or g.get("title"))
            gy0 = y
            home = HOME.get(g.get("home"), ("", g.get("home") or ""))
            label = " ".join(x_ for x_ in [(g.get("icon") or home[0]), (home[1] if g.get("home") else ""),
                                           ("— " + g["title"]) if g.get("title") and g.get("home") else (g.get("title") or "")] if x_)
            glines = wrap(label, GH) if boxed else []
            clines = wrap(g.get("caption", ""), GH + 4) if boxed and g.get("caption") else []
            if boxed:
                y += 8 + 13 * len(glines) + 12 * len(clines)
            gx, gw = (x + IP, IW) if boxed else (x, W)
            for it in g["items"]:
                nm = wrap(it["name"], CH if boxed else CH + 3)
                sb = wrap(it.get("sub", ""), SH if boxed else SH + 3)
                ln = wrap(it.get("line", ""), SH) if it.get("line") else []
                extra = []
                if c == "engine":
                    if it.get("runs"):
                        extra.append(("run", wrap("runs " + it["runs"], SH + 3)))

                cardl = wrap("planned · " + it["card"], SH) if it.get("card") else []
                man = bool(it.get("manual"))
                h = (12 if not man else 22) + 15 * len(nm) + 13 * len(sb) + 13 * len(ln) + sum(4 + 13 * len(v) for _, v in extra) + (4 + 12 * len(cardl) if cardl else 0) + 6
                st = it.get("state") or g.get("state") or ""
                ws = item_state(it, states)
                cls = "pi" + (" eng" if c == "engine" else "") + (f" {st}" if st else "") + (f" {ws}" if ws else "")
                out.append(f'<g class="{cls}"><title>{e(it["name"])}: {e(it.get("sub", ""))}</title>'
                           f'<rect x="{gx}" y="{y}" width="{gw}" height="{h}" rx="6"/>')
                ty = y + 17
                for t in nm:
                    out.append(f'<text class="pn" x="{gx + 10}" y="{ty}">{e(t)}</text>')
                    ty += 15
                for t in sb:
                    out.append(f'<text class="ps" x="{gx + 10}" y="{ty}">{e(t)}</text>')
                    ty += 13
                for t in ln:
                    out.append(f'<text class="pl" x="{gx + 10}" y="{ty}">{e(t)}</text>')
                    ty += 13
                for kind, v in extra:
                    ty += 4
                    for t in v:
                        out.append(f'<text class="p{kind}" x="{gx + 10}" y="{ty}">{e(t)}</text>')
                        ty += 13
                if cardl:
                    ty += 4
                    for t in cardl:
                        out.append(f'<text class="pcard" x="{gx + 10}" y="{ty}">{e(t)}</text>')
                        ty += 12
                if ws:
                    out.append(f'<text class="pstate {ws}" x="{gx + gw - 8}" y="{y + 13}" text-anchor="end">{"conflict" if ws == "bad" else "stale"}</text>')
                if man:
                    out.append(f'<text class="pman" x="{gx + gw - 8}" y="{y + h - 7}" text-anchor="end">✍ by hand</text>')
                    anchors.setdefault("manual", (gx + gw - 4, y + h - 10))
                out.append("</g>")
                pos[it["name"]] = (gx, y, gw, h)
                anchors.setdefault("item", (gx + gw - 4, y + 4))
                if st in ("proposed", "legacy", "flag"):
                    anchors.setdefault("state", (gx + gw - 4, y + 4))

                y += h + (6 if boxed else VG)
            if boxed:
                y += IP - 6
                gcls = "pg" + (f" h-{g['home']}" if g.get("home") else "") + (f" {g['state']}" if g.get("state") else "")
                gbox.append((c, x, gy0, W, y - gy0))
                if g.get("home"):
                    anchors.setdefault("home", (x + W - 4, gy0 + 4))
                if g.get("icon"):
                    anchors.setdefault("icon", (x + W - 4, gy0 + 4))
                hdr = "".join(f'<text class="pgh" x="{x + 9}" y="{gy0 + 14 + 13 * k}">{e(t)}</text>' for k, t in enumerate(glines))
                hdr += "".join(f'<text class="pgc" x="{x + 9}" y="{gy0 + 14 + 13 * len(glines) + 12 * k}">{e(t)}</text>' for k, t in enumerate(clines))
                out.insert(0, f'<g class="{gcls}"><rect x="{x}" y="{gy0}" width="{W}" height="{y - gy0}" rx="9"/>{hdr}</g>')
            else:
                gbox.append((c, x, gy0, W, y - gy0 - VG))
            y += 14
        bottom = max(bottom, y)
    heads = "".join(f'<text class="pch" x="{colx[c] + W / 2}" y="18" text-anchor="middle">{e(COLUMNS[c].upper())}</text>' for c in cols)
    # the spine: one arrow per hop between neighbouring columns
    arrows = []
    def mid(b):
        return b[1], b[2] + b[4] / 2, b[1] + b[3]
    for i in range(len(cols) - 1):
        a_, b_ = cols[i], cols[i + 1]
        A_ = [b for b in gbox if b[0] == a_]
        B_ = [b for b in gbox if b[0] == b_]
        pairs = []
        if b_ == "engine":
            pairs = [(s, B_[0]) for s in A_]
        elif a_ == "engine":
            pairs = [(A_[0], t) for t in B_]
        else:
            for s in A_:
                t = min(B_, key=lambda t: abs((t[2] + t[4] / 2) - (s[2] + s[4] / 2)))
                pairs.append((s, t))
        for s, t in pairs:
            x1, y1 = s[1] + s[3], s[2] + min(s[4] / 2, 60)
            x2, y2 = t[1], t[2] + min(t[4] / 2, 60)
            mx = (x1 + x2) / 2
            arrows.append(f'<path class="pa" d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2 - 3},{y2}" marker-end="url(#pa)"/>')
    for a_, b_, kind in P.get("links") or []:
        if a_ in pos and b_ in pos:
            (ax, ay, aw, ah), (bx, by, bw, bh) = pos[a_], pos[b_]
            x = ax + aw - 14
            arrows.append(f'<path class="pa {kind}" d="M{x},{ay + ah} L{x},{by - 3}" marker-end="url(#pa-{kind})"/>')
    for a_, b_, kind in P.get("links") or []:
        if a_ in pos and b_ in pos:
            anchors.setdefault("link", (pos[a_][0] + pos[a_][2] - 4, pos[b_][1] - 10))
    anchors["cols"] = (colx[cols[0]] + 6, 12)
    if "lives" in cols:
        anchors["lives"] = (colx["lives"] + 6, 12)
    if "recipe" in cols:
        anchors["recipe"] = (colx["recipe"] + 6, 12)
    badges = ""
    for key, (num, typ) in (ann or {}).items():
        if key in anchors:
            ax, ay = anchors[key]
            badges += (f'<g class="ann-b {typ}"><circle cx="{ax}" cy="{ay}" r="11"/>'
                       f'<text x="{ax}" y="{ay + 4}" text-anchor="middle">{num}</text></g>')
    Wt = PAD * 2 + n * W + (n - 1) * GAP
    H = bottom + 4
    defs = ('<defs>' + "".join(f'<marker id="pa{s}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
                              f'<path d="M0,0 L10,5 L0,10z" class="pah{s.replace("-", " ")}"/></marker>' for s in ("", "-proposed")) + '</defs>')
    return f'<svg class="pic" viewBox="0 0 {Wt} {H}" role="img" aria-label="How {e(F.get("component"))} works">{defs}{heads}{"".join(arrows)}{"".join(out)}{badges}</svg>'


def bands(F, keys=("writes", "outcome", "waiting", "never")):
    B = (F.get("picture") or {}).get("bands") or {}
    out = []
    # writes_back is {who, events[]} (SCHEMA §4); a plain sentence is read as the events, the reader as who
    wb = [(dict(i, writes_back=i["writes_back"] if isinstance(i["writes_back"], dict)
                else {"who": (i.get("label") or "").split(" — ")[0].split(":")[0], "events": [str(i["writes_back"])]}), g)
          for g in F.get("used_by") or [] for i in g.get("items") or [] if i.get("writes_back")]
    if wb and "writes" in keys:
        out.append('<div class="band"><div class="bh">Who writes back, and what</div><div class="bcards">' + "".join(
            f'<div class="bc"><b>{e(i["writes_back"].get("who"))}</b><span>{e(" · ".join(i["writes_back"].get("events") or []))}</span>'
            f'<i>from {e((i.get("label") or "").split(" — ")[0].split(":")[0])}</i></div>' for i, g in wb) + "</div></div>")
    o = F.get("outcomes")
    if o and "outcome" in keys:
        tone = {"workflow": "ok", "sources": "warn", "stop": "idle", "engine": "warn"}
        out.append('<div class="band"><div class="bh">The outcome</div><p class="bl">' + e(o.get("fold")) + '</p><div class="bcards">' + "".join(
            f'<div class="bc x-{tone.get(x.get("to"), "idle")}"><b>{e((x.get("label") or "").split(" — ")[0].split(";")[0])}</b>'
            f'<span>{e((x.get("label") or "").split(" — ", 1)[1] if " — " in (x.get("label") or "") else "")}</span></div>' for x in o.get("exits") or []) + "</div></div>")
    for key, cls in (("waiting", "wait"), ("never", "never"), ("owners", "own")):
        b = B.get(key)
        if b and key in keys:
            out.append(f'<div class="band {cls}"><div class="bh">{e(b["title"])}</div><div class="bcards">' + "".join(
                f'<div class="bc{" flag" if it.get("state") == "flag" else ""}"><b>{e(it["name"])}</b><span>{e(it.get("sub", ""))}</span>'
                + (f'<i>{e(it["who"])}</i>' if it.get("who") else "") + "</div>" for it in b["items"]) + "</div></div>")
    r = B.get("rules")
    if r and "rules" in keys:
        out.append(f'<div class="band"><div class="bh">{e(r["title"])}</div><ul class="brules">' + "".join(
            f'<li class="{"prop" if it.get("state") == "proposed" else ""}">{e(it["text"])}</li>' for it in r["items"]) + "</ul>"
            + (f'<p class="kill">KILL · {e(r["kill"])}</p>' if r.get("kill") else "") + "</div>")
    return "".join(out)


LEGEND = ('<div class="plegend"><span><i class="lg run"></i>runs at HEAD</span><span class="lgman">✍ by hand: a person writes or copies it, the machine does not make it</span><span><i class="lg prop"></i>planned, or approved and waiting on a fact</span>'
          '<span><i class="lg legacy"></i>deferred, legacy, or beside</span><span><i class="lg flag"></i>runs today, worth a look</span>'
          '<span><i class="lg bad"></i>conflict or stale against the code</span></div>')
