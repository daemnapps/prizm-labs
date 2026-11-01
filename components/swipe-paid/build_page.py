#!/usr/bin/env python3
"""Render a brand's swipe into the one-page teardown, from what is on disk.

    python3 build_page.py <brand> [--quiz <walk-dir> ...] [--md]

--md also writes teardown.md from the content json. Never use it on a brand whose
teardown.md is hand-written (it would overwrite it).

Reads <brand>/blocks.json, <brand>/pages.json, <brand>/teardown-content.json,
the harvested creatives on the Drive mirror and the captured pages, and writes
<brand>/teardown.html. Same sections, same order as every other brand page
(see capture/build_teardown_page.py for the older builder this replaces for
brands swept after 2026-09-19). Stylesheet is page.css — shared, never per brand.

Everything countable is read off the library. The content JSON carries only what
a person has to judge: standfirst, metrics, the model, findings, page notes,
offer and stack panels, take and beat.
"""
import base64, glob, html, json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # page_slug
import swipe_home  # the swipe home, one definition for both pools (build put it on the path)

HERE = os.path.dirname(os.path.abspath(__file__))
E = html.escape
DRIVE = str(swipe_home.root("paid"))
TMP = tempfile.mkdtemp(prefix="pg_")


def b64(path, resize=None, crop=None, quality=55):
    if not path or not os.path.exists(path):
        return None
    out = os.path.join(TMP, f"{abs(hash((path, resize, crop)))}.jpg")
    cmd = ["magick", path + "[0]"]
    if crop:
        cmd += ["-crop", crop, "+repage"]
    if resize:
        cmd += ["-resize", resize]
    cmd += ["-strip", "-quality", str(quality), out]
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out):
        return None
    return "data:image/jpeg;base64," + base64.b64encode(open(out, "rb").read()).decode()


def short(u):
    return re.sub(r"^https?://", "", (u or "").split("?")[0])


def main(brand, quiz_dirs):
    root = os.path.join(HERE, brand)
    doc = json.load(open(os.path.join(root, "blocks.json")))
    blocks = doc["blocks"]
    pages = json.load(open(os.path.join(root, "pages.json")))
    c = json.load(open(os.path.join(root, "teardown-content.json")))
    css = open(os.path.join(HERE, "page.css")).read()
    total = sum(b["count"] for b in blocks)
    o = []
    A = o.append

    A(f'<meta charset="utf-8">\n<title>{E(c["title"])}</title>\n'
      '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
      f'<style>\n{css}\n</style>\n<div class="wrap">')

    A('<header class="col hdr"><div class="eyebrow">'
      + "".join(f"<span>{E(x)}</span>" for x in c["eyebrow"]) + "</div>"
      f'<h1>{E(c["h1"])}</h1><p class="stand">{c["standfirst"]}</p></header>')
    A('<nav class="toc">' + "".join(
        f'<a href="#{s}">{E(l)}</a>' for s, l in c["toc"]) + "</nav>")

    A('<section class="ratio"><div><span class="field-cap"><b>'
      f'{len(blocks)}</b>blocks of copy</span><div class="blocks">'
      + "<i></i>" * len(blocks) + "</div></div>"
      f'<div><span class="field-cap"><b>{total:,}</b>live creatives</span>'
      '<div class="dots">'
      + "".join(f'<i style="--d:{i}"></i>' for i in range(total))
      + "</div></div></section>")

    A('<section class="metrics">' + "".join(
        f'<div class="metric{" hot" if m.get("hot") else ""}">'
        f'<span class="v">{E(m["v"])}</span><span class="k">{E(m["k"])}</span></div>'
        for m in c["metrics"]) + "</section>")

    A(f'<section class="col prose" id="model"><h2>What they\'re actually doing</h2>{c["model"]}</section>')

    A('<section class="sec" id="findings"><h2>Structural findings</h2><div class="findings">'
      + "".join(f'<div class="finding"><p>{f["text"]}</p></div>' for f in c["findings"])
      + "</div></section>")

    # volume
    top = blocks[:15]
    mx = top[0]["count"]
    A('<section class="sec" id="volume"><h2>Creative volume per copy block</h2>'
      f'<p class="col dim lede">{c["volume_intro"]}</p><div class="bars">')
    for b in top:
        lab = f'{b["nn"]} · {(b["primary_text"] or b["headline"])[:46]}'
        A(f'<div class="bar-row"><span class="bar-label">{E(lab)}…</span>'
          f'<span class="bar-track"><span class="bar-fill" style="--w:{100*b["count"]/mx:.1f}%"></span></span>'
          f'<span class="bar-num">{b["count"]}</span></div>')
    A("</div></section>")

    # angle -> page
    A('<section class="sec" id="map"><h2>Angle → landing page</h2><div class="tbl-wrap"><table>'
      "<thead><tr><th>Creatives</th><th>Angle</th><th>Format</th><th>Landing page</th>"
      "<th>The ads</th></tr></thead><tbody>")
    for b in blocks:
        fmt = (f'{b["video_count"]} video / {b["image_count"]} static'
               if b["video_count"] and b["image_count"]
               else (f'{b["video_count"]} video' if b["video_count"] else f'{b["image_count"]} static'))
        lp = short(b["landing_page"]) if b.get("landing_page") else ""
        rep = b["media"].get(str(b["rep_ad_id"]), {}) if b.get("media") else {}
        ad = rep.get("video") or rep.get("image")
        A(f'<tr><td class="num">{b["count"]}</td><td>{b["nn"]} · {E(b["headline"])}</td>'
          f'<td class="dim">{fmt}</td>'
          f'<td><a href="https://{E(lp)}" target="_blank" rel="noopener"><code>{E(lp)}</code></a></td>'
          + (f'<td><a href="{E(ad)}" target="_blank" rel="noopener">a sample →</a></td>' if ad
             else "<td><span class='dim'>—</span></td>") + "</tr>")
    A("</tbody></table></div></section>")

    # funnel pages — every captured page, grouped by what it structurally is
    plist = c.get("pages") or [{"slug": k, "kind": "", "note": ""} for k in pages]
    notes = {p["slug"]: p for p in plist}
    for k, v in pages.items():
        notes.setdefault(k, {"slug": k, "kind": "", "note": ""})
    A('<section class="sec" id="pages"><h2>The funnel, page by page</h2>'
      f'<p class="col dim lede">{c["funnel_intro"]}</p><div class="lps">')
    order = ["advertorial", "listicle", "prelander", "quiz", "review-page", "salespage",
             "comparison", "product-page", "blog", "utility", "unknown"]
    by_type = {}
    for slug, p in notes.items():
        by_type.setdefault((pages.get(slug, {}).get("type") or "unknown"), []).append(p)
    for t in sorted(by_type, key=lambda x: order.index(x) if x in order else 99):
        A(f'<div class="typerule"><h3>{E(t.replace("-", " ").capitalize())}</h3><span>{len(by_type[t])} pages</span></div>')
        for p in by_type[t]:
            png = os.path.join(DRIVE, brand, "_pages", p["slug"], "page.png")
            fold = b64(png, resize="300x", crop="780x1688+0+0")
            rib = b64(png, resize="104x", quality=40)
            meta = pages.get(p["slug"], {})
            u = short(meta.get("url", f"shop/{p['slug']}"))
            angs = [b for b in blocks if b.get("landing_page") and build.page_slug(b["landing_page"]) == p["slug"]]
            A('<article class="lp"><div class="lp-shots">'
              + (f'<img class="lp-fold" src="{fold}" alt="Top of {E(u)}" loading="lazy">' if fold else "")
              + ('<div class="lp-rib-wrap">' + f'<img class="lp-rib" src="{rib}" alt="Full page {E(u)}" loading="lazy"></div>' if rib else "")
              + f'</div><div class="lp-info"><span class="kind">{E(p.get("kind") or t.replace("-", " ").capitalize())}</span>'
              f'<h3><a href="https://{E(u)}" target="_blank" rel="noopener"><code>{E(u)}</code></a></h3>'
              + (f'<p class="dim">{p["note"]}</p>' if p.get("note") else "")
              + f'<dl class="facts"><div><dt>Page height</dt><dd>{meta.get("height") or "—"}{"px" if meta.get("height") else ""}</dd></div>'
              f'<div><dt>Blocks</dt><dd>{len(angs)}</dd></div></dl>'
              '<ul class="ang">' + "".join(
                  f'<li>{b["nn"]} · {E(b["headline"][:44])} ({b["count"]})</li>' for b in angs[:6])
              + "</ul></div></article>")
    A("</div></section>")

    # quiz
    if c.get("quiz_intro"):
      A('<section class="sec" id="quiz"><h2>The quiz, all the way through</h2>'
      f'<p class="col dim lede">{c["quiz_intro"]}</p><div class="qstrip">')
    want = [tuple(x) for x in c.get("quiz_want", [])]   # (text to find, caption), per brand
    for qd in quiz_dirs:
        steps = json.load(open(os.path.join(qd, "steps.json")))
        used = set()
        for n, (key, cap) in enumerate(want, 1):
            hit = next((s for s in steps if key.lower() in (s["text"] + s["url"]).lower()
                        and s["step"] not in used), None)
            if not hit:
                continue
            used.add(hit["step"])
            img = b64(os.path.join(qd, f'step-{hit["step"]:02d}.png'), resize="360x", quality=60)
            if img:
                first = next((l for l in hit["text"].splitlines() if l.strip()), "")
                A(f'<figure class="qs"><img src="{img}" alt="{E(cap)}" loading="lazy">'
                  f'<figcaption><span class="qn">{n}</span><span>{E(cap)}<br>'
                  f'<span class="qopts">{E(first[:70])}</span></span></figcaption></figure>')
    if c.get("quiz_intro"):
      A("</div></section>")

    # wall
    A('<section class="sec" id="wall"><h2>The creative wall</h2>'
      f'<p class="col dim lede">{c["wall_intro"]}</p><div class="walls">')
    for b in [x for x in blocks if x["count"] >= 7]:
        base = os.path.join(DRIVE, brand, "blocks", b["slug"])
        pool = []
        for aid, m in b["media"].items():
            if m.get("video"):
                pool.append((aid, os.path.join(base, "video", f"{aid}_poster.jpg"), m["video"], True))
            elif m.get("image"):
                pool.append((aid, os.path.join(base, "photos", f"{aid}.jpg"), m["image"], False))
        pool = [p for p in pool if os.path.exists(p[1])]
        per = 16 if b["count"] > 100 else 8
        step = max(1, len(pool) // per)
        pick = pool[::step][:per]
        if not pick:
            continue
        A(f'<div class="wall-block"><div class="wall-head"><h4>{b["nn"]} · {E((b["primary_text"] or b["headline"])[:60])}…</h4>'
          f'<span class="chip">{b["count"]} live</span><span class="dim">showing {len(pick)}</span></div><div class="wall-grid">')
        for aid, path, url, isvid in pick:
            img = b64(path, resize="150x", quality=45)
            if img:
                cls = ' class="isvid"' if isvid else ''
                A(f'<a href="{E(url)}" target="_blank" rel="noopener" title="ad {aid}{" — watch the video" if isvid else ""}"'
                  f'{cls}><img src="{img}" alt="Ad {aid}" loading="lazy"></a>')
        A("</div></div>")
    A("</div></section>")

    # stack
    A('<section class="sec" id="stack"><h2>Offer and stack</h2><div class="two">'
      + "".join(f'<div class="panel"><h3>{E(p["h"])}</h3><ul class="tight">'
                + "".join(f"<li>{x}</li>" for x in p["items"]) + "</ul></div>" for p in c["panels"])
      + "</div></section>")

    # swipe file
    A('<section class="sec" id="swipe"><h2>The swipe file</h2>'
      f'<p class="col dim lede">{c["swipe_intro"]}</p><div class="swipes">')
    bodies = []
    for i, b in enumerate(blocks):
        body = b["primary_text"] or ""
        bodies.append(body)
        longish = " is-long" if len(body) > 700 else ""
        fmt = (f'{b["video_count"]} video / {b["image_count"]} static' if b["video_count"] and b["image_count"]
               else (f'{b["video_count"]} video' if b["video_count"] else f'{b["image_count"]} static'))
        A(f'<article class="swipe{longish}"><div class="swipe-head"><div>'
          f'<h3>{b["nn"]} · {E(b["headline"] or "no headline")}</h3>'
          f'<div class="swipe-meta"><span class="chip">{b["count"]} creatives</span>'
          f'<span class="chip">{fmt}</span></div></div>'
          f'<button class="copy" data-i="{i}">Copy</button></div>'
          f'<div class="swipe-body"><p>{E(body)}</p></div>'
          + ('<button class="more">Read full copy</button>' if longish else "") + "</article>")
    A("</div></section>")

    # take / beat
    A('<section class="sec" id="tb"><h2>What to take, and what to beat</h2><div class="tb">')
    for key, tag, label in (("take", "t", "Take"), ("beat", "b", "Beat")):
        A(f'<div class="tb-col"><h3><span class="tag {tag}">{label}</span></h3><ul>'
          + "".join(f"<li>{x}</li>" for x in c[key]) + "</ul></div>")
    A("</div></section>")

    A('<hr class="rule"><footer>' + "".join(f"<p>{x}</p>" for x in c["footer"]) + "</footer></div>")
    A("<script>const BODIES=" + json.dumps(bodies) + ";\n"
      "document.querySelectorAll('.copy').forEach(b=>{b.addEventListener('click',async()=>{\n"
      "  try{await navigator.clipboard.writeText(BODIES[+b.dataset.i]);b.textContent='Copied';b.classList.add('done');\n"
      "    setTimeout(()=>{b.textContent='Copy';b.classList.remove('done')},1600)}\n"
      "  catch(e){b.textContent='Press \\u2318C';setTimeout(()=>b.textContent='Copy',1600)}})});\n"
      "document.querySelectorAll('.more').forEach(b=>{b.addEventListener('click',()=>{\n"
      "  const c=b.closest('.swipe');b.textContent=c.classList.toggle('open')?'Collapse':'Read full copy'})});\n"
      "document.querySelectorAll('.lp-rib, .qs img').forEach(i=>{\n"
      "  i.addEventListener('click',()=>i.classList.toggle('zoom'))});\n</script>")

    out = os.path.join(root, "teardown.html")
    open(out, "w").write("\n".join(o))
    print(f"{out}  {os.path.getsize(out)/1e6:.1f} MB")


def strip(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    return html.unescape(t)


def write_md(brand):
    """The Markdown mirror the team reads. Same content, no pictures."""
    root = os.path.join(HERE, brand)
    doc = json.load(open(os.path.join(root, "blocks.json")))
    c = json.load(open(os.path.join(root, "teardown-content.json")))
    o = [f'# {c["h1"]}', "", " · ".join(c["eyebrow"]), "", strip(c["standfirst"]), ""]
    o += ["## Numbers", ""] + [f'- **{m["v"]}** {m["k"]}' for m in c["metrics"]] + [""]
    o += ["## What they're actually doing", "", strip(c["model"].replace("</p>", "\n\n")), ""]
    o += ["## Structural findings", ""] + [f'- {strip(f["text"])}' for f in c["findings"]] + [""]
    o += ["## The funnel", "", strip(c["funnel_intro"]), ""]
    o += [f'- **{p["slug"]}** — {p["kind"]}. {strip(p["note"])}' for p in c["pages"]] + [""]
    o += ["## The quiz", "", strip(c["quiz_intro"]), ""]
    o += ["## Offer and stack", ""]
    for p in c["panels"]:
        o += [f'### {p["h"]}', ""] + [f'- {strip(x)}' for x in p["items"]] + [""]
    o += ["## What to take", ""] + [f'- {strip(x)}' for x in c["take"]] + [""]
    o += ["## What to beat", ""] + [f'- {strip(x)}' for x in c["beat"]] + [""]
    o += ["## The swipe file", "", strip(c["swipe_intro"]), ""]
    for b in doc["blocks"]:
        o += [f'### {b["nn"]} · {b["headline"]}', "",
              f'{b["count"]} creatives ({b["video_count"]} video, {b["image_count"]} static) · {b["variants"]} variants', "",
              "> " + (b["primary_text"] or "").replace("\n", "\n> "), ""]
    o += ["---", ""] + [strip(x) + "\n" for x in c["footer"]]
    out = os.path.join(root, "teardown.md")
    open(out, "w").write("\n".join(o))
    print(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    qd = []
    a = sys.argv[2:]
    while a:
        if a[0] == "--quiz":
            qd.append(a[1]); a = a[2:]
        else:
            a = a[1:]
    main(sys.argv[1], qd)
    if "--md" in sys.argv:          # only for brands whose write-up IS generated from the content json
        write_md(sys.argv[1])
