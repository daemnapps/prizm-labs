#!/usr/bin/env python3
"""DQ-8 (act panel): a human act opens a panel, and the panel has a Done button only an assignee or developer may press.

    python3 components/page-features/test_dq8_act_panel.py

    (d) the command and the route, on a fixture workspace:
        1. dev_issues.py done by an assignee writes ONE tasks status record (to done) and the act is gone from
           `acts` on the next read
        2. done by someone neither an assignee nor developer is refused (exit 2), naming why; nothing written
        3. developer may tick any act
        4. dev_queue.py mark <task> done (the page server's argv) runs the same command: REFUSED: with the reason, or
           one record committed by path with a machine-prefixed subject naming no card
        5. kit/serve.py: 26 is a quick "review" entry with the mark "done"; Act.build gives dev_queue.py mark <task>
           done --by <the server's person> [--note=…]; a card id as item is refused; "done" is in the word list and
           no run kind was added (SCRIPTS unchanged)
        6. a priority move shows in the follow-up's history
    (v) the template platform/views/viewers/_templates/dev-queue.html, as it is on disk, in headless Chrome
        (test_pf18e_panel_opens.py's driver), from a stub page server whose POST /act runs the real Act (kit/serve.py)
        and the real dev_queue.py against the fixture workspace:
        1. a real press on an act tile opens the panel: title, the quote and who said it, session, raised by and date,
           who it is for, Urgent, the parent link, latest notes (one per person), the history, Copy for Claude, Done
        2. the parent link opens the parent card's panel; an issue parent goes to its tile
        3. Done by an assignee posts n 26 with the task id, writes one status→done record, and the act leaves the
           board and its panel closes
        4. Done by a non-assignee who is not developer is refused by dev_issues.py, the reason shown on the page, the act
           kept; 5. developer may tick any act
        6. the copy fallback carries the exact command: not served by a page server, and served but failing
        7. the view-as lens turns Done off (no button, read-only words, nothing posted)
        8. an issue tile still has no panel
    (r) at this tree: every open act's panel opens for its assignee with Done, no page exception.
    No Chrome → prints SKIPPED with the reason; exits 0 only when CI_NO_CHROME=1 is set, else 1.

Fixtures are test_dq5_human_acts.py's workspace (a test file) plus the notes and moves below, kept in this file (no
.md fixtures under components/). Stdlib only, Python 3.9. Writes only in temp folders; no network beyond 127.0.0.1.
"""
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import serve  # noqa: E402  kit/serve.py: the page server's POST /act
import test_dq5_human_acts as dq5  # noqa: E402  the fixture workspace with acts
import test_pf18b_review_marks as pf18b  # noqa: E402  git identity for a fixture commit
import test_pf18e_panel_opens as pf18e  # noqa: E402  the Chrome driver

REAL = dq5.REAL
PAGE = dq5.PAGE
DEV_QUEUE = os.path.join(HERE, "dev_queue.py")
TASKS = dq5.TASKS
BUILD_AT = dq5.BUILD_AT
HOOK = ("Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: t => {"
        " window.__copied.push(t); return Promise.resolve(); }}}); window.__copied = []; true")
SCRIPTS_BEFORE = {"requests", "ask", "cq", "own", "review", "statics"}


def comment(root, tid, by, text, at):
    """A tasks comment record on a follow-up (the fold's notes), written as the tasks kind writes it."""
    rec = {"schema": 1, "kind": "tasks", "reviewer": by, "item": tid, "verdict": {"event": "comment", "text": text},
           "notes": "", "created": at, "via": "test"}
    name = "%s--%s--%s--comment.json" % (at.replace("-", "").replace(":", ""), by, tid)
    dq5.pf18.write(root, TASKS + name, json.dumps(rec))


def workspace():
    """dq5's workspace, plus on `plain`: two notes from email_lead (the newer is her latest), one from developer, and an Urgent
    move (so its history has a priority line)."""
    root, ids = dq5.workspace()
    comment(root, ids["plain"], "email_lead", "first look, not yet", "2026-10-30T07:50:00Z")
    comment(root, ids["plain"], "email_lead", "the disk is fine now", "2026-10-30T07:52:00Z")
    comment(root, ids["plain"], "developer", "thanks", "2026-10-30T07:53:00Z")
    code, _out, err = dq5.run(root, "priority", ids["plain"], "--urgent", "--by", "developer", "--now", "2026-10-30T07:55:00Z")
    assert code == 0, err
    return root, ids


def acts_of(root):
    return dict((a["id"], a) for a in dev_queue.build(root, now=BUILD_AT)["acts"])


def cli(root, *argv, **kw):
    """The page server's argv for Done, run with the real dev_queue.py against the fixture workspace."""
    p = subprocess.run([sys.executable, DEV_QUEUE] + list(argv) + ["--root", root] + list(kw.get("tail", ())),
                       capture_output=True, text=True, timeout=120, env=kw.get("env"))
    return p.returncode, p.stdout + p.stderr


class Data(unittest.TestCase):
    """(d)"""

    def setUp(self):
        self.root, self.ids = workspace()

    def tearDown(self):
        shutil.rmtree(self.root, True)

    def test_d1_an_assignee_ticks_it_done(self):
        two = self.ids["two"]
        before = dq5.task_files(self.root)
        code, out, err = dq5.run(self.root, "done", two, "--by", "designer", "--now", "2026-10-30T08:00:00Z")
        self.assertEqual(code, 0, err)
        new = sorted(set(dq5.task_files(self.root)) - set(before))
        self.assertEqual(len(new), 1, "one record")
        with open(os.path.join(self.root, TASKS, new[0]), encoding="utf-8") as fh:
            rec = json.load(fh)
        self.assertEqual((rec["item"], rec["reviewer"], rec["verdict"]["event"], rec["verdict"]["to"]),
                         (two, "designer", "status", "done"))
        self.assertNotIn(two, acts_of(self.root), "gone from acts on the next read")

    def test_d2_anyone_else_is_refused(self):
        plain = self.ids["plain"]
        before = dq5.task_files(self.root)
        code, _out, err = dq5.run(self.root, "done", plain, "--by", "email_lead", "--now", "2026-10-30T08:00:00Z")
        self.assertEqual(code, 2)
        self.assertIn("only an assignee of %s (developer) or developer may tick it done, not email_lead" % plain, err)
        self.assertEqual(dq5.task_files(self.root), before, "nothing written")
        self.assertIn(plain, acts_of(self.root))

    def test_d3_developer_may_tick_any_act(self):
        two = self.ids["two"]
        self.assertEqual(acts_of(self.root)[two]["assignees"], ["email_lead", "designer"])
        code, _out, err = dq5.run(self.root, "done", two, "--by", "developer", "--now", "2026-10-30T08:00:00Z")
        self.assertEqual(code, 0, err)
        self.assertNotIn(two, acts_of(self.root))

    def test_d4_the_page_servers_argv(self):
        plain, card = self.ids["plain"], self.ids["card"]
        code, out = cli(self.root, "mark", plain, "done", "--by", "designer", tail=["--no-commit"])
        self.assertEqual(code, 2, out)
        self.assertIn("REFUSED: only an assignee of %s (developer) or developer may tick it done, not designer. "
                      "Nothing was filed." % plain, out)
        code, out = cli(self.root, "mark", plain, "done", "--by", "developer", "--of", "email_lead", tail=["--no-commit"])
        self.assertEqual(code, 2, out)
        self.assertIn("done takes none", out)
        before = dq5.task_files(self.root)
        code, out = cli(self.root, "mark", card, "done", "--by", "developer", "--note=sent it", env=pf18b.env_for(self.root))
        self.assertEqual(code, 0, out)
        self.assertIn("%s ticked done by developer" % card, out)
        self.assertIn("(committed)", out)
        new = sorted(set(dq5.task_files(self.root)) - set(before))
        self.assertEqual(len(new), 1, "one record")
        with open(os.path.join(self.root, TASKS, new[0]), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["verdict"], {"event": "status", "to": "done", "note": "sent it"})
        subject = dev_queue.git(self.root, "log", "-1", "--format=%s").strip()
        files = dev_queue.git(self.root, "show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(files, [TASKS + new[0]], "committed by path: that record only")
        self.assertTrue(subject.startswith("review: "), "a machine prefix: never Shipped without a card")
        self.assertIn(subject.split(":")[0], dev_queue.MACHINE_PREFIXES)
        self.assertEqual([m for m in dev_queue.ID_RE.findall(subject) if not m.startswith("TSK-")], [],
                         "the subject names no card")
        self.assertNotIn(card, acts_of(self.root))

    def test_d5_the_route_is_the_review_route(self):
        self.assertIn("done", serve.REVIEW_MARKS)
        self.assertEqual(set(serve.SCRIPTS), SCRIPTS_BEFORE, "no new run kind on POST /act")
        self.assertEqual(serve.direct_table("dev-queue", REAL)["26"], {"kind": "quick", "run": "review", "mark": "done"})
        act = serve.Act("dev-queue", root=self.root, person="email_lead")
        two = self.ids["two"]
        argv, line = act.build({"family": "dev-queue", "n": 26, "item": two, "value": ""})
        self.assertIsNone(line)
        self.assertEqual(argv[1:], [os.path.join(self.root, "components/page-features/dev_queue.py"), "mark", two, "done",
                                    "--by", "email_lead"])
        argv, _line = act.build({"family": "dev-queue", "n": 26, "item": two, "value": "finished"})
        self.assertEqual(argv[-1], "--note=finished")
        for bad in ("PF-14", "TSK-1-x"):
            with self.assertRaises(serve.Refused) as e:
                act.build({"family": "dev-queue", "n": 26, "item": bad, "value": ""})
            self.assertEqual(e.exception.code, 400, bad)
        with self.assertRaises(serve.Refused) as e:      # a mark still takes a card id only
            act.build({"family": "dev-queue", "n": 24, "item": two, "value": "x"})
        self.assertEqual(e.exception.code, 400)

    def test_d6_priority_in_the_history(self):
        e = dict((x["id"], x) for x in dev_queue.build(self.root, now=BUILD_AT)["issues"])[self.ids["plain"]]
        self.assertEqual([h["what"] for h in e["history"]], ["raised", "urgent"])
        self.assertEqual(len(e["notes"]), 3)


class Stub(object):
    """127.0.0.1: / is the template (with a kit-token meta unless token=False), /data the fixture board read again
    after every write, POST /act the real kit/serve.py Act as `viewer`, its argv run by the real dev_queue.py against
    the fixture workspace. fail=True answers every /act 500 (a page server that broke)."""

    def __init__(self, page, root, token=True):
        self.root, self.asked, self.viewer, self.fail = root, [], None, False
        self.doc = dev_queue.build(root, now=BUILD_AT)
        if token:
            page = page.replace(b'<meta charset="utf-8">', b'<meta charset="utf-8">\n<meta name="kit-token" content="t">', 1)
        stub = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                path = self.path.split("?")[0]
                stub.asked.append(("GET", path, ""))
                if path == "/":
                    self.answer(200, "text/html; charset=utf-8", page)
                elif path == "/data/dev-queue":
                    self.answer(200, "application/json", json.dumps(dict(stub.doc, viewer=stub.viewer)).encode("utf-8"))
                elif path == "/stamp/dev-queue":
                    self.answer(200, "application/json", b'{"name": "dev-queue", "stamp": [1, 1]}')
                else:
                    self.answer(404, "text/plain", b"no")

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8")
                stub.asked.append(("POST", self.path, body))
                if stub.fail:
                    return self.answer(500, "application/json", b'{"ok": false, "said": "the page server broke"}')
                act = serve.Act("dev-queue", root=stub.root, person=stub.viewer, runner=stub.runner)
                try:
                    code, out = 200, act.run(json.loads(body))
                except serve.Refused as e:
                    code, out = e.code, {"ok": False, "said": e.said}
                if out.get("ok"):
                    stub.doc = dev_queue.build(stub.root, now=BUILD_AT)
                self.answer(code, "application/json", json.dumps(out).encode("utf-8"))

            def answer(self, code, kind, body):
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/" % self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def runner(self, argv):
        assert argv[1].endswith("components/page-features/dev_queue.py") and argv[2] == "mark", argv
        return cli(self.root, *argv[2:], tail=["--no-commit"])

    def posts(self):
        return [json.loads(a[2]) for a in self.asked if a[0] == "POST"]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


PANEL = """(() => {
  const p = document.getElementById('panel'), b = document.getElementById('panel-content');
  const q = s => b.querySelector(s), all = s => Array.from(b.querySelectorAll(s)).map(e => e.textContent);
  const terms = {};
  b.querySelectorAll('dl.detail-list dt').forEach(dt => { terms[dt.textContent] = dt.nextElementSibling.textContent; });
  return {open: p.open, kind: document.getElementById('panel-kind').textContent,
    ref: (q('.panel-ref') || {}).textContent || '', title: (q('.panel-title') || {}).textContent || '',
    quote: (q('.act-quote .quote') || {}).textContent || '', on: (q('.act-parent .card-chip, .act-parent .act-on') || {}).textContent || null,
    chips: all(':scope > .chips .chip'), notes: all('.act-notes li'), history: all('.act-history li'),
    done: b.querySelectorAll('button.done-button').length, copy: b.querySelectorAll('.copy-button').length,
    said: (q('.act-done .mark-said') || {}).textContent || '', text: b.textContent, terms: terms};
})()"""
PRESS = """(() => {
  const b = document.querySelector(%s); if (!b) return null;
  b.scrollIntoView({block: 'center', inline: 'center'});
  const r = b.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2, hit = document.elementFromPoint(x, y);
  return {x: x, y: y, on_top: hit && !b.contains(hit) ? (hit.id || hit.className || hit.tagName) : null};
})()"""


class Views(unittest.TestCase):
    """(v) and (r)"""

    @classmethod
    def setUpClass(cls):
        binary, _why = pf18e.chrome_bin()
        with open(PAGE, "rb") as fh:
            cls.html = fh.read()
        cls.chrome = pf18e.Chrome(binary)
        cls.stub, cls.root = None, None

    @classmethod
    def tearDownClass(cls):
        cls.chrome.quit()
        cls.fresh(None, stop=True)

    @classmethod
    def fresh(cls, viewer, token=True, root=None, stop=False):
        """A new fixture workspace (or `root`) and its stub; the old ones gone."""
        if cls.stub:
            cls.stub.stop()
        if cls.root and cls.root != REAL:
            shutil.rmtree(cls.root, True)
        cls.stub = cls.root = None
        if stop:
            return None
        if root is None:
            cls.root, cls.ids = workspace()
        else:
            cls.root = root
        cls.stub = Stub(cls.html, cls.root, token=token)
        cls.stub.viewer = viewer
        return cls.stub

    def page(self, viewer, token=True, root=None):
        stub = self.fresh(viewer, token, root)
        self.chrome.call("Page.navigate", url=stub.url)
        self.assertTrue(self.chrome.wait("document.readyState === 'complete' && "
                                         "document.getElementById('snapshot').textContent.indexOf('Read') === 0 && "
                                         "document.querySelectorAll('[data-act]').length > 0"),
                        "the board never drew: %s" % self.chrome.exceptions)
        self.chrome.js(HOOK)
        return stub

    def open_act(self, tid):
        aim = self.chrome.js(PRESS % json.dumps('[data-act="%s"] button.act-open' % tid))
        self.assertIsNotNone(aim, "%s has no open button" % tid)
        self.assertIsNone(aim["on_top"], "%s sits over the act tile" % aim["on_top"])
        self.chrome.press(aim["x"], aim["y"])
        got = self.chrome.js(PANEL)
        self.assertTrue(got["open"], "the act panel did not open for %s" % tid)
        return got

    def tearDown(self):
        self.assertEqual(self.chrome.exceptions, [], "no page exception")

    def test_v1_an_act_opens_its_panel(self):
        self.page("developer")
        ids = self.ids
        p = self.open_act(ids["plain"])
        self.assertEqual(p["kind"], "Human act")
        self.assertEqual(p["title"], "Check the Time Machine run")
        self.assertEqual(p["quote"], "“check it” — developer", "the quote and who said it")
        self.assertEqual(p["chips"], ["✋ Human act", "Urgent"])
        self.assertEqual((p["terms"]["For"], p["terms"]["Said by"], p["terms"]["Session"], p["terms"]["Raised by"],
                          p["terms"]["Urgent"], p["terms"]["Task"]), ("developer", "developer", "dq5a01", "developer", "Yes", ids["plain"]))
        self.assertTrue(p["terms"]["Raised"].startswith("30 Oct"), p["terms"]["Raised"])
        self.assertEqual(p["on"], None)
        self.assertIn("No parent", p["text"])
        self.assertEqual(len(p["notes"]), 2, "each person's latest note: %s" % p["notes"])
        self.assertTrue(p["notes"][0].startswith("✎ developer: thanks"), p["notes"])
        self.assertTrue(p["notes"][1].startswith("✎ email_lead: the disk is fine now"), p["notes"])
        self.assertEqual([x.split(":")[0].split("30 Oct")[0] for x in p["history"]], ["Raised", "Marked Urgent"])
        self.assertEqual((p["done"], p["copy"]), (1, 1), "Done and Copy for Claude")
        self.assertTrue(self.chrome.js("document.querySelector('[data-act=\"%s\"]').classList.contains('selected')"
                                       % ids["plain"]))
        self.chrome.js("document.getElementById('panel').close()")   # the panel is modal: a person closes it first
        self.assertTrue(self.chrome.wait("!document.querySelector('[data-act].selected')"), "the act tile lets go")
        two = self.open_act(ids["two"])
        self.assertEqual(two["terms"]["For"], "email_lead & designer")
        self.assertEqual(two["on"], "on: issue %s · Pictures stopped on one Mac" % ids["i"])
        self.assertEqual([a for a in self.stub.asked if a[0] == "POST"], [], "opening a panel writes nothing")

    def test_v2_the_parent_link(self):
        self.page("developer")
        p = self.open_act(self.ids["card"])
        self.assertTrue(p["on"].startswith("on: PF-14"), p["on"])
        self.chrome.js("document.querySelector('#panel-content .act-parent button.card-chip').click()")
        got = self.chrome.js(PANEL)
        self.assertTrue(got["open"])
        self.assertEqual(got["kind"], "Card details")
        self.assertTrue(got["ref"].startswith("PF-14"), got["ref"])
        self.chrome.js("document.getElementById('panel').close()")
        self.open_act(self.ids["two"])
        self.chrome.js("document.querySelector('#panel-content .act-parent a.act-on').click()")
        self.assertFalse(self.chrome.js("document.getElementById('panel').open"), "the panel closes for the issue")
        self.assertTrue(self.chrome.js("document.querySelector('[data-issue=\"%s\"]').classList.contains('selected')"
                                       % self.ids["i"]))

    def done(self):
        self.chrome.js("document.querySelector('#panel-content button.done-button').click()")

    def test_v3_done_by_an_assignee(self):
        stub = self.page("email_lead")
        two = self.ids["two"]
        before = dq5.task_files(self.root)
        self.open_act(two)
        self.done()
        self.assertTrue(self.chrome.wait("document.querySelectorAll('[data-act=\"%s\"]').length === 0" % two),
                        "the act leaves the board")
        self.assertFalse(self.chrome.js("document.getElementById('panel').open"), "its panel closes")
        self.assertEqual(stub.posts(), [{"item": two, "value": "", "family": "dev-queue", "n": 26}])
        new = sorted(set(dq5.task_files(self.root)) - set(before))
        self.assertEqual(len(new), 1)
        with open(os.path.join(self.root, TASKS, new[0]), encoding="utf-8") as fh:
            rec = json.load(fh)
        self.assertEqual((rec["reviewer"], rec["verdict"]["to"]), ("email_lead", "done"))
        self.assertNotIn(two, acts_of(self.root))

    def test_v4_done_by_anyone_else_is_refused(self):
        self.page("designer")
        plain = self.ids["plain"]
        before = dq5.task_files(self.root)
        self.open_act(plain)
        self.done()
        self.assertTrue(self.chrome.wait("document.querySelector('#panel-content .act-done .mark-said').textContent"
                                         ".indexOf('Not saved') === 0"))
        said = self.chrome.js(PANEL)["said"]
        self.assertEqual(said, "Not saved: only an assignee of %s (developer) or developer may tick it done, not designer. "
                               "Nothing was filed." % plain)
        self.assertEqual(self.chrome.js("window.__copied"), [], "a refusal is shown, never copied")
        self.assertEqual(dq5.task_files(self.root), before, "nothing written")
        self.assertTrue(self.chrome.js("document.querySelectorAll('[data-act=\"%s\"]').length > 0" % plain))

    def test_v5_developer_may_tick_any_act(self):
        self.page("developer")
        two = self.ids["two"]
        self.open_act(two)
        self.done()
        self.assertTrue(self.chrome.wait("document.querySelectorAll('[data-act=\"%s\"]').length === 0" % two))
        self.assertNotIn(two, acts_of(self.root))

    def test_v6_the_copy_fallback_carries_the_command(self):
        stub = self.page("developer", token=False)
        plain = self.ids["plain"]
        command = "python3 components/page-features/dev_issues.py done %s --by developer" % plain
        self.open_act(plain)
        self.done()
        self.assertTrue(self.chrome.wait("window.__copied.length > 0"))
        self.assertIn(command, self.chrome.js("window.__copied[0]"))
        self.assertTrue(self.chrome.js(PANEL)["said"].startswith("Not served by a page server"))
        self.assertEqual(stub.posts(), [], "unserved: nothing posted")
        stub = self.page("developer")                           # a fresh workspace: its own task ids
        stub.fail = True
        plain = self.ids["plain"]
        command = "python3 components/page-features/dev_issues.py done %s --by developer" % plain
        self.open_act(plain)
        self.done()
        self.assertTrue(self.chrome.wait("window.__copied.length > 0"))
        self.assertIn(command, self.chrome.js("window.__copied[0]"))
        self.assertIn("Not saved here: the page server broke", self.chrome.js(PANEL)["said"])
        self.assertIn(plain, acts_of(self.root))

    def test_v7_the_lens_turns_done_off(self):
        stub = self.page("developer")
        two = self.ids["two"]
        self.assertEqual(self.open_act(two)["done"], 1, "the positive control: his own view has Done")
        self.chrome.js("document.getElementById('panel').close()")
        self.chrome.js("document.querySelector('button.view-as[data-view=email_lead]').click()")
        p = self.open_act(two)
        self.assertEqual(p["done"], 0, "no Done while looking as email_lead")
        self.assertIn("Read-only: you are looking as email_lead. Back to your own view to tick it done.", p["text"])
        self.assertEqual(stub.posts(), [])

    def test_v8_an_issue_tile_has_no_panel(self):
        self.page("developer")
        i = self.ids["i"]
        self.assertEqual(self.chrome.js("document.querySelectorAll('[data-issue] button.tile-open, [data-issue] "
                                        "button.act-open').length"), 0)
        self.chrome.js("document.querySelector('[data-issue=\"%s\"] .issue-body').click()" % i)
        self.assertFalse(self.chrome.js("document.getElementById('panel').open"), "an issue tile opens nothing")

    def test_r_this_tree(self):
        stub = self.page(None, root=REAL)                  # the team board draws each act once
        self.assertTrue(stub.doc["acts"], "open acts at this tree")
        for a in stub.doc["acts"]:
            p = self.open_act(a["id"])
            self.assertEqual((p["kind"], p["title"], p["done"]), ("Human act", " ".join(a["title"].split()), 1), a["id"])
            self.assertEqual(p["terms"]["For"], " & ".join(stub.doc["people"].get(x, x) for x in a["assignees"]))
            self.chrome.js("document.getElementById('panel').close()")
        self.assertEqual(stub.posts(), [], "reading the tree writes nothing")


def main():
    binary, why = pf18e.chrome_bin()
    if not binary:
        print("SKIPPED: %s; set CHROME_BIN to a Chrome or Chromium binary" % why)
        sys.exit(0 if os.environ.get("CI_NO_CHROME") == "1" else 1)
    unittest.main()


if __name__ == "__main__":
    main()
