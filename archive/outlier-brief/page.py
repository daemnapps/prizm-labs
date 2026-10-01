#!/usr/bin/env python3
"""The Outlier Brief's page, rebuilt from SPEC.md.

    python3 page.py        # -> spec.html
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = next(d for d in HERE.parents if (d / "components").is_dir())
sys.path.insert(0, str(REPO / "components" / "copywriter" / "machine"))
import md  # noqa: E402  the workspace's own Markdown renderer

HEAD = '<meta charset="utf-8">\n<title>The Outlier Brief</title>\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Figtree:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">\n<style>\n:root{--ground:#F3F2F4;--card:#FFFFFF;--ink:#17161B;--mut:#5E5C68;--line:#D9D7DE;--hair:#E9E7EC;\n--accent:#5B2E8C;--accent-bg:#ECE3F6;--you:#0E6B5C;--you-bg:#DDEFEA}\n@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ground:#111015;--card:#19181E;--ink:#E8E6EE;--mut:#9C99A8;\n--line:#2C2A33;--hair:#221F28;--accent:#C3A2EA;--accent-bg:#261B35;--you:#7DD3C0;--you-bg:#12291F}}\n:root[data-theme="dark"]{--ground:#111015;--card:#19181E;--ink:#E8E6EE;--mut:#9C99A8;--line:#2C2A33;--hair:#221F28;\n--accent:#C3A2EA;--accent-bg:#261B35;--you:#7DD3C0;--you-bg:#12291F}\n*{box-sizing:border-box}\nbody{background:var(--ground);color:var(--ink);font:16px/1.62 Figtree,system-ui,-apple-system,sans-serif;margin:0}\n.wrap{max-width:940px;margin:0 auto;padding-inline:18px;padding-block:44px 90px}\n.eyebrow{font:500 12px/1 "JetBrains Mono",ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}\nh1,h2,h3{font-family:Fraunces,Georgia,serif;letter-spacing:-.015em;text-wrap:balance;font-weight:650}\nh1{font-size:clamp(36px,6.4vw,56px);line-height:1.02;margin:10px 0 14px}\nh2{font-size:28px;margin:52px 0 10px;padding-top:16px;border-top:2px solid var(--ink)}\nh3{font-size:20px;margin:28px 0 6px}\np,li{max-width:70ch}\n.lede{font-size:19px;color:var(--mut);max-width:62ch;margin:0}\nblockquote{margin:14px 0;padding:10px 16px;border-left:3px solid var(--line);color:var(--mut)}\ncode{font:13px "JetBrains Mono",ui-monospace,monospace;background:var(--hair);padding:1px 5px;border-radius:3px}\n.tw{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:6px;margin:12px 0 18px}\ntable{border-collapse:collapse;width:100%;font-size:14.5px}\nth,td{text-align:left;vertical-align:top;padding:10px 14px;border-bottom:1px solid var(--hair)}\nth{font:500 11px "JetBrains Mono",ui-monospace,monospace;letter-spacing:.09em;text-transform:uppercase;color:var(--mut);white-space:nowrap}\ntr:last-child td{border-bottom:0} td:first-child{font-weight:600}\nhr{border:0;border-top:1px solid var(--line);margin:40px 0 0}\n.flow{list-style:none;margin:30px 0 6px;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:8px;counter-reset:s}\n.flow li{counter-increment:s;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:12px 14px;max-width:none;display:grid;gap:4px}\n.flow li::before{content:counter(s);font:500 12px "JetBrains Mono",monospace;color:var(--mut)}\n.flow li.you{background:var(--you-bg);border-color:transparent} .flow li.you b{color:var(--you)}\n.flow b{font-family:Fraunces,Georgia,serif;font-size:17px} .flow span{color:var(--mut);font-size:13.5px;line-height:1.4}\n.key{font-size:13.5px;color:var(--mut);margin:0} .key b{color:var(--you)}\na{color:var(--accent)} :focus-visible{outline:2px solid var(--accent);outline-offset:2px}\nfooter{margin-top:60px;border-top:1px solid var(--line);padding-top:16px;font:12.5px/1.8 "JetBrains Mono",monospace;color:var(--mut)}\n</style>\n'

FLOW = """
<ol class="flow" aria-label="The flow">
  <li class="you"><b>Your idea</b><span>rough, in your words</span></li>
  <li><b>Round it out</b><span>position · customer words · research · offers · doctrine — and your questions</span></li>
  <li><b>Awareness first</b><span>where the reader is when they meet it</span></li>
  <li class="you"><b>The concept brief</b><span>format-free · you approve it</span></li>
  <li class="you"><b>Pick formats</b><span>format × style × medium</span></li>
  <li><b>Into the chains</b><span>video · image · email · page</span></li>
</ol>"""


def main():
    src = (HERE / "SPEC.md").read_text()
    body = md.render(src.split("\n---\n", 1)[1])
    if "class='tw'" not in body:   # the renderer already wraps tables in its own scroll box
        body = re.sub(r"<table", '<div class="tw"><table', body).replace("</table>", "</table></div>")
    page = (HEAD + '<div class="wrap">\n<div class="eyebrow">Tool spec · for Damon to mark up · 20 Sep 2026</div>\n'
            '<h1>The Outlier Brief</h1>\n<p class="lede">The second door, made its own tool: it starts from your idea '
            'instead of a swipe, rounds it out with everything we know, turns it into one approved brief, and sends '
            'it into any format and any chain.</p>\n' + FLOW +
            '\n<p class="key"><b>Green</b> is you. Everything else is the system.</p>\n' + body +
            '\n<footer>Source: outlier-brief/SPEC.md — this page is rebuilt from it by page.py. '
            'Nothing new is built yet.</footer>\n</div>\n')
    (HERE / "spec.html").write_text(page)
    print("->", HERE / "spec.html")


if __name__ == "__main__":
    main()
