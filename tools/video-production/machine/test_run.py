#!/usr/bin/env python3
"""python3 machine/test_run.py — from any cwd. Stdlib unittest only.

No provider or model slug is written here as a literal branch condition in
run.py or providers_fal.py; the closing check in this file grep-tests both
against providers.json's own model list to hold that."""

from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run = load("run")
platform = load("platform")
preflight = load("preflight")
providers_fal = load("providers_fal")
REG = json.loads((HERE / "providers.json").read_text())


@contextlib.contextmanager
def env(**extra):
    saved = dict(os.environ)
    saved_mod = sys.modules.get("daemn_keys")
    os.environ.update(extra)
    sys.modules["daemn_keys"] = types.SimpleNamespace(key=lambda name, required=False: "")
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)
        if saved_mod is None:
            sys.modules.pop("daemn_keys", None)
        else:
            sys.modules["daemn_keys"] = saved_mod


def run_quiet(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = fn(*a, **kw)
    return code, buf.getvalue()


# ---------------------------------------------------------------- fakes

def fake_transport(method, url, body, headers):
    if method == "POST":
        return {"status_url": url + "/status", "response_url": url + "/result",
                "request_id": "job-" + url.rsplit("/", 1)[-1]}
    if "/status?logs=0" in url:
        return {"status": "COMPLETED"}
    if url.endswith("/result"):
        return {"video": {"url": "https://cdn.example.test/media/clip.mp4"}}
    raise AssertionError(f"unexpected transport call: {method} {url}")


def fake_download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    Path(dest).write_bytes(b"fake-media")


def fake_download_maybe_fail(url, dest):
    if "bad" in url:
        raise RuntimeError("connection refused")
    fake_download(url, dest)


def fake_voice_transport(method, url, body, headers):
    return f"FAKE-AUDIO:{body['text']}".encode()


class FakeTranscriber:
    """Records every call it sees; returns a fixed transcript — the same
    seam lineparity.check() takes for its real ElevenLabs call."""
    def __init__(self, text: str):
        self.text = text
        self.calls = []

    def __call__(self, method, url, headers, body):
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        return 200, {}, json.dumps({"text": self.text}).encode()


class TempRuns(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-run-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def start_args(self, **over):
        a = ["start", str(FIX / "run-plan.json"),
             "--brand", "_fixture", "--format", "fixture-format", "--label", "t1",
             "--bank", str(FIX / "bank.json"), "--runs-root", str(self.tmp),
             "--cast-root", str(FIX / "cast-root")]
        for k, v in over.items():
            flag = f"--{k.replace('_', '-')}"
            if v is True:
                a.append(flag)
            elif v is not False:
                a += [flag, str(v)]
        return run.build_parser().parse_args(a)

    def run_dir(self):
        return self.tmp / "video-machine" / "_fixture" / "t1"


class StartHiggsfield(TempRuns):
    def test_dry_run_writes_submit_sheet_no_ledger(self):
        a = self.start_args(provider="higgsfield-ui", yes=True, dry_run=True)
        code, out = run_quiet(run.cmd_start, a)
        self.assertEqual(code, 0, out)
        r = self.run_dir()
        self.assertTrue((r / "run.json").is_file())
        self.assertTrue((r / "lines.json").is_file())
        self.assertTrue((r / "batches").is_dir())
        self.assertTrue(any((r / "batches").glob("*.json")))
        self.assertTrue((r / "SUBMIT.md").is_file())
        self.assertFalse((r / "ledger.json").exists())
        self.assertFalse((r / "voice").exists())  # voice respects --dry-run too

    def test_real_run_voices_every_line_and_lists_them_in_submit_md(self):
        a = self.start_args(provider="higgsfield-ui", yes=True)
        code, out = run_quiet(run.cmd_start, a, voice_transport=fake_voice_transport)
        self.assertEqual(code, 0, out)
        r = self.run_dir()
        voice_files = sorted(p.name for p in (r / "voice").glob("*.mp3"))
        self.assertEqual(voice_files, ["A1.mp3", "A2.mp3"])
        manifest = json.loads((r / "voice" / "manifest.json").read_text())
        self.assertEqual(set(manifest), {"A1", "A2"})
        submit_md = (r / "SUBMIT.md").read_text()
        self.assertIn("## Voices", submit_md)
        self.assertIn("voice/A1.mp3", submit_md)
        # the talking item's own batch entry carries the line as an audio media
        batch = json.loads(next((r / "batches").glob("*.json")).read_text())
        by_id = {it["id"]: it for it in batch["items"]}
        self.assertIn({"role": "audio", "value": "voice/A1.mp3"}, by_id["A1"]["medias"])

    def test_run_json_never_overwrites_existing_keys(self):
        a = self.start_args(provider="higgsfield-ui", yes=True, dry_run=True)
        run_quiet(run.cmd_start, a)
        r = self.run_dir()
        run_json = json.loads((r / "run.json").read_text())
        run_json["opened"] = "STAY"
        (r / "run.json").write_text(json.dumps(run_json))
        run_quiet(run.cmd_start, a)
        self.assertEqual(json.loads((r / "run.json").read_text())["opened"], "STAY")


class StartFal(TempRuns):
    def test_dry_run_prints_bodies_no_ledger(self):
        a = self.start_args(provider="fal", dry_run=True)
        code, out = run_quiet(run.cmd_start, a)
        self.assertEqual(code, 0, out)
        self.assertIn('"prompt"', out)
        r = self.run_dir()
        self.assertFalse((r / "ledger.json").exists())
        self.assertFalse((r / "SUBMIT.md").exists())
        self.assertFalse((r / "voice").exists())  # voice respects --dry-run too

    def test_fake_transport_submits_downloads_and_ledgers(self):
        a = self.start_args(provider="fal")
        with env(FAL_KEY="test-key"):
            code, out = run_quiet(run.cmd_start, a, transport=fake_transport,
                                   download=fake_download, voice_transport=fake_voice_transport)
        self.assertEqual(code, 0, out)
        r = self.run_dir()
        voice_files = sorted(p.name for p in (r / "voice").glob("*.mp3"))
        self.assertEqual(voice_files, ["A1.mp3", "A2.mp3"])
        media = sorted(p.name for p in (r / "media").glob("*.mp4"))
        self.assertEqual(media, ["A1.mp4", "A2.mp4", "B1.mp4"])
        ledger_rows = json.loads((r / "ledger.json").read_text())
        self.assertEqual(len(ledger_rows), 3)
        self.assertTrue(all(row["status"] == "done" for row in ledger_rows))

        reg = platform.registry()
        motion_slug = reg["providers"]["fal"]["stations"]["motion"]
        model = reg["models"][motion_slug]
        expected = sum(platform.estimate(model, secs, reg, resolution="1080p")["usd"] or 0
                       for secs in (6, 5, 4))
        totals = preflight.totals(ledger_rows)
        self.assertAlmostEqual(totals["grand_usd"], round(expected, 3), places=3)

        results = json.loads((r / "results.json").read_text())
        self.assertEqual(set(results), {"A1", "A2", "B1"})

    def test_refusal_when_item_names_no_resolvable_kind(self):
        # the 2026-09-17 streamlining fills every station on every provider
        # (down to a candidate), so there is no longer a real gap to derive —
        # a kind absent from station_of_kind is still a clean refusal path
        reg = platform.registry()
        fal = reg["providers"]["fal"]
        self.assertTrue(all(fal["stations"].get(s) is not None for s in reg["stations"]),
                         "expected every fal station to be filled by the 2026-09-17 table")
        item = {"id": "V1", "kind": "not-a-real-kind", "params": {}, "characters": [], "products": []}
        slug, refusal = platform.resolve_model(item, fal, reg)
        self.assertIsNotNone(refusal)


class StartMachineHand(TempRuns):
    """The two hands (Damon's 2026-09-17 ruling): cast/still/edit/song run
    direct, before the editor sees anything. This plan is its own fixture
    (not fixtures/run-plan.json) so the existing fal/Higgsfield tests above,
    which assert exact media/ledger counts, are never affected by it."""

    def make_plan(self) -> Path:
        # Reference images live in self.tmp, made on the fly — never as
        # committed fixture binaries, since **/*.png is gitignored
        # (workspace rule 3) and a file only on this machine would silently
        # break the test on a fresh clone.
        ref1 = self.tmp / "cast-ref.png"
        ref2 = self.tmp / "packshot-ref.png"
        ref1.write_bytes(b"fake-cast-sheet-bytes")
        ref2.write_bytes(b"fake-packshot-bytes")
        plan = {
            "brand": "_fixture",
            "cast": {
                "name": "Lead", "resolution": "1080p",
                "face": "00000000-0000-4000-8000-0000000000c1",
                "hands": "", "room": "00000000-0000-4000-8000-0000000000e1",
                "presenter": "LEAD", "who": "speaking to camera", "says": "She says",
                "voice": "00000000-0000-4000-8000-0000000000f1",
                "also": [], "alternates": {}, "elements": [],
            },
            "scenes": [
                {"id": "A1", "name": "opens on her hands", "seconds": 6, "line": "first line",
                 "delivery": "[confident]", "gesture": "She lifts one hand.",
                 "generate": {"kind": "still", "prompt": "A still of her, cast sheet then packshot.",
                              "references": [str(ref1), str(ref2)]},
                 "revoice": {}},
                {"id": "A2", "name": "closes to camera", "seconds": 5, "line": "second line",
                 "delivery": "[amused]", "gesture": "She tilts her head.",
                 "generate": {}, "revoice": {}},
            ],
            "cutaways": [],
            "song": {"prompt": "A short vocal-forward song about the product.", "clip": True},
            "overrides": {},
        }
        p = self.tmp / "plan-machine-hand.json"
        p.write_text(json.dumps(plan))
        return p

    def start_args(self, source: Path, **over):
        a = ["start", str(source),
             "--brand", "_fixture", "--format", "fixture-format", "--label", "t1",
             "--bank", str(FIX / "bank.json"), "--runs-root", str(self.tmp),
             "--cast-root", str(FIX / "cast-root")]
        for k, v in over.items():
            flag = f"--{k.replace('_', '-')}"
            if v is True:
                a.append(flag)
            elif v is not False:
                a += [flag, str(v)]
        return run.build_parser().parse_args(a)

    @staticmethod
    def fake_openai(method, url, headers, body):
        payload = {"data": [{"b64_json": base64.b64encode(b"fake-png").decode()}]}
        return 200, {"x-request-id": "req-1"}, json.dumps(payload).encode()

    @staticmethod
    def fake_google(method, url, headers, body):
        if "gemini-3-pro-image" in url:
            payload = {"candidates": [{"content": {"parts": [
                {"inlineData": {"mimeType": "image/png",
                                "data": base64.b64encode(b"fake-png").decode()}}]}}]}
        else:
            payload = {"candidates": [{"content": {"parts": [
                {"inlineData": {"mimeType": "audio/wav",
                                "data": base64.b64encode(b"fake-wav").decode()}},
                {"text": "[0:00] verse one"},
            ]}}]}
        return 200, {}, json.dumps(payload).encode()

    def test_real_run_produces_media_direct_json_and_linked_submit_md(self):
        a = self.start_args(self.make_plan(), provider="higgsfield-ui", yes=True)
        code, out = run_quiet(run.cmd_start, a, voice_transport=fake_voice_transport,
                               openai_transport=self.fake_openai, google_transport=self.fake_google)
        self.assertEqual(code, 0, out)
        r = self.run_dir()

        self.assertTrue((r / "media" / "A1-still.png").is_file())
        self.assertTrue((r / "media" / "SONG.wav").is_file())
        self.assertTrue((r / "media" / "SONG-song-timings.txt").is_file())

        direct_manifest = json.loads((r / "direct.json").read_text())
        self.assertEqual(set(direct_manifest), {"A1-still", "SONG"})
        # the still model is whatever the registry's direct door names — never a literal here
        expected_model = json.loads((HERE / "providers.json").read_text())["direct"]["openai"]["model"]
        self.assertEqual(direct_manifest["A1-still"]["model"], expected_model)
        self.assertEqual(direct_manifest["SONG"]["model"], "lyria-3-clip-preview")
        self.assertTrue(direct_manifest["SONG"]["timed"])

        submit_md = (r / "SUBMIT.md").read_text()
        self.assertIn("## Machine-made media", submit_md)
        self.assertIn("media/A1-still.png", submit_md)
        a1_block = submit_md.split("## A1 —", 1)[1].split("## A2", 1)[0]
        self.assertIn("start_image (upload first)", a1_block)
        self.assertIn("media/A1-still.png", a1_block)
        # machine-hand items were made directly — they never appear as their
        # own blocks for the editor
        self.assertNotIn("## A1-still", submit_md)
        self.assertNotIn("## SONG", submit_md)

        ledger_rows = json.loads((r / "ledger.json").read_text())
        models_billed = {row["model"] for row in ledger_rows}
        self.assertIn(expected_model, models_billed)
        self.assertIn("lyria-3-clip-preview", models_billed)

    def test_dry_run_prints_direct_requests_and_writes_no_media(self):
        a = self.start_args(self.make_plan(), provider="higgsfield-ui", yes=True, dry_run=True)
        code, out = run_quiet(run.cmd_start, a, voice_transport=fake_voice_transport)
        self.assertEqual(code, 0, out)
        self.assertIn("images/edits", out)      # A1's still has two references
        self.assertIn("generateContent", out)   # the song
        r = self.run_dir()
        self.assertFalse((r / "media").exists())
        self.assertFalse((r / "direct.json").exists())

    def test_missing_key_is_a_hard_stop_naming_it(self):
        a = self.start_args(self.make_plan(), provider="higgsfield-ui", yes=True)
        saved = {k: os.environ.pop(k, None) for k in ("OPENAI_API_KEY", "GEMINI_API_KEY")}
        try:
            with env():
                code, out = run_quiet(run.cmd_start, a, voice_transport=fake_voice_transport)
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v
        self.assertEqual(code, 2, out)
        self.assertIn("OPENAI_API_KEY", out)


class Record(TempRuns):
    def make_bare_run(self, provider="higgsfield-ui"):
        r = self.tmp / "video-machine" / "_fixture" / "rec1"
        (r / "batches").mkdir(parents=True)
        run.write_json(r / "run.json", {"machine": "video-machine", "brand": "_fixture",
                                        "label": "rec1", "format": "fixture-format",
                                        "provider": provider, "opened": "2026-09-17T00:00:00+00:00"})
        reg = platform.registry()
        motion_slug = reg["providers"][provider]["stations"]["motion"]
        run.write_json(r / "batches" / "01-motion.json", {"items": [
            {"id": "S1", "kind": "motion", "model": motion_slug,
             "params": {"duration": 5}, "medias": [], "characters": [], "products": [], "lines": []},
            {"id": "S2", "kind": "motion", "model": motion_slug,
             "params": {"duration": 5}, "medias": [], "characters": [], "products": [], "lines": []},
        ]})
        return r

    def test_nsfw_row_is_ambiguous_and_separate(self):
        r = self.make_bare_run()
        results_file = self.tmp / "results.json"
        results_file.write_text(json.dumps([
            {"id": "S1", "job": "job-1", "url": "https://cdn.example.test/s1.mp4",
             "seconds": 5, "status": "done"},
            {"id": "S2", "job": "job-2", "url": None, "seconds": 5, "status": "nsfw"},
        ]))
        a = run.build_parser().parse_args(["record", str(r), "--results", str(results_file)])
        code, out = run_quiet(run.cmd_record, a, download=fake_download)
        self.assertEqual(code, 0, out)

        rows = json.loads((r / "ledger.json").read_text())
        by_job = {row["job"]: row for row in rows}
        self.assertEqual(by_job["job-2"].get("billing"), "ambiguous")
        self.assertNotIn("billing", by_job["job-1"])

        t = preflight.totals(rows)
        self.assertGreater(t["ambiguous_usd"] + t["ambiguous_credits"], 0) if \
            (by_job["job-2"].get("usd") or by_job["job-2"].get("credits")) else None

        results = json.loads((r / "results.json").read_text())
        self.assertEqual(results["S1"]["status"], "done")
        self.assertEqual(results["S2"]["status"], "nsfw")
        self.assertTrue((r / "media" / "S1.mp4").exists())
        self.assertNotIn("file", results["S2"])  # never downloaded — no url

    def test_download_failure_recorded_and_retry_does_not_duplicate(self):
        r = self.make_bare_run()
        results_file = self.tmp / "results2.json"
        results_file.write_text(json.dumps([
            {"id": "S1", "job": "job-1", "url": "https://cdn.example.test/bad.mp4",
             "seconds": 5, "status": "done"},
            {"id": "S2", "job": "job-2", "url": "https://cdn.example.test/good.mp4",
             "seconds": 5, "status": "done"},
        ]))
        a = run.build_parser().parse_args(["record", str(r), "--results", str(results_file)])

        code, out = run_quiet(run.cmd_record, a, download=fake_download_maybe_fail)
        self.assertEqual(code, 1, out)
        rows = json.loads((r / "ledger.json").read_text())
        statuses = {row["job"]: row["status"] for row in rows}
        self.assertEqual(statuses["job-1"], "failed")
        self.assertEqual(statuses["job-2"], "done")
        results = json.loads((r / "results.json").read_text())
        self.assertEqual(results["S1"]["status"], "failed")
        self.assertNotIn("file", results["S1"])

        # retry: same results, same (still-failing) download — no duplicate rows
        code2, out2 = run_quiet(run.cmd_record, a, download=fake_download_maybe_fail)
        self.assertEqual(code2, 1, out2)
        rows2 = json.loads((r / "ledger.json").read_text())
        self.assertEqual(len(rows2), len(rows))


class RecordParity(TempRuns):
    """The 2026-09-18 line-parity gate: record transcribes every downloaded
    clip that carries a line and writes the verdict, automatically."""

    def make_run_with_lines(self, provider="higgsfield-ui"):
        r = self.tmp / "video-machine" / "_fixture" / "rec-parity"
        (r / "batches").mkdir(parents=True)
        run.write_json(r / "run.json", {"machine": "video-machine", "brand": "_fixture",
                                        "label": "rec-parity", "format": "fixture-format",
                                        "provider": provider, "opened": "2026-09-17T00:00:00+00:00"})
        run.write_json(r / "lines.json", {"L1": "Wake up and choose greatness."})
        reg = platform.registry()
        talking_slug = reg["providers"][provider]["stations"]["talking"]
        run.write_json(r / "batches" / "01-motion.json", {"items": [
            {"id": "S1", "kind": "talking", "model": talking_slug,
             "params": {"duration": 5}, "medias": [], "characters": [], "products": [],
             "lines": ["L1"]},
        ]})
        return r

    def results_for(self, one_id="S1"):
        f = self.tmp / "results.json"
        f.write_text(json.dumps([
            {"id": one_id, "job": "job-1", "url": "https://cdn.example.test/s1.mp4",
             "seconds": 5, "status": "done"}]))
        return f

    def test_record_writes_parity_verdict_with_fake_transcription(self):
        r = self.make_run_with_lines()
        results_file = self.results_for()
        a = run.build_parser().parse_args(["record", str(r), "--results", str(results_file)])
        fake_transcriber = FakeTranscriber("Wake up and choose greatness.")
        with env(ELEVENLABS_API_KEY="test-key"):
            code, out = run_quiet(run.cmd_record, a, download=fake_download,
                                   parity_transport=fake_transcriber)
        self.assertEqual(code, 0, out)
        self.assertIn("parity PASS", out)
        verdicts = json.loads((r / "verdicts.json").read_text())
        self.assertEqual(verdicts["S1"]["parity"]["verdict"], "PASS")
        self.assertEqual(verdicts["S1"]["parity"]["heard"], "Wake up and choose greatness.")
        self.assertEqual(len(fake_transcriber.calls), 1)

    def test_flagged_when_the_clip_says_other_words(self):
        r = self.make_run_with_lines()
        results_file = self.results_for()
        a = run.build_parser().parse_args(["record", str(r), "--results", str(results_file)])
        fake_transcriber = FakeTranscriber("I wanted to share this with you today.")
        with env(ELEVENLABS_API_KEY="test-key"):
            code, out = run_quiet(run.cmd_record, a, download=fake_download,
                                   parity_transport=fake_transcriber)
        self.assertEqual(code, 0, out)
        self.assertIn("parity FLAG", out)
        verdicts = json.loads((r / "verdicts.json").read_text())
        self.assertEqual(verdicts["S1"]["parity"]["verdict"], "FLAG")

    def test_no_parity_flag_skips_the_check(self):
        r = self.make_run_with_lines()
        results_file = self.results_for()
        a = run.build_parser().parse_args(["record", str(r), "--results", str(results_file),
                                           "--no-parity"])
        fake_transcriber = FakeTranscriber("Wake up and choose greatness.")
        with env(ELEVENLABS_API_KEY="test-key"):
            code, out = run_quiet(run.cmd_record, a, download=fake_download,
                                   parity_transport=fake_transcriber)
        self.assertEqual(code, 0, out)
        self.assertFalse((r / "verdicts.json").exists())
        self.assertEqual(fake_transcriber.calls, [])

    def test_missing_key_prints_note_and_does_not_fail_the_record(self):
        r = self.make_run_with_lines()
        results_file = self.results_for()
        a = run.build_parser().parse_args(["record", str(r), "--results", str(results_file)])
        with env():
            os.environ.pop("ELEVENLABS_API_KEY", None)
            code, out = run_quiet(run.cmd_record, a, download=fake_download)
        self.assertEqual(code, 0, out)
        self.assertIn("no ELEVENLABS_API_KEY", out)
        self.assertFalse((r / "verdicts.json").exists())


class Pack(TempRuns):
    def make_bare_run(self):
        r = self.tmp / "video-machine" / "_fixture" / "pack1"
        r.mkdir(parents=True)
        run.write_json(r / "run.json", {"machine": "video-machine", "brand": "_fixture",
                                        "label": "pack1", "format": "fixture-format",
                                        "provider": "higgsfield-ui",
                                        "opened": "2026-09-17T00:00:00+00:00"})
        run.write_json(r / "lines.json", {"L1": "first line"})
        return r

    def test_uncovered_line_fails(self):
        r = self.make_bare_run()
        (r / "batches").mkdir()
        a = run.build_parser().parse_args(["pack", str(r)])
        code, out = run_quiet(run.cmd_pack, a)
        self.assertEqual(code, 2, out)

    def test_covered_run_writes_editor_pack(self):
        r = self.make_bare_run()
        (r / "batches").mkdir()
        run.write_json(r / "batches" / "01-motion.json", {"items": [
            {"id": "S1", "kind": "motion", "params": {"duration": 5}, "medias": [],
             "characters": [], "products": [], "lines": ["L1"]},
        ]})
        (r / "media").mkdir()
        (r / "media" / "S1.mp4").write_bytes(b"fake")
        run.write_json(r / "results.json", {
            "S1": {"id": "S1", "job": "job-1", "url": "https://cdn.example.test/s1.mp4",
                   "seconds": 5, "status": "done", "file": "media/S1.mp4"}})
        run.write_json(r / "ledger.json", [
            {"model": "x", "job": "job-1", "seconds": 5, "status": "done",
             "credits": None, "usd": 1.0, "at": "2026-09-17T00:00:00+00:00"}])
        run.write_json(r / "verdicts.json", {
            "S1": {
                "motion": {"verdict": "OK", "at": "2026-09-17T00:00:00+00:00", "history": []},
                "director": {"verdict": "OK", "at": "2026-09-17T00:00:00+00:00", "history": []},
                "parity": {"verdict": "PASS", "heard": "first line", "match": 1.0,
                           "at": "2026-09-17T00:00:00+00:00", "history": []},
            }
        })
        run.write_json(r / "brief.json", {
            "brand": "_fixture", "product": "widget", "problem": "dry-skin",
            "angle": "testimonial", "concept": "beforeafter", "avatar": "lead",
            "format": "fixture-format", "talent": "lead", "source": "ai",
            "ratio": "9x16", "brief": "none"})
        a = run.build_parser().parse_args(["pack", str(r)])
        code, out = run_quiet(run.cmd_pack, a)
        self.assertEqual(code, 0, out)
        self.assertTrue((r / "deliverable" / "EDITOR-PACK.md").is_file())
        pack_text = (r / "deliverable" / "EDITOR-PACK.md").read_text()
        self.assertIn("LINE COVERAGE", pack_text)
        self.assertIn("L1: carried by S1", pack_text)


class ScenePassThrough(unittest.TestCase):
    """The brief's own Section/Technique/Emotion/Outcome labels ride along
    onto the batch item, verbatim, when the scene or cutaway record carries
    them — run.py never derives, checks or renames the values, it only
    carries whichever of them the brief actually wrote."""

    CAST = {"name": "Lead", "room": "00000000-0000-4000-8000-0000000000e1",
            "face": "00000000-0000-4000-8000-0000000000c1", "presenter": "LEAD",
            "resolution": "720p"}

    def setUp(self):
        # payload()/broll() append element facts, which need a brand named —
        # a fixture brand with no facts file resolves to "no facts", tolerated.
        self.saved_brand = run.prompt_mod.BRAND
        run.prompt_mod.use_brand("_fixture")

    def tearDown(self):
        run.prompt_mod.BRAND = self.saved_brand

    def test_scene_item_carries_fields_when_present(self):
        scene = {"id": "A1", "seconds": 5, "gesture": "g", "delivery": "d", "line": "l",
                  "section": "hook", "technique": "intensification",
                  "emotion": "anticipation", "outcome": "leans in"}
        item = run.scene_item(scene, self.CAST, None)
        self.assertEqual(item["section"], "hook")
        self.assertEqual(item["technique"], "intensification")
        self.assertEqual(item["emotion"], "anticipation")
        self.assertEqual(item["outcome"], "leans in")

    def test_scene_item_omits_fields_when_absent(self):
        scene = {"id": "A1", "seconds": 5, "gesture": "g", "delivery": "d", "line": "l"}
        item = run.scene_item(scene, self.CAST, None)
        for key in run.SCENE_METADATA_FIELDS:
            self.assertNotIn(key, item)

    def test_cutaway_item_carries_fields_when_present(self):
        cut = {"id": "B1", "seconds": 4, "place": "p", "subject": "s", "action": "a",
                "look": "l", "section": "problem", "technique": "gradualization",
                "emotion": "recognition", "outcome": "nods"}
        item = run.cutaway_item(cut, self.CAST, None)
        self.assertEqual(item["section"], "problem")
        self.assertEqual(item["technique"], "gradualization")
        self.assertEqual(item["emotion"], "recognition")
        self.assertEqual(item["outcome"], "nods")

    def test_still_item_for_carries_fields_when_present(self):
        scene = {"id": "A1", "generate": {"prompt": "a still prompt"},
                  "section": "hook", "technique": "camouflage",
                  "emotion": "curiosity", "outcome": "keeps watching"}
        item = run.still_item_for(scene, self.CAST, None)
        self.assertEqual(item["section"], "hook")
        self.assertEqual(item["technique"], "camouflage")
        self.assertEqual(item["emotion"], "curiosity")
        self.assertEqual(item["outcome"], "keeps watching")


class ProductsOf(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-ws-"))
        self.saved_ws = run.WS
        run.WS = self.tmp

    def tearDown(self):
        run.WS = self.saved_ws
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_tags_only_product_elements(self):
        facts_dir = self.tmp / "brands" / "acme"
        facts_dir.mkdir(parents=True)
        (facts_dir / "element-facts.json").write_text(json.dumps({"elements": {
            "00000000-0000-4000-8000-0000000000d1": {"kind": "product"},
            "00000000-0000-4000-8000-0000000000c1": {"kind": "face"},
        }}))
        prompt_text = ("<<<00000000-0000-4000-8000-0000000000d1>>> and "
                      "<<<00000000-0000-4000-8000-0000000000c1>>>")
        out = run.products_of(prompt_text, "acme")
        self.assertEqual(out, ["00000000-0000-4000-8000-0000000000d1"])

    def test_missing_facts_file_is_tolerated(self):
        self.assertEqual(run.products_of("<<<00000000-0000-4000-8000-0000000000d1>>>", "nobrand"), [])


class NoSlugs(unittest.TestCase):
    def test_no_model_slug_literal_in_run_or_providers_fal(self):
        slugs = list(REG["models"].keys())
        for fname in ("run.py", "providers_fal.py"):
            src = (HERE / fname).read_text()
            for slug in slugs:
                self.assertNotIn(slug, src, f"{fname} names model slug {slug!r}")


if __name__ == "__main__":
    unittest.main()
