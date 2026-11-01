#!/usr/bin/env python3
"""The lint of LD-77 (one person resolver): nothing turns `git config
user.email` into a person by taking the part before "@". A person is the
team/people/<id>/ whose identity.json lists the address — run_kit/people.py,
the one file allowed to handle the address at all.

A finding is one of these within 5 lines of `user.email`, in any file git
tracks (or would track) outside components/run-kit/run_kit/people.py:

    split("@")[0]   split("@", 1)[0]   partition("@")[0]   cut -d@   ${x%%@*}

Only what RUNS is read: code (CODE suffixes, or a `#!` first line) and the
instruction files Claude follows (`.claude/**/*.md`). Prose and records that
QUOTE the rule — this card's deck, the workflow-request records that carry
its text — derive nobody and are not read. lab/ and test files are REPORTED,
never failed (lab is quarantined; a test's fixture may name an address).
Known non-identity hits are listed by path in ALLOWED with the reason; the
card's three (run-kit test fixtures, lab/damon/control-room/comms.py's phone
jid, atlas/tools/triage_dryrun.py's paths) fall outside the window or are
tests/lab. A `.claude/` file with a draft under DRAFTS is read
AS ITS DRAFT: the maker branch cannot write .claude/, the lead copies each
draft over its original at merge — so this is green on the branch and stays
green after.

    /usr/bin/python3 components/run-kit/test_ld77_no_local_part.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_kit import paths  # noqa: E402

REPO = paths.repo(HERE)
RESOLVER = "components/run-kit/run_kit/people.py"
DRAFTS = "new-workflow-design/builds/system-path/ld77/drafts/dot-claude"
WINDOW = 5
NEAR = "user.email"
PATTERNS = (
    re.compile(r"""\.split\(\s*['"]@['"]\s*(?:,\s*1\s*)?\)\s*\[\s*0\s*\]"""),
    re.compile(r"""\.partition\(\s*['"]@['"]\s*\)\s*\[\s*0\s*\]"""),
    re.compile(r"""\bcut\s+-d\s*['"]?@"""),
    re.compile(r"""\$\{\w+%%@\*\}"""),
)
CODE = (".py", ".sh", ".bash", ".zsh", ".command", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl")
# path -> why its hit is not an identity derivation (none outside lab/tests today)
ALLOWED = {}


def runs(root, rel):
    """Code, or an instruction file Claude follows — not prose that quotes the rule."""
    if rel.endswith(CODE) or (rel.startswith(".claude/") and rel.endswith(".md")):
        return True
    if "." in rel.rsplit("/", 1)[-1]:
        return False
    try:
        with open(str(root / rel), "rb") as f:
            return f.read(2) == b"#!"
    except OSError:
        return False


def reported_only(rel):
    """lab/ and test files: reported, never failed."""
    name = rel.rsplit("/", 1)[-1]
    return (rel.startswith("lab/") or name.startswith("test_") or name.endswith("_test.py")
            or "/tests/" in "/" + rel)


def candidates(root):
    """Every tracked-or-trackable text file under root that mentions user.email."""
    p = subprocess.run(["git", "-C", str(root), "grep", "-I", "-l", "--untracked", "-F", "-e", NEAR],
                       capture_output=True, text=True)
    if p.returncode not in (0, 1):
        raise RuntimeError("git grep failed: " + p.stderr.strip())
    return sorted(set(l for l in p.stdout.splitlines() if l.strip()))


def source_of(root, rel):
    """The text the lint reads for rel: a .claude/ file's draft when one exists."""
    if rel.startswith(".claude/"):
        draft = root / DRAFTS / rel[len(".claude/"):]
        if draft.is_file():
            return draft.read_text(encoding="utf-8", errors="replace")
    return (root / rel).read_text(encoding="utf-8", errors="replace")


def scan(root):
    """[(rel, line number, line)] — every local-part derivation near user.email."""
    hits = []
    for rel in candidates(root):
        if rel == RESOLVER or not runs(root, rel):
            continue
        try:
            lines = source_of(root, rel).splitlines()
        except OSError:
            continue
        near = [i for i, l in enumerate(lines) if NEAR in l]
        for i, line in enumerate(lines):
            if any(p.search(line) for p in PATTERNS) and any(abs(i - j) <= WINDOW for j in near):
                hits.append((rel, i + 1, line.strip()))
    return hits


def split(hits):
    """(failing, reported) — lab/ and tests are reported; ALLOWED paths drop out."""
    failing, reported = [], []
    for h in hits:
        if h[0] in ALLOWED:
            continue
        (reported if reported_only(h[0]) else failing).append(h)
    return failing, reported


class TheRepo(unittest.TestCase):
    def test_no_local_part_derivation_outside_lab_and_tests(self):
        failing, reported = split(scan(REPO))
        for rel, n, line in reported:
            print("reported (lab/test, not failed): %s:%d %s" % (rel, n, line[:120]), file=sys.stderr)
        self.assertEqual(failing, [], "a person derived from the email's local part — resolve it "
                                      "through %s instead:\n%s" % (RESOLVER, "\n".join(
                                          "  %s:%d %s" % h for h in failing)))

    def test_every_draft_mirrors_a_live_claude_file(self):
        """A draft whose original is gone would shadow nothing and hide nothing."""
        drafts = REPO / DRAFTS
        for f in sorted(p for p in drafts.rglob("*") if p.is_file()) if drafts.is_dir() else []:
            self.assertTrue((REPO / ".claude" / f.relative_to(drafts)).is_file(), str(f))


class APlantedLine(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ld77-lint-"))
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=True)

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def plant(self, rel, text):
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def test_the_cards_fixture_line_is_caught(self):
        self.plant("platform/tools/x.sh", "#!/bin/bash\nowner=$(git config user.email | cut -d@ -f1)\n")
        failing, _ = split(scan(self.tmp))
        self.assertEqual([(r, n) for r, n, _ in failing], [("platform/tools/x.sh", 2)])

    def test_every_shape_within_the_window_and_none_outside_it(self):
        self.plant("a.py", 'e = git("config", "user.email")\nwho = e.split("@")[0]\n'
                           'who = e.split("@", 1)[0]\nwho = e.partition("@")[0]\n')
        self.plant("b.sh", 'e=$(git config user.email)\nwho="${e%%@*}"\n')
        self.plant("c.py", 'e = git("config", "user.email")\n' + "\n" * 6 + 'jid = x.split("@")[0]\n')
        failing, _ = split(scan(self.tmp))
        self.assertEqual(sorted((r, n) for r, n, _ in failing),
                         [("a.py", 2), ("a.py", 3), ("a.py", 4), ("b.sh", 2)])

    def test_lab_and_tests_are_reported_not_failed_and_the_resolver_is_exempt(self):
        line = "owner=$(git config user.email | cut -d@ -f1)\n"
        for rel in ("lab/someone/x.sh", "components/c/test_x.py", "components/c/tests/y.sh", RESOLVER):
            self.plant(rel, line)
        failing, reported = split(scan(self.tmp))
        self.assertEqual(failing, [])
        self.assertEqual(sorted(r for r, _, _ in reported),
                         ["components/c/test_x.py", "components/c/tests/y.sh", "lab/someone/x.sh"])

    def test_code_and_instructions_are_read_and_prose_that_quotes_the_rule_is_not(self):
        line = "owner=$(git config user.email | cut -d@ -f1)\n"
        self.plant("bin/tool", "#!/bin/bash\n" + line)
        self.plant(".claude/skills/s/SKILL.md", line)
        self.plant("builds/deck/task-cards.md", line)
        self.plant("platform/data/records/r/x.json", '{"instruction": "%s"}\n' % line.strip())
        failing, _ = split(scan(self.tmp))
        self.assertEqual(sorted(r for r, _, _ in failing), [".claude/skills/s/SKILL.md", "bin/tool"])

    def test_a_claude_file_is_read_as_its_draft(self):
        line = "OWNER=$(git config user.email | cut -d@ -f1)\n"
        self.plant(".claude/hooks/h.sh", line)
        failing, _ = split(scan(self.tmp))
        self.assertEqual([r for r, _, _ in failing], [".claude/hooks/h.sh"])
        self.plant(DRAFTS + "/hooks/h.sh", "OWNER=$(python3 people.py whoami)  # user.email\n")
        failing, _ = split(scan(self.tmp))
        self.assertEqual(failing, [])


if __name__ == "__main__":
    unittest.main()
