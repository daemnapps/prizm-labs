#!/usr/bin/env python3
"""SI-127 (chain-checks locator), marketing-chain-checks#31 and #19: the viewer
finds the workspace through run-kit's paths.repo() and every brand file through
brandpath, and no brand is named in this component's code, comments or
docstrings (workspace rule 7).

    /usr/bin/python3 components/marketing-chain-checks/test_one_locator.py

Nothing is RUN: the viewer is imported fresh under a private name. No key, no
network, no model, and no real brand named — the names checked against are read
from the checkout's brands/ folder. The temp workspace is a tempfile folder,
never the checkout.
"""
import importlib.util, os, re, sys, tempfile, unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))
from run_kit.paths import repo  # noqa: E402

VIEWER = HERE / "marketing_chain_checks" / "viewer.py"
# every code file of the component that is not a test
SOURCES = sorted(p for p in [*HERE.glob("*.py"), *(HERE / "marketing_chain_checks").glob("*.py")]
                 if not p.name.startswith("test_"))


def load_viewer():
    """viewer.py imported fresh, so its WS is computed under the current env."""
    spec = importlib.util.spec_from_file_location("si127_viewer", str(VIEWER))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def no_env():
    return {k: v for k, v in os.environ.items() if k != "AI_WORKSPACE"}


def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


class OneLocator(unittest.TestCase):

    def test_default_is_this_checkout(self):
        with unittest.mock.patch.dict(os.environ, no_env(), clear=True):
            V = load_viewer()
            self.assertEqual(Path(V.WS).resolve(), repo(HERE).resolve())
        self.assertEqual(Path(V.WS).resolve(), HERE.parent.parent.resolve())   # unchanged from before

    def test_viewer_resolves_inside_a_temp_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "clone"
            (ws / "components").mkdir(parents=True)
            core = ws / "brands" / "zz-a" / "core-avatars"
            prof = write(core / "a1" / "profile.md", "a person\n")
            rules = write(core / "a1" / "language" / "rules.md", "talk plainly\n")
            write(core / "objection-bank.md", 'doubt: "too good to be true"\n')
            write(ws / "brands" / "zz-a" / "offers" / "objection-answers.md", "answer one\n")
            # today's place for customer-experience is `customer/` — brandpath finds it
            write(ws / "brands" / "zz-a" / "customer" / "objection-bank.md", 'doubt: "does it last"\n')
            self.assertNotEqual(ws.resolve(), (Path.home() / "Projects" / "workspace").resolve())
            with unittest.mock.patch.dict(os.environ, {"AI_WORKSPACE": str(ws)}):
                V = load_viewer()
                self.assertEqual(Path(V.WS).resolve(), ws.resolve())
                self.assertEqual(V.profile_path("zz-a", "a1").resolve(), prof.resolve())
                self.assertIsNone(V.profile_path("zz-a", "nobody"))
                self.assertIsNone(V.profile_path("zz-b", "a1"))           # another brand's folder is never read
                bank = V.bank_text("zz-a")
                self.assertIn("=== brands/zz-a/core-avatars/objection-bank.md ===", bank)
                self.assertIn("=== brands/zz-a/customer/objection-bank.md ===", bank)
                self.assertIn("=== brands/zz-a/offers/objection-answers.md ===", bank)
                self.assertIn("talk plainly", V.language_text("zz-a", "a1"))
                real = V._real_text("zz-a", "a1")
                self.assertIn(V.words_only("too good to be true"), real)
                self.assertIn(V.words_only("does it last"), real)
            self.assertTrue(rules.is_file())

    def test_no_counted_root_and_no_hand_built_brand_path(self):
        hits = [f"{p.relative_to(HERE)}:{n}: {line.strip()}"
                for p in SOURCES for n, line in enumerate(p.read_text(errors="ignore").splitlines(), 1)
                if "parents[" in line or re.search(r'"brands"\s*/', line)]
        self.assertEqual(hits, [])

    def test_no_brand_named_outside_tests(self):
        with unittest.mock.patch.dict(os.environ, no_env(), clear=True):
            brands_dir = repo(HERE) / "brands"
        names = sorted(d.name for d in brands_dir.iterdir()
                       if d.is_dir() and not d.name.startswith(("_", ".")))
        self.assertTrue(names)
        pat = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b", re.I)
        hits = [f"{p.relative_to(HERE)}:{n}"
                for p in SOURCES for n, line in enumerate(p.read_text(errors="ignore").splitlines(), 1)
                if pat.search(line)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
