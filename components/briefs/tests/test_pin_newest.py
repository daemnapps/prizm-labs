#!/usr/bin/env python3
"""SI-129 (briefs register honest): the register resolves a pinned prompt to
the highest -vN- beside it, N as a NUMBER, the way image-teardown's run.py
`prompt_for()` does — and the static brief's pin follows it.

    /usr/bin/python3 components/briefs/tests/test_pin_newest.py

No key, no network. Loads the tool by file — image-teardown has its own
tools/briefs.py, so a module-name import could pick up the wrong one.
"""
import contextlib, importlib.util, io, tempfile, unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

COMPONENT = Path(__file__).resolve().parent.parent
TOOL = COMPONENT / "tools" / "briefs.py"

_spec = importlib.util.spec_from_file_location("briefs_register_newest", TOOL)
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

PIN = "prompts/stage6-image-brief-v2-owner.md"


def tree(tmp, names):
    root = Path(tmp)
    (root / "prompts").mkdir()
    for n in names:
        (root / "prompts" / n).write_text("x")
    return root


class PinNewest(unittest.TestCase):

    def test_v2_and_v6_resolves_to_v6(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tree(tmp, ["stage6-image-brief-v2-owner.md",
                              "stage6-image-brief-v6-owner.md"])
            self.assertEqual(B.newest(PIN, root),
                             "prompts/stage6-image-brief-v6-owner.md")

    def test_version_is_a_number_not_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tree(tmp, ["stage6-image-brief-v2-owner.md",
                              "stage6-image-brief-v6-owner.md",
                              "stage6-image-brief-v10-owner.md"])
            self.assertEqual(B.newest(PIN, root),
                             "prompts/stage6-image-brief-v10-owner.md")

    def test_other_styles_and_subfolders_never_compete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tree(tmp, ["stage6-image-brief-v2-owner.md",
                              "stage6-creator-static-brief-v9-owner.md"])
            (root / "prompts" / "archive").mkdir()
            (root / "prompts" / "archive" / "stage6-image-brief-v7-owner.md").write_text("x")
            self.assertEqual(B.newest(PIN, root), PIN)

    def test_a_pin_with_no_version_is_returned_as_it_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tree(tmp, ["campaign.md"])
            self.assertEqual(B.newest("prompts/campaign.md", root), "prompts/campaign.md")

    def test_path_prints_the_pin_by_default_and_the_newest_on_ask(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = tree(tmp, ["stage6-image-brief-v2-owner.md",
                              "stage6-image-brief-v6-owner.md"])
            reg = {"briefs": [{"id": "static--designer", "prompt": PIN}]}
            outs = []
            for flag in (False, True):
                buf = io.StringIO()
                with mock.patch.object(B, "WS", root), contextlib.redirect_stdout(buf):
                    code = B.cmd_path(Namespace(id="static--designer", newest=flag), reg)
                self.assertEqual(code, 0)
                outs.append(buf.getvalue().strip())
        self.assertEqual(outs, [PIN, "prompts/stage6-image-brief-v6-owner.md"])

    def test_the_static_brief_pin_is_the_newest_on_disk(self):
        reg = B.load()
        row = [b for b in reg["briefs"] if b["id"] == "static--designer"][0]
        self.assertTrue((B.WS / row["prompt"]).is_file(), row["prompt"])
        self.assertEqual(B.newest(row["prompt"]), row["prompt"])
        self.assertIn("-v6-", row["prompt"])

    def test_the_stage5_retire_note_cites_the_pinned_copy(self):
        reg = B.load()
        copy = "components/chain-runner/chains/video-teardown/prompts/stage5/v4.md"
        notes = [r.get("careful", "") for r in reg["retire_candidates"]
                 if r["prompt"].endswith("ai-lane/stage5-ai-brief-v4-owner.md")]
        self.assertEqual(len(notes), 1)
        self.assertIn(copy, notes[0])
        self.assertTrue((B.WS / copy).is_file())


if __name__ == "__main__":
    unittest.main()
