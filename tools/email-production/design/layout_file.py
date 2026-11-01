"""LD-76 (email layout file): an email's section map, measured once at build and kept beside it.

The section positions only change when klaviyo/email.html changes, and design/build.py is the one place that writes
it, so build measures the email there and keeps the answer as <run>/klaviyo/layout.json. The team page's data command
(adapter/sync.py list) reads it instead of launching headless Chrome for every email on every call.

    <run>/klaviyo/layout.json   {"schema": 1, "height": H, "sections": [{"i", "top", "bottom"}, ...],
                                 "from": sha256 of design/email.json, "html": sha256 of klaviyo/email.html}
                                pixels at 600 wide; small and tracked, so every Mac has the positions after a pull

    read(run)    the file only while its "html" is the current email.html's, else None (measure again)
    stale(run)   the layout (design/email.json) changed since the file was written: the email wants a rebuild

The same build step makes the whole-email picture once (klaviyo/whole-email.jpg, sync.py _shot's exact crop) and puts
klaviyo/assets/* and that picture onto the run's Drive mirror through gdrive-creator's reach, as LD-75 (design
pictures to Drive) does for media/ (picture_record.mirror), so no other Mac re-runs build's Chrome to have them.
Chrome runs by build.py's rules: its own profile folder in a temp dir, one retry without its sandbox (LD-22 (Chrome
in fenced runs)). Stdlib only; PIL is imported inside shot(), as sync.py does.
"""
import hashlib
import html
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

_HS = os.path.expanduser("~/Library/Caches/chrome-headless-shell/chrome-headless-shell-mac-arm64/chrome-headless-shell")   # background-only browser: no Dock icon; Chrome is the fallback
APP = (_HS if os.path.exists(_HS) else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SCHEMA = 1
NAME = "layout.json"
SHOT = "whole-email.jpg"
# the DOM-dump script sync.py's _measure injected: the wrap table's height, and each data-sec's rows merged top..bottom
JS = ("<script>addEventListener('load',()=>{const w=document.querySelector('table.wrap');const H=w.getBoundingClientRect().height;"
      "const o={};for(const r of w.querySelectorAll(':scope>tbody>tr[data-sec]')){const b=r.getBoundingClientRect();const i=r.dataset.sec;"
      "o[i]=o[i]?[o[i][0],b.bottom]:[b.top,b.bottom]}const p=document.createElement('pre');p.id='pos';"
      "p.textContent=JSON.stringify({H,o});document.body.appendChild(p)})</script>")
POS = re.compile(r'<pre id="pos">(.*?)</pre>', re.S)


def chrome():
    """Read at call time, so a test (or a fenced run) can name its own Chrome."""
    return os.environ.get("CHROME_BIN") or APP


def _sha(f):
    try:
        return hashlib.sha256(Path(f).read_bytes()).hexdigest()
    except OSError:
        return None


def _tail(p):
    err = p.stderr or ""
    err = err.decode("utf-8", "replace") if isinstance(err, bytes) else str(err)
    return " | ".join([ln for ln in err.splitlines() if ln.strip()][-3:]) or "(nothing)"


def _chrome(argv, url, made, timeout=120):
    """build.py's rule: if nothing came back, Chrome's own sandbox could not start (it cannot inside sandbox-exec) —
    one retry without it. Returns the last run."""
    p = subprocess.run(argv + [url], capture_output=True, text=True, timeout=timeout)
    if not made(p):
        p = subprocess.run(argv + ["--no-sandbox", url], capture_output=True, text=True, timeout=timeout)
    return p


def measure(page, tmp=None):
    """(height, {section: [top, bottom]}) of the built email, in pixels at 600 wide. The page is copied beside itself
    with the script injected (its assets/ load by relative path), Chrome dumps the DOM, the copy is removed."""
    page = Path(page).resolve()
    with tempfile.TemporaryDirectory() as own:
        tmp = Path(tmp or own)
        fd, name = tempfile.mkstemp(prefix=".measure-", suffix=".html", dir=str(page.parent))
        f = Path(name)
        try:
            with os.fdopen(fd, "w") as w:
                w.write(page.read_text().replace("</body>", JS + "</body>"))
            # --hide-scrollbars as shot() does (PF-24 (full-height shots)): with a scrollbar the page is 585 wide, the
            # email's phone rule (.wrap 100% at 620 px and under) shrinks every full-width picture, and the
            # measure came out ~75-140 px short of the 600-wide picture, cutting its footer
            argv = [chrome(), "--headless=new", "--hide-scrollbars", "--window-size=600,3000", "--virtual-time-budget=4000",
                    "--user-data-dir=%s" % (tmp / "chrome-profile"), "--dump-dom"]
            p = _chrome(argv, f.as_uri(), lambda r: bool(POS.search(r.stdout or "")))
        finally:
            f.unlink()
    m = POS.search(p.stdout or "")
    if not m:
        raise RuntimeError("could not measure %s: headless Chrome gave no positions, with and without its own sandbox;"
                           " its stderr ends: %s" % (page, _tail(p)))
    d = json.loads(html.unescape(m.group(1)))
    return float(d["H"]), {int(k): [float(v[0]), float(v[1])] for k, v in d["o"].items()}


def write(run_dir):
    """Measure <run>/klaviyo/email.html and keep the answer as <run>/klaviyo/layout.json; returns what was written."""
    run_dir = Path(run_dir)
    k = run_dir / "klaviyo"
    page = k / "email.html"
    h = _sha(page)                                    # the html it was measured from, taken before the measure
    H, pos = measure(page)
    doc = {"schema": SCHEMA, "height": H,
           "sections": [{"i": i, "top": pos[i][0], "bottom": pos[i][1]} for i in sorted(pos)],
           "from": _sha(run_dir / "design" / "email.json"), "html": h}
    (k / NAME).write_text(json.dumps(doc, indent=1) + "\n")
    return doc


def write_safe(run_dir):
    """write(), but a failure is printed by name and never sinks the build."""
    try:
        return write(run_dir)
    except Exception as e:  # noqa: BLE001 -- named below, never silent
        print("layout: NOT written — %s: %s" % (type(e).__name__, e))
        return None


def _load(run_dir):
    try:
        d = json.loads((Path(run_dir) / "klaviyo" / NAME).read_text())
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) and d.get("schema") == SCHEMA else None


def read(run_dir):
    """layout.json, only while it was measured from the email.html on disk now; else None."""
    d = _load(run_dir)
    if d is None or d.get("html") is None or d.get("html") != _sha(Path(run_dir) / "klaviyo" / "email.html"):
        return None
    return d


def positions(d):
    """A layout.json as measure() answers: (height, {i: [top, bottom]})."""
    return d["height"], {int(s["i"]): [s["top"], s["bottom"]] for s in d["sections"]}


def stale(run_dir):
    """True when layout.json is there but design/email.json changed since it was written."""
    f = Path(run_dir) / "klaviyo" / NAME
    if not f.is_file():
        return False
    d = _load(run_dir) or {}
    return d.get("from") != _sha(Path(run_dir) / "design" / "email.json")


def shot(run_dir, height, tmp=None):
    """<run>/klaviyo/whole-email.jpg: sync.py _shot's steps (600 x height+2 screenshot, cropped to 600 x height, RGB,
    quality 82), with build.py's Chrome rules. Raises RuntimeError naming the page when no picture comes."""
    k = Path(run_dir).resolve() / "klaviyo"
    page, out = k / "email.html", k / SHOT
    with tempfile.TemporaryDirectory() as own:
        tmp = Path(tmp or own)
        full = tmp / "whole-email.full.png"
        argv = [chrome(), "--headless=new", "--hide-scrollbars", "--window-size=600,%d" % int(height + 2),
                "--user-data-dir=%s" % (tmp / "chrome-profile"), "--screenshot=%s" % full]
        p = _chrome(argv, page.as_uri(), lambda r: full.is_file() and full.stat().st_size > 0)
        if not (full.is_file() and full.stat().st_size > 0):
            raise RuntimeError("headless Chrome made no picture of %s, with and without its own sandbox; its stderr ends: %s"
                               % (page, _tail(p)))
        from PIL import Image
        im = Image.open(full).convert("RGB").crop((0, 0, 600, int(height)))
        im.save(out, quality=82)
        full.unlink()
    return out


def _put(L, files, parts):
    """One put, exactly as picture_record.mirror(): an Exception is named, never raised; SystemExit stays loud."""
    try:
        how, placed, note = L.reach().put(files, parts)
    except Exception as e:  # noqa: BLE001 -- named below, never silent
        how, placed, note = "none", [], "%s: %s" % (type(e).__name__, e)
    if placed and not note:
        print("   drive: %s%s" % (placed[0], " (+%d more)" % (len(placed) - 1) if len(placed) > 1 else ""))
    else:
        print("   drive: NOT mirrored — %s" % (note or "nothing placed (route %s)" % how))
    return how, placed, note


def mirror_build(brand, run_dir):
    """klaviyo/assets/* onto Shared Assets/runs/email-production/<brand>/<label>/klaviyo/assets/, and the whole-email
    picture onto .../<label>/klaviyo/ when it is newer than email.html (an older one shows an older email); one
    (how, placed, note) per put."""
    import look as L
    run_dir = Path(run_dir)
    k = run_dir / "klaviyo"
    parts = ["runs", "email-production", brand, run_dir.name, "klaviyo"]
    done = []
    files = sorted(f for f in (k / "assets").glob("*") if f.is_file())
    if files:
        done.append(_put(L, files, parts + ["assets"]))
    pic, page = k / SHOT, k / "email.html"
    if pic.is_file() and (not page.is_file() or pic.stat().st_mtime >= page.stat().st_mtime):
        done.append(_put(L, [pic], parts))
    return done


MEDIA_LEDGER = "drive-media.json"


def media_names(run_dir):
    """Every run:media/<name> design/email.json names, in order, once each."""
    f = Path(run_dir) / "design" / "email.json"
    if not f.is_file():
        return []
    return list(dict.fromkeys(re.findall(r'"run:media/([^"/]+)"', f.read_text())))


def media_ledger(run_dir):
    """{name: sha256} of the run's media pictures already put on its Drive mirror (PF-21 (pictures reach every Mac))."""
    try:
        d = json.loads((Path(run_dir) / "media" / MEDIA_LEDGER).read_text())
        return d.get("put") or {}
    except (OSError, ValueError):
        return {}


def mirror_media(brand, run_dir, reach=None):
    """PF-21 (pictures reach every Mac): every picture design/email.json names as run:media/<name> onto the run's Drive
    mirror, Shared Assets/runs/email-production/<brand>/<label>/media/, the place look.py's run: fallback (LD-34 (run
    pictures from Drive)) reads on any other Mac. The designer's own flow (her Claude edits email.json and runs
    build.py) never called picture_record.mirror(), so her pictures stayed on her Mac. Only what changed since the
    ledger (media/drive-media.json) is put. Returns {"put", "already", "not_here", "error"}; never raises."""
    run_dir = Path(run_dir)
    ledger = media_ledger(run_dir)
    put, already, not_here, todo = [], [], [], []
    for name in media_names(run_dir):
        f = run_dir / "media" / name
        sha = _sha(f) if f.is_file() else None
        if sha is None:
            (already if name in ledger else not_here).append(name)
        elif ledger.get(name) == sha:
            already.append(name)
        else:
            todo.append((name, f, sha))
    error = None
    if todo:
        parts = ["runs", "email-production", brand, run_dir.name, "media"]
        try:
            if reach is None:
                import look as L
                reach = L.reach()
            how, placed, note = reach.put([f for _, f, _ in todo], parts)
        except Exception as e:  # noqa: BLE001 -- named in the result, never silent
            how, placed, note = "none", [], "%s: %s" % (type(e).__name__, e)
        if placed and not note and len(placed) == len(todo):
            for name, _, sha in todo:
                ledger[name] = sha
                put.append(name)
            (run_dir / "media").mkdir(parents=True, exist_ok=True)
            (run_dir / "media" / MEDIA_LEDGER).write_text(json.dumps(
                {"schema": 1, "_about": "PF-21 (pictures reach every Mac): media pictures already on the run's Drive "
                 "mirror, name -> sha256 of the bytes put; layout_file.mirror_media writes it.", "put": ledger},
                indent=1, sort_keys=True) + "\n")
        else:
            error = note or "only %d of %d placed (route %s)" % (len(placed or []), len(todo), how)
    return {"put": put, "already": already, "not_here": not_here, "error": error}


def assets_missing(run_dir):
    """The klaviyo/assets pictures email.html names that this Mac does not hold."""
    k = Path(run_dir) / "klaviyo"
    page = k / "email.html"
    names = sorted(set(re.findall(r'src="assets/([^"]+)"', page.read_text()))) if page.is_file() else []
    return [n for n in names if not (k / "assets" / n).is_file()]


def pull_build(brand, run_dir, reach=None):
    """The other way round: every picture email.html names (klaviyo/assets/<name>) and the whole-email picture, from
    the run's Drive mirror onto this Mac, over the local copy. Pictures are media, never in git, so after a pull a Mac
    holds the newest email.html with the pictures of its own last build: the team's redesign of brand-b-nov-01 showed (and
    would have gone to Klaviyo) with this Mac's pictures from 21 October (the team, 2026-10-27). Returns
    {"got": [...], "missing": [...], "error": note or None}; a Drive that won't answer is the note, never a crash."""
    run_dir = Path(run_dir)
    k = run_dir / "klaviyo"
    page = k / "email.html"
    names = sorted(set(re.findall(r'src="assets/([^"]+)"', page.read_text()))) if page.is_file() else []
    parts = ["runs", "email-production", brand, run_dir.name, "klaviyo"]
    got, missing = [], []
    try:
        if reach is None:
            import look as L
            reach = L.reach()
        with tempfile.TemporaryDirectory() as tmp:
            for sub, name in [("assets", n) for n in names] + [("", SHOT)]:
                src = reach.get(parts + ([sub] if sub else []), name, tmp)
                if not src or not Path(src).is_file():
                    if sub:
                        missing.append(name)
                    continue
                dest = k / sub / name if sub else k / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                if Path(src).resolve() != dest.resolve():
                    dest.write_bytes(Path(src).read_bytes())
                if sub:
                    got.append(name)
    except Exception as e:  # noqa: BLE001 -- the caller decides; the note says why
        return {"got": got, "missing": missing, "error": "%s: %s" % (type(e).__name__, e)}
    return {"got": got, "missing": missing, "error": None}


def changed_runs(names, repo):
    """The run folders an update touched under runs/email-production/<brand>/<label>/klaviyo/ (card, email.html, layout:
    any of them means someone rebuilt the email), from `git diff --name-only` lines; only folders this Mac holds."""
    out = []
    for n in names:
        m = re.match(r"runs/email-production/([^/]+)/([^/]+)/klaviyo/", n.strip())
        if m:
            d = Path(repo) / "runs" / "email-production" / m.group(1) / m.group(2)
            if d.is_dir() and d not in out:
                out.append(d)
    return out


def _report(d, r):
    print("%-30s %2d from Drive%s%s" % (d.name, len(r["got"]), "  missing: " + ", ".join(r["missing"]) if r["missing"] else "",
                                         "  NOT pulled — " + r["error"] if r["error"] else ""))


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "pull" and sys.argv[2] == "--changed":
        # .githooks post-merge / post-rewrite: the emails this update rebuilt get their pictures from the Drive, so a
        # Mac shows the email as its designer left it (the team, 2026-10-27). Never fails the update.
        rng = sys.argv[3] if len(sys.argv) > 3 else "ORIG_HEAD..HEAD"
        repo = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or "."
        names = subprocess.run(["git", "diff", "--name-only", rng, "--", "runs/email-production"], cwd=repo,
                               capture_output=True, text=True).stdout.splitlines()
        runs = changed_runs(names, repo)
        if runs:
            print("email pictures: %d email(s) changed in this update; their pictures come from the Drive" % len(runs))
        for d in runs:
            _report(d, pull_build(d.parent.name, d))
        sys.exit(0)
    if len(sys.argv) < 3 or sys.argv[1] != "pull":
        sys.exit("python3 design/layout_file.py pull <run folder> [<run folder> ...]   # the pictures from the Drive mirror\n"
                 "python3 design/layout_file.py pull --changed [<rev range>]          # the emails an update changed (hooks)")
    for d in sys.argv[2:]:
        d = Path(d).resolve()
        _report(d, pull_build(d.parent.name, d))
