#!/usr/bin/env python3
"""page-teardown's own tests. stdlib only, no network, no model — the model is
a stub handed to the runner. Everything is written under a TEMP workspace
(`AI_WORKSPACE`): a made-up brand in a temp `brands/`, runs in a temp `runs/`.
The real `runs/` and `brands/` are never touched.

    python3 page-teardown/tests/test_page_teardown.py
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

WS = Path(tempfile.mkdtemp(prefix="page-teardown-test-"))
(WS / "brands" / "testbrand" / "products").mkdir(parents=True)
(WS / "brands" / "testbrand" / "products" / "store.json").write_text(json.dumps(
    {"brand": "Testbrand", "site": "https://www.testbrandshop.example", "products": [{"title": "Morning Kit™ Set"}]}))
os.symlink(REAL / "components", WS / "components")
os.environ["AI_WORKSPACE"] = str(WS)

sys.path.append(str(TOOLS))
import paths as P                # noqa: E402
import slots as S                # noqa: E402
import furniture as F            # noqa: E402
import elements_label as L       # noqa: E402
import gates as G                # noqa: E402
import run as R                  # noqa: E402

BODY = """
<div class="announcement-bar">Free returns on everything, always</div>
<nav><ul><li><a href="/">Home</a></li><li><a href="/all">Shop the range</a></li></ul></nav>
<div id="cookie-banner">We use cookies. <button>Accept</button></div>
<main>
 <h1>The seven-day reset nobody told you about</h1>
 <p>I tried four of them before this one. {{ customer.first_name }}, here is what happened.</p>
 <img alt="A chart of the four that failed" src="https://cdn.example/x/chart.png?v=2">
 <h2>Why the others stopped working</h2>
 <p>Each one worked for a week and then quit. That is not bad luck, it is how they are built, and nobody says so.</p>
 <p>Loved by 12,000 readers. Save $26 today, a $7 value thrown in, 47% off.</p>
 <a class="btn btn-primary" href="/offer?utm=1">Get the Glowpath kit</a>
 <p>More words so the page is long enough to count as a page when it has been reduced to plain lines by the code.</p>
</main>
<footer><a href="/policies/privacy">Privacy Policy</a><p>© 2026 Example Holdings. All rights reserved.</p></footer>
"""
HTML = ("<html><head><title>The reset</title><meta property='og:site_name' content='Glowpath Labs'>"
        "<style>p{color:red}</style><script>var tracking = 'noise';</script></head><body>"
        + BODY + "</body></html>")

RECORD = """## Sections as read

**THE PAGE AT A GLANCE**
- PAGE JOB: hands off

**THE SECTIONS, IN ORDER**

S1 — opens on a count — lines 5–6
"The seven-day reset nobody told you about" · "I tried four of them before this one. {{ customer.first_name }}, here is what happened." [D1]
(furniture — see F2)

S2 — names why others fail — lines 8–9
"Each one worked for a week and then quit."

S3 — the offer and the ask — lines 10–11
"Save $26 today, a $7 value thrown in, 47% off." · [BUTTON Get the Glowpath kit -> /offer]

## Page furniture

F1 announcement strip — above — "Free returns on everything, always"
F2 site menu — above — "Home", "Shop the range"
F3 cookie bar — "We use cookies."
F4 footer — "Privacy Policy", "© 2026 Example Holdings. All rights reserved."

## Source defects

D1 — "{{ customer.first_name }}," — template tag as code — meant a first name

## Strip

```json
{"furniture_words": ["Shop the range", "Free returns on everything, always", "Home"],
 "defects": [{"id": "D1", "quote": "{{ customer.first_name }},", "meant": "a first name"}],
 "names": ["Glowpath", "Glowpath Labs", "Example Holdings"],
 "figures": ["$26", "$7", "47%", "12,000"],}
```
"""

CONSTRUCT = """# CONSTRUCT

**THE MOVES**
1. (from S1) Counts the alternatives already tried before anything is named. [SLOT: the count of failed alternatives]
2. (from S2) Names why the alternatives fail by design.
3. (from S3) Sets the terms against a bigger anchor. [SLOT: the anchor price the offer is set against]

**THE SEQUENCE LOGIC** — the count buys belief in the verdict.

**PROPORTION, RELATIVELY** — about half elapses before the ask.

**THE VOICE CONSTRUCT** — short flat sentences, first person.

**LOAD-BEARING** — the count; the single ask.

**WHAT IS PAGE-BOUND** — a button that repeats the ask; its job is to catch the reader at the moment of agreement.

**LEFT OUT:** F1, F2, F3, F4, D1
"""


def labels_answer(sections=("S1", "S2", "S3"), fence="```ELEMENTS", **over):
    E = L.library()
    ans = {L.key(el, a): {"id": E.rows(el, a)[0]["id"], "why": "S1 does it", "proposed": None}
           for el, a in L.single_lists()}
    sec = E.rows(*L.SECTION)[0]["id"]
    ans[L.key(*L.SECTION)] = [{"section": s, "id": sec, "why": f"{s} does it", "proposed": None} for s in sections]
    ans.update(over)
    return f"{fence}\n" + json.dumps(ans) + "\n```"


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
        self.src = WS / "saved" / "the-reset" / "page.html"
        self.src.parent.mkdir(parents=True, exist_ok=True)
        self.src.write_text(HTML)
        self.said = []
        shutil.rmtree(WS / "runs", ignore_errors=True)

    def run_it(self, *extra, stub=None, label="t1"):
        return R.main([str(self.src), "--brand", "testbrand", "--label", label,
                       "--source-url", "https://glowpathlabs.example/pages/the-reset", *extra],
                      runner=stub or Stub(), echo=self.said.append)

    def out(self, label="t1"):
        return WS / "runs" / "page-teardown" / "testbrand" / label


class Workspace(Base):
    def test_everything_resolves_inside_the_temp_workspace(self):
        self.assertEqual(P.REPO, WS)
        self.assertEqual(P.record_dir("testbrand", "x"), WS / "runs" / "page-teardown" / "testbrand" / "x")
        self.assertNotIn(str(REAL / "runs"), str(P.RECORDS))


class Reduce(Base):
    def test_html_becomes_readable_lines_and_noise_is_dropped(self):
        page = F.load(self.src)
        text = page["text"]
        self.assertIn("# The seven-day reset nobody told you about", text)
        self.assertIn("## Why the others stopped working", text)
        self.assertIn("[IMAGE alt=A chart of the four that failed · chart.png]", text)
        self.assertIn("[BUTTON Get the Glowpath kit -> /offer]", text)          # the tracking tail is cut
        for noise in ("tracking", "color:red", "The reset"):
            self.assertNotIn(noise, text)
        self.assertEqual(page["site_name"], "Glowpath Labs")
        self.assertLess(len(text), len(HTML))

    def test_the_free_scan_points_at_furniture_and_damage(self):
        found = F.scan(F.load(self.src))
        whys = " | ".join(f["why"] for f in found["furniture"])
        for zone in ("site menu", "cookie or consent bar", "footer", "announcement bar"):
            self.assertIn(zone, whys)
        self.assertEqual([d["quote"] for d in found["defects"]], ["{{ customer.first_name }}"])

    def test_a_second_copy_of_the_whole_page_is_dropped_and_a_repeated_ask_is_not(self):
        twice = WS / "twice.html"
        twice.write_text("<html><body>" + BODY + BODY.replace('href="/"', 'href="/m"') + "</body></html>")
        page = F.load(twice)
        self.assertEqual(page["text"].count("# The seven-day reset"), 1)
        self.assertGreater(page["second_copy_lines_dropped"], 5)
        once = F.load(self.src)
        self.assertEqual(once["second_copy_lines_dropped"], 0)

    def test_a_text_capture_is_read_as_it_stands(self):
        f = WS / "page.txt"
        f.write_text("A headline\nSome words\n")
        self.assertEqual(F.load(f)["text"], "A headline\nSome words\n")

    def test_names_come_from_the_page_the_address_and_the_brand_folder(self):
        self.assertEqual(F.code_names(F.load(self.src), "https://www.glowpathlabs.example/pages/x"),
                         ["Glowpath Labs", "glowpathlabs"])
        self.assertEqual(F.brand_names("testbrand"), ["Morning Kit Set", "Testbrand", "testbrand", "testbrandshop"])
        self.assertEqual(F.brand_names("nobody"), ["nobody"])


class TolerantSlots(unittest.TestCase):
    def test_a_slot_is_read_however_the_model_dressed_it(self):
        want = {"furniture_words": ["a b"], "defects": [], "names": [], "figures": []}
        body = json.dumps(want)
        for shape in (f"```STRIP\n{body}\n```", f"# STRIP\n\n```json\n{body}\n```", f"## Strip:\n```\n{body}\n```",
                      f"**STRIP**\n\n{body}\n", f"Here you go.\n```json\n{body}\n```"):
            self.assertEqual(F.strip_block(shape), want, shape)

    def test_a_missing_or_broken_slot_says_so(self):
        with self.assertRaisesRegex(ValueError, "no STRIP block"):
            F.strip_block("nothing here")
        with self.assertRaisesRegex(ValueError, "not valid JSON"):
            F.strip_block("```STRIP\n{not json}\n```")

    def test_headings_match_in_any_dress(self):
        for h in ("# SECTIONS AS READ", "## Sections as read", "**SECTIONS AS READ**", "### **Sections As Read:**"):
            self.assertTrue(S.heading("SECTIONS AS READ").search(h), h)
        self.assertFalse(S.heading("SECTIONS AS READ").search("the sections as read were long"))

    def test_the_labels_block_is_read_under_its_heading_with_sections_as_a_list_or_a_map(self):
        ans = labels_answer(fence="# ELEMENT LABELS\n\n```json")
        rec, problems = L.read(ans, ["S1", "S2", "S3"])
        self.assertEqual(problems, [])
        sec = L.library().rows(*L.SECTION)[0]["id"]
        as_map = labels_answer(**{"doctrine/section": {"S1": sec, "S2": {"id": sec}, "S3": sec}})
        rec, problems = L.read(as_map, ["S1", "S2", "S3"])
        self.assertEqual(problems, [])
        self.assertEqual(rec["labels"]["doctrine/section"], {"S1": sec, "S2": sec, "S3": sec})


class DryRun(Base):
    def test_spends_nothing_and_writes_nothing(self):
        stub = Stub()
        before = sorted(p.name for p in WS.iterdir())
        self.assertEqual(self.run_it("--dry-run", stub=stub), 0)
        self.assertEqual(stub.calls, [])
        self.assertEqual(sorted(p.name for p in WS.iterdir()), before)      # no runs/ made
        text = "\n".join(self.said)
        self.assertIn("would file  runs/page-teardown/testbrand/t1/", text)
        self.assertIn("0 model calls", text)
        self.assertIn("chars on file →", text)
        for tier in ("reads", "checks", "designs"):
            self.assertIn(f"({tier})", text)

    def test_names_what_is_missing(self):
        code = R.main([str(WS / "nope.html"), "--brand", "nobrand", "--dry"], runner=Stub(), echo=self.said.append)
        self.assertEqual(code, 1)
        text = "\n".join(self.said)
        self.assertIn("not on file", text)
        self.assertIn("does not fetch", text)
        self.assertIn("`nobrand` is not a brand folder", text)
        self.assertIn("testbrand", text)                                    # the real ones are named

    def test_a_shell_page_with_nothing_to_read_is_named(self):
        self.src.write_text("<html><body><div id='app'></div><script>render()</script></body></html>")
        self.assertEqual(self.run_it("--dry"), 1)
        self.assertIn("almost nothing to read", "\n".join(self.said))

    def test_there_is_no_default_brand(self):
        with self.assertRaises(SystemExit):
            R.main([str(self.src), "--dry-run"], runner=Stub(), echo=self.said.append)

    def test_the_label_defaults_to_the_saved_pages_folder(self):
        R.main([str(self.src), "--brand", "testbrand", "--dry"], runner=Stub(), echo=self.said.append)
        self.assertIn("label the-reset", self.said[0])


class FullRun(Base):
    def test_files_the_run_and_passes_every_gate(self):
        stub = Stub()
        self.assertEqual(self.run_it(stub=stub), 0, self.said)
        self.assertEqual([c[0] for c in stub.calls], ["tear1", "tear2", "tear3"])
        out = self.out()
        for f in ("source--as-read.md", "tear1--record.md", "tear1--sent.md", "tear2--labels.md", "tear3--construct.md",
                  "tear3--sent.md", "elements.json", "strip.json", "run.json", "check.json"):
            self.assertTrue((out / f).is_file(), f)
        check = json.loads((out / "check.json").read_text())
        self.assertEqual({g: v["result"] for g, v in check.items()},
                         {"inputs": "pass", "copy": "pass", "elements": "pass"})
        run = json.loads((out / "run.json").read_text())
        self.assertEqual((run["tool"], run["brand"], run["state"]), ("page-teardown", "testbrand", "filed"))
        self.assertEqual(run["assignment"]["source_url"], "https://glowpathlabs.example/pages/the-reset")
        self.assertEqual(set(run["elements"]["labels"]["doctrine/section"]), {"S1", "S2", "S3"})
        self.assertIn("format/page", run["elements"]["labels"])

    def test_tiers_not_model_ids_pick_the_model_and_a_big_page_steps_up(self):
        stub = Stub()
        self.run_it(stub=stub)
        sys.path.append(str(P.RUN_KIT))
        from run_kit import model as M
        self.assertEqual([m for _, m in stub.calls], [M.TIERS["reads"], M.TIERS["checks"], M.TIERS["designs"]])
        forced = Stub()
        self.run_it("--model", "one-model", stub=forced, label="t2")
        self.assertEqual({m for _, m in forced.calls}, {"one-model"})
        big = WS / "big.txt"
        big.write_text("A long page of words. " * (M.SMALL_WINDOW_CHARS // 20))
        stub3 = Stub()
        R.main([str(big), "--brand", "testbrand", "--label", "t3"], runner=stub3, echo=self.said.append)
        self.assertEqual(stub3.calls[0], ("tear1", M.TIERS["designs"]))

    def test_the_code_findings_reach_the_read_and_later_steps_never_see_furniture(self):
        stub = Stub()
        self.run_it(stub=stub)
        self.assertIn("sat inside the page's site menu", stub.prompts["tear1"])
        self.assertIn("   5  # The seven-day reset", stub.prompts["tear1"])         # numbered lines
        for step in ("tear2", "tear3"):
            self.assertNotIn("Shop the range", stub.prompts[step])
            self.assertNotIn("furniture_words", stub.prompts[step])
            self.assertIn("Items set aside: F1, F2, F3, F4", stub.prompts[step])
            self.assertIn("S3 — the offer and the ask", stub.prompts[step])

    def test_a_finished_run_is_reused_and_a_changed_page_is_read_again(self):
        self.run_it()
        again = Stub()
        self.assertEqual(self.run_it(stub=again), 0)
        self.assertEqual(again.calls, [])
        self.src.write_text(HTML.replace("More words", "Other words"))
        changed = Stub()
        self.run_it(stub=changed)
        self.assertEqual([c[0] for c in changed.calls], ["tear1", "tear2", "tear3"])

    def test_rerun_from_a_step(self):
        self.run_it()
        stub = Stub()
        self.run_it("--rerun-from", "tear3", stub=stub)
        self.assertEqual([c[0] for c in stub.calls], ["tear3"])


class ElementsGate(Base):
    def test_an_unknown_label_is_refused_with_the_real_ids_named(self):
        stub = Stub(labels=labels_answer(**{"format/page": "made-up-format"}))
        self.assertEqual(self.run_it(stub=stub), 2)
        self.assertEqual([c[0] for c in stub.calls], ["tear1", "tear2"])       # the construct never ran
        check = json.loads((self.out() / "check.json").read_text())
        self.assertEqual(check["elements"]["result"], "HELD")
        real = L.library().rows("format", "page")[0]["id"]
        self.assertIn(real, check["elements"]["problems"][0])
        rec = json.loads((self.out() / "elements.json").read_text())
        self.assertEqual(rec["refused"][0]["id"], "made-up-format")
        self.assertNotIn("format/page", rec["labels"])

    def test_an_unknown_section_label_is_refused_and_a_skipped_section_is_held(self):
        sec = L.library().rows(*L.SECTION)[0]["id"]
        bad = labels_answer(**{"doctrine/section": [{"section": "S1", "id": "vibes"}, {"section": "S2", "id": sec}]})
        self.assertEqual(self.run_it(stub=Stub(labels=bad)), 2)
        problems = " | ".join(json.loads((self.out() / "check.json").read_text())["elements"]["problems"])
        self.assertIn("doctrine/section S1: REFUSED", problems)
        self.assertIn(sec, problems)
        self.assertIn("doctrine/section S3: the record numbers this section", problems)

    def test_none_fits_is_recorded_as_a_proposed_row_never_written_to_the_library(self):
        lib = REAL / "components" / "elements" / "library"
        before = {f.name: f.read_bytes() for f in lib.glob("*.json")}
        sec = L.library().rows(*L.SECTION)[0]["id"]
        stub = Stub(labels=labels_answer(**{
            "format/page": {"id": "none-fits", "why": "S1–S3 run as a diary", "proposed": "diary-page — Diary page — dated entries that end on the ask"},
            "doctrine/section": [{"section": "S1", "id": sec}, {"section": "S2", "id": "none-fits", "why": "S2",
                                  "proposed": "design-flaw — Design flaw — why the alternatives fail by construction"},
                                 {"section": "S3", "id": sec}]}))
        self.assertEqual(self.run_it(stub=stub), 0, self.said)
        run = json.loads((self.out() / "run.json").read_text())
        self.assertTrue(run["elements"]["proposed"]["format/page"].startswith("diary-page"))
        self.assertTrue(run["elements"]["proposed"]["doctrine/section"]["S2"].startswith("design-flaw"))
        self.assertEqual({f.name: f.read_bytes() for f in lib.glob("*.json")}, before)

    def test_none_fits_without_a_proposed_row_is_held(self):
        stub = Stub(labels=labels_answer(**{"format/page": {"id": "none-fits", "why": "x", "proposed": None}}))
        self.assertEqual(self.run_it(stub=stub), 2)

    def test_the_classifiers_word_is_recorded_beside_the_label_and_holds_nothing(self):
        self.run_it()
        rec = json.loads((self.out() / "elements.json").read_text())
        self.assertIn("code_format", rec)
        self.assertIn(rec["format_agrees_with_code"], (True, False, None))


class CopyGate(Base):
    def held(self, construct):
        self.n = getattr(self, "n", 0) + 1                 # a fresh label each time: a finished step is reused
        label = f"held{self.n}"
        self.assertEqual(self.run_it(stub=Stub(construct=construct), label=label), 2)
        check = json.loads((self.out(label) / "check.json").read_text())
        self.assertEqual(check["copy"]["result"], "HELD")
        return " | ".join(check["copy"]["problems"])

    def swap(self, new, old="the single ask"):
        return CONSTRUCT.replace(old, new)

    def test_any_money_figure_in_the_construct_holds_it(self):
        why = self.held(self.swap("a $7 Value thrown in, Save $26"))
        self.assertIn("“$7”", why)
        self.assertIn("“$26”", why)
        self.assertIn("“$1,200.50”", self.held(self.swap("an anchor of $1,200.50")))     # not only the source's own

    def test_one_of_the_sources_own_figures_holds_it(self):
        self.assertIn("“47%”", self.held(self.swap("the 47% saving")))

    def test_the_sources_names_hold_it(self):
        self.assertIn("“Glowpath”", self.held(self.swap("the Glowpath ask")))
        self.assertIn("Example Holdings", self.held(self.swap("what example holdings asks")))

    def test_the_address_and_the_runs_own_brand_hold_it_whatever_the_case(self):
        self.assertIn("glowpathlabs", self.held(self.swap("as GlowpathLabs does")))
        self.assertIn("estbrand", self.held(self.swap("how TESTBRAND would ask")))
        self.assertIn("Morning Kit Set", self.held(self.swap("the morning kit set")))

    def test_a_one_word_name_in_lower_case_is_an_ordinary_word(self):
        strip = {"names": ["Reset"], "furniture_words": [], "defects": [], "figures": []}
        self.assertEqual(F.construct_problems(self.swap("the reader wants a reset"), strip), [])
        self.assertTrue(F.construct_problems(self.swap("the Reset ask"), strip))

    def test_furniture_words_and_the_sites_frame_hold_it(self):
        self.assertIn("shop the range", self.held(self.swap("the Shop the Range strip")))
        self.assertIn("footer", self.held(self.swap("the footer carries the ask")))
        self.assertIn("cookie banner", self.held(self.swap("a cookie banner first")))

    def test_a_carried_defect_or_template_tag_holds_it(self):
        why = self.held(self.swap('opens "{{ customer.first_name }}," flat'))
        self.assertIn("source defect (D1)", why)
        self.assertIn("template tag", why)

    def test_an_unfilled_note_or_a_missing_part_holds_it(self):
        self.assertIn("UNFILLED", self.held(self.swap("[UNFILLED: no proof]")))
        self.assertIn("LEFT OUT", self.held(CONSTRUCT.split("**LEFT OUT")[0]))
        self.assertIn("THE SEQUENCE LOGIC", self.held(CONSTRUCT.replace("**THE SEQUENCE LOGIC**", "**ORDER**")))

    def test_what_sits_on_the_left_out_line_is_not_swept(self):
        self.assertEqual(self.run_it(stub=Stub(construct=CONSTRUCT + "\n(F4 was the footer.)\n")), 0)

    def test_a_record_without_its_labelled_parts_is_held_before_anything_else_is_spent(self):
        stub = Stub(record="Here is a summary of the page, all in one run.")
        self.assertEqual(self.run_it(stub=stub), 2)
        self.assertEqual([c[0] for c in stub.calls], ["tear1"])
        problems = json.loads((self.out() / "check.json").read_text())["copy"]["problems"]
        self.assertTrue(any("PAGE FURNITURE" in p for p in problems))
        self.assertTrue(any("STRIP" in p for p in problems))

    def test_a_record_that_numbers_no_sections_is_held(self):
        rec = RECORD.replace("S1 —", "First —").replace("S2 —", "Second —").replace("S3 —", "Third —")
        self.assertEqual(self.run_it(stub=Stub(record=rec)), 2)
        self.assertIn("numbers no sections", " ".join(json.loads((self.out() / "check.json").read_text())["copy"]["problems"]))


class NoBrandInTheTool(unittest.TestCase):
    def test_no_brand_name_in_the_code_or_prompts(self):
        brands = [p.name for p in (REAL / "brands").iterdir() if p.is_dir() and not p.name.startswith(("_", "."))]
        files = sorted(TOOLS.glob("*.py")) + sorted((HERE.parent / "prompts").glob("*.md"))
        self.assertGreaterEqual(len(files), 8)
        for f in files:
            low = f.read_text().lower()
            for b in brands:
                self.assertNotIn(b.lower(), low, f"{f.name} names the brand {b}")

    def test_every_prompt_opens_on_the_invented_example_guard(self):
        for f in sorted((HERE.parent / "prompts").glob("*.md")):
            self.assertRegex(f.read_text()[:200], r"example", f.name)
            self.assertRegex(f.name, r"-v\d+-damon\.md$")


def tearDownModule():
    shutil.rmtree(WS, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=1)
