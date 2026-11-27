#!/usr/bin/env python3
"""QB-9 (editor statics): the content-queue page's Done (45) through POST /act. The kit turns it into exactly
`statics.py done <key> --by <its own person>`, takes no words, refuses a key that is not a hand-off key and a table
entry that names any other verb, and serves the cached approved pictures under runs/creative-queue/statics/ only.
Nothing runs: build() returns the argv the kit would run.

    /usr/bin/python3 components/page-features/kit/test_qb9_statics_button.py
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402

REAL = serve.ROOT
KEY = "brand_a_flex-face-brush_brief-0296"


class Done(unittest.TestCase):
    def act(self, person="editor"):
        return serve.Act("content-queue", REAL, person)

    def test_the_real_table_names_done_on_statics(self):
        self.assertEqual(serve.direct_table("content-queue", REAL)["45"], {"kind": "quick", "run": "statics", "verb": "done"})

    def test_done_is_one_statics_command_as_the_kits_person(self):
        argv, line = self.act().build({"family": "content-queue", "n": 45, "item": KEY})
        self.assertEqual(argv[1:], [os.path.join(REAL, "components/creative-queue/statics.py"), "done", KEY, "--by", "editor"])
        self.assertIsNone(line)
        argv, _ = self.act().build({"family": "content-queue", "n": 45, "item": KEY, "by": "email_lead"})
        self.assertEqual(argv[-1], "editor", "a body naming someone else is ignored")

    def test_refused_before_anything_runs(self):
        for body, code in (({"item": KEY, "value": "hi"}, 400), ({"item": "nounderscore"}, 400),
                           ({"item": "a_b..c"}, 400), ({"item": "../x"}, 400), ({"item": KEY, "field": "who"}, 400)):
            b = dict(body, family="content-queue", n=45)
            with self.assertRaises(serve.Refused) as e:
                self.act().build(b)
            self.assertEqual(e.exception.code, code, body)
        with self.assertRaises(serve.Refused) as e:
            serve.Act("content-queue", REAL, None, "no person").build({"family": "content-queue", "n": 45, "item": KEY})
        self.assertEqual(e.exception.code, 403)

    def test_another_verb_is_not_direct(self):
        a = self.act()
        real = serve.direct_table
        try:
            serve.direct_table = lambda fam, root=REAL: {"45": {"kind": "quick", "run": "statics", "verb": "list"}}
            with self.assertRaises(serve.Refused) as e:
                a.build({"family": "content-queue", "n": 45, "item": KEY})
            self.assertEqual(e.exception.code, 403)
        finally:
            serve.direct_table = real

    def test_pictures_are_served_from_the_statics_cache_only(self):
        decl = serve.sources("content-queue", REAL)
        self.assertEqual(serve.runs_prefixes(decl), ["creative-queue/statics/"])
        self.assertEqual(decl["statics"]["argv"], ["components/creative-queue/statics.py", "list"])
        self.assertIn("runs/creative-queue/statics/*/*/done.json", decl["statics"]["watch"])
        self.assertNotIn("statics", json.dumps(decl["queue"]["argv"]), "the queue source never waits on Drive")

    def test_features_42_to_46(self):
        with open(os.path.join(REAL, "platform/views/viewers/_templates/content-queue.features.json"), encoding="utf-8") as fh:
            got = {f["n"]: (f["name"], f["kind"]) for f in json.load(fh)["features"] if 42 <= f["n"] <= 46}   # 47+: QB-11 (creator view)
        self.assertEqual(got, {42: ("A static waiting for editor", "rule"), 43: ("The approved picture", "media"),
                               44: ("The hand-off on Drive", "data"), 45: ("Done: send to email_lead", "action"),
                               46: ("Files back", "data")})


if __name__ == "__main__":
    unittest.main()
