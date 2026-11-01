"""The swaps record (tools/swaps.py): the contract, what stage 3 writes, the backfill, and what a maker takes from it.
No model is called: the reader is a stub. No picture is made."""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
import swaps as SW  # noqa: E402  — puts the teardown's tools on the path for the two below
import paths as P, pictures as PIC  # noqa: E402  — the teardown's paths, and its picture step that reads the record

GOOD = {"product_in_frame": False, "product_where": None, "product_sides": [], "stays": ["the crop"],
        "swaps": [{"from": "the woman", "to": "Grandma Yai", "kind": "cast", "ref": "yai"},
                  {"from": "the caption", "to": "our words", "kind": "words", "ref": None}],
        "words": "set_on_top", "source": "stage3"}

STAGE3 = "**6. THE SWAPS RECORD**\n\n```json\n" + json.dumps({k: v for k, v in GOOD.items() if k != "source"}) + "\n```\n"
LAYER = {"layout": {"marks": [], "stickers": []}, "composited": [],
         "elements": [{"text": "HELLO", "top_pct": 74, "cap_pct": 2.5, "letterform": "caption-outline, hard black stroke"}]}
BRIEF = ("## 8 · Never on this ad\n- No product tube in frame. There is no place for one in this post.\n\n## 9 · Check\n\n"
         "```json\n" + json.dumps(LAYER) + "\n```\n")


def make_run(root, name="brand-b-batch-x", t3="", t6="", brand="brand-b"):
    run = Path(root) / name
    (run / "out").mkdir(parents=True)
    (run / "vars").mkdir()
    (run / "vars" / "brand_name.md").write_text(brand.upper())
    (run / "out" / "03-injection.md").write_text(t3)
    (run / "out" / "06-brief.md").write_text(t6)
    return run


def setUpModule():
    """The cast photo is media and never in git, so one banked character stands in for the real bank."""
    global _tmp, _patches
    _tmp = tempfile.TemporaryDirectory()
    photo = Path(_tmp.name) / "master.jpg"
    photo.write_bytes(b"jpg")
    _patches = [mock.patch.object(SW, "cast_ids", lambda brand: ["yai"] if brand == "brand-b" else []),
                mock.patch.object(SW, "cast_photo", lambda brand, cid: photo if cid == "yai" else None)]
    for p in _patches:
        p.start()


def tearDownModule():
    for p in _patches:
        p.stop()
    _tmp.cleanup()


class Contract(unittest.TestCase):
    def test_good_record_passes(self):
        self.assertEqual(SW.validate(GOOD), [])

    def test_product_yes_needs_where_and_sides(self):
        d = {**GOOD, "product_in_frame": True}
        self.assertTrue(any("product_where" in b for b in SW.validate(d)))
        self.assertTrue(any("product_sides" in b for b in SW.validate(d)))
        self.assertEqual(SW.validate({**d, "product_where": "in her hand", "product_sides": ["front"], "product_kit": "brilliance-face-scrub"}), [])
        self.assertTrue(SW.validate({**d, "product_where": "in her hand", "product_sides": ["front"]}))      # a kit, or listed unclear

    def test_product_no_carries_no_where_and_no_product_swap(self):
        bad = {**GOOD, "swaps": GOOD["swaps"] + [{"from": "x", "to": "our tube", "kind": "product", "ref": None}]}
        self.assertTrue(any("product swap while product_in_frame is false" in b for b in SW.validate(bad)))
        self.assertTrue(SW.validate({**GOOD, "product_where": "on a desk"}))

    def test_every_swap_has_a_kind_and_words_mode_and_source(self):
        self.assertTrue(SW.validate({**GOOD, "swaps": [{"from": "a", "to": "b", "kind": "magic", "ref": None}]}))
        self.assertTrue(SW.validate({**GOOD, "words": "maybe"}))
        self.assertTrue(SW.validate({**GOOD, "source": "guess"}))

    def test_unclear_is_null_with_a_reason_never_silent(self):
        self.assertTrue(SW.validate({**GOOD, "product_in_frame": None}))
        self.assertEqual(SW.validate({**GOOD, "product_in_frame": None, "unclear": ["text does not say"]}), [])


class StageThree(unittest.TestCase):
    def test_the_record_is_read_from_the_last_section_and_banks_resolve_refs(self):
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, t3="**5. CONFLICTS**\nnone\n\n" + STAGE3)
            rec, bad = SW.from_stage3(run)
            self.assertEqual(bad, [])
            self.assertEqual(rec["source"], "stage3")
            self.assertEqual(rec["swaps"][0]["ref"], "yai")             # a real cast id
            self.assertIsNone(rec["swaps"][1]["ref"])

    def test_a_made_up_cast_id_is_not_kept(self):
        d = {**GOOD, "swaps": [{"from": "the woman", "to": "Grandma Yai", "kind": "cast", "ref": "grandma-yai-72"}]}
        with tempfile.TemporaryDirectory() as t:
            run = make_run(t, t3="```json\n" + json.dumps(d) + "\n```")
            rec, _ = SW.from_stage3(run)
            self.assertEqual(rec["swaps"][0]["ref"], "yai")             # matched by name to the real id

    def test_a_made_up_person_is_drawn_never_a_cast_swap_with_no_id(self):
        d = {**GOOD, "swaps": [{"from": "the man", "to": "a generated man, mid-30s", "kind": "cast", "ref": None}]}
        with tempfile.TemporaryDirectory() as t:
            rec, bad = SW.from_stage3(make_run(t, t3="```json\n" + json.dumps(d) + "\n```"))
            self.assertEqual(bad, [])
            self.assertEqual(rec["swaps"][0]["kind"], "drawn")
        self.assertTrue(SW.validate({**GOOD, "swaps": [{"from": "a", "to": "b", "kind": "cast", "ref": None}]}))

    def test_the_kit_is_found_from_the_words_and_listed_unclear_when_none_leads(self):
        self.assertEqual(SW.kit_from_text("brand-a", "the FLEX brush head held against his neck"), "flex-face-brush")
        self.assertIsNone(SW.kit_from_text("brand-a", "a bottle in his hand"))

    def test_no_record_is_a_plain_problem(self):
        with tempfile.TemporaryDirectory() as d:
            rec, bad = SW.from_stage3(make_run(d, t3="five sections, no record"))
            self.assertIsNone(rec)
            self.assertIn("THE SWAPS RECORD", bad[0])

    def test_the_brief_must_carry_the_same_record(self):
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, t3=STAGE3, t6="```json\n" + json.dumps(GOOD) + "\n```")
            SW.write(run, SW.from_stage3(run)[0])
            self.assertTrue(SW.carried(run))
            (run / "out" / "06-brief.md").write_text("```json\n" + json.dumps({**GOOD, "product_in_frame": True}) + "\n```")
            self.assertFalse(SW.carried(run))


class Signals(unittest.TestCase):
    def test_no_product_sentence_settles_it_to_no(self):
        with tempfile.TemporaryDirectory() as d:
            f = SW.facts(make_run(d, t6=BRIEF))
            self.assertEqual(SW.product_call(f)[0], False)

    def test_a_product_reference_on_the_plate_settles_it_to_yes(self):
        plate = {"references": ["runs/ai-elements/brand-b/products/brilliance-face-scrub/front.png"]}
        with tempfile.TemporaryDirectory() as d:
            f = SW.facts(make_run(d, t6="```json\n" + json.dumps(plate) + "\n```"))
            self.assertEqual(SW.product_call(f)[0], True)

    def test_a_sentence_and_a_reference_that_disagree_are_left_to_the_reader(self):
        plate = {"references": ["runs/ai-elements/brand-b/products/brilliance-face-scrub/front.png"]}
        with tempfile.TemporaryDirectory() as d:
            f = SW.facts(make_run(d, t6=BRIEF + "```json\n" + json.dumps(plate) + "\n```"))
            self.assertIsNone(SW.product_call(f)[0])

    def test_a_no_product_inside_a_plate_negative_list_is_not_a_statement_about_the_ad(self):
        plate = {"references": [], "negatives": "no tube, no product, no logo"}
        with tempfile.TemporaryDirectory() as d:
            f = SW.facts(make_run(d, t6="```json\n" + json.dumps(plate) + "\n```"))
            self.assertEqual(f["no_product_sentences"], [])
            self.assertIsNone(SW.product_call(f)[0])

    def test_words_are_set_on_top_when_the_brief_has_a_type_layer_the_compositor_can_set(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(SW.words_call(SW.facts(make_run(d, t6=BRIEF)))[0], "set_on_top")

    def test_stickers_the_compositor_cannot_set_keep_the_words_drawn(self):
        layer = {**LAYER, "layout": {"marks": [], "stickers": [{"text": "60% OFF"}]}}
        with tempfile.TemporaryDirectory() as d:
            f = SW.facts(make_run(d, t6="```json\n" + json.dumps(layer) + "\n```"))
            self.assertEqual(SW.words_call(f)[0], "drawn")


class Backfill(unittest.TestCase):
    READER = json.dumps({"product_in_frame": True, "product_where": "wrongly guessed", "product_sides": ["front"],
                         "stays": ["the crop"], "words": "drawn",
                         "swaps": [{"from": "the woman", "to": "Grandma Yai", "kind": "cast", "ref": "yai"},
                                   {"from": "a prop", "to": "a jar", "kind": "library", "ref": "not-in-the-bank"}]})

    def test_plain_signals_win_over_the_reader_and_a_missing_library_prop_is_drawn(self):
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, t3="x", t6=BRIEF)
            rec, bad = SW.backfill(run, reader=lambda p, label: self.READER)
            self.assertEqual(bad, [])
            self.assertEqual(rec["source"], "backfill")
            self.assertIs(rec["product_in_frame"], False)               # the brief says no product
            self.assertEqual(rec["words"], "set_on_top")                # the brief has a type layer
            self.assertEqual([s["kind"] for s in rec["swaps"]], ["cast", "drawn"])
            self.assertTrue(rec["evidence"]["product"])
            self.assertEqual(SW.validate(rec), [])

    def test_what_the_text_does_not_settle_is_listed_as_unclear_never_guessed(self):
        reader = json.dumps({"product_in_frame": None, "product_evidence": "the text is silent", "stays": ["s"], "swaps": [], "words": "set_on_top"})
        with tempfile.TemporaryDirectory() as d:
            rec, bad = SW.backfill(make_run(d, t3="x", t6="no signals here"), reader=lambda p, label: reader)
            self.assertEqual(bad, [])
            self.assertIsNone(rec["product_in_frame"])
            self.assertEqual(rec["unclear"], ["the text is silent"])

    def test_the_reader_is_asked_once_and_remembered(self):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, t3="x", t6=BRIEF)
            SW.backfill(run, reader=lambda p, label: calls.append(1) or self.READER)
            (run / "out" / SW.FILE).unlink()
            SW.backfill(run, reader=lambda p, label: calls.append(1) or self.READER)
            self.assertEqual(len(calls), 1)

    def test_redo_rewrites_from_what_was_remembered_without_a_call(self):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, t3="x", t6=BRIEF)
            SW.backfill(run, reader=lambda p, label: calls.append(1) or self.READER)
            SW.backfill(run, reader=lambda p, label: calls.append(1) or self.READER, redo=True)
            self.assertEqual(len(calls), 1)

    def test_a_failed_read_is_a_listed_problem(self):
        def boom(p, label):
            raise RuntimeError("down")
        with tempfile.TemporaryDirectory() as d:
            rec, bad = SW.backfill(make_run(d, t3="x", t6=BRIEF), reader=boom)
            self.assertIsNone(rec)
            self.assertIn("down", bad[0])


class WhatAMakerTakes(unittest.TestCase):
    def test_a_cast_swap_sends_her_photo_and_a_product_no_sends_none(self):
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, t3="x", t6=BRIEF)
            SW.write(run, GOOD)
            pics = SW.pictures_for(run)
            self.assertEqual([p.name for p, _ in pics], ["master.jpg"])
            self.assertIn("Grandma Yai", pics[0][1])
            self.assertFalse(PIC.product_in_frame_for(run, "text that names FLEX", "FLEX"))     # the record says no

    def test_without_a_record_the_old_reading_of_the_text_still_answers(self):
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, t3="x")
            t = "**1. THE INJECTED FRAME**\nthe Brilliance in her hand\n**2. THE SUBJECT**\n"
            self.assertTrue(PIC.product_in_frame_for(run, t, "Brilliance"))

    def test_the_picture_text_says_no_words_when_they_are_set_on_top(self):
        with tempfile.TemporaryDirectory() as d:
            run = make_run(d, t3="x")
            (run / "assets").mkdir()
            SW.write(run, GOOD)
            text, _ = PIC.picture_inputs(run, "the woman becomes Yai", "", True)
            self.assertIn("NO WORDS IN THE PICTURE", text)
            self.assertNotIn("THE WORDS ON THE PICTURE", text)
            drawn, _ = PIC.picture_inputs(run, "the woman becomes Yai", "Caption: HELLO", True)   # a person chose to draw them
            self.assertIn("THE WORDS ON THE PICTURE", drawn)
            self.assertNotIn("NO WORDS IN THE PICTURE", drawn)

    def test_the_stage_prompts_carry_the_record(self):
        s3 = (P.WRITING_PROMPTS / "stage3-image-injection-v6-damon.md").read_text()
        self.assertIn("6. THE SWAPS RECORD", s3)
        self.assertIn("{cast_bank}", s3)
        self.assertIn("THE SWAPS RECORD", (P.WRITING_PROMPTS / "stage6-image-brief-v10-damon.md").read_text())


if __name__ == "__main__":
    unittest.main()
