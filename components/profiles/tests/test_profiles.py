"""profiles: the standard, the gates, merges, per-brand data and criteria, all on a made-up brand (no real brand on disk)."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import profiles as P                                                                                    # noqa: E402

W, N = P.W, P.N
ROWS = {"a": ["r%d" % i for i in range(0, 40)], "b": ["r%d" % i for i in range(30, 70)], "c": ["r%d" % i for i in range(100, 140)]}


def slots(rows):
    item = lambda k, rs: {k: "x", "rows": rs}                                                         # noqa: E731
    return {"desires": [item("want", rows[:5])], "roles": [item("role", rows[5:8])], "beliefs": [item("belief", rows[8:14])],
            "experiences": [item("fact", rows[14:22])], "behaviors": [item("does", rows[22:30])], "emotions": [item("feel", rows[30:38])],
            "doubts": {k: {"said": "x", "rows": rows[:2]} for k in W.DOUBTS}, "awareness_lead": "problem-aware", "stage": "heard it all", "gaps": []}


class Brand(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        r = self.r = Path(self.t.name)
        core = r / "brands" / "acme" / "core-avatars" / "sore-foot"
        for sub in ("runner", "walker", "nurse"):
            (core / "sub-avatars" / ("sub-01-" + sub)).mkdir(parents=True)
            (core / "sub-avatars" / ("sub-01-" + sub + ".md")).write_text("### sub\n")
        (core / "profile.md").write_text("# Sore foot\n")
        for sub, k in (("runner", "a"), ("walker", "b"), ("nurse", "c")):
            f = r / "runs" / "creative-strategist" / "acme" / "who" / "sore-foot" / (sub + ".json")
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(slots(ROWS[k])))
        (core.parent / "people.json").write_text(json.dumps({"avatars": {"sore-foot": "heel-pain"}, "subs": {"heel-pain": {"runner": "when-running", "walker": "when-walking", "nurse": "when-on-shift"}}, "demographics": {}}))
        self.m = [mock.patch.object(W.S, "root", lambda: r), mock.patch.object(N, "BRANDS", r / "brands"), mock.patch.object(P, "ROOT", r), mock.patch.dict(W._ROWS, {}, clear=True)]
        for m in self.m:
            m.start()

    def tearDown(self):
        for m in self.m:
            m.stop()
        self.t.cleanup()

    def test_the_brands_own_people_file_names_its_profiles(self):
        self.assertIn("heel-pain_when-running", P._listing("acme"))

    def test_every_profile_has_every_part(self):
        p = P.load("acme", "heel-pain_when-running")
        want = {"card." + k for k in P.CARD} | {"slot." + k for k in P.SLOT_LISTS} | {"slot.doubts", "slot.awareness", "slot.stage"}
        self.assertEqual(want, set(p["parts"]))
        self.assertEqual("own", p["parts"]["slot.doubts"]["state"])

    def test_slots_without_a_card_is_a_fail_with_a_name_to_build(self):
        fails, _ = P.check("acme", "heel-pain_when-running")
        self.assertTrue(any("no profile card" in x for x in fails))

    def test_missing_slots_is_a_fail(self):
        (self.r / "runs/creative-strategist/acme/who/sore-foot/nurse.json").unlink()
        fails, _ = P.check("acme", "heel-pain_when-on-shift")
        self.assertTrue(any("no slots" in x for x in fails))

    def test_gate_shares_lines_with_each_sibling(self):
        g = P.gate("acme", "heel-pain_when-running")
        self.assertAlmostEqual(8 / 38, g["shared"]["heel-pain_when-walking"], 2)    # r30..r37 of the 38 lines its slots cite
        self.assertEqual(0, g["shared"]["heel-pain_when-on-shift"])

    def test_a_brand_sets_its_own_thresholds(self):
        self.assertEqual((P.MIN_OWN, P.SAME_PERSON), P.criteria("acme"))
        (self.r / "brands/acme/core-avatars/criteria.json").write_text(json.dumps({"min_own": 5, "same_person": 0.2}))
        self.assertEqual((5, 0.2), P.criteria("acme"))
        self.assertTrue(any("same person" in h for h in P.gate("acme", "heel-pain_when-running")["holds"]))

    def test_a_merged_profile_resolves_to_its_keeper_and_leaves_the_list(self):
        f = self.r / "brands/acme/core-avatars/people.json"
        d = json.loads(f.read_text())
        d["merges"] = {"heel-pain_when-walking": {"into": "heel-pain_when-running", "lens": "on foot all day", "why": "x", "decided": "2026-11-27"}}
        f.write_text(json.dumps(d))
        self.assertEqual(N.folders("acme", "heel-pain_when-walking"), N.folders("acme", "heel-pain_when-running"))
        self.assertNotIn("heel-pain_when-walking", P._listing("acme"))
        self.assertEqual(["on foot all day"], [x["lens"] for x in P.load("acme", "heel-pain_when-running")["lenses"]])

    def test_the_same_sub_in_another_demographic_is_not_a_sibling(self):
        f = self.r / "brands/acme/core-avatars/people.json"
        d = json.loads(f.read_text())
        d["demographics"] = {"walker": {"sub": "when-walking", "demographic": "female-45-54-black"}}
        f.write_text(json.dumps(d))
        self.assertNotIn("heel-pain_when-walking_female-45-54-black", P.siblings("acme", "heel-pain_when-walking"))

    def test_pick_gives_a_filed_checked_profile_the_product_fits_and_the_same_one_per_seed(self):
        with mock.patch.object(P, "_card", lambda b, a, s: (None, "filed")), \
                mock.patch.object(P, "check", lambda b, n, d="": ([], [])), \
                mock.patch.object(W, "fits", lambda b, prod, a, s: "ruled out" if s == "nurse" else None):
            got = {P.pick("acme", "sore-foot", "insole", "send-%d" % i)["sub"] for i in range(40)}
            self.assertEqual(got, {"runner", "walker"})                       # spread across, never the one the product does not fit
            self.assertEqual(P.pick("acme", "sore-foot", "insole", "s1"), P.pick("acme", "sore-foot", "insole", "s1"))
            self.assertTrue(P.pick("acme", "sore-foot", "", "s1")["id"].startswith("heel-pain_"))
        self.assertIsNone(P.pick("acme", "none"))
        self.assertIsNone(P.pick("acme", "sore-foot", "insole", "s1"))          # no filed card: the whole avatar, as before

    def test_init_lists_what_stands_between_each_profile_and_ads(self):
        rows = {r["id"]: r for r in P.init("acme")}
        self.assertIn("build its card (who.py build)", rows["heel-pain_when-running"]["todo"])

    def test_doors_finds_a_tool_with_the_old_flags(self):
        t = self.r / "components" / "x"
        t.mkdir(parents=True)
        (t / "a.py").write_text("ap.add_argument('--avatar')\n")
        (t / "b.py").write_text("import profile_arg\nap.add_argument('--avatar')\n")
        self.assertEqual(["components/x/a.py"], [x["file"] for x in P.doors(self.r)])


class NoBrandInTheEngine(unittest.TestCase):
    def test_no_real_brand_is_named_in_the_engine_or_its_standard(self):
        brands = [p.name for p in (P.ROOT / "brands").iterdir() if p.is_dir() and not p.name.startswith("_")] if (P.ROOT / "brands").is_dir() else []
        for f in (HERE.parent / "profiles.py", HERE.parent / "SPEC.md", HERE.parent / "CLAUDE.md", HERE.parent / "CREATE.md"):
            for b in brands:
                self.assertIsNone(re.search(r"\b%s\b" % re.escape(b), f.read_text(), re.I), "%s names the brand %s" % (f.name, b))


if __name__ == "__main__":
    unittest.main()
