#!/usr/bin/env python3
"""ad-handoff check 7 — emails only, and a miss says group access is not checked.

    python3 components/ad-handoff/tests/test_group_access.py

Offline: Drive is a fake svc whose permissions().list(...).execute() returns
the grants each case chooses (SI-132 (handoff group honesty)).
"""
import io, sys, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import handoff as H
from test_ad_handoff import AD, build

FOR = "reader@example.com"
NOT_CHECKED = "group or domain access is not checked"
GROUP_CLAUSE = "this folder has group/domain grants, which this check cannot see into"


class _Call:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class _Files:
    """The folder holds the drop's one ad folder (2 pictures with bytes) and its two documents."""
    def list(self, q="", **kw):
        if q.startswith("'FAKEID'"):            # the id build()'s HANDOFF.md links (SI-149 check 1)
            return _Call({"files": [
                {"id": "ADF", "name": AD, "mimeType": "application/vnd.google-apps.folder"},
                {"id": "H", "name": "HANDOFF.md", "mimeType": "text/markdown"},
                {"id": "C", "name": "copy.csv", "mimeType": "text/csv"}]})
        return _Call({"files": [{"name": f"{AD}-a0{i}.png", "size": "9"} for i in (1, 2)]})


class _Perms:
    def __init__(self, perms):
        self.perms = perms

    def list(self, **kw):
        return _Call({"permissions": self.perms})


class FakeSvc:
    def __init__(self, perms):
        self._perms = perms

    def files(self):
        return _Files()

    def permissions(self):
        return _Perms(self._perms)


def user(email):
    return {"type": "user", "role": "reader", "emailAddress": email}


def online(perms):
    """Patch Drive with a fake svc holding these grants."""
    svc = FakeSvc(perms)
    return [mock.patch.object(H, "drive_service", return_value=(None, svc)),
            mock.patch.object(H, "drive_folder", return_value="FAKEID")]


def check(d, perms):
    ps = online(perms)
    for p in ps:
        p.start()
    try:
        return H.run_checks(d, "acme", "260101a", FOR, online=True)
    finally:
        for p in ps:
            p.stop()


class TestGroupAccess(unittest.TestCase):
    def test_an_email_match_passes_as_before(self):
        with tempfile.TemporaryDirectory() as t:
            problems, notes, _ = check(build(t), [user("someone@example.com"), user(FOR.upper())])
            self.assertEqual(problems, [])
            self.assertIn(f"{FOR} can open it", notes)

    def test_a_miss_with_only_user_grants_says_groups_are_not_checked(self):
        with tempfile.TemporaryDirectory() as t:
            problems, _, _ = check(build(t), [user("someone@example.com")])
            self.assertEqual(len(problems), 1, problems)
            self.assertEqual(problems[0],
                             f"{FOR} is not on this folder by email — {NOT_CHECKED}; if they "
                             "reach Shared Assets through a group, share the folder with them "
                             "directly")
            self.assertNotIn(GROUP_CLAUSE, problems[0])
            self.assertNotIn("not on the Shared Assets drive", problems[0])

    def test_a_miss_with_a_group_grant_names_the_group_fact(self):
        with tempfile.TemporaryDirectory() as t:
            perms = [user("someone@example.com"),
                     {"type": "group", "role": "reader", "emailAddress": "team@example.com"}]
            problems, _, _ = check(build(t), perms)
            self.assertEqual(len(problems), 1, problems)
            self.assertIn(NOT_CHECKED, problems[0])
            self.assertTrue(problems[0].endswith(f" ({GROUP_CLAUSE})"), problems[0])

    def test_a_miss_with_a_domain_grant_names_the_group_fact(self):
        with tempfile.TemporaryDirectory() as t:
            problems, _, _ = check(build(t), [{"type": "domain", "role": "reader"}])
            self.assertEqual(len(problems), 1, problems)
            self.assertIn(GROUP_CLAUSE, problems[0])

    def test_ready_cannot_print_on_a_miss(self):
        with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as runs:
            d = build(Path(t) / "acme" / "260101a" / "deliverable")
            out = io.StringIO()
            ps = online([{"type": "group", "role": "reader", "emailAddress": "team@example.com"}])
            ps += [mock.patch.object(H, "RUNS", Path(runs)),
                   mock.patch.object(sys, "argv",
                                     ["handoff.py", "--dir", str(d), "--for", FOR, "--check"])]
            for p in ps:
                p.start()
            try:
                with redirect_stdout(out), self.assertRaises(SystemExit) as ex:
                    H.main()
            finally:
                for p in ps:
                    p.stop()
            self.assertEqual(ex.exception.code, 1)
            self.assertNotIn("READY", out.getvalue())
            self.assertIn("REFUSED", out.getvalue())
            self.assertIn(NOT_CHECKED, out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
