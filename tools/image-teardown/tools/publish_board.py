#!/usr/bin/env python3
"""Make a copy of the board that survives leaving this folder.

    python3 tools/publish_board.py [--out FILE] [--wide 420] [--quality 72]

`build_ui.py` writes picture paths relative to the lane — `runs/<slug>/finals/
.web/x.jpg` — which resolve when the page is served out of this folder and
resolve nowhere else. Published as an artifact, every thumbnail on the board
came up as a broken-image icon (2026-09-13).

So this reads the board's own JSON payload out of the page, replaces every
picture path with the picture itself as a data URI, and writes a second file.
The local board keeps its paths and stays small and fast; the published copy
carries its pictures with it.
"""
import argparse, base64, io, json, re, sys, time
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
KEYS = ("src", "hero", "poster")


def inline(rel, wide, quality, cache):
    if not rel or rel.startswith("data:"):
        return rel
    if rel in cache:
        return cache[rel]
    f = HERE / rel
    if not f.is_file():
        cache[rel] = ""
        return ""
    im = Image.open(f).convert("RGB")
    im.thumbnail((wide, wide * 3), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)
    cache[rel] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return cache[rel]


def walk(node, wide, quality, cache, stats):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in KEYS and isinstance(v, str):
                got = inline(v, wide, quality, cache)
                node[k] = got
                stats["hit" if got else "miss"] += 1
            else:
                walk(v, wide, quality, cache, stats)
    elif isinstance(node, list):
        for v in node:
            walk(v, wide, quality, cache, stats)


def freeze(page):
    """Turn the live board into an honest snapshot.

    The board polls `status.json` every couple of seconds and repaints from
    `board.json` when the stamp moves. Published as an artifact there is no
    server behind it, so both fetches fail forever: the clock never ticks and
    the live dot never pulses, and the page reads as dead rather than as a
    copy taken at a moment (Damon, 2026-09-13: "looks like this image machine
    artifact is dead / not live").

    So the published copy stops polling and says when it was taken.
    """
    stamp = time.strftime("%a %-d %b, %-I:%M %p")

    marker = "async function poll(){"
    if marker not in page:
        print("! no poll() in the board — liveness not frozen, check build_ui.py")
    else:
        page = page.replace(
            marker,
            "async function poll(){ return; }  // frozen by publish_board.py\n"
            "async function pollLive(){", 1)

    # `tick()` repaints the clock from the browser's own time every second, so
    # freezing poll() alone leaves a running clock on a page that is not
    # running. Drop only the clock line out of tick — the rest of tick paints
    # the stage pills and still has to run.
    ticker = re.search(
        r'\n\s*document\.getElementById\("clock"\)\.textContent\s*=\s*\n?'
        r'\s*new Date\(\)\.toLocaleTimeString\([^;]*;', page)
    if ticker:
        page = page[:ticker.start()] + "\n  // clock frozen by publish_board.py" + page[ticker.end():]
    else:
        print("! no clock tick found — the published copy may show a running clock")

    # The clock is the board's liveness read-out; say what this copy is.
    page = re.sub(r'(<span id="clock">)[^<]*(</span>)',
                  rf'\1snapshot &middot; {stamp}\2', page, count=1)
    return page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", default=str(HERE / "image-board.html"))
    ap.add_argument("--out", default=str(HERE / "image-board-published.html"))
    ap.add_argument("--wide", type=int, default=420)
    ap.add_argument("--quality", type=int, default=72)
    a = ap.parse_args()

    page = Path(a.board).read_text()
    # The payload is `const RUNS = [ ... ];` written by build_ui.py. It is an
    # array, and it contains braces and brackets inside strings, so it is
    # found by decoding from its opening character rather than by a regex —
    # a non-greedy `\{.*?\}` matched nothing here and silently inlined zero
    # pictures while reporting success.
    m = re.search(r"const\s+RUNS\s*=\s*", page)
    if not m:
        sys.exit("no `const RUNS =` payload in the board — has build_ui.py changed shape?")
    start = m.end()
    try:
        data, length = json.JSONDecoder().raw_decode(page[start:])
    except json.JSONDecodeError as e:
        sys.exit(f"the board's payload is not valid JSON: {e}")
    end = start + length

    cache, stats = {}, {"hit": 0, "miss": 0}
    walk(data, a.wide, a.quality, cache, stats)

    out = page[:start] + json.dumps(data) + page[end:]
    out = freeze(out)
    Path(a.out).write_text(out)
    mb = len(out.encode()) / 1e6
    print(f"{a.out}  ({mb:.1f} MB) — {stats['hit']} pictures inlined, "
          f"{stats['miss']} missing, {len(cache)} unique")
    if mb > 15:
        print("! over 15 MB — drop --wide or --quality before publishing")


if __name__ == "__main__":
    main()
