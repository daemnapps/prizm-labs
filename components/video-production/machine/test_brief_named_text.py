"""Text the brief itself names for a scene (a sign, a notice) is passed to the picture inventory as allowed; cast names
and place labels are not text. Run: python3 -m unittest test_brief_named_text"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
_sp = importlib.util.spec_from_file_location("vm_cc_named_text", HERE / "clip_checklist.py")
CC = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(CC)


class BriefNamedText(unittest.TestCase):
    def test_sign_and_notice_allowed(self):
        run = Path(tempfile.mkdtemp(prefix="namedtext_"))
        doc = {"cast": [{"id": "DRE"}, {"id": "LOU"}],
               "scenes": [{"id": "S7", "setting_id": "GYM ENTRANCE", "on_screen": "the notice reads RESHOOT IN 12 WEEKS",
                           "first_frame": {"subject": "DRE and LOU under the GRIND HOUSE sign", "location": "GYM ENTRANCE"}}]}
        (run / "brief.md").write_text("```json\n" + json.dumps(doc) + "\n```\n")
        got = CC.brief_text(run, "S7-shot-4")
        self.assertIn("RESHOOT IN 12 WEEKS", got)
        self.assertIn("GRIND HOUSE", got)
        self.assertNotIn("DRE", got)
        self.assertNotIn("GYM ENTRANCE", got)


if __name__ == "__main__":
    unittest.main()
