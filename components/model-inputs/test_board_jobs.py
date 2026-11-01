"""The board only starts jobs and shows them; every job runs in its own process and its state is a file
(2026-10-28)."""
import json
import tempfile
import unittest
from pathlib import Path

import prompt_bench as pb


class JobFiles(unittest.TestCase):
    def test_a_job_state_is_read_from_its_file(self):
        with tempfile.TemporaryDirectory() as d:
            st = Path(d) / "m1.json"
            st.write_text(json.dumps({"state": "running"}))
            jobs = pb._Jobs()
            jobs["k"] = {"state": "running", "status_file": str(st), "running_as": "keeping", "done_as": "ready"}
            self.assertEqual(jobs.get("k")["state"], "keeping")
            st.write_text(json.dumps({"state": "done", "picked": 6}))
            self.assertEqual(jobs.get("k")["state"], "ready")
            self.assertEqual(jobs.get("k")["picked"], 6)
            st.write_text(json.dumps({"state": "failed", "error": "refused"}))
            self.assertEqual(jobs.get("k")["state"], "failed")

    def test_a_job_started_before_a_restart_is_still_found(self):
        old = pb.JOB_DIR
        with tempfile.TemporaryDirectory() as d:
            pb.JOB_DIR = Path(d)
            try:
                (Path(d) / "m42.json").write_text(json.dumps({"state": "done", "file": "x.mp4"}))
                self.assertEqual(pb.job("m42")["state"], "done")
                self.assertEqual(pb.job("nope")["state"], "unknown")
            finally:
                pb.JOB_DIR = old

    def test_the_board_starts_no_make_keep_or_remake_in_its_own_thread(self):
        src = (Path(pb.__file__)).read_text()
        for fn in ("def make(", "def shot_keep(", "def shot_change(", "def shot_open("):
            body = src[src.index(fn):]
            body = body[:body.index("\ndef ", 1)]
            self.assertNotIn("threading.Thread", body, fn)
            self.assertIn("_spawn(", body, fn)

    def test_change_it_does_its_work_in_the_job_not_the_board(self):
        """Change it rewrites the swaps and remakes the picture in one job of its own; the board's request only
        records the note and starts it (2026-10-28)."""
        calls = []
        old = (pb.shots, pb._video_run, pb._spawn)
        with tempfile.TemporaryDirectory() as d:
            pb.shots = lambda run: {"brand": "b", "product": "p", "shots": [
                {"id": "G01", "picture_state": "ready", "swipe_frame": "f.jpg", "picture_run": "pr"}]}
            pb._video_run = lambda run: Path(d)
            pb._spawn = lambda fn, args, **kw: calls.append((fn, args)) or "m1"
            try:
                code, got = pb.shot_change({"run": "b/x", "section": "G01", "note": "smaller hands"})
            finally:
                pb.shots, pb._video_run, pb._spawn = old
            self.assertEqual((code, got), (200, {"id": "m1"}))
            self.assertEqual(calls[0][0], "_change_job")
            self.assertEqual(calls[0][1][:4], [d, "G01", "f.jpg", "pr"])
            self.assertEqual(json.loads((Path(d) / "shot-notes.json").read_text())["G01"], ["smaller hands"])
        src = Path(pb.__file__).read_text()
        body = src[src.index("def shot_change("):]
        self.assertNotIn("subprocess", body[:body.index("\ndef ", 1)])

    def test_named_job_survives_board_restart(self):
        import hashlib
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d); (directory / 'keys').mkdir()
            status = directory / 'm99.json'; status.write_text(json.dumps({'state': 'running'}))
            key = 'clip:brand/ad/hooks/h02'
            (directory / 'keys' / (hashlib.sha256(key.encode()).hexdigest()+'.json')).write_text(json.dumps({'status_file': str(status)}))
            with patch.object(pb, 'JOB_DIR', directory):
                self.assertEqual(pb._Jobs().get(key)['state'], 'running')
                status.write_text(json.dumps({'state': 'done', 'file': 'clip.mp4'}))
                self.assertEqual(pb._Jobs().get(key)['file'], 'clip.mp4')


if __name__ == "__main__":
    unittest.main()
