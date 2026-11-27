"""The creator brief's prompt carries the person's full profile (creative-strategist who.block) when the brief's run
has an aim, and saves profile.json / profile.md beside it. No model, no network. Read on the first brand on disk with an
avatar, a sub-avatar, a product file and a guarantees file, so no brand is named here."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
C = HERE.parents[1]
sys.path.append(str(C / "creative-strategist" / "machine"))
import who  # noqa: E402
from test_build import BRIEF  # noqa: E402


def _mod():
    spec = importlib.util.spec_from_file_location("creator_brief_build_who", HERE / "build.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def first():
    for bd in sorted(p for p in (C.parent / "brands").iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        prods = sorted((bd / "products").glob("*.md")) if (bd / "products").is_dir() else []
        if not prods or not (bd / "offers" / "guarantees.json").is_file():
            continue
        for a in who.avatars(bd.name):
            for s in who.subs(bd.name, a):
                if who.filed(bd.name, a, s):
                    return bd.name, a, s, prods[0].stem
    return None


class WhoReachesCreatorBrief(unittest.TestCase):
    def setUp(self):
        self.who = first()
        if not self.who:
            self.skipTest("no brand with a filed profile, a product file and guarantees on disk")
        self.m = _mod()

    def test_prompt_carries_the_full_profile_and_saves_it(self):
        brand, avatar, sub, product = self.who
        with tempfile.TemporaryDirectory() as t:
            run = Path(t) / "run"
            run.mkdir()
            (run / "5-brief.md").write_text(BRIEF)
            (run / "run.json").write_text(json.dumps({"aim": {"avatar": avatar, "sub": sub, "awareness": "problem-aware"}}))
            out = Path(t) / "out"
            self.assertEqual(self.m.main(["inputs", str(run / "5-brief.md"), "--brand", brand, "--product", product, "--out", str(out)]), 0)
            prompt = (out / "creator-brief.prompt.md").read_text()
            self.assertTrue(prompt.startswith(who.MARK))
            self.assertIn(who.END, prompt)
            name = who.filed(brand, avatar, sub)["name"]
            self.assertIn("(the profile `%s`)" % name, prompt)          # the finished profile itself, not the card only
            self.assertTrue((out / "profile.json").is_file() and (out / "profile.md").is_file())
            self.assertEqual(json.loads((out / "profile.json").read_text())["person"]["name"], name)

    def test_no_aim_no_block(self):
        self.assertEqual(self.m.who_block(self.who[0], None), "")


if __name__ == "__main__":
    unittest.main()
