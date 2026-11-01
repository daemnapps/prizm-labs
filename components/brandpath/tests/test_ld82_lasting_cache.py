"""LD-82 (brandpath lasting cache): a picture fetched by Drive id lands in the one lasting cache, never a temp folder.

No key, no network: HOME and DRIVE_CACHE in a temp dir, a fake brands dir and a fake fetch.
    /usr/bin/python3 components/brandpath/tests/test_ld82_lasting_cache.py
"""
import importlib.util
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
import drive_index as DI  # noqa: E402

assert pathlib.Path(DI.__file__).resolve().is_relative_to(REPO), DI.__file__

BRAND = "zz-test-brand"
PRODUCT = "zz-product"
PACK_ID = "id-packshot-1"
PACK_PATH = "brands/%s/products/%s/packshot/front.png" % (BRAND, PRODUCT)
OLD_PATH = "products/%s/images/packshot-lockup.png" % PRODUCT


class LastingCache(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = pathlib.Path(self.tmp.name)
        self.t = t
        self.home = t / "home"
        self.home.mkdir()
        self.dc = t / "dc"
        self.brands = t / "brands"
        (self.brands / BRAND / "products").mkdir(parents=True)
        (self.brands / BRAND / "products" / "DRIVE-INDEX.json").write_text(json.dumps({"files": [
            {"drive_id": PACK_ID, "drive_path": PACK_PATH, "name": "front.png", "folder": PRODUCT,
             "kind": "packshot", "bytes": 3, "old_path": OLD_PATH},
        ]}))
        self.saved_env = dict(os.environ)
        os.environ["HOME"] = str(self.home)
        os.environ["DRIVE_CACHE"] = str(self.dc)
        os.environ.pop("GDRIVE_SA_KEY", None)
        os.environ.pop("DRIVE_MOUNT", None)
        # a SEPARATE temp folder, so "never under the temp folder" is testable though T sits under the system one
        self.saved_tempdir = tempfile.tempdir
        self.x = pathlib.Path(tempfile.mkdtemp())
        tempfile.tempdir = str(self.x)
        DI._SAID.clear()
        DI._CACHE.clear()
        self.calls = []

    def tearDown(self):
        tempfile.tempdir = self.saved_tempdir
        shutil.rmtree(str(self.x), ignore_errors=True)
        os.environ.clear()
        os.environ.update(self.saved_env)

    def fake(self, file_id, dest):
        self.calls.append(file_id)
        pathlib.Path(dest).write_bytes(b"abc")
        return str(dest)

    def test_default_root_is_the_lasting_cache(self):
        self.assertEqual(tempfile.gettempdir(), str(self.x))
        got = DI.local(BRAND, OLD_PATH, self.brands, fetch=self.fake)
        self.assertEqual(got, self.dc / "brandpath" / BRAND / PACK_ID / "front.png")
        self.assertTrue(got.is_file())
        self.assertEqual(self.calls, [PACK_ID])

    def test_never_under_the_temp_folder(self):
        got = DI.local(BRAND, OLD_PATH, self.brands, fetch=self.fake)
        self.assertFalse(got.is_relative_to(self.x), got)
        self.assertFalse(got.is_relative_to(self.x / "brandpath-drive-cache"), got)
        self.assertFalse(got.is_relative_to(tempfile.gettempdir()), got)
        self.assertFalse((self.x / "brandpath-drive-cache").exists())

    def test_second_call_with_size_matching_makes_no_fetch(self):
        first = DI.local(BRAND, OLD_PATH, self.brands, fetch=self.fake)
        again = DI.local(BRAND, PACK_ID, self.brands, fetch=self.fake)
        self.assertEqual(again, first)
        self.assertEqual(self.calls, [PACK_ID])

    def test_drive_cache_unset_falls_back_to_home(self):
        os.environ.pop("DRIVE_CACHE")
        want = self.home / ".upright" / "cache" / "drive" / "brandpath"
        self.assertEqual(DI._cache_root(), want)
        got = DI.local(BRAND, OLD_PATH, self.brands, fetch=self.fake)
        self.assertEqual(got, want / BRAND / PACK_ID / "front.png")

    def test_explicit_cache_dir_still_wins(self):
        explicit = self.t / "explicit"
        got = DI.local(BRAND, OLD_PATH, self.brands, cache_dir=explicit, fetch=self.fake)
        self.assertEqual(got, explicit / BRAND / PACK_ID / "front.png")
        self.assertFalse((self.dc / "brandpath").exists())

    def test_root_is_read_at_call_time_not_import(self):
        a, b = self.t / "a", self.t / "b"
        os.environ["DRIVE_CACHE"] = str(a)
        spec = importlib.util.spec_from_file_location("drive_index_ld82_fresh", DI.__file__)
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        os.environ["DRIVE_CACHE"] = str(b)
        self.assertEqual(fresh._cache_root(), b / "brandpath")
        got = fresh.local(BRAND, OLD_PATH, self.brands, fetch=self.fake)
        self.assertTrue(got.is_relative_to(b), got)
        self.assertFalse(got.is_relative_to(a), got)


if __name__ == "__main__":
    unittest.main()
