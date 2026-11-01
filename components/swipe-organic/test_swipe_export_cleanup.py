"""Swipe export cleanup — swipe-organic#13 (export brand roster) and
swipe-organic#24 (six unread files).

    /usr/bin/python3 components/swipe-organic/test_swipe_export_cleanup.py

The public export reads each feed's people line and renamed public id from the
feed's own sources.json and builds its brand scan from brands/, typing none of
them; the six unread files are gone and nothing here names them. Also runs
test_feedsexport.py's pytest-style functions, which plain python cannot.
No key, no network, no Pillow, no pytest.
"""
import ast, inspect, json, re, sys, tempfile, unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import desklib as D          # noqa: E402
import feedsexport as F      # noqa: E402

SRC = (HERE / "feedsexport.py").read_text()
SIX = ("status.py", "status.html", "progress.sh", "watch.py", "consolidate.py", "feedapp.py")
NAMES_THEM = re.compile(
    r"\b(?:status\.py|status\.html|progress\.sh|watch\.py|consolidate\.py|feedapp)\b"
    r"|^\s*(?:import|from)\s+(?:status|watch|consolidate|feedapp)\b", re.M)


class FeedsAt:
    """D.FEEDS pointed at a temp dir of made-up feeds; restored on exit."""

    def __init__(self, feeds):
        self.feeds = feeds

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for fid, extra in self.feeds.items():
            (root / fid).mkdir()
            (root / fid / "sources.json").write_text(json.dumps(dict({"sources": []}, **extra)))
        self.old = D.FEEDS
        D.FEEDS = root
        return root

    def __exit__(self, *exc):
        D.FEEDS = self.old
        self.tmp.cleanup()


class SwipeExportCleanup(unittest.TestCase):

    def test_six_files_are_gone(self):
        for n in SIX:
            self.assertFalse((HERE / n).exists(), n)

    def test_no_code_here_names_them(self):
        me = Path(__file__).resolve().name
        for p in sorted(HERE.iterdir()):
            if not p.is_file() or p.suffix not in (".py", ".sh", ".html", ".json") or p.name == me:
                continue
            m = NAMES_THEM.search(p.read_text(errors="ignore"))
            self.assertIsNone(m, f"{p.name}: {m and m.group(0)}")

    def test_no_typed_roster_or_renames(self):
        targets = {t.id for n in ast.parse(SRC).body if isinstance(n, ast.Assign)
                   for t in n.targets if isinstance(t, ast.Name)}
        self.assertFalse(targets & {"PEOPLE", "RENAME"})

    def test_feed_line_reads_sources_json(self):
        with FeedsAt({"zz-a--with-line": {"line": " A plain line. "}, "zz-a--no-line": {},
                      "zz-a--not-text": {"line": 7}, "zz-a--blank": {"line": "  "}}):
            self.assertEqual(F.feed_line("zz-a--with-line"), "A plain line.")
            for fid in ("zz-a--no-line", "zz-a--not-text", "zz-a--blank", "zz-a--missing"):
                self.assertIsNone(F.feed_line(fid), fid)

    def test_public_id_reads_sources_json(self):
        with FeedsAt({"zz-person--a-dull-name": {"public_id": "a-better-name"}, "zz-a--plain": {}}):
            self.assertEqual(F.public_id("zz-person--a-dull-name"), "a-better-name")
            self.assertEqual(F.public_id("zz-a--plain"), "plain")
            self.assertEqual(F.public_id("zz-a--missing"), "missing")

    def test_never_brand_part_comes_from_brands(self):
        self.assertTrue(F.OUR_BRANDS)
        for b in F.OUR_BRANDS:
            self.assertTrue(F.NEVER.search(f"{b}--some-feed"), b)
        self.assertIsNone(F.NEVER.search("zz-not-a-brand--some-feed"))
        low = SRC.lower()
        for b in F.OUR_BRANDS:
            self.assertNotIn(b.lower(), low, b)

    def test_real_feed_lines_are_text(self):
        got = []
        for d in sorted(D.FEEDS.iterdir()):
            if not (d / "sources.json").is_file():
                continue
            v = F.feed_line(d.name)
            self.assertTrue(v is None or (isinstance(v, str) and v), d.name)
            got.append(v)
        self.assertTrue(any(isinstance(v, str) for v in got))

    def test_old_export_rules_still_hold(self):
        import test_feedsexport as T
        for name, fn in sorted(vars(T).items()):
            if not (name.startswith("test_") and callable(fn)):
                continue
            with self.subTest(name):
                if inspect.signature(fn).parameters:
                    with tempfile.TemporaryDirectory() as t:
                        fn(Path(t))
                else:
                    fn()


if __name__ == "__main__":
    unittest.main()
