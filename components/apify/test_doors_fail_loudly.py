#!/usr/bin/env python3
"""SI-150 (apify fails loudly): a failed door writes its artifacts and exits
non-zero, reddit.json is always valid JSON, 'r/' is stripped as a prefix, and
a partial download is never cached.

Offline: apify.run, apify._call and urllib.request.urlopen are stubbed, the
token is a fake from the environment, every out dir is a temp dir. No package
here, so the doors are loaded by path.

    /usr/bin/python3 components/apify/test_doors_fail_loudly.py
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# THIS folder's apify.py, registered first so reddit.py and tiktok.py import it
# (and never a re-export elsewhere on sys.path).
A = _load("apify", HERE / "apify.py")
R = _load("si150_reddit", HERE / "reddit.py")
T = _load("si150_tiktok", HERE / "tiktok.py")


def _no_network(*a, **k):
    raise AssertionError("network touched in an offline test")


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="si150-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        p = mock.patch.object(urllib.request, "urlopen", _no_network)
        p.start()
        self.addCleanup(p.stop)

    def main(self, mod, argv):
        """Run a door's main(); return its exit code (0 when it returns)."""
        with mock.patch.object(sys, "argv", argv):
            try:
                mod.main()
            except SystemExit as e:
                return 0 if e.code is None else (e.code if isinstance(e.code, int) else 1)
        return 0


class RedditFailsLoudly(_Base):
    def test_1_no_token_writes_md_and_empty_json_then_exits_1(self):
        out = self.tmp / "out"
        out.mkdir()
        (out / "reddit.json").write_text('[{"title": "an older pull"}]')
        env = {k: v for k, v in os.environ.items() if not k.startswith("APIFY_TOKEN")}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(A, "_vault", lambda name: None), \
             mock.patch.object(A, "_call", _no_network):
            code = self.main(R, ["reddit.py", "--out", str(out), "--queries", "q"])
        self.assertEqual(code, 1)
        md = (out / "reddit.md").read_text()
        self.assertIn("UNFILLED", md)
        self.assertIn("APIFY_TOKEN", md)
        self.assertEqual(json.loads((out / "reddit.json").read_text()), [])

    def test_1b_any_other_failure_also_writes_both_and_exits_1(self):
        out = self.tmp / "out"

        def boom(*a, **k):
            raise urllib.error.URLError("refused")
        with mock.patch.object(R.apify, "run", boom):
            code = self.main(R, ["reddit.py", "--out", str(out), "--queries", "q"])
        self.assertEqual(code, 1)
        self.assertIn("refused", (out / "reddit.md").read_text())
        self.assertEqual(json.loads((out / "reddit.json").read_text()), [])

    def test_2_rows_over_the_cap_still_dump_valid_json(self):
        out = self.tmp / "out"
        rows = [{"title": f"post {i}", "body": "x" * 500, "url": f"https://r/{i}"} for i in range(40)]
        with mock.patch.object(R.apify, "run", lambda *a, **k: rows), \
             mock.patch.object(R, "JSON_CAP", 5_000):
            code = self.main(R, ["reddit.py", "--out", str(out), "--queries", "q"])
        self.assertEqual(code, 0)
        text = (out / "reddit.json").read_text()
        self.assertLessEqual(len(text), 5_000)
        kept = json.loads(text)                       # parses: never cut mid-row
        self.assertTrue(0 < len(kept) < len(rows))
        self.assertEqual(kept, rows[:len(kept)])      # dropped from the end
        md = (out / "reddit.md").read_text()
        self.assertIn(f"truncated: {len(rows) - len(kept)}", md)

    def test_2b_rows_under_the_cap_are_untouched(self):
        out = self.tmp / "out"
        rows = [{"title": "one"}]
        with mock.patch.object(R.apify, "run", lambda *a, **k: rows):
            self.assertEqual(self.main(R, ["reddit.py", "--out", str(out), "--queries", "q"]), 0)
        self.assertEqual(json.loads((out / "reddit.json").read_text()), rows)
        self.assertNotIn("truncated:", (out / "reddit.md").read_text())

    def test_3_r_slash_is_a_prefix_not_a_character_set(self):
        self.assertEqual(R._sub("running"), "running")
        self.assertEqual(R._sub("r/running"), "running")
        self.assertEqual(R._sub("rr"), "rr")
        seen = {}

        def capture(actor, payload, timeout=900):
            seen.update(payload)
            return []
        with mock.patch.object(R.apify, "run", capture):
            self.main(R, ["reddit.py", "--out", str(self.tmp / "o"), "--queries", "q",
                          "--subreddits", "running", "r/running"])
        urls = [u["url"] for u in seen["startUrls"]]
        self.assertEqual(len(urls), 2)
        self.assertTrue(all("/r/running/search/" in u for u in urls), urls)


class _Stream:
    """An urlopen response: yields chunks, then raises if told to."""

    def __init__(self, chunks, then=None):
        self.chunks, self.then = list(chunks), then

    def read(self, n=-1):
        if self.chunks:
            return self.chunks.pop(0)
        if self.then:
            raise self.then
        return b""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FetchNeverCachesAPartial(_Base):
    def test_4_interrupted_stream_leaves_no_dest_and_a_retry_redownloads(self):
        dest = self.tmp / "media" / "clip.mp4"
        url = "https://cdn.example/clip.mp4"
        cut = lambda *a, **k: _Stream([b"half"], then=ConnectionResetError("reset"))
        with mock.patch.object(urllib.request, "urlopen", cut), \
             mock.patch.object(A, "say", lambda m: None):
            self.assertFalse(A.fetch(url, dest, tries=1))
        self.assertFalse(dest.exists())                       # no dest to mistake for done

        whole = lambda *a, **k: _Stream([b"whole ", b"file"])
        with mock.patch.object(urllib.request, "urlopen", whole):
            self.assertTrue(A.fetch(url, dest, tries=1))      # the retry really downloads
        self.assertEqual(dest.read_bytes(), b"whole file")
        self.assertFalse(dest.with_name(dest.name + ".part").exists())

        # A complete dest still short-circuits: no second download.
        with mock.patch.object(urllib.request, "urlopen", _no_network):
            self.assertTrue(A.fetch(url, dest, tries=1))


class TikTokFailsLoudly(_Base):
    def _run(self, err):
        out = self.tmp / "tt"

        def fail(*a, **k):
            raise err
        with mock.patch.dict(os.environ, {"APIFY_TOKEN": "FAKE-si150"}), \
             mock.patch.object(urllib.request, "urlopen", fail):
            code = self.main(T, ["tiktok.py", "trends", "--out", str(out)])
        return code, out

    def test_5_http_500_exits_1_with_run_json_failed(self):
        err = urllib.error.HTTPError("https://api.apify.com/x", 500, "Server Error", {},
                                     io.BytesIO(b"actor crashed"))
        code, out = self._run(err)
        self.assertEqual(code, 1)
        rec = json.loads((out / "run.json").read_text())
        self.assertEqual(rec["status"], "failed")
        self.assertIn("500", rec["error"])
        self.assertEqual(json.loads((out / "rows.json").read_text()), [])

    def test_5b_no_answer_at_all_exits_1_with_run_json_failed(self):
        code, out = self._run(urllib.error.URLError("dns down"))
        self.assertEqual(code, 1)
        rec = json.loads((out / "run.json").read_text())
        self.assertEqual(rec["status"], "failed")
        self.assertIn("dns down", rec["error"])
        self.assertEqual(json.loads((out / "rows.json").read_text()), [])

    def test_5c_a_good_run_still_exits_0(self):
        out = self.tmp / "tt"
        with mock.patch.dict(os.environ, {"APIFY_TOKEN": "FAKE-si150"}), \
             mock.patch.object(urllib.request, "urlopen",
                               lambda *a, **k: _Stream([b'[{"id": 1}]'])):
            code = self.main(T, ["tiktok.py", "trends", "--out", str(out)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((out / "run.json").read_text())["status"], "done")


if __name__ == "__main__":
    unittest.main()
