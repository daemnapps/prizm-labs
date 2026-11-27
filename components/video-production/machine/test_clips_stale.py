#!/usr/bin/env python3
"""A call whose inputs changed since its clip was made is a new call (clips_run.stale_calls): a remade picture or a new
prompt makes it again on the run's go; an unchanged call keeps its clip. Nothing is called.

    python3 components/video-production/machine/test_clips_stale.py
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clips_run as C  # noqa: E402


class Stale(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="stale_"))
        (self.run / "clips").mkdir()
        (self.run / "media").mkdir()
        self.pic = self.run / "media" / "S1-F1.png"
        self.pic.write_bytes(b"v1")
        self.clip = self.run / "clips" / "C1.mp4"
        self.clip.write_bytes(b"mp4")
        self.call = {"id": "C1", "start_frame": "S1-F1", "prompt": "p"}
        p = mock.patch.object(C.cp, "picture_file", lambda run, f: self.pic if f == "S1-F1" else None)
        p.start()
        self.addCleanup(p.stop)

    def ledger(self, **row):
        led = C.Ledger(self.run)
        led.put("C1", status="done", **row)

    def test_a_fingerprinted_clip_is_stale_only_when_its_pictures_change(self):
        self.ledger(inputs=C.inputs_of(self.run, self.call), pictures=C.pictures_of(self.run, self.call))
        self.assertEqual(C.stale_calls(self.run, [self.call]), [])
        self.pic.write_bytes(b"v2")                                   # the picture was remade
        self.assertEqual(C.stale_calls(self.run, [self.call]), ["C1"])
        self.pic.write_bytes(b"v1")
        # 2026-11-21, brief-0380: a chain change that only rewrote the words re-made a good clip; words alone never do
        self.assertEqual(C.stale_calls(self.run, [dict(self.call, prompt="new")]), [])

    def test_a_clip_recorded_with_words_in_its_fingerprint_is_not_remade_for_new_words(self):
        self.ledger(inputs="an-old-fingerprint-with-words")
        old = time.time() - 100
        os.utime(self.pic, (old, old))
        self.assertEqual(C.stale_calls(self.run, [dict(self.call, prompt="new")]), [])

    def test_an_older_clip_is_stale_when_a_picture_it_sends_is_newer(self):
        self.ledger()
        old = time.time() - 100
        os.utime(self.pic, (old, old))
        self.assertEqual(C.stale_calls(self.run, [self.call]), [])
        os.utime(self.pic, None)
        os.utime(self.clip, (old - 10, old - 10))
        self.assertEqual(C.stale_calls(self.run, [self.call]), ["C1"])


if __name__ == "__main__":
    unittest.main()
