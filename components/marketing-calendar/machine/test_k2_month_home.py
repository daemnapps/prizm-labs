#!/usr/bin/env python3
"""A planned month has one home — runs/marketing-calendar/<brand>/<YYYY-MM>/ at
the workspace root — and every reader finds it there (SI-22 (calendar months
home), K2 (brands write wall)). Proven in a made-up workspace: no model, no
network, no real brand.

    /usr/bin/python3 components/marketing-calendar/machine/test_k2_month_home.py
"""
import os
import sys
import tempfile
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="k2-month-home-test-"))
WS = TMP / "ws"
WS.mkdir()
(WS / "brands").mkdir(parents=True, exist_ok=True)  # run-kit's repo() honours AI_WORKSPACE only with brands/
os.environ["AI_WORKSPACE"] = str(WS)            # before anything imports paths.py
# the script's own folder is sys.path[0], and it holds a calendar.py of its own:
# take it off so the stdlib's calendar is the one cached, then put it back
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != MACHINE]
import calendar as _stdlib_calendar      # noqa: E402,F401
import io                                # noqa: E402
import json                              # noqa: E402
import shutil                            # noqa: E402
import unittest                          # noqa: E402
from contextlib import redirect_stdout   # noqa: E402
sys.path.insert(0, str(MACHINE))
# the made-up workspace has no components/: borrow this checkout's brandpath
CHECKOUT = next(d for d in MACHINE.parents if (d / ".git").exists())
sys.path.append(str(CHECKOUT / "components" / "brandpath"))

import paths as P                        # noqa: E402
import dryrun as DRY                     # noqa: E402
import gates as G                        # noqa: E402
import month as MONTH                    # noqa: E402
import records as REC                    # noqa: E402
import serve as SERVE                    # noqa: E402


def seed(brand, month, mtime):
    d = P.RUNS / brand / month
    d.mkdir(parents=True)
    (d / "run.json").write_text(json.dumps({"brand": brand, "month": month}))
    (d / "slots.json").write_text(json.dumps([
        {"id": f"m-{brand}-01", "date": f"{month}-03", "type": "what-went-wrong",
         "segment": "Core | Churned", "category": "Promotional"}]))
    os.utime(str(d / "slots.json"), (mtime, mtime))
    return d


def tree(root):
    return sorted((str(p.relative_to(root)), p.stat().st_mtime_ns)
                  for p in Path(root).rglob("*"))


class Home(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = seed("a", "2026-10", 1_000_000_000)
        cls.b = seed("b", "2026-11", 1_100_000_000)
        (P.RUNS / "_system").mkdir()
        (P.RUNS / "a" / "moments-2026-10-07").mkdir()
        (P.RUNS / "a" / "moments-2026-10-07" / "slots.json").write_text("[]")

    def test_the_shelf_is_at_the_workspace_root(self):
        self.assertEqual(P.RUNS, WS / "runs" / "marketing-calendar")
        self.assertEqual(P.SYSTEM, P.RUNS / "_system")
        self.assertEqual(P.month_dir("Test Brand", "2026-11"), P.RUNS / "test-brand" / "2026-11")

    def test_the_dry_run_names_brand_then_month(self):
        self.assertEqual(DRY.where_it_would_land(TMP, "2026-11", "test-brand"),
                         TMP / "test-brand" / "2026-11")

    def test_months_are_exactly_the_two(self):
        self.assertEqual(P.months(), [self.a, self.b])

    def test_the_front_page_covers_both_and_lives_in_system(self):
        out = MONTH.build(quiet=True)
        self.assertEqual(out, P.SYSTEM / "calendar.html")
        page = out.read_text()
        self.assertIn("m-a-01", page)
        self.assertIn("m-b-01", page)

    def test_serve_opens_the_newest(self):
        self.assertEqual(SERVE.newest_run(), self.b)

    def test_a_month_at_home_is_not_filed_again(self):
        before = tree(WS)
        self.assertIsNone(G.file_after_run(self.a))
        self.assertEqual(tree(WS), before)
        said = io.StringIO()
        with redirect_stdout(said):
            self.assertEqual(G.main([]), 0)
        self.assertEqual(said.getvalue().count("already home"), 3, said.getvalue())  # two months + the total
        self.assertEqual(tree(WS), before)

    def test_records_all_finds_both(self):
        seen = []
        keep_file, keep_argv = REC.file_record, sys.argv
        REC.file_record = lambda d, *a, **k: seen.append(Path(d))
        sys.argv = ["records.py", "--all"]
        try:
            REC.main()
        finally:
            REC.file_record, sys.argv = keep_file, keep_argv
        self.assertEqual(seen, [self.a, self.b])


if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        shutil.rmtree(str(TMP), ignore_errors=True)
