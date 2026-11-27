#!/usr/bin/env python3
"""PF-14d (page family check): a page presses only its own family's buttons — POST /act on the page server refuses a
body family that is not the family of the page that sent it (its Referer), and a request from no page.

    python3 components/page-features/kit/test_pf14d_page_family.py

One page server over a temp root (no git), its act runner a recorder, so "nothing run" is exact. The families,
their run tables and the pages are fixtures here.
"""
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402
import server  # noqa: E402

PERSON = "tess"
PAGE = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n</head>\n<body><p>page</p></body>\n</html>\n'
TPL = "platform/views/viewers/_templates/"
SET = {"kind": "quick", "run": "cq", "verb": "set", "fields": ["who", "priority", "due", "note"]}
FILES = {
    TPL + "content-queue.actions.json": json.dumps({"direct": {"24": SET}}),
    TPL + "emails.actions.json": json.dumps({"direct": {"26": {"kind": "quick", "run": "requests", "word": "ok"}}}),
    TPL + "home.actions.json": json.dumps({"direct": {"3": {"kind": "quick", "run": "cq", "verb": "set",
                                                            "fields": ["who"]}}}),
    TPL + "content-queue.html": PAGE,
    TPL + "emails.html": PAGE,
    "platform/views/viewers/tess/content-queue.html": PAGE,
    "platform/views/viewers/tess/drafts/content-queue--try.html": PAGE,
    "platform/views/viewers/tess/emails.html": PAGE,
    "platform/views/viewers/tess/home.html": PAGE,
}
CQ = {"family": "content-queue", "n": 24, "item": "x1", "field": "who", "value": "editor"}
EM = {"family": "emails", "n": 26, "item": "x"}


class PageFamilyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pf14d-")
        self.root = os.path.join(self.tmp, "root")
        self.state = os.path.join(self.tmp, "state")
        os.makedirs(self.state)
        for rel, text in FILES.items():
            p = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        self.ran = []
        self.srv = server.PageServer(self.state, self.root, PERSON, act_person=PERSON,
                                     act_runner=lambda argv: self.ran.append(list(argv)) or (0, "ran"))
        self.httpd = server.Server(("127.0.0.1", 0), self.srv.handler())
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.port = self.httpd.server_address[1]

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------------ helpers
    def post(self, body, referer=None, host=None):
        h = {"Host": "127.0.0.1:%d" % self.port, "Origin": "http://127.0.0.1:%d" % self.port,
             "X-Kit-Token": self.srv.token, "Content-Type": "application/json"}
        if referer is not None:
            h["Referer"] = "http://%s%s" % (host or "127.0.0.1:%d" % self.port, referer)
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            c.request("POST", "/act", body=json.dumps(body), headers=h)
            r = c.getresponse()
            return r.status, json.loads(r.read().decode())
        finally:
            c.close()

    def files(self):
        out = {}
        for d, _, fs in os.walk(self.root):
            for f in fs:
                p = os.path.join(d, f)
                with open(p, "rb") as fh:
                    out[os.path.relpath(p, self.root)] = fh.read()
        return out

    def lines(self):
        p = os.path.join(self.state, "clicks.jsonl")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]

    # ------------------------------------------------------------------ (a) another family's button
    def test_a_content_queue_page_pressing_an_emails_button_is_403_and_runs_nothing(self):
        before = self.files()
        code, res = self.post(EM, referer="/v/tess/content-queue.html")
        self.assertEqual(code, 403, res)
        self.assertEqual(res["said"], "this page's buttons are content-queue's")
        self.assertFalse(res["ok"])
        self.assertEqual(self.ran, [], "nothing run")
        self.assertEqual(self.files(), before, "nothing written")
        (c,) = self.lines()
        self.assertEqual((c["page"], c["n"], c["ok"], c.get("refused")), ("tess/content-queue.html", 26, False, True))
        self.assertEqual(server.click_word(c), "refused")
        self.assertIn("<td>refused</td>", self.srv.index_html())

    # ------------------------------------------------------------------ (b) its own family: as today
    def test_b_the_same_family_runs_as_today(self):
        for page in ("/v/tess/content-queue.html", "/v/tess/drafts/content-queue--try.html",
                     "/p/_templates/content-queue.html"):
            code, res = self.post(CQ, referer=page)
            self.assertEqual((code, res["ok"]), (200, True), (page, res))
        self.assertEqual(len(self.ran), 3)
        self.assertEqual(self.ran[0][2:], ["set", "x1", "who", "editor", "--by", PERSON])
        self.assertEqual([server.click_word(c) for c in self.lines()], ["ok"] * 3)
        code, res = self.post(EM, referer="/v/tess/emails.html")
        self.assertEqual(code, 200, res)
        self.assertEqual(len(self.ran), 4, "the emails page's own button runs")

    # ------------------------------------------------------------------ (c) no page: refused
    def test_c_no_referer_or_another_host_or_no_page_route_is_403(self):
        before = self.files()
        for kw in ({}, {"referer": "/v/tess/content-queue.html", "host": "evil.example"},
                   {"referer": "/plain"}, {"referer": "/data/queue"}):
            code, res = self.post(CQ, **kw)
            self.assertEqual(code, 403, (kw, res))
            self.assertEqual(res["said"], server.NO_PAGE, kw)
        self.assertEqual(self.ran, [])
        self.assertEqual(self.files(), before)
        self.assertEqual([server.click_word(c) for c in self.lines()], ["refused"] * 4)

    # ------------------------------------------------------------------ (d) the home page, PF-17 (home page family)
    def test_d_the_home_pages_own_buttons_run_and_only_those(self):
        code, res = self.post({"family": "home", "n": 3, "item": "h1", "field": "who", "value": "editor"}, referer="/")
        self.assertEqual((code, res["ok"]), (200, True), res)
        self.assertEqual(self.ran[0][2:], ["set", "h1", "who", "editor", "--by", PERSON])
        self.assertEqual(self.lines()[-1]["page"], "tess/home.html")
        code, res = self.post(CQ, referer="/")
        self.assertEqual(code, 403)
        self.assertEqual(res["said"], "this page's buttons are home's")
        self.assertEqual(len(self.ran), 1)

    # ------------------------------------------------------------------ (e) the guards before it still hold
    def test_e_a_bad_family_is_still_400_and_a_wrong_number_still_not_direct(self):
        code, res = self.post(dict(CQ, family="Bad Family"), referer="/v/tess/content-queue.html")
        self.assertEqual(code, 400, res)
        code, res = self.post(dict(CQ, n=26), referer="/v/tess/content-queue.html")
        self.assertEqual((code, res["said"]), (403, serve.NOT_DIRECT))
        self.assertEqual(self.ran, [])

    # ------------------------------------------------------------------ (f) serve.py's session kit: one family
    def test_f_the_session_kit_was_one_family_already(self):
        a = serve.Act("content-queue", self.root, PERSON, runner=lambda argv: self.ran.append(argv) or (0, ""))
        with self.assertRaises(serve.Refused) as e:
            a.run(EM)
        self.assertEqual(e.exception.code, 403)
        self.assertEqual(self.ran, [])


if __name__ == "__main__":
    unittest.main()
