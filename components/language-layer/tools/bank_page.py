#!/usr/bin/env python3
"""The language bank as a page: per brand, rows by awareness level, lane,
origin and voice; the sources it draws from; the loudest repeated lines; and
real rows at every level. Read from the bank, nothing summarised by a model.

    python3 tools/bank_page.py --brand B [--brand B2] [--out <file.html>] [--md <file.md>] [--note "…"]
                                         # default runs/language-layer/_system/bank.html + BANK.md beside it
The Markdown mirror carries the same counts for the team; each --note is a
line under "Open".
"""
import argparse, collections, html, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import engine as E  # noqa: E402

LEVELS = ["unaware", "problem-aware", "solution-aware", "product-aware", "most-aware", "unclear"]
KNOWS = {"unaware": "Doesn't know the need exists — or won't admit it",
         "problem-aware": "Feels the need, no product category in sight",
         "solution-aware": "Knows a result is possible, not that our product delivers it",
         "product-aware": "Knows our product, not sold on it",
         "most-aware": "Knows it, wants it (buyers included)",
         "unclear": "The words carry nothing either way"}
X = html.escape


def same(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", (t or "").lower())).strip()


def brand_block(brand):
    rows = E.load(brand)
    lab = [r for r in rows if isinstance(r.get("awareness"), dict)]
    lv = collections.Counter(r["awareness"].get("level") for r in lab)
    lane = collections.Counter(r.get("funnel") for r in rows)
    origin = collections.Counter(r.get("origin") or "—" for r in rows)
    voice = collections.Counter(r.get("voice") or "—" for r in rows)
    src = collections.Counter((r.get("source") or {}).get("id") or "(no id)" for r in rows)
    rep = collections.Counter(same(r.get("text")) for r in rows if (r.get("source") or {}).get("kind") == "post")
    loud = [(k, n) for k, n in rep.most_common(40) if n >= 3 and k][:12]
    example = {}
    for r in sorted(lab, key=lambda r: -len(r.get("text") or "") if 20 < len(r.get("text") or "") < 220 else 0):
        l = r["awareness"].get("level")
        if l in LEVELS and len(example.setdefault(l, [])) < 5 and 20 < len(r.get("text") or "") < 220:
            example[l].append(r)
    total = max(1, len(lab))
    bars = "".join(f'<div class="bar"><span class="l">{X(l)}</span><span class="t"><i style="width:{lv.get(l,0)/total*100:.1f}%"></i></span>'
                   f'<b>{lv.get(l,0):,}</b><em>{X(KNOWS[l])}</em></div>' for l in LEVELS)
    chips = lambda c: " ".join(f'<span class="chip">{X(str(k))} <b>{v:,}</b></span>' for k, v in c.most_common())
    ex = ""
    for l in LEVELS[:-1]:
        items = "".join(f'<li>“{X(r["text"].strip())}”<small>{X(r.get("origin") or "")} · {X((r.get("source") or {}).get("id") or (r.get("source") or {}).get("name") or "")}'
                        f'{" · why: " + X(r["awareness"].get("why","")[:90]) if r["awareness"].get("why") else ""}</small></li>'
                        for r in example.get(l, []))
        ex += f'<div class="ex"><h4>{X(l)}</h4><ul>{items or "<li class=none>none yet</li>"}</ul></div>'
    loud_html = "".join(f'<li><b>{n}×</b> “{X(k)}”</li>' for k, n in loud) or "<li class=none>none</li>"
    top_src = "".join(f'<li><code>{X(k)}</code> <b>{v:,}</b></li>' for k, v in src.most_common(12))
    return f"""<section><h2>{X(brand.upper())} <span class="c">{len(rows):,} rows · {len(lab):,} labelled ({len(lab)/max(1,len(rows)):.0%})</span></h2>
<div class="grid2"><div class="card"><h3>Awareness — what the words show they know</h3>{bars}</div>
<div class="card"><h3>Lanes</h3><p>{chips(lane)}</p><h3>Internal / external</h3><p>{chips(origin)}</p><h3>Whose voice</h3><p>{chips(voice)}</p></div></div>
<div class="grid2"><div class="card"><h3>Loudest repeated comments</h3><ul class="loud">{loud_html}</ul></div>
<div class="card"><h3>Top sources</h3><ul class="src">{top_src}</ul></div></div>
<div class="card"><h3>Real rows at each level</h3><div class="exs">{ex}</div></div></section>"""


def brand_md(brand):
    """The same counts as brand_block(), as Markdown."""
    rows = E.load(brand)
    lab = [r for r in rows if isinstance(r.get("awareness"), dict)]
    lv = collections.Counter(r["awareness"].get("level") for r in lab)
    c = lambda cnt: " · ".join(f"{k} {v:,}" for k, v in cnt.most_common())  # noqa: E731
    lane = collections.Counter(r.get("funnel") for r in rows)
    origin = collections.Counter(r.get("origin") or "—" for r in rows)
    voice = collections.Counter(r.get("voice") or "—" for r in rows)
    src = collections.Counter((r.get("source") or {}).get("id") or "(no id)" for r in rows)
    rep = collections.Counter(same(r.get("text")) for r in rows if (r.get("source") or {}).get("kind") == "post")
    loud = [(k, n) for k, n in rep.most_common(40) if n >= 3 and k][:12]
    cta = sum(1 for r in rows if "keyword-cta" in (r.get("use") if isinstance(r.get("use"), list) else [r.get("use")]))
    out = [f"## {brand.upper()} — {len(rows):,} rows, {len(lab):,} labelled", "",
           "| Awareness level | Rows |", "|---|---|"] + [f"| {l} | {lv.get(l, 0):,} |" for l in LEVELS]
    out += ["", f"**Lanes:** {c(lane)}", "", f"**Internal / external:** {c(origin)}", "",
            f"**Voice:** {c(voice)}", "", f"**Rows tagged `keyword-cta`:** {cta:,}", "",
            "**Top sources:** " + " · ".join(f"`{k}` {v:,}" for k, v in src.most_common(8)), "",
            "**Loudest repeated comments:** " + (" · ".join(f"“{k}” ×{n}" for k, n in loud) or "none"), ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", action="append", required=True)
    ap.add_argument("--out", default=str(E.WORKSPACE / "runs" / "language-layer" / "_system" / "bank.html"))
    ap.add_argument("--md", default=None, help="the Markdown mirror (default: BANK.md beside --out)")
    ap.add_argument("--note", action="append", default=[], help="a line under Open in the mirror")
    ap.add_argument("--mirror-of", default=None, help="the published page this Markdown mirrors (its link)")
    a = ap.parse_args()
    body = "".join(brand_block(b) for b in a.brand)
    page = f"""<title>The Language Bank</title>
<style>
:root{{color-scheme:light;--bg:#f3f1ec;--panel:#fffdf8;--ink:#1a1814;--ink2:#58534a;--ink3:#8a8478;--line:#e1dcd1;--acc:#2d5bd0;--soft:#e9eefb}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#121212;--panel:#1b1b1a;--ink:#efece5;--ink2:#b2ada3;--ink3:#827c72;--line:#2e2d2a;--acc:#7ea2ff;--soft:#1f2433}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#121212;--panel:#1b1b1a;--ink:#efece5;--ink2:#b2ada3;--ink3:#827c72;--line:#2e2d2a;--acc:#7ea2ff;--soft:#1f2433}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif}}
.wrap{{max-width:1120px;margin:0 auto;padding-inline:16px;padding-block:32px 64px}}
h1{{font-size:clamp(32px,5vw,50px);margin:0 0 6px}} h2{{font-size:26px;margin:34px 0 10px}} h3{{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);margin:0 0 8px}}
h4{{margin:0 0 6px;font-size:15px;text-transform:capitalize}} .c{{font-size:14px;color:var(--ink3);font-weight:400}} .sub{{color:var(--ink2);max-width:75ch}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;margin-bottom:12px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.bar{{display:grid;grid-template-columns:120px 1fr 56px;gap:8px;align-items:center;margin:6px 0}} .bar em{{grid-column:1/-1;font-size:12px;color:var(--ink3);font-style:normal;margin-top:-4px}}
.bar .l{{font-weight:600;text-transform:capitalize}} .bar .t{{height:10px;background:var(--soft);border-radius:99px;overflow:hidden}} .bar i{{display:block;height:100%;background:var(--acc)}} .bar b{{text-align:right}}
.chip{{display:inline-block;border:1px solid var(--line);border-radius:99px;padding:2px 10px;margin:0 6px 6px 0;font-size:13px}}
ul{{margin:0;padding-left:18px}} li{{margin:4px 0}} li small{{display:block;color:var(--ink3);font-size:12px}} .none{{color:var(--ink3);list-style:none}}
code{{font-size:12px;background:var(--soft);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}}
.exs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}}
</style>
<div class="wrap"><h1>The Language Bank</h1>
<p class="sub">Every row read against the doctrine's own awareness definitions, in context: who said it, where, and in answer to what. Also shown: internal (our customers and our own properties) vs external (everyone else's spaces), and whether it's the audience or our own brand's copy. Built straight from the bank files.</p>
{body}</div>
"""
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(page)
    print(a.out)
    md = Path(a.md) if a.md else Path(a.out).with_name("BANK.md")
    from datetime import date
    md.write_text("\n".join([f"# The Language Bank — state on {date.today().isoformat()}", "",
                             "> " + (f"Mirror of {a.mirror_of} · " if a.mirror_of else "")
                            + "Built by `tools/language-layer/tools/bank_page.py` from the bank files, "
                             "beside `bank.html`. Rules: `brands/language-schema.md`; the reasoning: "
                             "`tools/language-layer/docs/STANDARD.md`.", ""]
                            + [brand_md(b) for b in a.brand]
                            + (["## Open", ""] + [f"- {n}" for n in a.note] + [""] if a.note else [])))
    print(md)


if __name__ == "__main__":
    main()
