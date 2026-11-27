"""An email's index.json is the same on every Mac, and opening its steps leaves git clean (email_lead, 2026-11-11: editor's
Done stayed on her Mac because the page rewrote tracked index.json files on every view, and ask.py's pull refused
the dirty tree). No network: a run is written to a temporary folder.

    python3 design/test_index_same_on_every_mac.py
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_index as R  # noqa: E402


def make_run(root, sent=True):
    run = Path(root) / "brand" / "brand-nov-03"
    run.mkdir(parents=True)
    (run / "stage8c--check.md").write_text("all fine")
    if sent:
        (run / "stage8c--sent.md").write_text("THE PROMPT AS SENT")
    (run / "run.json").write_text(json.dumps({"brand": "brand", "label": "brand-nov-03", "stages": {
        "stage8c": {"model": "m", "prompt_name": "stage8c-check-v2-owner.md", "prompt_file": "prompts/none.md",
                    "out": "stage8c--check.md", "sent": "stage8c--sent.md"}}}))
    return run


def step(idx, name):
    return next(x for x in idx["steps"] if x["step"] == name)


class SameOnEveryMac(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_an_unchanged_index_is_not_rewritten(self):
        run = make_run(self.tmp.name)
        R.index(run)
        f = run / "index.json"
        old = time.time() - 3600
        os.utime(f, (old, old))
        R.index(run)
        self.assertEqual(int(f.stat().st_mtime), int(old))

    def test_a_mac_without_the_sent_file_keeps_the_as_sent_prompt(self):
        run = make_run(self.tmp.name)
        first = step(R.index(run), "stage8c")
        self.assertEqual(first["prompt_kind"], "as sent")
        before = (run / "index.json").read_text()
        (run / "stage8c--sent.md").unlink()        # another Mac: git never carried the ignored file
        again = step(R.index(run), "stage8c")
        self.assertEqual(again["prompt_kind"], "as sent")
        self.assertEqual(again["prompt"], "THE PROMPT AS SENT")
        self.assertEqual((run / "index.json").read_text(), before)

    def test_pictures_follow_when_they_were_made_not_file_time(self):
        run = make_run(self.tmp.name)
        for name, made in (("p-b", "2026-11-01T10:00:00"), ("p-a", "2026-11-02T10:00:00")):
            d = run / "media" / "records" / name
            d.mkdir(parents=True)
            (d / "record.json").write_text(json.dumps({"label": name, "made_at": made, "purpose": name}))
        old = time.time() - 3600                   # a checkout gives the later picture the older file time
        os.utime(run / "media" / "records" / "p-a" / "record.json", (old, old))
        pics = [x["step"] for x in R.index(run)["steps"] if x["step"].startswith("picture:")]
        self.assertEqual(pics, ["picture:p-b", "picture:p-a"])


if __name__ == "__main__":
    unittest.main()
