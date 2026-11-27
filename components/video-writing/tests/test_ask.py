"""The ask a video was ordered with reaches every writing pass (2026-11-03). No model is called.

The creative strategist's ask.json carries the offer lines, the never-list and the moment; a run names it in
vars/ask.md (the image and copy writing convention), and the writing passes are handed it on top."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
M = HERE.parent / "machine"
sys.path.insert(0, str(M))
sys.path.insert(0, str(HERE.parents[1] / "video-teardown" / "machine"))

import writing_v2 as W  # noqa: E402

ASK = {"ask": "promo-bf-test", "brand": "zz-brand", "funnel": "bottom: seasonal offer",
       "offer": {"lines": ["THE DEVICE starting at $46", "90-day money-back guarantee"],
                 "never": ["a code", "Cyber Monday (that is its own ad)"]},
       "moment": {"key": "black-friday", "window": "2026-11-25 to 2026-11-28", "lines": ["Black Friday"]}}


class Ask(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        self.run = self.ws / "runs" / "video-teardown" / "_work" / "piece"
        self.run.mkdir(parents=True)
        (self.run / "run.json").write_text(json.dumps({"brand": "zz-brand", "stages": {}}))
        self.ask = self.ws / "runs" / "creative-strategist" / "zz-brand" / "promo-bf-test" / "ask.json"
        self.ask.parent.mkdir(parents=True)
        self.ask.write_text(json.dumps(ASK))
        self.p = mock.patch.object(W, "WS", self.ws)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_no_ask_named_is_no_block(self):
        self.assertEqual(W.ask_record(self.run), (None, None))
        self.assertEqual(W.ask_block(self.run), "")

    def test_naming_an_ask_by_name_keeps_a_repo_relative_path_and_the_moment(self):
        st = W.name_ask(self.run, "promo-bf-test")
        ref = (self.run / "vars" / "ask.md").read_text().strip()
        self.assertEqual(ref, "runs/creative-strategist/zz-brand/promo-bf-test/ask.json")
        self.assertEqual(st["ask"]["moment"], "black-friday")
        self.assertEqual(st["ask"]["window"], "2026-11-25 to 2026-11-28")
        self.assertEqual(st["ask"]["offer_lines"], ["THE DEVICE starting at $46", "90-day money-back guarantee"])
        self.assertEqual(json.loads((self.run / "run.json").read_text())["ask"]["ask"], "promo-bf-test")

    def test_naming_an_ask_by_path_works_too(self):
        W.name_ask(self.run, str(self.ask))
        self.assertEqual((self.run / "vars" / "ask.md").read_text().strip(),
                         "runs/creative-strategist/zz-brand/promo-bf-test/ask.json")

    def test_an_ask_that_is_not_there_is_refused(self):
        with self.assertRaises(SystemExit):
            W.name_ask(self.run, "no-such-ask")
        self.assertFalse((self.run / "vars" / "ask.md").exists())

    def test_the_block_carries_the_offer_lines_the_never_list_and_the_moment(self):
        W.name_ask(self.run, "promo-bf-test")
        b = W.ask_block(self.run)
        for want in ('"THE DEVICE starting at $46"', '"90-day money-back guarantee"', "- a code",
                     "- Cyber Monday (that is its own ad)", "`black-friday`", "2026-11-25 to 2026-11-28",
                     '"Black Friday"', "Funnel: bottom: seasonal offer", "THESE WIN"):
            self.assertIn(want, b)
        self.assertTrue(b.endswith("## END OF THIS AD'S ASK\n\n"))

    def test_a_named_ask_that_cannot_be_read_stops_the_pass(self):
        (self.run / "vars").mkdir()
        (self.run / "vars" / "ask.md").write_text("runs/creative-strategist/zz-brand/gone/ask.json\n")
        with self.assertRaises(RuntimeError):
            W.ask_block(self.run)

    def test_every_pass_is_handed_the_ask_first(self):
        W.name_ask(self.run, "promo-bf-test")
        out = self.run / "stages" / "3-injection.md"
        out.parent.mkdir()
        (self.run / "prompts").mkdir()
        sent = {}

        class R:                                   # the teardown's call seam, stood in: no model is called
            PURE_TEXT, CHATTER = "", ()

            @staticmethod
            def _cli_model(m):
                return m

            @staticmethod
            def _claude_run(argv, prompt, **kw):
                sent["prompt"] = prompt
                return mock.Mock(stdout=json.dumps({"result": "INJECTION\n" + "x" * 50, "usage": {}}), stderr="")

            @staticmethod
            def now():
                return "now"

            @staticmethod
            def _clean_env():
                return {}

        with mock.patch.dict(sys.modules, {"run": R}):
            W._HAND[0] = None
            W.claude_v2("THE PASS'S OWN PROMPT", out)
        self.assertTrue(sent["prompt"].startswith("## THIS AD'S ASK — `promo-bf-test`"))
        self.assertIn("THE PASS'S OWN PROMPT", sent["prompt"])
        self.assertEqual((self.run / "prompts" / out.name).read_text(), sent["prompt"])   # the prompt on file is the one sent


if __name__ == "__main__":
    unittest.main(verbosity=2)
