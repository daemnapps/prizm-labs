#!/usr/bin/env python3
"""PF-9c (share warns): template mode writes when the page's integrity holds.
Only a hard blocker (a lab-code door, an edited overlay) stops it; every other
finding prints as a "won't work on another machine yet" warning; a components/
door is routed through the person's own Claude; the CLI loads
components/system-integration/page_scan.py when it exists.

    python3 test_pf9c_share_warns.py

unittest, stdlib only, no network, never runs git: a fake runner answers
ls-files from a table and hash-object with the blob id of the file's bytes.
Fixtures are built in temporary roots from test_pf9_fixtures/, the way
test_pf9_share_check.py builds them. Runs under /usr/bin/python3 (3.9).
"""
import contextlib
import copy
import hashlib
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import features  # noqa: E402
import share  # noqa: E402

FIX = os.path.join(HERE, "test_pf9_fixtures")
TEMPLATE = "platform/views/viewers/_templates/sharefam.html"
FAMILY = "platform/views/viewers/_templates/sharefam.features.json"
DRAFT = "platform/views/viewers/fixp/drafts/sharefam--mine.html"
SCAN_FILE = "components/system-integration/page_scan.py"
RUN_LISTED = {"runs/fix/*.json": ["runs/fix/a.json"]}
CLEAR = (2, 4, 7, 9)  # a lab-page rule (note), a run file in git, not-built, layout


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def blob_id(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


DOC = features.load(os.path.join(FIX, "sharefam.features.json"))
PAGE = read(os.path.join(FIX, "sharefam.html"))


class FakeGit(object):
    def __init__(self, listed=None):
        self.calls = []
        self.listed = RUN_LISTED if listed is None else listed

    def __call__(self, argv, cwd):
        self.calls.append(list(argv))
        if argv[:3] == ["git", "ls-files", "--"]:
            return 0, "".join(h + "\n" for h in self.listed.get(argv[3], [])), ""
        if argv[:3] == ["git", "hash-object", "--"]:
            with open(os.path.join(cwd, argv[3]), "rb") as handle:
                return 0, blob_id(handle.read()) + "\n", ""
        return 0, "", ""


def only(*numbers, doc=DOC):
    doc = copy.deepcopy(doc)
    doc["features"] = [e for e in doc["features"] if e["n"] in numbers]
    return doc


def draft_of(template):
    sha = blob_id(template.encode("utf-8"))
    text = template.replace("<body>\n", '<body>\n<div data-personal-view="sharefam" '
                            'data-template-sha="%s" style="x">your personal sharefam</div>\n'
                            % sha, 1)
    return text.replace('<p id="hello">Hello</p>', '<p id="hello">Hello from fixp</p>', 1)


def tree(top):
    out = {}
    for base, _, names in os.walk(top):
        for name in names:
            path = os.path.join(base, name)
            with open(path, "rb") as handle:
                out[os.path.relpath(path, top)] = hashlib.sha256(handle.read()).hexdigest()
    return out


class ShareWarns(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pf9c-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def build(self, doc, page_text=None):
        write(os.path.join(self.root, TEMPLATE), PAGE)
        write(os.path.join(self.root, FAMILY), features.dumps(doc))
        write(os.path.join(self.root, DRAFT), draft_of(PAGE) if page_text is None else page_text)

    def template(self):
        return read(os.path.join(self.root, TEMPLATE))

    def cli(self, *extra, runner=None, scan=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = share.main([DRAFT, "--person", "fixp", "--no-share"] + list(extra),
                              root=self.root, runner=runner or FakeGit(), scan=scan)
        return code, out.getvalue().splitlines()

    def share(self, person="fixp", scan=lambda t: []):
        return share.share_template(DRAFT, person=person, root=self.root, runner=FakeGit(),
                                    scan=scan, share=False)

    def warnings(self, lines):
        heads = [i for i, line in enumerate(lines) if line.startswith("won't work on another "
                                                                      "machine yet (")]
        self.assertEqual(len(heads), 1, lines)
        return [line for line in lines[heads[0] + 1:] if line.startswith("  ")]

    # (a)
    def test_after_card_and_not_in_git_warn_and_write(self):
        doc = only(3, 4, 9)
        doc["features"][0]["kind"] = "data"  # an after-card D feature
        self.assertEqual(features.validate(doc), [])
        self.build(doc)
        code, lines = self.cli(runner=FakeGit(listed={}))
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].startswith("template: %s is now fixp's version" % TEMPLATE), lines)
        self.assertIn("won't work on another machine yet (2):", lines)
        warns = self.warnings(lines)
        self.assertTrue([w for w in warns if w.startswith("  D3: ") and "after-card" in w
                         and " — fix: " in w and w.endswith("(fix pictures)")], warns)
        self.assertTrue([w for w in warns if w.startswith("  D4: ") and "not in git" in w
                         and w.endswith("(fix runs)")], warns)
        self.assertNotIn("data-personal-view", self.template())
        self.assertIn("Hello from fixp", self.template())

    # (b)
    def test_lab_door_blocks(self):
        self.build(only(*(CLEAR + (5,))))
        before = tree(self.root)
        code, lines = self.cli(scan=lambda t: ["one warning"])
        self.assertEqual(code, 2, lines)
        self.assertEqual(tree(self.root), before)
        self.assertEqual(self.template(), PAGE)
        self.assertTrue(lines[0].startswith("blocked: %s stays as it is" % TEMPLATE), lines)
        self.assertTrue(lines[1].startswith("  A5: calls fixq's lab server"), lines)
        self.assertLess(lines.index("  A5: %s" % lines[1][6:]),
                        lines.index("won't work on another machine yet (1):"), lines)

    # (c)
    def test_component_door_is_not_a_blocker(self):
        self.build(only(*(CLEAR + (6,))))
        out = self.share()
        self.assertEqual(out["result"], "template", out)
        self.assertEqual(out["written"], [TEMPLATE])
        self.assertEqual([b for b in out["check"]["blockers"] if b["tag"] == "A6"], [])
        self.assertEqual(out["check"]["use"], "pass")
        self.assertIn("note: %s" % (share.NOTE_BUTTONS % 1), out["lines"])
        self.assertIn("1 through a component door", share.NOTE_BUTTONS % 1)
        self.assertNotEqual(self.template(), PAGE)

    # (d)
    def test_edited_overlay_blocks(self):
        self.build(only(*CLEAR), draft_of(PAGE).replace("/* the overlay */", "/* mine */"))
        before = tree(self.root)
        out = self.share()
        self.assertEqual(out["result"], "blocked", out)
        self.assertEqual(out["written"], [])
        self.assertEqual(tree(self.root), before)
        hard = [b for b in out["check"]["blockers"] if b["hard"]]
        self.assertEqual([(b["tag"], b["what"]) for b in hard],
                         [("page", "the overlay block was edited; it is component-owned")])

    # (e)
    def test_non_owner_refused(self):
        self.build(dict(only(*CLEAR), owner="fixo"))
        before = tree(self.root)
        out = self.share()
        self.assertEqual(out["result"], "refused", out)
        self.assertEqual(out["lines"], ["refused: only fixo shares sharefam as its template"])
        self.assertEqual(out["written"], [])
        self.assertEqual(tree(self.root), before)

    # (f)
    def test_scan_finding_is_a_warning(self):
        self.build(only(*CLEAR))
        out = self.share(scan=lambda t: ["127.0.0.1:8870 in a link"])
        self.assertEqual(out["result"], "template", out)
        found = [b for b in out["check"]["blockers"] if b["what"] == "127.0.0.1:8870 in a link"]
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["level"], found[0]["hard"]), ("VIEW", False))
        self.assertIn("won't work on another machine yet (1):", out["lines"])
        self.assertTrue([w for w in self.warnings(out["lines"])
                         if w.startswith("  page: 127.0.0.1:8870 in a link — fix: ")],
                        out["lines"])
        self.assertNotEqual(self.template(), PAGE)

    # (g)
    def test_cli_loads_page_scan(self):
        self.build(only(*CLEAR))
        write(os.path.join(self.root, SCAN_FILE),
              "def scan(page_text, features_doc):\n"
              "    assert 'Hello from fixp' in page_text\n"
              "    return ['stub finding for %s' % features_doc['owner']]\n")
        code, lines = self.cli()
        self.assertEqual(code, 0, lines)
        self.assertTrue([w for w in self.warnings(lines)
                         if w.startswith("  page: stub finding for fixp — fix: ")], lines)
        self.assertIn("note: %s" % share.NOTE_SCAN, lines)
        self.assertNotIn("note: %s" % share.NOTE_NO_SCAN, lines)

    def test_cli_without_page_scan(self):
        self.build(only(*CLEAR))
        code, lines = self.cli()
        self.assertEqual(code, 0, lines)
        self.assertIn("note: %s" % share.NOTE_NO_SCAN, lines)
        self.assertNotIn("note: %s" % share.NOTE_SCAN, lines)

    def test_cli_page_scan_that_raises_on_import(self):
        self.build(only(*CLEAR))
        write(os.path.join(self.root, SCAN_FILE), "raise RuntimeError('half-built')\n")
        code, lines = self.cli()
        self.assertEqual(code, 0, lines)
        errors = [line for line in lines if "half-built" in line]
        self.assertEqual(len(errors), 1, lines)
        self.assertTrue(errors[0].startswith("note: page scan not loaded from %s: RuntimeError"
                                             % SCAN_FILE), errors)
        self.assertNotIn("note: %s" % share.NOTE_NO_SCAN, lines)
        self.assertNotEqual(self.template(), PAGE)


if __name__ == "__main__":
    unittest.main()
