"""What may stop a finished script (owner ruling, 2026-11-20).

Only a line that breaks a written money or law rule holds a brief:
  - a banned claim word: cure / remove / erase, found by code in any line (unless a run ruling
    settles that exact line); the product file's own banned single words (a slash list under
    "Forbidden", e.g. "fixes / corrects / treats") hold when the claims judge flags them twice;
  - an offer, price or guarantee line that is not word for word in the brand's offer
    files, the product file or the run's ask.
Everything else a judge says is a NOTE: section labels (the judge's majority relabels
the scene), taste, and any claim the brand file, a run ruling or the language bank
already settles word for word. A judge's money/law flag holds only when a second
ask repeats it; a flag that does not repeat is a note.

Brand-agnostic: every brand fact comes from brands/<brand>/ files.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]

# the legal floor, every brand: a claim that the product cures, removes or erases something
LAW_ROOTS = ("cure", "remov", "eras")
LAW_WORD = re.compile(r"\b(cur(?:e|es|ed|ing)|remov(?:e|es|ed|ing|al)|eras(?:e|es|ed|ing))\b", re.I)
MONEY = re.compile(r"(\$\s?\d|\b\d+\s?%\s*off\b|\bguarantee[sd]?\b|\brefund|\bmoney[- ]back\b|\bfree\b|"
                   r"\b\d+\s?(?:-|\s)?day\b|\bper (?:jar|bottle|tub|month)\b|\bbuy \w+ get\b|\bbogo\b|\bdiscount|"
                   r"\bcoupon|\bcode\b|\bsave \$?\d|\bhalf off\b|\bdollars?\b)", re.I)
MIN_WORDS = 3          # a settled match is a phrase, never one shared word


def notes_rule(lane):
    """True when the 2026-11-20 rule is on for this lane (sections, claims, audit); the rollback switch is
    holds.json beside this file, or WRITING_HOLDS_OLD=all|<lanes> on one machine."""
    import os
    old = {x.strip() for x in os.environ.get("WRITING_HOLDS_OLD", "").split(",") if x.strip()}
    if "all" in old or lane in old:
        return False
    try:
        cfg = json.loads((HERE / "holds.json").read_text())
    except (OSError, ValueError):
        return True
    return bool(cfg.get("on", True)) and bool((cfg.get("lanes") or {}).get(lane, True))


def norm(text):
    return " ".join(re.findall(r"[a-z0-9$%']+", str(text or "").lower().replace("’", "'")))


def _read(p):
    try:
        return Path(p).read_text(errors="replace")
    except OSError:
        return ""


def _brand_dir(brand, root=None):
    """The brand's folder through brandpath (builder card rule 3)."""
    import sys
    sys.path.insert(0, str(WS / "components" / "brandpath"))
    from brandpath import brand_root
    return Path(brand_root(brand, Path(root or WS) / "brands"))


def product_file(brand, product, root=None):
    b = _brand_dir(brand, root) / "products"
    for p in (b / (product or "") / "product.md", b / ((product or "") + ".md")):
        if product and p.is_file():
            return p
    return None


def _without_forbidden(text):
    """A product file minus its Forbidden list: a banned phrase quoted as banned settles nothing."""
    return re.sub(r"(?is)\*\*Forbidden:?\*\*.*?(?=\n## |\n\*\*[A-Z][^*]*:\*\*|\Z)", "", text)


AD_OFFER = re.compile(r"<!-- ad-offer -->(.*?)<!-- /ad-offer -->", re.S)


def ad_offer(bank):
    """The part of an offer bank an ad may quote. A bank that rules one ad offer marks it `<!-- ad-offer -->` …
    `<!-- /ad-offer -->` (2026-11-25): then only that block, the guarantee and the brand's own claims settle an ad's
    line, so a funnel or holiday deal kept lower in the bank as a fact never passes as an ad's offer. A bank with no
    mark is read whole, as before."""
    m = AD_OFFER.search(bank or "")
    if not m:
        return bank
    parts = re.split(r"(?m)^(?=#{2,3} )", bank)
    return "\n".join([m.group(1)] + [x for x in parts if re.match(r"#{2,3} (guarantee|brand-owned-claims)\b", x)])


def money_sources(brand, product, run_dir=None, root=None):
    """The text an offer, price or guarantee line must match word for word."""
    b = _brand_dir(brand, root)
    out = [ad_offer(_read(b / "products" / "offer-bank.md"))]
    pf = product_file(brand, product, root)
    if pf:
        out.append(_without_forbidden(_read(pf)))
    if run_dir:
        out += [_read(Path(run_dir) / "vars" / "ask.md"), _read(Path(run_dir) / "RULINGS.md")]
    return norm("\n".join(out))


def language_sources(brand, root=None):
    """The language layer: the brand's customer words (language bank, every avatar's language folder)."""
    b = _brand_dir(brand, root)
    files = [b / "customer-experience" / "language-bank.md", *sorted(b.glob("products/*/language/*.md"))]
    for lang in sorted(b.glob("core-avatars/*/language")):
        files += [p for p in sorted(lang.rglob("*")) if p.suffix in (".md", ".json") and p.is_file()]
    return norm("\n".join(_read(p) for p in files))


def settled_sources(brand, product, run_dir=None, root=None):
    """Everything that settles a line word for word: the product file (not its Forbidden list), the brand
    position, the offer files, the run's rulings and ask, and the language bank."""
    b = _brand_dir(brand, root)
    out = [money_sources(brand, product, run_dir, root),
           norm(_read(b / "brand-identity" / "position.md")),
           language_sources(brand, root)]
    return "\n".join(out)


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", str(text or "")) if norm(s)]


def is_settled(words, corpus):
    n = norm(words)
    return len(n.split()) >= MIN_WORDS and n in corpus


def law_words(brand, product, root=None):
    """The legal floor plus the product file's own banned single words (a slash list under Forbidden)."""
    found = set()
    pf = product_file(brand, product, root)
    if pf:
        m = re.search(r"(?is)\*\*Forbidden:?\*\*(.*?)(?=\n## |\Z)", _read(pf))
        for line in (m.group(1).splitlines() if m else []):
            if line.count("/") >= 2:
                found |= {w.strip().lower() for w in re.sub(r"^[-*\s]+", "", line).split("/") if re.fullmatch(r"\s*[a-zA-Z]+\s*", w)}
    return found


def law_hits(text, extra=()):
    """Banned claim words in one line."""
    hits = [m.group(0) for m in LAW_WORD.finditer(text or "")]
    low = norm(text).split()
    hits += [w for w in extra if w in low and not w.startswith(LAW_ROOTS)]
    return sorted(set(h.lower() for h in hits))


def money_unmatched(text, sources):
    """Offer / price / guarantee sentences of a line that are not word for word in the money sources."""
    return [s.strip() for s in _sentences(text) if MONEY.search(s) and norm(s) not in sources]


def classify(rows, violations, brand, product, run_dir=None, root=None):
    """Split a claims judge's findings into holds and notes, and add the code's own law scan.

    rows: [{id, text}] every line; violations: the judge's [{id, words, rule}].
    Returns (hold_candidates, law_holds, notes). hold_candidates still need the second ask to repeat;
    law_holds are banned claim words found by code (no judge needed); notes never stop a brief.
    """
    by = {r["id"]: r for r in rows}
    corpus = settled_sources(brand, product, run_dir, root)
    money = money_sources(brand, product, run_dir, root)
    rulings = norm(_read(Path(run_dir) / "RULINGS.md")) if run_dir else ""
    extra = law_words(brand, product, root)
    law, notes, candidates = [], [], []
    for r in rows:
        hits = law_hits(r["text"])          # the legal floor only; the brand's extra words need the judge
        # a banned claim word holds unless a run ruling settles this very line
        if hits and not is_settled(r["text"], rulings):
            law.append({"id": r["id"], "words": r["text"], "rule": "banned claim word: " + ", ".join(hits),
                        "class": "law"})
    law_ids = {x["id"] for x in law}
    for v in violations:
        line = (by.get(v.get("id")) or {}).get("text", "")
        words = v.get("words") or ""
        if v.get("id") in law_ids:
            continue
        if is_settled(words, corpus) or is_settled(line, corpus):
            notes.append({**v, "note": "settled: the brand file, a run ruling or the language bank says these words"})
            continue
        unmatched = money_unmatched(words, money) or money_unmatched(line, money)
        if unmatched:
            candidates.append({**v, "class": "money", "unmatched": unmatched})
        elif law_hits(words, extra):
            candidates.append({**v, "class": "law"})
        else:
            notes.append({**v, "note": "not a money or law rule: reported, never a stop"})
    return candidates, law, notes


def section_notes(result):
    """A section label disagreement is a note: the judge's majority relabels the scene."""
    out = []
    for m in result.get("misfits") or []:
        out.append({"id": m.get("id"), "given": m.get("given"), "relabel_to": m.get("should_be"),
                    "votes": m.get("votes"), "why": m.get("why")})
    return out


AUDIT_HOLD = re.compile(r"\b(price|offer|guarantee|refund|cure[sd]?|remov(?:e|es|ed)|eras(?:e|es|ed)|banned)\b", re.I)


def audit_note(words):
    """The audit's findings, kept as a note when its automatic repairs are spent."""
    return {"kind": "audit", "words": (words or "").strip()[:4000],
            "money_or_law_named": sorted(set(m.lower() for m in AUDIT_HOLD.findall(words or "")))}


if __name__ == "__main__":
    import sys
    print(json.dumps(sorted(law_words(sys.argv[1], sys.argv[2]))))
