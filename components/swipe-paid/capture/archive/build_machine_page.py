#!/usr/bin/env python3
"""Render the swipe machine page — the workflow, and live links to every brand.

    python3 build_machine_page.py <out.html>

Regenerate it after every brand swipe: the library table and every Drive link
are read live off the synced folders, so the page is never out of date.
Shares teardown_page.css with the teardowns, so the whole swipe world reads as
one system.
"""
import html, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_links as dl

HERE = os.path.dirname(os.path.abspath(__file__))
E = html.escape

TEARDOWNS = {
    "brand-c": ("Brand C Teardown", "(team page)"),
}

STAGES = [
    ("sweep", "Their whole live ad library", "Pages the advertiser search until a page comes back short. That short page is the proof the library is exhausted — without it every count downstream is a floor, not a number.", "~1.2 credits per creative"),
    ("resolve", "Landing pages per copy block", "The search rows carry no destination. Pulls the ad detail for a few creatives per block and maps the result onto the block.", "1 credit each, ~30 a run"),
    ("library", "Filed by copy block, media on disk", "Dedupes, strips the page id Meta glues onto every body, groups by copy block, ranks the blocks by volume, downloads every video, poster and still.", "free"),
    ("sitemap", "Their real page list", "The ads point at a handful of pages; the funnel is everything else. Walks their sitemaps, drops locale mirrors, keeps every ad target.", "free"),
    ("capture", "Every page, as served", "HTML, readable text, redirect chain and detected stack for each URL, on a mobile user agent — these funnels serve a different page to a desktop browser.", "free"),
    ("classify", "Sorted by what each page is", "Advertorial, listicle, prelander, quiz, product page, review, comparison, blog, utility — decided by the page's shape. Reads the product, audience, channel and variant codes off the slug.", "free"),
    ("shoot", "Full-page mobile screenshots", "One per template family plus every ad-facing product page, 390pt wide, trimmed to the real page height.", "free"),
    ("drive", "Filed to the shared drive", "Into swipe-paid/&lt;brand&gt;/ in the shape that folder already uses: angles, _pages, teardown.", "free"),
    ("links", "Every output as a link", "Reads each synced file's Drive id and prints the link. Nothing is ever handed over as a file path.", "free"),
]

TRAPS = [
    ("Search bills per ad returned", "<code>count</code> defaults to 100 server-side. Always pass it. Dictionary calls are free."),
    ("Meta glues the page id onto the body text", "Strip a trailing run of 10+ digits before grouping, or every creative looks like its own copy block — Brand C read as 496 blocks that were really 8."),
    ("Shopify prices in the egress country's currency", "Competitor A came out in Thai baht, Brand C in Lao kip. Take prices from the product JSON or the ad copy, and say so in the teardown."),
    ("Chrome's new headless hangs on live commerce pages", "Plain <code>--headless</code>, a throwaway profile, no virtual-time budget. Buy height, then trim."),
    ("Locale mirrors triple the page count", "<code>/fr-ca/…</code> says nothing new. Dropped — unless an ad actually points at it."),
    ("The ad-detail store is shared across every brand", "Landing pages read back out of it have to be filtered to the brand in hand, or another advertiser's funnel walks into the capture list."),
    ("The ads' landing pages are not the funnel", "Brand C's 496 ads point at 7 product pages. The other 222 are a separate lane, and reading only the ad targets misses the whole factory."),
]

def link_cell(url, label, missing="still uploading"):
    if not url:
        return f'<span class="dim">{missing}</span>'
    return f'<a href="{url}" target="_blank" rel="noopener">{E(label)}</a>'

def main(out_path):
    P, A = [], None
    P = []; A = P.append
    A('<title>The Swipe Machine</title>\n<style>')
    A(open(os.path.join(HERE, "teardown_page.css")).read())
    A('''
.stage{display:grid;grid-template-columns:auto 1fr auto;gap:1rem;align-items:start;
  background:var(--surface);border:1px solid var(--rule);border-radius:10px;
  padding:16px 18px;box-shadow:var(--shadow)}
@media(max-width:640px){.stage{grid-template-columns:auto 1fr}.stage .cost{grid-column:2}}
.stage .no{font-family:var(--mono);font-size:.78rem;color:var(--accent);
  border:1px solid var(--accent);border-radius:4px;padding:.15em .5em;font-variant-numeric:tabular-nums}
.stage h4{font-family:var(--mono);font-size:.82rem;letter-spacing:.04em;color:var(--ink)}
.stage .what{font-size:.95rem;color:var(--ink);font-family:var(--serif);margin:.15rem 0 .35rem}
.stage p{font-size:.87rem;color:var(--muted)}
.cost{font-family:var(--mono);font-size:.68rem;color:var(--muted);white-space:nowrap;
  background:var(--surface-2);border:1px solid var(--rule);border-radius:20px;padding:.3em .8em}
.cmd{font-family:var(--mono);font-size:.95rem;background:var(--surface);border:1px solid var(--rule);
  border-left:3px solid var(--accent);border-radius:8px;padding:16px 18px;overflow-x:auto;color:var(--ink)}
.links td:last-child{font-family:var(--mono);font-size:.8rem}
.links td a{overflow-wrap:anywhere}
</style>
<div class="wrap">''')

    A('<header class="hdr sec"><div class="eyebrow"><span>Workflow</span>'
      '<span>research/dropship</span><span>playbooks/brand-swipe.md</span></div>'
      '<h1>The Swipe Machine</h1>'
      '<p class="stand">Point it at a competitor\'s domain. It comes back with '
      '<strong>every ad they are running, every page on their site, and the media on the drive</strong> '
      '— filed, sorted and linked. Reading it is the only part left to a person.</p>'
      '<div class="toc"><a href="#run">The command</a><a href="#stages">Nine stages</a>'
      '<a href="#library">The library</a><a href="#lands">Where it lands</a>'
      '<a href="#human">Stage ten</a><a href="#traps">Traps</a></div></header><hr class="rule">')

    A('<section class="sec" id="run"><h2>The command</h2>'
      '<div class="col prose"><p>One line. It runs the nine stages in order and stops at the first failure.</p></div>'
      '<div class="cmd">cd research/dropship<br>python3 swipe.py brand-c.shop</div>'
      '<div class="col prose"><p>Every stage is re-runnable — downloads and copies skip what is already '
      'there — so <code>--from library</code> picks up a broken run without paying for the sweep twice. '
      '<code>--max 1200</code> caps how much of a whale\'s library gets bought; the run says whether it '
      'exhausted their library or hit the cap, and every count in the teardown depends on which.</p></div></section>')

    A('<section class="sec" id="stages"><h2>Nine stages</h2>'
      '<div class="col prose"><p>The order matters: each stage feeds the next, and the two that '
      'cost money come first so a mistake is caught before the free work runs.</p></div>'
      '<div class="findings" style="gap:.7rem;max-width:none">')
    for i, (name, what, why, cost) in enumerate(STAGES, 1):
        A(f'<div class="stage"><span class="no">{i:02d}</span><div>'
          f'<h4>{E(name)}</h4><div class="what">{what}</div><p>{why}</p></div>'
          f'<span class="cost">{E(cost)}</span></div>')
    A('</div></section>')

    # live library
    A('<section class="sec" id="library"><h2>The library, right now</h2>'
      '<div class="col prose"><p>Every brand swiped so far, live from the shared drive.</p></div>'
      '<div class="tbl-wrap"><table><thead><tr><th>Brand</th><th>Copy blocks</th>'
      '<th>Pages captured</th><th>Files</th><th>Teardown</th><th>On the drive</th>'
      '</tr></thead><tbody>')
    for b in sorted(os.listdir(dl.DRIVE)):
        p = os.path.join(dl.DRIVE, b)
        if not os.path.isdir(p) or b in ("refs", "swipes"):
            continue
        ang, pg = os.path.join(p, "angles"), os.path.join(p, "_pages")
        na = len(os.listdir(ang)) if os.path.isdir(ang) else 0
        npg = len(os.listdir(pg)) if os.path.isdir(pg) else 0
        files = sum(len(f) for _, _, f in os.walk(p))
        td = TEARDOWNS.get(b)
        td_html = f'<a href="{td[1]}" target="_blank" rel="noopener">{E(td[0])}</a>' if td else '<span class="dim">—</span>'
        u = dl.link(p)
        A(f'<tr><td><b>{E(b)}</b></td><td class="num">{na}</td><td class="num">{npg}</td>'
          f'<td class="num">{files:,}</td><td>{td_html}</td>'
          f'<td>{link_cell(u, "open")}</td></tr>')
    A('</tbody></table></div></section>')

    # where it lands
    A('<section class="sec" id="lands"><h2>Where everything lands</h2>'
      '<div class="col prose"><p>Words in git, media on the drive — and the deliverable in both, '
      'plus an artifact. The drive shape is the one <code>swipe-paid/</code> already used, so a new '
      'brand folder looks like every other one.</p></div>'
      '<pre class="tree">swipe-paid/\n'
      '  &lt;brand&gt;/\n'
      '    teardown.html · teardown.md\n'
      '    angles/\n'
      '      NN_&lt;angle-slug&gt;/     NN is rank by creative volume\n'
      '        _ANGLE.md           headline + primary text verbatim, counts, landing pages\n'
      '        video/              &lt;ad_id&gt;.mp4 + &lt;ad_id&gt;_poster.jpg\n'
      '        photos/             &lt;ad_id&gt;.jpg\n'
      '    _pages/\n'
      '      &lt;page-slug&gt;/          _PAGE.md · page.png · page.html · page.txt</pre>')
    A('<div class="tbl-wrap links"><table><thead><tr><th>What</th><th>Link</th></tr></thead><tbody>')
    rows = [("The whole swipe library", dl.DRIVE),
            ("Brand C — everything", os.path.join(dl.DRIVE, "brand-c")),
            ("Brand C — creatives by copy block", os.path.join(dl.DRIVE, "brand-c", "angles")),
            ("Brand C — their whole funnel", os.path.join(dl.DRIVE, "brand-c", "_pages")),
            ("Brand C — teardown (HTML)", os.path.join(dl.DRIVE, "brand-c", "teardown.html")),
            ("Brand C — teardown (Markdown)", os.path.join(dl.DRIVE, "brand-c", "teardown.md")),
            ("Competitor A — everything", os.path.join(dl.DRIVE, "competitor-a"))]
    for label, path in rows:
        u = dl.link(path)
        A(f'<tr><td>{E(label)}</td><td>{link_cell(u, u)}</td></tr>')
    A('</tbody></table></div></section>')

    A('<section class="sec" id="human"><h2>Stage ten is a person</h2>'
      '<div class="col prose"><p>The machine does not read the library. Someone opens the angles and the '
      'pages, works out what is actually going on, and writes it down. That judgement is the whole value '
      'of the exercise and it is deliberately not automated.</p>'
      '<p>What <em>is</em> automated is the shape of the write-up. The content file carries only what a '
      'person has to decide — the standfirst, the findings, the page notes, the offer and stack, take and '
      'beat. Every number, every copy block, every still and screenshot is read off the library. So two '
      'teardowns from two different months read as the same document.</p></div>'
      '<div class="cmd">python3 build_teardown_page.py &lt;brand&gt; &lt;brand&gt;-teardown-content.json &lt;brand&gt;-teardown-&lt;date&gt;.html</div>'
      '<div class="col prose"><p>Then: publish the artifact, add its row to <code>context/artifacts.md</code>, '
      'add rows to both swipe registries so a brand run can pull the structures on a match, and log the '
      'run in the scan history.</p></div></section>')

    A('<section class="sec" id="traps"><h2>Traps, each one earned</h2><div class="findings">')
    for t, d in TRAPS:
        A(f'<div class="finding"><p><b>{E(t)}.</b> {d}</p></div>')
    A('</div></section>')

    A('<hr class="rule"><footer><p>Tools in <code>research/dropship/</code>; the written procedure is '
      '<code>playbooks/brand-swipe.md</code>. Lab quarantine applies to everything on the drive: research '
      'material, not production assets.</p></footer></div>')

    out = "\n".join(P)
    open(out_path, "w").write(out)
    print(f"{out_path} · {len(out)/1024:.0f} KB")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
