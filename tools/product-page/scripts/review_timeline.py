#!/usr/bin/env python3
"""When customers say it worked: find every review that states a time, group it into stages,
count what changed at each stage, and keep their own lines.

    python3 scripts/review_timeline.py reviews.json --outcomes outcomes.json --out runs/<brand>/timeline.json [--product "<store title>"]

reviews.json: a list of {id, title, body, rating, product, photos} (map your review app's export
to these names). outcomes.json: {"label": "regex", ...}, the changes worth counting for this
product: copy outcomes.template.json and replace the last key with the product's main result,
using the customers' own words from the avatar's language rows. Keys without a valid pattern are skipped. Output: stage counts, outcome counts per
stage, and every kept review with its stage, phrase and sentence.
"""
import argparse, collections, json, re, sys

WORDS = {'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
         'eight': 8, 'nine': 9, 'ten': 10, 'couple': 2, 'few': 3, 'several': 4}
SOON = ('overnight', 'first use', 'first time', 'first day', 'first wash', 'immediately', 'right away', 'after one use', 'one use')
TIME = re.compile(r"(?:(\d+(?:\.\d+)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten|couple|few|several)(?:\s+of)?\s*"
                  r"(?:-|to)?\s*(?:\d+\s*)?(day|days|week|weeks|wk|wks|month|months|mo)\b)|\b(" + '|'.join(SOON) + r"|within a week)\b", re.I)
NOT_RESULT = re.compile(r'ship|deliver|arriv|package|mail|still (nothing|waiting)|ago and|resupply', re.I)
STAGES = [('Day 1', 0, 1.5), ('Week 1', 1.5, 7.5), ('Weeks 2-3', 7.5, 22), ('Weeks 4-6', 22, 45),
          ('Weeks 7-12', 45, 91), ('3+ months', 91, 1e9)]

def days(m):
    if m.group(3):
        return 1 if m.group(3).lower() in SOON else 7
    n = m.group(1).lower()
    n = float(WORDS.get(n, n))
    u = m.group(2).lower()
    return n * (1 if u.startswith('d') else 7 if u.startswith('w') else 30)

def main():
    a = argparse.ArgumentParser()
    a.add_argument('reviews'); a.add_argument('--outcomes', required=True); a.add_argument('--out', required=True)
    a.add_argument('--product'); a.add_argument('--min-rating', type=int, default=4)
    o = a.parse_args()
    reviews = json.load(open(o.reviews))
    outcomes = {}
    for k, v in json.load(open(o.outcomes)).items():
        if k.startswith('<') or v.startswith('<'):
            continue
        outcomes[k] = re.compile(v, re.I)
    kept = []
    for r in reviews:
        if o.product and o.product.lower() not in (r.get('product') or '').lower():
            continue
        if (r.get('rating') or 0) < o.min_rating:
            continue
        text = f"{r.get('title') or ''}. {r.get('body') or ''}"
        for sentence in re.split(r'(?<=[.!?])\s+', text):
            m = TIME.search(sentence)
            if not m or NOT_RESULT.search(sentence):
                continue
            tags = [k for k, p in outcomes.items() if p.search(sentence)]
            if not tags:
                continue
            d = days(m)
            stage = next(s for s, lo, hi in STAGES if lo <= d < hi)
            kept.append({'id': r.get('id'), 'product': r.get('product'), 'stage': stage, 'phrase': m.group(0),
                         'sentence': sentence.strip(), 'outcomes': tags, 'photo': bool(r.get('photos'))})
            break
    table = {}
    for s, _, _ in STAGES:
        xs = [k for k in kept if k['stage'] == s]
        table[s] = {'reviews': len(xs), 'with_photo': sum(k['photo'] for k in xs),
                    'outcomes': collections.Counter(t for k in xs for t in k['outcomes']).most_common()}
    out = {'reviews_read': len(reviews), 'reviews_kept': len(kept), 'stages': table, 'kept': kept}
    json.dump(out, open(o.out, 'w'), indent=1, ensure_ascii=False)
    print(f"{len(kept)} of {len(reviews)} reviews state when it worked")
    for s, v in table.items():
        print(f"  {s:<11} {v['reviews']:>4}  " + ', '.join(f'{k} {n}' for k, n in v['outcomes'][:3]))

if __name__ == '__main__':
    sys.exit(main())
