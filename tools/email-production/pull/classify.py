#!/usr/bin/env python3
"""Tag every sent email with what it actually was.

    python3 calendar/classify.py --brand brand-b [--batch 8] [--limit N]

The system says an email belongs to exactly one of five categories, decided by
one test — whose material is it made of — and to one of 38 types beneath that.
This runs the real library through that test, which is the only way to find out
whether the model survives contact with three hundred real emails.

Batched, because a classification is a short answer and three hundred separate
calls to ask it would be wasteful. Every answer is validated against the known
keys; a made-up key is dropped rather than trusted, and an email the model
cannot place is recorded as `unlisted` instead of forced into the nearest bin.

Proposes email-sms/classified.json and a readable summary under
runs/email-production/<brand>/facts-<YYYY-MM-DD>/ (K2 (brands write wall)) — a
person folds them into brands/. Resumes from the brands/ copy. Reads only.
"""
import argparse
import glob
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from paths import WORKSPACE  # noqa: E402
import facts_proposal  # noqa: E402
BRAND_ROOT = WORKSPACE / "brands"


def _types(brand):
    f = BRAND_ROOT / brand / "email-sms" / "email-types.json"
    return json.loads(f.read_text())


CATS = {"ask": "Promotional (made of our offer)",
        "help": "Educational (made of our expertise)",
        "belong": "Cultural (made of the world outside)",
        "real": "Community (made of our customers)",
        "brand": "Brand (made of us)"}
# the brand's own catalogue, set by main() once --brand is known
TYPES, BY_KEY, TREATS = None, None, None


def load_types(brand):
    global TYPES, BY_KEY, TREATS
    TYPES = _types(brand)
    BY_KEY = {t["key"]: t for t in TYPES["types"]}
    TREATS = {t["key"] for t in TYPES.get("treatments", [])}


def catalogue():
    out = []
    for ck, cname in CATS.items():
        out.append(f"\n{ck} — {cname}")
        for t in TYPES["types"]:
            if t["well"] == ck:
                out.append(f"  {t['key']}: {t['name']} — {t['what']}")
    out.append("\nTREATMENTS (a treatment is not a category — it is how one is played):")
    out += [f"  {t['key']}: {t['what']}" for t in TYPES["treatments"]]
    return "\n".join(out)


PROMPT = """You are tagging emails a brand actually sent, against a fixed catalogue.

THE CATALOGUE
{cat}

THE TEST that decides the category, and it is the only test:
**Whose material is this email made of?**
- our offer -> ask
- our expertise -> help
- the world outside -> belong
- our customers -> real
- us -> brand

An education email that ends with a link is still `help`. The test is what it
is MADE of, not whether it links or sells. A funny email is not a category —
ask what it is made of and answer that, then note humour as a treatment.

For each email below return one JSON object with:
  "n": the number given
  "category": one of ask|help|belong|real|brand
  "type": one type key from that category
  "treatments": array of treatment keys, possibly empty
  "why": at most 12 words, naming the material

If an email genuinely fits no type, use "type": "unlisted" and say what shape it
is in "why". Do not force it into the nearest bin.

Return ONLY a JSON array, one object per email. No prose.

THE EMAILS
{emails}"""


def claude(text, model="claude-opus-5"):
    r = subprocess.run(["claude", "-p", "--model", model, "--output-format", "text"],
                       input=text, capture_output=True, text=True)
    if r.returncode:
        return None
    return r.stdout


def parse(out):
    if not out:
        return []
    m = re.search(r"\[.*\]", out, re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--chars", type=int, default=1800)
    ap.add_argument("--label", default=None, help="the proposal run (default facts-<UTC day>)")
    args = ap.parse_args()
    load_types(args.brand)

    src = BRAND_ROOT / args.brand / "email-sms" / "sends"
    idx = {x["file"]: x for x in json.loads((src / "index.json").read_text())}
    files = sorted(f for f in glob.glob(str(src / "*.md")) if "README" not in f)
    if args.limit:
        files = files[:args.limit]

    run = facts_proposal.run_dir(args.brand, args.label)
    dest = BRAND_ROOT / args.brand / "email-sms" / "classified.json"
    done = {}
    if dest.is_file():
        done = {x["file"]: x for x in json.loads(dest.read_text())}
    todo = [f for f in files if Path(f).name not in done]
    print(f"{len(files)} emails · {len(done)} already tagged · {len(todo)} to do")

    cat = catalogue()
    for i in range(0, len(todo), args.batch):
        chunk = todo[i:i + args.batch]
        blocks = []
        for n, f in enumerate(chunk, 1):
            p = Path(f)
            meta = idx.get(p.name, {})
            body = p.read_text()
            body = re.sub(r"^#.*?\n---\n", "", body, flags=re.S)
            body = re.sub(r"\[IMAGE[^\]]*\]\s*\S*", "[image]", body)
            blocks.append(
                f"--- EMAIL {n}\nsubject: {meta.get('subject')}\n"
                f"preview: {meta.get('preview')}\nfrom: {meta.get('from')}\n"
                f"{body[:args.chars]}")
        out = parse(claude(PROMPT.format(cat=cat, emails="\n".join(blocks))))
        got = {o.get("n"): o for o in out if isinstance(o, dict)}
        for n, f in enumerate(chunk, 1):
            p = Path(f)
            o = got.get(n, {})
            ck, tk = o.get("category"), o.get("type")
            if tk not in BY_KEY and tk != "unlisted":
                tk = "unlisted"
            if tk in BY_KEY and BY_KEY[tk]["well"] != ck:
                ck = BY_KEY[tk]["well"]          # the type decides; a mismatch is the model's slip
            if ck not in CATS:
                ck = BY_KEY.get(tk, {}).get("well")
            done[p.name] = {"file": p.name, "sent": idx.get(p.name, {}).get("sent"),
                            "subject": idx.get(p.name, {}).get("subject"),
                            "category": ck, "type": tk,
                            "treatments": [t for t in (o.get("treatments") or []) if t in TREATS],
                            "why": (o.get("why") or "")[:120]}
        facts_proposal.write(run, args.brand, "email-sms/classified.json", json.dumps(list(done.values()), indent=1) + "\n")
        print(f"  {min(i + args.batch, len(todo))}/{len(todo)}")

    rows = list(done.values())
    c = Counter(r["category"] for r in rows)
    t = Counter(r["type"] for r in rows)
    L = [f"# {args.brand} — every sent email, tagged", "",
         f"{len(rows)} emails run through the category test.", "",
         "## By category", "", "| Category | Emails | Share |", "|---|---|---|"]
    for k, name in CATS.items():
        L.append(f"| {name} | {c.get(k,0)} | {100*c.get(k,0)/max(len(rows),1):.0f}% |")
    L += ["", "## By type", "", "| Type | Category | Emails |", "|---|---|---|"]
    for k, n in t.most_common():
        L.append(f"| {BY_KEY.get(k,{}).get('name', k)} | "
                 f"{CATS.get(BY_KEY.get(k,{}).get('well'),'—').split(' (')[0]} | {n} |")
    L += ["", "## Never sent", ""]
    never = [x["name"] for x in TYPES["types"] if x["key"] not in t]
    L += [f"- {n}" for n in never] or ["- none — every type has been sent at least once"]
    facts_proposal.write(run, args.brand, "email-sms/classified.md", "\n".join(L) + "\n")
    print(f"\nby category: {dict(c)}")
    print(f"never sent: {len(never)} types")
    print(f"proposal -> {facts_proposal.note(run, args.brand)}")


if __name__ == "__main__":
    main()
