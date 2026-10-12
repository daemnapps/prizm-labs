#!/usr/bin/env python3
"""`moments_apply.py --write` proposes and never writes brands/ (SI-22
(calendar months home), K2 (brands write wall)): the new moments file, its
report and a one-screen PROPOSAL.md land under runs/marketing-calendar/<brand>/
moments-<YYYY-MM-DD>/, and the brand tree is byte-for-byte what it was. No
model, no network, no real brand — the record-reading is stubbed.

    /usr/bin/python3 components/marketing-calendar/machine/test_k2_moments_propose.py
"""
import os
import sys
import tempfile
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="k2-moments-propose-test-"))
WS = TMP / "ws"
WS.mkdir()
(WS / "brands").mkdir(parents=True, exist_ok=True)  # run-kit's repo() honours AI_WORKSPACE only with brands/
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py
# the script's own folder is sys.path[0], and it holds a calendar.py of its own:
# take it off so the stdlib's calendar is the one cached, then put it back
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != MACHINE]
import calendar as _stdlib_calendar      # noqa: E402,F401
import hashlib                           # noqa: E402
import io                                # noqa: E402
import json                              # noqa: E402
import shutil                            # noqa: E402
import unittest                          # noqa: E402
from contextlib import redirect_stdout   # noqa: E402
sys.path.insert(0, str(MACHINE))
# the made-up workspace has no components/: borrow this checkout's brandpath
CHECKOUT = next(d for d in MACHINE.parents if (d / ".git").exists())
sys.path.append(str(CHECKOUT / "components" / "brandpath"))

import brandpath as BP                   # noqa: E402
import moments_apply as MA               # noqa: E402
import paths as P                        # noqa: E402

BRAND, TODAY = "testbrand", "2026-10-07"
DOC = {"avatars": {"all": {"moments": []}}}


def snapshot(root):
    return sorted((str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest())
                  for p in Path(root).rglob("*") if p.is_file())


class Propose(unittest.TestCase):
    def setUp(self):
        self.target = Path(BP.brand_path(BRAND, "strategy", "moments.json", root=WS / "brands"))
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(json.dumps(DOC, indent=1) + "\n")
        self.keep = MA.plan, MA.report, MA.apply, sys.argv
        MA.plan = lambda brand: (DOC, [{"key": "a-moment"}], [], [], [], [], 1.0, TODAY)
        MA.report = lambda *a, **k: "report\n"
        MA.apply = lambda *a, **k: {"avatars": {}}

    def tearDown(self):
        MA.plan, MA.report, MA.apply, sys.argv = self.keep

    def test_write_proposes_and_brands_is_untouched(self):
        before = snapshot(WS / "brands")
        sys.argv = ["moments_apply.py", "--brand", BRAND, "--write"]
        said = io.StringIO()
        with redirect_stdout(said):
            MA.main()
        self.assertEqual(snapshot(WS / "brands"), before)
        self.assertEqual([p for p in (WS / "brands").rglob("*") if ".before-" in p.name], [])

        out = P.RUNS / BRAND / ("moments-" + TODAY)
        for name in ("moments.json", "report.md", "run.json", "PROPOSAL.md"):
            self.assertTrue((out / name).is_file(), name)
        self.assertIn(P.rel(out / "PROPOSAL.md"), said.getvalue())

        rel_target = str(self.target.relative_to(WS))
        note = (out / "PROPOSAL.md").read_text()
        self.assertIn(rel_target, note)
        self.assertTrue(rel_target.startswith("brands/" + BRAND + "/"), rel_target)
        sha = hashlib.sha256(self.target.read_bytes()).hexdigest()
        self.assertIn(sha, note)
        self.assertIn("STALE", note)
        self.assertIn("commit as yourself", note)

        run = json.loads((out / "run.json").read_text())
        self.assertEqual((run["machine"], run["brand"], run["target"]),
                         ("marketing-calendar", BRAND, rel_target))
        self.assertEqual(run["files"], {"moments.json": sha})
        self.assertEqual(json.loads((out / "moments.json").read_text()), {"avatars": {}})
        self.assertEqual((out / "report.md").read_text(), "report\n")


if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        shutil.rmtree(str(TMP), ignore_errors=True)
