#!/usr/bin/env python3
"""python3 test_workspace_paths.py — no component may reach outside the workspace.

Written 2026-09-23 after a folder move broke sixteen path resolutions at once.
Seven machines moved into components/ that week; each kept counting its way to
the workspace from the depth it had in lab/owner/, so every one of them landed
on ~/Projects — a personal folder, not the repo. Most only read there and failed
loudly. video-production/machine/run.py did not: its DEFAULT_RUNS_ROOT fed a
mkdir(parents=True), so the next run with no explicit --runs-root would have
CREATED ~/Projects/runs/ and filed the whole run outside git and outside Drive.

Two things are checked, both cheap and both static — nothing is imported and
nothing runs:

  1. no `parents[N]` in a component resolves above the workspace root
  2. no component reaches into another repo on this Mac for code or a key
     (~/Projects/outlier, ~/devel/daemn, another repo's .env — cut 2026-09-23)

A path is FOUND by walking up, never counted. `run_kit.paths.repo()` is the
shared way; a local five-line walk-up is fine where importing run-kit is heavier
than the file warrants.
"""
import ast
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COMPONENTS = REPO / "components"

# Third-party trees and this file's own prose are not ours to police.
SKIP_PARTS = {".venv", "__pycache__", "node_modules", "site-packages"}

# A component may anchor deliberately on its own folder or on components/ —
# what it may never do is land above the workspace root.
OUTSIDE = re.compile(r"^(?!" + re.escape(str(REPO)) + r"(/|$))")

REACHERS = re.compile(
    r"Projects/outlier"
    r"|devel/daemn/"
    r"|ecom_data_sync_supabase_demo/\.env")


def files():
    for p in sorted(COMPONENTS.rglob("*.py")):
        if SKIP_PARTS & set(p.parts):
            continue
        if p.resolve() == Path(__file__).resolve():
            continue
        yield p


def code_lines(p):
    """Every source line that is not a comment and not inside a docstring.

    Prose is allowed to say "this used to live in ~/devel" — that is history,
    and several of these files carry exactly that note on purpose. Only code
    is checked.
    """
    src = p.read_text(errors="ignore")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    doc = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
           and isinstance(node.value.value, str):
            doc.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    out = []
    for n, line in enumerate(src.splitlines(), 1):
        if n in doc or line.lstrip().startswith("#"):
            continue
        out.append((n, line))
    return out


class Paths(unittest.TestCase):

    def test_no_counted_path_lands_outside_the_workspace(self):
        bad = []
        for p in files():
            for n, line in code_lines(p):
                m = re.search(r"parents\[(\d+)\]", line)
                if not m:
                    continue
                k = int(m.group(1))
                # The anchor is the file when the expression starts from
                # __file__, and the file's folder when it starts from a HERE
                # that was defined as `.parent`.
                anchor = p.resolve()
                if re.search(r"\b(HERE|_H|ROOT|_P\(__file__\)\.resolve\(\)\.parent\b)\.parents\[", line):
                    anchor = p.resolve().parent
                try:
                    got = anchor.parents[k]
                except IndexError:
                    got = Path("/")
                if OUTSIDE.match(str(got)):
                    bad.append(f"{p.relative_to(REPO)}:{n} parents[{k}] -> {got}")
        self.assertEqual(bad, [], "counted paths resolving outside the workspace:\n  "
                                 + "\n  ".join(bad)
                                 + "\n\nWalk up instead — run_kit.paths.repo().")

    def test_no_component_reaches_into_another_repo(self):
        bad = []
        for p in files():
            for n, line in code_lines(p):
                if REACHERS.search(line):
                    bad.append(f"{p.relative_to(REPO)}:{n} {line.strip()[:80]}")
        self.assertEqual(bad, [], "components reaching outside the workspace:\n  "
                                 + "\n  ".join(bad)
                                 + "\n\nThe code, the cache and the key all live in here "
                                   "(the owner 2026-09-23).")


if __name__ == "__main__":
    unittest.main(verbosity=2)
