"""QB-7 (content queue Monday): the content-queue page speaks plain words, shows types, and keeps video read only.

Outside the folded "How it works" <details>, the page's visible text (static text, templates included, plus the
placeholder / title / aria-label words) never says cq.py, queue-shadow, serve.py or shadow, and no string in its
script does either, except the one cq.py command line the request copies to Claude. The "where changes go" line is
there (it replaced the "Test version" line, email_lead 2026-10-29); so are the type tabs, the Type column and the "show live" tick; the read-only row template (video and
email) has no Assign; check.py and js-parse exit 0. Stdlib only, no network, no Chrome, no git. Run from the repo
root:
    python3 components/page-features/kit/test_qb7_content_queue_page.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402  kit/serve.py, for ROOT and TEMPLATES only

ROOT = serve.ROOT
TPL = os.path.join(ROOT, serve.TEMPLATES)
PAGE = os.path.join(TPL, "content-queue.html")
FEATURES = os.path.join(TPL, "content-queue.features.json")
BANNED = ("cq.py", "queue-shadow", "serve.py", "shadow")
CQ_LINE = '"python3 components/creative-queue/cq.py"'
VOID = ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class Visible(HTMLParser):
    """The text a person can see, outside script, style and the How it works details; and each id's own text."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.stack, self.out, self.by_id, self.how = [], [], {}, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in VOID:
            if not self._hidden():
                self.out.extend(a[k] for k in ("placeholder", "title", "aria-label", "alt") if a.get(k))
            return
        self.stack.append((tag, a.get("id")))
        if not self._hidden():
            self.out.extend(a[k] for k in ("placeholder", "title", "aria-label", "alt") if a.get(k))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def _hidden(self):
        return any(t in ("script", "style") or i == "cq-how" for t, i in self.stack)

    def handle_data(self, data):
        for _, i in self.stack:
            if i:
                self.by_id[i] = self.by_id.get(i, "") + data
        if any(i == "cq-how" for _, i in self.stack):
            self.how.append(data)
        elif not self._hidden():
            self.out.append(data)


def visible(text):
    v = Visible()
    v.feed(text)
    return v


def squash(s):
    return re.sub(r"\s+", " ", s).strip()


class PlainWords(unittest.TestCase):
    def setUp(self):
        self.text = read(PAGE)
        self.v = visible(self.text)
        self.script = re.findall(r"<script>([\s\S]*?)</script>", self.text)[0]

    def test_no_technical_words_outside_how_it_works(self):
        seen = squash(" ".join(self.v.out)).lower()
        for word in BANNED:
            self.assertNotIn(word, seen, "visible text says %r" % word)

    def test_no_technical_words_in_the_script_strings_but_the_command(self):
        strings = re.findall(r'"(?:[^"\\\n]|\\.)*"', self.script)
        self.assertIn(CQ_LINE, strings)                           # the request still carries the exact commands
        for s in strings:
            if s == CQ_LINE:
                continue
            for word in BANNED:
                self.assertNotIn(word, s.lower(), "a script string says %r: %s" % (word, s))

    def test_test_version_line_and_how_it_works(self):
        self.assertEqual(squash(self.v.by_id["cq-testver"]), "Changes here reach everyone’s queue page. owner’s own Outlier doesn’t see them yet, and his list arrives about once a day.")
        how = re.search(r'<details class="how" id="cq-how"[^>]*>', self.text)
        self.assertTrue(how, "no How it works details")
        self.assertNotIn(" open", how.group(0))                     # folded
        h = squash(" ".join(self.v.how))
        self.assertTrue(h.startswith("How it works"), h[:40])
        for word in ("cq.py", "runs/queue-shadow", "serve.py", "turn my page server on", "Held"):   # how to reach the emails page now (2026-11-05)
            self.assertIn(word, h)
        self.assertNotIn("8765", h, "the 8765 server no longer runs (first-look QC, 2026-11-05): How it works never sends anyone there")
        self.assertTrue(squash(self.v.by_id["cq-req"]).startswith("Copy this to your Claude "))
        self.assertIn('<span class="eye">Copy this to your Claude</span>', self.text)


class TypesAndRows(unittest.TestCase):
    def setUp(self):
        self.text = read(PAGE)
        self.script = re.findall(r"<script>([\s\S]*?)</script>", self.text)[0]

    def template(self, tid):
        m = re.search(r'<template id="%s">([\s\S]*?)</template>' % tid, self.text)
        self.assertTrue(m, tid)
        return m.group(1)

    def test_tabs_with_counts(self):
        tabs = re.search(r'<div class="seg" role="group" aria-label="Type" id="cq-tabs"[^>]*>([\s\S]*?)</div>', self.text)
        self.assertTrue(tabs)
        got = re.findall(r'data-tab="([^"]*)"[^>]*>([A-Za-z]+)<small class="t-n">', tabs.group(1))
        self.assertEqual(got, [("", "All"), ("video", "Video"), ("statics", "Statics"), ("emails", "Emails"),
                               ("pages", "Pages")])
        self.assertIn('{key: "statics", types: ["image-ad", "carousel"]}', self.script)

    def test_type_column_first(self):
        head = re.findall(r"<th>([^<]*)</th>", self.template("cq-t-group"))
        self.assertEqual(head[0], "Type")
        for tid in ("cq-t-row", "cq-t-row-ro"):
            self.assertTrue(self.template(tid).lstrip().startswith('<tr data-feature="15">\n  <td class="c-type">'), tid)
        for word in ('"video-ad": "Video"', '"image-ad": "Static"', '"carousel": "Carousel"', '"email": "Email"',
                     '"landing-page": "Page"'):
            self.assertIn(word, self.script)

    def test_video_row_template_has_no_assign(self):
        ro = self.template("cq-t-row-ro")
        self.assertNotIn("assign", ro.lower())
        self.assertIn("owner + creator", ro)
        self.assertIn('clone(ro ? "cq-t-row-ro" : "cq-t-row")', self.script)
        self.assertIn('class="assign"', self.template("cq-t-row"))
        add = re.search(r'<select id="cq-a-type">([\s\S]*?)</select>', self.text).group(1)
        self.assertNotIn("video", add.lower())                     # the add form never offers video

    def test_show_live_people_and_the_emails_link(self):
        self.assertIn('<input type="checkbox" id="cq-f-live"> show live', self.text)
        self.assertNotIn("christine", self.script.lower())          # view.py drops her; no list in the page
        # view.py's link names the 8765 server, which no longer runs; on a page server the page sends it to the team's
        # emails page beside it instead (first-look QC, 2026-11-05: the old link opened nothing)
        # Since 2026-11-10 (editor): the person's own emails page when the server has one, else view.py's relative link,
        # which opens the team's emails page beside this one on the same server
        self.assertIn('return m && who && ownEmails === true ? "/p/" + who + "/emails.html#" + m[1] : val(u);', self.script)
        self.assertIn('fetch("/p/" + viewer() + "/emails.html", {cache: "no-store"}).then(function (r) { if (r.ok) { ownEmails = true; render(); } }', self.script)


class Checks(unittest.TestCase):
    def test_check_py_exits_0(self):
        p = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "components", "page-features", "check.py"),
                            "--features", FEATURES, PAGE], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_js_parse_exits_0(self):
        node = shutil.which("node")
        self.assertTrue(node, "node is not on PATH")
        p = subprocess.run([node, os.path.join(TPL, "js-parse.test.mjs")], cwd=ROOT, capture_output=True, text=True,
                           timeout=300)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)



class HandoffsLoading(unittest.TestCase):
    """2026-11-02, email_lead: a cold Drive read took 137 s, editor saw 0296's queue card with no Done and read it as "already
    finished". While her hand-offs load the page says plainly that the Done buttons are coming, a queue card that is a
    hand-off says its own Done is loading, and the page asks again while statics.py says it is refreshing."""

    def setUp(self):
        self.text = read(PAGE)
        self.script = re.findall(r"<script>([\s\S]*?)</script>", self.text)[0]

    def test_it_says_the_done_buttons_are_coming(self):
        self.assertIn("Done buttons are loading", self.script)
        self.assertIn("not finished", self.script)
        self.assertIn("its Done button is loading", self.script)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_the_queue_row_with_a_date_is_the_one_kept(self):
        """2026-11-02: four queue rows share brief 0296 (the real one due Oct 30, an old short name and two idea rows
        with no date); the last one read won and editor's overdue 0296 showed "no date yet" at the bottom of her list."""
        fn = re.search(r"  function keepQueued\(old, r\) \{[\s\S]*?\n  \}\n", self.text).group(0)
        rows = [{"id": "real", "due": "2026-10-30"}, {"id": "short", "due": None},
                {"id": "idea", "due": None, "priority": "P1"}, {"id": "later", "due": "2026-11-05"}]
        js = ("function val(v){return v===null||v===undefined?'':String(v);}\n" + fn +
              "var k=null;%s.forEach(function(r){k=keepQueued(k,r);});console.log(k.id);" % json.dumps(rows))
        p = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual((p.returncode, p.stdout.strip()), (0, "real"), p.stderr)
        js2 = ("function val(v){return v===null||v===undefined?'':String(v);}\n" + fn +
               "var k=null;%s.forEach(function(r){k=keepQueued(k,r);});console.log(k.id);" % json.dumps(rows[1:3]))
        p = subprocess.run(["node", "-e", js2], capture_output=True, text=True, timeout=30)
        self.assertEqual(p.stdout.strip(), "idea", "with no date anywhere, the one with a priority")

    def test_it_asks_again_while_refreshing(self):
        for fn in ("loadStatics", "loadVideos"):
            self.assertRegex(self.script, r"refreshing\) \w+ = setTimeout\(%s, \d+\)" % fn)
            self.assertRegex(self.script, r"function %s\(\) \{[^\n]*\n\s*clearTimeout\(\w+\);" % fn, "one timer, never two")

if __name__ == "__main__":
    unittest.main()
