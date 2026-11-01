#!/usr/bin/env python3
"""SI-98 (shelf and index homes): a person lives only under
runs/ai-elements/<brand>/casting/<person>/ — casting_home never falls back to
brands/, and make_voice refuses a person folder under brands/.

    /usr/bin/python3 tools/video-production/machine/test_si98_casting_home.py

Every tree is a temp folder; no key, no network. Stdlib only.
"""
import sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import element_paths                                         # noqa: E402
import make_voice                                            # noqa: E402

CHECK_ALIAS = element_paths.WS / "components" / "brandpath" / "check_alias.py"


class CastingHome(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.t = Path(td.name)
        (self.t / "components").mkdir()
        self.old = self.t / "brands" / "zz-brand" / "ai-cast" / "zz-person"
        self.old.mkdir(parents=True)
        self.new = self.t / "runs" / "ai-elements" / "zz-brand" / "casting" / "zz-person"

    def test_casting_home_is_runs_only(self):
        self.assertEqual(element_paths.casting_home("zz-brand", "zz-person", self.t), self.new)

    def test_refuse_brands(self):
        with self.assertRaises(SystemExit) as e:
            make_voice.refuse_brands(self.old, self.t)
        self.assertIn("REFUSED", str(e.exception.code))
        self.assertIsNone(make_voice.refuse_brands(self.new, self.t))

    def test_commands_refuse_a_brands_person_first(self):
        with mock.patch.object(make_voice, "WS", self.t):
            for argv in (["options", str(self.old), "--line", "x", "--dry-run"],
                         ["pick", str(self.old), "--option", "1"]):
                with self.assertRaises(SystemExit) as e:
                    make_voice.main(argv)
                self.assertIn("REFUSED", str(e.exception.code), argv[0])
        self.assertFalse((self.old / "voice").exists())

    def test_check_alias_pins_one_answer(self):
        self.assertNotIn("not existed(old) else old", CHECK_ALIAS.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=1)
