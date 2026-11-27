"""One script everywhere: a scene's spoken lines, each with its speaker, read and written the same way by the
storyboard, the production workflow (take-N.json) and the print sheet (take.json).

Written form, one line per spoken line:
    HOST: Smash or pass?
    RATER: Ew, bumpy face, pass. Hard pass.
A scene with one voice is written as plain words, no name.

    lines(text, old)  -> [{"speaker", "say"}]   reads the written form; plain words over several old lines are laid
                                                back onto those lines word by word, so an edit stays on its line
    written(lines)    -> the written form
Python 3.9."""
import difflib
import re

NAME = re.compile(r"^\s*([A-Z][A-Z0-9]*(?: [A-Z0-9]+){0,2})\s*:\s*(.*)$")


def written(rows):
    rows = [r for r in rows or [] if (r.get("say") or "").strip()]
    if len({r.get("speaker") or "" for r in rows}) <= 1:
        return " ".join(r["say"].strip() for r in rows)
    return "\n".join((r["speaker"] + ": " if r.get("speaker") else "") + r["say"].strip() for r in rows)


def _named(text):
    out = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        m = NAME.match(raw)
        if m:
            out.append({"speaker": m[1], "say": m[2].strip()})
        elif out:
            out[-1]["say"] = (out[-1]["say"] + " " + raw.strip()).strip()
        else:
            out.append({"speaker": "", "say": raw.strip()})
    return out


def _laid_on(text, old):
    """Plain words laid back onto the old lines: unchanged words keep their line, changed words take the line of the
    words they replace, added words join the line before them."""
    src = [(i, w) for i, r in enumerate(old) for w in (r.get("say") or "").split()]
    new = text.split()
    got = [[] for _ in old]
    sm = difflib.SequenceMatcher(a=[w for _, w in src], b=new, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "delete":
            continue
        for k in range(j2 - j1):
            if tag == "equal":
                at = src[i1 + k][0]
            elif tag == "replace":
                at = src[min(i2 - 1, i1 + k * (i2 - i1) // (j2 - j1))][0]
            else:
                at = src[i1 - 1][0] if i1 > 0 else (src[0][0] if src else 0)
            got[at].append(new[j1 + k])
    return [{"speaker": r.get("speaker") or "", "say": " ".join(g)} for r, g in zip(old, got) if g]


def lines(text, old=None, speaker=""):
    text = (text or "").strip()
    old = [r for r in old or [] if (r.get("say") or "").strip()]
    if not text:
        return []
    if any(NAME.match(raw) for raw in text.splitlines()):
        named = _named(text)
        if len(named) == 1 and not named[0]["speaker"]:
            named[0]["speaker"] = speaker
        return named
    if len({r.get("speaker") or "" for r in old}) > 1:
        return _laid_on(text, old)
    return [{"speaker": (old[0].get("speaker") if old else "") or speaker or "", "say": " ".join(text.split())}]


def plain(say):
    """The words as spoken: curly and straight quotes, dashes and spacing are the same line."""
    t = (say or "").translate(str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2014": "-", "\u2013": "-"}))
    return " ".join(t.split())


def same(a, b):
    key = lambda rows: [((r.get("speaker") or ""), plain(r.get("say"))) for r in rows or []]
    return key(a) == key(b)
