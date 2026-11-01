"""The API-first Shared Assets layer (gdrive_creator/shared.py, 20 Oct 2026). Offline: a fake Drive, no key, no
network. What it must never do: touch anything on the Drive other than read and upload, or remove a file outside
its own local copy."""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from gdrive_creator import shared as SH, reach as R  # noqa: E402

FOLDER = "application/vnd.google-apps.folder"


class FakeDrive:
    """A shared drive: nodes {id: {name, parent, mime, mtime, data}}; change feed as a list."""
    def __init__(self):
        self.nodes = {"root": {"name": "Shared Assets", "parent": None, "mime": FOLDER}}
        self.feed, self.n = [], 0

    def add(self, name, parent, data=None, mime=None, mtime="t1"):
        self.n += 1
        i = "id%d" % self.n
        self.nodes[i] = {"name": name, "parent": parent, "mime": mime or (FOLDER if data is None else "text/plain"),
                         "mtime": mtime, "data": data}
        return i

    def files(self):
        d = self

        class L:
            def list(self, q=None, **kw):
                parent = re.search(r"'([^']+)' in parents", q).group(1)
                kids = [{"id": i, "name": n["name"], "mimeType": n["mime"], "modifiedTime": n.get("mtime"),
                         "size": str(len(n.get("data") or b""))} for i, n in d.nodes.items() if n["parent"] == parent]
                return mock.Mock(execute=lambda: {"files": kids})
        return L()

    def changes(self):
        d = self

        class C:
            def getStartPageToken(self, **kw):
                return mock.Mock(execute=lambda: {"startPageToken": str(len(d.feed))})

            def list(self, pageToken=None, **kw):
                out = d.feed[int(pageToken):]
                return mock.Mock(execute=lambda: {"changes": out, "newStartPageToken": str(len(d.feed))})
        return C()


class Engine:
    FOLDER_MIME = FOLDER

    def __init__(self, drive):
        self.d = drive

    def service(self):
        return self.d

    def folder_by_path(self, label, svc=None):
        cur = "root"
        for part in label.split("/")[1:]:
            cur = next((i for i, n in self.d.nodes.items() if n["parent"] == cur and n["name"] == part
                        and n["mime"] == FOLDER), None)
            if cur is None:
                return None
        return cur

    def find_file(self, svc, name, parent, mime=None):
        i = next((i for i, n in self.d.nodes.items() if n["parent"] == parent and n["name"] == name), None)
        return {"id": i} if i else None

    def get_media(self, iid, dest, svc=None):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(self.d.nodes[iid]["data"])
        return dest


class Shared(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"GDRIVE_SA_KEY": "x", "DRIVE_CACHE": self.tmp.name})
        self.env.start()
        self.d = FakeDrive()
        self.meta = self.d.add("meta", "root")
        card = self.d.add("a", self.d.add("image", self.d.add("1-check", self.d.add("brand", self.meta))))
        self.card_json = self.d.add("card.json", card, b'{"v": 1}')
        self.big = self.d.add("clip.mp4", card, b"x" * 50)
        E = Engine(self.d)
        self.p = [mock.patch.object(R, "_engine", lambda: E), mock.patch.object(R, "shared_assets_id", lambda svc: "root")]
        for x in self.p:
            x.start()
        SH._SYNCED.clear()

    def tearDown(self):
        for x in self.p:
            x.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_the_folder_comes_down_and_want_leaves_big_files_on_the_drive(self):
        d = SH.folder("meta", want=lambda rel, size: size < 10)
        self.assertEqual((d / "brand/1-check/image/a/card.json").read_bytes(), b'{"v": 1}')
        self.assertFalse((d / "brand/1-check/image/a/clip.mp4").exists())

    def test_a_change_on_the_drive_arrives_through_the_change_feed(self):
        d = SH.folder("meta")
        self.d.nodes[self.card_json].update(data=b'{"v": 2}', mtime="t2")
        self.d.feed.append({"fileId": self.card_json, "file": {"name": "card.json", "parents": [self.d.nodes[self.card_json]["parent"]],
                                                                "mimeType": "text/plain", "modifiedTime": "t2", "size": "8"}})
        SH._SYNCED.clear()
        SH.folder("meta")
        self.assertEqual((d / "brand/1-check/image/a/card.json").read_bytes(), b'{"v": 2}')

    def test_a_file_gone_from_the_drive_leaves_the_local_copy_only(self):
        d = SH.folder("meta")
        self.d.feed.append({"fileId": self.big, "removed": True})
        SH._SYNCED.clear()
        SH.folder("meta")
        self.assertFalse((d / "brand/1-check/image/a/clip.mp4").exists())
        self.assertIn(self.big, self.d.nodes)                 # still on the Drive

    def test_save_uploads_to_the_same_place(self):
        d = SH.folder("meta")
        f = d / "brand/1-check/image/a/card.json"
        with mock.patch.object(R, "put", return_value=("api", ["x"], None)) as put:
            SH.save(f)
        self.assertEqual(put.call_args[0][1], ["meta", "brand", "1-check", "image", "a"])

    def test_on_the_drive_folder_route_save_does_nothing(self):
        with mock.patch.object(R, "put") as put:
            self.assertEqual(SH.save(Path(self.tmp.name).parent / "elsewhere.json"), ("mount", None))
        put.assert_not_called()

    def test_nothing_on_the_drive_is_deleted_moved_or_renamed(self):
        src = (HERE.parent / "gdrive_creator" / "shared.py").read_text()
        bad = re.compile(r"\.delete\(|emptyTrash|removeParents|addParents|trashed\s*[\"']?\s*[:=]\s*True|"
                         r"files\(\)\.update|files\(\)\.copy")
        self.assertIsNone(bad.search(src))
        # the only local removal is guarded to the cache
        self.assertIn("startswith(str(cache_home().resolve()))", src)


if __name__ == "__main__":
    unittest.main()
