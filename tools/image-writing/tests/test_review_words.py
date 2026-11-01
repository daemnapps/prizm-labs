"""A real customer review's words are fixed: read off the teardown, put on every writing step, checked on the brief."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import review_words as RW  # noqa: E402

TABLE = """| Zone | Position | Visual Content | Text (verbatim) | Type & Treatment |
| :--- | :--- | :--- | :--- | :--- |
| Zone A — photo | top | a man | none | none |
| Zone C — headline | mid | none | The ooohs and ahhhhs | bold |
| Zone D — body | mid | none | I enjoy the compliments / is...lol....thank you. | regular |
"""


def _run(name, block):
    d = Path(tempfile.mkdtemp()) / name
    (d / "assets").mkdir(parents=True)
    (d / "out").mkdir()
    (d / "assets" / "source.json").write_text(json.dumps({"block": block}))
    (d / "out" / "01-teardown.md").write_text("# teardown\n\n" + TABLE)
    return d


class ReviewWords(unittest.TestCase):
    def test_a_review_is_known_and_its_words_read_off_the_teardown(self):
        r = _run("x-batch-review-1", "review-1")
        self.assertTrue(RW.is_review(r))
        self.assertEqual([w for _, w in RW.fixed_words(r)],
                         ["The ooohs and ahhhhs", "I enjoy the compliments / is...lol....thank you."])
        self.assertIn("`The ooohs and ahhhhs`", RW.block(r))

    def test_a_swipe_that_is_not_a_review_gets_nothing(self):
        r = _run("x-batch-penrose-1", "ad-1")
        self.assertFalse(RW.is_review(r))
        self.assertEqual(RW.block(r), "")
        self.assertEqual(RW.problems(r, "anything"), [])

    def test_a_rewritten_review_is_caught_and_the_exact_words_pass(self):
        r = _run("x-batch-review-2", "review-2")
        bad = RW.problems(r, "## DOCUMENT ONE\n`The ooohs and ahhs`\n`I enjoy the compliments is lol thank you.`")
        self.assertEqual(len(bad), 2)
        ok = "## DOCUMENT ONE\n`The ooohs and ahhhhs`\n`I enjoy the compliments`\n`is...lol....thank you.`"
        self.assertEqual(RW.problems(r, ok), [])

    def test_document_three_does_not_count(self):
        r = _run("x-batch-review-3", "review-3")
        brief = "## DOCUMENT ONE\nnew words\n## DOCUMENT THREE\nThe ooohs and ahhhhs I enjoy the compliments is...lol....thank you."
        self.assertEqual(len(RW.problems(r, brief)), 2)


if __name__ == "__main__":
    unittest.main()
