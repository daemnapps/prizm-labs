#!/usr/bin/env python3
"""SI-136 (objects mesh default): `make` takes the Higgsfield connector's mesh by
default (--mesh) and runs components/3d/make3d only with --local.

    /usr/bin/python3 components/objects/tests/test_mesh_route.py

No key, no network, no node or blender: sh and finish are patched, and every
write lands in a temp project. Loads run.py by file.
"""
import importlib.util, json, sys, tempfile, unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

TOOL = Path(__file__).resolve().parent.parent / "machine" / "run.py"

_spec = importlib.util.spec_from_file_location("objects_run", TOOL)
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)


class MeshRoute(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.project = self.tmp / "project"
        self.ref = self.tmp / "ref.png"
        self.ref.write_bytes(b"png")
        self.mesh = self.tmp / "given.glb"
        self.mesh.write_bytes(b"glb-from-higgsfield")
        self.sh = mock.patch.object(R, "sh").start()
        self.finish = mock.patch.object(R, "finish").start()
        self.addCleanup(mock.patch.stopall)
        self.addCleanup(self._tmp.cleanup)

    def args(self, mesh=None, local=False):
        return Namespace(project=str(self.project), id="racket", ref=str(self.ref), what="a racket",
                         word="", mesh=mesh, local=local, prompt_file=None, finish="satin", credits=0)

    def row(self):
        return json.loads((self.project / "3d/catalogue.json").read_text())["objects"]["racket"]

    def test_neither_option_exits_naming_both(self):
        with self.assertRaises(SystemExit) as e:
            R.cmd_make(self.args())
        msg = str(e.exception.code)
        self.assertIn("--mesh", msg)
        self.assertIn("--local", msg)
        self.assertNotEqual(e.exception.code, 0)
        self.sh.assert_not_called()
        self.finish.assert_not_called()
        self.assertFalse((self.project / "3d").exists())

    def test_mesh_copies_and_records_higgsfield(self):
        R.cmd_make(self.args(mesh=str(self.mesh)))
        raw = self.project / "3d/objects/racket/racket-raw.glb"
        self.assertEqual(raw.read_bytes(), b"glb-from-higgsfield")
        self.sh.assert_not_called()
        self.finish.assert_called_once_with(self.project, "racket", "satin")
        self.assertEqual(self.row()["mesh_route"], "higgsfield (given mesh)")

    def test_local_calls_make3d(self):
        make3d = self.tmp / "make3d"
        make3d.write_text("#!/bin/sh\n")
        with mock.patch.object(R, "MAKE3D", make3d):
            R.cmd_make(self.args(local=True))
        raw = self.project / "3d/objects/racket/racket-raw.glb"
        self.sh.assert_called_once_with([make3d, self.ref.resolve(), raw])
        self.assertEqual(self.row()["mesh_route"], "local (components/3d/make3d)")

    def test_local_without_make3d_keeps_its_message(self):
        with mock.patch.object(R, "MAKE3D", self.tmp / "absent" / "make3d"):
            with self.assertRaises(SystemExit) as e:
                R.cmd_make(self.args(local=True))
        self.assertIn("No local 3D generator yet (components/3d/make3d)", str(e.exception.code))
        self.sh.assert_not_called()

    def test_mesh_and_local_together_refused(self):
        with mock.patch.object(sys, "argv", ["run.py", "make", str(self.project), "racket", "--ref", str(self.ref),
                                             "--mesh", str(self.mesh), "--local"]), \
                mock.patch("sys.stderr"):
            with self.assertRaises(SystemExit) as e:
                R.main()
        self.assertNotEqual(e.exception.code, 0)
        self.assertFalse((self.project / "3d").exists())


if __name__ == "__main__":
    sys.exit(not unittest.main(exit=False).result.wasSuccessful())
