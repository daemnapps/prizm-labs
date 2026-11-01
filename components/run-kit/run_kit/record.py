"""run.json — what the run was TOLD to do, and what wrote each step.
Lifted from email.py:693-707 (assignment, models) and video-teardown
run.py:1195 (per-variable provenance)."""
import datetime
import json
from pathlib import Path

from . import paths as _paths


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


class Record:
    def __init__(self, out_dir, tool, brand, label, assignment=None):
        self.path = Path(out_dir) / "run.json"
        self.state = {"tool": tool, "brand": brand, "label": label,
                      "assignment": assignment or {}, "generated_at": now(), "stages": {}}
        if self.path.is_file():
            try:
                old = _paths.local(json.loads(self.path.read_text()))   # stored paths read back (rule 4)
                self.state["stages"] = old.get("stages", {})
            except ValueError:
                pass

    def stage(self, key, **fields):
        self.state["stages"][key] = fields
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # builder card rule 4 (stored data references): repo-relative paths and "Shared Assets/…" on disk
        self.path.write_text(_paths.portable(json.dumps(self.state, indent=2, ensure_ascii=False)) + "\n")
