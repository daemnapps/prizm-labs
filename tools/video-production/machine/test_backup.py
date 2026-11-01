"""The backup clip (2026-10-26): Kling 4.0 behind Seedance, the Kling prompt, the Kling door, the rulebook's limits checked
in code before anything is sent. Fakes only: no network, no spend."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import clips_run as oc

HERE = Path(__file__).resolve().parent


def _load(name):
    sp = importlib.util.spec_from_file_location(f"t_bk_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


KP, KL, SD, CL = _load("kling_prompt"), _load("kling"), _load("seedance"), _load("clip_limits")
CFG = oc.route_cfg()
PEOPLE = {"LEAD": {"noun": "woman", "pron": "she", "poss": "her", "marks": "", "gestures": ""}}
SC = {"S1": {"id": "S1", "happens": "holds a jar to the lens", "voice": "Hi there.", "beats": [{"do": "opens the lid"}, {"do": "tilts the jar"}],
             "shots": [{"face": "eyes on the lens", "gestures": "slow nod", "camera_move": "hold", "emotion": "furious"}]}}


def call(talking=True, **kw):
    return {"id": "G01-C1", "scenes": ["S1"], "talking": talking, "duration": 5, "camera": "still", "people": ["LEAD"],
            "lines": [{"speaker": "LEAD", "on_camera": talking, "scene": "S1", "text": "Hi there."}],
            "start_frame": "S1-F1", "end_frame": None, "refs": [], **kw}


class LedgerFake:
    def __init__(self):
        self.d = {}

    def get(self, cid):
        return self.d.get(cid) or {}

    def put(self, cid, **kw):
        self.d.setdefault(cid, {}).update(kw)

    def spend(self, *a, **k):
        pass


class TheKlingPrompt(unittest.TestCase):
    def test_a_talking_call_becomes_a_silent_clip_with_the_mouth_closed(self):
        p = KP.build(call(), SC, PEOPLE, {}, "Native phone footage, handheld front camera.", "LEAD")["prompt"]
        self.assertIn("keeps the mouth closed and does not speak", p)
        self.assertNotIn("Hi there.", p)
        self.assertNotIn("Audio", p)
        self.assertNotIn("furious", p, "the emotion label is not sent")
        self.assertIn("eyes on the lens", p)
        self.assertNotIn("handheld", p, "a propped phone is not handheld")

    def test_the_four_parts_one_camera_line_and_the_two_negatives(self):
        r = KP.build(call(False), SC, PEOPLE, {}, "", "LEAD")
        p = r["prompt"]
        self.assertIn("0-", p)
        self.assertEqual(p.count("Camera:"), 1)
        self.assertIn("No subtitles. No on-screen text.", p)
        self.assertNotIn("cinematic", p.lower())


class TheKlingDoor(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        self.pic = self.d / "S1.png"
        self.pic.write_bytes(b"png")

    def tearDown(self):
        self.t.cleanup()

    def test_it_sends_the_picture_and_no_audio_and_says_which_model(self):
        sent = []

        class HF:
            def upload(self, p):
                return f"u/{Path(p).name}"

        orig = SD._make
        KL._load = lambda name, _l=KL._load: (type("S", (), {"_make": staticmethod(lambda path, payload, out, hf: sent.append((path, payload)) or {"request_id": "r", "file": str(out)})})
                                               if name == "seedance" else _l(name))
        try:
            r = KL.motion("a prompt", self.pic, self.d / "o.mp4", seconds=5, no_people=True, hf=HF())
        finally:
            del KL._load
        path, payload = sent[0]
        self.assertEqual(path, KL.PATH)
        self.assertEqual(payload["sound"], "off")
        self.assertNotIn("audio_url", payload)
        self.assertEqual(payload["resolution"], "720p")
        self.assertEqual(r["model"], "kling-4.0")

    def test_a_size_the_model_does_not_make_stops_before_anything_is_sent(self):
        with self.assertRaises(SystemExit):
            KL.motion("x", self.pic, self.d / "o.mp4", seconds=5, resolution="480p", no_people=True, dry_run=True)


class TheLimitsAreCheckedInCode(unittest.TestCase):
    def test_the_rulebook_is_the_one_source(self):
        L = CL.limits("seedance-2.5")
        self.assertEqual(L["duration_seconds"], [4, 30])
        import model_inputs as MI
        self.assertEqual(MI.station("talking")["limits"]["duration_seconds"], L["duration_seconds"])
        self.assertEqual(MI.station("motion")["limits"]["refs"]["images"], L["max_images"])

    def test_errors_stop_and_warnings_do_not(self):
        bad = CL.check("seedance-2.5", 40, "4k", images=["a.png"], measure=False)
        self.assertEqual({f["id"] for f in bad if f["level"] == "error"}, {"duration", "resolution"})
        with self.assertRaises(SystemExit) as e:
            CL.raise_on_errors(bad, "seedance")
        self.assertIn("duration", str(e.exception))
        warn = CL.check("seedance-2.5", 6, "480p", images=["a.png"] * 9, measure=False)
        self.assertEqual([f["level"] for f in warn], ["warn"])
        CL.raise_on_errors(warn)

    def test_the_seedance_door_refuses_a_call_outside_the_limits(self):
        with tempfile.TemporaryDirectory() as t:
            pic = Path(t) / "p.png"
            pic.write_bytes(b"x")
            with self.assertRaises(SystemExit):
                SD.motion("x", pic, Path(t) / "o.mp4", seconds=12, resolution="4k", no_people=True, dry_run=True)


class TheFallback(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.run = Path(self.t.name)
        (self.run / "media").mkdir()
        (self.run / "media" / "S1-F1.png").write_bytes(b"png")
        (self.run / "clips").mkdir()
        self.saved = (oc.make_backup, oc.finish)
        oc.finish = lambda run, c, cfg, led, shipped, final, d, key=None: (Path(final).parent.mkdir(parents=True, exist_ok=True),
                                                                          Path(final).write_bytes(Path(shipped).read_bytes()))

    def tearDown(self):
        oc.make_backup, oc.finish = self.saved
        self.t.cleanup()

    def failing(self, run, c, cfg, led, people):
        raise RuntimeError("Seedance refused it")

    def backup_ok(self, run, c, cfg, led, people, why):
        f = Path(c["final"])
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"kling")
        led.put(c["id"], model="kling-4.0", engine="kling", fallback=True, fallback_reason=why, lip_sync=False, file=str(f), status="done")
        return {"file": str(f)}

    def run_it(self, cfg_over=None, judge_pass=True, talking=False):
        judge = lambda *a: {"score": 7, "pass": judge_pass, "problems": [{"what": "lips"}] if not judge_pass else []}
        led = LedgerFake()
        cfg = {**CFG, "takes": 1, "max_tries": 2, **(cfg_over or {})}
        got = oc.make_picked(self.run, {"id": "G01-C1", "start_frame": "S1-F1", "talking": talking, "voice_parts": [{"scene": "S1", "line": "Hi."}],
                                        "lines": [{"scene": "S1", "on_camera": True, "text": "Hi."}]},
                            cfg, led, {}, make=self.failing, judge=judge)
        return got, led

    def test_when_the_takes_fail_the_same_scene_goes_to_the_backup_and_the_ledger_says_so(self):
        oc.make_backup = self.backup_ok
        got, led = self.run_it()
        self.assertEqual(got["status"], "done")
        self.assertEqual(got["model"], "kling-4.0")
        self.assertTrue(got["fallback"])
        self.assertFalse(got["lip_sync"])
        self.assertIn("refused", got["fallback_reason"])
        picks = json.loads((self.run / "clips" / "picks.json").read_text())
        self.assertEqual(picks["G01-C1"]["picked"], "backup")

    def test_a_backup_that_fails_its_check_is_still_kept_when_it_scores_best(self):
        oc.make_backup = self.backup_ok
        got, led = self.run_it(judge_pass=False)
        self.assertEqual(got["status"], "done")
        self.assertTrue(got["below_criteria"])
        self.assertEqual(got["picked"], "backup", "the only attempt that made a file")

    def test_a_backup_that_cannot_be_made_is_said_when_nothing_else_was_made(self):
        oc.make_backup = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Kling is down too"))
        with self.assertRaises(RuntimeError) as e:           # no Seedance attempt made a file either: nothing to keep
            self.run_it()
        self.assertIn("Kling is down too", str(e.exception))

    def test_a_talking_clip_never_goes_to_the_backup(self):
        """The backup takes no audio, so a talking clip made there would have no voice."""
        oc.make_backup = self.backup_ok
        with self.assertRaises(RuntimeError):
            self.run_it(talking=True)

    def test_switched_off_the_backup_is_never_tried(self):
        oc.make_backup = lambda *a, **k: (_ for _ in ()).throw(AssertionError("backup must not run"))
        with self.assertRaises(RuntimeError) as e:
            self.run_it({"backup": {"enabled": False}})
        self.assertIn("no attempt made a clip", str(e.exception))


if __name__ == "__main__":
    unittest.main()
