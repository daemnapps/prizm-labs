"""index_run cost tracking (LD-56 (footage index in git)): a response's usageMetadata → usage.json's shape
and the per-run ledger's totals; an unpriced model writes cost_usd null with its reason. No model, no network."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import index_run as IR  # noqa: E402

RES = {"usageMetadata": {"promptTokenCount": 1200, "candidatesTokenCount": 300, "thoughtsTokenCount": 50,
                         "totalTokenCount": 1550, "promptTokensDetails": [{"modality": "VIDEO", "tokenCount": 1000}]}}


class Cost(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_usage_of_reads_the_response(self):
        u = IR.usage_of(RES)
        self.assertEqual((u["prompt"], u["candidates"], u["thoughts"], u["total"]), (1200, 300, 50, 1550))
        self.assertEqual(u["by_modality"][0]["modality"], "VIDEO")

    def test_an_unpriced_model_writes_null_and_the_reason(self):
        with mock.patch.object(IR, "rate", lambda model=IR.MODEL: (None, "unpriced in components/models/models.json")):
            e = IR.ledger([IR.usage_of(RES), IR.usage_of(RES)], {"recorded": 2}, 12.4, "acme", "creators", runs=self.tmp)
        self.assertIsNone(e["cost_usd"])
        self.assertIn("unpriced", e["cost_reason"])
        self.assertEqual(e["tokens"]["total"], 3100)
        led = json.loads((self.tmp / "acme" / "creators" / "ledger.json").read_text())
        self.assertEqual(len(led["runs"]), 1)

    def test_a_priced_model_computes_cost(self):
        with mock.patch.object(IR, "rate", lambda model=IR.MODEL: ((0.5, 3.0), None)):
            e = IR.ledger([IR.usage_of(RES)], {"recorded": 1}, 3, "acme", "creators", runs=self.tmp)
        self.assertEqual(e["cost_usd"], round((1200 * 0.5 + 350 * 3.0) / 1e6, 4))

    def test_the_registry_row_today(self):
        r, why = IR.rate()
        self.assertTrue(r is not None or why)        # either a rate or a stated reason, never a silent zero


if __name__ == "__main__":
    unittest.main()
