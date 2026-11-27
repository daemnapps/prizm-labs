#!/usr/bin/env python3
"""thread.py — a phone text thread ad, drawn entirely in code. No video model.

The screen of a phone, inset on black as a screen recording is: one message held down at a time, the
chat blurred and scrolling behind it, the reaction bar above and the menu below. A new screen lands on
the music's beat. Voice notes play with their words on screen. Same doors as stick.py and cartoon.py;
only the voice costs money (voice.py, the house door, run first).

    python3 thread.py build <run>    write the HyperFrames page under <run>/page/
    python3 thread.py render <run>   render it and mix the voice notes and taps into <run>/final.mp4
    python3 thread.py look <run> [step ...]   render, then write one still per step to <run>/look/
    python3 thread.py all <run>      the same as render

<run> is runs/video-edit/<brand>/<label>/ and holds lines.json, vo/ and ad.json. The step grammar is
in README.md. No brand is named here: every word and picture comes from ad.json.
"""
import html
import json
import math
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stick"))
import stick as S  # noqa: E402

W, H, FPS = S.W, S.H, S.FPS
BPM = 117.5
BAR = 4 * 60.0 / BPM        # a new screen every four beats
ME, THEM = "#14513A", "#232526"
SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">%s</svg>'
ICON = {
    "Reply": '<path d="M10 5 3 11l7 6v-4c5 0 9 1 11 6 0-7-4-12-11-12z"/>',
    "Forward": '<path d="m14 5 7 6-7 6v-4c-5 0-9 1-11 6 0-7 4-12 11-12z"/>',
    "Copy": '<rect x="8" y="7" width="12" height="15" rx="2"/><path d="M8 18H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v3M11 12h6M11 16h6"/>',
    "Info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    "Star": '<path d="m12 3 2.8 5.8 6.2.9-4.5 4.4 1 6.3-5.5-3-5.5 3 1-6.3L3 9.7l6.2-.9z"/>',
    "Pin": '<path d="M8 3h8l-1 7 3 4H6l3-4zM12 14v8"/>',
    "Report": '<path d="M12 4 2.5 20h19zM12 10v5M12 17.500v.5"/>',
    "Delete": '<path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v8M14 10v8"/>',
}
MENUS = {
    "text": ["Reply", "Forward", "Copy", "Info", "Star", "Pin", "Delete"],
    "image": ["Reply", "Forward", "Copy", "Info", "Star", "Pin", "Delete"],
    "them": ["Reply", "Forward", "Copy", "Star", "Pin", "Report", "Delete"],
    "voice": ["Reply", "Forward", "Star", "Pin", "Report", "Delete"],
    "missed": ["Reply", "Star", "Pin", "Report", "Delete"],
}
EMOJI = ["👍", "❤️", "😂", "😮", "😢", "🙏"]
GROUP_Y = {"image": 140, "text": 950, "voice": 950, "missed": 620}  # where the reaction bar sits on the 2339-high phone


def esc(s):
    return html.escape(str(s))


# ---------------------------------------------------------------- one chat, scrolling behind everything
def chat_column(rnd, steps):
    """The chat itself, top to bottom, every block from a real step, plus older chat above it. Each screen
    blurs the same column at a later scroll, so old pictures stay in the blur as they do in the swipe."""
    y, blocks, at = 0, [], {}
    for _ in range(14):
        me = rnd.random() < .5
        h, w = rnd.choice([90, 130, 170]), rnd.randint(330, 720)
        blocks.append((w, h, 60 if not me else 1020 - w, y, ME if me else "#3A3C3E"))
        y += h + rnd.randint(60, 130)
    for st in steps:
        at[st["n"]] = y
        k = st["kind"]
        if k == "image":
            blocks.append((560, 780, 460, y, "#E8DFC8"))
            blocks.append((230, 380, 500, y + 330, "#7D9CC4"))
            y += 820
        elif k in ("text", "voice", "missed"):
            me = st.get("from") == "me"
            w = 700 if k == "voice" else max(280, min(820, 260 + 16 * len(st.get("text", "x" * 12))))
            blocks.append((w, 150, 1020 - w if me else 60, y, ME if me else "#3A3C3E"))
            y += 210
    return blocks, at


def blur_layer(blocks, top):
    vis = [b for b in blocks if -200 < b[3] - top < 2500]
    return '<div class="blur">%s</div>' % "".join(
        '<i style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;background:%s"></i>' % (x, yy - top, w, h, c) for w, h, x, yy, c in vis)


WAVE_BARS = 34
WAVE_STEP = 12              # a bar and its gap, so the dot's run ends on the last bar


def bars(lv, n=WAVE_BARS):
    """The note's own waveform: each bar is the loudest moment in its slice of the sound, first word to last."""
    out = []
    for i in range(n):
        part = lv[i * len(lv) // n:(i + 1) * len(lv) // n] or [0]
        out.append('<u style="height:%dpx"></u>' % (8 + 62 * max(part)))
    return "".join(out)


def bubble(step, uid, lv, secs):
    k = step["kind"]
    side = "me" if step.get("from") == "me" else "them"
    t = esc(step.get("time", ""))
    tick = '<span class="ticks">✓✓</span>' if side == "me" else ""
    if k == "text":
        return '<div class="bb %s"><span class="tx">%s</span><span class="tm">%s %s</span></div>' % (side, esc(step["text"]), t, tick)
    if k == "image":
        inner = '<img class="full" src="assets/%s" alt="">' % esc(step["src"])
        return '<div class="bb img %s"><div class="pagewrap">%s</div><span class="tm over">%s %s</span></div>' % (side, inner, t, tick)
    if k == "missed":
        return ('<div class="bb %s missed"><span class="ring">%s</span><span class="mt"><b>Missed voice call</b><br>Tap to call back</span><span class="tm">%s</span></div>'
                % (side, SVG % '<path d="M4 8c5-5 11-5 16 0l-3 3-3-2v-2c-2-.6-3-.6-4 0v2l-3 2zM8 15l4 4 4-4"/>', t))
    if k == "voice":
        return ('<div class="bb %s voice"><span class="pause"><i></i><i></i></span><div class="col"><div class="wave">%s<em id="%sdot"></em></div>'
                '<span class="cnt">0:%02d</span></div><div class="col r"><span class="speed">1x</span><span class="tm">%s</span></div></div>'
                % (side, bars(lv), uid, min(59, max(1, int(secs))), t))
    raise SystemExit("no step kind %r" % k)


def menu(step):
    kind = step["kind"]
    if kind == "text" and step.get("from") != "me":
        kind = "them"
    return '<div class="menu">%s</div>' % "".join(
        '<div class="%s"><span>%s</span>%s</div>' % ("del" if m == "Delete" else "", m, SVG % ICON[m]) for m in MENUS[kind])


def react():
    return '<div class="react">%s<span class="cut">🥰</span><span class="plus">+</span></div>' % "".join("<span>%s</span>" % e for e in EMOJI)


def statusbar(clock):
    return ('<div class="stat"><b>%s</b><span class="sig"><i></i><i></i><i></i><i></i></span><span class="wifi">%s</span><span class="bat"><i></i></span></div>'
            % (esc(clock), SVG % '<path d="M2 9c6-5 14-5 20 0M6 13c4-3 8-3 12 0M10 17c1-1 3-1 4 0"/>'))


def pov_boxes(lines):
    return '<div class="pov">%s</div>' % "".join("<span>%s</span>" % esc(x) for x in lines)


def editor(step, uid):
    tools = "".join('<div class="%s">%s<b>%s</b></div>' % (c, SVG % g, n) for c, g, n in [
        ("", '<path d="M12 3v18M7 4h3M14 4h3M7 20h3M14 20h3"/>', "Split"), ("dim", '<path d="M4 9h4l5-4v14l-5-4H4z"/>', "Volume"),
        ("", '<rect x="4" y="4" width="11" height="11"/><rect x="9" y="9" width="11" height="11"/>', "Splice"),
        ("", '<rect x="3" y="5" width="18" height="14"/><path d="m10 9 5 3-5 3z"/>', "Animations"),
        ("", '<path d="M4 6h16M6 6l1 15h10l1-15"/>', "Delete")])
    handles = ('<div class="hand" id="%shand"><i class="h1">✕</i><i class="h2">⧉</i><i class="h3">⤢</i></div>' % uid)
    return ('<div class="edit"><div class="etop"><span>✕</span><span class="pill trial"><em id="%strial">Try free trial   Try free trial</em></span>'
            '<span class="pill">AI ultra HD ▾</span><span class="chip">Export</span></div><div class="small"><img class="full" src="assets/%s" alt="">%s</div>'
            '<div class="ctrl"><span>⛶</span><span>▷</span><span>↶ ↷</span></div><div class="clock"><span>00:00 / 00:06</span><span>00:00</span><span>·</span><span>00:02</span></div>'
            '<div class="line"></div><div class="strip"><img src="assets/%s" alt=""><img src="assets/%s" alt=""><img src="assets/%s" alt=""></div>'
            '<div class="tools"><div class="back">«</div>%s</div></div>'
            % (uid, esc(step["src"]), handles, esc(step["photo"]), esc(step["photo"]), esc(step["photo"]), tools))


def screen(step, uid, lv, secs, blocks, tops, end_top):
    k = step["kind"]
    if k == "photo":
        return '<img class="wide" src="assets/%s" alt="">%s' % (esc(step["src"]), pov_boxes(step["pov"]))
    if k == "paper":
        return '<img class="plain" src="assets/%s" alt="">%s' % (esc(step["src"]), pov_boxes(step["pov"]))
    if k == "editor":
        return '<div class="phone">%s</div>%s' % (editor(step, uid) + statusbar(step["clock"]), pov_boxes(step["pov"]))
    side = "me" if step.get("from") == "me" else "them"
    y = step.get("y", GROUP_Y[k])
    caps = "".join('<div class="say" id="%ssay%d" style="top:%dpx">%s</div>' % (uid, i, y - 245, esc(c["text"])) for i, c in enumerate(step.get("say", [])))
    top = tops[step["n"]] - 900
    return ('<div class="phone">%s%s<div class="stack %s" id="%sgrp" style="top:%dpx">%s%s%s</div>%s<div class="home"></div></div>'
            % (blur_layer(blocks, top), caps, side, uid, y, react(), bubble(step, uid, lv, secs), menu(step), statusbar(step["clock"])))


# ---------------------------------------------------------------- the clock
def voice_secs(run, sid):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(run / "vo" / (sid + ".mp3"))],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def on_grid(d):
    """Every screen lasts a whole number of half bars, so every change lands on the beat."""
    return max(1, math.ceil((d - .12) / (BAR / 2))) * BAR / 2


def hold_of(step, run):
    k = step["kind"]
    if k in ("photo", "editor", "paper"):
        return step["hold"]
    told = voice_secs(run, step["narrate"]) + .15 if step.get("narrate") else 0
    if k == "voice":
        return on_grid(voice_secs(run, step["sid"]) + .2)
    return on_grid(max(told, step.get("hold", BAR)))


def clock(run, ad):
    t, out = 0.0, []
    for n, st in enumerate(ad["steps"]):
        d = hold_of(st, run)
        out.append(dict(st, n=n, t=round(t, 3), d=round(d, 3)))
        t += d
    return out, round(t, 2)


CSS = """
*{margin:0;padding:0;box-sizing:border-box}html,body{width:1080px;height:1920px;background:#000;overflow:hidden}
#root{position:relative;width:1080px;height:1920px;background:#000;overflow:hidden;color:#fff;
 font-family:-apple-system,'SF Pro Text','Helvetica Neue',Inter,sans-serif}
.scr{position:absolute;inset:0;overflow:hidden;background:#000}
.phone{position:absolute;left:116px;top:42px;width:1080px;height:2339px;transform:scale(.785);transform-origin:0 0;background:#111313;overflow:hidden;border-radius:30px}
.blur{position:absolute;inset:-70px;filter:blur(34px)}.blur i{position:absolute;display:block;border-radius:30px}
.stat{position:absolute;left:0;right:0;top:0;height:130px;display:flex;align-items:center;gap:14px;padding:30px 70px 0 112px;font-size:50px;z-index:9}
.stat b{flex:1;font-weight:700;letter-spacing:-.5px}.sig{display:flex;align-items:flex-end;gap:4px;height:30px}.sig i{width:7px;background:#fff;border-radius:2px}.sig i:nth-child(1){height:10px}.sig i:nth-child(2){height:16px}.sig i:nth-child(3){height:23px}.sig i:nth-child(4){height:30px;background:#777}
.wifi{width:50px;height:50px}.wifi svg{width:100%;stroke-width:3}.bat{width:70px;height:32px;border:2px solid #999;border-radius:9px;padding:3px}.bat i{display:block;width:45%;height:100%;background:#F4CE3D;border-radius:4px}
.home{position:absolute;left:345px;right:345px;bottom:22px;height:13px;border-radius:7px;background:#fff;z-index:9}
.stack{position:absolute;left:44px;right:44px;display:flex;flex-direction:column;gap:30px;z-index:3}.stack.me{align-items:flex-end}.stack.them{align-items:flex-start}
.say{position:absolute;left:30px;right:30px;text-align:center;font-size:68px;line-height:1.16;font-weight:500;letter-spacing:-.5px;z-index:4;text-shadow:0 0 3px #000,0 1px 3px #000}
.react{position:relative;display:flex;align-items:center;gap:34px;background:#262829F2;border-radius:90px;padding:0 44px 0 44px;font-size:78px;height:158px;width:912px;overflow:hidden}
.react .cut{margin-left:-6px;width:40px;overflow:hidden;display:block}.plus{position:absolute;right:44px;width:78px;height:78px;border-radius:50%;background:#54575A;font-size:62px;font-weight:300;display:flex;align-items:center;justify-content:center;color:#E8E8E8;line-height:1}
.bb{position:relative;max-width:900px;border-radius:30px;padding:22px 30px 16px;font-size:55px;line-height:1.16;display:flex;flex-direction:column}
.bb.me{background:#14513A}.bb.them{background:#232526}
.tm{font-size:38px;color:#B9C6BF;align-self:flex-end}.ticks{color:#6FD3F2;letter-spacing:-11px;margin-right:10px}
.bb.img{padding:9px;background:#14513A}.pagewrap{width:672px;height:940px;overflow:hidden;border-radius:22px;background:#fff;position:relative}
.pagewrap .np{transform:scale(.884);transform-origin:0 0}.pagewrap img.full{width:100%;height:100%;object-fit:cover;object-position:50% 0;display:block}
.tm.over{position:absolute;right:24px;bottom:18px;color:#fff;text-shadow:0 0 6px #000}
.missed{flex-direction:row;gap:26px;align-items:center;padding:22px 26px;width:742px}.mt{font-size:46px;color:#BDBDBD;line-height:1.2;flex:1}.mt b{color:#fff;font-size:46px}.ring{width:84px;height:84px;border-radius:50%;background:#0006;color:#FF5C7A;padding:18px}.missed .tm{align-self:flex-end}
.voice{flex-direction:row;gap:30px;align-items:flex-start;width:756px;padding:36px 34px 22px}.pause{display:flex;gap:9px;padding-top:24px}.pause i{width:10px;height:38px;background:#9AA;display:block}
.col{display:flex;flex-direction:column;gap:6px}.col.r{align-items:center;gap:12px}.wave{position:relative;display:flex;align-items:center;gap:5px;height:80px;width:408px}.wave u{display:block;width:7px;border-radius:4px;background:#C8D0D4}
.wave em{position:absolute;left:0;top:29px;width:26px;height:26px;border-radius:50%;background:#4FB6EC}.speed{background:#000;border-radius:26px;padding:6px 22px;font-size:36px;font-weight:600}.cnt{font-size:38px;color:#B9C6BF}
.menu{width:688px;background:#2A2C2DF2;border-radius:30px;overflow:hidden}.menu div{display:flex;justify-content:space-between;align-items:center;height:131px;padding:0 42px;font-size:55px;border-top:1px solid #FFFFFF14}.menu div:first-child{border:0}.menu svg{width:58px;height:58px}
.menu .del{color:#F0587A}
.wide{position:absolute;left:22px;top:272px;width:1036px;height:1376px;object-fit:cover;object-position:50% 20%}
.plain{position:absolute;left:0;top:205px;width:1080px;height:1510px}.small img.full{width:100%;height:100%;object-fit:cover;object-position:50% 0;display:block}
.pov{position:absolute;left:0;right:0;top:1250px;display:flex;flex-direction:column;align-items:center;z-index:6;font-size:53px;font-weight:500;color:#000;line-height:1.14;letter-spacing:-.4px}
.pov span{background:#fff;border-radius:16px;padding:0 28px;display:block;height:61px}
.edit{position:absolute;inset:0;background:#131415}.etop{position:absolute;left:44px;right:30px;top:150px;display:flex;gap:26px;font-size:46px;align-items:center;white-space:nowrap}
.pill{background:#2A2C2E;border-radius:14px;padding:12px 22px;font-size:40px;font-weight:600}.trial{width:230px;overflow:hidden;display:block}.trial em{display:inline-block;font-style:normal}.chip{background:#25D3E0;color:#012;border-radius:14px;padding:12px 26px;font-size:40px;font-weight:700;margin-left:auto}
.small{position:absolute;left:208px;top:262px;width:672px;height:952px;overflow:hidden;background:#fff}.small .np{transform:scale(.884);transform-origin:0 0}
.hand{position:absolute;left:96px;top:470px;width:320px;height:380px;border:2px solid #fff;opacity:0}.hand i{position:absolute;width:60px;height:60px;border-radius:50%;background:#111;color:#fff;font-style:normal;font-size:30px;display:flex;align-items:center;justify-content:center}.h1{left:-30px;top:-30px}.h2{left:-30px;bottom:-30px}.h3{right:-30px;bottom:-30px}
.ctrl{position:absolute;left:60px;right:60px;top:1250px;display:flex;justify-content:space-between;font-size:48px}.clock{position:absolute;left:44px;right:30px;top:1345px;display:flex;justify-content:space-between;font-size:30px;color:#999}
.line{position:absolute;left:539px;top:1410px;width:4px;height:600px;background:#fff;z-index:2}.strip{position:absolute;left:540px;top:1740px;display:flex;height:120px}.strip img{width:120px;height:120px;object-fit:cover}
.tools{position:absolute;left:30px;right:0;bottom:90px;display:flex;gap:58px;align-items:flex-end}.tools div{display:flex;flex-direction:column;align-items:center;gap:8px;width:110px}.tools svg{width:60px;height:60px}.tools b{font-size:26px;font-weight:500}.tools .dim{opacity:.35}.back{background:#2A2C2E;border-radius:12px;height:130px;justify-content:center;font-size:60px;width:80px!important}
.sm{position:absolute;left:0;right:0;bottom:66px;text-align:center;font-size:24px;color:#C9C9C9;z-index:12;text-shadow:0 1px 6px #000}
"""


def build(run):
    ad = S.read(run / "ad.json")
    steps, dur = clock(run, ad)
    rnd = random.Random(ad.get("seed", 7))
    blocks, tops = chat_column(rnd, steps)
    page = run / "page"
    (page / "assets").mkdir(parents=True, exist_ok=True)
    body, js = [], []
    for st in steps:
        n, t, d = st["n"], st["t"], st["d"]
        uid = "s%d" % n
        lv, secs = [], 0
        if st["kind"] == "voice":
            lv = S.audio_levels(run / "vo" / (st["sid"] + ".mp3"), .05)
            secs = voice_secs(run, st["sid"])
        body.append('<div id="%s" class="clip scr" data-start="%.3f" data-duration="%.3f" data-track-index="%d">%s</div>'
                    % (uid, t, d, 2 + n % 2, screen(st, uid, lv, secs, blocks, tops, 0)))
        if st["kind"] in ("text", "image", "voice", "missed"):
            js.append('tl.fromTo("#%sgrp",{scale:.97,y:14},{scale:1,y:0,duration:.14,ease:"power2.out"},%.3f);' % (uid, t))
        if st["kind"] == "editor":
            js.append('tl.to("#%strial",{x:-300,duration:%.2f,ease:"none"},%.3f);' % (uid, d, t))
            for a, b in st.get("handles", []):
                js.append('tl.set("#%shand",{opacity:1},%.3f);tl.set("#%shand",{opacity:0},%.3f);' % (uid, t + a, uid, t + b))
        if st["kind"] == "voice":
            js.append('tl.to("#%sdot",{left:%d,duration:%.3f,ease:"none"},%.3f);' % (uid, WAVE_BARS * WAVE_STEP - 19, secs, t))
        says = st.get("say", [])
        for i, c in enumerate(says):
            end = says[i + 1]["at"] if i + 1 < len(says) else c.get("to", d)
            js.append('tl.set("#%ssay%d",{opacity:0},0);tl.set("#%ssay%d",{opacity:1},%.3f);tl.set("#%ssay%d",{opacity:0},%.3f);'
                      % (uid, i, uid, i, t + c["at"], uid, i, t + end))
    for sm in ad.get("small_print", []):
        st = next(x for x in steps if x["n"] == sm["step"])
        body.append('<div id="sp%d" class="clip sm" data-start="%.3f" data-duration="%.3f" data-track-index="20">%s</div>'
                    % (st["n"], st["t"], dur - st["t"], esc(sm["text"])))
    doc = """<!doctype html>
<html><head><meta charset="utf-8"><script src="%s"></script><style>%s</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="%.2f" data-width="%d" data-height="%d">
%s
</div>
<script>window.__timelines=window.__timelines||{};const tl=gsap.timeline({paused:true});
%s
tl.set({}, {}, %.2f);
window.__timelines["main"]=tl;</script></body></html>
""" % (S.GSAP, CSS, dur, W, H, "\n".join(body), "\n".join(js), dur)
    (page / "index.html").write_text(doc)
    (page / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}))
    (run / "beats.json").write_text(json.dumps(steps, indent=1))
    print("page written: %d steps, %.1f s" % (len(steps), dur))
    return steps, dur


def mix(run, ad, steps, dur):
    """The whole sound: voice notes through the swipe's muffled phone sound, matched band by band, and teller on top, the swipe's own music and effects under them from the first
    message on, held down under every voice by the amount the swipe's own mix does. `sound.loop` is the stretch of
    the split music that repeats if the ad runs longer than the swipe."""
    snd = ad["sound"]
    first = next(s for s in steps if s["kind"] == "image")["t"]
    voiced = [(s["sid"], s["t"], True) for s in steps if s["kind"] == "voice"]
    voiced += [(s["narrate"], s["t"], False) for s in steps if s.get("narrate")]
    spans = sorted((t, t + voice_secs(run, sid)) for sid, t, _ in voiced)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    fx, tags = [], []
    n = 0
    for sid, t, phone in voiced:
        cmd += ["-i", str(run / "vo" / (sid + ".mp3"))]
        eq = "highpass=f=90,equalizer=f=1900:t=o:w=1.4:g=7,equalizer=f=4300:t=o:w=1:g=6,lowpass=f=6200,lowpass=f=6200,lowpass=f=9000,acompressor=threshold=-22dB:ratio=3," if phone else ""
        fx.append("[%d]aresample=44100,aformat=channel_layouts=stereo,%sadelay=%d:all=1[n%d]" % (n, eq, int(t * 1000), n))
        tags.append("[n%d]" % n)
        n += 1
    duck = "+".join("between(t,%.2f,%.2f)" % (a - .05, b + .1) for a, b in spans)
    a, b = snd["loop"]
    cmd += ["-i", str(run / "sound" / snd["music"]), "-i", str(run / "sound" / snd["music"])]
    fx.append("[%d]atrim=%.3f:%.3f,asetpts=N/SR/TB[m0];[%d]atrim=%.3f:%.3f,asetpts=N/SR/TB,aloop=loop=-1:size=2147483647[m1];[m0][m1]concat=v=0:a=1,aresample=44100,aformat=channel_layouts=stereo,"
              "atrim=0:%.2f,afade=t=out:st=%.2f:d=1.5,volume=%.3f,volume='if(%s,%.4f,1)':eval=frame,adelay=%d:all=1[m]"
              % (n, snd["start"], b, n + 1, a, b, dur - first, dur - first - 1.5, snd.get("music_gain", 1.0), duck, 10 ** (snd.get("music_duck_db", -6) / 20), int(first * 1000)))
    tags.append("[m]")
    fx.append("%samix=inputs=%d:duration=longest:normalize=0,loudnorm=I=-14:TP=-1:LRA=11[o]" % ("".join(tags), len(tags)))
    out = run / "vo" / "mix.wav"
    subprocess.run(cmd + ["-filter_complex", ";".join(fx), "-map", "[o]", "-ar", "48000", "-t", "%.2f" % dur, str(out)], check=True)
    return out


def render(run):
    steps, dur = build(run)
    silent = run / "silent.mp4"
    subprocess.run(["npx", "hyperframes", "render", "--fps", str(FPS), "--output", str(silent.resolve())], cwd=str(run / "page"), check=True)
    track = mix(run, S.read(run / "ad.json"), steps, dur)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(track), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-t", "%.2f" % dur, str(run / "final.mp4")], check=True)
    print("final:", run / "final.mp4")
    return steps


def look(run, only):
    steps = render(run)
    out = run / "look"
    out.mkdir(exist_ok=True)
    for s in steps:
        if only and str(s["n"]) not in only:
            continue
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % (s["t"] + min(.5, s["d"] / 2)), "-i", str(run / "final.mp4"),
                        "-frames:v", "1", "-vf", "scale=360:-1", str(out / ("s%02d.jpg" % s["n"]))], check=True)
    print("stills:", out)


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("build", "render", "all", "look"):
        raise SystemExit(__doc__)
    run = Path(sys.argv[2]).resolve()
    cmd = sys.argv[1]
    if cmd == "build":
        build(run)
    elif cmd == "look":
        look(run, sys.argv[3:])
    else:
        render(run)


if __name__ == "__main__":
    main()
