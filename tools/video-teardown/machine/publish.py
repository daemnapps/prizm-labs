#!/usr/bin/env python3
"""Make a self-contained copy of the board he can open anywhere.

The live board is a server on his laptop, so it is laptop-only. This bakes one
run into a single page — frames embedded, nothing fetched — which survives
being opened on a phone, off his wifi.
"""
import base64, json, re, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import board as B

MAX_W = 720          # frames are reference stills; full res is wasted on a phone
QUALITY = 62


def shrink(src: Path) -> str:
    """Downscale to a data URI. 13MB of PNGs will not fit in a page."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "f.jpg"
        r = subprocess.run(["sips", "-Z", str(MAX_W), "-s", "format", "jpeg",
                            "-s", "formatOptions", str(QUALITY),
                            str(src), "--out", str(out)],
                           capture_output=True)
        data = out.read_bytes() if out.exists() else src.read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def build(slug=None, dest=None):
    runs = B.collect()
    if slug:
        runs = [r for r in runs if r["slug"] == slug]
    if not runs:
        sys.exit("no run to publish")

    total = 0
    for r in runs:
        d = Path(r["dir"])
        for st in r["stage_list"]:
            html = st.get("output_html") or ""
            for m in set(re.findall(r'<img src="(runs/[^"]+)"', html)):
                f = B.C.MACHINE / m
                if not f.exists():
                    continue
                uri = shrink(f)
                total += len(uri)
                html = html.replace(f'src="{m}"', f'src="{uri}"')
            st["output_html"] = html
            # the video and poster cannot travel; drop the references
        r["poster"] = None
        r["source"] = None

    data = json.dumps(runs).replace("</", "<\\/")
    page = (B.TEMPLATE
            .replace("__DATA__", data)
            .replace("__EXPECTED__", json.dumps(B.expected()))
            .replace("__STAMP__", "snapshot")
            .replace("__LIVE__", "false"))
    # a snapshot has nothing to poll
    page = page.replace("setInterval(poll, 2000);", "")
    page = page.replace("poll(); tick();", "tick();")
    page = re.sub(r"<video[^>]*></video>", "", page)

    out = Path(dest or (B.C.MACHINE / "board-snapshot.html"))
    out.write_text(page)
    print(f"{out}  ({out.stat().st_size/1048576:.1f} MB, "
          f"{total/1048576:.1f} MB of that is frames)")
    return out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else None)
