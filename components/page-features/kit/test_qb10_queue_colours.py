#!/usr/bin/env python3
"""QB-10 (queue colours): the content-queue page's three colour families. The due rule is the emails page's, not a
fork: kit/due.js is carried whole by the page, and in node it gives the same class and words as the emails template's
and editor's page's own urgOf / dueTag over the same dates. Type colours are tokens in light and both dark blocks, an
outline chip and a left edge, and the type tabs carry them.

    /usr/bin/python3 components/page-features/kit/test_qb10_queue_colours.py
"""
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
VIEWERS = os.path.join(ROOT, "platform", "views", "viewers")
PAGE = os.path.join(VIEWERS, "_templates", "content-queue.html")
EMAILS = [os.path.join(VIEWERS, "_templates", "emails.html"), os.path.join(VIEWERS, "editor", "emails.html")]
DUE_JS = os.path.join(HERE, "due.js")
START = "<!-- page-features due.js: component-owned, do not edit -->\n<script id=\"pf-due\">\n"
END = "</script>\n<!-- end page-features due.js -->"
TOKENS = ("--t-email", "--t-static", "--t-video", "--t-page")


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def emails_rule(text):
    """The emails page's DAY, AWAY, urgOf and dueTag lines, as they are."""
    out = []
    for pat in (r"^const DAY=.*$", r"^const AWAY=.*$", r"^function urgOf\(e\).*$", r"^function dueTag\(e\).*\n.*$"):
        m = re.search(pat, text, re.M)
        assert m, "no %s in the emails page" % pat
        out.append(m.group(0))
    return "\n".join(out)


NODE = r"""
const fs = require("fs");
const w = {document: {createElement: () => ({})}};
new Function("window", fs.readFileSync(process.argv[2], "utf8"))(w);
const rules = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
function iso(k) { const d = new Date(); d.setHours(12, 0, 0, 0); d.setDate(d.getDate() + k); return d.toISOString().slice(0, 10); }
const cases = [-9, -3, -1, 0, 1, 2, 3, 5, 6, 30].map(k => [iso(k), false]).concat([["", false], [iso(1), true], [iso(9), true]]);
const out = {due: [], emails: []};
for (const [d, done] of cases) {
  const s = w.pfDue.tag(d, done);
  out.due.push([d, done, w.pfDue.urg(d, done), s ? s.className + " | " + s.textContent : null]);
}
for (const src of rules) {
  const f = new Function("dueOf", "eveDone", "esc", src + "\nreturn {urgOf, dueTag};");
  const r = f(e => e.d, e => e.done, x => x);
  out.emails.push(cases.map(([d, done]) => {
    const html = r.dueTag({d, done});
    const m = /class="(pill due [^"]+)">(.*)<\/span>/.exec(html);
    return [d, done, r.urgOf({d, done}), m ? m[1] + " | " + m[2] : null];
  }));
}
console.log(JSON.stringify(out));
"""


class Due(unittest.TestCase):
    def test_the_page_carries_due_js_whole(self):
        page = read(PAGE)
        self.assertEqual(page.count(START), 1)
        block = page[page.index(START) + len(START):]
        self.assertEqual(block[:block.index(END)], read(DUE_JS), "the due.js block is kit/due.js byte for byte")

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_same_class_and_words_as_both_emails_pages(self):
        tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "qb10-%d" % os.getpid())
        os.makedirs(tmp, exist_ok=True)
        try:
            js, rules = os.path.join(tmp, "t.js"), os.path.join(tmp, "rules.json")
            with open(js, "w") as fh:
                fh.write(NODE)
            with open(rules, "w") as fh:
                json.dump([emails_rule(read(p)) for p in EMAILS], fh)
            p = subprocess.run(["node", js, DUE_JS, rules], capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 0, p.stderr)
            got = json.loads(p.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        for page, emails in zip(EMAILS, got["emails"]):
            self.assertEqual(got["due"], emails, "due.js and %s disagree" % os.path.relpath(page, ROOT))
        words = {row[2]: row[3] for row in got["due"] if row[3]}
        self.assertEqual(sorted(words), ["grn", "red", "yel"], "all three bands are exercised")
        self.assertTrue(any(r[3] and " | Overdue · was due " in r[3] for r in got["due"]), "a past date says Overdue")
        self.assertTrue(all(r[3] is None for r in got["due"] if r[1] or not r[0]), "no date or done: no pill")

    def test_the_pill_colours_are_the_emails_pages(self):
        page = read(PAGE)
        for band, bg, fg in (("red", "F9B7D0", "9A1A55"), ("yel", "FBE8A6", "7A5800"), ("grn", "BCD9F6", "1A4F85")):
            self.assertIn(".pill.due.d-%s{background:#%s;color:#%s}" % (band, bg, fg), page)
            for e in EMAILS:
                self.assertIn(".pill.due.d-%s{background:#%s;color:#%s}" % (band, bg, fg), read(e))


class Type(unittest.TestCase):
    def test_a_board_card_says_its_type_on_its_colour(self):
        """email_lead, 2026-11-19: "debería tener un tag el tipo de creative más evidente. O que diga email antes"."""
        page = read(PAGE)
        self.assertIn('.cq .l-type{', page)
        self.assertIn("background:var(--tc);color:var(--panel)", page)
        self.assertIn('top.insertBefore(el("span", "l-type"', page)

    def test_tokens_in_light_and_both_dark_blocks(self):
        page = read(PAGE)
        # email_lead, 2026-11-19: "deberían ser más coloridos ... no se distingue bien la diferencia" (was #6E6058 #7A4E7E #2E6A70 #8A7F77)
        light = re.search(r"--t-email:#7C3AED; --t-static:#DB2777; --t-video:#0D9488; --t-page:#A16207;", page)
        self.assertTrue(light, "the four light values as email_lead set them")
        self.assertEqual(page.count("--t-email:#A78BFA; --t-static:#F472B6; --t-video:#2DD4BF; --t-page:#FACC15;"), 2,
                         "the dark values in the prefers-color-scheme block and the data-theme block")

    def test_outline_and_edge_never_a_fill(self):
        page = read(PAGE)
        chip = re.search(r"\.cq \.pill\.tchip\{([^}]*)\}", page).group(1)
        self.assertIn("background:transparent", chip)
        self.assertIn("box-shadow:inset 0 0 0 1.5px var(--tc", chip)
        self.assertIn('.cq .item[class*="ty-"]{border-left:4px solid var(--tc)}', page)
        self.assertIn('.cq tr[class*="ty-"] td:first-child{box-shadow:inset 4px 0 0 var(--tc)}', page)
        pressed = re.search(r'#cq-tabs button\[class\*="ty-"\]\[aria-pressed="true"\]\{([^}]*)\}', page).group(1)
        self.assertIn("background:none", pressed)

    def test_the_tabs_are_the_legend_and_types_map(self):
        page = read(PAGE)
        for tab, ty in (("video", "video"), ("statics", "static"), ("emails", "email"), ("pages", "page")):
            self.assertIn('data-tab="%s" aria-pressed="false" class="ty-%s"' % (tab, ty), page)
        m = re.search(r"var TY = (\{[^}]*\});", page)
        self.assertEqual(json.loads(m.group(1)), {"video-ad": "video", "image-ad": "static", "carousel": "static",
                                                   "email": "email", "landing-page": "page"})


if __name__ == "__main__":
    unittest.main()
