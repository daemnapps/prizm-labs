"""The writing station stands on its own and the teardown hands off to it (split 2026-10-19).

Spends nothing: no model is called, no run folder is written.

    /usr/bin/python3 -m unittest discover -s tools/video-writing/tests
"""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
MACHINE = COMP / "machine"
TD = COMP.parent / "video-teardown" / "machine"
sys.path.insert(0, str(MACHINE))
sys.path.insert(0, str(TD))

import chain as C          # noqa: E402  the teardown's engine, which writing leans on
import writing_v2 as W     # noqa: E402

BRAND = next(p.name for p in sorted((COMP.parents[1] / "brands").iterdir())
             if p.is_dir() and not p.name.startswith("_") and (p / "products").is_dir())


class PromptsLiveHere(unittest.TestCase):
    def test_the_chain_reads_writing_prompts_from_this_component(self):
        self.assertEqual(C.WRITING_PROMPTS.resolve(), (COMP / "prompts").resolve())

    def test_every_writing_prompt_home_exists(self):
        homes = [h for h in C.PROMPT_HOMES if str(COMP / "prompts") in str(h)]
        self.assertTrue(homes)
        self.assertEqual([str(h) for h in homes if not h.is_dir()], [])

    def test_every_v2_pass_prompt_exists(self):
        self.assertEqual([p[4] for p in W.PASSES if not (W.V2 / p[4]).is_file()], [])

    def test_no_writing_prompt_is_left_in_the_old_homes(self):
        self.assertFalse((COMP.parent / "copywriter" / "prompts" / "video").exists())


class EveryPassIsBound(unittest.TestCase):
    """Every {slot} a v2 prompt asks for has a source, on both routes."""

    def check(self, route):
        for p in W.plan(BRAND, route, "paid"):
            asks = set(re.findall(r"\{([a-z0-9_]+)\}", Path(p["prompt"]).read_text()))
            self.assertEqual(sorted(asks - set(p["vars"])), [], "%s %s" % (route, p["key"]))

    def test_ai_route(self):
        self.check("ai")

    def test_creator_route(self):
        self.check("creator")


class TeardownHandsOff(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.pop("VT_WRITING", None)
        import run as R
        self.R = R

    def tearDown(self):
        os.environ.pop("VT_WRITING", None)
        if self.prev is not None:
            os.environ["VT_WRITING"] = self.prev

    def test_the_teardown_loads_writing_from_this_component(self):
        mod = self.R._writing_line()
        self.assertEqual(Path(mod.__file__).resolve(), (MACHINE / "writing_v2.py").resolve())

    def test_hand_off_fires_on_v2_writing_stages_and_releases_otherwise(self):
        os.environ["VT_WRITING"] = "v2"
        self.assertTrue(self.R._writing_v2_on({"key": "stage3"}))
        self.assertFalse(self.R._writing_v2_on({"key": "stage1"}))
        os.environ.pop("VT_WRITING")
        self.assertFalse(self.R._writing_v2_on({"key": "stage3"}))

    def test_creator_and_founder_runs_keep_v1_writing(self):
        os.environ["VT_WRITING"] = "v2"
        self.assertTrue(self.R._writing_v2_on({"key": "stage3"}, {"production_route": "ai"}))
        self.assertFalse(self.R._writing_v2_on({"key": "stage3"}, {"production_route": "creator"}))
        self.assertFalse(self.R._writing_v2_on({"key": "stage3"}, {"production_route": "founder"}))

    def test_an_ai_run_always_writes_on_v2(self):
        # 2026-10-21 (sync W27): v1's AI brief v28 is archived; the AI route writes the v2 shooting script
        self.assertTrue(self.R._writing_v2_on({"key": "stage5"}, {"production_route": "ai"}))
        self.assertFalse(self.R._writing_v2_on({"key": "stage5"}, {"production_route": "creator"}))
        self.assertFalse(self.R._writing_v2_on({"key": "stage1"}, {"production_route": "ai"}))


class ItsOwnCommand(unittest.TestCase):
    def test_help_prints_and_spends_nothing(self):
        r = subprocess.run([sys.executable, str(MACHINE / "run.py"), "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Video writing", r.stdout)

    def test_refuses_a_run_that_does_not_exist(self):
        r = subprocess.run([sys.executable, str(MACHINE / "run.py"), "no-such-teardown-run-xyz"],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("run the teardown first", r.stderr + r.stdout)

    def test_a_creator_run_is_refused_before_any_call(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "v2test-creator"
            d.mkdir()
            (d / "run.json").write_text(json.dumps({
                "brand": BRAND, "label": "v2test-creator", "slug": "v2test-creator",
                "production_route": "creator", "format_id": "expert-consult", "stages": {}}))
            r = subprocess.run([sys.executable, str(MACHINE / "run.py"), str(d), "--sandbox"],
                               capture_output=True, text=True, env=dict(os.environ, QC_VIEWER="0"))
            self.assertEqual(r.returncode, 1)
            self.assertIn("ai route only", r.stdout + r.stderr)
            self.assertNotIn("stage3", json.loads((d / "run.json").read_text())["stages"])

    def test_a_writing_run_that_stops_exits_non_zero(self):
        """A teardown with no finished stages: writing stops before any model call, and says so
        in its exit code, so a mini job never files a stopped run as done."""
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "v2test-exit"
            d.mkdir()
            (d / "run.json").write_text(json.dumps({
                "brand": BRAND, "label": "v2test-exit", "slug": "v2test-exit",
                "production_route": "ai", "format_id": "expert-consult", "stages": {}}))
            env = dict(os.environ, VT_CHAIN="v2", QC_VIEWER="0")
            r = subprocess.run([sys.executable, str(MACHINE / "run.py"), str(d), "--sandbox"],
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 1, r.stdout[-400:] + r.stderr[-400:])
            st = json.loads((d / "run.json").read_text())
            self.assertEqual(st["stages"]["stage3"]["status"], "error")
            self.assertFalse(st.get("writing_v2_calls"))     # nothing was spent


class TheSync20261021(unittest.TestCase):
    """The 2026-10-21 video-system sync, worker 1: the brief as a shooting script, the lane, spice + realism
    into writing, cost trims undone (runs/video-system/sync/2026-10-21/CHANGES.md)."""

    def test_the_brief_pass_is_the_shooting_script(self):
        brief = (W.V2 / dict((p[0], p[4]) for p in W.PASSES)["stage5"]).read_text()
        # the shot contract's field names, exactly as production and the edit build to them
        for field in ("lane", "ask", "frames", "room_tone", "make_list", "face", "emotion", "gestures", "angle",
                      "camera_move", "hands_off", "ends_on", "start_picture", "length", "delivery_tag",
                      "emphasis", "props", "size", "look"):
            self.assertIn('"%s"' % field, brief, field)
        for move in ("push-in", "pan", "tilt", "arc", "handheld", "hold"):
            self.assertIn(move, brief)
        for join in ("continuous", "action", "match", "whip", "cut"):
            self.assertIn(join, brief)
        self.assertNotIn('"voice_settings": {', brief)         # W4: the v3 tag replaces the v2-era settings
        self.assertNotIn("`720p` or `480p`", brief)            # W25 / V6: takes are 360p
        self.assertNotIn("thirty seconds", brief)               # W25: the old clip door's limit
        self.assertNotIn("then the packshot where the product is in frame", brief)   # W8 / V16

    def test_every_pass_gets_the_lane_and_spice_reaches_spice_and_brief(self):
        for key, _sid, _fid, _n, prompt, _s in W.PASSES:
            asks = set(re.findall(r"\{([a-z0-9_]+)\}", (W.V2 / prompt).read_text()))
            self.assertIn("ask_lane", asks, key)
            if key in ("stage4g", "stage5"):
                self.assertTrue({"video_spice", "realism_index"} <= asks, key)

    def test_every_pass_keeps_its_own_name(self):
        self.assertEqual([p["name"] for p in W.plan(BRAND, "ai", "paid")], [x[3] for x in W.PASSES])

    def test_no_cost_trim_cuts_the_teardown_or_the_culture_map(self):
        for key, cuts in W.TRIMS.items():
            self.assertNotIn("tear", cuts, key)
            self.assertNotIn("cmap", cuts, key)

    def test_the_lane_input_names_only_the_ask(self):
        o = W.ask_lane({"brand": BRAND, "lane_declared": "organic"})
        self.assertIn("comment the word", o)
        self.assertIn("follow", o)
        p = W.ask_lane({"brand": BRAND, "lane_declared": "paid"})
        self.assertIn("tap the button", p)

    def test_realism_rows_are_the_writing_stage_rows(self):
        import json
        j = json.loads((COMP.parent / "video-production" / "spice" / "realism-index.json").read_text())
        want = [r["id"] for r in j["rows"] if r.get("stage") == "writing" or "writing" in (r.get("also") or [])]
        txt = W.realism_rows({})
        self.assertTrue(want)
        for rid in want:
            self.assertIn("`%s`" % rid, txt)
        prod_only = [r["id"] for r in j["rows"] if r.get("stage") == "production" and "writing" not in (r.get("also") or [])]
        for rid in prod_only:
            self.assertNotIn("`%s`" % rid, txt)

    def test_a_patch_applies_exactly_or_not_at_all(self):
        # W32: the audit's fixes patched into the build; a FIND not in the script once throws the patch away
        body = "=== PART 3: CLOSE ===\nLine one.\nTap the button below.\n"
        ans = ("=== FIX A3 ===\nPART: CLOSE\nFIND:\nTap the button below.\nREPLACE:\nComment GLOW and I'll send it.\n"
               "=== END ===\n")
        new, n = W.apply_patch(body, ans)
        self.assertEqual(n, 1)
        self.assertIn("Comment GLOW", new)
        self.assertIn("Line one.", new)
        self.assertIsNone(W.apply_patch(body, ans.replace("Tap the button below.\nREPLACE", "Not there.\nREPLACE"))[0])
        self.assertIsNone(W.apply_patch(body, "no blocks")[0])

    def test_a_patch_that_fails_falls_back_to_the_rebuild(self):
        import json, tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "stages").mkdir()
            (d / "stages" / "4cde-x.md").write_text("=== PART 1: PLACEMENT ===\nA\n")
            st = {"stages": {"stage4v2b": {"out": "stages/4cde-x.md"}}}
            (d / "run.json").write_text(json.dumps(st))
            p = dict(key="stage4v2b", file_id="4cde", model="opus", splits=[])
            fake = lambda prompt, out, model=None: out.write_text("nothing usable") or "opus"
            with mock.patch.object(W, "claude_v2", fake):
                self.assertFalse(W.patch_build(d, st, p, "RE-RUN BUILD. A1 fix the close", {"ask_lane": "paid"}))
            self.assertFalse(st["stages"]["stage4v2b"]["patches"][0]["applied"])
            self.assertEqual((d / "stages" / "4cde-x.md").read_text(), "=== PART 1: PLACEMENT ===\nA\n")

    def test_the_audit_and_its_prompt_are_untouched_by_the_patch(self):
        audit = dict((x[0], x[4]) for x in W.PASSES)["stage4e"]
        self.assertTrue(audit.startswith("stage4e-audit-v"))
        self.assertNotEqual(audit, W.PATCH_PROMPT)
        self.assertTrue((W.V2 / W.PATCH_PROMPT).is_file())

    def test_the_playbook_carries_only_what_writing_uses(self):
        # W33 (V22): the signature, what is specialised, and this run's variant row — not production's settings
        page = ("# Playbook · X (`x`)\n\n**Family:** x\n\nWhat it is.\n\n*Rendered from the .json*\n\n"
                "## Structural signature\n\n| audio | voice |\n\n## What is specialised, and why\n\n- a — b\n\n"
                "## Stage settings\n\n**clips** lots\n\n## Cost\n\n$\n\n## Variants (same workflow, refined)\n\n"
                "### one (`one`, draft)\n- differs: a\n\n### two (`two`, draft)\n- differs: b\n\n## Built from\n\n- r\n")
        out = W.playbook_for_writing(page, "two")
        for keep in ("What it is.", "## Structural signature", "## What is specialised, and why", "`two`"):
            self.assertIn(keep, out)
        for drop in ("## Stage settings", "## Cost", "`one`", "## Built from", "*Rendered from"):
            self.assertNotIn(drop, out)

    def test_the_build_gets_the_control_whole_and_each_variation_line(self):
        # W33 (V22): the body is built from the control; HOOK COMPATIBILITY needs each variation's line
        hooks = ("=== PART 1: READING ===\nlane\n=== PART 2: HOOKS ===\n**2. VERSION 0 — THE CONTROL**\nthe control\n"
                 "**3. THE FIVE VARIATIONS**\n\n**V1**\n\nTAKE V1: t\nLINE V1: the line\nCARD V1: c\n"
                 "SCROLL V1: a picture\nTHUMB V1: a thumb\n\n- **Specifics:** verbatim-xyz\n\n"
                 "**THE FORMAT TEST**\ntests\n\n**4. BRIEF VARIATION OPPORTUNITIES**\nopps\n\n## LANGUAGE USED\nrows\n")
        out = W.hooks_for_build(hooks)
        for keep in ("lane", "the control", "LINE V1: the line", "CARD V1: c", "TAKE V1: t", "opps"):
            self.assertIn(keep, out)
        for drop in ("SCROLL V1", "THUMB V1", "verbatim-xyz", "\ntests", "LANGUAGE USED"):
            self.assertNotIn(drop, out)
        self.assertEqual(W.hooks_for_build("no parts here"), "no parts here")
        self.assertIn("hooks", W.TRIMS["stage4v2b"])

    def test_spice_waits_for_a_passing_audit(self):
        # W35: spice comes after the audit in the pass order, and an audit RE-RUN jumps back before it
        keys = [x[0] for x in W.PASSES]
        self.assertLess(keys.index("stage4e"), keys.index("stage4g"))

    def test_nothing_sterile(self):
        # V23 (W36-W38): the injection keeps the swipe's bite, organic carries no offer stack, the audit fails sterile
        pr = dict((x[0], (W.V2 / x[4]).read_text()) for x in W.PASSES)
        self.assertIn("THE SWIPE'S BITE", pr["stage3"])
        self.assertIn("no offer stack", pr["stage4v2b"])
        self.assertIn("On the organic lane there is no offer", pr["stage4v2b"])
        self.assertIn("`STERILE`", pr["stage4e"])
        self.assertIn("No check here rewards softening", pr["stage4e"])

    def test_video_spice_is_the_whole_file(self):
        self.assertIn("The seven layers", W.video_spice())

    def test_the_format_playbook_reaches_every_pass(self):
        # T9: the playbook the teardown's hook builds is read by writing, through declared_layers
        fam = sorted(W.PLAYBOOKS.glob("*.md"))[0].stem
        self.assertIn("THE FORMAT'S PLAYBOOK", W.declared_layers({"format_id": fam}))
        self.assertEqual(W.format_playbook("no-such-format-xyz"), ("", ""))
        self.assertEqual(W.format_playbook("unknown"), ("", ""))

    def test_models_come_from_the_model_house(self):
        # T2-T5: the judge, the voice and the word timings are the house's, never typed in the code
        import importlib.util
        sp = importlib.util.spec_from_file_location("mh", COMP.parent / "generative-model-house" / "model_house.py")
        mh = importlib.util.module_from_spec(sp); sp.loader.exec_module(mh)
        import swipe_match as SM
        import manifest as MF
        self.assertEqual(SM.MODEL, mh.model("behind.judge"))
        self.assertEqual(MF.MODEL, mh.model("behind.judge"))
        self.assertEqual(C.GEMINI_MODEL, mh.model("behind.judge"))
        import cast_voice
        self.assertEqual(cast_voice.TTS_MODEL, mh.model("sound.voice")["model"])


if __name__ == "__main__":
    unittest.main()
