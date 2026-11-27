#!/usr/bin/env python3
"""The hand read of a brief is a role's (owner ruling, 2026-11-18: brief approval sits with the creative strategist
role; the owner steps in on a trip-wire). The stamp's shape, and that an edit after the read needs the read again,
are as they were; the 2026-09-24 rule named the owner as the reader, this replaces who reads.

    /usr/bin/python3 components/video-writing/tests/test_brief_read_role.py
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

COMP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMP / "machine"))
import swipe_match as SM   # noqa: E402


class TheHandReadOfABriefIsARoles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)
        (self.run / "stages").mkdir()
        self.brief = self.run / "stages" / "5-brief.md"
        self.brief.write_text("# The brief\n\nA scene at chest height.\n")

    def test_the_read_is_stamped_as_the_creative_strategists_and_an_edit_needs_it_again(self):
        SM.approve_read(self.brief)
        text = self.brief.read_text()
        self.assertIn("<!-- brief-read: APPROVED by the creative strategist ", text)
        self.assertEqual(SM.read_of(text), "APPROVED")
        self.assertEqual(SM.read_of(text.replace("chest height", "waist height")), "STALE")

    def test_the_command_takes_the_roles_name_and_the_older_name_still_works(self):
        tool = COMP / "machine" / "swipe_match.py"
        for flag in ("--strategist-read", "--owner-read"):
            self.brief.write_text("# The brief\n\nA scene at chest height.\n")
            r = subprocess.run([sys.executable, str(tool), str(self.run), "--brief", "5-brief.md", flag],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertIn("approved by the creative strategist", r.stdout)
            self.assertEqual(SM.read_of(self.brief.read_text()), "APPROVED")


if __name__ == "__main__":
    unittest.main()
