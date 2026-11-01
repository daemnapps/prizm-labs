#!/usr/bin/env python3
"""SI-72 (briefs status words): every style carries a rule-6 `status` beside an
activity-only `state`, and the gates that dropped `retired` drop `deprecated`.

    /usr/bin/python3 components/briefs/tests/test_status.py

No key, no network. Loads the tool by file — image-teardown has its own
tools/briefs.py, so a module-name import could pick up the wrong one.
"""
import contextlib, importlib.util, io, subprocess, sys, tempfile, unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

COMPONENT = Path(__file__).resolve().parent.parent
TOOL = COMPONENT / "tools" / "briefs.py"

_spec = importlib.util.spec_from_file_location("briefs_register", TOOL)
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def row(id_, status, state, prompt="p/one.md"):
    return {"id": id_, "record": "a record", "asset": "video", "actor": "creator",
            "prompt": prompt, "writes": "brief.md", "status": status, "state": state,
            "evidence": {"runs": 1, "last": "2026-10-01"}}


REG3 = {
    "_naming": "brief--<asset>--<actor>.md",
    "briefs": [
        row("a--one", "approved", "live"),
        row("b--two", "draft", "parked"),
        row("c--three", "deprecated", "parked"),
    ],
}

NO_FILTER = Namespace(asset=None, actor=None, record=None)


def run(fn, a, reg):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(a, reg)
    return code, buf.getvalue()


class StatusWords(unittest.TestCase):

    def test_every_entry_carries_rule6_status_and_activity_state(self):
        self.assertEqual(B.STATUSES, ("draft", "approved", "deprecated"))
        self.assertEqual(B.STATES, ("live", "parked"))
        reg = B.load()
        self.assertTrue(reg["briefs"])
        for b in reg["briefs"]:
            self.assertIn(b.get("status"), B.STATUSES, b["id"])
            self.assertIn(b.get("state"), B.STATES, b["id"])

    def test_find_and_records_drop_deprecated_as_they_dropped_retired(self):
        for fn in (B.cmd_find, B.cmd_records):
            code, out = run(fn, NO_FILTER, REG3)
            self.assertEqual(code or 0, 0, fn.__name__)
            self.assertIn("a--one", out, fn.__name__)
            self.assertIn("b--two", out, fn.__name__)
            self.assertNotIn("c--three", out, fn.__name__)

    def test_list_groups_live_parked_deprecated(self):
        _, out = run(B.cmd_list, NO_FILTER, REG3)
        live = out.index("LIVE — 1")
        parked = out.index("PARKED — 1")
        deprecated = out.index("DEPRECATED — 1")
        self.assertLess(live, parked)
        self.assertLess(parked, deprecated)
        self.assertGreater(out.index("c--three"), deprecated)

    def test_check_flags_a_word_off_the_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "p").mkdir()
            (ws / "p" / "one.md").write_text("x")
            (ws / "p" / "four.md").write_text("x")
            reg = {"_naming": "n", "briefs": [
                row("a--one", "approved", "live", "p/one.md"),
                row("d--four", "live", "live", "p/four.md"),
            ]}
            with mock.patch.object(B, "WS", ws):
                code, out = run(B.cmd_check, NO_FILTER, reg)
        self.assertEqual(code, 1)
        self.assertIn("BAD WORD d--four", out)
        self.assertNotIn("BAD WORD a--one", out)

    def test_the_real_list_runs(self):
        p = subprocess.run([sys.executable, str(TOOL), "list"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("styles · naming", p.stdout)
        self.assertNotIn("RETIRED", p.stdout)


if __name__ == "__main__":
    unittest.main()
