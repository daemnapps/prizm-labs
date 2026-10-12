#!/usr/bin/env python3
"""Tests for how image-production reaches the Drive (SI-37, image Drive reach).

    python3 tools/image-production/tests/test_drive_reach.py

Stdlib `unittest`. **No key, no network, no Pillow, and the real mount is
never touched**: every test that routes patches `drive_reach.mount`, and the
API half runs against a fake gdrive-creator engine.
"""
import inspect
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent))                  # APPEND — never insert at 0
from image_production import drive_reach as DR, filing as F, assets as AS, paths as P  # noqa: E402


class FakeSvc:
    def drives(self):
        return self

    def list(self, **kw):
        return self

    def execute(self):
        return {"drives": [{"id": "drv-sa", "name": "Team Drive"}]}


class FakeEngine:
    """Stands in for components/gdrive-creator's engine."""
    FOLDER_MIME = "application/vnd.google-apps.folder"

    def __init__(self):
        self.folders, self.uploads, self.services = [], [], 0

    def folder(self, name, parent, svc=None):
        self.folders.append((name, parent))
        return f"{parent}/{name}"

    def upload_file(self, path, name, parent_id, mime=None, svc=None):
        self.uploads.append((name, parent_id))
        return "id-" + name, True

    def service(self):
        self.services += 1
        return FakeSvc()


class Exploding:
    def __getattr__(self, name):
        raise AssertionError(f"the API was reached: {name}")


class Base(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(DR.KEY_ENV, None)
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(t.name)

    def patch(self, target, name, value):
        p = mock.patch.object(target, name, value)
        p.start()
        self.addCleanup(p.stop)

    def mount_at(self, where):
        self.patch(DR, "mount", lambda: where)

    def engine(self, eng):
        self.patch(DR, "_engine", lambda: eng)
        return eng

    def pictures(self, *names, data=b"new"):
        src = self.tmp / "out"
        src.mkdir(exist_ok=True)
        out = []
        for n in names:
            (src / n).write_bytes(data)
            out.append(src / n)
        return out


class TestRoute(Base):
    def test_key_means_api_even_with_a_mount(self):
        sa = self.tmp / "sa"
        sa.mkdir()
        self.mount_at(sa)
        os.environ[DR.KEY_ENV] = "x"
        self.assertEqual(DR.route(), "api")
        eng = self.engine(FakeEngine())
        F.mirror(self.pictures("a.png"), "zz-brand", "lbl")
        self.assertTrue(eng.folders)
        self.assertTrue(eng.uploads)
        self.assertEqual(list(sa.rglob("*")), [])

    def test_no_key_with_a_mount_is_the_mount(self):
        self.mount_at(self.tmp)
        eng = self.engine(FakeEngine())
        self.assertEqual(DR.route(), "mount")
        F.mirror(self.pictures("a.png"), "zz-brand", "lbl")
        self.assertEqual(eng.services, 0)

    def test_neither_is_a_named_refusal(self):
        self.mount_at(None)
        with self.assertRaises(DR.NoDrive) as c:
            DR.route()
        self.assertIn("GDRIVE_SA_KEY", str(c.exception))
        self.assertIn("mount", str(c.exception))

    def test_an_empty_key_is_no_key(self):
        os.environ[DR.KEY_ENV] = ""
        self.mount_at(self.tmp)
        self.assertEqual(DR.route(), "mount")
        self.mount_at(None)
        with self.assertRaises(DR.NoDrive):
            DR.route()


class TestMirror(Base):
    def test_mount_mirror_replaces_in_place_and_deletes_nothing(self):
        sa = self.tmp / "sa"
        dest = sa / "runs" / "zz-tool" / "zz-brand" / "lbl"
        dest.mkdir(parents=True)
        (dest / "keep.png").write_bytes(b"keep")
        (dest / "a.png").write_bytes(b"old")
        self.mount_at(sa)
        files = self.pictures("a.png", "b.png")
        got = F.mirror(files, "zz-brand", "lbl", tool="zz-tool")
        self.assertEqual(got, ([str(dest / "a.png"), str(dest / "b.png")], None))
        self.assertEqual((dest / "keep.png").read_bytes(), b"keep")
        self.assertEqual((dest / "a.png").read_bytes(), b"new")

    def test_api_mirror_goes_by_id(self):
        self.mount_at(None)
        os.environ[DR.KEY_ENV] = "x"
        eng = self.engine(FakeEngine())
        copied, note = F.mirror(self.pictures("a.png", "b.png"), "zz-brand", "lbl",
                                tool="zz-tool")
        self.assertEqual(eng.folders, [("runs", "drv-sa"), ("zz-tool", "drv-sa/runs"),
                                       ("zz-brand", "drv-sa/runs/zz-tool"),
                                       ("lbl", "drv-sa/runs/zz-tool/zz-brand")])
        leaf = "drv-sa/runs/zz-tool/zz-brand/lbl"
        self.assertEqual(eng.uploads, [("a.png", leaf), ("b.png", leaf)])
        self.assertEqual(copied, ["Team Drive/runs/zz-tool/zz-brand/lbl/a.png",
                                  "Team Drive/runs/zz-tool/zz-brand/lbl/b.png"])
        self.assertTrue(note.startswith("mirrored through the Drive API"), note)

    def test_no_route_skips_loudly(self):
        self.mount_at(None)
        copied, note = F.mirror(self.pictures("a.png"), "zz-brand", "lbl")
        self.assertEqual(copied, [])
        self.assertTrue(note.startswith("SKIP the Drive mirror — no Drive here"), note)

    def test_plan_never_calls_the_api(self):
        self.mount_at(None)
        os.environ[DR.KEY_ENV] = "x"
        self.engine(Exploding())
        self.assertEqual(F.drive_plan("zz-brand", "lbl"),
                         ("Team Drive/runs/image-production/zz-brand/lbl/ "
                          "(through the Drive API, by id)", None))

    def test_mirror_signature_unchanged(self):
        sig = inspect.signature(F.mirror)
        self.assertEqual(list(sig.parameters), ["files", "brand", "label", "tool"])
        self.assertIsNone(sig.parameters["tool"].default)


class TestShelvesAndMount(Base):
    def test_shelves_off_the_mount_only(self):
        sa = self.tmp / "sa"
        self.mount_at(sa)
        os.environ[DR.KEY_ENV] = "x"
        self.assertIsNone(AS._drive_brand("zz-brand"))
        del os.environ[DR.KEY_ENV]
        self.assertEqual(AS._drive_brand("zz-brand"), sa / "brands" / "zz-brand")
        self.mount_at(None)
        self.assertIsNone(AS._drive_brand("zz-brand"))

    def test_drive_runs_names_the_missing_mount(self):
        self.patch(P, "_drive_index", lambda start=None: types.SimpleNamespace(mount=lambda: None))
        with self.assertRaises(P.MountError) as c:
            P.drive_runs()
        self.assertIn("no Team Drive Drive mount", str(c.exception))

        def deadlock():
            raise OSError(35, "Resource deadlock avoided")
        self.patch(P, "_drive_index", lambda start=None: types.SimpleNamespace(mount=deadlock))
        with self.assertRaises(P.MountError):
            P.drive_runs()
        self.assertIsNone(DR.mount())

    def test_no_account_typed(self):
        pkg = HERE.parent / "image_production"
        for name in ("paths.py", "filing.py", "assets.py", "drive_reach.py"):
            text = (pkg / name).read_text()
            for word in ("GoogleDrive-", "CloudStorage"):
                self.assertNotIn(word, text, f"{name} names {word}")


if __name__ == "__main__":
    unittest.main()
