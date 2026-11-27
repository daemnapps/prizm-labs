"""QB-5 (production contract): the generic request loop, kit/requests.py.

The shared line parses (part n and -); an old "Email request (" line maps onto the shared words through the fallback;
the loop calls a fake adapter in the order pasted and commits only the paths it reported (git seam faked).
Stdlib only, no network, no git. Run from the repo root:
    python3 components/page-features/kit/test_qb5_requests.py
"""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import requests as R  # noqa: E402  kit/requests.py (this folder first: never the PyPI package of that name)

OLD_HEAD = "Email request (components/email-production/adapter/README.md): "


class Parse(unittest.TestCase):
    def one(self, line, family=None):
        got = R.parse(line, family)
        self.assertEqual(len(got), 1, got)
        return got[0]

    def test_shared_line_with_a_part(self):
        k, why, _ = self.one("Request (fxbrand__fx-ready, part 3): picture 1: warmer light (from editor)", "emails")
        self.assertIsNone(why)
        self.assertEqual((k["id"], k["part"], k["word"], k["payload"], k["by"], k["family"]),
                         ("fxbrand__fx-ready", "3", "picture", "1: warmer light", "editor", "emails"))

    def test_shared_line_whole_piece(self):
        k, why, _ = self.one("- Request (fxbrand_email_fx-ready, part -): redo: calmer all through (from email_lead)")
        self.assertIsNone(why)
        self.assertEqual((k["id"], k["part"], k["word"], k["payload"], k["by"]),
                         ("fxbrand_email_fx-ready", "-", "redo", "calmer all through", "email_lead"))
        k, _, _ = self.one("Request (x_email_y, part 2): ok")
        self.assertEqual((k["part"], k["word"], k["payload"], k["by"]), ("2", "ok", "", None))

    def test_words_payload_is_the_json(self):
        edits = [{"path": "headline", "before": "Hello (there)", "value": "Hi"}]
        k, _, _ = self.one("Request (x_email_y, part 1): words %s (from editor)" % json.dumps(edits))
        self.assertEqual(json.loads(k["payload"]), edits)
        self.assertEqual(k["by"], "editor")

    def test_unreadable_and_other_lines(self):
        self.assertEqual(R.parse("hello\nnot a request\n"), [])
        k, why, todo = self.one("Request (no part here): ok")
        self.assertIsNone(k)
        self.assertIn("can't read", why)
        self.assertFalse(todo)

    def test_old_lines_map_onto_the_shared_words(self):
        rows = [
            ("oct-20 · P2 [fxbrand/fx-ready, section 1, picture 0] · change this picture: warmer light (from editor)",
             ("1", "picture", "0: warmer light")),
            ("oct-20 · part 2 [fxbrand/fx-ready, section 1] · this part looks right (from editor)", ("1", "ok", "")),
            ("oct-20 · part 3 [fxbrand/fx-ready, section 2] · redesign this part: calmer (from editor)", ("2", "redo", "calmer")),
            ("oct-20 · part 3 [fxbrand/fx-ready, section 2] · move this part down (from editor)", ("2", "move", "down")),
            ("oct-20 · part 3 [fxbrand/fx-ready, section 2] · move this part up (from editor)", ("2", "move", "up")),
            ("oct-20 · part 4 [fxbrand/fx-ready, section 3] · remove this part (from editor)", ("3", "remove", "")),
            ('oct-20 · part 2 [fxbrand/fx-ready, section 1] · change the words: [{"path": "sub", "value": "x"}] (from editor)',
             ("1", "words", '[{"path": "sub", "value": "x"}]')),
            ("oct-20 [fxbrand/fx-ready] · make the missing parts (from editor)", ("-", "fill", "")),
            ("oct-20 [fxbrand/fx-ready] · redo the whole email: shorter (from email_lead)", ("-", "redo", "shorter")),
        ]
        for line, (part, word, payload) in rows:
            k, why, _ = self.one(OLD_HEAD + line)
            self.assertIsNone(why, line)
            self.assertEqual((k["id"], k["family"]), ("fxbrand__fx-ready", "emails"), line)
            self.assertEqual((k["part"], k["word"], k["payload"]), (part, word, payload), line)

    def test_old_lines_that_are_not_change_words_stay_with_ask(self):
        for line in ("oct-20 [fxbrand/fx-ready] · Done: send to email_lead (from editor)",
                     "oct-20 [fxbrand/fx-ready] · make the Klaviyo draft (Go) (from email_lead)",
                     "oct-20 [fxbrand/fx-ready] · I scheduled it in Klaviyo (from email_lead)",
                     "oct-20 · P1 [fxbrand/fx-ready, section 1, picture 0] · use my own picture. My picture: (I'll drag) (from editor)"):
            k, why, todo = self.one(OLD_HEAD + line)
            self.assertIsNone(k)
            self.assertTrue(todo, line)
            self.assertIn("ask.py", why)
            self.assertIn(OLD_HEAD.strip(), why)                  # the line itself, to hand to ask.py alone


class Loop(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qb5-req-"))
        (self.tmp / "fake-adapter.json").write_text(json.dumps({
            "schema": 1, "kind": "email",
            "report": ["components/creative-queue/contract.py", "report"],
            "detail": ["components/creative-queue/contract.py", "detail"],
            "apply": ["components/creative-queue/contract.py", "fake-apply"],
            "words": ["words", "picture", "redo", "move", "remove", "ok", "note"]}))
        for fam in ("fam", "emails"):
            (self.tmp / ("%s.actions.json" % fam)).write_text(json.dumps({
                "adapter": str(self.tmp / "fake-adapter.json"), "words_reviewer": "email_lead", "words_lane": "fam-words"}))
        self.adapter_calls, self.git_calls, self.reviews = [], [], []
        self.answers = {}

        def fake_adapter(argv):
            self.adapter_calls.append(argv)
            item, word = argv[3], argv[5]
            return 0, self.answers.get((item, word)) or {
                "ok": True, "revision": "r", "message": "done", "ref": "runs/x/%s/piece.json" % item,
                "paths": ["runs/x/%s/piece.json" % item, "runs/learnings/x.jsonl"]}

        def fake_review(k, res, reviewer, lane):
            self.reviews.append((k["by"], reviewer, lane, res["ref"]))
            return "platform/data/records/review/rq-%d.json" % len(self.reviews)

        def fake_git(args, **kw):
            self.git_calls.append(list(args))
            return subprocess.CompletedProcess(args, 0, stdout="abc1234def\n", stderr="")
        self.git = fake_git
        self.saved = (R.TEMPLATES, R.call_adapter, R.file_review)
        R.TEMPLATES, R.call_adapter, R.file_review = self.tmp, fake_adapter, fake_review

    def tearDown(self):
        R.TEMPLATES, R.call_adapter, R.file_review = self.saved
        shutil.rmtree(str(self.tmp))

    def run_loop(self, text, *args):
        f = self.tmp / "pasted.txt"
        f.write_text(text, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = R.main([str(f)] + list(args), git=self.git)
        return code, out.getvalue()

    def test_calls_the_adapter_in_order_and_commits_only_its_paths(self):
        text = "\n".join([
            "Here are my changes:",
            "Request (a_email_one, part 3): picture 1: warmer light (from editor)",
            'Request (a_email_two, part 1): words [{"path": "sub", "value": "x"}] (from editor)',
            "Request (a_email_one, part -): redo: calmer (from editor)",
        ])
        code, out = self.run_loop(text, "--family", "fam")
        self.assertEqual(code, 0, out)
        self.assertEqual([(c[3], c[4], c[5]) for c in self.adapter_calls],
                         [("a_email_one", "3", "picture"), ("a_email_two", "1", "words"), ("a_email_one", "-", "redo")])
        first = self.adapter_calls[0]
        self.assertEqual(first[0], sys.executable)
        self.assertTrue(first[1].endswith("components/creative-queue/contract.py"))
        self.assertEqual(first[2:], ["fake-apply", "a_email_one", "3", "picture", "1: warmer light", "--by", "editor"])
        # the words change by editor tells the reviewer the actions file names
        self.assertEqual(self.reviews, [("editor", "email_lead", "fam-words", "runs/x/a_email_two/piece.json")])
        want = sorted(["runs/x/a_email_one/piece.json", "runs/x/a_email_two/piece.json", "runs/learnings/x.jsonl",
                       "platform/data/records/review/rq-1.json"])
        add = [c for c in self.git_calls if c[1] == "add"]
        commit = [c for c in self.git_calls if c[1] == "commit"]
        self.assertEqual(len(add), 1)
        self.assertEqual(add[0][add[0].index("--") + 1:], want)
        self.assertEqual(len(commit), 1)
        self.assertEqual(commit[0][commit[0].index("--") + 1:], want)        # by pathspec, nothing else
        self.assertIn(["git", "push"], self.git_calls)
        self.assertIn("git: shared abc1234def", out)

    def test_words_by_the_reviewer_files_no_review(self):
        code, _ = self.run_loop('Request (a_email_one, part 1): words [{"path": "sub", "value": "x"}] (from email_lead)',
                                "--family", "fam")
        self.assertEqual(code, 0)
        self.assertEqual(self.reviews, [])

    def test_old_line_goes_through_the_fallback(self):
        code, out = self.run_loop(OLD_HEAD + "oct-20 · part 3 [fxbrand/fx-ready, section 2] · move this part up (from editor)\n"
                                  + OLD_HEAD + "oct-20 [fxbrand/fx-ready] · Done: send to email_lead (from editor)")
        self.assertEqual(code, 1, out)                                   # Done is still to do, with ask.py
        self.assertEqual([c[3:] for c in self.adapter_calls], [["fxbrand__fx-ready", "2", "move", "up", "--by", "editor"]])
        self.assertIn("ask.py", out)

    def test_refused_unknown_and_unattributed_never_reach_the_adapter(self):
        text = "\n".join(["Request (a_email_one, part -): go (from email_lead)",
                          "Request (a_email_one, part 2): sparkle (from editor)",
                          "Request (a_email_one, part 2): ok"])
        code, out = self.run_loop(text, "--family", "fam")
        self.assertEqual(code, 1)
        self.assertEqual(self.adapter_calls, [])
        self.assertEqual(self.git_calls, [])
        self.assertIn("approval", out)
        self.assertIn("who asked", out)
        code, _ = self.run_loop("Request (a_email_one, part 2): ok", "--family", "fam", "--by", "editor")
        self.assertEqual(code, 0)
        self.assertEqual(self.adapter_calls[-1][-2:], ["--by", "editor"])

    def test_a_failed_apply_commits_nothing_of_its_own(self):
        self.answers[("a_email_bad", "ok")] = {"ok": False, "message": "no designed email", "paths": ["runs/x/bad.json"]}
        code, out = self.run_loop("Request (a_email_bad, part 1): ok (from editor)\nRequest (a_email_one, part 1): ok (from editor)",
                                  "--family", "fam")
        self.assertEqual(code, 1)
        add = [c for c in self.git_calls if c[1] == "add"][0]
        self.assertNotIn("runs/x/bad.json", add)
        self.assertIn("runs/x/a_email_one/piece.json", add)

    def test_dry_run_changes_nothing(self):
        code, out = self.run_loop("Request (a_email_one, part 3): picture 1: warmer (from editor)", "--family", "fam", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would run", out)
        self.assertEqual((self.adapter_calls, self.git_calls, self.reviews), ([], [], []))

    def test_family_must_be_named_when_two_exist(self):
        code, out = self.run_loop("Request (a_email_one, part 1): ok (from editor)")
        self.assertEqual(code, 1)
        self.assertIn("--family", out)
        (self.tmp / "emails.actions.json").unlink()
        code, _ = self.run_loop("Request (a_email_one, part 1): ok (from editor)")
        self.assertEqual(code, 0)                                         # the one actions file there is

    def test_nothing_readable_exits_2(self):
        code, _ = self.run_loop("just words\n")
        self.assertEqual(code, 2)

    def test_the_emails_actions_file_names_a_valid_adapter(self):
        a = json.loads((self.saved[0] / "emails.actions.json").read_text())
        m = R.contract.load(R.REPO / a["adapter"])
        self.assertEqual(m["kind"], "email")
        self.assertEqual(a["words_reviewer"], "email_lead")


if __name__ == "__main__":
    unittest.main()
