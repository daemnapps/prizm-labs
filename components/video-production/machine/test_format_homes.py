"""One home per format (formats/README.md): every formats/<id>/format.json is the source of its bank row and
playbook, the copies match it, and its workflow is one the runner accepts."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMATS = HERE.parent / "formats"
sys.path.insert(0, str(HERE))
import playbook as PB  # noqa: E402
import workflow_catalog as catalog  # noqa: E402


def _sync():
    spec = importlib.util.spec_from_file_location("formats_sync", FORMATS / "sync.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FormatHomes(unittest.TestCase):
    def setUp(self):
        self.sync = _sync()
        self.found = self.sync.homes()

    def test_there_is_a_home(self):
        self.assertIn("narrator-montage", [d["id"] for _p, d in self.found])

    def test_copies_match_their_homes(self):
        self.assertEqual(self.sync.main(["--check"]), 0, "a copy differs from its home: run python3 formats/sync.py")

    def test_home_has_its_three_files(self):
        for path, doc in self.found:
            for name in ("FORMAT.md", "LEARNINGS.md"):
                self.assertTrue((path.parent / name).is_file(), "%s has no %s" % (doc["id"], name))

    def test_status_words(self):
        for _path, doc in self.found:
            self.assertIn(doc["status"], ("draft", "approved", "deprecated"))

    def test_bank_row_points_home(self):
        rows = {r["id"]: r for r in json.loads((FORMATS / "bank.json").read_text())["formats"]}
        for path, doc in self.found:
            self.assertEqual(rows[doc["id"]]["profile"], doc["id"] + "/FORMAT.md")
            self.assertTrue(rows[doc["id"]]["home"].endswith(doc["id"] + "/format.json"))

    def test_playbook_resolves_to_the_home(self):
        for _path, doc in self.found:
            pb = PB.playbook_for(doc["id"])
            self.assertEqual(pb.get("_source"), "family")
            self.assertEqual(pb.get("format_id"), doc["id"])

    def test_workflow_is_declared_and_valid(self):
        ws = HERE.parents[2]
        for _path, doc in self.found:
            res = catalog.resolve(doc["id"], ws)
            self.assertEqual(res["coverage"], "declared")
            self.assertEqual(catalog.validate(res["workflow"]), [])


if __name__ == "__main__":
    unittest.main()
