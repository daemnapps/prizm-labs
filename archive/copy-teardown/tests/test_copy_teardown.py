#!/usr/bin/env python3
"""copy-teardown's own tests. stdlib only, no network, no model — the model is
a stub handed to the runner. Everything is written under a TEMP workspace
(`AI_WORKSPACE`): a made-up brand in a temp `brands/`, runs in a temp `runs/`.
The real `runs/` and `brands/` are never touched.

    python3 copy-teardown/tests/test_copy_teardown.py
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
REAL = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())

WS = Path(tempfile.mkdtemp(prefix="copy-teardown-test-"))
(WS / "brands" / "testbrand").mkdir(parents=True)
(WS / "brands" / "otherbrand").mkdir(parents=True)
os.symlink(REAL / "components", WS / "components")
os.environ["AI_WORKSPACE"] = str(WS)

sys.path.append(str(TOOLS))
import paths as P                # noqa: E402
import source_text as S          # noqa: E402
import elements_label as L       # noqa: E402
import gates as G                # noqa: E402
import run as R                  # noqa: E402

SOURCE = """I spent four years hiding my hands in every photo.

Then a friend handed me Velvane Balm and said "just try it for a week, {{ first_name }}."

Nine days later I was the one asking for the camera. It was $38 and I would have paid triple.

Get yours at velvane.example.com or find @velvane.care #velvaneglow
"""

CARD = """# 07 · A card's own title

**3 live creatives** — notes that are not the copy
**Landing page:** `https://velvane.example.com/pages/x`

## Headline

> Four Years Of Hiding. Nine Days To Stop.

## Primary text (verbatim)

> I spent four years hiding my hands in every photo.
> Then a friend handed me Velvane Balm.

## Media (on Drive)

- `video/` — not the copy either
"""

RECORD = """# THE COPY AS READ

**WHAT IT WAS BUILT TO DO**
ALREADY AN AD — it ends on a place to buy.

**THE BEATS, IN ORDER**
B1 the hidden cost: "I spent four years hiding my hands in every photo."
B2 the hand-off: "Then a friend handed me Velvane Balm and said \\"just try it for a week, {{ first_name }}.\\"" [D1]
B3 the payoff: "Nine days later I was the one asking for the camera. It was $38 and I would have paid triple."

**AWARENESS**
entry problem-aware · exit most-aware

# SOURCE NAMES

N1 "Velvane Balm" — product
N2 "Velvane" — brand

# SOURCE DEFECTS

D1 — "{{ first_name }}" — merge tag — meant a first name

# STRIP

```STRIP
{"names": ["Velvane Balm", "Velvane"],
 "defects": [{"id": "D1", "quote": "just try it for a week, {{ first_name }}.", "meant": "a first name"}]}
```
"""

CONSTRUCT = """# CONSTRUCT

**THE MOVES**
1. Names a cost the reader has been quietly paying, before anything is offered. [SLOT: the hidden cost]
2. A trusted person hands the thing over with a small, bounded ask. [SLOT: the bounded trial]

**THE SEQUENCE LOGIC** — the cost buys the attention the hand-off spends.

**LOAD-BEARING** — the single ask.

**LEFT OUT:** 2 source names withheld; D1
"""


def labels_answer(**over):
    E = L.library()
    ids = {L.key(el, a): E.rows(el, a)[0]["id"] for el, a in L.LISTS}
    ids.update(over)
    return "```ELEMENTS\n" + json.dumps(
        {k: ({"id": v, "why": "B1 does it", "proposed": None} if isinstance(v, str) else v)
         for k, v in ids.items()}) + "\n```"


class Stub:
    """The model, stubbed: answers by which step's prompt it was handed."""
    def __init__(self, record=RECORD, labels=None, construct=CONSTRUCT):
        self.record, self.labels, self.construct = record, labels or labels_answer(), construct
        self.calls, self.prompts = [], {}

    def __call__(self, prompt, model):
        step = ("tear2" if "```ELEMENTS" in prompt else "tear3" if "# CONSTRUCT" in prompt else "tear1")
        self.calls.append((step, model))
        self.prompts[step] = prompt
        return 0, {"tear1": self.record, "tear2": self.labels, "tear3": self.construct}[step], ""


class Base(unittest.TestCase):
    def setUp(self):
        self.src = WS / "source.md"
        self.src.write_text(SOURCE)
        self.said = []
        shutil.rmtree(WS / "runs", ignore_errors=True)

    def run_it(self, *extra, stub=None, label="t1", source=None, piped=None):
        return R.main([str(source or self.src), "--brand", "testbrand", "--label", label, *extra],
                      runner=stub or Stub(), echo=self.said.append, piped=piped)

    def out(self, label="t1"):
        return WS / "runs" / "copy-teardown" / "testbrand" / label

    def check(self, label="t1"):
        return json.loads((self.out(label) / "check.json").read_text())


class Workspace(Base):
    def test_everything_resolves_inside_the_temp_workspace(self):
        self.assertEqual(P.REPO, WS)
        self.assertEqual(P.record_dir("testbrand", "x"), WS / "runs" / "copy-teardown" / "testbrand" / "x")
        self.assertNotIn(str(REAL / "runs"), str(P.RECORDS))


class DryRun(Base):
    def test_spends_nothing_and_writes_nothing(self):
        stub = Stub()
        before = sorted(p.name for p in WS.iterdir())
        self.assertEqual(self.run_it("--dry-run", stub=stub), 0)
        self.assertEqual(stub.calls, [])
        self.assertEqual(sorted(p.name for p in WS.iterdir()), before)      # no runs/ made
        text = "\n".join(self.said)
        self.assertIn("would file  runs/copy-teardown/testbrand/t1/", text)
        self.assertIn("0 model calls", text)
        for tier in ("reads", "checks", "designs"):
            self.assertIn(f"({tier})", text)

    def test_names_what_is_missing(self):
        code = R.main([str(WS / "nope.md"), "--brand", "nobrand", "--dry"], runner=Stub(), echo=self.said.append)
        self.assertEqual(code, 1)
        text = "\n".join(self.said)
        self.assertIn("not on file", text)
        self.assertIn("`nobrand` is not a brand folder", text)
        self.assertIn("testbrand", text)                                    # the real ones are named

    def test_there_is_no_default_brand(self):
        with self.assertRaises(SystemExit):
            R.main([str(self.src), "--dry-run"], runner=Stub(), echo=self.said.append)

    def test_piped_text_is_a_source(self):
        stub = Stub()
        code = R.main(["-", "--brand", "testbrand", "--dry"], runner=stub, echo=self.said.append, piped=SOURCE)
        self.assertEqual(code, 0)
        self.assertEqual(stub.calls, [])
        self.assertIn("label pasted-", "\n".join(self.said))


class WordsOnly(Base):
    def refused(self, name, text, needle):
        f = WS / name
        f.write_text(text)
        stub = Stub()
        self.assertEqual(self.run_it(stub=stub, source=f), 2)
        self.assertEqual(stub.calls, [])                                    # held before any model
        self.assertEqual(self.check()["inputs"]["result"], "HELD")
        self.assertIn(needle, " | ".join(self.check()["inputs"]["problems"]))

    def test_a_page_goes_to_page_teardown(self):
        self.refused("p.html", "<html><body>hi</body></html>", "page teardown")

    def test_a_picture_goes_to_image_teardown(self):
        self.refused("p.png", "not really a png", "image teardown")

    def test_an_email_with_pictures_goes_to_email_teardown(self):
        self.refused("e.md", "Subject\n\n[IMAGE alt=A headline] https://img.example/h.png\n", "email teardown")

    def test_an_unknown_brand_never_gets_a_run_folder(self):
        code = R.main([str(self.src), "--brand", "nobrand"], runner=Stub(), echo=self.said.append)
        self.assertEqual(code, 2)
        self.assertFalse((WS / "runs" / "copy-teardown" / "nobrand").exists())


class FullRun(Base):
    def test_files_the_run_and_passes_every_gate(self):
        stub = Stub()
        self.assertEqual(self.run_it(stub=stub), 0)
        self.assertEqual([c[0] for c in stub.calls], ["tear1", "tear2", "tear3"])
        out = self.out()
        for f in ("source.md", "tear1--record.md", "tear1--sent.md", "tear2--labels.md", "tear3--construct.md",
                  "tear3--sent.md", "elements.json", "strip.json", "run.json", "check.json"):
            self.assertTrue((out / f).is_file(), f)
        self.assertEqual({g: v["result"] for g, v in self.check().items()},
                         {"inputs": "pass", "copy": "pass", "elements": "pass"})
        run = json.loads((out / "run.json").read_text())
        self.assertEqual((run["tool"], run["brand"], run["state"]), ("copy-teardown", "testbrand", "filed"))
        self.assertEqual(set(run["elements"]["labels"]), set(L.KEYS))

    def test_tiers_not_model_ids_pick_the_model(self):
        stub = Stub()
        self.run_it(stub=stub)
        from run_kit import model as M
        self.assertEqual([m for _, m in stub.calls], [M.TIERS["reads"], M.TIERS["checks"], M.TIERS["designs"]])
        stub2 = Stub()
        self.run_it("--model", "one-model", stub=stub2, label="t2")
        self.assertEqual({m for _, m in stub2.calls}, {"one-model"})

    def test_later_steps_never_see_a_source_name(self):
        stub = Stub()
        self.run_it(stub=stub)
        self.assertIn("Velvane Balm", stub.prompts["tear1"])
        self.assertIn("handle · @velvane.care", stub.prompts["tear1"])       # the free scan is handed over
        for step in ("tear2", "tear3"):
            self.assertNotIn("velvane", stub.prompts[step].lower())
            self.assertIn("[SOURCE NAME 1]", stub.prompts[step])
            self.assertNotIn("```STRIP", stub.prompts[step])

    def test_no_brand_file_is_read_into_any_prompt(self):
        (WS / "brands" / "testbrand" / "secret.md").write_text("TESTBRAND-ONLY-FACT")
        stub = Stub()
        self.run_it(stub=stub)
        for p in stub.prompts.values():
            self.assertNotIn("TESTBRAND-ONLY-FACT", p)
            self.assertNotIn("testbrand", p.lower())

    def test_a_finished_run_is_reused_and_a_changed_source_is_read_again(self):
        self.run_it()
        again = Stub()
        self.assertEqual(self.run_it(stub=again), 0)
        self.assertEqual(again.calls, [])
        self.src.write_text(SOURCE + "\nOne more line.\n")
        changed = Stub()
        self.run_it(stub=changed)
        self.assertEqual([c[0] for c in changed.calls], ["tear1", "tear2", "tear3"])

    def test_rerun_from_a_step(self):
        self.run_it()
        stub = Stub()
        self.run_it("--rerun-from", "tear3", stub=stub)
        self.assertEqual([c[0] for c in stub.calls], ["tear3"])

    def test_piped_text_files_a_run(self):
        code = R.main(["-", "--brand", "testbrand", "--label", "p1"], runner=Stub(), echo=self.said.append, piped=SOURCE)
        self.assertEqual(code, 0)
        self.assertEqual((self.out("p1") / "source.md").read_text().strip(), SOURCE.strip())


class SwipeCard(Base):
    def test_only_the_copy_parts_of_a_saved_card_are_taken(self):
        f = WS / "card.md"
        f.write_text(CARD)
        words, how = S.load(f)
        self.assertIn("HEADLINE:\nFour Years Of Hiding. Nine Days To Stop.", words)
        self.assertIn("PRIMARY TEXT:\nI spent four years", words)
        self.assertNotIn("live creatives", words)
        self.assertNotIn("Drive", words)
        self.assertNotIn(">", words)
        self.assertIn("saved swipe card", how)

    def test_a_plain_file_is_read_as_it_stands(self):
        self.assertEqual(S.load(self.src), (SOURCE.strip() + "\n", "the file as it stands"))


class TolerantParsers(unittest.TestCase):
    """How a model actually formats a slot — a too-strict parser held the
    email teardown's first real run."""
    BODY = '{"names": ["Velvane"], "defects": []}'

    def test_a_tagged_fence(self):
        self.assertEqual(S.strip_block(f"```STRIP\n{self.BODY}\n```")["names"], ["Velvane"])

    def test_a_heading_over_a_plain_fence(self):
        self.assertEqual(S.strip_block(f"# STRIP\n\n```\n{self.BODY}\n```")["names"], ["Velvane"])

    def test_a_heading_over_a_json_fence(self):
        self.assertEqual(S.strip_block(f"## **STRIP**\n```json\n{self.BODY}\n```")["names"], ["Velvane"])

    def test_a_lowercase_tag_and_a_bare_object(self):
        self.assertEqual(S.strip_block(f"```strip\n{self.BODY}\n```")["names"], ["Velvane"])
        self.assertEqual(S.strip_block(f"Here it is:\n{self.BODY}\n")["names"], ["Velvane"])

    def test_headings_as_a_model_writes_them(self):
        rec = "## THE COPY AS READ\n\nx\n\n**SOURCE NAMES**\n\nx\n\n### Source Defects:\n\nx\n\n# STRIP\n```json\n" + self.BODY + "\n```"
        self.assertEqual(S.record_problems(rec), [])

    def test_the_labels_under_their_heading_or_in_a_json_fence(self):
        body = labels_answer().split("\n", 1)[1].rsplit("```", 1)[0]
        for shaped in (f"# ELEMENT LABELS\n\n```json\n{body}```", f"```json\n{body}```", f"```elements\n{body}```", body):
            record, problems = L.read(shaped)
            self.assertEqual(problems, [], shaped[:30])
            self.assertEqual(set(record["labels"]), set(L.KEYS))

    def test_no_block_at_all_is_said_plainly(self):
        _, problems = L.read("I think it is a caption.")
        self.assertIn("no ELEMENTS block", problems[0])


class ElementsGate(Base):
    def test_an_unknown_label_is_refused_with_the_real_ids_named(self):
        stub = Stub(labels=labels_answer(**{"format/copy": "made-up-format"}))
        self.assertEqual(self.run_it(stub=stub), 2)
        self.assertEqual([c[0] for c in stub.calls], ["tear1", "tear2"])       # the construct never ran
        check = self.check()
        self.assertEqual(check["elements"]["result"], "HELD")
        real = L.library().rows("format", "copy")[0]["id"]
        self.assertIn(real, check["elements"]["problems"][0])
        rec = json.loads((self.out() / "elements.json").read_text())
        self.assertEqual(rec["refused"][0]["id"], "made-up-format")
        self.assertNotIn("format/copy", rec["labels"])

    def test_an_id_from_the_wrong_list_is_refused(self):
        wrong = L.library().rows("framework", "all")[0]["id"]
        self.assertEqual(self.run_it(stub=Stub(labels=labels_answer(**{"format/copy": wrong}))), 2)

    def test_none_fits_is_recorded_as_a_proposed_row_never_written_to_the_library(self):
        lib = REAL / "components" / "elements" / "library"
        before = {f.name: f.read_bytes() for f in lib.glob("*.json")}
        stub = Stub(labels=labels_answer(**{"format/copy": {
            "id": "none-fits", "why": "THE PARTS: nothing but headlines",
            "proposed": "headline-set — Headline set — several stand-alone claims, each a whole ad's one line"}}))
        self.assertEqual(self.run_it(stub=stub), 0)
        run = json.loads((self.out() / "run.json").read_text())
        self.assertTrue(run["elements"]["proposed"]["format/copy"].startswith("headline-set"))
        self.assertEqual({f.name: f.read_bytes() for f in lib.glob("*.json")}, before)

    def test_none_fits_without_a_proposed_row_is_held(self):
        stub = Stub(labels=labels_answer(**{"format/copy": {"id": "none-fits", "why": "x", "proposed": None}}))
        self.assertEqual(self.run_it(stub=stub), 2)

    def test_every_list_it_labels_against_is_in_the_library(self):
        self.assertEqual(L.missing_lists(), [])


class CopyGate(Base):
    def held(self, construct):
        self.assertEqual(self.run_it(stub=Stub(construct=construct)), 2)
        self.assertEqual(self.check()["copy"]["result"], "HELD")
        return " | ".join(self.check()["copy"]["problems"])

    def swap(self, new):
        return CONSTRUCT.replace("the single ask", new)

    def test_a_source_name_in_the_construct_holds_it(self):
        self.assertIn("“Velvane Balm”", self.held(self.swap("the moment velvane balm is handed over")))

    def test_a_name_only_the_code_found_holds_it(self):
        self.assertIn("velvane.example.com", self.held(self.swap("the link to velvane.example.com")))

    def test_a_brand_on_file_in_the_construct_holds_it(self):
        self.assertIn("otherbrand", self.held(self.swap("ready for Otherbrand to fill")))

    def test_a_source_price_holds_it_and_another_number_does_not(self):
        self.assertIn("$38.00", self.held(self.swap("the $38 anchor")))
        self.assertEqual(S.construct_problems(self.swap("a $5 example"), {"names": [], "defects": []},
                                              {"names": []}, SOURCE), [])

    def test_a_carried_defect_or_merge_tag_holds_it(self):
        why = self.held(self.swap('opens "just try it for a week, {{ first_name }}." flat'))
        self.assertIn("source defect (D1)", why)
        self.assertIn("merge tag", why)

    def test_a_withheld_name_given_a_place_holds_it(self):
        self.assertIn("marker", self.held(self.swap("the hand-off of [SOURCE NAME 1]")))

    def test_an_unfilled_note_holds_it(self):
        self.assertIn("UNFILLED", self.held(self.swap("[UNFILLED: no proof]")))

    def test_a_construct_missing_its_parts_holds_it(self):
        why = self.held("# CONSTRUCT\n\nA summary with no labelled parts.\n")
        self.assertIn("THE MOVES", why)
        self.assertIn("LEFT OUT", why)

    def test_a_record_without_its_labelled_parts_is_held_before_anything_else_is_spent(self):
        stub = Stub(record="Here is a summary of the copy, all in one run.")
        self.assertEqual(self.run_it(stub=stub), 2)
        self.assertEqual([c[0] for c in stub.calls], ["tear1"])
        problems = self.check()["copy"]["problems"]
        self.assertTrue(any("SOURCE NAMES" in p for p in problems))
        self.assertTrue(any("STRIP" in p for p in problems))

    def test_a_one_word_name_is_not_swept_as_ordinary_english(self):
        strip = {"names": ["Glow"], "defects": []}
        self.assertEqual(S.construct_problems(self.swap("the reader's own glow of relief"), strip, {"names": []}, ""), [])
        self.assertTrue(S.construct_problems(self.swap("the Glow reveal"), strip, {"names": []}, ""))

    def test_a_name_the_record_lists_but_the_source_does_not_hold_is_noted(self):
        rec = RECORD.replace('["Velvane Balm", "Velvane"]', '["Velvane Balm", "Velvane", "Invented Co"]')
        self.run_it(stub=Stub(record=rec))
        strip = json.loads((self.out() / "strip.json").read_text())
        self.assertEqual(strip["listed_but_not_in_the_source"], ["Invented Co"])


class Scan(Base):
    def test_the_free_scan_finds_names_prices_and_damage(self):
        found = S.scan(SOURCE)
        self.assertEqual({n["kind"] for n in found["names"]}, {"handle", "hashtag", "web address"})
        self.assertEqual(found["prices"], ["38.00"])
        self.assertEqual([d["quote"] for d in found["defects"]], ["{{ first_name }}"])

    def test_a_markdown_heading_is_not_a_hashtag(self):
        self.assertEqual(S.scan("# Heading\n\n## Another\n")["names"], [])


class NoBrandInTheTool(unittest.TestCase):
    def test_no_brand_name_in_the_code_or_prompts(self):
        brands = [p.name for p in (REAL / "brands").iterdir() if p.is_dir() and not p.name.startswith(("_", "."))]
        files = sorted(TOOLS.glob("*.py")) + sorted((HERE.parent / "prompts").glob("*.md"))
        self.assertTrue(files)
        for f in files:
            low = f.read_text().lower()
            for b in brands:
                self.assertNotIn(b.lower(), low, f"{f.name} names the brand {b}")

    def test_no_file_shadows_the_standard_library(self):
        import copy
        self.assertNotIn(str(TOOLS), str(getattr(copy, "__file__", "")))
        self.assertFalse((TOOLS / "copy.py").exists())

    def test_the_prompts_open_on_the_invented_example_guard(self):
        for f in sorted((HERE.parent / "prompts").glob("*.md")):
            first = f.read_text().lstrip().splitlines()[0]
            self.assertTrue(first.startswith("**") and "example" in first.lower(), f.name)


def tearDownModule():
    shutil.rmtree(WS, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=1)
