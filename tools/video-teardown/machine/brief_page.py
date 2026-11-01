#!/usr/bin/env python3
"""One run's brief as a single page he can read anywhere.

    python3 brief_page.py <run label> [--frames frames-gpt] [--out <file.html>]

The brief with its reference frames inlined as data URIs, so it opens on a
phone, survives being sent, and needs no server. The run page at
`localhost:8820/run/<label>` is the live version; this is the one that travels.

the owner, 2026-09-22, asked for the brief twice in a row and got it hand-built
both times. This is the same page, as a command.

`--frames` picks which folder of frames to show — the default is the run's own
`frames/frames/`. A run regenerated on a different image door writes a second
folder beside it, and naming it here is how the two are compared.
"""
import argparse, base64, json, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import md  # noqa: E402
import workdir  # noqa: E402

CSS = """
:root{--bg:#fbfbfa;--panel:#fff;--line:#e4e4e7;--ink:#111114;--body:#33363d;--mut:#787f8c;--accent:#1f5fd0}
@media(prefers-color-scheme:dark){:root{--bg:#0c0d10;--panel:#15171b;--line:#272a31;--ink:#f5f6f8;
--body:#c8ccd4;--mut:#878e9b;--accent:#78a6ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--body);font:16px/1.65 -apple-system,BlinkMacSystemFont,
"Segoe UI",sans-serif;padding:30px 20px 70px;max-width:760px;margin-inline:auto;-webkit-font-smoothing:antialiased}
.run{font:500 11.5px/1 ui-monospace,Menlo,monospace;letter-spacing:.08em;text-transform:uppercase;
color:var(--mut);margin-bottom:10px}
dl.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px 18px;margin:0 0 22px;
padding-bottom:22px;border-bottom:1px solid var(--line)}
dl.facts div{display:flex;flex-direction:column;gap:1px}
dl.facts dt{font:500 10.5px/1 ui-monospace,Menlo,monospace;letter-spacing:.09em;text-transform:uppercase;color:var(--mut)}
dl.facts dd{margin:0;color:var(--ink);font-size:14.5px}
h1{color:var(--ink);font-size:30px;line-height:1.15;letter-spacing:-.022em;margin:0 0 10px;text-wrap:balance}
h2{color:var(--ink);font:600 12.5px/1 ui-monospace,Menlo,monospace;letter-spacing:.11em;text-transform:uppercase;
margin:40px 0 12px;padding-bottom:9px;border-bottom:1px solid var(--line)}
h3{color:var(--ink);font-size:17.5px;margin:28px 0 6px}
p{margin:0 0 12px;max-width:65ch} strong{color:var(--ink);font-weight:600}
blockquote{margin:12px 0;padding:10px 16px;border-left:3px solid var(--accent);background:var(--panel);
border-radius:0 8px 8px 0;color:var(--mut);font-size:14.5px}
blockquote p{margin:0}
ul,ol{max-width:65ch} li{margin-bottom:5px}
table{border-collapse:collapse;width:100%;margin:12px 0 20px;font-size:14px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:8px 11px;text-align:left;vertical-align:top}
th{background:var(--panel);color:var(--mut);font:500 11px/1.4 ui-monospace,Menlo,monospace;
letter-spacing:.06em;text-transform:uppercase}
.frame{display:inline-block;width:190px;max-width:48%;margin:4px 10px 18px 0;line-height:0}
.frame img{width:100%;border-radius:9px;border:1px solid var(--line);display:block}
.foot{margin-top:44px;padding-top:18px;border-top:1px solid var(--line);font-size:13px;color:var(--mut)}
"""


def thumb(src, px=560):
    """A frame small enough to travel. sips is on every Mac; if it is not
    there the full-size picture goes in and the file is simply bigger."""
    out = Path(tempfile.mkdtemp()) / (src.stem + ".jpg")
    r = subprocess.run(["sips", "-Z", str(px), "-s", "format", "jpeg",
                        "-s", "formatOptions", "72", str(src), "--out", str(out)],
                       capture_output=True)
    return out if r.returncode == 0 and out.is_file() else src


def page(run_dir, frames_dir, model_note=""):
    st = json.loads((run_dir / "run.json").read_text())
    body = md.render((run_dir / "brief-final.md").read_text())

    def swap(m):
        f = frames_dir / (Path(m.group(1)).stem + ".png")
        if not f.is_file():
            f = frames_dir / (Path(m.group(1)).stem + ".jpg")
        if not f.is_file():
            return ""
        b64 = base64.b64encode(thumb(f).read_bytes()).decode()
        return f'<span class="frame"><img src="data:image/jpeg;base64,{b64}" alt=""></span>'

    body, n = re.subn(r'<img src="([^"]+)"[^>]*>', swap, body)
    aud = st.get("audience") or {}
    facts = [("brand", st.get("brand")),
             ("creator", "@" + st["creator"] if st.get("creator") else None),
             ("avatar", aud.get("_avatar")), ("sub-avatar", aud.get("_sub_avatar")),
             ("framework", (st.get("doctrine") or {}).get("framework")),
             ("came from", {"ALREADY AN AD": "a paid ad", "ORGANIC": "an organic post"}
              .get(st.get("triage_lane"), st.get("triage_lane"))),
             ("frames", f"{n}{model_note}")]
    dl = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts if v)
    return f"""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{st.get('label', run_dir.name)} — the brief</title><style>{CSS}</style>
<div class="run">video teardown · {run_dir.name}</div>
<dl class="facts">{dl}</dl>
{body}
<p class="foot">The reference frames are what the shot should look like, not the shot itself —
the creator films it. Every stage's prompt as sent:
<code>localhost:8820/run/{run_dir.name}</code></p>
""", n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("--frames", default="frames/frames",
                    help="which frame folder to show, relative to the run "
                         "(default: frames/frames)")
    ap.add_argument("--note", default="", help="a word about the frames, e.g. the model")
    ap.add_argument("--out")
    a = ap.parse_args()
    run_dir = workdir.run_dir(a.label)
    if not (run_dir / "brief-final.md").exists():
        sys.exit(f"no finished brief in {run_dir}")
    frames_dir = run_dir / a.frames
    html, n = page(run_dir, frames_dir, f" · {a.note}" if a.note else "")
    out = Path(a.out) if a.out else run_dir / "brief.html"
    out.write_text(html)
    print(f"{n} frame(s) from {a.frames} -> {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
