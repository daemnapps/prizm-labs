"""The final check on a batch of designed emails, any brand, written onto each Klaviyo card (card.json → final_check).

Lifted from runs/email-production/brand-a/week-2026-10-12/final_check.py. Run after build.py, over the
whole batch (a calendar window), because one check spans the batch:

    python3 design/check.py <run folder> [<run folder> ...]

Per email: every link answers 200 (each page asked once per batch, tracking tags dropped; a 429 is asked
again after the store's wait, and one that stays 429, or a Cloudflare challenge, is a "by-hand" row: it does not hold the email, and
the approval page asks a person to open the page and confirm before Approve); subject and preview set; unsubscribe and preferences tags present;
alt text on every picture; no picture over 1MB, the whole email under 2.5MB; no name on the brand's
never-use list; the product check passed; a concept and its culture source on the card (EMAIL-LINE
step 1b, never generic). Across the batch: no customer photo or made picture used in two emails.
The approval page holds Approve until every row is ok.
"""
import html
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import look as L  # noqa: E402


ANSWERS = {}                                   # one answer per page for the whole batch: the tracking tags never change the page


def page_of(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip("/") or "/", "", ""))


PACE, RETRIES = 5, 2                           # seconds between pages; asks again after a 429
NOTE = "note"                                  # worth seeing, never a hold (a picture shared with another email)
BY_HAND = "by-hand"                            # a row no machine could settle; it holds nothing until the approver confirms it
CHALLENGE = "403 challenge"                    # Cloudflare asking for a browser (cf-mitigated: challenge), not a missing page
KEPT_OUT = ("429", CHALLENGE)


def ask(url):
    r = subprocess.run(["curl", "-sS", "-L", "-o", "/dev/null", "-w", "%{http_code}|%header{retry-after}|%header{cf-mitigated}",
                        "--max-time", "25", "-A", "Mozilla/5.0", url], capture_output=True, text=True)
    k, after, mitigated = (r.stdout.strip().split("|") + ["", "", ""])[:3]
    return (CHALLENGE if mitigated.strip() == "challenge" else k or "no answer"), after.strip()


def code(url, wait=time.sleep):
    """Pages are asked a few seconds apart, and a store that says 429 (too many requests) is asked again after
    the wait it names, up to 90 seconds, twice at most (the team, 2026-10-27: the BRAND-A store answers 429 to a
    check that visits the same page twelve times in a row). A Cloudflare challenge (403 with cf-mitigated:
    challenge) is never asked again: it wants a browser, and asking only deepens the block."""
    page = page_of(url)
    if page not in ANSWERS:
        if ANSWERS:
            wait(PACE)
        k, after = ask(page)
        for _ in range(RETRIES):
            if k != "429":
                break
            wait(min(int(after) if after.isdigit() else 60, 90))
            k, after = ask(page)
        ANSWERS[page] = k
    return ANSWERS[page]


def holds(card):
    """What holds an email, split by who fixes it (the team, 2026-10-28): a problem ABOUT A PICTURE is the designer's
    and is the only thing that stops the team's Done; every other problem is the words or the product, which the team
    settles before the email reaches the team, so it holds only the approver. Notes and by-hand rows hold no one.
    Returns (designer, approver), each a list of the problems' words, in order, without repeats."""
    rows = [x for x in (card.get("product_check") or []) + (card.get("final_check") or [])
            if x.get("result") not in ("ok", BY_HAND, NOTE)]
    pick = lambda pic: list(dict.fromkeys(x.get("detail") for x in rows if (x.get("about") == "picture") == pic))
    return pick(True), pick(False)


def pictures_of(spec):
    """Every proof item and made/photo picture an email's spec uses (not product cut-outs or ornaments, which repeat by design)."""
    out = set()
    def walk(x):
        if isinstance(x, dict):
            if "proof" in x:
                out.add("proof:" + x["proof"])
            if "photo" in x and x.get("source") in ("made", "photo", "proof"):
                out.add(x["photo"])
            if "gif" in x:
                out.add(x["gif"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(spec.get("sections", []))
    return out


def main(dirs):
    runs = [Path(d).resolve() for d in dirs]
    specs = {d: json.loads((d / "design" / "email.json").read_text()) for d in runs}
    used = defaultdict(list)
    for d, s in specs.items():
        for p in pictures_of(s):
            used[p].append(s["label"])
    for d in runs:
        f = d / "klaviyo" / "card.json"
        c = json.loads(f.read_text())
        spec = specs[d]
        lk = L.load(c["brand"], d)
        doc = (d / "klaviyo" / "email.html").read_text()
        rows = []
        def row(ok, what, about=None):
            rows.append(dict({"result": "ok" if ok else "PROBLEM", "detail": what}, **({"about": about} if about else {})))
        sub = (c.get("subjects") or [{}])[0]
        row(bool(sub.get("subject")), "subject: %s" % sub.get("subject"))
        row(bool(sub.get("preview")), "preview: %s" % sub.get("preview"))
        row("{% unsubscribe" in doc and "{% manage_preferences" in doc, "unsubscribe + preferences tags in the footer")
        imgs = re.findall(r"<img [^>]*>", doc)
        no_alt = [i for i in imgs if 'alt=""' in i and "foot.jpg" not in i]
        row(not no_alt, "alt text on every picture (%d pictures)" % len(imgs), "picture")
        a = d / "klaviyo" / "assets"
        big = [p.name for p in a.iterdir() if p.stat().st_size > 1_000_000]
        total = sum(p.stat().st_size for p in a.iterdir()) + len(doc)
        row(not big, "no picture over 1MB" if not big else "over 1MB: %s" % ", ".join(big), "picture")
        row(total < 2_500_000, "whole email %d KB" % (total // 1024), "picture")
        text = html.unescape(doc).lower()
        hits = [n for n in (lk.get("check") or {}).get("never_names", []) if n.lower() in text]
        row(not hits, "no never-use names" if not hits else "contains: %s" % ", ".join(hits))
        ok = bool(spec.get("concept") and spec.get("culture"))
        row(ok, "concept: %s" % spec.get("concept") if ok else "no concept or culture source (EMAIL-LINE step 1b): a generic email is held")
        # a picture row of the product check is held from the product check itself (holds), never repeated here
        bad = [x["detail"] for x in c.get("product_check", []) if x["result"] != "ok" and x.get("about") != "picture"]
        row(not bad, "product check passed" if not bad else "; ".join(bad))
        for u in c.get("links", []):
            k = code(u)
            if k in KEPT_OUT:                  # the store keeps machines out: a person opens it (approve_klaviyo.py, confirm)
                hand = {"result": BY_HAND, "detail": "%s → %s: the store would not let the check in; open it and confirm" % (page_of(u), k)}
                if hand not in rows:
                    rows.append(hand)
            else:
                row(k == "200", "%s → %s" % (u.split("?")[0], k))
        # A picture shared with another email is a NOTE, never a hold (the team, 2026-10-28): the same product
        # picture in several emails is fine, and the designer decides whether to swap it.
        rep = sorted(p for p in pictures_of(spec) if len(used[p]) > 1)
        rows.append({"result": "ok" if not rep else NOTE, "detail": "no picture shared with another email in this batch"
                     if not rep else "also used in %s: %s" % (
                         ", ".join(sorted({x for p in rep for x in used[p] if x != c["label"]})), ", ".join(rep))})
        c["final_check"] = rows
        f.write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
        bad = [r["detail"] for r in rows if r["result"] not in ("ok", BY_HAND, NOTE)]
        hand = [r["detail"].split(" → ")[0] for r in rows if r["result"] == BY_HAND]
        print("%-30s %2d checks  %s%s" % (c["label"], len(rows), "PASS" if not bad else "PROBLEMS: " + " | ".join(bad),
                                          "  · by hand: " + ", ".join(hand) if hand else ""))
        try:                                   # the email's full index (every step, in order) stays current with its checks
            import run_index
            run_index.index(d)
        except Exception as e:  # noqa: BLE001 — an index that won't write never blocks the check
            print("   index not written: %r" % e)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
