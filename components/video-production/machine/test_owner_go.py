#!/usr/bin/env python3
"""run_v2.py --go: the owner's go on the quote turns production to Auto for that process alone (quotes only,
owner 2026-11-27). Offline: nothing is generated, the house settings file is never read for writing."""
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load_run_v2():
    spec = importlib.util.spec_from_file_location("t_owner_go_run_v2", HERE / "run_v2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class OwnerGoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.house = self.root / "house.json"
        self.house.write_text(json.dumps({"automation": {"paused": True, "production": "auto", "stop_pictures": "manual"},
                                          "rulings": {"claims": "swap or cut"}}))
        self.quote = self.root / "quote.json"
        self.quote.write_text(json.dumps({"total_usd": 12.5, "lines": [], "stop_point": "the cut"}))
        self.go = self.root / "go.json"
        env = patch.dict(os.environ, {"OUTLIER_SETTINGS": str(self.house)})
        env.start()
        self.addCleanup(env.stop)
        self.v2 = load_run_v2()

    def write_go(self, **over):
        rec = {"quote": str(self.quote), "quote_sha256": hashlib.sha256(self.quote.read_bytes()).hexdigest(),
               "total_usd": 12.5, "approved_by": "owner", "said": "go", "cap_usd": 15}
        rec.update(over)
        self.go.write_text(json.dumps(rec))

    def test_valid_go_sets_this_process_to_auto_and_leaves_the_house_file(self):
        before = self.house.read_bytes()
        self.write_go()
        mine = Path(self.v2._owner_go(str(self.go)))
        cfg = json.loads(mine.read_text())
        self.assertEqual(mine, self.root / "autonomy-settings.json")
        self.assertFalse(cfg["automation"]["paused"])
        self.assertEqual(cfg["automation"]["production"], "auto")
        self.assertEqual(cfg["automation"]["stop_pictures"], "auto")
        self.assertEqual(cfg["rulings"], {"claims": "swap or cut"})       # the owner's rulings carry over
        self.assertEqual(os.environ["OUTLIER_SETTINGS"], str(mine))
        self.assertEqual(self.v2._setting("automation.paused"), False)
        self.assertEqual(self.house.read_bytes(), before)

    def test_no_go_without_his_words_a_cap_or_the_same_quote(self):
        for bad in ({"said": ""}, {"approved_by": ""}, {"cap_usd": 0}, {"cap_usd": 10}, {"quote_sha256": "0" * 64}):
            self.write_go(**bad)
            with self.assertRaises(SystemExit):
                self.v2._owner_go(str(self.go))
        self.assertEqual(os.environ["OUTLIER_SETTINGS"], str(self.house))
        self.assertFalse((self.root / "autonomy-settings.json").exists())


if __name__ == "__main__":
    unittest.main()
