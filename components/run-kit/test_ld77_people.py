#!/usr/bin/env python3
"""run_kit/people.py — THE one answer to "who is this" (LD-77 (one person
resolver)): a person is the team/people/<id>/ whose identity.json lists the
git email, exact and case-insensitive, never the email's local part. Fixture
identity files in temp trees, never the live team/people.

Covers the resolver (exact, case-insensitive, every address shape, unmapped /
empty / ambiguous refused naming the fix, try_person_of, whoami, the CLI's
exit 0 / exit 2), that mini_run's names ARE the resolver's, and the two shell
sites that call the CLI: platform/tools/hats.sh hat_owner (THE acceptance
check — pm-primary@company.com mints dev-pm) and the post-compact hook's
draft, which must never fail.

    /usr/bin/python3 components/run-kit/test_ld77_people.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_kit import paths  # noqa: E402
from run_kit import people as P  # noqa: E402
import mini_run as M  # noqa: E402

REPO = paths.repo(HERE)
CLI = HERE / "run_kit" / "people.py"
HATS = REPO / "platform/tools/hats.sh"
HOOK_DRAFT = REPO / "new-workflow-design/builds/system-path/ld77/drafts/dot-claude/hooks/post-compact.sh"
BASH = "/bin/bash"

FIXTURE = {
    "pm": {"person": "pm", "emails": [{"address": "the team@company.com"},
                                            {"address": "pm-primary@company.com"}]},
    "owner": {"person": "owner", "emails": [{"address": "the owner@company.com"},
                                            {"address": "primary@companyllc.com"}]},
    "plain": {"person": "plain", "emails": ["plain@example.com"]},       # a bare-string entry
    "single": {"person": "single", "email": "Single@Example.com"},       # the singular key
    "broken": "{ not json",
}


def tree(people=None, email=None):
    """A temp checkout: team/people/<id>/identity.json per entry, a copy of the
    resolver where the shell sites look for it, and git with user.email set."""
    root = Path(tempfile.mkdtemp(prefix="ld77-people-")).resolve()
    for folder, body in (FIXTURE if people is None else people).items():
        f = root / P.PEOPLE / folder / "identity.json"
        f.parent.mkdir(parents=True)
        f.write_text(body if isinstance(body, str) else json.dumps(body))
    kit = root / "components/run-kit/run_kit"
    kit.mkdir(parents=True)
    shutil.copy2(str(CLI), str(kit / "people.py"))
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    if email is not None:
        subprocess.run(["git", "-C", str(root), "config", "user.email", email], check=True)
    return root


ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


class Base(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        os.environ.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.roots = []

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        for r in self.roots:
            shutil.rmtree(str(r), ignore_errors=True)

    def tree(self, people=None, email=None):
        r = tree(people, email)
        self.roots.append(r)
        return r


class TheResolver(Base):
    def test_exact_and_case_insensitive(self):
        r = self.tree()
        self.assertEqual(P.person_of(r, "pm-primary@company.com"), "pm")
        self.assertEqual(P.person_of(r, "  PM@Company.com \n"), "pm")
        self.assertEqual(P.person_of(r, "primary@companyllc.com"), "owner")
        self.assertEqual(P.person_of(r, "owner@COMPANY.com"), "owner")

    def test_every_address_shape_an_identity_file_has_used(self):
        r = self.tree()
        self.assertEqual(P.person_of(r, "plain@example.com"), "plain")
        self.assertEqual(P.person_of(r, "single@example.com"), "single")

    def test_never_the_local_part(self):
        r = self.tree()
        for email in ("pm@company.com", "pm@elsewhere.com", "owner@companyllc.com"):
            with self.assertRaises(P.Refused) as cm:
                P.person_of(r, email)
            self.assertIn("team/people/<you>/identity.json", str(cm.exception))
            self.assertIsNone(P.try_person_of(r, email))

    def test_empty_is_refused_naming_the_fix(self):
        r = self.tree()
        for email in ("", "  ", None):
            with self.assertRaises(P.Refused) as cm:
                P.person_of(r, email)
            self.assertIn("identity.json", str(cm.exception))
            self.assertIsNone(P.try_person_of(r, email))

    def test_two_files_claiming_one_address_are_refused_naming_both(self):
        r = self.tree({"designer": {"emails": [{"address": "shared@example.com"}]},
                       "pm": {"emails": [{"address": "Shared@Example.com"}]}})
        with self.assertRaises(P.Refused) as cm:
            P.person_of(r, "shared@example.com")
        msg = str(cm.exception)
        self.assertIn("team/people/designer/identity.json", msg)
        self.assertIn("team/people/pm/identity.json", msg)
        self.assertIsNone(P.try_person_of(r, "shared@example.com"))

    def test_an_unreadable_file_is_skipped_and_handed_to_skipped(self):
        r = self.tree()
        seen = []
        self.assertEqual(P.claimants(r, "pm-primary@company.com", skipped=lambda f, e: seen.append(f.parent.name)),
                         ["pm"])
        self.assertEqual(seen, ["broken"])

    def test_whoami_through_a_git_seam_and_through_git(self):
        r = self.tree(email="the team@Company.com")
        self.assertEqual(P.whoami(r, lambda args, repo: (0, "primary@companyllc.com\n", "")), "owner")
        with self.assertRaises(P.Refused):
            P.whoami(r, lambda args, repo: (1, "", ""))
        self.assertEqual(P.whoami(r), "pm")


class TheCli(Base):
    def cli(self, *argv, cwd=None):
        return subprocess.run([sys.executable, str(CLI)] + list(argv), cwd=str(cwd or "/"),
                              capture_output=True, text=True, env=ENV, timeout=60)

    def test_whoami_prints_the_id_exit_0(self):
        r = self.tree(email="pm-primary@company.com")
        p = self.cli("whoami", "--repo", str(r))
        self.assertEqual((p.returncode, p.stdout), (0, "pm\n"), p.stderr)
        p = self.cli("whoami", "--repo", str(r), "--email", "PRIMARY@companyllc.com")
        self.assertEqual((p.returncode, p.stdout), (0, "owner\n"), p.stderr)

    def test_unmapped_is_the_refusal_on_stderr_exit_2(self):
        r = self.tree(email="pm@company.com")
        p = self.cli("whoami", "--repo", str(r))
        self.assertEqual((p.returncode, p.stdout), (2, ""))
        self.assertIn("team/people/<you>/identity.json", p.stderr)
        p = self.cli("whoami", "--repo", str(r), "--email", "")
        self.assertEqual(p.returncode, 2)
        self.assertIn("identity.json", p.stderr)


class MiniRunIsTheResolver(unittest.TestCase):
    def test_mini_run_names_are_the_resolvers(self):
        self.assertIs(M.person_of, P.person_of)
        self.assertIs(M.whoami, P.whoami)
        self.assertIs(M.Refused, P.Refused)


class HatOwner(Base):
    """THE acceptance check: a hat minted in the team's clone is dev-pm."""

    def owner(self, root, path=None, *arg):
        env = dict(ENV, HATS_WORKSPACE=str(root))
        env.pop("HAT_OWNER", None)
        if path is not None:
            env["PATH"] = path
        script = 'set -u; source "$1"; shift; hat_owner "$@"; echo " rc=$?"'
        return subprocess.run([BASH, "-c", script, "bash", str(HATS)] + list(arg),
                              capture_output=True, text=True, env=env, timeout=60)

    def test_pm_at_company_is_pm(self):
        p = self.owner(self.tree(email="pm-primary@company.com"))
        self.assertEqual(p.stdout, "pm rc=0\n", p.stderr)

    def test_unmapped_returns_2_and_never_guesses(self):
        p = self.owner(self.tree(email="pm@company.com"))
        self.assertEqual(p.stdout, " rc=2\n", p.stderr)

    def test_no_python3_returns_2_never_aborts(self):
        empty = Path(tempfile.mkdtemp(prefix="ld77-nopath-"))
        self.roots.append(empty)
        p = self.owner(self.tree(email="pm-primary@company.com"), str(empty))
        self.assertEqual(p.stdout, " rc=2\n", p.stderr)

    def test_an_explicit_owner_still_wins(self):
        p = self.owner(self.tree(email="pm-primary@company.com"), None, "engineer")
        self.assertEqual(p.stdout, "engineer rc=0\n", p.stderr)


class PostCompactDraft(Base):
    """The hook's draft (the lead applies it over .claude/hooks/post-compact.sh):
    the owner through the resolver, and never a failed hook."""

    def run_hook(self, root):
        plans = root / "team/plans"
        plans.mkdir(parents=True)
        (plans / "dev-pm.md").write_text("# plan\n## BATCH 1\n")
        (plans / "dev-pm.md").write_text("# plan\n## BATCH 9\n")
        return subprocess.run([BASH, str(HOOK_DRAFT)], cwd=str(root), env=ENV, timeout=60,
                              input='{"hook_event_name": "SessionStart", "source": "compact"}',
                              capture_output=True, text=True)

    def test_pm_sees_her_plan_by_her_id(self):
        p = self.run_hook(self.tree(email="pm-primary@company.com"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("dev-pm.md", p.stdout)
        self.assertNotIn("dev-pm.md", p.stdout)

    def test_unmapped_shows_no_plan_and_exits_0(self):
        p = self.run_hook(self.tree(email="pm@elsewhere.com"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("team/plans/", p.stdout)
        self.assertNotIn("identity.json", p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
