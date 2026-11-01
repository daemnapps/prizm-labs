#!/usr/bin/env python3
"""No machine-bound literals (SI-62 (research literals), research-gatherer#9).

    python3 components/research-gatherer/test_machine_paths.py

ffmpeg is found on PATH, never one Mac's Homebrew prefix; the declared
test's video-teardown shim check reads the checkout under test, not
~/Projects/workspace; the launchd plist is a template carrying __HOME__.
No key, no network, no ffmpeg needed."""
import os
import plistlib
import shutil
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import research_gatherer.engine as R   # noqa: E402
import research_gatherer.voiceprint as V   # noqa: E402

PLIST = HERE / "schedule" / "com.daemn.language-daily.plist"
TEST_HOME = "/Users/zz-test-home"


class MachinePaths(unittest.TestCase):

    def test_ffmpeg_comes_from_path(self):
        self.assertEqual(V.FFMPEG, shutil.which("ffmpeg") or "ffmpeg")
        src = (HERE / "research_gatherer" / "voiceprint.py").read_text(encoding="utf-8")
        self.assertNotIn('"/opt/homebrew/bin/ffmpeg"', src)

    def test_shim_check_reads_the_checkout_under_test(self):
        src = (HERE / "test_research_gatherer.py").read_text(encoding="utf-8")
        self.assertIn("ws = R.WORKSPACE", src)
        self.assertNotIn('Path.home() / "Projects" / "workspace"', src)

    @unittest.skipIf(os.environ.get("AI_WORKSPACE"), "AI_WORKSPACE names the workspace")
    def test_engine_workspace_is_this_checkout(self):
        self.assertEqual((R.WORKSPACE / "components" / "research-gatherer").resolve(), HERE)

    def test_plist_is_a_template(self):
        text = PLIST.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", text)
        self.assertGreaterEqual(text.count("__HOME__"), 3)
        p = plistlib.loads(text.replace("__HOME__", TEST_HOME).encode("utf-8"))
        self.assertEqual(p["Label"], "com.daemn.language-daily")
        self.assertEqual(p["ProgramArguments"], [TEST_HOME + "/.local/bin/daemn-language-daily.sh"])
        for key in ("StandardOutPath", "StandardErrorPath"):
            self.assertTrue(p[key].startswith(TEST_HOME + "/Library/Logs/daemn/"), p[key])
        self.assertEqual(p["StartCalendarInterval"], {"Hour": 5, "Minute": 30})


if __name__ == "__main__":
    print("python", sys.version_info[:3])
    unittest.main()
