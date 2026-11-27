#!/usr/bin/env python3
"""Where on the body a product may be used: the one door every tool reads (anatomy.json for the parts, the brand's
body-parts.json for the yes and no). Reads only; no model; nothing here names a brand or a product.

    body.py <brand> [<product> [<part>]]

The brand's filed list wins (`brands/<brand>/products/body-parts.json`), else the draft
(`runs/creative-strategist/<brand>/products/body-parts.json`). A product with no list has no rule: every answer is None
or empty and nothing is stopped. A set is what its members are: it fits where any member fits.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import anatomy as A  # noqa: E402

ROOT = HERE.parents[1]
USE = r"\b(?:us(?:e|es|ed|ing)|scrub(?:s|bed|bing)?|wash(?:es|ed|ing)?|brush(?:es|ed|ing)?|exfoliat(?:e|es|ed|ing)|massag(?:e|es|ed|ing)|rub(?:s|bed|bing)?|appl(?:y|ies|ied|ying)|put(?:s|ting)?|glid(?:e|es|ed|ing)|run(?:s|ning)?|work(?:s|ed|ing)?)\b"
NOT = re.compile(r"\b(not|never|no|don.?t|doesn.?t|isn.?t|won.?t|can.?t|cannot|without|avoid\w*|except|instead of|keep (it )?(off|away))\b", re.I)
HELD = ("palms", "fingers", "nails", "backs-of-hands", "wrists")          # what holds a product is not where it is used


def load(brand, root=None):
    """{product: {part: {"ok": yes|no, "from": why}}}"""
    r = Path(root or ROOT)
    for f in (r / "brands" / str(brand) / "products" / "body-parts.json", r / "runs" / "creative-strategist" / str(brand) / "products" / "body-parts.json"):
        try:
            return json.loads(f.read_text())["products"]
        except (OSError, ValueError, KeyError):
            continue
    return {}


SIGNED = "The owner's signed list of where this product may be used. It wins over any older line about where it goes, and what it allows is never a question. "


def signed(brand, root=None):
    return (Path(root or ROOT) / "brands" / str(brand) / "products" / "body-parts.json").is_file()


def members(brand, product, root=None):
    """The listed products a name means: itself, the one it is another name for, or what a set holds. [] when it has no list."""
    book, p = load(brand, root), Path(str(product or "")).stem.replace("_", "-").lower()
    if p in ("product", "readme"):                                       # .../<product>/product.md
        p = Path(str(product)).parent.name
    if not p or not book:
        return []
    if p in book:
        return [p]
    try:
        import names
        pid = names.product_id(brand, p)
    except Exception:                                        # noqa: BLE001 -- a name nobody knows has no list
        pid = None
    if pid in book:
        return [pid]
    if not re.search(r"\b(set|bundle|kit|trio|duo)\b", p.replace("-", " ")):
        return []
    f = Path(root or ROOT) / "brands" / str(brand) / "products" / (p + ".md")
    t = f.read_text().lower() if f.is_file() else ""
    return [k for k in book if k in t or re.search(r"\b%s\b" % re.escape(k.split("-")[0]), t)]


def parts(brand, product, want="yes", root=None):
    """The parts marked `want`. For a set: yes is any member's yes, no is every member's no."""
    book, ms = load(brand, root), members(brand, product, root)
    got = [{x for x, m in book[k].items() if m.get("ok") == want} for k in ms]
    if not got:
        return []
    s = set.union(*got) if want == "yes" else set.intersection(*got)
    return [x for x in A.parts() if x in s]


def why_not(brand, product, spot, root=None):
    """None when the product may be used there, when it has no list, or when no spot is named; else the reason it may not.
    A spot that is a group (arms) fits when some of it is marked yes; the parts of it marked no stay out (rule says which)."""
    if not spot or not members(brand, product, root):
        return None
    mine = A.open_(spot)
    if not mine:
        return "%s is not a part of the body on file (components/naming/anatomy.py list)" % spot
    ok, no = parts(brand, product, "yes", root), parts(brand, product, "no", root)
    if any(x in ok for x in mine):
        return None
    if any(x in no for x in mine):
        return "%s is ruled out for %s" % (product, spot.replace("-", " "))
    return "%s is not ruled for %s (ruled: %s)" % (product, spot.replace("-", " "), ", ".join(ok) or "nowhere")


def say(ids):
    """Parts in few words: a group that is all there is said once."""
    out, left = [], list(ids)
    for g, ps in A.groups().items():
        if len(ps) > 1 and all(p in left for p in ps):
            out.append("all of the " + g.replace("-", " "))
            left = [x for x in left if x not in ps]
    return ", ".join(out + [x.replace("-", " ") for x in left])


def together(brand, product, spot, root=None):
    """The parts close to this one (anatomy.json regions) that may be mentioned with it: never one ruled out for the product."""
    no = parts(brand, product, "no", root)
    return [x for x in A.together(spot) if x not in no]


def rule(brand, product, spot="", root=None):
    """One line for a writer, a picture, a clip or a judge. "" when the product has no list."""
    if not members(brand, product, root):
        return ""
    no = say(parts(brand, product, "no", root))
    if spot:
        near = together(brand, product, spot, root)
        out = [x for x in A.open_(spot) if x in parts(brand, product, "no", root)]
        return "%sThis piece is about the %s%s.%s No place further off is shown being treated or claimed." % (SIGNED if signed(brand, root) else "", spot.replace("-", " "), (" (never the %s)" % ", ".join(x.replace("-", " ") for x in out)) if out else "", (" Places close by may be mentioned with it: %s." % ", ".join(x.replace("-", " ") for x in near)) if near else "")
    return "%sUsed only on: %s.%s" % (SIGNED if signed(brand, root) else "", say(parts(brand, product, "yes", root)), (" Never shown used on, or claimed for: %s. Holding it in the hand is fine." % no) if no else "")


def misuse(brand, product, text, root=None):
    """[(sentence, part)]: a sentence that puts THIS product on a part ruled out for it. It must say so outright: a use
    word, then the product ("it", "this", or its name), then on/over/across the part. A part that is only talked about, a
    habit from before, and a sentence saying no are never read as use: a wrong hold costs more than a missed maybe, and
    the judges that read the whole piece are given the rule too."""
    ms = members(brand, product, root)
    no = [x for x in parts(brand, product, "no", root) if x not in HELD]
    if not no:
        return []
    called = "|".join(["it", "this", "the same \\w+"] + [re.escape(k.split("-")[0]) for k in ms] + [re.escape(k.replace("-", " ")) for k in ms])
    out = []
    for s in re.split(r"(?<=[.!?])\s+|\n+", str(text or "")):
        if NOT.search(s):
            continue
        for x in no:
            if re.search(USE + r"\s+(?:the |our |your |my )?(?:" + called + r")\b(?:\W+\w+){0,3}?\W+(?:on|onto|over|across|into|all over)\s+(?:(?:your|my|his|her|their|the|both|whole|dry|clean|wet)\s+){0,3}(?:" + A.parts()[x]["words"] + r")\b", s, re.I):
                out.append((s.strip(), x))
    return out


def problems(brand, product, text, root=None):
    return ["%s is ruled out for %s: “%s”" % (x.replace("-", " "), product, s[:160]) for s, x in misuse(brand, product, text, root)]


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or len(a) > 3:
        print(__doc__)
        return 2
    if len(a) == 1:
        for k in load(a[0]):
            print("%-26s %d yes, %d no" % (k, len(parts(a[0], k)), len(parts(a[0], k, "no"))))
    else:
        bad = why_not(a[0], a[1], a[2]) if len(a) == 3 else None
        print(bad or rule(a[0], a[1], a[2] if len(a) == 3 else "") or "no list for " + a[1])
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
