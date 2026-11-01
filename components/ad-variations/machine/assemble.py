"""Assemble the seven stage answers into variation-plan.json — THE CONTRACT (no
reader yet) — plus VARIATIONS.md, its Markdown mirror.

Everything arithmetic happens here, never in a prompt: costs are the recipe's
units × the rate in definitions/routes.json; forced gates come from the routes
a recipe uses; the planning spend is counted from the characters each stage
sent and got back.
"""
import datetime
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
SCHEMA = "ad-variations/1"
OPUS = {"in": 5.0, "out": 25.0}          # $ per 1M tokens, Claude Opus 5 (claude-api reference, cached 2026-06-24)
SONNET = {"in": 2.0, "out": 10.0}
PERSON = re.compile(r"\b(man|men|woman|women|person|people|face|reactor|creator|talent|him|her|he|she|guy|girl|actor|founder|model|roster|cast)\b", re.I)
PRODUCT = re.compile(r"\b(product|box|device|packshot|package|packaging|bottle|tube|jar|sku|set|kit|case|label)\b", re.I)


VIDEO_ROUTES = ("seedance-hf", "genjutsu-hf", "wan-animate-fal", "kling-mc-fal")


def _defs(name):
    return json.loads((COMP / "definitions" / name).read_text())


REPAIR_DIR = None          # run.py points this at the run folder so a repair is kept beside the answer
_repaired = {}


def parse(text):
    """A stage's JSON. When a model writes a stray straight quote inside a value the block
    will not parse; it is then handed to a small model to fix the punctuation only — the
    repair is kept beside the run as stage-json-repair-<sha>.json and reused, never silent."""
    from index import extract_json
    if not text or text.startswith("[dry run"):
        return {}
    try:
        return extract_json(text)
    except (ValueError, TypeError):
        pass
    import hashlib
    h = hashlib.sha256(text.encode()).hexdigest()[:12]
    if h in _repaired:
        return _repaired[h]
    cache = Path(REPAIR_DIR) / f"stage-json-repair-{h}.json" if REPAIR_DIR else None
    if cache and cache.is_file():
        _repaired[h] = json.loads(cache.read_text())
        return _repaired[h]
    import sys
    sys.path.insert(0, str(COMP.parent / "run-kit"))
    from run_kit import model as M
    ask = ("The JSON block below does not parse — most likely a straight double quote inside a string value. "
           "Return the same JSON with the punctuation fixed so it parses: escape or curl the inner quotes. "
           "Change no words, drop nothing, add nothing. Return only the JSON.\n\n" + text)
    try:
        fixed = extract_json(M.call(ask, M.TIERS["checks"], label="json-repair", timeout=900))
    except Exception:  # noqa: BLE001 — a failed repair leaves the stage empty and the problem is reported
        return {}
    _repaired[h] = fixed
    if cache:
        cache.write_text(json.dumps(fixed, indent=1, ensure_ascii=False) + "\n")
    return fixed


def section(stage_text, key, fallback=""):
    d = parse(stage_text)
    if not d.get(key):
        return fallback
    return json.dumps(d[key], indent=1, ensure_ascii=False) + ("\n\n" + fallback if fallback else "")


# ------------------------------------------------------------------ costs
def _routes():
    r = _defs("routes.json")
    return {x["id"]: x for x in r["routes"]}, r


def item_cost(route_id, units):
    routes, cfg = _routes()
    x = routes.get(route_id)
    try:
        units = float(units or 0)
    except (TypeError, ValueError):
        units = 0.0
    if not x:
        return {"usd": None, "hours": None, "note": f"unknown route {route_id!r}"}
    if x["usd_per_unit"] is None:
        return {"usd": None, "hours": round(x["hours_per_unit"] * max(units, 1), 2), "note": x.get("note")}
    usd = x["usd_per_unit"] * units
    if x.get("rolls"):
        usd *= x["rolls"]
    if x.get("overshoot"):
        usd *= 1 + cfg["video_overshoot"]
    hours = x["hours_per_unit"] * (units if x["unit"] in ("still", "clip-4s", "layer", "job", "shoot") else max(1, units / 4))
    return {"usd": round(usd, 2), "hours": round(hours, 2)}


def cost_recipes(recipes, shared):
    shared_cost = {}
    for s in shared:
        c = item_cost(s.get("route"), s.get("units"))
        s.update({"usd": c["usd"], "hours": c["hours"]})
        shared_cost[s.get("key")] = s
    for r in recipes:
        own_usd = own_h = 0.0
        routes_used = set()
        for m in r.get("make") or []:
            routes_used.add(m.get("route"))
            if m.get("shared"):
                m.update({"usd": 0.0, "hours": 0.0, "costed_in": m["shared"]})
                continue
            c = item_cost(m.get("route"), m.get("units"))
            m.update({"usd": c["usd"], "hours": c["hours"]})
            own_usd += c["usd"] or 0
            own_h += c["hours"] or 0
        uses = [s for s in shared if r.get("id") in (s.get("used_by") or [])]
        standalone = own_usd + sum(s.get("usd") or 0 for s in uses)
        test = r.get("cheaper_test") or None
        with_test = None
        if isinstance(test, dict) and test.get("route"):
            tc = item_cost(test["route"], test.get("units"))
            test["usd"] = tc["usd"]
            replaced = sum((m.get("usd") or 0) for m in r.get("make") or [] if m.get("route") == test.get("replaces_route"))
            with_test = round(own_usd - replaced + (tc["usd"] or 0), 2)
        r["cost"] = {"usd_own": round(own_usd, 2), "usd_standalone": round(standalone, 2),
                     "usd_with_test": with_test, "hours": round(0.25 + own_h, 2),
                     "shared_pieces": [s.get("key") for s in uses]}
        r["_routes"] = sorted(x for x in routes_used if x) + sorted({s.get("route") for s in uses if s.get("route")})
    return recipes


def forced_for(recipe, shared):
    gates = _defs("gates.json")["gates"]
    items = list(recipe.get("make") or []) + [s for s in shared if recipe.get("id") in (s.get("used_by") or [])]
    hits = {}
    for g in gates:
        for f in g.get("forced_by") or []:
            if f == "*":
                hits[g["id"]] = "every variation"
                continue
            if f == "chain":
                chained = [it for it in items if it.get("chain_order") not in (None, "", 0)]
                videos = [it for it in items if it.get("route") in VIDEO_ROUTES]
                if len(chained) >= 2 or (chained and len(videos) >= 2):
                    hits[g["id"]] = f"{len(chained)} chained clips"
                continue
            route, _, what = f.partition(":")
            for it in items:
                if it.get("route") != route:
                    continue
                text = f"{it.get('what', '')} {it.get('piece', '')}"
                if what == "person" and not PERSON.search(text):
                    continue
                if what == "product" and not PRODUCT.search(text):
                    continue
                hits[g["id"]] = f"{route}{' makes a ' + what if what else ''}"
    return hits


def forced_gates(stage5_text):
    d = parse(stage5_text)
    shared = d.get("shared") or []
    lines = []
    for r in d.get("recipes") or []:
        f = forced_for(r, shared)
        lines.append(f"- {r.get('id')}: " + ", ".join(f"{k} ({v})" for k, v in f.items()))
    return "\n".join(lines) or "(none)"


def join_for_gates(s3, s5):
    v, r = parse(s3), parse(s5)
    rec = {x.get("id"): x for x in r.get("recipes") or []}
    out = []
    for x in v.get("variations") or []:
        out.append({"id": x.get("id"), "title": x.get("title"), "changes": x.get("changes"),
                    "recipe": rec.get(x.get("id"))})
    for x in r.get("recipes") or []:
        if x.get("id", "").startswith("F"):
            out.append({"id": x["id"], "recipe": x})
    return json.dumps(out, indent=1, ensure_ascii=False) if out else s3


# ------------------------------------------------------------------ planning spend
def llm_cost(state, dry=False):
    tin = tout = 0
    usd = 0.0
    for k, s in (state.get("stages") or {}).items():
        ci = s.get("chars_in") or 0
        co = s.get("chars_out") or (6000 if dry else 0)
        rate = SONNET if "sonnet" in (s.get("model") or "") else OPUS
        tin += ci / 4
        tout += co / 4
        usd += ci / 4 / 1e6 * rate["in"] + co / 4 / 1e6 * rate["out"]
    return {"tokens_in": round(tin), "tokens_out": round(tout), "usd": round(usd, 2),
            "basis": "characters ÷ 4 per token, at API list price (Opus 5 $5 / $25 per million in / out). "
                     "claude -p also sends its own system prompt, mostly cached; not counted."}


# ------------------------------------------------------------------ the contract
def build(repo, brand, run, ix, out, texts, measurement, state):
    s = {k: parse(v) for k, v in texts.items()}
    problems = [f"{k}: the stage's answer did not parse, even after a repair — its part of the plan is empty"
                for k, v in s.items() if not v]
    vdefs = {v["id"]: v for v in _defs("variables.json")["variables"]}
    gdefs = {g["id"]: g for g in _defs("gates.json")["gates"]}
    edefs = {e["key"]: e for e in _defs("elements.json")["elements"]}
    calls = {}
    for c in s["stage2"].get("calls") or []:
        calls.setdefault(c.get("element"), []).append(c)
    elements = []
    for e in s["stage1"].get("elements") or []:
        cs = calls.get(e.get("key"), [])
        ranks = [c.get("impact_rank") for c in cs if isinstance(c.get("impact_rank"), int)]
        lever = any((c.get("call") or "").upper() == "LEVER" for c in cs)
        elements.append({**e, "name": edefs.get(e.get("key"), {}).get("name", e.get("key")),
                         "call": ("LEVER" if lever else "LOCK") if cs else None,
                         "calls": cs, "evidence": " · ".join(c.get("evidence") or "" for c in cs),
                         "impact_rank": min(ranks) if ranks else None,
                         "impact": next((c.get("impact") for c in cs if c.get("impact_rank") == (min(ranks) if ranks else None)), None),
                         "impact_basis": next((c.get("impact_basis") for c in cs if c.get("impact_basis")), None),
                         "needs_ruling": "; ".join(str(c["needs_ruling"]) for c in cs if c.get("needs_ruling")) or None})

    shared = s["stage5"].get("shared") or []
    recipes = cost_recipes(s["stage5"].get("recipes") or [], shared)
    rec_by = {r.get("id"): r for r in recipes}
    gates_by = {g.get("id"): g.get("apply") or [] for g in s["stage6"].get("gates") or []}
    links_by = {l.get("id"): l for l in s["stage7"].get("links") or []}

    def gates_for(vid):
        r = rec_by.get(vid) or {}
        forced = forced_for(r, shared) if r else {}
        out_g, seen = [], set()
        for g in gates_by.get(vid, []):
            gid = g.get("gate")
            seen.add(gid)
            out_g.append({"gate": gid, "name": gdefs.get(gid, {}).get("name", gid), "pass_line": g.get("pass_line"),
                          "check": g.get("check"), "auto_check": gdefs.get(gid, {}).get("check"), "forced": gid in forced})
        for gid, why in forced.items():
            if gid not in seen:
                out_g.append({"gate": gid, "name": gdefs.get(gid, {}).get("name", gid), "pass_line": gdefs.get(gid, {}).get("passes"),
                              "check": "automatic", "auto_check": gdefs.get(gid, {}).get("check"), "forced": True,
                              "added_by_machine": why})
        return out_g

    variations = []
    for v in s["stage3"].get("variations") or []:
        vid = v.get("id")
        for ch in v.get("changes") or []:
            if ch.get("variable") not in vdefs:
                problems.append(f"{vid}: change names {ch.get('variable')!r}, which is not in the Variable Index")
            else:
                ch["variable_name"] = vdefs[ch["variable"]]["name"]
        if len(v.get("changes") or []) > 2 and v.get("kind") != "control":
            problems.append(f"{vid}: changes {len(v['changes'])} variables — the one-lever rule allows two at most")
        r = rec_by.get(vid) or {}
        if not r:
            problems.append(f"{vid}: no recipe from stage 5")
        variations.append({**v, "recipe": {k: r.get(k) for k in ("reuse", "make", "cheaper_test", "seam_repair", "blocked_by")},
                           "cost": r.get("cost"), "gates": gates_for(vid), "congruence": links_by.get(vid)})

    formats = []
    for f in s["stage4"].get("formats") or []:
        for p in f.get("parts") or []:
            if p.get("variable") not in vdefs:
                problems.append(f"{f.get('id')}: part names {p.get('variable')!r}, not in the Variable Index")
        r = rec_by.get(f.get("id")) or {}
        formats.append({**f, "recipe": {k: r.get(k) for k in ("reuse", "make", "cheaper_test", "blocked_by")} if r else None,
                        "cost": r.get("cost"), "gates": gates_for(f.get("id")) if r else []})

    var_usd = sum((v.get("cost") or {}).get("usd_own") or 0 for v in variations)
    shared_usd = sum(x.get("usd") or 0 for x in shared)
    with_tests = sum(((v.get("cost") or {}).get("usd_with_test") if (v.get("cost") or {}).get("usd_with_test") is not None
                      else (v.get("cost") or {}).get("usd_own") or 0) for v in variations)
    hours = sum((v.get("cost") or {}).get("hours") or 0 for v in variations) + sum(x.get("hours") or 0 for x in shared)

    m = run.metrics or {}
    doc = {
        "schema": SCHEMA,
        "_what": "A variation plan for one proven ad. Production components read this file; nothing here has been generated.",
        "built": datetime.datetime.now().isoformat(timespec="seconds"),
        "brand": brand,
        "source": {"teardown_run": str(run.dir.relative_to(repo)), "post_id": m.get("id"), "url": m.get("url"),
                   "metrics": {k: m.get(k) for k in ("rank", "views", "likes", "saves", "comments", "shares", "duration_s", "posted", "caption")},
                   "video": (measurement or {}).get("video")},
        "index": {"path": f"runs/ad-variations/{brand}/variable-index/variable-index.json", "built": ix["built"], "runs": ix["runs"]},
        "measurement": {k: (measurement or {}).get(k) for k in ("duration", "fps", "shots", "soft_changes", "loudest", "quiet_windows_s", "skipped")},
        "beats": s["stage1"].get("beats") or [],
        "elements": elements,
        "record_vs_file": s["stage1"].get("record_vs_file") or [],
        "lever_order": s["stage2"].get("lever_order") or [],
        "variations": variations,
        "formats": formats,
        "shared": shared,
        "totals": {"variations": len(variations), "formats": len(formats), "usd": round(var_usd + shared_usd, 2),
                   "usd_with_tests": round(with_tests + shared_usd, 2), "hours": round(hours, 1),
                   "not_included": "creator fees, editor hours beyond the estimate, media spend, re-rolls beyond the costed rolls"},
        "damon_decides": s["stage2"].get("damon_decides") or [],
        "problems": problems,
        "run": {"stages": {k: {x: v.get(x) for x in ("prompt_name", "prompt_sha256_12", "model", "seconds", "chars_in", "chars_out")}
                           for k, v in (state.get("stages") or {}).items()},
                "llm_cost": llm_cost(state), "brand_files_read": state.get("brand_files_read")},
    }
    (out / "variation-plan.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    (out / "VARIATIONS.md").write_text(markdown(doc))
    return doc


def call_rows(elements):
    """One row per call (an element, or one part of it), levers first by rank."""
    rows = []
    for e in elements:
        for c in e.get("calls") or [{"call": e.get("call"), "evidence": e.get("evidence"), "impact_rank": e.get("impact_rank")}]:
            rows.append((e, c))
    return sorted(rows, key=lambda ec: ((ec[1].get("call") or "").upper() != "LEVER",
                                        ec[1].get("impact_rank") if isinstance(ec[1].get("impact_rank"), int) else 99))


def _money(x):
    return "—" if x is None else f"${x:,.2f}"


def markdown(d):
    m = d["source"]["metrics"]
    L = [f"# Ad Variations — {d['brand']} · {d['source']['post_id'] or d['source']['teardown_run']}", "",
         f"_Plan only — nothing generated. Built {d['built']} by `components/ad-variations`. Contract: `variation-plan.json` ({d['schema']})._", "",
         f"**The post:** #{m.get('rank')} · {m.get('views') and format(m['views'], ',.0f')} views · {m.get('saves') and format(m['saves'], ',.0f')} saves · "
         f"{m.get('duration_s')} s · “{m.get('caption')}” · {d['source'].get('url') or ''}", "",
         f"**Summary:** {d['totals']['variations']} variations + {d['totals']['formats']} new formats · machine cost {_money(d['totals']['usd'])} "
         f"({_money(d['totals']['usd_with_tests'])} if the TEST routes pass) · ≈{d['totals']['hours']} h · planning spend ≈{_money(d['run']['llm_cost']['usd'])}", ""]
    if d["problems"]:
        L += ["**Problems the machine found:**", *[f"- {p}" for p in d["problems"]], ""]
    L += ["## 1. Beats", "", "| # | Seconds | Section | Picture | Words | Sound | Attention |", "|---|---|---|---|---|---|---|"]
    for b in d["beats"]:
        L.append(f"| {b.get('n')} | {b.get('start')}–{b.get('end')} | {b.get('section')} | {b.get('picture')} | {b.get('words')} | {b.get('sound')} | {b.get('attention')} — {b.get('why') or ''} |")
    if d["record_vs_file"]:
        L += ["", "**Where the record and the file differ:**", *[f"- {x}" for x in d["record_vs_file"]]]
    L += ["", "## 2. Elements — lock or lever", "", "_Impact rank is an ESTIMATE; nothing in the corpus isolates one variable at a time._", "",
          "| Rank | Element · part | Cut | Call | Variables | What this ad does | Evidence |", "|---|---|---|---|---|---|---|"]
    for e, c in call_rows(d["elements"]):
        L.append(f"| {c.get('impact_rank') or ''} | {e.get('name')}{' · ' + c['part'] if c.get('part') else ''} | {c.get('cut') or 'both'} | "
                 f"{c.get('call')} | {', '.join(c.get('variables') or [])} | {c.get('what_this_ad_does') or e.get('what')} | {c.get('evidence')} |")
    L += ["", "## 3. Variations", ""]
    for v in d["variations"]:
        c = v.get("cost") or {}
        L += [f"### {v.get('id')} · {v.get('title')} — {_money(c.get('usd_own'))} · ≈{c.get('hours')} h", ""]
        for ch in v.get("changes") or []:
            L.append(f"- **Changes** {ch.get('variable')} ({ch.get('variable_name', '')}): {ch.get('from')} → {ch.get('to')}")
        L += [f"- **Locked:** {', '.join(v.get('locked') or [])}", f"- **Hypothesis:** {v.get('hypothesis')}",
              f"- **Confirms if:** {v.get('confirms_if')} · **Kills if:** {v.get('kills_if')}",
              f"- **Audience:** {json.dumps(v.get('audience'), ensure_ascii=False)}"]
        if v.get("needs_ruling"):
            L.append(f"- **Needs a ruling:** {v['needs_ruling']}")
        r = v.get("recipe") or {}
        for x in r.get("reuse") or []:
            L.append(f"- Reused as-is: `{x.get('seconds')}` — {x.get('what')}")
        for x in r.get("make") or []:
            chain = f" (clip {x['chain_order']}, starts from {x.get('start_frame')})" if x.get("chain_order") else ""
            L.append(f"- Made new: {x.get('what')}{chain} — {x.get('route')} × {x.get('units')} — {_money(x.get('usd')) if not x.get('costed_in') else 'shared ' + x['costed_in']}")
        if isinstance(r.get("cheaper_test"), dict):
            t = r["cheaper_test"]
            L.append(f"- TEST route: {t.get('route')} in place of {t.get('replaces_route')} — {_money(t.get('usd'))}; variation {_money(c.get('usd_with_test'))} — {t.get('why')}")
        if r.get("seam_repair"):
            L.append(f"- Seam repair (fallback only): {r['seam_repair']}")
        if r.get("blocked_by"):
            L.append(f"- Blocked by: {r['blocked_by']}")
        L.append("- Gates: " + "; ".join(f"{g['name']}{' (forced)' if g.get('forced') else ''}: {g.get('pass_line')}" for g in v.get("gates") or []))
        cg = v.get("congruence") or {}
        if cg:
            L.append(f"- Static: {(cg.get('static') or {}).get('format')} — {(cg.get('static') or {}).get('carries')} · "
                     f"Page: {(cg.get('page') or {}).get('format')} {(cg.get('page') or {}).get('section') or ''} — {(cg.get('page') or {}).get('carries')}")
        L.append("")
    L += ["## 4. New formats — untested", ""]
    for f in d["formats"]:
        c = f.get("cost") or {}
        L += [f"### {f.get('id')} · {f.get('name')} — {f.get('status')} — {_money(c.get('usd_own'))}", "", f"{f.get('what_the_viewer_sees')}", ""]
        for p in f.get("parts") or []:
            L.append(f"- {p.get('variable')} = {p.get('value')} — {p.get('evidence')}")
        L += [f"- Closest existing: {f.get('closest_existing')}", f"- Why: {f.get('why')}", f"- Seed footage: {f.get('seed_footage')}",
              f"- To make: {f.get('to_make')}", ""]
    L += ["## 5. Made once, used across the set", "", "| Key | Piece | Route | Cost | Used by |", "|---|---|---|---|---|"]
    for x in d["shared"]:
        L.append(f"| {x.get('key')} | {x.get('piece')} | {x.get('route')} × {x.get('units')} | {_money(x.get('usd'))} | {', '.join(x.get('used_by') or [])} |")
    L += ["", "## 6. the owner decides", "", *[f"- {x}" for x in d["damon_decides"]], "",
          f"_Planning spend: {d['run']['llm_cost']['tokens_in']:,} tokens in, {d['run']['llm_cost']['tokens_out']:,} out ≈ {_money(d['run']['llm_cost']['usd'])} — {d['run']['llm_cost']['basis']}_"]
    return "\n".join(L) + "\n"
