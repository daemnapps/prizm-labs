"""The email as the designer received it, beside the email as it goes out (the team, 2026-10-28: "el antes sería cómo
the team recibió y el después cómo quedó el correo").

    received.found(run)          -> {"rev", "by", "at"} or None: the commit just before the designer's first change
    received.picture(run, found) -> <run>/design/received-<rev>.jpg, made once (gitignored, like whole-email.jpg)
    received.changes(old, new, kind, words) -> what changed, part by part, in plain words
    received.start_maker(runs)   -> one detached `received.py --make <run> …` for the missing pictures (PF-20b (before
                                    in background)): the emails list never waits on Chrome; a failure is noted in the
                                    system temp folder and named on the row by received.error(run, found)

The designer is the card's own `eve_done.by`; an email with no Done has no "before" yet. The "before" is git's copy
of design/email.json at the parent of that person's first commit touching it, rendered by the engine at 600 wide.
A picture this Mac cannot reach is drawn grey and named in `missing`, never a crash.

    /usr/bin/python3 received.py <run folder>      # makes the picture and prints the changes
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import layout_file as LF  # noqa: E402

W = 400          # the engine's phone width, in CSS pixels
SCALE = 1.5      # 400 x 1.5 = 600, the width of whole-email.jpg
MAGENTA = (255, 0, 255)
# a style value or picture path the page lists among the words (a glow colour, a position, a background
# picture's run:media/… path) is not a word a reader sees
STYLE = re.compile(r"^\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|-?[\d.]+(%|px|em)?|(run|drive|proof):\S+)\s*$")


def _git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout


def _rel(run):
    return Path(run).resolve().relative_to(REPO).as_posix() + "/design/email.json"


def designers():
    """[(name, {names and emails, lower-cased})] for every person whose identity says designer on email-production."""
    out = []
    for f in sorted((REPO / "team" / "people").glob("*/identity.json")):
        try:
            d = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if d.get("key_audience") == "designer" and "email-production" in (d.get("stations") or []):
            person = d.get("person") or f.parent.name
            ids = {person.lower()} | {(e.get("address") or "").lower() for e in d.get("emails") or [] if isinstance(e, dict)}
            out.append((person.capitalize(), ids - {""}))
    return out


def found(run):
    """The commit whose design/email.json the designer received, or None (the email was never committed).

    With a Done, the designer is the card's `eve_done.by`; without one, any designer on email-production (PF-20
    (before from arrival), the team 2026-10-29: the before shows from the moment the email reaches the team). Once the
    designer has a commit, the before is the commit just before their first; until then it is the newest commit, the
    version she receives, marked `waiting`."""
    try:
        c = json.loads((Path(run) / "klaviyo" / "card.json").read_text())
    except (OSError, ValueError):
        return None
    log = [x.split("\t") for x in _git("log", "--format=%H\t%an\t%ae\t%aI", "--", _rel(run)).splitlines() if x]
    if not log:
        return None
    by = (c.get("eve_done") or {}).get("by")
    if not by and (c.get("klaviyo") or c.get("scheduled")):
        return None          # never on the designer's list: it went to Klaviyo without her (sync.py's own status rule)
    who = [(by, {by.lower()})] if by else designers()
    for name, ids in who:
        theirs = [i for i, x in enumerate(log) if x[1].lower() in ids or x[2].lower() in ids]
        if theirs:
            if theirs[-1] + 1 >= len(log):
                return None
            rev, _, _, at = log[theirs[-1] + 1]
            return {"rev": rev[:10], "by": name, "at": at}
    if by or not who:
        return None
    rev, _, _, at = log[0]
    return {"rev": rev[:10], "by": who[0][0], "at": at, "waiting": True}


def spec_at(run, rev):
    return json.loads(_git("show", "%s:%s" % (rev, _rel(run))))


def picture_path(run, f):
    """Where the received picture lives (it may not exist yet)."""
    return Path(run).resolve() / "design" / ("received-%s.jpg" % f["rev"])


def _state_dir():
    """The background maker's lock and error notes, outside the repo: the system temp folder, one per checkout."""
    key = hashlib.sha1(str(REPO.resolve()).encode()).hexdigest()[:12]
    d = Path(tempfile.gettempdir()) / "upright-received" / key
    d.mkdir(parents=True, exist_ok=True)
    return d


def _error_file(run, f):
    run = Path(run).resolve()
    return _state_dir() / ("%s__%s__%s.error" % (run.parent.name, run.name, f["rev"]))


def error(run, f):
    """The reason the background maker could not make this picture, or None (PF-20b (before in background))."""
    p = _error_file(run, f)
    if not p.is_file():
        return None
    return p.read_text().strip() or "unknown"


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def start_maker(runs, popen=subprocess.Popen, argv=None):
    """Start ONE detached maker for the runs whose received picture is missing, unless one is alive for this checkout.
    Returns True when a maker was started. The caller (sync.py rows) never waits on it (PF-20b (before in background)).
    `argv` is the maker's command before the runs (default: this file's --make); sync.py passes its own `pictures`,
    which also brings cut pictures from Drive (PF-21 (pictures reach every Mac)), so one lock serves both."""
    if not runs:
        return False
    lock = _state_dir() / "maker.pid"
    try:
        if _alive(int(lock.read_text().strip())):
            return False
    except (OSError, ValueError):
        pass
    with open(str(_state_dir() / "maker.log"), "a") as log:     # the child keeps its own handle
        p = popen((argv or [sys.executable, str(Path(__file__).resolve()), "--make"]) + [str(Path(r).resolve()) for r in runs],
                  cwd=str(REPO), stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    lock.write_text(str(p.pid))
    return True


def make_missing(runs, make=None):
    """The maker's body: each run's missing received picture, one at a time. A failure is written to its error file
    and the next run goes on. Returns (made, failed)."""
    make = make or picture
    made, failed = [], []
    for run in runs:
        f = found(run)
        if not f or picture_path(run, f).is_file() or _error_file(run, f).is_file():
            continue
        try:
            make(run, f)
            made.append(str(run))
        except Exception as e:  # noqa: BLE001 -- written down for the row, never silent
            _error_file(run, f).write_text("%s: %s" % (type(e).__name__, e))
            failed.append(str(run))
    return made, failed


def picture(run, f, chrome=None):
    """<run>/design/received-<rev>.jpg, 600 wide; made only when missing. Returns (path, missing pictures)."""
    run = Path(run).resolve()
    out = run / "design" / ("received-%s.jpg" % f["rev"])
    if out.is_file():
        return out, []
    import engine as E
    from PIL import Image
    spec = spec_at(run, f["rev"])
    lk = E.L.load(spec["brand"], run)
    missing, real = [], lk.path
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        grey = tmp / "missing.png"
        Image.new("RGB", (800, 800), (128, 128, 128)).save(grey)

        def reach(ref):
            p = real(ref)
            if Path(p).exists():
                return p
            missing.append(ref)
            return str(grey)
        lk.path = reach
        page = tmp / "received.html"
        page.write_text('<!doctype html><meta charset="utf-8"><body style="margin:0;background:#ff00ff">'
                        '<div style="width:%dpx">%s</div>' % (W, E.render(spec, lk, True)))
        shot = tmp / "shot.png"
        argv = [chrome or LF.chrome(), "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=%s" % SCALE,
                "--window-size=500,9000", "--user-data-dir=%s" % (tmp / "chrome-profile"), "--screenshot=%s" % shot]
        LF._chrome(argv, page.as_uri(), lambda r: shot.is_file() and shot.stat().st_size > 0)
        if not shot.is_file():
            raise RuntimeError("headless Chrome made no picture of the received email for %s" % run.name)
        im = Image.open(shot).convert("RGB")
        im = im.crop((0, 0, int(W * SCALE), im.size[1]))
        px, h = im.load(), im.size[1]
        while h > 1 and all(px[x, h - 1] == MAGENTA for x in range(0, im.size[0], 40)):
            h -= 1
        im.crop((0, 0, im.size[0], h)).save(out, quality=82)
    return out, missing


def _pics(sec):
    out = []

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("photo"), str):
                out.append(o["photo"])
            for k, v in o.items():
                if k != "history":
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(sec)
    return out


def _in_order(pairs):
    """The pairs (new place, old place) that kept their order: the longest run of old places rising with the new."""
    best = []
    for k, (i, j) in enumerate(pairs):
        run = max((r for r in best if r and pairs[r[-1]][1] < j), key=len, default=[])
        best.append(run + [k])
    keep = max(best, key=len, default=[])
    return {pairs[k] for k in keep}


def changes(old, new, kind=lambda t: t, words=lambda s: []):
    """What changed between the two specs, in plain words, part by part. Parts are numbered as the page numbers them
    (1-based, the new order). A part is matched first by its words (so one that only moved or changed its look is
    found), then by its kind; a part counts as moved only when it left the order the others kept."""
    out = []
    for k, name in (("subject", "Subject"), ("preview", "Preview text")):
        if (old.get(k) or "") != (new.get(k) or ""):
            out.append({"what": "%s changed" % name, "kind": "words"})
    A, B = old.get("sections") or [], new.get("sections") or []
    key = lambda s: tuple(w for w in words(s) if not STYLE.match(w))
    match = {}
    for i, s in enumerate(B):
        j = next((j for j in range(len(A)) if j not in match.values() and key(A[j]) == key(s) and key(s)), None)
        if j is not None:
            match[i] = j
    for i, s in enumerate(B):
        if i not in match:
            j = next((j for j in range(len(A)) if j not in match.values() and A[j].get("s") == s.get("s")), None)
            if j is not None:
                match[i] = j
    kept = _in_order(sorted(match.items()))
    for i, s in enumerate(B):
        name = kind(s.get("s"))
        if i not in match:
            out.append({"part": i + 1, "what": "Part %d (%s): new" % (i + 1, name), "kind": "layout"})
            continue
        j = match[i]
        was = A[j]
        if (i, j) not in kept:
            out.append({"part": i + 1, "what": "Part %d (%s): moved, was part %d" % (i + 1, name, j + 1), "kind": "order"})
        if was.get("s") != s.get("s"):
            out.append({"part": i + 1, "what": "Part %d: %s → %s" % (i + 1, kind(was.get("s")), name), "kind": "layout"})
        if key(was) != key(s):
            out.append({"part": i + 1, "what": "Part %d (%s): words changed" % (i + 1, name), "kind": "words"})
        n = len(set(_pics(s)) - set(_pics(was)))
        if n:
            out.append({"part": i + 1, "what": "Part %d (%s): %d new picture%s" % (i + 1, name, n, "s" if n > 1 else ""), "kind": "picture"})
    for j, s in enumerate(A):
        if j not in match.values():
            out.append({"what": "Removed: %s (was part %d)" % (kind(s.get("s")), j + 1), "kind": "layout"})
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["--make"]:                  # the background maker (start_maker)
        done, bad = make_missing([Path(a) for a in sys.argv[2:]])
        print("received pictures: %d made, %d failed" % (len(done), len(bad)))
        sys.exit(0)
    run = Path(sys.argv[1])
    f = found(run)
    if not f:
        sys.exit("%s: no designer Done with a commit before it, so no 'before' yet" % run.name)
    p, miss = picture(run, f)
    print("received %s (%s) → %s" % (f["rev"], f["at"], p))
    if miss:
        print("drawn grey (not on this Mac):", ", ".join(miss))
    sys.path.append(str(HERE.parent / "adapter"))
    import sync as S
    kind = lambda t: S.KIND.get(t, (t or "").replace("_", " ").capitalize())
    words = lambda s: [v for _, v in S.fields(s)]
    for c in changes(spec_at(run, f["rev"]), json.loads((run / "design" / "email.json").read_text()), kind, words):
        print(" ·", c["what"])
