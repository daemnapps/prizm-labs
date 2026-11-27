#!/usr/bin/env python3
"""An SMS from its written text to a person's go, behind the email approval page's own gate (2026-11-04).

    python3 sms_launch.py card  <runs/email-production/<brand>/<brand>-<slot>-sms>   # the approval card
    python3 sms_launch.py dry   <same folder>                                       # what launch would do

THE CARD (sms-card.json beside sms.json) is made from the written text and the plan: the text with the link
filled from the EMAIL IT FOLLOWS (an SMS is a companion, never a campaign of its own: an SMS whose email is
not written has no card), the audience (the slot's segments, SMS-consented members only), the send time (the
plan's day at the cadence's hour, in each recipient's own time zone), the platform (brands/<brand>/operations/
brand.json `sms_platform`) and a fingerprint of all of it. Making a card talks to no platform.

LAUNCH is approve() alone, reached from Approve on the email approval page (email_approve.py), which runs the
same refusals as an email: a waiting card, the off-switch on, a name on approvers.json, not the mini and not a
worker job, the text's checks passing again, nothing changed since the card was made, the first recipient at
least 30 minutes away. Then, by platform:
- klaviyo: the draft SMS campaign is created and scheduled (campaign-send-jobs) — scheduled, never sent now;
- postscript: its public API has no campaign endpoint, so the go writes postscript-handoff.md — the text, the
  audience, the time — and the person places it in Postscript. Nothing is created there by a machine.
dry() runs every check that needs no network and prints the platform calls it would make; it calls nothing.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import importlib.util

import klaviyo_upload as K          # the gate: Held, switch_state, who, machine_run, MIN_LEAD, utc_now
from paths import WORKSPACE


def email_state(v):
    """Where the email it follows stands: "scheduled" when the designed email's card (klaviyo/card.json, written
    by approve_klaviyo's guarded schedule) says so, else the copy-line draft card's state (deliverable/
    email-card.json), else None. brand_b-nov-08a (2026-11-06) was scheduled through the designed path, and the
    text was held because only the copy-line card was read."""
    try:
        if (json.loads((v / "klaviyo" / "card.json").read_text()).get("status") or "") == "scheduled":
            return "scheduled"
    except (OSError, ValueError):
        pass
    try:
        return json.loads((v / "deliverable" / K.CARD).read_text()).get("state")
    except (OSError, ValueError):
        return None


def designed_link(email):
    """The button link of the email as designed and approved (design/email.json `link`), which a person may have
    changed after the copy was written; None when the email has no design. brand_a-nov-10 glow-up (2026-11-06):
    its button was moved to the quiz before the Go, and the text still pointed at the copy's FLEX page."""
    try:
        return (json.loads((email / "design" / "email.json").read_text()).get("link") or "").strip() or None
    except (OSError, ValueError):
        return None


def _by_path(name):
    """klaviyo_upload takes this folder off sys.path (simple_email.py:44-47), so siblings load by path."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, K.HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    here = str(K.HERE)
    sys.path.append(here)           # at the END while it loads its own siblings, so the stdlib `email` still wins
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(here)
    return mod


SMS = _by_path("sms")

CARD = "sms-card.json"
HANDOFF = "postscript-handoff.md"


def _rec(run):
    return json.loads((Path(run) / "sms.json").read_text())


def plan_slot(brand, rec):
    """The SMS slot this text was written for, from the month it names (its date's month)."""
    m = WORKSPACE / "runs" / "marketing-calendar" / brand / (rec.get("date") or "")[:7] / "slots.json"
    if m.is_file():
        for s in json.loads(m.read_text()):
            if s["id"] == rec.get("slot") and s.get("channel") == "sms":
                return s
    return None


def platform(brand):
    f = WORKSPACE / "brands" / brand / "operations" / "brand.json"
    return (json.loads(f.read_text()).get("sms_platform") if f.is_file() else None)


def fingerprint(card):
    parts = {k: json.dumps(card.get(k), sort_keys=True) for k in ("text", "link", "segments", "send_at", "platform")}
    return {"sha256": hashlib.sha256("|".join(parts[k] for k in sorted(parts)).encode()).hexdigest(), "parts": parts}


def make_card(run, write=True):
    """-> (card, problems). The card is written only when nothing is wrong, and only when `write`."""
    run = Path(run)
    rec = _rec(run)
    brand = rec["brand"]
    probs = []
    if rec.get("state") != "ready for review":
        probs.append(f"the text is not ready: {rec.get('state')}")
    slot = plan_slot(brand, rec)
    if not slot:
        probs.append(f"no SMS slot {rec.get('slot')} in the {(rec.get('date') or '')[:7]} plan")
    # the link comes from the version of the email that carries the text's own offer (an email can have one
    # version per avatar, and a version whose lane the offer is not its own carries none), else the first
    versions = SMS.email_runs(brand, (slot or {}).get("follows"))
    def _offer_of(v):
        try:
            return ((json.loads((v / "run.json").read_text()).get("assignment") or {}).get("offer"))
        except (OSError, ValueError):
            return None
    email = next((v for v in versions if _offer_of(v) == rec.get("offer")), versions[0] if versions else None)
    if not email:
        probs.append(f"the email it follows ({(slot or {}).get('follows') or 'none named'}) is not written — "
                     "an SMS is a companion and launches only with its email")
    link = None
    if email:
        link = designed_link(email) or (json.loads((email / "deliverable" / "email.json").read_text()).get("button") or {}).get("link")
        if not link:
            probs.append("the email it follows has no button link to point the text at")
    plat = platform(brand)
    if not plat:
        probs.append("the brand names no sms_platform (operations/brand.json)")
    hour = int((slot or {}).get("hour", 12))
    send_at = f"{rec.get('date')}T{hour:02d}:00:00"
    sec = SMS.offer_section(brand, rec.get("offer") or "")
    probs += SMS.check(rec.get("text") or "", sec, SMS.cadence(), slot)
    card = {"kind": "sms", "brand": brand, "label": run.name, "slot": rec.get("slot"), "follows": (slot or {}).get("follows"),
            "email_run": str(email.relative_to(WORKSPACE)) if email else None, "platform": plat,
            "text": rec.get("text"), "link": link, "sent_text": (rec.get("text") or "").replace("{link}", link or "{link}"),
            "segments": (slot or {}).get("segments"), "audience_rule": (slot or {}).get("audience_rule"),
            "send_at": send_at, "send_at_is": "local time of each recipient", "job": rec.get("job"),
            "offer": rec.get("offer"), "state": "waiting", "made": K.now()}
    card["fingerprint"] = fingerprint(card)
    if write and not probs:
        (run / CARD).write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    return card, probs


def read_card(run):
    f = Path(run) / CARD
    return json.loads(f.read_text()) if f.is_file() else None


def klaviyo_calls(card):
    """The two Klaviyo calls approve() makes for a Klaviyo SMS: the draft campaign, then its schedule."""
    import simple_email as S
    _names, ids, missing = S.audience(card["brand"], {"segments": card["segments"], "segment": card["segments"][0]})
    body = {"data": {"type": "campaign", "attributes": {
        "name": f"{card['label']} · {card['send_at'][:10]}",
        "audiences": {"included": ids, "excluded": []},
        "send_strategy": {"method": "static", "datetime": card["send_at"] + "+00:00",
                          "options": {"is_local": True, "send_past_recipients_immediately": False}},
        "campaign-messages": {"data": [{"type": "campaign-message", "attributes": {"definition": {
            "channel": "sms", "content": {"body": without_brand_prefix(card)},
            "render_options": {"shorten_links": True, "add_org_prefix": True, "add_info_link": False,
                               "add_opt_out_language": False}}}}]}}}}
    return {"create": ("POST", "campaigns", body), "schedule": ("POST", "campaign-send-jobs", "<the new campaign id>"),
            "missing_segment_ids": missing}


def without_brand_prefix(card):
    """Klaviyo puts the brand's name in front of every text (add_org_prefix), so a text that already opens with
    it would carry it twice: the leading name is dropped from the body Klaviyo gets."""
    import re
    f = WORKSPACE / "brands" / card["brand"] / "operations" / "brand.json"
    label = (json.loads(f.read_text()).get("label") if f.is_file() else None) or card["brand"]
    return re.sub(rf"^\s*{re.escape(label)}\s*[:\-—]\s*", "", card["sent_text"], flags=re.I)


def handoff_text(card):
    return (f"# SMS to place in Postscript — {card['label']}\n\nApproved for scheduling; Postscript's public API "
            "has no campaign endpoint, so a person places it.\n\n"
            f"- Send: {card['send_at'][:10]} at {card['send_at'][11:16]}, each recipient's local time\n"
            f"- To: {', '.join(card['segments'] or [])} — {card.get('audience_rule')}\n"
            f"- Follows the email: {card.get('follows')}\n\n> {card['sent_text']}\n")


def approve(run, by, env=None, home=None, at=None, client=None):
    """Approve → Schedule for an SMS card. Every refusal raises K.Held before any platform call."""
    import os
    env = os.environ if env is None else env
    home = Path.home() if home is None else Path(home)
    at = at or K.utc_now()
    run = Path(run)
    card = read_card(run)
    if not card:
        raise K.Held(["REFUSED: no SMS card here — make it with sms_launch.py card"])
    if card.get("state") != "waiting":
        raise K.Held([f"REFUSED: this card is {card.get('state')} — only a waiting card is approved"])
    if K.switch_state() != "on":
        raise K.Held(["REFUSED: the off-switch is off (components/email-production/send-switch.json)"])
    by = K.who(by)
    why = K.machine_run(env, home)
    if why:
        raise K.Held([f"REFUSED: {why} — a machine never schedules a send"])
    shut = K.S.pages_hidden(card["brand"], [card.get("offer")])
    if shut:
        raise K.Held(["REFUSED: its store page is not open yet — " + "; ".join(f"{k}: {v}" for k, v in shut.items())])
    versions = SMS.email_runs(card["brand"], card.get("follows")) or [WORKSPACE / (card.get("email_run") or "-")]
    for v in versions:                       # every version of the email (one per avatar) is approved first
        estate = email_state(v)
        if estate not in ("approved", "scheduled"):
            raise K.Held([f"REFUSED: the email it follows ({v.name}) is {estate or 'not on the approval page yet'} "
                          "— an SMS goes only with its email, so approve the email first"])
    fresh, probs = make_card_view(run)
    if probs:
        raise K.Held(["REFUSED: a check is failing — " + p for p in probs])
    if fresh["fingerprint"]["sha256"] != card["fingerprint"]["sha256"]:
        raise K.Held(["REFUSED: the text, link, audience or time changed since the card was made — re-card it"])
    first = datetime.fromisoformat(card["send_at"]).replace(tzinfo=timezone.utc) - timedelta(hours=14)  # earliest zone
    if first < at + K.MIN_LEAD:
        raise K.Held([f"REFUSED: the first recipients would get it at {first.isoformat()} — under 30 minutes away"])
    card["approval"] = {"by": by, "at": K._iso(at), "fingerprint": card["fingerprint"]["sha256"]}
    if card["platform"] == "postscript":
        (run / HANDOFF).write_text(handoff_text(card))
        card["state"] = "approved — place in Postscript"
    elif card["platform"] == "klaviyo":
        calls = klaviyo_calls(card)
        if calls["missing_segment_ids"]:
            raise K.Held([f"REFUSED: no Klaviyo id for {calls['missing_segment_ids']} in the audience matrix"])
        kl = client or _klaviyo(card["brand"])
        made = kl(*calls["create"])
        cid = made["data"]["id"]
        kl("POST", "campaign-send-jobs", {"data": {"type": "campaign-send-job", "id": cid}})
        card.update(state="scheduled", campaign_id=cid)
    else:
        raise K.Held([f"REFUSED: no launch for platform {card['platform']!r}"])
    (run / CARD).write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    return card


def make_card_view(run):
    """The card as it would be made now, written nowhere — what approve() compares against."""
    return make_card(run, write=False)


def _klaviyo(brand):
    import simple_email as S
    key = S.kl_key(S.look(brand))           # the brand's own key, checked against its account (right_account)
    return lambda method, path, body: S.kl(method, path, key, body)


def dry(run):
    card, probs = make_card_view(run)
    out = {"label": card["label"], "platform": card["platform"], "sent_text": card["sent_text"],
           "characters": len(card["sent_text"]), "send_at": card["send_at"], "segments": card["segments"],
           "problems": probs}
    if card["platform"] == "klaviyo" and not probs:
        c = klaviyo_calls(card)
        out["would_call"] = [c["create"][:2], c["schedule"][:2]]
        out["missing_segment_ids"] = c["missing_segment_ids"]
    elif card["platform"] == "postscript":
        out["would_write"] = HANDOFF + " (a person places it in Postscript)"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="An SMS card, and what its launch would do. Never schedules here.")
    ap.add_argument("step", choices=("card", "dry"))
    ap.add_argument("run")
    a = ap.parse_args(argv)
    if a.step == "card":
        card, probs = make_card(a.run)
        print(json.dumps({"label": card["label"], "state": "card written" if not probs else "no card",
                          "problems": probs}, indent=1, ensure_ascii=False))
        return 1 if probs else 0
    print(json.dumps(dry(a.run), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
