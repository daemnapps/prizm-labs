#!/usr/bin/env python3
"""handoff <role> <brand> <briefs | batch> — one hand-off folder, checked, or a refusal.

    handoff.py <role> <brand> brief-0140 brief-0141 [--catalog PATH] [--staging DIR]
    handoff.py ad-uploader <brand> batch-2026-09-23-a --offline
    handoff.py take-back <role> <brand> <hand-off name>

The Hand-off Standard (components/handoff-standard/HANDOFF-STANDARD.md,
decision 19) in one tool. Every time work leaves the machine for a role it
goes as `<role>-handoff_<brand>_<date>/` — always the same shape, one
instruction file the receiver's own tool can read, whether the receiver is
an agent or a person:

    handoff.md      the instructions (8 sections, always the same 8)
    manifest.json   every id inside, every check, every file in assets/
    briefs/         brief.md + brief.json per piece
    assets/         the actual files they work from or upload — the ad
                    pictures, the edit kit, the email html and images —
                    copied in, plus index.json naming each one
    references/     the product / offer / link records from the catalog
    returned/       their finished work (empty until it comes back)

The folder is written at `<staging>/<role>/<brand>/<name>/` — no other level.

The process is the standard's: GATHER by id → CHECK every product, offer and
link id against the catalog → WRITE handoff.md + manifest.json + assets →
COPY to Drive at `Shared Assets/handoffs/<role>/<brand>/<name>/` through the
local Drive mount (the path is recorded in manifest.json; `--no-drive` skips
it) → a LEDGER record → TAKE BACK `returned/` + the live ids.

Ads are listed by their 29 Sep short-form names (`names.short_unit`,
`names.short_meta`: brand_product_brief_batch_funnel, one Meta ad name per
landing page, the funnel being the link id's page part) with the old 13-part
name beside each — live ads keep their old names on Meta.

**A refusal is the answer.** A brief with an id the catalog does not know, a
brief the register does not know, an ad whose name does not parse, a role
input that is missing — each is named with its reason and NO folder is
written. This is the check that stops wrong links and wrong products before
they reach anyone (the clipper briefs of 2026-09).

The Drive step is a COPY into the mounted shared drive, never more: it never
changes sharing, never deletes, never overwrites a folder already there.
Nothing here talks to Meta, Klaviyo or a store, and nothing here reads a key.

Reused, not rebuilt: `components/naming/names.py` (ids, both spellings, the
name parser), `components/brandpath` (the brand's folders), the brief register
(`tools/image-teardown/tools/briefs.py`), and `components/ad-handoff`'s
`links()` / `resolves()` for a drop's landing pages.
"""
import argparse, csv, importlib.util, json, re, shutil, subprocess, sys
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def repo(start=None):
    """The workspace root, found by walking up — never counted."""
    here = Path(start or __file__).resolve()
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise SystemExit("no workspace root above this file")


WS = repo()
# The brief register's tools: image teardown graduated to components/ on
# 2026-10-01; a checkout that has not pulled the move still has the lab copy.
IT_TOOLS = next((WS / p for p in ("tools/image-teardown/tools", "lab/image-teardown/tools")
                 if (WS / p / "briefs.py").is_file()), WS / "tools/image-teardown/tools")
IT_REGISTER = str((IT_TOOLS.parent / "briefs.json").relative_to(WS))
for p in ("components/naming", "components/brandpath"):
    sys.path.insert(0, str(WS / p))
sys.path.insert(0, str(IT_TOOLS))
import names as N                     # noqa: E402
from brandpath import brand_path      # noqa: E402
import briefs as BR                   # noqa: E402


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AD_HANDOFF = _load_module("ad_handoff_gate", WS / "components/ad-handoff/handoff.py")
_TB = _load_module("ad_handoff_take_back", WS / "components/ad-handoff/take_back.py")

ROLES = json.loads((HERE / "roles.json").read_text())["roles"]
NEEDS_WORDS = json.loads((HERE / "roles.json").read_text())["needs_words"]
DEFAULT_CATALOG = WS / "lab/catalog/data/catalog.json"
DEFAULT_STAGING = WS / "runs/handoffs"
DRIVE_ROOT = "Shared Assets/handoffs"
# the shared drive as the Drive app mounts it on this Mac; `Shared Assets/…` paths live under it
DRIVE_MOUNT = Path.home() / "Library/CloudStorage/GoogleDrive-<account>/Shared drives/Shared Assets"
SKIP_FILES = {".DS_Store"}
DROPS = WS / "runs/image-edit"
SCHEMA = "handoff/1"

KIND_PREFIX = {
    "product": ("product", "bundle", "variant"),
    "offer": ("offer",),
    "link": ("link", "placement"),
    "part": ("deal", "guarantee", "shipping", "gift", "deadline"),
}
DEAD_STATUS = {"retired"}
NOT_LIVE_STATUS = {"not-live", "draft", "hidden", "paused"}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


Refused = _TB.Refused  # one class with ad-handoff's take_back, so `except Refused` catches both


# ---- the catalog --------------------------------------------------------
class Catalog:
    """Every id the brand's catalog knows, from either shape the catalog
    takes today:

    A. `catalog.json` — one file, `brands.<brand>.{products, bundles, parts,
       offers[].ids, placements[].id, old_names}` (the 25 Sep survey the
       catalog tool refreshes);
    B. one JSON file per record (offer-system-design.md §C): a folder walked
       for `*.json`, or a single file holding a list / `{"records": [...]}`,
       each record `{id, type, brand, status, ...}`.

    `resolve(value, kind)` answers with the catalog id or None — an exact id,
    `<kind>_<brand>_<slug>`, or an old spelling the catalog lists."""

    def __init__(self, path, brand):
        self.path, self.brand = Path(path), brand
        self.records, self.old = {}, {}
        self.shape = None
        if not self.path.exists():
            raise Refused([f"catalog not found at {self.path} — pass --catalog"])
        if self.path.is_dir():
            self.shape = "B"
            for f in sorted(self.path.rglob("*.json")):
                try:
                    self._take(json.loads(f.read_text()))
                except (OSError, json.JSONDecodeError):
                    continue
        else:
            data = json.loads(self.path.read_text())
            if isinstance(data, dict) and "brands" in data:
                self.shape = "A"
                self._take_survey(data["brands"].get(brand) or {})
            else:
                self.shape = "B"
                self._take(data)
        if not self.records:
            raise Refused([f"catalog at {self.path} holds no records for this brand"])

    def _add(self, rec):
        rid = rec.get("id")
        if not rid or not isinstance(rid, str):
            return
        rec_brand = rec.get("brand") or (rid.split("_", 2)[1] if rid.count("_") >= 2 else None)
        if rec_brand != self.brand:
            return
        self.records[rid] = rec
        for old in rec.get("old_names") or []:
            self.old.setdefault(str(old).strip().lower(), rid)

    def _take(self, data):
        if isinstance(data, list):
            for r in data:
                if isinstance(r, dict):
                    self._add(r)
        elif isinstance(data, dict):
            if "records" in data and isinstance(data["records"], list):
                self._take(data["records"])
            elif "id" in data:
                self._add(data)

    def _take_survey(self, b):
        # the catalog tool (28 Sep) writes every record under `records`, keyed by id
        recs = b.get("records")
        if isinstance(recs, dict):
            for rid, r in recs.items():
                if isinstance(r, dict):
                    self._add(dict(r, id=r.get("id") or rid, brand=r.get("brand") or self.brand))
        for layer in ("products", "bundles", "parts", "placements"):
            for r in b.get(layer) or []:
                if isinstance(r, dict):
                    self._add(dict(r, brand=self.brand))
        for o in b.get("offers") or []:
            for oid in o.get("ids") or []:
                self._add(dict(o, id=oid, type="offer", brand=self.brand))
        for row in b.get("old_names") or []:
            # rows are {"old": …, "new": …} or [old names joined by " · ", kind, new id]
            if isinstance(row, (list, tuple)):
                row = {"old": row[0] if row else "", "new": row[-1] if len(row) > 1 else None}
            if not isinstance(row, dict):
                continue
            new = row.get("new")
            if not new:
                continue
            for old in re.split(r"\s*·\s*", str(row.get("old", ""))):
                if old:
                    self.old.setdefault(old.strip().lower(), new)

    def _kind_ok(self, rid, kind):
        return rid.split("_", 1)[0] in KIND_PREFIX[kind]

    def resolve(self, value, kind):
        if value is None:
            return None
        v = str(value).strip()
        if not v or v.lower() in ("not-recorded", "none", "null"):
            return None
        if v in self.records and self._kind_ok(v, kind):
            return v
        for prefix in KIND_PREFIX[kind]:
            cand = f"{prefix}_{self.brand}_{N.slug(v)}"
            if cand in self.records:
                return cand
        hit = self.old.get(v.lower())
        if hit and hit in self.records and self._kind_ok(hit, kind):
            return hit
        return None

    def status(self, rid):
        return str(self.records.get(rid, {}).get("status") or "").lower()

    def url(self, rid):
        r = self.records.get(rid, {})
        return r.get("url") or r.get("working_url") or None


# ---- gather -------------------------------------------------------------
def is_batch(token):
    t = str(token).strip()
    return bool(N.BATCH_OLD.match(t) or N.BATCH_NEW.match(t))


def batch_forms(token):
    """Both spellings of a batch: the folder name today is the old one."""
    new = N.norm_batch(token)
    m = N.BATCH_NEW.match(new or "")
    old = f"{m.group(1)[2:]}{m.group(2)}{m.group(3)}{m.group(4)}" if m else str(token)
    return {new, old, str(token)}


def drop_dirs(brand, batch=None):
    root = DROPS / brand
    if not root.is_dir():
        return []
    dirs = sorted(d / "deliverable" for d in root.iterdir() if (d / "deliverable").is_dir())
    if batch:
        forms = batch_forms(batch)
        dirs = [d for d in dirs if d.parent.name in forms]
    return dirs


def ads_for(brand, wanted_briefs=None, batch=None):
    """Every ad folder in the brand's drops whose manifest names one of the
    briefs (either spelling) — with its pictures, its copy row and the drop's
    landing pages. `wanted_briefs=None` with a batch takes the whole drop."""
    out = []
    for d in drop_dirs(brand, batch):
        rows = {r.get("ad_name"): r for r in AD_HANDOFF.copy_rows(d)}
        links = AD_HANDOFF.links(d)
        for folder in AD_HANDOFF.ad_folders(d):
            mf = folder / "manifest.json"
            if not mf.is_file():
                continue
            try:
                m = json.loads(mf.read_text())
            except json.JSONDecodeError:
                continue
            bid = N.brief_id(m.get("brief"))
            if wanted_briefs is not None and bid not in wanted_briefs:
                continue
            parsed = N.parse_any(folder.name)
            # the pictures are named by the ad's own manifest — the record. Whether
            # each one is on Drive with bytes is the ad-handoff gate's check (its #2),
            # made through the Drive API; the local mount is never trusted for it.
            named = [x.get("file") for x in (m.get("ads") or []) if isinstance(x, dict) and x.get("file")]
            local = sorted(p.name for p in folder.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".mp4"))
            out.append({
                "brief_id": bid,
                "ad_name": folder.name,
                "unit": (parsed or {}).get("ad_name"),
                "parses": parsed is not None,
                "drop": d.parent.name,
                "batch_id": N.norm_batch(d.parent.name),
                "folder": str(folder.relative_to(WS)),
                "pictures": named or local,
                "pictures_local": local,
                "copy": rows.get(folder.name),
                "links": links,
                "product": m.get("product"),
            })
    return out


def run_folder(rec, brand):
    """The brief's run, whatever lane made it (2026-10-01): a repo path
    (email, page, any lane run), a video-teardown run by name, else an
    image-teardown run by name."""
    r = rec.get("run")
    if not r:
        return None
    if "/" in str(r) and (WS / r).is_dir():
        return WS / r
    if rec.get("lane") == "video-teardown" or rec.get("type") in BR.VIDEO_TYPES:
        v = BR.video_run(r, brand)
        if v.is_dir():
            return v
    return BR.run_dir(rec, brand)


def brief_file(rec, brand):
    """The brief itself — from the run folder first, then the brand's briefs
    folder (through brandpath). Found, never assumed."""
    tries = [WS / rec["brief_file"]] if rec.get("brief_file") else []   # the register names it (page runs)
    run = run_folder(rec, brand)
    if run:
        tries += [run / "deliverable" / "06-brief.md", run / "06-brief.md", run / "brief.md",
                  run / "deliverable" / "brief.md",
                  # email (stage 9) and page (stage 6) runs write their brief under its stage name
                  run / "deliverable" / "stage9--brief.md", run / "stage9--brief.md",
                  run / "deliverable" / "stage6--brief.md", run / "stage6--brief.md"]
        # a lane run that named its brief (`run03-ai-brief.md`): the one in deliverable/, else beside run.json
        tries += sorted(run.glob("deliverable/*brief.md")) + sorted(run.glob("*brief.md"))
    for bid in sorted(N.brief_forms(rec.get("brief") or rec.get("id"))):
        tries += [brand_path(brand, "briefs", bid, "brief.md"), brand_path(brand, "briefs", f"{bid}.md")]
    return next((t for t in tries if t.is_file()), None)


def stage_files(rec, brand):
    run = run_folder(rec, brand)
    if not run or not run.is_dir():
        return []
    files = sorted(p for p in run.glob("*.md")) + sorted(p for p in (run / "deliverable").glob("*") if (run / "deliverable").is_dir() and p.suffix in (".md", ".json"))
    return [p for p in files if p.is_file()]


def gather(role, brand, which, ids_file=None, kit=None, email_run=None):
    """Every brief by id, its file, its ads and the ids it declares."""
    problems = []
    reg = BR.load()
    sidecar = json.loads(Path(ids_file).read_text()) if ids_file else {}
    tokens = [t.strip() for t in which if t and t.strip()]
    batch = next((t for t in tokens if is_batch(t)), None)
    brief_tokens = [t for t in tokens if not is_batch(t)]
    if batch and not drop_dirs(brand, batch):
        problems.append(f"batch {N.norm_batch(batch)} — no drop at runs/image-edit/{brand}/<batch>/deliverable")
    batch_ads = ads_for(brand, None, batch) if batch else []
    # (id, product): numbers count per brand AND product (the owner, 2026-10-01), so
    # a bare number two products share needs the product — a per-product key
    # (brand_product_brief-NNNN) or the product on the batch's own ads.
    brief_ids = []
    for t in brief_tokens:
        q = N.parse_brief_key(t)
        bid = q[2] if q else N.brief_id(t)
        if not N.is_brief_id(bid):
            problems.append(f"{t} — not a brief id or a batch id")
            continue
        brief_ids.append((bid, q[1] if q else None))
    for a in batch_ads:
        if a["brief_id"] and not any(a["brief_id"] == b and (p is None or p == a.get("product"))
                                     for b, p in brief_ids):
            brief_ids.append((a["brief_id"], a.get("product")))
    if not brief_ids and not problems:
        problems.append("nothing to hand off — name at least one brief id or a batch id")

    briefs = []
    for bid, want_product in brief_ids:
        try:
            key, rec = BR.get(reg, bid, brand, want_product)
        except N.AmbiguousBrief as e:
            problems.append(str(e))
            continue
        if rec is None:
            problems.append(f"{bid} — unknown brief: not in the brief register")
            continue
        if rec.get("brand") and rec["brand"] != brand:
            problems.append(f"{bid} — belongs to another brand's register entry, not {brand}")
            continue
        declares = rec.get("declares") or {}
        side = {**(sidecar.get("*") or {}), **(sidecar.get(bid) or sidecar.get(key) or {})}
        ads = [a for a in batch_ads if a["brief_id"] == bid] if batch else ads_for(brand, {bid})
        if N.parse_brief_key(key):
            # a per-product brief: only the ads of its own product share its number
            ads = [a for a in ads if not a.get("product") or N.slug(a["product"]) == N.slug(rec.get("product") or "")]
        f = brief_file(rec, brand)
        b = {
            "id": bid,
            "old_code": key,
            "brand": brand,
            "status": rec.get("status"),
            "opened": rec.get("opened"),
            "run": rec.get("run"),
            "avatar": rec.get("avatar") or declares.get("avatar"),
            "product": side.get("product") or rec.get("product") or declares.get("product")
                       or next((a["product"] for a in ads if a.get("product")), None),
            "offers": _listed(side.get("offer") or side.get("offers") or rec.get("offer") or declares.get("offer")),
            # the brief's own landing page (page_pick, chosen when the brief was
            # written) is the default; --ids still overrides it
            "links": _links(side.get("links") or rec.get("links")
                            or (rec.get("landing_page") or {}).get("link_ids") or declares.get("links"), ads,
                            "link" in ROLES[role]["needs"]),
            "parts": _listed(side.get("parts") or rec.get("parts")),
            "brief_file": str(f.relative_to(WS)) if f else None,
            "stage_files": [str(p.relative_to(WS)) for p in stage_files(rec, brand)],
            "ads": ads,
            "register": f"{IT_REGISTER}#{key}",
        }
        briefs.append(b)

    extra = {}
    if kit:
        k = Path(kit)
        extra["kit"] = str(k) if k.is_dir() else None
        if not k.is_dir():
            problems.append(f"edit kit not found at {kit}")
    if email_run:
        e = Path(email_run)
        extra["email_run"] = str(e) if e.is_dir() else None
        if not e.is_dir():
            problems.append(f"email run not found at {email_run}")
        # the email's own links (its button) are its landing pages: carried by URL,
        # named by the catalog in check() — a URL the catalog lacks is refused by name
        ej = e / "deliverable" / "email.json"
        if ej.is_file() and "link" in ROLES[role]["needs"]:
            urls = sorted(set(re.findall(r'https?://[^"\s<>)]+', ej.read_text())))
            for b in briefs:
                have = {_norm_url(r.get("url")) for r in b["links"]}
                b["links"] += [{"id": None, "url": u, "label": f"email link {u}"} for u in urls if _norm_url(u) not in have]
    return {"role": role, "brand": brand, "batch": N.norm_batch(batch) if batch else None,
            "briefs": briefs, "extra": extra, "problems": problems}


def _listed(v):
    if not v:
        return []
    if isinstance(v, str):
        return [x.strip() for x in re.split(r"[,\s]+", v) if x.strip() and x.strip().lower() != "not-recorded"]
    return [str(x).strip() for x in v if str(x).strip()]


def _links(declared, ads, with_drop_links):
    """Links as `{id, url, label}` rows: from the brief / sidecar first. For a
    role that needs a link, the drop's own links.json (label → url) is added
    too: a label whose URL a declared link already carries takes that id; a
    label nobody named by id stays id-less, and the check refuses it — a URL
    with no link id cannot be traced to the catalog."""
    rows = []
    for x in declared or []:
        if isinstance(x, dict):
            rows.append({"id": x.get("id"), "url": x.get("url"), "label": x.get("label")})
        elif isinstance(x, str):
            rows.append({"id": x, "url": None, "label": None})
    if not with_drop_links:
        return rows
    by_url = {_norm_url(r["url"]): r for r in rows if r.get("url")}
    for a in ads:
        for label, url in (a.get("links") or {}).items():
            hit = by_url.get(_norm_url(url))
            if hit:
                hit["label"] = hit.get("label") or label
                continue
            rows.append({"id": None, "url": url, "label": label})
            by_url[_norm_url(url)] = rows[-1]
    return rows


def _norm_url(u):
    return str(u or "").strip().rstrip("/").lower()


def _catalog_link(cat, url):
    """The catalog link id whose URL a drop's link carries (2026-10-01): a drop
    writes its pages by URL, the catalog knows them by id. Exact URL first;
    else the one link on the same page path (a funnel that moved host, e.g.
    the netlify preview to its own domain, is still the same page). None when
    nothing, or more than one, matches — then the check still refuses it."""
    from urllib.parse import urlparse
    want = _norm_url(url)
    links = {k: _norm_url(cat.url(k)) for k in cat.records if cat._kind_ok(k, "link") and cat.url(k)}
    hit = [k for k, u in links.items() if u == want]
    if not hit:
        path = lambda u: urlparse(u).path.rstrip("/").removesuffix(".html").removesuffix("/index")
        hit = [k for k, u in links.items() if path(u) and path(u) == path(want)]
    return hit[0] if len(hit) == 1 else None


# ---- check --------------------------------------------------------------
def check(g, cat, online=True):
    """Every id against the catalog, every role input present, every name
    parsing. Returns (checks, resolved) and raises Refused with every reason."""
    role = ROLES[g["role"]]
    problems = list(g["problems"])
    checks = []
    resolved = {"products": {}, "offers": {}, "links": {}, "parts": {}}

    def ok(name, detail):
        checks.append({"check": name, "result": "ok", "detail": detail})

    def bad(name, detail):
        checks.append({"check": name, "result": "refused", "detail": detail})
        problems.append(detail)

    def note(name, detail):
        checks.append({"check": name, "result": "not checked", "detail": detail})

    for b in g["briefs"]:
        bid = b["id"]
        # product
        pid = cat.resolve(b["product"], "product")
        if b["product"] and not pid:
            bad("product in catalog", f"{bid} — product '{b['product']}' is not in the catalog")
        elif pid:
            resolved["products"][pid] = cat.records[pid]
            b["product_id"] = pid
            ok("product in catalog", f"{bid} → {pid}")
            if cat.status(pid) in DEAD_STATUS:
                bad("product live", f"{bid} — {pid} is {cat.status(pid)}")
        elif "product" in role["needs"]:
            bad("product in catalog", f"{bid} — no product recorded on the brief ({NEEDS_WORDS['product']})")
        # offers
        b["offer_ids"] = []
        for o in b["offers"]:
            oid = cat.resolve(o, "offer")
            if not oid:
                bad("offer in catalog", f"{bid} — offer '{o}' is not in the catalog")
                continue
            b["offer_ids"].append(oid)
            resolved["offers"][oid] = cat.records[oid]
            ok("offer in catalog", f"{bid} → {oid}")
            st = cat.status(oid)
            if st in DEAD_STATUS or (role["publish"] and st in NOT_LIVE_STATUS):
                bad("offer live", f"{bid} — {oid} is {st}; a {g['role']} hand-off needs a live offer")
        # parts
        b["part_ids"] = []
        for p in b["parts"]:
            pid_ = cat.resolve(p, "part")
            if not pid_:
                bad("part in catalog", f"{bid} — part '{p}' is not in the catalog")
                continue
            b["part_ids"].append(pid_)
            resolved["parts"][pid_] = cat.records[pid_]
            ok("part in catalog", f"{bid} → {pid_}")
        # links
        b["link_ids"] = []
        for row in b["links"]:
            if not row.get("id") and row.get("url"):
                row["id"] = _catalog_link(cat, row["url"])     # the drop's URL, named by the catalog
        unnamed = [row.get("label") or row.get("url") for row in b["links"] if not row.get("id")]
        if unnamed:
            bad("link in catalog", f"{bid} — landing page(s) with no link id: {', '.join(map(str, unnamed))} — every link is named by its catalog id (give them with --ids)")
        for row in b["links"]:
            if not row.get("id"):
                continue
            if row.get("id"):
                lid = cat.resolve(row["id"], "link")
                if not lid:
                    bad("link in catalog", f"{bid} — link '{row['id']}' is not in the catalog")
                    continue
                row["id"] = lid
                row["url"] = row.get("url") or cat.url(lid)
                b["link_ids"].append(lid)
                resolved["links"][lid] = dict(cat.records[lid], url=row["url"], label=row.get("label"))
                ok("link in catalog", f"{bid} → {lid}")
            if row.get("url"):
                if online:
                    status, why = AD_HANDOFF.resolves(row["url"])
                    if status == 200:
                        ok("link answers", f"{row['url']} → 200")
                    else:
                        bad("link answers", f"{bid} — {row['url']} answers {status} {why}".strip())
                else:
                    note("link answers", f"{row['url']} — offline, not fetched")
        if "link" in role["needs"] and not b["link_ids"]:
            bad("link present", f"{bid} — {NEEDS_WORDS['link']}")
        # the brief itself
        if "brief_file" in role["needs"]:
            if b["brief_file"]:
                ok("brief file", f"{bid} → {b['brief_file']}")
            else:
                bad("brief file", f"{bid} — {NEEDS_WORDS['brief_file']} — none found")
        # the ads
        if "ads" in role["needs"]:
            if not b["ads"]:
                bad("ads present", f"{bid} — {NEEDS_WORDS['ads']} — none in runs/image-edit/{g['brand']}")
            for a in b["ads"]:
                if not a["parses"]:
                    bad("ad name parses", f"{a['ad_name']} — does not parse to the naming standard")
                if not a["pictures"]:
                    bad("ad has pictures", f"{a['ad_name']} — its manifest names no picture")
                else:
                    note("pictures on Drive", f"{a['ad_name']} — {len(a['pictures'])} named; bytes on Drive are the ad-handoff gate's check")
        if "copy" in role["needs"]:
            for a in b["ads"]:
                if a["copy"] is None:
                    bad("ad has copy", f"{a['ad_name']} — no copy row")
            if b["ads"] and all(a["copy"] is not None for a in b["ads"]):
                ok("ad has copy", f"{bid} — {len(b['ads'])} ad(s), every one with a copy row")
        for a in b["ads"]:
            if a["parses"]:
                ok("ad name parses", a["ad_name"])
    if "kit" in role["needs"] and not g["extra"].get("kit"):
        bad("edit kit", NEEDS_WORDS["kit"] + " — none given")
    if "email_run" in role["needs"] and not g["extra"].get("email_run"):
        bad("email run", NEEDS_WORDS["email_run"] + " — none given")
    if problems:
        raise Refused(problems)
    return checks, resolved


# ---- assets: the actual files, copied in ----------------------------------
def media_roots():
    """Where a file named by its repo path is found, in order: this checkout;
    the main checkout (a worktree carries the records, but git keeps no media,
    so the pictures and clips sit only in the checkout that made them); the
    Drive mirror (`Shared Assets/<same path>`)."""
    roots = [WS]
    try:
        common = subprocess.run(["git", "-C", str(WS), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                capture_output=True, text=True, check=True).stdout.strip()
        main = Path(common).parent
        if common and main.resolve() != WS.resolve() and main.is_dir():
            roots.append(main)
    except (OSError, subprocess.CalledProcessError):
        pass
    if Path(DRIVE_MOUNT).is_dir():
        roots.append(Path(DRIVE_MOUNT))
    return roots


def _rel(p):
    """A path as the repo names it (relative), or the absolute path if it lives elsewhere."""
    p = Path(p)
    if not p.is_absolute():
        return p
    for r in media_roots():
        try:
            return p.resolve().relative_to(r.resolve())
        except ValueError:
            continue
    return p


def find_file(path):
    rel = _rel(path)
    cands = [rel] if rel.is_absolute() else [r / rel for r in media_roots()]
    return next((c for c in cands if c.is_file()), None)


def tree_files(folder):
    """Every file under a folder, across the roots — the first root that has a
    file wins, so records come from this checkout and media from wherever it is."""
    rel = _rel(folder)
    srcs = [rel] if rel.is_absolute() else [r / rel for r in media_roots()]
    out = {}
    for src in srcs:
        if not src.is_dir():
            continue
        for f in sorted(src.rglob("*")):
            if f.is_file() and f.name not in SKIP_FILES:
                out.setdefault(f.relative_to(src), f)
    return out


def funnel_of(link_id):
    """The page part of a short Meta ad name. Each launch to a page is its own ad.

    The live ads name it `<funnel id>-<page>` (`…_body-scrub-cpk-quiz`,
    `…_body-scrub-cpk-offer`), the funnel id from brands/<brand>/web/funnels/
    funnels.json — made in ONE place, components/naming/page_pick.meta_page,
    which the card uploader reaches through here too (2 Oct 2026). A link the
    catalog or the funnel list does not know keeps the old spelling: the link
    id's page part (`link_<brand>_cpk_quiz` → `cpk-quiz`)."""
    try:
        import page_pick as PP
        named = PP.meta_page(link_id)
        if named:
            return named
    except Exception:                       # noqa: BLE001 — the old spelling is always there
        pass
    rest = link_id.split("_", 2)[2] if link_id.count("_") >= 2 else link_id
    return N.slug(rest.replace("_", "-"))


def plan_assets(g):
    """Every file assets/ will hold, as (path inside assets/, source file), and
    every ad's short-form names. Refuses, naming each one, when a file the
    hand-off lists cannot be found."""
    plan, missing = [], []
    for b in g["briefs"]:
        pid = b.get("product_id") or ""
        product = pid.split("_", 2)[2] if pid.count("_") >= 2 else None
        for a in b["ads"]:
            unit = None
            if product and a.get("batch_id"):
                try:
                    unit = N.short_unit(g["brand"], product, b["id"], a["batch_id"])
                except ValueError:
                    unit = None
            if not unit:
                missing.append(f"{a['ad_name']} — no short-form name (product {product or 'not recorded'}, batch {a.get('batch_id') or 'not recorded'})")
                continue
            a["short"] = unit
            a["meta_names"] = [{"link_id": lid, "meta_ad_name": N.short_meta(unit, funnel_of(lid))} for lid in b["link_ids"]]
            a["files"] = []
            for i, pic in enumerate(a["pictures"], 1):
                n = (N.parse_any(pic) or {}).get("asset_n") or i
                dest = f"ads/{unit}/{N.short_file(unit, n)}{Path(pic).suffix.lower()}"
                src = find_file(Path(a["folder"]) / pic)
                if not src:
                    missing.append(f"{a['ad_name']} — picture {pic} not found here, in the main checkout or on Drive")
                    continue
                plan.append((dest, src))
                a["files"].append({"file": f"assets/{dest}", "was": pic})
    kit = g["extra"].get("kit")
    if kit:
        files = tree_files(kit)
        if not files:
            missing.append(f"edit kit {kit} — no files in it")
        plan += [(f"kit/{r}", s) for r, s in files.items()]
    er = g["extra"].get("email_run")
    if er:
        n0 = len(plan)
        for sub in ("deliverable", "media"):
            plan += [(f"email/{sub}/{r}", s) for r, s in tree_files(Path(er) / sub).items()]
        if len(plan) == n0:
            missing.append(f"email run {er} — no deliverable/ or media/ files in it")
    if missing:
        raise Refused(missing)
    return plan


# ---- write --------------------------------------------------------------
def drive_dest(role, brand, name, mount=None):
    return Path(mount or DRIVE_MOUNT) / "handoffs" / role / brand / name


# A video-editor hand-off that carries ONE brief is a queue item: the owner assigns it
# to the editor straight from the Drive, so its folder is named by the brief's
# short form, brand_product_brief (components/naming CONVENTION.md; the batch joins
# at delivery). the owner, 2026-10-09: "we don't have a clear naming convention that
# makes sense for this queue".
QUEUE_ROLES = ("video-editor",)


def queue_base(g):
    bs = g.get("briefs") or []
    if g.get("role") not in QUEUE_ROLES or len(bs) != 1:
        return None
    b = bs[0]
    prefix = f"product_{g['brand']}_"
    pid = b.get("product_id") or ""
    if not (pid.startswith(prefix) and re.match(r"^brief-\d{4}$", b.get("id") or "")):
        return None
    return f"{g['brand']}_{pid[len(prefix):]}_{b['id']}"


def handoff_name(role, brand, when, staging, drive=False, base=None):
    base = base or f"{role}-handoff_{brand}_{when}"
    root = Path(staging) / role / brand
    name, n = base, 1
    while (root / name).exists() or (drive and drive_dest(role, brand, name).exists()):
        n += 1
        name = f"{base}-{n}"
    return name


def render_md(g, name, target, checks, resolved, drive_written=False):
    role = ROLES[g["role"]]
    L = []
    L.append(f"# {name}")
    L.append("")
    L.append(f"*{role['title']} hand-off · {g['brand']} · {date.today().isoformat()} · {SCHEMA}*")
    L.append("")
    L.append("## 1 What this is")
    L.append(f"A {role['title'].lower()} hand-off: {role['inside']}. Job types: {', '.join(role['job_types'])}. "
             f"It comes from {role['comes_from']}. Every id inside was checked against the catalog before this folder was written.")
    L.append("")
    L.append("## 2 Who it's for")
    L.append(f"The **{g['role']}** — an agent first; a person can take this same folder and do the same job, because the folder is the instruction. "
             f"Told: {role['told']}. Hands back: {role['comes_back']}.")
    L.append("")
    L.append("## 3 What's inside (by id)")
    L.append("| brief | product | offer | links | brief file | ads |")
    L.append("|---|---|---|---|---|---|")
    for b in g["briefs"]:
        L.append(f"| `{b['id']}` (was `{b['old_code']}`) | `{b.get('product_id') or '—'}` | "
                 f"{', '.join(f'`{o}`' for o in b['offer_ids']) or '—'} | {', '.join(f'`{l}`' for l in b['link_ids']) or '—'} | "
                 f"{'briefs/' + b['id'] + '/brief.md' if b['brief_file'] else '—'} | {len(b['ads'])} |")
    if g.get("batch"):
        L.append("")
        L.append(f"Batch: `{g['batch']}`.")
    ads = [a for b in g["briefs"] for a in b["ads"]]
    if ads:
        L.append("")
        L.append("### The ads, by their short name")
        L.append("Each ad goes up under its Meta ad name — one per landing page. The old name is beside it: "
                 "an ad already live on Meta keeps its old name there.")
        L.append("")
        L.append("| ad (short name) | Meta ad name, per page | pictures in assets/ | old name |")
        L.append("|---|---|---|---|")
        for a in ads:
            metas = "<br>".join(f"`{m['meta_ad_name']}`" for m in a.get("meta_names") or []) or "—"
            L.append(f"| `{a.get('short') or '—'}` | {metas} | {len(a.get('files') or [])} in `assets/ads/{a.get('short')}/` | `{a['ad_name']}` |")
    files = g.get("asset_files") or []
    L.append("")
    if files:
        tops = {}
        for f in files:
            top = f.split("/", 1)[0]
            tops[top] = tops.get(top, 0) + 1
        L.append("**In assets/:** " + " · ".join(f"`{t}/` {n} file(s)" for t, n in sorted(tops.items()))
                 + " — the actual files, copied in. `assets/index.json` names each one.")
    else:
        L.append("**In assets/:** nothing to work from beyond the brief — `assets/index.json` says so.")
    L.append("")
    L.append("## 4 What to do")
    if role["tools"]:
        L.append("Tools: " + " · ".join(role["tools"]))
        L.append("")
    for i, s in enumerate(role["steps"], 1):
        L.append(f"{i}. {s}")
    L.append("")
    L.append("## 5 What must not change")
    L.append("- **Product** — only the products in section 3, as the catalog records them (references/products.json). No other product appears.")
    L.append("- **Words** — the exact words in each brief (headline, offer bar, claims). Not rephrased, not shortened, not translated.")
    L.append("- **Offer** — only the offers in section 3, at the price and wording the catalog records (references/offers.json). No invented discount, no code.")
    L.append("- **Link** — only the links in section 6, by id. Nothing appended to a URL, no shortener.")
    L.append("- **Names** — every returned file carries its brief id and asset id; an ad name is never edited.")
    L.append("")
    L.append("## 6 Links (link id + working URL)")
    if resolved["links"]:
        L.append("| link id | URL | used by |")
        L.append("|---|---|---|")
        for lid, r in resolved["links"].items():
            used = ", ".join(b["id"] for b in g["briefs"] if lid in b["link_ids"])
            L.append(f"| `{lid}` | {r.get('url') or 'URL not on file'} | {used} |")
    else:
        L.append("No landing page in this hand-off.")
    L.append("")
    L.append("## 7 Checks before you're done")
    L.append("Before this folder was written:")
    L.append("")
    L.append("| check | result | detail |")
    L.append("|---|---|---|")
    for c in checks:
        L.append(f"| {c['check']} | {c['result']} | {c['detail']} |")
    L.append("")
    L.append("Before you send it back:")
    for i, r in enumerate(role["returned"], 1):
        L.append(f"{i}. `returned/{r.split(' — ')[0]}` — {r.split(' — ', 1)[1] if ' — ' in r else ''}".rstrip(" —"))
    L.append(f"{len(role['returned']) + 1}. Every file in returned/ carries its brief id and asset id.")
    L.append(f"{len(role['returned']) + 2}. You stopped at: **{role['stops_at']}**. Nothing goes live without the owner's go.")
    L.append("")
    L.append("## 8 How to send it back")
    L.append(f"Put finished work in `returned/` of this folder — on Drive at `{target}/returned/` "
             f"({'this folder is on Drive there' if drive_written else 'the folder is staged locally; the Drive copy is the next step'}). "
             f"Then `handoff take-back {g['role']} {g['brand']} {name}` reads it, joins every file to its brief and asset id, "
             f"records the live ids, and writes the ledger record. Nothing in returned/ is published by that step.")
    L.append("")
    return "\n".join(L)


def write(g, cat, checks, resolved, staging, when=None, plan=None, drive=False):
    """Write the folder at <staging>/<role>/<brand>/<name>/ with its files, and
    — with `drive` — copy it to Shared Assets/handoffs/<role>/<brand>/<name>/
    through the mount. Drive is checked before anything is written; a copy
    never overwrites and never deletes."""
    plan = plan or []
    when = when or date.today().isoformat()
    mount = Path(DRIVE_MOUNT)
    if drive and not mount.is_dir():
        raise Refused([f"Drive is not mounted at {mount} — open Google Drive, or run with --no-drive"])
    name = handoff_name(g["role"], g["brand"], when, staging, drive=drive, base=queue_base(g))
    target = f"{DRIVE_ROOT}/{g['role']}/{g['brand']}/{name}"
    root = Path(staging) / g["role"] / g["brand"] / name
    for sub in ("briefs", "assets", "references", "returned"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    for dest, src in plan:
        d = root / "assets" / dest
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, d)
    g["asset_files"] = sorted(dest for dest, _ in plan)

    assets_index = []
    for b in g["briefs"]:
        bdir = root / "briefs" / b["id"]
        bdir.mkdir(exist_ok=True)
        if b["brief_file"]:
            shutil.copy2(WS / b["brief_file"], bdir / "brief.md")
        for rel in b["stage_files"]:
            src = WS / rel
            if src.name != Path(b["brief_file"] or "").name:
                shutil.copy2(src, bdir / src.name)
        (bdir / "brief.json").write_text(json.dumps({k: v for k, v in b.items() if k != "ads"}, indent=1, ensure_ascii=False) + "\n")
        for a in b["ads"]:
            assets_index.append({
                "brief_id": b["id"], "ad_name": a.get("short"), "old_name": a["ad_name"], "batch_id": a["batch_id"],
                "meta_ad_names": a.get("meta_names") or [],
                "files": a.get("files") or [],
                "source": a["folder"],
                "source_drive": f"Shared Assets/runs/image-edit/{g['brand']}/{a['drop']}/deliverable/{a['ad_name']}",
                "copy": a["copy"],
            })
    (root / "assets" / "index.json").write_text(json.dumps({
        "_what": "the actual files the receiver works from or uploads, copied into this folder. Ads are named by the 29 Sep short form; old_name is the 13-part name a live ad keeps on Meta.",
        "files": [f"assets/{f}" for f in g["asset_files"]],
        "ads": assets_index,
        "kit": {"source": g["extra"]["kit"], "here": "assets/kit/"} if g["extra"].get("kit") else None,
        "email_run": {"source": g["extra"]["email_run"], "here": "assets/email/"} if g["extra"].get("email_run") else None,
    }, indent=1, ensure_ascii=False) + "\n")
    for layer in ("products", "offers", "links", "parts"):
        (root / "references" / f"{layer}.json").write_text(json.dumps(resolved[layer], indent=1, ensure_ascii=False) + "\n")
    (root / "returned" / "README.md").write_text(
        f"# returned/\n\nWhat comes back from the {g['role']}:\n\n" +
        "\n".join(f"- {r}" for r in ROLES[g["role"]]["returned"]) +
        "\n\nEvery file carries its brief id and asset id. Nothing here is live.\n")

    manifest = {
        "schema": SCHEMA, "name": name, "role": g["role"], "brand": g["brand"], "date": when,
        "batch": g.get("batch"),
        "briefs": [{k: b[k] for k in ("id", "old_code", "status", "product_id", "offer_ids", "link_ids", "part_ids", "brief_file")
                    if k in b} | {"ads": [{"ad_name": a.get("short"), "old_name": a["ad_name"],
                                           "meta_ad_names": [m["meta_ad_name"] for m in a.get("meta_names") or []]}
                                          for a in b["ads"]]} for b in g["briefs"]],
        "ids": {layer: sorted(resolved[layer]) for layer in ("products", "offers", "links", "parts")},
        "assets": [f"assets/{f}" for f in g["asset_files"]],
        "catalog": {"path": str(cat.path.relative_to(WS)) if cat.path.is_relative_to(WS) else str(cat.path), "shape": cat.shape},
        "checks": checks,
        "checks_passed": all(c["result"] != "refused" for c in checks),
        "drive": {"target": target, "written": False},
        "returned": {"expected": ROLES[g["role"]]["returned"], "received": []},
        "stops_at": ROLES[g["role"]]["stops_at"],
        "created": now(), "via": "components/handoff-standard/skill/handoff.py",
    }

    def put(written):
        (root / "handoff.md").write_text(render_md(g, name, target, checks, resolved, written))
        (root / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")

    if not drive:
        put(False)
        return root, manifest
    dest = drive_dest(g["role"], g["brand"], name, mount)
    manifest["drive"] = {"target": target, "written": True, "path": f"{target}/",
                         "mount": str(dest), "copied": now()}
    put(True)
    try:
        (mount / "handoffs").mkdir(exist_ok=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(root, dest, symlinks=False, ignore=shutil.ignore_patterns(*SKIP_FILES))
    except OSError as e:
        manifest["drive"] = {"target": target, "written": False, "error": str(e)}
        put(False)
        raise Refused([f"Drive copy failed ({e}) — the folder is written locally at {root}; nothing on Drive was removed"])
    return root, manifest


# ---- ledger -------------------------------------------------------------
def ledger_write(path, event, manifest=None, role=None, brand=None, reasons=None, extra=None):
    """One append-only line per event. Same envelope as the creative record
    (schema, kind, item, verdict, created, via); the item is the hand-off name."""
    row = {
        "schema": SCHEMA, "kind": "handoff",
        "item": (manifest or {}).get("name"),
        "role": role or (manifest or {}).get("role"),
        "brand": brand or (manifest or {}).get("brand"),
        "verdict": {"event": event},
        "briefs": [b["id"] for b in (manifest or {}).get("briefs", [])],
        "ids": (manifest or {}).get("ids"),
        "target": ((manifest or {}).get("drive") or {}).get("target"),
        "created": now(), "via": "components/handoff-standard/skill/handoff.py",
    }
    if reasons:
        row["verdict"]["reasons"] = reasons
    if extra:
        row.update(extra)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


# ---- take back ----------------------------------------------------------
LIVE_PREFIX = {"meta": "live_meta_", "klaviyo": "live_klaviyo_", "sms": "live_sms_"}


# moved to components/ad-handoff/take_back.py (SI-143 (take-back home)); one function, one ledger row shape
take_back = _TB.take_back


# ---- the command --------------------------------------------------------
def run(role, brand, which, catalog=None, staging=None, ledger=None, ids_file=None, kit=None,
        email_run=None, online=True, when=None, drive=False):
    """`drive=True` copies the finished folder to Drive (the command line does
    this by default; `--no-drive` skips it). Called from code, it is off."""
    if role not in ROLES:
        raise Refused([f"unknown role '{role}' — one of: {', '.join(ROLES)}"])
    staging = Path(staging or DEFAULT_STAGING)
    ledger = Path(ledger or staging / "ledger.jsonl")
    cat = Catalog(catalog or DEFAULT_CATALOG, brand)
    g = gather(role, brand, which, ids_file=ids_file, kit=kit, email_run=email_run)
    try:
        checks, resolved = check(g, cat, online=online)
        plan = plan_assets(g)
        root, manifest = write(g, cat, checks, resolved, staging, when=when, plan=plan, drive=drive)
    except Refused as e:
        ledger_write(ledger, "refused", role=role, brand=brand, reasons=e.reasons,
                     extra={"briefs": [b["id"] for b in g["briefs"]], "asked": list(which)})
        raise
    ledger_write(ledger, "sent", manifest, extra={"drive_written": manifest["drive"]["written"],
                                                  "asked": list(which), "assets": len(manifest["assets"])})
    return root, manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("role", help="take-back, or one of: " + ", ".join(ROLES))
    ap.add_argument("brand")
    ap.add_argument("which", nargs="+", help="brief ids (either spelling) and/or one batch id; for take-back: the hand-off name")
    ap.add_argument("--catalog", help=f"the catalog: catalog.json or a folder of records (default {DEFAULT_CATALOG.relative_to(WS)})")
    ap.add_argument("--staging", help=f"where the folder is written locally (default {DEFAULT_STAGING.relative_to(WS)})")
    ap.add_argument("--ledger", help="the ledger file, one JSON line per event (default <staging>/ledger.jsonl)")
    ap.add_argument("--ids", help="a JSON sidecar: brief id → {product, offers, links:[{id,url}], parts} for what the brief record does not carry yet")
    ap.add_argument("--kit", help="video-editor: the edit kit folder")
    ap.add_argument("--email-run", help="klaviyo-uploader: the finished email run folder")
    ap.add_argument("--offline", action="store_true", help="do not fetch links (recorded as not checked)")
    ap.add_argument("--date", help="the date in the hand-off name (default today)")
    ap.add_argument("--no-drive", action="store_true", help="write the folder locally only; skip the copy to Shared Assets/handoffs/")
    a = ap.parse_args(argv)
    try:
        if a.role == "take-back":
            # handoff.py take-back <role> <brand> <hand-off name>
            if len(a.which) < 2:
                raise Refused(["take-back needs: take-back <role> <brand> <hand-off name>"])
            role, brand, name = a.brand, a.which[0], a.which[-1]
            if role not in ROLES:
                raise Refused([f"unknown role '{role}' — one of: {', '.join(ROLES)}"])
            staging = Path(a.staging or DEFAULT_STAGING)
            idx = take_back(role, brand, name, staging, Path(a.ledger or staging / "ledger.jsonl"))
            print(f"TAKEN BACK {name}: {len(idx['files'])} file(s), {len([l for l in idx['live_ids'] if l.get('live_id')])} live id(s)")
            return 0
        root, manifest = run(a.role, a.brand, a.which, catalog=a.catalog, staging=a.staging, ledger=a.ledger,
                             ids_file=a.ids, kit=a.kit, email_run=a.email_run, online=not a.offline, when=a.date,
                             drive=not a.no_drive)
    except Refused as e:
        print("REFUSED — nothing written:")
        for r in e.reasons:
            print(f"  - {r}")
        return 1
    print(f"READY {manifest['name']}")
    print(f"  folder  {root}")
    print(f"  drive   {manifest['drive']['target']}  ({'copied' if manifest['drive']['written'] else 'not copied — --no-drive'})")
    print(f"  assets  {len(manifest['assets'])} file(s)")
    print(f"  briefs  {', '.join(b['id'] for b in manifest['briefs'])}")
    print(f"  ids     " + ", ".join(f"{k} {len(v)}" for k, v in manifest["ids"].items()))
    print(f"  stops   {manifest['stops_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
