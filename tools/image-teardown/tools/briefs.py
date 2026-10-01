#!/usr/bin/env python3
"""The brief register — the bank brief ids are looked up in, never coined.

    briefs.py list                          every brief, newest first
    briefs.py open <run> --brand <brand> [--type image-ai]
                                            give a finished run its id
    briefs.py open <run> --brand <brand> --type video-creator
                                            the same for a video-teardown creator
                                            brief (runs/video-teardown/<brand>/<run>/brief.md)
    briefs.py open runs/<tool>/<brand>/<label> --brand <brand> --type <type>
                                            any other lane's finished run (it has
                                            a deliverable/); every lane run gets
                                            the id written into its run.json
    briefs.py open <run> ... --link <link id> [--link <link id>]
                                            record the landing page(s) the brief
                                            sends people to, by catalog link id
    briefs.py link <id> <link id> [...]     add landing page(s) to an existing brief
    briefs.py show <id>                     one brief's record (p140 or brief-0140)
    briefs.py next --brand <brand> [--type <type>]
                                            the id the next brief would get
    briefs.py migrate                       write `id` + `brief` onto every entry
    briefs.py check                         every brief resolves under both spellings

A brief id has been sitting in the ad name since the naming convention was
written — the `brief` field, `p003` in
`<brand>-<product>-static-ai-<cast>-…-<angle>-<concept>-p003-9x16-260907b`. It is
in the name rather than the manifest because a Meta report is often read by
someone with no repo access, and "which briefs produce winners" is worth
ranking.

**Nothing defined those ids.** p001–p004 and p140–p142 are live in ad names
and in the creative ledger with no file behind them, so a new run either
guessed a number or wrote something off-convention (`braille`, 2026-09-13).
This is that file: one record per brief, so the id resolves to the swipe it
came from, the run that produced it, and the ads that carry it.

Ids are per brand and sequential in the brand's own block, because that is
how the live ones already read; the seeds live in briefs.json.

TWO SPELLINGS, ONE NUMBER (Master Plan v2, 3.3 — 2026-09-28). The id is
`brief-NNNN`, type-first, for EVERY kind of brief — image, sequence, video,
email, page, copy, concept — all counting in the brand's one block. `p140`
is the same brief as `brief-0140`: the old code stays the register key (the
worksheets, the drafts and the live ad names carry it) and every entry also
carries `brief`, the new id. Readers take either; `next_id()` hands out the
new one. See components/naming/brief-aliases.json.
"""
import argparse, json, re, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REGISTER = HERE / "briefs.json"
REPO = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
# Runs file to the repo's runs/ folder, per brand: runs/image-teardown/<brand>/<run>.
# `tools/image-teardown/runs` is the pre-move home and is still looked in.
RUNS = REPO / "runs" / "image-teardown"
OLD_RUNS = HERE / "runs"
# Video briefs are video-teardown runs: runs/video-teardown/<brand>/<run>/brief.md
# + run.json. Creator briefs went out from there before they had a number
# (2026-09-29). They sat in tools/video-teardown/records/runs/ until
# 2026-09-30 (system-blueprint/RUNS-MOVE-2026-09-30.md); that old
# home is still looked in for one release.
VIDEO_RUNS = REPO / "runs" / "video-teardown"
OLD_VIDEO_RUNS = REPO / "components" / "video-teardown" / "records" / "runs"
VIDEO_TYPES = ("video-ai", "video-creator")
ALIASES = REPO / "components" / "naming" / "brief-aliases.json"

sys.path.insert(0, str(REPO / "components" / "naming"))
import names as N                                       # brief_id, brief_code

# Every kind of brief the register issues an id for. One list, one number
# range per brand — a video brief and an image brief for the same brand
# count in the same block, so "brief-0145" is one thing whatever it briefs.
TYPES = ["image-ai", "image-creator", "sequence-ai", "sequence-creator",
         "video-ai", "video-creator", "email", "page", "copy", "concept"]
DEFAULT_TYPE = "image-ai"                               # what this lane makes

# Each brand gets its own hundred. The first two blocks are read off ids
# already live in ad names — <brand> at p001, <brand> at p140 — and every brand
# after them is allocated the next free hundred the first time it opens a
# brief. It used to be a hand-written map, so standing up a new brand exited
# and told somebody to edit this file, which is a person in the loop for no
# reason (2026-09-14).
BLOCK_SIZE = 100


def block_for(reg, brand):
    """This brand's hundred, allocated and remembered on first use."""
    # The first blocks were read off ids already live in ad names and live in
    # briefs.json as data. No brand is named in this file — a brand name in
    # code is how the next brand's run quietly aims at the last brand.
    blocks = reg.setdefault("blocks", {})
    if brand not in blocks:
        taken = set(blocks.values())
        n = 1
        while n in taken:
            n += BLOCK_SIZE
        blocks[brand] = n
    return blocks[brand]


class Briefs(dict):
    """The register's `briefs` (and `retired`) table: keyed on the old code
    (`p140`), looked up by either spelling. `reg["briefs"]["brief-0140"]`,
    `.get("brief-0140")` and `"brief-0140" in reg["briefs"]` all land on the
    `p140` row, so the twenty-odd readers that index this dict by whatever id
    they were handed read both spellings without each being rewritten.
    Iteration, keys() and the saved file stay on the old code — one key per
    brief, never two rows for one number."""

    @staticmethod
    def _k(k):
        return key(k) if isinstance(k, str) else k

    def __getitem__(self, k):
        return dict.__getitem__(self, self._k(k))

    def __setitem__(self, k, v):
        dict.__setitem__(self, self._k(k), v)

    def __delitem__(self, k):
        dict.__delitem__(self, self._k(k))

    def __contains__(self, k):
        return dict.__contains__(self, self._k(k))

    def get(self, k, default=None):
        return dict.get(self, self._k(k), default)

    def pop(self, k, *default):
        return dict.pop(self, self._k(k), *default)

    def setdefault(self, k, default=None):
        return dict.setdefault(self, self._k(k), default)


def load():
    reg = json.loads(REGISTER.read_text()) if REGISTER.is_file() else {"briefs": {}}
    reg["briefs"] = Briefs(reg.get("briefs", {}))
    if "retired" in reg:
        reg["retired"] = Briefs(reg["retired"])
    return reg


def save(reg):
    out = {k: (dict(v) if isinstance(v, Briefs) else v) for k, v in reg.items()}
    REGISTER.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")


def _number(k):
    """The number inside either spelling, or None."""
    m = N.BRIEF_OLD.match(str(k)) or N.BRIEF_NEW.match(str(k))
    return int(m.group(1)) if m else None


def taken_numbers(reg):
    """Every brief number that can never be issued again.

    Retired ids stay taken. A brief pulled off the board is not a free
    number: the id travels into ad names and creative records, and
    reissuing it would point two different ads at one row.
    (Damon, 2026-09-15: "remove those" — p011-p014.) The three numbers that
    were never used stay unused for the same reason — a number nobody can
    find a brief for must not suddenly have one."""
    keys = list(reg["briefs"]) + list(reg.get("retired", {}))
    keys += [r.get("brief") for r in reg["briefs"].values() if isinstance(r, dict)]
    keys += N.brief_aliases().get("never_used", [])
    return {n for n in (_number(k) for k in keys if k) if n is not None}


def check_type(kind):
    kind = kind or DEFAULT_TYPE
    if kind not in TYPES:
        sys.exit(f"--type must be one of {', '.join(TYPES)}, not {kind!r}")
    return kind


def next_id(reg, brand, kind=None):
    """The next free id in this brand's block, as `brief-NNNN`. Never reuses
    one. `kind` is checked against TYPES and does not move the number: every
    brief type counts in the brand's one block."""
    check_type(kind)
    lo = block_for(reg, brand)
    taken = taken_numbers(reg)
    n = lo
    while n in taken:
        n += 1
    if n >= lo + BLOCK_SIZE:
        # Spill into the next free hundred rather than stopping. A full block
        # is a counting problem, not a decision anybody needs to make.
        return next_id({"briefs": reg["briefs"], "retired": reg.get("retired", {}),
                        "blocks": {**reg.get("blocks", {}),
                                   brand: max(reg.get("blocks", {}).values() or [0])
                                   + BLOCK_SIZE}}, brand, kind)
    return N.brief_id(n)


def key(any_id):
    """The register key for either spelling: `brief-0140` -> `p140`."""
    return N.brief_code(any_id)


def get(reg, any_id):
    """(key, record) for either spelling, or (key, None)."""
    k = key(any_id)
    rec = reg["briefs"].get(k)
    if rec is None:
        # a record filed under the new spelling, should one ever be
        want = N.brief_id(any_id)
        for kk, r in reg["briefs"].items():
            if kk == want or (isinstance(r, dict) and r.get("brief") == want):
                return kk, r
    return k, rec


def ids(reg, wanted):
    """A list of ids in either spelling -> register keys, order kept."""
    return [key(x.strip()) for x in wanted if x and x.strip()]


def run_dir(rec_or_run, brand=None):
    """Where a brief's run lives. runs/image-teardown/<brand>/<run> first,
    then the un-branded and the pre-move homes — found, never assumed."""
    if isinstance(rec_or_run, dict):
        run, brand = rec_or_run.get("run"), brand or rec_or_run.get("brand")
    else:
        run = rec_or_run
    if not run:
        return None
    tries = ([RUNS / brand / run] if brand else []) + [RUNS / run, OLD_RUNS / run]
    tries += sorted(RUNS.glob(f"*/{run}")) if RUNS.is_dir() else []
    return next((t for t in tries if t.is_dir()), tries[0])


def stamp(reg):
    """Every entry carries `id` (the old code, the key) and `brief` (the new
    id). Idempotent; returns how many entries changed."""
    n = 0
    for k, rec in reg["briefs"].items():
        if not isinstance(rec, dict):
            continue
        want = {"id": k, "brief": N.brief_id(k)}
        if any(rec.get(f) != v for f, v in want.items()):
            # id and brief first, so the record reads as what it is
            rest = {f: v for f, v in rec.items() if f not in want}
            rec.clear(); rec.update(want); rec.update(rest); n += 1
    return n


def check(reg):
    """Every brief resolves under both spellings; every number sits in the
    alias file; no number is issued twice. Returns (ok, problems, n)."""
    probs = []
    aliases = N.brief_aliases().get("aliases", {})
    seen = {}
    for k, rec in list(dict.items(reg["briefs"])):
        old, new = N.brief_code(k), N.brief_id(k)
        if not N.BRIEF_OLD.match(k):
            probs.append(f"{k}: register key is not the old code")
        if aliases.get(old) != new:
            probs.append(f"{k}: not in brief-aliases.json as {old} -> {new}")
        if isinstance(rec, dict) and (rec.get("id") != old or rec.get("brief") != new):
            probs.append(f"{k}: record is not stamped id={old} brief={new}")
        for spelling in (old, new, str(_number(k))):
            kk, got = get(reg, spelling)
            if got is not rec or kk != k:
                probs.append(f"{k}: {spelling!r} does not resolve to it")
        n = _number(k)
        if n in seen:
            probs.append(f"{k}: number {n} also used by {seen[n]}")
        seen[n] = k
    for k in list(reg.get("retired", {})) + N.brief_aliases().get("never_used", []):
        if _number(k) in seen:
            probs.append(f"{k}: retired/never-used number is also a live brief")
    for brand in reg.get("blocks", {}):
        nxt = _number(next_id(reg, brand))
        if nxt in taken_numbers(reg):
            probs.append(f"{brand}: next id {nxt} is already taken")
    return not probs, probs, len(reg["briefs"])


def read_run(run: Path):
    """What the run itself says it is. Nothing here is invented."""
    src_file = next((p for p in (run / "assets/source.json", run / "source.json") if p.is_file()), None)
    src = json.loads(src_file.read_text()) if src_file else {}
    # Older runs keep their stages in out/; runs filed flat (the retired
    # carousel-creator lane, runs/image-teardown/<brand>/<run>/0*.md) do not.
    out = run / "out" if (run / "out").is_dir() else run
    stages = {p.name: p for p in sorted(out.glob("0*.md"))} if out.is_dir() else {}
    brief = out / "06-brief.md"
    # A FILED run (gates.file_record) keeps its brief in deliverable/, where the
    # standard puts the thing a person traffics — read it there too, or a filed
    # run can never be given its number (2026-10-01).
    if not brief.is_file() and (run / "deliverable" / "06-brief.md").is_file():
        brief = run / "deliverable" / "06-brief.md"
        stages[brief.name] = brief
    fields = {}
    if brief.is_file():
        # stage 6 declares problem / angle / concept in a json block
        m = re.search(r'\{[^{}]*"problem"[^{}]*\}', brief.read_text(), re.S)
        if m:
            try:
                fields = json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return src, stages, fields


def add_alias(bid, new):
    """Write `pNNN -> brief-NNNN` into brief-aliases.json, so `check` finds
    every number it issued there."""
    al = json.loads(ALIASES.read_text()) if ALIASES.is_file() else {"aliases": {}}
    if al.setdefault("aliases", {}).get(bid) != new:
        al["aliases"][bid] = new
        ALIASES.write_text(json.dumps(al, indent=1, ensure_ascii=False) + "\n")
        N._ALIASES = None


def read_video_run(run: Path):
    """What a video-teardown run says it is: run.json, and the brief's title
    (its first `# ` line). Nothing here is invented."""
    meta = json.loads((run / "run.json").read_text()) if (run / "run.json").is_file() else {}
    title = next((l[2:].strip() for l in (run / "brief.md").read_text().splitlines()
                  if l.startswith("# ")), None)
    return meta, title


def video_run(run_name, brand=None):
    """Where a video-teardown run lives: runs/video-teardown/<brand>/<run>
    first, then any brand, then the flat and the pre-move homes."""
    tries = ([VIDEO_RUNS / brand / run_name] if brand else [])
    tries += sorted(VIDEO_RUNS.glob(f"*/{run_name}")) if VIDEO_RUNS.is_dir() else []
    tries += [VIDEO_RUNS / run_name, OLD_VIDEO_RUNS / run_name]
    return next((t for t in tries if (t / "brief.md").is_file()),
                next((t for t in tries if t.is_dir()), tries[0]))


def stamp_run(run, new):
    """Write the brief id into a lane run's own run.json as `brief`, keeping
    the file's indent and escaping (cleanup plan job C, 2026-09-30)."""
    rj = Path(run) / "run.json"
    if not rj.is_file():
        return
    was = rj.read_text()
    meta = json.loads(was)
    if meta.get("brief") == new:
        return
    meta["brief"] = new
    m = re.match(r"\{\s*\n( +)\"", was)
    rj.write_text(json.dumps(meta, indent=len(m.group(1)) if m else 1,
                             ensure_ascii="\\u" in was) + "\n")


def open_video(run_name, brand, reg, product=None, avatar=None, kind="video-creator"):
    """A video-teardown brief's id. Same bank, same block, one id per run."""
    run = video_run(run_name, brand)
    if not (run / "brief.md").is_file():
        sys.exit(f"{run_name} has no brief.md in {VIDEO_RUNS} — a brief id is "
                 f"for a finished brief, not a run in progress")
    meta, title = read_video_run(run)
    if meta.get("brand") and meta["brand"] != brand:
        sys.exit(f"{run_name} is a {meta['brand']} run, not {brand}")
    new = next_id(reg, brand, kind)
    bid = key(new)
    reg["briefs"][bid] = {
        "id": bid,
        "brief": new,
        "type": kind,
        "brand": brand,
        "product": product or meta.get("product"),
        "avatar": avatar or (meta.get("audience") or {}).get("_avatar"),
        "run": run_name,
        "lane": "video-teardown",
        "title": title,
        "creator": meta.get("creator"),     # None = a GENERAL brief, any creator
        "gdoc_url": meta.get("gdoc_url"),
        "run_opened": meta.get("opened"),
        "opened": date.today().isoformat(),
        "swipe": {},                        # the image lane's shape, so its readers
        "declares": {},                     # read a video row without tripping
        "stages": [],
        "status": "for-review",
        "ads": [],
    }
    save(reg)
    add_alias(bid, new)
    stamp_run(run, new)                     # the run.json carries its number, like every lane (2026-10-01)
    return bid, reg["briefs"][bid]


EMAIL_RUNS = REPO / "runs" / "email-production"


def open_email(run_name, brand, reg, product=None, avatar=None):
    """An email-production run's id: runs/email-production/<brand>/<run>,
    finished = deliverable/email.json plus the stage-9 brief. The run is
    recorded by its repo path, so readers find it without guessing a lane."""
    p = Path(run_name)
    run = p if p.is_absolute() else (REPO / p if (REPO / p).is_dir() else EMAIL_RUNS / brand / run_name)
    if not run.is_dir():
        sys.exit(f"no email run at {run}")
    brief = next((b for b in (run / "deliverable" / "stage9--brief.md", run / "stage9--brief.md") if b.is_file()), None)
    if not (run / "deliverable" / "email.json").is_file() or not brief:
        sys.exit(f"{run.name} has no deliverable/email.json and stage-9 brief — a brief id is for a finished email")
    rel = str(run.resolve().relative_to(REPO.resolve()))
    for bid, rec in reg["briefs"].items():
        if rec.get("run") == rel:
            return bid, rec
    meta = json.loads((run / "run.json").read_text()) if (run / "run.json").is_file() else {}
    if meta.get("brand") and meta["brand"] != brand:
        sys.exit(f"{run.name} is a {meta['brand']} run, not {brand}")
    a = meta.get("assignment") or {}
    new = next_id(reg, brand, "email")
    bid = key(new)
    reg["briefs"][bid] = {
        "id": bid, "brief": new, "type": "email", "brand": brand,
        "product": product or a.get("product"),
        "avatar": avatar or a.get("avatar"),
        "run": rel, "lane": "email-production",
        "title": (a.get("occasion") or run.name)[:120],
        "send_date": a.get("send_date"),
        "run_opened": meta.get("generated_at"),
        "opened": date.today().isoformat(),
        "swipe": {"source": meta.get("source_path")},
        # an email with no offer says "none"; the register records no offer
        "declares": {"offer": None if str(a.get("offer") or "").lower() in ("", "none") else a.get("offer"),
                     "angle": a.get("angle")},
        "stages": sorted((meta.get("stages") or {}).keys()),
        "status": "for-review",
        "ads": [],
    }
    save(reg)
    add_alias(bid, new)
    stamp_run(run, new)
    return bid, reg["briefs"][bid]


PAGE_RUNS = REPO / "runs" / "page-machine"


def product_key(v):
    """A run's `product` as the catalog's key: runs write the product CARD's
    path (brands/<b>/products/<slug>/product.md or <slug>.md); the register
    and the catalog name the product by its slug (2026-10-01)."""
    if not v or "/" not in str(v):
        return v
    p = Path(str(v))
    return p.parent.name if p.name == "product.md" else p.stem


def open_page(run_name, brand, reg, product=None, avatar=None):
    """A page-machine run's id: runs/page-machine/<brand>/<run>, finished =
    the stage-6 page brief. Recorded by its repo path, like an email run."""
    p = Path(run_name)
    run = p if p.is_absolute() else (REPO / p if (REPO / p).is_dir() else PAGE_RUNS / brand / run_name)
    if not run.is_dir():
        sys.exit(f"no page run at {run}")
    brief = next((b for b in (run / "deliverable" / "stage6--brief.md", run / "stage6--brief.md") if b.is_file()), None)
    if not brief:
        sys.exit(f"{run.name} has no stage-6 brief — a brief id is for a finished page brief")
    rel = str(run.resolve().relative_to(REPO.resolve()))
    for bid, rec in reg["briefs"].items():
        if rec.get("run") == rel:
            return bid, rec
    meta = json.loads((run / "run.json").read_text()) if (run / "run.json").is_file() else {}
    if meta.get("brand") and meta["brand"] != brand:
        sys.exit(f"{run.name} is a {meta['brand']} run, not {brand}")
    new = next_id(reg, brand, "page")
    bid = key(new)
    reg["briefs"][bid] = {
        "id": bid, "brief": new, "type": "page", "brand": brand,
        "product": product_key(product or meta.get("product")),
        "avatar": avatar or meta.get("avatar"),
        "run": rel, "lane": "page-machine",
        "title": meta.get("page_name") or run.name,
        "run_opened": meta.get("started"),
        "opened": date.today().isoformat(),
        "swipe": {"source": meta.get("swipe") or meta.get("source_url")},
        "declares": {"angle": meta.get("angle"), "format": meta.get("format"), "next": meta.get("next")},
        "brief_file": str(brief.resolve().relative_to(REPO.resolve())),
        "stages": sorted((meta.get("stages") or {}).keys()),
        "status": "for-review",
        "ads": [],
    }
    save(reg)
    add_alias(bid, new)
    stamp_run(run, new)
    return bid, reg["briefs"][bid]


def _lane_run(run_name):
    """`runs/<tool>/<brand>/<label>` (any lane's filed run) -> its folder, else None."""
    p = Path(run_name)
    p = p if p.is_absolute() else REPO / p
    try:
        rel = p.resolve().relative_to(REPO.resolve())
    except ValueError:
        return None
    return p if len(rel.parts) == 4 and rel.parts[0] == "runs" and p.is_dir() else None


def open_lane(run, brand, reg, product=None, avatar=None, kind=None):
    """Any other lane's finished run (video-production, image-edit …) gets its
    id from the same bank, recorded by its repo path like an email run.
    Finished = it has a deliverable/. Nothing is invented: title, product and
    avatar come off the run or the flags."""
    rel = str(run.resolve().relative_to(REPO.resolve()))
    for bid, rec in reg["briefs"].items():
        if rec.get("run") == rel:
            return bid, rec                       # a run gets one id, for ever
    lane, run_brand = run.parts[-3], run.parts[-2]
    rj = run / "run.json"
    meta = json.loads(rj.read_text()) if rj.is_file() else {}
    if (meta.get("brand") or run_brand) != brand:
        sys.exit(f"{rel} is a {meta.get('brand') or run_brand} run, not {brand}")
    deliv = run / "deliverable"
    if not deliv.is_dir() or not any(deliv.iterdir()):
        sys.exit(f"{rel} has no deliverable/ — a brief id is for a finished "
                 f"run, not a run in progress or a test")
    title = None
    for md_file in sorted(deliv.glob("*.md")) + sorted(run.glob("*.md")):
        title = next((l[2:].strip() for l in md_file.read_text(errors="replace").splitlines()
                      if l.startswith("# ")), None)
        if title:
            break
    new = next_id(reg, brand, kind)
    bid = key(new)
    reg["briefs"][bid] = {
        "id": bid, "brief": new, "type": kind, "brand": brand,
        "product": product_key(product or meta.get("product")),
        "avatar": avatar or meta.get("avatar"),
        "run": rel, "lane": lane,
        "title": title or run.name,
        "run_opened": meta.get("opened") or meta.get("generated_at"),
        "opened": date.today().isoformat(),
        "swipe": {},                        # the image lane's shape, so its readers
        "declares": {},                     # read a lane row without tripping
        "stages": [],
        "status": "for-review",
        "ads": [],
    }
    save(reg)
    add_alias(bid, new)
    stamp_run(run, new)
    return bid, reg["briefs"][bid]


def open_brief(run_name, brand, reg=None, product=None, avatar=None, kind=None):
    kind = check_type(kind)
    reg = reg or load()
    for bid, rec in reg["briefs"].items():
        if rec.get("run") == run_name:
            return bid, rec           # a run gets one id, for ever
    if kind == "email":
        return open_email(run_name, brand, reg, product, avatar)
    if kind == "page":
        return open_page(run_name, brand, reg, product, avatar)
    lane = _lane_run(run_name) if "/" in str(run_name) else None
    if lane is not None and lane.parts[-3] not in ("image-teardown", "video-teardown"):
        return open_lane(lane, brand, reg, product, avatar, kind)
    run = run_dir(run_name, brand)
    if kind in VIDEO_TYPES and not run.is_dir():
        # not an image-teardown run: a video-teardown brief
        return open_video(run_name, brand, reg, product, avatar, kind)
    if not run.is_dir():
        sys.exit(f"no run at {run}")

    src, stages, fields = read_run(run)
    if "06-brief.md" not in stages:
        sys.exit(f"{run_name} has no 06-brief.md — a brief id is for a "
                 f"finished brief, not a run in progress")

    new = next_id(reg, brand, kind)
    bid = key(new)                    # the register key stays the old code
    reg["briefs"][bid] = {
        "id": bid,
        "brief": new,
        "type": kind,
        "brand": brand,
        "product": product,
        "avatar": avatar,
        "run": run_name,
        "opened": date.today().isoformat(),
        "swipe": {"brand": src.get("swipe"), "block": src.get("block"),
                  "block_file": src.get("block_file"),
                  "clone": src.get("clone"), "variants": src.get("variants"),
                  "drive": src.get("drive"), "why": src.get("why")},
        "declares": fields,           # problem / angle / concept, as stage 6 wrote them
        "stages": sorted(stages),
        "status": "for-review",       # for-review -> approved -> in-production
        "ads": [],                    # ad names that carry this brief id
    }
    save(reg)
    add_alias(bid, new)
    # the filed record carries its number too, like every other lane's run.json
    rec_dir = RUNS / brand / Path(run_name).name
    if (rec_dir / "run.json").is_file():
        stamp_run(rec_dir, new)
    return bid, reg["briefs"][bid]


def set_links(reg, any_id, links):
    """Record the landing page(s) a brief sends people to, by catalog link id
    (`links`: a list of ids, kept in order, never duplicated). The hand-off
    reads them from here, so a clipper, creator or email hand-off needs no
    sidecar (2026-10-01). The id is checked against the catalog by the
    hand-off, not here — this file does not read the catalog."""
    k, rec = get(reg, any_id)
    if rec is None:
        sys.exit(f"no brief {any_id}")
    have = [x if isinstance(x, str) else (x or {}).get("id") for x in rec.get("links") or []]
    for l in links or []:
        if l and l not in have:
            have.append(l)
    rec["links"] = [x for x in have if x]
    return k, rec


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    o = sub.add_parser("open"); o.add_argument("run"); o.add_argument("--brand", required=True)
    o.add_argument("--product"); o.add_argument("--avatar")
    o.add_argument("--type", default=DEFAULT_TYPE, choices=TYPES)
    o.add_argument("--link", action="append", default=[],
                   help="catalog link id of the landing page this brief sends people to (repeatable)")
    lk = sub.add_parser("link"); lk.add_argument("id"); lk.add_argument("links", nargs="+")
    s = sub.add_parser("show"); s.add_argument("id")
    n = sub.add_parser("next"); n.add_argument("--brand", required=True)
    n.add_argument("--type", default=DEFAULT_TYPE, choices=TYPES)
    sub.add_parser("migrate")
    sub.add_parser("check")
    a = ap.parse_args()
    reg = load()

    if a.cmd == "list":
        for bid, r in sorted(reg["briefs"].items(), reverse=True):
            d = r.get("declares", {})
            # A reserved id has no run — it predates the register.
            run = r["run"] or "(before the register)"
            print(f"{N.brief_id(bid)}  {bid:<5} {r['opened']:<20} {r['brand']:<8} {r['status']:<13} "
                  f"{run:<34} angle={d.get('angle') or '—'}")
    elif a.cmd == "open":
        bid, rec = open_brief(a.run, a.brand, reg, a.product, a.avatar, a.type)
        if a.link:
            reg = load()
            bid, rec = set_links(reg, bid, a.link)
            save(reg)
        print(f"{rec.get('brief', N.brief_id(bid))}  ({bid})  {rec['run']}  ({rec['status']})")
    elif a.cmd == "show":
        k, rec = get(reg, a.id)
        print(json.dumps(rec or f"no brief {a.id}", indent=1))
    elif a.cmd == "next":
        print(next_id(reg, a.brand, a.type))
    elif a.cmd == "migrate":
        n = stamp(reg)
        if n:
            save(reg)
        print(f"{n} entries stamped with id + brief · {len(reg['briefs'])} briefs")
    elif a.cmd == "link":
        k, rec = set_links(reg, a.id, a.links)
        save(reg)
        print(f"{rec.get('brief', N.brief_id(k))}  links: {', '.join(rec['links'])}")
    elif a.cmd == "check":
        ok, probs, n = check(reg)
        for p in probs:
            print(f"  ! {p}")
        print(f"{n} briefs · {'all resolve under both spellings' if ok else f'{len(probs)} problems'}")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
