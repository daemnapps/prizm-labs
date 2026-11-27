"""The approval-page learnings hooks stay off until the owner has seen the text: the switch file is untouched, and the
held copy with three hooks on is read by nothing.

    /usr/bin/python3 components/meta-upload/tests/test_hooks_stay_off.py
"""
import json, os, sys, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import learnings as L  # noqa: E402


class HooksStayOff(unittest.TestCase):
    def test_every_switch_in_the_live_file_is_off(self):
        live = json.loads((HERE / "learnings-hooks.json").read_text())
        self.assertEqual([k for k, v in live.items() if isinstance(v, dict) and v.get("on")], [])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("META_LEARNINGS_HOOKS", None)
            for tool in ("video-teardown", "copywriter", "video-edit", "image-teardown", "image-edit"):
                self.assertFalse(L.hook_on(tool))

    def test_the_held_copy_is_a_copy_and_nothing_reads_it(self):
        held = HERE / "proposed" / "learnings-hooks.on.json"
        d = json.loads(held.read_text())
        self.assertEqual(sorted(k for k, v in d.items() if isinstance(v, dict) and v.get("on")),
                         ["copywriter", "video-edit", "video-teardown"])
        self.assertIn("HELD FOR REVIEW", d["_what"])
        self.assertEqual(L.HOOKS, HERE / "learnings-hooks.json")


if __name__ == "__main__":
    unittest.main()
