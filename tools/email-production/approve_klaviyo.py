#!/usr/bin/env python3
"""The Klaviyo approval page: every finished email on one card; the owner's click puts it in Klaviyo as a DRAFT.

    python3 approve_klaviyo.py                  # http://localhost:8798  (launch config "klaviyo-approve")
    python3 approve_klaviyo.py --fake-klaviyo   # trials: nothing reaches Klaviyo

the owner, 2026-10-09: "Similar to how I have an approval page for Meta, I need the same exact thing,
but for Klaviyo." The twin of components/meta-upload/approve.py.

Shows every card at runs/email-production/<brand>/<label>/klaviyo/card.json (any brand): the email
exactly as it will go out, its day and send hour (each recipient's own time zone), its segments
resolved to their Klaviyo ids through the brand's audience matrix, subject and preview, every link
with whether it answers, and the flags a person must see first.

**Approve → Klaviyo** (refused while a link is dead or a segment has no id) uploads the email's
pictures to the brand's Klaviyo image library, swaps them into the HTML, and creates the template
and a DRAFT campaign with the segments, subject, preview, from-line and send time set
(simple_email.create_draft — the same calls the email line already makes). Approve makes a
DRAFT only: nothing is scheduled or sent. The campaign id, who approved and the draft's
fingerprint (read back from Klaviyo) are written on the card.

**Schedule** (two clicks) releases the draft on the send time already set, through the same
guards as klaviyo_upload.schedule_card — LD-74 (one guarded schedule): refused while the
off-switch send-switch.json is off or missing, for anyone not on approvers.json, on the mini or
in a worker job, while the final check has a problem, when Klaviyo's draft is not a draft or has
no fixed send time, when the email changed since its fingerprint, and when the first recipients
would get it less than 30 minutes from now. The refusal is shown on the card. **Send back**
needs a reason and a note; it is written on the card and to
runs/email-production/<brand>/learnings.jsonl.

The click on this page is the only thing that writes an approval. Nothing here runs on a timer.
Listens on 127.0.0.1 only.
"""
import sys
_here = sys.path.pop(0)          # this folder's email.py shadows the stdlib email package http.server needs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
sys.path.insert(0, _here)
import argparse
import datetime
import html
import json
import mimetypes
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import klaviyo_upload as K  # noqa: E402  (the schedule guards; before S, which takes this folder off sys.path)
import simple_email as S  # noqa: E402
from paths import WORKSPACE  # noqa: E402

RUNS = WORKSPACE / "runs" / "email-production"
LOCK = threading.Lock()
FAKE = False
REASONS = ["copy is off-brand", "copy makes a claim we can't make", "wrong picture", "product looks wrong",
           "wrong segment", "wrong day", "link is wrong", "too long", "other"]
E = html.escape


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def cards():
    out = []
    for f in sorted(RUNS.glob("*/*/klaviyo/card.json")):
        try:
            c = json.loads(f.read_text())
        except ValueError:
            continue
        c["_dir"] = str(f.parent)
        out.append(c)
    return sorted(out, key=lambda c: (c.get("brand"), c.get("year", 0), _iso(c)))


def _iso(c):
    try:
        return datetime.datetime.strptime("%s %s" % (c["date"], c.get("year", 2026)), "%d %b %Y").date().isoformat()
    except (KeyError, ValueError):
        return c.get("date") or ""


_KS = {}


def klaviyo_status(brand):
    """Read-only: is the brand's Klaviyo key live, and how many people are in each segment the cards use."""
    import time
    hit = _KS.get(brand)
    if hit and time.time() - hit["at"] < 600:
        return hit
    out = {"at": time.time(), "ok": False, "account": None, "segments": {}, "error": None}
    if FAKE:
        out.update(ok=True, account="trial mode")
        _KS[brand] = out; return out
    try:
        key = S.kl_key(S.look(brand))
        a = S.kl("GET", "accounts", key)
        out["account"] = a["data"][0]["attributes"]["contact_information"].get("organization_name")
        ids = sorted({i for c in cards() if c["brand"] == brand for _, i in audience(c)[0] if i})
        for sid in ids:
            time.sleep(2.2)   # Klaviyo allows about one segment read a second
            r = S.kl("GET", "segments/%s?additional-fields[segment]=profile_count" % sid, key)
            out["segments"][sid] = r["data"]["attributes"].get("profile_count")
        out["ok"] = True
    except SystemExit as e:
        out["error"] = str(e)
    _KS[brand] = out
    return out


def _layout_file():
    """design/layout_file.py, loaded at call time with design/ appended (never ahead) on the path, as its look import needs."""
    if str(HERE / "design") not in sys.path:
        sys.path.append(str(HERE / "design"))
    import layout_file
    return layout_file


def card_dir(brand, label):
    d = RUNS / brand / label / "klaviyo"
    if not (d / "card.json").is_file():
        raise KeyError(label)
    return d


def audience(c):
    names, ids, missing = S.audience(c["brand"], {"segments": c["segments"]})
    held = (c.get("klaviyo") or {}).get("segment_ids") or c.get("segment_ids") or []
    ids = [i or (held[n] if n < len(held) else None) for n, i in enumerate(ids)]
    return list(zip(names, ids)), [nm for nm, i in zip(names, ids) if not i]


_ASKED, _ASK_LOCK, ASK_FOR = {}, threading.Lock(), 600   # page → (when, code); one ask per page every 10 minutes


def link_status(url):
    """Each page is asked once, whatever its tracking tags, and the answer kept 10 minutes: the page's live check
    asks every link of every card at once, and twelve asks for one store page is what made it answer 429
    (the team, 2026-10-27, as in design/check.py). The lock keeps those parallel asks to one per page."""
    page = page_of(url)
    with _ASK_LOCK:
        hit = _ASKED.get(page)
        if hit and time.time() - hit[0] < ASK_FOR:
            return hit[1]
        r = subprocess.run(["curl", "-sS", "-L", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "20", "-A", "Mozilla/5.0", page],
                           capture_output=True, text=True)
        code = r.stdout.strip() or "no answer"
        _ASKED[page] = (time.time(), code)
        return code


BY_HAND = "by-hand"   # design/check.py: a page the store kept the check out of (429); a person opens it and confirms


def page_of(url):
    """design/check.py's page_of: the page a link opens, tracking tags dropped."""
    p = urlparse(url)
    return "%s://%s%s" % (p.scheme, p.netloc.lower(), p.path.rstrip("/") or "/")


def hand_pages(c):
    """Every page the final check sent to a person, confirmed or not."""
    return list(dict.fromkeys(x["detail"].split(" → ")[0] for x in c.get("final_check", []) if x["result"] == BY_HAND))


def by_hand(c):
    """The by-hand pages still waiting for a person to open them and confirm."""
    done = set((c.get("links_confirmed") or {}).get("pages") or [])
    return [p for p in hand_pages(c) if p not in done]


def check(c):
    """Problems that hold the Approve button."""
    probs = []
    segs, missing = audience(c)
    if missing:
        probs.append("no Klaviyo id for %s in the audience matrix" % ", ".join(missing))
    for u in c.get("links", []):
        code = c.get("_link_status", {}).get(u) or link_status(u)
        c.setdefault("_link_status", {})[u] = code
        if code in ("429", "403") and page_of(u) in hand_pages(c):   # the store keeps machines out; a person confirms it below
            continue
        if code != "200":
            probs.append("link %s answers %s" % (u, code))
    for x in c.get("product_check", []):
        if x["result"] != "ok":
            probs.append("product check: " + x["detail"])
    if not c.get("final_check"):
        probs.append("no final check on file (run final_check.py)")
    for x in c.get("final_check", []):
        if x["result"] not in ("ok", BY_HAND, "note"):
            probs.append("final check: " + x["detail"])
    if by_hand(c):
        probs.append("open and confirm by hand first: " + ", ".join(by_hand(c)))
    if not (c.get("subjects") or [{}])[0].get("subject"):
        probs.append("no subject line")
    return probs


def approve(brand, label, who):
    d = card_dir(brand, label)
    c = json.loads((d / "card.json").read_text())
    if c.get("klaviyo"):
        return {"ok": False, "error": "already in Klaviyo as draft %s" % c["klaviyo"]["campaign_id"]}
    c["_dir"] = str(d)
    probs = check(c)
    if probs:
        return {"ok": False, "error": "held: " + "; ".join(probs)}
    lk = S.look(brand)
    doc = (d / "email.html").read_text()
    pics = sorted(set(re.findall(r'src="(assets/[^"]+)"', doc)))
    fp, fp_why = None, None
    if FAKE:
        hosted = {p: "https://fake.klaviyo.test/%s/%s" % (label, p) for p in pics}
        rec = {"campaign_id": "FAKE-%s" % label, "template_id": "FAKE", "status": "DRAFT (fake: nothing reached Klaviyo)"}
    else:
        # the team's pictures, not this Mac's: they are media, outside git, so a pulled email.html can sit beside an
        # older build's pictures (brand-b-nov-01 on 2026-10-27, the team's redesign beside 21 October's pictures)
        got = _layout_file().pull_build(brand, d.parent)
        if got["error"] or got["missing"]:
            return _refused(["the pictures could not be checked against the team's Drive (%s); nothing went to Klaviyo"
                             % (got["error"] or "not on the Drive: " + ", ".join(got["missing"]))])
        key = S.kl_key(lk)
        hosted = {}
        for p in pics:
            hosted[p] = S.upload(key, str(d / p), "%s-%s-%s" % (brand, label, Path(p).stem))
        for p, url in hosted.items():
            doc = doc.replace('src="%s"' % p, 'src="%s"' % url)
        (d / "email-hosted.html").write_text(doc)
        iso = _iso(c)
        cal = S.the_slot(brand, label) or {}     # the calendar's send: an offer send names its product as the offer
        cal_product = next((v for v in (cal.get("product"), cal.get("offer"))
                            if str(v or "").lower() not in ("", "none", "null")), "")
        slot = {"date": iso, "product": c.get("product") or cal_product or ("flex" if "flex" in " ".join(c.get("links", [])) else "war" if "/war" in " ".join(c.get("links", [])) else ""),
                "segments": c["segments"]}
        segs, _ = audience(c)
        future = datetime.datetime.fromisoformat("%sT%s" % (iso, c.get("send_local", "13:00"))) > datetime.datetime.now()
        strategy = S.send_strategy(lk, slot) if future else None
        rec = S.create_draft(key, doc, {"subjects": c["subjects"], "from_label": c.get("from_label")}, lk, brand, label, slot,
                             [n for n, _ in segs], [i for _, i in segs], 0, strategy)
        # what Klaviyo now holds, fingerprinted: Schedule refuses a draft changed since (LD-74 (one guarded schedule))
        try:
            dr = K.klaviyo_draft(key, rec["campaign_id"])
            fp = K.fingerprint(dr["subject"], dr["preview"], dr["html"], dr["audience_ids"], dr["strategy"])
        except K.Held as e:
            fp_why = "; ".join(e.args[0])
        except SystemExit as e:
            fp_why = str(e.code)
        except Exception as e:  # the draft exists: a failed read-back never fails the approve
            fp_why = "%s: %s" % (type(e).__name__, e)
    c.pop("_dir", None); c.pop("_link_status", None)
    c["klaviyo"] = dict(rec, hosted=hosted)
    if fp:
        c["klaviyo"]["fingerprint"] = fp
    c["approval"] = {"by": who, "at": now()}
    c["status"] = "approved"
    (d / "card.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    out = {"ok": True, "campaign_id": rec["campaign_id"]}
    if fp_why:
        out["fingerprint"] = "not read: " + fp_why
    return out


def confirm_links(brand, label, who):
    """An approver opened every by-hand page and says it works: Approve and Schedule stop waiting on it
    (the team, 2026-10-27: the store answers 429 to the check, so a person confirms instead)."""
    d = card_dir(brand, label)
    c = json.loads((d / "card.json").read_text())
    try:
        by = K.who(who)
    except K.Held as e:
        return _refused(e.args[0])
    pages = by_hand(c)
    if not pages:
        return {"ok": False, "error": "nothing waits to be confirmed by hand"}
    done = (c.get("links_confirmed") or {}).get("pages") or []
    c["links_confirmed"] = {"by": by, "at": now(), "pages": done + pages}
    (d / "card.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    return {"ok": True, "confirmed": pages}


def _refused(problems):
    return {"ok": False, "error": "; ".join(problems)}


def schedule(brand, label, who, env=None, home=None, at=None):
    """A person's click on the page releases the draft: Klaviyo schedules it on the send time already set
    (each recipient's own time zone). The refusals are klaviyo_upload.schedule_card's, in its order
    (LD-74 (one guarded schedule)); every one comes before any Klaviyo write. Trial mode runs the
    checks that need no network and reaches nothing."""
    env = os.environ if env is None else env
    home = Path.home() if home is None else Path(home)
    at = at or K.utc_now()
    d = card_dir(brand, label)
    c = json.loads((d / "card.json").read_text())
    k = c.get("klaviyo") or {}
    if not k.get("campaign_id"):
        return {"ok": False, "error": "not in Klaviyo yet: approve it first"}
    if c.get("scheduled"):
        return {"ok": False, "error": "already scheduled by %s at %s" % (c["scheduled"]["by"], c["scheduled"]["at"])}
    if K.switch_state() != "on":
        return _refused(["REFUSED: the email off-switch is off (tools/email-production/send-switch.json)"])
    try:
        by = K.who(who)
    except K.Held as e:
        return _refused(e.args[0])
    why = K.machine_run(env, home)
    if why:
        return _refused(["REFUSED: %s — a machine never schedules an email" % why])
    if [x for x in c.get("final_check", []) if x["result"] not in ("ok", BY_HAND, "note")]:
        return {"ok": False, "error": "held: the final check has problems"}
    if by_hand(c):
        return {"ok": False, "error": "held: open and confirm by hand first: " + ", ".join(by_hand(c))}
    cid = k["campaign_id"]
    if FAKE:
        job = {"id": "FAKE-" + cid}
    else:
        try:
            key = S.kl_key(S.look(brand))
            dr = K.klaviyo_draft(key, cid)
        except SystemExit as e:
            return _refused(["REFUSED: Klaviyo's draft %s could not be read: %s" % (cid, e.code)])
        except K.Held as e:
            return _refused(["REFUSED: " + p for p in e.args[0]])
        if (dr["status"] or "").lower() != "draft":
            return _refused(["REFUSED: Klaviyo says campaign %s is %s, not a draft" % (cid, dr["status"] or "of no status")])
        st = dr["strategy"] if isinstance(dr["strategy"], dict) else {}
        earliest = K.earliest_send(st)
        if st.get("method") != "static" or earliest is None:
            return _refused(["REFUSED: the draft's send strategy is %s — it could send now; set a fixed time "
                             "in Klaviyo" % (st.get("method") or "not set")])
        fp = K.fingerprint(dr["subject"], dr["preview"], dr["html"], dr["audience_ids"], st)
        was = k.get("fingerprint") or {}
        if not was.get("sha256"):
            # approved before the page kept a fingerprint: record Klaviyo's draft now, refuse this once
            c["klaviyo"]["fingerprint"] = fp
            (d / "card.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
            return _refused(["REFUSED: fingerprint recorded from Klaviyo's draft now — look at the draft and "
                             "press Schedule again"])
        if fp["sha256"] != was["sha256"]:
            changed = [p for p in fp["parts"] if fp["parts"][p] != (was.get("parts") or {}).get(p)]
            return _refused(["REFUSED: the email changed since it was approved: %s" % (", ".join(changed) or "fingerprint")])
        if earliest < at + K.MIN_LEAD:
            return _refused(["REFUSED: the first recipients would get it at %s — less than 30 minutes from now"
                             % K._iso(earliest)])
        job = S.kl("POST", "campaign-send-jobs", key, {"data": {"type": "campaign-send-job", "id": cid}}).get("data") or {}
    c["scheduled"] = {"by": by, "at": now(), "job": job.get("id") or cid}
    c["status"] = "scheduled"
    (d / "card.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    out = {"ok": True, "scheduled": True}
    if FAKE:
        out["trial"] = True
    return out


def send_back(brand, label, who, reasons, note):
    d = card_dir(brand, label)
    c = json.loads((d / "card.json").read_text())
    c["sent_back"] = {"by": who, "at": now(), "reasons": reasons, "note": note}
    c["status"] = "draft"
    (d / "card.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    with open(RUNS / brand / "learnings.jsonl", "a") as f:
        f.write(json.dumps({"at": now(), "by": who, "label": label, "reasons": reasons, "note": note, "channel": "klaviyo"}) + "\n")
    return {"ok": True}


def redo(brand, label, who, note, stage):
    """the team's refinement (the owner, 2026-10-17: "every time a shift is made … with the feedback, that all needs to be
    stored and put into learnings back up and through the chain"): her note becomes a rule in the brand's
    learnings (design/learn.py) that every later email reads, then THIS email is redesigned, rebuilt and checked
    with it. A words note reruns the copy from its writing step first."""
    import subprocess
    if not note.strip():
        return {"ok": False, "error": "say what should change"}
    sys.path.insert(0, str(Path(__file__).resolve().parent / "design"))
    import learn as LN
    LN.add(brand, stage if stage in ("design", "picture", "copy") else "design", "do", note.strip(),
           "%s's refinement" % who, who, label)
    run = RUNS / brand / label
    here = Path(__file__).resolve().parent
    steps = []
    if stage == "copy":
        av = run / "copy-argv.json"
        if not av.exists():
            return {"ok": False, "error": "this email was written before refinements could replay it: rerun it from the calendar"}
        steps.append([sys.executable] + json.loads(av.read_text()) + ["--rerun-from", "stage3"])
    steps += [[sys.executable, "design/line.py", brand, "--run", str(run), "--pictures"],
              [sys.executable, "design/build.py", str(run)], [sys.executable, "design/check.py", str(run)]]
    for s in steps:
        p = subprocess.run(s, cwd=here, capture_output=True, text=True)
        if p.returncode:
            return {"ok": False, "error": "redo stopped at %s: %s" % (Path(s[1]).name, (p.stderr or p.stdout)[-300:])}
    return {"ok": True, "redone": True}


KS_CACHE = {}


def page():
    cs = cards()
    for b in sorted({c["brand"] for c in cs}):
        KS_CACHE[b] = klaviyo_status(b)
    bar = "".join('<span class="%s">%s Klaviyo: %s</span>' % ("kok" if k["ok"] else "kbad", E(b.upper()),
                  E(("connected · " + (k["account"] or "")) if k["ok"] else ("not connected · " + (k["error"] or "")))) for b, k in KS_CACHE.items())
    n_ready = sum(1 for c in cs if c.get("final_check") and not [x for x in c["final_check"] if x["result"] not in ("ok", BY_HAND, "note")]
                  and not by_hand(c) and not c.get("klaviyo"))
    n_in = sum(1 for c in cs if c.get("klaviyo"))
    rows = []
    for c in cs:
        segs, missing = audience(c)
        state = ("scheduled" if c.get("scheduled") else ("in Klaviyo · draft %s" % c["klaviyo"]["campaign_id"])) if c.get("klaviyo") else ("sent back" if c.get("sent_back") else "waiting for you")
        cls = "done" if c.get("klaviyo") else ("back" if c.get("sent_back") else "wait")
        sub = (c.get("subjects") or [{}])[0]
        flags = "".join('<p class="flag">%s</p>' % E(f) for f in c.get("flags", []))
        links = "".join('<li data-u="%s"><span class="ls">…</span> %s</li>' % (E(u), E(u.split("?")[0])) for u in c.get("links", []))
        ks = KS_CACHE.get(c["brand"]) or {}
        seg = ", ".join("%s <small>%s%s</small>" % (E(n.replace("Core | ", "")), E(i or "NO ID"),
                        (" · {:,} people".format(ks["segments"][i]) if i in ks.get("segments", {}) and ks["segments"][i] is not None else "")) for n, i in segs)
        seg_plain = ", ".join("%s%s" % (n.replace("Core | ", ""), (" ({:,} people)".format(ks["segments"][i]) if i in ks.get("segments", {}) and ks["segments"][i] is not None else "")) for n, i in segs)
        fc = c.get("final_check", [])
        fc_bad = [x for x in fc if x["result"] not in ("ok", BY_HAND, "note")]
        waiting = by_hand(c)
        ready = bool(fc) and not fc_bad and not waiting and not c.get("klaviyo")
        fcl = "".join('<li><span class="ls %s">%s</span> %s</li>' % ({"ok": ("ok", "ok"), BY_HAND: ("hand", "BY HAND")}.get(x["result"], ("bad", "PROBLEM")) + (E(x["detail"]),)) for x in fc)
        badge = ('<span class="ready">Ready for Klaviyo</span>' if ready else ('<span class="held">Held: %d problem%s</span>' % (len(fc_bad), "" if len(fc_bad) == 1 else "s") if fc_bad else
                 ('<span class="held">Open %d link%s first</span>' % (len(waiting), "" if len(waiting) == 1 else "s") if waiting and not c.get("klaviyo") else
                  ('<span class="held">No final check yet</span>' if not fc else ""))))
        lc = c.get("links_confirmed") or {}
        hand = ('<div class="hand"><h4>Open these and check they work</h4><p class="k">The store keeps the automatic check out (429), so a person looks instead.</p><ul>%s</ul>'
                '<button class="go" data-a="confirm">I opened them: they work</button></div>' % "".join(
                    '<li><a href="%s" target="_blank" rel="noopener">%s</a></li>' % (E(p), E(p)) for p in waiting)) if waiting and not c.get("klaviyo") else (
                '<p class="k">Opened by hand and confirmed by %s · %s</p>' % (E(lc["by"]), E(lc["at"][:16].replace("T", " "))) if lc and not waiting else "")
        notes = "".join("<li>%s</li>" % E(n) for n in c.get("notes", []))
        pc = "".join('<li><span class="ls %s">%s</span> %s</li>' % ("ok" if x["result"] == "ok" else "bad", "ok" if x["result"] == "ok" else "PROBLEM", E(x["detail"])) for x in c.get("product_check", []))
        v = int(Path(c["_dir"], "email.html").stat().st_mtime) if Path(c["_dir"], "email.html").exists() else 0
        src = "/email/%s/%s/email.html?v=%d" % (c["brand"], c["label"], v)
        sched = ""
        if c.get("klaviyo") and not c.get("scheduled"):
            sched = ('<div class="acts"><button class="go sch" data-a="schedule" data-n="%s">Schedule in Klaviyo</button></div>' % E(seg_plain))
        elif c.get("scheduled"):
            sched = '<p class="ready" style="margin-top:12px">Scheduled by %s · %s</p>' % (E(c["scheduled"]["by"]), E(c["scheduled"]["at"][:16].replace("T", " ")))
        acts = sched if c.get("klaviyo") else (
            '<div class="acts"><button class="go" data-a="approve">Approve → Klaviyo draft</button>'
            '<details><summary>Send back</summary><div class="why">%s</div><textarea placeholder="What should change?"></textarea>'
            '<button class="back" data-a="sendback">Send back</button></details>'
            '<details><summary>Redo with a note</summary><textarea class="redo" placeholder="What should change? It becomes a rule for every email after this one."></textarea>'
            '<label><input type="radio" name="st-%s" value="design" checked> design</label> <label><input type="radio" name="st-%s" value="picture"> pictures</label> '
            '<label><input type="radio" name="st-%s" value="copy"> words</label>'
            '<button class="go" data-a="redo">Redo this email</button></details></div>') % ("".join(
            '<label><input type="checkbox" value="%s"> %s</label>' % (E(r), E(r)) for r in REASONS), E(c["label"]), E(c["label"]), E(c["label"]))
        rows.append('''<article class="card %s" data-brand="%s" data-label="%s">
<div class="frame"><iframe loading="lazy" src="%s" title="%s"></iframe></div>
<div class="side"><div class="top"><b>%s %s</b><span class="st">%s</span></div>
<div class="k">%s · %s</div>%s
<div class="subj"><b>%s</b><small>%s</small></div>
<dl>%s<dt>Goes to</dt><dd>%s</dd><dt>Sends</dt><dd>%s %s at %s, each person's own time zone</dd><dt>In it</dt><dd>%d pictures · %d GIFs</dd></dl>
%s<h4>Final check</h4><ul>%s</ul>%s<h4>Product check</h4><ul>%s</ul><h4>Links</h4><ul class="links">%s</ul><h4>What changed</h4><ul class="notes">%s</ul>%s
<p class="msg"></p></div></article>''' % (cls, E(c["brand"]), E(c["label"]), src, E(sub.get("subject", "")),
                                         E(c.get("day", "")), E(c.get("date", "")), E(state), E(c.get("kind", "")), E(c.get("audience", "")), badge,
                                         E(sub.get("subject", "")), E(sub.get("preview", "")),
                                         '<dt>From</dt><dd>%s</dd>' % E(c["from_label"]) if c.get("from_label") else "",
                                         seg, E(c.get("day", "")), E(c.get("date", "")),
                                         E(c.get("send_local", "")), c.get("pictures", 0), len(c.get("gifs", [])), flags, fcl, hand, pc, links, notes, acts))
    return PAGE.replace("{{CARDS}}", "".join(rows) or "<p>No emails waiting.</p>").replace("{{N}}", str(len(cs))).replace("{{BAR}}", bar + '<span class="kok">%d ready · %d in Klaviyo</span>' % (n_ready, n_in)).replace("{{FAKE}}", "trial mode: nothing reaches Klaviyo" if FAKE else "")


PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Klaviyo Approvals</title><style>
:root{--bg:#0b0d0c;--card:#141716;--ink:#eef1ea;--mut:#9aa096;--line:#262a27;--sage:#c7cfad;--warn:#e7c27a;--ok:#9fd39a;--bad:#e58a7a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Helvetica,Arial,sans-serif}
header{padding:22px 20px;border-bottom:1px solid var(--line);display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}
h1{margin:0;font:400 26px Georgia,serif}header span{color:var(--mut)}#who{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:6px 10px}
.fake{color:var(--warn)}main{padding:20px;display:grid;gap:22px}
.card{display:grid;grid-template-columns:minmax(0,620px) minmax(0,1fr);gap:20px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}
.card.done{border-color:rgba(159,211,154,.4)}.frame{height:760px;border-radius:10px;overflow:hidden;background:#0c100f}iframe{width:100%;height:100%;border:0}
.top{display:flex;justify-content:space-between;gap:8px}.top b{font:400 22px Georgia,serif}.st{font-size:12px;border:1px solid var(--line);border-radius:99px;padding:2px 10px;color:var(--mut)}
.done .st{color:var(--ok)}.back .st{color:var(--bad)}.k{color:var(--mut);margin:2px 0 10px}
.subj{background:#0f1211;border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:10px}.subj b{display:block}.subj small{color:var(--mut)}
dl{display:grid;grid-template-columns:90px 1fr;gap:4px 10px;margin:0 0 10px}dt{color:var(--mut)}dd{margin:0}dd small{color:var(--mut)}
.flag{background:rgba(231,194,122,.1);border:1px solid rgba(231,194,122,.4);color:var(--warn);border-radius:8px;padding:8px 10px;margin:8px 0}
h4{margin:12px 0 4px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--mut)}ul{margin:0;padding-left:16px}.links li{word-break:break-all}
.ls{font-size:11px;font-weight:600}.ls.ok{color:var(--ok)}.ls.bad{color:var(--bad)}.ls.hand{color:var(--mut)}.hand{margin-top:10px}.notes{color:var(--mut)}
.acts{margin-top:14px;display:grid;gap:10px}button{font:600 14px Helvetica,Arial;border-radius:99px;padding:12px 18px;border:0;cursor:pointer}
.go{background:var(--sage);color:#0c100f}.back{background:transparent;color:var(--bad);border:1px solid var(--bad)}button:disabled{opacity:.5;cursor:wait}
details summary{cursor:pointer;color:var(--mut)}.why{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin:8px 0}textarea{width:100%;min-height:60px;background:#0f1211;color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px}
.msg{min-height:1em}.bar{display:flex;gap:8px;flex-wrap:wrap;width:100%}.bar span{font-size:12px;border-radius:99px;padding:3px 10px;border:1px solid var(--line)}.kok{color:var(--ok)}.kbad{color:var(--bad)}
.ready,.held{display:inline-block;margin:0 0 10px;font-size:12px;font-weight:600;border-radius:99px;padding:3px 10px}.ready{color:#0c100f;background:var(--ok)}.held{color:var(--bad);border:1px solid var(--bad)}@media(max-width:900px){.card{grid-template-columns:1fr}.frame{height:620px}}
</style></head><body>
<header><h1>Klaviyo approvals</h1><span>{{N}} emails · Approve makes a DRAFT in Klaviyo with its segments, subject and send time set. Schedule (two clicks) releases it; nothing goes out without that click.</span>
<span class="fake">{{FAKE}}</span><div class="bar">{{BAR}}</div><label>Deciding: <select id="who"><option>the owner</option><option>the team</option><option>the team</option><option>the team</option></select></label></header>
<main>{{CARDS}}</main>
<script>
const who=document.getElementById('who');try{who.value=localStorage.getItem('who')||'the owner'}catch(e){}
who.onchange=()=>{try{localStorage.setItem('who',who.value)}catch(e){}};
document.querySelectorAll('.links li').forEach(li=>{fetch('/link?u='+encodeURIComponent(li.dataset.u)).then(r=>r.json()).then(j=>{const s=li.querySelector('.ls');s.textContent=j.code;s.className='ls '+(j.code==='200'?'ok':(j.code==='429'||j.code==='403')?'hand':'bad');if(j.code==='429'||j.code==='403')s.textContent=j.code+' · open it'})});
const all=document.getElementById('all');if(all)all.onclick=async()=>{const m=document.getElementById('allmsg');
 if(!all.dataset.sure){all.dataset.sure='1';all.textContent='Confirm: schedule all '+all.dataset.n+' now';m.textContent='Click again to schedule every approved draft. Each sends at the time on its card.';return}
 all.disabled=true;m.textContent='Scheduling…';let ok=0,bad=[];
 for(const c of document.querySelectorAll('.card[data-sched="1"]')){const r=await fetch('/schedule',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({brand:c.dataset.brand,label:c.dataset.label,who:who.value})}).then(r=>r.json()).catch(e=>({ok:false,error:String(e)}));if(r.ok)ok++;else bad.push(c.dataset.label+': '+r.error)}
 m.textContent=ok+' scheduled.'+(bad.length?' Not scheduled: '+bad.join('; '):'');setTimeout(()=>location.reload(),2500)};
document.querySelectorAll('.card button').forEach(b=>b.onclick=async()=>{const c=b.closest('.card'),m=c.querySelector('.msg');
 if(b.dataset.a==='schedule'&&!b.dataset.sure){b.dataset.sure='1';b.textContent='Confirm: schedule to '+b.dataset.n;m.textContent='Click again to schedule. It sends at the time on this card.';return}
 b.disabled=true;m.textContent='Working…';
 const body={brand:c.dataset.brand,label:c.dataset.label,who:who.value};
 if(b.dataset.a==='redo'){body.note=c.querySelector('textarea.redo').value;const s=c.querySelector('input[name="st-'+c.dataset.label+'"]:checked');body.stage=s?s.value:'design';if(!body.note.trim()){m.textContent='Say what should change.';b.disabled=false;return}m.textContent='Redoing: the note is now a rule; redesigning this email (a few minutes)…'}
 if(b.dataset.a==='sendback'){body.reasons=[...c.querySelectorAll('.why input:checked')].map(i=>i.value);body.note=c.querySelector('textarea').value;if(!body.reasons.length){m.textContent='Pick at least one reason.';b.disabled=false;return}}
 const r=await fetch('/'+b.dataset.a,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(r=>r.json()).catch(e=>({ok:false,error:String(e)}));
 m.textContent=r.ok?(r.confirmed?'Confirmed. Approve no longer waits on these links.':r.redone?'Redone with your note. It is now a rule for every email after this one.':r.scheduled?'Scheduled in Klaviyo.':(r.campaign_id?'In Klaviyo as draft '+r.campaign_id+'. Schedule it from this card.':'Sent back.')):r.error;b.disabled=false;if(r.ok)setTimeout(()=>location.reload(),1500)});
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store, max-age=0"); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            return self._send(200, page())
        if u.path == "/link":
            url = parse_qs(u.query).get("u", [""])[0]
            return self._send(200, json.dumps({"code": link_status(url) if url.startswith("http") else "skip"}), "application/json")
        m = re.match(r"^/email/([a-z0-9-]+)/([a-z0-9-]+)/(.+)$", unquote(u.path))  # query (?v=) ignored: it only busts caches
        if m:
            try:
                d = card_dir(m.group(1), m.group(2))
            except KeyError:
                return self._send(404, "no such email")
            f = (d / m.group(3)).resolve()
            if d.resolve() not in f.parents or not f.is_file():
                return self._send(404, "not found")
            return self._send(200, f.read_bytes(), mimetypes.guess_type(str(f))[0] or "application/octet-stream")
        self._send(404, "not found")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            j = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, json.dumps({"ok": False, "error": "bad request"}), "application/json")
        with LOCK:
            try:
                if self.path == "/approve":
                    r = approve(j["brand"], j["label"], j.get("who") or "the owner")
                elif self.path == "/schedule":
                    r = schedule(j["brand"], j["label"], j.get("who"))   # checked against approvers.json, no default
                elif self.path == "/redo":
                    r = redo(j["brand"], j["label"], j.get("who") or "graphic-designer",j.get("note") or "", j.get("stage") or "design")
                elif self.path == "/confirm":
                    r = confirm_links(j["brand"], j["label"], j.get("who"))   # checked against approvers.json, no default
                elif self.path == "/sendback":
                    r = send_back(j["brand"], j["label"], j.get("who") or "the owner", j.get("reasons") or [], j.get("note") or "")
                else:
                    r = {"ok": False, "error": "unknown action"}
            except SystemExit as e:
                r = {"ok": False, "error": str(e)}
            except Exception as e:  # shown on the card, never swallowed
                r = {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
        self._send(200, json.dumps(r), "application/json")

    def log_message(self, *a):
        pass


def main():
    global FAKE
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8798)
    ap.add_argument("--fake-klaviyo", action="store_true")
    a = ap.parse_args()
    FAKE = a.fake_klaviyo
    print("Klaviyo approvals on http://localhost:%d%s" % (a.port, " (trial mode)" if FAKE else ""), flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
