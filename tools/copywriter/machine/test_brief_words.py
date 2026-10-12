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


def _brand_tree(case):
    """A temp workspace with the two product files these tests name (the public repo ships no brand)."""
    td = Path(tempfile.mkdtemp())
    case.addCleanup(lambda: shutil.rmtree(td, ignore_errors=True))
    (td / "brands/brand-b/products").mkdir(parents=True)
    (td / "brands/brand-b/products/gadget.md").write_text("# gadget")
    (td / "brands/brand-a/products/body-scrub").mkdir(parents=True)
    (td / "brands/brand-a/products/body-scrub/product.md").write_text("# body scrub")
    p = mock.patch.object(BW, "WS", td)
    p.start()
    case.addCleanup(p.stop)


class Names(unittest.TestCase):
    def test_label_carries_the_brief_number(self):
        self.assertEqual(BW.label_for("gadget", "brief-0001"), "gadget-brief-0001-words")
        self.assertEqual(BW.label_for("body-scrub", "p137"), "body-scrub-brief-0137-words")

    def test_product_file_or_folder(self):
        _brand_tree(self)
        self.assertEqual(BW.product_path("brand-b", "gadget"), "brands/brand-b/products/gadget.md")
        self.assertTrue(BW.product_path("brand-a", "body-scrub").startswith(
            "brands/brand-a/products/body-scrub"))
        self.assertIsNone(BW.product_path("brand-b", "no-such-product"))


class Source(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.td, ignore_errors=True))

    def test_a_delivered_transcript_comes_first_with_the_brief_on_top(self):
        u = self.td / "acme/2026-10-02-delivered/acme_widget_brief-0004_batch-2026-10-01-a"
        u.mkdir(parents=True)
        (u / "transcript.md").write_text("| T1 | 0:01 | Speaker 1 | en | Hello there. |\n")
        head = {"brief": "brief-0004", "product": "widget", "avatar": "avatar-one", "angle": "x", "title": "The Pull"}
        with mock.patch.object(BW, "AUDIO_RUNS", self.td), \
                mock.patch.object(BW, "brief_facts", lambda *a: (head, None)):
            src, what = BW.source_for("acme", "brief-0004", "widget")
        self.assertEqual(src.name, "copy-source.md")
        text = src.read_text()
        self.assertTrue(text.startswith("# The Pull — ACME brief-0004"))
        self.assertIn("- avatar: avatar-one", text)
        self.assertIn("Hello there.", text)
        self.assertIn("transcript", what)

    def test_else_the_briefs_writing_run(self):
        run = self.td / "runs/video-writing/acme/some-run"
        (run / "deliverable").mkdir(parents=True)
        (run / "deliverable/5-brief.md").write_text("# brief")
        with mock.patch.object(BW, "WS", self.td), mock.patch.object(BW, "AUDIO_RUNS", self.td / "none"), \
                mock.patch.object(BW, "brief_facts", lambda *a: (None, {"run": "some-run", "product": "widget"})):
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
                mock.patch.object(BW, "brief_facts", lambda *a: ({"product": "widget"}, None)), \
                mock.patch.object(BW.subprocess, "run", side_effect=AssertionError("no copy run without a source")):
            res = BW.write("acme", "brief-0004")
        self.assertIsNone(res["rc"])
        self.assertIn("no source", res["source"])


class Command(unittest.TestCase):
    def test_the_copywriters_own_chain_unchanged(self):
        _brand_tree(self)
        cmd = BW.command("brand-b", "brief-0001", "gadget", "/x/source.md", avatar="avatar-one")
        self.assertTrue(cmd[1].endswith("tools/copywriter/machine/copy.py"))
        self.assertEqual(cmd[cmd.index("--product") + 1], "brands/brand-b/products/gadget.md")
        self.assertEqual(cmd[cmd.index("--write-as") + 1], "short-form,caption")
        self.assertEqual(cmd[cmd.index("--label") + 1], "gadget-brief-0001-words")
        self.assertEqual(cmd[cmd.index("--avatar") + 1], "avatar-one")
        self.assertNotIn("--dry-run", cmd)
        self.assertIn("--dry-run", BW.command("brand-b", "brief-0001", "gadget", "/x", dry_run=True))

    def test_off_switch_and_already_written(self):
        lines = []
        with mock.patch.dict(os.environ, {"NO_AD_WORDS": "1"}), \
                mock.patch.object(BW, "write", side_effect=AssertionError("off means off")):
            self.assertIsNone(BW.auto("brand-b", "brief-0001", "gadget", say=lines.append))
        self.assertIn("off", lines[-1])
        td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(td, ignore_errors=True))
        (td / "runs/copywriter/brand-b/gadget-brief-0001-words").mkdir(parents=True)
        (td / "runs/copywriter/brand-b/gadget-brief-0001-words/stage8--render.md").write_text("x")
        with mock.patch.dict(os.environ, {"NO_AD_WORDS": ""}), mock.patch.object(BW, "WS", td), \
                mock.patch.object(BW, "brief_facts", return_value=({"product": "gadget"}, None)), \
                mock.patch.object(BW, "write", side_effect=AssertionError("never twice")):
            self.assertIsNone(BW.auto("brand-b", "brief-0001", "gadget", say=lines.append))
        self.assertIn("already written", lines[-1])

    def test_the_video_hook_reads_the_final_brief(self):
        _brand_tree(self)
        td = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(td, ignore_errors=True))
        run = td / "run03-x"
        (run / "deliverable").mkdir(parents=True)
        (run / "deliverable/5-brief.md").write_text("# brief")
        seen = {}
        def fake(cmd, **kw):
            seen["cmd"] = cmd
            return mock.Mock(returncode=0)
        with mock.patch.dict(os.environ, {"NO_AD_WORDS": ""}), mock.patch.object(BW.subprocess, "run", fake), \
                mock.patch.object(BW, "WS", BW.WS):
            rc = BW.for_writing_run(run, "brand-a", "body-scrub", say=lambda m: None)
        self.assertEqual(rc, 0)
        self.assertEqual(seen["cmd"][2], str(run / "deliverable/5-brief.md"))
        self.assertEqual(seen["cmd"][seen["cmd"].index("--label") + 1], "run03-x-words")
        self.assertIsNone(BW.for_writing_run(td / "no-brief", "brand-a", "body-scrub"))


if __name__ == "__main__":
    unittest.main()
