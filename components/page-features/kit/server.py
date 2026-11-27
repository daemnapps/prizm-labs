#!/usr/bin/env python3
"""PF-14 (page server): a person's own always-on private server for ALL their pages, switched on and off by asking
their Claude, syncing through its own private copy of the repo.

    python3 components/page-features/kit/server.py on [--no-open]   check, make the private copy, install, prove, open
    python3 components/page-features/kit/server.py off              switch it off (the private copy stays)
    python3 components/page-features/kit/server.py status           on or off, port, last sync, not pushed, clicks, down
    python3 components/page-features/kit/server.py restart [--new-token]  off, then on (--new-token: a new key)
    python3 components/page-features/kit/server.py remove [--force] off, then delete its own private copy and folder
    python3 components/page-features/kit/server.py push             push what the server kept (from your session)
    python3 components/page-features/kit/server.py run              what the background agent starts; not for people

Exit 0 ok · 2 refused, with the fix named · 1 failed.

Where it lives (nothing of it in git): ~/Library/Caches/upright-page-server/<person>/ holds config.json (person,
port, the clone `on` ran from), repo/ (the PRIVATE COPY: `git worktree add --detach … origin/main`, made from that
clone), state.json (last sync, families down), clicks.jsonl (one line per button click), server.log, git.lock,
token (PF-14e (token survives), owner-only).
The agent is ~/Library/LaunchAgents/com.upright.page-server.plist: /usr/bin/python3 <state>/repo/…/server.py run,
started at login and again whenever it exits.

`run` serves, on 127.0.0.1:<port> only: `/` the person's home page (PF-17 (home page family), below); `/plain` the
person's page index (PF-8 (show my pages)'s pages.list_pages: live
pages, then drafts, then other pages, each a link) with a status line (synced N s ago · N not pushed · families
down) and the last 20 clicks; `/v/<path under platform/views/viewers/>` a page exactly as kit/serve.py serves one,
with every serve.py route beside it (/p/, /data, /stamp, /runs, /status, POST /act with its guards and token). A
route a page asks for is answered for THAT page's family (from the request's Referer; a /data or /stamp name only
one family declares answers without one). One family's failing source marks that family "down" on its own pages
and on the index; every other family keeps serving. A source or family may declare "keys": [<NAME>, …]; a name
missing from the environment is "down: needs <NAME>" and runs nothing (keys for the server are a later card).

Sync (a thread, every 60 s), ONLY in the private copy: fetch; no local commits → merge --ff-only origin/main;
local commits → rebase origin/main, push HEAD to main (4 tries). A push the agent cannot make (no git login there)
keeps the commit; the index and `status` say "N not pushed — say 'push my page server' to your Claude", and `push`
pushes from the person's session. A pull that changed components/page-features/kit/ ends `run` (exit 0) after the
requests in flight; the agent starts it again on the new code. A rebase that stops is said as "diverged" until a
sync succeeds. No git command ever runs in the person's own working folder except `on`'s fetch and `worktree add`
and `remove`'s `worktree remove` and `prune` (and run-kit's whoami reading git config).

Direct buttons (PF-13 (direct buttons)) run from the private copy: their commands commit there. Their own `git
push` is pointed at main for that one command (GIT_CONFIG_COUNT: remote.origin.push=HEAD:refs/heads/main, the copy
is detached); whatever they leave unpushed the server pushes right after the click.

Slow buttons (PF-13b (slow buttons)): one Jobs (kit/jobs.py) for the whole server, every family's Act sharing it,
so one email never has two jobs. A job waits for the copy's one git writer (StateLock) before it starts, then runs
without it; the sync skips its round while any job is queued or running (the commands commit in the copy). When a
job ends the server pushes what it left unpushed, as after a click, and writes ONE line to clicks.jsonl: the click's
keys plus job, item, state and, when it failed, "ask" — "ask your Claude to finish it" with the exact request line.

Lifted, credited and adapted, never imported: owner's jobs.py (launchctl bootstrap/bootout/list, and refusing to
switch off the page you are using) and his board's per-tool "down" (git c686a6327b^:lab/owner/suite/). Not lifted:
his per-request code reload, his unguarded spend routes. Every platform call sits behind MacAgent or WinAgent.
Stdlib only, Python 3.9.

PF-14b (Windows page server): on Windows the folder is %LOCALAPPDATA%\\upright-page-server\\<person>\\ and the agent
is a Task Scheduler task, UprightPageServer, at logon: "<the Python `on` ran with>" "<state>\\repo\\…\\server.py"
supervise. `supervise` (Windows has no KeepAlive) runs `run` as its child, its output into server.log, and starts
it again when it exits: 1 s, doubling to 60 s while it keeps exiting within 10 s. `off` writes <state>/stop (a
supervise still alive ends its child and itself), then schtasks /End and /Delete. A supervised `run` also ends when
its supervise is gone (its stdin pipe closes). Locks: msvcrt where there is no fcntl.

PF-16 (fixed port): one permanent port per person, the same on every machine: "page_server_port" in
team/people/<person>/identity.json under the repo (8740–8749), read by record_port() here. `on`, `run` and `restart`
use exactly that port: free → serve on it; held → refused (exit 2), naming the holder (lsof on macOS, netstat -ano +
tasklist on Windows) and the fix. No fallback, no range, ever; a person with no port in their record is refused by
name. config.json's port is only the last address `on` started: an older one is ignored, the server moves to the
fixed port, and `on` says the new bookmark once. `status` and the index show the fixed port and say so when the
record and the running server disagree.

PF-16b (Windows port check): on Windows "held" comes from netstat -ano's TCP and TCPv6 tables — a LISTENING row on
exactly the port at 127.0.0.1, 0.0.0.0, ::1 or [::] — never a connect probe (Windows retries a connect to a closed
loopback port for ~2 s, so a probe's timeout called every free port held); macOS keeps the bind + connect check. With
no such row the holder line says "no listener found" and quotes nothing. On Windows stdout and stderr are utf-8
(errors replaced) from start-up, so the lines survive a cp1252 console.

PF-17 (home page family): `/` is a page of the family `home`, changed like any family with /page-draft, /page-change
and /page-live. It serves the person's live viewers/<person>/home.html when there is one, else _templates/home.html
(and the built-in index when this copy has neither). The template reads `/data/home` — answered here, never by a
sources.json: person, port, the status fields and line, families down and warnings, PF-8 (show my pages)'s list,
the last 20 clicks. Above any page served at `/` the server injects its own strip (the status line, with the fixed
port, and a link to /plain), first in <body> and outside the page's markup: a host element with no id and a tag name
new on every response (ps-<random>), its words in a CLOSED declarative shadow root (attached by script where the
browser does not read the declarative form), its inline style !important, and a guard script, run right after it,
that puts it back when the page removes it or edits its style. So a page's CSS on an id, a tag or a class cannot
reach it and a script that deletes the node sees it come back. `/plain` always serves the built-in index_html,
unchanged.

PF-16c (Windows git hang): every git call `run` makes or passes down has a timeout, GIT_TIMEOUT s. A call that does
not answer is killed with everything it started (taskkill /T /F on Windows, where cmd\\git.exe starts the real
git.exe; the child alone on macOS) and said as "git did not answer in N s: <command>" — one listing waits at most
once, the later calls of that listing fail at once with the same line, which /status, /data/home and the status line
on / and /plain carry until a listing answers. Every child starts with stdin from NUL and only its own three handles,
no window on Windows; the listening socket and git.lock are non-inheritable there. The cause: a supervised `run`
watched its stdin (supervise's pipe) with a blocking read, a read pending on a synchronous pipe locks its file
object, and every child that inherited that stdin (git, which asks the pipe its name at start-up) waited on the lock.
On Windows the watch now peeks at the pipe once a second and never reads it.

PF-14c (click lock): every git that only reads the private copy runs with GIT_OPTIONAL_LOCKS=0 — the page list
behind /, /plain and /data/home (GitRunner), and every child of `run` (data sources included) — so none of them
takes the copy's index.lock. The cause, reproduced 2026-10-29: the page list's `git status --porcelain` refreshes
the index under index.lock, outside the server's git lock, and a click's `git commit` meeting it failed. A quick
click whose command failed but wrote files in the copy is "saved — commit pending (<why>)" (its answer and its
click line, ok, with "pending"); the files are kept in <state>/pending.json and the next sync commits them before
it fetches. "failed" only when the command wrote nothing. A job's own commit still runs outside the lock (PF-13b
(slow buttons)'s design); a quick click meeting it is caught the same way.

PF-14d (page family check): POST /act runs only the buttons of the family of the page that sent it
(serve.family_of(page_of()), / being the home family's page): a body family that differs is 403 "this page's buttons
are <family>'s" and a request from no page of this server (no Referer here) 403; nothing runs and the click line is
"refused". POST /upload keeps its own guards (Host, Origin, token) and is not checked against the page.

PF-19 (behind notice): every listing (/, /plain, /data/home) keeps PF-8 (show my pages)'s behind live pages; the
status line — the strip on /, /plain's status, the home page's status line — ends with each one's line, "Your page
is behind the team version since <date> — say 'catch up my <family> page'", and /data/home carries them as
"pages_behind" (with the commits since the base). A live page whose family's actions.json changed after it went
live gets 403 on /act (serve.py's Act, live.stale_actions) and its click line is "refused": act.js copies the
request for Claude and says why.

PF-14e (token survives): the /act key a page carries is written once per server into <state>/token — owner-only
(created 0600 on macOS, re-read only when it is a regular file of this user with no group or other bit; on Windows
the user's own %LOCALAPPDATA% folder's ACL) — and re-read at every start, so a restart (each kit merge) leaves open
pages' buttons working. A new key only by `remove` (the file goes with the folder) or `restart --new-token`; a file
that cannot be written leaves the key in memory, said in server.log by path, never by value. The token is never in
git, a log line, clicks.jsonl or state.json. Host, Origin and token checks are serve.py's, unchanged; a key that is
present but wrong is "your page server restarted with a new key — reload the page".
"""
import argparse
import datetime
import glob
import html
import json
import os
import plistlib
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    import fcntl
except ImportError:  # Windows: msvcrt below, PF-14b (Windows page server)
    fcntl = None
try:
    import msvcrt
except ImportError:  # macOS
    msvcrt = None

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import serve  # noqa: E402  PF-4 (page starter kit), same folder: the kit's classes and routes
import jobs  # noqa: E402  PF-13b (slow buttons), same folder: background jobs
sys.path.append(os.path.dirname(HERE))
import pages  # noqa: E402  PF-8 (show my pages), same component: list_pages, its public reading
from run_kit import paths, people  # noqa: E402  appended by serve: the one locator and the one person resolver

LABEL = "com.upright.page-server"
PYTHON = "/usr/bin/python3"
PORT_FIELD = "page_server_port"                   # PF-16 (fixed port): in team/people/<person>/identity.json
PORT_FIX = "stop it, or ask the lead for a per-person override"
FREE_WAIT = 5.0                                     # restart / move: the old server's port, a moment to let go
SYNC_EVERY = 60
PUSH_TRIES = 4
KIT = "components/page-features/kit/"
SELF = os.path.join("components", "page-features", "kit", "server.py")
SELF_ENV = "UPRIGHT_PAGE_SERVER"
SUPERVISED_ENV = "UPRIGHT_PAGE_SERVER_SUPERVISED"
TASK = "UprightPageServer"
STOP = "stop"
FAST_EXIT = 10
BACKOFF_MAX = 60
SUPPORTED = ("the page server runs on macOS (a LaunchAgent) and Windows (a Task Scheduler task) only; this machine "
             "is %s")
ASK_PUSH = "say 'push my page server' to your Claude"
CLICKS_SHOWN = 20
HOME = "home"                                       # PF-17 (home page family): the family whose page / serves
PLAIN = "/plain"
DATA_HOME = "/data/home"
GIT_TIMEOUT = 20                                    # PF-16c (Windows git hang): every git call `run` makes or passes
KILL_WAIT = 2                                       # a killed child's pipes, a moment to close
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
PEEK_EVERY = 1.0                                    # supervise's pipe, looked at (never read) on Windows
NO_LOCKS = {"GIT_OPTIONAL_LOCKS": "0"}             # PF-14c (click lock): a git that reads never takes index.lock
PENDING = "saved — commit pending (%s)"             # PF-14c: a click that wrote but could not commit
PENDING_FILE = "pending.json"
NO_PAGE = "refused: this button was not pressed on a page of this server"   # PF-14d (page family check)
TOKEN_FILE = "token"                                # PF-14e (token survives): <state>/token, owner-only
TOKEN_SHAPE = re.compile(r"[A-Za-z0-9_-]{40,100}")  # what secrets.token_urlsafe(32) gives
STRIP_MARK = "<!-- page server strip: the server's own, above every page at / -->"
STRIP_STYLE = ("all:initial!important;display:block!important;position:sticky!important;top:0!important;"
               "z-index:2147483647!important;visibility:visible!important;opacity:1!important;"
               "transform:none!important;clip-path:none!important")
STRIP_CSS = (":host{all:initial}div{display:block;background:#f4f4f2;color:#1d1d1b;font:13px/1.45 system-ui,"
             "-apple-system,'Segoe UI',sans-serif;padding:6px 12px;border-bottom:1px solid #d9d9d4}"
             "a{color:#2b5fd9}b{font-weight:600}")
# The guard: run once, right after the host. A browser that left the <template> in place (no declarative shadow DOM)
# gets the closed root here; then the host goes back first in <body> when it leaves it, and its style back when edited.
STRIP_GUARD = (
    "<script>(function(s){var h=s.previousElementSibling,d=document,ins=Node.prototype.insertBefore,"
    "ga=Element.prototype.getAttribute,sa=Element.prototype.setAttribute,st=ga.call(h,'style'),M=window.MutationObserver,"
    "t=h.querySelector('template');if(t){try{var r=h.attachShadow({mode:'closed'});r.appendChild(t.content);"
    "h.removeChild(t)}catch(e){}}function keep(){var b=d.body;if(b&&h.parentNode!==b)ins.call(b,h,b.firstChild);"
    "if(ga.call(h,'style')!==st)sa.call(h,'style',st)}if(M){new M(keep).observe(d.documentElement,"
    "{childList:true,subtree:true});new M(keep).observe(h,{attributes:true})}s.parentNode.removeChild(s)})"
    "(document.currentScript)</script>")


def strip_html(line):
    """PF-17 (home page family): the server's strip, as injected above a page at /."""
    tag = "ps-" + secrets.token_hex(6)
    words = ('<div role="status"><b>Page server</b> · %s · <a href="%s">plain page list</a></div>'
             % (html.escape(line), PLAIN))
    return ('%s<%s style="%s"><template shadowrootmode="closed"><style>%s</style>%s</template></%s>%s'
            % (STRIP_MARK, tag, STRIP_STYLE, STRIP_CSS, words, tag, STRIP_GUARD))


def with_strip(data, line):
    """The page with the strip first in its <body> (after its <!doctype> when it has no <body>; at the top when it
    has neither). The page's bytes are otherwise untouched."""
    text = data.decode("utf-8", "replace")
    m = re.search(r"<body(\s[^>]*)?>", text, re.I) or re.search(r"<!doctype[^>]*>", text, re.I)
    at = m.end() if m else 0
    return (text[:at] + strip_html(line) + text[at:]).encode("utf-8")


def now_z(t=None):
    return datetime.datetime.fromtimestamp(time.time() if t is None else t, datetime.timezone.utc) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")


def child_kw(platform=None):
    """PF-16c (Windows git hang): how every child of the server starts — stdin from NUL, no handle but its own three,
    and on Windows no console window."""
    kw = {"stdin": subprocess.DEVNULL, "close_fds": True}
    if windows(platform):
        kw["creationflags"] = NO_WINDOW
    return kw


def did_not_answer(argv, timeout):
    return "%s did not answer in %d s: %s" % (os.path.basename(argv[0]) if argv else "the command", timeout,
                                              " ".join(argv))


def kill_tree(p, platform=None, run=None):
    """A timed-out child and everything it started: on Windows `taskkill /T /F /PID` (cmd\\git.exe is a shim that
    starts the real git.exe), then the child itself; on macOS the child."""
    if windows(platform):
        try:
            (run or subprocess.run)(["taskkill", "/T", "/F", "/PID", str(p.pid)], stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=10, **child_kw(platform))
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        p.kill()
    except OSError:
        pass


def call(argv, cwd=None, timeout=GIT_TIMEOUT, env=None, platform=None, popen=None, kill=None):
    """(code, stdout, stderr), or None when it did not answer in `timeout` s — then it and its children are killed
    and its pipes get KILL_WAIT s to close, so the caller never waits longer. PF-16c (Windows git hang)."""
    p = (popen or subprocess.Popen)(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True, **child_kw(platform))
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        (kill or kill_tree)(p, platform)
        try:
            p.communicate(timeout=KILL_WAIT)
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
        return None
    return p.returncode, out, err


def run_cmd(argv, cwd=None, timeout=120):
    """(code, stdout) on success, (code, stderr or stdout) on failure; never waits on a password prompt, nor past
    `timeout` s."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        got = call(argv, cwd, timeout, env)
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        return 1, str(e)
    if got is None:
        return 1, did_not_answer(argv, timeout)
    code, out, err = got
    return code, (out if code == 0 else (err or out))


def git_cmd(argv, cwd=None):
    """run_cmd for the private copy's git: GIT_TIMEOUT s, PF-16c (Windows git hang)."""
    return run_cmd(argv, cwd, GIT_TIMEOUT)


def reading_env():
    """PF-14c (click lock): the environment of a git that only reads — no prompt, no optional lock."""
    return dict(os.environ, GIT_TERMINAL_PROMPT="0", **NO_LOCKS)


def reading_call(argv, cwd=None, timeout=GIT_TIMEOUT):
    """call() for a git that only reads: it never takes index.lock to refresh the index."""
    return call(argv, cwd, timeout, env=reading_env())


def commit_why(out):
    """PF-14c (click lock): the line of a command's output that says why its commit did not happen — the first that
    names git's lock or a failure, else its last line."""
    lines = [x.strip() for x in (out or "").splitlines() if x.strip()]
    for x in lines:
        if re.search(r"index\.lock|fatal:|error:|not committed|not shared|failed", x):
            return x[:200]
    return lines[-1][:200] if lines else "no message"


def pending_line(why):
    return PENDING % why + "; the page server's next sync commits it"


class GitRunner(object):
    """PF-16c (Windows git hang): the runner the server hands pages.list_pages, one per listing — features.run_git's
    (code, stdout, stderr), started by call(). A call that does not answer in `timeout` s is killed and fails with
    "git did not answer in N s: <command>"; every later call of the same listing fails at once with that line, so
    a listing waits on git at most once. `stuck` is the line, or None. PF-14c (click lock): its git takes no
    optional lock (the listing's `git status` never holds the copy's index.lock)."""

    def __init__(self, timeout=GIT_TIMEOUT, call_=None):
        self.timeout, self.call, self.stuck = timeout, call_ or reading_call, None

    def __call__(self, argv, cwd):
        if self.stuck:
            return 1, "", self.stuck
        got = self.call(argv, cwd, self.timeout)
        if got is None:
            self.stuck = did_not_answer(argv, self.timeout)
            return 1, "", self.stuck
        return got


def watch_parent(stream, platform=None, peek=None, every=PEEK_EVERY, sleep=time.sleep):
    """Returns when supervise's pipe on `stream` (our stdin) has closed. On macOS a blocking read. On Windows never a
    read: a read pending on a synchronous pipe locks its file object, and a child that inherits the pipe as its
    stdin waits on that lock at start-up (git asks the pipe its name) — so the pipe is peeked at every `every` s
    until it is broken. PF-16c (Windows git hang)."""
    if not windows(platform):
        stream.buffer.read()
        return
    if peek is None:
        import _winapi
        handle = msvcrt.get_osfhandle(stream.fileno())
        peek = lambda: _winapi.PeekNamedPipe(handle, 0)  # noqa: E731
    while True:
        try:
            peek()
        except (OSError, ValueError):
            return
        sleep(every)


def caches(home=None, platform=None, env=None):
    """macOS ~/Library/Caches/upright-page-server; Windows %LOCALAPPDATA%\\upright-page-server (else
    <home>\\AppData\\Local), PF-14b (Windows page server)."""
    if (platform or sys.platform) == "win32":
        local = (os.environ if env is None else env).get("LOCALAPPDATA")
        return (Path(local) if local else Path(home or Path.home()) / "AppData" / "Local") / "upright-page-server"
    return Path(home or Path.home()) / "Library" / "Caches" / "upright-page-server"


def state_of(person, home=None, platform=None):
    return caches(home, platform) / person


def read_json(path, default=None):
    try:
        with open(str(path), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    tmp = "%s.tmp" % path
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True)
    os.replace(tmp, str(path))


# ---------------------------------------------------------------------------------------------- PF-14e (token survives)

def token_private(st, platform=None):
    """A token file the server may trust: a regular file; on macOS also this user's own, with no group or other
    bit. On Windows the user's own %LOCALAPPDATA% folder's ACL is what keeps it private."""
    if not stat.S_ISREG(st.st_mode):
        return False
    return windows(platform) or (st.st_uid == os.getuid() and not st.st_mode & 0o077)


def read_token(state):
    """The kept token, or None (no file, not private, a link, not a token's shape)."""
    try:
        fd = os.open(os.path.join(str(state), TOKEN_FILE), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return None
    try:
        if not token_private(os.fstat(fd)):
            return None
        got = os.read(fd, 256).decode("ascii", "replace").strip()
    except OSError:
        return None
    finally:
        os.close(fd)
    return got if TOKEN_SHAPE.fullmatch(got) else None


def write_token(state, token):
    """<state>/token, created 0600 beside it and moved into place, so no moment has it wider."""
    path = os.path.join(str(state), TOKEN_FILE)
    tmp = path + ".tmp"
    try:
        os.unlink(tmp)                                    # its own temp file, from a write cut short
    except OSError:
        pass
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        os.write(fd, token.encode("ascii"))
    finally:
        os.close(fd)
    os.replace(tmp, path)


def kept_token(state, new=False):
    """(token, why): the token kept in <state>/token, minted and written once when there is none (or `new`); why is
    None when it is kept, else the reason it lives in memory only. Never says the token itself."""
    if not new:
        got = read_token(state)
        if got:
            return got, None
    token = secrets.token_urlsafe(32)
    try:
        write_token(state, token)
    except OSError as e:
        return token, "in memory only: %s could not be written (%s)" % (
            os.path.join(str(state), TOKEN_FILE), e.strerror or type(e).__name__)
    return token, None


def drop_token(state):
    """`remove`: the kept token goes, so the next `on` mints a new one."""
    try:
        os.unlink(os.path.join(str(state), TOKEN_FILE))
    except OSError:
        pass


def plural(k, word):
    return "%d %s%s" % (k, word, "" if k == 1 else "s")


def click_word(c):
    """A click line's one word: refused (PF-14d (page family check): nothing ran), saved — commit pending (PF-14c
    (click lock): written, the next sync commits it), ok, or failed (nothing written)."""
    if c.get("refused"):
        return "refused"
    if c.get("pending"):
        return "saved — commit pending"
    return "ok" if c.get("ok") else "failed"


def not_pushed(k):
    return "%d not pushed — the page server kept %s here; %s" % (k, plural(k, "commit"), ASK_PUSH)


# ---------------------------------------------------------------------------------------------- the platform seam

class MacAgent(object):
    """THE one platform seam: install, start, stop, remove, status, show. A macOS LaunchAgent; PF-14b (Windows page
    server) adds its Windows twin beside it. launchctl bootstrap/bootout/print lifted, adapted, from owner's jobs.py
    (git c686a6327b^:lab/owner/suite/jobs.py, switch())."""
    platform, python, verb, tool = "darwin", PYTHON, "run", "launchctl"

    def __init__(self, home=None, runner=None, uid=None):
        self.home = Path(home or Path.home())
        self.runner = runner or run_cmd
        self.uid = os.getuid() if uid is None else uid
        self.plist = self.home / "Library" / "LaunchAgents" / (LABEL + ".plist")

    def install(self, argv, workdir, log):
        self.plist.parent.mkdir(parents=True, exist_ok=True)
        with open(str(self.plist), "wb") as fh:
            plistlib.dump({"Label": LABEL, "ProgramArguments": list(argv), "RunAtLoad": True, "KeepAlive": True,
                           "StandardOutPath": str(log), "StandardErrorPath": str(log),
                           "WorkingDirectory": str(workdir)}, fh)

    def start(self):
        return self.runner(["launchctl", "bootstrap", "gui/%d" % self.uid, str(self.plist)])

    def stop(self):
        code, out = self.runner(["launchctl", "bootout", "gui/%d/%s" % (self.uid, LABEL)])
        gone = code == 0 or "No such process" in (out or "") or "Could not find" in (out or "")
        return (0 if gone else code), out

    def remove(self):
        """Its own plist, and nothing else in LaunchAgents."""
        if self.plist.is_file():
            self.plist.unlink()

    def status(self):
        code, out = self.runner(["launchctl", "print", "gui/%d/%s" % (self.uid, LABEL)])
        m = re.search(r"^\s*pid = (\d+)", out or "", re.M) if code == 0 else None
        return {"loaded": code == 0, "pid": int(m.group(1)) if m else None, "installed": self.plist.is_file()}

    def show(self, url):
        return self.runner(["open", url])


def task_status(out):
    """The Status: field of `schtasks /Query /FO LIST` output ("Running", "Ready", …), or None."""
    m = re.search(r"^\s*Status:\s*(.+?)\s*$", out or "", re.M)
    return m.group(1) if m else None


class WinAgent(object):
    """MacAgent's Windows twin, PF-14b (Windows page server): a Task Scheduler task at logon, running `supervise`
    (Windows has no KeepAlive) with the Python that ran `on`. "loaded" = the task is Running."""
    platform, verb, tool = "win32", "supervise", "schtasks"

    def __init__(self, home=None, runner=None, python=None, startfile=None):
        self.home = Path(home or Path.home())
        self.runner = runner or run_cmd
        self.python = python or sys.executable
        self.startfile = startfile or getattr(os, "startfile", None)

    def install(self, argv, workdir, log):
        """(code, out). Task Scheduler has no working folder or log option: supervise sets both itself."""
        tr = " ".join('"%s"' % a if i < 2 else a for i, a in enumerate(argv))
        return self.runner(["schtasks", "/Create", "/SC", "ONLOGON", "/TN", TASK, "/TR", tr, "/RL", "LIMITED", "/F"])

    def start(self):
        return self.runner(["schtasks", "/Run", "/TN", TASK])

    def stop(self):
        """A failed /End counts as stopped when the task is not running (or not there) any more."""
        code, out = self.runner(["schtasks", "/End", "/TN", TASK])
        return (0, out) if code and not self.status()["loaded"] else (code, out)

    def remove(self):
        """(code, out): its own task, and nothing else in Task Scheduler (cmd_off has stopped it first). A failed
        /Delete counts as done when the task is not there."""
        code, out = self.runner(["schtasks", "/Delete", "/TN", TASK, "/F"])
        return (0, out) if code and not self.status()["installed"] else (code, out)

    def status(self):
        code, out = self.runner(["schtasks", "/Query", "/TN", TASK, "/FO", "LIST"])
        said = task_status(out) if code == 0 else None
        return {"loaded": (said or "").lower() == "running", "pid": None, "installed": code == 0, "said": said}

    def show(self, url):
        if self.startfile is None:
            return 1, "no os.startfile here"
        try:
            self.startfile(url)
        except OSError as e:
            return 1, str(e)
        return 0, ""


def agent_for(platform=None, home=None, runner=None):
    """The platform's agent: MacAgent on macOS, WinAgent on Windows, None anywhere else."""
    platform = platform or sys.platform
    if platform == "darwin":
        return MacAgent(home, runner)
    if platform == "win32":
        return WinAgent(home, runner)
    return None


class StateLock(object):
    """One git writer at a time in the private copy: a thread lock, plus a file lock on <state>/git.lock so `push`
    from a session and the agent's sync never run git there together (fcntl on macOS, msvcrt on Windows)."""

    def __init__(self, state):
        self.path, self.inner = os.path.join(str(state), "git.lock"), threading.Lock()
        self.fh = None

    def __enter__(self):
        self.inner.acquire()
        if fcntl is not None:
            self.fh = open(self.path, "a")
            self.private()
            fcntl.flock(self.fh, fcntl.LOCK_EX)
        elif msvcrt is not None:
            self.fh = open(self.path, "a+")
            self.private()
            self.fh.seek(0)
            while True:
                try:
                    msvcrt.locking(self.fh.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:                           # LK_LOCK gives up after ~10 s; keep waiting
                    continue
        return self

    def private(self):
        """PF-16c (Windows git hang): on Windows the lock's handle is never inherited by a child (Python opens it so;
        said here so no later open changes it)."""
        if windows():
            os.set_inheritable(self.fh.fileno(), False)

    def __exit__(self, *a):
        if self.fh is not None:
            if fcntl is not None:
                fcntl.flock(self.fh, fcntl.LOCK_UN)
            elif msvcrt is not None:
                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
            self.fh.close()
            self.fh = None
        self.inner.release()


# ---------------------------------------------------------------------------------------------- the private copy

class Copy(object):
    """The server's private copy. Every git command here is `git -C <state>/repo …`, GIT_TIMEOUT s unless the
    caller hands its own runner."""

    def __init__(self, path, runner=None):
        self.path, self.runner = str(path), runner or git_cmd

    def git(self, *args):
        return self.runner(["git", "-C", self.path] + list(args))

    def head(self):
        code, out = self.git("rev-parse", "HEAD")
        return out.strip() if code == 0 else None

    def count(self, rng):
        code, out = self.git("rev-list", "--count", rng)
        try:
            return int(out.strip()) if code == 0 else None
        except ValueError:
            return None

    def ahead(self):
        return self.count("origin/main..HEAD")


def _last(out):
    lines = [x.strip() for x in (out or "").splitlines() if x.strip()]
    return lines[-1][:200] if lines else "no message"


class Sync(object):
    """Keeps the private copy on origin/main: fetch, fast-forward or rebase + push. Holds the lock throughout."""

    def __init__(self, copy, lock, clock=time.time, tries=PUSH_TRIES):
        self.copy, self.lock, self.clock, self.tries = copy, lock, clock, tries
        self.last = {"at": None, "ok": None, "said": "not synced yet", "ahead": None, "behind": None, "good_at": None}
        self.restart = threading.Event()
        self.hold = None                # PF-13b (slow buttons): a callable; true = jobs are running, skip this round
        self.before = None              # PF-14c (click lock): a callable run first, lock held: the pending clicks'
                                        # commit; returns what it said, or None

    def push(self, tries=None):
        """(ok, said): rebase the copy's own commits onto origin/main and push HEAD to main; a rejected push fetches
        and tries again, anything else (no git login here) keeps the commits. Call with the lock held."""
        said = "nothing to push"
        for i in range(tries or self.tries):
            if i:
                self.copy.git("fetch", "-q", "origin")
            if not self.copy.ahead():
                return True, said
            code, out = self.copy.git("rebase", "--autostash", "-q", "origin/main")
            if code:
                self.copy.git("rebase", "--abort")
                return False, "diverged: the rebase onto origin/main stopped (%s)" % _last(out)
            code, out = self.copy.git("push", "-q", "origin", "HEAD:refs/heads/main")
            if code == 0:
                return True, "pushed"
            said = "not pushed: %s" % _last(out)
            if not re.search(r"\[rejected\]|fetch first|non-fast-forward", out or ""):   # someone pushed first
                return False, said
        return False, said

    def once(self):
        """One sync; the record it keeps. Asks `run` to restart when the pull changed the kit."""
        with self.lock:
            if self.hold and self.hold():
                return dict(self.last)                   # a job's command is committing here; next round
            at = self.clock()
            first = self.before() if self.before else None
            old = self.copy.head()
            code, out = self.copy.git("fetch", "-q", "origin")
            if code:
                ok, said = False, "fetch failed: %s" % _last(out)
            elif self.copy.ahead():
                ok, said = self.push()
            elif self.copy.count("HEAD..origin/main"):
                code, out = self.copy.git("merge", "--ff-only", "-q", "origin/main")
                ok, said = (True, "pulled") if code == 0 else \
                    (False, "diverged: fast-forward refused (%s)" % _last(out))
            else:
                ok, said = True, "up to date"
            new = self.copy.head()
            if old and new and old != new:
                code, out = self.copy.git("diff", "--name-only", old, new, "--", KIT)
                if code == 0 and out.strip():
                    self.restart.set()
                    said += "; the kit changed, restarting on the new code"
            if first:
                said = "%s; %s" % (first, said)
            self.last = {"at": at, "ok": ok, "said": said, "ahead": self.copy.ahead(),
                         "behind": self.copy.count("HEAD..origin/main"),
                         "good_at": at if ok else self.last.get("good_at")}
            return dict(self.last)


# ---------------------------------------------------------------------------------------------- serving

def gather(jobs, timeout=60):
    """({name: result}, {name: error}): each job in its own thread, one failing never stops the rest. Lifted,
    adapted, from owner's board (git c686a6327b^:lab/owner/suite/suite_serve.py, board())."""
    res, err = {}, {}
    if not jobs:
        return res, err
    with ThreadPoolExecutor(max_workers=min(4, len(jobs))) as pool:
        futs = {k: pool.submit(f) for k, f in jobs.items()}
        for k, f in futs.items():
            try:
                res[k] = f.result(timeout=timeout)
            except Exception as e:  # noqa: BLE001 — that one is down, the rest serve
                err[k] = str(e)[:200]
    return res, err


def missing_keys(decl, name=None):
    """The key names a family (or one of its sources) declares and this environment lacks."""
    want = []
    for d in (decl, decl.get(name) if name else None):
        got = d.get("keys") if isinstance(d, dict) else None
        want += [k for k in got if isinstance(k, str)] if isinstance(got, list) else []
    return [k for k in want if not os.environ.get(k)]


class Health(object):
    """Which families are down (a source failed, or a key is missing) and which warn (a need preflight found)."""

    def __init__(self):
        self.down, self.warn, self.lock = {}, {}, threading.Lock()

    def set_down(self, family, why):
        with self.lock:
            self.down[family] = why[:300]

    def set_up(self, family):
        with self.lock:
            self.down.pop(family, None)

    def snapshot(self):
        with self.lock:
            return dict(self.down), {k: list(v) for k, v in self.warn.items()}


class FamilySources(serve.Sources):
    """serve.Sources for one family; a failing source marks only that family down."""

    def __init__(self, family, health, root, runner=None):
        serve.Sources.__init__(self, lambda: serve.sources(family, root), root=root, runner=runner)
        self.family, self.health = family, health

    def get(self, name, params=None):
        need = missing_keys(self.decl_now(), name)
        if need:
            why = "down: needs %s" % ", ".join(need)
            self.health.set_down(self.family, why)
            raise RuntimeError(why)
        try:
            out = serve.Sources.get(self, name, params)
        except (KeyError, serve.BadParameter):
            raise                                        # the request was wrong, the family is not down
        except Exception as e:  # noqa: BLE001
            why = "down: %s" % (str(e).strip() or type(e).__name__)
            self.health.set_down(self.family, why)
            raise RuntimeError(why)
        self.health.set_up(self.family)
        return out


def behind_of(result):
    """PF-19 (behind notice): [{family, path, since, commits, line, buttons}] for each live page pages.list_pages
    found behind its template, by family."""
    out = []
    for f in (result or {}).get("families") or []:
        page = f.get("live") or {}
        if page.get("behind"):
            out.append(dict(page["behind"], family=f["family"], path=page["path"], buttons=page.get("buttons")))
    return out


def declared(root):
    """{family: sources declaration} for every _templates/<family>.sources.json."""
    out = {}
    for f in sorted(glob.glob(os.path.join(root, serve.TEMPLATES, "*.sources.json"))):
        fam = os.path.basename(f)[:-len(".sources.json")]
        try:
            out[fam] = serve.sources(fam, root)
        except (OSError, ValueError):
            out[fam] = {}
    return out


def act_env(root):
    """A direct button's environment: this copy is the workspace, no prompts, and its `git push` goes to main."""
    env = dict(os.environ, AI_WORKSPACE=str(root), GIT_TERMINAL_PROMPT="0")
    n = int(env.get("GIT_CONFIG_COUNT") or 0)
    env.update({"GIT_CONFIG_COUNT": str(n + 1), "GIT_CONFIG_KEY_%d" % n: "remote.origin.push",
                "GIT_CONFIG_VALUE_%d" % n: "HEAD:refs/heads/main"})
    return env


def with_banner(data, why):
    """The page with one plain line at the top of its <body> saying its data is down."""
    text = data.decode("utf-8", "replace")
    line = ('<div data-page-server="down" style="background:#fde8e8;color:#8a1c1c;padding:8px 12px;'
            'font:14px system-ui">This page\'s data is %s. Your other pages still work; ask your Claude.</div>'
            % html.escape(why))
    m = re.search(r"<body(\s[^>]*)?>", text, re.I)
    at = m.end() if m else 0
    return (text[:at] + line + text[at:]).encode("utf-8")


class ServerStatus(object):
    """/status for the page server: serve.Status's shape ({"behind", "checked"}) plus "server", from the sync's
    last record. Runs no git per request."""

    def __init__(self, srv):
        self.srv = srv

    def get(self):
        info = self.srv.info()
        return {"behind": info["behind"], "checked": info["synced_at"] or now_z(), "server": info}


class PageServer(object):
    """One server for all of one person's pages, from root (the private copy)."""

    def __init__(self, state, root, person, act_person=None, why=None, sync=None, lock=None, clock=time.time,
                 act_runner=None, job_timeout=jobs.TIMEOUT, port=None, git_timeout=GIT_TIMEOUT, git_call=None,
                 token=None):
        self.state, self.root, self.person, self.clock = str(state), str(root), person, clock
        self.port = port                                # PF-16 (fixed port): the port `run` bound, None in tests
        self.git_timeout, self.git_call = git_timeout, git_call
        self.git_stuck = None                           # PF-16c: the last listing's "git did not answer …", or None
        self.pages_behind = []                          # PF-19 (behind notice): the last listing's behind live pages
        self.act_person, self.why = act_person, why
        # PF-14e (token survives): kept in <state>/token across restarts; put into each page it serves
        self.token, self.token_why = (token, None) if token else kept_token(self.state)
        self.lock = lock or StateLock(state)
        self.sync = sync
        self.health = Health()
        self.act_runner = act_runner or self._act_run
        self._src, self._act, self._mk = {}, {}, threading.Lock()
        self.status = ServerStatus(self)
        self.jobs = jobs.Jobs(self.root, gate=self.lock, env=act_env(self.root), timeout=job_timeout,
                              on_end=self.job_end, clock=clock)
        self._click = threading.local()                 # PF-14c (click lock): this request's "pending" why, if any
        self._pend = threading.Lock()
        got = read_json(os.path.join(self.state, PENDING_FILE), {})
        self.pending = {k: v for k, v in got.items() if isinstance(v, str)} if isinstance(got, dict) else {}
        # PF-26 (page-family cleanup): set after the first sync round (at once with no sync); see starting()
        self.loaded = threading.Event()
        if self.sync:
            self.sync.hold = self.jobs.running
            self.sync.before = self.commit_pending
        else:
            self.loaded.set()
        for fam, decl in declared(self.root).items():
            problems = serve.preflight(decl)
            if problems:
                self.health.warn[fam] = problems

    def _act_run(self, argv):
        try:
            p = subprocess.run(argv, cwd=self.root, capture_output=True, text=True, timeout=120,
                               stdin=subprocess.DEVNULL, env=act_env(self.root))
        except subprocess.TimeoutExpired:
            return 1, "stopped: no answer in 120 s"
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    # ------------------------------------------------------------------ PF-14c (click lock)
    def _watched(self, argv):
        """A quick button's command, run by Act.run with the lock held. When it fails but wrote files in the copy, it
        is "saved — commit pending (<why>)": the files are kept for the next sync's commit and the answer is ok."""
        self._click.pending = None
        t0 = time.time()
        code, out = self.act_runner(argv)
        if not code:
            return code, out
        wrote = self.changed(t0)
        if not wrote:
            return code, out                             # nothing written: it failed
        why = commit_why(out)
        with self._pend:
            for p in wrote:
                self.pending[p] = why
            self.save_pending()
        self._click.pending = why
        return 0, "%s\n%s" % ((out or "").rstrip(), pending_line(why))   # last: Act.run keeps the last lines

    def changed(self, since=None):
        """The copy's changed or untracked files (paths under the copy), only those written at or after `since` when
        given; one git status that takes no lock. [] when git cannot say."""
        try:
            got = reading_call(["git", "-C", self.root, "status", "--porcelain", "-z", "--untracked-files=all"],
                               None, self.git_timeout)
        except (OSError, ValueError, subprocess.SubprocessError):
            return []
        if not got or got[0]:
            return []
        out, items = [], got[1].split("\0")
        i = 0
        while i < len(items):
            x = items[i]
            i += 1
            if len(x) < 4:
                continue
            if x[0] in "RC":
                i += 1                                   # a rename's old name follows; the new one is the file
            rel = x[3:]
            try:
                t = os.stat(os.path.join(self.root, rel)).st_mtime
            except OSError:
                continue
            if since is None or t >= since - 1.0:
                out.append(rel)
        return sorted(set(out))

    def save_pending(self):
        try:
            write_json(os.path.join(self.state, PENDING_FILE), self.pending)
        except OSError:
            pass

    def commit_pending(self):
        """What clicks saved but could not commit, in one commit; the sync calls it first, lock held. The files a
        later commit already carried are dropped from the list. Returns what it said, or None."""
        with self._pend:
            want = dict(self.pending)
        if not want:
            return None
        still = set(self.changed())
        keep = sorted(p for p in want if p in still)
        if keep:
            copy = self.sync.copy if self.sync else Copy(self.root)
            code, out = copy.git("add", "--", *keep)
            if not code:
                whys = sorted(set(want[p] for p in keep))
                code, out = copy.git("commit", "-q", "-m", "page server: %s saved by clicks, commit pending (%s)"
                                     % (plural(len(keep), "file"), "; ".join(whys)[:200]), "--", *keep)
            if code:
                return "pending clicks not committed yet: %s" % _last(out)
        with self._pend:
            for p in want:
                if self.pending.get(p) == want[p]:
                    self.pending.pop(p)
            self.save_pending()
        return "committed %s clicks had saved" % plural(len(keep), "file") if keep else None

    def sources(self, family):
        with self._mk:
            if family not in self._src:
                self._src[family] = FamilySources(family, self.health, self.root)
            return self._src[family]

    def act(self, family):
        with self._mk:
            if family not in self._act:
                a = serve.Act(family, self.root, self.act_person, self.why, token=self.token, runner=self._watched,
                              jobs_=self.jobs)
                a.lock = self.lock                       # the copy's one git writer: buttons and the sync take turns
                self._act[family] = a
            return self._act[family]

    def starting(self):
        """PF-26 (page-family cleanup): true before the first sync round has finished (a self-restart on new kit
        code serves at once, its copy still settling), and from a pull that changed the kit until `run` exits."""
        return not self.loaded.is_set() or bool(self.sync and self.sync.restart.is_set())

    def declaring(self, name):
        return [f for f, d in declared(self.root).items()
                if isinstance(d.get(name), dict) and (d[name].get("argv") or d[name].get("watch"))]

    def all_runs(self):
        prefixes = sorted(set(p for d in declared(self.root).values() for p in serve.runs_prefixes(d)))
        return serve.Sources({"runs": prefixes}, root=self.root)

    # ------------------------------------------------------------------ state, clicks
    def info(self):
        last = self.sync.last if self.sync else {}
        down, warn = self.health.snapshot()
        return {"person": self.person, "port": self.port, "synced_at": now_z(last["at"]) if last.get("at") else None,
                "sync_ok": last.get("ok"), "sync_said": last.get("said", "no sync in this server"),
                "good_at": now_z(last["good_at"]) if last.get("good_at") else None,
                "not_pushed": last.get("ahead") or 0, "behind": last.get("behind"), "down": down, "warn": warn,
                "git": self.git_stuck, "pages_behind": list(self.pages_behind)}

    def save(self):
        try:
            write_json(os.path.join(self.state, "state.json"), self.info())
        except OSError:
            pass

    def click(self, page, body, res, extra=None):
        n = body.get("n") if isinstance(body, dict) else None
        line = {"at": now_z(self.clock()), "page": page, "n": n, "ok": bool(res.get("ok")),
                "said": (res.get("said") or "")[:400]}
        line.update(extra or {})
        with open(os.path.join(self.state, "clicks.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(line) + "\n")

    def clicks(self, k=CLICKS_SHOWN):
        try:
            with open(os.path.join(self.state, "clicks.jsonl"), encoding="utf-8") as fh:
                lines = fh.readlines()[-k:]
        except OSError:
            return []
        out = []
        for x in lines:
            try:
                out.append(json.loads(x))
            except ValueError:
                pass
        return list(reversed(out))

    def job_end(self, job, state):
        """PF-13b (slow buttons): a job has ended — push what it left, then its one click line. Returns the line the
        job's said gets (the push), or None."""
        ahead, said = self.after_act()
        page = job.page or job.family
        text = "\n".join(x for x in (job.said(), said) if x)
        extra = {"job": job.id, "item": job.item, "state": state}
        if state != "done":
            extra["ask"] = "ask your Claude to finish it: " + job.ask
        try:
            self.click(page, {"n": job.n}, {"ok": state == "done", "said": text}, extra)
        except OSError:
            pass
        return said or None

    def after_act(self):
        """(ahead, said): push right after a click whatever the button's command left unpushed."""
        if not self.sync:
            return 0, ""
        with self.lock:
            if not self.sync.copy.ahead():
                return 0, ""
            ok, said = self.sync.push()
            ahead = self.sync.copy.ahead() or 0
            self.sync.last["ahead"] = ahead
        self.save()
        return ahead, ("page server: shared" if ok and not ahead else "page server: %s · %s" % (said, not_pushed(ahead)))

    def loop(self, stop, every=SYNC_EVERY):
        """The sync thread: once now, then every `every` s; sets `stop` when the kit changed (run then exits)."""
        while not stop.is_set():
            if self.sync:
                try:
                    self.sync.once()
                except Exception as e:  # noqa: BLE001 — said on the index, tried again next round
                    self.sync.last.update({"at": self.clock(), "ok": False, "said": "sync failed: %s" % e})
                self.save()
                self.loaded.set()
                if self.sync.restart.is_set():
                    stop.set()
                    return
            stop.wait(every)

    # ------------------------------------------------------------------ the index
    def status_line(self, info=None):
        info = info or self.info()
        bits = []
        if self.port:                                   # PF-16 (fixed port): the address, and a record that moved
            fixed, _ = record_port(self.root, self.person)
            bits.append("your address: http://localhost:%d/" % self.port + (
                "" if fixed == self.port else
                " — your record now says %s; say 'restart my page server' to move there" % (
                    ":%d" % fixed if fixed else "no %s" % PORT_FIELD)))
        if info["synced_at"]:
            ago = max(0, int(self.clock() - (self.sync.last["at"] if self.sync else self.clock())))
            bits.append("synced %d s ago" % ago if info["sync_ok"] else "sync: %s" % info["sync_said"])
            if not info["sync_ok"]:
                bits.append("last good sync %s" % (info["good_at"] or "never"))
        else:
            bits.append(info["sync_said"])
        bits.append(not_pushed(info["not_pushed"]) if info["not_pushed"] else "0 not pushed")
        if info["behind"]:
            bits.append("%d behind origin/main" % info["behind"])
        if info.get("git"):                             # PF-16c (Windows git hang): the call that did not answer
            bits.append(info["git"])
        down = info["down"]
        bits.append("down: " + "; ".join("%s (%s)" % (f, w) for f, w in sorted(down.items())) if down
                    else "every family up")
        bits.extend(b["line"] for b in info.get("pages_behind") or [])   # PF-19 (behind notice)
        return " · ".join(bits)

    def gathered(self):
        """(results, errors, info): the page list and every family's health, each in its own thread; what the
        built-in index and /data/home are made from."""
        def health(fam):
            fam_decl = declared(self.root).get(fam, {})
            need = missing_keys(fam_decl)
            if need:
                raise RuntimeError("down: needs %s" % ", ".join(need))
            return serve.preflight(fam_decl)
        git = GitRunner(self.git_timeout, self.git_call)   # PF-16c (Windows git hang): never a hang, said when stuck
        jobs = {"pages": lambda: pages.list_pages(person=self.person, root=self.root, runner=git)}
        for fam in declared(self.root):
            jobs["family:" + fam] = (lambda f: lambda: health(f))(fam)
        res, err = gather(jobs)
        self.git_stuck = git.stuck
        if "pages" in res:
            self.pages_behind = behind_of(res["pages"])
        for k, why in err.items():
            if k.startswith("family:"):
                self.health.set_down(k[len("family:"):], why)
        return res, err, self.info()

    def home_data(self):
        """PF-17 (home page family): GET /data/home, what the home template reads."""
        res, err, info = self.gathered()
        got = "pages" in res
        return {"person": self.person, "port": self.port, "status": info, "status_line": self.status_line(info),
                "down": info["down"], "warn": info["warn"], "pages": res.get("pages"),
                "pages_error": None if got else err.get("pages", "no answer"), "clicks": self.clicks(),
                "plain": PLAIN, "pages_behind": info["pages_behind"]}

    def home_page(self):
        """(file, path under viewers/) of the page / serves: the person's live home page, else the family's
        template; (None, None) when this copy has neither."""
        for rel in ("%s/%s.html" % (self.person, HOME), "_templates/%s.html" % HOME):
            f = serve.safe_file(self.root, serve.VIEWERS, rel)
            if f:
                return f, rel
        return None, None

    def index_html(self):
        res, err, info = self.gathered()
        down, warn = info["down"], info["warn"]
        e = html.escape
        out = ['<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>%s\'s pages</title>\n'
               '<style>body{font:15px/1.5 system-ui;margin:24px auto;max-width:880px;padding:0 16px}'
               '.st{background:#f4f4f2;padding:8px 12px;border-radius:6px}.down{color:#8a1c1c}.warn{color:#8a5a00}'
               'td{padding:2px 10px 2px 0;vertical-align:top}</style>\n</head>\n<body>' % e(self.person),
               '<h1>%s\'s pages</h1>' % e(self.person[:1].upper() + self.person[1:]),
               '<p class="st" id="status">%s</p>' % e(self.status_line(info))]
        result = res.get("pages")
        if result is None:
            out.append('<p class="down">your page list is down: %s</p>' % e(err.get("pages", "no answer")))
            result = {"families": [], "other": [], "refused": None}
        if result.get("refused"):
            out.append('<p class="down">%s</p>' % e(result["refused"]))

        def item(path, label, fam, extra):
            rel = path[len(serve.VIEWERS) + 1:] if path.startswith(serve.VIEWERS + "/") else path
            bits = [extra] if extra else []
            if fam in down:
                bits.append('<span class="down">%s</span>' % e(down[fam]))
            for w in warn.get(fam, []):
                bits.append('<span class="warn">warning: %s</span>' % e(w))
            return '<li><a href="/v/%s">%s</a> · %s%s</li>' % (
                e(rel, quote=True), e(label), e(rel), "".join(" · " + b for b in bits))
        lives = [item(f["live"]["path"], f["family"], f["family"], e(f["live"].get("save", "")))
                 for f in result["families"] if f.get("live")]
        drafts = [item(d["path"], "%s · %s" % (f["family"], d["name"]), f["family"], e(d.get("save", "")))
                  for f in result["families"] for d in f.get("drafts", [])]
        others = [item(p["path"], os.path.basename(p["path"]), serve.family_of(p["path"]), e(p.get("save", "")))
                  for p in result.get("other", [])]
        for title, rows in (("Live pages", lives), ("Drafts", drafts), ("Other pages", others)):
            if rows:
                out.append("<h2>%s</h2>\n<ul>\n%s\n</ul>" % (title, "\n".join(rows)))
        if not (lives or drafts or others):
            out.append("<p>No pages yet: ask your Claude to make a draft of a page.</p>")
        clicks = self.clicks()
        out.append("<h2>Recent clicks</h2>")
        if clicks:
            out.append("<table>%s</table>" % "".join(
                "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    e(c.get("at") or ""), e(str(c.get("page") or "")), e(str(c.get("n") or "")),
                    e(click_word(c)) if click_word(c) != "failed" else '<span class="down">failed</span>',
                    e(c.get("said") or ""))
                for c in clicks))
        else:
            out.append("<p>No clicks yet.</p>")
        out.append("<p><small>Pages as on origin/main, through the page server's own copy: a draft you have not "
                   "pushed shows here about a minute after you push it.</small></p>\n</body>\n</html>\n")
        return "\n".join(out)

    # ------------------------------------------------------------------ the routes
    def handler(self):
        srv = self

        class H(serve.KitHandler):
            root, status = srv.root, srv.status
            refused = False                               # PF-14d (page family check): this /act was another page's

            def page_of(self):
                """The page (path under viewers/) this request came from, by its Referer on this server."""
                u = urlparse(self.headers.get("Referer") or "")
                if not serve.allowed_host(u.netloc, self.server.server_address[1]):
                    return None
                p = unquote(u.path)
                if p == "/":                              # PF-17 (home page family): the page / serves
                    return srv.home_page()[1]
                for pre in ("/v/", "/p/"):
                    if p.startswith(pre) and p.endswith(".html"):
                        return p[len(pre):]
                return None

            def kit_sources(self):
                page = self.page_of()
                if page:
                    return srv.sources(serve.family_of(page))
                route = urlparse(self.path).path
                for pre in ("/data/", "/stamp/"):
                    if route.startswith(pre):
                        fams = srv.declaring(route[len(pre):])
                        if len(fams) == 1:
                            return srv.sources(fams[0])
                if route.startswith("/runs/"):
                    return srv.all_runs()
                return serve.Sources({}, root=srv.root)

            def kit_act(self, body):
                if not isinstance(body, dict):
                    raise serve.Refused(400, "the body must be a JSON object")
                fam = body.get("family")
                if not isinstance(fam, str) or not serve.FAMILY.fullmatch(fam):
                    raise serve.Refused(400, "bad family")
                page = self.page_of()
                if urlparse(self.path).path == "/act":    # PF-14d: only the asking page's own family's buttons
                    own = serve.family_of(page) if page else None
                    if fam != own:
                        self.refused = True
                        raise serve.Refused(403, "this page's buttons are %s's" % own if own else NO_PAGE)
                body[serve.PAGE_KEY] = page               # PF-13b: the page a job's click line names, never the body's
                return srv.act(fam)

            def kit_token(self):
                return srv.token

            def kit_starting(self):
                return srv.starting()

            def kit_jobs(self):
                return srv.jobs

            def kit_index(self):
                """PF-17 (home page family): the home page, the strip injected above it."""
                f, _ = srv.home_page()
                data = None
                if f:
                    try:
                        with open(f, "rb") as fh:
                            data = self.kit_page(f, fh.read())
                    except OSError:
                        data = None
                if data is None:
                    data = srv.index_html().encode("utf-8")   # gathers: its status line is fresh
                else:
                    srv.gathered()                        # PF-19 (behind notice): the strip names behind pages now
                self._send(200, with_strip(data, srv.status_line()), "text/html; charset=utf-8")

            def kit_page(self, path, data):
                data = serve.with_token(data, srv.token)
                why = srv.health.snapshot()[0].get(serve.family_of(path))
                return with_banner(data, why) if why else data

            def kit_acted(self, body, code, res):
                if code == 202:                          # PF-13b: a job started; its one line is written when it ends
                    return
                pending, srv._click.pending = getattr(srv._click, "pending", None), None
                if code == 200:
                    ahead, said = srv.after_act()
                    if said:
                        res["said"] = ((res.get("said") or "") + "\n" + said).strip()
                extra = {}
                if pending and code == 200:               # PF-14c (click lock): saved, the next sync commits it
                    res["pending"] = extra["pending"] = pending
                    line = pending_line(pending)          # first, so the click line's 400 characters keep it
                    res["said"] = (line + "\n" + (res.get("said") or "").replace(line, "")).strip()
                if self.refused or res.get("stale_actions"):   # PF-14d (page family check), PF-19: nothing ran
                    extra["refused"] = True
                page = self.page_of() or (body.get("family") if isinstance(body, dict) else None)
                try:
                    srv.click(page, body, res, extra or None)
                except OSError:
                    pass

            def do_GET(self):
                route = urlparse(self.path).path
                if route in (PLAIN, DATA_HOME):           # PF-17 (home page family): the server's own two
                    if self._foreign():
                        return
                    if route == PLAIN:
                        return self._send(200, srv.index_html(), "text/html; charset=utf-8")
                    return self._json(200, srv.home_data())
                if route.startswith("/v/"):
                    if self._foreign():
                        return
                    f = serve.safe_file(self.root, serve.VIEWERS, route[len("/v/"):])
                    return self._file(f, page=True) if f else self._send(404, "not here")
                return serve.KitHandler.do_GET(self)
        return H


class Server(ThreadingHTTPServer):
    """Finishes the requests in flight before it closes (run's restart on new code). No SO_REUSEADDR on Windows,
    where it would let a second server bind a port already in use."""
    daemon_threads = False
    block_on_close = True
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        """PF-16c (Windows git hang): on Windows the listening socket is never inherited by a child."""
        ThreadingHTTPServer.server_bind(self)
        if windows():
            self.socket.set_inheritable(False)


# ---------------------------------------------------------------------------------------------- the verbs

def say(*lines):
    for x in lines:
        print(x)


def utf8_console(platform=None, streams=None):
    """PF-16b (Windows port check): at start-up on Windows, stdout and stderr write utf-8 with errors replaced, so the
    em dashes survive a cp1252 console (and supervise's server.log stays one encoding). Elsewhere nothing changes."""
    if not windows(platform):
        return
    for s in (sys.stdout, sys.stderr) if streams is None else streams:
        fix = getattr(s, "reconfigure", None)             # None under pythonw, or a stream with no such method
        if fix:
            try:
                fix(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def refuse_self(verb):
    """Lifted from owner's jobs.py: never switch off the page you are using (here: from one of its own pages)."""
    if os.environ.get(SELF_ENV) == "1":
        say("refused: this is the page server itself — %s from one of its own pages would cut the page you are "
            "using. Ask your Claude in a session: '%s my page server'." % (verb, "turn off" if verb == "off" else verb))
        return True
    return False


def whoami(repo):
    try:
        return people.whoami(str(repo)), None
    except people.Refused as e:
        return None, str(e)


def windows(platform=None):
    """The one platform test for the port check, PF-16b (Windows port check): `platform` for tests, else this
    machine's."""
    return (platform or sys.platform) == "win32"


def port_free(port, platform=None, runner=None):
    """True when the server could bind the port now: SO_REUSEADDR as the server sets it, so a port the server just
    left (TIME_WAIT after off or restart) counts as free and the address stays the same. Not on Windows (see
    Server)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if Server.allow_reuse_address:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
    except OSError:
        return False
    finally:
        s.close()
    return not listening(port, platform, runner)


WIN_HOSTS = ("127.0.0.1", "0.0.0.0", "::1", "::")       # the addresses a holder of our 127.0.0.1 port listens on


def win_listeners(port, runner=None):
    """(pids, None) of netstat -ano's LISTENING rows on exactly `port` at 127.0.0.1, 0.0.0.0, ::1 or [::] — the TCP
    table, then TCPv6 when TCP has none — or ([], why) when netstat could not be read. PF-16b (Windows port
    check)."""
    runner = runner or run_cmd
    for proto in ("TCP", "TCPv6"):
        code, out = runner(["netstat", "-ano", "-p", proto])
        if code != 0:
            return [], "netstat -ano -p %s failed (%s)" % (proto, _last(out))
        pids = []
        for line in (out or "").splitlines():
            f = line.split()                              # Proto  Local  Foreign  State  PID
            if len(f) != 5 or f[0].upper() != "TCP" or f[3].upper() != "LISTENING" or not f[4].isdigit():
                continue
            host, _, p = f[1].rpartition(":")
            if p == str(port) and host.strip("[]") in WIN_HOSTS:
                pids.append(int(f[4]))
        if pids:
            return pids, None
    return [], None


def listening(port, platform=None, runner=None):
    """True when something already answers on the port at 127.0.0.1 or ::1. PF-16 (fixed port): on macOS a holder
    on 0.0.0.0 lets SO_REUSEADDR bind 127.0.0.1 beside it, so the bind alone would call a held port free. PF-16b
    (Windows port check): on Windows the listener table says, never a connect (see win_listeners); a table that
    cannot be read counts as held, and the refusal names why."""
    if windows(platform):
        pids, why = win_listeners(port, runner)
        return bool(pids or why)
    for fam, addr in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            s = socket.socket(fam, socket.SOCK_STREAM)
        except OSError:
            continue                                      # no IPv6 here
        try:
            s.settimeout(0.5)
            s.connect((addr, port))
            return True
        except socket.timeout:
            return True                                   # on loopback: a listener too busy to answer, still held
        except OSError:
            pass
        finally:
            s.close()
    return False


def record_of(person):
    return "%s/%s/identity.json" % (people.PEOPLE, person)


def record_port(repo, person):
    """(port, None) or (None, why): the person's one fixed page-server port, PF-16 (fixed port), from
    team/people/<person>/identity.json under the repo. Never a default."""
    doc = read_json(Path(str(repo)) / people.PEOPLE / person / "identity.json")
    if not isinstance(doc, dict):
        return None, "%s is missing or not JSON" % record_of(person)
    port = doc.get(PORT_FIELD)
    if isinstance(port, int) and not isinstance(port, bool) and 1024 <= port <= 65535:
        return port, None
    return None, "%s has no %s%s" % (record_of(person), PORT_FIELD,
                                     "" if port is None else " it can use (%r)" % (port,))


def no_port(person, why):
    return ("refused: %s has no page-server address — %s. Every person has one fixed port (PF-16 (fixed port)); "
            "ask the lead to add %s to your record" % (person, why, PORT_FIELD))


def holder(port, platform=None, runner=None):
    """(pid, command) of what listens on the port, or (None, why it could not be read): lsof + ps on macOS,
    netstat -ano + tasklist on Windows."""
    runner = runner or run_cmd
    if windows(platform):
        pids, why = win_listeners(port, runner)       # PF-16b (Windows port check): LISTENING rows, exact port only
        if not pids:
            return None, why or "netstat -ano named no listener on port %d: no listener found" % port
        code, out = runner(["tasklist", "/FI", "PID eq %d" % pids[0], "/FO", "CSV", "/NH"])
        m = re.match(r'\s*"([^"]+)"', out or "") if code == 0 else None
        return pids[0], (m.group(1) if m else "a process tasklist would not name")
    lsof = shutil.which("lsof") or "/usr/sbin/lsof"      # /usr/sbin is not on every session's PATH
    code, out = runner([lsof, "-nP", "-iTCP:%d" % port, "-sTCP:LISTEN", "-Fpc"])
    pid = next((x[1:] for x in (out or "").splitlines() if x.startswith("p")), None) if code == 0 else None
    if not pid or not pid.isdigit():
        return None, "lsof named no listener (%s)" % _last(out)
    name = next((x[1:] for x in out.splitlines() if x.startswith("c")), "")
    code, cmd = runner([shutil.which("ps") or "/bin/ps", "-o", "command=", "-p", pid])
    cmd = (cmd or "").strip() if code == 0 else ""
    return int(pid), (cmd or name or "a process ps would not name")[:200]


def held(person, port, platform=None, runner=None, refused=True):
    """The line for a fixed port something else holds: the holder named and the fix; `on` and `run` refuse with it
    and take no other port."""
    pid, what = holder(port, platform, runner)
    who = "pid %d: %s" % (pid, what) if pid else "a process this machine would not name (%s)" % what
    line = "port %d — %s's fixed address (%s) — is held by %s. %s%s" % (
        port, person, record_of(person), who, PORT_FIX[:1].upper(), PORT_FIX[1:])
    return ("refused: %s. Nothing was started; the page server never takes another port" % line if refused
            else "held: %s" % line)


def free_soon(port, settle):
    """port_free, given `settle` s for a port the server itself has just let go (restart, a move)."""
    end = time.time() + settle
    while not port_free(port):
        if time.time() >= end:
            return False
        time.sleep(0.2)
    return True


def wait_up(port, person, timeout=10.0):
    """True once GET /status on the port answers as this person's page server, within `timeout` s."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/status" % port, timeout=2) as r:
                if json.loads(r.read().decode()).get("server", {}).get("person") == person:
                    return True
        except Exception:  # noqa: BLE001 — not up yet
            pass
        time.sleep(0.3)
    return False


def live_status(port):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/status" % port, timeout=2) as r:
            return json.loads(r.read().decode()).get("server")
    except Exception:  # noqa: BLE001 — not running
        return None


def ours(port, person):
    """The person's own page server answers on the port now (one quick look, not wait_up's 10 s)."""
    live = live_status(port) if port else None
    return isinstance(live, dict) and live.get("person") == person


def bookmark(port, old):
    """PF-16 (fixed port): the one line that tells a person their address, said when config.json's port moves."""
    url = "http://localhost:%d/" % port
    return ("your address is now %s (was :%d)" % (url, old) if old else
            "your address is %s — fixed, the same on every machine; bookmark it" % url)


def cmd_on(repo, agent, runner, wait, no_open, settle=0.0):
    if not os.path.isfile(agent.python or ""):
        if agent.platform == "win32":
            say("refused: no Python at %r — install Python 3 from python.org (with the py launcher), then ask again"
                % agent.python)
        else:
            say("refused: %s is missing — install Apple's command line tools (xcode-select --install), then ask "
                "again" % PYTHON)
        return 2
    person, why = whoami(repo)
    if not person:
        say("refused: who are you? %s" % why)
        return 2
    port, why = record_port(repo, person)
    if not port:
        say(no_port(person, why))
        return 2
    for fam, decl in sorted(declared(str(repo)).items()):
        for p in serve.preflight(decl):
            say("warning: %s pages: %s" % (fam, p))
    state = state_of(person, platform=agent.platform)
    state.mkdir(parents=True, exist_ok=True)
    copy = state / "repo"
    cfg_path = state / "config.json"
    cfg = read_json(cfg_path, {}) or {}
    old = cfg.get("port") if cfg.get("port") != port else None
    st = agent.status()
    url = "http://127.0.0.1:%d/" % port
    if st["loaded"] and cfg.get("port") and (not old or ours(port, person)):  # on its fixed port already (an old
        if not wait(port, person):                                            # one moved itself at a restart)
            say("failed: the page server is switched on but does not answer at %s — see %s, or say 'restart my "
                "page server'" % (url, state / "server.log"))
            if not port_free(port):
                say(held(person, port, agent.platform, runner))
                return 2
            return 1
        if old:
            write_json(cfg_path, dict(cfg, port=port))
            say(bookmark(port, old))
        say("already on: %s's pages at %s" % (person, url))
        if not no_open:
            agent.show(url)
        return 0
    if not free_soon(port, settle):
        say(held(person, port, agent.platform, runner))
        return 2
    if st["loaded"]:                                      # still on an old address: switch it off, start it here
        say("moving: your page server was started on %s; switching it off to start it on your fixed port :%d"
            % (":%d" % old if old else "no recorded port", port))
        if agent.verb == "supervise":
            with open(str(state / STOP), "w", encoding="utf-8", newline="\n") as fh:
                fh.write("%s move\n" % now_z())
        code, out = agent.stop()
        if code:
            say("failed: %s could not switch off the old server: %s" % (agent.tool, _last(out)))
            return 1
    code, out = runner(["git", "-C", str(repo), "fetch", "-q", "origin"])
    if code:
        say("warning: could not fetch origin (%s); the private copy starts from the last fetched origin/main"
            % _last(out))
    if not (copy / ".git").exists():
        code, out = runner(["git", "-C", str(repo), "worktree", "add", "--detach", str(copy), "origin/main"])
        if code:
            say("failed: could not make the private copy: %s" % _last(out))
            return 1
        say("made the private copy at %s (origin/main)" % copy)
    else:
        say("using the private copy at %s" % copy)
    if not (copy / SELF).is_file():
        say("refused: origin/main has no %s yet — the page server arrives with PF-14 (page server)'s merge" % SELF)
        return 2
    write_json(cfg_path, {"person": person, "repo": str(repo), "port": port, "made": cfg.get("made") or now_z()})
    if cfg.get("port") != port:
        say(bookmark(port, old))
    log = state / "server.log"
    got = agent.install([agent.python, str(copy / SELF), agent.verb], copy, log)
    if got and got[0]:
        say("failed: %s would not take the background task: %s" % (agent.tool, _last(got[1])))
        return 1
    stop = state / STOP
    if stop.exists():
        stop.unlink()                                     # an earlier `off`'s word to supervise
    code, out = agent.start()
    if code:
        say("failed: the background agent did not start: %s" % _last(out))
        return 1
    if not wait(port, person):
        say("failed: switched on, but nothing answered at %s in 10 s — see %s" % (url, log))
        return 1
    say("on: %s's pages at %s (starts at login; say 'turn my page server off' to stop it)" % (person, url))
    if not no_open:
        agent.show(url)
    return 0


def cmd_off(agent, state=None):
    if refuse_self("off"):
        return 2
    if agent.verb == "supervise" and state and Path(state).is_dir():
        with open(str(Path(state) / STOP), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("%s off\n" % now_z())                # a supervise /End leaves alive ends itself
    code, out = agent.stop()
    got = agent.remove()
    if not code and got and got[0]:
        code, out = got
    if code:
        say("failed: %s could not switch it off: %s" % (agent.tool, _last(out)))
        return 1
    say("off: the page server is switched off and will not start at login (its private copy stays; say "
        "'remove my page server' to delete it)")
    return 0


def locate(repo, platform=None):
    """(person, state) for the verbs that only need the folder."""
    person, why = whoami(repo)
    if person:
        return person, state_of(person, platform=platform)
    found = [p for p in caches(platform=platform).glob("*/config.json")]
    if len(found) == 1:
        return found[0].parent.name, found[0].parent
    return None, why


def cmd_remove(repo, agent, runner, force):
    if refuse_self("remove"):
        return 2
    person, state = locate(repo, agent.platform)
    if not person:
        say("refused: who are you? %s" % state)
        return 2
    state = Path(state)
    copy = state / "repo"
    cfg = read_json(state / "config.json", {}) or {}
    if (copy / ".git").exists():
        ahead = Copy(copy, runner).ahead()
        if ahead and not force:
            say("refused: %s — or say 'remove my page server anyway' (remove --force) to drop them" % not_pushed(ahead))
            return 2
    code = cmd_off(agent, state)
    if code:
        return code
    drop_token(state)                                     # PF-14e (token survives): even if the folder stays
    origin_repo = cfg.get("repo") or str(repo)
    if copy.exists():
        code, out = runner(["git", "-C", origin_repo, "worktree", "remove", "--force", str(copy)])
        if code:
            say("warning: git worktree remove: %s" % _last(out))
    runner(["git", "-C", origin_repo, "worktree", "prune"])
    top = caches(platform=agent.platform).resolve()
    if state.exists() and state.resolve().parent == top and state.name == person:
        try:
            shutil.rmtree(str(state))                     # its own folder, nothing else
        except OSError as e:                              # Windows: a file a process still holds open
            say("failed: could not delete %s (%s) — sign out and in again, then say 'remove my page server'"
                % (state, e))
            return 1
    say("removed: the page server's private copy and its folder %s are gone" % state)
    return 0


def cmd_status(repo, agent, runner):
    person, state = locate(repo, agent.platform)
    if not person:
        say("refused: who are you? %s" % state)
        return 2
    state = Path(state)
    cfg = read_json(state / "config.json")
    st = agent.status()
    if not cfg:
        say("page server: not set up (%s). Say 'turn my page server on'." % ("switched on" if st["loaded"] else "off"))
        return 0
    fixed, why = record_port(repo, person)
    # PF-26 (page-family cleanup): while off, the record's port; config.json's is only where `on` last started it
    port, live = (cfg.get("port") if st["loaded"] else fixed or cfg.get("port")), None
    if st["loaded"]:                                    # where it answers: the port `on` started, else the fixed one
        for p in (cfg.get("port"), fixed):
            got = live_status(p) if p else None
            if isinstance(got, dict) and got.get("person") == person:
                port, live = p, got
                break
    port = port or fixed
    url = "http://127.0.0.1:%d/" % port if port else "no address"
    lines = ["page server: %s" % (("on at %s" % url + (" (pid %d)" % st["pid"] if st["pid"] else ""))
                                  if st["loaded"] and live else
                                  ("switched on but not answering at %s — see %s" % (url, state / "server.log"))
                                  if st["loaded"] else "off (port %s%s)" % (port, ", fixed" if port == fixed else ""))]
    if not fixed:                                         # PF-16 (fixed port): the record, and where they disagree
        lines.append(no_port(person, why))
    elif port != fixed:
        lines.append("address: your record says http://localhost:%d/ (%s) but the server %s :%d — say 'restart my "
                     "page server' to move it" % (fixed, record_of(person), "answers on" if live else "was started on",
                                                  port))
    else:
        lines.append("address: http://localhost:%d/ (fixed, %s)" % (fixed, record_of(person)))
    if fixed and st["loaded"] and not live and not port_free(fixed):
        lines.append(held(person, fixed, agent.platform, runner, refused=False))
    info = live or read_json(state / "state.json", {}) or {}
    if info.get("synced_at"):
        lines.append("last sync: %s — %s%s" % (info["synced_at"], "ok" if info.get("sync_ok") else "NOT OK",
                                               "" if info.get("sync_ok") else ": %s (last good %s)" % (
                                                   info.get("sync_said"), info.get("good_at") or "never")))
    else:
        lines.append("last sync: none recorded")
    copy = state / "repo"
    ahead = Copy(copy, runner).ahead() if (copy / ".git").exists() else None
    behind = Copy(copy, runner).count("HEAD..origin/main") if ahead is not None else None
    lines.append("not pushed: %s" % (not_pushed(ahead) if ahead else "0" if ahead == 0
                                     else "unknown (no private copy)"))
    if behind:
        lines.append("behind: %d commits on origin/main the copy has not taken (as of the last fetch)" % behind)
    down = info.get("down") or {}
    lines.append("down: " + "; ".join("%s (%s)" % kv for kv in sorted(down.items())) if down else "down: none")
    for fam, ws in sorted((info.get("warn") or {}).items()):
        for w in ws:
            lines.append("warning: %s pages: %s" % (fam, w))
    clicks = []
    try:
        with open(str(state / "clicks.jsonl"), encoding="utf-8") as fh:
            clicks = [json.loads(x) for x in fh.readlines()[-5:] if x.strip()]
    except (OSError, ValueError):
        pass
    lines.append("last clicks:" if clicks else "last clicks: none")
    for c in reversed(clicks):
        last = ((c.get("said") or "").splitlines() or [""])[-1][:120]
        lines.append("  %s · %s · %s · %s · %s" % (c.get("at"), c.get("page"), c.get("n"),
                                                  click_word(c), last))
    say(*lines)
    return 0


def cmd_push(repo, runner, platform=None):
    person, state = locate(repo, platform)
    if not person:
        say("refused: who are you? %s" % state)
        return 2
    copy = Path(state) / "repo"
    if not (copy / ".git").exists():
        say("refused: there is no page server copy to push from (say 'turn my page server on')")
        return 2
    c = Copy(copy, runner)
    with StateLock(state):
        c.git("fetch", "-q", "origin")
        ahead = c.ahead()
        if not ahead:
            say("nothing to push: the page server has kept nothing back")
            return 0
        ok, said = Sync(c, None).push(PUSH_TRIES)
        left = c.ahead() or 0
    if ok and not left:
        say("pushed: %s from the page server's copy are on origin/main" % plural(ahead, "commit"))
        return 0
    say("failed: %s (%s still kept in the copy)" % (said, plural(left, "commit")))
    return 1


def cmd_run(state=None):
    """What the agent starts: serve every page of the person from the private copy until the kit changes."""
    root = Path(str(paths.repo(HERE))) if state is None else Path(state) / "repo"
    state = Path(state) if state else root.parent
    cfg = read_json(state / "config.json")
    if not cfg or not cfg.get("person"):
        say("refused: %s has no config.json — `run` is what the page server's agent starts; say 'turn my page "
            "server on' to your Claude" % state)
        return 2
    port, why = record_port(root, cfg["person"])          # PF-16 (fixed port): the record, never config.json's port
    if not port:
        say(no_port(cfg["person"], why))
        return 2
    if not port_free(port):
        say(held(cfg["person"], port))
        return 2
    os.environ.update(dict(NO_LOCKS, AI_WORKSPACE=str(root), GIT_TERMINAL_PROMPT="0", **{SELF_ENV: "1"}))
    # PF-14c (click lock): no child's reading git (a data source's `git status`) takes the copy's index.lock
    os.environ.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    act_person, why = serve.kit_person(str(root))   # PF-13 (direct buttons): the server's own identity, once
    lock = StateLock(state)
    sync = Sync(Copy(root), lock)
    srv = PageServer(state, root, cfg["person"], act_person, why, sync=sync, lock=lock, port=port)
    try:
        httpd = Server(("127.0.0.1", port), srv.handler())
    except OSError as e:                              # taken between the look and the bind: still refused
        say("%s (%s)" % (held(cfg["person"], port), e))
        return 2
    say("%s page server for %s at http://127.0.0.1:%d/ from %s; direct buttons %s; key %s" % (
        now_z(), cfg["person"], port, root, "run as %s" % act_person if act_person else "off: %s" % why,
        srv.token_why or "kept across restarts"))           # PF-14e (token survives): never the token itself
    stop, gone = threading.Event(), []
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    threading.Thread(target=srv.loop, args=(stop,), daemon=True).start()
    if os.environ.pop(SUPERVISED_ENV, None) == "1":
        def parent_gone():
            """supervise holds our stdin pipe: EOF = it closed it (off) or it is gone (/End). Watched, on Windows
            never read: see watch_parent, PF-16c (Windows git hang)."""
            try:
                watch_parent(sys.stdin)
            except (OSError, ValueError, AttributeError, ImportError):
                pass
            gone.append(1)
            stop.set()
        threading.Thread(target=parent_gone, daemon=True).start()
    try:
        stop.wait()
    except KeyboardInterrupt:
        pass
    httpd.shutdown()
    httpd.server_close()                              # waits for the requests in flight
    say("%s %s" % (now_z(), "supervise is gone or stopping: exiting" if gone else
                   "the kit changed on origin/main: exiting so the agent starts the new code"))
    return 0


def spawn_run(state, root, log, explicit):
    """`run` as supervise's child: its stdin a pipe supervise holds, its output into server.log, no window."""
    argv = [sys.executable, os.path.abspath(__file__), "run"] + (["--state", str(state)] if explicit else [])
    return subprocess.Popen(argv, cwd=str(root), stdin=subprocess.PIPE, stdout=log, stderr=log,
                            env=dict(os.environ, **{SUPERVISED_ENV: "1"}),
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def end_child(child, timeout=30):
    """Close its stdin (it finishes the requests in flight and exits); terminate it if it has not in `timeout` s."""
    try:
        child.stdin.close()
    except (OSError, AttributeError):
        pass
    try:
        child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        child.terminate()
        child.wait()


def supervise(state, spawn, sleep=time.sleep, clock=time.time, note=say):
    """PF-14b (Windows page server): Windows has no KeepAlive, so this runs `run` (spawn()) and starts it again when
    it exits — 1 s after, doubling to BACKOFF_MAX while it keeps exiting within FAST_EXIT s — until <state>/stop
    exists. Returns the restart delays it used."""
    stop = Path(state) / STOP
    delays, delay, fast = [], 1, False
    while not stop.exists():
        started = clock()
        child = spawn()
        while child.poll() is None:
            if stop.exists():
                note("%s stop file: ending run" % now_z())
                end_child(child)
                return delays
            sleep(1)
        if stop.exists():
            break
        was_fast, fast = fast, clock() - started < FAST_EXIT
        delay = min(BACKOFF_MAX, delay * 2) if fast and was_fast else 1
        delays.append(delay)
        note("%s run exited (%s) after %d s: starting it again in %d s" % (
            now_z(), child.poll(), int(clock() - started), delay))
        for _ in range(delay):
            if stop.exists():
                break
            sleep(1)
    note("%s stop file: supervise ends" % now_z())
    return delays


def cmd_supervise(state=None):
    """What the Windows task starts: `run`, kept running. Its folder and log are worked out here, as cmd_run does."""
    explicit = state is not None
    root = Path(str(paths.repo(HERE))) if state is None else Path(state) / "repo"
    state = Path(state) if state else root.parent
    if not (state / "config.json").is_file():
        say("refused: %s has no config.json — `supervise` is what the page server's task starts; say 'turn my page "
            "server on' to your Claude" % state)
        return 2
    with open(str(state / "server.log"), "a", encoding="utf-8", newline="\n") as log:
        def note(text):
            log.write(text + "\n")
            log.flush()
        note("%s supervise %d: keeping `run` up from %s" % (now_z(), os.getpid(), root))
        supervise(state, lambda: spawn_run(state, root, log, explicit), note=note)
    return 0


def new_token(repo, platform=None):
    """`restart --new-token`, the server off: a new key in its folder, so every page opened before is refused (and
    says to reload). No folder yet: nothing to rotate, `on` mints the first."""
    person, state = locate(repo, platform)
    if not person or not Path(state).is_dir():
        return 0
    _, why = kept_token(state, new=True)
    if why:
        say("failed: no new key — %s; the old one still opens the buttons" % why)
        return 1
    say("new key: every page opened before now must be reloaded for its buttons")
    return 0


def main(argv=None, repo=None, runner=None, platform=None, wait=None, home=None):
    ap = argparse.ArgumentParser(prog="server.py", description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=["on", "off", "status", "restart", "remove", "run", "push", "supervise"])
    ap.add_argument("--no-open", action="store_true", help="on/restart: do not open the index")
    ap.add_argument("--force", action="store_true", help="remove: even with commits not pushed")
    ap.add_argument("--new-token", action="store_true",
                    help="restart: a new key for the buttons; every open page must then be reloaded")
    ap.add_argument("--state", help=argparse.SUPPRESS)
    x = ap.parse_args(argv)
    if x.new_token and x.verb != "restart":
        say("refused: --new-token goes with restart only ('restart my page server with a new key')")
        return 2
    runner = runner or run_cmd
    if x.verb == "run":
        return cmd_run(x.state)
    if x.verb == "supervise":
        return cmd_supervise(x.state)
    repo = Path(str(repo or paths.repo(HERE)))
    if x.verb == "push":
        return cmd_push(repo, runner, platform)
    agent = agent_for(platform, home, runner)
    if agent is None:
        say("refused: " + SUPPORTED % (platform or sys.platform))
        return 2
    wait = wait or wait_up
    if x.verb == "on":
        return cmd_on(repo, agent, runner, wait, x.no_open)
    if x.verb in ("off", "restart"):
        person, state = locate(repo, agent.platform) if agent.verb == "supervise" else (None, None)
        code = cmd_off(agent, state if person else None)
        if code or x.verb == "off":
            return code
        if x.new_token:                                   # PF-14e (token survives): the one rotation besides remove
            code = new_token(repo, agent.platform)
            if code:
                return code
        return cmd_on(repo, agent, runner, wait, x.no_open, settle=FREE_WAIT)
    if x.verb == "remove":
        return cmd_remove(repo, agent, runner, x.force)
    return cmd_status(repo, agent, runner)


if __name__ == "__main__":
    utf8_console()
    sys.exit(main())
