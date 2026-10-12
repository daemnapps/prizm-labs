"""The teardown starts the playbook builder right after triage names a format
(the owner, 2026-10-10: workflows built from the videos that come in). The hook only
starts a background process; it never blocks or raises."""
import sys, tempfile, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as R


class PlaybookHook(unittest.TestCase):
    def test_starts_the_builder_on_the_run_when_a_format_is_named(self):
        d = Path(tempfile.mkdtemp())
        with mock.patch.object(R.subprocess, "Popen") as P:
            R.playbook_hook(d, "song-ad")
        args = P.call_args[0][0]
        self.assertEqual(args[0], sys.executable)
        self.assertTrue(args[1].endswith("video-production/machine/playbook_builder.py"))
        self.assertEqual(args[2], str(d))

    def test_no_format_no_builder(self):
        with mock.patch.object(R.subprocess, "Popen") as P:
            self.assertIsNone(R.playbook_hook(Path(tempfile.mkdtemp()), None))
        P.assert_not_called()

    def test_a_failure_to_start_never_raises(self):
        with mock.patch.object(R.subprocess, "Popen", side_effect=OSError("nope")):
            self.assertIsNone(R.playbook_hook(Path(tempfile.mkdtemp()), "song-ad"))

    def test_the_hook_runs_right_after_triage_names_the_format(self):
        src = Path(R.__file__).read_text()
        self.assertLess(src.index("style_format_from_triage((d / out_name)"), src.index('playbook_hook(d, sf.get("format_id"))'))


if __name__ == "__main__":
    unittest.main()
