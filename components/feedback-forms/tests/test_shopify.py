"""The Shopify target: a standalone template Liquid leaves alone; install only with --go (fake store, no network)."""
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import shopify as SH  # noqa: E402

TPL = HERE.parents[2] / "brands" / "_TEMPLATE"


class FakeStore:
    def __init__(self, scopes=("write_themes", "write_content"), page=None):
        self._scopes, self._page, self.calls = set(scopes), page, []

    def scopes(self):
        return self._scopes

    def main_theme(self):
        return {"id": 7, "name": "Live", "role": "main"}

    def page(self):
        return self._page

    def call(self, method, path, body=None):
        self.calls.append((method, path, body))
        return {}


class Shopify(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        shutil.copytree(TPL, self.root / "brands" / "acme")
        shutil.copytree(TPL, self.root / "brands" / "_TEMPLATE")

    def run_sh(self, *argv, store=None):
        out = io.StringIO()
        return SH.main(list(argv), out=out, root=self.root, store=store), out.getvalue()

    def test_template_is_standalone_and_raw(self):
        t = SH.template("acme", self.root)
        self.assertTrue(t.startswith("{% layout none %}\n{% raw %}\n"))
        self.assertTrue(t.rstrip().endswith("{% endraw %}"))
        self.assertIn("data-feedback-root", t)
        self.assertIn('"mode": "live"', t)

    def test_install_without_go_changes_nothing(self):
        s = FakeStore()
        code, out = self.run_sh("install", "--brand", "acme", store=s)
        self.assertEqual(code, 0)
        self.assertIn("Would:", out)
        self.assertEqual(s.calls, [])

    def test_install_with_go_adds_template_and_page(self):
        s = FakeStore()
        code, out = self.run_sh("install", "--brand", "acme", "--go", store=s)
        self.assertEqual(code, 0, out)
        self.assertEqual(s.calls[0][0:2], ("PUT", f"/api/{SH.API}/themes/7/assets.json"))
        self.assertEqual(s.calls[0][2]["asset"]["key"], "templates/page.feedback.liquid")
        self.assertEqual(s.calls[1][0], "POST")
        self.assertEqual(s.calls[1][2]["page"]["template_suffix"], "feedback")

    def test_missing_access_refuses(self):
        s = FakeStore(scopes=("read_themes",))
        code, out = self.run_sh("install", "--brand", "acme", "--go", store=s)
        self.assertEqual(code, 2)
        self.assertIn("missing: write_content, write_themes", out)
        self.assertEqual(s.calls, [])


if __name__ == "__main__":
    unittest.main()
