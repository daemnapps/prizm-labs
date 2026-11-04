#!/usr/bin/env python3
"""SI-59 (gatherer fallback cut): the Apify layer comes from
`components/apify/apify.py` and nowhere else.

    python3 components/research-gatherer/test_apify_layer_path.py

No pytest, no network, no key — temp folders only. Proves the dead lab
fallback (`lab/owner/swipe-organic/apify.py`) is gone: a workspace holding
only that file gets the component path back and a RuntimeError naming it,
which every caller already turns into [UNFILLED: why].
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import research_gatherer.engine as R  # noqa: E402

LAYER = "components/apify/apify.py"


class ApifyLayerPath(unittest.TestCase):
    def setUp(self):
        self.saved = (R.WORKSPACE, R._apify_mod)
        R._apify_mod = None
        self.tmp = Path(tempfile.mkdtemp(prefix="si59-"))

    def tearDown(self):
        R.configure(self.saved[0])
        R._apify_mod = self.saved[1]
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, rel, text):
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def test_no_lab_fallback(self):
        self._write("lab/owner/swipe-organic/apify.py", "MARK = 'lab'\n")
        R.configure(self.tmp)
        self.assertEqual(R._swipe_apify(),
                         self.tmp / "components" / "apify" / "apify.py")
        with self.assertRaises(RuntimeError) as cm:
            R.apify_layer()
        self.assertIn(LAYER, str(cm.exception))

    def test_component_layer_loads(self):
        self._write(LAYER, "MARK = 'component'\n")
        R.configure(self.tmp)
        self.assertEqual(R.apify_layer().MARK, "component")

    def test_source_names_only_the_component(self):
        text = (HERE / "research_gatherer" / "engine.py").read_text()
        self.assertNotIn("lab/owner/swipe-organic", text)
        self.assertNotIn("components/swipe-organic/apify.py", text)
        self.assertIn(LAYER, R.__doc__)
        self.assertIn(LAYER, R.apify_layer.__doc__)

    def test_real_workspace_has_the_layer(self):
        R.configure(self.saved[0])
        self.assertTrue(R._swipe_apify().is_file())


if __name__ == "__main__":
    unittest.main()
