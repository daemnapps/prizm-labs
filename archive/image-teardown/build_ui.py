#!/usr/bin/env python3
"""The Image Machine — the same board as the video one, fed by image runs.

    python3 build_ui.py

Deliberately not its own design. It lifts the video board's own template
(components/video-teardown/machine/board.py) and patches the handful of places
that say "video" into the handful that say "ad", so the two boards stay one
board. When Dayu changes the video board's shape, a rebuild here picks it up.

Damon reviews in HTML. The .md files each run writes are what the team reads;
this page is built from those and never replaces them.
"""
import html as H, json, re, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
OUT = HERE / "image-board.html"
VIDEO_BOARD = (Path.home() /
               "Projects/ai-workspace/components/video-teardown/machine/board.py")

# Each stage: the file it writes, the name and one line on what it is for, and
# the block of work it belongs to. Mirrors the video board's stage plan.
PLAN = [
    # ---- stage one: swipe in, brief out -----------------------------------
    ("01-teardown",   "1", "Teardown",    "STAGE ONE · READ THE AD",
     "One ad in, an objective record out — every zone placed, the layout measured."),
    ("02-replication", "2", "The format", "STAGE ONE · READ THE AD",
     "The ad abstracted into a brand-free format, in words and as layout data."),
    ("03-injection",  "3", "Injection",   "STAGE ONE · MAKE IT OURS",
     "Our brand put through that format, one zone at a time."),
    ("04-headlines",  "4", "Headlines",   "STAGE ONE · MAKE IT OURS",
     "Six headlines, each on its own axis, each anchored to a real customer sentence."),
    ("05-image-variations", "5", "Picture variations", "STAGE ONE · MAKE IT OURS",
     "The genuinely different pictures this layout can carry, cheapest first."),
    ("06-brief",      "6", "The brief",   "STAGE ONE · THE BRIEF",
     "Everything the ad is, before anyone makes it — plus the build data and the claim trace."),

    # ---- stage two: brief in, finished ads out -----------------------------
    ("07-plates",     "7", "Make the plates", "STAGE TWO · BUILD IT",
     "The photographs, no words in them at all, made against the layout reference."),
    ("08-plate-check", "8", "Judge the plates", "STAGE TWO · BUILD IT",
     "The brief's own accept tests, run on the picture before anything is built on it."),
    ("09-measure",    "9", "Measure the plate", "STAGE TWO · BUILD IT",
     "Where the bands and the inset actually landed — the layout adapts to this picture."),
    ("10-product",   "10", "Composite the product", "STAGE TWO · BUILD IT",
     "The real packshot cut in. Never generated — a near-miss on a wordmark is worse than an absence."),
    ("11-type",      "11", "Set the type", "STAGE TWO · BUILD IT",
     "Every character exact, from the layout data. Never rendered by the image model."),
    ("12-proof",     "12", "Prove it", "STAGE TWO · BUILD IT",
     "Side by side with the source, with every warning the compositor raised."),
]

# Which engine writes which stage — Gemini reads the picture, Claude does the
# brand-side thinking, Higgsfield makes the plates. Shown so it is visible rather
# than trusted.
ENGINE = {"1": "gemini · 3.1 pro", "2": "gemini · 3.1 pro",
          "3": "claude · opus", "4": "claude · opus",
          "5": "claude · opus", "6": "claude · opus",
          "7": "higgsfield · nano_banana_pro", "8": "you",
          "9": "code", "10": "imagemagick", "11": "imagemagick",
          "12": "imagemagick"}


PRODUCTION = Path(__file__).resolve().parents[1] / "image-production/runs"


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, check=False).returncode == 0


def md_render(text):
    """Enough markdown to read a stage output on a page."""
    out, tbl, code = [], [], False
    def flush():
        if not tbl:
            return
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl]
        out.append("<table><thead><tr>"
                   + "".join(f"<th>{inline(c)}</th>" for c in rows[0])
                   + "</tr></thead><tbody>")
        for r in rows[2:]:
            out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
        out.append("</tbody></table>")
        tbl.clear()
    for ln in text.splitlines():
        if ln.strip().startswith("```"):
            flush()
            out.append("</pre>" if code else "<pre>")
            code = not code
            continue
        if code:
            out.append(H.escape(ln))
            continue
        if ln.strip().startswith("|"):
            tbl.append(ln)
            continue
        flush()
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            n = min(len(s) - len(s.lstrip("#")) + 2, 5)
            out.append(f"<h{n}>{inline(s.lstrip('# '))}</h{n}>")
        elif s.startswith(("- ", "* ")):
            out.append(f"<ul><li>{inline(s[2:])}</li></ul>")
        elif re.match(r"^\d+\.\s", s):
            stripped = re.sub(r"^\d+\.\s", "", s)
            out.append(f"<ul><li>{inline(stripped)}</li></ul>")
        else:
            out.append(f"<p>{inline(s)}</p>")
    flush()
    if code:
        out.append("</pre>")
    return "\n".join(out)


def inline(s):
    s = H.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\*\w])\*([^\*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    return s


def provenance(text):
    m = re.match(r"<!--\s*(.*?)\s*-->", text)
    return m.group(1) if m else ""


def prov_field(prov, key):
    m = re.search(rf"{key}:\s*([^|]+)", prov)
    return m.group(1).strip() if m else ""


def web_thumb(src: Path, run: Path, wide=520):
    """A jpeg beside the original that the page can load without inlining
    forty megabytes of PNG. Returns a path relative to this folder."""
    cache = run / "finals" / ".web"
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / (src.stem + ".jpg")
    if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
        sh(["magick", str(src), "-resize", f"{wide}x", "-quality", "82", str(dest)])
    return dest.relative_to(HERE).as_posix() if dest.exists() else ""


def verdicts(slug):
    """What the judge said about each plate, so the board shows it in place.

    A plate the judge rejected looks exactly like one it passed. Without the
    verdict beside the picture, the board invites you to trust a plate that
    was thrown away."""
    f = (PRODUCTION / slug / "out/08-plate-check.md")
    if not f.is_file():
        return {}
    out, cur = {}, None
    for line in f.read_text().splitlines():
        h = re.match(r"#+\s*(plate-\S+)", line)
        if h:
            cur = h.group(1)
        v = re.match(r"\*\*Verdict:\*\*\s*(PASS|FAIL)", line, re.I)
        if v and cur:
            out[cur + ".png"] = v.group(1).upper()
    return out


def delivered(slug):
    """The ad unit a run shipped, if it has been delivered.

    A board that shows pictures but not the name they went out under cannot
    answer "which of these is the row in my report" — which is the only
    question worth asking once spend is running."""
    for m in (PRODUCTION / slug).rglob("manifest.json"):
        try:
            d = json.loads(m.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if d.get("ad_name"):
            return {"ad_name": d["ad_name"], "batch": d.get("batch", ""),
                    "assets": len(d.get("ads", [])),
                    "by_file": {r["file"]: r["name"] for r in d.get("ads", [])}}
    return None


def pictures(run: Path):
    """Plates and finished ads live in the production run, the source in
    either — the split put them in two trees and the board only read one,
    so every plate and every ad was invisible here."""
    pics = []
    seen = set()
    v = verdicts(run.name)
    roots = [run, PRODUCTION / run.name]
    for root in roots:
      for sub, label in (("finals", "finished"), ("iterations", "plate"),
                         ("assets", "source")):
        d = root / sub
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            if f.name.startswith("."):
                continue
            if (label, f.name) in seen:
                continue
            seen.add((label, f.name))
            rel = web_thumb(f, run, 700)
            if rel:
                pics.append({"label": label, "name": f.name, "src": rel,
                             "verdict": v.get(f.name, "")})
    return pics


def collect():
    runs = []
    if not RUNS.is_dir():
        return runs
    for d in sorted(RUNS.iterdir(), reverse=True):
        # `archive/` holds finished experiments — kept on disk, off the board.
        if not d.is_dir() or d.name == "archive":
            continue
        out = d / "out"
        files = sorted(out.glob("*.md")) if out.is_dir() else []
        if not files and not (d / "finals").is_dir():
            continue
        # Several prefixes can name the same stage — file naming changed
        # between runs. Resolve each stage id to the first prefix that
        # actually matches a file, so a stage appears exactly once.
        by_id = {}
        for prefix, sid, name, group, blurb in PLAN:
            hit = next((f for f in files if f.name.startswith(prefix)), None)
            if sid not in by_id or (hit and by_id[sid][0] is None):
                by_id[sid] = (hit, sid, name, group, blurb)
        order = []
        for _, sid, _, _, _ in PLAN:
            if sid not in order:
                order.append(sid)

        stages, done = [], 0
        for sid in order:
            hit, sid, name, group, blurb = by_id[sid]
            rec = {"id": sid, "name": name, "group": group, "blurb": blurb,
                   "engine_planned": ENGINE.get(sid, ""),
                   "status": "waiting", "engine": "", "version": "",
                   "prompt_name": "", "prompt_html": "", "prompt_text": "",
                   "sent_html": "", "output_html": "", "output_text": "",
                   "chars": 0, "seconds": 0, "wants": []}
            if hit:
                raw = hit.read_text(errors="replace")
                prov = provenance(raw)
                body = re.sub(r"^<!--.*?-->\s*", "", raw, flags=re.S)
                rec.update(status="done", output_text=body,
                           output_html=md_render(body), chars=len(body),
                           engine=prov_field(prov, "model") or ENGINE.get(sid, ""),
                           prompt_name=prov_field(prov, "prompt") or hit.name,
                           wants=[v.strip() for v in
                                  prov_field(prov, "vars").split(",") if v.strip()])
                pf = HERE / "prompts" / rec["prompt_name"]
                if pf.is_file():
                    ptxt = pf.read_text(errors="replace")
                    rec["prompt_text"] = ptxt
                    rec["prompt_html"] = md_render(ptxt)
                done += 1
            stages.append(rec)

        pics = pictures(d)
        finished = [p for p in pics if p["label"] == "finished"]
        hero = next((p for p in finished if "sheet" in p["name"]),
                    finished[0] if finished else (pics[0] if pics else None))
        poster = hero["src"] if hero else ""
        kind = ("CLONES — proving the format" if "clone" in d.name
                or "<competitor>" in d.name else "VARIATIONS — new ads")
        date = d.name[:10] if re.match(r"\d{4}-\d{2}-\d{2}", d.name) else ""
        label = d.name[11:] if date else d.name
        bf = d / "vars/brand_name.md"
        brand = bf.read_text().strip().splitlines()[0] if bf.is_file() else ""
        if not brand:
            src = d / "assets/source.json"
            if src.is_file():
                try:
                    brand = json.loads(src.read_text()).get("brand", "")
                except Exception:
                    brand = ""
        runs.append({
            "slug": d.name, "label": label, "brand": brand, "creator": "",
            "lane": kind, "poster": poster, "hero": poster,
            "stamp": date, "pics": pics,
            "triage": {"lane": kind, "category": label.replace("-", " "),
                       "runtime": f"{len(finished)} finished",
                       "ai": "", "summary": ""},
            "stage_list": stages, "versions": [], "done": done,
            "delivered": delivered(d.name),
        })
    return runs


def template():
    src = VIDEO_BOARD.read_text()
    t = src.split('TEMPLATE = r"""', 1)[1].rsplit('"""', 1)[0]

    # --- the media: a still, not a player -------------------------------
    t = re.sub(r"<video src=[^>]*?></video>",
               '<img class="hero" src="${r.hero||\'\'}" alt="">', t, flags=re.S)
    t = t.replace(".runhead video{", ".runhead img.hero{")
    t = t.replace(".runhead video{width:104px}", ".runhead img.hero{width:104px}")
    t = t.replace('.runhead video{width:104px}', '.runhead img.hero{width:104px}')

    # rail thumbnails already sit at runs/<slug>/… in the video board; ours
    # carry a path relative to this folder instead.
    t = t.replace('<img src="runs/${r.slug}/${r.poster}" alt="">',
                  '<img src="${r.poster}" alt="">')

    # --- the words ------------------------------------------------------
    t = t.replace("<title>The Swipe Machine</title>",
                  "<title>The Image Machine</title>")
    t = t.replace(">The Swipe Machine<", ">The Image Machine<")
    t = t.replace("video in &rarr; brief out", "one static ad in &rarr; a set out")
    t = t.replace("Search videos, category, lane…", "Search runs, formats, lanes…")
    t = t.replace('video${RUNS.length===1?"":"s"}', 'run${RUNS.length===1?"":"s"}')
    t = t.replace("Re-run this video to bring it in line.",
                  "Re-run this ad to bring it in line.")

    # --- the gallery, appended under the stages -------------------------
    gallery_css = """
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
  gap:10px;margin:10px 0 26px}
.gallery figure{margin:0;background:var(--paper);border:1px solid var(--line);
  border-radius:8px;overflow:hidden}
.gallery img{width:100%;height:190px;object-fit:contain;background:var(--ground);
  display:block;cursor:zoom-in}
.vd{margin-left:7px;font-weight:700;letter-spacing:.06em;padding:1px 6px;
border-radius:20px}
.vd.pass{background:#16351f;color:#7ee39b;border:1px solid #2c6b3f}
.vd.fail{background:#3a1a1a;color:#ff8b8b;border:1px solid #7a3333}
.gallery figcaption{padding:6px 9px;font:10px var(--mono);color:var(--dimmer);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gallery .lbl{color:var(--run);font-weight:600;text-transform:uppercase;
  letter-spacing:.05em;margin-right:5px}
.adunit{margin-top:9px;display:flex;align-items:center;gap:9px;flex-wrap:wrap;
  font:11px var(--mono);color:var(--dimmer)}
.adunit code{font:11px var(--mono);background:rgba(126,227,155,.10);
  border:1px solid rgba(126,227,155,.35);color:#7ee39b;padding:3px 8px;
  border-radius:4px;word-break:break-all}
dialog.zoom{border:none;background:transparent;padding:0;max-width:96vw}
dialog.zoom::backdrop{background:rgba(0,0,0,.9)}
dialog.zoom img{max-width:96vw;max-height:94vh;display:block;border-radius:6px}
"""
    t = t.replace("</style>", gallery_css + "</style>", 1)

    # --- the pictures, between the head and the stages ------------------
    old_meta = ('&middot; brand <b>${esc(r.brand)}</b> '
                '&middot; <b>${esc(r.lane)}</b> lane')
    new_meta = ('&middot; <b>${esc(r.brand||"—")}</b> '
                '&middot; <b>${r.pics.length}</b> pictures'
                '${r.delivered ? `<div class="adunit"><span>shipped as</span>'
                '<code>${esc(r.delivered.ad_name)}</code>'
                '<span>${r.delivered.assets} assets</span></div>` : ""}')
    t = t.replace(old_meta, new_meta)

    anchor = '  const list = (keepVersion && VIEWING) ? VIEWING : r.stage_list;'
    gal = """  if((r.pics||[]).length){
    out += `<div class="grp">THE PICTURES</div><div class="gallery">` +
      r.pics.map(p=>`<figure>
        <img src="${p.src}" alt="${esc(p.name)}" onclick="zoom('${p.src}')">
        <figcaption><span class="lbl">${esc(p.label)}</span>${esc(r.delivered&&r.delivered.by_file&&r.delivered.by_file[p.name]?r.delivered.by_file[p.name].slice(-3):p.name)}${p.verdict?`<span class="vd ${p.verdict.toLowerCase()}">${p.verdict}</span>`:""}</figcaption>
      </figure>`).join("") + `</div>`;
  }
""" + anchor
    t = t.replace(anchor, gal, 1)

    # zoom dialog + handler
    t = t.replace("</body>",
                  '<dialog class="zoom" id="zoomdlg" onclick="this.close()">'
                  '<img alt=""></dialog></body>')
    t = t.replace("rail(); render(); restore();",
                  "function zoom(src){const d=document.getElementById('zoomdlg');"
                  "d.querySelector('img').src=src;d.showModal();}\n"
                  "rail(); render(); restore();")
    return t


def main():
    runs = collect()
    stamp = time.strftime("%-I:%M:%S %p", time.localtime())
    t = template()
    page = (t.replace("__DATA__", json.dumps(runs).replace("</", "<\\/"))
             .replace("__EXPECTED__", "{}")
             .replace("__STAMP__", stamp)
             .replace("__LIVE__", "false"))
    # the board polls these beside itself; give it real ones so it never
    # sits on a failed fetch
    (HERE / "status.json").write_text(json.dumps(
        {"stamp": stamp, "sig": [[r["slug"]] for r in runs]}))
    (HERE / "board.json").write_text(json.dumps(
        {"runs": runs, "expected": {}, "stamp": stamp}))
    OUT.write_text(page)
    pics = sum(len(r["pics"]) for r in runs)
    print(f"{OUT}  ({len(page)//1024} KB) — {len(runs)} runs, {pics} pictures")


if __name__ == "__main__":
    main()
