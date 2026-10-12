#!/usr/bin/env python3
"""drive_link — step [10], the Drive mirror. stdlib only, no key, no network.

    /usr/bin/python3 static/tests/test_drive_link.py

  a  every script the static tool invokes by path is there to invoke
  b  drive_link runs no script and reads no mount
  c  a run's finished ads land under Team Drive/runs/<tool>/<brand>/<run>/,
     a picture already there keeps its id, and nothing else in finals/ goes
  d  no GDRIVE_SA_KEY is a loud SKIP, never a silent pass
  e  run_production's [10] shows drive_link's output and returns its exit

SI-35 (static mirror live). Step [10] ran `P.LAB / "mirror.py"`, a script that
had not existed since the move, with its output captured and dropped, so it
mirrored nothing and never said so. Test (a) is the one that would have caught
it. The Google client is stubbed and the Drive is a fake that has no delete.
"""
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
REPO = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
os.environ["AI_WORKSPACE"] = str(REPO)          # a worktree must not read the main checkout
sys.path.insert(0, str(TOOLS))

# The Google client, stubbed BEFORE any engine call: upload_file asks
# _google("googleapiclient.http") for MediaFileUpload, and this answers it.
LOG = []


class MediaFileUpload(object):
    def __init__(self, path, mimetype=None, resumable=None):
        LOG.append({"op": "media.file", "name": os.path.basename(path),
                    "mime": mimetype, "resumable": resumable})


_gac = types.ModuleType("googleapiclient")
_gac.__path__ = []
_http = types.ModuleType("googleapiclient.http")
_http.MediaFileUpload = MediaFileUpload
_gac.http = _http
sys.modules["googleapiclient"] = _gac
sys.modules["googleapiclient.http"] = _http

import paths as P              # noqa: E402
import drive_link as DL        # noqa: E402
import run_production as RP    # noqa: E402
sys.path.insert(0, str(P.GDRIVE))
from gdrive_creator import engine as E   # noqa: E402

STATIC = TOOLS.parent
INVOKED = re.compile(r'\bP\.([A-Z_]+)\s*/\s*"([^"]+\.(?:py|sh))"')
OPS = {"drives.list", "files.list", "files.create", "files.update"}


# ── the fake Drive (after new-workflow-design/builds/drive-pipe/test_gdrive_creator.py) ──

def parse(q):
    nm = re.search(r"name = '((?:[^'\\]|\\.)*)'", q)
    parent = re.search(r"'([^']+)' in parents", q)
    mime = re.search(r"mimeType = '([^']+)'", q)
    name = None
    if nm:
        name = nm.group(1).replace("\\'", "'").replace("\\\\", "\\")
    return (name, parent.group(1) if parent else None,
            mime.group(1) if mime else None)


class Exec(object):
    def __init__(self, call, result):
        self.call, self.result = call, result

    def execute(self):
        LOG.append(self.call)
        return self.result


class Files(object):
    """list, create, update — and no delete: a mirror that tried one fails."""

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
        return Exec({"op": "files.list", "q": kw["q"]},
                    {"files": hits[:kw.get("pageSize", 100)]})

    def create(self, body=None, fields=None, media_body=None, **kw):
        fid = "id-%d" % (len(self.d.store) + 1)
        self.d.store[fid] = {"parent": (body.get("parents") or [""])[0],
                             "name": body["name"],
                             "mime": body.get("mimeType", "")}
        return Exec({"op": "files.create", "name": body["name"],
                     "mime": body.get("mimeType"),
                     "parents": body.get("parents")},
                    {"id": fid})

    def update(self, fileId=None, fields=None, media_body=None, **kw):
        return Exec({"op": "files.update", "fileId": fileId,
                     "media": media_body is not None}, {"id": fileId})


class Drives(object):
    def list(self, **kw):
        return Exec({"op": "drives.list"},
                    {"drives": [{"id": "drive-sa", "name": "Team Drive"}]})


class Drive(object):
    def __init__(self):
        self.store = {}

    def files(self):
        return Files(self)

    def drives(self):
        return Drives()

    def seed(self, fid, name, parent, mime=E.FOLDER_MIME):
        self.store[fid] = {"parent": parent, "name": name, "mime": mime}
        return fid


class DriveLink(unittest.TestCase):

    def setUp(self):
        del LOG[:]

    def test_every_invoked_script_exists(self):
        files = sorted(STATIC.glob("*.py")) + sorted(TOOLS.glob("*.py"))
        hits, missing = 0, []
        for f in files:
            for n, line in enumerate(f.read_text().splitlines(), 1):
                for const, rel in INVOKED.findall(line):
                    hits += 1
                    if not (Path(getattr(P, const)) / rel).is_file():
                        missing.append(f"{f.relative_to(STATIC)}:{n} invokes "
                                       f"P.{const} / \"{rel}\" — not there")
        self.assertGreater(hits, 0, "the scan found no invoked script at all")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_drive_link_runs_no_script_and_reads_no_mount(self):
        src = (TOOLS / "drive_link.py").read_text()
        said = [w for w in ("subprocess", "mirror.py", "P.LAB", "P.DRIVE", "xattr", "CloudStorage")
                if w in src]
        self.assertEqual(said, [], f"drive_link.py still says {said}")

    def test_mirror_lands_under_runs_and_keeps_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            finals = Path(tmp) / "r1" / "finals"
            (finals / ".compose-tmp-ad-01").mkdir(parents=True)
            (finals / "ad-01.png").write_bytes(b"png")
            (finals / "ad-02.jpg").write_bytes(b"jpg")
            (finals / ".compose-tmp-ad-01" / "el00.png").write_bytes(b"el")
            (finals / "notes.txt").write_text("notes")
            fake = Drive()
            runs = fake.seed("f-runs", "runs", "drive-sa")
            tool = fake.seed("f-tool", P.TOOL, runs)
            brand = fake.seed("f-brand", "zz-brand", tool)
            r1 = fake.seed("f-r1", "r1", brand)
            fake.seed("x-ad1", "ad-01.png", r1, mime="image/png")
            with mock.patch.object(P, "RUNS", Path(tmp)):
                fid, ids = DL.mirror("r1", "zz-brand", E, fake)
        self.assertEqual(fid, "f-r1")
        self.assertEqual(set(ids), {"ad-01.png", "ad-02.jpg"})
        self.assertEqual(ids["ad-01.png"], "x-ad1")
        creates = [c for c in LOG if c.get("op") == "files.create"]
        self.assertFalse([c for c in creates if c["mime"] == E.FOLDER_MIME],
                         "a folder was made where one was already there")
        self.assertFalse([c for c in creates if c["name"] in ("el00.png", "notes.txt")])
        self.assertEqual({c["op"] for c in LOG if c["op"] != "media.file"} - OPS, set())

    def test_no_key_is_a_loud_skip(self):
        env = {k: v for k, v in os.environ.items() if k != "GDRIVE_SA_KEY"}
        with mock.patch.dict(os.environ, env, clear=True):
            engine, svc, note = DL._service()
        self.assertIsNone(engine)
        self.assertIsNone(svc)
        self.assertTrue(note.startswith("SKIP the Drive mirror — no GDRIVE_SA_KEY"), note)

    def test_deliver_shows_and_returns_the_exit(self):
        seen = []

        def run(argv, **kw):
            seen.append((argv, kw))
            return subprocess.CompletedProcess(argv, 4)

        with mock.patch.object(RP.subprocess, "run", run), \
                mock.patch("sys.stdout", new_callable=lambda: open(os.devnull, "w")):
            rc = RP.deliver(["r1"], "zz-brand")
        self.assertEqual(rc, 4)
        argv, kw = seen[0]
        self.assertEqual(argv, [sys.executable, str(P.TOOLS / "drive_link.py"),
                                "r1", "--brand", "zz-brand"])
        for k in ("capture_output", "stdout", "stderr"):
            self.assertNotIn(k, kw)


if __name__ == "__main__":
    print(f"python {sys.version_info[:2]}")
    unittest.main(verbosity=2)
