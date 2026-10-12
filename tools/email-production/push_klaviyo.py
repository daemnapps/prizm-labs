#!/usr/bin/env python3
"""Push a finished, picked email into Klaviyo as a DRAFT campaign.

    python3 push_klaviyo.py results/<label> --brand <brand> --pick 3
    python3 push_klaviyo.py results/<label> --brand <brand> --pick 0   # the control

What it does, in order: reads the run's final HTML and its subject set,
takes the HUMAN-PICKED pair (--pick N, from the numbered set on the page),
resolves the slot's segment to the brand's live segment id, creates a
template + a draft campaign in the brand's Klaviyo account, and assigns the
template. THE CAMPAIGN IS A DRAFT AND STAYS ONE — this tool has no send
call, and never will (HANDOFF-TO-HUMANS: send authority is human, in the
platform).

From-line: reused from the brand's most recent real campaign unless
--from-email/--from-label are given — the brand's own record, never invented.
Uses curl throughout (email.py shadows the stdlib `email` package).
Requires a FULL private key (campaigns/templates write) — the pulls' key is
read-only by design; a 403 here names the fix.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from paths import HERE, WORKSPACE, brand_runs

API = "https://a.klaviyo.com/api"
REVISION = "2025-07-15"

def key_for(brand):
    """Same convention as the pulls (pull/derive.py) — duplicated here only
    because importing that module drags urllib through the email.py shadow.
    ENVIRONMENT only: a key by path is a wall (FOLD Y4c, 2026-09-23)."""
    import os
    name = f"KLAVIYO_{brand.upper()}_KEY"
    env = os.environ.get(name)
    if env and env.strip():
        return env.strip()
    sys.exit(f"no Klaviyo key for {brand}: set {name} in your environment")


def kl(method, path, key, payload=None):
    cmd = ["curl", "-sS", "--max-time", "60", "-X", method,
           "-H", f"Authorization: Klaviyo-API-Key {key}",
           "-H", f"revision: {REVISION}",
           "-H", "Content-Type: application/vnd.api+json",
           "-H", "accept: application/vnd.api+json",
           f"{API}/{path}"]
    if payload is not None:
        cmd += ["-d", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"curl failed: {r.stderr[:200]}")
    out = json.loads(r.stdout) if r.stdout.strip() else {}
    if "errors" in out:
        e = out["errors"][0]
        if e.get("status") in (401, 403, "401", "403"):
            sys.exit("Klaviyo refused: the key lacks write access.\n"
                     "  One action (only the account owner can): Klaviyo → "
                     "Settings → API keys → Create Private Key with Full "
                     "Access, and paste it into the brand's key file — then "
                     "say 'push again'.")
        sys.exit(f"Klaviyo error: {e.get('detail', e)[:300]}")
    return out


def subject_pairs(run_dir):
    """The numbered set from stage 5 — VERSION 0 is the control, pick 0."""
    text = (run_dir / "stage5--subjects.md").read_text()
    # Stage 5's shape varies run to run (VERSION 0 / VARIATION N / bare "N —").
    # Number every Subject/Preview pair in document order: 0 is always the
    # control (the prompt requires VERSION 0 first), then 1..N.
    pairs = {}
    for i, m in enumerate(re.finditer(
            r"[-*\s]*\*\*Subject:\*\*\s*`?([^`\n]+?)`?\s*\n"
            r"[-*\s]*\*\*Preview:\*\*\s*`?([^`\n]+?)`?\s*(?:\n|$)", text)):
        pairs[i] = (m.group(1).strip(), m.group(2).strip())
    return pairs


def segment_id(brand_root, segment_name):
    m = json.loads((brand_root / "email-sms/audience-matrix.json").read_text())
    for s in m["segments"]:
        if s["name"] == segment_name:
            return s["id"]
    sys.exit(f"segment {segment_name!r} not in the brand's audience matrix")


def latest_from_line(key):
    out = kl("GET", "campaigns/?filter=equals(messages.channel,'email')"
                    "&sort=-created_at&page%5Bsize%5D=1"
                    "&include=campaign-messages", key)
    for inc in out.get("included", []):
        c = inc.get("attributes", {}).get("definition", {}).get("content", {})
        if c.get("from_email"):
            return c["from_email"], c.get("from_label", "")
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--pick", type=int, required=True,
                    help="which subject pair the human chose (0 = control)")
    ap.add_argument("--from-email", default=None)
    ap.add_argument("--from-label", default=None)
    a = ap.parse_args()
    run_dir = Path(a.run_dir)
    if not run_dir.is_absolute():
        run_dir = HERE / run_dir
    brand_root = WORKSPACE / "brands" / a.brand
    label = run_dir.name

    html = (run_dir / "email-final.html")
    if not html.is_file():
        sys.exit("no email-final.html — render_email.py first")
    pairs = subject_pairs(run_dir)
    if a.pick not in pairs:
        sys.exit(f"pick {a.pick} not in the set — available: {sorted(pairs)}")
    subject, preview = pairs[a.pick]

    slot = None
    # compose runs land under runs/ since email-production#19; results/ is pre-move history
    for cal in sorted(brand_root.glob("email-sms/calendar-*.json")) + \
               sorted(brand_runs(a.brand).glob("compose-*/slots.json")) + \
               sorted((HERE / "results").glob("compose-*/slots.json")):
        data = json.loads(cal.read_text())
        for s in (data.get("slots") if isinstance(data, dict) else data) or []:
            if s.get("id") == label:
                slot = s
    if not slot:
        sys.exit(f"no slot named {label} in any calendar — the segment comes "
                 "from the plan, never guessed")
    # one send to several segments is ONE campaign with several audiences
    seg_names = slot.get("segments") or [slot["segment"]]
    seg_ids = [segment_id(brand_root, n) for n in seg_names]
    seg_id = seg_ids[0]

    key = key_for(a.brand)
    frm, frml = a.from_email, a.from_label
    if not frm:
        frm, frml = latest_from_line(key)
    if not frm:
        sys.exit("no from-address on record — pass --from-email")

    print(f"push: {label} · pick {a.pick} · “{subject}” · "
          f"{slot['segment']} → segment {seg_id} · from {frml} <{frm}>")

    tpl = kl("POST", "templates/", key, {"data": {
        "type": "template",
        "attributes": {"name": f"{a.brand} · {label} · machine",
                       "editor_type": "CODE",
                       "html": html.read_text()}}})
    tpl_id = tpl["data"]["id"]

    camp = kl("POST", "campaigns/", key, {"data": {
        "type": "campaign",
        "attributes": {
            "name": f"[MACHINE DRAFT] {label} — {slot.get('type')}",
            "audiences": {"included": seg_ids, "excluded": []},
            "send_strategy": {"method": "static"},
            "campaign-messages": {"data": [{
                "type": "campaign-message",
                "attributes": {"definition": {
                    "channel": "email",
                    "label": label,
                    "content": {"subject": subject,
                                "preview_text": preview,
                                "from_email": frm,
                                "from_label": frml or a.brand}}}}]}}}})
    camp_id = camp["data"]["id"]
    msg_id = camp["data"]["relationships"]["campaign-messages"]["data"][0]["id"]

    kl("POST", "campaign-message-assign-template/", key, {"data": {
        "type": "campaign-message",
        "id": msg_id,
        "relationships": {"template": {"data": {"type": "template",
                                                "id": tpl_id}}}}})
    (run_dir / "pushed.json").write_text(json.dumps(
        {"campaign_id": camp_id, "template_id": tpl_id, "message_id": msg_id,
         "pick": a.pick, "subject": subject, "segment": slot["segment"],
         "status": "DRAFT — schedule it in Klaviyo yourself"}, indent=1) + "\n")
    print(f"DRAFT created: campaign {camp_id} · template {tpl_id}\n"
          "It will never send itself — schedule it in Klaviyo when ready.")


if __name__ == "__main__":
    main()
