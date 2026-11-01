#!/usr/bin/env python3
"""SI-112 (doctrine one locator): both shape gates find the workspace through
run-kit's paths.repo() (triage page 12) — never two `.parent` hops up — and
find each brand's position.md / story.md through brandpath, whose
brand-identity map keeps the old top-of-folder layout.

    /usr/bin/python3 components/marketing-doctrine/test_one_locator.py

Offline: modules are imported, nothing is run. Every test tree is a temp
folder; no real brand is named.
"""
import importlib, os, sys, tempfile, unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))

import lint_position  # noqa: E402
import lint_story     # noqa: E402
from run_kit import paths  # noqa: E402

GATES = (lint_position, lint_story)


def touch(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# test\n")


class OneLocator(unittest.TestCase):

    @unittest.skipIf(os.environ.get("AI_WORKSPACE"), "AI_WORKSPACE names another checkout")
    def test_ws_is_run_kit_repo(self):
        for mod in GATES:
            with self.subTest(gate=mod.__name__):
                self.assertEqual(Path(mod.WS).resolve(), paths.repo(HERE).resolve())

    def test_no_counted_root(self):
        for mod in GATES:
            with self.subTest(gate=mod.__name__):
                self.assertNotIn("HERE.parent.parent", Path(mod.__file__).read_text())

    def test_brand_files_in_a_clone_elsewhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "elsewhere-clone"
            (ws / "components").mkdir(parents=True)
            brands = ws / "brands"
            touch(brands / "zz-a" / "brand-identity" / "position.md")
            touch(brands / "zz-a" / "brand-identity" / "story.md")
            touch(brands / "zz-b" / "position.md")       # old layout: top of the brand folder
            touch(brands / "zz-b" / "story.md")
            touch(brands / "_TEMPLATE" / "position.md")
            touch(brands / "_TEMPLATE" / "story.md")
            (brands / "zz-c").mkdir()                     # a brand with neither file
            try:
                with unittest.mock.patch.dict(os.environ, {"AI_WORKSPACE": str(ws)}):
                    for mod in GATES:
                        importlib.reload(mod)
                        fname = "position.md" if mod is lint_position else "story.md"
                        with self.subTest(gate=mod.__name__):
                            self.assertEqual(Path(mod.WS).resolve(), ws.resolve())
                            got = [Path(f).resolve() for f in mod.brand_files()]
                            self.assertEqual(got, [
                                (brands / "zz-a" / "brand-identity" / fname).resolve(),
                                (brands / "zz-b" / fname).resolve()])
                            self.assertEqual(sorted(mod.brand_names()), ["zz-a", "zz-b", "zz-c"])
            finally:
                for mod in GATES:
                    importlib.reload(mod)


if __name__ == "__main__":
    unittest.main()
