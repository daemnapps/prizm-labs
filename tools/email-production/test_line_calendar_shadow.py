#!/usr/bin/env python3
"""LD-19 (calendar shadow fix): the design step no longer hides Python's own
`calendar` module behind marketing-calendar's machine/ (whose planner was
named `calendar` until LD-49 (stdlib-name renames) made it
marketing_calendar.py) — proven offline.

    python3 tools/email-production/test_line_calendar_shadow.py

A child process (sys.executable) runs design/line.py as run_month.py runs it —
`design/line.py <brand> --run <run>` from this folder, as __main__ — with a
brand that has no look, so main() imports `kinds` and `paths` (as it always
does) and then stops at look.load's SystemExit. No key, no network, nothing
written. PIL is stood in only when this interpreter has none (design/engine.py
imports it; nothing here draws). Stdlib only, 3.9.

  a  after `import kinds` and `import paths`, `calendar` is the standard
     library's: sys.modules and a fresh import agree, its file is not under
     components/marketing-calendar, and calendar.timegm answers (google-auth's
     token code calls it)
  b  `kinds` and `paths` are marketing-calendar/machine's own files
  c  line.py pins the stdlib `calendar` before its first path change and puts
     that folder on the END of the path; no other path entry holds a `kinds`
     or `paths` module
  d  with machine/ at sys.path[0] (kinds.py re-inserts it there), a fresh
     path search for `calendar` still finds the standard library's file, not
     one under components/marketing-calendar — machine/ holds no `calendar`
     (LD-49 (stdlib-name renames)); the pin in c stays as belt and braces
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE / "design"
MACHINE = (HERE.parent / "marketing-calendar" / "machine").resolve()

CHILD = r"""
import json, runpy, sys, types
from importlib.machinery import PathFinder
from pathlib import Path

design, machine = sys.argv[1], sys.argv[2]
try:
    import PIL  # noqa: F401
except ImportError:
    PIL = types.ModuleType("PIL")
    for _n in ("Image", "ImageDraw", "ImageFilter"):
        setattr(PIL, _n, types.ModuleType("PIL." + _n))
        sys.modules["PIL." + _n] = getattr(PIL, _n)
    sys.modules["PIL"] = PIL
sys.path[0] = design                                   # as `python3 design/line.py` sets it
sys.argv = ["design/line.py", "zz-no-such-brand", "--run", "zz-no-such-run"]
stopped = None
try:
    runpy.run_path(design + "/line.py", run_name="__main__")
except SystemExit as e:
    stopped = str(e)

import calendar
import importlib
fresh = importlib.import_module("calendar")
kinds, paths = sys.modules.get("kinds"), sys.modules.get("paths")
at = [str(Path(p).resolve()) if p else p for p in sys.path]
ahead = []
for d in sys.path:
    if str(Path(d).resolve()) == machine:
        continue
    for n in ("kinds", "paths"):
        s = PathFinder.find_spec(n, [d])
        if s is not None:
            ahead.append([n, s.origin])
print(json.dumps({
    "stopped": stopped,
    "calendar": getattr(sys.modules["calendar"], "__file__", None),
    "fresh": getattr(fresh, "__file__", None),
    "same": fresh is sys.modules["calendar"] is calendar,
    "timegm": calendar.timegm((1970, 1, 2, 0, 0, 0)) if hasattr(calendar, "timegm") else None,
    "kinds": getattr(kinds, "__file__", None),
    "paths": getattr(paths, "__file__", None),
    "first": at[0],
    "machine_at": [i for i, p in enumerate(at) if p == machine],
    "ahead": ahead,
    "shadow": getattr(PathFinder.find_spec("calendar", [machine]), "origin", None),
    "resolved": getattr(PathFinder.find_spec("calendar", sys.path), "origin", None),
}))
"""


class TestLineCalendarShadow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = subprocess.run([sys.executable, "-c", CHILD, str(DESIGN), str(MACHINE)],
                           cwd=str(HERE), capture_output=True, text=True, timeout=120)
        assert p.returncode == 0, "child failed (%d):\n%s\n%s" % (p.returncode, p.stdout, p.stderr)
        cls.r = json.loads(p.stdout.strip().splitlines()[-1])

    def under_machine(self, f):
        return f is not None and str(Path(f).resolve()).startswith(str(MACHINE))

    def test_main_ran_up_to_the_look(self):
        self.assertIn("zz-no-such-brand has no email look yet", self.r["stopped"] or "")
        self.assertIsNotNone(self.r["kinds"])                            # main() got past `import kinds`
        self.assertIsNotNone(self.r["paths"])                            # and `import paths as CP`

    def test_calendar_is_the_standard_library_after_kinds_and_paths(self):
        for f in (self.r["calendar"], self.r["fresh"]):
            self.assertIsNotNone(f)
            self.assertFalse(self.under_machine(f), f)
            self.assertNotIn("marketing-calendar", str(Path(f).resolve()))
        self.assertTrue(self.r["same"])
        self.assertEqual(self.r["timegm"], 86400)                        # calendar.timegm, the stdlib's

    def test_kinds_and_paths_are_marketing_calendars(self):
        self.assertEqual(Path(self.r["kinds"]).resolve(), MACHINE / "kinds.py")
        self.assertEqual(Path(self.r["paths"]).resolve(), MACHINE / "paths.py")

    def test_line_appends_the_machine_folder_and_nothing_ahead_shadows_kinds_or_paths(self):
        src = (DESIGN / "line.py").read_text()
        self.assertIn('sys.path.append(str(REPO / "components" / "marketing-calendar" / "machine"))', src)
        self.assertNotIn('sys.path.insert(0, str(REPO / "components" / "marketing-calendar" / "machine"))', src)
        head = src.split("sys.path.")[0]                                 # before line.py's first path change
        self.assertRegex(head, r"(?m)^import calendar\b")                # the stdlib pin comes first
        self.assertEqual(self.r["ahead"], [])                            # no other path entry has one
        self.assertGreaterEqual(len(self.r["machine_at"]), 2)            # kinds.py's insert(0) + line.py's append
        self.assertGreater(self.r["machine_at"][-1], 0)

    def test_with_machine_first_calendar_still_resolves_to_the_standard_library(self):
        self.assertEqual(self.r["first"], str(MACHINE))                  # kinds.py:24's insert(0)
        self.assertEqual(self.r["machine_at"][0], 0)
        self.assertIsNone(self.r["shadow"])                              # machine/ holds no `calendar`
        f = self.r["resolved"]                                           # a fresh search, machine/ first
        self.assertIsNotNone(f)
        self.assertFalse(self.under_machine(f), f)
        self.assertNotIn("marketing-calendar", str(Path(f).resolve()))
        self.assertEqual(Path(f).stem, "calendar")                       # the stdlib's own file


if __name__ == "__main__":
    unittest.main(verbosity=2)
