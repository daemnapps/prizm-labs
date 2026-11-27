"""The proposed-prompt switch is retired (2026-11-19).

History: from 2026-11-07 a new prompt version waited in video-teardown/prompts/proposed/ and ran only when its
switch in machine/proposed-switches.json was on. On 2026-11-16 the owner's V57 prompts (the swipe is the backbone)
were promoted into video-writing/prompts/v2/ and pinned in writing_v2.PASSES, and the switch was taken out of the
code; on 2026-11-19 the coordinating session ruled that state the intended one when it was saved. These tests
replace the switch's own tests under that ruling: what they now hold is that the writing line names its prompts by
hand, every pinned prompt is on disk, and nothing reads a proposed/ folder.

    /usr/bin/python3 -m unittest components/video-writing/tests/test_proposed_switch.py
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
sys.path.insert(0, str(COMP / "machine"))
sys.path.insert(0, str(COMP.parent / "video-teardown" / "machine"))

import chain as C          # noqa: E402
import writing_v2 as W     # noqa: E402

BRAND = next(p.name for p in sorted((COMP.parents[1] / "brands").iterdir())
             if p.is_dir() and not p.name.startswith("_") and (p / "products").is_dir())


class TheSwitchIsRetired(unittest.TestCase):
    def test_no_switch_is_left_in_the_code(self):
        for mod in (C, W):
            for name in ("proposed_prompt", "proposed_on", "PROPOSED_FILES"):
                self.assertFalse(hasattr(mod, name), f"{mod.__name__}.{name}")

    def test_every_pinned_pass_prompt_is_on_disk(self):
        for key, _sid, _fid, _name, prompt, _splits in W.PASSES:
            self.assertTrue((W.V2 / prompt).is_file(), f"{key}: {prompt}")

    def test_the_plan_reads_only_the_pinned_files(self):
        pinned = {key: str(W.V2 / prompt) for key, _s, _f, _n, prompt, _sp in W.PASSES}
        for route, lane in (("ai", "paid"), ("ai", "organic"), ("ai", "")):
            for p in W.plan(BRAND, route, lane):
                self.assertEqual(p["prompt"], pinned[p["key"]], p["key"])
                self.assertNotIn("proposed", Path(p["prompt"]).parts)

    def test_no_stage_reads_a_proposed_folder(self):
        for route in ("ai", "creator"):
            for s in C.stages(BRAND, "", route, ""):
                if s.get("prompt"):
                    self.assertNotIn("proposed", Path(s["prompt"]).parts, s["key"])


if __name__ == "__main__":
    unittest.main()
