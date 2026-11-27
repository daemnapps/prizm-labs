#!/usr/bin/env python3
"""Who the email is for (creative-strategist who.py) is really in the prompt that is sent: every stage that writes or
judges the words, both lanes, and the SMS. A made-up brand on disk, no model, no network.

    python3 test_who_reaches_email.py
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import email_line as E   # noqa: E402
import sms as SMS        # noqa: E402
sys.path.append(str(HERE.parent / "creative-strategist" / "tests"))
import test_who as TW    # noqa: E402  its made-up brand: acme · sore-foot · sub-01-runner
import who as W          # noqa: E402

SRC = (HERE / "email_line.py").read_text()
CARD = "my heel barks at mile two"


class Base(unittest.TestCase):
    def setUp(self):
        self.b = TW.Who("test_sub_rows_are_read")
        self.b.setUp()
        self.addCleanup(self.b.tearDown)
        self.d = Path(tempfile.mkdtemp(prefix="who-email-"))


class Stages(Base):
    def sent(self, stage, who, lane="full"):
        seen = []
        state = {"brand": "acme", "stages": {}}
        with mock.patch.object(E, "claude", lambda p, m, label=None: seen.append(p) or "out"), \
                mock.patch.object(E, "creative_qc", lambda *a, **k: {}), mock.patch.object(E, "WHO", who), \
                mock.patch.object(E, "LANE", lane), contextlib.redirect_stdout(io.StringIO()):
            E.run_stage(stage, self.d, "m", state)
        self.assertEqual((self.d / f"{stage}--sent.md").read_text(), seen[0])
        return seen[0]

    def test_every_writing_stage_of_both_lanes_is_sent_it(self):
        block, aim = E.who_aim("acme", "sore-foot", "sub-01-runner", "m/25-34/black", {"awareness": "problem-aware"})
        for lane in ("full", "fast"):
            for s in E.STAGES:
                text = self.sent(s["key"], block, lane)
                if s["group"] == "READ THE SOURCE":
                    self.assertNotIn(W.MARK, text, s["key"])
                else:
                    for x in (W.MARK, CARD, "walk without heel pain", "m/25-34/black", "problem-aware"):
                        self.assertIn(x, text, s["key"])
        self.assertEqual((aim["sub"], aim["awareness"]), ("runner", "problem-aware"))

    def test_an_email_to_everyone_says_nothing(self):
        self.assertEqual(E.who_aim("acme", None), ("", None))
        self.assertNotIn(W.MARK, self.sent("stage8", ""))

    def test_only_a_named_sub_that_is_not_there_stops(self):
        with self.assertRaises(SystemExit):
            E.who_aim("acme", "sore-foot", "nobody")
        with mock.patch.object(W, "block", side_effect=ValueError("no")), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(E.who_aim("acme", "sore-foot"), ("", None))

    def test_the_run_sets_it_at_triages_level_before_any_stage_that_writes(self):
        at = SRC.index('WHO, state["aim"] = who_aim(args.brand, args.avatar, args.sub, args.demographic, {"awareness": aw, "product": args.product})')
        self.assertLess(SRC.index("aw = (_first(AWARENESS_LINE, triage)"), at)
        self.assertLess(at, SRC.index('injection = run_stage("stage3"'))


class Sms(Base):
    def test_a_text_to_one_avatar_is_sent_it_and_a_mixed_one_is_not(self):
        pf = self.d / "p.md"
        pf.write_text("write it")
        for slot, want in (({"id": "a", "variants": [{"avatar": "sore-foot"}]}, True),
                           ({"id": "b", "avatar": "mixed", "variants": [{"avatar": "sore-foot"}, {"avatar": "other-foot"}]}, False)):
            seen = []
            with mock.patch.object(SMS, "WORKSPACE", self.d), mock.patch.object(SMS, "section_for", lambda *a: "no code"):
                SMS.write_one(dict(slot, offer="x"), "acme", {}, pf, call=lambda t: seen.append(t) or "hi {link}")
            self.assertEqual(W.MARK in seen[0], want)
            f = self.d / "runs" / "email-production" / "acme" / f"acme-{slot['id']}-sms"
            self.assertEqual(W.MARK in (f / "prompt-sent.md").read_text(), want)
            self.assertEqual(bool(json.loads((f / "sms.json").read_text())["aim"]), want)


if __name__ == "__main__":
    unittest.main()
