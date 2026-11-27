"""gather.py person: searches come from what is missing, a pull needs a cap and the owner's words, lines keep their link."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_gatherer import engine, person as P  # noqa: E402


class Person(unittest.TestCase):
    PLAN = {"reddit": {"rooms": ["a", "b"], "searches": ["heel pain mile two"]}, "youtube": {"searches": ["x"]}, "tiktok": {"searches": ["y"]}}

    def test_never_past_the_cap_and_one_dead_platform_does_not_stop_the_rest(self):
        spent = []

        def run(actor, payload, dollars):
            spent.append(dollars)
            if actor == P.ACTORS["yt_search"]:
                raise RuntimeError("down")
            if actor == P.ACTORS["reddit"]:
                return [{"dataType": "comment", "id": "t1_c", "parsedPostId": "p", "url": "https://www.reddit.com/r/a/comments/p/", "body": "my heel barks at mile two every run", "subredditName": "a", "commentUpVotes": 3}]
            if actor == P.ACTORS["tt_search"]:
                return [{"webVideoUrl": "https://www.tiktok.com/@x/video/1"}]
            return [{"text": "same here my heel is gone", "videoWebUrl": "https://www.tiktok.com/@x/video/1", "diggCount": 2}]
        lines, notes = P.pull(self.PLAN, 1.9, run=run)
        self.assertLessEqual(sum(spent), 1.9)
        self.assertTrue(any("youtube" in n for n in notes))
        self.assertEqual({x["src"] for x in lines}, {"reddit r/a", "tiktok comment"})
        self.assertIn("/comments/p/comment/c/", lines[0]["url"])
        few, notes = P.pull(self.PLAN, 0.3, run=run)
        self.assertTrue(any("cap is reached" in n for n in notes))

    def test_a_line_is_filed_once_with_its_link_under_runs(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.object(engine, "WORKSPACE", Path(t)):
            rows = [P.line("my heel barks", "reddit r/a", "https://u/1")]
            P.file_rows("acme", "sore-foot", "runner", rows)
            f, n = P.file_rows("acme", "sore-foot", "runner", rows)
            self.assertEqual(n, 1)
            self.assertIn("runs", f.parts)
            self.assertEqual(json.loads(f.read_text())["entries"][0]["source"]["ref"], "https://u/1")

    def test_a_pull_without_the_owners_words_is_refused(self):
        with mock.patch.object(P, "who") as w:
            w.return_value.resolve.return_value = ("runner", None, None, [])
            w.return_value.N.canon.return_value = ("sore-foot", "runner")
            with self.assertRaises(SystemExit):
                P.main(["--brand", "acme", "--avatar", "sore-foot", "--sub", "runner", "--pull", "--cap", "2"])


if __name__ == "__main__":
    unittest.main()
