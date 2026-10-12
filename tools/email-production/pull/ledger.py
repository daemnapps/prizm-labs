#!/usr/bin/env python3
"""Every subject line this brand has already sent, with what it did.

    python3 ledger.py --brand brand-b

Stage 5 of the email lane asks for a hook ledger and refuses to reuse ground
that is on it. Without this file that rule is unenforceable, and the machine
will eventually propose a subject line the list has already seen.

The campaign NAME is not the subject line — they differ often — so this pulls
the message behind each campaign and reads the real subject and preview text.
Proposes email-sms/ledger.json + ledger.md under
runs/email-production/<brand>/facts-<YYYY-MM-DD>/ (K2 (brands write wall)).

Reads only.
"""
import argparse
import json
import sys
import urllib.error
from pathlib import Path

import derive as D

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import WORKSPACE  # noqa: E402
import facts_proposal  # noqa: E402
BRAND_ROOT = WORKSPACE / "brands"

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--since", default="2025-01-01",
                    help="how far back to read. Ground spent three years ago is "
                         "not ground the list remembers.")
    ap.add_argument("--max-pages", type=int, default=12)
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    args = ap.parse_args()
    key = D.key_for(args.brand)

    rows, url_params = [], {
        "filter": f"and(equals(messages.channel,'email'),"
                  f"greater-or-equal(created_at,{args.since}T00:00:00Z))",
        "sort": "-created_at",
        "include": "campaign-messages",
    }
    page, cursor = 0, None
    while True:
        p = dict(url_params)
        if cursor:
            p["page[cursor]"] = cursor
        r = D.get("campaigns", key, **p)
        # subjects live on the included messages, keyed back by id
        subj = {}
        for m in r.get("included", []):
            c = (m.get("attributes", {}).get("definition", {}) or {}).get("content", {}) or {}
            subj[m["id"]] = (c.get("subject"), c.get("preview_text"), c.get("from_label"))
        for c in r.get("data", []):
            a = c["attributes"]
            if a.get("status") != "Sent":
                continue
            mids = [d["id"] for d in c["relationships"]["campaign-messages"]["data"]]
            s, pv, fl = next((subj[i] for i in mids if i in subj), (None, None, None))
            st = a.get("send_strategy") or {}
            dtm = st.get("datetime") or a.get("send_time") or ""
            rows.append({
                "sent": (a.get("send_time") or "")[:10],
                "hour": dtm[11:13] if len(dtm) > 13 else None,
                "is_local": bool((st.get("options") or {}).get("is_local")),
                "campaign": a["name"],
                "subject": s,
                "preview": pv,
                "from": fl,
                "audiences": a.get("audiences", {}).get("included", []),
                "id": c["id"],
            })
        nxt = r.get("links", {}).get("next")
        page += 1
        if not nxt or page >= args.max_pages:
            break
        import urllib.parse as U
        cursor = U.parse_qs(U.urlparse(nxt).query).get("page[cursor]", [None])[0]
        if not cursor:
            break

    rows.sort(key=lambda x: x["sent"], reverse=True)
    run = facts_proposal.run_dir(args.brand, args.label)
    facts_proposal.write(run, args.brand, "email-sms/ledger.json", json.dumps(rows, indent=1) + "\n")

    L = [f"# {args.brand} — subject lines already sent", "",
         f"{len(rows)} sent email campaigns. **Everything here is ground already",
         "spent.** Stage 5 of the email lane reads this and will not build on a",
         "line that appears below without saying so.", "",
         "A blank subject means the campaign's message could not be read — that is",
         "a gap in the ledger, not a campaign without a subject.", "",
         "| Sent | Subject | Preview | From |", "|---|---|---|---|"]
    for r in rows:
        f = lambda s: (s or "—").replace("|", "\\|")
        L.append(f"| {r['sent'] or '—'} | {f(r['subject'])} | {f(r['preview'])} | {f(r['from'])} |")
    facts_proposal.write(run, args.brand, "email-sms/ledger.md", "\n".join(L) + "\n")

    got = sum(1 for r in rows if r["subject"])
    print(f"{len(rows)} sent campaigns · {got} with a readable subject line")
    print(f"proposal -> {facts_proposal.note(run, args.brand)}")
    from collections import Counter
    yrs = Counter(r["sent"][:4] for r in rows if r["sent"])
    print("by year:", dict(sorted(yrs.items())))
    nop = sum(1 for r in rows if r["subject"] and not r["preview"])
    print(f"subject with NO preview text: {nop} of {got}")


if __name__ == "__main__":
    main()
