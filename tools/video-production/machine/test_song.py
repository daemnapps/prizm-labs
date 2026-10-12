#!/usr/bin/env python3
"""python3 machine/test_song.py — the song chain (song.py), with fakes. No network."""
from __future__ import annotations

import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures" / "song" / "nova-song-plan.json"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"t_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


song = _load("song")
# song.py's OWN defaults are what this file tests — no playbook layer on top. The
# playbook layer (formats/playbooks/song-ad.json) is asserted in test_playbook.py.
os.environ["VIDEO_PLAYBOOKS_DIR"] = tempfile.mkdtemp(prefix="no-playbooks-")
PLAN = json.loads(FIX.read_text())
LINES = [l for s in PLAN["song"]["sections"] for l in s["lines"]]


def plan():
    return copy.deepcopy(PLAN)


def words_of(lines, t0=0.0):
    """A scribe-shaped transcript: every word with a time."""
    out, t = [], t0
    for ln in lines:
        for w in ln.split():
            out.append({"text": w, "start": round(t, 2), "end": round(t + 0.3, 2), "type": "word"})
            t += 0.4
    return {"text": " ".join(lines), "words": out}


class Music:
    """The music door, faked: counts calls, hands back a short real mp3."""
    def __init__(self, audio: bytes):
        self.audio, self.calls = audio, []

    def __call__(self, method, url, headers, body):
        self.calls.append(json.loads(body))
        return 200, {}, self.audio


class Ear:
    """Speech-to-text, faked: one transcript per call, in order."""
    def __init__(self, *transcripts):
        self.transcripts, self.calls = list(transcripts), 0

    def __call__(self, method, url, headers, body):
        t = self.transcripts[min(self.calls, len(self.transcripts) - 1)]
        self.calls += 1
        return 200, {}, json.dumps(t).encode()


def never(*a, **k):
    raise AssertionError("the network was called on a dry run")


class Base(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="vm-song-"))
        tone = self.run / "tone.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
                        str(tone)], check=True)
        self.audio = tone.read_bytes()

    def tearDown(self):
        shutil.rmtree(self.run, ignore_errors=True)

    def quiet(self, fn, *a, **k):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return fn(*a, **k)


class PlanBuilding(Base):
    def test_the_plan_is_built_mechanically_from_the_block_and_the_row(self):
        req = song.build_request(PLAN["song"], PLAN)
        chunks = req["body"]["composition_plan"]["chunks"]
        self.assertEqual([c["duration_ms"] for c in chunks], [4000, 12000, 14000])
        self.assertEqual(chunks[0]["text"], "")
        self.assertEqual(chunks[1]["text"], "\n".join(PLAN["song"]["sections"][1]["lines"]))
        row = song.load_styles()["neo-soul-90s"]
        self.assertEqual(chunks[2]["positive_styles"],
                         row["positive_styles"] + ["88 BPM", row["section_styles"]["chorus"]])
        self.assertEqual(chunks[2]["negative_styles"], row["negative_styles"])
        door = song.door()
        self.assertEqual(req["body"]["model_id"], door["model_id"])
        self.assertEqual(req["body"]["seed"], door["seed"])
        self.assertTrue(req["url"].startswith(door["url"]))

    def test_the_same_block_prints_the_same_request(self):
        self.assertEqual(song.build_request(PLAN["song"], PLAN), song.build_request(plan()["song"], plan()))

    def test_a_bpm_in_the_brief_replaces_the_rows(self):
        p = plan(); p["song"]["bpm"] = 92
        chunks = song.build_request(p["song"], p)["body"]["composition_plan"]["chunks"]
        self.assertIn("92 BPM", chunks[1]["positive_styles"])
        self.assertNotIn("88 BPM", chunks[1]["positive_styles"])

    def test_a_section_outside_the_doors_limits_is_refused(self):
        p = plan(); p["song"]["sections"][0]["seconds"] = 1
        with self.assertRaisesRegex(SystemExit, "section 1 .*1 s"):
            song.build_request(p["song"], p)


class TheWords(Base):
    def test_a_lyric_that_is_not_in_the_script_is_refused_by_name(self):
        p = plan(); p["song"]["sections"][2]["lines"][1] = "The third opinion is a miracle cream"
        with self.assertRaisesRegex(SystemExit, "The third opinion is a miracle cream.*not a line of the script"):
            song.build_request(p["song"], p)

    def test_a_script_line_nobody_sings_is_refused_by_name(self):
        p = plan(); p["song"]["sections"][1]["lines"].pop()
        with self.assertRaisesRegex(SystemExit, "scene S2's line 'He said taking the top layer off is a cop out'"):
            song.build_request(p["song"], p)

    def test_punctuation_and_case_do_not_make_a_new_line(self):
        p = plan(); p["song"]["sections"][2]["lines"][2] = "twenty-nine dollars that's the proof"
        song.build_request(p["song"], p)

    def test_no_script_at_all_is_refused(self):
        p = plan()
        for s in p["scenes"]:
            s["lyrics"] = []
        with self.assertRaisesRegex(SystemExit, "no script to sing"):
            song.build_request(p["song"], p)


class TheStyle(Base):
    def test_an_unknown_style_is_refused_naming_the_rows(self):
        p = plan(); p["song"]["style_id"] = "sad-jazz"
        with self.assertRaisesRegex(SystemExit, "'sad-jazz' is not a row.*neo-soul-90s"):
            song.build_request(p["song"], p)

    def test_a_draft_style_is_refused(self):
        p = plan(); p["song"]["style_id"] = "acoustic-folk-warm"
        with self.assertRaisesRegex(SystemExit, "draft row, not approved"):
            song.build_request(p["song"], p)

    def test_a_vocal_the_row_does_not_sing_is_refused(self):
        p = plan(); p["song"]["vocal"] = "male"
        with self.assertRaisesRegex(SystemExit, "male vocal but style 'neo-soul-90s'"):
            song.build_request(p["song"], p)

    def test_a_section_the_row_has_no_line_for_is_refused(self):
        p = plan(); p["song"]["sections"][2]["name"] = "bridge"
        with self.assertRaisesRegex(SystemExit, "no line for a 'bridge' section"):
            song.build_request(p["song"], p)

    def test_no_style_at_all_is_refused(self):
        p = plan(); del p["song"]["style_id"]
        with self.assertRaisesRegex(SystemExit, "no style_id"):
            song.build_request(p["song"], p)


class TheGate(Base):
    def test_every_line_heard_in_order_passes_with_times(self):
        g = song.gate(PLAN["song"], words_of(LINES, t0=4.0))
        self.assertTrue(g["pass"], g["problems"])
        self.assertEqual(len(g["lines"]), 6)
        self.assertEqual(g["lines"][0]["start"], 4.0)
        self.assertEqual(g["sections"][1]["start"], 4.0)
        self.assertIsNone(g["sections"][0]["start"])   # the intro has no words
        self.assertEqual([(x["planned_start"], x["planned_end"]) for x in g["sections"]],
                         [(0.0, 4.0), (4.0, 16.0), (16.0, 30.0)])

    def test_a_missing_line_fails_naming_it(self):
        heard = LINES[:4] + LINES[5:]
        g = song.gate(PLAN["song"], words_of(heard))
        self.assertFalse(g["pass"])
        self.assertIn("The third opinion's in a tube", g["problems"][0])

    def test_a_line_sung_out_of_order_fails(self):
        heard = [LINES[1], LINES[0]] + LINES[2:]
        self.assertFalse(song.gate(PLAN["song"], words_of(heard))["pass"])

    def test_a_song_that_stops_before_the_last_line_finishes_fails(self):
        heard = LINES[:5] + ["Twenty-nine dollars"]
        g = song.gate(PLAN["song"], words_of(heard))
        self.assertFalse(g["pass"])
        self.assertTrue(any("does not finish" in p or "not heard" in p for p in g["problems"]))

    def test_sound_tags_are_not_words(self):
        t = words_of(LINES)
        t["words"].insert(0, {"text": "[soft humming]", "start": 0.0, "end": 3.0, "type": "audio_event"})
        t["words"].append({"text": "[outro music]", "start": 30.0, "end": 31.0, "type": "word"})
        t["text"] = "[soft humming] " + t["text"] + " [outro music]"
        self.assertTrue(song.gate(PLAN["song"], t)["pass"])

    def test_figures_written_as_digits_count_as_the_words(self):
        heard = LINES[:3] + ["I'm 64 and still not lasering my legs", LINES[4], "$29, that's the proof"]
        self.assertTrue(song.gate(PLAN["song"], words_of(heard))["pass"])


class TheFlow(unittest.TestCase):
    """the owner, 2026-10-10: awkward space in the song loses the viewer — every take is listened to."""

    def test_a_tight_take_flows(self):
        self.assertTrue(song.flow(words_of(LINES, t0=0.3))["pass"])

    def test_a_late_first_word_fails(self):
        f = song.flow(words_of(LINES, t0=12.0))
        self.assertFalse(f["pass"]); self.assertIn("first word", " ".join(f["problems"]))

    def test_a_long_gap_mid_song_fails(self):
        t = words_of(LINES, t0=0.2)
        for w in t["words"][10:]:
            w["start"] += 9.0; w["end"] += 9.0
        f = song.flow(t)
        self.assertFalse(f["pass"]); self.assertEqual(len(f["gaps"]), 1)

    def test_sections_fit_their_lines(self):
        row = {"bpm": 88, "section_styles": {}}
        self.assertAlmostEqual(song.fit_seconds(["a"] * 8, 88, row), round((8 * 4 + 1) * 60 / 88, 1))
        self.assertGreaterEqual(song.fit_seconds(["a"], 200, row), 3.0)

    def test_a_dead_air_take_is_remade_tighter(self):
        row = {"bpm": 88}
        tight = song.shrink_block({"bpm": 88, "sections": [{"name": "verse", "seconds": 40, "lines": ["a"] * 8}]}, row, 0.85)
        self.assertEqual(tight["sections"][0]["seconds"], 34.0)


class TheRun(Base):
    def test_dry_run_writes_the_request_and_spends_nothing(self):
        rec = self.quiet(song.make, self.run, plan=plan(), dry_run=True, transport=never, stt_transport=never)
        self.assertTrue(rec["pass"])
        req = json.loads((self.run / "song" / "request.json").read_text())
        self.assertEqual(req, song.build_request(PLAN["song"], PLAN))
        self.assertFalse((self.run / "song" / "song.mp3").exists())
        self.assertFalse((self.run / "ledger.json").exists())

    def test_a_passing_song_is_saved_timed_and_levelled_on_a_copy(self):
        # the first word on the punch, inside a second (the flow rule, 2026-10-10)
        music, ear = Music(self.audio), Ear(words_of(LINES, t0=0.5))
        rec = self.quiet(song.make, self.run, plan=plan(), transport=music, stt_transport=ear, key="k")
        self.assertTrue(rec["pass"])
        self.assertEqual(len(music.calls), 1)
        sd = self.run / "song"
        self.assertEqual((sd / "song.mp3").read_bytes(), self.audio)       # the original, untouched
        self.assertTrue((sd / "song-14lufs.mp3").exists())
        timing = json.loads((sd / "timing.json").read_text())
        self.assertEqual(timing["lines"][0]["start"], 0.5)
        self.assertEqual(json.loads((self.run / "verdicts.json").read_text())["SONG"]["song"]["verdict"], "PASS")

    def test_a_failing_song_is_remade_once_with_the_next_seed_then_passes(self):
        music = Music(self.audio)
        ear = Ear(words_of(LINES[:4]), words_of(LINES))
        rec = self.quiet(song.make, self.run, plan=plan(), transport=music, stt_transport=ear, key="k")
        self.assertTrue(rec["pass"])
        self.assertEqual([c["seed"] for c in music.calls], [1, 2])
        self.assertEqual(music.calls[0]["composition_plan"], music.calls[1]["composition_plan"])
        self.assertTrue((self.run / "song" / "versions" / "song-v1.mp3").exists())

    def test_failing_twice_stops_naming_the_missing_line(self):
        music = Music(self.audio)
        ear = Ear(words_of(LINES[:4]))
        rec = self.quiet(song.make, self.run, plan=plan(), transport=music, stt_transport=ear, key="k")
        self.assertFalse(rec["pass"])
        self.assertEqual(len(music.calls), 2)
        self.assertIn("The third opinion's in a tube", rec["problems"][0])
        self.assertFalse((self.run / "song" / "song-14lufs.mp3").exists())

    def test_a_refused_block_calls_nothing(self):
        p = plan(); p["song"]["sections"][1]["lines"][0] = "an invented line"
        with self.assertRaises(SystemExit):
            self.quiet(song.make, self.run, plan=p, transport=never, stt_transport=never, key="k")


class TheStart(Base):
    """run.py start: a sung brief's song is printed by song.py, before any picture."""

    def start(self, source: Path, *extra):
        run = _load("run")
        a = run.build_parser().parse_args(
            ["start", str(source), "--brand", "_fixture", "--format", "fixture-format", "--label", "s1",
             "--bank", str(HERE / "fixtures" / "bank.json"), "--runs-root", str(self.run),
             "--cast-root", str(HERE / "fixtures" / "cast-root"), *extra])
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run.cmd_start(a, song_transport=never, song_stt_transport=never)
        return code, out.getvalue(), err.getvalue(), self.run / "video-production" / "_fixture" / "s1"

    def test_dry_run_start_writes_the_song_request_and_calls_nothing(self):
        code, out, err, r = self.start(FIX, "--dry-run")
        self.assertIn("song (dry run)", out)
        self.assertEqual(json.loads((r / "song" / "request.json").read_text()),
                         song.build_request(PLAN["song"], PLAN))

    def test_start_refuses_an_invented_lyric_before_anything_is_made(self):
        p = plan(); p["song"]["sections"][1]["lines"][0] = "an invented line"
        src = self.run / "bad.json"; src.write_text(json.dumps(p))
        code, out, err, r = self.start(src, "--dry-run")
        self.assertEqual(code, 2)
        self.assertIn("'an invented line', which is not a line of the script", err)
        self.assertFalse((r / "song" / "request.json").exists())
        self.assertEqual(list((r / "batches").glob("*.json")), [])


class TheDoor(unittest.TestCase):
    def test_the_song_door_is_elevenlabs_music_v2_5_with_lyria_kept(self):
        reg = song.platform.registry()
        d = reg["doors"]["audio"]
        self.assertEqual((d["primary"], d["model"]), ("direct:elevenlabs", "music_v2_5"))
        self.assertTrue(any("lyria" in a for a in d["alternates"]))
        self.assertIn("Eleven Labs won for me for sure", reg["_house"]["ruling_2026_09_23_song"])
        self.assertIn("music_v2_5", reg["models"])
        self.assertEqual(song.door_closed(), "")


if __name__ == "__main__":
    unittest.main()
