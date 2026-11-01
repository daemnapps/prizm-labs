#!/usr/bin/env python3
"""The out-dir jail — card CR-1's hard done-when, enforced structurally.

A run writes ONLY under `--out`. Not by convention and not by review: every
write this component performs goes through `OutDir`, which resolves the
candidate path and REFUSES anything that does not land under the out root,
naming the offending path. `runner/` contains no other write call site — that
is the property, and the declared test asserts it from the outside by
fingerprinting the tree AROUND the out dir and requiring it byte-unchanged
across a run, including a run that fails.

WHY THIS IS A DONE-WHEN AND NOT A PREFERENCE. A chain engine whose run root
sits inside the tree it runs from writes its outputs into the working copy,
and from that moment "the run" and "the repo" are one place: a run dirties
git, a git operation can eat a run, and anything wrapping the engine cannot
say what a run actually produced. That is the flaw this component exists to
cure, so the cure is a wall, not a habit.

WHAT COUNTS AS AN ESCAPE — every one refused, with the path named:

  - an ABSOLUTE path (`/tmp/x`), including one that happens to sit under the
    root. A caller that already knows the root does not need the jail, and
    accepting absolute paths would make every check below optional;
  - a PARENT TRAVERSAL that leaves the root (`../x`, `a/../../x`);
  - a path crossing an existing SYMLINK at any depth — the classic escape, and
    the one a pure-string check misses;
  - a path resolving to the out root ITSELF (that is a directory, not a file).

A root that is itself a symlink is fine: it is resolved once, up front, and
every candidate is compared against the resolved form.

Known and accepted limit: the symlink check is a check-then-write, so a
symlink planted between the check and the write would defeat it. Closing that
needs `O_NOFOLLOW` per component, which buys nothing against the failure this
card is about — a chain writing where it should not — and costs a portable
implementation. Stated here rather than discovered later.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


class OutDirViolation(Exception):
    """A write was attempted outside the out root. Always fatal to a run."""

    def __init__(self, requested, resolved, reason):
        self.requested = requested
        self.resolved = resolved
        self.reason = reason
        detail = " -> " + str(resolved) if resolved is not None else ""
        Exception.__init__(
            self,
            "OUT-DIR VIOLATION: refused write to {0!r}{1} — {2}".format(
                requested, detail, reason
            ),
        )


class OutDir(object):
    """The only way this component writes a byte.

    `root` is resolved once (symlinks included) and every candidate is checked
    against that resolved form. `written` is the ordered list of relative
    posix paths this run produced — the run record's output list, and what a
    reader consults to ask what a run made.
    """

    def __init__(self, root, create=True):
        self.declared = str(root)
        self.root = os.path.realpath(os.path.abspath(str(root)))
        if create:
            os.makedirs(self.root, exist_ok=True)
        self.written = []

    # ------------------------------------------------------------------ jail

    def resolve(self, relative):
        """The absolute path `relative` names, or raise. No side effects."""
        if not isinstance(relative, str) or not relative.strip():
            raise OutDirViolation(relative, None,
                                  "a write path must be a non-empty string")
        if "\x00" in relative:
            raise OutDirViolation(relative, None,
                                  "a write path may not contain a NUL byte")
        if os.path.isabs(relative):
            raise OutDirViolation(
                relative, relative,
                "absolute write paths are never accepted; give a path "
                "relative to --out")

        root = self.root
        norm = os.path.normpath(os.path.join(root, relative))
        if norm == root:
            raise OutDirViolation(relative, norm,
                                  "resolves to the out root itself, which is "
                                  "a directory and not a writable file")
        if not norm.startswith(root + os.sep):
            raise OutDirViolation(relative, norm,
                                  "resolves outside the out root " + root)

        # No component of the path may be an existing symlink: a symlinked
        # directory under the root can point anywhere, and normpath above
        # cannot see it.
        cursor = root
        for part in os.path.relpath(norm, root).split(os.sep):
            cursor = os.path.join(cursor, part)
            if os.path.islink(cursor):
                raise OutDirViolation(
                    relative, cursor,
                    "path crosses the symlink " + cursor +
                    ", which can point outside the out root")

        # Belt and braces for anything the walk above could not see: the real
        # parent directory must still be under the real root.
        parent = os.path.dirname(norm)
        real_parent = os.path.realpath(parent) if os.path.exists(parent) else parent
        if real_parent != root and not real_parent.startswith(root + os.sep):
            raise OutDirViolation(relative, real_parent,
                                  "the parent directory resolves outside the "
                                  "out root " + root)
        return norm

    def relative(self, absolute):
        return Path(os.path.relpath(str(absolute), self.root)).as_posix()

    # ----------------------------------------------------------------- write

    def write_text(self, relative, text):
        target = self.resolve(relative)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        rel = self.relative(target)
        if rel not in self.written:
            self.written.append(rel)
        return Path(target)

    def write_json(self, relative, document):
        return self.write_text(
            relative,
            json.dumps(document, indent=2, ensure_ascii=False) + "\n")

    # ----------------------------------------------------------------- audit

    def manifest(self):
        """Every file under the root, by relative path, with its sha256 —
        what the run record publishes and what a determinism check diffs."""
        rows = []
        for base, dirs, files in os.walk(self.root):
            dirs.sort()
            for name in sorted(files):
                full = os.path.join(base, name)
                rows.append({
                    "path": self.relative(full),
                    "bytes": os.path.getsize(full),
                    "sha256": sha256_file(full),
                })
        rows.sort(key=lambda row: row["path"])
        return rows


def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ------------------------------------------------------------- root sanity
#
# The jail above answers "may this write happen". These two answer the
# question one level up: "is this a sane place to put a run at all". They are
# separated on purpose — the jail is absolute, this is policy, and policy that
# hides inside a wall is policy nobody can find.

def inspect_root(out_root, component_dir, repo_root=None):
    """(refusals, warnings) for a proposed `--out`.

    REFUSED: an out root inside this component's own folder. A component that
    writes its runs into itself is the exact disease — the folder stops being
    a capability and becomes a run store, and every consumer that was told to
    read the contract starts reading run leftovers instead.

    WARNED, never refused: an out root inside the repo working tree. Runs
    landing in a checkout is how a working copy fills with untracked output,
    but a records adapter writing under `platform/data/` is legitimate and
    deliberate (components/CLAUDE.md rule 3), so this is a loud warning with
    the reason attached rather than a wall in front of the intended use.

    NOT WARNED: an out root under the repo's own `runs/`. That folder is the
    workspace's one home for machine output (runs/README.md: a local run
    "writes to the repo's `runs/` like every other run"), so a run landing
    there is the intended place, not a stray in a checkout — and warning on
    every correctly filed run would teach people to read past the warning
    that matters (CR-9 (chain-runner runs home), the team 2026-10-07).
    """
    refusals = []
    warnings = []
    root = os.path.realpath(os.path.abspath(str(out_root)))
    component = os.path.realpath(os.path.abspath(str(component_dir)))
    if root == component or root.startswith(component + os.sep):
        refusals.append(
            "--out is inside the component itself ({0}). A component that "
            "stores runs in its own folder stops being a capability and "
            "becomes a run store; put runs somewhere the component does not "
            "own.".format(component))
    if repo_root is not None:
        tree = os.path.realpath(os.path.abspath(str(repo_root)))
        runs = os.path.join(tree, "runs")
        in_runs = root == runs or root.startswith(runs + os.sep)
        if not in_runs and (root == tree or root.startswith(tree + os.sep)):
            warnings.append(
                "--out is inside the repo working tree ({0}). This run will "
                "write into a checkout: git will see it, and a git operation "
                "can eat it. Deliberate for a records adapter, a mistake "
                "everywhere else.".format(tree))
    return refusals, warnings
