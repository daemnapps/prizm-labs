#!/usr/bin/env python3
"""Every language query of a video run asks at the run's own awareness level (the owner, 2026-10-27: "awareness levels
and verbatims and spice are the foundation of what we're doing here") — not only the hook stage of a Variation
branch — and a failed or empty query is said on stderr, never only inside the prompt. No model, no network.

    python3 test_language_awareness.py
"""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C                                            # noqa: E402

_s = importlib.util.spec_from_file_location("td_run_language_awareness", HERE / "run.py")
R = importlib.util.module_from_spec(_s); _s.loader.exec_module(R)


class FakeL:
    def __init__(self, txt="# rows\n- [language_a1] \"a line\"", boom=None):
        self.txt, self.boom, self.calls = txt, boom, []

    def for_stage(self, *a, **kw):
        self.calls.append((a, kw))
        if self.boom:
            raise self.boom
        return self.txt


def ask(src, outputs, fake):
    err = io.StringIO()
    with mock.patch.dict(sys.modules, {"language": fake}), \
            mock.patch.object(C, "shown_counts", lambda *_: {}), contextlib.redirect_stderr(err):
        got = C.resolve_source(src, "brand-x", outputs)
    return got, err.getvalue()


class RunLevel(unittest.TestCase):
    def test_the_market_state_level_wins(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "doctrine.json").write_text(json.dumps({"awareness": {"entry": "unaware"}}))
            st = {"market_state": {"awareness": "problem-aware"}}
            self.assertEqual(R.awareness_level(d, st), "problem-aware")

    def test_the_swipe_entry_level_when_1b_named_none(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "doctrine.json").write_text(json.dumps({"awareness": {"entry": "solution-aware", "exit": "x"}}))
            self.assertEqual(R.awareness_level(d, {}), "solution-aware")

    def test_no_level_and_not_a_level(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(R.awareness_level(d, {}))
            self.assertIsNone(R.awareness_level(d, {"market_state": {"awareness": "[UNCLEAR: which]"}}))

    def test_run_stage_puts_it_in_every_stage_pack(self):
        src = (HERE / "run.py").read_text()
        self.assertIn('pack["_awareness"] = awareness_level(d, st)', src)


class Query(unittest.TestCase):
    def test_every_stage_asks_at_the_run_level_not_only_hooks(self):
        for stage in ("injection", "expansion", "close", "hooks", "spice"):
            fake = FakeL()
            (txt, origin), _ = ask("?" + stage, {"_avatar": "av-1", "_awareness": "problem-aware"}, fake)
            (args, kw), = fake.calls
            self.assertEqual(args[2], "av-1", stage)
            self.assertEqual(kw["awareness"], "problem-aware", stage)
            self.assertEqual(kw["used"], "fresh", stage)
            self.assertIn("problem-aware", origin)

    def test_a_variation_target_still_outranks_the_run_level(self):
        fake = FakeL()
        ask("?hooks", {"_avatar": "av-1", "_awareness": "problem-aware", "target_awareness": "unaware branch"}, fake)
        self.assertEqual(fake.calls[0][1]["awareness"], "unaware")

    def test_a_failed_query_is_said_on_stderr(self):
        (txt, origin), err = ask("?hooks", {"_avatar": "av-1"}, FakeL(boom=RuntimeError("bank gone")))
        self.assertIn("LANGUAGE QUERY FAILED", err)
        self.assertIn("bank gone", txt)
        self.assertIn("failed", origin)

    def test_an_empty_query_is_said_on_stderr(self):
        (txt, origin), err = ask("?hooks", {"_avatar": "av-1"},
                                 FakeL("(no rows matched — say so rather than inventing one)"))
        self.assertIn("LANGUAGE QUERY EMPTY", err)
        self.assertIn("NO ROWS", origin)


if __name__ == "__main__":
    unittest.main(verbosity=2)
