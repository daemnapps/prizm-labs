#!/usr/bin/env python3
"""Tests for casting's baseline taking the frames the footage reader hands it
(SI-99 (asset-index readers)): extract.py writes `f_NN.jpg` and names them in
clip.json, so a row's own `frames` win; an older row without them still
falls back to the record's `frame_*.jpg`.

    /usr/bin/python3 components/casting/tests/test_record_frames.py

Stdlib `unittest`, 3.9-safe. A stub footage reader and temp folders only.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                  # APPEND — never insert at 0
import casting as C                                # noqa: E402


class StubReader:
    """Stands in for image-production's assets reader."""

    def __init__(self, rows):
        self.rows = rows

    def described(self, brand, force=False):
        return list(self.rows)

    def pick(self, brand, like, limit=4):
        return [], []


class RecordFrames(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="casting-record-frames-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.rec = self.tmp / "rec"
        self.rec.mkdir()

    def test_reader_frames_win(self):
        frame = self.rec / "f_01.jpg"
        frame.write_bytes(b"jpg")
        reader = StubReader([{"name": "a.mp4", "collection": "pull1", "kind": "footage",
                              "said": "a baker in a bakery", "record": str(self.rec),
                              "frames": [str(frame)]}])
        rows, _ = C.search.baselines("fx", "baker", reader=reader)
        self.assertEqual(rows[0]["baseline"], str(frame))

    def test_old_records_still_work(self):
        frame = self.rec / "frame_01.jpg"
        frame.write_bytes(b"jpg")
        reader = StubReader([{"name": "a.mp4", "collection": "fx-old", "kind": "footage",
                              "said": "a baker in a bakery", "record": str(self.rec)}])
        rows, _ = C.search.baselines("fx", "baker", reader=reader)
        self.assertEqual(rows[0]["baseline"], str(frame))


if __name__ == "__main__":
    unittest.main()
