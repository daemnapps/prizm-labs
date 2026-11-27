#!/usr/bin/env python3
"""cartoon.py — a flat 1960s Saturday morning cartoon, drawn entirely in code. No video model.

The voice track and the beat list go in; a finished 9:16 video comes out. Inked line that
boils on twos, flat paint, mid-century colour, limited animation. Same doors as stick.py,
whose word timing, captions and pause tightening it uses.

    python3 cartoon.py look <run> [scene ...]   one still of each scene, into <run>/look/, no voice needed
    python3 cartoon.py pace <run> 1.15          speed the whole read, pitch held
    python3 cartoon.py tighten <run>            bring every long pause in the voice down
    python3 cartoon.py build <run>              write the HyperFrames page under <run>/page/
    python3 cartoon.py render <run>             render it and mix voice and music into <run>/final.mp4
    python3 cartoon.py all <run>                build and render

<run> is runs/video-edit/<brand>/<label>/ and holds lines.json, vo/ and ad.json. The beat
grammar is in README.md. No brand is named here: words come from ad.json.
"""
import array
import html
import json
import math
import random
import shutil
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stick"))
import stick as S  # noqa: E402

W, H = 1080, 1920
FPS = 30
GSAP = S.GSAP
ART = .86  # the drawing sits above the caption band
TWOS = 1 / 8.0  # the drawing changes eight times a second, like limited animation

INK = "#2A1B12"
CREAM, TEAL, DEEP, MUSTARD, CORAL, RED, OLIVE, NIGHT, PINK, SKY, SILVER = (
    "#F4E6C8", "#3F8F8B", "#1F5C63", "#E2A93B", "#E2714F", "#C33B2E", "#7C8A3A", "#1D2B4F", "#EFB7A5", "#9CCFD0", "#C9D3D6")
SKIN = "#F2C49B"
LINE = 'stroke="%s" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"' % INK
THIN = 'stroke="%s" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"' % INK


def r(x, y, w, h, fill, rx=0, ink=True):
    return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" %s/>' % (x, y, w, h, rx, fill, LINE if ink else "")


def c(x, y, rad, fill, ink=True):
    return '<circle cx="%s" cy="%s" r="%s" fill="%s" %s/>' % (x, y, rad, fill, LINE if ink else "")


def p(d, fill="none", ink=True, thin=False):
    return '<path d="%s" fill="%s" %s/>' % (d, fill, (THIN if thin else LINE) if ink else "")


def limb(d, col):
    """An arm or leg with weight: an ink stroke with paint down its middle."""
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="%s" fill="none" stroke="%s" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>' % (d, INK, d, col))


def label(x, y, text, size, fill=INK, anchor="middle", font="Chango"):
    return '<text x="%s" y="%s" text-anchor="%s" font-family="%s" font-size="%s" fill="%s">%s</text>' % (x, y, anchor, font, size, fill, html.escape(text))


def g(inner, id_=None, tr=None):
    return "<g%s%s>%s</g>" % (' id="%s"' % id_ if id_ else "", ' transform="%s"' % tr if tr else "", inner)


def star(x, y, rad, fill, pts=8, ink=False, inner=.32):
    a = []
    for i in range(pts * 2):
        q = rad if i % 2 == 0 else rad * inner
        t = math.pi * i / pts
        a.append("%.1f,%.1f" % (x + q * math.sin(t), y - q * math.cos(t)))
    return '<polygon points="%s" fill="%s" %s/>' % (" ".join(a), fill, LINE if ink else "")


def wall(col, dots=None):
    """A painted wall: flat colour, a floating band of darker paint, mid-century stars."""
    out = r(-120, -120, W + 240, H + 700, col, ink=False)
    rnd = random.Random(col)
    for _ in range(9):
        out += star(rnd.randint(40, W - 40), rnd.randint(120, 900), rnd.randint(22, 44), dots or "#ffffff33", 4)
    return out


def floor(col, y=1380):
    return r(-120, y, W + 240, H - y + 600, col, ink=False) + p("M-20 %d H1100" % y)


def tree_shape(x, y, w, h, fill, tiers=4):
    out = ""
    for i in range(tiers):
        top = y + h * i / tiers * .82
        wid = w * (i + 1.4) / (tiers + .4)
        hei = h * .36
        out += '<polygon points="%d,%d %d,%d %d,%d" fill="%s" %s/>' % (x, top, x - wid / 2, top + hei, x + wid / 2, top + hei, fill, LINE)
    return out


def snow(uid, n=46, seed=1):
    rnd = random.Random(seed)
    return g("".join(c(rnd.randint(0, W), rnd.randint(-200, H), rnd.randint(5, 13), "#fff", ink=False) for _ in range(n)), uid + "s")


def snow_moves(uid, t, d):
    return ['tl.fromTo("#%ss",{y:-120},{y:320,duration:%.2f,ease:"steps(%d)"},%.3f);' % (uid, d, max(2, int(d * 8)), t)]


# ------------------------------------------------------------------ the cast: lookalikes of nobody
def girl(uid, x, y, s=1.0, dress=CORAL, arm_id=None, flip=False):
    arm = g(limb("M-46 -150 L-128 -92", dress) + c(-132, -88, 17, SKIN), arm_id) if arm_id else limb("M-46 -150 L-96 -60", dress) + c(-98, -54, 17, SKIN)
    body = ('<polygon points="-58,-190 58,-190 96,-30 -96,-30" fill="%s" %s/>' % (dress, LINE)
            + limb("M-34 -30 V40", SKIN) + limb("M34 -30 V40", SKIN) + r(-62, 34, 50, 22, INK, 8) + r(12, 34, 50, 22, INK, 8)
            + limb("M46 -150 L96 -60", dress) + c(98, -54, 17, SKIN) + arm
            + c(-82, -292, 30, MUSTARD) + c(82, -292, 30, MUSTARD)
            + c(0, -270, 78, SKIN)
            + p("M-78 -280 C-74 -372 74 -372 78 -280 C40 -318 -40 -318 -78 -280 Z", MUSTARD)
            + g(c(-28, -268, 8, INK, ink=False) + c(28, -268, 8, INK, ink=False), uid + "e")
            + p("M-26 -226 Q0 -204 26 -226"))
    return g(g(body, uid + "bob"), None, "translate(%s %s) scale(%s %s)" % (x, y, -s if flip else s, s))


def dad(uid, x, y, s=1.0, arm_id=None):
    arm = g(limb("M50 -300 L140 -220", TEAL) + c(144, -216, 20, SKIN), arm_id) if arm_id else ""
    body = (limb("M-30 -70 V60", DEEP) + limb("M30 -70 V60", DEEP) + r(-62, -340, 124, 270, TEAL, 18) + r(-62, 54, 54, 24, INK, 8) + r(10, 54, 54, 24, INK, 8)
            + limb("M-58 -300 L-108 -170", TEAL) + c(-110, -162, 20, SKIN) + arm
            + r(-58, -470, 116, 136, SKIN, 40)
            + r(-74, -490, 148, 22, DEEP, 8) + r(-50, -546, 100, 62, DEEP, 12)
            + g(c(-22, -408, 8, INK, ink=False) + c(22, -408, 8, INK, ink=False), uid + "de")
            + p("M-24 -366 Q0 -348 24 -366"))
    return g(g(body, uid + "dbob"), None, "translate(%s %s) scale(%s)" % (x, y, s))


def bob(uid, t, d, part="bob", amt=8):
    """Limited animation: the character holds, then hops a pose on the eights."""
    return ['tl.to("#%s%s",{y:%d,duration:.25,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (uid, part, -amt, max(1, int(d / .25) - 1), t)]


def blink(uid, t, d, part="e"):
    out, k = [], t + .9
    while k < t + d - .2:
        out.append('tl.set("#%s%s",{opacity:0},%.3f);tl.set("#%s%s",{opacity:1},%.3f);' % (uid, part, k, uid, part, k + .125))
        k += 2.3
    return out


# ------------------------------------------------------------------ the scenes: (art, moves(uid,t,d))
def scene_title(u, ac, txt):
    rays = "".join('<polygon points="540,820 %d,%d %d,%d" fill="%s"/>' % (
        540 + 1500 * math.cos(a), 820 + 1500 * math.sin(a), 540 + 1500 * math.cos(a + .2), 820 + 1500 * math.sin(a + .2), MUSTARD)
        for a in [i * math.pi / 8 for i in range(16)])
    art = (r(-120, -120, W + 240, H + 700, CORAL, ink=False) + g(rays, u + "r")
           + star(540, 820, 520, CREAM, 22, ink=True, inner=.84)
           + label(540, 640, "IF YOU", 104, DEEP) + label(540, 760, "GREW UP", 118, DEEP) + label(540, 866, "IN THE", 86, RED)
           + label(540, 1030, "1960s", 184, RED)
           + g(tree_shape(150, 1250, 220, 330, TEAL, 3) + tree_shape(930, 1230, 240, 350, OLIVE, 3)))
    return art, lambda t, d: ['tl.to("#%sr",{rotation:22,svgOrigin:"540 820",duration:%.2f,ease:"steps(%d)"},%.3f);' % (u, d, int(d * 8), t)]


def scene_catalog(u, ac, txt):
    art = (wall(TEAL) + floor(OLIVE, 1180) + '<ellipse cx="540" cy="1310" rx="500" ry="150" fill="%s" %s/>' % (CORAL, LINE)
           + g(r(330, 880, 560, 390, CREAM, 10) + p("M610 880 V1270") + label(470, 990, "TOYS", 72, RED) + c(470, 1110, 72, TEAL)
               + r(680, 950, 150, 130, MUSTARD, 8) + c(730, 1160, 46, CORAL)
               + g('<circle cx="756" cy="1014" r="104" fill="none" stroke="%s" stroke-width="13"/>' % RED, u + "o")
               + g(r(780, 1120, 22, 200, MUSTARD) + p("M780 1320 L791 1356 L802 1320"), u + "pen", "rotate(24 790 1340)"), u + "c")
           + girl(u, 190, 1290, .95, CORAL))
    return art, lambda t, d: bob(u, t, d) + blink(u, t, d) + [
        'tl.from("#%so",{drawSVG:0,opacity:0,duration:.5,ease:"steps(4)"},%.3f);' % (u, t + .4),
        'tl.to("#%spen",{x:-46,y:-20,duration:.25,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .25) - 1), t)]


def scene_tv(u, ac, txt):
    art = (wall(DEEP, "#ffffff22") + floor(MUSTARD, 1300)
           + r(190, 470, 700, 640, "#8A4B23", 34) + r(240, 520, 470, 440, NIGHT, 50)
           + g(c(350, 870, 150, "#fff", ink=False) + c(620, 900, 180, "#fff", ink=False)
               + c(480, 700, 44, "#fff") + c(480, 790, 66, "#fff") + c(480, 880, 86, "#fff")
               + '<circle cx="466" cy="690" r="6" fill="%s"/><circle cx="494" cy="690" r="6" fill="%s"/>' % (INK, INK)
               + '<polygon points="480,702 526,712 480,716" fill="%s"/>' % CORAL, u + "show")
           + g(snow(u + "t", 14, 3), None)
           + c(790, 620, 44, MUSTARD) + c(790, 780, 44, MUSTARD) + r(750, 880, 80, 60, INK, 8)
           + p("M300 1110 L260 1250") + p("M780 1110 L820 1250")
           + p("M430 470 L320 300") + p("M640 470 L760 300")
           + g(girl(u, 340, 1680, .95, RED))
           + g(girl(u + "b", 740, 1700, .85, TEAL)))
    return art, lambda t, d: bob(u, t, d, amt=4) + blink(u, t, d) + blink(u + "b", t + .6, d) + snow_moves(u + "t", t, d) + [
        'tl.to("#%sshow",{x:-14,duration:.5,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .5) - 1), t)]


def scene_stocking(u, ac, txt):
    art = (wall(RED, "#ffffff1c") + r(-20, 720, 1120, 90, "#8A4B23") + r(120, 810, 840, 1600, "#B5683A", 0)
           + r(300, 1000, 480, 1500, INK, 0)
           + p("M340 2400 Q420 1560 540 1460 Q660 1560 740 2400 Z", MUSTARD, ink=False)
           + g(p("M420 620 V960 L320 1020 Q280 1120 380 1120 L560 1050 V620 Z", CREAM)
               + r(390, 570, 200, 96, "#fff", 18), u + "st")
           + g(c(490, 500, 86, "#E8872B") + p("M490 416 Q510 390 540 396"), u + "or")
           + g(p("M700 610 q50 -70 100 0 q-50 76 -100 0 Z", "#9A6A3B") + p("M750 560 V650", thin=True), u + "w1")
           + g(p("M820 640 q50 -70 100 0 q-50 76 -100 0 Z", "#9A6A3B") + p("M870 590 V680", thin=True), u + "w2"))
    return art, lambda t, d: [
        'tl.from("#%sor",{y:420,duration:.5,ease:"back.out(2)"},%.3f);' % (u, t + .1),
        'tl.from("#%sw1",{y:-900,duration:.4,ease:"bounce.out"},%.3f);' % (u, t + .8),
        'tl.from("#%sw2",{y:-900,duration:.4,ease:"bounce.out"},%.3f);' % (u, t + 1.15)]


def scene_tinsel(u, ac, txt):
    rnd = random.Random(4)
    strands = "".join(g('<path d="M%d %d v%d" stroke="#E9EEF0" stroke-width="5" stroke-linecap="round"/>' % (
        rnd.randint(250, 830), rnd.randint(460, 1240), rnd.randint(80, 130)), "%sq%d" % (u, i)) for i in range(26))
    art = (wall(MUSTARD) + floor(CORAL, 1520) + tree_shape(540, 300, 740, 1160, DEEP, 5) + r(490, 1450, 100, 110, "#8A4B23")
           + strands + r(800, 1500, 200, 40, "#8A4B23", 8) + p("M830 1540 V1700") + p("M970 1540 V1700")
           + girl(u, 900, 1480, 1.0, TEAL, u + "a", True))
    def mv(t, d):
        out = bob(u, t, d, amt=4) + blink(u, t, d)
        out.append('tl.to("#%sa",{rotation:-14,svgOrigin:"-46 -150",duration:.5,ease:"steps(3)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .5) - 1), t))
        for i in range(26):
            out.append('tl.from("#%sq%d",{opacity:0,y:-40,duration:.12,ease:"steps(2)"},%.3f);' % (u, i, t + d * .9 * i / 26))
        return out
    return art, mv


def scene_aluminum(u, ac, txt):
    rnd = random.Random(8)
    branches = ""
    for row in range(11):
        y = 330 + row * 106
        wid = 90 + row * 44
        for k in range(-3, 4):
            branches += '<path d="M540 %d L%d %d" stroke="#fff" stroke-width="12" stroke-linecap="round"/>' % (y - 40, 540 + wid * k / 3, y + 26)
    balls = "".join(c(rnd.randint(300, 780), rnd.randint(620, 1400), 30, RED) for _ in range(14))
    art = (wall(NIGHT, "#ffffff14") + floor("#3A2E55", 1560)
           + '<polygon points="540,240 150,1500 930,1500" fill="%s" %s/>' % (SILVER, LINE)
           + g('<polygon points="540,240 150,1500 930,1500" fill="#ffffff"/>', u + "tint")
           + branches + balls + star(540, 230, 70, MUSTARD, 8, ink=True)
           + r(500, 1500, 80, 90, "#777") + r(360, 1580, 360, 26, "#999", 10)
           + r(120, 1690, 150, 90, "#555", 12) + g(c(195, 1640, 90, "#fff") + "".join(
               '<path d="M195 1640 L%.0f %.0f A90 90 0 0 1 %.0f %.0f Z" fill="%s" %s/>' % (
                   195 + 90 * math.cos(a), 1640 + 90 * math.sin(a), 195 + 90 * math.cos(a + 1.57), 1640 + 90 * math.sin(a + 1.57), col, THIN)
               for a, col in zip([0, 1.57, 3.14, 4.71], [RED, "#3D6FD1", "#3FAE6A", MUSTARD])), u + "w"))
    def mv(t, d):
        out = ['tl.to("#%sw",{rotation:%d,svgOrigin:"195 1640",duration:%.2f,ease:"none"},%.3f);' % (u, int(d * 90), d, t)]
        k, i = t, 0
        tints = ["#F0563F", "#4E86F0", "#49C07B", "#F2BE3D"]
        while k < t + d:
            out.append('tl.set("#%stint polygon",{attr:{fill:"%s"}},%.3f);' % (u, tints[i % 4], k))
            k += 1.0
            i += 1
        return out
    art = art.replace('<polygon points="540,240 150,1500 930,1500" fill="#ffffff"/>', '<polygon points="540,240 150,1500 930,1500" fill="#F0563F" opacity=".55"/>')
    return art, mv


def scene_bubble(u, ac, txt):
    rnd = random.Random(2)
    art = wall(DEEP, "#ffffff18") + tree_shape(540, 120, 1500, 1800, OLIVE, 3)
    moves = []
    for i, (x, tube, base) in enumerate([(230, "#F3C95B", RED), (540, "#F08A5D", TEAL), (850, "#8FD6C6", MUSTARD)]):
        art += c(x, 760, 210, tube + "44", ink=False) + r(x - 74, 1180, 148, 190, base, 18) + p("M%d 1370 Q%d 1480 %d 1560" % (x, x + 30, x + 80)) + r(x - 54, 300, 108, 900, tube, 54)
        for k in range(9):
            art += g(c(x + rnd.randint(-22, 22), 1150, rnd.randint(11, 20), "#fff", ink=False), "%sb%d_%d" % (u, i, k))
            moves.append(("%sb%d_%d" % (u, i, k), k / 9.0))
    def mv(t, d):
        out = []
        for id_, ph in moves:
            out.append('tl.fromTo("#%s",{y:0},{y:-810,duration:1.4,ease:"steps(11)",repeat:%d},%.3f);' % (id_, max(1, int(d / 1.4) + 1), t + ph * 1.4 - 1.4))
        return out
    return art, mv


def house(x, base, wid, hgt, col, seed):
    rnd = random.Random(seed)
    out = r(x, base - hgt, wid, hgt, col) + '<polygon points="%d,%d %d,%d %d,%d" fill="%s" %s/>' % (x - 30, base - hgt, x + wid / 2, base - hgt - 170, x + wid + 30, base - hgt, DEEP, LINE)
    out += r(x + wid * .18, base - hgt * .7, 90, 90, "#F9D66B") + r(x + wid * .6, base - hgt * .7, 90, 90, "#F9D66B")
    for k in range(13):
        tt = k / 12.0
        out += c(x - 30 + tt * (wid / 2 + 30), base - hgt - tt * 170, 13, [RED, MUSTARD, "#49C07B", "#4E86F0"][k % 4], ink=False)
        out += c(x + wid / 2 + tt * (wid / 2 + 30), base - hgt - 170 + tt * 170, 13, [MUSTARD, "#4E86F0", RED, "#49C07B"][k % 4], ink=False)
    return out


def scene_drive(u, ac, txt):
    houses = "".join(house(x, 1180, 420, 300, col, x) for x, col in [(40, CORAL), (620, OLIVE), (1200, TEAL), (1780, MUSTARD), (2360, CORAL), (2940, OLIVE)])
    car = (r(-250, -120, 500, 130, SKY, 40) + p("M-160 -120 L-90 -230 H120 L190 -120 Z", CREAM)
           + r(-70, -210, 80, 80, "#F9D66B", 6) + r(30, -210, 80, 80, "#F9D66B", 6)
           + c(-40, -170, 30, SKIN) + c(70, -170, 26, SKIN)
           + g(c(-140, 10, 54, INK) + c(-140, 10, 18, CREAM), u + "w1") + g(c(150, 10, 54, INK) + c(150, 10, 18, CREAM), u + "w2")
           + r(-250, -70, 500, 14, CREAM, 6, ink=False))
    art = (r(-120, -120, W + 240, H + 700, NIGHT, ink=False) + c(860, 280, 90, CREAM, ink=False) + snow(u, 30, 6)
           + g(houses, u + "h") + r(-120, 1180, W + 240, 1400, "#E8EEF2", ink=False) + p("M-20 1180 H1100")
           + r(-120, 1460, W + 240, 1100, "#3C4356", ink=False)
           + g(car, u + "car", "translate(540 1420) scale(1.25)"))
    return art, lambda t, d: snow_moves(u, t, d) + [
        'tl.to("#%sh",{x:%d,duration:%.2f,ease:"steps(%d)"},%.3f);' % (u, -min(2300, int(d * 330)), d, int(d * 10), t),
        'tl.to("#%scar",{y:"-=8",duration:.25,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .25) - 1), t)]


def scene_window(u, ac, txt):
    santa = g(c(0, -300, 72, SKIN) + p("M-72 -310 Q0 -440 72 -310 Z", RED) + c(0, -400, 22, "#fff")
              + p("M-72 -280 Q0 -160 72 -280 Q0 -250 -72 -280 Z", "#fff")
              + r(-96, -210, 192, 230, RED, 40) + r(-96, -70, 192, 26, INK, 0, ink=False)
              + g(p("M90 -170 L170 -270") + c(174, -276, 20, "#fff"), u + "wv")
              + c(-26, -310, 7, INK, ink=False) + c(26, -310, 7, INK, ink=False), u + "san")
    art = (r(-120, -120, W + 240, H + 700, "#7A3B2E", ink=False) + r(60, 170, 960, 120, DEEP, 10) + label(540, 262, "CHRISTMAS", 76, MUSTARD)
           + r(60, 310, 960, 840, "#FBE9B8", 10) + r(100, 980, 880, 170, "#fff", 0, ink=False) + tree_shape(830, 480, 240, 520, OLIVE, 3)
           + g(santa, None, "translate(370 1040)") + star(180, 420, 40, MUSTARD) + star(620, 400, 34, CORAL)
           + r(60, 310, 960, 840, "#ffffff00", 10)
           + r(-120, 1150, W + 240, 1400, "#D9DEE2", ink=False) + p("M-20 1150 H1100")
           + girl(u, 300, 1760, 1.15, RED) + girl(u + "b", 760, 1760, 1.05, TEAL) + snow(u, 22, 11))
    return art, lambda t, d: blink(u, t, d) + blink(u + "b", t + .5, d) + bob(u, t, d, amt=5) + snow_moves(u, t, d) + [
        'tl.to("#%swv",{rotation:-30,svgOrigin:"90 -170",duration:.25,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .25) - 1), t)]


def scene_gift(u, ac, txt):
    radio = g(r(-120, -170, 240, 340, "#C33B2E", 22) + r(-90, -140, 180, 120, CREAM, 8) + c(0, 70, 70, MUSTARD) + "".join(p("M-40 %d H40" % y, thin=True) for y in (50, 70, 90))
              + p("M90 -170 V-310") + c(90, -320, 12, SILVER), u + "rad", "translate(540 880)")
    notes = "".join(g(label(300 + i * 150, 620 + (i % 2) * 90, "♪", 120, MUSTARD, font="serif"), "%sn%d" % (u, i)) for i in range(4))
    art = (wall(OLIVE) + floor("#8A4B23", 1340) + r(300, 1200, 480, 300, RED, 12) + r(500, 1200, 80, 300, MUSTARD, 0)
           + radio + notes + girl(u, 170, 1700, 1.0, MUSTARD, u + "a") + tree_shape(900, 900, 280, 640, DEEP, 3))
    def mv(t, d):
        out = blink(u, t, d) + bob(u, t, d, amt=5)
        out.append('tl.from("#%srad",{y:520,duration:.5,ease:"back.out(1.8)"},%.3f);' % (u, t + .1))
        for i in range(4):
            out.append('tl.from("#%sn%d",{opacity:0,y:80,duration:.5,ease:"steps(4)"},%.3f);' % (u, i, t + .6 + i * .3))
        return out
    return art, mv


def scene_slinky(u, ac, txt):
    coil = "".join('<ellipse cx="%d" cy="%d" rx="%d" ry="%d" fill="none" stroke="%s" stroke-width="9" transform="rotate(%d %d %d)"/>' % (
        x, y, a, b, SILVER, rot, x, y) for x, y, a, b, rot in [
        (540, 1180, 200, 70, 8), (500, 1130, 170, 90, -24), (590, 1120, 150, 100, 40), (520, 1220, 220, 60, -8), (610, 1200, 140, 80, 70),
        (450, 1190, 130, 90, 110), (560, 1080, 120, 60, 20), (640, 1150, 110, 70, 130), (480, 1090, 110, 60, 60)])
    art = (wall(CORAL) + floor(TEAL, 1300) + g(coil, u + "co") + girl(u, 210, 1640, .95, MUSTARD, u + "a") + girl(u + "b", 880, 1660, .9, RED)
           + p("M250 1420 Q380 1320 470 1240", "none") + p("M830 1440 Q720 1330 640 1240", "none"))
    return art, lambda t, d: blink(u, t, d) + blink(u + "b", t + .4, d) + bob(u, t, d, amt=6) + bob(u + "b", t + .1, d, amt=6) + [
        'tl.to("#%sco",{rotation:3,svgOrigin:"540 1150",duration:.25,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .25) - 1), t)]


def scene_cards(u, ac, txt):
    rnd = random.Random(5)
    cols = [CREAM, RED, TEAL, MUSTARD, "#fff", OLIVE]
    cards = ""
    for i in range(16):
        ang = -math.pi + math.pi * i / 15
        x, y = 540 + 440 * math.cos(ang), 760 + 560 * math.sin(ang)
        cards += g(r(-70, -50, 140, 100, cols[i % 6], 4) + star(0, 0, 26, rnd.choice([RED, DEEP, MUSTARD]), 5), "%sk%d" % (u, i), "translate(%.0f %.0f) rotate(%d)" % (x, y, rnd.randint(-12, 12)))
    art = (wall(SKY, "#ffffff44") + floor("#8A4B23", 1560) + r(200, 300, 680, 1270, "#F6EEDC", 0) + r(280, 360, 520, 1210, DEEP, 0) + cards
           + girl(u, 540, 1700, 1.05, RED, u + "a"))
    def mv(t, d):
        out = blink(u, t, d) + bob(u, t, d, amt=4)
        for i in range(16):
            out.append('tl.from("#%sk%d",{opacity:0,duration:.1,ease:"steps(1)"},%.3f);' % (u, i, t + .1 + d * .75 * i / 16))
        return out
    return art, mv


def scene_lot(u, ac, txt):
    wisps = "".join(g(p("M%d 1000 q-40 -70 0 -140 q40 -70 0 -140" % x, "none"), "%sv%d" % (u, i)) for i, x in enumerate((300, 460, 620)))
    art = (r(-120, -120, W + 240, H + 700, "#2E4A6B", ink=False) + c(180, 260, 80, CREAM, ink=False) + r(-120, 1380, W + 240, 1200, "#EEF2F4", ink=False) + p("M-20 1380 H1100")
           + tree_shape(170, 760, 300, 700, DEEP, 4) + tree_shape(910, 700, 320, 760, DEEP, 4)
           + p("M-20 330 H1100") + "".join(c(x, 345, 16, [RED, MUSTARD, "#49C07B"][i % 3], ink=False) for i, x in enumerate(range(40, 1080, 110)))
           + tree_shape(470, 720, 340, 780, OLIVE, 4)
           + g(wisps, None) + dad(u, 730, 1640, 1.05, u + "a") + girl(u, 310, 1720, .9, CORAL) + snow(u, 44, 2))
    def mv(t, d):
        out = blink(u, t, d) + blink(u, t, d, "de") + bob(u, t, d, amt=4) + bob(u, t, d, "dbob", 4) + snow_moves(u, t, d)
        for i in range(3):
            out.append('tl.fromTo("#%sv%d",{opacity:0,y:60},{opacity:1,y:-120,duration:1.6,ease:"steps(8)",repeat:%d},%.3f);' % (u, i, max(1, int(d / 1.6)), t + i * .5))
        return out
    return art, mv


def scene_angel(u, ac, txt):
    rnd = random.Random(7)
    wisps = "".join('<path d="M%d %d q60 -40 120 0 t120 0" fill="none" stroke="#fff" stroke-width="7" opacity=".85"/>' % (rnd.randint(300, 640), rnd.randint(520, 1320)) for _ in range(24))
    sparks = "".join(g(star(250 + i * 38, 900 - (i % 3) * 46, 26, MUSTARD, 4), "%sz%d" % (u, i)) for i in range(5))
    art = wall(TEAL) + floor(MUSTARD, 1480) + tree_shape(600, 260, 760, 1180, DEEP, 5) + wisps + r(550, 1420, 100, 90, "#8A4B23") + girl(u, 210, 1660, 1.05, RED, u + "a") + sparks
    def mv(t, d):
        out = blink(u, t, d) + bob(u, t, d, amt=6)
        out.append('tl.to("#%sa",{rotation:18,svgOrigin:"-46 -150",duration:.13,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .13) - 1), t))
        for i in range(5):
            out.append('tl.fromTo("#%sz%d",{scale:.2,opacity:0,svgOrigin:"%d 880"},{scale:1.2,opacity:1,duration:.3,ease:"steps(3)",repeat:%d,yoyo:true},%.3f);' % (u, i, 250 + i * 38, max(1, int(d / .3) - 1), t + i * .12))
        return out
    return art, mv


def scene_canes(u, ac, txt):
    rnd = random.Random(12)
    canes = ""
    for i in range(10):
        x, y = rnd.randint(280, 800), 620 + i * 84
        canes += ('<path d="M%d %d v90 M%d %d q0 -44 36 -44 q36 0 36 40" fill="none" stroke="%s" stroke-width="26" stroke-linecap="round"/>'
                  '<path d="M%d %d v90 M%d %d q0 -44 36 -44 q36 0 36 40" fill="none" stroke="%s" stroke-width="14" stroke-linecap="round" stroke-dasharray="16 16"/>' % (x, y, x, y, INK, x, y, x, y, "#F7EFE3"))
    art = (wall(CORAL) + floor(TEAL, 1500) + tree_shape(540, 260, 800, 1200, DEEP, 5) + canes + r(490, 1440, 100, 90, "#8A4B23")
           + r(800, 180, 190, 210, CREAM, 6) + r(800, 180, 190, 60, RED, 6) + label(895, 228, "DEC", 40, CREAM) + label(895, 338, "24", 92, INK)
           + g(limb("M180 1450 L420 1190", CORAL) + c(424, 1186, 24, SKIN), u + "hand")
           + g(limb("M1100 1000 L900 1060", MUSTARD) + c(894, 1064, 26, SKIN) + limb("M880 1064 L862 980", SKIN), u + "mum"))
    return art, lambda t, d: [
        'tl.fromTo("#%shand",{x:-90,y:90},{x:0,y:0,duration:.5,ease:"steps(4)"},%.3f);' % (u, t + .2),
        'tl.to("#%shand",{x:-120,y:120,duration:.4,ease:"steps(3)"},%.3f);' % (u, t + max(1.2, d * .6)),
        'tl.to("#%smum",{rotation:6,svgOrigin:"880 1064",duration:.2,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .2) - 1), t + .8)]


def scene_lot_empty(u, ac, txt):
    wisps = "".join(g(p("M%d 1200 q-40 -70 0 -140 q40 -70 0 -140" % x, "none"), "%sv%d" % (u, i)) for i, x in enumerate((360, 540, 720)))
    art = (r(-120, -120, W + 240, H + 700, "#3A4F73", ink=False) + c(860, 240, 80, CREAM, ink=False) + r(-120, 1380, W + 240, 1200, "#EEF2F4", ink=False) + p("M-20 1380 H1100")
           + tree_shape(170, 760, 300, 700, DEEP, 4) + tree_shape(910, 700, 320, 760, DEEP, 4)
           + p("M-20 330 H1100") + "".join(c(x, 345, 16, [RED, MUSTARD, "#49C07B"][i % 3], ink=False) for i, x in enumerate(range(40, 1080, 110)))
           + wisps + snow(u, 44, 5))
    def mv(t, d):
        out = snow_moves(u, t, d)
        for i in range(3):
            out.append('tl.fromTo("#%sv%d",{opacity:0,y:60},{opacity:1,y:-120,duration:1.6,ease:"steps(8)",repeat:%d},%.3f);' % (u, i, max(1, int(d / 1.6)), t + i * .5))
        return out
    return art, mv


def scene_tablet(u, ac, txt):
    art = (wall(SKY, "#ffffff44") + floor(OLIVE, 1400) + girl(u, 540, 1560, 1.25, TEAL) + r(350, 1270, 380, 250, INK, 22) + r(370, 1290, 340, 210, "#6DB6F2", 10) + label(540, 1440, "?", 110, CREAM))
    return art, lambda t, d: blink(u, t, d)


def woman(uid, x, y, s=1.0, top=MUSTARD, arm_id=None, sleeves=True, spots=False, cardigan=False):
    """Her, today: silver set hair, kind face. Spots are drawn on her bare arm when asked."""
    sk = top if sleeves else SKIN
    arm = g(limb("M56 -250 L150 -170", sk) + c(154, -166, 20, SKIN), arm_id) if arm_id else limb("M56 -250 L108 -120", sk) + c(110, -112, 20, SKIN)
    marks = "".join(c(px, py, 8, "#8A5A33", ink=False) for px, py in ((80, -220), (98, -176), (-84, -206))) if spots else ""
    body = (limb("M-30 -40 V70", SKIN) + limb("M30 -40 V70", SKIN) + r(-62, 66, 54, 22, INK, 8) + r(8, 66, 54, 22, INK, 8)
            + '<polygon points="-66,-290 66,-290 92,-20 -92,-20" fill="%s" %s/>' % (top, LINE)
            + ('<polygon points="-66,-290 -22,-290 -40,-20 -92,-20" fill="%s" %s/><polygon points="66,-290 22,-290 40,-20 92,-20" fill="%s" %s/>' % (DEEP, LINE, DEEP, LINE) if cardigan else "")
            + limb("M-56 -250 L-108 -120", DEEP if cardigan else sk) + c(-110, -112, 20, SKIN) + arm + marks
            + c(0, -372, 84, SKIN)
            + p("M-92 -372 C-104 -486 104 -486 92 -372 C60 -436 -60 -436 -92 -372 Z", SILVER)
            + g(c(-30, -372, 8, INK, ink=False) + c(30, -372, 8, INK, ink=False), uid + "e")
            + p("M-24 -326 Q0 -310 24 -326"))
    return g(g(body, uid + "bob"), None, "translate(%s %s) scale(%s)" % (x, y, s))


def tube(x, y, s, kind, tr=""):
    """The real tube's shape and colour, in the film's style."""
    col, ink = ("#4A3A32", CREAM) if kind == "body" else ("#EBDDAA", INK)
    name = "BODY SCRUB" if kind == "body" else "FACE SCRUB"
    art = (r(-90, -220, 180, 26, col, 4) + '<polygon points="-90,-196 90,-196 70,190 -70,190" fill="%s" %s/>' % (col, LINE)
           + r(-72, 190, 144, 70, col, 8) + '<circle cx="0" cy="-90" r="46" fill="none" stroke="%s" stroke-width="5"/>' % ink
           + label(0, -14, "brand_b", 27, ink, font="Playfair Display") + label(0, 54, name, 22, ink, font="Fredoka"))
    return g(art, None, "translate(%s %s) scale(%s) %s" % (x, y, s, tr))


def scene_portrait(u, ac, txt):
    frame = r(120, 300, 840, 1000, CREAM, 8) + r(170, 350, 740, 760, SKY, 0) + r(170, 900, 740, 210, "#8A4B23", 0, ink=False)
    art = (wall(RED, "#ffffff1c") + floor("#8A4B23", 1500) + frame
           + g(dad(u + "a", 700, 1040, .8) + woman(u, 480, 1020, .8, RED, cardigan=True) + girl(u + "b", 300, 1050, .7, TEAL), None)
           + label(540, 1220, "CHRISTMAS", 60, RED) + g(star(880, 400, 210, "#fff", 10), u + "fl"))
    return art, lambda t, d: blink(u, t, d) + ['tl.fromTo("#%sfl",{opacity:0},{opacity:1,duration:.1,repeat:1,yoyo:true},%.3f);' % (u, t + .5), 'tl.set("#%sfl",{opacity:0},%.3f);' % (u, t + .75)]


def scene_face(u, ac, txt):
    """Her face, close, with the problem on it: brown marks that stamp back, or dry cracked patches."""
    art = wall(TEAL) + c(540, 760, 380, SKIN) + p("M150 760 C130 240 950 240 930 760 C840 470 240 470 150 760 Z", SILVER)
    art += g(c(390, 720, 24, INK, ink=False) + c(690, 720, 24, INK, ink=False), u + "e") + p("M430 960 Q540 1020 650 960")
    pts = [(300, 840), (760, 830), (540, 620), (650, 900), (420, 880)]
    moves = []
    for i, (x, y) in enumerate(pts):
        if txt == "dry":
            art += g(p("M%d %d l34 22 l-14 30 l38 18 M%d %d l-30 26" % (x - 40, y - 40, x - 6, y - 18), thin=True) + c(x + 20, y + 20, 10, "#F7EBDD"), "%sm%d" % (u, i))
        else:
            art += g(c(x, y, 32 - i * 2, "#8A5A33", ink=False), "%sm%d" % (u, i))
        moves.append('tl.from("#%sm%d",{opacity:0,duration:.15,ease:"steps(2)"},T+%.2f);' % (u, i, .2 + i * .3))
    return art, lambda t, d: blink(u, t, d) + [m.replace("T+", "%.3f+" % t) for m in moves]


def scene_covered(u, ac, txt):
    art = wall(TEAL) + floor(OLIVE, 1420) + r(120, 280, 840, 1140, "#8A4B23", 12) + r(160, 320, 760, 1060, "#CDE4E2", 8) + woman(u, 540, 1270, 1.1, MUSTARD, u + "a", cardigan=True)
    return art, lambda t, d: blink(u, t, d) + bob(u, t, d, amt=4) + ['tl.to("#%sa",{rotation:-16,svgOrigin:"56 -250",duration:.4,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .4) - 1), t)]


def scene_spots(u, ac, txt):
    """Her arm, close. The spots stamp themselves back in the same places."""
    pts = [(340, 840), (560, 760), (720, 900), (470, 1000), (830, 800)]
    spots = "".join(g(c(x, y, 46 - i * 4, "#8A5A33"), "%ss%d" % (u, i)) for i, (x, y) in enumerate(pts))
    art = wall(CORAL) + r(-120, 620, W + 240, 520, SKIN, 0) + p("M-20 620 H1100") + p("M-20 1140 H1100") + spots
    def mv(t, d):
        out = []
        for i in range(len(pts)):
            out.append('tl.fromTo("#%ss%d",{scale:1.8,opacity:0,transformOrigin:"50%% 50%%"},{scale:1,opacity:1,duration:.2,ease:"steps(3)"},%.3f);' % (u, i, t + .15 + i * .3))
            if d > 4:
                out.append('tl.to("#%ss%d",{opacity:.25,duration:.5,ease:"steps(3)"},%.3f);' % (u, i, t + d * .5))
                out.append('tl.to("#%ss%d",{opacity:1,scale:1,duration:.15,ease:"steps(2)"},%.3f);' % (u, i, t + d * .75 + i * .08))
        return out
    return art, mv


def scene_dry(u, ac, txt):
    """A shin, close, flaking like sandpaper."""
    rnd = random.Random(6)
    flakes = "".join(g('<polygon points="%d,%d %d,%d %d,%d" fill="#F7EBDD" %s/>' % (x, y, x + 34, y + 8, x + 12, y + 30, THIN), "%sf%d" % (u, i)) for i, (x, y) in enumerate((rnd.randint(150, 900), rnd.randint(640, 1080)) for _ in range(24)))
    cracks = "".join(p("M%d %d l40 26 l-16 34 l44 22" % (rnd.randint(120, 860), rnd.randint(640, 1000)), thin=True) for _ in range(12))
    art = wall(MUSTARD) + r(-120, 620, W + 240, 520, "#E3B58B", 0) + p("M-20 620 H1100") + p("M-20 1140 H1100") + cracks + flakes
    def mv(t, d):
        out = []
        for i in range(24):
            out.append('tl.to("#%sf%d",{y:%d,x:%d,duration:1.2,ease:"steps(8)",repeat:%d},%.3f);' % (u, i, 820, rnd.randint(-40, 40), max(1, int(d / 2.0)), t + i * .08))
        return out
    return art, mv


def scene_shelf(u, ac, txt):
    """Everything she tried, and why: bottle after bottle, each one crossed out."""
    rnd = random.Random(3)
    bottles, moves = "", []
    for row, y in enumerate((620, 1040)):
        for k, x in enumerate((230, 450, 670, 870)):
            col = rnd.choice([PINK, SKY, CREAM, MUSTARD, "#fff"])
            i = row * 4 + k
            bottles += r(x - 66, y - 240, 132, 240, col, 18) + r(x - 34, y - 300, 68, 62, INK, 8) + r(x - 44, y - 170, 88, 80, "#ffffffaa", 4, ink=False)
            bottles += g(p("M%d %d L%d %d" % (x - 88, y - 260, x + 88, y + 10)).replace('stroke-width="9"', 'stroke-width="18"').replace(INK, RED) + p("M%d %d L%d %d" % (x + 88, y - 260, x - 88, y + 10)).replace('stroke-width="9"', 'stroke-width="18"').replace(INK, RED), "%sx%d" % (u, i))
    art = wall(SKY, "#ffffff44") + bottles + r(70, 620, 940, 30, "#8A4B23", 6) + r(70, 1040, 940, 30, "#8A4B23", 6)
    return art, lambda t, d: ['tl.from("#%sx%d",{opacity:0,scale:1.6,transformOrigin:"50%% 50%%",duration:.14,ease:"steps(2)"},%.3f);' % (u, i, t + .2 + i * min(.35, d / 10)) for i in range(8)]


def scene_layers(u, ac, txt):
    """Cross-section: the old top layer clears, and what comes in behind it changes."""
    marks = (240, 480, 760) if txt != "dry" else ()
    top = "".join(c(x, 640, 26, "#8A5A33", ink=False) for x in marks)
    new = "".join(c(x, 900, 26, "#8A5A33", ink=False) for x in marks)
    art = (wall(DEEP, "#ffffff18") + g(r(70, 560, 940, 170, "#E3B58B", 14) + top, u + "t") + g(r(70, 760, 940, 200, "#F2C49B", 14) + g(new, u + "n"), None)
           + r(70, 990, 940, 280, "#F7D9BC", 14) + g(tube(860, 330, .9, ac, "rotate(24)"), u + "tb"))
    return art, lambda t, d: [
        'tl.to("#%st",{x:1200,duration:.7,ease:"steps(6)"},%.3f);' % (u, t + d * .35),
        'tl.to("#%sn",{opacity:0,duration:.7,ease:"steps(5)"},%.3f);' % (u, t + d * .6),
        'tl.from("#%stb",{y:-700,duration:.45,ease:"back.out(1.6)"},%.3f);' % (u, t + .1)]


def scene_scrub(u, ac, txt):
    """In the shower: small circles, the tube beside her."""
    tiles = "".join(p("M-20 %d H1100" % y, thin=True) for y in range(150, 1500, 150)) + "".join(p("M%d 0 V1500" % x, thin=True) for x in range(135, 1080, 135))
    art = (r(-120, -120, W + 240, H + 700, "#CDE4E2", ink=False) + tiles + floor(TEAL, 1480) + g(c(620, 780, 34, "#fff") + c(700, 700, 22, "#fff"), u + "b")
           + woman(u, 430, 1420, 1.15, PINK, u + "a", sleeves=False) + tube(860, 1240, .95, ac))
    return art, lambda t, d: blink(u, t, d) + bob(u, t, d, amt=4) + [
        'tl.to("#%sa",{rotation:-22,svgOrigin:"56 -250",duration:.25,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .25) - 1), t),
        'tl.to("#%sb",{y:-90,duration:1,ease:"steps(6)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d)), t)]


def scene_glad(u, ac, txt):
    """The payoff: the same Christmas, no cardigan."""
    art = (wall(RED, "#ffffff1c") + floor("#8A4B23", 1500) + tree_shape(830, 480, 400, 980, DEEP, 4) + star(830, 470, 66, MUSTARD, 8, ink=True)
           + woman(u, 400, 1480, 1.15, TEAL, u + "a", sleeves=False) + girl(u + "b", 650, 1560, .75, CORAL))
    return art, lambda t, d: blink(u, t, d) + bob(u, t, d) + ['tl.to("#%sa",{rotation:-30,svgOrigin:"56 -250",duration:.25,ease:"steps(2)",repeat:%d,yoyo:true},%.3f);' % (u, max(1, int(d / .25) - 1), t)]


def scene_pack(u, ac, txt):
    """The close: the real packshot sits on this card, laid over as a picture, never drawn."""
    art = r(-120, -120, W + 240, H + 700, CREAM, ink=False) + star(540, 1040, 640, MUSTARD, 24, inner=.9) + snow(u, 18, 4)
    return art, lambda t, d: snow_moves(u, t, d)


def scene_end(u, ac, txt):
    art = (r(-120, -120, W + 240, H + 700, DEEP, ink=False) + snow(u, 40, 9) + star(540, 700, 440, CREAM, 20, ink=True, inner=.84)
           + label(540, 660, "WHAT DID", 84, RED) + label(540, 770, "WE MISS?", 84, RED)
           + g(label(540, 1320, txt or "", 76, CREAM, font="Playfair Display"), u + "name"))
    return art, lambda t, d: snow_moves(u, t, d) + ['tl.from("#%sname",{opacity:0,duration:.5,ease:"steps(5)"},%.3f);' % (u, t + max(.2, d - 2.4))]


# ------------------------------------------------------------------ the Christmas set: one drawing, one action, per spoken thought
def tw(sel, vars_, at, kind="to"):
    return 'tl.%s("%s",%s,%.3f);' % (kind, sel, vars_, at)


def ft(sel, a, b, at):
    return 'tl.fromTo("%s",%s,%s,%.3f);' % (sel, a, b, at)


def stamps(sel_fmt, n, t, step, vars_='{opacity:0,scale:1.8,transformOrigin:"50%% 50%%",duration:.14,ease:"steps(2)"}'):
    return [tw(sel_fmt % i, vars_.replace("%%", "%"), t + i * step, "from") for i in range(n)]


def creator(uid, x, y, s=1.0, top=RED, arm_id=None, spots=False):
    """Her, today: chin-length silver bob, gold hoops, the same woman in every scene."""
    sk = top
    arm = g(limb("M56 -250 L150 -170", sk) + c(154, -166, 20, SKIN), arm_id) if arm_id else limb("M56 -250 L108 -120", sk) + c(110, -112, 20, SKIN)
    marks = c(-42, -350, 11, "#8A5A33", ink=False) + c(-22, -326, 8, "#8A5A33", ink=False) + c(48, -340, 10, "#8A5A33", ink=False) if spots else ""
    body = (limb("M-30 -40 V70", SKIN) + limb("M30 -40 V70", SKIN) + r(-62, 66, 54, 22, INK, 8) + r(8, 66, 54, 22, INK, 8)
            + '<polygon points="-66,-290 66,-290 92,-20 -92,-20" fill="%s" %s/>' % (top, LINE)
            + limb("M-56 -250 L-108 -120", sk) + c(-110, -112, 20, SKIN) + arm
            + p("M-96 -350 C-110 -476 110 -476 96 -350 L96 -296 L60 -296 C70 -350 60 -400 0 -404 C-60 -400 -70 -350 -60 -296 L-96 -296 Z", SILVER)
            + c(0, -360, 78, SKIN) + p("M-82 -372 C-70 -452 70 -452 82 -372 C50 -414 -50 -414 -82 -372 Z", SILVER)
            + c(-82, -326, 9, MUSTARD) + c(82, -326, 9, MUSTARD) + marks
            + g(c(-28, -368, 8, "#3C5A70", ink=False) + c(28, -368, 8, "#3C5A70", ink=False), uid + "e")
            + p("M-24 -318 Q0 -300 24 -318"))
    return g(g(body, uid + "bob"), None, "translate(%s %s) scale(%s)" % (x, y, s))


def head(x, y, rad, hair):
    return c(x, y, rad, SKIN) + p("M%d %d C%d %d %d %d %d %d Z" % (x - rad, y - 6, x - rad, y - rad * 1.5, x + rad, y - rad * 1.5, x + rad, y - 6), hair) + c(x - rad * .35, y + 6, 6, INK, ink=False) + c(x + rad * .35, y + 6, 6, INK, ink=False)


def scene_ornament(u, ac, txt):
    """A giant glass ornament swings in; the room is curved in its reflection; we dive through."""
    room = r(370, 760, 340, 300, "#F2C14E", 150, ink=False) + tree_shape(470, 780, 130, 240, DEEP, 3) + c(620, 860, 34, CREAM, ink=False) + p("M380 1000 Q540 1060 700 1000", thin=True)
    orn = (c(540, 880, 400, RED) + g(room, u + "rm") + '<path d="M260 680 Q340 560 470 520" fill="none" stroke="#fff" stroke-width="26" stroke-linecap="round" opacity=".7"/>'
           + r(490, 450, 100, 60, MUSTARD, 8) + p("M540 450 V-200"))
    art = wall(NIGHT, "#ffffff14") + snow(u, 34, 3) + g(orn, u + "o") + g(label(540, 1490, "IF YOU GREW UP", 74, CREAM) + label(540, 1610, "IN THE 1960s", 74, MUSTARD), u + "ttl")
    return art, lambda t, d: snow_moves(u, t, d) + [
        ft("#%so" % u, '{rotation:-14,svgOrigin:"540 -200"}', '{rotation:10,svgOrigin:"540 -200",duration:%.2f,ease:"steps(%d)"}' % (d * .55, int(d * 6) or 2), t),
        tw("#%so" % u, '{scale:9,svgOrigin:"540 880",duration:%.2f,ease:"power2.in"}' % (d * .4), t + d * .58), tw("#%sttl" % u, "{opacity:0,duration:.1}", t + d * .58)]


def scene_catalog_thump(u, ac, txt):
    heads = "".join(g(head(x, 930, rd, h), "%sh%d" % (u, i)) for i, (x, rd, h) in enumerate([(170, 62, MUSTARD), (350, 72, "#8A4B23"), (540, 58, RED), (730, 74, MUSTARD), (910, 64, "#8A4B23")]))
    book = g(r(250, 760, 580, 250, RED, 10) + r(270, 730, 540, 30, CREAM, 2) + r(270, 700, 540, 30, "#fff", 2) + label(540, 900, "CHRISTMAS", 64, MUSTARD) + label(540, 975, "TOY BOOK", 44, CREAM), u + "b")
    art = wall(TEAL) + heads + r(-120, 1000, W + 240, 1200, "#8A4B23", 0) + p("M-20 1000 H1100") + book
    return art, lambda t, d: [tw("#%sb" % u, '{y:-1100,duration:.3,ease:"power3.in"}', t + .05, "from"), tw("#%sb" % u, '{y:18,duration:.08,repeat:1,yoyo:true}', t + .36)] + [
        tw("#%sh%d" % (u, i), '{y:260,duration:.2,ease:"back.out(2)"}', t + .4 + i * .09, "from") for i in range(5)]


def scene_crayon(u, ac, txt):
    toys = c(310, 620, 92, CORAL) + r(620, 530, 200, 170, TEAL, 12) + p("M250 980 L370 880 L490 980 Z", MUSTARD) + r(250, 980, 240, 60, RED, 8) + c(720, 960, 92, OLIVE)
    rings = "".join('<circle id="%sr%d" cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="15" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>' % (u, i, x, y, rad, RED) for i, (x, y, rad) in enumerate([(310, 620, 134), (720, 615, 158), (370, 950, 158), (720, 960, 134)]))
    cray = g(r(-22, -170, 44, 170, RED, 8) + '<polygon points="-22,0 22,0 0,46" fill="%s" %s/>' % (RED, LINE), u + "cr", "translate(310 486) rotate(24)")
    art = wall(OLIVE) + r(110, 380, 860, 800, "#FFF6DF", 10) + p("M540 380 V1180") + g(toys, u + "t") + rings + cray
    def mv(t, d):
        out, pts = [], [(310, 486), (720, 457), (370, 792), (720, 826)]
        for i, (x, y) in enumerate(pts):
            at = t + i * (d / 4.2)
            out.append(tw("#%scr" % u, '{x:%d,y:%d,duration:.14,ease:"steps(2)"}' % (x - 310, y - 486), at))
            out.append(tw("#%sr%d" % (u, i), '{attr:{"stroke-dashoffset":0},duration:%.2f,ease:"steps(7)"}' % (min(.5, d / 5)), at + .1))
        return out
    return art, mv


def tv_set(u, inner):
    return (r(190, 420, 700, 640, "#8A4B23", 34) + r(240, 470, 470, 440, NIGHT, 50) + g(inner, u + "sc") + c(790, 570, 44, MUSTARD) + c(790, 730, 44, MUSTARD)
            + p("M300 1060 L260 1200") + p("M780 1060 L820 1200") + p("M430 420 L320 250") + p("M640 420 L760 250"))


def scene_once(u, ac, txt):
    show = (c(400, 830, 120, "#fff", ink=False) + c(570, 860, 130, "#fff", ink=False) + c(475, 650, 40, "#fff") + c(475, 730, 58, "#fff") + c(475, 810, 74, "#fff")
            + c(462, 642, 5, INK, ink=False) + c(488, 642, 5, INK, ink=False) + g(limb("M530 720 L600 660", "#8A4B23"), u + "wv"))
    kids = "".join(head(x, 1560, 80, h) for x, h in ((240, MUSTARD), (440, RED), (640, "#8A4B23"), (840, MUSTARD)))
    art = wall(DEEP, "#ffffff22") + floor(CORAL, 1250) + tv_set(u, show) + kids
    return art, lambda t, d: [tw("#%swv" % u, '{rotation:-26,svgOrigin:"530 720",duration:.25,ease:"steps(2)",repeat:%d,yoyo:true}' % max(1, int(d / .25) - 1), t)]


def scene_out_of_luck(u, ac, txt):
    show = g(c(475, 690, 150, "#fff", ink=False) + c(475, 640, 44, "#CFE2E8", ink=False), u + "dot")
    kids = "".join(g(c(x, 1560, 80, SKIN) + p("M%d 1554 C%d 1450 %d 1450 %d 1554 Z" % (x - 80, x - 80, x + 80, x + 80), h) + c(x - 26, 1560, 6, INK, ink=False) + c(x + 26, 1560, 6, INK, ink=False)
                       + g(p("M%d 1608 Q%d 1630 %d 1608" % (x - 22, x, x + 22)), "%sm%d" % (u, i)) + g('<ellipse cx="%d" cy="1616" rx="14" ry="22" fill="%s"/>' % (x, INK), "%sn%d" % (u, i)), "%sk%d" % (u, i))
                   for i, (x, h) in enumerate(((240, MUSTARD), (440, RED), (640, "#8A4B23"), (840, MUSTARD))))
    art = wall(DEEP, "#ffffff22") + floor(CORAL, 1250) + tv_set(u, show) + kids
    def mv(t, d):
        out = [tw("#%sdot" % u, '{scale:.03,svgOrigin:"475 690",duration:.45,ease:"steps(5)"}', t + .3), tw("#%sdot" % u, '{opacity:0,duration:.05}', t + .85)]
        for i in range(4):
            out += [tw("#%sn%d" % (u, i), '{opacity:0,duration:.01}', t, "from"), tw("#%sm%d" % (u, i), '{opacity:0,duration:.01}', t + .9), tw("#%sn%d" % (u, i), '{opacity:0,duration:.01}', t - .01, "to")]
            out.append(ft("#%sn%d" % (u, i), "{opacity:0}", "{opacity:1,duration:.05}", t + .9))
            out.append(tw("#%sk%d" % (u, i), '{y:26,duration:.2,ease:"steps(2)"}', t + .95))
        return out
    return art, mv


def scene_lights(u, ac, txt):
    bulbs, n = "", 26
    cols = [RED, MUSTARD, "#49C07B", "#4E86F0"]
    for i in range(n):
        f = i / (n - 1)
        wid = 60 + 340 * f
        x, y = 540 + wid * math.sin(f * 15), 340 + f * 1010
        bulbs += g(c(x, y, 22, cols[i % 4]) + c(x, y, 46, cols[i % 4] + "55", ink=False), "%sb%d" % (u, i))
    hand = g(limb("M1160 900 L780 760", TEAL) + c(772, 756, 26, SKIN), u + "hd")
    art = wall(MUSTARD) + floor(CORAL, 1480) + tree_shape(540, 240, 860, 1200, DEEP, 5) + r(490, 1420, 100, 90, "#8A4B23") + bulbs + hand
    def mv(t, d):
        out = stamps("#" + u + "b%d", n, t + .1, d * .8 / n)
        out.append(tw("#%shd" % u, '{y:-120,x:-40,duration:.4,ease:"steps(3)",repeat:%d,yoyo:true}' % max(1, int(d / .4) - 1), t))
        return out
    return art, mv


def scene_icicles(u, ac, txt):
    """One strand laid on one Y-shaped branch; then every branch fills in, row by row."""
    rnd = random.Random(14)
    fills = "".join(g('<path d="M%d %d v%d" stroke="#E9EEF0" stroke-width="6" stroke-linecap="round"/>' % (rnd.randint(120, 960), rnd.randint(860, 1500), rnd.randint(70, 130)), "%sq%d" % (u, i)) for i in range(60))
    art = (wall(NIGHT, "#ffffff14") + r(-120, 840, W + 240, 1700, DEEP, 0) + p("M100 500 L420 620 L640 500 M420 620 L470 780", "none").replace('stroke-width="9"', 'stroke-width="26"').replace(INK, "#5A3A20")
           + g('<path d="M640 500 v150" stroke="#E9EEF0" stroke-width="10" stroke-linecap="round"/>', u + "one") + fills
           + g(c(640, 430, 30, SKIN) + limb("M1160 250 L660 420", CORAL), u + "hd"))
    def mv(t, d):
        out = [tw("#%sone" % u, '{y:-160,opacity:0,duration:.4,ease:"steps(4)"}', t + .3, "from"), tw("#%shd" % u, '{x:320,y:-110,duration:.3,ease:"steps(3)"}', t + .9)]
        out += stamps("#" + u + "q%d", 60, t + 1.0, max(.01, (d - 1.2) / 60), '{opacity:0,y:-30,duration:.1,ease:"steps(1)"}')
        return out
    return art, mv


def scene_one_gift(u, ac, txt):
    rays = "".join('<polygon points="540,1040 %d,%d %d,%d" fill="%s"/>' % (540 + 1300 * math.cos(a), 1040 + 1300 * math.sin(a), 540 + 1300 * math.cos(a + .14), 1040 + 1300 * math.sin(a + .14), "#F2C14E55") for a in [i * math.pi / 6 for i in range(12)])
    box = r(330, 900, 420, 320, RED, 10) + r(500, 900, 80, 320, MUSTARD, 0) + g(r(300, 860, 480, 70, RED, 10) + r(500, 860, 80, 70, MUSTARD, 0) + c(540, 840, 46, MUSTARD), u + "lid")
    art = r(-120, -120, W + 240, H + 700, "#26223F", ink=False) + g(rays, u + "r") + floor("#3A2E55", 1220) + g(r(-120, 0, 240, 340, "#C33B2E", 22) + r(-90, 30, 180, 120, CREAM, 8) + c(0, 240, 70, MUSTARD), u + "rad", "translate(540 640)") + box
    return art, lambda t, d: [tw("#%sr" % u, '{rotation:30,svgOrigin:"540 1040",duration:%.2f,ease:"steps(%d)"}' % (d, int(d * 8)), t),
                              tw("#%slid" % u, '{y:-420,rotation:-24,svgOrigin:"540 880",duration:.35,ease:"back.out(1.6)"}', t + d * .35),
                              tw("#%srad" % u, '{y:420,opacity:0,duration:.4,ease:"back.out(1.6)"}', t + d * .4, "from")]


def scene_radio_years(u, ac, txt):
    """The radio never moves on the nightstand; she grows up around it, three pictures of the same girl."""
    stand = r(620, 1120, 340, 40, "#8A4B23", 6) + p("M660 1160 V1500") + p("M920 1160 V1500") + r(700, 920, 150, 200, RED, 16) + r(720, 940, 110, 70, CREAM, 6) + c(775, 1060, 40, MUSTARD)
    art = (wall(SKY, "#ffffff44") + floor(OLIVE, 1500) + stand + g(girl(u + "a", 340, 1500, .85, RED), u + "g1") + g(girl(u + "b", 340, 1500, 1.15, TEAL), u + "g2") + g(creator(u + "c", 340, 1500, 1.15, MUSTARD), u + "g3"))
    return art, lambda t, d: [tw("#%sg2" % u, "{opacity:0,duration:.01}", t - .01), tw("#%sg3" % u, "{opacity:0,duration:.01}", t - .01), tw("#%sg1" % u, "{opacity:0,duration:.01}", t + d * .35),
                              tw("#%sg2" % u, "{opacity:1,duration:.01}", t + d * .35), tw("#%sg2" % u, "{opacity:0,duration:.01}", t + d * .7), tw("#%sg3" % u, "{opacity:1,duration:.01}", t + d * .7)]


def scene_orange_roll(u, ac, txt):
    art = (wall(RED, "#ffffff1c") + r(-120, 1380, W + 240, 1200, "#8A4B23", 0) + p("M-20 1380 H1100") + r(-20, 240, 1120, 80, "#8A4B23")
           + g(p("M420 310 V800 L300 880 Q250 1020 400 1010 L600 930 V310 Z", CREAM) + r(390, 280, 240, 96, "#fff", 18), u + "st")
           + g(c(0, 0, 76, "#E8872B") + p("M0 -76 Q20 -100 50 -92"), u + "or", "translate(330 960)")
           + g(p("M-50 0 q50 -70 100 0 q-50 76 -100 0 Z", "#9A6A3B"), u + "w1", "translate(430 1000)") + g(p("M-50 0 q50 -70 100 0 q-50 76 -100 0 Z", "#9A6A3B"), u + "w2", "translate(380 1040)"))
    return art, lambda t, d: [tw("#%sst" % u, '{scaleY:1.05,svgOrigin:"500 310",duration:.15,repeat:3,yoyo:true}', t),
                              tw("#%sor" % u, '{x:430,y:340,rotation:540,duration:.9,ease:"bounce.out"}', t + .5),
                              tw("#%sw1" % u, '{x:-260,y:300,rotation:-300,duration:.7,ease:"bounce.out"}', t + .7), tw("#%sw2" % u, '{x:-120,y:280,rotation:300,duration:.7,ease:"bounce.out"}', t + .85)]


def scene_orange_sun(u, ac, txt):
    sun = g(c(0, 0, 300, "#E8872B") + "".join(p("M%d %d q18 12 8 30" % (120 * math.cos(a), 120 * math.sin(a)), thin=True) for a in (0, 1.2, 2.4, 3.6, 4.8)) + p("M0 -300 Q30 -350 80 -340"), u + "sun", "translate(540 1200)")
    rays = "".join('<polygon points="540,900 %d,%d %d,%d" fill="#F2C14E44"/>' % (540 + 1300 * math.cos(a), 900 + 1300 * math.sin(a), 540 + 1300 * math.cos(a + .16), 900 + 1300 * math.sin(a + .16)) for a in [i * math.pi / 7 for i in range(14)])
    art = r(-120, -120, W + 240, H + 700, "#2E4A6B", ink=False) + g(rays, u + "r") + sun + r(-120, 1200, W + 240, 90, "#F6EEDC") + r(-120, 1290, W + 240, 1200, "#8A4B23", 0)
    return art, lambda t, d: [tw("#%ssun" % u, '{y:-500,duration:%.2f,ease:"steps(%d)"}' % (d, int(d * 8)), t), tw("#%sr" % u, '{rotation:16,svgOrigin:"540 900",opacity:.4,duration:%.2f,ease:"steps(%d)"}' % (d, int(d * 8)), t)]


def scene_album(u, ac, txt):
    snap = g(r(190, 420, 700, 860, CREAM, 6) + r(240, 470, 600, 620, SKY, 0, ink=False) + girl(u + "a", 540, 1040, 1.3, RED) + label(540, 1190, "CHRISTMAS 1964", 44, INK, font="Fredoka"), u + "s")
    mirror = g(r(170, 290, 740, 1080, "#8A4B23", 280) + r(210, 330, 660, 1000, "#CDE4E2", 250, ink=False) + creator(u + "b", 540, 1330, 1.5, RED, spots=True), u + "m")
    art = wall(OLIVE) + mirror + snap
    return art, lambda t, d: [tw("#%ss" % u, '{opacity:0,scale:1.12,transformOrigin:"50%% 50%%",duration:.3,ease:"steps(3)"}', t + d * .5)] + blink(u + "b", t, d)


def scene_sofa(u, ac, txt):
    fam = dad(u + "a", 620, 1360, .85) + girl(u + "b", 780, 1380, .75, TEAL) + girl(u + "c", 300, 1380, .75, RED) + creator(u + "d", 150, 1420, .85, RED)
    cam = g(r(-120, -90, 240, 170, INK, 14) + c(0, -6, 62, SILVER) + c(0, -6, 30, NIGHT) + p("M-60 80 L-110 330") + p("M60 80 L110 330") + p("M0 80 V330"), u + "cm", "translate(830 620) scale(.8)")
    art = wall(CORAL) + floor("#8A4B23", 1400) + r(120, 1000, 800, 420, DEEP, 40) + g(creator(u + "k", 460, 1420, .85, RED), u + "her") + fam.replace(creator(u + "d", 150, 1420, .85, RED), "") + r(90, 1300, 860, 130, TEAL, 30) + cam
    return art, lambda t, d: blink(u + "b", t, d) + blink(u + "c", t + .6, d) + [tw("#%sher" % u, '{x:-640,duration:.5,ease:"steps(5)"}', t + d * .5), tw("#%scm" % u, '{y:-16,duration:.25,ease:"steps(2)",repeat:%d,yoyo:true}' % max(1, int(d / .25) - 1), t)]


def scene_puff(u, ac, txt):
    rnd = random.Random(21)
    flakes = "".join(g(c(rnd.randint(60, 1020), rnd.randint(200, 1380), rnd.randint(8, 22), "#FFF3E2", ink=False), "%sz%d" % (u, i)) for i in range(70))
    puff = g(r(-160, -100, 320, 200, PINK, 70) + r(-34, -146, 68, 60, RED, 10), u + "pf", "translate(760 620)")
    art = wall(TEAL) + floor(OLIVE, 1480) + r(120, 200, 840, 1280, "#8A4B23", 12) + r(160, 240, 760, 1200, "#CDE4E2", 8) + creator(u, 520, 1420, 1.4, RED, u + "a", spots=True) + puff + flakes
    def mv(t, d):
        out = blink(u, t, d) + [tw("#%spf" % u, '{x:-200,y:-70,scale:.8,duration:.3,ease:"steps(3)",repeat:3,yoyo:true}', t)]
        out += stamps("#" + u + "z%d", 70, t + 1.1, .012, '{opacity:0,y:-60,duration:.12,ease:"steps(1)"}')
        out.append(tw("#%spf" % u, '{y:100,duration:.3,ease:"steps(3)"}', t + 1.3))
        return out
    return art, mv


def scene_jars(u, ac, txt):
    rnd = random.Random(9)
    rows, cols = [(1, 300), (2, 480), (3, 660), (4, 840), (5, 1020)], [PINK, SKY, CREAM, MUSTARD, "#fff", TEAL]
    jars, n = "", 0
    for cnt, y in rows:
        for k in range(cnt):
            x = 540 + (k - (cnt - 1) / 2) * 180
            jars += g(r(x - 74, y, 148, 160, rnd.choice(cols), 16) + r(x - 60, y - 34, 120, 40, INK, 8), "%sj%d" % (u, n))
            n += 1
    art = wall(RED, "#ffffff1c") + floor("#8A4B23", 1190) + g(jars, u + "all") + g(star(540, 210, 80, MUSTARD, 8, ink=True), u + "st")
    def mv(t, d):
        out = stamps("#" + u + "j%d", n, t + .1, d * .7 / n, '{y:-500,opacity:0,duration:.16,ease:"steps(2)"}')
        out.append(tw("#%sst" % u, '{y:-400,duration:.25,ease:"bounce.out"}', t + d * .75, "from"))
        out.append(tw("#%sall" % u, '{rotation:2.4,svgOrigin:"540 1190",duration:.2,ease:"steps(2)",repeat:%d,yoyo:true}' % max(1, int(d / .2) - 1), t + d * .5))
        return out
    return art, mv


def scene_spot_back(u, ac, txt):
    """Her cheek, close. The spot pales, the calendar flips, the spot comes right back."""
    art = wall(CORAL) + r(-120, 500, W + 240, 760, SKIN, 0) + p("M-20 500 H1100") + p("M-20 1260 H1100") + g(c(380, 880, 110, "#8A5A33"), u + "s")
    cal = g(r(0, 0, 230, 250, CREAM, 6) + r(0, 0, 230, 66, RED, 6) + g(label(115, 200, "DEC", 76, INK), u + "c1") + g(label(115, 200, "JAN", 76, INK), u + "c2") + g(label(115, 200, "FEB", 76, INK), u + "c3"), None, "translate(740 170)")
    art += cal
    def mv(t, d):
        return [tw("#%sc2" % u, "{opacity:0,duration:.01}", t - .01), tw("#%sc3" % u, "{opacity:0,duration:.01}", t - .01),
                tw("#%ss" % u, '{opacity:.15,duration:%.2f,ease:"steps(5)"}' % (d * .4), t + .1),
                tw("#%sc1" % u, "{opacity:0,duration:.01}", t + d * .3), tw("#%sc2" % u, "{opacity:1,duration:.01}", t + d * .3),
                tw("#%sc2" % u, "{opacity:0,duration:.01}", t + d * .55), tw("#%sc3" % u, "{opacity:1,duration:.01}", t + d * .55),
                tw("#%ss" % u, '{opacity:1,scale:1.12,transformOrigin:"50%% 50%%",duration:.14,ease:"steps(2)"}', t + d * .7)]
    return art, mv


def scene_branches(u, ac, txt):
    """The same icicles on the same branches: the same place, every year."""
    arts = ""
    for i, x in enumerate((200, 540, 880)):
        arts += g(r(x - 150, 480, 300, 760, CREAM, 8) + label(x, 560, str(1964 + i * 30), 44, RED) + p("M%d 760 L%d 860 L%d 760 M%d 860 V1100" % (x - 110, x, x + 110, x)).replace('stroke-width="9"', 'stroke-width="18"').replace(INK, "#5A3A20")
                  + '<path d="M%d 770 v110" stroke="%s" stroke-width="9" stroke-linecap="round"/>' % (x + 96, TEAL), "%sc%d" % (u, i))
    art = wall(MUSTARD) + arts
    return art, lambda t, d: stamps("#" + u + "c%d", 3, t + .1, d * .28, '{y:60,opacity:0,duration:.2,ease:"steps(3)"}')


def scene_card_stack(u, ac, txt):
    """Skin as a deck of cards dealt one by one, the same blot in the same corner of each."""
    cards = ""
    for i in range(7):
        cards += g(r(0, 0, 480, 620, "#F2C49B", 14) + c(380, 110, 44, "#8A5A33") + label(240, 560, "DAY %d" % (i * 28 + 1), 48, INK, font="Fredoka"), "%sc%d" % (u, i), "translate(%d %d) rotate(%d)" % (130 + i * 40, 440 + i * 56, -9 + i * 3))
    art = wall(DEEP, "#ffffff18") + cards
    return art, lambda t, d: stamps("#" + u + "c%d", 7, t + .1, d * .85 / 7, '{x:-1000,duration:.2,ease:"steps(3)"}')


def scene_name_card(u, ac, txt):
    """The spot finds its place card and sits down in its usual chair."""
    chair = r(380, 980, 330, 40, "#8A4B23", 8) + r(380, 620, 40, 400, "#8A4B23", 8) + p("M410 1020 V1280") + p("M680 1020 V1280")
    spot = g(c(0, 0, 118, "#8A5A33") + c(-36, -16, 11, INK, ink=False) + c(36, -16, 11, INK, ink=False) + p("M-34 34 Q0 60 34 34") + limb("M-50 100 V200", "#8A5A33") + limb("M50 100 V200", "#8A5A33"), u + "s", "translate(1240 760)")
    art = wall(SKY, "#ffffff44") + floor(CORAL, 1280) + chair + spot + r(250, 240, 580, 240, CREAM, 8) + label(540, 340, "PIGMENT", 70, RED) + label(540, 430, "MEMORY", 70, RED)
    return art, lambda t, d: [tw("#%ss" % u, '{x:-680,y:90,duration:%.2f,ease:"steps(7)"}' % (min(1.6, d * .5)), t + .1), tw("#%ss" % u, '{y:"-=26",duration:.2,ease:"steps(2)",repeat:%d,yoyo:true}' % max(1, int(d / .4)), t + min(1.8, d * .55))]


def scene_sink(u, ac, txt):
    rnd = random.Random(30)
    grit = "".join(g(c(rnd.randint(440, 640), rnd.randint(470, 640), rnd.randint(6, 12), "#C9A470", ink=False), "%sg%d" % (u, i)) for i in range(20))
    hand = g(limb("M1160 1000 L690 650", RED) + c(680, 640, 30, SKIN), u + "h")
    art = wall(SKY, "#ffffff44") + r(-120, 1240, W + 240, 1300, CREAM) + c(480, 590, 260, SKIN) + p("M210 590 C200 240 760 240 750 590 C680 390 280 390 210 590 Z", SILVER) + c(390, 560, 13, INK, ink=False) + c(570, 560, 13, INK, ink=False) + p("M420 720 Q480 760 540 720") + grit + hand + g(tube(180, 1040, .9, ac), u + "tb")
    def mv(t, d):
        out = [tw("#%stb" % u, '{x:-420,duration:.35,ease:"back.out(1.5)"}', t + .1, "from"),
               tw("#%sh" % u, '{x:-46,y:30,duration:.25,ease:"steps(3)",repeat:%d,yoyo:true}' % max(1, int(d / .25) - 1), t)]
        return out + stamps("#" + u + "g%d", 20, t + .4, max(.02, d * .6 / 20), '{opacity:0,duration:.08,ease:"steps(1)"}')
    return art, mv


def scene_botanicals(u, ac, txt):
    """Four plants hang as ornaments and glow down into the skin below."""
    items = [(190, "#E8A52B", "TURMERIC"), (430, "#6F9A3C", "MORINGA"), (670, "#D9B26A", "GINGER"), (900, "#F4E08A", "CHAMOMILE")]
    art = wall(NIGHT, "#ffffff14") + r(-120, 1120, W + 240, 200, "#E3B58B", 0) + p("M-20 1120 H1100") + r(-120, 1320, W + 240, 1400, "#F7D9BC", 0)
    for i, (x, col, name) in enumerate(items):
        art += g('<polygon points="%d,540 %d,1320 %d,1320" fill="%s55"/>' % (x, x - 90, x + 90, col), "%sb%d" % (u, i))
        art += g(p("M%d -20 V400" % x, thin=True) + c(x, 480, 96, col) + r(x - 26, 368, 52, 26, MUSTARD, 4) + label(x, 640, name, 30, CREAM, font="Fredoka"), "%so%d" % (u, i))
    def mv(t, d):
        out = []
        for i in range(4):
            at = t + .1 + i * d * .2
            out += [tw("#%so%d" % (u, i), '{y:-620,duration:.3,ease:"back.out(1.5)"}', at, "from"), ft("#%sb%d" % (u, i), "{opacity:0}", '{opacity:1,duration:.3,ease:"steps(3)"}', at + .3)]
        return out
    return art, mv


def scene_stats(u, ac, txt):
    balls = c(300, 620, 230, RED) + r(260, 366, 80, 40, MUSTARD, 6) + label(300, 650, txt.split("|")[0] if txt and "|" in txt else "85%", 92, CREAM) + c(790, 900, 210, TEAL) + r(750, 666, 80, 40, MUSTARD, 6) + label(790, 930, txt.split("|")[1] if txt and "|" in txt else "91%", 92, CREAM)
    art = wall(MUSTARD) + g(balls, u + "b") + r(120, 1320, 840, 40, "#8A4B23", 6) + g(r(-130, -70, 260, 140, PINK, 60), u + "pf", "translate(300 1250)")
    return art, lambda t, d: [tw("#%sb" % u, '{y:-20,duration:.3,ease:"steps(2)",repeat:%d,yoyo:true}' % max(1, int(d / .3) - 1), t), tw("#%spf" % u, '{y:-500,duration:.5,ease:"steps(5)"}', t + d * .4, "from")]


def scene_strand_now(u, ac, txt):
    """Today: she lays icicles the patient way, with the clock and the spoon beside her."""
    clock = c(0, 0, 110, CREAM) + g(p("M0 0 V-84"), u + "hnd") + label(0, 76, "60", 40, INK, font="Fredoka")
    art = (wall(TEAL) + floor(CORAL, 1460) + tree_shape(760, 300, 560, 1120, DEEP, 4) + creator(u, 330, 1400, 1.15, RED, u + "a", spots=False)
           + g(clock, None, "translate(160 420)") + r(120, 640, 190, 50, SILVER, 20) + r(300, 655, 200, 18, SILVER, 8))
    art += "".join(g('<path d="M%d %d v90" stroke="#E9EEF0" stroke-width="6" stroke-linecap="round"/>' % (560 + i * 40, 700 + (i % 4) * 120), "%sq%d" % (u, i)) for i in range(14))
    return art, lambda t, d: blink(u, t, d) + stamps("#" + u + "q%d", 14, t + .2, d * .8 / 14, '{opacity:0,y:-40,duration:.1,ease:"steps(1)"}') + [
        tw("#%shnd" % u, '{rotation:360,svgOrigin:"0 0",duration:%.2f,ease:"steps(%d)"}' % (d, int(d * 2) or 2), t),
        tw("#%sa" % u, '{rotation:-14,svgOrigin:"56 -250",duration:.4,ease:"steps(2)",repeat:%d,yoyo:true}' % max(1, int(d / .4) - 1), t)]


def scene_rinse(u, ac, txt):
    rnd = random.Random(2)
    drops = "".join(g('<path d="M%d 300 v50" stroke="#7FC4E0" stroke-width="12" stroke-linecap="round"/>' % rnd.randint(470, 610), "%sd%d" % (u, i)) for i in range(16))
    art = wall(SKY, "#ffffff44") + r(-120, 1160, W + 240, 1500, CREAM) + r(420, 200, 240, 60, SILVER, 18) + r(420, 200, 60, 150, SILVER, 18) + drops + creator(u, 540, 1280, 1.2, TEAL)
    return art, lambda t, d: blink(u, t, d) + ['tl.to("#%sd%d",{y:640,opacity:.4,duration:.6,ease:"steps(6)",repeat:%d},%.3f);' % (u, i, max(1, int(d / .6)), t + i * .04) for i in range(16)]


def scene_stocking_drop(u, ac, txt):
    """The offer as a stocking stuffer: tubes fall in, the bow, then the pouch."""
    n = 3
    tubes = "".join(g(tube(330 + i * 200, 560, .75, ac), "%st%d" % (u, i)) for i in range(n))
    art = wall(RED, "#ffffff1c") + floor("#8A4B23", 1540) + p("M260 760 H840 L820 1320 Q700 1520 420 1480 L260 1400 Z", CREAM) + tubes + r(230, 700, 640, 110, "#fff", 18) + g(r(0, 0, 200, 140, INK, 30) + r(70, -14, 60, 34, MUSTARD, 6) + label(100, 92, "POUCH", 34, CREAM, font="Fredoka"), u + "pc", "translate(760 1360)")
    return art, lambda t, d: [tw("#%st%d" % (u, i), '{y:-900,duration:.3,ease:"bounce.out"}', t + .1 + i * d * .22, "from") for i in range(n)] + [tw("#%spc" % u, '{x:500,duration:.35,ease:"back.out(1.6)"}', t + d * .7, "from")]


def scene_tag(u, ac, txt):
    tag = g(p("M0 -560 V-160", thin=True) + '<polygon points="-210,-160 210,-160 240,-90 240,340 -240,340 -240,-90" fill="%s" %s/>' % (CREAM, LINE) + c(0, -100, 24, TEAL) + label(0, 90, "60", 170, RED) + label(0, 210, "DAYS", 80, RED) + label(0, 300, "MONEY BACK", 40, INK, font="Fredoka"), u + "t", "translate(540 700)")
    art = wall(OLIVE) + tag
    return art, lambda t, d: [ft("#%st" % u, '{rotation:-12,svgOrigin:"540 140"}', '{rotation:12,svgOrigin:"540 140",duration:.6,ease:"sine.inOut",repeat:%d,yoyo:true}' % max(1, int(d / .6) - 1), t)]


def scene_print(u, ac, txt):
    """The photo at last: she steps back in the line, the flash, the print falls into the album."""
    pic = (r(160, 280, 760, 900, CREAM, 8) + r(210, 330, 660, 680, SKY, 0, ink=False) + creator(u, 540, 960, .95, RED) + dad(u + "a", 760, 980, .8) + girl(u + "b", 300, 990, .75, TEAL) + label(540, 1120, "CHRISTMAS", 56, RED))
    art = wall(RED, "#ffffff1c") + r(100, 1240, 880, 460, "#8A4B23", 10) + p("M540 1240 V1700") + g(pic, u + "p") + g(star(860, 300, 280, "#fff", 12), u + "fl")
    return art, lambda t, d: blink(u, t, d) + [ft("#%sfl" % u, "{opacity:1}", "{opacity:0,duration:.25}", t + .1), tw("#%sp" % u, '{rotation:-4,svgOrigin:"540 700",y:40,duration:.5,ease:"steps(5)"}', t + d * .5)]


def scene_moon_stocking(u, ac, txt):
    roofs = "".join('<polygon points="%d,1180 %d,1040 %d,1180" fill="%s" %s/>' % (x, x + 90, x + 180, col, LINE) + r(x + 20, 1180, 140, 220, CREAM) for x, col in ((40, RED), (260, TEAL), (480, OLIVE), (700, CORAL), (900, DEEP)))
    art = (wall(NIGHT, "#ffffff14") + c(540, 520, 400, "#F6EEDC", ink=False) + g(p("M440 180 V620 L320 700 Q270 840 420 820 L640 730 V180 Z", RED) + r(410, 140, 260, 90, "#fff", 18), u + "st")
           + r(-120, 1400, W + 240, 1200, "#E8EEF2", ink=False) + roofs + snow(u, 40, 8) + g(label(540, 1560, "IF YOU GREW UP", 70, DEEP) + label(540, 1660, "IN THE 1960s", 70, RED), u + "t"))
    return art, lambda t, d: snow_moves(u, t, d) + [tw("#%sst" % u, '{rotation:5,svgOrigin:"540 140",duration:.5,ease:"sine.inOut",repeat:%d,yoyo:true}' % max(1, int(d / .5) - 1), t)]


def scene_porch_catalog(u, ac, txt):
    art = (r(-120, -120, W + 240, H + 700, "#2E4A6B", ink=False) + snow(u, 26, 13) + r(90, 200, 500, 1100, RED) + r(150, 280, 170, 300, "#F9D66B") + c(520, 760, 22, MUSTARD) + r(-120, 1300, W + 240, 1300, "#E8EEF2", ink=False) + p("M-20 1300 H1100")
           + g(girl(u, 860, 1400, .95, DEEP), u + "post") + g(r(0, 0, 640, 220, RED, 12) + r(20, -26, 600, 28, CREAM, 2) + label(320, 140, "TOY BOOK", 90, MUSTARD), u + "b", "translate(170 1100)"))
    return art, lambda t, d: snow_moves(u, t, d) + [tw("#%sb" % u, '{y:-1400,duration:.3,ease:"power3.in"}', t + .05, "from"), tw("#%spost" % u, '{x:90,rotation:8,svgOrigin:"860 1400",duration:.2,ease:"steps(2)",repeat:3,yoyo:true}', t + .36)]


def scene_rag(u, ac, txt):
    rnd = random.Random(44)
    bits = "".join(g('<polygon points="%d,%d %d,%d %d,%d" fill="#FFF6DF" %s/>' % (x, y, x + 50, y + 16, x + 14, y + 44, THIN), "%sb%d" % (u, i)) for i, (x, y) in enumerate((rnd.randint(120, 940), rnd.randint(420, 1000)) for _ in range(22)))
    kids = girl(u + "a", 180, 1420, .8, RED) + girl(u + "c", 900, 1420, .8, TEAL) + girl(u + "d", 540, 1500, .9, MUSTARD)
    book = g(r(-190, -120, 380, 240, "#FFF6DF", 10) + p("M0 -120 V120") + p("M-150 -60 L-40 -40 M40 -50 L160 -60 M-140 40 L-30 60", thin=True), u + "bk", "translate(250 760)")
    art = wall(OLIVE) + floor(CORAL, 1480) + kids + book + bits
    return art, lambda t, d: [tw("#%sbk" % u, '{keyframes:[{x:290,y:-60,duration:%.2f},{x:580,y:60,duration:%.2f}],ease:"steps(4)"}' % (d * .4, d * .4), t)] + stamps("#" + u + "b%d", 22, t + .2, d * .8 / 22, '{opacity:0,y:-120,duration:.2,ease:"steps(2)"}')


def scene_walnuts(u, ac, txt):
    w = lambda x: p("M%d 1250 q70 -96 140 0 q-70 104 -140 0 Z" % x, "#9A6A3B") + p("M%d 1180 V1320" % (x + 70), thin=True)
    art = wall(RED, "#ffffff1c") + r(-120, 1120, W + 240, 1500, "#8A4B23", 0) + p("M-20 1120 H1100") + g(w(240), u + "a") + g(w(620), u + "b")
    return art, lambda t, d: [tw("#%sa" % u, '{y:-800,rotation:220,svgOrigin:"310 1250",duration:.5,ease:"bounce.out"}', t + .05, "from"), tw("#%sb" % u, '{y:-800,rotation:-260,svgOrigin:"690 1250",duration:.5,ease:"bounce.out"}', t + .25, "from"),
                              tw("#%sb" % u, '{rotation:"+=1080",svgOrigin:"690 1250",duration:%.2f,ease:"power1.out"}' % max(.4, d - .8), t + .8)]


def scene_frost_mirror(u, ac, txt):
    rnd = random.Random(52)
    frost = "".join(g(p("M%d %d l30 -30 l30 30 l-30 30 Z" % (rnd.randint(330, 720), rnd.randint(390, 740)), "#F8FBFD", thin=True), "%sf%d" % (u, i)) for i in range(16))
    art = (wall(TEAL) + c(540, 640, 450, "#8A4B23") + c(540, 640, 410, "#CDE4E2", ink=False) + c(540, 640, 300, SKIN) + p("M226 640 C210 210 870 210 854 640 C770 420 310 420 226 640 Z", SILVER) + c(430, 610, 15, INK, ink=False) + c(650, 610, 15, INK, ink=False) + p("M480 800 Q540 780 600 800") + frost + r(470, 1090, 140, 300, "#8A4B23"))
    return art, lambda t, d: stamps("#" + u + "f%d", 16, t + .2, d * .8 / 16, '{opacity:0,scale:.2,transformOrigin:"50%% 50%%",duration:.2,ease:"steps(2)"}')


def scene_flake_globe(u, ac, txt):
    rnd = random.Random(61)
    flakes = "".join(g('<polygon points="%d,700 %d,712 %d,736" fill="#F7EBDD" %s/>' % (x, x + 26, x + 8, THIN), "%sf%d" % (u, i)) for i, x in enumerate(rnd.randint(330, 700) for _ in range(30)))
    art = wall(SKY, "#ffffff44") + c(540, 640, 420, "#ffffff55") + c(520, 620, 280, SKIN) + c(420, 590, 14, INK, ink=False) + c(620, 590, 14, INK, ink=False) + p("M590 520 l60 -16", "none") + flakes + g(limb("M1180 1100 L700 560", RED) + c(690, 548, 30, SKIN), u + "h")
    return art, lambda t, d: [tw("#%sh" % u, '{y:300,x:-40,duration:%.2f,ease:"steps(6)"}' % d, t)] + ['tl.to("#%sf%d",{y:%d,opacity:.3,duration:%.2f,ease:"steps(7)"},%.3f);' % (u, i, 600, d * .8, t + i * d * .02) for i in range(30)]


def scene_crispy(u, ac, txt):
    rnd = random.Random(70)
    wind = "".join(p("M%d %d q80 -30 160 0 t160 0" % (rnd.randint(-100, 700), rnd.randint(200, 1300)), thin=True) for _ in range(9))
    crumbs = "".join(g(c(620 + (i % 3) * 16, 900, 12, "#B5683A"), "%sc%d" % (u, i)) for i in range(12))
    art = r(-120, -120, W + 240, H + 700, "#7E9BB0", ink=False) + g(wind, u + "w") + r(-120, 1420, W + 240, 1200, "#E8EEF2", ink=False) + creator(u, 520, 1420, 1.25, DEEP) + c(590, 950, 70, "#C78A52") + p("M550 930 l30 30 l-16 30 M600 920 l20 40", thin=True) + crumbs
    return art, lambda t, d: blink(u, t, d) + bob(u, t, d, amt=10) + [tw("#%sw" % u, '{x:-300,duration:%.2f,ease:"steps(%d)"}' % (d, int(d * 6)), t)] + ['tl.to("#%sc%d",{y:520,x:%d,duration:.9,ease:"steps(6)",repeat:%d},%.3f);' % (u, i, -40 - i * 8, max(1, int(d)), t + i * .1) for i in range(12)]


def scene_icing(u, ac, txt):
    rnd = random.Random(80)
    crust = "".join(g('<polygon points="%d,1000 %d,1012 %d,1040" fill="#E8D6BD" %s/>' % (x, x + 44, x + 18, THIN)) for x in range(90, 960, 62))
    art = wall(MUSTARD) + r(-120, 1040, W + 240, 1500, SKIN, 0) + p("M-20 1040 H1100") + crust + g(p("M300 960 Q540 860 780 960 Q700 1010 540 1000 Q380 1010 300 960 Z", "#FFFFFF"), u + "ic") + g(r(-90, -260, 180, 260, CREAM, 18) + r(-50, -320, 100, 66, INK, 8), u + "b", "translate(540 480)")
    return art, lambda t, d: [tw("#%sic" % u, '{y:-420,opacity:0,duration:.4,ease:"steps(4)"}', t + .1, "from"), tw("#%sic" % u, '{x:760,rotation:12,svgOrigin:"540 980",duration:%.2f,ease:"power2.in"}' % max(.5, d * .4), t + d * .5)]


def scene_hail(u, ac, txt):
    rnd = random.Random(90)
    drops = "".join(g(c(rnd.randint(120, 960), 300, 26, "#fff"), "%sd%d" % (u, i)) for i in range(16))
    art = wall(DEEP, "#ffffff18") + '<polygon points="540,640 40,1020 1040,1020" fill="#D7C3A5" %s/>' % LINE + r(90, 1020, 900, 520, "#F2C49B") + label(540, 960, "THE CRUST", 44, INK, font="Fredoka") + label(540, 1250, "YOUR SKIN", 60, "#A5764E") + drops
    return art, lambda t, d: ['tl.fromTo("#%sd%d",{y:-260},{keyframes:[{y:440,duration:.32,ease:"power2.in"},{y:%d,x:%d,duration:.3,ease:"power1.out"}],repeat:%d},%.3f);' % (u, i, 180, (-1) ** i * 160, max(1, int(d / .7)), t + i * .09) for i in range(16)]


def scene_walnut_crack(u, ac, txt):
    rnd = random.Random(101)
    grains = "".join(g(c(rnd.randint(360, 720), rnd.randint(860, 1180), rnd.randint(6, 12), "#C9A470", ink=False), "%sg%d" % (u, i)) for i in range(40))
    art = wall(OLIVE) + g(p("M380 640 q160 -220 320 0 Z", "#9A6A3B"), u + "l") + g(p("M380 640 q160 220 320 0 Z", "#9A6A3B"), u + "r") + grains + g(tube(540, 1310, .9, ac), u + "tb")
    return art, lambda t, d: [tw("#%sl" % u, '{y:-160,x:-90,rotation:-24,svgOrigin:"540 640",duration:.3,ease:"steps(3)"}', t + .4), tw("#%sr" % u, '{y:160,x:90,rotation:24,svgOrigin:"540 640",duration:.3,ease:"steps(3)"}', t + .4)] + stamps("#" + u + "g%d", 40, t + .6, d * .6 / 40, '{opacity:0,y:-300,duration:.2,ease:"steps(2)"}')


def scene_tube_up(u, ac, txt):
    art = (r(-120, -120, W + 240, H + 700, CREAM, ink=False) + star(540, 680, 620, MUSTARD, 24, inner=.9) + creator(u, 360, 1420, 1.45, RED, u + "a") + g(tube(800, 860, 1.55, ac), u + "tb"))
    return art, lambda t, d: blink(u, t, d) + [tw("#%stb" % u, '{y:900,duration:.4,ease:"back.out(1.6)"}', t + .1, "from")]


def scene_smooth(u, ac, txt):
    art = wall(CORAL) + c(500, 690, 340, SKIN) + p("M150 690 C130 240 870 240 850 690 C770 440 230 440 150 690 Z", SILVER) + p("M350 660 q40 -36 80 0 M570 660 q40 -36 80 0") + p("M410 840 Q500 910 590 840") + g(star(790, 640, 60, "#fff", 4), u + "s") + g(limb("M1180 1200 L760 760", RED) + c(750, 750, 34, SKIN), u + "h")
    return art, lambda t, d: [tw("#%sh" % u, '{y:190,x:-50,duration:.8,ease:"sine.inOut",repeat:%d,yoyo:true}' % max(1, int(d / .8) - 1), t), ft("#%ss" % u, '{scale:.2,opacity:0,transformOrigin:"50%% 50%%"}', '{scale:1.3,opacity:1,duration:.3,repeat:%d,yoyo:true}' % max(1, int(d / .3) - 1), t)]


def scene_timer(u, ac, txt):
    tim = g(c(0, 0, 150, CREAM) + g(p("M0 0 V-110"), u + "hnd") + label(0, 100, "60", 54, INK, font="Fredoka"), None, "translate(280 520)")
    days = "".join(r(120 + (k % 7) * 122, 900 + (k // 7) * 112, 104, 96, "#fff", 4) for k in range(14))
    rings = "".join(g('<circle cx="%d" cy="%d" r="48" fill="none" stroke="%s" stroke-width="12"/>' % (172 + d % 7 * 122, 948 + d // 7 * 112, RED), "%sr%d" % (u, i)) for i, d in enumerate((1, 4, 8, 11)))
    art = wall(SKY, "#ffffff44") + tim + r(560, 480, 300, 80, SILVER, 34) + r(850, 505, 190, 28, SILVER, 10) + c(690, 440, 90, "#C9A470") + r(100, 820, 880, 340, CREAM, 8) + r(100, 820, 880, 60, RED, 8) + days + rings
    return art, lambda t, d: [tw("#%shnd" % u, '{rotation:360,svgOrigin:"0 0",duration:%.2f,ease:"steps(%d)"}' % (d, int(d * 3) or 3), t)] + stamps("#" + u + "r%d", 4, t + .3, d * .8 / 4, '{opacity:0,scale:1.6,transformOrigin:"50%% 50%%",duration:.15,ease:"steps(2)"}')


def scene_window_wipe(u, ac, txt):
    """She wipes a circle in the frost; the girl she was grins back beside her reflection."""
    art = (wall(RED, "#ffffff1c") + r(130, 240, 820, 1120, "#8A4B23", 8) + r(170, 280, 740, 1040, "#DDEBF0", 0, ink=False)
           + creator(u + "k", 430, 1200, 1.0, TEAL) + girl(u + "g", 720, 1200, .9, RED) + g('<path d="M170 280 H910 V1320 H170 Z" fill="#F4F9FB"/>', u + "fr"))
    return art, lambda t, d: [tw("#%sfr" % u, '{opacity:0,duration:%.2f,ease:"steps(6)"}' % min(1.5, d * .5), t + .3)] + blink(u + "k", t, d) + blink(u + "g", t + .3, d)


def pane(fill="#CFE6F2"):
    return r(150, 200, 780, 1140, "#8A4B23", 8) + r(190, 240, 700, 1060, fill, 0) + p("M540 240 V1300") + p("M190 770 H890")


def frost_star(x, y, rad, fill="#FDFEFF", txt=None):
    return star(x, y, rad, fill, 12, inner=.5) if txt == "snow" else star(x, y, rad, fill, 5, inner=.45)


def scene_star_tape(u, ac, txt):
    """Frame one: a mitten tapes a paper star to the pane and a sponge dabs frost through it."""
    paper = g('<polygon points="150,0 150,300 450,300 450,0" fill="%s" %s/>' % (CREAM, LINE) + frost_star(300, 150, 110, "#CFE6F2", txt), None, "translate(210 450)")
    dabs = "".join(g(c(420 + 34 * math.cos(i * 1.3) * (i % 3 + 1), 600 + 34 * math.sin(i * 1.3) * (i % 3 + 1), 20, "#FDFEFF", ink=False), "%sd%d" % (u, i)) for i in range(18))
    art = (wall(NIGHT, "#ffffff14") + pane() + g(paper, u + "p") + dabs + g(r(-70, -60, 150, 110, MUSTARD, 30) + limb("M0 50 L120 400", RED), u + "s", "translate(560 640)")
           + g(label(540, 1490, "IF YOU GREW UP", 74, CREAM) + label(540, 1610, "IN THE 1960s", 74, MUSTARD), u + "t"))
    return art, lambda t, d: [tw("#%sp" % u, '{y:-700,duration:.3,ease:"back.out(1.4)"}', t + .05, "from"), tw("#%ss" % u, '{x:-90,y:-50,duration:.2,ease:"steps(2)",repeat:%d,yoyo:true}' % max(1, int(d / .2) - 1), t + .4)] + stamps("#" + u + "d%d", 18, t + .5, (d - .6) / 18, '{opacity:0,duration:.08,ease:"steps(1)"}')


def scene_star_peel(u, ac, txt):
    paper = g('<polygon points="310,500 770,500 770,960 310,960" fill="%s" %s/>' % (CREAM, LINE), u + "p")
    art = wall(NIGHT, "#ffffff14") + pane() + frost_star(540, 730, 190, txt=txt) + paper + g(c(0, 0, 80, "#ffffff66", ink=False), u + "b", "translate(780 1100)")
    return art, lambda t, d: [tw("#%sp" % u, '{rotation:70,svgOrigin:"770 500",opacity:0,duration:.5,ease:"steps(5)"}', t + d * .45), tw("#%sb" % u, '{scale:2.4,opacity:0,transformOrigin:"50%% 50%%",duration:1.2,ease:"steps(6)"}', t + .1)]


def scene_year_cards(u, ac, txt):
    """The same star comes out of the same box, year after year, and the hand holding it ages."""
    yrs = "".join(g(r(250, 300, 580, 180, CREAM, 8) + label(540, 425, str(y), 110, RED), "%sy%d" % (u, i)) for i, y in enumerate((1964, 1979, 1994, 2009, 2026)))
    art = wall(RED, "#ffffff1c") + yrs + r(300, 900, 480, 360, "#B5683A", 8) + label(540, 1100, "XMAS", 90, CREAM) + g('<polygon points="410,560 670,560 670,820 410,820" fill="%s" %s/>' % (CREAM, LINE) + frost_star(540, 690, 100, "#CFE6F2", txt), u + "st") + r(280, 870, 520, 60, "#8A4B23", 8)
    return art, lambda t, d: [tw("#%sst" % u, '{y:300,duration:.4,ease:"steps(4)",repeat:%d,yoyo:true}' % max(1, int(d / .8) - 1), t)] + stamps("#" + u + "y%d", 5, t + .1, d * .8 / 5, '{opacity:0,duration:.05,ease:"steps(1)"}')


def scene_star_spot(u, ac, txt):
    """Her sleeve pushed back: a spot, in the place the star always went."""
    art = wall(CORAL) + r(-120, 560, W + 240, 620, SKIN, 0) + p("M-20 560 H1100") + p("M-20 1180 H1100") + g(r(-300, 500, 620, 740, DEEP, 0), u + "sl") + star(620, 860, 110, "#8A5A33", 5, inner=.5) + c(820, 740, 34, "#8A5A33", ink=False) + c(860, 980, 26, "#8A5A33", ink=False)
    return art, lambda t, d: [tw("#%ssl" % u, '{x:-420,duration:.5,ease:"steps(5)"}', t + .2, "from") if False else tw("#%ssl" % u, '{x:-260,duration:.5,ease:"steps(5)"}', t + .2)]


def scene_aisle(u, ac, txt):
    rnd = random.Random(33)
    shelves = "".join(r(x, y, 70, 110, rnd.choice([PINK, SKY, CREAM, MUSTARD, "#fff"]), 10) for y in (360, 640, 920) for x in range(60, 1020, 96)) + "".join(r(40, y + 110, 1000, 22, "#8A4B23", 4) for y in (360, 640, 920))
    art = wall(SKY, "#ffffff44") + g(star(540, 180, 120, MUSTARD, 12, ink=True), u + "sun") + shelves + floor(OLIVE, 1300) + creator(u, 380, 1480, .95, RED) + r(560, 1230, 280, 190, SILVER, 10) + r(590, 1150, 70, 110, PINK, 10) + r(680, 1130, 70, 130, MUSTARD, 10) + r(760, 1160, 60, 100, SKY, 10)
    return art, lambda t, d: blink(u, t, d) + [tw("#%ssun" % u, '{rotation:60,svgOrigin:"540 180",duration:%.2f,ease:"steps(%d)"}' % (d, int(d * 6) or 2), t)]


def scene_squeegee(u, ac, txt):
    frost = g(r(190, 240, 700, 1060, "#F4F9FB", 0, ink=False), u + "f")
    art = wall(NIGHT, "#ffffff14") + pane() + frost + g(r(-260, -30, 520, 56, INK, 10) + r(-30, -220, 60, 200, RED, 10) + c(0, -240, 34, PINK), u + "sq", "translate(540 300)")
    return art, lambda t, d: [tw("#%ssq" % u, '{y:980,duration:%.2f,ease:"steps(9)"}' % min(1.6, d * .8), t + .1), tw("#%sf" % u, '{scaleY:0,svgOrigin:"540 1300",duration:%.2f,ease:"steps(9)"}' % min(1.6, d * .8), t + .1)]


def scene_taped_star(u, ac, txt):
    """The wiped glass, and the old star still taped up behind it, frost creeping back in its shape."""
    art = wall(NIGHT, "#ffffff14") + r(150, 200, 780, 1140, "#8A4B23", 8) + r(190, 240, 700, 1060, "#CFE6F2", 0) + '<polygon points="340,520 740,520 740,920 340,920" fill="%s" %s/>' % (CREAM, LINE) + star(540, 720, 170, "#CFE6F2", 12 if txt == "snow" else 5, inner=.5 if txt == "snow" else .45, ink=True) + r(310, 500, 120, 40, MUSTARD, 4) + r(650, 500, 120, 40, MUSTARD, 4) + g(frost_star(540, 720, 150, txt=txt), u + "s") + p("M540 240 V1300", thin=True) + p("M190 770 H890", thin=True)
    return art, lambda t, d: [tw("#%ss" % u, '{opacity:0,scale:.2,transformOrigin:"50%% 50%%",duration:%.2f,ease:"steps(7)"}' % (d * .7), t + .2, "from")]


def scene_day_ring(u, ac, txt):
    ticks = "".join(p("M%d %d L%d %d" % (540 + 300 * math.cos(a), 640 + 300 * math.sin(a), 540 + 340 * math.cos(a), 640 + 340 * math.sin(a)), thin=True) for a in [i * math.pi / 14 for i in range(28)])
    art = wall(TEAL) + c(540, 640, 360, CREAM) + ticks + label(540, 620, "28", 150, RED) + label(540, 760, "TO 40 DAYS", 56, INK, font="Fredoka") + g(p("M540 640 V330").replace('stroke-width="9"', 'stroke-width="16"'), u + "h") + r(-120, 1120, W + 240, 420, SKIN, 0) + p("M-20 1120 H1100") + p("M-20 1540 H1100")
    return art, lambda t, d: [tw("#%sh" % u, '{rotation:720,svgOrigin:"540 640",duration:%.2f,ease:"steps(%d)"}' % (d, int(d * 8)), t)]


def scene_star_returns(u, ac, txt):
    """A fresh coat of frost; the same star comes through; cut to the same spot on her hand."""
    art = wall(NIGHT, "#ffffff14") + pane("#F4F9FB") + g(star(540, 560, 170, "#CFE6F2", 12 if txt == "snow" else 5, inner=.5 if txt == "snow" else .45, ink=True), u + "s") + r(-120, 1100, W + 240, 500, SKIN, 0) + p("M-20 1100 H1100") + g(star(540, 1320, 90, "#8A5A33", 5, inner=.5), u + "m")
    return art, lambda t, d: [tw("#%ss" % u, '{opacity:0,duration:%.2f,ease:"steps(6)"}' % (d * .4), t + .1, "from"), tw("#%sm" % u, '{opacity:0,scale:1.7,transformOrigin:"50%% 50%%",duration:.2,ease:"steps(2)"}', t + d * .55, "from")]


def scene_memory_card(u, ac, txt):
    art = wall(NIGHT, "#ffffff14") + pane("#F4F9FB") + star(540, 760, 240, "#E3ECF2", 5, inner=.45) + r(190, 620, 700, 280, CREAM, 8) + label(540, 740, "PIGMENT", 92, RED) + label(540, 850, "MEMORY", 92, RED)
    return art, lambda t, d: [tw("#%ss" % u, "{opacity:1,duration:.01}", t)]


def scene_child_sponge(u, ac, txt):
    art = wall(OLIVE) + pane("#F4F9FB") + g(r(-90, -60, 180, 120, MUSTARD, 34) + limb("M60 40 L420 500", CORAL), u + "s", "translate(520 700)")
    return art, lambda t, d: [tw("#%ss" % u, '{keyframes:[{x:60,y:-50,duration:.15},{x:0,y:-90,duration:.15},{x:-60,y:-50,duration:.15},{x:0,y:0,duration:.15}],ease:"none",repeat:%d}' % max(1, int(d / .6)), t)]


def scene_milan_door(u, ac, txt):
    """Three little herb figures peel the old star off and tape a new snowflake up."""
    fig = lambda x, col: g(c(x, 1040, 62, col) + p("M%d 980 q-30 -50 0 -80 q30 30 0 80" % x, OLIVE) + limb("M%d 1100 V1200" % (x - 26), col) + limb("M%d 1100 V1200" % (x + 26), col))
    art = wall(NIGHT, "#ffffff14") + pane() + g('<polygon points="360,440 720,440 720,800 360,800" fill="%s" %s/>' % (CREAM, LINE) + star(540, 620, 130, "#CFE6F2", 5, inner=.45, ink=True), u + "o") + g('<polygon points="360,440 720,440 720,800 360,800" fill="%s" %s/>' % ("#fff", LINE) + star(540, 620, 130, "#BFD9EA", 12, inner=.5, ink=True), u + "n") + g(fig(300, "#E8A52B"), u + "a") + g(fig(540, "#6F9A3C"), u + "b") + g(fig(780, "#D9B26A"), u + "c")
    return art, lambda t, d: [tw("#%sn" % u, '{opacity:0,y:-200,duration:.4,ease:"steps(4)"}', t + d * .55, "from"), tw("#%so" % u, '{rotation:-40,y:900,x:-500,duration:.6,ease:"steps(6)"}', t + d * .2)] + [tw("#%s%s" % (u, x), '{y:-30,duration:.2,ease:"steps(2)",repeat:%d,yoyo:true}' % max(1, int(d / .2) - 1), t + i * .1) for i, x in enumerate("abc")]


def scene_frost_soften(u, ac, txt):
    art = wall(NIGHT, "#ffffff14") + pane("#E3F0F6") + g(frost_star(540, 620, 200, txt=txt), u + "s") + r(-120, 1120, W + 240, 420, SKIN, 0) + p("M-20 1120 H1100") + g(c(540, 1320, 62, "#8A5A33", ink=False), u + "m") + g(limb("M1180 1500 L760 1330", RED) + c(750, 1326, 30, SKIN), u + "h")
    return art, lambda t, d: [tw("#%ss" % u, '{opacity:.25,scale:.86,transformOrigin:"50%% 50%%",duration:%.2f,ease:"steps(7)"}' % d, t), tw("#%sm" % u, '{opacity:.3,scale:.8,transformOrigin:"50%% 50%%",duration:%.2f,ease:"steps(7)"}' % d, t), tw("#%sh" % u, '{x:-30,duration:.5,ease:"sine.inOut",repeat:%d,yoyo:true}' % max(1, int(d / .5) - 1), t)]


def scene_hundred(u, ac, txt):
    """A street of a hundred windows; eighty-seven stars soften."""
    cells = ""
    for i in range(100):
        x, y = 90 + (i % 10) * 92, 360 + (i // 10) * 106
        cells += r(x, y, 74, 88, "#F9D66B", 4) + g(star(x + 37, y + 44, 30, "#8A5A33", 5, inner=.5), "%ss%d" % (u, i) if i < 87 else None)
    art = r(-120, -120, W + 240, H + 700, "#2E4A6B", ink=False) + cells + label(540, 280, "87 OF EVERY 100", 66, MUSTARD)
    return art, lambda t, d: ['tl.to("#%ss%d",{opacity:.15,duration:.2,ease:"steps(2)"},%.3f);' % (u, i, t + .2 + i * d * .75 / 87) for i in range(87)]


def scene_two_tubes(u, ac, txt):
    art = wall(RED, "#ffffff1c") + floor("#8A4B23", 1380) + tree_shape(760, 240, 560, 1120, DEEP, 4) + g(tube(300, 1090, 1.1, "body"), u + "a") + g(r(-90, -220, 180, 26, "#1E3A6E", 4) + '<polygon points="-90,-196 90,-196 70,190 -70,190" fill="#1E3A6E" %s/>' % LINE + r(-72, 190, 144, 70, "#1E3A6E", 8) + label(0, -14, "brand_b", 27, CREAM, font="Playfair Display") + label(0, 54, "BODY CREAM", 22, CREAM, font="Fredoka"), u + "b", "translate(520 1110) scale(1.1)")
    return art, lambda t, d: [tw("#%sa" % u, '{y:-900,duration:.35,ease:"bounce.out"}', t + .1, "from"), tw("#%sb" % u, '{y:-900,duration:.35,ease:"bounce.out"}', t + .45, "from")]


def scene_new_stencil(u, ac, txt):
    art = wall(RED, "#ffffff1c") + floor("#8A4B23", 1500) + pane() + g(star(540, 620, 200, "#FDFEFF", 12, inner=.5, ink=True), u + "s") + creator(u, 300, 1500, .95, TEAL, u + "a") + girl(u + "b", 720, 1520, .75, RED)
    return art, lambda t, d: blink(u, t, d) + blink(u + "b", t + .5, d) + [tw("#%ss" % u, '{opacity:0,scale:.3,transformOrigin:"50%% 50%%",duration:.5,ease:"back.out(1.6)"}', t + .3, "from")]


def scene_two_jobs(u, ac, txt):
    """Two jobs, shown as two numbered cards: wipe the glass, change the stencil."""
    art = (wall(TEAL) + g(r(70, 300, 440, 620, CREAM, 10) + label(290, 400, "1", 90, RED) + pane_small(130, 440) + g(r(0, 0, 150, 60, MUSTARD, 20), u + "w", "translate(210 620)"), u + "a")
           + g(r(570, 300, 440, 620, CREAM, 10) + label(790, 400, "2", 90, RED) + pane_small(630, 440) + star(790, 640, 90, "#BFD9EA", 12, inner=.5, ink=True), u + "b") + g(tube(540, 1220, .9, ac), u + "t"))
    return art, lambda t, d: [tw("#%sa" % u, '{x:-700,duration:.3,ease:"back.out(1.4)"}', t + .05, "from"), tw("#%sb" % u, '{x:700,duration:.3,ease:"back.out(1.4)"}', t + d * .4, "from"), tw("#%sw" % u, '{x:60,duration:.2,ease:"steps(2)",repeat:%d,yoyo:true}' % max(1, int(d / .2) - 1), t + .3), tw("#%st" % u, '{y:600,duration:.3,ease:"back.out(1.5)"}', t + .1, "from")]


def pane_small(x, y):
    return r(x, y, 320, 400, "#CFE6F2", 4) + p("M%d %d V%d" % (x + 160, y, y + 400), thin=True)


def scene_salt_melt(u, ac, txt):
    """Grains under her hand, shrinking to nothing like snow on a warm pane."""
    rnd = random.Random(77)
    grains = "".join(g(c(rnd.randint(220, 860), rnd.randint(640, 1000), rnd.randint(14, 26), "#E7D2B3"), "%sg%d" % (u, i)) for i in range(26))
    art = wall(CORAL) + r(-120, 560, W + 240, 520, "#EDBE93", 0) + p("M-20 560 H1100") + p("M-20 1080 H1100") + grains + g(limb("M1180 460 L720 780", SKIN) + c(700, 800, 80, SKIN), u + "h")
    return art, lambda t, d: [tw("#%sh" % u, '{x:-120,y:60,duration:.4,ease:"sine.inOut",repeat:%d,yoyo:true}' % max(1, int(d / .4) - 1), t)] + ['tl.to("#%sg%d",{scale:0,transformOrigin:"50%% 50%%",duration:.3,ease:"steps(3)"},%.3f);' % (u, i, t + .15 + i * d * .75 / 26) for i in range(26)]


def scene_cream_on(u, ac, txt):
    """The cream smoothed along, and this time it stays."""
    art = wall(RED, "#ffffff1c") + r(-120, 700, W + 240, 500, "#F2C49B", 0) + p("M-20 700 H1100") + p("M-20 1200 H1100") + g(r(120, 860, 840, 180, "#FFFFFF", 90, ink=False), u + "c") + g(limb("M1180 620 L900 900", SKIN) + c(880, 920, 80, SKIN), u + "h") + g(r(-90, -220, 180, 26, "#1E3A6E", 4) + '<polygon points="-90,-196 90,-196 70,190 -70,190" fill="#1E3A6E" %s/>' % LINE + r(-72, 190, 144, 70, "#1E3A6E", 8) + label(0, -14, "brand_b", 27, CREAM, font="Playfair Display") + label(0, 54, "BODY CREAM", 22, CREAM, font="Fredoka"), None, "translate(200 430) scale(.8)")
    if txt == "face":
        art = art.replace("BODY CREAM", "MOISTURIZER").replace('fill="#1E3A6E"', 'fill="#E7EEF3"').replace('"%s"' % CREAM, '"%s"' % INK)
    return art, lambda t, d: [tw("#%sc" % u, '{scaleX:0,svgOrigin:"960 950",duration:%.2f,ease:"steps(8)"}' % max(.6, d * .6), t + .1, "from"), tw("#%sh" % u, '{x:-680,duration:%.2f,ease:"steps(8)"}' % max(.6, d * .6), t + .1)]


def scene_long_pants(u, ac, txt):
    art = (wall(OLIVE) + floor("#8A4B23", 1500) + r(120, 200, 300, 900, "#8A4B23", 8) + r(160, 240, 220, 400, "#F3F7FA", 0) + snow(u, 16, 19)
           + creator(u + "k", 600, 1330, 1.0, MUSTARD) + '<polygon points="510,1290 690,1290 730,1500 620,1500 600,1360 580,1500 470,1500" fill="%s" %s/>' % (DEEP, LINE))
    return art, lambda t, d: blink(u + "k", t, d) + snow_moves(u, t, d)


def scene_lotion_shine(u, ac, txt):
    """Lotion shines on the shin, it soaks in, and the dry cracks come straight back."""
    rnd = random.Random(23)
    cracks = "".join(p("M%d %d l40 26 l-16 34 l44 22" % (rnd.randint(120, 860), rnd.randint(640, 1000)), thin=True) for _ in range(14))
    art = wall(MUSTARD) + r(-120, 560, W + 240, 560, "#E3B58B", 0) + p("M-20 560 H1100") + p("M-20 1120 H1100") + g(cracks, u + "c") + g(r(90, 640, 900, 380, "#FFF4E6", 120, ink=False), u + "s")
    return art, lambda t, d: [ft("#%ss" % u, "{opacity:.95}", '{opacity:0,duration:%.2f,ease:"steps(7)"}' % (d * .55), t + d * .3), ft("#%sc" % u, "{opacity:0}", '{opacity:1,duration:.3,ease:"steps(3)"}', t + d * .75)]


def scene_spa(u, ac, txt):
    art = (wall(TEAL) + r(-120, 1200, W + 240, 1300, "#F7EFE3", 0) + p("M-20 1200 H1100") + r(150, 960, 780, 240, CREAM, 20) + r(190, 880, 700, 90, PINK, 20) + r(250, 800, 580, 90, SKY, 20)
           + r(760, 1080, 90, 120, "#fff", 8) + c(805, 1060, 12, MUSTARD) + creator(u, 320, 1200, .7, CORAL)
           + "".join(g(p("M%d 560 q-30 -50 0 -100 q30 -50 0 -100" % x, "none"), "%ss%d" % (u, i)) for i, x in enumerate((520, 640, 760))))
    return art, lambda t, d: blink(u, t, d) + ['tl.fromTo("#%ss%d",{opacity:0,y:50},{opacity:1,y:-90,duration:1.5,ease:"steps(8)",repeat:%d},%.3f);' % (u, i, max(1, int(d / 1.5)), t + i * .4) for i in range(3)]


def scene_drawer(u, ac, txt):
    art = (wall(CORAL) + r(200, 700, 680, 760, "#8A4B23", 12) + g(r(250, 760, 580, 260, "#A8642F", 10) + c(540, 880, 26, MUSTARD) + r(330, 640, 240, 130, PINK, 56), u + "d")
           + r(250, 1090, 580, 300, "#A8642F", 10) + c(540, 1240, 26, MUSTARD))
    return art, lambda t, d: [ft("#%sd" % u, '{y:-110,scale:1.1,transformOrigin:"50%% 50%%"}', '{y:0,scale:1,transformOrigin:"50%% 50%%",duration:.35,ease:"steps(4)"}', t + d * .35)]


def scene_tree_tubes(u, ac, txt):
    tubes = "".join(g(tube(270 + i * 170, 1190, .78, ac), "%st%d" % (u, i)) for i in range(3))
    art = wall(RED, "#ffffff1c") + floor("#8A4B23", 1400) + tree_shape(540, 200, 760, 1150, DEEP, 5) + star(540, 190, 70, MUSTARD, 8, ink=True) + tubes
    return art, lambda t, d: [tw("#%st%d" % (u, i), '{y:-1100,duration:.3,ease:"bounce.out"}', t + .1 + i * d * .25, "from") for i in range(3)]


def scene_tree_lights(u, ac, txt):
    bulbs = "".join(g(c(240 + (i % 7) * 100, 360 + (i // 7) * 170, 26, [RED, MUSTARD, "#49C07B", "#4E86F0"][i % 4]) + c(240 + (i % 7) * 100, 360 + (i // 7) * 170, 54, [RED, MUSTARD, "#49C07B", "#4E86F0"][i % 4] + "44", ink=False), "%sb%d" % (u, i)) for i in range(35))
    art = wall(NIGHT, "#ffffff14") + r(150, 200, 780, 1140, "#8A4B23", 8) + r(190, 240, 700, 1060, "#1D2B4F", 0) + bulbs + g(r(190, 240, 700, 1060, "#F4F9FB", 0, ink=False), u + "fr") + p("M540 240 V1300") + p("M190 770 H890")
    return art, lambda t, d: [tw("#%sfr" % u, '{opacity:0,duration:%.2f,ease:"steps(7)"}' % (d * .7), t + .1)]


CHRISTMAS = {"two_jobs": scene_two_jobs, "salt_melt": scene_salt_melt, "cream_on": scene_cream_on, "long_pants": scene_long_pants, "lotion_shine": scene_lotion_shine, "spa": scene_spa, "drawer": scene_drawer, "tree_tubes": scene_tree_tubes, "tree_lights": scene_tree_lights,
             "star_tape": scene_star_tape, "star_peel": scene_star_peel, "year_cards": scene_year_cards, "star_spot": scene_star_spot, "aisle": scene_aisle, "squeegee": scene_squeegee, "taped_star": scene_taped_star, "day_ring": scene_day_ring, "star_returns": scene_star_returns, "memory_card": scene_memory_card, "child_sponge": scene_child_sponge, "milan_door": scene_milan_door, "frost_soften": scene_frost_soften, "hundred": scene_hundred, "two_tubes": scene_two_tubes, "new_stencil": scene_new_stencil,
             "moon_stocking": scene_moon_stocking, "porch_catalog": scene_porch_catalog, "rag": scene_rag, "walnuts": scene_walnuts, "frost_mirror": scene_frost_mirror, "flake_globe": scene_flake_globe, "crispy": scene_crispy, "icing": scene_icing, "hail": scene_hail, "walnut_crack": scene_walnut_crack, "tube_up": scene_tube_up, "smooth": scene_smooth, "timer": scene_timer, "window_wipe": scene_window_wipe,
             "ornament": scene_ornament, "catalog_thump": scene_catalog_thump, "crayon": scene_crayon, "once": scene_once, "out_of_luck": scene_out_of_luck,
             "lights": scene_lights, "icicles": scene_icicles, "one_gift": scene_one_gift, "radio_years": scene_radio_years, "orange_roll": scene_orange_roll,
             "orange_sun": scene_orange_sun, "album": scene_album, "sofa": scene_sofa, "puff": scene_puff, "jars": scene_jars, "spot_back": scene_spot_back,
             "branches": scene_branches, "card_stack": scene_card_stack, "name_card": scene_name_card, "sink": scene_sink, "botanicals": scene_botanicals,
             "stats": scene_stats, "strand_now": scene_strand_now, "rinse": scene_rinse, "stocking_drop": scene_stocking_drop, "tag": scene_tag, "print": scene_print}


SCENES = {"title": scene_title, "catalog": scene_catalog, "tv": scene_tv, "stocking": scene_stocking, "tinsel": scene_tinsel,
          "aluminum": scene_aluminum, "bubble": scene_bubble, "drive": scene_drive, "window": scene_window, "gift": scene_gift,
          "angel": scene_angel, "canes": scene_canes, "lot_empty": scene_lot_empty, "tablet": scene_tablet, "face": scene_face, "portrait": scene_portrait, "covered": scene_covered, "spots": scene_spots, "dry": scene_dry, "shelf": scene_shelf, "layers": scene_layers, "scrub": scene_scrub, "glad": scene_glad, "pack": scene_pack, "slinky": scene_slinky, "cards": scene_cards, "lot": scene_lot, "end": scene_end}


SCENES.update(CHRISTMAS)


# ------------------------------------------------------------------ the page
def defs():
    """Three wobbles of the ink, swapped on twos so the whole drawing boils."""
    out = ""
    for i, seed in enumerate((3, 11, 23)):
        out += ('<filter id="boil%d" x="-5%%" y="-5%%" width="110%%" height="110%%"><feTurbulence type="fractalNoise" baseFrequency=".018" '
                'numOctaves="2" seed="%d"/><feDisplacementMap in="SourceGraphic" scale="9"/></filter>' % (i, seed))
    return '<svg width="0" height="0" style="position:absolute"><defs>%s</defs></svg>' % out


FONTS = "https://fonts.googleapis.com/css2?family=Chango&family=Fredoka:wght@600&family=Playfair+Display:wght@700&display=block"


def page_doc(body, js, dur):
    return """<!doctype html>
<html><head><meta charset="utf-8"><link rel="stylesheet" href="%s"><script src="%s"></script><style>
*{margin:0;padding:0;box-sizing:border-box}html,body{width:%dpx;height:%dpx;background:#000;overflow:hidden}
#root{position:relative;width:%dpx;height:%dpx;overflow:hidden;background:#F4E6C8}
.art{position:absolute;inset:0}.art svg{display:block}
.num{position:absolute;left:44px;top:150px;width:170px;height:170px;border-radius:50%%;background:%s;border:9px solid %s;color:%s;font-family:Chango;font-size:90px;display:flex;align-items:center;justify-content:center}
.cap{position:absolute;left:50px;right:50px;top:1560px;text-align:center;font-family:Fredoka,sans-serif;font-size:82px;line-height:1.08;color:#fff;-webkit-text-stroke:0;paint-order:stroke;text-shadow:0 5px 0 #2A1B12,4px 0 0 #2A1B12,-4px 0 0 #2A1B12,0 -4px 0 #2A1B12,4px 4px 0 #2A1B12,-4px 4px 0 #2A1B12}
.packshot{position:absolute;left:0;right:0;top:0;height:1920px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}.packshot img{height:640px;max-width:1000px;object-fit:contain}
.offer{font-family:Chango;font-size:54px;line-height:1.2;color:#C33B2E;margin:10px 60px 0}
.sm{position:absolute;left:0;right:0;top:1775px;text-align:center;font-family:Fredoka,sans-serif;font-size:32px;color:#fff;text-shadow:0 2px 0 #2A1B12}
.grain{position:absolute;inset:0;background:#E9C98A;mix-blend-mode:multiply;opacity:.16}
</style></head><body>%s
<div id="root" data-composition-id="main" data-start="0" data-duration="%.2f" data-width="%d" data-height="%d">
%s
<div id="grain" class="clip grain" data-start="0" data-duration="%.2f" data-track-index="40"></div>
</div>
<script>window.__timelines=window.__timelines||{};const tl=gsap.timeline({paused:true});
%s
tl.set({}, {}, %.2f);
window.__timelines["main"]=tl;</script></body></html>
""" % (FONTS, GSAP, W, H, W, H, MUSTARD, INK, INK, defs(), dur, W, H, "\n".join(body), dur, "\n".join(js), dur)


def art_clip(uid, name, t, d, ad, n=None):
    art, moves = SCENES[name](uid, ad.get("tube", "body"), ad.get("brand_card") if name == "end" else ad.get("problem"))
    svg = '<svg id="%ssvg" viewBox="0 0 %d %d" width="%d" height="%d" xmlns="http://www.w3.org/2000/svg"><g id="%sink" filter="url(#boil0)"><g transform="translate(%.1f 0) scale(%s)">%s</g></g></svg>' % (uid, W, H, W, H, uid, W * (1 - ART) / 2, ART, art)
    body = ['<div id="%s" class="clip art" data-start="%.3f" data-duration="%.3f" data-track-index="10">%s</div>' % (uid, t, d, svg)]
    js = list(moves(t, d))
    k, i = t, 0
    while k < t + d:
        js.append('tl.set("#%sink",{attr:{filter:"url(#boil%d)"}},%.3f);' % (uid, i % 3, k))
        k += TWOS
        i += 1
    if name == "pack":
        body.append('<div id="%sp" class="clip packshot" data-start="%.3f" data-duration="%.3f" data-track-index="20"><img src="assets/pack.png" alt=""><div class="offer">%s</div></div>'
                    % (uid, t, d, html.escape(ad.get("offer_line", ""))))
        js.append('tl.from("#%sp",{y:900,duration:.4,ease:"back.out(1.5)"},%.3f);' % (uid, t))
    if n:
        body.append('<div id="%sn" class="clip num" data-start="%.3f" data-duration="%.3f" data-track-index="20">%s</div>' % (uid, t, d, n))
        js.append('tl.from("#%sn",{scale:0,rotation:-40,duration:.3,ease:"back.out(2.2)"},%.3f);' % (uid, t))
    return body, js


def spoken_words(run):
    """Every word with its time, taken from each read's true start and end. Words share the read by length,
    with the breath at an ellipsis or a comma counted, so a long one-breath line stays in step."""
    if (run / "vo" / "words.json").is_file():   # heard back, word by word: the true clock
        return S.read(run / "vo" / "words.json")
    sheet = S.read(run / "vo" / "timing.json")["scenes"]
    said = S.read(run / "lines.json")
    out = []
    for sid, sc in sheet.items():
        ws = said[sid].split()
        weight = [len(w) + 1 + (9 if w.endswith("...") else 3 if w[-1] in ",.?!" else 0) for w in ws]
        t, span = sc["start"], (sc["end"] - sc["start"]) * .97
        for w, n in zip(ws, weight):
            d = span * n / sum(weight)
            out.append({"w": w, "t": round(t, 3), "e": round(t + d, 3), "sid": sid})
            t += d
    return out


def build(run):
    ad = S.read(run / "ad.json")
    words = spoken_words(run)
    sheet = S.read(run / "vo" / "timing.json")["scenes"]
    dur = round(sheet[list(sheet)[-1]]["end"] + ad.get("tail", 3.0), 2)
    i, beats = 0, []
    for b in ad["beats"]:
        i = S.phrase_at(words, b["at"], i)
        beats.append(dict(b, t=0.0 if not beats else words[i]["t"]))
    for a, b in zip(beats, beats[1:]):
        a["e"] = b["t"]
    beats[-1]["e"] = dur
    body, js = [], []
    for n, b in enumerate(beats):
        a, q = art_clip("b%d" % n, b["scene"], b["t"], b["e"] - b["t"], dict(ad, problem=b.get("arg", ad.get("problem"))), b.get("num"))
        body += a
        js += q
    chunks = S.captions(words, set(), max_chars=20)
    for n, ch in enumerate(chunks):
        st = ch[0]["t"]
        en = min(chunks[n + 1][0]["t"], ch[-1]["e"] + 1.2) if n + 1 < len(chunks) else dur - ad.get("tail", 3.0) + .6
        en = max(en, st + .1)                  # a zero-length clip would never leave the screen
        body.append('<div id="c%d" class="clip cap" data-start="%.3f" data-duration="%.3f" data-track-index="30">%s</div>' % (n, st, en - st, " ".join(html.escape(w["w"]) for w in ch).replace("nineteen sixties", "1960s")))
    for sm in ad.get("small_print", []):
        q = S.phrase_at(words, sm["at"], 0)
        body.append('<div id="sp%d" class="clip sm" data-start="%.3f" data-duration="%.3f" data-track-index="31">%s</div>' % (q, words[q]["t"], min(4.0, dur - words[q]["t"]), html.escape(sm["text"])))
    page = run / "page"
    (page / "assets").mkdir(parents=True, exist_ok=True)
    if ad.get("packshot"):
        shutil.copy2(S.HERE.parents[2] / ad["packshot"], page / "assets" / "pack.png")
    (page / "index.html").write_text(page_doc(body, js, dur))
    (page / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}))
    (run / "beats.json").write_text(json.dumps(beats, indent=1))
    print("page written: %d beats, %.1f s" % (len(beats), dur))
    return dur, beats


def look(run, names):
    """One held frame of each scene, free, before any voice exists."""
    names = names or list(SCENES)
    ad = S.read(run / "ad.json") if (run / "ad.json").is_file() else {}
    body, js = [], []
    for n, name in enumerate(names):
        a, q = art_clip("b%d" % n, name, n * 4.0, 4.0, ad, (n if name not in ("title", "end") else None))
        body += a
        js += q
    page = run / "look-page"
    page.mkdir(parents=True, exist_ok=True)
    dur = len(names) * 4.0
    (page / "index.html").write_text(page_doc(body, js, dur))
    (page / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}}))
    out = run / "look.mp4"
    subprocess.run(["npx", "hyperframes", "render", "--fps", "10", "--output", str(out.resolve())], cwd=str(page), check=True)
    (run / "look").mkdir(exist_ok=True)
    for n, name in enumerate(names):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.1f" % (n * 4.0 + 3.2), "-i", str(out), "-frames:v", "1", str(run / "look" / (name + ".jpg"))], check=True)
    print("look:", run / "look")


# ------------------------------------------------------------------ the sound, made here too
NOTE = {"G4": 392.0, "A4": 440.0, "B4": 493.9, "C5": 523.3, "D5": 587.3, "E5": 659.3, "F#5": 740.0, "G5": 784.0, "A5": 880.0}


def bells(path, dur, tune, beat=.62, rate=22050):
    """A music box playing a public-domain carol, written sample by sample."""
    n = int(dur * rate)
    a = [0.0] * n
    t0, i = 0.4, 0
    while t0 < dur - 1.5:
        name, length = tune[i % len(tune)]
        i += 1
        if name:
            f = NOTE[name]
            s0 = int(t0 * rate)
            for j in range(int(rate * 1.6)):
                if s0 + j >= n:
                    break
                t = j / rate
                a[s0 + j] += (math.sin(2 * math.pi * f * t) + .35 * math.sin(2 * math.pi * f * 3.01 * t)
                              + .15 * math.sin(2 * math.pi * f * 5.4 * t)) * math.exp(-t * 3.2) * .2
        t0 += length * beat
    fade = int(rate * 1.2)
    out = array.array("h", bytes(2 * n))
    for j in range(n):
        env = min(1.0, (n - j) / fade)
        out[j] = int(max(-1, min(1, a[j] * env)) * 32000)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(out.tobytes())


def pace(run, factor):
    """Speed the whole read, pitch held, every time on the voice sheet moved with it. The old track stays beside it."""
    vo = run / "vo"
    shutil.copy2(vo / "track.mp3", vo / "track-before-pace.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(vo / "track-before-pace.mp3"), "-af", "atempo=%s" % factor, "-c:a", "libmp3lame", "-b:a", "192k", str(vo / "track.mp3")], check=True)
    timing = S.read(vo / "timing.json")
    for sc in timing["scenes"].values():
        sc["start"], sc["end"] = round(sc["start"] / factor, 3), round(sc["end"] / factor, 3)
        for ln in sc["lines"]:
            ln["start"], ln["end"] = round(ln["start"] / factor, 3), round(ln["end"] / factor, 3)
    (vo / "timing.json").write_text(json.dumps(timing, indent=1))
    return sc["end"]


def render(run):
    dur, beats = build(run)
    silent = run / "silent.mp4"
    subprocess.run(["npx", "hyperframes", "render", "--fps", str(FPS), "--output", str(silent.resolve())], cwd=str(run / "page"), check=True)
    ad = S.read(run / "ad.json")
    bells(run / "bed.wav", dur, [tuple(x) for x in ad["tune"]])
    final = run / "final.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(run / "vo" / "track.mp3"), "-i", str(run / "bed.wav"),
                    "-filter_complex", "[1]volume=1.0[v];[2]volume=%s[m];[v][m]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[a]" % ad.get("music", "0.32"),
                    "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", "%.2f" % dur, str(final)], check=True)
    print("final:", final)


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("look", "pace", "tighten", "build", "render", "all"):
        raise SystemExit(__doc__)
    run = Path(sys.argv[2]).resolve()
    cmd = sys.argv[1]
    if cmd == "look":
        run.mkdir(parents=True, exist_ok=True)
        look(run, sys.argv[3:])
    if cmd == "pace":
        print("track now %s s" % pace(run, float(sys.argv[3])))
    if cmd == "tighten":
        print("cut %s s of pauses" % S.tighten(run, float(S.read(run / "ad.json").get("tighten", .6))))
    if cmd == "build":
        build(run)
    if cmd in ("render", "all"):
        render(run)


if __name__ == "__main__":
    main()
