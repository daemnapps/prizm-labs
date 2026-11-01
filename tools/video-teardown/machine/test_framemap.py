"""The frame map (2026-10-01): cuts found in the pixels, one answer per shot,
nothing asked twice. A made-up two-colour video, no model."""
import json, subprocess, tempfile, unittest
from pathlib import Path
import framemap as fm


class FrameMap(unittest.TestCase):
    def test_cuts_shots_and_a_cached_answer(self):
        d = Path(tempfile.mkdtemp()); (d / "stages").mkdir()
        (d / "stages" / "1-teardown.md").write_text("**CAST**\n\n**Host**\n*   Voice: Female\n\n**PLACES**\n")
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=red:s=180x320:d=1.5",
                        "-f", "lavfi", "-i", "color=blue:s=180x320:d=1.5", "-filter_complex",
                        "[0][1]concat=n=2:v=1:a=0", str(d / "source.mp4")], check=True)
        calls = []
        def ask(clip, text, want_json=True):
            calls.append(clip)
            return [{"who": ["Host (face)"], "moments": [{"t": 0.0, "who": "Host", "does": "holds still"}]}]
        doc = fm.build(d, ask=ask, workers=1)
        self.assertEqual(len(doc["shots"]), 2, doc["cuts"])
        self.assertAlmostEqual(doc["cuts"][0], 1.5, delta=0.1)
        self.assertEqual(doc["shots"][0]["map"]["who"], ["Host (face)"])      # a one-item list is unwrapped
        self.assertIn("Host", doc["people"])
        fm.build(d, ask=ask, workers=1)
        self.assertEqual(len(calls), 2)                                     # cached: never asked twice
        self.assertIn("## K02", (d / "framemap" / "FRAME-MAP.md").read_text())
        # EVERY frame at 8 a second, named <K>-<index>-<t>.jpg, indexed (2026-10-08)
        idx = json.loads((d / "framemap" / "frames" / "index.json").read_text())
        k2 = [r for r in idx["frames"] if r["shot"] == "K02"]
        self.assertAlmostEqual(len(k2), 12, delta=1)
        self.assertEqual(k2[0]["index"], 0)
        self.assertAlmostEqual(k2[0]["t"], doc["shots"][1]["start"], delta=0.01)
        self.assertAlmostEqual(k2[1]["t"] - k2[0]["t"], 0.125, delta=0.002)
        self.assertRegex(k2[3]["file"], r"^frames/K02/K02-0003-\d+\.\d{3}\.jpg$")
        self.assertTrue((d / "framemap" / k2[3]["file"]).is_file())
        before = (d / "framemap" / k2[0]["file"]).stat().st_mtime
        fm.extract_frames(d / "source.mp4", doc["shots"], d / "framemap")      # idempotent: not cut again
        self.assertEqual((d / "framemap" / k2[0]["file"]).stat().st_mtime, before)
        # the elements cut from those frames: Host in both shots, no position → the full frame
        el = json.loads((d / "framemap" / "elements" / "index.json").read_text())
        host = next(e for e in el["elements"] if e["kind"] == "person")
        self.assertEqual((host["name"], host["shots"]), ("Host", ["K01", "K02"]))
        rec = json.loads((d / "framemap" / host["folder"] / "element.json").read_text())
        self.assertEqual(len(rec["crops"]), len(idx["frames"]))
        self.assertEqual(rec["crops"][0]["box"], [0, 0, 180, 320])
        self.assertTrue((d / "framemap" / host["folder"] / "best.jpg").is_file())
        self.assertIsNone(fm.mirror(d))                                     # a temp run never reaches the Drive


class DriveCopyIsShotsAndText(unittest.TestCase):
    """2026-10-20, worklist 7b option (i): the Drive gets the frame map's text and shots/ only —
    frames/ and elements/ stay on this machine, in both Drive copies (the swipes/ library copy here,
    the runs/ copy in chain.mirror_to_drive)."""

    def fake_run(self):
        d = Path(tempfile.mkdtemp()) / "run"
        fmd = d / "framemap"
        for rel in ("framemap.json", "FRAME-MAP.md", "shots/K01.mp4", "shots/K01-first.jpg",
                    "frames/index.json", "frames/K01/K01-0000-0.000.jpg",
                    "elements/index.json", "elements/person-host/best.jpg"):
            (fmd / rel).parent.mkdir(parents=True, exist_ok=True)
            (fmd / rel).write_text("x")
        (d / "run.json").write_text("{}")
        return d

    def test_library_copy_skips_frames_and_elements(self):
        d = self.fake_run()
        dest = d.parent / "drive"
        got = fm.mirror(d, dest=dest)
        self.assertEqual(got[1], 4)
        names = sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())
        self.assertEqual(names, ["FRAME-MAP.md", "framemap.json", "shots/K01-first.jpg", "shots/K01.mp4"])

    def test_station_copy_skips_frames_and_elements(self):
        # LD-53 (station-path runner): the run goes to runs/video-teardown/<brand>/<slug>/ through
        # run_kit.station push with chain.NOT_ON_DRIVE — never the old components/ mirror.
        import shutil
        from unittest import mock
        import chain as C
        d = self.fake_run()
        (d / "run.json").write_text('{"brand": "brand-a"}')
        drive = d.parent / "drive"

        class Reach:
            def put(self, files, parts):
                dest = drive.joinpath(*parts)
                dest.mkdir(parents=True, exist_ok=True)
                for f in files:
                    shutil.copy2(str(f), str(dest / Path(f).name))
                return "api", list(files), None
        S = C._station()
        with mock.patch.object(C, "runs_root", lambda create=True: d.parent), \
                mock.patch.object(S, "_reach", lambda: Reach()):
            to = C.mirror_to_drive(d.name)
        self.assertEqual(str(to), "Shared Assets/runs/video-teardown/brand-a/" + d.name)
        up = drive / "runs" / "video-teardown" / "brand-a" / d.name
        self.assertTrue((up / "framemap" / "shots" / "K01.mp4").is_file())
        self.assertTrue((up / "framemap" / "framemap.json").is_file())
        self.assertFalse((up / "framemap" / "frames").exists())
        self.assertFalse((up / "framemap" / "elements").exists())
        self.assertFalse((drive / "components").exists())                         # no old mirror
        self.assertFalse((drive / "runs" / "video-writing").exists())             # no brief yet
        (d / "stages").mkdir()
        (d / "stages" / "5-brief.md").write_text("brief")
        with mock.patch.object(C, "runs_root", lambda create=True: d.parent), \
                mock.patch.object(S, "_reach", lambda: Reach()):
            C.mirror_to_drive(d.name)
        self.assertTrue((drive / "runs" / "video-writing" / "brand-a" / d.name / "stages" / "5-brief.md").is_file())
        self.assertTrue((d / "framemap" / "frames" / "index.json").is_file())     # the local run keeps all

    def test_no_brand_is_a_loud_mount_error(self):
        from unittest import mock
        import chain as C
        d = self.fake_run()
        with mock.patch.object(C, "runs_root", lambda create=True: d.parent):
            with self.assertRaises(C.MountError):
                C.mirror_to_drive(d.name)


class Positions(unittest.TestCase):
    def test_ranges_points_and_words(self):
        import frame_elements as fe
        self.assertEqual(fe.parse_position("centred (20% to 60% width, 20% to 80% height)"),
                         {"w": (20.0, 60.0), "h": (20.0, 80.0), "how": "range"})
        self.assertEqual(fe.parse_position("Model center (30-90% width)")["w"], (30.0, 90.0))
        self.assertEqual(fe.parse_position("(20-80% W, 10-70% H)")["h"], (10.0, 70.0))
        self.assertEqual(fe.parse_position("visible from 10% to 90% height")["h"], (10.0, 90.0))
        self.assertIsNone(fe.parse_position("(left, 20% width) faces right"))       # one person: a point is no box
        self.assertEqual(fe.parse_position("(left, 20% width)", crowd=True)["w"], (5.0, 35.0))
        self.assertEqual(fe.parse_position("on left, facing camera", crowd=True)["w"], (0.0, 55.0))
        self.assertIsNone(fe.parse_position("eyes at 40% height"))                  # a body mark, not a box

    def test_crop_box_pads_and_clamps(self):
        import frame_elements as fe
        self.assertEqual(fe.crop_box({"w": (20.0, 60.0), "h": (20.0, 80.0)}, 1000, 2000), (120, 240, 680, 1760))
        self.assertEqual(fe.crop_box({"w": (0.0, 95.0), "h": None}, 1000, 2000), (0, 0, 1000, 2000))
        self.assertEqual(fe.crop_box(None, 1080, 1920), (0, 0, 1080, 1920))

    def test_segment_stops_at_the_next_person(self):
        import frame_elements as fe
        t = "Makeup Artist (left, 20% width) faces right. Model (center, 50% width) faces forward."
        self.assertIn("20%", fe.segment(t, "Makeup Artist", ["Model"]))
        self.assertNotIn("50%", fe.segment(t, "Makeup Artist", ["Model"]))
        self.assertIn("50%", fe.segment(t, "Model", ["Makeup Artist"]))


if __name__ == "__main__":
    unittest.main()
