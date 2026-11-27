#!/usr/bin/env python3
"""natural_statics — a round of natural static ads: real pictures we own, words set in code, winners' copy beside them.

    natural_statics.py start    --brand <b> --product <p> --avatar <a> --label <name>    a sprint.json to fill
    natural_statics.py comments --brand <b> --ads <ad id> ...                            why people bought: an ad's own comments, most liked first
    natural_statics.py who      <sprint.json> [--only <id> ...]                          who each ad is for and what it must say: read it, then write the lines
    natural_statics.py copy     <sprint.json> [--search <words>]                         copy that already ran, clean of the round's banned lines
    natural_statics.py check    <sprint.json>                                            words, one change per version, pictures, copy (no model)
    natural_statics.py draft    <sprint.json> [--only <id> ...] [--all]                  the first picture of each ad, 1080 x 1920 (--all: every version)
    natural_statics.py assign   <sprint.json> [--only <id> ...] [--publish]   the five versions of each ad, one design assignment each
    natural_statics.py page     <sprint.json>                                            page.html, its Markdown copy and small pictures
    natural_statics.py number   <sprint.json>                                            one brief number per ad, finished files in its own run
    natural_statics.py file     <sprint.json> [--only <id> ...] [--replace] [--dry-run]  each ad onto the approval page, gates as they stand
    natural_statics.py status   <sprint.json>                                            what the approval page says about each card

Nothing here approves, uploads or spends, and nothing here turns a gate off: a refusal is printed as it came. No model
call. The record is runs/ad-variations/<brand>/<label>/. Layouts: story, tag, letter, note, comments, plate, list, thread,
search. `draft` makes the first picture of each ad; the five versions are the graphic designer's (`assign`).
"""
import argparse, html, json, math, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
IMG = REPO / "components" / "image-production"
META = REPO / "components" / "meta-upload"
W, H = 1080, 1920
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
HELV = "/System/Library/Fonts/HelveticaNeue.ttc"
AVN = "/System/Library/Fonts/Avenir Next.ttc"
LAYOUTS = ("story", "tag", "letter", "note", "comments", "plate", "list", "thread", "search")
NOTE_YELLOW, NIGHT = (218, 165, 32), (14, 14, 15)


# ---------------------------------------------------------------------------------------------------- the record --
def load(p):
    p = Path(p).resolve()
    d = json.loads(p.read_text())
    d["_dir"] = p.parent
    return d


def name_of(i):
    return "control" if i == 0 else "v%d" % i


def pic(sp, rel):
    """A picture path: inside the sprint folder first, then the workspace."""
    for base in (sp["_dir"], REPO):
        if (base / rel).is_file():
            return base / rel
    return None


def lines(text):
    return [x.strip() for x in str(text).split(" / ")]


def start(a):
    d = REPO / "runs" / "ad-variations" / a.brand / a.label
    f = d / "sprint.json"
    if f.exists():
        return "already started: %s" % f.relative_to(REPO)
    d.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({
        "brand": a.brand, "product": a.product, "avatar": a.avatar, "angle": "promo", "label": a.label,
        "page": "", "batch": "", "offer": "", "moment": "", "until": "", "aim": True,
        "never": [], "bubble": [], "wordmark": a.brand.upper(),
        "copy": {"primary": [], "headlines": [], "descriptions": []},
        "ads": [{"id": "a", "title": "", "sub_avatar": "", "desire": "", "awareness": "", "doubt": "", "why": "", "layout": "story", "photo": "", "lines": ["control line / second line", "version 1"],
                 "body": [], "comments": [], "emoji": [], "receipt": ""}]}, indent=1, ensure_ascii=False))
    return str(f.relative_to(REPO))


# ------------------------------------------------------------------------------------------------------ the check --
def ad_words(sp, ad):
    out = list(ad.get("lines") or []) + list(ad.get("body") or []) + list(ad.get("after") or []) + [t for m in ad.get("thread") or [] for t in [m.get("text") or ""] + list(m.get("caption") or [])] + [c["text"] if isinstance(c, dict) else c for c in ad.get("comments") or []]
    return out + list(sp.get("bubble") or []) + list(ad.get("bubble") or [])


AIM_KEYS = ("desire", "awareness", "stage", "doubt", "claim")


def who_of(sp, ad):
    """(brand, avatar, sub, demographic, what) as the ad and its round name them. `sub` is drawn words on the comments
    layout, so it counts only when it is one of the avatar's sub-avatars; `sub_avatar` is always the person."""
    sys.path.append(str(HERE))
    import brandctx as BC
    H, av, sub = BC.who(), ad.get("avatar") or sp.get("avatar"), ad.get("sub_avatar") or ""
    if not sub and ad.get("sub"):
        key = re.sub(r"^sub-\d+-", "", str(ad["sub"]).strip())
        sub = key if av and key in H.subs(sp["brand"], av) else ""
    what = {k: ad.get(k) or sp.get("claim" if k == "claim" else "") for k in AIM_KEYS}
    lv = re.search(r"\b(%s)\b" % "|".join(BC.LEVELS), str(what.get("awareness") or "").lower())
    what["awareness"] = lv.group(1) if lv else None
    return sp["brand"], av, sub, ad.get("demographic") or sp.get("demographic") or None, {k: v for k, v in what.items() if v}


def aim_of(sp, ad):
    """The ad's `aim` (who.stamp). A round that does not set `aim` keeps only what its ad named: nothing is claimed for it."""
    import brandctx as BC
    args = who_of(sp, ad)
    st = BC.who().stamp(*args)
    return st if sp.get("aim") else {**st, **{k: args[4].get(k) for k in AIM_KEYS}}


def who_text(sp, ad):
    args = who_of(sp, ad)
    import brandctx as BC
    return BC.who_text(args)


def check_aim(sp, ad):
    """What a round with `aim` must name on every ad: the person, the desire, the awareness level, the one doubt."""
    if not sp.get("aim"):
        return []
    args = who_of(sp, ad)
    import brandctx as BC
    H, i, bad = BC.who(), ad["id"], []
    if not args[1] or not (H.avatar_dir(sp["brand"], args[1]) / "profile.md").is_file():
        bad.append("%s: no avatar on file: %r" % (i, args[1]))
    elif not (ad.get("sub_avatar") or args[2]):
        bad.append("%s: no sub_avatar (or \"none\" when it speaks to the whole avatar): %s" % (i, ", ".join(H.subs(sp["brand"], args[1])) or "it has none"))
    else:
        try:
            H.resolve(sp["brand"], args[1], args[2])
        except SystemExit as e:
            bad.append("%s: %s" % (i, e))
    if not ad.get("desire"):
        bad.append("%s: no desire" % i)
    if not args[4].get("awareness"):
        bad.append("%s: awareness is one of %s" % (i, ", ".join(H.LEVELS)))
    if ad.get("doubt") not in H.DOUBTS:
        bad.append("%s: doubt is one of %s" % (i, ", ".join(H.DOUBTS)))
    return bad


def price_tokens(t):
    return set(re.findall(r"\$\d+(?:\.\d\d)?", t))


def old_product(path, brand):
    """Why a product cut-out is not the official one, or None (components/casting new_only: the list and its copies)."""
    import importlib.util
    q = importlib.util.spec_from_file_location("new_only", str(REPO / "components" / "casting" / "casting" / "new_only.py"))
    no = importlib.util.module_from_spec(q)
    q.loader.exec_module(no)
    return no.old_picture(str(path), brand) or no.copy_of_old(path, brand)


def check(sp):
    """Every fault, by ad. Empty means the round may be drafted and filed."""
    bad = []
    if not sp.get("offer"):
        bad.append("round: no offer line")
    ok_price = price_tokens(" ".join([sp.get("offer") or ""] + list(sp.get("prices") or [])))
    for ad in sp["ads"]:
        i = ad["id"]
        if ad.get("layout") not in LAYOUTS:
            bad.append("%s: layout %r is not one of %s" % (i, ad.get("layout"), ", ".join(LAYOUTS)))
        ls = ad.get("lines") or []
        if len(ls) != 6:
            bad.append("%s: %d pictures, every ad ships six: a control and five versions" % (i, len(ls)))
        if len(set(ls)) != len(ls):
            bad.append("%s: two versions say the same thing" % i)
        bad += check_aim(sp, ad)
        if not ad.get("why"):
            bad.append("%s: no reason it sells" % i)
        if not ad.get("receipt"):
            bad.append("%s: no receipt (the swipe, the winner or the customer's words it comes from)" % i)
        if ad.get("layout") in ("story", "tag", "plate", "search") and not pic(sp, ad.get("photo") or "-"):
            bad.append("%s: picture not found: %s" % (i, ad.get("photo")))
        if ad.get("layout") == "comments" and not all(isinstance(c, dict) and c.get("text") and c.get("source") for c in ad.get("comments") or [None]):
            bad.append("%s: every comment is a real one, with its source" % i)
        for q in [m.get("photo") for m in ad.get("thread") or []] + [(ad.get("picture") or {}).get("path")]:
            if q and not pic(sp, q):
                bad.append("%s: picture not found: %s" % (i, q))
        if ad.get("cutout") and pic(sp, ad["cutout"]):
            why = old_product(pic(sp, ad["cutout"]), sp["brand"])
            if why:
                bad.append("%s: %s; use the official sheet's cut-out (the kit's model/sheet/current/cutouts)" % (i, why))
        for t in ad_words(sp, ad):
            for n in sp.get("never") or []:
                if n.lower() in t.lower():
                    bad.append("%s: banned line %r in %r" % (i, n, t[:60]))
            if "—" in t or "–" in t:
                bad.append("%s: long dash in %r" % (i, t[:60]))
            extra = price_tokens(t) - ok_price
            if extra:
                bad.append("%s: price %s is not this round's offer" % (i, ", ".join(sorted(extra))))
        said = " ".join(ad_words(sp, ad)).lower()
        if sp.get("offer") and sp["offer"].lower() not in said and not ad.get("no_offer_on_picture"):
            bad.append("%s: the offer is not on the picture" % i)
    return bad


def ran_lines(brand):
    sys.path.insert(0, str(META))
    import copy_library as CL
    lib = CL.library(brand, n=400)
    return {k: [o for o in lib[k] if o.get("from") in ("winner", "live")] for k in ("primary", "headlines", "descriptions")}


def lib_heads(lib):
    return [o["text"] for o in lib["headlines"]][:2]


def check_copy(sp, lib=None):
    """The words beside the ad have run before (offer matched to today's is still the same line). An ad may bring its
    own words for its sub-avatar (`copy` on the ad): its first text opens in his signed angle or a customer's words and
    is new on purpose, the rest ran."""
    own = [x for x in sp.get("ads") or [] if x.get("copy")]
    if own:
        lib, bad = lib or ran_lines(sp["brand"]), []
        for x in own:
            c = x["copy"]
            bad += ["%s: %s" % (x["id"], b) for b in check_copy({**sp, "ads": [], "copy": {**c, "primary": (c.get("primary") or [])[1:] * 2, "headlines": sp.get("ran_headlines") or lib_heads(lib)}}, lib)
                    if not b.startswith("copy: %d" % 0)]
            if len(c.get("primary") or []) < 2 or len(c.get("headlines") or []) < 2 or not c.get("descriptions"):
                bad.append("%s: copy: two texts, two headlines and a description" % x["id"])
            for t in (c.get("primary") or []) + (c.get("headlines") or []):
                bad += ["%s: copy: banned line %r" % (x["id"], n) for n in sp.get("never") or [] if n.lower() in t.lower()]
        return bad
    c, bad = sp.get("copy") or {}, []
    for k, need in (("primary", 2), ("headlines", 2), ("descriptions", 1)):
        if len(c.get(k) or []) < need:
            bad.append("copy: %d %s, need %d" % (len(c.get(k) or []), k, need))
        for t in c.get(k) or []:
            for n in sp.get("never") or []:
                if n.lower() in t.lower():
                    bad.append("copy: banned line %r in %r" % (n, t[:50]))
    if bad:
        return bad
    lib = lib or ran_lines(sp["brand"])
    sys.path.insert(0, str(META))
    import copy_library as CL, approve as A
    for k in ("primary", "headlines"):
        ran = {CL.norm(o["text"]) for o in lib[k]}
        for t in c[k]:
            if not A.has_run(t, ran):
                bad.append("copy: never ran, so it files as unchecked: %r" % t[:70])
    return bad


# ----------------------------------------------------------------------------------------------------- the pictures --
def font(path, size, index=0):
    from PIL import ImageFont
    if not Path(path).is_file():
        raise SystemExit("font missing on this machine: %s" % path)
    return ImageFont.truetype(path, int(size), index=index)


def fit(text, path, size, index, width):
    while font(path, size, index).getlength(text) > width and size > 12:
        size -= 2
    return font(path, size, index)


def wrap(text, f, width):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if cur and f.getlength(t) > width:
            out.append(cur); cur = w
        else:
            cur = t
    return out + [cur] if cur else out


def story_photo(path):
    """The picture at 9:16: a tall one fills it, anything else sits in the story on its own soft colours."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if im.height / im.width > 1.6:
        return ImageOps.fit(im, (W, H), Image.LANCZOS)
    im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    top, bot = im.resize((1, 24)).getpixel((0, 0)), im.resize((1, 24)).getpixel((0, 23))
    can = Image.new("RGB", (W, H))
    for y in range(H):
        k = y / (H - 1)
        can.paste(tuple(int((a + (b - a) * k) * .62) for a, b in zip(top, bot)), (0, y, W, y + 1))
    can.paste(im, (0, (H - im.height) // 2))
    return can


def bubbles(im, groups, top, size=.056, pad_x=.04, pad_y=.012, gap=.014):
    """White story bubbles, the native look, sized down until they fit."""
    import tempfile
    sys.path.insert(0, str(IMG))
    from image_production import story_caption as SC
    from PIL import Image
    if not groups:
        return im
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / "a.png", Path(d) / "b.png"
        im.save(a)
        while True:
            try:
                SC.render(str(a), str(b), {"bubbles": groups, "font": BOLD}, {"bubble_top": top, "size": size, "pad_x": pad_x, "pad_y": pad_y, "gap": gap})
                return Image.open(b).convert("RGB")
            except ValueError:
                size *= .96
                if size < .02:
                    raise


def emoji(ch, px):
    sys.path.insert(0, str(IMG))
    from image_production import story_caption as SC
    return SC._emoji(ch, px)


def glow_text(im, xy, text, f):
    from PIL import Image, ImageDraw, ImageFilter
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).text((xy[0], xy[1] + 4), text, font=f, fill=190, anchor="ma")
    im.paste((0, 0, 0), (0, 0), m.filter(ImageFilter.GaussianBlur(7)))
    ImageDraw.Draw(im).text(xy, text, font=f, fill="white", anchor="ma")


def gold(im, box, text, size):
    from PIL import Image, ImageDraw, ImageFilter
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    strip = Image.new("RGB", (w, 1))
    for x in range(w):
        s = .5 + .5 * math.cos((x / max(1, w - 1) - .5) * 2 * math.pi)
        strip.putpixel((x, 0), tuple(int(a * (1 - s) + b * s) for a, b in zip((176, 130, 50), (243, 217, 130))))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 14, fill=255)
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 6, x1, y1 + 8), 14, fill=110)
    im.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(9)))
    im.paste(strip.resize((w, h)), (x0, y0), m)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x0 + 5, y0 + 5, x1 - 6, y1 - 6), 10, outline=(250, 234, 175), width=2)
    d.text(((x0 + x1) / 2, (y0 + y1) / 2), text, font=fit(text, BOLD, size, 0, w - 50), fill=(18, 15, 10), anchor="mm")


def offer_bubble(sp, ad):
    b = ad.get("bubble") if ad.get("bubble") is not None else sp.get("bubble")
    return [b] if b else []


def d_story(sp, ad, text, i):
    im = story_photo(pic(sp, ad["photo"]))
    im = bubbles(im, [lines(text)], ad.get("top", .12))
    return bubbles(im, offer_bubble(sp, ad), ad.get("offer_top", .78))


def d_tag(sp, ad, text, i):
    from PIL import Image, ImageDraw
    im, ls = story_photo(pic(sp, ad["photo"])), lines(text)
    w, h = 1040, 150 + 110 * len(ls) + 70
    tag = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    q = ImageDraw.Draw(tag)
    q.rounded_rectangle((0, 40, w, h - 40), 34, fill=(0, 0, 0, 255))
    f = min((fit(t, AVN, 92, 2, w - 110) for t in ls), key=lambda z: z.size)
    for j, t in enumerate(ls):
        q.text((w / 2, h / 2 - 55 * (len(ls) - 1) + j * 110), t, font=f, fill="white", anchor="mm")
    tag = tag.rotate(ad.get("tilt", 10), expand=True, resample=Image.BICUBIC)
    im.paste(tag, (W // 2 - tag.width // 2, int(ad.get("tag_y", .787) * H) - tag.height // 2), tag)
    return bubbles(im, offer_bubble(sp, ad), ad.get("offer_top", .135))


def d_letter(sp, ad, text, i):
    from PIL import Image, ImageDraw, ImageFilter
    im, ls, y = Image.new("RGB", (W, H), (0, 0, 0)), lines(text), 260
    cut = pic(sp, ad.get("cutout") or "-")
    if cut:
        c = Image.open(cut).convert("RGBA")
        c = c.resize((round(c.width * 470 / c.height), 470), Image.LANCZOS)
        g = Image.new("L", (W, H), 0)
        ImageDraw.Draw(g).ellipse((310, 200, 770, 720), fill=70)
        im.paste((120, 124, 122), (0, 0), g.filter(ImageFilter.GaussianBlur(70)))
        im.paste(c, ((W - c.width) // 2, 225), c)
        y = 740
    d, em = ImageDraw.Draw(im), (ad.get("emoji") or [])
    e = em[i] if i < len(em) else None
    for j, t in enumerate(ls):
        last = e and j == len(ls) - 1
        f = fit(t, AVN, 94, 8, 720 if last else 900)
        x = (W - f.getlength(t) - (106 if last else 0)) / 2
        d.text((x, y), t, font=f, fill="white")
        if last:
            g = emoji(e, 86)
            im.paste(g, (int(x + f.getlength(t) + 20), y + 26), g)
        y += 102
    y += 44
    for t in ad.get("body") or []:
        if not t:
            y += 34
            continue
        b, t = t.startswith("*"), t.lstrip("*")
        d.text((W / 2, y), t, font=fit(t, HELV, 42 if b else 38, 1 if b else 0, 960), fill="white", anchor="ma")
        y += 58 if b else 52
    if sp.get("wordmark"):
        d.text((W / 2, max(y + 40, 1640)), sp["wordmark"], font=font(HELV, 52, 1), fill="white", anchor="ma")
    return im


def attach(sp, ad, im, y):
    """A picture pasted into a note, under the words."""
    from PIL import Image, ImageDraw, ImageOps
    p = ad.get("picture")
    if not p:
        return
    h = min(p.get("h", 460), 1760 - int(y))
    if h < 260:
        raise SystemExit("%s: no room for the picture under the words" % ad["id"])
    ph = ImageOps.fit(ImageOps.exif_transpose(Image.open(pic(sp, p["path"]))).convert("RGB"), (p.get("w", 700), h), Image.LANCZOS, centering=tuple(p.get("at", (.5, .5))))
    m = Image.new("L", ph.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, ph.width - 1, ph.height - 1), 26, fill=255)
    im.paste(ph, (70, int(y)), m)


def d_note(sp, ad, text, i):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.text((70, 196), "‹ Notes", font=font(HELV, 46), fill=NOTE_YELLOW)
    d.text((1010, 196), "Done", font=font(HELV, 46, 1), fill=NOTE_YELLOW, anchor="ra")
    f, y = font(HELV, 66, 1), 300
    for t in wrap(text, f, 930):
        d.text((70, y), t, font=f, fill=(10, 10, 10))
        y += 78
    y += 34
    for t in ad.get("body") or []:
        if not t:
            y += 32
            continue
        b, t = t.startswith("*"), t.lstrip("*")
        d.text((70, y), t, font=fit(t, HELV, 48, 1 if b else 0, 950), fill=(20, 20, 20))
        y += 63
    attach(sp, ad, im, y + 30)
    return im


def say(im, x, y, text, f, fill):
    """A line of text with its emoji in colour, left at x, top at y."""
    from PIL import ImageDraw
    sys.path.insert(0, str(IMG))
    from image_production import story_caption as SC
    d, px = ImageDraw.Draw(im), f.size
    for t, e in SC._parts(text):
        if e:
            g = SC._emoji(t, int(px * .96))
            im.paste(g, (int(x + px * .04), int(y + px * .12)), g)
            x += px * 1.02
        else:
            d.text((x, y), t, font=f, fill=fill)
            x += f.getlength(t)


def said_width(text, f):
    sys.path.insert(0, str(IMG))
    from image_production import story_caption as SC
    return SC._width(text, f, f.size)


def d_list(sp, ad, text, i):
    """A phone checklist: everyone is ticked off, the last line is the one that changes."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.text((70, 236), "‹ Notes", font=font(HELV, 46), fill=NOTE_YELLOW)
    d.text((1010, 236), "Done", font=font(HELV, 46, 1), fill=NOTE_YELLOW, anchor="ra")
    d.text((70, 350), ad.get("heading") or "", font=font(HELV, 78, 1), fill=(10, 10, 10))
    y, f, b = 500, font(HELV, 56), font(HELV, 58, 1)
    for t in ad.get("body") or []:
        d.ellipse((70, y + 6, 126, y + 62), fill=NOTE_YELLOW)
        d.line([(85, y + 35), (95, y + 46), (113, y + 23)], fill="white", width=6, joint="curve")
        say(im, 160, y, t, f, (150, 150, 152))
        y += 104
    d.ellipse((70, y + 8, 126, y + 64), outline=(190, 190, 192), width=4)
    for t in lines(text):
        say(im, 160, y, t, fit(t, HELV, 58, 1, 850), (10, 10, 10))
        y += 78
    y += 34
    for t in ad.get("after") or []:
        say(im, 160, y, t, fit(t, HELV, 50, 0, 850), (60, 60, 62))
        y += 66
    attach(sp, ad, im, y + 30)
    return im


def d_thread(sp, ad, text, i):
    """A text thread. `thread` is the turns, {"who": "me"|"them", "text"|"photo"}; "{line}" is the line that changes."""
    from PIL import Image, ImageDraw, ImageOps
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d, grey = ImageDraw.Draw(im), (142, 142, 147)
    d.rectangle((0, 0, W, 430), fill=(247, 247, 249))
    d.line((0, 430, W, 430), fill=(214, 214, 217), width=2)
    d.ellipse((480, 220, 600, 340), fill=(166, 170, 180))
    d.text((540, 280), (ad.get("contact") or "?")[0], font=font(HELV, 62, 1), fill="white", anchor="mm")
    d.text((540, 386), ad.get("contact") or "", font=font(HELV, 36), fill=(20, 20, 20), anchor="mm")
    d.text((70, 280), "‹", font=font(HELV, 90), fill=(0, 122, 255), anchor="lm")
    d.text((540, 486), ad.get("when") or "", font=font(HELV, 32), fill=grey, anchor="mm")
    y, f = 540, font(HELV, 46)
    for m in ad.get("thread") or []:
        mine = m["who"] == "me"
        if m.get("photo"):
            ph = ImageOps.fit(ImageOps.exif_transpose(Image.open(pic(sp, m["photo"]))).convert("RGB"), (m.get("w", 420), m.get("h", 420)), Image.LANCZOS, centering=tuple(m.get("at", (.5, .5))))
            mk = Image.new("L", ph.size, 0)
            ImageDraw.Draw(mk).rounded_rectangle((0, 0, ph.width - 1, ph.height - 1), 40, fill=255)
            x, cap = W - 50 - ph.width if mine else 50, m.get("caption") or []
            if cap:                                      # a link card: the picture over its grey caption
                full = ph.height + 34 + 54 * len(cap)
                d.rounded_rectangle((x, y, x + ph.width, y + full), 40, fill=(233, 233, 235))
                im.paste(ph, (x, y), mk)
                d.rectangle((x, y + ph.height - 40, x + ph.width, y + ph.height), fill=(233, 233, 235))
                im.paste(ph.crop((0, ph.height - 40, ph.width, ph.height)), (x, y + ph.height - 40))
                for j, t in enumerate(cap):
                    d.text((x + 30, y + ph.height + 14 + 54 * j), t, font=fit(t, HELV, 42 if j == 0 else 34, 1 if j == 0 else 0, ph.width - 60), fill=(15, 15, 15) if j == 0 else (110, 110, 115))
                y += full + 22
            else:
                im.paste(ph, (x, y), mk)
                y += ph.height + 22
            continue
        ls = []
        for part in lines(m["text"].replace("{line}", text)):
            ls += wrap(part, f, 720)
        w = max(said_width(t, f) for t in ls)
        h = 58 * len(ls) + 44
        x = W - 50 - w - 72 if mine else 50
        d.rounded_rectangle((x, y, x + w + 72, y + h), 44, fill=(0, 122, 255) if mine else (233, 233, 235))
        for j, t in enumerate(ls):
            say(im, x + 36, y + 20 + 58 * j, t, f, "white" if mine else (10, 10, 10))
        y += h + (14 if m.get("close") else 30)
    if y > (1560 if offer_bubble(sp, ad) else 1700):
        raise SystemExit("%s: the thread is too long for one picture, take a turn out" % ad["id"])
    return bubbles(im, offer_bubble(sp, ad), ad.get("offer_top", .845))


def d_search(sp, ad, text, i):
    """A search, what it suggests, and the one answer. No search company's name or look."""
    from PIL import Image, ImageDraw, ImageOps
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d, grey = ImageDraw.Draw(im), (120, 124, 130)

    def glass(x, y, r, c):
        d.ellipse((x - r, y - r, x + r, y + r), outline=c, width=5)
        d.line((x + r * .7, y + r * .7, x + r * 1.6, y + r * 1.6), fill=c, width=6)

    f = fit(text, HELV, 50, 0, 780)
    d.rounded_rectangle((50, 250, 1030, 366), 58, outline=(205, 208, 212), width=3, fill=(250, 250, 251))
    glass(116, 302, 18, grey)
    d.text((172, 308), text, font=f, fill=(15, 15, 15), anchor="lm")
    d.line((178 + f.getlength(text), 280, 178 + f.getlength(text), 336), fill=(0, 122, 255), width=4)
    y = 400
    for t in ad.get("body") or []:
        glass(116, y + 34, 14, (170, 174, 180))
        d.text((172, y + 40), t, font=fit(t, HELV, 44, 1, 820), fill=(40, 42, 46), anchor="lm")
        y += 92
    y += 30
    ph = ImageOps.fit(ImageOps.exif_transpose(Image.open(pic(sp, ad["photo"]))).convert("RGB"), (980, ad.get("photo_h", 620)), Image.LANCZOS, centering=tuple(ad.get("at", (.5, .5))))
    m = Image.new("L", ph.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, ph.width - 1, ph.height - 1), 30, fill=255)
    im.paste(ph, (50, y), m)
    y += ph.height + 34
    for j, t in enumerate(ad.get("after") or []):
        d.text((56, y), t, font=fit(t, HELV, 56 if j == 0 else 42, 1 if j == 0 else 0, 960), fill=(15, 15, 15) if j == 0 else (70, 72, 76))
        y += 76 if j == 0 else 60
    return im


def d_comments(sp, ad, text, i):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), (18, 20, 22))
    d, grey = ImageDraw.Draw(im), (150, 154, 158)
    d.text((W / 2, 215), text, font=fit(text, AVN, 82, 8, 940), fill="white", anchor="ma")
    if ad.get("sub"):                                          # no small print under the headline unless an ad says one
        d.text((W / 2, 352), ad["sub"], font=font(HELV, 32), fill=grey, anchor="ma")
    d.line((0, 425, W, 425), fill=(46, 49, 52), width=2)
    f, y = font(HELV, 42), 470
    tint = [(70, 78, 82), (92, 74, 60), (58, 84, 74), (84, 70, 88), (66, 72, 96), (96, 84, 56)]
    for k, c in enumerate(ad.get("comments") or []):
        ls = wrap(c["text"], f, 740)
        if y + 42 + 52 * len(ls) > 1590:
            raise SystemExit("%s: too many comments for one picture, take one out" % ad["id"])
        d.ellipse((64, y, 140, y + 76), fill=tint[k % 6])
        d.rounded_rectangle((170, y + 6, 170 + [190, 230, 160, 210, 180, 240][k % 6], y + 30), 12, fill=(58, 62, 66))
        for j, q in enumerate(ls):
            d.text((170, y + 42 + j * 52), q, font=f, fill=(240, 242, 243))
        pts = []
        for s in range(0 if ad.get("no_hearts") else 61):
            t = s * math.pi / 30
            pts.append((1000 + 15 * math.sin(t) ** 3, y + 62 - 15 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 16))
        if pts:
            d.line(pts, fill=grey, width=3)
        if c.get("likes"):
            d.text((1000, y + 86), str(c["likes"]), font=font(HELV, 28), fill=grey, anchor="ma")
        y += 88 + 52 * len(ls)
    return bubbles(im, offer_bubble(sp, ad), .845)


def d_plate(sp, ad, text, i):
    from PIL import Image, ImageDraw, ImageOps
    ls = lines(text)
    im = Image.new("RGB", (W, H), NIGHT)
    ph = ImageOps.fit(ImageOps.exif_transpose(Image.open(pic(sp, ad["photo"]))).convert("RGB"), (W, ad.get("photo_h", 1200)), Image.LANCZOS)
    ph_h, m = ph.height, Image.new("L", ph.size, 255)
    d, dark = ImageDraw.Draw(m), ad.get("fade_from", 0)        # fade_from: how far down the picture starts to show
    for y in range(ph_h):
        d.line((0, y, W, y), fill=int(255 * max(0, min(1, (y - dark) / 150)) * min(1, (ph_h - 1 - y) / 110)))
    im.paste(ph, (0, ad.get("photo_y", 560)), m)
    glow_text(im, (W / 2, 300), ls[0], fit(ls[0], AVN, 116, 8, 940))
    for j, t in enumerate(ls[1:]):
        glow_text(im, (W / 2, 452 + j * 70), t, fit(t, AVN, 58, 5, 920))
    p = ad.get("plates") or [sp["offer"], (sp.get("moment") or "") and "%s%s" % (sp["moment"].upper(), ("  ENDS " + sp["until"].upper()) if sp.get("until") else "")]
    boxes = ad.get("boxes") or [(116, 1340, 964, 1450), (116, 1480, 964, 1590)]   # over a plate already in the picture
    for b, t in zip(boxes, p):
        if t:
            gold(im, tuple(b), t, 54)
    return im


DRAW = {"story": d_story, "tag": d_tag, "letter": d_letter, "note": d_note, "comments": d_comments, "plate": d_plate, "list": d_list, "thread": d_thread, "search": d_search}


def draft(sp, only=None, every=False):
    from PIL import Image
    out = sp["_dir"] / "drafts"
    out.mkdir(exist_ok=True)
    made = []
    for ad in sp["ads"]:
        if only and ad["id"] not in only:
            continue
        row = []
        for i, t in enumerate(ad["lines"] if every else ad["lines"][:1]):
            im = DRAW[ad["layout"]](sp, ad, t, i).convert("RGB")
            if im.size != (W, H):
                raise SystemExit("%s: %s is %s, the approval page takes 1080 x 1920" % (ad["id"], name_of(i), im.size))
            f = out / ("%s-%s.png" % (ad["id"], name_of(i)))
            im.save(f)
            made.append(f)
            row.append(im.resize((300, 533)))
        if every:
            sheet = Image.new("RGB", (310 * len(row), 533), "white")
            for k, im in enumerate(row):
                sheet.paste(im, (310 * k, 0))
            sheet.save(out / ("%s-sheet.jpg" % ad["id"]), quality=85)
    return made


# --------------------------------------------------------------------------------------------------------- the page --
def page(sp):
    from PIL import Image
    e = html.escape
    d = sp["_dir"] / "page"
    (d / "dr").mkdir(parents=True, exist_ok=True)
    rows, md = "", ["# %s" % (sp.get("title") or sp["label"]), "", "%s · %s" % (sp.get("moment") or "", sp.get("offer") or ""), ""]
    for ad in sp["ads"]:
        figs = ""
        for i, t in enumerate(ad["lines"]):
            src = sp["_dir"] / "drafts" / ("%s-%s.png" % (ad["id"], name_of(i)))
            if not src.is_file():
                continue
            im = Image.open(src).convert("RGB")
            im.thumbnail((720, 1280))
            im.save(d / "dr" / (src.stem + ".jpg"), quality=84)
            figs += '<figure><img loading="lazy" src="dr/%s.jpg" alt="%s %s"><figcaption>%s</figcaption></figure>' % (src.stem, e(ad["title"]), name_of(i), "Control" if i == 0 else i)
        rows += '<section><header><b>%s</b><h2>%s</h2><em>%s</em></header><div class="row">%s</div></section>' % (e(ad["id"].upper()), e(ad["title"]), e(ad.get("why") or ""), figs)
        md += ["## %s · %s" % (ad["id"].upper(), ad["title"]), "Why: %s" % ad.get("why"), "Receipt: %s" % ad.get("receipt")] + ["- %s: %s" % (name_of(i), t) for i, t in enumerate(ad["lines"])] + [""]
    c = sp.get("copy") or {}
    copy = "".join("<details open><summary>Text %d</summary><p>%s</p></details>" % (i + 1, e(x)) for i, x in enumerate(c.get("primary") or []))
    copy += "<p><b>Headlines</b><br>%s</p><p><b>Descriptions</b><br>%s</p>" % ("<br>".join(e(x) for x in c.get("headlines") or []), "<br>".join(e(x) for x in c.get("descriptions") or []))
    md += ["## Ad copy", ""] + list(c.get("primary") or []) + ["Headlines: " + " | ".join(c.get("headlines") or []), "Descriptions: " + " | ".join(c.get("descriptions") or [])]
    title = e(sp.get("title") or sp["label"])
    (d / "page.html").write_text('''<title>%s</title>
<style>
:root{--bg:#f1f4f1;--panel:#fff;--ink:#101a16;--mute:#5b6862;--line:#d5ddd8;--em:#0d5a3c;--soft:#e2ece6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0c100f;--panel:#141a18;--ink:#f2f6ea;--mute:#9aa8a0;--line:#26302c;--em:#7fd0a8;--soft:#16241e;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0c100f;--panel:#141a18;--ink:#f2f6ea;--mute:#9aa8a0;--line:#26302c;--em:#7fd0a8;--soft:#16241e;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:500 15px/1.4 "Archivo",system-ui,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:22px 16px 56px;display:flex;flex-direction:column;gap:28px}
h1{font-size:28px;margin:0}h2{font-size:18px;margin:0}.now{background:var(--soft);border:1px solid var(--em);border-radius:10px;padding:12px 14px;font-weight:700}
header{display:flex;gap:10px;align-items:center;flex-wrap:wrap}header b{border:1px solid var(--ink);border-radius:99px;min-width:28px;text-align:center}em{font-style:normal;color:var(--mute)}
section{display:flex;flex-direction:column;gap:10px;min-width:0}.row{display:flex;gap:12px;overflow-x:auto}figure{margin:0;flex:none;width:min(62vw,236px)}img{width:100%%;border-radius:9px;border:1px solid var(--line);display:block}
figcaption{color:var(--mute);font-size:13px;margin-top:6px}article{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}details p{white-space:pre-line}
</style><div class="wrap"><h1>%s</h1><div class="now">%s</div>%s<article><h2>Ad copy</h2>%s</article></div>''' % (title, title, e(sp.get("now") or "Your look"), rows, copy))
    (d / (sp["label"] + ".md")).write_text("\n".join(md))
    return d / "page.html"


# ---------------------------------------------------------------------------------------------- number, file, status --
def run_dir(sp, ad):
    return REPO / "runs" / "ad-variations" / sp["brand"] / ("%s-ad-%s" % (sp["label"], ad["id"]))


def key_of(sp, brief):
    return "%s_%s_%s" % (sp["brand"], sp["product"], brief)


def manifest(sp, ad, brief):
    """One ad as a design assignment: the first picture is made; the designer makes the five versions, one line changed."""
    key, rel = key_of(sp, brief), lambda f: str(Path(f).resolve().relative_to(REPO))
    rows = "\n".join("| v%d | %s |" % (i, t) for i, t in enumerate(ad["lines"][1:], 1))
    emo = ad.get("emoji") or []
    if emo:
        rows = "\n".join("| v%d | %s %s |" % (i, t, emo[i] if i < len(emo) else "") for i, t in enumerate(ad["lines"][1:], 1))
    refs = [{"path": rel(sp["_dir"] / "drafts" / ("%s-control.png" % ad["id"])), "role": "the first picture: match it"}]
    for q, role in [(ad.get("photo"), "the photo under the words"), ((ad.get("picture") or {}).get("path"), "the picture in the note"), (ad.get("cutout"), "the product cutout")] + [
            (m.get("photo"), "the picture in the thread") for m in ad.get("thread") or []]:
        if q:
            refs.append({"path": rel(pic(sp, q)), "role": role})
    brief_md = "\n".join([
        "%s. Offer: %s. Runs to %s." % (sp.get("moment") or "", sp["offer"], sp.get("until") or ""), "",
        "Why it sells: %s." % ad["why"], "",
        "## Make five versions", "",
        "The first picture says **%s**. Each version is the same picture with only that line changed. ` / ` is a line break. Words are exact, letter for letter." % ad["lines"][0], "",
        "| Version | The line |", "|---|---|", rows, "",
        "## Keep", "", "- Same photo, same place, same type and sizes as the first picture. Resize the line only if it does not fit.",
        "- Every other word stays as it is, %s included." % sp["offer"], "- 1080 x 1920, nothing important in the top 14% or bottom 20%.", "",
        "## Return", "", "In `returned/`: " + ", ".join("`%s-v%d.png`" % (key, i) for i in range(1, 6)) + ". The checklist's `control` is the first picture, `refs/01-%s-control.png`, unchanged." % ad["id"]])
    return {"id": key, "brand": sp["brand"], "product": sp["product"], "stage": "production", "source_id": key, "title": "%s · %s" % (brief, ad["title"]),
            "brief": brief_md, "next_action": "Make the five versions in BRIEF.md from the first picture and return them.", "references": refs}


def assign(sp, only=None, publish=False):
    """Each ad's five versions to the graphic designer: the assignment folder, its checklist, and (publish) the Drive."""
    have = json.loads((sp["_dir"] / "briefs.json").read_text())
    for p in ("image-edit", "briefs"):
        sys.path.append(str(REPO / "components" / p))
    from image_edit import assignment as AS
    import delivery_contract as DC
    md, out = sp["_dir"] / "manifests", []
    md.mkdir(exist_ok=True)
    for ad in sp["ads"]:
        if only and ad["id"] not in only:
            continue
        key = key_of(sp, have[ad["id"]])
        f = md / (key + ".json")
        f.write_text(json.dumps(manifest(sp, ad, have[ad["id"]]), indent=1, ensure_ascii=False))
        folder, sheet = AS.build(f, repo=REPO)
        DC.pack(folder, "graphic-designer", slots=[{"id": "slot-%02d" % (i + 1), "label": name_of(i), "kind": "image", "cover_required": False} for i in range(6)])
        out.append((ad["id"], key, AS.publish(folder, sheet, repo=REPO)["link"] if publish else "packed, not sent"))
    return out


def number(sp):
    import shutil
    f = sp["_dir"] / "briefs.json"
    have = json.loads(f.read_text()) if f.is_file() else {}
    for ad in sp["ads"]:
        run = run_dir(sp, ad)
        dl = run / "deliverable"
        dl.mkdir(parents=True, exist_ok=True)
        for i in range(len(ad["lines"])):
            src = sp["_dir"] / "drafts" / ("%s-%s.png" % (ad["id"], name_of(i)))
            if src.is_file():                             # the first picture; the versions come back from the designer
                shutil.copy2(str(src), str(dl / ("%02d-%s.png" % (i + 1, name_of(i)))))
        aim = aim_of(sp, ad)
        for_who = " · ".join(str(aim[k]) for k in ("avatar", "sub", "demographic", "awareness", "desire", "doubt") if aim.get(k))
        (dl / "brief.md").write_text("# %s · %s\n\nFor: %s.\n\n%s. Why it sells: %s. Receipt: %s.\n\n%s\n\nMade by components/ad-variations/machine/natural_statics.py: a picture we own with the words set in code.\n" % (
            ad["title"], sp.get("moment") or "", for_who, sp["offer"], ad.get("why"), ad.get("receipt"), "\n".join("- %s: %s" % (name_of(i), t) for i, t in enumerate(ad["lines"]))))
        (run / "run.json").write_text(json.dumps({"brand": sp["brand"], "product": sp["product"], "avatar": aim["avatar"], "sprint": sp["label"], "ad": ad["id"], "aim": aim}, indent=1))
        import brandctx as BC
        for d_ in (run, dl):                              # the full profile travels with the run and with what the designer opens
            BC.who().attach(d_, sp["brand"], aim["avatar"], aim.get("sub"), aim.get("demographic"), {k: aim.get(k) for k in ("desire", "awareness", "stage", "doubt", "claim")})
        if ad["id"] in have:
            continue
        r = subprocess.run([sys.executable, "components/image-teardown/tools/briefs.py", "open", str(run.relative_to(REPO)), "--brand", sp["brand"], "--product", sp["product"],
                            "--avatar", aim["avatar"], "--type", "image-ai", "--link", sp["page"]], cwd=str(REPO), capture_output=True, text=True, env=dict(os.environ, NAMING_ANGLE_PICK="off"))
        m = re.search(r"\bbrief-\d{4}\b", r.stdout + r.stderr)
        if not m:
            raise SystemExit("%s: no number: %s" % (ad["id"], (r.stdout + r.stderr)[-300:]))
        have[ad["id"]] = m.group(0)
        f.write_text(json.dumps(have, indent=1))
    return have


def file_cards(sp, only=None, replace=False, dry=False):
    have = json.loads((sp["_dir"] / "briefs.json").read_text())
    wf = sp["_dir"] / "words.json"
    wf.write_text(json.dumps({k: (sp["copy"].get(k) or []) for k in ("primary", "headlines", "descriptions")}, indent=1, ensure_ascii=False))
    out = []
    for ad in sp["ads"]:
        if only and ad["id"] not in only:
            continue
        run = run_dir(sp, ad)
        mine = wf
        if ad.get("copy"):                                # this ad speaks to one sub-avatar: its own words
            mine = sp["_dir"] / ("words-%s.json" % ad["id"])
            mine.write_text(json.dumps({k: (ad["copy"].get(k) or []) for k in ("primary", "headlines", "descriptions")}, indent=1, ensure_ascii=False))
        n = len(list((run / "deliverable").glob("*.png")))
        if n != 6:
            out.append((ad["id"], have[ad["id"]], 1, "%d pictures here, an ad files with six: the designer's five are not in yet" % n))
            continue
        cmd = [sys.executable, str(META / "to_check.py"), "--brand", sp["brand"], "--lane", "image", "--product", sp["product"], "--brief", have[ad["id"]], "--batch", sp["batch"],
               "--avatar", sp["avatar"], "--angle", sp["angle"], "--media"] + sorted(str(x) for x in (run / "deliverable").glob("*.png")) + [
               "--words", str(mine), "--links", sp["page"], "--tool", "ad-variations", "--run", str(run.relative_to(REPO))]
        cmd += (["--replace"] if replace else []) + (["--dry-run"] if dry else [])
        r = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
        out.append((ad["id"], have[ad["id"]], r.returncode, (r.stdout + r.stderr).strip()))
    return out


def status(sp, port=8795):
    import urllib.request
    have = json.loads((sp["_dir"] / "briefs.json").read_text())
    d = json.load(urllib.request.urlopen("http://127.0.0.1:%d/api/cards?brand=%s" % (port, sp["brand"]), timeout=120))
    want, rows = set(sp["copy"].get("primary") or []), []
    for c in d["cards"]:
        for i, b in have.items():
            if "_%s_" % b in c["ad_name"]:
                bad = [str(x.get("key") or x.get("label")) for x in c["checks"] if not x.get("ok")]
                rows.append({"ad": i, "brief": b, "ready": not bad, "failing": bad, "copy_checked": c.get("copy_checked"),
                             "our_copy": set((c.get("words") or {}).get("primary") or []) == want, "pictures": len(c.get("media") or [])})
    return rows


# ------------------------------------------------------------------------------------------------------- reading --
def comments(brand, ads, limit=100):
    for p in ("funnel-tracking/machine", "meta-upload"):
        sys.path.append(str(REPO / "components" / p))
    from meta import Meta
    m, rows = Meta(brand), []
    for a in ads:
        try:
            c = m.get(str(a), fields="creative{effective_instagram_media_id}")["creative"]
            got = m.get(c["effective_instagram_media_id"] + "/comments", fields="text,like_count", limit=limit)["data"]
            rows += [{"ad": str(a), "likes": x.get("like_count") or 0, "text": x.get("text") or ""} for x in got]
        except BaseException as ex:  # noqa: BLE001  the Meta helper exits on an error; the other ads still read
            print("%s: %s" % (a, str(ex)[:140]), file=sys.stderr)
    return sorted(rows, key=lambda r: -r["likes"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = ap.add_subparsers(dest="do", required=True)
    q = s.add_parser("start")
    for k in ("brand", "product", "avatar", "label"):
        q.add_argument("--" + k, required=True)
    q = s.add_parser("comments")
    q.add_argument("--brand", required=True)
    q.add_argument("--ads", nargs="+", required=True)
    for k in ("who", "copy", "check", "draft", "assign", "page", "number", "file", "status"):
        q = s.add_parser(k)
        q.add_argument("sprint")
        if k in ("who", "draft", "file", "assign"):
            q.add_argument("--only", nargs="+")
        if k == "draft":
            q.add_argument("--all", action="store_true")
        if k == "assign":
            q.add_argument("--publish", action="store_true")
        if k == "copy":
            q.add_argument("--search")
        if k == "file":
            q.add_argument("--replace", action="store_true")
            q.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.do == "start":
        print(start(a)); return 0
    if a.do == "comments":
        for r in comments(a.brand, a.ads):
            print("%4d  %s  %s" % (r["likes"], r["ad"], r["text"].replace("\n", " ")[:300]))
        return 0
    sp = load(a.sprint)
    if a.do == "who":
        for ad in sp["ads"]:
            if not a.only or ad["id"] in a.only:
                print("# %s\n\n%s" % (ad["id"], who_text(sp, ad)))
        return 0
    if a.do == "copy":
        for k, rows in ran_lines(sp["brand"]).items():
            print("\n##", k)
            for o in rows:
                t = o["text"]
                if any(n.lower() in t.lower() for n in sp.get("never") or []) or (a.search and not re.search(a.search, t, re.I)):
                    continue
                print("%s  %s sales  $%s  %s" % (o["id"], o.get("purchases"), o.get("cpa"), t[:400].replace("\n", " ")))
        return 0
    bad = check(sp)
    if a.do == "check":
        bad += check_copy(sp)
        print("\n".join(bad) or "clean: %d ads, %d pictures" % (len(sp["ads"]), sum(len(x["lines"]) for x in sp["ads"])))
        return 1 if bad else 0
    if a.do == "status":
        for r in status(sp):
            print(json.dumps(r))
        return 0
    if bad:
        print("\n".join(bad)); return 1
    if a.do == "draft":
        print("\n".join(str(f) for f in draft(sp, a.only, a.all)))
    elif a.do == "assign":
        for row in assign(sp, a.only, a.publish):
            print("%s  %s  %s" % row)
    elif a.do == "page":
        print(page(sp))
    elif a.do == "number":
        print(json.dumps(number(sp)))
    elif a.do == "file":
        bad = check_copy(sp)
        if bad:
            print("\n".join(bad)); return 1
        rc = 0
        for i, b, code, o in file_cards(sp, a.only, a.replace, a.dry_run):
            print("## %s %s %s\n%s" % (i, b, "ok" if code == 0 else "REFUSED", o[-900:]))
            rc = rc or code
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
