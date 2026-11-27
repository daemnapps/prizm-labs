"""--stages names where each prompt comes from and which other homes also hold the stage key."""
import io, sys, tempfile, unittest, contextlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C  # noqa: E402


class StagesPrint(unittest.TestCase):
    def test_homes_holding_lists_other_homes_only(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t) / "a", Path(t) / "b"
            a.mkdir(); b.mkdir()
            (a / "stage9x-foo-v1-owner.md").write_text("x")
            (b / "stage9x-foo-v2-owner.md").write_text("x")
            (b / "stage9x-foo-v3-owner.md").write_text("x")
            old = C.PROMPT_HOMES
            C.PROMPT_HOMES = [a, b]
            try:
                got = C.homes_holding("stage9x", a / "stage9x-foo-v1-owner.md")
            finally:
                C.PROMPT_HOMES = old
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0].endswith("stage9x-foo-v3-owner.md"))

    def test_report_prints_from_line_for_every_stage(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            C.report()
        out = buf.getvalue()
        self.assertIn("from: ", out)
        self.assertIn("prompts/", out)


if __name__ == "__main__":
    unittest.main()
