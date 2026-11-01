"""image-edit — the approval-page learnings ride INSIDE the 700-char band
(SI-144 (learnings in band), image-edit#20).

`engine._learnings` keeps the header plus as many digest lines, newest first,
as `discipline.fits` allows; the block is counted raw; a failed hook says so
once on stderr and in the record. A fake learnings module goes in through
`load=`, so nothing here reads Drive, a key or the network.

    /usr/bin/python3 tools/image-edit/tests/test_learnings_band.py
"""
import contextlib
import io
import os
import re
import sys
import tokenize
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))
sys.path.append(str(HERE.parent / "image-production"))
from image_edit import discipline as D, engine as E  # noqa: E402

ENGINE = HERE / "image_edit" / "engine.py"
HEAD = "Avoid these:"       # a short header, so a 600-char instruction leaves room for some lines


def fake(lines, head=HEAD):
    """A learnings module whose prompt_block is shaped exactly as learnings.py
    builds it: two blank lines, the header, the lines, a closing newline."""
    block = ("\n\n" + head + "\n" + "\n".join(lines) + "\n") if lines else ""
    return lambda: SimpleNamespace(prompt_block=lambda tool, step, brand: block)


def rec(n):
    text = "a" * n
    return {"brand": "zz-test-brand", "instruction": text, "chars": len(text)}


def forty(i):
    return f"- line {i} " + "x" * (40 - len(f"- line {i} "))


class TestLearningsBand(unittest.TestCase):

    def test_i_an_empty_block_changes_nothing(self):
        r = rec(600)
        before = dict(r)
        E._learnings(r, load=fake([]))
        self.assertEqual(r, before)
        self.assertNotIn("learnings", r)

    def test_i_the_real_hook_switched_off_changes_nothing(self):
        # The default by-path load of components/meta-upload/learnings.py, its
        # switch forced off: what every edit does today, byte for byte.
        r = rec(600)
        before = dict(r)
        with mock.patch.dict(os.environ, {"META_LEARNINGS_HOOKS": ""}):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                E._learnings(r)
        self.assertEqual(r, before)
        self.assertEqual(err.getvalue(), "")

    def test_ii_only_the_lines_that_fit_are_kept_in_order(self):
        lines = [forty(i) for i in range(8)]
        self.assertTrue(all(len(x) == 40 for x in lines))
        r = rec(600)
        base = r["instruction"]
        E._learnings(r, load=fake(lines))
        got = r["learnings"]
        self.assertEqual(got["kept"] + got["dropped"], 8)
        self.assertGreaterEqual(got["kept"], 1)
        self.assertGreaterEqual(got["dropped"], 1)
        added = r["instruction"][len(base):]
        self.assertTrue(r["instruction"].startswith(base))
        self.assertTrue(D.fits(base, added))
        self.assertEqual(added, "\n\n" + HEAD + "\n" + "\n".join(lines[:got["kept"]]) + "\n")
        self.assertEqual(r["chars"], len(r["instruction"]))
        # one more line would not have fitted
        self.assertFalse(D.fits(base, "\n\n" + HEAD + "\n" + "\n".join(lines[:got["kept"] + 1]) + "\n"))

    def test_ii_a_block_that_fits_whole_is_appended_whole(self):
        lines = [forty(i) for i in range(8)]
        r = rec(200)
        E._learnings(r, load=fake(lines))
        self.assertEqual(r["learnings"], {"kept": 8, "dropped": 0})
        self.assertEqual(r["instruction"], "a" * 200 + "\n\n" + HEAD + "\n" + "\n".join(lines) + "\n")

    def test_iii_a_full_instruction_appends_nothing(self):
        r = rec(700)
        before = r["instruction"]
        E._learnings(r, load=fake([forty(i) for i in range(8)]))
        self.assertEqual(r["instruction"], before)
        self.assertEqual(r["chars"], 700)
        self.assertEqual(r["learnings"], {"kept": 0, "dropped": 8})

    def test_iv_a_quoted_note_is_counted_raw(self):
        lines = ['- "' + "q" * 36 + '"' for _ in range(8)]
        block = "\n\n" + HEAD + "\n" + "\n".join(lines) + "\n"
        r = rec(600)
        base = r["instruction"]
        # measured with its quotes left out, the whole block would fit ...
        self.assertLessEqual(len(D._unquoted(base)) + len(D._unquoted(block)), D.TEXT_MAX)
        # ... measured raw, as it is sent, it does not
        self.assertFalse(D.fits(base, block))
        E._learnings(r, load=fake(lines))
        self.assertGreaterEqual(r["learnings"]["dropped"], 1)
        self.assertTrue(D.fits(base, r["instruction"][len(base):]))
        self.assertLessEqual(len(r["instruction"]), D.TEXT_MAX)

    def test_iv_fits_counts_the_extra_raw(self):
        self.assertTrue(D.fits("a" * 600, "b" * 100))
        self.assertFalse(D.fits("a" * 600, "b" * 101))
        self.assertFalse(D.fits("a" * 600, '"' + "q" * 120 + '"'))
        # the instruction itself is measured as the guard measures it
        self.assertTrue(D.fits("a" * 600 + '"' + "q" * 300 + '"', "b" * 90))

    def test_v_a_failed_hook_is_said_once_and_the_edit_goes_on(self):
        def boom():
            raise RuntimeError("no digest")
        r = rec(400)
        before_text, before_chars = r["instruction"], r["chars"]
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            E._learnings(r, load=boom)
        self.assertEqual(r["instruction"], before_text)
        self.assertEqual(r["chars"], before_chars)
        self.assertEqual(r["learnings"], {"error": "RuntimeError: no digest"})
        out = err.getvalue().splitlines()
        self.assertEqual(len(out), 1, out)
        self.assertEqual(out[0], "learnings hook failed: RuntimeError: no digest — instruction sent without it")

    def test_vi_no_silent_except_inside_the_hook_markers(self):
        src = ENGINE.read_text()
        raw = src.splitlines()
        starts = [i for i, l in enumerate(raw, 1) if ">>> APPROVAL-PAGE LEARNINGS HOOK" in l]
        ends = [i for i, l in enumerate(raw, 1) if "<<< APPROVAL-PAGE LEARNINGS HOOK" in l]
        self.assertEqual((len(starts), len(ends)), (1, 1), "one pair of hook markers")
        lo, hi = starts[0], ends[0]
        self.assertLess(lo, hi)
        # comments and strings stripped: only code tokens between the markers
        code = [t.string for t in tokenize.generate_tokens(io.StringIO(src).readline)
                if lo < t.start[0] < hi and t.type in (tokenize.NAME, tokenize.OP)]
        joined = " ".join(code)
        self.assertIn("_learnings", joined)
        self.assertIsNone(re.search(r"\bexcept\s+Exception\s*(as\s+\w+\s*)?:\s*pass\b", joined), joined)
        # and the function the markers call does not swallow a failure either
        body = [t.string for t in tokenize.generate_tokens(io.StringIO(src).readline)
                if t.type in (tokenize.NAME, tokenize.OP)]
        joined = " ".join(body)
        fn = joined[joined.index("def _learnings"):]
        fn = fn[:fn.index("def ", 4)]
        self.assertIsNone(re.search(r"\bexcept\s+Exception\s*(as\s+\w+\s*)?:\s*pass\b", fn), fn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
