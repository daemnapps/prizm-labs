#!/usr/bin/env python3
"""An affiliate send, built straight from the partner record — no swipe, no
ten-stage chain. The chain reverse-engineers a competitor's argument and
injects our brand into it; an affiliate feature is not that kind of email.
It is one partner product, our honest reason for pointing at it, and one
tracked link (the owner, 2026-09-01: "specific emails directly for him, push
traffic to his website, that's it").

    python3 affiliate_email.py results/calendar-2026-09            # every affiliate slot
    python3 affiliate_email.py results/calendar-2026-09 sep-02     # one

Writes runs/email-production/<brand>/<slot>/stage8--blocks.md in the same BLOCKS shape the chain
produces, so render_email.py, the review page and the Klaviyo push treat it
like any other email. Copy is assembled from the partner's real name, real
category and the brand's own one-line reason (affiliates.json `blurb`) —
nothing invented, no first-person claim nobody can own, no commission talk.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from paths import HERE, WORKSPACE, run_home


def blocks_for(partner, brand):
    name = partner["name"]
    cat = (partner.get("category") or "").split("—")[0].strip() or "a partner product"
    blurb = partner.get("blurb", "").strip()
    link = partner["link"]
    return [
        {"type": "preheader", "text": f"Something we don't make, but point people to."},
        {"type": "headline", "text": f"Not ours. Still worth your time."},
        {"type": "copy", "text": (f"We don't make {cat}. When someone asks what we'd use, "
                                  f"this is the answer: {name}.")},
        {"type": "image", "image_brief": f"Product photo — {name}, clean background, in the partner's own product photography style",
         "alt": name},
        {"type": "copy", "text": blurb or f"{name} — a partner's product we're happy to point at."},
        {"type": "button", "label": "Take a look", "href": link},
        {"type": "copy", "text": ("A partner brand, not ours — we're recommending it because it "
                                  "covers ground we don't. Nothing here is a claim we've tested "
                                  "ourselves.")},
        {"type": "footer"},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("slot_ids", nargs="*")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    run_dir = Path(a.run_dir)
    if not run_dir.is_absolute():
        run_dir = HERE / run_dir
    slots = json.loads((run_dir / "slots.json").read_text())
    brand = json.loads((run_dir / "run.json").read_text())["brand"]
    brand_root = WORKSPACE / "brands" / brand
    partners = {p["key"]: p for p in json.loads(
        (brand_root / "email-sms/affiliates.json").read_text()).get("affiliates", [])}
    want = set(a.slot_ids)
    n = 0
    for s in slots:
        if s.get("category") != "Affiliate" or (want and s["id"] not in want):
            continue
        p = partners.get(s.get("affiliate"))
        if not p:
            print(f"  !! {s['id']}: partner {s.get('affiliate')!r} not in affiliates.json — skipped")
            continue
        out = run_home(brand, s["id"])
        out.mkdir(parents=True, exist_ok=True)
        blocks = blocks_for(p, brand)
        (out / "stage8--blocks.md").write_text(
            f"# {s['id']} — affiliate feature: {p['name']}\n\nBuilt straight from the partner "
            "record (affiliate_email.py) — no chain, no swipe.\n\n```BLOCKS\n"
            + json.dumps(blocks, indent=1) + "\n```\n")
        (out / "stage5--subjects.md").write_text(
            f"# Subject lines — {s['id']}\n\n**VERSION 0 (control)**\n- **Subject:** "
            f"Not ours. Still worth it.\n- **Preview:** {p['name']}\n\n**VARIATION 1**\n"
            f"- **Subject:** The part of the routine we don't cover\n- **Preview:** "
            f"{p['name']} — a partner we point people to\n")
        (out / "run.json").write_text(json.dumps({
            "label": s["id"], "brand": brand, "lane_kind": "affiliate",
            "source_path": "affiliates.json", "partner": p["key"],
            "stages": {"stage8": {"status": "done", "by": "code"},
                       "stage5": {"status": "done", "by": "code"}}}, indent=1) + "\n")
        n += 1
        print(f"  -> {s['id']}  {p['name']}")
        if not a.no_render:
            subprocess.run([sys.executable, "render_email.py", str(out),
                            "--brand", brand], cwd=HERE)
    print(f"{n} affiliate email(s) built")


if __name__ == "__main__":
    main()
