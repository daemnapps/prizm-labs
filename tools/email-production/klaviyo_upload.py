#!/usr/bin/env python3
"""The Klaviyo uploader: a finished email → a DRAFT campaign in Klaviyo,
the campaign id written back. One command.

    python3 klaviyo_upload.py --handoff <klaviyo-uploader hand-off folder>
    python3 klaviyo_upload.py --run runs/email-production/<brand>/<label>
    python3 klaviyo_upload.py --handoff <folder> --dry-run   # checks only; talks to nothing
    python3 klaviyo_upload.py --handoff <folder> --send      # REFUSED unless the owner's go is on file

DEFAULT = THE DRAFT, AND ONLY THE DRAFT. In order:
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
  4 writes the id back: returned/live-ids.json + returned/<brief>_klaviyo-checks.md
    in the hand-off, then runs ad-handoff's take_back, so the ledger records
    live_klaviyo_<campaign id>. For a bare run: deliverable/pushed.json.
  5 writes klaviyo-status.json — the small record a page shows.

THE SEND STEP (--send) exists and refuses. It goes ahead only when an
approvals.json beside the status file carries THIS campaign id with
"go_by": "the owner". Nothing in this tool, and no agent, writes that file.

--dry-run runs every check that needs no network and prints what it would
create: no Klaviyo call, no link fetch, no Keychain read, no file written.
"""
import argparse
import datetime
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import simple_email as S          # the engine; puts ~/.daemn and the shared checks on the path
from paths import HERE, WORKSPACE
import drive_reach as DR

STATUS = "klaviyo-status.json"
APPROVALS = "approvals.json"
TAKE_BACK_PY = HERE.parent / "ad-handoff" / "take_back.py"


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
    return [h for h in re.findall(r'href="([^"]+)"', doc) if not h.startswith("{%")]


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
    doc = S.render(email, lk, {"hero": "cid:hero"} if hero else {}, lk["logo"].get("url") or "cid:logo")
    logo_link = (lk.get("logo") or {}).get("link")
    allowed = job["links"] if job["links"] is not None else \
        {(email.get("button") or {}).get("link"): "the button"}
    for url in dict.fromkeys(hrefs(doc)):
        if url == logo_link:
            how = "the brand's logo link (simple.json)"
        elif url in allowed:
            how = allowed[url]
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
    doc = S.render(plan["email"], lk, pics, logo)
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
        "send_go": "the owner's go not on file — the draft cannot be scheduled or sent by this tool",
    }
    st.update(extra or {})
    return st


def save_status(job, st):
    out = job["out"] / STATUS
    out.write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")
    return out


# ---------------------------------------------------------------- the send

def approved(job, campaign_id):
    """the owner's go for THIS campaign, or None. The file is a list (or
    {"approvals": [...]}) of {"campaign_id", "go_by": "the owner", ...}."""
    f = job["out"] / APPROVALS
    if not f.is_file():
        return None
    try:
        d = json.loads(f.read_text())
    except ValueError:
        return None
    for a in (d.get("approvals", []) if isinstance(d, dict) else d):
        if isinstance(a, dict) and a.get("campaign_id") == campaign_id and a.get("go_by") == "the owner":
            return a
    return None


def send(job):
    """Schedule the draft by its own send time — only on the owner's recorded go."""
    cid = existing_draft(job)
    if not cid:
        raise Held(["no Klaviyo draft on record for this email — make the draft first"])
    go = approved(job, cid)
    if not go:
        raise Held([f"REFUSED: no go from the owner on file for campaign {cid} "
                    f"({job['out'] / APPROVALS} must list this campaign id with \"go_by\": \"the owner\")"])
    prev = json.loads((job["out"] / STATUS).read_text()) if (job["out"] / STATUS).is_file() else {}
    if prev.get("send_day_passed") and not go.get("send_at"):
        raise Held([f"REFUSED: campaign {cid} was made with no send time (the plan's day had "
                    "passed) — the go must name the new time as \"send_at\""])
    lk = S.look(job["brand"])
    key = S.kl_key(lk)
    if go.get("send_at"):        # a new day the owner named with the go
        S.kl("PATCH", f"campaigns/{cid}", key, {"data": {"type": "campaign", "id": cid, "attributes": {
            "send_strategy": {"method": "static", "datetime": go["send_at"],
                              "options": {"is_local": bool((lk.get("send_time") or {}).get("recipient_time_zone", True)),
                                          "send_past_recipients_immediately": False}}}}})
    out = S.kl("POST", "campaign-send-jobs", key, {"data": {"type": "campaign-send-job", "id": cid}})
    return cid, go, out


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
    ap.add_argument("--send", action="store_true", help="schedule the draft — refused without the owner's go")
    a = ap.parse_args(argv)
    try:
        job = from_handoff(a.handoff) if a.handoff else from_run(a.run, a.brand)
        if a.send:
            cid, go, _ = send(job)
            prev = json.loads((job["out"] / STATUS).read_text()) if (job["out"] / STATUS).is_file() else {}
            prev.update({"state": "SCHEDULED IN KLAVIYO", "updated": now(),
                         "send_go": f"go by {go['go_by']}" + (f" at {go['at']}" if go.get("at") else "")})
            save_status(job, prev)
            print(f"SCHEDULED campaign {cid} on the owner's go")
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
        ledger = write_back(job, rec, rows)
        out = save_status(job, status(job, "DRAFT IN KLAVIYO", rows, problems, plan, rec, ledger))
        print(f"DRAFT in Klaviyo: campaign {rec['campaign_id']} · “{rec['subject']}” · "
              f"{', '.join(rec['segments'])}" + (f" · ledger {', '.join(ledger)}" if ledger else "")
              + f"\n  status {out}\n  Not scheduled, not sent — that waits for the owner's go.")
        return 0
    except Held as h:
        print("HELD — nothing sent to Klaviyo:\n  " + "\n  ".join(h.args[0]))
        return 1


if __name__ == "__main__":
    sys.exit(main())
