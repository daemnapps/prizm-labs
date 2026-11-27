#!/usr/bin/env python3
"""stick.py — a stick-figure explainer ad, drawn entirely in code. No video model.

The voice track, the real pictures and the beat list go in; a finished 9:16 video
comes out. Only the voice costs money (voice.py, the house door, run first).

    python3 stick.py pictures <run>   fetch every picture in ad.json from the Drive by key
    python3 stick.py tighten <run>    bring every long pause in the voice down to 0.2 s
    python3 stick.py build <run>      write the HyperFrames page under <run>/page/
    python3 stick.py render <run>     render it and mix voice, music and pops into <run>/final.mp4
    python3 stick.py all <run>        the three above, in order

<run> is runs/video-edit/<brand>/<label>/ and holds lines.json, vo/ and ad.json. The
beat grammar is in README.md. No brand is named here: colours and words come from ad.json.
"""
import array
import html
import json
import math
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "gdrive-creator"))

W, H = 1080, 1920
FPS = 30
GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"

# (upper-left, fore-left, upper-right, fore-right) in degrees
POSES = {
    "idle": (-60, -20, 60, 20),
    "point-left": (42, 8, 62, -72),
    "point-right": (-62, 72, -42, -8),
    "point-both": (42, 8, -42, -8),
    "shrug": (-22, 72, 22, -72),
    "no": (-60, 20, -12, -82),
    "rub": (-45, -10, 48, 104),
    "scratch": (-30, 112, 60, 20),
    "scrub": (-42, -66, 34, 118),
    "cheer": (56, 20, -56, -20),
    "facepalm": (-40, 126, 60, 20),
}
# which forearm shakes during a pose, and how far
SHAKE = {"no": ("fR", 20), "rub": ("fR", 16), "scratch": ("fL", 14), "scrub": ("fR", 24), "cheer": ("fR", 10)}


def read(p):
    return json.loads(Path(p).read_text())


def words_of(run):
    """Every spoken word with its time. The voice sheet times each sentence; words share
    their sentence's time by length."""
    timing = read(run / "vo" / "timing.json")
    out = []
    for sid, sc in timing["scenes"].items():
        for ln in sc["lines"]:
            ws = ln["text"].split()
            total = sum(len(w) + 1 for w in ws)
            t = ln["start"]
            span = ln["end"] - ln["start"]
            for w in ws:
                d = span * (len(w) + 1) / total
                out.append({"w": w, "t": round(t, 3), "e": round(t + d, 3), "sid": sid})
                t += d
    return out


def norm(s):
    return re.sub(r"[^a-z0-9$]", "", s.lower())


def phrase_at(words, phrase, start):
    want = [norm(x) for x in phrase.split()]
    for i in range(start, len(words) - len(want) + 1):
        if all(norm(words[i + j]["w"]) == want[j] for j in range(len(want))):
            return i
    raise SystemExit("beat phrase not in the voice track, or out of order: %r" % phrase)


def audio_levels(track, step=0.1):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(track), "-ac", "1", "-ar", "8000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    a = array.array("h", raw)
    n = int(8000 * step)
    lv = []
    for i in range(0, len(a), n):
        c = a[i:i + n]
        lv.append(math.sqrt(sum(x * x for x in c) / max(1, len(c))) / 32768)
    top = max(lv) or 1
    return [min(1.0, x / top * 1.6) for x in lv]


# ---------------------------------------------------------------- doodles
INK = 'stroke="#111" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round"'


def doodle(name, ac, uid, text=""):
    v = 'viewBox="0 0 480 560" class="dd"'
    if name == "lotion":
        return ('<svg %s><path d="M170 190 h140 l25 60 v230 a24 24 0 0 1 -24 24 h-142 a24 24 0 0 1 -24 -24 v-230z" %s/>'
                '<rect x="205" y="120" width="70" height="70" %s/><path d="M240 120 v-44 h-70" %s/>'
                '<text x="240" y="370" text-anchor="middle" font-family="Archivo Black" font-size="36" fill="#111">%s</text></svg>'
                % (v, INK, INK, INK, html.escape(text or "LOTION")))
    if name == "dry":
        cracks = "".join('<path d="M%d %d l30 -24 l26 30 l34 -18" %s/>' % (70 + (i % 3) * 110, 160 + (i // 3) * 95, INK)
                         for i in range(9))
        flakes = "".join('<path id="%sf%d" d="M%d 500 l22 -12 l10 16z" fill="%s"/>' % (uid, i, 80 + i * 62, ac) for i in range(6))
        return ('<svg %s><rect x="30" y="100" width="420" height="340" rx="30" %s/>%s%s</svg>' % (v, INK, cracks, flakes))
    if name == "question":
        return ('<svg %s><text x="240" y="400" text-anchor="middle" font-family="Archivo Black" font-size="340" fill="%s">?</text></svg>' % (v, ac))
    if name == "phone":
        return ('<svg %s><rect x="130" y="50" width="220" height="460" rx="36" %s/><path d="M180 170 h120 M180 240 h120 M180 310 h70" %s/>'
                '<circle cx="240" cy="450" r="14" fill="#111"/></svg>' % (v, INK, INK))
    if name == "jar":
        return ('<svg %s><rect x="110" y="170" width="260" height="60" rx="14" %s/><path d="M125 230 v210 a26 26 0 0 0 26 26 h178 a26 26 0 0 0 26 -26 v-210" %s/>'
                '<text x="240" y="380" text-anchor="middle" font-family="Archivo Black" font-size="110" fill="%s">$$$</text></svg>' % (v, INK, INK, ac))
    if name == "x":
        return ('<svg %s><path d="M100 130 L380 430 M380 130 L100 430" stroke="#D23B2E" stroke-width="44" stroke-linecap="round"/></svg>' % v)
    if name == "earth":
        return ('<svg %s><circle cx="240" cy="280" r="190" %s/><path d="M120 190 q60 40 110 10 t80 60 t-70 90 t-90 -40z M330 150 q40 30 50 80" %s/></svg>' % (v, INK, INK))
    if name == "shelf":
        b = "".join('<path d="M%d %d h42 l8 18 v76 h-58 v-76z M%d %d v-22" %s/>' % (44 + c * 104, 96 + r * 170, 65 + c * 104, 96 + r * 170, INK)
                    for r in range(2) for c in range(4))
        return ('<svg %s>%s<path d="M20 196 h440 M20 366 h440" %s/></svg>' % (v, b, INK))
    if name == "clock":
        return ('<svg %s><circle cx="240" cy="280" r="190" %s/><path id="%sh" d="M240 280 V130" %s/><path d="M240 280 V170" %s/>'
                '<text x="240" y="520" text-anchor="middle" font-family="Archivo Black" font-size="50" fill="%s">LUNCH</text></svg>' % (v, INK, uid, INK, INK, ac))
    if name == "badge":
        return ('<svg %s><circle cx="240" cy="270" r="200" stroke="%s" stroke-width="16" fill="none"/>'
                '<text x="240" y="280" text-anchor="middle" font-family="Archivo Black" font-size="140" fill="#111">60</text>'
                '<text x="240" y="350" text-anchor="middle" font-family="Archivo Black" font-size="42" fill="#111">DAY MONEY</text>'
                '<text x="240" y="400" text-anchor="middle" font-family="Archivo Black" font-size="42" fill="#111">BACK</text></svg>' % (v, ac))
    if name == "blob":
        return ('<svg %s><rect x="30" y="420" width="420" height="90" rx="10" fill="#F4C9A8" stroke="#111" stroke-width="8"/>'
                '<ellipse id="%sm" cx="240" cy="450" rx="46" ry="16" fill="#7A4A25"/>'
                '<g id="%sb"><path d="M178 250 q-30 -70 50 -84 q80 -18 92 50 q14 66 -66 72 q-60 6 -76 -38z" fill="#7A4A25" stroke="#111" stroke-width="8"/>'
                '<circle cx="222" cy="214" r="9" fill="#fff"/><circle cx="268" cy="210" r="9" fill="#fff"/><path d="M222 256 h46" stroke="#111" stroke-width="8"/>'
                '<path d="M190 300 l30 60 M292 296 l-40 64" stroke="#111" stroke-width="8"/><rect x="214" y="350" width="50" height="40" fill="#C9A06A" stroke="#111" stroke-width="7"/><rect x="186" y="388" width="106" height="24" fill="#111"/></g></svg>' % (v, uid, uid))
    if name == "price":
        return ('<svg %s><text x="240" y="330" text-anchor="middle" font-family="Archivo Black" font-size="130" fill="%s">%s</text></svg>' % (v, ac, html.escape(text)))
    raise SystemExit("no doodle called %r" % name)


def skin_diagram(uid, ac):
    """The whole-width picture of why lotion fails: drops on the old layer, salt clears it,
    drops reach the new skin. Its parts move on the beat's clock (see skin_moves)."""
    drops = "".join('<path id="%sd%d" d="M%d 40 q-26 40 0 60 q26 -20 0 -60z" fill="%s"/>' % (uid, i, 200 + i * 170, ac) for i in range(5))
    salt = "".join('<rect id="%ss%d" x="%d" y="270" width="30" height="30" transform="rotate(20 %d 285)" fill="#fff" stroke="#111" stroke-width="6"/>'
                   % (uid, i, -60 - i * 70, -45 - i * 70) for i in range(6))
    return ('<svg viewBox="0 0 1000 560" class="dd wide">%s'
            '<rect id="%sold" x="20" y="250" width="960" height="90" fill="#D9CDBF" stroke="#111" stroke-width="8"/>'
            '<text id="%soldt" x="500" y="310" text-anchor="middle" font-family="Archivo Black" font-size="48" fill="#111">OLD DRY SKIN</text>'
            '<rect x="20" y="340" width="960" height="170" fill="#F4C9A8" stroke="#111" stroke-width="8"/>'
            '<text x="500" y="440" text-anchor="middle" font-family="Archivo Black" font-size="48" fill="#111">YOUR SKIN</text>%s</svg>'
            % (drops, uid, uid, salt))


def skin_moves(uid, t, d, stage):
    js = []
    for i in range(5):
        at = t + 0.1 + i * 0.13
        if stage == "sit":
            js.append('tl.to("#%sd%d",{y:150,duration:.3,ease:"bounce.out"},%.3f);' % (uid, i, at))
        else:
            js.append('tl.set("#%sd%d",{opacity:0},%.3f);' % (uid, i, t))
    if stage == "scrub":
        for i in range(6):
            js.append('tl.to("#%ss%d",{x:1500,duration:%.2f,ease:"none"},%.3f);' % (uid, i, d * 0.8, t + i * 0.12))
        js.append('tl.to("#%sold,#%soldt",{x:1100,duration:%.2f,ease:"power2.in"},%.3f);' % (uid, uid, d * 0.4, t + d * 0.5))
    if stage == "through":
        js.append('tl.set("#%sold,#%soldt",{opacity:0},%.3f);' % (uid, uid, t))
        for i in range(5):
            js.append('tl.set("#%sd%d",{opacity:1},%.3f);tl.to("#%sd%d",{y:290,duration:.45,ease:"power1.in"},%.3f);'
                      % (uid, i, t + i * 0.1, uid, i, t + i * 0.1))
    return js


# ---------------------------------------------------------------- the figure
def figure(ac):
    arm = ('<line x1="540" y1="400" x2="%d" y2="400"/><g id="%s"><line x1="%d" y1="400" x2="%d" y2="400"/>'
           '<circle cx="%d" cy="400" r="16" fill="#fff"/><line x1="%d" y1="400" x2="%d" y2="400" stroke-width="10"/></g>')
    return ('<svg id="fig" viewBox="0 0 1080 1000" width="1080" height="1000" style="position:absolute;left:0;top:900px">'
            '<g id="bob" stroke="#111" stroke-width="12" fill="none" stroke-linecap="round" stroke-linejoin="round">'
            '<line x1="540" y1="350" x2="540" y2="650"/>'
            '<g id="uL">' + arm % (370, "fL", 370, 215, 215, 200, 160) + '</g>'
            '<g id="uR">' + arm % (710, "fR", 710, 865, 865, 880, 920) + '</g>'
            '<path d="M540 650 L440 900 M540 650 L640 900"/>'
            '<ellipse cx="415" cy="908" rx="40" ry="16" fill="#fff"/><ellipse cx="665" cy="908" rx="40" ry="16" fill="#fff"/>'
            '<g id="head">'
            '<path d="M420 240 q-14 -130 120 -135 q134 5 120 135 q10 60 -20 90 l-20 -40 h-160 l-20 40 q-30 -30 -20 -90z" fill="#111"/>'
            '<circle cx="540" cy="245" r="105" fill="#fff"/>'
            '<path d="M440 215 q60 -10 100 -70 q40 60 100 70" fill="#111" stroke="none"/>'
            '<circle id="eL" cx="500" cy="245" r="10" fill="#111"/><circle id="eR" cx="580" cy="245" r="10" fill="#111"/>'
            '<ellipse id="mouth" cx="540" cy="295" rx="26" ry="20" fill="#111" stroke="none"/>'
            '</g>'
            '<circle cx="540" cy="372" r="14" fill="%s" stroke="none"/>'
            '</g></svg>' % ac)


def figure_moves(beats, levels, dur, calm=False):
    js = []
    tween = 'duration:.5,ease:"sine.inOut"' if calm else 'duration:.2,ease:"back.out(2.2)"'
    last = "idle"
    for b in beats:
        p = POSES[b.get("pose") or last]
        last = b.get("pose") or last
        t, d = b["t"], b["e"] - b["t"]
        for sel, a in zip(("#uL", "#fL", "#uR", "#fR"), p):
            org = {"#uL": "540 400", "#fL": "370 400", "#uR": "540 400", "#fR": "710 400"}[sel]
            js.append('tl.to("%s",{rotation:%d,svgOrigin:"%s",%s},%.3f);' % (sel, a, org, tween, t))
        if last in SHAKE:
            arm, amp = SHAKE[last]
            base = p[1 if arm == "fL" else 3]
            amp, step = (amp * .5, .22) if calm else (amp, .09)
            org = "370 400" if arm == "fL" else "710 400"
            k, x = 0, t + 0.22
            while x < t + d - 0.1:
                js.append('tl.to("#%s",{rotation:%d,svgOrigin:"%s",duration:%.2f,ease:"none"},%.3f);' % (arm, base + (amp if k % 2 else -amp), org, step, x))
                x += step
                k += 1
    # never still: body sway from the first frame, breath on the head, a blink every 3.1 s, mouth on the voice
    t = 0.0
    while t < dur:
        js.append('tl.to("#bob",{rotation:%.2f,y:%.1f,svgOrigin:"540 900",duration:.3,ease:"sine.inOut"},%.2f);'
                  % (2.4 * math.sin(t * 2.1), 7 * math.sin(t * 4.2), t))
        js.append('tl.to("#head",{rotation:%.2f,svgOrigin:"540 350",duration:.3,ease:"sine.inOut"},%.2f);' % (4 * math.sin(t * 1.7 + 1), t))
        t += 0.3
    t = 2.0
    while t < dur:
        js.append('tl.set("#eL,#eR",{attr:{r:2}},%.2f);tl.set("#eL,#eR",{attr:{r:10}},%.2f);' % (t, t + 0.1))
        t += 3.1
    for i, lv in enumerate(levels):
        js.append('tl.set("#mouth",{attr:{ry:%.1f,rx:%.1f}},%.2f);' % (3 + 30 * lv, 26 + 6 * lv, i * 0.1))
    return js


# ---------------------------------------------------------------- amplify
def amplify(beats, ac, amp):
    """Turns the same ad up: punch-ins on the figure, slams and shake on every new picture,
    a flash, a problem or relief tint behind the beat, skin flying off on the skin beats.
    Set by `amp` in ad.json: {"turn": "<beat at>", "flakes": [poses], "big": [poses]}."""
    import random
    rnd = random.Random(5)
    under, body, js = [], [], []
    turn = next((i for i, b in enumerate(beats) if b["at"] == amp["turn"]), len(beats))
    for n, b in enumerate(beats):
        t, d = b["t"], b["e"] - b["t"]
        tint = "#FFD9CC" if n < turn else "#FFE9B8"
        under.append('<div id="tn%d" class="clip" data-start="%.3f" data-duration="%.3f" data-track-index="0" style="position:absolute;inset:0;background:%s"></div>' % (n, t, d, tint if n % 2 else "#fff"))
        big = 1.1 if b.get("pose") in amp.get("big", []) else (1.05 if n % 2 else 1.0)
        js.append('tl.to("#figwrap",{scale:%.2f,transformOrigin:"50%% 96%%",duration:.09,ease:"power4.out"},%.3f);' % (big, t))
        js.append('tl.fromTo("#fig",{y:-46},{y:0,duration:.26,ease:"bounce.out"},%.3f);' % t)
        if b.get("show"):
            body.append('<div id="fl%d" class="clip" data-start="%.3f" data-duration=".14" data-track-index="40" style="position:absolute;inset:0;background:%s"></div>' % (n, t, ac))
            js.append('tl.fromTo("#fl%d",{opacity:.75},{opacity:0,duration:.14},%.3f);' % (n, t))
            for k in range(8):
                js.append('tl.set(".pic,#figwrap",{x:%d,y:%d},%.3f);' % (rnd.randint(-22, 22), rnd.randint(-22, 22), t + k * .03))
            js.append('tl.set(".pic,#figwrap",{x:0,y:0},%.3f);' % (t + .25))
        if b.get("pose") in amp.get("flakes", []):
            bits = "".join('<i id="f%d_%d" style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;background:%s;display:block"></i>'
                           % (n, k, rnd.randint(380, 700), rnd.randint(1100, 1400), rnd.randint(30, 70), rnd.randint(18, 44), "#E9D8C4" if k % 3 else ac) for k in range(40))
            body.append('<div id="fw%d" class="clip" data-start="%.3f" data-duration="%.3f" data-track-index="41" style="position:absolute;inset:0;overflow:hidden">%s</div>' % (n, t, d, bits))
            for k in range(40):
                js.append('tl.to("#f%d_%d",{x:%d,y:%d,rotation:%d,opacity:0,duration:%.2f,ease:"power2.out"},%.3f);'
                          % (n, k, rnd.randint(-620, 620), rnd.randint(-900, 500), rnd.randint(-500, 500), min(d, rnd.uniform(.5, 1.1)), t + k * min(.03, d / 40)))
    return under, body, js


# ---------------------------------------------------------------- the page
def captions(words, hl, max_chars=20):
    """Short chunks, cut on the clock of the voice, one highlighted word colour."""
    chunks, cur = [], []
    for w in words:
        if cur and (sum(len(x["w"]) + 1 for x in cur) + len(w["w"]) > max_chars or cur[-1]["w"][-1] in ".,!?"):
            chunks.append(cur)
            cur = []
        cur.append(w)
    chunks.append(cur)
    return chunks


def build(run):
    ad = read(run / "ad.json")
    ac = ad.get("accent", "#C9731F")
    words = words_of(run)
    dur = round(read(run / "vo" / "timing.json")["scenes"][list(read(run / "vo" / "timing.json")["scenes"])[-1]]["end"] + 1.2, 2)
    i = 0
    beats = []
    for b in ad["beats"]:
        i = phrase_at(words, b["at"], i)
        beats.append(dict(b, t=words[i]["t"]))
    for a, b in zip(beats, beats[1:]):
        a["e"] = b["t"]
    beats[-1]["e"] = dur

    page = run / "page"
    (page / "assets").mkdir(parents=True, exist_ok=True)
    body, js = [], []
    for n, b in enumerate(beats):
        uid = "b%d" % n
        t, d = b["t"], b["e"] - b["t"]
        items = b.get("show") or []
        if not items:  # the picture stays up until something new replaces it
            continue
        end = next((x["t"] for x in beats[n + 1:] if x.get("show")), dur)
        d = end - t
        box = [(90, 110, 900, 660)] if len(items) == 1 else [(40, 150, 480, 600), (560, 150, 480, 600)]
        for k, it in enumerate(items):
            x, y, w, h = box[min(k, len(box) - 1)]
            sub = "%si%d" % (uid, k)
            if it.startswith("skin:"):
                inner = skin_diagram(sub, ac)
                if ad.get("skin_labels"):
                    inner = inner.replace("OLD DRY SKIN", ad["skin_labels"][0]).replace("YOUR SKIN", ad["skin_labels"][1])
                js += skin_moves(sub, t, d, it.split(":")[1])
            elif it.startswith("pic:"):
                inner = '<img src="assets/%s.jpg" alt="">' % it[4:]
            else:
                nm, _, txt = it.partition("|")
                inner = doodle(nm, ac, sub, txt)
                if nm == "blob":
                    k2 = t
                    while k2 < t + d - .1:
                        js.append('tl.to("#%sb",{y:%d,duration:.14,ease:"power2.in"},%.3f);tl.to("#%sb",{y:0,duration:.3,ease:"sine.out"},%.3f);' % (sub, 34, k2 + .2, sub, k2 + .36))
                        k2 += .8
                if nm == "clock":
                    js.append('tl.to("#%sh",{rotation:360,svgOrigin:"240 280",duration:%.2f,ease:"none"},%.3f);' % (sub, min(d, 1.4), t))
            body.append('<div id="%s" class="clip pic" data-start="%.3f" data-duration="%.3f" data-track-index="%d" '
                        'style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"><div id="%sw" class="fill">%s</div></div>'
                        % (sub, t, d, 10 + k, x, y, w, h, sub, inner))
            if ad.get("calm"):
                js.append('tl.from("#%sw",{opacity:0,duration:.45,ease:"sine.out"},%.3f);' % (sub, t + k * 0.1))
            else:
              js.append('tl.from("#%sw",{scale:%s,rotation:%d,opacity:0,duration:%s,ease:"%s"},%.3f);' % (sub, "2.4" if ad.get("amp") else ".3", -8 if k else 8, ".14" if ad.get("amp") else ".3", "power4.in" if ad.get("amp") else "back.out(2.4)", t + k * 0.06))
            js.append('tl.to("#%sw",{scale:1.03,duration:%.2f,ease:"none"},%.3f);' % (sub, max(0.1, d - 0.32), t + 0.32))
            if ad.get("calm") and it.startswith("pic:") and it[4:] in ("yai", "milan", "applied", "onarm", "dry", "shelf", "leg", "salt", "clock", "earth"):
                pass

    hl = {norm(x) for x in ad.get("highlight", [])}
    chunks = captions(words, hl, max_chars=16 if ad.get("calm") else 20)
    for n, ch in enumerate(chunks):
        st = ch[0]["t"]
        en = chunks[n + 1][0]["t"] if n + 1 < len(chunks) else dur  # a line stays up until the next one replaces it
        spans = " ".join('<span style="color:%s">%s</span>' % (ac, html.escape(w["w"])) if norm(w["w"]) in hl else html.escape(w["w"]) for w in ch)
        body.append('<div id="c%d" class="clip cap" data-start="%.3f" data-duration="%.3f" data-track-index="30">%s</div>' % (n, st, en - st, spans))
        if ad.get("amp"):
            js.append('tl.from("#c%d",{scale:1.5,duration:.1,ease:"power3.out"},%.3f);' % (n, st))
    for sm in ad.get("small_print", []):
        i = phrase_at(words, sm["at"], 0)
        body.append('<div id="sp%d" class="clip sm" data-start="%.3f" data-duration="%.3f" data-track-index="31">%s</div>'
                    % (i, words[i]["t"], dur - words[i]["t"], html.escape(sm["text"])))

    js += figure_moves(beats, audio_levels(run / "vo" / "track.mp3"), dur, calm=bool(ad.get("calm")))
    calm = ad.get("calm")
    if calm:
        rnd = __import__("random").Random(9)
        for n, b in enumerate(beats):
            if b.get("pose") in calm.get("flakes", []):
                bits = "".join('<i id="f%d_%d" style="position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx;background:#D9CDBF;display:block"></i>' % (n, k, rnd.randint(330, 750), rnd.randint(1050, 1300), rnd.randint(14, 30), rnd.randint(8, 16)) for k in range(18))
                body.append('<div id="fw%d" class="clip" data-start="%.3f" data-duration="%.3f" data-track-index="41" style="position:absolute;inset:0;overflow:hidden">%s</div>' % (n, b["t"], b["e"] - b["t"], bits))
                js += ['tl.to("#f%d_%d",{y:%d,x:%d,rotation:%d,duration:%.2f,ease:"none"},%.3f);' % (n, k, rnd.randint(350, 700), rnd.randint(-60, 60), rnd.randint(-120, 120), max(1.2, b["e"] - b["t"]), b["t"]) for k in range(18)]
    amp = ad.get("amp")
    if amp:
        under, body2, js2 = amplify(beats, ac, amp)
        body = under + body + body2
        js += js2
    doc = """<!doctype html>
<html><head><meta charset="utf-8"><script src="%s"></script><style>
*{margin:0;padding:0;box-sizing:border-box}html,body{width:%dpx;height:%dpx;background:#fff;overflow:hidden}
#root{position:relative;width:%dpx;height:%dpx;background:#fff;overflow:hidden;font-family:'Archivo Black',sans-serif}
.pic{position:absolute}.fill{width:100%%;height:100%%;display:flex;align-items:center;justify-content:center}
.fill img{max-width:100%%;max-height:100%%;object-fit:contain;border-radius:14px}.dd{width:100%%;height:100%%}
.cap{position:absolute;left:40px;right:40px;top:790px;text-align:center;font-size:%(cap)dpx;line-height:1.05;color:#111;z-index:5}
.sm{position:absolute;left:0;right:0;top:1860px;text-align:center;font-family:Inter,sans-serif;font-size:28px;color:#666}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="%.2f" data-width="%d" data-height="%d">
%s
<div id="figwrap" class="clip" data-start="0" data-duration="%.2f" data-track-index="1">%s</div>
</div>
<script>window.__timelines=window.__timelines||{};const tl=gsap.timeline({paused:true});
%s
tl.set({}, {}, %.2f);
window.__timelines["main"]=tl;</script></body></html>
""".replace("%(cap)dpx", "84px" if ad.get("amp") else "76px" if ad.get("calm") else "66px") % (GSAP, W, H, W, H, dur, W, H, "\n".join(body), dur, figure(ac), "\n".join(js), dur)
    (page / "index.html").write_text(doc)
    (page / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}))
    (run / "beats.json").write_text(json.dumps(beats, indent=1))
    print("page written: %d beats, %.1f s" % (len(beats), dur))
    return dur, beats


def pictures(run):
    from gdrive_creator import engine as E
    ad = read(run / "ad.json")
    dest = run / "page" / "assets"
    dest.mkdir(parents=True, exist_ok=True)
    for name, key in ad.get("pictures", {}).items():
        out = dest / (name + ".jpg")
        if out.exists():
            continue
        raw = dest / (name + ".raw")
        E.get_media(key, str(raw))
        subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "1400", str(raw), "--out", str(out)], capture_output=True, check=True)
        raw.unlink()
        print("picture", name)


# ---------------------------------------------------------------- the sound, made here too
def bed(path, dur, bpm=84, rate=22050, soft=False):
    """Soft chord pad and a light kick and hat, written sample by sample, seeded by nothing."""
    beat = 60.0 / bpm
    chords = [(220.0, 277.2, 329.6), (196.0, 246.9, 293.7), (174.6, 220.0, 261.6), (196.0, 246.9, 329.6)]
    n = int(dur * rate)
    a = array.array("h", bytes(2 * n))
    for i in range(n):
        t = i / rate
        bar = int(t / (beat * 4)) % 4
        pos = t % beat
        s = sum(math.sin(2 * math.pi * f * t) for f in chords[bar]) * 0.05
        s *= 0.75 + 0.25 * math.sin(2 * math.pi * t / (beat * 2))
        kick = math.sin(2 * math.pi * (55 + 90 * math.exp(-pos * 30)) * pos) * math.exp(-pos * 9) * 0.28 if int(t / beat) % 2 == 0 else 0
        hp = (t + beat / 2) % beat
        hat = math.sin(i * 12.9898) * 43758.5453 % 1 * 2 - 1
        hat *= math.exp(-hp * 60) * 0.05
        a[i] = int(max(-1, min(1, s if soft else s + kick + hat)) * 32000)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(a.tobytes())


def pops(path, beats, dur, rate=22050, hit=False):
    n = int(dur * rate)
    a = array.array("h", bytes(2 * n))
    for b in beats:
        if not b.get("show"):
            continue
        s = int(b["t"] * rate)
        for i in range(int(0.09 * rate)):
            t = i / rate
            if s + i < n:
                a[s + i] = int(14000 * math.sin(2 * math.pi * (900 - 5000 * t) * t) * math.exp(-t * 45))
        if hit:
            for i in range(int(0.3 * rate)):
                t = i / rate
                if s + i < n:
                    a[s + i] = max(-32000, min(32000, a[s + i] + int(20000 * math.sin(2 * math.pi * (120 - 180 * t) * t) * math.exp(-t * 11))))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(a.tobytes())


def render(run):
    dur, beats = build(run)
    page = run / "page"
    silent = run / "silent.mp4"
    subprocess.run(["npx", "hyperframes", "render", "--fps", str(FPS), "--output", str(silent.resolve())], cwd=str(page), check=True)
    calm = bool(read(run / "ad.json").get("calm"))
    bed(run / "bed.wav", dur, bpm=60 if calm else 84, soft=calm)
    amp = read(run / "ad.json").get("amp")
    pops(run / "pops.wav", beats, dur, hit=bool(amp))
    final = run / "final.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(run / "vo" / "track.mp3"),
                    "-i", str(run / "bed.wav"), "-i", str(run / "pops.wav"), "-filter_complex",
                    "[1]volume=1.0[v];[2]volume=%s[m];[3]volume=%s[p];[v][m][p]amix=inputs=3:duration=longest:normalize=0,alimiter=limit=0.95[a]" % ("0.24", "0.7") if amp else "[1]volume=1.0[v];[2]volume=0.12[m];[3]volume=0.0[p];[v][m][p]amix=inputs=3:duration=longest:normalize=0,alimiter=limit=0.95[a]" if calm else "[1]volume=1.0[v];[2]volume=0.16[m];[3]volume=0.35[p];[v][m][p]amix=inputs=3:duration=longest:normalize=0,alimiter=limit=0.95[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", "%.2f" % dur, str(final)], check=True)
    print("final:", final)


def tighten(run, limit=0.2):
    """Any pause in the voice longer than `limit` comes down to `limit`, and every time on the
    voice sheet moves with it. Runs after the voice and before build; the old track stays beside it."""
    import re
    vo = run / "vo"
    track = vo / "track.mp3"
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(track), "-af", "silencedetect=noise=-38dB:d=%.2f" % limit,
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
    cuts = [(a + limit / 2, b - limit / 2) for a, b in zip(starts, ends)]
    if not cuts:
        return 0.0
    def moved(t):
        return t - sum(max(0.0, min(t, b) - a) for a, b in cuts)
    keep, last = [], 0.0
    for a, b in cuts:
        keep.append("between(t,%.4f,%.4f)" % (last, a))
        last = b
    keep.append("gte(t,%.4f)" % last)
    shutil.copy2(track, vo / "track-before-tighten.mp3")
    shutil.copy2(vo / "timing.json", vo / "timing-before-tighten.json")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(vo / "track-before-tighten.mp3"), "-af",
                    "aselect='%s',asetpts=N/SR/TB" % "+".join(keep), "-c:a", "libmp3lame", "-b:a", "192k", str(track)], check=True)
    timing = read(vo / "timing.json")
    for sc in timing["scenes"].values():
        sc["start"], sc["end"] = round(moved(sc["start"]), 3), round(moved(sc["end"]), 3)
        for ln in sc["lines"]:
            ln["start"], ln["end"] = round(moved(ln["start"]), 3), round(moved(ln["end"]), 3)
    (vo / "timing.json").write_text(json.dumps(timing, indent=1))
    return round(sum(b - a for a, b in cuts), 2)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("pictures", "tighten", "build", "render", "all"):
        raise SystemExit(__doc__)
    run = Path(sys.argv[2]).resolve()
    cmd = sys.argv[1]
    if cmd in ("pictures", "all"):
        pictures(run)
    if cmd == "tighten":
        print("cut %s s of pauses" % tighten(run))
    if cmd == "build":
        build(run)
    if cmd in ("render", "all"):
        render(run)


if __name__ == "__main__":
    main()
