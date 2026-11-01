#!/usr/bin/env python3
"""intake — one front door for every swipe.

    python3 tools/run.py --brand <brand> --dry-run
    python3 tools/run.py --brand <brand> [--source paid|organic|own|competitor]
                         [--kind video|image|carousel|copy|page|email]
                         [--label <label>] [--limit N] [--gates hold|warn]

Reads BOTH swipe pools where they live (components/swipe-paid, components/swipe-organic),
makes ONE record per swipe — its source, its asset kind, where the asset is, the
brand it was swiped for, its format if its pool knows one, and which teardown it
routes to — and files the index to `runs/intake/<brand>/<label>/`:

    swipes.jsonl   one record per line
    run.json       what ran, against which pools, the counts
    check.json     gate-keyed: inputs, elements
    summary.md     the counts a person reads: source × kind × route, no-format, unknown-format,
                   asset not located (a swipe with no url, file or Drive path — counted, never dropped)

On a hold (either gate) no index is filed, and an earlier index in the same
label folder is renamed `swipes.jsonl.superseded` / `summary.md.superseded`
(intake#7), so the folder never shows an old index beside a HELD run.json.

It tears nothing down, fetches nothing, scrapes nothing, and calls no model —
a swipe's kind is read off its asset, so every run is free. `--dry-run` also
WRITES nothing: it prints the counts and where it would file.

`--brand` is required and must be a real folder under brands/. The index holds
every swipe saved FOR that brand plus every `shared` swipe (a competitor's ad
library belongs to no brand of ours; the pool does not say, so neither do we).
"""
import argparse
import collections
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))                              # appended, never inserted at 0

import gates as G                                           # noqa: E402
import paths as P                                           # noqa: E402
import pools                                                # noqa: E402


def counts(records):
    c = collections.Counter
    by = c((r["source"], r["owner"], r["kind"], r["route"]) for r in records)
    kinds = sorted({r["kind"] for r in records})
    return {
        "swipes": len(records),
        "by_source_kind_route": [{"source": s, "owner": o, "kind": k, "route": rt, "swipes": n}
                                 for (s, o, k, rt), n in sorted(by.items())],
        "by_route": dict(sorted(c(r["route"] for r in records).items())),
        "swiped_for": dict(sorted(c(r["swiped_for"] for r in records).items())),
        "format": {k: dict(sorted(c(r["format_state"] for r in records if r["kind"] == k).items())) for k in kinds},
        "no_format_by_source": {f"{s} · {k}": n for (s, k), n in
                                sorted(c((r["source"], r["kind"]) for r in records
                                         if r["format_state"] == "empty").items())},
        "structure_video": dict(sorted(c(r["structure_state"] for r in records
                                         if r["kind"] == "video" and r["source"] == "organic").items())),
        "unknown_format_values": dict(sorted(c(f'{r["format_list"] if "format_list" in r else r["kind"]}={r["format"]}'
                                               for r in records if r["format_state"] == "unknown-format").items())),
        "unknown_structure_values": dict(sorted(c(r["structure"] for r in records
                                                  if r["structure_state"] == "unknown-structure").items())),
        "asset_not_located": {f"{s} · {k}": n for (s, k), n in
                              sorted(c((r["source"], r["kind"]) for r in records
                                       if not (r["asset"]["url"] or r["asset"]["file"] or r["asset"]["drive"])).items())},
    }


def creative_qc(tool, stage, run_dir, output, given=None, items=None):
    """THE CREATIVE QC LOOP (the owner, 2026-10-02: "installed for each of my
    production tools … for all stages in the creation process"): the output is
    reviewed against what it was given and the stage's bars
    (components/marketing-chain-checks/definitions/stages.json); the round is filed in
    <run>/qc-log/. Never stops the run on its own."""
    try:
        here = Path(__file__).resolve()
        comp = next(p for p in here.parents if (p / "marketing-chain-checks" / "marketing_chain_checks").is_dir())
        q = str(comp / "marketing-chain-checks")
        if q not in sys.path:
            sys.path.insert(0, q)
        from marketing_chain_checks import review
        f = review.after_stage(tool, stage, run_dir, output=output, items=items,
                               sources=[given] if given and Path(given).exists() else None)
        bad = [k for k, v in f.items() if isinstance(v, dict) and v.get("severity") in ("BLOCKER", "FIX")]
        if bad:
            print(f"  QC {stage}: {len(bad)} finding(s) — see qc-log/QC-LOG.md")
        return f
    except Exception as e:
        print(f"  QC {stage}: review not run ({type(e).__name__})")
        return {}


def summary_md(brand, label, n, a, found, mode, elements_problems):
    L = [f"# Swipe intake — {brand} · {label}", "",
         f"**{n['swipes']:,} swipes** in one index — read from the two swipe folders where they live. "
         "Nothing was torn down, fetched, scraped or sent to a model.", "",
         "Filters: " + (", ".join(f"{k} = {v}" for k, v in (("source", a.source), ("kind", a.kind), ("limit", a.limit)) if v)
                        or "none — every swipe for this brand, plus every shared one"), "",
         "## Where they came from, what they are, where they go", "",
         "| source | whose | kind | goes to | swipes |", "|---|---|---|---|---:|"]
    L += [f"| {r['source']} | {r['owner']} | {r['kind']} | {r['route']} | {r['swipes']:,} |" for r in n["by_source_kind_route"]]
    L += ["", "## By teardown", "", "| goes to | swipes |", "|---|---:|"]
    L += [f"| {k} | {v:,} |" for k, v in n["by_route"].items()]
    L += ["", "## Swiped for", "", "| brand | swipes |", "|---|---:|"]
    L += [f"| {k} | {v:,} |" for k, v in n["swiped_for"].items()]
    L += ["", "`shared` = the pool does not say which brand it was saved for (a competitor's ad library, a general feed).", "",
          "## Format — who has one", "", "| kind | has a real format | no format | format not in the library |", "|---|---:|---:|---:|"]
    L += [f"| {k} | {v.get('known', 0):,} | {v.get('empty', 0):,} | {v.get('unknown-format', 0):,} |" for k, v in n["format"].items()]
    L += ["", "No format, by source:", ""] + [f"- {k}: **{v:,}**" for k, v in n["no_format_by_source"].items()]
    s = n["structure_video"]
    L += ["", "## Organic structure (organic videos only — a different list from format)", "",
          f"- a real structure: **{s.get('known', 0):,}** · none read yet: **{s.get('empty', 0):,}** · "
          f"a structure not in the library: **{s.get('unknown-structure', 0):,}**"]
    if n["unknown_format_values"] or n["unknown_structure_values"]:
        L += ["", "## Labels the library does not know (never passed, never invented)", ""]
        L += [f"- `{k}` — {v} swipe(s)" for k, v in n["unknown_format_values"].items()]
        L += [f"- structure `{k}` — {v} swipe(s)" for k, v in n["unknown_structure_values"].items()]
        L += ["", "The real ids for each list are in `check.json` beside this file."]
    L += ["", "## Asset not located", ""]
    L += ([f"- {k}: **{v:,}**" for k, v in n["asset_not_located"].items()]
          or ["- none — every swipe points at an asset (a url, a file or a Drive path)"])
    L += ["", "## Gates", "", "- inputs: **pass**",
          f"- elements: **{'pass' if not elements_problems else 'HELD'}**"
          + (f" — {len(elements_problems)} label(s) not in the library; gate mode `{mode}`"
             + (", so the index still filed" if mode == "warn" else "") if elements_problems else "")]
    if a.source is None and G.own_missing(found):
        L += [f"- own lane: **skipped** — the own-ads cache is not on this machine, so this index holds "
              f"no ad we ran; rebuild it with `{G.OWN_REBUILD}`"]
    L += ["", "## The pools it read", ""]
    L += [f"- {k}: `{v['path']}` — {v['files']} file(s)" for k, v in found.items()]
    return "\n".join(L) + "\n"


def show(n):
    print(f"  {n['swipes']:,} swipes\n")
    print(f"  {'source':<9}{'whose':<12}{'kind':<10}{'goes to':<17}{'swipes':>7}")
    for r in n["by_source_kind_route"]:
        print(f"  {r['source']:<9}{r['owner']:<12}{r['kind']:<10}{r['route']:<17}{r['swipes']:>7,}")
    print("\n  format, per kind:")
    for k, v in n["format"].items():
        print(f"    {k:<10} real {v.get('known', 0):>6,} · none {v.get('empty', 0):>6,} · not in the library {v.get('unknown-format', 0):>4,}")
    s = n["structure_video"]
    print(f"  organic structure (organic video): real {s.get('known', 0):,} · none {s.get('empty', 0):,} · "
          f"not in the library {s.get('unknown-structure', 0):,}")
    print("  swiped for: " + " · ".join(f"{k} {v:,}" for k, v in n["swiped_for"].items()))
    lost = n["asset_not_located"]
    print(f"  asset not located: {sum(lost.values()):,}"
          + (" (" + " · ".join(f"{k} {v:,}" for k, v in lost.items()) + ")" if lost else ""))


def supersede(out):
    """intake#7: a hold files no index, so an earlier one in this label folder
    is renamed `*.superseded` (an older `.superseded` is replaced). Renames
    only these two files; deletes nothing, makes no subfolder."""
    moved = []
    for name in ("swipes.jsonl", "summary.md"):
        if (out / name).is_file():
            (out / name).replace(out / (name + ".superseded"))
            moved.append(name + ".superseded")
    return moved


def run_json(out, a, label, found, result, files, superseded, n=None):
    doc = {"tool": P.TOOL, "brand": a.brand, "label": label,
           "when": datetime.datetime.now().isoformat(timespec="seconds"),
           "asked": {"source": a.source, "kind": a.kind, "limit": a.limit, "gates": a.gates},
           "pools": found, "model_calls": 0, "spend": 0,
           "result": result, "files": files, "superseded": superseded}
    if n is not None:
        doc["counts"] = n
    (out / "run.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="one front door for every swipe — index both pools as one")
    ap.add_argument("--brand", help="required — a real folder under brands/")
    ap.add_argument("--source", choices=pools.SOURCES)
    ap.add_argument("--kind", choices=pools.KINDS)
    ap.add_argument("--label", help="the run's label; default is today's date")
    ap.add_argument("--limit", type=int, help="index only the first N swipes")
    ap.add_argument("--gates", choices=G.MODES, default="warn",
                    help="the elements gate: hold stops the run, warn files it and says HELD (default warn)")
    ap.add_argument("--dry-run", "--dry", dest="dry_run", action="store_true",
                    help="write nothing, spend nothing — print the counts and where it would file")
    a = ap.parse_args(argv)
    if not a.brand:
        ap.error("--brand is required — there is no default brand. Real brands: " + ", ".join(P.brands()))
    Q = G.quality()
    label = a.label or datetime.date.today().isoformat()
    try:
        out = P.run_dir(a.brand, label, make=False)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"intake · {a.brand} · {label}" + (" · DRY RUN — nothing is written, nothing is spent" if a.dry_run else ""))

    # gate 1 — inputs. Always holds: an index of a missing pool is a wrong index.
    found = pools.found()
    problems = G.inputs_problems(a.brand, found, a.source)
    # a brand that does not exist gets no run folder made for it
    gate_dir = None if (a.dry_run or a.brand not in P.brands()) else out
    try:
        G.run_gate("inputs", problems, gate_dir, "hold")
    except Q.Held:
        if gate_dir is not None:                            # intake#7: no old index left beside a hold
            run_json(out, a, label, found, "HELD at the inputs gate — no index filed", [], supersede(out))
        return 2
    print("  ✓ inputs — both pools found, the brand is real")
    if a.source is None and G.own_missing(found):           # intake#5: a default run says the lane is empty
        print("  " + G.OWN_SKIPPED)

    records = [r for r in pools.read_all() if pools.matches(r, a.brand, a.source, a.kind)]
    if a.limit:
        records = records[: a.limit]

    # gate 2 — elements
    elements_problems = G.label_elements(records)
    n = counts(records)
    show(n)
    if a.dry_run:
        if elements_problems:
            print(f"\n  ✗ elements — {len(elements_problems)} label(s) are not in the library "
                  f"(gate mode `{a.gates}`: a real run would {'STOP here' if a.gates == 'hold' else 'still file, and say HELD'}):")
            for p in elements_problems[:8]:
                print("      " + p[:150])
            if len(elements_problems) > 8:
                print(f"      … and {len(elements_problems) - 8} more")
        else:
            print("\n  ✓ elements — every label carried is a real row")
        print(f"\n  would file to: {out}")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    held = False
    try:
        G.run_gate("elements", elements_problems, out, a.gates)
    except Q.Held:
        held = True
    if not held:
        with open(out / "swipes.jsonl", "w") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        (out / "summary.md").write_text(summary_md(a.brand, label, n, a, found, a.gates, elements_problems))
        creative_qc("intake", "record", out, out / "summary.md")
    run_json(out, a, label, found,
             "HELD at the elements gate — no index filed" if held else "filed",
             [] if held else ["swipes.jsonl", "summary.md", "check.json"],
             supersede(out) if held else [], n)
    print(f"\n  -> {out}" + ("   (HELD — check.json says why; no index filed)" if held else ""))
    if not held:                                            # the living index follows every run (swipes_index.py)
        try:
            import swipes_index
            swipes_index.build(a.brand)
        except Exception as e:  # noqa: BLE001 — an index that cannot rebuild never fails the run
            print(f"  swipes index not rebuilt: {type(e).__name__}: {e}")
    return 2 if held else 0


if __name__ == "__main__":
    sys.exit(main())
