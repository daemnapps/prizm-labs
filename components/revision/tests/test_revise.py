#!/usr/bin/env python3
"""python3 -m unittest components/revision/tests/test_revise.py — the revision step on a made-up brand, with a fake
model. No network, no model call, nothing outside a temp folder."""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "revise.py"

HOOKS = "# Hooks\n\n| # | Hook |\n|---|---|\n| H1 | You won't believe this. |\n| H2 | Stop scrolling. |\n"
SCRIPT = "# Script\n\n| # | Time | Line |\n|---|---|---|\n| 1 | 0:00 | Stop scrolling. |\n| 2 | 0:03 | Here is why. |\n"
BRIEF = "# Brief\n\n## Lines\n\n| 1 | Stop scrolling. |\n| 2 | Here is why. |\n\n## Cast\n\nOne man, 30s, kitchen.\n"


def load(ws):
    os.environ["PRIZM_WS"] = str(ws)
    os.environ["AI_WORKSPACE"] = str(ws)                       # the learnings store, in the temp folder
    os.environ["OWNER_QUOTES"] = str(ws / "his-node" / "quotes.jsonl")
    spec = importlib.util.spec_from_file_location("revise_under_test", SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.stage_check = lambda where: {"ran": True, "exit": 0, "tail": ["fake stage check"]}
    return m


def fake(route, edit):
    """A stand-in model: the first call answers the route pass, the second the edit pass. Keeps the prompts."""
    seen = []

    def run(prompt):
        seen.append(prompt)
        ans = route if len(seen) == 1 else edit
        return json.dumps(ans), {"model": "claude-sonnet-5-5", "cost_usd": 0.01, "tokens_in": 10, "tokens_out": 5,
                                 "seconds": 1}
    run.seen = seen
    return run


class Revise(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        (self.ws / "brands").mkdir()          # the learnings store honours AI_WORKSPACE only where brands/ exists
        (self.ws / "components").mkdir()
        run = self.ws / "runs/video-teardown/_work/brand_a-swipe-1"
        (run / "stages").mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"brand": "brand_a", "label": "brand_a-swipe-1"}))
        (run / "stages/4b-hooks.md").write_text(HOOKS)
        (run / "stages/4cde-placement-expansion-close.md").write_text(SCRIPT)
        (run / "stages/5-brief.md").write_text(BRIEF)
        self.run = run
        em = self.ws / "runs/email-production/brand_a/brand_a-mail-1"
        em.mkdir(parents=True)
        (em / "run.json").write_text("{}")
        (em / "stage5--subjects.md").write_text("# Subjects\n\n1. Last chance\n")
        self.R = load(self.ws)
        self.tella = self.ws / "tella/rec-1"
        (self.tella / "frames").mkdir(parents=True)
        (self.tella / "transcript.md").write_text("[0:04] on the stop scrolling one, the hook is soft, make it hit\n")
        (self.tella / "frames/t0005.jpg").write_bytes(b"jpg")
        self.add({"id": "n1", "item": "t:brand_a-swipe-1", "text": 'change the first line to "Put the phone down."'})
        self.add({"id": "n2", "item": "w:brand_a-swipe-1", "text": "",
                  "tella": {"title": "my review", "folder": str(self.tella), "words": 14}})

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)
        for k in ("PRIZM_WS", "AI_WORKSPACE", "OWNER_QUOTES"):
            os.environ.pop(k, None)

    def add(self, n):
        f = self.ws / "runs/studio-feedback/brand_a/feedback.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "a") as out:
            out.write(json.dumps(dict({"brand": "brand_a", "kind": "video", "title": "Swipe 1", "state": "new",
                                       "at": "2026-11-28T10:00:00"}, **n)) + "\n")

    def exact(self):
        route = {"read": "new first line", "asks": [{"quote": 'change the first line to "Put the phone down."',
                 "kind": "exact", "owner": "script", "files": ["stages/4cde-placement-expansion-close.md",
                                                                "stages/5-brief.md"],
                 "exact_words": ["Put the phone down."]}], "needs_paid": [], "not_here": []}
        edit = {"edits": [
            {"file": "stages/4cde-placement-expansion-close.md", "find": "| 1 | 0:00 | Stop scrolling. |",
             "replace": "| 1 | 0:00 | Put the phone down. |", "why": "his first line", "quote": "Put the phone down."},
            {"file": "stages/5-brief.md", "find": "| 1 | Stop scrolling. |", "replace": "| 1 | Put the phone down. |",
             "why": "the brief carries it", "quote": "Put the phone down."}], "not_done": [],
            "summary": "The first line is now his."}
        return fake(route, edit)

    def test_the_learnings_store_is_the_temp_folder(self):
        self.assertEqual(Path(self.R._ln().paths.repo()), self.ws)       # never the real store

    def test_typed_exact_words_make_a_proposal_and_leave_live_files(self):
        rec = self.R.revise("brand_a", "n1", runner=self.exact(), say=lambda *_: None)
        self.assertEqual(rec["state"], "proposed")
        self.assertEqual(sorted(rec["files"]), ["stages/4cde-placement-expansion-close.md", "stages/5-brief.md"])
        self.assertTrue(rec["checks"]["passed"])
        self.assertIn("script check", rec["checks"]["note"])                              # said, never a hold
        self.assertEqual(self.run.joinpath("stages/5-brief.md").read_text(), BRIEF)       # live untouched
        out = self.ws / "runs/revision/brand_a" / rec["id"]
        for f in ("record.json", "why.md", "diff.patch", "route.prompt.md", "edit.reply.md",
                  "before/stages/5-brief.md", "after/stages/5-brief.md"):
            self.assertTrue((out / f).is_file(), f)
        self.assertNotIn("4b-hooks.md", (out / "diff.patch").read_text())                 # only what he asked
        n = self.R.note("brand_a", "n1")
        self.assertEqual(n["state"], "revised")
        self.assertEqual(n["revision_view"]["changes"][0]["after"], "| 1 | 0:00 | Put the phone down. |")
        self.assertIn("Put the phone down.", (out / "why.md").read_text())

    def test_use_puts_it_in_place_and_keeps_the_old(self):
        rec = self.R.revise("brand_a", "n1", runner=self.exact(), say=lambda *_: None)
        self.R.use("brand_a", "n1", say=lambda *_: None)
        self.assertIn("Put the phone down.", self.run.joinpath("stages/5-brief.md").read_text())
        old = self.run / "stages" / ("5-brief.before-rev-%s.md" % rec["id"])
        self.assertEqual(old.read_text(), BRIEF)
        n = self.R.note("brand_a", "n1")
        self.assertEqual(n["state"], "in use")
        self.assertTrue(n["revision_view"]["in_use"])

    def lesson_run(self, said, brand_only=False):
        route = {"read": "one scene", "asks": [{"quote": "this is the last time I'm gonna say this, combine the hook shots",
                 "kind": "general", "owner": "brief", "files": ["stages/5-brief.md"],
                 "lesson": "Put every hook shot in one scene, with the shots listed inside it", "lesson_kind": "do",
                 "rule_said": said, "brand_only": brand_only}]}
        edit = {"edits": [{"file": "stages/5-brief.md", "find": "| 1 | Stop scrolling. |\n| 2 | Here is why. |",
                           "replace": "| 1 | Stop scrolling. Here is why. |", "why": "one scene", "quote": "combine"}]}
        return fake(route, edit)

    def learned(self, name):
        f = self.ws / "runs/learnings" / name
        return [json.loads(l) for l in f.read_text().splitlines()] if f.is_file() else []

    def test_a_kept_revision_teaches_the_chain(self):
        self.R.revise("brand_a", "n1", runner=self.lesson_run(said=True), say=lambda *_: None)
        self.assertEqual(self.learned("candidates.jsonl"), [])         # a proposal teaches nothing yet
        rec = self.R.use("brand_a", "n1", say=lambda *_: None)
        rules = [r["rule"] for r in self.learned("_all.jsonl")]
        self.assertIn("Put every hook shot in one scene, with the shots listed inside it", rules)   # said: in force
        cands = self.learned("candidates.jsonl")
        self.assertTrue(any(c["from"] == "kept edit" and c["stations"] == ["writing"] for c in cands))
        self.assertTrue(any(x["promoted"] for x in rec["learned"]))
        self.assertIn("Put every hook shot", " ".join(self.R.note("brand_a", "n1")["revision_view"]["learned"]["in_force"]))
        for f in (self.ws / "runs/learnings").glob("*.jsonl"):
            self.assertNotIn("last time I'm gonna say", f.read_text())    # his words stay in his own node
        self.assertIn("last time I'm gonna say", (self.ws / "his-node/quotes.jsonl").read_text())
        LN = self.R._ln()
        self.assertIn("Put every hook shot", LN.handed(None, "writing", "brand_a"))   # the next writing run gets it

    def test_a_lesson_not_said_as_a_rule_waits_for_a_second_run(self):
        self.R.revise("brand_a", "n1", runner=self.lesson_run(said=False, brand_only=True), say=lambda *_: None)
        self.R.use("brand_a", "n1", say=lambda *_: None)
        self.assertEqual(self.learned("brand_a.jsonl"), [])
        self.assertTrue(any(c["brand"] == "brand_a" for c in self.learned("candidates.jsonl")))

    def test_use_refuses_when_the_live_file_moved_on(self):
        self.R.revise("brand_a", "n1", runner=self.exact(), say=lambda *_: None)
        self.run.joinpath("stages/5-brief.md").write_text(BRIEF + "\nchanged by the chain\n")
        with self.assertRaises(ValueError):
            self.R.use("brand_a", "n1", say=lambda *_: None)

    def test_dry_run_keeps_the_note_new(self):
        self.R.revise("brand_a", "n1", dry=True, runner=self.exact(), say=lambda *_: None)
        self.assertEqual(self.R.note("brand_a", "n1")["state"], "new")

    def test_tella_note_reads_the_recording_and_a_general_ask_changes_only_its_owner(self):
        route = {"read": "harder hook", "asks": [{"quote": "the hook is soft, make it hit", "kind": "general",
                 "shift": "a harder hook", "owner": "hook", "files": ["stages/4b-hooks.md"]}]}
        edit = {"edits": [{"file": "stages/4b-hooks.md", "find": "| H2 | Stop scrolling. |",
                           "replace": "| H2 | Stop. Your skin is lying to you. |", "why": "harder", "quote": "make it hit"}],
                "summary": "H2 hits harder."}
        run = fake(route, edit)
        rec = self.R.revise("brand_a", "n2", runner=run, say=lambda *_: None)
        self.assertIn("the hook is soft", run.seen[0])                 # his recording is in the prompt
        self.assertIn("t0005.jpg", run.seen[0])                        # and his stills are offered
        self.assertEqual(rec["files"], ["stages/4b-hooks.md"])
        self.assertEqual(rec["tella"]["title"], "my review")
        self.assertNotIn("folder", rec["tella"])                       # no machine path in the record

    def test_missing_exact_words_hold_the_revision(self):
        route = {"read": "x", "asks": [{"quote": "q", "kind": "exact", "owner": "hook", "files": ["stages/4b-hooks.md"],
                                        "exact_words": ["Put the phone down."]}]}
        edit = {"edits": [{"file": "stages/4b-hooks.md", "find": "| H1 | You won't believe this. |",
                           "replace": "| H1 | Put the phone, down |", "why": "x", "quote": "q"}]}
        rec = self.R.revise("brand_a", "n1", runner=fake(route, edit), say=lambda *_: None)
        self.assertTrue(rec["checks"]["passed"])                       # punctuation aside, the words are in
        edit["edits"][0]["replace"] = "| H1 | Put it down |"
        rec = self.R.revise("brand_a", "n1", runner=fake(route, edit), say=lambda *_: None)
        self.assertFalse(rec["checks"]["passed"])

    def test_an_edit_that_does_not_match_once_is_refused(self):
        route = {"read": "x", "asks": [{"quote": "q", "kind": "general", "owner": "brief", "files": ["stages/5-brief.md"]}]}
        edit = {"edits": [{"file": "stages/5-brief.md", "find": "Stop scrolling", "replace": "Halt", "why": "x"},
                          {"file": "stages/9-nope.md", "find": "a", "replace": "b"}]}
        self.run.joinpath("stages/5-brief.md").write_text(BRIEF + "Stop scrolling\n")
        rec = self.R.revise("brand_a", "n1", runner=fake(route, edit), say=lambda *_: None)
        self.assertEqual(rec["state"], "nothing to change")
        self.assertEqual(len(rec["refused"]), 2)

    def test_a_data_block_keeps_its_shape(self):
        data = '```json\n[\n {"scene": "S1", "text": "a"},\n {"scene": "S2", "text": "a"}\n]\n```\n'
        texts = {"f.md": "# Brief\n\n" + data}
        drop = {"file": "f.md", "find": ' {"scene": "S1", "text": "a"},\n', "replace": ""}
        value = {"file": "f.md", "find": '{"scene": "S2", "text": "a"}', "replace": '{"scene": "S2", "text": "b"}'}
        new, kept, refused = self.R.apply_edits(texts, [drop, value])
        self.assertEqual(len(refused), 1)                              # deleting an entry: refused
        self.assertIn('"text": "b"', new["f.md"])                      # one value: allowed
        self.assertIn('"scene": "S1"', new["f.md"])

    def test_email_piece_and_not_here(self):
        self.add({"id": "n3", "item": "e:brand_a-mail-1", "text": "subject: Your last shot"})
        route = {"read": "new subject", "asks": [{"quote": "Your last shot", "kind": "exact", "owner": "subject",
                 "files": ["stage5--subjects.md"], "exact_words": ["Your last shot"]}],
                 "not_here": [{"quote": "fix the board", "why": "not this email"}]}
        edit = {"edits": [{"file": "stage5--subjects.md", "find": "1. Last chance", "replace": "1. Your last shot",
                           "why": "his subject", "quote": "Your last shot"}]}
        rec = self.R.revise("brand_a", "n3", runner=fake(route, edit), say=lambda *_: None)
        self.assertEqual(rec["piece_type"], "email")
        self.assertTrue(rec["checks"]["passed"])
        self.assertIn("fix the board", " ".join(self.R.note("brand_a", "n3")["revision_view"]["not_done"]))

    def test_a_failed_model_call_puts_the_note_back(self):
        def boom(prompt):
            raise RuntimeError("the model call failed")
        with self.assertRaises(RuntimeError):
            self.R.revise("brand_a", "n1", runner=boom, say=lambda *_: None)
        self.assertEqual(self.R.note("brand_a", "n1")["state"], "new")

    def test_model_is_first_drafts_tier_never_top(self):
        self.assertEqual(self.R.model(), "claude-sonnet-5-5")
        os.environ["REVISION_MODEL"] = "claude-opus-5-5"
        try:
            with self.assertRaises(SystemExit):
                self.R.model()
        finally:
            os.environ.pop("REVISION_MODEL")

    def test_nightly_with_no_new_notes_skips(self):
        for nid in ("n1", "n2"):
            self.R.mark("brand_a", nid, state="revised")
        self.assertEqual(self.R.main(["run", "--brand", "brand_a", "--all-new"]), 3)

    def test_mark_keeps_a_note_added_meanwhile(self):
        self.add({"id": "n9", "item": "t:brand_a-swipe-1", "text": "later"})
        self.R.mark("brand_a", "n1", state="revised")
        ids = [n["id"] for n in self.R.notes("brand_a")]
        self.assertEqual(ids, ["n1", "n2", "n9"])

    def test_ask_writes_a_result_and_a_meter_line(self):
        fk = self.exact()
        self.R.revise.__globals__["call_model"] = lambda p, m, d=None, r=None: fk(p)
        out = self.ws / "result.md"
        saved = sys.stdout
        try:
            import io
            sys.stdout = buf = io.StringIO()
            self.R.main(["ask", "--brand", "brand_a", "--input", "n1", "--out", str(out)])
        finally:
            sys.stdout = saved
        self.assertIn("first line", out.read_text())
        ev = json.loads(buf.getvalue().strip().splitlines()[-1])
        self.assertEqual(ev["type"], "result")
        self.assertIn("claude-sonnet-5-5", ev["modelUsage"])


if __name__ == "__main__":
    unittest.main()
