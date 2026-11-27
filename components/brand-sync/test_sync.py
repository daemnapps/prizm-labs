#!/usr/bin/env python3
"""Tests for brand sync against a small stand-in brand-folder server (synthetic files only)."""
import hashlib
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync  # noqa: E402

KEY = "pcbf_0a1b2c3d_" + "s" * 40


def h(data):
    return hashlib.sha256(data).hexdigest()


class FakeServer(BaseHTTPRequestHandler):
    files = {}
    writable = True
    puts = []

    def log_message(self, *a):
        pass

    def _send(self, status, body=b"", kind="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _route(self):
        if self.headers.get("Authorization") != "Bearer " + KEY:
            return None
        parts = urllib.parse.unquote(self.path).split("/api/v1/brand-folders/", 1)[1]
        return parts

    def do_GET(self):
        route = self._route()
        if route is None:
            return self._send(401, b"{}")
        access = "read_write" if self.writable else "read"
        if route == "":
            return self._send(200, json.dumps({"access": access, "brands": [{"key": "alpha", "name": "Alpha"}]}).encode())
        if route == "alpha/":
            files = [{"path": p, "sha256": h(d), "size": len(d)} for p, d in sorted(self.files.items())]
            return self._send(200, json.dumps({"brand": "alpha", "access": access, "files": files}).encode())
        if route.startswith("alpha/files/") and route[12:] in self.files:
            return self._send(200, self.files[route[12:]], "application/octet-stream")
        return self._send(404, b"{}")

    def do_PUT(self):
        route = self._route()
        if route is None:
            return self._send(401, b"{}")
        if not self.writable:
            return self._send(403, b"{}")
        rel = route[12:]
        body = self.rfile.read(int(self.headers["Content-Length"]))
        current = h(self.files[rel]) if rel in self.files else "none"
        if self.headers.get("X-Base-SHA256") != current:
            return self._send(409, b"{}")
        self.files[rel] = body
        self.puts.append(rel)
        return self._send(201 if current == "none" else 200, b"{}")


class BrandSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeServer)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/api/v1/"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        FakeServer.files = {"avatars/main.md": b"avatar v1\n", "products.json": b"{}\n"}
        FakeServer.writable = True
        FakeServer.puts = []
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.brands = Path(self.temp.name)
        self.folder = self.brands / "alpha"

    def run_sync(self, *argv, key=KEY):
        out = io.StringIO()
        client = sync.Client(url=self.url, key=key, tenant="")
        code = sync.main([*argv, "--brands-dir", str(self.brands)], out=out, client=client)
        return code, out.getvalue()

    def test_brands_lists_access(self):
        code, out = self.run_sync("brands")
        self.assertEqual(code, 0)
        self.assertIn("read and write", out)
        self.assertIn("alpha", out)

    def test_bad_key_says_so_plainly(self):
        code, out = self.run_sync("brands", key="pcbf_00000000_" + "x" * 40)
        self.assertEqual(code, 2)
        self.assertIn("didn't accept BRAND_API_KEY", out)
        self.assertNotIn("x" * 40, out)

    def test_first_pull_brings_everything_in(self):
        code, out = self.run_sync("pull", "alpha")
        self.assertEqual(code, 0, out)
        self.assertEqual((self.folder / "avatars" / "main.md").read_bytes(), b"avatar v1\n")
        self.assertIn("Pulled 2", out)
        self.assertIn("In step: 2", self.run_sync("status", "alpha")[1])

    def test_server_change_pulls_and_local_change_pushes(self):
        self.run_sync("pull", "alpha")
        FakeServer.files["avatars/main.md"] = b"avatar v2\n"
        (self.folder / "products.json").write_bytes(b'{"a": 1}\n')
        (self.folder / "briefs").mkdir()
        (self.folder / "briefs" / "0001.md").write_bytes(b"brief\n")
        code, out = self.run_sync("status", "alpha")
        self.assertIn("1 new or changed on the server", out)
        self.assertIn("2 new or changed here", out)
        self.run_sync("pull", "alpha")
        self.assertEqual((self.folder / "avatars" / "main.md").read_bytes(), b"avatar v2\n")
        # The pull did not overwrite the local edit.
        self.assertEqual((self.folder / "products.json").read_bytes(), b'{"a": 1}\n')
        code, out = self.run_sync("push", "alpha")
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(FakeServer.puts), ["briefs/0001.md", "products.json"])
        self.assertEqual(FakeServer.files["products.json"], b'{"a": 1}\n')
        self.assertIn("In step: 3", self.run_sync("status", "alpha")[1])

    def test_change_in_both_places_is_a_conflict_and_left_alone(self):
        self.run_sync("pull", "alpha")
        FakeServer.files["products.json"] = b"server\n"
        (self.folder / "products.json").write_bytes(b"here\n")
        code, out = self.run_sync("pull", "alpha")
        self.assertEqual(code, 1)
        self.assertIn("changed in both places", out)
        self.assertEqual((self.folder / "products.json").read_bytes(), b"here\n")
        code, out = self.run_sync("push", "alpha")
        self.assertEqual(FakeServer.puts, [])
        self.assertEqual(FakeServer.files["products.json"], b"server\n")

    def test_push_refused_when_server_moved_since_pull(self):
        self.run_sync("pull", "alpha")
        (self.folder / "products.json").write_bytes(b"here\n")
        # Someone else changed it after our manifest was read: the server answers 409.
        real_upload = sync.Client.upload

        def racing(client, brand, rel, data, base):
            FakeServer.files[rel] = b"someone else\n"
            return real_upload(client, brand, rel, data, base)
        sync.Client.upload = racing
        try:
            code, out = self.run_sync("push", "alpha")
        finally:
            sync.Client.upload = real_upload
        self.assertEqual(code, 1)
        self.assertIn("pull first", out)
        self.assertEqual(FakeServer.files["products.json"], b"someone else\n")

    def test_read_only_key_cannot_push(self):
        self.run_sync("pull", "alpha")
        FakeServer.writable = False
        (self.folder / "products.json").write_bytes(b"here\n")
        code, out = self.run_sync("push", "alpha")
        self.assertEqual(code, 2)
        self.assertIn("read only", out)
        self.assertEqual(FakeServer.puts, [])

    def test_nothing_is_deleted_and_secrets_never_travel(self):
        self.run_sync("pull", "alpha")
        del FakeServer.files["products.json"]
        (self.folder / "avatars" / "main.md").unlink()
        (self.folder / ".env").write_bytes(b"SYNTHETIC=1\n")
        (self.folder / ".git").mkdir()
        (self.folder / ".git" / "config").write_bytes(b"x\n")
        code, out = self.run_sync("status", "alpha")
        self.assertIn("removed on the server — kept here", out)
        self.assertIn("removed here — still on the server", out)
        self.assertNotIn(".env", out)
        self.run_sync("pull", "alpha")
        self.run_sync("push", "alpha")
        self.assertTrue((self.folder / "products.json").exists())
        self.assertIn("avatars/main.md", FakeServer.files)
        self.assertEqual(FakeServer.puts, [])
        # Still reported next time, not forgotten.
        self.assertIn("removed on the server", self.run_sync("status", "alpha")[1])

    def test_bad_brand_name_is_refused(self):
        code, out = self.run_sync("pull", "../etc")
        self.assertEqual(code, 2)
        self.assertIn("lower-case", out)

    def test_compare_buckets(self):
        plan = sync.compare({"a": "1", "b": "1", "c": "1"}, {"a": "1", "b": "2", "c": "2", "n": "9"}, {"a": "2", "b": "1", "c": "3"})
        self.assertEqual(plan["pull"], ["a"])
        self.assertEqual(plan["push"], ["b", "n"])
        self.assertEqual(plan["conflict"], ["c"])


if __name__ == "__main__":
    unittest.main()
