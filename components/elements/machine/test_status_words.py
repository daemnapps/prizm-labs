#!/usr/bin/env python3
"""The element library's status words — components rule 6 (triage page 15,
2026-10-07; SI-79 (elements status words)).

    python3 test_status_words.py

Proves: every row's status is draft / approved / deprecated; only `approved`
counts as approved (proven no longer does); the words that moved
(unreviewed, proposed, seed) live in `state` at their source and reach the
library with the same counts; the approval gate refuses and accepts the same
rows; every reader that shows the word shows state first; a status off rule 6
is listed at build; a ruling may set state. Builds into temp dirs only.
"""
import collections
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import elements as E  # noqa: E402

RULE6 = {"draft", "approved", "deprecated"}
MOVED = {"unreviewed", "proposed", "seed"}
SOURCES = {"components/swipe-organic/formats.json": "formats",
           "tools/video-production/styles/bank.json": "styles"}


def _all_rows(index):
    for l in index["lists"]:
        for r in E.rows(l["element"], l["asset"]):
            yield l, r


class Library(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.real = E.LIBRARY
        E.LIBRARY = cls.tmp
        E._cache.clear()
        cls.index = E.build()

    @classmethod
    def tearDownClass(cls):
        E.LIBRARY = cls.real
        E._cache.clear()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_status_is_a_rule_6_word(self):
        off = {f'{l["element"]}/{l["asset"]}': l["off_status"] for l in self.index["lists"] if l["off_status"]}
        self.assertEqual(off, {})
        for l, r in _all_rows(self.index):
            self.assertIn(r["status"], RULE6, f'{l["element"]}/{l["asset"]} {r["id"]}')

    def test_approved_means_status_approved(self):
        self.assertEqual(E.APPROVED, {"approved"})
        for l, r in _all_rows(self.index):
            self.assertEqual(r["approved"], r["status"] == "approved", f'{l["element"]}/{l["asset"]} {r["id"]}')

    def test_moved_words_live_in_state_with_their_counts(self):
        moved = [r for _, r in _all_rows(self.index) if r.get("state") in MOVED]
        self.assertTrue(moved)
        for r in moved:
            self.assertEqual(r["status"], "draft", r["id"])
        for path, key in SOURCES.items():
            src = json.loads((E.REPO / path).read_text())[key]
            for s in src:
                self.assertIn(s.get("status"), RULE6, f'{path} {s.get("id")}')
            want = collections.Counter(s["state"] for s in src if s.get("state"))
            got = collections.Counter(r["state"] for _, r in _all_rows(self.index)
                                      if r["source"] == path and r.get("state"))
            self.assertEqual(got, want, path)
        for r in E.rows("format", "carousel"):
            self.assertEqual(r["state"], "proposed", r["id"])

    def test_the_gate_refuses_and_accepts_the_same_rows(self):
        unreviewed = next(r for r in E.rows("structure", "video") if r.get("state") == "unreviewed")
        carousel = E.rows("format", "carousel")[0]
        for (el, asset), r in ((("structure", "video"), unreviewed), (("format", "carousel"), carousel)):
            probs = E.check({(el, asset): r["id"]}, approved_only=True)
            self.assertEqual(len(probs), 1, r["id"])
            self.assertIn("not approved", probs[0])
        self.assertEqual(E.check({("style", "video"): "claymation"}, approved_only=True), [])


class Readers(unittest.TestCase):
    def test_each_reader_shows_state_first(self):
        shapes = {
            "components/swipe-organic/app.py": 'st = f.get("state") or f.get("status", "unreviewed")',
            "components/swipe-organic/feedsexport.py": '"status", "state", "family"',
            "tools/video-production/styles/render_board.py": '"fits_formats", "status", "state", "keeps_proof"',
            "tools/video-production/styles/board-template.html": "${h(s.state || s.status)}",
            "components/elements/machine/page.py": 'e(r.get("state") or r.get("status") or "draft")',
        }
        for path, shape in shapes.items():
            self.assertIn(shape, (E.REPO / path).read_text(), path)


class Gate(unittest.TestCase):
    def setUp(self):
        self.T = Path(tempfile.mkdtemp())
        (self.T / "sources.json").write_text(json.dumps({"sources": [{
            "element": "format", "asset": "zz", "inline": [
                dict(id="a", status="draft"),
                dict(id="b", status="proven"),                   # off rule 6 on purpose
                dict(id="c", status="draft", state="unreviewed")]}]}))
        (self.T / "additions.json").write_text(json.dumps({"rows": []}))
        self.patches = [mock.patch.object(E, "ROOT", self.T), mock.patch.object(E, "LIBRARY", self.T / "library")]
        for p in self.patches:
            p.start()
        E._cache.clear()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        E._cache.clear()
        shutil.rmtree(self.T, ignore_errors=True)

    def _row(self, id_):
        return next(r for r in E.rows("format", "zz") if r["id"] == id_)

    def test_build_flags_a_status_off_rule_6(self):
        self.assertEqual(E.build()["lists"][0]["off_status"], ["b"])
        self.assertIs(self._row("b")["approved"], False)                 # proven no longer counts
        self.assertEqual(self._row("c")["state"], "unreviewed")
        self.assertIsNone(self._row("a")["state"])

    def test_a_ruling_may_set_state(self):
        (self.T / "decisions.json").write_text(json.dumps({"lists": {"format/zz": {"rulings": {
            "a": {"state": "proposed"}, "c": {"status": "approved", "state": None}}}}}))
        E.build()
        a, c = self._row("a"), self._row("c")
        self.assertEqual((a["status"], a["state"]), ("draft", "proposed"))
        self.assertEqual((c["status"], c["state"], c["approved"]), ("approved", None, True))


if __name__ == "__main__":
    unittest.main(verbosity=1)
