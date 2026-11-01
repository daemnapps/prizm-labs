#!/usr/bin/env python3
"""The library page renders every list the index carries (SI-135 (elements rows truthful)).

    python3 test_page_every_list.py

Proves, offline, on a temp copy of components/elements (the real folder is
never written): build() leaves a fresh library.html; every list in index.json
has a section on it; the first eight sections are page.ORDER's, in order; an
element with no QUESTION line gets the fallback; and the list order the image
teardown's labeler reads — index.json's `lists` order, and its LISTS resolved
against it — is byte-identical before and after build().
"""
import ast
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import elements as E  # noqa: E402
import page as PG  # noqa: E402

LABELER = E.REPO / "tools/image-teardown/tools/elements_label.py"


def _labeler_lists():
    """elements_label.LISTS, read from its source — importing it would import
    the teardown's paths.py, which acts at import time."""
    tree = ast.parse(LABELER.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "LISTS" for t in node.targets):
            return [tuple(x) for x in ast.literal_eval(node.value)]
    raise AssertionError(f"no LISTS in {LABELER}")


def _order_bytes(index_file):
    """The order the labeler sees: index.json's lists, and LISTS resolved against them."""
    idx = json.loads(Path(index_file).read_text())
    order = [[l["element"], l["asset"]] for l in idx["lists"]]
    pos = {(el, asset): i for i, (el, asset) in enumerate(order)}
    files = {(l["element"], l["asset"]): l["file"] for l in idx["lists"]}
    resolved = [[el, asset, pos.get((el, asset)), files.get((el, asset))] for el, asset in _labeler_lists()]
    return (json.dumps(order, ensure_ascii=False).encode("utf-8"),
            json.dumps(resolved, ensure_ascii=False).encode("utf-8"))


def _sections(page):
    """[(element, section html)] in page order."""
    parts = re.split(r'<section id="', page)[1:]
    return [(p.split('"', 1)[0], p.split("</section>", 1)[0]) for p in parts]


class BuildRendersEveryList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.T = cls.tmp / "elements"
        shutil.copytree(str(E.ROOT), str(cls.T))
        cls.real_index = (E.ROOT / "library" / "index.json").read_bytes()
        cls.real_page = (E.ROOT / "library.html").read_bytes() if (E.ROOT / "library.html").is_file() else None
        cls.before = _order_bytes(cls.T / "library" / "index.json")
        (cls.T / "library.html").write_text("stale")
        patches = [mock.patch.object(E, "ROOT", cls.T), mock.patch.object(E, "LIBRARY", cls.T / "library")]
        for p in patches:
            p.start()
        E._cache.clear()
        try:
            cls.index = E.build()
        finally:
            for p in patches:
                p.stop()
            E._cache.clear()
        cls.after = _order_bytes(cls.T / "library" / "index.json")
        cls.page = (cls.T / "library.html").read_text()
        cls.sections = _sections(cls.page)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_build_leaves_a_fresh_page(self):
        self.assertNotEqual(self.page, "stale")
        self.assertIn("<title>The Element Library</title>", self.page)

    def test_every_element_has_a_section(self):
        got = [el for el, _ in self.sections]
        for el in {l["element"] for l in self.index["lists"]}:
            self.assertIn(el, got, f"{el} has no section on library.html")
        self.assertEqual(len(got), len(set(got)), "an element rendered twice")

    def test_every_list_appears_in_its_elements_section(self):
        body = dict(self.sections)
        for l in self.index["lists"]:
            self.assertIn(f'<b>{l["asset"]}</b>', body[l["element"]],
                          f'{l["element"]}/{l["asset"]} is missing from library.html')

    def test_first_eight_sections_are_order(self):
        self.assertEqual([el for el, _ in self.sections][:len(PG.ORDER)], PG.ORDER)

    def test_the_rest_follow_index_order(self):
        rest = []
        for l in self.index["lists"]:
            if l["element"] not in PG.ORDER and l["element"] not in rest:
                rest.append(l["element"])
        self.assertEqual([el for el, _ in self.sections][len(PG.ORDER):], rest)

    def test_labeler_order_is_byte_identical(self):
        self.assertEqual(self.before[0], self.after[0], "index.json's lists order moved")
        self.assertEqual(self.before[1], self.after[1], "LISTS resolve differently")
        for el, asset, pos, f in json.loads(self.after[1]):
            self.assertIsNotNone(pos, f"{el}/{asset} is not in index.json")

    def test_the_real_folder_is_untouched(self):
        self.assertEqual((E.ROOT / "library" / "index.json").read_bytes(), self.real_index)
        if self.real_page is not None:
            self.assertEqual((E.ROOT / "library.html").read_bytes(), self.real_page)


class Fallback(unittest.TestCase):
    def test_an_element_with_no_question_gets_the_fallback(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            lib = tmp / "library"
            lib.mkdir()
            (lib / "zz.one.json").write_text(json.dumps({"rows": [
                {"id": "a", "name": "A", "what": "a row", "approved": False, "status": "draft"}]}))
            (lib / "index.json").write_text(json.dumps({"lists": [{
                "element": "zz", "asset": "one", "file": "library/zz.one.json", "source": "inline",
                "enforced_by": None, "note": None, "rows": 1, "approved": 0}]}))
            out = PG.render(lib)
            self.assertEqual(out, tmp / "library.html")
            secs = _sections(out.read_text())
            self.assertEqual([el for el, _ in secs], PG.ORDER + ["zz"])
            self.assertIn(PG.FALLBACK, dict(secs)["zz"])
            self.assertIn("<b>one</b>", dict(secs)["zz"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_letterform_has_its_own_question(self):
        self.assertEqual(PG.question("letterform"), "what lettering does it use?")


if __name__ == "__main__":
    unittest.main(verbosity=2)
