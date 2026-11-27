#!/usr/bin/env python3
"""python3 machine/test_audiocheck.py — the audio gate, with a fake ear. No network."""
from __future__ import annotations
import importlib.util, json, shutil, subprocess, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("t_audiocheck", HERE / "audiocheck.py")
ac = importlib.util.module_from_spec(spec); spec.loader.exec_module(ac)


def ear(text):
    def t(method, url, headers, body):
        return 200, {}, json.dumps({"text": text}).encode()
    return t


class Gate(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="vm-audio-"))
        (self.run / "vo").mkdir()
        (self.run / "lines.json").write_text(json.dumps({"S1": "Doctor said taking the top layer off is a cop out."}))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
                        "-af", "volume=2.0", str(self.run / "vo" / "S1.mp3")], check=True)

    def tearDown(self):
        shutil.rmtree(self.run, ignore_errors=True)

    def test_a_whole_line_passes(self):
        out = ac.check_run(self.run, fix=False, transport=ear("Doctor said taking the top layer off is a cop out."), key="k")
        self.assertTrue(out["pass"])
        self.assertTrue((self.run / "vo" / "audio-check.json").exists())

    def test_a_line_that_stops_short_stops_the_run(self):
        out = ac.check_run(self.run, fix=False, transport=ear("Doctor said taking the top layer"), key="k")
        self.assertFalse(out["pass"])
        self.assertIn("the line does not finish", out["scenes"]["S1"]["problems"])

    def test_silence_is_broken_sound(self):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=d=2", str(self.run / "vo" / "S1.mp3")], check=True)
        out = ac.check_run(self.run, fix=False, transport=ear("Doctor said taking the top layer off is a cop out."), key="k")
        self.assertFalse(out["pass"])
        self.assertTrue(any("broken sound" in p for p in out["scenes"]["S1"]["problems"]))


if __name__ == "__main__":
    unittest.main()
