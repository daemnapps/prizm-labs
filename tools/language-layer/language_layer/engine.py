#!/usr/bin/env python3
"""Query the language layer instead of reading it.

The banks are ~14.6k sourced rows, each tagged with what it IS (`use`), what
it is ABOUT (`topics`), who said it (`speaker`, `funnel`) and how loud it was
(`signal`). Loading a file and truncating at a byte budget throws all of that
away: which real customer sentences the copy sees ends up decided by file
order.

So: rows in, filtered rows out, per stage. A hook stage asks for the rows
people actually open with; a close asks for objections and refund reasons.
Every row keeps its provenance, because a paid panellist and a refunding
customer are not the same evidence.

    python3 tools/language-layer/query_language.py --brand <b> --avatars
    python3 tools/language-layer/query_language.py --brand <b> \
        --stage hooks --profile <chain>.json

ONE HOME (LL-1, 2026-09-01). This engine used to exist as two drifted copies
— `tools/video-teardown/machine/language.py` and the copy lab's — 103
diff lines apart, with the render fix living only in one of them. Both are now
thin shims over this file. The convergence was ruled: the copy lab's version
is the base (it was the most recent; the drift was staleness), with the video
machine's environment tolerance folded in, because that machine still needs it
to run.

Brand-agnostic (workspace rule 7) and brand-blind by construction: a bank path
arrives as an argument or is found by SHAPE across the roots below. The word
"brand" names a lookup key here, never a behaviour branch. Banks read from
`brands/<brand>/core-avatars/*/language/` — the real brands tree, rule-9
(brand home).

NO STAGE MAP LIVES HERE. What a stage is looking for is a per-chain
DEFINITION, not engine: the video chain's map and the copy chain's map differ
legitimately (the copy chain has a `render` stage; the video chain does not),
and baking either one in is what would make this a chain's engine rather than
the org's. Callers hand it in — `configure(stage_use=...)`, a `for_stage`
argument, or a `--profile` file.

Reads no credential and touches no network, at import time or ever.
"""

import argparse
import json, re
import os
from pathlib import Path

# Where the workspace sits when nobody says: `AI_WORKSPACE` if set, else the
# checkout this file sits in (<ws>/tools/language-layer/language_layer/).
# Never a home-folder guess, so the same code resolves the same tree on any
# machine and for any person (brand-finder's `workspace()` rule, restated here
# because this engine is stdlib-only and imports no other component). A host
# that knows better hands its own root to `configure(workspace=...)` — both
# shims do, which is how each machine keeps resolving the tree it always did.
def _default_workspace():
    named = os.environ.get("AI_WORKSPACE")
    return Path(os.path.expanduser(named)) if named else Path(__file__).resolve().parents[2].parent


WORKSPACE = _default_workspace()

TIER_RANK = {"gold": 0, "silver": 1, "house": 2, "community": 3}

# Per-chain settings, set by the host at import. Private on purpose: this
# module is not a home for definitions, it is the code that executes them.
_STAGE_USE = {}
_WIDEN = "once"
_TITLE = "Customer language for this stage"


# Where a brand's banks live is not this module's business to assume. It
# looks for the shape — brands/<brand>/core-avatars — across the
# roots it knows about, and takes the first tree that actually has it. That
# is what lets the same file serve every chain, survive the banks moving, and
# work for a brand nobody has told it about.
_ROOTS = [
    lambda: Path(os.environ["LANGUAGE_ROOT"]).expanduser() if os.environ.get("LANGUAGE_ROOT") else None,
    lambda: WORKSPACE / "lab" / "damon",
    lambda: WORKSPACE,
    lambda: WORKSPACE / "components",
]


def configure(workspace=None, stage_use=None, widen=None, title=None,
              roots=None):
    """The host seams. Every one is optional; an unset seam keeps the default.

    workspace   this host's workspace root (its `paths.WORKSPACE`, usually)
    stage_use   this chain's stage -> evidence-types map. A DEFINITION —
                the chain owns it, this engine only executes it
    widen       how far to relax filters when a stage's rows are thin:
                "once" (drop topics if nothing matched) or "ladder" (relax
                topics, then funnel, until a floor is met, and SAY SO in the
                header). Per-chain, same species as the map above
    title       the header line a stage reads. Per-chain presentation
    roots       replaces the root probe list wholesale
    """
    global WORKSPACE, _STAGE_USE, _WIDEN, _TITLE, _ROOTS
    if workspace is not None:
        WORKSPACE = Path(workspace)
    if stage_use is not None:
        _STAGE_USE = stage_use
    if widen is not None:
        _WIDEN = widen
    if title is not None:
        _TITLE = title
    if roots is not None:
        _ROOTS = list(roots)


# The banks have lived at two shapes: brands/<brand>/avatars/core-avatars/ and,
# after the 2026-08-30 restructure, brands/<brand>/core-avatars/. Both machines
# went blind the day the folders moved — an empty roster reads exactly like a
# brand with no banks, so the chain ran on with no language and said nothing.
# Accept either shape rather than pin one, and the next move costs nothing.
def bank_dir(cand):
    """Where this brand's core avatars sit, whichever layout is in use."""
    for rel in (("core-avatars",), ("avatars", "core-avatars")):
        d = Path(cand).joinpath(*rel)
        if d.is_dir():
            return d
    return Path(cand) / "core-avatars"


def brand_dir(brand, root=None):
    """The brand's tree — named if given, else found by its shape."""
    if root:
        return Path(root) / "brands" / brand
    for get in _ROOTS:
        try:
            r = get()
        except Exception:
            continue
        if not r:
            continue
        cand = Path(r) / "brands" / brand
        if bank_dir(cand).is_dir():
            return cand
    return WORKSPACE / "brands" / brand      # so the failure names a real path


def avatar_root(brand, root=None):
    """The bank directory for a brand, in one call.

    Kept because the copy lane uses it as a PROBE — `avatar_root(brand, cand)`
    over candidate trees, taking the first that answers `.is_dir()`. A named
    root is therefore never second-guessed: it resolves under that tree or it
    does not resolve.
    """
    return bank_dir(brand_dir(brand, root))


def avatars(brand, root=None):
    """Every core avatar this brand has, with row counts. Brands have more
    than one — which to write as is a decision, not a default."""
    d = bank_dir(brand_dir(brand, root))
    out = []
    if not d.is_dir():
        return out
    for a in sorted(x for x in d.iterdir() if x.is_dir()):
        rows = load(brand, a.name, root)
        funnels = {}
        for r in rows:
            funnels[r.get("funnel")] = funnels.get(r.get("funnel"), 0) + 1
        prof = a / "profile.md"
        out.append(dict(key=a.name, rows=len(rows), funnels=funnels,
                        has_profile=prof.is_file(),
                        subs=[p.stem for p in sorted((a / "sub-avatars").glob("*.md"))]
                        if (a / "sub-avatars").is_dir() else []))
    return out


def load(brand, avatar=None, root=None):
    """Every row for a brand, or for one avatar. Provenance travels."""
    base = bank_dir(brand_dir(brand, root))
    if not base.is_dir():
        return []
    dirs = [base / avatar] if avatar else [d for d in base.iterdir() if d.is_dir()]
    rows = []
    for d in dirs:
        # The avatar's own bank, plus every sub-avatar's own folder beside its
        # card (`sub-avatars/<sub-file-stem>/language/`) — one home per
        # sub-avatar, the owner 2026-09-18. A sub folder's rows default their
        # `sub` to the folder's slug when the file does not say.
        banks = [(d / "language", None)]
        subs = d / "sub-avatars"
        if subs.is_dir():
            for sd in sorted(x for x in subs.iterdir() if x.is_dir()):
                banks.append((sd / "language", sd.name))
        for lang, sub_default in banks:
            if not lang.is_dir():
                continue
            for f in sorted(lang.rglob("*.json")):
                if USED_DIR in f.relative_to(lang).parts:
                    continue                 # the used lane is a record, not bank rows
                try:
                    data = json.loads(f.read_text())
                except Exception:
                    continue
                for e in data.get("entries") or []:
                    e.setdefault("avatar", data.get("avatar") or d.name)
                    e.setdefault("funnel", data.get("funnel"))
                    if sub_default and not e.get("sub"):
                        e["sub"] = data.get("sub") or re.sub(r"^sub-\d+-", "", sub_default)
                    e["_file"] = f.name
                    rows.append(e)
    return rows


# THE USED LANE (Ruled 2026-09-28): "anytime any of that language is used, we
# clearly mark it as used in X asset … index and search between things that
# have been used and things that have not been used, and then … performance
# metrics on what has been used." One folder beside the bank —
# `<avatar>/language/used/` (and the same under a sub-avatar's own language
# folder) — one file per asset a chain wrote. A bank row is never edited: its
# `status` stays a person's call. Shape: brands/language-schema.md, "The used lane".
USED_DIR = "used"
RETIRED = ("dropped", "inactive", "retired", "burned")


def _lang_dirs(brand, avatar=None, root=None):
    base = bank_dir(brand_dir(brand, root))
    if not base.is_dir():
        return []
    dirs = [base / avatar] if avatar else [d for d in base.iterdir() if d.is_dir()]
    out = []
    for d in dirs:
        out.append(d / "language")
        subs = d / "sub-avatars"
        if subs.is_dir():
            out += [sd / "language" for sd in sorted(x for x in subs.iterdir() if x.is_dir())]
    return out


def _proposal_files(brand, avatar=None, root=None):
    """Open used-lane proposals a machine wrote under runs/ (K2 (brands write wall),
    SI-97 (brand research proposals)) —
    runs/video-writing/<brand>/<slug>/proposals/language-used/<avatar>/*.json."""
    base = (Path(root) if root else WORKSPACE) / "runs" / "video-writing" / brand
    return sorted(base.glob(f"*/proposals/language-used/{avatar or '*'}/*.json"))


def load_used(brand, avatar=None, root=None):
    """Every used-lane record: one per (row, asset) — the row id, the words,
    where it was used and in what. Newest file last. Open proposals under runs/
    count too (`_proposal: True`), unless a person already committed the same
    file into the brand's used lane — the accepted copy wins."""
    recs = []
    for lang in _lang_dirs(brand, avatar, root):
        u = lang / USED_DIR
        if not u.is_dir():
            continue
        for f in sorted(u.glob("*.json")):
            try:
                data = json.loads(f.read_text())
            except Exception:
                continue
            for e in data.get("used") or []:
                e = dict(e)
                e.setdefault("asset", data.get("asset"))
                e.setdefault("run", data.get("run"))
                e.setdefault("chain", data.get("chain"))
                e["_file"] = f.name
                recs.append(e)
    banks = bank_dir(brand_dir(brand, root))
    for f in _proposal_files(brand, avatar, root):
        if (banks / f.parent.name / "language" / USED_DIR / f.name).exists():
            continue                                 # accepted copy wins; no double count
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        for e in data.get("used") or []:
            e = dict(e)
            e.setdefault("asset", data.get("asset"))
            e.setdefault("run", data.get("run"))
            e.setdefault("chain", data.get("chain"))
            e["_file"] = f.name
            e["_proposal"] = True
            recs.append(e)
    return recs


def used_ids(brand, avatar=None, root=None):
    """The ids of every bank row that has been used in anything."""
    return {r.get("row_id") for r in load_used(brand, avatar, root) if r.get("row_id")}


def uses(row):
    """A row's use tags, always a list — a single tag or a list, blanks dropped."""
    u = row.get("use")
    return [x for x in (u if isinstance(u, list) else [u]) if x]


_uses = uses  # old private name, kept for callers


def _same(text):
    """Two lines are the same line when they match ignoring case, punctuation
    and emoji."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", (text or "").lower())).strip()


def query(rows, use=None, topics=None, funnel=None, speaker=None,
          contains=None, exclude_assumed=False, limit=40, used=None,
          spent=None, awareness=None, area=None, feedback_stage=None,
          shown=None):
    """Filter and rank. Ranking matters as much as filtering: with hundreds
    of candidate rows, which forty a stage sees is the whole difference
    between real language and arbitrary language.

    used   None/"any" — ignore the used lane · "no" — only rows never used ·
           "yes" — only rows already used. `spent` is the set of used ids
           (`used_ids()`); without it "no"/"yes" have nothing to test.
    Rows retired or burned by a person never come back (status is a person's call).

    shown  {row id: times handed to a stage before} — the exposure record
           (the owner, 2026-10-05: "over time we have some level of variance and
           variety with our copywriting"). Within the same tag rank, a row
           shown fewer times comes first, so runs rotate through the bank
           instead of every run reading the same most-liked forty.

    awareness  a level (or list of levels) the row's `awareness.level` must
               match — the language bank upgrade, 2026-09-28. Rows not yet
               labelled are kept, ranked after the labelled matches, so a bank
               mid-backfill still answers.

    area / feedback_stage  rows from the brand's own feedback forms carry
               `feedback: {stage, areas}` (components/feedback-forms,
               2026-09-29). `area` keeps rows whose question serves that
               business area (marketing, product, operations, customer-service,
               customer-experience, website); `feedback_stage` keeps rows from
               that customer stage. Either one keeps feedback-form rows only."""
    want_use = list(use or [])
    want_top = {t.lower() for t in (topics or [])}
    spent = spent or set()
    want_aw = {awareness} if isinstance(awareness, str) else set(awareness or [])
    # THE SAME WORDS SAID MANY TIMES (2026-09-28: 55 people commented "Recipe"
    # on one ad). Identical lines collapse into one, carrying how many times
    # they were said; volume ranks like likes do.
    said = {}
    for r in rows:
        k = _same(r.get("text"))
        said[k] = said.get(k, 0) + 1
    seen = set()
    out = []
    for r in rows:
        if r.get("status") in RETIRED:
            continue
        k = _same(r.get("text"))
        if k in seen:
            continue
        if used == "no" and r.get("id") in spent:
            continue
        if used == "yes" and r.get("id") not in spent:
            continue
        if exclude_assumed and r.get("attribution") == "assumed":
            continue
        if funnel and r.get("funnel") != funnel:
            continue
        if speaker and r.get("speaker") != speaker:
            continue
        if contains and contains.lower() not in (r.get("text") or "").lower():
            continue
        if area or feedback_stage:
            fb = r.get("feedback") if isinstance(r.get("feedback"), dict) else {}
            if area and area not in (fb.get("areas") or []):
                continue
            if feedback_stage and fb.get("stage") != feedback_stage:
                continue
        aw = ((r.get("awareness") or {}).get("level") if isinstance(r.get("awareness"), dict) else None)
        if want_aw and aw and aw not in want_aw:
            continue
        rus = _uses(r)
        # with an awareness asked for, a labelled match stands in for a tag match
        if want_use and not any(u in want_use for u in rus) and not (want_aw and aw in want_aw):
            continue
        rt = {t.lower() for t in (r.get("topics") or [])}
        if want_top and not (rt & want_top):
            continue
        # rank: the stage's primary tags first, then topic overlap, then how
        # loud the row was, then measured over assumed
        use_rank = min((want_use.index(u) for u in rus if u in want_use),
                       default=len(want_use))
        seen.add(k)
        r["_repeats"] = said.get(k, 1)
        sig = r.get("signal") or {}
        try:
            n = int(sig.get("likes") or sig.get("count") or 0)
        except (TypeError, ValueError):
            n = 0
        loud = -max(n, r["_repeats"])
        tier = TIER_RANK.get(sig.get("tier"), 9)
        assumed = 1 if r.get("attribution") == "assumed" else 0
        unlabelled = 1 if (want_aw and not aw) else 0
        times = (shown or {}).get(r.get("id"), 0)
        out.append(((unlabelled, use_rank, -len(rt & want_top), times, tier, loud, assumed), r))
    out.sort(key=lambda x: x[0])
    return [r for _, r in out[:limit]]


def render(rows, header=""):
    """Rows as a stage reads them — the words, and where they came from."""
    if not rows:
        return "(no rows matched — say so rather than inventing one)"
    out = [header] if header else []
    for r in rows:
        src = (r.get("source") or {})
        bits = [src.get("name") or "source not recorded"]
        if src.get("type"):
            bits.append(src["type"])
        if src.get("date"):
            bits.append(src["date"])
        sig = r.get("signal") or {}
        if sig.get("likes"):
            try:
                bits.append(f"{int(sig['likes']):,} likes")
            except (TypeError, ValueError):
                bits.append(f"{sig['likes']} likes")
        if sig.get("tier"):
            bits.append(sig["tier"])
        if r.get("attribution") == "assumed":
            bits.append("ATTRIBUTION ASSUMED")
        who = r.get("speaker") or "unattributed"
        tags = ", ".join(_uses(r)) or "untagged"
        rid = f'[{r["id"]}] ' if r.get("id") else ""
        if (r.get("_repeats") or 1) > 1:
            bits.insert(0, f"said {r['_repeats']}× in this bank")
        out.append(f'- {rid}"{(r.get("text") or "").strip()}"')
        out.append(f'  _{who} · {tags} · {" · ".join(bits)}_')
    return "\n".join(out)


def for_stage(brand, stage, avatar=None, funnel=None, topics=None,
              limit=40, root=None, stage_use=None, widen=None, title=None,
              used=None, awareness=None, area=None, feedback_stage=None,
              shown=None, proven_share=0.25):
    """The rows one stage should see. The whole point of the module.

    used="fresh" (2026-10-05): never-used rows first, ranked so the rows
    earlier runs were shown least come first (`shown`), plus a proven slice —
    up to `proven_share` of the set — of rows already used in an asset.
    Proven words still work; they just stop crowding out the rest.

    `stage_use`, `widen` and `title` default to whatever the host configured;
    they are per-chain definitions, so a caller may also pass them per call.
    """
    smap = _STAGE_USE if stage_use is None else stage_use
    use = smap.get(stage)
    widen = _WIDEN if widen is None else widen
    title = _TITLE if title is None else title

    rows = load(brand, avatar, root)
    relaxed = []
    fresh = used == "fresh"
    spent = used_ids(brand, avatar, root) if used in ("no", "yes", "fresh") else None
    n_proven = int(limit * proven_share) if fresh else 0
    def q(rows, limit=limit, **kw):      # every pass below keeps the used filter
        if fresh:
            new = query(rows, used="no", spent=spent, awareness=awareness, area=area,
                        feedback_stage=feedback_stage, shown=shown, limit=limit, **kw)
            old = query(rows, used="yes", spent=spent, awareness=awareness, area=area,
                        feedback_stage=feedback_stage, shown=shown, limit=limit, **kw)
            k_old = min(len(old), n_proven)          # the proven slice
            k_new = min(len(new), limit - k_old)     # fresh fills the rest
            k_old = min(len(old), limit - k_new)     # proven tops up a thin fresh set
            return new[:k_new] + old[:k_old]
        return query(rows, used=used, spent=spent, awareness=awareness,
                     area=area, feedback_stage=feedback_stage, shown=shown, limit=limit, **kw)
    picked = q(rows, use=use, topics=topics, funnel=funnel, limit=limit)
    if widen == "ladder":
        # Narrow first, then widen only as far as needed. A funnel can be thin
        # — a bank with 13k customer rows can hold 34 prospect rows — and a
        # stage handed three rows will fill the gap by inventing. Each
        # relaxation is recorded, because "we widened" is a fact about the
        # bank the reader should see, not something to do quietly.
        MIN = max(8, limit // 4)
        if len(picked) < MIN and topics:
            picked = q(rows, use=use, funnel=funnel, limit=limit)
            relaxed.append("topics")
        if len(picked) < MIN and funnel:
            picked = q(rows, use=use, topics=topics, limit=limit)
            relaxed.append("funnel")
        if len(picked) < MIN:
            picked = q(rows, use=use, limit=limit)
            relaxed = ["topics", "funnel"]
    else:                                # "once" — topic filter too narrow
        if not picked and topics:
            picked = q(rows, use=use, funnel=funnel, limit=limit)
    head = (f"# {title} — {stage}\n"
            f"_{len(picked)} rows, drawn from {len(rows)} for "
            f"{avatar or 'all avatars'}"
            + (f", funnel: {funnel}" if funnel else "")
            + (f", topics: {', '.join(topics)}" if topics else "")
            + (f", never used before ({len(spent)} rows already used are held back)"
               if used == "no" else "")
            + (f", already used only" if used == "yes" else "")
            + (f", {sum(1 for r in picked if r.get('id') not in (spent or set()))} never used "
               f"+ {sum(1 for r in picked if r.get('id') in (spent or set()))} proven (used before), "
               f"least-shown first" if fresh else "")
            + (f", spoken at the {awareness} level first" if awareness else "")
            + (f", feedback-form rows serving {area}" if area else "")
            + (f", from the {feedback_stage} feedback stage" if feedback_stage else "") + "._\n"
            + (f"\n**Widened:** too few rows matched, so the "
               f"{' and '.join(relaxed)} filter was relaxed to fill this set. "
               f"Treat the fit as looser than the header suggests.\n"
               if relaxed else "")
            + "**These are real sentences real people said.** Use their words; "
            "do not paraphrase them into ours. Provenance is on every row — a "
            "paid panellist and a refunding customer are not equal evidence. "
            "The id in [brackets] is how you cite a row you used.\n")
    return render(picked, head)


def topics_of(brand, root=None, top=40):
    c = {}
    for r in load(brand, None, root):
        for t in r.get("topics") or []:
            c[t] = c.get(t, 0) + 1
    return sorted(c.items(), key=lambda x: -x[1])[:top]


def load_profile(path):
    """A chain profile: its stage map, and how it wants thin sets handled.

    Either the bare map — `{"hooks": ["hook", ...], ...}` — or the full shape
    `{"stage_use": {...}, "widen": "ladder", "title": "..."}`. Both are
    per-chain DEFINITIONS; this function only reads them.
    """
    doc = json.loads(Path(path).read_text())
    if isinstance(doc, dict) and "stage_use" in doc:
        return (doc.get("stage_use") or {}, doc.get("widen"), doc.get("title"))
    return (doc or {}, None, None)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--root", default=None)
    ap.add_argument("--avatar", default=None)
    ap.add_argument("--funnel", default=None)
    stages = sorted(_STAGE_USE)
    ap.add_argument("--stage", default=None, choices=stages or None)
    ap.add_argument("--topics", default=None)
    ap.add_argument("--avatars", action="store_true")
    ap.add_argument("--topic-list", action="store_true")
    ap.add_argument("--limit", type=int, default=25)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--used", action="store_true",
                   help="only rows already used in an asset")
    g.add_argument("--unused", action="store_true",
                   help="only rows never used in any asset")
    ap.add_argument("--used-log", action="store_true",
                    help="list the used lane: every row, the asset it went into, where")
    ap.add_argument("--profile", default=None,
                    help="this chain's stage map (json); see load_profile")
    ap.add_argument("--awareness", default=None,
                    help="rows spoken at this awareness level first (unlabelled rows follow)")
    ap.add_argument("--area", default=None,
                    help="feedback-form rows only, whose question serves this business area "
                         "(marketing, product, operations, customer-service, customer-experience, website)")
    ap.add_argument("--feedback-stage", default=None,
                    help="feedback-form rows only, from this customer stage (e.g. new-customer, churned-refund)")
    a = ap.parse_args(argv)
    root = Path(a.root).expanduser() if a.root else None

    if a.avatars:
        for av in avatars(a.brand, root):
            print(f"  {av['key']:34} {av['rows']:6,} rows  {av['funnels']}")
            for s in av["subs"]:
                print(f"      sub · {s}")
        return
    if a.used_log:
        for u in load_used(a.brand, a.avatar, root):
            res = u.get("results") or {}
            money = (f"  spend {res.get('spend')} · purchases {res.get('purchases')}"
                     if res else "")
            print(f"  {u.get('row_id',''):22} {u.get('where',''):4} {u.get('asset') or u.get('run')}"
                  f"  \"{(u.get('text') or '')[:60]}\"{money}")
        return
    if a.topic_list:
        for t, n in topics_of(a.brand, root):
            print(f"  {n:6,}  {t}")
        return
    smap = wdn = ttl = None
    if a.profile:
        smap, wdn, ttl = load_profile(a.profile)
    print(for_stage(a.brand, a.stage or "injection", a.avatar, a.funnel,
                    a.topics.split(",") if a.topics else None, a.limit, root,
                    stage_use=smap, widen=wdn, title=ttl,
                    used="yes" if a.used else "no" if a.unused else None,
                    awareness=a.awareness, area=a.area, feedback_stage=a.feedback_stage))


if __name__ == "__main__":
    main()
