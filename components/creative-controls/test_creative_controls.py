#!/usr/bin/env python3
"""The creative controls hold together: every dial is a full scale, every
preset and default sits on it, the rendered files are current, nothing is
gendered, and the target folds preset over defaults. No network."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import creative_controls as CC  # noqa: E402
import read as RD  # noqa: E402


class Controls(unittest.TestCase):
    def setUp(self):
        self.c = CC.load()
        self.levels = {d["id"]: [s["level"] for s in d["scale"]] for d in self.c["dials"]}

    def test_every_dial_is_five_named_levels(self):
        for d in self.c["dials"]:
            self.assertEqual(len(d["scale"]), 5, d["id"])
            self.assertTrue(all(s["name"] and s["what"] for s in d["scale"]), d["id"])
            self.assertTrue(set(d["media"]) <= {"copy", "video", "image"} and d["media"], d["id"])
            self.assertIn(d["default"]["level"], self.levels[d["id"]], d["id"])

    def test_presets_sit_on_the_scales(self):
        for p in self.c["presets"]:
            for k, v in p["levels"].items():
                self.assertIn(k, self.levels, "%s names no dial %s" % (p["id"], k))
                self.assertIn(v, self.levels[k], "%s %s=%s" % (p["id"], k, v))

    def test_no_preset_is_sterile(self):
        floor = self.c["floor"]["levels"]
        for p in self.c["presets"]:
            for k, v in floor.items():
                self.assertGreaterEqual(p["levels"][k], v, "%s %s below the floor" % (p["id"], k))
                self.assertGreaterEqual(CC.target(p["id"])[1][k], v)

    def test_ids_unique_and_statused(self):
        for bank in ("dials", "emotions", "techniques", "presets"):
            ids = [x["id"] for x in self.c[bank]]
            self.assertEqual(len(ids), len(set(ids)), bank)
            self.assertTrue(all(x["status"] in ("draft", "approved", "deprecated") for x in self.c[bank]), bank)

    def test_target_folds_preset_over_defaults(self):
        pr, lv = CC.target("native-unaware", None, "image")
        self.assertEqual(lv["ad_likeness"], 0)
        self.assertNotIn("cutting_rate", lv)             # a video-only dial is not a picture's
        self.assertEqual(lv["density"], next(d for d in self.c["dials"] if d["id"] == "density")["default"]["level"])
        with self.assertRaises(KeyError):
            CC.target("no-such-preset")

    def test_rendered_files_are_current(self):
        self.assertEqual(CC.main(["render", "--check"]), 0)

    def test_no_gendered_pronoun(self):
        lint = CC.REPO / "components/marketing-doctrine/lint_prompts.py"
        files = [CC.SLICE, CC.GLOSSARY_MD, CC.CONTROLS] + sorted((HERE / "prompts").glob("*.md"))
        r = subprocess.run([sys.executable, str(lint)] + [str(f) for f in files], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_reader_check_holds_off_scale_and_unknown(self):
        good = {"dials": {d["id"]: {"level": d["default"]["level"], "why": "x"} for d in CC.dials("image")},
                "emotion": {"primary": "disgust"}, "techniques": ["replacement"]}
        self.assertEqual(RD.check(good, "image"), [])
        bad = json.loads(json.dumps(good))
        bad["dials"]["absurdity"]["level"] = 9
        bad["techniques"] = ["made-up"]
        bad["emotion"]["primary"] = "glee"
        self.assertEqual(len(RD.check(bad, "image")), 3)



class ParodyFloor(unittest.TestCase):
    def test_parody_checked_only_when_set(self):
        base = "\n".join("- %s: swipe 1 → ours 4" % k for k in ("intensity", "absurdity", "humor", "dramatisation", "stopping_power"))
        self.assertEqual(CC.floor_problems(base), [])
        self.assertTrue(CC.floor_problems(base + "\n- parody_marks: swipe 0 → ours 1"))


class Story(unittest.TestCase):
    """The story layer: every arc beat names a real doctrine section, every awareness level has arcs."""
    def setUp(self):
        self.c = CC.load()
        doc = json.loads((HERE.parent / "marketing-doctrine" / "frameworks.json").read_text())
        self.sections = {s["id"] for s in doc["sections"]}
        self.levels = [l["id"] for l in doc["awareness"]["levels"]]

    def test_every_beat_holds_a_doctrine_section(self):
        for a in self.c["arcs"]:
            self.assertTrue(a["what"] and a["how"] and a["beats"], a["id"])
            for b in a["beats"]:
                self.assertIn(b["section"], self.sections, "%s: %s" % (a["id"], b))

    def test_every_awareness_level_has_an_arc(self):
        for lv in self.levels:
            self.assertTrue(CC.arcs_for(lv), lv)

    def test_section_plan_reads_the_arc(self):
        a = self.c["arcs"][0]
        self.assertEqual([b["section"] for b in CC.section_plan(a["id"])], [b["section"] for b in a["beats"]])
        with self.assertRaises(KeyError):
            CC.section_plan("no-such-arc")

if __name__ == "__main__":
    unittest.main()
