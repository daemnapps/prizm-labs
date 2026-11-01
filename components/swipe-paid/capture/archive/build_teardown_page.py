#!/usr/bin/env python3
"""Render a brand teardown into the house format.

    python3 build_teardown_page.py <brand> <content.json> <out.html>

THE STRUCTURE IS FIXED. It was set by the Competitor A teardown (2026-08-19) and
every brand after it renders the same sections in the same order, so two
teardowns from two different months read as the same document:

    header            eyebrow · title · standfirst
    toc               jump links
    ratio             copy blocks vs creatives, drawn — the thesis as a picture
    metrics           five numbers
    #model            What they're actually doing
    #findings         Structural findings (+ evidence figures)
    #volume           Creative volume per copy block
    #map              Angle → landing page
    #pages            The funnel, page by page — EVERY captured page
    #quiz             The quiz, all the way through
    #wall             The creative wall — every angle, sampled
    #stack            Offer and stack
    #swipe            The swipe file — every copy block verbatim
    #tb               Take / beat

Everything countable is read off the library on disk. The content JSON carries
only what a person has to judge: standfirst, metrics, the model paragraph,
findings, per-page notes for the pages worth a sentence, the offer and stack
panels, take and beat. A page with no hand-written note still gets a card.

Stylesheet is teardown_page.css — shared, never per brand.
"""
import base64, collections, glob, html, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
E = html.escape
TYPE_ORDER = ["advertorial", "listicle", "prelander", "quiz", "review-page",
              "comparison", "product-page", "blog", "utility", "other"]
TYPE_LABEL = {"advertorial": "Advertorial", "listicle": "Listicle",
              "prelander": "Prelander", "quiz": "Quiz", "review-page": "Review page",
              "comparison": "Comparison", "product-page": "Product page",
              "blog": "Blog", "utility": "Utility", "other": "Page"}

def norm_copy(s):
    return re.sub(r"\d{10,}$", "", (s or "").strip()).strip()

def b64(path, quality=62, resize=None, crop=None):
    if not path or not os.path.exists(path):
        return None
    src = path
    if resize or crop:
        tmp = f"/tmp/_td_{os.getpid()}.jpg"
        cmd = ["magick", path]
        if resize: cmd += ["-resize", resize]
        if crop:   cmd += ["-crop", crop, "+repage"]
        cmd += ["-quality", str(quality), tmp]
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(tmp): return None
        src = tmp
    with open(src, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

def blocks_of(brand):
    d = json.load(open(os.path.join(HERE, "raw", f"{brand}_uniq.json")))
    g = collections.defaultdict(list)
    for a in d["items"]:
        g[(a.get("title") or "", norm_copy(a.get("description")))].append(a)
    lp = {}
    for f in glob.glob(os.path.join(HERE, "raw", "ad_*.json")):
        a = json.load(open(f))
        lp[a["id"]] = [l["url"].split("?")[0] for l in (a.get("landing_pages") or []) if l.get("url")]
    out = []
    for (t, b), ads in sorted(g.items(), key=lambda kv: -len(kv[1])):
        v = sum(1 for a in ads if a.get("video_url"))
        out.append({"title": t, "body": b, "n": len(ads), "video": v,
                    "static": len(ads) - v,
                    "lps": sorted({u for a in ads for u in lp.get(a["id"], [])})})
    return out

def media_urls(brand):
    """ad id -> (video url, image url) straight off the sweep, so a still on the
    wall links to the ad itself. These are the tool's own CDN files: they play."""
    d = json.load(open(os.path.join(HERE, "raw", f"{brand}_uniq.json")))
    return {a["id"]: (a.get("video_url"), a.get("image_url")) for a in d["items"]}

def drive_link(brand, *parts):
    try:
        sys.path.insert(0, HERE)
        import drive_links
        return drive_links.link(os.path.join(drive_links.DRIVE, brand, *parts))
    except Exception:
        return None

def wall(brand, per=14):
    root = os.path.join(HERE, "assets", brand, "by-angle")
    out = []
    for angle in sorted(os.listdir(root)):
        d = os.path.join(root, angle)
        if not os.path.isdir(d): continue
        pool = sorted(glob.glob(d + "/video/*_poster.jpg")) + sorted(glob.glob(d + "/image/*.jpg"))
        if not pool: continue
        step = max(1, len(pool) // per)
        out.append((angle, pool[::step][:per], len(pool)))
    return out

def shot_paths(brand):
    root = os.path.join(HERE, "assets", brand, "pages", "by-type")
    return {os.path.basename(os.path.dirname(p)): p
            for p in glob.glob(root + "/*/*/page.png")}

def px_height(p):
    h = subprocess.run(["identify", "-format", "%h", p], capture_output=True, text=True).stdout.strip()
    return int(h) if h.isdigit() else None

# The house structure, in order. A brand page that does not have all of these is
# not in the house format, and the build stops rather than shipping a one-off.
CONTRACT = [('<header class="col hdr">', "header"), ('<nav class="toc">', "toc"),
            ('<section class="ratio">', "ratio"), ('<section class="metrics">', "metrics"),
            ('id="model"', "the model"), ('id="findings"', "findings"),
            ('id="volume"', "volume bars"), ('id="map"', "angle → page table"),
            ('id="pages"', "the funnel"), ('id="quiz"', "the quiz"),
            ('id="wall"', "creative wall"), ('id="stack"', "offer and stack"),
            ('id="swipe"', "swipe file"), ('id="tb"', "take / beat"),
            ("<footer>", "footer")]

def verify(out):
    """Every brand renders the same sections in the same order, or the build fails."""
    at = -1
    for needle, label in CONTRACT:
        i = out.find(needle)
        if i < 0:
            sys.exit(f"STRUCTURE: missing section — {label}")
        if i < at:
            sys.exit(f"STRUCTURE: section out of order — {label}")
        at = i
    for tag in ("section", "article", "div", "figure", "ul", "table"):
        o, c = len(re.findall(rf"<{tag}[ >]", out)), out.count(f"</{tag}>")
        if o != c:
            sys.exit(f"STRUCTURE: unbalanced <{tag}> — {o} open, {c} close")

def main(brand, content_path, out_path):
    c = json.load(open(content_path))
    blocks = blocks_of(brand)
    pngs = shot_paths(brand)
    classified = json.load(open(os.path.join(HERE, "assets", brand, "pages", "_classified.json")))
    by_slug = {r["slug"]: r for r in classified}
    notes = {n["slug"]: n for n in c.get("pages", [])}
    total_creatives = sum(b["n"] for b in blocks)

    # which copy blocks land on which page
    lands = collections.defaultdict(list)
    for b in blocks:
        for u in b["lps"]:
            lands[u.rstrip("/")].append(b["title"] or "no copy")

    P, A = [], None
    P = []; A = P.append
    A('<meta charset="utf-8">')
    A(f'<title>{E(c["title"])}</title>\n<style>')
    A(open(os.path.join(HERE, "teardown_page.css")).read())
    A('''
.typerule{grid-column:1/-1;display:flex;align-items:baseline;gap:.8rem;margin:.6rem 0 -.2rem;
  border-bottom:1px solid var(--rule);padding-bottom:.4rem}
.typerule h3{font-size:1rem}
.typerule span{font-family:var(--mono);font-size:.7rem;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted)}
.qs .qtext{font-size:.82rem;color:var(--ink);line-height:1.45}
.allads{font-family:var(--mono);font-size:.66rem;letter-spacing:.06em;text-transform:uppercase;
  text-decoration:none;border-bottom:1px solid transparent;white-space:nowrap}
.allads:hover{border-bottom-color:var(--accent)}
.wall-grid a{position:relative;display:block;border-radius:4px;overflow:hidden}
.wall-grid a img{cursor:pointer}
.wall-grid a.isvid::after{content:"";position:absolute;inset:auto 6px 6px auto;width:18px;height:18px;
  border-radius:50%;background:rgba(0,0,0,.62);
  -webkit-mask:radial-gradient(circle,#000 99%,transparent);opacity:.9}
.wall-grid a.isvid::before{content:"";position:absolute;right:11px;bottom:11px;z-index:2;
  border-left:6px solid #fff;border-top:4px solid transparent;border-bottom:4px solid transparent}
.wall-grid a:hover img{outline:2px solid var(--accent);outline-offset:-2px}
.qs .qopts{font-size:.76rem;color:var(--muted);line-height:1.4}
</style>
<div class="wrap">''')

    # header + toc
    A('<header class="col hdr"><div class="eyebrow">'
      + "".join(f'<span>{E(x)}</span>' for x in c["eyebrow"]) + '</div>'
      f'<h1>{E(c["h1"])}</h1><p class="stand">{c["standfirst"]}</p></header>')
    A('<nav class="toc">' + "".join(
        f'<a href="#{s}">{E(l)}</a>' for s, l in c["toc"]) + '</nav>')

    # ratio — the thesis as a picture
    A('<section class="ratio"><div><span class="field-cap"><b>'
      f'{len(blocks)}</b>blocks of copy</span><div class="blocks">'
      + "<i></i>" * len(blocks) + '</div></div>'
      '<div><span class="field-cap"><b>' f'{total_creatives}</b>live creatives</span>'
      '<div class="dots">'
      + "".join(f'<i style="--d:{i}"></i>' for i in range(total_creatives))
      + '</div></div></section>')

    # metrics
    A('<section class="metrics">' + "".join(
        f'<div class="metric{" hot" if m.get("hot") else ""}">'
        f'<span class="v">{E(m["v"])}</span><span class="k">{E(m["k"])}</span></div>'
        for m in c["metrics"]) + '</section>')

    # the model
    A(f'<section class="col prose" id="model"><h2>What they\'re actually doing</h2>{c["model"]}</section>')

    # findings
    A('<section class="sec" id="findings"><h2>Structural findings</h2><div class="findings">')
    for f in c["findings"]:
        if isinstance(f, dict):
            A(f'<div class="finding"><p>{f["text"]}</p></div>')
            img = b64(os.path.join(HERE, f["ev"]), resize="900x", quality=68) if f.get("ev") else None
            if img:
                A(f'<figure class="ev"><img src="{img}" alt="{E(f.get("alt",""))}" loading="lazy">'
                  f'<figcaption>{f["cap"]}</figcaption></figure>')
        else:
            A(f'<div class="finding"><p>{f}</p></div>')
    A('</div></section>')

    # volume
    A('<section class="sec" id="volume"><h2>Creative volume per copy block</h2>'
      f'<p class="col dim lede">{c["volume_intro"]}</p><div class="bars">')
    top = blocks[0]["n"]
    for b in blocks:
        A(f'<div class="bar-row"><span class="bar-label">{E(b["title"] or "no copy")}</span>'
          f'<span class="bar-track"><span class="bar-fill" style="--w:{b["n"]/top*100:.1f}%"></span></span>'
          f'<span class="bar-num">{b["n"]}</span></div>')
    A('</div></section>')

    # angle -> lp
    A('<section class="sec" id="map"><h2>Angle → landing page</h2><div class="tbl-wrap"><table>'
      '<thead><tr><th>Creatives</th><th>Angle</th><th>Format</th><th>Landing page</th>'
      '<th>The ads</th></tr></thead><tbody>')
    angle_dirs = sorted(d for d in os.listdir(os.path.join(HERE, "assets", brand, "by-angle"))
                        if os.path.isdir(os.path.join(HERE, "assets", brand, "by-angle", d)))
    for bi, b in enumerate(blocks):
        fmt = (f'{b["video"]}v/{b["static"]}s' if b["video"] and b["static"]
               else ("video" if b["video"] else "static"))
        links = "<br>".join(
            f'<a href="{E(u)}" target="_blank" rel="noopener"><code>{E(u.replace("https://",""))}</code></a>'
            for u in b["lps"]) or '<span class="dim">unresolved</span>'
        folder = drive_link(brand, "angles", angle_dirs[bi]) if bi < len(angle_dirs) else None
        A(f'<tr><td class="num">{b["n"]}</td><td>{E(b["title"] or "—")}</td>'
          f'<td class="dim">{fmt}</td><td>{links}</td>'
          f'<td>{f"<a href={chr(34)}{folder}{chr(34)} target={chr(34)}_blank{chr(34)} rel={chr(34)}noopener{chr(34)}>watch</a>" if folder else "<span class=\'dim\'>—</span>"}</td></tr>')
    A('</tbody></table></div></section>')

    # funnel — every captured page that has a screenshot, grouped by type
    shown = [s for s in pngs if s in by_slug]
    shown.sort(key=lambda s: (TYPE_ORDER.index(by_slug[s]["type"])
                              if by_slug[s]["type"] in TYPE_ORDER else 99,
                              -(by_slug[s].get("chars") or 0)))
    A('<section class="sec" id="pages"><h2>The funnel, page by page</h2>'
      f'<p class="col dim lede">{c["funnel_intro"]}</p><div class="lps">')
    last_type = None
    for slug in shown:
        r = by_slug[slug]
        if r["type"] != last_type:
            last_type = r["type"]
            n = sum(1 for s in shown if by_slug[s]["type"] == last_type)
            A(f'<div class="typerule"><h3>{E(TYPE_LABEL.get(last_type, last_type))}</h3>'
              f'<span>{n} page{"s" if n != 1 else ""}</span></div>')
        note = notes.get(slug, {})
        src = pngs[slug]
        fold = b64(src, resize="260x", crop="260x360+0+0", quality=55)
        rib = b64(src, resize="72x", quality=44)
        h = px_height(src)
        codes = [x for k in ("product", "audience", "channel", "variant") for x in r.get(k, [])]
        facts = []
        if h: facts.append(("Page height", f"{h}px"))
        if r.get("chars"): facts.append(("Words", f'{r["chars"]//6:,}'))
        for k, v in note.get("facts", []): facts.append((k, v))
        facts_html = "".join(f'<div><dt>{E(k)}</dt><dd>{E(str(v))}</dd></div>' for k, v in facts[:3])
        angles = lands.get(r["url"].rstrip("/"), [])
        ang_html = ("<ul class=\"ang\">" + "".join(f'<li>{E(a)}</li>' for a in sorted(set(angles)))
                    + "</ul>") if angles else ""
        body = note.get("note") or (
            f'{TYPE_LABEL.get(r["type"], r["type"])}'
            + (f' · coded <code>{E(" · ".join(codes))}</code>' if codes else "")
            + ".")
        A(f'<article class="lp">'
          f'<div class="lp-shots"><img class="lp-fold" src="{fold}" alt="Top of {E(r["url"])}" loading="lazy">'
          f'<div class="lp-rib-wrap"><img class="lp-rib" src="{rib}" alt="Full page {E(r["url"])}" loading="lazy"></div></div>'
          f'<div class="lp-info"><span class="kind">{E(note.get("kind") or TYPE_LABEL.get(r["type"], r["type"]))}</span>'
          f'<h3><a href="{E(r["url"])}" target="_blank" rel="noopener">'
          f'<code>{E(r["url"].replace("https://",""))}</code></a></h3>'
          f'<p class="dim">{body}</p>'
          + (f'<dl class="facts">{facts_html}</dl>' if facts_html else "")
          + ang_html + '</div></article>')
    A('</div></section>')

    # quiz
    A('<section class="sec" id="quiz"><h2>The quiz, all the way through</h2>'
      f'<p class="col dim lede">{c["quiz_intro"]}</p><div class="qstrip">')
    for q in c.get("quiz_shots", []):
        img = b64(pngs.get(q["slug"]), resize="420x", quality=64)
        if img:
            A(f'<figure class="qs"><img src="{img}" alt="{E(q["cap"])}" loading="lazy">'
              f'<figcaption><span class="qn">{E(q["n"])}</span><span>{E(q["cap"])}</span></figcaption></figure>')
    for i, q in enumerate(c["quiz"], 1):
        A(f'<figure class="qs"><figcaption><span class="qn">{E(q[0])}</span>'
          f'<span><span class="qtext">{E(q[1])}</span><br>'
          f'<span class="qopts">{E(q[2])}</span></span></figcaption></figure>')
    A('</div></section>')

    # creative wall
    A('<section class="sec" id="wall"><h2>The creative wall</h2>'
      f'<p class="col dim lede">{c["wall_intro"]}</p><div class="walls">')
    ranked = {i + 1: b for i, b in enumerate(blocks)}
    media = media_urls(brand)
    for angle, files, total in wall(brand):
        b = ranked.get(int(angle[:2]), {})
        folder = drive_link(brand, "angles", angle)
        A(f'<div class="wall-block"><div class="wall-head">'
          f'<h4>{E(b.get("title") or angle)}</h4>'
          f'<span class="chip">{total} live</span>'
          f'<span class="dim">showing {len(files)}</span>'
          + (f'<a class="allads" href="{folder}" target="_blank" rel="noopener">'
             f'all {total} on the drive →</a>' if folder else "")
          + '</div><div class="wall-grid">')
        for f in files:
            u = b64(f, resize="200x", quality=55)
            if not u:
                continue
            aid = int(re.sub(r"\D", "", os.path.basename(f).split("_")[0]))
            vid, img = media.get(aid, (None, None))
            href = vid or img
            play = ' class="isvid"' if vid else ""
            if href:
                A(f'<a href="{E(href)}" target="_blank" rel="noopener" title="ad {aid} — '
                  f'{"watch the video" if vid else "open the image"}"{play}>'
                  f'<img src="{u}" alt="Ad {aid}" loading="lazy"></a>')
            else:
                A(f'<img src="{u}" alt="Ad {aid}" loading="lazy">')
        A('</div></div>')
    A('</div></section>')

    # offer and stack
    A('<section class="sec" id="stack"><h2>Offer and stack</h2><div class="two">')
    for panel in c["panels"]:
        A(f'<div class="panel"><h3>{E(panel["h"])}</h3><ul class="tight">'
          + "".join(f'<li>{x}</li>' for x in panel["items"]) + '</ul></div>')
    A('</div></section>')

    # swipe file
    A('<section class="sec" id="swipe"><h2>The swipe file</h2>'
      f'<p class="col dim lede">{c["swipe_intro"]}</p><div class="swipes">')
    bodies = []
    for i, b in enumerate(blocks):
        bodies.append(b["body"])
        longish = " is-long" if len(b["body"]) > 700 else ""
        fmt = (f'{b["video"]} video / {b["static"]} static' if b["video"] and b["static"]
               else (f'{b["video"]} video' if b["video"] else f'{b["static"]} static'))
        folder = drive_link(brand, "angles", angle_dirs[i]) if i < len(angle_dirs) else None
        A(f'<article class="swipe{longish}"><div class="swipe-head"><div>'
          f'<h3>{E(b["title"] or "no copy")}</h3>'
          f'<div class="swipe-meta"><span class="chip">{b["n"]} creatives</span>'
          f'<span class="chip">{fmt}</span>'
          + (f'<a class="allads" href="{folder}" target="_blank" rel="noopener">'
             f'see the ads →</a>' if folder else '')
          + '</div></div>'
          f'<button class="copy" data-i="{i}">Copy</button></div>'
          f'<div class="swipe-body"><p>{E(b["body"])}</p></div>'
          + ('<button class="more">Read full copy</button>' if longish else '')
          + '</article>')
    A('</div></section>')

    # take / beat
    A('<section class="sec" id="tb"><h2>What to take, and what to beat</h2><div class="tb">')
    for key, tag, label in (("take", "t", "Take"), ("beat", "b", "Beat")):
        A(f'<div class="tb-col"><h3><span class="tag {tag}">{label}</span></h3><ul>'
          + "".join(f'<li>{x}</li>' for x in c[key]) + '</ul></div>')
    A('</div></section>')

    A(f'<hr class="rule"><footer>{"".join(f"<p>{x}</p>" for x in c["footer"])}</footer></div>')
    A('<script>const BODIES=' + json.dumps(bodies) + ';')
    A('''
document.querySelectorAll('.copy').forEach(b=>{b.addEventListener('click',async()=>{
  try{await navigator.clipboard.writeText(BODIES[+b.dataset.i]);b.textContent='Copied';b.classList.add('done');
    setTimeout(()=>{b.textContent='Copy';b.classList.remove('done')},1600)}
  catch(e){b.textContent='Press \\u2318C';setTimeout(()=>b.textContent='Copy',1600)}})});
document.querySelectorAll('.more').forEach(b=>{b.addEventListener('click',()=>{
  const c=b.closest('.swipe');b.textContent=c.classList.toggle('open')?'Collapse':'Read full copy'})});
document.querySelectorAll('.lp-rib, .qs img').forEach(i=>{
  i.addEventListener('click',()=>i.classList.toggle('zoom'))});
</script>''')

    out = "\n".join(P)
    verify(out)
    if len(out) > 15_500_000:
        sys.exit(f"SIZE: {len(out)/1e6:.1f} MB — over the 16 MB artifact cap. "
                 f"Drop the fold/ribbon quality or the wall sample.")
    open(out_path, "w").write(out)
    print(f"{out_path} · {len(out)/1e6:.2f} MB · {len(blocks)} copy blocks · "
          f"{len(shown)} page cards · {sum(len(f) for _,f,_ in wall(brand))} stills")

if __name__ == "__main__":
    if len(sys.argv) < 4: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
