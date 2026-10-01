#!/usr/bin/env python3
"""Tests for the 2026-09-20 rollout additions. Stdlib only, no network, no
model — `python3 test_rollout.py`.

    * the dry run makes ZERO model calls, opens no run folder, and reports a
      missing variable with a non-zero exit
    * the elements validation records an unknown value AS unknown
    * the repo-root filing copies text only
    * the workspace is found by walking up
    * a malformed extra-stages.json stops loud, naming the file
    * a brand's display name comes from the brand's folder
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import chain as C                                            # noqa: E402
import run as R                                              # noqa: E402

# TESTS NEVER TOUCH LIVE RUNS: the runs root is a temp folder from import on.
_TMP_RUNS = Path(tempfile.mkdtemp(prefix="video-teardown-rollout-tests-"))
R.RUNS = _TMP_RUNS
C.runs_root = lambda *a, **k: _TMP_RUNS

import dryrun as DRY                                         # noqa: E402
import elements_check as EC                                  # noqa: E402
import file_run as FR                                        # noqa: E402

NO_BRAND = "zz-no-such-brand"        # a brand folder that does not exist


class _Spent(AssertionError):
    pass


def _boom(name):
    def f(*a, **k):
        raise _Spent(f"{name} was called — a dry run must spend nothing")
    return f


class DryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.video = Path(self.tmp.name) / "a-video.mp4"
        self.video.write_bytes(b"\x00")
        self.patches = [mock.patch.object(R, n, _boom(n)) for n in (
            "gemini_video", "gemini_text", "claude", "frames", "inject",
            "open_run", "run_video", "run_stage", "stay_awake",
            "rebuild_board", "save")]
        self.patches.append(mock.patch.object(R.subprocess, "run", _boom("subprocess.run")))
        self.patches.append(mock.patch.object(R.subprocess, "Popen", _boom("subprocess.Popen")))
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _resolve(self, **kw):
        with redirect_stdout(io.StringIO()):
            return DRY.resolve(self.video, "dry-label", NO_BRAND,
                               extras={"brand_name": "X", "video_count": "3",
                                       "declared_audience": "NONE"}, **kw)

    def test_no_model_call_and_no_run_folder(self):
        before = sorted(p.name for p in _TMP_RUNS.iterdir())
        res = self._resolve()
        self.assertGreater(len(res["stages"]), 10)
        self.assertEqual(before, sorted(p.name for p in _TMP_RUNS.iterdir()))
        self.assertFalse((_TMP_RUNS / "dry-label").exists())

    def test_every_stage_names_its_prompt_and_version(self):
        res = self._resolve()
        for row in res["stages"]:
            self.assertTrue(row["prompt"], row["stage"]["key"])
            self.assertIsInstance(row["version"], int)

    def test_a_missing_brand_file_is_reported_and_counted(self):
        res = self._resolve()
        self.assertGreater(res["missing"], 0)
        s3 = next(r for r in res["stages"] if r["stage"]["key"] == "stage3")
        missing = {v: o for v, stt, o in s3["vars"] if stt == DRY.MISSING}
        self.assertIn("language_bank", missing)
        self.assertIn(NO_BRAND, missing["language_bank"])

    def test_an_earlier_stage_output_reads_as_not_run(self):
        res = self._resolve()
        s1c = next(r for r in res["stages"] if r["stage"]["key"] == "stage1c")
        got = {v: (stt, o) for v, stt, o in s1c["vars"]}
        self.assertEqual(got["teardown_record"][0], DRY.LATER)
        self.assertEqual(got["teardown_record"][1], "from stage 1 (not run)")
        # a doctrine slice is a real file in this repo and resolves for real
        self.assertEqual(got["sections"][0], DRY.OK)

    def test_a_field_the_prompt_asks_for_that_nothing_supplies(self):
        fake = Path(self.tmp.name) / "stage1c-doctrine-v99-test.md"
        fake.write_text("read {teardown_record} and {a_field_nobody_binds}")
        real = C.stages

        def patched(*a, **k):
            out = real(*a, **k)
            for s in out:
                if s["key"] == "stage1c":
                    s["prompt"] = str(fake)
            return out
        with mock.patch.object(C, "stages", patched):
            res = self._resolve(stop="1c")
        s1c = next(r for r in res["stages"] if r["stage"]["key"] == "stage1c")
        self.assertEqual(s1c["unbound"], ["a_field_nobody_binds"])
        self.assertGreaterEqual(res["missing"], 1)

    def test_a_video_that_is_not_there_is_missing(self):
        with redirect_stdout(io.StringIO()):
            res = DRY.resolve(Path(self.tmp.name) / "nope.mp4", "x", NO_BRAND,
                              stop="0")
        self.assertFalse(res["video_ok"])
        self.assertEqual(res["missing"], 1)

    def test_the_flag_on_run_py_exits_non_zero_and_spends_nothing(self):
        argv = ["run.py", str(self.video), "--brand", NO_BRAND, "--dry-run"]
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", argv), redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                R.main()
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("DRY RUN", buf.getvalue())
        self.assertIn("MISSING", buf.getvalue())
        self.assertIn("0 model calls made", buf.getvalue())

    def test_the_short_flag_is_the_same_flag(self):
        argv = ["run.py", str(self.video), "--brand", NO_BRAND, "--dry", "--to", "1"]
        with mock.patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                R.main()


DOC = {
    "framework": "PAS (problem · agitate · solve)",
    "crosswalk_row": "PAS (problem · agitate · solve)",
    "sections_carried": [{"id": "hook", "span": "0:00-0:03"},
                         {"id": "hook", "span": "0:20-0:22"},
                         {"id": "a-section-nobody-listed", "span": "0:03-0:09"}],
    "awareness": {"entry": "problem-aware", "exit": "Product-Aware"},
    "sophistication_signature": "a mechanism",
    "mass_desire": {"words": "x", "urgency": "x", "staying_power": "x", "scope": "x"},
    "techniques": [{"section": "hook", "technique": "intensification",
                    "sub_method": "x", "span": "0:00-0:03"},
                   {"section": "hook", "technique": "time-travel",
                    "sub_method": "x", "span": "0:03-0:09"}],
    "mood": "x",
    "delivery": {"humor": "not shown in the record",
                 "delivery_style": "not shown in the record",
                 "register": "a-register-nobody-listed · 0:00-0:30 · the beat",
                 "pacing": "not shown in the record",
                 "reference_world": [], "avoid": []},
    "unique": "x",
}


class Elements(unittest.TestCase):
    def test_a_known_value_gets_its_library_id(self):
        got = EC.label(DOC)
        self.assertEqual(got["framework/all"]["id"], "pas")
        self.assertTrue(got["framework/all"]["known"])
        self.assertEqual(got["doctrine/awareness.entry"]["id"], "problem-aware")
        self.assertEqual(got["doctrine/awareness.exit"]["id"], "product-aware")
        self.assertTrue(got["doctrine/sophistication"]["known"])
        self.assertTrue(got["doctrine/sophistication"]["id"].startswith("stage-"))

    def test_an_unknown_value_is_recorded_as_unknown_never_dropped(self):
        got = EC.label(DOC)
        techs = {e["value"]: e for e in got["doctrine/technique"]}
        self.assertEqual(techs["time-travel"], {"value": "time-travel",
                                                "id": None, "known": False})
        self.assertTrue(techs["intensification"]["known"])
        secs = {e["value"]: e for e in got["doctrine/section"]}
        self.assertEqual(len(secs), 2)                       # the repeat is one label
        self.assertFalse(secs["a-section-nobody-listed"]["known"])
        self.assertIsNone(secs["a-section-nobody-listed"]["id"])
        reg = got["delivery/register"]
        self.assertFalse(reg["known"])
        self.assertIsNone(reg["id"])
        self.assertIn("a-register-nobody-listed", reg["value"])

    def test_an_unanswered_slot_is_not_counted_as_a_new_row(self):
        got = EC.label(DOC)
        self.assertTrue(got["delivery/humor"].get("not_shown"))
        self.assertFalse(got["delivery/humor"]["known"])

    def test_no_crosswalk_row_is_a_candidate_not_a_guess(self):
        doc = dict(DOC, crosswalk_row=None,
                   framework="a countdown of objections (no crosswalk row)")
        e = EC.label(doc)["framework/all"]
        self.assertFalse(e["known"])
        self.assertIsNone(e["id"])
        self.assertIn("countdown", e["value"])

    def test_check_run_writes_the_file_and_never_fails_the_run(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "doctrine.json").write_text(json.dumps(DOC))
            rep, note = EC.check_run(d)
            on_disk = json.loads((d / "elements.json").read_text())
            self.assertEqual(on_disk["counts"]["unknown"], 3)
            self.assertIn("doctrine/technique: time-travel", on_disk["unknown"])
            self.assertIn("UNKNOWN", note)
            # a broken doctrine file is a note, never an exception
            (d / "doctrine.json").write_text("{not json")
            rep, note = EC.check_run(d)
            self.assertIsNone(rep)
            self.assertTrue(note)

    def test_a_block_that_carries_format_and_structure_is_labelled_too(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "doctrine.json").write_text(json.dumps(
                dict(DOC, format="a-format-nobody-listed", structure="not shown in the record")))
            rep, _ = EC.check_run(d)
            self.assertFalse(rep["elements"]["format/video"]["known"])
            self.assertIn("format/video: a-format-nobody-listed", rep["unknown"])
            self.assertNotIn("not_labelled", rep)


class RepoFiling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.repo = t / "repo"
        self.repo.mkdir()
        self.run = t / "machine-runs" / "a-run"
        (self.run / "stages").mkdir(parents=True)
        (self.run / "prompts").mkdir()
        (self.run / "frames" / "frames").mkdir(parents=True)
        (self.run / "run.json").write_text(json.dumps(
            {"slug": "a-run", "brand": "zz-brand", "label": "A run"}))
        (self.run / "doctrine.json").write_text("{}")
        (self.run / "stages" / "1-teardown.md").write_text("the record")
        (self.run / "prompts" / "1-teardown.md").write_text("the prompt as sent")
        (self.run / "stages" / "too-big.md").write_text("x" * (FR.MAX_BYTES + 1))
        (self.run / "stages" / "not-text.md").write_bytes(b"\xff\xfe\x00\xd8\xff")
        (self.run / "stages" / "notes.txt").write_text("not markdown")
        (self.run / "source.mp4").write_bytes(b"\x00\x01")
        (self.run / "poster.jpg").write_bytes(b"\xff\xd8")
        (self.run / "brief.html").write_text("<html>")
        (self.run / "frames" / "frames" / "1.png").write_bytes(b"\x89PNG")

    def tearDown(self):
        self.tmp.cleanup()

    def test_text_only_under_runs_tool_brand_slug(self):
        dest, copied, left_out = FR.file_run(self.run, repo=self.repo)
        self.assertEqual(dest, self.repo / "runs" / "video-teardown" / "zz-brand" / "a-run")
        have = sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())
        self.assertEqual(have, ["doctrine.json", "prompts/1-teardown.md",
                                "run.json", "stages/1-teardown.md"])
        self.assertEqual(len(left_out), 2)
        # the working folder is untouched — this is a copy, nothing moved
        self.assertTrue((self.run / "source.mp4").is_file())
        self.assertTrue((self.run / "stages" / "1-teardown.md").is_file())

    def test_a_run_with_no_brand_is_refused_not_guessed(self):
        (self.run / "run.json").write_text(json.dumps({"slug": "a-run"}))
        with self.assertRaises(ValueError):
            FR.file_run(self.run, repo=self.repo)

    def test_a_run_outside_the_machines_runs_folder_never_reaches_the_repo(self):
        with mock.patch.object(FR, "file_run", _boom("file_run")):
            self.assertIsNone(FR.file_after_run(self.run))

    def test_the_switch_turns_it_off(self):
        with mock.patch.dict("os.environ", {FR.OFF_ENV: "1"}):
            self.assertIsNone(FR.file_after_run(self.run, repo=self.repo))
        self.assertFalse((self.repo / "runs").exists())

    def test_the_end_of_run_hook_prints_skipped_and_never_raises(self):
        buf = io.StringIO()
        with mock.patch.object(FR, "file_after_run", _boom("filing")), redirect_stdout(buf):
            R.file_to_repo(self.run)
        self.assertIn("SKIPPED", buf.getvalue())


class RealPathStillRuns(unittest.TestCase):
    """The live path — open_run, run_stage, the early-stop ending — with every
    engine stubbed and the Drive, the swipe library and the bank fenced off.
    Proves the two hooks fire where they were added and the run is unchanged."""

    def test_a_stubbed_run_to_1c_files_doctrine_elements_and_the_repo_record(self):
        import framework_bank as FB
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        t = Path(tmp.name)
        video = t / "zz-stub-video.mp4"
        video.write_bytes(b"\x00")
        calls = []

        def video_engine(ppath, vid, out):
            calls.append(("gemini_video", Path(ppath).name))
            out.write_text("LANE: ORGANIC\n\nthe record")
            return "stub-model"

        def text_engine(filled, out):
            calls.append(("claude", len(filled)))
            out.write_text("FRAMEWORK: x\n\n```json\n" + json.dumps(DOC) + "\n```\n")
            return "stub-model"

        filed = {}

        def fake_filing(d):
            filed["dest"], filed["copied"], _ = FR.file_run(d, repo=t / "repo")

        class _Motion:
            @staticmethod
            def check(v):
                return {"verdict": "moving", "movement": 1.0}

        with mock.patch.object(R, "gemini_video", video_engine), \
                mock.patch.object(R, "claude", text_engine), \
                mock.patch.object(R, "with_retry", lambda fn, what, **k: fn()), \
                mock.patch.object(R, "library_home", lambda v, l, st: t / "library"), \
                mock.patch.object(R, "source_url", lambda v: ""), \
                mock.patch.object(R, "record_time", lambda *a, **k: None), \
                mock.patch.object(R, "TIMES", t / "stage-times.json"), \
                mock.patch.object(R, "file_to_repo", fake_filing), \
                mock.patch.object(R.shutil, "which", lambda x: None), \
                mock.patch.object(R.L, "save_teardown", lambda *a, **k: None), \
                mock.patch.object(C, "mirror_to_drive", _boom("the Drive")), \
                mock.patch.object(FB, "refresh", lambda *a, **k: None), \
                mock.patch.dict(sys.modules, {"motion": _Motion}), \
                redirect_stdout(io.StringIO()) as buf:
            ok = R.run_video(video, "zz-stub-run", NO_BRAND, stop="1c",
                             extras={"brand_name": "X"})
        self.assertTrue(ok, buf.getvalue())
        d = _TMP_RUNS / C.run_slug("zz-stub-run")
        self.assertEqual([c[0] for c in calls],
                         ["gemini_video", "gemini_video", "claude"])
        self.assertTrue((d / "doctrine.json").is_file())
        el = json.loads((d / "elements.json").read_text())
        self.assertIn("doctrine/technique: time-travel", el["unknown"])
        st = json.loads((d / "run.json").read_text())
        self.assertEqual(st["elements"]["unknown"], 3)
        self.assertEqual(st["stages"]["stage1c"]["status"], "done")
        self.assertIn("elements.json", filed["copied"])
        self.assertIn("stages/1c-doctrine.md", filed["copied"])
        self.assertIn("elements:", buf.getvalue())


class Workspace(unittest.TestCase):
    def test_walks_up_to_the_folder_holding_components_and_brands(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve() / "somewhere" / "a-checkout"
            deep = root / "components" / "video-teardown" / "machine"
            deep.mkdir(parents=True)
            (root / "brands").mkdir()
            self.assertEqual(C.workspace(start=deep, env=""), root)

    def test_the_environment_wins_when_it_points_at_a_real_workspace(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve() / "a-checkout"
            deep = root / "components" / "x"
            deep.mkdir(parents=True)
            (root / "brands").mkdir()
            other = Path(t).resolve() / "other"
            (other / "brands").mkdir(parents=True)
            self.assertEqual(C.workspace(start=deep, env=str(other)), other)
            # an env that points at nothing is ignored, not obeyed
            self.assertEqual(C.workspace(start=deep, env=str(Path(t) / "nope")), root)

    def test_the_old_default_is_the_last_resort(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(C.workspace(start=Path(t), env=""),
                             Path.home() / "Projects" / "ai-workspace")

    def test_this_checkout_finds_itself(self):
        self.assertTrue((C.WS / "components" / "video-teardown").is_dir())
        self.assertTrue((C.WS / "brands").is_dir())


class ExtraStages(unittest.TestCase):
    def test_a_malformed_file_stops_loud_and_names_itself(self):
        with tempfile.TemporaryDirectory() as t:
            bad = Path(t) / "extra-stages.json"
            bad.write_text('{"stages": [,]}')
            with mock.patch.object(C, "EXTRA", bad):
                with self.assertRaises(SystemExit) as cm:
                    C.load_config()
            self.assertIn("extra-stages.json", str(cm.exception))

    def test_a_stage_with_no_key_stops_loud(self):
        with tempfile.TemporaryDirectory() as t:
            bad = Path(t) / "extra-stages.json"
            bad.write_text('{"stages": [{"prompt": "x.md"}]}')
            with mock.patch.object(C, "EXTRA", bad):
                with self.assertRaises(SystemExit):
                    C.load_config()

    def test_no_file_is_no_extras_and_the_real_file_still_loads(self):
        with tempfile.TemporaryDirectory() as t:
            with mock.patch.object(C, "EXTRA", Path(t) / "absent.json"):
                shared = [s["stage"] for s in C.load_config()["stages"]]
        full = [s["stage"] for s in C.load_config()["stages"]]
        self.assertTrue(set(shared) < set(full))
        self.assertIn("stage1c", full)
        order = json.loads(C.EXTRA.read_text()).get("order") or []
        self.assertEqual([k for k in order if k in full],
                         [k for k in full if k in order])


class BrandLabel(unittest.TestCase):
    def test_the_display_name_is_read_from_the_brands_folder(self):
        import simplify as S
        with tempfile.TemporaryDirectory() as t:
            ws = Path(t)
            (ws / "brands" / "zz-one").mkdir(parents=True)
            (ws / "brands" / "zz-one" / "brand.json").write_text(
                json.dumps({"display_name": "ZZ One & Co"}))
            (ws / "brands" / "zzcaps").mkdir()
            (ws / "brands" / "zzcaps" / "position.md").write_text("# ZZCAPS — the position\n")
            (ws / "brands" / "zzplain").mkdir()
            with mock.patch.object(S.C, "WS", ws):
                self.assertEqual(S.brand_label("zz-one"), "ZZ One & Co")
                self.assertEqual(S.brand_label("zzcaps"), "ZZCAPS")
                self.assertEqual(S.brand_label("zzplain"), "Zzplain")


if __name__ == "__main__":
    unittest.main(verbosity=1)
