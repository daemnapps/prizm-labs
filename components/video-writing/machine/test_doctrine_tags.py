#!/usr/bin/env python3
"""Doctrine tags: times decide which doctrine sections, techniques and phase a scene carries (no model in this test).

    python3 components/video-writing/machine/test_doctrine_tags.py
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import doctrine_tags as D  # noqa: E402

DOC = """**FRAMEWORK:** Story (life · tried · found · now)

**SECTIONS CARRIED:**
hook 0:00–0:08
the consequence (candidate for the bank) 0:08–0:20

**AWARENESS ENTRY:** problem-aware.

**TECHNIQUES OBSERVED:**
```
hook · camouflage · Register — understatement · 0:00–0:02 · "I stole a bottle"
```

**MOOD:** warm.
"""
TEAR = """**Phase 1: The Confession (0:00 - 0:36)**
*   Emotion: Intrigue, slight guilt.
"""


class Tags(unittest.TestCase):
    def test_times_decide_the_tags(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "stages").mkdir()
            (Path(d) / "stages" / "1c-doctrine.md").write_text(DOC)
            (Path(d) / "stages" / "1-teardown.md").write_text(TEAR)
            doc, ph = D.doctrine(d), D.phases(d)
        self.assertEqual([c["name"] for c in doc["carried"]], ["hook", "the consequence"])
        self.assertTrue(doc["carried"][1]["bank"])
        self.assertEqual(doc["techniques"][0]["lever"], "camouflage")
        self.assertEqual(ph[0]["emotion"], "Intrigue, slight guilt.")
        self.assertTrue(D.overlaps(0, 4, 0, 8))
        self.assertFalse(D.overlaps(0, 4, 8, 20))


if __name__ == "__main__":
    unittest.main()
