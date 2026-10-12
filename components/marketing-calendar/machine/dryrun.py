#!/usr/bin/env python3
"""The dry run: everything a month needs, checked — nothing spent, nothing written.

    python3 calendar.py 2026-11 --brand <brand> --dry-run

What it does, in the order the real run would:

    the brand      can it run the chain at all? (`chain.readiness`) — a blocked
                   brand stops here and the command exits 2
    layer 1        the month's public holidays           (code, really run)
    layer 2        the brand's moments, resolved to dates (code, really run)
    layer 3  AI    the prompt it would send (highest -vN-), every field it
                   would be handed, OK / EMPTY / MISSING, any `{field}` left open
    layer 5  AI    the same. Two of its fields (`cells`, `anchored`) are MADE by
                   layers 3 and 4 — they are taken from a month already on disk
                   when there is one, and otherwise reported as waiting on
                   layer 3, which is the truth and not a fault
    the types      every type in the brand's catalogue, looked up in the
                   element library (components/elements, format/email)

ZERO model calls: this file never touches `runner.claude`. NOTHING is written:
no folder is made, not even the month's — it only says where the month WOULD go.

Exit codes: 0 ready · 1 a prompt is missing, a `{field}` has nothing to fill it,
or a doctrine slice is absent · 2 the brand is blocked.
"""
import datetime
import json
import re
import sys
from pathlib import Path

import chain as CH
import holidays as H
import runner as R
import gates as G
from paths import WORKSPACE, COMPONENTS, rel
sys.path.append(str(COMPONENTS / "brandpath"))      # appended, never ahead of this tool
import brandpath as BP                                # noqa: E402

TOKEN = re.compile(r"\{([a-z_]+)\}")
UPSTREAM = object()          # a field an earlier thinking layer makes at run time


def where_it_would_land(out_root, month, brand):
    """The same folder rule as the real run, read-only: <out>/<brand>/<month>."""
    return Path(out_root) / G._safe(brand) / month


def prompt_report(key, fields, forced_model=None):
    """-> (lines, problems) for one thinking layer."""
    s = CH.BY_KEY[key]
    lines, problems = [], []
    try:
        pf = R.latest_prompt(s["prompt"])
    except SystemExit as e:
        lines.append(f"  layer {s['n']} · {s['name']}  PROMPT MISSING — {e}")
        return lines, [f"layer {s['n']}: no prompt file for `{s['prompt']}`"]
    template = pf.read_text()
    wanted = list(dict.fromkeys(TOKEN.findall(template)))
    known = {k: v for k, v in fields.items() if v is not UPSTREAM}
    filled = R.fill(template, known)
    model, why = R.pick_model(key, len(filled), forced_model)
    lines.append(f"  layer {s['n']} · {s['name']}  prompt {pf.name} (sha {R.sha(pf)}) · "
                 f"would go to {model} ({why}) · {len(filled):,} characters")
    for name in wanted:
        if name not in fields:
            lines.append(f"      {{{name}}}  MISSING — the prompt asks for it and nothing fills it")
            problems.append(f"layer {s['n']}: `{{{name}}}` in {pf.name} is never filled")
            continue
        v = fields[name]
        if v is UPSTREAM:
            lines.append(f"      {{{name}}}  WAITS — made by an earlier layer at run time")
        elif not str(v or "").strip():
            lines.append(f"      {{{name}}}  EMPTY — the brand's record gives it nothing; "
                         "the prompt would read \"(none supplied)\"")
        elif "[UNFILLED" in str(v):
            lines.append(f"      {{{name}}}  MISSING — {str(v).strip()[:120]}")
            problems.append(f"layer {s['n']}: `{{{name}}}` — {str(v).strip()[:120]}")
        else:
            txt = str(v).strip()
            # a short value is shown whole: "OK — 20 characters" hides a brand
            # whose record gives the layer one line where another gives it forty
            lines.append(f"      {{{name}}}  OK — {len(txt):,} characters"
                         + (f": {txt!r}" if len(txt) < 80 and "\n" not in txt else ""))
    for name in fields:
        if name not in wanted:
            lines.append(f"      ({name} is handed over, and {pf.name} has no slot for it)")
    return lines, problems


def run(args, cal, out_root):
    """`cal` is the calendar module itself (it is `__main__` when run as a
    script, so it is handed in rather than imported a second time)."""
    import paths
    brand_root = paths.brand_root(args.brand)
    print(f"DRY RUN · {args.brand} · {args.month} — nothing is spent, nothing is written\n")
    if not brand_root.is_dir():
        print(f"  BLOCKED  there is no {rel(brand_root)}/")
        return 2

    # the brand
    ready = CH.readiness(brand_root)
    blocked = [L for L in ready if L["verdict"] == "blocked"]
    for L in ready:
        if L["verdict"] == "full":
            continue
        miss = ", ".join(r["path"] for r in L["needs"] if not r["have"]
                         and (r["required"] or L["verdict"] == "degraded"))
        print(f"  {L['verdict'].upper():8} layer {L['n']} {L['name']} — {miss}")
    print(f"  the brand: {sum(L['verdict'] == 'full' for L in ready)} layer(s) full, "
          f"{sum(L['verdict'] == 'degraded' for L in ready)} degraded, {len(blocked)} blocked")
    if blocked:
        print(f"\nBLOCKED — {args.brand} cannot run this chain yet. "
              f"`chain.py --check {args.brand}` says what each layer needs.")
        return 2

    catalogue_file = cal.catalogue_path(args.brand)
    catalogue = json.loads(catalogue_file.read_text())

    # layers 1 and 2 — code, really run, kept in memory
    hol_rows = H.in_month(args.month, lead_in_days=10)
    moments = cal.resolve_moments(brand_root, args.month)
    mj = json.loads(BP.brand_path(brand_root.name, "strategy", "moments.json", root=brand_root.parent).read_text())
    anchored_keys = set()
    for b in mj["avatars"].values():
        for m in b["moments"]:
            a = m.get("anchor") or {}
            anchored_keys |= {a.get("holiday"), a.get("through"), a.get("peak")}
    skeleton = cal.render_skeleton(args.month, hol_rows, moments, anchored_keys)
    inwin = [m for m in moments if m["in_month"]]
    print(f"  layer 1 · OK — {len(hol_rows)} public holiday(s) land in {args.month}")
    print(f"  layer 2 · OK — {len(inwin)} of the brand's moment(s) are in window")

    out_dir = where_it_would_land(out_root, args.month, args.brand)
    today = f"{datetime.date.today():%A, %-d %B %Y}"
    problems = []

    # layer 3
    sheet = cal.C_state_sheet(brand_root, catalogue, args.month)
    lines, p = prompt_report("cells", dict(today=today, month=args.month,
                                           state=sheet, skeleton=skeleton), args.model)
    print("\n".join(lines)); problems += p

    # layer 5 — cells and anchored come from a month on disk, if there is one
    cells, anchored = UPSTREAM, UPSTREAM
    on_disk = out_dir / "3-cells" / "cells.json"
    if on_disk.is_file():
        try:
            c = json.loads(on_disk.read_text())
            anchors = cal.anchor_arcs(args.month, moments, c, catalogue, brand_root, hol_rows)
            cells, anchored = json.dumps(c, indent=1), cal.render_anchors(anchors)
            print(f"  layer 4 · OK — {len(anchors)} send(s) would pin to real dates "
                  f"(from the cells already in {rel(out_dir)})")
        except Exception as e:                       # a dry run reports, it never dies
            print(f"  layer 4 · could not be rehearsed from {rel(on_disk)}: {e}")
    C = cal.C
    avatars = [a["key"] for a in cal.L_avatars(brand_root)]
    lines, p = prompt_report("concepts", dict(
        today=today, month=args.month, skeleton=skeleton, anchored=anchored, cells=cells,
        types=C.render_types(catalogue_file), products=C.render_products(brand_root),
        offers=C.render_offers(brand_root, avatars),
        coldness=C.coldness(brand_root, catalogue),
        findings="\n".join(C.findings(brand_root)) or "(no measured sends yet)",
        techniques=R.doctrine("techniques")), args.model)
    print("\n".join(lines)); problems += p

    # the types, against the element library and the brand's own catalogue
    keys = [t["key"] for t in catalogue["types"]]
    lib = G.library_ids()
    own = G.brand_type_ids(brand_root)
    only_brand = [k for k in keys if k not in lib]
    print(f"  the types · {len(keys)} in {rel(catalogue_file)} — "
          f"{len(keys) - len(only_brand)} in the element library (format/email)"
          + (f", {len(only_brand)} the brand's own: {', '.join(only_brand)}" if only_brand else "")
          + ("" if lib else " · THE LIBRARY COULD NOT BE READ"))
    stray = [k for k in keys if k not in lib and k not in own]
    if stray:
        problems.append("type(s) in neither the library nor the brand's catalogue: " + ", ".join(stray))

    print(f"\n  the month would land in {rel(out_dir)}/ and be filed to "
          f"{rel(G.repo_home(args.brand, args.month))}/")
    if problems:
        print(f"\nNOT READY — {len(problems)} thing(s) to fix:")
        for x in problems:
            print(f"  - {x}")
        return 1
    print("\nREADY — 0 model calls made, 0 files written.")
    return 0
