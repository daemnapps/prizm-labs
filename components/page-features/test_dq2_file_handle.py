#!/usr/bin/env python3
"""DQ-2 (file handle closed): `dev_issues.py file <path>` closes the list file it reads.

Runs `dev_issues.py file <list> --by developer --dry-run --root <fixture repo>` in a subprocess under
`sys.executable -W error::ResourceWarning` and asserts exit 0 and no "ResourceWarning" on stderr. Before the fix the
bare `open(...).read()` left the handle to the garbage collector, which printed a ResourceWarning on every run.

The fixture repo is built here, in a temp folder (no fixture files under components/). Stdlib only, Python 3.9.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "dev_issues.py")
TASKS = "platform/data/records/tasks/"
ITEMS = [
    {"kind": "issue", "ref": "1", "title": "A list file is left open", "quote": "close it", "session": "dq2a01"},
    {"kind": "follow-up", "ref": "2", "title": "Tell the owner after", "quote": "tell email_lead", "session": "dq2a01",
     "parent": "1", "person": "developer"},
]


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


def fixture():
    """A temp workspace with one person, an empty id-tag file and an empty tasks folder."""
    root = os.path.realpath(tempfile.mkdtemp(prefix="dq2-"))
    os.makedirs(os.path.join(root, "brands"))
    os.makedirs(os.path.join(root, TASKS))
    write(root, "team/people/developer/identity.json",
          json.dumps({"person": "developer", "emails": [{"address": "developer@example.com"}]}))
    write(root, "team/id-tags.json", json.dumps({"_readme": "fixture"}))
    write(root, "items.json", json.dumps(ITEMS))
    return root


class FileClosesItsList(unittest.TestCase):

    def setUp(self):
        self.root = fixture()
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_no_resource_warning(self):
        before = sorted(os.listdir(os.path.join(self.root, TASKS)))
        p = subprocess.run([sys.executable, "-W", "error::ResourceWarning", SCRIPT, "file",
                            os.path.join(self.root, "items.json"), "--by", "developer", "--dry-run",
                            "--now", "2026-10-30T06:00:00Z", "--root", self.root],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("ResourceWarning", p.stderr)
        self.assertIn("Would file", p.stdout)
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, TASKS))), before, "a dry run writes nothing")


if __name__ == "__main__":
    unittest.main()
