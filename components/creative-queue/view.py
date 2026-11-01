"""view.py — the content-queue page's read door, QB-6 (content queue page), QB-7 (content queue Monday). It WRITES
NOTHING.

  view.py [--index <repo>/runs/queue/index.json] [--root <repo>/runs/queue-shadow]
          [--emails <repo>/runs/email-production] [--now <UTC …Z>]

the owner's index becomes ONE in-memory observation (source `damon-index`, `as_of` = the index's "built", each entry's
`stage` as `observed_stage`); his own person fields (who, priority, title_set, note, removed) become in-memory legacy
decisions, read exactly as `cq.py import-legacy` reads them, so any real decision beats them. The shadow root's
decisions are read with `qcore.load`, the way `cq.py rebuild` reads them, and `qcore.reduce` does the rest. Nothing
is written: no observation file, no index.

Emails come from the email line, never from the owner's index (QB-7 (content queue Monday)): one read-only row per
<emails>/<brand>/<label>/klaviyo/card.json, its status by the line's own rule (email-production adapter/sync.py:
scheduled, else draft when the card has a Klaviyo draft, else ready; `held` needs sync.py's checks and is not
worked out here), whose turn as the emails page says it, the send date and the team's deadline (<emails>/<brand>/
deadlines.json, else 5 working days before the send, the emails page's EVE_WORKDAYS).

Prints {"damon_built", "damon_age_h", "shadow_root", "people", "stages", "rows"}. Rows: every piece in the owner's index
that is not an email (video ads read only, `"read_only": "video"`), every shadow `add`, and every email card
(`"read_only": "email"`), each with its decision fields and who decided them. Ids starting `zz-` (test pieces) are
left out; so is Christine from `people`. A title that is empty or looks like an id is rebuilt from the id's parts. A
link whose host is 127.0.0.1 or localhost, or that has no host at all (a path on the owner's own Outlier), carries
"local": true: it opens only on the owner's Mac. Exit 0 ok, 2 refused (the live queue as --root while it is off), 1 any
other error.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
import cq  # noqa: E402  the same component: its legacy reading, reused
import qcore  # noqa: E402

SOURCE = "damon-index"
VIDEO = "video-ad"
EMAIL = "email"
FIELDS = ("who", "priority", "due", "note", "requested_stage")      # the decisions a row carries
LOCAL_HOSTS = ("127.0.0.1", "localhost")
LEFT = ("christine",)                       # people who have left: never in `people` (the team's item 11)
TEST_ID = "zz-"                             # test pieces, hidden everywhere
EMAILS_PAGE = "http://127.0.0.1:8765/#%s"   # the emails page runs on its own server (email-review skill, step 4)
EVE_WORKDAYS = 5                            # emails.html EVE_WORKDAYS: the team finishes 5 working days before the send
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
BATCH = re.compile(r"^batch-(\d{4})-(\d{2})-(\d{2})(?:-.*)?$")
SHORT_DATE = re.compile(r"^\s*(\d{1,2})\s+([A-Za-z]{3})[A-Za-z]*\.?\s*$")     # an older card's "12 Oct"


def _z(stamp):
    """The index's "built" (ISO with an offset, or …Z) as UTC …Z text, or None."""
    if not isinstance(stamp, str) or not stamp:
        return None
    try:
        t = datetime.fromisoformat(stamp[:-1] + "+00:00" if stamp.endswith("Z") else stamp)
    except ValueError:
        return None
    if t.tzinfo is None:
        return None
    return t.astimezone(timezone.utc).strftime(qcore.ZFMT)


def observation(index):
    """the owner's entries as one observation, plus his person fields as legacy decisions (cq.py import-legacy's
    reading, in memory)."""
    entries, lines = {}, []
    for e in index.get("entries") or []:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str):
            continue
        eid = e["id"]
        o = {k: v for k, v in e.items() if k not in cq.LEGACY_HUMAN and k not in ("id", "stage")}
        if e.get("stage") not in (None, ""):
            o["observed_stage"] = e["stage"]
        entries[eid] = o
        for k in ("who", "priority", "title_set", "note"):
            if e.get(k) not in (None, ""):
                lines.append(cq._legacy(eid, "set", k, e[k], cq._when(e, k)))
        if e.get("removed"):
            lines.append(cq._legacy(eid, "remove", None, None, e.get("removed_at") or cq._when(e, "removed")))
    obs = {"schema": 1, "source": SOURCE, "as_of": _z(index.get("built")), "entries": entries}
    return obs, lines


def _link(x):
    if not isinstance(x, dict) or not isinstance(x.get("url"), str):
        return None
    host = (urlparse(x["url"]).hostname or "").lower()
    out = {"label": x.get("label") or x["url"], "url": x["url"]}
    if host in LOCAL_HOSTS or not host:
        out["local"] = True
    return out


def _human(slug):
    """brilliance-face-scrub -> Brilliance face scrub."""
    t = slug.replace("-", " ").strip()
    return t[:1].upper() + t[1:]


def _iso(s):
    """A YYYY-MM-DD text as a date, or None."""
    if not isinstance(s, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", s.strip()):
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def readable(eid):
    """A title from the id's parts: <brand>_<product>_<format>_batch-<YYYY-MM-DD>-<x> -> "<Product> · <format> ·
    batch <D Mon>" (format "none" left out); <brand>[_<product>]_idea_<run> -> "<Product> idea", the product being
    the part before _idea_ after the brand, else the run's --<product> tail; anything else -> the id itself."""
    parts = eid.split("_")
    if len(parts) >= 4:
        m = BATCH.match(parts[-1])
        d = _iso("-".join(m.groups())) if m else None
        if d and parts[-3]:
            bits = [_human(parts[-3])]
            if parts[-2] and parts[-2] != "none":
                bits.append(parts[-2].replace("-", " "))
            bits.append("batch %d %s" % (d.day, MONTHS[d.month - 1]))
            return " · ".join(bits)
    if "_idea_" in eid:
        head, _, run = eid.partition("_idea_")
        hp = head.split("_")
        product = hp[-1] if len(hp) >= 2 else (run.rsplit("--", 1)[1] if "--" in run else "")
        product = product.strip("-")
        if product:
            return "%s idea" % _human(product)
    return eid


def title_of(eid, title):
    """The title as given, unless it is empty or looks like an id (no space and contains "_")."""
    t = title.strip() if isinstance(title, str) else ""
    if t and not (" " not in t and "_" in t):
        return t
    return readable(eid)


def row(e):
    decided = e.get("decided_by") or {}
    r = {
        "id": e["id"],
        "type": e.get("type"),
        "brand": e.get("brand"),
        "title": title_of(e["id"], e.get("title_set") or e.get("title")),
        "read_only": "video" if e.get("type") == VIDEO else None,
        "stage": e.get("observed_stage"),
        "flag": e.get("flag"),
        "since": e.get("since"),
        "gone": e.get("gone"),
        "email_run": e.get("email_run"),
        "in_damon": SOURCE in (e.get("observed_in") or []),
        "links": [y for y in (_link(x) for x in e.get("links") or []) if y],
        "removed": bool(e.get("removed")),
        "decided_by": {k: decided[k] for k in FIELDS + ("title_set", "removed") if k in decided},
    }
    if e.get("thumb"):
        r["thumb"] = e["thumb"]
    for k in FIELDS:
        r[k] = e.get(k)
    if not r["in_damon"] and "title" in decided:
        r["added_by"] = decided["title"]
    return r


def _workdays_before(d, n):
    """n working days (Mon-Fri) before d, as emails.html dueOf counts them."""
    k = 0
    while k < n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            k += 1
    return d


def _send_date(raw, year):
    """The card's `date` as a date: YYYY-MM-DD as it is, an older "12 Oct" with the year given; else None."""
    d = _iso(raw)
    if d or not isinstance(raw, str) or not year:
        return d
    m = SHORT_DATE.match(raw)
    if not m or m.group(2).capitalize() not in MONTHS:
        return None
    try:
        return date(year, MONTHS.index(m.group(2).capitalize()) + 1, int(m.group(1)))
    except ValueError:
        return None


def _read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def email_rows(emails, today):
    """One read-only row per <emails>/<brand>/<label>/klaviyo/card.json. Reads only."""
    cards = []
    for f in sorted(Path(emails).glob("*/*/klaviyo/card.json")):
        c = _read(f)
        if isinstance(c, dict):
            cards.append((f.parent.parent.parent.name, f.parent.parent.name, c))
    newest, deadlines = {}, {}
    for brand, _, c in cards:
        d = _iso(c.get("date"))
        if d and (brand not in newest or d > newest[brand]):
            newest[brand] = d
        if brand not in deadlines:
            got = _read(Path(emails) / brand / "deadlines.json")
            deadlines[brand] = got if isinstance(got, dict) else {}
    out = []
    for brand, label, c in cards:
        eid = "%s__%s" % (brand, label)
        y = c.get("year")
        year = y if isinstance(y, int) and not isinstance(y, bool) else (newest[brand].year if brand in newest else None)
        raw = c.get("date")
        d = _send_date(raw, year)
        send = d.isoformat() if d else (raw.strip() if isinstance(raw, str) and raw.strip() else None)
        status = "scheduled" if c.get("scheduled") else "draft" if c.get("klaviyo") else "ready"   # sync.py, less held
        stage = None
        if status == "scheduled" and d is not None and d < today:
            turn, stage = "Sent %s (date passed; no sent field on the card)" % send, "live"
        elif status == "scheduled":
            turn = "Scheduled · %s" % (send or "no send date")
        elif status == "draft":
            turn = "the team: schedule in Klaviyo"
        elif c.get("eve_done"):
            turn = "the team: words, then Go"
        else:
            turn = "the team: pictures"
        set_by = deadlines[brand].get(label)
        if isinstance(set_by, str) and set_by.strip():
            eve_due, eve_from = set_by.strip(), "deadlines.json"
        elif d is not None:
            eve_due, eve_from = _workdays_before(d, EVE_WORKDAYS).isoformat(), "%d working days before the send" % EVE_WORKDAYS
        else:
            eve_due, eve_from = None, None
        s0 = (c.get("subjects") or [{}])[0]
        subject = s0.get("subject") if isinstance(s0, dict) else None
        r = {
            "id": eid, "type": EMAIL, "brand": brand, "email_run": label, "read_only": "email",
            "title": subject.strip() if isinstance(subject, str) and subject.strip() else label,
            "stage": stage, "flag": None, "since": None, "gone": None, "in_damon": False, "links": [],
            "removed": False, "decided_by": {},
            "status": status, "turn": turn, "send_date": send, "send_date_ok": d is not None,
            "eve_due": eve_due, "eve_due_from": eve_from,
            "email_link": {"label": "open in the emails page", "url": EMAILS_PAGE % quote(eid, safe="_-.")},
        }
        for k in FIELDS:
            r[k] = None
        out.append(r)
    return out


def _stages():
    try:
        got = json.loads((HERE.parent / "naming" / "stages.json").read_text())["stages"]
    except (OSError, ValueError, KeyError, TypeError):
        return [{"id": s, "name": s} for s in qcore.ORDER]
    return [{"id": s["id"], "name": s.get("name") or s["id"]} for s in got if isinstance(s, dict) and s.get("id")]


def _rel(root):
    """The root as a repo-relative path when it sits in the repo (never a machine path in the page), else as given."""
    try:
        return Path(root).resolve().relative_to(qcore.shadow_root().parent.parent.resolve()).as_posix()
    except (ValueError, OSError, RuntimeError):
        return str(root)


def build(index, root, now, emails=None):
    """The page's JSON; reads the shadow root and the email cards under `emails` (none when None), writes nothing."""
    obs, legacy = observation(index)
    _, decisions = qcore.load(root)                       # the shadow's own observations are not the owner's queue
    idx = qcore.reduce({SOURCE: obs}, legacy + decisions, now)
    built, at = qcore._utc(obs["as_of"]), qcore._utc(now)
    age = round((at - built).total_seconds() / 3600.0, 1) if built and at else None
    rows = [row(e) for e in idx["entries"] if e.get("type") != EMAIL]      # emails come from the email line only
    if emails is not None:
        rows += email_rows(emails, (at or datetime.now(timezone.utc)).date())
    return {
        "damon_built": index.get("built"),
        "damon_age_h": age,
        "shadow_root": _rel(root),
        "people": [p for p in index.get("people") or [] if str(p).strip().lower() not in LEFT],
        "stages": _stages(),
        "rows": [r for r in rows if not r["id"].startswith(TEST_ID)],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(prog="view.py", description="The content-queue page's data; writes nothing.")
    ap.add_argument("--index", help="the owner's queue index (default <repo>/runs/queue/index.json)")
    ap.add_argument("--root", help="the decisions folder (default <repo>/runs/queue-shadow)")
    ap.add_argument("--emails", help="the email line's runs (default <repo>/runs/email-production), read only")
    ap.add_argument("--now", help="UTC like 2026-10-22T02:24:18Z (default: now)")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 1
    try:
        now = qcore._need_utc(a.now, "--now") if a.now else qcore.utc_now()
        root = qcore.check_root(a.root or qcore.shadow_root())
        index_path = Path(a.index) if a.index else qcore.live_root() / "index.json"
        index = json.loads(index_path.read_text())
        if not isinstance(index, dict):
            raise ValueError("%s is not an object" % index_path)
        emails = Path(a.emails) if a.emails else qcore.live_root().parent / "email-production"
        print(json.dumps(build(index, root, now, emails), ensure_ascii=False, sort_keys=True))
        return 0
    except qcore.Refused as e:
        print(str(e), file=sys.stderr)
        return 2
    except (ValueError, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
