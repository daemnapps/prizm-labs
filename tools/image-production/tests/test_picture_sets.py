"""picture_sets.print_prompt: the print's words keep the product's label, bar other writing, and let the set's own
signage through (the moment's name on a real prop, 2026-10-30)."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.append(str(Path(__file__).resolve().parents[1]))
import picture_sets as PS  # noqa: E402

BASE = {"shot": "a product on a plinth", "light": "one hard key from the top right",
        "objects": ["the plinth is matte black stone"], "product": "a green tube", "size_cm": 15}


class PrintPrompt(unittest.TestCase):
    def test_no_signage_bars_every_other_word(self):
        p = PS.print_prompt(dict(BASE))
        self.assertIn("No writing anywhere except the product's own label.", p)
        self.assertNotIn("printed words", p)

    def test_signage_is_printed_on_its_prop_and_allowed(self):
        p = PS.print_prompt(dict(BASE, signage=[{"prop": "desk flag", "words": "BLACK FRIDAY"}]))
        self.assertIn('desk flag carries the printed words "BLACK FRIDAY"', p)
        self.assertIn("except the product's own label and the words named on the props above.", p)

    def test_a_sign_without_words_is_ignored(self):
        p = PS.print_prompt(dict(BASE, signage=[{"prop": "desk flag", "words": ""}]))
        self.assertIn("No writing anywhere except the product's own label.", p)


class Signage(unittest.TestCase):
    """The words on a prop travel from the brief or the swaps into the set record and the print's words."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="signage-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for p in (mock.patch.object(PS.P, "repo", lambda *a: self.tmp),
                  mock.patch.object(PS, "home", lambda brand, name: self.tmp / "sets" / name),
                  mock.patch.object(PS, "_product", lambda brand, slug: {"what": "a green tube", "size_cm": 15})):
            p.start()
            self.addCleanup(p.stop)
        self.out = self.tmp / "runs" / "image-teardown" / "b" / "r1" / "out"
        self.out.mkdir(parents=True)

    def brief(self, props):
        block = {"set": {"camera": {"lens_mm": 26, "height_cm": 14, "angle": "overhead"},
                         "light": [{"from": "upper left", "hardness": "soft"}], "surfaces": [{"what": "couch", "material": "grey cloth"}],
                         "props": props, "product": {"kit": "tube"}, "print": "worn cloth, fine grain"}}
        (self.out / "06-brief.md").write_text('```json\n{"layout": {}}\n```\n```json\n' + json.dumps(block) + "\n```\n")

    def swaps(self, *rows):
        (self.out / "swaps.json").write_text(json.dumps({"swaps": list(rows), "product_kit": "tube"}))

    def test_the_brief_block_gives_the_words_and_the_prop(self):
        self.brief([{"what": "desk flag", "signage": "BLACK FRIDAY"}, {"what": "tray", "signage": None}])
        self.assertEqual(PS.signage_for("b", "r1"), [{"prop": "desk flag", "words": "BLACK FRIDAY"}])

    def test_a_brief_block_with_no_signage_beats_the_swap_text(self):
        self.brief([{"what": "tray", "signage": None}])
        self.swaps({"kind": "drawn", "to": "a flag printed OLD WORDS"})
        self.assertEqual(PS.signage_for("b", "r1"), [])

    def test_an_older_run_gives_them_from_its_swap_row(self):
        self.swaps({"kind": "drawn", "to": "a small black cloth desk flag on the same dowel, printed BLACK FRIDAY in big plain white letters"},
                   {"kind": "words", "to": "BLACK FRIDAY / SALE"})
        self.assertEqual(PS.signage_for("b", "r1"), [{"prop": "small black cloth desk flag", "words": "BLACK FRIDAY"}])

    def test_no_lettering_and_lowercase_are_not_signage(self):
        self.swaps({"kind": "drawn", "to": "a pennant, matte, no lettering and no logo"},
                   {"kind": "drawn", "to": "a tag printed in soft ink"})
        self.assertEqual(PS.signage_for("b", "r1"), [])

    def test_stage_three_art_direction_is_the_last_place_read(self):
        self.swaps({"kind": "drawn", "to": "a plain stone"})
        (self.out / "03-injection.md").write_text("**3. THE ART DIRECTION**\n- a shop sign on the wall, reading LAST CALL\n\n**4. NEXT**\n- a tag printed NOPE\n")
        self.assertEqual(PS.signage_for("b", "r1"), [{"prop": "shop sign", "words": "LAST CALL"}])

    def test_the_first_print_carries_the_words_and_allows_them(self):
        self.brief([{"what": "desk flag", "material": "black cloth", "signage": "BLACK FRIDAY"}])
        p = PS.first_print("b", "r1")["print_words"]
        self.assertIn('desk flag carries the printed words "BLACK FRIDAY"', p)
        self.assertIn("and the words named on the props above", p)
        for words in ("26 mm", "upper left, soft", "couch, grey cloth", "worn cloth, fine grain", "a green tube"):
            self.assertIn(words, p)

    def test_filing_a_print_with_its_run_records_the_words_in_the_set(self):
        self.brief([{"what": "desk flag", "signage": "SALE"}])
        src = self.tmp / "made.png"
        src.write_bytes(b"y")
        PS.put("b", "hero", printed=src, note="kept: first", run="r1")
        r = PS.record("b", "hero")
        self.assertEqual((r["runs"], r["signage"]), (["r1"], [{"prop": "desk flag", "words": "SALE"}]))

    def test_a_variation_of_a_set_with_none_recorded_finds_them_itself(self):
        self.brief([{"what": "desk flag", "signage": "SALE"}])
        d = PS.home("b", "hero")
        d.mkdir(parents=True)
        (d / "print-v1.png").write_bytes(b"x")
        (d / "set.json").write_text(json.dumps({"runs": ["r1"], "prints": [{"file": "print-v1.png", "note": "kept"}]}))
        q = PS.change_request("b", PS.kept("b", "r1"), "v1", {"picture": "a 12 cm tray"}, {"run": "r1"})
        self.assertIn('desk flag carries the printed words "SALE"', q["print_words"])
        self.assertEqual(q["signage"], [{"prop": "desk flag", "words": "SALE"}])
        self.assertNotIn("no signage", " ".join(q["flags"]))

    def test_fill_writes_only_sets_that_lack_them(self):
        self.brief([{"what": "desk flag", "signage": "SALE"}])
        for name, extra in (("a", {}), ("b", {"signage": [{"prop": "sign", "words": "KEEP"}]})):
            d = PS.home("b", name)
            d.mkdir(parents=True)
            (d / "set.json").write_text(json.dumps({"runs": ["r1"], **extra}))
        self.assertEqual(PS.fill_signage("b"), ["a"])
        self.assertEqual(PS.record("b", "b")["signage"], [{"prop": "sign", "words": "KEEP"}])


RUN = "brand-batch-1"
BRIEF = {"run": RUN, "swap_list": {"swaps": [
    {"from": "the old block", "to": "a slab of grey stone", "kind": "drawn"},
    {"from": "the old words", "to": "our words", "kind": "words"}]}}
ONE = "a 12 cm brass tray under the product, on the slab"


class SetChange(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sets-test-"))
        for p in (mock.patch.object(PS, "home", lambda brand, name: self.tmp / "sets" / name),
                  mock.patch.object(PS.P, "rel", lambda p, *a: Path(p).name)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        d = PS.home("b", "hero")
        d.mkdir(parents=True)
        (d / "print-v1.png").write_bytes(b"x")
        (d / "print-v2.png").write_bytes(b"x")
        (d / "set.json").write_text(json.dumps({
            "project": {"id": "p1", "collection": "SET_hero"}, "camera": "85 mm, level", "light": "one hard key", "runs": [RUN],
            "signage": [{"prop": "desk flag", "words": "SALE"}],
            "prints": [{"file": "print-v1.png", "note": "kept: first"}, {"file": "print-v2.png", "note": "too flat"}]}))

    def found(self):
        return PS.kept("b", RUN)

    def test_kept_takes_the_newest_kept_print_of_the_run(self):
        self.assertEqual(self.found()["print"].name, "print-v1.png")
        self.assertEqual(self.found()["set"], "hero")
        self.assertIsNone(PS.kept("b", "another-run"))

    def test_a_run_whose_prints_are_not_kept_has_no_set(self):
        f = PS.home("b", "hero") / "set.json"
        d = json.loads(f.read_text())
        d["prints"][0]["note"] = "rejected"
        f.write_text(json.dumps(d))
        self.assertIsNone(self.found())

    def test_the_request_carries_the_change_and_its_print_words(self):
        q = PS.change_request("b", self.found(), "v1", {"picture": ONE + "."}, BRIEF)
        self.assertEqual((q["set"], q["variation_of"], q["run"]), ("hero--v1", "hero", RUN))
        self.assertEqual(q["change"], ONE)
        self.assertEqual(q["credits"], PS.PRINT_CREDITS)
        self.assertEqual((q["collection"], q["base_collection"]), ("SET_hero_v1", "SET_hero"))
        for words in (ONE, "a slab of grey stone", "85 mm, level", "one hard key",
                      'desk flag carries the printed words "SALE"'):
            self.assertIn(words, q["print_words"])
        self.assertNotIn("our words", q["print_words"])       # the words are set on top, never printed
        self.assertNotIn("no real size", " ".join(q["flags"]))

    def test_a_person_row_lets_the_print_show_a_person(self):
        q = PS.change_request("b", self.found(), "v1", {"picture": ONE, "people": "made-up"}, BRIEF)
        self.assertNotIn("No people", q["print_words"])

    def test_a_row_with_no_size_and_a_set_with_no_signage_are_flagged(self):
        f = self.found()
        f["record"] = {k: v for k, v in f["record"].items() if k != "signage"}
        q = PS.change_request("b", f, "v1", {"picture": "a brass tray under the product"}, BRIEF)
        said = " ".join(q["flags"])
        self.assertIn("no real size", said)
        self.assertIn("no signage", said)

    def test_a_set_with_no_camera_or_light_still_builds(self):
        f = self.found()
        f["record"] = {"prints": f["record"]["prints"], "project": "p1"}
        self.assertIn(ONE, PS.change_request("b", f, "v1", {"picture": ONE}, BRIEF)["print_words"])

    def test_swap_rows_stand_for_the_change_when_there_is_no_sentence(self):
        self.assertEqual(PS.change_words({"swap": [{"from": "a", "to": "b"}]}), "a becomes b")

    def test_the_print_files_as_its_own_set_and_never_takes_the_runs_place(self):
        q = PS.change_request("b", self.found(), "v1", {"picture": ONE}, BRIEF)
        src = self.tmp / "made.png"
        src.write_bytes(b"y")
        self.assertIsNone(PS.kept_change("b", "hero", "v1", ONE))
        PS.put_change(q, printed=src, note="kept: tray in")
        got = PS.kept_change("b", "hero", "v1", ONE)
        self.assertEqual(got.name, "print-v1.png")
        self.assertEqual(self.found()["set"], "hero")
        self.assertNotIn("runs", PS.record("b", "hero--v1"))

    def test_a_print_for_other_words_is_not_this_rows_print(self):
        q = PS.change_request("b", self.found(), "v1", {"picture": ONE}, BRIEF)
        src = self.tmp / "made.png"
        src.write_bytes(b"y")
        PS.put_change(q, printed=src, note="kept: tray in")
        self.assertIsNone(PS.kept_change("b", "hero", "v1", "a different change"))

    def test_a_print_not_marked_kept_is_not_used(self):
        q = PS.change_request("b", self.found(), "v1", {"picture": ONE}, BRIEF)
        src = self.tmp / "made.png"
        src.write_bytes(b"y")
        PS.put_change(q, printed=src, note="too flat")
        self.assertIsNone(PS.kept_change("b", "hero", "v1", ONE))


class Creative(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "03-injection.md").write_text("**THE CONCEPT:** A small thing, staged big.\n\n"
                                                  "- `intensity: swipe 0 → ours 3 (high)`: bright.\n- `humor: swipe 0 → ours 2 (playful)`: dry.\n")

    def test_the_brief_concept_and_picture_dials_reach_the_print(self):
        with mock.patch.object(PS, "run_home", return_value=self.tmp):
            lines = PS.creative("b", "r")
        self.assertEqual(lines[0], "The concept of this picture: A small thing, staged big.")
        self.assertEqual(len(lines), 2)   # intensity sends a picture line, humor is a writing dial and sends none
        self.assertIn(lines[1], PS.print_prompt(dict(BASE, creative=lines)))

    def test_a_run_with_no_brief_adds_nothing(self):
        with mock.patch.object(PS, "run_home", return_value=None):
            self.assertEqual(PS.creative("b", "r"), [])


if __name__ == "__main__":
    unittest.main()
