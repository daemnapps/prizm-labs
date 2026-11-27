"""Edit-only screen/card scenes must not be sent to a paid clip generator."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "maker"))
import maker_pack as MP


class EditOnlyScenes(unittest.TestCase):
    def test_empty_screen_placeholder_is_edit_only(self):
        step = {"tool": "gen.shot", "prompt": "", "inputs": {"refs": []}, "params": {"picture": None}}
        self.assertEqual(MP._clip_tool(step, {"roll": "S", "pictures": {}}, {"source": "0:29.4 - 0:31.0 · S · [screen: site]"}), "edit")

    def test_cards_and_endcards_without_plates_are_edit_only(self):
        for kind in ("screen", "card", "endcard"):
            with self.subTest(kind=kind):
                self.assertEqual(MP._clip_tool({"tool": "gen.shot"}, {}, {"kind": kind}), "edit")

    def test_a_generated_plate_or_prompt_keeps_its_generation(self):
        for step, wf, scene in [
            ({"tool": "gen.shot", "prompt": "Animate the product"}, {}, {"kind": "screen"}),
            ({"tool": "gen.take"}, {}, {"kind": "card", "card": {"plate": "Product on a table"}}),
            ({"tool": "gen.take", "params": {"picture": "plate.png"}}, {"roll": "S"}, {}),
            ({"tool": "gen.shot"}, {"roll": "S", "pictures": {"first": "plate.png"}}, {}),
        ]:
            with self.subTest(step=step, scene=scene):
                self.assertEqual(MP._clip_tool(step, wf, scene), step["tool"])

    def test_an_empty_ordinary_shot_stays_a_generation_gap(self):
        self.assertEqual(MP._clip_tool({"tool": "gen.shot", "prompt": ""}, {"roll": "B"}, {}), "gen.shot")


if __name__ == "__main__":
    unittest.main()
