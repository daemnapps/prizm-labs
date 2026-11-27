#!/usr/bin/env python3
"""score: give every ad an origin, and join ad results back to the prompt versions that wrote each ad and the winners
each run borrowed from.

Normally driven by `winners.py score`, which reads results from the warehouse (trailing --days), falling back to
the newest media-buying file when the warehouse can't be reached. Directly, offline, from that file only:
    score.py --brand <brand> [--asof YYYY-MM-DD] [--root REPO]

Read-only on its inputs. Reads:
  the warehouse (audit.warehouse_ads), or runs/media-buying/<brand>/filter/<asof>/verdicts.json   per-ad results
  components/image-teardown/briefs.json                   the brief register (brief key -> run path or run label)
  runs/video-writing/<brand>/*/run.json, runs/video-teardown/<brand>/*/run.json, and each run's stages/4b-hooks.md
  runs/winners/<brand>/bank.json and each audit window's merges.json     the banked creatives
  runs/*/<brand>/<run>/    prompt records of a run in another lane: run.json and the `prompt:` header on its stage files
Writes:
  runs/winners/<brand>/score/<asof>/score.json and score.md

Join: Meta ad name -> names.parse_short (brand, product, brief-NNNN) -> brief key
<brand>_<product-id>_brief-NNNN -> register entry (by its map key or its own `key` field) -> its `run`, a repo path or
a bare run label, else a run.json whose brief_key / brief matches -> hook-stage prompt (stage4b) and brief-stage
prompt (stage5). A run has several hooks and one ad, so an ad lists every winner id its run's BORROWED_FROM lines cite.

Origin, the first that holds, for every ad:
  chain                        brief -> run -> hook or brief prompt version
  banked                       the ad's id is in a bank row, or its name reaches one through the audit's own merging rules
  brief, made outside writing  the name carries a brief, old spellings included, with no writing run behind it
  pre-system                   everything else
`matched` holds the chain ads and `unmatched` all the others, each with its origin and family.
Exit 2 on bad input.
"""
import argparse, datetime as dt, glob, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402

DEFAULT_ROOT = paths.repo(__file__)
PROMPT_RE = re.compile(r"^(?P<fam>.+?)-v(?P<v>\d+)(?:-.*)?\.md$")
RUN_LANES = ("video-writing", "video-teardown")
BORROWED_RE = re.compile(r"BORROWED_FROM\s+V\d+\s*:\s*([^\s·]+)")
P_NUMBER_RE = re.compile(r"(?:^|[-_\s])p(\d{3})(?=$|[-_\s])", re.I)    # the old brief code inside an older ad name
PROMPT_HEADER_RE = re.compile(r"\bprompt:\s*([^\s|]+\.md)")             # first line of a stage file a run wrote
ORIGINS = ("chain", "banked", "brief, made outside writing", "pre-system")
CANT_TRACE_OVER = 500


class BadInput(Exception):
    pass


def load_json(p):
    p = Path(p)
    if not p.is_file():
        raise BadInput(f"missing input file: {p}")
    try:
        return json.loads(p.read_text())
    except ValueError as e:
        raise BadInput(f"not valid JSON: {p} ({e})")


def load_names(root):
    sys.path.insert(0, str(Path(root) / "components" / "naming"))
    try:
        import names  # noqa: WPS433
    except Exception as e:  # the convention module is required: no guessing
        raise BadInput(f"cannot load components/naming/names.py ({e})")
    return names


def prompt_version(stage):
    """(family, version) from a run stage. v2 runs record version=2 for every pass, so the name wins."""
    if not isinstance(stage, dict):
        return None, None
    name = stage.get("prompt_name") or (Path(stage["prompt_file"]).name if stage.get("prompt_file") else None)
    if not name:
        return None, None
    m = PROMPT_RE.match(name)
    if m:
        return m["fam"], int(m["v"])
    v = stage.get("version")
    return name, v if isinstance(v, int) else None


def label(fam, ver):
    if fam is None:
        return "(none recorded)"
    return f"{fam} v{ver}" if ver is not None else fam


def index_runs(root, brand, product_id):
    """All run.json for the brand -> (by_path, by_key). Key = <brand>_<product-id>_<brief-NNNN>."""
    by_path, by_key = {}, {}
    for lane in RUN_LANES:
        for f in sorted(glob.glob(str(Path(root) / "runs" / lane / brand / "*" / "run.json"))):
            try:
                d = json.loads(Path(f).read_text())
            except ValueError:
                continue
            if not isinstance(d, dict) or not isinstance(d.get("stages"), dict):
                continue
            rel = str(Path(f).parent.relative_to(root))
            d["_rel"] = rel
            by_path[rel] = d
            keys = set()
            if d.get("brief_key"):
                keys.add(d["brief_key"])
            if d.get("brief") and d.get("product"):
                keys.add(f"{brand}_{product_id(d['product'])}_{d['brief']}")
            for k in keys:
                by_key.setdefault(k, []).append(d)
    return by_path, by_key


def pick_run(cands):
    """Prefer runs carrying both prompts, then either, then latest opened."""
    def score(d):
        s = d["stages"]
        return (bool(prompt_version(s.get("stage4b"))[0]) + bool(prompt_version(s.get("stage5"))[0]),
                str(d.get("opened") or ""))
    return max(cands, key=score)


def latest_asof(root, brand):
    ds = sorted(p.name for p in (Path(root) / "runs" / "media-buying" / brand / "filter").glob("*")
                if (p / "verdicts.json").is_file())
    if not ds:
        raise BadInput(f"no verdicts.json under runs/media-buying/{brand}/filter/")
    return ds[-1]


def register_index(register):
    """Every name an entry answers to: its map key (a catalog id, an old store handle, or a bare p-number)
    and its own `key` field."""
    out = dict(register)
    for v in register.values():
        if isinstance(v, dict) and v.get("key"):
            out.setdefault(v["key"], v)
    return out


def register_run(reg, brand, by_path):
    """The run record a register entry names, with how: (run, how) or None. `run` is a repo path on the newer
    entries and a bare run label on the older ones; one label can sit in both lanes."""
    r = (reg or {}).get("run")
    if not r:
        return None
    if r in by_path:
        return by_path[r], "register run path"
    cands = [by_path[x] for x in (f"runs/{lane}/{brand}/{r}" for lane in RUN_LANES) if x in by_path]
    return (pick_run(cands), "register run label") if cands else None


def cited(root, run):
    """Every winner id the run's hook stage cites, in order, or ["none"]."""
    f = Path(root) / run / "stages" / "4b-hooks.md"
    found = []
    if f.is_file():
        for m in BORROWED_RE.finditer(f.read_text(errors="ignore")):
            i = m.group(1).strip("`*")
            if i.lower() != "none" and i not in found:
                found.append(i)
    return found or ["none"]


def sums(rs):
    """Ads, spend, purchases, CPA and ROAS of a set of ad rows."""
    sp = round(sum(r["spend"] for r in rs), 2)
    pu = sum(r["purchases"] for r in rs)
    rev = sum((r["roas"] or 0) * r["spend"] for r in rs)
    return {"ads": len(rs), "spend": sp, "purchases": pu,
            "cpa": round(sp / pu, 2) if pu else None,
            "roas": round(rev / sp, 2) if sp else None}


def rollup(rows, field):
    g = {}
    for r in rows:
        g.setdefault(r[field], []).append(r)
    return sorted(({"version": k, **sums(rs)} for k, rs in g.items()), key=lambda x: -x["spend"])


# ---------- origin: what stands behind an ad ----------

def load_winners_rules():
    sys.path.insert(0, str(HERE))
    import audit as A
    import bank as B
    return A, B


class BankIndex:
    """A brand's bank rows by ad id and by the name each answers to under audit.base(), audit.script_key() and the
    merges.json of the window the row came from."""

    def __init__(self, root, brand):
        self.A, B = load_winners_rules()
        self.by_id, self.by_window = {}, {}
        here = B.brand_dir(root, brand)
        bank = B.load_bank(B.bank_path(root, brand), brand)
        for row in bank["rows"]:
            for i in row.get("ad_ids") or []:
                self.by_id.setdefault(str(i), row)
            for folder in {s.get("audit") for s in row.get("snapshots") or [] if s.get("kind") == "audit"}:
                if folder not in self.by_window:
                    f = here / str(folder) / "merges.json"
                    self.by_window[folder] = (load_json(f) if f.is_file() else {}, {})
                merges, keys = self.by_window[folder]
                for n in [row.get("name")] + list(row.get("ad_names") or []):
                    keys.setdefault(self.key(n, merges), row)

    def key(self, name, merges):
        k = self.A.script_key(self.A.base(name))
        while k in merges:
            k = merges[k]
        return k

    def find(self, ad_id, ad_name):
        row = self.by_id.get(str(ad_id))
        if row:
            return row
        for merges, keys in self.by_window.values():
            row = keys.get(self.key(ad_name, merges))
            if row:
                return row
        return None


def read_brief(names, name):
    """What an ad name says about its brief -> dict(brand, product, brief, as_named, old), or None. Any full form
    through the naming module, the copy marks off when the whole name doesn't read; then a bare p-number inside an
    older name, which says nothing about brand or product."""
    A, _ = load_winners_rules()
    for s in (name, A.base(name)):
        p = names.parse_any(s)
        if p and (p.get("brief") or "none") != "none" and names.is_brief_id(p["brief"]):
            old = p.get("form") == "old"
            return {"brand": p["brand"], "product": p["product"], "brief": names.brief_id(p["brief"]),
                    "as_named": p["brief"] if old else p.get("brief_as_named"), "old": old}
    m = P_NUMBER_RE.search(A.base(name))
    if m:
        return {"brand": None, "product": None, "brief": names.brief_id(int(m.group(1))),
                "as_named": "p" + m.group(1), "old": True}
    return None


def old_register_entry(names, register, brand, product, brief):
    """The register entry for an old-spelled brief: under its p-number when that entry is this brand's, else the one
    entry of this brand with this number (and this product, when the name gives one). -> (entry or None, whether the
    p-number is another brand's). Two candidates and no product: no entry, never a guess."""
    hit = register.get(names.brief_code(brief))
    if isinstance(hit, dict) and hit.get("brand") in (brand, None):
        return hit, False
    seen, cands = set(), []
    for v in register.values():
        if isinstance(v, dict) and id(v) not in seen and v.get("brand") == brand and v.get("brief") == brief:
            seen.add(id(v))
            if product is None or v.get("product_id") == product or v.get("product") == product:
                cands.append(v)
    return (cands[0] if len(cands) == 1 else None), isinstance(hit, dict) and not cands


def run_folders(root, brand, reg):
    """The folders a register entry's `run` names: a repo path, or a bare label that can sit in several lanes."""
    r = (reg or {}).get("run")
    if not r:
        return []
    root = Path(root)
    if str(r).startswith("runs/"):
        return [root / r] if (root / r).is_dir() else []
    return sorted(p for p in list((root / "runs").glob(f"*/{brand}/{r}")) + list((root / "runs").glob(f"*/_hand/{r}"))
                  if p.is_dir())


def prompts_in(root, folder, hops=2):
    """Every prompt file name a run folder records: its run.json (stages, `prompt`, the runs it was made from) and the
    `prompt:` header its stage files open with. Rendered temp copies (`_prompt-*`) are not prompts."""
    names, folder = set(), Path(folder)
    d = None
    if (folder / "run.json").is_file():
        try:
            d = json.loads((folder / "run.json").read_text())
        except ValueError:
            d = None
    if isinstance(d, dict):
        stages = d.get("stages") if isinstance(d.get("stages"), dict) else {}
        for s in stages.values():
            if isinstance(s, dict) and (s.get("prompt_name") or s.get("prompt_file")):
                names.add(s.get("prompt_name") or Path(s["prompt_file"]).name)
        p = d.get("prompt")
        for v in (p.values() if isinstance(p, dict) else [p]):
            if isinstance(v, str) and v.endswith(".md") and "\n" not in v:
                names.add(Path(v).name)
        if hops:
            for k in ("writing_run", "brief_from", "from_run"):
                m = re.match(r"(runs/[^/]+/[^/]+/[^/]+)", str(d.get(k) or ""))
                if m and (Path(root) / m.group(1)).is_dir():
                    names |= prompts_in(root, Path(root) / m.group(1), hops - 1)
    for f in [x for sub in (folder, folder / "stages", folder / "deliverable") for x in sorted(sub.glob("*.md"))]:
        with f.open(errors="ignore") as fh:
            m = PROMPT_HEADER_RE.search(fh.readline())
        if m:
            names.add(Path(m.group(1)).name)
    return {n for n in names if not n.startswith("_")}


def other_prompts(root, brand, reg, cache):
    """The prompt versions on record for a brief's run, in whatever lane it was made: name, version, label."""
    r = (reg or {}).get("run")
    if r not in cache:
        names = set()
        for folder in run_folders(root, brand, reg):
            names |= prompts_in(root, folder)
        cache[r] = [dict(zip(("name", "version"), prompt_version({"prompt_name": n}))) for n in sorted(names)]
        for p in cache[r]:
            p["label"] = label(p["name"], p["version"])
    return cache[r]


def made_in(root, brand, reg):
    """The register's lane and type; an older entry with neither, the lane its run folder sits in; else unknown."""
    said = " / ".join(x for x in ((reg or {}).get("lane"), (reg or {}).get("type")) if x)
    if said:
        return said
    lanes = [f.relative_to(Path(root) / "runs").parts[0] for f in run_folders(root, brand, reg)]
    return next((x for x in lanes if x != "stage-check"), "unknown")


def by_origin(rows):
    total = sum(r["spend"] for r in rows)
    out = []
    for o in ORIGINS:
        rs = [r for r in rows if r["origin"] == o]
        out.append({"origin": o, **sums(rs), "share": round(sum(r["spend"] for r in rs) / total, 4) if total else 0})
    return out


def by_family(rows, top=15):
    g = {}
    for r in rows:
        g.setdefault((r["family"], r["origin"]), []).append(r)
    out = [{"family": k[0], "origin": k[1], **sums(rs)} for k, rs in g.items()]
    return sorted(out, key=lambda x: -x["spend"])[:top]


def file_results(root, brand, asof=None):
    """Results from a media-buying verdicts file: the newest unless asof names one."""
    root = Path(root)
    asof = asof or latest_asof(root, brand)
    vpath = root / "runs" / "media-buying" / brand / "filter" / asof / "verdicts.json"
    ver = load_json(vpath)
    ads = ver.get("ads") if isinstance(ver, dict) else None
    if not isinstance(ads, list):
        raise BadInput(f"{vpath}: no 'ads' list")
    return {"asof": asof, "since": None, "data_through": ver.get("data_through"), "ads": ads,
            "source": str(vpath.relative_to(root)),
            "used": f"the media-buying file dated {asof}"}


def warehouse_results(brand, days, today=None):
    """Results per ad for the trailing days, from the warehouse. Raises when it can't be reached or holds nothing."""
    sys.path.insert(0, str(HERE))
    import audit as A
    today = today or dt.date.today()
    since, until = (today - dt.timedelta(days=days)).isoformat(), (today - dt.timedelta(days=1)).isoformat()
    rows = [r for r in A.warehouse_ads(brand, since, until) if r["spend"] > 0]
    if not rows:
        raise RuntimeError(f"it holds no spend for {brand} from {since} to {until}")
    ads = [{"ad_id": r["ad_id"], "ad_name": r["ad_name"], "spend": round(r["spend"], 2), "purchases": r["purchases"],
            "value": round(r["value"], 2), "cpa": round(r["spend"] / r["purchases"], 2) if r["purchases"] else None,
            "roas": round(r["value"] / r["spend"], 2)} for r in rows]
    return {"asof": today.isoformat(), "since": since, "data_through": max(r["last"] for r in rows), "ads": ads,
            "source": "warehouse meta_ad_insights", "used": f"the warehouse, trailing {days} days from {since} to {until}"}


def results(root, brand, days=90, today=None):
    """The Results step: the warehouse, else the newest file, said plainly."""
    try:
        return warehouse_results(brand, days, today)
    except Exception as e:  # noqa: BLE001  anything between here and the warehouse means the same thing: use the file
        why = str(e).split("\n")[0][:160]
    r = file_results(root, brand)
    r["used"] += " (the warehouse could not be used: %s)" % why
    print(f"Results: the warehouse could not be used ({why}); used {r['source']}, dated {r['asof']}.")
    return r


def build(root, brand, asof=None, res=None):
    root = Path(root)
    res = res or file_results(root, brand, asof)
    asof, ads, vpath = res["asof"], res["ads"], res["source"]
    regpath = root / "components" / "image-teardown" / "briefs.json"
    register = (load_json(regpath) or {}).get("briefs")
    if not isinstance(register, dict):
        raise BadInput(f"{regpath}: no 'briefs' map")
    register = register_index(register)
    names = load_names(root)

    def product_id(p):
        try:
            return names.product_id(brand, p)
        except Exception:
            return p
    by_path, by_key = index_runs(root, brand, product_id)
    A, _ = load_winners_rules()
    banked, prompt_cache = BankIndex(root, brand), {}

    def not_chain(row, reason, reg=None, has_brief=False, **more):
        """Where an ad with no prompt record behind it comes from; it joins `unmatched`, with the reason."""
        row.update(reason=reason, **more)
        family = A.script_key(A.base(row["ad_name"]))
        hit = banked.find(row["ad_id"], row["ad_name"])
        if hit:
            row.update(origin="banked", family=hit.get("name") or family, bank_row=hit["id"])
        elif has_brief:
            named = row["brief_key"] if "_none_" not in row["brief_key"] else family
            run = (reg or {}).get("run")
            row.update(origin="brief, made outside writing",
                       family=(reg or {}).get("title") or (Path(run).name if run else named), made_in=made_in(root, brand, reg))
            found = other_prompts(root, brand, reg, prompt_cache)
            if found:
                row["prompt_other"] = found
        else:
            row.update(origin="pre-system", family=family)
        unmatched.append(row)

    matched, unmatched, in_register = [], [], 0
    for a in ads:
        for need in ("ad_id", "ad_name", "spend", "purchases"):
            if need not in a:
                raise BadInput(f"{vpath}: ad row missing '{need}'")
        base = {"ad_id": a["ad_id"], "ad_name": a["ad_name"], "spend": a["spend"],
                "purchases": a["purchases"], "cpa": a.get("cpa"), "roas": a.get("roas")}
        if a.get("value") is not None:
            base["value"] = a["value"]
        p = read_brief(names, a["ad_name"])
        if not p:
            not_chain(base, "ad name does not parse as brand_product_brief-NNNN_batch[_funnel]")
            continue
        if p["brand"] not in (brand, None):
            not_chain(base, f"ad name brand '{p['brand']}' is not {brand}")
            continue
        pid = product_id(p["product"]) if p["product"] else None
        reg, foreign = None, False
        key = f"{brand}_{pid or 'none'}_{p['brief']}"
        # old register entries keep the store handle (`<brand>_<handle>_brief-NNNN`); the new ones the catalog id
        alt = f"{brand}_{p['product'] or 'none'}_{p['brief']}"
        if p["product"]:
            reg = register.get(key) or register.get(alt)
        if not reg and p["old"]:
            reg, foreign = old_register_entry(names, register, brand, pid, p["brief"])
            if reg and not pid and reg.get("key"):
                key = alt = reg["key"]
        if foreign and not p["brand"]:      # a bare p-number another brand's brief holds is not this ad's brief
            not_chain(base, "ad name does not parse as brand_product_brief-NNNN_batch[_funnel]")
            continue
        base.update(brief_key=key, brief_as_named=p["as_named"])
        if p["old"]:
            base["old_name"] = True
        in_register += 1 if reg else 0
        cands = by_key.get(key, []) + [d for d in by_key.get(alt, []) if d not in by_key.get(key, [])]
        run, how = None, None
        named = register_run(reg, brand, by_path)
        if named:
            run, how = named
        elif cands:
            run, how = pick_run(cands), "run.json brief match"
        if not run:
            why = "brief key not in register" if not reg else "no writing/teardown run record carries this brief"
            not_chain(base, why, reg, True, register_run=reg.get("run") if reg else None)
            continue
        hf, hv = prompt_version(run["stages"].get("stage4b"))
        bf, bv = prompt_version(run["stages"].get("stage5"))
        if hf is None and bf is None:
            not_chain(base, "run found but records no hook or brief prompt", reg, True, run=run["_rel"])
            continue
        matched.append({**base, "origin": "chain", "run": run["_rel"], "joined_by": how,
                        "family": (reg or {}).get("title") or Path(run["_rel"]).name,
                        "hook_prompt": {"name": hf, "version": hv, "label": label(hf, hv)},
                        "brief_prompt": {"name": bf, "version": bv, "label": label(bf, bv)},
                        "borrowed_from": cited(root, run["_rel"])})
    for r in matched:
        r["_hook"], r["_brief"] = r["hook_prompt"]["label"], r["brief_prompt"]["label"]
    per_cite = [{**r, "_cited": c} for r in matched for c in r["borrowed_from"]]
    per_other = [{**r, "_other": p["label"]} for r in unmatched for p in r.get("prompt_other") or []]
    every = matched + unmatched
    out = {
        "brand": brand, "asof": asof, "since": res.get("since"), "data_through": res.get("data_through"),
        "results_from": res["used"],
        "sources": [vpath, str(regpath.relative_to(root)),
                    f"runs/video-writing/{brand}/*/run.json", f"runs/video-teardown/{brand}/*/run.json"],
        "counts": {"ads": len(ads), "matched": len(matched), "unmatched": len(unmatched),
                   "brief_keys_in_register": in_register,
                   "old_name_briefs": sum(1 for r in every if r.get("old_name")),
                   "matched_spend": round(sum(r["spend"] for r in matched), 2),
                   "unmatched_spend": round(sum(r["spend"] for r in unmatched), 2)},
        "by_origin": by_origin(every),
        "by_family": by_family(every),
        "cant_trace": sorted(({k: r[k] for k in ("ad_id", "ad_name", "family", "spend", "purchases", "cpa", "roas")}
                              for r in unmatched if r["origin"] == "pre-system" and r["spend"] > CANT_TRACE_OVER),
                             key=lambda x: -x["spend"]),
        "by_hook_prompt": rollup(matched, "_hook"),
        "by_brief_prompt": rollup(matched, "_brief"),
        "by_borrowed_from": rollup(per_cite, "_cited"),
        "by_other_prompt": rollup(per_other, "_other"),
        "matched": [{k: v for k, v in r.items() if not k.startswith("_")} for r in matched],
        "unmatched": unmatched,
    }
    return out


def money(x):
    return "-" if x is None else f"${x:,.2f}"


def x_roas(r):
    return "-" if r["roas"] is None else f"{r['roas']}x"


def origin_line(o):
    """One line on where the last score's spend came from, or None for a score from before origins."""
    s = {r["origin"]: r["spend"] for r in o.get("by_origin") or []}
    if not s:
        return None
    return (f"Last score: ${s.get('chain', 0):,.0f} traced to a chain prompt, ${s.get('banked', 0):,.0f} banked winners, "
            f"${s.get('brief, made outside writing', 0):,.0f} brief outside writing, ${s.get('pre-system', 0):,.0f} pre-system")


def render_md(o):
    c = o["counts"]
    tot = sums(o["matched"] + o["unmatched"])
    L = [f"# Score: {o['brand']}", "",
         f"asof: {o['asof']} (ad data through {o['data_through']})",
         f"Results from: {o['results_from']}", "",
         "Sources:"] + [f"- `{s}`" for s in o["sources"]] + [
         "", "## Every dollar by origin", "",
         "| Origin | Ads | Spend | Share of spend | Purchases | CPA | ROAS |", "|---|---|---|---|---|---|---|"]
    for r in o.get("by_origin") or []:
        L.append(f"| {r['origin']} | {r['ads']} | {money(r['spend'])} | {r['share'] * 100:.1f}% | {r['purchases']:g} | "
                 f"{money(r['cpa'])} | {x_roas(r)} |")
    L += [f"| Total | {tot['ads']} | {money(tot['spend'])} | 100.0% | {tot['purchases']:g} | {money(tot['cpa'])} | {x_roas(tot)} |",
          "", f"Brief key in the register: {c['brief_keys_in_register']} ads. Brief read from an old-style name: "
          f"{c.get('old_name_briefs', 0)} ads.", ""]
    for title, key, col in (("By hook prompt version", "by_hook_prompt", "Version"),
                            ("By brief prompt version", "by_brief_prompt", "Version"),
                            ("By winner borrowed from", "by_borrowed_from", "Winner id"),
                            ("Other prompts", "by_other_prompt", "Version")):
        if key not in o:
            continue
        L += [f"## {title}", ""]
        if key == "by_borrowed_from":
            L += ["An ad counts under every id its run cites, so these rows can add up to more than the total.", ""]
        if key == "by_other_prompt":
            L += ["Prompts on record for ads made outside the writing chain, in the lane that made them. An ad counts "
                  "under every prompt its run lists, so these rows can add up to more than the total.", ""]
        L += [f"| {col} | Ads | Spend | Purchases | CPA | ROAS |", "|---|---|---|---|---|---|"]
        for r in o[key]:
            L.append(f"| {r['version']} | {r['ads']} | {money(r['spend'])} | {r['purchases']:g} | "
                     f"{money(r['cpa'])} | {'-' if r['roas'] is None else str(r['roas']) + 'x'} |")
        L.append("")
    L += ["## Top families by spend", "", "| Family | Origin | Ads | Spend | Purchases | CPA | ROAS |", "|---|---|---|---|---|---|---|"]
    for r in o.get("by_family") or []:
        L.append(f"| {r['family']} | {r['origin']} | {r['ads']} | {money(r['spend'])} | {r['purchases']:g} | "
                 f"{money(r['cpa'])} | {x_roas(r)} |")
    L += ["", "## Can't trace", "", f"Pre-system, not banked, spend over ${CANT_TRACE_OVER}.", ""]
    if o.get("cant_trace"):
        L += ["| Ad | Family | Spend | Purchases | CPA | ROAS |", "|---|---|---|---|---|---|"]
        for r in o["cant_trace"]:
            L.append(f"| {r['ad_name']} | {r['family']} | {money(r['spend'])} | {r['purchases']:g} | {money(r['cpa'])} | {x_roas(r)} |")
    else:
        L += ["None."]
    L += ["", "## Joined ads", "", "| Ad | Brief | Run | Hook prompt | Brief prompt | Borrowed from | Spend | Purch | CPA | ROAS |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(o["matched"], key=lambda x: -x["spend"]):
        L.append(f"| {r['ad_name']} | {r['brief_key']} | {r['run']} | {r['hook_prompt']['label']} | "
                 f"{r['brief_prompt']['label']} | {', '.join(r['borrowed_from'])} | {money(r['spend'])} | {r['purchases']:g} | {money(r['cpa'])} | {r['roas']} |")
    L += ["", "## Not joined", "", "| Ad | Origin | Family | Made in | Spend | Purch | Reason |", "|---|---|---|---|---|---|---|"]
    for r in sorted(o["unmatched"], key=lambda x: -x["spend"]):
        L.append(f"| {r['ad_name']} | {r['origin']} | {r['family']} | {r.get('made_in', '-')} | {money(r['spend'])} | "
                 f"{r['purchases']:g} | {r['reason']} |")
    return "\n".join(L) + "\n"


def write(root, o):
    """score.json and score.md for one build. -> the folder."""
    d = Path(root) / "runs" / "winners" / o["brand"] / "score" / o["asof"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "score.json").write_text(json.dumps(o, indent=2) + "\n")
    (d / "score.md").write_text(render_md(o))
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--asof")
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    a = ap.parse_args(argv)
    try:
        o = build(a.root, a.brand, a.asof)
    except BadInput as e:
        print(f"score: {e}", file=sys.stderr)
        return 2
    d = write(a.root, o)
    c = o["counts"]
    print(f"{a.brand} asof {o['asof']}: {c['matched']} joined / {c['unmatched']} not joined of {c['ads']} -> {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
