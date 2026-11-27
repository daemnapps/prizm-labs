#!/usr/bin/env python3
"""Search keywords from an avatar's own words — any brand, any avatar.

    python3 machine/keywords.py --brand <brand> --avatar <avatar> [--sub <sub stem>] [--top 25]

Reads every row in brands/<brand>/core-avatars/<avatar>/language/ (and the
sub-avatar's own language/ folder when --sub is given), counts the 1-3 word
phrases the avatar repeats, and prints them ranked. There is no seed list:
the words come from the bank, never from this file. Read-only.

Anchors: the avatar's own desire statement (its profile, and the sub-avatar
card when --sub is given), read by the research gatherer's desire_words().
Phrases are ranked only if they carry an anchor, so "love" and "order" drop
out and "dark spots" stays. With no desire statement on file, it says so
and ranks the raw phrases instead.
"""
import argparse, collections, glob, json, os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "brandpath"))
import brandpath  # noqa: E402

STOP = set("""a an the and or but if so of to in on at by for with from as is are was were be been
being it its it's this that these those i me my mine we our you your he she her his they them their
im i'm ive i've id i'd dont don't didnt didn't cant can't wont won't just really very so too also
not no yes do does did have has had get got go going went would could should will can may might
what which who when where why how all any some more most much many one two than then there here
about up out over into after before again only own same such like even still back off now well
make made use used using thing things way lot bit thank thanks please oh ok okay yeah
product products buying buy bought next received great good works work love""".split())

def root():
    return str(brandpath.repo())

# The avatar's own desire statement ("Core desire ... "quote""), as search words. Read here, not imported
# from another component's internals (research-gatherer's contract does not offer it).
DESIRE_RE = re.compile(r"Core desire[^\"]*\"([^\"]+)\"", re.I)
DESIRE_STOP = {"i", "want", "to", "a", "the", "and", "my", "for", "that", "so", "can", "with", "of", "in", "on",
               "it", "without", "this", "his", "her", "their", "them", "me", "actually", "really", "stop", "keep",
               "get", "have", "has", "from", "just"}

def desire_words(text, limit=6):
    m = DESIRE_RE.search(text or "")
    out, seen = [], set()
    for w in re.findall(r"[A-Za-zÀ-ÿ']{4,}", m.group(1) if m else ""):
        lw = w.lower()
        if lw in DESIRE_STOP or lw in seen:
            continue
        seen.add(lw)
        out.append(lw)
        if len(out) >= limit:
            break
    return out

def rows(brand, avatar, sub):
    base = str(brandpath.brand_path(brand, "core-avatars", avatar, root=Path(root()) / "brands"))
    if not os.path.isdir(base):
        raise SystemExit(f"no avatar folder: {base}")
    dirs = [os.path.join(base, "language")]
    if sub:
        dirs = [os.path.join(base, "sub-avatars", sub, "language")] + dirs
    for d in dirs:
        for f in glob.glob(os.path.join(d, "**", "*.json"), recursive=True):
            try:
                data = json.load(open(f))
            except Exception:
                continue
            for e in (data.get("entries") or []) if isinstance(data, dict) else []:
                if sub and d == dirs[-1] and e.get("sub") not in (None, sub):
                    continue
                t = e.get("text") or e.get("quote") or e.get("verbatim") or ""
                if t:
                    yield t

def phrases(text):
    words = [w for w in re.findall(r"[a-z][a-z'-]+", text.lower())]
    out = set()
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            g = words[i:i + n]
            if g[0] in STOP or g[-1] in STOP or all(w in STOP for w in g):
                continue
            if n == 1 and len(g[0]) < 4:
                continue
            out.add(" ".join(g))
    return out

def anchors(brand, avatar, sub):
    base = str(brandpath.brand_path(brand, "core-avatars", avatar, root=Path(root()) / "brands"))
    files = [os.path.join(base, "profile.md")]
    if sub:
        files += glob.glob(os.path.join(base, "sub-avatars", f"*{sub}*.md"))
    words = []
    for f in files:
        if os.path.isfile(f):
            words += desire_words(open(f).read(), limit=10)
    return sorted(set(words))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--sub")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--min-rows", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    import importlib.util as _u, pathlib as _pl
    _s = _u.spec_from_file_location("profile_arg", next(q for q in _pl.Path(__file__).resolve().parents if q.name == "components") / "naming" / "profile_arg.py")
    _PA = _u.module_from_spec(_s); _s.loader.exec_module(_PA)                                   # --profile <avatar>[_<sub>][_<demographic>] (naming/PEOPLE.md)
    a = ap.parse_args(_PA.expand(None, has=("avatar", "sub")))
    texts = list(rows(a.brand, a.avatar, a.sub))
    c = collections.Counter()
    for t in texts:
        c.update(phrases(t))          # counted once per row: how many people say it
    stems = anchors(a.brand, a.avatar, a.sub)
    def hit(w):
        return any(w == x or w == x + "s" or w + "s" == x or w == x + "ed" or w + "d" == x
                   for x in stems)
    # the brand's own product names are what we sell, not what she searches for
    prod = str(brandpath.brand_path(a.brand, "products", root=Path(root()) / "brands"))
    ours = {d.replace("-", " ") for d in os.listdir(prod)} if os.path.isdir(prod) else set()
    ours |= {" ".join(o.split()[-2:]) for o in ours}
    if stems:
        c = collections.Counter({p: n for p, n in c.items()
                                 if any(hit(w) for w in p.split())
                                 and not any(o and o in p for o in ours)})
    ranked = [(p, n) for p, n in c.most_common() if n >= a.min_rows]
    # a longer phrase said as often as its parts beats them
    keep = []
    for p, n in ranked:
        if any(p != q and p in q and m >= n * 0.8 for q, m in keep):
            continue
        keep.append((p, n))
    keep = keep[:a.top]
    if a.json:
        print(json.dumps({"brand": a.brand, "avatar": a.avatar, "sub": a.sub,
                          "rows": len(texts), "anchors": stems, "phrases": keep}, indent=1))
    else:
        print(f"{a.brand} · {a.avatar}{' · ' + a.sub if a.sub else ''} · {len(texts)} rows · "
              f"anchors from its own desire statement: {', '.join(stems) or 'NONE ON FILE (raw ranking)'}")
        for p, n in keep:
            print(f"{n:5}  {p}")

if __name__ == "__main__":
    main()
