#!/usr/bin/env python3
"""SI-123 (Drive through engine): image-teardown reaches Drive only through
gdrive-creator (triage page 8).

    /usr/bin/python3 tools/image-teardown/tests/test_drive_through_engine.py

Source: no `drives().list` and no bare `permissions().create` left in
deliver.py, pack.py or variations.py — the shared drive is found with
`engine.shared_drive_id`, and sharing goes through `engine.share`.
Behaviour, against a fake Drive (offline, no key): deliver's `upload` is the
engine's upload plus a reader share, and its update-in-place query now
escapes an apostrophe; pack's `upload_big` keeps its own chunked loop but
finds the existing file and shares through the engine; deliver's
`drive_root` refuses with the drive's name when the drive is absent.
"""
import os
import re
import socket
import sys
import tempfile
import types
import unittest
import unittest.mock
from pathlib import Path

LANE = Path(__file__).resolve().parent.parent
TOOLS = LANE / "tools"
sys.path.insert(0, str(TOOLS))

FILES = ("deliver.py", "pack.py", "variations.py")


# ---- the Google client, stood in for each test -------------------------------
class MediaFileUpload(object):
    """What both uploaders build; it keeps what it was given."""

    def __init__(self, path, mimetype=None, resumable=None, chunksize=None):
        self.path, self.mimetype = path, mimetype
        self.resumable, self.chunksize = resumable, chunksize


def google_stub():
    gac = types.ModuleType("googleapiclient")
    gac.__path__ = []
    http = types.ModuleType("googleapiclient.http")
    http.MediaFileUpload = MediaFileUpload
    gac.http = http
    return {"googleapiclient": gac, "googleapiclient.http": http}


# ---- the fake Drive ------------------------------------------------------------
class Req(object):
    """A request: `execute()` for the one-write calls, `next_chunk()` for the
    chunked one — both log the call once, when it is sent."""

    def __init__(self, log, call, result):
        self.log, self.call, self.result = log, call, result

    def execute(self):
        self.log.append(self.call)
        return self.result

    def next_chunk(self, num_retries=0):
        self.log.append(dict(self.call, chunked=True, num_retries=num_retries))
        return None, self.result


def query_name(q):
    m = re.search(r"name = '((?:[^'\\]|\\.)*)'", q)
    return m.group(1).replace("\\'", "'").replace("\\\\", "\\") if m else None


class Files(object):
    def __init__(self, d):
        self.d = d

    def list(self, **kw):
        name = query_name(kw["q"])
        parent = re.search(r"'([^']+)' in parents", kw["q"]).group(1)
        hits = [{"id": fid} for fid, f in sorted(self.d.store.items())
                if f["name"] == name and f["parent"] == parent]
        return Req(self.d.log, {"op": "files.list", "q": kw["q"]}, {"files": hits})

    def create(self, body=None, media_body=None, **kw):
        fid = "new-%d" % (len(self.d.store) + 1)
        self.d.store[fid] = {"name": body["name"], "parent": body["parents"][0]}
        return Req(self.d.log, dict(kw, op="files.create", name=body["name"],
                                    media=media_body), {"id": fid})

    def update(self, fileId=None, media_body=None, **kw):
        return Req(self.d.log, dict(kw, op="files.update", fileId=fileId,
                                    media=media_body), {"id": fileId})


class Permissions(object):
    def __init__(self, d):
        self.d = d

    def list(self, **kw):
        return Req(self.d.log, {"op": "permissions.list", "fileId": kw["fileId"]},
                   {"permissions": []})

    def create(self, **kw):
        return Req(self.d.log, dict(kw, op="permissions.create"), {"id": "perm"})


class Drives(object):
    def __init__(self, d):
        self.d = d

    def list(self, **kw):
        return Req(self.d.log, {"op": "drives.list"}, {"drives": list(self.d.shared)})


class Drive(object):
    def __init__(self, shared=True):
        self.store, self.log = {}, []
        self.shared = [{"id": "drive-sa", "name": "Team Drive"}] if shared else []

    def files(self):
        return Files(self)

    def permissions(self):
        return Permissions(self)

    def drives(self):
        return Drives(self)

    def ops(self, op):
        return [c for c in self.log if c["op"] == op]


# ---- the source -----------------------------------------------------------------
class Source(unittest.TestCase):
    def test_no_raw_drives_list_and_no_bare_permission_create(self):
        for fn in FILES:
            src = (TOOLS / fn).read_text()
            self.assertIsNone(re.search(r"drives\(\)\s*\.\s*list", src),
                              "%s still lists drives itself" % fn)
            self.assertIsNone(re.search(r"permissions\(\)\s*\.\s*create", src),
                              "%s still creates a permission itself" % fn)

    def test_each_finds_the_drive_through_the_engine(self):
        for fn in FILES:
            self.assertIn('shared_drive_id("Team Drive"', (TOOLS / fn).read_text(),
                          "%s does not ask the engine for the drive" % fn)


# ---- the behaviour ---------------------------------------------------------------
class Offline(unittest.TestCase):
    def setUp(self):
        self.env = unittest.mock.patch.dict(os.environ)
        self.env.start()
        os.environ.pop("GDRIVE_SA_KEY", None)
        self.mods = unittest.mock.patch.dict(sys.modules, google_stub())
        self.mods.start()
        self.timeout = socket.getdefaulttimeout()
        self.tmp = tempfile.TemporaryDirectory()
        import deliver
        import pack
        self.D, self.P = deliver, pack

    def tearDown(self):
        self.tmp.cleanup()
        socket.setdefaulttimeout(self.timeout)
        self.mods.stop()
        self.env.stop()

    def file(self, name, data=b"bytes"):
        p = Path(self.tmp.name) / name
        p.write_bytes(data)
        return p


class Deliver(Offline):
    def test_a_new_file_is_created_and_shared_to_readers(self):
        fake = Drive()
        fid = self.D.upload(fake, self.file("draft.png"), "folder-1")
        self.assertEqual([c["name"] for c in fake.ops("files.create")], ["draft.png"])
        self.assertEqual(fake.store[fid]["parent"], "folder-1")
        made = fake.ops("files.create")[0]
        self.assertIs(made["supportsAllDrives"], True)
        self.assertEqual(made["media"].mimetype, "image/png")
        share = fake.ops("permissions.create")
        self.assertEqual(len(share), 1)
        self.assertEqual(share[0]["fileId"], fid)
        self.assertEqual(share[0]["body"], {"type": "anyone", "role": "reader"})

    def test_an_existing_file_is_updated_in_place_under_its_given_name(self):
        fake = Drive()
        fake.store["old-1"] = {"name": "source.jpg", "parent": "folder-1"}
        fid = self.D.upload(fake, self.file("swipe-0042.jpg"), "folder-1", "source.jpg")
        self.assertEqual(fid, "old-1", "the id a link was handed out for must stay")
        self.assertEqual(fake.ops("files.create"), [])
        self.assertEqual([c["fileId"] for c in fake.ops("files.update")], ["old-1"])

    def test_an_apostrophe_in_a_name_is_escaped(self):
        fake = Drive()
        fake.store["old-2"] = {"name": "don't.md", "parent": "folder-1"}
        fid = self.D.upload(fake, self.file("don't.md"), "folder-1")
        self.assertEqual(fid, "old-2")
        self.assertIn("name = 'don\\'t.md'", fake.ops("files.list")[0]["q"])

    def test_a_refused_share_does_not_lose_the_upload(self):
        fake = Drive()

        def refuse(**kw):
            raise RuntimeError("403 the Workspace refuses anyone links")
        fake.permissions = lambda: types.SimpleNamespace(
            list=lambda **kw: Req(fake.log, {"op": "permissions.list"}, {"permissions": []}),
            create=refuse)
        fid = self.D.upload(fake, self.file("brief.md"), "folder-1")
        self.assertIn(fid, fake.store)

    def test_drive_root_walks_from_the_shared_drive(self):
        from gdrive_creator import engine
        fake = Drive()
        made = []

        def folder(name, parent, svc=None):
            made.append((name, parent))
            return "f-" + name
        walker = types.SimpleNamespace(shared_drive_id=engine.shared_drive_id,
                                       folder=folder)
        self.assertEqual(self.D.drive_root(walker, fake), "f-" + self.D.ROOT[-1])
        self.assertEqual(made[0][1], "drive-sa")
        self.assertEqual([m[0] for m in made], list(self.D.ROOT))

    def test_drive_root_without_the_drive_says_so(self):
        from gdrive_creator import engine
        with self.assertRaises(SystemExit) as cm:
            self.D.drive_root(engine, Drive(shared=False))
        self.assertIn("Team Drive", str(cm.exception))


class Pack(Offline):
    def test_big_upload_keeps_its_chunks_and_shares_through_the_engine(self):
        fake = Drive()
        fid = self.P.upload_big(fake, self.file("pack.zip"), "folder-1")
        made = fake.ops("files.create")
        self.assertEqual(len(made), 1)
        self.assertTrue(made[0]["chunked"])
        self.assertEqual(made[0]["num_retries"], 5)
        self.assertEqual(made[0]["media"].chunksize, 8 * 1024 * 1024)
        self.assertIs(made[0]["media"].resumable, True)
        share = fake.ops("permissions.create")
        self.assertEqual([(s["fileId"], s["body"]["role"]) for s in share], [(fid, "reader")])

    def test_big_upload_finds_the_existing_pack_and_updates_it(self):
        fake = Drive()
        fake.store["pack-old"] = {"name": "it's-a-pack.zip", "parent": "folder-1"}
        fid = self.P.upload_big(fake, self.file("it's-a-pack.zip"), "folder-1")
        self.assertEqual(fid, "pack-old")
        self.assertEqual(fake.ops("files.create"), [])
        self.assertEqual([c["fileId"] for c in fake.ops("files.update")], ["pack-old"])
        self.assertIn("name = 'it\\'s-a-pack.zip'", fake.ops("files.list")[0]["q"])


if __name__ == "__main__":
    print("python %s" % (sys.version_info[:2],))
    r = unittest.main(exit=False, verbosity=2).result
    print("\n%d/%d passed on python %s" % (
        r.testsRun - len(r.failures) - len(r.errors), r.testsRun,
        sys.version_info[:2]))
    sys.exit(0 if r.wasSuccessful() else 1)
