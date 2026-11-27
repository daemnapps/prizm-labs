"""Every ad-variations prompt that writes words is handed who the ad is for, and a statics round keeps its aim. No model.

    python3 components/ad-variations/machine/test_who.py
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brandctx as BC          # noqa: E402
import format_swap as FS       # noqa: E402
import natural_statics as NS   # noqa: E402
import static_plan as SP       # noqa: E402

REAL = BC.BrandContext
LONG = "\n".join("- line %d of the card" % i for i in range(200))


def workspace(d):
    av = Path(d) / "brands" / "acme" / "core-avatars" / "a1"
    (av / "sub-avatars").mkdir(parents=True)
    (Path(d) / "components" / "brandpath").mkdir(parents=True)
    (av / "profile.md").write_text('# a1\n\nHe says: "I want the marks to be gone for good"\n')
    for n, want in (("sub-01-night-worker", "I want to look awake at dawn"), ("sub-02-day-worker", "I want to hide it at noon")):
        (av / "sub-avatars" / (n + ".md")).write_text('- **Core desire:** "%s"\n- **Pain:** it shows\n%s\nLAST LINE OF %s\n' % (want, LONG, n))


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name).resolve()
        workspace(self.root)
        p = mock.patch.dict(os.environ, AI_WORKSPACE=str(self.root))
        p.start()
        self.addCleanup(p.stop)


class Context(Base):
    def ctx(self, sub=None, what=None):
        bc = REAL(self.root, "acme", "a1")
        self.aim = bc.speak_to(sub, what=what)
        return bc

    def test_the_named_sub_is_whole_and_alone(self):
        got = self.ctx("night-worker", {"doubt": "worth-it"}).avatars()
        self.assertIn(BC.who().MARK, got)
        self.assertIn("I want to look awake at dawn", got)
        self.assertIn("LAST LINE OF sub-01-night-worker", got)
        self.assertNotIn("hide it at noon", got)
        self.assertEqual((self.aim["sub"], self.aim["doubt"]), ("night-worker", "worth-it"))

    def test_no_sub_keeps_the_roster_uncut(self):
        got = self.ctx().avatars()
        self.assertIn(BC.who().MARK, got)
        for n in ("sub-01-night-worker", "sub-02-day-worker"):
            self.assertIn("LAST LINE OF " + n, got)

    def test_the_parents_level_is_the_language_level(self):
        self.assertEqual(self.ctx("none", {"awareness": "problem-aware"}).awareness, "problem-aware")

    def test_the_audience_read_is_enough(self):
        sub, demo, what = BC.aim_of({"audience": {"_sub_avatar": "sub-01-night-worker"}})
        self.assertEqual((sub, demo, what), ("sub-01-night-worker", None, {}))

    def test_format_swap_carries_it(self):
        with mock.patch.object(FS.BC, "BrandContext", lambda repo, b, a: types.SimpleNamespace(
                rules=lambda: "rules", product_rel=lambda *x: "p.md", file=lambda *x: None, read_files=[])):
            t, _ = FS.brand_context("acme", "p", "a1", "night-worker")
        self.assertIn(BC.who().MARK, t)
        self.assertIn("I want to look awake at dawn", t)


class StaticPlan(Base):
    def plan(self, rec=None, run=None):
        runs = self.root / "runs"
        rd = runs / "image-teardown" / "acme" / "win"
        (rd / "out").mkdir(parents=True)
        (rd / "out" / "01-teardown.md").write_text("MARKET STATE: solution-aware")
        (rd / "out" / "02-replication-spec.md").write_text("zones")
        (rd / "run.json").write_text(json.dumps(run or {}))
        ask = self.root / "ask.json"
        ask.write_text(json.dumps(rec or {}))
        sent = []
        with mock.patch.object(SP, "RUNS", runs), mock.patch.object(SP, "offer_prices", lambda b: set()), \
                mock.patch.object(BC, "BrandContext", lambda repo, b: types.SimpleNamespace(rules=lambda: "rules")):
            doc = SP.plan("acme", "win", "lab", ask=str(ask) if rec else None, say=lambda *_: None,
                          ask_fn=lambda t: sent.append(t) or "```json\n{}\n```")
        return sent[0], doc

    def test_the_orders_person_reaches_the_prompt(self):
        sent, doc = self.plan({"avatar": "a1", "sub_avatar": "night-worker"})
        self.assertIn(BC.who().MARK, sent)
        self.assertIn("I want to look awake at dawn", sent)
        self.assertEqual((doc["aim"]["sub"], doc["aim"]["awareness"]), ("night-worker", "solution-aware"))

    def test_the_parent_runs_aim_reaches_the_prompt(self):
        sent, doc = self.plan(run={"aim": {"avatar": "a1", "sub": "day-worker", "doubt": "for-me"}})
        self.assertIn("I want to hide it at noon", sent)
        self.assertEqual(doc["aim"]["doubt"], "for-me")

    def test_no_person_named_leaves_the_prompt_alone(self):
        sent, doc = self.plan()
        self.assertNotIn(BC.who().MARK, sent)
        self.assertEqual(doc["aim"], {})


class Sprint(Base):
    def sp(self, aim=True, **ad):
        base = {"id": "a", "title": "T", "why": "w", "receipt": "r", "layout": "note", "lines": ["%d" % i for i in range(6)], "body": ["OFFER"]}
        base.update(ad)
        d = {"brand": "acme", "product": "p", "avatar": "a1", "label": "lab", "offer": "OFFER", "page": "pg", "ads": [base], "_dir": self.root}
        return dict(d, aim=True) if aim else d

    FULL = {"sub_avatar": "night-worker", "desire": "to look awake", "awareness": "problem-aware", "doubt": "for-me"}

    def test_a_new_round_names_the_person_and_the_message(self):
        self.assertEqual(NS.check(self.sp(**self.FULL)), [])
        for k in self.FULL:
            got = NS.check(self.sp(**{x: y for x, y in self.FULL.items() if x != k}))
            self.assertTrue(any(k in g for g in got), (k, got))
        self.assertTrue(any("no sub-avatar" in g for g in NS.check(self.sp(**dict(self.FULL, sub_avatar="nobody")))))
        self.assertEqual(NS.check(self.sp(**dict(self.FULL, sub_avatar="none"))), [])

    def test_an_older_round_is_not_asked_for_it(self):
        self.assertEqual(NS.check(self.sp(aim=False)), [])

    def test_drawn_words_are_never_read_as_a_person(self):
        self.assertEqual(NS.aim_of(self.sp(aim=False, sub="real comments from this week"), self.sp(sub="real comments from this week")["ads"][0])["sub"], None)
        self.assertEqual(NS.who_of(self.sp(), {"id": "a", "sub": "sub-02-day-worker"})[2], "day-worker")

    def test_who_prints_the_block(self):
        sp = self.sp(**self.FULL)
        t = NS.who_text(sp, sp["ads"][0])
        self.assertIn(BC.who().MARK, t)
        self.assertIn("I want to look awake at dawn", t)
        self.assertIn("`for-me`", t)

    def test_number_writes_the_aim(self):
        sp = self.sp(**self.FULL)
        seen = []
        with mock.patch.object(NS, "REPO", self.root), mock.patch.object(NS.subprocess, "run", side_effect=lambda c, **k: seen.append(c) or mock.Mock(
                stdout="brief-0001", stderr="", returncode=0)):
            NS.number(sp)
            run = json.loads((NS.run_dir(sp, sp["ads"][0]) / "run.json").read_text())
        self.assertEqual({k: run["aim"][k] for k in ("avatar", "sub", "desire", "awareness", "doubt")},
                         {"avatar": "a1", "sub": "night-worker", "desire": "to look awake", "awareness": "problem-aware", "doubt": "for-me"})
        self.assertIn("night-worker", (self.root / "runs/ad-variations/acme/lab-ad-a/deliverable/brief.md").read_text())

    def test_an_older_round_claims_nothing_its_ad_did_not_name(self):
        st = self.root / "runs/creative-strategist/acme/who/a1"
        st.mkdir(parents=True)
        (st / "avatar.json").write_text(json.dumps({"doubt_lead": "worth-it", "awareness_lead": "unaware"}))
        sp = self.sp(aim=False, awareness="problem-aware")
        got = NS.aim_of(sp, sp["ads"][0])
        self.assertEqual((got["awareness"], got["doubt"]), ("problem-aware", None))
        sp = self.sp(**dict(self.FULL, doubt=""))
        self.assertEqual(NS.aim_of(sp, sp["ads"][0])["doubt"], "worth-it")

    def test_start_opens_a_round_that_asks_for_it(self):
        with mock.patch.object(NS, "REPO", self.root):
            NS.start(types.SimpleNamespace(brand="acme", product="p", avatar="a1", label="new"))
        self.assertTrue(json.loads((self.root / "runs/ad-variations/acme/new/sprint.json").read_text())["aim"])


if __name__ == "__main__":
    unittest.main()
