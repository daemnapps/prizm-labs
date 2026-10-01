#!/usr/bin/env python3
"""Every finished brief, on one page.

The board shows how a brief was made — thirteen stages, prompts, timings.
This shows the briefs themselves, which is what a person opens when they are
about to shoot something.
"""
import base64, html, json, re, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import md

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
OUT = HERE / "briefs.html"

# Reference frames are ~14MB of PNG each run. A published page cannot reach a
# file on the machine that made it, so they are inlined — downscaled, because
# 387MB of PNG will not fit anywhere.
MAX_W, QUALITY = 620, 60


def shrink(src: Path) -> str:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "f.jpg"
        subprocess.run(["sips", "-Z", str(MAX_W), "-s", "format", "jpeg",
                        "-s", "formatOptions", str(QUALITY),
                        str(src), "--out", str(out)], capture_output=True)
        data = out.read_bytes() if out.exists() else src.read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def embed(body_html: str, run_dir: Path) -> str:
    """Point every <img> at the picture itself rather than at a path."""
    def sub(m):
        rel = m.group(1)
        f = run_dir / rel
        if not f.is_file():
            return m.group(0)
        try:
            return m.group(0).replace(rel, shrink(f))
        except Exception:
            return m.group(0)
    return re.sub(r'src="([^"]+\.(?:png|jpg|jpeg))"', sub, body_html)

CSS = """
:root{--bg:#f6f5f2;--card:#fff;--line:#e4e1da;--ink:#23211d;--body:#3a3730;
--dim:#7a7469;--accent:#8a5a1f;--mono:ui-monospace,"SF Mono",Menlo,monospace;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#15130f;--card:#1e1b16;--line:#332e26;--ink:#efeae0;--body:#dcd6ca;
--dim:#a09889;--accent:#dda94f}}
:root[data-theme=dark]{--bg:#15130f;--card:#1e1b16;--line:#332e26;--ink:#efeae0;
--body:#dcd6ca;--dim:#a09889;--accent:#dda94f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--body);font:16.5px/1.65 var(--sans);
padding:0 18px 90px;-webkit-font-smoothing:antialiased}
.wrap{max-width:50rem;margin:0 auto}
header{padding:46px 0 8px}
.eyebrow{font:600 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
h1{font-size:32px;margin:8px 0 0;color:var(--ink);letter-spacing:-.02em}
.sub{color:var(--dim);margin-top:10px}
nav{display:flex;flex-wrap:wrap;gap:8px;margin:26px 0 0;padding-bottom:22px;
border-bottom:1px solid var(--line)}
nav a{font:12px var(--mono);color:var(--dim);text-decoration:none;
border:1px solid var(--line);border-radius:20px;padding:5px 12px;background:var(--card)}
nav a:hover{color:var(--accent);border-color:var(--accent)}
.brief{margin-top:52px;scroll-margin-top:18px}
.brief > .head{border-top:3px solid var(--accent);padding-top:14px;margin-bottom:6px}
.brief .meta{font:11.5px var(--mono);color:var(--dim)}
.doc{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:26px 30px;margin-top:16px}
.doc h1{font-size:25px;margin:0 0 6px}
.doc h2{font-size:19px;color:var(--ink);margin:30px 0 10px;letter-spacing:-.01em}
.doc h3,.doc h4{font-size:15.5px;color:var(--ink);margin:22px 0 6px}
.doc p{margin:0 0 13px;max-width:60ch}
.doc strong{color:var(--ink);font-weight:640}
.doc ul,.doc ol{margin:0 0 14px;padding-left:22px}
.doc li{margin-bottom:6px}
.doc hr{border:0;border-top:1px solid var(--line);margin:26px 0}
.doc blockquote{margin:0 0 14px;padding-left:16px;border-left:3px solid var(--line);color:var(--dim)}
.doc code{font:.86em var(--mono);background:var(--bg);border:1px solid var(--line);
border-radius:3px;padding:1px 5px;color:var(--ink)}
.doc .tw{overflow-x:auto;margin:0 0 16px;border:1px solid var(--line);border-radius:7px}
.doc table{border-collapse:collapse;width:100%;font-size:14px}
.doc th{background:var(--bg);text-align:left;font-weight:640;color:var(--ink);
padding:9px 13px;border-bottom:1px solid var(--line);white-space:nowrap}
.doc td{padding:9px 13px;border-bottom:1px solid var(--line);vertical-align:top}
.doc img{max-width:260px;border-radius:8px;border:1px solid var(--line);display:block;margin:6px 0 16px}
footer{margin-top:60px;padding-top:16px;border-top:1px solid var(--line);
font:11.5px var(--mono);color:var(--dim)}
"""

def main():
    # The two oldest runs were written by brief prompts v18/v19, which ended
    # with a "still to fill in" checklist that v21 dropped. They are old
    # output sitting next to new, and reading them as current is confusing.
    SKIP = {"ai-swipe-luxe-foundation", "graduation-test"}
    # Focused on one run while it is being worked on. Clear ONLY to show
    # every current brief again.
    ONLY = {"<person>-06-dbtdq1qon4a"}
    briefs = []
    for d in sorted(RUNS.iterdir()):
        if d.name in SKIP or (ONLY and d.name not in ONLY):
            continue
        f = d / "brief-final.md"
        if not f.is_file():
            f = d / "5-brief.md"
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        title = re.sub(r"^#\s*", "", text.splitlines()[0]).strip().strip("*")
        st = {}
        rj = d / "run.json"
        if rj.is_file():
            try: st = json.loads(rj.read_text())
            except Exception: st = {}
        aud = st.get("audience") or {}
        meta = " · ".join(x for x in [
            st.get("brand"), (st.get("triage_lane") or "").lower() or None,
            aud.get("_avatar"), aud.get("_funnel"),
            ", ".join(aud.get("_topics") or []) or None] if x)
        briefs.append((d.name, title, meta, embed(md.render(text), d)))

    parts = ['<meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             "<title>Creator Briefs</title>", f"<style>{CSS}</style>",
             "<div class='wrap'><header>",
             "<div class='eyebrow'>the video machine · finished briefs</div>",
             "<h1>Three tops, one pick</h1>",
             f"<p class='sub'>The brief, the openings to test, and a reference frame on every shot.</p>",
             "<nav>" + "".join(
                 f"<a href='#{html.escape(s)}'>{html.escape(t)}</a>"
                 for s, t, _, _ in briefs) + "</nav></header>"]
    for slug, title, meta, body in briefs:
        parts.append(
            f"<div class='brief' id='{html.escape(slug)}'>"
            f"<div class='head'><div class='meta'>{html.escape(meta or slug)}</div></div>"
            f"<div class='doc'>{body}</div></div>")
    parts.append("<footer>components/video-teardown/machine/runs/</footer></div>")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"{OUT}  ({len(briefs)} briefs)")

if __name__ == "__main__":
    main()
