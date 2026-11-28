#!/usr/bin/env python3
"""promo-pack — one offer change in, one pack out: a hand-off for every workflow the offer has to reach.

    python3 components/promo-pack/machine/pack.py build  --brand <brand> --month <YYYY-MM> [--moment <name>]
                                                         [--stock <runway.json>] [--videos 5] [--statics 5]
    python3 components/promo-pack/machine/pack.py hand   --brand <brand> --moment <name> [--only static,video,sms] [--dry-run]
    python3 components/promo-pack/machine/pack.py status --brand <brand> --moment <name>
    python3 components/promo-pack/machine/pack.py tick   [--brand <brand>] [--lead-days 14] [--stock <runway.json>]

`tick` is the trigger, run when a month's calendar is planned (marketing-calendar's skill runs it with --month):
it builds the pack for every promotion touching that month, hands everything off and says when the pack is loaded.
With no --month it takes promotions within --lead-days.

Reads the brand's offer bank (brands/<brand>/products/offer-bank.md: the promo-calendar row for the month and every
line the bank lets creative use word for word), the month's calendar (runs/marketing-calendar/<brand>/<YYYY-MM>/
slots.json), the brand's winners (runs/winners/<brand>/bank.json) and, when given, a stock runway read.

Writes runs/promo-pack/<brand>/<moment>/: pack.json (the contract), PACK.md (its copy for people) and
handoffs/<id>/ (what each workflow is handed). Whoever triggers it, it runs: there is no approval step. Nothing it
starts goes live, sends or spends money: the doors make plans and drafts, and going live stays inside each workflow.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
DEFS = json.loads((COMP / "definitions" / "handoffs.json").read_text())
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
FLAGS = {"LATE", "ORDER THIS WEEK"}


def root():
    return Path(os.environ.get("PROMO_PACK_ROOT") or COMP.parent.parent).resolve()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "promo"


def plain(s):
    return re.sub(r"\s+", " ", str(s).replace("™", "").replace("®", "")).strip().lower()


# ---------------------------------------------------------------------------------------------- the offer bank --
def bank_text(brand, base=None):
    f = (base or root()) / "brands" / brand / "products" / "offer-bank.md"
    if not f.is_file():
        raise SystemExit("no offer bank: brands/%s/products/offer-bank.md" % brand)
    return f.read_text()


def sections(text):
    """Every `## key — Title` / `### key — Title` heading: key -> title."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"^#{2,3}\s+([a-z0-9][a-z0-9-]*)\s+—\s+(.+)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def parse_dates(cell, year_hint=None):
    """'Dec 1 – Dec 25, 2026 (anything)' -> (date, date)."""
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})\s*[–-]\s*(?:([A-Za-z]{3})[a-z]*\.?\s+)?(\d{1,2}),?\s*(\d{4})?", cell)
    if not m:
        return None
    y = int(m.group(5) or year_hint or dt.date.today().year)
    m1 = MONTHS.get(m.group(1).lower())
    m2 = MONTHS.get((m.group(3) or m.group(1)).lower())
    if not m1 or not m2:
        return None
    return dt.date(y, m1, int(m.group(2))), dt.date(y, m2, int(m.group(4)))


def promo_rows(text):
    """The rows of the bank's promo-calendar table, each with its window."""
    lines, out, on, head = text.splitlines(), [], False, None
    for line in lines:
        s = line.strip()
        if re.match(r"^#{2,3}\s+promo-calendar\b", s):
            on = True
            continue
        if on and s.startswith("#"):
            break
        if on and s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if head is None:
                head = [c.lower() for c in cells]
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            row = dict(zip(head, cells))
            win = parse_dates(row.get("dates", ""))
            if win:
                out.append({"dates": row.get("dates", ""), "promo": row.get("promo", ""), "code": row.get("code", ""),
                            "approved": row.get("approved", ""), "start": win[0].isoformat(), "end": win[1].isoformat()})
    return out


def surfaces_of(intro):
    t = intro.lower()
    found = [name for name, pat in (("store", r"store"), ("email", r"email"), ("sms", r"\btexts?\b|sms"),
                                    ("funnel", r"funnel"), ("pop-up", r"pop-?up"), ("ads", r"\bads?\b"))
             if re.search(pat, t)]
    return found or ["all"]


QUOTE = re.compile(r"[\"“]([^\"”]{3,160})[\"”]")


def word_lines(text):
    """Every line the bank lets creative use word for word, with the section it sits in and its surfaces.
    A `- Funnel offer` bullet's bold line is a funnel line. A line marked '(through <date>)' carries its end."""
    out, key, intro, indent = [], None, None, None
    for raw in text.splitlines():
        s = raw.strip()
        m = re.match(r"^#{1,3}\s+([a-z0-9][a-z0-9-]*)\s+—", s)
        if m or s.startswith("#"):
            key, intro = (m.group(1) if m else key), None
            continue
        lead = len(raw) - len(raw.lstrip())
        if "word for word" in s.lower():
            intro, indent = s, lead
            if s.startswith("|"):          # a table row: the lines sit in the row itself
                cells = s.strip("|").split("|")
                for q in QUOTE.findall("|".join(cells[1:])):
                    out.append({"line": q.strip(), "section": key, "surfaces": surfaces_of(cells[0])})
                intro = None
            continue
        if intro and s.startswith("-") and lead > indent:
            for q in QUOTE.findall(s):
                through = re.search(r"\(through ([^)]+)\)", s)
                note = re.search(r"[\"”]\s*\(([^)]+)\)", s)
                out.append({"line": q.strip(), "section": key, "surfaces": surfaces_of(intro),
                            "through": through.group(1) if through else None,
                            "note": note.group(1) if note and not through else None})
            continue
        if intro and not (s.startswith("-") and lead > indent):
            intro = None
        if re.match(r"^-\s*Funnel offer", s, re.I):
            for b in re.findall(r"\*\*([^*]{3,120})\*\*", s)[:1]:
                out.append({"line": b.strip(), "section": key, "surfaces": ["funnel", "ads"]})
    return out


def retired(line, start):
    """True when the line carries '(through <date>)' and that date is before the window opens."""
    if not line.get("through"):
        return False
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})(?:,?\s*(\d{4}))?", line["through"])
    if not m or m.group(1).lower() not in MONTHS:
        return False
    end = dt.date(int(m.group(3) or start.year), MONTHS[m.group(1).lower()], int(m.group(2)))
    return end < start


def dated_elsewhere(line, start, end):
    """A line that names a month outside the window ('Order by Nov 20') does not belong to this pack."""
    names = re.findall(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}\b", line["line"])
    months = {start.month, end.month}
    return bool(names) and not any(MONTHS[n.lower()] in months for n in names)


# --------------------------------------------------------------------------------------------- the calendar --
def slots(brand, month, base=None):
    f = (base or root()) / "runs" / "marketing-calendar" / brand / month / "slots.json"
    if not f.is_file():
        return None, f
    d = json.loads(f.read_text())
    return (d.get("slots") if isinstance(d, dict) else d), f


def in_window(s, start, end):
    try:
        return start <= dt.date.fromisoformat(s.get("date") or "") <= end
    except ValueError:
        return False


def email_snapshot(slot, brand, base):
    """email-production's own calendar hand-off check for one send (its public snapshot), or the reason it holds."""
    try:
        home = str(base / "components" / "email-production")
        if home not in sys.path:
            sys.path.insert(0, home)
        import calendar_handoff as CH
        snap = CH.snapshot(slot, brand)
        return {"state": "ready", "fingerprint": snap.get("fingerprint"), "schedule": snap.get("schedule")}
    except ImportError:
        return {"state": "unchecked", "why": "email-production is not in this checkout"}
    except Exception as ex:   # calendar_handoff.Held and any malformed send
        return {"state": "held", "why": str(ex)}


def gifts_by_offer(words, titles):
    """Each offer's free gift, from lines shaped '<offer> + Free <gift>': offer key -> [gift]."""
    out = {}
    for w in words:
        m = re.match(r"^(.+?)\s*\+\s*free\s+(.+)$", w["line"], re.I)
        if not m:
            continue
        for key, title in titles.items():
            if plain(m.group(1)) and plain(m.group(1)) in plain(title):
                out.setdefault(key, []).append(m.group(2).strip())
    return out


def written(brand, slot_id, channel, words, dropped, base, gifts=()):
    """Whether email-production has already written this send, and any line in it the window does not allow:
    a funnel-only line in an email or text, a line the bank has retired, or a selling send that never names its
    offer's free gift."""
    home = base / "runs" / "email-production" / brand
    if not slot_id or not home.is_dir():
        return {"state": "not written"}
    pat = "%s-%s-sms" % (brand, slot_id) if channel == "sms" else "%s-%s--*" % (brand, slot_id)
    files = [f for d in sorted(home.glob(pat)) for f in (d / "deliverable" / "email.json", d / "sms.json") if f.is_file()]
    if not files:
        return {"state": "not written"}
    text = plain(" ".join(f.read_text() for f in files))
    funnel_only = [w["line"] for w in words if set(w["surfaces"]) <= {"funnel", "ads"}]
    flags = ["funnel line in a %s: %s" % (channel, l) for l in funnel_only if plain(l) in text]
    flags += ["retired line: %s" % d["line"] for d in dropped if d["why"].startswith("retired") and plain(d["line"]) in text]
    flags += ["never names the free gift: %s" % g for g in gifts
              if " ".join(plain(g).split()[-2:]) not in text]
    return {"state": "written", "versions": len(files), "flags": flags}


# ------------------------------------------------------------------------------------------------ winners --
def winners(brand, kind, n, start, base):
    """The brand's top winners of one format, ranked by spend in their latest audit, active in the last 6 months
    when any are (the winner definition: the top spenders first)."""
    f = base / "runs" / "winners" / brand / "bank.json"
    if not f.is_file() or n <= 0:
        return []
    rows = [r for r in json.loads(f.read_text()).get("rows", []) if (r.get("format") or "").lower() == kind]

    def audit(r):
        snaps = [s for s in r.get("snapshots") or [] if s.get("kind") == "audit"]
        return snaps[-1] if snaps else {}

    recent_from = (start.replace(day=1) - dt.timedelta(days=183)).strftime("%Y-%m")
    recent = [r for r in rows if (audit(r).get("last") or "") >= recent_from]
    pool = recent if len(recent) >= n else rows
    pool = sorted(pool, key=lambda r: -(audit(r).get("spend") or 0))
    out = []
    for r in pool[:n]:
        a = audit(r)
        out.append({"id": r.get("id"), "name": r.get("name"), "ad_id": (r.get("ad_ids") or [None])[0],
                    "spend": a.get("spend"), "purchases": a.get("purchases"), "cpa": a.get("cpa"),
                    "last": a.get("last"), "state": r.get("state")})
    return out


# -------------------------------------------------------------------------------------------------- stock --
def stock_read(path, products, end):
    """The stock rows for every product the offer names or gives away, and the ones that block the pack."""
    if not path:
        return {"read": False, "rows": [], "blockers": [], "why": DEFS["stock"]["gap"]}
    rows = json.loads(Path(path).read_text())
    if isinstance(rows, dict):
        rows = rows.get("rows", [])
    mine, blockers = [], []
    for r in rows:
        name = plain(r.get("name", ""))
        hit = [p for p in products if plain(p) and plain(p) in name]
        if not hit:
            continue
        r = dict(r, product=hit[0])
        mine.append(r)
        out = r.get("runs_out_with_backup") or r.get("runs_out") or ""
        why = [r["status"]] if r.get("status") in FLAGS else []
        if out and out <= end.isoformat():
            why.append("runs out %s, inside the window" % out)
        if why:
            blockers.append(dict(r, why=why))
    same = Counter((b.get("available"), b.get("per_day")) for b in blockers)
    for b in blockers:
        if same[(b.get("available"), b.get("per_day"))] > 1:
            b["why"].append("reads the same count as another item: the warehouse may be counting one shared part")
    return {"read": True, "source": Path(path).name, "rows": mine, "blockers": blockers}


# --------------------------------------------------------------------------------------------------- build --
def fingerprint(words):
    return hashlib.sha256(json.dumps(words, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def pack_dir(brand, moment, base=None):
    return (base or root()) / "runs" / "promo-pack" / brand / slug(moment)


def build(brand, month, moment=None, stock=None, n_videos=5, n_statics=5, base=None, today=None):
    base = base or root()
    today = today or dt.date.today()
    text = bank_text(brand, base)
    titles = sections(text)
    y, mo = (int(x) for x in month.split("-"))
    first = dt.date(y, mo, 1)
    last = (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    rows = [r for r in promo_rows(text) if r["start"] <= last.isoformat() and r["end"] >= first.isoformat()]
    if not rows:
        raise SystemExit("the offer bank has no promo-calendar row for %s: the offer change starts there "
                         "(Offer change workflow)" % month)
    row = rows[0]
    start, end = dt.date.fromisoformat(row["start"]), dt.date.fromisoformat(row["end"])

    cal, cal_file = slots(brand, month, base)
    cal = cal or []
    win = [s for s in cal if in_window(s, start, end)]
    occ = Counter(s.get("occasion") for s in win if s.get("occasion") and s.get("type") == "sale-window")
    moment = moment or (occ.most_common(1)[0][0] if occ else "promo-%s" % month)
    order_by = Counter(s.get("order_by") for s in win if s.get("order_by")).most_common(1)
    order_by = order_by[0][0] if order_by else None

    lines = word_lines(text)
    keep, dropped = [], []
    for l in lines:
        if retired(l, start):
            dropped.append(dict(l, why="retired: through %s" % l["through"]))
        elif dated_elsewhere(l, start, end):
            dropped.append(dict(l, why="names a date outside the window"))
        elif l["surfaces"] == ["pop-up"]:
            dropped.append(dict(l, why="the standing pop-up offer; inside a promo window the moment's offer leads"))
        else:
            keep.append(l)
    seen, words = set(), []
    for l in keep:
        k = (l["line"], tuple(l["surfaces"]))
        if k not in seen:
            seen.add(k)
            words.append({"line": l["line"], "section": l["section"], "surfaces": l["surfaces"],
                          "note": l.get("note")})
    kept = {w["line"] for w in words}
    dropped = [d for d in dropped if d["line"] not in kept]
    if not order_by:
        m = next((w for w in words if w["line"].lower().startswith("order by")), None)
        order_by = m["line"] if m else None
    store_words = [w for w in words if set(w["surfaces"]) & {"store", "email", "sms", "all"}]
    funnel_words = [w for w in words if "funnel" in w["surfaces"]]
    lead = store_words[0]["line"] if store_words else (words[0]["line"] if words else None)

    named = " ".join([row["promo"]] + [w["line"] for w in words])
    products = [t for k, t in titles.items() if plain(t) and plain(t) in plain(named)]
    lead_key = next((w["section"] for w in store_words if w["section"] in titles), None)
    gifts = gifts_by_offer(words, titles)
    stock_info = stock_read(stock, products, end)

    offer = {"row": row, "lead_line": lead, "words": words, "dropped": dropped, "order_by": order_by,
             "products": products, "lead_section": lead_key}
    offer["fingerprint"] = fingerprint({"row": row["promo"], "lead": lead, "words": words, "order_by": order_by})

    out = pack_dir(brand, moment, base)
    label = "%s-%s-promo-pack" % (slug(moment), start.year)
    ready_open = (start - dt.timedelta(days=1)).isoformat()
    ready_preview = (start - dt.timedelta(days=2)).isoformat()
    avatar = Counter(v.get("avatar") for s in win for v in s.get("variants") or []
                     if v.get("avatar") and v.get("avatar") != "mixed").most_common(1)
    avatar = avatar[0][0] if avatar else "core"
    handoffs = []
    for h in DEFS["handoffs"]:
        door = h["door"] if h["door"] and (not h["door"].get("requires")
                                           or (base / h["door"]["requires"]).is_file()) else None
        item = {"id": h["id"], "workflow": h["workflow"], "type": h["type"], "role": h["role"], "makes": h["makes"],
                "door": door, "gap": h.get("gap") if not door else None,
                "note": h.get("gap") if door and h["id"] == "video" else None}
        if h["id"] in ("email", "sms"):
            sends = sorted((s for s in win if (s.get("channel") or "email") == h["id"]),
                           key=lambda s: (s["date"], s.get("hour") or 0))
            selling = [s for s in sends if (s.get("offer") or "none") != "none"]
            unknown = sorted({s["offer"] for s in selling if s["offer"] not in titles})
            rows_ = []
            for s in sends:
                due = dt.date.fromisoformat(s["date"]) - dt.timedelta(days=1)
                while due.weekday() >= 5:
                    due -= dt.timedelta(days=1)
                r = {"id": s.get("id"), "date": s["date"], "hour": s.get("hour"), "offer": s.get("offer"),
                     "type": s.get("type"), "ready_by": due.isoformat()}
                if h["id"] == "email":
                    r["check"] = email_snapshot(s, brand, base)
                r["written"] = written(brand, s.get("id"), h["id"], words, dropped, base,
                                       gifts.get(s.get("offer") or "", []))
                rows_.append(r)
            after = [s.get("id") for s in cal if (s.get("channel") or "email") == h["id"]
                     and not in_window(s, start, end) and (s.get("date") or "") > end.isoformat()]
            item.update(briefs=len(sends), selling=len(selling), dates=sorted({s["date"] for s in sends}),
                        ready_by=rows_[0]["ready_by"] if rows_ else None, sends=rows_,
                        offers=dict(Counter(s.get("offer") or "none" for s in sends)),
                        not_in_bank=unknown, after_window=after,
                        calendar="runs/marketing-calendar/%s/%s/slots.json" % (brand, month))
            item["args"] = {"run": "runs/marketing-calendar/%s/%s" % (brand, month),
                            "slots": ",".join(r["id"] for r in rows_ if r["id"] and r["written"]["state"] != "written")}
        elif h["id"] == "video":
            picked = winners(brand, "video", n_videos, start, base)
            item.update(briefs=len(picked), winners=picked, ready_by=ready_open, dates=[row["start"]],
                        ending=[x for x in [lead] + [w["line"] for w in words if w["line"].lower().startswith("order by")]
                                if x],
                        args={"label": label, "plan_file": "runs/promo-pack/%s/%s/handoffs/video/campaign-plan.md"
                              % (brand, slug(moment))})
        elif h["id"] == "static":
            picked = winners(brand, "image", n_statics, start, base)
            item.update(briefs=max(len(picked), n_statics), winners=picked, ready_by=ready_open,
                        dates=[row["start"]],
                        args={"label": label, "product": lead_key or "", "avatar": avatar})
        elif h["id"] == "store":
            item.update(briefs=1, ready_by=ready_preview, dates=[row["start"], row["end"]],
                        words=[w["line"] for w in store_words], args={"moment": moment, "year": str(start.year)})
        elif h["id"] == "funnel":
            item.update(briefs=len({w["section"] for w in funnel_words}) or 0, ready_by=ready_preview,
                        dates=[row["start"], row["end"]], words=[w["line"] for w in funnel_words])
        handoffs.append(item)

    gaps = [{"handoff": h["id"], "workflow": h["workflow"], "gap": h["gap"]} for h in handoffs if h.get("gap")]
    gaps += [{"handoff": h["id"], "workflow": h["workflow"], "gap": h["note"]} for h in handoffs if h.get("note")]
    if not stock_info["read"]:
        gaps.append({"handoff": "stock", "workflow": "-", "gap": DEFS["stock"]["gap"]})
    else:
        gaps.append({"handoff": "stock", "workflow": "-", "gap": DEFS["stock"]["gap"] + " (read given: %s)"
                     % stock_info["source"]})
    if not cal:
        gaps.append({"handoff": "email", "workflow": "Email campaign workflow",
                     "gap": "no calendar for %s: run marketing-calendar first" % month})

    pack = {"brand": brand, "month": month, "moment": moment, "label": label, "built": today.isoformat(),
            "window": {"start": row["start"], "end": row["end"]}, "offer": offer, "stock": stock_info,
            "handoffs": handoffs, "gaps": gaps,
            "gate": {"what": "No approval step: whoever triggers the pack, it runs. Nothing it starts goes live, sends "
                             "or spends money; going live stays inside each workflow.", "fingerprint": offer["fingerprint"]},
            "reads": {"offer_bank": "brands/%s/products/offer-bank.md" % brand,
                      "calendar": str(cal_file.relative_to(base)) if cal else None,
                      "winners": "runs/winners/%s/bank.json" % brand, "stock": stock_info.get("source")}}
    write(out, pack)
    return pack, out


def load(out):
    f = out / "pack.json"
    if not f.is_file():
        raise SystemExit("no pack at %s: build it first" % out)
    return json.loads(f.read_text())


# ------------------------------------------------------------------------------------------------- hand off --
def fill(argv, args):
    return [a.format(**args) for a in argv]


def campaign_plan(pack):
    o = pack["offer"]
    lines = ["# Campaign plan: %s, %s to %s" % (pack["moment"], pack["window"]["start"], pack["window"]["end"]), "",
             "Change one thing in each winner: the offer ending. Keep everything else.", "",
             "Lead line, word for word: %s" % o["lead_line"]]
    if o.get("order_by"):
        lines.append("Order-by date: %s" % o["order_by"])
    lines += ["", "Every line the ads may use, word for word:"] + \
             ["- %s  (%s)" % (w["line"], ", ".join(w["surfaces"])) for w in o["words"]]
    lines += ["", "Lines that may not run in this window:"] + ["- %s  (%s)" % (d["line"], d["why"]) for d in o["dropped"]]
    return "\n".join(lines) + "\n"


DONE = ("handed", "loaded")


def hand(brand, moment, only=None, dry_run=False, base=None, runner=None, now=None):
    """Hand every wired workflow its part of the pack. Doors that spend nothing run, doors that only write drafts
    run for what is not written yet, and any other spending door is written into the hand-off for the role's holder.
    A hand-off already handed for these exact words is not run again."""
    base = base or root()
    now = now or dt.datetime.now()
    out = pack_dir(brand, moment, base)
    pack = load(out)
    fp = pack["offer"]["fingerprint"]
    runner = runner or (lambda argv: subprocess.run(argv, cwd=base, capture_output=True, text=True))
    done = []
    for h in pack["handoffs"]:
        if only and h["id"] not in only:
            continue
        d = out / "handoffs" / h["id"]
        d.mkdir(parents=True, exist_ok=True)
        f = d / "handoff.json"
        prior = json.loads(f.read_text()) if f.is_file() else {}
        args = dict(h.get("args") or {}, brand=brand)
        if prior.get("fingerprint") == fp and prior.get("state", "").split(":")[0] in DONE \
                and not (h["id"] in ("email", "sms") and args.get("slots")):
            done.append(prior)
            continue
        if prior.get("fingerprint") == fp and prior.get("state") == "running" and prior.get("at", "") > \
                (now - dt.timedelta(hours=20)).isoformat(timespec="seconds"):
            done.append(prior)
            continue
        rec = {"id": h["id"], "workflow": h["workflow"], "role": h["role"], "fingerprint": fp,
               "at": now.isoformat(timespec="seconds"), "runs": []}
        door = h["door"]
        if not door:
            rec["state"] = "gap"
            rec["why"] = h["gap"]
        else:
            if h["id"] == "video":
                (base / args["plan_file"]).parent.mkdir(parents=True, exist_ok=True)
                (base / args["plan_file"]).write_text(campaign_plan(pack))
                cmds = [fill(door["argv"], dict(args, ad_id=w["ad_id"], label="%s-%s" % (args["label"], w["ad_id"])))
                        for w in h.get("winners") or [] if w.get("ad_id")]
            elif h["id"] in ("email", "sms") and not args.get("slots"):
                cmds = []
            else:
                cmds = [fill(door["argv"], args)]
            rec["commands"] = [" ".join(c) for c in cmds]
            allowed = not door["spends"] or door.get("drafts_only")
            if not cmds:
                rec["state"] = "loaded: everything is written"
            elif dry_run:
                rec["state"] = "dry run: nothing run"
            elif not allowed:
                rec["state"] = "written: the role's holder runs it under the workflow's own gates"
            else:
                if door["spends"]:
                    f.write_text(json.dumps(dict(rec, state="running"), indent=1, ensure_ascii=False))
                for c in cmds:
                    r = runner(c)
                    rec["runs"].append({"command": " ".join(c), "code": r.returncode,
                                        "out": (r.stdout or "")[-400:], "err": (r.stderr or "")[-400:]})
                rec["state"] = "handed" if all(x["code"] == 0 for x in rec["runs"]) else "failed"
                if h["id"] == "static" and rec["state"] == "handed":
                    rec["sprint"] = fill_sprint(pack, base, args["label"])
        f.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        done.append(rec)
    return done


def loaded(pack, out):
    """Where every hand-off stands, and whether the pack is loaded: nothing waiting, running or failed.
    Gaps do not hold it; they stay listed."""
    rows = []
    for h in pack["handoffs"]:
        f = out / "handoffs" / h["id"] / "handoff.json"
        rec = json.loads(f.read_text()) if f.is_file() else {}
        st = rec.get("state", "not handed") if rec.get("fingerprint", pack["offer"]["fingerprint"]) == \
            pack["offer"]["fingerprint"] else "not handed"
        rows.append({"id": h["id"], "state": st})
    held = [r for r in rows if r["state"].split(":")[0] not in DONE + ("gap",)]
    return {"loaded": not held, "handoffs": rows, "held": [r["id"] for r in held]}


# ---------------------------------------------------------------------------------------------- the trigger --
def due(brand, today, lead_days, base):
    """The promo-calendar rows that are close: from `lead_days` before they open until they close."""
    try:
        rows = promo_rows(bank_text(brand, base))
    except SystemExit:
        return []
    return [r for r in rows if (dt.date.fromisoformat(r["start"]) - dt.timedelta(days=lead_days)) <= today
            <= dt.date.fromisoformat(r["end"])]


def tick(brands=None, lead_days=14, stock=None, base=None, today=None, runner=None, month=None):
    """The trigger: run when a month's calendar is planned (`month`), or with no month for every promotion within
    `lead_days` of opening. Builds the pack from the newest bank, calendar, winners and stock, hands it off, and
    says when it is loaded.
    Writes runs/promo-pack/<brand>/<moment>/status.json and one line per pack to runs/promo-pack/tick.log."""
    base = base or root()
    today = today or dt.date.today()
    brands = brands or sorted(p.name for p in (base / "brands").iterdir()
                              if p.is_dir() and not p.name.startswith("_")
                              and (p / "products" / "offer-bank.md").is_file())
    report = []
    for brand in brands:
        rows = due(brand, today, lead_days, base) if not month else [
            r for r in promo_rows(bank_text(brand, base)) if r["start"][:7] <= month <= r["end"][:7]]
        for row in rows:
            try:
                pack, out = build(brand, month or row["start"][:7], stock=stock, base=base, today=today)
            except SystemExit as ex:
                report.append({"brand": brand, "window": row["start"], "state": "held", "why": str(ex)})
                continue
            st = {"brand": brand, "moment": pack["moment"], "window": pack["window"],
                  "blockers": len(pack["stock"]["blockers"]), "at": dt.datetime.now().isoformat(timespec="seconds")}
            hand(brand, pack["moment"], base=base, runner=runner)
            st.update(loaded(pack, out))
            st["state"] = "loaded" if st["loaded"] else "loading"
            (out / "status.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
            report.append(st)
    log = base / "runs" / "promo-pack" / "tick.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as fh:
        for r in report:
            fh.write("%s  %s  %s  %s\n" % (dt.datetime.now().isoformat(timespec="seconds"), r["brand"],
                                            r.get("moment", r.get("window")), r["state"]))
    return report


def fill_sprint(pack, base, label):
    """Put the pack's words into the statics sprint the door just started (only fields still empty)."""
    f = base / "runs" / "ad-variations" / pack["brand"] / label / "sprint.json"
    if not f.is_file():
        return None
    sp = json.loads(f.read_text())
    o = pack["offer"]
    for k, v in (("offer", o["lead_line"]), ("moment", pack["moment"]), ("until", pack["window"]["end"])):
        if not sp.get(k):
            sp[k] = v
    if not sp.get("never"):
        sp["never"] = [d["line"] for d in o["dropped"] if d["why"].startswith("retired")]
    f.write_text(json.dumps(sp, indent=1, ensure_ascii=False))
    return str(f.relative_to(base))


# -------------------------------------------------------------------------------------------------- writing --
def md(pack):
    o, w = pack["offer"], pack["window"]
    L = ["# Promo pack: %s, %s" % (pack["moment"], pack["brand"]), "",
         "Window %s to %s. Built %s." % (w["start"], w["end"], pack["built"]), "",
         "## The offer words (from the offer bank)", "", "Lead line: **%s**" % o["lead_line"], ""]
    if o.get("order_by"):
        L += ["Order by: %s" % o["order_by"], ""]
    L += ["| Line | Where | Section |", "|---|---|---|"]
    L += ["| %s | %s | %s |" % (x["line"], ", ".join(x["surfaces"]), x["section"]) for x in o["words"]]
    L += ["", "Promo calendar row: %s (approved: %s)" % (o["row"]["promo"], o["row"]["approved"] or "-"), ""]
    if o["dropped"]:
        L += ["Not in this pack:", ""] + ["- %s (%s)" % (d["line"], d["why"]) for d in o["dropped"]] + [""]
    s = pack["stock"]
    L += ["## Stock", ""]
    if not s["read"]:
        L += ["Not read: %s" % s["why"], ""]
    else:
        L += ["| Item | Left | Per day | Runs out | Reorder by | Status |", "|---|---|---|---|---|---|"]
        L += ["| %s | %s | %s | %s | %s | %s |" % (r.get("name", "").strip(), r.get("available"), r.get("per_day"),
                                                r.get("runs_out"), r.get("reorder_by"), r.get("status"))
              for r in s["rows"]]
        L += [""] + ["Blocker: %s: %s" % (r.get("name", "").strip(), "; ".join(r["why"])) for r in s["blockers"]] + [""]
    L += ["## Hand-offs", "", "| Hand-off | Workflow | Role | Briefs | Ready by | Door |", "|---|---|---|---|---|---|"]
    for h in pack["handoffs"]:
        door = " ".join(h["door"]["argv"][:3]) if h["door"] else "gap"
        L.append("| %s | %s | %s | %s | %s | %s |" % (h["id"], h["workflow"], h["role"], h.get("briefs", "-"),
                                                     h.get("ready_by") or "-", door))
    for h in pack["handoffs"]:
        if h["id"] in ("email", "sms") and h.get("sends"):
            L += ["", "### %s sends" % h["id"], "", "| Send | Date | Offer | Ready by | Check |", "|---|---|---|---|---|"]
            L[-2:] = ["| Send | Date | Offer | Ready by | Check | Written |", "|---|---|---|---|---|---|"]
            L += ["| %s | %s | %s | %s | %s | %s |" % (r["id"], r["date"], r["offer"], r["ready_by"],
                                                     (r.get("check") or {}).get("state", "-"),
                                                     "; ".join(r["written"].get("flags") or []) or r["written"]["state"])
                  for r in h["sends"]]
            if h.get("after_window"):
                L.append("\nAfter the window, not in this pack: %s" % ", ".join(h["after_window"]))
            if h.get("not_in_bank"):
                L.append("\nOffers on the calendar the bank does not have: %s" % ", ".join(h["not_in_bank"]))
        if h["id"] in ("video", "static") and h.get("winners"):
            L += ["", "### %s winners" % h["id"], "", "| Winner | Spend | Purchases | CPA |", "|---|---|---|---|"]
            L += ["| %s | %s | %s | %s |" % (x["name"], x["spend"], x["purchases"], x["cpa"]) for x in h["winners"]]
    L += ["", "## Gaps", ""] + ["- %s (%s): %s" % (g["handoff"], g["workflow"], g["gap"]) for g in pack["gaps"]]
    L += ["", "## The gate", "", pack["gate"]["what"], ""]
    return "\n".join(L)


def write(out, pack):
    out.mkdir(parents=True, exist_ok=True)
    (out / "pack.json").write_text(json.dumps(pack, indent=1, ensure_ascii=False))
    (out / "PACK.md").write_text(md(pack))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = ap.add_subparsers(dest="do", required=True)
    b = s.add_parser("build")
    b.add_argument("--brand", required=True)
    b.add_argument("--month", required=True)
    b.add_argument("--moment")
    b.add_argument("--stock")
    b.add_argument("--videos", type=int, default=5)
    b.add_argument("--statics", type=int, default=5)
    t = s.add_parser("tick")
    t.add_argument("--brand", action="append")
    t.add_argument("--lead-days", type=int, default=14)
    t.add_argument("--month", help="the month just planned on the calendar: every promotion touching it")
    t.add_argument("--stock")
    for k in ("hand", "status"):
        q = s.add_parser(k)
        q.add_argument("--brand", required=True)
        q.add_argument("--moment", required=True)
        if k == "hand":
            q.add_argument("--only")
            q.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.do == "build":
        pack, out = build(a.brand, a.month, a.moment, a.stock, a.videos, a.statics)
        print("pack: %s" % (out / "PACK.md").relative_to(root()))
        print("hand-offs: %d · gaps: %d · stock blockers: %d"
              % (len(pack["handoffs"]), len(pack["gaps"]), len(pack["stock"]["blockers"])))
    elif a.do == "tick":
        for r in tick(a.brand, a.lead_days, a.stock, month=a.month):
            print("%-10s %-14s %s" % (r["brand"], r.get("moment", r.get("window")), r["state"]))
    elif a.do == "hand":
        for r in hand(a.brand, a.moment, a.only.split(",") if a.only else None, a.dry_run):
            print("%-7s %s" % (r["id"], r["state"]))
    else:
        pack = load(pack_dir(a.brand, a.moment))
        out = pack_dir(a.brand, a.moment)
        st = loaded(pack, out)
        for r in st["handoffs"]:
            print("%-7s %s" % (r["id"], r["state"]))
        print("loaded" if st["loaded"] else "loading: %s" % ", ".join(st["held"]))


if __name__ == "__main__":
    main()
