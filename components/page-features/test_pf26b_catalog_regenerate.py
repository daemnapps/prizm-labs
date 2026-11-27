#!/usr/bin/env python3
"""PF-26b (emails catalog regenerate): emails.html's embedded feature catalog (<script id="fo-features">) is
regenerated from emails.features.json, and features.py can now tell drift without writing.

    /usr/bin/python3 components/page-features/test_pf26b_catalog_regenerate.py

Found 2026-10-30: the template's embed and the family file had the same 51 numbers, but 16 notes in the embed
were older (3, 7, 25-32, 45-47, 53, 57, 58). check.py never compares the two, so the drift was invisible.

  1  `sync <page> <family> --check` on a drifted page: exit 1, names the differing numbers, writes nothing
  2  after `sync`, `--check` says in sync, exit 0; a page with no fo-features block is refused (2), unchanged
  3  the emails template is in sync with emails.features.json (the lasting guard)
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import features  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
TEMPLATES = os.path.join(ROOT, "platform", "views", "viewers", "_templates")
FAMILY = {"family": "zz", "features": [
    {"n": 1, "name": "One", "kind": "R", "note": "new words"},
    {"n": 2, "name": "Two", "kind": "R", "note": "same"}]}
OLD = {"family": "zz", "features": [
    {"n": 1, "name": "One", "kind": "R", "note": "old words"},
    {"n": 2, "name": "Two", "kind": "R", "note": "same"}]}


def page(doc):
    return ('<html><body><p data-feature="1">x</p>'
            '<script type="application/json" id="fo-features">%s</script></body></html>' % json.dumps(doc))


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = features.main(argv)
    return code, out.getvalue()


class TestCatalogDrift(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.page = os.path.join(t.name, "zz.html")
        self.fam = os.path.join(t.name, "zz.features.json")
        with open(self.fam, "w") as f:
            json.dump(FAMILY, f)
        with open(self.page, "w") as f:
            f.write(page(OLD))

    def read(self):
        with open(self.page) as f:
            return f.read()

    def test_1_check_names_the_drift_and_writes_nothing(self):
        before = self.read()
        code, out = run(["sync", self.page, self.fam, "--check"])
        self.assertEqual(code, 1)
        self.assertIn("DRIFT", out)
        self.assertIn("1", out.split("DRIFT", 1)[1])
        self.assertNotIn(" 2", out.split("DRIFT", 1)[1].split(":", 1)[1])
        self.assertEqual(self.read(), before)

    def test_2_sync_then_check_is_clean(self):
        self.assertEqual(run(["sync", self.page, self.fam])[0], 0)
        code, out = run(["sync", self.page, self.fam, "--check"])
        self.assertEqual(code, 0)
        self.assertIn("in sync", out)
        with open(self.page, "w") as f:
            f.write("<html><body>no catalog</body></html>")
        self.assertEqual(run(["sync", self.page, self.fam, "--check"])[0], 2)
        self.assertEqual(self.read(), "<html><body>no catalog</body></html>")


class TestEmailsTemplate(unittest.TestCase):
    def test_3_emails_template_matches_its_family_list(self):
        code, out = run(["sync", os.path.join(TEMPLATES, "emails.html"),
                         os.path.join(TEMPLATES, "emails.features.json"), "--check"])
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
