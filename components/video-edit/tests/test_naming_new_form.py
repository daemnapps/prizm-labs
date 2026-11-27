"""The file names the edit writes are the naming convention's NEW form, end to end
(components/naming/names.py:11-23, locked 2026-09-28: tools READ both forms and WRITE
the new one). Imports only versions from machine/ so it runs on the mini's Python
3.9.6; no files written, no network."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import versions as V  # noqa: E402

SHEET = {"meta": {"brand": "t", "label": "t", "format": "talkinghead"},
         "name": {"product": "balm", "talent": "none", "avatar": "tight", "problem": "dry",
                  "angle": "fix", "concept": "stop", "brief": "p140"}}
WANT = "t_balm_video_ai_none_tight_dry_fix_stop_talkinghead_brief-0140_1x1_batch-2026-09-23-a_asset-03"


class NamingNewForm(unittest.TestCase):
    def name(self, sheet=None):
        return V.file_name(sheet or copy.deepcopy(SHEET), "1x1", 3, "260923a")

    def test_written_in_the_new_form(self):
        self.assertEqual(self.name(), (WANT, None))

    def test_it_parses_back(self):
        name, _ = self.name()
        import names as N  # versions put components/naming on sys.path
        p = N.parse_any(name)
        self.assertIsNotNone(p)
        self.assertEqual(p["form"], "new")
        self.assertEqual(p["brief"], "brief-0140")
        self.assertEqual(p["batch"], "batch-2026-09-23-a")
        self.assertEqual(p["asset_n"], 3)
        self.assertEqual(p["format"], "talkinghead")

    def test_no_old_form_pieces(self):
        name, _ = self.name()
        self.assertNotIn("-a03", name)
        self.assertNotIn("260923a", name)

    def test_missing_field_is_never_invented(self):
        s = copy.deepcopy(SHEET)
        del s["name"]["concept"]
        name, note = self.name(s)
        self.assertEqual(name, "t-full-1x1")
        self.assertIn("concept", note)


if __name__ == "__main__":
    unittest.main()
