"""The 2026-10-21 verify pass, writing + teardown rows (runs/video-system/sync/2026-10-21/VERIFY.md rows 10, 11,
12, 17, 21, 22): every route writes on the same lane/spice/realism rules, the build pass agrees with itself, the
playbook page writing reads carries no punch-in or cover-up rule, the teardown labels continuous and action
joins, the models come from the Generative Model House, and a creator run's stage 7 takes the brief alone.

Spends nothing: no model is called.

    /usr/bin/python3 -m unittest discover -s tools/video-writing/tests
"""
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
PROMPTS = COMP / "prompts"
TD = COMP.parent / "video-teardown"
sys.path.insert(0, str(COMP / "machine"))
sys.path.insert(0, str(TD / "machine"))

import chain as C          # noqa: E402
import writing_v2 as W     # noqa: E402

BRAND = next(p.name for p in sorted((COMP.parents[1] / "brands").iterdir())
             if p.is_dir() and not p.name.startswith("_") and (p / "products").is_dir())
WRITING_KEYS = ("stage3", "stage4b", "stage4a", "stage4c", "stage4d", "stage4e", "stage4g", "stage5")


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


MH = _load("vf_model_house", COMP.parent / "generative-model-house" / "model_house.py")


def live_writing_prompts():
    """The prompt each writing stage runs on today, on both routes (v1 for creator/founder, v2 for ai)."""
    out = {("creator", s["key"]): Path(s["prompt"]) for s in C.stages(BRAND, "", "creator", "")
           if s["key"] in WRITING_KEYS}
    out.update({("ai", p[0]): W.V2 / p[4] for p in W.PASSES})
    return out


class Row10EveryRouteGetsTheLane(unittest.TestCase):
    def test_creator_and_founder_writing_prompts_ask_for_the_lane(self):
        for route in ("creator", "founder"):
            for s in C.stages(BRAND, "", route, ""):
                if s["key"] not in WRITING_KEYS:
                    continue
                asks = set(re.findall(r"\{([a-z0-9_]+)\}", Path(s["prompt"]).read_text()))
                self.assertIn("ask_lane", asks, (route, s["key"], s["prompt"]))
                self.assertEqual(s["vars"].get("ask_lane"), "~ask_lane", (route, s["key"]))
                if s["key"] in ("stage4g", "stage5"):
                    for g in ("video_spice", "realism_index"):
                        self.assertIn(g, asks, (route, s["key"]))
                        self.assertEqual(s["vars"].get(g), "~" + g, (route, s["key"]))

    def test_every_creator_slot_has_a_source(self):
        for s in C.stages(BRAND, "", "creator", ""):
            if s["key"] not in WRITING_KEYS:
                continue
            asks = set(re.findall(r"\{([a-z0-9_]+)\}", Path(s["prompt"]).read_text()))
            self.assertEqual(sorted(asks - set(s["vars"])), [], s["key"])

    def test_no_live_prompt_lets_organic_drop_the_product_or_the_sell(self):
        banned = ("may carry no product", "carries no sell", "the ask is still the click",
                  "THE ASK IS THE CLICK", "NO ENTRY: this format", "It becomes a hook asset that hands off")
        for (route, key), f in live_writing_prompts().items():
            text = f.read_text()
            # version notes may quote what they replaced: the rules are the body around them
            body = "\n".join(l for l in re.sub(r"(?s)<!--.*?-->", "", text).splitlines() if not l.startswith("*v"))
            for b in banned:
                self.assertNotIn(b, body, (route, key, f.name, b))

    def test_the_teardown_fills_the_three_inputs_on_a_v1_stage(self):
        import run as R
        st = {"brand": BRAND, "label": "vf-row10", "slug": "vf-row10", "production_route": "creator",
              "lane_declared": "organic", "stages": {}}
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "vf-row10"
            (d / "stages").mkdir(parents=True)
            (d / "prompts").mkdir()
            (d / "run.json").write_text(json.dumps(st))
            tpl = Path(tmp) / "probe-v1-owner.md"
            tpl.write_text("LANE {ask_lane}\nSPICE {video_spice}\nREALISM {realism_index}\n")
            stage = dict(key="stage4zz", id="4zz", file_id="4zz", name="Probe", prompt=str(tpl), version=1,
                         engine="claude", vars={g: "~" + g for g in C.RUN_INPUTS}, role="stage")
            seen = {}

            def fake(prompt, out, model=None):
                seen["prompt"] = prompt
                out.write_text("probe")
                return "opus"
            with mock.patch.object(R, "claude", fake), mock.patch.object(R, "TIMES", Path(tmp) / "times.json"):
                R.run_stage(d, st, stage, {"video_count": "1"})
        self.assertIn("comment the word", seen.get("prompt", ""))
        self.assertIn("The seven layers", seen["prompt"])
        self.assertNotIn("{realism_index}", seen["prompt"])

    def test_run_inputs_is_what_writing_v2_hands_every_pass(self):
        got = W.run_inputs({"brand": BRAND, "lane_declared": "paid"})
        self.assertEqual(sorted(got), sorted(C.RUN_INPUTS))
        self.assertIn("tap the button", got["ask_lane"])


class Row11TheBuildAgreesWithItself(unittest.TestCase):
    def setUp(self):
        text = (W.V2 / dict((p[0], p[4]) for p in W.PASSES)["stage4v2b"]).read_text()
        self.build = re.sub(r"(?s)^<!--.*?-->", "", text)          # the version note may quote what it replaced

    def test_the_live_build_is_v3_or_later(self):
        self.assertGreaterEqual(int(re.search(r"-v(\d+)-", dict((p[0], p[4]) for p in W.PASSES)["stage4v2b"]).group(1)), 3)

    def test_no_no_entry_verdict_and_no_click_only_ask(self):
        self.assertNotIn("NO ENTRY: this format", self.build)
        self.assertNotIn("the ask is still the click", self.build)
        self.assertIn("There is no `NO ENTRY`", self.build)
        self.assertIn("THE LANE's ask", self.build)
        # the rung map no longer sends rung 1 to a piece without an entry
        self.assertNotIn("`NO ENTRY` ≈ rung 1", self.build)

    def test_the_audit_map_matches(self):
        audit = (W.V2 / dict((p[0], p[4]) for p in W.PASSES)["stage4e"]).read_text()
        self.assertNotIn("NO ENTRY ≈ rung 1", audit)


class Row12NoPunchInsReachTheBrief(unittest.TestCase):
    def test_no_playbook_page_writing_reads_carries_a_punch_in_or_cover_up(self):
        for page in sorted(W.PLAYBOOKS.glob("*.md")):
            text = page.read_text()
            seen = W.playbook_for_writing(text)
            for bad in ("7% punch-in", "punch-ins, b-roll", "cover a fault at the edit", "punch past at the edit",
                        "or punch in past it"):
                self.assertNotIn(bad, seen, (page.name, bad))
                self.assertNotIn(bad, text, (page.name, bad))

    def test_every_playbook_page_is_rendered_from_its_json(self):
        pb = _load("vf_playbook", COMP.parent / "video-production" / "machine" / "playbook.py")
        for j in sorted(W.PLAYBOOKS.glob("*.json")):
            md = j.with_suffix(".md")
            self.assertTrue(md.is_file(), md.name)
            self.assertEqual(md.read_text(), pb.render_md(json.loads(j.read_text())), md.name)


class Row21TheTeardownLabelsEveryJoin(unittest.TestCase):
    def test_the_record_names_continuous_and_action(self):
        rec = Path(C.stages(BRAND, "", "creator", "")[1]["prompt"]).read_text()
        self.assertIn("`continuous`", rec)
        self.assertIn("`action`", rec)
        self.assertIn("continuous | action", rec)

    def test_the_frame_map_names_them_too(self):
        fm = _load("vf_framemap", TD / "machine" / "framemap.py")
        text = fm.prompt_file().read_text()
        for join in ("continuous", "action", "match", "whip"):
            self.assertIn(join, text)


class Row17ModelsFromTheHouse(unittest.TestCase):
    def test_the_teardown_reads_its_fallbacks_and_deep_model_from_the_house(self):
        judge = MH.model("behind.judge")
        busy = MH.model("behind.judge_busy")["models"]
        self.assertEqual(C.VIDEO_MODELS, [judge] + [m for m in busy if m != judge])
        self.assertEqual(C.GEMINI_FALLBACKS, [m for m in busy if m != judge])
        dp = _load("vf_deepen", TD / "machine" / "deepen.py")
        self.assertEqual(dp.MODEL, judge)

    def test_the_hand_tools_default_to_the_house_fast_read(self):
        fast = MH.model("behind.fast_read")["model"]
        for tool in ("gemini_breakdown.py", "gemini_text.py"):
            m = _load("vf_" + tool[:-3], TD / "tools" / tool)
            self.assertEqual(m.house_model("behind.fast_read"), fast)
            self.assertNotIn('default="gemini-', (TD / "tools" / tool).read_text())
        self.assertNotIn(":-gemini-", (TD / "tools" / "run-prompt.sh").read_text())

    def test_no_dead_model_field_in_extra_stages(self):
        extra = json.loads((TD / "machine" / "extra-stages.json").read_text())
        self.assertEqual([s["stage"] for s in extra["stages"] if "model" in s], [])

    def test_the_audio_teardown_reads_the_house(self):
        at = COMP.parent / "audio-teardown"
        sys.path.insert(0, str(at))
        try:
            sp = _load("vf_at_speakers", at / "speakers.py")
            g = _load("vf_at_gemini", at / "gemini.py")
        finally:
            sys.path.remove(str(at))
        self.assertEqual(sp.MODEL, MH.model("sound.speakers")["model"])
        self.assertEqual(g.MODELS[0][0], MH.model("behind.judge"))
        self.assertIn(g.MODELS[1][0], MH.model("behind.judge_busy")["models"])
        for f in ("speakers.py", "gemini.py", "effects.py"):
            self.assertNotRegex((at / f).read_text(), r"[\"'](gemini-\d|scribe_v\d)", f)


class Row22CreatorStage7AndTheBriefHistory(unittest.TestCase):
    def test_stage7_takes_the_brief_alone(self):
        s7 = next(s for s in C.stages(BRAND, "", "creator", "") if s["key"] == "stage7")
        self.assertNotIn("@stage6", s7["vars"].values())
        self.assertEqual(s7["vars"].get("brief"), "@stage5")

    def test_a_creator_run_reaches_through_stage7(self):
        import run as R
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "vf-s7"
            (d / "stages").mkdir(parents=True)
            (d / "prompts").mkdir()
            (d / "stages" / "5-brief.md").write_text("# Concept\n\nsays: hi\n")
            st = {"brand": BRAND, "label": "vf-s7", "slug": "vf-s7", "production_route": "creator",
                  "stages": {"stage5": {"status": "done", "out": "stages/5-brief.md"}}}
            (d / "run.json").write_text(json.dumps(st))
            s7 = next(s for s in C.stages(BRAND, "", "creator", "") if s["key"] == "stage7")
            with mock.patch.dict("os.environ", {"QC_VIEWER": "0"}), \
                    mock.patch.object(R, "TIMES", Path(tmp) / "times.json"):
                self.assertTrue(R.run_stage(d, st, s7, {"video_count": "1"}))
            self.assertTrue((d / "brief-final.md").is_file())

    def test_the_retired_frames_stage_only_says_so(self):
        import run as R
        with self.assertRaises(RuntimeError):
            R.frames({}, Path("."), {}, {}, Path("x"))
        self.assertNotIn("import frames as _frames", (TD / "machine" / "run.py").read_text())

    def test_the_ai_brief_no_longer_says_scenes_carry_voice_settings(self):
        brief = (W.V2 / dict((p[0], p[4]) for p in W.PASSES)["stage5"]).read_text()
        self.assertNotIn("SETTINGS line as `voice_settings`", brief)


if __name__ == "__main__":
    unittest.main()
