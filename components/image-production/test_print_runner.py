#!/usr/bin/env python3
"""The 3D print runner (print_runner.py): each open request through the skill, headless, one print each, held to a cap
read off the account's own spend; nothing runs without the go. The skill and the account are faked; nothing is called.

    python3 components/image-production/test_print_runner.py
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import print_runner as PR  # noqa: E402


class Runner(unittest.TestCase):
    REQS = [{"id": "b-run-s1-f1", "resume": {"run": "b_run"}}, {"id": "b-run-s2-f1", "resume": {"run": "b_run"}},
            {"id": "other", "resume": {"run": "x"}}, {"id": "b-run-s3-f1", "printing": {"sent_at": "t"}}]

    def test_only_this_runs_open_requests_not_already_printing(self):
        q = mock.MagicMock()
        q.open_requests.return_value = self.REQS
        with mock.patch.object(PR, "queue", lambda: q):
            self.assertEqual([r["id"] for r in PR.waiting("b", run="b_run")], ["b-run-s1-f1", "b-run-s2-f1"])

    def fake_queue(self, prints_on_ask=True):
        """A queue whose request gains a print record when the skill is asked for it (a print was sent)."""
        recs = {r["id"]: dict(r) for r in self.REQS}
        q = mock.MagicMock()
        q.read.side_effect = lambda brand, rid: recs.get(rid)
        q.open_requests.return_value = list(recs.values())
        return q, recs

    def test_each_request_goes_to_the_skill_once_and_its_report_is_read(self):
        q, recs = self.fake_queue()
        asked = []

        def ask(prompt):
            asked.append(prompt)
            rid = "b-run-s1-f1" if "b-run-s1-f1" in prompt else "b-run-s2-f1"
            recs[rid]["printing"] = {"generation": "g-" + rid}
            return 'built and printed\n{"request": "x", "printed": true, "kept": true, "note": "label right"}'
        with mock.patch.object(PR, "queue", lambda: q):
            res = PR.clear("b", self.REQS[:2], cap=10, ask=ask, spent=lambda s: 184.5)
        self.assertEqual(len(asked), 2)
        self.assertIn("ONE print only", asked[0])
        self.assertIn("b-run-s1-f1", asked[0])
        self.assertTrue(res["requests"]["b-run-s1-f1"]["kept"])
        self.assertEqual(res["spent"], 5.0)                    # its own two prints, not the account's 184.5
        self.assertEqual(res["account_spent"], 184.5)

    def test_the_cap_counts_only_this_runners_own_prints(self):
        q, recs = self.fake_queue()

        def ask(prompt):
            for rid in recs:
                if rid in prompt:
                    recs[rid]["printing"] = {"generation": "g-" + rid}
            return '{"printed": true, "kept": false}'
        with mock.patch.object(PR, "queue", lambda: q):
            res = PR.clear("b", self.REQS[:2], cap=4, ask=ask, spent=lambda s: 500.0)
        self.assertEqual(list(res["requests"]), ["b-run-s1-f1"])        # 2.5 spent, the next would pass 4
        self.assertIn("by this runner", res["stopped"])

    def test_a_print_already_sent_is_read_back_and_filed_never_sent_again(self):
        q, recs = self.fake_queue()
        asked = []
        with mock.patch.object(PR, "queue", lambda: q):
            self.assertEqual([r["id"] for r in PR.sent("b", only=["b-run-s3-f1"])], ["b-run-s3-f1"])
            res = PR.clear("b", [], cap=10, ask=lambda p: asked.append(p) or '{"printed": true, "kept": true}',
                           spent=lambda s: 0.0, finish=[recs["b-run-s3-f1"]])
        self.assertIn("NEVER print again", asked[0])
        self.assertEqual(res["spent"], 0.0)

    def test_nothing_runs_without_the_go_and_a_cap(self):
        q = mock.MagicMock()
        q.open_requests.return_value = self.REQS[:1]
        with mock.patch.object(PR, "queue", lambda: q), mock.patch.object(PR, "clear", lambda *a, **k: self.fail("ran")):
            self.assertEqual(PR.main(["--brand", "b"]), 2)
            self.assertEqual(PR.main(["--brand", "b", "--yes"]), 2)
            self.assertEqual(PR.main(["--brand", "b", "--dry-run"]), 0)

    def test_a_reply_with_no_json_is_said_not_passed(self):
        self.assertFalse(PR.report_of("it broke")["kept"])
        self.assertIn("no report", PR.report_of("it broke")["note"])


if __name__ == "__main__":
    unittest.main()
