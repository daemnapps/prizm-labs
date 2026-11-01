"""SI-124 (audio-teardown honest) — the four known bugs, the Gemini request out of
system temp, and the workspace found through run-kit. No network, no key, no spend.
    python3 -m unittest tests/test_honest.py"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import gemini as G  # noqa: E402
import run as R  # noqa: E402
import split as SPL  # noqa: E402
import voices as V  # noqa: E402
import words as W  # noqa: E402

SCRIBE = {"model": "scribe_v2", "language": "eng",
          "words": [{"text": "So", "start": 0.3, "end": 0.5, "speaker": "s0", "type": "word"},
                    {"text": "good", "start": 0.5, "end": 0.9, "speaker": "s0", "type": "word"}]}


def touch_last(*args):
    """Stands in for ffmpeg: writes its output file (the last argument)."""
    Path(args[-1]).write_bytes(b"x")


class Words(unittest.TestCase):
    """(1) A non-list reply raises, so run.py falls back to Scribe's words."""

    def test_non_list_reply_raises(self):
        with unittest.mock.patch.object(G, "ask", return_value=({"lines": []}, "gemini-x", [])):
            with self.assertRaises(RuntimeError):
                W.listen("voices.mp3")

    def test_teardown_falls_back_to_scribe(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            tracks = {"voices": d / "v.mp3", "music": None, "mix": d / "v.mp3", "how": "mix", "why": "Demucs is not installed"}
            with unittest.mock.patch.object(R.SPL, "split", return_value=tracks), \
                    unittest.mock.patch.object(R.SPL, "duration", return_value=2.0), \
                    unittest.mock.patch.object(G, "ask", return_value=({"lines": []}, "gemini-x", [])), \
                    unittest.mock.patch.object(R.SP, "listen", return_value=SCRIBE), \
                    unittest.mock.patch.object(R.V, "cards", return_value=[]), \
                    unittest.mock.patch.object(R, "add_sound", side_effect=lambda v, o, t, t0: json.loads((o / "sound-sheet.json").read_text())):
                sheet = R.teardown(d / "in.mp4", d / "out")
            lines = json.loads((d / "out" / "transcript.json").read_text())
        self.assertEqual([l["text"] for l in lines], ["So good"])
        self.assertIn("scribe-only", lines[0]["flags"])
        self.assertIsNone(sheet["words"]["model"])
        self.assertIn("not a list", sheet["words"]["error"])


class Split(unittest.TestCase):
    """(2) Tracks already in --out are reused only when they came from this video."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.video, self.out = d / "in.mp4", d / "audio"
        self.video.write_bytes(b"one video")
        self.demucs = d / "demucs-python"
        self.demucs.write_text("")
        self.calls = []

        def fake_demucs(argv, **kw):
            self.calls.append(argv)
            sep = Path(argv[argv.index("-o") + 1]) / "htdemucs" / "stereo"
            sep.mkdir(parents=True, exist_ok=True)
            (sep / "vocals.wav").write_bytes(b"v")
            (sep / "no_vocals.wav").write_bytes(b"n")
            return subprocess.CompletedProcess(argv, 0, "", "")

        self.patches = [unittest.mock.patch.object(SPL, "_ff", side_effect=touch_last),
                        unittest.mock.patch.object(SPL, "DEMUCS", self.demucs),
                        unittest.mock.patch.object(SPL.subprocess, "run", side_effect=fake_demucs)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_tracks_from_another_video_are_split_again(self):
        self.out.mkdir()
        (self.out / "voices.mp3").write_bytes(b"old")
        (self.out / "music.mp3").write_bytes(b"old")
        r = SPL.split(self.video, self.out)
        self.assertEqual(r["why"], "voices lifted off the music")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(json.loads((self.out / SPL.STAMP).read_text())["video"], str(self.video.resolve()))

    def test_same_video_reused_changed_video_split_again(self):
        SPL.split(self.video, self.out)
        self.assertEqual(SPL.split(self.video, self.out)["why"], "already split")
        self.assertEqual(len(self.calls), 1)
        self.video.write_bytes(b"another, longer video")
        self.assertEqual(SPL.split(self.video, self.out)["why"], "voices lifted off the music")
        self.assertEqual(len(self.calls), 2)

    def test_no_demucs_is_never_already_split(self):
        self.out.mkdir()
        (self.out / "voices.mp3").write_bytes(b"old")
        (self.out / "music.mp3").write_bytes(b"old")
        with unittest.mock.patch.object(SPL, "DEMUCS", Path(self.tmp.name) / "missing"):
            r = SPL.split(self.video, self.out)
        self.assertEqual((r["how"], r["music"]), ("mix", None))


class VoiceCards(unittest.TestCase):
    """(3) voice-cards.json is always written; music.mp3 stays optional and the sheet says why."""

    def test_no_lines_still_writes_cards_and_says_why_no_music(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            tracks = {"voices": d / "m.mp3", "music": None, "mix": d / "m.mp3", "how": "mix", "why": "Demucs is not installed"}
            with unittest.mock.patch.object(R.SPL, "split", return_value=tracks), \
                    unittest.mock.patch.object(R.SPL, "duration", return_value=2.0), \
                    unittest.mock.patch.object(R.W, "listen", return_value={"model": "gemini-x", "prompt": "p", "lines": [], "tried": []}), \
                    unittest.mock.patch.object(R.SP, "listen", return_value=dict(SCRIBE, words=[])), \
                    unittest.mock.patch.object(R, "add_sound", side_effect=lambda v, o, t, t0: json.loads((o / "sound-sheet.json").read_text())):
                sheet = R.teardown(d / "in.mp4", d / "out")
            vc = json.loads((d / "out" / "voices" / "voice-cards.json").read_text())
        self.assertEqual(vc["cards"], [])
        self.assertEqual(sheet["split"]["how"], "mix")
        self.assertEqual(sheet["split"]["music"], "not written — Demucs is not installed")


class Doctrine(unittest.TestCase):
    """(4) An unreadable doctrine is flagged on the card, never skipped silently."""

    def test_unreadable_doctrine_flagged_on_card(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            lines = [{"speaker": "Speaker 1", "start": 0.0, "end": 1.0, "text": "So good", "language": "en"}]
            with unittest.mock.patch.object(V, "repo", return_value=d), \
                    unittest.mock.patch.object(V, "cut", return_value=(None, 0.0)):
                cards = V.cards(lines, d / "v.mp3", d / "voices", 1.0)
                styles, why = V.delivery_styles()
            on_disk = json.loads((d / "voices" / "voice-cards.json").read_text())["cards"]
        self.assertEqual(styles, [])
        self.assertTrue(why.startswith("doctrine unreadable"))
        self.assertTrue(cards[0]["doctrine_unreadable"].startswith("doctrine unreadable"))
        self.assertEqual(on_disk[0]["doctrine_unreadable"], cards[0]["doctrine_unreadable"])
        self.assertIn("Delivery style not checked", V.render(cards))

    def test_readable_doctrine_not_flagged(self):
        styles, why = V.delivery_styles()
        self.assertIsNone(why)
        self.assertTrue(styles)


class GeminiRequest(unittest.TestCase):
    """#13: the request body goes to curl on stdin — nothing is left in system temp."""

    def test_ask_creates_nothing_in_temp(self):
        reply = json.dumps({"candidates": [{"content": {"parts": [{"text": "[]"}]}}]})
        seen = {}

        def fake_curl(argv, **kw):
            seen["argv"], seen["input"] = argv, kw.get("input")
            seen["during"] = os.listdir(tempfile.gettempdir())     # while curl runs, not only after
            return subprocess.CompletedProcess(argv, 0, reply, "")

        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tmp:
            audio = Path(src) / "clip.mp3"
            audio.write_bytes(b"\x00\x01")
            with unittest.mock.patch.object(tempfile, "tempdir", tmp), \
                    unittest.mock.patch.object(G, "key", return_value="k"), \
                    unittest.mock.patch.object(G.subprocess, "run", side_effect=fake_curl):
                self.assertEqual(tempfile.gettempdir(), tmp)
                rows, model, tried = G.ask(audio, "listen")
                left = os.listdir(tmp)
        self.assertEqual((seen["during"], left), ([], []))
        self.assertEqual((rows, model, tried), ([], G.MODELS[0][0], []))
        self.assertIn("@-", seen["argv"])
        self.assertEqual(json.loads(seen["input"])["contents"][0]["parts"][1]["text"], "listen")


class Workspace(unittest.TestCase):
    """#23: voices.py finds the workspace through run-kit, not a walk of its own."""

    def test_no_hand_rolled_walk(self):
        src = (HERE / "voices.py").read_text()
        self.assertNotIn(".git", src)
        self.assertIsNone(re.search(r"\.parents\b", src))         # mkdir(parents=True) is not a walk
        self.assertIn("from run_kit.paths import repo", src)


if __name__ == "__main__":
    unittest.main()
