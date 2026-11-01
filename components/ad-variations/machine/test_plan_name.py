"""SI-133 (ad-variations plan name): the contract file is variation-plan.json, so it
stops colliding with image-edit's and image-teardown's files of the old name. assemble
writes only the new name; the page reads the new name and, for runs made before the
rename, the old one. Offline; every tree is a temp folder."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
sys.path.insert(0, str(COMP.parent / "run-kit"))
sys.path.insert(0, str(HERE))
import assemble  # noqa: E402
import page  # noqa: E402

OLD = "variations" + ".json"            # spelled apart so this file is not a hit for the grep below
OLD_RE = re.compile("variations" + r"\.json")


class _Run:
    def __init__(self, d):
        self.dir = d
        self.metrics = {}


def _doc(rank, label):
    return {"schema": "ad-variations/1", "brand": "zz-brand", "built": "2026-10-08T00:00:00",
            "source": {"teardown_run": f"runs/video-teardown/zz-brand/{label}", "metrics": {"rank": rank}}}


class PlanName(unittest.TestCase):
    def test_assemble_writes_the_new_name_only(self):
        with tempfile.TemporaryDirectory() as t:
            repo = Path(t)
            run_dir = repo / "runs" / "video-teardown" / "zz-brand" / "r1"
            out = repo / "runs" / "ad-variations" / "zz-brand" / "r1"
            run_dir.mkdir(parents=True)
            out.mkdir(parents=True)
            texts = {f"stage{n}": "" for n in range(1, 8)}
            assemble.build(repo, "zz-brand", _Run(run_dir), {"built": "x", "runs": 0}, out, texts, None, {})
            self.assertTrue((out / "variation-plan.json").is_file())
            self.assertFalse((out / OLD).exists())
            self.assertEqual(json.loads((out / "variation-plan.json").read_text())["schema"], "ad-variations/1")
            self.assertIn("`variation-plan.json`", (out / "VARIATIONS.md").read_text())

    def test_page_reads_new_and_old_names(self):
        with tempfile.TemporaryDirectory() as t:
            repo = Path(t)
            root = repo / "runs" / "ad-variations" / "zz-brand"
            a, b, c = root / "run-a", root / "run-b", root / "run-c"
            for d in (a, b, c):
                d.mkdir(parents=True)
            (a / "variation-plan.json").write_text(json.dumps(_doc(1, "run-a")))
            (b / OLD).write_text(json.dumps(_doc(2, "run-b")))
            # a run holding both: the new name wins, the run is counted once
            (c / "variation-plan.json").write_text(json.dumps(_doc(3, "run-c-new")))
            (c / OLD).write_text(json.dumps(_doc(3, "run-c-old")))
            files = page.contract_files(repo)
            self.assertEqual(files, [a / "variation-plan.json", b / OLD, c / "variation-plan.json"])
            _, runs, _, _ = page.load(repo)
            self.assertEqual([Path(d["source"]["teardown_run"]).name for d in runs], ["run-a", "run-b", "run-c-new"])

    def test_old_name_only_in_the_page_fallback(self):
        hits = []
        for f in sorted(COMP.rglob("*.py")):
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if OLD_RE.search(line):
                    hits.append((f.relative_to(COMP).as_posix(), line))
        self.assertEqual(len(hits), 1, hits)
        self.assertEqual(hits[0][0], "machine/page.py")
        self.assertIn("OLD_CONTRACT =", hits[0][1])


if __name__ == "__main__":
    unittest.main()
