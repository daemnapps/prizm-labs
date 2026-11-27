#!/usr/bin/env python3
"""PF-13c (Outlier queue buttons): the outlier-demo family's six direct buttons through kit/serve.py's POST /act onto
creative-queue's cq.py, shadow only, and the template's two modes (served by the kit: the token and /data/queue;
unserved: the demo fixtures).

    python3 components/page-features/kit/test_pf13c_outlier_queue.py

A temp repo holds the real template, its real actions and sources files, and stub cq.py and view.py: the stub cq.py
records its argv, the stub view.py prints a small queue. No network beyond 127.0.0.1, no git, nothing in the real
shadow folder is written.
"""
import http.client
import json
import os
import re
import shutil
import subprocess
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
FAM = "outlier-demo"
PERSON = "developer"
ITEM = "brand_a_flex_brief-0048"
STUB_CQ = r'''import json, os, sys
with open(os.environ["PF13C_LOG"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"script": os.path.basename(__file__), "argv": sys.argv[1:]}) + "\n")
print("stub: done")
'''
QUEUE = {"owner_built": "2026-10-28T12:19:56", "people": ["owner", "editor"], "shadow_root": "runs/queue-shadow",
         "stages": [{"id": "idea", "name": "Teardown"}],
         "rows": [{"id": ITEM, "type": "image-ad", "brand": "brand_a", "title": "Brief 0048", "stage": "making",
                   "removed": False, "read_only": None, "requested_stage": "editing"}]}
STUB_VIEW = "import json\nprint(json.dumps(%r))\n" % (QUEUE,)
SIX = {"14", "16", "17", "58", "59", "60"}


def read(rel, root=REAL):
    with open(os.path.join(root, rel), encoding="utf-8") as fh:
        return fh.read()


def page_stages(html):
    """The stage ids of the page's own word list (FX.queue.words.stages, the board's columns)."""
    line = next(x for x in html.split("\n") if "var FX = window.__DEMO_FX = " in x)
    fx = json.loads(line.split("var FX = window.__DEMO_FX = ", 1)[1].rstrip().rstrip(";"))
    return [s["id"] for s in fx["queue"]["words"]["stages"]]


class OutlierQueue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="pf13c-")
        files = {"components/creative-queue/cq.py": STUB_CQ, "components/creative-queue/view.py": STUB_VIEW}
        for ext in ("html", "actions.json", "sources.json", "features.json"):
            rel = os.path.join(TPL, "%s.%s" % (FAM, ext))
            files[rel] = read(rel)
        files[os.path.join(TPL, "fam-x.actions.json")] = json.dumps(
            {"direct": {"1": {"run": "cq", "verb": "set", "fields": ["requested_stage"]},
                        "2": {"run": "cq", "verbs": ["remove", "approve"]}}})
        for rel, text in files.items():
            p = os.path.join(cls.root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        cls.log = os.path.join(cls.root, "stub-log.jsonl")
        os.environ["PF13C_LOG"] = cls.log
        src = serve.Sources(lambda: serve.sources(FAM, cls.root), root=cls.root)
        cls.act = serve.Act(FAM, cls.root, PERSON)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), serve.handler(
            "_templates/%s.html" % FAM, src, root=cls.root,
            status=serve.Status(cls.root, runner=lambda argv: (0, "0\n")), act=cls.act))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.port = cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.root)

    def setUp(self):
        if os.path.exists(self.log):
            os.unlink(self.log)

    def post(self, body):
        h = {"Host": "127.0.0.1:%d" % self.port, "Origin": "http://127.0.0.1:%d" % self.port,
             "X-Kit-Token": self.act.token, "Content-Type": "application/json"}
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            c.request("POST", "/act", body=json.dumps(body), headers=h)
            r = c.getresponse()
            return r.status, json.loads(r.read().decode())
        finally:
            c.close()

    def get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            c.request("GET", path, headers={"Host": "127.0.0.1:%d" % self.port})
            r = c.getresponse()
            return r.status, r.read().decode()
        finally:
            c.close()

    def ran(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]

    def body(self, n, field=None, value=None, item=ITEM):
        b = {"family": FAM, "n": n, "item": item}
        if field is not None:
            b["field"] = field
        if value is not None:
            b["value"] = value
        return b

    # ------------------------------------------------------------------ each of the six, exact argv, never --root
    def test_the_six_run_cq_with_the_exact_argv(self):
        cases = [
            (self.body(14, "requested_stage", "editing"), ["set", ITEM, "requested_stage", "editing"]),
            (self.body(16, "requested_stage", "launch"), ["set", ITEM, "requested_stage", "launch"]),
            (self.body(16, "requested_stage", "making"), ["set", ITEM, "requested_stage", "making"]),   # a restart
            (self.body(17, "who", "editor"), ["set", ITEM, "who", "editor"]),
            (self.body(17, "who", ""), ["set", ITEM, "who", ""]),
            (self.body(58, "title_set", "Flex brief 48, the gold one"), ["set", ITEM, "title_set", "Flex brief 48, the gold one"]),
            (self.body(59, "priority", "top"), ["set", ITEM, "priority", "top"]),
            (self.body(60, "remove"), ["remove", ITEM]),
            (self.body(60, "restore"), ["restore", ITEM]),
        ]
        for b, _ in cases:
            code, res = self.post(b)
            self.assertEqual((code, res), (200, {"ok": True, "said": "stub: done"}), b)
        got = self.ran()
        self.assertEqual([g["argv"] for g in got], [want + ["--by", PERSON] for _, want in cases])
        for g in got:
            self.assertEqual(g["script"], "cq.py")
            self.assertFalse(any(a == "--root" or a.startswith("--root=") for a in g["argv"]), g["argv"])

    def test_a_body_asking_for_root_still_runs_shadow_only(self):
        b = dict(self.body(59, "priority", "low"), root="runs/queue", args={"root": "runs/queue"})
        self.assertEqual(self.post(b)[0], 200)
        self.assertEqual(self.ran()[0]["argv"], ["set", ITEM, "priority", "low", "--by", PERSON])

    # ------------------------------------------------------------------ refusals, before anything runs
    def test_the_cast_shelf_looks_good_and_script_lines_are_not_direct(self):
        for n in (25, 26, 55, 31, 57):
            code, res = self.post(self.body(n, "who", "editor"))
            self.assertEqual(code, 403, n)
            self.assertIn("not direct", res["said"])
        self.assertEqual(self.ran(), [])

    def test_a_stage_outside_the_page_list_is_400(self):
        for n in (14, 16):
            for value in ("shipped", "", "Live", "live ", "making|live", "brief-needs-you\n", "--root"):
                code, _ = self.post(self.body(n, "requested_stage", value))
                self.assertEqual(code, 400, (n, value))
            for field, value in (("who", "editor"), (None, "live"), ("stage", "live")):
                code, _ = self.post(self.body(n, field, value))
                self.assertEqual(code, 400, (n, field))
        self.assertEqual(self.ran(), [])

    def test_bad_values_and_fields_are_400(self):
        for b in (self.body(59, "priority", "urgent"), self.body(59, "priority", "2"),
                  self.body(17, "who", "--root=runs/queue"), self.body(17, "who", "editor; rm"),
                  self.body(58, "title_set", "a\nb"), self.body(58, "title_set", "x" * 201),
                  self.body(58, "priority", "top"), self.body(60, "remove", "yes"), self.body(60, "approve"),
                  self.body(60), self.body(60, "remove", item="a b")):
            code, _ = self.post(b)
            self.assertEqual(code, 400, b)
        self.assertEqual(self.ran(), [])

    def test_requested_stage_without_a_stage_list_and_unknown_verbs_are_not_direct(self):
        act = serve.Act("fam-x", self.root, PERSON)
        for b in ({"family": "fam-x", "n": 1, "item": ITEM, "field": "requested_stage", "value": "live"},
                  {"family": "fam-x", "n": 2, "item": ITEM, "field": "approve"}):
            with self.assertRaises(serve.Refused) as e:
                act.build(b)
            self.assertEqual(e.exception.code, 403, b)
        self.assertEqual(act.build({"family": "fam-x", "n": 2, "item": ITEM, "field": "remove"})[0][2:],
                         ["remove", ITEM, "--by", PERSON])

    # ------------------------------------------------------------------ the tables
    def test_the_real_table_is_the_six_and_the_page_stage_list(self):
        t = serve.direct_table(FAM, REAL)
        self.assertEqual(set(t), SIX)
        self.assertTrue(all(d["run"] == "cq" for d in t.values()))
        stages = page_stages(read(os.path.join(TPL, "%s.html" % FAM)))
        self.assertEqual(stages, ["idea", "brief", "brief-needs-you", "making", "editing", "final-needs-you",
                                  "launch", "live"])
        for n in ("14", "16"):
            self.assertEqual(t[n]["fields"], ["requested_stage"])
            self.assertEqual(t[n]["values"]["requested_stage"].split("|"), stages, "the page's own stage list")
        self.assertEqual(t["60"]["verbs"], ["remove", "restore"])
        for n in ("25", "26", "55"):
            self.assertNotIn(n, t)
        with open(os.path.join(REAL, TPL, "%s.actions.json" % FAM), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["status"], "draft")

    def test_requests_py_tolerates_the_new_actions_file(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pf13c_requests", os.path.join(HERE, "requests.py"))
        R = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(R)
        self.assertEqual(R.only_family(), "emails")

    # ------------------------------------------------------------------ served: the token and /data/queue
    def test_served_page_carries_the_token_above_the_shim_and_loads_data_queue(self):
        code, text = self.get("/p/_templates/%s.html" % FAM)
        self.assertEqual(code, 200)
        meta = '<meta name="kit-token" content="%s">' % self.act.token
        self.assertEqual(text.count(meta), 1)
        self.assertLess(text.index(meta), text.index('<script id="demo-shim">'), "the shim reads the token")
        self.assertIn('KIT?get("/data/queue").then(kitQueue):get("/api/queue")', text)
        self.assertIn('"X-Kit-Token": t', text)          # PF-15 (direct by default): the header is act.js's now
        self.assertIn('pfAct(n,{item,field,value:value??""},{family:"outlier-demo"', text)
        code, data = self.get("/data/queue")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(data), QUEUE)

    def test_the_real_source_is_creative_queues_read_door(self):
        d = serve.sources(FAM, REAL)
        self.assertEqual(d["queue"]["argv"], ["components/creative-queue/view.py"])
        self.assertTrue(os.path.isfile(os.path.join(REAL, "components/creative-queue/view.py")))
        self.assertFalse(any("--root" in a for a in d["queue"]["argv"]))
        self.assertEqual(serve.preflight(d), [])
        self.assertEqual(serve.runs_prefixes(d), [], "no /runs/ for this family")

    # ------------------------------------------------------------------ unserved: the demo stays (static)
    def test_unserved_keeps_the_fixtures_and_the_demo_answers(self):
        html = read(os.path.join(TPL, "%s.html" % FAM))
        self.assertNotIn('<meta name="kit-token"', html, "the file on disk carries no token")
        self.assertIn('var KIT = document.querySelector(\'meta[name="kit-token"]\');', html)
        self.assertIn('if (KIT && realFetch && /^\\/(?!\\/)/.test(raw) && (p === "/act" || p === "/data/queue")) '
                      'return realFetch(input, opts);', html)
        self.assertIn('"/api/queue": FX.queue', html)
        self.assertIn('const KIT=document.querySelector(\'meta[name="kit-token"]\')?.content||"";', html)
        for demo in ('qpost("/api/queue/remove",{id:x.id})', 'qpost("/api/queue/remove",{id:x.id,undo:true})',
                     'qpost("/api/queue/meta",{id:x.id,priority:b.dataset.prio})', 'fetch("/api/queue/advance"',
                     'qpost("/api/queue/restart",{id:x.id})', 'fetch("/api/queue/assign"'):
            self.assertIn(demo, html, "the demo branch stays")
        main = html.split('<script>', 1)[1]
        ns = set(re.findall(r"kitAct\((\d+),", main)) | set(re.findall(r"kitMove\(x,(\d+)\)", main)) \
            | set(re.findall(r"moveOn\(id,null,(\d+)\)", main)) | set(re.findall(r"kitMove\(x,n\|\|(\d+)\)", main))
        self.assertEqual(ns, SIX, "the page posts exactly the table's numbers")
        for n in ("25", "26", "55"):
            self.assertNotIn("kitAct(%s," % n, html)
        for m in re.finditer(r"KIT\?await (kit\w+)\(", main):
            self.assertIn(m.group(1), ("kitAct", "kitMove"))

    # ------------------------------------------------------------------ js-parse
    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_js_parse_stays_at_zero_failures(self):
        p = subprocess.run(["node", os.path.join(REAL, TPL, "js-parse.test.mjs")], capture_output=True, text=True,
                           timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn(" 0 failure(s)", p.stdout)


if __name__ == "__main__":
    unittest.main()
