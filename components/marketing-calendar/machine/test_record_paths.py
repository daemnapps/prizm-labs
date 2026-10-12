#!/usr/bin/env python3
"""A calendar-run record names its month the way a person can follow it —
relative to the workspace, never a machine's /Users/... prefix (SI-131
(calendar record paths)). Proven in a made-up workspace: no model, no network,
no real brand.

    /usr/bin/python3 components/marketing-calendar/machine/test_record_paths.py
"""
import os
import sys
import tempfile
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="record-paths-test-"))
WS = TMP / "ws"
WS.mkdir()
(WS / "brands").mkdir(parents=True, exist_ok=True)  # run-kit's repo() honours AI_WORKSPACE only with brands/
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py
# the script's own folder is sys.path[0], and it holds a calendar.py of its own:
# take it off so the stdlib's calendar is the one cached, then put it back
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != MACHINE]
import calendar as _stdlib_calendar      # noqa: E402,F401
import json                              # noqa: E402
import shutil                            # noqa: E402
import unittest                          # noqa: E402
sys.path.insert(0, str(MACHINE))
# the made-up workspace has no components/: borrow this checkout's brandpath
CHECKOUT = next(d for d in MACHINE.parents if (d / ".git").exists())
sys.path.append(str(CHECKOUT / "components" / "brandpath"))

import paths as P                        # noqa: E402
import records as REC                    # noqa: E402


class RecordPaths(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(str(TMP), ignore_errors=True)

    def test_workspace_is_the_temp_tree(self):
        self.assertEqual(P.WORKSPACE.resolve(), WS.resolve())

    def test_run_dir_is_repo_relative(self):
        # the smallest month summarise() reads: a slots.json, nothing else
        d = P.RUNS / "test-brand" / "2026-10"
        d.mkdir(parents=True)
        (d / "slots.json").write_text(json.dumps([
            {"id": "m-test-01", "date": "2026-10-03", "type": "what-went-wrong"}]))
        _, verdict = REC.summarise(d)
        run_dir = verdict["run_dir"]
        self.assertFalse(run_dir.startswith("/"), run_dir)
        self.assertNotIn("/Users/", run_dir)
        self.assertEqual(run_dir, "runs/marketing-calendar/test-brand/2026-10")


if __name__ == "__main__":
    unittest.main()
