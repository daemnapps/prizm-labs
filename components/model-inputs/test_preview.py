"""The preflight: assembled from real briefs, gated on rulebook errors, a new job plugs in by registry. No network, no spend."""
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import preview as PV  # noqa: E402

# the runs' own swap lists (out/swaps.json) come from the teardown; these sample lists stand in for them in tests
CHURCH = str(HERE / "fixtures" / "church-after-fight-swaps.json")
SPOTS = str(HERE / "fixtures" / "three-spots-swaps.json")
PIC = {"brand": "brand-b", "run": "brand-b-batch-grandma-church-after-fight", "product": "brilliance-face-scrub", "swap_file": CHURCH}
THREE = {"brand": "brand-b", "run": "brand-b-batch-grandma-dark-spots-not-growing-old", "product": "", "product_slug": "brilliance-face-scrub",
         "swap_file": SPOTS}
CLIP = {"run": "brand-b/yai-sun-spots-back", "call": "G01-C1"}


class Preview(unittest.TestCase):
    def test_picture_prompt_comes_from_the_brief_and_is_numbered(self):
        r = PV.preview("pictures.generate", PIC, quote=False)
        self.assertIn("THE SWAPS:", r["prompt"])
        self.assertIn("Grandma Yai", r["prompt"])
        self.assertEqual([i["n"] for i in r["inputs"]], [1, 2, 3, 4, 5])   # the product's casting sheet joined (2026-10-27)
        self.assertTrue(any(str(i.get("path", "")).endswith("sheets/headshot.jpg") for i in r["inputs"]))   # her ONE face (2026-10-28)
        self.assertIn("THE PEOPLE ARE REAL PEOPLE", r["prompt"])
        self.assertTrue(any("casting sheet" in str(i["role"]) for i in r["inputs"]))
        self.assertTrue(r["ok"])
        self.assertEqual(r["model"], "gpt-image-2.5")
        self.assertTrue(r["ladder"])

    def test_editing_a_field_changes_the_prompt(self):
        a = PV.preview("pictures.generate", PIC, quote=False)["prompt"]
        b = PV.preview("pictures.generate", {**PIC, "note": "make the sky orange"}, quote=False)["prompt"]
        self.assertIn("make the sky orange", b)
        self.assertNotIn("make the sky orange", a)

    def test_opening_direction_replaces_inherited_gesture(self):
        swaps = json.loads(Path(CHURCH).read_text())
        swaps.update(from_brief=True, feeling={"emotion": "calm", "face": "old face", "gesture": "old gesture"})
        with patch.object(PV, "swap_list", return_value=swaps):
            a = PV.preview("pictures.generate", {**PIC, "shot_direction": {
                "emotion": "surprise", "face": "deadpan at lens",
                "gesture": "hold a magnifier over the teaching model"}}, quote=False)["prompt"]
        feeling = a.split("THE FEELING:", 1)[1].split("\n", 1)[0]
        self.assertIn("hold a magnifier over the teaching model", feeling)
        self.assertIn("deadpan at lens", feeling)
        self.assertNotIn("old gesture", feeling)

    def test_clip_prompt_is_the_chains_own(self):
        r = PV.preview("clips.seedance", CLIP, quote=False)
        self.assertTrue(r["prompt"].startswith("Image 1 is the first frame"))
        self.assertEqual(r["model"], "seedance-2.5")
        self.assertEqual(r["settings"]["aspect"], "9:16")
        e = PV.preview("clips.seedance", {**CLIP, "face": "eyes down, calm"}, quote=False)["prompt"]
        self.assertIn("eyes down, calm", e)

    def test_a_rulebook_error_stops_and_exits_nonzero(self):
        PV.register("pictures.generate", lambda b: {**PV.build_picture(PIC), "inputs": [{"n": i, "role": "x", "path": "x.png"} for i in range(1, 40)]})
        try:
            r = PV.preview("pictures.generate", PIC, quote=False)
            self.assertFalse(r["ok"])
            self.assertGreaterEqual(r["errors"], 1)
        finally:
            PV.register("pictures.generate", PV.build_picture)

    def test_a_new_job_plugs_in_without_touching_preview(self):
        self.assertIn("pictures.generate", PV.jobs())
        with self.assertRaises(KeyError):
            PV.builder_for("clips.nothing")

    def test_cli_exit_codes(self):
        self.assertEqual(PV.main(["pictures.generate", json.dumps(PIC), "--no-quote"]), 0)
        self.assertEqual(PV.main(["clips.nothing", "{}", "--no-quote"]), 2)


class Swaps(unittest.TestCase):
    # THREE reads the sample list; test_the_real_three_spots_list reads the teardown's own when it is there
    """PSH-11 (inputs from the swaps): the pictures that go in are worked out from the run's swap list."""

    def spots(self, **kw):
        return PV.preview("pictures.generate", {**THREE, **kw}, quote=False)

    def tmp_list(self, **change):
        import tempfile
        d = {**json.loads(Path(SPOTS).read_text()), **change}
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(d, f)
        f.close()
        return f.name

    def test_no_swap_list_is_missing_never_guessed(self):
        r = PV.preview("pictures.generate", {k: v for k, v in THREE.items() if k != "swap_file"}
                       | {"swap_file": "/nonexistent/swaps.json"}, quote=False)
        rows = {x["id"]: x for x in r["sheet"]["rows"]}
        for k in ("swap_list", "product_in_frame", "swaps", "stays", "words_mode"):
            self.assertEqual(rows[k]["state"], PV.MISSING, k)
        self.assertFalse(r["ok"])

    def test_three_spots_sends_the_swipe_and_the_cast_photo_and_no_product(self):
        r = self.spots()
        self.assertTrue(r["ok"], [f["say"] for f in r["findings"] if f["level"] == "error"])
        paths = [i["path"] for i in r["inputs"]]
        self.assertTrue(paths[0].endswith("assets/source.jpg"))
        # the cast member's face reference: her plain headshot when she has one, else her master photo (lessons L-11)
        d = Path(paths[1]).parent if paths[1].endswith("master.jpg") else Path(paths[1]).parent.parent
        want = "casting/yai/sheets/headshot.jpg" if (d / "sheets" / "headshot.jpg").is_file() else "casting/yai/master.jpg"
        self.assertTrue(paths[1].endswith(want), paths[1])
        self.assertFalse([p for p in paths if "product" in p or "/kits/" in p])
        self.assertNotIn("THE PRODUCT", r["prompt"])
        rows = {x["id"]: x for x in r["sheet"]["rows"]}
        self.assertTrue(rows["product_in_frame"]["value"].startswith("no: No product tube in frame"), rows["product_in_frame"]["value"])
        self.assertEqual(rows["product_kit"]["state"], PV.NA)

    def test_a_cast_swap_names_the_cast_member_and_keeps_the_face(self):
        p = self.spots()["prompt"]
        people = p.split("THE PEOPLE\n")[1].split("\n\n")[0]
        self.assertIn("The person in IMAGE 2 is Grandma Yai", people)
        self.assertIn("face exactly", people)
        self.assertNotIn("LOOKALIKE", p)
        self.assertNotIn("lookalike", p.lower())

    def test_words_set_on_top_ask_for_no_writing_and_drop_the_words_block(self):
        r = self.spots()
        self.assertNotIn("THE WORDS ON THE PICTURE", r["prompt"])
        self.assertTrue("No writing anywhere in the picture" in r["prompt"] or "NO WORDS IN THE PICTURE" in r["prompt"])
        self.assertEqual(r["prompt"].count("set on afterwards") + r["prompt"].count("set on top afterwards"), 1)
        self.assertNotIn("The caption words swap", r["prompt"])
        self.assertEqual(r["fields"]["words_mode"], "set on top after")
        self.assertTrue(r["fields"]["words_plain"])              # the exact words still show on the Bench

    def test_drawn_words_keep_the_words_block_and_product_yes_sends_only_named_sides(self):
        r = PV.preview("pictures.generate", PIC, quote=False)
        self.assertIn("THE WORDS ON THE PICTURE", r["prompt"])
        self.assertIn("THE PRODUCT", r["prompt"])
        prod = [i for i in r["inputs"] if "BRILLIANCE" in str(i["role"]).upper()]
        sheet = [i for i in prod if "casting sheet" in str(i["role"])]
        sides = [i for i in prod if i not in sheet]
        self.assertEqual(len(sheet), 1)                          # every side, always (the product casting sheet, 2026-10-27)
        self.assertEqual(len(sides), 1)                          # and only the named side beyond it
        self.assertIn("FRONT", sides[0]["role"])

    def test_a_cast_swap_with_no_photo_on_file_stops_before_spend(self):
        f = self.tmp_list(swaps=[{"from": "The woman", "to": "Nobody Yet", "kind": "cast", "ref": "no-such-person"}])
        r = self.spots(swap_file=f)
        self.assertFalse(r["ok"])
        self.assertTrue([x for x in r["findings"] if x.get("var") == "swaps" and "not on file" in x["say"]])

    def test_a_library_swap_adds_its_photo(self):
        lib = str(PV.cast_photo("brand-b", "yai"))             # any real photo on file stands in for a library prop
        f = self.tmp_list(swaps=[{"from": "The wall", "to": "our kitchen set", "kind": "library", "ref": lib}])
        r = self.spots(swap_file=f)
        self.assertIn(lib, [i["path"] for i in r["inputs"]])
        self.assertTrue(r["ok"], [x["say"] for x in r["findings"] if x["level"] == "error"])

    def test_the_real_three_spots_list(self):
        run = {k: v for k, v in THREE.items() if k != "swap_file"}
        if not (PV._lane_run("brand-b", run["run"]) / "out" / "swaps.json").is_file():
            self.skipTest("the teardown has not written this run's swap list yet")
        r = PV.preview("pictures.generate", run, quote=False)
        self.assertNotIn("THE PRODUCT", r["prompt"])
        self.assertIn("The person in IMAGE 2 is Grandma Yai", r["prompt"])
        self.assertTrue({x["id"]: x for x in r["sheet"]["rows"]}["product_in_frame"]["value"].startswith("no: No product tube"))

    def test_words_on_top_carry_our_words_into_the_type_layer(self):
        b = {k: v for k, v in THREE.items() if k != "swap_file"}
        if not (PV.COMP / "image-writing" / "tools" / "swaps.py").is_file():
            self.skipTest("the teardown's swaps.py is not here")
        s = PV.build_picture(b)["send"]
        if not s.get("type_layer"):
            self.skipTest("this run's brief has no type layer")
        ours = PV.build_picture(b)["fields"]["words_plain"]
        self.assertEqual([e["text"] for e in s["type_layer"]["elements"]][:len(ours)], ours[:len(s["type_layer"]["elements"])])
        e = PV.build_picture({**b, "our_copy": ["NEW / WORDS"]})["send"]["type_layer"]["elements"][0]["text"]
        self.assertEqual(e, "NEW\nWORDS")
        self.assertIsNone(PV.build_picture({**b, "words_mode": "drawn"})["send"]["type_layer"])

    def test_a_drawn_swap_needs_no_picture(self):
        rows = PV.swap_rows("brand-b", json.loads(Path(SPOTS).read_text()))
        self.assertEqual([r["needs"] for r in rows if r["kind"] == "drawn"], ["none: drawn from words"] * 3)


class Ready(unittest.TestCase):
    """Step 1's badge: ready or not from the sheet gate, before anyone opens a brief."""

    def test_a_complete_brief_is_ready_and_an_incomplete_one_names_its_first_gap(self):
        import prompt_bench as PB
        r = PB.readiness("brand-b", "brand-b-batch-grandma-dark-spots-not-growing-old", "brilliance-face-scrub")
        self.assertEqual(r, {"ready": True, "missing": 0, "first": ""})
        bad = PB.readiness("brand-a", "brand-a-batch-bald-problem-54865677", "")
        self.assertFalse(bad["ready"])
        self.assertTrue(bad["first"])
        self.assertIs(PB.readiness("brand-a", "brand-a-batch-bald-problem-54865677", ""), bad)   # cached

    def test_the_product_kit_is_read_from_the_brief_title(self):
        import prompt_bench as PB
        kits = ["nova-charging-case", "nova-face-brush", "war-face-wash"]
        self.assertEqual(PB._product_of("# BRIEF · BRAND-A · NOVA™ Pro Vibrating Face Brush · Bathroom review", kits), "nova-face-brush")
        self.assertEqual(PB._product_of("# BRIEF · BRAND-A · NOVA · Neck Detail", kits, {"nova-face-brush": ["nova"]}), "nova-face-brush")
        # a short name only counts in the product slot, never in the title
        self.assertEqual(PB._product_of("# BRIEF · BRAND-A · CRUSH · The war on bumps", kits, {"war-face-wash": ["war"]}), "")

    def test_the_words_row_reads_as_the_words(self):
        r = PV.preview("pictures.generate", {k: v for k, v in THREE.items() if k != "swap_file"}, quote=False)
        v = {x["id"]: x for x in r["sheet"]["rows"]}["words"]["value"]
        self.assertNotIn("`", v)
        self.assertNotIn("sits", v)
        self.assertIn("\n", v)


class Sheet(unittest.TestCase):
    """The picture sheet: every variable filled or not applicable with an allowed reason before anything is made."""

    def full(self):
        r = PV.fill_defaults({"brief": PIC})
        r["sheet"][PV.APPROVAL] = {"state": "filled", "value": "test", "source": "person"}
        return r

    def test_a_complete_sheet_passes(self):
        self.assertEqual(PV.validate(self.full()), [])

    def test_a_blank_fails_by_name(self):
        r = self.full()
        r["sheet"]["angle"] = {"state": "missing"}
        self.assertIn("The angle", [p["name"] for p in PV.validate(r)])
        with self.assertRaises(ValueError):
            PV.gate(r)

    def test_not_applicable_without_an_allowed_reason_fails(self):
        r = self.full()
        r["sheet"]["offer"] = {"state": "not_applicable"}
        self.assertIn("The offer", [p["name"] for p in PV.validate(r)])

    def test_not_applicable_on_a_guard_required_dial_fails(self):
        r = self.full()
        r["sheet"]["dial.absurdity"] = {"state": "not_applicable", "reason": "not used in a still picture"}
        self.assertIn("Absurdity", [p["name"] for p in PV.validate(r)])

    def test_a_floor_dial_under_the_floor_fails(self):
        r = self.full()
        r["sheet"]["dial.stopping_power"] = {"state": "filled", "value": 1, "source": "person"}
        self.assertTrue(any("floor" in p["say"] for p in PV.validate(r)))

    def test_preview_refuses_a_blank_by_name(self):
        r = PV.preview("pictures.generate", {**PIC, "product": ""}, quote=False)
        self.assertFalse(r["ok"])
        self.assertTrue(any(f["id"] == "sheet" and f["say"].startswith("Product") for f in r["findings"]))

    def test_an_unapproved_made_picture_cannot_go_in(self):
        import tempfile
        d = REPO_RUNS / "image-production" / "_test-unapproved"
        d.mkdir(parents=True, exist_ok=True)
        f = d / "made.png"
        f.write_bytes(Path(PV.build_picture(PIC)["choices"][1]["path"]).read_bytes())
        try:
            r = PV.fill_defaults({"brief": {**PIC, "added": [{"path": str(f), "label": "our earlier picture"}]}})
            self.assertTrue(any("no chosen record" in p["say"] for p in PV.validate(r)))
            f.with_suffix(".recipe.json").write_text(json.dumps({"chosen": True, "below_criteria": ["the judge saw a drawn label"]}))
            r = PV.fill_defaults({"brief": {**PIC, "added": [{"path": str(f), "label": "our earlier picture"}]}})
            self.assertFalse(any("no chosen record" in p["say"] for p in PV.validate(r)))
            self.assertTrue(any("below criteria" in p["say"] for p in PV.flags(r)))     # amber, travels, never stops
        finally:
            for x in d.glob("*"):
                x.unlink()
            d.rmdir()

    def test_a_pair_differing_only_in_its_declared_change_passes(self):
        a = PV.fill_defaults({"brief": PIC})
        b = PV.make_frame_pair({"brief": PIC}, {"subject": "she turns to the camera"})
        self.assertEqual(PV.validate_pair(a, b), [])

    def test_a_pair_with_a_locked_variable_changed_fails_by_name(self):
        a = PV.fill_defaults({"brief": PIC})
        b = PV.make_frame_pair({"brief": PIC}, {"subject": "she turns to the camera"})
        b["sheet"]["colours"] = {"state": "filled", "value": "blue", "source": "person"}
        self.assertIn("colours", [p["id"] for p in PV.validate_pair(a, b)])
        with self.assertRaises(ValueError):
            PV.make_frame_pair({"brief": PIC}, {"wardrobe": "a red dress"})

    def test_every_filled_dial_feeling_and_technique_reaches_the_prompt(self):
        r = PV.preview("pictures.generate", PIC, quote=False)
        self.assertIn("THE LOOK OF THE PICTURE:", r["prompt"])
        self.assertIn("THE FEELING:", r["prompt"])
        self.assertNotIn("A hand holding it", r["prompt"])        # a film dial is not applicable to a still
        sh = r["sheet"]["recipe"]["sheet"]
        self.assertEqual(sh["dial.camera"]["state"], "not_applicable")
        self.assertEqual(sh["dial.absurdity"]["state"], "filled")  # a writing dial the guards read: recorded, not sent
        self.assertEqual(r["errors"], 0)

    def test_a_dial_definition_sent_verbatim_is_refused(self):
        f = PV.IR.check("gpt-image-2.5", "THE PICTURE\nA building-sized object.\nDream logic, rules broken on purpose, still pinned to the claim\nRULES\nno writing")
        self.assertTrue(any(x["id"] == "dial-definition" for x in f))

    def test_a_failed_pair_is_flagged_and_the_best_attempt_chosen(self):
        a = PV.fill_defaults({"brief": PIC})
        good = PV.make_frame_pair({"brief": PIC}, {"subject": "she turns to the camera"})
        worse = json.loads(json.dumps(good))
        worse["sheet"]["colours"] = {"state": "filled", "value": "blue", "source": "person"}
        worse["sheet"]["camera"] = {"state": "filled", "value": "low angle", "source": "person"}
        bad = json.loads(json.dumps(good))
        bad["sheet"]["colours"] = {"state": "filled", "value": "blue", "source": "person"}
        got = PV.choose_pair(a, [worse, bad])
        self.assertEqual(got["id"], 1)
        self.assertTrue(got["chosen"])
        self.assertEqual(len(got["below_criteria"]), 1)

    def test_the_gate_stops_with_one_plain_line(self):
        r = self.full()
        r["sheet"]["angle"] = {"state": "missing"}
        with self.assertRaises(ValueError) as e:
            PV.gate(r)
        self.assertTrue(str(e.exception).startswith("Stopped before any spend, not set: The angle"))

    def test_the_prompt_carries_no_brief_notes(self):
        for brief in (THREE, PIC):
            r = PV.preview("pictures.generate", brief, quote=False)
            for bad in ("**", "| Zone", "Source copy", "characters (source", "Why it rhymes", "`"):
                self.assertNotIn(bad, r["prompt"])
        first = r["fields"]["words_plain"][0].split("\n")[0]      # drawn words go in exactly
        self.assertIn(f'"{first}"', r["prompt"])

    def test_swaps_stop_at_the_next_label_and_source_of_is_kept(self):
        t = "- **SWAPS:** (1) the young woman becomes Creator-A.\n- **THE DIALS:**\n- intensity: swipe 3 → ours 4 (peak): x\n**1. THE INJECTED FRAME**\n| Zone |"
        self.assertEqual(PV.swaps_block(t), "(1) the young woman becomes Creator-A.")
        self.assertIn("the source of the remedy", PV.clean_md("the source of the remedy keeps its place"))
        self.assertEqual(PV.clean_md("The source woman becomes Yai"), "the woman in IMAGE 1 becomes Yai")

    def test_the_rulebook_refuses_notes_in_a_picture_prompt(self):
        f = PV.IR.check("gpt-image-2.5", "THE PICTURE\n**Why it rhymes:** x\n| Zone | a |\nRULES\nno writing")
        self.assertTrue(any(x["id"] == "notes-in-prompt" and x["level"] == "error" for x in f))

    def test_cli_check_exits_nonzero_on_a_blank_and_make_refuses(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t:
            json.dump({"brief": {**PIC, "product": ""}}, t)
        self.assertEqual(PV.main(["check", t.name]), 1)
        self.assertEqual(PV.main(["make", t.name]), 1)


class ClipSheet(unittest.TestCase):
    """The clip sheet: every clip input filled or not applicable with a reason; the voice is audio only."""

    def test_the_clip_ladder_ends_with_the_best_take_kept_and_flagged(self):
        rungs = [x["rung"] for x in PV._ladder("clips.seedance")]
        self.assertEqual(rungs[-1], "the best take is kept and flagged below_criteria")
        self.assertNotIn("held for a person", rungs)
        self.assertNotIn("clips.kling", rungs)
        self.assertIn("Kling", PV.plain_rung(next(x for x in PV._ladder("clips.seedance") if x["rung"] == "clips.backup")))

    def test_a_real_clip_fills_everything_but_the_approval(self):
        r = PV.preview("clips.seedance", CLIP, quote=False)
        self.assertTrue(r["ok"])
        self.assertEqual(r["sheet"]["needs"], ["Cost approved by"])
        sh = r["sheet"]["recipe"]["sheet"]
        self.assertEqual(sh["line_not_typed"]["value"], "yes")       # CSH-1 (voice is audio)
        self.assertEqual(sh["shot_emotion"]["state"], "filled")      # the doctrine map's emotion row

    def test_an_emotion_without_a_face_is_missing(self):
        r = PV.fill_defaults_clip({**CLIP, "face": "", "gestures": ""})
        self.assertIn("The face", r["needs"])

    def test_make_goes_through_the_clip_chain_take_loop(self):
        cr = PV._clip_chain()
        seen = {}
        orig = PV._clip_chain
        def fake(run, call, prompt=None, cfg=None, people=None):
            seen.update(call=call, prompt=prompt)
            return {"file": None, "rung": "kling-4.0", "attempts": [{"take": 1}], "below_criteria": ["lip sync"]}
        cr.make_clip = fake
        PV._clip_chain = lambda: cr
        try:
            got = PV.make_clip(CLIP, "test")
        finally:
            PV._clip_chain = orig
        self.assertEqual(got["rung"], "kling-4.0")
        self.assertTrue(seen["prompt"].startswith("Image 1 is the first frame"))
        self.assertEqual(seen["call"]["id"], "G01-C1")

    def test_a_dry_run_spends_nothing(self):
        got = PV.make_clip(CLIP, "test", dry_run=True)
        self.assertIsNone(got.get("file"))


REPO_RUNS = HERE.parent.parent / "runs"


class Matrix(unittest.TestCase):
    """A person's matrix: their rows replace the teardown's, the swap words are rebuilt from them, a row turned back is a keep."""

    BASE = {"product_in_frame": False, "product_kit": "kit-a", "stays": ["the wall"], "words": "set_on_top",
            "swaps": [{"from": "A woman", "to": "Our cast member", "kind": "cast", "ref": "x"},
                      {"from": "The caption", "to": "New words", "kind": "words", "ref": None}]}

    def test_rows_replace_and_other_keys_stay(self):
        m = PV.matrix_list({"swaps": [{"from": "A pendant", "to": "An amulet", "kind": "bogus"}, {"from": "Hair", "to": " "}]}, self.BASE)
        self.assertEqual(m["swaps"], [{"from": "A pendant", "to": "An amulet", "kind": "drawn", "ref": None}])
        self.assertEqual(m["product_kit"], "kit-a")
        self.assertEqual(m["source"], "matrix")
        self.assertNotEqual(PV.swap_key(m), PV.swap_key(self.BASE))

    def test_text_skips_words_set_on_top_and_says_keeps(self):
        t = PV.matrix_text(PV.matrix_list({}, self.BASE), ["Stray hairs"])
        self.assertEqual(t.splitlines(), ["A woman in IMAGE 1 becomes our cast member.", "Keep stray hairs exactly as in IMAGE 1."])
        self.assertIn("becomes an amulet.", PV.matrix_text({"swaps": [{"from": "a pendant", "to": "An amulet", "kind": "drawn"}]}))



class Variation(unittest.TestCase):
    """A variation is the approved picture's own brief with ONE change, built on the same path (2026-10-27)."""

    BRIEF = {"brand": "b", "run": "r", "dials": {"humor": 3, "cultural_casting": 3},
             "swap_list": {"swaps": [{"from": "A woman", "to": "Our cast", "kind": "cast", "ref": "c"}],
                           "stays": ["The crop", "The light"], "words": "set_on_top"}}

    def test_board_and_maker_use_the_same_relative_base_from_another_directory(self):
        import os
        before = Path.cwd()
        base = Path(PV.preview("pictures.generate", PIC, quote=False)["inputs"][0]["path"])
        try:
            os.chdir(HERE)
            r = PV.preview("pictures.generate", {**PIC, "base": str(base.relative_to(PV.REPO))}, quote=False)
        finally:
            os.chdir(before)
        self.assertEqual(Path(r["inputs"][0]["path"]), base)
        self.assertEqual(r["choices"][0]["path"], r["inputs"][0]["path"])
        self.assertEqual(r["choices"][0]["label"], "The approved picture")

    def test_missing_approved_base_never_falls_back_to_the_swipe(self):
        with self.assertRaisesRegex(ValueError, "approved base picture is missing"):
            PV.build_picture({**PIC, "base": "runs/absent-variation-base.png"})

    def test_words_only_makes_no_picture(self):
        b = PV.variation_brief(self.BRIEF, {"words": ["NEW / WORDS"]}, approved="/x/plate.png")
        self.assertEqual(b["our_copy"], ["NEW / WORDS"])
        self.assertNotIn("added", b)
        self.assertFalse(PV.needs_picture({"words": ["NEW"]}))

    def test_one_change_rides_with_the_approved_picture(self):
        b = PV.variation_brief(self.BRIEF, {"picture": "The spots move to the arm."}, approved="/x/plate.png")
        self.assertEqual(b["base"], "/x/plate.png")                   # an edit of the approved picture, not a remake
        self.assertEqual(b["swaps"], "THE ONE CHANGE to IMAGE 1: The spots move to the arm. Everything else stays "
                                     "exactly as IMAGE 1 shows it.")
        self.assertEqual(b["swap_list"], self.BRIEF["swap_list"])     # nothing else touched

    def test_a_swap_row_replaces_its_match_and_a_new_person_drops_the_lookalike(self):
        b = PV.variation_brief(self.BRIEF, {"swap": [{"from": "A woman", "to": "A woman of 45"}], "people": "made-up",
                                            "stays_drop": ["The light"]})
        self.assertEqual([r["to"] for r in b["swap_list"]["swaps"]], ["A woman of 45"])
        self.assertEqual(b["swap_list"]["swaps"][0]["kind"], "drawn")
        self.assertEqual(b["swap_list"]["stays"], ["The crop"])
        self.assertNotIn("cultural_casting", b["dials"])
        self.assertEqual(self.BRIEF["swap_list"]["swaps"][0]["to"], "Our cast")   # the approved brief is never written to

class Lessons(unittest.TestCase):
    """Every lesson from a review is a rule for any ad, and the chain really applies it (lessons.json)."""
    def test_every_lesson_names_code_that_applies_it(self):
        import json
        repo = Path(__file__).resolve().parents[2]
        for x in json.loads((Path(__file__).parent / "lessons.json").read_text())["lessons"]:
            f, _, line = (s.strip() for s in x["enforced_by"].partition("::"))
            self.assertTrue((repo / f).is_file(), f"{x['id']}: {f} is not a file")
            self.assertIn(line, (repo / f).read_text(), f"{x['id']}: its rule is not applied where it says")
            self.assertIn(x["status"], ("draft", "approved", "deprecated"))

    def test_a_product_in_a_hand_is_in_use_and_one_on_a_shelf_is_not(self):
        import preview as PV
        self.assertTrue(PV.in_use({"product_in_frame": True, "product_where": "held in a black-gloved hand at the lathered nape"}))
        self.assertTrue(PV.in_use({"product_in_frame": True, "product_where": "pressed on his cheek, bristles to skin"}))
        self.assertFalse(PV.in_use({"product_in_frame": True, "product_where": "standing on the bathroom counter, front to camera"}))
        self.assertFalse(PV.in_use({"product_in_frame": False, "product_where": "in his hand"}))

    def test_no_lesson_names_a_brand(self):
        import json
        brands = [d.name for d in (Path(__file__).resolve().parents[2] / "brands").iterdir() if d.is_dir()]
        for x in json.loads((Path(__file__).parent / "lessons.json").read_text())["lessons"]:
            for b in brands:
                self.assertNotIn(b.lower(), x["rule"].lower(), f"{x['id']} names {b}: a lesson is for every brand")

    def test_the_board_gets_them(self):
        self.assertTrue(PV.lessons("image"))


class SetWords(unittest.TestCase):
    def test_a_writers_type_note_never_goes_on_the_picture(self):
        cell = '"80\'s filter kept my dark spots" / "\U0001F603" (white fill, black outline, bold sans, ~3% frame height)'
        self.assertEqual(PV.set_words(cell), "80's filter kept my dark spots")

    def test_a_typed_line_break_is_kept(self):
        self.assertEqual(PV.set_words("Shaved 2 days ago... / bumps already"), "Shaved 2 days ago...\nbumps already")


if __name__ == "__main__":
    unittest.main()
