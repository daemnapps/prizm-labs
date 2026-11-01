"""SI-116 (audit fix offer): the audit-fix prompt names the batch's own offer,
never a fixed one. Offline — subprocess.run and the chain's environment are
patched, so no model is called and no key is read; every tree is a temp folder."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
with contextlib.redirect_stderr(io.StringIO()):
    import proven_to_format as P2F  # noqa: E402

OFFER = "zz offer: three for the price of two"
OLD = "buy 2, get 1"
SCRIPT = "\n".join(f"line {i}: the script says the same thing it said" for i in range(20)) + "\n"


def _square(root):
    d = Path(root) / "sq-zz"
    (d / "stages").mkdir(parents=True)
    (d / "stages" / "4e-close.md").write_text(SCRIPT)
    (d / "AUDIT-HOLD.md").write_text("| A1 | offer reads wrong |\n")
    (d / "run.json").write_text(json.dumps({"stages": {"stage4d": {}, "stage4e": {}}}))
    return d


class AuditOffer(unittest.TestCase):
    def _fix(self, d, offer):
        done = unittest.mock.Mock(returncode=0, stdout=SCRIPT, stderr="")
        with unittest.mock.patch.object(P2F.subprocess, "run", return_value=done) as run, \
                unittest.mock.patch.object(P2F, "_chain_env", return_value={}):
            P2F.fix_audit(d, ["A1"], offer)
        self.assertEqual(run.call_count, 1)
        return run.call_args[1]["input"]

    def test_prompt_carries_the_passed_offer(self):
        with tempfile.TemporaryDirectory() as t:
            prompt = self._fix(_square(t), OFFER)
        self.assertIn(f"make the offer read '{OFFER}' only", prompt)
        self.assertNotIn(OLD, prompt)

    def test_a_different_offer_reads_through(self):
        with tempfile.TemporaryDirectory() as t:
            prompt = self._fix(_square(t), "zz second offer")
        self.assertIn("make the offer read 'zz second offer' only", prompt)
        self.assertNotIn(OFFER, prompt)

    def test_rest_of_the_fix_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            d = _square(t)
            prompt = self._fix(d, OFFER)
            self.assertIn("checks A1", prompt)
            self.assertIn("=== THE SCRIPT ===\n" + SCRIPT, prompt)
            self.assertEqual((d / "stages" / "4e-close.md").read_text(), SCRIPT.strip() + "\n")
            self.assertTrue((d / "AUDIT-HOLD-fixed-A1.md").is_file())
            st = json.loads((d / "run.json").read_text())
            self.assertNotIn("stage4e", st["stages"])
            self.assertEqual(st["fixed_audit"], [["A1"]])

    def test_run_square_passes_the_batch_offer(self):
        b = {"offer": OFFER, "brand": "zz-brand", "route": "ai", "product": "zz-product", "avatar": "a1"}
        with tempfile.TemporaryDirectory() as t:
            d = _square(t)
            with unittest.mock.patch.object(P2F.swipe_home, "resolve", return_value=Path(t) / "v.mp4"), \
                    unittest.mock.patch.object(P2F, "next_stage", return_value=("stage4d", "4e")), \
                    unittest.mock.patch.object(P2F, "holds", return_value=([], ["A1"])), \
                    unittest.mock.patch.object(P2F, "fix_audit") as fix, \
                    contextlib.redirect_stdout(io.StringIO()):
                P2F.run_square(b, d, {"video": "v.mp4"}, tries=1)
        fix.assert_called_once_with(d, ["A1"], OFFER)

    def test_source_has_no_fixed_offer(self):
        self.assertNotIn(OLD, (HERE / "proven_to_format.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
