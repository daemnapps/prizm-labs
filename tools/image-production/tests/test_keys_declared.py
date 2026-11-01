#!/usr/bin/env python3
"""LD-5 (image keys declared) — image-production's key names are visible to the
worker's code scan, so a mini run is handed the keys it routes to.

The worker hands a lab run only the keys its code is SEEN to read (WM-121
(component keys from code)); models.json is data the scan never reads, so
route.KEY_NAMES carries every `key` it names as string literals.

  (1) match — every distinct `key` in models.json is in route.KEY_NAMES and
              vice versa.
  (2) scan  — with real git, lab_run.component_keys at this checkout's HEAD,
              walking from make.py, hands OPENAI_API_KEY. It reads the tree AT
              THE SHA, so it sees route.py as committed, never the working copy.

No network, no key value: names only.

Run: python3 tools/image-production/tests/test_keys_declared.py
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LANE = HERE.parent
REPO = LANE.parent.parent
MINI = REPO / "platform" / "workers" / "mini-worker"
sys.path.append(str(LANE))                         # APPEND — never insert at 0
sys.path.append(str(MINI))
from image_production import route as R            # noqa: E402
import lab_run as LR                               # noqa: E402

ENTRY = "tools/image-production/make.py"


def _keys_in(node):
    """Every string value of a `key` field, anywhere in the table."""
    found = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "key" and isinstance(v, str):
                found.add(v)
            else:
                found |= _keys_in(v)
    elif isinstance(node, list):
        for v in node:
            found |= _keys_in(v)
    return found


class KeyNamesMatchTheTable(unittest.TestCase):
    def test_every_key_in_models_json_is_declared_and_nothing_else(self):
        table = json.loads((LANE / "models.json").read_text())
        in_table = _keys_in(table)
        self.assertIn("OPENAI_API_KEY", in_table)          # the table really names it
        self.assertIsInstance(R.KEY_NAMES, tuple)
        self.assertEqual(len(R.KEY_NAMES), len(set(R.KEY_NAMES)), "KEY_NAMES repeats a name")
        self.assertEqual(set(R.KEY_NAMES), in_table)


class TheWorkerScanSeesThem(unittest.TestCase):
    def test_component_keys_from_make_py_hands_openai(self):
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             check=True).stdout.decode().strip()
        keys = LR.component_keys(sha, "image-production", REPO, entry=ENTRY)
        self.assertIn("OPENAI_API_KEY", keys, "keys seen at {0}: {1}".format(sha, sorted(keys)))
        self.assertTrue(any("image_production/route.py" in ev
                            for ev in keys["OPENAI_API_KEY"]), keys["OPENAI_API_KEY"])


if __name__ == "__main__":
    unittest.main()
