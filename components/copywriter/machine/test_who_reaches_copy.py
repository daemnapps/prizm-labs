#!/usr/bin/env python3
"""Who the ad is for (creative-strategist who.py) is really in the prompt that is sent: the stage chain, the copy set,
the format filler and the Google ads. A made-up brand on disk, no model, no network.

    python3 machine/test_who_reaches_copy.py
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import copy_writer as C                  # noqa: E402
import copy_set as CS                    # noqa: E402
import context                           # noqa: E402
import paths as P                        # noqa: E402
sys.path.append(str(HERE.parents[1] / "creative-strategist" / "tests"))
import test_who as TW                    # noqa: E402  its made-up brand: acme · sore-foot · sub-01-runner
import who as W                          # noqa: E402

CARD = "my heel barks at mile two"       # words only the sub-avatar's card says
CORE = "walk without heel pain"          # the avatar's own desire


class Base(unittest.TestCase):
    def setUp(self):
        self.b = TW.Who("test_sub_rows_are_read")
        self.b.setUp()
        self.addCleanup(self.b.tearDown)
        self.root = self.b.r
        self.tmp = Path(tempfile.mkdtemp(prefix="who-copy-"))

    def put(self, obj, **kw):
        for k, v in kw.items():
            p = mock.patch.object(obj, k, v)
            p.start()
            self.addCleanup(p.stop)


class Chain(Base):
    def run_chain(self, *extra, run=None):
        prod = self.root / "brands" / "acme" / "products"
        prod.mkdir(exist_ok=True)
        (prod / "offer-bank.md").write_text("# Offers\n\n## core — One\n- Price: $49.00\n")
        (prod / "thing.md").write_text("# The thing\nIt does a job.\n")
        src = self.tmp / "teardown" / "stages" / "5-brief.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("A runner says his heel hurts.\n")
        if run:
            (src.parents[1] / "run.json").write_text(json.dumps(run))
        self.sent = {}

        def model(prompt, model, label=None):
            self.sent[label] = prompt
            return {"stage0": "LANE: ALREADY AN AD\nFORMAT: caption\nAVATAR: sore-foot\n",
                    "stage1": "AWARENESS\nEntry level: `solution-aware`\n",
                    "stage8": "**FORMAT: caption**\n\n**BODY A**\n\nWords.\n\n**HEADLINES**\n\n1. One\n",
                    "stage8b": "**FORMAT: caption**\n\n**BODY A**\n\nWords.\n\n**HEADLINES**\n\n1. One\n",
                    "stage8c": json.dumps({"primary": [{"n": 1, "pass": True}], "headlines": [{"n": 1, "pass": True}]}),
                    }.get(label, "ok")
        self.put(C, claude=model, creative_qc=lambda *a, **k: {}, _rebuild_board=lambda: None, WORKSPACE=C.WORKSPACE,
                 RERUN_FROM=None, DRY=None)
        self.put(context, WORKSPACE=context.WORKSPACE)
        self.put(P, RUNS=self.tmp / "runs", RESULTS=self.tmp / "results")
        import research
        self.put(research, text_for=lambda **k: "no research in a test")
        import language as L
        self.put(L, avatars=lambda *a, **k: [{"key": "sore-foot", "rows": 1, "funnels": {}, "subs": ["runner"]}],
                 for_stage=lambda *a, **k: "rows")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                code = C.main([str(src), "--brand", "acme", "--product", str(prod / "thing.md"), "--brand-root",
                               str(self.root), "--label", "t", "--no-gate", *extra])
            except SystemExit as e:
                code = e
        self.out = out.getvalue()
        return code, self.tmp / "runs" / "acme" / "t"

    def test_every_writing_stage_is_sent_it_and_no_reading_stage_is(self):
        code, d = self.run_chain("--avatar", "sore-foot", "--sub", "sub-01-runner", "--demographic", "m/25-34/black",
                                 "--doubt", "for-me", "--awareness", "problem-aware")
        self.assertEqual(code, 0, self.out)
        for k in ("stage3", "stage4", "stage5", "stage7", "stage8", "stage8b", "stage8c", "stage9"):
            for text in (self.sent[k], (d / f"{k}--sent.md").read_text()):
                self.assertTrue(text.startswith(W.MARK), k)
                for x in (CARD, CORE, "m/25-34/black", "problem-aware", "same skin or hair"):
                    self.assertIn(x, text, k)
        for k in ("stage0", "stage1", "stage2", "stage1b"):
            self.assertNotIn(W.MARK, self.sent[k], k)
        aim = json.loads((d / "run.json").read_text())["aim"]
        self.assertEqual((aim["avatar"], aim["sub"], aim["doubt"], aim["awareness"], aim["demographic"]),
                         ("sore-foot", "runner", "for-me", "problem-aware", "m/25-34/black"))
        self.assertNotIn("_who", json.loads((d / "run.json").read_text()))

    def test_the_sources_own_run_is_the_default(self):
        _, d = self.run_chain(run={"aim": {"avatar": "sore-foot", "sub": "runner", "demographic": "f/35-44/latina",
                                           "desire": "run again", "doubt": "worth-it"}})
        self.assertIn(CARD, self.sent["stage8"])
        for x in ("f/35-44/latina", "run again"):
            self.assertIn(x, self.sent["stage8"])
        aim = json.loads((d / "run.json").read_text())["aim"]
        self.assertEqual((aim["sub"], aim["desire"], aim["doubt"]), ("runner", "run again", "worth-it"))
        self.assertEqual(aim["awareness"], "solution-aware")          # what stage 1 read, when nothing was given

    def test_a_declared_audience_is_read_too(self):
        self.run_chain(run={"declared_audience": {"avatar": "sore-foot", "sub": "sub-01-runner"}})
        self.assertIn(CARD, self.sent["stage8"])

    def test_with_no_sub_it_speaks_to_the_whole_avatar(self):
        self.run_chain("--avatar", "sore-foot")
        self.assertIn(W.MARK, self.sent["stage8"])
        self.assertNotIn(CARD, self.sent["stage8"])

    def test_a_named_sub_that_is_not_there_stops_before_a_call(self):
        code, _ = self.run_chain("--avatar", "sore-foot", "--sub", "nobody")
        self.assertIsInstance(code, SystemExit)
        self.assertIn("nobody", str(code.code))
        self.assertEqual(self.sent, {})

    def test_a_sub_only_the_source_names_never_stops_the_run(self):
        code, _ = self.run_chain(run={"aim": {"avatar": "sore-foot", "sub": "gone"}})
        self.assertEqual(code, 0, self.out)
        self.assertIn(W.MARK, self.sent["stage8"])
        self.assertIn("gone", self.out)

    def test_a_broken_reader_never_stops_the_run(self):
        with mock.patch.object(W, "block", side_effect=ValueError("no")):
            code, _ = self.run_chain("--avatar", "sore-foot")
        self.assertEqual(code, 0, self.out)
        self.assertNotIn(W.MARK, self.sent["stage8"])


class Aim(Base):
    def test_another_avatars_run_lends_nothing(self):
        self.assertEqual(CS.settle_aim("acme", "other-foot", {}, {"avatar": "sore-foot", "sub": "runner", "doubt": "for-me"}),
                         (None, None, {}))

    def test_another_subs_desire_is_never_lent(self):
        got = CS.settle_aim("acme", "sore-foot", {"sub": "walker"}, {"avatar": "sore-foot", "sub": "runner", "desire": "run"})
        self.assertEqual(got, ("walker", None, {}))


class CopySet(Base):
    def test_the_set_is_sent_it_and_keeps_the_aim(self):
        self.put(CS, offer_text=lambda *a: ("offers", "offers"), product_text=lambda *a: "product", angle_text=lambda *a: "angle",
                 guarantee_text=lambda *a: "g", language_rows=lambda *a, **k: [], spice_rows=lambda *a: "", is_promo=lambda *a, **k: False,
                 brand_core=lambda *a: {"position": "p", "story": "s"}, load=lambda *a, **k: None, check=lambda *a, **k: [])
        kept = {}
        self.put(CS, save=lambda s: kept.update(s) or CS.WS / "x", claude=lambda t, m: self.fail("a model call"))
        answer = self.tmp / "a.json"
        answer.write_text('{"primary": [], "headlines": []}')
        out = self.tmp / "sent.md"
        with contextlib.redirect_stdout(io.StringIO()):
            CS.write("acme", "thing", "an-angle", avatar="sore-foot", sub="runner", demographic="m/25-34/black", doubt="for-me",
                     awareness="problem-aware", answer=answer, prompt_out=out)
        text = out.read_text()
        self.assertTrue(text.startswith(W.MARK))
        for x in (CARD, CORE, "m/25-34/black", "same skin or hair"):
            self.assertIn(x, text)
        self.assertEqual((kept["aim"]["sub"], kept["aim"]["doubt"]), ("runner", "for-me"))


class Formats(Base):
    def test_the_format_filler_is_sent_it(self):
        import format_copy as FC
        e = {"id": "p1", "name": "n", "numbers": {"spend": 1, "purchases": 1, "cpa": 1}, "awareness": None, "structure": "s", "format": "[X]"}
        self.put(FC.RF, load=lambda *a: [e])
        self.put(FC, shortlists=lambda *a, **k: {s: [e] for s in FC.RF.SLOTS})
        self.put(CS, offer_text=lambda *a: ("o", "o"), product_text=lambda *a: "p", guarantee_text=lambda *a: "g",
                 language_rows=lambda *a, **k: [], spice_rows=lambda *a: "", brand_core=lambda *a: {"position": "p", "story": "s"})
        src = self.tmp / "s.md"
        src.write_text("the ad")
        got = FC.write("acme", "brief-0001", "thing", src, avatar="sore-foot", label="t", dry_run=True, say=lambda *_: None,
                       aim={"sub": "runner", "awareness": "unaware"}, ws=CS.WS)
        self.assertTrue(got["sent"].startswith(W.MARK))
        self.assertIn(CARD, got["sent"])
        self.assertEqual((got["aim"]["sub"], got["aim"]["awareness"]), ("runner", "unaware"))

    def test_a_brief_hands_its_runs_aim_on(self):
        import brief_words as BW
        run = self.tmp / "r"
        run.mkdir()
        (run / "run.json").write_text(json.dumps({"aim": {"avatar": "sore-foot", "sub": "runner", "doubt": "for-me"}}))
        self.assertEqual(BW.aim_for({"run": str(run)}, None)["sub"], "runner")
        with mock.patch.object(BW, "product_path", lambda *a: "p.md"):
            cmd = BW.command("acme", "brief-0001", "thing", "/x.md", avatar="sore-foot", aim={"sub": "runner", "doubt": "for-me"})
        self.assertEqual((cmd[cmd.index("--sub") + 1], cmd[cmd.index("--doubt") + 1]), ("runner", "for-me"))


class Google(Base):
    def test_a_group_that_names_an_avatar_is_sent_it_and_one_that_does_not_is_not(self):
        import google_copy as GC
        self.put(GC, RUNS=self.tmp / "runs")
        f = self.tmp / "runs" / "copywriter" / "acme" / "google-formats" / "formats.json"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"formats": []}))
        groups = self.tmp / "g.json"
        g = {"name": "heel pain", "final_url": "https://x.com", "keywords": []}
        prod = self.tmp / "p.md"
        prod.write_text("# P")
        for extra, want in (({"avatar": "sore-foot", "sub": "runner"}, True), ({}, False)):
            groups.write_text(json.dumps({"groups": [dict(g, **extra)]}))
            seen = []
            GC.write("acme", groups, prod, "t", say=lambda *_: None, fetch=lambda u: "<h1>x</h1>",
                     ask_fn=lambda t: seen.append(t) or "{}")
            self.assertEqual(W.MARK in seen[0], want)
            self.assertEqual(CARD in seen[0], want)
            rec = json.loads((self.tmp / "runs/copywriter/acme/t/heel-pain/ad.json").read_text())
            self.assertEqual((rec["aim"] or {}).get("sub"), "runner" if want else None)


if __name__ == "__main__":
    unittest.main()
