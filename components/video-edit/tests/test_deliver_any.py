"""The one door (machine/deliver_any.py) and the used-everything check (machine/studio/used_everything.py).
No network, no render, no live production: every case builds its own folder."""
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

VE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VE / "machine"))
sys.path.insert(0, str(VE / "machine" / "studio"))


def _w(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj) if not isinstance(obj, (str, bytes)) else obj) if not isinstance(obj, bytes) else p.write_bytes(obj)


class Roads(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        import deliver_any as DA
        self.DA = DA

    def test_a_hand_off_folder_takes_the_hand_off_road(self):
        _w(self.t / "h" / "manifest.json", {"role": "video-editor"})
        self.assertEqual(self.DA.road_of(str(self.t / "h"))[0], "handoff")

    def test_a_kit_takes_the_kit_road(self):
        _w(self.t / "k" / "edit-kit.json", {"brand": "b"})
        self.assertEqual(self.DA.road_of(str(self.t / "k"))[0], "kit")

    def test_a_production_run_takes_the_line(self):
        _w(self.t / "r" / "plan.json", {}); _w(self.t / "r" / "run.json", {})
        self.assertEqual(self.DA.road_of(str(self.t / "r"))[0], "line")

    def test_a_studio_folder_takes_the_studio_road(self):
        _w(self.t / "idea-1" / "brief.json", {}); (self.t / "idea-1" / "scenes").mkdir()
        self.assertEqual(self.DA.road_of(str(self.t / "idea-1")), ("studio", "idea-1"))


class UsedEverything(unittest.TestCase):
    """A one-scene production whose edit plays exactly what production made, then broken one way at a time."""

    def setUp(self):
        self.data = Path(tempfile.mkdtemp())
        os.environ["VIDEO_STUDIO_DATA"] = str(self.data)
        for m in ("settings", "video_studio", "used_everything"):
            sys.modules.pop(m, None)
        import used_everything as UE
        self.UE = UE
        self.B = self.data / "briefs" / "p1"
        _w(self.B / "brief.json", {"order": ["S1"], "picks": {"S1": "take-1"}})
        _w(self.B / "scenes" / "S1" / "take-1.json", {"steps": []})
        self.clip = b"scene-one-clip"
        _w(self.B / "scenes" / "S1" / "out" / "take-1" / "S1.mp4", self.clip)
        _w(self.B / "scenes" / "S1" / "out" / "take-1" / "S1.captions.json", {"lines": [{"text": "Your skin, sorted."}]})
        _w(self.B / "studio" / "assets" / "S1.mp4", self.clip)
        self.page = ('<video src="assets/S1.mp4"></video><div class="plate"><span>Your</span> <span>skin,</span> '
                     '<span>sorted.</span></div>')
        _w(self.B / "studio" / "index.html", self.page)
        _w(self.B / "rough-cut-v1-sdr.mp4", b"control")

    def tearDown(self):
        os.environ.pop("VIDEO_STUDIO_DATA", None)

    def holds(self):
        return [(c, w) for ok, c, w in self.UE.check("p1", self.B, level=False) if not ok]

    def test_what_production_made_passes(self):
        self.assertEqual(self.holds(), [])

    def test_a_swapped_clip_holds(self):
        _w(self.B / "studio" / "assets" / "S1.mp4", b"another-clip-entirely")
        self.assertEqual([c for c, _ in self.holds()], ["the scene as made"])

    def test_a_missing_caption_word_holds(self):
        _w(self.B / "studio" / "index.html", self.page.replace("<span>sorted.</span>", ""))
        self.assertEqual([c for c, _ in self.holds()], ["every line on screen"])

    def test_media_production_never_made_holds(self):
        _w(self.B / "studio" / "index.html", self.page + '<video src="assets/stock-clip.mp4"></video>')
        self.assertEqual([c for c, _ in self.holds()], ["nothing invented"])

    def test_a_missing_scene_holds(self):
        _w(self.B / "studio" / "index.html", "<div>nothing</div>")
        self.assertIn("every scene in", [c for c, _ in self.holds()])

    def test_a_missing_version_holds(self):
        _w(self.B / "brief.json", {"order": ["S1"], "picks": {"S1": "take-1"}, "hooks": ["H1"]})
        self.assertEqual([c for c, _ in self.holds()], ["every version"])

    def test_a_version_off_level_holds(self):
        res = self.UE.check("p1", self.B, level=True, measure=lambda f: -9.0)
        self.assertEqual([c for ok, c, _ in res if not ok], ["the level"])


if __name__ == "__main__":
    unittest.main()
