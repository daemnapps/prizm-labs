"""P67 (2026-10-21, the owner: "make sure that's put in the chain"): on Auto, a sound the brief calls for that the bank
cannot supply is written as a row from the brief's own cue and made through make_bank's code path, then bound —
the banks gate refuses only what is still missing. Fakes only: nothing is paid for."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, as_name):
    sp = importlib.util.spec_from_file_location(as_name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


B = _load("banks", "t_auto_banks")


class AutoBanks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for bank, rows in (("sfx", [{"id": "whoosh", "tags": ["whoosh"], "status": "made",
                                     "file": "Shared Assets/banks/sfx/whoosh.mp3"}]),
                           ("music", [{"id": "music-low-calm-80", "energy": "low", "mood": "calm", "tempo_bpm": 80,
                                       "status": "made", "file": "Shared Assets/banks/music/music-low-calm-80.mp3"}])):
            (self.root / bank).mkdir()
            (self.root / bank / "index.json").write_text(json.dumps({"bank": bank, "drive_root": f"Shared Assets/banks/{bank}",
                                                                     "rows": rows}))
        self.made = []

    def tearDown(self):
        self.tmp.cleanup()

    def maker(self, bank, ids, root):
        # make_bank's own effect, faked: the rows marked made with their Drive file
        p = Path(root) / bank / "index.json"
        doc = json.loads(p.read_text())
        for r in doc["rows"]:
            if r["id"] in ids:
                r["status"], r["file"] = "made", f"Shared Assets/banks/{bank}/{r['id']}.mp3"
        p.write_text(json.dumps(doc))
        self.made += list(ids)
        return {"made": list(ids)}

    def plan(self):
        return {"sfx": [{"cue": "whoosh", "scene": "S1"},
                        {"cue": "typewriter", "what": "a burst of old manual typewriter keys", "scene": "S2"}]}

    def test_a_called_cue_with_no_row_is_written_from_the_brief_made_and_bound(self):
        plan = self.plan()
        self.assertTrue(B.resolve(json.loads(json.dumps(plan)), self.root), "the gate refuses it today")
        notes = B.auto_make(plan, self.root, maker=self.maker)
        self.assertEqual(self.made, ["typewriter"], "only the missing cue is made; whoosh is already in the bank")
        row = next(r for r in json.loads((self.root / "sfx" / "index.json").read_text())["rows"] if r["id"] == "typewriter")
        self.assertIn("old manual typewriter keys", row["prompt"], "the brief's own words are the prompt")
        self.assertIn("system", row["written_by"])
        self.assertEqual(B.resolve(plan, self.root), [], "the gate now passes")
        self.assertEqual(plan["sfx"][1]["bank_id"], "typewriter")
        self.assertTrue(any("row written" in n for n in notes))

    def test_a_dry_run_writes_and_makes_nothing(self):
        before = (self.root / "sfx" / "index.json").read_text()
        notes = B.auto_make(self.plan(), self.root, dry=True, maker=self.maker)
        self.assertEqual(self.made, [])
        self.assertEqual((self.root / "sfx" / "index.json").read_text(), before)
        self.assertTrue(any("would make" in n for n in notes))

    def test_only_called_cues_are_ever_made(self):
        B.auto_make({"sfx": []}, self.root, maker=self.maker)
        B.auto_make({}, self.root, maker=self.maker)
        self.assertEqual(self.made, [], "no cue in the brief, nothing made (V14)")

    def test_the_chain_makes_it_on_auto_and_refuses_on_manual(self):
        V2 = _load("run_v2", "t_auto_banks_run_v2")
        settings = self.root / "settings.json"
        saved = os.environ.get("OUTLIER_SETTINGS")
        os.environ["OUTLIER_SETTINGS"] = str(settings)
        try:
            settings.write_text(json.dumps({"automation": {"production": "manual"}}))
            m = V2.v2_load("banks")
            m._make_rows = self.maker
            self.assertTrue(m.resolve(self.plan(), self.root), "Manual: the gate as it was")
            settings.write_text(json.dumps({"automation": {"production": "auto", "paused": False}}))
            plan = self.plan()
            self.assertEqual(m.resolve(plan, self.root), [], "Auto: made inside the chain, then bound")
            self.assertEqual(self.made, ["typewriter"])
        finally:
            if saved is None:
                os.environ.pop("OUTLIER_SETTINGS", None)
            else:
                os.environ["OUTLIER_SETTINGS"] = saved


if __name__ == "__main__":
    unittest.main()
