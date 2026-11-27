"""Writing identity, exact acceptance and bounded resume. No provider calls."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

M = Path(__file__).resolve().parents[1] / "machine"
TD = M.parents[1] / "video-teardown" / "machine"
sys.path.insert(0, str(M))
sys.path.insert(0, str(TD))
import writing_result as S
import writing_v2 as W
import run as R
spec = importlib.util.spec_from_file_location("writing_launcher_state_test", M / "run.py")
LAUNCH = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LAUNCH)
spec = importlib.util.spec_from_file_location("writing_filing_state_test", TD / "file_run.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)


def save(d, st):
    (d / "run.json").write_text(json.dumps(st))


def fixture(d, status="done", accepted=False):
    (d / "stages").mkdir(parents=True, exist_ok=True)
    st = {"brand": "fixture", "production_route": "ai", "format_id": "expert-consult",
          "writing": "v2", "slug": d.name, "stages": {}}
    for key, _, _, _, _, splits in W.PASSES:
        out = "stages/5-brief.md" if key == "stage5" else "stages/" + key + ".md"
        (d / out).write_text("Locked spoken lines. " + key)
        st["stages"][key] = {"status": status if key == "stage5" else "done", "out": out}
        for _, split_key, _, _ in splits or []:
            st["stages"][split_key] = {"status": "done", "out": out}
    if accepted:
        S.record_acceptance(d, st)
    save(d, st)
    return st


class Identity(unittest.TestCase):
    def test_child_discards_parent_0070_and_passed_receipts(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "source"; d.mkdir()
            st = fixture(d, accepted=True)
            st.update(brief="brief-0070", brief_key="fixture_device_brief-0070",
                      gdoc_url="https://docs.google.com/document/d/parent-only",
                      creator_folder="https://drive.google.com/drive/folders/parent-only",
                      start_here_url="https://docs.google.com/document/d/parent-start",
                      swipe_match="passed", manifest={"missing": []}, production_contract={"open": []},
                      writing_retry_budget={"used": 2}, viewer_check={"passed": True})
            save(d, st)
            child = LAUNCH.fork(d, "child")
            fresh = json.loads((child / "run.json").read_text())
            self.assertEqual(fresh["parent_provenance"]["brief"], "brief-0070")
            self.assertEqual(fresh["parent_provenance"]["run"], "source")
            for key in S.DELIVERY_KEYS:
                self.assertEqual(fresh["parent_provenance"][key], st[key])
            for key in S.IDENTITY_KEYS + S.DELIVERY_KEYS + S.ACCEPTANCE_KEYS:
                self.assertNotIn(key, fresh)
            self.assertFalse(S.inspect_result(child)["accepted"])
            self.assertEqual(json.loads((d / "run.json").read_text()), st)


class Acceptance(unittest.TestCase):
    def test_source_or_ruling_change_makes_receipt_stale(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t);st = fixture(d, accepted=True)
            self.assertTrue(S.inspect_result(d)["accepted"])
            (d / "RULINGS.md").write_text("Owner changed the ask")
            self.assertFalse(S.inspect_result(d)["accepted"])
            self.assertIn("acceptance_stale", [x["code"] for x in S.inspect_result(d)["blockers"]])
            S.record_acceptance(d, st);save(d, st)
            (d / "stages/5-brief.md").write_text("Different spoken line")
            self.assertFalse(S.inspect_result(d)["accepted"])

    def test_one_byte_change_in_either_raw_source_invalidates_acceptance(self):
        for name in ("verbatim-sources.md", "verbatim-sources.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as t:
                d = Path(t)
                source = d / name
                source.write_bytes(b'{"quote":"A"}\r\n')
                fixture(d, accepted=True)
                self.assertTrue(S.inspect_result(d)["accepted"])
                source.write_bytes(b'{"quote":"B"}\r\n')
                result = S.inspect_result(d)
                self.assertFalse(result["accepted"])
                self.assertIn("acceptance_stale", [b["code"] for b in result["blockers"]])

    def test_existing_receipt_with_no_raw_packet_keeps_its_context_hash(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "stages").mkdir()
            brief = d / "stages/5-brief.md"
            brief.write_bytes(b"existing accepted brief")
            st = {"brand": "fixture", "stages": {"stage5": {"status": "done", "out": "stages/5-brief.md"}},
                  "writing_acceptance": {"accepted": True, "source_sha256": S.digest(brief),
                                         "context_sha256": "986520a8dc200ab0a65735e7b0a230fac20f844d7637f48502a0019f1336b3b7"}}
            self.assertTrue(S.inspect_result(d, st)["accepted"])

    def test_downstream_production_records_do_not_invalidate_writing(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t);st = fixture(d, accepted=True)
            st["stages"]["stage7"] = {"status": "running", "out": "production.md"}
            (d / "production.md").write_text("downstream work")
            save(d, st)
            self.assertTrue(S.inspect_result(d)["accepted"])

    def test_fresh_success_issues_a_hash_bound_receipt(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t);st = fixture(d, "pending")
            p = {"key": "stage5", "id": "5", "name": "Brief", "splits": None}
            def checked(d, st, p, extras, redo=False):
                st["stages"]["stage5"]["status"] = "done"
                save(d, st)
                return True
            with mock.patch.object(W, "plan", return_value=[p]), mock.patch.object(W, "run_inputs", return_value={}), \
                    mock.patch.object(W, "declared_layers", return_value=""), mock.patch.object(W, "apply_call", side_effect=lambda d,s:s), \
                    mock.patch.object(W, "format_approved", return_value=True), mock.patch.object(R, "run_stage", side_effect=checked), \
                    mock.patch.object(R, "save", side_effect=save), mock.patch.object(W, "apply_owner_check", return_value=None):
                self.assertTrue(W.run_writing(d, st, {}))
            self.assertTrue(S.inspect_result(d)["accepted"])

    def test_global_passed_flags_and_done_do_not_prove_acceptance(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t);st = fixture(d)
            st.update(swipe_match="passed", viewer_check={"passed": True});save(d, st)
            r = S.inspect_result(d)
            self.assertTrue(r["artifact_written"]);self.assertFalse(r["accepted"])

    def test_held_cli_exits_one_without_touching_the_creative(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t);fixture(d, "held")
            before = (d / "stages/5-brief.md").read_bytes()
            proc = subprocess.run([sys.executable, str(M / "run.py"), str(d), "--sandbox"],
                                  text=True, capture_output=True, timeout=30)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            r = json.loads((d / "writing-result.json").read_text())
            self.assertTrue(r["artifact_written"]);self.assertFalse(r["accepted"])
            self.assertEqual((d / "stages/5-brief.md").read_bytes(), before)
            self.assertFalse(json.loads((d / "run.json").read_text()).get("writing_v2_calls"))

    def test_unchanged_accepted_resume_reuses_passes_without_model_calls(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t);fixture(d, accepted=True)
            before = {p.name: p.read_bytes() for p in (d / "stages").iterdir()}
            for _ in range(2):
                proc = subprocess.run([sys.executable, str(M / "run.py"), str(d), "--sandbox"],
                                      text=True, capture_output=True, timeout=30)
                self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            st = json.loads((d / "run.json").read_text())
            self.assertFalse(st.get("writing_v2_calls"))
            self.assertEqual(before, {p.name: p.read_bytes() for p in (d / "stages").iterdir()})
            self.assertTrue(S.inspect_result(d)["accepted"])

    def test_held_filing_archives_stages_without_promoting_or_numbering(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t);d = root / "child";d.mkdir();st = fixture(d, "held")
            st["brief"] = "brief-0070";save(d, st)
            repo = root / "repo";dest, _, _ = F.file_run(d, repo)
            writing = repo / "runs/video-writing/fixture/child"
            self.assertTrue((writing / "stages/5-brief.md").is_file())
            self.assertFalse((writing / "deliverable").exists())
            with mock.patch("subprocess.run", side_effect=AssertionError("allocator called")):
                self.assertIsNone(F.number_brief(d, dest))


class RetryBudget(unittest.TestCase):
    def test_legacy_audit_history_consumes_budget(self):
        self.assertEqual(S.retry_budget({"writing_v2_calls": [{"stage": "stage4e"}] * 5})["used"], 2)

    def test_audit_budget_is_persisted_and_exhausted_resume_calls_no_models(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t);(d / "stages").mkdir()
            st = {"brand": "fixture", "production_route": "ai", "stages": {}}
            save(d, st)
            plan = [{"key": k, "id": k, "name": k, "splits": None} for k in ("stage3", "stage4e")]
            calls = []
            def run_stage(d, st, p, extras, redo=False):
                k = p["key"]
                if st["stages"].get(k, {}).get("status") == "done" and not redo:
                    return True
                calls.append(k)
                path = "stages/" + k + ".md"
                (d / path).write_text("VERDICT: RE-RUN INJECTION" if k == "stage4e" else "same creative")
                st["stages"][k] = {"status": "held" if k == "stage4e" else "done", "out": path}
                W._CURRENT["calls"] = [{"stage": k, "cost_usd": 0, "api_seconds": 0}]
                save(d, st)
                return k != "stage4e"
            with mock.patch.object(W, "plan", return_value=plan), mock.patch.object(W, "run_inputs", return_value={}), \
                    mock.patch.object(W, "declared_layers", return_value=""), mock.patch.object(W, "apply_call", side_effect=lambda d,s:s), \
                    mock.patch.object(W, "format_approved", return_value=True), mock.patch.object(R, "run_stage", side_effect=run_stage), \
                    mock.patch.object(R, "save", side_effect=save), mock.patch.object(R, "say"):
                self.assertFalse(W.run_writing(d, st, {}))
                after = json.loads((d / "run.json").read_text())
                self.assertEqual(after["writing_retry_budget"]["used"], 2)
                self.assertEqual(calls.count("stage4e"), 3)
                n = len(calls)
                self.assertFalse(W.run_writing(d, after, {}))
                self.assertEqual(len(calls), n)
                self.assertEqual(json.loads((d / "run.json").read_text())["writing_retry_budget"]["used"], 2)


if __name__ == "__main__":
    unittest.main()
