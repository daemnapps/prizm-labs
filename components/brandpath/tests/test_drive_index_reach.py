"""drive_index reach: the mount on any Drive account, else the picture by its Drive id.

No key, no network: a fake HOME, a fake brands dir and a fake fetch.
    /usr/bin/python3 components/brandpath/tests/test_drive_index_reach.py
"""
import contextlib
import errno
import inspect
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
import drive_index as DI  # noqa: E402

assert pathlib.Path(DI.__file__).resolve().is_relative_to(REPO), DI.__file__

BRAND = "zz-test-brand"
PRODUCT = "zz-product"
PACK_ID = "id-packshot-1"
LIFE_ID = "id-lifestyle-1"
PACK_PATH = "brands/%s/products/%s/packshot/front.png" % (BRAND, PRODUCT)
LIFE_PATH = "brands/%s/products/%s/lifestyle/scene.jpg" % (BRAND, PRODUCT)
OLD_PATH = "products/%s/images/packshot-lockup.png" % PRODUCT


class Reach(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = pathlib.Path(self.tmp.name)
        self.home = t / "home"
        self.home.mkdir()
        self.brands = t / "brands"
        (self.brands / BRAND / "products").mkdir(parents=True)
        (self.brands / BRAND / "products" / "DRIVE-INDEX.json").write_text(json.dumps({"files": [
            {"drive_id": PACK_ID, "drive_path": PACK_PATH, "name": "front.png", "folder": PRODUCT,
             "kind": "packshot", "bytes": 3, "old_path": OLD_PATH},
            {"drive_id": LIFE_ID, "drive_path": LIFE_PATH, "name": "scene.jpg", "folder": PRODUCT,
             "kind": "lifestyle", "bytes": None, "old_path": None},
        ]}))
        self.cache = t / "cache"
        p = mock.patch.object(pathlib.Path, "home", return_value=self.home)
        p.start()
        self.addCleanup(p.stop)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("GDRIVE_SA_KEY", None)
        # LD-26 (mount switch): a worker-spawned run of this suite inherits
        # DRIVE_MOUNT=off; these tests are a person's session, so drop it.
        os.environ.pop("DRIVE_MOUNT", None)
        DI._SAID.clear()
        DI._CACHE.clear()
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def cloud(self):
        return self.home / "Library" / "CloudStorage"

    def fake(self, file_id, dest):
        self.calls.append(file_id)
        pathlib.Path(dest).write_bytes(b"abc")
        return str(dest)

    def test_mount_matches_any_domain(self):
        a = self.cloud() / "GoogleDrive-a@example.org"
        a.mkdir(parents=True)
        b = self.cloud() / "GoogleDrive-b@example.net"
        (b / "Shared drives" / "Shared Assets").mkdir(parents=True)
        self.assertEqual(DI.accounts(), [a, b])
        self.assertEqual(DI.mount(), b / "Shared drives" / "Shared Assets")

    def test_no_cloudstorage_is_none(self):
        self.assertEqual(DI.accounts(), [])
        self.assertIsNone(DI.mount())

    def test_mount_file_wins(self):
        sa = self.cloud() / "GoogleDrive-b@example.net" / "Shared drives" / "Shared Assets"
        f = sa / PACK_PATH
        f.parent.mkdir(parents=True)
        f.write_bytes(b"abc")
        got = DI.local(BRAND, OLD_PATH, self.brands, cache_dir=self.cache, fetch=self.fake)
        self.assertEqual(got, f)
        self.assertEqual(self.calls, [])

    def test_no_mount_fetches_by_id_into_cache(self):
        got = DI.local(BRAND, OLD_PATH, self.brands, cache_dir=self.cache, fetch=self.fake)
        self.assertIsInstance(got, pathlib.Path)
        self.assertEqual(got, self.cache / BRAND / PACK_ID / "front.png")
        self.assertTrue(got.is_file())
        self.assertEqual(self.calls, [PACK_ID])
        again = DI.local(BRAND, PACK_ID, self.brands, cache_dir=self.cache, fetch=self.fake)
        self.assertEqual(again, got)
        self.assertEqual(self.calls, [PACK_ID])

    def placeholder(self):
        """LD-25 (picture mount deadlock): a mount file whose is_file raises EDEADLK."""
        sa = self.cloud() / "GoogleDrive-b@example.net" / "Shared drives" / "Shared Assets"
        f = sa / PACK_PATH
        f.parent.mkdir(parents=True)
        f.write_bytes(b"abc")
        real = pathlib.Path.is_file

        def is_file(path, *a, **k):
            if path == f:
                raise OSError(errno.EDEADLK, "Resource deadlock avoided", str(path))
            return real(path, *a, **k)

        p = mock.patch.object(pathlib.Path, "is_file", is_file)
        p.start()
        self.addCleanup(p.stop)
        with self.assertRaises(OSError):
            f.is_file()
        return f

    def test_mount_deadlock_fetches_by_id(self):
        f = self.placeholder()
        want = self.cache / BRAND / PACK_ID / "front.png"
        got = DI.local(BRAND, OLD_PATH, self.brands, cache_dir=self.cache, fetch=self.fake)
        self.assertEqual(got, want)
        self.assertNotEqual(got, f)
        self.assertEqual(self.calls, [PACK_ID])
        pics = DI.product_pictures(BRAND, PRODUCT, self.brands, cache_dir=self.cache, fetch=self.fake)
        self.assertEqual(pics, [want])
        self.assertEqual(self.calls, [PACK_ID])

    def test_mount_deadlock_no_key_no_fetch_is_none(self):
        self.placeholder()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(DI.local(BRAND, OLD_PATH, self.brands, cache_dir=self.cache))
            self.assertEqual(DI.product_pictures(BRAND, PRODUCT, self.brands, cache_dir=self.cache), [])
        self.assertIn("GDRIVE_SA_KEY", err.getvalue())
        self.assertEqual(self.calls, [])

    def test_default_route_is_gdrive_creator_get_media(self):
        gc = REPO / "components" / "gdrive-creator"
        if str(gc) not in sys.path:
            sys.path.insert(0, str(gc))
        from gdrive_creator import engine
        self.assertTrue(pathlib.Path(engine.__file__).resolve().is_relative_to(REPO))
        os.environ["GDRIVE_SA_KEY"] = "not-a-real-key"
        seen = []

        def fake_get_media(file_id, dest_path, svc=None):
            seen.append(file_id)
            pathlib.Path(dest_path).write_bytes(b"abc")
            return str(dest_path)

        with mock.patch.object(engine, "get_media", fake_get_media):
            got = DI.product_pictures(BRAND, PRODUCT, self.brands, cache_dir=self.cache)
        self.assertEqual(got, [self.cache / BRAND / PACK_ID / "front.png"])
        self.assertEqual(seen, [PACK_ID])

    def test_no_mount_no_key_is_loud_none(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(DI.local(BRAND, OLD_PATH, self.brands))
            self.assertEqual(DI.product_pictures(BRAND, PRODUCT, self.brands), [])
        self.assertEqual(err.getvalue().count("GDRIVE_SA_KEY"), 1)
        self.assertIn("no Drive mount", err.getvalue())

    def test_failed_fetch_leaves_no_part_file(self):
        def broken(file_id, dest):
            pathlib.Path(dest).write_bytes(b"a")
            raise OSError("boom")

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            got = DI.local(BRAND, OLD_PATH, self.brands, cache_dir=self.cache, fetch=broken)
        self.assertIsNone(got)
        self.assertEqual(list(self.cache.rglob("*.part")), [])
        self.assertIn(PACK_ID, err.getvalue())
        self.assertIn("OSError", err.getvalue())

    def test_callers_signatures_still_bind(self):
        inspect.signature(DI.local).bind("b", "r", "d")
        inspect.signature(DI.product_pictures).bind("b", "p", "d", ("packshot",))
        for fn in (DI.local, DI.product_pictures):
            ps = inspect.signature(fn).parameters
            for name in ("cache_dir", "fetch"):
                self.assertIs(ps[name].kind, inspect.Parameter.KEYWORD_ONLY)
                self.assertIsNone(ps[name].default)


class FakeLibc(object):
    """Stands in for libc: records each setiopolicy_np call, returns rc or raises."""

    def __init__(self, rc=0, boom=None):
        self.calls = []
        self.rc = rc
        self.boom = boom

    def setiopolicy_np(self, *args):
        self.calls.append(args)
        if self.boom is not None:
            raise self.boom
        return self.rc


class Dataless(unittest.TestCase):
    """LD-10 (Drive reads in sessions): accounts() turns dataless reads ON once per process."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = pathlib.Path(self.tmp.name)
        self.a = self.home / "Library" / "CloudStorage" / "GoogleDrive-a@example.org"
        self.a.mkdir(parents=True)
        p = mock.patch.object(pathlib.Path, "home", return_value=self.home)
        p.start()
        self.addCleanup(p.stop)
        flag = mock.patch.object(DI, "_DATALESS_TRIED", False)
        flag.start()
        self.addCleanup(flag.stop)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("GDRIVE_SA_KEY", None)
        os.environ.pop("DRIVE_MOUNT", None)   # LD-26 (mount switch): a person's session

    def stub(self, libc):
        p = mock.patch.object(DI, "_libc", lambda: libc)
        p.start()
        self.addCleanup(p.stop)

    def test_setter_called_once_across_calls(self):
        libc = FakeLibc()
        self.stub(libc)
        with mock.patch.object(DI.sys, "platform", "darwin"):
            for _ in range(3):
                self.assertEqual(DI.accounts(), [self.a])
            DI.mount()
        self.assertEqual(len(libc.calls), 1)

    def test_call_passes_materialize_on(self):
        libc = FakeLibc()
        self.stub(libc)
        with mock.patch.object(DI.sys, "platform", "darwin"):
            DI.accounts()
            self.assertTrue(DI.allow_dataless())
        self.assertEqual(libc.calls[0], (3, 0, 2))

    def test_raising_libc_leaves_accounts_working(self):
        libc = FakeLibc(boom=OSError("no libc"))
        self.stub(libc)
        with mock.patch.object(DI.sys, "platform", "darwin"):
            self.assertEqual(DI.accounts(), [self.a])
            self.assertFalse(DI.allow_dataless())
        self.assertEqual(len(libc.calls), 2)

    def test_failing_rc_leaves_accounts_working(self):
        libc = FakeLibc(rc=-1)
        self.stub(libc)
        with mock.patch.object(DI.sys, "platform", "darwin"):
            self.assertEqual(DI.accounts(), [self.a])
            self.assertFalse(DI.allow_dataless())

    def test_unloadable_libc_never_raises(self):
        def broken():
            raise OSError("dlopen failed")

        with mock.patch.object(DI, "_libc", broken), \
                mock.patch.object(DI.sys, "platform", "darwin"):
            self.assertEqual(DI.accounts(), [self.a])
            self.assertFalse(DI.allow_dataless())

    def test_off_darwin_setter_not_called(self):
        libc = FakeLibc()
        self.stub(libc)
        with mock.patch.object(DI.sys, "platform", "linux"):
            self.assertEqual(DI.accounts(), [self.a])
            self.assertFalse(DI.allow_dataless())
        self.assertEqual(libc.calls, [])

    def test_key_set_never_calls_setter(self):
        """LD-18 (headless policy off): a job holding the Drive key leaves the policy OFF."""
        libc = FakeLibc()
        self.stub(libc)
        os.environ["GDRIVE_SA_KEY"] = "not-a-real-key"
        with mock.patch.object(DI.sys, "platform", "darwin"):
            for _ in range(3):
                self.assertEqual(DI.accounts(), [self.a])
            DI.mount()
        self.assertEqual(libc.calls, [])

    def test_key_empty_keeps_single_call(self):
        libc = FakeLibc()
        self.stub(libc)
        os.environ["GDRIVE_SA_KEY"] = ""
        with mock.patch.object(DI.sys, "platform", "darwin"):
            DI.accounts()
            DI.mount()
        self.assertEqual(libc.calls, [(3, 0, 2)])

    def test_key_unset_keeps_single_call(self):
        libc = FakeLibc()
        self.stub(libc)
        with mock.patch.object(DI.sys, "platform", "darwin"):
            DI.accounts()
            DI.mount()
        self.assertEqual(libc.calls, [(3, 0, 2)])


class MountOff(unittest.TestCase):
    """LD-26 (mount switch): a worker-spawned job carries DRIVE_MOUNT=off and
    has no Drive folder — mount() is None and accounts() is [] before ANY
    filesystem touch; unset (a person's session), today's behaviour."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = pathlib.Path(self.tmp.name)
        self.home = t / "home"
        self.acct = self.home / "Library" / "CloudStorage" / "GoogleDrive-a@example.org"
        self.sa = self.acct / "Shared drives" / "Shared Assets"
        f = self.sa / PACK_PATH
        f.parent.mkdir(parents=True)
        f.write_bytes(b"abc")
        self.mount_file = f
        self.brands = t / "brands"
        (self.brands / BRAND / "products").mkdir(parents=True)
        (self.brands / BRAND / "products" / "DRIVE-INDEX.json").write_text(json.dumps({"files": [
            {"drive_id": PACK_ID, "drive_path": PACK_PATH, "name": "front.png", "folder": PRODUCT,
             "kind": "packshot", "bytes": 3, "old_path": OLD_PATH},
        ]}))
        self.cache = t / "cache"
        p = mock.patch.object(pathlib.Path, "home", return_value=self.home)
        p.start()
        self.addCleanup(p.stop)
        flag = mock.patch.object(DI, "_DATALESS_TRIED", False)
        flag.start()
        self.addCleanup(flag.stop)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("GDRIVE_SA_KEY", None)
        os.environ.pop("DRIVE_MOUNT", None)
        DI._SAID.clear()
        DI._CACHE.clear()
        self.calls = []

    def fake(self, file_id, dest):
        self.calls.append(file_id)
        pathlib.Path(dest).write_bytes(b"abc")
        return str(dest)

    def no_touch(self):
        """Every stat, listing and dataless call fails loudly while open."""
        def boom(name):
            def f(*a, **k):
                raise AssertionError("LD-26 (mount switch): %s touched the filesystem %r"
                                     % (name, a[:1]))
            return f

        stack = contextlib.ExitStack()
        for n in ("stat", "lstat", "is_dir", "is_file", "exists", "glob", "iterdir"):
            stack.enter_context(mock.patch.object(pathlib.Path, n, boom("Path." + n)))
        for n in ("stat", "lstat", "scandir", "listdir"):
            stack.enter_context(mock.patch.object(os, n, boom("os." + n)))
        stack.enter_context(mock.patch.object(DI, "allow_dataless", boom("allow_dataless")))
        stack.enter_context(mock.patch.object(DI, "_libc", boom("_libc")))
        return stack

    def test_guard_fires_without_the_switch_and_releases(self):
        with self.no_touch():
            with self.assertRaises(AssertionError):
                DI.accounts()
        self.assertEqual(DI.accounts(), [self.acct])

    def test_off_mount_none_accounts_empty_nothing_touched(self):
        os.environ["DRIVE_MOUNT"] = "off"
        with self.no_touch():
            self.assertIsNone(DI.mount())
            self.assertEqual(DI.accounts(), [])
        self.assertFalse(DI._DATALESS_TRIED)
        self.assertTrue(self.sa.is_dir())

    def test_off_with_key_nothing_touched(self):
        os.environ["DRIVE_MOUNT"] = "off"
        os.environ["GDRIVE_SA_KEY"] = "not-a-real-key"
        with self.no_touch():
            self.assertIsNone(DI.mount())
            self.assertEqual(DI.accounts(), [])

    def test_unset_is_todays_behaviour(self):
        with mock.patch.object(DI, "allow_dataless", lambda: False):
            self.assertEqual(DI.accounts(), [self.acct])
            self.assertEqual(DI.mount(), self.sa)

    def test_only_the_exact_word_off_switches(self):
        with mock.patch.object(DI, "allow_dataless", lambda: False):
            for v in ("", "on", "OFF", "0", "false"):
                os.environ["DRIVE_MOUNT"] = v
                self.assertEqual(DI.accounts(), [self.acct], v)
                self.assertEqual(DI.mount(), self.sa, v)

    def test_off_picture_goes_by_drive_id_not_the_mount(self):
        os.environ["DRIVE_MOUNT"] = "off"
        want = self.cache / BRAND / PACK_ID / "front.png"
        got = DI.local(BRAND, OLD_PATH, self.brands, cache_dir=self.cache, fetch=self.fake)
        self.assertEqual(got, want)
        self.assertNotEqual(got, self.mount_file)
        self.assertEqual(self.calls, [PACK_ID])
        pics = DI.product_pictures(BRAND, PRODUCT, self.brands, cache_dir=self.cache, fetch=self.fake)
        self.assertEqual(pics, [want])

    def test_off_no_key_is_loud_none(self):
        os.environ["DRIVE_MOUNT"] = "off"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(DI.local(BRAND, OLD_PATH, self.brands, cache_dir=self.cache))
        self.assertIn("GDRIVE_SA_KEY", err.getvalue())
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
