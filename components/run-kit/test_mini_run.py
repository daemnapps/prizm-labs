#!/usr/bin/env python3
"""The mini run filer (mini_run.py, LD-9 (mini run filer)), checked against a
fixture checkout in a temp dir — a grants file, two people, a lab_door.json
door with dry_run, a routed door, an ACCEPTS door and a plain script — with git
injected, so no real repo, remote or network is touched. The record's verdict
is held to the fields platform/workers/mini-worker/lab_run.py accepts, read
from that file with `ast`, so a drift there fails here.

    /usr/bin/python3 components/run-kit/test_mini_run.py
"""
import ast
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mini_run as M    # noqa: E402

REAL = M.find_repo(__file__)
LAB_RUN = REAL / "platform/workers/mini-worker/lab_run.py"
NOW = datetime(2026, 10, 18, 3, 7, 9, tzinfo=timezone.utc)
REQ = M.REQUESTS


def lab_run_fields():
    """(ALLOWED_FIELDS, the required tuple in plan()) read from lab_run.py by ast."""
    tree = ast.parse(LAB_RUN.read_text())
    allowed, required = None, None
    for node in tree.body:
        if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ALLOWED_FIELDS"
                                                 for t in node.targets)):
            allowed = frozenset(ast.literal_eval(node.value.args[0]))
        if isinstance(node, ast.FunctionDef) and node.name == "plan":
            for sub in ast.walk(node):
                if (isinstance(sub, ast.comprehension) and isinstance(sub.iter, ast.Tuple)
                        and "requested_by" in [getattr(e, "value", None) for e in sub.iter.elts]):
                    required = tuple(e.value for e in sub.iter.elts)
    return allowed, required


class FakeGit:
    """Answers the git calls mini_run makes; records every one. A commit by pathspec keeps the
    file's text, and a push that goes through puts it in `published` (name -> text), which
    ls-tree and show read as origin/main: LD-95 (posts off-clone) commits in a throwaway
    worktree, so a pushed record is never on the fixture's disk."""

    def __init__(self, email="alice@example.com", branch="main", rejects=0, origin=None):
        self.email, self.branch, self.rejects = email, branch, rejects
        self.origin = dict(origin or {})
        self.calls = []
        self.pending, self.published = {}, {}

    def __call__(self, args, repo):
        self.calls.append(list(args))
        cmd = args[0]
        if cmd == "config":
            return (0, self.email + "\n", "") if self.email else (1, "", "")
        if cmd == "rev-parse":
            return 0, self.branch + "\n", ""
        if cmd == "commit" and args[-2] == "--":
            path = Path(repo) / args[-1]
            if path.is_file():
                self.pending[path.name] = path.read_text()
        if cmd == "push":
            if self.rejects:
                self.rejects -= 1
                return 1, "", "! [rejected] main -> main (fetch first)"
            self.published.update(self.pending)
            self.pending = {}
            self.pushed = True
            return 0, "", ""
        if cmd == "merge-base":          # the destination check: on origin/main only once pushed
            return (0, "", "") if getattr(self, "pushed", False) else (1, "", "")
        if cmd == "ls-tree":
            names = sorted(set(self.origin) | set(self.published))
            return 0, "".join("{0}/{1}\n".format(REQ, n) for n in names), ""
        if cmd == "show":
            name = args[1].rsplit("/", 1)[1]
            if name in self.origin:
                return 0, json.dumps(self.origin[name]), ""
            if name in self.published:
                return 0, self.published[name], ""
            return 128, "", "fatal: path does not exist"
        return 0, "", ""                 # add, commit, fetch, worktree, rebase, merge-base

    def verbs(self):
        return [c[0] for c in self.calls]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def build_fixture(root):
    rows = [
        {"component": "door-one", "owner": "alice", "script": "components/door-one/lab_entry.py",
         "filers": ["*"], "ready": "runs/x"},
        {"component": "routed", "owner": "alice", "script": "components/routed/lab_entry.py",
         "filers": ["*"], "ready": "runs/x"},
        {"component": "accepts", "owner": "alice", "script": "components/accepts/lab_entry.py",
         "filers": ["alice"], "ready": "runs/x"},
        {"component": "plain", "owner": "bob", "script": "components/plain/run.py",
         "filers": ["*"], "ready": "runs/x"},
    ]
    write(root / M.GRANTS, json.dumps({"schema": "1", "_rules": [], "grants": [], "components": rows}))
    write(root / "team/people/alice/identity.json",
          json.dumps({"person": "alice", "emails": [{"address": "Alice@Example.com"}]}))
    write(root / "team/people/bob/identity.json",
          json.dumps({"person": "bob", "emails": [{"address": "bob@example.com"}]}))
    write(root / "components/door-one/lab_entry.py", "# stub door\n")
    write(root / "components/door-one/run.py", '"""door one CLI"""\n')
    write(root / "components/door-one/lab_door.json", json.dumps({
        "status": "draft", "script": "components/door-one/run.py", "subcommand": None,
        "positionals": [], "flags": {"product": "--product"},
        "bool_flags": {"dry_run": "--dry-run"}, "brand_flag": "--brand",
        "out": {"flag": "--out", "runs_root_flag": None, "run_dir": None},
        "refuse": ["upload"]}))
    route = {"script": "components/routed/chain.py", "positionals": [], "brand_flag": "--brand",
             "out": {"flag": None, "runs_root_flag": None, "run_dir": None}, "refuse": []}
    write(root / "components/routed/lab_entry.py", "# stub door\n")
    write(root / "components/routed/chain.py", '"""routed CLI"""\n')
    write(root / "components/routed/lab_door.json", json.dumps({
        "status": "draft", "script": "components/routed/chain.py", "default_route": "start",
        "routes": {
            "start": dict(route, subcommand="start", flags={"swipe": "--swipe"},
                          bool_flags={"dry_run": "--dry-run"}),
            "draft": dict(route, subcommand="draft", flags={"briefs": "--briefs"},
                          bool_flags={"no_ship": "--no-ship"}),
        }}))
    # ACCEPTS must be read without importing: the import below would fail.
    write(root / "components/accepts/lab_entry.py",
          '"""The accepts door."""\nimport no_such_module_anywhere\n\nACCEPTS = ("asof", "label")\n')
    write(root / "components/plain/run.py",
          '#!/usr/bin/python3\n"""Plain tool — does one thing.\n\nMore words here."""\n')


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="mini-run-"))
        build_fixture(self.root)
        # the fixture's doors do not run: no real RED check unless a case passes its own
        self.env_was = os.environ.get(M.NO_PREFLIGHT)
        os.environ[M.NO_PREFLIGHT] = "1"
        self.published = {}    # the fixture's origin/main, shared by every FakeGit in a case

    def tearDown(self):
        shutil.rmtree(str(self.root))
        if self.env_was is None:
            os.environ.pop(M.NO_PREFLIGHT, None)
        else:
            os.environ[M.NO_PREFLIGHT] = self.env_was

    def run_cli(self, argv, git=None, check=None):
        self.git = git or FakeGit()
        self.git.published = self.published
        self.out = []
        code = M.main(argv, repo=self.root, git=self.git, now=NOW, say=self.out.append, check=check)
        self.text = "\n".join(self.out)
        return code

    def records(self):
        """{name: text}: requests in the fixture (--no-push) and published to origin/main."""
        found = {p.name: p.read_text() for p in (self.root / REQ).glob("*.json")} \
            if (self.root / REQ).is_dir() else {}
        found.update(self.published)
        return found

    def filed(self):
        return sorted(self.records())

    def only_record(self):
        files = self.filed()
        self.assertEqual(len(files), 1, self.text)
        return Path(files[0]), json.loads(self.records()[files[0]])


class TestList(Base):
    def test_lists_every_door_kind(self):
        self.assertEqual(self.run_cli(["list"]), 0, self.text)
        t = self.text
        self.assertIn("door-one — owner alice · filers *", t)
        self.assertIn("[--product <value>] [--dry_run yes|no] --label <name>", t)
        self.assertIn("--command start  [--swipe <value>] [--dry_run yes|no]", t)
        self.assertIn("--command draft  [--briefs <value>] [--no_ship yes|no]", t)
        self.assertIn("--asof <value> --label <value>  (ACCEPTS in the script)", t)
        self.assertIn("see components/plain/run.py — Plain tool — does one thing.", t)
        self.assertNotIn("More words here", t)
        self.assertEqual(self.filed(), [])


class TestFile(Base):
    def test_person_from_email_case_insensitive(self):
        code = self.run_cli(["file", "door-one", "--brand", "b1", "--label", "one", "product=p"],
                            FakeGit(email="ALICE@example.COM"))
        self.assertEqual(code, 0, self.text)
        path, rec = self.only_record()
        self.assertEqual(path.name, "20261018T030709Z--alice--one.json")
        self.assertEqual(rec["verdict"]["requested_by"], "alice")
        self.assertEqual(rec["reviewer"], "alice")

    def test_unknown_email_refused_naming_it(self):
        code = self.run_cli(["file", "door-one", "--brand", "b1"], FakeGit(email="stranger@else.org"))
        self.assertEqual(code, 2)
        self.assertIn("stranger@else.org", self.text)
        self.assertEqual(self.filed(), [])

    def test_non_filer_refused_and_star_accepted(self):
        self.assertEqual(self.run_cli(["file", "accepts", "--brand", "b1", "asof=2026-10-16"],
                                      FakeGit(email="bob@example.com")), 2)
        self.assertIn("bob is not a filer on accepts", self.text)
        self.assertEqual(self.filed(), [])
        self.assertEqual(self.run_cli(["file", "door-one", "--brand", "b1"],
                                      FakeGit(email="bob@example.com")), 0, self.text)
        self.assertEqual(self.only_record()[1]["verdict"]["requested_by"], "bob")

    def test_not_a_row_refused(self):
        self.assertEqual(self.run_cli(["file", "nope", "--brand", "b1"]), 2)
        self.assertIn("'nope' is not a component row", self.text)

    def test_door_refusal_passes_through_exit_2(self):
        self.assertEqual(self.run_cli(["file", "door-one", "--brand", "b1", "upload=x"]), 2)
        self.assertIn("--upload is refused by this door (upload)", self.text)
        self.assertEqual(self.run_cli(["file", "door-one", "--brand", "b1", "nope=1"]), 2)
        self.assertIn("unknown argument(s) --nope", self.text)
        self.assertEqual(self.run_cli(["file", "routed", "--brand", "b1", "command=nowhere"]), 2)
        self.assertIn("'nowhere' is not a route of this door", self.text)
        self.assertEqual(self.filed(), [])

    def test_accepts_door_refuses_unknown_name(self):
        self.assertEqual(self.run_cli(["file", "accepts", "--brand", "b1", "scale=2"]), 2)
        self.assertIn("unknown argument(s) scale", self.text)

    def test_dry_run_refused_where_door_declares_none(self):
        for argv in (["file", "routed", "--brand", "b1", "--dry-run", "command=draft"],
                     ["file", "accepts", "--brand", "b1", "--dry-run"],
                     ["file", "plain", "--brand", "b1", "--dry-run"]):
            self.assertEqual(self.run_cli(argv), 2, argv)
            self.assertIn("declares no dry_run", self.text)
        self.assertEqual(self.filed(), [])

    def test_dry_run_added_where_door_declares_it(self):
        self.assertEqual(self.run_cli(["file", "routed", "--brand", "b1", "--dry-run",
                                       "--label", "r1", "command=start", "swipe=s"]), 0, self.text)
        args = self.only_record()[1]["verdict"]["args"]
        self.assertEqual(args, {"command": "start", "swipe": "s", "dry_run": "yes"})

    def test_record_shape_matches_lab_run(self):
        allowed, required = lab_run_fields()
        self.assertTrue(allowed and required, "ALLOWED_FIELDS / required tuple not found in lab_run.py")
        self.assertEqual(self.run_cli(["file", "door-one", "--brand", "b1", "--dry-run"]), 0, self.text)
        path, rec = self.only_record()
        v = rec["verdict"]
        self.assertLessEqual(set(v), allowed)
        self.assertLessEqual(set(required), set(v))
        self.assertNotIn("scheduled", v)
        label = "door-one-20261018-0307"
        self.assertEqual(v, {"action": "lab-run", "component": "door-one",
                             "script": "components/door-one/lab_entry.py",
                             "args": {"dry_run": "yes", "label": label}, "brand": "b1",
                             "out": label, "requested_by": "alice", "machine": "door-one"})
        self.assertEqual(rec["item"], label)
        self.assertEqual(rec["via"], "mini_run")
        self.assertEqual(rec["created"], "2026-10-18T03:07:09Z")
        self.assertIn("notes", rec)
        self.assertEqual(path.name.split("--")[1], "alice")

    def test_duplicate_label_refused(self):
        self.assertEqual(self.run_cli(["file", "door-one", "--brand", "b1", "--label", "same"]), 0)
        self.assertEqual(self.run_cli(["file", "plain", "--brand", "b2", "--label", "same"]), 2)
        self.assertIn("already filed label 'same'", self.text)
        self.assertEqual(len(self.filed()), 1)

    def test_print_writes_nothing(self):
        self.assertEqual(self.run_cli(["file", "door-one", "--brand", "b1", "--print"]), 0, self.text)
        self.assertEqual(self.filed(), [])
        self.assertEqual(self.git.verbs(), ["config"])
        self.assertIn('"action": "lab-run"', self.text)

    def test_no_push_commits_by_pathspec(self):
        self.assertEqual(self.run_cli(["file", "plain", "--brand", "b1", "--label", "np", "--no-push"]),
                         0, self.text)
        rel = "{0}/20261018T030709Z--alice--np.json".format(REQ)
        self.assertIn(["add", "--", rel], self.git.calls)
        commit = [c for c in self.git.calls if c[0] == "commit"]
        self.assertEqual(len(commit), 1)
        self.assertEqual(commit[0][-2:], ["--", rel])
        self.assertNotIn("push", self.git.verbs())

    def test_push_to_main(self):
        # LD-95 (posts off-clone): pushed from a throwaway worktree of origin/main, not this checkout
        self.assertEqual(self.run_cli(["file", "plain", "--brand", "b1"]), 0, self.text)
        self.assertIn(["push", "origin", "HEAD:main"], self.git.calls)
        self.assertNotIn("pull", self.git.verbs())
        self.assertFalse((self.root / REQ).exists())
        self.assertEqual(len(self.filed()), 1)

    def test_rejected_push_rebases_in_the_worktree_never_pulls(self):
        # LD-95 (posts off-clone) replaces the in-clone `pull --no-rebase` this case pinned
        with mock.patch.object(M, "PUBLISH_PAUSE_S", 0):
            self.assertEqual(self.run_cli(["file", "plain", "--brand", "b1"], FakeGit(rejects=1)), 0, self.text)
        self.assertNotIn("pull", self.git.verbs())
        self.assertEqual(self.git.verbs().count("push"), 2)
        self.assertIn(["rebase", "-q", "origin/main"], self.git.calls)
        self.assertEqual(len(self.filed()), 1)

    def test_every_push_refused_prints_the_way_by_hand(self):
        with mock.patch.object(M, "PUBLISH_PAUSE_S", 0):
            self.assertEqual(self.run_cli(["file", "plain", "--brand", "b1"],
                                          FakeGit(rejects=M.PUBLISH_ATTEMPTS)), 1)
        self.assertEqual(self.git.verbs().count("push"), M.PUBLISH_ATTEMPTS)
        self.assertNotIn("pull", self.git.verbs())
        self.assertIn("not published: ", self.text)
        self.assertIn("run the same command again", self.text)
        self.assertIn("git push origin main", self.text)
        self.assertEqual(self.filed(), [])

    def test_label_published_but_not_yet_pulled_is_refused(self):
        self.assertEqual(self.run_cli(["file", "plain", "--brand", "b1", "--label", "once"]), 0, self.text)
        self.assertEqual(self.run_cli(["file", "plain", "--brand", "b1", "--label", "once"]), 2)
        self.assertIn("already filed label 'once'", self.text)
        self.assertEqual(len(self.filed()), 1)

    def test_off_main_refused_before_writing(self):
        self.assertEqual(self.run_cli(["file", "plain", "--brand", "b1"], FakeGit(branch="topic")), 2)
        self.assertIn("'topic', not main", self.text)
        self.assertEqual(self.filed(), [])


class FakeCheck:
    """A preflight stand-in: (refuse, show) given; every call recorded."""

    def __init__(self, refuse=(), show=()):
        self.answer = (list(refuse), list(show))
        self.calls = []

    def __call__(self, repo, component, brand, args):
        self.calls.append((component, brand, dict(args)))
        return self.answer


class TestPreflightInFile(Base):
    """LD-45 (mini-run refuses on RED): the check file_run runs before it writes."""

    def test_refuse_line_refuses_writes_nothing_no_git(self):
        check = FakeCheck(refuse=["new RED: a path on this machine only (components/door-one/run.py:3): x"])
        code = self.run_cli(["file", "door-one", "--brand", "b1", "--label", "r1", "product=p"], check=check)
        self.assertEqual(code, 2, self.text)
        self.assertIn("mini_run: refused — 1 RED(s) a mini run of door-one would hit — nothing written", self.text)
        self.assertIn("components/door-one/run.py:3", self.text)
        self.assertEqual(self.filed(), [])
        self.assertEqual(self.git.verbs(), ["config"])    # only who is filing; no add, commit or push
        self.assertEqual(check.calls, [("door-one", "b1", {"product": "p", "label": "r1"})])

    def test_show_lines_are_said_and_it_files(self):
        check = FakeCheck(show=["already in the code: 1 RED(s):", "  a path on this machine only (x.py:1): y",
                                "amber: edited, not committed"])
        self.assertEqual(self.run_cli(["file", "plain", "--brand", "b1", "--label", "s1"], check=check), 0, self.text)
        self.only_record()
        for line in check.answer[1]:
            self.assertIn(line, self.out)
        self.assertLess(self.out.index("amber: edited, not committed"),
                        self.out.index("wrote {0}/20261018T030709Z--alice--s1.json".format(REQ)))
        self.assertIn(["push", "origin", "HEAD:main"], self.git.calls)

    def test_print_skips_the_check(self):
        check = FakeCheck(refuse=["new RED: would refuse"])
        self.assertEqual(self.run_cli(["file", "door-one", "--brand", "b1", "--print"], check=check), 0, self.text)
        self.assertEqual(check.calls, [])
        self.assertIn("(--print: nothing written)", self.text)

    def test_dry_run_still_checks_with_dry_run_arg(self):
        check = FakeCheck()
        self.assertEqual(self.run_cli(["file", "door-one", "--brand", "b1", "--dry-run", "--label", "d1"],
                                      check=check), 0, self.text)
        self.assertEqual(check.calls, [("door-one", "b1", {"dry_run": "yes", "label": "d1"})])

    def test_passed_check_runs_even_with_the_env_switch(self):
        check = FakeCheck(refuse=["the dry run opened ~/x"])
        self.assertEqual(self.run_cli(["file", "plain", "--brand", "b1"], check=check), 2, self.text)
        self.assertEqual(self.filed(), [])


class FakeCompare:
    """Stands in for mini_compare: trace() answers or raises, findings() answers as given."""

    def __init__(self, t=None, raises=None, found=None):
        self.t, self.raises = t, raises
        self.found = dict({"new_red": [], "old_red": [], "amber": [], "unchecked": [], "notes": []},
                          **(found or {}))
        self.traced, self.found_with = [], []

    def trace(self, root, component, brand=None, args=None):
        self.traced.append((component, brand, dict(args or {})))
        if self.raises is not None:
            raise self.raises
        return self.t

    def findings(self, root, component, trace=None):
        self.found_with.append(trace)
        out = dict(self.found)
        if trace is None:
            out.pop("trace_red", None)
        return out


OLD_REACHED = "a path on this machine only (components/c/run.py:12): HOME = '/Users/x'"
OLD_ELSEWHERE = ["local service (components/c/run.py:{0}): http://localhost:{0}".format(n) for n in range(40, 47)]


class TestDefaultPreflight(Base):
    """LD-45 (mini-run refuses on RED), REVISED: refuse only a new RED or what the dry run
    opened outside; show every RED already in the code, reached file:line first."""

    def stub(self, fake):
        was = sys.modules.get("mini_compare")
        sys.modules["mini_compare"] = fake
        self.addCleanup(lambda: sys.modules.__setitem__("mini_compare", was) if was is not None
                        else sys.modules.pop("mini_compare", None))
        return fake

    def traced(self, **found):
        return self.stub(FakeCompare(
            t={"opened": [], "absent": [], "reached": {"components/c/run.py:12"}, "exit": 0, "timed_out": False},
            found=found))

    def test_new_red_refuses(self):
        self.traced(new_red=["breaks on the mini's Python 3.9.6: components/c/new.py:3"])
        refuse, show = M.preflight(self.root, "c", "b1", {"label": "l"})
        self.assertEqual(refuse, ["new RED: breaks on the mini's Python 3.9.6: components/c/new.py:3"])
        self.assertEqual(show, [])

    def test_trace_red_refuses_and_trace_is_dry_run(self):
        fake = self.traced(trace_red=["the dry run opened ~/secret.json"])
        refuse, _ = M.preflight(self.root, "c", "b1", {"label": "l"})
        self.assertEqual(refuse, ["the dry run opened ~/secret.json"])
        self.assertEqual(fake.traced, [("c", "b1", {"label": "l", "dry_run": "yes"})])
        self.assertIs(fake.found_with[0], fake.t)

    def test_old_reds_show_reached_first_and_marked_then_count_and_five(self):
        self.traced(old_red=OLD_ELSEWHERE + [OLD_REACHED], amber=["edited, not committed — x"])
        refuse, show = M.preflight(self.root, "c", "b1", {})
        self.assertEqual(refuse, [])
        self.assertEqual(show[0], "already in the code, reached in the dry run: " + OLD_REACHED)
        self.assertEqual(show[1], "already in the code: 7 RED(s), the first 5:")
        self.assertEqual(show[2:7], ["  " + r for r in OLD_ELSEWHERE[:5]])
        self.assertNotIn("  " + OLD_ELSEWHERE[5], show)
        self.assertEqual(show[-1], "amber: edited, not committed — x")
        self.assertEqual(len(show), 8)

    def test_old_red_elsewhere_only_shows(self):
        self.traced(old_red=OLD_ELSEWHERE[:1])
        refuse, show = M.preflight(self.root, "c", "b1", {})
        self.assertEqual(refuse, [])
        self.assertEqual(show, ["already in the code: 1 RED(s):", "  " + OLD_ELSEWHERE[0]])

    def test_no_trace_only_new_red_refuses(self):
        found = {"new_red": ["shadows the standard library: components/c/json.py"],
                 "old_red": [OLD_REACHED], "trace_red": ["the dry run opened /Users/x"]}
        cases = {
            "refused": dict(raises=M.Refused("no dry run door: the trace is skipped")),
            "exit": dict(t={"opened": ["/Users/x"], "reached": {"components/c/run.py:12"}, "exit": 3}),
            "timeout": dict(t={"opened": [], "reached": set(), "exit": 124, "timed_out": True, "timeout": 240}),
        }
        for name, kw in cases.items():
            with self.subTest(name):
                fake = self.stub(FakeCompare(found=found, **kw))
                refuse, show = M.preflight(self.root, "c", "b1", {})
                self.assertEqual(refuse, ["new RED: shadows the standard library: components/c/json.py"])
                self.assertEqual(fake.found_with, [None])
                self.assertTrue(show[0].startswith("not traced: "), show)
                self.assertIn("already in the code: 1 RED(s):", show)
                self.assertNotIn("already in the code, reached in the dry run: " + OLD_REACHED, show)

    def test_refused_from_a_second_copy_of_mini_run_is_caught(self):
        # run as a script, this module is __main__ and mini_compare's `import mini_run` is another copy
        class Other(ValueError):
            pass
        was = sys.modules["mini_run"]
        sys.modules["mini_run"] = type("Copy", (), {"Refused": Other})
        try:
            self.stub(FakeCompare(raises=Other("no dry run door")))
            refuse, show = M.preflight(self.root, "c", "b1", {})
        finally:
            sys.modules["mini_run"] = was
        self.assertEqual((refuse, show), ([], ["not traced: no dry run door"]))

    def test_default_runs_from_file_without_the_env_switch(self):
        os.environ.pop(M.NO_PREFLIGHT, None)
        fake = self.traced(new_red=["breaks on the mini's Python 3.9.6: components/door-one/run.py:1"])
        self.assertEqual(self.run_cli(["file", "door-one", "--brand", "b1", "--label", "z"]), 2, self.text)
        self.assertIn("new RED: breaks on the mini's Python 3.9.6: components/door-one/run.py:1", self.text)
        self.assertEqual(self.filed(), [])
        self.assertEqual(fake.traced, [("door-one", "b1", {"label": "z", "dry_run": "yes"})])


def result(item, status, detail):
    return {"schema": 1, "kind": "workflow-requests", "reviewer": "mini-worker", "item": item,
            "verdict": {"status": status, "detail": detail}}


def lab_request(person, item):
    return {"reviewer": person, "item": item,
            "verdict": {"action": "lab-run", "requested_by": person, "out": item}}


class TestStatus(Base):
    def test_queued_without_a_worker_record(self):
        git = FakeGit(origin={"20261018T030000Z--alice--waiting.json": lab_request("alice", "waiting")})
        self.assertEqual(self.run_cli(["status", "waiting"], git), 0, self.text)
        self.assertIn("waiting: queued", self.text)
        self.assertEqual(git.calls[0], ["fetch", "origin", "main"])

    def test_newest_status_and_detail_tail(self):
        detail = "\n".join("line {0:02d}".format(i) for i in range(1, 21))
        git = FakeGit(origin={
            "20261018T030000Z--alice--r1.json": lab_request("alice", "r1"),
            "20261018T030100Z--mini-worker--r1.json": result("r1", "running", "started"),
            "20261018T030500Z--mini-worker--r1.json": result("r1", "done", detail),
        })
        self.assertEqual(self.run_cli(["status", "r1"], git), 0, self.text)
        self.assertIn("r1: done", self.text)
        self.assertIn("line 06", self.text)
        self.assertIn("line 20", self.text)
        self.assertNotIn("line 05", self.text)
        self.assertNotIn("started", self.text)

    def test_failed_run_offers_mini_debug(self):
        # LD-29 (mini-debug threads): one line after the tail, on a failed run only.
        line = ('mini-debug this run: python3 components/run-kit/mini_debug.py open --run r9 '
                '--slug r9 --ask "…"')
        git = FakeGit(origin={
            "20261018T030000Z--alice--r9.json": lab_request("alice", "r9"),
            "20261018T030500Z--mini-worker--r9.json": result("r9", "failed", "a\nexit 3"),
        })
        self.assertEqual(self.run_cli(["status", "r9"], git), 0, self.text)
        self.assertEqual(self.out[-1], line)
        self.assertEqual(self.out[-2], "  exit 3")
        self.assertEqual(self.text.count("mini-debug"), 1)
        git = FakeGit(origin={
            "20261018T030000Z--alice--r8.json": lab_request("alice", "r8"),
            "20261018T030500Z--mini-worker--r8.json": result("r8", "done", "ok"),
        })
        self.assertEqual(self.run_cli(["status", "r8"], git), 0, self.text)
        self.assertNotIn("mini-debug", self.text)

    def test_no_label_lists_this_persons_runs(self):
        git = FakeGit(origin={
            "20261018T010000Z--alice--a1.json": lab_request("alice", "a1"),
            "20261018T010100Z--mini-worker--a1.json": result("a1", "failed", "exit 1"),
            "20261018T020000Z--alice--a2.json": lab_request("alice", "a2"),
            "20261018T020000Z--bob--b1.json": lab_request("bob", "b1"),
            "20261018T020500Z--alice--other.json": {"item": "other", "verdict": {"action": "generate"}},
        })
        self.assertEqual(self.run_cli(["status"], git), 0, self.text)
        self.assertEqual(len(self.out), 2, self.text)
        self.assertTrue(self.out[0].startswith("queued") and "a2" in self.out[0], self.out)
        self.assertTrue(self.out[1].startswith("failed") and "a1" in self.out[1], self.out)
        self.assertNotIn("b1", self.text)
        self.assertNotIn("other", self.text)


class FakeTime:
    """A fake clock and sleep: each sleep advances the clock, then runs the next step
    (a function of the FakeGit) — so a run moves on between two passes of the watch."""

    def __init__(self, steps=()):
        self.t, self.steps, self.slept = 1000.0, list(steps), []

    def clock(self):
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += seconds
        if self.steps:
            self.steps.pop(0)(self.git)


class FlakyFetch(FakeGit):
    """A FakeGit whose fetch fails on the passes named (1-based)."""

    def __init__(self, fail_on=(), **kw):
        FakeGit.__init__(self, **kw)
        self.fail_on, self.fetches = set(fail_on), 0

    def __call__(self, args, repo):
        if args[0] == "fetch":
            self.calls.append(list(args))
            self.fetches += 1
            if self.fetches in self.fail_on:
                return 128, "", "fatal: unable to access origin"
            return 0, "", ""
        return FakeGit.__call__(self, args, repo)


DONE_DETAIL = ("exit 0 · components/c/lab_entry.py at abc123 · 4 file(s), 2 text file(s) mirrored "
               "· outputs stay at runs/c/b1/w1 · record platform/data/records/runs/x.json\nall good")


class TestWatch(Base):
    """LD-57 (mini-run watch): silent while queued or running, one ending, a code per outcome."""

    REQ_NAME = "20261020T120000Z--alice--w1.json"

    def put(self, stamp, status, detail="", **extra):
        def step(git):
            rec = result("w1", status, detail)
            rec["verdict"].update(extra)
            git.origin["20261020T{0}Z--mini-worker--w1.json".format(stamp)] = rec
        return step

    def watch(self, steps, argv=(), git=None):
        self.time = FakeTime(steps)
        self.git = git or FakeGit(origin={self.REQ_NAME: lab_request("alice", "w1")})
        self.time.git = self.git
        self.out = []
        code = M.main(["watch", "w1"] + list(argv), repo=self.root, git=self.git, now=NOW,
                      say=self.out.append, sleep=self.time.sleep, clock=self.time.clock)
        self.text = "\n".join(self.out)
        return code

    START = "watching w1 on origin/main every 30s, up to 90 min — one line when it ends"

    def test_queued_running_done_passes_in_one_line(self):
        nothing = lambda git: None    # noqa: E731  a pass where the run is still queued
        code = self.watch([nothing, self.put("120100", "running", "started"), nothing,
                           self.put("120500", "done", DONE_DETAIL)])
        self.assertEqual(code, 0, self.text)
        self.assertEqual(self.out, [self.START, "PASSED w1 — outputs at runs/c/b1/w1"])
        self.assertEqual(self.time.slept, [30] * 4)
        self.assertEqual(self.git.verbs().count("fetch"), 5)
        self.assertEqual(self.git.calls[0], ["fetch", "origin", "main"])

    def test_done_without_outputs_path_falls_back(self):
        code = self.watch([self.put("120500", "done", "exit 0", run_record="runs/r.json")])
        self.assertEqual((code, self.out[-1]), (0, "PASSED w1 — outputs at runs/r.json"))
        code = self.watch([self.put("120500", "done", "exit 0")])
        self.assertEqual((code, self.out[-1]), (0, "PASSED w1 — outputs at 20261020T120500Z--mini-worker--w1.json"))

    def test_running_then_failed_says_the_last_detail_line(self):
        detail = "exit 1 · components/c/lab_entry.py\nTraceback (most recent call last):\n  x\n" \
                 "KeyError: 'brand'\n\n"
        code = self.watch([self.put("120100", "running", "started"), self.put("120400", "failed", detail)])
        self.assertEqual(code, 1, self.text)
        self.assertEqual(self.out, [self.START, "FAILED w1 (failed) — KeyError: 'brand'",
                                    "say 'status' for the full reason"])

    NOISY = ["exit 1 · components/c/lab_entry.py", "real error here", "/x.py:5: FutureWarning: old",
             '  warnings.warn(eol_message.format("3.9"), FutureWarning)',
             "research-gatherer: $0.000 this run (forums cache)"]

    def test_failed_line_skips_noise_status_keeps_the_full_tail(self):
        # LD-57b (watch skips noise): the warning pair and the cost line are never quoted as the error.
        code = self.watch([self.put("120400", "failed", "\n".join(self.NOISY) + "\n")])
        self.assertEqual(code, 1, self.text)
        self.assertEqual(self.out[1], "FAILED w1 (failed) — real error here")
        self.assertEqual(self.run_cli(["status", "w1"], self.git), 0, self.text)
        self.assertEqual(self.out[1:6], ["  " + line for line in self.NOISY])

    def test_all_noise_detail_falls_back_to_the_last_line(self):
        code = self.watch([self.put("120400", "failed", "\n".join(self.NOISY[2:]) + "\n\n")])
        self.assertEqual(code, 1, self.text)
        self.assertEqual(self.out[1], "FAILED w1 (failed) — research-gatherer: $0.000 this run (forums cache)")
        self.assertEqual(M.last_line(""), "(no detail)")

    def test_every_other_status_fails(self):
        for word in ("refused", "done-unverified", "error", "something-new"):
            with self.subTest(word):
                code = self.watch([self.put("120400", word, "why\nthe reason")])
                self.assertEqual(code, 1, self.text)
                self.assertEqual(self.out[1:], ["FAILED w1 ({0}) — the reason".format(word),
                                                "say 'status' for the full reason"])

    def test_no_terminal_record_times_out(self):
        code = self.watch([self.put("120100", "running", "started")], ["--interval", "60", "--timeout", "300"])
        self.assertEqual(code, 3, self.text)
        self.assertEqual(self.out, [
            "watching w1 on origin/main every 60s, up to 5 min — one line when it ends",
            "stopped watching after 5 min — w1 still running; say 'status'"])
        self.assertEqual(self.time.slept, [60] * 5)
        code = self.watch([], ["--timeout", "60"])
        self.assertEqual((code, self.out[-1]), (3, "stopped watching after 1 min — w1 still queued; say 'status'"))

    def test_fetch_failure_said_once_and_watch_goes_on(self):
        git = FlakyFetch(fail_on=(2, 3), origin={self.REQ_NAME: lab_request("alice", "w1")})
        code = self.watch([lambda g: None, lambda g: None, self.put("120500", "done", DONE_DETAIL)], git=git)
        self.assertEqual(code, 0, self.text)
        self.assertEqual(self.out, [
            self.START,
            "git fetch failed (fatal: unable to access origin) — still watching, reading origin/main as last fetched",
            "PASSED w1 — outputs at runs/c/b1/w1"])

    def test_interval_below_one_refused(self):
        code = self.watch([], ["--interval", "0"])
        self.assertEqual(code, 2, self.text)
        self.assertIn("mini_run: refused — --interval must be at least 1 second", self.text)
        self.assertEqual(self.git.calls, [])


if __name__ == "__main__":
    unittest.main()
