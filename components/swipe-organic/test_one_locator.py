#!/usr/bin/env python3
"""SI-111 (organic one locator), swipe-organic#29: every workspace lookup in
this desk is run-kit's paths.repo() — the five `_workspace()` copies, add.py's
workspace() and apify.py's `_ws()` are wrappers over it, and no hand-rolled
walk is left in the desk's code.

    /usr/bin/python3 components/swipe-organic/test_one_locator.py

Nothing is RUN: modules are imported. No key, no network, no model, no Drive,
and no real brand named. The temp clone is a tempfile folder, never the checkout.
"""
import ast, importlib.util, os, re, sys, tempfile, unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))
from run_kit.paths import repo  # noqa: E402

# module -> the locator it exposes
LOCATORS = (("packs", "_workspace"), ("paidpack", "_workspace"), ("paiddata", "_workspace"),
            ("bundle", "_workspace"), ("slideshows", "_workspace"), ("add", "workspace"),
            ("apify", "_ws"))
WALK = re.compile(r'/ "components"\)\.is_dir\(\) and \(\w+ / "brands"\)|\bHERE\.parent\.parent\b')


def load(name):
    """Import one file fresh under a private name, with sys.argv naming it."""
    path = HERE / (name + ".py")
    spec = importlib.util.spec_from_file_location("si111_" + name, str(path))
    mod = importlib.util.module_from_spec(spec)
    argv = sys.argv
    sys.argv = [str(path)]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = argv
    return mod


def code_lines(p):
    """Every source line that is not a comment and not inside a docstring."""
    src = p.read_text(errors="ignore")
    try:
        tree = ast.parse(src)
    except SyntaxError:          # unparseable here: scan every line rather than skip the file
        tree = ast.parse("")
    doc = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
           and isinstance(node.value.value, str):
            doc.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return [(n, line) for n, line in enumerate(src.splitlines(), 1)
            if n not in doc and not line.lstrip().startswith("#")]


def no_env():
    return {k: v for k, v in os.environ.items() if k != "AI_WORKSPACE"}


class OneLocator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mods = {name: load(name) for name, _ in LOCATORS}

    def call(self, name, fn):
        return Path(getattr(self.mods[name], fn)()).resolve()

    def test_each_locator_is_run_kit_repo_here(self):
        with unittest.mock.patch.dict(os.environ, no_env(), clear=True):
            want = repo(HERE).resolve()
            for name, fn in LOCATORS:
                with self.subTest(module=name):
                    self.assertEqual(self.call(name, fn), want)
        self.assertTrue((want / "components" / "swipe-organic").is_dir())

    def test_each_locator_follows_ai_workspace_to_a_temp_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "clone"
            (clone / "components").mkdir(parents=True)
            (clone / "brands").mkdir()
            self.assertNotEqual(clone.resolve(), (Path(os.environ.get("AI_WORKSPACE", "."))).resolve())
            with unittest.mock.patch.dict(os.environ, {"AI_WORKSPACE": str(clone)}):
                self.assertEqual(Path(repo(HERE)).resolve(), clone.resolve())
                for name, fn in LOCATORS:
                    with self.subTest(module=name):
                        self.assertEqual(self.call(name, fn), clone.resolve())

    def test_no_hand_rolled_walk_outside_run_kit(self):
        hits = [f"{p.name}:{n}: {line.strip()}"
                for p in sorted(HERE.glob("*.py")) if not p.name.startswith("test_")
                for n, line in code_lines(p) if WALK.search(line)]
        self.assertEqual(hits, [])

    def test_feedsexport_still_reaches_packs_workspace(self):
        src = (HERE / "feedsexport.py").read_text()
        self.assertEqual(src.count("packs._workspace()"), 2)


if __name__ == "__main__":
    unittest.main()
