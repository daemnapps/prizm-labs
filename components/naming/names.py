#!/usr/bin/env python3
"""Ad names and batch manifests — the join key back to Meta spend.

    names.py next-batch <brand>            the next free batch id for today
    names.py check <name> [name...]        does this parse (old or new form)
    names.py parse <name>                  show its fields
    names.py brief-id <p140|brief-0140>    the one brief id, either spelling

See CONVENTION.md. The name carries what you group by; the manifest carries
everything else and is joined to Meta's report on the name itself.

TWO FORMS, ONE DICT (Master Plan v2, 3.3 — 2026-09-28). The rule, locked:
everything lowercase; "-" joins words INSIDE a value; "_" joins values; every
value exists in its list; type-first references.

    new  <brand>_glow-body-scrub_static_ai_none_spot-cover_dark-spots_
         tone-memory_hands-application_photo-strip_brief-0140_9x16_
         batch-2026-09-02-a_asset-01
    old  <brand>-bodyscrub-static-ai-none-spotcover-darkspots-tonememory-
         handsapplication-photostrip-p140-9x16-260902a-a01

Tools READ both (parse_any) and WRITE the new form (ad_name, asset_name).
The live Meta ads keep their old names until the alias layer is green
(decision 9), so the old form is not legacy — it is what the account says.
"""
import argparse, datetime as dt, json, re, sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / "run-kit"))     # appended, never ahead of this tool
sys.path.append(str(Path(__file__).resolve().parent.parent / "brandpath"))
from run_kit.paths import repo as _repo  # noqa: E402  the one workspace locator
try:
    import brandpath as BP               # noqa: E402  the brand-folder map, where a workspace has one
except ImportError:
    class BP:                            # brands/<brand>/<folder>/… as laid out in brands/_TEMPLATE
        @staticmethod
        def brand_path(brand, key, *rest, root=None):
            return Path(root).joinpath(brand, key, *rest)

# SEAM (CLAUDE.md, public interface 4): video-edit deliver.py:92 asks which workspace a
# RUN sits in, from the run's own path. Kept as written until that caller moves; WS below
# is run-kit's repo().
def _workspace_root(start=None):
    """Walk up to the workspace, rather than counting folders.

    This used to be parents[3], which was the root only while this file sat
    three deep in lab/. It graduated to components/naming/ on 2026-09-11 and
    every brand lookup silently pointed at the wrong place. A marker cannot
    go quietly wrong the next time something moves.
    """
    p = (start or Path(__file__)).resolve()
    for d in p.parents:
        if (d / "brands").is_dir() and ((d / "CLAUDE.md").is_file() or (d / "components").is_dir()):
            return d
    raise RuntimeError("not inside the ai-workspace")


WS  = _repo(Path(__file__))
# Every lane names assets the same way, so every run root is scanned when
# picking the next free batch letter for a day. The real root is runs/ — every
# lane files under runs/<lane>/<brand>/ (runs/README.md), so the whole folder
# is walked rather than a list of lanes that goes stale the day a lane is
# added. The older home stays on the list so a batch delivered before a move
# still counts as taken (a letter is never reused).
RUNS = [WS / "runs",                                   # every lane: runs/<lane>/<brand>/...
        WS / "records" / "runs"]                       # older
# Six fields name the AD UNIT — what Meta reports on. The filename is that
# same name plus a seventh field for the asset, because every variation of a
# concept is uploaded into ONE ad unit and Meta returns one row for all of
# them. Putting the asset id in the ad name would have six files claiming
# one row.
# Grounded in the names already running in a live ad account, read
# 2026-09-02 — `ai_bs_p133_h1-3_v4_Coco`, `ugc_fullritual_review_andrea`,
# `static_mothers-day_gifttoself_p001`. Those carry source, product, talent
# and version, and a scheme without them cannot answer the questions the
# account is already being asked.
# problem -> angle -> concept is a hierarchy, not one field. A problem has
# many angles; an angle has many concepts. Collapsing them into "concept"
# meant a winning ad could not be traced back to the problem it solved or
# the angle that framed it, which is the thing worth repeating.
#   problem  the customer's problem            darkspots
#   angle    the angle taken on that problem   (signed in strategy/angles.json)
#   concept  the ideation and execution of it  handsapplication
AD_FIELDS = ["brand", "product", "media", "source", "talent", "avatar",
             "problem", "angle", "concept", "format", "brief", "ratio",
             "batch"]
# "static" is the performance-marketing word for a single-image ad, and it is
# what the buyer says out loud. A name nobody uses in conversation is a name
# that gets typed wrong.
MEDIA = {"static", "video", "carousel"}
# Who made the picture. The single most valuable split once AI and creator
# content run side by side, and recoverable from nothing else.
SOURCE = {"ai", "ugc", "studio", "mixed"}
FIELDS = AD_FIELDS + ["asset"]
# A value: letters, digits, "-" between words. No leading or trailing "-".
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# The old form squashed words, so its values carry no "-" at all.
OLD_SLUG = re.compile(r"^[a-z0-9]+$")
# The two brief spellings. p140 -> brief-0140, same number.
BRIEF_OLD = re.compile(r"^p(\d{3})$")
BRIEF_NEW = re.compile(r"^brief-(\d{4})$")
# A brief numbered per brand AND product (the owner, 2026-10-01) is identified by
# all three: `acme_serum_brief-0004`. The register keys new briefs this way.
BRIEF_KEY = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)_([a-z0-9]+(?:-[a-z0-9]+)*)_(brief-(\d{4}))$")
# The two batch spellings. 260902a -> batch-2026-09-02-a.
BATCH_OLD = re.compile(r"^(\d{2})(\d{2})(\d{2})([a-z])$")
BATCH_NEW = re.compile(r"^batch-(\d{4})-(\d{2})-(\d{2})-([a-z])$")
# The two asset spellings. a01 -> asset-01.
ASSET_OLD = re.compile(r"^a(\d{2})$")
ASSET_NEW = re.compile(r"^asset-(\d{2})$")
SEP = "_"                       # joins values in the new form
OLD_SEP = "-"                   # joined values in the old form

# ---------------------------------------------------------------- shared ---
# The fields that describe A CREATIVE, whoever made it. A competitor's ad and
# one of ours are the same kind of object: something with a form, a maker, a
# person in it, a problem it speaks to, an angle on that problem, an execution
# of the angle, a template and a frame. Everything else in AD_FIELDS is ours
# alone — our brand, our product, our avatar, our brief, our batch.
#
# The swipe library describes its ads in exactly these words, so a Meta export
# grouped on `problem` or `source` and the swipe corpus grouped on the same
# field are answering one question, not two. Two vocabularies for one idea is
# how you end up unable to say whether the thing that won was the thing you
# swiped.
CREATIVE_FIELDS = ["media", "source", "talent", "problem", "angle", "concept",
                   "format", "ratio"]
# A field a human has not judged yet. Written, never blank: a blank reads as
# "no person in it" (which is `none`) and quietly becomes an answer.
UNCLASSIFIED = "unclassified"
# The id is the ad tool's number, or a page swipe's slug (`pages-acne`).
SWIPE_REF = re.compile(r"^swipe:([a-z0-9]+):([a-z0-9-]+)$")


def swipe_id(brand, ad_id):
    """The reference a production manifest keeps for the ad it was built from.

    `swipe:resilia:162098799` — competitor brand and the id the ad tool gave
    it. Not a description and not a path: the Drive file gets renamed, the
    teardown gets rewritten, and this still resolves.

    It lives in the manifest rather than in the ad name for the same reason
    the prompt and the plate do: the name carries what you group by, and you
    do not group a report by which competitor an idea came from — you look it
    up once you have a winner."""
    return f"swipe:{slug(brand)}:{int(ad_id)}"


def swipe_source_key(s):
    """The source segment of a swipe-corpus id: lowercase letters and digits
    only — hyphens, underscores, spaces and punctuation are all dropped
    (`4bu_m` -> `4bum`, `alpha--some-sub` -> `alphasomesub`).

    Deliberately NOT slug() and NOT slug_ref(). Swipe-corpus ids predate the
    2026-09-28 slug change (which let "-" survive inside a value), and every
    stored row — intake's swipes.jsonl, swipe-paid's frames.json and
    judgements.json — uses this hyphenless form. Moving it to slug() would
    orphan all of them."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def corpus_swipe_id(lane, source, ref):
    """The id of one swipe-corpus row: `swipe:<lane>:<source key>:<ref>`.

    intake (components/intake/tools/pools.py record()) and swipe-paid
    (components/swipe-paid/corpus.py row()) both build swipe ids ONLY through
    this function, so the two sides cannot drift (two private slugs did once:
    the doubled NN_ prefix). The source segment is swipe_source_key(), the
    stored hyphenless form — see its docstring for why it is not slug()."""
    return f"swipe:{lane}:{swipe_source_key(source)}:{ref}"


def parse_swipe_id(ref):
    """(brand, ad_id) or None. ad_id is an int for an ad tool's number, the
    string for a page swipe's id."""
    m = SWIPE_REF.match((ref or "").strip())
    if not m:
        return None
    i = m.group(2)
    return (m.group(1), int(i) if i.isdigit() else i)


FORMAT_REF = re.compile(r"^format:([a-z0-9-]+):([a-z0-9-]+)(?::([A-Za-z0-9._-]+))?$")


def _registry():
    import json
    return json.loads((Path(__file__).resolve().parent / "registry.json").read_text())


def format_ref(asset, bank, brand=None):
    """The reference a tool keeps for a vocabulary, instead of a file path.

    `format:organic-video:format` — the organic video structures.
    `format:<brand>:email:design-format` — one brand's own email templates.

    Same grammar as swipe_id() above, brand in the same position, for the same
    reason: a path moves and a name does not. The organic library rendered as
    a blank page for days because every consumer hard-coded its path and
    nothing anywhere noticed it had stopped resolving.

    A per-brand bank REQUIRES the brand segment. Without it
    `format:email:design-format` does not say whose FMT-04, and two brands
    both have one."""
    return (f"format:{slug_ref(brand)}:{slug_ref(asset)}:{slug_ref(bank)}" if brand
            else f"format:{slug_ref(asset)}:{slug_ref(bank)}")


def parse_format_ref(ref):
    """(brand, asset, bank) or None. brand is None for a brand-agnostic bank."""
    m = FORMAT_REF.match((ref or "").strip())
    if not m:
        return None
    a, b, c = m.groups()
    return (a, b, c) if c else (None, a, b)


def resolve_format(ref):
    """A reference -> the registry row, or None if nothing is registered.

    Raises on an EVIDENCE path: evidence has no address on purpose. Asking for
    one is the mistake the rule exists to catch, so it fails loudly rather
    than handing back something that looks pickable."""
    parsed = parse_format_ref(ref)
    if not parsed:
        return None
    brand, asset, bank = parsed
    for row in _registry()["banks"]:
        if row["asset"] == asset and row["id"] == bank:
            if row["brand"] and not brand:
                raise ValueError(
                    f"{ref} is a per-brand bank and carries no brand — "
                    f"say format:<brand>:{asset}:{bank}")
            return {**row, "brand_asked": brand}
    return None


def slug_ref(s):
    """A reference segment. Unlike slug(), a hyphen SURVIVES here — the asset
    tokens are already written with hyphens (organic-video, image-ad) and the
    reference is split on colons, not on hyphens, so there is no column to
    protect."""
    return re.sub(r"[^a-z0-9-]", "", str(s).lower())


def slug(s):
    """One value's worth of characters: lowercase letters, digits, and "-"
    between words. Spaces, underscores and punctuation become "-"; a run of
    them becomes one; none survives at either end.

    Until 2026-09-28 the hyphen was stripped, because "-" was the joint
    between values and a hyphen inside one would have added a column to
    every downstream split. The joint is now "_", so the hyphen is free to do
    what it does everywhere else in the system: join the words of one value
    (`glow-body-scrub`, `spot-cover`, `brief-0140`)."""
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9-]+", "-", str(s).lower())).strip("-")


SUB_ORDER = re.compile(r"^sub-\d{2}-")


def sub_key(s):
    """The canonical sub-avatar slug — the bare story slug.

    Cards are filed as `sub-02-bald-bumps-guy.md`; the `sub-NN-` prefix is
    reading order inside one core's folder, not identity. The language bank
    and the swipe records already key on the bare slug, so a record that
    stored `sub-02-bald-bumps-guy` would never join to them. Strips the
    prefix and any extension: a card path, a card stem or a bare slug all
    give the same key. `None` stays `None` — undeclared is never guessed."""
    if s is None:
        return None
    return SUB_ORDER.sub("", Path(str(s)).stem.strip().lower()) or None


def signed_angles(brand):
    """The angles the brand has actually signed.

    `strategy/angles.json` is the one angle source, and its own rule is "no
    receipt, no entry; only the owner signs an angle active". A naming scheme
    that let anyone type a new angle into a filename would quietly create a
    second, unsigned vocabulary — and the reports would then be grouped on
    words nobody ruled."""
    f = BP.brand_path(slug(brand), "strategy", "angles.json", root=WS / "brands")
    if not f.is_file():
        return None
    try:
        active = [a for a in json.loads(f.read_text()).get("angles", [])
                  if a.get("status") == "active"]
    except (json.JSONDecodeError, OSError):
        return None
    signed = {slug(a.get("id") or a.get("name")): a for a in active}
    # An angle renamed to the two-mark form keeps its old squashed id in
    # `was`, so an old-form ad name (`tonememory`) still reads as signed.
    signed.update({slug(a["was"]): a for a in active if a.get("was")})
    return signed


def check_angle(brand, angle):
    """Warn, never block. An unsigned angle is a strategy gap to close, not
    a reason to stop a batch from shipping."""
    known = signed_angles(brand)
    if known is None:
        return f"no angle source for {brand} — angle '{angle}' is unverified"
    if not known:
        return (f"{brand} has no signed angles yet (strategy/angles.json is "
                f"empty by design — only the owner signs one active), so "
                f"'{angle}' is unverified")
    if slug(angle) not in known and slug(angle) != "unsigned":
        return (f"'{angle}' is not a signed angle for {brand}. Signed: "
                + ", ".join(sorted(known)))
    return None


_ALIASES = None


def brief_aliases():
    """brief-aliases.json — every brief number in both spellings, and the
    numbers that were never used. Read once."""
    global _ALIASES
    if _ALIASES is None:
        f = Path(__file__).resolve().parent / "brief-aliases.json"
        try:
            _ALIASES = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            _ALIASES = {"aliases": {}, "never_used": []}
    return _ALIASES


def add_alias(bid, new, path=None):
    """Write `bid -> new` (`p140 -> brief-0140`) into brief-aliases.json and
    drop the cached copy, so the next lookup reads it. Writes only when the
    entry is missing or different. `path` is for tests — a temp copy; the
    default is this folder's own file (SI-121 (teardown stops reaching))."""
    global _ALIASES
    f = Path(path) if path else Path(__file__).resolve().parent / "brief-aliases.json"
    al = json.loads(f.read_text()) if f.is_file() else {"aliases": {}}
    if al.setdefault("aliases", {}).get(bid) != new:
        al["aliases"][bid] = new
        f.write_text(json.dumps(al, indent=1, ensure_ascii=False) + "\n")
        _ALIASES = None


def brief_id(any_id):
    """The one brief id, new spelling, from either spelling.

    `p140` -> `brief-0140`; `brief-0140` -> `brief-0140`; `140` -> `brief-0140`.
    Anything that is not a brief id (`none`, a word) comes back slugged and
    unchanged, so a name with no brief behind it still names that fact."""
    if any_id is None:
        return None
    if isinstance(any_id, int):
        return f"brief-{any_id:04d}"
    t = str(any_id).strip().lower()
    q = BRIEF_KEY.match(t)
    if q:                                   # brand_product_brief-NNNN -> brief-NNNN
        return q.group(3)
    hit = brief_aliases().get("aliases", {}).get(t)
    if hit:
        return hit
    m = BRIEF_OLD.match(t)
    if m:
        return f"brief-{int(m.group(1)):04d}"
    if BRIEF_NEW.match(t):
        return t
    if t.isdigit():
        return f"brief-{int(t):04d}"
    return slug(t)


def brief_code(any_id):
    """The OLD spelling (`p140`) from either — the key briefs.json, the
    worksheets and the live ad names still use. Not a brief id: unchanged."""
    if any_id is None:
        return None
    if BRIEF_KEY.match(str(any_id).strip().lower()):
        # a brief numbered per brand+product has no old code: its key is the
        # whole of it, and `p004` would name a different brief
        return str(any_id).strip().lower()
    new = brief_id(any_id)
    m = BRIEF_NEW.match(new or "")
    return f"p{int(m.group(1)):03d}" if m else new


def brief_forms(any_id):
    """Both spellings of one brief, for a lookup that must hit either."""
    forms = {x for x in (brief_id(any_id), brief_code(any_id)) if x}
    return forms | ({str(any_id).strip().lower()} if any_id else set())


def is_brief_id(s):
    """pNNN, brief-NNNN, or a per-product key brand_product_brief-NNNN."""
    return bool(BRIEF_OLD.match(str(s or "")) or BRIEF_NEW.match(str(s or ""))
                or BRIEF_KEY.match(str(s or "")))


def batch_id(when=None, letter="a"):
    """`batch-YYYY-MM-DD-a` — the new form. `260902a` is the old one and is
    normalised on parse."""
    return f"batch-{(when or dt.date.today()):%Y-%m-%d}-{letter}"


def norm_batch(b):
    """Either batch spelling -> `batch-YYYY-MM-DD-a`. Not a batch: unchanged."""
    if b is None:
        return None
    t = str(b).strip().lower()
    m = BATCH_OLD.match(t)
    if m:
        yy, mm, dd, c = m.groups()
        return f"batch-20{yy}-{mm}-{dd}-{c}"
    return t


def norm_asset(a):
    """Either asset spelling -> `asset-NN`. Not an asset token: unchanged."""
    if a is None:
        return None
    t = str(a).strip().lower()
    m = ASSET_OLD.match(t)
    return f"asset-{int(m.group(1)):02d}" if m else t


def asset_n(a):
    """The asset number out of either spelling, or None."""
    m = ASSET_OLD.match(str(a or "")) or ASSET_NEW.match(str(a or ""))
    return int(m.group(1)) if m else None


def batches_used(day=None, roots=None):
    """Every batch letter already taken on `day`, read off the run roots.

    Recursive: manifests sit beside the assets, and how deep that is
    differs by lane — runs/<x>/finals/ for statics, runs/<x>/ for video.
    A shallow glob missed the delivered batch entirely and handed out a
    letter that was already taken, which is the one thing the convention
    forbids outright.

    The batch is read off the FIELD NAMED `batch` — the manifest's own, and
    each row's name through parse_any — never off position [12]. Both
    spellings count: a batch delivered as `260902a` is `batch-2026-09-02-a`."""
    prefix = batch_id(day or dt.date.today(), "")
    used = set()
    for m in (f for r in (roots or RUNS) if r.is_dir() for f in r.rglob("manifest.json")):
        try:
            man = json.loads(m.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(man, dict):
            continue
        found = [norm_batch(man.get("batch"))]
        for row in man.get("ads", []) or []:
            d = parse_any(row.get("name", "")) if isinstance(row, dict) else None
            if d:
                found.append(d["batch_id"])
        for b in found:
            if b and b.startswith(prefix) and BATCH_NEW.match(b):
                used.add(b[len(prefix):])
    return used


def next_batch(brand):
    """Today's next unused letter, so two runs in one day never collide.
    `batch-YYYY-MM-DD-a`."""
    used = batches_used()
    for c in "abcdefghijklmnopqrstuvwxyz":
        if c not in used:
            return batch_id(letter=c)
    raise SystemExit("26 batches today already — use a new day")


def ad_name(brand, product, media, source, talent, avatar, problem, angle,
            concept, fmt, brief, ratio, batch):
    """The ad unit — this string goes in Meta's Ad name field.

    `media` is static | video | carousel. `source` is ai | ugc | studio |
    mixed. `brief` is the brief that produced it — `p133`, or `none` when
    there is no brief behind it. Kept in the name rather than the manifest
    because a Meta report is often read by someone with no repo access, and
    "which briefs produce winners" is a thing worth ranking. `talent` is who
    is in it — a trained AI identity (`susan`), a real
    creator (`andrea`), or `none` when no person appears. One field answers
    both "which creator earns" and "which identity earns"; `none` keeps the
    column count fixed so nothing downstream shifts. It is the first thing anyone slices
    a report by and it cannot be recovered from any other field, so it is
    named rather than inferred."""
    if slug(media) not in MEDIA:
        raise SystemExit(f"media must be one of {sorted(MEDIA)}, not {media!r}")
    if slug(source) not in SOURCE:
        raise SystemExit(f"source must be one of {sorted(SOURCE)}, not {source!r}")
    # Written in the NEW form, whatever spelling the caller handed over: a
    # brief `p140` becomes `brief-0140`, a batch `260902a` becomes
    # `batch-2026-09-02-a`. Tools read both and write one.
    vals = [slug(x) for x in (brand, product, media, source, talent, avatar,
                              problem, angle, concept, fmt)]
    vals += [brief_id(brief), slug(ratio), norm_batch(slug(batch))]
    for k, v in zip(AD_FIELDS, vals):
        if not v:
            raise SystemExit(f"{k} is empty — every value of an ad name is written")
    return SEP.join(vals)


def asset_name(ad, n):
    """A file inside that ad unit. The ad name plus one value, so dropping
    the last value of any filename gives the unit it was uploaded in.
    `_asset-NN`; the old `-aNN` is accepted on parse."""
    return f"{ad}{SEP}asset-{int(n):02d}"


def _form(stem):
    """Which form a name is in, read off the name itself: the new form joins
    with "_"; an old-form value is [a-z0-9]+ so an old name never carries one.
    (Keying on `brief-` too, as this first did, misread a new-form name with
    no brief behind it — `_none_` — as old.)"""
    return "new" if SEP in stem else "old"


def parse_any(s):
    """Any form -> one dict. 13 values is an ad unit, 14 is an asset. The
    short form (4 or 5 values, see parse_short) is read too. Anything else
    is not ours (None).

    The dict carries every AD_FIELD as written, plus:
        asset      the asset token as written (`a01` | `asset-01`), if any
        ad_name    the unit (the name minus its asset value)
        form       "old" | "new"
        brief_id   the brief, new spelling (`brief-0140`) — join on this
        batch_id   the batch, new spelling (`batch-2026-09-02-a`)
        asset_n    the asset number, or None for a unit
        asset_id   `asset-NN`, or None
        funnel     the funnel id on a short Meta ad name, else None
    Old-form values are squashed (`bodyscrub`) and stay so — nobody can
    un-squash them — so join old and new on the normalised keys, never on
    the raw product/concept words."""
    if not s:
        return None
    stem = Path(str(s)).stem.strip() if "/" in str(s) or "." in str(s) else str(s).strip()
    form = _form(stem)
    sep, ok = (SEP, SLUG) if form == "new" else (OLD_SEP, OLD_SLUG)
    parts = stem.split(sep)
    if form == "new" and len(parts) in (4, 5):
        return parse_short(stem)
    if len(parts) not in (13, 14) or not all(ok.match(p) for p in parts):
        return None
    d = dict(zip(FIELDS, parts))
    if form == "new":
        if not BRIEF_NEW.match(d["brief"]) and d["brief"] != "none":
            return None
        if len(parts) == 14 and not ASSET_NEW.match(d["asset"]):
            return None
    d["funnel"] = None
    d["ad_name"] = sep.join(parts[:13])
    d["form"] = form
    d["brief_id"] = brief_id(d["brief"]) if is_brief_id(d["brief"]) else d["brief"]
    d["batch_id"] = norm_batch(d["batch"])
    d["asset_n"] = asset_n(d.get("asset"))
    d["asset_id"] = norm_asset(d["asset"]) if d.get("asset") else None
    return d



# ---------------------------------------------------------------- short ---
# The short form (the owner, 2026-09-29). The name says only what it takes to
# find the ad and read Ads Manager at a glance; everything else — media,
# source, talent, avatar, problem, angle, concept, format, ratio — is in the
# brief, looked up by its number (`brief_header`).
#
#   folder    brand_product_brief_batch                 the delivery
#   file      brand_product_brief_batch_asset-NN        one cut / picture
#   meta ad   brand_product_brief_batch_funnel          one ad per batch
#
# The file carries no funnel (one file can launch to several pages); the
# Meta ad carries no asset (a batch's variations run as one ad).
SHORT_FIELDS = ["brand", "product", "brief", "batch"]


def short_unit(brand, product, brief, batch):
    vals = [slug(brand), slug(product), brief_id(brief), norm_batch(batch)]
    name = SEP.join(vals)
    if not parse_short(name):
        raise ValueError(f"not a clean short name: {name}")
    return name


def short_file(unit, n):
    return f"{unit}{SEP}asset-{int(n):02d}"


def short_meta(unit, funnel):
    d = parse_short(unit)
    if not d or d.get("asset") or d.get("funnel"):
        raise ValueError(f"not a short unit name: {unit}")
    if not SLUG.match(str(funnel or "")):
        raise ValueError(f"not a funnel id: {funnel!r}")
    return f"{unit}{SEP}{funnel}"


def parse_short(s):
    """brand_product_brief_batch[_asset-NN | _funnel] -> dict, or None."""
    stem = Path(str(s)).stem if "." in str(s) else str(s)
    parts = stem.split(SEP)
    if len(parts) not in (4, 5) or not all(SLUG.match(p) for p in parts):
        return None
    brand, product, brief, batch = parts[:4]
    if not (BRIEF_NEW.match(brief) or brief == "none") or not BATCH_NEW.match(batch):
        return None
    d = {"form": "short", "brand": brand, "product": product, "brief": brief,
         "batch": batch, "asset": None, "funnel": None,
         "ad_name": SEP.join(parts[:4]), "brief_id": brief, "batch_id": batch}
    if len(parts) == 5:
        if ASSET_NEW.match(parts[4]):
            d["asset"] = d["asset_id"] = parts[4]
        else:
            d["funnel"] = parts[4]
    return d


# ------------------------------------------------- per brand + product ---
# the owner, 2026-10-01: "brief numbers count per brand AND product — each product
# starts at 1 inside its brand." Older briefs keep the numbers they have (one
# shared count until that day), so one brand can hold an old brief-0001 and a
# newer product's brief-0001. A brief is brand + product + number; the short name
# brand_product_brief-NNNN carries all three. Where only brand + number is
# known and two briefs share it, nothing here guesses — it says so.
PER_PRODUCT = "brand+product"      # a brand-file record numbered under the new rule: "count": PER_PRODUCT


class AmbiguousBrief(ValueError):
    """brand + number names more than one brief — the product decides."""


def brief_number(any_id):
    """The number in any spelling (p004, brief-0004, acme_serum_brief-0004), or None."""
    t = str(any_id or "").strip().lower()
    q = BRIEF_KEY.match(t)
    if q:
        return int(q.group(4))
    m = BRIEF_OLD.match(t) or BRIEF_NEW.match(t)
    return int(m.group(1)) if m else None


def brief_key(brand, product, brief):
    """`<brand>_<product>_brief-NNNN` — how the register keys a brief numbered
    per brand+product. No product is written `none`, never left blank."""
    return SEP.join([slug(brand), slug(product) if product else "none", brief_id(brief)])


def parse_brief_key(k):
    """(brand, product, brief-NNNN) or None."""
    q = BRIEF_KEY.match(str(k or "").strip().lower())
    return (q.group(1), q.group(2), q.group(3)) if q else None


def _prod(p):
    return slug(p) if p and slug(p) != "none" else None


def next_brief_number(rows, brand, product):
    """1 + the highest number any brief of this brand AND product already uses.

    `rows` is every brief record that might count — dicts carrying brand,
    product and a number under `brief`/`id`/`key`. Old records count where
    their product is known; a brand's old briefs with no product only count
    toward the brand's product-less briefs. Nothing is reissued: retired
    records are rows too."""
    want = _prod(product)
    top = 0
    for r in rows:
        if not isinstance(r, dict) or slug(r.get("brand") or "") != slug(brand):
            continue
        if _prod(r.get("product")) != want:
            continue
        n = next((x for x in (brief_number(r.get(f)) for f in ("brief", "key", "id")) if x), None)
        top = max(top, n or 0)
    return top + 1


def brand_alias(brand, alias):
    """A brand's own code for a brief (`acm01`) -> (product, brief-NNNN), or
    None. These live per brand in brief-aliases.json `brand_aliases`, not in
    the global map: a brand's code for its newer product's brief-0001 cannot sit there,
    where brief-0001 also means the old p001."""
    hit = (brief_aliases().get("brand_aliases", {}).get(slug(brand)) or {}).get(str(alias or "").strip().lower())
    return (hit.get("product"), hit.get("brief")) if hit else None


def brand_briefs(brand):
    """brands/<brand>/briefs/briefs.json `briefs`, or []."""
    f = BP.brand_path(slug(brand), "briefs", "briefs.json", root=WS / "brands")
    try:
        return json.loads(f.read_text()).get("briefs", []) if f.is_file() else []
    except (OSError, json.JSONDecodeError):
        return []


def register_file():
    """The brief register every lane's `briefs.py open` writes to."""
    return next((f for f in (WS / "tools" / "image-teardown" / "briefs.json",
                             WS / "components" / "image-teardown" / "briefs.json") if f.is_file()),
                WS / "tools" / "image-teardown" / "briefs.json")


def register_rows(brand=None, reg=None):
    """Register records (briefs + retired) as rows with their key, optionally one brand's."""
    if reg is None:
        try:
            reg = json.loads(register_file().read_text())
        except (OSError, json.JSONDecodeError):
            reg = {}
    rows = []
    for table in ("briefs", "retired"):
        for k, r in dict.items(reg.get(table) or {}):
            if isinstance(r, dict) and (brand is None or slug(r.get("brand") or "") == slug(brand)):
                rows.append({**r, "key": k, "_table": table})
    return rows


def brief_candidates(brand, brief_or_alias, product=None, reg=None):
    """Every distinct brief this brand could mean by `brief_or_alias`.

    Each is a dict: brief, product, per_product (numbered under the 1 Oct
    rule), header (the brands/<brand>/briefs/briefs.json record, if any) and
    register (the register record, if any). An old register record and the
    brand-file record for the same old number are ONE brief. With `product`,
    only briefs of that product are kept — or, if none, the old shared-count
    brief with that number."""
    key = str(brief_or_alias or "").strip()
    low = key.lower()
    want_prod = _prod(product)
    ba = brand_alias(brand, low)
    if ba:
        want_prod = want_prod or _prod(ba[0])
        low = ba[1]
    q = parse_brief_key(low)
    if q:
        want_prod, low = want_prod or _prod(q[1]), q[2]
    num = brief_number(low)
    out = []
    for b in brand_briefs(brand):
        aliases = [str(a).lower() for a in b.get("aliases") or []]
        if b.get("brief") == key or (num and brief_number(b.get("brief")) == num) or low in aliases:
            out.append({"brief": b.get("brief"), "product": _prod(b.get("product")),
                        "per_product": b.get("count") == PER_PRODUCT, "header": b, "register": None})
    if num:
        for r in register_rows(brand, reg):
            if r["_table"] != "briefs" or brief_number(r.get("brief") or r["key"]) != num:
                continue
            per = bool(parse_brief_key(r["key"]))
            same = next((c for c in out if c["register"] is None and c["per_product"] == per
                         and (per is False or c["product"] == _prod(r.get("product")))), None)
            if same:
                same["register"] = r
                if same["product"] is None:
                    same["product"] = _prod(r.get("product"))
            else:
                out.append({"brief": brief_id(num), "product": _prod(r.get("product")),
                            "per_product": per, "header": None, "register": r})
    if want_prod:
        exact = [c for c in out if c["product"] == want_prod]
        # no brief of that product: an OLD brief still answers (its number was
        # unique across the old shared count), a newer product's never does
        out = exact or [c for c in out if not c["per_product"]]
    return out


def find_brief(brand, brief_or_alias, product=None, reg=None):
    """The one brief brand (+ product) + number names, or None. Refuses —
    AmbiguousBrief — rather than guess when two briefs share the number and
    no product says which."""
    c = brief_candidates(brand, brief_or_alias, product, reg)
    if len(c) > 1:
        raise AmbiguousBrief(
            f"{brief_id(brief_or_alias) if brief_number(brief_or_alias) else brief_or_alias} is used by more "
            f"than one {str(brand).upper()} product ({', '.join(sorted(x['product'] or 'no product' for x in c))})"
            f" — say which")
    return c[0] if c else None


def brief_header(brand, brief_or_alias, product=None):
    """A brief's naming header from brands/<brand>/briefs/briefs.json.

    `product` picks between briefs that share a number (the owner, 2026-10-01:
    numbers count per brand and product). Callers that read the product off
    a short name pass it. Without one, a number two products share raises
    AmbiguousBrief instead of handing back the wrong brief's header."""
    if not BP.brand_path(slug(brand), "briefs", "briefs.json", root=WS / "brands").is_file():
        return None
    hit = find_brief(brand, brief_or_alias, product)
    return hit["header"] if hit else None

def parse(s):
    """Kept for every caller that learned this name. Reads both forms."""
    return parse_any(s)


def to_new(s):
    """An old-form name in the new joint, values as they are (squashed words
    stay squashed; brief, batch and asset take their new spelling). For
    showing old and new side by side — NOT for renaming live ads
    (decision 9)."""
    d = parse_any(s)
    if not d:
        return None
    vals = [d[k] for k in AD_FIELDS[:10]] + [d["brief_id"], d["ratio"], d["batch_id"]]
    if d.get("asset"):
        vals.append(d["asset_id"])
    return SEP.join(vals)


def rename_to(src, dst):
    """Rename, and never onto a file that already exists.

    Measured cause, 2026-09-02: a rename pass ran twice over the same folder,
    the second pass shifted every index by one, and one finished ad was
    overwritten and lost. The manifest still listed six. A name collision is
    silent and it destroys work — refuse it."""
    src, dst = Path(src), Path(dst)
    if src.resolve() == dst.resolve():
        return dst
    if dst.exists():
        raise SystemExit(f"refusing to rename {src.name} onto existing "
                         f"{dst.name} — a name is never reused")
    src.rename(dst)
    return dst


def audit(manifest):
    """Every row in the manifest must have its file. A manifest that claims
    an ad nobody can open is worse than no manifest.

    Files are resolved beside the manifest, never against the working
    directory. A manifest that only validates from the folder someone
    happened to run the command in is not a record — and these folders get
    mirrored to Drive, where that directory does not exist."""
    m = Path(manifest)
    d = json.loads(m.read_text())
    # Rows without a file are pre-convention (retired batches) — not ours to audit.
    return [r["name"] for r in d.get("ads", []) if r.get("file")
            if not (m.parent / Path(r["file"]).name).is_file()]


def write_manifest(out_dir, brand, avatar, fmt, concept, batch, rows):
    """One row per ad, keyed by the ad name. This is the half of the record
    the name deliberately does not carry — the headline verbatim, the offer,
    the plate, the model, the swipe it came from."""
    man = {
        "batch": batch,
        "brand": brand, "avatar": avatar, "format": fmt, "concept": concept,
        "built": dt.datetime.now().isoformat(timespec="seconds"),
        "_join": "Meta's ad_name equals `name` below. Read it with "
                 "names.parse_any — both forms parse to one dict.",
        "ads": rows,
    }
    p = Path(out_dir) / "manifest.json"
    p.write_text(json.dumps(man, indent=1) + "\n")
    return p


def main():
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("next-batch"); n.add_argument("brand")
    c = sub.add_parser("check"); c.add_argument("names", nargs="+")
    p = sub.add_parser("parse"); p.add_argument("name")
    b = sub.add_parser("brief-id"); b.add_argument("id")
    o = a.parse_args()

    if o.cmd == "next-batch":
        print(next_batch(o.brand))
    elif o.cmd == "brief-id":
        print(brief_id(o.id))
    elif o.cmd == "parse":
        d = parse_any(o.name)
        if not d:
            sys.exit(f"{o.name!r} does not parse into 13 or 14 values")
        for k, v in d.items():
            print(f"  {k:9} {v}")
        if d["form"] == "old":
            print(f"  {'as new':9} {to_new(o.name)}")
    else:
        bad = [x for x in o.names if not parse_any(x)]
        for x in bad:
            print(f"  BAD  {x}")
        print(f"{len(o.names) - len(bad)}/{len(o.names)} parse")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
