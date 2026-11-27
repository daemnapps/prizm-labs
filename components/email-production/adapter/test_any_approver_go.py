"""Any approver's Go counts, whoever is available (email_lead, 2026-11-05).

  1  a Go or a "scheduled" from each name on approvers.json is read as a request
  2  a Go or a "scheduled" from someone not on the list (editor, the role default) is refused, and the refusal names
     the approvers
  3  an empty or unreadable approvers.json refuses everyone
No network, no key, no git: parse() only.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ask  # noqa: E402

BRAND, LABEL = "brand-x", "brand-x-nov-01"


def line(act, who=None):
    tail = " (from %s)" % who if who else ""
    return "Email request (nov-01): nov-01 [%s/%s] · %s%s" % (BRAND, LABEL, act, tail)


class AnyApproverGo(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.f = self.tmp / "approvers.json"
        self.f.write_text(json.dumps({"approvers": ["owner", "email_lead", "designer"]}))
        self.p = mock.patch.object(ask, "APPROVERS_F", self.f)
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_1_each_approver_counts(self):
        for who in ("owner", "email_lead", "designer"):
            for act in ("make the Klaviyo draft (Go)", "I scheduled it in Klaviyo"):
                k, why = ask.parse(line(act, who))[0]
                self.assertIsNone(why, (who, act, why))
                self.assertEqual(k["action"], "go" if "Go" in act else "scheduled")

    def test_2_others_refused(self):
        for who in ("editor", None):
            for act in ("make the Klaviyo draft (Go)", "I scheduled it in Klaviyo"):
                k, why = ask.parse(line(act, who))[0]
                self.assertIsNone(k)
                self.assertIn("only an approver", why)
                self.assertIn("designer", why)

    def test_3_empty_list_refuses_everyone(self):
        self.f.write_text(json.dumps({"approvers": []}))
        k, why = ask.parse(line("make the Klaviyo draft (Go)", "email_lead"))[0]
        self.assertIsNone(k)
        self.f.write_text("not json")
        k, why = ask.parse(line("make the Klaviyo draft (Go)", "email_lead"))[0]
        self.assertIsNone(k)


if __name__ == "__main__":
    unittest.main()
