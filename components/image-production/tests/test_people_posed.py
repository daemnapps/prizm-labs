#!/usr/bin/env python3
"""People are posed in 3D (21 Nov 2026): a picture whose request names its people is made only from a kept print whose
set posed those people as 3D figures (its cast board). A room-only print is refused and queued.

    python3 components/image-production/tests/test_people_posed.py
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
sys.path.append(str(HERE.parent))
from test_set_gate import Workspace, SG   # noqa: E402


class PeoplePosed(Workspace):
    def board(self, name, members):
        d = self.root / "runs" / "image-production" / "b" / "sets" / name
        (d / "cast-board.json").write_text(json.dumps({"order": members,
                                                       "members": [{"element": m} for m in members]}))

    def test_room_only_print_refused_for_people(self):
        pr = self.file_set("bar")
        with self.assertRaises(SG.SetRefused) as cm:
            SG.door_gate([pr], ["best-man", "the-girl"], door="test door")
        self.assertIn("posed", str(cm.exception))

    def test_print_with_people_posed_passes(self):
        pr = self.file_set("bar")
        self.board("bar", ["best-man", "the-girl"])
        SG.door_gate([pr], ["best-man", "the-girl"], door="test door")

    def test_one_missing_person_refused(self):
        pr = self.file_set("bar")
        self.board("bar", ["best-man"])
        with self.assertRaises(SG.SetRefused) as cm:
            SG.door_gate([pr], ["best-man", "the-rival"], door="test door")
        self.assertIn("the-rival", str(cm.exception))

    def test_no_people_named_asks_nothing(self):
        pr = self.file_set("bar")
        SG.door_gate([pr], None, door="test door")
        SG.door_gate([pr], False, door="test door")


if __name__ == "__main__":
    unittest.main()
