#!/usr/bin/env python3
"""ad-variations — one proven ad's teardown in, a variation plan out.

    python3 machine/run.py plan <teardown run | post id> --brand <brand> [--n 10] [--k 5]
                             [--plan <campaign plan file>] [--label <label>] [--dry-run]
                             [--rerun-from stage3] [--model <model id>]
    python3 machine/run.py index --brand <brand> [--dry-run] [--workers 6] [--all-runs]
    python3 machine/run.py page                 rebuild the Ad Variations page from every run on disk
    python3 machine/run.py stages               print the current prompt file for every stage

A run lands in runs/ad-variations/<brand>/<label>/ (label defaults to the
teardown run's folder name): every prompt as sent, every stage's answer,
measure.json, evidence.md, variation-plan.json (THE CONTRACT), VARIATIONS.md, and
deliverable/. This component plans; it generates nothing and spends nothing
on production. `--dry-run` fills every prompt and spends nothing at all.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
sys.path.insert(0, str(COMP.parent / "run-kit"))
from run_kit import filing, paths  # noqa: E402
from run_kit.stage import Chain, DRY  # noqa: E402

import assemble  # noqa: E402
import brandctx  # noqa: E402
import corpus  # noqa: E402
import index as IX  # noqa: E402
import measure  # noqa: E402

TOOL = "ad-variations"
PROMPTS = COMP / "prompts"
STEPS = [
    {"key": "stage1", "name": "Anatomy → elements", "tier": "designs", "label": "elements"},
    {"key": "stage2", "name": "Locks vs levers", "tier": "designs", "label": "locks-levers", "depends": ["stage1"]},
    {"key": "stage3", "name": "Variation matrix", "tier": "designs", "label": "matrix", "depends": ["stage2"]},
    {"key": "stage4", "name": "New formats", "tier": "designs", "label": "formats", "depends": ["stage1"]},
    {"key": "stage5", "name": "Merge recipe", "tier": "designs", "label": "recipe", "depends": ["stage3", "stage4"]},
    {"key": "stage6", "name": "QC gates", "tier": "designs", "label": "gates", "depends": ["stage5"]},
    {"key": "stage7", "name": "Congruence links", "tier": "designs", "label": "congruence", "depends": ["stage3"]},
]


def defs(name):
    return json.loads((COMP / "definitions" / name).read_text())


# ------------------------------------------------------------------ deterministic inputs
def load_index(repo, brand):
    p = Path(repo) / "runs" / TOOL / brand / "variable-index" / "variable-index.json"
    if not p.is_file():
        raise SystemExit(f"no Variable Index for {brand} yet — build it first: run.py index --brand {brand}")
    return json.loads(p.read_text())


def ad_values(ix, run, repo, brand, dry):
    """This ad's value for every variable — from the index, or coded now if the ad is not in it."""
    if run.slug in ix["per_run"]:
        return ix["per_run"][run.slug]["values"]
    out_dir = Path(repo) / "runs" / TOOL / brand / "variable-index"
    rec, _ = IX.code_run(run, IX.definitions(), out_dir, dry=dry)
    return IX.run_values(run, IX.definitions(), rec)


def fmt_values(vals, vdefs):
    names = {v["id"]: v["name"] for v in vdefs}
    L = []
    for vid, val in vals.items():
        if isinstance(val, list):
            val = "; ".join(map(str, val)) or None
        L.append(f"- {vid} · {names.get(vid, '?')} · {val if val not in (None, '') else '(not in the record)'}")
    return "\n".join(L)


def tend(v):
    return f"lock-leaning → {v['tendency_value']}" if v.get("tendency_value") else v["tendency"]


def evidence(ix, vals):
    """The table stage 2 quotes from: this ad's value in the brand's corpus, per variable."""
    tot_v, tot_s = ix["total_views"], ix["total_saves"]
    L = [f"Corpus: {ix['runs']} posts ({ix['weighted_runs']} with metrics), {tot_v:,.0f} views, {tot_s:,.0f} saves. "
         f"Set save rate {tot_s / tot_v:.2%}. Top quartile = the {len(ix['top_quartile'])} most-viewed posts.", "",
         "| Variable | This ad | Posts | Views | Saves | Save rate (these) | Save rate (the rest) | Top-quartile views | Tendency | Cost class |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for v in ix["variables"]:
        val = vals.get(v["id"])
        buckets = IX._bucket({"type": v["type"], "bins": next((d.get("bins") for d in IX.definitions()["variables"] if d["id"] == v["id"]), None)}, val)
        for b in buckets:
            row = next((x for x in v["values"] if x.get("value") == b), None)
            if row is None or row.get("count") is None:
                L.append(f"| {v['id']} {v['name']} | {str(val)[:90]} | — | — | — | — | — | — | {tend(v)} | {v['cost_class']} |")
                continue
            rest_v, rest_s = tot_v - row["view_share"] * tot_v, tot_s - row["save_share"] * tot_s
            rest_rate = f"{rest_s / rest_v:.2%}" if rest_v > 0 else "—"
            L.append(f"| {v['id']} {v['name']} | {str(b)[:90]} | {row['count']} | {row['view_share']:.1%} | {row['save_share']:.1%} | "
                     f"{(row['save_rate'] or 0):.2%} | {rest_rate} | {row['top_quartile_view_share']:.1%} | {tend(v)} | {v['cost_class']} |")
    return "\n".join(L)


def siblings(ix, slug, vals, top=5):
    """The brand's posts closest to this ad — same values on most categorical variables.
    Where a near-twin differs on one or two variables and its views differ, the brand has
    already half-tested those variables. Computed, not modelled."""
    # what a viewer SEES and HEARS — the audience and structure reads are left out, so two posts
    # shot the same way match even when the reads describe them differently
    cats = [v for v in ix["variables"] if v["family"] not in ("audience", "structure")
            and (v["type"] == "categorical" or v["id"] in ("V-hook.03", "V-hook.11", "V-text.07"))]
    norm = lambda x: None if x in (None, "", []) else re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", str(x).lower()))[:60].strip()
    TEXT = ("V-hook.03", "V-hook.11", "V-text.07")
    eq = lambda k, a, b: (a in b or b in a) if k in TEXT and a and b and a != "none" and b != "none" else a == b
    mine = {v["id"]: norm(vals.get(v["id"])) for v in cats}
    views = {s: r["views"] for s, r in ix["per_run"].items()}
    rows = []
    for s, r in ix["per_run"].items():
        if s == slug:
            continue
        theirs = {v["id"]: norm(r["values"].get(v["id"])) for v in cats}
        both = [k for k in mine if mine[k] is not None and theirs[k] is not None]
        if not both:
            continue
        wt = {k: (4 if k in ("V-hook.03", "V-hook.11", "V-text.07") and mine[k] not in ("none",) else 1) for k in both}
        same = sum(wt[k] for k in both if eq(k, mine[k], theirs[k]))
        diff = [k for k in both if not eq(k, mine[k], theirs[k])]
        rows.append((same / sum(wt.values()), s, diff, theirs))
    rows.sort(key=lambda x: -x[0])
    name = {v["id"]: v["name"] for v in cats}
    mv = views.get(slug)
    L = [f"This ad: {mv:,.0f} views." if mv else "This ad has no metrics on file.", "",
         "Similarity counts matching values on what a viewer sees and hears; the same spoken first line or the same sticker wording counts four times — it usually means the same template.", "",
         "| Post | Rank | Views | Similarity | Differs on (theirs → vs this ad) |", "|---|---|---|---|---|"]
    for sim, s, diff, theirs in rows[:top]:
        r = ix["per_run"][s]
        raw = r["values"]
        d = "; ".join(f"{k} {name[k]}: {str(raw.get(k))[:50]} (this ad: {str(vals.get(k))[:50]})" for k in diff[:14])
        L.append(f"| {s} | {r.get('rank')} | {r['views']:,.0f} | {sim:.0%} | {d}{' …' if len(diff) > 14 else ''} |")
    return "\n".join(L)


def index_summary(ix, top=4):
    L = []
    for fam, label in ix["families"].items():
        rows = [v for v in ix["variables"] if v["family"] == fam and v["type"] != "text"]
        if not rows:
            continue
        L.append(f"## {label}")
        for v in rows:
            vals = [x for x in v["values"] if x.get("count") and x["value"] != "(not in the record)"][:top]
            L.append(f"- {v['id']} {v['name']} ({v['tendency']}): " + "; ".join(
                f"{x['value']} — {x['count']} posts, {x['view_share']:.1%} of views, save rate {(x['save_rate'] or 0):.2%}" for x in vals))
    return "\n".join(L)


def combos(ix, keys=("V-hook.04", "V-proof.01", "V-struct.07")):
    seen = {}
    for slug, r in ix["per_run"].items():
        k = tuple(str(r["values"].get(x) or "—") for x in keys)
        e = seen.setdefault(k, {"posts": 0, "views": 0.0})
        e["posts"] += 1
        e["views"] += r["views"]
    L = [f"| {' | '.join(keys)} | Posts | View share |", "|" + "---|" * (len(keys) + 2)]
    for k, e in sorted(seen.items(), key=lambda kv: -kv[1]["views"]):
        L.append(f"| {' | '.join(k)} | {e['posts']} | {e['views'] / ix['total_views']:.1%} |")
    return "\n".join(L)


def routes_table():
    r = defs("routes.json")
    L = [f"Overshoot on video routes: +{r['video_overshoot']:.0%}. Rolls per still: {r['still_rolls']}.", "",
         "| id | what | unit | $ per unit | status |", "|---|---|---|---|---|"]
    for x in r["routes"]:
        rate = "not in machine cost" if x["usd_per_unit"] is None else f"${x['usd_per_unit']}"
        L.append(f"| {x['id']} | {x['name']} — {x.get('note', '')} | {x['unit']} | {rate} | {'TEST' if x.get('test') else 'locked' if x.get('locked') else 'not locked'} |")
    return "\n".join(L)


def gates_table():
    return "\n".join(f"- {g['id']} · {g['name']} — passes: {g['passes']} — check: {g['check']}" for g in defs("gates.json")["gates"])


def library_rows(repo, name):
    p = Path(repo) / "components" / "elements" / "library" / name
    if not p.is_file():
        return "(the element library has no such list)"
    d = json.loads(p.read_text())
    return "\n".join(f"- {r['id']} — {r.get('name')}: {r.get('what') or ''}" for r in d.get("rows", []))


def metrics_line(run):
    m = run.metrics
    if not m:
        return "No post metrics on file for this run."
    keys = ("rank", "views", "likes", "saves", "comments", "shares", "duration_s", "posted", "caption", "url")
    s = " · ".join(f"{k} {m.get(k)}" for k in keys if m.get(k) not in (None, ""))
    if m.get("views"):
        s += f" · save rate {float(m.get('saves') or 0) / float(m['views']):.2%} · like rate {float(m.get('likes') or 0) / float(m['views']):.2%}"
    return s


# ------------------------------------------------------------------ the chain
def plan(args):
    repo = paths.repo(HERE)
    brand = args.brand
    tdir = corpus.find_run(repo, brand, args.source)
    mx = corpus.metrics_index(repo, brand)
    run = corpus.Run(tdir, mx.get(tdir.name))
    if not run.complete:
        raise SystemExit(f"{tdir} is not a finished teardown (needs triage, record, doctrine, audience, spec)")
    ix = load_index(repo, brand)
    label = args.label or tdir.name
    out = filing.run_dir(TOOL, brand, label, start=HERE)
    assemble.REPAIR_DIR = out
    avatar = corpus.kv(run.audience, "AVATAR")
    bc = brandctx.BrandContext(repo, brand, avatar)
    vdefs = IX.definitions()["variables"]
    vals = ad_values(ix, run, repo, brand, args.dry_run)
    edefs = defs("elements.json")["elements"]

    chain = Chain(TOOL, brand, label, out, PROMPTS, STEPS, dry=args.dry_run, rerun_from=args.rerun_from,
                  force_model=args.model,
                  assignment={"teardown_run": str(tdir.relative_to(repo)), "post": run.metrics.get("id"),
                              "n": args.n, "k": args.k, "plan": args.plan, "avatar": avatar,
                              "index_built": ix["built"], "index_runs": ix["runs"]})
    print(f"ad-variations · {brand} · {label}{' · DRY RUN' if args.dry_run else ''}")

    m = measure.run(out, tdir)                     # free: ffmpeg only, so it runs on a dry run too
    measurement = (out / "measure.md").read_text()
    ev = evidence(ix, vals)
    (out / "evidence.md").write_text("# Evidence — this ad in the brand's corpus\n\n" + ev + "\n")
    rules = bc.rules()
    avatars, language, cast, products = bc.avatars(), bc.language(), bc.cast(), bc.products()
    elist = "\n".join(f"- {e['key']} · {e['name']} · {', '.join(e['variables'])}" for e in edefs)
    common = {"metrics": metrics_line(run)}

    s1 = chain.run("stage1", **common, teardown_record=run.teardown, replication_spec=run.spec,
                   doctrine_read=run.doctrine_md or json.dumps(run.doctrine, indent=1), audience_read=run.audience,
                   measurement=measurement, ad_values=fmt_values(vals, vdefs), element_list=elist)
    sib = siblings(ix, run.slug, vals)
    (out / "evidence.md").write_text("# Evidence — this ad in the brand's corpus\n\n" + ev + "\n\n## The closest posts\n\n" + sib + "\n")
    s2 = chain.run("stage2", **common, elements=s1, evidence=ev, siblings=sib, brand_rules=rules)
    s3 = chain.run("stage3", **common, elements=s1, calls=s2, siblings=sib, audience_read=run.audience, avatars=avatars,
                   language=language, cast=cast, products=products, brand_rules=rules, n=args.n)
    s4 = chain.run("stage4", elements=s1, index_summary=index_summary(ix), combos=combos(ix), avatars=avatars,
                   brand_rules=rules, k=args.k)
    beats = assemble.section(s1, "beats", measurement)
    s5 = chain.run("stage5", beats=beats, variations=s3, formats=s4, routes=routes_table(), cast=cast, brand_rules=rules)
    forced = assemble.forced_gates(s5) if s5 != DRY else "(computed from stage 5 at run time)"
    s6 = chain.run("stage6", variations=assemble.join_for_gates(s3, s5), gates=gates_table(), forced=forced, brand_rules=rules)
    plan_text = Path(args.plan).read_text()[:12000] if args.plan and Path(args.plan).is_file() else "(no campaign plan supplied for this run)"
    s7 = chain.run("stage7", variations=s3, static_formats=library_rows(repo, "format.image.json"),
                   page_formats=library_rows(repo, "format.page.json"),
                   funnels=f"{bc.funnels()}\n\n=== campaign plan ({args.plan or 'none'}) ===\n{plan_text}")

    chain.record.state["brand_files_read"] = sorted(set(bc.read_files))
    chain.record.save()
    if args.dry_run:
        est = assemble.llm_cost(chain.record.state, dry=True)
        print(f"  dry run: every prompt filled and saved beside the run; ≈{est['tokens_in'] / 1000:.0f}k tokens in; "
              f"≈${est['usd']:.2f} at Opus rates with a typical answer size. Nothing spent.")
        return
    doc = assemble.build(repo, brand, run, ix, out, {"stage1": s1, "stage2": s2, "stage3": s3, "stage4": s4,
                                                     "stage5": s5, "stage6": s6, "stage7": s7}, m, chain.record.state)
    chain.deliver(out / "variation-plan.json", out / "VARIATIONS.md")
    t = doc["totals"]
    print(f"  done: {len(doc['variations'])} variations + {len(doc['formats'])} new formats · machine ${t['usd']:.2f} "
          f"(${t['usd_with_tests']:.2f} with the TEST routes) · ≈{t['hours']:.1f} h · planning spend ≈${doc['run']['llm_cost']['usd']:.2f}")
    print(f"  {out.relative_to(repo)}/variation-plan.json")


def stages(_):
    from run_kit import prompts as P
    for s in [{"key": "stage0c", "name": "Coder (Variable Index)"}] + STEPS:
        print(f"{s['key']:8} {s['name']:24} {P.latest(PROMPTS, s['key']).relative_to(COMP)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("source")
    p.add_argument("--brand", required=True)
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--plan")
    p.add_argument("--label")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--rerun-from")
    p.add_argument("--model")
    i = sub.add_parser("index")
    i.add_argument("--brand", required=True)
    i.add_argument("--dry-run", action="store_true")
    i.add_argument("--workers", type=int, default=6)
    i.add_argument("--all-runs", action="store_true")
    sub.add_parser("page")
    sub.add_parser("stages")
    a = ap.parse_args()
    if a.cmd == "plan":
        plan(a)
    elif a.cmd == "index":
        IX.build(paths.repo(HERE), a.brand, dry=a.dry_run, workers=a.workers, all_runs=a.all_runs)
    elif a.cmd == "page":
        import page
        page.build(paths.repo(HERE))
    else:
        stages(a)


if __name__ == "__main__":
    main()
