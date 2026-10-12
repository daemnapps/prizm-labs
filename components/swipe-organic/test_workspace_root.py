#!/usr/bin/env python3
"""SI-70 (swipe workspace root): every reader in this desk takes the workspace
from desklib.WS — run-kit's paths.repo() (triage page 12) — never three
`.parent` hops up (the old lab depth, one folder above the clone) and never
one person's home folder.

    /usr/bin/python3 components/swipe-organic/test_workspace_root.py

Nothing is RUN: modules are imported. No key, no network, no model, no Drive,
and no real brand named.
"""
import ast, importlib.util, json, os, re, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]

import desklib as D  # noqa: E402

FILES = ("desk.py", "briefs.py", "subfeeds.py", "profile.py", "app.py", "formats.py", "paidpack.py",
         # SI-111 (organic one locator): the hand-rolled walks that passed the first scan
         "add.py", "packs.py", "paiddata.py", "bundle.py", "slideshows.py", "apify.py", "feedsexport.py")
BAD = (r"/Users/[a-z]+/Projects/workspace|\.parent\.parent\.parent"
       r'|\bHERE\.parent\.parent\b'
       r'|\(d / "components"\)\.is_dir\(\) and \(d / "brands"\)')


def load_path(path, name):
    """Import one file fresh, with sys.argv naming it while it executes."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    argv = sys.argv
    sys.argv = [str(path)]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = argv
    return mod


def load(name):
    return load_path(HERE / (name + ".py"), "si70_" + name)


def code_lines(p):
    """Every source line that is not a comment and not inside a docstring
    (as in components/run-kit/test_workspace_paths.py)."""
    src = p.read_text(errors="ignore")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    doc = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
           and isinstance(node.value.value, str):
            doc.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    out = []
    for n, line in enumerate(src.splitlines(), 1):
        if n in doc or line.lstrip().startswith("#"):
            continue
        out.append((n, line))
    return out


def same(a, b):
    return Path(a).resolve() == Path(b).resolve()


class WorkspaceRoot(unittest.TestCase):

    def test_no_counted_root_and_no_home_literal(self):
        hits = [f"{f}:{n}: {line.strip()}" for f in FILES
                for n, line in code_lines(HERE / f) if re.search(BAD, line)]
        self.assertEqual(hits, [])

    @unittest.skipIf(os.environ.get("AI_WORKSPACE"), "AI_WORKSPACE names another checkout")
    def test_desklib_ws_is_this_checkout(self):
        self.assertEqual(Path(D.WS).resolve(), REPO.resolve())

    def test_every_reader_shares_desklib_ws(self):
        for name in ("desk", "briefs", "profile", "app"):
            with self.subTest(name=name):
                self.assertTrue(same(load(name).WS, D.WS))
        self.assertEqual(load("subfeeds").BRANDS, D.WS / "brands")

    def test_app_paths_are_inside_the_checkout(self):
        app = load("app")
        self.assertTrue(app.CHAIN.is_dir(), str(app.CHAIN))
        self.assertIsNotNone(app.BRANDS_DIR)
        self.assertTrue(same(app.BRANDS_DIR, D.WS / "brands"))

    def test_sub_avatar_card_goes_through_brandpath(self):
        briefs = load("briefs")
        with tempfile.TemporaryDirectory() as tmp:
            brand = Path(tmp) / "brands" / "zz-test-brand"
            subs = brand / "avatars" / "core-1" / "sub-avatars"
            subs.mkdir(parents=True)
            (subs / "sub-07-early-riser.md").write_text("# a test card\n")
            (brand / "FOLDERS.json").write_text(json.dumps({"core-avatars": ["avatars"]}))
            old = briefs.WS
            briefs.WS = Path(tmp)
            try:
                stem = briefs.sub_stem({"brand": "zz-test-brand", "core": "core-1",
                                        "sub": "early-riser"})
            finally:
                briefs.WS = old
        self.assertEqual(stem, "sub-07-early-riser")

    def test_swipe_paid_profile_finds_the_checkout(self):
        mod = load_path(REPO / "components" / "swipe-paid" / "profile.py", "si70_paid_profile")
        self.assertEqual(Path(mod.WS).resolve(), Path(D.WS).resolve())

    def test_ingest_names_no_personal_venv(self):
        src = (REPO / "components" / "swipe-paid" / "own" / "ingest.py").read_text()
        self.assertNotIn(".local/venvs", src)
        self.assertIn("pip install 'psycopg[binary]'", src)


if __name__ == "__main__":
    unittest.main()
