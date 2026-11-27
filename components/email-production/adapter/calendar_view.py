"""One month of sends for the emails page's Calendar tab (email_lead, 2026-11-05): every email and SMS text with its send
date, its status and editor's due date, plus each planned slot nothing was written for yet. Reads only; writes nothing.

    sync.py calendar [--month YYYY-MM]      (JSON on stdout; the month defaults to this one)

Where each thing comes from (the data rules, checked against the repo 2026-11-05):
- an email is a run under runs/email-production/<brand>/<label>/; a run with off-page.json beside it is no item
  (the emails page's own rule, sync.py _row)
- send date: klaviyo/card.json `date`; a run with no card: its run.json calendar hand-off date, else
  assignment.send_date
- status: card `status` "scheduled" (or `scheduled`) -> scheduled; card `editor_done` -> done (editor finished, waiting for
  a Go); any other card -> editor (with editor), or unpushed when the card is only in the person's own clone (designed, not
  pushed: editor's page lacks it); a run with no card -> nodesign (written, no design)
- the slot it was written for: the card's (or run.json's) calendar_handoff.expected.slot_id; a run from before a
  re-plan has none, so the slot on the same date whose variant carries the run's own angle, when exactly one does
  (the rule simple_email.the_slot reads a re-planned month by, 2026-11-03)
- not written: a slot in runs/marketing-calendar/<brand>/<YYYY-MM>/slots.json that no on-page run points to, ONE
  item per slot whatever its avatar variants: one version per send per audience (email_lead, decision log 2026-11-04;
  Klaviyo has no avatar tag), so a slot with one written, on-page version is written, and its sibling versions taken
  off the page (off-page.json) are gone, not still to write. The content queue counts editor's load the same way
- a planned send's fields (angle per variant, segments, type, category, product, offer, occasion, the first sentence
  of its why) and its review mark come from slots.json with the reviewer's layer laid on, through marketing-calendar's
  review.py load() and applied() (CONTRACT.md); a mark is written back with `review.py mark`, the page's L60 (slot
  review) button (email_lead, 2026-11-06: "you fix it, owner reviews")
- editor's due date: runs/email-production/<brand>/deadlines.json, else none here (the page works out its default,
  editor_WORKDAYS working days before the send, as it does for every email)
- SMS: a slot with channel "sms"; its text is runs/email-production/<brand>/<brand>-<slot>-sms/sms.json (a text whose
  `state` starts with "superseded" is skipped), matched to the slot by its send date; sms-card.json beside it ->
  carded, or scheduled once it says so
- only on this Mac: the page server reads its own private copy of origin/main, which never holds an unpushed run.
  That copy is a git worktree of the person's clone, so git names the clone; its run folders are read (files only, no
  git in that folder) and a run origin/main lacks is an item marked `local`. Run in the clone itself, the same check
  marks its unpushed runs. No machine path ever leaves this script.
"""
import datetime as dt
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
WHY_MAX = 320


def _review_module():
    """marketing-calendar's review.py, its declared readers load() and applied() (CONTRACT.md): the reviewer's layer
    over a planned month. Loaded under its own name, so no other `review` module on the path is taken for it."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "marketing_calendar_review", str(REPO / "components" / "marketing-calendar" / "machine" / "review.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _short(text):
    """The first sentence of a slot's `why`, at most WHY_MAX characters."""
    t = " ".join(str(text or "").split())
    for end in (". ", " — "):
        if end in t[:WHY_MAX]:
            t = t[:t.index(end, 0, WHY_MAX) + 1].rstrip(" —")
            break
    return t if len(t) <= WHY_MAX else t[:WHY_MAX - 1].rstrip() + "…"


def _verdict(m):
    """A planned send's review mark for the page, or None when nobody has judged it (or the mark was for another
    send: review.applied() then resets it to pending and says so in the note)."""
    r = m.get("_review") or {}
    if not r.get("identity"):
        return None
    return {"status": r.get("status") or "pending", "note": r.get("note") or "", "by": r.get("by"), "at": r.get("at"),
            "for_another_send": r.get("identity") == "mismatch"}
GIT_S = 20


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def _git(root, *args):
    try:
        r = subprocess.run(["git", "-C", str(root)] + list(args), capture_output=True, text=True, timeout=GIT_S,
                           env={"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
                                "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"})
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def clone_of(root):
    """The person's own clone when root is a worktree of it (the page server's private copy), else None."""
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        return None
    clone = Path(common.strip()).parent
    try:
        return None if clone.resolve() == Path(root).resolve() else (clone if (clone / "runs").is_dir() else None)
    except OSError:
        return None


def pushed_files(root):
    """Every runs/email-production path on origin/main, or None when git cannot say (then nothing is marked local)."""
    out = _git(root, "ls-tree", "-r", "--name-only", "origin/main", "runs/email-production")
    return None if out is None else set(out.split())


def _runs(root, clone):
    """{(brand, label): (run folder, from_clone)} — this root's runs, then the clone's runs this root lacks."""
    got = {}
    for base, from_clone in ((root, False), (clone, True)):
        if base is None:
            continue
        for b in sorted(p for p in (base / "runs" / "email-production").glob("*") if p.is_dir()):
            for r in sorted(p for p in b.iterdir() if p.is_dir()):
                got.setdefault((b.name, r.name), (r, from_clone))
    return got


def _handoff(x):
    ch = (x or {}).get("calendar_handoff")
    if not isinstance(ch, dict):
        return {}
    ex = ch.get("expected") if isinstance(ch.get("expected"), dict) else ch
    return ex if isinstance(ex, dict) else {}


def _angles(slot):
    return [v.get("angle") for v in slot.get("variants") or [] if isinstance(v, dict) and v.get("angle")]


def month_items(month, root=REPO, clone="find"):
    root = Path(root)
    clone = clone_of(root) if clone == "find" else clone
    pushed = pushed_files(root)
    slots = {}
    for f in sorted((root / "runs" / "marketing-calendar").glob("*/%s/slots.json" % month)):
        got = _read(f)
        slots[f.parent.parent.name] = [s for s in got if isinstance(s, dict) and s.get("id")] if isinstance(got, list) else []
    deadlines = {}
    items = []

    def local(run, from_clone, key):
        if from_clone:
            return True
        if pushed is None:
            return False
        return (run.relative_to(root) / key).as_posix() not in pushed

    for (brand, label), (run, from_clone) in sorted(_runs(root, clone).items()):
        if (run / "off-page.json").is_file():
            continue
        if (run / "sms.json").is_file():
            s = _read(run / "sms.json") or {}
            if str(s.get("state") or "").startswith("superseded") or not str(s.get("date") or "").startswith(month):
                continue
            card = _read(run / "sms-card.json")
            sched = isinstance(card, dict) and ("scheduled" in (card.get("status"), card.get("state")) or card.get("scheduled"))
            items.append({"kind": "sms", "brand": brand, "label": label, "slot": s.get("slot"), "avatar": None,
                          "send": s.get("date"), "status": "scheduled" if sched else "carded" if card else "written",
                          "text": (card or {}).get("text") or s.get("text"), "beat": s.get("beat"),
                          "local": local(run, from_clone, "sms.json")})
            continue
        if not (run / "run.json").is_file():
            continue
        state = _read(run / "run.json") or {}
        card = _read(run / "klaviyo" / "card.json")
        a = state.get("assignment") if isinstance(state.get("assignment"), dict) else {}
        if isinstance(card, dict):
            ex = _handoff(card) or _handoff(state)
            send = card.get("date")
            st = "scheduled" if card.get("status") == "scheduled" or card.get("scheduled") else \
                "done" if "editor_done" in card else "editor"
            s0 = (card.get("subjects") or [{}])[0]
            subject, preview = (s0.get("subject"), s0.get("preview")) if isinstance(s0, dict) else (None, None)
            key = "klaviyo/card.json"
        else:
            ex = _handoff(state)
            send = (ex.get("fields") or {}).get("date") if isinstance(ex.get("fields"), dict) else None
            send = send or a.get("send_date")
            st, subject, preview, key = "nodesign", None, None, "run.json"
        if not isinstance(send, str) or not send.startswith(month):
            continue
        slot = ex.get("slot_id")
        if not slot and a.get("angle"):
            hits = [s["id"] for s in slots.get(brand, []) if s.get("date") == send and a["angle"] in _angles(s)]
            slot = hits[0] if len(hits) == 1 else None
        if brand not in deadlines:
            got = _read(root / "runs" / "email-production" / brand / "deadlines.json")
            deadlines[brand] = got if isinstance(got, dict) else {}
        due = deadlines[brand].get(label)
        here_only = local(run, from_clone, key)
        if here_only and st == "editor":
            st = "unpushed"           # designed, but editor's page lacks it until it is pushed (email_lead, 2026-11-06)
        items.append({"kind": "email", "id": "%s__%s" % (brand, label), "brand": brand, "label": label, "slot": slot,
                      "avatar": ex.get("avatar") or state.get("avatar"), "send": send, "status": st,
                      "due": due.strip() if isinstance(due, str) and due.strip() else None,
                      "subject": subject, "preview": preview, "angle": a.get("angle"),
                      "local": here_only})

    RV = _review_module() if slots else None
    for brand, L in sorted(slots.items()):
        # the reviewer's layer laid over the plan, as the board and the email line read it (edits win)
        A = {m["id"]: m for m in RV.applied(L, RV.load(root / "runs" / "marketing-calendar" / brand / month))}
        for i in items:
            if i["brand"] == brand and i["kind"] == "email" and i["slot"] in A:
                i["review"] = _verdict(A[i["slot"]])
        made = {i["slot"] for i in items if i["brand"] == brand and i["kind"] == "email" and i["slot"]}
        # a text is matched to its slot by send date, not by number: texts written before a re-plan keep the old slot
        # numbers (brand_b-nov-45-sms is the Nov 20 text, while slot nov-45 is now a Nov 30 email), and a month plans
        # at most one text a day per brand
        texts = {i["send"] for i in items if i["brand"] == brand and i["kind"] == "sms"}
        for s in L:
            if not str(s.get("date") or "").startswith(month):
                continue
            if s.get("channel") == "sms":
                if s["date"] not in texts:
                    items.append({"kind": "sms", "brand": brand, "label": None, "slot": s["id"], "avatar": None,
                                  "send": s["date"], "status": "unwritten", "text": None, "beat": s.get("type"), "local": False})
                continue
            if s["id"] in made:
                continue
            m = A.get(s["id"], s)
            vs = [v for v in m.get("variants") or [] if isinstance(v, dict)]
            one = vs[0] if len(vs) == 1 else {}
            segs = m.get("segments") if isinstance(m.get("segments"), list) else [m.get("segment")]
            items.append({"kind": "email", "id": None, "brand": brand, "label": None, "slot": s["id"],
                          "month": month,           # where its review lives, even after a reviewer moves its date
                          "avatar": one.get("avatar") or (m.get("avatar") if m.get("avatar") != "mixed" else None),
                          "send": m.get("date") or s["date"], "status": "unwritten",
                          "due": None, "subject": None, "preview": None, "angle": one.get("angle") or m.get("angle"),
                          "angles": [{"avatar": v.get("avatar"), "angle": v.get("angle")} for v in vs if v.get("angle")],
                          "segments": [x for x in segs if x], "type": m.get("type"), "category": m.get("category"),
                          "product": m.get("product"), "offer": m.get("offer"), "occasion": m.get("occasion"),
                          "why": _short(m.get("why")), "edited": sorted((m.get("_review") or {}).get("edits") or {}),
                          # L61 (rewrite a planned send): every field a reviewer may rewrite, as it stands now and as
                          # the planner first wrote it (review.applied's _orig), so the page shows both
                          "plan": {f: (one.get("angle") or m.get("angle")) if f == "angle" else m.get(f)
                                   for f in RV.EDITABLE},
                          "orig": m.get("_orig") or {},
                          "review": _verdict(m), "local": False})
    items.sort(key=lambda i: (i["send"] or "", i["brand"], i["kind"], i["label"] or "~", i["slot"] or "", i["avatar"] or ""))
    return {"month": month, "today": dt.date.today().isoformat(), "items": items}
