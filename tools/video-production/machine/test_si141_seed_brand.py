#!/usr/bin/env python3
"""SI-141 (brand names out of code): the evidence seeder takes the brand as a
required flag and writes it into the seeded run record.

    /usr/bin/python3 tools/video-production/machine/test_si141_seed_brand.py

Offline. SRC and OUT are pointed at a temp folder, so the real archive is
not read and no real run record is written; the refusal runs the real script
as a sub-process (it exits before reading anything). Stdlib only.
"""
import contextlib, importlib.util, io, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SRC = HERE / "seed_evidence.py"

_spec = importlib.util.spec_from_file_location("_si141_seed_evidence", SRC)
seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed)

ITEMS = [{"id": "abcdef0123", "stage": "scene-still", "type": "image", "iso_date": "2026-07-28T00:00:00Z",
          "params": {"prompt": "a still", "aspect_ratio": "9:16"}, "results": {"rawUrl": "u"}}]


def seeded(argv):
    with tempfile.TemporaryDirectory() as td:
        src, out = Path(td) / "evidence-run.json", Path(td) / "runs" / "x" / "run.json"
        src.write_text(json.dumps(ITEMS))
        with mock.patch.object(seed, "SRC", src), mock.patch.object(seed, "OUT", out), \
                contextlib.redirect_stdout(io.StringIO()):
            seed.main(argv)
        return json.loads(out.read_text())


class SeedBrand(unittest.TestCase):

    def test_brand_flag_is_written(self):
        run = seeded(["--brand", "zz-brand"])
        self.assertEqual(run["brand"], "zz-brand")
        self.assertEqual(len(run["stations"]["scenes"]), 1)

    def test_no_brand_refuses_in_process(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "run.json"
            with mock.patch.object(seed, "OUT", out), contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as cm:
                    seed.main([])
            self.assertEqual(cm.exception.code, 2)
            self.assertIn("--brand", err.getvalue())
            self.assertFalse(out.exists())

    def test_no_brand_refuses_on_the_command_line(self):
        r = subprocess.run([sys.executable, str(SRC)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("usage:", r.stderr)
        self.assertIn("--brand", r.stderr)

    def test_no_brand_literal_in_the_record(self):
        text = SRC.read_text(encoding="utf-8")
        self.assertIn('"brand": brand,', text)
        brands = {p.name for p in (HERE.parents[2] / "brands").iterdir()
                  if p.is_dir() and not p.name.startswith((".", "_"))}
        self.assertTrue(brands)
        self.assertEqual([b for b in sorted(brands) if b.lower() in text.lower()], [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
