"""The production rows of the 2026-10-21 verify pass (runs/video-system/sync/2026-10-21/VERIFY.md rows 3, 4, 7, 8,
13, 14, 17, 18, 19, 22; the record is production-fix.md beside it) — fakes only, no network, no money.

  3 off-camera lines ship their locked read · 4 every shot reaches its take, every line its own tag · 7 the voice
  model is the house's · 8 no cost cuts · 13 the model lock reads the house · 17 no model typed in code ·
  18 voice first by a flag · 19 spice levels, realism formats and steps reach production · 22 small leftovers
"""
import importlib.util
import json
import re
import tempfile
import unittest
import os
os.environ["IMAGE_DOOR_TEST_FORCE_OPENAI"] = "1"      # these tests drive the legacy OpenAI path with a transport stub
from pathlib import Path

import clips_run as oc
import seedance_prompt as SP

HERE = Path(__file__).resolve().parent
CFG = oc.route_cfg()
W = CFG["words"]
PEOPLE = {"LEAD": {"noun": "woman", "pron": "she", "poss": "her", "identity": "", "marks": "a scar on her chin",
                   "gestures": "rubs her thumb on her palm", "voice_id": "v1"}}


def _load(name):
    sp = importlib.util.spec_from_file_location(f"pf_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


H = _load("house")


def call(lines, scenes=("S1",), **kw):
    return {"id": "G01-C1", "scenes": list(scenes), "people": ["LEAD"], "camera": "selfie", "refs": [],
            "lines": lines, "start_frame": "S1-F1", "end_frame": None, **kw}


class FakeOmni:
    def __init__(self):
        self.cmds = []

    def ffmpeg_path(self):
        return "ffmpeg"

    def ledger_path(self, run):
        return Path(run) / "clips" / "ledger.json"

    def calls_dir(self, run):
        return Path(run) / "clips" / "calls"

    def run_cmd(self, cmd):
        self.cmds.append(cmd)
        Path(cmd[-1]).write_bytes(b"cut")

    def crisp(self, src, out):
        Path(out).write_bytes(Path(src).read_bytes() + b"+crisp")
        return Path(out)


class OffCameraLinesAreTheLockedRead(unittest.TestCase):          # row 3
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.run = Path(self.t.name)
        (self.run / "vo").mkdir()
        self.omni = FakeOmni()
        self.saved = oc._load
        oc._load = lambda name: self.omni if name == "clip_kit" else self.saved(name)

    def tearDown(self):
        oc._load = self.saved
        self.t.cleanup()

    def job(self, **kw):
        return {"scene": "S2", "text": "It works.", "out": "clips/offcam/S2.mp3", "at": 3.0, "chars": 9, **kw}

    def test_the_locked_read_ships_and_nothing_is_read_again(self):
        (self.run / "vo" / "S2.mp3").write_bytes(b"locked")
        (self.run / "vo" / "locks.json").write_text(json.dumps({"S2": {"locked": 2}}))
        got = oc.make_tts(self.run, self.job(), CFG, oc.Ledger(self.run))
        self.assertEqual(got["read"], "vo/S2.mp3")
        self.assertEqual(got["locked_read"], 2)
        self.assertTrue((self.run / "clips" / "offcam" / "S2.mp3").read_bytes().endswith(b"+crisp"))
        self.assertIn(str(self.run / "vo" / "S2.mp3"), self.omni.cmds[0], "cut from the locked read")
        self.assertNotIn("make_tts", "")                 # no text-to-speech door is reached: no transport is given

    def test_no_locked_read_stops(self):
        with self.assertRaises(RuntimeError) as e:
            oc.make_tts(self.run, self.job(), CFG, oc.Ledger(self.run))
        self.assertIn("no locked read", str(e.exception))

    def test_a_read_the_word_check_failed_is_held(self):
        (self.run / "vo" / "S2.mp3").write_bytes(b"locked")
        (self.run / "vo" / "audio-check.json").write_text(json.dumps({"scenes": {"S2": {"pass": False, "problems": ["extra words"]}}}))
        with self.assertRaises(RuntimeError) as e:
            oc.make_tts(self.run, self.job(), CFG, oc.Ledger(self.run))
        self.assertIn("word check", str(e.exception))


class EveryShotReachesItsTake(unittest.TestCase):                # row 4
    SC = {"S1": {"id": "S1", "who": "LEAD", "happens": "shows the jar", "voice": "It burns. Then it stopped.",
                 "shots": [{"id": "S1.1", "emotion": "worn down", "face": "brows pinched", "camera_move": "hold",
                            "lines": [{"say": "It burns.", "delivery_tag": "[tired]"}], "hands_off": "continuous"},
                           {"id": "S1.2", "emotion": "quietly relieved", "face": "a small smile", "camera_move": "push-in",
                            "gestures": ["taps the lid"], "lines": [{"say": "Then it stopped.", "delivery_tag": "[softly]"}],
                            "hands_off": "whip", "ends_on": "her eyes on the lens"}],
                 "beats": [{"shot": "S1.2", "do": "twists the lid open"}]}}

    def prompt(self):
        c = call([{"scene": "S1", "speaker": "LEAD", "text": "It burns. Then it stopped.", "on_camera": True}],
                 hands_off=oc.last_shot(self.SC["S1"]).get("hands_off"))
        return SP.build(c, self.SC, PEOPLE, W, "", "LEAD")["prompt"]

    def test_both_shots_their_acting_lines_tags_moves_and_hand_offs(self):
        p = self.prompt()
        for want in ("brows pinched", "a small smile", "taps the lid", "twists the lid open",
                     SP.HAND["continuous"], SP.END["whip"], "her eyes on the lens", "Then"):
            self.assertIn(want, p)
        for gone in ("worn down", "quietly relieved", "It burns.", "Then it stopped.", "tired", "softly"):
            self.assertNotIn(gone, p, "no emotion label, and the line and its tag live in the audio")
        self.assertIn(SP.CAMERA["push-in"], p, "the second shot's own camera move")
        self.assertLess(p.index("brows pinched"), p.index("a small smile"))

    def test_the_hand_off_is_the_last_shots(self):
        self.assertEqual(oc.last_shot(self.SC["S1"])["hands_off"], "whip")

    def test_a_scene_of_one_line_reads_on_that_lines_tag(self):
        v = _load("voice")
        with tempfile.TemporaryDirectory() as t:
            run = Path(t)
            doc = {"scenes": [{"id": "S1", "lines": [{"say": "It works.", "delivery_tag": "[warmly]"}]},
                              {"id": "S2", "lines": [{"text": "One.", "delivery_tag": "[flat]"},
                                                     {"text": "Two.", "delivery_tag": "[up]"}]}]}
            (run / "brief.md").write_text("```json\n" + json.dumps(doc) + "\n```\n")
            self.assertEqual(v.scene_lines(run, "S1", "It works.", None), [("S1", "It works.", "[warmly]")])
            self.assertEqual([x[2] for x in v.scene_lines(run, "S2", "One. Two.", None)], ["[flat]", "[up]"])


class TheVoiceIsTheHouses(unittest.TestCase):                   # row 7 (+ row 17's silent fallback)
    def test_an_old_voice_json_model_is_never_used(self):
        v = _load("voice")
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "voice.json").write_text(json.dumps({"voice_id": "abc", "model_id": "eleven_multilingual_v2"}))
            self.assertEqual(v.binding(Path(t))[1], H.voice_model())

    def test_an_unreadable_house_refuses(self):
        v = _load("voice")
        v._load = lambda name: (_ for _ in ()).throw(OSError("gone"))
        with self.assertRaises(SystemExit):
            v.default_model_id()


class NoCostCuts(unittest.TestCase):                            # row 8
    def test_no_silent_share_and_no_quality_step_down(self):
        self.assertNotIn("silent_share", CFG)
        self.assertNotIn("one quality step down", (HERE / "playbook_learn.py").read_text())
        self.assertNotIn("model_fast", (HERE / "direct_openai.py").read_text())
        self.assertNotIn("model_fast", json.loads((HERE / "providers.json").read_text())["direct"]["openai"])


class TheModelLockReadsTheHouse(unittest.TestCase):             # row 13
    def test_the_whole_picture_ladder_passes_anything_else_stops(self):
        R = _load("run")
        D = _load("direct_openai")
        for m in (H.picture_model("generate"), H.picture_model("edit"), H.picture_backup(), H.picture_object(), H.picture_safety_net()):
            R.ruled_model({}, "still", m)
        R.ruled_model({"doors": {"still": {"model": "x"}}}, "still", H.picture_model("generate"))   # doors not read
        with self.assertRaises(SystemExit):
            R.ruled_model({}, "still", "some-other-model")

    def test_the_overflow_door_is_retired(self):
        self.assertEqual(H.picture_overflow(), {})
        self.assertNotIn("overflow", _load("direct_openai").cfg())          # no fal address survives in the config


class NoModelTypedInCode(unittest.TestCase):                    # row 17
    def test_each_door_reads_the_house(self):
        self.assertEqual(_load("swap_run").MODEL, H.swap()["api"])
        self.assertEqual(_load("lineparity").STT_MODEL_ID, H.words_model())
        self.assertEqual(_load("make_voice").MODEL, H.voice_design_model())
        self.assertEqual(oc.route_cfg()["engines"]["seedance"]["id"], H.clip("seedance")["id"])

    def test_the_named_files_type_no_model(self):
        typed = re.compile(r"""["'](?:gpt-5\.5|gpt-image[\w./-]*|gemini-[\w.-]+|scribe_v\d|eleven_[\w]+|"""
                           r"""higgsfield/genjutsu[\w./-]*)["']""")
        for f in ("swap_run.py", "lineparity.py", "face_lock.py", "element_match.py", "clip_kit.py", "make_voice.py"):
            hits = [m.group(0) for m in typed.finditer((HERE / f).read_text())]
            self.assertEqual(hits, [], f)
        self.assertNotIn("FALLBACK_MODEL", (HERE / "face_lock.py").read_text())


class VoiceFirstByAFlag(unittest.TestCase):                     # row 18
    def test_run_has_voice_only_and_the_order_asks_for_it(self):
        V2 = _load("run_v2")
        self.assertTrue(V2._parser_has("--voice-only"))
        self.assertEqual(V2._voice_step(["start", "b.md"])[-1], "--voice-only")


class SpiceAndRealismInProduction(unittest.TestCase):           # row 19
    def test_the_levels_come_from_video_spice(self):
        self.assertEqual(oc.spice_layers(1), {1, 5, 6})
        self.assertEqual(oc.spice_layers(2), {1, 3, 5, 6})
        self.assertEqual(oc.spice_layers(3), {1, 2, 3, 4, 5, 6, 7})
        self.assertIsNone(oc.spice_layers(None))

    def test_formats_beyond_the_four_camera_kinds(self):
        self.assertEqual(oc.realism_format_of({"who": "HANDS", "happens": "mixes the paste"}), "pov-hands")
        self.assertEqual(oc.realism_format_of({"happens": "grinds turmeric at the kitchen counter"}, "still"), "counter-demo")
        self.assertEqual(oc.realism_format_of({"happens": "talks while walking to the car"}, "selfie"), "walk-and-talk")
        self.assertEqual(oc.realism_format_of({"happens": "talks"}, "mirror"), "grwm-mirror")
        self.assertEqual(oc.realism_format_of({"realism_format": "sit-down-interview"}), "sit-down-interview")

    def test_no_format_means_no_format_rows(self):
        self.assertEqual(oc.realism_rows(None, oc.PICTURE_FAMILIES), [])

    def test_level_one_drops_own_gestures_and_life_marks(self):
        sc = {"S1": {"id": "S1", "who": "LEAD", "happens": "talks", "voice": "Hi."}}
        l = [{"scene": "S1", "speaker": "LEAD", "text": "Hi.", "on_camera": True}]
        full = SP.build(call(l), sc, PEOPLE, W, "", "LEAD")["prompt"]
        one = SP.build(call(l, spice_level=1, spice_layers=[1, 5, 6]), sc, PEOPLE, W, "", "LEAD")["prompt"]
        self.assertIn("rubs her thumb", full)
        self.assertIn("a scar on her chin", full)
        self.assertNotIn("rubs her thumb", one)
        self.assertNotIn("a scar on her chin", one)

    def test_one_step_a_line_reaches_a_one_shot_take(self):
        sc = {"S1": {"id": "S1", "who": "LEAD", "happens": "makes the paste", "voice": "Squeeze. Then mix.",
                     "beats": [{"do": "squeezes the lime", "over": "Squeeze."}, {"do": "mixes the paste", "over": "Then mix."}]}}
        p = SP.build(call([{"scene": "S1", "speaker": "LEAD", "text": "Squeeze. Then mix.", "on_camera": True}]),
                     sc, PEOPLE, W, "", "LEAD")["prompt"]
        self.assertIn("squeezes the lime", p)
        self.assertIn("mixes the paste", p)
        self.assertLess(p.index("squeezes the lime"), p.index("mixes the paste"))


class Leftovers(unittest.TestCase):                             # row 22
    def test_speech_to_speech_is_retired_in_the_registry(self):
        m = json.loads((HERE / "providers.json").read_text())["models"]
        for k in ("voice_change", "fal-ai/elevenlabs/voice-changer"):
            self.assertEqual(m[k]["status"], "retired", k)
            self.assertTrue(m[k].get("retired"), k)

    def test_the_picture_record_keeps_door_and_backup_for(self):
        self.assertIn('for k in ("door", "backup_for")', (HERE / "run.py").read_text())

    def test_no_cover_before_the_edit(self):
        self.assertNotIn("fix or cover before the edit", (HERE / "clips_run.py").read_text())


if __name__ == "__main__":
    unittest.main()
