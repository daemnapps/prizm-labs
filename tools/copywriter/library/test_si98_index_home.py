#!/usr/bin/env python3
"""SI-98 (shelf and index homes): the copy library's index renders under
runs/copywriter/_system/library/index.json, and both pages read it there.

    /usr/bin/python3 tools/copywriter/library/test_si98_index_home.py

main() runs with every reader stubbed and INDEX pointed at a temp file, so
nothing under the real runs/ or this folder is written. Stdlib only.
"""
import contextlib, importlib.util, io, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
EXPECTED = REPO / "runs" / "copywriter" / "_system" / "library" / "index.json"
OLD = HERE / "index.json"
READERS = ("emails", "captions", "angles", "raw_ads", "pages", "teardowns", "our_pages", "machine")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(m)
    return m


build = load("_si98_build_library", HERE / "build_library.py")
page = load("_si98_library_page", HERE / "library_page.py")
cmap = load("_si98_channel_map_page", HERE.parent / "machine" / "channel_map_page.py")


class IndexHome(unittest.TestCase):

    def test_every_reader_and_the_writer_name_the_runs_home(self):
        for m in (build, page, cmap):
            self.assertEqual(m.INDEX, EXPECTED, m.__name__)
        for f in ("build_library.py", "library_page.py"):
            self.assertNotIn('HERE / "index.json"', (HERE / f).read_text(encoding="utf-8"), f)
        self.assertNotIn('"library" / "index.json"',
                         (HERE.parent / "machine" / "channel_map_page.py").read_text(encoding="utf-8"))

    def test_main_writes_the_index_where_INDEX_says(self):
        before = OLD.stat().st_mtime_ns if OLD.exists() else None
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "x" / "index.json"
            with contextlib.ExitStack() as st:
                st.enter_context(mock.patch.object(build, "INDEX", target))
                for r in READERS:
                    st.enter_context(mock.patch.object(build, r, lambda *a, **k: None))
                st.enter_context(contextlib.redirect_stdout(io.StringIO()))
                build.main()
            self.assertIn("rows", json.loads(target.read_text(encoding="utf-8")))
        after = OLD.stat().st_mtime_ns if OLD.exists() else None
        self.assertEqual(before, after)

    def test_channel_map_counts_read_INDEX(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "index.json"
            f.write_text(json.dumps({"rows": [{"origin": "swiped", "format": "f1"},
                                              {"origin": "machine", "format": "f1"}]}))
            with mock.patch.object(cmap, "INDEX", f):
                self.assertEqual(cmap.counts(), {"f1": {"swiped": 1}})
            with mock.patch.object(cmap, "INDEX", Path(td) / "missing.json"):
                self.assertEqual(cmap.counts(), {})


if __name__ == "__main__":
    unittest.main(verbosity=1)
