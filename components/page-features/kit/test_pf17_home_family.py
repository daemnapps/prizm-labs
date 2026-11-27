#!/usr/bin/env python3
"""PF-17 (home page family): the page server's / is a page of the family `home`, its strip stays above it, and /plain
always serves the built-in index.

    python3 components/page-features/kit/test_pf17_home_family.py

    (a) / serves _templates/home.html when the person has no live home page, and their live one when they do
    (b) /data/home answers the person, the status fields and line, families down, PF-8 (show my pages)'s list, clicks
    (c) the strip (the status line with the fixed port, a link to /plain) is first in <body> on both, and on a live
        page that tries to hide it by id CSS and by script: no id, a tag new on every response, its words in a closed
        shadow root, its style !important, a guard that puts it back
    (d) /plain is byte for byte the code-built index_html, with no strip; a live page that throws on load, is not
        UTF-8 or is gone still leaves / and /plain working; a copy with no home template serves the index at /
    (e) at HEAD: the template reads only /data/home; going live (check_live, on a /page-draft of it) and the share
        check pass on it; pages.list_pages lists `home`, owner developer

Each server test builds a temp root (a git repo, never pushed) with the real home template copied in. Stdlib only,
Python 3.9. No network beyond 127.0.0.1; writes only in temp folders.
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
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402
import server  # noqa: E402
sys.path.insert(0, os.path.dirname(HERE))
import draft  # noqa: E402
import features  # noqa: E402
import live  # noqa: E402
import pages  # noqa: E402
import share  # noqa: E402

REAL = features.ROOT
TPL = "platform/views/viewers/_templates/"
PERSON, PORT = "tess", 18747
PAGE = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n</head>\n<body><p>page</p></body>\n</html>\n'
LIVE = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>mine</title>\n</head>\n'
        '<body class="mine">\n<h1>Tess made this home herself</h1>\n</body>\n</html>\n')
HIDES = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<style>#page-server-strip,#strip,'
         '[role=status],body>*:first-child{display:none!important;visibility:hidden!important}</style>\n</head>\n'
         '<body>\n<script>var s=document.getElementById("page-server-strip");if(s)s.remove();'
         'document.body.firstElementChild.remove();document.body.removeChild(document.body.firstChild);</script>\n'
         '<p>a home that hides the strip</p>\n</body>\n</html>\n')
THROWS = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<script>throw new Error("boom on '
          'load")</script>\n</head>\n<body onload="undefinedThing()">\n<script>null.x</script>\n</body>\n</html>\n')
HOST_RE = re.compile(r'<(ps-[0-9a-f]{12}) style="([^"]*)"><template shadowrootmode="closed">(.*?)</template></\1>',
                     re.S)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write(root, rel, text, mode="w"):
    p = os.path.join(str(root), rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as fh:
        fh.write(text)


def strip_of(text):
    """(start, tag, style, inside) of the one strip in a served page; the test fails when there is not exactly one."""
    hits = list(HOST_RE.finditer(text))
    assert len(hits) == 1, "%d strips in %r" % (len(hits), text[:400])
    m = hits[0]
    return m.start(), m.group(1), m.group(2), m.group(3)


class FakeGit(object):
    def __call__(self, argv, cwd):
        return 0, "", ""


class Served(unittest.TestCase):
    """(a)–(d) against a PageServer on a temp root."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="pf17-")).resolve()
        self.addCleanup(shutil.rmtree, str(self.root), True)
        subprocess.run(["git", "init", "-q", str(self.root)], capture_output=True)
        for ext in ("html", "features.json"):
            write(self.root, TPL + "home." + ext, read(os.path.join(REAL, TPL, "home." + ext)))
        write(self.root, TPL + "alpha.features.json", json.dumps({"owner": PERSON}))
        write(self.root, TPL + "alpha.html", PAGE)
        write(self.root, "platform/views/viewers/tess/alpha.html", PAGE)
        write(self.root, "platform/views/viewers/tess/drafts/alpha--try.html", PAGE)
        write(self.root, "team/people/tess/identity.json", json.dumps({"page_server_port": PORT}))
        self.state = self.root.parent / (self.root.name + "-state")
        self.state.mkdir()
        self.addCleanup(shutil.rmtree, str(self.state), True)
        self.srv = server.PageServer(self.state, self.root, PERSON, act_person=PERSON, port=PORT)
        httpd = server.Server(("127.0.0.1", 0), self.srv.handler())
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        self.port = httpd.server_address[1]

    def req(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            c.request("GET", path, headers={"Host": "127.0.0.1:%d" % self.port})
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def home(self):
        code, body = self.req("/")
        self.assertEqual(code, 200, body[:300])
        return body.decode("utf-8")

    def live(self, text, mode="w"):
        write(self.root, "platform/views/viewers/tess/home.html", text, mode)

    def assert_strip_first(self, text, body_at):
        start, tag, style, inside = strip_of(text)
        self.assertGreaterEqual(start, body_at, "the strip is inside <body>")
        self.assertEqual(text[body_at:start], server.STRIP_MARK, "nothing of the page comes before it")
        self.assertIn("your address: http://localhost:%d/" % PORT, inside, "the strip names the fixed port")
        self.assertIn("every family up", inside)
        self.assertIn("0 not pushed", inside)
        self.assertIn('<a href="/plain">plain page list</a>', inside)
        return tag, style, inside

    # (a)
    def test_a_the_template_without_a_live_page(self):
        text = self.home()
        tpl = read(os.path.join(str(self.root), TPL, "home.html"))
        self.assertIn('fetch("/data/home"', text)
        self.assertIn('<meta name="kit-token" content="%s">' % self.srv.token, text)
        body = re.search(r"<body(\s[^>]*)?>", text).end()
        self.assert_strip_first(text, body)
        start, tag, _, _ = strip_of(text)
        served = text[:body] + text[text.index("</script>", start) + len("</script>"):]
        self.assertEqual(served, serve.with_token(tpl.encode("utf-8"), self.srv.token).decode("utf-8"),
                         "the template exactly, plus the token and the strip")

    def test_a_the_live_page_when_there_is_one(self):
        self.live(LIVE)
        text = self.home()
        self.assertIn("Tess made this home herself", text)
        self.assertNotIn('fetch("/data/home"', text, "not the template")
        self.assert_strip_first(text, text.index('<body class="mine">') + len('<body class="mine">'))
        code, page = self.req("/v/tess/home.html")
        self.assertEqual(code, 200)
        self.assertNotIn(server.STRIP_MARK, page.decode(), "the strip is the / route's, not the page's")

    # (b)
    def test_b_data_home(self):
        with open(str(self.state / "clicks.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": "2026-10-29T01:00:00Z", "page": "tess/alpha.html", "n": 5, "ok": True,
                                 "said": "saved"}) + "\n")
        self.srv.health.set_down("alpha", "down: alpha broke")
        code, body = self.req("/data/home")
        self.assertEqual(code, 200)
        d = json.loads(body.decode())
        self.assertEqual((d["person"], d["port"], d["plain"]), (PERSON, PORT, "/plain"))
        self.assertEqual(d["status_line"], self.srv.status_line())
        self.assertIn("down: alpha (down: alpha broke)", d["status_line"])
        self.assertEqual(d["down"], {"alpha": "down: alpha broke"})
        for k in ("synced_at", "sync_ok", "sync_said", "not_pushed", "behind", "down", "warn"):
            self.assertIn(k, d["status"])
        self.assertIsNone(d["pages_error"])
        fams = {f["family"]: f for f in d["pages"]["families"]}
        self.assertEqual(sorted(fams), ["alpha", "home"], "home is a family like the others")
        self.assertEqual(fams["alpha"]["live"]["path"], "platform/views/viewers/tess/alpha.html")
        self.assertEqual([x["name"] for x in fams["alpha"]["drafts"]], ["try"])
        self.assertTrue(fams["home"]["available"])
        self.assertEqual(fams["home"]["owner"], "developer")
        self.assertEqual(d["clicks"][0]["said"], "saved")
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", "/data/home", headers={"Host": "evil.example:%d" % self.port})
        self.assertEqual(c.getresponse().status, 403, "a foreign Host is refused")
        c.close()

    # (c)
    def test_c_a_page_that_hides_the_strip_still_shows_it(self):
        self.live(HIDES)
        text = self.home()
        tag, style, inside = self.assert_strip_first(text, text.index("<body>") + len("<body>"))
        self.assertNotRegex(text[text.index(server.STRIP_MARK):text.index("</%s>" % tag)], r"\sid=",
                            "no id: getElementById and #id CSS find nothing")
        self.assertNotIn(tag, HIDES)
        self.assertNotEqual(tag, strip_of(self.home())[1], "a new tag name on every response")
        for rule in ("display:block!important", "visibility:visible!important", "opacity:1!important",
                     "position:sticky!important"):
            self.assertIn(rule, style, "inline !important outranks the page's own !important rules")
        self.assertIn("<style>:host", inside, "its words and look live in a closed shadow root the page's CSS "
                                              "cannot reach")
        guard = text[text.index("</%s>" % tag):text.index("</script>", text.index("</%s>" % tag))]
        for step in ("attachShadow({mode:'closed'})", "MutationObserver", "insertBefore", "setAttribute",
                     "subtree:true", "attributes:true", "document.currentScript"):
            self.assertIn(step, guard)
        self.assertLess(text.index(server.STRIP_MARK), text.index("document.body.firstElementChild.remove()"),
                        "the guard runs before the page's own body script")
        self.assertIn(server.STRIP_GUARD, text)

    def test_c_the_strip_on_the_built_in_index_when_no_template(self):
        os.remove(os.path.join(str(self.root), TPL, "home.html"))
        text = self.home()
        self.assertIn("<h1>Tess's pages</h1>", text)
        self.assert_strip_first(text, text.index("<body>") + len("<body>"))

    # (d)
    def test_d_plain_is_the_code_built_index_byte_for_byte(self):
        self.live(HIDES)
        code, body = self.req("/plain")
        self.assertEqual(code, 200)
        self.assertEqual(body, self.srv.index_html().encode("utf-8"))
        text = body.decode()
        self.assertNotIn(server.STRIP_MARK, text, "/plain is untouched")
        self.assertIn("<title>tess's pages</title>", text)
        self.assertIn('<p class="st" id="status">your address: http://localhost:%d/' % PORT, text)
        self.assertLess(text.find('href="/v/tess/alpha.html"'), text.find('href="/v/tess/drafts/alpha--try.html"'))
        self.assertIn("<h2>Recent clicks</h2>", text)

    def test_d_a_broken_live_page_leaves_plain_working(self):
        want = None
        for broken, mode in ((THROWS, "w"), (b"\xff\xfe<html><body>\x00\x9c not utf-8", "wb")):
            self.live(broken, mode)
            text = self.home()
            strip_of(text)
            code, body = self.req("/plain")
            want = want or self.srv.index_html().encode("utf-8")
            self.assertEqual((code, body), (200, want))
        os.remove(os.path.join(str(self.root), "platform/views/viewers/tess/home.html"))
        os.makedirs(os.path.join(str(self.root), "platform/views/viewers/tess/home.html"))
        self.assertIn('fetch("/data/home"', self.home(), "a home.html that is no file: the template")
        self.assertEqual(self.req("/plain"), (200, want))


GUARD_HARNESS = r"""
// A minimal DOM: just what the strip's guard touches. MutationObserver callbacks run as microtasks, as in a browser.
const fs = require("fs");
const code = fs.readFileSync(process.argv[2], "utf8");
const observers = [];
function within(n, top) { for (; n; n = n.parentNode) if (n === top) return true; return false; }
function notify(target, type) {
  for (const o of observers) {
    const hit = type === "attributes" ? (o.opts.attributes && o.target === target)
      : (o.opts.childList && (o.target === target || (o.opts.subtree && within(target, o.target))));
    if (hit && !o.queued) { o.queued = true; queueMicrotask(() => { o.queued = false; o.cb([]); }); }
  }
}
class Node {
  constructor(tag) { this.tag = tag; this.children = []; this.parentNode = null; this.attrs = {}; }
  get firstChild() { return this.children[0] || null; }
  insertBefore(n, ref) {
    if (n.parentNode) n.parentNode.removeChild(n);
    const i = ref ? this.children.indexOf(ref) : -1;
    if (i < 0) this.children.push(n); else this.children.splice(i, 0, n);
    n.parentNode = this; notify(this, "childList"); return n;
  }
  appendChild(n) { return this.insertBefore(n, null); }
  removeChild(n) {
    const i = this.children.indexOf(n);
    if (i >= 0) { this.children.splice(i, 1); n.parentNode = null; notify(this, "childList"); }
    return n;
  }
  remove() { if (this.parentNode) this.parentNode.removeChild(this); }
}
class Element extends Node {
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  setAttribute(k, v) { this.attrs[k] = String(v); notify(this, "attributes"); }
  querySelector(sel) { return this.children.find(c => c.tag === sel) || null; }
  get previousElementSibling() { const s = this.parentNode.children; return s[s.indexOf(this) - 1] || null; }
  attachShadow(o) { this.shadowMode = o.mode; const self = this; return {appendChild(c) { self.shadowGot = c; }}; }
}
const html = new Element("html"), body = new Element("body"), host = new Element("ps-test"),
      tpl = new Element("template"), script = new Element("script"), page = new Element("p");
tpl.content = "the strip's words";
host.attrs.style = "display:block!important";
html.appendChild(body); host.appendChild(tpl); body.appendChild(host); body.appendChild(script); body.appendChild(page);
global.Node = Node; global.Element = Element;
global.document = {documentElement: html, body: body, currentScript: script};
global.window = {MutationObserver: class { constructor(cb) { this.cb = cb; }
  observe(target, opts) { observers.push({cb: this.cb, target, opts, queued: false}); } }};
new Function(code)();
const tick = () => new Promise(r => setTimeout(r, 0));
const out = {};
(async () => {
  out.shadow = host.shadowMode === "closed" && host.shadowGot === "the strip's words" && !host.children.length;
  out.script_gone = body.children.indexOf(script) < 0;
  body.removeChild(host); await tick();
  out.removed = body.children[0] === host;
  host.setAttribute("style", "display:none"); await tick();
  out.restyled = host.getAttribute("style") === "display:block!important";
  host.remove(); body.firstChild.remove(); await tick();
  out.removed_twice = body.children[0] === host;
  const fresh = new Element("body"); html.removeChild(body); html.appendChild(fresh); document.body = fresh; await tick();
  out.new_body = fresh.children[0] === host;
  console.log(JSON.stringify(out));
})();
"""


class Guard(unittest.TestCase):
    """(c) the strip's guard script itself, in node with a minimal DOM (skipped where there is no node; the markup
    checks above still hold)."""

    def test_c_the_guard_puts_the_strip_back(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node on this machine")
        tmp = tempfile.mkdtemp(prefix="pf17-guard-")
        self.addCleanup(shutil.rmtree, tmp, True)
        js = server.STRIP_GUARD[len("<script>"):-len("</script>")]
        write(tmp, "guard.js", js)
        write(tmp, "harness.js", GUARD_HARNESS)
        p = subprocess.run([node, os.path.join(tmp, "harness.js"), os.path.join(tmp, "guard.js")],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual(got, {"shadow": True, "script_gone": True, "removed": True, "restyled": True,
                               "removed_twice": True, "new_body": True})


class AtHead(unittest.TestCase):
    """(e) the real family at HEAD, read-only."""

    def test_e_the_template_reads_only_data_home(self):
        text = read(os.path.join(REAL, TPL, "home.html"))
        outside = text.replace(text[slice(*live._overlay_span(text))], "")
        self.assertEqual(re.findall(r"fetch\(\s*[\"']([^\"']+)", outside), ["/data/home"])
        self.assertNotIn("innerHTML", outside, "the page builds its own elements from the data")
        doc = features.load(os.path.join(REAL, TPL, "home.features.json"))
        self.assertEqual(features.validate(doc), [])
        self.assertEqual(doc["owner"], "developer")
        self.assertEqual(features.sync_text(text, doc), text, "the embedded catalog is the family list")
        self.assertIsNone(live.run_table("home", REAL), "no buttons, no run table")
        self.assertFalse([e for e in doc["features"] if e["kind"] == "action"])

    def test_e_check_live_passes_on_a_draft_of_the_template(self):
        root = tempfile.mkdtemp(prefix="pf17-live-")
        self.addCleanup(shutil.rmtree, root, True)
        for ext in ("html", "features.json"):
            write(root, TPL + "home." + ext, read(os.path.join(REAL, TPL, "home." + ext)))
        made = draft.make_draft("home", name="try", person="fixp", root=root, runner=FakeGit(), share=False)
        self.assertEqual(made["result"], "draft", made)
        r = live.check_live(made["written"][0], person="fixp", root=root, runner=FakeGit())
        self.assertIsNone(r["refused"], r)
        self.assertEqual(r["failures"], [])
        self.assertTrue(r["ok"])
        got = live.go_live(made["written"][0], person="fixp", root=root, runner=FakeGit(), share=False)
        page = os.path.join(root, "platform/views/viewers/fixp/home.html")
        self.assertTrue(os.path.isfile(page), got)
        self.assertIn('fetch("/data/home"', read(page))
        self.assertNotIn(live.OVERLAY_START, read(page))

    def test_e_the_share_check_passes_on_the_template(self):
        sys.path.insert(0, os.path.join(REAL, "components", "system-integration"))
        import page_scan
        r = share.share_check(TPL + "home.html", root=REAL, scan=page_scan.scan)
        self.assertIsNone(r["refused"], r)
        self.assertEqual(r["blockers"], [])
        self.assertEqual((r["view"], r["use"]), ("pass", "pass"))

    def test_e_list_pages_lists_home(self):
        result = pages.list_pages(person="nobody-here", root=REAL, runner=FakeGit())
        fams = {f["family"]: f for f in result["families"]}
        self.assertIn("home", fams)
        self.assertEqual((fams["home"]["owner"], fams["home"]["available"]), ("developer", True))


if __name__ == "__main__":
    unittest.main()
