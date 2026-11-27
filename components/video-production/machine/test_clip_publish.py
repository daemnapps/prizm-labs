"""clip_publish.py (2026-10-20): clip check results are saved where the edit reads them, and
the clips reach media/<scene>.mp4. Builds a tiny run with real (ffmpeg-made) clips; spends nothing."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clip_publish as CP  # noqa: E402


def clip(path, secs):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=64x64:d={secs}:r=10",
                    "-f", "lavfi", "-i", f"sine=d={secs}", "-shortest", "-c:v", "libx264", "-c:a", "aac", str(path)], check=True)


OK_QC = {"framing": {"ok": True}, "scene": {"ok": True}, "camera": {"clip_movement": 0.1}, "lips": {"ok": True}, "ok": True}


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class Publish(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.run = Path(self.t.name)
        (self.run / "clips").mkdir()
        calls = [
            {"id": "G1-C1", "at": 0, "lines": [{"scene": "S1", "at": 0, "until": 1.0}, {"scene": "S2", "at": 1.2, "until": 2.5}],
             "voice_parts": [{"scene": "S2"}]},
            {"id": "G1-C2", "at": 2.6, "lines": [{"scene": "S2", "at": 0, "until": 1.0}], "voice_parts": [{"scene": "S2"}]},
            {"id": "G2-C1", "at": 4, "lines": [{"scene": "S3", "at": 0, "until": 1.0}], "voice_parts": []},
        ]
        (self.run / "clips" / "plan.json").write_text(json.dumps({"calls": calls}))
        self.led = {
            "G1-C1": {"status": "done", "qc": OK_QC, "line_check": {"verdict": "PASS", "match": 1.0}},
            "G1-C2": {"status": "done", "qc": OK_QC, "line_check": {"verdict": "PASS", "match": 1.0}},
            "G2-C1": {"status": "done", "qc": OK_QC},
        }
        for cid, s in (("G1-C1", 2.6), ("G1-C2", 1.1), ("G2-C1", 1.1)):
            clip(self.run / "clips" / f"{cid}.mp4", s)

    def tearDown(self):
        self.t.cleanup()

    def save(self):
        (self.run / "clips" / "omni-ledger.json").write_text(json.dumps(self.led))

    def verdicts(self):
        return json.loads((self.run / "verdicts.json").read_text())

    def test_clips_and_verdicts_land_where_the_edit_reads(self):
        self.save()
        res = CP.publish(self.run)
        self.assertEqual(sorted(res["published"]), ["S1", "S2", "S3"])
        for s in ("S1", "S2", "S3"):
            self.assertTrue((self.run / "media" / f"{s}.mp4").stat().st_size > 0)
        v = self.verdicts()
        self.assertEqual(v["S2"]["motion"]["verdict"], "PASS")
        self.assertEqual(v["S2"]["director"]["verdict"], "PASS")
        self.assertEqual(v["S2"]["parity"]["verdict"], "PASS")
        self.assertNotIn("parity", v["S1"])                 # a silent B-roll scene has no words check
        # and the edit's own gate says approved
        ed = HERE.parent.parent / "video-edit" / "machine"
        sys.path.insert(0, str(ed))
        import kit_from_run as K
        for sid, talking in (("S1", False), ("S2", True), ("S3", False)):
            self.assertEqual(K.approved(self.run, sid, talking, v), (True, ""), sid)

    def test_a_cut_off_line_is_not_approved(self):
        self.led["G1-C2"]["line_check"] = {"verdict": "CUT_OFF", "match": 0.9}
        self.save()
        CP.publish(self.run)
        self.assertEqual(self.verdicts()["S2"]["parity"]["verdict"], "CUT_OFF")

    def test_a_check_that_never_ran_writes_no_verdict(self):
        self.led["G2-C1"].pop("qc")
        self.save()
        CP.publish(self.run)
        self.assertNotIn("motion", self.verdicts().get("S3", {}))

    def test_an_unmade_call_holds_its_scenes(self):
        self.led["G1-C2"]["status"] = "failed"
        self.save()
        res = CP.publish(self.run)
        self.assertIn("S2", res["held"])
        self.assertFalse((self.run / "media" / "S2.mp4").exists())


if __name__ == "__main__":
    unittest.main()
