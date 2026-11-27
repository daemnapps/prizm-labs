"""set_queue.reopen: a done request opens again for a new print and its set's kept prints are retired, never deleted,
so the old print can never stay the picture (2026-11-21, brief-0380). Temp folders only."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.append(str(Path(__file__).resolve().parents[1]))
from image_production import set_queue as Q  # noqa: E402
from image_production import set_gate as G  # noqa: E402


class Reopen(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, True)
        self.reqs = self.t / "runs" / "image-production" / "b" / "set-requests"; self.reqs.mkdir(parents=True)
        self.set = self.t / "runs" / "image-production" / "b" / "sets" / "r-s1-f1"; self.set.mkdir(parents=True)
        (self.set / "print-v1.png").write_bytes(b"p")
        (self.set / "set.json").write_text(json.dumps({"prints": [{"file": "print-v1.png", "note": "kept: right"}]}))
        (self.reqs / "r-s1-f1.json").write_text(json.dumps({"id": "r-s1-f1", "state": "done", "set": "r-s1-f1"}))
        for p in (mock.patch.object(Q.P, "repo", lambda *a: self.t), mock.patch.object(Q, "home", lambda b: self.reqs)):
            p.start(); self.addCleanup(p.stop)

    def test_a_done_request_opens_and_its_kept_print_is_retired(self):
        r = Q.reopen("b", "r-s1-f1", "wrong outfit")
        self.assertEqual(r["state"], "open")
        self.assertNotIn("set", r)
        note = json.loads((self.set / "set.json").read_text())["prints"][0]["note"]
        self.assertTrue(note.startswith("retired: wrong outfit (was: kept: right)"))
        self.assertTrue((self.set / "print-v1.png").is_file())                 # never deleted
        with mock.patch.object(G, "homes", lambda b, n: [self.set], create=True), \
                mock.patch.object(G, "record", lambda b, n: json.loads((self.set / "set.json").read_text())):
            self.assertIsNone(G.kept_print("b", "r-s1-f1"))

    def test_a_reason_is_required_and_a_printing_request_is_refused(self):
        with self.assertRaises(SystemExit):
            Q.reopen("b", "r-s1-f1", " ")
        (self.reqs / "r-s1-f1.json").write_text(json.dumps({"id": "r-s1-f1", "state": "open", "printing": {"g": 1}}))
        with self.assertRaises(SystemExit):
            Q.reopen("b", "r-s1-f1", "x")


if __name__ == "__main__":
    unittest.main()
