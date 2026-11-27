"""The run folder's own names (2026-10-26): new runs write clips/ledger.json and clips/calls/<call>/; a run made before
keeps clips/omni-ledger.json and clips/omni/<call>/ and both are found. No network."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location("t_clip_kit", HERE / "clip_kit.py")
CK = importlib.util.module_from_spec(sp)
sp.loader.exec_module(CK)


class Names(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.run = Path(self.t.name)
        (self.run / "clips").mkdir()

    def tearDown(self):
        self.t.cleanup()

    def test_a_new_run_gets_the_new_names(self):
        self.assertEqual(CK.ledger_path(self.run).name, "ledger.json")
        self.assertEqual(CK.calls_dir(self.run).name, "calls")

    def test_an_older_run_is_found_under_its_old_names(self):
        (self.run / "clips" / "omni-ledger.json").write_text("{}")
        (self.run / "clips" / "omni").mkdir()
        self.assertEqual(CK.ledger_path(self.run).name, "omni-ledger.json")
        self.assertEqual(CK.calls_dir(self.run).name, "omni")

    def test_once_the_new_names_exist_they_win(self):
        (self.run / "clips" / "omni-ledger.json").write_text("{}")
        (self.run / "clips" / "ledger.json").write_text("{}")
        (self.run / "clips" / "omni").mkdir()
        (self.run / "clips" / "calls").mkdir()
        self.assertEqual(CK.ledger_path(self.run).name, "ledger.json")
        self.assertEqual(CK.calls_dir(self.run).name, "calls")


if __name__ == "__main__":
    unittest.main()
