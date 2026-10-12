#!/usr/bin/env python3
"""SI-182 (swipe one shape): readers read blocks/, the old engine sits in capture/archive/.

    /usr/bin/python3 components/swipe-paid/test_damon1_one_shape.py

the owner, 2026-10-08, I-196 (the owner notice and asks): the advertiser folder's shape
is blocks/, and the run is build.py + build_page.py. Both readers are loaded by
path and pointed at a temp pool, so nothing under the real pool, runs/ or
brands/ is read or written. Stdlib only, offline, no key.
"""
import contextlib, importlib.util, io, re, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent                     # components/swipe-paid
REPO = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
LIBRARY = REPO / "tools" / "copywriter" / "library" / "build_library.py"
CHECK = REPO / "tools" / "image-teardown" / "tools" / "check.py"
CAPTURE = HERE / "capture"
ARCHIVE = CAPTURE / "archive"
ARCHIVED = ("swipe.py", "build_teardown_page.py", "build_machine_page.py")
# A file name (not build_swipe_library.py or swipe_intake.py) or an import of one.
NAMES = re.compile(r"(?<![\w-])swipe\.py|build_teardown_page|build_machine_page"
                   r"|\bimport swipe\b|\bfrom swipe import\b|\bcapture\.swipe\b"
                   r"|\bfrom capture import\b.*\bswipe\b")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(m)
    return m


build = load("_si182_build_library", LIBRARY)
check = load("_si182_check", CHECK)


def record(headline, live):
    """A block or angle file, in the lines both readers parse."""
    return (f"# {headline}\n\n**{live} live creatives** — {live} video, 0 image  \n\n"
            f"## Headline\n\n> {headline}\n\n## Primary text (verbatim)\n\n> words for {headline}\n")


def pool(root):
    """zz-both: blocks/ (1 file) beside angles/ (2 files, other words).
    zz-angles-only: angles/ (3 files). zz-neither: no records at all."""
    p = root / "components" / "swipe-paid"
    (p / "zz-neither" / "_pages").mkdir(parents=True)
    files = {
        "zz-both/blocks/01_b.md": record("block headline", 7),
        "zz-both/angles/01_b.md": record("angle headline one", 1),
        "zz-both/angles/02_b.md": record("angle headline two", 1),
        "zz-angles-only/angles/01_a.md": record("fallback one", 2),
        "zz-angles-only/angles/02_a.md": record("fallback two", 2),
        "zz-angles-only/angles/03_a.md": record("fallback three", 2),
    }
    for rel, text in files.items():
        f = p / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    return p


class CopywriterLibraryReadsBlocks(unittest.TestCase):

    def setUp(self):
        build.rows[:] = []
        build.notes[:] = []
        self._td = tempfile.TemporaryDirectory()
        ws = Path(self._td.name)
        sp = pool(ws)
        with mock.patch.object(build, "WS", ws), mock.patch.object(build, "SWIPE_PAID", sp), \
                contextlib.redirect_stdout(io.StringIO()):
            build.angles()
        self.by_brand = {}
        for r in build.rows:
            self.by_brand.setdefault(r["tags"]["swipe_brand"], []).append(r)

    def tearDown(self):
        self._td.cleanup()

    def test_a_brand_with_blocks_and_angles_is_read_from_blocks(self):
        rows = self.by_brand["zz-both"]
        self.assertEqual(len(rows), 2, rows)       # one angle row + one primary-text row
        self.assertTrue(all(r["path"] == "components/swipe-paid/zz-both/blocks/01_b.md" for r in rows), rows)
        self.assertEqual({r["title"] for r in rows}, {"block headline"})
        self.assertEqual({r["tags"]["live_creatives"] for r in rows}, {7})

    def test_a_brand_with_only_angles_falls_back(self):
        rows = self.by_brand["zz-angles-only"]
        self.assertEqual(len(rows), 6, rows)
        self.assertTrue(all("/zz-angles-only/angles/" in r["path"] for r in rows), rows)
        self.assertEqual({r["title"] for r in rows}, {"fallback one", "fallback two", "fallback three"})

    def test_angles_beside_blocks_are_not_read(self):
        self.assertEqual(sorted(self.by_brand), ["zz-angles-only", "zz-both"])
        self.assertFalse(any("angle headline" in r["title"] for r in build.rows))


class ImageTeardownCountsBlocks(unittest.TestCase):

    def test_blocks_win_angles_fall_back_and_the_word_is_block(self):
        with tempfile.TemporaryDirectory() as td:
            sp = pool(Path(td))
            with mock.patch.object(check.P, "SWIPE", sp):
                ok, msg = check.swipe_records()
        self.assertTrue(ok, msg)
        # zz-both counts its 1 block (not its 2 angles); zz-angles-only its 3 angles.
        self.assertEqual(msg, "2 brands, 4 block records — zz-angles-only, zz-both")

    def test_an_empty_pool_says_block_records(self):
        with tempfile.TemporaryDirectory() as td:
            sp = Path(td) / "swipe-paid"
            sp.mkdir()
            with mock.patch.object(check.P, "SWIPE", sp):
                ok, msg = check.swipe_records()
        self.assertFalse(ok)
        self.assertIn("no brands with block records under", msg)
        self.assertNotIn("angle", msg)


class OldEngineArchived(unittest.TestCase):

    def test_the_three_files_moved_into_archive(self):
        for name in ARCHIVED:
            self.assertFalse((CAPTURE / name).exists(), f"capture/{name} still in capture/")
            self.assertTrue((ARCHIVE / name).is_file(), f"capture/archive/{name} missing")

    def test_archive_readme_names_the_run(self):
        text = (ARCHIVE / "README.md").read_text(encoding="utf-8")
        for word in ("build.py", "build_page.py", "nine-stage", "the owner", "2026-10-08"):
            self.assertIn(word, text)

    def test_the_modules_build_py_uses_stay_in_capture(self):
        for name in ("adplexity_client.py", "capture_pages.py", "drive_links.py", "sync_to_drive.py"):
            self.assertTrue((CAPTURE / name).is_file(), name)

    def test_no_code_outside_archive_names_them_but_build_page_history(self):
        """Every .py and .sh in swipe-paid outside archive/ (and this test).
        Advertiser write-ups are data, not code, and are not scanned."""
        me = Path(__file__).resolve()
        hits = []
        for f in sorted(HERE.rglob("*")):
            if f.suffix not in (".py", ".sh") or not f.is_file() or f.resolve() == me:
                continue
            if ARCHIVE in f.parents:
                continue
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if NAMES.search(line):
                    hits.append((str(f.relative_to(HERE)), i, line.strip()))
        self.assertEqual(len(hits), 1, hits)
        rel, _, line = hits[0]
        self.assertEqual(rel, "build_page.py")
        self.assertIn("build_teardown_page.py", line)
        self.assertIn("replaces", line)


if __name__ == "__main__":
    unittest.main(verbosity=1)
