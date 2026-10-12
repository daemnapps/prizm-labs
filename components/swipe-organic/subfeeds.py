#!/usr/bin/env python3
"""A feed for every sub-avatar — the brands' own cards are the asks.

    python3 subfeeds.py [--brand <brand>] [--only <sub-id>] [--dry-run] [--parallel 3]

Walks brands/<brand>/core-avatars/<core>/sub-avatars/*.md. For each card with
no feed yet, hands dig.py the PERSON half of the card (everything above the
"### rooms" block) as the ask. The plan prompt is told to read the card for who
the person is and to ignore what we sell him. Feed folder: <brand>--<sub-id>.
Brand-agnostic: nothing here names a brand; a new brand's cards get feeds the
next time this runs.
"""
import argparse, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import desklib as D

BRANDS = D.WS / "brands"


def cards(brand=None):
    for f in sorted(BRANDS.glob("*/core-avatars/*/sub-avatars/*.md")):
        b, core = f.parts[-5], f.parts[-3]
        if b.startswith("_") or (brand and b != brand):
            continue
        text = f.read_text()
        m = re.search(r"^id:\s*(\S+)", text, re.M)
        t = re.search(r"^###\s+\S+\s+—\s+(.+)$", text, re.M)
        sid = m.group(1) if m else re.sub(r"^sub-\d+-", "", f.stem)
        body = text.split("---", 2)[-1].split("### rooms")[0].strip()
        body = re.sub(r"https?://\S+", "", body)[:2600]
        yield {"brand": b, "core": core, "sub": sid, "title": t.group(1).strip() if t else sid,
               "card": str(f.relative_to(BRANDS.parent)), "person": body}


def cores(brand=None):
    """Core avatars get a feed too — the whole profile's person, one level up."""
    for f in sorted(BRANDS.glob("*/core-avatars/*/profile.md")):
        b, core = f.parts[-4], f.parts[-2]
        if b.startswith("_") or (brand and b != brand):
            continue
        text = f.read_text()
        t = re.search(r"^#\s+(.+)$", text, re.M)
        body = re.sub(r"https?://\S+", "", text.split("---", 2)[-1].strip())[:3200]
        yield {"brand": b, "core": core, "sub": None, "title": core.replace("-", " ").title(),
               "card": str(f.relative_to(BRANDS.parent)), "person": body}


def has_ask(c):
    f = D.FEEDS / f'{c["brand"]}--{c["sub"] or c["core"]}' / "sources.json"
    return f.exists() and bool(json.loads(f.read_text()).get("ask"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand"); ap.add_argument("--only")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--per", type=int, default=20)
    a = ap.parse_args()
    todo = [c for c in [*cores(a.brand), *cards(a.brand)]
            if (not a.only or a.only in (c["sub"], c["core"] if not c["sub"] else None)) and not has_ask(c)]
    print(f"{len(todo)} avatars without a feed")
    for c in todo:
        print(f'  {c["brand"]} · {c["core"]} · {c["sub"]} — {c["title"]}')
    if a.dry_run or not todo:
        return

    def one(c):
        feed = f'{c["brand"]}--{c["sub"] or c["core"]}'
        ask = ("The scroll of this person — what they watch purely for fun, nothing about the "
               "product or the problem on this card:\n\n" + c["person"])
        meta = {k: c[k] for k in ("brand", "core", "sub", "card") if c[k]}
        meta["title"] = c["title"]
        r = subprocess.run([sys.executable, "dig.py", ask, "--feed", feed, "--per", str(a.per),
                            "--job", f"dig-{feed}", "--meta", json.dumps(meta)],
                           cwd=str(D.HERE), capture_output=True, text=True)
        print(f"  {feed}: {'done' if r.returncode == 0 else 'FAILED ' + (r.stderr or '')[-160:]}", flush=True)

    with ThreadPoolExecutor(max_workers=a.parallel) as pool:
        list(pool.map(one, todo))


if __name__ == "__main__":
    main()
