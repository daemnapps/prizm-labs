#!/usr/bin/env python3
"""The test set as a page Damon reads and corrects: per awareness level, each
row's words, the label, the quoted reason, and the lane its words point to vs
the lane it is filed in.

    python3 tools/review_page.py <dir with test-set.json>   → <dir>/review.html
"""
import html, json, sys
from pathlib import Path

E = html.escape
ORDER = ["unaware", "problem-aware", "solution-aware", "product-aware", "most-aware", "unclear"]
KNOWS = {
    "unaware": "Does not know the desire or the need exists — or will not admit it.",
    "problem-aware": "Feels a need but has not connected it to any product category.",
    "solution-aware": "Carries the desire and knows a result is possible, but does not know a product delivers it.",
    "product-aware": "Knows the product exists but is not sold on it.",
    "most-aware": "Knows the product, wants it, simply has not bought yet.",
    "unclear": "The words show nothing either way.",
}


def build(d):
    d = Path(d)
    t = json.loads((d / "test-set.json").read_text())
    secs, n = [], 0
    for lv in ORDER:
        rows = t["test"].get(lv) or []
        if not rows:
            secs.append(f'<section><h2>{E(lv)} <span class="c">0 found in the sample</span></h2><p class="k">{E(KNOWS[lv])}</p></section>')
            continue
        items = []
        for r in rows:
            n += 1
            move = r.get("lane_words") != r.get("lane")
            items.append(f"""<tr><td class="n">{n}</td><td class="w">“{E((r.get('text') or '')[:400])}”</td>
<td>{E(r.get('why') or '')}</td><td>{E(r.get('sophistication') or '')}</td>
<td>{E(r.get('lane') or '')}{' → <b>' + E(r.get('lane_words')) + '</b>' if move else ''}</td>
<td class="s"><b class="o">{E(str(r.get('origin') or ''))}</b>{' · brand-written' if r.get('voice') == 'brand' else ''}<br>{E(str(r.get('speaker') or ''))} · {E(str(r.get('source') or '')[:80])}</td></tr>""")
        secs.append(f"""<section><h2>{E(lv)} <span class="c">{len(rows)} rows</span></h2><p class="k">Knows: “{E(KNOWS[lv])}”</p>
<div class="tbl"><table><tr><th>#</th><th>The words</th><th>Why (quoted)</th><th>Sophistication</th><th>Lane now → words say</th><th>Internal / external · who · source</th></tr>{''.join(items)}</table></div></section>""")
    per = " · ".join(f"{k} {v}" for k, v in sorted((t.get("per_level") or {}).items(), key=lambda kv: ORDER.index(kv[0]) if kv[0] in ORDER else 99))
    page = f"""<title>Awareness Test Set</title>
<style>
:root{{color-scheme:light;--bg:#f3f1ec;--panel:#fffdf8;--ink:#1a1814;--ink2:#58534a;--ink3:#8a8478;--line:#e1dcd1;--acc:#2d5bd0}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#121212;--panel:#1b1b1a;--ink:#efece5;--ink2:#b2ada3;--ink3:#827c72;--line:#2e2d2a;--acc:#7ea2ff}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#121212;--panel:#1b1b1a;--ink:#efece5;--ink2:#b2ada3;--ink3:#827c72;--line:#2e2d2a;--acc:#7ea2ff}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding-inline:16px;padding-block:32px 64px}}
h1{{font-size:clamp(30px,5vw,46px);margin:0 0 8px}} h2{{margin:28px 0 4px;font-size:22px}} .c{{font-size:13px;color:var(--ink3);font-weight:400}}
.sub,.k{{color:var(--ink2);margin:0 0 10px;max-width:80ch}} .k{{font-style:italic;font-size:14px}}
.tbl{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel)}}
table{{border-collapse:collapse;width:100%;min-width:820px;font-size:13.5px}}
th,td{{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}}
th{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);background:var(--bg)}}
td.n{{color:var(--acc);font-weight:700}} td.w{{color:var(--ink);max-width:420px}} td.s{{color:var(--ink3);font-size:12px}} td b{{color:var(--acc)}} b.o{{text-transform:uppercase;font-size:11px;letter-spacing:.06em}}
</style>
<div class="wrap">
<h1>Awareness Test Set</h1>
<p class="sub">{t.get('brand')} · {t.get('sampled')} rows sampled across every lane and tag, labelled by the model against the doctrine's own "knows" lines. Up to 20 per level below. Tell me any row number whose label is wrong and what it should be; the full backfill runs only once these agree with you.</p>
<p class="sub">Found in the sample: {E(per)}</p>
{''.join(secs)}
</div>
"""
    out = d / "review.html"
    out.write_text(page)
    return out


if __name__ == "__main__":
    print(build(sys.argv[1]))
