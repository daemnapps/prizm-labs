#!/usr/bin/env python3
"""Every prompt in the chain, verbatim, on one page.

Damon reads prompts as a page, never as a file path. Rebuilt after any
prompt change — if a prompt moved, this moved with it.
"""
import html, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C

OUT = Path(__file__).resolve().parent / "prompts.html"

CSS = """
:root{--bg:#f7f6f3;--card:#fff;--line:#e5e1d9;--ink:#221f1a;--body:#39352e;
--dim:#7b7469;--accent:#2c6b60;--new:#8a5a1f;--code:#1d1b18;--codeink:#ddd7cd;
--mono:ui-monospace,"SF Mono",Menlo,monospace;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#141310;--card:#1d1b17;--line:#332e26;--ink:#efeae1;--body:#dbd5c9;
--dim:#a09889;--accent:#5cb5a8;--new:#dda94f;--code:#0f0e0c;--codeink:#d6d0c6}}
:root[data-theme=dark]{--bg:#141310;--card:#1d1b17;--line:#332e26;--ink:#efeae1;
--body:#dbd5c9;--dim:#a09889;--accent:#5cb5a8;--new:#dda94f;--code:#0f0e0c;--codeink:#d6d0c6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--body);font:16px/1.6 var(--sans);
padding:0 18px 90px;-webkit-font-smoothing:antialiased}
.wrap{max-width:54rem;margin:0 auto}
header{padding:46px 0 6px}
.eyebrow{font:600 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
h1{font-size:31px;margin:8px 0 0;color:var(--ink);letter-spacing:-.02em}
.sub{color:var(--dim);margin-top:10px;max-width:40rem}
nav{display:flex;flex-wrap:wrap;gap:7px;margin:24px 0 0;padding-bottom:20px;border-bottom:1px solid var(--line)}
nav a{font:11.5px var(--mono);color:var(--dim);text-decoration:none;border:1px solid var(--line);
border-radius:20px;padding:5px 11px;background:var(--card)}
nav a:hover{color:var(--accent);border-color:var(--accent)}
nav a.new{color:var(--new);border-color:var(--new)}
.st{margin-top:44px;scroll-margin-top:16px}
.top{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;
border-top:3px solid var(--accent);padding-top:13px}
.st.changed .top{border-top-color:var(--new)}
.id{font:700 12px var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--accent)}
.st.changed .id{color:var(--new)}
h2{font-size:21px;margin:0;color:var(--ink);letter-spacing:-.01em}
.file{margin-left:auto;font:11px var(--mono);color:var(--dim)}
.blurb{color:var(--dim);font-size:14.5px;margin:8px 0 0;max-width:64ch}
.tag{font:600 9.5px var(--mono);letter-spacing:.08em;text-transform:uppercase;
background:var(--new);color:#fff;border-radius:3px;padding:2px 7px}
pre{background:var(--code);color:var(--codeink);font:12.5px/1.7 var(--mono);
padding:20px 22px;overflow-x:auto;white-space:pre-wrap;word-break:break-word;
border-radius:6px;margin:14px 0 0;max-height:34rem;border-left:3px solid var(--accent)}
.st.changed pre{border-left-color:var(--new)}
pre b{color:#ffb08a;font-weight:600}
pre i{color:#ffd08a;font-style:normal}
footer{margin-top:56px;padding-top:16px;border-top:1px solid var(--line);
font:11.5px var(--mono);color:var(--dim)}
"""

CHANGED = {"stage5", "stage7b"}


def render(txt):
    t = html.escape(txt.strip())
    t = re.sub(r"\{([a-z0-9_]+)\}", r"<i>{\1}</i>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
    return t


def main(argv=None):
    # The prompts are brand-free by rule, so the page needs no brand to build.
    # One brand's name used to be typed here; `--brand` is accepted for a
    # caller that wants to name one, and the page is the same either way.
    import argparse
    ap = argparse.ArgumentParser(description="Every prompt in the chain, on one page.")
    ap.add_argument("--brand", default="",
                    help="optional — the prompts name no brand, so the page is "
                         "the same for every brand")
    a = ap.parse_args(argv)
    stages = [s for s in C.stages(a.brand, lane=C.LANE_ANY) if s.get("prompt") and Path(s["prompt"]).is_file()]
    parts = ['<meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             "<title>The Teardown Prompts</title>", f"<style>{CSS}</style>",
             "<div class='wrap'><header>",
             "<div class='eyebrow'>video teardown · every prompt, verbatim</div>",
             "<h1>The teardown prompts</h1>",
             "<p class='sub'>Every prompt in the chain as it actually runs. "
             "Highlighted ones changed today.</p><nav>"]
    for s in stages:
        cls = " class='new'" if s["key"] in CHANGED else ""
        parts.append(f"<a href='#{s['id']}'{cls}>{html.escape(s['id'])} · {html.escape(s['name'])}</a>")
    parts.append("</nav></header>")
    for s in stages:
        chg = s["key"] in CHANGED
        parts.append(
            f"<div class='st{' changed' if chg else ''}' id='{html.escape(s['id'])}'>"
            f"<div class='top'><span class='id'>Stage {html.escape(s['id'])}</span>"
            f"<h2>{html.escape(s['name'])}</h2>"
            + ("<span class='tag'>changed today</span>" if chg else "")
            + f"<span class='file'>{html.escape(Path(s['prompt']).name)}</span></div>"
            f"<p class='blurb'>{html.escape(s.get('blurb',''))}</p>"
            f"<pre>{render(Path(s['prompt']).read_text())}</pre></div>")
    parts.append(f"<footer>{len(stages)} prompts · components/video-teardown/prompts/</footer></div>")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"{OUT}  ({len(stages)} prompts)")


if __name__ == "__main__":
    main()
