#!/usr/bin/env python3
"""research-gatherer — the query-the-open-internet engine, as a component.

Two jobs (plan.md Part C / C2 of the Schwartz build):

1. **`inputs(st, chain_profile)`** — a Schwartz-shaped research packet for
   ONE run: forums pulled for the avatar's named rooms, comments on the
   swiped post, and (when the caller hands in a `chain_profile`) the
   language bank's own stage tags. Returns `{"research": <markdown>}` — the
   same shape `~var` callers already expect (the `creator_profile.py`
   precedent: `inputs(st)` returning a dict a chain binds by name). NEVER
   RAISES: a research gap is a section that says `[UNFILLED: why]`, never a
   stopped chain.

2. **`deep_for(...)` / `pick_thinnest(...)`** — the C2 deep-research
   trigger. Pulls for ONE sub-avatar using that file's OWN named rooms +
   desire words + the Schwartz research questions, and FILES verbatim rows
   — with permalinks — into that sub-avatar's own language bank. Brand- and
   chain-agnostic: it reads `brands/<brand>/core-avatars/**` and nothing
   else names a brand, avatar or room.

**Ships no stage map** (components rule, LL-1 precedent): which language
STAGE_USE keys a chain wants queried for its `language.md` section is a
per-chain definition. A caller hands it in as `chain_profile`:

    chain_profile = {
        "language_stages": ["depth", "spice"],       # STAGE_USE keys to query
        "language_for_stage": <a for_stage(...) callable>,   # that chain's own
        "run_dir": lambda st: Path(...) or None,      # where <run>/research/ goes
    }

Any key can be omitted — the section it feeds records `[UNFILLED: why]`
rather than guessing. `components/video-teardown/machine/research.py` and
any sibling chain's shim hand in their own map; this engine holds none.

Reuses rather than re-implements (workspace convention — CC-3):
  - `components/apify/reddit.py` — the Reddit door: its actor,
    its flags, its cap, its 403 handling. Driven through its own CLI
    contract (`main()` + `sys.argv`).
  - `components/apify/apify.py` — the shared Apify layer (token,
    spare-account fallback) and its per-platform comment actors.

Machine-agnostic (components rule 8): no credential read at import time,
`workspace` resolved via `configure()` or the default, every write under a
declared output folder. Every pull is capped (`research.json`) and prints
what it spent; forum pulls cache 14 days per (brand, avatar, sub, words,
rooms), comment pulls per source_url, so repeat runs on the same avatar
don't re-spend. No key / 403 / missing actor never raises.
"""
import hashlib, json, os, re, sys, time
from datetime import date
from pathlib import Path

from . import gates as G                        # the gates + the one shared hold()
# (the element library it asks lives at components/elements — see gates.py)

HERE = Path(__file__).resolve().parent          # .../research-gatherer/research_gatherer
ROOT = HERE.parent                              # .../research-gatherer


def _default_workspace():
    """AI_WORKSPACE when it names a real folder, else the checkout this file
    sits in (found by walking up), else the old fixed home. Rollout 2026-09-20:
    the fixed home made a worktree read and write the MAIN checkout."""
    env = os.environ.get("AI_WORKSPACE")
    if env and Path(env).is_dir():
        return Path(env)
    for d in HERE.parents:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    return Path.home() / "Projects" / "workspace"


WORKSPACE = _default_workspace()


def configure(workspace=None):
    """The one host seam. `workspace` is the caller's own `paths.WORKSPACE`
    (or equivalent) — everything else is found relative to it."""
    global WORKSPACE
    if workspace is not None:
        WORKSPACE = Path(workspace)


def _reddit_tool():
    return WORKSPACE / "components" / "apify" / "reddit.py"


def _swipe_apify():
    """The Apify layer, `components/apify/apify.py` — a component since
    2026-09-22."""
    return WORKSPACE / "components" / "apify" / "apify.py"


def _doctrine_questions_path():
    return WORKSPACE / "components" / "marketing-doctrine" / "frameworks.json"


def _cache_root():
    # Run records never live inside a component (CLAUDE.md §1,
    # runs/README.md): the repo-root `runs/` tree, not this folder, even
    # though this engine is what writes into it.
    return WORKSPACE / "runs" / "research-cache" / "_system"


def _deep_runs_root():
    return WORKSPACE / "runs" / "research"


CONFIG_PATH = ROOT / "research.json"

METHOD_HEADER = (
    "_Every claim below carries a receipt — a permalink, a date, a count with "
    "its denominator. Where nothing came back it says `[UNFILLED]` and why, "
    "rather than guessing (the standard: "
    "control-room/prompts/research/_METHOD.md)._"
)


def _config():
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception:
        return {}


CFG = _config()


def _gate_mode(gate):
    """research.json > gates > <gate>: "hold" (the default) or "record"."""
    mode = str(((_config().get("gates") or {}).get(gate)) or "hold").lower()
    return mode if mode in ("hold", "record") else "hold"


def _cap(name, default):
    return int((CFG.get("caps") or {}).get(name, default))


def default_cap(name, default):
    """The public seam a chain's shim uses for its own `--cap` default,
    without reaching into this module's private config loader."""
    return _cap(name, default)


def _cache_days():
    return int(CFG.get("cache_days", 14))


def _discovery_cfg():
    """How the room-finding search is shaped — `research.json`'s `discovery`
    block, never a constant in this file, so a sort that turns out wrong is a
    config change rather than a code change. No room name ever lives there
    (workspace rule 7); only sort, window, posts-only and how many to keep."""
    d = CFG.get("discovery") or {}
    return (str(d.get("sort", "relevance")), str(d.get("window", "year")),
            bool(d.get("posts_only", True)), int(d.get("keep", 5)))


# ---------------------------------------------------------------- reuse, never re-implement

_reddit_mod = None
_apify_mod = None


def _load_module(path, name):
    import importlib.util
    if not path.is_file():
        raise RuntimeError(f"missing: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def reddit_door():
    """`components/apify/reddit.py`, loaded once. Pure at import
    time — no network call happens until `.main()` runs."""
    global _reddit_mod
    if _reddit_mod is None:
        _reddit_mod = _load_module(_reddit_tool(), "_research_reddit_door")
    return _reddit_mod


def apify_layer():
    """`components/apify/apify.py`, loaded once — the shared token +
    spare-account layer and its per-platform comment actors."""
    global _apify_mod
    if _apify_mod is None:
        _apify_mod = _load_module(_swipe_apify(), "_research_apify_layer")
    return _apify_mod


# ---------------------------------------------------------------- cache (14 days, per pull kind)

def _cache_key(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:20]


def _cache_get(bucket, *parts):
    p = _cache_root() / bucket / f"{_cache_key(*parts)}.json"
    if not p.is_file():
        return None
    try:
        doc = json.loads(p.read_text())
    except Exception:
        return None
    age_days = (time.time() - doc.get("_ts", 0)) / 86400
    if age_days > _cache_days():
        return None
    doc["_cache_hit"] = True
    doc["_cache_age_days"] = round(age_days, 1)
    return doc


def _cache_put(bucket, payload, *parts):
    d = _cache_root() / bucket
    d.mkdir(parents=True, exist_ok=True)
    payload = dict(payload, _ts=time.time())
    (d / f"{_cache_key(*parts)}.json").write_text(json.dumps(payload, indent=1)[:6_000_000])
    return payload


# ---------------------------------------------------------------- rooms + desire words

# A `### rooms` block, however deep the heading, up to the next heading of
# the same or shallower level (or EOF). See brands/_TEMPLATE/core-avatars/
# README.md, "rooms — where they talk". NOTE: `[^\n]*` on the heading line,
# not `.*$` — with DOTALL on for the body capture, a dotall `.*$` here would
# swallow the rest of the file before backtracking (found testing this
# against real avatar files, 2026-09-18).
ROOMS_RE = re.compile(r"^#{2,4}\s*rooms\b[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", re.M | re.S | re.I)
DESIRE_RE = re.compile(r"Core desire[^\"]*\"([^\"]+)\"", re.I)
STOP = {
    "i", "want", "to", "a", "the", "and", "my", "for", "that", "so", "can",
    "with", "of", "in", "on", "it", "without", "this", "his", "her", "their",
    "them", "los", "las", "el", "la", "de", "que", "me", "mi", "con", "por",
    "para", "actually", "really", "stop", "keep", "get", "have", "has",
    "from", "just", "sin", "salgan",
}


def _room_name(row):
    """The subreddit a row came from, bare (no `r/`) — the actor's own
    `communityName` already carries the prefix on some rows (found in the
    2026-09-18 proving run: `f"reddit r/{room}"` was printing
    `reddit r/r/es` because `communityName` was already `"r/es"`)."""
    room = row.get("communityName") or row.get("subreddit") or "?"
    return re.sub(r"^r/", "", str(room), flags=re.I)


def parse_rooms(text):
    """Every room named in a `### rooms` block — a bullet's first token
    (e.g. `r/bald`). Never a bare search: this tool never invents a room."""
    if not text:
        return []
    m = ROOMS_RE.search(text)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        body = line[1:].strip()
        token = re.split(r"—| - ", body)[0].strip().strip("`* ")
        if token:
            out.append(token)
    return out


def desire_words(text, limit=6):
    """The avatar's own desire, as search words — the fallback when a run
    carries no stage-1b topics yet."""
    m = DESIRE_RE.search(text or "")
    quote = m.group(1) if m else ""
    words = re.findall(r"[A-Za-zÀ-ÿ']{4,}", quote)
    seen, out = set(), []
    for w in words:
        lw = w.lower()
        if lw in STOP or lw in seen:
            continue
        seen.add(lw)
        out.append(lw)
        if len(out) >= limit:
            break
    return out


def avatar_dir(brand, avatar, root=None):
    return (Path(root) if root else WORKSPACE) / "brands" / brand / "core-avatars" / avatar


def sub_slug(path):
    """The sub-avatar's own slug — its frontmatter `id:`, else its filename
    with the `sub-NN-` prefix stripped."""
    m = re.search(r"^id:\s*(\S+)", path.read_text(), re.M)
    return m.group(1) if m else re.sub(r"^sub-\d+-", "", path.stem)


def sub_file(brand, avatar, sub, root=None):
    d = avatar_dir(brand, avatar, root) / "sub-avatars"
    if not d.is_dir() or not sub:
        return None
    for f in sorted(d.glob("*.md")):
        if sub_slug(f) == sub:
            return f
    return None


def sub_home(brand, avatar, sub, root=None):
    """ONE home per sub-avatar (the owner, 2026-09-18): the folder beside its
    card, named exactly like the card — `sub-avatars/<card stem>/` — holding
    `language/` (its clean rows, read by every chain through the language
    layer) and `research/<date>/` (the readable report). Raw pulls never
    land here; they stay under runs/research/."""
    sf = sub_file(brand, avatar, sub, root)
    stem = sf.stem if sf else sub
    return avatar_dir(brand, avatar, root) / "sub-avatars" / stem


def profile_file(brand, avatar, root=None):
    f = avatar_dir(brand, avatar, root) / "profile.md"
    return f if f.is_file() else None


# ---------------------------------------------------------------- confirmed vs. seeded

# THE LOCK IS THE LINE, NOT THE HEADING. the owner ruled it on 2026-09-18:
# "he should never have to write down rooms, the system finds where the avatar talks on its own".
# A `### rooms` block is treated as a PERSON'S ruling only when it
# carries a `confirmed by: <name>` line; everything else — an agent's seed, a
# gatherer write-back, a hand-typed guess nobody has stood behind — is
# provisional and gets replaced by the next discovery. The heading's own
# wording ("seeded", "found ... by the gatherer") is a label for a reader, and
# is never enough on its own to lock a block: a person adding the confirm line
# to a gatherer-written block must be able to keep the heading as it stands.
CONFIRMED_RE = re.compile(r"^\s*(?:[-*>]\s*)?(?:\*\*)?confirmed by:?(?:\*\*)?\s*\S", re.M | re.I)
SEEDED_HEADING_RE = re.compile(r"seeded|found by the gatherer", re.I)


def rooms_block_state(text):
    """-> ("confirmed" | "seeded" | "none", match_or_None) for one file's text."""
    if not text:
        return "none", None
    m = ROOMS_RE.search(text)
    if not m:
        return "none", None
    if CONFIRMED_RE.search(m.group(0)):
        return "confirmed", m
    return "seeded", m


def rooms_block_heading(text):
    """The `### rooms` heading line itself, or "". `SEEDED_HEADING_RE` matches
    the wording the gatherer writes — useful for a reader and for a report,
    never the lock (see `rooms_block_state`)."""
    _state, m = rooms_block_state(text)
    return text[m.start():].split("\n", 1)[0] if m else ""


def rooms_are_confirmed(text):
    return rooms_block_state(text)[0] == "confirmed"


def _avatar_texts(brand, avatar, sub=None, root=None, sub_path=None):
    """(path, text) for the sub-avatar file first — the narrower room list —
    then the core avatar's profile.md."""
    out = []
    sf = Path(sub_path) if sub_path else (sub_file(brand, avatar, sub, root) if sub else None)
    if sf and Path(sf).is_file():
        out.append((Path(sf), Path(sf).read_text()))
    pf = profile_file(brand, avatar, root)
    if pf:
        out.append((pf, pf.read_text()))
    return out


DELTA_RE = re.compile(r"^#{2,4}\s*language-delta\b[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", re.M | re.S | re.I)


def delta_words(text, limit=4):
    """A SUB-avatar's own narrowing words — the quoted phrases in its
    `### language-delta` block (the words only this sub says), shortest
    phrases first so the search stays the way the person types it. A core
    avatar has no delta and returns nothing here."""
    m = DELTA_RE.search(text or "")
    if not m:
        return []
    # Only the bullet lines are the sub's own phrases; the block's intro
    # names the CORE dialect that stays at the avatar level, so it is skipped.
    bullets = [ln for ln in m.group(1).splitlines() if ln.lstrip().startswith("-")]
    phrases = []
    for ln in bullets:
        phrases += re.findall(r'[\"\u201c]([^\"\u201d\n]{3,60})[\"\u201d]', ln)
    phrases = [p for p in phrases if len(p.split()) <= 4]
    phrases.sort(key=lambda p: len(p.split()))
    seen, out = set(), []
    for p in phrases:
        for w in re.findall(r"[A-Za-zÀ-ÿ']{3,}", p):
            lw = w.lower()
            if lw in STOP or lw in seen:
                continue
            seen.add(lw)
            out.append(lw)
            if len(out) >= limit:
                return out
    return out


def _words_from(texts, topics=None):
    """Search words for one avatar or sub-avatar. Stage-1b topics win when a
    run carries them. Otherwise a SUB-avatar searches on its own narrowing
    words first (its language-delta — "sun damage", not the core's "dark
    spots"), then the core desire fills the rest; a core avatar searches on
    its core desire alone. Ruled 2026-09-18 after the first discovery for a
    sub pulled the core avatar's rooms instead of the sub's."""
    words = list(topics or [])
    if words:
        return words
    seen = set()
    for _p, t in texts:
        if "sub-avatars" in str(_p):
            for w in delta_words(t):
                if w not in seen:
                    seen.add(w); words.append(w)
    for _p, t in texts:
        core = desire_words(t)
        if core:
            for w in core:
                if w not in seen and len(words) < 6:
                    seen.add(w); words.append(w)
            break
    return words


# ---------------------------------------------------------------- demographic fit

# THE RULING (the owner, 2026-09-18): room discovery for a sun-damage sub-avatar
# came back with r/Blackskincare, r/skincare_ph and r/indianbeautyyappers, and
# that brand's customers are none of those people. **Research has to be
# reconciled against the avatar's own demographics or it is irrelevant for that
# avatar.** So: the avatar's profile carries a labelled `### demographics`
# block, the room name is read for markers, and a room that plainly belongs to
# a different set of people is DROPPED before a single row is filed from it.
#
# What this check can and cannot say, by construction: the marker table says a
# room is plainly for SOMEONE ELSE. It never says a room is plainly for us — a
# name with no marker is `general` and is always kept, and a slot the profile
# leaves `unknown` rules nothing out.

DEMO_RE = re.compile(r"^#{2,4}\s*demographics\b[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", re.M | re.S | re.I)

DEMO_FIELDS = {
    "age": "age",
    "gender": "gender",
    "skin tone / ethnicity": "skin tone / ethnicity",
    "skin tone/ethnicity": "skin tone / ethnicity",
    "skin tone": "skin tone / ethnicity",
    "ethnicity": "skin tone / ethnicity",
    "region": "region",
    "language": "language",
}
UNKNOWN_VALUES = {"", "unknown", "n/a", "na", "none", "-", "—", "tbd", "?", "not known",
                  "unstated", "unrecorded"}


def _fit_cfg():
    return CFG.get("demographic_fit") or {}


def markers_table():
    """The room-name markers, from `research.json` — never a constant here, so
    a marker that turns out wrong is a config change. No room of ours is named
    in it (workspace rule 7): these are generic community-naming conventions."""
    return _fit_cfg().get("markers") or []


def _segments(text):
    """The text split the way a room name reads: on punctuation, on a camelCase
    boundary, and between letters and digits. `30PlusSkinCare` -> 30 · plus ·
    skin · care; `skincare_ph` -> skincare · ph."""
    out = []
    for chunk in re.split(r"[^A-Za-z0-9]+", str(text or "")):
        if not chunk:
            continue
        out += [s.lower() for s in
                re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+|[0-9]+", chunk) if s]
    return out


def _marker_hits(text, marker):
    """Does this text carry this marker? A marker of 3 characters or fewer must
    EQUAL a whole segment (`ph` finds `skincare_ph`, never `phimosis`); a longer
    one must START a segment or a run of them (`black` finds `blackskincare`,
    and `men` never fires inside `women`) — or, at 5+ characters, END one
    (`india` finds `skinsolutionsindia`)."""
    segs = _segments(text)
    joins = ["".join(segs[i:]) for i in range(len(segs))]
    for word in marker.get("match") or []:
        w = str(word).lower()
        if len(w) <= 3:
            if w in segs:
                return w
        elif any(j.startswith(w) for j in joins):
            return w
        elif len(w) >= 5 and any(seg.endswith(w) for seg in segs):
            # a run-together name can END on the marker: r/SkinSolutionsindia
            # (2026-10-01 — 80 rows from it reached a 55-70 US avatar's bank)
            return w
    return None


def _age_band(text):
    """The widest band the numbers in this text describe. `50+` and `50 and
    over` are open upward; `55–70` is closed. -> (lo, hi) or None."""
    s = str(text or "")
    lo, hi, open_up = None, None, False
    for m in re.finditer(r"(\d{1,3})\s*(?:[–—-]|to)\s*(\d{1,3})", s):
        a, b = int(m.group(1)), int(m.group(2))
        lo = a if lo is None else min(lo, a)
        hi = b if hi is None else max(hi, b)
    for m in re.finditer(r"(\d{1,3})\s*(?:\+|plus\b|and over\b|and up\b)", s, re.I):
        a = int(m.group(1))
        lo = a if lo is None else min(lo, a)
        open_up = True
    if lo is None:
        singles = [int(x) for x in re.findall(r"\b(\d{1,3})\b", s) if 5 <= int(x) <= 110]
        if not singles:
            return None
        lo, hi = min(singles), max(singles)
    if open_up or hi is None:
        hi = 120
    return (lo, max(hi, lo))


def parse_demographics(text):
    """The `### demographics` block of one avatar file, as {field: value}.
    Five slots, plain words, `unknown` allowed — see
    brands/_TEMPLATE/core-avatars/README.md. A line the block does not carry is
    simply absent; a value of `unknown` is kept, because "the profile says it
    does not know" and "nobody wrote a block" read the same way downstream and
    both rule nothing out."""
    if not text:
        return {}
    m = DEMO_RE.search(text)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        line = line.strip().lstrip("-*• ").strip()
        line = re.sub(r"^\*\*(.+?)\*\*", r"\1", line)
        if ":" not in line or line.startswith("_") or line.startswith("<!--"):
            continue
        key, _sep, val = line.partition(":")
        key = re.sub(r"\s+", " ", key.strip().strip("*` ").lower())
        field = DEMO_FIELDS.get(key)
        if not field:
            continue
        out[field] = val.strip()
    return out


def demographics(brand, avatar, sub=None, root=None, sub_path=None):
    """Who this avatar actually is, as labelled slots — the CORE avatar's
    `### demographics` block, overridden line for line by the sub-avatar's own
    block when it has one (brands/_TEMPLATE/core-avatars/README.md). Never
    raises and never guesses: an avatar with no block at all comes back {} and
    every room is then `unknown`."""
    demo = {}
    try:
        pf = profile_file(brand, avatar, root)
        if pf:
            demo.update(parse_demographics(pf.read_text()))
        sf = Path(sub_path) if sub_path else (sub_file(brand, avatar, sub, root) if sub else None)
        if sf and Path(sf).is_file():
            demo.update(parse_demographics(Path(sf).read_text()))
    except Exception:
        return demo
    return demo


def _slot(demo, field):
    """One slot's value, or None when the profile says it does not know. A slot
    is allowed to explain itself — `unknown — this file states none` is still
    unknown — so a value that OPENS on an unknown word is unknown."""
    v = (demo or {}).get(field)
    if v is None:
        return None
    s = str(v).strip()
    low = s.lower().strip(". ")
    if low in UNKNOWN_VALUES:
        return None
    for word in UNKNOWN_VALUES:
        if word and low.startswith(word) and (len(low) == len(word)
                                              or not low[len(word)].isalnum()):
            return None
    return s


def room_fit(room_name, demo):
    """Judge ONE room name against ONE avatar's demographics.

    -> {"room", "fit": "yes"|"no"|"unknown", "marker", "why"}.

    `no` is the only verdict that costs a room anything, and it is only ever
    reached when the room name carries a marker AND the avatar's own slot for
    that field plainly names someone else. Everything else keeps the room:
    no marker in the name (`general`), or a slot the profile left `unknown`."""
    room = re.sub(r"^r/", "", str(room_name or ""), flags=re.I)
    hits = []
    for marker in markers_table():
        word = _marker_hits(room, marker)
        if word:
            hits.append((marker, word))
    if not hits:
        return dict(room=room, fit="unknown", marker="general", markers=[],
                    why="the room name carries no demographic marker — nothing to reconcile")

    verdicts, reasons = [], []
    for marker, word in hits:
        sig = marker.get("signal") or {}
        field = sig.get("field") or ""
        value = sig.get("value") or marker.get("id")
        slot = _slot(demo, field)
        if slot is None:
            verdicts.append("unknown")
            reasons.append(f"`{word}` reads as {field} {value}, and this avatar's "
                           f"{field} is unknown — nothing to reconcile")
            continue
        if field == "age":
            room_band, avatar_band = _age_band(value), _age_band(slot)
            if not room_band or not avatar_band:
                verdicts.append("unknown")
                reasons.append(f"`{word}` reads as age {value}, and this avatar's age "
                               f"slot carries no readable band")
                continue
            overlap = room_band[0] <= avatar_band[1] and avatar_band[0] <= room_band[1]
            verdicts.append("yes" if overlap else "no")
            reasons.append(
                f"`{word}` reads as age {value} ({room_band[0]}–{room_band[1]}); this avatar is "
                f"{avatar_band[0]}–{avatar_band[1]} — "
                + ("the bands overlap" if overlap else "the bands do not overlap"))
            continue
        shared = _marker_hits(slot, marker)
        verdicts.append("yes" if shared else "no")
        reasons.append(
            f"`{word}` reads as {field} {value}; this avatar's {field} is "
            f"\"{slot[:120]}\" — "
            + (f"which names the same group (`{shared}`)" if shared
               else "which names someone else"))

    fit = "no" if "no" in verdicts else ("yes" if "yes" in verdicts else "unknown")
    ids = [m["id"] for m, _w in hits]
    return dict(room=room, fit=fit, marker=",".join(ids), markers=ids,
                why="; ".join(reasons))


def split_by_fit(rooms, demo):
    """(kept, dropped) over `tally_rooms` rows or bare room names. Each row
    comes back carrying its own `fit` record, so a reader never has to re-derive
    why a room was kept."""
    kept, dropped = [], []
    for r in rooms or []:
        row = dict(r) if isinstance(r, dict) else {"room": re.sub(r"^r/", "", str(r), flags=re.I)}
        row["fit"] = room_fit(row.get("room"), demo)
        (dropped if row["fit"]["fit"] == "no" else kept).append(row)
    return kept, dropped


def demographics_line(demo):
    """The one line a run's research.md prints so a reader can see what the
    check actually ran against."""
    if not demo:
        return "[UNFILLED: this avatar carries no `### demographics` block — every room was kept]"
    order = ["age", "gender", "skin tone / ethnicity", "region", "language"]
    parts = [f"{k}: {demo[k]}" for k in order if k in demo]
    parts += [f"{k}: {v}" for k, v in demo.items() if k not in order]
    return " · ".join(parts)


def render_dropped_md(dropped):
    if not dropped:
        return "None — every room found matched this avatar's demographics."
    out = []
    for r in dropped:
        out.append(f"- **r/{r['room']}** — {r['fit']['why']}")
    return "\n".join(out)


# ---------------------------------------------------------------- room discovery

def tally_rooms(posts, top=5, score_fn=None):
    """Which rooms these posts actually came from, WEIGHTED BY SCORE — the
    loudest room wins, not merely the busiest. Pure: no network, no door, so
    the weighting is testable on rows alone (`score_fn` defaults to the
    reddit door's own reader, which spells the field five different ways)."""
    if score_fn is None:
        score_fn = reddit_door().score
    by = {}
    for p in posts:
        name = _room_name(p)
        if not name or name == "?":
            continue
        slot = by.setdefault(name, {"room": name, "posts": 0, "score": 0,
                                    "sample_title": "", "sample_url": "", "_best": None})
        slot["posts"] += 1
        s = score_fn(p) or 0
        slot["score"] += s
        if slot["_best"] is None or s >= slot["_best"]:
            slot["_best"] = s
            slot["sample_title"] = (p.get("title") or "").strip()[:160]
            slot["sample_url"] = p.get("url") or p.get("link") or p.get("permalink") or ""
    ranked = sorted(by.values(), key=lambda r: (-r["score"], -r["posts"], r["room"]))
    for r in ranked:
        r.pop("_best", None)
    return ranked[:top]


def discovery_query(words):
    """ONE search, in the avatar's own desire words. No room named — that is
    the whole point: this is the pull that FINDS the rooms."""
    return " ".join(list(words)[:4]).strip()


def _find_rooms_detail(brand, avatar, sub, cap=None, root=None, use_cache=True,
                       out_dir=None, words=None, sub_path=None, top=None):
    """The full discovery record — rooms, spend, the query fired, whether it
    came from cache. `find_rooms()` is this, narrowed to the rooms."""
    cap = int(cap or _cap("discovery", 40))
    sort, window, posts_only, keep = _discovery_cfg()
    top = int(top or keep)
    words = list(words or []) or _words_from(_avatar_texts(brand, avatar, sub, root, sub_path))
    if not words:
        return dict(ok=False, rooms=[], spend=0.0, cached=False, words=[], query="", cap=cap,
                    why="[UNFILLED: this avatar names no desire words to search on — "
                        "a `Core desire` line on the avatar file is what discovery searches on]")
    query = discovery_query(words)
    # `v2` in the key: the first live discovery (2026-09-18, <brand> /
    # sun-damage-reckoner) came back with ONE room, because the door's
    # default `maxComments: 25` let a single viral thread's comments eat the
    # entire 25-item budget — 1 post, 24 comments, one room, and the room was
    # a cave-diving video. Discovery is a question about ROOMS, so it now
    # pulls posts only; the key is versioned so no cached answer from before
    # that fix is ever served.
    demo = demographics(brand, avatar, sub, root=root, sub_path=sub_path)
    key = ("discovery", "v3", brand, avatar, sub or "", tuple(sorted(words)), cap, top,
           sort, window, posts_only)
    if use_cache:
        hit = _cache_get("discovery", *key)
        if hit:
            # Everything the record prints has to survive the cache, or a
            # cached run's own receipt reads `sort ?, window ?` and nobody can
            # tell how the answer was reached. THE FIT CHECK IS NOT CACHED: the
            # rooms the search found are, and they are re-judged on the way out,
            # so correcting a demographics block takes effect on the next run
            # without re-spending on the search.
            raw = hit.get("rooms_raw") or hit.get("rooms") or []
            kept, dropped = split_by_fit(raw, demo)
            return dict(ok=True, rooms=kept, rooms_raw=raw, dropped=dropped, demographics=demo,
                        spend=0.0, cached=True,
                        cache_age_days=hit.get("_cache_age_days"), words=words, query=query,
                        cap=cap, sort=hit.get("sort", sort), window=hit.get("window", window),
                        posts_read=hit.get("posts_read"))
    raw = Path(out_dir) if out_dir else (_cache_root() / "discovery" / "_raw" / _cache_key(*key))
    try:
        # No `rooms` argument, on purpose — an unrestricted search is the only
        # way a room we have never named can come back at all. POSTS ONLY: a
        # comment thread is one room repeated, and a cap spent on one thread
        # answers nothing about where an avatar talks.
        rows, _md, spend = _run_reddit([], [query], cap, raw, sort=sort, time_window=window,
                                       no_comments=posts_only)
    except SystemExit as e:
        return dict(ok=False, rooms=[], dropped=[], demographics=demo, spend=0.0, cached=False,
                    words=words, query=query, cap=cap,
                    why=f"[UNFILLED: room discovery failed — {e}]")
    except Exception as e:
        return dict(ok=False, rooms=[], dropped=[], demographics=demo, spend=0.0, cached=False,
                    words=words, query=query, cap=cap,
                    why=f"[UNFILLED: room discovery failed — {e}]")
    posts, _comments = _split_posts_comments(rows)
    found = tally_rooms(posts, top=top)
    if use_cache:
        _cache_put("discovery", dict(rooms=found, rooms_raw=found, spend=spend, query=query,
                                     sort=sort, window=window, posts_read=len(posts)), *key)
    # THE RULING: a room that plainly belongs to a different set of people is
    # dropped here, before anything is written back or pulled from.
    kept, dropped = split_by_fit(found, demo)
    return dict(ok=True, rooms=kept, rooms_raw=found, dropped=dropped, demographics=demo,
                spend=round(spend, 3), cached=False, words=words,
                query=query, cap=cap, posts_read=len(posts), sort=sort, window=window)


def find_rooms(brand, avatar, sub, cap=40, **kw):
    """ONE discovery search in the avatar's own desire words, unrestricted,
    sorted `top` over the last `year`, capped small (~40 items ~ $__) —
    then the returned posts tallied by room, weighted by score, top 5 kept.

    -> [{"room", "posts", "score", "sample_title", "sample_url"}], loudest
    first. Never raises: no key, a 403 or a strange actor all come back as an
    empty list, and the caller falls back to whatever the file already said."""
    return _find_rooms_detail(brand, avatar, sub, cap=cap, **kw).get("rooms") or []


def write_rooms_block(path, found, when=None, dropped=None):
    """Write the found rooms back into the avatar's own file, REPLACING any
    earlier gatherer/agent-seeded block and leaving every other byte of the
    file exactly as it was. A block a person confirmed is never touched.

    ONLY THE KEPT ROOMS ARE LISTED (the owner, 2026-09-18). Rooms dropped for a
    demographic mismatch get one line naming them, so the file says out loud
    that discovery found them and the check threw them out — a dropped room
    never sits in the block looking like a room to pull from.
    -> True when the file changed."""
    path = Path(path)
    try:
        text = path.read_text()
    except Exception:
        return False
    state, m = rooms_block_state(text)
    if state == "confirmed":
        return False
    when = when or date.today().isoformat()
    lines = [f'### rooms — found {when} by the gatherer '
             '(edit freely; add "confirmed by: <your name>" to lock)', ""]
    for r in found:
        lines.append(f"- r/{r['room']} — {r['posts']} post(s), {r['score']} total score "
                     "in the discovery pull")
    if dropped:
        lines += ["", "Dropped as a demographic mismatch for this avatar (not pulled from): "
                  + ", ".join(f"r/{d['room']}" for d in dropped) + "."]
    block = "\n".join(lines) + "\n\n"
    new = (text[:m.start()] + block + text[m.end():]) if m else (text.rstrip("\n") + "\n\n" + block)
    if new == text:
        return False
    path.write_text(new)
    return True


def resolve_rooms(brand, avatar, sub=None, topics=None, root=None, discover=True,
                  cap=None, sub_path=None):
    """Rooms, desire words, and (when one ran) the discovery record.

    A `### rooms` block a PERSON confirmed wins outright. Otherwise the
    gatherer goes and finds the rooms itself, writes them back into the
    avatar's own file, and uses them — the owner's 2026-09-18 ruling: nobody
    should have to write down where an avatar talks. Discovery that comes
    back empty (no key, a 403) falls back to whatever the seeded block
    already said, so this is never worse than the old behaviour."""
    texts = _avatar_texts(brand, avatar, sub, root, sub_path)
    words = _words_from(texts, topics)

    for path, text in texts:
        state, _m = rooms_block_state(text)
        if state == "confirmed":
            rooms = parse_rooms(text)
            if rooms:
                # A block a person confirmed is a ruling and is used as written —
                # the fit check is still run and recorded, so the run says which
                # rooms it would have questioned, but it drops nothing here.
                demo = demographics(brand, avatar, sub, root=root, sub_path=sub_path)
                _k, questioned = split_by_fit(rooms, demo)
                return rooms, words, dict(source="confirmed", file=str(path), rooms=[],
                                          demographics=demo, questioned=questioned, dropped=[])

    seeded = []
    for _path, text in texts:
        seeded = parse_rooms(text)
        if seeded:
            break

    if not discover:
        return seeded, words, None

    det = _find_rooms_detail(brand, avatar, sub, cap=cap, root=root, words=words,
                             sub_path=sub_path)
    found = det.get("rooms") or []
    if not found:
        det["source"] = "discovery-empty"
        det["fell_back_to"] = seeded
        return seeded, words, det
    target = texts[0][0] if texts else None
    det["source"] = "discovery"
    det["written_to"] = (str(target) if (target and write_rooms_block(
        target, found, dropped=det.get("dropped"))) else None)
    return [f"r/{r['room']}" for r in found], words, det


def rooms_and_words(brand, avatar, sub=None, topics=None, root=None):
    """Rooms and desire words for one avatar or sub-avatar — the sub-avatar
    file first (the narrower room list), the core avatar's profile.md as
    fallback.

    A `### rooms` block CONFIRMED by a person is used as written. Anything
    else — a seeded block, or no block at all — means the gatherer discovers
    the rooms itself first (`resolve_rooms`), so an avatar nobody has typed
    rooms for is no longer an `[UNFILLED]`. Callers that want the discovery
    record itself (to file it in a run) call `resolve_rooms` directly."""
    rooms, words, _discovery = resolve_rooms(brand, avatar, sub, topics, root)
    return rooms, words


# ---------------------------------------------------------------- Schwartz research questions

FALLBACK_QUESTIONS = [
    dict(id="fallback-role", framework="identification",
         question="What roles does this avatar already claim for themselves?",
         tags=["role-claimed"]),
    dict(id="fallback-belief", framework="gradualization",
         question="What belief does this avatar already accept without argument?",
         tags=["accepted-belief"]),
    dict(id="fallback-mechanism", framework="mechanization",
         question="What mechanism language does real speech use to explain why something works or fails?",
         tags=["mechanism"]),
    dict(id="fallback-objection", framework="redefinition",
         question="What exact objection language shows up in reviews or comments?",
         tags=["objection"]),
    dict(id="fallback-failed", framework="concentration",
         question="What alternatives has this avatar already tried and named as failures?",
         tags=["alternative-solution", "tried-and-failed"]),
    dict(id="fallback-subculture", framework="camouflage",
         question="What in-words, slang or reference points mark this subculture as its own?",
         tags=["subculture", "in-word"]),
    dict(id="fallback-fulfilled", framework="intensification",
         question="What fulfilled-desire picture does this avatar paint when things go right?",
         tags=["result-language", "post-use-feeling"]),
]


def schwartz_questions():
    """The doctrine component's research-question bank, when it exists,
    else this minimal built-in list — marked as a fallback wherever it's
    used, never silently."""
    try:
        doc = json.loads(_doctrine_questions_path().read_text())
        qs = doc.get("research_questions") or []
        if qs:
            return qs, False
    except Exception:
        pass
    return FALLBACK_QUESTIONS, True


# The seed a question's own tag adds to the avatar's desire words — never a
# semantic classifier, just what keeps several pulls from being copies of
# the same search. A person can hand-tune these once real pulls show what
# actually lands.
QUESTION_SEED = {
    "role-claimed": "I am", "accepted-belief": "everyone knows",
    "mechanism": "why does", "objection": "worried that",
    "alternative-solution": "tried everything", "tried-and-failed": "nothing worked",
    "subculture": "we all", "in-word": "we all",
    "result-language": "finally", "post-use-feeling": "feels like",
}


def build_queries_per_question(words, questions):
    base = " ".join(words[:3]) if words else ""
    out = []
    for q in questions:
        tag = (q.get("tags") or ["general"])[0]
        seed = QUESTION_SEED.get(tag, "")
        query = " ".join(x for x in [base, seed] if x).strip() or (base or "help")
        out.append(dict(question=q, query=query))
    return out


# ---------------------------------------------------------------- the reddit door, driven

def _run_reddit(rooms, queries, cap, out_dir, sort=None, time_window=None, no_comments=False):
    """Calls the reddit door for real via its own CLI contract (argv + its
    own `main()`). Returns (rows, md, spend) or raises — SystemExit on a
    missing key/actor failure (the door's own error path), any other
    Exception on something stranger. Callers turn both into `[UNFILLED]`.

    `sort`/`time_window`/`no_comments` are the door's own `--sort`/`--time`/
    `--no-comments` flags, passed through only when a caller names them — room
    DISCOVERY wants `top`/`year` (the loudest rooms of the last year) and
    POSTS ONLY; every other pull keeps the door's own defaults. Omitted means
    omitted: this never invents a flag."""
    door = reddit_door()
    out_dir.mkdir(parents=True, exist_ok=True)
    argv = ["reddit.py", "--out", str(out_dir), "--queries", *queries,
            "--limit", str(cap)]
    if sort:
        argv += ["--sort", str(sort)]
    if time_window:
        argv += ["--time", str(time_window)]
    if no_comments:
        argv.append("--no-comments")
    if rooms:
        bare = [re.sub(r"^r/", "", r, flags=re.I) for r in rooms]
        argv += ["--subreddits", *bare]
    old_argv = sys.argv
    sys.argv = argv
    try:
        door.main()
    finally:
        sys.argv = old_argv
    md = (out_dir / "reddit.md").read_text() if (out_dir / "reddit.md").is_file() else ""
    rows = json.loads((out_dir / "reddit.json").read_text()) if (out_dir / "reddit.json").is_file() else []
    spend = round(len(rows) * 0.004, 3)
    return rows, md, spend


def _split_posts_comments(rows):
    posts = [r for r in rows if r.get("title") or (r.get("dataType") or r.get("type")) == "post"]
    ids = {id(r) for r in posts}
    comments = [r for r in rows if id(r) not in ids]
    return posts, comments


def pull_forums(brand, avatar, sub, rooms, words, cap, out_dir, use_cache=True):
    """Never a bare search: no rooms means no pull, and the section says
    so. Cached 14 days per (brand, avatar, sub, words, rooms) so repeat
    runs on the same avatar don't re-spend."""
    if not rooms:
        return dict(ok=False, md="[UNFILLED: no rooms recorded for this avatar]",
                    posts=[], comments=[], spend=0.0, cached=False)
    key = ("forums", brand, avatar, sub or "", tuple(sorted(words)), tuple(sorted(rooms)))
    if use_cache:
        hit = _cache_get("forums", *key)
        if hit:
            return dict(ok=True, md=hit.get("md", ""), posts=hit.get("posts", []),
                        comments=hit.get("comments", []), spend=0.0, cached=True,
                        cache_age_days=hit.get("_cache_age_days"))
    queries = words or [avatar.replace("-", " ")]
    try:
        rows, md, spend = _run_reddit(rooms, queries, cap, out_dir)
    except SystemExit as e:
        return dict(ok=False, md=f"[UNFILLED: the forums pull failed — {e}]",
                    posts=[], comments=[], spend=0.0, cached=False)
    except Exception as e:
        return dict(ok=False, md=f"[UNFILLED: the forums pull failed — {e}]",
                    posts=[], comments=[], spend=0.0, cached=False)
    posts, comments = _split_posts_comments(rows)
    if use_cache:
        _cache_put("forums", dict(md=md, posts=posts, comments=comments), *key)
    return dict(ok=True, md=md, posts=posts, comments=comments, spend=spend, cached=False)


# ---------------------------------------------------------------- comments on the swiped post

PLATFORM_RE = [
    ("tiktok", re.compile(r"tiktok\.com", re.I)),
    ("instagram", re.compile(r"instagram\.com", re.I)),
    ("youtube", re.compile(r"youtu\.?be", re.I)),
]


def platform_of(url):
    for name, rx in PLATFORM_RE:
        if rx.search(url or ""):
            return name
    return None


def pull_comments(source_url, cap, use_cache=True):
    if not source_url or str(source_url).upper() == "NONE":
        return dict(ok=False, md="[UNFILLED: this run has no source_url]",
                    rows=[], spend=0.0, cached=False)
    platform = platform_of(source_url)
    actor_map = CFG.get("actors", {}).get("comments", {})
    if not platform or platform not in actor_map:
        return dict(ok=False,
                    md=f"[UNFILLED: no comment actor configured for {platform or 'this platform'}]",
                    rows=[], spend=0.0, cached=False)
    key = ("comments", source_url)
    if use_cache:
        hit = _cache_get("comments", *key)
        if hit:
            return dict(ok=True, md=hit.get("md", ""), rows=hit.get("rows", []),
                        spend=0.0, cached=True, cache_age_days=hit.get("_cache_age_days"))
    try:
        layer = apify_layer()
        out = layer.comments_for([source_url], platform, per_post=cap)
    except SystemExit as e:
        return dict(ok=False, md=f"[UNFILLED: the comment pull failed — {e}]",
                    rows=[], spend=0.0, cached=False)
    except Exception as e:
        return dict(ok=False, md=f"[UNFILLED: the comment pull failed — {e}]",
                    rows=[], spend=0.0, cached=False)
    if out is None:
        return dict(ok=False, md="[UNFILLED: the comment actor returned nothing]",
                    rows=[], spend=0.0, cached=False)
    rows = [r for lst in out.values() for r in (lst or [])]
    spend = round(len(rows) * 0.003, 3)
    md = render_comments_md(rows, source_url)
    if use_cache:
        _cache_put("comments", dict(md=md, rows=rows), *key)
    return dict(ok=True, md=md, rows=rows, spend=spend, cached=False)


# ---------------------------------------------------------------- two bands, counts, rendering

def two_bands(rows, score_fn):
    """The room / the different band, mechanically: ranked by score, split
    at the midpoint. Same standard _METHOD.md asks a person for — applied
    without one in the loop, so it's a split, not a judgment."""
    scored = sorted(rows, key=lambda r: -(score_fn(r) or 0))
    half = (len(scored) + 1) // 2
    return scored[:half], scored[half:]


def counts_with_denominator(rows, words, text_fn):
    total = len(rows)
    out = []
    for w in words:
        n = sum(1 for r in rows if w.lower() in (text_fn(r) or "").lower())
        out.append((w, n, total))
    return out


def render_forums_md(result, words):
    if not result["ok"]:
        return f"# Forums\n\n{result['md']}\n"
    door = reddit_door()
    posts, comments = result["posts"], result["comments"]
    room_band, diff_band = two_bands(posts, door.score)
    counts = counts_with_denominator(
        posts + comments, words,
        lambda r: f"{r.get('title', '')} {r.get('body') or r.get('selftext') or ''}")
    L_ = ["# Forums — Reddit, via the reddit door", ""]
    if result.get("cached"):
        L_.append(f"_(from cache, {result.get('cache_age_days')} day(s) old — no new spend this run)_\n")
    L_.append(f"**{len(posts)} posts, {len(comments)} comments.**\n")
    L_.append("## Counts, with denominators\n")
    if counts:
        for w, n, total in counts:
            L_.append(f"- {n} of {total} rows mention **{w}**")
    else:
        L_.append("- (no desire words to count against)")
    L_.append(f"\n## Band 1 — the room ({len(room_band)} posts, top half by score)\n")
    for p in room_band[:15]:
        L_.append(f"- **{door.score(p) or 0}** · r/{_room_name(p)} "
                  f"· {p.get('title', '(no title)')} — {p.get('url') or p.get('link') or ''}")
    L_.append(f"\n## Band 2 — the different band ({len(diff_band)} posts, bottom half by score)\n")
    for p in diff_band[:15]:
        L_.append(f"- **{door.score(p) or 0}** · r/{_room_name(p)} "
                  f"· {p.get('title', '(no title)')} — {p.get('url') or p.get('link') or ''}")
    L_.append("\n## What I left out\n")
    L_.append(f"- Everything beyond the cap ({len(posts) + len(comments)} rows pulled this run).")
    L_.append("\n## The reddit door's own read, verbatim\n")
    L_.append(result["md"])
    return "\n".join(L_)


def render_comments_md(rows, source_url):
    if not rows:
        return f"# Comments — {source_url}\n\n[UNFILLED: no comments came back]\n"
    room, diff = two_bands(rows, lambda r: r.get("likes") or 0)
    L_ = ["# Comments — the swiped post's own thread", "", str(source_url), "",
         f"**{len(rows)} comments read.**", "",
         f"## Band 1 — the room ({len(room)}, top half by likes)"]
    for c in room[:15]:
        L_.append(f'- **{c.get("likes") or 0}** · {c.get("date") or "?"} · '
                  f'"{(c.get("text") or "").strip()[:300]}"')
    L_.append(f"\n## Band 2 — the different band ({len(diff)}, bottom half by likes)")
    for c in diff[:15]:
        L_.append(f'- **{c.get("likes") or 0}** · {c.get("date") or "?"} · '
                  f'"{(c.get("text") or "").strip()[:300]}"')
    return "\n".join(L_)


def render_language_md(brand, avatar, chain_profile, funnel=None, topics=None):
    """The `depth`/`spice`-style language section — entirely the CALLER's
    definition. No `chain_profile`, or one naming no stages/no callable,
    means this section is [UNFILLED] — the engine ships no stage map."""
    cp = chain_profile or {}
    stages = cp.get("language_stages") or []
    for_stage = cp.get("language_for_stage")
    if not brand or not avatar:
        return "[UNFILLED: no brand/avatar decided yet for this run]"
    if not stages or not for_stage:
        return "[UNFILLED: no chain profile given for the language bank]"
    parts = []
    for stage in stages:
        try:
            parts.append(for_stage(brand, stage, avatar, funnel, topics, 30))
        except Exception as e:
            parts.append(f"(language query for {stage} failed: {e})")
    return "\n\n---\n\n".join(parts)


def render_rooms_md(discovery):
    """The discovery section: room, posts, score, one sample title each —
    so a reader can see WHY each room was picked, not just that it was."""
    if not discovery:
        return "[UNFILLED: no room discovery ran this pull]"
    if discovery.get("source") == "confirmed":
        out = ["The rooms came from the avatar's own `### rooms` block, confirmed by a "
               f"person — no discovery ran. ({discovery.get('file', '')})"]
        q = discovery.get("questioned") or []
        if q:
            out += ["", "The demographic check would have questioned "
                    + ", ".join(f"r/{r['room']}" for r in q)
                    + " — kept anyway, because a confirmed block is a person's ruling."]
        return "\n".join(out)
    rooms = discovery.get("rooms") or []
    spend = float(discovery.get("spend") or 0.0)
    L_ = [f"One discovery search, unrestricted, posts only, sort "
          f"`{discovery.get('sort', '?')}`, window `{discovery.get('window', '?')}`, cap "
          f"{discovery.get('cap', '?')} — query `{discovery.get('query', '')}`"
          + (" (from cache, no new spend)." if discovery.get("cached") else f" (${spend:.3f}).")]
    if not rooms:
        L_ += ["", discovery.get("why") or "[UNFILLED: no rooms came back]"]
        if discovery.get("fell_back_to"):
            L_.append(f"Fell back to the rooms already on file: "
                      f"{', '.join(discovery['fell_back_to'])}.")
        return "\n".join(L_)
    read = discovery.get("posts_read")
    L_ += ["", f"**{len(rooms)} room(s) kept**"
           + (f", {len(discovery.get('dropped') or [])} dropped on demographic fit"
              if discovery.get("dropped") else "")
           + ", ranked by total score across the pull"
           + (f" ({read} posts read)." if read is not None else "."), ""]
    for r in rooms:
        L_.append(f"- **r/{r['room']}** — {r['posts']} post(s) · {r['score']} total score "
                  f"· e.g. \"{r.get('sample_title') or '(no title)'}\" "
                  f"{r.get('sample_url') or ''}".rstrip())
    dropped = discovery.get("dropped") or []
    L_ += ["", "### Rooms dropped — demographic mismatch", "",
           render_dropped_md(dropped)]
    if discovery.get("written_to"):
        L_ += ["", f"Written back into `{discovery['written_to']}` as a gatherer block — "
               'edit it freely, or add `confirmed by: <your name>` to lock it.']
    return "\n".join(L_)


def render_research_md(brand, avatar, sub, language_md, forums_md, comments_md, spend_total,
                       left_out, rooms_md=None, demo=None):
    L_ = [f"# Research — {avatar}" + (f" / {sub}" if sub else "") + f" ({brand})", "",
         METHOD_HEADER, "",
         "**demographics** (what every room was reconciled against — "
         "brands/<brand>/core-avatars/**, `### demographics`): "
         + demographics_line(demo), "",
         "## Rooms — where this avatar actually talks", "",
         rooms_md or "[UNFILLED: no room discovery ran this pull]", "",
         "## Language bank", "", language_md, "",
         "## Forums", "", forums_md, "",
         "## Comments on the swiped post", "", comments_md, "",
         "## What I left out", ""]
    for line in (left_out or ["nothing — every pull ran"]):
        L_.append(f"- {line}")
    L_ += ["", "## Spend", "", f"**${spend_total:.3f}** this run "
          "(cap enforced per pull; cache hits cost nothing)."]
    return "\n".join(L_)


# ---------------------------------------------------------------- inputs(st, chain_profile)

def _inputs_core(st, chain_profile=None, out_dir=None):
    brand = st.get("brand")
    aud = st.get("audience") or {}
    avatar = aud.get("_avatar") or aud.get("avatar")
    sub = aud.get("_sub_avatar") or aud.get("sub_avatar")
    if (sub or "").strip().lower() in ("", "none", "unknown"):
        sub = None
    topics = aud.get("_topics") or []
    source_url = st.get("source_url")
    left_out = []

    if not brand or not avatar:
        return {"research": "# Research\n\n[UNFILLED: no avatar decided yet for this run — "
                            "research needs stage 1b to have run first]\n"}

    rooms, words, discovery = resolve_rooms(brand, avatar, sub, topics)
    for d in (discovery or {}).get("dropped") or []:
        left_out.append(f"r/{d['room']} — dropped, demographic mismatch: {d['fit']['why']}")
    if not rooms:
        left_out.append("no rooms recorded for this avatar and discovery came back empty "
                        "— the forums pull was skipped")

    if out_dir is None:
        run_dir_fn = (chain_profile or {}).get("run_dir")
        rd = run_dir_fn(st) if run_dir_fn else None
        # No chain-named run folder (no `run_dir` in the profile, or it
        # returned None) still needs somewhere real to land — the repo-root
        # `runs/` tree, never this component's own folder.
        out_dir = (Path(rd) / "research") if rd else (WORKSPACE / "runs" / "research" / "_unfiled")
    out_dir = Path(out_dir)

    forums = pull_forums(brand, avatar, sub, rooms, words, _cap("forums_per_run", 40),
                         out_dir / "_forums_raw")
    comments = pull_comments(source_url, _cap("comments_per_post", 60))

    forums_md = render_forums_md(forums, words)
    comments_md = (render_comments_md(comments["rows"], source_url) if comments["ok"]
                  else f"# Comments\n\n{comments['md']}\n")
    funnel = aud.get("_funnel") or aud.get("funnel")
    language_md = render_language_md(brand, avatar, chain_profile, funnel, topics)

    if not comments.get("ok"):
        left_out.append(comments["md"].strip("[]"))

    rooms_md = render_rooms_md(discovery)
    demo = (discovery or {}).get("demographics")
    if demo is None:
        demo = demographics(brand, avatar, sub)
    spend_total = round((forums.get("spend") or 0) + (comments.get("spend") or 0)
                        + ((discovery or {}).get("spend") or 0), 3)
    research_md = render_research_md(brand, avatar, sub, language_md, forums_md, comments_md,
                                     spend_total, left_out, rooms_md=rooms_md, demo=demo)

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "rooms-found.json").write_text(json.dumps(discovery or {}, indent=1, default=str))
        (out_dir / "language.md").write_text(language_md)
        (out_dir / "forums.md").write_text(forums_md)
        (out_dir / "comments.md").write_text(comments_md)
        (out_dir / "research.md").write_text(research_md)
    except Exception:
        pass  # a filesystem hiccup here must never be why a stage fails

    print(f"research-gatherer: ${spend_total:.3f} this run "
         f"(forums {'cache' if forums.get('cached') else '$' + str(forums.get('spend', 0))}, "
         f"comments {'cache' if comments.get('cached') else '$' + str(comments.get('spend', 0))})",
         file=sys.stderr)
    return {"research": research_md}


def inputs(st, chain_profile=None):
    """The engine's own `~research` implementation. A chain's shim
    re-exports this bound to its own `chain_profile` so `run.py` keeps
    calling a plain `inputs(st)`. NEVER raises — any unexpected failure
    becomes a section that says so, not a stopped chain."""
    try:
        return _inputs_core(st, chain_profile)
    except Exception as e:
        return {"research": f"# Research\n\n[UNFILLED: the research gatherer failed — {e}]\n"}


def run_over(st, chain_profile=None, out_dir=None):
    """Same as `inputs()`, with an explicit output folder — for a chain's
    own `run --run <dir>` CLI, driven over a run already on disk rather
    than one mid-chain. NEVER raises, same guarantee as `inputs()`."""
    try:
        return _inputs_core(st, chain_profile, out_dir=out_dir)
    except Exception as e:
        return {"research": f"# Research\n\n[UNFILLED: the research gatherer failed — {e}]\n"}


# ---------------------------------------------------------------- deep mode (chain-agnostic)

def all_sub_avatars(root=None):
    out = []
    brands_dir = (Path(root) if root else WORKSPACE) / "brands"
    if not brands_dir.is_dir():
        return out
    for bd in sorted(brands_dir.iterdir()):
        if not bd.is_dir() or bd.name.startswith("_"):
            continue
        cores = bd / "core-avatars"
        if not cores.is_dir():
            continue
        for ad in sorted(cores.iterdir()):
            if not ad.is_dir():
                continue
            sdir = ad / "sub-avatars"
            if not sdir.is_dir():
                continue
            for f in sorted(sdir.glob("*.md")):
                out.append(dict(brand=bd.name, avatar=ad.name, sub=sub_slug(f), file=f))
    return out


def row_count(brand, avatar, sub, root=None):
    """Depends on `language_layer` only for this one count — imported
    lazily so a caller that never touches `deep` mode never needs it on
    its path."""
    sys.path.insert(0, str(WORKSPACE / "components" / "language-layer"))
    from language_layer import engine as _lang
    rows = _lang.load(brand, avatar, root=root)
    return sum(1 for r in rows if r.get("sub") == sub)


def pick_thinnest(root=None):
    cands = all_sub_avatars(root)
    if not cands:
        return None, []
    for c in cands:
        c["rows"] = row_count(c["brand"], c["avatar"], c["sub"], root)
    ranked = sorted(cands, key=lambda c: (c["rows"], c["brand"], c["avatar"], c["sub"]))
    return ranked[0], ranked


def build_bank_rows(brand, avatar, sub, posts_by_ref, comments_by_ref, demo=None,
                    dropped_out=None):
    """The bank's own schema (brands/language-schema.md). A row with no
    permalink never enters — `posts_by_ref`/`comments_by_ref` are keyed by
    ref, so an empty key is the drop signal, checked again here.

    AND (the owner, 2026-09-18) every row carries the demographic verdict of the
    room it came from, in a `fit` field; a row from a room the check says `no`
    to is NEVER filed. `dropped_out`, when a list is handed in, collects those
    rows so a run record can show what was thrown away and why."""
    door = reddit_door()
    demo = demographics(brand, avatar, sub) if demo is None else demo
    fits = {}
    entries = []
    i = 0
    for speaker, bucket in (("prospect", posts_by_ref), ("commenter", comments_by_ref)):
        for ref, slot in bucket.items():
            r = slot["row"]
            title = (r.get("title") or "").strip()
            body = (r.get("body") or r.get("selftext") or "").strip()
            text = f"{title} — {body}" if title and body else (title or body)
            if not text or not ref:
                continue
            room = _room_name(r) or "reddit"
            if room not in fits:
                fits[room] = room_fit(room, demo)
            fit = fits[room]
            if fit["fit"] == "no":
                if dropped_out is not None:
                    dropped_out.append({"room": room, "ref": ref, "text": text[:2000],
                                        "speaker": speaker, "fit": fit})
                continue
            i += 1
            entries.append({
                "id": f"{sub}-{date.today().isoformat()}-{i:04d}",
                "text": text[:2000],
                "avatar": avatar,
                "sub": sub,
                "funnel": "prospect",
                "speaker": speaker,
                "source": {"name": f"reddit r/{room}", "type": "community",
                          "date": door.when(r), "ref": ref},
                "signal": {"likes": door.score(r), "tier": "community"},
                "topics": [],
                "use": sorted(slot["tags"]) or ["subculture"],
                "status": "active",
                "fit": {"room": f"r/{room}", "verdict": fit["fit"], "why": fit["why"]},
            })
    return entries


def _write_deep_run_record(out_root, brand, avatar, sub, entries, spend, plan, is_fallback,
                           room_band=None, diff_band=None, discovery=None, demo=None,
                           dropped_rows=None):
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "rows.json").write_text(json.dumps(entries, indent=1))
    (out_root / "rooms-found.json").write_text(json.dumps(discovery or {}, indent=1, default=str))
    if dropped_rows:
        (out_root / "rows-dropped-demographic-mismatch.json").write_text(
            json.dumps({"brand": brand, "avatar": avatar, "sub": sub,
                        "date": date.today().isoformat(),
                        "why": "the room these rows came from does not match this avatar's "
                               "demographics (the owner, 2026-09-18) — never filed into the bank",
                        "demographics": demo or {}, "rows": dropped_rows}, indent=1))
    L_ = [f"# Deep research — {brand} / {avatar} / {sub}", "", METHOD_HEADER, "",
         "**demographics** (what every room was reconciled against): "
         + demographics_line(demo if demo is not None
                             else (discovery or {}).get("demographics")), "",
         f"**{len(entries)} rows written**, ${spend:.3f} spent, {len(plan)} question(s) fired"
         + (" (fallback question bank — components/marketing-doctrine/frameworks.json "
            "not found or empty)" if is_fallback else "") + ".", "",
         "## Rooms — where this avatar actually talks", "",
         render_rooms_md(discovery), ""]
    if dropped_rows:
        L_ += [f"**{len(dropped_rows)} row(s) were pulled and NOT filed** — their room does not "
               "match this avatar's demographics; they are kept in "
               "`rows-dropped-demographic-mismatch.json` beside this file.", ""]
    if room_band is not None:
        door = reddit_door()
        L_.append(f"## Band 1 — the room ({len(room_band)} posts, top half by score)\n")
        for s in room_band[:15]:
            r = s["row"]
            L_.append(f"- **{door.score(r) or 0}** · {r.get('url') or r.get('link') or ''} "
                      f"— \"{(r.get('title') or '')[:140]}\"")
        L_.append(f"\n## Band 2 — the different band ({len(diff_band)} posts, bottom half by score)\n")
        for s in diff_band[:15]:
            r = s["row"]
            L_.append(f"- **{door.score(r) or 0}** · {r.get('url') or r.get('link') or ''} "
                      f"— \"{(r.get('title') or '')[:140]}\"")
    L_.append("\n## Questions fired\n")
    for p in plan:
        q = p["question"]
        L_.append(f"- `{q['id']}` ({', '.join(q.get('tags') or [])}): \"{p['query']}\"")
    (out_root / "research.md").write_text("\n".join(L_))
    (out_root / "run.json").write_text(json.dumps(dict(
        brand=brand, avatar=avatar, sub=sub, date=date.today().isoformat(),
        rows_written=len(entries), spend=round(spend, 3),
        fallback_questions=is_fallback), indent=1))


def deep_for(brand, avatar, sub, cap, dry_run=False):
    """Pulls for ONE sub-avatar and files rows into ITS OWN bank
    (C2 — the 2026-09-18 exception to "a person moves it"). Never invents a
    room: no `### rooms` block anywhere for this avatar means nothing is
    pulled, ever, dry-run or not."""
    f = sub_file(brand, avatar, sub) or next(
        (c["file"] for c in all_sub_avatars() if c["brand"] == brand and c["avatar"] == avatar and c["sub"] == sub),
        None)
    if f is None:
        # the inputs gate, with no run folder to write into: a mistyped brand
        # must not leave a folder behind under runs/
        G.record("inputs", G.inputs_problems(False, []), None)
        return dict(ok=False, why=f"no sub-avatar file found for {brand}/{avatar}/{sub}",
                    held="inputs")

    text = f.read_text()
    state, _m = rooms_block_state(text)
    demo = demographics(brand, avatar, sub, sub_path=f)
    # DISCOVERY FIRST unless a person has confirmed the block (the owner, 2026-09-18).
    # A dry run discovers nothing — it spends nothing, by contract — and says
    # instead what the real run would go and look for.
    # THE ELEMENTS GATE, before a cent is spent (rollout 2026-09-20): every
    # doctrine technique / delivery dial a research question names is asked of
    # the element library. An unknown one holds the pull, with the real ids
    # named — `research.json` > gates > elements: "record" writes it down and
    # pulls anyway (the behaviour before this gate existed).
    questions, is_fallback = schwartz_questions()
    el_problems, el_checked = G.question_problems(questions)
    out_root = _deep_runs_root() / brand / f"{sub}-{date.today().isoformat()}"
    if el_problems and not dry_run and _gate_mode("elements") == "hold":
        G.record("elements", el_problems, out_root)
        return dict(ok=False, held="elements", rows_written=0, spend=0.0,
                    why="HELD at the elements gate — " + "; ".join(el_problems),
                    problems=el_problems, out=str(out_root))

    rooms, words, discovery = resolve_rooms(brand, avatar, sub, root=None,
                                            discover=not dry_run, sub_path=f)
    plan = build_queries_per_question(words, questions)

    if dry_run:
        return dict(ok=True, dry_run=True, rooms=rooms, words=words, fallback_questions=is_fallback,
                    rooms_state=state, would_discover=(state != "confirmed"),
                    discovery_query=discovery_query(words), demographics=demo,
                    elements_checked=el_checked, elements_problems=el_problems,
                    queries=[dict(question=p["question"]["id"], tags=p["question"].get("tags"),
                                  query=p["query"]) for p in plan])

    if not rooms:
        G.record("inputs", G.inputs_problems(True, rooms), out_root)
        return dict(ok=False, why="no rooms on file and discovery came back empty — "
                                  "nothing pulled, no room invented",
                    rows_written=0, spend=0.0, discovery=discovery, held="inputs",
                    out=str(out_root))
    G.record("inputs", [], out_root)
    if not el_checked:
        el_note = ["the element library could not be asked — the research questions' "
                   "doctrine terms were NOT checked on this pull"]
    else:
        el_note = ["(recorded only — research.json gates.elements is 'record') " + p
                   for p in el_problems]
    G.record("elements", el_note, out_root)

    per_q_cap = max(5, cap // max(1, len(plan)))
    pulled = no_receipt = 0
    posts_by_ref, comments_by_ref = {}, {}
    spend_total = float((discovery or {}).get("spend") or 0.0)

    for p in plan:
        q = p["question"]
        try:
            rows, _md, spend = _run_reddit(rooms, [p["query"]], per_q_cap, out_root / "_raw" / q["id"])
        except SystemExit as e:
            print(f"  {q['id']}: [UNFILLED] {e}")
            continue
        except Exception as e:
            print(f"  {q['id']}: [UNFILLED] {e}")
            continue
        spend_total += spend
        posts, comments = _split_posts_comments(rows)
        pulled += len(posts) + len(comments)
        no_receipt += sum(1 for r in list(posts) + list(comments)
                          if not (r.get("url") or r.get("link") or r.get("permalink")))
        for r in posts:
            ref = r.get("url") or r.get("link") or r.get("permalink")
            if not ref:
                continue
            slot = posts_by_ref.setdefault(ref, {"row": r, "tags": set()})
            slot["tags"] |= set(q.get("tags") or [])
        for r in comments:
            ref = r.get("url") or r.get("link") or r.get("permalink")
            if not ref:
                continue
            slot = comments_by_ref.setdefault(ref, {"row": r, "tags": set()})
            slot["tags"] |= set(q.get("tags") or [])

    dropped_rows = []
    entries = build_bank_rows(brand, avatar, sub, posts_by_ref, comments_by_ref, demo=demo,
                              dropped_out=dropped_rows)
    # THE DELIVERY GATE — before a row enters the avatar's bank. What passes is
    # what passed before (build_bank_rows did the dropping); this writes the
    # verdict into the run's check.json, so a pull that files nothing reads HELD.
    held = G.record("delivery", G.delivery_problems(entries, pulled=pulled, no_receipt=no_receipt,
                                                    dropped=len(dropped_rows)), out_root)
    if not entries or held:
        _write_deep_run_record(out_root, brand, avatar, sub, [], spend_total, plan, is_fallback,
                               discovery=discovery, demo=demo, dropped_rows=dropped_rows)
        return dict(ok=True, rows_written=0, spend=round(spend_total, 3), sample=[],
                    out=str(out_root), rooms=rooms, discovery=discovery,
                    rows_dropped=len(dropped_rows), demographics=demo,
                    held="delivery", problems=held)

    # Every row the gatherer writes carries the proposal's fields (lane by
    # language, awareness, sophistication — tools/language-layer/docs/STANDARD.md,
    # 2026-09-28). Optional: with no model or no doctrine the rows go out as before.
    try:
        from . import annotate as _A
        oc = _config().get("ownvoice", {})
        entries = _A.enrich_deep(entries, brand, avatar, sub, brand, oc.get("model", "claude-sonnet-5"),
                                 oc.get("batch", 30))
    except Exception as e:  # never fail a pull over the enrichment
        print(f"  annotate skipped: {type(e).__name__}: {e}")

    # The avatar's language tree is the only place the language layer reads
    # (`<avatar>/language/**/*.json`); a sub-avatar is a `sub` field on each
    # row, never a folder of its own (brands/language-schema.md rule 4).
    dest = sub_home(brand, avatar, sub) / "language" / f"deep-research-{date.today().isoformat()}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"schema": 1, "avatar": avatar, "sub": sub, "entries": entries}, indent=1))

    room_band, diff_band = two_bands(list(posts_by_ref.values()), lambda s: reddit_door().score(s["row"]))
    _write_deep_run_record(out_root, brand, avatar, sub, entries, spend_total, plan, is_fallback,
                           room_band=room_band, diff_band=diff_band, discovery=discovery,
                           demo=demo, dropped_rows=dropped_rows)
    # The CLEAN copy — only what passed the gates — under the sub-avatar's own
    # folder, beside its rows. Raw (everything pulled, the dropped rows and
    # why, spend, cache) stays in runs/research/.
    try:
        clean = sub_home(brand, avatar, sub) / "research" / date.today().isoformat()
        clean.mkdir(parents=True, exist_ok=True)
        for name in ("research.md", "rooms-found.json", "rows.json"):
            src = out_root / name
            if src.is_file():
                (clean / name).write_text(src.read_text())
        (clean / "RAW.md").write_text(f"Raw pull, dropped rows and spend: `{out_root}`\n")
    except Exception as e:  # never fail a pull over the clean copy
        print(f"  clean copy not written: {type(e).__name__}: {e}")

    return dict(ok=True, rows_written=len(entries), spend=round(spend_total, 3),
               sample=entries[:5], bank_file=str(dest), out=str(out_root),
               room_count=len(room_band), diff_count=len(diff_band),
               rooms=rooms, discovery=discovery, rows_dropped=len(dropped_rows),
               demographics=demo)


# ---------------------------------------------------------------- CLI (deep mode only — chain-agnostic)

def main(argv=None):
    import argparse
    argv = list(sys.argv[1:] if argv is None else argv)
    # An optional leading mode word. `deep` is the default so every call that
    # worked before this existed still works verbatim.
    mode = "deep"
    if argv and argv[0] in ("deep", "rooms"):
        mode = argv.pop(0)
    ap = argparse.ArgumentParser(
        description="The deep-research trigger and the room finder — chain-agnostic. "
                    "`inputs(st, chain_profile)` is a library call; a chain's own shim "
                    "exposes the `run` CLI over it with its own chain_profile.")
    ap.add_argument("--brand")
    ap.add_argument("--avatar")
    ap.add_argument("--sub")
    ap.add_argument("--all", action="store_true", help="every sub-avatar of --brand")
    ap.add_argument("--pick-thinnest", action="store_true",
                    help="across ALL brands, the sub-avatar with the fewest language rows")
    # Resolved per mode below, so `rooms` can default small (one discovery
    # search) while `deep` keeps its own, bigger default.
    ap.add_argument("--cap", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true", help="print the queries; spend nothing")
    a = ap.parse_args(argv)

    if a.pick_thinnest:
        picked, ranked = pick_thinnest()
        if not picked:
            sys.exit("no sub-avatars found anywhere in brands/")
        # `--brand B --pick-thinnest` narrows the pick to that brand's own
        # sub-avatars (2026-09-19, the nightly pull: one pick per brand per
        # night, so a brand with a thick bank never starves a thin one).
        scope = "all brands"
        if a.brand:
            ranked = [c for c in ranked if c["brand"] == a.brand]
            if not ranked:
                sys.exit(f"{a.brand} has no sub-avatars on file")
            picked, scope = ranked[0], a.brand
        print(f"pick-thinnest: {picked['brand']}/{picked['avatar']}/{picked['sub']} "
             f"({picked['rows']} language rows on file — thinnest of {len(ranked)}, {scope})")
        targets = [picked]
    elif a.all:
        if not a.brand:
            sys.exit("--all needs --brand")
        targets = [c for c in all_sub_avatars() if c["brand"] == a.brand]
        if not targets:
            sys.exit(f"{a.brand} has no sub-avatars on file")
    else:
        if not (a.brand and a.avatar and a.sub):
            sys.exit("name --brand --avatar --sub, or pass --all / --pick-thinnest")
        targets = [dict(brand=a.brand, avatar=a.avatar, sub=a.sub)]

    if mode == "rooms":
        for t in targets:
            print(f"\n== {t['brand']} / {t['avatar']} / {t['sub']} ==")
            texts = _avatar_texts(t["brand"], t["avatar"], t["sub"], None, t.get("file"))
            state = rooms_block_state(texts[0][1])[0] if texts else "none"
            words = _words_from(texts)
            demo = demographics(t["brand"], t["avatar"], t["sub"], sub_path=t.get("file"))
            print(f"  demographics: {demographics_line(demo)}")
            print(f"  rooms block on file: {state}"
                  + ("  (a person confirmed it — discovery would not run)"
                     if state == "confirmed" else ""))
            if a.dry_run:
                print(f"  would search: \"{discovery_query(words)}\"  "
                      f"(unrestricted, sort top, window year, cap {a.cap or _cap('discovery', 40)})")
                print("  --dry-run: nothing pulled, nothing spent")
                continue
            det = _find_rooms_detail(t["brand"], t["avatar"], t["sub"],
                                     cap=a.cap or _cap("discovery", 40), sub_path=t.get("file"))
            if not det.get("ok"):
                print(f"  [UNFILLED] {det.get('why')}")
                continue
            print(f"  query: \"{det['query']}\"  ·  "
                  + ("from cache, $0.000" if det.get("cached") else f"${det['spend']:.3f}"))
            if not det["rooms"] and not (det.get("dropped") or []):
                print("  no rooms came back")
                continue
            for r in det["rooms"]:
                print(f"    KEPT    r/{r['room']:<26} {r['posts']:>3} post(s)  {r['score']:>6} score  "
                      f"\"{(r.get('sample_title') or '')[:60]}\"")
            for r in det.get("dropped") or []:
                print(f"    DROPPED r/{r['room']:<26} {r['posts']:>3} post(s)  {r['score']:>6} score")
                print(f"            {r['fit']['why']}")
            target = texts[0][0] if texts else None
            if target and state != "confirmed":
                changed = write_rooms_block(target, det["rooms"], dropped=det.get("dropped"))
                print(f"  {'written back into' if changed else 'unchanged:'} {target}")
        return 0

    for t in targets:
        print(f"\n== {t['brand']} / {t['avatar']} / {t['sub']} ==")
        res = deep_for(t["brand"], t["avatar"], t["sub"],
                       a.cap or _cap("forums_per_deep", 150), dry_run=a.dry_run)
        if res.get("dry_run"):
            print(f"  rooms block on file: {res.get('rooms_state')}"
                  + ("  -> discovery WOULD run first (nothing discovered on a dry run)"
                     if res.get("would_discover") else "  (confirmed by a person — used as written)"))
            print(f"  rooms: {res['rooms'] or '(none on file yet — discovery would find them)'}")
            print(f"  words: {res['words']}")
            print(f"  discovery would search: \"{res.get('discovery_query')}\"")
            if not res.get("elements_checked"):
                print("  elements gate: the element library could not be asked")
            for p in res.get("elements_problems") or []:
                print(f"  elements gate WOULD HOLD: {p}")
            if res.get("fallback_questions"):
                print("  (fallback question bank — components/marketing-doctrine/frameworks.json not found)")
            for q in res["queries"]:
                print(f"    {q['question']:<20} {q['tags']}: \"{q['query']}\"")
            continue
        if not res.get("ok"):
            print(f"  [UNFILLED] {res.get('why')}")
            if res.get("held"):
                print(f"  HELD at the {res['held']} gate"
                      + (f" — {res['out']}/check.json" if res.get("out") else ""))
            continue
        if res.get("held"):
            print(f"  HELD at the {res['held']} gate — {res.get('out')}/check.json")
            for p in res.get("problems") or []:
                print(f"    - {p}")
        if res.get("discovery", {}).get("source") == "discovery":
            for r in res["discovery"].get("rooms") or []:
                print(f"    found   r/{r['room']:<26} {r['posts']:>3} post(s)  {r['score']:>6} score")
            for r in res["discovery"].get("dropped") or []:
                print(f"    dropped r/{r['room']:<26} demographic mismatch — {r['fit']['why'][:90]}")
        print(f"  rows written: {res['rows_written']}  spend: ${res['spend']:.3f}"
              + (f"  ({res['rows_dropped']} row(s) dropped on demographic fit)"
                 if res.get("rows_dropped") else ""))
        for s in res.get("sample", [])[:5]:
            print(f"    - {s['text'][:100]!r} — {s['source']['ref']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
