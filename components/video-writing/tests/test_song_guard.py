"""The swipe's song is never ours (2026-11-20): a copied or style-less song block becomes an instrumental bed."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import writing_v2 as W  # noqa: E402


def brief(song):
    return "# B\n\n```json\n" + json.dumps({"scenes": [{"id": "S1"}], "song": song}) + "\n```\n"


class SongGuard(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "stages").mkdir()
        (self.d / "music").mkdir()
        (self.d / "stages" / "1-transcript.md").write_text("Chestnuts roasting on an open fire.")
        (self.d / "music" / "music.json").write_text(json.dumps({"described": "warm vocal jazz, 74 bpm"}))
        self.out = self.d / "stages" / "5-brief.md"

    def song(self):
        return json.loads(self.out.read_text().split("```json\n")[1].split("\n```")[0])["song"]

    def test_the_swipes_own_lyrics_become_a_bed(self):
        self.out.write_text(brief({"style_id": "acoustic-folk-warm", "sections": [{"lines": ["Chestnuts roasting on an open fire."]}]}))
        W.song_guard("stage5", self.d, self.out)
        self.assertEqual(self.song()["sections"], [])
        self.assertIn("warm vocal jazz", self.song()["bed"])

    def test_an_unfilled_style_becomes_a_bed(self):
        self.out.write_text(brief({"style_id": "[UNFILLED]", "sections": [{"lines": ["our own new line here"]}]}))
        W.song_guard("stage5", self.d, self.out)
        self.assertEqual(self.song()["sections"], [])

    def test_our_own_song_on_a_style_row_is_kept(self):
        text = brief({"style_id": "acoustic-folk-warm", "sections": [{"lines": ["our own new line here"]}]})
        self.out.write_text(text)
        self.assertIsNone(W.song_guard("stage5", self.d, self.out))
        self.assertEqual(self.out.read_text(), text)


if __name__ == "__main__":
    unittest.main()
