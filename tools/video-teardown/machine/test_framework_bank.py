#!/usr/bin/env python3
"""The declared test for the framework bank and the doctrine block parse.

    python3 test_framework_bank.py

Two runs with a clean doctrine read compile into two rows; a filter narrows
them; a malformed file is skipped with a reason rather than taking the bank
down with it. The block parse is tested on its own, because that is where a
model's output meets our schema and it must never raise.

Stdlib only. Writes nothing outside a temp tree.
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import framework_bank as FB  # noqa: E402

# run.py imports the machine's engines at module scope, so the block parser is
# read out of the file rather than imported — the test must not need a key, a
# model or a network to check a regex.
RUN = Path(__file__).resolve().parent / "run.py"


def _load_parser():
    """`json_block` and `file_doctrine` out of run.py, with nothing else."""
    src = RUN.read_text()
    start = src.index("FENCE = re.compile")
    end = src.index("def outputs_so_far(")
    ns = {"re": re, "json": json, "Path": Path}
    exec(compile(src[start:end], str(RUN), "exec"), ns)
    return ns


PARSE = _load_parser()

CLEAN = {
    "framework": "Mechanism-led (the new way)",
    "crosswalk_row": "Mechanism-led (the new way)",
    "sections_carried": [{"id": "hook", "span": "0:00-0:04"},
                         {"id": "root-cause", "span": "0:04-0:12"},
                         {"id": "unique-mechanism", "span": "0:12-0:26"}],
    "awareness": {"entry": "problem-aware", "exit": "product-aware"},
    "sophistication_signature": "a mechanism",
    "mass_desire": {"words": "stop it coming back every month",
                    "urgency": "named as a this-week problem at 0:06",
                    "staying_power": "not shown in the record",
                    "scope": "not shown in the record"},
    "techniques": [{"section": "hook", "technique": "intensification",
                    "sub_method": "Picture the dark side too",
                    "span": "0:00-0:04"},
                   {"section": "unique-mechanism", "technique": "mechanization",
                    "sub_method": "Feature it", "span": "0:12-0:26"}],
    "mood": "plain and level at the open, staccato from 0:12",
    "delivery": {"humor": "dry", "delivery_style": "deadpan",
                 "register": "plain-flat", "pacing": "beat-and-pause",
                 "reference_world": ["a hands-and-voiceover shape, 0:12-0:26"],
                 "avoid": ["no announcer lift anywhere"]},
    "unique": "a mechanism carried entirely by a one-take demonstration",
}

SECOND = {
    "framework": "Direct offer (most-aware)",
    "crosswalk_row": "Direct offer (most-aware)",
    "sections_carried": [{"id": "hook", "span": "0:00-0:03"},
                         {"id": "offer", "span": "0:03-0:15"}],
    "awareness": {"entry": "most-aware", "exit": "most-aware"},
    "sophistication_signature": "the claim enlarged",
    "mass_desire": {"words": "get the one everybody is out of",
                    "urgency": "a stock line at 0:11", "staying_power": "",
                    "scope": ""},
    "techniques": [{"section": "offer", "technique": "redefinition",
                    "sub_method": "Price reduction", "span": "0:03-0:15"}],
    "mood": "staccato throughout",
    "delivery": {"humor": "none", "delivery_style": "hype",
                 "register": "staccato-urgent", "pacing": "escalating",
                 "reference_world": [], "avoid": []},
    "unique": "an offer read that never states a benefit at all",
}


def tree(base, runs):
    """A shelf of runs: {slug: (doctrine_payload_or_text, run_json)}."""
    root = Path(base) / "runs"
    for slug, (doc, state) in runs.items():
        d = root / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "doctrine.json").write_text(
            doc if isinstance(doc, str) else json.dumps(doc, indent=2))
        if state is not None:
            (d / "run.json").write_text(json.dumps(state, indent=2))
    return root


class Bank(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = tree(self.tmp.name, {
            "aaa-the-scrub": (CLEAN, {
                "label": "AAA-the-scrub", "brand": "<brand>", "lane": "swipe",
                "triage_lane": "ALREADY AN AD",
                "origin_url": "https://example.invalid/p/AAA",
                "gdoc_url": "https://docs.example.invalid/d/AAA/edit"}),
            "bbb-the-deal": (SECOND, {
                "label": "BBB-the-deal", "brand": "<brand>", "lane": "creator",
                "triage_lane": "ORGANIC"}),
        })

    def tearDown(self):
        self.tmp.cleanup()

    # ------------------------------------------------------------ rows
    def test_two_readings_become_two_rows(self):
        rows, skipped, paths = FB.build(self.root)
        self.assertEqual(len(rows), 2, rows)
        self.assertEqual(skipped, [])
        a = next(r for r in rows if r["run"] == "aaa-the-scrub")
        self.assertEqual(a["framework"], "Mechanism-led (the new way)")
        self.assertEqual(a["awareness_entry"], "problem-aware")
        self.assertEqual(a["awareness_exit"], "product-aware")
        self.assertEqual(a["signature"], "a mechanism")
        self.assertEqual(a["desire"], "stop it coming back every month")
        self.assertEqual(a["brand"], "<brand>")
        self.assertEqual(a["source_url"], "https://example.invalid/p/AAA")
        # the finished document is the link, never the folder path
        self.assertEqual(a["link"], "https://docs.example.invalid/d/AAA/edit")
        self.assertEqual(a["sections_carried"][0], "hook 0:00-0:04")
        self.assertIn("mechanization", a["techniques_flat"])
        self.assertIn("Feature it", a["techniques_flat"])
        # the delivery read is banked dial by dial (stage 1c v2)
        self.assertEqual(a["humor"], "dry")
        self.assertEqual(a["delivery_style"], "deadpan")
        self.assertEqual(a["register"], "plain-flat")
        self.assertEqual(a["pacing"], "beat-and-pause")
        self.assertIn("hands-and-voiceover", a["reference_world"])
        self.assertIn("announcer lift", a["avoid"])
        self.assertEqual(a["delivery_flat"],
                         "dry · deadpan · plain-flat · beat-and-pause")
        # a run with no document falls back to a link to its own folder
        b = next(r for r in rows if r["run"] == "bbb-the-deal")
        self.assertTrue(b["link"].startswith("file://"), b["link"])

    def test_both_files_are_written(self):
        rows, _, paths = FB.build(self.root)
        self.assertTrue(paths["json"].is_file())
        self.assertTrue(paths["md"].is_file())
        got = json.loads(paths["json"].read_text())
        self.assertEqual(got["count"], 2)
        self.assertEqual(len(got["rows"]), 2)
        md = paths["md"].read_text()
        self.assertIn("Mechanism-led (the new way)", md)
        self.assertIn("problem-aware → product-aware", md)
        self.assertIn("[AAA-the-scrub](https://docs.example.invalid/d/AAA/edit)", md)
        # how it was delivered reads on the shelf beside what it argued
        self.assertIn("dry · deadpan · plain-flat · beat-and-pause", md)

    def test_the_headers_are_plain_names(self):
        rows, _, paths = FB.build(self.root)
        md = paths["md"].read_text()
        for jargon in ("sophistication", "crosswalk_row", "sections_carried",
                       "mass_desire", "awareness_entry", "sub_method",
                       "delivery_style", "delivery_flat", "reference_world"):
            self.assertNotIn(jargon, md.split("\n|", 1)[0] + "\n".join(
                l for l in md.splitlines() if l.startswith("| Framework")))
        self.assertIn("| Framework | Sections it carries |", md)
        self.assertIn("| How it is delivered | Humor | Register |", md)

    # ---------------------------------------------------------- queries
    def test_query_filters(self):
        rows, _, _ = FB.build(self.root, write=False)
        hit = FB.query(rows, {"awareness": "problem-aware",
                              "signature": "mechanism"})
        self.assertEqual([r["run"] for r in hit], ["aaa-the-scrub"])
        # substring, both ways round — "mechanism" finds "a mechanism"
        self.assertEqual(len(FB.query(rows, {"framework": "direct offer"})), 1)
        # a filter nothing answers returns nothing rather than everything
        self.assertEqual(FB.query(rows, {"awareness": "unaware"}), [])
        # techniques and sections are searchable too
        self.assertEqual(len(FB.query(rows, {"technique": "redefinition"})), 1)
        self.assertEqual(len(FB.query(rows, {"section": "root-cause"})), 1)
        # the delivery read is filterable — the three a person actually asks for
        self.assertEqual([r["run"] for r in FB.query(rows, {"humor": "dry"})],
                         ["aaa-the-scrub"])
        self.assertEqual([r["run"] for r in
                          FB.query(rows, {"delivery-style": "deadpan"})],
                         ["aaa-the-scrub"])
        self.assertEqual([r["run"] for r in
                          FB.query(rows, {"register": "staccato-urgent"})],
                         ["bbb-the-deal"])
        self.assertEqual(FB.query(rows, {"humor": "absurd"}), [])
        # free text runs across the whole row
        self.assertEqual(len(FB.query(rows, {}, "one-take")), 1)
        self.assertEqual(len(FB.query(rows, {}, "nothing like this")), 0)

    def test_every_filter_flag_reaches_its_row_field(self):
        """--delivery-style becomes args.delivery_style; a filter whose name
        carries a dash must still be read, or it silently never filters."""
        FB.build(self.root)
        rc = FB.main(["--runs", str(self.root), "--delivery-style", "deadpan"])
        self.assertEqual(rc, 0)
        rc = FB.main(["--runs", str(self.root), "--delivery-style", "nobody"])
        self.assertEqual(rc, 1)

    def test_a_reading_with_no_delivery_key_still_banks(self):
        """An older run, read before the delivery layer existed, is a row with
        empty delivery cells — never a skip."""
        old = {k: v for k, v in CLEAN.items() if k != "delivery"}
        tree(self.tmp.name, {"fff-pre-delivery": (old, None)})
        rows, skipped, _ = FB.build(self.root)
        self.assertEqual(skipped, [])
        r = next(x for x in rows if x["run"] == "fff-pre-delivery")
        self.assertEqual(r["delivery_flat"], "")
        self.assertEqual(r["humor"], "")

    def test_a_filter_does_not_rewrite_the_bank(self):
        FB.build(self.root)
        before = (self.root / "framework-bank.json").read_text()
        rc = FB.main(["--runs", str(self.root), "--awareness", "most-aware"])
        self.assertEqual(rc, 0)
        self.assertEqual((self.root / "framework-bank.json").read_text(), before)

    # --------------------------------------------------------- skipping
    def test_a_malformed_file_is_skipped_with_a_note(self):
        (self.root / "ccc-broken").mkdir()
        (self.root / "ccc-broken" / "doctrine.json").write_text("{not json,")
        (self.root / "ddd-errored").mkdir()
        (self.root / "ddd-errored" / "doctrine.json").write_text(json.dumps(
            {"error": "no fenced block in the output", "raw": "prose only"}))
        rows, skipped, _ = FB.build(self.root)
        self.assertEqual(len(rows), 2)          # the good two still compile
        self.assertEqual({s["run"] for s in skipped},
                         {"ccc-broken", "ddd-errored"})
        for s in skipped:
            self.assertTrue(s["why"], s)
        md = (self.root / "framework-bank.md").read_text()
        self.assertIn("Not banked", md)
        self.assertIn("ccc-broken", md)

    def test_a_run_with_no_run_json_still_banks(self):
        tree(self.tmp.name, {"eee-bare": (CLEAN, None)})
        rows, skipped, _ = FB.build(self.root)
        self.assertEqual(skipped, [])
        bare = next(r for r in rows if r["run"] == "eee-bare")
        self.assertEqual(bare["label"], "eee-bare")
        self.assertEqual(bare["brand"], "")

    def test_an_empty_shelf_compiles_to_an_empty_bank(self):
        empty = Path(self.tmp.name) / "nothing-here"
        rows, skipped, paths = FB.build(empty)
        self.assertEqual((rows, skipped), ([], []))
        self.assertIn("Nothing banked yet", paths["md"].read_text())

    def test_refresh_never_raises(self):
        self.assertIn("2 swipe(s) banked", FB.refresh(self.root))
        # a shelf that cannot be read is a None, never an exception
        self.assertIsNone(FB.refresh("/dev/null/not-a-place"))


class JsonBlock(unittest.TestCase):
    """The parse that turns stage 1c's output into doctrine.json."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def body(self, payload, lang="json", before="FRAMEWORK: something\n\n",
             after=""):
        return (before + "```" + lang + "\n"
                + (payload if isinstance(payload, str)
                   else json.dumps(payload, indent=2))
                + "\n```\n" + after)

    def test_the_block_is_read_out_of_the_prose(self):
        got, why = PARSE["json_block"](self.body(CLEAN))
        self.assertIsNone(why)
        self.assertEqual(got["framework"], CLEAN["framework"])

    def test_the_last_block_wins(self):
        text = (self.body({"framework": "first"})
                + "\nOn reflection:\n\n"
                + self.body({"framework": "second"}))
        got, why = PARSE["json_block"](text)
        self.assertIsNone(why)
        self.assertEqual(got["framework"], "second")

    def test_an_untagged_fence_still_counts(self):
        got, why = PARSE["json_block"](self.body(CLEAN, lang=""))
        self.assertIsNone(why)
        self.assertEqual(got["signature"] if "signature" in got
                         else got["sophistication_signature"], "a mechanism")

    def test_a_tagged_block_beats_an_untagged_one(self):
        text = (self.body({"framework": "untagged"}, lang="")
                + self.body({"framework": "tagged"}))
        got, _ = PARSE["json_block"](text)
        self.assertEqual(got["framework"], "tagged")

    def test_no_block_is_a_reason_not_a_crash(self):
        got, why = PARSE["json_block"]("prose, and nothing fenced at all")
        self.assertIsNone(got)
        self.assertIn("no fenced block", why)

    def test_broken_json_is_a_reason_not_a_crash(self):
        got, why = PARSE["json_block"](self.body("{not json,"))
        self.assertIsNone(got)
        self.assertTrue(why)

    def test_file_doctrine_writes_the_clean_block(self):
        got, note = PARSE["file_doctrine"](self.d, self.body(CLEAN))
        self.assertIsNone(note)
        self.assertEqual(got["framework"], CLEAN["framework"])
        on_disk = json.loads((self.d / "doctrine.json").read_text())
        self.assertEqual(on_disk["awareness"]["entry"], "problem-aware")

    def test_file_doctrine_records_a_failure_and_keeps_the_words(self):
        got, note = PARSE["file_doctrine"](self.d, "no block here, only prose")
        self.assertIsNone(got)
        self.assertTrue(note)
        on_disk = json.loads((self.d / "doctrine.json").read_text())
        self.assertIn("error", on_disk)
        self.assertIn("only prose", on_disk["raw"])

    def test_the_delivery_key_is_one_of_the_keys_a_reading_must_carry(self):
        thin = {k: v for k, v in CLEAN.items() if k != "delivery"}
        got, note = PARSE["file_doctrine"](self.d, self.body(thin))
        self.assertIn("delivery", note)
        self.assertEqual(got["_missing_keys"], ["delivery"])

    def test_a_missing_key_is_noted_not_dropped(self):
        thin = {k: v for k, v in CLEAN.items() if k != "unique"}
        got, note = PARSE["file_doctrine"](self.d, self.body(thin))
        self.assertIn("unique", note)
        self.assertEqual(got["_missing_keys"], ["unique"])

    def test_a_list_at_the_top_is_a_failure_not_a_row(self):
        got, note = PARSE["file_doctrine"](self.d, self.body([1, 2, 3]))
        self.assertIsNone(got)
        self.assertIn("not an object", note)

    def test_the_failure_file_is_skipped_by_the_bank(self):
        PARSE["file_doctrine"](self.d, "prose only, no block")
        (self.d / "run.json").write_text(json.dumps({"label": "X"}))
        row, why = FB.read_run(self.d)
        self.assertIsNone(row)
        self.assertIn("stage 1c filed an error", why)


if __name__ == "__main__":
    unittest.main(verbosity=2)
