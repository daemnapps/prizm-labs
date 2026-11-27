"""build.py: the inputs packet from an accepted brief, and the draft check (creator-brief-v1-owner.md, OUTPUT and BANNED)."""
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location("creator_brief_build", HERE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BLOCK = {
    "piece": {"title": "T", "ask": "Get it below.", "awareness": "solution-aware", "aspect_ratio": "9:16"},
    "openings": [{"id": "Opening 1", "say": "Would you date a guy with acne?"}],
    "scenes": [
        {"id": "S1", "section": "hook", "to_camera": True, "voice": "Which one, the before or the after?",
         "first_frame": {"subject": "two people on a street"}},
        {"id": "S3", "section": "product", "to_camera": False,
         "voice": "This is the brush that cleans out the tiny holes your hands never reach every single day.",
         "first_frame": {"subject": "the brush set down on a counter"}},
        {"id": "S9", "section": "offer", "to_camera": True,
         "voice": "There's a reason it sells out every month. 90 days or your money back."},
        {"id": "S11", "section": "call-to-action", "to_camera": False, "voice": "Get it below.",
         "first_frame": {"subject": "a man pointing at the lens"}},
    ],
}
BRIEF = "# Brief\n\n```json\n%s\n```\n" % json.dumps(BLOCK)
PRODUCT = """# Brush

## What it does

- IPX7 Waterproof
- 10 Sonic Vibrations up to 12000 RPM
- Package Includes:

## What the live store says

- An ad may say "There's a reason it sells out every month."

## The mechanism in plain terms

"Runs at 12,000 RPM" is wrong: it turns a ceiling into one speed. "Medical-grade silicone" has been written
into drafts and is invented. "Deeper than your hands reach" is the position's own claim and is safe; a depth is
not on file.
"""
GUARANTEES = {"guarantees": {"flex-device": {"surface": "device (FLEX) surfaces",
                                            "verbatim": "90 days. If your skin doesn't transform, full refund."}}}

DRAFT = """# Creator brief: Brush · test

**DRAFT. Not sent.** owner sends it, through Trybe.
**Format:** problem_solution · **Length:** 30 s · **Aspect:** 9:16 · **Ask:** Get it below.

## Hook options (pick one, say it your way)
1. Ask the lens if a girl would date a guy with acne.
2. Say your hands never got your face clean.
3. Say other stuff never did this.

## Talking points (your words, not a script)
| Beat | Time | What to get across |
|---|---|---|
| Hook | 0-2 s | One hook. |
| Problem | 2-7 s | What your skin did before. |
| Discovery | 7-15 s | How you found a brush that reaches past your hands. |
| Experience | 15-22 s | How it felt. There's a reason it sells out every month. |
| Result | 22-27 s | "90 days. If your skin doesn't transform, full refund." (guarantee) |
| CTA | 27-30 s | You'll leave the link. |

## Shots to film
1. Hands splashing (under Problem)
2. The brush on the counter (under Discovery)
3. The brush on your jaw (under Discovery)
4. You pointing at the lens (under CTA)

## Facts you can say
- IPX7 waterproof.

## Do
- Film in your own bathroom.

## Don't
- Say "Runs at 12,000 RPM".
- Say "Medical-grade silicone".
"""


class Inputs(unittest.TestCase):
    def setUp(self):
        self.m = _mod()
        self.p = self.m.build_inputs(BRIEF, PRODUCT, GUARANTEES, "brand_a", "flex", label="test")

    def test_beats_come_from_sections(self):
        self.assertEqual([x["scene"] for x in self.p["beats"]["Hook"]], ["S1"])
        self.assertEqual([x["scene"] for x in self.p["beats"]["Discovery"]], ["S3"])
        self.assertEqual([x["scene"] for x in self.p["beats"]["Result"]], ["S9"])
        self.assertEqual([x["scene"] for x in self.p["beats"]["CTA"]], ["S11"])

    def test_gaps_name_empty_beats(self):
        self.assertTrue(any("Problem" in g for g in self.p["gaps"]))

    def test_shots_are_the_silent_scenes(self):
        self.assertEqual([s["scene"] for s in self.p["shots"]], ["S3", "S11"])

    def test_facts_skip_headings(self):
        self.assertIn("IPX7 Waterproof", self.p["facts"])
        self.assertNotIn("Package Includes:", self.p["facts"])

    def test_banned_only_what_the_file_rules_out(self):
        self.assertEqual(self.p["banned"], ["Runs at 12,000 RPM", "Medical-grade silicone"])

    def test_guarantee_and_gate(self):
        self.assertEqual(self.p["guarantee"]["key"], "flex-device")
        self.assertEqual(self.p["route"], "trybe")
        self.assertIs(self.p["sent"], False)

    def test_bad_format_refused(self):
        with self.assertRaises(SystemExit):
            self.m.build_inputs(BRIEF, PRODUCT, GUARANTEES, "brand_a", "flex", ugc_format="script")


class Check(unittest.TestCase):
    def setUp(self):
        self.m = _mod()
        self.p = self.m.build_inputs(BRIEF, PRODUCT, GUARANTEES, "brand_a", "flex")

    def test_good_draft_passes(self):
        self.assertEqual(self.m.check(DRAFT, self.p), [])

    def test_copied_script_fails(self):
        bad = DRAFT.replace("How you found a brush that reaches past your hands.",
                            "This is the brush that cleans out the tiny holes your hands never reach.")
        self.assertTrue(any("word for word" in f for f in self.m.check(bad, self.p)))

    def test_header_gate(self):
        self.assertTrue(self.m.check(DRAFT.replace("**DRAFT. Not sent.**", ""), self.p))

    def test_banned_used_outside_dont(self):
        bad = DRAFT.replace("How it felt.", "It runs at 12,000 RPM.")
        self.assertTrue(any("outside Don't" in f for f in self.m.check(bad, self.p)))

    def test_price_fails(self):
        bad = DRAFT.replace("You'll leave the link.", "Only $49 today.")
        self.assertTrue(any("$49" in f for f in self.m.check(bad, self.p)))

    def test_three_hooks_and_shot_count(self):
        bad = DRAFT.replace("3. Say other stuff never did this.\n", "")
        self.assertTrue(any("hook options" in f for f in self.m.check(bad, self.p)))
        bad = DRAFT.replace("4. You pointing at the lens (under CTA)\n", "")
        self.assertTrue(any("shots" in f for f in self.m.check(bad, self.p)))

    def test_missing_beat(self):
        bad = DRAFT.replace("| Result | 22-27 s |", "| Payoff | 22-27 s |")
        self.assertTrue(any("Result" in f for f in self.m.check(bad, self.p)))

    def test_pushy_close(self):
        bad = DRAFT.replace("You'll leave the link.", "Act now, limited time.")
        self.assertTrue(any("close word" in f for f in self.m.check(bad, self.p)))

    def test_header_ask_must_be_the_briefs_ask(self):
        bad = DRAFT.replace("**Ask:** Get it below.", "**Ask:** Get it below and see for yourself.")
        self.assertTrue(any("is not the brief's ask" in f for f in self.m.check(bad, self.p)))
        self.assertTrue(any("names no Ask" in f for f in self.m.check(DRAFT.replace(" · **Ask:** Get it below.", ""), self.p)))

    def test_a_long_ask_in_the_header_is_not_a_copied_line(self):
        block = json.loads(json.dumps(BLOCK))
        long_ask = "Tap below, king. Try the brush and see for yourself."
        block["piece"]["ask"] = long_ask
        block["scenes"][3]["voice"] = long_ask
        p = self.m.build_inputs("```json\n%s\n```" % json.dumps(block), PRODUCT, GUARANTEES, "brand_a", "flex")
        self.assertEqual(self.m.check(DRAFT.replace("**Ask:** Get it below.", "**Ask:** " + long_ask), p), [])

    def test_prompt_has_its_placeholder(self):
        self.assertIn("{inputs_json}", (HERE / "creator-brief-v1-owner.md").read_text())


class LedgerAsk(unittest.TestCase):
    """The creator brief's ask is the series ledger's ask for that ad, word for word."""
    LEDGER = {"series": "s", "current": 1, "arc": [{"ad": 1, "ask": "Get it below."}, {"ad": 2, "ask": "Get yours below."}]}

    def setUp(self):
        self.m = _mod()

    def test_inputs_carry_the_ledgers_ask_when_it_matches(self):
        p = self.m.build_inputs(BRIEF, PRODUCT, GUARANTEES, "brand_a", "flex", ledger=self.LEDGER)
        self.assertEqual(p["ledger"], {"series": "s", "ad": 1, "ask": "Get it below.", "rules": []})
        self.assertEqual(self.m.check(DRAFT, p), [])

    def test_inputs_take_the_ledgers_ask_as_filed_when_the_brief_says_another(self):
        p = self.m.build_inputs(BRIEF, PRODUCT, GUARANTEES, "brand_a", "flex", ledger=self.LEDGER, ad=2)
        self.assertEqual(p["ledger"], {"series": "s", "ad": 2, "ask": "Get yours below.", "rules": []})
        self.assertEqual(self.m.check(DRAFT.replace("**Ask:** Get it below.", "**Ask:** Get yours below."), p), [])
        self.assertTrue(any("differs from the ledger's ask for ad 2" in f for f in self.m.check(DRAFT, p)))

    def test_the_ledgers_rules_for_the_ad_ride_along(self):
        led = dict(self.LEDGER, rules=[{"id": "R1", "rule": "row 0761 stays a card", "ads": [1, 3]},
                                       {"id": "R2", "rule": "ad 2 only", "ads": [2]}])
        p = self.m.build_inputs(BRIEF, PRODUCT, GUARANTEES, "brand_a", "flex", ledger=led)
        self.assertEqual(p["ledger"]["rules"], ["row 0761 stays a card"])

    def test_nothing_stacked_on_the_guarantee_is_carried(self):
        g = {"guarantees": {"flex-device": {"surface": "device", "verbatim": "90 days.",
                                            "stacks_with": {"rule": "plus a $100 store credit"}}}}
        p = self.m.build_inputs(BRIEF, PRODUCT, g, "brand_a", "flex")
        self.assertEqual(p["guarantee"], {"key": "flex-device", "verbatim": "90 days."})
        self.assertTrue(any("$100" in f for f in self.m.check(DRAFT.replace("How it felt.", "How it felt. $100 back."), p)))

    def test_check_fails_when_the_draft_ask_differs_from_the_ledger(self):
        p = self.m.build_inputs(BRIEF, PRODUCT, GUARANTEES, "brand_a", "flex")
        led = {"series": "s", "current": 1, "arc": [{"ad": 1, "ask": "Get it below and believe it."}]}
        found = self.m.check(DRAFT, p, ledger=led)
        self.assertTrue(any("differs from the ledger's ask for ad 1" in f for f in found))

    def test_spacing_and_curly_apostrophes_are_the_same_ask(self):
        self.assertTrue(self.m.same_ask("Don\u2019t wait,  get it.", "Don't wait, get it."))
        self.assertFalse(self.m.same_ask("Get it below.", "Get it below and see for yourself."))

    def test_the_header_says_who_when_the_run_has_an_aim_and_nothing_when_it_has_none(self):
        self.assertNotIn("who", self.m.build_inputs(BRIEF, PRODUCT, GUARANTEES, "b", "p"))
        aim = {"avatar": "a1", "sub": "night-worker", "demographic": "m/25-34", "doubt": "for-me", "desire": "x", "awareness": "unaware"}
        p = self.m.build_inputs(BRIEF, PRODUCT, GUARANTEES, "b", "p", aim=aim)
        self.assertTrue(p["who"].startswith("**Who:** a1 · night-worker · m/25-34 · doubt to close: "))
        self.assertNotIn("for-me", p["who"])                    # the doubt in plain words, never its id
        self.assertNotIn("unaware", p["who"])
        self.assertTrue(any("who line" in f for f in self.m.check(DRAFT, p)))
        line = DRAFT.replace("**Ask:** Get it below.\n", "**Ask:** Get it below.\n" + p["who"] + "\n", 1)
        self.assertFalse(any("who line" in f or "Ask" in f for f in self.m.check(line, p)))

    def test_the_prompts_header_carries_the_line_off_the_runs_own_record(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "stages").mkdir()
            (Path(d) / "run.json").write_text(json.dumps({"aim": {"avatar": "a1", "sub": "night-worker"}}))
            f = Path(d) / "stages" / "5-brief.md"
            f.write_text(BRIEF)
            self.assertEqual(self.m.who_line(self.m.run_aim(f)), "**Who:** a1 · night-worker")
            (Path(d) / "run.json").write_text("{}")
            self.assertIsNone(self.m.run_aim(f))



if __name__ == "__main__":
    unittest.main()
