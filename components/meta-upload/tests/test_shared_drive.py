"""SI-40 (meta mount helper): meta-upload finds Shared Assets through the shared
mount helper (components/brandpath drive_index.mount()), types no account, has
no home-checkout fallback, reads a mount that will not stat as absent, and its
writers refuse (cards, to_check) or skip by name (learnings) with no mount and no
META_CARDS_ROOT. Stdlib only: no PIL, no network, no key; the real mount is
never read."""
import io, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))
sys.path.append(str(HERE.parent / "brandpath"))
# the module constants are read at import; none of them may come from this machine's mount
with mock.patch("drive_index.mount", return_value=None):
    import shared_drive as SD, drop, to_check as T, learnings as L, cards as C

DEADLK = OSError(11, "Resource deadlock avoided")


class Base(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("META_CARDS_ROOT", None)
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.tmp = Path(d.name)


class SharedDrive(Base):
    def test_shared_assets(self):
        with mock.patch.object(SD.DI, "mount", return_value=self.tmp):
            self.assertEqual(SD.shared_assets(), self.tmp)
        with mock.patch.object(SD.DI, "mount", return_value=None):
            self.assertEqual(SD.shared_assets(), SD.NO_MOUNT)
        with mock.patch.object(SD.DI, "mount", side_effect=DEADLK):
            self.assertEqual(SD.shared_assets(), SD.NO_MOUNT)
        self.assertFalse(SD.NO_MOUNT.exists())
        self.assertTrue(SD.mounted(self.tmp))
        self.assertFalse(SD.mounted(SD.NO_MOUNT))


class Drop(Base):
    def test_where_has_no_home_checkout_root(self):
        sa = self.tmp / "sa"
        (sa / "x").mkdir(parents=True)
        (sa / "x/y.txt").write_text("y")
        with mock.patch.object(drop, "DRIVE", sa):
            self.assertEqual(drop.where("x/y.txt"), sa / "x/y.txt")
        home = self.tmp / "home"
        (home / "Projects/workspace/x").mkdir(parents=True)
        (home / "Projects/workspace/x/z.txt").write_text("z")
        with mock.patch.object(drop, "DRIVE", SD.NO_MOUNT), \
                mock.patch.object(Path, "home", return_value=home):
            self.assertEqual(drop.where("x/z.txt"), drop.REPO / "x/z.txt")

    def test_a_mount_that_will_not_stat_reads_as_absent(self):
        with mock.patch.object(Path, "is_file", side_effect=DEADLK), \
                mock.patch.object(Path, "exists", side_effect=DEADLK):
            self.assertFalse(drop._is_file(Path("a")))
            self.assertFalse(drop._exists(Path("a")))


class Writers(Base):
    def test_card_filing_refuses_by_name(self):
        with mock.patch.object(T, "SHARED", SD.NO_MOUNT):
            with self.assertRaises(T.Refused) as e:
                T.cards_root()
            self.assertIn("META_CARDS_ROOT", str(e.exception))
            os.environ["META_CARDS_ROOT"] = str(self.tmp)
            self.assertEqual(T.cards_root(), self.tmp)

    def test_cards_root_refuses_by_name(self):
        with mock.patch.object(C, "DRIVE", SD.NO_MOUNT):
            with self.assertRaises(SystemExit) as e:
                C.root()
            self.assertIn("META_CARDS_ROOT", str(e.exception))
        with mock.patch.object(C, "DRIVE", self.tmp / "sa"):
            self.assertEqual(C.root(), self.tmp / "sa" / "meta")
        os.environ["META_CARDS_ROOT"] = str(self.tmp)
        self.assertEqual(C.root(), self.tmp)

    def test_learnings_without_a_root_logs_nothing_and_says_so(self):
        args = ({"ad_name": "zz_x_brief-0001_batch-2026-01-01-a", "brand": "zz-brand"},
                {"brand": "zz-brand", "lane": "image", "name": "n"}, "tester",
                [{"id": "r1", "label": "l", "step": 1, "tool": "t"}], "note")
        err = io.StringIO()
        with mock.patch.object(L, "DRIVE", SD.NO_MOUNT), mock.patch("sys.stderr", err):
            self.assertIsInstance(L.record(*args), dict)
        self.assertFalse(SD.NO_MOUNT.exists())
        self.assertIn("NOT logged", err.getvalue())
        os.environ["META_CARDS_ROOT"] = str(self.tmp)
        with mock.patch.object(L, "DRIVE", SD.NO_MOUNT):
            L.record(*args)
        self.assertEqual(len((self.tmp / "learnings.jsonl").read_text().splitlines()), 1)


class Literals(unittest.TestCase):
    def test_no_account_and_no_home_checkout_typed(self):
        for p in sorted(HERE.rglob("*")):
            if p.suffix in (".py", ".md") and p.is_file():
                self.assertNotIn("GoogleDrive-" + "damon@", p.read_text(errors="replace"), p)
        for name in ("drop.py", "to_check.py", "learnings.py"):
            self.assertNotIn("Projects/workspace", (HERE / name).read_text(), name)


if __name__ == "__main__":
    unittest.main()
