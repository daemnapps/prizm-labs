#!/usr/bin/env python3
"""LD-27 (platform shadow fix), then LD-49 (stdlib-name renames), 2026-10-20: the provider/cost chooser is
machine/provider_platform.py, so nothing in this folder shadows Python's own `platform` — proven offline.

    python3 tools/video-production/machine/test_platform_shadow.py

Why: lab_entry_v2.py on the mini (vp-batchtest-meme-dry-20261020) died in googleapiclient/model.py:43
`platform.python_version()` — a script started in machine/ got machine/platform.py. run.py's pin covered
run.py only. Child processes (sys.executable) start with sys.path[0] = machine/, as `python3 machine/x.py`
sets it. No key, no network, nothing written. Stdlib only, 3.9.

  a  there is no platform.py (nor any other stdlib name this hazard has hit) in machine/
  b  a script started in machine/ imports the standard library's `platform`
  c  the Google client stack imports cleanly from there, when it is installed
  d  run.py's and budget.py's chooser is provider_platform (it has resolve_provider and registry)
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STDLIB_HIT = ("platform.py", "calendar.py")        # names that have shadowed the standard library here before

PROBE = r"""
import json, sys, importlib.util
machine = sys.argv[1]
sys.path[0] = machine                                  # as `python3 machine/<script>.py` sets it
import platform
out = {"platform": getattr(platform, "__file__", None), "python_version": hasattr(platform, "python_version")}
try:
    import googleapiclient.model                       # the import that died on the mini
    out["googleapiclient"] = "ok"
except ImportError:
    out["googleapiclient"] = "not installed"
except AttributeError as e:
    out["googleapiclient"] = "SHADOWED: %s" % e
spec = importlib.util.spec_from_file_location("vm_budget_probe", machine + "/budget.py")
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)
chooser = budget._load("provider_platform")
out["chooser"] = [n for n in ("resolve_provider", "registry", "plan") if hasattr(chooser, n)]
out["run_platform"] = None
spec = importlib.util.spec_from_file_location("vm_run_probe", machine + "/run.py")
run = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(run)
    out["run_platform"] = getattr(run.platform, "__file__", None)
except SystemExit:
    pass
print(json.dumps(out))
"""


def probe():
    r = subprocess.run([sys.executable, "-c", PROBE, str(HERE)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-1500:]
    return json.loads(r.stdout.strip().splitlines()[-1])


class NoShadow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = probe()

    def test_a_no_stdlib_name_in_the_folder(self):
        for n in STDLIB_HIT:
            self.assertFalse((HERE / n).exists(), n)
        self.assertTrue((HERE / "provider_platform.py").is_file())

    def test_b_a_script_here_gets_the_standard_library(self):
        self.assertTrue(self.r["python_version"], self.r)
        self.assertFalse(str(self.r["platform"] or "").startswith(str(HERE)), self.r)

    def test_c_the_google_client_imports(self):
        self.assertIn(self.r["googleapiclient"], ("ok", "not installed"), self.r)

    def test_d_the_chooser_is_provider_platform(self):
        self.assertEqual(self.r["chooser"], ["resolve_provider", "registry", "plan"])
        if self.r["run_platform"]:
            self.assertEqual(Path(self.r["run_platform"]).resolve(), (HERE / "provider_platform.py").resolve())


if __name__ == "__main__":
    unittest.main()
