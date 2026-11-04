"""The 2026-10-21 production rows (runs/video-system/sync/2026-10-21/CHANGES.md, worker 2) against
VIDEO-RULINGS V1–V20 — fakes only, no network, no money.

  the acting and the camera reach the take (P1–P3, P38) · three takes scored, the best kept, none passing: the best kept and flagged
  (P4, P5, P42, E32) · the voice: per-line reads, the v3 tag sent, three reads one locked (P11–P13) · the locked
  read fitted per part (P16) · 360p and the pick-only upscale (P19, P20) · the Model House read (P23, P25, P26) ·
  the joins (P6, P7, P39) · life marks, realism, swipe-edit prompts (P33, P36, P37) · the order (P9)
"""
import json
import tempfile
import unittest
from pathlib import Path

import clips_run as oc
import seedance_prompt as SP

HERE = Path(__file__).resolve().parent
CFG = oc.route_cfg()
W = CFG["words"]
PEOPLE = {"LEAD": {"noun": "woman", "pron": "she", "poss": "her", "identity": "blue-grey eyes", "marks": "",
                   "gestures": "", "voice_id": "v1"},
          "DOC": {"noun": "doctor", "pron": "he", "poss": "his", "identity": "", "marks": "", "gestures": "",
                  "voice_id": "v2"}}


def prompt_of(c, scenes, people, words=None, style="", lead="LEAD"):
    return SP.build(c, scenes, people, words or W, style, lead)["prompt"]


def call(lines, scenes=("S1",), people=("LEAD",), camera="selfie", **kw):
    return {"id": "G01-C1", "scenes": list(scenes), "people": list(people), "camera": camera, "refs": [],
            "lines": lines, "start_frame": "S1-F1", "end_frame": None, **kw}


class ActingAndCamera(unittest.TestCase):
    def test_face_and_gestures_reach_the_prompt_the_emotion_label_and_the_audio_tag_do_not(self):
        sc = {"S1": {"id": "S1", "who": "LEAD", "happens": "leans in", "voice": "[softly, a beat before the price] It works.",
                     "emotion": "quietly sure", "face": "a small knowing smile", "gestures": ["taps the jar twice"],
                     "camera_move": "push-in"}}
        p = prompt_of(call([{"scene": "S1", "speaker": "LEAD", "text": "It works.", "on_camera": True}]), sc, PEOPLE)
        self.assertNotIn("quietly sure", p, "a label like this is what makes Seedance overact")
        self.assertIn("a small knowing smile", p)
        self.assertIn("taps the jar twice", p)
        self.assertNotIn("It works.", p, "the words are in Audio 1, never typed beside it")
        self.assertNotIn("softly", p, "the delivery tag is for the voice, the read already carries it")
        self.assertIn(SP.CAMERA["push-in"], p)
        self.assertNotIn(SP.CAMERA["selfie"], p, "the shot's own move replaces the camera kind")

    def test_no_contract_fields_falls_back_to_the_cameras_kind(self):
        sc = {"S1": {"id": "S1", "who": "LEAD", "happens": "leans in", "voice": "It works.", "delivery": "warm · x"}}
        p = prompt_of(call([{"scene": "S1", "speaker": "LEAD", "text": "It works.", "on_camera": True}]), sc, PEOPLE)
        self.assertIn(SP.CAMERA["selfie"], p)

    def test_handheld_and_hold_map_to_the_held_and_still_camera(self):
        for move in ("handheld", "hold"):
            sc = {"S1": {"id": "S1", "who": "LEAD", "happens": "waits", "voice": "", "camera_move": move}}
            p = prompt_of(call([], camera="selfie"), sc, PEOPLE)
            self.assertIn(SP.CAMERA[move], p, move)

    def test_a_real_push_in_in_happens_gets_through_but_framing_does_not(self):
        self.assertIn("push-in", oc.no_composition("a slow push-in toward her hands"))
        self.assertEqual(oc.no_composition("close-up of her hands"), "")
        self.assertNotIn("push", oc.style_clean("Warm light. Motion: fluid animation, slow push-ins."))

    def test_off_camera_speech_never_reaches_the_clip(self):
        # P38: the 2026-10-20 Rita run's S1 — "the off-screen voice names kojic acid soap" made Omni say a line
        self.assertEqual(oc.no_speech("waits for the verdict as the off-screen voice names kojic acid soap"),
                         "waits for the verdict")
        self.assertEqual(oc.no_speech('nods on "that is the one"'), "nods")
        self.assertEqual(oc.no_speech("lifts the jar to the light"), "lifts the jar to the light")
        sc = {"S1": {"id": "S1", "who": "LEAD", "voice": "Kojic acid soap.",
                     "happens": "waits for the verdict as the off-screen voice names kojic acid soap"}}
        p = prompt_of(call([{"scene": "S1", "speaker": "DOC", "text": "Kojic acid soap.", "on_camera": False}]),
                            sc, PEOPLE, W, "", "LEAD")
        self.assertNotIn("kojic", p.lower())
        self.assertIn("waits for the verdict", p.lower())
        self.assertIn("lips closed", p)


class LifeMarksAndRealism(unittest.TestCase):
    def test_life_marks_and_gestures_are_read_from_character_md(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "character.md").write_text(
                "# X\n\n## Life marks and gestures (video spice)\nintro\n"
                "- **Life marks:** turmeric-stained fingertips; a thin burn on the left wrist.\n"
                "- **Gestures:** a slow knowing nod.\n\n## Voice\n- x\n")
            lm = oc.life_marks(Path(t))
        self.assertIn("turmeric-stained fingertips", lm["marks"])
        self.assertEqual(lm["gestures"], "a slow knowing nod")
        self.assertEqual(oc.life_marks(Path("/nonexistent")), {})

    def test_marks_and_own_gestures_reach_the_take(self):
        ppl = {**PEOPLE, "LEAD": {**PEOPLE["LEAD"], "marks": "turmeric-stained fingertips", "gestures": "a slow nod"}}
        sc = {"S1": {"id": "S1", "who": "LEAD", "happens": "talks", "voice": "Hi."}}
        p = prompt_of(call([{"scene": "S1", "speaker": "LEAD", "text": "Hi.", "on_camera": True}]),
                            sc, ppl, W, "", "LEAD")
        self.assertIn("turmeric-stained fingertips", p)
        self.assertIn("a slow nod", p)

    def test_realism_rows_by_format_by_pick_and_never_deprecated(self):
        idx = {"rows": [
            {"id": "a", "family": "camera-hand", "stage": "production", "formats": ["selfie-talk"], "level": 1, "prompt": "Tiny shake."},
            {"id": "b", "family": "skin", "stage": "writing", "also": ["production"], "formats": ["selfie-talk"], "level": 1, "prompt": "Pores."},
            {"id": "c", "family": "camera-hand", "stage": "production", "formats": ["selfie-talk"], "level": 3, "prompt": "Big."},
            {"id": "d", "family": "camera-hand", "stage": "production", "formats": ["selfie-talk"], "level": 1, "prompt": "Gone.", "status": "deprecated"},
            {"id": "e", "family": "camera-hand", "stage": "editing", "formats": ["selfie-talk"], "level": 1, "prompt": "Edit."}]}
        self.assertEqual([r["id"] for r in oc.realism_rows("selfie-talk", oc.CLIP_FAMILIES, index=idx)], ["a"])
        self.assertEqual([r["id"] for r in oc.realism_rows("selfie-talk", oc.PICTURE_FAMILIES, index=idx)], ["b"])
        self.assertEqual([r["id"] for r in oc.realism_rows(None, oc.CLIP_FAMILIES, ids=["c", "e"], index=idx)], ["c"])

    def test_the_real_index_puts_production_rows_in_a_selfie_take(self):
        sc = {"S1": {"id": "S1", "who": "LEAD", "happens": "talks", "voice": "Hi."}}
        p = prompt_of(call([{"scene": "S1", "speaker": "LEAD", "text": "Hi.", "on_camera": True}]),
                            sc, PEOPLE, W, "", "LEAD")
        want = oc.realism_rows("selfie-talk", oc.CLIP_FAMILIES)
        self.assertTrue(want)
        self.assertIn(want[0]["prompt"].strip().rstrip("."), p)


class Engines(unittest.TestCase):
    def test_every_clip_is_seedance_and_no_other_engine_is_chosen(self):
        self.assertFalse(hasattr(oc, "engine_of"))
        self.assertFalse(hasattr(oc, "build_prompt"), "the Omni prompt writer is gone: seedance_prompt.build writes the only one")
        self.assertEqual(list(CFG["engines"]), ["seedance"])

    def test_the_upscale_is_local_and_there_is_no_paid_upscaler(self):
        self.assertEqual(CFG["upscale_where"], "local")
        self.assertNotIn("upscale", CFG)

    def test_the_models_are_the_houses(self):
        import house, seedance
        self.assertEqual(CFG["models"]["image-to-video"], seedance.MOTION)
        self.assertEqual(CFG["models"]["reference-to-video"], seedance.TALK)
        self.assertEqual(CFG["tts"]["model_id"], house.voice_model())
        self.assertEqual(CFG["engines"]["seedance"]["id"], house.clip("seedance")["id"])
        self.assertEqual(CFG["takes"], 1)                       # V34: one take, another only on failure
        self.assertEqual(CFG["max_tries"], 1)                   # a hand run (the board): one take per press (2026-10-28)
        self.assertEqual(CFG["resolution"], "480p")             # the owner, 2026-10-26
        self.assertEqual(CFG["upscale_where"], "local")


class LedgerFake:
    def __init__(self):
        self.d = {}

    def get(self, cid):
        return self.d.get(cid) or {}

    def put(self, cid, **kw):
        self.d.setdefault(cid, {}).update(kw)

    def spend(self, *a, **k):
        pass


class ThreeTakes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name)
        (self.run / "media").mkdir()
        (self.run / "media" / "S1-F1.png").write_bytes(b"png")
        self.finished = []
        self._fin = oc.finish
        oc.finish = lambda run, c, cfg, led, shipped, final, d, key=None: (
            self.finished.append(Path(shipped).name), final.write_bytes(Path(shipped).read_bytes()))

    def tearDown(self):
        oc.finish = self._fin
        self.tmp.cleanup()

    def make(self, words):
        def mk(run, c, cfg, led, people):
            f = Path(c["final"])
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(c["id"].encode())
            row = {"file": str(f), "line_check": {"verdict": words.get(c["id"], "PASS")}, "status": "done"}
            led.put(c["id"], **row)
            return row
        return mk

    def test_three_takes_are_made_judged_and_the_best_kept_and_only_it_upscaled(self):
        scores = {"G01-C1-t1": 6, "G01-C1-t2": 9, "G01-C1-t3": 8}
        judge = lambda run, f, c, sc, start: {"score": scores[Path(f).stem], "pass": scores[Path(f).stem] >= 7, "problems": []}
        led = LedgerFake()
        c = {"id": "G01-C1", "start_frame": "S1-F1", "talking": True}
        got = oc.make_picked(self.run, c, {**CFG, "takes": 3}, led, {}, make=self.make({}), judge=judge)
        self.assertEqual(got["picked"], 2)
        self.assertEqual(self.finished, ["G01-C1-t2.mp4"], "only the picked take is upscaled")
        self.assertEqual((self.run / "clips" / "G01-C1.mp4").read_bytes(), b"G01-C1-t2")
        picks = json.loads((self.run / "clips" / "picks.json").read_text())
        self.assertEqual(picks["G01-C1"]["picked"], 2)
        self.assertEqual(len(picks["G01-C1"]["takes"]), 3)

    def test_a_take_whose_words_failed_is_never_picked(self):
        judge = lambda run, f, c, sc, start: {"score": 9 if Path(f).stem.endswith("t1") else 7.5, "pass": True, "problems": []}
        got = oc.make_picked(self.run, {"id": "G01-C1", "start_frame": "S1-F1", "talking": True}, {**CFG, "takes": 3},
                             LedgerFake(), {}, make=self.make({"G01-C1-t1": "CUT_OFF"}), judge=judge)
        self.assertEqual(got["picked"], 2)

    def test_none_passing_keeps_the_best_scoring_attempt_flagged_below_criteria(self):
        scores = {"G01-C1-t1": 3, "G01-C1-t2": 5, "G01-C1-t3": 4}
        judge = lambda run, f, c, sc, start: {"score": scores[Path(f).stem], "pass": False,
                                              "problems": [{"what": "lips move while listening"}]}
        led = LedgerFake()
        got = oc.make_picked(self.run, {"id": "G01-C1", "start_frame": "S1-F1"}, {**CFG, "takes": 3}, led, {},
                             make=self.make({}), judge=judge)
        self.assertEqual(got["status"], "done", "an output never stops the chain")
        self.assertEqual(got["picked"], 2)
        self.assertTrue(got["below_criteria"])
        self.assertIn("lips move while listening", " ".join(got["failed_checks"]))
        self.assertGreaterEqual(len(got["takes"]), 3, "every attempt and its score are on the ledger")
        self.assertEqual(self.finished, ["G01-C1-t2.mp4"])

    def test_a_tie_goes_to_the_later_attempt(self):
        judge = lambda run, f, c, sc, start: {"score": 4, "pass": False, "problems": [{"what": "x"}]}
        got = oc.make_picked(self.run, {"id": "G01-C1", "start_frame": "S1-F1"}, {**CFG, "takes": 3}, LedgerFake(), {},
                             make=self.make({}), judge=judge)
        self.assertEqual(got["picked"], 3)

    def test_no_attempt_making_a_file_is_the_only_stop(self):
        def mk(run, c, cfg, led, people):
            raise RuntimeError("the door is down")
        judge = lambda *a: {"score": 0, "pass": False, "problems": []}
        with self.assertRaises(RuntimeError) as cm:
            oc.make_picked(self.run, {"id": "G01-C1", "start_frame": "S1-F1"}, {**CFG, "takes": 3}, LedgerFake(), {},
                           make=mk, judge=judge)
        self.assertIn("no attempt made a clip", str(cm.exception))

    def test_a_new_round_makes_new_takes(self):
        judge = lambda run, f, c, sc, start: {"score": 8, "pass": True, "problems": []}
        got = oc.make_picked(self.run, {"id": "G01-C1", "start_frame": "S1-F1", "take_round": 2}, {**CFG, "takes": 3},
                             LedgerFake(), {}, make=self.make({}), judge=judge)
        self.assertEqual(got["picked"], 4)

    def test_one_take_then_another_only_when_it_fails(self):
        # V34: take 1 fails the judge, take 2 passes — take 3 is never made
        made = []
        mk = self.make({})
        judge = lambda run, f, c, sc, start: {"score": 4 if Path(f).stem.endswith("t1") else 8,
                                              "pass": not Path(f).stem.endswith("t1"), "problems": []}
        got = oc.make_picked(self.run, {"id": "G01-C1", "start_frame": "S1-F1"}, {**CFG, "takes": 1, "max_tries": 3},
                             LedgerFake(), {}, make=lambda *a: made.append(a[1]["id"]) or mk(*a), judge=judge)
        self.assertEqual(made, ["G01-C1-t1", "G01-C1-t2"])
        self.assertEqual(got["picked"], 2)

    def test_a_first_take_that_passes_is_the_only_one(self):
        made = []
        mk = self.make({})
        judge = lambda run, f, c, sc, start: {"score": 8, "pass": True, "problems": []}
        got = oc.make_picked(self.run, {"id": "G01-C1", "start_frame": "S1-F1"}, {**CFG, "takes": 1, "max_tries": 3},
                             LedgerFake(), {}, make=lambda *a: made.append(a[1]["id"]) or mk(*a), judge=judge)
        self.assertEqual(made, ["G01-C1-t1"])
        self.assertEqual(got["picked"], 1)

    def test_three_failures_is_the_most_then_the_best_is_kept(self):
        made = []
        mk = self.make({})
        judge = lambda run, f, c, sc, start: {"score": 3, "pass": False, "problems": [{"what": "x"}]}
        got = oc.make_picked(self.run, {"id": "G01-C1", "start_frame": "S1-F1"}, {**CFG, "takes": 1, "max_tries": 3},
                             LedgerFake(), {}, make=lambda *a: made.append(a[1]["id"]) or mk(*a), judge=judge)
        self.assertEqual(made, ["G01-C1-t1", "G01-C1-t2", "G01-C1-t3"])
        self.assertTrue(got["below_criteria"])

    def test_one_take_is_the_single_call(self):
        seen = []
        oc.make_picked(self.run, {"id": "X"}, {**CFG, "takes": 1, "max_tries": 1}, LedgerFake(), {},
                       make=lambda *a: seen.append(a[1]["id"]) or {})
        self.assertEqual(seen, ["X"])

    def test_the_judge_reads_the_house_and_never_passes_an_unanswered_take(self):
        import clip_judge
        boom = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
        r = clip_judge.judge(self.run, self.run / "x.mp4", {"id": "c", "prompt": "p", "lines": []}, {}, ask=boom)
        self.assertFalse(r["pass"])
        import house
        self.assertEqual(r["by"], house.judge())
        ok = clip_judge.judge(self.run, self.run / "x.mp4", {"id": "c", "prompt": "p", "lines": []}, {},
                              ask=lambda *a, **k: ('{"score": 8, "pass": true, "problems": []}', {"model": "m"}))
        self.assertTrue(ok["pass"])
        low = clip_judge.judge(self.run, self.run / "x.mp4", {"id": "c", "prompt": "p", "lines": []}, {},
                               ask=lambda *a, **k: ('{"score": 5, "pass": true, "problems": []}', {"model": "m"}))
        self.assertFalse(low["pass"], "a score under 7 never passes, whatever the judge's flag says")


class LockedRead(unittest.TestCase):
    def test_a_split_part_gets_only_its_own_words_of_the_read(self):
        timing = {"scenes": {"S5": {"start": 10.0, "lines": [{"text": "Three tubes, sixty days.", "start": 10.2, "end": 11.8},
                                                            {"text": "Use all three.", "start": 12.0, "end": 13.0}]}}}
        self.assertEqual(oc.part_window(timing, "S5", "Use all three."), (1.95, 3.15))
        self.assertEqual(oc.part_window(timing, "S9", "x"), (0.0, None))

    def test_no_locked_read_stops_the_call_nothing_is_revoiced(self):
        with tempfile.TemporaryDirectory() as t:
            c = {"id": "G01-C1", "voice_parts": [{"scene": "S1", "line": "Hi."}], "lines": []}
            with self.assertRaises(RuntimeError) as cm:
                oc.locked_read(Path(t), c, Path(t), None)
            self.assertIn("nothing is re-voiced", str(cm.exception))

    def test_speech_to_speech_is_gone(self):
        import clip_kit
        for name in ("revoice", "revoice_lines", "revoice_file"):
            self.assertFalse(hasattr(clip_kit, name), name)
        self.assertFalse((HERE / "omni.py").exists(), "the Omni module is removed from the chain")
        reg = json.loads((HERE / "providers.json").read_text())
        self.assertNotIn("speech_to_speech", reg["direct"]["elevenlabs"])
        self.assertNotIn("sts_model_id", reg["direct"]["elevenlabs"])
        self.assertNotIn("speech-to-speech", " ".join(oc.steps_of({"talking": True, "voice_parts": [{"person": "A"}],
                                                                   "endpoint": "image-to-video", "duration": 4,
                                                                   "start_frame": "S1-F1"})))


class Voice(unittest.TestCase):
    def setUp(self):
        import voice
        self.v = voice

    def test_the_v3_tag_is_sent_and_only_on_v3(self):
        b, _ = self.v.body_for("It works.", "eleven_v3", [], tag="softly")
        self.assertTrue(b["text"].startswith("[softly] "))
        b2, _ = self.v.body_for("It works.", "eleven_multilingual_v2", [], tag="softly")
        self.assertNotIn("[softly]", b2["text"])
        b3, _ = self.v.body_for("It works.", "eleven_v3", [])
        self.assertFalse(b3["text"].startswith("["))

    def test_the_locked_read_passes_first_then_the_closest_words_then_the_consistent_length(self):
        reads = [{"pass": False, "match": 0.99, "seconds": 2.0}, {"pass": True, "match": 0.9, "seconds": 5.0},
                 {"pass": True, "match": 0.9, "seconds": 2.1}]
        self.assertEqual(self.v.best_read(reads), 2)
        self.assertEqual(self.v.best_read([{"pass": True, "match": 0.8, "seconds": 2.0},
                                           {"pass": True, "match": 0.95, "seconds": 2.0}]), 1)

    def test_three_reads_of_every_line_the_best_locked_and_the_tag_sent(self):
        import shutil
        import test_voice as TV
        t = TV.ContinuousTests("test_scene_shape_run_goes_continuous_by_itself")
        t.setUp()
        self.v = TV.voice                                   # the module the fixture's run_for lives in
        saved = (self.v.READS, self.v.score_read)
        try:
            self.v.write_json(t.home / "voice.json", {"voice_id": "abc123", "model_id": "eleven_v3"})
            doc = {"scenes": [{"id": "S1", "delivery_tag": "warmly"}, {"id": "S2"}]}
            (t.run / "brief.md").write_text("```json\n" + json.dumps(doc) + "\n```\n")
            self.v.READS = 3
            n = {"k": 0}

            def scored(path, line, rows, check=None):
                n["k"] += 1
                return {"pass": True, "match": 0.99 if path.name.endswith("-r2.mp3") else 0.9, "seconds": 2.0, "problems": []}
            self.v.score_read = scored
            t.make()
            self.assertEqual(len(t.tr.calls), 6, "three reads of each of the two lines")
            # the reads run side by side (P52), so the calls arrive in any order: sort them by their words
            s1 = [c for c in t.tr.calls if "First sentence" in c["body"]["text"]]
            s2 = [c for c in t.tr.calls if "Third sentence" in c["body"]["text"]]
            self.assertEqual((len(s1), len(s2)), (3, 3))
            self.assertTrue(all(c["body"]["text"].startswith("[warmly] ") for c in s1))
            self.assertFalse(any(c["body"]["text"].startswith("[") for c in s2))
            self.assertEqual(len({c["body"].get("seed") for c in s1}), 3, "each read asked with its own seed")
            locks = json.loads((t.run / "vo" / "locks.json").read_text())
            self.assertEqual(locks["S1"]["locked"], 2)
            self.assertEqual(len(locks["S1"]["reads"]), 3)
            self.assertTrue((t.run / "vo" / "reads" / "S1-r3.mp3").is_file())
        finally:
            self.v.READS, self.v.score_read = saved
            t.tearDown()

    def test_one_read_again_only_when_the_words_fail_three_at_most(self):
        # V34 (2026-10-21): S1's first read fails its words check, its second passes (2 reads); S2's first passes (1 read)
        import test_voice as TV
        t = TV.ContinuousTests("test_scene_shape_run_goes_continuous_by_itself")
        t.setUp()
        self.v = TV.voice
        saved = (self.v.READS, self.v.TRIES, self.v.score_read)
        try:
            self.v.write_json(t.home / "voice.json", {"voice_id": "abc123", "model_id": "eleven_v3"})
            (t.run / "brief.md").write_text("```json\n" + json.dumps({"scenes": [{"id": "S1"}, {"id": "S2"}]}) + "\n```\n")
            self.v.READS, self.v.TRIES = 1, 3

            def scored(path, line, rows, check=None):
                bad = path.name == "S1-r1.mp3"
                return {"pass": not bad, "match": 0.5 if bad else 0.99, "seconds": 2.0, "problems": []}
            self.v.score_read = scored
            t.make()
            s1 = [c for c in t.tr.calls if "First sentence" in c["body"]["text"]]
            s2 = [c for c in t.tr.calls if "Third sentence" in c["body"]["text"]]
            self.assertEqual((len(s1), len(s2)), (2, 1))
            locks = json.loads((t.run / "vo" / "locks.json").read_text())
            self.assertEqual((locks["S1"]["locked"], len(locks["S1"]["reads"])), (2, 2))
            self.assertEqual(len(locks["S2"]["reads"]), 1)
        finally:
            self.v.READS, self.v.TRIES, self.v.score_read = saved
            t.tearDown()

    def test_the_default_voice_model_is_the_houses(self):
        import house
        self.assertEqual(self.v.default_model_id(), house.voice_model())


class Joins(unittest.TestCase):
    def test_a_persons_split_call_ends_on_the_next_parts_picture(self):
        import test_clips_run as T
        f = T.Fixture("run")
        f.setUp()
        try:
            res = f.plan()
            parts = [c for c in res["calls"] if c["clip"] == "G04-C1"]
            self.assertGreater(len(parts), 1, "the long line splits")
            for a, b in zip(parts, parts[1:]):
                self.assertEqual(a["end_frame"], b["start_frame"])
            self.assertIsNone(parts[-1]["end_frame"])
        finally:
            f.tearDown()

    def test_continuous_ends_on_the_next_sections_first_picture(self):
        import storyboard_plan as SP
        import clips_plan as CP
        secs = [{"id": "G01", "scenes": ["S1"], "clips": [{}], "frames": [{"what": "start frame", "from": "S1"},
                                                                         {"what": "end frame", "from": "S1", "edit_of": "S1"}]},
                {"id": "G02", "scenes": ["S2"], "clips": [{}], "frames": [{"what": "start frame", "from": "S2"}]}]
        joined = SP.continuous_joins(secs, {"S1": {"id": "S1", "hands_off": "continuous"}, "S2": {"id": "S2"}})
        self.assertEqual(joined, ["G01"])
        self.assertEqual(CP.picture_ids(secs[0])["end"], "S2-F1")
        self.assertEqual(CP.picture_ids(secs[1])["start"], "S2-F1")
        cut = [{"id": "G01", "scenes": ["S1"], "clips": [{}], "frames": [{"what": "start frame", "from": "S1"}]},
               {"id": "G02", "scenes": ["S2"], "clips": [{}], "frames": [{"what": "start frame", "from": "S2"}]}]
        self.assertEqual(SP.continuous_joins(cut, {"S1": {"hands_off": "cut"}}), [])

    def test_the_gate_checks_join_props_nowhere_and_set_before_any_spend(self):
        import clip_gate as G
        calls = [{"id": "G01-C1", "clip": "G01-C1", "scenes": ["S1", "S2"], "start_frame": "S1-F1", "end_frame": None,
                  "hands_off": "continuous"},
                 {"id": "G02-C1", "clip": "G02-C1", "scenes": ["S3"], "start_frame": "S3-F1", "end_frame": None}]
        scenes = {"S1": {"id": "S1", "setting_id": "KITCHEN", "props": ["jar"]},
                  "S2": {"id": "S2", "setting_id": "BATH", "props": ["lime"]},
                  "S3": {"id": "S3", "setting_id": "BATH", "props": ["jar"]}}
        out = G.continuity(calls, scenes, {"props": [{"name": "jar"}, {"name": "lime", "size": "6 cm"}]})
        red = " | ".join(out["G01-C1"]["red"])
        self.assertIn("JOIN", red)
        self.assertIn("NOWHERE: lime", red)
        self.assertIn("SET", red)
        self.assertIn("PROPS: jar", red)
        calm = G.continuity(calls[1:], {"S3": {"id": "S3", "props": ["jar"]}}, {})
        self.assertEqual(calm["G02-C1"]["red"], [], "a brief without the fields is never failed")


class RunV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util as u
        sp = u.spec_from_file_location("vm_test_run_v2", HERE / "run_v2.py")
        cls.V2 = u.module_from_spec(sp)
        sp.loader.exec_module(cls.V2)

    def test_one_version_of_each_start_picture(self):
        # the owner, 2026-10-24: "Stop doing 3 versions each, remove that from the process"
        self.assertEqual(self.V2.CFG["pictures"]["versions"], 1)

    def test_every_take_is_480p_every_format(self):
        # the owner, 2026-10-26: every clip is Seedance 2.5 at 480p, upscaled locally (replaces the 720p ruling)
        for fmt in (None, "song-ad", "expert-consult", "remedy"):
            self.assertEqual(self.V2.clip_resolution(fmt), "480p")
        m = self.V2._patch_clips(self.V2._orig_load("clips_run"), "expert-consult")
        c = m.route_cfg(None, "expert-consult")
        # V34 (2026-10-21): ONE take, another only when it fails, three in all at most; 480p since 2026-10-26
        self.assertEqual((c["resolution"], c["takes"], c["max_tries"], c["upscale_where"]), ("480p", 1, 3, "local"))

    def test_a_version_whose_face_failed_is_never_kept_over_one_that_passed(self):
        # 2026-10-24: S4 kept a different man in Marcus's chair (fewest other problems) over two versions that passed
        V2 = self.V2
        FG = V2._orig_load("face_gate")
        saved = (V2._orig_hand, V2._problems, V2._refs_of, V2.R.record_subject_boxes)
        problems = {1: 0, 2: 3, 3: 1}
        faces = {"S1-F1": "DIFFERENT", "S1-F1-pick2": "SAME", "S1-F1-pick3": "SAME"}

        def hand(items, run, dry, brand=None, **kw):
            out = {}
            for it in items:
                f = Path(run) / "media" / f"{it['id']}.png"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(str(it["id"]).encode())
                FG.stamp(f, [str(master)], check=lambda p, ms: [{"master": m, "verdict": faces[it["id"]]} for m in ms])
                out[str(it["id"])] = {"file": str(f)}
            return out

        def probs(run, it, f, refs, piece, job):
            k = int(job.rsplit("-", 1)[-1])
            return problems[k], [{"what": "x"}] * problems[k]
        # the mechanism, for a run set above one version (pictures are ONE version since 2026-10-24)
        _pv = V2.CFG["pictures"].get("versions")
        V2.CFG["pictures"]["versions"] = 3
        self.addCleanup(V2.CFG["pictures"].__setitem__, "versions", _pv)
        try:
            V2._orig_hand, V2._problems, V2._refs_of = hand, probs, lambda *a: []
            V2.R.record_subject_boxes = lambda *a, **k: None
            with tempfile.TemporaryDirectory() as t:
                run = Path(t)
                master = run / "casting" / "m" / "full" / "master.png"
                master.parent.mkdir(parents=True)
                master.write_bytes(b"m")
                it = {"id": "S1-F1", "kind": "still", "frame_role": "first", "params": {"prompt": "x"}}
                V2.v2_hand([it], run, False, brand="_fixture")
                rec = json.loads((run / "picture-picks.json").read_text())
                self.assertEqual(rec["S1-F1"]["kept"], 3, "the face first, then the fewest problems")
                kept = run / "media" / "S1-F1.png"
                self.assertEqual(kept.read_bytes(), b"S1-F1-pick3")
                self.assertTrue(FG.require(kept)["pass"], "the kept picture carries the record of its own bytes")
        finally:
            V2._orig_hand, V2._problems, V2._refs_of, V2.R.record_subject_boxes = saved

    def test_a_swipe_edit_prompt_carries_the_change_only(self):
        slot = self.V2.CFG["safe_area"]["slot"]
        self.assertNotIn(slot, self.V2.v2_prompt("Edit image 1.", {}, True, swipe_edit=True))
        self.assertIn(slot, self.V2.v2_prompt("A woman at a counter.", {}, True))
        self.assertTrue(self.V2.v2_prompt("A woman.", {}, False, extra="Pores.").endswith("Pores."))

    def test_a_flagged_picture_is_held_not_signed_off(self):
        with tempfile.TemporaryDirectory() as t:
            run = Path(t)
            (run / "clips").mkdir()
            (run / "clips" / "gate-approved.json").write_text(json.dumps({"S1-F1": {"by": "the system"},
                                                                          "S2-F1": {"by": "the system"},
                                                                          "S3-F1": {"by": "the owner"}}))
            held = self.V2._hold_flagged(run, [{"id": "S1-F1", "verdict": "PASS"}, {"id": "S2-F1", "verdict": "FLAGGED"},
                                               {"id": "S3-F1", "verdict": "FLAGGED"}])
            self.assertEqual(held, ["S2-F1"])
            left = json.loads((run / "clips" / "gate-approved.json").read_text())
            self.assertIn("S1-F1", left)
            self.assertNotIn("S2-F1", left)
            self.assertIn("S3-F1", left, "the owner's own word overrules")

    def test_the_voice_reads_three_and_the_product_is_never_baked(self):
        # V34: one read of every line, read again only when its words check fails, three in all at most
        self.assertEqual((self.V2.R.voice_mod.READS, self.V2.R.voice_mod.TRIES), (1, 3))
        self.assertIsNone(self.V2.R.product_gate([], "S1-F1"))
        self.assertEqual(self.V2.R.product_of({}, {"file": "x"}, "S1-F1", "", [], None, False), {"file": "x"})

    def test_picture_versions_are_made_and_checked_side_by_side_with_the_same_pick(self):
        # P53: version 1, 2 and 3 at once; fewest problems wins, the earliest version on a tie — unchanged. Since V33 the
        # default is ONE version (asserted below); this test sets 3 to prove the side-by-side pick still works when asked.
        import time
        V2 = self.V2
        self.assertEqual(V2.CFG["pictures"]["versions"], 1, "V33: one picture per start picture")
        saved_versions = V2.CFG["pictures"]["versions"]
        V2.CFG["pictures"]["versions"] = 3
        saved = (V2._orig_hand, V2._problems, V2._refs_of, V2.R.record_subject_boxes, V2.CFG["pictures"].get("parallel"))
        problems = {1: 2, 2: 1, 3: 1}

        def hand(items, run, dry, brand=None, **kw):
            time.sleep(0.5)
            out = {}
            for it in items:
                f = Path(run) / "media" / f"{it['id']}.png"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(str(it["id"]).encode())
                out[str(it["id"])] = {"file": str(f)}
            return out

        def probs(run, it, f, refs, piece, job):
            time.sleep(0.5)
            k = int(job.rsplit("-", 1)[-1])
            return problems[k], [{"what": "x"}] * problems[k]
        # the mechanism, for a run set above one version (pictures are ONE version since 2026-10-24)
        _pv = V2.CFG["pictures"].get("versions")
        V2.CFG["pictures"]["versions"] = 3
        self.addCleanup(V2.CFG["pictures"].__setitem__, "versions", _pv)
        try:
            V2._orig_hand, V2._problems, V2._refs_of = hand, probs, lambda *a: []
            V2.R.record_subject_boxes = lambda *a, **k: None
            with tempfile.TemporaryDirectory() as t:
                run = Path(t)
                it = {"id": "S1-F1", "kind": "still", "frame_role": "first", "params": {"prompt": "x"}}
                t0 = time.time()
                V2.v2_hand([it], run, False, brand="_fixture")
                took = round(time.time() - t0, 2)
                rec = json.loads((run / "picture-picks.json").read_text())
                self.assertEqual(rec["S1-F1"]["kept"], 2, "fewest problems, then the earliest version")
                self.assertEqual((run / "media" / "S1-F1.png").read_bytes(), b"S1-F1-pick2")
        finally:
            V2._orig_hand, V2._problems, V2._refs_of, V2.R.record_subject_boxes = saved[:4]
            V2.CFG["pictures"]["versions"] = saved_versions
        # made one after another this is 3 x 0.5 s of making + 3 x 0.5 s of checking = 3.0 s (the same 2/3 bound as at 0.2 s, longer so a busy machine's overhead cannot decide it)
        self.assertLess(took, 2.0, f"took {took} s")
        print(f"\n  P53 measured (3 versions, 0.5 s to make and 0.5 s to check each): serial 3.0 s → side by side {took} s")

    def test_every_voice_reads_on_the_house_model(self):
        import house
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "voice.json").write_text(json.dumps({"voice_id": "abc", "model_id": "eleven_multilingual_v2"}))
            vid, mid, _st = self.V2.R.voice_mod.binding(Path(t))
        self.assertEqual((vid, mid), ("abc", house.voice_model()))

    def test_no_edit_covers_it_anywhere_in_the_runner(self):
        src = (HERE / "run_v2.py").read_text()
        self.assertNotIn("the edit covers it", src)
        self.assertNotIn("the edit punches in", src)

    def test_the_order_is_voice_storyboard_pictures_clips(self):
        src = (HERE / "run_v2.py").read_text()
        i = [src.index(s) for s in ('print("1 · voice', '_storyboard(run, brief', 'argv + ["--storyboard"]',
                                    'R.main(argv + ["--clips"])')]
        self.assertEqual(i, sorted(i))

    def test_checks_ask_the_house_judge(self):
        import v2_checks, house
        self.assertEqual(v2_checks.model_of(self.V2.CFG["checks"]["review_model"]), house.judge())
        self.assertEqual(v2_checks.model_of(self.V2.CFG["checks"]["zone_model"]), house.judge())


class NoProductInGeneration(unittest.TestCase):
    def test_the_product_is_never_attached_to_a_generation(self):
        import element_refs as ER
        self.assertFalse(ER.PRODUCT_IN_GENERATION)


class VoiceClarity(unittest.TestCase):
    """P47: the read is asked for at the best mp3, measured for clarity, and the crisp finish follows the fit."""

    def test_the_read_is_asked_for_at_192k(self):
        import voice
        self.assertIn("output_format=mp3_44100_192", voice.timestamps_url("abc"))

    def test_clarity_tells_a_muffled_voice_from_a_clear_one(self):
        import subprocess, audiocheck
        with tempfile.TemporaryDirectory() as t:
            clear, dull = Path(t) / "clear.wav", Path(t) / "dull.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=d=2:c=pink", str(clear)], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clear), "-af", "lowpass=f=2500,lowpass=f=2500", str(dull)],
                           check=True)
            c, d = audiocheck.clarity(clear), audiocheck.clarity(dull)
        self.assertGreater(c, audiocheck.DULL_DB)
        self.assertLess(d, audiocheck.DULL_DB)

class PictureBackup(unittest.TestCase):
    """P48 (V21): a picture GPT Image refuses goes to the house backup, Seedream on fal — fakes only."""

    def test_a_refused_picture_is_never_dropped_and_points_to_the_picture_ladder(self):
        # the legacy OpenAI door has no backup of its own since 2026-10-26; the ladder (tools/image-production:
        # GPT Image, Seedream, Nano Banana Pro, OpenAI) moves a refused picture on. This door must stop loudly, name the
        # refusal and the ladder, and write nothing.
        import direct_openai as D
        calls = []

        def openai(method, url, headers, body):
            return 400, {}, json.dumps({"error": {"code": "moderation_blocked"}}).encode()

        def fal(method, url, headers, body):
            calls.append(url)
            return 200, {}, b"{}"
        with tempfile.TemporaryDirectory() as t:
            ref = Path(t) / "cast.png"
            ref.write_bytes(b"\x89PNG ref")
            out = Path(t) / "S1-F1.png"
            with self.assertRaises(RuntimeError) as cm:
                D.generate("a woman at a counter", [ref], out, transport=openai, key="k", backup_transport=fal)
            self.assertFalse(out.exists())
        self.assertIn("moderation_blocked", str(cm.exception))
        self.assertIn("picture ladder", str(cm.exception))
        self.assertEqual(calls, [])

    def test_the_model_lock_lets_the_house_backup_through_and_nothing_else(self):
        import importlib.util as u, direct_openai as D
        sp = u.spec_from_file_location("vm_t_run_lock", HERE / "run.py")
        R = u.module_from_spec(sp); sp.loader.exec_module(R)
        reg = {"doors": {"still": {"model": "gpt-image-2.5-sunburst"}}}
        R.ruled_model(reg, "still", D.backup_model())
        with self.assertRaises(SystemExit):
            R.ruled_model(reg, "still", "some-other-model")

    def test_the_house_backup_id_is_verified(self):
        import house
        b = house.model("pictures.backup")
        self.assertEqual(b["registry_id"], "seedream-5-pro-edit")
        self.assertTrue(b["model"].startswith("seedream"))      # Higgsfield's id (HOUSE-PIC-3), not fal's
        self.assertIn("verified", b)


class ReadAndTakeAsAPair(unittest.TestCase):
    """P49: the read and the take are picked together; a pair off its lips gets one paced read before a hold."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name)
        (self.run / "media").mkdir()
        (self.run / "media" / "S1-F1.png").write_bytes(b"png")
        (self.run / "vo" / "reads").mkdir(parents=True)
        reads = []
        for k in (1, 2, 3):
            (self.run / "vo" / "reads" / f"S1-r{k}.mp3").write_bytes(b"r")
            reads.append({"read": k, "file": f"vo/reads/S1-r{k}.mp3", "pass": True})
        (self.run / "vo" / "locks.json").write_text(json.dumps({"S1": {"locked": 1, "reads": reads}}))
        self.c = {"id": "G01-C1", "start_frame": "S1-F1", "talking": True,
                  "voice_parts": [{"scene": "S1", "line": "Hi there."}],
                  "lines": [{"scene": "S1", "on_camera": True, "text": "Hi there."}]}
        self._fin = oc.finish
        oc.finish = lambda run, c, cfg, led, shipped, final, d, key=None: final.write_bytes(Path(shipped).read_bytes())

    def tearDown(self):
        oc.finish = self._fin
        self.tmp.cleanup()

    def make(self, offset):
        def mk(run, c, cfg, led, people):
            f = Path(c["final"]); f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(c["id"].encode())
            raw = f.with_name(c["id"] + "-raw.mp4"); raw.write_bytes(b"raw")
            row = {"file": str(f), "raw": str(raw), "line_check": {"verdict": "PASS"},
                   "align": {"stretch": 0.1, "max_offset_s": offset, "take_span": 3.0, "lip_span": 2.0}}
            led.put(c["id"], **row)
            return row
        return mk

    def fit(self, offsets):
        def f(run, c, raw, read, out):
            out.write_bytes(read.name.encode())
            off = next((v for kk, v in offsets.items() if kk in read.stem), 0.9)
            return {"file": str(out), "line_check": {"verdict": "PASS"},
                    "align": {"stretch": 0.02, "max_offset_s": off, "take_span": 3.0, "lip_span": 2.0}}
        return f

    def judge(self, *a):
        return {"score": 8, "pass": True, "problems": []}

    def test_each_line_is_its_own_read_with_its_own_tag_and_lock(self):
        # P55 (VIDEO-RULINGS V4): a scene whose shots carry lines is read line by line, three reads a line, one locked
        import test_voice as TV
        t = TV.ContinuousTests("test_scene_shape_run_goes_continuous_by_itself")
        t.setUp()
        v = TV.voice
        saved = (v.READS, v.score_read)
        try:
            v.write_json(t.home / "voice.json", {"voice_id": "abc123", "model_id": "eleven_v3"})
            doc = {"scenes": [{"id": "S1", "shots": [{"lines": [{"say": "First sentence here.", "delivery_tag": "softly"}]},
                                                     {"lines": [{"say": "Second one lands.", "delivery_tag": "with a grin"}]}]},
                              {"id": "S2", "delivery_tag": "flat"}]}
            (t.run / "brief.md").write_text("```json\n" + json.dumps(doc) + "\n```\n")
            v.READS = 3
            v.score_read = lambda path, line, rows, check=None: {
                "pass": True, "match": 0.99 if path.name.endswith("-r2.mp3") else 0.9, "seconds": 2.0, "problems": []}
            t.make()
            texts = [c["body"]["text"] for c in t.tr.calls]
            self.assertEqual(sum(x == "[softly] First sentence here." for x in texts), 3)
            self.assertEqual(sum(x == "[with a grin] Second one lands." for x in texts), 3)
            self.assertEqual(sum(x.startswith("[flat] Third sentence") for x in texts), 3, "a scene with no lines is one line")
            locks = json.loads((t.run / "vo" / "locks.json").read_text())
            self.assertEqual(sorted(locks), ["S1.L1", "S1.L2", "S2"])
            self.assertEqual(locks["S1.L2"]["say"], "Second one lands.")
            tm = json.loads((t.run / "vo" / "timing.json").read_text())["scenes"]["S1"]
            self.assertEqual([x["line"] for x in tm["line_reads"]], ["S1.L1", "S1.L2"])
            self.assertEqual(len(tm["lines"]), 2, "the scene's slice still times both sentences")
            self.assertTrue((t.run / "vo" / "S1.mp3").is_file())
        finally:
            v.READS, v.score_read = saved
            t.tearDown()

    def test_the_paced_read_asks_the_voice_for_the_takes_pace(self):
        import test_voice as TV
        t = TV.ContinuousTests("test_scene_shape_run_goes_continuous_by_itself")
        t.setUp()
        try:
            TV.voice.write_json(t.home / "voice.json", {"voice_id": "abc123", "model_id": "eleven_v3", "settings": {"speed": 1.0}})
            tr = TV.FakeTimestamps()
            got = TV.voice.paced_read(t.run, "S1", 1.5, t.run / "vo" / "reads" / "S1-paced.mp3", character="lead",
                                      cast_root=str(t.cast_root), transport=tr, key="k")
            self.assertEqual(got["speed"], 1.2, "held to ElevenLabs' own 0.7-1.2")
            self.assertEqual(tr.calls[0]["body"]["voice_settings"]["speed"], 1.2)
            self.assertTrue((t.run / "vo" / "reads" / "S1-paced.mp3").is_file())
            self.assertTrue(json.loads((t.run / "vo" / "locks.json").read_text())["S1"]["paced"])
        finally:
            t.tearDown()

class BriefContract(unittest.TestCase):
    """P50 + P51 (2026-10-21, worker 1's proof run): the brief contract takes the hand-offs, and a claim fix follows
    the shot lines."""

    def test_continuous_and_action_transitions_pass_the_contract_and_drive_the_join(self):
        import model_inputs as MI, storyboard_plan as SP
        doc = {"scenes": [{"id": "S1"}, {"id": "S2"}],
               "layers": {"transitions": [{"after_scene": "S1", "kind": "continuous"}, {"after_scene": "S2", "kind": "action"}]}}
        faults = [f for f in MI.element_faults(doc) if "transitions" in f]
        self.assertEqual(faults, [])
        self.assertTrue([f for f in MI.element_faults({**doc, "layers": {"transitions": [{"after_scene": "S1", "kind": "dissolve"}]}})
                         if "transitions" in f], "a kind off the list is still refused")
        ho = SP.hands_off_of(doc)
        self.assertEqual((ho["S1"]["hands_off"], ho["S2"]["hands_off"]), ("continuous", "action"))
        secs = [{"id": "G01", "scenes": ["S1"], "clips": [{}], "frames": [{"what": "start frame", "from": "S1"}]},
                {"id": "G02", "scenes": ["S2"], "clips": [{}], "frames": [{"what": "start frame", "from": "S2"}]}]
        self.assertEqual(SP.continuous_joins(secs, ho), ["G01"])

    def test_a_claim_fix_follows_into_every_shot_line_and_they_still_join(self):
        import claimfix as CF
        was = "Turmeric tells those cells to stop. Use it twice a week."
        doc = {"scenes": [{"id": "S1", "voice": was, "shots": [
            {"lines": [{"say": "Turmeric tells those cells to stop."}]}, {"lines": [{"say": "Use it twice a week."}]}]}]}
        with tempfile.TemporaryDirectory() as t:
            b = Path(t) / "5-brief.md"
            b.write_text("# brief\n\n```json\n" + json.dumps(doc) + "\n```\n")
            now = "Turmeric helps the look of dark spots fade. Use it twice a week."
            reply = json.dumps({"fixes": [{"id": "S1.voice", "now": now, "rule": "appearance only"}]})
            saved = CF.claim_rules
            CF.claim_rules = lambda brand, product=None: "(rules)"
            try:
                done = CF.fix(b, "_fixture", call=lambda p: reply)
            finally:
                CF.claim_rules = saved
            out = CF.SL._block(b.read_text())[1]
        says = [l["say"] for sh in out["scenes"][0]["shots"] for l in sh["lines"]]
        self.assertEqual(says, ["Turmeric helps the look of dark spots fade.", "Use it twice a week."])
        self.assertEqual(out["scenes"][0]["voice"], now)
        self.assertTrue(done[0]["lines_join"])


class AbsurdOnPurpose(unittest.TestCase):
    """P59 (VIDEO-RULINGS V24): absurd on purpose passes, slop still fails, stop-power breaks a tie, and the brief's
    hyper-specific depiction words reach the clip untrimmed."""

    def test_the_reviewer_and_the_judge_read_the_new_prompts(self):
        import clip_judge
        cfg = json.loads((HERE / "v2.json").read_text())
        # the review the run reads is v5 (P68), which keeps every v4 rule (absurd on purpose, slop still slop)
        self.assertTrue(cfg["review"]["prompt"].endswith("picture-review-v8-owner.md"))   # P72: v8 = v7 + culture
        self.assertTrue((HERE.parent / "prompts" / "v2" / "picture-review-v7-owner.md").is_file(), "v7 kept")
        v7 = (HERE.parent / "prompts" / "v2" / "picture-review-v7-owner.md").read_text()
        self.assertIn("tone drifts", v7.lower())
        self.assertTrue((HERE.parent / "prompts" / "v2" / "picture-review-v6-owner.md").is_file(), "v6 kept")
        rv = (HERE.parent / "prompts" / "v2" / "picture-review-v6-owner.md").read_text()
        self.assertIn("Absurd on purpose is not slop", rv)
        self.assertIn("Slop is still slop", rv)
        self.assertTrue((HERE.parent / "prompts" / "v2" / "picture-review-v3-owner.md").is_file(), "v3 kept, never edited in place")
        self.assertTrue(clip_judge.PROMPT.name == "clip-judge-v4-owner.md")
        self.assertIn("stop_power", clip_judge.PROMPT.read_text())
        r = clip_judge.judge(Path(tempfile.mkdtemp()), Path("x.mp4"), {"id": "c", "prompt": "p", "lines": []}, {},
                             ask=lambda *a, **k: ('{"score": 8, "pass": true, "stop_power": 9, "problems": []}', {}))
        self.assertEqual(r["stop_power"], 9.0)

    def test_equal_quality_the_more_striking_take_wins(self):
        takes = [{"take": 1, "score": 8.0, "stop_power": 4, "pass": True, "read": "locked"},
                 {"take": 2, "score": 8.0, "stop_power": 9, "pass": True, "read": "locked"},
                 {"take": 3, "score": 8.5, "stop_power": 1, "pass": True, "read": "locked"}]
        self.assertEqual(oc.pick(takes)["take"], 3, "quality first")
        self.assertEqual(oc.pick(takes[:2])["take"], 2, "then stop-power")
        self.assertEqual(oc.pick([{**t, "stop_power": 5} for t in takes[:2]])["take"], 1, "then the earliest")

    def test_hyper_specific_depictions_reach_the_clip_prompt_untrimmed(self):
        happens = "an extreme close-up of a grapefruit-sized whitehead oozing thick yellow pus onto a white tile"
        self.assertEqual(oc.no_composition(happens), "a grapefruit-sized whitehead oozing thick yellow pus onto a white tile")
        sc = {"S1": {"id": "S1", "who": "LEAD", "happens": happens, "voice": ""}}
        p = prompt_of(call([], scenes=("S1",)), sc, PEOPLE, W, "", "LEAD")
        self.assertIn("grapefruit-sized whitehead oozing thick yellow pus onto a white tile", p)
        self.assertNotRegex(p.lower(), r"close-?up")


class EveryShotAndTheLastGaps(unittest.TestCase):
    """P60–P64 (the 10-21 re-verify): every shot's acting in every case, the gate's remake per line, the bed model from
    the house, the voice at the edit's rate, and no caller lowers the picture quality."""

    SC = {"S1": {"id": "S1", "who": "LEAD", "happens": "talks", "voice": "First thing here. Second thing lands hard.",
                 "shots": [{"face": "wary eyes", "camera_move": "hold", "lines": [{"say": "First thing here."}]},
                           {"face": "triumphant grin", "camera_move": "push-in", "hands_off": "continuous",
                            "lines": [{"say": "Second thing lands hard.", "delivery_tag": "loud"}]}]}}

    def test_a_split_part_gets_the_acting_of_the_shots_its_words_fall_in(self):
        l = {"scene": "S1", "speaker": "LEAD", "text": "Second thing lands hard.", "on_camera": True, "part": "2/2"}
        p = prompt_of(call([l]), self.SC, PEOPLE, W, "", "LEAD")
        self.assertIn("triumphant grin", p)
        self.assertNotIn("wary eyes", p)

    def test_a_piece_of_one_long_shot_line_maps_to_that_shot(self):
        got = oc.shots_in(self.SC["S1"], "lands hard")
        self.assertEqual([g.get("face") for g in got], ["triumphant grin"])

    def test_shots_whose_lines_do_not_join_still_each_act_and_the_calls_line_is_said(self):
        sc = {"S1": {**self.SC["S1"], "voice": "A different line now."}}
        l = {"scene": "S1", "speaker": "LEAD", "text": "A different line now.", "on_camera": True}
        p = prompt_of(call([l]), sc, PEOPLE, W, "", "LEAD")
        self.assertIn("wary eyes", p)
        self.assertIn("triumphant grin", p)
        self.assertNotIn("A different line now.", p, "the call's line is Audio 1, never typed")
        self.assertNotIn("First thing here.", p)

    def test_one_shot_row_is_still_that_shots_acting(self):
        sc = {"S1": {"id": "S1", "who": "LEAD", "happens": "talks", "voice": "Hi.",
                     "shots": [{"face": "giddy laugh", "lines": [{"say": "Hi."}]}]}}
        p = prompt_of(call([{"scene": "S1", "speaker": "LEAD", "text": "Hi.", "on_camera": True}]), sc, PEOPLE, W, "", "LEAD")
        self.assertIn("giddy laugh", p)

    def test_the_gates_remake_is_per_line_three_reads_one_locked(self):
        import test_voice as TV
        t = TV.ContinuousTests("test_scene_shape_run_goes_continuous_by_itself")
        t.setUp()
        v = TV.voice
        saved = (v.READS, v.score_read)
        try:
            v.write_json(t.home / "voice.json", {"voice_id": "abc123", "model_id": "eleven_v3"})
            doc = {"scenes": [{"id": "S1", "shots": [{"lines": [{"say": "First sentence here.", "delivery_tag": "softly"}]},
                                                     {"lines": [{"say": "Second one lands.", "delivery_tag": "loud"}]}]}]}
            (t.run / "brief.md").write_text("```json\n" + json.dumps(doc) + "\n```\n")
            v.READS = 3
            v.score_read = lambda path, line, rows, check=None: {"pass": True, "match": 0.9, "seconds": 2.0, "problems": []}
            tr = TV.FakeTimestamps()
            v.remake_scene(t.run, "S1", character="lead", cast_root=str(t.cast_root), transport=tr, key="k")
            texts = [c["body"]["text"] for c in tr.calls]
            self.assertEqual(sum(x == "[softly] First sentence here." for x in texts), 3)
            self.assertEqual(sum(x == "[loud] Second one lands." for x in texts), 3)
            locks = json.loads((t.run / "vo" / "locks.json").read_text())
            self.assertEqual(locks["S1.L1"]["remake"], 1)
            self.assertTrue((t.run / "vo" / "S1.mp3").is_file())
        finally:
            v.READS, v.score_read = saved
            t.tearDown()

    def test_the_bed_is_made_on_the_houses_music_model(self):
        import make_bank, house
        req = make_bank.request_of("music", {"id": "x", "prompt": "a lo-fi bed", "seconds": 30})
        self.assertEqual(req["body"]["model_id"], house.model("sound.music_bed")["model"])
        self.assertTrue((HERE / "sound.py").read_text().split("BED_MODEL = ")[1].startswith('BED["model"]'),
                        "the bed model is read from the house, never typed")

    def test_the_claude_md_no_longer_sends_the_edit_to_swipe_cut(self):
        self.assertNotIn("swipe_cut.py`).", (HERE.parent / "CLAUDE.md").read_text())


class FiveHardFails(unittest.TestCase):
    """P68 (2026-10-21, the first real v2 pictures): the review fails the swipe's things, any words, a drawn product,
    a face that is not the cast master and a set that is not ours; the swipe-edit prompt changes all five."""

    def test_the_review_names_all_five_and_never_shows_the_on_screen_words(self):
        rv = (HERE.parent / "prompts" / "v2" / "picture-review-v5-owner.md").read_text()
        for k in ("The swipe's things, not ours", "Any words", "A drawn product", "Not the cast member", "The set is ours"):
            self.assertIn(k, rv)
        self.assertTrue((HERE.parent / "prompts" / "v2" / "picture-review-v4-owner.md").is_file(), "v4 kept")
        import importlib.util as u
        sp = u.spec_from_file_location("t_p68_run_v2", HERE / "run_v2.py")
        V2 = u.module_from_spec(sp); sp.loader.exec_module(V2)
        with tempfile.TemporaryDirectory() as t:
            run = Path(t)
            (run / "plan.json").write_text(json.dumps({"scenes": [{"id": "S8", "setting_id": "K", "happens": "holds it up",
                                                                     "on_screen": "Most Women Who Used It Saw Their Dark Spots Fade.",
                                                                     "props": ["the gold pitcher"]}],
                                                       "piece": {"props": [{"name": "the gold pitcher", "size": "22 cm", "look": "gold water"}]}}))
            (run / "brief.md").write_text("```json\n" + json.dumps({"scenes": [{"id": "S8"}], "world": [
                {"id": "K", "description": "a kitchen", "dressing": ["jars of roots"]}]}) + "\n```\n")
            w = V2._scene_words(run, {"for": "S8"})
        self.assertNotIn("Most Women", w, "on-screen words are the edit's — never asked of the picture")
        self.assertIn("the ONLY objects allowed", w)
        self.assertIn("jars of roots", w)
        self.assertIn("no words of any kind", w)
        self.assertIn("not in this picture", w, "a scene with no product held asks for no product")

    def test_two_people_are_each_placed_and_never_blended(self):
        import element_refs as ER
        people = [("MAN master", "m"), ("MAN turnaround", "t"), ("PASTOR master", "pm"), ("PASTOR details", "pd")]
        cast = {"MAN": {"identity_block": "a bald giant"}, "PASTOR": {"identity_block": "a man in glasses"}}
        s = ER.person_clauses(["MAN", "PASTOR"], people, cast,
                              "MAN at the left leaning on the door; PASTOR inside at the open rear window")
        self.assertIn("(a) MAN — the one at the left leaning on the door — becomes a bald giant, as images 2–3", s)
        self.assertIn("(b) PASTOR — the one inside at the open rear window — becomes a man in glasses, as images 4–5", s)
        self.assertIn("never a blend", ER.PERSON_MANY)

    def test_the_swipe_edit_prompt_changes_all_five(self):
        import element_refs as ER
        doc = {"props": [{"name": "the four ingredient bowls", "size": "8 cm", "look": "turmeric, moringa, chamomile, ginger"}],
               "world": [{"id": "K", "dressing": ["jars of dried roots", "a Thai calligraphy card"]}]}
        sc = {"id": "S5", "setting_id": "K", "props": ["the four ingredient bowls"]}
        words, _refs = ER.swipe_props(sc, doc, "_fixture")
        p = ER.SWIPE_EDIT.format(who="YAI", worn="indigo", s="s", verb="", people="next 5", props=words,
                                 dressing=ER.set_words(sc, doc), product=ER.product_words(sc, doc, "_fixture"))
        for k in ("THE PERSON", "THE PROPS", "THE WORDS", "THE PRODUCT", "THE SET"):
            self.assertIn(k, p)
        self.assertIn("turmeric, moringa, chamomile, ginger", p)
        self.assertIn("a Thai calligraphy card", p)
        self.assertIn("flag", p)
        self.assertIn("never younger", p)


class TheRealProductInHerHands(unittest.TestCase):
    """P68 add (the owner, 2026-10-21: "why are we using the wrong product in those images of yai holding something?????"):
    a scene where a person holds the product gets the brand's real packshot as a reference and the real photograph
    pasted over it; the review and the clip judge fail anything else."""

    def test_a_held_product_scene_asks_for_the_real_product_and_others_for_none(self):
        import element_refs as ER
        doc = {"piece": {"product": "x-scrub"}, "product_lock": ["S8 — the tube held in both hands"]}
        held = {"id": "S8", "happens": "holds the scrub steady in both hands"}
        other = {"id": "S3", "happens": "talks to the lens"}
        self.assertTrue(ER.held_product(held, doc))
        self.assertFalse(ER.held_product(other, doc))
        self.assertIn("brand's own", ER.product_words(held, doc, "_fixture"))
        self.assertIn("replaced with the real photograph", ER.product_words(held, doc, "_fixture"))
        self.assertIn("draw no product", ER.product_words(other, doc, "_fixture"))

    def test_the_paste_uses_the_kits_real_photo_cutouts_when_there_is_no_turntable(self):
        import product_paste as PP
        with tempfile.TemporaryDirectory() as t:
            kit = Path(t)
            (kit / "model").mkdir()
            (kit / "sources").mkdir()
            for n in ("reference-front-transparent.png", "reference-back-transparent.png"):
                (kit / "model" / n).write_bytes(b"png")
            self.assertEqual([a for a, _ in PP.cutouts(kit)], [0, 180])
            (kit / "sources" / "turntable-015.png").write_bytes(b"png")
            self.assertEqual([a for a, _ in PP.cutouts(kit)], [15], "a real turntable wins")

    def test_v2_pastes_the_real_product_and_holds_a_picture_whose_paste_failed(self):
        import importlib.util as u
        sp = u.spec_from_file_location("t_p68b_run_v2", HERE / "run_v2.py")
        V2 = u.module_from_spec(sp); sp.loader.exec_module(V2)
        with tempfile.TemporaryDirectory() as t:
            kit = Path(t) / "kit"
            kit.mkdir()
            (kit / "kit.json").write_text(json.dumps({"what": "the cream tube"}))
            saved = (V2.R.product_gate, V2.R._load)
            calls = []

            class PP:
                @staticmethod
                def run(pic, kitdir, what="x"):
                    calls.append((pic, Path(kitdir).name, what))
                    return {"ok": False, "why": ["the drawn thing does not match the real product at any angle"]}
            try:
                V2.R.product_gate = lambda refs, iid="?": ("b", "s", kit / "kit.json")
                V2.R._load = lambda name: PP if name == "product_paste" else saved[1](name)
                it = {}
                V2.R.product_of(it, {"file": "S8-F1.png"}, "S8-F1", "", ["packshot.jpg"], None, False)
            finally:
                V2.R.product_gate, V2.R._load = saved
        self.assertEqual(calls, [("S8-F1.png", "kit", "the cream tube")])
        self.assertFalse(it["product_paste"]["ok"], "recorded, so the reviewer holds the picture")

    def test_the_review_and_the_judge_name_the_real_product(self):
        rv = (HERE.parent / "prompts" / "v2" / "picture-review-v6-owner.md").read_text()
        self.assertIn("Not the real product", rv)
        self.assertIn("loofah", rv)
        cj = (HERE.parent / "prompts" / "v2" / "clip-judge-v4-owner.md").read_text()
        self.assertIn("The real product stays real", cj)


class SilentShot(unittest.TestCase):
    """P70 (2026-10-21, V14): a wordless B-roll shot ("no words, music only") passes the brief contract with an empty
    voice, has no read, and claims no slice; a talking or spoken-over scene with an empty voice is still refused."""

    def setUp(self):
        import importlib.util as u
        sp = u.spec_from_file_location("vm_t_mi_p70", HERE / "model_inputs.py")
        self.MI = u.module_from_spec(sp); sp.loader.exec_module(self.MI)

    def _faults(self, sc):
        out = []
        self.MI._keys("scene S2", sc, ["id", "voice"], out)
        return out

    def test_a_wordless_broll_shot_passes_with_no_voice(self):
        sc = {"id": "S2", "to_camera": False, "speaker": "", "voice": "", "kind": "broll"}
        self.assertTrue(self.MI.is_silent_shot(sc))
        self.assertEqual(self._faults(sc), [])

    def test_an_empty_voice_with_a_speaker_or_to_camera_is_still_refused(self):
        for sc in ({"id": "S2", "to_camera": False, "speaker": "YAI", "voice": ""},
                   {"id": "S2", "to_camera": True, "speaker": "", "voice": ""},
                   {"id": "S2", "speaker": "", "voice": ""}):          # to_camera unsaid is never silent
            self.assertFalse(self.MI.is_silent_shot(sc), sc)
            self.assertTrue(any("'voice' is empty" in f for f in self._faults(sc)), sc)

    def test_a_silent_shot_gets_no_line_to_read(self):
        src = (HERE / "run.py").read_text()
        self.assertIn("and not mi.is_silent_shot(s)}", src)
        self.assertFalse(self.MI.is_silent_shot({"id": "S2", "to_camera": False, "speaker": "", "voice": "x"}))


class AgnosticPrompts(unittest.TestCase):
    """P72 (the owner, 2026-10-21: "this needs to be brand agnostic … product-brand-avatar-scene-setting agnostic"): the
    review, the clip judge and the picture-edit words name no brand, product, cast member or set — every one of those
    is read per run from the run's own files. The names checked are read from the data folders, never listed here."""

    def _names(self):
        ws = HERE.parents[2]
        out = set()
        for b in (ws / "brands").iterdir():
            if b.is_dir() and not b.name.startswith((".", "_")):
                out.add(b.name)
                prods = b / "products"
                if prods.is_dir():
                    out |= {p.name for p in prods.iterdir() if p.is_dir() and len(p.name) > 3 and (p / "product.md").is_file()}
        ae = ws / "runs" / "ai-elements"
        if ae.is_dir():
            for b in ae.iterdir():
                for kind in ("casting", "sets"):
                    f = b / kind
                    if f.is_dir():
                        out |= {p.name for p in f.iterdir() if p.is_dir() and len(p.name) > 2
                                and any((p / n).is_file() for n in ("character.md", "set.md", "spec.json"))}
        return {n.lower().replace("-", " ") for n in out} | {n.lower() for n in out}

    def _texts(self):
        cfg = json.loads((HERE / "v2.json").read_text())
        ws = HERE.parents[2]
        ER = __import__("importlib.util").util
        sp = ER.spec_from_file_location("vm_t_er_p72", HERE / "element_refs.py")
        er = ER.module_from_spec(sp); sp.loader.exec_module(er)
        yield "review", (ws / cfg["review"]["prompt"]).read_text().split("\n", 3)[-1]      # past the title + history line
        cj = (HERE.parent / "prompts" / "v2" / "clip-judge-v4-owner.md").read_text()
        yield "clip judge", cj.split("\n", 3)[-1]
        for k in ("SWIPE_EDIT", "PRODUCT_NONE", "PRODUCT_HELD", "NO_PRODUCT"):
            yield k, getattr(er, k)

    def test_no_brand_product_person_or_set_name_in_the_prompts(self):
        import re as _re
        names = self._names()
        self.assertTrue(names, "the data folders were read")
        for where, text in self._texts():
            low = text.lower()
            hits = sorted(n for n in names if _re.search(r"\b" + _re.escape(n) + r"\b", low))
            self.assertEqual(hits, [], f"{where} names {hits}")

    def test_the_review_gets_the_presenters_culture_and_the_banked_dressing_from_the_runs_files(self):
        import importlib.util as u
        sp = u.spec_from_file_location("vm_t_v2_p72", HERE / "run_v2.py")
        src = (HERE / "run_v2.py").read_text()
        self.assertIn("def _presenter_culture(", src)
        self.assertIn("def _banked_set(", src)
        rv = (HERE.parent / "prompts" / "v2" / "picture-review-v8-owner.md").read_text()
        self.assertIn("Another culture's room", rv)
        with tempfile.TemporaryDirectory() as t:
            run = Path(t)
            # a person and a set made up for the test only, written into the run's own files
            pdir = run / "p"; sdir = run / "s"; pdir.mkdir(); sdir.mkdir()
            (pdir / "character.md").write_text("# x\n\n- **Culture:** Culture-Q, home decor of Culture-Q\n")
            (sdir / "set.md").write_text("# s\n\nA plain room with one window.\n\n- Dressing (must be in frame): a Q-script card\n")
            # an absolute folder: the run's element sheet may name one (ws / absolute is the absolute path)
            (run / "elements.json").write_text(json.dumps({"items": [
                {"kind": "person", "folder": str(pdir)}, {"kind": "setting", "folder": str(sdir)}]}))
            V = u.module_from_spec(sp); sp.loader.exec_module(V)
            self.assertIn("Culture-Q", V._presenter_culture(run))
            b = V._banked_set(run)
            self.assertEqual(b["description"], "A plain room with one window.")
            self.assertEqual(b["dressing"], "a Q-script card")


class SplitScenePicture(unittest.TestCase):
    """P73 (2026-10-21, a split scene stopped production: "production has no item S4-F1"): the storyboard's picture for
    a split scene is its LEFT side's item, made under the scene's own id; a scene with no item is still a problem."""

    def test_the_left_side_is_the_scenes_picture(self):
        import importlib.util as u
        sp = u.spec_from_file_location("vm_t_sb_p73", HERE / "storyboard_plan.py")
        SB = u.module_from_spec(sp); sp.loader.exec_module(SB)
        plan = {"sections": [{"id": "G03", "frames": [{"from": "S4", "what": "start frame"}], "swipe": {"shots": []}},
                             {"id": "G04", "frames": [{"from": "S9", "what": "start frame"}], "swipe": {"shots": []}}]}
        items = [{"id": "S4L-F1", "kind": "still", "split": {"of": "S4", "side": "left"}, "params": {"prompt": "l"}},
                 {"id": "S4R-F1", "kind": "still", "split": {"of": "S4", "side": "right"}, "params": {"prompt": "r"}}]
        keep, problems = SB.picture_jobs(plan, items)
        self.assertEqual([k["id"] for k in keep], ["S4-F1"])
        self.assertEqual(keep[0]["params"]["prompt"], "l")
        self.assertEqual(len(problems), 1)
        self.assertIn("production has no item S9-F1", problems[0])

class ReviewerSeesTheLook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.V2 = RunV2.V2 if hasattr(RunV2, "V2") else None
        if cls.V2 is None:
            RunV2.setUpClass(); cls.V2 = RunV2.V2

    def test_the_reviewer_always_sees_each_persons_look(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            files = [d / "framemap/K39.jpg"] + [d / "casting/m/full" / n for n in ("master.png",)] + \
                    [d / "casting/m/full/sheets" / n for n in ("turnaround.png", "angles-expressions.png", "details.png",
                                                              "look-2-grey-suit.jpg")]
            for f in files:
                f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(b"x")
            it = {"medias": [{"role": "image_references", "value": str(f)} for f in files]}
            saved = (self.V2.R._named_ref, self.V2._prop_pictures)
            try:
                self.V2.R._named_ref = lambda run, v, it, brand: Path(v)
                self.V2._prop_pictures = lambda *a: []
                got = [f.name for f in self.V2._refs_of(d, it, "_fixture")]
            finally:
                self.V2.R._named_ref, self.V2._prop_pictures = saved
            self.assertEqual(got[:3], ["K39.jpg", "master.png", "look-2-grey-suit.jpg"])
            self.assertEqual(len(got), 4)


if __name__ == "__main__":
    unittest.main()
