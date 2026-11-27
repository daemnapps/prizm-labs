"""Behavior checks for source-stage design handoffs; no network or generation."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
sys.path.append(str(HERE))
from image_edit import assignment as A
from image_edit.engine import BadRequest

class Assignment(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / "runs/source").mkdir(parents=True)
        (self.repo / "runs/source/swipe.jpg").write_bytes(b"swipe bytes")
        self.req = {"id": "acme_idea_existing-run", "brand": "acme", "stage": "brief",
                    "title": "Design", "brief": "Current words", "next_action": "Finish layout",
                    "references": [{"path": "runs/source/swipe.jpg", "role": "picked swipe"}]}
        self.manifest = self.repo / "request.json"
    def build(self):
        self.manifest.write_text(json.dumps(self.req))
        return A.build(self.manifest, self.repo)
    def test_queue_packet_and_generation_refusal(self):
        folder, sheet = self.build()
        self.assertEqual(sheet["state"], "brief")
        self.assertFalse(sheet["execution_ready"])
        self.assertEqual((folder / sheet["references"][0]["local"]).read_bytes(), b"swipe bytes")
        spec = importlib.util.spec_from_file_location("maker", HERE.parent / "briefs/make.py")
        maker = importlib.util.module_from_spec(spec); spec.loader.exec_module(maker)
        with self.assertRaisesRegex(SystemExit, "not execution-ready"):
            maker.plan(folder, 1)
    def test_repeat_preserves_return_and_production_packet(self):
        folder, _ = self.build()
        returned = folder / "returned/delivered.png"; returned.write_bytes(b"return")
        self.build(); self.assertEqual(returned.read_bytes(), b"return")
        (folder / "run.json").write_text('{"packet_kind":"production"}')
        with self.assertRaisesRegex(BadRequest, "production packet is preserved"):
            self.build()
    def test_missing_and_private_escape_refused_before_output(self):
        for path in ("../outside", "runs/source/missing.jpg", "runs/_hold/rejected.jpg"):
            self.req["references"][0]["path"] = path
            with self.assertRaises(BadRequest): self.build()
        self.assertFalse((self.repo / "runs/handoffs").exists())
    def test_symlink_escape_refused(self):
        (self.repo / "runs/source/outside").symlink_to("/etc/hosts")
        self.req["references"][0]["path"] = "runs/source/outside"
        with self.assertRaises(BadRequest): self.build()

if __name__ == "__main__": unittest.main()
