"""The Studio calls the chain's editing rules, never copies of its own (owner ruling 2026-11-16, V57 (swipe is the backbone)): shot timing and
the frame look in swipe_cut, the cut checks in swipe_check, voices, edit notes and the cover rules."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as ST  # noqa: E402


def home(mod):
    return Path(mod.__file__).resolve()


class StudioUsesTheChain(unittest.TestCase):
    def test_shot_timing_and_the_frame_look(self):
        import swipe_cut as SWC
        self.assertEqual(home(SWC.TIMING), (ST.part("video-edit") / "machine" / "shot_timing.py").resolve())
        self.assertEqual(home(SWC.LOOKS), (ST.part("video-production") / "machine" / "frame_look.py").resolve())
        self.assertEqual((SWC.MAX_SHOT, SWC.END_CARD), (SWC.TIMING.MAX_SHOT, SWC.TIMING.END_CARD))
        self.assertEqual(SWC.LOOK, SWC.LOOKS.LOOK)

    def test_the_cut_checks(self):
        import swipe_check as SC
        self.assertIs(SC.cuts, SC.CC.cuts)
        self.assertIs(SC.canon, SC.CC.canon)
        self.assertEqual(home(SC.CC), (ST.part("video-edit") / "machine" / "cut_check.py").resolve())

    def test_voices(self):
        import voices as VO
        self.assertIs(VO.NoVoice, ST.chain("video-production", "voice_cast").NoVoice)

    def test_edit_notes_is_the_chain_module(self):
        import edit_notes as EN
        self.assertEqual(home(EN), (ST.part("video-edit") / "machine" / "edit_notes.py").resolve())

    def test_cover_rules(self):
        import covers_stage as CS
        CR = ST.chain("video-edit", "cover_rules")
        self.assertIs(CS.CR, CR)
        self.assertEqual(CS.headline_for("v1", "Three days in. It works.", ["Three days in. Wow."]),
                         CR.headline_for("v1", "Three days in. It works.", ["Three days in. Wow."]))

    def test_one_module_object_per_chain_file(self):
        self.assertIs(ST.chain("video-edit", "cut_check"), ST.chain("video-edit", "shot_timing")._sibling("cut_check"))


if __name__ == "__main__":
    unittest.main()
