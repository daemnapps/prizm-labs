"""take.reread: a cast member set by `voice_id` alone (no `voice` name) is read in that voice and named on the take."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import take as TK  # noqa: E402

VID = "A" * 20


class Reread(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._say = TK.say
        TK.say = lambda vid, words, dest, settings=None: Path(dest).write_bytes(b"read")   # no voice call

    def tearDown(self):
        TK.say = self._say

    def take(self, cast):
        return {"cast": cast, "script": [{"speaker": "HOST", "say": "hi"}]}

    def test_a_voice_id_with_no_voice_name_is_named_by_its_id(self):
        t = TK.reread(self.take({"HOST": {"voice_id": VID}}), self.tmp)
        self.assertEqual(t["voices"], {"HOST": {"name": VID, "voice_id": VID}})
        self.assertTrue(Path(t["script"][0]["read"]).is_file())

    def test_the_voice_name_set_beside_the_id_is_kept(self):
        t = TK.reread(self.take({"HOST": {"voice_id": VID, "voice_name": "host voice"}}), self.tmp)
        self.assertEqual(t["voices"]["HOST"]["name"], "host voice")


if __name__ == "__main__":
    unittest.main()
