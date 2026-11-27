"""The email as designed: one text for the checks (LD-105 (check the designed email), 2026-11-04).

The delivery gate used to read the writer's copy (stage8--blocks.md, stage8c--check.md) while the email that goes
out is the designed one (design/email.json), so a word fixed on the page stayed held. Where a run has a design,
the checks read its words; an email with no design is read as before.

    load(run_dir)            the design's spec, or None
    words(spec)              every word a reader gets: subject, preview and each section's text
    quotes(spec)             every credited quote: {quote, who, verified}
    bank_rows(brand, root)   the brand's language rows, plus the language layer's lived-moments index
    credit_problems(spec, brand, root)   the shared quote-credit check on this email

Reads only. brands/ is never written; the language layer is used through its public API.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_MCC = HERE.parent / "marketing-chain-checks"
if str(_MCC) not in sys.path:
    sys.path.append(str(_MCC))
import marketing_chain_checks as Q  # noqa: E402

# keys a section keeps for the designer, never shown as words; a picture is its own world (its words are drawn)
NOT_WORDS = {"s", "style", "glow", "picture", "picture.brief", "photo", "proof", "record", "route", "use", "source",
             "ratio", "focus", "brief", "history", "todo", "gif", "stage", "alt", "link", "href", "url"}
# sections whose renderer prints "· verified buyer" after the credit (design/engine.py s_example)
VERIFIED = {"example"}
# a credit naming a public place says where the words were said, never "verified buyer" (brand_a dec-19, 2026-11-17:
# an Instagram ad comment from a lead showed as a verified buyer); engine.py renders by this same rule
PUBLIC_CREDIT = ("comment", "survey", "reddit", "youtube", "instagram", "tiktok", "facebook", "review", "forum", "post")


def badge(q):
    """True when a quote section's credit gets "· verified buyer": not a public place, and not "verified": false."""
    who = (q.get("who") or "").lower()
    return q.get("verified") is not False and not any(w in who for w in PUBLIC_CREDIT)


def load(run_dir):
    f = Path(run_dir) / "design" / "email.json"
    if not f.is_file():
        return None
    try:
        spec = json.loads(f.read_text())
    except ValueError:
        return None
    return spec if isinstance(spec, dict) and isinstance(spec.get("sections"), list) else None


def words(spec):
    """Every string a reader gets, in order: subject, preview, then each section's words."""
    out = [spec.get("subject") or "", spec.get("preview") or ""]

    def walk(x):
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, dict):
            for k, v in x.items():
                if k not in NOT_WORDS:
                    walk(v)
    for s in spec.get("sections") or []:
        walk(s)
    return [w for w in out if w and w.strip()]


def quotes(spec):
    """Every quote with a credit, from a section itself or a list inside it (notes, tiles)."""
    out = []

    def walk(x, verified):
        if isinstance(x, dict):
            if x.get("quote") and isinstance(x.get("quote"), str):
                out.append({"quote": x["quote"], "who": x.get("who") or "", "verified": verified and badge(x)})
            for k, v in x.items():
                if k not in NOT_WORDS and isinstance(v, (list, dict)):
                    walk(v, verified)
        elif isinstance(x, list):
            for v in x:
                walk(v, verified)
    for s in spec.get("sections") or []:
        walk(s, s.get("s") in VERIFIED)
    return out


_BANK = {}


def bank_rows(brand, root):
    """The brand's language rows (language_layer.engine.load) and each avatar's lived-moments index
    (language_layer.experience.load, where the YouTube and Reddit moments a writer is handed live)."""
    key = (brand, str(root))
    if key not in _BANK:
        lang = Path(root) / "components" / "language-layer"
        here = HERE.parent / "language-layer"
        for d in (lang, here):
            if d.is_dir() and str(d) not in sys.path:
                sys.path.append(str(d))
        from language_layer import engine as LE
        from language_layer import experience as LX
        rows = list(LE.load(brand, root=root))
        base = LE.avatar_root(brand, root)
        for a in sorted(x.name for x in base.iterdir() if x.is_dir()) if base.is_dir() else []:
            rows += [r for r in LX.load(brand, a, root=root) if isinstance(r, dict)]
        _BANK[key] = rows
    return _BANK[key]


def credit_problems(spec, brand, root):
    qs = quotes(spec)
    return Q.quote_credit_check(qs, bank_rows(brand, root)) if qs else []
