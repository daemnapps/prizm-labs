#!/usr/bin/env python3
"""local-studio's 3d job calls components/3d/make3d, and no reader names the old tools path (SI-29).

    python3 components/local-studio/test_make3d_path.py

No network. make3d is never run: the job's run() is replaced by a recorder.
"""
import argparse
import importlib.util
import os
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("local_studio_local", Path(__file__).resolve().parent / "local.py")
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

MAKE3D = m.REPO / "components" / "3d" / "make3d"
READERS = [
    "components/local-studio/local.py",
    "components/local-studio/README.md",
    "components/objects/machine/run.py",
    "components/3d/make3d.py",
]
OLD = "/".join(("tools", "3d"))     # built, so this file never matches its own grep


class Make3dPathTest(unittest.TestCase):
    def setUp(self):
        self._run = m.run
        self.calls = []
        m.run = lambda *a, **k: self.calls.append((a, k)) or {}

    def tearDown(self):
        m.run = self._run

    def test_3d_job_calls_the_component(self):
        m.job_object3d(argparse.Namespace(input="in.png", output="out.glb", seed=None))
        cmd = self.calls[0][0][0]
        self.assertEqual(cmd[0], MAKE3D)
        self.assertTrue(cmd[0].is_file())
        self.assertTrue(os.access(cmd[0], os.X_OK))
        self.assertNotIn("tools", cmd[0].relative_to(m.REPO).parts)

    def test_seed_passes_through(self):
        m.job_object3d(argparse.Namespace(input="in.png", output="out.glb", seed="7"))
        self.assertEqual(self.calls[0][0][0][-2:], ["--seed", "7"])

    def test_no_reader_names_tools_3d(self):
        for rel in READERS:
            self.assertNotIn(OLD, (m.REPO / rel).read_text(), rel)

    def test_objects_and_local_studio_agree(self):
        machine = m.REPO / "components" / "objects" / "machine"
        self.assertIn('HERE.parents[1] / "3d" / "make3d"', (machine / "run.py").read_text())
        self.assertEqual(machine.parents[1] / "3d" / "make3d", MAKE3D)


if __name__ == "__main__":
    unittest.main()
