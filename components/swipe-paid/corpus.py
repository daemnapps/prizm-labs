#!/usr/bin/env python3
"""One corpus over every swipe lane.

    python3 corpus.py build      rebuild sources + creatives from all lanes
    python3 corpus.py report     what is in it, by lane

Three lanes, one shape:

    paid      competitor ads, from their live library      swipe-paid/<brand>/
    own       ads we ran, from our own accounts            own/<account>/ads.json
    organic   posts the avatar's world watches             ../swipe-organic/records/

They are all the same kind of object — a creative with a form, a maker, a
person in it, a problem, an angle, an execution, a template and a frame — so
they land in one table described in one vocabulary (`naming/names.py`,
CREATIVE_FIELDS). What differs is only where they came from and what we know
for free:

    paid      nothing is known until a person judges it
    own       EVERYTHING is known — our ads are named in the convention, so
              the fields are parsed out of the ad name, not guessed
    organic   platform and format are known; the rest is judged

That asymmetry is the point of putting them in one table. Our own ads arrive
already described, so they are the labelled set the judged ones are read
against.

The lane files stay the record; this table is derived and rebuilt, never
migrated.
"""
import glob, importlib.util, json, os, re, sqlite3, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LAB, "naming"))
import names as N

DB = os.path.join(HERE, "swipe.db")

# The funnel-stage heuristic already exists for the competitor lane. Import it
# rather than writing a second one: a stage rule that differs between lanes
# makes the one bar that compares them a lie.
_spec = importlib.util.spec_from_file_location("swipebuild", os.path.join(HERE, "build.py"))
_b = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(_b)
    stage_of, is_seasonal = _b.stage_of, _b.is_seasonal
except Exception:
    stage_of = lambda h, b="": "unclassified"
    is_seasonal = lambda h, b="": 0
ORGANIC = os.path.join(LAB, "swipe-organic", "records", "avatar-feeds")
for _r in Path(HERE).parents:          # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
# The lab root on the Drive, for OUR OWN media only (not a swipe pool); the
# pools' labels come from swipe_home.
DRIVE = str(swipe_home.shared_assets() / "lab" / "damon")
# Where our own delivered assets live, so an ad in the account can be shown as
# the picture we actually made. The ad name is the prefix of the filename —
# that is what the naming convention is for.
OWN_ASSETS = [os.path.join(DRIVE, "image-production", "runs"),
              os.path.join(DRIVE, "video-production", "runs")]

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  lane        TEXT NOT NULL,   -- paid | own | organic
  source      TEXT NOT NULL,   -- brand, ad account, or feed
  label       TEXT,
  market      TEXT,
  creatives   INTEGER,
  judged      INTEGER,         -- how many have a source field filled in
  swiped      INTEGER,
  drive_path  TEXT,
  PRIMARY KEY (lane, source)
);

CREATE TABLE IF NOT EXISTS creatives (
  swipe_id    TEXT PRIMARY KEY,   -- swipe:<lane>:<source>:<ref>
  lane        TEXT NOT NULL,
  source      TEXT NOT NULL,
  ref         TEXT NOT NULL,      -- the id in its own world
  title       TEXT,               -- headline, ad name, or caption
  body        TEXT,
  group_slug  TEXT,               -- angle / batch / feed section
  group_label TEXT,
  url         TEXT,               -- where it lives publicly
  thumb       TEXT,               -- served path or absolute url
  file        TEXT,               -- path under the Drive mirror, if we hold it
  variants    INTEGER,            -- how hard they cloned it
  posted      TEXT,
  -- the shared vocabulary
  media       TEXT, source_f TEXT, talent TEXT, problem TEXT,
  angle       TEXT, concept TEXT, format TEXT, ratio TEXT,
  -- Read off the frame, not the copy. The hook is the line burned into the
  -- first frame and it is the closest thing to the angle a machine can get at
  -- without a person: two ads on one copy block took $__ and $__, and the
  -- only visible difference was this line.
  hook        TEXT,
  shows       TEXT,
  person      TEXT,
  problem_shown TEXT,
  demonstration TEXT,
  style       TEXT,
  frame_read  TEXT,
  stage       TEXT,               -- top | mid | bottom | unclassified
  seasonal    INTEGER,            -- 1 = a dated promo, a volume play not a strategy
  known       TEXT,               -- named | judged | unjudged
  verdict     TEXT,
  -- Only the own lane has these: what the ad actually did. They are the
  -- reason our own ads sit in the same table as the swiped ones — the
  -- labelled set is only worth having if it carries the outcome.
  spend       REAL,
  impressions INTEGER,
  purchases   REAL,
  revenue     REAL
);

CREATE INDEX IF NOT EXISTS idx_cr_lane   ON creatives(lane, source);
CREATE INDEX IF NOT EXISTS idx_cr_group  ON creatives(lane, source, group_slug);
CREATE INDEX IF NOT EXISTS idx_cr_known  ON creatives(known);

-- Everything we hold, in the columns a Meta export is grouped by.
CREATE VIEW IF NOT EXISTS all_creatives AS
SELECT lane, source, swipe_id, media, source_f AS source_field, talent,
       problem, angle, concept, format, ratio, verdict, known, title, url
FROM creatives;

-- The hooks, which is where the angle actually lives. One row per creative
-- that has been through the frame scan, heaviest first.
CREATE VIEW IF NOT EXISTS hooks AS
SELECT lane, source, group_label AS copy_block, hook, problem_shown, person,
       demonstration, style, spend, swipe_id
FROM creatives WHERE hook IS NOT NULL AND hook != ''
ORDER BY COALESCE(spend,0) DESC;

-- The labelled set: our own ads, whose fields came out of their names, with
-- what they earned. This is the half that makes prediction possible — every
-- other lane is described in the same words but has no outcome attached.
CREATE VIEW IF NOT EXISTS named AS
SELECT swipe_id, source, title, media, source_f, talent, problem, angle,
       concept, format, ratio, spend, impressions, purchases, revenue,
       CASE WHEN spend > 0 THEN round(revenue / spend, 2) END AS roas
FROM creatives WHERE known = 'named' ORDER BY spend DESC;

-- The queue: what a person still has to look at, heaviest first.
CREATE VIEW IF NOT EXISTS judge_queue AS
SELECT lane, source, group_slug, group_label, COUNT(*) AS creatives,
       SUM(known = 'unjudged') AS unjudged,
       SUM(verdict = 'swipe')  AS swiped
FROM creatives GROUP BY lane, source, group_slug
ORDER BY unjudged = 0, creatives DESC;
"""

def norm_body(t, n=400):
    """A copy block, normalised enough that the same words cluster.

    Same idea as the competitor sweep: an account runs one block of copy
    against many pictures, so the block — not the ad — is the unit worth
    ranking. Truncated because Meta stores the body with trailing variations
    (emoji runs, a shifting CTA line) that would split one block into ten.
    """
    return re.sub(r"\s+", " ", (t or "")).strip().lower()[:n]


def slugify(s, n=52):
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:n] or "none")


BLANK = {k: N.UNCLASSIFIED for k in N.CREATIVE_FIELDS}
# One judgement record for every lane, keyed by swipe_id. The lane files stay
# as their own systems wrote them; what a person decided lives here and is
# laid over the top on every rebuild. Three write paths for one idea is how a
# judgement gets lost the first time a lane is re-ingested.
JUDGEMENTS = os.path.join(HERE, "judgements.json")


def judgements():
    if not os.path.isfile(JUDGEMENTS):
        return {}
    try:
        return json.load(open(JUDGEMENTS))
    except json.JSONDecodeError:
        return {}


def save_judgement(swipe_id, fields=None, verdict=None):
    """Record one judgement. Fields already decided are never cleared by a
    later call that does not mention them."""
    j = judgements()
    e = j.setdefault(swipe_id, {"fields": {}, "verdict": ""})
    for k, v in (fields or {}).items():
        if k in N.CREATIVE_FIELDS and str(v).strip():
            e["fields"][k] = N.slug(v)
    if verdict:
        e["verdict"] = N.slug(verdict)
    json.dump(j, open(JUDGEMENTS, "w"), indent=1, sort_keys=True)
    return e


def row(lane, source, ref, **kw):
    f = dict(BLANK); f.update(kw.pop("fields", {}) or {})
    known = kw.pop("known", None) or (
        "named" if f.get("source") not in (N.UNCLASSIFIED,) and kw.get("_named")
        else ("judged" if f.get("source") != N.UNCLASSIFIED else "unjudged"))
    kw.pop("_named", None)
    return {"swipe_id": N.corpus_swipe_id(lane, source, ref),
            "lane": lane, "source": N.slug(source), "ref": str(ref),
            "title": kw.get("title"), "body": kw.get("body"),
            "group_slug": kw.get("group_slug"), "group_label": kw.get("group_label"),
            "url": kw.get("url"), "thumb": kw.get("thumb"), "file": kw.get("file"),
            "variants": kw.get("variants", 1), "posted": kw.get("posted"),
            "media": f["media"], "source_f": f["source"], "talent": f["talent"],
            "problem": f["problem"], "angle": f["angle"], "concept": f["concept"],
            "format": f["format"], "ratio": f["ratio"],
            "hook": None, "shows": None, "person": None,
            "problem_shown": None, "demonstration": None, "style": None,
            "frame_read": None,
            "stage": kw.get("stage", "unclassified"),
            "seasonal": kw.get("seasonal", 0),
            "known": known, "verdict": kw.get("verdict", ""),
            "spend": kw.get("spend"), "impressions": kw.get("impressions"),
            "purchases": kw.get("purchases"), "revenue": kw.get("revenue")}


# ------------------------------------------------------------------ paid ---
def lane_paid():
    out, srcs = [], []
    for f in sorted(glob.glob(os.path.join(HERE, "*", "blocks.json"))):
        brand = os.path.basename(os.path.dirname(f))
        doc = json.load(open(f))
        for a in doc["blocks"]:
            for ref, m in a.get("media", {}).items():
                is_v = bool(m.get("video"))
                rel = (f"swipe-paid/{brand}/blocks/{a['slug']}/"
                       + (f"video/{ref}.mp4" if is_v else f"photos/{ref}.jpg"))
                poster = rel.replace(".mp4", "_poster.jpg") if is_v else rel
                out.append(row("paid", brand, ref,
                               fields=m.get("fields"),
                               title=a.get("headline"), body=a.get("primary_text"),
                               group_slug=a["slug"], group_label=a.get("headline"),
                               stage=a.get("stage", "unclassified"),
                               seasonal=a.get("seasonal", 0),
                               url=a.get("landing_page"), thumb=poster, file=rel,
                               variants=m.get("variants", 1),
                               verdict=m.get("verdict", "")))
        srcs.append(("paid", brand, brand, "", swipe_home.label("paid", brand)))
    return out, srcs


# ------------------------------------------------------------------- own ---
def own_asset(ad_name):
    """The picture we actually made, found by name prefix.

    Drop the last field of any delivered filename and you have the ad unit it
    was uploaded in — so the ad in the account and the file on Drive join with
    a prefix match and no id to keep in sync."""
    for root in OWN_ASSETS:
        # `-a01` is the old asset suffix, `_asset-01` the new; a unit named
        # either way finds its picture
        for pat in (ad_name + "-a*.*", ad_name + "_asset-*.*"):
            for p in glob.glob(os.path.join(root, "**", pat), recursive=True):
                if p.lower().endswith((".png", ".jpg", ".jpeg", ".mp4")):
                    return os.path.relpath(p, DRIVE)
    return None


def lane_own():
    out, srcs = [], []
    files = sorted(glob.glob(os.path.join(HERE, "own", "*", "ads.json")))
    # Our own live libraries, swept from the outside the way a competitor is.
    files += sorted(glob.glob(os.path.join(HERE, "own", "library", "*.json")))
    for f in files:
        acct = (os.path.splitext(os.path.basename(f))[0]
                if os.path.basename(os.path.dirname(f)) == "library"
                else os.path.basename(os.path.dirname(f)))

        doc = json.load(open(f))
        ads = doc.get("ads", [])
        # Rank the blocks by spend, not by count. A competitor's conviction is
        # read off how many variants they cloned; ours is read off what we
        # actually paid to run — the one signal they can never give us.
        by_block, spend = {}, {}
        for ad in ads:
            b = norm_body(ad.get("body") or ad.get("title"))
            by_block.setdefault(b, []).append(ad)
            spend[b] = spend.get(b, 0) + (ad.get("spend") or 0)
        rank = {b: i + 1 for i, b in enumerate(
            sorted(by_block, key=lambda b: (-spend[b], -len(by_block[b]))))}
        for ad in ads:
            block = norm_body(ad.get("body") or ad.get("title"))
            nn = f"{rank[block]:02d}"
            unit = ad.get("unit")
            p = N.parse(unit) if unit else None
            fields = {k: p[k] for k in N.CREATIVE_FIELDS if p and k in p}
            # A derived fact beats a blank: the creative's own story spec says
            # whether it is a video, so the name does not have to.
            if ad.get("media"):
                fields["media"] = ad["media"]
            # The picture: our own delivered file when the name resolves one,
            # otherwise Meta's own thumbnail. A named ad shows what we made;
            # an unnamed one still shows something.
            rel = own_asset(unit) if p else None
            out.append(row("own", acct, ad["id"],
                           fields=fields, _named=bool(p),
                           known="named" if p else "unjudged",
                           title=ad.get("name"),
                           body=ad.get("body") or ad.get("title"),
                           group_slug=f"{nn}_{slugify(block or 'no-copy')}",
                           group_label=(block[:110] or "— no body copy —"),
                           stage=stage_of(ad.get("title") or "", ad.get("body") or ""),
                           seasonal=is_seasonal(ad.get("title") or "", ad.get("body") or ""),
                           url=ad.get("preview") or ad.get("landing_page"),
                           thumb=rel or ad.get("thumb"), file=rel,
                           posted=ad.get("created"),
                           spend=ad.get("spend"), impressions=ad.get("impressions"),
                           purchases=ad.get("purchases"), revenue=ad.get("revenue")))
        srcs.append(("own", acct, doc.get("label") or acct,
                     doc.get("source", ""), ""))
    return out, srcs


# --------------------------------------------------------------- organic ---
def lane_organic():
    out, srcs = [], []
    for f in sorted(glob.glob(os.path.join(ORGANIC, "*", "items.json"))):
        feed = os.path.basename(os.path.dirname(f))
        doc = json.load(open(f))
        items = doc.get("items", doc)
        for key, it in items.items():
            # platform is a fact, and it is the closest thing organic has to
            # `media` — a short-form video post is a video creative.
            fields = {"media": "video" if it.get("platform") in
                      ("tiktok", "youtube", "reels") else N.UNCLASSIFIED}
            # The creator is the unit here, not the post. swipe-organic's own
            # method is one profile per creator, and a room is legible through
            # who is in it — a platform column only says where, never who.
            who = slugify(it.get("author") or "unknown", 40)
            out.append(row("organic", feed, key.replace(":", "-"),
                           fields=fields,
                           title=(it.get("caption") or "")[:180],
                           body=it.get("caption"),
                           stage=stage_of(it.get("caption") or "", ""),
                           seasonal=is_seasonal(it.get("caption") or "", ""),
                           group_slug=f"{it.get('platform','?')}-{who}",
                           group_label=(f"@{it.get('author')}" if it.get("author")
                                        else "unattributed")
                                       + f" · {it.get('platform','?')}",
                           url=it.get("url"), thumb=it.get("cover"),
                           posted=it.get("posted"),
                           verdict="swipe" if it.get("status") == "kept" else ""))
        srcs.append(("organic", feed, feed.replace("--", " · "), "",
                     swipe_home.label("organic", feed)))
    return out, srcs


# ----------------------------------------------------------------- build ---
def build():
    rows, srcs = [], []
    for fn in (lane_paid, lane_own, lane_organic):
        r, s = fn()
        rows += r; srcs += s
    # What the frame said. Recorded by scan_frames.py, laid over the corpus
    # like a judgement — a machine reading, below a person's, above nothing.
    fpath = os.path.join(HERE, "frames.json")
    frames = json.load(open(fpath)) if os.path.isfile(fpath) else {}
    for r in rows:
        f = frames.get(r["swipe_id"])
        if not f or f.get("error"):
            continue
        r["hook"] = f.get("hook") or None
        r["shows"] = f.get("shows")
        r["person"] = f.get("person")
        r["problem_shown"] = f.get("problem_shown")
        r["demonstration"] = f.get("demonstration")
        r["style"] = f.get("style")
        r["frame_read"] = f.get("read")
        # `style` is a fact about the picture and answers the same question
        # `source` does — is this made or filmed — so it seeds it rather than
        # leaving the field blank for a person who can see it at a glance.
        if r["source_f"] == N.UNCLASSIFIED and f.get("style") in (
                "3d-animation", "illustration"):
            r["source_f"] = "ai"

    # A person's judgement wins over anything a lane adapter derived.
    j = judgements()
    for r in rows:
        e = j.get(r["swipe_id"])
        if not e:
            continue
        for k, v in (e.get("fields") or {}).items():
            r["source_f" if k == "source" else k] = v
        if e.get("verdict"):
            r["verdict"] = e["verdict"]
        if r["source_f"] != N.UNCLASSIFIED and r["known"] != "named":
            r["known"] = "judged"
    con = sqlite3.connect(DB)
    for v in ("all_creatives", "named", "judge_queue"):
        con.execute(f"DROP VIEW IF EXISTS {v}")
    for t in ("sources", "creatives"):
        con.execute(f"DROP TABLE IF EXISTS {t}")
    con.executescript(SCHEMA)
    cols = list(rows[0]) if rows else []
    con.executemany(f"INSERT OR REPLACE INTO creatives ({','.join(cols)}) "
                    f"VALUES ({','.join('?' * len(cols))})",
                    [tuple(r[c] for c in cols) for r in rows])
    for lane, source, label, market, drive in srcs:
        s = N.slug(source)
        n = con.execute("SELECT COUNT(*), SUM(known!='unjudged'), "
                        "SUM(verdict='swipe') FROM creatives "
                        "WHERE lane=? AND source=?", (lane, s)).fetchone()
        con.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?,?,?,?)",
                    (lane, s, label, market, n[0], n[1] or 0, n[2] or 0, drive))
    con.commit()
    for lane, n, k in con.execute(
            "SELECT lane, COUNT(*), SUM(known='named') FROM creatives GROUP BY lane"):
        print(f"  {lane:<8} {n:>5} creatives · {k or 0} already named")
    print(f"  {'total':<8} {len(rows):>5}")
    con.close()


def report():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    for r in con.execute("SELECT * FROM sources ORDER BY lane, creatives DESC"):
        print(f"  {r['lane']:<8} {r['source']:<22} {r['creatives']:>5} "
              f"· {r['judged']:>4} known · {r['swiped']:>3} swiped")
    con.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    {"build": build, "report": report}.get(cmd, lambda: sys.exit(__doc__))()
