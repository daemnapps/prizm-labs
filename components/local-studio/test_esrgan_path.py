#!/usr/bin/env python3
"""The upscale job FINDS Real-ESRGAN — never one hard-coded path (2026-10-10: the job pointed at a
tools/av path this repo does not have, and the first song ad was upscaled from another checkout).

    python3 components/local-studio/test_esrgan_path.py

No network. Real-ESRGAN is never run: the job's run() is replaced by a recorder.
"""
import argparse
import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_spec = importlib.util.spec_from_file_location("local_studio_local_esrgan", Path(__file__).resolve().parent / "local.py")
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


def fake_esrgan(folder: Path) -> Path:
    (folder / "models").mkdir(parents=True)
    b = folder / m.ESRGAN_BIN
    b.write_text("")
    b.chmod(b.stat().st_mode | stat.S_IXUSR)
    return folder


class EsrganPath(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._models, self._av = m.MODELS, m.AV_BIN
        m.MODELS, m.AV_BIN = self.tmp / "models", self.tmp / "av" / "bin"
        self.env = mock.patch.dict(os.environ, {"PATH": str(self.tmp / "empty")})
        self.env.start()
        os.environ.pop("REALESRGAN_DIR", None)

    def tearDown(self):
        self.env.stop()
        m.MODELS, m.AV_BIN = self._models, self._av

    def test_the_named_folder_wins(self):
        fake_esrgan(m.MODELS / "realesrgan")
        named = fake_esrgan(self.tmp / "elsewhere")
        os.environ["REALESRGAN_DIR"] = str(named)
        self.assertEqual(m.esrgan_dir(), named)

    def test_the_components_own_models_folder(self):
        fake_esrgan(m.AV_BIN / "realesrgan")
        own = fake_esrgan(m.MODELS / "realesrgan")
        self.assertEqual(m.esrgan_dir(), own)

    def test_the_old_tools_av_place_still_works(self):
        old = fake_esrgan(m.AV_BIN / "realesrgan")
        self.assertEqual(m.esrgan_dir(), old)

    def test_on_path(self):
        d = fake_esrgan(self.tmp / "bin")
        os.environ["PATH"] = str(d)
        self.assertEqual(m.esrgan_dir(), d.resolve())

    def test_a_binary_without_its_models_is_not_found(self):
        (m.MODELS / "realesrgan").mkdir(parents=True)
        (m.MODELS / "realesrgan" / m.ESRGAN_BIN).write_text("")
        with self.assertRaises(SystemExit) as e:
            m.esrgan_dir()
        self.assertIn(str(m.MODELS / "realesrgan"), str(e.exception))
        self.assertIn("REALESRGAN_DIR", str(e.exception))

    def test_nothing_found_names_every_place_looked(self):
        with self.assertRaises(SystemExit) as e:
            m.esrgan_dir()
        for place in (m.MODELS / "realesrgan", m.AV_BIN / "realesrgan"):
            self.assertIn(str(place), str(e.exception))

    def test_the_job_runs_the_found_binary(self):
        d = fake_esrgan(self.tmp / "found")
        os.environ["REALESRGAN_DIR"] = str(d)
        calls, real = [], m.run
        m.run = lambda *a, **k: calls.append((a, k)) or {}
        try:
            img = self.tmp / "in.png"; img.write_bytes(b"x")
            m.job_upscale(argparse.Namespace(input=str(img), output=str(self.tmp / "out.png"), scale=4, engine="esrgan",
                                             esrgan_model="realesrgan-x4plus", softness="0.0"))
        finally:
            m.run = real
        cmd = calls[0][0][0]
        self.assertEqual(cmd[0], d / m.ESRGAN_BIN)
        self.assertEqual(cmd[cmd.index("-m") + 1], d / "models")

    def test_no_reader_names_a_machine_path(self):
        text = (Path(__file__).resolve().parent / "local.py").read_text()
        for bad in ("/Users/", "devel/", "~/"):
            self.assertNotIn(bad, text)


if __name__ == "__main__":
    unittest.main()
