#!/usr/bin/env python3
"""PF-1d (auto-log page changes): autolog reads each unlogged commit that
changed a person's draft and logs its numbers; the change-line contract
accepts the auto, unnumbered and backfill shapes and refuses each defect by
name; autosave hands its runner to autolog only when log_commits is on.

    python3 test_pf1d_autolog.py

Stdlib only, no network. Git runs ONLY in repositories this test makes with
`git init` under tempfile.mkdtemp(), each call with cwd = that temporary root
and -c user.name / user.email / core.hooksPath=/dev/null / commit.gpgsign=false;
no remote, never a push. Reads the real editor draft, its log and the
emails-demo family list (read only; their sha256 is checked before and
after). Runs under python3 and /usr/bin/python3 (3.9). One PASS/FAIL line per
check, then "N/M passed"; exit 1 on any FAIL.
"""
import copy, hashlib, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import autolog  # noqa: E402
import features  # noqa: E402

VIEWERS = os.path.join(ROOT, "platform", "views", "viewers")
REAL_PAGE = os.path.join(VIEWERS, "editor", "drafts", "emails--demo.html")  # renamed from emails-demo--demo, 2026-10-22
REAL_LOG = os.path.join(VIEWERS, "editor", "drafts", "emails--demo.changes.jsonl")
REAL_LIST = os.path.join(VIEWERS, "_templates", "emails.features.json")  # family renamed from emails-demo, 2026-10-21
V1_1 = os.path.join(HERE, "examples", "mini-runs-run-detail.v1-1.features.json")
SCHEMA = os.path.join(HERE, "features.schema.json")
SMALL = os.path.join(HERE, "test_pf1d_fixtures", "small.html")

TPL = "platform/views/viewers/_templates/emails-demo.features.json"
PAGE = "platform/views/viewers/editor/drafts/emails-demo--demo.html"
LOG = "platform/views/viewers/editor/drafts/emails-demo--demo.changes.jsonl"
SPAGE = "platform/views/viewers/editor/drafts/emails-demo--small.html"
SLOG = "platform/views/viewers/editor/drafts/emails-demo--small.changes.jsonl"
developer = "platform/views/viewers/developer/drafts/emails-demo--small.html"
SUBJECT = "editor draft: move 'how this works' guide to the bottom of the page"
GIT_C = ["-c", "user.name=PF-1d test", "-c", "user.email=pf1d@example.invalid",
         "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
         "-c", "init.defaultBranch=main"]
READ_ONLY = ("log", "show", "rev-parse")

RESULTS = []
TEMPS = []
if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout.reconfigure(encoding="utf-8")


def check(label, fn):
    try:
        fn()
        RESULTS.append(True)
        print("PASS  %s" % label)
    except AssertionError as exc:
        RESULTS.append(False)
        print("FAIL  %s — %s" % (label, exc))
    except Exception as exc:  # a crash is a failure, never a pass
        RESULTS.append(False)
        print("FAIL  %s — raised %s: %s" % (label, type(exc).__name__, exc))


def tree_hashes():
    out = {}
    for folder, _, names in os.walk(VIEWERS):
        for name in names:
            path = os.path.join(folder, name)
            with open(path, "rb") as fh:
                out[path] = hashlib.sha256(fh.read()).hexdigest()
    return out


BEFORE_TREE = tree_hashes()


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def git_env(**over):
    env = dict(os.environ)
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_AUTHOR_DATE": "2026-10-21T10:00:00+00:00",
                "GIT_COMMITTER_DATE": "2026-10-21T10:00:00+00:00"})
    env.update(over)
    return env


class Repo:
    """A temporary git repository; every git call has cwd = its root."""

    def __init__(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="pf1d-"))
        TEMPS.append(self.root)
        assert not self.root.startswith(os.path.realpath(ROOT) + os.sep)
        self.calls = []
        self.git("init", "-q")

    def git(self, *args, **env):
        assert os.path.realpath(self.root) != os.path.realpath(ROOT)
        proc = subprocess.run(["git"] + GIT_C + list(args), cwd=self.root,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, env=git_env(**env), timeout=30)
        assert proc.returncode == 0, (args, proc.stderr)
        return proc.stdout

    def runner(self, argv, cwd):
        """The runner autolog gets: read-only git, cwd = this root, -c flags."""
        assert os.path.realpath(cwd) == self.root, "git outside the temp repo: %r" % cwd
        assert argv[0] == "git" and argv[1] in READ_ONLY, "not a read-only call: %r" % argv
        self.calls.append(list(argv))
        proc = subprocess.run(["git"] + GIT_C + list(argv[1:]), cwd=self.root,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, env=git_env(), timeout=30)
        return proc.returncode, proc.stdout, proc.stderr

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def read(self, rel):
        return read(os.path.join(self.root, rel))

    def edit(self, rel, old, new):
        text = self.read(rel)
        assert text.count(old) == 1, (rel, old)
        self.write(rel, text.replace(old, new))

    def commit(self, subject, *paths, **env):
        self.git("add", "-A", "--", *(paths or ["."]))
        self.git("commit", "-q", "-m", subject, **env)
        return self.git("rev-parse", "HEAD").strip()

    def run(self, person="editor", **kw):
        return autolog.autolog(self.root, person, git_runner=self.runner, **kw)


# editor's page AS OF her commit 315a3bfeed, read from git — never the live file, which
# she keeps editing (fb9f501e08 broke a test that read the current draft).
AFTER = subprocess.run(["git", "-C", ROOT, "show", "315a3bfeed:platform/views/viewers/editor/drafts/emails-demo--demo.html"],
                       capture_output=True, text=True, check=True).stdout


def before_page():
    """editor's draft before 315a3bfeed: its line 166 back at line 163."""
    rows = AFTER.split("\n")
    moved = rows.pop(165)
    assert 'id="guide" data-feature="2"' in moved, moved
    rows.insert(162, moved)
    return "\n".join(rows)


def seeded():
    """Commit 1: the real family list, editor's draft as it was before
    315a3bfeed, an empty log, the small fixture page for editor and developer, a page
    to delete, editor's live page and a draft of a family with no list."""
    repo = Repo()
    repo.write(TPL, read(REAL_LIST))
    repo.write(PAGE, before_page())
    repo.write(LOG, "")
    repo.write(SPAGE, read(SMALL))
    repo.write(developer, read(SMALL))
    repo.write("platform/views/viewers/editor/drafts/emails-demo--gone.html", read(SMALL))
    repo.write("platform/views/viewers/editor/emails-demo.html", read(SMALL))
    repo.write("platform/views/viewers/editor/drafts/nolist--x.html", read(SMALL))
    repo.seed = repo.commit("seed")
    return repo


def editor_commit(repo):
    repo.write(PAGE, AFTER)
    return repo.commit(SUBJECT, PAGE, GIT_AUTHOR_NAME="editor",
                       GIT_AUTHOR_EMAIL="editor@example.invalid",
                       GIT_AUTHOR_DATE="2026-10-21T15:32:15+07:00")


FAMILY = features.load(REAL_LIST)


def valid(lines):
    return features.validate_changes(lines, FAMILY)


# ------------------------------------------------------ the reference case


def _reference():
    repo = seeded()
    sha = editor_commit(repo)
    assert repo.read(PAGE) == AFTER
    names = repo.git("show", "--name-status", "--format=", sha).split()
    assert names == ["M", PAGE], names
    dry = repo.run(dry_run=True)
    assert repo.read(LOG) == "", "dry_run wrote the log"
    got = repo.run()
    want = {"n": 2, "said": SUBJECT, "at": "2026-10-21T08:32:15Z", "by": "editor",
            "route": "claude-code", "commit": sha[:10], "logged": "auto"}
    assert got == dry, (got, dry)
    assert len(got) == 1, got
    assert got[0] == {"page": PAGE, "log": LOG, "entry": want}, got
    assert list(got[0]["entry"]) == list(want), list(got[0]["entry"])
    lines = features.read_changes(os.path.join(repo.root, LOG))
    assert [json.loads(l) for l in lines] == [want], lines
    assert repo.read(LOG) == features.dumps_changes([want])
    assert valid(lines) == [], valid(lines)
    for call in repo.calls:
        assert call[1] in READ_ONLY, call
    assert repo.git("status", "--porcelain") == " M %s\n" % LOG, "autolog committed or touched more"


def _idempotent():
    repo = seeded()
    sha = editor_commit(repo)
    assert len(repo.run()) == 1
    before = repo.read(LOG)
    assert repo.run() == [], "a second run logged again"
    assert repo.read(LOG) == before, "a second run changed the log"
    repo = seeded()
    sha = editor_commit(repo)
    real = json.loads(features.read_changes(REAL_LOG)[0])
    assert list(real) == ["n", "said", "at", "by", "route", "commit", "logged", "note"], real
    line = dict(real, commit=sha[:10])
    repo.write(LOG, features.dumps_changes([line]))
    assert repo.run() == [], "a commit with a backfilled line was logged again"
    repo.write(LOG, features.dumps_changes([dict(real, commit=sha[:7])]))
    assert repo.run() == [], "a 7-character prefix did not count as the same commit"
    assert repo.read(LOG) == features.dumps_changes([dict(real, commit=sha[:7])])


# ------------------------------------------------------ manual and auto lines


def _manual_line():
    repo = seeded()
    repo.edit(SPAGE, "Loading the emails", "Loading every email")
    manual = {"n": 9, "said": "say every email", "at": "2026-10-21T09:00:00Z",
              "by": "editor", "route": "claude-code"}
    repo.write(SLOG, features.dumps_changes([manual]))
    repo.commit("page: emails-demo 9 (editor)", SPAGE, SLOG)
    repo.edit(SPAGE, "a second inner line", "a second inner line, changed")
    auto = {"n": 2, "said": "an earlier commit", "at": "2026-10-21T09:00:00Z", "by": "editor",
            "route": "claude-code", "commit": "abcdef1234", "logged": "auto"}
    with open(os.path.join(repo.root, SLOG), "a", encoding="utf-8") as fh:
        fh.write(features.dumps_changes([auto]))
    third = repo.commit("page: autosave (editor)", SPAGE, SLOG)
    got = repo.run()
    assert [g["entry"]["commit"] for g in got] == [third[:10]], got
    assert [g["entry"]["n"] for g in got] == [9], got
    assert got[0]["log"] == SLOG and got[0]["entry"]["said"] == "page: autosave (editor)", got
    assert valid(features.read_changes(os.path.join(repo.root, SLOG))) == []


# ------------------------------------------------------ which numbers


def _numbers():
    repo = seeded()
    repo.write(SLOG, json.dumps({"n": 8, "said": "older", "at": "2026-10-21T09:00:00Z",
                                 "by": "editor", "route": "claude-code"}))  # no final newline
    repo.commit("a log with no final newline", SLOG)
    repo.edit(SPAGE, "PF-1d fixture page", "PF-1d fixture page, retitled")
    head = repo.commit("retitle the page")
    repo.edit(SPAGE, "Loading the emails", "Loading the emails now")
    inner = repo.commit("inner line of 9")
    repo.edit(SPAGE, 'href="#a"', 'href="#b"')
    two = repo.commit("a line carrying 3 and 37")
    repo.edit(SPAGE, "a retired number", "a retired number, edited")
    retired = repo.commit("a line carrying only retired 39")
    repo.edit(SPAGE, "<h1>Emails waiting on you</h1>",
              "<h1>Emails waiting on you</h1>\n  <h2>and more</h2>")
    added = repo.commit("a line added inside 8")
    got = repo.run()
    by = {}
    for g in got:
        by.setdefault(g["entry"]["commit"], []).append(g["entry"])
    assert list(by) == [s[:10] for s in (head, inner, two, retired, added)], list(by)
    unn = by[head[:10]]
    assert unn == [{"n": None, "said": "retitle the page", "at": "2026-10-21T10:00:00Z",
                    "by": "editor", "route": "claude-code", "kind": "unnumbered",
                    "commit": head[:10], "logged": "auto"}], unn
    assert list(unn[0]) == ["n", "said", "at", "by", "route", "kind", "commit", "logged"]
    assert [e["n"] for e in by[inner[:10]]] == [9], by[inner[:10]]
    assert [e["n"] for e in by[two[:10]]] == [3, 37], by[two[:10]]
    assert [(e["n"], e.get("kind")) for e in by[retired[:10]]] == [(None, "unnumbered")]
    assert [e["n"] for e in by[added[:10]]] == [8], by[added[:10]]
    lines = features.read_changes(os.path.join(repo.root, SLOG))
    assert len(lines) == 1 + 6, lines
    assert valid(lines) == [], valid(lines)


def _numbers_in_versions():
    old = read(SMALL)
    assert autolog._numbers_in(old, [5]) == set()
    assert autolog._numbers_in(old, [12, 13]) == {9}
    assert autolog._numbers_in(old, [15]) == {3, 37}
    assert autolog._numbers_in(old, [17, 19]) == set(), "img / main carry no number"
    nested = '<div data-feature="4">\n<section data-feature="5">\n<b>x</b>\n</section>\n</div>\n'
    assert autolog._numbers_in(nested, [3]) == {5}, "not the innermost"
    multi = '<div\n  class="a"\n  data-feature="6">\n</div>\n'
    assert autolog._numbers_in(multi, [2]) == {6}, "a multi-line start tag"
    assert autolog._hunks("@@ -163 +162,0 @@\n-x\n@@ -165,0 +166 @@\n+x\n") == ([163], [166])


# ------------------------------------------------------ skips


def _skips():
    repo = seeded()
    repo.edit(SPAGE, "Loading the emails", "Loading one")
    repo.edit(developer, "Loading the emails", "Loading one")
    repo.commit("an engine propagation to two people")
    repo.edit(SPAGE, "Loading one", "Loading two")
    repo.write("platform/views/viewers/_templates/notes.txt", "x\n")
    repo.commit("a change with the templates")
    repo.write("platform/views/viewers/editor/drafts/emails-demo--new.html", read(SMALL))
    repo.commit("a new page")
    os.remove(os.path.join(repo.root, "platform/views/viewers/editor/drafts/emails-demo--gone.html"))
    repo.commit("a page deleted")
    repo.edit("platform/views/viewers/editor/emails-demo.html", "Loading the emails", "Live")
    repo.commit("editor's live page")
    repo.edit("platform/views/viewers/editor/drafts/nolist--x.html", "Loading the emails", "x")
    repo.commit("a family with no list")
    repo.edit(developer, "Loading one", "Loading developer")
    developer = repo.commit("developer's own draft")
    assert repo.run() == [], "editor: something out of scope was logged"
    got = repo.run("developer", dry_run=True)
    assert [g["entry"]["commit"] for g in got] == [developer[:10]], got
    assert got[0]["page"] == developer and got[0]["entry"]["by"] == "developer", got
    assert not os.path.exists(os.path.join(repo.root, developer[:-5] + ".changes.jsonl"))


def _merge():
    repo = seeded()
    repo.git("checkout", "-q", "-b", "side")
    repo.edit(SPAGE, "a retired number", "side edit")
    side = repo.commit("side: edit 39's line")
    repo.git("checkout", "-q", "main")
    repo.edit(SPAGE, "plain text, no number around it", "main edit")
    main = repo.commit("main: edit main's line")
    repo.git("merge", "-q", "--no-ff", "-m", "merge side", "side")
    merge = repo.git("rev-parse", "HEAD").strip()
    got = repo.run()
    commits = sorted(g["entry"]["commit"] for g in got)
    assert commits == sorted([side[:10], main[:10]]), (commits, side, main, merge)
    assert merge[:10] not in commits


def _git_failure():
    repo = Repo()  # no commit: git log HEAD fails
    assert repo.run() == []
    repo = seeded()
    editor_commit(repo)

    def failing(argv, cwd):
        if argv[1] == "show":
            return 128, "", "fatal: bad object"
        return repo.runner(argv, cwd)
    assert autolog.autolog(repo.root, "editor", git_runner=failing) == []
    assert repo.read(LOG) == ""
    assert autolog.autolog(repo.root, "", git_runner=failing) == []


# ------------------------------------------------------ the contract


AUTO = {"n": 2, "said": SUBJECT, "at": "2026-10-21T08:32:15Z", "by": "editor",
        "route": "claude-code", "commit": "315a3bfeed", "logged": "auto"}
UNN = {"n": None, "said": "retitle", "at": "2026-10-21T08:32:15Z", "by": "editor",
       "route": "claude-code", "kind": "unnumbered", "commit": "315a3bfeed", "logged": "auto"}


def one(line, text):
    got = valid([line])
    assert got == ["line 1: " + text], got


def _contract():
    assert valid([AUTO, UNN]) == [], valid([AUTO, UNN])
    assert valid([dict(UNN, logged="backfill", note="by hand")]) == []
    no_logged = dict(UNN)
    del no_logged["logged"]
    assert valid([no_logged]) == []
    no_kind = dict(UNN)
    del no_kind["kind"]
    one(no_kind, "n None is not an integer")
    one(dict(UNN, n=2), "kind 'unnumbered' needs n null")
    no_commit = dict(UNN)
    del no_commit["commit"], no_commit["logged"]
    one(no_commit, "`commit` is missing (an unnumbered line names its commit)")
    one(dict(AUTO, logged="x"), "logged 'x' is not auto | backfill")
    logged_only = dict(AUTO)
    del logged_only["commit"]
    one(logged_only, "`commit` is missing (a logged line names its commit)")
    one(dict(AUTO, commit="xyz"), "commit 'xyz' is not a 7-40 character hex sha")
    one(dict(AUTO, commit="315A3BFEED"), "commit '315A3BFEED' is not a 7-40 character hex sha")
    one(dict(AUTO, note=""), "`note` is empty or not a string")
    one(dict(AUTO, kind="extra"), "kind 'extra' is not 'missing'")
    assert features.CHANGE_LOGGED == ["auto", "backfill"]
    assert features.CHANGE_KINDS == ["missing", "unnumbered"]
    assert features.CHANGE_OPTIONAL[-3:] == ["commit", "logged", "note"]
    assert features.SCHEMA_MINOR == 2


def _real_log():
    proc = subprocess.run([sys.executable, os.path.join(HERE, "features.py"),
                           "--changes", REAL_LOG, REAL_LIST],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    text = proc.stdout.decode("utf-8")
    assert proc.returncode == 0 and "valid: 1 change" in text, (proc.returncode, text)


def _v11_refuses():
    doc = features.load(V1_1)
    assert doc["schema_minor"] == 1
    doc = copy.deepcopy(doc)
    line = {"n": 3, "said": "x", "at": "2026-10-21T08:32:15Z", "by": "editor",
            "route": "claude-code", "commit": "315a3bfeed", "logged": "auto", "note": "x"}
    doc["changes"] = [line]
    got = features.validate(doc)
    assert got == ["changes 1: unknown key 'commit'", "changes 1: unknown key 'logged'",
                   "changes 1: unknown key 'note'"], got


def _schema():
    with open(SCHEMA, encoding="utf-8") as fh:
        ch = json.load(fh)["$defs"]["change"]
    assert list(ch["properties"]) == features.CHANGE_KEYS + features.CHANGE_OPTIONAL
    assert ch["properties"]["commit"]["pattern"] == features.COMMIT_RE.pattern
    assert ch["properties"]["logged"]["enum"] == features.CHANGE_LOGGED
    assert ch["properties"]["kind"]["enum"] == features.CHANGE_KINDS
    assert ch["properties"]["note"]["minLength"] == 1
    assert ch["properties"]["n"]["type"] == ["integer", "null"]
    assert ch["dependentRequired"] == {"resolved": ["match"]}
    assert "if" not in ch and len(ch["allOf"]) == 3, ch
    assert ch["allOf"][2] == {"if": {"required": ["logged"]}, "then": {"required": ["commit"]}}
    for key in ("commit", "logged", "note"):
        assert "PF-1d (auto-log page changes)" in ch["properties"][key]["description"], key


# ------------------------------------------------------ autosave wiring


class FakeGit:
    """Records every argv; never runs git. git log answers with nothing."""

    def __init__(self, status):
        self.calls, self.status = [], status

    def __call__(self, argv, cwd):
        self.calls.append(list(argv))
        if argv[:2] == ["git", "status"]:
            return 0, self.status, ""
        return 0, "", ""


def _wiring():
    root = tempfile.mkdtemp(prefix="pf1d-")
    TEMPS.append(root)
    os.makedirs(os.path.join(root, "platform", "views", "viewers", "editor", "drafts"))
    os.makedirs(os.path.join(root, ".git"))
    status = " M platform/views/viewers/editor/drafts/emails-demo--demo.html\n"
    off, on = FakeGit(status), FakeGit(status)
    a = features.autosave(root, person="editor", runner=off)
    b = features.autosave(root, person="editor", runner=on, log_commits=True)
    assert a == b == "saved and shared (1 file)", (a, b)
    extra = len(on.calls) - len(off.calls)
    assert extra == 1, on.calls
    assert on.calls[0][:2] == ["git", "log"] and on.calls[0][-2:] == [
        "--", "platform/views/viewers/editor/drafts/"], on.calls[0]
    assert on.calls[extra:] == off.calls, (on.calls, off.calls)
    assert not any(c[:2] == ["git", "log"] for c in off.calls), off.calls


def _untouched():
    assert tree_hashes() == BEFORE_TREE, "a file under platform/views/viewers/ changed"


check("reference case, editor's 315a3bfeed: one auto entry n 2 with her subject, "
      "author time in UTC, sha[:10]; written, valid, nothing committed; dry_run "
      "writes nothing", _reference)
check("idempotent: a second run logs nothing and leaves the log byte-identical; "
      "a backfilled line (sha[:10], and a 7-character prefix) counts", _idempotent)
check("a commit with a manual line in its log logs nothing; one carrying only an "
      "auto line is logged", _manual_line)
check("numbers: a <head> line → n null unnumbered; an inner line → 9; a line with "
      "two numbers → 3, 37; only a retired number → unnumbered; an added line → "
      "its parent's 8; a log with no final newline", _numbers)
check("_numbers_in: on the line, innermost enclosing, multi-line start tag, void "
      "elements; the -U0 hunk reader", _numbers_in_versions)
check("skips: another person's draft, _templates/, added, deleted, the live page, "
      "a family with no list; developer's commits are not editor's", _skips)
check("a merge commit logs nothing; both sides' own commits are logged", _merge)
check("a failing git call returns what was done ([]) and writes nothing; no person → []",
      _git_failure)
check("contract: auto, unnumbered and backfill shapes validate; each defect refused "
      "by name; kind 'extra' keeps today's text", _contract)
check("the real editor log validates against the real emails-demo list (--changes exit 0)",
      _real_log)
check("a v1.1 file still refuses commit, logged and note as unknown keys", _v11_refuses)
check("the schema's change: commit, logged, note after needs; n integer or null; "
      "kind missing | unnumbered; three if/then; dependentRequired unchanged", _schema)
check("autosave(log_commits=True) hands its runner to autolog; the other git calls "
      "equal the log_commits=False run", _wiring)
check("the real tree is untouched: sha256 of every file under platform/views/viewers/",
      _untouched)

for path in TEMPS:
    shutil.rmtree(path, ignore_errors=True)
passed = sum(RESULTS)
print("%d/%d passed" % (passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
