#!/usr/bin/env python3
"""The Klaviyo uploader: a finished email → a checked DRAFT campaign in
Klaviyo plus its approval card, the campaign id written back. One command.

    python3 klaviyo_upload.py --handoff <klaviyo-uploader hand-off folder>
    python3 klaviyo_upload.py --run runs/email-production/<brand>/<label>
    python3 klaviyo_upload.py --handoff <folder> --dry-run   # checks only; talks to nothing
    python3 klaviyo_upload.py --run <run folder> --card      # the card for a draft already in Klaviyo
    python3 klaviyo_upload.py --handoff <folder> --send      # ALWAYS REFUSED — see THE SEND STEP

DEFAULT = THE DRAFT AND ITS CARD, NOTHING SCHEDULED. In order:
  1 checks the email — the words (email.json), the picked subject + preview
    text, the shared delivery gate (prices, the chain's check step, unfilled
    notes, the money path — the same checks simple_email.py runs), the
    audience (the calendar slot's segments → ids from the brand's audience
    matrix), the from-line and send hour (the brand's simple.json), the hero
    picture, and every link in the finished HTML: each one is a link the
    hand-off names in references/links.json (or, for a bare run, the button
    link), and each one answers.
  2 anything wrong → HELD, nothing goes to Klaviyo, every problem listed.
  3 creates the template + the campaign as a DRAFT (simple_email.create_draft
    — the same calls the email line already makes; nothing duplicated here).
  4 reads the draft back from Klaviyo and writes its approval card,
    email-card.json + email-card.html (Klaviyo's own HTML), beside the status
    file: what Klaviyo holds, the checks, and a fingerprint of the subject,
    preview, HTML, audience and send time. Klaviyo holding anything other than
    what was checked → HELD, the draft stays in Klaviyo with no card. A draft
    whose plan day has passed gets no card (it has no send time).
  5 writes the id back: returned/live-ids.json + returned/<brief>_klaviyo-checks.md
    in the hand-off, then runs ad-handoff's take_back, so the ledger records
    live_klaviyo_<campaign id>. For a bare run: deliverable/pushed.json.
  6 writes klaviyo-status.json — the small record a page shows.

SCHEDULING (EP-3 (email approval card), decision log 2026-10-12): a Klaviyo
email is scheduled — never sent now — only by schedule_card(), reached from
the owner's Approve → Schedule on the email approval page (email_approve.py,
http://localhost:8797), or his own Claude acting on that page. It re-runs
every check, refuses any change since the card was made, a send time that is
not fixed or is under 30 minutes away, a run on the mini or in a worker job,
the team's off-switch (send-switch.json) off or missing, and anyone not on
approvers.json. Send back records the reasons and leaves the draft in Klaviyo.

THE SEND STEP (--send) always refuses: a card file is never a go, and
approvals.json is no longer read (O5c).

--dry-run runs every check that needs no network and prints what it would
create: no Klaviyo call, no link fetch, no Keychain read, no file written.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import simple_email as S          # the engine; puts the shared checks on the path
from paths import HERE, WORKSPACE
import drive_reach as DR

STATUS = "klaviyo-status.json"
TAKE_BACK_PY = HERE.parent / "ad-handoff" / "take_back.py"
# EP-3 (email approval card)
CARD = "email-card.json"
CARD_HTML = "email-card.html"
LOG = "email-schedule-log.jsonl"                 # append-only, one JSON object per line
APPROVERS_F = HERE / "approvers.json"
SWITCH_F = HERE / "send-switch.json"
REASONS_F = HERE / "send-back-reasons.json"
MIN_LEAD = datetime.timedelta(minutes=30)        # the first recipient gets it no sooner than this
LOCAL_SPAN = datetime.timedelta(hours=14)        # a local send reaches UTC+14 first
KLAVIYO_LINK = "https://www.klaviyo.com/campaign/{id}/wizard/1"   # unchecked against live Klaviyo
PAGE_URL = "http://localhost:8797"
NOT_AGAIN = "not already in Klaviyo"             # check()'s own row; a card is FOR the existing draft
# The mini / batch markers, restated with their homes (nothing imported from them):
MINI_MARKER = ".workflow-worker.env"   # components/keys/loader.py:43-44 MANAGED, existence only, never opened
LAB_RUN_ENV = ("BRAND", "OUT")         # platform/workers/mini-worker/lab_run.py:1712-1713 (and lab_entry.py:81-83)
WORKER_ENV = "WORKER_WS"               # platform/workers/mini-worker/clone_root.py:42 ENV_VAR


class Held(Exception):
    pass


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


# ------------------------------------------------------------------ the job

def from_handoff(folder):
    """What the hand-off folder says: brand, the run label, the email, the
    links it allows, where the pictures are."""
    root = Path(folder).resolve()
    mf = json.loads((root / "manifest.json").read_text())
    if mf.get("role") != "klaviyo-uploader":
        raise Held([f"{root.name} is a {mf.get('role')} hand-off, not klaviyo-uploader"])
    idx = json.loads((root / "assets/index.json").read_text())
    src = ((idx.get("email_run") or {}).get("source") or "")
    here = root / ((idx.get("email_run") or {}).get("here") or "assets/email/")
    links = json.loads((root / "references/links.json").read_text()) \
        if (root / "references/links.json").is_file() else {}
    run_dir = WORKSPACE / src if src else None
    return {
        "mode": "handoff", "root": root, "brand": mf["brand"],
        "label": Path(src).name if src else None,
        "brief_ids": [b["id"] for b in mf.get("briefs", [])],
        "deliverable": here / "deliverable",
        "media": [here / "media", run_dir / "media" if run_dir else None,
                  S.drive_media(mf["brand"], (Path(src).name if src else ""))[1]],
        "run_dir": run_dir if run_dir and (run_dir / "run.json").is_file() else None,
        "links": {v.get("url"): k for k, v in links.items() if v.get("url")},
        "out": root,
    }


def from_run(folder, brand=None):
    rd = Path(folder)
    rd = (rd if rd.is_absolute() else Path.cwd() / rd).resolve()
    run = json.loads((rd / "run.json").read_text()) if (rd / "run.json").is_file() else {}
    brand = brand or run.get("brand")
    if not brand:
        raise Held([f"{rd.name}: no brand in run.json — pass --brand"])
    return {
        "mode": "run", "root": rd, "brand": brand, "label": rd.name, "brief_ids": [],
        "deliverable": rd / "deliverable",
        "media": [rd / "media", S.drive_media(brand, rd.name)[1]],
        "run_dir": rd if (rd / "stage8c--check.md").is_file() or (rd / "run.json").is_file() else None,
        "links": None, "out": rd / "deliverable",
    }


def hero_picture(job, online=True):
    """The hero as made for this email: hero.png, or the image machine's
    <label>--hero-NN.png. Gitignored pictures are looked for on Drive too —
    on the API route (a key in the environment), read back by id into the
    run's media/; never on a dry run, which talks to nothing."""
    for d in job["media"]:
        if not d or not Path(d).is_dir():
            continue
        for pat in ("hero.png", f"{job['label']}--hero-*.png", "*--hero-*.png"):
            hits = sorted(Path(d).glob(pat))
            if hits:
                return hits[0]
    if online and job["mode"] == "run" and job.get("label"):
        try:
            if DR.route() == "api":
                got = DR.get(["runs", S.MACHINE, job["brand"], job["label"]], "hero.png",
                             Path(job["root"]) / "media")
                if got:
                    return got
        except DR.NoDrive:
            pass
    if job["mode"] == "handoff":   # the hand-off's own Drive copy
        mf = json.loads((job["root"] / "manifest.json").read_text())
        mount = (mf.get("drive") or {}).get("mount")
        if mount and Path(mount).is_dir():
            hits = sorted((Path(mount) / "assets/email/media").glob("*hero*.png"))
            if hits:
                return hits[0]
    return None


def hrefs(doc):
    import html
    return [html.unescape(h) for h in re.findall(r'href="([^"]+)"', doc) if not h.startswith("{%")]


def answers(url):
    r = subprocess.run(["curl", "-sS", "-L", "-o", "/dev/null", "-w", "%{http_code}",
                        "--max-time", "30", "-A", "Mozilla/5.0", url],
                       capture_output=True, text=True)
    return r.stdout.strip() or r.stderr.strip()[:120]


def check(job, pick, online):
    """Every check; returns (checks rows, problems, the plan for the draft)."""
    rows, problems = [], []

    def row(name, ok, detail):
        rows.append({"check": name, "result": "ok" if ok else "PROBLEM", "detail": detail})
        if not ok:
            problems.append(f"{name}: {detail}")

    brand, label = job["brand"], job["label"]
    ej = job["deliverable"] / "email.json"
    if not ej.is_file():
        raise Held([f"no finished email at {ej} — run simple_email.py first"])
    email = json.loads(ej.read_text())
    lk = S.look(brand)

    # the words
    row("headline", bool((email.get("headline") or "").strip()), email.get("headline") or "missing")
    row("body", any(p.strip() for p in email.get("body") or []),
        f"{len(email.get('body') or [])} paragraph(s)")
    subs = email.get("subjects") or []
    pair = subs[pick] if 0 <= pick < len(subs) else {}
    row("subject", bool((pair.get("subject") or "").strip()),
        f"pair {pick}: {pair.get('subject')!r}" if pair else f"pair {pick} not in the set (0..{len(subs) - 1})")
    row("preview text", bool((pair.get("preview") or "").strip()),
        f"pair {pick}: {pair.get('preview')!r}" if pair.get("preview") else f"pair {pick} has no preview text")

    # the delivery gate — the shared checks, rerun on the source run when we
    # have it, on the pair that will be SENT (SI-151 (picked subject gated))
    if job["run_dir"] and (job["run_dir"] / "stage8c--check.md").is_file():
        found = S.delivery_problems(email, brand, job["run_dir"], pick)
        row("delivery gate", not found, "pass (rerun now)" if not found else "; ".join(found))
    else:
        # check.json records no pick (Q.hold writes result/problems/items/
        # cleared only), so its pass vouches for pair 0 alone
        cj = job["deliverable"] / "check.json"
        res = (json.loads(cj.read_text()).get("delivery") or {}) if cj.is_file() else {}
        if res.get("result") == "pass" and pick != 0:
            row("delivery gate", False,
                f"the run's own check.json passed subject pair 0, not pair {pick} — "
                f"rerun the gate with --pick {pick}")
        else:
            row("delivery gate", res.get("result") == "pass",
                "pass (the run's own check.json)" if res.get("result") == "pass"
                else f"check.json says {res.get('result') or 'nothing'}: {res.get('problems')}")

    # the audience and the day
    slot = S.the_slot(brand, label) if label else None
    seg_names, seg_ids = [], []
    if not slot:
        row("audience", False, f"no calendar send named {label} for {brand} — never guessed")
    else:
        seg_names, seg_ids, missing = S.audience(brand, slot)
        row("audience", not missing,
            ", ".join(f"{n} → {i}" for n, i in zip(seg_names, seg_ids)) if not missing
            else f"no Klaviyo id in the audience matrix for {missing}")
    frm = lk.get("from") or {}
    row("from-line", bool(frm.get("email")), f"{frm.get('label')} <{frm.get('email')}>")
    row("Klaviyo key named", bool(lk.get("klaviyo_key")),
        lk.get("klaviyo_key") or "simple.json names no klaviyo_key — this brand's Klaviyo is not connected")

    strategy, when, passed = None, None, False
    st = lk.get("send_time") or {}
    if slot and slot.get("date") and st.get("local"):
        when = f"{slot['date']} {st['local']}"
        passed = datetime.datetime.fromisoformat(f"{slot['date']}T{st['local']}") <= datetime.datetime.now()
        if not passed:
            strategy = S.send_strategy(lk, slot)
    rows.append({"check": "send day", "result": "ok" if not passed else "NOTE",
                 "detail": (f"{when}, each recipient's own time zone" if not passed else
                            f"the plan's day ({when}) has passed — the draft is made with no "
                            "send time; a new day is set before it can be scheduled")
                 if when else "no day in the plan"})

    # the picture
    hero = hero_picture(job, online=online) if email.get("hero") else None
    if email.get("hero"):
        row("hero picture", bool(hero), str(hero) if hero else
            f"no hero picture found for {label} (looked in the run, the hand-off and Drive)")

    # the links, in the HTML exactly as it will go out
    # — tagged with the tracking standard's email tags (components/funnel-tracking, email_url);
    # a link is matched to the hand-off's list by its plain form, and fetched as it will go out
    doc = S.finished_html(email, lk, {"hero": "cid:hero"} if hero else {},
                          lk["logo"].get("url") or "cid:logo", brand, label or "", S.EL.term_for(seg_names))
    untagged = S.link_problems(doc, brand)
    row("link tags", not untagged,
        "every own link carries utm_source/medium/campaign/content (+ funnel on a funnel page)"
        if not untagged else "; ".join(untagged))
    logo_link = S.EL.untag((lk.get("logo") or {}).get("link") or "")
    allowed = job["links"] if job["links"] is not None else \
        {(email.get("button") or {}).get("link"): "the button"}
    allowed = {S.EL.untag(k): v for k, v in allowed.items() if k}
    for url in dict.fromkeys(hrefs(doc)):
        plain = S.EL.untag(url)
        if plain == logo_link:
            how = "the brand's logo link (simple.json)"
        elif plain in allowed:
            how = allowed[plain]
        else:
            row("link allowed", False, f"{url} is not a link the hand-off names")
            continue
        if online:
            code = answers(url)
            row("link answers", code == "200", f"{url} ({how}) → {code}")
        else:
            rows.append({"check": "link allowed", "result": "ok",
                         "detail": f"{url} ({how}) — not fetched (dry run)"})

    # already done once?
    prior = existing_draft(job)
    if prior:
        row("not already in Klaviyo", False,
            f"this email already has Klaviyo campaign {prior} — pass --again to make another")

    plan = {"email": email, "lk": lk, "slot": slot, "names": seg_names, "ids": seg_ids,
            "strategy": strategy, "when": when, "date_passed": passed, "hero": hero,
            "subject": pair.get("subject"), "preview": pair.get("preview")}
    return rows, problems, plan


def existing_draft(job):
    for f in (job["out"] / "returned/live-ids.json", job["out"] / "pushed.json", job["out"] / STATUS):
        if f.is_file():
            try:
                d = json.loads(f.read_text())
            except ValueError:
                continue
            for r in (d if isinstance(d, list) else [d]):
                cid = r.get("platform_id") or r.get("campaign_id")
                if cid:
                    return cid
    return None


# --------------------------------------------------------------- the draft

def create(job, plan, pick):
    key = S.kl_key(plan["lk"])
    pics = {}
    if plan["hero"]:
        pics["hero"] = S.upload(key, S.web_copy(plan["hero"]), f"{job['brand']}-{job['label']}-hero")
    lk = plan["lk"]
    logo = lk["logo"].get("url") or S.upload(key, S.logo_file(job["brand"], lk["logo"]["file"]),
                                             f"{job['brand']}-logo")
    doc = S.finished_html(plan["email"], lk, pics, logo, job["brand"], job["label"],
                          S.EL.term_for(plan["names"]))
    rec = S.create_draft(key, doc, plan["email"], lk, job["brand"], job["label"], plan["slot"],
                         plan["names"], plan["ids"], pick, plan["strategy"])
    rec["hosted"] = pics
    return rec


def write_back(job, rec, rows):
    """The id goes back where the hand-off expects it, and the ledger hears."""
    if job["mode"] == "run":
        (job["out"] / "pushed.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
        return None
    ret = job["root"] / "returned"
    ret.mkdir(exist_ok=True)
    live = [{"send": job["label"], "email_name": rec["campaign_name"], "brief_id": b,
             "channel": "klaviyo", "platform_id": rec["campaign_id"],
             "template_id": rec["template_id"], "status": "DRAFT"}
            for b in (job["brief_ids"] or [None])]
    (ret / "live-ids.json").write_text(json.dumps(live, indent=1, ensure_ascii=False) + "\n")
    lines = [f"# Klaviyo checks — {job['label']}", "",
             f"Campaign {rec['campaign_id']} · DRAFT · {now()}", "",
             "| check | result | detail |", "|---|---|---|"]
    lines += [f"| {r['check']} | {r['result']} | {str(r['detail']).replace('|', '/')} |" for r in rows]
    tag = job["brief_ids"][0] if job["brief_ids"] else job["label"]
    (ret / f"{tag}_klaviyo-checks.md").write_text("\n".join(lines) + "\n")
    # handoff take-back: staging/<role>/<brand>/<name>
    root = job["root"]
    staging = root.parents[2]
    spec = importlib.util.spec_from_file_location("ad_handoff_take_back", TAKE_BACK_PY)
    TB = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(TB)
    idx = TB.take_back(root.parents[1].name, root.parent.name, root.name, staging,
                      staging / "ledger.jsonl")
    return [l["live_id"] for l in idx["live_ids"] if l.get("live_id")]


def status(job, state, rows, problems, plan=None, rec=None, ledger=None, extra=None):
    st = {
        "state": state, "updated": now(), "brand": job["brand"], "email": job["label"],
        "briefs": job["brief_ids"], "from": job["mode"], "folder": str(job["root"]),
        "campaign_id": (rec or {}).get("campaign_id"),
        "template_id": (rec or {}).get("template_id"),
        "campaign_name": (rec or {}).get("campaign_name"),
        "subject": (plan or {}).get("subject"), "preview": (plan or {}).get("preview"),
        "audience": [{"segment": n, "id": i} for n, i in
                     zip((plan or {}).get("names") or [], (plan or {}).get("ids") or [])],
        "send_day": (plan or {}).get("when"), "send_day_passed": (plan or {}).get("date_passed"),
        "checks": rows, "problems": problems, "ledger": ledger,
        "send_go": "waiting for the owner on the email approval page (EP-3 (email approval card))",
    }
    st.update(extra or {})
    return st


def save_status(job, st):
    out = job["out"] / STATUS
    out.write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")
    return out


# ---------------------------------------------------------------- the card
# EP-3 (email approval card): every checked draft gets a card, and the owner's
# Approve → Schedule on the email approval page is the only road to a send.

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(t):
    return t.isoformat(timespec="seconds") if t else None


def _sha(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _when(stamp):
    """A Klaviyo datetime → an aware datetime, or None (3.9's fromisoformat
    takes no trailing Z; a stamp with no offset is read as UTC)."""
    if not isinstance(stamp, str) or not stamp.strip():
        return None
    try:
        t = datetime.datetime.fromisoformat(stamp.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def plain_strategy(strategy):
    """The send strategy reduced to what decides WHEN: the method, the time in
    UTC, and whether it is each recipient's own time. No is_local on file
    counts as local — the earlier first send, so the 30-minute floor bites
    sooner, never later."""
    s = strategy if isinstance(strategy, dict) else {}
    t = _when(s.get("datetime"))
    opts = s.get("options") if isinstance(s.get("options"), dict) else {}
    return {"method": s.get("method"),
            "datetime": t.astimezone(datetime.timezone.utc).isoformat() if t else None,
            "is_local": bool(opts.get("is_local", True))}


def earliest_send(strategy):
    """When the FIRST recipient gets it, in aware UTC, or None. A local send
    goes out at its wall time in each recipient's own zone, so UTC+14 gets it
    LOCAL_SPAN before that wall time read as UTC."""
    t = _when((strategy or {}).get("datetime") if isinstance(strategy, dict) else None)
    if t is None:
        return None
    if plain_strategy(strategy)["is_local"]:
        return t.replace(tzinfo=datetime.timezone.utc) - LOCAL_SPAN
    return t.astimezone(datetime.timezone.utc)


def fingerprint(subject, preview, html, audience_ids, strategy):
    """One hash per part that reaches a recipient, and one over them all."""
    parts = {"subject": _sha(subject), "preview": _sha(preview), "html": _sha(html),
             "audience": _sha(json.dumps(sorted(str(i) for i in audience_ids or []))),
             "send_time": _sha(json.dumps(plain_strategy(strategy), sort_keys=True))}
    return {"sha256": _sha(json.dumps(parts, sort_keys=True)), "parts": parts}


def klaviyo_draft(key, campaign_id):
    """What Klaviyo holds for the campaign — two reads, nothing written."""
    camp = S.kl("GET", f"campaigns/{campaign_id}?include=campaign-messages", key)
    attrs = (camp.get("data") or {}).get("attributes") or {}
    msg = next((i for i in camp.get("included") or [] if i.get("type") == "campaign-message"), None)
    if not msg or not msg.get("id"):
        raise Held([f"Klaviyo's campaign {campaign_id} has no email message"])
    content = ((msg.get("attributes") or {}).get("definition") or {}).get("content") or {}
    tpl = (S.kl("GET", f"campaign-messages/{msg['id']}/template", key).get("data")) or {}
    return {"status": attrs.get("status") or "", "subject": content.get("subject"),
            "preview": content.get("preview_text"), "html": (tpl.get("attributes") or {}).get("html") or "",
            "audience_ids": list((attrs.get("audiences") or {}).get("included") or []),
            "strategy": attrs.get("send_strategy") or {}, "message_id": msg["id"],
            "template_id": tpl.get("id")}


def html_link_rows(job, plan, doc):
    """check()'s offline link rows (its :232-254), over the HTML Klaviyo holds."""
    rows, problems = [], []

    def row(name, ok, detail):
        rows.append({"check": name, "result": "ok" if ok else "PROBLEM", "detail": detail})
        if not ok:
            problems.append(f"{name}: {detail}")

    lk, email = plan["lk"], plan["email"]
    untagged = S.link_problems(doc, job["brand"])
    row("Klaviyo's HTML: link tags", not untagged,
        "every own link carries its tracking tags" if not untagged else "; ".join(untagged))
    logo_link = S.EL.untag((lk.get("logo") or {}).get("link") or "")
    allowed = job["links"] if job["links"] is not None else \
        {(email.get("button") or {}).get("link"): "the button"}
    allowed = {S.EL.untag(k): v for k, v in allowed.items() if k}
    for url in dict.fromkeys(hrefs(doc)):
        plain = S.EL.untag(url)
        if plain == logo_link or plain in allowed:
            how = "the brand's logo link (simple.json)" if plain == logo_link else allowed[plain]
            rows.append({"check": "Klaviyo's HTML: link allowed", "result": "ok", "detail": f"{url} ({how})"})
        else:
            row("Klaviyo's HTML: link allowed", False, f"{url} is not a link the hand-off names")
    return rows, problems


def read_card(job):
    f = job["out"] / CARD
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text())
    except ValueError:
        raise Held([f"{f} cannot be read — make the card again (klaviyo_upload.py --card)"])


def save_card(job, card):
    f = job["out"] / CARD
    f.write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    return f


def write_card(job, campaign_id, rows, plan, pick, key):
    """Read the draft back from Klaviyo and write its card — only when Klaviyo
    holds exactly what was checked."""
    try:
        d = klaviyo_draft(key, campaign_id)
    except SystemExit as e:
        raise Held([f"Klaviyo's draft {campaign_id} could not be read back: {e.code}"])
    differ = []
    if (d["subject"] or "") != (plan["subject"] or ""):
        differ.append(f"subject (Klaviyo {d['subject']!r}, checked {plan['subject']!r})")
    if (d["preview"] or "") != (plan["preview"] or ""):
        differ.append(f"preview (Klaviyo {d['preview']!r}, checked {plan['preview']!r})")
    if sorted(map(str, d["audience_ids"])) != sorted(str(i) for i in plan["ids"] if i):
        differ.append(f"audience (Klaviyo {d['audience_ids']}, checked {plan['ids']})")
    if plain_strategy(d["strategy"]) != plain_strategy(plan["strategy"]):
        differ.append(f"send time (Klaviyo {d['strategy']}, checked {plan['strategy']})")
    if differ:
        raise Held([f"Klaviyo's draft {campaign_id} is not what was checked: " + "; ".join(differ)])
    more, problems = html_link_rows(job, plan, d["html"])
    if problems:
        raise Held(problems)
    t = _iso(utc_now())
    card = {
        "schema": "ep3-email-card/1", "state": "waiting", "brand": job["brand"], "email": job["label"],
        "from": job["mode"], "folder": str(job["root"]), "pick": pick, "campaign_id": campaign_id,
        "template_id": d["template_id"], "message_id": d["message_id"],
        "campaign_name": S.campaign_name(plan["slot"] or {}, plan["subject"], plan["names"]),
        "klaviyo_link": KLAVIYO_LINK.format(id=campaign_id),
        "subject": d["subject"], "preview": d["preview"],
        "audience": [{"segment": n, "id": i} for n, i in zip(plan["names"], plan["ids"])],
        "send": {"strategy": d["strategy"], "earliest_utc": _iso(earliest_send(d["strategy"]))},
        "checks": list(rows) + more, "checked_at": t,
        "fingerprint": fingerprint(d["subject"], d["preview"], d["html"], d["audience_ids"], d["strategy"]),
        "fingerprint_at": t, "approval": None, "scheduled": None, "schedule_error": None,
    }
    (job["out"] / CARD_HTML).write_text(d["html"])
    return save_card(job, card)


def checks_now(job, pick, online):
    """check(), less its "not already in Klaviyo" row — the card is FOR that draft."""
    rows, problems, plan = check(job, pick, online)
    return ([r for r in rows if r["check"] != NOT_AGAIN],
            [p for p in problems if not p.startswith(NOT_AGAIN)], plan)


def card_for_existing(job, pick):
    """--card: the card for a draft already in Klaviyo (the owner's own, or a
    simple_email --push draft)."""
    cid = existing_draft(job)
    if not cid:
        raise Held(["no Klaviyo draft on record for this email — make the draft first"])
    prev = read_card(job)
    if prev and prev.get("state") == "scheduled":
        raise Held([f"REFUSED: campaign {prev.get('campaign_id')} is already scheduled from its card"])
    rows, problems, plan = checks_now(job, pick, online=True)
    if problems:
        raise Held(problems)
    if plan["date_passed"]:
        raise Held(["no card: the plan's day has passed — no send time on the draft"])
    return write_card(job, cid, rows, plan, pick, S.kl_key(plan["lk"]))


# --------------------------------------------------------------- the guards

def switch_state():
    """the team's off-switch: "on" only when send-switch.json says exactly that."""
    try:
        v = json.loads(SWITCH_F.read_text()).get("email_schedule")
    except (OSError, ValueError, AttributeError):
        return "off"
    return "on" if v == "on" else "off"


def approvers():
    try:
        names = json.loads(APPROVERS_F.read_text())["approvers"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    return [n for n in names if isinstance(n, str) and n.strip()] if isinstance(names, list) else []


def who(by):
    """The approver named, checked against approvers.json; a blank name picks
    the one approver when there is only one (meta-upload approve.py's who())."""
    names = approvers()
    by = (by or "").strip() if isinstance(by, str) else ""
    if by and by in names:
        return by
    if not by and len(names) == 1:
        return names[0]
    raise Held([f"REFUSED: {by or 'nobody'} is not on the approver list "
                f"({APPROVERS_F.name}: {', '.join(names) or 'empty'})"])


def reasons():
    """The send-back reasons manifest (send-back-reasons.json), the owner's."""
    try:
        rs = json.loads(REASONS_F.read_text())["reasons"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    return [r for r in rs if isinstance(r, dict) and r.get("id")]


def machine_run(env, home):
    """Why this is a machine's run and not a person's, or None."""
    if os.path.lexists(str(Path(home) / MINI_MARKER)):
        return f"this is the mini (~/{MINI_MARKER} is here — components/keys/loader.py:44)"
    if all(k in env for k in LAB_RUN_ENV):
        return "this is a lab-run job ($BRAND and $OUT are set — platform/workers/mini-worker/lab_run.py:1712-1713)"
    if WORKER_ENV in env:
        return f"this is a worker job (${WORKER_ENV} is set — platform/workers/mini-worker/clone_root.py:42)"
    return None


def log_line(job, card, by, decision, fp=None, detail=None, at=None):
    """One line on the schedule log — appended, never rewritten."""
    line = {"at": at or _iso(utc_now()), "by": by, "campaign_id": card.get("campaign_id"),
            "brand": card.get("brand") or job["brand"], "email": card.get("email") or job["label"],
            "decision": decision, "fingerprint": fp, "detail": detail}
    with open(job["out"] / LOG, "a") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


# ------------------------------------------------------------ the schedule

def schedule_card(job, by, env=None, home=None, at=None, online=True):
    """Approve → Schedule: the ONE place a Klaviyo email is scheduled (never
    sent now). Every refusal raises Held before any Klaviyo call."""
    env = os.environ if env is None else env
    home = Path.home() if home is None else Path(home)
    at = at or utc_now()
    card = read_card(job)
    if not card:
        raise Held(["REFUSED: no email card for this email — make it with klaviyo_upload.py --card"])
    if card.get("state") not in ("waiting", "approved"):
        raise Held([f"REFUSED: this card is {card.get('state')} — only a waiting card is scheduled "
                    "(or an approved one, retried)"])
    if switch_state() != "on":
        raise Held(["REFUSED: the email off-switch is off (tools/email-production/send-switch.json)"])
    by = who(by)
    why = machine_run(env, home)
    if why:
        raise Held([f"REFUSED: {why} — a machine never schedules an email"])
    rows, problems, plan = checks_now(job, card.get("pick") or 0, online)
    if problems:
        raise Held(["REFUSED: a check is failing — " + p for p in problems])
    if plan["date_passed"]:
        raise Held(["REFUSED: the plan's day has passed — no send time to schedule"])
    cid = card.get("campaign_id")
    try:
        key = S.kl_key(plan["lk"])
        d = klaviyo_draft(key, cid)
    except SystemExit as e:
        raise Held([f"REFUSED: Klaviyo's draft {cid} could not be read: {e.code}"])
    if (d["status"] or "").lower() != "draft":
        raise Held([f"REFUSED: Klaviyo says campaign {cid} is {d['status'] or 'of no status'}, not a draft"])
    st = d["strategy"] if isinstance(d["strategy"], dict) else {}
    earliest = earliest_send(st)
    if st.get("method") != "static" or earliest is None:
        raise Held([f"REFUSED: the draft's send strategy is {st.get('method') or 'not set'} — it could send "
                    "now; set a fixed time in Klaviyo and re-card"])
    fp = fingerprint(d["subject"], d["preview"], d["html"], d["audience_ids"], st)
    was = card.get("fingerprint") or {}
    if fp["sha256"] != was.get("sha256"):
        changed = [k for k in fp["parts"] if fp["parts"][k] != (was.get("parts") or {}).get(k)]
        raise Held([f"REFUSED: the email changed since its checks passed: {', '.join(changed) or 'fingerprint'}"])
    if earliest < at + MIN_LEAD:
        raise Held([f"REFUSED: the first recipients would get it at {_iso(earliest)} — "
                    "less than 30 minutes from now"])

    stamp = _iso(at)
    card["approval"] = {"by": by, "at": stamp, "decision": "approve", "fingerprint": fp["sha256"]}
    card["state"] = "approved"
    save_card(job, card)
    log_line(job, card, by, "approve", fp["sha256"], f"earliest send {_iso(earliest)}", at=stamp)
    try:
        S.kl("POST", "campaign-send-jobs", key, {"data": {"type": "campaign-send-job", "id": cid}})
    except SystemExit as e:
        card["schedule_error"] = {"at": _iso(utc_now()), "error": str(e.code)}
        save_card(job, card)
        log_line(job, card, by, "error", fp["sha256"], str(e.code))
        raise Held([f"Klaviyo refused the schedule: {e.code} — the card stays approved; retry it from the page"])
    try:        # the schedule is made; a failed read-back only leaves its status unknown
        got = S.kl("GET", f"campaigns/{cid}", key)
        kstatus = ((got.get("data") or {}).get("attributes") or {}).get("status")
    except SystemExit as e:
        kstatus = f"not read: {e.code}"
    card["scheduled"] = {"at": _iso(utc_now()), "klaviyo_status": kstatus}
    card["schedule_error"] = None
    card["state"] = "scheduled"
    save_card(job, card)
    log_line(job, card, by, "scheduled", fp["sha256"], f"Klaviyo: {kstatus}")
    try:
        prev = json.loads((job["out"] / STATUS).read_text()) if (job["out"] / STATUS).is_file() else {}
    except ValueError:
        prev = {}
    prev.update({"state": "SCHEDULED IN KLAVIYO", "updated": now(),
                 "send_go": f"approved by {by} on the email approval page at {stamp}"})
    save_status(job, prev)
    return cid, card


def send_back(job, by, reason_ids, note):
    """Send back: reasons from send-back-reasons.json and a note. No Klaviyo
    call — the draft stays in Klaviyo."""
    note = (note or "").strip() if isinstance(note, str) else ""
    if not reason_ids:
        raise Held(["pick at least one reason"])
    if not note:
        raise Held(["say why — a send-back needs a note"])
    by = who(by)
    card = read_card(job)
    if not card:
        raise Held(["no email card for this email"])
    if card.get("state") not in ("waiting", "approved"):
        raise Held([f"this card is {card.get('state')} — it cannot be sent back from here"])
    known = {r["id"]: r for r in reasons()}
    unknown = [str(r) for r in reason_ids if not isinstance(r, str) or r not in known]
    if unknown:
        raise Held([f"unknown reason(s): {', '.join(unknown)} (not in {REASONS_F.name})"])
    stamp = _iso(utc_now())
    picked = [{"id": r, "label": known[r].get("label")} for r in dict.fromkeys(reason_ids)]
    card["approval"] = {"by": by, "at": stamp, "decision": "send-back", "reasons": picked, "note": note}
    card["state"] = "sent-back"
    save_card(job, card)
    log_line(job, card, by, "send-back", (card.get("fingerprint") or {}).get("sha256"),
             "; ".join(r["id"] for r in picked) + f" — {note}", at=stamp)
    return card


def send_cli(job):
    """--send never schedules (lead ruling, EP-3 (email approval card)): it
    reads no card and no approvals.json and makes no Klaviyo call."""
    raise Held([f"REFUSED: --send does not schedule. A Klaviyo email is scheduled only by the owner's "
                f"Approve on the email approval page ({PAGE_URL}), or his own Claude acting on that "
                "page — a card file or approvals.json is never a go (O5c; EP-3 (email approval card))"])


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--handoff", help="a klaviyo-uploader hand-off folder")
    src.add_argument("--run", help="a finished email run (runs/email-production/<brand>/<label>)")
    ap.add_argument("--brand", help="--run only, when run.json names none")
    ap.add_argument("--pick", type=int, default=0, help="subject pair (0 = the main one)")
    ap.add_argument("--dry-run", action="store_true", help="checks only — talks to nothing, writes nothing")
    ap.add_argument("--again", action="store_true", help="make a draft even though one exists")
    ap.add_argument("--card", action="store_true",
                    help="make the approval card for a draft already in Klaviyo (re-checked first)")
    ap.add_argument("--send", action="store_true",
                    help="always refused — scheduling is the owner's Approve on the email approval page")
    a = ap.parse_args(argv)
    if a.card and a.dry_run:
        ap.error("--card reads Klaviyo; it has no dry run")
    try:
        job = from_handoff(a.handoff) if a.handoff else from_run(a.run, a.brand)
        if a.send:
            send_cli(job)                # always raises Held
        if a.card:
            try:
                out = card_for_existing(job, a.pick)
            except SystemExit as e:      # no key, or Klaviyo refused a read
                raise Held([f"no card: {e.code}"])
            print(f"CARD written: {out}\n  waiting for the owner on the email approval page ({PAGE_URL})")
            return 0
        rows, problems, plan = check(job, a.pick, online=not a.dry_run)
        if a.again:
            problems = [p for p in problems if not p.startswith("not already in Klaviyo")]
        if problems:
            if not a.dry_run:
                save_status(job, status(job, "HELD", rows, problems, plan))
            print("HELD — nothing sent to Klaviyo:\n  " + "\n  ".join(problems))
            return 1
        if a.dry_run:
            st = status(job, "DRY RUN — would make a draft in Klaviyo", rows, problems, plan)
            print(json.dumps(st, indent=1, ensure_ascii=False))
            return 0
        try:
            rec = create(job, plan, a.pick)
        except SystemExit as e:          # the engine exits on a Klaviyo refusal; keep its words
            save_status(job, status(job, "KLAVIYO ERROR", rows, [str(e.code)], plan))
            print(f"KLAVIYO ERROR — {e.code}")
            return 1
        if plan["date_passed"]:
            card = "no card: the plan's day has passed — no send time on the draft"
        else:
            try:
                card = f"card {write_card(job, rec['campaign_id'], rows, plan, a.pick, S.kl_key(plan['lk']))}"
            except Held as h:            # the draft stays in Klaviyo, with no card
                save_status(job, status(job, "HELD", rows, h.args[0], plan, rec))
                print(f"HELD — the draft is in Klaviyo (campaign {rec['campaign_id']}) but gets no card:\n  "
                      + "\n  ".join(h.args[0]))
                return 1
        ledger = write_back(job, rec, rows)
        out = save_status(job, status(job, "DRAFT IN KLAVIYO", rows, problems, plan, rec, ledger))
        print(f"DRAFT in Klaviyo: campaign {rec['campaign_id']} · “{rec['subject']}” · "
              f"{', '.join(rec['segments'])}" + (f" · ledger {', '.join(ledger)}" if ledger else "")
              + f"\n  status {out}\n  {card}\n  Not scheduled, not sent — that waits for the owner on the "
              f"email approval page ({PAGE_URL}).")
        return 0
    except Held as h:
        print("HELD — nothing sent to Klaviyo:\n  " + "\n  ".join(h.args[0]))
        return 1


if __name__ == "__main__":
    sys.exit(main())
