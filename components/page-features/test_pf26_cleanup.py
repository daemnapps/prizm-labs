#!/usr/bin/env python3
"""PF-26 (page-family cleanup): one test per fix built — (1) 503 "starting" then 200, and the page's retry; (2) status
names the identity port while off; (3) no machine path in the run-detail template; (6) the pf18c dry-run `card` runs
on a fixed clock. Fixes (4) and (5) were not built (dropped; PF-26b (emails catalog regenerate)).

    python3 components/page-features/test_pf26_cleanup.py

Every fixture is made here, in temp folders; no git, no network. (1)'s retry runs in node, skipped where there is none.
"""
import contextlib
import http.client
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REAL = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "kit"))
import serve  # noqa: E402
import server  # noqa: E402

PERSON = "tess"
TPL = "platform/views/viewers/_templates/"


def write(root, rel, text):
    p = os.path.join(str(root), rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


class SettlingSync(object):
    """A sync whose first round lands the family's sources in the copy, as a pull right after a restart does."""

    def __init__(self, root):
        self.root, self.restart, self.hold, self.before = root, threading.Event(), None, None
        self.last = {"at": None, "ok": None, "said": "not synced yet", "ahead": None, "behind": None, "good_at": None}

    def once(self):
        write(self.root, TPL + "alpha.sources.json", json.dumps({"x": {"argv": ["components/alpha/ok.py"]}}))
        write(self.root, "components/alpha/ok.py", "print('[{\"ok\": 1}]')\n")
        self.last = dict(self.last, ok=True, said="pulled")
        return dict(self.last)


class Fix1Starting(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pf26-")).resolve()
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.root, self.state = self.tmp / "repo", self.tmp / "state"
        write(self.root, "components/.keep", "")
        self.state.mkdir()

    def get(self, port, path):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        try:
            c.request("GET", path, headers={"Host": "127.0.0.1:%d" % port})
            r = c.getresponse()
            return r.status, r.read().decode()
        finally:
            c.close()

    def test_1_data_is_503_starting_until_the_first_sync_then_200(self):
        srv = server.PageServer(self.state, self.root, PERSON, sync=SettlingSync(self.root))
        httpd = server.Server(("127.0.0.1", 0), srv.handler())
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        port = httpd.server_address[1]
        self.assertEqual(self.get(port, "/data/x"), (503, "starting"), "sources not loaded yet: starting, never 404")
        stop = threading.Event()
        t = threading.Thread(target=srv.loop, args=(stop, 3600), daemon=True)
        t.start()
        self.assertTrue(srv.loaded.wait(10), "the first sync round finished")
        stop.set()
        t.join(10)
        self.assertEqual(self.get(port, "/data/x"), (200, '[{"ok": 1}]\n'))
        self.assertEqual(self.get(port, "/data/nope"), (404, "no data source called nope"), "a real unknown stays 404")
        srv.sync.restart.set()                            # a pull changed the kit: starting again until `run` exits
        self.assertEqual(self.get(port, "/data/nope")[0], 503)

    def test_1_the_page_asks_a_503_again_and_leaves_other_fetches_alone(self):
        page = serve.with_token(b"<html><head><title>t</title></head><body></body></html>", "tok").decode()
        self.assertIn('<head>\n<meta name="kit-token" content="tok">\n' + serve.DATA_RETRY, page)
        self.assertLess(page.index(serve.DATA_RETRY), page.index("<title>"), "before any page script")
        node = shutil.which("node")
        if not node:
            self.skipTest("no node here: the retry script's behaviour is not run")
        js = serve.DATA_RETRY[len("<script>"):-len("</script>")]
        harness = (
            "const seen=[];let n503=2;globalThis.setTimeout=(f)=>Promise.resolve().then(f);"
            "const window={location:{href:'http://127.0.0.1:9/v/x.html',origin:'http://127.0.0.1:9'},"
            "fetch:(u)=>{seen.push(String(u));const s=String(u).indexOf('/data/')>=0&&n503-->0?503:"
            "(String(u).indexOf('/stamp/')>=0?503:200);return Promise.resolve({status:s})}};"
            + js + ";(async()=>{const a=await window.fetch('/data/x');const b=await window.fetch('/stamp/x');"
            "const c=await window.fetch('/data/x',{method:'POST'});"
            "console.log(JSON.stringify({a:a.status,b:b.status,c:c.status,seen}))})()")
        p = subprocess.run([node, "-e", harness], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout)
        self.assertEqual((got["a"], got["b"], got["c"]), (200, 503, 200))
        self.assertEqual(got["seen"], ["/data/x"] * 3 + ["/stamp/x", "/data/x"],
                         "a /data GET asked again after each 503; /stamp and a POST once")


class Fix2StatusPort(unittest.TestCase):
    def test_2_status_while_off_names_the_identity_port_not_config_json(self):
        tmp = Path(tempfile.mkdtemp(prefix="pf26-status-")).resolve()
        self.addCleanup(shutil.rmtree, str(tmp), True)
        repo, state = tmp / "repo", tmp / "state"
        write(repo, "team/people/%s/identity.json" % PERSON, json.dumps({"page_server_port": 8740}))
        write(state, "config.json", json.dumps({"person": PERSON, "repo": str(repo), "port": 8766}))
        agent = mock.Mock(platform="darwin")
        agent.status.return_value = {"loaded": False, "pid": None}
        out = io.StringIO()
        with mock.patch.object(server, "locate", return_value=(PERSON, str(state))), contextlib.redirect_stdout(out):
            code = server.cmd_status(repo, agent, server.run_cmd)
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("page server: off (port 8740, fixed)", out.getvalue())
        self.assertNotIn("8766", out.getvalue(), "config.json's last port is not the address")


class Fix3RunDetailPath(unittest.TestCase):
    def test_3_the_run_detail_template_holds_no_machine_drive_path(self):
        with open(os.path.join(REAL, TPL, "run-detail.html"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual([m.group(0) for m in re.finditer(r"/var/folders/\S*|\S*/upright-drive/", text)], [],
                         "builder-card rule 4: a 'Shared Assets/…' label, never a mount path")


class Fix6FixedClock(unittest.TestCase):
    def test_6_the_pf18c_dry_run_card_runs_on_a_clock_later_than_its_fixture(self):
        f = os.path.join(HERE, "test_pf18c_issue_queue.py")
        with open(f, encoding="utf-8") as fh:
            text = fh.read()
        line = [x for x in text.splitlines() if '"card"' in x and '"--dry-run"' in x]
        self.assertEqual(len(line), 1, line)
        now = re.search(r'"--now", "([0-9TZ:-]+)"', line[0])
        self.assertTrue(now, "the dry-run card names --now")
        moves = re.findall(r'"(2026-\d\d-\d\dT\d\d:\d\d:\d\dZ)"', text.replace(line[0], ""))
        self.assertGreater(now.group(1), max(moves), "later than the fixture's last move")
        p = subprocess.run([sys.executable, "-m", "unittest", "-q", "test_pf18c_issue_queue.Moves.test_d_refused_moves"],
                           cwd=HERE, capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
