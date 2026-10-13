#!/usr/bin/env python3
"""No machine tells in what we say (the owner, 2026-10-13: "completely
eliminate AI sounding / looking generative output"). The tells slice reaches
the writing steps, and the hard tells hold stages 3 and 5. No model.

    python3 test_tells_check.py
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C   # noqa: E402

SLICE = "components/marketing-doctrine/slices/tells.md"
sys.path.insert(0, str(C.WS / "components/marketing-doctrine"))
import tells as T   # noqa: E402


class Wired(unittest.TestCase):
    def test_slice_bound_to_the_writing_steps(self):
        self.assertTrue((C.WS / SLICE).is_file())
        sv = json.loads((HERE / "extra-stages.json").read_text())["stage_vars"]
        for k in ("stage3", "stage4g", "stage5"):
            self.assertEqual(sv[k].get("tells"), SLICE, k)

    def test_current_prompts_ask_for_it(self):
        for k in ("stage3", "stage4g"):
            self.assertIn("{tells}", C.newest(k)[0].read_text(), k)
        for stem in ("stage5-ai-", "stage5-creator-"):
            best = max((f for h in C.PROMPT_HOMES if h.exists() for f in h.glob(stem + "*.md")),
                       key=lambda f: int(C.VERSION.search(f.name).group(1)))
            self.assertIn("{tells}", best.read_text(), best.name)

    def test_the_runner_holds_on_a_tell_at_3_and_5(self):
        src = (HERE / "run.py").read_text()
        self.assertIn("marketing-doctrine/tells.py", src)
        self.assertIn('st["tells_check"]', src)


class Combination(unittest.TestCase):
    def test_creativity_reaches_the_spice_pass(self):
        sv = json.loads((HERE / "extra-stages.json").read_text())["stage_vars"]
        self.assertEqual(sv["stage4g"].get("creativity"),
                         "components/marketing-doctrine/slices/creativity.md")
        txt = C.newest("stage4g")[0].read_text()
        self.assertIn("{creativity}", txt)
        self.assertIn("THE COMBINATION", txt)


class Caught(unittest.TestCase):
    def test_a_template_line_is_caught(self):
        got = T.check_text("Honestly this serum is a game changer.")
        self.assertEqual([g["id"] for g in got], ["W2"])

    def test_the_swipes_own_phrase_is_not(self):
        self.assertEqual(T.check_text("Say goodbye to the old way.",
                                      swipe="ok so say goodbye to the old way"), [])

    def test_plain_speech_is_clean(self):
        self.assertEqual(T.check_text("I wash it off at night and that's it."), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
