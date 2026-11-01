"""SI-139 (dead builder files): the four dead page-builder files stay gone.

build_pages.py raised at import (its page_template.html was never in the
folder); thumbs.py, videolinks.json and test_thumbs_swipe_home.py served only
it. proven_to_format.py still reads BUILDER's template and cache/ — kept.

    python3 components/ad-variations/machine/test_no_dead_builder.py
"""
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
BUILDER = COMP / "page" / "builder"          # proven_to_format.py's BUILDER
COMPONENTS = COMP.parent

DEAD = ("build_pages.py", "thumbs.py", "videolinks.json", "test_thumbs_swipe_home.py")
# names a reader would carry; bare "thumbs.py" also names video-edit's own live file
NEEDLES = (b"build_pages.py", b"page/builder/thumbs.py", b"videolinks.json", b"test_thumbs_swipe_home")
SKIP_DIRS = {".git", "__pycache__", "node_modules"}


class NoDeadBuilder(unittest.TestCase):
    def test_four_paths_gone(self):
        for name in DEAD:
            self.assertFalse((BUILDER / name).exists(), name)

    def test_proven_to_format_inputs_kept(self):
        self.assertTrue((BUILDER / "proven_to_format_template.html").is_file())
        self.assertTrue((BUILDER / "cache").is_dir())
        src = (HERE / "proven_to_format.py").read_text(encoding="utf-8")
        self.assertIn('BUILDER = COMP / "page" / "builder"', src)
        self.assertIn('BUILDER / "proven_to_format_template.html"', src)
        self.assertIn('BUILDER / "cache"', src)

    def test_no_reader_in_components(self):
        me = Path(__file__).resolve()
        hits = []
        for p in COMPONENTS.rglob("*"):
            if not p.is_file() or p.resolve() == me or SKIP_DIRS & set(p.parts):
                continue
            data = p.read_bytes()
            hits += [f"{p.relative_to(COMPONENTS)}: {n.decode()}" for n in NEEDLES if n in data]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
