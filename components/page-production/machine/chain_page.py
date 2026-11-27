#!/usr/bin/env python3
"""One page that shows page-chain runs end to end: the built page, then every stage's prompt exactly as sent and its
output exactly as returned, plus the identity check and the bank check. Built for the owner to read the prompts and
outputs and tighten the prompts.

    python3 chain_page.py <brand>/<label> [<brand>/<label> ...] --out <dir>

Writes <dir>/index.html, <dir>/<brand>-<label>/ (each built site) and <dir>/files.json (published path -> file) for
publishing as one multi-file page.
"""
import argparse
import html
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "page-teardown" / "machine"))
import chain_io as C  # noqa: E402

E = html.escape


def pre(t):
    return f"<pre>{E(t)}</pre>"


def run_block(brand, label, out):
    d = C.WS / "runs" / "page-chain" / brand / label
    st = json.loads((d / "run.json").read_text())
    slug = f"{brand}-{label}"
    shutil.copytree(d / "site", out / slug, dirs_exist_ok=True)
    page = json.loads((d / "page.json").read_text())
    idr = json.loads((d / "identity-result.json").read_text())
    bank = json.loads((d / "bank-check.json").read_text())
    pics = json.loads((d / "pictures.json").read_text()) if (d / "pictures.json").exists() else {}
    used = sum(1 for v in pics.values() if "set" in v)
    queued = len(pics) - used
    struct = json.loads((d / "structure.json").read_text())
    ident = json.loads((d / "identity-all.json").read_text())["items"]
    src_heads = [i["text"] for i in ident if i.get("kind") in ("heading", "cta")][:8]
    our_heads = []
    for s in page.get("sections", []):
        for b in s.get("blocks", []):
            if b.get("type") in ("headline", "button"):
                our_heads.append(b.get("text", ""))
    mark = lambda ok: '<span class="ok">✓</span>' if ok else '<span class="no">✗</span>'
    stages = sorted(st["stages"].items(), key=lambda kv: kv[1].get("order", 0))
    stage_html = ""
    for name, rec in stages:
        sent = (d / rec["sent"]).read_text()
        outp = (d / rec["out"]).read_text()
        stage_html += (f'<details class="stage"><summary><b>{E(rec.get("title") or name)}</b>'
                       f'<span class="meta">{E(Path(rec["prompt"]).name)} · {E(rec["model"])} · {rec["seconds"]}s</span></summary>'
                       f'<details class="inner"><summary>Prompt as sent · {len(sent):,} characters</summary>{pre(sent)}</details>'
                       f'<details class="inner" open><summary>Output · {len(outp):,} characters</summary>{pre(outp)}</details>'
                       f'</details>')
    surv = idr.get("survivors") or []
    surv_html = ("<p class='quiet'>Nothing of the source found.</p>" if not surv else
                 "<ul>" + "".join(f"<li>{E(x.get('text') or x.get('ours') or '')} <i>{E(x.get('kind') or x.get('source_item') or '')}</i></li>" for x in surv) + "</ul>")
    adapted = "".join(f"<li>{E(x)}</li>" for x in page.get("adapted") or [])
    return slug, f"""
<section class="run" id="{slug}">
  <h2>{E(brand.upper())} · {E(st.get('topic', label))}</h2>
  <div class="chips">
    <span class="chip">{E(struct.get('format', ''))} → {E(page.get('format', ''))}</span>
    <span class="chip">{mark(idr.get('pass'))} no source identity</span>
    <span class="chip">{mark(bank.get('pass'))} {bank.get('rows_cited', 0)} bank rows cited</span>
    <span class="chip">🧊 {used} 3D prints · ⏳ {queued} queued</span>
  </div>
  <div class="frame"><iframe src="{slug}/index.html" title="{E(brand)} page" loading="lazy"></iframe>
    <a class="open" href="{slug}/index.html" target="_blank">Open the page ↗</a></div>
  <div class="vs">
    <div><h3>Source had</h3><ul>{''.join(f'<li>{E(x)}</li>' for x in src_heads)}</ul>
      <p class="quiet"><a href="{E(st.get('source_url', ''))}" target="_blank">{E(st.get('source_url', ''))}</a></p></div>
    <div><h3>Ours has</h3><ul>{''.join(f'<li>{E(x)}</li>' for x in our_heads)}</ul></div>
  </div>
  <details class="stage"><summary><b>Identity check</b><span class="meta">{len(ident)} source items tested</span></summary>{surv_html}</details>
  <details class="stage"><summary><b>Structure adapted</b><span class="meta">{len(page.get('adapted') or [])} changes</span></summary><ul>{adapted}</ul></details>
  <h3 class="stages-h">Every stage · prompt and output, word for word</h3>
  {stage_html}
</section>"""


CSS = """
:root{--bg:#fbfaf7;--ink:#17181a;--ink2:#5d6166;--line:#e3e1db;--card:#fff;--ok:#1f7a3f;--no:#b3261e;--acc:#2b4a8b}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#141516;--ink:#ecebe7;--ink2:#a3a6a9;--line:#2c2e30;--card:#1c1d1f;--ok:#5cc985;--no:#ff8a80;--acc:#8fb0ff}}
:root[data-theme="dark"]{--bg:#141516;--ink:#ecebe7;--ink2:#a3a6a9;--line:#2c2e30;--card:#1c1d1f;--ok:#5cc985;--no:#ff8a80;--acc:#8fb0ff}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark}}:root[data-theme="dark"]{color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding-block:20px 60px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.run,.vs>div,details.stage{min-width:0}
h1{font-size:24px;margin:8px 0 14px}h2{font-size:20px;margin:0 0 10px}h3{font-size:15px;margin:0 0 6px}
.top{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-bottom:22px}
.top a,.top div{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;color:var(--ink);text-decoration:none}
.top b{display:block;font-size:13px;color:var(--ink2);font-weight:600}.top span{font-size:17px;font-weight:600}
.run{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:0 0 22px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}.chip{border:1px solid var(--line);border-radius:99px;padding:3px 10px;font-size:13px}
.ok{color:var(--ok);font-weight:700}.no{color:var(--no);font-weight:700}
.frame{position:relative;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fff}
iframe{width:100%;height:720px;border:0;display:block}
.open{position:absolute;top:8px;right:8px;background:var(--acc);color:#fff;font-size:13px;padding:5px 10px;border-radius:6px;text-decoration:none}
.vs{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0}.vs>div{border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.vs ul{margin:0;padding-left:18px;font-size:14px}
details.stage{border:1px solid var(--line);border-radius:10px;margin:8px 0;padding:8px 12px}
details.stage>summary{cursor:pointer;display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}
.meta{color:var(--ink2);font-size:12px}
details.inner{margin:8px 0}details.inner>summary{cursor:pointer;font-size:13px;color:var(--acc)}
pre{white-space:pre-wrap;word-break:break-word;font:12.5px/1.45 ui-monospace,Menlo,monospace;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;max-height:70vh;overflow:auto}
.quiet{color:var(--ink2);font-size:13px}.stages-h{margin-top:16px}
@media (max-width:600px){.vs{grid-template-columns:1fr}iframe{height:600px}}
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Page Chain")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    blocks, tops = [], []
    for r in a.runs:
        brand, label = r.split("/", 1)
        slug, b = run_block(brand, label, out)
        blocks.append(b)
        tops.append(f'<a href="#{slug}"><b>Look</b><span>{E(brand.upper())} page ↓</span></a>')
    tops.append('<div><b>Live</b><span>Nothing live</span></div>')
    waiting = sum(1 for r in a.runs for v in json.loads((C.WS / "runs" / "page-chain" / r / "pictures.json").read_text()).values()
                  if "queued" in v)
    tops.insert(len(a.runs), f'<div><b>Pictures</b><span>⏳ {waiting} in the 3D print queue</span></div>')
    doc = (f'<title>{E(a.title)}</title><meta name="claude:viewport-fit-sides" content="cover">'
           f'<style>{CSS}</style><main><h1>{E(a.title)}</h1>'
           f'<div class="top">{"".join(tops)}</div>{"".join(blocks)}</main>')
    (out / "index.html").write_text(doc)
    files = {str(p.relative_to(out)): str(p) for p in out.rglob("*")
             if p.is_file() and p.relative_to(out).as_posix() not in ("index.html", "files.json")}
    (out / "files.json").write_text(json.dumps(files, indent=1))
    print(f"chain page: {out / 'index.html'} · {len(files)} supporting files")


if __name__ == "__main__":
    main()
