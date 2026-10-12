#!/usr/bin/env python3
"""SI-38 (email Drive reach): one helper, and the email line reaches its
pictures through it — proven with no key, no network and no real mount.

    python3 test_drive_reach.py

The mount is patched in every test (a temp folder or None) and the Drive API
is a fake engine, so nothing here reads the real Drive or a credential.

  a  the route: a key means the API even with a mount; no key and a mount
     means the mount; neither is a named refusal; an empty key is no key
  b  a read on the mount is the file itself, never a copy
  c  a read through the API goes by id, and never makes a folder
  d  a missing folder on the API is None, with nothing read
  e  a put through the API finds/makes the folder chain and uploads per file
  g  the uploader never names a mount it does not have
  h  the uploader fetches the hero by id when a key is set
  i  the dashboard lists no format bank without a mount, and does not fail
  j  one helper: the three copies and their literals are gone
"""
import contextlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="drive-reach-test-"))
WS = TMP / "ws"
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py

HERE = Path(__file__).resolve().parent
import drive_reach as DR                          # noqa: E402
import simple_email as S                          # noqa: E402
sys.path.append(str(HERE))   # simple_email takes this folder off the path; appended, stdlib email still wins
import klaviyo_upload as K                        # noqa: E402
import build_dashboard as BD                      # noqa: E402

BRAND, LABEL = "zz-brand", "lbl"
PARTS = ["runs", "email-production", BRAND, LABEL]


def load_folders():
    spec = importlib.util.spec_from_file_location(
        "build_email_folders_under_test", HERE / "pull" / "build_email_folders.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeSvc:
    def drives(self):
        return self

    def list(self, **kw):
        return self

    def execute(self):
        return {"drives": [{"id": "drv-other", "name": "Somewhere else"},
                           {"id": "drv-sa", "name": "Shared Assets"}]}


class FakeEngine:
    FOLDER_MIME = "application/vnd.google-apps.folder"

    def __init__(self):
        self.store = {}            # (parent id, name) -> id
        self.folders, self.uploads, self.media = [], [], []
        self.services = 0

    def service(self):
        self.services += 1
        return FakeSvc()

    def find_file(self, svc, name, parent, mime=None):
        fid = self.store.get((parent, name))
        return {"id": fid} if fid else None

    def folder(self, name, parent_id, svc=None):
        self.folders.append((name, parent_id))
        return f"{parent_id}/{name}"

    def upload_file(self, path, name, parent_id, mime="application/octet-stream", svc=None):
        self.uploads.append((str(path), name, parent_id))
        return f"{parent_id}/{name}", True

    def get_media(self, file_id, dest_path, svc=None):
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"png-" + file_id.encode())
        self.media.append(file_id)
        return str(dest)


def chain(store, upto=None):
    """runs -> email-production -> zz-brand -> lbl under drv-sa, stopping
    before `upto` when given; returns the last folder id."""
    parent = "drv-sa"
    for i, part in enumerate(PARTS):
        if part == upto:
            return None
        store[(parent, part)] = f"id-{i}"
        parent = f"id-{i}"
    return parent


class DriveReach(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(DR.KEY_ENV, None)
        self.tmp = Path(tempfile.mkdtemp(dir=TMP))
        self.sa = self.tmp / "sa"
        self.sa.mkdir()
        m = mock.patch.object(DR, "mount", return_value=None)     # never the real mount
        self.mount = m.start()
        self.addCleanup(m.stop)
        self.fake = FakeEngine()
        e = mock.patch.object(DR, "_engine", return_value=self.fake)
        e.start()
        self.addCleanup(e.stop)
        S._NO_DRIVE_TOLD.clear()
        BD._BANK_TOLD.clear()

    def local_media(self):
        return S.WORKSPACE / "runs" / "email-production" / BRAND / LABEL / "media"

    # a — the route
    def test_key_means_api_even_with_a_mount(self):
        self.mount.return_value = self.sa
        os.environ[DR.KEY_ENV] = "x"
        self.assertEqual(DR.route(), "api")
        self.assertEqual(S.drive_media(BRAND, LABEL), ("api", self.local_media()))
        self.assertEqual(list(self.sa.iterdir()), [])

    def test_no_key_with_a_mount_is_the_mount(self):
        self.mount.return_value = self.sa
        self.assertEqual(DR.route(), "mount")
        self.assertEqual(S.drive_media(BRAND, LABEL)[1],
                         self.sa / "runs" / "email-production" / BRAND / LABEL)
        self.assertEqual(self.fake.services, 0)

    def test_neither_is_a_named_refusal(self):
        with self.assertRaises(DR.NoDrive) as c:
            DR.route()
        self.assertIn("GDRIVE_SA_KEY", str(c.exception))
        self.assertIn("mount", str(c.exception))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            got = S.drive_media(BRAND, LABEL)
        self.assertEqual(got, ("none", self.local_media()))
        self.assertIn("GDRIVE_SA_KEY", err.getvalue())
        self.assertIn("mount", err.getvalue())
        self.assertFalse(self.local_media().exists())       # said, not built

    def test_an_empty_key_is_no_key(self):
        os.environ[DR.KEY_ENV] = ""
        with self.assertRaises(DR.NoDrive):
            DR.route()
        self.mount.return_value = self.sa
        self.assertEqual(DR.route(), "mount")

    # b — the mount read
    def test_get_on_the_mount_is_the_file_itself(self):
        self.mount.return_value = self.sa
        f = self.sa.joinpath(*PARTS, "hero.png")
        f.parent.mkdir(parents=True)
        f.write_bytes(b"on-the-mount")
        dest = self.tmp / "dest"
        self.assertEqual(DR.get(PARTS, "hero.png", dest), f)
        self.assertFalse(dest.exists() and any(dest.iterdir()))
        self.assertIsNone(DR.get(PARTS, "offer.png", dest))

    # c, d — the API read
    def test_get_through_the_api_reads_by_id(self):
        os.environ[DR.KEY_ENV] = "x"
        self.mount.return_value = self.sa
        decoy = self.sa.joinpath(*PARTS, "hero.png")
        decoy.parent.mkdir(parents=True)
        decoy.write_bytes(b"the mount, which must not be read")
        self.fake.store[(chain(self.fake.store), "hero.png")] = "hero-id"
        dest = self.tmp / "dest"
        got = DR.get(PARTS, "hero.png", dest)
        self.assertEqual(got, dest / "hero.png")
        self.assertEqual(got.read_bytes(), b"png-hero-id")
        self.assertEqual(self.fake.folders, [])

    def test_get_through_the_api_missing_folder_is_none(self):
        os.environ[DR.KEY_ENV] = "x"
        chain(self.fake.store, upto=LABEL)
        self.assertIsNone(DR.get(PARTS, "hero.png", self.tmp / "dest"))
        self.assertEqual(self.fake.media, [])
        self.assertEqual(self.fake.folders, [])
        self.assertFalse((self.tmp / "dest").exists())

    # e — the API write
    def test_put_through_the_api(self):
        os.environ[DR.KEY_ENV] = "x"
        files = []
        for n in ("hero.png", "hero.jpg"):
            p = self.tmp / n
            p.write_bytes(b"x")
            files.append(p)
        how, placed, note = DR.put(files, PARTS)
        self.assertEqual((how, note), ("api", None))
        self.assertEqual(self.fake.folders, [
            ("runs", "drv-sa"), ("email-production", "drv-sa/runs"),
            (BRAND, "drv-sa/runs/email-production"),
            (LABEL, f"drv-sa/runs/email-production/{BRAND}")])
        dest = f"drv-sa/runs/email-production/{BRAND}/{LABEL}"
        self.assertEqual(self.fake.uploads, [(str(f), f.name, dest) for f in files])
        self.assertEqual(placed, [f"Shared Assets/runs/email-production/{BRAND}/{LABEL}/{f.name}"
                                  for f in files])

    def test_put_with_no_drive_is_a_named_skip_and_a_missing_package_is_not_caught(self):
        how, placed, note = DR.put([self.tmp / "hero.png"], PARTS)
        self.assertEqual((how, placed), ("none", []))
        self.assertTrue(note.startswith("SKIP the rest of the Drive mirror — NoDrive:"), note)
        os.environ[DR.KEY_ENV] = "x"
        with mock.patch.object(self.fake, "service", side_effect=SystemExit("no package")):
            with self.assertRaises(SystemExit):
                DR.put([self.tmp / "hero.png"], PARTS)

    # g, h — the uploader
    def test_uploader_media_never_names_a_mount_it_does_not_have(self):
        rd = self.tmp / "run" / LABEL
        rd.mkdir(parents=True)
        with contextlib.redirect_stderr(io.StringIO()):
            media = K.from_run(rd, BRAND)["media"]
        for m in media:
            self.assertNotIn("CloudStorage", str(m))

    def test_uploader_fetches_the_hero_by_id(self):
        os.environ[DR.KEY_ENV] = "x"
        self.fake.store[(chain(self.fake.store), "hero.png")] = "hero-id"
        rd = self.tmp / "run" / LABEL
        rd.mkdir(parents=True)
        job = {"mode": "run", "brand": BRAND, "label": LABEL, "root": rd, "media": [rd / "media"]}
        self.assertEqual(K.hero_picture(job), rd / "media" / "hero.png")
        self.assertEqual((rd / "media" / "hero.png").read_bytes(), b"png-hero-id")

    def test_uploader_dry_run_reads_nothing_by_id(self):
        os.environ[DR.KEY_ENV] = "x"
        self.fake.store[(chain(self.fake.store), "hero.png")] = "hero-id"
        rd = self.tmp / "run" / LABEL
        rd.mkdir(parents=True)
        job = {"mode": "run", "brand": BRAND, "label": LABEL, "root": rd, "media": [rd / "media"]}
        self.assertIsNone(K.hero_picture(job, online=False))
        self.assertEqual((self.fake.services, self.fake.media), (0, []))

    # i — the dashboard
    def test_dashboard_without_a_mount_lists_no_bank(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            got = BD.board_order(BRAND)
        self.assertIsInstance(got, list)
        self.assertIn("Drive mount only", err.getvalue())

    # j — one helper
    def test_one_helper(self):
        for rel in ("simple_email.py", "klaviyo_upload.py", "build_dashboard.py",
                    "pull/build_email_folders.py"):
            src = (HERE / rel).read_text()
            for gone in ("def _drive_mount", "DRIVE_RUNS", "GoogleDrive-", "Library/CloudStorage"):
                self.assertNotIn(gone, src, f"{rel}: {gone}")
        self.assertNotIn("GoogleDrive-damon@", (HERE / "IMAGERY.md").read_text())
        mod = load_folders()                     # DR.mount is patched to None here
        self.assertIsNone(mod.DRIVE)
        sys.argv = ["build_email_folders.py", "--brand", BRAND]
        with self.assertRaises(SystemExit) as c:
            mod.main()
        self.assertIn("--out", str(c.exception.code))


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
