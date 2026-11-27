"""Opt-in sections that draw editor's own Figma emails ("2026 Campaigns Designs 2/2", file qDb2jGXrz8RgQQbnFRfcgt).

Added 2026-11-17 for brand_b-nov-33 (editor: brand_b emails follow her Figma, not the AI-made "circled in pen" look).
Every section here is named fg_* and is used ONLY by an email whose email.json asks for it, so nothing drawn
before changes and no other brand sees it. engine.py picks these up with one line at its end.

Everything is written in the Figma's own pixels (600 wide, 32px margins, 536 content) and shrunk to the engine's
400px page by `zoom`, so the numbers below can be read straight off the file:

    header      70px, logo 200x42 centred                                       (node 2035:1133)
    hero        photo, then the words; headline 50px Marlide, line 22px Inter Tight Medium, button 65px
    block       cream section, 50px above and below, 40px between its parts       (nodes 2035:1172, 2038:2166)
    headline    Marlide Display Medium 50px / 1.1, centred, two tones (Dark Brown #422F28 then Gold #B19A6F)
    body        Inter Tight Medium 22px / 1.4, Brown Grey #3A3433, centred, 467px wide
    button      65px tall, 5px corners, Dark Grey #19110E, cream capitals Inter Tight Bold 20px, 1px spacing, arrow
    signal      536 x 181 white card, gold 1px line, 166px square picture 7px in, tag + serif 32 title + 22px line
    closing     Marlide 30px / 1.2 line
    footer      225px, #19110E (live in build.py: it carries the unsubscribe link)

No section here puts a shade, band or gradient on a picture (editor's standing rule).
"""
import base64
import html
import re
from pathlib import Path

E = html.escape
Z = 400.0 / 600.0                      # the engine's page is 400 CSS px wide; the email is 600

DARK, BROWN, GREY, CREAM, GOLD = "#19110E", "#422F28", "#3A3433", "#FBFAF5", "#B19A6F"
SERIF = "'Marlide Display','Georgia',serif"
SANS = "'Inter Tight','Helvetica Neue',Helvetica,Arial,sans-serif"


def _t(x):
    s = E(x or "")
    for tag in ("i", "b", "br"):
        s = s.replace("&lt;%s&gt;" % tag, "<%s>" % tag).replace("&lt;/%s&gt;" % tag, "</%s>" % tag)
    return s


def _wrap(inner, bg, extra=""):
    """One section: 600px of Figma pixels shrunk to the engine's 400."""
    return ('<section class="m m-fg" style="padding:0;margin:0;background:%s;overflow:hidden"><div style="width:600px;zoom:%.6f;%s">%s</div></section>'
            % (bg, Z, extra, inner))


def _light(hexcolor):
    """True when a #rrggbb colour is light enough to need dark words on it."""
    try:
        h = hexcolor.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return (0.299 * r + 0.587 * g + 0.114 * b) > 165
    except (ValueError, AttributeError, IndexError):
        return False


def _asset(lk, ref):
    """A run's own copy of a header/footer asset when it has one (older emails do); else the brand's own logo from its look file and the
    social icons bundled beside this file, so a brand-new run draws the same header and footer (2026-11-19)."""
    try:
        p = lk.path(ref)
        if p and Path(p).is_file():
            return p
    except (ValueError, KeyError, OSError):
        pass
    name = Path(ref.partition(":")[2]).stem
    if name == "logo":
        return lk.path(lk["logo"])
    return Path(__file__).resolve().parent / "social" / (name + ".svg")


def _seal_file(lk, it):
    """The gold seal picture: the item's own file, else the brand look's guarantee seal, else the one bundled beside this file."""
    ref = it.get("file") or (lk.get("guarantee") or {}).get("seal")
    if ref:
        try:
            p = Path(lk.path(ref))
            if p.is_file():
                return p
        except (ValueError, KeyError, OSError):
            pass
    return Path(__file__).resolve().parent / "social" / "seal.png"


def _logo_svg(lk, ref):
    p = _asset(lk, ref)
    return '<img src="data:image/svg+xml;base64,%s" alt="%s" style="display:block;width:200px;height:42px;margin:0 auto">' % \
        (base64.b64encode(Path(p).read_bytes()).decode(), E((lk.get("logo") or {}).get("alt", "")))


def _pic(lk, p, w, h, border=None, r=0):
    """A picture cropped to exactly w x h Figma pixels (at 2x), no shade of any kind."""
    import engine as EN
    ratio = float(w) / float(h)
    if "photo" not in p:    # a picture still to be made (a `todo` slot): a calm placeholder of the same size, so the layout can be checked and drawn before the picture exists
        bd = ("border:1px solid %s;" % border if border else "") + ("border-radius:%dpx;" % r if r else "")
        return ('<div style="box-sizing:border-box;width:%dpx;height:%dpx;%sbackground:#E6DCC8;display:flex;align-items:center;justify-content:center;padding:24px;text-align:center;'
                'font:500 16px/1.3 %s;color:#6B5D52">PICTURE TO MAKE (%d x %d)<br>%s</div>' % (w, h, bd, SANS, w, h, E(str(p.get("todo", "")))[:160]))
    u = EN.photo(lk, p["photo"], ratio, int(w * 2), tuple(p.get("focus", (.5, .5))), p.get("top", 0), p.get("bottom", 0))
    bd = ("border:1px solid %s;" % border if border else "") + ("border-radius:%dpx;" % r if r else "")
    return '<img src="%s" alt="%s" style="display:block;width:%dpx;height:%dpx;%s">' % (u, E(p.get("alt", "")), w, h, bd)


def _button(label, dark=True):
    bg, ink = (DARK, CREAM) if dark else ("#FFFFFF", DARK)
    # editor, 2026-11-20: the email button follows the website's normal button: sentence case, no all-capitals, no arrow. 65px tall, 5px corners;
    # a long label wraps inside the 536px content width instead of running off the edge.
    return ('<div style="text-align:center"><div style="display:inline-flex;align-items:center;justify-content:center;min-height:65px;max-width:536px;padding:12px 32px;box-sizing:border-box;background:%s;border-radius:5px;'
            'font:600 20px/1.2 %s;letter-spacing:0;color:%s;text-align:center">%s</div></div>') % (bg, SANS, ink, E(label))


def _headline(lines, size=50, tone=(BROWN, GOLD), lh=1.1, keep_breaks=False, align="center"):
    """lines: ["First part", "last words"]. The parts run on as one centred, balanced block (a short headline stays on one line),
    the first part in the dark tone and the rest in gold; keep_breaks=True puts each part on its own line as the Figma does."""
    if isinstance(lines, str):
        lines = [lines]
    sep = "<br>" if keep_breaks else " "
    out = sep.join('<span style="color:%s">%s</span>' % (tone[0] if i == 0 or len(tone) == 1 else tone[1], _t(ln)) for i, ln in enumerate(lines))
    return '<div style="font:400 %dpx/%s %s;text-align:%s;letter-spacing:0;text-wrap:balance">%s</div>' % (size, lh, SERIF, align, out)


def _body(text, ink=GREY, w=467):
    return '<div style="width:%dpx;margin:0 auto;font:500 22px/1.4 %s;text-align:center;color:%s">%s</div>' % (w, SANS, ink, _t(text))


def _signals(lk, rows, card_h=230, pad_v=32, sans=False):
    cards = []
    for r in rows:
        tag_bg = r.get("tag_bg", GOLD)
        cards.append(
            '<div style="box-sizing:border-box;width:536px;min-height:%dpx;box-sizing:border-box;background:#fff;border:1px solid %s;border-radius:16px;padding:%dpx 16px %dpx 24px;display:flex;gap:26px;align-items:center;margin:0 auto">'
            '%s'
            '<div style="flex:1;display:flex;flex-direction:column;gap:20px;align-items:flex-start">'
            '%s'
            '<div style="font:%s;color:%s">%s</div>'
            '<div style="font:500 22px/1.2 %s;color:%s">%s</div></div></div>'
            % (card_h, GOLD, pad_v, pad_v, ('<div style="flex:none;width:166px;height:166px">%s</div>' % _pic(lk, r["picture"], 166, 166, None, 12)) if r.get("picture") else "",
               ('<div style="background:%s;padding:8px 10px;font:700 22px/1.2 %s;color:%s;white-space:nowrap">%s</div>' % (tag_bg, SANS, CREAM, _t(r["tag"]))) if r.get("tag") else "", ("700 28px/1.15 " + SANS) if sans else ("400 32px/1.1 " + SERIF), BROWN, _t(r["title"]), SANS, BROWN, _t(r["line"])))
    return '<div style="display:flex;flex-direction:column;gap:20px">%s</div>' % "".join(cards)


def _item(lk, it, ink_dark=True):
    t = it["t"]
    if t == "headline":
        tone = tuple(it.get("tone") or ((BROWN, "#7A4E2D") if ink_dark else (CREAM, CREAM)))    # the second tone on a light ground is deep bronze, never gold (editor, 2026-11-20)
        return _headline(it["lines"], it.get("size", 50), tone, it.get("lh", 1.1), it.get("keep_breaks", False), it.get("align", "center"))
    if t == "body":
        return _body(it["text"], it.get("ink") or (GREY if ink_dark else CREAM), it.get("w", 467))
    if t == "button":
        return _button(it["label"], it.get("dark", True))
    if t == "line":    # the closing serif line
        return '<div style="font:%s 30px/1.2 %s;text-align:center;color:%s">%s</div>' % ("600" if it.get("sans") else "400", SANS if it.get("sans") else SERIF, it.get("ink") or (BROWN if ink_dark else CREAM), _t(it["text"]))
    if t == "picture":
        w = it.get("w", 536)
        return '<div style="width:%dpx;margin:0 auto">%s</div>' % (w, _pic(lk, it["picture"], w, it["h"], it.get("frame"), it.get("r", 16)))
    if t == "pictures":    # two or more side by side, a serif caption under each (Figma "photo_row")
        n = len(it["items"]); gap = it.get("gap", 16); w = it.get("w") or (536 - gap * (n - 1)) // n
        cells = "".join('<div style="width:%dpx">%s%s</div>' % (
            w, _pic(lk, x["picture"], w, it.get("h", w), it.get("frame"), it.get("r", 16)),
            (('<div style="font:400 24px/1.2 %s;text-align:center;color:%s;margin-top:14px">%s</div>' % (SERIF, CREAM if not ink_dark else BROWN, _t(x["caption"]))) if x.get("caption") else "") +
            (('<div style="font:500 %dpx/1.3 %s;text-align:center;color:%s;margin-top:6px">%s</div>' % (it.get("sub_size", 16), SANS, "#E8DFCB" if not ink_dark else GREY, _t(x["sub"]))) if x.get("sub") else ""))
            for x in it["items"])
        return '<div style="display:flex;gap:%dpx;justify-content:center;width:536px;margin:0 auto">%s</div>' % (gap, cells)
    if t == "card":    # a gold-outlined box with one serif line (the guarantee)
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;border:1px solid %s;border-radius:16px;padding:32px 40px;text-align:center;font:400 30px/1.2 %s;color:%s">%s</div>'
                % (GOLD, SERIF, it.get("ink") or (BROWN if ink_dark else CREAM), _t(it["text"])))
    if t == "guarantee":    # the promise made obvious: a white gold-outlined card, a round "60 DAYS" badge, a serif line, the exact words
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:#fff;border:1px solid %s;border-radius:16px;padding:40px 32px 44px;text-align:center">'
                '<div style="width:132px;height:132px;margin:0 auto;border-radius:50%%;border:2px solid %s;display:flex;align-items:center;justify-content:center">'
                '<div style="width:112px;height:112px;border-radius:50%%;border:1px solid %s;display:flex;flex-direction:column;align-items:center;justify-content:center">'
                '<div style="font:400 58px/1 %s;color:%s">%s</div><div style="font:700 15px/1 %s;letter-spacing:3px;color:%s;margin:6px 0 0 3px">%s</div></div></div>'
                '<div style="font:400 40px/1.1 %s;color:%s;margin-top:28px;text-wrap:balance">%s</div>'
                '<div style="font:500 22px/1.4 %s;color:%s;margin-top:16px">%s</div></div>'
                % (GOLD, GOLD, GOLD, SERIF, GOLD, E(it.get("big", "60")), SANS, BROWN, E(it.get("small", "DAYS")),
                   SERIF, BROWN, _t(it["head"]), SANS, GREY, _t(it["text"])))
    if t == "seal":    # the brand's gold filigree frame (made from the crest on the tube) with a figure and a small word inside it
        u = "data:image/png;base64," + base64.b64encode(_seal_file(lk, it).read_bytes()).decode()
        sz = int(it.get("size", 300))
        return ('<div style="position:relative;width:%dpx;height:%dpx;margin:0 auto"><img src="%s" alt="" style="display:block;width:%dpx;height:%dpx">'
                '<div style="position:absolute;left:0;right:0;top:0;bottom:0;display:flex;flex-direction:column;align-items:center;justify-content:center">'
                '<div style="font:400 %dpx/1 %s;color:%s">%s</div><div style="font:700 17px/1 %s;letter-spacing:5px;color:%s;margin:10px 0 0 5px">%s</div></div></div>'
                % (sz, sz, u, sz, sz, int(sz * .30), SERIF, GOLD, E(it.get("big", "60")), SANS, BROWN, E(it.get("small", "DAYS"))))
    if t == "quote":    # customers' words in a gold-outlined rounded box: a gold tag, a big serif line, who said it
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;border:%s;background:%s;border-radius:16px;padding:36px 40px 40px;text-align:center">'
                '<div style="display:inline-block;background:%s;padding:8px 10px;font:700 22px/1.2 %s;color:%s">%s</div>'
                '<div style="font:400 64px/0.6 %s;color:%s;margin-top:34px;height:30px">\u201c</div>'
                '<div style="font:400 38px/1.15 %s;color:%s;text-wrap:balance">%s</div>'
                '<div style="font:700 17px/1 %s;letter-spacing:3px;text-transform:uppercase;color:%s;margin-top:24px">%s</div></div>'
                % ("none" if it.get("plain") else "1px solid " + GOLD, it.get("card_bg", "#FFFFFF") if it.get("plain") else "transparent", GOLD, SANS, CREAM, E(it.get("tag", "In her words")), SERIF, GOLD, SERIF, it.get("ink") or (BROWN if ink_dark else CREAM), _t(it["text"]), SANS, GOLD, E(it.get("who", ""))))
    if t == "pullquote":    # (2026-11-20, editor: the old boxed quote looked outdated) one voice on the open page: no box, no tag; a small bronze quote mark, the words big in the serif, a small round still and the name
        ink = BROWN if ink_dark else CREAM
        sub = "#7A4E2D" if ink_dark else "#E3C892"
        pic = ('<div style="width:84px;height:84px;margin:0 auto 20px;border-radius:50%%;overflow:hidden">%s</div>' % _pic(lk, it["picture"], 84, 84, None, 0)) if it.get("picture") else ""
        return ('<div style="width:%dpx;margin:0 auto;text-align:center">%s<div style="font:400 56px/0.7 %s;color:%s;height:26px">\u201c</div>'
                '<div style="font:400 %dpx/1.15 %s;color:%s;text-wrap:balance;margin-top:10px">%s</div>'
                '<div style="font:700 15px/1 %s;letter-spacing:3px;text-transform:uppercase;color:%s;margin-top:22px">%s</div></div>'
                % (int(it.get("w", 480)), pic, SERIF, sub, int(it.get("size", 40)), SERIF, ink, _t(it["text"]), SANS, sub, E(it.get("who", ""))))
    if t == "voicecards":    # (2026-11-20) a soft filled card per voice, the creator's still on the left, her words and name on the right; no outline, no tag
        out = []
        for i, r in enumerate(it["rows"]):
            bg = r.get("bg") or ("#F4EDDA" if i % 2 == 0 else "#ECEEE2")
            ph = int(r.get("ph", 150))
            pic = ('<div style="flex:none;width:%dpx">%s</div>' % (ph, _pic(lk, r["picture"], ph, int(r.get("h", 190)), None, 14))) if r.get("picture") else ""
            out.append('<div style="box-sizing:border-box;width:536px;background:%s;border-radius:16px;padding:18px;display:flex;gap:20px;align-items:center">%s'
                       '<div style="flex:1;text-align:left"><div style="font:400 26px/1.2 %s;color:%s">%s</div>'
                       '<div style="font:700 14px/1 %s;letter-spacing:3px;text-transform:uppercase;color:#7A4E2D;margin-top:14px">%s</div></div></div>'
                       % (bg, pic, SERIF, BROWN, _t(r["text"]), SANS, E(r.get("who", ""))))
        return '<div style="display:flex;flex-direction:column;gap:14px">%s</div>' % "".join(out)
    if t == "quotegrid":    # (2026-11-20) two columns of soft tinted tiles of different heights, the words in the serif, the name small underneath; no outline, no tag
        tints = ["#F4EDDA", "#ECEEE2", "#EFE4D3", "#F3E3D3"]
        cols = [[], []]
        for i, r in enumerate(it["items"]):
            cols[i % 2].append('<div style="box-sizing:border-box;background:%s;border-radius:16px;padding:24px 22px 22px;text-align:left">'
                               '<div style="font:400 40px/0.6 %s;color:#7A4E2D;height:16px">\u201c</div>'
                               '<div style="font:400 %dpx/1.2 %s;color:%s;margin-top:10px">%s</div>'
                               '<div style="font:700 13px/1 %s;letter-spacing:3px;text-transform:uppercase;color:#7A4E2D;margin-top:16px">%s</div></div>'
                               % (r.get("bg") or tints[i % len(tints)], SERIF, int(r.get("size", 24)), SERIF, BROWN, _t(r["text"]), SANS, E(r.get("who", ""))))
        return '<div style="width:536px;display:flex;gap:12px;align-items:flex-start">%s</div>' % "".join(
            '<div style="flex:1;display:flex;flex-direction:column;gap:12px%s">%s</div>' % (";margin-top:36px" if k else "", "".join(c)) for k, c in enumerate(cols))
    if t == "reviewcard":    # (2026-11-20, editor: bring the website's review card into email) stars, an area tag, a title, the review, then name, age range and Verified buyer when it is literally true
        out = []
        for r in it["rows"]:
            stars = "\u2605" * int(r.get("stars", 5))
            tag = ('<span style="font:600 14px/1 %s;background:#F1E6D2;color:#5C4630;border-radius:999px;padding:7px 12px">%s</span>' % (SANS, E(r["tag"]))) if r.get("tag") else ""
            who = "<b>%s</b>%s" % (E(r.get("who", "")), (", " + E(str(r["age"]))) if r.get("age") else "")
            ver = (' &middot; <span style="color:#3F6B2E;font-weight:600">Verified buyer</span>' if r.get("verified") else "")
            out.append('<div style="box-sizing:border-box;width:536px;background:%s;border:1px solid #E3D8C6;border-radius:16px;padding:26px 28px;text-align:left;display:flex;flex-direction:column;gap:14px">'
                       '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px"><span style="color:#9A6B1F;letter-spacing:3px;font:400 20px/1 %s" aria-label="%d out of 5 stars">%s</span>%s</div>'
                       '%s<div style="font:500 20px/1.5 %s;color:%s">%s</div>'
                       '<div style="font:500 17px/1.4 %s;color:%s;padding-top:14px;border-top:1px solid #EFE7DA">%s%s</div></div>'
                       % (r.get("bg", "#FFFFFF"), SANS, int(r.get("stars", 5)), stars, tag,
                          ('<div style="font:400 28px/1.2 %s;color:%s">%s</div>' % (SERIF, BROWN, _t(r["title"]))) if r.get("title") else "",
                          SANS, GREY, _t(r["text"]), SANS, GREY, who, ver))
        return '<div style="display:flex;flex-direction:column;gap:14px">%s</div>' % "".join(out)
    if t == "pills":    # (2026-11-20) the website's tags: savings pills and area tags (sand fill, brown words) and the dark sale pill
        cells = []
        for r in it["items"]:
            if r.get("kind") == "sale":
                cells.append('<span style="background:%s;color:%s;border-radius:999px;padding:8px 16px;font:600 14px/1 %s;letter-spacing:1.2px;text-transform:uppercase">%s</span>' % (DARK, CREAM, SANS, E(r["text"])))
            else:
                cells.append('<span style="background:#F1E6D2;color:#5C4630;border-radius:999px;padding:7px 14px;font:600 15px/1 %s">%s</span>' % (SANS, E(r["text"])))
        return '<div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center">%s</div>' % "".join(cells)
    if t == "gcard":    # the guarantee in the Figma signal-card style: a small gold seal on the left, tag, serif title and the exact words on the right
        u = "data:image/png;base64," + base64.b64encode(_seal_file(lk, it).read_bytes()).decode()
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:%s;border:1px solid %s;border-radius:16px;padding:36px 32px;display:flex;gap:28px;align-items:center">'
                '<div style="position:relative;flex:none;width:170px;height:170px"><img src="%s" alt="" style="display:block;width:170px;height:170px">'
                '<div style="position:absolute;left:0;right:0;top:0;bottom:0;display:flex;flex-direction:column;align-items:center;justify-content:center">'
                '<div style="font:400 50px/1 %s;color:%s">%s</div><div style="font:700 13px/1 %s;letter-spacing:4px;color:%s;margin:7px 0 0 4px">%s</div></div></div>'
                '<div style="flex:1;display:flex;flex-direction:column;gap:16px;align-items:flex-start;text-align:left">'
                '<div style="background:%s;padding:8px 10px;font:700 22px/1.2 %s;color:%s">%s</div>'
                '<div style="font:400 36px/1.1 %s;color:%s">%s</div>'
                '<div style="font:500 22px/1.3 %s;color:%s">%s</div></div></div>'
                % (it.get("fill", CREAM), GOLD, u, SERIF, GOLD, E(it.get("big", "60")), SANS, BROWN, E(it.get("small", "DAYS")),
                   GOLD, SANS, CREAM, E(it.get("tag", "Our guarantee")), SERIF, BROWN, _t(it["head"]), SANS, GREY, _t(it["text"])))
    if t == "chat":    # customers' words as a text-message thread: white phone card, grey bubbles, a picture bubble, a message bar
        g = "#E9E9EB"
        def bub(txt, size=28, w=None, serif=False):
            return ('<div style="display:inline-block;max-width:%s;background:%s;border-radius:24px;padding:14px 26px;font:%s %dpx/1.25 %s;color:#1C1C1E;text-align:left">%s</div>'
                    % (w or "420px", g, "400" if serif else "400", size, SERIF if serif else SANS, _t(txt)))
        pics = ""
        if it.get("pictures"):
            n = len(it["pictures"]); w = (446 - 6 * (n + 1) - 8 * (n - 1)) // n
            pics = ('<div style="display:inline-block;background:%s;border-radius:26px;padding:6px"><div style="display:flex;gap:8px">%s</div></div>'
                    % (g, "".join('<div>%s</div>' % _pic(lk, p, w, int(w * 1.25), None, 20) for p in it["pictures"])))
        mic = ('<svg width="26" height="32" viewBox="0 0 26 32" fill="none" stroke="#B5B5BA" stroke-width="2.4" stroke-linecap="round"><rect x="8" y="2" width="10" height="17" rx="5"/>'
               '<path d="M3.5 14.5c0 5.5 4 9.5 9.5 9.5s9.5-4 9.5-9.5M13 24v5"/></svg>')
        bar = ('<div style="display:flex;gap:14px;align-items:center;margin-top:34px"><div style="flex:none;width:62px;height:62px;border-radius:50%%;background:#F4F4F6;box-shadow:0 1px 4px rgba(0,0,0,.12);'
               'display:flex;align-items:center;justify-content:center;font:300 44px/1 %s;color:#1C1C1E">+</div>'
               '<div style="flex:1;height:62px;border-radius:31px;background:#F4F4F6;box-shadow:0 1px 4px rgba(0,0,0,.12);display:flex;align-items:center;justify-content:space-between;padding:0 24px 0 26px;font:400 28px/1 %s;color:#B5B5BA">iMessage%s</div></div>'
               % (SANS, SANS, mic))
        parts = ([bub(it["lead"])] if it.get("lead") else []) + [pics] + ["" if not it.get("text") else bub("\u201c%s\u201d" % it["text"], 34, "440px", True)] + ([bub(it["who"])] if it.get("who") else [])
        body = '<div style="display:flex;flex-direction:column;gap:10px;align-items:flex-start">%s</div>' % "".join(parts)
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:#fff;border-radius:28px;padding:36px 28px 32px">%s%s</div>' % (body, bar))
    if t == "marquee":    # a full-width gold strip of spaced capitals (the moment named, nothing promised)
        return '<div style="margin:0 -32px;background:%s;color:%s;text-align:center;padding:18px 32px;font:700 14px/1.5 %s;letter-spacing:3px">%s</div>' % (it.get("bg", GOLD), it.get("ink", DARK), SANS, E(it["text"]))
    if t == "receipt":    # an itemised till receipt (nov-34): a white rounded card, dashed rules, items left, prices right, the saving struck through
        def row(l, r, big=False, strike=False):
            return ('<div style="display:flex;justify-content:space-between;align-items:baseline;gap:20px;font:%s %dpx/1.3 %s;color:%s"><span>%s</span><span%s>%s</span></div>'
                    % ("700" if big else "500", 28 if big else 21, SERIF if big else SANS, BROWN if big else GREY, _t(l), ' style="text-decoration:line-through;color:#9a8f86"' if strike else "", _t(r)))
        rule = '<div style="border-top:2px dashed %s;margin:22px 0"></div>' % GOLD
        rows = "".join('<div style="margin-top:12px">%s</div>' % row(*r) for r in it["items"])
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:#fff;border:1px solid %s;border-radius:16px;padding:40px 36px 36px">'
                '<div style="font:400 34px/1.1 %s;color:%s;text-align:center">%s</div>%s<div style="margin-top:-12px">%s</div>%s%s%s'
                '<div style="margin-top:6px">%s</div><div style="text-align:center;font:700 15px/1 %s;letter-spacing:3px;color:%s;margin-top:28px">%s</div></div>'
                % (GOLD, SERIF, BROWN, _t(it["title"]), rule, rows, rule, row(it["was"][0], it["was"][1], False, True), "",
                   row(it["total"][0], it["total"][1], True), SANS, GOLD, E(it.get("foot", ""))))
    if t == "tag":    # a small gold highlight chip, cream capitals (nov-37)
        return ('<div style="text-align:center"><div style="display:inline-block;background:%s;padding:10px 14px;font:700 17px/1.2 %s;letter-spacing:1.5px;text-transform:uppercase;color:%s">%s</div></div>'
                % (it.get("bg", GOLD), SANS, it.get("ink", CREAM), _t(it["text"])))
    if t == "freecard":    # the free gift shown, not a button: a white gold-outlined card, the gift's picture left, gold capitals tag, serif name and one line right (nov-37)
        w = int(it.get("pic", 168))
        border = "none" if it.get("plain") else "1px solid %s" % GOLD    # (nov-40) opt-in "plain": no gold outline (editor's no-thin-gold-strokes rule)
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:#fff;border:%s;border-radius:16px;padding:%dpx 20px;display:flex;gap:20px;align-items:center">'
                '<div style="flex:none;width:%dpx">%s</div>'
                '<div style="flex:1;text-align:left"><div style="font:700 15px/1.2 %s;letter-spacing:3px;text-transform:uppercase;color:%s">%s</div>'
                '<div style="font:400 36px/1.1 %s;color:%s;margin-top:10px">%s</div>'
                '<div style="font:500 20px/1.3 %s;color:%s;margin-top:10px">%s</div></div></div>'
                % (border, int(it.get("pad", 20)), w, _pic(lk, it["picture"], w, w, None, 12), SANS, it.get("tag_ink", GOLD), E(it["tag"]), SERIF, BROWN, _t(it["head"]), SANS, GREY, _t(it["text"])))
    if t == "stats":    # big-number cards side by side (nov-37): a serif figure with a gold unit, one plain line under it
        n = len(it["items"]); gap = 16; w = (536 - gap * (n - 1)) // n
        def fig(b):
            b = str(b); u = b[-1] if b[-1] in "%x" else ""
            return _t(b[:-1] if u else b) + ('<span style="color:%s;font-size:.62em;margin-left:2px">%s</span>' % (GOLD, u) if u else "")
        cells = "".join('<div style="box-sizing:border-box;width:%dpx;background:#fff;border:1px solid %s;border-radius:16px;padding:28px 18px 26px;text-align:center">'
                        '<div style="font:400 %dpx/1 %s;color:%s">%s</div>'
                        '<div style="font:500 20px/1.3 %s;color:%s;margin-top:14px">%s</div></div>'
                        % (w, GOLD, int(it.get("size", 92)), SERIF, BROWN, fig(x["big"]), SANS, GREY, _t(x["text"])) for x in it["items"])
        return '<div style="display:flex;gap:%dpx;width:536px;margin:0 auto">%s</div>' % (gap, cells)
    if t == "label":    # small gold spaced capitals, centred (nov-37)
        return '<div style="text-align:center;font:700 15px/1.2 %s;letter-spacing:3px;text-transform:uppercase;color:%s">%s</div>' % (SANS, it.get("ink", GOLD), _t(it["text"]))
    if t == "statpanel":    # (nov-37) a tonal picture with a thin cream hairline grid set on it: a small caps label across the top cell, bold figures below, side by side
        h = int(it.get("h", 670)); n = len(it["items"]); line = "1px solid rgba(251,250,245,.85)"; ink = it.get("ink", CREAM)
        cells = "".join('<div style="flex:1;box-sizing:border-box;padding:20px 12px 18px;text-align:center;%s">'
                        '<div style="font:700 %dpx/1 %s;letter-spacing:-1px;color:%s">%s</div>'
                        '<div style="font:500 14px/1.35 %s;letter-spacing:1.6px;text-transform:uppercase;color:%s;margin-top:12px">%s</div></div>'
                        % ("border-left:" + line + ";" if k else "", int(it.get("size", 84)), SANS, ink, _t(x["big"]), SANS, ink, _t(x["text"]))
                        for k, x in enumerate(it["items"]))
        grid = ('<div style="position:absolute;left:24px;right:24px;bottom:%dpx;border:%s;border-radius:16px;overflow:hidden">'
                '<div style="padding:14px 10px;text-align:center;font:700 14px/1.2 %s;letter-spacing:3px;text-transform:uppercase;color:%s;border-bottom:%s">%s</div>'
                '<div style="display:flex">%s</div></div>' % (int(it.get("bottom", 28)), line, SANS, ink, line, _t(it["label"]), cells))
        return '<div style="position:relative;width:536px;margin:0 auto">%s%s</div>' % (_pic(lk, it["picture"], 536, h, None, 16), grid)
    if t == "productcard":    # (nov-37) one product as a whole tappable card: picture left; gold capitals tag, serif name, one line, and a "shop" cue right
        w = int(it.get("pic", 150))
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:#fff;border:1px solid %s;border-radius:16px;padding:14px;display:flex;gap:22px;align-items:center">'
                '<div style="flex:none;width:%dpx">%s</div>'
                '<div style="flex:1;text-align:left"><div style="font:700 14px/1.2 %s;letter-spacing:3px;text-transform:uppercase;color:%s">%s</div>'
                '<div style="font:400 36px/1.1 %s;color:%s;margin-top:8px">%s</div>'
                '<div style="font:500 18px/1.3 %s;color:%s;margin-top:8px">%s</div>'
                '<div style="font:700 15px/1.2 %s;letter-spacing:2px;text-transform:uppercase;color:%s;margin-top:14px;padding-top:12px;border-top:1px solid %s">%s &nbsp;\u2192</div></div></div>'
                % (GOLD, w, _pic(lk, it["picture"], w, w, None, 12), SANS, GOLD, E(it.get("tag", "Start with")), SERIF, BROWN, _t(it["head"]), SANS, GREY, _t(it["text"]), SANS, BROWN, GOLD, E(it.get("cue", "Shop the bundle"))))
    if t == "trio":    # (nov-37) three short text columns with hairline dividers: a gold capitals tag, a serif name, one plain line
        n = len(it["items"])
        cells = "".join('<div style="flex:1;box-sizing:border-box;padding:0 14px;text-align:center;%s">'
                        '<div style="font:700 13px/1.2 %s;letter-spacing:2.4px;text-transform:uppercase;color:%s">%s</div>'
                        '<div style="font:400 30px/1.1 %s;color:%s;margin-top:10px">%s</div>'
                        '<div style="font:500 17px/1.35 %s;color:%s;margin-top:8px">%s</div></div>'
                        % ("border-left:1px solid %s;" % GOLD if k else "", SANS, GOLD if x.get("hot") else "#9a8f86", _t(x["tag"]), SERIF, BROWN, _t(x["head"]), SANS, GREY, _t(x["text"]))
                        for k, x in enumerate(it["items"]))
        return '<div style="display:flex;width:536px;margin:0 auto">%s</div>' % cells
    if t == "benefitcard":    # (nov-37) one product as a stacked card in the hero's palette: texture picture, gold tag, serif name, one line, three line-icon benefits
        glyph = {
            "drop": '<path d="M24 8 C24 8 12 22 12 29 a12 12 0 0 0 24 0 C36 22 24 8 24 8Z"/>',
            "sun": '<circle cx="24" cy="24" r="6.5"/><path d="M24 9v5M24 34v5M9 24h5M34 24h5M13.4 13.4l3.5 3.5M31.1 31.1l3.5 3.5M13.4 34.6l3.5-3.5M31.1 16.9l3.5-3.5"/>',
            "sparkle": '<path d="M20 10 L23 19 L32 22 L23 25 L20 34 L17 25 L8 22 L17 19Z"/><path d="M34 8 L35.5 12 L39.5 13.5 L35.5 15 L34 19 L32.5 15 L28.5 13.5 L32.5 12Z"/>',
            "leaf": '<path d="M12 36 C12 20 22 10 38 10 C38 26 28 36 12 36Z"/><path d="M12 36 L28 20"/>',
            "flower": '<circle cx="24" cy="24" r="4"/><circle cx="24" cy="13" r="5.5"/><circle cx="24" cy="35" r="5.5"/><circle cx="13" cy="24" r="5.5"/><circle cx="35" cy="24" r="5.5"/>',
        }
        def ben(b):
            return ('<div style="flex:1;text-align:center;padding:0 4px"><div style="width:62px;height:62px;border-radius:50%%;border:1.5px solid rgba(251,250,245,.9);margin:0 auto;display:flex;align-items:center;justify-content:center">'
                    '<svg width="34" height="34" viewBox="0 0 48 48" fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">%s</svg></div>'
                    '<div style="font:700 14px/1.2 %s;letter-spacing:1.6px;text-transform:uppercase;color:%s;margin-top:14px">%s</div>'
                    '<div style="font:500 15px/1.35 %s;color:#F1E4D0;margin-top:8px">%s</div></div>'
                    % (CREAM, glyph[b["icon"]], SANS, CREAM, _t(b["title"]), SANS, _t(b["text"])))
        grad = it.get("grad", "linear-gradient(180deg,#E58A2E 0%,#B9531F 42%,#5C2E1E 100%)")
        pic = _pic(lk, it["picture"], 496, int(it.get("h", 372)), None, 12)
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:%s;background-color:#B9531F;border-radius:16px;padding:20px 20px 28px">%s'
                '<div style="text-align:center;margin-top:24px"><div style="font:700 14px/1.2 %s;letter-spacing:3px;text-transform:uppercase;color:%s">%s</div>'
                '<div style="font:400 40px/1.1 %s;color:%s;margin-top:10px">%s</div>'
                '<div style="font:500 18px/1.3 %s;color:#F1E4D0;margin-top:8px">%s</div></div>'
                '<div style="height:1px;background:rgba(251,250,245,.35);margin:24px 0"></div>'
                '<div style="display:flex;gap:8px">%s</div></div>'
                % (grad, pic, SANS, "#F6D9A0", E(it.get("tag", "")), SERIF, CREAM, _t(it["head"]), SANS, _t(it["text"]), "".join(ben(b) for b in it["benefits"])))
    if t == "minicard":    # (nov-37) a small product box in a gradient of the tube's own colour: texture picture left; tag, serif name, one line and three short benefits right
        glyph = {"drop": '<path d="M24 8 C24 8 12 22 12 29 a12 12 0 0 0 24 0 C36 22 24 8 24 8Z"/>',
                 "sun": '<circle cx="24" cy="24" r="6.5"/><path d="M24 9v5M24 34v5M9 24h5M34 24h5M13.4 13.4l3.5 3.5M31.1 31.1l3.5 3.5M13.4 34.6l3.5-3.5M31.1 16.9l3.5-3.5"/>',
                 "sparkle": '<path d="M20 10 L23 19 L32 22 L23 25 L20 34 L17 25 L8 22 L17 19Z"/><path d="M34 8 L35.5 12 L39.5 13.5 L35.5 15 L34 19 L32.5 15 L28.5 13.5 L32.5 12Z"/>',
                 "leaf": '<path d="M12 36 C12 20 22 10 38 10 C38 26 28 36 12 36Z"/><path d="M12 36 L28 20"/>',
                 "flower": '<circle cx="24" cy="24" r="4"/><circle cx="24" cy="13" r="5.5"/><circle cx="24" cy="35" r="5.5"/><circle cx="13" cy="24" r="5.5"/><circle cx="35" cy="24" r="5.5"/>'}
        ink, tag, sub = it.get("ink", CREAM), it.get("tagink", "#F6D9A0"), it.get("sub", "#F1E4D0")
        ring = it.get("ring", "rgba(251,250,245,.9)")
        rows = "".join('<div style="display:flex;align-items:center;gap:12px;margin-top:%dpx"><div style="flex:none;width:30px;height:30px;border-radius:50%%;border:1.5px solid %s;display:flex;align-items:center;justify-content:center">'
                       '<svg width="18" height="18" viewBox="0 0 48 48" fill="none" stroke="%s" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">%s</svg></div>'
                       '<div style="font:600 16px/1.25 %s;color:%s">%s</div></div>' % (int(it.get("row_gap", 15)), ring, ink, glyph[b["icon"]], SANS, ink, _t(b["text"])) for b in it["benefits"])    # (nov-42) opt-in row_gap: tighter benefit lines
        w = int(it.get("pic", 216)); ph = int(it.get("ph", 264))
        c1, c2 = it["colors"]
        import urllib.parse as _up
        _svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='260' height='260'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/>"
                "<feColorMatrix type='saturate' values='0'/></filter><rect width='100%' height='100%' filter='url(#n)' opacity='.7'/></svg>")
        grain = "url(data:image/svg+xml," + _up.quote(_svg, safe="") + ")"
        bg = "%s, radial-gradient(circle at 12%% 8%%, rgba(255,255,255,.38) 0%%, rgba(255,255,255,0) 58%%), linear-gradient(150deg,%s 0%%,%s 100%%)" % (grain, c1, c2)
        if it.get("flat"):    # (2026-11-23, editor: flat colours only unless named) one solid tint, no glow, no grain
            bg = c1
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:%s;border-radius:16px;padding:24px;display:flex;gap:26px;align-items:center;background-blend-mode:overlay,normal,normal">'
                '<div style="flex:none;width:%dpx">%s</div>'
                '<div style="flex:1"><div style="font:700 13px/1.2 %s;letter-spacing:3px;text-transform:uppercase;color:%s">%s</div>'
                '<div style="font:400 38px/1.1 %s;color:%s;margin-top:8px">%s</div>'
                '<div style="font:500 16px/1.3 %s;color:%s;margin-top:6px">%s</div>%s</div></div>'
                % (bg, w, _pic(lk, it["picture"], w, ph, None, 14), SANS, tag, E(it.get("tag", "")), SERIF, ink, _t(it["head"]), SANS, sub, _t(it["text"]), rows))
    if t == "routinepanel":    # (nov-37) a tonal picture with a rounded hairline grid on it, one column per product: name on top, big figures with a plain line each
        h = int(it.get("h", 800)); ink = it.get("ink", CREAM); line = "1px solid rgba(251,250,245,.85)"
        def col(k, c):
            sts = []
            for q, st in enumerate(c["stats"]):
                sts.append('<div style="padding:16px 8px 14px;text-align:center;%s"><div style="font:700 %dpx/1 %s;letter-spacing:-1px;color:%s">%s</div>'
                           '<div style="font:500 15px/1.4 %s;letter-spacing:.2px;color:%s;margin-top:10px">%s</div></div>'
                           % ("border-top:" + line + ";" if q else "", int(st.get("size", 56)), SANS, ink, _t(st["big"]), SANS, ink, _t(st["text"])))
            return ('<div style="flex:1;box-sizing:border-box;display:flex;flex-direction:column;%s"><div style="padding:13px 6px;text-align:center;font:700 12px/1.2 %s;letter-spacing:2.4px;text-transform:uppercase;color:%s;border-bottom:%s">%s</div>'
                    '<div style="flex:1;display:flex;flex-direction:column;justify-content:center">%s</div></div>'
                    % ("border-left:" + line + ";" if k else "", SANS, it.get("tagink", "#FBE3B5"), line, _t(c["name"]), "".join(sts)))
        grid = ('<div style="position:absolute;left:20px;right:20px;bottom:%dpx;border:%s;border-radius:16px;overflow:hidden">'
                '<div style="padding:13px 10px;text-align:center;font:700 13px/1.2 %s;letter-spacing:3px;text-transform:uppercase;color:%s;border-bottom:%s">%s</div>'
                '<div style="display:flex;align-items:stretch">%s</div></div>' % (int(it.get("bottom", 20)), line, SANS, ink, line, _t(it["label"]), "".join(col(k, c) for k, c in enumerate(it["cols"]))))
        return '<div style="position:relative;width:536px;margin:0 auto">%s%s</div>' % (_pic(lk, it["picture"], 536, h, None, 16), grid)
    if t == "divider":    # a thin gold rule (nov-37)
        return '<div style="width:%dpx;margin:0 auto;height:1px;background:%s"></div>' % (int(it.get("w", 536)), it.get("ink", GOLD))
    if t == "small":    # a small plain note under a picture (nov-34)
        return '<div style="width:%dpx;margin:0 auto;font:500 16px/1.4 %s;text-align:center;color:%s;letter-spacing:.3px">%s</div>' % (it.get("w", 480), SANS, it.get("ink", "#7A6F66"), _t(it["text"]))
    if t == "price":    # the sale price big, the old price slashed through beside it (nov-34)
        return ('<div style="text-align:center;display:flex;justify-content:center;align-items:baseline;gap:18px">'
                '<span style="font:400 64px/1 %s;color:%s">%s</span>'
                '<span style="position:relative;font:400 34px/1 %s;color:#9a8f86">%s<span style="position:absolute;left:-6px;right:-6px;top:50%%;border-top:3px solid %s;transform:rotate(-14deg)"></span></span></div>'
                % (SERIF, it.get("ink", BROWN), _t(it["now"]), SERIF, _t(it["was"]), GOLD))    # (nov-44, opt-in) ink: the price colour on a dark section
    if t == "infographic":    # (nov-34) three white cards, each with a drawn skin diagram, a serif title and one plain line, joined by small arrows
        def svg(kind):
            head = '<svg width="166" height="166" viewBox="0 0 166 166" xmlns="http://www.w3.org/2000/svg"><rect width="166" height="166" rx="14" fill="#FBF6EA"/>'
            if kind == "layer":    # the top layer fades, the darker layer under it stays
                body = ('<rect x="18" y="38" width="130" height="28" rx="7" fill="#EFD6B8"/><rect x="18" y="70" width="130" height="62" rx="7" fill="#D3A27A"/>'
                        '<circle cx="46" cy="52" r="3.5" fill="#E1C2A0"/><circle cx="98" cy="54" r="3" fill="#E1C2A0"/><circle cx="130" cy="51" r="3.5" fill="#E1C2A0"/>'
                        '<circle cx="48" cy="100" r="7" fill="#6F4430"/><circle cx="92" cy="108" r="8" fill="#6F4430"/><circle cx="128" cy="98" r="6" fill="#6F4430"/>'
                        '<path d="M83 22 L83 34 M77 29 L83 35 L89 29" stroke="#B19A6F" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
            elif kind == "cycle":    # the 28 to 40 day renewal turns and the spot is printed again
                body = ('<circle cx="83" cy="83" r="50" fill="none" stroke="#E3D6B8" stroke-width="9"/>'
                        '<path d="M83 33 A50 50 0 1 1 33 83" fill="none" stroke="#B19A6F" stroke-width="9" stroke-linecap="round"/>'
                        '<polygon points="22,76 44,76 33,94" fill="#B19A6F"/><circle cx="83" cy="33" r="9" fill="#6F4430"/>'
                        '<text x="83" y="90" text-anchor="middle" font-family="Marlide Display,Georgia,serif" font-size="30" fill="#422F28">28-40</text>'
                        '<text x="83" y="108" text-anchor="middle" font-family="Inter Tight,Helvetica,Arial,sans-serif" font-size="11" font-weight="700" letter-spacing="3" fill="#8B6B4A">DAYS</text>')
            else:    # the scrub lifts the surface, the turmeric works on the layer beneath
                body = ('<rect x="18" y="26" width="130" height="24" rx="7" fill="none" stroke="#C9B48A" stroke-width="2.5" stroke-dasharray="6 5"/>'
                        '<circle cx="40" cy="38" r="2.6" fill="#B19A6F"/><circle cx="72" cy="34" r="2.2" fill="#B19A6F"/><circle cx="104" cy="41" r="2.6" fill="#B19A6F"/><circle cx="130" cy="35" r="2.2" fill="#B19A6F"/>'
                        '<rect x="18" y="62" width="130" height="70" rx="7" fill="#E9B54E"/>'
                        '<circle cx="48" cy="96" r="6" fill="#D99A32"/><circle cx="92" cy="104" r="6.5" fill="#D99A32"/><circle cx="126" cy="92" r="5" fill="#D99A32"/>'
                        '<path d="M120 70 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3z" fill="#FFF3CF"/><path d="M62 112 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2z" fill="#FFF3CF"/>')
            return head + body + '</svg>'
        arrow = '<div style="text-align:center;margin:10px 0"><svg width="26" height="18" viewBox="0 0 26 18"><path d="M3 4 L13 14 L23 4" stroke="%s" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></div>' % GOLD
        cards = []
        for r in it["rows"]:
            # (nov-42) opt-in "plain": true drops the thin gold outline (editor's no-thin-gold-strokes rule); "card_bg" sets the card fill
            cards.append('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:%s;border:%s;border-radius:16px;padding:28px 28px;display:flex;gap:26px;align-items:center">'
                         '<div style="flex:none;width:166px;height:166px">%s</div><div style="flex:1"><div style="font:400 34px/1.1 %s;color:%s">%s</div>'
                         '<div style="font:500 22px/1.35 %s;color:%s;margin-top:12px">%s</div></div></div>'
                         % (it.get("card_bg", "#fff"), "0" if it.get("plain") else "1px solid " + GOLD, svg(r["icon"]), SERIF, BROWN, _t(r["title"]), SANS, GREY, _t(r["line"])))
        return arrow.join(cards)
    if t == "steps":    # an easy-to-read numbered timeline (nov-34): gold numbered circles on a dotted line, a serif title and one plain line each
        out = []
        n = len(it["rows"])
        for i, r in enumerate(it["rows"]):
            line = ('<div style="position:absolute;left:35px;top:76px;bottom:-24px;border-left:2px dotted %s"></div>' % GOLD) if i < n - 1 else ""
            out.append('<div style="position:relative;display:flex;gap:28px;align-items:flex-start;padding-bottom:%dpx">%s'
                       '<div style="flex:none;width:72px;height:72px;border-radius:50%%;background:%s;color:%s;display:flex;align-items:center;justify-content:center;font:400 38px/1 %s;position:relative;z-index:1">%d</div>'
                       '<div style="flex:1;padding-top:4px"><div style="font:%s;color:%s">%s</div>'
                       '<div style="font:500 22px/1.4 %s;color:%s;margin-top:10px">%s</div></div></div>'
                       % (0 if i == n - 1 else 44, line, GOLD, CREAM, SERIF, i + 1, ("700 26px/1.2 " + SANS) if it.get("sans") else ("400 34px/1.1 " + SERIF), BROWN, _t(r["title"]), SANS, GREY, _t(r["line"])))
        return '<div style="width:536px;margin:0 auto">%s</div>' % "".join(out)
    if t == "mosaic":    # Nova Skin / Solacea mood board (editor, 2026-11-18): rows of rounded tiles, each a picture or a colour with a short serif line
        rows = []
        for row in it["rows"]:
            if isinstance(row, list):    # a bare list of tiles is one row of them
                row = {"tiles": row}
            gap = 10; tl = row["tiles"]; tot = sum(x.get("f", 1) for x in tl); avail = 536 - gap * (len(tl) - 1); h = row.get("h", 180)
            cells = []
            for x in tl:
                w = int(round(avail * x.get("f", 1) / tot))
                if x.get("picture"):
                    cells.append('<div style="flex:none;width:%dpx;height:%dpx">%s</div>' % (w, h, _pic(lk, x["picture"], w, h, None, 16)))
                else:
                    ink = x.get("ink", BROWN)
                    cells.append('<div style="flex:none;box-sizing:border-box;width:%dpx;height:%dpx;background:%s;border-radius:16px;padding:18px 20px;display:flex;flex-direction:column;justify-content:%s;align-items:center;text-align:center;gap:10px">%s%s</div>'
                                 % (w, h, x.get("bg", "#F4EDDA"), "flex-start" if (x.get("top", row.get("top"))) else "center",
                                    ('<div style="font:%s %dpx/1.15 %s;color:%s;text-wrap:balance">%s</div>' % ("700" if x.get("sans", it.get("sans")) else "400", x.get("size", 30) - (4 if x.get("sans", it.get("sans")) else 0), SANS if x.get("sans", it.get("sans")) else SERIF, ink, _t(x["title"]))) if x.get("title") else "",
                                    ('<div style="font:500 %dpx/1.3 %s;color:%s">%s</div>' % (x.get("small_size", 19), SANS, x.get("small_ink", ink), _t(x["small"]))) if x.get("small") else ""))
            rows.append('<div style="display:flex;gap:%dpx">%s</div>' % (gap, "".join(cells)))
        return '<div style="width:536px;margin:0 auto;display:flex;flex-direction:column;gap:10px">%s</div>' % "".join(rows)
    if t == "chips":    # a list in one rounded white card: a picture, a bold name and one short line each; "big": true = the larger size
        big = it.get("big"); ps, nf, lf, pv = (88, 26, 20, 16) if big else (64, 22, 18, 14)
        rows = []
        for i, r in enumerate(it["rows"]):
            rows.append('<div style="display:flex;gap:22px;align-items:center;padding:%dpx 20px;%s"><div style="flex:none;width:%dpx;height:%dpx">%s</div>'
                        '<div style="flex:1"><div style="font:700 %dpx/1.2 %s;color:%s">%s</div><div style="font:500 %dpx/1.3 %s;color:%s;margin-top:4px">%s</div></div></div>'
                        % (pv, "border-top:1px solid #EADFC8;" if i else "", ps, ps, _pic(lk, r["picture"], ps, ps, None, 12), nf, SANS, BROWN, _t(r["title"]), lf, SANS, GREY, _t(r["line"])))
        return '<div style="box-sizing:border-box;width:536px;margin:0 auto;background:#fff;border:1px solid %s;border-radius:16px;overflow:hidden">%s</div>' % (GOLD, "".join(rows))
    if t == "prices":    # (nov-38) two rounded white cards side by side, a serif price and a plain label each; nothing struck through
        cells = "".join('<div style="box-sizing:border-box;flex:1;background:%s;border:1px solid %s;border-radius:16px;padding:30px 16px 28px;text-align:center">'
                        '<div style="font:400 58px/1 %s;color:%s">%s</div>'
                        '<div style="font:700 17px/1.2 %s;letter-spacing:2px;text-transform:uppercase;color:%s;margin-top:16px">%s</div></div>'
                        % ("#fff", GOLD, SERIF, BROWN, _t(c["price"]), SANS, GOLD if i else GREY, _t(c["label"])) for i, c in enumerate(it["cells"]))
        return '<div style="display:flex;gap:16px;width:536px;margin:0 auto">%s</div>' % cells
    if t == "rhythm":    # (nov-38) three small white cards in a row: a gold ring with the number of days, a serif title, one plain line
        n = len(it["cards"]); gap = 16; w = (536 - gap * (n - 1)) // n
        cells = "".join('<div style="box-sizing:border-box;width:%dpx;background:#fff;border:1px solid %s;border-radius:16px;padding:26px 14px 28px;text-align:center">'
                        '<div style="width:104px;height:104px;margin:0 auto;border-radius:50%%;border:2px solid %s;display:flex;align-items:center;justify-content:center">'
                        '<div style="width:88px;height:88px;border-radius:50%%;border:1px solid %s;display:flex;flex-direction:column;align-items:center;justify-content:center">'
                        '<div style="font:400 40px/1 %s;color:%s">%s</div><div style="font:700 11px/1 %s;letter-spacing:3px;color:%s;margin:5px 0 0 3px">DAYS</div></div></div>'
                        '<div style="font:400 26px/1.1 %s;color:%s;margin-top:20px">%s</div>'
                        '<div style="font:500 18px/1.35 %s;color:%s;margin-top:10px">%s</div></div>'
                        % (w, GOLD, GOLD, GOLD, SERIF, GOLD, E(c["days"]), SANS, BROWN, SERIF, BROWN, _t(c["title"]), SANS, GREY, _t(c["line"])) for c in it["cards"])
        return '<div style="display:flex;gap:%dpx;width:536px;margin:0 auto">%s</div>' % (gap, cells)
    if t == "panelpic":    # (nov-38, editor's reference) a big rounded picture with an outlined, see-through panel set on its empty floor: a small caps title, a hairline,
        # then two big figures side by side with a label under each. No fill and no shade on the picture: the words sit on the picture's own floor.
        w, h = it.get("w", 536), it["h"]
        cells = "".join('<div style="flex:1;text-align:center;padding:10px 8px 14px;%s"><div style="font:700 54px/1 %s;color:#fff;letter-spacing:-1px">%s</div>'
                        '<div style="font:700 16px/1.2 %s;letter-spacing:2px;color:#fff;text-transform:uppercase;margin-top:10px">%s</div></div>'
                        % ("border-left:1px solid rgba(255,255,255,.6);" if i else "", SANS, E(c["big"]), SANS, E(c["label"])) for i, c in enumerate(it["cells"]))
        panel = ('<div style="position:absolute;left:22px;right:22px;bottom:20px;border:1px solid rgba(255,255,255,.65);border-radius:16px">'
                 '<div style="text-align:center;font:700 16px/1 %s;letter-spacing:4px;color:#fff;padding:13px 0 12px;border-bottom:1px solid rgba(255,255,255,.6);text-transform:uppercase">%s</div>'
                 '<div style="display:flex">%s</div></div>' % (SANS, E(it["title"]), cells))
        return '<div style="position:relative;width:%dpx;height:%dpx;margin:0 auto">%s%s</div>' % (w, h, _pic(lk, it["picture"], w, h, None, 16), panel)
    if t == "rhythm_rows":    # (nov-38) open rows: a soft tonal fill, a big serif number with DAYS under it, a title and one plain line. No outline, ring or shadow.
        num, ttl, ln, fill = ("#A68C57", BROWN, GREY, "#FBF7EC") if ink_dark else ("#E3C892", "#FBFAF5", "#EDE4D0", "rgba(255,255,255,.13)")
        rows = []
        for c in it["cards"]:
            rows.append('<div style="display:flex;align-items:center;gap:26px;background:%s;border-radius:16px;padding:24px 28px">'
                        '<div style="flex:none;width:92px;text-align:center"><div style="font:400 62px/1 %s;color:%s">%s</div><div style="font:700 13px/1 %s;letter-spacing:3px;color:%s;margin-top:8px">DAYS</div></div>'
                        '<div style="flex:1"><div style="font:400 34px/1.1 %s;color:%s">%s</div><div style="font:500 21px/1.35 %s;color:%s;margin-top:8px">%s</div></div></div>'
                        % (fill, SERIF, num, E(c["days"]), SANS, num, SERIF, ttl, _t(c["title"]), SANS, ln, _t(c["line"])))
        return '<div style="width:536px;margin:0 auto;display:flex;flex-direction:column;gap:12px">%s</div>' % "".join(rows)
    if t == "guarantee_row":    # (nov-38) the guarantee: one open tile, a big gold serif number with DAYS, a small tag, a serif title and the exact words. ink_dark = light theme.
        if ink_dark:
            tile, num, tag, ttl, ln = "background:#FFFFFF;border-radius:20px;padding:30px 30px", "#A68C57", "#A68C57", BROWN, GREY
            if it.get("accent"):    # (nov-41, opt-in) editor: no gold text on a light background; the number and tag take this colour instead
                num = tag = it["accent"]
        else:
            tile, num, tag, ttl, ln = "background:linear-gradient(105deg,rgba(255,255,255,.17),rgba(255,255,255,.08));border-radius:20px;padding:30px 30px", "#E3C892", "#E3C892", "#FBFAF5", "#EDE4D0"
        return ('<div style="box-sizing:border-box;width:536px;margin:0 auto;display:flex;align-items:center;gap:26px;%s">'
                '<div style="flex:none;width:130px;text-align:center"><div style="font:400 104px/0.9 %s;color:%s">%s</div><div style="font:700 15px/1 %s;letter-spacing:4px;color:%s;margin-top:12px">%s</div></div>'
                '<div style="flex:1;min-width:0"><div style="font:700 14px/1 %s;letter-spacing:3px;color:%s">%s</div><div style="font:400 40px/1.05 %s;color:%s;margin-top:12px">%s</div>'
                '<div style="font:500 22px/1.4 %s;color:%s;margin-top:12px">%s</div></div></div>'
                % (tile, SERIF, num, E(it.get("big", "60")), SANS, num, E(it.get("small", "DAYS")), SANS, tag, E(it.get("tag", "OUR GUARANTEE")), SERIF, ttl, _t(it["head"]), SANS, ln, _t(it["text"])))
    if t == "zigzag":    # (nov-38) open rows, a big rounded picture on one side and a serif title with one plain line on the other, flipping side each row. No boxes or outlines.
        pw = it.get("pic_w", 250); ph = int(pw * 1.2); rows = []
        for n, r in enumerate(it["rows"]):
            pic = '<div style="flex:none;width:%dpx;height:%dpx">%s</div>' % (pw, ph, _pic(lk, r["picture"], pw, ph, None, 16))
            txt = ('<div style="flex:1;min-width:0;text-align:%s"><div style="font:400 36px/1.1 %s;color:%s">%s</div>'
                   '<div style="font:500 22px/1.4 %s;color:%s;margin-top:14px">%s</div></div>'
                   % ("left" if n % 2 == 0 else "right", SERIF, BROWN if ink_dark else CREAM, _t(r["title"]), SANS, GREY if ink_dark else "#EDE4D0", _t(r["line"])))
            card = ('box-sizing:border-box;background:%s;border-radius:16px;padding:%dpx;' % (it.get("card_bg", "#FFFFFF"), int(it.get("card_pad", 20)))) if it.get("card") else ""    # (nov-40) opt-in: each row in a white rounded box, no outline
            rows.append('<div style="display:flex;align-items:center;gap:30px;%s">%s</div>' % (card, (pic + txt) if n % 2 == 0 else (txt + pic)))
        return '<div style="width:536px;margin:0 auto;display:flex;flex-direction:column;gap:%dpx">%s</div>' % (it.get("row_gap", 36), "".join(rows))
    if t == "glasspanels":    # (nov-38, editor's reference) big soft panels stacked: a picture on the left; on the right an outlined caps pill, a serif headline and a plain subline
        pw = it.get("pic_w", 190); ph = int(pw * 1.3); rows = []
        fill = it.get("fill", "rgba(255,255,255,.78)")
        for r in it["rows"]:
            rows.append('<div style="box-sizing:border-box;display:flex;align-items:center;gap:26px;padding:22px 28px 22px 22px;border-radius:30px;min-height:%dpx;background:%s">'
                        '<div style="flex:none;width:%dpx;height:%dpx">%s</div>'
                        '<div style="flex:1;min-width:0"><div style="display:inline-block;border:1.5px solid %s;border-radius:30px;padding:9px 18px;font:700 15px/1.2 %s;letter-spacing:1.5px;text-transform:uppercase;color:%s">%s</div>'
                        '<div style="font:400 34px/1.08 %s;color:%s;margin-top:20px;text-wrap:balance">%s</div>'
                        '<div style="font:500 21px/1.4 %s;color:%s;margin-top:12px">%s</div></div></div>'
                        % (ph + 44, fill, pw, ph, _pic(lk, r["picture"], pw, ph, None, 18), BROWN, SANS, BROWN, _t(r["pill"]), SERIF, BROWN, _t(r["title"]), SANS, GREY, _t(r["line"])))
        return '<div style="width:536px;margin:0 auto;display:flex;flex-direction:column;gap:%dpx">%s</div>' % (it.get("row_gap", 18), "".join(rows))
    if t == "prodcards":    # (nov-40, editor: section 6 "too simple" + keep alignment even) one product per white rounded box, every box the same way round:
        # picture left; a small gold tag, the serif name, one short line, then the benefits, each with a small icon in a FILLED sage dot (no outline)
        glyph = {"drop": '<path d="M24 8 C24 8 12 22 12 29 a12 12 0 0 0 24 0 C36 22 24 8 24 8Z"/>',
                 "sun": '<circle cx="24" cy="24" r="6.5"/><path d="M24 9v5M24 34v5M9 24h5M34 24h5M13.4 13.4l3.5 3.5M31.1 31.1l3.5 3.5M13.4 34.6l3.5-3.5M31.1 16.9l3.5-3.5"/>',
                 "sparkle": '<path d="M20 10 L23 19 L32 22 L23 25 L20 34 L17 25 L8 22 L17 19Z"/><path d="M34 8 L35.5 12 L39.5 13.5 L35.5 15 L34 19 L32.5 15 L28.5 13.5 L32.5 12Z"/>',
                 "leaf": '<path d="M12 36 C12 20 22 10 38 10 C38 26 28 36 12 36Z"/><path d="M12 36 L28 20"/>',
                 "flower": '<circle cx="24" cy="24" r="4"/><circle cx="24" cy="13" r="5.5"/><circle cx="24" cy="35" r="5.5"/><circle cx="13" cy="24" r="5.5"/><circle cx="35" cy="24" r="5.5"/>'}
        dot, tagc = it.get("dot", "#9AA184"), it.get("tag_ink", "#8F7F5E")
        pw, ph = int(it.get("pic_w", 196)), int(it.get("pic_h", 236))
        cards = []
        for c in it["cards"]:
            bens = "".join('<div style="display:flex;align-items:center;gap:12px;margin-top:10px"><div style="flex:none;width:30px;height:30px;border-radius:50%%;background:%s;display:flex;align-items:center;justify-content:center">'
                           '<svg width="17" height="17" viewBox="0 0 48 48" fill="none" stroke="%s" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">%s</svg></div>'
                           '<div style="font:500 18px/1.3 %s;color:%s">%s</div></div>' % (dot, CREAM, glyph[b["icon"]], SANS, GREY, _t(b["text"])) for b in c["benefits"])
            cards.append('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:#FFFFFF;border-radius:16px;padding:20px;display:flex;gap:24px;align-items:center">'
                         '<div style="flex:none;width:%dpx;height:%dpx">%s</div>'
                         '<div style="flex:1;min-width:0;text-align:left"><div style="font:700 13px/1.2 %s;letter-spacing:2.5px;text-transform:uppercase;color:%s">%s</div>'
                         '<div style="font:400 32px/1.08 %s;color:%s;margin-top:8px">%s</div>'
                         '<div style="font:500 17px/1.35 %s;color:%s;margin-top:8px">%s</div>%s</div></div>'
                         % (pw, ph, _pic(lk, c["picture"], pw, ph, None, 12), SANS, tagc, _t(c["tag"]), SERIF, BROWN, _t(c["name"]), SANS, "#7A6F66", _t(c["line"]), bens))
        return '<div style="display:flex;flex-direction:column;gap:%dpx">%s</div>' % (int(it.get("gap", 16)), "".join(cards))
    if t == "curvepanel":    # (nov-40, editor's sage editorial board) a flat sage panel, 16px corners, one soft cream curve through a few filled
        # cream dots, each with small spaced capitals and one plain line beside it. No outline, ring, shadow or gold stroke.
        w, h = 536, int(it.get("h", 560))
        light = _light(it.get("bg", "#9AA184"))    # words follow the panel: dark on a light sage, cream on a mid or deep one (a layout once set cream words on pale sage)
        ink = it.get("ink", BROWN if light else CREAM); sub = it.get("sub", GREY if light else "#EEF0E4")
        nodes = it["nodes"]
        pts = [(int(n["x"]), int(n["y"])) for n in nodes]
        d = "M %d %d" % pts[0]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            my = (y0 + y1) / 2.0
            d += " C %d %.0f %d %.0f %d %d" % (x0, my, x1, my, x1, y1)
        dots = "".join('<circle cx="%d" cy="%d" r="9" fill="%s"/>' % (x, y, ink) for x, y in pts)
        svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" style="position:absolute;left:0;top:0">'
               '<path d="%s" fill="none" stroke="%s" stroke-opacity=".75" stroke-width="2.5" stroke-linecap="round"/>%s</svg>' % (w, h, w, h, d, ink, dots))
        txt = []
        for n in nodes:
            x, y = int(n["x"]), int(n["y"]); tw = int(n.get("w", 300)); right = n.get("side", "right") == "right"
            left = x + 26 if right else x - 26 - tw
            txt.append('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;text-align:%s">'
                       '<div style="font:700 15px/1.2 %s;letter-spacing:3px;color:%s">%s</div>'
                       '<div style="font:500 21px/1.35 %s;color:%s;margin-top:8px">%s</div></div>'
                       % (left, y - 12 + int(n.get("dy", 0)), tw, "left" if right else "right", SANS, ink, _t(n["label"]), SANS, sub, _t(n["line"])))
        head = ('<div style="position:absolute;left:0;right:0;top:34px;text-align:center;font:700 14px/1 %s;letter-spacing:3px;color:%s">%s</div>' % (SANS, sub, _t(it["title"]))) if it.get("title") else ""
        return ('<div style="position:relative;box-sizing:border-box;width:%dpx;height:%dpx;margin:0 auto;background:%s;border-radius:16px;overflow:hidden">%s%s%s</div>'
                % (w, h, it.get("bg", "#9AA184"), head, svg, "".join(txt)))
    if t == "stackrows":    # (nov-41, editor) separate white rounded boxes stacked vertically: a small rounded picture on the left, then an optional
        # small capitals tag, a serif name and one plain line. No outline, ring, shadow or gold stroke; tag ink defaults to brown (no gold text on light).
        pw = int(it.get("pic", 96)); rows = []
        for r in it["rows"]:
            tag = ('<div style="font:700 13px/1.2 %s;letter-spacing:3px;text-transform:uppercase;color:%s;margin-bottom:8px">%s</div>'
                   % (SANS, it.get("tag_ink", "#7A4E2D"), _t(r["tag"]))) if r.get("tag") else ""
            rows.append('<div style="box-sizing:border-box;width:536px;margin:0 auto;background:%s;border-radius:16px;padding:%dpx;display:flex;gap:22px;align-items:center">'
                        '<div style="flex:none;width:%dpx;height:%dpx">%s</div><div style="flex:1;min-width:0;text-align:left">%s'
                        '<div style="font:400 %dpx/1.1 %s;color:%s">%s</div><div style="font:500 %dpx/1.35 %s;color:%s;margin-top:6px">%s</div></div></div>'
                        % (it.get("card_bg", "#FFFFFF"), int(it.get("pad", 16)), pw, pw, _pic(lk, r["picture"], pw, pw, None, 12), tag,
                           int(it.get("title_size", 28)), SERIF, BROWN, _t(r["title"]), int(it.get("line_size", 19)), SANS, GREY, _t(r["line"])))
        return '<div style="width:536px;margin:0 auto;display:flex;flex-direction:column;gap:%dpx">%s</div>' % (int(it.get("row_gap", 12)), "".join(rows))
    if t == "signals":
        return _signals(lk, it["rows"], sans=it.get("sans", False))
    raise ValueError("fg_block: no item type %r" % t)


def s_fg_header(lk, s, th):
    """The 70px header: the wordmark, 200 x 42, centred (Figma 2035:1133)."""
    bg = s.get("bg", DARK)
    return _wrap('<div style="height:70px;padding-top:14px;box-sizing:border-box">%s</div>' % _logo_svg(lk, s.get("logo", "run:design/assets/logo.svg")), bg)


def s_fg_hero(lk, s, th):
    """The hero. Default ("full": true): ONE full-width picture, the headline, one line and the button set on its lower part (Figma 2035:1166),
    with no fade, band or shade on the picture; legibility comes from the picture's own tones and a faint shadow on the letters only.
    "full": false keeps the older form: photo, then the words on a flat colour panel."""
    h = int(s.get("photo_h", 640))
    if s.get("open_hero"):    # (nov-38, editor: seamless, premium, Figma-like) NO card, no shadow, no outline. Words sit straight on a warm gradient that melts, over
        # one long soft ramp, into exactly the cream of the section below (the last pixel row is #FBFAF5, so there is no seam). The checklist is plain: soft tonal rows with a
        # small solid gold tick; the product is a clean 16px-rounded picture with its name, the "no date" line and the prices on the cream.
        LT, GLD = "#EDE4D0", "#E3C892"
        tick = ('<svg width="26" height="26" viewBox="0 0 26 26"><path d="M4.5 13.5 L10.5 19.5 L21.5 7" stroke="%s" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>' % "#D9B56E")
        rows = "".join('<div style="display:flex;align-items:center;gap:18px;height:56px;padding:0 20px;background:rgba(255,255,255,.13);border-radius:14px">'
                       '<div style="flex:none;width:26px;height:26px">%s</div><div style="flex:1;height:12px;border-radius:6px;background:rgba(255,255,255,.34);max-width:%d%%"></div>'
                       '<div style="flex:none;width:58px;height:20px;border-radius:10px;background:rgba(255,255,255,.2)"></div></div>' % (tick, w) for w in s.get("fade", (100, 76, 90)))
        pw = int(s.get("pic_w", 224)); ph = int(pw * 1.25); ramp_px = int(s.get("ramp", 380))
        hero_tile = ('<div style="background:%s;border-radius:18px;padding:14px;display:flex;gap:20px;align-items:center">'
                     '<div style="flex:none;width:%dpx;height:%dpx">%s</div>'
                     '<div style="flex:1;min-width:0"><div style="font:400 40px/1.05 %s;color:%s">%s</div>'
                     '<div style="font:700 15px/1 %s;letter-spacing:3px;color:#8F7F5E;margin-top:16px;text-transform:uppercase">%s</div>'
                     '<div style="font:500 21px/1.4 %s;color:%s;margin-top:14px">%s</div></div></div>'
                     % (CREAM, pw, ph, _pic(lk, s["picture"], pw, ph, None, 14), SERIF, BROWN, _t(s["product"]), SANS, E(s.get("tag", "No date on it")), SANS, GREY, _t(s["prices"])))
        words = ('<div style="padding:%dpx 32px 0"><div style="text-align:center;font:700 15px/1 %s;letter-spacing:3px;color:%s">%s</div>'
                 '<div style="margin-top:18px">%s</div>'
                 '<div style="font:500 22px/1.4 %s;color:%s;text-align:center;margin:20px auto 0;width:470px">%s</div>'
                 '<div style="margin-top:34px;display:flex;flex-direction:column;gap:10px">%s</div>'
                 '<div style="margin-top:12px">%s</div>'
                 '<div style="margin-top:32px">%s</div></div>'
                 % (int(s.get("pad_top", 56)), SANS, GLD, E(s.get("label", "")), _headline(s["headline"], 50, ("#FBFAF5", GLD), 1.1, False), SANS, LT, _t(s["sub"]),
                    rows, hero_tile, _button(s["cta"], dark=bool(s.get("cta_dark")))))
        _svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/>"
                "<feColorMatrix values='0 0 0 0 0.25  0 0 0 0 0.18  0 0 0 0 0.12  0 0 0 .7 0'/></filter><rect width='300' height='300' filter='url(#n)'/></svg>")
        grain = "data:image/svg+xml;base64," + base64.b64encode(_svg.encode()).decode()
        stops = ((0, 0), (8, .03), (16, .1), (26, .22), (38, .4), (50, .6), (60, .78), (70, .91), (80, .985), (88, 1), (100, 1))
        ramp = ",".join("rgba(251,250,245,%s) %s%%" % (a_, p_) for p_, a_ in stops)
        base = ("radial-gradient(95% 40% at 8% 2%,#B48650 0%,rgba(180,134,80,0) 64%),radial-gradient(85% 40% at 100% 30%,#6B6D4C 0%,rgba(107,109,76,0) 66%),"
                "radial-gradient(110% 40% at 0% 55%,#4A3322 0%,rgba(74,51,34,0) 70%),linear-gradient(170deg,#7E5B36,#5B4631 45%,#4F4A33)")
        mask = "linear-gradient(180deg,#000 calc(100%% - %dpx),transparent 100%%)" % ramp_px
        return _wrap('<div style="position:relative;background:%s"><div style="position:absolute;left:0;top:0;right:0;bottom:0;background:%s"></div>'
                     '<div style="position:absolute;left:0;top:0;right:0;bottom:0;background:url(%s);opacity:.9;-webkit-mask-image:%s;mask-image:%s"></div>'
                     '<div style="position:absolute;left:0;right:0;bottom:0;height:%dpx;background:linear-gradient(180deg,%s)"></div>'
                     '<div style="position:relative;padding-bottom:%dpx">%s</div></div>' % (CREAM, base, grain, mask, mask, ramp_px, ramp, int(s.get("pad_bottom", ramp_px)), words), CREAM)
    if s.get("reminders"):    # (nov-38, editor's pick: the Reminders list) a white phone-style card: gold label, serif headline, one line, a few faded ticked items with
        # date chips, then the hero item: the product itself, large (picture left, name, "no date" tag and the prices right), then the button.
        cw = 536 - 2 * 28
        glass = bool(s.get("glass"))
        CARD = ("background:rgba(255,251,242,.88);-webkit-backdrop-filter:blur(22px);backdrop-filter:blur(22px);border:1px solid rgba(255,255,255,.6);border-radius:34px;padding:30px 28px 28px;box-shadow:0 20px 50px rgba(66,47,40,.18)"
                if glass else "background:#fff;border-radius:34px;padding:30px 28px 28px;box-shadow:0 14px 40px rgba(66,47,40,.15)")
        tick = ('<svg width="30" height="30" viewBox="0 0 30 30"><circle cx="15" cy="15" r="15" fill="%s"/><path d="M8.5 15.5 L13 20 L21.5 10.5" stroke="#fff" stroke-width="3.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>' % GOLD)
        rows = "".join('<div style="display:flex;align-items:center;gap:14px;background:rgba(255,255,255,.78);border:1px solid #E3D8BF;border-radius:18px;padding:13px 16px">'
                       '<div style="flex:none;width:30px;height:30px">%s</div>'
                       '<div style="flex:1;height:14px;border-radius:7px;background:#C9BEA6;max-width:%d%%"></div>'
                       '<div style="flex:none;width:70px;height:26px;border-radius:13px;background:#E3D6B6;border:1px solid #D6C79F"></div></div>' % (tick, w)
                       for w in s.get("fade", (100, 72)))
        pw = int(s.get("pic_w", 240)); ph = int(pw * 1.25)
        pic = _pic(lk, s["picture"], pw, ph, None, 16)
        hero = ('<div style="margin-top:18px;border:1.5px solid %s;border-radius:22px;padding:14px;background:%s;display:flex;gap:18px;align-items:center">'
                '<div style="flex:none;position:relative;width:%dpx;height:%dpx">%s</div>'
                '<div style="flex:1;min-width:0"><div style="width:30px;height:30px;border-radius:50%%;border:3px solid %s;margin-bottom:14px"></div>'
                '<div style="font:400 38px/1.05 %s;color:%s">%s</div>'
                '<div style="display:inline-block;background:%s;color:%s;border-radius:20px;padding:7px 14px;font:700 17px/1 %s;margin-top:14px">%s</div>'
                '<div style="font:500 19px/1.35 %s;color:%s;margin-top:14px">%s</div></div></div>'
                % (GOLD, CREAM, pw, ph, pic, GOLD, SERIF, DARK, _t(s["product"]), GOLD, CREAM, SANS, E(s.get("tag", "No date on it")), SANS, GREY, _t(s["prices"])))
        card = ('<div style="box-sizing:border-box;width:536px;margin:0 auto;%s">'
                '<div style="text-align:center;font:700 14px/1 %s;letter-spacing:3px;color:%s">%s</div>'
                '<div style="margin-top:16px">%s</div>'
                '<div style="font:500 22px/1.4 %s;color:%s;text-align:center;margin:12px auto 24px;width:440px">%s</div>'
                '<div style="display:flex;flex-direction:column;gap:14px">%s</div>%s<div style="margin-top:26px">%s</div></div>'
                % (CARD, SANS, GOLD, E(s.get("label", "")), _headline(s["headline"], 50, tuple(s.get("tone", (BROWN, GOLD))), 1.1, False), SANS, GREY, _t(s["sub"]), rows, hero, _button(s["cta"], dark=True)))
        ov, pb = int(s.get("overlap", 0)), int(s.get("pad_bottom", 56))
        inner = '<div style="padding:%dpx 32px %dpx">%s</div>' % (int(s.get("pad_top", 40)), pb, card)
        if glass:    # a soft multi-tone gradient of the brand's own tones with fine grain, as the backdrop only (never on a picture).
            # With "overlap" the gradient stops that many px above the card's foot, so the card straddles this section and the cream one below.
            _svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/>"
                    "<feColorMatrix values='0 0 0 0 0.25  0 0 0 0 0.18  0 0 0 0 0.12  0 0 0 .7 0'/></filter><rect width='300' height='300' filter='url(#n)'/></svg>")
            grain = "data:image/svg+xml;base64," + base64.b64encode(_svg.encode()).decode()
            gr = ("radial-gradient(95% 55% at 8% 4%,#B48650 0%,rgba(180,134,80,0) 64%),radial-gradient(85% 60% at 100% 55%,#6B6D4C 0%,rgba(107,109,76,0) 66%),"
                  "radial-gradient(110% 55% at 0% 100%,#4A3322 0%,rgba(74,51,34,0) 70%),radial-gradient(90% 50% at 100% 100%,#3B2A1C 0%,rgba(59,42,28,0) 72%),linear-gradient(170deg,#7E5B36,#5B4631 55%,#4F4A33)")
            return _wrap('<div style="position:relative;background:%s"><div style="position:absolute;left:0;top:0;right:0;bottom:%dpx;background:%s"></div>'
                         '<div style="position:absolute;left:0;top:0;right:0;bottom:%dpx;background:url(\'%s\');opacity:.9"></div><div style="position:relative">%s</div></div>'
                         % (CREAM if ov else "#D3BE97", ov + pb if ov else 0, gr, ov + pb if ov else 0, grain, inner), CREAM if ov else "#D3BE97")
        return _wrap(inner, s.get("backdrop", "#F4EDDA"))
    if s.get("popup"):    # (nov-38, editor's phone pop-up reference) a modern dialog: a bright, softly blurred picture as the backdrop (a blur, never a shade),
        # a big rounded white card with a bold title, one line, the picture edge to edge, a small gold oval sticker on it, and a hairline with two text buttons.
        cw, ph = int(s.get("card_w", 480)), int(s.get("pic_h", 400))
        bgp = s.get("bg_picture") or s["picture"]
        bg = _pic(lk, bgp, 600, h).replace('style="display:block', 'style="filter:blur(18px);transform:scale(1.15);display:block', 1)
        inner = _pic(lk, dict(s["picture"], focus=s.get("pic_focus", (.5, .12))), cw, ph)
        sticker = ('<div style="position:absolute;left:18px;bottom:18px;background:%s;color:%s;border-radius:50%%/60%%;padding:10px 24px 12px;font:italic 400 30px/1 %s">%s</div>' % (GOLD, CREAM, SERIF, E(s.get("sticker", ""))) ) if s.get("sticker") else ""
        two = ('<div style="display:flex;height:%dpx;border-top:1px solid #E3E3E6"><div style="flex:1;text-align:center;font:600 24px/%dpx %s;color:%s;border-right:1px solid #E3E3E6">%s</div>'
               '<div style="flex:1;text-align:center;font:700 24px/%dpx %s;color:%s">%s</div></div>' % (92, 92, SANS, "#8F7F5E", E(s.get("no", "Decline")), 92, SANS, DARK, E(s.get("yes", s["cta"]))))
        card = ('<div style="position:absolute;left:%dpx;top:%dpx;width:%dpx;background:#fff;border-radius:44px;overflow:hidden;box-shadow:0 24px 60px rgba(25,17,14,.22)">'
                '<div style="padding:34px 28px 28px;text-align:center"><div style="font:700 40px/1.1 %s;color:%s;letter-spacing:-.8px">%s</div>'
                '<div style="font:500 24px/1.3 %s;color:%s;margin-top:12px">%s</div></div>'
                '<div style="position:relative">%s%s</div>%s</div>'
                % ((600 - cw) // 2, int(s.get("top", 50)), cw, SANS, DARK, _t(" ".join(s["headline"])), SANS, DARK, _t(s["sub"]), inner, sticker, two))
        return _wrap('<div style="position:relative;height:%dpx;overflow:hidden"><div style="position:absolute;left:0;top:0;width:600px;height:%dpx;overflow:hidden">%s</div>%s</div>'
                     % (h, h, bg, card), "#F4F4F4")
    head = _headline(s["headline"], 50, tuple(s.get("tone", (CREAM, CREAM))), 1.1, bool(s.get("keep_breaks")))
    sub = '<div style="font:500 22px/1.4 %s;text-align:center;color:#fff;width:500px;margin:0 auto">%s</div>' % (SANS, _t(s["sub"])) if s.get("sub") else ""
    btn = _button(s["cta"], dark=False) if s.get("cta") else ""
    if s.get("ink") in ("dark", "light"):    # a picture made with clear space at the top: words at the top, no shadow needed
        lt = s.get("ink") == "light"
        head = _headline(s["headline"], 50, tuple(s.get("tone", (CREAM, GOLD) if lt else (BROWN, GOLD))), 1.1, bool(s.get("keep_breaks")))
        sub = '<div style="font:500 22px/1.4 %s;text-align:center;color:%s;width:500px;margin:0 auto">%s</div>' % (SANS, "#FBFAF5" if lt else GREY, _t(s["sub"])) if s.get("sub") else ""
        btn = _button(s["cta"], dark=not lt) if s.get("cta") else ""
        if btn and s.get("button_gap"):    # (nov-39) opt-in: editor's subline-to-button gap (32) instead of the shared gap
            btn = '<div style="margin-top:%dpx">%s</div>' % (int(s["button_gap"]) - int(s.get("gap", 20)), btn)
        if s.get("label"):    # (nov-39) opt-in: small spaced capitals above the headline, naming the moment
            head = ('<div style="text-align:center;font:700 15px/1.2 %s;letter-spacing:4px;text-transform:uppercase;color:%s;margin-bottom:-6px">%s</div>'
                    % (SANS, s.get("label_ink", GOLD), _t(s["label"]))) + head
        words = ('<div style="position:absolute;left:32px;right:32px;top:%dpx;display:flex;flex-direction:column;gap:%dpx">%s%s%s</div>'
                 % (int(s.get("top", 56)), int(s.get("gap", 20)), head, sub, btn))
        return _wrap('<div style="position:relative;height:%dpx">%s%s</div>' % (h, _pic(lk, s["picture"], 600, h), words), DARK)
    if s.get("full", True):
        words = ('<div style="position:absolute;left:32px;right:32px;bottom:%dpx;display:flex;flex-direction:column;gap:%dpx;text-shadow:0 1px 14px rgba(0,0,0,.5)">%s%s<div style="text-shadow:none">%s</div></div>'
                 % (int(s.get("bottom", 40)), int(s.get("gap", 18)), head, sub, btn))
        return _wrap('<div style="position:relative;height:%dpx">%s%s</div>' % (h, _pic(lk, s["picture"], 600, h), words), DARK)
    bg = s.get("panel", BROWN)
    words = ('<div style="background:%s;padding:%dpx 32px %dpx;display:flex;flex-direction:column;gap:%dpx">%s%s%s</div>'
             % (bg, int(s.get("pad_top", 40)), int(s.get("pad_bottom", 40)), int(s.get("gap", 24)), head, sub, btn))
    return _wrap('<div>%s</div>' % _pic(lk, s["picture"], 600, h) + words, bg)


def s_fg_block(lk, s, th):
    """A section on one flat colour: 50px above and below, 40px between its parts, 32px side margins.
    items: headline / body / button / line / picture / pictures / signals (see _item). bg: cream by default;
    "ink": "dark" (default) for the brown-on-cream tones or "light" for cream words on a brown section."""
    bg = s.get("bg", CREAM)
    dark_ink = s.get("ink", "dark") == "dark"
    items, prev, parts = s["items"], None, ""
    gap = int(s.get("gap", 40))
    for it in items:
        mt = 0 if prev is None else (int(it["gap"]) if "gap" in it else 12 if it.get("tight") else
                                      int(s.get("head_gap", 20)) if prev == "headline" and it["t"] in ("body", "line") else
                                      int(s.get("button_gap", 32)) if it["t"] == "button" else gap)
        parts += '<div style="margin-top:%dpx">%s</div>' % (mt, _item(lk, it, dark_ink))
        prev = it["t"]
    pt, pb = int(s.get("pad_top", 72)), int(s.get("pad_bottom", 72))
    gap = int(s.get("gap", 40))
    side = int(s.get("pad_side", 32))    # 0 = a picture that runs edge to edge
    return _wrap('<div style="padding:%dpx %dpx %dpx;">%s</div>' % (pt, side, pb, parts), bg)


def s_fg_foot(lk, s, th):
    """The picture of the footer, for the preview only: build.py draws the real one as live HTML (it carries the unsubscribe link)."""
    ic = "".join('<img src="data:image/svg+xml;base64,%s" alt="" style="height:20px;width:%dpx">' % (
        base64.b64encode(Path(_asset(lk, "run:design/assets/%s.svg" % n)).read_bytes()).decode(), w)
        for n, w in (("instagram", 20), ("facebook", 10), ("tiktok", 20), ("youtube", 20)))
    words = '' if s.get("top_only") else ('<div style="font:500 14px/1.4 %s;color:%s;margin-top:26px">No longer want to receive these emails? <u style="color:%s">Unsubscribe.</u><br>%s</div>'
             % (SANS, CREAM, GOLD, E((lk.get("footer") or {}).get("line", ""))))
    inner = ('<div style="height:%dpx;box-sizing:border-box;padding-top:40px;text-align:center;background:%s">%s'
             '<div style="display:flex;gap:40px;justify-content:center;align-items:center;margin-top:25px;height:20px">%s</div>%s</div>'
             % (135 if s.get("top_only") else 225, DARK, _logo_svg(lk, "run:design/assets/logo.svg"), ic, words))
    return _wrap(inner, DARK)


def s_fg_band(lk, s, th):
    """(nov-38) A warm gradient band with fine grain, in the hero's own tones, that melts in from the section above ("from" colour) and out into the one
    below ("to" colour) over "feather" px each way, so there is no hard edge. Items are the same as fg_block (cream words on the band)."""
    f = int(s.get("feather", 130)); frm, to = s.get("from", CREAM), s.get("to", CREAM)
    items, prev, parts = s["items"], None, ""
    for it in items:
        mt = 0 if prev is None else (20 if prev == "headline" and it["t"] in ("body", "line") else 32 if it["t"] == "button" else int(s.get("gap", 40)))
        parts += '<div style="margin-top:%dpx">%s</div>' % (mt, _item(lk, it, s.get("ink", "light") == "dark"))
        prev = it["t"]
    _svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/>"
            "<feColorMatrix values='0 0 0 0 0.25  0 0 0 0 0.18  0 0 0 0 0.12  0 0 0 .7 0'/></filter><rect width='300' height='300' filter='url(#n)'/></svg>")
    grain = "data:image/svg+xml;base64," + base64.b64encode(_svg.encode()).decode()
    stops = ((0, 0), (10, .03), (22, .12), (36, .3), (50, .55), (64, .78), (78, .93), (90, .99), (100, 1))
    # top ramp: opaque "from" at the very top fading to clear; bottom ramp: clear fading to opaque "to" at the very bottom
    def hex_rgb(c): return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    tr = ",".join("rgba(%d,%d,%d,%s) %s%%" % (hex_rgb(frm) + (round(1 - a, 3), p)) for p, a in stops)
    br = ",".join("rgba(%d,%d,%d,%s) %s%%" % (hex_rgb(to) + (round(a, 3), p)) for p, a in stops)
    base = ("radial-gradient(95% 40% at 8% 10%,#B48650 0%,rgba(180,134,80,0) 64%),radial-gradient(85% 40% at 100% 50%,#6B6D4C 0%,rgba(107,109,76,0) 66%),"
            "radial-gradient(110% 45% at 0% 90%,#4A3322 0%,rgba(74,51,34,0) 70%),linear-gradient(170deg,#7E5B36,#5B4631 45%,#4F4A33)")
    if (s.get("tone") or ("light" if s.get("ink", "light") == "dark" else "dark")) == "light":    # (dark words always get the light band, so they can be read) a lighter, airier version in the same tones (champagne, amber, a little olive and bronze), for a band with frosted panels on it
        base = ("radial-gradient(90% 38% at 10% 12%,#EFE3C6 0%,rgba(239,227,198,0) 66%),radial-gradient(80% 36% at 100% 38%,#D8C49B 0%,rgba(216,196,155,0) 66%),"
                "radial-gradient(90% 36% at 0% 72%,#E3D5B0 0%,rgba(227,213,176,0) 66%),radial-gradient(90% 38% at 100% 96%,#C9B386 0%,rgba(201,179,134,0) 68%),linear-gradient(170deg,#F4EBD3,#E2D2AA)")
    mask = "linear-gradient(180deg,transparent 0,#000 %dpx,#000 calc(100%% - %dpx),transparent 100%%)" % (f, f)
    inner = ('<div style="position:relative;background:%s"><div style="position:absolute;left:0;top:0;right:0;bottom:0;background:%s"></div>'
             '<div style="position:absolute;left:0;top:0;right:0;bottom:0;background:url(%s);opacity:.9;-webkit-mask-image:%s;mask-image:%s"></div>'
             '<div style="position:absolute;left:0;right:0;top:0;height:%dpx;background:linear-gradient(180deg,%s)"></div>'
             '<div style="position:absolute;left:0;right:0;bottom:0;height:%dpx;background:linear-gradient(180deg,%s)"></div>'
             '<div style="position:relative;padding:%dpx 32px %dpx">%s</div></div>'
             % (frm, base, grain, mask, mask, f, tr, f, br, f + int(s.get("pad_top", 20)), f + int(s.get("pad_bottom", 20)), parts))
    return _wrap(inner, frm)


FG = {"fg_band": s_fg_band, "fg_header": s_fg_header, "fg_hero": s_fg_hero, "fg_block": s_fg_block, "fg_foot": s_fg_foot}


# ---- the layout step's guide to these sections (2026-11-19) ---------------------------------------------------------------------------------
# line.py offers this to a brand whose look file says `"default_look": "figma"`, so a new email's first layout is built from these sections,
# not from the older house ones. No brand name here: brand recipes (which email type gets which order) come from the brand's own look file
# (`figma.recipes`), its words and pictures from its own job card and copy.
FG_SECTIONS_GUIDE = {
    "fg_header": "no fields. The dark band with the logo. First section of every email.",
    "fg_hero": "picture (tall, full width), photo_h (840 to 900 for an offer, 640 to 760 otherwise), headline, sub (one line), cta, optional label (small caps above the headline), top/bottom/gap (where the words sit on the picture's EMPTY area). The picture must be made with a calm empty lower part for the words; never a dark overlay.",
    "fg_block": "items: a list of items (below), optional bg (hex), ink (\"dark\" or \"light\"), pad_top/pad_bottom (default 72), gap (default 40), head_gap (20), button_gap (32). One flat colour; most of the email is this section.",
    "fg_foot": "no fields. The dark footer with the unsubscribe line. Last section of every email.",
}
FG_ITEMS_GUIDE = {
    "headline": "lines: a list of one or two short lines, the first in the dark tone, the last in the gold accent (use <i>..</i> for the accent); size (default 50, closing 30).",
    "body": "text (one or two short sentences, centred).",
    "button": "label: at most four words, a verb phrase in normal sentence case (never all capitals, no arrow), e.g. Shop the duo.",
    "line": "text: the closing serif line.",
    "picture": "picture {todo, brief, alt} or a photo, w (default 536), h, r (corner radius, default 16).",
    "pictures": "items: two to four {picture, caption, sub}: a row of rounded pictures with a serif caption under each; h, gap.",
    "signals": "rows: three {picture, tag, title, line}: picture left, gold tag, serif title, one plain line.",
    "marquee": "text: a gold strip of spaced capitals naming the moment; nothing promised in it.",
    "price": "now, was: the sale price big, the old one slashed.",
    "small": "text: a small plain note (disclaimers, what is included) directly under the item above.",
    "infographic": "ALWAYS plain: true (no gold outline); one style among several ways to explain (curvepanel, steps, comparison, big numbers, a timeline): do not default to it; rows: three {icon, title, line}: an explanation as three drawn cards joined by arrows. Use instead of a numbered list.",
    "steps": "rows: two or three {title, line}: an easy numbered timeline.",
    "mosaic": "rows: a list of rows, each {tiles: [{picture, f?} or {bg, title, text?, f?}], h}: rounded tiles side by side, each a picture or a colour with a short serif line; f is the tile's width share, h the row height in px.",
    "chips": "rows: {picture, title, line}: a list in one white rounded card.",
    "reviewcard": "rows: {stars?, tag?, title?, text, who, age?, verified?}: the website's review card for WRITTEN reviews: stars, an area tag (e.g. Hands · Body Scrub), a title, the review, name and age range; verified: true only when it is literally true. Reviews are real and each shown once.",
    "pills": "items: {text, kind?}: the website's tags in a centred row: savings pills and area tags (sand fill), or kind: sale for the dark sale pill.",
    "pullquote": "only when the designer names it: text, who, picture?, size?: one voice big on the open page.",
    "voicecards": "EVERY row must carry the creator's still as picture {todo, alt} (a cleared creator video still; the wireframe shows a placeholder). THE template for creators' and customers' SPOKEN words (the designer's choice, 2026-11-20): rows: {text, who, picture?, bg?}: one soft filled card per voice, the creator's still on the left, her exact words and first name beside it; no outline, no tag. Written star reviews use reviewcard instead",
    "quotegrid": "only when the designer names it: items: {text, who, bg?}: tinted quote tiles.",
    "quote": "OLDER boxed style, not the template (use voicecards instead; only when the designer names it): text, who, tag, plain?: a customer's exact words in a rounded box; set plain: true for a soft filled box with no gold outline (the designer's rule: no thin gold strokes); card_bg sets its fill.",
    "gcard": "head, text, tag: the promise in the signal-card style (seal on the left). Use the brand's exact guarantee words.",
    "guarantee": "head, text: the promise as an obvious white card with a round badge.",
    "guarantee_row": "head, text, tag, big: the promise as one open tile.",
    "freecard": "ALWAYS plain: true (no gold outline). head, text, tag, picture: a free gift shown as a card, never button-like.",
    "minicard": "ALWAYS flat: true and ring: \"transparent\" (a solid tint, no gradient, no outlined circles) unless the designer names the gradient. head, text, tag, benefits (three short lines, never ingredients), picture: a small product box in a flat tint of the tube's own colour (a gradient only when the designer names it).",
    "routinepanel": "cols: {name, stats}, picture, label: a picture with a rounded grid on it, one column per product.",
    "rhythm_rows": "cards: {days, title, line}, open rows with a big number and a title (no outline, ring or shadow).",
    "zigzag": "rows: {picture, title, line} with the picture flipping side each row, no boxes.",
    "glasspanels": "rows: {picture, pill, title, line}: big soft panels with a picture on the left.",
    "divider": "no fields. A thin gold rule.",
    "stackrows": "rows: {picture, tag?, title, line}: separate white rounded boxes stacked vertically, a small rounded picture on the left; no outline, no gold text on light. Use for ingredients or benefits.",
    "prodcards": "cards: one {name, tag, line, picture, benefits: [{icon, text}]} per product (icon: drop, sun and similar): one white rounded box each, picture left, every box the same way round.",
    "curvepanel": "title?, h (about 520), bg (a flat sage hex), picture?, nodes: three {x, y, w, label, line}: x and y are pixel positions inside the 536 x h panel stepping down and across (e.g. 104,120 then 60,282 then 104,420), w the text width, label small capitals, line one plain sentence: a mechanism drawn as a curve (renew, erase, reset).",
    "benefitcard": "head, text, tag, picture, benefits: [{icon, title, text}]: one NEW product as a bigger stacked card above the 'also inside' cards.",
}
FG_RULES = (
    "FIGMA LOOK RULES (the designer's own, from the emails she approved): FLAT COLOURS ONLY: no gradient background in any section, band or box unless the designer names it for this email (then she says which). build the email from fg_header, fg_hero, fg_block and fg_foot, in the order of the "
    "recipe that fits the email's type. Every picture has a calm empty area where words sit; never a dark overlay, band or gradient on a picture. "
    "One main button per section, and the first one above the first screen's end (about 700px down). Headlines short enough for one or two lines. "
    "An explanation is an infographic or steps, never a long paragraph; a list of ingredients is pictures with captions. Boxes are small, gaps are small, "
    "disclaimers are small. Every picture inset has rounded corners. The promise is an obvious card with the brand's exact words. "
    "Words come only from the copy; a heading is cut from the copy's own sentences, nothing added. Skin is dry and the real product is shown as its product file describes it.")


def guide_text(recipes=None, rules=None):
    """The text the layout step is offered for a Figma-look brand: sections, items, the brand's recipes, the rules."""
    out = "FIGMA LOOK SECTIONS (this brand's default look; use these):\n" + "\n".join("%s: %s" % kv for kv in FG_SECTIONS_GUIDE.items())
    out += "\n\nITEMS INSIDE fg_block / fg_band (each item is {\"t\": <name>, ...fields}):\n" + "\n".join("%s: %s" % kv for kv in FG_ITEMS_GUIDE.items())
    if recipes:
        out += "\n\nTHIS BRAND'S RECIPES (pick the one that fits the email's type; its order is a starting point, the copy decides the rest):\n" + "\n".join(
            "%s: %s" % (k, v) for k, v in recipes.items())
    if rules:
        out += "\n\nTHIS BRAND'S DESIGN RULES (from the designer's own reviews; they outrank the generic rules below):\n" + "\n".join("- " + r for r in rules)
    return out + "\n\n" + FG_RULES


def box_ratio(sec, item=None):
    """Width / height of the box a Figma-look picture fills, so a picture is made at its own shape; None when unknown."""
    try:
        if item is None:
            return 600.0 / float(sec.get("photo_h", 640))
        if item.get("w") and item.get("h"):
            return float(item["w"]) / float(item["h"])
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None
