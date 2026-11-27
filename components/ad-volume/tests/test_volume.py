"""Offline checks of the ad-volume runner: formats load, take args follow the tier, the spend floor holds a take,
the edit renders versions, the Studio files are written. No network, no credits. Run: python3 -m unittest discover"""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
TMP = tempfile.mkdtemp()
os.environ["VIDEO_STUDIO_DATA"] = TMP
sys.path.insert(0, str(HERE))
import volume as V  # noqa: E402

KIT = {"avatar": "zz-a", "product": "acme-thing", "product_name": "Acme thing", "product_use": "rubs it in",
       "cast": [{"name": "ann", "group": "g1", "file": "x/ann.jpg", "looks": "a woman", "role": "hero"}],
       "product_refs": [], "sets": []}
CONCEPT = {"id": "c01", "format": "micro-drama", "title": "T", "cast": ["ann"], "take_prompt": "Ann talks.",
           "beats": [{"id": "hook", "at": [0, 2.5], "who": "ann", "does": "points", "says": "Look."}],
           "hooks": [{"id": "H1", "text": "Look at this"}, {"id": "H2", "text": "No way"}], "end_card": "Try it today"}


class Volume(unittest.TestCase):
    def test_formats(self):
        for f in ("micro-drama", "song-ad", "ai-skit"):
            self.assertIn(f, V.FORMATS)
            self.assertTrue(V.FORMATS[f]["beats"])

    def test_args_follow_tier(self):
        a = V._args("test-seedance", "p", ["u1", "u2"], 12)
        self.assertEqual(a[0], "seedance_2_5")
        self.assertIn("omni_reference", a)
        self.assertEqual(a.count("--image-references"), 2)
        self.assertNotIn("--mode", V._args("test", "p", [], 12))

    def test_take_prompt_names_cast_and_no_text(self):
        p = V._take_prompt(CONCEPT, KIT)
        self.assertIn("ann = a woman", p)
        self.assertIn("no on-screen text", p)

    def test_floor_holds_take(self):
        batch = "vol-20000101-acme"
        V.save(V.batch_dir(batch) / "batch.json", {"batch": batch, "brand": "acme", "concepts": [CONCEPT]})

        def fake_hf(*a, **k):
            if a[:2] == ("account", "status"):
                return {"credits": 305}
            if a[:2] == ("generate", "cost"):
                return {"credits": 12}
            if a[:2] == ("upload", "create"):
                return {"id": "u"}
            raise AssertionError(f"no job may be sent: {a[:2]}")
        with mock.patch.object(V, "kit", return_value=KIT), mock.patch.object(V, "hf", side_effect=fake_hf), \
                mock.patch.object(V, "_refs", return_value=[]):
            res = V.make(batch, floor=300)
        self.assertEqual(res[0]["state"], "held (spend floor)")

    def test_edit_and_studio(self):
        batch = "vol-20000102-acme"
        V.save(V.batch_dir(batch) / "batch.json", {"batch": batch, "brand": "acme", "concepts": [CONCEPT]})
        take = V.concept_dir(batch, "c01") / "take" / "take.mp4"
        take.parent.mkdir(parents=True)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=480x854:d=3", "-f", "lavfi",
                        "-i", "sine=f=440:d=3", "-shortest", "-pix_fmt", "yuv420p", str(take)], check=True)
        V.save(take.parent / "sent.json", {"state": "made", "credits": 12})
        V.edit(batch)
        cd = V.concept_dir(batch, "c01")
        self.assertTrue((cd / "rough-cut-v1-sdr.mp4").is_file())
        self.assertTrue((cd / "versions" / "H2" / f"{cd.name}-H2.mp4").is_file())
        with mock.patch.object(V, "kit", return_value=KIT):
            V.studio(batch)
        b = json.loads((cd / "brief.json").read_text())
        self.assertEqual(b["order"], ["S1"])
        self.assertTrue((cd / "stages.html").is_file())
        self.assertTrue((V.batch_dir(batch) / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
