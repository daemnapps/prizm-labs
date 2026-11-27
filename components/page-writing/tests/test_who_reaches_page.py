"""Who the page is for (creative-strategist who.py), with the desire and belief doctrine, is really in the prompt that is
sent to the writing step and the fix step. A made-up brand on disk, no model, no network.

    python3 components/page-writing/tests/test_who_reaches_page.py
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "machine"))
import write as PW       # noqa: E402
sys.path.append(str(HERE.parents[1] / "creative-strategist" / "tests"))
import test_who as TW    # noqa: E402  its made-up brand: acme · sore-foot · sub-01-runner
import who as W          # noqa: E402

CARD = "my heel barks at mile two"
BAD = {"title": "t", "sections": [{"n": 1, "blocks": [{"type": "quote", "text": "made up", "rows": ["nope"]}]}]}


class Page(unittest.TestCase):
    def setUp(self):
        self.b = TW.Who("test_sub_rows_are_read")
        self.b.setUp()
        self.addCleanup(self.b.tearDown)
        self.d = Path(tempfile.mkdtemp(prefix="who-page-"))
        (self.d / "source").mkdir()
        (self.d / "source" / "page.txt").write_text("their page")
        (self.d / "structure.json").write_text("{}")
        (self.d / "identity-all.json").write_text('{"items": []}')

    def run_it(self, *extra):
        self.sent = {}

        def call(sent, model, label=None, timeout=None):
            self.sent[label] = sent
            return json.dumps({"survivors": []} if label.startswith("check") else BAD)
        with mock.patch.object(PW.C, "run_dir", lambda *a: self.d), mock.patch.object(PW.C.KIT, "call", call), \
                mock.patch.object(PW.LANG, "load", lambda *a: []), contextlib.redirect_stdout(io.StringIO()):
            PW.main(["--brand", "acme", "--label", "t", "--avatar", "sore-foot", "--product", "p.md", "--offer", "o.md",
                     "--next-url", "https://x", "--format", "listicle", "--topic", "heel", *extra])

    def test_the_writing_and_the_fix_steps_are_sent_it(self):
        self.run_it("--sub", "sub-01-runner", "--demographic", "m/25-34/black")
        for k in ("write", "fix@1"):
            for text in (self.sent[k], (self.d / f"{k}--sent.md").read_text()):
                for x in (W.MARK, CARD, "walk without heel pain", "m/25-34/black",
                          (PW.C.WS / "components/marketing-doctrine/slices/belief.md").read_text().strip(),
                          (PW.C.WS / "components/marketing-doctrine/slices/desire.md").read_text().strip()):
                    self.assertIn(x, text, k)
        self.assertNotIn(W.MARK, self.sent["check@1"])      # it looks for the source's identity, never ours
        self.assertEqual(json.loads((self.d / "run.json").read_text())["aim"]["sub"], "runner")

    def test_no_sub_speaks_to_the_avatar_and_a_missing_one_stops(self):
        self.run_it()
        self.assertIn(W.MARK, self.sent["write"])
        self.assertNotIn(CARD, self.sent["write"])
        with self.assertRaises(SystemExit):
            self.run_it("--sub", "nobody")
        self.assertEqual(self.sent, {})


if __name__ == "__main__":
    unittest.main()
