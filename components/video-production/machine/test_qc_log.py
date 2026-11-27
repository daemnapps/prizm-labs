import json, tempfile, unittest
from pathlib import Path
import qc_log


class QcLog(unittest.TestCase):
    """Every QC round files itself beside the run (2026-10-02)."""

    def test_rounds_file_and_count(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d)
            self.assertEqual(qc_log.add(run, "chain checks", "qc.py", []), 1)
            n = qc_log.add(run, "pictures", "reviewer", {"S1-F1": {"ok": True}, "S2-F1": {"ok": False, "problems": ["too wide"]}})
            self.assertEqual(n, 2)
            log = (run / "qc-log" / "QC-LOG.md").read_text()
            self.assertIn("| 2 |", log); self.assertIn("S2-F1: too wide", log); self.assertIn("| 1 | 1 |", log)
            self.assertTrue((run / "qc-log" / "pictures-r2-reviewer.json").exists())
            self.assertTrue(qc_log.fix(run, 2, "CHAIN-FIXES 99"))
            self.assertIn("CHAIN-FIXES 99", (run / "qc-log" / "QC-LOG.md").read_text())


if __name__ == "__main__":
    unittest.main()
