#!/usr/bin/env python3
"""PF-19b (catch up): `features.py catchup <family>` makes a NEW draft of today's template and says which of three
cases the person's live page is in; `catchup-mark` records each replayed change's outcome.

    python3 components/page-features/test_pf19b_catch_up.py

    (b) changes to replay: a live page with three logged changes on an old template — all three are planned in
        order, replayed through features.change (the /page-change route) onto the new draft and marked applied;
        the draft goes live with go_live as today; a later catch-up replays the three once, never their replays
    skipped: a change whose anchor today's template removed, and one whose number left the list, are skipped
        with the why; a line with no number needs a person
    (c) hand edits: an empty log on a page that differs from what going live made routes to compare, with the
        differences, and writes no plan; no recorded base routes there too
    (a) no changes: an empty log on a page that IS what going live made from its (old) base says so
    refusals write nothing; the live page, its logs and the existing drafts are never written; the CLI is wired;
    the real platform/views/viewers tree is untouched

Every fixture is built here, in a temp git repo (the base template is read back with `git cat-file`); add,
commit, push and pull are recorded, never run. Stdlib only, Python 3.9, no network.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import draft  # noqa: E402
import features  # noqa: E402
import live  # noqa: E402

PV = draft._pv()
PERSON = "tess"
V = "platform/views/viewers/"
TPL = V + "_templates/"
LIVE_PAGE = V + "tess/alpha.html"
LIVE_LOG = V + "tess/alpha.changes.jsonl"
RECORD = V + "tess/alpha.live.jsonl"
OLD_DRAFT = V + "tess/drafts/alpha--old.html"
NEW_DRAFT = V + "tess/drafts/alpha--catchup-20261029.html"
PLAN = V + "tess/drafts/alpha--catchup-20261029.catchup.json"
NOW = "2026-10-29T12:00:00Z"
OVERLAY = "%s\n<script>/* overlay */</script>\n%s" % (live.OVERLAY_START, live.OVERLAY_END)
PAGE = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>alpha</title>\n</head>\n'
        '<body>\n%s\n' + OVERLAY + '\n</body>\n</html>\n')
PARTS = {1: '<h1 data-feature="1">alpha</h1>', 2: '<p data-feature="2">the list</p>',
         3: '<p data-feature="3">the footer</p>', 4: '<p data-feature="4">a new column</p>'}
KINDS = dict((kind, {"letter": letter, "name": kind, "means": "the %s kind" % kind})
             for kind, letter in features.KINDS.items())
STATE_WORDS = dict((word, "the %s state" % word) for word in features.STATE_WORDS)
CHANGES = [{"n": 1, "said": "make the title bigger", "at": "2026-10-23T09:00:00Z", "by": PERSON,
            "route": "claude-code"},
           {"n": 2, "said": "sort the list by date", "at": "2026-10-23T09:05:00Z", "by": PERSON,
            "route": "claude-code"},
           {"n": 3, "said": "drop the footer's second line", "at": "2026-10-23T09:10:00Z", "by": PERSON,
            "route": "claude-code"}]


def tree_hashes(top):
    out = {}
    for base, _, names in os.walk(top):
        for name in names:
            path = os.path.join(base, name)
            with open(path, "rb") as handle:
                out[os.path.relpath(path, top)] = hashlib.sha256(handle.read()).hexdigest()
    return out


REAL_BEFORE = tree_hashes(os.path.join(REPO, V))


def page(*numbers):
    return PAGE % "\n".join(PARTS[n] for n in numbers)


def family(*numbers):
    return {"schema": 1, "schema_minor": 2, "title": "alpha", "status": "draft", "page": TPL + "alpha.html",
            "kinds": KINDS, "state_words": STATE_WORDS,
            "features": [{"n": n, "name": "part %d" % n, "kind": "layout", "state": "wired", "status": "draft",
                          "source": None, "anchor": str(n)} for n in numbers]}


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as handle:
        return handle.read()


def jsonl(objs):
    return "".join(json.dumps(o) + "\n" for o in objs)


def git(root, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@x.test", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@x.test")
    proc = subprocess.run(["git", "-C", root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, env=env)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


class Git(object):
    """Real git for reads (cat-file); add / commit / push / pull are recorded and never run."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, cwd):
        self.calls.append(list(argv))
        if argv[1] in ("add", "commit", "push", "pull"):
            return 0, "", ""
        return features.run_git(argv, cwd)

    def verbs(self):
        return [c[1] for c in self.calls]


class CatchUp(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pf19b-")
        self.addCleanup(shutil.rmtree, self.root, True)
        git(self.root, "init", "-q")

    # --- fixtures ------------------------------------------------------------------------------------------

    def old_template(self, *numbers):
        """The template tess's page was cut from, committed; its blob."""
        write(self.root, TPL + "alpha.html", page(*numbers))
        write(self.root, TPL + "alpha.features.json", features.dumps(family(*numbers)))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "alpha: the old template")
        return live.blob_id(os.path.join(self.root, TPL + "alpha.html"))

    def new_template(self, html_numbers, list_numbers):
        write(self.root, TPL + "alpha.html", page(*html_numbers))
        write(self.root, TPL + "alpha.features.json", features.dumps(family(*list_numbers)))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "alpha: today's template")

    def went_live(self, base, text, log, from_log=None, record=True):
        """Tess's live page, its change log, the old draft it came from and its live.jsonl line."""
        write(self.root, LIVE_PAGE, text)
        write(self.root, LIVE_LOG, jsonl(log))
        write(self.root, OLD_DRAFT, "<!-- the old draft -->\n")
        write(self.root, live._log_rel(OLD_DRAFT), jsonl(from_log or []))
        if record:
            write(self.root, RECORD, jsonl([{"kind": "live", "at": "2026-10-23T10:00:00Z", "by": PERSON,
                                             "from": OLD_DRAFT, "base": base, "old": None,
                                             "changes": len(log)}]))
        self.kept = dict((rel, read(self.root, rel)) for rel in
                         (LIVE_PAGE, LIVE_LOG, OLD_DRAFT, live._log_rel(OLD_DRAFT))
                         + ((RECORD,) if record else ()))

    def assert_kept(self):
        for rel, text in self.kept.items():
            self.assertEqual(read(self.root, rel), text, "%s was written" % rel)

    def run_catchup(self, **kw):
        runner = kw.pop("runner", None) or Git()
        return draft.catch_up("alpha", person=PERSON, root=self.root, runner=runner, now=NOW, **kw), runner

    def mark(self, step, state, **kw):
        return draft.catchup_mark(NEW_DRAFT, step, state, person=PERSON, root=self.root, runner=Git(),
                                  now=NOW, **kw)

    def plan(self):
        return json.loads(read(self.root, PLAN))

    def three_changes_on_old_template(self):
        base = self.old_template(1, 2, 3)
        live_text = live.transform(PV.personal_text(page(1, 2, 3), "alpha", base)).replace(
            "alpha</h1>", "ALPHA</h1>")
        self.went_live(base, live_text, CHANGES)
        self.new_template((1, 2, 3, 4), (1, 2, 3, 4))
        return base

    # --- (b) changes to replay -----------------------------------------------------------------------------

    def test_three_changes_replay_onto_the_new_template(self):
        self.three_changes_on_old_template()
        result, runner = self.run_catchup()
        self.assertEqual(result["result"], "catch-up", result["lines"])
        self.assertEqual(result["case"], draft.CASE_REPLAY)
        self.assertEqual(result["draft"], NEW_DRAFT)
        self.assertEqual(result["written"], [NEW_DRAFT, live._log_rel(NEW_DRAFT), PLAN])
        today = read(self.root, TPL + "alpha.html")
        self.assertEqual(read(self.root, NEW_DRAFT), PV.personal_text(
            today, "alpha", live.blob_id(os.path.join(self.root, TPL + "alpha.html"))), "not today's template")
        self.assertEqual(read(self.root, live._log_rel(NEW_DRAFT)), "")
        plan = self.plan()
        self.assertEqual(plan["source"], LIVE_LOG)
        self.assertEqual([(e["step"], e["n"], e["said"], e["by"], e["at"], e["state"]) for e in plan["changes"]],
                         [(i + 1, c["n"], c["said"], c["by"], c["at"], "todo") for i, c in enumerate(CHANGES)])
        for i, c in enumerate(CHANGES):
            self.assertIn("  %d. [todo] n %d · %s · by tess · %s" % (i + 1, c["n"], c["said"], c["at"]),
                          result["lines"])
        self.assertIn(draft.SAY_REPLAY % NEW_DRAFT, result["lines"])
        self.assertEqual([v for v in runner.verbs() if v in ("add", "commit", "push")], ["add", "commit", "push"])
        self.assertEqual(runner.calls[-3][3:], result["written"])
        self.assert_kept()
        # The replay, one change at a time through features.change (the /page-change route), in order.
        for e in plan["changes"]:
            refused = self.mark(e["step"], "applied")
            self.assertEqual(refused["result"], "refused", "applied before /page-change logged it")
            self.assertIn("replay step %d through /page-change first" % e["step"], refused["lines"][0])
            said = features.change(NEW_DRAFT, e["n"], e["said"], person=PERSON, root=self.root, runner=Git(),
                                   now=NOW)
            self.assertEqual(said, "saved and shared")
            marked = self.mark(e["step"], "applied")
            self.assertEqual(marked["result"], "marked", marked["lines"])
        self.assertEqual([e["state"] for e in self.plan()["changes"]], ["applied"] * 3)
        self.assertEqual([e["replay"]["said"] for e in self.plan()["changes"]], [c["said"] for c in CHANGES])
        self.assertIn(draft.SAY_DONE, marked["lines"])
        status = draft.catchup_status("alpha", person=PERSON, root=self.root)
        self.assertIn("3 changes: 3 applied · 0 skipped · 0 need a person · 0 to do", status["lines"])
        self.assert_kept()
        # The person puts it live with /page-live as today.
        went = live.go_live(NEW_DRAFT, person=PERSON, root=self.root, runner=Git(), now="2026-10-29T13:00:00Z")
        self.assertEqual(went["result"], "live", went["lines"])
        self.assertEqual(read(self.root, LIVE_PAGE), live.transform(read(self.root, NEW_DRAFT)))
        self.assertEqual(len(features.read_changes(os.path.join(self.root, LIVE_LOG))), 6)
        # A later catch-up replays the three changes once, never the replays going live carried over.
        self.new_template((1, 2, 3), (1, 2, 3))
        again, _ = self.run_catchup()
        self.assertEqual(again["case"], draft.CASE_REPLAY, again["lines"])
        self.assertEqual([e["said"] for e in again["changes"]], [c["said"] for c in CHANGES])
        self.assertEqual([e["at"] for e in again["changes"]], [c["at"] for c in CHANGES])

    def test_a_removed_anchor_is_skipped(self):
        base = self.old_template(1, 2, 3)
        log = CHANGES + [{"n": 3, "said": "and bold it", "at": "2026-10-23T09:20:00Z", "by": PERSON,
                          "route": "claude-code"}, {"said": "no number here", "at": "2026-10-23T09:30:00Z"}]
        self.went_live(base, live.transform(PV.personal_text(page(1, 2, 3), "alpha", base)), log)
        self.new_template((1, 3), (1, 2))          # 2's anchor left the template; 3 left the list
        result, _ = self.run_catchup()
        self.assertEqual(result["case"], draft.CASE_REPLAY, result["lines"])
        got = [(e["n"], e["state"], e["why"]) for e in result["changes"]]
        self.assertEqual(got, [
            (1, "todo", None),
            (2, "skipped", "number 2's place is gone from today's template"),
            (3, "skipped", "number 3 is not on today's list (removed or retired)"),
            (3, "skipped", "number 3 is not on today's list (removed or retired)"),
            (None, "needs-a-person", "the change names no number")])
        self.assertIn("     why: number 2's place is gone from today's template", "\n".join(result["lines"]))
        self.assertIn("5 changes: 0 applied · 3 skipped · 1 need a person · 1 to do", "\n".join(result["lines"]))
        self.assert_kept()

    def test_the_from_drafts_log_when_the_live_log_is_empty(self):
        base = self.old_template(1, 2, 3)
        self.went_live(base, live.transform(PV.personal_text(page(1, 2, 3), "alpha", base)), [],
                       from_log=CHANGES[:2])
        self.new_template((1, 2, 3, 4), (1, 2, 3, 4))
        result, _ = self.run_catchup()
        self.assertEqual(result["case"], draft.CASE_REPLAY, result["lines"])
        self.assertEqual(self.plan()["source"], live._log_rel(OLD_DRAFT))
        self.assertEqual([e["n"] for e in result["changes"]], [1, 2])

    # --- (c) hand edits ---------------------------------------------------------------------------------------

    def test_an_empty_log_on_a_hand_edited_page_routes_to_compare(self):
        base = self.old_template(1, 2, 3)
        went = live.transform(PV.personal_text(page(1, 2, 3), "alpha", base))
        self.went_live(base, went.replace("</h1>", "</h1>\n<p>edited by hand</p>"), [])
        self.new_template((1, 2, 3, 4), (1, 2, 3, 4))
        result, runner = self.run_catchup()
        self.assertEqual(result["case"], draft.CASE_HAND, result["lines"])
        self.assertIn(draft.SAY_HAND, result["lines"])
        self.assertIn("/page-compare", draft.SAY_HAND)
        self.assertIn("compare: %s with %s" % (LIVE_PAGE, NEW_DRAFT), result["lines"])
        self.assertEqual(result["diff"]["lines"], 1)
        self.assertEqual(result["diff"]["spots"], ["line 9 added: <p>edited by hand</p>"])
        self.assertIsNone(result["plan"])
        self.assertFalse(os.path.exists(os.path.join(self.root, PLAN)), "a plan for a hand-edited page")
        self.assertIn(["git", "cat-file", "blob", base], runner.calls)
        self.assert_kept()

    def test_no_recorded_base_routes_to_compare(self):
        base = self.old_template(1, 2, 3)
        self.went_live(base, live.transform(PV.personal_text(page(1, 2, 3), "alpha", base)), [], record=False)
        result, _ = self.run_catchup()
        self.assertEqual(result["case"], draft.CASE_HAND, result["lines"])
        self.assertIn("cannot be shown unchanged: no base template is recorded", "\n".join(result["lines"]))
        self.assertIsNone(result["diff"])

    # --- (a) no changes -----------------------------------------------------------------------------------------

    def test_an_unchanged_page_on_an_old_base_has_nothing_to_replay(self):
        base = self.old_template(1, 2, 3)
        self.went_live(base, live.transform(PV.personal_text(page(1, 2, 3), "alpha", base)), [])
        self.new_template((1, 2, 3, 4), (1, 2, 3, 4))
        result, runner = self.run_catchup()
        self.assertEqual(result["case"], draft.CASE_NONE, result["lines"])
        self.assertIn(draft.SAY_NONE, result["lines"])
        self.assertIn("make this draft live", draft.SAY_NONE)
        self.assertIn(["git", "cat-file", "blob", base], runner.calls)
        self.assertEqual(result["written"], [NEW_DRAFT, live._log_rel(NEW_DRAFT)])
        self.assertIn(PARTS[4], read(self.root, NEW_DRAFT))
        self.assert_kept()

    # --- refusals, marks, the CLI --------------------------------------------------------------------------------

    def test_refusals_write_nothing(self):
        self.old_template(1, 2, 3)
        before = tree_hashes(self.root)
        for name, words in (("alpha", "you have no live alpha page"), ("beta", "beta is not a page family"),
                            ("Alpha Page", "is not a family name")):
            result = draft.catch_up(name, person=PERSON, root=self.root, runner=Git(), now=NOW)
            self.assertEqual(result["result"], "refused", result)
            self.assertIn(words, result["lines"][0])
        self.assertEqual(tree_hashes(self.root), before, "a refusal wrote something")
        write(self.root, LIVE_PAGE, page(1).replace("<title>", live.PREPARED_META + "\n<title>"))
        before = tree_hashes(self.root)
        result, runner = self.run_catchup()
        self.assertIn("is prepared, not yet opened", result["lines"][0])
        self.assertEqual(runner.verbs(), [])
        self.assertEqual(tree_hashes(self.root), before, "a refusal wrote something")

    def test_marks(self):
        self.three_changes_on_old_template()
        self.run_catchup()
        before = read(self.root, PLAN)
        for args, words in (((9, "skipped"), "has no step 9"), ((1, "done"), "'done' is not one of"),
                            ((1, "todo"), "'todo' is not one of")):
            result = self.mark(*args)
            self.assertEqual(result["result"], "refused", result)
            self.assertIn(words, result["lines"][0])
        other = draft.catchup_mark(NEW_DRAFT, 1, "skipped", person="editor", root=self.root, runner=Git())
        self.assertIn("is tess's draft, not editor's", other["lines"][0])
        none = draft.catchup_mark(OLD_DRAFT, 1, "skipped", person=PERSON, root=self.root, runner=Git())
        self.assertIn("has no catch-up plan", none["lines"][0])
        self.assertEqual(read(self.root, PLAN), before, "a refused mark wrote the plan")
        marked = self.mark(2, "needs-a-person", why="the list has two sorts now")
        self.assertEqual(marked["result"], "marked")
        self.assertEqual(marked["lines"][0], "step 2 (n 2): needs-a-person — the list has two sorts now")
        entry = self.plan()["changes"][1]
        self.assertEqual((entry["state"], entry["why"], entry["marked"], entry["marked_by"]),
                         ("needs-a-person", "the list has two sorts now", NOW, PERSON))
        self.assertNotIn(draft.SAY_DONE, marked["lines"])
        self.assertEqual(marked["shared"], "shared")
        self.assert_kept()

    def test_cli(self):
        self.assertIs(features.SUBCOMMANDS.get("catchup"), features._main_catchup)
        self.assertIs(features.SUBCOMMANDS.get("catchup-mark"), features._main_catchup_mark)
        self.assertIn("features.py catchup <family>", features.USAGE)
        self.assertIn("features.py catchup-mark <draft page> <step>", features.USAGE)
        self.three_changes_on_old_template()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = draft.main_catchup(["alpha", "--person", PERSON, "--json", "--no-share"], root=self.root,
                                      runner=Git(), now=NOW)
        self.assertEqual(code, 0, out.getvalue())
        result = json.loads(out.getvalue())
        self.assertEqual((result["case"], result["shared"], len(result["changes"])),
                         (draft.CASE_REPLAY, "not shared", 3))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = draft.main_catchup(["alpha", "--status", "--person", PERSON], root=self.root, runner=Git())
        self.assertEqual(code, 0)
        self.assertTrue(out.getvalue().startswith("plan: %s · draft %s" % (PLAN, NEW_DRAFT)), out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(draft.main_mark([NEW_DRAFT, "3", "skipped", "--why", "x", "--person", PERSON,
                                              "--no-share"], root=self.root, runner=Git(), now=NOW), 0)
            self.assertEqual(draft.main_catchup(["beta", "--status", "--person", PERSON], root=self.root,
                                                runner=Git()), 2)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(draft.main_mark([NEW_DRAFT, "1", "maybe"], root=self.root, runner=Git()), 2)
        self.assertEqual(self.plan()["changes"][2]["state"], "skipped")


class RealTree(unittest.TestCase):

    def test_zz_the_real_viewers_tree_is_untouched(self):
        self.assertEqual(tree_hashes(os.path.join(REPO, V)), REAL_BEFORE, "the real viewers tree changed")


if __name__ == "__main__":
    unittest.main()
