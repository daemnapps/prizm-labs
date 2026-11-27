#!/usr/bin/env python3
"""PF-13b (slow buttons): the kit's background jobs (kit/jobs.py) through POST /act and GET /job/<id>, the confirm a
model button asks first, one job per email, the 20 min limit, POST /upload for 53 use my picture, and the note that
travels only in the request file — under kit/serve.py's one-page kit and kit/server.py's page server.

    python3 components/page-features/kit/test_pf13b_jobs.py

A temp repo holds the real emails.actions.json (so the real run table is what is tested) and stub requests.py and
own_picture.py that log their argv and request file, and sleep, print or fail as the request asks (an item or note
naming slow, hang or fail). The request lines are read back by the real requests.py parse(). No network beyond
127.0.0.1, no git.
"""
import http.client
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jobs  # noqa: E402
import serve  # noqa: E402
import server  # noqa: E402

REAL = serve.ROOT
TPL = os.path.join("platform", "views", "viewers", "_templates")
PERSON = "email_lead"
EMAIL = "brand_b__brand_b-nov-02"
RUN = "runs/email-production/brand_b/brand_b-nov-02"
STUB = r'''import json, os, sys, time
a = sys.argv[1:]
inp = open(a[0], encoding="utf-8").read() if a and os.path.isfile(a[0]) else None
text = (inp or "") + " " + " ".join(a)
def log(event):
    with open(os.environ["PF13B_LOG"], "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"script": os.path.basename(__file__), "argv": a, "file": a[0] if a else None,
                             "input": inp, "pid": os.getpid(), "event": event, "at": time.time()}) + "\n")
log("start")
print("stub: started")
if "hang" in text:
    time.sleep(60)
if "slow" in text:
    time.sleep(1.5)
if "fail" in text:
    for i in range(10):
        print("line %d" % i)
    sys.exit(1)
log("end")
print("stub: done")
'''
PAGE = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n</head>\n<body><p>page</p></body>\n</html>\n'
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REAL, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Jobs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="pf13b-")
        with open(os.path.join(REAL, TPL, "emails.actions.json"), encoding="utf-8") as fh:
            actions = fh.read()
        files = {os.path.join(TPL, "emails.html"): PAGE, os.path.join(TPL, "emails.actions.json"): actions,
                 os.path.join(TPL, "emails.sources.json"): json.dumps({"emails": {"argv": ["components/em/sync.py"]}}),
                 "components/em/sync.py": "print('[]')",
                 "components/email-production/adapter/adapter.json": json.dumps({"models": {"redo": ["claude-opus-5"]}}),
                 "components/models/models.json": json.dumps({"models": [{"id": "claude-opus-5",
                                                                          "label": "Claude Opus 5"}]}),
                 RUN + "/design/email.json": "{}", "runs/email-production/brand_b/brand_b-nov-03/design/email.json": "{}",
                 "team/people/email_lead/identity.json": "{}"}
        for rel in serve.SCRIPTS.values():
            files[rel] = STUB
        for rel, text in files.items():
            p = os.path.join(cls.root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        cls.log = os.path.join(cls.root, "stub-log.jsonl")
        os.environ["PF13B_LOG"] = cls.log
        cls.servers = []
        src = serve.Sources(lambda: serve.sources("emails", cls.root), root=cls.root, runner=lambda argv: "[]")
        status = serve.Status(cls.root, runner=lambda argv: (0, "0\n"))
        cls.act = serve.Act("emails", cls.root, PERSON)
        cls.port = cls.up(serve.handler("_templates/emails.html", src, root=cls.root, status=status, act=cls.act))
        cls.short = serve.Act("emails", cls.root, PERSON)                       # (e): a 1 s limit
        cls.short._jobs = jobs.Jobs(cls.root, gate=cls.short.lock, timeout=1)
        cls.short_port = cls.up(serve.handler("_templates/emails.html", src, root=cls.root, status=status,
                                              act=cls.short))
        cls.state = os.path.join(cls.root, "state")                             # (d): the page server's click log
        os.makedirs(cls.state)
        cls.ps = server.PageServer(cls.state, cls.root, PERSON, act_person=PERSON)
        cls.ps_port = cls.up(cls.ps.handler())

    @classmethod
    def up(cls, h):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), h)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        cls.servers.append(srv)
        return srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        for srv in cls.servers:
            srv.shutdown()
            srv.server_close()
        shutil.rmtree(cls.root, ignore_errors=True)

    def setUp(self):
        if os.path.exists(self.log):
            os.unlink(self.log)

    # ------------------------------------------------------------------ helpers
    def req(self, method, path, body=None, port=None, origin="own", token=None, ctype="application/json",
            referer=None):
        port = port or self.port
        h = {"Host": "127.0.0.1:%d" % port}
        if method == "POST":
            h["Content-Type"] = ctype
            if origin == "own":
                h["Origin"] = "http://127.0.0.1:%d" % port
            elif origin:
                h["Origin"] = origin
            tok = token if token is not None else self.token_for(port)
            if tok:
                h["X-Kit-Token"] = tok
        if referer:
            h["Referer"] = "http://127.0.0.1:%d%s" % (port, referer)
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
        try:
            data = body if isinstance(body, bytes) or body is None else json.dumps(body)
            c.request(method, path, body=data, headers=h)
            r = c.getresponse()
            text = r.read().decode()
        finally:
            c.close()
        try:
            return r.status, json.loads(text)
        except ValueError:
            return r.status, text

    def token_for(self, port):
        return {self.port: self.act.token, self.short_port: self.short.token, self.ps_port: self.ps.token}[port]

    def post(self, body, **kw):
        return self.req("POST", "/act", body, **kw)

    def job(self, job_id, port=None):
        return self.req("GET", "/job/" + job_id, port=port)

    def wait(self, job_id, port=None, limit=30):
        end = time.time() + limit
        while time.time() < end:
            code, j = self.job(job_id, port)
            self.assertEqual(code, 200, j)
            if j["state"] in ("done", "failed"):
                return j
            time.sleep(0.1)
        self.fail("job %s never ended" % job_id)

    def ran(self, event="start"):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as fh:
            return [x for x in (json.loads(y) for y in fh if y.strip()) if x["event"] == event]

    def files(self):
        out = set()
        for d, _, fs in os.walk(self.root):
            for f in fs:
                out.add(os.path.relpath(os.path.join(d, f), self.root).replace(os.sep, "/"))
        return out

    def upload(self, data, item=EMAIL, port=None, **kw):
        return self.req("POST", "/upload?family=emails&item=%s" % quote(item), data, port=port, ctype="image/png", **kw)

    # ------------------------------------------------------------------ (a) a job answers at once, then runs
    def test_a_a_job_answers_at_once_and_runs_to_done(self):
        t0 = time.time()
        code, res = self.post({"family": "emails", "n": 31, "item": "b__slow-a", "part": 2, "value": "up"})
        self.assertEqual(code, 202, res)
        self.assertLess(time.time() - t0, 1.0, "the answer does not wait for the command")
        self.assertTrue(re.fullmatch(r"[0-9a-f]{16}", res["job"]), res)
        self.assertEqual(res["ask"], "Request (b__slow-a, part 2): move up (from email_lead)")
        code, j = self.job(res["job"])
        self.assertEqual(code, 200)
        self.assertIn(j["state"], ("queued", "running"))
        self.assertIsNone(j["ended"])
        j = self.wait(res["job"])
        self.assertEqual(j["state"], "done", j)
        self.assertEqual(j["code"], 0)
        self.assertTrue(j["said"].endswith("stub: done"), j)
        self.assertTrue(j["started"] and j["ended"])
        (g,) = self.ran()
        self.assertEqual(g["script"], "requests.py")
        self.assertEqual(g["input"], "Request (b__slow-a, part 2): move up (from email_lead)\n")
        self.assertEqual(g["argv"][1:], ["--family", "emails", "--by", "email_lead"])
        self.assertFalse(os.path.exists(g["file"]), "the request file is deleted when the job ends")
        self.assertEqual(self.job("0" * 16)[0], 404)

    def test_a_32_and_46_are_jobs_with_the_shared_line(self):
        code, res = self.post({"family": "emails", "n": 32, "item": "b__c1", "part": 4})
        self.assertEqual(code, 202, res)
        self.wait(res["job"])
        edits = [{"path": "title", "before": "Old", "value": "Neu —   \"new\" (from owner)"}]
        code, res = self.post({"family": "emails", "n": 46, "item": "b__c2", "part": 1, "edits": edits})
        self.assertEqual(code, 202, res)
        self.wait(res["job"])
        got = self.ran()
        self.assertEqual([g["input"].splitlines()[0][:34] for g in got],
                         ["Request (b__c1, part 4): remove (f", "Request (b__c2, part 1): words [{\""])
        R = load("pf13b_requests_a", "components/page-features/kit/requests.py")
        (k, why, _), = R.parse(got[1]["input"], "emails")
        self.assertIsNone(why)
        self.assertEqual((k["word"], k["by"], json.loads(k["payload"])), ("words", "email_lead", edits))
        for bad in ({"part": "-", "edits": edits}, {"part": 1}, {"part": 1, "edits": [{"value": "x"}]},
                    {"part": 1, "edits": edits, "note": "x"}):
            code, _ = self.post(dict({"family": "emails", "n": 46, "item": "b__c3"}, **bad))
            self.assertEqual(code, 400, bad)

    # ------------------------------------------------------------------ (b) one job per email
    def test_b_a_second_click_on_a_working_email_is_409_another_runs_beside_it(self):
        code, one = self.post({"family": "emails", "n": 32, "item": "b__slow-b", "part": 1})
        self.assertEqual(code, 202, one)
        code, res = self.post({"family": "emails", "n": 31, "item": "b__slow-b", "part": 1, "value": "down"})
        self.assertEqual(code, 409, res)
        self.assertEqual(res["said"], "already working on b__slow-b")
        self.assertEqual(res["job"], one["job"])
        code, two = self.post({"family": "emails", "n": 32, "item": "b__slow-c", "part": 1})
        self.assertEqual(code, 202, two)
        self.wait(one["job"])
        self.wait(two["job"])
        starts = {g["input"].split(",")[0]: g["at"] for g in self.ran()}
        ends = {g["input"].split(",")[0]: g["at"] for g in self.ran("end")}
        self.assertEqual(len(starts), 2, "the refused click ran nothing")
        self.assertLess(starts["Request (b__slow-c"], ends["Request (b__slow-b"], "the two emails ran side by side")
        code, res = self.post({"family": "emails", "n": 32, "item": "b__slow-b", "part": 1})
        self.assertEqual(code, 202, "once it ended, the email takes a new job")
        self.wait(res["job"])

    def test_b_two_clicks_at_once_start_one_job(self):
        out = []
        body = {"family": "emails", "n": 32, "item": "b__slow-d", "part": 1}
        ts = [threading.Thread(target=lambda: out.append(self.post(body))) for _ in range(5)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(sorted(c for c, _ in out), [202, 409, 409, 409, 409])
        self.wait(next(r["job"] for c, r in out if c == 202))
        self.assertEqual(len(self.ran()), 1)

    # ------------------------------------------------------------------ (c) the confirm for model buttons
    def test_c_a_model_button_without_confirmed_is_428_and_runs_nothing(self):
        note = {"family": "emails", "n": 29, "item": EMAIL, "part": "-", "note": "warmer, less text"}
        for extra in ({}, {"confirmed": "true"}, {"confirmed": 1}, {"confirmed": False}):
            code, res = self.post(dict(note, **extra))
            self.assertEqual(code, 428, extra)
            self.assertFalse(res["ok"])
            self.assertEqual(res["confirm"], res["said"])
        for word in ("Redo the whole email", "costs money", "Claude Opus 5 (claude-opus-5)", "Cancel runs nothing"):
            self.assertIn(word, res["confirm"])
        code, res = self.post({"family": "emails", "n": 27, "item": EMAIL, "part": "-"})
        self.assertEqual(code, 428)
        self.assertIn("names no model", res["confirm"])
        for n, body in ((25, {"part": 2, "picture": 0, "note": "x"}), (30, {"part": 2, "note": "x"})):
            code, res = self.post(dict({"family": "emails", "n": n, "item": EMAIL}, **body))
            self.assertEqual(code, 428, n)
            self.assertIn("costs money", res["confirm"])
        self.assertEqual(self.ran(), [], "no confirm, nothing runs")
        code, res = self.post(dict(note, confirmed=True))
        self.assertEqual(code, 202, res)
        self.assertEqual(self.wait(res["job"])["state"], "done")
        (g,) = self.ran()
        self.assertEqual(g["input"], "Request (%s, part -): redo warmer, less text (from email_lead)\n" % EMAIL)

    def test_c_the_kinds_of_the_real_table(self):
        t = serve.direct_table("emails", REAL)
        kinds = {n: d.get("kind") for n, d in t.items()}
        self.assertEqual(kinds, {"26": "quick", "28": "quick", "47": "quick", "60": "quick", "61": "quick", "31": "job", "32": "job", "46": "job",
                                 "25": "confirm-job", "27": "confirm-job", "29": "confirm-job", "30": "confirm-job",
                                 "53": "confirm-job"})
        self.assertNotIn("57", t, "the Go is PF-13d (Go button)'s")
        for n in ("29", "30"):
            self.assertEqual(t[n]["note"], 2000)
        self.assertIn("calls no model", t["53"]["cost"])
        c = serve.direct_table("content-queue", REAL)
        self.assertEqual({d.get("kind") for d in c.values()}, {"quick"})

    # ------------------------------------------------------------------ (d) a failure is said, and logged
    def test_d_a_failed_job_says_its_last_lines_and_the_click_log_has_its_line(self):
        body = {"family": "emails", "n": 32, "item": "b__fail-1", "part": 3}
        code, res = self.post(body, port=self.ps_port, referer="/v/email_lead/emails.html")
        self.assertEqual(code, 202, res)
        j = self.wait(res["job"], self.ps_port)
        self.assertEqual(j["state"], "failed")
        self.assertEqual(j["code"], 1)
        self.assertEqual(j["said"].splitlines(), ["line %d" % i for i in range(2, 10)])
        self.assertEqual(j["ask"], "Request (b__fail-1, part 3): remove (from email_lead)")
        with open(os.path.join(self.state, "clicks.jsonl"), encoding="utf-8") as fh:
            lines = [json.loads(x) for x in fh if x.strip()]
        mine = [x for x in lines if x.get("job") == res["job"]]
        self.assertEqual(len(mine), 1, "one line per finished job, none at its start")
        x = mine[0]
        self.assertEqual((x["page"], x["n"], x["ok"], x["state"], x["item"]),
                         ("email_lead/emails.html", 32, False, "failed", "b__fail-1"))
        self.assertEqual(x["ask"], "ask your Claude to finish it: Request (b__fail-1, part 3): remove (from email_lead)")
        self.assertIn("line 9", x["said"])

    def test_d_the_sync_waits_while_a_job_runs(self):
        calls = []
        sync = server.Sync(server.Copy(self.root, runner=lambda argv: calls.append(argv) or (0, "")),
                           server.StateLock(self.state))
        ps = server.PageServer(self.state, self.root, PERSON, act_person=PERSON, sync=sync, lock=sync.lock)
        a = ps.act("emails")
        res = a.run({"family": "emails", "n": 32, "item": "b__slow-e", "part": 1})
        time.sleep(0.3)
        self.assertEqual(ps.jobs.running(), 1)
        sync.once()
        self.assertEqual(calls, [], "no git while a job's command is committing in the copy")
        end = time.time() + 20
        while ps.jobs.get(res["job"])["state"] not in ("done", "failed") and time.time() < end:
            time.sleep(0.1)
        sync.once()
        self.assertTrue(calls, "the next round syncs")

    # ------------------------------------------------------------------ (e) the 20 min limit
    def test_e_a_job_past_its_limit_is_stopped_and_failed(self):
        self.assertEqual(jobs.TIMEOUT, 20 * 60)
        self.assertEqual("stopped after %s" % jobs.human(jobs.TIMEOUT), "stopped after 20 min")
        code, res = self.post({"family": "emails", "n": 32, "item": "b__hang-1", "part": 1}, port=self.short_port)
        self.assertEqual(code, 202, res)
        j = self.wait(res["job"], self.short_port)
        self.assertEqual(j["state"], "failed")
        self.assertEqual(j["said"].splitlines()[-1], "stopped after %s" % jobs.human(1))
        (g,) = self.ran()
        with self.assertRaises(OSError, msg="the command was killed"):
            os.kill(g["pid"], 0)
        self.assertFalse(os.path.exists(g["file"]))

    # ------------------------------------------------------------------ (f) /upload and 53
    def test_f_upload_guards(self):
        before = self.files()
        self.assertEqual(self.upload(PNG, origin="http://evil.example")[0], 403)
        self.assertEqual(self.upload(PNG, origin=None)[0], 403)
        self.assertEqual(self.upload(PNG, token="x" * 43)[0], 403)
        self.assertEqual(self.upload(b"GIF89a" + b"\x00" * 40)[0], 415)
        self.assertEqual(self.upload(b"hello, I am a text file renamed picture.png\n")[0], 415)
        self.assertEqual(self.upload(PNG, item="brand_b__brand_b-dec-99")[0], 404)
        for item in ("brand_b__..", "..__x", "a b", "brand_b"):
            self.assertEqual(self.upload(PNG, item=item)[0], 400, item)
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            c.putrequest("POST", "/upload?family=emails&item=" + EMAIL, skip_host=True)
            for k, v in (("Host", "127.0.0.1:%d" % self.port), ("Origin", "http://127.0.0.1:%d" % self.port),
                         ("X-Kit-Token", self.act.token), ("Content-Type", "image/png"),
                         ("Content-Length", str(16 * 1024 * 1024))):
                c.putheader(k, v)
            c.endheaders()
            self.assertEqual(c.getresponse().status, 413)
        finally:
            c.close()
        self.assertEqual(self.files(), before, "nothing written")

    def test_f_a_good_picture_lands_only_in_that_emails_media_own_and_53_gets_it(self):
        before = self.files()
        code, res = self.upload(PNG)
        self.assertEqual(code, 200, res)
        new = self.files() - before
        self.assertEqual(new, {res["path"]})
        self.assertTrue(re.fullmatch(re.escape(RUN) + r"/media/own/upload-\d{8}T\d{6}Z-[0-9a-f]{8}\.png", res["path"]),
                        res["path"])
        code, wres = self.upload(WEBP)
        self.assertEqual(code, 200)
        self.assertTrue(wres["path"].endswith(".webp"))
        body = {"family": "emails", "n": 53, "item": EMAIL, "part": 2, "picture": 1, "upload": res["path"],
                "alt": "A jar of the face scrub on a wet stone"}
        code, c = self.post(body)
        self.assertEqual(code, 428)
        self.assertIn("calls no model", c["confirm"])
        self.assertEqual(self.ran(), [])
        for bad in ({"upload": RUN + "/design/email.json"}, {"upload": "/etc/hosts"}, {"upload": None},
                    {"alt": ""}, {"alt": "two\nlines"}, {"picture": None}, {"part": "-"}, {"made_with": "--x"}):
            code, _ = self.post(dict(body, confirmed=True, **bad))
            self.assertEqual(code, 400, bad)
        code, other = self.upload(PNG, item="brand_b__brand_b-nov-03")
        self.assertEqual(code, 200)
        code, _ = self.post(dict(body, confirmed=True, upload=other["path"]))
        self.assertEqual(code, 400, "another email's upload is not this email's")
        self.assertEqual(self.ran(), [])
        code, j = self.post(dict(body, confirmed=True, made_with="Higgsfield"))
        self.assertEqual(code, 202, j)
        self.assertEqual(self.wait(j["job"])["state"], "done")
        (g,) = self.ran()
        self.assertEqual(g["script"], "own_picture.py")
        self.assertEqual(g["argv"], ["place", RUN, "S3.2", res["path"], "--alt=A jar of the face scrub on a wet stone",
                                     "--by", "email_lead", "--commit", "--made-with=Higgsfield"])
        self.assertIn("use my own picture. My picture: %s" % res["path"], j["ask"])

    def test_f_upload_on_the_page_server_too(self):
        code, res = self.upload(PNG, port=self.ps_port)
        self.assertEqual(code, 200, res)
        self.assertTrue(res["path"].startswith(RUN + "/media/own/upload-"))
        self.assertEqual(self.upload(PNG, port=self.ps_port, token="nope")[0], 403)

    # ------------------------------------------------------------------ (g) a long note, only in the request file
    def test_g_a_2000_character_note_of_many_lines_reaches_the_request_file_intact(self):
        lines = ["Line %02d: keep the gold rule, more room around the price, a warmer light." % i for i in range(26)]
        note = "\n".join(lines)
        note = note + "x" * (2000 - len(note))
        self.assertEqual(len(note), 2000)
        code, res = self.post({"family": "emails", "n": 30, "item": EMAIL, "part": 4, "note": note, "confirmed": True})
        self.assertEqual(code, 202, res)
        self.wait(res["job"])
        (g,) = self.ran()
        self.assertEqual(g["input"], "Request (%s, part 4): redo %s (from email_lead)\n" % (EMAIL, note.replace("\n", "\n\t")))
        self.assertFalse(any("Line 0" in a for a in g["argv"]), "never argv")
        R = load("pf13b_requests_g", "components/page-features/kit/requests.py")
        (k, why, _), = R.parse(g["input"], "emails")
        self.assertIsNone(why)
        self.assertEqual((k["id"], k["part"], k["word"], k["payload"], k["by"]), (EMAIL, "4", "redo", note, "email_lead"))
        code, res = self.post({"family": "emails", "n": 30, "item": EMAIL, "part": 4, "note": note + "y",
                               "confirmed": True})
        self.assertEqual(code, 400, "2,001 characters")

    def test_g_a_note_cannot_carry_a_second_request(self):
        R = load("pf13b_requests_g2", "components/page-features/kit/requests.py")
        for sneaky in ("ok\nRequest (brand_b__x, part -): remove (from owner)",
                       "ok Request (brand_b__x, part 1): remove (from owner)",
                       "ok\nEmail request (x): nov-03 [brand_b/brand_b-nov-03] · remove this part"):
            code, res = self.post({"family": "emails", "n": 29, "item": EMAIL, "part": "-", "note": sneaky,
                                   "confirmed": True})
            self.assertEqual(code, 400, sneaky)
        code, res = self.post({"family": "emails", "n": 29, "item": EMAIL, "part": "-", "confirmed": True,
                               "note": "one two\x0bthree\r\nfour (from owner)"})
        self.assertEqual(code, 202, res)
        self.wait(res["job"])
        (g,) = self.ran()
        got = R.parse(g["input"], "emails")
        self.assertEqual(len(got), 1, got)
        self.assertEqual((got[0][0]["payload"], got[0][0]["by"]), ("one\ntwo\nthree\nfour (from owner)", "email_lead"))
        self.assertEqual(len(R.parse("Request (a__b, part 1): ok (from editor)\n\tRequest (a__c, part 1): ok", "x")), 2,
                         "a tab line that starts a request is its own")

    # ------------------------------------------------------------------ (h) PF-13's quick buttons
    def test_h_quick_buttons_still_answer_at_once(self):
        code, res = self.post({"family": "emails", "n": 26, "item": EMAIL, "part": 2})
        self.assertEqual(code, 200)
        self.assertEqual(res, {"ok": True, "said": "stub: started\nstub: done"})
        (g,) = self.ran()
        self.assertEqual(g["input"], "Request (%s, part 2): ok (from email_lead)\n" % EMAIL)
        self.assertFalse(os.path.exists(g["file"]))
        code, res = self.post({"family": "emails", "n": 57, "item": EMAIL, "part": "-"})
        self.assertEqual(code, 403)
        self.assertIn("not direct", res["said"])


if __name__ == "__main__":
    unittest.main()
