"""A person's yes on a first picture, and nothing downstream changing it (made-up brand; no model)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE.parents[2] / "image-teardown" / "tools"))
import approve_picture as AP  # noqa: E402
import writing as W  # noqa: E402

BRIEF = "# DOCUMENT ONE\n## 3 · The picture\na real photo\n## 4 · The words on the ad\n`HELLO`\n## 6 · Variations\n| 0 | approved | `HELLO` | None |\n| 1 | h | `HI` | None |\n# DOCUMENT TWO\n"


class Approved(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.r = Path(self.t.name)
        (self.r / "runs/image-teardown/acme/run-1/out").mkdir(parents=True)
        (self.r / "p.png").write_bytes(b"x")

    def tearDown(self):
        self.t.cleanup()

    def rec(self, **k):
        return AP.record("run-1", "acme", self.r / "p.png", k.pop("said", "yes"), "thing", ["HELLO"], ["on the note"], root=self.r, **k)

    def test_no_words_from_a_person_is_no_approval(self):
        with self.assertRaises(SystemExit):
            self.rec(said=" ")

    def test_a_real_photo_is_never_changed_and_every_reader_finds_it(self):
        p = self.rec(real=True, in_frame="on the note", swaps=["words | theirs | ours"])
        self.assertEqual(p.parent, self.r / "runs/image-production/acme/prompt-bench")
        sl = json.loads(p.with_suffix(".liked.json").read_text())["brief"]["swap_list"]
        t = " ".join(sl["stays"])
        for x in ("words only", "false proof", "HELLO: on the note", "product stays"):
            self.assertIn(x, t)
        with mock.patch.object(W.P, "REPO", self.r):
            self.assertEqual(W.liked_picture(Path("run-1"), "acme"), p)
            self.assertFalse(W.changes_approved(Path("run-1"), "acme", BRIEF, BRIEF.replace("`HI`", "`HEY`")))
            self.assertTrue(W.changes_approved(Path("run-1"), "acme", BRIEF, BRIEF.replace("a real photo", "a redraw")))
            self.assertTrue(W.changes_approved(Path("run-1"), "acme", BRIEF, BRIEF.replace("`HELLO`", "`BYE`")))
            self.assertFalse(W.changes_approved(Path("run-2"), "acme", BRIEF, BRIEF.replace("`HELLO`", "`BYE`")))

    def test_a_made_picture_keeps_the_runs_own_swaps(self):
        (self.r / "runs/image-teardown/acme/run-1/out/swaps.json").write_text(json.dumps({"swaps": [{"kind": "drawn", "from": "a", "to": "b", "ref": None}], "stays": ["the layout"]}))
        sl = json.loads(self.rec().with_suffix(".recipe.json").read_text())["brief"]["swap_list"]
        self.assertEqual(sl["swaps"][0]["to"], "b")
        self.assertNotIn("false proof", " ".join(sl["stays"]))


if __name__ == "__main__":
    unittest.main()
