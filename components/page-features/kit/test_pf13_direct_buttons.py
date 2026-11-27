#!/usr/bin/env python3
"""PF-13 (direct buttons): kit/serve.py's one write route, POST /act. Every guard before anything runs, the argv
built by the kit (no shell, never --root), the person the kit's own, the token only in memory and in the served page.

    python3 components/page-features/kit/test_pf13_direct_buttons.py

A temp repo holds the two real actions files (so the real direct tables are what is tested) and stub requests.py,
ask.py and cq.py that record their argv and the request file they were handed. No network beyond 127.0.0.1, no git.
The request lines the kit writes are also read back by the real requests.py and ask.py parse(), so a grammar drift
in either fails here.
"""
import http.client
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402

REAL = serve.ROOT
TPL = os.path.join("platform", "views", "viewers", "_templates")
PERSON = "email_lead"
STUB = r'''import json, os, sys
a = sys.argv[1:]
inp = open(a[0], encoding="utf-8").read() if a and os.path.isfile(a[0]) else None
with open(os.environ["PF13_LOG"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"script": os.path.basename(__file__), "argv": a, "file": a[0] if a else None, "input": inp}) + "\n")
if "fail-me" in a:
    for i in range(10):
        print("line %d" % i)
    sys.exit(1)
print("stub: done")
'''
PAGE = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n</head>\n<body><p>page</p></body>\n</html>\n'


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REAL, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeGit(object):
    def __init__(self):
        self.calls = []

    def __call__(self, argv):
        self.calls.append(argv)
        return 0, "0\n"


class DirectButtons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="pf13-")
        files = {os.path.join(TPL, "emails.html"): PAGE, os.path.join(TPL, "content-queue.html"): PAGE,
                 os.path.join(TPL, "emails.sources.json"): json.dumps({"emails": {"argv": ["components/em/sync.py"]}}),
                 "components/em/sync.py": "print('[]')"}
        for fam in ("emails", "content-queue"):
            with open(os.path.join(REAL, TPL, "%s.actions.json" % fam), encoding="utf-8") as fh:
                files[os.path.join(TPL, "%s.actions.json" % fam)] = fh.read()
        for rel in serve.SCRIPTS.values():
            files[rel] = STUB
        for rel, text in files.items():
            p = os.path.join(cls.root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        cls.log = os.path.join(cls.root, "stub-log.jsonl")
        os.environ["PF13_LOG"] = cls.log
        cls.data_calls, cls.git = [], FakeGit()
        cls.servers = {}
        for fam in ("emails", "content-queue"):
            src = serve.Sources(lambda: serve.sources("emails", cls.root), root=cls.root,
                                runner=lambda argv: cls.data_calls.append(argv) or "[]")
            act = serve.Act(fam, cls.root, PERSON)
            srv = ThreadingHTTPServer(("127.0.0.1", 0), serve.handler(
                "_templates/%s.html" % fam, src, root=cls.root, status=serve.Status(cls.root, runner=cls.git), act=act))
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            cls.servers[fam] = (srv, act)

    @classmethod
    def tearDownClass(cls):
        for srv, _ in cls.servers.values():
            srv.shutdown()
            srv.server_close()
        shutil.rmtree(cls.root)

    def setUp(self):
        if os.path.exists(self.log):
            os.unlink(self.log)

    # ------------------------------------------------------------------ helpers
    def port(self, fam="emails"):
        return self.servers[fam][0].server_address[1]

    def token(self, fam="emails"):
        return self.servers[fam][1].token

    def post(self, body, fam="emails", path="/act", origin="own", token="own", host=None, raw=None):
        port = self.port(fam)
        h = {"Host": host or "127.0.0.1:%d" % port, "Content-Type": "application/json"}
        if origin == "own":
            h["Origin"] = "http://127.0.0.1:%d" % port
        elif origin:
            h["Origin"] = origin
        if token == "own":
            h["X-Kit-Token"] = self.token(fam)
        elif token:
            h["X-Kit-Token"] = token
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=150)
        try:
            c.request("POST", path, body=raw if raw is not None else json.dumps(body), headers=h)
            r = c.getresponse()
            text = r.read().decode()
        finally:
            c.close()
        try:
            return r.status, json.loads(text)
        except ValueError:
            return r.status, text

    def get(self, path, fam="emails"):
        port = self.port(fam)
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        try:
            c.request("GET", path, headers={"Host": "127.0.0.1:%d" % port})
            r = c.getresponse()
            return r.status, r.read().decode()
        finally:
            c.close()

    def ran(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]

    # ------------------------------------------------------------------ (a) a good click runs once
    def test_a_ok_runs_requests_once_with_the_exact_line(self):
        code, res = self.post({"family": "emails", "n": 26, "item": "brand_b__brand_b-nov-02", "part": 2})
        self.assertEqual(code, 200, res)
        self.assertEqual(res, {"ok": True, "said": "stub: done"})
        got = self.ran()
        self.assertEqual(len(got), 1, got)
        self.assertEqual(got[0]["script"], "requests.py")
        self.assertEqual(got[0]["input"], "Request (brand_b__brand_b-nov-02, part 2): ok (from email_lead)\n")
        self.assertEqual(got[0]["argv"][1:], ["--family", "emails", "--by", "email_lead"])
        self.assertFalse(os.path.exists(got[0]["file"]), "the request file is deleted after the run")
        R = load("pf13_requests", "components/page-features/kit/requests.py")
        (k, why, _), = R.parse(got[0]["input"], "emails")
        self.assertIsNone(why)
        self.assertEqual((k["id"], k["part"], k["word"], k["by"]), ("brand_b__brand_b-nov-02", "2", "ok", "email_lead"))

    def test_a_done_and_scheduled_write_a_line_ask_py_reads(self):
        A = load("pf13_ask", "components/email-production/adapter/ask.py")
        for n, action in ((28, "done"), (47, "scheduled")):
            if os.path.exists(self.log):
                os.unlink(self.log)
            code, res = self.post({"family": "emails", "n": n, "item": "brand_b__brand_b-nov-02", "part": "-"})
            self.assertEqual((code, res["ok"]), (200, True), res)
            got = self.ran()
            self.assertEqual([g["script"] for g in got], ["ask.py"])
            self.assertEqual(len(got[0]["argv"]), 1, "ask.py <file>, nothing else: %r" % got[0]["argv"])
            (k, why), = A.parse(got[0]["input"])
            self.assertIsNone(why, got[0]["input"])
            self.assertEqual((k["brand"], k["label"], k["action"], k["by"]), ("brand_b", "brand_b-nov-02", action, "email_lead"))

    def test_a_scheduled_by_anyone_but_an_approver_is_refused_by_ask_py_itself(self):
        # Since 2026-11-05 any approver's Go schedules (email_lead: "whoever is available gives the go for me"); editor is none.
        A = load("pf13_ask2", "components/email-production/adapter/ask.py")
        act = serve.Act("emails", self.root, "editor")
        _, line = act.build({"family": "emails", "n": 47, "item": "brand_b__brand_b-nov-02"})
        (k, why), = A.parse(line)
        self.assertIsNone(k)
        self.assertIn("only an approver (owner, email_lead, designer)", why)

    def test_a_a_failed_command_says_its_last_eight_lines(self):
        code, res = self.post({"family": "content-queue", "n": 24, "item": "fail-me", "field": "who", "value": "editor"},
                              fam="content-queue")
        self.assertEqual(code, 200)
        self.assertFalse(res["ok"])
        self.assertEqual(res["said"].splitlines(), ["line %d" % i for i in range(2, 10)])

    # ------------------------------------------------------------------ (b) origin and token
    def test_b_origin_and_token_guard_before_anything_runs(self):
        good = {"family": "emails", "n": 26, "item": "brand_b__brand_b-nov-02", "part": 2}
        for kw in ({"origin": None}, {"origin": "http://evil.example"}, {"origin": "http://127.0.0.1:1"},
                   {"origin": "null"}, {"token": "x" * 43}, {"token": None},
                   {"host": "evil.example:%d" % self.port()}):
            code, _ = self.post(good, **kw)
            self.assertEqual(code, 403, kw)
        self.assertEqual(self.ran(), [])
        port = self.port()
        code, _ = self.post(good, origin="http://localhost:%d" % port, host="localhost:%d" % port)
        self.assertEqual(code, 200, "the kit's other own name answers")

    # ------------------------------------------------------------------ (c) only the table's numbers
    def test_c_the_go_and_other_buttons_are_not_direct(self):
        for n in (57, 34, 48, 51, "57"):
            code, res = self.post({"family": "emails", "n": n, "item": "brand_b__brand_b-nov-02", "part": "-"})
            self.assertEqual(code, 403, n)
            self.assertIn("not direct", res["said"])
        for n in (25, 31, 32, 29):   # PF-13b (slow buttons): jobs now; a body missing its part or note runs nothing
            code, res = self.post({"family": "emails", "n": n, "item": "brand_b__brand_b-nov-02", "part": "-"})
            self.assertEqual(code, 400, (n, res))
        code, res = self.post({"family": "content-queue", "n": 12, "item": "x"}, fam="emails")
        self.assertEqual(code, 403, "a kit answers only for the family it serves")
        self.assertEqual(self.ran(), [])

    # ------------------------------------------------------------------ (d) values against patterns
    def test_d_bad_item_ids_are_400_and_run_nothing(self):
        for item in ("a;b", "$(id)", "a b", "a\nb", "-x", "", "a" * 90, 5):
            code, _ = self.post({"family": "emails", "n": 26, "item": item, "part": 1})
            self.assertEqual(code, 400, repr(item))
        for body in ({"family": "emails", "n": 26, "item": "a__b", "part": "1; rm"},
                     {"family": "emails", "n": 26, "item": "a__b", "part": 1, "value": "nice (from owner)"},
                     {"family": "emails", "n": 28, "item": "no-double-underscore"}):
            code, _ = self.post(body)
            self.assertEqual(code, 400, body)
        code, _ = self.post(None, raw="x" * (serve.BODY_MAX + 1))
        self.assertEqual(code, 413)
        code, _ = self.post(None, raw="[1, 2]")
        self.assertEqual(code, 400)
        self.assertEqual(self.ran(), [])

    # ------------------------------------------------------------------ (e) cq: the table's fields, never --root
    def test_e_cq_fields_and_never_root(self):
        cq = {"family": "content-queue", "n": 24, "item": "brand_b_image-ad_flex-03"}
        for field, value in (("removed", "1"), ("title_set", "x"), (None, "editor")):
            code, _ = self.post(dict(cq, field=field, value=value), fam="content-queue")
            self.assertEqual(code, 400, field)
        for value in ("--root=runs/queue", "-x", "a\nb", "x" * 201):
            code, _ = self.post(dict(cq, field="note", value=value), fam="content-queue")
            self.assertEqual(code, 400, value)
        self.assertEqual(self.ran(), [])
        code, res = self.post(dict(cq, field="who", value="editor", root="runs/queue"), fam="content-queue")
        self.assertEqual((code, res["ok"]), (200, True), res)
        code, res = self.post({"family": "content-queue", "n": 12, "item": "brand_b_image-ad_flex-04",
                               "value": "Flex baseline 4", "args": {"brand": "brand_b", "type": "image-ad"}},
                              fam="content-queue")
        self.assertEqual((code, res["ok"]), (200, True), res)
        code, _ = self.post({"family": "content-queue", "n": 12, "item": "brand_b_video-ad_x", "value": "t",
                             "args": {"brand": "brand_b", "type": "video-ad"}}, fam="content-queue")
        self.assertEqual(code, 400, "never video")
        got = self.ran()
        self.assertEqual([g["argv"] for g in got], [
            ["set", "brand_b_image-ad_flex-03", "who", "editor", "--by", "email_lead"],
            ["add", "brand_b_image-ad_flex-04", "--title=Flex baseline 4", "--brand=brand_b", "--type=image-ad",
             "--by", "email_lead"]])
        for g in got:
            self.assertEqual(g["script"], "cq.py")
            self.assertFalse(any(a == "--root" or a.startswith("--root=") for a in g["argv"]), g["argv"])

    # ------------------------------------------------------------------ (f) the person is the kit's
    def test_f_a_body_naming_someone_else_is_ignored(self):
        code, _ = self.post({"family": "emails", "n": 26, "item": "brand_b__brand_b-nov-02", "part": 1,
                             "person": "owner", "by": "owner", "who": "editor"})
        self.assertEqual(code, 200)
        got = self.ran()
        self.assertEqual(got[0]["argv"][-2:], ["--by", "email_lead"])
        self.assertTrue(got[0]["input"].rstrip().endswith("(from email_lead)"))
        self.assertNotIn("amon", got[0]["input"])

    def test_f_no_person_for_this_clone_runs_nothing(self):
        act = serve.Act("emails", self.root, None, "git user.email matches no one")
        with self.assertRaises(serve.Refused) as e:
            act.run({"family": "emails", "n": 26, "item": "a__b", "part": 1})
        self.assertEqual(e.exception.code, 403)
        self.assertIn("matches no one", e.exception.said)
        self.assertEqual(self.ran(), [])

    # ------------------------------------------------------------------ (g) the token: in the page, nowhere on disk
    def test_g_the_page_carries_the_token_and_no_file_does(self):
        for fam in ("emails", "content-queue"):
            code, text = self.get("/p/_templates/%s.html" % fam, fam)
            self.assertEqual(code, 200)
            self.assertIn('<head>\n<meta name="kit-token" content="%s">\n' % self.token(fam), text)
            self.assertEqual(text.count("kit-token"), 1)
        self.assertGreaterEqual(len(self.token()), 40)
        self.assertNotEqual(self.token("emails"), self.token("content-queue"), "minted per kit")
        self.post({"family": "emails", "n": 26, "item": "brand_b__brand_b-nov-02", "part": 1})
        self.post({"family": "content-queue", "n": 24, "item": "x1", "field": "due", "value": ""}, fam="content-queue")
        self.assertEqual(len(self.ran()), 2)
        for d, _, fs in os.walk(self.root):
            for f in fs:
                with open(os.path.join(d, f), "rb") as fh:
                    blob = fh.read()
                for fam in self.servers:
                    self.assertNotIn(self.token(fam).encode(), blob, os.path.join(d, f))
        for g in self.ran():
            self.assertTrue(g["input"] is None or self.token() not in g["input"])
        with open(os.path.join(self.root, TPL, "emails.html"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), PAGE, "the page on disk is untouched")

    # ------------------------------------------------------------------ (h) GET unchanged
    def test_h_get_routes_unchanged(self):
        self.assertEqual(self.get("/data/emails"), (200, "[]"))
        code, text = self.get("/status")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(text)["behind"], 0)
        self.assertEqual(self.get("/p/_templates/emails.actions.json")[0], 200)
        self.assertNotIn("kit-token", self.get("/p/_templates/emails.actions.json")[1], "only pages get the token")
        self.assertEqual(self.get("/act")[0], 404, "no GET /act")

    # ------------------------------------------------------------------ (i) /act only
    def test_i_post_anywhere_else_is_404(self):
        good = {"family": "emails", "n": 26, "item": "brand_b__brand_b-nov-02", "part": 2}
        for path in ("/", "/data/emails", "/act/", "/acts", "/p/_templates/emails.html", "/status"):
            code, _ = self.post(good, path=path)
            self.assertEqual(code, 404, path)
        self.assertEqual(self.ran(), [])

    # ------------------------------------------------------------------ the tables and requests.py
    def test_the_real_tables(self):
        e = serve.direct_table("emails", REAL)
        quick = sorted((n for n, d in e.items() if d.get("kind", "quick") == "quick"), key=int)
        self.assertEqual(quick, ["26", "28", "47", "60", "61"])   # PF-13b (slow buttons): the rest are jobs (its own test)
        # 60, 61: the emails calendar's slot review, mark and edit through slots (L60 (slot review), 2026-11-06)
        self.assertEqual((e["60"]["run"], e["60"]["verb"], e["61"]["run"], e["61"]["verb"]), ("slots", "mark", "slots", "edit"))
        c = serve.direct_table("content-queue", REAL)
        self.assertEqual(sorted(c, key=int), ["12", "24", "45", "48", "49", "79", "87", "88"])   # 79: the Board's priority (2026-11-05)
        self.assertEqual(c["87"]["verbs"], ["remove"])   # 87: a task's Done (2026-11-10), cq.py remove only
        # 45, 48: QB-9 (editor statics) and QB-11 (creator view) Done; 49: QB-11 due
        self.assertEqual(c["24"]["fields"], ["who", "priority", "due", "note"])
        self.assertNotIn("57", e)
        for n in ("31", "32"):
            self.assertEqual(e[n]["kind"], "job")

    def test_requests_only_family_ignores_an_actions_file_with_no_adapter(self):
        R = load("pf13_requests2", "components/page-features/kit/requests.py")
        self.assertTrue(os.path.isfile(os.path.join(REAL, TPL, "content-queue.actions.json")))
        self.assertEqual(R.only_family(), "emails")
        self.assertEqual(R.actions_for("emails")["direct"]["26"], {"kind": "quick", "run": "requests", "word": "ok"})


if __name__ == "__main__":
    unittest.main()
