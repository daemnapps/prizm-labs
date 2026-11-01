"""stage-check, no network and no model: the lane map is whole, a check reads a run correctly, the judge reads a
reader's answer, and a replaced brief is reported as replaced."""
import json, sys, tempfile, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import stage_check as S


class Lane(unittest.TestCase):
    def test_every_step_has_checks_and_a_fix_or_a_reason(self):
        for st in S.lane("image")["steps"]:
            self.assertTrue(st["checks"], st["id"])
            self.assertTrue(st.get("fix") or st.get("why_no_fix"), st["id"])
            for c in st["checks"]:
                ok, why = True, ""
                self.assertNotIn("unknown check", S.check(FakePiece(), c)[1], c)

    def test_judged_steps_have_criteria(self):
        crit = json.loads((HERE / "criteria.json").read_text())["criteria"]
        for st in S.lane("image")["steps"]:
            if st.get("judge"):
                self.assertIn(st["judge"], crit)


class FakePiece:
    """A run folder in a temp dir with just enough in it."""
    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.lane_run = self.tmp / "run"; (self.lane_run / "out").mkdir(parents=True); (self.lane_run / "vars").mkdir()
        (self.lane_run / "assets").mkdir()
        self.record = self.tmp / "record"; self.pictures = self.record / "pictures"
        self.brand, self.product, self.brief_id, self.rec, self.avatar = "brand", "prod", None, None, None
        self.run_name = "run"
    def out(self, n): return self.lane_run / "out" / n
    def source(self): return {}
    def source_image(self): return None
    def short(self): return None
    label = "run"


class Checks(unittest.TestCase):
    def test_stage_file_needs_real_content(self):
        p = FakePiece()
        self.assertFalse(S.check(p, "stage_file:01-teardown.md")[0])
        p.out("01-teardown.md").write_text("x" * 400)
        self.assertTrue(S.check(p, "stage_file:01-teardown.md")[0])

    def test_wordless_swipe_is_said(self):
        p = FakePiece()
        self.assertTrue(S.check(p, "has_words")[0])
        (p.lane_run / "vars" / "wordless.md").write_text("no words")
        ok, why = S.check(p, "has_words")
        self.assertFalse(ok); self.assertIn("captioned", why)

    def test_gate_reads_check_json(self):
        p = FakePiece()
        (p.lane_run / "check.json").write_text(json.dumps({"copy": {"result": "pass", "problems": []}}))
        self.assertTrue(S.check(p, "gate:copy")[0])
        self.assertFalse(S.check(p, "gate:elements")[0])

    def test_picture_finish_needs_the_polished_twin(self):
        p = FakePiece(); p.pictures.mkdir(parents=True)
        (p.pictures / "a.png").write_bytes(b"x")
        self.assertFalse(S.check(p, "picture_finish")[0])
        (p.pictures / "polished").mkdir(); (p.pictures / "polished" / "a.png").write_bytes(b"x")
        self.assertTrue(S.check(p, "picture_finish")[0])


class Six(unittest.TestCase):
    def test_six_needs_six_distinct_versions(self):
        p = FakePiece(); p.pictures.mkdir(parents=True)
        v = {}
        for i in range(6):
            (p.pictures / f"{i}.png").write_bytes(b"x"); v[f"{i}.png"] = {"h": f"h{i % 3}", "c": f"c{i // 3}"}
        (p.pictures / "variants.json").write_text(json.dumps(v))
        self.assertTrue(S.check(p, "picture_variants")[0])
        v["5.png"] = {"h": "h0", "c": "c0"}                       # a repeat is not a sixth version
        (p.pictures / "variants.json").write_text(json.dumps(v))
        self.assertFalse(S.check(p, "picture_variants")[0])

    def test_a_stopped_headline_stage_fails(self):
        p = FakePiece()
        p.out("04-headlines.md").write_text("**STAGE-2 DEFECT — Missing headline word ceiling** ... stop here")
        self.assertFalse(S.check(p, "headline_set")[0])
        # the variations record (the owner, 2026-10-27: the approved picture + 5 one-change variations)
        rows = [{"id": f"v{i}", "label": f"v{i}", "words": ["w"]} for i in range(1, 6)]
        p.out("variations.json").write_text(json.dumps({"variations": rows}))
        self.assertTrue(S.check(p, "variation_set")[0])
        p.out("variations.json").write_text(json.dumps({"variations": rows[:4]}))
        self.assertFalse(S.check(p, "variation_set")[0])


class Judge(unittest.TestCase):
    def test_reads_a_fail_and_a_pass(self):
        p = FakePiece()
        p.out("03-injection.md").write_text("SWAPS: purple becomes emerald")
        ok, why, failed = S.judge(p, "brand_native", model_call=lambda *a, **k: '{"pass": false, "failed": ["1"], "why": "recolours the room"}')
        self.assertFalse(ok); self.assertEqual(failed, ["1"])
        ok, _, _ = S.judge(p, "brand_native", model_call=lambda *a, **k: 'sure: {"pass": true, "failed": [], "why": ""}')
        self.assertTrue(ok)

    def test_unreadable_answer_fails(self):
        ok, why, _ = S.judge(FakePiece(), "brand_native", model_call=lambda *a, **k: "looks fine to me")
        self.assertFalse(ok); self.assertIn("could not be read", why)


if __name__ == "__main__":
    unittest.main()
