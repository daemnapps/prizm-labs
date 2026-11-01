#!/usr/bin/env python3
"""Top up the comment record on posts already harvested.

The member gate (2+ seeded posts) can only fire if the comment record is
deep enough to catch the same person twice. The first harvest captured a
thin slice; this re-reads the SAME posts' comment sections at depth and
merges — never shrinking, never duplicating a row.

    python3 recomment.py --sub <brand>/<avatar>/<sub> [--comments 100] [--dry-run]
"""
import argparse, json, re
from pathlib import Path
import apify as A

HERE = Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", required=True)
    ap.add_argument("--comments", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = HERE / "records/culture-digs" / args.sub
    posts = []
    for d in sorted((root / "posts").iterdir()):
        pm = d / "post.md"
        if not pm.exists():
            continue
        m = re.search(r"- url: (\S+)", pm.read_text())
        plat = "tiktok" if "tiktok" in d.name else "instagram"
        if m:
            posts.append((d, plat, m.group(1)))
    print(f"{len(posts)} posts on record")
    if args.dry_run:
        return
    for plat in ("tiktok", "instagram"):
        all_batch = [(d, u) for d, p, u in posts if p == plat]
        if not all_batch:
            continue
        print(f"reading {plat} comment sections ({len(all_batch)} posts, up to {args.comments} each, in chunks of 12)")
        got = {}
        for i in range(0, len(all_batch), 12):
            chunk = all_batch[i:i + 12]
            g = A.comments_for([u for _, u in chunk], plat, args.comments)
            if g is None:
                print(f"  chunk {i//12+1} failed — its posts stay as-is, moving on")
                continue
            got.update(g)
            print(f"  chunk {i//12+1}: {len(g)} posts returned")
        batch = all_batch
        for d, u in batch:
            cm = got.get(u)
            if not cm:
                continue
            f = d / "comments.md"
            existing = {}
            if f.exists():
                for line in f.read_text().splitlines():
                    m = re.match(r"- \*\*(\d+)\*\* · @([^\s]+) — (.*)", line)
                    if m:
                        existing[(m.group(2), m.group(3))] = int(m.group(1))
            for c in cm:
                k = (c.get("owner") or "?", c.get("text") or "")
                existing[k] = max(existing.get(k, 0), c.get("likes") or 0)
            rows = sorted(existing.items(), key=lambda kv: -kv[1])
            total_on_post = re.search(r"comments: ([\d,]+)", (d / "post.md").read_text())
            top = total_on_post.group(1) if total_on_post else "?"
            L = [f"# Comments — {len(rows)} captured of {top} on the post", "",
                 "The room talking to each other, ranked by likes. **This is the payload** —",
                 "a caption is a creator broadcasting, this is the avatar unprompted.", ""]
            L += [f"- **{n}** · @{who} — {txt}" for (who, txt), n in rows]
            f.write_text("\n".join(L) + "\n")
    total = sum(len((d / "comments.md").read_text().splitlines()) for d, _, _ in posts
                if (d / "comments.md").exists())
    print(f"done — comment lines on record now: ~{total}")

if __name__ == "__main__":
    main()
