#!/usr/bin/env python3
"""Every entry of the seed catalogue carries a rule-6 status, and both
readers render it exactly as before (SI-75 (send-types status)).

    python3 machine/test_seed_status.py

    a  every entry of types, forms, modifiers and treatments carries a
       components rule 6 `status` (draft / approved / deprecated)
    b  the calendar's render_types gives the same text with and without it
    c  the email chain's render_types gives the same text with and without it

No brand is named here: the seed is the generic catalogue.
"""
import calendar as _stdlib_calendar      # noqa: F401 — cached BEFORE machine/ joins the path,
import json                              # because this folder has a calendar.py of its own
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
SEED = MACHINE.parent / "definitions" / "send-types.seed.json"
EP = MACHINE.parent.parent / "email-production"
sys.path.insert(0, str(MACHINE))

import brandrecord as C                  # noqa: E402

LISTS = ("types", "forms", "modifiers", "treatments")
STATUS_WORDS = {"draft", "approved", "deprecated"}

# email-production has its own `paths` module and `email` is a stdlib name,
# so its renderer runs in a fresh interpreter, loaded by file.
EMAIL_RENDER = """
import importlib.util, sys
sys.path.insert(0, sys.argv[1])
spec = importlib.util.spec_from_file_location("ep_email", sys.argv[1] + "/email.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.stdout.write("\\x00".join(m.render_types(p) for p in sys.argv[2:]))
"""


class SeedStatus(unittest.TestCase):

    def setUp(self):
        d = json.loads(SEED.read_text(encoding="utf-8"))
        for k in LISTS:
            for e in d[k]:
                e.pop("status", None)
        self.tmp = tempfile.TemporaryDirectory()
        self.old = Path(self.tmp.name) / "send-types.seed.json"
        self.old.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_entry_carries_a_rule6_status(self):
        d = json.loads(SEED.read_text(encoding="utf-8"))
        total = 0
        for k in LISTS:
            for e in d[k]:
                self.assertIn(e.get("status"), STATUS_WORDS, "%s/%s" % (k, e.get("key")))
            total += len(d[k])
        self.assertEqual(len(d["types"]), 46)
        self.assertEqual(total, 58)

    def test_the_calendar_renders_the_catalogue_unchanged(self):
        self.assertEqual(C.render_types(SEED), C.render_types(self.old))

    def test_the_email_chain_renders_the_catalogue_unchanged(self):
        r = subprocess.run([sys.executable, "-c", EMAIL_RENDER,
                            str(EP), str(SEED), str(self.old)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        new, old = r.stdout.split("\x00")
        self.assertIn("## Treatments", new)
        self.assertEqual(new, old)


if __name__ == "__main__":
    unittest.main()
