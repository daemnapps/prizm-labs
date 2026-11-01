#!/usr/bin/env python3
"""SI-137 (brief vocabulary map): every brief TYPE image-teardown's register
numbers has an entry in this register's `teardown_types`, every style id it
names is declared here, and style_for() returns them.

    /usr/bin/python3 components/briefs/tests/test_teardown_types.py

No key, no network. Both tools are called briefs.py, so each is loaded by
file under its own name — a module-name import could pick up the wrong one.
"""
import importlib.util, unittest
from pathlib import Path

COMPONENT = Path(__file__).resolve().parent.parent
TOOL = COMPONENT / "tools" / "briefs.py"
TEARDOWN_TOOL = COMPONENT.parent / "image-teardown" / "tools" / "briefs.py"


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B = load_file("briefs_register", TOOL)
T = load_file("image_teardown_briefs", TEARDOWN_TOOL)


class TeardownTypes(unittest.TestCase):

    def setUp(self):
        self.reg = B.load()
        self.map = self.reg["teardown_types"]
        self.ids = {b["id"] for b in self.reg["briefs"]}

    def test_every_teardown_type_has_a_map_entry(self):
        self.assertTrue(T.TYPES)
        for t in T.TYPES:
            self.assertIn(t, self.map, t)

    def test_no_entry_for_a_type_teardown_does_not_issue(self):
        extra = {k for k in self.map if not k.startswith("_")} - set(T.TYPES)
        self.assertEqual(extra, set())

    def test_each_entry_is_a_placement_or_a_reasoned_unmapped(self):
        for t in T.TYPES:
            v = self.map[t]
            if isinstance(v, list):
                self.assertTrue(v, t)
            else:
                self.assertEqual(set(v), {"unmapped"}, t)
                self.assertTrue(v["unmapped"].strip(), t)

    def test_every_mapped_id_exists_in_briefs(self):
        for t in T.TYPES:
            for sid in self.map[t] if isinstance(self.map[t], list) else []:
                self.assertIn(sid, self.ids, f"{t} -> {sid}")

    def test_style_for_returns_the_mapped_ids(self):
        for t in T.TYPES:
            v = self.map[t]
            self.assertEqual(B.style_for(t), v if isinstance(v, list) else [], t)
            self.assertEqual(B.style_for(t, self.reg), B.style_for(t), t)

    def test_style_for_refuses_a_word_that_is_not_a_type(self):
        for word in ("static--designer", "_what", "nope"):
            with self.assertRaises(KeyError):
                B.style_for(word)


if __name__ == "__main__":
    unittest.main()
