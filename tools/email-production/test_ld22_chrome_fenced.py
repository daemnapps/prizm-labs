#!/usr/bin/env python3
"""LD-22 (Chrome in fenced runs): design/build.py's slices() gives headless
Chrome its own profile folder under the build's temp folder, retries ONCE
with --no-sandbox when no picture comes, and raises a RuntimeError naming
Chrome's stderr when the retry makes none either — never a bare
FileNotFoundError.

    python3 test_ld22_chrome_fenced.py

Offline: build's subprocess.run is replaced by a fake that records every argv
and writes (or not) the screenshot; the picture reader and the page's look
are stubbed, so no Chrome, no brand and no PIL are needed.
"""
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
try:
    import PIL  # noqa: F401
except ImportError:                                  # build.py and engine.py import PIL at the top; nothing here draws
    _pil = types.ModuleType("PIL")
    for _n in ("Image", "ImageDraw", "ImageFilter"):
        setattr(_pil, _n, types.ModuleType("PIL." + _n))
        sys.modules["PIL." + _n] = getattr(_pil, _n)
    sys.modules["PIL"] = _pil
sys.path.insert(0, str(HERE / "design"))
import build as B                                    # noqa: E402

SECS = 2
BAND, BAR = 4, 2                                     # a fake 3x picture: two sections, each followed by a magenta bar


class FakeImage:
    def __init__(self):
        self.size = (B.CSS_W * B.SCALE, SECS * (BAND + BAR))

    def convert(self, mode):
        return self

    def load(self):
        return self

    def __getitem__(self, xy):
        return B.MAGENTA if xy[1] % (BAND + BAR) >= BAND else (0, 0, 0)

    def crop(self, box):
        return ("crop", box)


def opener(path):
    assert Path(path).stat().st_size > 0, path
    return FakeImage()


class Lk:
    def tokens(self, theme):
        return {"canvas": "#fff"}


def run_slices(writes, stderr=b""):
    """slices() over SECS sections; writes[i] says whether Chrome's i-th call makes
    the picture. Returns (every argv, the result or the exception, tmp, stdout)."""
    seen = []

    def run(argv, **kw):
        seen.append(list(argv))
        if writes[len(seen) - 1]:
            shot = [a for a in argv if a.startswith("--screenshot=")][0].split("=", 1)[1]
            Path(shot).write_bytes(b"\x89PNG fake")
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=stderr)

    out = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp, \
            mock.patch.object(B.subprocess, "run", run), \
            mock.patch.object(B, "Image", types.SimpleNamespace(open=opener)), \
            mock.patch.object(B.EN, "fonts", lambda lk: ""), \
            mock.patch.object(B.EN, "css", lambda lk, th: ""), \
            mock.patch.object(B.EN, "root_classes", lambda lk: ""), \
            mock.patch("sys.stdout", out):
        try:
            got = B.slices({"label": "ld22-send"}, Lk(), [(None, "<p>%d</p>" % i) for i in range(SECS)], tmp)
        except Exception as e:                       # noqa: BLE001  (the test names which one it expects)
            got = e
        return seen, got, Path(tmp).resolve(), out.getvalue()


def flag(argv, name):
    return [a.split("=", 1)[1] for a in argv if a.startswith(name + "=")]


class ChromeInFencedRuns(unittest.TestCase):
    def test_first_call_has_its_own_profile_and_its_sandbox(self):
        seen, got, tmp, out = run_slices([True])
        self.assertEqual(len(seen), 1, seen)                # a run that renders the first time is unchanged: one call
        first = seen[0]
        self.assertEqual(first[0], B.CHROME)
        profile = flag(first, "--user-data-dir")
        self.assertEqual(len(profile), 1, first)
        self.assertEqual(Path(profile[0]).resolve(), tmp / "chrome-profile")
        self.assertNotIn("--no-sandbox", first)
        self.assertTrue(first[-1].startswith("file://"), first)
        self.assertNotIn("no-sandbox", out)
        self.assertEqual(len(got), SECS, got)

    def test_no_picture_then_one_retry_without_the_sandbox(self):
        seen, got, tmp, out = run_slices([False, True])
        self.assertEqual(len(seen), 2, seen)
        self.assertNotIn("--no-sandbox", seen[0])
        self.assertIn("--no-sandbox", seen[1])
        self.assertEqual(Path(flag(seen[1], "--user-data-dir")[0]).resolve(), tmp / "chrome-profile")
        self.assertEqual(flag(seen[0], "--screenshot"), flag(seen[1], "--screenshot"))
        self.assertTrue(seen[1][-1].startswith("file://"), seen[1])
        self.assertEqual(len([ln for ln in out.splitlines() if "--no-sandbox" in ln]), 1, out)   # one line says so
        self.assertIsInstance(got, list, got)                # slices() goes on
        self.assertEqual(got, [("crop", (0, 0, B.CSS_W * B.SCALE, BAND)),
                               ("crop", (0, BAND + BAR, B.CSS_W * B.SCALE, 2 * BAND + BAR))])

    def test_never_a_picture_is_a_runtime_error_with_chromes_stderr(self):
        err = (b"[1:2:ERROR] early noise\n[3:4:ERROR] first of the last three\n"
               b"sandbox initialization failed: Operation not permitted\n[5:6:ERROR] last line\n")
        seen, got, _, _ = run_slices([False, False], stderr=err)
        self.assertEqual(len(seen), 2, seen)                 # exactly one retry, never more
        self.assertIn("--no-sandbox", seen[1])
        self.assertIsInstance(got, RuntimeError, repr(got))
        self.assertNotIsInstance(got, FileNotFoundError)
        msg = str(got)
        self.assertIn("first of the last three", msg)
        self.assertIn("sandbox initialization failed: Operation not permitted", msg)
        self.assertIn("last line", msg)
        self.assertNotIn("early noise", msg)                 # the last 3 lines, not the whole stderr

    def test_an_empty_picture_counts_as_none(self):
        seen = []

        def run(argv, **kw):
            seen.append(list(argv))
            shot = flag(argv, "--screenshot")[0]
            Path(shot).write_bytes(b"" if len(seen) == 1 else b"\x89PNG fake")
            return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(B.subprocess, "run", run), \
                mock.patch("sys.stdout", io.StringIO()):
            B.screenshot(Path(tmp) / "page.html", Path(tmp) / "shot.png", tmp, 1000)
        self.assertEqual(len(seen), 2, seen)
        self.assertIn("--no-sandbox", seen[1])


if __name__ == "__main__":
    unittest.main()
