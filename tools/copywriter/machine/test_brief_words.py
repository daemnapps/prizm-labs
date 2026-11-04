"""brief_words.py — every lane's brief routed through the copywriter's own chain
for its ad words. No model is called (the copywriter's command is built and
read, never run), nothing written outside a temp folder.

    python3 tools/copywriter/machine/test_brief_words.py
"""
import os, shutil, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brief_words as BW  # noqa: E402


class Names(unittest.TestCase):
    def test_label_carries_the_brief_number(self):
        self.assertEqual(BW.label_for("crush", "brief-0001"), "crush-brief-0001-words")
        self.assertEqual(BW.label_for("brilliance-body-scrub", "p137"), "brilliance-body-scrub-brief-0137-words")

    def test_product_file_or_folder(self):
        self.assertEqual(BW.product_path("brand-a", "crush"), "brands/brand-a/products/crush.md")
        self.assertTrue(BW.product_path("brand-b", "brilliance-body-scrub").startswith(
            "brands/brand-b/products/brilliance-body-scrub"))
        self.assertIsNone(BW.product_path("brand-a", "no-such-product"))


class Source(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.td, ignore_errors=True))

    def test_a_delivered_transcript_comes_first_with_the_brief_on_top(self):
        u = self.td / "acme/2026-10-02-delivered/acme_nova_brief-0004_batch-2026-10-01-a"
        u.mkdir(parents=True)
        (u / "transcript.md").write_text("| T1 | 0:01 | Speaker 1 | en | Hello there. |\n")
        head = {"brief": "brief-0004", "product": "nova", "avatar": "fed-up-king", "angle": "x", "title": "The Pull"}
        with mock.patch.object(BW, "AUDIO_RUNS", self.td), \
                mock.patch.object(BW, "brief_facts", lambda *a: (head, None)):
            src, what = BW.source_for("acme", "brief-0004", "nova")
        self.assertEqual(src.name, "copy-source.md")
        text = src.read_text()
        self.assertTrue(text.startswith("# The Pull — ACME brief-0004"))
        self.assertIn("- avatar: fed-up-king", text)
        self.assertIn("Hello there.", text)
        self.assertIn("transcript", what)

    def test_else_the_briefs_writing_run(self):
        run = self.td / "runs/video-writing/acme/some-run"
        (run / "deliverable").mkdir(parents=True)
        (run / "deliverable/5-brief.md").write_text("# brief")
        with mock.patch.object(BW, "WS", self.td), mock.patch.object(BW, "AUDIO_RUNS", self.td / "none"), \
                mock.patch.object(BW, "brief_facts", lambda *a: (None, {"run": "some-run", "product": "nova"})):
            src, what = BW.source_for("acme", "brief-0004")
        self.assertEqual(src, run / "deliverable/5-brief.md")

    def test_a_production_runs_own_brief(self):
        run = self.td / "runs/video-production/acme/x"
        run.mkdir(parents=True)
        (run / "x-ai-brief.md").write_text("# ai brief")
        (run / "run.json").write_text('{"source_brief": "x-ai-brief.md"}')
        with mock.patch.object(BW, "WS", self.td):
            self.assertEqual(BW.run_source("runs/video-production/acme/x", "acme"), run / "x-ai-brief.md")

    def test_no_source_runs_nothing(self):
        with mock.patch.object(BW, "AUDIO_RUNS", self.td / "none"), \
                mock.patch.object(BW, "brief_facts", lambda *a: ({"product": "nova"}, None)), \
                mock.patch.object(BW.subprocess, "run", side_effect=AssertionError("no copy run without a source")):
            res = BW.write("acme", "brief-0004")
        self.assertIsNone(res["rc"])
        self.assertIn("no source", res["source"])


class Command(unittest.TestCase):
    def test_the_copywriters_own_chain_unchanged(self):
        cmd = BW.command("brand-a", "brief-0001", "crush", "/x/source.md", avatar="fed-up-king")
        self.assertTrue(cmd[1].endswith("tools/copywriter/machine/copy_writer.py"))
        self.assertEqual(cmd[cmd.index("--product") + 1], "brands/brand-a/products/crush.md")
        self.assertEqual(cmd[cmd.index("--write-as") + 1], "short-form,caption")
        self.assertEqual(cmd[cmd.index("--label") + 1], "crush-brief-0001-words")
        self.assertEqual(cmd[cmd.index("--avatar") + 1], "fed-up-king")
        self.assertNotIn("--dry-run", cmd)
        self.assertIn("--dry-run", BW.command("brand-a", "brief-0001", "crush", "/x", dry_run=True))
        self.assertNotIn("--awareness", cmd)
        self.assertNotIn("--promo", cmd)
        c2 = BW.command("brand-a", "brief-0001", "crush", "/x", awareness="unaware", promo=True)
        self.assertEqual(c2[c2.index("--awareness") + 1], "unaware")
        self.assertIn("--promo", c2)

    def test_the_awareness_its_run_recorded_flows_through(self):
        td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(td, ignore_errors=True))
        (td / "brief.md").write_text('{"awareness": "unaware"}')
        self.assertEqual(BW.awareness_for("brand-a", "brief-0001", header={}, reg={"run": str(td)}), "unaware")
        self.assertEqual(BW.awareness_for("brand-a", "brief-0001", header={"awareness": "problem-aware"},
                                          reg={"run": str(td)}), "problem-aware")

    def test_off_switch_and_already_written(self):
        lines = []
        with mock.patch.dict(os.environ, {"NO_AD_WORDS": "1"}), \
                mock.patch.object(BW, "write", side_effect=AssertionError("off means off")):
            self.assertIsNone(BW.auto("brand-a", "brief-0001", "crush", say=lines.append))
        self.assertIn("off", lines[-1])
        td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(td, ignore_errors=True))
        (td / "runs/copywriter/brand-a/crush-brief-0001-words").mkdir(parents=True)
        (td / "runs/copywriter/brand-a/crush-brief-0001-words/stage8--render.md").write_text("x")
        with mock.patch.dict(os.environ, {"NO_AD_WORDS": ""}), mock.patch.object(BW, "WS", td), \
                mock.patch.object(BW, "brief_facts", return_value=({"product": "crush"}, None)), \
                mock.patch.object(BW, "write", side_effect=AssertionError("never twice")):
            self.assertIsNone(BW.auto("brand-a", "brief-0001", "crush", say=lines.append))
        self.assertIn("already written", lines[-1])

    def test_an_angle_with_a_copy_set_writes_nothing_new(self):
        import copy_set as CS
        lines = []
        head = ({"product": "crush", "angle": "razor-not-problem", "avatar": "fed-up-king", "problem": "razor-bumps"}, None)
        have = {"id": "copy_brand_a_crush_razor-not-problem", "version": 1, "status": "approved"}
        with mock.patch.dict(os.environ, {"NO_AD_WORDS": ""}), mock.patch.object(BW, "brief_facts", return_value=head), \
                mock.patch.object(CS, "load", return_value=have), \
                mock.patch.object(CS, "write", side_effect=AssertionError("same angle, no new copy")), \
                mock.patch.object(BW, "write", side_effect=AssertionError("no per-ad chain run")):
            self.assertIsNone(BW.auto("brand-a", "brief-0009", "crush", say=lines.append))
        self.assertIn("nothing new written", lines[-1])
        made = {"id": "copy_brand_a_crush_new-angle"}
        with mock.patch.dict(os.environ, {"NO_AD_WORDS": ""}), \
                mock.patch.object(BW, "brief_facts", return_value=({**head[0], "angle": "new-angle"}, None)), \
                mock.patch.object(CS, "load", return_value=None), \
                mock.patch.object(CS, "write", return_value=made) as w, \
                mock.patch.object(BW, "write", side_effect=AssertionError("no per-ad chain run")):
            self.assertEqual(BW.auto("brand-a", "brief-0009", "crush", say=lines.append), made)
        self.assertEqual(w.call_args.args, ("brand-a", "crush", "new-angle"))
        self.assertIn("NEW ANGLE", lines[-1])

    def test_the_video_hook_reads_the_final_brief(self):
        td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(td, ignore_errors=True))
        run = td / "kzn03-x"
        (run / "deliverable").mkdir(parents=True)
        (run / "deliverable/5-brief.md").write_text("# brief")
        seen = {}
        def fake(cmd, **kw):
            seen["cmd"] = cmd
            return mock.Mock(returncode=0)
        with mock.patch.dict(os.environ, {"NO_AD_WORDS": ""}), mock.patch.object(BW.subprocess, "run", fake), \
                mock.patch.object(BW, "WS", BW.WS):
            rc = BW.for_writing_run(run, "brand-b", "brilliance-body-scrub", say=lambda m: None)
        self.assertEqual(rc, 0)
        self.assertEqual(seen["cmd"][2], str(run / "deliverable/5-brief.md"))
        self.assertEqual(seen["cmd"][seen["cmd"].index("--label") + 1], "kzn03-x-words")
        self.assertIsNone(BW.for_writing_run(td / "no-brief", "brand-b", "brilliance-body-scrub"))


if __name__ == "__main__":
    unittest.main()
