#!/usr/bin/env python3
"""PF-2d (overlay remembers settings), part 2: `features.py sync-overlay <page>`
rewrites a page's overlay block, the <script id="ov-main"> inside the
component-owned overlay markers, from components/page-features/overlay.js
byte for byte, and touches nothing else; a page with no recognisable overlay
block is refused (exit 2, named) and left as it was.

    python3 test_pf2d_overlay_sync.py

unittest, stdlib only, no network, never runs git. Every fixture page is a
string in this file, written to a temporary folder; no page under
platform/views/viewers/ is read or written. Runs under /usr/bin/python3 (3.9).
"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import features  # noqa: E402
import live  # noqa: E402

FEATURES_PY = os.path.join(HERE, "features.py")
with open(os.path.join(HERE, "overlay.js"), "rb") as _handle:
    OVERLAY = _handle.read()

START, END = live.OVERLAY_START.encode(), live.OVERLAY_END.encode()
OPEN, CLOSE = b'<script id="ov-main">', b"</script>"
# The bytes before the overlay body, and after it: CRLF and LF lines, non-ASCII
# text, a page script that is not the overlay, the ov-style and ov-prefs
# blocks inside the markers (kept), and an ov-main-looking id outside them.
HEAD = ("<!doctype html>\r\n<html><head><meta charset=\"utf-8\"><title>Fixture · café</title></head>\r\n"
        "<body>\n<main data-feature=\"4\">Run id — ✓</main>\n"
        "<script id=\"pg-main\">var x = \"<script id='ov-main'>\";</script>\n"
        "<script type=\"application/json\" id=\"fo-features\">{\"features\": []}</script>\n").encode("utf-8") + START + (
        "\n<style id=\"ov-style\">#fo-layer{position:fixed}</style>\r\n"
        "<script id=\"ov-prefs\">window.__foPrefs = {apply: function () {}};</script>\n").encode("utf-8") + OPEN
OLD_BODY = b"/* PLAN's prototype overlay, old copy */\n(function () { var PFKEY = 'pf-prefs:' + location.pathname; })();\n"
TAIL = CLOSE + b"\n" + END + "\n<p>after the overlay · ünïcode</p>\r\n</body></html>\n".encode("utf-8")
PAGE = HEAD + OLD_BODY + TAIL


def run(*args):
    proc = subprocess.run([sys.executable, FEATURES_PY] + list(args), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    return proc.returncode, proc.stdout + proc.stderr


class SyncOverlay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.page = os.path.join(self.tmp.name, "fixture.html")

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, data):
        with open(self.page, "wb") as handle:
            handle.write(data)

    def got(self):
        with open(self.page, "rb") as handle:
            return handle.read()

    def test_component_has_no_script_close(self):
        self.assertNotIn(b"</script", OVERLAY.lower(), "overlay.js must be inlinable")
        self.assertIn("sync-overlay", features.SUBCOMMANDS)
        self.assertIn("features.py sync-overlay <page>", features.USAGE)

    def test_replaces_block_byte_for_byte_and_nothing_else(self):
        self.put(PAGE)
        code, out = run("sync-overlay", self.page)
        self.assertEqual(code, 0, out)
        self.assertIn("synced", out)
        new = self.got()
        self.assertEqual(new, HEAD + OVERLAY + TAIL)
        self.assertTrue(new.startswith(HEAD) and new.endswith(TAIL))
        self.assertEqual(new[len(HEAD):len(new) - len(TAIL)], OVERLAY)
        self.assertNotIn(OLD_BODY, new)
        self.assertIn(b"\r\n", new)  # line endings outside the block kept as they were

    def test_second_run_is_unchanged(self):
        self.put(PAGE)
        self.assertEqual(run("sync-overlay", self.page)[0], 0)
        once = self.got()
        code, out = run("sync-overlay", self.page)
        self.assertEqual(code, 0, out)
        self.assertIn("unchanged", out)
        self.assertEqual(self.got(), once)

    def refused(self, data, why):
        self.put(data)
        code, out = run("sync-overlay", self.page)
        self.assertEqual(code, 2, out)
        self.assertIn("no recognisable overlay block", out)
        self.assertIn(why, out)
        self.assertIn(self.page, out)
        self.assertEqual(self.got(), data, "a refused page is left byte for byte")

    def test_refuses_page_without_markers(self):
        self.refused(PAGE.replace(START, b"").replace(END, b""), "no overlay markers")

    def test_refuses_markers_without_ov_main(self):
        self.refused(PAGE.replace(OPEN, b"<script id=\"ov-other\">"), "0 <script id=\"ov-main\"> blocks")

    def test_ov_main_outside_markers_does_not_count(self):
        outside = PAGE.replace(OPEN, b"<script id=\"ov-other\">") + OPEN + b"var y;" + CLOSE
        self.refused(outside, "0 <script id=\"ov-main\"> blocks")

    def test_refuses_two_ov_main_blocks(self):
        two = PAGE.replace(START, START + b"\n" + OPEN + b"var z;" + CLOSE)
        self.refused(two, "2 <script id=\"ov-main\"> blocks")

    def test_refuses_markers_not_one_pair(self):
        self.refused(PAGE + START, "not one pair")

    def test_unreadable_and_usage(self):
        code, out = run("sync-overlay", os.path.join(self.tmp.name, "missing.html"))
        self.assertEqual(code, 3, out)
        self.assertIn("UNREADABLE", out)
        self.assertEqual(run("sync-overlay")[0], 2)
        self.assertEqual(run("sync-overlay", "a.html", "b.html")[0], 2)


if __name__ == "__main__":
    unittest.main()
