#!/usr/bin/env python3
"""LD-68 (teardown door finds run): the mini door looks for the teardown's working folder where
run.py put it, chain.run_slug(label) — label--<operator> for anyone but the owner — and falls back
to the bare label folder, so a finished non-owner run is handed on instead of reported as stopped.

    /usr/bin/python3 tools/video-teardown/machine/test_ld68_door_finds_run.py

Stdlib only, no key, no network, no model call. Every tree is a temp folder behind a fake chain
module; the real runs/ folder is never touched.
"""
import importlib.util, os, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mini_step = _load("mini_step_ld68", HERE / "mini_step.py")


def _fake_chain(root, who):
    return types.SimpleNamespace(
        runs_root=lambda create=True: Path(root),
        run_slug=lambda base, w=None: base if (w or who) == "damon" else "%s--%s" % (base, w or who))


def _run(root, name):
    d = Path(root) / name
    d.mkdir(parents=True)
    (d / "run.json").write_text('{"brand": "brand-a"}')
    return d


class DoorFindsRun(unittest.TestCase):
    def test_operator_suffixed_folder_is_found(self):
        with tempfile.TemporaryDirectory() as t:
            C = _fake_chain(t, "dayu")
            want = _run(t, "lab-x--dayu")
            self.assertEqual(mini_step.work_dir("lab-x", C), want)

    def test_owner_bare_folder_is_found(self):
        with tempfile.TemporaryDirectory() as t:
            C = _fake_chain(t, "damon")
            want = _run(t, "lab-x")
            self.assertEqual(mini_step.work_dir("lab-x", C), want)

    def test_only_bare_folder_falls_back_to_it(self):
        with tempfile.TemporaryDirectory() as t:
            C = _fake_chain(t, "dayu")
            want = _run(t, "lab-x")
            self.assertEqual(mini_step.work_dir("lab-x", C), want)

    def test_neither_exists_gives_bare_path_without_raising(self):
        with tempfile.TemporaryDirectory() as t:
            C = _fake_chain(t, "dayu")
            got = mini_step.work_dir("lab-x", C)
            self.assertEqual(got, Path(t) / "lab-x")
            self.assertFalse(got.exists())

    def test_fake_matches_the_real_rule(self):
        real = _load("chain_ld68", HERE / "chain.py")
        with mock.patch.dict(os.environ, {"TEARDOWN_RAN_BY": "dayu"}):
            self.assertEqual(real.run_slug("lab-x"), "lab-x--dayu")
            with tempfile.TemporaryDirectory() as t:
                self.assertEqual(_fake_chain(t, "dayu").run_slug("lab-x"), real.run_slug("lab-x"))


if __name__ == "__main__":
    unittest.main()
