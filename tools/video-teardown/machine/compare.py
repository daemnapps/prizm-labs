#!/usr/bin/env python3
"""Swipe vs ours — every frame, side by side.

    python3 compare.py <run-slug>

Cuts a still from the source video at each frame's timestamp and puts it
next to the frame we generated for it, with the directions underneath.
This is the review surface: it is the only way to see, in one pass,
whether our version of a format is actually the same format.

Written to compare-<slug>.html beside the board, so it serves from the
same place the board does.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C
import frames as F

HERE = Path(__file__).resolve().parent


def secs(span):
    """'1:15–1:29' -> 75.0, from the first timestamp in the span."""
    first = re.split(r"[–—-]", span.strip())[0].strip()
    m = re.match(r"(?:(\d+):)?(\d+)(?:\.(\d+))?$", first)
    if not m:
        return 0.0
    mins = int(m.group(1) or 0)
    return mins * 60 + int(m.group(2)) + float("0." + (m.group(3) or "0"))


def cut(video, at, dest):
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{at:.2f}", "-i", str(video),
         "-frames:v", "1", "-vf", "scale=540:-1", str(dest)],
        capture_output=True)
    return dest if dest.exists() else None


def field(block, label):
    m = re.search(rf"\*\*{label}:?\*\*\s*(.+?)(?=\n\*\*|\n>|\n!\[|\Z)",
                  block, re.S | re.I)
    return " ".join(m.group(1).split()) if m else ""


def spoken(block):
    m = re.search(r">\s*\*\*Say:?\*\*\s*(.+?)(?=\n|$)", block, re.I)
    return " ".join(m.group(1).split()) if m else ""


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build(slug):
    run = C.runs_root() / slug
    brief = run / "5-brief.md"
    if not brief.exists():
        sys.exit(f"no brief for {slug}")
    video = run / "source.mp4"
    gen_dir = run / "frames" / "frames"
    still_dir = run / "compare-stills"

    md = brief.read_text()
    scenes = F.parse(md)
    blocks = re.split(r"\n(?=\*\*(?:Frame|Scene) \d+)", md)
    by_n = {}
    for b in blocks:
        m = re.match(r"\*\*(?:Frame|Scene) (\d+)", b)
        if m:
            by_n[int(m.group(1))] = b

    rows = []
    for sc in scenes:
        b = by_n.get(sc["n"], "")
        at = secs(sc["span"])
        src = cut(video, at, still_dir / f"{sc['key']}.jpg") if video.exists() else None
        # Our frames are 2K PNGs, 2-3MB each. Forty of them in one page is
        # over 100MB and the browser never finishes painting it, so the
        # right-hand column just stays blank. Thumbnail for the review view;
        # the full-size original stays where it is.
        gen = None
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            p = gen_dir / f"{sc['key']}{ext}"
            if p.exists():
                thumb = still_dir / f"{sc['key']}-ours.jpg"
                if not thumb.exists():
                    thumb.parent.mkdir(parents=True, exist_ok=True)
                    subprocess.run(
                        ["sips", "-Z", "540", "-s", "format", "jpeg",
                         "-s", "formatOptions", "72", str(p), "--out", str(thumb)],
                        capture_output=True)
                gen = thumb if thumb.exists() else p
                break
        rows.append(dict(
            n=sc["n"], key=sc["key"], span=sc["span"],
            src=(src.relative_to(HERE) if src else None),
            gen=(gen.relative_to(HERE) if gen else None),
            src_shot=field(b, "Source"),
            film=field(b, "Film"), hear=field(b, "Hear"),
            wear=field(b, "Wearing"), cap=field(b, "On[- ]screen"),
            say=spoken(b)))

    cards = []
    for r in rows:
        src = (f'<img src="{r["src"]}" loading="lazy" alt="source frame">'
               if r["src"] else '<div class="miss">no still</div>')
        gen = (f'<img src="{r["gen"]}" loading="lazy" alt="our frame">'
               if r["gen"] else '<div class="miss">not generated</div>')
        bits = ""
        if r["src_shot"]:
            bits += f'<p class="srcshot"><b>Replaces</b> {esc(r["src_shot"])}</p>'
        if r["film"]:
            bits += f'<p><b>Film</b> {esc(r["film"])}</p>'
        if r["cap"]:
            bits += f'<p><b>On screen</b> {esc(r["cap"])}</p>'
        if r["hear"]:
            bits += f'<p><b>Hear</b> {esc(r["hear"])}</p>'
        if r["say"]:
            bits += f'<p><b>Say</b> {esc(r["say"])}</p>'
        cards.append(f"""
<section class="row" id="f{r['n']}">
  <div class="hd"><span class="num">Frame {r['n']}</span>
    <span class="span">{esc(r['span'])}</span></div>
  <div class="pair">
    <figure><figcaption>THE SWIPE</figcaption>{src}</figure>
    <figure><figcaption>OURS</figcaption>{gen}</figure>
  </div>
  <div class="dirs">{bits}</div>
</section>""")

    n_pairs = sum(1 for r in rows if r["src"] and r["gen"])
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>{slug} — swipe vs ours</title>
<style>
:root{{--bg:#0e1014;--card:#171a20;--ink:#e9ecf1;--dim:#8a919c;--line:#252a33;--hot:#ff6a55}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--ink);margin:0;padding:28px 18px 80px;
 font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
.wrap{{max-width:1040px;margin:0 auto}}
h1{{font-size:26px;letter-spacing:-.02em;margin:0 0 6px}}
.sub{{color:var(--dim);margin:0 0 26px}}
.row{{background:var(--card);border:1px solid var(--line);border-radius:10px;
 padding:16px 18px 14px;margin-bottom:16px}}
.hd{{display:flex;gap:12px;align-items:baseline;margin-bottom:12px}}
.num{{font-weight:750}} .span{{color:var(--dim);font:12px ui-monospace,Menlo,monospace}}
.pair{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
figure{{margin:0}}
figcaption{{font:10.5px ui-monospace,Menlo,monospace;letter-spacing:.14em;
 color:var(--dim);margin-bottom:6px}}
figure:last-child figcaption{{color:var(--hot)}}
img{{width:100%;border-radius:6px;display:block;background:#000}}
.miss{{aspect-ratio:9/16;display:grid;place-items:center;border:1px dashed var(--line);
 border-radius:6px;color:var(--dim);font-size:13px}}
.dirs{{margin-top:12px;padding-top:11px;border-top:1px solid var(--line);font-size:13.5px}}
.dirs p{{margin:0 0 5px;color:#c6ccd6}}
.srcshot{{color:#8a919c !important;font-style:italic}} .dirs b{{color:var(--dim);
 font:10.5px ui-monospace,Menlo,monospace;letter-spacing:.1em;margin-right:7px}}
@media(max-width:720px){{.pair{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">
<h1>{slug}</h1>
<p class="sub">{len(rows)} frames · {n_pairs} with both sides · left is the video we swiped, right is what we generated</p>
{''.join(cards)}
</div></body></html>"""

    out = HERE / f"compare-{slug}.html"
    out.write_text(html)
    print(out)
    print(f"{len(rows)} frames, {n_pairs} pairs")
    return out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "ai-swipe-luxe-foundation")
