#!/usr/bin/env python3
"""The research packet's language section asks at the run's awareness level (2026-10-27) and says an empty or
failed query on stderr. No network, no model.

    python3 components/research-gatherer/test_language_awareness.py
"""
import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import research_gatherer.engine as R  # noqa: E402


def profile(answer):
    calls = []

    def for_stage(*a, **kw):
        calls.append((a, kw))
        if isinstance(answer, Exception):
            raise answer
        return answer
    return {"language_stages": ["depth", "spice"], "language_for_stage": for_stage}, calls


class LanguageSection(unittest.TestCase):
    def test_the_level_reaches_every_stage_query(self):
        cp, calls = profile("# rows\n- [language_a1] \"a line\"")
        R.render_language_md("brand-x", "av-1", cp, awareness="problem-aware")
        self.assertEqual([a[1] for a, _ in calls], ["depth", "spice"])
        self.assertTrue(all(kw == {"awareness": "problem-aware"} for _, kw in calls))
        self.assertTrue(all(a[2] == "av-1" for a, _ in calls))

    def test_no_level_keeps_the_old_call(self):
        cp, calls = profile("# rows")
        R.render_language_md("brand-x", "av-1", cp)
        self.assertTrue(all(kw == {} for _, kw in calls))

    def test_empty_and_failed_are_said(self):
        for answer, word in (("(no rows matched — say so rather than inventing one)", "returned no rows"),
                             (RuntimeError("bank gone"), "failed")):
            cp, _ = profile(answer)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                R.render_language_md("brand-x", "av-1", cp, awareness="unaware")
            self.assertIn(word, err.getvalue())

    def test_the_run_level_is_read_off_the_audience_or_the_market_state(self):
        src = (HERE / "research_gatherer" / "engine.py").read_text()
        self.assertIn('aud.get("_awareness")', src)
        self.assertIn('(st.get("market_state") or {}).get("awareness")', src)
        self.assertIn("render_language_md(brand, avatar, chain_profile, funnel, topics, awareness=awareness)", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
