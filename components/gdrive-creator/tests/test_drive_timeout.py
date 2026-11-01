#!/usr/bin/env python3
"""Every Drive call has a time limit, and a download chunk is retried (2026-10-29).

    python3 components/gdrive-creator/tests/test_drive_timeout.py

Why: service() built its client with no timeout, so one stalled get_media held the page server's email list for
ten minutes on a cold cache. The Google modules are stood in through engine._google, so no Google package, no key
and no network are needed. Stdlib only, 3.9.

  a  service(): the client's http is an authorized http over httplib2.Http(timeout=engine.TIMEOUT_S), and build()
     is given that http and no bare credentials
  b  get_media(): every next_chunk is asked to retry engine.CHUNK_RETRIES times, and the bytes are written whole
  c  a stall that raises the timeout inside the retries is retried, then the download finishes
  d  TIMEOUT_S is a minute and CHUNK_RETRIES at least one
  e  a missing httplib2 or google-auth-httplib2 is named by its package, not as the API client
"""
import socket
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
sys.path.append(str(COMPONENT))                    # APPEND — never insert at 0

from gdrive_creator import engine  # noqa: E402


class FakeHttp:
    def __init__(self, timeout=None):
        self.timeout = timeout


class FakeAuthorizedHttp:
    def __init__(self, creds, http=None):
        self.creds, self.http = creds, http


def fake_google(seen):
    def build(name, version, **kw):
        seen["build"] = (name, version, kw)
        return "svc"
    mods = {"googleapiclient.discovery": types.SimpleNamespace(build=build),
            "httplib2": types.SimpleNamespace(Http=FakeHttp),
            "google_auth_httplib2": types.SimpleNamespace(AuthorizedHttp=FakeAuthorizedHttp)}
    return lambda dotted: mods[dotted]


class FakeFiles:
    def get_media(self, fileId, supportsAllDrives):
        return {"fileId": fileId, "data": b"picture-bytes"}


class FakeSvc:
    def files(self):
        return FakeFiles()


def downloader(retries_seen, stalls=0):
    class FakeDownload:
        def __init__(self, fh, req):
            self.fh, self.req, self.stalls = fh, req, stalls

        def next_chunk(self, num_retries=0):
            retries_seen.append(num_retries)
            while self.stalls:                     # what googleapiclient does inside num_retries: retry the timeout
                self.stalls -= 1
                if num_retries < 1:
                    raise socket.timeout("timed out")
            self.fh.write(self.req["data"])
            return None, True
    return types.SimpleNamespace(MediaIoBaseDownload=FakeDownload)


class Timeout(unittest.TestCase):
    def test_a_service_has_a_time_limit(self):
        seen = {}
        with mock.patch.object(engine, "_google", fake_google(seen)), \
                mock.patch.object(engine, "_creds", lambda: "creds"):
            self.assertEqual(engine.service(), "svc")
        name, version, kw = seen["build"]
        self.assertEqual((name, version), ("drive", "v3"))
        self.assertNotIn("credentials", kw)
        self.assertIsInstance(kw["http"], FakeAuthorizedHttp)
        self.assertEqual(kw["http"].creds, "creds")
        self.assertEqual(kw["http"].http.timeout, engine.TIMEOUT_S)
        self.assertFalse(kw["cache_discovery"])

    def test_b_get_media_retries_each_chunk(self):
        retries = []
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(engine, "_google", lambda dotted: downloader(retries)):
            out = engine.get_media("abc", Path(d) / "p.png", svc=FakeSvc())
            self.assertEqual(Path(out).read_bytes(), b"picture-bytes")
        self.assertEqual(retries, [engine.CHUNK_RETRIES])

    def test_c_a_stall_is_retried(self):
        retries = []
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(engine, "_google", lambda dotted: downloader(retries, stalls=2)):
            out = engine.get_media("abc", Path(d) / "p.png", svc=FakeSvc())
            self.assertEqual(Path(out).read_bytes(), b"picture-bytes")

    def test_d_the_limits(self):
        self.assertEqual(engine.TIMEOUT_S, 60)
        self.assertGreaterEqual(engine.CHUNK_RETRIES, 1)

    def test_e_missing_http_packages_are_named(self):
        for dotted, package in (("httplib2", "httplib2"), ("google_auth_httplib2", "google-auth-httplib2")):
            with mock.patch.object(engine.importlib, "import_module", side_effect=ImportError("no " + dotted)):
                with self.assertRaises(SystemExit) as e:
                    engine._google(dotted)
            self.assertIn("install %s " % package, str(e.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
