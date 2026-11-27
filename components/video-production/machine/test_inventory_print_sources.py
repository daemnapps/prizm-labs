"""A picture taken from a kept 3D print is judged against its print request: the full words, the ad's style and the
reference and cast boards come first in its sources. Run: python3 -m unittest test_inventory_print_sources"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
_sp = importlib.util.spec_from_file_location("vm_cc_print_sources", HERE / "clip_checklist.py")
CC = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(CC)


class PrintSources(unittest.TestCase):
    def test_request_words_style_and_boards(self):
        ws = Path(tempfile.mkdtemp(prefix="invsrc_"))
        run = ws / "runs" / "video-production" / "b" / "r1"
        (run / "media").mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"brand": "b"}))
        rdir = ws / "runs" / "image-production" / "b" / "set-requests"
        rdir.mkdir(parents=True)
        (rdir / "r1-s2-shot-2.json").write_text(json.dumps({
            "id": "r1-s2-shot-2", "scene": "Who and what: the photographer holds his camera", "style": "family-3d",
            "style_formula": "big-studio 3D animated feature", "cast": ["hero", "photographer"]}))
        for f in ("r1-s2-shot-2-reference.png", "r1-s2-shot-2-cast-board.png"):
            (rdir / f).write_bytes(b"x")
        (run / "media" / "S2-shot-2.paste.json").write_text(json.dumps({"from_set": "r1-s2-shot-2"}))
        old = CC.WS
        CC.WS = ws
        try:
            src = CC.sources_of(run, "S2-shot-2", most=4)
        finally:
            CC.WS = old
        text = " ".join(str(x) for x in src)
        self.assertIn("photographer holds his camera", text)
        self.assertIn("family-3d", text)
        self.assertIn("never call it photoreal", text)
        self.assertTrue(any(str(x).endswith("-reference.png") for x in src))
        self.assertTrue(any(str(x).endswith("-cast-board.png") for x in src))


if __name__ == "__main__":
    unittest.main()
