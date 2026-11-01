"""python3 machine/test_py39_parse.py — every machine file parses on the mini's 3.9.6. No network, no model, writes nothing."""
import ast
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class T(unittest.TestCase):
    def test_every_machine_file_parses(self):
        files = sorted(HERE.glob("*.py"))
        self.assertTrue(files)
        for f in files:
            with self.subTest(file=f.name):
                ast.parse(f.read_text(encoding="utf-8"), filename=str(f))

    def test_run_imports(self):
        r = subprocess.run([sys.executable, "-c", "import run, assemble"], cwd=str(HERE),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_same_numbers(self):
        self.assertEqual(format(12345.6, ",.0f"), "12,346")
        self.assertEqual(format(0, ",.0f"), "0")

    def test_page_hoist(self):
        src = (HERE / "page.py").read_text(encoding="utf-8")
        self.assertIn('ixjson = json.dumps(indexes, ensure_ascii=False).replace(', src)
        self.assertIn("{ixjson}", src)
        self.assertNotIn(r'.replace("</", "<\\/")}', src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
