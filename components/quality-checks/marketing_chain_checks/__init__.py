"""marketing-chain-checks — the checks every chain runs before it hands work on, and
the one hold() that stops failing work (rollout Step 0c, 2026-09-20).

Lifted from components/email-production/simple_email.py, where each one was
added after a real failure: a price for a size the store had dropped, an
[UNFILLED] note shipped inside an email, a serum called a scrub.

    CHECK   one question of one piece of work — it reports, it stops nothing
    GATE    a fixed point in a chain where checks run; any failure holds the work
    REVIEW  a person's verdict

Not the developer's components/qc-checks — a separate component this code does not call
(kept separate by SD-2 (qc shared truth), 2026-09-30). Renamed from
components/quality-checks on 2026-10-02; a tombstone there forwards old imports.
"""
import hashlib
import json
import pathlib
import re
from pathlib import Path

GATES = [
    ("inputs",   "before any model runs",             "is everything it needs on file and current?"),
    ("elements", "after the teardown or the brief",   "is every format, framework, style it names in the library?"),
    ("copy",     "after the words are written",       "prices, product facts, chopped thoughts, typos, unfilled notes"),
    ("media",    "after pictures or video are made",  "does it match the brief, the product, the words?"),
    ("delivery", "before it leaves the system",       "named right, going to the right place, to the right people"),
]
MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d{2})?)")


class Held(Exception):
    """Work that failed a gate. Carries the problems."""
    def __init__(self, gate, problems):
        self.gate, self.problems = gate, list(problems)
        super().__init__(f"HELD at the {gate} gate:\n  " + "\n  ".join(self.problems))


def prices_in(text):
    """Every price in the text, normalised to two decimals — "$49" and "$49.00"
    are one price (found by the copy-production rollout, 2026-09-20)."""
    out = set()
    for m in MONEY.findall(text or ""):
        try:
            out.add(f"{float(m.replace(',', '')):.2f}")
        except ValueError:
            pass
    return out


def price_check(text, offer_block, offer_key=None):
    """Every price in the piece is one the offer's own bank entry sells today."""
    said = prices_in(text)
    if not said:
        return []
    if not offer_block:
        return [f"the piece names a price ({', '.join('$' + s for s in sorted(said))}) but carries no offer"]
    allowed = prices_in(offer_block)
    name = f" for `{offer_key}`" if offer_key else ""
    return [f"${s} is not a price the offer bank sells{name} today "
            f"(live: {', '.join('$' + a for a in sorted(allowed)) or 'none'})" for s in sorted(said - allowed)]


def offer_block(bank_text, offer_key):
    """One offer's entry out of a bank laid out as `## key — Name` blocks."""
    m = re.search(rf"^## {re.escape(offer_key)} —.*?(?=^## |\Z)", bank_text or "", re.S | re.M)
    return m.group(0) if m else ""


def unfilled_check(text):
    """A hole the writer marked is honest in a working copy and a defect in a finished piece."""
    return (["the finished piece still carries an UNFILLED note — the writer could not fill a part, and a person has to"]
            if "UNFILLED" in (text or "") else [])


def _check_rows(check_text):
    """The CHECK block as (kind, text, quote, files_say) rows — one reading
    behind both read_check_block (strings) and check_items (items)."""
    m = re.search(r"```CHECK\s*\n(.*?)```", check_text or "", re.S)
    if not m:
        return [("check-unreadable", "the check step's answer could not be read", None, None)]
    try:
        found = json.loads(m.group(1))
    except ValueError:
        return [("check-unreadable", "the check step's answer is not valid JSON", None, None)]
    out = []
    for f in found.get("facts") or []:
        out.append(("fact", f"product fact {f.get('problem', 'WRONG')}: “{f.get('quote')}” — the files say: {f.get('files_say')}",
                    str(f.get("quote")), f.get("files_say")))
    for d in found.get("drafts") or []:                 # from check v2 (2026-09-21)
        out.append(("draft", f"names a DRAFT product: “{d.get('quote')}” — `{d.get('product')}` is not live",
                    str(d.get("quote")), None))
    for c in found.get("chops") or []:
        out.append(("chop", f"chopped thought: “{c.get('quote')}” → “{c.get('joined')}”",
                    str(c.get("quote")), None))
    for y in found.get("typos") or []:
        out.append(("typo", f"typo: “{y.get('quote')}” → “{y.get('fix')}”", str(y.get("quote")), None))
    return out


def read_check_block(check_text):
    """The copy-check step's answer (a fenced ```CHECK JSON block) as problems."""
    return [text for _kind, text, _quote, _files in _check_rows(check_text)]


# EVERY PROBLEM HAS AN ID (HE-1 (fact rulings), 2026-10-01): a person rules on
# a problem once, and the ruling has to find the same problem on the next run.
# The id is the gate, the kind and the quoted words — so changed words are a
# new problem, and a standing ruling never follows text it was not given.
def problem_id(gate, kind, quote):
    return hashlib.sha256("\x1f".join([gate, kind, quote or ""]).encode("utf-8")).hexdigest()[:12]


def item(gate, kind, text, quote=None, files_say=None):
    """One problem as a structured item; `text` is the string hold() reports."""
    quote = text if quote is None else quote
    return {"id": problem_id(gate, kind, quote), "kind": kind, "quote": quote,
            "files_say": files_say, "text": text}


def check_items(check_text, gate):
    """read_check_block's problems as items — same order, same texts."""
    return [item(gate, kind, text, quote, files)
            for kind, text, quote, files in _check_rows(check_text)]


def elements_check(labels):
    """{(element, asset): id or [ids]} against the element library."""
    import sys
    lib = next(d for d in Path(__file__).resolve().parents if (d / "components" / "elements").is_dir())
    sys.path.insert(0, str(lib / "components" / "elements" / "machine"))
    import elements as E
    return E.check(labels)


def hold(gate, problems, out_dir=None, items=None, cleared=None):
    """Write check.json and stop the work if anything failed. A caller that
    passes `items` (the problems as item() dicts) gets them, and the problems a
    standing ruling `cleared`, written beside the strings; no items, no change."""
    assert gate in {g[0] for g in GATES}, f"unknown gate {gate}"
    problems = [p for p in problems if p]
    if items is not None:
        assert problems == [i["text"] for i in items], "problems must be the items' texts"
    if out_dir:
        f = Path(out_dir) / "check.json"
        state = json.loads(f.read_text()) if f.is_file() else {}
        state[gate] = {"result": "pass" if not problems else "HELD", "problems": problems}
        if items is not None:
            state[gate]["items"] = items
            state[gate]["cleared"] = cleared or []
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    if problems:
        raise Held(gate, problems)
    return True


# A partner's product is not ours, and the only facts about it that may appear
# are the ones on the roster. Added 2026-09-21, after an affiliate send was
# planned with the partner living only in prose: the real link and the terms of
# the arrangement never reached the writer, so nothing downstream could tell an
# invented link from the real one.
EARNINGS = re.compile(
    r"\b(commission|affiliate link|we (?:get|earn|make) (?:paid|a cut|money)|"
    r"kickback|referral fee|we profit|paid to (?:say|recommend))\b", re.I)
URL = re.compile(r'https?://[^\s)\]}"\'<>]+', re.I)


def partner_check(text, partner, own_domains=()):
    """`partner` is one entry from the brand's own affiliate roster."""
    if not partner:
        return []
    out, body = [], text or ""
    link = (partner.get("link") or "").rstrip("/")
    name = partner.get("name") or partner.get("key") or "the partner"
    if link and link not in body:
        out.append(f"the piece features {name} and never carries their real link ({link})")
    host = link.split("//")[-1].split("/")[0].lower() if link else ""
    allowed = {host, *{d.lower() for d in own_domains}}
    for u in set(URL.findall(body)):
        h = u.split("//")[-1].split("/")[0].lower()
        if h and not any(h == a or h.endswith("." + a) for a in allowed if a):
            out.append(f"{u} is neither ours nor {name}'s — a link nobody put on the roster")
    if "traffic" in (partner.get("commission") or "").lower():
        out += earnings_claims(body)
    return out


# Raising the suspicion and denying it is the honest move, not a claim. A real
# affiliate email opened "Somebody's going to read this and think I'm getting
# paid to say it. Fair." and the keyword check held it (2026-09-21). A sentence
# only claims earnings if it is not denying them and not putting the thought in
# someone else's head.
DENIED = re.compile(r"\b(not|n't|never|nobody|no one|without|free|think(?:s|ing)? "
                    r"(?:i|we)'?m?|going to (?:read|think|say)|assume|suspect|"
                    r"wonder|fair\b)", re.I)


def earnings_claims(text):
    out = []
    for sentence in re.split(r"(?<=[.!?])\s+", text or ""):
        for m in set(EARNINGS.findall(sentence)):
            if DENIED.search(sentence):
                continue
            out.append("the arrangement is traffic-only and the piece says "
                       f"'{m}' — no earnings claim belongs in it: “{sentence.strip()[:120]}”")
    return out


def partner_on_file(brand_dir, key):
    """The roster entry, or None. Never invents one; a paused partner is not live.
    The roster is found through brandpath — email-sms/ first, then the
    template's email/; without brandpath, the email-sms/ path as before."""
    import json
    import sys
    brand_dir = pathlib.Path(brand_dir)
    f = brand_dir / "email-sms" / "affiliates.json"
    try:
        bp = str(pathlib.Path(__file__).resolve().parent.parent.parent / "brandpath")
        if bp not in sys.path:
            sys.path.append(bp)
        import brandpath
        # brandpath's root is the folder holding the brand folders
        f = brandpath.brand_path(brand_dir.name, "email-sms", "affiliates.json",
                                 root=brand_dir.parent)
    except Exception:
        pass
    if not (key and f.is_file()):
        return None
    for a in json.loads(f.read_text()).get("affiliates", []):
        if a.get("key") == key and a.get("status", "active") == "active":
            return a
    return None


# A PRODUCT THAT IS NOT LIVE IS NOT A PRODUCT. the owner, 2026-09-21: "you have to
# also make sure that the product is not a draft. FADE is a draft, so we
# shouldn't be talking about FADE." A brand's own files describe things that
# were never launched — one brand's asset-bed names three of them as drafts — and a
# writer handed those files will use one. The live list is the brand's; this
# only compares against it.
def draft_product_check(text, never):
    """`never` — handles or names that exist in the brand's files but are not live."""
    body, out = (text or ""), []
    for h in never or []:
        # a handle is `ghost-tin`; the copy writes "Ghost Tin", "ghost tin" or
        # "ghost-tin". Each part is escaped, then joined by the separator.
        parts = [re.escape(x) for x in str(h).split("-") if x]
        if not parts:
            continue
        if re.search(r"\b" + r"[\s\-—]?".join(parts) + r"\b", body, re.I):
            out.append(f"the piece names `{h}`, which is not a live product — it is a draft, "
                       "and nothing in the brand's other files makes it one")
    return out


# EVERY PIECE ENDS SOMEWHERE A READER CAN BUY. the owner, same day: "Every email
# should have some sort of refocus back into a product in some capacity, and
# then the offer that goes with it. Even if it's more like a value email, just
# make sure we have the ability to make money." Three of nine September drafts
# ended on "[UNFILLED: destination]" and one on a collection page.
def money_path_check(link, sellable, label="", extra_ok=()):
    """`sellable` — the live products' urls. `extra_ok` — a partner's link on an
    affiliate send, which is a real destination that is not ours."""
    link = (link or "").strip()
    if not link or "UNFILLED" in link.upper():
        return ["the piece ends on no destination — there is nowhere for a reader to go"]
    urls = {str(u).rstrip("/") for u in sellable or ()} | {str(u).rstrip("/") for u in extra_ok}
    if link.rstrip("/") in urls:
        return []
    # A code link (`<site>/discount/<CODE>/?next=<path>`) applies the code and
    # lands on `next` (the ops lead, 2026-10-01, on a brand's code link). The destination is
    # the page it lands on, so that is what is checked.
    from urllib.parse import urlsplit, parse_qs
    parts = urlsplit(link)
    nxt = (parse_qs(parts.query).get("next") or [""])[0]
    if re.match(r"^/discount/[^/]+/?$", parts.path) and nxt.startswith("/"):
        bare = lambda u: re.sub(r"^https?://(www\.)?", "", u).rstrip("/")   # <brand>.com == www.<brand>.com
        if bare(f"{parts.netloc}{nxt}") in {bare(u) for u in urls}:
            return []
    if not urls:
        # A brand that has not declared a catalogue cannot have its destination
        # checked, and that is the BRAND's gap, not this email's — the doctor
        # says so. Having SOME destination is already settled above.
        return []
    return [f"the button goes to `{link}`, which is not a live product page" +
            (f" and not the partner's link" if extra_ok else "") +
            " — a collection or the front page is not a destination" +
            (f" (button reads \"{label}\")" if label else "")]


# THE SUBJECT LINE AND THE PREVIEW ARE THE EMAIL. Added 2026-09-21: a September
# batch went to review with one empty preview, one that had lost its first
# letter ("uild your set"), and one still holding the writer's own
# "[UNFILLED: preview]". The body was checked; the two lines a reader actually
# sees in the inbox were not.
def subject_check(chosen):
    """`chosen` — the subject the email will send with: {subject, preview}."""
    out = []
    for field in ("subject", "preview"):
        v = ((chosen or {}).get(field) or "").strip()
        if not v:
            out.append(f"the {field} is empty — it is the first thing a reader sees")
            continue
        if "UNFILLED" in v.upper():
            out.append(f"the {field} still carries an UNFILLED note: “{v[:70]}”")
        if v[0].islower() and v.split()[0].lower() not in LOWER_OK:
            out.append(f"the {field} starts mid-word or mid-sentence: “{v[:50]}” — "
                       "check the first letter did not get eaten")
    return out


# Openers a person really does write in lower case. Everything else starting
# lower is read as a dropped first letter, which is what happened.
LOWER_OK = {"a", "an", "the", "and", "but", "so", "if", "when", "you", "your",
            "i", "it", "we", "that", "this", "there", "he", "she", "they",
            "what", "why", "how", "no", "not", "just", "still", "nobody",
            "almost", "every", "most", "all", "one", "two", "three"}
