#!/usr/bin/env python3
"""Draw the page machine's board: every run, every stage, the prompt as it was
sent and what came back. Reads runs/<label>/ and the chain's shape from run.py;
writes pages/board.html. Never hand-edited. Republish over the artifact link in
context/artifacts.md after every run.

    python3 board.py
"""
import html, json, re, sys, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "machine"))
from run import STAGES, SPEC   # noqa: E402
import page_paths as P         # noqa: E402
import page_gates as G         # noqa: E402

RUNS = P.RUNS                  # runs/page-machine/<brand>/<label>/; the old runs/ is read too (P.all_runs)
OUT = HERE / "pages" / "board.html"

def esc(s): return html.escape(s or "", quote=False)

def md(text):
    """A light Markdown → HTML: headings, fenced code, lists, paragraphs, bold, code."""
    out, para, in_code, in_list = [], [], False, None
    def flush():
        nonlocal para
        if para:
            t = " ".join(para).strip()
            if t: out.append(f"<p>{inline(t)}</p>")
            para = []
    def inline(t):
        t = esc(t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", t)
        t = re.sub(r"\[(UNFILLED[^\]]*)\]", r'<span class="unfilled">[\1]</span>', t)
        t = re.sub(r"\[(SLOT:[^\]]*)\]", r'<span class="slot">[\1]</span>', t)
        return t
    def end_list():
        nonlocal in_list
        if in_list: out.append(f"</{in_list}>"); in_list = None
    for line in text.splitlines():
        if line.strip().startswith("```"):
            flush(); end_list()
            if in_code: out.append("</pre>"); in_code = False
            else: out.append("<pre>"); in_code = True
            continue
        if in_code:
            out.append(esc(line)); continue
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            flush(); end_list()
            lvl = min(len(m.group(1)) + 2, 5)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>"); continue
        m = re.match(r"^\s*([-*]|\d+\.)\s+(.*)", line)
        if m:
            flush()
            tag = "ol" if m.group(1)[0].isdigit() else "ul"
            if in_list != tag: end_list(); out.append(f"<{tag}>"); in_list = tag
            out.append(f"<li>{inline(m.group(2))}</li>"); continue
        if line.startswith("|"):
            flush(); end_list()
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "): continue
            out.append("<div class='row'>" + "".join(f"<span>{inline(c)}</span>" for c in cells) + "</div>"); continue
        if line.startswith(">"):
            flush(); end_list(); out.append(f"<blockquote>{inline(line.lstrip('> '))}</blockquote>"); continue
        if not line.strip():
            flush(); end_list(); continue
        para.append(line)
    flush(); end_list()
    if in_code: out.append("</pre>")
    return "\n".join(out)

def stage_rows(run_dir, state):
    """Stage entries in chain order, sub-avatar stages grouped after the base."""
    st = state.get("stages", {})
    order = []
    for s in STAGES:
        if s["key"] in ("stage5", "stage6"): continue
        if s["key"] in st: order.append((s["key"], s))
    for k in ("stage6", "stage7"):
        if k in st: order.append((k, SPEC[k]))
    for sub in state.get("subs", []):
        for k in (f"stage5-{sub}", f"stage6-{sub}", f"stage7-{sub}"):
            if k in st: order.append((k, SPEC[k.split("-")[0]]))
    return order


def pictures_html(run_dir, state, sub=None):
    """The pictures a page was given: each brief beside what came back, inlined so the board carries them."""
    import base64, mimetypes
    suffix = "" if not sub else f"-{sub}"
    lp, pp = run_dir / f"layout{suffix}.json", run_dir / f"pictures{suffix}.json"
    if not lp.exists(): return ""
    plan = json.loads(lp.read_text()); made = json.loads(pp.read_text()) if pp.exists() else {}
    proj = Path.home() / "Projects" / f"{state['brand']}-pages" / "src" / state["funnel"] / "assets"
    cards = []
    for sec in plan["sections"]:
        for pic in sec.get("pictures", []):
            rec = made.get(pic["id"], {})
            img = ""
            asset = rec.get("asset")
            if asset and (proj / asset).exists():
                b = (proj / asset).read_bytes()
                if len(b) < 600_000:
                    mt = mimetypes.guess_type(asset)[0] or "image/jpeg"
                    img = f'<img src="data:{mt};base64,{base64.b64encode(b).decode()}" alt="{esc(pic.get("alt",""))}">'
            how = "the brand's own photograph" if pic.get("use") else ("reused: " + pic["reuse"]) if pic.get("reuse") else "generated to the brief"
            cards.append(f'<figure class="pic"><div class="picimg">{img or "<span class=muted>(not made yet)</span>"}</div><figcaption><b>{esc(pic["id"])}</b> <span class="muted">· {esc(sec["block"])} · {esc(how)}</span><p>{esc(pic.get("brief",""))}</p>{("<p class=muted>reference: " + esc(", ".join(pic.get("attach") or [])) + "</p>") if pic.get("attach") and pic.get("attach") != ["none"] else ""}</figcaption></figure>')
    if not cards: return ""
    return f'<details class="stage pictures" open><summary><span class="num">8</span><span class="name">Pictures{(" · " + esc(sub)) if sub else ""}</span><span class="blurb">Every picture slot: the brief as written, and what came back.</span></summary><div class="body picgrid">{"".join(cards)}</div></details>'

def render_run(run_dir):
    state = json.loads((run_dir / "run.json").read_text())
    label = state["label"]
    secs = sum((v.get("seconds") or 0) for v in state["stages"].values())
    head = f'''<section class="run" id="run-{esc(label)}">
<header class="runhead">
  <h2>{esc(state.get("page_name") or label)}</h2>
  <div class="meta">
    <span><b>run</b> {esc(label)}</span>
    <span><b>brand</b> {esc(state.get("brand"))}</span>
    <span><b>avatar</b> {esc(state.get("avatar"))}</span>
    <span><b>angle</b> {esc(state.get("angle"))}</span>
    <span><b>format</b> {esc(state.get("format"))} (classifier)</span>
    <span><b>hands off to</b> {esc(state.get("next"))}</span>
    <span><b>swipe</b> <a href="{esc(state.get("source_url"))}">{esc(state.get("swipe") or state.get("source_url"))}</a></span>
    <span><b>subs</b> {esc(", ".join(state.get("subs", [])) or "none")}</span>
    <span><b>started</b> {esc(state.get("started"))}</span>
    <span><b>stages done</b> {sum(1 for v in state["stages"].values() if v.get("status")=="done")} / {len(state["stages"])} · {round(secs/60,1)} min of model time</span>
  </div>
</header>'''
    parts = [head]
    held = G.held(run_dir)
    if held:
        rows = "".join(f"<li><b>{esc(g)} gate</b> — {esc(p_)}</li>" for g, ps in held.items() for p_ in ps)
        parts.append(f'<details class="stage" open><summary><span class="num">!</span><span class="name">HELD</span>'
                     f'<span class="blurb">this run is not delivered until these are fixed</span></summary>'
                     f'<div class="body"><ul>{rows}</ul></div></details>')
    picked = state.get("elements") or {}
    if picked:
        fmt_el = picked.get("format/page") or {}
        sec = picked.get("doctrine/section") or {}
        line = f"format <code>{esc(fmt_el.get('id'))}</code> ({esc(fmt_el.get('name'))}, {esc(fmt_el.get('status'))})"
        if sec:
            line += f" · sections carried: {esc(', '.join(sec.get('carried', [])) or 'none read')}"
            if sec.get("unknown"):
                line += f" · <b>not in the library:</b> {esc(', '.join(sec['unknown']))}"
        parts.append(f'<p class="muted">From the element library — {line}</p>')
    src = run_dir / "source.md"
    if src.exists():
        parts.append(f'<details class="stage source"><summary><span class="num">src</span><span class="name">The source page</span><span class="blurb">as read by the chain</span></summary><div class="body">{md(src.read_text())}</div></details>')
    last_group = None
    for key, spec in stage_rows(run_dir, state):
        info = state["stages"][key]
        sub = key.split("-", 1)[1] if "-" in key else ""
        group = spec["group"] if not sub else f"ONE PER SUB-AVATAR · {sub}"
        if group != last_group:
            parts.append(f'<h3 class="group">{esc(group)}</h3>'); last_group = group
        out_file = run_dir / (info.get("out") or "")
        sent_file = run_dir / (info.get("sent") or "")
        status = info.get("status")
        body = md(out_file.read_text()) if info.get("out") and out_file.exists() else f'<p class="muted">({esc(status)} — no output yet)</p>'
        sent = esc(sent_file.read_text()) if sent_file.exists() else ""
        stat = f'{esc(info.get("model",""))} · {info.get("seconds","–")}s · {info.get("chars_in",0):,} in / {info.get("chars_out",0):,} out'
        parts.append(f'''<details class="stage {esc(status)}" {"open" if spec["key"] in ("stage4","stage5") else ""}>
<summary><span class="num">{esc(spec["id"])}</span><span class="name">{esc(spec["name"])}{(" · " + esc(sub)) if sub else ""}</span><span class="blurb">{esc(spec["blurb"])}</span><span class="stat">{stat}</span></summary>
<div class="body">
<details class="sent"><summary>The prompt, as sent — <code>{esc(info.get("prompt_name",""))}</code> · sha {esc(info.get("prompt_sha256_12",""))}</summary><pre>{sent}</pre></details>
{body}
</div></details>''')
    parts.append(pictures_html(run_dir, state))
    for sub in state.get("subs", []):
        parts.append(pictures_html(run_dir, state, sub))
    parts.append("</section>")
    return parts, state

runs = sorted(P.all_runs(), key=lambda p: p.stat().st_mtime, reverse=True)
sections, nav = [], []
for r in runs:
    parts, state = render_run(r)
    sections.extend(parts)
    nav.append(f'<a href="#run-{esc(state["label"])}">{esc(state.get("page_name") or state["label"])}<small>{esc(state["label"])} · {esc(state.get("brand"))}</small></a>')

chain = "".join(f'<div class="step"><span class="num">{esc(s["id"])}</span><b>{esc(s["name"])}</b><span>{esc(s["blurb"])}</span></div>' for s in STAGES)
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

HTML = f'''<title>The Page Machine</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--ground:#F2ECE2;--surface:#FBF8F2;--ink:#2A1B12;--ink-2:#6B5A4C;--line:#DACFC0;--gold:#B7760F;--gold-ink:#7A4E08;--moringa:#4F6B3A;--flag:#A8422A;--code-bg:#EAE2D6;--unfilled-bg:#EFE6D3}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--ground:#1B140F;--surface:#241B15;--ink:#EFE6D8;--ink-2:#B3A392;--line:#3D3128;--gold:#E0A33A;--gold-ink:#F0C070;--moringa:#A6BE87;--flag:#E8916F;--code-bg:#32281F;--unfilled-bg:#33291E}}}}
:root[data-theme="dark"]{{--ground:#1B140F;--surface:#241B15;--ink:#EFE6D8;--ink-2:#B3A392;--line:#3D3128;--gold:#E0A33A;--gold-ink:#F0C070;--moringa:#A6BE87;--flag:#E8916F;--code-bg:#32281F;--unfilled-bg:#33291E}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:"Newsreader",Georgia,serif;font-size:17px;line-height:1.5;font-optical-sizing:auto}}
code{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.8em;background:var(--code-bg);padding:.05em .3em;border-radius:3px}}
pre{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12.5px;line-height:1.5;background:var(--code-bg);padding:14px;border-radius:5px;overflow-x:auto;white-space:pre-wrap;word-break:break-word;max-height:70vh;overflow-y:auto}}
.wrap{{max-width:1080px;margin:0 auto;padding:36px 24px 96px}}
h1{{font-weight:500;font-size:38px;line-height:1.05;margin:0 0 8px;letter-spacing:-.01em}}
.lede{{color:var(--ink-2);max-width:66ch;margin:0 0 22px}}
.mono,.meta,.stat,.num,.group,.step .num,summary .name small{{font-family:"IBM Plex Mono",ui-monospace,monospace}}
.chain{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0 0 28px}}
.step{{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:10px 12px;display:grid;gap:2px;font-size:14px}}
.step .num{{font-size:11px;letter-spacing:.08em;color:var(--gold-ink)}} .step b{{font-weight:500;font-size:16px}} .step span:last-child{{color:var(--ink-2);font-size:13.5px;line-height:1.35}}
nav.runs{{display:grid;gap:8px;margin:0 0 28px}} nav.runs a{{display:grid;background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:10px 14px;color:var(--ink);text-decoration:none;font-size:18px}} nav.runs a small{{font-size:12px;color:var(--ink-2);letter-spacing:.04em}}
.run{{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:22px 24px;margin:0 0 28px}}
.runhead h2{{margin:0 0 8px;font-weight:500;font-size:28px;letter-spacing:-.01em}}
.meta{{display:flex;flex-wrap:wrap;gap:6px 22px;font-size:12.5px;color:var(--ink-2)}} .meta b{{color:var(--gold-ink);font-weight:500;text-transform:uppercase;letter-spacing:.06em;font-size:10.5px;margin-right:6px}} .meta a{{color:inherit}}
h3.group{{font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-2);margin:26px 0 8px;font-weight:500}}
details.stage{{border:1px solid var(--line);border-radius:6px;margin:0 0 8px;background:var(--ground)}}
details.stage>summary{{cursor:pointer;display:grid;grid-template-columns:44px 1fr auto;gap:4px 14px;align-items:baseline;padding:10px 14px;list-style:none}}
details.stage>summary::-webkit-details-marker{{display:none}}
summary .num{{font-size:12px;color:var(--gold-ink);letter-spacing:.06em}} summary .name{{font-size:19px;font-weight:500}} summary .blurb{{grid-column:2;color:var(--ink-2);font-size:14px}} summary .stat{{font-size:11.5px;color:var(--ink-2);grid-column:3;grid-row:1}}
details.stage>.body{{padding:4px 18px 18px 58px;border-top:1px dashed var(--line)}}
details.stage>.body p,.body li{{max-width:72ch}}
details.sent{{margin:10px 0 14px}} details.sent summary{{cursor:pointer;font-size:13px;color:var(--ink-2)}}
.body h3,.body h4,.body h5{{font-weight:500;margin:1.2em 0 .4em}} .body h3{{font-size:22px}} .body h4{{font-size:18px}} .body h5{{font-size:16px}}
.row{{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(120px,1fr);gap:12px;padding:6px 0;border-bottom:1px solid var(--line);font-size:14.5px}}
blockquote{{margin:.6em 0;padding-left:14px;border-left:3px solid var(--gold);color:var(--ink)}}
.unfilled{{background:var(--unfilled-bg);color:var(--flag);padding:0 4px;border-radius:3px}} .slot{{color:var(--moringa)}}
.muted{{color:var(--ink-2)}}
.picgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;padding-top:14px}}
.pic{{margin:0;border:1px solid var(--line);border-radius:6px;background:var(--surface);overflow:hidden}}
.pic .picimg img{{width:100%;height:auto;display:block}} .pic figcaption{{padding:10px 12px;font-size:13.5px;line-height:1.4}} .pic figcaption p{{margin:.4em 0 0;color:var(--ink-2);font-size:12.5px}}
details.dry>summary .name::after{{content:" · dry";color:var(--ink-2);font-size:12px}}
@media (max-width:820px){{.chain{{grid-template-columns:1fr 1fr}} .wrap{{padding:20px 14px 60px}} details.stage>.body{{padding-left:14px}} details.stage>summary{{grid-template-columns:36px 1fr}} summary .stat{{grid-column:2;grid-row:auto}}}}
</style>
<div class="wrap">
<h1>The Page Machine</h1>
<p class="lede">One swipe page in, one pre-sell page out in our avatar's own words, then one page per sub-avatar. Every stage below shows the prompt exactly as it was sent and what came back, so the prompt can be tightened where the output went wrong. Drawn {now}.</p>
<div class="chain">{chain}</div>
<nav class="runs">{"".join(nav) or "<span class='muted'>no runs yet</span>"}</nav>
{"".join(sections)}
</div>
'''
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(HTML)
print("wrote", OUT, len(HTML), "chars;", len(runs), "run(s)")
