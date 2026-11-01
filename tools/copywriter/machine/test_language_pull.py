#!/usr/bin/env python3
"""The language pull of every copy stage (the owner, 2026-10-27: "awareness levels and verbatims and spice are the
foundation of what we're doing here"). Each stage's query names the avatar AND the ad's awareness level, the hook and
render stages get the spice and the research, and an empty or failed query says so out loud. No model, no network.

    python3 test_language_pull.py
"""
import contextlib
import io
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import copy_writer as C   # noqa: E402
import copy_set as CS     # noqa: E402

RECORD = """**AWARENESS**

- Entry level: `problem-aware`. The opening assumes the viewer already feels this need.
- Exit level: `solution-aware`.
"""


class FakeL:
    def __init__(self, txt="# Customer language — hooks\n- [language_a1] \"a real line\""):
        self.txt, self.calls = txt, []

    def for_stage(self, *a, **kw):
        self.calls.append((a, kw))
        return self.txt


class CopywriterStages(unittest.TestCase):
    def test_entry_level_is_read_off_the_record(self):
        self.assertEqual(C.entry_level(RECORD), "problem-aware")
        self.assertIsNone(C.entry_level("no awareness named here"))
        self.assertIsNone(C.entry_level(None))

    def test_every_stage_pull_passes_the_avatar_and_the_awareness_level(self):
        L = FakeL()
        C.language_for(L, "brand-x", "hooks", "av-1", "lead", "problem-aware", None)
        (args, kw), = L.calls
        self.assertEqual(args[:4], ("brand-x", "hooks", "av-1", "lead"))
        self.assertEqual(kw["awareness"], "problem-aware")
        self.assertEqual(kw["used"], "fresh")

    def test_an_empty_pull_is_said_out_loud_and_in_the_slot(self):
        L = FakeL("(no rows matched — say so rather than inventing one)")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = C.language_for(L, "brand-x", "spice", "av-1", None, "unaware", None)
        self.assertIn("no rows for brand-x/spice", out.getvalue())
        self.assertIn("NO rows", got)
        self.assertIn("never invent", got)

    def test_main_pulls_at_the_run_level_and_hands_spice_and_research_to_hooks_and_render(self):
        src = (HERE / "copy_writer.py").read_text()
        self.assertIn("args.awareness or entry_level(record)", src)
        for stage in ("stage5", "stage8"):
            call = src[src.index(f'run_stage("{stage}"'):]
            call = call[:call.index("save()")]
            self.assertIn('spice_bank=lang("spice")', call, stage)
            self.assertIn("research=research_text", call, stage)
        call = src[src.index('run_stage("stage3"'):]
        self.assertIn("research=research_text", call[:call.index("save()")])
        # the research is pulled before injection, so stage 3 has it
        self.assertLess(src.index("research_text = \"[UNFILLED"), src.index('run_stage("stage3"'))
        self.assertEqual(set(C.RESEARCH_READERS), {"stage3", "stage5", "stage6", "stage7", "stage8"})

    def test_the_live_prompts_bind_the_new_slots(self):
        want = {"stage3": {"research"}, "stage5": {"spice_bank", "research"}, "stage8": {"spice_bank", "research"}}
        for stage, slots in want.items():
            t = C.latest_prompt(stage).read_text()
            for s in slots:
                self.assertIn("{" + s + "}", t, f"{stage} {C.latest_prompt(stage).name}")


class Research(unittest.TestCase):
    def test_the_research_packet_is_asked_at_the_level(self):
        import research as RS
        seen = []
        with mock.patch.object(RS, "inputs", lambda st: seen.append(st) or {"research": "# Research"}):
            RS.text_for(brand="brand-x", avatar="av-1", awareness="solution-aware")
        self.assertEqual(seen[0]["audience"]["_awareness"], "solution-aware")
        self.assertIn("awareness=args.awareness or entry_level(record)", (HERE / "copy_writer.py").read_text())


class CopySet(unittest.TestCase):
    def run_with(self, returncode=0, stdout="- [language_a1] \"line\"\n", stderr=""):
        calls = []

        def fake(cmd, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)
        return calls, fake

    def test_the_query_passes_the_awareness_level(self):
        calls, fake = self.run_with()
        with mock.patch.object(CS.subprocess, "run", fake):
            rows = CS.language_rows("brand-x", "av-1", None, awareness="unaware")
        self.assertTrue(rows)
        for cmd in calls:
            self.assertEqual(cmd[cmd.index("--awareness") + 1], "unaware")
            self.assertEqual(cmd[cmd.index("--avatar") + 1], "av-1")

    def test_a_failed_query_is_a_problem_not_zero_rows_quietly(self):
        calls, fake = self.run_with(returncode=2, stdout="", stderr="Traceback\nKeyError: boom")
        problems, err = [], io.StringIO()
        with mock.patch.object(CS.subprocess, "run", fake), contextlib.redirect_stderr(err):
            rows = CS.language_rows("brand-x", "av-1", None, awareness="unaware", problems=problems)
        self.assertEqual(rows, [])
        self.assertEqual(len(problems), len(CS.STAGES))
        self.assertIn("KeyError: boom", problems[0])
        self.assertIn("language query failed", err.getvalue())

    def test_an_empty_query_is_a_problem(self):
        calls, fake = self.run_with(stdout="(no rows matched — say so rather than inventing one)\n")
        problems = []
        with mock.patch.object(CS.subprocess, "run", fake), contextlib.redirect_stderr(io.StringIO()):
            CS.language_rows("brand-x", "av-1", None, problems=problems)
        self.assertTrue(all("no rows" in p for p in problems))

    def test_spice_is_queried_at_the_level_and_the_prompt_binds_it(self):
        calls, fake = self.run_with()
        with mock.patch.object(CS.subprocess, "run", fake):
            got = CS.spice_rows("brand-x", "av-1", "problem-aware")
        self.assertIn("language_a1", got)
        cmd, = calls
        self.assertEqual(cmd[cmd.index("--stage") + 1], "spice")
        self.assertEqual(cmd[cmd.index("--awareness") + 1], "problem-aware")
        self.assertIn("{spice_bank}", CS.PROMPT.read_text().split("\n---\n", 1)[1])
        self.assertTrue(re.search(r"copy-set-v\d+-damon\.md$", CS.PROMPT.name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
