#!/usr/bin/env python3
"""One swipe id (SI-138 (intake reads corpus)) — stdlib unittest, no network, no model.

    python3 components/intake/tests/test_one_swipe_id.py

intake (tools/pools.py record()) and swipe-paid (corpus.py row()) used to
build `swipe:<lane>:<source>:<ref>` with two private slugs, and they drifted
(the doubled NN_ prefix). Both now build it only through
components/naming/names.py corpus_swipe_id(), whose source segment is the
stored hyphenless form (swipe_source_key) — never slug(), which keeps
hyphens since 2026-09-28 and would orphan every stored id.
Each module is loaded by path; record() and row() touch no pool.
"""
import importlib.util
import io
import re
import sys
import tokenize
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENTS = HERE.parent.parent
TOOLS = HERE.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.append(str(TOOLS))                             # appended, never inserted at 0 (pools imports paths)

NAMES_PY = COMPONENTS / "naming" / "names.py"
POOLS_PY = TOOLS / "pools.py"
CORPUS_PY = COMPONENTS / "swipe-paid" / "corpus.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


N = load("si138_names", NAMES_PY)
pools = load("si138_pools", POOLS_PY)
corpus = load("si138_corpus", CORPUS_PY)

# (lane, source, ref): NN_ prefixes, upper case, spaces, punctuation, hyphen runs, underscores.
CASES = [
    ("paid", "01_Big Claim!", "1001"),
    ("paid", "NN_Rival-Co", "1002"),
    ("paid", "Rival Co.", "pages-ten-reasons"),
    ("own", "Our Account #111", "a1"),
    ("own", "live", "a9"),
    ("organic", "alpha--some-sub", "tiktok:77"),
    ("organic", "  Some One / Saves?? ", "instagram:AAA"),
    ("organic", "4bu_m", "7301"),
]


def stored_form(lane, source, ref):
    """What every stored row already carries — written out here, not imported."""
    return "swipe:%s:%s:%s" % (lane, re.sub(r"[^a-z0-9]", "", str(source).lower()), ref)


def intake_id(lane, source, ref):
    return pools.record(lane, source, ref, source=lane, owner="competitor", kind="video",
                        swiped_for="", pool="components/swipe-paid/x/blocks.json")["id"]


def corpus_id(lane, source, ref):
    return corpus.row(lane, source, ref)["swipe_id"]


def code_only(path):
    """The file's source with every comment and string literal removed."""
    out = []
    with open(str(path), "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING, tokenize.ENCODING):
                continue
            out.append(tok.string)
    return " ".join(out)


class TestOneId(unittest.TestCase):
    def test_all_three_call_sites_agree(self):
        for lane, source, ref in CASES:
            with self.subTest(lane=lane, source=source):
                want = N.corpus_swipe_id(lane, source, ref)
                self.assertEqual(intake_id(lane, source, ref), want)
                self.assertEqual(corpus_id(lane, source, ref), want)

    def test_the_id_is_the_stored_hyphenless_form(self):
        for lane, source, ref in CASES:
            with self.subTest(lane=lane, source=source):
                want = stored_form(lane, source, ref)
                self.assertEqual(N.corpus_swipe_id(lane, source, ref), want)
                self.assertNotIn("-", want.split(":")[2])

    def test_an_underscore_source_joins_the_stored_row(self):
        # components/swipe-organic/4bu_m is stored as `4bum`; slug() would mint `4bu-m`.
        want = "swipe:organic:4bum:7301"
        self.assertEqual(N.corpus_swipe_id("organic", "4bu_m", "7301"), want)
        self.assertEqual(intake_id("organic", "4bu_m", "7301"), want)
        self.assertEqual(corpus_id("organic", "4bu_m", "7301"), want)
        self.assertNotEqual(N.slug("4bu_m"), N.swipe_source_key("4bu_m"))

    def test_swipe_source_key_is_letters_and_digits_only(self):
        self.assertEqual(N.swipe_source_key("01_Big Claim!"), "01bigclaim")
        self.assertEqual(N.swipe_source_key("alpha--some-sub"), "alphasomesub")
        self.assertEqual(N.swipe_source_key(""), "")

    def test_both_sides_build_the_id_only_through_names(self):
        # pools and corpus each import naming/names.py as N; swap its function and both must follow.
        for mod in (pools.N, corpus.N):
            self.assertEqual(Path(mod.__file__).resolve(), NAMES_PY.resolve())
        held = {id(m): (m, m.corpus_swipe_id) for m in (pools.N, corpus.N)}
        for m, _ in held.values():
            m.corpus_swipe_id = lambda lane, source, ref: "SENTINEL"
        try:
            self.assertEqual(intake_id("paid", "x", "1"), "SENTINEL")
            self.assertEqual(corpus_id("paid", "x", "1"), "SENTINEL")
        finally:
            for m, real in held.values():
                m.corpus_swipe_id = real


class TestNoPrivateSlug(unittest.TestCase):
    def test_pools_has_no_slug_function_of_its_own(self):
        code = code_only(POOLS_PY)
        self.assertIsNone(re.search(r"\bdef\s+\w*slug\w*", code))
        self.assertIsNone(re.search(r"\b_slug\b", code))
        self.assertIn("corpus_swipe_id", code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
