#!/usr/bin/env python3
"""shapes: the story shape of every winner, rolled up by money, pointed at the story presets that carry it.
Reached as `winners.py shapes <do>`. Any brand: the brand enters only as data.

    todo     winners with no shape call yet: each one's teardown files and the ids a call may use
    check    exit 1 when a winner is uncalled, or a call uses an arc, device or format id that is not in the lists
    build    shapes.json (the chain reads it), shapes.md (team copy) and page.html (the owner's page)

A CALL names, for one winner: its arc (an id from creative-controls' `arcs`, or null when the piece has no story turn),
how well it fits (clear: every arc beat in order; loose: the nearest arc, `why` says what differs; none: no arc), its
devices (ids from `story_devices`), its production, script and hook format (ids from video-production's
formats/names.json), its teller, an optional flag, and the transcript lines that prove the call. A call is a person's
(or a person's Claude's) read of the teardown the chain already wrote; nothing here reads a video or calls a model.

The record, runs/winners/<brand>/shapes/calls.json, holds only those calls plus the brand's own notes:
  {"calls": [{run, arc, fit, why, devices, production_format, script_format, hook_format, teller, flag, proof_lines}],
   "near": {arc: [[preset id, why], ...]}, "caveats": [...], "notes": [...]}
Everything else is read: the winners, their proof and teardown state from runs/winners/<brand>/winner-index.json, the
arcs and devices from components/creative-controls/controls.json, the presets from story_presets.json, outside
evidence from creative-controls/research/arc-evidence.json. Folds count once on the original; retires are listed, not
ranked. Money: cost per sale per arc = all spend / all sales; a winner with no spend on record has it derived as
sales x its own cost per sale, shown apart. Facts only, no verdict. Offline, stdlib only, no model, no spend."""
import argparse, html, json, math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))
from run_kit import paths  # noqa: E402
FITS = ("clear", "loose", "none")
CC = "components/creative-controls"
# The drawn curve of each arc: fortune from start to end, 0 low to 1 high (Vonnegut's axis). Drawing only.
CURVE = {"person-in-a-hole": [.6, .55, .25, .12, .5, .85], "rags-to-riches": [.12, .3, .45, .6, .75, .92],
         "icarus": [.3, .55, .8, .9, .5, .15], "cinderella": [.3, .6, .75, .3, .6, .92], "oedipus": [.6, .3, .5, .62, .25, .15],
         "story-circle": [.6, .45, .3, .2, .35, .55, .6], "save-the-cat": [.5, .45, .6, .7, .55, .2, .1, .5, .9],
         "heros-journey": [.5, .45, .55, .3, .2, .7, .85], "kishotenketsu": [.5, .55, .6, .9, .65],
         "but-therefore": [.5, .3, .55, .3, .6, .4, .75], "cold-open": [.9, .4, .5, .6, .8], "mystery-box": [.4, .42, .4, .44, .42, .95],
         "epiphany-bridge": [.35, .3, .15, .12, .55, .75, .9], "escalation-ladder": [.3, .45, .6, .8, .95, .4],
         "micro-drama": [.5, .2, .7, .3, .8], "two-sides": [.5, .7, .3, .55], "unreliable-narrator": [.8, .7, .5, .3, .5],
         "transformation-reveal": [.2, .2, .22, .2, .92, .95], None: [.5, .5, .5, .5, .5, .5]}


def home(root, brand):
    return root / "runs/winners" / brand / "shapes"


def jload(p, empty):
    return json.loads(p.read_text()) if p.is_file() else empty


def lists(root):
    c = jload(root / CC / "controls.json", {})
    n = jload(root / "components/video-production/formats/names.json", {})
    ids = lambda k: {x["id"] for x in (n.get(k) or {}).get("names") or []}
    return {"arcs": {a["id"]: a for a in c.get("arcs") or []}, "devices": {d["id"] for d in c.get("story_devices") or []},
            "production_format": ids("production_format"), "script_format": ids("script_format"), "hook_format": ids("hook_format"),
            "presets": jload(root / CC / "story_presets.json", {}).get("presets") or [],
            "evidence": jload(root / CC / "research/arc-evidence.json", {})}


def index(root, brand):
    return jload(root / "runs/winners" / brand / "winner-index.json", {"winners": []})


def ranked(ix):
    """The winners that carry money: not a fold, not a retire."""
    return [w for w in ix["winners"] if not w.get("copy_of") and (w.get("retire") or {}).get("call") not in ("fold", "retire")]


def problems(root, brand):
    L, calls = lists(root), {c["run"]: c for c in jload(home(root, brand) / "calls.json", {}).get("calls") or []}
    bad, known = [], set()
    for w in ranked(index(root, brand)):
        known.add(w["run"])
        c = calls.get(w["run"])
        if not c:
            bad.append("%s: no shape call" % w["label"]); continue
        if c.get("arc") is not None and c["arc"] not in L["arcs"]:
            bad.append("%s: arc %r is not in the arcs list" % (w["label"], c["arc"]))
        if c.get("fit") not in FITS or (c.get("arc") is None) != (c.get("fit") == "none"):
            bad.append("%s: fit must be clear or loose with an arc, none without one" % w["label"])
        bad += ["%s: device %r is not in the story devices" % (w["label"], d) for d in c.get("devices") or [] if d not in L["devices"]]
        for k in ("production_format", "script_format", "hook_format"):
            if c.get(k) is not None and c[k] not in L[k]:
                bad.append("%s: %s %r is not in the format names" % (w["label"], k, c[k]))
            if c.get(k) is None and k != "hook_format":
                bad.append("%s: no %s" % (w["label"], k))
        if not c.get("proof_lines"):
            bad.append("%s: no proof lines" % w["label"])
    bad += ["%s: called but not a ranked winner" % r for r in calls if r not in known]
    return bad


def todo(root, brand):
    calls = {c["run"] for c in jload(home(root, brand) / "calls.json", {}).get("calls") or []}
    return [{"run": w["run"], "label": w["label"], "sales": (w.get("proof") or {}).get("purchases"),
             "read": ["runs/video-teardown/_work/%s/stages/%s" % (w["run"], f) for f in ("1-transcript.md", "1-teardown.md", "1c-doctrine.md", "2-spec.md")]}
            for w in ranked(index(root, brand)) if w["run"] not in calls]


def sections(t):
    out = []
    for s in t.get("sections") or []:
        if isinstance(s, dict):
            s = s.get("id")
        elif isinstance(s, str) and s.startswith("{") and "'id': '" in s:
            s = s.split("'id': '")[1].split("'")[0]
        out.append(s)
    return out


def near_by_devices(presets, devs, arc, k=4):
    """Presets of another arc ranked by the devices they share with the arc's winners, each weighted by how many use it."""
    sc = []
    for q in presets:
        if q.get("arc") == arc or not q.get("devices"):
            continue
        shared = sorted(set(q["devices"]) & set(devs))
        if shared:
            sc.append((sum(devs[d] for d in shared) / math.sqrt(len(q["devices"])), q["id"], q.get("arc"), shared))
    sc.sort(key=lambda z: (-z[0], z[1]))
    return [{"preset": i, "arc": a, "shared_devices": s} for _, i, a, s in sc[:k]]


def build_data(root, brand):
    L, ix, rec = lists(root), index(root, brand), jload(home(root, brand) / "calls.json", {})
    calls = {c["run"]: c for c in rec.get("calls") or []}
    winners, uncalled = [], []
    for w in ranked(ix):
        c, t, p = calls.get(w["run"]), w.get("traits") or {}, w.get("proof") or {}
        if not c:
            uncalled.append(w["run"]); continue
        arc = c.get("arc")
        winners.append({"run": w["run"], "label": w["label"], "call": (w.get("retire") or {}).get("call"),
                        "folded_copies": [y["run"] for y in ix["winners"] if y.get("copy_of") == w["run"]],
                        "arc": arc, "arc_fit": c["fit"], "arc_why": c.get("why"),
                        "arc_beats": [b["beat"] for b in L["arcs"][arc]["beats"]] if arc else [],
                        "sections": sections(t), "devices": c.get("devices") or [],
                        "seconds": t.get("runtime"), "length": None if t.get("runtime") is None else ("short" if t["runtime"] <= 120 else "long"),
                        "production_format": c.get("production_format"), "script_format": c.get("script_format"), "hook_format": c.get("hook_format"),
                        "index_format": t.get("format"), "teller": c.get("teller") or "", "flag": c.get("flag"),
                        "awareness": "%s → %s" % (t.get("aware_in"), t.get("aware_out")),
                        "core_message": (w.get("message_read") or {}).get("core"), "proof_lines": c.get("proof_lines") or [],
                        "money": {"sales": p.get("purchases") or 0, "spend": p.get("spend"), "cost_per_sale": p.get("cpa"), "return": p.get("roas"),
                                  "first_ran": p.get("first_ran"), "last_ran": p.get("last_ran")},
                        "teardown": "runs/video-teardown/_work/%s/stages/" % w["run"]})
    groups = {}
    for w in winners:
        groups.setdefault(w["arc"] or "none", []).append(w)
    roll = []
    for arc, ws in groups.items():
        sales = sum(w["money"]["sales"] for w in ws)
        rec_sp = sum(w["money"]["spend"] or 0 for w in ws)
        der = sum(w["money"]["sales"] * (w["money"]["cost_per_sale"] or 0) for w in ws if not w["money"]["spend"])
        tot = rec_sp + der
        rev = sum((w["money"]["spend"] or w["money"]["sales"] * (w["money"]["cost_per_sale"] or 0)) * (w["money"]["return"] or 0) for w in ws)
        devs = {}
        for w in ws:
            for d in w["devices"]:
                devs[d] = devs.get(d, 0) + 1
        top = max(ws, key=lambda w: w["money"]["sales"])
        secs = sorted(w["seconds"] for w in ws if w["seconds"])
        a = L["arcs"].get(arc)
        roll.append({"arc": arc, "arc_name": a["name"] if a else "No arc (offer or argument only)", "arc_what": a["what"] if a else "No story turn.",
                     "winners": [w["run"] for w in ws], "count": len(ws), "clear_fits": sum(w["arc_fit"] == "clear" for w in ws),
                     "keep": sum(w["call"] == "keep" for w in ws), "watch": sum(w["call"] == "watch" for w in ws),
                     "founder_teller": sum(w["teller"].startswith("founder") for w in ws), "flagged": sum(bool(w["flag"]) for w in ws),
                     "sales": sales, "spend_recorded": round(rec_sp, 2), "spend_derived": round(der, 2), "spend_total": round(tot, 2),
                     "cost_per_sale": round(tot / sales, 2) if sales else None, "return": round(rev / tot, 2) if tot else None,
                     "best_cost_per_sale": min(w["money"]["cost_per_sale"] or 0 for w in ws), "worst_cost_per_sale": max(w["money"]["cost_per_sale"] or 0 for w in ws),
                     "top_winner": {"run": top["run"], "label": top["label"], "sales": top["money"]["sales"]},
                     "devices_used": dict(sorted(devs.items(), key=lambda z: -z[1])), "median_seconds": secs[len(secs) // 2] if secs else None,
                     "production_formats": sorted({w["production_format"] for w in ws if w["production_format"]}),
                     "presets_same_arc": [{"preset": q["id"], "name": q.get("name"), "devices": q.get("devices") or [],
                                           "production_format": (q.get("format") or {}).get("production_format"),
                                           "script_format": (q.get("format") or {}).get("script_format"), "seconds": q.get("seconds")}
                                          for q in L["presets"] if arc != "none" and q.get("arc") == arc],
                     "presets_near": [{"preset": i, "arc": next((q.get("arc") for q in L["presets"] if q["id"] == i), None), "why": y}
                                      for i, y in (rec.get("near") or {}).get(arc, [])],
                     "presets_sharing_most_devices": near_by_devices(L["presets"], devs, arc)})
    roll.sort(key=lambda r: -r["sales"])
    total = sum(r["sales"] for r in roll) or 1
    for r in roll:
        r["share_of_sales"] = round(r["sales"] / total, 3)
    pba = {}
    for q in L["presets"]:
        pba.setdefault(q.get("arc") or "none", []).append(q["id"])
    caveats = ["Money is the winner index's proof, snapshot %s: one window, no year-by-year split." % (ix.get("snapshot") or "unknown")]
    nospend = [w["label"] for w in winners if not w["money"]["spend"]]
    if nospend:
        caveats.append("%d winners have no spend on record; their spend is derived as sales x their own cost per sale: %s." % (len(nospend), ", ".join(nospend)))
    nolen = [w["label"] for w in winners if not w["seconds"]]
    if nolen:
        caveats.append("No length on record: %s." % ", ".join(nolen))
    caveats.append("The money belongs to the whole ad (offer, hook, teller, season), not to the shape alone.")
    return {"schema": "winner-shapes/v1", "brand": brand, "made": ix.get("built"), "snapshot": ix.get("snapshot"),
            "what": "The story shape of every winner, rolled up by arc with its money, pointed at the story presets that carry the same arc.",
            "sources": {"winners": "runs/winners/%s/winner-index.json" % brand, "calls": "runs/winners/%s/shapes/calls.json" % brand,
                        "arcs_devices": CC + "/controls.json", "presets": CC + "/story_presets.json",
                        "formats": "components/video-production/formats/names.json", "evidence": CC + "/research/arc-evidence.json"},
            "caveats": caveats + list(rec.get("caveats") or []), "notes": list(rec.get("notes") or []),
            "rollup": roll, "winners": winners, "uncalled": uncalled,
            "not_ranked": [{"run": w["run"], "label": w["label"], "why": (w.get("retire") or {}).get("why")}
                           for w in ix["winners"] if (w.get("retire") or {}).get("call") == "retire"],
            "presets_by_arc": pba, "external_evidence": L["evidence"]}


def curve(arc):
    ys = CURVE.get(arc) or CURVE[None]
    p = [(6 + i * (108 / (len(ys) - 1)), 40 - y * 34) for i, y in enumerate(ys)]
    d = "M%.1f,%.1f" % p[0]
    for i in range(len(p) - 1):
        a, b, c, e = p[i - 1] if i else p[i], p[i], p[i + 1], p[i + 2] if i + 2 < len(p) else p[i + 1]
        d += " C%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (b[0] + (c[0] - a[0]) / 6, b[1] + (c[1] - a[1]) / 6, c[0] - (e[0] - b[0]) / 6, c[1] - (e[1] - b[1]) / 6, c[0], c[1])
    return ('<svg class="curve" viewBox="0 0 120 46" aria-hidden="true"><line x1="4" y1="23" x2="116" y2="23" class="mid"/>'
            '<path d="%s" class="ln"/><circle cx="%.1f" cy="%.1f" r="3" class="dot"/></svg>' % (d, p[-1][0], p[-1][1]))


def marks(r, byrun):
    """The one-line marks under a shape card, read from the numbers and the calls."""
    out = []
    if r["count"] > 1 and r["founder_teller"] == r["count"]:
        out.append("all %d founder-told" % r["count"])
    if r["count"] > 1 and r["top_winner"]["sales"] / max(r["sales"], 1) > .6:
        out.append("%s of %s sales = %s" % ("{:,}".format(r["top_winner"]["sales"]), "{:,}".format(r["sales"]), r["top_winner"]["label"]))
    for f in sorted({byrun[x]["flag"] for x in r["winners"] if byrun[x]["flag"]}):
        out.append(f)
    return out


CSS = """/* layout: answer strip on top, then one card per story shape with its curve drawn, detail behind a tap */
:root{--bg:#f3f5f6;--card:#fff;--fg:#14202a;--mute:#5d6b76;--line:#d9e0e5;--acc:#0f7c86;--acc2:#d9efef;--warn:#b5541b;--warnbg:#fbeee5;--ok:#2f7d3c;
--disp:"Bricolage Grotesque",ui-sans-serif,system-ui,sans-serif;--body:Inter,ui-sans-serif,system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1519;--card:#172027;--fg:#e6edf1;--mute:#93a3ae;--line:#2a3640;--acc:#4cc3cc;--acc2:#183a3e;--warn:#f0995f;--warnbg:#3a2417;--ok:#7fd08b;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f1519;--card:#172027;--fg:#e6edf1;--mute:#93a3ae;--line:#2a3640;--acc:#4cc3cc;--acc2:#183a3e;--warn:#f0995f;--warnbg:#3a2417;--ok:#7fd08b;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--body);padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:24px 48px}
.wrap{max-width:1080px;margin:0 auto;display:grid;gap:22px}
h1{font-family:var(--disp);font-weight:800;font-size:clamp(26px,4vw,38px);margin:0;letter-spacing:-.01em;text-wrap:balance}
.sub{color:var(--mute);font-size:13px;display:flex;gap:14px;flex-wrap:wrap}
.answers{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.ans{background:var(--acc2);border-radius:12px;padding:14px 16px;display:grid;gap:4px}.ans.warn{background:var(--warnbg)}
.ans .k{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--mute)}.ans b{font-family:var(--disp);font-size:20px}.ans span{font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.shape{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;display:grid;gap:10px;min-width:0;align-content:start}
.top{display:flex;gap:12px;align-items:center}.curve{width:96px;height:38px;flex:none}
.curve .ln{fill:none;stroke:var(--acc);stroke-width:3;stroke-linecap:round}.curve .mid{stroke:var(--line);stroke-width:1;stroke-dasharray:3 3}.curve .dot{fill:var(--acc)}
h3{font-family:var(--disp);font-weight:600;font-size:19px;margin:0}.beats{font-size:12.5px;color:var(--mute)}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden}.bar i{display:block;height:100%;background:var(--acc)}
.nums{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}.nums b{display:block;font-size:18px;font-variant-numeric:tabular-nums}.nums span{font-size:11px;color:var(--mute)}
.note{font-size:12.5px;color:var(--ok)}
.cards{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--mute);width:44px}
.chip{font-size:12px;padding:3px 8px;border-radius:999px;border:1px solid var(--line);color:var(--mute)}.chip.on{background:var(--acc);border-color:var(--acc);color:var(--card)}.chip.gap{border-color:var(--warn);color:var(--warn)}
details summary{cursor:pointer;font-size:13px;color:var(--acc);font-weight:500}details summary:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.tw{overflow-x:auto;margin-top:8px}table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{text-align:left;padding:5px 6px;border-bottom:1px solid var(--line);white-space:nowrap}th{color:var(--mute);font-weight:500}
.n{text-align:right;font-variant-numeric:tabular-nums}.fl{color:var(--ok)}.devs{font-size:12px;color:var(--mute);margin-top:8px}
h2{font-family:var(--disp);font-weight:600;font-size:20px;margin:6px 0 0}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.ev{list-style:none;padding:0;margin:10px 0 0;display:grid;gap:8px}
.ev li{display:grid;grid-template-columns:150px minmax(0,1fr) auto;gap:4px 12px;font-size:13px;border-bottom:1px solid var(--line);padding-bottom:8px}
.ev li span{min-width:0}.ev a{color:var(--acc);font-size:12px}.ev em{grid-column:2/4;font-size:11px;color:var(--mute);font-style:normal}
.srow{display:grid;grid-template-columns:150px minmax(0,1fr) 30px 40px;gap:10px;align-items:center;font-size:13px;padding:3px 0}
.sb{height:8px;background:var(--line);border-radius:4px;overflow:hidden}.sb i{display:block;height:100%;background:var(--mute)}
.w{color:var(--acc);font-weight:600}.shead{font-size:11px;color:var(--mute);text-transform:uppercase;letter-spacing:.08em}
.props{margin:10px 0 0;padding-left:18px;font-size:13px;display:grid;gap:6px}
@media (max-width:600px){.answers{grid-template-columns:1fr}.ev li{grid-template-columns:1fr}.ev em{grid-column:1}.srow{grid-template-columns:110px minmax(0,1fr) 26px 34px}}"""


def page(d):
    e, R = html.escape, d["rollup"]
    byrun = {w["run"]: w for w in d["winners"]}
    if not R:
        return "<title>%s Winner Shapes</title><p>No shape calls yet.</p>" % e(d["brand"].upper())
    maxs, money = max(r["sales"] for r in R), lambda x: "${:,.0f}".format(x)
    cheap = sorted([r for r in R if r["cost_per_sale"]], key=lambda r: r["cost_per_sale"])[:2]
    gaps = [r for r in R if r["arc"] != "none" and not r["presets_same_arc"]]
    total = sum(r["sales"] for r in R)
    top = ('<section class="answers"><div class="ans"><span class="k">Most sales</span><b>%s</b><span>%s · %d%% · %s</span></div>'
           '<div class="ans"><span class="k">Cheapest per sale</span><b>%s</b><span>%s</span></div>'
           '<div class="ans%s"><span class="k">Card gap</span><b>%s</b><span>%s</span></div></section>') % (
        e(R[0]["arc_name"]), "{:,}".format(R[0]["sales"]), R[0]["share_of_sales"] * 100, money(R[0]["cost_per_sale"]),
        e(" · ".join("%s %s" % (r["arc_name"], money(r["cost_per_sale"])) for r in cheap)),
        e(" · ".join("{:,} sales".format(r["sales"]) for r in cheap)),
        " warn" if gaps else "", e(" · ".join(r["arc_name"] for r in gaps) or "none"),
        "✗ no story preset" if gaps else "✓ every shape has a card")
    cards = []
    for r in R:
        same = "".join('<span class="chip on">%s</span>' % e(p["preset"]) for p in r["presets_same_arc"]) or '<span class="chip gap">✗ no card</span>'
        near = "".join('<span class="chip">%s</span>' % e(p["preset"]) for p in r["presets_near"] or r["presets_sharing_most_devices"][:2])
        rows = "".join("<tr><td>%s%s</td><td class=n>%s</td><td class=n>%s</td><td>%s</td><td>%s s</td><td>%s</td></tr>" % (
            e(byrun[x]["label"]), " <b class=fl>★</b>" if byrun[x]["flag"] else "", "{:,}".format(byrun[x]["money"]["sales"]),
            money(byrun[x]["money"]["cost_per_sale"] or 0), byrun[x]["arc_fit"], byrun[x]["seconds"] or "?", e(byrun[x]["production_format"] or ""))
            for x in r["winners"])
        notes = "".join('<div class="note">%s</div>' % e(m) for m in marks(r, byrun))
        cards.append('<article class="shape"><div class="top">%s<div><h3>%s</h3><div class="beats">%s</div></div></div>'
                     '<div class="bar"><i style="width:%.1f%%"></i></div><div class="nums"><div><b>%s</b><span>sales · %d%%</span></div>'
                     '<div><b>%s</b><span>per sale</span></div><div><b>%sx</b><span>return</span></div><div><b>%d</b><span>winners</span></div></div>%s'
                     '<div class="cards"><span class="lbl">Cards</span>%s</div>%s<details><summary>Winners and devices</summary><div class="tw"><table><thead>'
                     '<tr><th>Winner</th><th>Sales</th><th>$/sale</th><th>Fit</th><th>Length</th><th>Made as</th></tr></thead><tbody>%s</tbody></table></div>'
                     '<div class="devs">%s</div></details></article>' % (
                         curve(r["arc"] if r["arc"] != "none" else None), e(r["arc_name"]), e(r["arc_what"]), r["sales"] / maxs * 100,
                         "{:,}".format(r["sales"]), r["share_of_sales"] * 100, money(r["cost_per_sale"] or 0), r["return"], r["count"], notes, same,
                         '<div class="cards"><span class="lbl">Near</span>%s</div>' % near if near else "", rows,
                         e(" · ".join("%s %d" % kv for kv in list(r["devices_used"].items())[:6]))))
    won = {r["arc"]: r["count"] for r in R}
    shelf = sorted(d["presets_by_arc"].items(), key=lambda z: -len(z[1]))
    most = max([len(p) for _, p in shelf] + [1])
    srows = "".join('<div class="srow"><span>%s</span><span class="sb"><i style="width:%.0f%%"></i></span><span class=n>%d</span><span class="n w">%s</span></div>' % (
        e(a if a != "none" else "no arc"), len(p) / most * 100, len(p), won.get(a) or "–") for a, p in shelf)
    ev = d.get("external_evidence") or {}
    li = lambda x: '<li><b>%s</b><span>%s</span><a href="%s" target="_blank" rel="noopener">%s</a><em>%s</em></li>' % (
        e(x.get("arc") or x.get("what") or ""), e(x.get("number", "")), e(x.get("url", "")), e(x.get("source", "")), e(x.get("strength", "")))
    evp = "".join('<div class="panel"><details><summary>%s</summary><ul class="ev">%s</ul></details></div>' % (t, "".join(li(x) for x in ev.get(k) or []))
                  for t, k in (("Sells most", "selling"), ("Watched most", "consumption")) if ev.get(k))
    notes = '<div class="panel"><details><summary>Proposed changes (not made)</summary><ol class="props">%s</ol></details></div>' % "".join(
        "<li>%s</li>" % e(n.get("short") or n.get("text")) for n in d["notes"]) if d["notes"] else ""
    return ('<title>%s Winner Shapes</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Inter:wght@400;500;600&display=swap">\n'
            '<style>%s</style><div class="wrap"><header><h1>%s Winner Shapes</h1><div class="sub"><span>%d winners · %s sales</span><span>proof %s</span>%s</div></header>'
            '%s<section class="grid">%s</section><h2>Cards held vs our wins</h2><div class="panel"><div class="srow shead"><span>Shape</span><span>Story presets</span>'
            '<span class=n>#</span><span class=n>Wins</span></div>%s</div>%s%s%s<div class="sub">%s<span>Data: runs/winners/%s/shapes/shapes.json</span></div></div>') % (
        e(d["brand"].upper()), CSS, e(d["brand"].upper()), len(d["winners"]), "{:,}".format(total), e(str(d.get("snapshot") or "")),
        '<span>%d not called yet</span>' % len(d["uncalled"]) if d["uncalled"] else "<span>Nothing needs you</span>",
        top, "".join(cards), srows, '<h2>Outside evidence</h2>' if evp else "", evp, notes,
        '<span>Not ranked: %s</span>' % e(", ".join(n["label"] for n in d["not_ranked"])) if d["not_ranked"] else "", e(d["brand"]))


def markdown(d):
    byrun, L = {w["run"]: w for w in d["winners"]}, []
    L.append("# %s winner shapes\n" % d["brand"].upper())
    L.append("The story shape of every winner, ranked by money, and the story presets that carry each shape. Data: `shapes.json` beside this file; "
             "calls: `calls.json`; built by `components/winners/shapes.py` (`winners.py shapes build`). Arc, device and format ids are the existing lists only. "
             "Folds count once on the original; retires are listed, not ranked.\n")
    L.append("## Shapes by sales\n")
    L.append("| arc | winners (clear fit) | sales | share | spend | $/sale | return | best–worst $/sale | founder teller | presets, same arc | presets, near |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in d["rollup"]:
        sp = "${:,.0f}".format(r["spend_total"]) + (" (${:,.0f} derived)".format(r["spend_derived"]) if r["spend_derived"] else "")
        L.append("| %s | %d (%d) | %s | %d%% | %s | $%.2f | %.2fx | $%.0f–$%.0f | %d | %s | %s |" % (
            r["arc"], r["count"], r["clear_fits"], "{:,}".format(r["sales"]), r["share_of_sales"] * 100, sp, r["cost_per_sale"] or 0, r["return"] or 0,
            r["best_cost_per_sale"], r["worst_cost_per_sale"], r["founder_teller"], ", ".join(p["preset"] for p in r["presets_same_arc"]) or "–",
            ", ".join(p["preset"] for p in r["presets_near"]) or "–"))
    L.append("\nBy cost per sale (lowest first): " + " · ".join("%s $%.0f" % (r["arc"], r["cost_per_sale"]) for r in sorted(d["rollup"], key=lambda r: r["cost_per_sale"] or 0)) + "\n")
    L.append("## Each shape\n")
    for r in d["rollup"]:
        L.append("### %s — %s\n" % (r["arc"], r["arc_name"]))
        if r["arc"] != "none":
            L.append("Arc beats: " + " → ".join(byrun[r["winners"][0]]["arc_beats"]) + "\n")
        L.append("Devices used (winners using it): " + ", ".join("%s %d" % kv for kv in r["devices_used"].items()) + "\n")
        L.append("Production formats: %s · median length %s s\n" % (", ".join(r["production_formats"]), r["median_seconds"]))
        for p in r["presets_same_arc"]:
            L.append("- preset, same arc: **%s** (%s, %s, %s s) devices %s" % (p["preset"], p["production_format"], p["script_format"], p["seconds"], ", ".join(p["devices"]) or "–"))
        for p in r["presets_near"]:
            L.append("- preset, near: **%s** (%s): %s" % (p["preset"], p["arc"], p["why"]))
        if not r["presets_same_arc"]:
            L.append("- no story preset carries this arc")
        L.append("")
        L.append("| winner | call | fit | sales | $/sale | length | production · script · hook | devices |")
        L.append("|---|---|---|---|---|---|---|---|")
        for x in r["winners"]:
            w, m = byrun[x], byrun[x]["money"]
            L.append("| %s | %s | %s | %s | $%.0f | %s s | %s · %s · %s | %s |" % (w["label"], w["call"], w["arc_fit"], "{:,}".format(m["sales"]), m["cost_per_sale"] or 0,
                     w["seconds"] or "?", w["production_format"], w["script_format"], w["hook_format"] or "–", ", ".join(w["devices"])))
        L.append("")
        for x in r["winners"]:
            w = byrun[x]
            L.append("**%s** — %s%s" % (w["label"], w["arc_why"], " *%s.*" % w["flag"] if w["flag"] else ""))
            if w["teller"].startswith("founder"):
                L.append("- proof lines: `shapes.json` → winners → proof_lines (founder-told; kept out of the team copy)")
            else:
                L += ["- %s" % q for q in w["proof_lines"]]
            L.append("")
    if d["uncalled"]:
        L.append("## Not called yet\n")
        L += ["- `%s`" % r for r in d["uncalled"]]
        L.append("")
    if d["not_ranked"]:
        L.append("## Not ranked\n")
        L += ["- %s (`%s`): %s." % (n["label"], n["run"], n["why"]) for n in d["not_ranked"]]
        L.append("")
    L.append("## Caveats\n")
    L += ["- %s" % c for c in d["caveats"]]
    won = {r["arc"]: r["count"] for r in d["rollup"]}
    L.append("\n## Story presets held against wins\n")
    L.append("| arc | story presets held | winners |")
    L.append("|---|---|---|")
    for a in sorted(set(d["presets_by_arc"]) | set(won), key=lambda a: -(won.get(a, 0) * 100 + len(d["presets_by_arc"].get(a, [])))):
        L.append("| %s | %d | %d |" % (a if a != "none" else "no arc", len(d["presets_by_arc"].get(a, [])), won.get(a, 0)))
    ev = d.get("external_evidence") or {}
    if ev:
        L.append("\n## Outside evidence (brand-free)\n")
        L.append("From `%s/research/arc-evidence.json` (%s). %s\n" % (CC, ev.get("state", ""), ev.get("thin", "")))
        L.append("| arc / form | what | number | source | strength |")
        L.append("|---|---|---|---|---|")
        for k in ("selling", "consumption"):
            for x in ev.get(k) or []:
                L.append("| %s | %s | %s | [%s](%s) | %s |" % (x.get("arc") or x.get("what"), k, x.get("number"), x.get("source"), x.get("url"), x.get("strength")))
    if d["notes"]:
        L.append("\n## Proposed wiring (not done; each needs its owner)\n")
        L += ["%d. %s" % (i + 1, n.get("text")) for i, n in enumerate(d["notes"])]
    return "\n".join(L) + "\n"


def build(root, brand):
    d, h = build_data(root, brand), home(root, brand)
    h.mkdir(parents=True, exist_ok=True)
    (h / "shapes.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    (h / "shapes.md").write_text(markdown(d))
    (h / "page.html").write_text(page(d))
    return h


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("do", choices=("todo", "check", "build"))
    ap.add_argument("--brand", required=True)
    ap.add_argument("--root", default=str(paths.repo(__file__)))
    a = ap.parse_args(argv)
    root = Path(a.root)
    if not (root / "runs/winners" / a.brand / "winner-index.json").is_file():
        print("No winner index for %s yet: build it first with components/video-writing/machine/winner_index.py build --brand %s" % (a.brand, a.brand))
        return 1
    if a.do == "todo":
        t = todo(root, a.brand)
        L = lists(root)
        print("%d winners with no shape call. Arc ids: %s" % (len(t), ", ".join(sorted(L["arcs"]))))
        for x in t:
            print("- %s (%s sales) %s\n    read: %s" % (x["label"], x["sales"], x["run"], "  ".join(x["read"])))
        return 0
    if a.do == "check":
        bad = problems(root, a.brand)
        print("\n".join(bad) if bad else "every winner has a whole shape call")
        return 1 if bad else 0
    h = build(root, a.brand)
    for f in ("shapes.json", "shapes.md", "page.html"):
        print("  -> %s" % (h / f).relative_to(root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
