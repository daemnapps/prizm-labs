#!/usr/bin/env python3
"""The Variation video chain — route, control, any-hook pick, map check,
mark used, proven gate. No model, no network, no brand folder written.

    python3 test_variation.py
"""
import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C  # noqa: E402

NEW_VIDEO = ["stage0", "stage1", "stage1c", "stage1b", "stage2", "stage3", "stage4r", "stage4b",
             "stage4a", "stage4c", "stage4d", "stage4e", "stage4g", "stage5", "stage5u"]
HOOKS = """**1. THE FOUNDATIONAL HOOK**
FORMAT LINE: The [THING] is that?
LINE V0: The heck is that?
CARD V0: so this brush turns you into a new person? 😂
LINE V3: The heck is he rubbing on his face?
CARD V3: he said it's a brush 😂
LANGUAGE USED:
- av-pro-0001 | rubbing on his face
- av-pro-0002 | new person
"""


class Route(unittest.TestCase):
    def test_variation_plan(self):
        keys = [s["key"] for s in C.stages("", "", "ai", "VARIATION")]
        for k in ("stage3v", "stage4m", "stage5u", "stage4c"):
            self.assertIn(k, keys)
        r = C.route_for("VARIATION")
        self.assertEqual(r["skip"], ["stage3"])
        self.assertNotIn("stage4c", r["skip"])            # expansion always runs here
        self.assertEqual(r["substitute"], {"stage3": "stage3v"})

    def test_new_video_plan_unchanged_but_for_mark_used(self):
        for lane in ("ALREADY AN AD", "ORGANIC", ""):
            keys = [s["key"] for s in C.stages("", "", "ai", lane)]
            self.assertEqual([k for k in keys if k in NEW_VIDEO], NEW_VIDEO)
            self.assertNotIn("stage3v", keys); self.assertNotIn("stage4m", keys)

    def test_variation_only_inputs_are_empty_elsewhere(self):
        s = next(x for x in C.stages("", "", "ai", "ORGANIC") if x["key"] == "stage4b")
        self.assertEqual(s["vars"]["target_awareness"], "~target_awareness")
        txt, _ = C.resolve_source("~target_awareness", "", {})
        self.assertEqual(txt, "")


class Pick(unittest.TestCase):
    def test_hook_lines(self):
        got = C.hook_lines(HOOKS, "V3")
        self.assertIn("LINE V3: The heck is he rubbing on his face?", got)
        self.assertIn("CARD V3: he said it's a brush", got)
        self.assertEqual(C.hook_lines(HOOKS, "V4"), "")

    def test_pick_is_control_unless_a_leaf_names_one(self):
        ctl, _ = C.resolve_source("@stage4b#pick", "", {"stage4b": HOOKS})
        self.assertTrue(ctl.startswith("CONTROL"))
        leaf, why = C.resolve_source("@stage4b#pick", "", {"stage4b": HOOKS, "hook_pick": "V3"})
        self.assertIn("LINE V3:", leaf); self.assertIn("variation tree", why)


class Control(unittest.TestCase):
    def test_every_line_word_for_word(self):
        import control
        tr = [dict(id="T1", start=0.78, speaker="Speaker 1", text="The heck is that?"),
              dict(id="T2", start=3.0, speaker="Speaker 1", text="Rubbing it on his face?")]
        out = control.render(tr, [dict(kind="organic", views=16400000, saves=146000, source="m.json")], "#1")
        self.assertIn('| T1 | 0:00.8 | Speaker 1 | "The heck is that?" | "The heck is that?" |', out)
        self.assertIn("T2", out); self.assertIn("16,400,000", out)
        self.assertIn("## ELEMENT LEDGER", out); self.assertIn("Kept", out)


class MarkUsed(unittest.TestCase):
    def test_cited_block(self):
        import mark_used as M
        self.assertEqual(M.cited(HOOKS), [("av-pro-0001", "rubbing on his face"), ("av-pro-0002", "new person")])
        self.assertEqual(M.cited("x\nLANGUAGE USED: none\n"), [])

    def test_a_leaf_keeps_only_its_own_hooks_rows_and_matches_the_brief(self):
        import mark_used as M
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); (d / "stages").mkdir()
            (d / "stages" / "4b-hooks.md").write_text(HOOKS)
            (d / "stages" / "5-brief.md").write_text("Scene 1. He said: I stopped getting razor bumps after one week of this.")
            st = dict(hook_pick="V3", stages=dict(stage4b=dict(status="done", out="stages/4b-hooks.md"),
                                                   stage5=dict(status="done", out="stages/5-brief.md")))
            rows = {"av-pro-0001": dict(id="av-pro-0001", text="rubbing on his face", avatar="a"),
                    "av-pro-0002": dict(id="av-pro-0002", text="new person", avatar="a"),
                    "av-cus-0009": dict(id="av-cus-0009", text="I stopped getting razor bumps", avatar="a"),
                    "av-cus-0010": dict(id="av-cus-0010", text="bumps", avatar="a")}
            used = M.collect(d, st, rows)
            self.assertIn("av-pro-0001", used)           # V3's words
            self.assertNotIn("av-pro-0002", used)        # V0's words — a sibling leaf's
            self.assertEqual(used["av-cus-0009"]["how"], "matched")
            self.assertNotIn("av-cus-0010", used)        # too short to match uncited


class Proven(unittest.TestCase):
    def test_refuses_without_proof(self):
        import proven
        ok, proof, why = proven.check("no-such-brand", "nothing-0")
        self.assertFalse(ok); self.assertEqual(proof, [])


class Map(unittest.TestCase):
    def test_map_is_checked_against_the_doctrine(self):
        import variation as V
        levels = [dict(level=l, sections=["hook", "call-to-action"]) for l in V.LEVELS]
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "stages").mkdir()
            def write(m):
                (root / "stages" / "4m.md").write_text("map\n```json\n" + json.dumps(m) + "\n```\n")
                (root / "run.json").write_text(json.dumps(dict(variation_of="x", stages=dict(
                    stage4m=dict(status="done", out="stages/4m.md")))))
            write(dict(control_level="solution-aware", levels=levels))
            self.assertEqual(V.read_map(root)["control_level"], "solution-aware")
            bad = [dict(level=l, sections=["hook", "made-up-section"]) for l in V.LEVELS]
            write(dict(control_level="solution-aware", levels=bad))
            with self.assertRaises(SystemExit):
                V.read_map(root)
            write(dict(control_level="solution-aware", levels=levels[:4]))
            with self.assertRaises(SystemExit):
                V.read_map(root)

    def test_labels_never_cut_to_the_same_name(self):
        import variation as V
        src = "brand-7167399325910289706"
        names = {V.base_for(src)} | {V.base_for(src, l) for l in V.LEVELS} | \
                {V.base_for(src, l, n) for l in V.LEVELS for n in range(6)}
        self.assertEqual(len(names), 1 + 5 + 30)
        self.assertTrue(all(len(n) <= 40 for n in names))


if __name__ == "__main__":
    unittest.main(verbosity=1)
