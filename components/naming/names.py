#!/usr/bin/env python3
"""Ad names and batch manifests — the join key back to Meta spend.

    names.py next-batch <brand>            the next free batch id for today
    names.py check <name> [name...]        does this parse into six fields
    names.py parse <name>                  show its fields

See CONVENTION.md. The name carries what you group by; the manifest carries
everything else and is joined to Meta's report on the name itself.
"""
import argparse, datetime as dt, json, re, sys
from pathlib import Path

def _workspace_root(start=None):
    """Walk up to the workspace, rather than counting folders.

    This used to be parents[3], which was the root only while this file sat
    three deep in lab/. It graduated to components/naming/ on 2026-09-11 and
    every brand lookup silently pointed at the wrong place. A marker cannot
    go quietly wrong the next time something moves.
    """
    p = (start or Path(__file__)).resolve()
    for d in p.parents:
        if (d / "brands").is_dir() and (d / "CLAUDE.md").is_file():
            return d
    raise RuntimeError("not inside the ai-workspace")


WS  = _workspace_root()
LAB = WS / "lab" / "damon"      # a person's runs and swipes stay in lab
# Both lanes name assets the same way, so the runs of both are scanned when
# picking the next free batch letter for a day.
RUNS = [LAB / "image-production/runs",
        LAB / "ai-video-production/runs",
        WS / "runs" / "video-machine"]
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
SLUG = re.compile(r"^[a-z0-9]+$")

# ---------------------------------------------------------------- shared ---
# The fields that describe A CREATIVE, whoever made it. A competitor's ad and
# one of ours are the same kind of object: something with a form, a maker, a
# person in it, a problem it speaks to, an angle on that problem, an execution
# of the angle, a template and a frame. Everything else in AD_FIELDS is ours
# alone — our brand, our product, our avatar, our brief, our batch.
#
# The My Feeds library describes its ads in exactly these words, so a Meta export
# grouped on `problem` or `source` and the swipe corpus grouped on the same
# field are answering one question, not two. Two vocabularies for one idea is
# how you end up unable to say whether the thing that won was the thing you
# swiped.
CREATIVE_FIELDS = ["media", "source", "talent", "problem", "angle", "concept",
                   "format", "ratio"]
# A field a human has not judged yet. Written, never blank: a blank reads as
# "no person in it" (which is `none`) and quietly becomes an answer.
UNCLASSIFIED = "unclassified"
SWIPE_REF = re.compile(r"^swipe:([a-z0-9]+):(\d+)$")


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


def parse_swipe_id(ref):
    """(brand, ad_id) or None."""
    m = SWIPE_REF.match((ref or "").strip())
    return (m.group(1), int(m.group(2))) if m else None


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
    """One field's worth of characters. A hyphen inside a field would add a
    seventh column to every downstream split, so it is stripped here rather
    than found later in a report that silently mis-columns."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


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
    receipt, no entry; only Damon signs an angle active". A naming scheme
    that let anyone type a new angle into a filename would quietly create a
    second, unsigned vocabulary — and the reports would then be grouped on
    words nobody ruled."""
    f = (WS / "brands" / slug(brand)
         / "strategy/angles.json")
    if not f.is_file():
        return None
    try:
        return {slug(a.get("id") or a.get("name")): a
                for a in json.loads(f.read_text()).get("angles", [])
                if a.get("status") == "active"}
    except (json.JSONDecodeError, OSError):
        return None


def check_angle(brand, angle):
    """Warn, never block. An unsigned angle is a strategy gap to close, not
    a reason to stop a batch from shipping."""
    known = signed_angles(brand)
    if known is None:
        return f"no angle source for {brand} — angle '{angle}' is unverified"
    if not known:
        return (f"{brand} has no signed angles yet (strategy/angles.json is "
                f"empty by design — only Damon signs one active), so "
                f"'{angle}' is unverified")
    if slug(angle) not in known and slug(angle) != "unsigned":
        return (f"'{angle}' is not a signed angle for {brand}. Signed: "
                + ", ".join(sorted(known)))
    return None


def batch_id(when=None, letter="a"):
    return f"{(when or dt.date.today()):%y%m%d}{letter}"


def next_batch(brand):
    """Today's next unused letter, so two runs in one day never collide."""
    today = f"{dt.date.today():%y%m%d}"
    used = set()
    # Recursive: manifests sit beside the assets, and how deep that is
    # differs by lane — runs/<x>/finals/ for statics, runs/<x>/ for video.
    # A shallow glob missed the delivered batch entirely and handed out a
    # letter that was already taken, which is the one thing the convention
    # forbids outright.
    for m in (f for r in RUNS if r.is_dir() for f in r.rglob("manifest.json")):
        try:
            for row in json.loads(m.read_text()).get("ads", []):
                parts = row.get("name", "").split("-")
                if len(parts) < 13:
                    continue              # a pre-convention row — not a batch
                b = parts[12]
                if b.startswith(today):
                    used.add(b[len(today):])
        except (json.JSONDecodeError, OSError):
            continue
    for c in "abcdefghijklmnopqrstuvwxyz":
        if c not in used:
            return today + c
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
    return "-".join(slug(x) for x in
                    (brand, product, media, source, talent, avatar, problem,
                     angle, concept, fmt, brief, ratio, batch))


def asset_name(ad, n):
    """A file inside that ad unit. The ad name plus one field, so dropping
    the last field of any filename gives the unit it was uploaded in."""
    return f"{ad}-a{int(n):02d}"


def parse(s):
    """Six fields is an ad unit, seven is an asset. Anything else is not ours."""
    parts = Path(s).stem.strip().split("-")
    if len(parts) not in (13, 14) or not all(SLUG.match(p) for p in parts):
        return None
    d = dict(zip(FIELDS, parts))
    d["ad_name"] = "-".join(parts[:13])
    return d


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
        "_join": "Meta's ad_name equals `name` below. Split it on '-' for "
                 "brand, avatar, format, concept, asset, batch.",
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
    o = a.parse_args()

    if o.cmd == "next-batch":
        print(next_batch(o.brand))
    elif o.cmd == "parse":
        d = parse(o.name)
        if not d:
            sys.exit(f"{o.name!r} does not parse into six fields")
        for k, v in d.items():
            print(f"  {k:9} {v}")
    else:
        bad = [x for x in o.names if not parse(x)]
        for x in bad:
            print(f"  BAD  {x}")
        print(f"{len(o.names) - len(bad)}/{len(o.names)} parse")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
