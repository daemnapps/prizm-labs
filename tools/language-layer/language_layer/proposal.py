"""A proposed change to a brand's language bank — written under `runs/`,
never into `brands/`.

`brands/` is read-only to machines (decision-log 2026-09-17), with no
carve-out: K2 (brands write wall) in `components/system-integration/conventions.md`
retired the research gatherer's old O5 (brands read-only) carve-out. So the
bank tools here write what they WOULD change — every row, every field, as
data — plus a readable summary, into
`runs/language-layer/<brand>/<run-label>/`:

    proposal.json   the change, row by row (the file the gatherer applies)
    proposal.md     what it changes, in counts and examples

and hand the proposal to the gatherer's apply step
(`components/research-gatherer/gather.py apply --proposal <path>`), which
checks every change against its gates and is the only thing that writes.

Shape (version 1):

    {"kind": "language-bank-proposal", "version": 1, "brand", "tool", "made",
     "summary": {...},
     "rows":  [{"file": "brands/<b>/core-avatars/…/x.json", "id", "index",
                "text_sha", "set": {field: value}}],
     "used":  [{"file": "brands/<b>/…/language/used/x.json", "index",
                "row_id", "new_row_id"}],
     "write": [{"file": "brands/<b>/core-avatars/language-sources.json",
                "content": {...}}]}

A row is found by its id (the index is a hint when an id repeats) and must
still carry the words the proposal read (`text_sha`).
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

KIND = "language-bank-proposal"
VERSION = 1


def text_sha(text):
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]


def rel(path):
    """`brands/…` — the path from the tree that holds `brands/`, so the same
    proposal applies in any checkout."""
    parts = Path(path).parts
    return "/".join(parts[parts.index("brands"):])


class Proposal:
    def __init__(self, brand, tool, folder):
        self.brand, self.tool, self.folder = brand, tool, Path(folder)
        self.rows, self.used, self.write = [], [], []

    def row(self, f, index, entry, **fields):
        self.rows.append({"file": rel(f), "id": entry.get("id"), "index": index,
                          "text_sha": text_sha(entry.get("text")), "set": fields})

    def used_mark(self, f, index, row_id, new_row_id):
        self.used.append({"file": rel(f), "index": index, "row_id": row_id,
                          "new_row_id": new_row_id})

    def whole(self, f, content):
        self.write.append({"file": rel(f), "content": content})

    @property
    def path(self):
        return self.folder / "proposal.json"

    def load(self):
        """Pick up a proposal this run already started (a stopped label run)."""
        if self.path.is_file() and not (self.folder / "applied.json").is_file():
            d = json.loads(self.path.read_text())
            self.rows, self.used, self.write = d.get("rows", []), d.get("used", []), d.get("write", [])
        return self

    def save(self, summary=None, examples=None):
        self.folder.mkdir(parents=True, exist_ok=True)
        made = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        summary = dict(summary or {}, rows=len(self.rows), used_marks=len(self.used),
                       whole_files=len(self.write))
        self.path.write_text(json.dumps(dict(
            kind=KIND, version=VERSION, brand=self.brand, tool=self.tool, made=made,
            summary=summary, rows=self.rows, used=self.used, write=self.write),
            indent=1, ensure_ascii=False) + "\n")
        fields = {}
        for r in self.rows:
            for k in r["set"]:
                fields[k] = fields.get(k, 0) + 1
        files = sorted({r["file"] for r in self.rows} | {u["file"] for u in self.used}
                       | {w["file"] for w in self.write})
        md = [f"# Proposal — {self.tool} — {self.brand} — {made}", "",
              "A proposed change to the language bank. Nothing under `brands/` has "
              "changed yet: the research gatherer's apply step checks every row "
              "below and is the only thing that writes it.", "",
              "## Counts", ""]
        md += [f"- {k.replace('_', ' ')}: {v}" for k, v in summary.items()]
        if fields:
            md += ["", "## Fields set", ""] + [f"- `{k}` on {v:,} rows" for k, v in sorted(fields.items())]
        md += ["", f"## Files ({len(files)})", ""] + [f"- `{x}`" for x in files[:60]]
        if len(files) > 60:
            md.append(f"- … and {len(files) - 60} more")
        if examples:
            md += ["", "## Examples", ""] + [f"- {e}" for e in examples[:12]]
        md += ["", "## Apply", "", "```",
               f"python3 components/research-gatherer/gather.py apply --proposal {rel_run(self.path)}",
               "```", ""]
        (self.folder / "proposal.md").write_text("\n".join(md))
        return self.path


def rel_run(path):
    parts = Path(path).parts
    return "/".join(parts[parts.index("runs"):]) if "runs" in parts else str(path)


def hand_off(path, root=None, dry_run=False):
    """Hand a proposal to the one machine that may write the bank — the
    research gatherer, this component's sibling under components/. Returns
    its exit code; it prints what it applied and skipped."""
    gather = Path(__file__).resolve().parents[3] / "components" / "research-gatherer" / "gather.py"
    if not gather.is_file():
        print(f"research gatherer not found at {gather} — the proposal stays at {path}; nothing applied")
        return 3
    cmd = [sys.executable, str(gather), "apply", "--proposal", str(path)]
    if root:
        cmd += ["--root", str(root)]
    if dry_run:
        cmd.append("--dry-run")
    return subprocess.call(cmd)
