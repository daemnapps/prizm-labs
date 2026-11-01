"""SI-44 (video mount helper): every Drive site in this machine reaches the
mount through components/brandpath's drive_index — `mount()` / `accounts()` —
never an account path or a glob of its own, so a second person's Mac on any
Drive account finds the drive.

    /usr/bin/python3 tools/video-production/machine/test_drive_mount_helper.py

No key, no network. Every module is imported with the REAL home first
(pipeline.py reads it at import); only then is `Path.home` patched to a fake.
"""
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
BRANDPATH = HERE.parents[1] / "brandpath"

# ORDER MATTERS: this repo's drive_index first, so every module below gets it.
sys.path.insert(0, str(BRANDPATH))
import drive_index as DI                                # noqa: E402
assert hasattr(DI, "accounts"), "drive_index.accounts() missing — SI-41 (Drive picture reach) not in the tree"

sys.path.insert(0, str(HERE))
import chain                                            # noqa: E402
import board                                            # noqa: E402
import elements                                         # noqa: E402
import elements_page                                    # noqa: E402
import make_bank                                        # noqa: E402
import ship                                             # noqa: E402
import pipeline                                         # noqa: E402
import product_kit                                      # noqa: E402

TOUCHED = ["chain.py", "element_paths.py", "board.py", "elements.py", "elements_page.py",
           "make_bank.py", "ship.py", "pipeline.py", "product_kit.py"]
BRAND = "zz-test-brand"
# split so this folder's own grep for an account path stays empty (rule 9 of the card)
CLOUD = "Cloud" + "Storage"
FORBIDDEN = (CLOUD, "Google" + "Drive-")
ACCOUNT = "Google" + "Drive-tester@example.org"


class Base(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp())
        for p in (mock.patch.object(pathlib.Path, "home", return_value=self.home),
                  mock.patch.dict(os.environ),
                  mock.patch.object(ship, "CONF", self.home / "no-drive.json")):
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("PRODUCT_DRIVE", None)
        # LD-26 (mount switch): a worker-spawned run of this suite inherits
        # DRIVE_MOUNT=off; these tests are a person's session, so drop it.
        os.environ.pop("DRIVE_MOUNT", None)

    def assertUnder(self, path, root):
        self.assertIsNotNone(path)
        try:
            pathlib.Path(path).relative_to(root)
        except ValueError:
            self.fail(f"{path} is not under {root}")


class MountHelper(Base):
    def test_all_touched_modules_import_on_39(self):
        print(f"\n  imported under Python {sys.version_info[:2]}")
        for m in (board, elements, elements_page, make_bank, ship, pipeline, product_kit, chain):
            self.assertTrue(m.__file__)
        self.assertIs(ship._drive_index(), DI)

    def test_no_account_path_or_own_glob_left(self):
        # O9 (Drive by fileId) — components/system-integration/conventions.md, by id
        for name in TOUCHED:
            text = (HERE / name).read_text()
            for bad in FORBIDDEN:
                self.assertNotIn(bad, text, f"{name} still names {bad}")

    def test_every_site_finds_a_mount_on_any_domain(self):
        mount = self.home / "Library" / CLOUD / ACCOUNT / "Shared drives" / "Shared Assets"
        (mount / "brands" / BRAND).mkdir(parents=True)
        self.assertEqual(DI.mount(), mount)
        self.assertEqual(make_bank.drive_bank_dir("zz-bank"), mount / "banks" / "zz-bank")
        self.assertEqual(pipeline.drive_brands(), mount / "brands")
        self.assertEqual(product_kit.drive_brands(), mount / "brands")
        self.assertEqual(elements.drive_brands(), mount / "brands")
        self.assertEqual(elements_page.drive_roots(), [mount])
        self.assertUnder(ship.destination(BRAND), mount / "brands" / BRAND)

    def test_no_mount_is_none_or_loud(self):
        self.assertIsNone(make_bank.drive_bank_dir("zz-bank"))
        self.assertIsNone(pipeline.drive_brands())
        self.assertIsNone(product_kit.drive_brands())
        self.assertEqual(elements_page.drive_roots(), [])
        self.assertIsNone(ship.destination(BRAND))
        with self.assertRaises(SystemExit) as cm:
            elements.drive_brands()
        self.assertIn("Shared Assets", str(cm.exception))

    def test_ship_finds_a_shortcut_folder(self):
        acct = self.home / "Library" / CLOUD / ACCOUNT
        folder = acct / ".shortcut-targets-by-id" / "abc123" / "Shared Assets" / "brands" / BRAND
        folder.mkdir(parents=True)
        self.assertIsNone(DI.mount())
        self.assertUnder(ship.destination(BRAND), folder)

    def test_chain_count_regex_unchanged(self):
        self.assertEqual(chain._n(r'^[*][*]Scene ', "**Scene 1\n**Scene 2\n*Scene x"), 2)


if __name__ == "__main__":
    unittest.main()
