#!/usr/bin/env python3
"""The variation batch's Drive mirror — found by name, updated in place,
nothing ever deleted (SI-34 (no Drive delete)).

    python3 tests/test_variations_drive.py

No key, no network, no PIL. The Google client is stubbed and Drive is a fake
held in memory; the fakes are COPIED from
new-workflow-design/builds/drive-pipe/test_gdrive_creator.py, not imported,
because that file runs its fakes inside subprocess scripts.
"""
import inspect
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE / "tools"))

# ---- the Google client, stubbed BEFORE any engine call ----------------------
UPLOADS = []


class MediaFileUpload(object):
    """What upload_file builds; it records the file name and nothing else."""

    def __init__(self, path, mimetype=None, resumable=None):
        UPLOADS.append(os.path.basename(path))


_gac = types.ModuleType("googleapiclient")
_gac.__path__ = []
_http = types.ModuleType("googleapiclient.http")
_http.MediaFileUpload = MediaFileUpload
_gac.http = _http
sys.modules["googleapiclient"] = _gac
sys.modules["googleapiclient.http"] = _http

import variations as V                          # noqa: E402
from gdrive_creator import engine as E          # noqa: E402


# ---- the fake Drive ----------------------------------------------------------
def parse(q):
    """Enough of the Drive query language to answer honestly."""
    nm = re.search(r"name = '((?:[^'\\]|\\.)*)'", q)
    parent = re.search(r"'([^']+)' in parents", q)
    mime = re.search(r"mimeType = '([^']+)'", q)
    name = None
    if nm:
        name = nm.group(1).replace("\\'", "'").replace("\\\\", "\\")
    return (name, parent.group(1) if parent else None,
            mime.group(1) if mime else None)


class Exec(object):
    def __init__(self, log, call, result):
        self.log, self.call, self.result = log, call, result

    def execute(self):
        self.log.append(self.call)
        return self.result


class Files(object):
    """list / create / update — and NO delete: a call to one is an error."""

    def __init__(self, d):
        self.d = d

    def list(self, **kw):
        name, parent, mime = parse(kw["q"])
        hits = []
        for fid in sorted(self.d.store):
            f = self.d.store[fid]
            if parent is not None and f["parent"] != parent:
                continue
            if mime is not None and f["mime"] != mime:
                continue
            if name is not None and f["name"] != name:
                continue
            hits.append({"id": fid, "name": f["name"], "size": "1"})
        return Exec(self.d.log, {"op": "files.list", "q": kw["q"]},
                    {"files": hits[:kw.get("pageSize", 100)]})

    def create(self, body=None, fields=None, media_body=None, **kw):
        fid = "id-%d" % (len(self.d.store) + 1)
        self.d.store[fid] = {"parent": (body.get("parents") or [""])[0],
                             "name": body["name"],
                             "mime": body.get("mimeType", "")}
        return Exec(self.d.log, {"op": "files.create", "name": body["name"],
                                 "mime": body.get("mimeType")}, {"id": fid})

    def update(self, fileId=None, fields=None, media_body=None, **kw):
        return Exec(self.d.log, {"op": "files.update", "fileId": fileId},
                    {"id": fileId})


class Drives(object):
    def __init__(self, d):
        self.d = d

    def list(self, **kw):
        return Exec(self.d.log, {"op": "drives.list"}, {"drives": list(self.d.shared)})


class Drive(object):
    def __init__(self, shared=True):
        self.store, self.log = {}, []
        self.shared = [{"id": "drive-sa", "name": "Team Drive"}] if shared else []

    def drives(self):
        return Drives(self)

    def files(self):
        return Files(self)

    def seed(self, fid, name, parent, folder=True):
        self.store[fid] = {"parent": parent, "name": name,
                           "mime": E.FOLDER_MIME if folder else "image/png"}
        return fid


def local_drop(root):
    out = Path(root) / "out"
    ad = out / "deliverable" / "ad-one"
    ad.mkdir(parents=True)
    (out / "deliverable" / "drop.csv").write_text("brief,ad_name\n")
    (ad / "00-baseline.png").write_bytes(b"base")
    (ad / "01-headline.png").write_bytes(b"head")
    (ad / "manifest.json").write_text("{}\n")
    return out


def seeded():
    fake = Drive()
    node = "drive-sa"
    for fid, name in [("f-runs", "runs"), ("f-machine", V.MACHINE),
                      ("f-brand", "zz-brand"), ("f-d1", "d1"),
                      ("f-deliv", "deliverable")]:
        node = fake.seed(fid, name, node)
    fake.seed("x-drop", "drop.csv", "f-deliv", folder=False)
    fake.seed("f-ad", "ad-one", "f-deliv")
    fake.seed("x-base", "00-baseline.png", "f-ad", folder=False)
    return fake


def creates(fake):
    return [c for c in fake.log if c["op"] == "files.create"]


class Mirror(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = local_drop(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_seeded(self):
        fake = seeded()
        fid, ids = V.mirror(self.out, "zz-brand", "d1", E, fake)
        return fake, fid, ids

    def test_mirror_updates_in_place_and_keeps_ids(self):
        fake, fid, ids = self.run_seeded()
        self.assertEqual(fid, "f-deliv")
        self.assertEqual(ids["drop.csv"], "x-drop")
        self.assertEqual(ids["ad-one/00-baseline.png"], "x-base")
        self.assertEqual(set(ids), {"drop.csv", "ad-one/00-baseline.png",
                                    "ad-one/01-headline.png", "ad-one/manifest.json"})
        seeded_names = {"runs", V.MACHINE, "zz-brand", "d1", "deliverable",
                        "drop.csv", "ad-one", "00-baseline.png"}
        made = creates(fake)
        self.assertFalse([c for c in made if c["name"] in seeded_names], made)
        self.assertEqual(sorted(c["name"] for c in made),
                         ["01-headline.png", "manifest.json"])
        self.assertFalse([c for c in made if c["mime"] == E.FOLDER_MIME], made)

    def test_a_second_run_creates_nothing(self):
        fake = Drive()
        _, first = V.mirror(self.out, "zz-brand", "d1", E, fake)
        before = len(creates(fake))
        self.assertTrue(before)
        _, second = V.mirror(self.out, "zz-brand", "d1", E, fake)
        self.assertEqual(len(creates(fake)), before)
        self.assertEqual(second, first)

    def test_nothing_is_ever_deleted(self):
        fake, _, _ = self.run_seeded()
        ops = {c["op"] for c in fake.log}
        self.assertLessEqual(ops, {"drives.list", "files.list",
                                   "files.create", "files.update"}, ops)
        self.assertFalse(hasattr(Files(fake), "delete"))

    def test_no_shared_assets_drive_is_named(self):
        with self.assertRaises(SystemExit) as cm:
            V.mirror(self.out, "zz-brand", "d1", E, Drive(shared=False))
        self.assertIn("Team Drive", str(cm.exception))


class Source(unittest.TestCase):
    def test_no_personal_mount_no_delete_in_source(self):
        for fn in (V.mirror, V._drive_folder, V._service):
            src = inspect.getsource(fn)
            for bad in ("rmtree", "copytree", "CloudStorage", "GoogleDrive-"):
                self.assertNotIn(bad, src, f"{fn.__name__} holds {bad!r}")
        self.assertNotIn("damon@", Path(V.__file__).read_text())


class Service(unittest.TestCase):
    def test_no_key_is_a_loud_skip(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("GDRIVE_SA_KEY", None)
            with mock.patch.object(V.DV, "service",
                                   side_effect=SystemExit("No GDRIVE_SA_KEY yet")):
                engine, svc, note = V._service()
        self.assertIsNone(engine)
        self.assertIsNone(svc)
        self.assertTrue(note.startswith("SKIP the Drive mirror — no GDRIVE_SA_KEY"), note)

    def test_a_key_with_a_missing_package_is_a_failure(self):
        with mock.patch.dict(os.environ, {"GDRIVE_SA_KEY": "x"}):
            with mock.patch.object(V.DV, "service", side_effect=SystemExit(
                    "gdrive-creator could not import googleapiclient.discovery")):
                with self.assertRaises(SystemExit):
                    V._service()


if __name__ == "__main__":
    print(f"python {sys.version_info[:2]}")
    r = unittest.main(exit=False, verbosity=2).result
    print(f"\n{r.testsRun - len(r.failures) - len(r.errors)}/{r.testsRun} passed "
          f"on python {sys.version_info[:2]}")
    sys.exit(0 if r.wasSuccessful() else 1)
