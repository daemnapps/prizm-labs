#!/usr/bin/env python3
"""python3 machine/test_sectionfit.py — the section-fit gate with a fake checker. No network."""
import importlib.util, json, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("t_sf", HERE / "sectionfit.py"); sf = importlib.util.module_from_spec(spec); spec.loader.exec_module(sf)
PLAN = {"framework": "us-vs-them", "scenes": [
    {"id": "S1", "section": "hook", "to_camera": True, "voice": "I'm at the clinic about my spots."},
    {"id": "S2", "section": "solution", "to_camera": False, "voice": "Do a little dot of the prescription cream."}]}

def fake(reply):
    return lambda prompt: json.dumps(reply)

class Gate(unittest.TestCase):
    def test_the_prompt_carries_the_doctrine_and_the_words(self):
        seen = {}
        def call(p):
            seen["p"] = p
            return json.dumps({"scenes": [], "order": []})
        sf.check(PLAN, call=call)
        self.assertIn("failed-solutions", seen["p"])
        self.assertIn("prescription cream", seen["p"])
        self.assertIn("`solution`", seen["p"])

    def test_absent_run_rulings_preserve_legacy_request_bytes(self):
        import sys
        sys.path.insert(0, str(sf.WS / "components/run-kit"))
        from run_kit import prompts as P
        expected = P.fill(Path(P.latest(sf.PROMPTS, "stage0c-section-fit")).read_text(), {
            "sections": (sf.WS / "components/marketing-doctrine/slices/sections.md").read_text(),
            "framework": PLAN["framework"], "awareness": json.dumps("not named"),
            "scenes": sf.scenes_text(PLAN)})
        sent = []
        sf.check(PLAN, call=lambda p: sent.append(p) or '{"scenes": [], "order": []}')
        self.assertEqual(sent, [expected] * 3)

    def test_full_rulings_change_cache_but_do_not_force_pass(self):
        import tempfile
        rules = "Source: signed instruction. The opening is hook.\n" + "Source detail.\n" * 6000 + "END OF SOURCE"
        sent = []
        reply = {"scenes": [{"id": "S2", "given": "solution", "fits": False,
                            "should_be": "failed-solutions", "why": "Unruled rival pitch"}], "order": []}
        def call(p):
            sent.append(p)
            return json.dumps(reply)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            first = sf.check(PLAN, out, call=call, run_rulings=rules)
            self.assertFalse(first["pass"])
            self.assertEqual(first["misfits"][0]["id"], "S2")
            self.assertEqual(len(sent), 3)
            self.assertTrue(all(p.endswith(rules) for p in sent))
            self.assertEqual((out / "sent.md").read_text(), sent[-1])
            sf.check(PLAN, out, call=call, run_rulings=rules)
            self.assertEqual(len(sent), 3)
            changed = sf.check(PLAN, out, call=call, run_rulings=rules + "\nUpdated source.")
            self.assertEqual(len(sent), 6)
            self.assertNotEqual(changed["sent_hash"], first["sent_hash"])
            self.assertFalse(changed["pass"])

    def test_a_misfit_stops(self):
        r = sf.check(PLAN, call=fake({"scenes": [{"id": "S1", "given": "hook", "fits": True, "should_be": "hook", "why": "entry"},
                                                   {"id": "S2", "given": "solution", "fits": False, "should_be": "failed-solutions", "why": "a rival pitch"}], "order": []}))
        self.assertFalse(r["pass"])
        self.assertEqual(r["misfits"][0]["should_be"], "failed-solutions")

    def test_all_fit_passes(self):
        r = sf.check(PLAN, call=fake({"scenes": [{"id": "S1", "given": "hook", "fits": True, "should_be": "hook", "why": "x"}], "order": []}))
        self.assertTrue(r["pass"])

    def test_an_order_problem_is_a_warning_not_a_stop(self):
        r = sf.check(PLAN, call=fake({"scenes": [], "order": ["S10 offer card plays before the objection"]}))
        self.assertTrue(r["pass"])
        self.assertEqual(len(r["order"]), 1)

    def test_relabel_fixes_the_brief_at_source_and_keeps_the_words(self):
        import tempfile
        f = Path(tempfile.mkdtemp()) / "brief.md"
        f.write_text("# brief\n\n```json\n" + json.dumps(PLAN) + "\n```\n")
        res = {"misfits": [{"id": "S2", "given": "solution", "fits": False, "should_be": "failed-solutions", "why": "a rival pitch"}], "order": []}
        changes = sf.relabel(f, res)
        self.assertEqual(len(changes), 1)
        d = sf.plan_of(f)
        self.assertEqual(d["scenes"][1]["section"], "failed-solutions")
        self.assertEqual(d["scenes"][1]["voice"], PLAN["scenes"][1]["voice"])
        self.assertIn("Section check (automatic", f.read_text())

    def test_a_made_up_section_from_the_checker_is_a_misfit(self):
        r = sf.check(PLAN, call=fake({"scenes": [{"id": "S1", "given": "hook", "fits": True, "should_be": "social-proof", "why": "x"}], "order": []}))
        self.assertFalse(r["pass"])

if __name__ == "__main__":
    unittest.main()
