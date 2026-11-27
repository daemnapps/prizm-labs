"""A run started with --winner hands that ad's core message to the writing passes (2026-11-25)."""
import importlib.util, sys, unittest
from pathlib import Path
from unittest import mock
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import run as R  # noqa: E402


def wi(tmp):
    sp = importlib.util.spec_from_file_location("wi_t", H.parents[1] / "video-writing/machine/winner_index.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    m.RUNS = tmp
    return m


class T(unittest.TestCase):
    def test_the_message_is_read_as_the_teardown_and_spec_wrote_it(self):
        import tempfile
        t = Path(tempfile.mkdtemp())
        d = t / "r/stages"
        d.mkdir(parents=True)
        (d / "1-teardown.md").write_text("### THE CORE MESSAGE\n*   **Core message:** It reaches.\n*   **Beliefs under it:**\n    *   Hands fail (\"x\")\n"
                                         "*   **Delivery:** A man.\n*   **Angle, not message:** The sink.\n\n> **The audio was measured.**\n\n### VERBATIM TRANSCRIPT\n")
        (d / "2-spec.md").write_text("**6. LOAD-BEARING**\n* **One take:** stays.\n**7. SWAPPABLE**\n* The towel\n")
        (d / "1c-doctrine.md").write_text("**MASS DESIRE:** clear skin\n")
        m = wi(t).message("r")
        self.assertEqual((m["core"], m["beliefs"], m["delivery"], m["angle"]), ("It reaches.", ['Hands fail ("x")'], "A man.", ["The sink."]))
        self.assertEqual((m["load_bearing"], m["swappable"], m["desire"]), (["One take: stays."], ["The towel"], "clear skin"))
        self.assertIn("CORE MESSAGE", wi(t).message_text("r"))

    def test_a_teardown_with_no_core_message_says_nothing(self):
        import tempfile
        self.assertEqual(wi(Path(tempfile.mkdtemp())).message_text("none"), "")

    def test_the_run_reads_it_through_the_one_reader(self):
        self.assertEqual(R.winner_message("no-such-run"), "")


if __name__ == "__main__":
    unittest.main()
