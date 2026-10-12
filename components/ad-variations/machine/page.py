"""The Ad Variations page — how the component works, every prompt verbatim,
every run on disk as variation cards, and the Variable Index as a filterable
tab. Rebuilt from files, never retyped:

    python3 machine/run.py page

Writes page/ad-variations.html (the artifact source) and
AD-VARIATIONS-damon.md (the Markdown mirror) inside the component.
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
E = html.escape
CONTRACT = "variation-plan.json"
OLD_CONTRACT = "variations.json"          # runs made before 2026-10-08 — read, never written

STRIP = [
    ("index", "Variable Index", "Every teardown the brand has, counted", "rule reads + a Sonnet coder per post, cached", "stage0c"),
    ("stage0", "Measure", "The file's own clock: cuts, loudness, fps", "ffmpeg — no model, $0", None),
    ("stage1", "Anatomy → elements", "The ad by the second, on nineteen fixed elements", "Claude Opus", "stage1"),
    ("stage2", "Locks vs levers", "Keep or test each element, ranked by estimated impact", "Claude Opus · numbers from the index", "stage2"),
    ("stage3", "Variation matrix", "N variations, one lever each, highest impact first", "Claude Opus", "stage3"),
    ("stage4", "New formats", "Proven parts recombined into formats not yet run", "Claude Opus", "stage4"),
    ("stage5", "Merge recipe", "Seconds reused, what AI makes, route — the machine prices it", "Claude Opus · $ from routes.json", "stage5"),
    ("stage6", "QC gates", "The gates each variation must pass", "Claude Opus · forced gates from routes", "stage6"),
    ("stage7", "Congruence", "The static and page section each variation feeds", "Claude Opus", "stage7"),
]


def money(x):
    return "—" if x is None else f"${x:,.2f}"


def pct(x):
    return "—" if x is None else f"{x * 100:.1f}%"


def contract_files(repo):
    """Every run's contract file, one per run folder. variation-plan.json wins; runs
    made before the rename (SI-133 (ad-variations plan name)) still carry the old name."""
    root = Path(repo) / "runs" / "ad-variations"
    found = {vj.parent: vj for vj in root.glob(f"*/*/{OLD_CONTRACT}")}
    found.update({vj.parent: vj for vj in root.glob(f"*/*/{CONTRACT}")})
    return [found[k] for k in sorted(found)]


def load(repo):
    from run_kit import prompts as P
    prompts = []
    for key, name, *_ in STRIP:
        pk = {"index": "stage0c"}.get(key, key)
        if pk == "stage0":
            continue
        f = P.latest(COMP / "prompts", pk)
        prompts.append({"key": pk, "name": name, "file": str(f.relative_to(COMP)), "text": f.read_text()})
    runs = []
    for vj in contract_files(repo):
        runs.append(json.loads(vj.read_text()))
    runs.sort(key=lambda d: (d["source"]["metrics"].get("rank") or 999))
    indexes = {}
    for ij in sorted((Path(repo) / "runs" / "ad-variations").glob("*/variable-index/variable-index.json")):
        ix = json.loads(ij.read_text())
        for v in ix["variables"]:
            for x in v["values"]:
                x.pop("runs", None)
        ix.pop("per_run", None)
        indexes[ix["brand"]] = ix
    cal = json.loads((COMP / "notes" / "calibration.json").read_text()) if (COMP / "notes" / "calibration.json").is_file() else None
    return prompts, runs, indexes, cal


# ------------------------------------------------------------------ sections
def strip_html():
    cells = []
    for key, name, what, how, _ in STRIP:
        tag = "index" if key == "index" else key.replace("stage", "")
        cells.append(f'<li class="st"><span class="st-n">{E(tag)}</span><b>{E(name)}</b><span>{E(what)}</span><em>{E(how)}</em></li>')
    return f'<ol class="strip">{"".join(cells)}</ol>'


def run_html(d):
    m = d["source"]["metrics"]
    t = d["totals"]
    vid = d["source"].get("post_id") or d["source"]["teardown_run"]
    head = (f'<header class="run-h"><div><p class="eyebrow">{E(d["brand"].upper())} · post #{E(str(m.get("rank")))} · TikTok {E(str(vid))}</p>'
            f'<h3>“{E(str(m.get("caption") or ""))}”</h3></div>'
            f'<dl class="kpis"><div><dt>Views</dt><dd>{(m.get("views") or 0) / 1e6:.1f}M</dd></div>'
            f'<div><dt>Saves</dt><dd>{(m.get("saves") or 0) / 1e3:.1f}K</dd></div>'
            f'<div><dt>Length</dt><dd>{E(str(m.get("duration_s")))} s</dd></div>'
            f'<div><dt>Plan</dt><dd>{t["variations"]} + {t["formats"]}</dd></div>'
            f'<div><dt>Machine cost</dt><dd>{money(t["usd"])}</dd></div>'
            f'<div><dt>With TEST routes</dt><dd>{money(t["usd_with_tests"])}</dd></div>'
            f'<div><dt>Work</dt><dd>≈{t["hours"]} h</dd></div>'
            f'<div><dt>Planning spend</dt><dd>{money(d["run"]["llm_cost"]["usd"])}</dd></div></dl></header>')
    probs = "".join(f"<li>{E(p)}</li>" for p in d.get("problems") or [])
    probs = f'<div class="warn"><b>What the machine\'s own checks found</b><ul>{probs}</ul></div>' if probs else ""

    import assemble
    rows = []
    for e, c in assemble.call_rows(d["elements"]):
        call = (c.get("call") or "").upper()
        ev = e.get("variables") or {}
        ids = c.get("variables") or list(ev)
        vars_ = "<br>".join(f'<code>{E(k)}</code> {E(str(ev.get(k, "")))}' for k in ids)
        part = f' · {E(str(c["part"]))}' if c.get("part") else ""
        rows.append(f'<tr><td class="num">{E(str(c.get("impact_rank") or ""))}</td><td><b>{E(e.get("name") or e.get("key"))}</b>{part}'
                    f'<div class="sub">{E(str(e.get("seconds") or ""))} · {E(str(c.get("cut") or "both"))} cut</div></td>'
                    f'<td><span class="pill {call.lower()}">{E(call or "—")}</span></td><td>{E(str(c.get("what_this_ad_does") or e.get("what") or ""))}</td>'
                    f'<td class="vars">{vars_}</td><td>{E(str(c.get("evidence") or ""))}'
                    + (f'<div class="sub">{E(str(c["impact_basis"]))}</div>' if c.get("impact_basis") and call == "LEVER" else "")
                    + (f'<div class="rule">Needs a ruling: {E(str(c["needs_ruling"]))}</div>' if c.get("needs_ruling") else "")
                    + "</td></tr>")
    table = ('<div class="tw"><table class="grid"><thead><tr><th>Rank</th><th>Element · part</th><th>Call</th><th>What this ad does</th>'
             f'<th>Index values</th><th>Evidence</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')

    cards = [variation_card(v) for v in d["variations"]]
    fmts = [format_card(f) for f in d["formats"]]
    shared = "".join(f'<tr><td><code>{E(str(s.get("key")))}</code></td><td>{E(str(s.get("piece")))}</td><td><code>{E(str(s.get("route")))}</code> × {E(str(s.get("units")))}</td>'
                     f'<td class="num">{money(s.get("usd"))}</td><td>{E(", ".join(s.get("used_by") or []))}</td></tr>' for s in d["shared"])
    beats = "".join(f'<tr><td class="num">{E(str(b.get("n")))}</td><td class="num">{E(str(b.get("start")))}–{E(str(b.get("end")))}</td>'
                    f'<td>{E(str(b.get("section") or ""))}</td><td>{E(str(b.get("picture") or ""))}</td><td>{E(str(b.get("words") or ""))}</td>'
                    f'<td>{E(str(b.get("sound") or ""))}</td><td><span class="att">{E(str(b.get("attention") or ""))}</span> {E(str(b.get("why") or ""))}</td></tr>'
                    for b in d["beats"])
    rvf = "".join(f"<li>{E(str(x))}</li>" for x in d.get("record_vs_file") or [])
    decides = "".join(f"<li>{E(str(x))}</li>" for x in d.get("damon_decides") or [])
    return f'''<article class="run" id="run-{E(str(vid))}">{head}{probs}
<h4>Elements — lock or lever</h4><p class="note">Rank is an ESTIMATE: nothing in the corpus isolates one variable at a time. Index values use the Variable Index ids.</p>{table}
<h4>Variations</h4><div class="cards">{"".join(cards)}</div>
<h4>New formats — untested</h4><div class="cards">{"".join(fmts)}</div>
<h4>Made once, used across the set</h4><div class="tw"><table class="grid"><thead><tr><th>Key</th><th>Piece</th><th>Route × units</th><th>Cost</th><th>Used by</th></tr></thead><tbody>{shared}</tbody></table></div>
<details class="more"><summary>The ad beat by beat, on the file's clock</summary><div class="tw"><table class="grid"><thead><tr><th>#</th><th>Seconds</th><th>Section</th><th>Picture</th><th>Words</th><th>Sound</th><th>Attention</th></tr></thead><tbody>{beats}</tbody></table></div>
{f"<p><b>Where the record and the file differ</b></p><ul>{rvf}</ul>" if rvf else ""}</details>
<div class="decides"><h4>the owner decides</h4><ul>{decides}</ul></div>
<p class="foot">Contract: <code>runs/ad-variations/{E(d["brand"])}/{E(Path(d["source"]["teardown_run"]).name)}/variation-plan.json</code> · built {E(d["built"])}</p>
</article>'''


def recipe_html(r, c):
    if not r:
        return ""
    reuse = "".join(f'<li><code>{E(str(x.get("seconds")))}</code> {E(str(x.get("what")))}</li>' for x in r.get("reuse") or [])
    make = "".join(f'<li>{"<span class=route>clip " + E(str(x["chain_order"])) + " · </span>" if x.get("chain_order") else ""}{E(str(x.get("what")))} '
                   f'<span class="route">{E(str(x.get("route")))} × {E(str(x.get("units")))}</span> '
                   f'<b>{"shared " + E(str(x["costed_in"])) if x.get("costed_in") else money(x.get("usd"))}</b>'
                   + (f'<div class="sub">starts from: {E(str(x["start_frame"]))}</div>' if x.get("chain_order") and x.get("start_frame") else "")
                   + '</li>' for x in r.get("make") or [])
    t = r.get("cheaper_test")
    test = (f'<p class="test">TEST route: <code>{E(str(t.get("route")))}</code> in place of <code>{E(str(t.get("replaces_route")))}</code> — '
            f'{money(t.get("usd"))}; variation {money((c or {}).get("usd_with_test"))}. {E(str(t.get("why") or ""))}</p>') if isinstance(t, dict) and t.get("route") else ""
    blocked = f'<p class="rule">Blocked by: {E(str(r["blocked_by"]))}</p>' if r.get("blocked_by") else ""
    if r.get("seam_repair"):
        blocked += f'<p class="test">Seam repair, only if a clip cannot be made again: {E(str(r["seam_repair"]))}</p>'
    return (f'<div class="recipe"><div><span class="lbl">Reused as-is</span><ul>{reuse or "<li>—</li>"}</ul></div>'
            f'<div><span class="lbl">Made new</span><ul>{make or "<li>nothing</li>"}</ul></div></div>{test}{blocked}')


def variation_card(v):
    c = v.get("cost") or {}
    ch = "".join(f'<li><code>{E(str(x.get("variable")))}</code> {E(str(x.get("variable_name") or ""))}: '
                 f'<s>{E(str(x.get("from")))}</s> → <b>{E(str(x.get("to")))}</b></li>' for x in v.get("changes") or [])
    aud = v.get("audience") or {}
    gates = "".join(f'<li><b>{E(str(g.get("name")))}</b>{" <i>forced</i>" if g.get("forced") else ""} — {E(str(g.get("pass_line") or ""))}</li>' for g in v.get("gates") or [])
    cg = v.get("congruence") or {}
    st, pg = cg.get("static") or {}, cg.get("page") or {}
    return f'''<section class="card{" ctrl" if v.get("kind") == "control" else ""}">
<header><span class="vid">{E(str(v.get("id")))}</span><h5>{E(str(v.get("title")))}</h5><span class="cost">{money(c.get("usd_own"))} · ≈{E(str(c.get("hours")))} h</span></header>
<ul class="changes">{ch or "<li>No change — the control</li>"}</ul>
<p>{E(str(v.get("hypothesis") or ""))}</p>
<p class="sub">Confirms if: {E(str(v.get("confirms_if") or "—"))} · Kills if: {E(str(v.get("kills_if") or "—"))}</p>
<p class="sub">Aimed at: {E(str(aud.get("avatar") or ""))} {E(str(aud.get("sub_avatar") or ""))} · {E(str(aud.get("cut") or ""))} cut</p>
{f'<p class="rule">Needs a ruling: {E(str(v["needs_ruling"]))}</p>' if v.get("needs_ruling") else ""}
{recipe_html(v.get("recipe"), c)}
<details><summary>Gates ({len(v.get("gates") or [])}) and congruence</summary><ul class="gates">{gates}</ul>
<p class="sub"><b>Static:</b> {E(str(st.get("format") or "—"))} — {E(str(st.get("carries") or ""))}</p>
<p class="sub"><b>Page:</b> {E(str(pg.get("format") or "—"))} {E(str(pg.get("section") or ""))} — {E(str(pg.get("carries") or ""))}</p></details>
</section>'''


def format_card(f):
    c = f.get("cost") or {}
    parts = "".join(f'<li><code>{E(str(p.get("variable")))}</code> {E(str(p.get("value")))} <span class="sub">— {E(str(p.get("evidence")))}</span></li>' for p in f.get("parts") or [])
    return f'''<section class="card new">
<header><span class="vid">{E(str(f.get("id")))}</span><h5>{E(str(f.get("name")))}</h5><span class="cost">{money(c.get("usd_own")) if c else ""}</span></header>
<p class="badge">NEW — untested</p><p>{E(str(f.get("what_the_viewer_sees") or ""))}</p><ul class="changes">{parts}</ul>
<p class="sub">{E(str(f.get("why") or ""))}</p><p class="sub"><b>Closest existing:</b> {E(str(f.get("closest_existing") or ""))}</p>
<p class="sub"><b>Seed footage:</b> {E(str(f.get("seed_footage") or ""))} · <b>To make:</b> {E(str(f.get("to_make") or ""))}</p>
{recipe_html(f.get("recipe"), c)}</section>'''


def prompts_html(prompts):
    out = []
    for p in prompts:
        out.append(f'<details class="prompt" id="p-{E(p["key"])}"><summary><b>{E(p["name"])}</b><span>{E(p["file"])} · {len(p["text"].split()):,} words</span></summary><pre>{E(p["text"])}</pre></details>')
    return "".join(out)


def calibration_html(cal):
    if not cal:
        return "<p>Calibration against the hand-made spec has not run yet.</p>"
    rows = "".join(f'<tr><td><b>{E(r["what"])}</b></td><td>{E(r["hand"])}</td><td>{E(r["auto_v1"])}</td><td>{E(r.get("change", ""))}</td><td>{E(r.get("auto_v2", ""))}</td></tr>' for r in cal["rows"])
    return (f'<p class="lede2">{E(cal["summary"])}</p><div class="tw"><table class="grid"><thead><tr><th>What</th><th>Hand-made Asset 01</th>'
            f'<th>Automatic, first prompts</th><th>What changed in the prompts</th><th>Automatic, after</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'<p class="foot">Hand-made spec: {E(cal["golden"])}</p>')


HOWTO = """
<div class="howto">
<section><h4>Say it</h4><p class="say">“Run ad variations on &lt;brand&gt; post &lt;post id&gt;.”</p>
<p>Any post that has been torn down works — a post id, or the name of its teardown run. Add what you want: “twelve variations”, “only paid cuts”, “use the relaunch plan for the page sections”.</p></section>
<section><h4>What the session does</h4><ol>
<li>Checks the post has a finished teardown (triage, record, doctrine, audience, spec). If it doesn't, it runs the teardown first.</li>
<li>Refreshes the brand's Variable Index — only posts torn down since the last build get coded, so it takes seconds when nothing is new.</li>
<li>Runs a free dry run: every prompt filled, nothing spent, the planning cost estimated.</li>
<li>Runs the seven stages, then adds the run to this page and republishes it — same link.</li></ol></section>
<section><h4>What comes back</h4><ul>
<li>A new set of cards on the Test runs tab: locks and levers, the variations, new formats, costs, gates.</li>
<li><code>variation-plan.json</code> in the run folder — the plan; no component reads it yet.</li>
<li>A Markdown copy for the team beside it.</li></ul></section>
<section><h4>Where it stops and asks you</h4><ul>
<li>Anything under “the owner decides” — likeness, voice cloning, public figures, the hero SKU, the offer.</li>
<li>A variation marked “Needs a ruling” is planned but never produced until you rule.</li></ul></section>
</div>"""


CSS = r"""
:root{--ground:#F2F3EF;--card:#FFFFFF;--ink:#1C211E;--mut:#5B655F;--line:#D5D9D2;--hair:#E6E9E3;--accent:#0F6A5B;--accent-bg:#E1EFEA;
--lock:#34407A;--lock-bg:#E3E6F4;--lever:#9A5410;--lever-bg:#F6EADC;--new:#6B3E8C;--new-bg:#EFE6F5;--bad:#9B2C2C;--bad-bg:#F8E5E3;--bar:#0F6A5B}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--ground:#121614;--card:#1A201D;--ink:#E4E9E5;--mut:#9AA59E;--line:#2E3632;--hair:#252C28;--accent:#5DC0AA;--accent-bg:#183229;
--lock:#A9B4F0;--lock-bg:#232A48;--lever:#F0B070;--lever-bg:#3A2A18;--new:#D1A8EE;--new-bg:#322540;--bad:#F0A0A0;--bad-bg:#3C1E1E;--bar:#5DC0AA}}
:root[data-theme="dark"]{color-scheme:dark;--ground:#121614;--card:#1A201D;--ink:#E4E9E5;--mut:#9AA59E;--line:#2E3632;--hair:#252C28;--accent:#5DC0AA;--accent-bg:#183229;
--lock:#A9B4F0;--lock-bg:#232A48;--lever:#F0B070;--lever-bg:#3A2A18;--new:#D1A8EE;--new-bg:#322540;--bad:#F0A0A0;--bad-bg:#3C1E1E;--bar:#5DC0AA}
*{box-sizing:border-box}body{background:var(--ground);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,sans-serif;margin:0}
.wrap{max-width:1180px;margin:0 auto;padding-inline:20px;padding-block:28px 60px}
h1,h2,h3,h4,h5{font-family:"Bricolage Grotesque","IBM Plex Sans",sans-serif;text-wrap:balance;margin:0}
h1{font-size:40px;letter-spacing:-.01em}h2{font-size:26px;margin-bottom:6px}h3{font-size:22px}h4{font-size:18px;margin:26px 0 10px}h5{font-size:16px}
code,pre,.route,.st-n,.vid,.eyebrow,.lbl,dt{font-family:"IBM Plex Mono",ui-monospace,monospace}
code{font-size:12.5px;background:var(--hair);padding:1px 5px;border-radius:4px}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin:0 0 6px}
.lede{max-width:72ch;color:var(--mut);font-size:16px;margin:8px 0 18px}.lede2{max-width:80ch}
nav.tabs{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--ground);display:flex;flex-wrap:wrap;gap:6px;padding:10px 0;border-bottom:1px solid var(--line);margin-bottom:22px}
nav.tabs a{font-size:14px;text-decoration:none;color:var(--ink);padding:6px 12px;border-radius:99px;border:1px solid var(--line);background:var(--card)}
nav.tabs a[aria-selected="true"]{background:var(--ink);color:var(--ground);border-color:var(--ink)}
nav.tabs a:focus-visible,summary:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.strip{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--card)}
.st{padding:14px 14px 16px;border-right:1px solid var(--hair);display:flex;flex-direction:column;gap:4px;position:relative}
.st:last-child{border-right:0}.st b{font-family:"Bricolage Grotesque",sans-serif;font-size:16px}.st span{font-size:13.5px}.st em{font-style:normal;font-size:12px;color:var(--mut)}
.st-n{font-size:12px;color:var(--accent)}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-top:18px}
.facts div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}.facts p{margin:4px 0 0;font-size:14px;color:var(--mut)}
.run{margin-bottom:56px}.run-h{display:flex;flex-wrap:wrap;gap:16px;justify-content:space-between;align-items:flex-end;border-bottom:2px solid var(--ink);padding-bottom:12px}
.kpis{display:flex;flex-wrap:wrap;gap:6px 18px;margin:0}.kpis div{min-width:80px}dt{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--mut)}dd{margin:0;font-size:18px;font-weight:600;font-variant-numeric:tabular-nums}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card)}
table.grid{border-collapse:collapse;width:100%;font-size:13.5px}table.grid th{text-align:left;font-weight:600;font-size:12px;color:var(--mut);padding:9px 10px;border-bottom:1px solid var(--line);background:var(--card);position:sticky;top:0}
table.grid td{padding:9px 10px;border-bottom:1px solid var(--hair);vertical-align:top}.num{font-variant-numeric:tabular-nums;white-space:nowrap}
td.vars{font-size:12.5px;min-width:190px}.sub{color:var(--mut);font-size:13px;margin:4px 0}
.pill{display:inline-block;font:600 11px "IBM Plex Mono",monospace;letter-spacing:.06em;padding:3px 8px;border-radius:99px}
.pill.lock,.pill.lock-leaning{background:var(--lock-bg);color:var(--lock)}.pill.lever{background:var(--lever-bg);color:var(--lever)}
.rule{color:var(--bad);background:var(--bad-bg);font-size:13px;padding:6px 9px;border-radius:6px;margin:6px 0}
.warn{background:var(--bad-bg);color:var(--bad);border-radius:10px;padding:10px 14px;margin:14px 0}.warn ul{margin:6px 0 0}
.note{color:var(--mut);font-size:13px;margin:-4px 0 8px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:6px;min-width:0}
.card.ctrl{border-style:dashed}.card.new{border-color:var(--new)}
.card header{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:baseline}
.vid{font-size:13px;color:var(--accent);font-weight:600}.card.new .vid{color:var(--new)}.cost{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap}
.card p{margin:0;font-size:14px}.changes{margin:0;padding-left:18px;font-size:13.5px}.changes s{color:var(--mut)}
.badge{align-self:flex-start;font:600 11px "IBM Plex Mono",monospace;background:var(--new-bg);color:var(--new);padding:3px 8px;border-radius:99px}
.recipe{display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:13px;background:var(--ground);border-radius:8px;padding:8px 10px}
@media (max-width:560px){.recipe{grid-template-columns:1fr}.cards{grid-template-columns:1fr}h1{font-size:30px}}
.recipe ul{margin:4px 0 0;padding-left:16px}.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut)}
.route{font-size:12px;color:var(--mut)}.test{font-size:13px;background:var(--lever-bg);color:var(--lever);padding:6px 9px;border-radius:6px}
.gates{font-size:13px;padding-left:18px;margin:6px 0}summary{cursor:pointer;font-size:13.5px;font-weight:600}
details.more{margin-top:16px}.decides{background:var(--accent-bg);border-radius:10px;padding:4px 16px 10px;margin-top:18px}.decides h4{margin-top:12px}
.att{font:600 11px "IBM Plex Mono",monospace;color:var(--accent)}.foot{font-size:12.5px;color:var(--mut);margin-top:12px}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px}.filters button{font:13px "IBM Plex Sans",sans-serif;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:5px 11px;border-radius:99px;cursor:pointer}
.filters button[aria-pressed="true"]{background:var(--ink);color:var(--ground);border-color:var(--ink)}
.filters label{font-size:12px;color:var(--mut);align-self:center;margin-right:4px;min-width:60px}
#ixq{font:14px "IBM Plex Sans",sans-serif;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);width:min(360px,100%);margin-bottom:12px}
.var{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:8px}
.var summary{display:grid;grid-template-columns:110px 1fr auto auto;gap:10px;align-items:center;padding:10px 14px;font-weight:400}
.var summary code{background:none;padding:0;color:var(--accent)}.var .body{padding:0 14px 12px}
.vals{width:100%;border-collapse:collapse;font-size:13px}.vals td{padding:5px 6px;border-top:1px solid var(--hair);vertical-align:middle}
.barc{width:34%;min-width:90px}.bar{height:8px;background:var(--bar);border-radius:4px;min-width:1px}
@media (max-width:640px){.var summary{grid-template-columns:1fr auto}.var summary .fam,.var summary .cc{display:none}}
.prompt{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:10px;padding:10px 14px}.prompt summary span{font:400 12px "IBM Plex Mono",monospace;color:var(--mut);margin-left:8px}
pre{white-space:pre-wrap;word-break:break-word;font-size:12.8px;line-height:1.55;background:var(--ground);border:1px solid var(--hair);border-radius:8px;padding:14px;margin:10px 0 2px}
.howto{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}.howto section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:4px 16px 12px}
.say{font-family:"Bricolage Grotesque",sans-serif;font-size:19px}
.panel[hidden]{display:none!important}
@media (prefers-reduced-motion:no-preference){.card{transition:border-color .15s}}
"""

JS = r"""
const tabs=[...document.querySelectorAll('nav.tabs a')];
function show(id){tabs.forEach(a=>a.setAttribute('aria-selected',a.hash==='#'+id));document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!==id);try{localStorage.setItem('av-tab',id)}catch(e){}}
tabs.forEach(a=>a.addEventListener('click',e=>{e.preventDefault();show(a.hash.slice(1));history.replaceState(null,'',a.hash)}));
let start=location.hash.slice(1);if(!document.getElementById(start)){try{start=localStorage.getItem('av-tab')||''}catch(e){start=''}}
show(document.getElementById(start)?start:'how');
const IX=JSON.parse(document.getElementById('ixdata').textContent);
const st={brand:Object.keys(IX)[0],fam:'all',ten:'all',q:''};
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pc=x=>x==null?'—':(x*100).toFixed(1)+'%';
function btns(el,items,key){el.innerHTML='<label>'+el.dataset.label+'</label>'+items.map(([v,l])=>`<button type="button" data-v="${esc(v)}" aria-pressed="${st[key]===v}">${esc(l)}</button>`).join('');
 el.querySelectorAll('button').forEach(b=>b.onclick=()=>{st[key]=b.dataset.v;render()})}
function render(){const ix=IX[st.brand];if(!ix)return;
 btns(document.getElementById('fb'),Object.keys(IX).map(b=>[b,b.toUpperCase()]),'brand');
 btns(document.getElementById('ff'),[['all','All families'],...Object.entries(ix.families).map(([k,v])=>[k,v.split(' — ')[0]])],'fam');
 btns(document.getElementById('ft'),[['all','Both'],['lock-leaning','Lock-leaning'],['lever','Lever']],'ten');
 const q=st.q.toLowerCase();
 const vs=ix.variables.filter(v=>(st.fam==='all'||v.family===st.fam)&&(st.ten==='all'||v.tendency===st.ten)&&(!q||(v.id+' '+v.name+' '+v.values.map(x=>x.value).join(' ')).toLowerCase().includes(q)));
 document.getElementById('ixmeta').textContent=`${vs.length} of ${ix.variables.length} variables · ${ix.runs} posts, ${(ix.total_views/1e6).toFixed(1)}M views · built ${ix.built}`;
 const mx=v=>Math.max(...v.values.map(x=>x.view_share||0),0.0001);
 document.getElementById('ixlist').innerHTML=vs.map(v=>`<details class="var"><summary><code>${esc(v.id)}</code><span><b>${esc(v.name)}</b> <span class="sub">— ${esc(v.type)}</span></span><span class="pill ${esc(v.tendency)}">${esc(v.tendency==='lock-leaning'?'LOCK-LEANING':'LEVER')}</span><span class="cc sub">${esc(v.cost_class)}</span></summary>
 <div class="body"><p class="sub">${esc(v.tendency_why)}.</p><p class="sub"><b>Read from:</b> ${esc(v.read_from.join('; '))} <code>${esc(v.how)}</code></p>
 <p class="sub"><b>Changed in production by:</b> ${v.change_by.map(r=>'<code>'+esc(r)+'</code>').join(' ')} · cost class ${esc(v.cost_class)} (${esc(ix.cost_classes[v.cost_class]||'')})</p>
 ${v.numeric?`<p class="sub">Median ${v.numeric.median} · range ${v.numeric.min}–${v.numeric.max}</p>`:''}
 <div class="tw"><table class="vals"><tr><td class="sub">Value</td><td class="sub">Posts</td><td class="sub barc">Share of views</td><td class="sub">Views</td><td class="sub">Saves</td><td class="sub">Save rate</td></tr>
 ${v.values.map(x=>x.count==null?`<tr><td colspan="6" class="sub">${esc(x.value)}</td></tr>`:`<tr><td>${esc(x.value)}</td><td class="num">${x.count}</td><td class="barc"><div class="bar" style="width:${(x.view_share/mx(v)*100).toFixed(1)}%"></div></td><td class="num">${pc(x.view_share)}</td><td class="num">${pc(x.save_share)}</td><td class="num">${pc(x.save_rate)}</td></tr>`).join('')}</table></div></div></details>`).join('')}
document.getElementById('ixq').addEventListener('input',e=>{st.q=e.target.value;render()});render();
"""


def build(repo, echo=print):
    prompts, runs, indexes, cal = load(repo)
    run_tabs = "".join(run_html(d) for d in runs) or "<p>No runs yet.</p>"
    ix_note = ""
    for b, ix in indexes.items():
        ix_note += (f'<p class="lede2">{E(b.upper())}: {ix["runs"]} posts torn down, {ix["total_views"] / 1e6:.1f}M views, '
                    f'{len(ix["variables"])} variables in {len(ix["families"])} families. <b>Lock-leaning</b> = the brand\'s top-quartile '
                    f'posts converge on one value (≥ {ix["lock_share"]:.0%} of their views); <b>lever</b> = they vary. '
                    f'Every variation and new format on this page names its changes by these ids.</p>')
    run_sum = "".join(f'<li><a href="#runs">#{E(str(d["source"]["metrics"].get("rank")))} · {E(str(d["source"].get("post_id")))}</a> — '
                      f'{d["totals"]["variations"]} variations, {d["totals"]["formats"]} new formats, {money(d["totals"]["usd"])} machine cost</li>' for d in runs)
    per_run = [d["run"]["llm_cost"]["usd"] for d in runs]
    avg = sum(per_run) / len(per_run) if per_run else None
    ixjson = json.dumps(indexes, ensure_ascii=False).replace("</", "<\\/")
    page = f'''<title>Ad Variations</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<p class="eyebrow">the team · components/ad-variations</p>
<h1>Ad Variations</h1>
<p class="lede">One ad that already worked goes in. Out comes the plan: every element marked keep or test, with the brand's own numbers behind it; one-lever variations, highest impact first; new formats built from parts the brand has already proven; which seconds of the original get reused, what AI makes, what it costs, and what each one must pass. It plans — nothing is generated here.</p>
<nav class="tabs" aria-label="Sections"><a href="#how">How it works</a><a href="#runs">Test runs</a><a href="#index">Variable Index</a><a href="#prompts">Prompts</a><a href="#calibration">Against the hand-made spec</a><a href="#run">How to run it</a></nav>

<section class="panel" id="how"><h2>How it works</h2><p class="note">Each stage is its own prompt, so each can be read and tightened on its own. Numbers never come from a model: the index counts them, and the machine prices every recipe from the route list.</p>
{strip_html()}
<div class="facts">
<div><b>Input</b><p>A finished video teardown of a post (triage, record + verbatim transcript, doctrine read, audience read, replication spec), the post's views and saves, and the brand folder.</p></div>
<div><b>Output</b><p><code>variation-plan.json</code> — the plan; no component reads it yet — plus a Markdown copy and this page.</p></div>
<div><b>Planning cost</b><p>{"≈" + money(avg) + " per ad (Claude Opus, seven stages)" if avg is not None else "—"}; the brand's Variable Index costs ≈$__ once for 60 posts and then only codes new posts.</p></div>
<div><b>Routes it may plan on</b><p>GPT Image direct via OpenAI · Seedance on Higgsfield · Genjutsu motion transfer (Wan 2.2 Animate and Kling Motion Control flagged TEST) · the local studio for cut-outs, tracking, interpolation, stems, captions · ElevenLabs voice.</p></div>
</div>
<h4>Runs on this page</h4><ul>{run_sum}</ul></section>

<section class="panel" id="runs" hidden><h2>Test runs</h2>{run_tabs}</section>

<section class="panel" id="index" hidden><h2>Variable Index</h2>{ix_note}
<div class="filters" id="fb" data-label="Brand"></div><div class="filters" id="ff" data-label="Family"></div><div class="filters" id="ft" data-label="Call"></div>
<input id="ixq" type="search" placeholder="Search a variable or a value" aria-label="Search the index">
<p class="sub" id="ixmeta"></p><div id="ixlist"></div></section>

<section class="panel" id="prompts" hidden><h2>Every stage prompt, verbatim</h2><p class="note">Read from the prompt files as they are right now. A change is always a new numbered file; the old one is kept in that stage's archive.</p>{prompts_html(prompts)}</section>

<section class="panel" id="calibration" hidden><h2>Against the hand-made spec</h2>{calibration_html(cal)}</section>

<section class="panel" id="run" hidden><h2>How to run it on any ad</h2>{HOWTO}</section>
<p class="foot">Rebuilt from the component's files by <code>components/ad-variations/machine/page.py</code> · Markdown copy <code>components/ad-variations/AD-VARIATIONS-damon.md</code></p>
</div>
<script type="application/json" id="ixdata">{ixjson}</script>
<script>{JS}</script>'''
    out = COMP / "page" / "ad-variations.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    (COMP / "AD-VARIATIONS-damon.md").write_text(mirror(prompts, runs, indexes, cal, avg))
    echo(f"  page: {out.relative_to(repo)} ({len(page) / 1024:.0f} KB) · mirror AD-VARIATIONS-damon.md")
    return out


def mirror(prompts, runs, indexes, cal, avg):
    L = ["# Ad Variations (damon)", "",
         "Markdown mirror of the Ad Variations page. Rebuilt by `components/ad-variations/machine/page.py`.", "",
         "## How it works", ""]
    for key, name, what, how, _ in STRIP:
        L.append(f"- **{name}** ({key}) — {what}. _{how}._")
    L += ["", f"Planning cost: ≈{money(avg)} per ad." if avg is not None else "", "", "## Test runs", ""]
    for d in runs:
        L.append(f"- #{d['source']['metrics'].get('rank')} `{d['source'].get('post_id')}` — {d['totals']['variations']} variations, "
                 f"{d['totals']['formats']} new formats, {money(d['totals']['usd'])} machine cost — full record: "
                 f"`runs/ad-variations/{d['brand']}/{Path(d['source']['teardown_run']).name}/VARIATIONS.md`")
    L += ["", "## Variable Index", ""]
    for b in indexes:
        L.append(f"- {b}: `runs/ad-variations/{b}/variable-index/VARIABLE-INDEX.md`")
    if cal:
        L += ["", "## Against the hand-made spec", "", cal["summary"], "", "| What | Hand-made | Automatic, first prompts | What changed | Automatic, after |", "|---|---|---|---|---|"]
        for r in cal["rows"]:
            L.append(f"| {r['what']} | {r['hand']} | {r['auto_v1']} | {r.get('change', '')} | {r.get('auto_v2', '')} |")
    L += ["", "## Every stage prompt, verbatim", ""]
    for p in prompts:
        L += [f"### {p['name']} — `{p['file']}`", "", "````", p["text"].rstrip(), "````", ""]
    L += ["## How to run it on any ad", "", "Say: “Run ad variations on <brand> post <id>.” The session checks the teardown exists, refreshes the Variable Index, "
          "dry-runs, runs the seven stages, and republishes the page. Anything under “the owner decides” waits for the owner."]
    return "\n".join(L) + "\n"
