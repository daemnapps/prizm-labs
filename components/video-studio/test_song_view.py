"""A sung ad on the pages (owner, 17 Nov 2026): the song card reads the brief's song block and song.py's clock, scenes
land on their time on the song, and the Studio's Next step runs Make the song in Suno, Check the song, Cut to the song
in that order. A spoken ad gets none of it."""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import song_view as SV  # noqa: E402
import video_studio as VS  # noqa: E402

LINE_A = "You can turn away, but I will never hide my face."
LINE_B = "Lift your head high and stand in the light again."
SUNG = {"brand": "brand-x", "song": {"style_id": "a-style", "vocal": "female", "bpm": 120, "sections": [
    {"name": "verse", "scene": "S1", "seconds": 8, "lines": [LINE_A]},
    {"name": "chorus", "scene": "S3", "seconds": 10, "lines": [LINE_B]},
    {"name": "chorus 2", "scene": "S5", "seconds": 10, "lines": [LINE_B]},
    {"name": "outro", "scene": "S6", "seconds": 4, "lines": []}]},
    "scenes": [{"id": "S1", "lyrics": [LINE_A]}, {"id": "S2"}, {"id": "S3", "lyrics": [LINE_B]}, {"id": "S4"},
               {"id": "S5", "lyrics": [LINE_B]}, {"id": "S6"}, {"id": "S7"}]}
TIMING = {"sections": [{"section": 1, "name": "verse", "start": 0.3, "end": 6.0},
                       {"section": 2, "name": "chorus", "start": 9.0, "end": 17.0},
                       {"section": 3, "name": "chorus 2", "start": 20.0, "end": 28.0},
                       {"section": 4, "name": "outro", "start": None, "end": None}],
          "lines": [{"section": 1, "line": LINE_A, "start": 0.3, "end": 6.0},
                    {"section": 2, "line": LINE_B, "start": 9.0, "end": 17.0},
                    {"section": 3, "line": LINE_B, "start": 20.0, "end": 28.0}]}


def write(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data if isinstance(data, str) else json.dumps(data))
    return p


class SongCard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.run = self.tmp / "run"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def made(self, passed=True):
        write(self.run / "song" / "song.mp3", "mp3")
        write(self.run / "song" / "timing.json", TIMING)
        write(self.run / "song" / "song.json", {"pass": passed, "problems": [] if passed else ["section 2: a line is not heard"]})

    def test_spoken_brief_is_not_a_song(self):
        self.assertEqual(SV.view({"song": None, "scenes": [{"id": "S1"}]}), {"sung": False})
        self.assertEqual(SV.view({"scenes": []}), {"sung": False})
        self.assertEqual(SV.scene_times(["S1"], {"sung": False}), {"S1": None})

    def test_section_names_fall_into_their_family(self):
        self.assertEqual([SV.kind(n) for n in ("chorus 2", "final hook", "the turn", "pre-chorus", "verse 3", "outro", "punch")],
                         ["chorus", "chorus", "bridge", "pre", "verse", "outro", "intro"])

    def test_before_the_song_the_plan_lays_sections_end_to_end(self):
        v = SV.view(SUNG, self.run)
        self.assertTrue(v["sung"])
        self.assertFalse(v["song"]["made"])
        self.assertEqual([(s["start"], s["end"], s["timed"]) for s in v["sections"]],
                         [(0, 8, False), (8, 18, False), (18, 28, False), (28, 32, False)])
        self.assertEqual((v["style_id"], v["bpm"], v["vocal"], v["seconds"]), ("a-style", 120, "female", 32))

    def test_a_made_song_puts_each_section_and_scene_on_its_clock(self):
        self.made()
        v = SV.view(SUNG, self.run)
        self.assertEqual(v["song"], {"made": True, "timed": True, "heard": True, "problems": [], "file": "song/song.mp3"})
        self.assertEqual([(s["start"], s["end"]) for s in v["sections"][:3]], [(0.3, 6.0), (9.0, 17.0), (20.0, 28.0)])
        self.assertFalse(v["sections"][3]["timed"])              # the outro was not heard: planned after the last one
        # the same chorus line sung twice lands on each scene's own section, never both on the first
        self.assertEqual((v["scenes"]["S3"]["start"], v["scenes"]["S5"]["start"]), (9.0, 20.0))
        self.assertEqual(v["scenes"]["S5"]["section"], "chorus 2")
        self.assertNotIn("S2", v["scenes"])

    def test_a_failed_take_says_which_line(self):
        self.made(passed=False)
        v = SV.view(SUNG, self.run)
        self.assertIs(v["song"]["heard"], False)
        self.assertEqual(v["song"]["problems"], ["section 2: a line is not heard"])

    def test_unsung_scenes_share_the_gap_between_sung_ones(self):
        self.made()
        t = SV.scene_times([s["id"] for s in SUNG["scenes"]], SV.view(SUNG, self.run))
        self.assertEqual((t["S2"]["start"], t["S2"]["end"]), (6.0, 9.0))
        self.assertEqual((t["S4"]["start"], t["S4"]["end"]), (17.0, 20.0))
        self.assertTrue(t["S3"]["sung"])
        self.assertFalse(t["S4"]["sung"])
        self.assertIsNone(t["S7"])                               # after the song: keeps its own length

    def test_production_run_is_named_after_the_writing_run(self):
        self.assertEqual(SV.production_run("/w/runs", "brand-x", "run-1"), Path("/w/runs/video-production/brand-x/run-1"))
        self.assertIsNone(SV.production_run("/w/runs", "brand-x", "../escape"))
        self.assertIsNone(SV.production_run("/w/runs", None, "run-1"))

    def test_a_spoken_brief_with_a_song_run_is_a_song_ad(self):
        runs = self.tmp / "runs"
        spoken = {"song": None, "scenes": [{"id": "S1"}]}
        self.assertEqual(SV.view(spoken, SV.production_run(runs, "brand-x", "idea-run")), {"sung": False})
        write(runs / "video-production" / "brand-x" / "idea-run-song" / "plan.json", {"song": SUNG["song"], "scenes": []})
        run = SV.production_run(runs, "brand-x", "idea-run")
        self.assertEqual(run.name, "idea-run-song")
        v = SV.view(spoken, run)
        self.assertTrue(v["sung"])
        self.assertEqual([s["name"] for s in v["sections"]], ["verse", "chorus", "chorus 2", "outro"])
        self.assertEqual(v["scenes"]["S1"]["section"], "verse")   # the song's section names its scene: placed
        fit = dict(SUNG["song"], sections=[{"name": "verse", "seconds": "fit", "lines": ["one two three four five six seven eight nine ten"]}])
        sec = SV.view({"song": fit, "scenes": []})["sections"][0]
        self.assertEqual((sec["start"], sec["end"], sec["timed"]), (0, 5.0, False))   # a "fit" section is planned, never zero

    def test_the_brief_is_read_from_the_writing_runs_stage_five(self):
        wr = self.tmp / "writing" / "run-1"
        write(wr / "run.json", {"brand": "brand-x", "stages": {"stage5": {"out": "stages/5-brief.md"}}})
        write(wr / "stages" / "5-brief.md", "# Brief\n\n```json\n" + json.dumps(SUNG) + "\n```\n")
        self.assertEqual(SV.brief_of(wr)["song"]["style_id"], "a-style")
        write(wr / "stages" / "5-brief.md", "# Brief\n\nno structured block\n")
        self.assertIsNone(SV.brief_of(wr))


class StudioSongSteps(unittest.TestCase):
    """The Studio's Next step on a sung production, with the song door stubbed (song.py is tested in its component)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ws = self.tmp / "ws"
        self.writing = self.ws / "runs" / "video-teardown" / "_work"
        self.briefs = self.tmp / "briefs"
        self.saved = (VS.BRIEFS, VS.ST.WRITING)
        VS.BRIEFS, VS.ST.WRITING = str(self.briefs), self.writing
        wr = self.writing / "run-1"
        write(wr / "run.json", {"brand": "brand-x"})
        write(wr / "stages" / "5-brief.md", "```json\n" + json.dumps(SUNG) + "\n```\n")
        write(self.briefs / "p1" / "brief.json", {"brief": "run-1", "brand": "brand-x", "order": [s["id"] for s in SUNG["scenes"]], "picks": {}})
        spoken = self.writing / "run-2"
        write(spoken / "run.json", {"brand": "brand-x"})
        write(spoken / "stages" / "5-brief.md", "```json\n" + json.dumps({"song": None, "scenes": [{"id": "S1"}]}) + "\n```\n")
        write(self.briefs / "p2" / "brief.json", {"brief": "run-2", "order": ["S1"], "picks": {}})
        self.run = self.ws / "runs" / "video-production" / "brand-x" / "run-1"

    def tearDown(self):
        VS.BRIEFS, VS.ST.WRITING = self.saved
        shutil.rmtree(self.tmp)

    def test_a_spoken_production_has_no_song_stage(self):
        self.assertIsNone(VS.song_due("p2"))
        self.assertEqual(VS.song_state("p2"), {"sung": False})

    def test_a_spoken_brief_turns_sung_when_its_song_run_exists(self):
        write(self.ws / "runs" / "video-production" / "brand-x" / "run-2-song" / "plan.json", {"song": SUNG["song"], "scenes": []})
        write(self.briefs / "p2" / "brief.json", {"brief": "run-2", "brand": "brand-x", "order": ["S1"], "picks": {}})
        self.assertEqual(VS.song_due("p2"), "song")
        self.assertTrue(VS.song_state("p2")["sung"])

    def test_the_song_stages_run_in_order(self):
        self.assertEqual(VS.song_due("p1"), "song")                       # nothing made yet
        self.assertEqual(VS.NEXT_STAGES["song"][0], "Make the song in Suno")
        VS.song_take_add("p1", "my take.mp3", b"audio")
        self.assertEqual(VS.song_due("p1"), "songcheck")                  # a take added: hear it next
        write(self.run / "song" / "song.mp3", "mp3")
        write(self.run / "song" / "timing.json", TIMING)
        time.sleep(0.02)
        write(self.run / "song" / "song.json", {"pass": False, "problems": ["a line"]})
        self.assertEqual(VS.song_due("p1"), "song")                       # heard and failed: make another take
        write(self.run / "song" / "song.json", {"pass": True, "problems": []})
        self.assertEqual(VS.song_due("p1"), "songcut")
        job = {"n": "p1", "stage": "songcut", "steps": [{"id": "cut", "state": "waiting", "said": ""}], "file": str(self.tmp / "job.json")}
        VS._run_song(job)
        cut = json.loads((self.briefs / "p1" / "song-cut.json").read_text())
        self.assertEqual(cut["scenes"]["S3"]["seconds"], 8.0)
        self.assertEqual(cut["song"], "runs/video-production/brand-x/run-1/song/song.mp3")   # repo-relative, never a machine path
        self.assertNotIn("S7", cut["scenes"])
        self.assertIsNone(VS.song_due("p1"))                              # the song is done: production carries on

    def test_a_take_is_only_audio_and_never_overwrites(self):
        with self.assertRaises(ValueError):
            VS.song_take_add("p1", "notes.txt", b"x")
        with self.assertRaises(ValueError):
            VS.song_take_add("p2", "take.mp3", b"x")                      # a spoken ad takes no song
        a = VS.song_take_add("p1", "take.mp3", b"1")["take"]
        b = VS.song_take_add("p1", "take.mp3", b"2")["take"]
        self.assertNotEqual(a, b)
        self.assertEqual((self.run / "song" / "suno-takes" / a).read_bytes(), b"1")

    def test_the_song_state_carries_each_scenes_time(self):
        st = VS.song_state("p1")
        self.assertTrue(st["sung"])
        self.assertEqual(st["takes"], [])
        self.assertIsNone(st["suno"])
        self.assertEqual(st["times"]["S1"]["start"], 0)


if __name__ == "__main__":
    unittest.main()
