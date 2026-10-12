#!/usr/bin/env python3
"""Every email this brand has actually sent, pulled down whole.

    python3 calendar/index_sends.py --brand brand-b [--limit N]

The ledger gives subject lines. This gives the EMAILS — the real body of every
campaign that went out, so past sends stop being a list of titles and become a
swipe library. Our own winners are sources to swipe, exactly like anyone else's.

Per campaign: the campaign, its message, and the template behind it. Proposes
one readable file per send plus an index, under
runs/email-production/<brand>/facts-<YYYY-MM-DD>/email-sms/sends/ (K2 (brands
write wall)) — a person folds them into brands/. Reads only; nothing is sent,
changed or deleted.

Rate limits are real — Klaviyo caps template reads — so this throttles, retries
on 429, and can be re-run: anything already pulled — in brands/ or in this
run — is skipped.
"""
import argparse
import html as H
import json
import re
import sys
import time
import urllib.error
from pathlib import Path

import derive as D

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import WORKSPACE  # noqa: E402
import facts_proposal  # noqa: E402
BRAND_ROOT = WORKSPACE / "brands"

HERE = Path(__file__).resolve().parent


def strip_html(s):
    """The email as a person reads it — copy, images, buttons, in order.

    An email is not prose. Throwing the images and the buttons away leaves
    something the teardown cannot read the LAYOUT of, and stage 1 is written to
    count CTAs, count images and describe what is in the frame. So the
    structure survives the reduction, marked up in plain text.
    """
    if not s:
        return ""
    s = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", s)
    # images become a named block with their source and alt text
    def _img(m):
        tag = m.group(0)
        src = (re.search(r'src=["\']([^"\']+)', tag) or [None, ""])[1]
        alt = (re.search(r'alt=["\']([^"\']*)', tag) or [None, ""])[1]
        if not src or src.startswith("data:"):
            return "\n"
        return f"\n[IMAGE{' alt=' + alt if alt else ''}] {src}\n"
    s = re.sub(r"(?is)<img[^>]*>", _img, s)
    # headings keep their level, so the visual hierarchy is legible
    s = re.sub(r"(?is)<h([1-3])[^>]*>(.*?)</h\1>",
               lambda m: f"\n[HEADING] {re.sub('<[^>]+>', '', m.group(2)).strip()}\n", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|tr|h[1-6]|li)>", "\n", s)
    # a link that is styled as a button is a CTA, and worth marking as one
    def _a(m):
        href, inner = m.group(1), re.sub("<[^>]+>", "", m.group(2)).strip()
        if not inner:
            return " "
        cta = re.search(r"(?i)button|btn|cta", m.group(0))
        return f"\n[{'BUTTON' if cta else 'LINK'}] {inner} -> {href[:120]}\n"
    s = re.sub(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', _a, s)
    s = re.sub(r"(?is)<hr[^>]*>", "\n[DIVIDER]\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = H.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    return "\n".join(l.strip() for l in s.splitlines()).strip()


def get(path, key, tries=5, **params):
    for a in range(tries):
        try:
            return D.get(path, key, **params)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** a
                print(f"    rate limited, waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"gave up on {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--sleep", type=float, default=0.35)
    ap.add_argument("--force", action="store_true",
                    help="re-pull even where a file already exists")
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    args = ap.parse_args()
    key = D.key_for(args.brand)

    led = BRAND_ROOT / args.brand / "email-sms" / "ledger.json"
    if not led.is_file():
        sys.exit(f"no ledger at {led} — run ledger.py first")
    rows = json.loads(led.read_text())
    if args.limit:
        rows = rows[:args.limit]

    have = BRAND_ROOT / args.brand / "email-sms" / "sends"
    run = facts_proposal.run_dir(args.brand, args.label)
    out = run / "email-sms" / "sends"
    index, pulled, skipped, failed = [], 0, 0, []

    for i, r in enumerate(rows, 1):
        slug = re.sub(r"[^a-z0-9]+", "-", (r["subject"] or r["campaign"]).lower())[:60].strip("-")
        name = f"{r['sent'] or '0000-00-00'}--{slug}.md"
        if ((have / name).is_file() or (out / name).is_file()) and not args.force:
            skipped += 1
            index.append({**{k: r[k] for k in ("sent", "subject", "preview", "from", "campaign")},
                          "file": name})
            continue
        try:
            m = get(f"campaigns/{r['id']}/campaign-messages", key, **{"include": "template"})
            tpl = next((x for x in m.get("included", []) if x["type"] == "template"), None)
            a = (tpl or {}).get("attributes", {})
            body = strip_html(a.get("html")) or (a.get("text") or "").strip()
            if not body:
                failed.append((r["sent"], r["subject"], "no template body"))
                continue
            facts_proposal.write(run, args.brand, f"email-sms/sends/{name}",
                f"# {r['subject'] or r['campaign']}\n\n"
                f"- sent: {r['sent']}\n- from: {r['from']}\n"
                f"- preview: {r['preview']}\n"
                f"- audiences: {', '.join(r['audiences']) or '(none recorded)'}\n"
                f"- campaign: {r['campaign']}\n- id: {r['id']}\n\n---\n\n{body}\n")
            index.append({**{k: r[k] for k in ("sent", "subject", "preview", "from", "campaign")},
                          "file": name, "chars": len(body)})
            pulled += 1
        except Exception as e:
            failed.append((r["sent"], r["subject"], str(e)[:90]))
        if i % 20 == 0:
            print(f"  {i}/{len(rows)} · pulled {pulled} · skipped {skipped} · failed {len(failed)}")
        time.sleep(args.sleep)

    facts_proposal.write(run, args.brand, "email-sms/sends/index.json", json.dumps(index, indent=1) + "\n")
    L = [f"# {args.brand} — every email actually sent", "",
         f"{len(index)} emails on disk, pulled from the sending platform. Bodies are",
         "the readable reduction of each template, with link destinations kept beside",
         "their text.", "",
         "**These are sources to swipe.** An email of ours that worked is a source",
         "exactly like a competitor's — that collapse is why the chain has one input",
         "slot and no separate bank to match against.", "",
         "| Sent | Subject | From | File |", "|---|---|---|---|"]
    for x in sorted(index, key=lambda z: z["sent"] or "", reverse=True):
        f = lambda s: (s or "—").replace("|", "\\|")
        L.append(f"| {x['sent'] or '—'} | {f(x['subject'])} | {f(x['from'])} | `{x['file']}` |")
    if failed:
        L += ["", "## Could not pull", ""]
        L += [f"- {d or '—'} · {s or '—'} — {w}" for d, s, w in failed]
    facts_proposal.write(run, args.brand, "email-sms/sends/README.md", "\n".join(L) + "\n")

    print(f"\n{pulled} pulled · {skipped} already had · {len(failed)} failed")
    print(f"proposal -> {facts_proposal.note(run, args.brand)}")


if __name__ == "__main__":
    main()
