#!/usr/bin/env python3
"""The front of the logic layer, in the writing station (W1, 2026-11-18).

What these hold:
  - the layers reach the writing with the reason each was called what it was called;
  - what the later stations hand back (the winners feed, the edit's lessons, a winner taken apart) is in reach of
    every pass on every route, says NONE when there is nothing yet, and no live prompt reads it until it asks;
  - the dial preset follows the run's awareness level, is chosen once a run, and the hook check and the director
    read the same choice;
  - the decision trail reads as NONE when the run has none, and the brief carries its three keys (trail, idea,
    concept) the moment the stage-5 writer call lands, before anything stamps it.

No network, no spend, no real model (a fake `claude` on PATH where a writer call is needed).

    /usr/bin/python3 components/video-writing/tests/test_logic_layer_front.py
"""
import json
import os
import re
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
TD = COMP.parent / "video-teardown" / "machine"
sys.path.insert(0, str(COMP / "machine"))
sys.path.insert(0, str(TD))
import chain as C          # noqa: E402
import writing_v2 as W     # noqa: E402
import hook_matrix as H    # noqa: E402
import director as D       # noqa: E402

HANDED_BACK = ("winners_feed", "edit_lessons", "winner_breakdown")


class LayersComeWithTheirReasons(unittest.TestCase):
    def test_each_layers_reason_is_printed_under_its_name(self):
        st = {"layers": {"format": "new:desk-demo", "style": "studio-clean", "structure": "problem-solution",
                         "made": "from-scratch",
                         "_why": {"format": "one presenter at a desk shows the thing working",
                                  "style": "flat even light", "made": "every picture is generated new"}}}
        text = W.declared_layers(st)
        fmt = text.split("- **STYLE:**")[0]
        self.assertIn("`new:desk-demo`", fmt)
        self.assertIn("why it was called that: one presenter at a desk shows the thing working", fmt)
        self.assertIn("why it was called that: flat even light", text.split("- **STRUCTURE:**")[0])
        self.assertIn("why it was called that: every picture is generated new", text)
        self.assertNotIn("why it was called that", text.split("- **STRUCTURE:**")[1].split("- **HOW IT'S MADE:**")[0])

    def test_the_older_chains_reasons_are_read_from_where_it_keeps_them(self):
        st = {"format_id": "new:desk-demo", "style_id": "studio-clean", "layer_reasons": {"style": "flat even light"}}
        self.assertIn("- **STYLE:** `studio-clean`\n  - why it was called that: flat even light", W.declared_layers(st))

    def test_a_run_with_no_reasons_on_file_prints_exactly_what_it_printed_before(self):
        st = {"layers": {"format": "new:desk-demo", "style": "studio-clean", "structure": "problem-solution", "made": "from-scratch"}}
        self.assertEqual(W.declared_layers(st).splitlines()[:4], [
            "- **FORMAT:** `new:desk-demo` — a format new to the bank, approved for this run",
            "- **STYLE:** `studio-clean`", "- **STRUCTURE:** problem-solution", "- **HOW IT'S MADE:** from-scratch"])


class WhatTheLaterStationsHandBack(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        p = mock.patch.object(W, "WS", self.ws)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)
        self.st = {"brand": "brand-a"}

    def put(self, rel, text):
        f = self.ws / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)

    def test_each_says_none_in_words_when_there_is_nothing_yet(self):
        for fn in (W.winners_feed, W.edit_lessons, W.winner_breakdown):
            self.assertTrue(fn(self.st).startswith("NONE"), fn.__name__)
            self.assertTrue(fn({}).startswith("NONE"), fn.__name__)

    def test_the_winners_feed_is_what_the_winners_side_taught_for_this_brand(self):
        self.put("runs/winners/brand-a/taught.md", "# Top ads\n\n1. the mirror confession\n")
        self.put("runs/winners/brand-b/taught.md", "# another brand's\n")
        self.assertEqual(W.winners_feed(self.st), "# Top ads\n\n1. the mirror confession")

    def test_a_winner_taken_apart_is_read_from_the_winners_side(self):
        self.put("runs/winners/brand-a/breakdown.md", "HOOK: the question\nLEAD: the admission\n")
        self.assertIn("LEAD: the admission", W.winner_breakdown(self.st))

    def test_the_edits_lessons_are_the_ones_the_writing_can_act_on(self):
        self.put("components/video-edit/learned.json", json.dumps({"rules": [
            {"id": "a", "rule": "The headline is on screen from the first frame.", "scope": "every edit"},
            {"id": "b", "rule": "A line the cut had to trim is written shorter next time.", "scope": "the brief"},
            {"id": "c", "rule": "Name the prop in the scene that uses it.", "stage": "writing"}]}))
        self.put("runs/video-edit/_lessons/lessons.jsonl", "\n".join(json.dumps(r) for r in [
            {"stage": "brief", "brand": "brand-a", "lesson": "Two demos in one scene had to be split.", "at": "2026-11-10"},
            {"stage": "captions", "brand": "brand-a", "lesson": "Captions sat on the chin."},
            {"stage": "brief", "brand": "brand-b", "lesson": "Another brand's lesson."},
            {"stage": "teardown", "lesson": "A voice-only speaker was missed in the cast."}]) + "\nnot json\n")
        got = W.edit_lessons(self.st)
        self.assertIn("A line the cut had to trim is written shorter next time.", got)
        self.assertIn("Name the prop in the scene that uses it.", got)
        self.assertIn("Two demos in one scene had to be split.", got)
        self.assertIn("A voice-only speaker was missed in the cast.", got)        # brand-free: every brand reads it
        self.assertNotIn("first frame", got)                                      # an edit-only rule stays with the edit
        self.assertNotIn("chin", got)
        self.assertNotIn("Another brand", got)

    def test_every_route_can_ask_for_them_and_for_the_layers(self):
        got = W.run_inputs(self.st)
        for name in HANDED_BACK + ("declared_layers",):
            self.assertIn(name, got)
            self.assertIn(name, C.RUN_INPUTS)
            self.assertIn(name, W.RUN_INPUTS)


class AnIdeaPromptThatAsksForTheAngles(unittest.TestCase):
    def test_gets_the_list_cut_to_this_avatars_active_angles_as_the_brief_does(self):
        angles = {"angles": [
            {"id": "a1", "name": "The cost of hiding", "what": "what it costs to cover it", "avatar": "core-a", "status": "active"},
            {"id": "a2", "name": "Another reader's", "what": "not for this reader", "avatar": "core-b", "status": "active"},
            {"id": "a3", "name": "Parked", "what": "an old one", "avatar": "core-a", "status": "deprecated"}]}
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            f = ws / "brands" / "brand-a" / "strategy" / "angles.json"
            f.parent.mkdir(parents=True)
            f.write_text(json.dumps(angles, indent=1) + "\n")
            st = {"brand": "brand-a", "audience": {"_avatar": "core-a"}, "stages": {}}
            prompt = "The brand's angle list: " + f.read_text().strip() + "\n\nChoose the angle before the idea."
            with mock.patch.object(W, "WS", ws):
                got, log = W.slim(prompt, "stage4i", ws / "run", st)
                same, _ = W.slim("An idea prompt that asks for no angle list.", "stage4i", ws / "run", st)
        self.assertIn("- `a1` — The cost of hiding: what it costs to cover it", got)
        self.assertNotIn("Another reader's", got)
        self.assertNotIn("Parked", got)
        self.assertEqual([t for t, _ in log], ["angles"])
        self.assertEqual(same, "An idea prompt that asks for no angle list.")     # the live idea prompt: untouched


class NoLivePromptReadsThemUntilItAsks(unittest.TestCase):
    def test_the_live_passes_bind_none_of_the_new_inputs(self):
        for p in W.plan("any-brand", "ai", ""):
            self.assertEqual(sorted(set(HANDED_BACK) & set(p["vars"])), [], p["key"])


class TheDialPresetRuleIsOffUntilRuled(unittest.TestCase):
    def test_off_every_run_aims_at_the_house_preset_and_nothing_is_kept_or_noted(self):
        self.assertFalse(W.PRESET_FOLLOWS_AWARENESS)
        with mock.patch.dict(os.environ, {"VW_PRESET_BY_AWARENESS": ""}):
            st = {"brand": "brand-a", "market_state": {"awareness": "unaware"}}
            self.assertEqual(W.controls_preset(st)[0], W.HOUSE_PRESET)
            self.assertEqual(W.keep_controls_preset(st), W.HOUSE_PRESET)
            self.assertNotIn("controls_preset", st)
            self.assertNotIn("trail", st)
            self.assertTrue(W.controls_target(st).startswith("Preset: Maxed (maxed)"))
            self.assertNotIn("Why this preset", W.controls_target(st))


class TheDialPresetFollowsTheAwarenessLevel(unittest.TestCase):
    """With the rule switched on (the owner's tick)."""

    def setUp(self):
        p = mock.patch.dict(os.environ, {"VW_PRESET_BY_AWARENESS": "1"})
        p.start()
        self.addCleanup(p.stop)

    def st(self, level=None, **more):
        st = {"brand": "brand-a"}
        if level:
            st["market_state"] = {"awareness": level}
        st.update(more)
        return st

    def test_a_level_with_a_preset_of_its_own_takes_it_and_says_why(self):
        for level, want in (("unaware", "native-unaware"), ("problem-aware", "problem-aware"),
                            ("product-aware", "product-proof"), ("most-aware", "product-proof")):
            pid, why, lv = W.controls_preset(self.st(level))
            self.assertEqual((pid, lv), (want, level))
            self.assertIn(level, why)

    def test_a_level_with_no_preset_and_a_run_with_no_level_stay_on_the_house_preset_and_say_so(self):
        pid, why, _ = W.controls_preset(self.st("solution-aware"))
        self.assertEqual(pid, W.HOUSE_PRESET)
        self.assertIn("no preset is written for that level", why)
        pid, why, lv = W.controls_preset(self.st())
        self.assertEqual((pid, lv), (W.HOUSE_PRESET, None))
        self.assertIn("no awareness level", why)

    def test_a_preset_the_dials_file_does_not_hold_is_never_named(self):
        with mock.patch.dict(W.PRESET_BY_AWARENESS, {"unaware": "not-a-preset"}):
            self.assertEqual(W.controls_preset(self.st("unaware"))[0], W.HOUSE_PRESET)

    def test_a_hold_before_any_pass_wrote_is_not_writing_started(self):
        st = self.st("unaware", stages={"stage3": {"status": "held", "error": "no writing lane"}})
        self.assertEqual(W.controls_preset(st)[0], "native-unaware")

    def test_reading_the_target_keeps_nothing(self):
        st = self.st("unaware")
        W.controls_target(st)
        self.assertNotIn("controls_preset", st)
        self.assertNotIn("trail", st)

    def test_a_filed_matrix_names_its_preset_and_a_reader_that_passes_none_checks_against_it(self):
        asked = []

        class FakeControls:
            def target(self, preset, brand, medium):
                asked.append(preset)
                return {}, {}

            def dials(self, medium):
                return []

            def load(self):
                return {}
        with mock.patch.object(H, "controls", lambda: FakeControls()):
            H.check({"format_contract": {"a": "b"}, "openings": [], "controls_preset": "native-unaware"})
        self.assertEqual(asked, ["native-unaware"])

    def test_a_run_whose_writing_had_already_started_stays_on_the_preset_it_was_written_to(self):
        st = self.st("unaware", stages={"stage3": {"status": "done"}})
        pid, why, _ = W.controls_preset(st)
        self.assertEqual(pid, W.HOUSE_PRESET)
        self.assertIn("had started before", why)

    def test_the_swipes_own_entry_level_is_read_when_the_audience_stage_named_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "doctrine.json").write_text(json.dumps({"awareness": {"entry": "problem-aware", "exit": "most-aware"}}))
            self.assertEqual(W.controls_preset(self.st(), Path(tmp))[0], "problem-aware")

    def test_it_is_chosen_once_kept_on_the_run_and_noted_on_the_trail(self):
        st = self.st("unaware")
        self.assertEqual(W.keep_controls_preset(st), "native-unaware")
        self.assertEqual(st["controls_preset"]["preset"], "native-unaware")
        self.assertEqual(st["controls_preset"]["awareness"], "unaware")
        st["market_state"]["awareness"] = "most-aware"             # a later read never moves a run's preset
        st["stages"] = {"stage3": {"status": "done"}}
        self.assertEqual(W.keep_controls_preset(st), "native-unaware")
        rows = [r for r in st.get("trail") or [] if r["decision"] == "Dial preset"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["choice"], rows[0]["why"]), ("native-unaware", st["controls_preset"]["why"]))

    def test_the_target_every_pass_reads_names_that_preset_then_why(self):
        st = self.st("problem-aware")
        W.keep_controls_preset(st)
        text = W.controls_target(st)
        self.assertTrue(text.startswith("Preset: Problem aware (problem-aware)"))
        self.assertNotIn("Why this preset", text)                         # the reason is on the run, not in the prompt
        # the shape the Studio reads the levels back from is unchanged: the header, a blank line, one row per dial
        self.assertRegex(text, r"Preset: [^\n(]*\((?P<id>[a-z0-9_-]+)\)[^\n]*\n\s*\n(?:- [a-z_]+: -?\d[^\n]*\n)+")

    def test_the_hook_check_holds_the_openings_to_the_runs_own_preset(self):
        asked = []

        class FakeControls:
            def target(self, preset, brand, medium):
                asked.append(preset)
                return {}, {}

            def dials(self, medium):
                return []

            def load(self):
                return {}
        with mock.patch.object(H, "controls", lambda: FakeControls()):
            H.check({"format_contract": {"a": "b"}, "openings": []}, None, "native-unaware")
            H.check({"format_contract": {"a": "b"}, "openings": []})
            H.from_text('```hook-matrix\n{"format_contract": {"a": "b"}, "openings": []}\n```', None, preset="problem-aware")
        self.assertEqual(asked, ["native-unaware", "maxed", "problem-aware"])

    def test_the_director_aims_where_the_passes_before_it_aimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            self.assertEqual(D.run_preset(run), "maxed")                         # no record: the house preset
            (run / "run.json").write_text(json.dumps({"controls_preset": {"preset": "product-proof"}}))
            self.assertEqual(D.run_preset(run), "product-proof")
            self.assertTrue(D.controls_target(W.WS, None, D.run_preset(run)).startswith("Preset: Product proof (product-proof)"))


class TheDecisionTrailSlot(unittest.TestCase):
    """The plan's named tests: the trail reads as NONE when empty; its rows reach every pass."""

    def test_the_trail_reads_as_none_when_the_run_has_none(self):
        self.assertIn("decision_trail", W.RUN_INPUTS)
        self.assertIn("decision_trail", C.RUN_INPUTS)
        self.assertEqual(W.run_inputs({"brand": "brand-a"})["decision_trail"].strip(), "NONE")
        self.assertEqual(W.run_inputs({"brand": "brand-a", "trail": []})["decision_trail"].strip(), "NONE")

    def test_a_run_with_rows_hands_every_pass_the_choice_and_the_reason(self):
        import run as R
        st = {"brand": "brand-a"}
        R.trail_add(st, "1b", "Awareness level our version enters at", "unaware", "the post never names a problem", "the audience stage")
        text = W.run_inputs(st)["decision_trail"]
        self.assertIn("unaware", text)
        self.assertIn("the post never names a problem", text)


# the idea pass's answer, in the shape it is handed on in (a heading, the idea on the line under it, the candidates last)
IDEA_ANSWER = ("### THE CONTROLLING IDEA\nThe thing hidden is the thing everyone can see.\n\n"
               "### THE LINE IT TURNS ON\n\"You were never hiding it.\"\n\n"
               "### THE FIVE CANDIDATES\n| # | Idea |\n|---|---|\n| 2 | a candidate that lost |\n")


def named(value):
    """A key's own words: the line itself, or the `name` of a small record that holds it."""
    return (value.get("name") or value.get("line") or "") if isinstance(value, dict) else value


FAKE = """#!{python}
import json, sys
sys.stdin.read()
out = "# The brief\\n\\n```json\\n" + json.dumps({brief}) + "\\n```\\n"
print(json.dumps({{"result": out, "usage": {{"input_tokens": 1, "output_tokens": 1}}, "total_cost_usd": 0, "is_error": False}}))
"""
BRIEF = {"piece": {"title": "Test"}, "cast": [], "scenes": []}          # no scene to direct: the director has nothing to do


class TheBriefCarriesItsThreeKeysBeforeItIsStamped(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        bin_dir = t / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "claude"
        fake.write_text(FAKE.format(python=sys.executable, brief=repr(BRIEF)))
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.run = t / "run"
        (self.run / "stages").mkdir(parents=True)
        (self.run / "prompts").mkdir()
        self.trail = [{"stage": "1b", "decision": "Awareness level our version enters at", "choice": "unaware",
                       "why": "the post never names a problem", "by": "the audience stage"}]
        (self.run / "run.json").write_text(json.dumps({"brand": "brand-a", "stages": {}, "trail": self.trail}))
        self.idea_file = self.run / "stages" / "4i-controlling-idea.md"
        self.idea_file.write_text(IDEA_ANSWER + "\nCONCEPT: the mirror confession\nCONCEPT WHY: one voice, one room\n")
        names = ("PATH", "CLAUDE_CODE_OAUTH_TOKEN_CHAIN", "ANTHROPIC_API_KEY_CHAIN", "VT_CLAUDE_TIMEOUT")
        self.prev = {k: os.environ.get(k) for k in names}
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        os.environ["CLAUDE_CODE_OAUTH_TOKEN_CHAIN"] = "not-a-token"
        os.environ["ANTHROPIC_API_KEY_CHAIN"] = "not-a-key"
        os.environ["VT_CLAUDE_TIMEOUT"] = "60"
        self.hand = W._HAND[0]
        W._HAND[0] = None
        W._CURRENT.clear()

    def tearDown(self):
        for k, v in self.prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        W._HAND[0] = self.hand
        W._CURRENT.clear()
        self.tmp.cleanup()

    def piece(self, name="5-brief.md"):
        t = (self.run / "stages" / name).read_text()
        return json.loads(re.findall(r"```json\s*\n(.*?)\n```", t, re.S)[-1]).get("piece") or {}

    def test_trail_idea_and_concept_are_on_the_brief_when_the_stage_5_writer_call_returns(self):
        W._CURRENT["key"] = "stage5"
        W.claude_v2("Write the brief.", self.run / "stages" / "5-brief.md", "opus")
        piece = self.piece()
        for key in ("trail", "idea", "concept"):
            self.assertIn(key, piece)
        self.assertEqual(piece["title"], "Test")                                  # what the writer wrote is kept
        self.assertEqual([(r["decision"], r["choice"]) for r in piece["trail"]],
                         [(r["decision"], r["choice"]) for r in self.trail])
        self.assertIn("The thing hidden is the thing everyone can see.", named(piece["idea"]))
        self.assertNotIn("a candidate that lost", json.dumps(piece["idea"]))     # the losers are not this run's idea
        self.assertEqual(named(piece["concept"]), "the mirror confession")
        # nothing has stamped it yet: the keys were there first, so every hash taken after reads them
        self.assertNotIn("<!-- swipe-match:", (self.run / "stages" / "5-brief.md").read_text())
        self.assertNotIn("<!-- brief-read:", (self.run / "stages" / "5-brief.md").read_text())

    def test_an_idea_pass_that_names_no_concept_leaves_the_key_there_and_empty(self):
        for answer in (IDEA_ANSWER, IDEA_ANSWER + "\nCONCEPT: none\nCONCEPT WHY: none\n"):
            self.idea_file.write_text(answer)
            W._CURRENT.clear()
            W._CURRENT["key"] = "stage5"
            W.claude_v2("Write the brief.", self.run / "stages" / "5-brief.md", "opus")
            piece = self.piece()
            self.assertIn("concept", piece)
            self.assertIn(named(piece["concept"]), ("", None))
            self.assertIn("everyone can see", named(piece["idea"]))

    def test_another_pass_never_gets_them(self):
        W._CURRENT["key"] = "stage4g"
        W.claude_v2("Write it.", self.run / "stages" / "4g-spice.md", "opus")
        self.assertEqual(self.piece("4g-spice.md"), {"title": "Test"})


if __name__ == "__main__":
    unittest.main()
