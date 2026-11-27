"""The micro-drama workflow: the named format resolves to the dialogue line (not the wordless short movie) and lists its
stations and gates in order, for any micro drama. A series is planned ahead, outside the workflow; its continuity tool
(drama_series.py) holds a following part written off the last part's script or on a new matrix row."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import drama_series as DS  # noqa: E402
import drama_start as DST  # noqa: E402
import workflow as W  # noqa: E402
import workflow_catalog as C  # noqa: E402

ORDER = ["swipe", "brief", "pack", "price", "go-check",
         "sheets", "sheets-check", "script-plan", "setups", "setups-check", "clips", "takes", "takes-check",
         "edit", "meta"]


class Resolves(unittest.TestCase):
    def test_micro_drama_is_its_own_declared_family(self):
        r = C.resolve("micro-drama", W.WS, "ai")
        self.assertEqual(r["family"], "micro-drama")
        self.assertEqual(r["coverage"], "declared")
        self.assertFalse(r["selection_required"])
        self.assertEqual([s["id"] for s in r["workflow"]["steps"]], ORDER)
        self.assertEqual(C.validate(r["workflow"]), [])

    def test_owner_gates_and_paid_stations(self):
        steps = {s["id"]: s for s in C.resolve("micro-drama", W.WS)["workflow"]["steps"]}
        # autonomous: the quote is the only stop; every other call goes through the decision layer
        self.assertEqual([s for s in steps.values() if s.get("gate") or s.get("stops_for")], [steps["price"]])
        self.assertFalse(any(s["executor"] == "review" for s in steps.values()))
        self.assertIn("--autonomous", steps["brief"]["does"])
        self.assertIn("drama_lane.py decide", steps["takes"]["does"])
        self.assertIn("both", steps["price"]["does"])
        self.assertTrue(steps["sheets"]["paid"] and steps["clips"]["paid"])
        for check in ("go-check", "sheets-check", "setups-check", "takes-check"):
            self.assertEqual(steps[check]["executor"], "command")
            self.assertIn("drama_lane.py check", steps[check]["run"])
        self.assertIn("hf_route.py pack", steps["pack"]["run"])
        self.assertTrue(steps["pack"]["done_when"].endswith("drama-ads-{pack_label}/pack.json"))
        self.assertIn("brief_check", steps["brief"])
        self.assertNotIn("series", steps)                     # a series is planned ahead, never a station of every film

    def test_the_clip_model_is_one_setting(self):
        pb = W.PB.playbook_for("micro-drama")
        self.assertEqual(pb["clip_models"]["default"], "seedance-2.5")
        self.assertEqual(set(pb["clip_models"]["models"]), {"seedance-2.5", "wan-3.0"})
        self.assertEqual(pb["workflow"]["settings"]["clip_model"]["default"], "seedance-2.5")
        self.assertEqual(pb["clip_models"]["models"]["wan-3.0"]["lane"], "option")

    def test_dry_run_spends_nothing_and_stops_at_the_first_open_station(self):
        with patch("subprocess.run", side_effect=AssertionError("a dry run ran a process")):
            import workflow_runner as R
            code = R.main(["run", "micro-drama", "--brand", "fixture", "--label", "no-such-run", "--dry-run",
                           "--set", "intake=x", "--set", "teardown=x"])
        self.assertEqual(code, 2)
        self.assertFalse((W.WS / "runs/video-production/fixture/workflow-no-such-run").exists())


class Start(unittest.TestCase):
    def test_both_starts_are_one_station(self):
        swipe = C.resolve("micro-drama", W.WS)["workflow"]["steps"][0]
        self.assertEqual(swipe["inputs"], ["source", "teardown", "source_record"])
        for words in ("WITH A SWIPE", "WITHOUT A SWIPE", "drama_start.py preset", "scratch.py"):
            self.assertIn(words, swipe["does"])

    def test_no_swipe_picks_a_live_action_drama_preset_and_rotates(self):
        with patch.object(DST, "used", lambda brand, avatar: []):
            first = DST.preset("b", "a", "problem-aware")
        SP = DST._presets()
        p = SP.get(first["id"])
        self.assertEqual(p["format"]["script_format"], "micro-drama")
        self.assertEqual(p["format"]["style"], "cinematic-live")
        with patch.object(DST, "used", lambda brand, avatar: [first["id"]]):
            self.assertNotEqual(DST.preset("b", "a", "problem-aware")["id"], first["id"])


class Series(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.ws = Path(self.t.name)
        self.p = patch.object(DS, "WS", self.ws)
        self.p.start()
        self.prev = self.ws / "runs/video-production/b/workflow-part1"
        self.cur = self.ws / "runs/video-production/b/workflow-part2"
        self.prev.mkdir(parents=True)
        self.cur.mkdir(parents=True)
        (self.prev / "continuity.json").write_text(json.dumps({"part": 1, "matrix_cell": {"batch": "B", "row": "r3"}}))
        cut = self.ws / "runs/cut.mp4"
        cut.write_bytes(b"cut")
        (self.cur / "previous-part-on-screen.md").write_text("Shot 1 ... The product never appears on screen.")
        on = "runs/video-production/b/workflow-part2/previous-part-on-screen.md"
        (self.cur / "story.md").write_text("Built from: %s\nThe story." % on)
        self.series = self.cur / "series.json"
        self.doc = {"series": "s", "part": 2,
                    "previous": {"workflow": "runs/video-production/b/workflow-part1",
                                 "cut": {"path": "runs/cut.mp4", "sha256": hashlib.sha256(b"cut").hexdigest()}},
                    "on_screen": on, "story": "runs/video-production/b/workflow-part2/story.md",
                    "pin": {"batch": "B", "row": "r3"}}
        self.series.write_text(json.dumps(self.doc))

    def tearDown(self):
        self.p.stop()
        self.t.cleanup()

    def writing_run(self, row, story_text):
        run = self.ws / "runs/video-teardown/_work/part2"
        run.mkdir(parents=True, exist_ok=True)
        (run / "matrix-cell.json").write_text(json.dumps({"batch": "B", "row": row}))
        (run / "run.json").write_text(json.dumps({"story": {"sha": hashlib.sha256(story_text.encode()).hexdigest()[:16]}}))
        return run

    def test_part1_passes_on_its_slug(self):
        self.series.write_text(json.dumps({"series": "s", "part": 1}))
        self.assertEqual(DS.check(self.series), [])

    def test_part2_passes_when_built_from_the_cut(self):
        self.assertEqual(DS.check(self.series), [])

    def test_part2_held_without_the_on_screen_read_or_story_source(self):
        (self.cur / "story.md").write_text("Written from part 1's script.\n")
        (self.cur / "previous-part-on-screen.md").unlink()
        bad = " ".join(DS.check(self.series))
        self.assertIn("on-screen read", bad)

    def test_part2_held_on_a_pin_that_is_not_part1s_row(self):
        self.doc["pin"] = {"batch": "B", "row": "r9"}
        self.series.write_text(json.dumps(self.doc))
        self.assertTrue(any("not part 1's row" in b for b in DS.check(self.series)))

    def test_a_changed_cut_is_held(self):
        (self.ws / "runs/cut.mp4").write_bytes(b"another cut")
        self.assertTrue(any("changed" in b for b in DS.check(self.series)))

    def test_written_holds_a_new_row_and_a_foreign_story(self):
        run = self.writing_run("r7", "some other story")
        bad, _rec = DS.written(self.series, str(run))
        text = " ".join(bad)
        self.assertIn("not the pinned", text)
        self.assertIn("locked story", text)

    def test_written_records_the_row_for_the_next_part(self):
        run = self.writing_run("r3", (self.cur / "story.md").read_text())
        bad, rec = DS.written(self.series, str(run))
        self.assertEqual(bad, [])
        self.assertEqual(rec["matrix_cell"], {"batch": "B", "row": "r3"})
        self.assertEqual(rec["part"], 2)


if __name__ == "__main__":
    unittest.main()
