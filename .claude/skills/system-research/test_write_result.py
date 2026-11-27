#!/usr/bin/env python3
"""Tests for write_result.py — SI-95 (system research)'s declared tests.

    /usr/bin/python3 .claude/skills/system-research/test_write_result.py

Stdlib only. Every write goes to a temp runs root; the real runs/ is never touched.
"""
import contextlib
import copy
import html
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_result as wr  # noqa: E402

FIXTURE = {
    "job": "Alert when a web store's stock drops below ours",
    "parts": ["drive a browser", "read the store's data", "compare with our stock",
              "alert on a schedule"],
    "our_system": {"answer": "extend", "matches": [
        {"name": "page capture", "path": "components/example/capture.py",
         "what": "drives a browser to capture pages", "note": "different job, same part"}]},
    "parts_we_have": [{"part": "drive a browser", "name": "Playwright scripts",
                       "path": "components/example/capture.py", "note": ""}],
    "outside": [
        {"shelf": "apps", "name": "Stock alert app", "trust_tier": "official vendor",
         "url": "https://example.com/app", "notes": "$10/month"},
        {"shelf": "open-source", "name": "a scraper lib", "trust_tier": "well-known open source",
         "url": "https://example.org/lib", "notes": ""}],
    "options": [
        {"name": "Adopt the app", "fit": "whole job", "cost": "$10/mo", "time": "1 day",
         "needs": "store access", "maintainer": "vendor", "recommended": True},
        {"name": "Extend capture", "fit": "parts 1-2", "cost": "dev time", "time": "1 week",
         "needs": "none", "maintainer": "us", "recommended": False}],
    "recommendation": {"text": "Trial the app for a week.", "confidence": "medium",
                       "trial": "Install on a test store; compare one week of alerts.",
                       "would_change_it": "Alerts miss more than one drop."},
    "flow": [
        {"step": "Watch the store", "who_or_what": "the app", "part": "read the store's data",
         "chip": "outside"},
        {"step": "Compare with our stock", "who_or_what": "a person", "part": "", "chip": "person"},
        {"step": "Decide on the threshold", "who_or_what": "owner", "part": "", "chip": "open"}],
    "could_also_help": [{"option": "Adopt the app", "work": "every store's stock checks"}],
    "sources": [{"label": "vendor page", "ref": "https://example.com/app"},
                {"label": "capture code", "ref": "components/example/capture.py"}],
}

SKETCH = {
    "title": "Stock against the store",
    "kind": "simulator",
    "data": "example",
    "html": ('<!doctype html><svg xmlns="http://www.w3.org/2000/svg" width="200" height="40">'
             '<rect id="bar" width="120" height="40"/></svg><input type="range" id="s">'
             '<script>s.oninput=()=>bar.setAttribute("width",s.value*2)</script>'),
    "note": "Drag the slider: the bar is our stock.",
}
ORDER = ["Recommendation", "The five steps", "How the recommendation would work", "Sketch",
         "What our system has", "Parts we already have", "What exists outside",
         "The options", "Could also help other work", "The cheap trial", "Sources"]


def with_sketch(**changes):
    r = copy.deepcopy(FIXTURE)
    r["sketch"] = dict(copy.deepcopy(SKETCH), **changes)
    return r


def headings(page):
    return re.findall(r'<section id="[^"]+"><h2>([^<]+)</h2>', page)


class WriteResultTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "runs" / "system-research"

    def tearDown(self):
        self.tmp.cleanup()

    def test_files_land_under_the_injected_runs_root(self):
        folder, jp, pp = wr.write(copy.deepcopy(FIXTURE), self.root, "2026-10-08")
        self.assertEqual(folder.parent, self.root)
        self.assertTrue(folder.name.startswith("2026-10-08-alert-when-a-web-store"))
        self.assertTrue(jp.is_file() and pp.is_file())
        self.assertEqual({p.name for p in folder.iterdir()}, {"result.json", "page.html"})

    def test_workspace_root_is_found_by_walking_up(self):
        self.assertTrue((wr.repo_root() / "components").is_dir())
        self.assertTrue((wr.repo_root() / ".claude").is_dir())

    def test_result_json_round_trips(self):
        _, jp, _ = wr.write(copy.deepcopy(FIXTURE), self.root, "2026-10-08")
        back = json.loads(jp.read_text(encoding="utf-8"))
        expected = dict(copy.deepcopy(FIXTURE), date="2026-10-08",
                        slug=wr.slugify(FIXTURE["job"]))
        self.assertEqual(back, expected)

    def test_page_has_every_section_in_the_fixed_order(self):
        self.assertEqual([h for _, h in wr.SECTIONS], ORDER)
        _, _, pp = wr.write(with_sketch(), self.root, "2026-10-08")
        self.assertEqual(headings(pp.read_text(encoding="utf-8")), ORDER)
        _, _, pp = wr.write(copy.deepcopy(FIXTURE), self.root, "2026-10-08")
        self.assertEqual(headings(pp.read_text(encoding="utf-8")),
                         [h for h in ORDER if h != "Sketch"])

    def test_object_sketch_renders_a_sandboxed_iframe(self):
        _, _, pp = wr.write(with_sketch(data="real"), self.root, "2026-10-08")
        page = pp.read_text(encoding="utf-8")
        sec = page.split('<section id="sketch">', 1)[1].split("</section>", 1)[0]
        self.assertEqual(sec.count("<iframe"), 1)
        self.assertIn('sandbox="allow-scripts"', sec)
        self.assertNotIn("allow-same-origin", page)
        self.assertIn("Stock against the store", sec)
        self.assertIn("real data", sec)
        self.assertNotIn("not real", sec)
        self.assertIn("Drag the slider", sec)
        self.assertNotIn("<script", page)  # the sketch sits escaped inside srcdoc
        srcdoc = re.search(r'srcdoc="([^"]*)"', sec).group(1)
        self.assertEqual(html.unescape(srcdoc), SKETCH["html"])

    def test_example_data_is_labelled_not_real(self):
        _, _, pp = wr.write(with_sketch(), self.root, "2026-10-08")
        sec = pp.read_text(encoding="utf-8").split('<section id="sketch">', 1)[1]
        self.assertIn("example data — not real", sec.split("<iframe", 1)[0])

    def test_sketch_that_calls_out_is_refused(self):
        bad = [
            '<script src="https://cdn.example.com/x.js"></script>',
            "<img src='http://example.com/a.png'>",
            '<link rel="stylesheet" href="https://fonts.example.com/a.css">',
            '<iframe src="//example.com"></iframe>',
            '<script>fetch("https://api.example.com/stock")</script>',
            '<script>import("https://esm.example.com/m.js")</script>',
            '<script>var u="https://api.example.com";var x=new XMLHttpRequest();x.open("GET",u)</script>',
            '<style>body{background:url(https://example.com/b.png)}</style>',
        ]
        for body in bad:
            with self.subTest(body=body):
                with self.assertRaises(wr.Refused):
                    wr.validate(with_sketch(html=body))
        src = Path(self.tmp.name) / "bad.json"
        src.write_text(json.dumps(with_sketch(html=bad[0])), encoding="utf-8")
        self.assertEqual(wr.main([str(src), "--out-root", str(self.root)]), 2)
        self.assertFalse(self.root.exists())
        wr.validate(with_sketch())  # the SVG namespace URI is not a call

    def test_bad_sketch_fields_are_refused(self):
        for changes in ({"kind": "video"}, {"kind": None}, {"data": "real-ish"},
                        {"html": ""}, {"html": "   "}, {"title": ""}):
            with self.subTest(changes=changes):
                with self.assertRaises(wr.Refused):
                    wr.validate(with_sketch(**changes))
        for kind in wr.SKETCH_KINDS:
            wr.validate(with_sketch(kind=kind))
        lst = copy.deepcopy(FIXTURE)
        lst["sketch"] = ["not", "a", "sketch"]
        with self.assertRaises(wr.Refused):
            wr.validate(lst)

    def test_use_it_skips_the_sketch_with_a_note(self):
        r = with_sketch()
        r["our_system"]["answer"] = "use"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            _, jp, pp = wr.write(r, self.root, "2026-10-08")
        page = pp.read_text(encoding="utf-8")
        self.assertNotIn("Sketch", headings(page))
        self.assertNotIn("<iframe", page)
        self.assertIn("sketch not rendered", err.getvalue())
        self.assertEqual(json.loads(jp.read_text(encoding="utf-8"))["sketch"], r["sketch"])

    def test_old_string_sketch_still_renders_as_text(self):
        r = copy.deepcopy(FIXTURE)
        r["sketch"] = "watch -> compare <stock> -> alert"
        _, _, pp = wr.write(r, self.root, "2026-10-08")
        page = pp.read_text(encoding="utf-8")
        rec = page.split('<section id="recommendation">', 1)[1].split("</section>", 1)[0]
        self.assertIn("<h3>Sketch</h3><pre>watch -&gt; compare &lt;stock&gt; -&gt; alert</pre>", rec)
        self.assertNotIn("Sketch", headings(page))
        self.assertNotIn("<iframe", page)

    def test_page_marks_the_recommended_row_and_tallies_chips(self):
        _, _, pp = wr.write(copy.deepcopy(FIXTURE), self.root, "2026-10-08")
        page = pp.read_text(encoding="utf-8")
        self.assertEqual(page.count('<tr class="rec">'), 1)
        self.assertIn("★ recommended</td><td>Adopt the app", page)
        tally = page.split('<div class="tally">', 1)[1].split("</div>", 1)[0]
        self.assertEqual(tally.count('class="chip'), 6)
        self.assertNotIn("<script", page)

    def test_unknown_chip_is_refused(self):
        bad = copy.deepcopy(FIXTURE)
        bad["flow"][0]["chip"] = "maybe"
        with self.assertRaises(wr.Refused):
            wr.write(bad, self.root, "2026-10-08")
        self.assertFalse(self.root.exists())

    def test_answer_enum_is_enforced(self):
        for answer in ("use", "extend", "being-built", "nothing"):
            ok = copy.deepcopy(FIXTURE)
            ok["our_system"]["answer"] = answer
            wr.validate(ok)
        for answer in ("build it", "", None, "USE"):
            bad = copy.deepcopy(FIXTURE)
            bad["our_system"]["answer"] = answer
            with self.assertRaises(wr.Refused):
                wr.validate(bad)

    def test_trust_tier_and_single_recommendation_enforced(self):
        bad = copy.deepcopy(FIXTURE)
        bad["outside"][0]["trust_tier"] = "trust me"
        with self.assertRaises(wr.Refused):
            wr.validate(bad)
        two = copy.deepcopy(FIXTURE)
        two["options"][1]["recommended"] = True
        with self.assertRaises(wr.Refused):
            wr.validate(two)

    def test_existing_folder_is_never_overwritten(self):
        f1, _, _ = wr.write(copy.deepcopy(FIXTURE), self.root, "2026-10-08")
        f2, _, _ = wr.write(copy.deepcopy(FIXTURE), self.root, "2026-10-08")
        self.assertNotEqual(f1, f2)
        self.assertTrue(f2.name.endswith("-2"))

    def test_cli_refusal_exits_2(self):
        bad = copy.deepcopy(FIXTURE)
        bad["our_system"]["answer"] = "probably"
        src = Path(self.tmp.name) / "bad.json"
        src.write_text(json.dumps(bad), encoding="utf-8")
        self.assertEqual(wr.main([str(src), "--out-root", str(self.root)]), 2)

    def test_skill_triggers_include_component_checks(self):
        text = (HERE / "SKILL.md").read_text(encoding="utf-8")
        front = text.split("---", 2)[1]
        self.assertIn("name: system-research", front)
        for phrase in ("is there a component for X", "do we already have something that does X",
                       "component check", "check the register before I build this",
                       '"build"', "write a script", "make a tool", "is there a tool for",
                       "what's out there for", "does this already exist"):
            self.assertIn(phrase, front)


if __name__ == "__main__":
    unittest.main(verbosity=2)
