#!/usr/bin/env python3
"""Customer answers, ranked, per question: what customers say most for every survey question in
a brand's language rows. This is the evidence each block's words are chosen from.

    python3 scripts/rank_answers.py <brand>/core-avatars/<avatar>/language --out runs/<brand>/answers.md [--top 15]

Reads every *.json of language rows under the folder (skips used/). Each row needs id, text and
source.name; signal.count is used when present. Writes one ranked list per question, each line
with its count and row id so the words can be cited.
"""
import argparse, collections, glob, json, os, re

def rows_in(folder):
    for f in glob.glob(os.path.join(folder, '**', '*.json'), recursive=True):
        if os.sep + 'used' + os.sep in f:
            continue
        data = json.load(open(f))
        yield from (data if isinstance(data, list) else next((v for v in data.values() if isinstance(v, list)), []))

def main():
    a = argparse.ArgumentParser()
    a.add_argument('folder'); a.add_argument('--out', required=True); a.add_argument('--top', type=int, default=15)
    o = a.parse_args()
    by_q = collections.defaultdict(list)
    for r in rows_in(o.folder):
        src = r.get('source') or {}
        if src.get('type') == 'survey' and r.get('text'):
            by_q[src.get('name', '')].append(r)
    norm = lambda t: re.sub(r'[^a-z0-9 ]', '', t.lower()).strip()
    lines = []
    for q, rs in sorted(by_q.items(), key=lambda kv: -len(kv[1])):
        count, first = collections.Counter(), {}
        for r in rs:
            n = norm(r['text'])
            if n:
                count[n] += (r.get('signal') or {}).get('count') or 1
                first.setdefault(n, r)
        lines.append(f'\n## {q} ({len(rs)} rows)\n')
        lines += [f'- {k}× "{first[n]["text"]}" [{first[n]["id"]}]' for n, k in count.most_common(o.top)]
    open(o.out, 'w').write('\n'.join(lines) + '\n')
    print(f'{len(by_q)} questions ranked → {o.out}')

if __name__ == '__main__':
    main()
