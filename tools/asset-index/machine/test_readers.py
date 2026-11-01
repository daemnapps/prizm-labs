#!/usr/bin/env python3
"""Tests for asset-index's one reader of clip records and extract.py's failed
step (SI-99 (asset-index readers)): collections() reads runs/asset-index/<brand>/*,
then work/<brand>-*, then the old lab folder (name contains the brand), newer
home winning on a shared name; record_frames() returns the frames clip.json
names; a failed ffmpeg step writes no clip.json and the run exits non-zero.
No network, no ffmpeg, no faster_whisper: every folder is a temp folder.

    /usr/bin/python3 tools/asset-index/machine/test_readers.py
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "brandpath"))
sys.path.insert(0, str(HERE))
import shared_paths  # noqa: E402
import extract  # noqa: E402


def _mk(*dirs):
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


class Collections(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="asset-index-readers-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.runs, self.work, self.lab = self.tmp / "runs", self.tmp / "work", self.tmp / "lab"

    def _names(self, brand="fx"):
        return [p.name for p in shared_paths.collections(brand, work=self.work, runs=self.runs, lab=self.lab)]

    def test_order_runs_then_work_then_lab(self):
        _mk(self.runs / "fx" / "pull1", self.work / "fx-a", self.lab / "fx-b", self.work / "zz-c")
        self.assertEqual(self._names(), ["pull1", "fx-a", "fx-b"])

    def test_runs_skips_hidden_and_underscore(self):
        _mk(self.runs / "fx" / "pull1", self.runs / "fx" / ".tmp", self.runs / "fx" / "_maps")
        (self.runs / "fx" / "notes.txt").write_text("x")
        self.assertEqual(self._names(), ["pull1"])

    def test_lab_leftover_is_read_when_it_is_the_only_source(self):
        _mk(self.lab / "fx-b")
        got = shared_paths.collections("fx", work=self.work, runs=self.runs, lab=self.lab)
        self.assertEqual(got, [self.lab / "fx-b"])
        with mock.patch.object(shared_paths, "RUNS", self.runs), \
                mock.patch.object(shared_paths, "WORK", self.work), \
                mock.patch.object(shared_paths, "LAB_WORK", self.lab):
            self.assertEqual(shared_paths.collections("fx"), [self.lab / "fx-b"])
            self.assertEqual(shared_paths.runs_root(), self.runs)

    def test_lab_matches_by_contains(self):
        _mk(self.lab / "creators-fx-2025", self.lab / "other")
        self.assertEqual(self._names(), ["creators-fx-2025"])
        self.assertEqual(self._names("FX"), ["creators-fx-2025"])

    def test_same_name_newer_home_wins(self):
        _mk(self.work / "fx-a", self.lab / "fx-a")
        got = shared_paths.collections("fx", work=self.work, runs=self.runs, lab=self.lab)
        self.assertEqual(got, [self.work / "fx-a"])

    def test_nothing_anywhere_is_empty_not_an_error(self):
        self.assertEqual(self._names(), [])


class RecordFrames(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="asset-index-frames-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_record_frames(self):
        rec = self.tmp / "rec"
        rec.mkdir()
        for n in ("f_01.jpg", "f_02.jpg"):
            (rec / n).write_bytes(b"x")
        (rec / "clip.json").write_text(json.dumps(
            {"frames": [{"file": "f_01.jpg", "t": 0.0}, {"file": "f_02.jpg", "t": 8.0}]}))
        self.assertEqual(shared_paths.record_frames(rec), [str(rec / "f_01.jpg"), str(rec / "f_02.jpg")])

        old = self.tmp / "old"
        old.mkdir()
        (old / "frame_01.jpg").write_bytes(b"x")
        self.assertEqual(shared_paths.record_frames(old), [str(old / "frame_01.jpg")])

        self.assertEqual(shared_paths.record_frames(self.tmp / "missing"), [])
        self.assertEqual(shared_paths.record_frames(None), [])

    def test_named_frames_missing_fall_back_to_glob(self):
        rec = self.tmp / "rec"
        rec.mkdir()
        (rec / "f_03.jpg").write_bytes(b"x")
        (rec / "clip.json").write_text(json.dumps({"frames": [{"file": "f_09.jpg"}]}))
        self.assertEqual(shared_paths.record_frames(rec), [str(rec / "f_03.jpg")])
        (rec / "clip.json").write_text("{not json")
        self.assertEqual(shared_paths.record_frames(rec), [str(rec / "f_03.jpg")])


def _done(code, stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=code, stdout="", stderr=stderr)


class ExtractFails(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="asset-index-extract-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.meta = {"duration_s": 4, "width": 1, "height": 1, "has_audio": False, "size_mb": 0.1}

    def test_extract_refuses_a_failed_ffmpeg(self):
        out = self.tmp / "clip"
        with mock.patch.object(extract, "run", return_value=_done(1, "boom")):
            with self.assertRaises(extract.StepFailed) as e:
                extract.extract(self.tmp / "a.mp4", out, self.meta)
            self.assertIn("boom", str(e.exception))
        with mock.patch.object(extract, "run", return_value=_done(0)):
            with self.assertRaises(extract.StepFailed):
                extract.extract(self.tmp / "a.mp4", out, self.meta)
        with mock.patch.object(extract, "run", return_value=_done(1, "no audio")):
            with self.assertRaises(extract.StepFailed):
                extract.transcribe(self.tmp / "a.mp4", out, object())

    def test_a_failed_clip_writes_no_record_and_the_run_fails(self):
        src, out = self.tmp / "src", self.tmp / "out"
        src.mkdir()
        (src / "a.mp4").write_bytes(b"")
        fake = types.ModuleType("faster_whisper")
        fake.WhisperModel = lambda *a, **k: object()
        printed = io.StringIO()
        with mock.patch.dict(sys.modules, {"faster_whisper": fake}), \
                mock.patch.object(extract, "probe", return_value=dict(self.meta)), \
                mock.patch.object(extract, "extract", side_effect=extract.StepFailed("frames: boom")), \
                contextlib.redirect_stdout(printed):
            code = extract.main([str(src), "--brand", "fx", "--out", str(out)])
        self.assertNotEqual(code, 0)
        self.assertEqual(list(out.rglob("clip.json")), [])
        self.assertIn("FAIL a.mp4:", printed.getvalue())


if __name__ == "__main__":
    unittest.main()
