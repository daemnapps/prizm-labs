#!/usr/bin/env python3
"""SI-115 (reddit door fallback): the Reddit door comes from
`components/apify/reddit.py` and nowhere else.

    python3 components/research-gatherer/test_reddit_door_path.py

No pytest, no network, no key — temp folders only. Proves the lab fallback
(`lab/damon/control-room/tools/reddit.py`) is gone: a workspace holding only
that file gets a SystemExit naming the component path, which every caller
of `_run_reddit` already turns into [UNFILLED: why]. Same shape as
SI-59 (gatherer fallback cut)'s `test_apify_layer_path.py`.
"""
import inspect
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import research_gatherer.engine as R  # noqa: E402

DOOR = "components/apify/reddit.py"
LAB_DOOR = "lab/damon/control-room/tools/reddit.py"


class RedditDoorPath(unittest.TestCase):
    def setUp(self):
        self.saved = (R.WORKSPACE, R._reddit_mod)
        R._reddit_mod = None
        self._td = tempfile.TemporaryDirectory(prefix="si115-")
        self.tmp = Path(self._td.name)

    def tearDown(self):
        R.configure(self.saved[0])
        R._reddit_mod = self.saved[1]
        self._td.cleanup()

    def _write(self, rel, text):
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def test_component_door_is_the_path(self):
        self._write(DOOR, "MARK = 'component'\n")
        self._write(LAB_DOOR, "MARK = 'lab'\n")
        R.configure(self.tmp)
        self.assertEqual(R._reddit_tool(),
                         self.tmp / "components" / "apify" / "reddit.py")
        self.assertEqual(R.reddit_door().MARK, "component")

    def test_no_lab_fallback(self):
        self._write(LAB_DOOR, "MARK = 'lab'\n")
        R.configure(self.tmp)
        with self.assertRaises(SystemExit) as cm:
            R._reddit_tool()
        self.assertIn(DOOR, str(cm.exception))
        self.assertNotIn("lab", str(cm.exception).replace(str(self.tmp), ""))
        with self.assertRaises(SystemExit):
            R.reddit_door()
        self.assertIsNone(R._reddit_mod)

    def test_source_names_no_lab_door(self):
        text = (HERE / "research_gatherer" / "engine.py").read_text()
        self.assertNotIn(LAB_DOOR, text)
        self.assertNotIn('"lab" / "damon"', text)
        self.assertNotIn('"lab"', inspect.getsource(R._reddit_tool))
        self.assertIn(DOOR, R._reddit_tool.__doc__)

    def test_real_workspace_has_the_door(self):
        R.configure(self.saved[0])
        self.assertTrue(R._reddit_tool().is_file())


if __name__ == "__main__":
    unittest.main()
