"""The full-download guard (2026-10-21, thread 20261020T0755Z post 139): a search never reads a clip, and a frame
asked for later is made by a RANGED seek on the Drive URL when the record knows its Drive id, never by reading
the whole original. Found when one search on a clean checkout began pulling multi-GB originals (post 138).

    python3 tools/asset-index/machine/test_download_guard.py

Fakes only: the ranged request, local() and ffmpeg are replaced; no Drive, no network.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shared_paths as SP  # noqa: E402
import search as S  # noqa: E402

FID = "1RiBpCr8t4mD-8_KKpwbG58rFql-30aSF"


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.col = self.tmp / "acme" / "creators"
        self.rec = self.col / FID
        self.rec.mkdir(parents=True)
        (self.rec / "clip.json").write_text(json.dumps({
            "clip_id": FID, "drive_id": FID, "label": "Shared Assets/brands/acme/creators/raw/kitchen.mov",
            "meta": {"duration_s": 40.0}, "frames": [{"file": "frame_01.jpg", "at_s": 6.0}, {"file": "frame_02.jpg", "at_s": 20.0}]}))
        (self.rec / "breakdown.json").write_text(json.dumps({"scenes": [
            {"t_start": 0, "t_end": 40, "visuals": "woman spreads scrub along her forearm at a kitchen sink"}]}))
        (self.col / "map.json").write_text(json.dumps({FID: {"label": "Shared Assets/brands/acme/creators/raw/kitchen.mov"}}))
        self.local, self.ranged, self.cmds = [], [], []

        def local(ref):
            self.local.append(ref)
            return str(self.tmp / "whole.mov")

        def media_request(fid):
            self.ranged.append(fid)
            return "https://www.googleapis.com/drive/v3/files/%s?alt=media" % fid, "Authorization: Bearer T\r\n"

        def run(cmd):
            self.cmds.append(cmd)
            Path(cmd[-1]).write_bytes(b"jpg")
        for p in (mock.patch.object(SP, "local", local), mock.patch.object(SP, "_media_request", media_request),
                  mock.patch.object(SP, "_run", run)):
            p.start()
            self.addCleanup(p.stop)
        S._corpus.cache_clear()
        self.addCleanup(S._corpus.cache_clear)

    def test_a_clip_frame_is_a_ranged_seek_never_the_whole_file(self):
        got = SP.record_frames(self.rec)
        self.assertEqual([Path(f).name for f in got], ["frame_01.jpg", "frame_02.jpg"])
        self.assertEqual(self.local, [])                        # the original was never read whole
        self.assertEqual(self.ranged, [FID])
        for c in self.cmds:
            self.assertEqual(c[c.index("-headers") + 1], "Authorization: Bearer T\r\n")
            self.assertLess(c.index("-ss"), c.index("-i"))      # the seek comes before the input: ranged
            self.assertIn(FID, c[c.index("-i") + 1])

    def test_no_ranged_read_means_no_frame_not_a_full_download(self):
        def refused(fid):
            raise SystemExit("no key here")
        with mock.patch.object(SP, "_media_request", refused):
            self.assertEqual(SP.record_frames(self.rec), [])
        self.assertEqual((self.local, self.cmds), ([], []))

    def test_search_never_fetches_and_frame_of_asks_once(self):
        hits = S.search("woman spreads scrub on her forearm", "", "acme", work=self.tmp / "acme",
                        maps=self.tmp / "_maps", collections=["creators"])
        self.assertEqual(hits[0]["clip_id"], FID)
        self.assertIsNone(hits[0]["frame"])
        self.assertEqual((self.local, self.ranged, self.cmds), ([], [], []))   # nothing read during the search
        f = S.frame_of(hits[0])
        self.assertTrue(f and f.endswith("frame_02.jpg"), f)                 # the frame nearest the scene's middle (20 s)
        self.assertEqual((self.local, self.ranged), ([], [FID]))


if __name__ == "__main__":
    unittest.main()
