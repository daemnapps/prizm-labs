"""The research route: rows ranked to his problem, receipts that must resolve, numbers that need a source, and the block
the writing chains read. No model, no network; a made-up brand in a temp folder."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
import idea as I  # noqa: E402
import strategy as S  # noqa: E402

CARD = "# Porch painter\n- **Pain:** Paint peels on the porch rail by winter; he sands it by hand and it peels again.\n"
POS = 'PROBLEM WORD: peeling paint (40 rows)\nMECHANISM: the primer gets into the grain\nNEVER: "lasts forever" · "miracle"\n'
ROWS = [("customer_0001", "the rail peels every winter", "porch-painter", "problem-aware"), ("lead_0002", "I sand it by hand and it peels again", None, "problem-aware"),
        ("customer_0003", "love the colour of the kitchen", None, "most-aware"), ("prospect_0004", "lol the cat sat on it", None, "unaware"),
        ("customer_0005", "a brush got it in the grain", None, "solution-aware")]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        b = self.root / "brands" / "acme"
        for rel, text in {"core-avatars/owner/sub-avatars/sub-01-porch-painter.md": CARD, "core-avatars/owner/profile.md": "An owner.", "brand-identity/position.md": POS,
                          "core-avatars/objection-bank.md": "too dear", "core-avatars/owner/culture-map.md": "fishing", "products/primer.md": "Primer.",
                          "core-avatars/owner/language/all.json": json.dumps({"entries": [{"id": "language_acme_owner_" + i, "text": t, "sub": s, "awareness": {"level": a}} for i, t, s, a in ROWS]})}.items():
            (b / rel).parent.mkdir(parents=True, exist_ok=True)
            (b / rel).write_text(text)
        for p in (mock.patch.object(S, "root", return_value=self.root), mock.patch.object(S.brandpath, "brand_path", side_effect=lambda n, k, *r, **kw: b.joinpath(k, *r)),
                  mock.patch.object(S.brandpath, "brand_file", side_effect=lambda n, k, f, **kw: b / k / f)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)
        self.run_ = self.root / "runs/creative-strategist/acme/strategy/t"
        self.run_.mkdir(parents=True)
        self.ev = S.evidence("acme", "owner", "porch-painter", "primer")
        (self.run_ / "evidence.json").write_text(json.dumps(self.ev))

    def thought(self, **kw):
        obs = [{"true": "He sands by hand.", "receipts": [{"from": "lead_0002", "quote": "sand it by hand"}]}] * 8
        d = {"observations": obs, "insight": "He sands the same rail again.", "awareness": "problem-aware: at the problem", "ideas": [{"idea": "A", "line": "a"}, {"idea": "B", "line": "b"}],
             "the_one": {"idea": "Sanding is the second paint job", "line": "You paint it twice.", "see": "two hands"}, "not_cleared": ["seals it"], "missing_research": []}
        d.update(kw)
        return d


class Evidence(Base):
    def test_only_rows_about_his_problem_his_own_first(self):
        self.assertEqual(self.ev["rows"][0], "customer_0001")
        self.assertIn("lead_0002", self.ev["rows"])
        self.assertNotIn("prospect_0004", self.ev["rows"])
        self.assertNotIn("customer_0003", self.ev["rows"])

    def test_gaps_are_said_and_never_filled(self):
        self.assertTrue(any("no full profile" in g for g in self.ev["gaps"]))
        self.assertTrue(any("1 rows" in g for g in self.ev["gaps"]))

    def test_never_list_is_read_off_the_position(self):
        self.assertEqual(self.ev["never"], ["lasts forever", "miracle"])

    def test_unknown_sub_is_refused(self):
        with self.assertRaises(SystemExit):
            S.evidence("acme", "owner", "nobody", "primer")


class Receipts(Base):
    def test_clean(self):
        self.assertEqual(S.verify(self.thought(), self.ev), {})

    def test_a_quote_that_is_not_in_the_row_is_caught(self):
        o = [{"true": "x", "receipts": [{"from": "lead_0002", "quote": "I cried about it"}]}] + self.thought()["observations"]
        self.assertIn("observation 1", S.verify(self.thought(observations=o), self.ev))

    def test_an_invented_row_is_caught(self):
        o = [{"true": "x", "receipts": [{"from": "customer_9999", "quote": "peels"}]}] + self.thought()["observations"]
        self.assertIn("not a row or a file", S.verify(self.thought(observations=o), self.ev)["observation 1"][0])

    def test_a_card_quote_resolves(self):
        self.assertEqual(S.resolve([{"from": "card", "quote": "peels on the porch rail by winter"}], S.bank("acme", "owner"), S.sources(self.ev)), [])

    def test_a_number_nobody_said_is_caught(self):
        self.assertIn("30 minutes", S.verify(self.thought(insight="He spends 30 minutes a week on it."), self.ev)["insight"][0].replace("30, minutes", "30 minutes"))

    def test_a_number_spelled_out_is_caught_too(self):
        self.assertIn("eleven", S.verify(self.thought(the_one={"idea": "x", "line": "You painted it eleven times."}), self.ev)["the one"][0])

    def test_never_list_is_caught(self):
        self.assertIn("never list", S.verify(self.thought(the_one={"idea": "x", "line": "It lasts forever"}), self.ev)["the one"][0])

    def test_thin_thinking_is_held(self):
        self.assertIn("observations", S.verify(self.thought(observations=self.thought()["observations"][:3]), self.ev))


class Think(Base):
    def test_a_bad_receipt_is_sent_back_once_then_kept_clean(self):
        bad = self.thought(observations=[{"true": "x", "receipts": [{"from": "customer_9999", "quote": "peels"}]}] + self.thought()["observations"])
        answers, seen = [bad, self.thought()], []

        def caller(p):
            seen.append(p)
            return "```json\n%s\n```" % json.dumps(answers[len(seen) - 1])
        with mock.patch.object(S, "fill", return_value="ask"):
            d = S.think(self.run_, caller=caller)
        self.assertEqual(len(seen), 2)
        self.assertIn("customer_9999", seen[1])
        self.assertEqual(d["held"], {})

    def test_what_still_fails_is_dropped_never_kept(self):
        bad = self.thought(observations=[{"true": "made up", "receipts": [{"from": "customer_9999", "quote": "peels"}]}] + self.thought()["observations"])
        with mock.patch.object(S, "fill", return_value="ask"):
            d = S.think(self.run_, caller=lambda p: json.dumps(bad))
        self.assertNotIn("made up", json.dumps(d["observations"]))

    def test_two_men_never_get_the_same_idea(self):
        o = self.run_.parent / "other"
        o.mkdir()
        one = {"idea": "He only ever finished half the porch and nobody told him about the second coat", "line": "Half a coat"}
        (o / "evidence.json").write_text(json.dumps(dict(self.ev, sub="deck-owner")))
        (o / "idea.json").write_text(json.dumps(self.thought(the_one=one)))
        self.assertEqual(S.too_close(self.run_, self.thought(the_one={"idea": "Half the porch, and nobody mentioned a second coat", "line": "x"})), "deck-owner")
        self.assertEqual(S.too_close(self.run_, self.thought()), "")

    def test_it_is_shown_what_the_other_men_already_have(self):
        o = self.run_.parent / "other"
        o.mkdir()
        (o / "evidence.json").write_text(json.dumps(dict(self.ev, sub="deck-owner")))
        (o / "idea.json").write_text(json.dumps(self.thought()))
        self.assertIn("deck-owner", S.fill(self.run_, "research-to-idea"))

    def test_every_prompt_slot_is_supplied(self):
        for stem, extra in (("research-to-idea", {}), ("idea-to-form", {"idea": "i", "insight": "n", "forms": "f"})):
            self.assertNotIn("{rows}", S.fill(self.run_, stem, extra))


class Copy(Base):
    def test_machine_phrasing_is_caught(self):
        for t in ("Your barber drew it. Your neck erased it.", "You didn't fix it. You hid it.", "You weren't using the wrong product. You were using the wrong hands.",
                  "You replaced what cuts. You never replaced what cleans.", "It's not about the razor", "Peeling \u2014 again", "The tool was never the problem. The washing was.", "Imagine no peeling"):
            self.assertTrue(S.tells(t), t)

    def test_lines_that_sold_are_not_called_machine(self):
        for t in ("Ever wonder why your skin breaks out 3 days after a fresh cut?", "Still washing your face with your hands?", "Better Than Hands", "Why Popping Never Works",
                  "I thought skincare was cap until I saw this...", "Yeah, $99 was too much."):
            self.assertEqual(S.tells(t), [], t)

    def test_a_line_must_name_the_problem(self):
        rows = S.bank("acme", "owner")
        self.assertIn("does not name the problem", " ".join(S.line_faults({"text": "Two people see you this close", "kind": "fact"}, self.ev, rows)))
        self.assertEqual(S.line_faults({"text": "Porch paint peeling again?", "kind": "question"}, self.ev, rows), [])

    def test_his_words_must_be_his_words(self):
        rows = S.bank("acme", "owner")
        self.assertEqual(S.line_faults({"text": "I sand it by hand and it peels again", "kind": "his words", "row": "lead_0002"}, self.ev, rows), [])
        self.assertIn("not his words", S.line_faults({"text": "I sand it daily and it peels", "kind": "his words", "row": "lead_0002"}, self.ev, rows))

    def test_a_reader_that_throws_out_what_sold_is_ignored(self):
        win = [(9, "Sold one"), (8, "Sold two")]
        allbad = lambda p: json.dumps({"lines": [{"n": i, "about": "x", "sounds": "machine"} for i in (1, 2, 3)]})
        self.assertEqual(S.read_cold(["Ours"], win, allbad), {})


class Ask(Base):
    def make(self, **kw):
        (self.run_ / "idea.json").write_text(json.dumps(self.thought(**kw)))
        S.choose(self.run_, "owner")
        return S.strategy_block(self.run_)

    def test_problem_aware_carries_no_price(self):
        self.assertTrue(self.make()["no_price"])
        self.assertFalse(self.make(awareness="most-aware")["no_price"])

    def test_the_story_file_for_video_carries_the_idea_and_its_receipts(self):
        self.make()
        t = S.story(self.run_).read_text()
        for x in ("You paint it twice.", "lead_0002", "seals it"):
            self.assertIn(x, t)

    def test_a_static_needs_a_form_and_video_needs_none(self):
        self.make()
        f = self.root / "runs/creative-strategist/acme/a1/ask.json"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"strategy": S.strategy_block(self.run_)}))
        self.assertIn("scratch.py", S.hand(self.run_, "a1", "video")[0])
        self.assertIn("--sub %s " % self.ev["sub"], S.hand(self.run_, "a1", "video")[0])
        with self.assertRaises(SystemExit):
            S.hand(self.run_, "a1", "image")
        f.write_text(json.dumps({"strategy": S.strategy_block(self.run_, json.loads(S.FORMS.read_text())["forms"][0]["no"])}))
        self.assertIn("--ask runs/creative-strategist/acme/a1/ask.json", S.hand(self.run_, "a1", "image")[1])

    def test_a_held_idea_cannot_be_chosen(self):
        (self.run_ / "idea.json").write_text(json.dumps(self.thought(held={"insight": ["no receipt for: 30"]})))
        with self.assertRaises(SystemExit):
            S.choose(self.run_, "owner")

    def test_nothing_chosen_makes_no_ask(self):
        (self.run_ / "idea.json").write_text(json.dumps(self.thought()))
        with self.assertRaises(SystemExit):
            S.strategy_block(self.run_)

    def test_the_block_says_the_idea_wins_and_carries_receipts(self):
        b = I.block({"strategy": self.make()})
        for x in ("THIS WINS", "Sanding is the second paint job", "lead_0002", "No price", "seals it"):
            self.assertIn(x, b)

    def test_an_ask_from_the_swipe_route_is_untouched(self):
        self.assertEqual(I.block({"offer": {"lines": []}}), "")
        self.assertEqual(I.block(None), "")


class Definitions(unittest.TestCase):
    def test_forms_are_whole_and_carry_no_machine_path(self):
        d = json.loads(S.FORMS.read_text())
        self.assertEqual(len({f["no"] for f in d["forms"]}), len(d["forms"]))
        for f in d["forms"]:
            self.assertIn(f["job"], d["jobs"])
            self.assertTrue(f["swipe"]["label"].startswith("Shared Assets/"))

    def test_no_brand_or_avatar_in_the_prompts(self):
        for p in S.PROMPTS.glob("*-to-*.md"):
            self.assertNotRegex(p.read_text().lower(), r"brand_a|brand_b|\bflex\b|razor|acne")


if __name__ == "__main__":
    unittest.main()
