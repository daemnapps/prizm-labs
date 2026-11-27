"""Does an email's layout follow the rules the designer agreed? (editor, 2026-11-23: Nov 44 and 45 "didn't follow the rules we agreed")

    python3 rules_check.py <run folder> [<run folder> ...]     prints every broken rule, by section

Reads design/email.json only; calls no model; changes nothing. Used by line.py after a layout (a broken rule sends the layout back once)
and by hand on any email. Each check is one agreed rule; a rule that is not about the layout (the words, the pictures) is not here.
"""
import json
import re
import sys
from pathlib import Path

GOLDS = ("#b19a6f", "#e3c892", "#d2bc8a", "#c9a24a", "#c9b493")


def _light(h):
    try:
        h = h.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return (0.299 * r + 0.587 * g + 0.114 * b) > 165
    except (ValueError, AttributeError, IndexError):
        return False


def _caps(s):
    if isinstance(s, (list, tuple)):
        s = " ".join(x for x in s if isinstance(x, str))
    if not isinstance(s, str):
        return False
    t = re.sub(r"<[^>]+>", "", s or "")
    letters = [c for c in t if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def check(spec, ruled_strip=None, recent=None):
    """[(section index or None, rule, what)] for every agreed rule this layout breaks."""
    out = []
    secs = spec.get("sections", [])
    add = lambda i, rule, what: out.append((i, rule, what))
    prev_bg = None
    for i, s in enumerate(secs):
        name = s.get("s")
        light = s.get("ink", "dark") == "dark" and not (s.get("bg") and not _light(s["bg"]))
        if name == "fg_band" or s.get("open_hero"):
            add(i, "flat colours only", "a gradient band or open hero fade (only when the designer names it)")
        if name == "fg_hero":
            tone = s.get("tone")
            if tone and len(tone) > 1 and str(tone[1]).lower() in GOLDS:
                add(i, "no gold text on a light ground", "the hero's second headline tone is gold")
            if _caps(s.get("headline")) or _caps(s.get("sub")):
                add(i, "normal case, never all capitals", "hero headline or line in capitals")
            if _caps(s.get("cta")) or "→" in (s.get("cta") or "") or "▶" in (s.get("cta") or ""):
                add(i, "buttons: normal case, no arrow", "hero button %r" % s.get("cta"))
            if s.get("photo_h") and not 700 <= int(s["photo_h"]) <= 1120:
                add(i, "tall hero (900 to 1100)", "hero height %s" % s["photo_h"])
        bg = s.get("bg")
        if name == "fg_block":
            if bg and prev_bg and bg.lower() == prev_bg.lower() and bg.lower() != "#b19a6f":
                add(i, "sections alternate colours", "the same colour %s as the section above" % bg)
            if bg:
                prev_bg = bg
            only_strip = bool(s.get("items")) and all(isinstance(x, dict) and x.get("t") == "marquee" for x in s["items"])
            for k in ("pad_top", "pad_bottom"):
                if not only_strip and k in s and int(s[k]) not in (0, 72, 56, 64, 40, 32, 16) and s.get("bg", "").lower() != "#b19a6f":
                    add(i, "72px above and below a section", "%s is %s" % (k, s[k]))
        for it in s.get("items", []) or []:
            if not isinstance(it, dict):
                continue
            t = it.get("t")
            if t == "headline":
                tone = it.get("tone")
                if _caps(" ".join(it.get("lines", []))):
                    add(i, "normal case, never all capitals", "headline %r" % " ".join(it.get("lines", []))[:50])
                if tone and len(tone) > 1 and str(tone[1]).lower() in GOLDS and light:
                    add(i, "no gold text on a light ground", "headline second tone is gold on a light section")
            elif t == "button":
                lab = it.get("label", "")
                if _caps(lab) or "→" in lab or "▶" in lab:
                    add(i, "buttons: normal case, no arrow", "button %r" % lab)
            elif t == "quote" and not it.get("plain"):
                add(i, "customer words as voice cards", "the older boxed quote with a Customer tag")
            elif t in ("freecard", "infographic") and not it.get("plain"):
                add(i, "no thin gold outlines", "%s with a gold outline (set plain: true)" % t)
            elif t == "minicard":
                if not it.get("flat"):
                    add(i, "flat colours only", "a gradient product box (set flat: true)")
                if str(it.get("ring", "")) not in ("transparent", "rgba(0,0,0,0)", "none"):
                    add(i, "no thin outlines", "outlined circles round the benefit icons (set ring: transparent)")
            elif t == "voicecards":
                if any(not isinstance(r.get("picture"), dict) for r in it.get("rows", [])):
                    add(i, "voice cards carry the creator's still", "a voice card with no still")
            elif t == "marquee" and ruled_strip and it.get("text") != ruled_strip:
                add(i, "the ruled top-strip wording", "strip says %r, the owner ruled %r" % (it.get("text"), ruled_strip))
            elif t == "label" and light and str(it.get("ink", "")).lower() in GOLDS:
                add(i, "no gold text on a light ground", "a gold label on a light section")
    # ingredients are never a big section
    for i, s in enumerate(secs):
        text = json.dumps(s).lower()
        if "ingredient" in text and any(isinstance(it, dict) and it.get("t") in ("pictures", "stackrows", "zigzag", "prodcards") for it in s.get("items", []) or []) \
                and "ingredient" in " ".join(" ".join(it.get("lines", [])) for it in s.get("items", []) or [] if isinstance(it, dict) and it.get("t") == "headline").lower():
            add(i, "ingredients are never a big section", "an ingredients section built from pictures or cards")
    first = secs[1] if len(secs) > 1 else {}
    if not any(isinstance(it, dict) and it.get("t") == "marquee" for sec in secs[1:3] for it in sec.get("items", []) or []):
        add(None, "gold strip under the header", "no marquee strip right under the header")
    if recent is not None:
        import directions as DR
        for p in DR.repeat_problems(spec, recent):
            add(None, "do not repeat a recent email", p)
    return out


def main(dirs):
    import line
    for d in dirs:
        d = Path(d).resolve()
        spec = json.loads((d / "design" / "email.json").read_text())
        brand = spec.get("brand") or d.parent.name
        rl = line.ruled_lines(brand, spec.get("date")) if hasattr(line, "ruled_lines") else {}
        import directions as DR
        rec = DR.recent(brand, line.REPO, exclude=d.name, before=spec.get("date"))
        found = check(spec, rl.get("top bar"), rec)
        print("== %s: %d broken rule(s)" % (d.name, len(found)))
        for i, rule, what in found:
            print("  %s  %-42s %s" % ("part %d" % (i + 1) if i is not None else "email  ", rule, what))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main(sys.argv[1:])
