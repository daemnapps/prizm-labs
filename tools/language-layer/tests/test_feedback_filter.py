#!/usr/bin/env python3
"""The feedback-form filters on the query — `area` and `feedback_stage`
(components/feedback-forms, 2026-09-29). A fixture tree, no network, no real brand.

    python3 -m unittest discover -s tests          # from tools/language-layer
"""
import io, json, sys, tempfile, unittest, contextlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import engine as E  # noqa: E402


def fixture(root):
    lang = Path(root) / "brands" / "fx" / "core-avatars" / "a1" / "language"
    lang.mkdir(parents=True)
    rows = [dict(id="f1", text="shipping took three weeks", use="objection",
                 feedback={"stage": "churned-refund", "areas": ["operations", "customer-service"]}),
            dict(id="f2", text="the site never said how to use it", use="objection",
                 feedback={"stage": "new-customer", "areas": ["website"]}),
            dict(id="f3", text="nothing else cleared my bumps", use="why-bought",
                 feedback={"stage": "new-customer", "areas": ["marketing"]}),
            dict(id="c1", text="a comment with no form behind it", use="objection")]
    (lang / "leads.json").write_text(json.dumps({"schema": 1, "entries": rows}))


class FeedbackFilter(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        fixture(self.root)
        self.rows = E.load("fx", root=self.root)

    def tearDown(self):
        self._t.cleanup()

    def ids(self, **kw):
        return sorted(r["id"] for r in E.query(self.rows, **kw))

    def test_area(self):
        self.assertEqual(self.ids(area="operations"), ["f1"])
        self.assertEqual(self.ids(area="website"), ["f2"])

    def test_stage(self):
        self.assertEqual(self.ids(feedback_stage="new-customer"), ["f2", "f3"])

    def test_both_and_with_tags(self):
        self.assertEqual(self.ids(feedback_stage="new-customer", area="marketing"), ["f3"])
        self.assertEqual(self.ids(use=["objection"], feedback_stage="new-customer"), ["f2"])

    def test_no_filter_keeps_everything(self):
        self.assertEqual(self.ids(), ["c1", "f1", "f2", "f3"])

    def test_cli_flags_and_header(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            E.main(["--brand", "fx", "--root", str(self.root), "--area", "website", "--feedback-stage", "new-customer"])
        out = buf.getvalue()
        self.assertIn("[f2]", out)
        self.assertNotIn("[f3]", out)
        self.assertIn("feedback-form rows serving website", out)
        self.assertIn("from the new-customer feedback stage", out)


if __name__ == "__main__":
    unittest.main()
