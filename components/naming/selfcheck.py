#!/usr/bin/env python3
"""Does the standard actually hold? Run before trusting a report.

    selfcheck.py

Every claim the convention makes, exercised against the real code and the
real delivered batches. A naming standard that is only a document drifts the
first time a field is added — this is what catches that.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import names as N

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
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [ ok ] {label}")
    else:
        fail += 1
        print(f"  [FAIL] {label}  {detail}")


print("\nThe name")
ad = N.ad_name("<brand>", "bodyscrub", "static", "ai", "none", "spothider",
               "darkspots", "pigmentmemory", "handsapplication",
               "photostrip", "p140", "9x16", "260902a")
check("an ad name has one field per position",
      len(ad.split("-")) == len(N.AD_FIELDS),
      f"{len(ad.split('-'))} vs {len(N.AD_FIELDS)}")
asset = N.asset_name(ad, 1)
check("an asset name is the ad name plus one field",
      asset.startswith(ad + "-") and
      len(asset.split("-")) == len(N.AD_FIELDS) + 1)
check("an asset parses back to its ad unit",
      (N.parse(asset) or {}).get("ad_name") == ad)
check("a filename parses the same as a bare name",
      N.parse(asset + ".png") == N.parse(asset))
check("hyphens inside a value are stripped, not passed through",
      "-" not in N.slug("spot-hider"))
def refused(f):
    """A bad value must stop the run, not quietly create a new category."""
    try:
        f()
        return False
    except SystemExit:
        return True


check("a wrong media value is refused",
      refused(lambda: N.ad_name("b", "p", "photo", "ai", "none", "a", "pr",
                                "an", "c", "f", "br", "9x16", "260101a")))
check("a wrong source value is refused",
      refused(lambda: N.ad_name("b", "p", "static", "robot", "none", "a", "pr",
                                "an", "c", "f", "br", "9x16", "260101a")))
check("a rename onto an existing name is refused",
      refused(lambda: N.rename_to(__file__, __file__.replace(
          "selfcheck.py", "names.py"))))


print("\nThe angle vocabulary")
signed = N.signed_angles("<brand>")
check("the brand's angle source is readable", signed is not None)
check("an unsigned angle is flagged",
      N.check_angle("<brand>", "somethingmadeup") is not None)
check("a signed angle passes",
      N.check_angle("<brand>", "pigmentmemory") is None,
      f"signed: {list(signed or [])}")

print("\nDelivered batches")
# Recursive, and per lane. Manifests sit beside the assets, and how deep
# that is differs by lane and by run — a shallow glob silently checked one
# batch and reported all-clear.
mans = sorted(set(LAB.glob("image-production/runs/**/manifest.json")) |
              set(LAB.glob("ai-video-production/runs/**/manifest.json")) |
              set((WS / "runs" / "video-machine").glob("**/manifest.json")))
check("at least one delivered batch exists", bool(mans))
for m in mans:
    d = json.loads(m.read_text())
    run = m.parent.parent.name
    # Retired batches from before the convention keep their old manifests;
    # rows without a name are not ours to check.
    names = [r["name"] for r in d.get("ads", []) if "name" in r]
    check(f"{run}: every asset name parses",
          all(N.parse(n) for n in names), f"{names[:1]}")
    check(f"{run}: every asset belongs to the declared ad unit",
          all((N.parse(n) or {}).get("ad_name") == d["ad_name"] for n in names))
    check(f"{run}: every file the manifest claims exists",
          not N.audit(m), str(N.audit(m))[:80])
    on_disk = {p.stem for p in m.parent.glob("*.png")}
    check(f"{run}: no unnamed asset in the folder",
          all(N.parse(x) for x in on_disk),
          str(sorted(x for x in on_disk if not N.parse(x))[:2]))

# ------------------------------------------------------- the swipe join ---
# One vocabulary, or the join is fiction. The swipe corpus describes a
# competitor's ad in these same words so that a Meta export and the swipe
# library group on the same columns; if the two ever drift, a report that
# looks joined is silently comparing two different questions.
print("\nThe swipe join")
SWIPE = LAB / "swipe-paid"
check("the shared creative vocabulary is declared",
      N.CREATIVE_FIELDS == ["media", "source", "talent", "problem", "angle",
                            "concept", "format", "ratio"],
      str(N.CREATIVE_FIELDS))
check("every shared field is also a field of an ad name",
      all(f in N.AD_FIELDS for f in N.CREATIVE_FIELDS),
      str([f for f in N.CREATIVE_FIELDS if f not in N.AD_FIELDS]))
check("a swipe reference round-trips",
      N.parse_swipe_id(N.swipe_id("resilia", 162098799)) == ("resilia", 162098799))
check("a swipe reference refuses anything else",
      N.parse_swipe_id("resilia-162098799") is None)

# The My Feeds library calls a copy block a BLOCK, not an angle: an angle is
# the signed read on a problem and lives on the creative, not on the file.
block_files = sorted(SWIPE.glob("*/blocks.json")) if SWIPE.is_dir() else []
check("the My Feeds library has brands in it", bool(block_files))
for f in block_files:
    brand = f.parent.name
    doc = json.loads(f.read_text())
    ads = [m for a in doc.get("blocks", []) for m in a.get("media", {}).values()]
    described = [m for m in ads if m.get("fields")]
    if not described:
        check(f"{brand}: creatives are described", False,
              "run swipe_fields.py apply")
        continue
    check(f"{brand}: every described creative has every shared field",
          all(set(m["fields"]) == set(N.CREATIVE_FIELDS) for m in described),
          f"{len(described)} of {len(ads)} described")
    check(f"{brand}: no field is blank — unjudged is written, not omitted",
          all(v not in ("", None) for m in described for v in m["fields"].values()))
    check(f"{brand}: every creative carries a swipe reference",
          all(N.parse_swipe_id(m.get("swipe_id") or "") for m in described))
    vocab = (doc.get("vocabulary") or {}).get("creative_fields")
    check(f"{brand}: its vocabulary matches the namer's",
          vocab == N.CREATIVE_FIELDS, str(vocab))


# ── the format registry ──────────────────────────────────────────────────
# A bank that has moved should fail HERE, not silently render a blank page
# three days later (which is exactly what the organic library did).
print("\nThe format registry")
REG = json.loads((Path(__file__).resolve().parent / "registry.json").read_text())

# Brands are DISCOVERED, never named. A literal here would be the same bug the
# registry exists to prevent, one level up (workspace rule 7).
BRAND_DIRS = sorted(d.name for d in (WS / "brands").iterdir()
                    if d.is_dir() and not d.name.startswith("_"))
check("at least one brand is on disk to test against", bool(BRAND_DIRS),
      ", ".join(BRAND_DIRS))
SAMPLE = BRAND_DIRS[0] if BRAND_DIRS else None

for row in REG["banks"]:
    ref = N.format_ref(row["asset"], row["id"], brand=SAMPLE if row["brand"] else None)
    got = N.resolve_format(ref)
    check(f"{ref} resolves", got is not None and got["path"] == row["path"], ref)

for row in REG["banks"]:
    # a per-brand bank must resolve for EVERY brand, not just the one that
    # happened to be built first — this is what breaks on the second brand
    for b in (BRAND_DIRS if row["brand"] else [None]):
        p = row["path"].replace("<brand>", b) if b else row["path"]
        if "/" not in p or p.split("/")[0] not in {d.name for d in WS.iterdir() if d.is_dir()}:
            continue                      # lives outside the workspace; checked elsewhere
        where = "" if not b else f" for {b}"
        exists = (WS / p.split()[0] if " " in p else WS / p).exists()
        known = (row.get("brands_missing") or {}).get(b)
        if known and not exists:
            # a recorded gap stays visible without turning the board red forever
            print(f"  [GAP ] {row['asset']}:{row['id']} absent for {b} — {known[:70]}")
            continue
        check(f"{row['asset']}:{row['id']} — its file is still there{where}", exists, p)

for row in REG["banks"]:
    if not row["brand"]:
        continue
    bare = f"format:{row['asset']}:{row['id']}"
    try:
        N.resolve_format(bare)
        refused = False
    except ValueError:
        refused = True
    check(f"{bare} is refused — a per-brand bank needs its brand", refused, bare)

ev_paths = {e["path"] for e in REG["evidence"]}
for row in REG["banks"]:
    check(f"{row['asset']}:{row['id']} is not also filed as evidence",
          row["path"] not in ev_paths, row["path"])

# Rule 7 enforced, not just stated: a brand name may appear as DATA about a
# brand (a recorded gap, a recorded conflict) but never in a path, an id or an
# asset token, and never in this component's code. Without a check, "brand-
# agnostic by design" is a sentence in a file rather than a property of it.
import re as _rx
_BRAND_RE = _rx.compile("|".join(BRAND_DIRS), _rx.I) if BRAND_DIRS else None
if _BRAND_RE:
    for row in REG["banks"]:
        for field in ("asset", "id", "path"):
            check(f"{row['asset']}:{row['id']} — no brand name in its {field}",
                  not _BRAND_RE.search(str(row.get(field, ""))), str(row.get(field)))
    for src in sorted((Path(__file__).resolve().parent).glob("*.py")):
        hits = [ln for ln in src.read_text().splitlines()
                if _BRAND_RE.search(ln) and "brands_missing" not in ln
                and "location_conflict" not in ln]
        # selfcheck's own fixtures name a brand on purpose — they exercise real data
        allowed = src.name == "selfcheck.py"
        check(f"{src.name} carries no brand literal",
              not hits or allowed, f"{len(hits)} line(s): {hits[0][:60] if hits else ''}")

# ── the four-axis model ──────────────────────────────────────────────────
# Ruled 2026-09-11. An angle is a CLAIM: channel-free, format-free, aimed at
# one core avatar. Stating that in a document is not enough — the <brand> bank
# had nine entries breaking it, seven of them signed.
print("\nThe four-axis model")
_CONTAINER = _rx.compile(
    r"\b(slideshow|carousel|reel|static|podium|grid|accordion|slide \d|"
    r"per slide|tiktok|meta ad|thumbnail|overlay|caption)\b", _rx.I)

for b in BRAND_DIRS:
    ab = WS / "brands" / b / "strategy" / "angles.json"
    check(f"{b}: has an angle bank", ab.is_file(), str(ab))
    if not ab.is_file():
        continue
    bank = json.loads(ab.read_text())
    for field in ("scope", "brand", "source", "updated", "note"):
        check(f"{b}: the angle bank declares `{field}`", field in bank, field)
    check(f"{b}: its scope says an angle is channel-free and format-free",
          "CHANNEL-FREE" in str(bank.get("scope", "")))

    cores = {d.name for d in (WS / "brands" / b / "core-avatars").glob("*")
             if d.is_dir() and (d / "profile.md").is_file()}
    for a in bank.get("angles", []):
        i = a.get("id", "?")
        for field in ("id", "name", "what", "status", "signed"):
            check(f"{b}/{i}: carries `{field}`", field in a, field)
        # an angle is aimed at exactly one core avatar that actually exists
        check(f"{b}/{i}: its avatar is a real core avatar",
              a.get("avatar") in cores or bool(a.get("misfiled")),
              f"{a.get('avatar')} not in {sorted(cores)}")
        # a claim that names a container is a format wearing an angle's clothes
        words = " ".join(str(a.get(k, "")) for k in ("id", "name", "what"))
        hit = _CONTAINER.search(words)
        check(f"{b}/{i}: names no container — a claim is format-free",
              not hit or bool(a.get("misfiled")),
              f"says '{hit.group(0)}'" if hit else "")
        # only a human signs
        sg = a.get("signed")
        check(f"{b}/{i}: if signed, a person signed it",
              sg is None or (isinstance(sg, dict) and sg.get("by")), str(sg)[:40])

# What a new brand inherits. _TEMPLATE had none of this, which is why two
# brands drifted into different shapes and neither noticed.
_T = WS / "brands" / "_TEMPLATE"
for rel, why in [("strategy/angles.json", "the angle axis"),
                 ("core-avatars/README.md", "the avatar axis"),
                 ("offers/offers.json",     "the offer bank"),
                 ("variables/copy.md",      "the brand map every machine reads")]:
    check(f"a new brand inherits {why}", (_T / rel).is_file(), rel)

# the shells must teach the rule, not just exist
import json as _js
_ta = _js.loads((_T / "strategy/angles.json").read_text())
check("the template's angle bank states the channel-free rule",
      "CHANNEL-FREE" in str(_ta.get("scope", "")))
check("the template's angle bank ships nothing signed",
      all(a.get("signed") is None for a in _ta.get("angles", [])))

check("every evidence entry stays unaddressable",
      all(N.parse_format_ref(e.get("address", "")) is None for e in REG["evidence"]))

print(f"\n{ok} ok · {fail} failing\n")
sys.exit(1 if fail else 0)


# ---------------------------------------------------------------- subs ---
# Every sub-avatar a brand declares — on a roster man, in lineage.json —
# must resolve to a card whose frontmatter `id` is that same bare slug. A
# sub that resolves nowhere is a record that will never join to a card;
# a card whose id disagrees with its filename is two names for one man.
import re as _re
BRANDS = WS / "brands"
for brand_dir in sorted(p for p in BRANDS.iterdir() if (p / "core-avatars").is_dir()):
    cards = {}
    for card in (brand_dir / "core-avatars").glob("*/sub-avatars/sub-*.md"):
        m = _re.search(r"^id:\s*(\S+)", card.read_text(), _re.M)
        cards[m.group(1) if m else None] = card
        check(f"{brand_dir.name}: {card.name} carries an id equal to its bare slug",
              m is not None and m.group(1) == N.sub_key(card.name), card.name)
    declared = set()
    roster = brand_dir / "core-avatars/casting/roster.json"
    if roster.is_file():
        for p in json.loads(roster.read_text()).get("people", []):
            for s in [p.get("sub")] + list(p.get("also_plays", [])):
                if s: declared.add(s)
    lineage = brand_dir / "core-avatars/casting/lineage.json"
    cores = {p.parent.name for p in (brand_dir / "core-avatars").glob("*/profile.md")}
    if lineage.is_file():
        declared |= set(json.loads(lineage.read_text()).get("subs", {}))
    for s in sorted(declared):
        check(f"{brand_dir.name}: declared sub `{s}` resolves to a card or a core",
              N.sub_key(s) in cards or s in cores, s)
