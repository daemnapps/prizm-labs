"""The editor hand-off builder runs from the chain on its own: no Studio module, no Studio setting needed."""
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def load(name, key):
    spec = importlib.util.spec_from_file_location(key, str(HERE / (name + ".py")))
    m = importlib.util.module_from_spec(spec)
    sys.modules[key] = m
    spec.loader.exec_module(m)
    return m


class Standalone(unittest.TestCase):
    def setUp(self):
        self.saved = {k: os.environ.pop(k) for k in ("VIDEO_PRODUCTIONS", "VIDEO_STUDIO_DATA", "VIDEO_WRITING",
                                                     "VIDEO_STUDIO_WRITING") if k in os.environ}
        for k in [k for k in sys.modules if k.startswith("video_edit_maker_")]:
            sys.modules.pop(k)

    def tearDown(self):
        os.environ.update(self.saved)

    def test_defaults_are_this_workspace(self):
        st = load("maker_settings", "video_edit_maker_maker_settings")
        ws = HERE.parents[2]
        self.assertEqual(st.BRIEFS, ws / "runs" / "video-studio" / "briefs")
        self.assertEqual(st.WRITING, ws / "runs" / "video-teardown" / "_work")
        self.assertEqual(st.part("video-edit"), ws / "components" / "video-edit")

    def test_a_named_productions_folder_wins(self):
        os.environ["VIDEO_PRODUCTIONS"] = "/somewhere/productions"
        st = load("maker_settings", "video_edit_maker_maker_settings")
        self.assertEqual(str(st.BRIEFS), "/somewhere/productions")

    def test_a_callers_same_named_module_is_never_used(self):
        decoy = types.ModuleType("maker_elements")
        sys.modules["maker_elements"] = decoy                      # e.g. the Studio's own forwarder
        sys.modules["settings"] = types.ModuleType("settings")
        try:
            mp = load("maker_pack", "video_edit_maker_maker_pack")
            me = mp._here("maker_elements")
            self.assertIsNot(me, decoy)
            self.assertTrue(hasattr(me, "build"))
            self.assertEqual(Path(mp.ST.__file__).parent, HERE)
        finally:
            sys.modules.pop("maker_elements", None)
            sys.modules.pop("settings", None)


class SungParts(unittest.TestCase):
    """A sung production joins written scenes; its clips are one per written scene and place, on the song's clock."""

    def test_joined_scenes_split_by_written_scene_and_place(self):
        sys.modules["settings"] = types.ModuleType("settings")
        try:
            mp = load("maker_pack", "video_edit_maker_maker_pack_sung")
        finally:
            sys.modules.pop("settings", None)
        sh = lambda i, a, b, where: {"id": i, "start": a, "end": b, "where": where, "lyrics": [i]}  # noqa: E731
        song = {"brief_scenes": [
            {"id": "S1", "shots": [sh("S1.1", 0.3, 2.0, "BATH"), sh("S1.2", 2.0, 4.0, "BATH")]},
            {"id": "S2", "shots": [sh("S2.1", 4.5, 6.0, "OFFICE")]},
            {"id": "S3", "shots": [sh("S3.1", 7.0, 9.0, "KITCHEN"), sh("S3.2", 9.0, 11.0, "OFFICE"),
                                   sh("S3.3", 11.0, 12.0, "KITCHEN")]}]}
        parts = mp._sung_parts(song, ["S1"])                     # the production joined all three into S1
        got = [(p["scene"], p["where"], [x["id"] for x in p["shots"]]) for p in parts["S1"]]
        self.assertEqual(got, [("S1", "BATH", ["S1.1", "S1.2"]), ("S2", "OFFICE", ["S2.1"]),
                               ("S3", "KITCHEN", ["S3.1"]), ("S3", "OFFICE", ["S3.2"]), ("S3", "KITCHEN", ["S3.3"])])

    def test_a_part_never_passes_one_generation(self):
        sys.modules["settings"] = types.ModuleType("settings")
        try:
            mp = load("maker_pack", "video_edit_maker_maker_pack_sung2")
        finally:
            sys.modules.pop("settings", None)
        shots = [{"id": "S1.%d" % i, "start": i * 4.0, "end": i * 4.0 + 4.0, "where": "BATH"} for i in range(6)]
        parts = mp._sung_parts({"brief_scenes": [{"id": "S1", "shots": shots}]}, ["S1"])["S1"]
        self.assertTrue(all(p["end"] - p["start"] <= mp.CLIP_MAX_S for p in parts))
        self.assertEqual(sum(len(p["shots"]) for p in parts), 6)


if __name__ == "__main__":
    unittest.main()
