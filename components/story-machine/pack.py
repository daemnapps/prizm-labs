"""Story machine — language pack: the customer words a run is allowed to write with.

    python3 pack.py --root <workspace> --brand <brand> --avatar <avatar> --out pack.md
                    [--spent spent.txt] [--per-topic 10]

Pulls rows from the brand's language layer (components/copywriter/machine/language.py
in <workspace>) topic by topic, never-used rows only, drops any row that contains a
spent phrase (one per line in spent.txt — the lines earlier runs leaned on), and
writes one markdown pack. Every row keeps its id and its source so a script can
say exactly whose words it borrowed.
"""
import argparse
import os
import re
import subprocess

# Topic groups, in the order a story needs them. Each group is one language-layer query.
GROUPS = [
    ("her problem, in her words", ["dark-spots", "brown-spots", "arms", "legs", "crepey"]),
    ("what she tried and why she stopped believing", ["no-results", "skepticism", "diy-alternative", "timeline"]),
    ("who she is", ["shares-her-own-story", "pro-aging", "grey-transition", "origin"]),
    ("her life outside her skin", ["grief-support", "celebration", "recipe-request"]),
    ("what she buys on", ["clean", "ingredients", "ingredient-disclosure", "value", "price"]),
    ("what it felt like after", ["results", "compliment", "texture", "scent"]),
]


def query(root, brand, avatar, topics, limit):
    out = subprocess.run(
        ["python3", os.path.join(root, "components/copywriter/machine/language.py"), "--root", root,
         "--brand", brand, "--avatar", avatar, "--topics", ",".join(topics), "--unused", "--limit", str(limit)],
        capture_output=True, text=True, cwd=root).stdout
    rows = []
    for m in re.finditer(r'^- \[(\S+)\] "(.*?)"\n  _(.*?)_\s*$', out, re.S | re.M):
        rows.append((m.group(1), " ".join(m.group(2).split()), m.group(3).split(" · ")[0:4]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spent", default="")
    ap.add_argument("--per-topic", type=int, default=10)
    ap.add_argument("--skip-ids", default="", help="file of row ids earlier story runs used, one per line")
    a = ap.parse_args()
    spent = [s.strip().lower() for s in open(a.spent)] if a.spent else []
    spent = [s for s in spent if s and not s.startswith("#")]
    seen, parts, total = set(), [], 0
    if a.skip_ids and os.path.exists(a.skip_ids):
        seen |= {x.strip() for x in open(a.skip_ids) if x.strip()}
    for name, topics in GROUPS:
        rows = query(a.root, a.brand, a.avatar, topics, a.per_topic * len(topics))
        keep = []
        for rid, text, meta in rows:
            if rid in seen or len(text.split()) < 4 or any(s in text.lower() for s in spent):
                continue
            seen.add(rid)
            keep.append(f'- [{rid}] "{text}"  \n  _{" · ".join(meta)}_')
        total += len(keep)
        parts.append(f"## {name}\n_topics: {', '.join(topics)} · {len(keep)} rows_\n\n" + "\n".join(keep))
    head = (f"# Language pack — {a.brand} / {a.avatar}\n\n"
            f"{total} never-used rows from the brand's language layer. These are real sentences real people said. "
            "Write with their words; cite the [id] of every row you borrow. "
            f"Spent phrases excluded: {len(spent)}.\n\n")
    open(a.out, "w").write(head + "\n\n".join(parts) + "\n")
    print(f"pack: {total} rows -> {a.out}")


if __name__ == "__main__":
    main()
