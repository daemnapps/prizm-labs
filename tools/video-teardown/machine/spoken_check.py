"""EVERY WORD IN A SPOKEN LINE IS A WORD (2026-10-01).

the owner, on "br- br-" read aloud as "bar, bar": "That's not a real word. Nobody
actually says that in real life, so that should have been flagged … find where
that issue happened … we solve for that, and you have to test it."

The transcript records stumbles as heard ("that really br- br- that little
bit") — that is right for a record and wrong for a script: a voice reads a
fragment as nonsense. This finds, without a model, the two shapes a fragment
takes in a line someone has to say:

  1. a cut-off word — letters ending in a hyphen with nothing joined after it
     ("br- ", "th-" at the end), never a real hyphenated word ("Mm-hmm");
  2. a repeated short token that is not a word ("br, br", "bar bar" is fine).

Used at the rewrite (our column only), on the brief's voice lines, and by
video-production before a voice is paid for. Brand-agnostic.

    python3 spoken_check.py "<text>"
"""
import re, sys
from pathlib import Path

CUT = re.compile(r"\b([A-Za-z]{1,6})-(?=\s|$|[\"'”.,!?…])")
REPEAT = re.compile(r"\b([A-Za-z]{1,4})\b[\s,.\-…]+\1\b", re.I)
FILLERS = {"mm", "hmm", "um", "uh", "ah", "oh", "eh", "huh", "mhm", "uhm", "er", "ok"}
_WORDS = None


def words():
    global _WORDS
    if _WORDS is None:
        f = Path("/usr/share/dict/words")
        _WORDS = {w.strip().lower() for w in f.read_text().splitlines()} if f.exists() else set()
        _WORDS |= FILLERS
    return _WORDS


def is_word(tok):
    t = tok.lower()
    return t in FILLERS or (t in words() and len(t) > 1) or t in {"a", "i"}


def fragments(text):
    """Every fragment in one spoken line, as short descriptions."""
    out = []
    for m in CUT.finditer(text or ""):
        out.append(f"cut-off word \"{m.group(0).strip()}\"")
    for m in REPEAT.finditer(text or ""):
        if not is_word(m.group(1)):
            out.append(f"repeated non-word \"{m.group(0).strip()}\"")
    return out


def check_lines(pairs):
    """pairs: [(id, spoken text)] → [{id, text, found}] for every line with a fragment."""
    return [{"id": i, "text": t, "found": f} for i, t in pairs if (f := fragments(t))]


if __name__ == "__main__":
    for line in sys.argv[1:]:
        print(line, "→", fragments(line) or "clean")
