#!/usr/bin/env python3
"""PF-19 (behind notice): a live page that has fallen behind its team template says so, and its direct buttons fall
back to copying a request for Claude while its family's actions.json has changed since it went live.

    python3 components/page-features/test_pf19_behind_notice.py

    (a) a live page on an old base: PF-8 (show my pages)'s list carries "behind" — the line, the date of the first
        template commit after the base, the subjects since it (newest first, none from before the base) — and
        render() prints them; the page server's strip on /, /plain's status and /data/home say the same line
    (b) a page at the current base shows nothing: no "behind" in the list, the render, the strip or /data/home
    (c) a changed actions.json turns that live page's direct buttons into copy-a-request: /act 403 with the why and
        stale_actions, nothing run, the click line "refused"; an unchanged one, a draft, a template and a line from
        before PF-19 stay direct; made live again (a new line with the blob now) is direct again; serve.py's one-page
        kit refuses the same way
    (d) go_live and first_open record the blob of the family's actions.json; validate_live_log takes a line without
        it and refuses one whose blob is not a sha

Every fixture is built here, in temp folders (a git repo for (a)–(b), never pushed). Stdlib only, Python 3.9. No
network beyond 127.0.0.1.
"""
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import draft  # noqa: E402
import features  # noqa: E402
import live  # noqa: E402
import pages  # noqa: E402
import serve  # noqa: E402
import server  # noqa: E402

PERSON = "tess"
V = "platform/views/viewers/"
TPL = V + "_templates/"
PAGE_REL = "tess/alpha.html"
LIVE_PAGE = V + PAGE_REL
RECORD = V + "tess/alpha.live.jsonl"
PAGE = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n</head>\n'
        '<body><h1 data-feature="1">alpha</h1>%s</body>\n</html>\n')
SET = {"kind": "quick", "run": "cq", "verb": "set", "fields": ["who"]}
ACTIONS = json.dumps({"direct": {"5": SET}}, indent=2) + "\n"
ACTIONS_NEW = json.dumps({"direct": {"5": dict(SET, fields=["who", "due"])}}, indent=2) + "\n"
BODY = {"family": "alpha", "n": 5, "item": "x1", "field": "who", "value": "editor"}
LINE = "Your page is behind the team version since 2026-10-24 — say 'catch up my alpha page'"


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def git(root, *args, date=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@x.test", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@x.test")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    p = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    return p.stdout


def commit(root, subject, date):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", subject, date=date)


def record(root, base, actions="absent", at="2026-10-22T09:00:00Z"):
    """One live line for tess's alpha page, appended; actions "absent" writes a line from before PF-19."""
    line = {"kind": "live", "at": at, "by": PERSON, "from": V + "tess/drafts/alpha--try.html", "base": base,
            "old": None, "changes": 0}
    if actions != "absent":
        line["actions"] = actions
    with open(os.path.join(root, RECORD), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(line) + "\n")


def strip_of(text):
    """The words of the one strip the page server put on a page at /."""
    at = text.index(server.STRIP_MARK)
    return text[at:text.index("</template>", at)]


def live_of(result, family="alpha"):
    return next(f for f in result["families"] if f["family"] == family)["live"]


class Repo(unittest.TestCase):
    """A temp git repo: the alpha template in three commits, tess's live page cut from the second."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pf19-")
        self.addCleanup(shutil.rmtree, self.root, True)
        git(self.root, "init", "-q")
        write(self.root, TPL + "alpha.features.json", json.dumps({"owner": "email_lead"}))
        write(self.root, TPL + "alpha.actions.json", ACTIONS)
        write(self.root, TPL + "alpha.html", PAGE % "<p>one</p>")
        commit(self.root, "alpha: the first template", "2026-10-20T08:00:00Z")
        write(self.root, TPL + "alpha.html", PAGE % "<p>two</p>")
        commit(self.root, "alpha: the base tess cut from", "2026-10-21T08:00:00Z")
        self.base = live.blob_id(os.path.join(self.root, TPL + "alpha.html"))
        write(self.root, LIVE_PAGE, PAGE % "<p>two</p>")
        record(self.root, self.base, live.actions_blob("alpha", self.root))
        write(self.root, "team/people/tess/identity.json", json.dumps({"page_server_port": 18749}))
        commit(self.root, "page: live alpha (tess)", "2026-10-22T09:00:00Z")
        self.state = tempfile.mkdtemp(prefix="pf19-state-")
        self.addCleanup(shutil.rmtree, self.state, True)

    def move_template(self):
        write(self.root, TPL + "alpha.html", PAGE % "<p>three</p>")
        commit(self.root, "alpha: a new column", "2026-10-24T08:00:00Z")
        write(self.root, TPL + "alpha.html", PAGE % "<p>four</p>")
        commit(self.root, "alpha: the column renamed", "2026-10-26T08:00:00Z")

    def listed(self):
        return pages.list_pages(person=PERSON, root=self.root, runner=features.run_git)

    def served(self):
        srv = server.PageServer(self.state, self.root, PERSON, act_person=PERSON)
        httpd = server.Server(("127.0.0.1", 0), srv.handler())
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        return srv, httpd.server_address[1]

    def get(self, port, path):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
        try:
            c.request("GET", path, headers={"Host": "127.0.0.1:%d" % port})
            r = c.getresponse()
            return r.status, r.read().decode("utf-8")
        finally:
            c.close()

    # (a)
    def test_a_an_old_base_shows_the_line_and_the_commits(self):
        self.move_template()
        page = live_of(self.listed())
        self.assertEqual(page["drift"], "yes")
        self.assertEqual(page["behind"], {"since": "2026-10-24", "line": LINE,
                                          "commits": ["alpha: the column renamed", "alpha: a new column"]},
                         "subjects only, newest first, none from before the base")
        lines = pages.render(self.listed())
        pad = " " * 12
        at = lines.index(pad + LINE)
        self.assertEqual(lines[at:at + 4], [pad + LINE, pad + "team commits since your base: 2",
                                            pad + "  alpha: the column renamed", pad + "  alpha: a new column"])
        self.assertIsNone(page["buttons"], "the actions did not change: the buttons stay direct")

    def test_a_the_strip_plain_and_the_home_page_say_the_same_line(self):
        self.move_template()
        srv, port = self.served()
        code, text = self.get(port, "/")
        self.assertEqual(code, 200)
        inside = strip_of(text)
        self.assertIn(LINE.replace("'", "&#x27;"), inside, "the strip on / names it")
        code, text = self.get(port, server.PLAIN)
        self.assertIn('<p class="st" id="status">', text)
        self.assertIn(LINE.replace("'", "&#x27;"), text.split('id="status">')[1].split("</p>")[0])
        code, text = self.get(port, server.DATA_HOME)
        d = json.loads(text)
        self.assertIn(LINE, d["status_line"], "the home page's status line")
        (b,) = d["pages_behind"]
        self.assertEqual((b["family"], b["path"], b["line"], b["commits"]),
                         ("alpha", LIVE_PAGE, LINE, ["alpha: the column renamed", "alpha: a new column"]))

    def test_a_the_strip_on_a_home_template_is_fresh_on_first_load(self):
        self.move_template()
        write(self.root, TPL + "home.html", PAGE % "<p>home</p>")
        srv, port = self.served()
        code, text = self.get(port, "/")
        self.assertEqual(code, 200)
        self.assertIn("<p>home</p>", text)
        self.assertIn(LINE.replace("'", "&#x27;"), strip_of(text))

    # (b)
    def test_b_a_page_at_the_current_base_shows_nothing(self):
        page = live_of(self.listed())
        self.assertEqual(page["drift"], "no")
        self.assertIsNone(page["behind"])
        self.assertFalse([x for x in pages.render(self.listed()) if "behind" in x or "team commits" in x])
        srv, port = self.served()
        for route in ("/", server.PLAIN):
            self.assertNotIn("behind the team version", self.get(port, route)[1], route)
        d = json.loads(self.get(port, server.DATA_HOME)[1])
        self.assertEqual(d["pages_behind"], [])
        self.assertNotIn("behind the team version", d["status_line"])

    def test_b_a_base_its_history_never_wrote_names_no_commits(self):
        with open(os.path.join(self.root, RECORD), "w", encoding="utf-8") as fh:
            fh.write("")
        record(self.root, "f" * 40, live.actions_blob("alpha", self.root))
        result = self.listed()
        page = live_of(result)
        self.assertEqual(page["behind"], {"since": None, "commits": [],
                                          "line": "Your page is behind the team version — say 'catch up my "
                                                  "alpha page'"})
        self.assertTrue(any("never wrote the base ffffffffffff" in n for n in result["notes"]), result["notes"])
        self.assertIn(" " * 12 + "team commits since your base: none found", pages.render(result))


class Buttons(unittest.TestCase):
    """(c) one page server over a temp root (no git), its act runner a recorder."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pf19-act-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.state = tempfile.mkdtemp(prefix="pf19-act-state-")
        self.addCleanup(shutil.rmtree, self.state, True)
        write(self.root, TPL + "alpha.actions.json", ACTIONS)
        write(self.root, TPL + "alpha.html", PAGE % "")
        write(self.root, LIVE_PAGE, PAGE % "")
        write(self.root, V + "tess/drafts/alpha--try.html", PAGE % "")
        self.ran = []
        self.srv = server.PageServer(self.state, self.root, PERSON, act_person=PERSON,
                                     act_runner=lambda argv: self.ran.append(list(argv)) or (0, "ran"))
        httpd = server.Server(("127.0.0.1", 0), self.srv.handler())
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        self.port = httpd.server_address[1]

    def post(self, referer, body=None):
        h = {"Host": "127.0.0.1:%d" % self.port, "Origin": "http://127.0.0.1:%d" % self.port,
             "X-Kit-Token": self.srv.token, "Content-Type": "application/json",
             "Referer": "http://127.0.0.1:%d%s" % (self.port, referer)}
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            c.request("POST", "/act", body=json.dumps(body or BODY), headers=h)
            r = c.getresponse()
            return r.status, json.loads(r.read().decode())
        finally:
            c.close()

    def clicks(self):
        p = os.path.join(self.state, "clicks.jsonl")
        with open(p, encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]

    def change_actions(self):
        write(self.root, TPL + "alpha.actions.json", ACTIONS_NEW)

    def test_c_unchanged_actions_leave_the_buttons_direct(self):
        record(self.root, None, live.actions_blob("alpha", self.root))
        code, res = self.post("/v/" + PAGE_REL)
        self.assertEqual((code, res["ok"]), (200, True), res)
        self.assertEqual(self.ran[0][2:], ["set", "x1", "who", "editor", "--by", PERSON])
        self.assertIsNone(live.stale_actions(PAGE_REL, self.root))

    def test_c_changed_actions_turn_the_buttons_into_copy_a_request(self):
        record(self.root, None, live.actions_blob("alpha", self.root))
        self.change_actions()
        code, res = self.post("/v/" + PAGE_REL)
        self.assertEqual(code, 403, res)
        self.assertFalse(res["ok"])
        self.assertTrue(res["stale_actions"])
        self.assertEqual(res["said"], "ask your Claude: " + live.STALE_ACTIONS % ("2026-10-22", "alpha"))
        self.assertIn("say 'catch up my alpha page'", res["said"], "it says why and what to say")
        self.assertNotEqual(res.get("status"), 409, "409 is the one answer act.js never copies")
        self.assertEqual(self.ran, [], "nothing run")
        (c,) = self.clicks()
        self.assertEqual((c["page"], c["ok"], server.click_word(c)), (PAGE_REL, False, "refused"))
        self.assertEqual(live.stale_actions(LIVE_PAGE, self.root), live.stale_actions(PAGE_REL, self.root),
                         "the repo-relative path and the page server's own form agree")

    def test_c_a_draft_a_template_and_a_line_from_before_stay_direct(self):
        self.change_actions()
        record(self.root, None)                                       # no "actions": went live before PF-19
        for page in ("/v/" + PAGE_REL, "/v/tess/drafts/alpha--try.html", "/p/_templates/alpha.html"):
            code, res = self.post(page)
            self.assertEqual((code, res["ok"]), (200, True), (page, res))
        self.assertEqual(len(self.ran), 3)
        record(self.root, None, "0" * 40)                             # a recorded blob that is not today's
        code, res = self.post("/v/tess/drafts/alpha--try.html")
        self.assertEqual(code, 200, "a draft is never held back")
        code, res = self.post("/v/" + PAGE_REL)
        self.assertEqual(code, 403, res)

    def test_c_made_live_again_is_direct_again(self):
        record(self.root, None, live.actions_blob("alpha", self.root))
        self.change_actions()
        self.assertEqual(self.post("/v/" + PAGE_REL)[0], 403)
        record(self.root, None, live.actions_blob("alpha", self.root), at="2026-10-29T09:00:00Z")
        code, res = self.post("/v/" + PAGE_REL)
        self.assertEqual((code, res["ok"]), (200, True), res)
        self.assertEqual(len(self.ran), 1)

    def test_c_the_family_with_no_actions_file(self):
        record(self.root, None, live.actions_blob("alpha", self.root))
        self.assertIsNotNone(live.actions_blob("alpha", self.root))
        os.remove(os.path.join(self.root, TPL + "alpha.actions.json"))
        self.assertIsNone(live.actions_blob("alpha", self.root))
        self.assertIn("catch up my alpha page", live.stale_actions(PAGE_REL, self.root),
                      "the run table it went live with is gone: not today's")

    def test_c_the_list_says_why_the_buttons_copy(self):
        record(self.root, None, live.actions_blob("alpha", self.root))
        self.change_actions()
        write(self.root, TPL + "alpha.features.json", json.dumps({"owner": "email_lead"}))
        result = pages.list_pages(person=PERSON, root=self.root, runner=lambda argv, cwd: (0, "", ""))
        self.assertEqual(live_of(result)["buttons"], live.STALE_ACTIONS % ("2026-10-22", "alpha"))
        self.assertIn(" " * 12 + "buttons: " + live_of(result)["buttons"], pages.render(result))

    def test_c_serve_one_page_kit_refuses_the_same_way(self):
        record(self.root, None, live.actions_blob("alpha", self.root))
        self.change_actions()
        ran = []
        act = serve.Act("alpha", self.root, PERSON, runner=lambda argv: ran.append(argv) or (0, "ran"))
        serve.handler(PAGE_REL, serve.Sources({}, root=self.root), root=self.root, act=act)
        self.assertEqual(act.page, PAGE_REL, "handler names the one page it serves")
        with self.assertRaises(serve.Refused) as got:
            act.run(dict(BODY, _page="tess/drafts/alpha--try.html"))
        self.assertEqual(got.exception.code, 403)
        self.assertIn("catch up my alpha page", got.exception.said, "the body cannot name another page")
        self.assertEqual(ran, [])
        draft = serve.Act("alpha", self.root, PERSON, runner=lambda argv: ran.append(argv) or (0, "ran"))
        serve.handler("tess/drafts/alpha--try.html", serve.Sources({}, root=self.root), root=self.root, act=draft)
        self.assertTrue(draft.run(dict(BODY))["ok"])
        self.assertEqual(len(ran), 1)


class Records(unittest.TestCase):
    """(d) the new field in the live.jsonl line."""

    def test_d_validate_takes_a_line_without_it_and_refuses_a_bad_one(self):
        good = {"kind": "live", "at": "2026-10-29T09:00:00Z", "by": PERSON, "from": None, "base": None,
                "old": None, "changes": 0}
        self.assertEqual(live.validate_live_log([good, dict(good, actions=None), dict(good, actions="a" * 40)]), [])
        found = live.validate_live_log([dict(good, actions="abc")])
        self.assertEqual(found, ["line 1: actions 'abc' is neither a 40-hex sha nor null"])

    def test_d_blob_id_is_gits(self):
        tmp = tempfile.mkdtemp(prefix="pf19-blob-")
        self.addCleanup(shutil.rmtree, tmp, True)
        write(tmp, "a.json", ACTIONS)
        p = subprocess.run(["git", "hash-object", "--no-filters", os.path.join(tmp, "a.json")],
                           capture_output=True, text=True)
        self.assertEqual(live.blob_id(os.path.join(tmp, "a.json")), p.stdout.strip())
        self.assertIsNone(live.blob_id(os.path.join(tmp, "missing.json")))

    def test_d_go_live_and_first_open_record_the_actions_blob(self):
        """On a copy of the real home family (no buttons), with an empty run table added."""
        root = tempfile.mkdtemp(prefix="pf19-live-")
        self.addCleanup(shutil.rmtree, root, True)
        for ext in ("html", "features.json"):
            with open(os.path.join(features.ROOT, TPL + "home." + ext), encoding="utf-8") as fh:
                write(root, TPL + "home." + ext, fh.read())
        write(root, TPL + "home.actions.json", json.dumps({"direct": {}}))
        quiet = lambda argv, cwd: (0, "", "")  # noqa: E731
        made = draft.make_draft("home", name="try", person="fixp", root=root, runner=quiet, share=False)
        self.assertEqual(made["result"], "draft", made)
        got = live.go_live(made["written"][0], person="fixp", root=root, runner=quiet, share=False)
        self.assertEqual(got["result"], "live", got)
        last = live.last_live("fixp", "home", root)
        self.assertEqual(last["actions"], live.actions_blob("home", root))
        self.assertIsNone(live.stale_actions("fixp/home.html", root))
        page = os.path.join(root, V + "fixp/home.html")
        with open(page, encoding="utf-8") as fh:
            text = fh.read()
        write(root, V + "fixp/home.html", text.replace("<head>", "<head>\n" + live.PREPARED_META, 1))
        write(root, TPL + "home.actions.json", json.dumps({"direct": {}, "note": "moved"}))
        self.assertIsNotNone(live.stale_actions("fixp/home.html", root), "changed since go_live")
        got = live.first_open(V + "fixp/home.html", person="fixp", root=root, runner=quiet, share=False)
        self.assertEqual(got["result"], "live", got)
        last = live.last_live("fixp", "home", root)
        self.assertEqual((last["kind"], last["actions"]), ("first-open", live.actions_blob("home", root)))
        self.assertIsNone(live.stale_actions("fixp/home.html", root), "first open records the blob now")


if __name__ == "__main__":
    unittest.main()
