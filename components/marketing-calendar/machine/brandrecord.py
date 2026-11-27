#!/usr/bin/env python3
"""The brand's record, as the calendar reads it — and the month's checker.

These are the readers the calendar flow runs on: who the brand's segments are,
which avatars carry no offer, the type catalogue and offer bank as the model
sees them, what the brand has learned, how each segment responds, how cold each
one has gone. Plus `check()`, which tests a finished month against the rules
deterministically rather than trusting the model to have obeyed them.

Moved here 2026-09-13 when the calendar became its own component. They were
inside the email chain's `compose.py`, which meant the calendar could not run
without the email machine — untrue then and wrong now, since a month of ad
concepts reads exactly the same record. Bodies are unchanged; the email
chain imports them back from here, so there is still one copy.

Brand-agnostic: every fact resolves through `brands/<brand>/`.
"""
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

CATEGORY = {"ask": "Promotional", "help": "Educational", "belong": "Cultural",
            "real": "Community", "brand": "Brand", "affiliate": "Affiliate"}

# The brand's language bank — who its avatars are, in its customers' own
# words. `components/language-layer/` owns it; before that was extracted, the
# email chain reached sideways into another lab machine's folder for it.
# Absent, a brand simply has no roster yet — that is a brand, not an error.
# Found, never counted: this file has moved folders twice and a `parents[N]`
# breaks silently on every move. It also cannot ask its own `paths` module for
# help — the email chain has a `paths` of its own, and when it imports this
# file its copy wins the name (that silently left the roster empty, 09-13).
# So: walk up to the checkout, then look in components/.
def _language_layer():
    here = Path(__file__).resolve()
    for d in [here.parent, *here.parents]:
        cand = d / "components" / "language-layer"
        if cand.is_dir():
            sys.path.append(str(cand))
            try:
                from language_layer import engine
                return engine
            except ImportError:
                return None
    return None


L = _language_layer()


def _json_or(path, default):
    """A brand file that is not there yet reads as empty — a brand with no
    history is a brand, not an error (brand_b, 2026-09-09)."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return default


def _text_or(path, default=""):
    try:
        return path.read_text()
    except FileNotFoundError:
        return default


def brand_segments(brand_root):
    """The segments are the BRAND's vocabulary — read from its audience
    matrix (EM-1's record), never hardcoded (de-branded 2026-08-31)."""
    m = brand_root / "email-sms" / "audience-matrix.json"
    if m.is_file():
        return [s["name"] for s in json.loads(m.read_text())["segments"]]
    sys.exit(f"{brand_root.name} has no audience-matrix.json — run "
             "pull/matrix.py for this brand first; the composer cannot "
             "invent a segment vocabulary")


def bank_is_per_avatar(text, roster):
    """Does this bank group its offers UNDER avatars, or is it one flat list?

    Both shapes exist and they are read differently. The older one used
    `## <avatar>` with `### <offer>` beneath; the current generated one is flat
    — `## <key> — <name>` per offer, brand-wide, after owner's 2026-09-13
    ruling ("stop overcomplicating these things"). Guessing wrong is not a
    cosmetic error: on 2026-09-14 the flat bank was read with the old rule, so
    every product heading looked like an avatar, no line looked like an offer,
    and BOTH brands silently lost their entire offer bank. A month was planned
    with every send offerless and nothing said why.
    """
    heads = {ln[3:].strip() for ln in text.splitlines() if ln.startswith("## ")}
    return bool(heads & set(roster or ()))


def offerless_avatars(brand_root, roster):
    """Which avatars carry no offers.

    In a per-avatar bank that is any avatar without a section of its own. In a
    FLAT bank the offers belong to the brand, so no avatar is offerless — and
    answering "all of them" there is what emptied both banks.
    """
    f = brand_root / "products" / "offer-bank.md"
    if not f.is_file():
        return set(roster)
    text = f.read_text()
    if not bank_is_per_avatar(text, roster):
        return set()
    sections = {ln[3:].strip() for ln in text.splitlines() if ln.startswith("## ")}
    return {a for a in roster if a not in sections}


def render_types(path, include_notes=True):
    """The full catalogue as the composer reads it — role, arc, needs, usage."""
    d = json.loads(Path(path).read_text())
    out = []
    for well, cat in CATEGORY.items():
        out.append(f"## {cat}")
        for t in d["types"]:
            if t["well"] != well:
                continue
            line = (f"- `{t['key']}` — {t['name']} · role: {t['role']}"
                    + (f" · then: {', '.join(t['then'])}" if t.get("then") else "")
                    + f" · sent {t.get('n', 0)}x · {t['what']}")
            out.append(line)
            for k in (("note", "arc_note") if include_notes else ("arc_note",)):
                if t.get(k):
                    out.append(f"    ({t[k]})")
        out.append("")
    a = d.get("arc", {})
    out.append("## The arc")
    for r, meaning in a.get("roles", {}).items():
        out.append(f"- `{r}` — {meaning}")
    if a.get("rule"):
        out.append(f"\n{a['rule']}")
    return "\n".join(out)


def identity_sources(brand_root):
    """Authoritative identity/origin inputs from this brand only; catalogue hints are not evidence."""
    root = Path(brand_root)
    return {rel: (root / rel).read_text() for rel in
            ("brand-identity/position.md", "brand-identity/story.md") if (root / rel).is_file()}


def planner_types(path, brand_root):
    """Format choices plus sourced identity; free-form catalogue notes never supply biographies."""
    sources = identity_sources(brand_root)
    identity = "\n\n".join("### %s\n%s" % (rel, text) for rel, text in sources.items())
    return ("## Format catalogue — format choices only, not evidence of credentials or origin\n"
            + render_types(path, include_notes=False)
            + "\n\n## Identity and origin from this brand's own sources\n"
            + (identity or "No identity source supplied. Do not propose founder credentials or origin claims.")
            + "\n\nCredential, founder, family and formulation claims must be supported by these identity sources. "
              "A format name, example, catalogue note or another brand is not evidence. "
              "Do not turn a manufacturer or family member's work into the founder's personal credential.")


def identity_problems(slots, brand_root):
    """Flag credential claims when that credential is absent from the brand's identity sources."""
    sources = "\n".join(identity_sources(brand_root).values()).lower()
    credential = r"pharmacist|dermatologist|doctor|chemist"
    claim = re.compile(r"\b(?:is|was|am|as)\s+(?:a[n]?\s+)?(" + credential + r")\b|\b(" + credential + r")\s+who\b", re.I)
    out = []
    for slot in slots:
        text = json.dumps({k: slot.get(k) for k in ("variants", "angle", "why")}, ensure_ascii=False)
        for match in claim.finditer(text):
            word = next(x for x in match.groups() if x).lower()
            if not re.search(r"\b" + word + r"\b", sources):
                out.append("%s: identity claim uses %s without support in this brand's position/story; catalogue hints are not identity evidence" % (slot.get("id", "move"), word))
    return out


NOTE_KEYS = {"guarantee", "guarantees", "social-proof", "cadence", "rules",
             "open", "funnel-shape", "page-pricing", "sms-capture",
             "never-pair", "promo-calendar", "brand-owned-claims",
             "funnel-offer-map", "storefront-order",   # storefront-order: which products lead, in order (2026-11-04)
             "popup"}                                  # popup: the sign-up opt-in, not an offer a send carries (2026-11-04)


def render_offers(brand_root, roster=()):
    """The bank as the planner reads it, in whichever shape the brand keeps.

    One rule decides everything: **a heading is an OFFER when its section says
    what the thing costs.** A price is what makes an offer an offer, and it is
    the only test that survives the bank being reshaped — which it was, on
    2026-09-13, silently emptying both banks for a day.

    In a FLAT bank a `### ` heading is held to the same test as a `## ` one
    (2026-11-03). A flat bank keeps its generated products as `## ` and its
    human-ruled offers as `### ` beneath them — a funnel offer, a dated
    promotion — and reading only `## ` made every ruled offer invisible while
    its prose was swallowed into the last product's section. Every heading's
    section now ends at the next heading of either depth, so a note's section
    (`## Guarantees`) and the sections beneath it are each judged on their own.
    """
    text = (brand_root / "products" / "offer-bank.md").read_text()
    per_avatar = bank_is_per_avatar(text, roster)
    lines = text.splitlines()

    def body(i):
        out = []
        for ln in lines[i + 1:]:
            if ln.startswith("## ") or ln.startswith("### "):
                break
            out.append(ln)
        return out

    def emit(head, i, out):
        key = head.split(" ")[0].strip("`").strip()
        rows = body(i)
        priced = any(re.match(r"\s*[-*]\s*(price|subscribed)\b", b, re.I)
                     or "$" in b for b in rows)
        # A FREE THING IS NOT AN OFFER. brand_b's bank carries three samples at
        # $0.00 and $1.00 straight off the storefront; you cannot ask somebody
        # to buy something that costs nothing, and a send built on one would be
        # an ask with no ask in it (2026-09-14).
        free = any(re.search(r"\bPrice:\s*\*\*\$0(\.00)?\*\*", b) for b in rows)
        if key.lower() in NOTE_KEYS or free or not (priced or per_avatar):
            out.append(f"- (note, not an offer) {head}")
        else:
            out.append(f"- OFFER `{key}` — {head}")

    out = []
    for i, line in enumerate(lines):
        if line.startswith("## "):
            head = line[3:].strip()
            if per_avatar:
                out.append(f"\n## {head}")          # an avatar's section
            else:
                emit(head, i, out)                  # one flat list of offers
        elif line.startswith("### "):
            emit(line[4:].strip(), i, out)
    out.append("\nOnly a line marked OFFER is an offer a send can carry. "
               "A note is context.")
    return "\n".join(out)


MONTHS = {m: i + 1 for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}
_DAY = r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})\b"


def order_by_dates(brand_root, year):
    """The brand's own order-by dates: [{arrive_by, order_by, label}], dated in
    `year`, from the order-by table in `operations/shipping.md` (2026-11-03).

    The table is the shipping record's — a heading naming order-by, then rows
    with a "To arrive by" and an "Order by" column. A row whose order-by cell
    is not one plain date ("arrive about Dec 4–8") states no order-by date and
    is skipped. No table, no dates: a brand that has not measured its shipping
    has no order-by date, and none is worked out for it here.
    """
    text = _text_or(brand_root / "operations" / "shipping.md")
    sec = re.search(r"^#{2,3} [^\n]*order-by[^\n]*\n(.*?)(?=^#{1,3} |\Z)", text, re.I | re.S | re.M)
    if not sec:
        return []
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")]
            for ln in sec.group(1).splitlines() if ln.strip().startswith("|")]
    if not rows:
        return []
    head = [h.lower() for h in rows[0]]
    try:
        ia = next(i for i, h in enumerate(head) if "arrive by" in h)
        io = next(i for i, h in enumerate(head) if "order by" in h)
    except StopIteration:
        return []

    def day(m):
        return datetime.date(year, MONTHS[m.group(1).lower()], int(m.group(2)))

    out = []
    for r in rows[1:]:
        if len(r) <= max(ia, io) or set(r[0]) <= set("-: "):
            continue
        cell = re.sub(r"\*", "", r[io]).strip()
        cell = re.sub(r"^[A-Za-z]+day,\s*", "", cell)
        om = re.fullmatch(_DAY, cell)
        am = list(re.finditer(_DAY, r[ia]))
        if not om or not am:
            continue
        out.append({"arrive_by": day(am[-1]).isoformat(), "order_by": day(om).isoformat(),
                    "label": re.sub(r"\*", "", r[ia]).strip()})
    return out


def lead_products(brand_root):
    """The products the brand's own `storefront-order` note leads with, in its order (2026-11-04): every
    **bold** name in that section that is a product key or a product's own section of the bank (a bundle can be
    sold before it has a product file). [] when the bank keeps no such note."""
    text = _text_or(brand_root / "products" / "offer-bank.md")
    m = re.search(r"^#{2,3}\s+storefront-order\b(.*?)(?=^#{1,3}\s|\Z)", text, re.M | re.S)
    if not m:
        return []
    keys = {k for k, _f in product_files(brand_root)} | set(re.findall(r"(?m)^## ([a-z0-9-]+) — ", text))
    out = []
    for k in re.findall(r"\*\*([a-z0-9-]+)\*\*", m.group(1)):
        if k in keys and k not in out:
            out.append(k)
    return out


def _named_products(line, products):
    """The product keys a line of prose names: the key itself (bold or not, any case), or the product's own
    title as the bank spells it, without a leading "The" and the trademark sign. In the order named."""
    low = line.lower().replace("™", "")
    hits = []
    for key, title in products.items():
        t = re.sub(r"[™®]", "", title or "").strip()
        names = {key.lower(), re.sub(r"^the\s+", "", t.lower())}
        pos = [low.find(n) for n in names if n and re.search(rf"(?<![a-z0-9-]){re.escape(n)}(?![a-z0-9-])", low)]
        if pos:
            hits.append((min(p for p in pos if p >= 0), key))
    return [k for _, k in sorted(hits)]


def storefront_mix(brand_root):
    """How the brand's own `storefront-order` note mixes products in a send (2026-11-04), read from its lines:
    {"lead": [the products a promo's lead sends carry together], "singles": {set: [its single products]}}.
    A line saying lead sends mix … names the lead mix; a line naming a set's sends with the option to buy …
    on its own names that set and its singles. Empty when the note says neither."""
    text = _text_or(brand_root / "products" / "offer-bank.md")
    m = re.search(r"^#{2,3}\s+storefront-order\b(.*?)(?=^#{1,3}\s|\Z)", text, re.M | re.S)
    out = {"lead": [], "singles": {}}
    if not m:
        return out
    prods = {k: product_title(f) for k, f in product_files(brand_root)}
    bullets = []
    for ln in m.group(1).splitlines():                # a bullet may wrap onto the next lines
        if ln.strip().startswith("-"):
            bullets.append(ln.strip())
        elif bullets and ln.startswith("  ") and ln.strip():
            bullets[-1] += " " + ln.strip()
        elif not ln.strip():
            bullets.append("")
    for ln in bullets:
        if not ln:
            continue
        named = _named_products(ln, prods)
        if re.search(r"\blead sends?\b.*\bmix", ln, re.I) and len(named) >= 2:
            out["lead"] = named
        elif re.search(r"\bon its own\b|\bsingles?\b|\bindividual", ln, re.I) and len(named) >= 2:
            out["singles"][named[0]] = named[1:]
    return out


def standing_offer(brand_root, roster=()):
    """What a brand sells when no sale is on (2026-11-04: every week sells something). -> (offer key, mix or None,
    lead product or None). The brand's own storefront-order note: its lead mix, else the first product it leads with;
    else its ruled `paid-funnel` section (what its ads sell); else its one front-end product (`_hero: paid`).
    (None, None, None) when the bank answers none of these — nothing is invented."""
    mix = storefront_mix(brand_root)
    if mix["lead"]:
        return mix["lead"][0], list(mix["lead"]), mix["lead"][0]
    leads = lead_products(brand_root)
    if leads:
        return leads[0], None, leads[0]
    heroes = hero_products(brand_root)
    one = next(iter(heroes.values())) if len(set(heroes.values())) == 1 else None
    offers = [ln.split("`")[1] for ln in render_offers(brand_root, roster).splitlines() if ln.startswith("- OFFER `")]
    if "paid-funnel" in offers:
        return "paid-funnel", None, one
    return (one, None, one) if one else (None, None, None)


def hero_products(brand_root):
    """{lane: product} — the front-end product of each lane, from the offer bank's own
    `_lane: <avatar>_ · _hero: paid_` line under a product's section (both the bank's rule:
    "The hero offer is the front end. One per lane"). Only lanes the bank has ruled."""
    text = _text_or(brand_root / "products" / "offer-bank.md")
    out, key = {}, None
    for ln in text.splitlines():
        if ln.startswith("## "):
            key = ln[3:].strip().split(" ")[0].strip("`")
        m = re.search(r"_lane:\s*([a-z0-9-]+)_\s*·\s*_hero:\s*paid_", ln)
        if m and key:
            out.setdefault(m.group(1), key)
    return out


def findings(brand_root):
    """CMP-2 made explicit: the evidence read into numbered findings, parsed
    deterministically from the brand's own learnings tables. The composer
    cites finding ids; the checker can verify a citation exists. Nothing
    here is invented — a table that does not parse yields no finding."""
    f = brand_root / "email-sms" / "learnings.md"
    out = []
    if not f.is_file():
        return out
    text = f.read_text()

    def table(heading):
        # the table may sit below prose; take the first table before the
        # next heading
        sec = re.search(rf"## {heading}\n(.*?)(?=\n## |\Z)", text, re.S)
        if not sec:
            return []
        m = re.search(r"((?:\|.*\n)+)", sec.group(1))
        if not m:
            return []
        rows = []
        for ln in m.group(1).splitlines():
            cells = [re.sub(r"\*+", "", c).strip() for c in ln.strip("|").split("|")]
            if len(cells) >= 4 and not set(cells[0]) <= {"-", " ", ":"}:
                rows.append(cells)
        return rows[1:]  # drop header

    for r in table("By category"):
        out.append(f"per recipient, {r[0]} earns {r[3]} across {r[1]} sends")
    hours = table("By send hour")
    if hours:
        best = hours[0]
        out.append(f"the best-evidenced hour is {best[0]} at {best[3]} per "
                   f"recipient ({best[1]} sends behind it)")
    for r in table("Local time vs one fixed time"):
        out.append(f"{r[0]}: {r[3]} per recipient over {r[1]} sends")
    for r in table("The opportunity"):
        if len(r) >= 4 and r[3] and r[3] not in ("balanced", ""):
            out.append(f"{r[0]} is {r[3]}: {r[1]} of sends against {r[2]} of revenue")
    return [f"[F{i+1}] {t}" for i, t in enumerate(out)]


def responsiveness(brand_root):
    """What each audience actually DOES when it is sent to — revenue per
    recipient against unsubscribe cost, joined from the ledger (who each
    send went to) and the performance record (what it did).

    This is the signal frequency follows (owner: cadence is not a rule; no
    ceiling, no floor — what goes out is decided by what a send earns). An
    audience that earns well and unsubscribes little can carry more; one
    that earns little and costs list can carry less. The number of emails is
    an OUTPUT of that, never a band to sit inside."""
    lf = brand_root / "email-sms" / "ledger.json"
    pf = brand_root / "email-sms" / "performance.json"
    if not (lf.is_file() and pf.is_file()):
        return None
    from collections import defaultdict
    led = {r["id"]: r for r in json.loads(lf.read_text()) if r.get("id")}
    agg = defaultdict(lambda: {"sends": 0, "rec": 0, "rev": 0.0,
                               "unsub": 0, "clicks": 0})
    for p in json.loads(pf.read_text()):
        r = led.get(p["groupings"].get("campaign_id"))
        if not r:
            continue
        s = p["statistics"]
        for a in (r.get("audiences") or []):
            d = agg[a]
            d["sends"] += 1
            d["rec"] += s.get("recipients", 0) or 0
            d["rev"] += s.get("conversion_value", 0) or 0
            d["unsub"] += s.get("unsubscribes", 0) or 0
            d["clicks"] += s.get("clicks_unique", 0) or 0
    rows = [(a, d) for a, d in agg.items() if d["sends"] >= 3 and d["rec"] > 0]
    if not rows:
        return None
    rows.sort(key=lambda x: -(x[1]["rev"] / x[1]["rec"]))
    out = []
    for a, d in rows[:12]:
        out.append({"audience": a, "sends": d["sends"], "recipients": d["rec"],
                    "rev_per_recipient": round(d["rev"] / d["rec"], 4),
                    "unsub_pct": round(100 * d["unsub"] / d["rec"], 3),
                    "click_pct": round(100 * d["clicks"] / d["rec"], 2)})
    return {"audiences": out, "measured": len(rows)}


def cadence_history(brand_root):
    """What this brand has done per month, per audience — context, not a
    limit. Reported so a plan can be compared to practice, never to bound it."""
    f = brand_root / "email-sms" / "ledger.json"
    if not f.is_file():
        return None
    from collections import Counter, defaultdict
    per, allm = defaultdict(Counter), Counter()
    for r in json.loads(f.read_text()):
        mo = (r.get("sent") or "")[:7]
        if not mo:
            continue
        allm[mo] += 1
        for a in (r.get("audiences") or []):
            per[a][mo] += 1
    bands = []
    for aud, months in per.items():
        if len(months) >= 3:
            v = sorted(months.values())
            bands.append((v[len(v) // 2], max(v), sum(v)))
    if not bands:
        return None
    bands.sort(key=lambda x: -x[2])
    heavy_med, heavy_max = bands[0][0], bands[0][1]
    meds = sorted(b[0] for b in bands)
    typical = meds[len(meds) // 2]
    av = sorted(allm.values())
    return {"heaviest_median": heavy_med, "heaviest_max": heavy_max,
            "typical_median": typical, "audiences_measured": len(bands),
            "account_median_sends_per_month": av[len(av) // 2],
            "months_measured": len(allm)}


def coldness(brand_root, catalogue):
    """CMP-3 made explicit: how cold every cell and every type is, computed
    from the brand's own record — the classified sends for types, the
    adopted calendars for cells. The known limit is stated in the output:
    historical sends carry no avatar tag, so cell coldness starts at the
    first adopted calendar."""
    out = []
    today = datetime.date.today()
    cl_f = brand_root / "email-sms" / "classified.json"
    if cl_f.is_file():
        cl = json.loads(cl_f.read_text())
        last = {}
        for r in cl:
            t = r.get("type")
            if t and r.get("sent"):
                last[t] = max(last.get(t, r["sent"]), r["sent"])
        never = [t["key"] for t in catalogue["types"] if t["key"] not in last]
        out.append("## Types — days since last sent (from the classified record)")
        for t, d in sorted(last.items(), key=lambda x: x[1]):
            days = (today - datetime.date.fromisoformat(d)).days
            out.append(f"- `{t}` — {days} days cold (last {d})")
        if never:
            out.append(f"- never sent at all: {', '.join(f'`{t}`' for t in sorted(never))}")
    cells = {}
    for cal in sorted(brand_root.glob("email-sms/calendar-*.json")):
        for s in json.loads(cal.read_text()).get("slots", []):
            key = (s.get("avatar") or "none", s.get("sub_avatar") or "none")
            cells[key] = max(cells.get(key, s["date"]), s["date"])
    out.append("")
    out.append("## Cells — last time each avatar/sub-avatar was planned "
               "(adopted calendars only; historical sends carry no avatar tag)")
    if cells:
        for (av, sub), d in sorted(cells.items(), key=lambda x: x[1]):
            cell = av if sub == "none" else f"{av} / {sub}"
            out.append(f"- {cell} — last planned {d}")
    else:
        out.append("- no adopted calendar yet — every cell is cold")
    return "\n".join(out)


def per_person(slots, resp=None):
    """CMP-11's missing arithmetic: what one reader in each segment receives
    this month. REPORTED, not capped — cadence is derived, never set; a cap
    is a rule only the owner can bind (open question on the cards)."""
    seg = Counter(x for s in slots for x in (s.get("segments") or [s.get("segment")]))
    lines = ["## What one person receives this month, per segment",
             "(a send to several segments reaches everyone in each of them)", ""]
    for k, v in seg.most_common():
        lines.append(f"- {k}: {v} email(s)")
    if resp:
        a = resp["audiences"]
        lines += ["", "### What sending actually earns here (the brand's own record)",
                  f"- measured across {resp['measured']} audiences with 3+ sends",
                  f"- best: ${a[0]['rev_per_recipient']:.4f} per recipient at "
                  f"{a[0]['unsub_pct']}% unsubscribe",
                  f"- weakest of the top set: ${a[-1]['rev_per_recipient']:.4f} at "
                  f"{a[-1]['unsub_pct']}%",
                  "- frequency follows this, not a cap: an audience that earns "
                  "well at low unsubscribe cost can carry more sends; one that "
                  "does not, carries fewer."]
    return "\n".join(lines)


def parse_slots(output):
    m = re.search(r"```json\s*(\[.*?\])\s*```", output, re.S)
    if not m:
        sys.exit("the composer returned no ```json slots block — read the raw output")
    return json.loads(m.group(1))


def check(slots, month, types_by_key, sends_dir, roster,
          subs_by_avatar=None, segments=(), no_offer_avatars=frozenset(),
          cells=None, moment_windows=None, moment_keys=None, retail_holidays=()):
    """SLOT.md's rules, checked in code. Errors break the plan; warnings stand
    beside it — a human reads both.

    moment_windows: {moment key: [(start, end), ...]} for THIS month, from
    the brand's anchored calendar; (None, None) means usable any time.
    moment_keys: every key the brand's calendar knows, in or out of window.
    A slot whose occasion names a moment outside its window is a break —
    that is how Black Friday landed in October (owner, 2026-09-02)."""
    errors, warns = [], []
    ids = {s.get("id") for s in slots}
    earned = {}   # segment -> [date of each earns/sets-up slot]
    moment_windows = moment_windows or {}
    moment_keys = set(moment_keys or ())
    for s in slots:
        sid = s.get("id", "?")
        try:
            d = datetime.date.fromisoformat(s["date"])
            if f"{d:%Y-%m}" != month:
                errors.append(f"{sid}: date {s['date']} is outside {month}")
        except Exception:
            errors.append(f"{sid}: unreadable date {s.get('date')!r}")
            continue
        # DATES ARE REAL: an occasion naming a moment must sit inside that
        # moment's window for this month.
        occ = (s.get("occasion") or "").lower()
        for key in sorted(moment_keys, key=len, reverse=True):
            if key and re.search(r"(?<![a-z0-9-])" + re.escape(key) + r"(?![a-z0-9-])", occ):
                wins = moment_windows.get(key)
                if not wins:
                    errors.append(f"{sid}: occasion names `{key}`, which does not land in "
                                  f"{month} at all — a moment is used only in its window")
                elif not any(a is None or a <= s["date"] <= b for a, b in wins):
                    errors.append(f"{sid}: `{key}` is dated {s['date']}, outside its window "
                                  + ", ".join(f"{a}..{b}" for a, b in wins))
                break
        for sg in (s.get("segments") or [s.get("segment")]):
            if sg not in segments:
                errors.append(f"{sid}: segment {sg!r} is not in this brand's segment vocabulary")
        av = s.get("avatar")
        # "mixed" is legal and meaningful: the slot carries variants across
        # avatars, which is how a segment gets reached (RULED 2026-08-31).
        if av not in roster and av not in ("none", "mixed"):
            errors.append(f"{sid}: avatar {av!r} is not on the roster (or 'none')")
        # sub-avatars were retired from planning (RULED 2026-08-31) — a slot
        # carrying one is a leftover, flagged as a warning, never a break.
        if s.get("sub_avatar") and str(s["sub_avatar"]).lower() not in ("none", "unspecified", ""):
            warns.append(f"{sid}: carries a sub_avatar ({s['sub_avatar']!r}) — "
                         "that level was retired from planning; ignore or drop it")
        t = types_by_key.get(s.get("type"))
        if not t:
            errors.append(f"{sid}: type {s.get('type')!r} is not in the catalogue")
            continue
        if s.get("category") != CATEGORY[t["well"]]:
            errors.append(f"{sid}: category {s.get('category')!r} but "
                          f"`{t['key']}` is {CATEGORY[t['well']]}")
        if s.get("role") != t["role"]:
            errors.append(f"{sid}: role {s.get('role')!r} but the type carries {t['role']!r}")
        if not isinstance(s.get("hour"), int) or not 0 <= s["hour"] <= 23:
            errors.append(f"{sid}: hour {s.get('hour')!r} is not 0-23")
        for ref_field in ("follows", "then"):
            ref = s.get(ref_field)
            if not ref or ref in ids:
                continue
            if "contingent" in str(ref).lower():
                continue          # "last-chance (contingent)" is a legal answer
            errors.append(f"{sid}: {ref_field} names {ref!r}, which is not a slot")
        off = str(s.get("offer") or "none").strip().lower()
        if av in no_offer_avatars and not off.startswith("none"):
            why = str(s.get("why") or "")
            # An avatar with no offer section can still legitimately carry
            # one it borrowed on the record — buying FOR someone whose
            # section does have it (a gift-buyer riding fed-up-king's offer).
            # The stage already said so in the open with [UNFILLED: ...]; a
            # documented borrow is a warning to read, not a break to fix.
            if "[unfilled" in why.lower() and "offer bank" in why.lower():
                warns.append(f"{sid}: {av} carries offer {s['offer']!r} borrowed "
                             "from another avatar's section — read the why")
            else:
                errors.append(f"{sid}: {av} carries offer {s['offer']!r} — the offer "
                              "bank has no section for this avatar")
        src = s.get("source", "")
        if src and not src.startswith("[UNFILLED") and not (sends_dir / src).is_file():
            errors.append(f"{sid}: source {src!r} is not in the sends library")
    def segs_of(x):
        return set(x.get("segments") or [x.get("segment")])
    # every ask earned — an earns/sets-up slot to the same segment, earlier
    for s in sorted(slots, key=lambda x: x.get("date", "")):
        role = s.get("role")
        if role in ("earns", "sets-up", "closes"):
            for seg in segs_of(s):
                earned.setdefault(seg, []).append(s["date"])
        if role == "asks":
            for seg in segs_of(s):
                prior = [d for d in earned.get(seg, []) if d < s.get("date", "")]
                if not prior and "already-sent" not in (s.get("why") or "").lower() \
                        and not (s.get("follows") in ids):
                    warns.append(f"{s.get('id')}: asks {seg} with no earns slot before it "
                                 "this month — the why must name what earned it")
    # obligations met — a then-type slot later, same segment
    by_date = sorted(slots, key=lambda x: x.get("date", ""))
    for s in by_date:
        t = types_by_key.get(s.get("type"))
        if not t or not t.get("then") or s.get("role") == "recovers":
            continue
        if s.get("then") in ids or s.get("then") == "contingent":
            continue
        later = [x for x in by_date if x.get("date", "") > s.get("date", "")
                 and x.get("type") in t["then"] and segs_of(x) & segs_of(s)]
        if not later:
            warns.append(f"{s.get('id')}: type `{t['key']}` obliges {t['then']} and "
                         "nothing meets it — schedule the follow-up or drop the slot")
    # PROMOTIONAL ARC (RULED, owner, 2026-08-31): a promotional moment is
    # never one email. Every offer-carrying ask needs a WARM-UP before it and
    # a COOL-DOWN after it, to the same segment, linked by follows/then — or,
    # for an ask inside a holiday period's arc (2026-11-03: two to three sends
    # a day, 2026-10-09), linked by the arc they all name: the arc's own
    # warm-up before it and its own close after it, to the same segment.
    WARM = {"earns", "sets-up"}
    COOL = {"recovers", "closes"}
    by_id = {s.get("id"): s for s in slots}
    for s in slots:
        off = str(s.get("offer") or "none").strip().lower()
        if s.get("role") != "asks" or off.startswith("none"):
            continue
        seg, sid, when = s.get("segment"), s.get("id"), s.get("date", "")
        warm = [x for x in slots
                if segs_of(x) & segs_of(s) and x.get("date", "") < when
                and x.get("role") in WARM
                and (x.get("then") == sid or s.get("follows") == x.get("id"))]
        cool_ref = by_id.get(s.get("then"))
        cool = (cool_ref and segs_of(cool_ref) & segs_of(s)
                and cool_ref.get("date", "") > when
                and cool_ref.get("role") in COOL)
        arc = s.get("arc")
        if arc:
            members = [x for x in slots if x.get("arc") == arc and x is not s and segs_of(x) & segs_of(s)]
            warm = warm or [x for x in members if x.get("date", "") < when and x.get("role") in WARM]
            cool = cool or any(x.get("date", "") > when and x.get("role") in COOL for x in members)
        if s.get("type") == "early-access" and s.get("arc"):
            # early access opens the arc for the best customers (2026-11-04): the arc's own warm-up and close
            # stand around it, whichever audience they go to, so a VIP list that is not live gets one send, not an arc
            arc_all = [x for x in slots if x.get("arc") == s["arc"] and x is not s]
            warm = warm or [x for x in arc_all if x.get("role") in WARM and x.get("date", "") <= when]
            cool = cool or any(x.get("role") in COOL and x.get("date", "") > when for x in arc_all)
        if not warm:
            errors.append(f"{sid}: promotional ask carrying offer "
                          f"{s.get('offer')!r} has no WARM-UP — a promotional "
                          "moment is never one email; an earns/sets-up slot to "
                          f"{seg} must precede it and name it in `then`")
        if not cool:
            errors.append(f"{sid}: promotional ask carrying offer "
                          f"{s.get('offer')!r} has no COOL-DOWN — it must name "
                          f"a recovers/closes slot to {seg} in `then`, dated "
                          "after it")
    # AN SMS IS A COMPANION (2026-11-04): it follows an email of the same day and audience, never stands alone
    for s in slots:
        if s.get("channel") != "sms":
            continue
        e = by_id.get(s.get("follows"))
        if not (e and e.get("channel", "email") == "email" and e.get("date") == s.get("date")
                and segs_of(e) & segs_of(s)):
            errors.append(f"{s.get('id')}: an SMS is the companion of an email — it must follow an email "
                          "sent the same day to the same audience, named in `follows`")
    # The plan must match the decision it was built from: one slot per SEND.
    # Variants live inside a slot; a variant split into its own slot inflates
    # what a person receives (hit 2026-08-31).
    if cells:
        live = {c.get("segment") for c in cells.get("serve", []) if c.get("live", True)}
        for s in slots:
            for sg in segs_of(s):
                if live and sg not in live and not (s.get("early_access_call") and s.get("type") == "early-access"):
                    errors.append(f"{s.get('id')}: sends to {sg}, which "
                                  "the cells stage did not make live this month")
    held = [s for s in slots if "HELD OPEN" in (s.get("occasion") or "").upper()]
    if len(held) < 2:
        warns.append(f"only {len(held)} HELD OPEN slot(s) — the rule asks for at "
                     "least two, because live moments cannot be planned")
    # a retail holiday in the month that nothing serves is an opportunity the
    # brand has not claimed — never silent
    used = " ".join((s.get("occasion") or "") for s in slots).lower()
    for r in retail_holidays:
        if r.get("span", 1) > 1:
            continue                      # a composite span (Cyber Week) is its days
        covered = any(a is not None and a <= r["start"] <= b
                      for wins in moment_windows.values() for a, b in wins)
        if r["key"] not in used and not covered:
            warns.append(f"`{r['key']}` ({r['name']}, {r['start']}) is a {r['kind']} holiday "
                         "in this month and the brand's calendar has no moment for it — "
                         "add one to calendar/moments.json to plan against it, or leave "
                         "it unclaimed on purpose")
    return errors, warns



def product_files(brand_root):
    """Every product a brand declares, as (slug, file). Two layouts are read:
    flat `products/<slug>.md`, and a folder per product,
    `products/<slug>/product.md` — the folder is the convention; a brand is
    never reshaped to suit this reader."""
    root = brand_root / "products"
    found = {}
    for f in root.glob("*.md"):
        if f.name not in ("README.md", "offer-bank.md"):
            found[f.stem] = f
    for f in root.glob("*/product.md"):
        found.setdefault(f.parent.name, f)
    return sorted(found.items())


def product_title(f):
    """The first `# ` heading; else a front-matter `name:`; else the slug."""
    lines = f.read_text().splitlines()
    name = None
    if lines and lines[0].strip() == "---":
        for ln in lines[1:]:
            if ln.strip() == "---":
                break
            if ln.startswith("name:"):
                name = ln.split(":", 1)[1].strip()
    for ln in lines:
        if ln.startswith("# "):
            return ln[2:].strip()
    return name or (f.parent.name if f.name == "product.md" else f.stem)


def render_products(brand_root):
    return "\n".join(f"- `{slug}` — {product_title(f)}"
                     for slug, f in product_files(brand_root))

