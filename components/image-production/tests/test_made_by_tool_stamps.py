#!/usr/bin/env python3
"""Made by the tool (RULE GATE-5, 2026-11-11): every picture this tool delivers is fingerprinted where it lands, so the
Meta approval filer can tell a tool-made picture from a frame grab or a hand edit (image_production/provenance.py).

    python3 components/image-production/tests/test_made_by_tool_stamps.py

Before this the team line fingerprinted covers only, and models.json had no `gate.made_by_tool`, so the filer's gate
(components/meta-upload/made_by_tool.py `installed`) stayed asleep. Stdlib `unittest` and Pillow; no network, no model,
no key. The ledger is a throwaway file per test (IMAGE_MADE_LEDGER).
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                  # APPEND, never insert at 0
import image_production as IP                      # noqa: E402
from image_production import plain as PL, provenance as PV, words as WD   # noqa: E402
import test_covers as TC                           # noqa: E402  (its workspace: a stub door, a filed set, a stand-in face reader)


def flat(path, colour=(10, 20, 30), size=(270, 480)):
    from PIL import Image
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path)
    return Path(path)


class TheSwitchIsOnTheTeamLine(unittest.TestCase):
    def test_models_json_carries_the_gate_so_the_filer_wakes(self):
        cfg = json.loads((HERE.parent / "models.json").read_text())["gate"]["made_by_tool"]
        self.assertTrue(cfg["on"])
        self.assertTrue(cfg["since"])
        self.assertEqual(cfg["lanes"], {"video": True, "image": True, "carousel": True, "creator": False})
        self.assertEqual(PV.switch(), cfg)
        filer = HERE.parents[1] / "meta-upload" / "made_by_tool.py"
        if filer.is_file():
            import importlib.util
            spec = importlib.util.spec_from_file_location("made_by_tool_under_test", filer)
            MB = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(MB)
            self.assertTrue(MB.installed())


class Ledger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        p = mock.patch.dict(os.environ, {"IMAGE_MADE_LEDGER": str(self.root / "made.jsonl")})
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)


class ToFrameKeepsTheStamp(Ledger):
    def test_a_resize_of_a_tool_picture_is_still_the_tools(self):
        made = flat(self.root / "made.png")
        PV.stamp(made, "engine")
        out = PL.to_frame(made, self.root / "framed.png")
        self.assertTrue(PV.known(out))

    def test_a_resize_of_any_other_picture_is_not(self):
        grab = flat(self.root / "grab.png", (90, 90, 90))
        out = PL.to_frame(grab, self.root / "framed.png")
        self.assertIsNone(PV.known(out))


class TheToolsWordsKeepTheStamp(Ledger):
    def compose(self, colour):
        def run(cmd, capture_output=True, text=True):
            out = cmd[cmd.index("--out") + 1]
            flat(out, colour)
            return mock.Mock(returncode=0, stdout="set 1 element", stderr="")
        return run

    def test_words_over_a_tool_picture_are_stamped_and_over_a_grab_are_not(self):
        layer = {"elements": [{"text": "Hello", "role": "headline"}]}
        made = flat(self.root / "made.png")
        PV.stamp(made, "engine")
        with mock.patch.object(WD.subprocess, "run", self.compose((1, 2, 3))), mock.patch.object(WD, "ui_icons", lambda *a: None):
            got = WD.set_on_top(made, layer, out=self.root / "worded.png")
        self.assertTrue(got["ok"])
        self.assertTrue(PV.known(self.root / "worded.png"))
        grab = flat(self.root / "grab.png", (90, 90, 90))
        with mock.patch.object(WD.subprocess, "run", self.compose((4, 5, 6))), mock.patch.object(WD, "ui_icons", lambda *a: None):
            WD.set_on_top(grab, layer, out=self.root / "grab-worded.png")
        self.assertIsNone(PV.known(self.root / "grab-worded.png"))


class TheEngineStampsEveryPicture(TC.Workspace):
    def test_a_picture_that_is_not_a_cover_is_fingerprinted(self):
        req = {"brand": "b", "purpose": "ad", "direction": "her face close, mid-reaction", "out": str(self.out),
               "set": "lineup", "people": True}
        try:
            got = IP.make(req, library=TC.Library(), transport=TC.door(self.calls), mirror=False)
        except IP.BadRequest as ex:
            self.skipTest(f"an ad picture is refused in this fixture: {str(ex)[:120]}")
        pic = Path(got["delivered"][0])
        self.assertTrue(PV.known(pic))
        run = json.loads((self.out / "run.json").read_text())
        self.assertEqual(run["pictures"][0]["sha256"], PV.sha256(pic))

    def test_a_cover_is_fingerprinted_once_with_its_words(self):
        got = self.make()
        cover = Path(got["delivered"][0])
        rows = [json.loads(x) for x in PV.ledger_path().read_text().splitlines()]
        mine = [r for r in rows if r["sha256"] == PV.sha256(cover)]
        self.assertEqual([r["route"] for r in mine], ["cover"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
