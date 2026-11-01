#!/usr/bin/env python3
"""Tag the audience's own call-to-action words — `keyword-cta` — by rule, no model.

    python3 tools/keyword_cta.py --brand B --dry-run        # what would be tagged, nothing written
    python3 tools/keyword_cta.py --brand B                  # propose the tags; the research gatherer applies them
    python3 tools/keyword_cta.py --brand B --propose-only   # the proposal under runs/, nothing applied

The tag (brands/language-schema.md, "The audience's own call-to-action
words, and repeats", ruled 2026-09-28): "one short word or phrase the
audience repeats to ask for the thing" — "Recipe", "link?", "price?". The
rule, read straight off that definition:
  - a COMMENT (source type `comment`, or a source id of kind `post`);
  - SHORT: one word or a short phrase — at most 4 words once punctuation
    and emoji are set aside;
  - REPEATED: the same words (case and punctuation aside) on 2 or more rows
    of the SAME source;
  - ASKING FOR THE THING: the row sits in the lead lane (`leads.json`) or its
    words point there (`lane_words: "lead"`).
Every row that meets all four gets `keyword-cta` added to its `use`; nothing
else on the row changes, and a row already tagged is left alone.

`brands/` is read-only to machines (decision-log 2026-09-17): the tags are a
PROPOSAL under runs/language-layer/<brand>/keyword-cta-<date>/, applied by the
research gatherer (`gather.py apply --proposal …`).
"""
import argparse, collections, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import proposal as P  # noqa: E402
sys.path.append(str(Path(__file__).resolve().parent))
from label import open_run, bank_files, finish  # noqa: E402

TAG = "keyword-cta"
MAX_WORDS = 4
MIN_REPEATS = 2


def words(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", (t or "").lower())).strip()


def is_comment(e):
    s = e.get("source") or {}
    return (s.get("type") or "").lower() == "comment" or str(s.get("id") or "").startswith("post_")


def is_lead(f, e):
    return f.name == "leads.json" or e.get("lane_words") == "lead"


def uses(e):
    u = e.get("use")
    return list(u) if isinstance(u, list) else ([u] if u else [])


def find(brand, avatar=None):
    """[(file, index, entry, words)] that meet the rule."""
    groups = collections.defaultdict(list)
    for f, d in bank_files(brand, avatar):
        for i, e in enumerate(d.get("entries") or []):
            w = words(e.get("text"))
            if not e.get("id") or not w or len(w.split()) > MAX_WORDS or not is_comment(e):
                continue
            s = e.get("source") or {}
            groups[(w, s.get("id") or s.get("name"))].append((f, i, e))
    out = []
    for (w, src), rows in groups.items():
        if len(rows) < MIN_REPEATS:
            continue
        out += [(f, i, e, w) for f, i, e in rows if is_lead(f, e)]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--propose-only", action="store_true")
    ap.add_argument("--run", default=None)
    a = ap.parse_args(argv)
    hits = find(a.brand, a.avatar)
    new = [(f, i, e, w) for f, i, e, w in hits if TAG not in uses(e)]
    said = collections.Counter(w for *_, w in hits)
    print(f"{len(hits)} rows meet the rule · {len(new)} not yet tagged · "
          + ", ".join(f"{w!r} ×{n}" for w, n in said.most_common(10)))
    if a.dry_run or not new:
        return 0
    prop = P.Proposal(a.brand, "language-layer tools/keyword_cta.py", open_run(a.brand, "keyword-cta", a.run))
    for f, i, e, w in new:
        prop.row(f, i, e, use=uses(e) + [TAG])
    return finish(prop, a, dict(rule=f"comment · ≤{MAX_WORDS} words · same words ≥{MIN_REPEATS}× on one source · lead lane",
                                rows_meeting_rule=len(hits), rows_tagged=len(new)),
                  [f"{w!r} ×{n}" for w, n in said.most_common(12)])


if __name__ == "__main__":
    sys.exit(main())
