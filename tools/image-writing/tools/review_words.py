"""A real customer review handed in as the swipe: its words are fixed, quoted as given, never rewritten.

the owner, 2026-10-26: one of his best ads was "a swipe of a real customer review i had", so real reviews were made into
review cards and run through the teardown. the owner, 2026-10-27, on one of those briefs: "this is not a swipe. This is the
actual review. So in this case, we would not wanna make anything up."

    is_review(run)      the swipe is a real review (its source block is review-<id>, or the run is named -review-)
    fixed_words(run)    the review's words, zone by zone, as the teardown read them off the card (stage 1's
                        "Text (verbatim)" column)
    block(run)          prompts/review-words-vN-owner.md with the words in, riding on the end of each writing step
    problems(run)       a fixed line the brief does not carry word for word (checked after step 6)
"""
import json
import re
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def is_review(run):
    run = Path(run)
    try:
        block = json.loads((run / "assets" / "source.json").read_text()).get("block") or ""
    except (OSError, ValueError):
        block = ""
    return block.startswith("review-") or "-review-" in run.name


def fixed_words(run):
    """[(zone, words)] from the teardown's zone table: every row whose verbatim text is not "none"."""
    f = Path(run) / "out" / "01-teardown.md"
    if not f.is_file():
        return []
    lines = f.read_text(errors="replace").splitlines()
    head = next((i for i, l in enumerate(lines) if l.startswith("|") and "Text (verbatim)" in l), None)
    if head is None:
        return []
    col = [c.strip() for c in lines[head].strip("|").split("|")].index("Text (verbatim)")
    out = []
    for l in lines[head + 2:]:
        if not l.startswith("|"):
            break
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) > col and cells[col] and cells[col].lower() != "none":
            out.append((cells[0], cells[col].strip("`\"")))
    return out


def _newest():
    got = sorted(PROMPTS.glob("review-words-v*-owner.md"), key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    return got[-1]


def block(run):
    words = fixed_words(run)
    if not (is_review(run) and words):
        return ""
    return _newest().read_text().replace("{review_words}", "\n".join(f"- {z}: `{w}`" for z, w in words))


def _flat(s):
    return " ".join(re.sub(r"\s*/\s*", " ", s.replace("`", " ")).split())   # line breaks, backticks and spacing aside


def problems(run, brief=None):
    """A fixed line missing from the brief's built part, word for word (line breaks and spacing aside)."""
    if not is_review(run):
        return []
    if brief is None:
        f = Path(run) / "out" / "06-brief.md"
        brief = f.read_text(errors="replace") if f.is_file() else ""
    m = re.search(r"^##\s*DOCUMENT THREE\b", brief, re.M | re.I)
    have = _flat(brief[:m.start()] if m else brief)
    return [f"real review: {z} is not on the ad word for word (`{w}`); a review's words are never rewritten"
            for z, w in fixed_words(run) if _flat(w) not in have]
