#!/usr/bin/env python3
"""SI-184 (zero-run styles retired), briefs#6: no style is `live` on zero runs.
Each of the nine that were is deprecated — its prompt in its own folder's
archive/, or left in lab/ when lab holds it — unless code still reads it, in
which case it stays approved and its evidence names the reader.

    /usr/bin/python3 components/briefs/tests/test_damon3_zero_run_styles.py

Offline: reads the real briefs.json and the tree, no key, no network. Loads the
tool by file — image-teardown has its own tools/briefs.py, so a module-name
import could pick up the wrong one.
"""
import contextlib, importlib.util, io, unittest
from argparse import Namespace
from pathlib import Path

COMPONENT = Path(__file__).resolve().parent.parent
TOOL = COMPONENT / "tools" / "briefs.py"

_spec = importlib.util.spec_from_file_location("briefs_register_zero_run", TOOL)
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

# the nine that were state "live" on {"runs": 0} before SI-184 (zero-run styles retired)
NINE = ("video--hook-asset", "static--creator", "carousel--generator", "carousel--creator",
        "email--production", "email--designer",
        "campaign--executor", "calendar--executor", "page--executor")
# read by code, so never deprecated (the card's (a))
KEPT = ("video--hook-asset", "static--creator", "carousel--generator",
        "email--production", "email--designer")
MOVED = {"carousel--creator":
         "tools/image-writing/prompts/stage6-creator-sequence-brief-v1-damon.md"}   # the writing station's since 2026-10-27


class ZeroRunStyles(unittest.TestCase):

    def setUp(self):
        self.reg = B.load()
        self.by = {b["id"]: b for b in self.reg["briefs"]}

    def test_no_entry_is_live_on_zero_runs(self):
        for b in self.reg["briefs"]:
            if b["state"] == "live":
                self.assertGreater((b.get("evidence") or {}).get("runs") or 0, 0, b["id"])

    def test_every_deprecated_prompt_exists_moved_ones_under_archive(self):
        dep = [b for b in self.reg["briefs"] if b["status"] == "deprecated"]
        self.assertTrue(dep)
        for b in dep:
            self.assertTrue((B.WS / b["prompt"]).is_file(), b["prompt"])
            self.assertEqual(b["state"], "parked", b["id"])
            if not b["prompt"].startswith("lab/"):
                self.assertIn("/archive/", b["prompt"], b["id"])

    def test_a_moved_prompt_left_its_old_home(self):
        for sid, old in MOVED.items():
            b = self.by[sid]
            self.assertEqual(b["status"], "deprecated", sid)
            self.assertEqual(b["prompt"], str(Path(old).parent / "archive" / Path(old).name), sid)
            self.assertFalse((B.WS / old).exists(), old)

    def test_lab_prompts_stay_where_lab_keeps_them(self):
        for sid in ("campaign--executor", "calendar--executor", "page--executor"):
            b = self.by[sid]
            self.assertEqual(b["status"], "deprecated", sid)
            self.assertTrue(b["prompt"].startswith("lab/damon/control-room/prompts/brief/"), sid)
            self.assertNotIn("/archive/", b["prompt"], sid)

    def test_email_production_and_designer_are_not_deprecated(self):
        for sid in ("email--production", "email--designer"):
            b = self.by[sid]
            self.assertNotEqual(b["status"], "deprecated", sid)
            self.assertTrue(b["prompt"].endswith(".py"), sid)
            self.assertTrue((B.WS / b["prompt"]).is_file(), b["prompt"])

    def test_a_style_code_still_reads_is_kept_and_names_its_reader(self):
        for sid in KEPT:
            b = self.by[sid]
            self.assertEqual(b["status"], "approved", sid)
            self.assertTrue((b["evidence"].get("reader") or "").strip(), sid)
            self.assertTrue((B.WS / b["prompt"]).is_file(), b["prompt"])

    def test_each_of_the_nine_is_settled(self):
        for sid in NINE:
            b = self.by[sid]
            if sid in KEPT:
                self.assertEqual(b["status"], "approved", sid)
            else:
                self.assertEqual(b["status"], "deprecated", sid)
                self.assertTrue((b["evidence"].get("ruled") or "").strip(), sid)

    def test_the_register_check_passes_on_the_nine(self):
        reg = dict(self.reg, briefs=[self.by[sid] for sid in NINE], retire_candidates=[])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = B.cmd_check(Namespace(), reg)
        self.assertEqual(code, 0, buf.getvalue())


if __name__ == "__main__":
    unittest.main()
