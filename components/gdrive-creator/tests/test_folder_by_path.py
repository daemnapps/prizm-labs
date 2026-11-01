#!/usr/bin/env python3
"""LD-11 (stills by Drive API): a "Shared Assets/a/b/c" label read to a folder
id, and that folder's files listed — the two calls a machine needs to read a
folder it cannot see on the mount.

    /usr/bin/python3 components/gdrive-creator/tests/test_folder_by_path.py

`folder_by_path(label, svc=None)` walks from the shared drive down each part
and answers the leaf's id, or None when any part is missing — and makes
nothing. `list_files(folder_id, svc=None)` answers every non-folder child,
across pages.

Offline, stdlib only, no key: a fake `svc` (the engine's own seam).
"""
import os
import re
import sys
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
sys.path.insert(0, str(COMPONENT))

from gdrive_creator import engine as E   # noqa: E402  imports nothing from Google

FOLDER = E.FOLDER_MIME


class Req(object):
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class Drive(object):
    """Shared drives + a tree of children by parent id. `page` cuts every
    listing into pages of that many, so paging is exercised."""

    def __init__(self, drives, children, page=2):
        self.drives_ = drives               # [{id, name}]
        self.children = children            # parent id -> [{id, name, mimeType}]
        self.page = page
        self.calls = []

    def drives(self):
        d = self

        class Drives(object):
            def list(self, **kw):
                d.calls.append(("drives.list", kw))
                return Req({"drives": list(d.drives_)})
        return Drives()

    def files(self):
        d = self

        class Files(object):
            def list(self, **kw):
                d.calls.append(("files.list", kw))
                parent = re.search(r"'([^']+)' in parents", kw["q"]).group(1)
                rows = list(d.children.get(parent, []))
                if f"mimeType = '{FOLDER}'" in kw["q"]:
                    rows = [r for r in rows if r["mimeType"] == FOLDER]
                # deliberately NOT honouring "mimeType !=": the engine must drop folders itself
                start = int(kw.get("pageToken") or 0)
                out = {"files": rows[start:start + d.page]}
                if start + d.page < len(rows):
                    out["nextPageToken"] = str(start + d.page)
                return Req(out)

            def create(self, **kw):
                raise AssertionError("folder_by_path must never create")
        return Files()


def tree():
    f = lambda i, n: {"id": i, "name": n, "mimeType": FOLDER}
    return Drive(
        drives=[{"id": "d-other", "name": "Other"}, {"id": "d-sa", "name": "Shared Assets"}],
        children={
            "d-sa": [f("x1", "lab"), f("x2", "runs"), f("s", "swipe")],
            "s": [f("p", "paid"), f("o", "organic")],
            "o": [f("x3", "sounds"), f("x4", "kits"), f("b", "brand-x")],
            "b": [f("ph", "photos")],
            "ph": [
                {"id": "f1", "name": "01.jpg", "mimeType": "image/jpeg"},
                f("sub", "nested"),
                {"id": "f2", "name": "02.png", "mimeType": "image/png"},
                {"id": "f3", "name": "notes.md", "mimeType": "text/markdown"},
                f("sub2", "more"),
                {"id": "f4", "name": "03.jpeg", "mimeType": "image/jpeg"},
            ],
        })


class FolderByPath(unittest.TestCase):

    def setUp(self):
        env = dict(os.environ)
        env.pop("GDRIVE_SA_KEY", None)
        env["KEYS_NO_FALLBACK"] = "1"               # step 1.6: the real key file never counts in a test
        p = unittest.mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)

    def test_walks_drive_then_each_part_to_the_leaf(self):
        svc = tree()
        got = E.folder_by_path("Shared Assets/swipe/organic/brand-x/photos", svc=svc)
        self.assertEqual(got, "ph")
        lists = [kw for c, kw in svc.calls if c == "files.list"]
        # one parent per part, in order — the walk, not a drive-wide search
        parents = [re.search(r"'([^']+)' in parents", kw["q"]).group(1) for kw in lists]
        self.assertEqual(sorted(set(parents), key=parents.index), ["d-sa", "s", "o", "b"])
        for kw in lists:
            self.assertTrue(kw["supportsAllDrives"])
            self.assertTrue(kw["includeItemsFromAllDrives"])

    def test_a_missing_part_is_none(self):
        self.assertIsNone(E.folder_by_path("Shared Assets/swipe/organic/nobody/photos",
                                           svc=tree()))
        self.assertIsNone(E.folder_by_path("Shared Assets/swipe/organic/brand-x/photos/x",
                                           svc=tree()))

    def test_a_missing_drive_is_none(self):
        self.assertIsNone(E.folder_by_path("No Such Drive/swipe", svc=tree()))

    def test_the_drive_alone_is_its_id_and_an_empty_label_is_none(self):
        self.assertEqual(E.folder_by_path("Shared Assets", svc=tree()), "d-sa")
        self.assertIsNone(E.folder_by_path("", svc=tree()))

    def test_slashes_at_the_ends_do_not_matter(self):
        self.assertEqual(E.folder_by_path("/Shared Assets/swipe/paid/", svc=tree()), "p")


class ListFiles(unittest.TestCase):

    def test_pages_across_next_page_token_and_drops_folders(self):
        svc = tree()
        got = E.list_files("ph", svc=svc)
        self.assertEqual(got, [
            {"id": "f1", "name": "01.jpg", "mimeType": "image/jpeg"},
            {"id": "f2", "name": "02.png", "mimeType": "image/png"},
            {"id": "f3", "name": "notes.md", "mimeType": "text/markdown"},
            {"id": "f4", "name": "03.jpeg", "mimeType": "image/jpeg"},
        ])
        lists = [kw for c, kw in svc.calls if c == "files.list"]
        self.assertEqual(len(lists), 3)                       # 6 children, pages of 2
        self.assertEqual([kw.get("pageToken") for kw in lists], [None, "2", "4"])
        for kw in lists:
            self.assertIn("trashed = false", kw["q"])
            self.assertTrue(kw["supportsAllDrives"])
            self.assertTrue(kw["includeItemsFromAllDrives"])

    def test_an_empty_folder_is_an_empty_list(self):
        self.assertEqual(E.list_files("nothing-here", svc=tree()), [])


if __name__ == "__main__":
    unittest.main()
