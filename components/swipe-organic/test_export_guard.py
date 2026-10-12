#!/usr/bin/env python3
"""SI-111 (organic one locator), swipe-organic#32: the public export replaces
only its OWN previous copy (O5b (export replace is deploy)). A --site folder
that is not the export's — no index.json carrying `feeds` and `posts` — is
refused before anything is deleted, and every file in it stays.

    /usr/bin/python3 components/swipe-organic/test_export_guard.py

Offline: build, scan and sizes are patched, so no record is read, no picture
made and nothing pushed. Every folder is a tempfile folder.
"""
import json, sys, tempfile, unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import feedsexport as FE  # noqa: E402

OWN_INDEX = {"updated": "Updated 1 Jan 2026", "feeds": [], "posts": 0, "ads": 0}


def tree(root):
    """Every file under root, with its bytes."""
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


class SiteIsOurs(unittest.TestCase):

    def test_missing_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(FE.site_is_ours(Path(tmp) / "data"))

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(FE.site_is_ours(Path(tmp)))

    def test_feedsexport_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.json").write_text(json.dumps(OWN_INDEX))
            (Path(tmp) / "cards").mkdir()
            self.assertTrue(FE.site_is_ours(Path(tmp)))

    def test_other_files_no_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "notes.md").write_text("somebody's work\n")
            self.assertFalse(FE.site_is_ours(Path(tmp)))

    def test_index_without_feeds_and_posts(self):
        for body in (json.dumps({"feeds": []}), json.dumps({"posts": 3}),
                     json.dumps(["feeds", "posts"]), "not json"):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "index.json").write_text(body)
                self.assertFalse(FE.site_is_ours(Path(tmp)))

    def test_a_file_is_not_a_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "data"
            f.write_text("x")
            self.assertFalse(FE.site_is_ours(f))


class ExportMain(unittest.TestCase):

    def run_main(self, root, site):
        records = root / "records"
        (records / "avatar-feeds").mkdir(parents=True)

        def build(records, ws, stage, old, repix):
            stage.mkdir(parents=True)
            (stage / "index.json").write_text(json.dumps(OWN_INDEX))
            return OWN_INDEX, 0, set()

        argv = ["feedsexport.py", "--records", str(records), "--site", str(site), "--first"]
        with unittest.mock.patch.object(FE, "build", build), \
             unittest.mock.patch.object(FE, "scan", lambda stage, ids: []), \
             unittest.mock.patch.object(FE, "sizes", lambda stage, old: (0, 0, 0)), \
             unittest.mock.patch.object(sys, "argv", argv):
            FE.main()

    def test_refuses_a_folder_that_is_not_its_own(self):
        for files in ({"notes.md": b"somebody's work\n", "sub/keep.txt": b"keep"},
                      {"index.json": b'{"title": "another site"}', "page.html": b"<p>x</p>"}):
            with self.subTest(files=sorted(files)), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                site = root / "site" / "data"
                for rel, body in files.items():
                    (site / rel).parent.mkdir(parents=True, exist_ok=True)
                    (site / rel).write_bytes(body)
                before = tree(site)
                with self.assertRaises(SystemExit) as cm:
                    self.run_main(root, site)
                self.assertNotIn(cm.exception.code, (0, None))
                self.assertIn("REFUSED", str(cm.exception.code))
                self.assertIn("nothing deleted", str(cm.exception.code))
                self.assertEqual(tree(site), before)

    def test_replaces_its_own_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / "site" / "data"
            (site / "cards").mkdir(parents=True)
            (site / "cards" / "old.json").write_text("{}")
            (site / "index.json").write_text(json.dumps(dict(OWN_INDEX, posts=9)))
            self.run_main(root, site)
            self.assertEqual(json.loads((site / "index.json").read_text()), OWN_INDEX)
            self.assertFalse((site / "cards" / "old.json").exists())


if __name__ == "__main__":
    unittest.main()
