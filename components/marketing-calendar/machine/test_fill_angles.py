"""Holiday fill sends get an angle of their own, asked once and cached (2026-11-06). No model, no network."""
import json
import tempfile
import unittest
from pathlib import Path

import fill_angles as F

COPIED = "He has never had a routine"


def month():
    def fill(i, date, t):
        return {"id": f"m-{i:02d}", "date": date, "hour": 9, "type": t, "role": "asks", "occasion": "x",
                "product": "p", "offer": "p", "segments": ["Core | Lead", "Core | VIP Customer"],
                "variants": [{"avatar": "a", "angle": COPIED}, {"avatar": "b", "angle": COPIED}],
                "why": "holiday period: send 2 of 2 on " + date}
    own = {"id": "m-01", "date": "2026-12-01", "hour": 17, "type": "routine", "variants": [{"avatar": "a", "angle": "Own angle"}],
           "why": "a recorded problem"}
    return [own, fill(2, "2026-12-01", "proof-drop"), fill(3, "2026-12-02", "guarantee")]


class FillAngles(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.calls = []

    def ask(self, prompt, model):
        self.calls.append(prompt)
        return 'Sure: {"m-02": "Proof angle", "m-03": "Risk angle", "m-99": "stray"}'

    def test_each_fill_send_gets_its_own_angle_and_keeps_the_copied_one(self):
        s = month()
        F.apply(s, "b", self.tmp, self.tmp, "2026-12", ask=self.ask)
        self.assertEqual([v["angle"] for v in s[1]["variants"]], ["Proof angle", "Proof angle"])
        self.assertEqual(s[2]["variants"][0]["angle"], "Risk angle")
        self.assertEqual(s[1]["variants"][0]["angle_copied"], COPIED)
        self.assertEqual(s[0]["variants"][0]["angle"], "Own angle")          # not a fill send: untouched

    def test_the_prompt_names_every_segment_and_the_month_s_other_angles(self):
        F.apply(month(), "b", self.tmp, self.tmp, "2026-12", ask=self.ask)
        p = self.calls[0]
        self.assertIn("m-02", p)
        self.assertIn("Lead, VIP Customer", p)
        self.assertIn("Own angle", p)
        self.assertNotIn("- " + COPIED, p.split("## The sends")[0].split("## Angles")[1])

    def test_fill_sends_sharing_one_variants_list_each_keep_their_own_angle(self):
        s = month()
        shared = s[1]["variants"]
        s[2]["variants"] = shared                     # how holiday_fill hands them out
        F.apply(s, "b", self.tmp, self.tmp, "2026-12", ask=self.ask)
        self.assertEqual(s[1]["variants"][0]["angle"], "Proof angle")
        self.assertEqual(s[2]["variants"][0]["angle"], "Risk angle")

    def test_a_replay_reuses_the_cache_and_asks_nothing(self):
        F.apply(month(), "b", self.tmp, self.tmp, "2026-12", ask=self.ask)
        s = month()
        F.apply(s, "b", self.tmp, self.tmp, "2026-12", ask=self.ask)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(s[2]["variants"][0]["angle"], "Risk angle")

    def test_a_send_with_no_answer_keeps_its_angle_and_is_logged(self):
        s = month()
        log = F.apply(s, "b", self.tmp, self.tmp, "2026-12", ask=lambda p, m: '{"m-02": "Only one"}')
        self.assertEqual(s[2]["variants"][0]["angle"], COPIED)
        self.assertTrue(any("got no angle back" in x for x in log))

    def test_a_month_with_no_fill_sends_never_asks(self):
        s = month()[:1]
        self.assertEqual(F.apply(s, "b", self.tmp, self.tmp, "2026-12", ask=self.ask), [])
        self.assertEqual(self.calls, [])

    def test_unparseable_answers_give_nothing(self):
        self.assertEqual(F.parse("no json here", {"m-02"}), {})
        self.assertEqual(F.parse('["m-02"]', {"m-02"}), {})


if __name__ == "__main__":
    unittest.main()
