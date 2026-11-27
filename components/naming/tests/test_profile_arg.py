"""--profile becomes the tool's own flags; nothing else about a command changes."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import profile_arg as PA  # noqa: E402


class Expand(unittest.TestCase):
    def test_no_profile_leaves_the_command_as_it_is(self):
        argv = ["--brand", "brand_a", "--avatar", "fed-up-king", "--sub", "x"]
        self.assertEqual(PA.expand(argv), argv)

    def test_a_profile_becomes_the_folders_flags(self):
        out = PA.expand(["--brand", "brand_a", "--profile", "razor-bumps_tried-everything", "--product", "flex"])
        self.assertEqual(out, ["--brand", "brand_a", "--product", "flex", "--avatar", "fed-up-king", "--sub", "ingrown-fighter"])

    def test_the_equals_spelling_works_too(self):
        out = PA.expand(["--profile=razor-bumps_tried-everything", "--brand=brand_a"])
        self.assertIn("ingrown-fighter", out)
        self.assertNotIn("--profile", " ".join(out))

    def test_only_the_flags_the_tool_has_are_added(self):
        out = PA.expand(["--brand", "brand_a", "--profile", "razor-bumps_where-back-of-head_male-35-44-black"], has=("sub", "demographic"))
        self.assertNotIn("--avatar", out)
        self.assertEqual(out[out.index("--sub") + 1], "bald-bumps-guy")
        self.assertEqual(out[out.index("--demographic") + 1], "male-35-44-black")

    def test_a_flag_the_person_typed_wins_over_the_profile(self):
        out = PA.expand(["--brand", "brand_a", "--profile", "razor-bumps_tried-everything", "--sub", "other"])
        self.assertEqual(out.count("--sub"), 1)
        self.assertEqual(out[out.index("--sub") + 1], "other")

    def test_a_profile_needs_a_brand(self):
        with self.assertRaises(SystemExit):
            PA.expand(["--profile", "razor-bumps"])


if __name__ == "__main__":
    unittest.main()
