"""static_plan: the winner's rows are one change each, checked with no model. No network.

    python3 components/ad-variations/machine/test_static_plan.py
"""
import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import static_plan as SP  # noqa: E402

W = ["BLACK FRIDAY", "FLEX starting at $49", "90-day money-back guarantee"]


def plan(rows):
    return {"locks": [{"element": "layout", "why": "x"}], "levers": [{"element": "wall", "kind": "picture", "rank": 1, "why": "x"}],
            "rows": rows}


GOOD = [
    {"id": "w1", "kind": "picture", "lever": "wall", "label": "a", "words": W, "picture": "slate wall", "why": "x"},
    {"id": "w2", "kind": "picture", "lever": "ground", "label": "b", "words": W, "picture": "white marble ground", "why": "x"},
    {"id": "w3", "kind": "copy", "lever": "event line", "label": "c", "words": ["LAST CHANCE"] + W[1:], "picture": "", "why": "x"},
    {"id": "w4", "kind": "copy", "lever": "proof line", "label": "d", "words": W[:2] + ["Keep it 90 days, or your money back"], "picture": "", "why": "x"},
]


class Check(unittest.TestCase):
    def test_clean_plan_passes(self):
        self.assertEqual(SP.check(plan(GOOD), never=["50% off"], prices={"$49"}, n_rows=4), [])

    def test_a_copy_row_may_change_one_zone_only(self):
        rows = [dict(r) for r in GOOD]
        rows[2] = dict(rows[2], words=["LAST CHANCE", "FLEX now $49", W[2]])
        self.assertTrue(any("changes 2 word zones" in p for p in SP.check(plan(rows), n_rows=4)))

    def test_a_copy_row_never_changes_the_picture_too(self):
        rows = [dict(r) for r in GOOD]
        rows[2] = dict(rows[2], picture="and a new wall")
        self.assertTrue(any("two changes" in p for p in SP.check(plan(rows), n_rows=4)))

    def test_a_picture_row_keeps_the_winners_words(self):
        rows = [dict(r) for r in GOOD]
        rows[1] = dict(rows[1], words=["CYBER MONDAY"] + W[1:])
        self.assertTrue(any("words differ" in p for p in SP.check(plan(rows), n_rows=4)))

    def test_banned_lines_and_unsold_prices_are_caught(self):
        rows = [dict(r) for r in GOOD]
        rows[3] = dict(rows[3], words=W[:2] + ["50% OFF, was $99.99"])
        p = " | ".join(SP.check(plan(rows), never=["50% off"], prices={"$49"}, n_rows=4))
        self.assertIn("banned line (50% off)", p)
        self.assertIn("$99.99 is not a price", p)

    def test_a_lever_the_feed_cannot_see_is_caught(self):
        rows = [dict(r) for r in GOOD]
        rows[1] = dict(rows[1], lever="Downlight intensity")
        self.assertTrue(any("too small" in p for p in SP.check(plan(rows), n_rows=4)))

    def test_rows_build_on_the_control(self):
        X = ["CHRISTMAS"] + W[1:]
        p = dict(plan([dict(GOOD[0], words=X), dict(GOOD[1], words=W)]), control={"words": X, "picture": "wreath"})
        self.assertEqual([x for x in SP.check(p, n_rows=2)], ["w2: a picture row whose words differ from the other picture rows (the winner's words stay)"])
        self.assertEqual(SP.to_rows(p)[0]["id"], "control")

    def test_both_kinds_and_the_count(self):
        p = " | ".join(SP.check(plan([GOOD[0], GOOD[1], dict(GOOD[0], id="w5"), dict(GOOD[1], id="w6")]), n_rows=6))
        self.assertIn("only one kind", p)
        self.assertIn("4 rows, 6 were asked", p)

    def test_rows_hand_over_in_the_variation_row_shape(self):
        rows = SP.to_rows(plan(GOOD))
        self.assertEqual(set(rows[0]) >= {"id", "label", "words", "picture", "swap"}, True)
        self.assertEqual(rows[2]["words"], ["LAST CHANCE / FLEX starting at $49 / 90-day money-back guarantee"])
        self.assertEqual(rows[2]["picture"], "")


class Plan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        SP.RUNS = Path(self.tmp.name)
        rd = SP.RUNS / "image-teardown/acme/win/out"; rd.mkdir(parents=True)
        (rd / "01-teardown.md").write_text("<!-- x -->\nthe teardown")
        (rd / "02-replication-spec.md").write_text("the copy zones")

    def tearDown(self):
        self.tmp.cleanup()

    def test_sent_back_once_then_bad_rows_dropped_and_named(self):
        bad = [dict(r) for r in GOOD]; bad[2] = dict(bad[2], picture="x")
        answers = iter(["```json\n" + json.dumps(plan(bad)) + "\n```", "```json\n" + json.dumps(plan(bad)) + "\n```"])
        seen = []
        SP.offer_prices = lambda brand: {"$49"}
        import brandctx
        brandctx.BrandContext = lambda repo, brand: type("C", (), {"rules": lambda self: "rules"})()
        doc = SP.plan("acme", "win", "lab", n_rows=4, say=lambda *_: None, ask_fn=lambda t: (seen.append(t), next(answers))[1])
        self.assertIn("What broke last time", seen[1])
        self.assertEqual(doc["dropped"], ["w3"])
        v = json.loads((SP.RUNS / "ad-variations/acme/lab/variations.json").read_text())
        self.assertEqual([r["id"] for r in v["variations"]], ["w1", "w2", "w4"])


if __name__ == "__main__":
    unittest.main()
