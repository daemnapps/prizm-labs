#!/usr/bin/env python3
"""QB-9 (the team statics): reach.subfolders lists one folder's child folders, in name order, read-only, one listing per
page; files and trashed folders are not among them. Offline: a fake Drive service, no key, no network.

    /usr/bin/python3 components/gdrive-creator/tests/test_qb9_subfolders.py
"""
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from gdrive_creator import reach  # noqa: E402

FOLDER = "application/vnd.google-apps.folder"


class Svc(object):
    """files().list(q=..., pageToken=...) over a fixed set of pages; records every call; any other verb fails."""

    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def files(self):
        return self

    def list(self, **kw):
        self.calls.append(kw)
        page = self.pages[int(kw.get("pageToken") or 0)]
        nxt = int(kw.get("pageToken") or 0) + 1
        out = {"files": page}
        if nxt < len(self.pages):
            out["nextPageToken"] = str(nxt)
        return type("R", (), {"execute": lambda _s: out})()


class Subfolders(unittest.TestCase):
    def test_every_page_in_name_order(self):
        svc = Svc([[{"id": "2", "name": "brand-b"}], [{"id": "1", "name": "brand-a"}]])
        self.assertEqual(reach.subfolders("root", svc=svc), [{"id": "1", "name": "brand-a"}, {"id": "2", "name": "brand-b"}])
        self.assertEqual(len(svc.calls), 2)

    def test_the_query_asks_for_live_folders_of_that_parent_only(self):
        svc = Svc([[]])
        self.assertEqual(reach.subfolders("abc", svc=svc), [])
        q = svc.calls[0]["q"]
        self.assertIn("'abc' in parents", q)
        self.assertIn("trashed = false", q)
        self.assertIn(FOLDER, q)
        self.assertTrue(svc.calls[0]["supportsAllDrives"])


if __name__ == "__main__":
    unittest.main()
