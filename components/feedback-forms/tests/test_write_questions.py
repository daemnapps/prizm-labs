"""The question writer: the packet carries the research, the answer is checked against it (no model, no brand)."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import write_questions as W  # noqa: E402

TPL = W.REPO / "brands" / "_TEMPLATE" / "operations"


def template():
    return json.loads((TPL / "feedback-stages.json").read_text()), json.loads((TPL / "feedback-questions.json").read_text())


class Writer(unittest.TestCase):
    def test_prompt_takes_every_packet_field(self):
        text = sorted(HERE.parent.joinpath("prompts").glob("questions-v*-write.md"))[-1].read_text()
        for field in ("brand_voice", "people", "words", "stages", "starter", "rules"):
            self.assertIn("{" + field + "}", text)

    def test_merge_keeps_shape_and_refuses_uncited_lines(self):
        st, qs = template()
        answer = {"stages": {sid: {"title": "T", "intro": "I", "why": "fills doubts",
                                   "email": {"subject": "S", "preview": "P", "button": "Go"},
                                   "questions": s["questions"]} for sid, s in qs["stages"].items()}}
        first = next(iter(answer["stages"]))
        answer["stages"][first]["questions"][0] = dict(answer["stages"][first]["questions"][0], language_used=["row-1"])
        merged, bad = W.merge(qs, answer, {"row-1"})
        self.assertEqual(bad, [])
        self.assertEqual(W.B.check(st, merged), [])
        self.assertEqual(merged["stages"][first]["title"], "T")
        answer["stages"][first]["questions"][0]["language_used"] = ["made-up"]
        _, bad = W.merge(qs, answer, {"row-1"})
        self.assertTrue(any("cites lines it was not given" in b for b in bad))
        q0 = answer["stages"][first]["questions"][0]
        answer["stages"][first]["questions"][0] = dict(q0, type="choice", options=list("abcdefg"), language_used=[])
        _, bad = W.merge(qs, answer, {"row-1"})
        self.assertTrue(any("7 options" in b for b in bad))
        del answer["stages"][first]
        _, bad = W.merge(qs, answer, {"row-1"})
        self.assertTrue(any("no questions for this stage" in b for b in bad))

    def test_parse_finds_the_json(self):
        self.assertEqual(W.parse('Here you go:\n{"stages": {}}\n'), {"stages": {}})
        with self.assertRaises(SystemExit):
            W.parse("no json")

    def test_packet_without_research_still_works(self):
        fields, meta, (st, qs) = W.packet("no-such-brand")
        self.assertEqual(meta["config_from"], "template")
        self.assertIn("no voice files yet", fields["brand_voice"])
        self.assertTrue(fields["stages"].startswith("- list-no-order"))


if __name__ == "__main__":
    unittest.main()
