"""names.add_alias — naming's own door for writing brief-aliases.json, so a
caller never writes the file or resets the cache itself (SI-121 (teardown
stops reaching)). Every write goes to a temp copy; the real file is only read.

    python3 components/naming/test_add_alias.py
"""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import names as N  # noqa: E402


class AddAlias(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.f = Path(td.name) / "brief-aliases.json"
        shutil.copy(HERE / "brief-aliases.json", self.f)
        self.before = json.loads(self.f.read_text())
        saved = N._ALIASES
        self.addCleanup(lambda: setattr(N, "_ALIASES", saved))

    def test_add_then_reread(self):
        N.add_alias("p999", "brief-0999", self.f)
        after = json.loads(self.f.read_text())
        self.assertEqual(after["aliases"]["p999"], "brief-0999")
        # everything that was there is still there
        for k, v in self.before.get("aliases", {}).items():
            self.assertEqual(after["aliases"][k], v)
        for k in self.before:
            self.assertIn(k, after)

    def test_a_write_drops_the_cache(self):
        N._ALIASES = {"aliases": {}, "never_used": []}
        N.add_alias("p999", "brief-0999", self.f)
        self.assertIsNone(N._ALIASES)

    def test_idempotent(self):
        N.add_alias("p999", "brief-0999", self.f)
        once = self.f.read_text()
        stale = {"aliases": {"kept": "as-is"}}
        N._ALIASES = stale
        N.add_alias("p999", "brief-0999", self.f)
        self.assertEqual(self.f.read_text(), once)
        self.assertIs(N._ALIASES, stale)              # nothing written, cache left alone

    def test_a_changed_entry_is_rewritten(self):
        N.add_alias("p999", "brief-0999", self.f)
        N.add_alias("p999", "brief-0998", self.f)
        self.assertEqual(json.loads(self.f.read_text())["aliases"]["p999"], "brief-0998")

    def test_missing_file_is_started(self):
        self.f.unlink()
        N.add_alias("p001", "brief-0001", self.f)
        self.assertEqual(json.loads(self.f.read_text()), {"aliases": {"p001": "brief-0001"}})

    def test_same_format_as_before(self):
        N.add_alias("p999", "brief-0999", self.f)
        al = json.loads(self.f.read_text())
        self.assertEqual(self.f.read_text(), json.dumps(al, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    unittest.main()
