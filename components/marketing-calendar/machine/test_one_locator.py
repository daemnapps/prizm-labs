#!/usr/bin/env python3
"""The calendar finds its workspace through run-kit's paths.repo() and its
brand folders through brandpath — no named default in anyone's home folder
(SI-109 (calendar one locator); DW-1 (one locator sweep) 2 of 5). Proven
offline in a made-up workspace: no model, no network, no real brand.

    /usr/bin/python3 components/marketing-calendar/machine/test_one_locator.py
"""
import os
import sys
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
# the script's own folder is sys.path[0], and it holds a calendar.py of its own:
# take it off so the stdlib's calendar is the one cached, then put it back
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != MACHINE]
import calendar as _stdlib_calendar      # noqa: E402,F401
import importlib                         # noqa: E402
import subprocess                        # noqa: E402
import tempfile                          # noqa: E402
import unittest                          # noqa: E402
import unittest.mock                     # noqa: E402
sys.path.insert(0, str(MACHINE))

import paths as P                        # noqa: E402
import gates as G                        # noqa: E402
from run_kit import paths as KIT         # noqa: E402

BRAND = "zz-brand"


def unset():
    """os.environ without AI_WORKSPACE, restored afterwards."""
    env = {k: v for k, v in os.environ.items() if k != "AI_WORKSPACE"}
    return unittest.mock.patch.dict(os.environ, env, clear=True)


def listing(root):
    root = Path(root)
    if not root.exists():
        return []
    return sorted((str(p.relative_to(root)), p.stat().st_mtime_ns)
                  for p in root.rglob("*"))


class OneLocator(unittest.TestCase):
    def tearDown(self):
        with unset():
            importlib.reload(P)

    def test_a_temp_clone_elsewhere_is_the_workspace(self):
        with tempfile.TemporaryDirectory(prefix="one-locator-test-") as tmp:
            ws = Path(tmp)
            self.assertNotEqual(ws.resolve(), (Path(os.environ.get("AI_WORKSPACE", "."))).resolve())
            (ws / "components").mkdir()
            (ws / "brands" / BRAND / "email-sms").mkdir(parents=True)
            with unittest.mock.patch.dict(os.environ, {"AI_WORKSPACE": str(ws)}):
                importlib.reload(P)
                self.assertEqual(P.WORKSPACE, ws)
                self.assertEqual(P.COMPONENTS, ws / "components")
                self.assertEqual(P.RUNS, ws / "runs" / "marketing-calendar")
                self.assertEqual(P.brand_root(BRAND), ws / "brands" / BRAND)
                self.assertEqual(G.repo_root(), P.WORKSPACE)

    def test_unset_it_is_run_kits_repo(self):
        with unset():
            importlib.reload(P)
            self.assertEqual(P.WORKSPACE, KIT.repo(P.HERE))
            self.assertEqual(P.COMPONENTS, P.WORKSPACE / "components")
            self.assertEqual(P.PLATFORM, P.WORKSPACE / "platform")
            self.assertEqual(P.SYSTEM, P.WORKSPACE / "runs" / "marketing-calendar" / "_system")
            self.assertEqual(P.brand_root(BRAND), P.WORKSPACE / "brands" / BRAND)
            self.assertEqual(P.rel(P.WORKSPACE / "brands" / BRAND), "brands/" + BRAND)
            self.assertEqual(G.repo_root(), P.WORKSPACE)

    def test_no_home_folder_in_the_source(self):
        src = (MACHINE / "paths.py").read_text()
        self.assertNotIn("Path.home()", src)
        self.assertNotIn("_NAMED_DEFAULT", src)
        self.assertNotIn("brand_finder", src)

    def test_the_month_tests_write_nothing_under_the_real_runs(self):
        with unset():
            real = KIT.repo(MACHINE) / "runs" / "marketing-calendar"
            before = listing(real)
            for name in ("test_k2_month_home.py", "test_k2_moments_propose.py"):
                r = subprocess.run([sys.executable, str(MACHINE / name)],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   universal_newlines=True, env=dict(os.environ))
                self.assertEqual(r.returncode, 0, name + "\n" + r.stdout[-2000:])
            self.assertEqual(listing(real), before)


if __name__ == "__main__":
    unittest.main(verbosity=1)
