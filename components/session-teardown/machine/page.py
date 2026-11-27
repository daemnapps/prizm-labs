"""The run's page (page.html): the hypothesis and the change on top, where each group stopped on the page by
section, the counted patterns, the leaks, then every step's prompt exactly as sent and its output exactly as
returned — read off run-kit's run.json. Same look as the page chain's run page (page-production chain_page.CSS),
so every teardown page reads the same.
"""
import html
from pathlib import Path

import shared

E = html.escape
EXTRA = """
.sec{display:grid;grid-template-columns:minmax(120px,1.2fr) 2fr 2fr;gap:8px;align-items:center;font-size:13px;margin:4px 0}
.bar{height:14px;border-radius:4px;background:var(--line);position:relative;overflow:hidden}
.bar>i{position:absolute;inset:0 auto 0 0;border-radius:4px}.bar.l>i{background:var(--no)}.bar.c>i{background:var(--ok)}
.bar>span{position:relative;padding-left:6px;font-size:11px;line-height:14px}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid var(--line);padding:6px;text-align:left}
.scroll{overflow-x:auto}
@media (max-width:600px){.sec{grid-template-columns:1fr}}
"""


def pre(t):
    return "<pre>%s</pre>" % E(t)


def _read(out, name):
    p = Path(out) / name if name else None
    return p.read_text() if p and p.is_file() else None


def render(out, st, steps, leaks):
    out = Path(out)
    hyp = st.get("hypothesis") or {}
    n_left, n_conv = st.get("n_left") or 0, st.get("n_converted") or 0
    pmap = st.get("page_map") or []
    reach = st.get("reach") or {"left": {}, "converted": {}}

    swings, fixes = st.get("swings") or [], st.get("fixes") or []
    usd = lambda v: "$" + format(int(v or 0), ",")                                    # noqa: E731
    picked = st.get("picked")
    tops = ['<div><b>🎯 Big swing %d%s · %s/mo at stake · %s</b><span>%s</span><p class="quiet">%s</p></div>' % (
        w["n"], " ✓ picked" if picked == w["n"] else "", usd(w["at_stake_month"]), E(w["type"]), E(w["hypothesis"]),
        E(w["change"])) for w in swings]
    if not swings and hyp:
        tops.append('<div><b>Hypothesis</b><span>%s</span><p class="quiet">%s</p></div>' % (
            E(hyp.get("hypothesis") or "—"), E(hyp.get("change") or "")))
    tops.append('<div><b>🔧 Team fixes · %s</b><span>%d fixes · %s/mo at stake</span></div>' % (
        E(st.get("fix_state") or "—"), len(fixes), usd(sum(f.get("value_usd_month") or 0 for f in fixes))))

    if pmap:
        rows = []
        for s in pmap:
            lc, cc = reach["left"].get(s["label"], 0), reach["converted"].get(s["label"], 0)
            lp = 100.0 * lc / n_left if n_left else 0
            cp = 100.0 * cc / n_conv if n_conv else 0
            rows.append('<div class="sec"><div><b>%s</b> <span class="meta">%d–%d%%</span><br><span class="quiet">%s</span></div>'
                        '<div class="bar l"><i style="width:%.0f%%"></i><span>%d of %d left</span></div>'
                        '<div class="bar c"><i style="width:%.0f%%"></i><span>%d of %d converted</span></div></div>' % (
                            E(s["label"] + (" · “%s”" % s["heading"] if s.get("heading") else "")), s["start"], s["end"],
                            E(s["job"]), lp, lc, n_left, cp, cc, n_conv))
        where = ('<h3>Where they stopped · deepest section reached</h3><p class="quiet">Page map from %s. Depth bands are '
                 'estimates from section length.</p>%s' % (E(st.get("structure_from") or ""), "".join(rows)))
    else:
        where = '<h3>Where they stopped</h3><p class="quiet">No page map for this page yet, so depth is scroll % only.</p>'

    frows = "".join("<tr><td>%s</td><td>%s · %s</td><td>%s</td><td>%s</td><td>%s/%d · %s/%d</td><td>%s</td></tr>" % (
        E((f.get("where") or {}).get("section") or ""), E(f.get("type") or ""), E(f.get("effort") or ""),
        E((f.get("why") or {}).get("pattern") or ""), E(f.get("what") or ""), (f.get("why") or {}).get("left"), n_left,
        (f.get("why") or {}).get("converted"), n_conv, usd(f.get("value_usd_month"))) for f in fixes)
    fix_html = ('<section class="run"><h3>🔧 Team fix list</h3><div class="scroll"><table><tr><th>Section</th><th>Type · effort</th>'
                '<th>Seen</th><th>Fix</th><th>Left · converted</th><th>$/mo</th></tr>%s</table></div></section>' % frows
                if fixes else "")
    rub = st.get("friction") or []
    rub_html = ("<h3 class=\"stages-h\">Friction, counted</h3><ul>%s</ul>" % "".join(
        "<li>%s “%s” — %d left · %d converted</li>" % (E({"rage": "rage-tapped", "dead": "nothing happened on",
                                                           "repeat": "tapped 3+ times"}[r["kind"]]),
                                                         E(r["element"]), r["left"], r["converted"]) for r in rub)
                if rub else "")
    pats = "".join("<li>%s %s — <b>%s</b> of %d who left · %s of %d who reached checkout · %s/mo</li>" % (
        "🔧" if f.get("kind") == "fix" else "🎯", E(f["finding"]), f.get("left"), n_left, f.get("converted"), n_conv,
        usd(f.get("at_stake_month"))) for f in st.get("findings") or [])
    lrows = "".join("<tr><td>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%.0f%%</td><td>$%.2f</td></tr>" % (
        E(p["page_id"]), E(p["step"]), p["visitors"], p["reached_next"], 100 * p["reach_rate"], p["at_stake"])
        for p in leaks[:10])

    stages = st.get("stages") or {}
    sh = ""
    for s in steps:
        rec = stages.get(s["key"]) or {}
        status = rec.get("status") or "not run"
        meta = " · ".join(x for x in (status, rec.get("prompt_name") or rec.get("source") or "", rec.get("model") or "",
                                      ("%ss" % rec["seconds"]) if rec.get("seconds") is not None else "",
                                      rec.get("why") or "") if x)
        sent, got = _read(out, rec.get("sent")), _read(out, rec.get("out"))
        inner = ""
        if sent is not None:
            inner += '<details class="inner"><summary>Prompt as sent · %s characters</summary>%s</details>' % (
                format(len(sent), ","), pre(sent))
        if got is not None:
            inner += '<details class="inner" open><summary>Output · %s characters</summary>%s</details>' % (
                format(len(got), ","), pre(got))
        sh += ('<details class="stage"><summary><b>%s</b><span class="meta">%s</span></summary>%s</details>'
               % (E(s["name"]), E(meta), inner or '<p class="quiet">No prompt: this step is code.</p>'))

    body = ('<title>Session Teardown</title><style>%s%s</style><main>'
            '<h1>%s</h1><p class="quiet">%s · %s · %s</p><div class="top">%s</div>'
            '%s<section class="run">%s%s<h3 class="stages-h">Every finding, priced</h3><ul>%s</ul></section>'
            '<section class="run"><h3>Leaks ranked</h3><div class="scroll"><table><tr><th>Page</th><th>Step</th><th>Visitors</th>'
            '<th>Reached checkout</th><th>Rate</th><th>At stake</th></tr>%s</table></div></section>'
            '<section class="run"><h3>Every step · prompt and output, word for word</h3>%s</section></main>') % (
        shared.page_css(), EXTRA, E(st.get("page_id") or "no page"), E(st.get("state") or ""), E(st.get("source") or ""),
        E(st.get("at") or ""), "".join(tops), fix_html, where, rub_html, pats or "<li>—</li>", lrows, sh)
    (out / "page.html").write_text('<!doctype html><meta charset="utf-8"><meta name="viewport" '
                                   'content="width=device-width,initial-scale=1">' + body)
