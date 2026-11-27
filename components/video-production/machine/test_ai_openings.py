#!/usr/bin/env python3
"""The AI lane's openings (ai_openings.py): the chain's cut as the edit map the openings read, and each opening's line,
concept and moving event from the brief's hooks. Temp folders; nothing is called.

    python3 components/video-production/machine/test_ai_openings.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ai_openings as O  # noqa: E402


class Openings(unittest.TestCase):
    def test_the_chains_cut_gives_each_scenes_spoken_span(self):
        run = Path(tempfile.mkdtemp())
        (run / "edit").mkdir()
        for s, w in (("S1", [[0.0, 0.5], [8.0, 9.5]]), ("S2", [[0.2, 1.0], [3.0, 4.0]])):
            (run / "edit" / (s + ".words.json")).write_text(json.dumps(
                {"words": [{"w": "x", "start": a, "end": b} for a, b in w]}))
        (run / "edit" / "EDIT.json").write_text(json.dumps({"scenes": [
            {"scene": "S1", "seconds": 9.6, "words": "edit/S1.words.json"},
            {"scene": "S2", "seconds": 4.5, "words": "edit/S2.words.json"}]}))
        m = O.edit_map_of(run)["voice"]
        self.assertEqual([(r["scene"], r["a"], r["b"]) for r in m], [("S1", 0.0, 9.5), ("S2", 9.8, 13.6)])

    def test_each_opening_moves_as_the_control_opening_moves(self):
        plan = {"hooks": [{"id": "1", "take": "control", "opener_scene": "S1", "text": "c"},
                          {"id": "2", "take": "x", "text": "So many lotions.", "thumb": "The last drop hangs."}]}
        doc = {"scenes": [{"id": "S1", "first_frame": {"action": "Lotion runs off the column."}}]}
        m = O.matrix_of(plan, doc)["openings"]
        self.assertEqual((m[0]["id"], m[0]["line"]), ("V1", "So many lotions."))
        self.assertIn("The last drop hangs.", m[0]["scroll"])
        self.assertIn("Lotion runs off the column.", m[0]["scroll"])


class StudioTake(unittest.TestCase):
    """2026-11-21: an opening's Studio take written with only its steps stopped the version render at its `title`."""
    def test_an_opening_take_has_the_studio_take_shape(self):
        from unittest import mock
        sys.path.insert(0, str(O.WS / "components" / "video-studio"))
        import ai_shots as A
        import settings as ST
        t = Path(tempfile.mkdtemp())
        B = t / "briefs" / "p1"
        (B / "scenes" / "S1").mkdir(parents=True)
        (B / "brief.json").write_text(json.dumps({"order": ["S1"], "picks": {"S1": "take-1"}}))
        (B / "scenes" / "S1" / "take-1.json").write_text(json.dumps(
            {"schema": "scene-workflow/v1", "brief": "b", "scene": "S1", "take": "take-1", "title": "the control",
             "lane": "ai", "roll": "B", "pictures": {}, "clock": {}, "words": "old", "subjects": {}, "steps": [1]}))
        run = t / "run"
        op = run / "hooks" / "h02"
        (op / "edit").mkdir(parents=True)
        (op / "edit" / "EDIT.json").write_text(json.dumps({"scenes": [{"scene": "S1"}]}))
        with mock.patch.object(ST, "BRIEFS", t / "briefs"), mock.patch.object(A, "lay_edit", lambda *a: None), \
                mock.patch.object(O, "openings", lambda r: [{"id": "h02", "title": "Opening 2", "text": "New line."}]):
            self.assertEqual(O.studio(run, "p1"), ["H2"])
        take = json.loads((B / "scenes" / "H2" / "take-1.json").read_text())
        for k in ("schema", "brief", "lane", "roll", "pictures", "clock", "subjects"):
            self.assertIn(k, take)
        self.assertEqual((take["scene"], take["title"], take["words"], take["replaces"]), ("H2", "Opening 2", "New line.", "S1"))
        self.assertIn("H2", json.loads((B / "brief.json").read_text())["hooks"])


if __name__ == "__main__":
    unittest.main()
