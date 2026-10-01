#!/usr/bin/env python3
"""python3 machine/test_voice.py — from any cwd. Stdlib unittest only.

Never reads brands/ — every character home is a temp `--cast-root`, so this
suite says nothing about, and depends on nothing in, the real cast."""
from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


voice = load("voice")


def run_quiet(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = fn(*a, **kw)
    return code, buf.getvalue()


def fake_transport(method, url, body, headers):
    assert method == "POST"
    return f"FAKE-AUDIO:{body['text']}".encode()


class FakeTimestamps:
    """The with-timestamps door, faked: one alignment row per character at a
    tenth of a second each, and a `request-id` header per call — which is
    what the next call has to be stitched onto."""

    def __init__(self):
        self.calls = []
        self.n = 0

    def __call__(self, method, url, body, headers):
        assert method == "POST"
        assert "with-timestamps" in url, url
        self.n += 1
        self.calls.append({"url": url, "body": json.loads(json.dumps(body))})
        text = body["text"]
        starts = [round(i * 0.1, 3) for i in range(len(text))]
        ends = [round((i + 1) * 0.1, 3) for i in range(len(text))]
        payload = {
            "audio_base64": base64.b64encode(f"AUDIO:{text}".encode()).decode(),
            "alignment": {"characters": list(text),
                          "character_start_times_seconds": starts,
                          "character_end_times_seconds": ends},
        }
        return json.dumps(payload).encode(), {"request-id": f"rid-{self.n}"}


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-voice-"))
        self.run = self.tmp / "run1"
        self.run.mkdir()
        voice.write_json(self.run / "run.json", {"brand": "_fixture", "label": "run1"})
        voice.write_json(self.run / "plan.json", {"cast": {"name": "Lead"}})
        voice.write_json(self.run / "lines.json", {"A1": "first line", "A2": "second line"})
        self.cast_root = self.tmp / "cast"
        self.home = self.cast_root / "lead"
        self.home.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def bind(self, rec, home=None):
        voice.write_json((home or self.home) / "voice.json", rec)

    def test_dry_run_writes_nothing(self):
        self.bind({"voice_id": "abc123", "model_id": "eleven_multilingual_v2"})
        code, out = run_quiet(voice.main, [str(self.run), "--cast-root", str(self.cast_root),
                                            "--dry-run"])
        self.assertEqual(code, 0, out)
        self.assertIn("abc123", out)
        self.assertFalse((self.run / "voice").exists())

    def test_dry_run_still_refuses_a_preset_only_voice(self):
        self.bind({"voice": "Matilda"})
        code, out = run_quiet(voice.main, [str(self.run), "--cast-root", str(self.cast_root),
                                            "--dry-run"])
        self.assertEqual(code, 2, out)
        self.assertIn("fal library preset", out)
        self.assertFalse((self.run / "voice").exists())

    def test_generates_every_line_with_fake_transport(self):
        self.bind({"voice_id": "abc123", "stability": 0.4})
        manifest = voice.run_for(self.run, cast_root=str(self.cast_root),
                                  transport=fake_transport, key="test-key")
        self.assertEqual(set(manifest), {"A1", "A2"})
        for lid in ("A1", "A2"):
            f = self.run / manifest[lid]["file"]
            self.assertTrue(f.is_file())
            self.assertEqual(manifest[lid]["voice_id"], "abc123")
            self.assertIn("at", manifest[lid])
        self.assertTrue((self.run / "voice" / "manifest.json").is_file())
        on_disk = json.loads((self.run / "voice" / "manifest.json").read_text())
        self.assertEqual(on_disk, manifest)

    def test_refuses_a_fal_preset_only_voice(self):
        self.bind({"voice": "Matilda", "provider": "elevenlabs (via fal)"})
        with self.assertRaises(SystemExit) as ctx:
            voice.run_for(self.run, cast_root=str(self.cast_root), key="test-key")
        self.assertIn("fal library preset", str(ctx.exception))
        self.assertIn("2026-09-17", str(ctx.exception))

    def test_missing_voice_json_is_a_hard_stop(self):
        with self.assertRaises(SystemExit) as ctx:
            voice.run_for(self.run, cast_root=str(self.cast_root), key="test-key")
        self.assertIn("no voice.json", str(ctx.exception))

    def test_no_lines_is_a_clean_noop_and_needs_no_character(self):
        voice.write_json(self.run / "lines.json", {})
        manifest = voice.run_for(self.run, cast_root=str(self.cast_root), key="test-key")
        self.assertEqual(manifest, {})

    def test_character_flag_overrides_plan_cast_name(self):
        other = self.cast_root / "other"
        other.mkdir()
        self.bind({"voice_id": "zzz"}, home=other)
        manifest = voice.run_for(self.run, character="other", cast_root=str(self.cast_root),
                                  transport=fake_transport, key="test-key")
        self.assertEqual(manifest["A1"]["voice_id"], "zzz")

    def test_cli_main_reports_line_count_via_injected_transport(self):
        # main() itself takes no transport — it is the real CLI, real
        # network by default — so this exercises the CLI wiring (argument
        # parsing, exit code, the printed count) by monkeypatching the
        # module's own default rather than touching the network.
        self.bind({"voice_id": "abc123"})
        saved = voice.http_transport
        voice.http_transport = fake_transport
        try:
            code, out = run_quiet(voice.main, [str(self.run), "--cast-root", str(self.cast_root)])
        finally:
            voice.http_transport = saved
        self.assertEqual(code, 0, out)
        self.assertIn("2 line(s) voiced into", out)
        self.assertTrue((self.run / "voice" / "A1.mp3").is_file())

    def test_slugify(self):
        self.assertEqual(voice.slugify("Lead"), "lead")
        self.assertEqual(voice.slugify("Dr. Susan O'Neil"), "dr-susan-o-neil")
        self.assertEqual(voice.slugify(""), "")


class ContinuousTests(unittest.TestCase):
    """ONE read for the whole piece: one chunk per scene paragraph, stitched
    on the request ids, timed cumulatively, sliced per scene."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-vo-"))
        self.run = self.tmp / "run1"
        self.run.mkdir()
        voice.write_json(self.run / "run.json", {"brand": "_fixture", "label": "run1"})
        voice.write_json(self.run / "plan.json", {
            "shape": "scene", "cast": {"name": "Lead"},
            "scenes": [{"id": "S1", "frames": []}, {"id": "S2", "frames": []}]})
        voice.write_json(self.run / "lines.json", {
            "S1": "First sentence here. Second one lands.",
            "S2": "Third sentence now. And the last."})
        self.cast_root = self.tmp / "cast"
        self.home = self.cast_root / "lead"
        self.home.mkdir(parents=True)
        voice.write_json(self.home / "voice.json", {"voice_id": "abc123"})
        self.cuts = []
        self.saved_ffmpeg = voice.run_ffmpeg
        voice.run_ffmpeg = self.record_ffmpeg

    def record_ffmpeg(self, args):
        self.cuts.append(list(args))
        return False        # the fallback path writes the files, as on a machine with no ffmpeg

    def tearDown(self):
        voice.run_ffmpeg = self.saved_ffmpeg
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self):
        self.tr = FakeTimestamps()
        return voice.run_for(self.run, cast_root=str(self.cast_root),
                             transport=self.tr, key="test-key")

    def test_scene_shape_run_goes_continuous_by_itself(self):
        self.assertTrue(voice.is_scene_shape(self.run))

    def test_stitching_carries_the_request_ids_forward(self):
        self.make()
        bodies = [c["body"] for c in self.tr.calls]
        self.assertEqual(len(bodies), 2)
        self.assertNotIn("previous_request_ids", bodies[0])
        self.assertEqual(bodies[1]["previous_request_ids"], ["rid-1"])
        # stitching is not on v3 — the contract's own house default is sent
        self.assertEqual(bodies[0]["model_id"], voice.default_model_id())

    def test_a_scene_carrying_voice_settings_lays_them_over_the_cast_record(self):
        """The spoken pass (2026-09-19) writes stability / style / speed per
        scene from the register recipe; the cast record stays the base."""
        voice.write_json(self.home / "voice.json",
                         {"voice_id": "abc123", "stability": 0.5, "similarity_boost": 0.8})
        voice.write_json(self.run / "plan.json", {
            "shape": "scene", "cast": {"name": "Lead"},
            "scenes": [{"id": "S1", "frames": [],
                        "voice_settings": {"stability": 0.7, "speed": 0.95, "style": 0.05}},
                       {"id": "S2", "frames": []}]})
        self.make()
        bodies = [c["body"] for c in self.tr.calls]
        self.assertEqual(bodies[0]["voice_settings"],
                         {"stability": 0.7, "similarity_boost": 0.8, "speed": 0.95, "style": 0.05})
        self.assertEqual(bodies[1]["voice_settings"], {"stability": 0.5, "similarity_boost": 0.8})
        timing = json.loads((self.run / "vo" / "timing.json").read_text())
        self.assertEqual(timing["scenes"]["S1"]["voice_settings"]["stability"], 0.7)
        self.assertEqual(voice.scene_settings(self.run), {"S1": {"stability": 0.7, "speed": 0.95, "style": 0.05}})

    def test_never_more_ids_than_the_contract_allows(self):
        voice.write_json(self.run / "lines.json",
                         {f"S{i}": f"Line number {i} here." for i in range(1, 7)})
        self.make()
        cap = voice.stitch_depth()
        for body in [c["body"] for c in self.tr.calls][1:]:
            self.assertLessEqual(len(body["previous_request_ids"]), cap)
        self.assertEqual([c["body"] for c in self.tr.calls][-1]["previous_request_ids"],
                         ["rid-3", "rid-4", "rid-5"])

    def test_timing_is_cumulative_on_one_timeline(self):
        self.make()
        timing = json.loads((self.run / "vo" / "timing.json").read_text())
        s1, s2 = timing["scenes"]["S1"], timing["scenes"]["S2"]
        self.assertEqual(s1["start"], 0.0)
        self.assertAlmostEqual(s1["end"], s2["start"], places=3)
        self.assertAlmostEqual(timing["total"], s2["end"], places=3)
        # every sentence inside a scene, on the same one timeline
        self.assertEqual([l["text"] for l in s1["lines"]],
                         ["First sentence here.", "Second one lands."])
        self.assertGreater(s2["lines"][0]["start"], s1["end"] - 0.001)
        for row in s1["lines"] + s2["lines"]:
            self.assertLess(row["start"], row["end"])

    def test_the_track_and_a_slice_per_scene_exist(self):
        manifest = self.make()
        self.assertEqual(set(manifest), {"S1", "S2"})
        self.assertTrue((self.run / "vo" / "track.mp3").is_file())
        for sid in ("S1", "S2"):
            self.assertTrue((self.run / "vo" / f"{sid}.mp3").is_file())
            self.assertEqual(manifest[sid]["file"], f"vo/{sid}.mp3")

    def test_slices_are_cut_at_the_scene_bounds(self):
        self.make()
        timing = json.loads((self.run / "vo" / "timing.json").read_text())
        cuts = [c for c in self.cuts if "-ss" in c]
        self.assertEqual(len(cuts), 2)
        for sid, args in zip(("S1", "S2"), cuts):
            row = timing["scenes"][sid]
            self.assertEqual(args[args.index("-ss") + 1], f"{row['start']:.3f}")
            self.assertEqual(args[args.index("-to") + 1], f"{row['end']:.3f}")
            self.assertTrue(args[-1].endswith(f"{sid}.mp3"))

    def test_dry_run_writes_nothing_and_still_refuses_a_preset_voice(self):
        code, out = run_quiet(voice.main, [str(self.run), "--cast-root",
                                           str(self.cast_root), "--dry-run"])
        self.assertEqual(code, 0, out)
        self.assertIn("with-timestamps", out)
        self.assertFalse((self.run / "vo").exists())
        voice.write_json(self.home / "voice.json", {"voice": "SomePreset"})
        code, out = run_quiet(voice.main, [str(self.run), "--cast-root",
                                           str(self.cast_root), "--dry-run"])
        self.assertEqual(code, 2, out)

    def test_per_line_still_works_on_a_scene_shape_run(self):
        manifest = voice.run_for(self.run, cast_root=str(self.cast_root),
                                 transport=fake_transport, key="test-key",
                                 per_line=True)
        self.assertEqual(set(manifest), {"S1", "S2"})
        self.assertTrue((self.run / "voice" / "S1.mp3").is_file())
        self.assertFalse((self.run / "vo").exists())



class ForReadingTests(unittest.TestCase):
    """The take reads the doctrine's punctuation map (2026-09-19). A brief
    written before the spoken pass still gets its dashes read as commas."""

    def test_the_map_comes_from_the_doctrine_when_it_is_there(self):
        pm = voice.punctuation_map()
        if pm:
            marks = {m["mark"] for m in pm["marks"]}
            self.assertIn("—", marks)
            self.assertIn(",", marks)
            rules = voice.take_rules(pm)
            self.assertTrue(any(re.search(r["pattern"], "a — b") for r in rules), rules)
            self.assertEqual(voice.for_reading("Look (it works); it does... really — truly [laughs] now"),
                             "Look, it works. it does... really, truly now")

    def test_a_dash_becomes_a_comma_and_an_ellipsis_is_kept(self):
        # the ellipsis is the mid-thought breath (Damon, 2026-09-19) — kept
        self.assertEqual(
            voice.for_reading("This — the old surface — is why... it failed."),
            "This, the old surface, is why... it failed.")

    def test_the_fallback_rows_carry_the_take_without_the_doctrine(self):
        out = voice.for_reading("Now – go… please", rules=voice.FALLBACK_TAKE)
        self.assertEqual(out, "Now, go... please")

    def test_spoken_copy_passes_through_untouched(self):
        s = "It comes back, every time. Right? That's not the product failing."
        self.assertEqual(voice.for_reading(s), s)

if __name__ == "__main__":
    unittest.main()
