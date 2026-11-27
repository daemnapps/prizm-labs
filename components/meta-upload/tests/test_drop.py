#!/usr/bin/env python3
"""Drop: a card not worth running leaves every list, goes nowhere upstream, and stays on the Drive (renamed, never deleted)."""
import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
ROOT = tempfile.mkdtemp()
os.environ["META_CARDS_ROOT"] = ROOT
import approve as A  # noqa: E402
import cards as C  # noqa: E402


class Drop(unittest.TestCase):
    def setUp(self):
        # the scratch root is set for every test, not only at import: another test file's tearDown clears it, and a
        # run of the whole folder then filed these stand-in cards under the real cards root (found 2026-11-18)
        self._env = mock.patch.dict(os.environ, {"META_CARDS_ROOT": ROOT})
        self._env.start()

    def tearDown(self):
        self._env.stop()

    def test_drop_renames_into_dropped_and_leaves_the_lists(self):
        name = "zzbrand_widget_brief-0001_batch-2026-10-30-a"
        folder = C.root() / "zzbrand" / "1-check" / "image" / name
        folder.mkdir(parents=True)
        (folder / "card.json").write_text(json.dumps({"ad_name": name, "brand": "zzbrand"}))
        code, out = A.drop(C.card_id(folder), "not worth it", "owner")
        self.assertEqual((code, out["ok"]), (200, True))
        gone = C.root() / "zzbrand" / "dropped" / "image" / name
        self.assertTrue((gone / "card.json").exists())
        self.assertFalse(folder.exists())
        self.assertEqual(json.loads((gone / "card.json").read_text())["approval"]["decision"], "drop")

    def test_a_live_card_cannot_be_dropped(self):
        name = "zzbrand_widget_brief-0002_batch-2026-10-30-a"
        folder = C.root() / "zzbrand" / "3-live" / "image" / name
        folder.mkdir(parents=True)
        (folder / "card.json").write_text(json.dumps({"ad_name": name, "brand": "zzbrand"}))
        code, out = A.drop(C.card_id(folder), "x", "owner")
        self.assertEqual(code, 409)
        self.assertTrue(folder.exists())


if __name__ == "__main__":
    unittest.main()
