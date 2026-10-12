#!/usr/bin/env python3
"""compose.py — turns a green cut sheet into a HyperFrames project: one web
page with timing marks that renders the same video every time.

    compose(sheet, root, project_dir, captions=True) -> Path to index.html

It executes the sheet and decides nothing. Picture order is the sheet's order;
b-roll paints over a-roll; text is a layer, never generated. Every move eases,
entrances move more than one property, exits are faster than entrances
(the editing rules in CLAUDE.md).

HyperFrames contract used here (read from its docs 2026-09-20, re-read 2026-09-23):
  root  data-composition-id / data-start / data-width / data-height / data-duration
  clip  class="clip" id data-start data-duration data-track-index
  trim  data-media-start   (NOT data-playback-start — that one desyncs audio)
  vol   data-volume 0..3.98 (1 = 0 dB); data-automation {version, lanes:[{target:"volume", points:[{t,v}]}]}
        with t in CLIP-LOCAL seconds — the music's duck lane and room tone's fades
  one paused GSAP timeline registered in window.__timelines[<id>]
  never tween visibility/autoAlpha on a .clip; never a <video data-start> inside a
  timed element — so every picture sits in its own UNTIMED `.cam` wrapper, which is
  what the transitions and the split wipe move; no <br> in body text (block lines)

Every element in ELEMENTS.md is drawn here (2026-09-23): card · screen (per surface) ·
split (side / top-bottom / wipe, labels) · greenscreen (cutout / pip) · endcard ·
lower thirds · annotations (arrow / circle / underline / highlight) · platform UI
(comment_reply / stitch / duet / search / likes) · disclaimers · transitions
(cut / whip / match / zoom / flash) · one grade over the picture · music ducked and
cut to the bar · room tone · SFX two frames early. Looks come from looks/*.json.

Words, 2026-09-23 (the owner: "it looks like there's a lot of space between words"): every
text layer sits in a ZONE (looks/placement.json, moved off the face by placement.py),
is set in a FONT ID (looks/fonts.json — a fetched font gets an @font-face to its local
file, a bundled one needs none, a missing one draws in its fallback), and has exactly
one normal space between words (`word_spacing` / `letter_spacing` on the look; no
margin on the per-word spans). Platform UI is drawn per style (looks/platform_ui.json);
icons, emoji, stickers and drawn elements per row (looks/icons.json).
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

import fonts as FT
import icons as IC
import gl_transitions as GL
import placement as P

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"
TEXT_KINDS = ("card", "screen", "endcard")


def db_to_volume(db: float) -> float:
    return round(min(3.98, 10 ** (db / 20.0)), 3)


def look_of(sheet: dict) -> dict:
    look = (sheet.get("captions") or {}).get("look")
    if isinstance(look, dict):
        return look
    for r in json.loads((TOOL / "looks/bank.json").read_text())["looks"]:
        if r["id"] == look:
            return r
    raise SystemExit(f"caption look `{look}` is not in looks/bank.json")


def caption_lines(words: list[dict], max_words: int, max_gap: float = 0.35) -> list[list[dict]]:
    """Group timed words into on-screen lines: break on a pause, on sentence
    punctuation, or when the line is full."""
    lines, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > max_gap or cur[-1]["text"].rstrip()[-1:] in ".!?"):
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def _asset(src: Path, assets: Path) -> str:
    assets.mkdir(parents=True, exist_ok=True)
    dest = assets / src.name
    if dest.exists() and dest.stat().st_size != src.stat().st_size:
        dest = assets / f"{src.parent.name}-{src.name}"  # two files of one name from two folders
    if not dest.exists() or dest.stat().st_size != src.stat().st_size:
        shutil.copy2(src, dest)
    return f"assets/{dest.name}"


def _grade(sheet: dict) -> str:
    g = sheet.get("grade")
    if not g:
        return "none"
    for r in json.loads((TOOL / "looks/grades.json").read_text())["grades"]:
        if r["id"] == g:
            return r["filter"]
    return "none"


def _esc(t) -> str:
    return html.escape(str(t or ""))


def _auto(points: list[dict]) -> str:
    return html.escape(json.dumps({"version": 1, "lanes": [{"target": "volume", "points": points}]}), quote=True)


def _box(z: str | dict) -> str:
    """CSS for a zone's box (looks/placement.json) — the layer's words centre (or left-align) inside it."""
    Z = P.zones()[z] if isinstance(z, str) else z
    jc = "flex-start" if Z.get("align") == "left" else "center"
    return f"left:{Z['x']}%;top:{Z['y']}%;width:{Z['w']}%;height:{Z['h']}%;display:flex;align-items:center;justify-content:{jc};text-align:{Z.get('align', 'center')}"


def _where(row: dict, default_zone: str) -> str:
    """A row's zone box; a legacy row with only a raw y_pct gets a band centred on it."""
    if row.get("zone") or row.get("y_pct") is None:
        return _box(row.get("zone") or default_zone)
    y = row["y_pct"]
    return f"left:8%;top:{y - 5}%;width:84%;height:10%;display:flex;align-items:center;justify-content:center;text-align:center"


def _spacing(src: dict, fallback: dict | None = None) -> str:
    """One normal space between words, the font's own letter spacing — unless the look says otherwise."""
    f = fallback or {}
    return f"word-spacing:{src.get('word_spacing', f.get('word_spacing', 'normal'))};letter-spacing:{src.get('letter_spacing', f.get('letter_spacing', '0'))}"


def compose(sheet: dict, root: Path, project: Path, captions: bool = True) -> Path:
    meta = sheet["meta"]
    W, H, fps = meta["width"], meta["height"], meta["fps"]
    k = W / 1080  # every size in the looks is for a 1080-wide 9:16 frame
    cid = "edit"
    end = max(c["start"] + c["duration"] for c in sheet["picture"])
    assets = project / "assets"
    ST = json.loads((TOOL / "looks/layers.json").read_text())
    body, pics, tl, css = [], [], [], []
    draw_fns: list[str] = []  # per-frame drawers (confetti) — run by GL.HOOK
    ids = set()
    used_fonts: set[str] = set()
    TX = ST.get("text") or {}

    def fam(font_id: str) -> str:
        """The CSS family for a font id — its @font-face is added once, at the end."""
        used_fonts.add(font_id)
        return FT.stack(font_id)

    ICON_LIB = json.loads((TOOL / "looks/icons.json").read_text())
    ICONS = {x["id"]: x for x in ICON_LIB["icons"]}

    def icons_layer(rows: list[dict]) -> None:
        """Icons, emoji, stickers and drawn elements (looks/icons.json), each in its zone, on its words."""
        ist = ST.get("icons") or {}
        for r in rows:
            ic = ICONS.get(r.get("icon"))
            if r.get("start") is None or not ic:
                continue
            i = uid(r["id"])
            sz = r.get("size", ist.get("size", "m"))
            px = round((ICON_LIB["sizes"].get(sz, 160) if isinstance(sz, str) else float(sz)) * k)
            sprite = IC.sprite(ic["id"]) if ic["kind"] in ("emoji", "sticker") else None
            if sprite:  # an animated emoji (Fluent, MIT): a sprite strip stepped by the timeline — seek-safe
                href = _asset(sprite["png"], assets)
                inner, anim = _sprite_icon(i, px, href, sprite, ic["kind"] == "sticker", k), {"sprite": sprite}
            elif ic["id"] in DRAWN_JS:  # a burst drawn on a canvas per frame (canvas-confetti's physics, ISC)
                inner, anim = f'<canvas id="{i}-in" class="icn-in" width="{W}" height="{H}" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px"></canvas>', {}
                draw_fns.append(DRAWN_JS[ic["id"]](i, r["start"], r["duration"], W, H, r))
            else:
                inner, anim = _icon(ic, r, i, px, k, ist, fam(ist.get("font", ST["font_heavy"])))
            if ic["id"] in DRAWN_JS:
                body.append(f'<div id="{i}" class="clip icn" data-start="{r["start"]}" data-duration="{r["duration"]}" data-track-index="36" style="left:0;top:0;width:100%;height:100%">{inner}</div>')
                continue
            body.append(f'<div id="{i}" class="clip icn" data-start="{r["start"]}" data-duration="{r["duration"]}" data-track-index="36" style="{_where(r, ist.get("zone", "left-rail"))}">{inner}</div>')
            tl.extend(_icon_tl(ic, i, r["start"], r["duration"], anim))
        css.append(".icn{position:absolute;z-index:36;pointer-events:none}.icn-in{position:relative;display:block}")

    def uid(x: str) -> str:
        x = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(x))
        x = x if x[:1].isalpha() else f"x{x}"
        n, i = x, 2
        while n in ids:
            n, i = f"{x}-{i}", i + 1
        ids.add(n)
        return n

    def media_el(el_id: str, src: str, start: float, dur: float, z: int, cls: str = "pic", source_start: float = 0, vol=None, style: str = "") -> str:
        common = f'id="{el_id}" class="clip {cls}" data-start="{round(start, 3)}" data-duration="{round(dur, 3)}" data-track-index="{z}"'
        if src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            return f'<img {common} src="{src}" alt=""{f" style={chr(34)}{style}{chr(34)}" if style else ""}>'
        audio = f' data-has-audio="true" data-volume="{db_to_volume(vol)}"' if vol is not None else " muted"
        return f'<video {common} src="{src}" data-media-start="{source_start}" playsinline{audio}{f" style={chr(34)}{style}{chr(34)}" if style else ""}></video>'

    # ------------------------------------------------ picture — a-roll first, b-roll above it, each in its own camera
    cams: dict[str, str] = {}
    media_ids: dict[str, dict] = {}  # picture id → its main media element (what a GL transition samples)
    drift_n = 0
    for z, roll in ((1, "a"), (2, "b")):
        for c in (x for x in sheet["picture"] if x["roll"] == roll):
            cam = uid(f"cam-{c['id']}")
            cams[c["id"]] = cam
            kind = c.get("kind")
            inner = []
            if kind == "split":
                d = c["split"]
                lay = d.get("layout", "side")
                L_src, R_src = _asset(root / d["left"], assets), _asset(root / d["right"], assets)
                if lay == "side":
                    sl, sr = "left:0;width:50%;", "left:50%;width:50%;"
                elif lay == "top-bottom":
                    sl, sr = "top:0;height:50%;", "top:50%;height:50%;"
                else:
                    sl = sr = ""
                ss = c.get("source_start", 0)
                lid_ = uid(f"{c['id']}-L")
                media_ids[c["id"]] = {"el": lid_, "src": L_src, "path": root / d["left"], "source_start": ss}
                inner.append(media_el(lid_, L_src, c["start"], c["duration"], z, "pic side", ss, None, sl))
                rid = uid(f"{c['id']}-R")
                if lay == "wipe":  # the right picture wipes across the left, then holds at half
                    rcam = uid(f"wipe-{c['id']}")
                    inner.append(f'<div id="{rcam}" class="cam" style="clip-path:inset(0 0 0 100%)">{media_el(rid, R_src, c["start"], c["duration"], z, "pic side", ss, None, sr)}</div>')
                    tl.append(f'tl.fromTo("#{rcam}",{{clipPath:"inset(0% 0% 0% 100%)"}},{{clipPath:"inset(0% 0% 0% 50%)",duration:{ST["split"]["wipe_s"]},ease:"power3.inOut"}},{round(c["start"] + 0.3, 3)});')
                else:
                    inner.append(media_el(rid, R_src, c["start"], c["duration"], z, "pic side", ss, None, sr))
                div = uid(f"{c['id']}-div")
                dv = ST["split"]
                geom = (f"left:calc(50% - {dv['divider_px'] / 2}px);top:0;bottom:0;width:{dv['divider_px']}px" if lay in ("side", "wipe")
                        else f"top:calc(50% - {dv['divider_px'] / 2}px);left:0;right:0;height:{dv['divider_px']}px")
                body_div = f'<div id="{div}" class="clip" data-start="{c["start"]}" data-duration="{c["duration"]}" data-track-index="5" style="position:absolute;{geom};background:{dv["divider"]};z-index:6"></div>'
                body.append(body_div)
                for j, lab in enumerate(d.get("labels") or []):
                    lid = uid(f"{c['id']}-lab{j}")
                    x = ("left:6%" if j == 0 else "right:6%") if lay != "top-bottom" else "left:6%"
                    y = dv["label_y_pct"] if lay != "top-bottom" else (dv["label_y_pct"] if j == 0 else 50 + dv["label_y_pct"] / 2)
                    body.append(f'<div id="{lid}" class="clip lab" data-start="{c["start"]}" data-duration="{c["duration"]}" data-track-index="6" style="{x};top:{y}%"><span id="{lid}-in">{_esc(lab)}</span></div>')
                    tl.append(f'tl.fromTo("#{lid}-in",{{opacity:0,y:-18,scale:.9}},{{opacity:1,y:0,scale:1,duration:0.28,ease:"back.out(1.7)"}},{round(c["start"] + 0.15 + 0.12 * j, 3)});')
                css.append(f'.lab{{position:absolute;z-index:7}}.lab span{{display:block;font:900 {round(dv["label_size_px"] * k)}px/1 {fam(dv.get("font", ST["font_heavy"]))};{_spacing(dv, TX)};color:{dv["label_ink"]};background:{dv["label_paper"]};padding:.22em .5em;border-radius:.3em;text-transform:uppercase}}')
            elif kind == "greenscreen":
                d = c["greenscreen"]
                g = ST["greenscreen"]
                inner.append(media_el(uid(f"{c['id']}-bg"), _asset(root / d["background"], assets), c["start"], c["duration"], z, "pic"))
                talk_src = _asset(root / c["src"], assets)
                cut = (c.get("cutout") or {}).get("webm")
                cut = Path(cut) if cut and Path(cut).is_file() else None
                if d.get("layout") == "cutout":  # the presenter stands in front of the plate — BiRefNet's alpha WebM (cutout.py), else the raw clip
                    sty = f"position:absolute;left:0;right:0;bottom:{g['cutout_bottom_pct']}%;height:{g['cutout_height_pct']}%;width:100%;object-fit:contain;object-position:50% 100%"
                else:
                    sty = (f"position:absolute;right:{g['pip_right_pct']}%;bottom:{g['pip_bottom_pct']}%;width:{g['pip_width_pct']}%;aspect-ratio:9/13;height:auto;"
                           f"object-fit:cover;border-radius:{round(28 * k)}px;box-shadow:0 {round(10 * k)}px {round(40 * k)}px rgba(0,0,0,.5);border:{round(5 * k)}px solid #fff")
                gid_ = uid(c["id"])
                media_ids[c["id"]] = {"el": gid_, "src": talk_src, "path": root / c["src"], "source_start": c.get("source_start", 0)}
                if d.get("layout") == "cutout" and cut:
                    # her own clip still carries the sound (that keeps the lips right) but is not seen;
                    # the cut-out of the SAME picture, read at the same point, is what stands on the plate
                    inner.append(media_el(gid_, talk_src, c["start"], c["duration"], z, "gs", c.get("source_start", 0), c.get("volume_db"), sty + ";opacity:0"))
                    inner.append(media_el(uid(f"{c['id']}-cut"), _asset(cut, assets), c["start"], c["duration"], z, "gs cut", c.get("source_start", 0), None, sty))
                else:
                    inner.append(media_el(gid_, talk_src, c["start"], c["duration"], z, "gs", c.get("source_start", 0), c.get("volume_db"), sty))
            else:
                src = _asset(root / c["src"], assets)
                el = uid(c["id"])
                media_ids[c["id"]] = {"el": el, "src": src, "path": root / c["src"], "source_start": c.get("source_start", 0)}
                inner.append(media_el(el, src, c["start"], c["duration"], z, "pic", c.get("source_start", 0), c.get("volume_db")))
                if src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):  # a still never sits frozen: slow push or drift, alternating
                    drift = 1.06 if drift_n % 2 == 0 else 1.0
                    drift_n += 1
                    tl.append(f'tl.fromTo("#{el}",{{scale:{2.06 - drift:.2f}}},{{scale:{drift},duration:{c["duration"]},ease:"sine.inOut"}},{c["start"]});')
                elif c.get("punch", 1.0) != 1.0:
                    css.append(f'#{el}{{transform:scale({c["punch"]});transform-origin:50% 32%}}')
            pics.append(f'<div id="{cam}" class="cam" style="z-index:{z}">{"".join(inner)}</div>')

            # the words a plate carries, set on it — the plan's words, exactly
            if kind in TEXT_KINDS:
                d = c[kind]
                at = d.get("lands_at", c["start"] + 0.1)
                box = uid(f"{c['id']}-{kind}")
                box_start, box_dur = round(c["start"], 3), round(c["duration"], 3)
                if kind == "card":
                    s = ST["card"]
                    rows = "".join(f'<div class="ln" id="{box}-l{j}">{_esc(t)}</div>' for j, t in enumerate(d["lines"]))
                    body.append(f'<div id="{box}" class="clip card" data-start="{box_start}" data-duration="{box_dur}" data-track-index="25" style="{_where(d, s["zone"])}"><div class="card-in">{rows}</div></div>')
                    css.append(f'.card{{position:absolute;z-index:25}}.card-in{{width:100%}}.card .ln{{font:{s.get("weight", 900)} {round(s["size_px"] * k)}px/1.08 {fam(s.get("font", ST["font_heavy"]))};{_spacing(s, TX)};color:{s["ink"]};-webkit-text-stroke:{round(s["stroke_px"] * k)}px {s["stroke"]};paint-order:stroke fill;text-transform:uppercase;margin:.12em 0}}')
                    for j in range(len(d["lines"])):
                        tl.append(f'tl.fromTo("#{box}-l{j}",{{opacity:0,y:34,scale:.9}},{{opacity:1,y:0,scale:1,duration:0.26,ease:"back.out(1.6)"}},{round(at + j * s["stagger_s"], 3)});')
                elif kind == "screen":
                    s = ST["screen"]
                    sf = s["surfaces"].get(d["surface"], {})
                    body.append(f'<div id="{box}" class="clip screen sf-{d["surface"]}" data-start="{box_start}" data-duration="{box_dur}" data-track-index="25" style="{_where(d, s["zone"])}">{_surface(d, box, sf)}</div>')
                    css.append(_surface_css(d["surface"], sf, s, k, fam(s.get("font", ST["font"])), _spacing(s, TX)))
                    tl.append(f'tl.fromTo("#{box}-in",{{opacity:0,y:40,scale:.94}},{{opacity:1,y:0,scale:1,duration:0.32,ease:"power3.out"}},{round(at, 3)});')
                    for j in range(len(d["lines"])):
                        tl.append(f'tl.fromTo("#{box}-l{j}",{{opacity:0,y:14}},{{opacity:1,y:0,duration:0.22,ease:"power2.out"}},{round(at + 0.2 + j * 0.28, 3)});')
                else:  # endcard: the offer, the call, the guarantee
                    s = ST["endcard"]
                    rows = "".join(f'<div class="of" id="{box}-o{j}">{_esc(t)}</div>' for j, t in enumerate(d["offer_lines"]))
                    cta = f'<div class="cta" id="{box}-cta"><span>{_esc(d["cta"])}</span></div>'
                    gu = f'<div class="gu" id="{box}-gu">{_esc(d["guarantee"])}</div>' if str(d.get("guarantee", "")).strip().lower() not in ("", "none") else ""
                    body.append(f'<div id="{box}" class="clip endcard" data-start="{box_start}" data-duration="{box_dur}" data-track-index="25" style="{_where(d, s["zone"])}"><div class="ec-in">{rows}{cta}{gu}</div></div>')
                    hv = fam(s.get("font", ST["font_heavy"]))
                    css.append(f'.endcard{{position:absolute;z-index:25;color:{s["ink"]}}}.ec-in{{width:100%;{_spacing(s, TX)}}}'
                               f'.endcard .of{{font:900 {round(s["offer_size_px"] * k)}px/1.08 {hv};text-transform:uppercase;text-shadow:0 {round(4 * k)}px {round(18 * k)}px rgba(0,0,0,.6);margin:.08em 0}}'
                               f'.endcard .cta{{margin-top:.7em}}.endcard .cta span{{display:inline-block;font:900 {round(s["cta_size_px"] * k)}px/1 {hv};color:{s["cta_ink"]};background:{s["cta_paper"]};padding:.45em 1em;border-radius:999px;text-transform:uppercase}}'
                               f'.endcard .gu{{margin-top:.9em;font:700 {round(s["guarantee_size_px"] * k)}px/1.2 {fam(ST["font"])};text-shadow:0 2px 8px rgba(0,0,0,.7)}}')
                    n = len(d["offer_lines"])
                    for j in range(n):
                        tl.append(f'tl.fromTo("#{box}-o{j}",{{opacity:0,y:30,scale:.92}},{{opacity:1,y:0,scale:1,duration:0.26,ease:"back.out(1.5)"}},{round(at + j * s["stagger_s"], 3)});')
                    tl.append(f'tl.fromTo("#{box}-cta",{{opacity:0,scale:.7}},{{opacity:1,scale:1,duration:0.3,ease:"back.out(2)"}},{round(at + n * s["stagger_s"] + 0.1, 3)});')
                    if gu:
                        tl.append(f'tl.fromTo("#{box}-gu",{{opacity:0,y:12}},{{opacity:1,y:0,duration:0.24,ease:"power2.out"}},{round(at + n * s["stagger_s"] + 0.35, 3)});')

    # ------------------------------------------------ hand-offs that are not a hard cut
    spans: dict[str, list[float]] = {}
    for c in sheet["picture"]:
        sp = spans.setdefault(c.get("scene") or c["id"], [c["start"], c["start"] + c["duration"]])
        sp[0], sp[1] = min(sp[0], c["start"]), max(sp[1], c["start"] + c["duration"])
    TROWS = {x["id"]: x for x in json.loads((TOOL / "looks/transitions.json").read_text())["transitions"]}
    gl_cuts: list[dict] = []
    for r in (sheet.get("layers") or {}).get("transitions") or []:
        kind = r.get("kind", "cut")
        if kind == "cut" or r.get("after_scene") not in spans:
            continue
        T = round(spans[r["after_scene"]][1], 3)
        outs = [c for c in sheet["picture"] if abs(c["start"] + c["duration"] - T) < 0.05 and (c.get("scene") or c["id"]) == r["after_scene"]]
        ins = [c for c in sheet["picture"] if abs(c["start"] - T) < 0.05]
        o = cams.get(outs[-1]["id"]) if outs else None
        i = cams.get(ins[0]["id"]) if ins else None
        if (TROWS.get(kind) or {}).get("engine") == "gl":  # a WebGL pass over the two pictures (looks/gl-transitions, MIT)
            gl_cuts.append(GL.cut(r, TROWS[kind], T, outs, ins, media_ids, spans))
            continue
        if kind == "whip":
            if o: tl.append(f'tl.fromTo("#{o}",{{x:0,filter:"blur(0px)"}},{{x:{-round(W * 0.35)},filter:"blur(18px)",duration:0.1,ease:"power3.in"}},{round(T - 0.1, 3)});')
            if i: tl.append(f'tl.fromTo("#{i}",{{x:{round(W * 0.35)},filter:"blur(18px)"}},{{x:0,filter:"blur(0px)",duration:0.12,ease:"power3.out"}},{T});')
        elif kind == "zoom":
            if o: tl.append(f'tl.fromTo("#{o}",{{scale:1,filter:"blur(0px)"}},{{scale:1.35,filter:"blur(14px)",duration:0.11,ease:"power3.in"}},{round(T - 0.11, 3)});')
            if i: tl.append(f'tl.fromTo("#{i}",{{scale:0.82,filter:"blur(10px)"}},{{scale:1,filter:"blur(0px)",duration:0.14,ease:"power3.out"}},{T});')
        elif kind == "match":
            p = (outs[-1].get("punch") or 1.0) if outs else 1.0
            if i: tl.append(f'tl.fromTo("#{i}",{{scale:{max(p, 1.04)}}},{{scale:1,duration:0.25,ease:"power2.out"}},{T});')
        elif kind == "flash":
            fid = uid(f"flash-{r['after_scene']}")
            body.append(f'<div id="{fid}" class="flash"></div>')
            # two plain `to` tweens: a fromTo's immediate render would hold the white over every earlier frame
            tl.append(f'tl.to("#{fid}",{{opacity:1,duration:0.05,ease:"power2.in"}},{round(T - 0.05, 3)});')
            tl.append(f'tl.to("#{fid}",{{opacity:0,duration:0.1,ease:"power2.out"}},{T});')
    css.append(".flash{position:absolute;inset:0;background:#fff;opacity:0;z-index:15;pointer-events:none}")
    gl_pics, gl_script = GL.build([g for g in gl_cuts if g], W, H, uid, media_el, sheet) if any(gl_cuts) else ([], "")
    pics.extend(gl_pics)

    # ------------------------------------------------ sound
    track = 10
    for key in ("voice", "music"):
        a = sheet.get(key)
        if a:
            src = _asset(root / a["src"], assets)
            dur = f' data-duration="{a["duration"]}"' if a.get("duration") else ""
            ms = f' data-media-start="{a["source_start"]}"' if a.get("source_start") else ""
            if key == "music" and (a.get("duck") or {}).get("points"):
                body.append(f'<audio id="music" data-start="{a.get("start", 0)}"{dur}{ms} data-track-index="{track}" data-volume="1" data-automation="{_auto(a["duck"]["points"])}" src="{src}"></audio>')
            else:
                body.append(f'<audio id="{key}" data-start="{a.get("start", 0)}"{dur}{ms} data-track-index="{track}" data-volume="{db_to_volume(a.get("volume_db", 0))}" src="{src}"></audio>')
            track += 1
    for v in sheet.get("voice_cuts") or []:
        src = _asset(root / v["src"], assets)
        body.append(f'<audio id="{uid(v["id"])}" data-start="{v["start"]}" data-duration="{v["duration"]}" data-media-start="{v["source_start"]}" data-track-index="{track}" data-volume="{db_to_volume(v.get("volume_db", 0))}" src="{src}"></audio>')
    track += 1
    for r in sheet.get("room_tone") or []:  # quiet air under every trimmed join, so a cut never drops to dead silence
        src = _asset(root / r["src"], assets)
        v, d = db_to_volume(r.get("volume_db", -30)), r["duration"]
        f = min(0.06, d / 3)
        pts = [{"t": 0, "v": 0}, {"t": round(f, 3), "v": v}, {"t": round(d - f, 3), "v": v}, {"t": round(d, 3), "v": 0}]
        body.append(f'<audio id="{uid(r["id"])}" data-start="{r["start"]}" data-duration="{d}" data-media-start="{r.get("source_start", 0)}" data-track-index="{track}" data-volume="1" data-automation="{_auto(pts)}" src="{src}"></audio>')
    track += 1
    lead = ((sheet.get("controls") or {}).get("sound") or {}).get("sfx_lead_frames", 2) / fps
    for s in sheet.get("sfx") or []:
        if s.get("at") is None:
            continue
        src = _asset(root / s["src"], assets)
        body.append(f'<audio id="{uid(s["id"])}" data-start="{max(0, round(s["at"] - lead, 3))}" data-track-index="{track}" data-volume="{db_to_volume(s.get("volume_db", -8))}" src="{src}"></audio>')
        track += 1

    # ------------------------------------------------ captions — a setting, never a re-edit
    caps = sheet.get("captions") or {}
    if captions and caps.get("words"):
        L = look_of(sheet)
        fixes = {f["from"]: f["to"] for f in caps.get("fixes") or []}
        size = round(L["size_px"] * k)
        stroke = round(L.get("stroke_px", 0) * k)
        # one normal space between words: the spans are joined by a single space and carry NO margin
        # (until 2026-09-23 they also had `margin:0 .22em`, which doubled every gap — the owner: "a lot of space between words")
        cap_font = fam(L["font"]) if L.get("font") in FT.rows() else L.get("font", fam("inter"))
        css.append(f""".cap{{position:absolute;z-index:20;
font-family:{cap_font};font-weight:{L['weight']};font-size:{size}px;line-height:1.08;color:{L['color']};{_spacing(L)};
text-transform:{'uppercase' if L.get('case') == 'upper' else 'none'};text-shadow:{L.get('shadow', 'none')};
{f'-webkit-text-stroke:{stroke}px {L["stroke"]};paint-order:stroke fill;' if stroke else ''}}}
.cap span{{display:inline-block}}
.cap .plate{{display:inline-block;padding:.18em .5em;border-radius:.2em;background:{L.get('plate', 'transparent')}}}""")
        # THE WORD BOX (the owner, 2026-10-10, the first song ad): a box behind the ONE word being said or sung,
        # moving word to word — until then only the whole line could sit on a box (`plate`)
        word_box = L.get("word_box")
        if word_box:
            css.append(".cap .wb{padding:.04em .16em;margin:0 -.16em;border-radius:.14em;background:transparent}")
        cap_zones = caps.get("zones") or {}
        look_zone = L.get("zone") or ("caption-band" if L.get("y_pct") is None else None)

        def cap_box(t: float) -> str:
            """The zone for a caption line: its scene's (moved off the face if placement moved it), else the look's."""
            on = [c for c in sheet["picture"] if c["start"] <= t < c["start"] + c["duration"]]
            on.sort(key=lambda c: 0 if c.get("roll") == "b" else 1)
            sc = (on[0].get("scene") or on[0]["id"]) if on else None
            z = (cap_zones.get(sc) or {}).get("zone") or look_zone
            return _box(z) if z else _where({"y_pct": L["y_pct"]}, "caption-band")
        quiet = [(c["start"], c["start"] + c["duration"]) for c in sheet["picture"] if c.get("kind") in TEXT_KINDS]  # a plate's own words are on screen: no second line of text
        lines = [ln for ln in caption_lines(caps["words"], L["max_words"])
                 if not any(a <= (ln[0]["start"] + ln[-1]["end"]) / 2 < b for a, b in quiet)]
        for i, line in enumerate(lines):
            s, e = line[0]["start"], line[-1]["end"]
            nxt = e + 0.12
            if i + 1 < len(lines):  # never two lines on screen at once
                nxt = max(e, min(nxt, lines[i + 1][0]["start"] - 0.07))
            lid = f"cap{i}"
            spans_html = " ".join(f'<span id="{lid}w{j}"' + (' class="wb"' if word_box else "")
                                  + f'>{html.escape(fixes.get(w["text"], w["text"]))}</span>' for j, w in enumerate(line))
            body.append(f'<div id="{lid}" class="clip cap" data-start="{round(max(0, s - 0.06), 3)}" data-duration="{round(nxt - max(0, s - 0.06), 3)}" data-track-index="20" style="{cap_box((s + e) / 2)}"><div class="plate" id="{lid}p">{spans_html}</div></div>')
            y = 26 if L.get("entrance") == "rise" else 0
            sc = 0.86 if L.get("entrance") == "pop" else 1
            tl.append(f'tl.fromTo("#{lid}p",{{opacity:0,y:{y},scale:{sc}}},{{opacity:1,y:0,scale:1,duration:0.16,ease:"back.out(1.6)"}},{round(max(0, s - 0.06), 3)});')
            tl.append(f'tl.to("#{lid}p",{{opacity:0,duration:0.08,ease:"power2.in"}},{round(nxt - 0.08, 3)});')
            if word_box:
                for j, w in enumerate(line):
                    off = min(w["end"], line[j + 1]["start"]) if j + 1 < len(line) else w["end"]
                    tl.append(f'tl.set("#{lid}w{j}",{{backgroundColor:"{word_box}"}},{round(w["start"], 3)});')
                    tl.append(f'tl.set("#{lid}w{j}",{{backgroundColor:"transparent"}},{round(off, 3)});')
            if L["highlight"].lower() != L["color"].lower():
                for j, w in enumerate(line):
                    tl.append(f'tl.to("#{lid}w{j}",{{color:"{L["highlight"]}",scale:1.08,duration:0.08,ease:"power2.out"}},{w["start"]});')
                    off = min(w["end"], line[j + 1]["start"]) if j + 1 < len(line) else w["end"]
                    tl.append(f'tl.to("#{lid}w{j}",{{color:"{L["color"]}",scale:1,duration:0.08,ease:"power2.in"}},{round(off, 3)});')

    # ------------------------------------------------ overlays — hooks, labels
    for o in sheet.get("overlays") or []:
        oid = uid(o["id"])
        hk = ST["hook"]
        css.append(f'#{oid}{{position:absolute;{_where(o, hk["zone"])};z-index:30;font:{hk.get("weight", 900)} {round(hk["size_px"] * k)}px/1.1 {fam(hk.get("font", ST["font_heavy"]))};{_spacing(hk, TX)};color:{hk["ink"]};}}#{oid} b{{display:inline-block;background:{hk["paper"]};padding:.12em .4em;border-radius:.18em;line-height:1.1}}#{oid} .hl{{display:block;margin:0 0 .14em}}')
        rows = "".join(f'<span class="hl"><b>{html.escape(t)}</b></span>' for t in str(o.get("text", "")).split("\n"))
        body.append(f'<div id="{oid}" class="clip" data-start="{o["start"]}" data-duration="{o["duration"]}" data-track-index="30"><div id="{oid}-in">{rows}</div></div>')
        if o["start"] > 0.05:  # a hook that opens the video is simply THERE on frame one — no fade, no slide
            tl.append(f'tl.fromTo("#{oid}-in",{{opacity:0,y:-30,scale:.94}},{{opacity:1,y:0,scale:1,duration:0.3,ease:"power3.out"}},{o["start"]});')
        tl.append(f'tl.to("#{oid}-in",{{opacity:0,y:-16,duration:0.15,ease:"power2.in"}},{round(o["start"] + o["duration"] - 0.15, 3)});')

    # ------------------------------------------------ layers set on top
    LY = sheet.get("layers") or {}
    lt = ST["lower_third"]
    for r in LY.get("lower_thirds") or []:
        if r.get("start") is None:
            continue
        i = uid(r["id"])
        body.append(f'<div id="{i}" class="clip lt" data-start="{r["start"]}" data-duration="{r["duration"]}" data-track-index="32" style="{_where(r, lt["zone"])}"><div id="{i}-in" class="lt-in"><div class="nm">{_esc(r.get("name"))}</div><div class="tt">{_esc(r.get("title"))}</div></div></div>')
        tl.append(f'tl.fromTo("#{i}-in",{{opacity:0,x:{-round(60 * k)}}},{{opacity:1,x:0,duration:0.3,ease:"power3.out"}},{r["start"]});')
        tl.append(f'tl.to("#{i}-in",{{opacity:0,x:{-round(30 * k)},duration:0.15,ease:"power2.in"}},{round(r["start"] + r["duration"] - 0.15, 3)});')
    ltf = fam(lt.get("font", ST["font"]))
    css.append(f'.lt{{position:absolute;z-index:32}}.lt-in{{background:{lt["paper"]};color:{lt["ink"]};padding:.5em .8em;border-left:{round(8 * k)}px solid {lt["accent"]};border-radius:{round(8 * k)}px;text-align:left;{_spacing(lt, TX)}}}'
               f'.lt .nm{{font:800 {round(lt["name_size_px"] * k)}px/1.1 {ltf}}}.lt .tt{{font:500 {round(lt["title_size_px"] * k)}px/1.2 {ltf};opacity:.85;margin-top:.15em}}')
    an = ST["annotation"]
    for r in LY.get("annotations") or []:
        if r.get("start") is None or not r.get("place"):
            continue
        i = uid(r["id"])
        p = r["place"]
        x0, y0 = p["x_pct"] - p["w_pct"] / 2, p["y_pct"] - p["h_pct"] / 2
        sw = round(an["stroke_px"] * k)
        box = f'left:{x0}%;top:{y0}%;width:{p["w_pct"]}%;height:{p["h_pct"]}%'
        keys = (r.get("follow") or {}).get("keys") or []
        follow = len(keys) > 1

        def ann_div(content: str) -> str:
            """A fixed annotation IS its box; one that follows the person is a full-frame clip with a mover
            inside it (the .clip itself is never tweened), moved key to key by the timeline."""
            if not follow:
                return f'<div id="{i}" class="clip ann" data-start="{r["start"]}" data-duration="{r["duration"]}" data-track-index="33" style="{box}">{content}</div>'
            return (f'<div id="{i}" class="clip ann" data-start="{r["start"]}" data-duration="{r["duration"]}" data-track-index="33" style="left:0;top:0;width:100%;height:100%">'
                    f'<div id="{i}-mv" style="position:absolute;{box}">{content}</div></div>')
        if follow:  # smoothed keyframes (follow.py): only the position moves, eased between keys
            off = lambda q: (round((q["x_pct"] - p["x_pct"]) / 100 * W, 1), round((q["y_pct"] - p["y_pct"]) / 100 * H, 1))  # noqa: E731
            for a_, b_ in zip(keys, keys[1:]):
                (ax, ay), (bx, by) = off(a_), off(b_)
                dt = round(b_["t"] - a_["t"], 3)
                if dt > 0:
                    tl.append(f'tl.fromTo("#{i}-mv",{{x:{ax},y:{ay}}},{{x:{bx},y:{by},duration:{dt},ease:"sine.inOut",immediateRender:false}},{a_["t"]});')
        if r["kind"] == "highlight":
            body.append(ann_div(f'<div id="{i}-in" style="position:absolute;inset:0;background:{an["highlight"]};mix-blend-mode:multiply;transform-origin:0 50%;border-radius:{round(10 * k)}px"></div>'))
            tl.append(f'tl.fromTo("#{i}-in",{{scaleX:0}},{{scaleX:1,duration:{an["draw_s"]},ease:"power2.out"}},{r["start"]});')
            continue
        w, h = round(W * p["w_pct"] / 100), round(H * p["h_pct"] / 100)  # drawn in the box's own pixels, so the stroke keeps its weight and pathLength holds
        shape = {"circle": [f'<ellipse cx="{w / 2}" cy="{h / 2}" rx="{w * .47}" ry="{h * .44}" pathLength="1"/>'],
                 "underline": [f'<path d="M{w * .02} {h * .96} Q{w * .5} {h * .9} {w * .98} {h * .95}" pathLength="1"/>'],
                 "arrow": [f'<path d="M{-w * .35} {h * 1.6} Q{-w * .12} {h * .95} {w * .1} {h * .55}" pathLength="1"/>',
                           f'<path d="M{w * .1 - 34 * k} {h * .55 + 4 * k} L{w * .1} {h * .55} L{w * .1 - 8 * k} {h * .55 + 34 * k}" pathLength="1"/>']}[r["kind"]]
        ink = an["ink"]                                       # hoisted: a nested same-quote f-string needs 3.12 (builder card rule 10)
        strokes = "".join(x.replace("pathLength", 'stroke-dasharray="1 1" stroke-dashoffset="1" pathLength') for x in shape)
        body.append(ann_div(f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" style="position:absolute;left:0;top:0;overflow:visible"><g id="{i}-in" fill="none" stroke="{ink}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{strokes}</g></svg>'))
        tl.append(f'tl.fromTo("#{i}-in > *",{{attr:{{"stroke-dashoffset":1}}}},{{attr:{{"stroke-dashoffset":0}},duration:{an["draw_s"]},ease:"power2.inOut",stagger:0.12}},{r["start"]});')
    css.append(".ann{position:absolute;z-index:33;pointer-events:none}")
    UIS = {x["id"]: x for x in json.loads((TOOL / "looks/platform_ui.json").read_text())["styles"]}
    UIK = json.loads((TOOL / "looks/platform_ui.json").read_text())["kinds"]
    for r in LY.get("platform_ui") or []:
        if r.get("start") is None:
            continue
        i = uid(r["id"])
        st = UIS.get(r.get("style") or (UIK.get(r["kind"]) or {}).get("default"))
        if not st:
            continue
        inner, extra_tl = _ui(r, st, i, k, fam(st["draw"]["font"]), _spacing(st["draw"], TX))
        body.append(f'<div id="{i}" class="clip ui" data-start="{r["start"]}" data-duration="{r["duration"]}" data-track-index="34" style="{_where(r, st["zone"])}">{inner}</div>')
        tl.append(f'tl.fromTo("#{i}-in",{{opacity:0,y:{round(-24 * k)},scale:.9}},{{opacity:1,y:0,scale:1,duration:0.28,ease:"back.out(1.6)"}},{r["start"]});')
        tl.append(f'tl.to("#{i}-in",{{opacity:0,scale:.94,duration:0.14,ease:"power2.in"}},{round(r["start"] + r["duration"] - 0.14, 3)});')
        for kind_, j, t in extra_tl:
            if kind_ == "char":
                tl.append(f'tl.set("#{i}-c{j}",{{opacity:1}},{round(r["start"] + t, 3)});')
            else:
                tl.append(f'tl.fromTo("#{i}-b{j}",{{opacity:0,y:{round(18 * k)},scale:.92}},{{opacity:1,y:0,scale:1,duration:0.22,ease:"back.out(1.7)"}},{round(r["start"] + t, 3)});')
    css.append(".ui{position:absolute;z-index:34}")
    icons_layer(LY.get("icons") or [])
    dsty = ST["disclaimer"]
    for r in LY.get("disclaimers") or []:
        i = uid(r["id"])
        body.append(f'<div id="{i}" class="clip disc" data-start="{r["start"]}" data-duration="{r["duration"]}" data-track-index="35" style="{_where(r, dsty["zone"])}"><div>{_esc(r["text"])}</div></div>')
    css.append(f'.disc{{position:absolute;z-index:35;font:500 {round(dsty["size_px"] * k)}px/1.25 {fam(dsty.get("font", ST["font"]))};{_spacing(dsty, TX)};color:{dsty["ink"]};text-shadow:{dsty["shadow"]}}}')

    draws_script = ("".join(draw_fns) + GL.HOOK) if (draw_fns or gl_script) else ""
    faces = []
    for f in sorted(used_fonts):
        face, files = FT.faces(f)
        if face:
            faces.append(face)
            (project / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
            for src in files:
                shutil.copy2(src, project / "assets" / "fonts" / f"{f}-{src.name}")
    css.insert(0, "".join(faces))

    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><script src="{GSAP}"></script>
<style>html,body{{margin:0;background:#000}}#stage{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:#000}}
#picture{{position:absolute;inset:0;filter:{_grade(sheet)}}}
.cam{{position:absolute;inset:0;overflow:hidden}}
.pic{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.pic.side{{inset:auto;top:0;left:0;width:100%;height:100%}}
{''.join(dict.fromkeys(css))}</style></head><body>
<div id="stage" data-composition-id="{cid}" data-start="0" data-width="{W}" data-height="{H}" data-fps="{fps}" data-duration="{round(end, 3)}">
<div id="picture">
{chr(10).join(pics)}
</div>
{chr(10).join(body)}
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(tl)}
{gl_script}{draws_script}
window.__timelines = window.__timelines || {{}};
window.__timelines["{cid}"] = tl;
</script>
</div></body></html>
"""
    project.mkdir(parents=True, exist_ok=True)
    (project / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}}, indent=1))
    (project / "meta.json").write_text(json.dumps({"id": meta["label"], "name": meta["label"]}, indent=1))
    out = project / "index.html"
    out.write_text(page)
    return out


def _surface(d: dict, box: str, sf: dict) -> str:
    """The legible text of a screen, set per surface. The plate is the screen; these are its words."""
    lines = [_esc(t) for t in d.get("lines") or []]
    L = lambda j, t, cls="": f'<div class="{cls}" id="{box}-l{j}">{t}</div>'  # noqa: E731
    s = d["surface"]
    if s == "review":
        inner = f'<div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>' + "".join(L(j, t, "rv-name" if j == 0 and len(lines) > 1 else "rv-text") for j, t in enumerate(lines))
    elif s == "comment":
        inner = '<div class="av"></div><div class="cm">' + "".join(L(j, t, "cm-h" if j == 0 and len(lines) > 1 else "cm-t") for j, t in enumerate(lines)) + "</div>"
    elif s == "dm":
        inner = "".join(L(j, t, "dm-them" if j % 2 == 0 else "dm-us") for j, t in enumerate(lines))
    elif s == "site":
        inner = '<div class="bar"><i></i><i></i><i></i><span></span></div>' + "".join(L(j, t, "st-h" if j == 0 else "st-t") for j, t in enumerate(lines))
    elif s == "order":
        inner = '<div class="tick">&#10003;</div>' + "".join(L(j, t, "od-h" if j == 0 else "od-r") for j, t in enumerate(lines))
    else:  # search
        inner = "".join(L(j, t, "sr-q" if j == 0 else "sr-r") for j, t in enumerate(lines))
    return f'<div id="{box}-in" class="sf-in">{inner}</div>'


def _surface_css(s: str, sf: dict, st: dict, k: float, font: str, spacing: str = "") -> str:
    fs = round(st["size_px"] * k)
    base = (f'.screen{{position:absolute;z-index:25}}'
            f'.screen .sf-in{{width:100%;box-sizing:border-box;text-align:left;{spacing};font:500 {fs}px/1.3 {font};color:{sf.get("ink", "#111")};background:{sf.get("paper", "#fff")};border-radius:{round(28 * k)}px;padding:.9em 1em;box-shadow:0 {round(12 * k)}px {round(44 * k)}px rgba(0,0,0,.45)}}')
    per = {
        "review": f'.sf-review .stars{{color:{sf.get("accent")};font-size:1.3em;letter-spacing:.1em}}.sf-review .rv-name{{font-weight:800;margin:.2em 0}}.sf-review .rv-text{{margin-top:.2em}}',
        "comment": f'.sf-comment .sf-in{{display:flex;gap:.6em;align-items:flex-start}}.sf-comment .av{{flex:0 0 1.9em;height:1.9em;border-radius:50%;background:{sf.get("accent")}}}.sf-comment .cm-h{{font-weight:700;font-size:.8em;opacity:.65}}.sf-comment .cm-t{{font-weight:600}}',
        "dm": f'.sf-dm .sf-in{{display:flex;flex-direction:column;gap:.4em}}.sf-dm .dm-them,.sf-dm .dm-us{{max-width:78%;padding:.45em .75em;border-radius:1.1em}}.sf-dm .dm-them{{align-self:flex-start;background:#fff}}.sf-dm .dm-us{{align-self:flex-end;background:{sf.get("accent")};color:#fff}}',
        "site": f'.sf-site .bar{{display:flex;gap:.3em;align-items:center;background:{sf.get("accent")};border-radius:.5em;padding:.35em .5em;margin-bottom:.7em}}.sf-site .bar i{{width:.5em;height:.5em;border-radius:50%;background:#bbb}}.sf-site .bar span{{flex:1;height:.7em;background:#fff;border-radius:.35em;margin-left:.4em}}.sf-site .st-h{{font-weight:900;font-size:1.25em;line-height:1.1}}.sf-site .st-t{{margin-top:.35em}}',
        "order": f'.sf-order .tick{{width:1.6em;height:1.6em;border-radius:50%;background:{sf.get("accent")};color:#fff;text-align:center;line-height:1.6em;font-weight:900;margin-bottom:.4em}}.sf-order .od-h{{font-weight:900;font-size:1.15em}}.sf-order .od-r{{border-top:1px solid #e5e5e5;padding-top:.3em;margin-top:.3em}}',
        "search": f'.sf-search .sr-q{{border:2px solid {sf.get("accent")};border-radius:999px;padding:.4em .8em;font-weight:600}}.sf-search .sr-r{{margin-top:.5em;padding-left:.8em;color:#1a0dab}}',
    }
    return base + per.get(s, "")


# ---------------------------------------------------------------- platform UI, per style (looks/platform_ui.json)
HEART = '<svg viewBox="0 0 24 24" width="1em" height="1em" style="vertical-align:-.12em"><path d="M12 21s-7.5-4.6-9.8-9.1C.6 8.6 2.6 4.6 6.4 4.3c2.3-.2 4 1 5.6 3 1.6-2 3.3-3.2 5.6-3 3.8.3 5.8 4.3 4.2 7.6C19.5 16.4 12 21 12 21z" fill="currentColor"/></svg>'
PLAY = '<svg viewBox="0 0 24 24" width="1em" height="1em" style="vertical-align:-.12em"><path d="M7 4.5v15l12.5-7.5z" fill="currentColor"/></svg>'
MAG = '<svg viewBox="0 0 24 24" width="1em" height="1em" style="vertical-align:-.14em;margin-right:.45em;opacity:.55"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2.4"/><path d="M15.5 15.5 21 21" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>'
STAR = '<svg viewBox="0 0 24 24" width="1em" height="1em" style="vertical-align:-.12em"><path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z" fill="currentColor"/></svg>'


def _ui(r: dict, st: dict, i: str, k: float, font: str, spacing: str) -> tuple[str, list]:
    """One platform-UI element drawn from its style. Returns its HTML and the extra beats
    (typed characters, bubbles landing one by one) as (kind, index, seconds-after-start)."""
    d, kind = st["draw"], st["kind"]
    fs = round(d.get("size_px", 34) * k)
    rad = round(d.get("radius_px", 24) * k) if d.get("radius_px", 0) < 900 else 999
    handle = _esc(r.get("handle"))
    text = str(r.get("text") or "")
    av_letter = _esc((str(r.get("handle") or r.get("name") or "?").lstrip("@")[:1] or "?").upper())
    avatar = (f'<div style="flex:0 0 1.9em;height:1.9em;border-radius:50%;background:{d.get("avatar_fill", "#888")};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.9em">{av_letter}</div>'
              if d.get("avatar") == "circle" else "")
    card = (f'font-family:{font};{spacing};font-size:{fs}px;font-weight:{d.get("weight", 400)};color:{d.get("ink")};background:{d.get("fill")};'
            f'border-radius:{rad}px;box-shadow:{d.get("shadow", "none")};line-height:1.25')
    sub = f'color:{d.get("sub_ink", d.get("ink"))};font-size:.72em;font-weight:500'
    extra: list = []
    if kind == "comment_reply":
        tail = (f'<div style="position:absolute;left:1.1em;bottom:-.5em;width:1em;height:1em;background:{d.get("fill")};transform:rotate(45deg);border-radius:.15em"></div>' if d.get("tail") else "")
        inner = (f'<div id="{i}-in" style="position:relative;width:100%;box-sizing:border-box;padding:.6em .8em;{card}"><div style="display:flex;gap:.55em;align-items:flex-start">{avatar}'
                 f'<div><div style="{sub}">Reply to {handle}\'s comment</div><div style="font-weight:{d.get("weight", 700)}">{_esc(text)}</div></div></div>{tail}</div>')
    elif kind in ("ig_comment", "youtube_comment"):
        meta = f'<div style="{sub};margin-bottom:.15em">{handle} · {_esc(r.get("ago") or "2d")}</div>' if kind == "youtube_comment" else ""
        lead = "" if kind == "youtube_comment" else f'<b style="font-weight:700">{handle}</b> '
        foot = (f'<div style="{sub};margin-top:.3em">{_esc(r.get("count") or "")} likes · Reply</div>' if kind == "youtube_comment"
                else f'<div style="{sub};margin-top:.25em">{_esc(r.get("ago") or "2d")} · {_esc(r.get("count") or "")} likes · Reply</div>')
        trail = f'<div style="margin-left:auto;color:{d.get("sub_ink")};font-size:.8em">{HEART}</div>' if d.get("trailing") == "heart" else ""
        inner = (f'<div id="{i}-in" style="width:100%;box-sizing:border-box;padding:.6em .8em;{card};display:flex;gap:.6em;align-items:flex-start">{avatar}'
                 f'<div style="flex:1">{meta}<div>{lead}{_esc(text)}</div>{foot}</div>{trail}</div>')
    elif kind == "x_post":
        name = _esc(r.get("name") or str(r.get("handle") or "").lstrip("@"))
        counts = r.get("counts") or ["24", "118", "2.4K"]
        row = f'<div style="{sub};display:flex;gap:1.6em;margin-top:.5em">&#9711; {_esc(counts[0])} <span>&#8634; {_esc(counts[1])}</span><span>{HEART} {_esc(counts[2])}</span></div>'
        inner = (f'<div id="{i}-in" style="width:100%;box-sizing:border-box;padding:.75em .9em;{card}"><div style="display:flex;gap:.55em;align-items:center;margin-bottom:.35em">{avatar}'
                 f'<div><div style="font-weight:800">{name}</div><div style="{sub}">{handle}</div></div></div><div>{_esc(text)}</div>{row}</div>')
    elif kind in ("imessage", "whatsapp", "dm_generic"):
        lines = r.get("lines") or [x for x in text.split("\n") if x.strip()]
        first_us = r.get("first") == "us"
        bubbles = []
        for j, t in enumerate(lines):
            us = (j % 2 == 0) == first_us
            fill, ink = (d.get("us_fill"), d.get("us_ink")) if us else (d.get("them_fill"), d.get("them_ink"))
            stamp = f'<span style="font-size:.55em;opacity:.55;margin-left:.6em;white-space:nowrap">9:4{j % 10} am</span>' if d.get("stamp") else ""
            bubbles.append(f'<div id="{i}-b{j}" style="align-self:{"flex-end" if us else "flex-start"};max-width:78%;padding:.45em .75em;border-radius:{rad}px;background:{fill};color:{ink};box-shadow:{d.get("shadow", "none")}">{_esc(t)}{stamp}</div>')
            extra.append(("bubble", j, 0.15 + j * 0.55))
        inner = f'<div id="{i}-in" style="width:100%;display:flex;flex-direction:column;gap:.35em;font-family:{font};{spacing};font-size:{fs}px;line-height:1.25">{"".join(bubbles)}</div>'
    elif kind in ("stitch", "duet"):
        inner = f'<div id="{i}-in" style="display:inline-block;padding:.35em .75em;{card};font-weight:{d.get("weight", 700)}">{"Stitched with" if kind == "stitch" else "Duet with"} {handle}</div>'
    elif kind == "search":
        chars = "".join(f'<span id="{i}-c{j}" style="opacity:0">{_esc(ch)}</span>' for j, ch in enumerate(text))
        extra += [("char", j, 0.3 + j * d.get("type_s_per_char", 0.05)) for j in range(len(text))]
        inner = f'<div id="{i}-in" style="width:100%;box-sizing:border-box;padding:.55em .9em;{card};white-space:nowrap;overflow:hidden">{MAG}{chars}</div>'
    elif kind in ("likes", "views"):
        glyph = HEART if kind == "likes" else PLAY
        inner = (f'<div id="{i}-in" style="display:inline-flex;flex-direction:{"column" if kind == "likes" else "row"};align-items:center;gap:.25em;padding:{".2em" if kind == "likes" else ".3em .6em"};{card};text-shadow:{d.get("shadow", "none")};box-shadow:none">'
                 f'<div style="color:{d.get("accent")};font-size:{"2.2em" if kind == "likes" else "1em"};line-height:1">{glyph}</div><div style="font-weight:800">{_esc(text)}</div></div>')
    else:  # review
        n = int(r.get("stars") or d.get("stars") or 5)
        stars = "".join(f'<span style="color:{d.get("accent") if j < n else "#D1D5DB"}">{STAR}</span>' for j in range(5))
        who = _esc(r.get("name") or r.get("handle") or "Verified buyer")
        inner = (f'<div id="{i}-in" style="width:100%;box-sizing:border-box;padding:.7em .9em;{card}"><div style="font-size:1.25em;letter-spacing:.08em">{stars}</div>'
                 f'<div style="display:flex;gap:.5em;align-items:center;margin:.35em 0">{avatar}<div><div style="font-weight:800">{who}</div><div style="{sub}">Verified buyer</div></div></div>'
                 f'<div>&ldquo;{_esc(text)}&rdquo;</div></div>')
    return inner, extra


# ---------------------------------------------------------------- icons, emoji, stickers, drawn elements (looks/icons.json)
def _star_pts(n: int, ro: float, ri: float, cx: float = 50, cy: float = 50, rot: float = -90) -> str:
    import math
    pts = []
    for j in range(n * 2):
        a = math.radians(rot + j * 180 / n)
        rr = ro if j % 2 == 0 else ri
        pts.append(f"{cx + rr * math.cos(a):.2f},{cy + rr * math.sin(a):.2f}")
    return " ".join(pts)


def _icon(ic: dict, r: dict, i: str, px: int, k: float, ist: dict, font: str) -> tuple[str, dict]:
    """The element's HTML (its moving part is `#{i}-in`) and what its animation needs."""
    ink, red, gold, paper = ist.get("ink", "#fff"), ist.get("accent", "#FF3B30"), ist.get("gold", "#F5B301"), ist.get("paper", "#fff")
    sh = "drop-shadow(0 4px 10px rgba(0,0,0,.45))"
    txt = _esc(r.get("text"))
    wrap = lambda inner, w=px, h=px, extra="": f'<div id="{i}-in" class="icn-in" style="width:{w}px;height:{h}px;filter:{sh};{extra}">{inner}</div>'  # noqa: E731
    draw = lambda paths, col, sw=9, vb="0 0 100 100": (f'<svg viewBox="{vb}" width="100%" height="100%" style="overflow:visible"><g fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">'  # noqa: E731
                                                     + "".join(f'<path d="{p}" pathLength="1" stroke-dasharray="1 1" stroke-dashoffset="1"/>' for p in paths) + "</g></svg>")
    label = lambda size_px, col="#fff": f'<div style="position:absolute;inset:18%;display:flex;align-items:center;justify-content:center;text-align:center;font:900 {size_px}px/1.05 {font};color:{col};text-transform:uppercase;word-spacing:normal;letter-spacing:0">{txt}</div>'  # noqa: E731
    anim: dict = {}
    kind, iid = ic["kind"], ic["id"]
    if kind in ("icon", "emoji", "sticker"):
        svg = IC.svg(iid)
        body = svg if svg else f'<div style="font-size:{round(px * .82)}px;line-height:{px}px;text-align:center;color:{ink}">{html.escape(ic.get("fallback_char", "?"))}</div>'
        extra = f"color:{ink}"
        if kind == "sticker":
            o = max(3, round(6 * k))
            extra += f";filter:drop-shadow({o}px 0 0 #fff) drop-shadow(-{o}px 0 0 #fff) drop-shadow(0 {o}px 0 #fff) drop-shadow(0 -{o}px 0 #fff) {sh}"
        return f'<div id="{i}-in" class="icn-in" style="width:{px}px;height:{px}px;filter:{sh};{extra}">{body}</div>', anim
    if iid == "arrow-straight":
        return wrap(draw(["M12 88 L84 16", "M56 14 L86 14 L86 44"], red)), anim
    if iid == "arrow-curved":
        return wrap(draw(["M10 88 Q16 22 84 20", "M62 6 L86 20 L66 40"], red)), anim
    if iid == "arrow-hand":
        return wrap(draw(["M12 90 C16 72 28 62 33 52 S50 28 80 18", "M60 9 L82 17 L71 37"], red, 11)), anim
    if iid == "ring":
        return wrap(draw(["M50 8 C80 7 95 30 92 52 C89 79 65 93 43 90 C17 87 5 65 9 43 C13 21 32 9 58 13"], red), round(px * 1.4), px), anim
    if iid == "underline-scribble":
        return wrap(draw(["M5 22 Q50 8 100 20 T195 16", "M22 32 Q92 22 182 30"], red, 7, "0 0 200 40"), round(px * 2.2), round(px * .44)), anim
    if iid == "highlight-marker":
        return (f'<div id="{i}-in" class="icn-in" style="transform-origin:0 50%;background:rgba(255,216,74,.85);padding:.08em .35em;border-radius:.12em;font:900 {round(px * .32)}px/1.15 {font};color:#111;text-transform:uppercase">{txt or "&nbsp;" * 12}</div>', anim)
    if iid == "checkmark":
        return wrap(draw(["M14 54 L40 80 L88 22"], "#1FAA59", 13)), anim
    if iid == "cross":
        return wrap(draw(["M20 20 L80 80", "M80 20 L20 80"], red, 13)), anim
    if iid == "star-rating":
        v = max(0.0, min(5.0, float(r.get("value") or 5)))
        star = lambda x, col: f'<polygon points="{_star_pts(5, 46, 19, x, 50)}" fill="{col}"/>'  # noqa: E731
        grey = "".join(star(50 + j * 104, "rgba(255,255,255,.35)") for j in range(5))
        gold_ = "".join(star(50 + j * 104, gold) for j in range(5))
        anim["fill_to"] = round(v / 5 * 520, 1)
        return wrap(f'<svg viewBox="0 0 520 100" width="100%" height="100%"><defs><clipPath id="{i}-clip"><rect id="{i}-fill" x="0" y="0" width="0" height="100"/></clipPath></defs>{grey}<g clip-path="url(#{i}-clip)">{gold_}</g></svg>',
                    round(px * 3.2), round(px * .62)), anim
    if iid == "badge-seal":
        return wrap(f'<svg viewBox="0 0 100 100" width="100%" height="100%"><polygon points="{_star_pts(24, 49, 43)}" fill="{gold}"/><circle cx="50" cy="50" r="36" fill="none" stroke="#fff" stroke-width="2.5" stroke-dasharray="3 3"/></svg>{label(round(px * (0.2 if len(txt) <= 6 else 0.14)), "#111")}', extra="position:relative"), anim
    if iid == "price-tag":
        return wrap(f'<svg viewBox="0 0 160 100" width="100%" height="100%"><path d="M4 50 L40 8 H150 a6 6 0 0 1 6 6 V86 a6 6 0 0 1-6 6 H40 Z" fill="{paper}"/><circle cx="36" cy="50" r="7" fill="#222"/></svg>'
                    f'<div style="position:absolute;left:28%;right:4%;top:0;bottom:0;display:flex;align-items:center;justify-content:center;font:900 {round(px * .3)}px/1 {font};color:#111">{txt}</div>',
                    round(px * 1.6), px, "position:relative;transform-origin:10% 50%"), anim
    if iid in ("burst-new", "burst-sale"):
        fill = "#FFD84A" if iid == "burst-new" else red
        col = "#111" if iid == "burst-new" else "#fff"
        words = txt or ("NEW" if iid == "burst-new" else "SALE")
        return (f'<div id="{i}-in" class="icn-in" style="width:{px}px;height:{px}px;filter:{sh};position:relative"><svg viewBox="0 0 100 100" width="100%" height="100%"><polygon points="{_star_pts(16, 50, 38)}" fill="{fill}"/></svg>'
                f'<div style="position:absolute;inset:14%;display:flex;align-items:center;justify-content:center;text-align:center;font:900 {round(px * (0.26 if len(words) <= 4 else 0.17))}px/1 {font};color:{col};text-transform:uppercase">{words}</div></div>', anim)
    if iid == "progress-bar":
        v = max(0.0, min(100.0, float(r.get("value") or 100)))
        anim["fill_to"] = round(v / 100 * 588, 1)
        lab = f'<div style="position:absolute;left:0;right:0;bottom:115%;font:800 {round(px * .22)}px/1 {font};color:#fff;text-align:left">{txt}</div>' if txt else ""
        return wrap(f'{lab}<svg viewBox="0 0 600 60" width="100%" height="100%"><rect x="0" y="0" width="600" height="60" rx="30" fill="rgba(255,255,255,.3)"/><rect id="{i}-fill" x="6" y="6" width="0" height="48" rx="24" fill="{gold}"/></svg>',
                    round(px * 3.4), round(px * .34), "position:relative"), anim
    if iid == "countdown":
        n = max(1, min(60, int(r.get("value") or 3)))
        anim["count"] = n
        digits = "".join(f'<div id="{i}-d{j}" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:{1 if j == n else 0}">{j}</div>' for j in range(n, -1, -1))
        return wrap(f'<div style="position:absolute;inset:0;border-radius:50%;background:rgba(0,0,0,.55);border:{max(3, round(6 * k))}px solid #fff"></div><div style="position:absolute;inset:0;font:900 {round(px * .5)}px/1 {font};color:#fff">{digits}</div>', extra="position:relative"), anim
    if iid == "finger-tap":
        return wrap(f'<div id="{i}-ring" style="position:absolute;inset:0;border-radius:50%;border:{max(3, round(6 * k))}px solid #fff;opacity:0"></div><div id="{i}-dot" style="position:absolute;inset:28%;border-radius:50%;background:rgba(255,255,255,.85)"></div>', extra="position:relative"), anim
    if iid == "cursor":
        return wrap('<svg viewBox="0 0 24 24" width="100%" height="100%"><path d="M4 2.5 L4 19 L8.4 14.9 L11.3 21.3 L14.2 20 L11.4 13.8 L17.5 13.6 Z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>', round(px * .6), round(px * .6)), anim
    # sparkle: three four-point stars
    sp = lambda cx, cy, rr, j: f'<polygon id="{i}-s{j}" points="{_star_pts(4, rr, rr * .28, cx, cy, -90)}" fill="#fff" style="transform-box:fill-box;transform-origin:center"/>'  # noqa: E731
    return wrap(f'<svg viewBox="0 0 100 100" width="100%" height="100%" style="overflow:visible">{sp(40, 45, 30, 0)}{sp(78, 20, 16, 1)}{sp(76, 76, 12, 2)}</svg>'), anim


def _icon_tl(ic: dict, i: str, t0: float, dur: float, anim: dict) -> list[str]:
    """The element's entrance (named in its row), and an exit twice as fast."""
    a, out, T = ic.get("anim_in", "pop"), [], round(t0, 3)
    sel = f"#{i}-in"
    if a == "draw":
        out.append(f'tl.fromTo("{sel} path",{{attr:{{"stroke-dashoffset":1}}}},{{attr:{{"stroke-dashoffset":0}},duration:0.35,ease:"power2.inOut",stagger:0.12}},{T});')
        tin = 0.35
    elif a == "wipe":
        out.append(f'tl.fromTo("{sel}",{{scaleX:0}},{{scaleX:1,duration:0.3,ease:"power2.out"}},{T});'); tin = 0.3
    elif a == "fill":
        out.append(f'tl.fromTo("{sel}",{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.2,ease:"power2.out"}},{T});')
        out.append(f'tl.fromTo("#{i}-fill",{{attr:{{width:0}}}},{{attr:{{width:{anim.get("fill_to", 0)}}},duration:0.8,ease:"power2.inOut"}},{round(T + 0.15, 3)});'); tin = 0.2
    elif a == "slap":
        out.append(f'tl.fromTo("{sel}",{{opacity:0,scale:1.7,rotation:-18}},{{opacity:1,scale:1,rotation:-6,duration:0.18,ease:"power4.in"}},{T});')
        out.append(f'tl.fromTo("{sel}",{{x:-6}},{{x:0,duration:0.16,ease:"elastic.out(1,0.3)"}},{round(T + 0.18, 3)});'); tin = 0.3
    elif a == "spin-in":
        out.append(f'tl.fromTo("{sel}",{{opacity:0,scale:.3,rotation:-90}},{{opacity:1,scale:1,rotation:0,duration:0.4,ease:"back.out(1.6)"}},{T});'); tin = 0.4
    elif a == "swing":
        out.append(f'tl.fromTo("{sel}",{{opacity:0,rotation:-28,y:-30}},{{opacity:1,rotation:0,y:0,duration:0.55,ease:"elastic.out(1,0.45)"}},{T});'); tin = 0.4
    elif a == "tap":
        out.append(f'tl.fromTo("{sel}",{{opacity:0,scale:1.3}},{{opacity:1,scale:1,duration:0.18,ease:"power2.out"}},{T});')
        out.append(f'tl.fromTo("#{i}-dot",{{scale:1}},{{scale:.72,duration:0.1,ease:"power2.in",yoyo:true,repeat:1}},{round(T + 0.25, 3)});')
        out.append(f'tl.fromTo("#{i}-ring",{{opacity:1,scale:.4}},{{opacity:0,scale:1.8,duration:0.5,ease:"power2.out"}},{round(T + 0.3, 3)});'); tin = 0.3
    elif a == "glide":
        out.append(f'tl.fromTo("{sel}",{{opacity:0,x:120,y:160}},{{opacity:1,x:0,y:0,duration:0.55,ease:"power3.out"}},{T});')
        out.append(f'tl.fromTo("{sel}",{{scale:1}},{{scale:.85,duration:0.08,ease:"power2.in",yoyo:true,repeat:1}},{round(T + 0.6, 3)});'); tin = 0.55
    elif a == "twinkle":
        for j in range(3):
            out.append(f'tl.fromTo("#{i}-s{j}",{{scale:0,opacity:0}},{{scale:1,opacity:1,duration:0.22,ease:"back.out(2.5)"}},{round(T + j * 0.12, 3)});')
        tin = 0.45
    else:  # pop
        out.append(f'tl.fromTo("{sel}",{{opacity:0,scale:.4}},{{opacity:1,scale:1,duration:0.26,ease:"back.out(1.8)"}},{T});'); tin = 0.26
    if anim.get("sprite"):  # step the strip through its frames, looping for as long as it is up
        sp = anim["sprite"]
        n, loop = sp["frames"], sp["frames"] / sp["fps"]
        reps = max(0, int(dur / loop))
        out.append(f'tl.fromTo("#{i}-sp",{{backgroundPositionX:"0%"}},{{backgroundPositionX:"{round(100 * n / (n - 1), 4)}%",duration:{round(loop, 4)},ease:"steps({n})",repeat:{reps}}},{T});')
    if anim.get("count"):
        n = anim["count"]
        for j in range(n, 0, -1):  # one number a second, then zero
            at = round(T + (n - j + 1) * 1.0, 3)
            if at < t0 + dur - 0.05:
                out.append(f'tl.set("#{i}-d{j}",{{opacity:0}},{at});')
                out.append(f'tl.set("#{i}-d{j - 1}",{{opacity:1}},{at});')
    tout = round(max(0.08, tin / 2), 3)
    out.append(f'tl.to("{sel}",{{opacity:0,scale:.6,duration:{tout},ease:"power2.in"}},{round(max(T + tin, t0 + dur - tout), 3)});')
    return out


# ---------------------------------------------------------------- animated emoji and drawn bursts (2026-09-23)
def _sprite_icon(i: str, px: int, href: str, sp: dict, sticker: bool, k: float) -> str:
    """An animated emoji (Fluent Emoji Animated, MIT) as a one-row sprite strip; the timeline steps it."""
    o = max(3, round(6 * k))
    edge = f"drop-shadow({o}px 0 0 #fff) drop-shadow(-{o}px 0 0 #fff) drop-shadow(0 {o}px 0 #fff) drop-shadow(0 -{o}px 0 #fff) " if sticker else ""
    return (f'<div id="{i}-in" class="icn-in" style="width:{px}px;height:{px}px;filter:{edge}drop-shadow(0 4px 10px rgba(0,0,0,.45))">'
            f'<div id="{i}-sp" style="width:100%;height:100%;background:url({href}) 0% 0% / {sp["frames"] * 100}% 100% no-repeat"></div></div>')


def _confetti_js(i: str, t0: float, dur: float, W: int, H: int, r: dict) -> str:
    """canvas-confetti's physics (ISC, Kiril Vatev — looks/vendor/canvas-confetti/LICENSE), ported to be SEEK-SAFE:
    a seeded random, and every frame re-simulated from the burst's start at 60 ticks a second, so frame N is the
    same frame however the renderer gets there. Options ride on the row: `value` = particle count, `text` unused."""
    k = W / 1080
    seed = sum(ord(ch) * (n + 1) for n, ch in enumerate(i)) & 0xFFFFFFFF
    count = int(r.get("value") or 160)
    return f"""
window.__editDraws = window.__editDraws || [];
(function(){{
  const cv = document.getElementById("{i}-in"), cx = cv.getContext("2d"), T0 = {t0}, DUR = {dur}, K = {k};
  const COLORS = ["#26ccff","#a25afd","#ff5e7e","#88ff5a","#fcff42","#ffa62d","#ff36ff"];
  function rng(a){{ return function(){{ a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }}; }}
  function burst(R, n, x, y, angle, spread, vel){{
    const out = [];
    for (let j = 0; j < n; j++) {{
      const c = COLORS[j % COLORS.length], ra = angle * Math.PI / 180, rs = spread * Math.PI / 180;
      out.push({{ x: x, y: y, wobble: R() * 10, wobbleSpeed: Math.min(0.11, R() * 0.1 + 0.05), velocity: (vel * 0.5) + R() * vel,
        angle2D: -ra + (0.5 * rs - R() * rs), tiltAngle: (R() * 0.5 + 0.25) * Math.PI, color: c, square: j % 2 === 0,
        decay: 0.9, gravity: 3 * K, scalar: 2.2 * K, totalTicks: 200 }});
    }}
    return out;
  }}
  function draw(t){{
    cx.clearRect(0, 0, cv.width, cv.height);
    if (t < T0 || t > T0 + DUR) return;
    const R = rng({seed}), ticks = Math.floor((t - T0) * 60);
    const ps = burst(R, {count // 2}, 0.12 * {W}, 0.72 * {H}, 60, 55, 62 * K).concat(burst(R, {count - count // 2}, 0.88 * {W}, 0.72 * {H}, 120, 55, 62 * K));
    for (const f of ps) {{
      let x1, y1, x2, y2, random = 2, tiltSin = 0, tiltCos = 0, wx = 0, wy = 0;
      for (let tick = 0; tick <= ticks; tick++) {{
        f.x += Math.cos(f.angle2D) * f.velocity; f.y += Math.sin(f.angle2D) * f.velocity + f.gravity; f.velocity *= f.decay;
        f.wobble += f.wobbleSpeed; wx = f.x + 10 * f.scalar * Math.cos(f.wobble); wy = f.y + 10 * f.scalar * Math.sin(f.wobble);
        f.tiltAngle += 0.1; tiltSin = Math.sin(f.tiltAngle); tiltCos = Math.cos(f.tiltAngle); random = R() + 2;
      }}
      const progress = ticks / f.totalTicks;
      if (progress >= 1) continue;
      x1 = f.x + random * tiltCos; y1 = f.y + random * tiltSin; x2 = wx + random * tiltCos; y2 = wy + random * tiltSin;
      cx.fillStyle = f.color; cx.globalAlpha = Math.max(0, 1 - progress);
      cx.beginPath();
      if (f.square) {{ cx.moveTo(Math.floor(f.x), Math.floor(f.y)); cx.lineTo(Math.floor(wx), Math.floor(y1)); cx.lineTo(Math.floor(x2), Math.floor(y2)); cx.lineTo(Math.floor(x1), Math.floor(wy)); }}
      else {{ cx.ellipse(f.x, f.y, Math.abs(x2 - x1) * 0.6, Math.abs(y2 - y1) * 0.6, Math.PI / 10 * f.wobble, 0, 2 * Math.PI); }}
      cx.closePath(); cx.fill();
    }}
    cx.globalAlpha = 1;
  }}
  window.__editDraws.push(draw);
}})();
"""


DRAWN_JS = {"confetti-burst": _confetti_js}
