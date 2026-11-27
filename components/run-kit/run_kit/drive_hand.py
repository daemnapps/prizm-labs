"""Hand a finished file to the Shared Drive and keep no lasting copy on this Mac.

    from run_kit import drive_hand
    drive_hand.hand(path)          # call once a final video or picture is done

owner, 2026-11-17, after the Mac filled up with finished renders: finished ad
exports go straight to the Drive folder, the Mac stays clean, and no new
scheduled job does it — the drop is part of the export step itself.

What `hand(path)` does, for a file under the workspace's `runs/`:
  1. copies it to `Shared Assets/runs/<same path>` on the Drive mount (a file
     already there is written over IN PLACE, so its Drive id and every link
     already handed out stay good; nothing on the Drive is ever removed);
  2. checks the Drive copy is the same size;
  3. puts a pointer (symlink) at the old place, so every board, page and later
     step that reads the file still finds it where it always was;
  4. starts one short-lived follower that waits for Drive to finish the upload
     and then tells Drive to drop this Mac's downloaded copy (the file stays in
     Drive and comes back by itself when something opens it). The follower ends
     when its list is empty or after FOLLOW_HOURS; the next hand() picks up
     anything it left.

It does nothing (and says why) when: there is no Drive mount (the mini, a
worker job with DRIVE_MOUNT=off, a teammate without Drive for desktop);
RUNS_TO_DRIVE=off; the file is not under runs/; or git tracks the file (those
stay exactly as they are). It never raises: a failed hand leaves the file
where it was. Returns (drive_path or None, note).

The mount is found through components/brandpath/drive_index.py mount() via
filing.drive_runs(), never typed. A temporary exception to builder-card rule 4
(keys-only Drive): owner's direct instruction to point exports at the mounted
Drive folder; eviction only exists on the mount.
"""
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import filing, paths

HERE = Path(__file__).resolve().parent
SWIFT = HERE / "drivetool.swift"
CACHE = Path.home() / "Library" / "Caches" / "ai-workspace" / "drive-hand"
FOLLOW_HOURS = 6
POLL_SECONDS = 30
# what a finished piece is: the picture or video itself, never its record (a .json/.md stays in git's reach)
FINISHED = {".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _say(msg):
    print("drive_hand: " + msg, file=sys.stderr)


def enabled():
    """RUNS_TO_DRIVE=off keeps everything on this machine; a home name picks that home."""
    return os.environ.get("RUNS_TO_DRIVE", "").lower() not in ("off", "0", "no")


def tool():
    """The compiled Drive status/drop helper, built from drivetool.swift into
    the Mac's cache on first use (and rebuilt when the source changes). None
    when it cannot be built (no swiftc, not a Mac)."""
    src = SWIFT.read_bytes()
    exe = CACHE / ("drivetool-" + hashlib.sha1(src).hexdigest()[:10])
    if exe.is_file():
        return exe
    swiftc = shutil.which("swiftc")
    if not swiftc:
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = exe.with_name(exe.name + ".building-%d" % os.getpid())
    r = subprocess.run([swiftc, "-O", "-o", str(tmp), str(SWIFT)], capture_output=True, text=True)
    if r.returncode != 0 or not tmp.is_file():
        _say("could not build the Drive helper: " + (r.stderr or "")[-300:])
        return None
    os.replace(str(tmp), str(exe))
    return exe


def status(paths_):
    """{path: uploaded?} for each file (folders walked). {} without the helper."""
    exe = tool()
    if not exe or not paths_:
        return {}
    out = subprocess.run([str(exe), "status"] + [str(p) for p in paths_], capture_output=True, text=True).stdout
    got = {}
    for line in out.splitlines():
        flag, _, p = line.partition("\t")
        got[p] = flag == "1"
    return got


def drop(paths_):
    """Tell Drive to drop this Mac's copy of each UPLOADED file. Returns the
    paths dropped. A file not uploaded yet is held, never touched."""
    exe = tool()
    if not exe or not paths_:
        return []
    out = subprocess.run([str(exe), "evict"] + [str(p) for p in paths_], capture_output=True, text=True).stdout
    return [line.split("\t", 1)[1] for line in out.splitlines() if line.startswith("dropped\t")]


# ------------------------------------------------------------------ the list

def _pending_file():
    return CACHE / "pending.json"


def _with_list(fn):
    CACHE.mkdir(parents=True, exist_ok=True)
    lock = open(str(CACHE / "pending.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            items = json.loads(_pending_file().read_text())
        except (OSError, ValueError):
            items = []
        items, out = fn(items)
        tmp = _pending_file().with_suffix(".tmp")
        tmp.write_text(json.dumps(items, indent=1))
        os.replace(str(tmp), str(_pending_file()))
        return out
    finally:
        lock.close()


def _queue(drive_path):
    def add(items):
        if str(drive_path) not in items:
            items.append(str(drive_path))
        return items, None
    _with_list(add)


def follow_once():
    """Drop every listed file Drive has finished uploading. Returns how many
    are still waiting."""
    def step(items):
        live = [p for p in items if os.path.exists(p)]
        up = status(live)
        done = [p for p in live if up.get(os.path.realpath(p), up.get(p))]
        dropped = set(drop(done)) if done else set()
        dropped_real = {os.path.realpath(p) for p in dropped}
        left = [p for p in live if p not in dropped and os.path.realpath(p) not in dropped_real]
        return left, len(left)
    return _with_list(step)


def follow(hours=FOLLOW_HOURS):
    """The one-shot follower: one at a time per Mac, ends when nothing waits."""
    CACHE.mkdir(parents=True, exist_ok=True)
    me = open(str(CACHE / "follower.lock"), "w")
    try:
        fcntl.flock(me, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0                       # another follower is already on it
    end = time.time() + hours * 3600
    left = follow_once()
    while left and time.time() < end:
        time.sleep(POLL_SECONDS)
        left = follow_once()
    return left


def _start_follower():
    CACHE.mkdir(parents=True, exist_ok=True)
    log = open(str(CACHE / "follower.log"), "a")
    subprocess.Popen([sys.executable, "-m", "run_kit.drive_hand", "follow"],
                     cwd=str(HERE.parent), stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                     start_new_session=True, close_fds=True)


# ------------------------------------------------------------------ the hand

def _tracked(repo, rel):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}   # the repo's own index, always
    r = subprocess.run(["git", "-C", str(repo), "ls-files", "--error-unmatch", "--", rel],
                       capture_output=True, text=True, env=env)
    return r.returncode == 0


def _repo_of(p, start=None):
    """The workspace holding `p`, walking up its path AS WRITTEN (never through
    a pointer into the Drive); else run-kit's own repo()."""
    if start is None:
        for d in [Path(p).parent, *Path(p).parent.parents]:
            if (d / "components").is_dir() and (d / "brands").is_dir() and (d / "runs").is_dir():
                return d
    return paths.repo(start)


# ------------------------------------------------------------------ where to

HOMES_FILE = Path.home() / ".drive-homes.json"
DEFAULT_HOME = "upright"


def homes():
    """The named Drive homes a file may go to, and the routes that pick one.

    A machine-local file, ~/.drive-homes.json, never in the repo, so a person's
    own drives are never written into team code:

        {"default": "upright",
         "homes":  {"upright": "<Drive folder>", "<name>": "<Drive folder>"},
         "routes": {"runs/video-edit/<brand>/<label>": "<name>", ...}}

    `upright` is always there: the company's Shared Assets on the mount
    (components/brandpath drive_index.mount()) unless the file names it.
    A route sends every file under that runs/ path to its home; the longest
    route wins. Returns (homes {name: Path}, routes {rel: name}, default)."""
    try:
        cfg = json.loads(HOMES_FILE.read_text())
    except (OSError, ValueError):
        cfg = {}
    hs = {k: Path(os.path.expanduser(v)) for k, v in (cfg.get("homes") or {}).items() if v}
    if DEFAULT_HOME not in hs:
        try:
            hs[DEFAULT_HOME] = filing.drive_runs().parent
        except filing.MountError:
            pass
    return hs, dict(cfg.get("routes") or {}), cfg.get("default") or DEFAULT_HOME


def choose(rel, to=None):
    """Which home a runs/<rel> file goes to: `to` if named, else
    RUNS_TO_DRIVE when it names a home, else the longest route, else the
    default. Returns (name, home folder) or (name, None) when that home is
    not on this machine."""
    hs, routes, default = homes()
    env = os.environ.get("RUNS_TO_DRIVE", "").strip().lower()
    name = to or (env if env in hs else None)
    if not name:
        key = "runs/" + str(rel).replace(os.sep, "/")
        best = None
        for r in routes:
            r_ = r.rstrip("/")
            if (key == r_ or key.startswith(r_ + "/")) and (best is None or len(r_) > len(best.rstrip("/"))):
                best = r
        name = routes[best] if best else None
    name = name or default
    return name, hs.get(name)


def route(rel_folder, to):
    """Point every future file under runs/<rel_folder> at home `to` (saved in
    ~/.drive-homes.json). `to` None removes the route."""
    try:
        cfg = json.loads(HOMES_FILE.read_text())
    except (OSError, ValueError):
        cfg = {}
    routes = cfg.setdefault("routes", {})
    key = "runs/" + str(rel_folder).replace(os.sep, "/").strip("/").split("runs/", 1)[-1]
    if to:
        routes[key] = to
    else:
        routes.pop(key, None)
    HOMES_FILE.write_text(json.dumps(cfg, indent=1) + "\n")
    return key


def _home_of(real):
    """The home name a Drive path sits in, or None."""
    hs, _, _ = homes()
    for name, h in hs.items():
        if str(real).startswith(os.path.realpath(str(h)) + os.sep):
            return name
    return None


def readable(path, root):
    """For a page that serves files from `root` (the workspace): the real file
    behind `path` when `path` sits inside `root` AS WRITTEN and its real place
    is inside `root` or under a Drive home's runs/ (a finished file handed to
    the Drive leaves a pointer). None otherwise. Never follows `..` out."""
    try:
        a = Path(os.path.normpath(os.path.abspath(str(path))))
        root = Path(os.path.abspath(str(root)))
        if root not in a.parents:
            return None
        real = Path(os.path.realpath(str(a)))
        if Path(os.path.realpath(str(root))) in real.parents:
            return real
        hs, _, _ = homes()
        for h in hs.values():
            if Path(os.path.realpath(str(h))) / "runs" in real.parents:
                return real
    except (OSError, ValueError):
        return None
    return None


def drive_path(path, start=None, to=None):
    """Where `path` (under runs/) goes on the Drive, or None."""
    try:
        p = Path(os.path.abspath(str(path)))
        rel = p.relative_to(_repo_of(p, start) / "runs")
        _, home = choose(rel, to)
        return home / "runs" / rel if home else None
    except (ValueError, FileNotFoundError):
        return None


def hand(path, start=None, follow_up=True, to=None):
    """Move one finished file to <home>/runs/<same path> (home: Upright's Shared
    Assets unless `to`, RUNS_TO_DRIVE or a route names another), leave a pointer
    at the old place, and have this Mac's copy dropped once Drive has it.
    Never raises. Returns (drive_path or None, note)."""
    try:
        return _hand(Path(os.path.abspath(str(path))), start, follow_up, to)
    except Exception as e:             # filing never stops a delivery
        _say("kept on this Mac, %s: %s" % (path, e))
        return None, "kept on this Mac: %s" % e


def _copy_in(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(src), str(dst))        # over an existing file in place: same Drive id
    try:
        shutil.copystat(str(src), str(dst))
    except OSError:
        pass
    return os.stat(str(dst)).st_size == os.stat(str(src)).st_size


def _point(p, dst):
    link = p.with_name("." + p.stem + ".drive-link" + p.suffix)   # same suffix: same .gitignore line
    if os.path.lexists(str(link)):
        os.unlink(str(link))
    os.symlink(str(dst), str(link))
    os.replace(str(link), str(p))              # the swap is one step: never a moment with no file


def _hand(p, start, follow_up, to):
    if not enabled():
        return None, "RUNS_TO_DRIVE is off"
    repo = _repo_of(p, start)
    try:
        rel = p.relative_to(repo / "runs")
    except ValueError:
        return None, "not under runs/"
    name, home = choose(rel, to)
    if home is None:
        return None, "no Drive home '%s' on this machine" % name
    dst = home / "runs" / rel
    real = Path(os.path.realpath(str(p)))
    on = _home_of(real)
    if on:
        # already on a Drive: a pointer (maybe re-rendered through it), or its
        # whole run folder was moved there earlier
        if on != name and p.is_symlink() and real.is_file():
            # asked for another home: copy it over and repoint; the first copy
            # stays where it is (nothing on a Drive is ever removed)
            if not _copy_in(real, dst):
                return None, "the %s copy came out a different size; pointer unchanged" % name
            _point(p, dst)
            real = dst
        if real.is_file():
            _queue(real)
            if follow_up:
                _start_follower()
        return real, "on the %s Drive" % (on if real != dst else name)
    if p.is_symlink():
        return None, "a pointer to somewhere else; left alone"
    if not p.is_file():
        return None, "no such file"
    if _tracked(repo, str(Path("runs") / rel)):
        return None, "tracked in git; left as it is"
    if not _copy_in(p, dst):
        return None, "the Drive copy came out a different size; kept on this Mac"
    _point(p, dst)
    _queue(dst)
    if follow_up:
        _start_follower()
    return dst, "on the %s Drive; this Mac's copy drops once the upload finishes" % name


def hand_all(files, start=None, to=None):
    """hand() each file, one follower for the lot. Returns [(path, drive_path, note)]."""
    out = []
    for f in files:
        d, note = hand(f, start, follow_up=False, to=to)
        out.append((str(f), d, note))
    if any(d for _, d, _ in out):
        _start_follower()
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "follow":
        sys.exit(1 if follow() else 0)
    if len(sys.argv) >= 3 and sys.argv[1] == "hand":
        args, to = sys.argv[2:], None
        if "--to" in args:
            i = args.index("--to"); to = args[i + 1]; args = args[:i] + args[i + 2:]
        for f, d, note in hand_all(args, to=to):
            print("%s -> %s (%s)" % (f, d, note))
        sys.exit(0)
    if len(sys.argv) >= 3 and sys.argv[1] == "route":
        print("routed:", route(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
        sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == "homes":
        hs, rs, d = homes()
        print(json.dumps({"default": d, "homes": {k: str(v) for k, v in hs.items()}, "routes": rs}, indent=1))
        sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == "status":
        print("waiting:", follow_once())
        sys.exit(0)
    print("usage: python3 -m run_kit.drive_hand hand <file>... [--to <home>] | route <runs/ folder> [<home>] | homes | follow | status")
    sys.exit(2)
