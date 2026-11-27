"""marketing-chain-checks — the checks every chain runs before it hands work on, and
the one hold() that stops failing work (rollout Step 0c, 2026-09-20).

Lifted from components/email-production/simple_email.py, where each one was
added after a real failure: a price for a size the store had dropped, an
[UNFILLED] note shipped inside an email, a serum called a scrub.

    CHECK   one question of one piece of work — it reports, it stops nothing
    GATE    a fixed point in a chain where checks run; any failure holds the work
    REVIEW  a person's verdict

Not developer's components/qc-checks — a separate component this code does not call
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
    """Every price in the piece is one the offer's own bank entry sells today. A line that FORBIDS a price ("No
    $49.99, no $46.66", "never $X") names it to keep it off the ad, so its prices are not prices the piece says
    (2026-10-28: a brief was held for its own never-line)."""
    forbids = re.compile(r"(?i)^\W*(?:no|never|not|don't|do not|avoid)\b|\b(?:never|no|not)\s+(?:\$|price|prices)")
    # a line that only describes the SWIPE (what the ad was built on, its letterforms, a swap's `from`) quotes the other
    # brand's prices, which are never ours (2026-10-28: a brief was held for the swipe's "$118 -> $39")
    swipe = re.compile(r"(?i)\bbuilt on\b|\bletterform\b|\"from\"\s*:|\bthe swipe'?s?\b|\bthe source'?s?\b|\bsource (?:copy|instance)\b")
    keep, never = [], False
    for l in str(text or "").splitlines():
        if re.match(r"^\s*#{1,6}\s", l):                  # a heading opens a section; a "Never ..." section lists what is barred
            never = bool(re.search(r"(?i)\bnever\b", l))
            continue
        if not never and not forbids.search(l) and not swipe.search(l):
            keep.append(l)
    text = "\n".join(keep)
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


def read_check_block(check_text, still_in=None):
    """The copy-check step's answer (a fenced ```CHECK JSON block) as problems. With `still_in` (the words a reader
    will get, LD-105 (check the designed email)), a finding whose quoted line is no longer there is not a problem."""
    return [i["text"] for i in check_split(check_text, "delivery", still_in)[0]]


def _plain(text):
    """Words only: markup, case, punctuation and spacing do not make two lines different (LD-105 (check the designed
    email); engine._same's reading in the language layer, plus tags dropped)."""
    text = re.sub(r"<[^>]+>", " ", str(text or "")).replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", text.lower())).strip()


def on_page(quote, text):
    """Is this quoted line, word for word (markup, case and punctuation aside), in the text?"""
    q = _plain(quote)
    return bool(q) and q in _plain(text)


def check_split(check_text, gate, still_in=None):
    """(live, gone): the check step's findings as items, split by whether the line each one quotes is still in
    `still_in`. One text, LD-105 (check the designed email): a line fixed on the page clears its finding. With no
    `still_in`, or a finding that quotes nothing (an unreadable check), it stays live: today's reading."""
    live, gone = [], []
    for i in check_items(check_text, gate):
        stale = still_in is not None and i["kind"] != "check-unreadable" and i.get("quote") and not on_page(i["quote"], still_in)
        (gone if stale else live).append(i)
    return live, gone


# WHO SAID IT (LD-105 (check the designed email), 2026-11-04): a YouTube comment and two Reddit posts went out
# credited "A <brand> customer · verified buyer". A credit claims a kind of source; the language bank says where each
# line was really said. Both readings are by words in the record, never by a brand's name.
PLATFORMS = ("reddit", "youtube", "tiktok", "instagram", "facebook")
_BUYER_TYPES = {"survey", "ticket", "interview", "database", "review"}


def credit_claim(who, verified=False):
    """The kind of source a printed credit claims, or None when it names none (a first name, an empty credit).
    `verified` = the section prints "· verified buyer" after the credit, which claims a customer whatever it says."""
    w = (who or "").lower()
    if verified:
        return "customer"
    for p in PLATFORMS:
        if p in w:
            return p
    if "panel" in w or "tester" in w:
        return "panel"
    if "follower" in w:
        return "follower"
    if re.search(r"\b(customer|buyer|client)s?\b", w):
        return "customer"
    return None


def source_kind(row):
    """Where a language row was said: a platform, `panel`, `customer` (a buyer's own words on our own record),
    `follower` (a non-buyer survey), `comment` or `community` — read off the row's own source fields."""
    s = row.get("source") if isinstance(row.get("source"), dict) else {}
    typ = str(s.get("type") or "").lower()
    where = " ".join(str(s.get(k) or "") for k in ("name", "ref", "url", "type")).lower()
    for p in PLATFORMS:
        if p in where:
            return p
    if typ == "panel":
        return "panel"
    speaker = str(row.get("speaker") or "").lower()
    if typ == "review" and "competitor" in where:      # another brand's buyer reviewing another brand's product
        return "review"
    if typ in _BUYER_TYPES and speaker in ("customer", "churned") and row.get("attribution") != "assumed":
        return "customer"
    if typ == "survey" and speaker == "lead":
        return "follower"
    return typ or "unknown"


FITS = {"follower": {"follower", "tiktok", "instagram", "facebook", "comment"}}


def _row_words(row):
    return row.get("text") or row.get("quote") or ""


def _same_line(quote, rows):
    """The rows that hold this quoted line: word for word inside the row, or — a quote of six words or more — nearly
    so (a typo fixed, a word dropped: 85% of its words in one row)."""
    q = _plain(quote)
    if not q:
        return []
    exact = [r for r in rows if q in _plain(_row_words(r))]
    if exact or len(q.split()) < 6:
        return exact
    qw = q.split()
    out = []
    for r in rows:
        rw = set(_plain(_row_words(r)).split())
        if rw and sum(w in rw for w in qw) >= 0.85 * len(qw) and len(rw) <= 2 * len(qw):
            out.append(r)
    return out


def _source_name(row):
    s = row.get("source") if isinstance(row.get("source"), dict) else {}
    name = s.get("name") or s.get("type") or "an unnamed source"
    ref = s.get("ref") or s.get("url")
    return "%s (%s)" % (name, ref) if ref else name


def quote_credit_check(quotes, rows):
    """Every quote's credit against where the bank says it was said. `quotes` = [{quote, who, verified}]; `rows` =
    language rows (`text`, or the experience index's `quote`, with `source`). A credit naming no kind of source, or a
    quote the bank does not hold, is not judged here (an invented quote is LD-104 (no invented facts)'s)."""
    out = []
    for x in quotes:
        claim = credit_claim(x.get("who"), x.get("verified"))
        if not claim:
            continue
        found = _same_line(x.get("quote"), rows)
        if not found:
            continue
        kinds = {source_kind(r) for r in found}
        if kinds & FITS.get(claim, {claim}):
            continue
        credit = (x.get("who") or "") + (" · verified buyer" if x.get("verified") else "")
        names = list(dict.fromkeys(_source_name(r) for r in found))
        out.append("quote “%s” is credited “%s”, but the language bank has it from %s — credit it to where it was "
                   "said, or use a %s's own words" % (x.get("quote"), credit.strip(" ·"), "; ".join(names[:3]), claim))
    return out


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


def check_items(check_text, gate, still_in=None):
    """read_check_block's problems as items — same order, same texts. With `still_in`, only the live ones
    (check_split)."""
    if still_in is not None:
        return check_split(check_text, gate, still_in)[0]
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


# A PRODUCT THAT IS NOT LIVE IS NOT A PRODUCT. owner, 2026-09-21: "you have to
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


# EVERY PIECE ENDS SOMEWHERE A READER CAN BUY. owner, same day: "Every email
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
    # lands on `next` (email_lead, 2026-10-01, on a brand's code link). The destination is
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
