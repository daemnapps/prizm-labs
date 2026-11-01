#!/usr/bin/env python3
"""LD-21 (no mini picture-making): run_month asks design/line.py to MAKE
pictures (`--pictures`) only when the build's own picture test passes —
`not NO_IMAGES and have_picture_key()` — so the mini's words-only door never
sends the design step to the image engine with no key.

    python3 test_ld21_design_pictures.py

Offline: run_month's subprocess.run is replaced by a fake that records every
argv, and have_picture_key is stubbed. Everything lands in a temp workspace.
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="ld21-design-pictures-")).resolve()
os.environ["AI_WORKSPACE"] = str(TMP)            # before anything imports paths.py

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_month as M                              # noqa: E402

BRAND = "testbrand"
LABEL = "ld21-send"


def setUpModule():
    # a brand with a look file is designed (run_month: DESIGN and design-system.json)
    look = TMP / "brands" / BRAND / "email-sms" / "design-system.json"
    look.parent.mkdir(parents=True, exist_ok=True)
    look.write_text("{}")


def one_email(no_images, key):
    """One email through one_run with the design line on; returns (the build's
    argv, the design step's argv, the log)."""
    seen = []

    def run(argv, **kw):
        seen.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "ok\n", "")

    logf = io.StringIO()
    with mock.patch.object(M.subprocess, "run", run), \
            mock.patch.object(M, "have_picture_key", lambda: key), \
            mock.patch.object(M, "NO_IMAGES", no_images), \
            mock.patch.object(M, "DESIGN", True), \
            mock.patch.object(M, "PUSH", False), \
            mock.patch("sys.stdout", io.StringIO()):
        label, status, _, _ = M.one_run(LABEL, ["python3", "email_line.py", LABEL], BRAND, logf)
    assert (label, status) == (LABEL, "done"), (label, status)
    build = [a for a in seen if len(a) > 1 and a[1] == "simple_email.py"]
    design = [a for a in seen if len(a) > 1 and a[1] == "design/line.py"]
    assert len(build) == 1 and len(design) == 1, seen
    return build[0], design[0], logf.getvalue()


class DesignPicturesOnlyWhenAllowed(unittest.TestCase):
    def test_words_only_run_never_asks_for_pictures(self):
        _, design, log = one_email(no_images=True, key=True)
        self.assertNotIn("--pictures", design)
        self.assertEqual(design[2:4], [BRAND, "--run"])
        self.assertIn("no pictures made (slots left todo): words-only run", log)

    def test_pictures_allowed_with_a_key(self):
        _, design, log = one_email(no_images=False, key=True)
        self.assertIn("--pictures", design)
        self.assertIn("pictures asked of the image engine", log)
        self.assertNotIn("no pictures made", log)

    def test_no_key_never_asks_for_pictures(self):
        _, design, log = one_email(no_images=False, key=False)
        self.assertNotIn("--pictures", design)
        self.assertIn("no pictures made (slots left todo): no OPENAI_API_KEY on this machine", log)

    def test_build_and_design_agree(self):
        # the Klaviyo build's --no-images and the design's --pictures come from the one test
        for no_images, key in ((True, True), (False, True), (False, False), (True, False)):
            build, design, _ = one_email(no_images, key)
            self.assertNotEqual("--no-images" in build, "--pictures" in design, (no_images, key))


if __name__ == "__main__":
    unittest.main()
