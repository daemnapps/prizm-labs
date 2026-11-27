"""keywords.py ranks the phrases an avatar repeats around its own desire statement. Fixture workspace only."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
import keywords as K  # noqa: E402


class Desire(unittest.TestCase):
    def test_desire_words_come_from_the_quoted_statement(self):
        self.assertEqual(K.desire_words('Core desire: "I want smooth, soft skin"'), ["smooth", "soft", "skin"])
        self.assertEqual(K.desire_words("no statement here"), [])

    def test_phrases_drop_filler_and_short_single_words(self):
        p = K.phrases("my dry skin is so rough")
        self.assertIn("dry skin", p)
        self.assertNotIn("my", p)


class Ranking(unittest.TestCase):
    def test_a_phrase_said_by_many_rows_and_carrying_the_desire_ranks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "components").mkdir()
            av = root / "brands" / "bx" / "core-avatars" / "av"
            (av / "language").mkdir(parents=True)
            (root / "brands" / "bx" / "products").mkdir()
            (av / "profile.md").write_text('Core desire: "smooth skin"\n')
            rows = [{"text": "my rough skin is awful"}, {"text": "rough skin everywhere"},
                    {"text": "rough skin and dry arms"}, {"text": "I love candles"}]
            (av / "language" / "r.json").write_text(json.dumps({"entries": rows}))
            env = dict(os.environ, AI_WORKSPACE=str(root))
            out = subprocess.run([sys.executable, str(HERE.parent / "machine" / "keywords.py"), "--brand", "bx",
                                  "--avatar", "av", "--json"], env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            got = json.loads(out.stdout)
            self.assertEqual(got["rows"], 4)
            self.assertIn("rough skin", [p for p, n in got["phrases"]])
            self.assertNotIn("candles", " ".join(p for p, n in got["phrases"]))


if __name__ == "__main__":
    unittest.main()
