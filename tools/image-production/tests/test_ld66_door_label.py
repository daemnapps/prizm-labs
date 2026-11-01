#!/usr/bin/env python3
"""LD-66 (image door label) — the image-production mini door hands the run
label to make.py, so each run gets its own Drive folder instead of the UTC date.

  (a) door     — lab_door.command over this component's lab_door.json puts
                 `--label <label>` on make.py's argv.
  (b) parser   — make.py's parser carries --label onto the request.
  (c) filing   — filing.label_for returns the request's label; the UTC date
                 only when the request has none.

OFFLINE: stdlib unittest, temp dirs only, no network, no key.

Run: python3 tools/image-production/tests/test_ld66_door_label.py
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.append(str(REPO / "components" / "run-kit"))         # APPEND, never insert at 0
sys.path.append(str(REPO / "tools" / "image-production"))

from run_kit import lab_door                                  # noqa: E402
import make                                                   # noqa: E402
from image_production import filing                           # noqa: E402

MANIFEST = REPO / "tools" / "image-production" / "lab_door.json"


class DoorLabel(unittest.TestCase):

    def test_door_argv_carries_the_label(self):
        m = lab_door.load(MANIFEST)
        with tempfile.TemporaryDirectory() as tmp:
            argv = lab_door.command(
                m, {"purpose": "email-story", "direction": "a test", "label": "run-a"},
                REPO, "brand-a", Path(tmp) / "run-a", None)
        self.assertIn("--label", argv)
        self.assertEqual(argv[argv.index("--label") + 1], "run-a")

    def test_parser_puts_the_label_on_the_request(self):
        a = make.build_parser().parse_args(
            ["--brand", "brand-a", "--purpose", "email-story", "--direction", "x",
             "--label", "run-a"])
        self.assertEqual(make.request_from(a)["label"], "run-a")

    def test_filing_names_the_folder_by_the_label(self):
        self.assertEqual(filing.label_for({"label": "run-a"}), "run-a")

    def test_filing_falls_back_to_the_date_without_a_label(self):
        self.assertRegex(filing.label_for({}), re.compile(r"^\d{4}-\d{2}-\d{2}$"))


if __name__ == "__main__":
    unittest.main()
