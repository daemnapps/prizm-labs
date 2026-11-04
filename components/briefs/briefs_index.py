#!/usr/bin/env python3
"""THE BRIEFS INDEX: one brief key in, every place its work sits out.

    python3 components/briefs/briefs_index.py                 rebuild runs/BRIEFS-INDEX.json + runs/BRIEFS.md
    python3 components/briefs/briefs_index.py find <key>      one brief's entry (any spelling of the key, or brief-NNNN --brand b)
    python3 components/briefs/backfill_brief_key.py [--apply] stamp `brief_key` into every run record the index can place

    import briefs_index as BI
    BI.find("acme_nova_brief-0076")  -> the entry, or None (acme_nova-face-brush_brief-0076 finds the same one)
    BI.build()                       -> the index dict (what BRIEFS-INDEX.json holds)
    BI.place_runs()                  -> [{station, brand, folder, key, how}] every run folder and the brief it is for

the owner, 2026-10-28 (components/naming/WHERE-EVERYTHING-GOES-owner.md, "What's confusing today" 2): one ad has a
different label at each station (`<swipe>-<brand>` at teardown, `<swipe>` at production) and only a
handful of run folders carry the brief number. The folders are NOT renamed (links and other sessions lean on them);
instead every run record carries `brief_key` and this one index joins them per brief.

Per brief key (`brand_<catalog product id>_brief-NNNN`, names.brief_key / catalog_key; every other spelling maps to the
same entry through `forms`): every station's run folder (repo path + the Drive label, the same words under Shared
Assets/), its hand-off folders with their returned files, and its Meta cards from runs/meta-upload/<brand>/ADS-INDEX.json.

How a run folder is placed, first that answers: (1) its run.json already says `brief_key`; (2) a hand-off folder's own
name; (3) the brief register's `run` / `brief_file` names this folder's label (also with or without a `-<brand>` tail);
(4) its run.json names a brief number (brief, brief_id) that the register gives to one brief of this brand; (5) the run
it was made from (writing_run, from_run, brief_from, lane_run, copied_from, the picture it edited) is placed. A label
the register gives to two briefs, or a number two briefs share, is left unplaced, never guessed.

Reads the repo only; writes only the two index files (and, in backfill, one line into run.json files). Spends nothing,
sends nothing, no key, no network. Repo-relative paths and "Shared Assets/..." labels only. Python 3.9.
"""
import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
STATIONS = ["video-teardown", "video-writing", "video-production", "video-edit",
            "image-teardown", "image-production", "image-edit", "handoffs", "meta-upload"]
SKIP_FILE = HERE / "briefs_index_skip.json"   # run folders left out while another session is making them (data, not code)
LINKS = ("writing_run", "from_run", "brief_from", "lane_run", "copied_from", "forked_from", "branched_from",
         "production_run", "production", "edit_run", "storyboard_from")
RUN_PATH = re.compile(r"(?:^|/)runs/([a-z0-9-]+)/([^/]+)/([^/]+)")
DRIVE = "Shared Assets/"

_N = None


def names(repo=None):
    """components/naming's names (public surface: brief_key, catalog_key, brief_key_forms, parse_brief_key,
    brief_number, slug)."""
    global _N
    if _N is None:
        f = Path(repo or REPO) / "components" / "naming" / "names.py"
        if str(f.parent) not in sys.path:
            sys.path.append(str(f.parent))
        spec = importlib.util.spec_from_file_location("briefs_index_names", f)
        _N = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_N)
    return _N


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def rel(p, repo):
    return Path(p).resolve().relative_to(Path(repo).resolve()).as_posix()


# ------------------------------------------------------------------------------------------------ the register

class Register:
    """The brief register (tools/image-teardown/briefs.json), read as data: each brief's ONE key — its `key`
    field, else its catalog form — and every spelling that lands on it."""

    def __init__(self, repo=None):
        self.repo = Path(repo or REPO)
        N = names(self.repo)
        raw = _read(self.repo / "tools" / "image-teardown" / "briefs.json") or {}
        self.rows = {k: r for k, r in (raw.get("briefs") or {}).items() if isinstance(r, dict)}
        want = {}
        for k, r in self.rows.items():
            if r.get("key"):
                want[k] = r["key"]
            elif N.parse_brief_key(k):
                want[k] = N.catalog_key(k)
            elif r.get("brand") and N.brief_number(r.get("brief") or k):
                want[k] = N.brief_key(r["brand"], r.get("product"), r.get("brief") or k)
        owners = {}
        for k, v in want.items():
            owners.setdefault(v, []).append(k)
        self.key, self.forms = {}, {}
        for k in self.rows:
            v = want.get(k)
            mine = owners.get(v) or []
            if len(mine) > 1:
                mine = [o for o in mine if N.parse_brief_key(o)]
            self.key[k] = v if v and mine == [k] else k        # a pNNN that would share a key keeps its own id
        for k, v in self.key.items():
            for f in [v, k] + N.brief_key_forms(v) + N.brief_key_forms(k):
                self.forms.setdefault(f.lower(), v)
        # label -> register keys, from `run` and `brief_file`
        self.by_label = {}
        for k, r in self.rows.items():
            labels = set()
            run = str(r.get("run") or "").rstrip("/")
            if run:
                labels.add(run.split("/")[-1])
            m = RUN_PATH.search(str(r.get("brief_file") or ""))
            if m:
                labels.add(m.group(3))
            for lab in labels:
                self.by_label.setdefault(lab.lower(), set()).add(k)

    def lookup(self, any_key):
        """The register key for any spelling of a brief key (or the register id), or None."""
        v = self.forms.get(str(any_key or "").strip().lower())
        if not hasattr(self, "_reg_of"):
            self._reg_of = {kk: k for k, kk in self.key.items()}
        return self._reg_of.get(v) if v else None

    def by_number(self, brand, number, product=None):
        N = names(self.repo)
        hits = [k for k, r in self.rows.items() if N.slug(r.get("brand") or "") == N.slug(brand or "")
                and N.brief_number(r.get("brief") or k) == number]
        if product and len(hits) > 1:
            pid = N.product_id(brand, product)
            same = [k for k in hits if N.product_id(brand, self.rows[k].get("product")) == pid]
            hits = same or hits
        return hits

    def for_label(self, label, brand):
        hits = set()
        label = str(label).lower()
        for lab in {label, re.sub(r"-" + re.escape(str(brand)) + r"$", "", label), f"{label}-{brand}"}:
            hits |= {k for k in self.by_label.get(lab, ()) if not brand or brand.startswith("_")
                     or self.rows[k].get("brand") in (None, brand)}
        return hits


# ------------------------------------------------------------------------------------------------ the run folders

def skipped(repo=None):
    """Repo-relative run folders to leave alone (briefs_index_skip.json `skip`; a trailing * matches a prefix)."""
    d = _read(SKIP_FILE) or {}
    return [str(x) for x in d.get("skip") or []]


def _skip(relpath, skip):
    return any(relpath == s or (s.endswith("*") and relpath.startswith(s[:-1])) for s in skip)


def run_folders(repo=None, skip=None):
    """Every run folder under the stations: (station, brand, folder). A hand-off folder sits one level deeper
    (runs/handoffs/<role>/<brand>/<brief key>/)."""
    repo = Path(repo or REPO)
    skip = skipped(repo) if skip is None else skip
    out = []
    for st in STATIONS:
        base = repo / "runs" / st
        if not base.is_dir():
            continue
        tops = ([d for d in base.iterdir() if d.is_dir() and not d.name.startswith(".")] if st == "handoffs" else [base])
        for top in tops:
            for b in sorted(d for d in top.iterdir() if d.is_dir() and not d.name.startswith(".")):
                for f in sorted(d for d in b.iterdir() if d.is_dir() and not d.name.startswith(".")):
                    if _skip(rel(f, repo), skip):
                        continue
                    out.append((st, b.name, f))
    return out


def records(folder):
    """The run records of one run folder: its run.json and those one level down (deliverable/, engine/ …)."""
    fs = [folder / "run.json"] + sorted(folder.glob("*/run.json"))
    return [f for f in fs if f.is_file()]


def _brief_numbers(d):
    out = []
    for f in ("brief", "brief_id"):
        v = d.get(f)
        if isinstance(v, str):
            out.append(v)
    nm = d.get("name")
    if isinstance(nm, dict) and isinstance(nm.get("brief"), str):
        out.append(nm["brief"])
    return out


def _linked(d, repo):
    """The run folders this record says it was made from, repo-relative ((station, brand, label) triples)."""
    vals = [d.get(k) for k in LINKS]
    req = d.get("request") if isinstance(d.get("request"), dict) else {}
    vals += [req.get("from_image"), d.get("kit")]
    out = []
    for v in vals:
        m = RUN_PATH.search(str(v or ""))
        if m and m.group(1) in STATIONS and m.group(1) != "handoffs":
            out.append((m.group(1), m.group(2), m.group(3)))
    return out


def place_runs(repo=None, reg=None):
    """Every run folder with the brief it is for: [{station, brand, folder, key, register, how, records}]; key None
    (with `why`) when nothing places it."""
    repo = Path(repo or REPO)
    reg = reg or Register(repo)
    N = names(repo)
    folders = run_folders(repo)
    index = {(st, b, f.name): f for st, b, f in folders}
    memo = {}

    def solve(st, b, f, depth=0):
        k = (st, b, f.name)
        if k in memo:
            return memo[k]
        memo[k] = (None, "a loop of made-from links", None)
        recs = [(p, _read(p)) for p in records(f)]
        recs = [(p, d) for p, d in recs if isinstance(d, dict)]
        got = None
        for _, d in recs:                                                    # 1 the record says so
            r = reg.lookup(d.get("brief_key")) if d.get("brief_key") else None
            if r:
                got = (r, "its run.json brief_key", None)
                break
        if not got and st == "handoffs":                                      # 2 a hand-off folder's own name
            r = reg.lookup(f.name)
            if not r and N.brief_number(f.name):
                m = re.match(re.escape(b) + r"[_-](.+?)[_-]brief", f.name.lower())
                hits = reg.by_number(b, N.brief_number(f.name), m.group(1) if m else None)
                r = hits[0] if len(hits) == 1 else None
            if r:
                got = (r, "the hand-off folder's name", None)
        if not got and st != "handoffs" and N.parse_brief_key(f.name):       # 2b a run labelled by its brief key
            r = reg.lookup(f.name)
            if r:
                got = (r, "the run folder's own name (its brief key)", None)
        if not got:                                                           # 3 the register names this label
            hits = reg.for_label(f.name, b)
            if len(hits) == 1:
                got = (next(iter(hits)), "the register's run label", None)
            elif len(hits) > 1:
                got = (None, None, f"the register gives this label to {len(hits)} briefs ({', '.join(sorted(hits)[:4])})")
        if not got or got[0] is None:
            for _, d in recs:                                                 # 4 a brief number in the record
                for num in _brief_numbers(d):
                    n = N.brief_number(num)
                    hits = reg.by_number(d.get("brand") or b, n) if n else []
                    # the number counts only where the register agrees: the brief names this label, or no run at all
                    # (video runs carry numbers the register later gave to other briefs; 2026-10-28 audit)
                    lab = reg.for_label(f.name, b)
                    ok = [h for h in hits if h in lab or not reg.rows[h].get("run")]
                    if hits and not ok:
                        got = (None, None, f"its run.json says {num}, but the register gives {num} to run "
                                           f"{', '.join(sorted(str(reg.rows[h].get('run')) for h in hits))}")
                        continue
                    hits = ok
                    if len(hits) == 1:
                        got = (hits[0], f"its run.json says {num}", None)
                        break
                    if len(hits) > 1:
                        got = (None, None, f"{num} names {len(hits)} briefs of this brand")
                if got and got[0]:
                    break
        if (not got or got[0] is None) and depth < 6:                          # 5 the run it was made from
            for _, d in recs:
                for lst, lb, ll in _linked(d, repo):
                    pf = index.get((lst, lb, ll))
                    if pf is None or (lst, lb, ll) == k:
                        continue
                    r, how, _ = solve(lst, lb, pf, depth + 1)
                    if r:
                        got = (r, f"made from runs/{lst}/{lb}/{ll} ({how})", None)
                        break
                if got and got[0]:
                    break
        memo[k] = got or (None, None, "nothing names its brief (no register label, no brief number, no made-from run)")
        return memo[k]

    out = []
    for st, b, f in folders:
        r, how, why = solve(st, b, f)
        claims = []
        for p in records(f):
            d = _read(p)
            if isinstance(d, dict):
                claims += [{"record": rel(p, repo), "says": c, "brand": d.get("brand") or b} for c in _brief_numbers(d)]
        out.append({"station": st, "brand": b, "folder": rel(f, repo), "register": r,
                    "key": reg.key.get(r) if r else None, "how": how, "why": why,
                    "records": [rel(p, repo) for p in records(f)], "claims": claims})
    return out


def _handoff_names_run(repo, reg, key, folder):
    """The hand-off folder(s) of this brief that name this run folder (its repo path) in their own record — the second
    witness that makes a correction clear. -> [repo-relative hand-off folder]."""
    N = names(repo)
    forms = set([key] + N.brief_key_forms(key))
    hit = []
    for d in (Path(repo) / "runs" / "handoffs").glob("*/*/*"):
        if d.is_dir() and d.name in forms:
            for fn in ("manifest.json", "handoff.json", "run.json"):
                f = d / fn
                try:
                    if f.is_file() and folder in f.read_text():
                        hit.append(rel(d, repo))
                        break
                except OSError:
                    continue
    return hit


def collisions(placed, reg, repo=None):
    """Every run whose own run.json `brief` disagrees with the register: [{folder, record, says, register_gives,
    placed, how, clear, handoffs}]. `clear` = the register placed the run by its label, its own name or its brief key
    (never by the number it claims) AND a hand-off folder of that brief names this run — then `correct()` may fix it."""
    repo = Path(repo or REPO)
    N = names(repo)
    out = []
    for p in placed:
        label = p["folder"].split("/")[-1]
        for c in p.get("claims") or []:
            n = N.brief_number(c["says"])
            if not n:
                continue
            gives = [{"key": reg.key[h], "run": reg.rows[h].get("run")} for h in reg.by_number(c["brand"], n)]
            if p["key"]:
                if N.brief_number(reg.rows[p["register"]].get("brief") or p["register"]) == n:
                    continue
            elif not gives or any(h in reg.for_label(label, p["brand"]) for h in reg.by_number(c["brand"], n)):
                continue
            ho = _handoff_names_run(repo, reg, p["key"], p["folder"]) if p["key"] else []
            clear = bool(p["key"] and ho and p["how"] and "says" not in p["how"])
            out.append({"folder": p["folder"], "record": c["record"], "says": c["says"], "register_gives": gives,
                        "placed": p["key"], "how": p["how"], "clear": clear, "handoffs": ho})
    return out


# ------------------------------------------------------------------------------------------------ the index

def _returned(folder):
    back = folder / "returned"
    if not back.is_dir():
        return []
    return sorted(p.relative_to(back).as_posix() for p in back.rglob("*")
                  if p.is_file() and not p.name.startswith(".") and p.name not in ("README.md", "index.json"))


def _meta(repo):
    """register key or brief-key spelling -> the brief's ADS-INDEX row, per brand."""
    out = []
    for f in sorted((Path(repo) / "runs" / "meta-upload").glob("*/ADS-INDEX.json")):
        d = _read(f) or {}
        for row in d.get("briefs") or []:
            if isinstance(row, dict):
                out.append((rel(f, repo), row))
    return out


def build(repo=None):
    """The index: {built, what, forms: {any spelling: key}, briefs: {key: entry}, unplaced: {station: n}, old_names}."""
    repo = Path(repo or REPO)
    reg = Register(repo)
    placed = place_runs(repo, reg)
    briefs = {}
    for k, r in reg.rows.items():
        key = reg.key[k]
        briefs[key] = {"key": key, "register_id": k, "forms": sorted({f for f, v in reg.forms.items() if v == key}),
                       "brief": r.get("brief"), "brand": r.get("brand"), "product": r.get("product_id") or r.get("product"),
                       "type": r.get("type"), "title": r.get("title"), "state": r.get("state") or r.get("status"),
                       "runs": [], "handoffs": [], "meta": []}
    unplaced, old_names = {}, []
    for p in placed:
        if not p["key"]:
            unplaced[p["station"]] = unplaced.get(p["station"], 0) + 1
            continue
        e = briefs[p["key"]]
        row = {"station": p["station"], "folder": p["folder"], "drive": DRIVE + p["folder"], "how": p["how"]}
        if p["station"] == "handoffs":
            f = repo / p["folder"]
            row.update({"role": f.parent.parent.name, "returned": _returned(f),
                        "returned_to": DRIVE + p["folder"] + "/returned",
                        "delivery": rel(f / "delivery.json", repo) if (f / "delivery.json").is_file() else None})
            e["handoffs"].append(row)
            if f.name != p["key"]:
                old_names.append({"folder": p["folder"], "named": f.name, "catalog_form": p["key"]})
        else:
            e["runs"].append(row)
    for src, row in _meta(repo):
        k = next((reg.lookup(x) for x in [row.get("brief")] + list(row.get("register") or []) + list(row.get("names") or [])
                  if x and reg.lookup(x)), None)
        if k:
            briefs[reg.key[k]]["meta"].append({"ads_index": src, "state": row.get("state"), "lanes": row.get("lanes"),
                                               "meta_ad_ids": row.get("meta_ad_ids") or [],
                                               "cards": [{"state": c.get("state"), "ad_name": c.get("ad_name"),
                                                          "folder": c.get("folder"), "live": c.get("live")}
                                                         for c in row.get("cards") or [] if isinstance(c, dict)]})
    forms = {f: v for f, v in sorted(reg.forms.items())}
    clash = collisions(placed, reg, repo)
    return {"what": "every brief key -> every station's run folder (repo path + Drive label), its hand-off folders and "
                    "returned files, its Meta cards. Any spelling of a key finds its entry through `forms`.",
            "built": datetime.now().isoformat(timespec="seconds"), "via": "components/briefs/briefs_index.py",
            "read_with": "components/briefs/briefs_index.py find <key>",
            "counts": {"briefs": len(briefs), "with_runs": sum(1 for e in briefs.values() if e["runs"]),
                       "runs_placed": sum(1 for p in placed if p["key"]), "runs_unplaced": sum(unplaced.values())},
            "unplaced": unplaced, "old_names": old_names,
            "collisions": clash, "forms": forms, "briefs": briefs}


def markdown(ix):
    L = ["# Briefs — every station's run, per brief", "",
         f"Built {ix['built']} by `{ix['via']}`. The machine copy is `runs/BRIEFS-INDEX.json` (`find <key>` reads it; "
         "every spelling of a key, `brand_nova_brief-NNNN` or `brand_<catalog id>_brief-NNNN`, lands on one entry). "
         "Each folder is on the Drive at the same path under `Shared Assets/`.", "",
         f"{ix['counts']['briefs']} briefs · {ix['counts']['with_runs']} with run folders · "
         f"{ix['counts']['runs_placed']} run folders placed · {ix['counts']['runs_unplaced']} not placed "
         f"({', '.join(f'{k} {v}' for k, v in sorted(ix['unplaced'].items())) or 'none'}).", ""]
    if ix["old_names"]:
        L += ["## Hand-off folders under an older spelling (kept, never renamed)", "", "| Folder | Catalog form |", "|---|---|"]
        L += [f"| `{o['folder']}` | `{o['catalog_form']}` |" for o in ix["old_names"]]
        L += [""]
    if ix.get("collisions"):
        L += ["## Runs whose own brief number disagrees with the register", "",
              "`clear` = the register places the run by its label or name AND a hand-off of that brief names the run: "
              "`backfill_brief_key.py --fix-briefs --apply` corrects it (old value kept as `brief_was`). The rest are "
              "for the owner.", "", "| Run | Says | Register gives that number to | Placed as | Clear |", "|---|---|---|---|---|"]
        for c in ix["collisions"]:
            gives = "<br>".join(f"`{g['key']}` (run {g['run']})" for g in c["register_gives"]) or "nothing"
            L.append(f"| `{c['folder']}` | {c['says']} | {gives} | `{c['placed'] or '—'}` | "
                     f"{'yes — ' + ', '.join(c['handoffs']) if c['clear'] else 'no: for the owner'} |")
        L += [""]
    L += ["## Briefs with work on disk", "", "| Brief key | Title | Runs | Hand-off | Returned | Meta |", "|---|---|---|---|---|---|"]
    for k, e in sorted(ix["briefs"].items(), key=lambda kv: (kv[1]["brand"] or "", kv[0])):
        if not (e["runs"] or e["handoffs"] or e["meta"]):
            continue
        runs = "<br>".join(f"{r['station']}: `{r['folder'].split('/')[-1]}`" for r in e["runs"]) or "—"
        ho = "<br>".join(f"`{h['folder']}`" for h in e["handoffs"]) or "—"
        back = sum(len(h["returned"]) for h in e["handoffs"])
        meta = ", ".join(sorted({m["state"] or "?" for m in e["meta"]})) or "—"
        title = str(e.get("title") or "").replace("|", "/")[:60]
        L.append(f"| `{k}` | {title} | {runs} | {ho} | {back or '—'} | {meta} |")
    return "\n".join(L) + "\n"


def write(repo=None, ix=None):
    repo = Path(repo or REPO)
    ix = ix or build(repo)
    j, m = repo / "runs" / "BRIEFS-INDEX.json", repo / "runs" / "BRIEFS.md"
    j.write_text(json.dumps(ix, indent=1, ensure_ascii=False) + "\n")
    m.write_text(markdown(ix))
    return {"json": rel(j, repo), "md": rel(m, repo)}


def find(any_key, brand=None, repo=None, ix=None):
    """One brief's entry by any spelling of its key, its register id, or brief-NNNN with a brand; None when it is not
    there or a number names two briefs."""
    repo = Path(repo or REPO)
    ix = ix or _read(repo / "runs" / "BRIEFS-INDEX.json") or build(repo)
    k = ix["forms"].get(str(any_key or "").strip().lower())
    if k:
        return ix["briefs"].get(k)
    N = names(repo)
    n = N.brief_number(any_key)
    if n and brand:
        hits = [e for e in ix["briefs"].values() if e["brand"] == brand and N.brief_number(e["brief"]) == n]
        return hits[0] if len(hits) == 1 else None
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", nargs="?", default="build", choices=["build", "find"])
    ap.add_argument("key", nargs="?")
    ap.add_argument("--brand")
    a = ap.parse_args(argv)
    if a.cmd == "find":
        e = find(a.key, a.brand)
        print(json.dumps(e, indent=1, ensure_ascii=False) if e else f"no brief {a.key} in runs/BRIEFS-INDEX.json")
        return 0 if e else 1
    ix = build()
    w = write(ix=ix)
    c = ix["counts"]
    print(f"{w['json']} + {w['md']}: {c['briefs']} briefs, {c['runs_placed']} run folders placed, {c['runs_unplaced']} not")
    return 0


if __name__ == "__main__":
    sys.exit(main())
