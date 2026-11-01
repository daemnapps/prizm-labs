"""image-edit — the `product` fix on a resting product (fixes-v4).

A product on a plinth, shelf or sink has no hand in frame. Under fixes-v3 the
fix said "in the hand" and its check demanded one, so the judge failed it with
"There is no hand in the image to judge the size against" and the picture was
held (runs/image-edit/brand-a/brand-a-nov-02--gift-buyer-n1-label, 2026-10-29).

The judge here is a stand-in that answers as that real verdict did: a test that
needs a hand fails on a picture with none, unless the test itself says what to
do when no hand is there. No key, no network, nothing spent.

    python3 tools/image-edit/tests/test_resting_product.py
"""
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_image_edit import (Base, RE, StubLibrary, judge_saying, setUpModule,  # noqa: F401,E402
                             stub_transport, tearDownModule)
from image_edit import engine as E  # noqa: E402

V3 = Path(__file__).resolve().parent.parent / "library" / "fixes-v3-damon.json"


def judge_of_a_picture_with_no_hand(prompt, paths, entry):
    tests = re.findall(r"^(\d+)\. (.+)$", prompt, re.M)
    results = []
    for n, text in tests:
        needs_a_hand = re.search(r"\bhand\b", text, re.I) and "no hand" not in text.lower()
        results.append({"test": int(n), "verdict": "FAIL" if needs_a_hand else "PASS",
                        "evidence": "There is no hand in the image to judge the size against."
                        if needs_a_hand else "stub"})
    return json.dumps({"results": results})


class TestRestingProduct(Base):
    def edit(self):
        return RE.edit(self.req(fix="product", product="widget"), transport=stub_transport(self.calls),
                       judge_caller=judge_saying("PASS"), compare_caller=judge_of_a_picture_with_no_hand,
                       mirror=False, library=StubLibrary())

    def test_a_resting_product_is_not_held(self):
        r = self.edit()
        self.assertEqual(r["state"], "filed", r.get("rejected"))

    def test_the_old_row_held_it_which_is_the_fault(self):
        old = {x["id"]: x for x in json.loads(V3.read_text())["fixes"]}
        with mock.patch.object(E, "fixes", lambda folder=None: (old, V3)):
            r = self.edit()
        self.assertEqual(r["state"], "held")
        self.assertIn("no hand in the image", r["rejected"][0]["fails"][0])

    def test_the_request_no_longer_says_it_is_in_a_hand(self):
        asked = RE.resolve(self.req(fix="product", product="widget"))["asked"]
        self.assertNotIn("in the hand,", asked)
        self.assertIn("where it already sits", asked)

    def test_a_held_product_still_gets_the_size_test(self):
        checks = RE.resolve(self.req(fix="product", product="widget"))["checks"]
        self.assertTrue(any("never larger than the hand" in c for c in checks))


if __name__ == "__main__":
    unittest.main()
