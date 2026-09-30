"""quality-checks — the checks every chain runs before it hands work on, and
the one hold() that stops failing work (rollout Step 0c, 2026-09-20).

Lifted from components/email-production/simple_email.py, where each one was
added after a real failure: a price for a size the store had dropped, an
[UNFILLED] note shipped inside an email, a serum called a scrub.

    CHECK   one question of one piece of work — it reports, it stops nothing
    GATE    a fixed point in a chain where checks run; any failure holds the work
    REVIEW  a person's verdict

Dayu's components/qc-checks (text + voice) is CALLED where useful, never edited.
"""
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


def read_check_block(check_text):
    """The copy-check step's answer (a fenced ```CHECK JSON block) as problems."""
    m = re.search(r"```CHECK\s*\n(.*?)```", check_text or "", re.S)
    if not m:
        return ["the check step's answer could not be read"]
    try:
        found = json.loads(m.group(1))
    except ValueError:
        return ["the check step's answer is not valid JSON"]
    out = []
    for f in found.get("facts") or []:
        out.append(f"product fact {f.get('problem', 'WRONG')}: “{f.get('quote')}” — the files say: {f.get('files_say')}")
    for c in found.get("chops") or []:
        out.append(f"chopped thought: “{c.get('quote')}” → “{c.get('joined')}”")
    for y in found.get("typos") or []:
        out.append(f"typo: “{y.get('quote')}” → “{y.get('fix')}”")
    return out


def elements_check(labels):
    """{(element, asset): id or [ids]} against the element library."""
    import sys
    lib = next(d for d in Path(__file__).resolve().parents if (d / "components" / "elements").is_dir())
    sys.path.insert(0, str(lib / "components" / "elements" / "machine"))
    import elements as E
    return E.check(labels)


def hold(gate, problems, out_dir=None):
    """Write check.json and stop the work if anything failed."""
    assert gate in {g[0] for g in GATES}, f"unknown gate {gate}"
    problems = [p for p in problems if p]
    if out_dir:
        f = Path(out_dir) / "check.json"
        state = json.loads(f.read_text()) if f.is_file() else {}
        state[gate] = {"result": "pass" if not problems else "HELD", "problems": problems}
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    if problems:
        raise Held(gate, problems)
    return True


COPY_CHECK_PROMPT = Path(__file__).resolve().parent.parent / "prompts"


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
        for m in set(EARNINGS.findall(body)):
            out.append(f"the arrangement is traffic-only and the piece says '{m}' — "
                       "no earnings claim belongs in it")
    return out


def partner_on_file(brand_dir, key):
    """The roster entry, or None. Never invents one; a paused partner is not live."""
    import json
    f = pathlib.Path(brand_dir) / "email-sms" / "affiliates.json"      # v6 name
    if not f.is_file():
        f = pathlib.Path(brand_dir) / "email" / "affiliates.json"      # old name
    if not (key and f.is_file()):
        return None
    for a in json.loads(f.read_text()).get("affiliates", []):
        if a.get("key") == key and a.get("status", "active") == "active":
            return a
    return None
