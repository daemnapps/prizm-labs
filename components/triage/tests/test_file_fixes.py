"""file_fixes.py files one `change` record per id a card's `- Fixes:` line fully fixes, or refuses with the reason
(ATL-46 (merge files fixes)). Behaviour through the library seam (run(argv)), against a temp deck, a temp data.json and
a temp records dir; file_record.ROOT/PLANE are patched there and is_commit is stubbed, so no git and no real plane."""
import contextlib, io, json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(HERE.parents[2] / "new-workflow-design/builds/atlas/tools"))
import file_fixes, file_record  # noqa: E402
from triage_rederive import active_fixes  # noqa: E402

SHA = "abc1234"
DECK = """# task cards

### TST-1 — fixes a, partly b
- Why: a test card.
- Fixes: a#1; partial: b #2
- Done when: tested.

### TST-2 — names an id the atlas lacks
- Fixes: a#1, a#9

### TST-3 — no fixes line
- Why: nothing to file.

### TST-4 — fixes none
- Fixes: none
"""
ATLAS = {"system": {"flows": [
    {"component": "a", "flow": {"issues": [{"n": 1}, {"n": 2}]}},
    {"component": "b", "flow": {"issues": [{"n": 2}]}},
    {"component": "c"},
    {"component": "d", "flow": {}},
]}}


class FileFixes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.plane = root / "platform/data/records/triage"
        self.plane.mkdir(parents=True)
        self.deck = root / "task-cards.md"
        self.deck.write_text(DECK, encoding="utf-8")
        self.atlas = root / "data.json"
        self.atlas.write_text(json.dumps(ATLAS), encoding="utf-8")
        for p in (mock.patch.object(file_record, "ROOT", root), mock.patch.object(file_record, "PLANE", self.plane),
                  mock.patch.object(file_record, "is_commit", lambda sha: True)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def run_card(self, card, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            paths = file_fixes.run(["--card", card, "--commit", SHA, "--test", "t.py",
                                    "--deck", str(self.deck), "--atlas", str(self.atlas)] + list(extra))
        return paths, out.getvalue(), err.getvalue()

    def written(self):
        return sorted(p.name for p in self.plane.iterdir())

    def refused(self, card):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as c:
            self.run_card(card)
        self.assertIn("refused", str(c.exception))
        self.assertEqual(self.written(), [])
        return str(c.exception)

    def test_full_filed_partial_never(self):
        paths, out, _ = self.run_card("TST-1")
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].endswith("--lead--a-1.json"), paths[0])
        self.assertEqual(self.written(), [Path(paths[0]).name])
        self.assertIn("partial, not filed: b#2", out)
        fixes = active_fixes(self.plane)
        self.assertIn("a#1", fixes)
        self.assertNotIn("b#2", fixes)
        self.assertEqual((fixes["a#1"]["commit"], fixes["a#1"]["test"]), (SHA, "t.py"))
        v = json.loads((self.plane / Path(paths[0]).name).read_text(encoding="utf-8"))["verdict"]
        self.assertEqual((v["act"], v["who"], v["theme"]), ("change", "lead", "components"))
        self.assertEqual(v["why"], f"TST-1 merged at {SHA}")

    def test_unknown_id_refuses_and_writes_nothing(self):
        self.assertIn("a#9", self.refused("TST-2"))

    def test_no_fixes_line_warns_and_writes_nothing(self):
        paths, _, err = self.run_card("TST-3")
        self.assertEqual(paths, [])
        self.assertIn("warning", err)
        self.assertIn("Fixes:", err)
        self.assertEqual(self.written(), [])

    def test_fixes_none_files_nothing_without_warning(self):
        paths, _, err = self.run_card("TST-4")
        self.assertEqual((paths, err), ([], ""))
        self.assertEqual(self.written(), [])

    def test_dry_run_writes_nothing(self):
        paths, out, _ = self.run_card("TST-1", "--dry-run")
        self.assertEqual(paths, [])
        self.assertIn('"act": "change"', out)
        self.assertEqual(self.written(), [])

    def test_card_in_no_deck_refuses(self):
        self.assertIn("TST-99", self.refused("TST-99"))


if __name__ == "__main__":
    unittest.main()
