#!/usr/bin/env python3
"""One version per send (2026-11-04): with --one-version the month line writes a send's first version only, under
the same label as before; without it, one version per audience the send names. No model, no chain, no key."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix="one-version-")).resolve()
os.environ["AI_WORKSPACE"] = str(TMP)            # before anything imports paths.py

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_month as M                              # noqa: E402

SLOTS = [{"id": "nov-01", "date": "2026-11-20", "type": "sale-window", "segment": "S",
          "variants": [{"avatar": "a", "angle": "x"}, {"avatar": "b", "angle": "y"}]},
         {"id": "nov-02", "date": "2026-11-21", "type": "sale-window", "segment": "S",
          "variants": [{"avatar": "a", "angle": "z"}]}]


def labels(*extra):
    d = TMP / "month"
    d.mkdir(exist_ok=True)
    (d / "slots.json").write_text(json.dumps(SLOTS))
    (d / "run.json").write_text(json.dumps({"brand": "zz"}))
    got = {}

    def produce(jobs, *a, **k):
        got["labels"] = [lab for lab, _ in jobs]
        return 0
    with mock.patch.object(M, "produce", produce), mock.patch.object(M.brief, "chain_argv", return_value=["x"]), \
            mock.patch.object(M.brief, "label_prefix", return_value=""), \
            mock.patch.object(M.EE, "type_problem", return_value=None), \
            mock.patch("reviewed_plan.reviewed", lambda _d, s: [dict(x, _review={"note": None, "edits": []}) for x in s]), \
            mock.patch.object(sys, "argv", ["run_month.py", str(d), *extra]):
        with self_exit():
            M.main()
    return got["labels"]


class self_exit:
    def __enter__(self):
        return self

    def __exit__(self, kind, *_):
        return kind is SystemExit


class OneVersion(unittest.TestCase):
    def test_the_default_writes_one_per_audience(self):
        self.assertEqual(labels(), ["nov-01--a", "nov-01--b", "nov-02"])

    def test_the_switch_writes_the_first_only_under_the_same_label(self):
        self.assertEqual(labels("--one-version"), ["nov-01--a", "nov-02"])

    def test_only_labels_leaves_a_sends_other_versions_as_written(self):
        self.assertEqual(labels("--only-labels", "nov-01--b"), ["nov-01--b"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
