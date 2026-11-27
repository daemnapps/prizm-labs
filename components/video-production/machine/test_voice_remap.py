"""Voices follow a renumbered brief by their words (2026-10-02): same words are
copied, a split line is cut from its own recording in order, nothing re-recorded."""
import json, subprocess, tempfile, unittest
from pathlib import Path
import voice_remap as vr


def tone(path, secs):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"sine=d={secs}", str(path)], check=True)


class Remap(unittest.TestCase):
    def test_copy_split_and_order(self):
        run = Path(tempfile.mkdtemp()); (run / "vo").mkdir()
        old = {"S1": "Hello there.", "S2": "Feel like it keeps coming back, like...", "S3": "He is like a friend."}
        (run / "lines.json").write_text(json.dumps(old))
        (run / "vo" / "manifest.json").write_text(json.dumps({k: {"voice_id": "v"} for k in old}))
        for k in old:
            tone(run / "vo" / f"{k}.mp3", 3)
        doc = {"scenes": [{"id": "S1", "voice": "Hello there."},
                          {"id": "S2", "voice": "Feel like it keeps coming back,"},
                          {"id": "S3", "voice": "like..."},
                          {"id": "S4", "voice": "He is like a friend."}]}
        brief = run / "brief.md"; brief.write_text("x\n```json\n" + json.dumps(doc) + "\n```\n")
        ws = [("feel", 0.0, 0.3), ("like", 0.3, 0.5), ("it", 0.5, 0.6), ("keeps", 0.6, 0.9), ("coming", 0.9, 1.2),
              ("back", 1.2, 1.5), ("like", 2.0, 2.3)]
        stt = lambda f: {"words": [{"text": w, "start": a, "end": b} for w, a, b in ws]}
        plan, lost = vr.remap(run, brief, stt=stt)
        self.assertEqual(lost, [])
        self.assertEqual(plan["S1"]["how"], "same words")
        self.assertEqual(plan["S4"]["from"], "S3")                  # renumbered, same recording
        self.assertEqual(plan["S3"]["from"], "S2")                  # "like..." is the tail of S2, not S3's "like"
        self.assertGreaterEqual(plan["S3"]["cut"][0], 1.5)          # found after the part before it
        self.assertTrue((run / "vo" / "S4.mp3").exists())
        self.assertEqual(json.loads((run / "lines.json").read_text())["S3"], "like...")


if __name__ == "__main__":
    unittest.main()
