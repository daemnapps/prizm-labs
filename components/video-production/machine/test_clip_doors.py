#!/usr/bin/env python3
"""The clip doors fall through (seedance._send, 2026-11-20): a call goes to the first door; a door out of credits, not
signed in or refusing before anything is sent passes it on; a request already sent is never sent on another door.
Fake doors only; nothing is called.

    python3 components/video-production/machine/test_clip_doors.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seedance as SD  # noqa: E402
import higgsfield_cli as CLI  # noqa: E402


class Door:
    def __init__(self, name, ready=(True, 100.0), submit_error=None):
        self.name, self._ready, self.submit_error, self.sent = name, ready, submit_error, []

    def ready(self):
        return self._ready

    def upload(self, p):
        return f"{self.name}://{Path(p).name}"

    def submit(self, path, payload):
        if self.submit_error:
            raise RuntimeError(self.submit_error)
        self.sent.append(payload)
        return f"{self.name}-job"

    def wait(self, rid):
        return {"status": "completed"}

    def outputs(self, body):
        return ["http://x/clip.mp4"]

    def download(self, url, dest):
        Path(dest).write_bytes(b"mp4")
        return 3


class ClipDoors(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="doors_"))
        (self.d / "s.png").write_bytes(b"png")
        self.out = self.d / "clip.mp4"
        p = mock.patch.dict(os.environ, {"VP_CLIP_DOORS": "account,key"})
        p.start()
        self.addCleanup(p.stop)

    def send(self, mods):
        return SD._send("bytedance/seedance-2.5/image-to-video", {"prompt": "p", "duration": 5},
                        {"image_url": self.d / "s.png"}, self.out, door_mods=mods)

    def test_the_first_door_with_credits_takes_the_call(self):
        acct, key = Door("account"), Door("key")
        r = self.send({"account": acct, "key": key})
        self.assertEqual(r["door"], "account")
        self.assertEqual(acct.sent[0]["image_url"], "account://s.png")
        self.assertEqual(key.sent, [])
        saved = json.loads(self.out.with_suffix(".request.json").read_text())
        self.assertEqual((saved["door"], saved["seconds"], saved["state"]), ("account", 5, "completed"))

    def test_a_door_out_of_credits_passes_the_call_on(self):
        acct = Door("account", submit_error='submit refused — HTTP 403: {"detail": "not_enough_credits"}')
        key = Door("key")
        r = self.send({"account": acct, "key": key})
        self.assertEqual(r["door"], "key")
        self.assertEqual(len(key.sent), 1)

    def test_a_door_not_signed_in_is_skipped(self):
        acct, key = Door("account", ready=(False, "not signed in")), Door("key")
        self.assertEqual(self.send({"account": acct, "key": key})["door"], "key")

    def test_every_door_refused_names_each_reason(self):
        acct = Door("account", submit_error="HTTP 403 not_enough_credits")
        key = Door("key", submit_error="HTTP 403 not_enough_credits")
        with self.assertRaises(RuntimeError) as e:
            self.send({"account": acct, "key": key})
        self.assertIn("account:", str(e.exception))
        self.assertIn("key:", str(e.exception))

    def test_a_request_already_sent_resumes_on_its_own_door_only(self):
        self.out.with_suffix(".request.json").write_text(json.dumps(
            {"request_id": "key-job", "state": "submitted", "door": "key",
             "fingerprint": SD.hashlib.sha256(json.dumps(["bytedance/seedance-2.5/image-to-video",
                                                          {"prompt": "p", "duration": 5, "image_url": "key://s.png"}],
                                                         sort_keys=True).encode()).hexdigest()}))
        acct, key = Door("account"), Door("key")
        r = self.send({"account": acct, "key": key})
        self.assertEqual(r["door"], "key")
        self.assertEqual(acct.sent + key.sent, [])                  # waited on, never sent again

    def test_the_account_is_the_only_door_unless_the_key_is_named(self):
        with mock.patch.dict(os.environ, {"VP_CLIP_DOORS": ""}):
            self.assertEqual(SD.doors(), ["account"])
            acct = Door("account", submit_error="HTTP 403 not_enough_credits")
            key = Door("key")
            with self.assertRaises(RuntimeError):
                self.send({"account": acct, "key": key})
            self.assertEqual(key.sent, [])

    def test_an_ended_checkpoint_never_pins_the_call_to_its_door(self):
        self.out.with_suffix(".request.json").write_text(json.dumps(
            {"request_id": "old", "state": "failed", "fingerprint": "x"}))      # an old run's, on the key
        acct = Door("account", submit_error="HTTP 403 not_enough_credits")
        key = Door("key")
        self.assertEqual(self.send({"account": acct, "key": key})["door"], "key")    # the account was asked first
        with mock.patch.dict(os.environ, {"VP_CLIP_DOORS": "account"}):
            self.out.with_suffix(".request.json").write_text(json.dumps(
                {"request_id": "old", "state": "failed", "fingerprint": "x"}))
            r = self.send({"account": Door("account"), "key": Door("key")})
            self.assertEqual(r["door"], "account")

    def test_an_uncertain_send_never_falls_through(self):
        acct = Door("account", submit_error="UNCERTAIN: accepted but named no job")
        key = Door("key")
        with self.assertRaises(RuntimeError):
            self.send({"account": acct, "key": key})
        self.assertEqual(key.sent, [])


class NeverTwice(unittest.TestCase):
    JOBS = [{"id": "run", "job_type": "seedance_2_5", "status": "in_progress", "created_at": "2026-11-20T11:59",
             "params": {"prompt": "p", "duration": 5}},
            {"id": "made", "job_type": "seedance_2_5", "status": "completed", "created_at": "2026-11-20T11:54",
             "params": {"prompt": "p", "duration": 5}},
            {"id": "bad", "job_type": "seedance_2_5", "status": "failed", "created_at": "2026-11-20T11:50",
             "params": {"prompt": "p", "duration": 5}},
            {"id": "other", "job_type": "seedance_2_5", "status": "completed", "created_at": "2026-11-20T11:50",
             "params": {"prompt": "q", "duration": 5}}]

    def test_the_same_request_already_made_is_taken_not_paid_again(self):
        self.assertEqual(CLI.find("bytedance/seedance-2.5/image-to-video", {"prompt": "p", "duration": 5},
                                  jobs=self.JOBS), "made")
        self.assertEqual(CLI.find("bytedance/seedance-2.5/image-to-video", {"prompt": "p", "duration": 5},
                                  jobs=self.JOBS[:1] + self.JOBS[2:3]), "run")
        self.assertIsNone(CLI.find("bytedance/seedance-2.5/image-to-video", {"prompt": "p", "duration": 6},
                                   jobs=self.JOBS))

    def test_a_command_that_errored_is_read_back_before_it_counts_as_refused(self):
        with mock.patch.object(CLI, "_run", return_value=(1, "", "HTTP 403 not_enough_credits")), \
                mock.patch.object(CLI, "recent", return_value=self.JOBS):
            self.assertEqual(CLI.submit("bytedance/seedance-2.5/image-to-video", {"prompt": "p", "duration": 5}), "made")

    def test_the_account_door_is_never_followed_by_another_after_its_command_ran(self):
        d = Path(tempfile.mkdtemp())
        (d / "s.png").write_bytes(b"png")
        acct = Door("account", submit_error="submit refused — command line: HTTP 403 not_enough_credits")
        acct.find = lambda path, payload: None
        key = Door("key")
        with mock.patch.dict(os.environ, {"VP_CLIP_DOORS": "account,key"}):
            with self.assertRaises(RuntimeError):
                SD._send("bytedance/seedance-2.5/image-to-video", {"prompt": "p", "duration": 5},
                         {"image_url": d / "s.png"}, d / "c.mp4", door_mods={"account": acct, "key": key})
        self.assertEqual(key.sent, [])

    def test_no_new_submit_takes_only_what_is_already_out(self):
        d = Path(tempfile.mkdtemp())
        (d / "s.png").write_bytes(b"png")
        acct = Door("account")
        acct.find = lambda path, payload: None
        with mock.patch.dict(os.environ, {"VP_CLIP_DOORS": "account", "VP_NO_NEW_SUBMIT": "1"}):
            with self.assertRaises(RuntimeError):
                SD._send("bytedance/seedance-2.5/image-to-video", {"prompt": "p", "duration": 5},
                         {"image_url": d / "s.png"}, d / "c.mp4", door_mods={"account": acct})
        self.assertEqual(acct.sent, [])


class CommandLine(unittest.TestCase):
    def test_a_talking_call_becomes_reference_mode_with_picture_voice_and_video(self):
        a = CLI.args_for("bytedance/seedance-2.5/reference-to-video",
                         {"prompt": "p", "duration": 7, "resolution": "480p", "aspect_ratio": "9:16",
                          "generate_audio": True, "image_urls": ["/a.png", "/b.png"], "audio_urls": ["/v.mp3"],
                          "video_urls": ["/m.mp4"]})
        self.assertEqual(a[:3], ["generate", "create", "seedance_2_5"])
        self.assertIn("omni_reference", a)
        self.assertEqual([a[i + 1] for i, x in enumerate(a) if x == "--image-references"], ["/a.png", "/b.png"])
        self.assertEqual(a[a.index("--audio-references") + 1], "/v.mp3")
        self.assertEqual(a[a.index("--video-references") + 1], "/m.mp4")
        self.assertEqual(a[a.index("--generate_audio") + 1], "true")

    def test_a_silent_call_starts_on_its_picture(self):
        a = CLI.args_for("bytedance/seedance-2.5/image-to-video",
                         {"prompt": "p", "duration": 5, "resolution": "480p", "generate_audio": False,
                          "image_url": "/s.png", "end_image_url": "/e.png"})
        self.assertEqual(a[a.index("--start-image") + 1], "/s.png")
        self.assertEqual(a[a.index("--end-image") + 1], "/e.png")
        self.assertEqual(a[a.index("--aspect-ratio") + 1], "auto")
        self.assertEqual(a[a.index("--generate_audio") + 1], "false")

    def test_a_job_id_is_read_from_a_list_or_a_line(self):
        self.assertEqual(CLI._job_id('[{"id": "j1", "status": "queued"}]'), "j1")
        self.assertEqual(CLI._job_id("job 6b8c66a8-75ed-4514-a529-6e95b6aaa1f4 queued"),
                         "6b8c66a8-75ed-4514-a529-6e95b6aaa1f4")
        self.assertIsNone(CLI._job_id("ok"))


if __name__ == "__main__":
    unittest.main()
