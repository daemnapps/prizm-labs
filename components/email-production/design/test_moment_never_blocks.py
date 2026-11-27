#!/usr/bin/env python3
"""A moment email with no research or no look of its own is laid out anyway, in the brand's own look, with a note
for editor; it is never held for either (email_lead, 2026-11-03). Source-level: the layout step is a model call.

    /usr/bin/python3 components/email-production/design/test_moment_never_blocks.py
"""
import unittest
from pathlib import Path

LINE = (Path(__file__).resolve().parent / "line.py").read_text()
REPICK = (Path(__file__).resolve().parent / "repick.py").read_text()


class MomentNeverBlocks(unittest.TestCase):
    def test_the_model_is_not_told_the_email_is_held(self):
        self.assertNotIn("the email is held until it is researched", LINE)
        self.assertIn("Never hold the layout for this.", LINE)

    def test_a_missing_look_or_research_is_a_note_not_a_hold(self):
        self.assertNotIn("before this email builds", LINE)
        self.assertIn('notes = notes + ["for editor: no %s look for the moment', LINE)
        self.assertIn('notes = notes + ["for editor: no research on file for the moment', LINE)
        self.assertIn('spec["for_editor"] = notes', LINE)


    def test_a_picture_repick_never_holds_on_a_missing_look_either(self):
        # repick.py held brand_a nov-11 fed-up-king (Veterans Day) after the 2026-11-03 rule; same note as line.py now
        self.assertNotIn("before this email builds", REPICK)
        self.assertIn("for editor: no %s look for the moment", REPICK)

if __name__ == "__main__":
    unittest.main(verbosity=1)
