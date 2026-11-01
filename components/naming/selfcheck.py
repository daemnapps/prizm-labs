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
sys.path.append(str(N.WS / "components" / "brandpath"))   # appended, never ahead of this tool
import brandpath as BP                                   # noqa: E402  brand folders by plan name

WS  = N.WS                      # names.py's locator: run-kit paths.repo()
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
OLD = ("brand-b-bodyscrub-static-ai-none-spothider-darkspots-pigmentmemory-"
       "handsapplication-photostrip-p140-9x16-260902a")
NEW = ("brand_b_brilliance-body-scrub_static_ai_none_spot-hider_dark-spots_"
       "pigment-memory_hands-application_photo-strip_brief-0140_9x16_"
       "batch-2026-09-02-a")
ad = N.ad_name("brand-b", "brilliance-body-scrub", "static", "ai", "none",
               "spot-hider", "dark-spots", "pigment-memory", "hands-application",
               "photo-strip", "p140", "9x16", "260902a")
check("an ad name is written in the NEW form, values joined by '_'",
      ad == NEW, ad)
check("an ad name has one value per position",
      len(ad.split("_")) == len(N.AD_FIELDS),
      f"{len(ad.split('_'))} vs {len(N.AD_FIELDS)}")
asset = N.asset_name(ad, 1)
check("an asset name is the ad name plus one value, `_asset-NN`",
      asset == NEW + "_asset-01", asset)
check("an asset parses back to its ad unit",
      (N.parse_any(asset) or {}).get("ad_name") == ad)
check("a filename parses the same as a bare name",
      N.parse_any(asset + ".png") == N.parse_any(asset))
check("parse() still answers — every caller that learned it keeps working",
      N.parse(asset) == N.parse_any(asset))
check("hyphens inside a value SURVIVE — '-' joins words, '_' joins values",
      N.slug("spot-hider") == "spot-hider" and N.slug("Spot Hider") == "spot-hider")
check("a value never starts or ends with a hyphen",
      N.slug("-spot--hider_") == "spot-hider")

# the old form: the live account still speaks it (decision 9)
o = N.parse_any(OLD + "-a01")
check("the old 14-value form parses", o is not None)
check("the old form reads as `old` with the same field names",
      o and o["form"] == "old" and o["brief"] == "p140" and o["batch"] == "260902a"
      and o["asset"] == "a01" and o["ad_name"] == OLD)
check("the old form's brief, batch and asset are normalised alongside",
      o and o["brief_id"] == "brief-0140" and o["batch_id"] == "batch-2026-09-02-a"
      and o["asset_n"] == 1 and o["asset_id"] == "asset-01")
check("the old 13-value form parses as a unit (no asset)",
      (N.parse_any(OLD) or {}).get("asset_n") is None
      and (N.parse_any(OLD) or {}).get("ad_name") == OLD)
n = N.parse_any(NEW + "_asset-01")
check("the new 14-value form parses", n is not None)
check("the new form reads as `new` and keeps its hyphenated values",
      n and n["form"] == "new" and n["product"] == "brilliance-body-scrub"
      and n["brief"] == "brief-0140" and n["asset_n"] == 1)
check("old and new agree on every normalised key",
      o and n and all(o[k] == n[k] for k in ("brand", "media", "source", "talent",
                                             "ratio", "brief_id", "batch_id",
                                             "asset_n", "asset_id")))
check("the fields of one dict are the fields of the other",
      o and n and set(o) == set(n))
check("round trip: parse -> ad_name -> parse gives the same name",
      N.ad_name(*[n[k] for k in N.AD_FIELDS]) == NEW
      and N.asset_name(N.ad_name(*[n[k] for k in N.AD_FIELDS]), n["asset_n"]) == NEW + "_asset-01")
check("an old name shown in the new joint keeps its squashed words",
      N.to_new(OLD + "-a01") == OLD.replace("-", "_").replace("p140", "brief-0140")
      .replace("260902a", "batch-2026-09-02-a") + "_asset-01", N.to_new(OLD + "-a01"))
check("twelve values is nobody's name", N.parse_any("a-b-c-d-e-f-g-h-i-j-k-l") is None)
check("a new-form name with a bad brief value is refused",
      N.parse_any(NEW.replace("brief-0140", "brief-14") + "_asset-01") is None)

print("\nThe brief id")
check("p140 -> brief-0140", N.brief_id("p140") == "brief-0140")
check("brief-0140 -> brief-0140", N.brief_id("brief-0140") == "brief-0140")
check("140 -> brief-0140", N.brief_id(140) == "brief-0140")
check("brief-0140 -> p140 (the key briefs.json still uses)", N.brief_code("brief-0140") == "p140")
check("`none` is not a brief and stays `none`", N.brief_id("none") == "none")
check("both spellings come back for a lookup",
      N.brief_forms("p140") == {"p140", "brief-0140"})
AL = N.brief_aliases()
check("the alias file covers p001-p190", all(f"p{i:03d}" in AL["aliases"] for i in range(1, 191))
      and len(AL["aliases"]) >= 190)      # the register keeps issuing numbers past p190
check("the alias file agrees with the arithmetic",
      all(v == N.brief_id(k) for k, v in AL["aliases"].items()))
check("the three never-used numbers are named",
      set(AL["never_used"]) == {"p128", "p130", "p134"})

print("\nBrief numbers per brand and product (the owner, 2026-10-01)")
_rows = N.register_rows() + [{**b, "brand": br} for br in ("brand-a", "brand-b") for b in N.brand_briefs(br)]
check("BRAND-A CRUSH counts on from its own 0003", N.next_brief_number(_rows, "brand-a", "crush") == 4)
check("a product with no brief yet starts at 1", N.next_brief_number(_rows, "brand-b", "no-such-product") == 1)
check("DXS-01 is BRAND-A CRUSH brief-0001, inside BRAND-A only",
      N.brand_alias("brand-a", "dxs01") == ("crush", "brief-0001") and "dxs01" not in AL["aliases"])
try:
    N.brief_header("brand-a", "brief-0001"); _amb = False
except N.AmbiguousBrief:
    _amb = True
check("BRAND-A brief-0001 with no product is refused (old p001 and CRUSH share it)", _amb)
check("with the product it is CRUSH's", (N.brief_header("brand-a", "brief-0001", "crush") or {}).get("product") == "crush")

print("\nThe batch")
check("a batch id is `batch-YYYY-MM-DD-a`",
      N.BATCH_NEW.match(N.batch_id()) is not None, N.batch_id())
check("an old batch normalises", N.norm_batch("260902a") == "batch-2026-09-02-a")
import tempfile as _tf, datetime as _dt
with _tf.TemporaryDirectory() as td:
    root = Path(td) / "runs"; today = _dt.date.today()
    (root / "x").mkdir(parents=True)
    (root / "x/manifest.json").write_text(json.dumps({
        "batch": N.batch_id(today, "a"),
        "ads": [{"name": N.asset_name(N.ad_name(*[n[k] if k != "batch" else N.batch_id(today, "b")
                                                     for k in N.AD_FIELDS]), 1)},
                {"name": OLD.replace("260902a", f"{today:%y%m%d}c") + "-a01"}]}))
    (root / "y").mkdir()
    (root / "y/manifest.json").write_text(json.dumps({"ads": [{"name": "old-style-row"}]}))
    used = N.batches_used(today, roots=[root])
    check("used letters are read off the field named `batch`, in both forms",
          used == {"a", "b", "c"}, str(used))
check("next_batch scans the real run roots",
      N.RUNS[0] == WS / "runs" and N.RUNS[1] == WS / "records" / "runs")   # runs/<lane>/<brand>/ since 2026-09-30
check("next_batch hands out today's next free letter",
      N.BATCH_NEW.match(N.next_batch("any")) is not None, N.next_batch("any"))


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
check("an empty value is refused — every value of a name is written",
      refused(lambda: N.ad_name("b", "", "static", "ai", "none", "a", "pr",
                                "an", "c", "f", "br", "9x16", "260101a")))
check("a rename onto an existing name is refused",
      refused(lambda: N.rename_to(__file__, __file__.replace(
          "selfcheck.py", "names.py"))))


print("\nThe angle vocabulary")
signed = N.signed_angles("brand-b")
check("the brand's angle source is readable", signed is not None)
check("an unsigned angle is flagged",
      N.check_angle("brand-b", "somethingmadeup") is not None)
check("a signed angle passes",
      N.check_angle("brand-b", "pigmentmemory") is None,
      f"signed: {list(signed or [])}")

print("\nDelivered batches")
# Recursive, and per lane. Manifests sit beside the assets, and how deep
# that is differs by lane and by run — a shallow glob silently checked one
# batch and reported all-clear.
mans = sorted({m for r in N.RUNS if r.is_dir() for m in r.rglob("manifest.json")})
check("at least one delivered batch exists", bool(mans))
for m in mans:
    d = json.loads(m.read_text())
    if not isinstance(d, dict):
        continue                          # an image-teardown iteration list, not a delivery
    run = m.parent.parent.name
    # Retired batches from before the convention keep their old manifests;
    # rows without a name are not ours to check.
    names = [r["name"] for r in d.get("ads", []) if isinstance(r, dict) and "name" in r]
    if not names or "ad_name" not in d:
        continue                          # a voice-over or teardown manifest, not a delivery
    check(f"{run}: every asset name parses (either form)",
          all(N.parse_any(n) for n in names), f"{names[:1]}")
    check(f"{run}: every asset belongs to the declared ad unit",
          all((N.parse_any(n) or {}).get("ad_name") == d["ad_name"] for n in names))
    on_disk = {p.stem for p in m.parent.glob("*.png")}
    if not on_disk:
        # Pictures are content and live on Drive; a fresh checkout has the
        # manifest and no PNGs. Said, not scored — a gitignored file is not
        # a missing file.
        print(f"  [GAP ] {run} ({m.parent.name[:40]}): pictures not on this disk — file check skipped")
        continue
    check(f"{run}: every file the manifest claims exists",
          not N.audit(m), str(N.audit(m))[:80])
    check(f"{run}: no unnamed asset in the folder",
          all(N.parse_any(x) for x in on_disk),
          str(sorted(x for x in on_disk if not N.parse_any(x))[:2]))

# ------------------------------------------------------- the swipe join ---
# One vocabulary, or the join is fiction. The swipe corpus describes a
# competitor's ad in these same words so that a Meta export and the swipe
# library group on the same columns; if the two ever drift, a report that
# looks joined is silently comparing two different questions.
print("\nThe swipe join")
SWIPE = WS / "components" / "swipe-paid"   # a component since 2026-09-22 (was lab/damon/swipe-paid)
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

# The swipe library calls a copy block a BLOCK, not an angle: an angle is
# the signed read on a problem and lives on the creative, not on the file.
block_files = sorted(SWIPE.glob("*/blocks.json")) if SWIPE.is_dir() else []
check("the swipe library has brands in it", bool(block_files))
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
# one core avatar. Stating that in a document is not enough — the BRAND-A bank
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
    roster = BP.brand_path(brand_dir.name, "ai-elements/characters", "casting", "roster.json")
    if roster.is_file():
        for p in json.loads(roster.read_text()).get("people", []):
            for s in [p.get("sub")] + list(p.get("also_plays", [])):
                if s: declared.add(s)
    lineage = BP.brand_path(brand_dir.name, "ai-elements/characters", "casting", "lineage.json")
    cores = {p.parent.name for p in (brand_dir / "core-avatars").glob("*/profile.md")}
    if lineage.is_file():
        declared |= set(json.loads(lineage.read_text()).get("subs", {}))
    for s in sorted(declared):
        check(f"{brand_dir.name}: declared sub `{s}` resolves to a card or a core",
              N.sub_key(s) in cards or s in cores, s)

print(f"\n{ok} ok · {fail} failing\n")
sys.exit(1 if fail else 0)
