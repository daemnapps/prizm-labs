"""The Variable Index — every adjustable variable the teardown records, with
every value a brand's posts show, counted and weighted by views and saves.

    python3 machine/run.py index --brand <brand> [--dry-run] [--workers 6] [--all-runs]

Definitions (which variables exist, where each is read from, how production
changes it) live in definitions/variables.json. The observed values are
computed here and emitted to runs/ad-variations/<brand>/variable-index/:

    variable-index.json   the index — the shared vocabulary stages 2–4 cite
    VARIABLE-INDEX.md     the Markdown mirror
    coded/<run>.json      the coder's answer per teardown run (cached: a run
                          is coded again only when its teardown or the coder
                          prompt changes)

`rule:` variables are read straight from the record (corpus.py). `coder:`
variables are coded by one model call per run (prompt stage0c). Adding runs
or a brand grows the index: the next build codes only what is new, and every
value lists the runs it came from.
"""
import datetime
import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
sys.path.insert(0, str(COMP.parent / "run-kit"))
from run_kit import model as M, prompts as P, pool  # noqa: E402

import corpus  # noqa: E402

CODER_TIER = "checks"              # coding against a written list is applying rules → Sonnet
LOCK_SHARE = 0.60                  # the lock-leaning threshold, stated in variables.json
TEXT_TOP = 8


def definitions():
    return json.loads((COMP / "definitions" / "variables.json").read_text())


def coder_vocabulary(defs):
    lines = []
    for v in defs["variables"]:
        if not v["how"].startswith("coder:"):
            continue
        key = v["how"][6:]
        if v["type"] == "numeric":
            allowed = "a number (seconds or a count) or null"
        elif v["type"] == "text":
            allowed = "the record's own words, or null"
        else:
            allowed = " | ".join(v.get("vocab") or []) + " | other: <label>"
        lines.append(f"- {key} — {v['name']} ({v['id']}) — {allowed}")
    return "\n".join(lines)


def extract_json(text):
    """The last fenced json block, else the outermost braces."""
    blocks = re.findall(r"```(?:json)?\s*\n(.*?)\n```", text or "", re.S)
    for b in reversed(blocks):
        try:
            return json.loads(b)
        except ValueError:
            continue
    a, b = (text or "").find("{"), (text or "").rfind("}")
    if a >= 0 and b > a:
        return json.loads(text[a:b + 1])
    raise ValueError("no JSON in the model's answer")


def _run_hash(r):
    h = hashlib.sha256()
    for part in (r.teardown, r.spec, json.dumps(r.doctrine, sort_keys=True)):
        h.update(part.encode())
    return h.hexdigest()[:12]


def code_run(r, defs, out_dir, dry=False, force_model=None):
    """The coder's values for one run — from cache when nothing changed."""
    pf = P.latest(COMP / "prompts", "stage0c")
    psha, rsha = P.sha(pf), _run_hash(r)
    cache = out_dir / "coded" / f"{r.slug}.json"
    old = corpus.load_json(cache, {}) or {}
    if old.get("prompt_sha256_12") == psha and old.get("teardown_sha12") == rsha and old.get("codes"):
        return old, "cached"
    filled = P.fill(pf.read_text(), {
        "teardown_record": r.teardown, "replication_spec": r.spec,
        "doctrine_json": json.dumps(r.doctrine, indent=1, ensure_ascii=False),
        "coder_vocabulary": coder_vocabulary(defs)})
    model, _ = M.pick(CODER_TIER, len(filled), force_model)
    if dry:
        return {"codes": {}, "chars_in": len(filled), "model": model}, "dry"
    text = M.call(filled, model, label=f"stage0c:{r.slug}", timeout=900)
    codes = extract_json(text).get("codes") or {}
    rec = {"run": r.slug, "prompt": pf.name, "prompt_sha256_12": psha, "teardown_sha12": rsha, "model": model,
           "coded_at": datetime.datetime.now().isoformat(timespec="seconds"), "chars_in": len(filled),
           "chars_out": len(text), "codes": codes}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    return rec, "coded"


# ------------------------------------------------------------------ values
def run_values(r, defs, coded):
    """{variable id: value} for one run. Lists stay lists (multi); None = not in the record."""
    out = {}
    codes = (coded or {}).get("codes") or {}
    for v in defs["variables"]:
        kind, key = v["how"].split(":", 1)
        if kind == "rule":
            val = corpus.rule(key, r)
        else:
            c = codes.get(key)
            val = c.get("value") if isinstance(c, dict) else c
        if isinstance(val, str):
            val = val.strip()
            if val.lower() in ("null", "none found", ""):
                val = None
        out[v["id"]] = val
    return out


def _bucket(v, val):
    """The value a run is counted under for one variable."""
    if val is None or val == []:
        return ["(not in the record)"]
    if v["type"] == "numeric":
        try:
            x = float(val)
        except (TypeError, ValueError):
            return [f"other: {val}"]
        return [corpus._band(x, v.get("bins") or [0, 999]) or "(out of range)"]
    if v["type"] == "multi":
        return [str(x) for x in (val if isinstance(val, list) else [val])]
    s = str(val)
    if v["type"] == "categorical":
        s = s.strip().strip('"').lower() if len(s) < 60 else s[:80]
    return [s]


def build(repo, brand, dry=False, workers=6, all_runs=False, force_model=None, echo=print):
    defs = definitions()
    out_dir = Path(repo) / "runs" / "ad-variations" / brand / "variable-index"
    out_dir.mkdir(parents=True, exist_ok=True)
    runs = corpus.load(repo, brand, with_metrics_only=not all_runs)
    if not runs:
        raise SystemExit(f"no finished teardown runs for {brand} (with metrics: {not all_runs})")
    echo(f"  index · {brand}: {len(runs)} teardown runs")

    coded, status = {}, {}

    def job(slug, r):
        return code_run(r, defs, out_dir, dry=dry, force_model=force_model)

    res = pool.run_all([(r.slug, r) for r in runs], job, workers=workers,
                       on_done=lambda s, x: echo(f"    {s}: {x[0]} {x[1][1] if x[0] == 'done' else x[1][:160]}"))
    for slug, (st, val) in res.items():
        if st == "done":
            coded[slug], status[slug] = val[0], val[1]
        else:
            status[slug] = f"{st}: {val[:200]}"
    if dry:
        chars = sum(c.get("chars_in", 0) for c in coded.values() if status.get(c.get("run", ""), "") == "dry") or \
            sum(c.get("chars_in", 0) for c in coded.values())
        echo(f"  dry run: {sum(1 for s in status.values() if s == 'dry')} runs would be coded, "
             f"{sum(1 for s in status.values() if s == 'cached')} already cached; ≈{chars / 4 / 1000:.0f}k tokens in")
        return None

    per_run = {r.slug: run_values(r, defs, coded.get(r.slug)) for r in runs}
    weighted = [r for r in runs if r.views > 0]
    tot_v = sum(r.views for r in weighted) or 1
    tot_s = sum(r.saves for r in weighted) or 1
    top_q = sorted(weighted, key=lambda r: -r.views)[:max(1, math.ceil(len(weighted) / 4))]
    top_slugs = {r.slug for r in top_q}
    top_v = sum(r.views for r in top_q) or 1
    by_slug = {r.slug: r for r in runs}

    variables = []
    for v in defs["variables"]:
        vals = {}
        for r in runs:
            for b in _bucket(v, per_run[r.slug][v["id"]]):
                e = vals.setdefault(b, {"value": b, "count": 0, "views": 0.0, "saves": 0.0, "likes": 0.0, "runs": [],
                                        "top_views": 0.0})
                e["count"] += 1
                e["views"] += r.views
                e["saves"] += r.saves
                e["likes"] += r.likes
                e["runs"].append(r.slug)
                if r.slug in top_slugs:
                    e["top_views"] += r.views
        rows = []
        for e in vals.values():
            rows.append({"value": e["value"], "count": e["count"],
                         "view_share": round(e["views"] / tot_v, 4), "save_share": round(e["saves"] / tot_s, 4),
                         "save_rate": round(e["saves"] / e["views"], 4) if e["views"] else None,
                         "like_rate": round(e["likes"] / e["views"], 4) if e["views"] else None,
                         "top_quartile_view_share": round(e["top_views"] / top_v, 4),
                         "runs": e["runs"]})
        rows.sort(key=lambda x: (-x["view_share"], -x["count"]))
        known = [x for x in rows if x["value"] != "(not in the record)"]
        lead = max(known, key=lambda x: x["top_quartile_view_share"]) if known else None
        if v["type"] == "text":
            tendency, why = "lever", "wording — always adjustable"
            distinct = len(known)
            rows = rows[:TEXT_TOP] + ([{"value": f"… {distinct - TEXT_TOP} more distinct values", "count": None}] if distinct > TEXT_TOP else [])
        elif lead and lead["top_quartile_view_share"] >= LOCK_SHARE:
            tendency = "lock-leaning"
            why = (f"{lead['value']!s} carries {lead['top_quartile_view_share']:.0%} of the top-quartile posts' views "
                   f"({len(top_q)} posts)")
        else:
            tendency = "lever"
            why = (f"the top-quartile posts vary — the most common value, {lead['value']!s}, carries "
                   f"{lead['top_quartile_view_share']:.0%} of their views" if lead else "no values in the record")
        numeric = None
        if v["type"] == "numeric":
            xs = [float(x) for x in (per_run[s][v["id"]] for s in per_run) if isinstance(x, (int, float))]
            numeric = {"median": round(statistics.median(xs), 2), "min": min(xs), "max": max(xs)} if xs else None
        variables.append({**{k: v[k] for k in ("id", "name", "family", "read_from", "type", "how", "change_by", "cost_class")},
                          "tendency": tendency, "tendency_why": why,
                          "tendency_value": lead["value"] if lead and tendency == "lock-leaning" else None, "numeric": numeric,
                          "new_values": [x["value"] for x in known if str(x["value"]).startswith("other:")],
                          "values": rows})

    index = {
        "_what": "The Variable Index for one brand — generated by components/ad-variations/machine/index.py from "
                 "the brand's video-teardown runs. Definitions: components/ad-variations/definitions/variables.json.",
        "brand": brand, "built": datetime.datetime.now().isoformat(timespec="seconds"),
        "runs": len(runs), "weighted_runs": len(weighted), "total_views": tot_v, "total_saves": tot_s,
        "top_quartile": sorted(top_slugs), "lock_share": LOCK_SHARE,
        "sources": sorted({r.metrics.get("_manifest") for r in runs if r.metrics.get("_manifest")}),
        "coder": {"prompt": P.latest(COMP / "prompts", "stage0c").name, "tier": CODER_TIER,
                  "coded_now": sum(1 for s in status.values() if s == "coded"),
                  "cached": sum(1 for s in status.values() if s == "cached"),
                  "failed": {k: s for k, s in status.items() if s not in ("coded", "cached")}},
        "families": defs["families"], "cost_classes": defs["cost_classes"], "lock_lever_rule": defs["lock_lever_rule"],
        "variables": variables,
        "per_run": {s: {"views": by_slug[s].views, "saves": by_slug[s].saves, "likes": by_slug[s].likes,
                        "rank": by_slug[s].metrics.get("rank"), "id": by_slug[s].metrics.get("id"),
                        "values": per_run[s]} for s in per_run},
    }
    (out_dir / "variable-index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    (out_dir / "VARIABLE-INDEX.md").write_text(markdown(index))
    echo(f"  index written: {out_dir.relative_to(repo)}/variable-index.json · {len(variables)} variables · "
         f"coded now {index['coder']['coded_now']}, cached {index['coder']['cached']}, failed {len(index['coder']['failed'])}")
    return index


def pct(x):
    return "—" if x is None else f"{x * 100:.1f}%"


def markdown(ix):
    L = [f"# Variable Index — {ix['brand']}", "",
         f"_Built {ix['built']} by `components/ad-variations/machine/index.py` from {ix['runs']} teardown runs "
         f"({ix['weighted_runs']} with views and saves). Metrics: {', '.join(f'`{s}`' for s in ix['sources']) or 'none'}._", "",
         f"**Lock or lever:** {ix['lock_lever_rule']}", "",
         "Columns: count of posts · share of all views · share of all saves · save rate (saves ÷ views) of those posts · "
         "share of the top-quartile posts' views.", ""]
    fams = {}
    for v in ix["variables"]:
        fams.setdefault(v["family"], []).append(v)
    for fam, label in ix["families"].items():
        if fam not in fams:
            continue
        L += [f"## {label}", ""]
        for v in fams[fam]:
            L += [f"### {v['id']} · {v['name']} — {v['tendency'].upper()}", "",
                  f"- Read from: {'; '.join(v['read_from'])} (`{v['how']}`)",
                  f"- Type: {v['type']} · changed by: {', '.join(v['change_by'])} · cost class: {v['cost_class']}",
                  f"- Why {v['tendency']}: {v['tendency_why']}"]
            if v.get("numeric"):
                L.append(f"- Median {v['numeric']['median']} (range {v['numeric']['min']}–{v['numeric']['max']})")
            if v.get("new_values"):
                L.append(f"- New values the coder found: {', '.join(v['new_values'])}")
            L += ["", "| Value | Posts | Views | Saves | Save rate | Top-quartile views |", "|---|---|---|---|---|---|"]
            for x in v["values"]:
                if x.get("count") is None:
                    L.append(f"| {x['value']} | | | | | |")
                    continue
                val = str(x["value"]).replace("|", "/").replace("\n", " ")[:160]
                L.append(f"| {val} | {x['count']} | {pct(x['view_share'])} | {pct(x['save_share'])} | "
                         f"{pct(x['save_rate'])} | {pct(x['top_quartile_view_share'])} |")
            L.append("")
    return "\n".join(L) + "\n"
