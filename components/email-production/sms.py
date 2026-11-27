#!/usr/bin/env python3
"""The words for a month's SMS — one text per calendar slot marked `channel: sms` (2026-11-03).

    python3 sms.py ../../runs/marketing-calendar/<brand>/<YYYY-MM> [--only nov-21,nov-37] [--dry-run]

The calendar plans SMS (marketing-calendar definitions/sms-cadence.json); this writes them, the same way for
every brand, moment and offer. The prompt is prompts/sms-v<N>-*.md (highest wins), filled from the slot, the
offer's own section of the bank (read through offers.parse, the reader the calendar shares) and the brand's
sender identity. Every text is then checked in code: its length with the link and the opt-out counted, the
opt-out present, the link written once as {link}, every price one the offer section states, and no code when
the section says there is none. A text that fails is kept with the reasons, `state: held`.

Writes runs/email-production/<brand>/<brand>-<slot id>-sms/ (sms.json, sms.md, prompt-sent.md). Never sends,
never schedules, never touches Klaviyo or any SMS platform: a person approves and sends.
--dry-run fills every prompt and reports, spending nothing and writing nothing.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from paths import HERE, WORKSPACE, calendar_tool
import offers as OFFERS

PROMPTS = HERE / "prompts"


def cadence():
    cal = calendar_tool()
    f = (cal / "definitions" / "sms-cadence.json") if cal else None
    return json.loads(f.read_text()) if f and f.is_file() else {}


def latest_prompt():
    best, v = None, -1
    for f in PROMPTS.glob("sms-v*-*.md"):
        m = re.match(r"sms-v(\d+)-", f.name)
        if m and int(m.group(1)) > v:
            best, v = f, int(m.group(1))
    return best


def offer_section(brand, key):
    """The offer's own section of the bank, as written: a `## key — …` block or a ruled `### key — …` one."""
    text = (WORKSPACE / "brands" / brand / "products" / "offer-bank.md").read_text()
    m = re.search(rf"^(#{{2,3}})\s+{re.escape(key)}\b.*?(?=^#{{1,3}}\s|\Z)", text, re.M | re.S)
    keep_off = re.compile(r"never in an email|funnel only|never (in|on) (an? )?(email|sms|text)", re.I)
    return "\n".join(ln for ln in m.group(0).strip().splitlines() if not keep_off.search(ln)) if m else ""


def prices_in(text):
    return {p.rstrip("0").rstrip(".") if "." in p else p
            for p in re.findall(r"\$([0-9]+(?:\.[0-9]{1,2})?)", text)}


def check(msg, section, cad, slot=None):
    """The rules, in code. -> [problems]; empty when the text stands."""
    ln = cad.get("length") or {}
    mx, link_n = int(ln.get("max_chars", 160)), int(ln.get("link_chars", 25))
    opt = ln.get("opt_out", "Reply STOP to opt out")
    out = []
    n = len(msg.replace("{link}", "x" * link_n))
    if n > mx:
        out.append(f"{n} characters with the link counted as {link_n} — the limit is {mx}")
    if msg.count("{link}") != 1:
        out.append(f"the link must appear once as {{link}} (found {msg.count('{link}')})")
    if re.search(r"https?://|www\.", msg):
        out.append("a real URL is written in — only {link} may stand for it")
    if opt.lower() not in msg.lower():
        out.append(f"no opt-out line (“{opt}”)")
    stray = prices_in(msg) - prices_in(section)
    if stray:
        out.append("prices the offer section does not state: " + ", ".join(f"${p}" for p in sorted(stray)))
    if re.search(r"\bno code\b", section, re.I) and re.search(r"\bcode\b", re.sub(r"(?i)\bno code\b", "", msg), re.I):
        out.append("mentions a code, and the offer section says there is none")
    if re.search(r"\bno code\b", section, re.I) and re.search(
            r"\b(your|a) (discount|code|savings?)\b|\bdiscount (is )?(waiting|saved|sitting|on your account|unused)\b", msg, re.I):
        out.append("implies a discount held for the reader, and the offer section says there is no code — "
                   "the price is on the page")
    facts = slot or {}
    required_lead = facts.get("required_lead")
    if required_lead and not msg.casefold().startswith(required_lead.casefold()):
        out.append(f"does not lead with the calendar's required line: {required_lead}")
    last_day = re.search(r"\b(last day|today only|ends today|final day)\b", msg, re.I)
    if last_day:
        day, deadline, order_by = facts.get("date"), facts.get("deadline"), facts.get("order_by")
        if order_by:
            if day != order_by or not re.search(r"\b(last day|final day) to order\b", msg, re.I):
                out.append("order-by cutoff is not the sale's last day; say last day to order only on the cutoff")
        elif deadline and day != deadline:
            out.append(f"says last day on {day}, but the calendar deadline is {deadline}")
    out += OFFERS.saving_problems(msg.replace("{link}", ""), section)
    bare = re.sub(re.escape(opt), "", msg, flags=re.I)
    beat = (slot or {}).get("sms_beat")
    if slot is not None and beat != "early-access" and re.search(r"\bearly access\b", bare, re.I):
        out.append(f"says early access on the `{beat}` beat — only the early-access beat may")
    if slot is not None and beat != "last-chance" and re.search(r"\b(last day|today only|ends today|final day)\b", bare, re.I):
        out.append(f"says it is the last day on the `{beat}` beat — only the last-chance beat may")
    kw = (slot or {}).get("reply_keyword")
    if (slot or {}).get("sms_job") == "reply" and kw:
        if not re.search(rf"\b{re.escape(kw)}\b", bare):
            out.append(f"a reply ask without its keyword `{kw}`")
    elif re.search(r"\breply\b", bare, re.I):
        out.append("asks for a reply, and this text's job is not a reply ask (sms-cadence.json `jobs`)")
    return out


def email_runs(brand, slot_id):
    """Every written version of the email a slot id names: runs/email-production/<brand>/<brand>-<id>/, or one
    folder per avatar version, <brand>-<id>--<avatar>/ (run_month.py writes a version per avatar)."""
    if not slot_id:
        return []
    home = WORKSPACE / "runs" / "email-production" / brand
    out = []
    for d in sorted(home.glob(f"{brand}-*")):
        if not (d / "deliverable" / "email.json").is_file() or (d / "off-page.json").exists():
            continue
        sid = recorded_slot(d)
        if sid == slot_id or (sid is None and (d.name == f"{brand}-{slot_id}" or d.name.startswith(f"{brand}-{slot_id}--"))):
            out.append(d)
    return out


def recorded_slot(d):
    """The calendar slot a run was written for, from its own record, or None when it records none (2026-11-05:
    a run's folder name is not its slot — brand-a-nov-08a is slot nov-09, brand-b-nov-10--reader is nov-56 —
    so matching by name sent a weekly SMS to the wrong email, or found none)."""
    for f, path in (("klaviyo/card.json", ("calendar_handoff", "expected", "slot_id")),
                    ("run.json", ("calendar_handoff", "slot_id"))):
        try:
            v = json.loads((d / f).read_text())
            for k in path:
                v = v.get(k) if isinstance(v, dict) else None
            if isinstance(v, str) and v:
                return v
        except (OSError, ValueError):
            continue
    return None


def email_run(brand, slot_id):
    """The first written version of the email a slot id names, or None."""
    got = email_runs(brand, slot_id)
    return got[0] if got else None


def email_line_of(brand, slot_id):
    """The email an SMS follows, in words: its slot id and, once it is written, its first subject line."""
    if not slot_id:
        return "no email named"
    d = email_run(brand, slot_id)
    if not d:
        return f"`{slot_id}`, not written yet"
    card = d / "klaviyo" / "card.json"       # the subject that goes out; the deliverable can hold an older draft's
    e = json.loads((card if card.is_file() else d / "deliverable" / "email.json").read_text())
    subs = e.get("subjects") or []
    first = (subs[0].get("subject") if subs and isinstance(subs[0], dict) else e.get("subject")) or ""
    return f"`{slot_id}`" + (f", subject “{first}”" if first else "")


# 2026-11-05: a weekly SMS carries no offer (marketing-calendar weekly_sms.py: "no new urgency or offer"), and the
# writer refused every one because the bank has no `none` section. With no offer the text sells nothing of its own:
# it points to the email it follows, and the checks below see no price and "no code", so a price or code is held.
NO_OFFER = ("No offer. This text sells nothing on its own: it names no price, no discount, no saving, no code and "
            "no deadline. It points the reader to the email it follows ({email}); its link is that email's link.")


def section_for(brand, slot):
    """The offer's section, or for a slot with no offer, the no-offer rule naming the email it follows."""
    key = slot.get("offer") or "none"
    if key == "none":
        return NO_OFFER.format(email=email_line_of(brand, slot.get("follows")))
    return offer_section(brand, key)


def fill(template, slot, brand, cad):
    sec = section_for(brand, slot)
    sender = WORKSPACE / "brands" / brand / "email-sms" / "identity" / "sender.md"
    ln = cad.get("length") or {}
    moment_text = slot.get("occasion") or ""
    vals = {
        "brand_name": brand.replace("-", " ").title(), "moment": slot.get("occasion") or "",
        "moment_text": moment_text, "beat": slot.get("sms_beat") or "",
        "beat_meaning": (cad.get("beat_meaning") or {}).get(slot.get("sms_beat") or "", ""),
        "date": slot.get("date", ""), "segment": ", ".join(slot.get("segments") or [slot.get("segment", "")]),
        "audience_rule": slot.get("audience_rule") or cad.get("audience", ""), "why": slot.get("why", ""),
        "offer_key": slot.get("offer") or "none", "offer_section": sec or "(the bank has no section for it)",
        "sender": sender.read_text().strip() if sender.is_file() else "(no sender identity on file — plain, warm, direct)",
        "job": slot.get("sms_job") or "reminder",
        "job_meaning": (cad.get("job_meaning") or {}).get(slot.get("sms_job") or "reminder", ""),
        "email_follows": email_line_of(brand, slot.get("follows")),
        "reply_rule": (f"Ask for one reply: the keyword `{slot['reply_keyword']}`, written exactly so, once."
                       if slot.get("sms_job") == "reply" and slot.get("reply_keyword")
                       else "Ask for no reply: no keyword, no \"reply YES\"."),
        "max_chars": ln.get("max_chars", 160), "link_chars": ln.get("link_chars", 25),
        "opt_out": ln.get("opt_out", "Reply STOP to opt out"),
    }
    out = template
    for k, v in vals.items():
        out = out.replace("{" + k + "}", str(v))
    required_lead = slot.get("required_lead")
    if required_lead:
        out += "\n\nRequired opening, verbatim: " + required_lead
    if slot.get("order_by"):
        out += "\nShipping order-by cutoff: " + slot["order_by"] + ". This is not the sale end."
    elif slot.get("deadline"):
        out += "\nSale deadline: " + slot["deadline"] + ". Last day wording is allowed only on that date."
    note = (slot.get("_review") or {}).get("note", "").strip()
    if note:
        out += "\n\nProduction instructions from calendar review:\n" + note
    return out.replace("{{link}}", "{link}"), sec


def one_avatar(slot):
    """The one avatar a text speaks to, or None: a text to a mixed list speaks to no one person."""
    named = {v.get("avatar") for v in slot.get("variants") or [] if isinstance(v, dict)} or {slot.get("avatar")}
    named = {a for a in named if a not in (None, "", "none", "mixed")}
    return named.pop() if len(named) == 1 else None


def write_one(slot, brand, cad, prompt_file, dry=False, call=None):
    label = f"{brand}-{slot['id']}-sms"
    text, sec = fill(prompt_file.read_text(), slot, brand, cad)
    from email_line import who_aim               # who it is for (creative-strategist who.py), the email line's own read
    who_block, aim = who_aim(brand, one_avatar(slot))
    text = who_block + text
    if not sec:
        return label, None, [f"offer `{slot.get('offer')}` has no section in the bank"]
    if dry:
        return label, None, []
    msg = (call(text) if call else _model(text)).strip().splitlines()
    msg = " ".join(x.strip() for x in msg if x.strip())
    problems = check(msg, sec, cad, slot)
    d = WORKSPACE / "runs" / "email-production" / brand / label
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt-sent.md").write_text(text)
    rec = {"label": label, "brand": brand, "slot": slot["id"], "date": slot.get("date"),
           "beat": slot.get("sms_beat"), "segments": slot.get("segments"), "offer": slot.get("offer"), "aim": aim,
           "moment": slot.get("occasion"), "job": slot.get("sms_job"), "follows": slot.get("follows"),
           "text": msg, "characters": len(msg.replace("{link}", "x" * int((cad.get("length") or {}).get("link_chars", 25)))),
           "status": "draft", "state": ("held: " + "; ".join(problems)) if problems else "ready for review",
           "prompt": prompt_file.name, "written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "sent": False}
    (d / "sms.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    (d / "sms.md").write_text(f"# {label}\n\n{slot.get('date')} · {rec['beat']} · {', '.join(slot.get('segments') or [])}"
                              f" · offer `{slot.get('offer')}`\n\n> {msg}\n\n{rec['characters']} characters · {rec['state']}\n")
    return label, rec, problems


def recheck_one(slot, brand, cad, prompt_file):
    """Check the saved words against today's reviewed slot; never rewrite their provenance."""
    label = f"{brand}-{slot['id']}-sms"
    d = WORKSPACE / "runs" / "email-production" / brand / label
    f = d / "sms.json"
    if not f.is_file():
        return label, None, ["no saved SMS draft to check"]
    rec = json.loads(f.read_text())
    _, section = fill(prompt_file.read_text(), slot, brand, cad)
    problems = check(rec["text"], section, cad, slot)
    if rec.get("date") != slot.get("date") or rec.get("segments") != slot.get("segments"):
        problems.append("saved date or audience differs from the reviewed calendar; rewrite this draft")
    rec["state"] = ("held: " + "; ".join(problems)) if problems else "ready for review"
    rec["checked"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    f.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    md = d / "sms.md"
    if md.is_file():
        text = md.read_text()
        text = re.sub(r"(?m)^([0-9]+ characters) · .*?$", lambda m: m[1] + " · " + rec["state"], text)
        md.write_text(text)
    return label, rec, problems


def _model(prompt):
    import lean_call
    from run_kit import model as M
    m, _why = M.pick("designs", len(prompt))
    return M.call(prompt, m, label="sms", runner=lean_call.runner(M))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write the SMS a calendar month plans. Never sends.")
    ap.add_argument("run_dir")
    ap.add_argument("--only", default=None, help="comma-separated slot ids")
    ap.add_argument("--dry-run", action="store_true", help="fill every prompt and report; spend and write nothing")
    ap.add_argument("--check-only", action="store_true", help="recheck saved drafts against reviewed slots; no model calls")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    if not run_dir.is_absolute():
        run_dir = (Path.cwd() / run_dir).resolve()
    brand = run_dir.parent.name
    sys.path.insert(0, str(HERE / "machine"))
    import reviewed_plan as RP
    slots = [s for s in RP.reviewed(run_dir, json.loads((run_dir / "slots.json").read_text()))
             if s.get("channel") == "sms"]
    if a.only:
        want = set(a.only.split(","))
        slots = [s for s in slots if s["id"] in want]
    cad, pf = cadence(), latest_prompt()
    if not pf:
        sys.exit("no prompts/sms-v*-*.md")
    print(f"{brand} {run_dir.name}: {len(slots)} SMS · prompt {pf.name}" + (" · DRY RUN" if a.dry_run else ""))
    bad = 0
    for s in slots:
        label, rec, problems = recheck_one(s, brand, cad, pf) if a.check_only else write_one(s, brand, cad, pf, dry=a.dry_run)
        bad += bool(problems)
        print(f"  {s['id']} {s.get('date')} {s.get('sms_beat') or '':<12} offer {s.get('offer')}: "
              + ("ready to fill" if a.dry_run and not problems else
                 (rec or {}).get("text", "") + f"  [{(rec or {}).get('state', '; '.join(problems))}]"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
