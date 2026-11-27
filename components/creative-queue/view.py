"""view.py — the content-queue page's read door, QB-6 (content queue page), QB-7 (content queue Monday). It WRITES
NOTHING.

  view.py [--index <repo>/runs/queue/index.json] [--root <repo>/runs/queue-shadow]
          [--emails <repo>/runs/email-production] [--learnings <Shared Assets>/meta/learnings.jsonl] [--now <UTC …Z>]

owner's index becomes ONE in-memory observation (source `owner-index`, `as_of` = the index's "built", each entry's
`stage` as `observed_stage`); his own person fields (who, priority, title_set, note, removed) become in-memory legacy
decisions, read exactly as `cq.py import-legacy` reads them, so any real decision beats them. The shadow root's
decisions are read with `qcore.load`, the way `cq.py rebuild` reads them, and `qcore.reduce` does the rest. Nothing
is written: no observation file, no index.

Emails come from the email line, never from owner's index (QB-7 (content queue Monday)): one read-only row per
<emails>/<brand>/<label>/klaviyo/card.json, its status by the line's own rule (email-production adapter/sync.py:
scheduled, else draft when the card has a Klaviyo draft, else ready; `held` needs sync.py's checks and is not
worked out here), whose turn as the emails page says it, the send date and editor's deadline (<emails>/<brand>/
deadlines.json, else 5 working days before the send, the emails page's editor_WORKDAYS).

An email row carries `moment` (2026-11-03): its card's `theme`, the marketing calendar's moment key (black-friday),
or null; the board folds a campaign's pieces together by it.

Prints {"owner_built", "owner_age_h", "shadow_root", "people", "stages", "rows", "loose", "calendar", "towrite", "ledger", "from_register", "trail", "register_runs"}. Rows: every piece in owner's index
that is not an email (video ads read only, `"read_only": "video"`), every shadow `add`, and every email card
(`"read_only": "email"`), each with its decision fields and who decided them. Ids starting `zz-` (test pieces) are
left out; so is Christine from `people`. A title that is empty or looks like an id is rebuilt from the id's parts. A
link whose host is 127.0.0.1 or localhost, or that has no host at all (a path on owner's own Outlier), carries
"local": true: it opens only on owner's Mac. Exit 0 ok, 2 refused (the live queue as --root while it is off), 1 any
other error.

`loose` (2026-11-03): the who / priority / due set on an id that is in neither owner's index nor a shadow `add`, keyed
by id. A hand-off his list has not caught up with is dated this way (email_lead, 2026-11-03: the Black Friday statics,
due Friday, while his list was last pushed Oct 30); the page gives a static its own `loose` date by its exact key.
It is never a row: a mistyped id shows nowhere.
A `remove` or `restore` on such an id is loose too (2026-11-06, email_lead: "Yes, fix it", when owner dropped the brand_b
face scrub statics and sent seven FLEX back for a $49 redo): `"removed": true` takes the hand-off off its maker's list
and the board; `"back_on": "<made>"` is a `restore`, and the page counts the hand-off unfinished until a Done made
after that moment (work already in returned/ no longer finishes it).

`calendar` (2026-11-04, the board's To make column): the promo calendar's own observation in the shadow root
(`observations/promo-calendar.json`, written by components/promo-calendar machine/queue_source.py), handed over as
it is, read only: {"as_of", "entries": [{id, brand, type, role, lane, moment, due, title, observed_stage, priority}]},
sorted by id; null when the file is not there. Its pieces are never rows and no decision is applied to them; the
board shows them before a brief exists (email_lead, 2026-11-04: "Sí, constrúyela").

`sent_back` on a row (2026-11-05, the board's side panel): when owner disapproved the piece on Approve to Meta, his
latest disapproval for that brief key from `Shared Assets/meta/learnings.jsonl` (meta-upload learnings.py writes one
line per Disapprove), read only: {"by", "at", "note", "reasons"}. Read through the Drive mount (components/brandpath
drive_index.mount); with no mount, or `--learnings ""`, rows carry none and the board says only that it was sent
back. Only rows whose flag is "sent-back" get one.

`towrite` (2026-11-05, the board's Calendar view): every email the marketing calendar plans from today on that the
email line has not written yet, read only: [{brand, slot, month, send, type, segment, approved}], by send date. A
month counts when `runs/marketing-calendar/<brand>/<YYYY-MM>/slots.json` is in the checkout; `channel: sms` slots are
left out (texts are not designed). A slot is written when a run under `runs/email-production/<brand>/` with a
`deliverable/email.json`, and no `off-page.json`, records it, by the run's own record (its card's
`calendar_handoff.expected.slot_id`, else its run.json's `calendar_handoff.slot_id`; email-production sms.py
`recorded_slot`, 2026-11-05: a folder's name is not its slot), else by its folder name `<brand>-<slot>[--<avatar>]`.
`approved` is the month's review.json status for that slot, null when the month has no review yet; a slot whose
status is `cut` is no email to write and is left out (2026-11-24). email_lead's word,
2026-11-05: "que salga yo con cuántos correos tengo que mandar a diseñar".
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

SOURCE = "owner-index"
VIDEO = "video-ad"
EMAIL = "email"
FIELDS = ("who", "priority", "due", "note", "requested_stage")      # the decisions a row carries
LOCAL_HOSTS = ("127.0.0.1", "localhost")
LEFT = ("christine",)                       # people who have left: never in `people` (email_lead's item 11)
TEST_ID = "zz-"                             # test pieces, hidden everywhere
TEST_BRAND = "zz"                             # a test brand (zzbrand) is hidden the same way (2026-11-06: it showed in the List's brand filter)
EMAILS_PAGE = "emails.html#%s"   # the emails page sits beside this page on the same page server (old :8765 server is gone, 2026-11-10)
editor_WORKDAYS = 5                            # emails.html editor_WORKDAYS: editor finishes 5 working days before the send
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
    """owner's entries as one observation, plus his person fields as legacy decisions (cq.py import-legacy's
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
        "in_owner": SOURCE in (e.get("observed_in") or []),
        "links": [y for y in (_link(x) for x in e.get("links") or []) if y],
        "removed": bool(e.get("removed")),
        "decided_by": {k: decided[k] for k in FIELDS + ("title_set", "removed") if k in decided},
    }
    if e.get("thumb"):
        r["thumb"] = e["thumb"]
    for k in FIELDS:
        r[k] = e.get(k)
    if not r["in_owner"] and "title" in decided:
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


_HOLDS = []


def email_holds(card):
    """(designer, approver): what holds an email, by the emails page's own rule (email-production design/check.py
    holds(), the one sync.py uses), plus a card marked `state: held` (email-production CLAUDE.md: hold an email with
    `state` and `manual_repair`). Read only. A rule that will not load holds nothing and says so once on stderr."""
    if not _HOLDS:
        f = HERE.parent / "email-production" / "design" / "check.py"   # components/email-production
        keep = list(sys.path)
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("email_design_check", str(f))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _HOLDS.append(mod.holds)
        except Exception as e:                        # the page stays up; held emails then show as ready, as before
            sys.stderr.write("view.py: email holds not read (%s): %s\n" % (f, e))
            _HOLDS.append(lambda c: ([], []))
        finally:
            sys.path[:] = keep                        # check.py puts its own folder first; give the path back
    designer, approver = _HOLDS[0](card)
    if str(card.get("state") or "").lower() == "held":
        approver = list(approver) + [str(card.get("manual_repair") or "held for a rebuild")]
    return list(designer), list(approver)


def email_rows(emails, today):
    """One read-only row per <emails>/<brand>/<label>/klaviyo/card.json. Reads only."""
    cards = []
    for f in sorted(Path(emails).glob("*/*/klaviyo/card.json")):
        if (f.parent.parent / "off-page.json").is_file():
            continue                                       # the emails page's rule (sync.py _row): kept for the record, off every page
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
        held_editor, held_email_lead = email_holds(c) if not (c.get("scheduled") or c.get("klaviyo")) else ([], [])
        status = "scheduled" if c.get("scheduled") else "draft" if c.get("klaviyo") else "held" if held_editor or held_email_lead else "ready"   # sync.py's rule
        stage = None
        if status == "scheduled" and d is not None and d < today:
            turn, stage = "Sent %s (date passed; no sent field on the card)" % send, "live"
        elif status == "scheduled":
            turn = "Scheduled · %s" % (send or "no send date")
        elif status == "draft":
            turn = "email_lead: schedule in Klaviyo"
        elif c.get("editor_done"):
            turn = "email_lead: words, then Go"
        else:
            turn = "editor: pictures"
        set_by = deadlines[brand].get(label)
        if isinstance(set_by, str) and set_by.strip():
            editor_due, editor_from = set_by.strip(), "deadlines.json"
        elif d is not None:
            editor_due, editor_from = _workdays_before(d, editor_WORKDAYS).isoformat(), "%d working days before the send" % editor_WORKDAYS
        else:
            editor_due, editor_from = None, None
        s0 = (c.get("subjects") or [{}])[0]
        subject = s0.get("subject") if isinstance(s0, dict) else None
        r = {
            "id": eid, "type": EMAIL, "brand": brand, "email_run": label, "read_only": "email",
            "title": subject.strip() if isinstance(subject, str) and subject.strip() else label,
            "stage": stage, "flag": None, "since": None, "gone": None, "in_owner": False, "links": [],
            "removed": False, "decided_by": {},
            "status": status, "turn": turn, "send_date": send, "send_date_ok": d is not None,
            "editor_due": editor_due, "editor_due_from": editor_from,
            "held": held_editor, "held_email_lead": held_email_lead,       # a picture problem holds editor; words or product hold email_lead
            "moment": c.get("theme") if isinstance(c.get("theme"), str) and c.get("theme").strip() else None,
            "email_link": {"label": "open in the emails page", "url": EMAILS_PAGE % quote(eid, safe="_-.")},
            # when each step happened, read from the card (email_lead, 2026-11-11: "que haya un registro de qué día se terminaron
            # las cosas"): editor's Done, the Go, the schedule
            "history": _history(c),
            # the day email_lead wrote it and it reached editor's page: the run's generated_at, the line's local time (email_lead,
            # 2026-11-19: "que se vean en el board cuando le lleguen a editor y en el calendar como hechos")
            "written_at": _written_at(Path(emails) / brand / label),
        }
        if r["written_at"]:                                # first in its story on the Board
            r["history"] = sorted(r["history"] + [{"step": "Written; on editor's page", "at": r["written_at"], "by": "email_lead"}], key=lambda h: h["at"])
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


CALENDAR = "promo-calendar"                              # the calendar's source name in the shadow root
CAL_FIELDS = ("brand", "type", "role", "lane", "moment", "due", "title", "observed_stage", "priority")


def calendar(observations):
    """The promo calendar's pieces as the board reads them, or None when it has written nothing."""
    obs = observations.get(CALENDAR)
    if not isinstance(obs, dict):
        return None
    out = []
    for k in sorted(obs.get("entries") or {}):
        e = obs["entries"][k]
        if isinstance(e, dict) and not k.startswith(TEST_ID):
            out.append(dict({f: e.get(f) for f in CAL_FIELDS}, id=k))
    return {"as_of": obs.get("as_of"), "entries": out}


def learnings(path):
    """owner's disapprovals by brief key, the latest per key: {key: {by, at, note, reasons}}; {} when unreadable."""
    out = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, TypeError, ValueError):
        return out
    for ln in lines:
        try:
            x = json.loads(ln)
        except ValueError:
            continue
        k = x.get("brief_key") if isinstance(x, dict) else None
        if not isinstance(k, str) or (k in out and str(out[k]["at"]) > str(x.get("at") or "")):
            continue
        out[k] = {"by": x.get("by"), "at": x.get("at"), "note": x.get("note"),
                  "reasons": [r.get("label") for r in x.get("reasons") or [] if isinstance(r, dict) and r.get("label")]}
    return out


def _learnings_path():
    """Shared Assets/meta/learnings.jsonl through the Drive mount, or None (a worker, or no Drive on this Mac)."""
    bp = str(HERE.parent / "brandpath")
    if bp not in sys.path:
        sys.path.append(bp)
    try:
        import drive_index  # components/brandpath: every Drive account signed in on this Mac
        m = drive_index.mount()
    except Exception:  # noqa: BLE001  a missing mount is never an error here
        return None
    return m / "meta" / "learnings.jsonl" if m else None


def _recorded_slot(d):
    """The calendar slot a run was written for, from its own record, or None (as email-production sms.py reads it)."""
    for f, path in (("klaviyo/card.json", ("calendar_handoff", "expected", "slot_id")),
                    ("run.json", ("calendar_handoff", "slot_id"))):
        v = _read(d / f)
        for k in path:
            v = v.get(k) if isinstance(v, dict) else None
        if isinstance(v, str) and v:
            return v
    return None


def towrite(calendars, emails, today):
    """The calendar's email slots from `today` on that no written run stands for, by send date. Reads only."""
    out = []
    for month in sorted(Path(calendars).glob("*/[0-9][0-9][0-9][0-9]-[0-9][0-9]/slots.json")):
        brand, ym = month.parent.parent.name, month.parent.name
        slots = _read(month)
        if not isinstance(slots, list):
            continue
        written = set()
        for d in Path(emails).glob("%s/%s-*" % (brand, brand)) if emails else []:
            if not (d / "deliverable" / "email.json").is_file() or (d / "off-page.json").exists():
                continue
            sid = _recorded_slot(d)
            written.add(("id", sid) if sid else ("name", d.name.split("--")[0]))
        review = (_read(month.parent / "review.json") or {}).get("slots") or {}
        # owner approves a month by reviewing it on the calendar's review page: his edits are saved "by: owner" and the
        # status stays "pending" (Nov 7: November's unwritten sends and December). A month he reviewed counts as approved
        # (email_lead, 2026-11-11: "revisa cómo fue que owner aprobó ... Y con eso fue que quedó").
        owner_reviewed = any(isinstance(v, dict) and str(v.get("by", "")).lower() == "owner" for v in review.values())
        for x in slots:
            if not isinstance(x, dict) or x.get("channel", "email") != "email":
                continue
            sid, send = x.get("id"), _iso(x.get("date"))
            if not sid or not send or send < today:
                continue
            if ("id", sid) in written or ("name", "%s-%s" % (brand, sid)) in written:
                continue
            st = (review.get(sid) or {}).get("status") if review else None
            if st == "cut":     # cut on the calendar's review: no email to write (email_lead, 2026-11-24, December to ~2 a week)
                continue
            out.append({"brand": brand, "slot": sid, "month": ym, "send": send.isoformat(), "type": x.get("type"),
                        "segment": x.get("segment"), "approved": (st == "approved" or owner_reviewed) if review else None})
    return sorted(out, key=lambda r: (r["send"], r["brand"], r["slot"]))


def _loose(e):
    """One loose id's facts for the page: who / priority / due when set (with due_by, who set the due), removed, or
    back_on (a restore's moment)."""
    o = {f: e[f] for f in ("who", "priority", "due", "note", "requested_stage") if e.get(f) not in (None, "")}   # note: a recorded send; requested_stage: "working on it" (2026-11-11)
    if "who" in o:                                       # when it was given to that person: creator's two a day start from it
        o["who_at"] = ((e.get("decided_by") or {}).get("who") or {}).get("made")   # (email_lead, 2026-11-19)
    if "due" in o:                                       # who set it: an email moved by owner, designer or email_lead stays on that
        o["due_by"] = ((e.get("decided_by") or {}).get("due") or {}).get("by")   # day on editor's load (2026-11-06)
    if e.get("removed"):
        o["removed"] = True
    elif "removed" in (e.get("decided_by") or {}):
        o["back_on"] = e["decided_by"]["removed"].get("made")
    return o


def _written_at(run_dir):
    """When the email line wrote this run (run.json generated_at, local time, kept through rebuilds), or None."""
    got = _read(Path(run_dir) / "run.json")
    v = got.get("generated_at") if isinstance(got, dict) else None
    return v if isinstance(v, str) and len(v) >= 10 and _iso(v[:10]) else None


def _history(card):
    """[{step, at, by}] from an email card: editor's Done (editor_done), the approval, the schedule; oldest first."""
    out = []
    for key, step in (("editor_done", "editor finished the pictures"), ("approval", "Approved"), ("scheduled", "Scheduled in Klaviyo")):
        v = card.get(key)
        if isinstance(v, dict) and isinstance(v.get("at"), str) and v["at"]:
            by = v.get("by") if isinstance(v.get("by"), str) else ""
            out.append({"step": step, "at": v["at"], "by": "editor" if by == "graphic-designer" else by})
    return sorted(out, key=lambda h: h["at"])


def ledger_of(path):
    """owner's brief ledger (runs/queue/brief-ledger.json, components/briefs/ledger.py), read only: {"built", "status":
    {brief key: stage name}} for video briefs. The board uses it so a hand-off he marks Live, or one he never listed, is not
    shown as the video editor's work (email_lead, 2026-11-11). Missing or unreadable: {}."""
    try:
        doc = json.loads(Path(path).read_text())
        return {"built": doc.get("built"), "status": {r["key"]: r.get("status") for r in doc.get("briefs") or []
                                                    if isinstance(r, dict) and r.get("key") and r.get("type") == "video"}}
    except (OSError, ValueError, AttributeError):
        return {}


REG_TYPE = {"video-ai": VIDEO, "image-ai": "image-ad", "sequence-ai": "image-ad"}   # concepts and emails stay out
REG_STAGE = {("draft", "for-review"): "brief-needs-you", ("approved", "in-production"): "making",
             ("approved", "approved"): "making", ("approved", "shipped"): "live"}


def register_entries(register, index):
    """owner's brief register (components/image-teardown/briefs.json, read only) fills in what his list has not caught
    up with (email_lead, 2026-11-17: "a mí me llega en todo lo que está trabajando owner?"; his list was last saved Oct 30,
    the register on Nov 16). Only a brief OPENED on or after the day his list was built, not deprecated, whose
    4-digit number his list doesn't carry, of a kind the board draws (video, image, sequence; concepts and emails
    left out). Draft for review: "brief-needs-you" (his to approve); approved: "making"; shipped: "live". Each comes
    in as one of his entries, so a decision on it (who, due, remove) works the same."""
    built = str(index.get("built") or "")[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", built):
        return []
    have = {m.group(1) for e in index.get("entries") or [] if isinstance(e, dict)
            for m in [re.search(r"brief-(\d{4})", str(e.get("id")))] if m}
    out = []
    for e in ((register or {}).get("briefs") or {}).values():
        if not isinstance(e, dict) or not isinstance(e.get("key"), str):
            continue
        n, opened = str(e.get("brief") or "")[-4:], str(e.get("opened") or "")
        stage, typ = REG_STAGE.get((e.get("status"), e.get("state"))), REG_TYPE.get(e.get("type"))
        if not (re.match(r"^\d{4}-\d{2}-\d{2}$", opened) and opened >= built and n.isdigit() and n not in have and stage and typ):
            continue
        out.append({"id": e["key"], "brand": e.get("brand"), "type": typ, "title": e.get("title") or "",
                    "stage": stage, "since": opened + "T00:00:00Z", "links": e.get("links") or []})
    return sorted(out, key=lambda x: x["id"])


def register_runs(register):
    """{run: {"brief", "key", "opened"}} for every brief in owner's register that names the run it was written in
    (email_lead, 2026-11-24: the six Yai writing jobs stayed open on the queue after owner wrote them as briefs 0377-0382 on
    Nov 20; "Sí, automático"). The page closes a writing job once a brief was written from it. Deprecated ones left out."""
    out = {}
    for e in ((register or {}).get("briefs") or {}).values():
        if not isinstance(e, dict) or e.get("status") == "deprecated":
            continue
        run, n, opened = e.get("run"), str(e.get("brief") or "")[-4:], str(e.get("opened") or "")
        if isinstance(run, str) and run.strip() and n.isdigit() and re.match(r"^\d{4}-\d{2}-\d{2}$", opened):
            out[run.strip()] = {"brief": n, "key": e.get("key"), "opened": opened}
    return out


def _pm_card(repo, links):
    """The task's START card, read from the clone, as sections: [{"title", "lines"}] (email_lead, 2026-11-19: editor should
    know what a task is about from the queue alone, as with emails and statics). The card is the instructions; the
    task body only points at it. None when the task has no card in this clone."""
    ref = next((l.get("ref") for l in links or [] if isinstance(l, dict) and l.get("type") == "card"), None)
    try:
        f = (Path(repo) / ref).resolve()
        f.relative_to(Path(repo).resolve())
        text = f.read_text(encoding="utf-8")
    except (TypeError, ValueError, OSError):
        return None
    out, cur = [], {"title": "", "lines": []}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            if cur["lines"]:
                out.append(cur)
            cur = {"title": line[3:].strip(), "lines": []}
        elif line:
            cur["lines"].append(re.sub(r"^(?:[-*]|\d+\.)\s+", "", line).replace("`", ""))
    if cur["lines"]:
        out.append(cur)
    return out or None


def _pm_todo(body):
    """What a PM task asks, in plain words: its body without the markdown headings, first 400 characters."""
    lines = [l.strip() for l in str(body or "").splitlines() if l.strip() and not l.strip().startswith("#")]
    return " ".join(lines)[:400] or None


def pm_tasks(repo):
    """Open PM tasks for editor, read only (email_lead, 2026-11-19: owner now hands some design work out as PM tasks with a
    START card, and editor sees only this page). Every task assigned to editor or tagged role:graphic-designer that is not
    done or dropped, folded by the PM's own mytasks.fold through mytasks.load_tasks; the records are read in one pass
    from the clone (mytasks.make_local_fetch rereads every record file per task, ~50 s here). A row each: type task,
    who editor, its due, priority and START card link. [] when the PM can't be read."""
    from urllib.parse import parse_qs
    repo = Path(repo)
    try:
        sys.path.insert(0, str(repo / "new-workflow-design" / "builds" / "pm-tool"))
        import mytasks
        man = json.loads((repo / "platform" / "data" / "kinds" / "tasks.json").read_text(encoding="utf-8"))
        items = [{"id": it["id"], "content": it} for it in man.get("items") or [] if isinstance(it, dict) and it.get("id")]
        by = {}
        for f in sorted((repo / "platform" / "data" / "records" / "tasks").glob("*.json")):
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(r, dict):
                by.setdefault(str(r.get("item")), []).append(r)

        def fetch(path):
            if path.startswith("/api/items"):
                return {"items": items}
            return {"records": by.get((parse_qs(urlparse(path).query).get("item") or [""])[0], [])}
        tasks = mytasks.load_tasks(fetch)
    except Exception:  # noqa: BLE001  the PM is extra here: never fail the page for it
        return []
    out = []
    for t in tasks.values():
        who = [str(a).lower() for a in t.get("assignees") or []]
        if t.get("status") in ("done", "dropped") or not ("editor" in who or "role:graphic-designer" in (t.get("tags") or [])):
            continue
        card = next((l.get("ref") for l in t.get("links") or [] if isinstance(l, dict) and l.get("type") == "url"), None)
        # waiting_on in the PM holds it here (email_lead, 2026-11-19): no day while held, its reason on the card; cleared in
        # the PM, it is back on its due date by itself
        wait = str(t.get("waiting_on") or "").strip()
        out.append({"id": t["id"], "type": "task", "brand": next((g for g in ("brand_b", "brand_a") if g in t["id"].lower()), None),
                    "title": t.get("title") or t["id"], "read_only": "pm", "stage": None, "flag": None, "since": None,
                    "gone": None, "email_run": None, "in_owner": False, "removed": False, "decided_by": {},
                    "links": [{"label": "START card", "url": card}] if card else [], "who": "editor",
                    "due": None if wait else t.get("due"), "due_when_free": t.get("due") if wait else None,
                    "priority": None,   # the PM's p1/p2 is not the queue's Now/Next/Later: no pill (email_lead, 2026-11-19)
                    "note": ("On hold: " + wait) if wait else "PM task %s (%s)" % (t["id"], t.get("status") or "todo"),
                    "pm": {"id": t["id"], "status": t.get("status") or "todo", "waiting_on": wait or None, "card": card,
                           "created": t.get("created"),
                           "by": t.get("requested_by") or t.get("by"), "todo": _pm_todo(t.get("body")),
                           "last_comment": (str((t.get("comments") or [""])[-1])[:600] or None),
                           "start": _pm_card(repo, t.get("links"))}, "requested_stage":
                    "editing" if t.get("status") in ("in_progress", "doing") else None})
    return sorted(out, key=lambda r: r["id"])


def trail(decisions, extra=()):
    """Each piece's story for its card, read only (email_lead, 2026-11-19: "en tal fecha se creó la tarea, en tal pasó de
    tal persona a tal persona, qué sigue hacer"): {id: [{at, by, what, value}]}, oldest first, from every shadow
    decision (set who/due/note/priority/requested_stage, add, remove, restore) plus the day a register brief opened."""
    out = {}
    for d in decisions or []:
        if not isinstance(d, dict) or not isinstance(d.get("id"), str):
            continue
        what = d.get("field") if d.get("op") == "set" else d.get("op")
        if what not in ("who", "due", "note", "priority", "requested_stage", "add", "remove", "restore"):
            continue
        out.setdefault(d["id"], []).append({"at": d.get("made"), "by": d.get("by"), "what": what,
                                            "value": d.get("value") if what != "add" else (d.get("fields") or {}).get("title")})
    for e in extra or ():
        out.setdefault(e["id"], []).insert(0, {"at": e.get("since"), "by": "owner", "what": "opened", "value": None})
    for k in out:
        out[k].sort(key=lambda x: str(x.get("at") or ""))
    return out


def build(index, root, now, emails=None, sent_back=None, calendars=None, ledger=None, register=None, pm=None):
    """The page's JSON; reads the shadow root and the email cards under `emails` (none when None), writes nothing."""
    extra = register_entries(register, index)
    if extra:
        index = dict(index, entries=list(index.get("entries") or []) + extra)
    obs, legacy = observation(index)
    shadow_obs, decisions = qcore.load(root)              # the shadow's own observations are not owner's queue
    idx = qcore.reduce({SOURCE: obs}, legacy + decisions, now)
    built, at = qcore._utc(obs["as_of"]), qcore._utc(now)
    age = round((at - built).total_seconds() / 3600.0, 1) if built and at else None
    rows = [row(e) for e in idx["entries"] if e.get("type") != EMAIL]      # emails come from the email line only
    known = {e["id"] for e in idx["entries"]}
    loose = sorted({d["id"] for d in decisions if isinstance(d, dict) and d.get("op") in ("set", "remove", "restore")
                    and isinstance(d.get("id"), str) and d["id"] not in known})
    lidx = qcore.reduce({"loose": {"as_of": now, "entries": {i: {} for i in loose}}}, decisions, now)
    for r in rows:
        if r.get("flag") == "sent-back" and (sent_back or {}).get(r["id"]):
            r["sent_back"] = sent_back[r["id"]]
    if emails is not None:
        rows += email_rows(emails, (at or datetime.now(timezone.utc)).date())
    rows += pm or []
    return {
        "owner_built": index.get("built"),
        "owner_age_h": age,
        "shadow_root": _rel(root),
        "people": [p for p in index.get("people") or [] if str(p).strip().lower() not in LEFT],
        "stages": _stages(),
        "rows": [r for r in rows if not r["id"].startswith(TEST_ID) and not str(r.get("brand") or "").startswith(TEST_BRAND)],
        "loose": {e["id"]: o for e in lidx["entries"] if e["id"] in loose for o in [_loose(e)] if o},
        "calendar": calendar(shadow_obs),
        "towrite": towrite(calendars, emails, (at or datetime.now(timezone.utc)).date()) if calendars else [],
        "ledger": ledger or {},
        "from_register": [x["id"] for x in extra],
        "trail": trail(decisions, extra),
        "register_runs": register_runs(register),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(prog="view.py", description="The content-queue page's data; writes nothing.")
    ap.add_argument("--index", help="owner's queue index (default <repo>/runs/queue/index.json)")
    ap.add_argument("--root", help="the decisions folder (default <repo>/runs/queue-shadow)")
    ap.add_argument("--emails", help="the email line's runs (default <repo>/runs/email-production), read only")
    ap.add_argument("--learnings", help="owner's disapprovals (default Shared Assets/meta/learnings.jsonl on the Drive mount; \"\" for none)")
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
        lp = a.learnings if a.learnings is not None else _learnings_path()
        cals = qcore.live_root().parent / "marketing-calendar"
        led = ledger_of(qcore.live_root() / "brief-ledger.json")
        try:
            reg = json.loads((HERE.parent / "image-teardown" / "briefs.json").read_text())
        except (OSError, ValueError):
            reg = None
        print(json.dumps(build(index, root, now, emails, learnings(lp) if lp else {}, cals, led, reg, pm_tasks(HERE.parent.parent) if not a.index else []), ensure_ascii=False, sort_keys=True))   # a run on another index (a fixture) reads no PM
        return 0
    except qcore.Refused as e:
        print(str(e), file=sys.stderr)
        return 2
    except (ValueError, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
