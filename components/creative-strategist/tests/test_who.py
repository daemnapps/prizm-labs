"""who.py: one read of who an ad is for and what it must say (no model, no brand: a made-up brand on disk)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import strategy as S  # noqa: E402
import who  # noqa: E402


class Who(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        r = Path(self.t.name)
        a = r / "brands" / "acme" / "core-avatars" / "sore-foot"
        (a / "language").mkdir(parents=True)
        (a / "sub-avatars" / "sub-01-runner" / "language").mkdir(parents=True)
        (a / "profile.md").write_text('# Sore foot\n\n- **Core desire:** "I want to walk without heel pain every morning"\n\n### demographics\nage: 30-50\ngender: any\n')
        (a / "sub-avatars" / "sub-01-runner.md").write_text('### sub-01-runner\n\n- **Id / narrowed by:** Situation\n- **Core desire:** "I want to run without heel pain"\n- **Pain:** Heel pain stops the run at mile two\n\n### language-delta — x\n- "my heel barks at mile two"\n')
        rows = lambda n, sub: {"entries": [{"id": "language_acme_sore-foot_%s" % n, "text": "my heel pain stops the run at mile two", "sub": sub, "status": "active"}]}
        (a / "language" / "core.json").write_text(json.dumps(rows("c1", None)))
        (a / "sub-avatars" / "sub-01-runner" / "language" / "r.json").write_text(json.dumps({"entries": [{"id": "language_acme_sore-foot_s1", "text": "heel pain every run and I quit", "sub": "runner", "status": "active"}]}))
        (r / "brands" / "acme" / "core-avatars" / "objection-bank.md").write_text("## other-foot\n- \"too dear\"\n\n## sore-foot\n- \"insoles never worked\"\n")
        (r / "brands" / "acme" / "core-avatars" / "other-foot").mkdir()
        (r / "brands" / "acme" / "core-avatars" / "other-foot" / "profile.md").write_text("# other")
        self.r = r
        self.m = [mock.patch.object(S, "root", lambda: r), mock.patch.dict(who._ROWS, {}, clear=True)]
        for m in self.m:
            m.start()

    def tearDown(self):
        for m in self.m:
            m.stop()
        self.t.cleanup()

    def test_id_and_file_name_are_the_same_sub(self):
        self.assertEqual(who.resolve("acme", "sore-foot", "sub-01-runner")[0], "runner")
        self.assertEqual(who.block("acme", "sore-foot", "runner"), who.block("acme", "sore-foot", "sub-01-runner"))

    def test_a_named_sub_that_does_not_exist_stops(self):
        with self.assertRaises(SystemExit):
            who.block("acme", "sore-foot", "nobody")

    def test_block_carries_person_message_words_and_only_his_objections(self):
        b = who.block("acme", "sore-foot", "runner", "female/35-44/white", {"awareness": "problem-aware", "doubt": "for-me", "desire": "run again"})
        for x in (who.MARK, "walk without heel pain", "my heel barks at mile two", "female/35-44/white", "problem-aware", "same skin or hair", "run again", "insoles never worked", "heel pain every run and I quit"):
            self.assertIn(x, b)
        self.assertNotIn("too dear", b)

    def test_culture_is_on_every_block_and_only_theirs(self):
        (self.r / "brands/acme/core-avatars/sore-foot/culture-map.md").write_text(
            "# Culture map\n\n## What they watch and listen to\n\n### Core feed\n- trail films [post:http://x]\n\n### runner (race days)\n- parkrun clips\n\n### walker\n- dog walks\n\n"
            "### Barrio (Spanish-dominant)\n- Canelo fights\n\n## Off-limits\n- injury jokes\n")
        (self.r / "brands/acme/core-avatars/sore-foot/sub-avatars/sub-02-walker.md").write_text("- **Core desire:** \"I want to walk\"\n")
        b = who.block("acme", "sore-foot", "runner")
        for x in ("Their world", "trail films", "parkrun clips", "injury jokes"):
            self.assertIn(x, b)
        for x in ("dog walks", "Canelo", "http://x"):
            self.assertNotIn(x, b)
        self.assertIn("Canelo", who.block("acme", "sore-foot", "runner", "male/25-34/latino"))

    def test_a_profile_is_written_from_own_lines_and_names_what_research_answers(self):
        ans = {"profile-sort": {"his": ["s1"], "asks": []},
               "profile": {"desire": {"text": "I want to run again", "lines": ["s1"], "from": "own"}, "experiences": [{"text": "Quit running", "lines": ["s1"]}, {"text": "Made up", "lines": ["zz"]}],
                           "emotions": [{"text": "Wider thing", "lines": ["c1"], "from": "own"}], "behaviors": [], "culture": [], "missing": ["What did they try?"]},
               "profile-check": {"bad": []}}

        def caller(p):
            k = "profile-sort" if "Which of these lines" in p else ("profile-check" if "Is every line really" in p else "profile")
            return "```json\n%s\n```" % json.dumps(ans[k])
        f_, t = who.file_profile("acme", "sore-foot", "runner", caller=caller)
        d = json.loads(f_.read_text())
        for x in ("1 lines are this person's own", "I want to run again", "Quit running", "What did they try?", "heel pain every run"):
            self.assertIn(x, t)
        self.assertNotIn("Made up", t)
        self.assertEqual(d["emotions"][0]["from"], "shared")            # the line decides, never the writer's label
        self.assertEqual(who.stamp("acme", "sore-foot", "runner", "female/35-44/white")["profile"], "sore-foot_runner_female-35-44-white")

    def test_the_person_lives_once_and_joins_a_look_and_rides_with_the_piece(self):
        p = {"name": "sore-foot_runner", "brand": "acme", "avatar": "sore-foot", "sub": "runner", "own_lines": 1, "desire": {"text": "I want to run again", "lines": ["s1"], "from": "own"}, "experiences": [], "emotions": [], "behaviors": [],
             "culture": [], "doubt": None, "opening": None, "missing": [], "lines": {"s1": {"text": "heel pain every run and I quit", "dataset": "x"}}}
        d = who.draft("acme", "sore-foot", "runner")
        d.parent.mkdir(parents=True)
        d.write_text(json.dumps(p))
        self.assertEqual(who.index("acme")[0]["state"], "waiting for the owner")
        h = who.home("acme", "sore-foot", "runner")
        self.assertEqual(h.parts[-3:], ("sub-avatars", "sub-01-runner", "profile.json"))
        h.write_text(json.dumps(dict(p, desire={"text": "I want my runs back", "lines": ["s1"], "from": "own"})))
        self.assertEqual(who.filed("acme", "sore-foot", "runner")["desire"]["text"], "I want my runs back")      # the owner's wins
        self.assertEqual(who.index("acme")[0]["state"], "update waiting for the owner")
        d.unlink()
        self.assertEqual(who.index("acme")[0]["state"], "in the brand folder")
        one, two = who.full("acme", "sore-foot", "runner", "female-35-44-white"), who.full("acme", "sore-foot", "runner", "male-18-24-black")
        self.assertEqual(one["person"], two["person"])
        self.assertNotEqual(one["name"], two["name"])
        out = self.r / "runs" / "a-brief"
        who.attach(out, "acme", "sore-foot", "runner", "female-35-44-white", {"awareness": "problem-aware", "doubt": "for-me"})
        j = json.loads((out / "profile.json").read_text())
        self.assertEqual((j["person"]["desire"]["text"], j["message"]["awareness"], j["look"]["demographic"]), ("I want my runs back", "problem-aware", "female-35-44-white"))
        for x in ("I want my runs back", "female, 35-44, white", "heel pain every run"):
            self.assertIn(x, (out / "profile.md").read_text())

    def test_a_person_hears_the_brands_own_customers_filed_under_another(self):
        d = self.r / "brands/acme/core-avatars/other-foot/language/customers"
        d.mkdir(parents=True)
        (d / "all.json").write_text(json.dumps({"entries": [{"id": "language_acme_other-foot_customer_1", "text": "heel pain every morning for ten years", "sub": "x", "status": "active"}]}))
        (d.parent / "prospects.json").write_text(json.dumps({"entries": [{"id": "language_acme_other-foot_prospect_1", "text": "heel pain jokes", "status": "active"}] * 1}))
        who._ROWS.clear()
        b = who.bank("acme", "sore-foot")
        self.assertEqual(b["other-foot:customer_1"]["sub"], None)
        self.assertEqual(who.where("acme", "sore-foot")["other-foot:customer_1"], "brands/acme/core-avatars/other-foot/language/customers/all.json")
        self.assertIn("other-foot:customer_1", S.voices("acme", "sore-foot"))

    def test_a_product_is_only_sold_where_it_is_ruled(self):
        f = self.r / "runs/creative-strategist/acme/products/body-parts.json"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"products": {"balm": {"heels": {"ok": "yes"}, "palms": {"ok": "no"}}}}))
        self.assertEqual(who.body_parts("acme"), {"balm": ["heels"]})
        with mock.patch.object(who.N, "new_names", lambda b, a, s="": (a, "where-" + s)):
            self.assertIsNone(who.fits("acme", "balm", "sore-foot", "heels"))
            self.assertIsNone(who.fits("acme", "balm", "sore-foot", "feet"))             # a group: some of it is ruled
            self.assertIn("ruled out for palms", who.fits("acme", "balm", "sore-foot", "palms"))
            self.assertIn("not ruled for knees", who.fits("acme", "balm", "sore-foot", "knees"))
            self.assertIn("not a part of the body", who.fits("acme", "balm", "sore-foot", "tail"))
            self.assertIn("cannot be seen without a mirror", who.place("acme", "sore-foot", "back-of-head"))
        self.assertIsNone(who.fits("acme", "balm", "sore-foot", "runner"))          # a person about no place
        b = who.block("acme", "sore-foot", "runner", what={"product": "balm"})
        self.assertIn("Used only on: heels", b)
        self.assertNotIn("Used only on", who.block("acme", "sore-foot", "runner"))   # no product named: no long list
        with mock.patch.object(who.N, "new_names", lambda b, a, s="": (a, "where-palms")):
            with self.assertRaises(SystemExit) as e:
                who.block("acme", "sore-foot", "runner", what={"product": "balm"})
            self.assertIn("ruled out for palms", str(e.exception))
        with mock.patch.object(who.N, "new_names", lambda b, a, s="": (a, "where-heels")):
            b = who.block("acme", "sore-foot", "runner", what={"product": "balm"})
            self.assertIn("This piece is about the heels. Places close by may be mentioned with it: ankles", b)
            self.assertNotIn("knees", b.split("This piece is about")[1].split("\n")[0])
            self.assertEqual(who.stamp("acme", "sore-foot", "runner")["where"], "heels")
            f = who.full("acme", "sore-foot", "runner", what={"product": "balm"})
            self.assertEqual((f["body"]["part"], f["body"]["products_yes"]), ("heels", ["balm"]))
            self.assertIn("## Where on the body", who.full_page(f))
            self.assertIn("one place on the body: the heels", who.unknowns("acme", "sore-foot", "runner")[0])

    def test_build_stops_at_the_price_then_researches_on_the_owners_words_and_the_writers_read_it(self):
        import types
        first = {"profile-sort": {"his": ["s1"], "asks": []}, "profile-check": {"bad": []},
                 "profile": {"desire": {"text": "I want to run again", "lines": ["s1"]}, "experiences": [], "emotions": [], "behaviors": [], "culture": [], "missing": ["What did they try?"]}}

        def caller(p):
            if "What to search for" in p:
                return '```json\n{"reddit":{"rooms":["r"],"searches":["heel pain run"]},"youtube":{"searches":["x"]},"tiktok":{"searches":["y"]}}\n```'
            k = "profile-sort" if "Which of these lines" in p else ("profile-check" if "Is every line really" in p else "profile")
            a = json.loads(json.dumps(first[k]))
            if k == "profile-sort" and "insoles gave me two good weeks" in p:
                a["his"] = ["s1"] + [x for x in __import__("re").findall(r"\[(research_[^\]]+)\]", p)]
            if k == "profile" and "insoles gave me two good weeks" in p:
                rid = __import__("re").search(r"\[(research_[^\]]+)\]", p).group(1)
                a["experiences"], a["missing"] = [{"text": "Insoles worked for two weeks", "lines": [rid]}], []
            return "```json\n%s\n```" % json.dumps(a)
        P = who._research()
        calls = []
        with mock.patch.object(P.engine, "WORKSPACE", self.r):
            f, state = who.build("acme", "sore-foot", "runner", "female-35-44-white", caller=caller, pull=lambda *a: calls.append(a), say=lambda *a: None)
            self.assertEqual((state, calls), ("planned", []))                       # no words from the owner: nothing spent
            f, state = who.build("acme", "sore-foot", "runner", "female-35-44-white", cap=2, go="yes", caller=caller, say=lambda *a: None,
                                 pull=lambda p, c: ([P.line("insoles gave me two good weeks then my heel went again mid run", "reddit r/x", "https://u/1")], []))
            self.assertEqual(state, "researched")
            d = json.loads(f.read_text())
            self.assertEqual(d["experiences"][0]["text"], "Insoles worked for two weeks")
            self.assertIn("runs/research/acme/person-runner", list(d["lines"].values())[-1]["dataset"])
            b = who.block("acme", "sore-foot", "runner", "female-35-44-white")
            for x in ("Insoles worked for two weeks", "insoles gave me two good weeks", "written from their own lines"):
                self.assertIn(x, b)
            self.assertFalse([x for x in who.index("acme") if x["sub"] == "runner"][0]["stale"])
            (self.r / "brands/acme/core-avatars/sore-foot/language/new.json").write_text('{"entries":[{"id":"language_acme_sore-foot_n1","text":"heel again","status":"active"}]}')
            self.assertTrue([x for x in who.index("acme") if x["sub"] == "runner"][0]["stale"])                          # a source moved on

    def test_only_measured_mechanics_with_their_gates(self):
        m = json.loads((S.DOCTRINE.parent / "mechanics.json").read_text())
        b = who.block("acme", "sore-foot", "runner")
        measured = [r for r in m["mechanics"] if r["tier"] == "measured" and any(not r[k].lower().startswith("no move") for k in ("ad", "email", "page"))]
        for r in measured:
            self.assertIn("`%s`" % r["id"], b)
        for r in m["mechanics"]:
            if r["tier"] != "measured":
                self.assertNotIn("`%s`" % r["id"], b)
        self.assertIn("never estimated", b)

    def test_sub_rows_are_read(self):
        self.assertIn("s1", who.bank("acme", "sore-foot"))

    def test_stamp_is_the_same_decision(self):
        s = who.stamp("acme", "sore-foot", "sub-01-runner", None, {"awareness": "unaware"})
        self.assertEqual((s["avatar"], s["sub"], s["awareness"]), ("sore-foot", "runner", "unaware"))

    def test_fill_drops_what_no_row_says(self):
        ans = {"desires": [{"want": "I want to run", "human": ["comfort", "made-up"], "rows": ["c1"]}, {"want": "I want fame", "rows": ["zz"]}], "roles": [], "beliefs": [], "emotions": [],
               "doubts": {"for-me": {"said": "heel pain every run", "rows": ["s1"]}, "trust-you": {"said": "they all lie", "rows": ["c1"]}}, "doubt_lead": "for-me", "awareness_lead": "problem-aware", "stage": "x"}
        f, d = who.fill("acme", "sore-foot", caller=lambda p: "```json\n%s\n```" % json.dumps(ans), tries=1)
        self.assertEqual([x["want"] for x in d["desires"]], ["I want to run"])
        self.assertEqual(d["desires"][0]["human"], ["comfort"])
        self.assertEqual(list(d["doubts"]), ["for-me"])
        self.assertEqual(d["state"], "proposed")
        self.assertIn("runs", f.parts)


if __name__ == "__main__":
    unittest.main()
