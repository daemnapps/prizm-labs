"""Who the ad is for reaches every writing prompt as sent, and no teardown prompt (2026-11-25). No model is called."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
M = HERE.parent / "machine"
sys.path.insert(0, str(M))
sys.path.insert(0, str(HERE.parents[1] / "video-teardown" / "machine"))

import writing_v2 as W  # noqa: E402
import scratch as X  # noqa: E402

CARD = """# Porch painter
- **Id / narrowed by:** porch-painter, paints the same porch every spring
- **Core desire:** "I want to paint it once and leave it alone"
- **Pain:** scraping the north rail on his knees every April
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name).resolve()
        (self.ws / "components").mkdir()
        av = self.ws / "brands" / "acme" / "core-avatars" / "owner"
        (av / "sub-avatars").mkdir(parents=True)
        (av / "profile.md").write_text("# Owner\n- **Core desire:** a house that stays done\n")
        (av / "sub-avatars" / "sub-01-porch-painter.md").write_text(CARD)
        self.run = self.ws / "runs" / "video-teardown" / "_work" / "piece"
        (self.run / "stages").mkdir(parents=True)
        (self.run / "prompts").mkdir()
        self.env = mock.patch.dict(os.environ, {"AI_WORKSPACE": str(self.ws)})
        self.env.start()
        W._HAND[0] = None
        W.who_module()._ROWS.clear()

    def tearDown(self):
        W._DRY[0] = False
        W._CURRENT.clear()
        W.who_module()._ROWS.clear()
        self.env.stop()
        self.tmp.cleanup()

    def state(self, **kw):
        st = {"brand": "acme", "stages": {}, "audience": {"_avatar": "owner", "_sub_avatar": "sub-01-porch-painter"},
              "market_state": {"lead_desire": "paint it ONE time", "awareness": "solution-aware", "sophistication": "stage three",
                               "sophistication_leads_with": "a new mechanism"}}
        st.update(kw)
        (self.run / "run.json").write_text(json.dumps(st))
        return st

    def sent(self, name, key="stage3"):
        W._DRY[0] = True
        W._CURRENT.clear()
        W._CURRENT["key"] = key
        with self.assertRaises(W.DryRunStop):
            W.claude_v2("THE PASS'S OWN PROMPT", self.run / "stages" / name)
        return (self.run / "prompts" / name).read_text()


class Sent(Base):
    def test_every_writing_pass_is_sent_the_person_and_the_message(self):
        self.state()
        for key, name in (("stage3", "3-injection.md"), ("stage4i", "4i-controlling-idea.md"), ("stage4v2a", "4ab-reading-hooks.md"),
                          ("stage4v2b", "4cde-placement-expansion-close.md"), ("stage4v2b-patch", "4cde-patch-1.md"),
                          ("stage4e", "4f-audit.md"), ("stage4g", "4g-spice.md"), ("stage5", "5-brief.md")):
            p = self.sent(name, key)
            for want in (W.who_module().MARK, "scraping the north rail on his knees", "paint it ONE time", "solution-aware",
                         "stage three", "a new mechanism", "THE PASS'S OWN PROMPT"):
                self.assertIn(want, p, name)

    def test_a_teardown_pass_is_not(self):
        self.state()
        for name in ("0-triage.md", "1-teardown.md", "1b-audience.md", "1c-doctrine.md", "1k-culture.md", "2-spec.md"):
            self.assertNotIn(W.who_module().MARK, self.sent(name, "stage5"), name)

    def test_no_avatar_yet_is_no_block(self):
        st = self.state(audience={})
        self.assertEqual(W.who_block(self.run, st, "3-injection.md"), "")
        self.assertIsNone(W.who_stamp(self.run, st))

    def test_the_asks_and_the_owners_words_come_above_it(self):
        self.state(owner_script={"file": "owner-script.md", "by": "owner", "at": "2026-11-25"})
        (self.run / "owner-script.md").write_text("### LINES\n| S1 | him | Paint it once. |\n")
        p = self.sent("3-injection.md")
        self.assertLess(p.index("OWNER'S LOCKED SCRIPT"), p.index(W.who_module().MARK))

    def test_the_trims_cut_nothing_of_it(self):
        st = self.state()
        b = W.who_block(self.run, st, "3-injection.md")
        for key, name in (("stage4g", "4g-spice.md"), ("stage5", "5-brief.md")):
            self.assertIn(b, self.sent(name, key))

    def test_the_angle_4i_chose_is_the_claim_after_4i_only(self):
        st = self.state()
        (self.run / "stages" / "4i-controlling-idea.md").write_text("ANGLE: one-coat - One coat\n")
        self.assertIn("The claim:** one-coat", W.who_block(self.run, st, "4ab-reading-hooks.md"))
        self.assertNotIn("one-coat", W.who_block(self.run, st, "4i-controlling-idea.md"))
        self.assertEqual(W.who_stamp(self.run, st)["claim"], "one-coat - One coat")

    def test_the_declared_person_wins_and_a_demographic_travels(self):
        st = self.state(declared_audience={"avatar": "owner", "sub": "porch-painter", "demographic": "m/55+"},
                        audience={"_avatar": "someone"}, doubt="for-me")
        self.assertEqual(W.who_args(self.run, st)[:4], ("acme", "owner", "porch-painter", "m/55+"))
        b = W.who_block(self.run, st, "5-brief.md")
        self.assertIn("m/55+", b)
        self.assertIn("`for-me`", b)
        self.assertEqual(W.who_stamp(self.run, st)["demographic"], "m/55+")

    def test_a_named_sub_that_does_not_exist_stops_by_name(self):
        st = self.state(declared_audience={"avatar": "owner", "sub": "ghost"})
        for f in (lambda: W.who_block(self.run, st, "3-injection.md"), lambda: W.who_stamp(self.run, st)):
            with self.assertRaises(SystemExit) as e:
                f()
            self.assertIn("no sub-avatar ghost", str(e.exception))

    def test_anything_else_going_wrong_costs_the_run_nothing(self):
        st = self.state()
        with mock.patch.object(W.who_module(), "block", side_effect=ValueError("broken file")):
            self.assertEqual(W.who_block(self.run, st, "3-injection.md"), "")
        self.assertEqual(W.who_block(self.run, self.state(audience={"_avatar": "nobody"}), "3-injection.md"), "")

    def test_loading_it_puts_nothing_ahead_of_this_machine(self):
        home = HERE.parents[1] / "creative-strategist" / "machine"
        before = list(sys.path)
        with mock.patch.object(W, "_WHO", []), mock.patch.object(sys, "path", list(before)):
            W.who_module()
            self.assertEqual(sys.path[:len(before)], before)
            self.assertIn(str(home), sys.path)


class Scratch(Base):
    def args(self, **kw):
        a = argparse.Namespace(label="s1", brand="acme", product="paint", avatar="owner", awareness="problem-aware", arc=None, format=None,
                               style=None, story=None, preset=None, seconds=None, combo=None, sub="sub-01-porch-painter", demographic="m/55+")
        for k, v in kw.items():
            setattr(a, k, v)
        return a

    def build(self, a):
        import chain as C
        root = self.ws / "runs" / "video-teardown" / "_work"
        with mock.patch.object(C, "runs_root", lambda create=False: root), mock.patch.object(X, "records", lambda a: {}):
            return X.build(a)

    def test_the_sub_and_the_demographic_are_kept_and_reach_the_prompt(self):
        d = self.build(self.args())
        st = json.loads((d / "run.json").read_text())
        self.assertEqual(st["declared_audience"], {"avatar": "owner", "sub": "porch-painter", "demographic": "m/55+"})
        self.assertEqual(st["audience"]["_sub_avatar"], "porch-painter")
        b = W.who_block(d, st, "3-injection.md")
        for want in ("scraping the north rail on his knees", "m/55+", "problem-aware"):
            self.assertIn(want, b)

    def test_no_sub_is_as_before_and_a_wrong_one_makes_no_run(self):
        st = json.loads((self.build(self.args(sub=None, demographic=None)) / "run.json").read_text())
        self.assertEqual(st["declared_audience"], {"avatar": "owner", "sub": None})
        with self.assertRaises(SystemExit):
            self.build(self.args(label="s2", sub="ghost"))
        self.assertFalse((self.run.parent / "s2").exists())

    def test_the_door_takes_them(self):
        out = subprocess.run([sys.executable, str(M / "scratch.py"), "--help"], capture_output=True, text=True).stdout
        for want in ("--sub", "--demographic"):
            self.assertIn(want, out)


class RunWriting(Base):
    def test_the_aim_is_kept_on_the_run_before_any_pass(self):
        import run as R
        st = self.state(writing_lane={"lane": "swipe"}, label="piece", slug="piece")
        for n, v in (("apply_call", lambda d, s: s), ("format_approved", lambda s: True), ("winner_match_step", lambda d, s: (True, "")),
                     ("keep_controls_preset", lambda *a: None), ("declared_layers", lambda s: ""), ("run_inputs", lambda s: {}),
                     ("plan", lambda *a: [])):
            p = mock.patch.object(W, n, v)
            p.start()
            self.addCleanup(p.stop)
        real = R.claude
        self.addCleanup(setattr, R, "claude", real)
        with mock.patch.object(R, "say", lambda *a: None):
            W.run_writing(self.run, st, {})
        aim = json.loads((self.run / "run.json").read_text())["aim"]
        self.assertEqual((aim["avatar"], aim["sub"], aim["desire"], aim["awareness"]), ("owner", "porch-painter", "paint it ONE time", "solution-aware"))


class OldLine(Base):
    """A route that still writes on v1 (creator, founder) is handed the same block by the teardown's own engine."""

    def stage(self, key, name, st, extra=None):
        import run as R
        tpl = self.ws / "probe-v1.md"
        tpl.write_text("THE STAGE'S OWN PROMPT")
        stage = dict(key=key, id=key[5:], file_id=key[5:], name=name, prompt=str(tpl), version=1, engine="claude", vars={}, role="stage", per_run=[])
        seen = {}

        def fake(prompt, out, model=None):
            seen["prompt"] = prompt
            out.write_text("AVATAR: owner\nSUB-AVATAR: sub-01-porch-painter\nAWARENESS: solution-aware\n")
            return "fake"
        with mock.patch.object(R, "claude", fake), mock.patch.object(R, "creative_qc"), mock.patch.object(R, "record_time"), \
                mock.patch.object(R, "TMP", self.ws / "tmp"), mock.patch.object(R, "say", lambda *a: None), \
                mock.patch.object(R.C, "chain_version", return_value="v1"):
            ok = R.run_stage(self.run, st, stage, dict({"video_count": "1"}, **(extra or {})))
        return ok, seen.get("prompt", ""), st

    def test_a_v1_writing_stage_gets_it_and_a_teardown_stage_does_not(self):
        st = self.state(label="piece", slug="piece", production_route="creator")
        _, p, st = self.stage("stage4zz", "Probe", st)
        self.assertTrue(p.startswith(W.who_module().MARK))
        self.assertIn("scraping the north rail on his knees", p)
        self.assertEqual(st["aim"]["sub"], "porch-painter")
        self.assertNotIn(W.who_module().MARK, self.stage("stage1c", "Doctrine", self.state(label="piece", slug="piece"))[1])

    def test_a_missing_sub_is_the_stages_error_in_who_s_words(self):
        ok, p, _ = self.stage("stage4zz", "Probe", self.state(label="piece", slug="piece", audience={"_avatar": "owner", "_sub_avatar": "ghost"}))
        self.assertFalse(ok)
        self.assertEqual(p, "")
        self.assertIn("no sub-avatar ghost", json.loads((self.run / "run.json").read_text())["stages"]["stage4zz"]["error"])

    def test_the_declared_demographic_is_kept_by_the_audience_stage(self):
        _, _, st = self.stage("stage1b", "Audience", self.state(label="piece", slug="piece", audience={}),
                              {"declared_avatar": "owner", "declared_sub": "porch-painter", "declared_demographic": "m/55+"})
        self.assertEqual(st["declared_audience"], {"avatar": "owner", "sub": "porch-painter", "demographic": "m/55+"})

    def test_learnings_fall_back_to_the_avatars(self):
        import run as R
        fake = self.ws / "components" / "video-teardown" / "machine" / "run.py"
        rec = self.ws / "components" / "marketing-chain-checks" / "records" / "learnings"
        rec.mkdir(parents=True)
        (rec / "acme--owner.md").write_text("THE AVATAR'S LEARNINGS")
        with mock.patch.object(R, "__file__", str(fake)), mock.patch.object(R, "_writing_line", lambda: W):
            self.assertIn("THE AVATAR'S LEARNINGS", self.stage("stage4zz", "Probe", self.state(label="piece", slug="piece"))[1])
            (rec / "acme--sub-01-porch-painter.md").write_text("THE SUB'S LEARNINGS")     # the sub named by its id, the file by its card
            p = self.stage("stage4zz", "Probe", self.state(label="piece", slug="piece", audience={"_avatar": "owner", "_sub_avatar": "porch-painter"}))[1]
        self.assertIn("THE SUB'S LEARNINGS", p)
        self.assertNotIn("THE AVATAR'S LEARNINGS", p)


if __name__ == "__main__":
    unittest.main()
