"""kit_from_run.bank_file, key first (LD-47 (Drive sweep) step 2; the first mini edit run, 2026-10-20,
died stat-ing the mini's Drive folder: OSError EDEADLK). With a key the Drive folder is never touched;
a Drive-folder stat that raises is "not found", never a crash. No Drive, no network."""
import errno
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
sys.path.append(str(HERE.parents[1] / "gdrive-creator"))
import kit_from_run as K  # noqa: E402
from gdrive_creator import shared as SH, reach as R  # noqa: E402

DRIVE_FILE = ("~/Library/CloudStorage/GoogleDrive-x@example.com/Shared drives/"
              "Shared Assets/banks/music/music-mid-confident-104.mp3")


class BankFileKeyFirst(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.copy = self.tmp / "api" / "music-mid-confident-104.mp3"
        self.copy.parent.mkdir(parents=True)
        self.copy.write_bytes(b"mp3")
        real = Path.is_file

        def is_file(p):
            if "CloudStorage" in str(p):
                raise OSError(errno.EDEADLK, "Resource deadlock avoided", str(p))
            return real(p)
        for patch in (mock.patch.object(Path, "is_file", is_file),
                      mock.patch.object(K, "workspace", lambda: self.tmp / "ws")):
            patch.start()
            self.addCleanup(patch.stop)

    def test_with_a_key_the_drive_folder_is_never_touched(self):
        asked = []
        with mock.patch.object(SH, "route", lambda: "api"), \
                mock.patch.object(SH, "ensure", lambda rel: asked.append(rel) or self.copy):
            got = K.bank_file(self.tmp / "vm", "music", {"file": DRIVE_FILE})
        self.assertEqual(got, self.copy)
        self.assertEqual(asked, ["banks/music/music-mid-confident-104.mp3"])

    def test_without_a_key_a_deadlocked_stat_is_not_found(self):
        with mock.patch.object(SH, "route", lambda: "mount"), \
                mock.patch.object(R, "mount", lambda: Path(DRIVE_FILE.split("Shared Assets/")[0]) / "Shared Assets"):
            self.assertIsNone(K.bank_file(self.tmp / "vm", "music", {"file": DRIVE_FILE}))

    def test_a_local_bank_file_still_wins(self):
        local = self.tmp / "ws" / "tools" / "video-production" / "banks" / "music" / "a.mp3"
        local.parent.mkdir(parents=True)
        local.write_bytes(b"x")
        with mock.patch.object(SH, "route", lambda: "api"), \
                mock.patch.object(SH, "ensure", mock.Mock(side_effect=AssertionError("API asked for a local file"))):
            self.assertEqual(K.bank_file(self.tmp / "vm", "music", {"file": "a.mp3"}), local)


if __name__ == "__main__":
    unittest.main()
