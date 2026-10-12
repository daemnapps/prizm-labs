#!/usr/bin/env python3
"""Every email in the format bank, rendered as its own picture.

    python3 sweep/capture.py --bank <format-bank dir served at --url> [--board jul-2025]

The bank's board pages render the real Figma boards (React bundles) and
detect the email artboards themselves. This drives headless Chrome — no
extra dependencies — in two passes per board:

  1. RECTS   a wrapper page loads the board page in a same-origin iframe,
             runs the board's own artboard test (550-820 wide, overflow
             hidden) and writes every artboard's box into the DOM, which
             --dump-dom hands back.
  2. SHOTS   for each artboard, a wrapper page offsets the iframe so that
             artboard sits at 0,0 and Chrome screenshots exactly its size.

Out: results/format-bank/<board>/rects.json and <board>/<nn>.png — the
raw material for the layout index (sweep/layouts.py). results/ is not
committed; the pictures are working material, the index is the record.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
import os as _os
OUT = Path(_os.environ["FORMAT_BANK_DIR"]).resolve() if _os.environ.get("FORMAT_BANK_DIR") else HERE / "results" / "format-bank"
URLBASE = f"/results/{OUT.name}"          # the local server's path to it

BOARD_PAGES = {
    "jan-2025": "Format Bank - January 2025 - Campaign.dc.html",
    "jan-2025-welcome": "Format Bank - January 2025 - Welcome Series.dc.html",
    "feb-2025": "Format Bank - February 2025 - Campaign.dc.html",
    "feb-2025-flow": "Format Bank - February 2025 - Flow Designs.dc.html",
    "mar-2025": "Format Bank - March 2025 - Campaign.dc.html",
    "apr-2025": "Format Bank - April 2025 - Campaign.dc.html",
    "may-2025": "Format Bank - May 2025 - Campaign.dc.html",
    "jun-2025": "Format Bank - June 2025 - Campaign.dc.html",
    "jul-2025": "Format Bank - July 2025 - Campaign.dc.html",
    "aug-2025": "Format Bank - August 2025 - Campaign.dc.html",
    "sep-2025": "Format Bank - September 2025 - Campaign.dc.html",
    "oct-2025": "Format Bank - October 2025 - Campaign.dc.html",
    "nov-2025": "Format Bank - November 2025 - Campaign.dc.html",
    "flow-nov-2025": "Format Bank - Flow Designs - November 2025.dc.html",
    "dec-2025": "Format Bank - December 2025 - Campaign.dc.html",
    "jan-2026": "Format Bank - January 2026 - Campaign.dc.html",
    "flow-2026": "Format Bank - FLOW 2026.dc.html",
    "flow-results-request": "Format Bank - FLOW - Customer Results Request.dc.html",
}


def boards_in(bank):
    """Every board the bank holds — the HTML export's known pages plus any
    board folder with its own nodes (a .fig intake)."""
    names = [b for b in BOARD_PAGES if (Path(bank) / "boards" / b / "Components.bundle.js").is_file()]
    bd = Path(bank) / "boards"
    if bd.is_dir():
        for p_ in sorted(bd.iterdir()):
            if p_.is_dir() and p_.name not in names and ((p_ / "nodes.json").is_file() or (p_ / "Components.bundle.js").is_file()):
                names.append(p_.name)
    return names

RECTS_JS = """
(function(){
  var f = document.getElementById('b');
  function go(){
    var d = f.contentDocument; if(!d || !d.body){ return setTimeout(go, 500); }
    var all = Array.prototype.slice.call(d.querySelectorAll('div'));
    var frames = all.filter(function(n){
      if (n.offsetWidth < 550 || n.offsetWidth > 820 || n.offsetHeight < 500 || n.offsetHeight > 6500) return false;
      var cs = d.defaultView.getComputedStyle(n);
      if (cs.overflow !== 'hidden' || cs.borderRadius === '50%' || cs.borderRadius.slice(-1) === '%') return false;
      var p = n.parentElement;
      while (p) { if (p.offsetWidth >= 550 && p.offsetWidth <= 820 && p.offsetHeight >= 500 && p.offsetHeight <= 6500 &&
                      d.defaultView.getComputedStyle(p).overflow === 'hidden') return false; p = p.parentElement; }
      return true;
    });
    var rects = frames.map(function(n){ var r = n.getBoundingClientRect();
      return {x: Math.round(r.left + f.contentWindow.scrollX), y: Math.round(r.top + f.contentWindow.scrollY),
              w: Math.round(r.width), h: Math.round(r.height), name: n.getAttribute('data-name') || ''}; });
    rects.sort(function(a,b){ return (a.y - b.y > 400 ? 1 : b.y - a.y > 400 ? -1 : a.x - b.x); });
    var pre = document.getElementById('rects'); pre.textContent = JSON.stringify(rects);
    document.title = 'RECTS_READY';
  }
  f.addEventListener('load', function(){ setTimeout(go, 2500); });
})();
"""


def wrapper_rects(url):
    return (f'<!doctype html><meta charset="utf-8"><title>rects</title>'
            f'<pre id="rects"></pre><iframe id="b" src="{url}" style="width:32000px;height:8000px;border:0"></iframe>'
            f'<script>{RECTS_JS}</script>')


def wrapper_shot(url, r):
    return (f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;overflow:hidden;background:#0c100f}}'
            f'#c{{position:relative;width:{r["w"]}px;height:{r["h"]}px;overflow:hidden}}'
            f'#b{{position:absolute;left:{-r["x"]}px;top:{-r["y"]}px;width:32000px;height:8000px;border:0}}</style>'
            f'<div id="c"><iframe id="b" src="{url}"></iframe></div>')


def chrome(args, timeout=90):
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                           "--no-first-run", "--disable-extensions", *args],
                          capture_output=True, text=True, timeout=timeout)


def capture_board(bank, base_url, board, only_rects=False):
    page = BOARD_PAGES[board]
    url = base_url + page.replace(" ", "%20")
    bdir = OUT / board
    bdir.mkdir(parents=True, exist_ok=True)
    w = bank / f"_wrap_{board}.html"
    w.write_text(wrapper_rects(url))
    r = chrome(["--virtual-time-budget=12000", "--window-size=1200,800", "--dump-dom",
                base_url + w.name])
    m = re.search(r'<pre id="rects">(\[.*?\])</pre>', r.stdout, re.S)
    rects = json.loads(m.group(1)) if m else []
    (bdir / "rects.json").write_text(json.dumps(rects, indent=1) + "\n")
    print(f"{board}: {len(rects)} artboard(s)")
    if only_rects:
        return rects
    for i, rc in enumerate(rects, 1):
        png = bdir / f"{i:02d}.png"
        if png.is_file():
            continue
        w.write_text(wrapper_shot(url, rc))
        chrome(["--virtual-time-budget=9000", f"--window-size={rc['w']},{min(rc['h'], 6500)}",
                f"--screenshot={png}", base_url + w.name])
        print(f"   {i:02d}  {rc['w']}x{rc['h']}  {rc.get('name') or ''}")
    w.unlink(missing_ok=True)
    return rects


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--url", default="http://127.0.0.1:8791/")
    ap.add_argument("--board", default=None)
    ap.add_argument("--rects-only", action="store_true")
    a = ap.parse_args()
    bank = Path(a.bank)
    boards = [a.board] if a.board else list(BOARD_PAGES)
    t0 = time.time()
    for b in boards:
        capture_board(bank, a.url, b, a.rects_only)
    print(f"done in {time.time() - t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    main()
