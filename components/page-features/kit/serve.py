#!/usr/bin/env python3
"""PF-4 (page starter kit), the minimal form: a tiny server on a person's own Mac that shows their page with
today's data from their own clone of the repo.

    python3 components/page-features/kit/serve.py <page.html> [--port 8765] [--open]

<page.html> is any page under platform/views/viewers/ (a live page or a draft). It is served at
http://127.0.0.1:<port>/ — localhost only — with five read-only routes beside it (and one write route, POST /act,
below):

    /p/<path>       files under platform/views/viewers/ (the page and its assets)
    /runs/<path>    files under runs/ (the built email, its whole-email picture, a deadlines file), only under
                    the folders the family declares in "runs" (below); a family that declares none gets no /runs/
    /data/<name>    the JSON a component's own command prints, as the family declares it in
                    platform/views/viewers/_templates/<family>.sources.json:
                        {"runs": ["email-production/", …], "needs": ["PIL", "chrome"],
                         "<name>": {"argv": ["components/<component>/<script>.py", "<arg>", ...], "cache_s": 300,
                                    "watch": ["runs/<…>/*/design/email.json", …]}}
                    argv[0] must be a script under components/ (a component's door; never lab code, builder
                    card rule 12). It runs with this Python, from the repo root; its stdout is served as it is,
                    kept for cache_s seconds, or until a file matching a `watch` pattern changes (so a reload right
                    after a change shows it).
                    A source may take arguments by a declared "params" map, {"<key>": "<regex>"}, asked for as
                    /data/<name>?<key>=<value> (PF-4c (emails page loading)): an argv element exactly "{<key>}" is
                    replaced by the value; an undeclared key, a missing declared one, a key given twice or a value
                    not fully matching its regex is 400 and runs nothing. Each set of values is cached on its own.
                    An unknown name is 404, except while the page server is starting (PF-26 (page-family
                    cleanup)): 503 "starting", which each served page's DATA_RETRY script asks again.
    /stamp/<name>   {"name", "stamp": [newest mtime, count]} of a source's `watch` files, running nothing: a page
                    polls this and asks /data only when the stamp moves
    /status         {"behind": N, "checked": …} — commits on the upstream this clone has not pulled, from
                    `git rev-list --count HEAD..@{upstream}` after a `git fetch` at most every 5 minutes; never a
                    pull ("behind": null with "why" when git cannot say)

PF-4b (kit hardening), 2026-10-22: a request whose Host is not 127.0.0.1:<port> or localhost:<port> gets 403 and
touches nothing (a web page using DNS rebinding cannot read the kit); "needs" are checked before serving, and the
kit refuses to start with the fix named.

PF-13 (direct buttons), 2026-10-28, developer's word: one write route, POST /act, for the quick state changes a family
lists in the "direct" table of _templates/<family>.actions.json (emails 26 ok, 28 Done, 47 scheduled; content-queue
12 add, 24 set). Every guard runs before anything does: the Host check; Origin exactly http://127.0.0.1:<port> or
http://localhost:<port> (missing → 403); X-Kit-Token equal to the token minted at start (secrets.token_urlsafe,
held in memory only, put into each page under /p/ as <meta name="kit-token">; another website cannot read it, so
cannot post; PF-14e (token survives): the page server keeps its own in its state folder, and a token present but
wrong is "your page server restarted with a new key — reload the page", a missing one as before); a JSON object of at most 8 KB, {family, n, item, part, field, value}, never a command line; the
family the kit serves; n in that family's table ("ask your Claude: this button is not direct" otherwise); every
value against a pattern. The kit builds the argv itself, no shell: requests/ask get ONE request line in their own
grammar in a temp file (deleted after), cq gets its verb and fields and never --root (shadow only). The person is
the kit's own identity, run_kit.people.whoami once at start, never the body. Answer {ok, said}. Model calls,
rebuilds, spends and sends are never direct (57 the Go, 31 move, 32 remove stay with the person's Claude).
PF-13c (Outlier queue buttons), 2026-10-28, developer's word: a cq entry may list "verbs" (remove, restore; the body's
field names which, no value) and a set entry may give "values", {field: regex} each value must fully match;
requested_stage is direct only with its pattern (the page's stage list), so it records a stage and starts nothing.
PF-18b (review marks), 2026-10-29, developer's word: a "review" entry (dev-queue 20-23) names its mark (understood,
question, issue, resolve); item must be a card id; the kit runs dev_queue.py mark <card> <mark> --by <person>, plus
--note=<value> (one line, at most 200 characters) or, for resolve, --of=<value> (a person id): one review record
through the review module, nothing else. DQ-8 (act panel): the mark "done" (dev-queue 26) takes a follow-up's task id
as item and runs dev_queue.py mark <task> done --by <person> [--note=<value>], which ticks it done through dev_issues.py.

PF-19 (behind notice), 2026-10-29, developer's word: a live page whose family's actions.json changed after it went live
(live.stale_actions: the blob its last live.jsonl line recorded, against the file now) runs no direct button: /act
answers 403 "ask your Claude: <why>" with stale_actions: true before anything else is read, and act.js's fallback
copies the page's request for Claude and shows that why — until the page is caught up or made live again. A draft,
a template, or a page that went live before PF-19 recorded nothing and keeps its direct buttons.

Minimal by email_lead's choice (2026-10-21, owner of page-features): data comes from the person's own working tree
(they `git pull`, their Claude does at the start of each session), not `git show origin/main`, so a person sees
their own changes at once; pictures are the files a component already wrote under runs/, not Drive thumbnails
(the thumbnail lift in gdrive-creator stays on the PF-4 card). Every button but the direct ones writes a request
for the person's own Claude.

PF-14 (page server), 2026-10-28: the routes live in KitHandler; handler() binds them to one page, exactly as before,
and kit/server.py subclasses KitHandler to host all of a person's pages on one always-on server.

PF-13b (slow buttons), 2026-10-28, developer's word ("Make all buttons work"): every entry of the direct table has a
`kind` — quick (PF-13's: run while the page waits; an entry with no kind is quick), job (slow, free) or confirm-job
(it calls a model or is otherwise in the money group). A job or confirm-job /act passes every guard above, then:
the email (item) already has a job → 409 "already working on <item>"; a confirm-job body without "confirmed": true
→ 428 {confirm: what runs, what it costs, the models the adapter names in components/models/models.json} and nothing
runs; else the command starts in the background (kit/jobs.py) and the answer is 202 {job, ask} at once. GET
/job/<id> answers its state (queued · running · done · failed), the last lines said, started, ended, and "ask": the
exact request line to paste in Claude if it fails. A 20 min limit per job. An entry's own keys say what it takes:
"part" one|whole, "value" a regex, "note" a length (up to 2,000 characters, newlines kept: the request file
carries further lines tab-continued, kit/requests.py reads them back; never argv), "picture" (a picture number),
"edits" (the words JSON). POST /upload (the same Host, Origin and token guards; at most 15 MB; png, jpg or webp by
their first bytes, never by name) saves a file the page picked into that email's run folder under the entry's
"into" with a name the kit makes, and answers {path}; a "run": "own" /act takes only a path this kit saved for that
email, so no path from the browser ever reaches a command.

The kit itself writes nothing in the repo but uploads (git fetch's own writes in .git, through /status, are one
exception; a direct button's command writes what it always writes, its request file sits in the system temp folder
and is deleted; an upload lands in the email's run folder, under runs/, where pictures are gitignored). Stdlib
only, Python 3.9.
"""
import argparse
import datetime
import glob
import hmac
import importlib.util
import json
import mimetypes
import os
import re
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(HERE)), "run-kit"))  # appended, never ahead
from run_kit import paths  # noqa: E402  the one workspace locator (builder card rule 3)
from run_kit import people  # noqa: E402  the one person resolver, LD-77 (one person resolver)
if HERE not in sys.path:
    sys.path.append(HERE)
import jobs  # noqa: E402  PF-13b (slow buttons), same folder: background jobs
if os.path.dirname(HERE) not in sys.path:
    sys.path.append(os.path.dirname(HERE))
import live  # noqa: E402  PF-7 (working versions), same component: stale_actions, PF-19 (behind notice)

ROOT = str(paths.repo(HERE))
VIEWERS = os.path.join("platform", "views", "viewers")
TEMPLATES = os.path.join(VIEWERS, "_templates")
SERVE_EXT = {".html", ".css", ".js", ".json", ".jsonl", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
CHROME_APP = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def allowed_host(host, port):
    """True only for the kit's own names: 127.0.0.1:<port> and localhost:<port>. A missing Host is refused."""
    return (host or "").strip().lower() in ("127.0.0.1:%d" % port, "localhost:%d" % port)


def runs_prefixes(decl):
    """The runs/ folders a family declares, each as "<folder>/"; anything with .. or a leading / is dropped."""
    got = decl.get("runs") if isinstance(decl, dict) else None
    if not isinstance(got, list):
        return []
    out = []
    for p in got:
        if not isinstance(p, str):
            continue
        p = p.strip().replace("\\", "/")
        if not p or ".." in p or p.startswith("/"):
            continue
        out.append(p.rstrip("/") + "/")
    return out


def preflight(decl):
    """What the family's commands need and this Mac lacks, each with its fix named. [] = ready."""
    needs = decl.get("needs", []) if isinstance(decl, dict) else []
    if not isinstance(needs, list):
        return ["needs must be a list of names, e.g. [\"PIL\", \"chrome\"]"]
    problems = []
    for n in needs:
        if n == "PIL":
            if importlib.util.find_spec("PIL") is None:
                problems.append("Pillow is missing for %s: run the kit with /usr/bin/python3, or %s -m pip install "
                                "--user Pillow" % (sys.executable, sys.executable))
        elif n == "chrome":
            bins = [b for b in (os.environ.get("CHROME_BIN"), CHROME_APP) if b]
            if not any(os.path.isfile(b) and os.access(b, os.X_OK) for b in bins):
                problems.append("Google Chrome is missing: install it, or set CHROME_BIN")
        else:
            problems.append("unknown need %s" % n)
    return problems


def family_of(page):
    """emails from …/emails.html or …/drafts/emails--final.html."""
    return os.path.basename(page)[:-len(".html")].split("--")[0]


def sources(family, root=ROOT):
    f = os.path.join(root, TEMPLATES, "%s.sources.json" % family)
    if not os.path.isfile(f):
        return {}
    with open(f, encoding="utf-8") as fh:
        return json.load(fh)


def safe_file(root, base, rel):
    """The file at base/rel when it is a servable file inside base, else None (no .., no other folders)."""
    top = os.path.realpath(os.path.join(root, base))
    path = os.path.realpath(os.path.join(top, unquote(rel)))
    if not path.startswith(top + os.sep) or not os.path.isfile(path):
        return None
    return path if os.path.splitext(path)[1].lower() in SERVE_EXT else None


class BadParameter(ValueError):
    """A /data request's query does not fit the source's declared params; answered 400, nothing runs."""


class Sources(object):
    """Runs a declared component command and keeps its output for cache_s seconds."""

    def __init__(self, decl, root=ROOT, runner=None, clock=time.time):
        self.decl, self.root, self.clock = decl, root, clock
        self.runner = runner or self._run
        self.cache, self.lock = {}, threading.Lock()

    def _run(self, argv):
        p = subprocess.run([sys.executable] + argv, cwd=self.root, capture_output=True, text=True, timeout=600)
        if p.returncode:
            raise RuntimeError((p.stderr or p.stdout).strip()[-400:] or "exit %d" % p.returncode)
        return p.stdout

    def decl_now(self):
        return self.decl() if callable(self.decl) else self.decl   # a loader re-reads the family's file each time

    def wants_viewer(self, name):
        """A declared source with "viewer": true gets the page server's person as `viewer` (2026-11-06: the content
        board lets only owner, designer or email_lead move an email off editor's rule)."""
        d = self.decl_now().get(name)
        return isinstance(d, dict) and d.get("viewer") is True

    def stamp(self, name):
        """The watch stamp of a declared source, [newest mtime, count]; runs nothing."""
        d = self.decl_now().get(name)
        if not isinstance(d, dict) or not d.get("watch"):
            raise KeyError(name)
        return list(self._stamp(d["watch"]))

    def get(self, name, params=None):
        decl = self.decl_now()
        d = decl.get(name)
        if not isinstance(d, dict) or not d.get("argv"):
            raise KeyError(name)
        params = dict(params or {})
        argv = self._bind(d, params)
        script = os.path.normpath(d["argv"][0])   # the declared script, never a value a request filled in
        if not script.startswith("components" + os.sep) or not os.path.isfile(os.path.join(self.root, script)):
            raise PermissionError("%s is not a component's script" % d["argv"][0])
        key = (name, tuple(sorted(params.items())))
        with self.lock:
            stamp = self._stamp(d.get("watch") or [])
            hit = self.cache.get(key)
            if hit and hit[2] == stamp and self.clock() - hit[0] < float(d.get("cache_s", 60)):
                return hit[1]
            out = self.runner(argv)
            json.loads(out)                       # serve JSON only
            self.cache[key] = (self.clock(), out, stamp)
            return out

    @staticmethod
    def _bind(d, params):
        """The argv with each element that is exactly "{key}" replaced by its value (PF-4c (emails page loading)).
        A key the source does not declare, a declared key missing, or a value not fully matching its regex is
        refused before anything runs."""
        declared = d.get("params") or {}
        if not isinstance(declared, dict):
            raise RuntimeError("params must be a map of name to regex")
        for k in sorted(params):
            if k not in declared:
                raise BadParameter("bad parameter %s" % k)
        for k in sorted(declared):
            v = params.get(k)
            if not isinstance(v, str) or not re.fullmatch(declared[k], v):
                raise BadParameter("bad parameter %s" % k)
        whole = {"{%s}" % k: v for k, v in params.items()}
        return [whole.get(a, a) if isinstance(a, str) else a for a in d["argv"]]

    def _stamp(self, patterns):
        """The newest change time among the watched files, and how many there are."""
        files = [f for p in patterns for f in glob.glob(os.path.join(self.root, p))]
        return (max([os.path.getmtime(f) for f in files] or [0]), len(files))


class Status(object):
    """How many upstream commits this clone has not pulled. Fetches at most once per `every` seconds; never pulls."""

    def __init__(self, root=ROOT, runner=None, clock=time.time, every=300):
        self.root, self.clock, self.every = root, clock, float(every)
        self.runner = runner or self._run
        self.fetched_at, self.lock = None, threading.Lock()

    def _run(self, argv):
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")   # a fetch never waits on a password prompt
        p = subprocess.run(argv, capture_output=True, text=True, timeout=60, env=env)
        return p.returncode, (p.stdout if p.returncode == 0 else (p.stderr or p.stdout))

    def _git(self, *args):
        try:
            return self.runner(["git", "-C", self.root] + list(args))
        except Exception as e:  # noqa: BLE001 — no git, a timeout: the page shows the reason
            return 1, str(e)

    def get(self):
        with self.lock:
            now = self.clock()
            if self.fetched_at is None or now - self.fetched_at >= self.every:
                self.fetched_at = now                   # a failed fetch also waits `every` before the next try
                self._git("fetch", "-q")
            code, out = self._git("rev-list", "--count", "HEAD..@{upstream}")
        res = {"behind": None, "checked": datetime.datetime.fromtimestamp(now, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        try:
            if code == 0:
                res["behind"] = int(out.strip())
                return res
        except ValueError:
            pass
        res["why"] = "git rev-list --count HEAD..@{upstream}: " + ((out or "").strip()[-300:] or "exit %d" % code)
        return res


# PF-13 (direct buttons): what POST /act will run, and the patterns every value must fully match
SCRIPTS = {"requests": "components/page-features/kit/requests.py",
           "ask": "components/email-production/adapter/ask.py",
           "cq": "components/creative-queue/cq.py",
           "own": "components/email-production/adapter/own_picture.py",   # PF-13b (slow buttons): 53 place
           "review": "components/page-features/dev_queue.py",   # PF-18b (review marks): its `mark` verb only
           "statics": "components/creative-queue/statics.py",   # QB-9 (editor statics): its `done` verb only
           "slots": "components/marketing-calendar/machine/review.py"}   # L60 (slot review): its `mark` verb only
# L60 (slot review), email_lead 2026-11-06: a reviewer's verdict on one planned send, from the emails page's Calendar tab.
# item is <brand>__<YYYY-MM>__<slot id>; field the status, from the table's own list; value an optional one-line note
SLOT_ITEM = re.compile(r"([a-z0-9][a-z0-9-]{0,40})__(\d{4}-\d{2})__([a-z0-9][a-z0-9-]{0,30})")
SLOT_STATUSES = ("approved", "needs-work", "cut", "pending")
SLOT_FIELDS = ("date", "hour", "segment", "category", "type", "role", "offer", "product", "occasion", "angle")  # review.EDITABLE
SLOT_VALUE_MAX = 600                  # an angle runs long; a verdict's note stays REVIEW_NOTE's 200
ITEM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,80}")
# PF-18b (review marks): a "review" entry names its mark; item is a card id; the value is the note (Understood,
# Question, Issue) or the raiser a Resolve resolves, nothing else
REVIEW_MARKS = ("understood", "question", "issue", "resolve", "note",   # DQ-3 (note mark): its words are the value
                "done")   # DQ-8 (act panel): Done on a human act; item is the follow-up's task id, value an optional note
REVIEW_CARD = re.compile(r"[A-Z][A-Z0-9]{0,15}-[A-Z]?\d{1,5}[a-z]{0,3}")
REVIEW_TASK = re.compile(r"TSK-\d{14}-[a-z0-9-]{1,40}|T-\d{1,6}")   # DQ-8 (act panel): a dev task id, or its alias
REVIEW_PERSON = re.compile(r"[a-z0-9][a-z0-9-]{0,30}")
REVIEW_NOTE = re.compile(r"[^\x00-\x1f\x7f]{1,200}")
FAMILY = re.compile(r"[a-z0-9][a-z0-9-]{0,60}")
BODY_MAX = 32768                      # PF-13b: a 2,000-character note or a part's words fit (PF-13's was 8 KB)
VALUE_MAX = 200
NOT_DIRECT = "ask your Claude: this button is not direct"
CQ_ID_VERBS = ("remove", "restore")
STATICS_ROLES = ("graphic-designer", "video-editor")   # QB-11 (creator view): statics.py done --role   # PF-13c (Outlier queue buttons): cq verbs that take only the id
# PF-13b (slow buttons)
JOB_KINDS = ("job", "confirm-job")
NOTE_MAX = 2000
UPLOAD_MAX = 15 * 1024 * 1024
MAGIC = ((b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpg"))   # webp: RIFF....WEBP, below
SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,60}")
MONEY = "It calls a model and costs money."
MODELS = os.path.join("components", "models", "models.json")
PAGE_KEY = "_page"   # set by the page server's kit_act on the body it passes on (the asking page); only a label


class Refused(Exception):
    """A POST /act the kit will not run; answered with its code, nothing runs. `extra` joins the answer (428's
    confirm, 409's job)."""

    def __init__(self, code, said, **extra):
        Exception.__init__(self, said)
        self.code, self.said, self.extra = code, said, extra


def picture_kind(data):
    """png, jpg or webp from the file's first bytes; None for anything else (a gif, a text file renamed .png)."""
    for magic, ext in MAGIC:
        if data.startswith(magic):
            return ext
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def one_note(text):
    """A note as the request file carries it: its lines joined by "\\n" (every line break Python's splitlines knows
    becomes one), outer space gone; ValueError when it is empty, too long, or could be read as a request itself."""
    if not isinstance(text, str):
        raise ValueError("the note must be words")
    note = "\n".join(text.splitlines()).strip()
    if not note:
        raise ValueError("say the change first")
    if len(note) > NOTE_MAX:
        raise ValueError("the note is %d characters; at most %d" % (len(note), NOTE_MAX))
    if "\x00" in note or re.search(r"(?i)request\s*\(", note):
        raise ValueError("a note can't hold the words 'Request ('")
    return note


def tab_lines(text):
    """The note's further lines tab-continued, the way kit/requests.py reads a request over several lines."""
    return "\n\t".join(text.split("\n"))


NO_TOKEN = "refused: no kit token (reload the page from the kit)"
NEW_KEY = "refused: your page server restarted with a new key — reload the page"   # PF-14e: present but wrong


def token_ok(given, token):
    return isinstance(given, str) and hmac.compare_digest(given.encode("utf-8"), token.encode("utf-8"))


def kit_person(root):
    """(person id, None) from run_kit.people.whoami, or (None, why) when this clone's git email maps to no one."""
    try:
        return people.whoami(root), None
    except people.Refused as e:
        return None, str(e)


# PF-18j (people data): the /data sources whose response carries `viewer`, the page server's own person (or None)
VIEWER_SOURCES = ("dev-queue",)
_VIEWERS = {}


def with_viewer(out, viewer):
    """A source's JSON object with `viewer` set; anything else as it came."""
    doc = json.loads(out)
    if not isinstance(doc, dict):
        return out
    doc["viewer"] = viewer
    return json.dumps(doc, ensure_ascii=False)


def direct_table(family, root=ROOT):
    """The family's "direct" table from _templates/<family>.actions.json, {} when there is none."""
    f = os.path.join(root, TEMPLATES, "%s.actions.json" % family)
    try:
        with open(f, encoding="utf-8") as fh:
            got = json.load(fh).get("direct")
    except (OSError, ValueError, AttributeError):
        return {}
    return got if isinstance(got, dict) else {}


class Act(object):
    """POST /act: one direct button, checked, turned into one argv by the kit, run from the repo root. `page` is the
    one page serve.py serves (handler() sets it); the page server leaves it None and names the asking page in the
    body (PAGE_KEY)."""
    page = None

    def __init__(self, family, root=ROOT, person=None, why=None, token=None, runner=None, timeout=120, jobs_=None):
        self.family, self.root, self.timeout = family, root, timeout
        self.person, self.why = person, why          # resolved once, at kit start (main)
        self.token = token or secrets.token_urlsafe(32)
        self.runner = runner or self._run
        self.lock = threading.Lock()                 # one command at a time: they commit and push
        self._jobs = jobs_                           # PF-13b (slow buttons): the page server passes its one Jobs
        self.uploads, self._up = {}, threading.Lock()   # path -> item: the only files a "run": "own" job may take

    @property
    def jobs(self):
        """This kit's Jobs, made on first use with this Act's lock as the gate (serve.py's one-page kit)."""
        if self._jobs is None:
            self._jobs = jobs.Jobs(self.root, gate=self.lock)
        return self._jobs

    def _run(self, argv):
        try:
            p = subprocess.run(argv, cwd=self.root, capture_output=True, text=True, timeout=self.timeout,
                               stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return 1, "stopped: no answer in %d s" % self.timeout
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    def name(self):
        """The person as the request lines say it: editor, email_lead (ask.py's email_lead-only rule reads "email_lead")."""
        return self.person[:1].upper() + self.person[1:]

    def token_ok(self, given):
        return token_ok(given, self.token)

    def entry(self, body):
        """(n, the direct-table entry) for a body's family and n; Refused before anything runs."""
        if not isinstance(body, dict):
            raise Refused(400, "the body must be a JSON object")
        fam = body.get("family")
        if not isinstance(fam, str) or not FAMILY.fullmatch(fam):
            raise Refused(400, "bad family")
        if fam != self.family:
            raise Refused(403, "this kit serves the %s page, not %s" % (self.family, fam))
        n = body.get("n")
        if isinstance(n, bool) or not isinstance(n, (int, str)) or not re.fullmatch(r"\d{1,4}", str(n)):
            raise Refused(400, "bad n")
        why = live.stale_actions(self.page if self.page is not None else body.get(PAGE_KEY), self.root)
        if why:                                      # PF-19 (behind notice): act.js copies the request instead
            raise Refused(403, "ask your Claude: %s" % why, stale_actions=True)
        d = direct_table(fam, self.root).get(str(int(n)))
        if not isinstance(d, dict) or d.get("run") not in SCRIPTS:
            raise Refused(403, NOT_DIRECT)
        if (d.get("kind") or "quick") not in ("quick",) + JOB_KINDS:
            raise Refused(403, NOT_DIRECT)
        return int(n), d

    def build(self, body):
        """(argv, request line or None) for one checked body; Refused names why, before anything runs."""
        n, d = self.entry(body)
        fam = self.family
        if not self.person:
            raise Refused(403, "who are you? %s" % (self.why or "no person for this clone"))
        item = body.get("item")
        if not isinstance(item, str) or not ITEM.fullmatch(item):
            raise Refused(400, "bad item id")
        part = body.get("part")
        if part is None or part == "-":
            part = "-"
        elif isinstance(part, int) and not isinstance(part, bool) and 0 <= part < 1000:
            part = str(part)
        elif isinstance(part, str) and re.fullmatch(r"\d{1,3}", part):
            part = str(int(part))
        else:
            raise Refused(400, "bad part")
        if (d.get("kind") or "quick") in JOB_KINDS:
            return self.build_job(n, d, body, item, part)
        field, value = body.get("field"), body.get("value")
        fields = d.get("fields") or d.get("verbs") or []   # an id-only cq entry: the field names one of its verbs
        if field not in (None, "") and field not in fields:
            raise Refused(400, "bad field: %s takes %s" % (n, ", ".join(fields) or "none"))
        if fields and field in (None, ""):
            raise Refused(400, "which field? %s" % ", ".join(fields))
        if value is None:
            value = ""
        if d["run"] == "slots":                     # L60 (slot review) / L61 (rewrite a planned send)
            return self.build_slots(d, fields, item, field, value)
        if not isinstance(value, str) or len(value) > VALUE_MAX or re.search(r"[\r\n\x00]", value) \
                or value.startswith("-"):
            raise Refused(400, "bad value: one line, at most %d characters, not starting with -" % VALUE_MAX)
        script = os.path.join(self.root, SCRIPTS[d["run"]])
        if d["run"] in ("requests", "ask") and value:
            raise Refused(400, "button %s takes no words" % n)
        if d["run"] == "requests":
            word = d.get("word")
            if not isinstance(word, str) or not re.fullmatch(r"[a-z_-]{1,30}", word):
                raise Refused(403, NOT_DIRECT)
            line = "Request (%s, part %s): %s (from %s)" % (item, part, word, self.name())
            return [sys.executable, script, None, "--family", fam, "--by", self.name()], line
        if d["run"] == "ask":
            phrase = d.get("phrase")
            m = re.fullmatch(r"([\w-]+)__([\w-]+)", item)
            if not isinstance(phrase, str) or not re.fullmatch(r"[a-z: ]{1,60}", phrase):
                raise Refused(403, NOT_DIRECT)
            if not m:
                raise Refused(400, "bad item id: an email is <brand>__<label>")
            line = "Email request (kit direct): %s [%s/%s] · %s (from %s)" % (
                m.group(2), m.group(1), m.group(2), phrase, self.name())
            return [sys.executable, script, None], line
        if d["run"] == "statics":                   # QB-9 (editor statics): Done on one hand-off, by its key
            if d.get("verb") != "done" or fields:
                raise Refused(403, NOT_DIRECT)
            if value:
                raise Refused(400, "button %s takes no words" % n)
            if "_" not in item or ".." in item:
                raise Refused(400, "bad item id: a hand-off key, <brand>_<product>_<brief>")
            role = d.get("role")                     # QB-11 (creator view): from the table, never from the body
            if role is not None and role not in STATICS_ROLES:
                raise Refused(403, NOT_DIRECT)
            return [sys.executable, script, "done", item] + (["--role", role] if role else []) + \
                ["--by", self.person], None
        if d["run"] == "review":
            mark = d.get("mark")
            if mark not in REVIEW_MARKS or fields:
                raise Refused(403, NOT_DIRECT)
            if mark == "done":
                if not REVIEW_TASK.fullmatch(item):
                    raise Refused(400, "bad item id: a follow-up's task id, like TSK-20261030055827-…")
            elif not REVIEW_CARD.fullmatch(item):
                raise Refused(400, "bad item id: a card id, like PF-18b")
            argv = [sys.executable, script, "mark", item, mark, "--by", self.person]
            if mark == "resolve":
                if not REVIEW_PERSON.fullmatch(value):
                    raise Refused(400, "whose mark? the person who raised it")
                return argv + ["--of=" + value], None
            if value and not REVIEW_NOTE.fullmatch(value):
                raise Refused(400, "bad note: one line, at most 200 characters")
            return argv + (["--note=" + value] if value else []), None
        verbs = d.get("verbs")
        if verbs is not None:
            if not isinstance(verbs, list) or field not in verbs or field not in CQ_ID_VERBS:
                raise Refused(403, NOT_DIRECT)
            if value:
                raise Refused(400, "button %s takes no words" % n)
            return [sys.executable, script, field, item, "--by", self.person], None
        verb = d.get("verb")
        if verb == "set":
            values = d.get("values")
            pat = values.get(field) if isinstance(values, dict) else None
            if field == "requested_stage" and not isinstance(pat, str):
                raise Refused(403, NOT_DIRECT)       # a requested stage only from the page's own stage list
            if isinstance(pat, str) and not re.fullmatch(pat, value):
                raise Refused(400, "bad value for %s" % field)
            return [sys.executable, script, "set", item, field, value, "--by", self.person], None
        if verb == "add":
            if not value:
                raise Refused(400, "a title is needed")
            args = body.get("args") or {}
            if not isinstance(args, dict):
                raise Refused(400, "bad args")
            argv = [sys.executable, script, "add", item, "--title=" + value]
            for k, pat in sorted((d.get("args") or {}).items()):
                v = args.get(k)
                if v in (None, ""):
                    continue
                if not isinstance(v, str) or not re.fullmatch(pat, v):
                    raise Refused(400, "bad %s" % k)
                argv.append("--%s=%s" % (k, v))
            return argv + ["--by", self.person], None
        raise Refused(403, NOT_DIRECT)

    def build_slots(self, d, fields, item, field, value):
        """review.py mark (a verdict and an optional one-line note) or edit (one planned field's new words, up to
        SLOT_VALUE_MAX characters, an empty value clearing the rewrite) on one planned send, as the kit's person."""
        script = os.path.join(self.root, SCRIPTS["slots"])
        verb = d.get("verb")
        allowed = SLOT_STATUSES if verb == "mark" else SLOT_FIELDS if verb == "edit" else ()
        if not fields or any(f not in allowed for f in fields):
            raise Refused(403, NOT_DIRECT)
        m = SLOT_ITEM.fullmatch(item)
        if not m:
            raise Refused(400, "bad item id: a planned send is <brand>__<YYYY-MM>__<slot id>")
        if not isinstance(value, str) or re.search(r"[\r\n\x00]", value) or value.startswith("-"):
            raise Refused(400, "bad value: one line, not starting with -")
        argv = [sys.executable, script, verb, m.group(1), m.group(2), m.group(3), field]
        if verb == "mark":
            if value and not REVIEW_NOTE.fullmatch(value):
                raise Refused(400, "bad note: one line, at most 200 characters")
            return argv + ["--by", self.person] + (["--note=" + value] if value else []), None
        if len(value) > SLOT_VALUE_MAX or re.search(r"[\x00-\x1f\x7f]", value):
            raise Refused(400, "bad value: one line, at most %d characters" % SLOT_VALUE_MAX)
        return argv + ["--value=" + value, "--by", self.person], None

    # ------------------------------------------------------------------ PF-13b (slow buttons)
    @staticmethod
    def email_of(item):
        """(brand, label) of an email item id <brand>__<label>, each a plain name."""
        m = re.fullmatch(r"([^_].*?)__(.+)", item)
        if not m or not SLUG.fullmatch(m.group(1)) or not SLUG.fullmatch(m.group(2)) or ".." in item:
            raise Refused(400, "bad item id: an email is <brand>__<label>")
        return m.group(1), m.group(2)

    @staticmethod
    def picture_no(body):
        k = body.get("picture")
        if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k < 100:
            raise Refused(400, "which picture? a number from 0")
        return k

    def build_job(self, n, d, body, item, part):
        """(argv, request file text or None) for a job or confirm-job entry; Refused before anything runs."""
        want = d.get("part")
        if want == "one" and part == "-":
            raise Refused(400, "button %s is for one part: give its number" % n)
        if want == "whole" and part != "-":
            raise Refused(400, "button %s is for the whole email: part -" % n)
        for k in ("field", "args"):
            if body.get(k) not in (None, "", {}):
                raise Refused(400, "button %s takes no %s" % (n, k))
        note = None
        if d.get("note"):
            try:
                note = one_note(body.get("note"))
            except ValueError as e:
                raise Refused(400, str(e))
        elif body.get("note") not in (None, ""):
            raise Refused(400, "button %s takes no note" % n)
        value = body.get("value")
        pat = d.get("value")
        if isinstance(pat, str):
            if not isinstance(value, str) or not re.fullmatch(pat, value):
                raise Refused(400, "bad value for button %s" % n)
        elif value not in (None, ""):
            raise Refused(400, "button %s takes no words" % n)
        script = os.path.join(self.root, SCRIPTS[d["run"]])
        if d["run"] == "own":
            return self.build_own(n, d, body, item, part, script), None
        if d["run"] != "requests":
            raise Refused(403, NOT_DIRECT)
        word = d.get("word")
        if not isinstance(word, str) or not re.fullmatch(r"[a-z_-]{1,30}", word):
            raise Refused(403, NOT_DIRECT)
        payload = ""
        if word == "picture":
            payload = " %d: %s" % (self.picture_no(body), tab_lines(note or ""))
        elif note is not None:
            payload = " " + tab_lines(note)
        elif isinstance(pat, str):
            payload = " " + value
        if d.get("edits"):
            payload = " " + self.edits_json(body.get("edits"))
        elif body.get("edits") not in (None, []):
            raise Refused(400, "button %s takes no edits" % n)
        line = "Request (%s, part %s): %s%s (from %s)" % (item, part, word, payload, self.name())
        return [sys.executable, script, None, "--family", self.family, "--by", self.name()], line

    @staticmethod
    def edits_json(edits):
        """The words as the shared line carries them: one JSON list on one line, every non-ASCII letter escaped (so
        no line break of any kind can split the request)."""
        if not isinstance(edits, list) or not 1 <= len(edits) <= 60:
            raise Refused(400, "the new words: a list of 1 to 60 changes")
        out = []
        for e in edits:
            if not isinstance(e, dict) or not isinstance(e.get("path"), str) \
                    or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.\[\]-]{0,119}", e["path"]):
                raise Refused(400, "bad words: each change needs its field's path")
            x = {"path": e["path"]}
            for k in ("before", "value"):
                v = e.get(k)
                if v is None and k == "before":
                    continue
                if not isinstance(v, str) or len(v) > 4000 or "\x00" in v:
                    raise Refused(400, "bad words: %s must be words, at most 4000 characters" % k)
                x[k] = v
            out.append(x)
        return json.dumps(out, ensure_ascii=True)

    def build_own(self, n, d, body, item, part, script):
        """53 use my picture: own_picture.py place <run folder> S<part>.<picture> <the file this kit saved> --alt."""
        brand, label = self.email_of(item)
        if part == "-":
            raise Refused(400, "button %s is for one picture: give its part" % n)
        k = self.picture_no(body)
        path = body.get("upload")
        with self._up:
            mine = isinstance(path, str) and self.uploads.get(path) == item
        if not mine or not os.path.isfile(os.path.join(self.root, path)):
            raise Refused(400, "pick the picture on the page first (only a file this kit saved for %s)" % item)
        alt = body.get("alt")
        if not isinstance(alt, str) or not alt.strip() or len(alt) > 300 or re.search(r"[\r\n\x00]", alt):
            raise Refused(400, "say what the new picture shows (one line, at most 300 characters)")
        made = body.get("made_with") or ""
        if made and (not isinstance(made, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .'&+-]{0,39}", made)):
            raise Refused(400, "made with: a tool's name, at most 40 characters")
        run = (d.get("run_folder") or "").format(brand=brand, label=label)
        if not run.startswith("runs/") or not os.path.isdir(os.path.join(self.root, run)):
            raise Refused(404, "no email %s here" % item)
        argv = [sys.executable, script, "place", run, "S%d.%d" % (int(part) + 1, k + 1), path,
                "--alt=" + alt.strip(), "--by", self.name(), "--commit"]
        return argv + (["--made-with=" + made] if made else [])

    def ask_line(self, d, body, line):
        """The exact words to paste in Claude when a job stops: the request line itself, or for an own picture the
        emails page's own line naming the saved file."""
        if line is not None:
            return line
        brand, label = self.email_of(body["item"])
        part, k = int(body.get("part")), int(body.get("picture"))
        short = re.sub(r"^%s-" % re.escape(brand), "", label)
        return ("Email request (components/email-production/adapter/README.md): %s · S%d.%d [%s/%s, section %d, "
                "picture %d] · use my own picture. My picture: %s, alt: %s (from %s)"
                % (short, part + 1, k + 1, brand, label, part, k, body.get("upload"), body.get("alt", "").strip(),
                   self.name()))

    def confirm_text(self, n, d):
        """The confirm a confirm-job asks first: what runs, what it costs, the models the adapter names."""
        said = [(d.get("confirm") or "Button %d runs on this email." % n).strip(), (d.get("cost") or MONEY).strip()]
        names = self.models_for(d)
        said.append("Models (from the models registry): %s." % ", ".join(names) if names else
                    "The adapter names no model for this in the models registry; the email line picks it.")
        said.append("OK runs it once; Cancel runs nothing.")
        return " ".join(said)

    def models_for(self, d):
        """The registry labels of the models the family's adapter manifest names for this word ("models": {word:
        [registry id, …]}), [] when it names none."""
        try:
            with open(os.path.join(self.root, TEMPLATES, "%s.actions.json" % self.family), encoding="utf-8") as fh:
                adapter = json.load(fh).get("adapter")
            with open(os.path.join(self.root, adapter), encoding="utf-8") as fh:
                ids = (json.load(fh).get("models") or {}).get(d.get("word") or d.get("run")) or []
            with open(os.path.join(self.root, MODELS), encoding="utf-8") as fh:
                reg = {m.get("id"): m for m in json.load(fh).get("models") or [] if isinstance(m, dict)}
        except (OSError, ValueError, TypeError, AttributeError):
            return []
        return ["%s (%s)" % (reg[i].get("label") or i, i) for i in ids if i in reg]

    def start_job(self, n, d, body, argv, line):
        """202's answer: the job started; Refused 409 (one job per email) or 428 (no confirm yet) first."""
        item = body["item"]
        busy = self.jobs.working(self.family, item)
        if busy:
            raise Refused(409, "already working on %s" % item, job=busy.id)
        if (d.get("kind") == "confirm-job") and body.get("confirmed") is not True:
            text = self.confirm_text(n, d)
            raise Refused(428, text, confirm=text)
        ask = self.ask_line(d, body, line)
        f = None
        if line is not None:
            fd, f = tempfile.mkstemp(prefix="kit-job-", suffix=".txt")
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(line + "\n")
            argv[2] = f
        try:
            page = body.get(PAGE_KEY)
            view = self.jobs.start(self.family, item, n, argv, ask, f, page if isinstance(page, str) else None)
        except jobs.Busy as e:
            if f:
                os.unlink(f)
            raise Refused(409, str(e), job=e.job)
        return {"ok": True, "job": view["job"], "state": view["state"], "said": "working on %s" % item, "ask": ask}

    def upload(self, item, data, family=None):
        """{"ok", "path"}: the picked file saved under the email's run folder, in the "into" folder of this family's
        "run": "own" entry, with a name the kit makes; Refused before anything is written."""
        if family is not None and family != self.family:
            raise Refused(403, "this kit serves the %s page, not %s" % (self.family, family))
        d = next((x for x in direct_table(self.family, self.root).values()
                  if isinstance(x, dict) and x.get("run") == "own"), None)
        if not d or not d.get("into") or not d.get("run_folder"):
            raise Refused(403, "this page takes no pictures")
        if not self.person:
            raise Refused(403, "who are you? %s" % (self.why or "no person for this clone"))
        if not isinstance(item, str) or not ITEM.fullmatch(item):
            raise Refused(400, "bad item id")
        brand, label = self.email_of(item)
        if not data:
            raise Refused(400, "no picture in the request")
        ext = picture_kind(data)
        if not ext:
            raise Refused(415, "only a png, jpg or webp picture")
        run = d["run_folder"].format(brand=brand, label=label)
        into = d["into"].format(brand=brand, label=label)
        top = os.path.realpath(os.path.join(self.root, run))
        if not run.startswith("runs/") or not os.path.isdir(top):
            raise Refused(404, "no email %s here" % item)
        folder = os.path.realpath(os.path.join(top, into))
        if not folder.startswith(top + os.sep) or ".." in into:
            raise Refused(403, "refused: outside the email's run folder")
        os.makedirs(folder, exist_ok=True)
        name = "upload-%s-%s.%s" % (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), secrets.token_hex(4), ext)
        fd = os.open(os.path.join(folder, name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o644)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        rel = "/".join([run.rstrip("/"), into.strip("/"), name])
        with self._up:
            self.uploads[rel] = item
        return {"ok": True, "path": rel}

    def run(self, body):
        """{"ok", "said"} after the command; a job's {"ok", "job", "ask"} at once; Refused before anything runs."""
        argv, line = self.build(body)
        if any(a and (a == "--root" or a.startswith("--root=")) for a in argv):
            raise Refused(403, "never --root: the shadow queue only")
        n, d = self.entry(body)
        if (d.get("kind") or "quick") in JOB_KINDS:
            return self.start_job(n, d, body, argv, line)
        with self.lock:
            f = None
            try:
                if line is not None:
                    fd, f = tempfile.mkstemp(prefix="kit-act-", suffix=".txt")
                    with os.fdopen(fd, "w", encoding="utf-8") as fh:
                        fh.write(line + "\n")
                    argv[2] = f
                code, out = self.runner(argv)
            finally:
                if f:
                    try:
                        os.unlink(f)
                    except OSError:
                        pass
        lines = [x for x in (out or "").splitlines() if x.strip()]
        return {"ok": code == 0, "said": "\n".join(lines[-8:]) or ("done" if code == 0 else "exit %d" % code)}


# PF-26 (page-family cleanup): the kit's own injected script, after the token meta and before any page script. A GET
# to this server's /data/ answered 503 ("starting": the server's sources are not loaded yet) is asked again, up to
# DATA_TRIES times DATA_WAIT_MS apart; every other fetch goes through untouched. Pages call /data with their own
# fetch, so this is the one place every page gets the retry.
DATA_TRIES, DATA_WAIT_MS = 8, 1000
DATA_RETRY = (
    "<script>(function(w){var f=w.fetch;if(!f)return;w.fetch=function(u,o){var t=this,a=arguments,n=0,p;"
    "try{p=new URL(typeof u==='string'?u:(u&&u.url)||String(u),w.location.href)}catch(e){return f.apply(t,a)}"
    "var m=((o&&o.method)||(u&&u.method)||'GET').toUpperCase();"
    "if(m!=='GET'||p.origin!==w.location.origin||p.pathname.indexOf('/data/')!==0)return f.apply(t,a);"
    "return f.apply(t,a).then(function again(r){if(r.status!==503||n>=%d)return r;n++;"
    "return new Promise(function(ok){setTimeout(ok,%d)}).then(function(){return f.apply(t,a)}).then(again)})}})"
    "(window)</script>" % (DATA_TRIES, DATA_WAIT_MS))


def with_token(data, token):
    """The page with <meta name="kit-token"> right after its <head>, then DATA_RETRY (PF-26 (page-family cleanup));
    a page with no <head> is served as it is."""
    text = data.decode("utf-8", "replace")
    m = re.search(r"<head(\s[^>]*)?>", text, re.I)
    if not m:
        return data
    meta = '\n<meta name="kit-token" content="%s">\n%s' % (token, DATA_RETRY)
    return (text[:m.end()] + meta + text[m.end():]).encode("utf-8")


class KitHandler(BaseHTTPRequestHandler):
    """The kit's routes. handler() below binds it to one page; PF-14 (page server)'s server.py subclasses it to host
    many pages on one server through the kit_* hooks: kit_sources() the Sources this request reads, kit_act(body) the
    Act a POST /act body goes to, kit_token() the token pages carry, kit_index() what / answers, kit_page(path, data)
    a page's bytes as served, kit_acted(body, code, res) after every /act answer past the token guard (202 = a job
    started), kit_jobs() the Jobs GET /job/<id> reads (PF-13b (slow buttons))."""
    root, status, src, act, page_rel = ROOT, None, None, None, None

    def log_message(self, *a):
        pass

    def kit_sources(self):
        return self.src

    def kit_act(self, body):
        return self.act

    def kit_jobs(self):
        return self.act.jobs

    def kit_token(self):
        return self.act.token

    def kit_index(self):
        self.send_response(302)
        self.send_header("Location", "/p/" + self.page_rel)
        self.end_headers()

    def kit_page(self, path, data):
        return with_token(data, self.kit_token())       # PF-13 (direct buttons): in memory only, never on disk

    def kit_acted(self, body, code, res):
        pass

    def kit_starting(self):
        """PF-26 (page-family cleanup): true while the server's sources are not loaded yet; an unknown /data name
        then answers 503 "starting" (DATA_RETRY asks again), never 404. One page's kit is loaded from the start."""
        return False

    def kit_viewer(self):
        """PF-18j (people data): the page server's person: its Act's (resolved at kit start), else kit_person of
        this root, resolved once per root (server.py resolves its own the same way)."""
        if self.act is not None:
            return self.act.person
        if self.root not in _VIEWERS:
            _VIEWERS[self.root] = kit_person(self.root)[0]
        return _VIEWERS[self.root]

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path, page=False):
        with open(path, "rb") as fh:
            data = fh.read()
        if page and path.lower().endswith(".html"):
            data = self.kit_page(path, data)
        self._send(200, data, mimetypes.guess_type(path)[0] or "application/octet-stream")

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def _foreign(self):
        """True (and 403 sent) when the Host is not this kit's own name: first, so a foreign name touches nothing."""
        port = self.server.server_address[1]
        if allowed_host(self.headers.get("Host", ""), port):
            return False
        self._send(403, "refused: this kit answers only http://127.0.0.1:%d/" % port)
        return True

    def do_POST(self):
        """PF-13 (direct buttons): /act, and PF-13b (slow buttons)'s /upload; every guard before anything runs."""
        port = self.server.server_address[1]
        if self._foreign():
            return
        route = urlparse(self.path).path
        if route not in ("/act", "/upload"):
            return self._send(404, "not here")
        origin = (self.headers.get("Origin") or "").strip().lower()
        if origin not in ("http://127.0.0.1:%d" % port, "http://localhost:%d" % port):
            return self._json(403, {"ok": False, "said": "refused: only this kit's own page may ask"})
        given = self.headers.get("X-Kit-Token")
        if not token_ok(given, self.kit_token()):         # PF-14e (token survives): a wrong key says why
            return self._json(403, {"ok": False, "said": NEW_KEY if (given or "").strip() else NO_TOKEN})
        top = UPLOAD_MAX if route == "/upload" else BODY_MAX
        try:
            size = int(self.headers.get("Content-Length") or "-1")
        except ValueError:
            size = -1
        if size < 0 or size > top:
            return self._json(413 if size > top else 411, {"ok": False, "said": "the body must be 1 to %d bytes" % top})
        if route == "/upload":
            return self._upload(size)
        try:
            body = json.loads(self.rfile.read(size).decode("utf-8"))
        except ValueError:
            return self._json(400, {"ok": False, "said": "the body must be JSON"})
        try:
            code, res = 200, self.kit_act(body).run(body)
            if res.get("job"):
                code = 202                                  # PF-13b: started; GET /job/<id> follows it
        except Refused as e:
            code, res = e.code, dict(e.extra, ok=False, said=e.said)
        except Exception as e:  # noqa: BLE001 — the page shows the reason
            code, res = 500, {"ok": False, "said": str(e)[:400]}
        self.kit_acted(body, code, res)
        return self._json(code, res)

    def _upload(self, size):
        """PF-13b (slow buttons): POST /upload?family=<f>&item=<email id>, the picture's bytes as the body."""
        q = parse_qs(urlparse(self.path).query)
        fam, item = (q.get("family") or [""])[0], (q.get("item") or [""])[0]
        data = self.rfile.read(size)
        try:
            res = self.kit_act({"family": fam}).upload(item, data, fam)
            code = 200
        except Refused as e:
            code, res = e.code, {"ok": False, "said": e.said}
        except Exception as e:  # noqa: BLE001 — the page shows the reason
            code, res = 500, {"ok": False, "said": str(e)[:400]}
        return self._json(code, res)

    def _runs_file(self, rel):
        """A file under runs/ only when it resolves inside one of the family's declared prefixes."""
        f = safe_file(self.root, "runs", rel)
        if not f:
            return None
        inside = os.path.relpath(f, os.path.realpath(os.path.join(self.root, "runs"))).replace(os.sep, "/")
        return f if any(inside.startswith(p) for p in runs_prefixes(self.kit_sources().decl_now())) else None

    def do_GET(self):
        if self._foreign():
            return
        route = urlparse(self.path).path
        if route == "/":
            return self.kit_index()
        if route.startswith("/p/"):
            f = safe_file(self.root, VIEWERS, route[len("/p/"):])
            return self._file(f, page=True) if f else self._send(404, "not here")
        if route.startswith("/runs/"):
            f = self._runs_file(route[len("/runs/"):])
            return self._file(f) if f else self._send(404, "not here")
        if route.startswith("/stamp/"):
            name = route[len("/stamp/"):]
            try:
                body = json.dumps({"name": name, "stamp": self.kit_sources().stamp(name)})
            except KeyError:
                return self._send(404, "no watched source called %s" % name)
            return self._send(200, body, "application/json; charset=utf-8")
        if route == "/status":
            return self._send(200, json.dumps(self.status.get()), "application/json; charset=utf-8")
        if route.startswith("/job/"):                       # PF-13b (slow buttons): one job's state
            got = self.kit_jobs().get(route[len("/job/"):])
            return self._json(200, got) if got else self._send(404, "no job here by that id")
        if route.startswith("/data/"):
            name = route[len("/data/"):]
            try:
                params = {}
                for k, vs in parse_qs(urlparse(self.path).query, keep_blank_values=True).items():
                    if len(vs) != 1:
                        raise BadParameter("bad parameter %s" % k)
                    params[k] = vs[0]
                src = self.kit_sources()
                out = src.get(name, params)                    # PF-18j (people data): the page learns its viewer; a family
                if name in VIEWER_SOURCES or src.wants_viewer(name):   # asks for it per source with "viewer": true (2026-11-06)
                    out = with_viewer(out, self.kit_viewer())
                return self._send(200, out, "application/json; charset=utf-8")
            except KeyError:
                if self.kit_starting():                     # PF-26 (page-family cleanup): sources not loaded yet
                    return self._send(503, "starting")
                return self._send(404, "no data source called %s" % name)
            except BadParameter as e:
                return self._send(400, str(e)[:400])
            except Exception as e:  # noqa: BLE001 — the page shows the reason
                return self._send(502, str(e)[:400])
        self._send(404, "not here")


def handler(page_rel, src, root=ROOT, status=None, act=None):
    """The kit's routes for one page (what `serve.py <page>` serves)."""
    status = status or Status(root)
    act = act or Act(family_of(page_rel), root, *kit_person(root))
    if act.page is None:
        act.page = page_rel                          # PF-19 (behind notice): whose buttons these are
    return type("H", (KitHandler,), {"root": root, "status": status, "src": src, "act": act, "page_rel": page_rel})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("page")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--open", action="store_true", help="open the page in the default browser")
    x = ap.parse_args(argv)
    page = os.path.realpath(x.page)
    top = os.path.realpath(os.path.join(ROOT, VIEWERS))
    if not page.startswith(top + os.sep) or not page.endswith(".html") or not os.path.isfile(page):
        print("refused: %s is not a page under %s" % (x.page, VIEWERS))
        return 2
    rel = os.path.relpath(page, top).replace(os.sep, "/")
    fam = family_of(page)
    problems = preflight(sources(fam, ROOT))
    if problems:
        for p in problems:
            print("refused: " + p)
        return 2
    src = Sources(lambda: sources(fam, ROOT), root=ROOT)
    person, why = kit_person(ROOT)                  # PF-13 (direct buttons): the kit's own identity, once
    act = Act(fam, ROOT, person, why)
    srv = ThreadingHTTPServer(("127.0.0.1", x.port), handler(rel, src, root=ROOT, act=act))
    url = "http://127.0.0.1:%d/" % x.port
    print("serving %s at %s (Ctrl-C stops it)" % (rel, url))
    print("direct buttons (quick and slow) run as %s" % person if person else "direct buttons are off: %s" % why)
    if x.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
