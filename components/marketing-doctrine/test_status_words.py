#!/usr/bin/env python3
"""The status words on the four definition files (SI-76 (doctrine maturity state)).

    python3 components/marketing-doctrine/test_status_words.py

Rule 6 (components/CLAUDE.md, triage page 15, Option A): every entry of a
manifest carries `status` in draft / approved / deprecated, and any other
meaning goes in `state`. frameworks.json, delivery.json, spoken.json and
ad-frameworks.json are all read entry by entry, so every entry here carries a
status; ad-frameworks' old seed/proven lives on as `state`. This proves the
words are there, that the slice and the composed card show both, and that the
one gate on the old word (the element library's `approved`) reads a proven
row as approved and a seed row as not — before and after the word moved.

Other components are reached only through their declared surfaces (O2
(contract not internals), SI-117 (doctrine test seams)): elements through
`use(library)` + `get` / `check` over a temp library; video-teardown through
`compose.extras_for`, a SEAM. How `build` derives `approved` from `status` is
elements' own test (components/elements/machine/test_status_words.py).

Stdlib only (unittest, tempfile), no key, no network.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True      # a test run leaves no __pycache__ behind

HERE = Path(__file__).resolve().parent
COMPONENTS = HERE.parent
VT_MACHINE = COMPONENTS / "video-teardown" / "machine"
ELEMENTS_MACHINE = COMPONENTS / "elements" / "machine"
ELEMENTS_LIBRARY = COMPONENTS / "elements" / "library"     # the built library/ (elements CLAUDE.md, Files)
for _p in (HERE, VT_MACHINE, ELEMENTS_MACHINE):              # appended, never ahead of what is there
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

import render                # noqa: E402
import compose as C          # noqa: E402
import elements as E         # noqa: E402

RULE6 = {"draft", "approved", "deprecated"}

# Every path whose rows are entries. "a[].b" means every b-list of every row
# of a. Sub-structure of one entry (techniques[].sub_methods, .method,
# written_vs_spoken[].receipts, frameworks[].sections) is approved with its
# entry and is deliberately absent.
ROWS = {
    "frameworks.json": [
        "desire.sources_of_desire", "desire.dimensions", "awareness.levels",
        "sophistication.stages", "techniques", "mood.rules",
        "verification.three_distinct_things", "verification.rules",
        "offer_close.rules", "sections", "research_questions",
        "frameworks_crosswalk.rows",
    ],
    "delivery.json": ["dials", "dials[].values"],
    "spoken.json": [
        "written_vs_spoken", "levels", "register_recipes.recipes",
        "punctuation_map.marks", "demographic_bands.bands",
    ],
    "ad-frameworks.json": ["frameworks"],
}


def _load(name):
    return json.loads((HERE / name).read_text())


def _dig(d, dotted):
    for part in dotted.split("."):
        d = d[part]
    return d


def _lists(doc, path):
    """Every row-list a path names: one list, or one per parent row for a[].b."""
    if "[]." in path:
        parent, child = path.split("[].", 1)
        return [_dig(row, child) for row in _dig(doc, parent)]
    return [_dig(doc, path)]


def _status_strings(o):
    """Every string `status` value anywhere in a parsed file."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "status" and isinstance(v, str):
                yield v
            for x in _status_strings(v):
                yield x
    elif isinstance(o, list):
        for v in o:
            for x in _status_strings(v):
                yield x


def _library_row(r, status, state, approved):
    """One ad-frameworks row as the element library holds it (its row fields)."""
    return {"id": r["id"], "name": r["name"], "what": r.get("what"), "why_it_works": None,
            "status": status, "state": state, "signed": None, "examples": None,
            "evidence": None, "approved": approved, "source": "ad-frameworks.json",
            "extra": {}, "aliases": [], "note": None}


def _framework_library(root, rows):
    """A temp element library holding one list, framework/all."""
    entry = {"element": "framework", "asset": "all", "source": "ad-frameworks.json",
             "enforced_by": None, "note": None, "rows": rows, "dropped": {},
             "duplicates": [], "off_rule": [], "off_status": [], "unresolved": []}
    (root / "framework.all.json").write_text(json.dumps(entry))
    return root


class StatusWords(unittest.TestCase):

    def test_imports_come_from_their_homes(self):
        # the paths are appended, so nothing earlier on sys.path may stand in
        self.assertEqual(Path(render.__file__).resolve().parent, HERE)
        self.assertEqual(Path(C.__file__).resolve().parent, VT_MACHINE)
        self.assertEqual(Path(E.__file__).resolve().parent, ELEMENTS_MACHINE)

    def test_every_entry_carries_a_rule6_status(self):
        total = 0
        for name, paths in ROWS.items():
            doc = _load(name)
            for path in paths:
                for rows in _lists(doc, path):
                    self.assertTrue(rows, "%s %s is empty" % (name, path))
                    for i, r in enumerate(rows):
                        self.assertIn(r.get("status"), RULE6,
                                      "%s %s[%d] status %r" % (name, path, i, r.get("status")))
                        total += 1
            bad = sorted(set(s for s in _status_strings(doc) if s not in RULE6))
            self.assertEqual(bad, [], "%s carries a status outside rule 6" % name)
        self.assertGreaterEqual(total, 184)

    def test_ad_frameworks_state_carries_seed_or_proven(self):
        a = _load("ad-frameworks.json")
        self.assertEqual(set(a["status_values"]), RULE6)
        self.assertEqual(set(a["state_values"]), {"seed", "proven"})
        for r in a["frameworks"]:
            self.assertIn(r["state"], {"seed", "proven"}, r["id"])
            if r["status"] == "approved":
                self.assertEqual(r["state"], "proven", r["id"])
            if r["state"] == "proven":
                self.assertIn(r["status"], {"approved", "deprecated"}, r["id"])
            if r["state"] == "seed":
                self.assertIn(r["status"], {"draft", "deprecated"}, r["id"])

    def test_the_slice_shows_status_and_state(self):
        text = render.ad_frameworks(_load("frameworks.json"))
        self.assertIn("| Framework | Status | State |", text)
        for r in _load("ad-frameworks.json")["frameworks"]:
            self.assertIn("| %s (`%s`) | %s | %s |" % (r["name"], r["id"], r["status"], r["state"]),
                          text)

    def test_compose_card_names_both(self):
        r = _load("ad-frameworks.json")["frameworks"][0]
        card = C.extras_for({"framework": r, "format": {}, "brand": "zz-brand"})["ad_framework"]
        self.assertIn("- **Status:** %s · **State:** %s · " % (r["status"], r["state"]), card)

    def test_elements_reads_proven_as_approved_seed_as_not(self):
        a, b = _load("ad-frameworks.json")["frameworks"][:2]
        key = ("framework", "all")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                E.use(_framework_library(Path(tmp), [
                    _library_row(a, "approved", "proven", True),
                    _library_row(b, "draft", "seed", False)]))
                signed = E.get("framework", "all", a["id"])
                self.assertEqual((signed["status"], signed["state"]), ("approved", "proven"))
                self.assertIs(signed["approved"], True)
                unsigned = E.get("framework", "all", b["id"])
                self.assertEqual((unsigned["status"], unsigned["state"]), ("draft", "seed"))
                self.assertIs(unsigned["approved"], False)
                self.assertEqual(E.check({key: a["id"]}, approved_only=True), [])
                self.assertEqual(E.check({key: b["id"]}, approved_only=True),
                                 ["framework/all `%s` is a draft, not approved" % b["id"]])
                self.assertEqual(E.check({key: [a["id"], b["id"]]}), [])    # both are real ones
            finally:
                E.use(ELEMENTS_LIBRARY)


if __name__ == "__main__":
    unittest.main()
