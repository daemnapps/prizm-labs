"""The source-identity check: does anything of the swiped page survive in text we made from it?

Three tests, all deterministic (the model-read identity list is one input):
  1. ITEMS   every identity item (brand, person, place, offer, guarantee, cta, nav, heading, claim, phrase, contact,
             date) the teardown listed, plus the ones read straight off the capture (headings, buttons, links,
             furniture lines), searched in our text, case-insensitive, on word boundaries.
  2. RUNS    any run of 8+ words in a row shared with the source page (shorter shared runs are everyday phrasing
             like "one to two times a week"; the source's distinctive shorter phrases are in the identity list).
  3. NAMES   capitalised names on the source page (two or more capitalised words in a row) found in our text.

Generic words a page in this category needs anyway (one-word headings, "shop now", "learn more") are not identity on
their own, so items shorter than two words are only flagged when they are a brand, person, place or contact.
"""
import re

STRONG = {"brand", "person", "place", "contact"}
COMMON_NAMES = {"the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "with", "your", "our", "how", "what",
                "why", "when", "best", "is", "are", "it", "this", "that", "you", "we", "my"}


def norm(t):
    t = t.lower().replace("’", "'").replace("&amp;", "&")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9'&$%\s]", " ", t)).strip()


def from_capture(page_txt):
    """Identity read straight off the captured page, no model: headings, buttons, links, furniture lines."""
    items = []
    for ln in page_txt.splitlines():
        furn = re.match(r"^\[(NAV|HEADER|FOOTER|ASIDE|FURNITURE)\]\s*(.*)$", ln)
        body = furn.group(2) if furn else ln
        m = re.match(r"^#{1,6}\s+(.+)$", body)
        if m:
            items.append({"text": m.group(1).strip(), "kind": "nav" if furn else "heading", "from": "capture"})
            continue
        m = re.match(r"^\[(BUTTON|LINK): (.+?)(?: -> .*)?\]$", body)
        if m:
            items.append({"text": m.group(2).strip(), "kind": "nav" if furn else "cta", "from": "capture"})
            continue
        if furn and body and not body.startswith("[IMAGE"):
            items.append({"text": body.strip("- ").strip(), "kind": "nav", "from": "capture"})
    return items


def names_on(page_txt):
    found = set()
    for m in re.finditer(r"\b([A-Z][a-zA-Z'’.]+(?:\s+(?:&\s+)?[A-Z][a-zA-Z'’.]+)+)\b", page_txt):
        words = m.group(1).split()
        if all(w.lower().strip(".") in COMMON_NAMES for w in words):
            continue
        low = m.group(1).lower()
        if re.search(r"(?<![A-Za-z])" + re.escape(low) + r"(?![A-Za-z])", page_txt):
            continue   # the source also writes it in plain lowercase: an ordinary phrase, not a name
        found.add(m.group(1))
    return sorted(found)


def check(our_text, source_txt, items, run_len=8, allow=()):
    """Return {"pass": bool, "hits": [...]} — every place the source survives in our text."""
    ours = " " + norm(our_text) + " "
    allow_n = {norm(a) for a in allow if a}
    hits, seen = [], set()
    for it in items:
        t = (it.get("text") or "").strip()
        n = norm(t)
        if not n or n in allow_n or n in seen:
            continue
        words = n.split()
        if len(words) < 2 and it.get("kind") not in STRONG:
            continue
        if len(n) < 3 or n in COMMON_NAMES:
            continue
        if f" {n} " in ours:
            seen.add(n)
            hits.append({"test": "item", "kind": it.get("kind"), "text": t})
    for name in names_on(source_txt):
        n = norm(name)
        if n in seen or n in allow_n:
            continue
        if f" {n} " in ours:
            seen.add(n)
            hits.append({"test": "name", "kind": "name", "text": name})
    src_words = norm(source_txt).split()
    grams = {" ".join(src_words[i:i + run_len]) for i in range(len(src_words) - run_len + 1)}
    our_words = norm(our_text).split()
    i = 0
    while i <= len(our_words) - run_len:
        g = " ".join(our_words[i:i + run_len])
        if g in grams:
            j = i + run_len
            while j < len(our_words) and " ".join(our_words[j - run_len + 1:j + 1]) in grams:
                j += 1
            run = " ".join(our_words[i:j])
            if not any(a and a in run for a in allow_n):
                hits.append({"test": "run", "kind": f"{j - i} words in a row from the source", "text": run})
            i = j
        else:
            i += 1
    return {"pass": not hits, "hits": hits}
