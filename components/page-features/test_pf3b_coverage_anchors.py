#!/usr/bin/env python3
"""PF-3b (coverage and anchors): check.py proves every top-level region of a page carries a feature number, and
every feature's anchor (its data-feature="n") sits on exactly one element.

    /usr/bin/python3 components/page-features/test_pf3b_coverage_anchors.py

Read the way check.py reads every page: the static HTML (html.parser), so a row a script repeats for each email is
not a second anchor. A region is a direct child of <body> (of the document when there is no <body>), leaving out
head tags, scripts, styles, templates and anything `hidden`; a region marked data-feature-skip is left out and
counted. Both report by number and never fail the exit code unless --strict.

  1  a clean page: COVERAGE 0, ANCHORS 0, exit 0 with and without --strict
  2  an unnumbered banner: one COVERAGE line naming it; exit 0, and 1 under --strict
  3  an anchor on two elements and an anchor on none: ANCHORS names both numbers; exit 1 under --strict
  4  data-feature-skip leaves a region out and the report counts it; hidden regions and <template> copies don't count
  5  a page with no <body> tag: its top-level elements are the regions
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "check.py")
FIX = os.path.join(HERE, "test_check_fixtures")
ROOT = os.path.join(FIX, "root")
CLEAN = os.path.join(FIX, "clean.features.json")
PS = "".join('<p data-feature="%d">feature %d</p>' % (n, n) for n in range(1, 9))


def body(inner, ps=PS):
    return '<!doctype html><html><head><title>t</title></head><body>%s%s</body></html>' % (inner, ps)


class TestCoverageAnchors(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.dir = t.name

    def run_check(self, html, *extra):
        page = os.path.join(self.dir, "page.html")
        with open(page, "w") as f:
            f.write(html)
        p = subprocess.run([sys.executable, TOOL, page, "--features", CLEAN, "--root", ROOT] + list(extra),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        return p.returncode, p.stdout

    def section(self, out, name):
        m = re.search(r"^%s — (\d+)(.*)$\n((?:  .*\n?)*)" % name, out, re.M)
        self.assertIsNotNone(m, "no %s section in:\n%s" % (name, out))
        items = [ln.strip() for ln in m.group(3).splitlines() if ln.strip() and ln.strip() != "(none)"]
        return int(m.group(1)), m.group(2), items

    def test_1_clean_page(self):
        for extra in ((), ("--strict",)):
            code, out = self.run_check(body(""), *extra)
            self.assertEqual(self.section(out, "COVERAGE")[0], 0, out)
            self.assertEqual(self.section(out, "ANCHORS")[0], 0, out)
            self.assertEqual(code, 0, out)

    def test_2_unnumbered_banner(self):
        html = body('<header class="banner">company</header>')
        code, out = self.run_check(html)
        n, _, items = self.section(out, "COVERAGE")
        self.assertEqual(n, 1, out)
        self.assertIn("header.banner", items[0])
        self.assertIn("company", items[0])
        self.assertEqual(code, 0)
        self.assertEqual(self.run_check(html, "--strict")[0], 1)

    def test_3_anchor_on_two_and_on_none(self):
        ps = PS.replace('<p data-feature="8">feature 8</p>', "") + '<p data-feature="2">again</p>'
        code, out = self.run_check(body("", ps), "--strict")
        n, _, items = self.section(out, "ANCHORS")
        self.assertEqual(n, 2, out)
        joined = "\n".join(items)
        self.assertRegex(joined, r"\b2\b.*2 elements")
        self.assertRegex(joined, r"\b8\b.*no element")
        self.assertEqual(code, 1)

    def test_4_skip_marker_hidden_and_templates(self):
        html = body('<div class="toast" data-feature-skip></div><div hidden>later</div>'
                    '<template><p data-feature="1">row copy</p></template><script>x="<div>"</script>')
        code, out = self.run_check(html, "--strict")
        n, rest, _ = self.section(out, "COVERAGE")
        self.assertEqual(n, 0, out)
        self.assertIn("1 skipped", rest)
        self.assertEqual(self.section(out, "ANCHORS")[0], 0, out)
        self.assertEqual(code, 0, out)

    def test_5_page_without_body_tag(self):
        code, out = self.run_check('<title>t</title><nav>Menu</nav>' + PS)
        n, _, items = self.section(out, "COVERAGE")
        self.assertEqual(n, 1, out)
        self.assertIn("nav", items[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
