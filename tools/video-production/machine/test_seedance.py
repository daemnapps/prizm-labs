"""The Seedance door (2026-10-23): picture + voice in one call, the face gate first. No network — the Higgsfield door is a stub."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    sp = importlib.util.spec_from_file_location(f"t_sd_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


SD = _load("seedance")


class StubHF:
    def __init__(self):
        self.sent = []

    def upload(self, p):
        return f"https://up/{Path(p).name}"

    def submit(self, path, payload):
        self.sent.append((path, payload))
        return "rid"

    def wait(self, rid):
        return {"status": "completed", "video": {"url": "https://out/v.mp4"}}

    def outputs(self, body):
        return [body["video"]["url"]]

    def download(self, url, dest):
        Path(dest).write_bytes(b"video")
        return 5


def same(picture, masters):
    return [{"master": m, "verdict": "SAME", "votes": ["SAME"] * 3, "why": "stub"} for m in masters]


def different(picture, masters):
    return [{"master": m, "verdict": "DIFFERENT", "votes": ["DIFFERENT"] * 3, "why": "stub"} for m in masters]


class Door(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.still = self.d / "C.png"; self.still.write_bytes(b"pic")
        self.voice = self.d / "line.mp3"; self.voice.write_bytes(b"mp3")
        self.master = self.d / "casting" / "p" / "full" / "master.png"
        self.master.parent.mkdir(parents=True); self.master.write_bytes(b"m")

    def test_talking_clip_sends_picture_and_voice_together_at_480p(self):
        hf = StubHF()
        r = SD.talk("It is NOT the razor.", self.still, self.voice, self.d / "out.mp4", seconds=5,
                    masters=[self.master], hf=hf, face_check=same)
        path, payload = hf.sent[0]
        self.assertEqual(path, SD.TALK)
        self.assertEqual(payload["image_urls"], ["https://up/C.png"])
        self.assertEqual(payload["audio_urls"], ["https://up/line.mp3"])
        self.assertEqual(payload["resolution"], "480p")
        self.assertEqual(payload["aspect_ratio"], "9:16")
        self.assertIn("Audio 1 is the speaker's voice", payload["prompt"])
        self.assertNotIn("It is NOT the razor.", payload["prompt"], "the words are in the audio, never typed beside it")
        self.assertTrue(Path(r["file"]).is_file())

    def test_a_motion_reference_rides_with_the_picture_and_voice(self):
        hf = StubHF()
        ref = self.d / "swipe.mp4"; ref.write_bytes(b"v")
        SD.talk("line", self.still, self.voice, self.d / "out.mp4", seconds=5, masters=[self.master], hf=hf,
                face_check=same, videos=[ref])
        self.assertEqual(hf.sent[0][1]["video_urls"], ["https://up/swipe.mp4"])
        self.assertEqual(hf.sent[0][1]["audio_urls"], ["https://up/line.mp3"])

    def test_a_silent_clip_with_a_motion_reference_is_reference_mode_not_image_to_video(self):
        hf = StubHF()
        ref = self.d / "swipe.mp4"; ref.write_bytes(b"v")
        SD.motion("hands move", self.still, self.d / "out.mp4", seconds=5, no_people=True, hf=hf, videos=[ref])
        path, payload = hf.sent[0]
        self.assertEqual(path, SD.TALK)
        self.assertEqual(payload["image_urls"], ["https://up/C.png"])
        self.assertEqual(payload["video_urls"], ["https://up/swipe.mp4"])
        self.assertFalse(payload["generate_audio"])
        hf2 = StubHF()
        SD.motion("hands move", self.still, self.d / "o2.mp4", seconds=5, no_people=True, hf=hf2)
        self.assertEqual(hf2.sent[0][0], SD.MOTION)

    def test_a_wrong_face_never_reaches_seedance(self):
        hf = StubHF()
        with self.assertRaises(SystemExit):
            SD.talk("line", self.still, self.voice, self.d / "out.mp4", masters=[self.master], hf=hf, face_check=different)
        self.assertEqual(hf.sent, [])

    def test_no_voice_no_talking_clip(self):
        with self.assertRaises(SystemExit):
            SD.talk("line", self.still, self.d / "missing.mp3", self.d / "o.mp4", masters=[self.master],
                    hf=StubHF(), face_check=same)

    def test_silent_clip_from_the_picture(self):
        hf = StubHF()
        SD.motion("the crowd stands", self.still, self.d / "m.mp4", seconds=3, no_people=True, hf=hf)
        path, payload = hf.sent[0]
        self.assertEqual(path, SD.MOTION)
        self.assertEqual(payload["duration"], 4)              # Seedance's floor
        self.assertFalse(payload["generate_audio"])

    def test_length_bounds(self):
        self.assertEqual(SD.span(2), 4)
        self.assertEqual(SD.span(12.2), 13)
        self.assertEqual(SD.span(45), 30)

    def test_interrupted_wait_resumes_same_paid_request(self):
        hf = StubHF(); calls = []
        wait = hf.wait
        def interrupted(rid):
            calls.append(rid)
            if len(calls) == 1: raise TimeoutError('connection interrupted')
            return wait(rid)
        hf.wait = interrupted
        out = self.d / 'recover.mp4'
        with self.assertRaises(TimeoutError): SD._make('model', {'prompt': 'same'}, out, hf)
        self.assertTrue(out.with_suffix('.request.json').is_file())
        SD._make('model', {'prompt': 'same'}, out, hf)
        self.assertEqual(len(hf.sent), 1)
        self.assertEqual(calls, ['rid', 'rid'])

    def test_recovery_refuses_changed_inputs_before_second_spend(self):
        hf = StubHF()
        def interrupted(rid): raise TimeoutError('interrupted')
        hf.wait = interrupted; out = self.d / 'held.mp4'
        with self.assertRaises(TimeoutError): SD._make('model', {'prompt': 'first'}, out, hf)
        with self.assertRaisesRegex(RuntimeError, 'different inputs'):
            SD._make('model', {'prompt': 'changed'}, out, hf)
        self.assertEqual(len(hf.sent), 1)


if __name__ == "__main__":
    unittest.main()
