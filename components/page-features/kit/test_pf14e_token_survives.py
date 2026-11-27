#!/usr/bin/env python3
"""PF-14e (token survives): the page server's /act key is kept in its own state folder, owner-only, and re-read at
every start — so a page opened before a restart (each kit merge) keeps its direct buttons; only `remove` or
`restart --new-token` makes a new one, and a key that is present but wrong says the server restarted with a new key.

    python3 components/page-features/kit/test_pf14e_token_survives.py

Page servers over a temp root (no git) and a temp state folder, their act runner a recorder, so "nothing run" is
exact. The verbs run through server.main with the agent and on/off stubbed. Fixtures are here.
"""
import contextlib
import http.client
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import threading
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402
import server  # noqa: E402

PERSON = "tess"
PAGE = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n</head>\n<body><p>page</p></body>\n</html>\n'
TPL = "platform/views/viewers/_templates/"
SET = {"kind": "quick", "run": "cq", "verb": "set", "fields": ["who"]}
FILES = {
    TPL + "content-queue.actions.json": json.dumps({"direct": {"24": SET}}),
    TPL + "content-queue.html": PAGE,
    "platform/views/viewers/tess/content-queue.html": PAGE,
}
CQ = {"family": "content-queue", "n": 24, "item": "x1", "field": "who", "value": "editor"}
REFERER = "/v/tess/content-queue.html"
WRONG = "your page server restarted with a new key — reload the page"
MISSING = "refused: no kit token (reload the page from the kit)"


class FakeAgent(object):
    platform, verb, tool, python = "darwin", "run", "launchctl", sys.executable


class TokenSurvivesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pf14e-")
        self.root = os.path.join(self.tmp, "root")
        self.state = os.path.join(self.tmp, "state")
        os.makedirs(self.state)
        for rel, text in FILES.items():
            p = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        self.ran, self.httpds = [], []

    def tearDown(self):
        for h in self.httpds:
            self.stop(h)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------------ helpers
    def start(self, state=None):
        """A page server over the state folder: (srv, httpd, port)."""
        srv = server.PageServer(state or self.state, self.root, PERSON, act_person=PERSON,
                                act_runner=lambda argv: self.ran.append(list(argv)) or (0, "ran"))
        httpd = server.Server(("127.0.0.1", 0), srv.handler())
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.httpds.append(httpd)
        return srv, httpd, httpd.server_address[1]

    def stop(self, httpd):
        if httpd in self.httpds:
            self.httpds.remove(httpd)
            httpd.shutdown()
            httpd.server_close()

    def page_token(self, port):
        """The token the page carries, as a browser would read it from the served page."""
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        try:
            c.request("GET", REFERER, headers={"Host": "127.0.0.1:%d" % port})
            r = c.getresponse()
            text = r.read().decode()
        finally:
            c.close()
        self.assertEqual(r.status, 200)
        m = re.search(r'<meta name="kit-token" content="([^"]+)">', text)
        self.assertTrue(m, "the page carries a token")
        return m.group(1)

    def post(self, port, token=None, origin="own", send_token=True):
        h = {"Host": "127.0.0.1:%d" % port, "Referer": "http://127.0.0.1:%d%s" % (port, REFERER),
             "Content-Type": "application/json"}
        if origin:
            h["Origin"] = "http://127.0.0.1:%d" % port if origin == "own" else origin
        if send_token:
            h["X-Kit-Token"] = token or ""
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        try:
            c.request("POST", "/act", body=json.dumps(CQ), headers=h)
            r = c.getresponse()
            return r.status, json.loads(r.read().decode())
        finally:
            c.close()

    def token_file(self, state=None):
        return os.path.join(state or self.state, server.TOKEN_FILE)

    def main(self, *argv):
        out = io.StringIO()
        with mock.patch.object(server, "agent_for", lambda *a: FakeAgent()), \
                mock.patch.object(server, "cmd_off", lambda agent, state=None: 0), \
                mock.patch.object(server, "cmd_on", lambda *a, **k: 0), \
                mock.patch.object(server, "locate", lambda repo, platform=None: (PERSON, self.state)), \
                contextlib.redirect_stdout(out):
            code = server.main(list(argv), repo=self.root, runner=lambda argv: (0, ""), platform="darwin")
        return code, out.getvalue()

    # ------------------------------------------------------------------ (a) a restart keeps the page's buttons
    def test_a_a_page_opened_before_a_restart_still_presses_its_buttons(self):
        srv, httpd, port = self.start()
        tok = self.page_token(port)
        self.assertEqual(tok, srv.token)
        self.assertIsNone(srv.token_why, "kept, not in memory only")
        self.assertEqual(self.post(port, tok)[0], 200)
        self.stop(httpd)                                   # the kit changed: run exits, the agent starts it again
        srv2, _, port2 = self.start()
        self.assertEqual(srv2.token, tok, "re-read from the same state folder, not minted again")
        code, res = self.post(port2, tok)
        self.assertEqual((code, res["ok"]), (200, True), res)
        self.assertEqual(len(self.ran), 2)
        self.assertEqual(self.page_token(port2), tok, "a page opened after the restart carries the same key")

    def test_a_the_token_is_in_its_file_and_nowhere_else(self):
        srv, _, port = self.start()
        self.post(port, srv.token)
        self.post(port, "nope")
        srv.save()
        with open(self.token_file(), encoding="ascii") as fh:
            self.assertEqual(fh.read(), srv.token)
        for d, _, fs in os.walk(self.tmp):
            for f in fs:
                p = os.path.join(d, f)
                if p == self.token_file():
                    continue
                with open(p, "rb") as fh:
                    self.assertNotIn(srv.token.encode(), fh.read(), p)   # root, clicks.jsonl, state.json
        self.assertTrue(os.path.isfile(os.path.join(self.state, "clicks.jsonl")))
        self.assertTrue(os.path.isfile(os.path.join(self.state, "state.json")))

    # ------------------------------------------------------------------ (b) owner-only
    @unittest.skipIf(sys.platform == "win32", "Windows has no 0600: the user's own %LOCALAPPDATA% ACL keeps it")
    def test_b_the_token_file_is_mode_0600(self):
        old = os.umask(0)                                  # the widest umask: the mode is the server's, not luck
        try:
            srv, _, _ = self.start()
        finally:
            os.umask(old)
        st = os.stat(self.token_file())
        self.assertEqual(stat.S_IMODE(st.st_mode), 0o600)
        self.assertEqual(st.st_uid, os.getuid())
        self.assertFalse(os.path.exists(self.token_file() + ".tmp"))

    @unittest.skipIf(sys.platform == "win32", "modes and links are the macOS half")
    def test_b_a_token_file_others_could_read_is_not_trusted(self):
        srv, httpd, _ = self.start()
        old = srv.token
        self.stop(httpd)
        os.chmod(self.token_file(), 0o644)
        srv2, httpd2, _ = self.start()
        self.assertNotEqual(srv2.token, old, "a key others could read is replaced")
        self.assertEqual(stat.S_IMODE(os.stat(self.token_file()).st_mode), 0o600)
        self.stop(httpd2)
        elsewhere = os.path.join(self.tmp, "elsewhere")
        with open(elsewhere, "w", encoding="ascii") as fh:
            fh.write("x" * 43)
        os.chmod(elsewhere, 0o600)
        os.unlink(self.token_file())
        os.symlink(elsewhere, self.token_file())
        srv3, _, _ = self.start()
        self.assertNotEqual(srv3.token, "x" * 43, "a link is never followed")
        self.assertFalse(os.path.islink(self.token_file()))

    def test_b_a_folder_it_cannot_write_keeps_the_key_in_memory_and_says_where_not_what(self):
        srv, _, port = self.start(state=os.path.join(self.tmp, "no-such", "state"))
        self.assertTrue(srv.token)
        self.assertIn("in memory only", srv.token_why)
        self.assertIn(server.TOKEN_FILE, srv.token_why)
        self.assertNotIn(srv.token, srv.token_why)

    # ------------------------------------------------------------------ (c) restart --new-token, remove
    def test_c_restart_new_token_refuses_the_old_page_with_the_new_wording(self):
        srv, httpd, port = self.start()
        old = self.page_token(port)
        self.stop(httpd)
        code, out = self.main("restart", "--new-token", "--no-open")
        self.assertEqual(code, 0, out)
        self.assertIn("new key", out)
        self.assertNotIn(old, out)
        srv2, _, port2 = self.start()
        self.assertNotEqual(srv2.token, old)
        self.assertNotIn(srv2.token, out, "the new key is never printed")
        code, res = self.post(port2, old)
        self.assertEqual((code, res["ok"]), (403, False))
        self.assertEqual(res["said"], "refused: " + WRONG)
        self.assertEqual(self.ran, [], "nothing run")
        self.assertEqual(self.post(port2, self.page_token(port2))[0], 200, "a reloaded page works")

    def test_c_a_plain_restart_keeps_the_key_and_new_token_goes_with_restart_only(self):
        srv, httpd, _ = self.start()
        self.stop(httpd)
        self.assertEqual(self.main("restart", "--no-open")[0], 0)
        self.assertEqual(server.read_token(self.state), srv.token)
        for verb in ("on", "off", "status", "remove"):
            code, out = self.main(verb, "--new-token")
            self.assertEqual(code, 2, verb)
            self.assertIn("--new-token goes with restart only", out)
        self.assertEqual(server.read_token(self.state), srv.token)

    def test_c_remove_takes_the_key_with_it(self):
        srv, httpd, _ = self.start()
        self.stop(httpd)
        with mock.patch.object(server, "cmd_off", lambda agent, state=None: 0), \
                mock.patch.object(server, "locate", lambda repo, platform=None: (PERSON, self.state)), \
                contextlib.redirect_stdout(io.StringIO()):
            code = server.cmd_remove(self.root, FakeAgent(), lambda argv: (0, ""), False)
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(self.token_file()))
        srv2, _, _ = self.start()
        self.assertNotEqual(srv2.token, srv.token, "the next start mints a new key")

    # ------------------------------------------------------------------ (d) the wording, and Origin as today
    def test_d_a_wrong_token_says_the_server_restarted_with_a_new_key(self):
        _, _, port = self.start()
        code, res = self.post(port, "x" * 43)
        self.assertEqual((code, res), (403, {"ok": False, "said": "refused: " + WRONG}))
        self.assertEqual(self.ran, [])
        self.assertFalse(os.path.exists(os.path.join(self.state, "clicks.jsonl")), "no token, no click")

    def test_d_no_token_keeps_todays_wording(self):
        _, _, port = self.start()
        for kw in ({"send_token": False}, {"token": ""}):
            code, res = self.post(port, **kw)
            self.assertEqual((code, res), (403, {"ok": False, "said": MISSING}), kw)
        self.assertEqual(self.ran, [])

    def test_d_a_foreign_origin_is_refused_as_today(self):
        srv, _, port = self.start()
        for origin in ("http://evil.example", None):
            code, res = self.post(port, srv.token, origin=origin)
            self.assertEqual((code, res["said"]), (403, "refused: only this kit's own page may ask"), origin)
        self.assertEqual(self.ran, [])

    def test_d_serve_py_says_the_same_words(self):
        self.assertEqual(serve.NEW_KEY, "refused: " + WRONG)
        self.assertEqual(serve.NO_TOKEN, MISSING)


if __name__ == "__main__":
    unittest.main()
