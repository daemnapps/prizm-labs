#!/usr/bin/env python3
"""python3 machine/test_elements.py — from any cwd. Stdlib unittest only; no
network, no paid call. Synthetic media is made with ffmpeg's lavfi sources.

EVERY ELEMENT OF A VIDEO (ELEMENTS.md, the owner 2026-09-23: "teardown names every
element, the AI brief carries it, PRODUCTION MAKES IT (or pulls it from a bank
made once), the edit only assembles … all these elements need to be green").

On the v15 fixture — one scene of every kind, plus layers, music, sfx, hooks,
doctrine sections, the piece's ad framework, and priorities:

  * each kind is parsed, validated and turned into items: a screen is one
    text-free plate; a split is two B-roll pictures (two frames and one silent
    clip a side); a greenscreen is a talking scene plus a background plate; an
    endcard is an EDIT of the brand's real packshot;
  * every element field is carried into plan.json untouched, and a malformed
    one is a gate finding naming the field;
  * the banks pick deterministically and refuse loudly; the maker only plans;
  * every clip is colour-matched to the piece's first frame, original archived;
  * a scene's `section` and the piece's `framework` are the MARKETING
    DOCTRINE's ids, read from components/marketing-doctrine at run time; v14's
    retired `module` is read only as a warned alias for a missing section.
"""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
BRIEF = FIX / "brief-v15.md"
BRIEF_V14 = FIX / "brief-v14.md"     # the retired `module` shape, kept to prove it is caught


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"test_el_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run = load("run")
mi = load("model_inputs")
scenes = load("scenes")
banks = load("banks")
make_bank = load("make_bank")
colour = load("colour_match")
preflight = load("preflight")

HAVE_FFMPEG = bool(shutil.which("ffmpeg"))
_DOORS = run.platform.registry().get("doors") or {}
MOTION_MODEL = _DOORS["motion"]["model"]        # read, never written here
STILL_MODEL = _DOORS["still"]["model"]


@contextlib.contextmanager
def env(**extra):
    saved = dict(os.environ)
    saved_mod = sys.modules.get("daemn_keys")
    os.environ.update(extra)
    sys.modules["daemn_keys"] = types.SimpleNamespace(key=lambda name, required=False: "")
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)
        if saved_mod is None:
            sys.modules.pop("daemn_keys", None)
        else:
            sys.modules["daemn_keys"] = saved_mod


def quiet(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = fn(*a, **kw)
    return code, buf.getvalue()


def text():
    return BRIEF.read_text()


def block():
    doc, why = scenes.json_block(text())
    assert why is None, why
    return doc


def with_block(doc) -> str:
    return text().split("```json")[0] + "```json\n" + json.dumps(doc, indent=1) + "\n```\n"


def sc(doc, sid):
    return next(s for s in doc["scenes"] if s["id"] == sid)


def plan_of(t: str | None = None):
    if t is None:
        return run.build_plan_from_brief(BRIEF, "_fixture")
    d = Path(tempfile.mkdtemp(prefix="vm-el-"))
    try:
        p = d / "brief.md"
        p.write_text(t)
        return run.build_plan_from_brief(p, "_fixture")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def items_of(plan=None):
    return {it["id"]: it for it in run.batches_of(plan or plan_of(), "_fixture", {})}


def gate(doc):
    t = with_block(doc)
    return mi.production_gate(t, scenes.parse(t), brand="_fixture")[0]


def refused(testcase, doc, *needles):
    fails = gate(doc)
    bv = mi.brief_violations(doc)
    for n in needles:
        testcase.assertTrue(any(n in f for f in fails), f"{n!r} not in gate: {fails}")
        testcase.assertTrue(any(n in b for b in bv), f"{n!r} not in rule 12: {bv}")


# ======================================================================
# the brief as written

class TheV15BriefIsGreen(unittest.TestCase):
    def test_block_and_gate_are_green_and_only_warn_on_unfilled(self):
        self.assertEqual(mi.brief_violations(text()), [])
        fails, warns = mi.production_gate(text(), scenes.parse(text()), brand="_fixture")
        self.assertEqual(fails, [])
        self.assertTrue(any("screen S4" in w and "[UNFILLED]" in w for w in warns), warns)
        self.assertTrue(any("card S3" in w for w in warns), warns)

    def test_one_scene_of_every_kind_in_play_order(self):
        plan = plan_of()
        self.assertEqual([(s["id"], s.get("kind")) for s in plan["scenes"]],
                         [("S1", "talking"), ("S2", "broll"), ("S3", "card"),
                          ("S4", "screen"), ("S5", "split"), ("S6", "greenscreen"),
                          ("S7", "endcard")])

    def test_the_view_shows_every_kind_and_the_piece_elements(self):
        view = scenes.render_view(block())
        for needle in ("**S4 · SCREEN**", "**S5 · SPLIT**", "GREENSCREEN (cutout)",
                       "**S7 · ENDCARD**", "## Layers", "## Music", "## Sound effects",
                       "## Hooks"):
            self.assertIn(needle, view)


# ======================================================================
# what production makes, per kind

class ProductionMakesEachKind(unittest.TestCase):
    def setUp(self):
        self.items = items_of()

    def ids_for(self, sid):
        return [i for i, it in self.items.items() if it.get("for") == sid or i == sid
                or (it.get("split") or {}).get("of") == sid]

    def test_screen_is_one_text_free_plate_and_no_clip(self):
        self.assertEqual(self.ids_for("S4"), ["S4-PLATE"])
        p = self.items["S4-PLATE"]
        self.assertEqual((p["kind"], p["contract"], p["frame_role"]), ("still", "still-generate", "plate"))
        for line in ("FIVE STARS", "IT STOPPED COMING BACK"):
            self.assertNotIn(line, p["params"]["prompt"])
        self.assertIn(mi.card_plate()["clean_line"], p["params"]["prompt"])
        self.assertEqual(p["screen"]["surface"], "review")
        self.assertEqual(p["screen"]["lines"][0], "FIVE STARS")
        self.assertEqual(mi.violations(p), [])
        self.assertEqual(preflight.post_effect_hits(p["params"]["prompt"]), [])

    def test_split_is_two_b_roll_pictures_each_with_two_frames_and_a_silent_clip(self):
        self.assertEqual(sorted(self.ids_for("S5")),
                         sorted(["S5-L-F1", "S5-L-FLAST", "S5-L", "S5-R-F1", "S5-R-FLAST", "S5-R"]))
        for side in ("L", "R"):
            clip = self.items[f"S5-{side}"]
            self.assertEqual(clip["kind"], "motion")
            self.assertFalse(clip["to_camera"])
            self.assertEqual(clip["start_frame"], f"S5-{side}-F1")
            self.assertEqual(clip["last_frame"], f"S5-{side}-FLAST")
            self.assertFalse(any(m["role"] == "audio_references" for m in clip["medias"]))
            self.assertEqual(clip["split"]["labels"], ["BEFORE", "AFTER"])
            self.assertEqual(mi.violations(clip), [], side)
            self.assertEqual(self.items[f"S5-{side}-FLAST"]["edit_of"], f"S5-{side}-F1")
        # the paragraph is laid under the pair ONCE
        self.assertEqual(self.items["S5-L"]["vo_over"], "vo/S5.mp3")
        self.assertIsNone(self.items["S5-R"]["vo_over"])
        self.assertNotIn("BEFORE", self.items["S5-L-F1"]["params"]["prompt"])

    def test_greenscreen_is_a_talking_scene_plus_a_background_plate(self):
        self.assertEqual(sorted(self.ids_for("S6")), ["S6", "S6-BG", "S6-F1", "S6-FLAST"])
        self.assertEqual(self.items["S6"]["kind"], "talking")
        self.assertTrue(any(m["role"] == "audio_references" for m in self.items["S6"]["medias"]))
        bg = self.items["S6-BG"]
        self.assertEqual((bg["kind"], bg["contract"]), ("still", "still-generate"))
        self.assertEqual(bg["greenscreen"], {"talker_scene": "S6", "layout": "cutout"})
        self.assertTrue(bg["params"]["prompt"].startswith("an article page on a laptop"))
        self.assertEqual(mi.violations(bg), [])

    def test_endcard_is_an_edit_of_the_real_packshot(self):
        self.assertEqual(self.ids_for("S7"), ["S7-PACKSHOT"])
        e = self.items["S7-PACKSHOT"]
        self.assertEqual((e["kind"], e["contract"]), ("edit", "still-edit-fidelity"))
        first = e["medias"][0]["value"]
        self.assertTrue(first.endswith("_fixture-product/images/packshot-hero.png"), first)
        self.assertTrue(Path(first).is_file())
        # "the Fixture Balm packshot" is replaced by the real file, never sent as words
        self.assertFalse(any("packshot" in m["value"] and not m["value"].endswith(".png")
                             for m in e["medias"]))
        self.assertEqual(e["products"], ["_fixture-product"])
        self.assertIn(mi.elements()["endcard_keep_line"], e["params"]["prompt"])
        for line in ("Price: $24.00", "Get yours today"):
            self.assertNotIn(line, e["params"]["prompt"])
        self.assertEqual(e["endcard"]["offer_lines"][1], "Price: $24.00")
        self.assertEqual(mi.violations(e), [])
        self.assertEqual(preflight.post_effect_hits(e["params"]["prompt"]), [])

    def test_endcard_product_is_read_from_the_briefs_words(self):
        s7 = next(s for s in plan_of()["scenes"] if s["id"] == "S7")
        self.assertEqual(s7["endcard"]["product"], "_fixture-product")

    def test_the_machine_hand_refuses_an_endcard_with_no_packshot_file(self):
        e = copy.deepcopy(self.items["S7-PACKSHOT"])
        e["packshot"] = {"product": "_fixture-other", "file": None}
        e["medias"] = []
        d = Path(tempfile.mkdtemp(prefix="vm-el-"))
        self.addCleanup(shutil.rmtree, d, True)
        with self.assertRaises(SystemExit) as cm:
            with env():
                run.run_machine_hand([e], d, dry_run=False, brand="_fixture")
        self.assertIn("no real packshot", str(cm.exception))


# ======================================================================
# carried untouched into plan.json

class ElementsAreCarried(unittest.TestCase):
    def test_scene_fields_travel_on_scenes_and_items(self):
        plan = plan_of()
        s1 = plan["scenes"][0]
        self.assertEqual((s1["opens"], s1["section"], s1["priority"]), (True, "hook", 1))
        self.assertNotIn("module", s1)
        items = items_of(plan)
        self.assertEqual(items["S1"]["section"], "hook")
        self.assertEqual(items["S7-PACKSHOT"]["priority"], 1)
        self.assertEqual(items["S5-L"]["section"], "unique-mechanism")
        self.assertFalse(any("module" in it for it in items.values()))

    def test_the_piece_carries_its_framework_id(self):
        self.assertEqual(plan_of()["piece"]["framework"], "pas")

    def test_piece_elements_travel_untouched(self):
        plan = plan_of()
        doc = block()
        for k in ("layers", "hooks"):
            self.assertEqual(plan[k], doc[k])
        self.assertEqual(plan["music"], doc["music"])     # banks not resolved yet
        self.assertEqual(plan["sfx"], doc["sfx"])

    def test_null_music_is_simply_absent(self):
        doc = block()
        doc["music"] = None
        self.assertNotIn("music", plan_of(with_block(doc)))
        self.assertEqual(gate(doc), [])


# ======================================================================
# v14's `module` is retired — read only as a warned alias for `section`

class ModuleIsADeprecatedAlias(unittest.TestCase):
    def test_module_fills_a_missing_section_with_a_warning(self):
        doc = block()
        for sid, mod in (("S1", "hook"), ("S5", "mechanism"), ("S7", "cta")):
            s = sc(doc, sid)
            s.pop("section")
            s["module"] = mod
        t = with_block(doc)
        fails, warns = mi.production_gate(t, scenes.parse(t), brand="_fixture")
        self.assertEqual(fails, [])
        self.assertEqual(mi.brief_violations(doc), [])
        for sid, want in (("S1", "hook"), ("S5", "unique-mechanism"), ("S7", "call-to-action")):
            self.assertTrue(any(f"scene {sid} carries 'module'" in w and f"read as section "
                                f"{want!r}" in w for w in warns), (sid, warns))
        plan = plan_of(t)
        got = {s["id"]: s["section"] for s in plan["scenes"]}
        self.assertEqual((got["S1"], got["S5"], got["S7"]),
                         ("hook", "unique-mechanism", "call-to-action"))
        self.assertFalse(any("module" in s for s in plan["scenes"]))

    def test_module_never_overrides_a_stated_section(self):
        doc = block()
        sc(doc, "S2")["module"] = "proof"
        t = with_block(doc)
        fails, warns = mi.production_gate(t, scenes.parse(t), brand="_fixture")
        self.assertEqual(fails, [])
        self.assertTrue(any("scene S2 carries 'module'" in w and "the section wins" in w
                            for w in warns), warns)
        self.assertEqual(sc_plan(plan_of(t), "S2")["section"], "problem")

    def test_the_v14_fixture_is_caught(self):
        t = BRIEF_V14.read_text()
        fails, warns = mi.production_gate(t, scenes.parse(t), brand="_fixture")
        self.assertTrue(any("scene S5's 'section' is 'mechanism'" in f for f in fails), fails)
        self.assertTrue(any("'_fixture-framework' is its own" in w for w in warns), warns)
        self.assertTrue(any("scene S1 carries 'module'" in w for w in warns), warns)


def sc_plan(plan, sid):
    return next(s for s in plan["scenes"] if s["id"] == sid)


# ======================================================================
# refused by name

class ElementsAreRefusedByName(unittest.TestCase):
    def test_screen_plate_with_quoted_words(self):
        doc = block()
        sc(doc, "S4")["screen"]["plate"] += ', a banner reading "BEST EVER"'
        refused(self, doc, "screen S4's plate has words in it")

    def test_screen_plate_copying_a_line(self):
        doc = block()
        sc(doc, "S4")["screen"]["plate"] += ", five stars across the top"
        refused(self, doc, "screen S4's plate has words in it ('FIVE STARS')")

    def test_screen_surface_off_the_list(self):
        doc = block()
        sc(doc, "S4")["screen"]["surface"] = "tweet"
        refused(self, doc, "screen S4's 'surface' is 'tweet'")

    def test_split_layout_and_side_without_beats(self):
        doc = block()
        sc(doc, "S5")["split"]["layout"] = "diagonal"
        sc(doc, "S5")["split"]["right"]["beats"] = []
        refused(self, doc, "split S5's 'layout' is 'diagonal'", "split S5's right has no beats")

    def test_split_side_with_words_in_its_frame(self):
        doc = block()
        sc(doc, "S5")["split"]["left"]["first_frame"]["subject"] += ' under a sign saying "BEFORE"'
        refused(self, doc, "split S5's left's first_frame.subject has words in it")

    def test_greenscreen_background_with_words(self):
        doc = block()
        sc(doc, "S6")["greenscreen"]["background"] = 'a page headed "WHY IT COMES BACK"'
        refused(self, doc, "greenscreen S6's background has words in it")

    def test_greenscreen_talker_scene_missing_or_not_to_camera(self):
        doc = block()
        sc(doc, "S6")["greenscreen"]["talker_scene"] = "S9"
        refused(self, doc, "greenscreen S6's talker_scene 'S9' is not in the brief's scenes")
        doc = block()
        sc(doc, "S6")["greenscreen"]["talker_scene"] = "S2"
        refused(self, doc, "greenscreen S6's talker_scene S2 is not a to_camera scene")

    def test_greenscreen_off_camera_is_refused(self):
        doc = block()
        sc(doc, "S6")["to_camera"] = False
        refused(self, doc, "greenscreen S6's 'to_camera' is False")

    def test_endcard_line_not_from_the_offer_bank(self):
        doc = block()
        sc(doc, "S7")["endcard"]["offer_lines"].append("NOW 50% OFF")
        refused(self, doc, "endcard S7's offer line 'NOW 50% OFF' is not from the offer bank")

    def test_endcard_unfilled_line_is_warned_not_refused(self):
        doc = block()
        sc(doc, "S7")["endcard"]["offer_lines"].append("FREE SHIPPING [UNFILLED]")
        t = with_block(doc)
        fails, warns = mi.production_gate(t, scenes.parse(t), brand="_fixture")
        self.assertEqual(fails, [])
        self.assertTrue(any("endcard S7" in w and "[UNFILLED]" in w for w in warns), warns)

    def test_endcard_guarantee_not_in_the_bank(self):
        doc = block()
        sc(doc, "S7")["endcard"]["guarantee"] = "lifetime guarantee"
        refused(self, doc, "endcard S7's guarantee 'lifetime guarantee' is not from the offer bank")

    def test_endcard_that_names_no_product(self):
        doc = block()
        sc(doc, "S7")["refs"] = ["the packshot", "the style frame"]
        doc["product_lock"] = []
        refused(self, doc, "endcard S7 names no product the brand has a packshot for")

    def test_endcard_whose_product_has_no_photograph(self):
        doc = block()
        sc(doc, "S7")["endcard"]["product"] = "_fixture-other"
        refused(self, doc, "endcard S7's product '_fixture-other' has no real packshot")

    def test_kind_and_to_camera_must_agree(self):
        doc = block()
        sc(doc, "S2")["kind"] = "talking"
        refused(self, doc, "scene S2 is kind talking with to_camera False")

    def test_opens_exactly_once(self):
        doc = block()
        sc(doc, "S2")["opens"] = True
        refused(self, doc, "'opens' is true on S1, S2")
        doc = block()
        sc(doc, "S1")["opens"] = False
        refused(self, doc, "'opens' is true on no scene")

    def test_section_off_the_doctrine_and_priority(self):
        doc = block()
        sc(doc, "S3")["section"] = "tease"
        sc(doc, "S4")["priority"] = 5
        refused(self, doc, "scene S3's 'section' is 'tease' — a section id from "
                "components/marketing-doctrine/frameworks.json",
                "scene S4's 'priority' is 5")
        # the ids named are the doctrine's own, read from the file
        fails = gate(doc)
        msg = next(f for f in fails if "scene S3's 'section'" in f)
        for sid in mi.section_ids():
            self.assertIn(sid, msg)

    def test_a_framework_of_its_own_is_carried_and_warned(self):
        # the owner, 2026-09-23: an ad can run a framework of its own; the sections are the contract
        doc = block()
        doc["piece"]["framework"] = "the glow-up arc"
        fails, warns = mi.doctrine_findings(doc)
        self.assertFalse(any("framework" in f for f in fails), fails)
        msg = next(w for w in warns if "'the glow-up arc' is its own" in w)
        for fid in (f["id"] for f in mi.ad_frameworks()):
            self.assertIn(fid, msg)

    def test_framework_observed_or_by_name(self):
        doc = block()
        doc["piece"]["framework"] = "observed — a list of four tries, then the answer"
        self.assertEqual(gate(doc), [])
        self.assertEqual(mi.brief_violations(doc), [])
        # an older brief wrote the row's full name: read as its id, warned
        row = next(f for f in mi.ad_frameworks() if f["id"] == "pas")
        doc["piece"]["framework"] = row["name"]
        t = with_block(doc)
        fails, warns = mi.production_gate(t, scenes.parse(t), brand="_fixture")
        self.assertEqual(fails, [])
        self.assertTrue(any("read as its id 'pas'" in w for w in warns), warns)
        self.assertEqual(plan_of(t)["piece"]["framework"], "pas")

    def test_a_candidate_section_is_warned_not_refused(self):
        doc = block()
        sc(doc, "S2")["section"] = "the shelf check (candidate for the bank)"
        t = with_block(doc)
        fails, warns = mi.production_gate(t, scenes.parse(t), brand="_fixture")
        self.assertEqual(fails, [])
        self.assertTrue(any("scene S2's 'section'" in w and "candidate" in w for w in warns))


    def test_layers_music_sfx_hooks_shapes(self):
        doc = block()
        doc["layers"]["stickers"] = []
        doc["layers"]["annotations"][0]["kind"] = "sparkle"
        doc["layers"]["transitions"][0]["kind"] = "spin"
        doc["layers"]["platform_ui"][0]["scene"] = "S12"
        doc["music"]["energy"] = "extreme"
        doc["sfx"].append({"cue": "pop", "at_words": "", "scene": ""})
        doc["hooks"][0]["opener_scene"] = "S99"
        refused(self, doc, "layers.stickers is not a layer",
                "layers.annotations[1].kind is 'sparkle'",
                "layers.transitions[1].kind is 'spin'",
                "layers.platform_ui[1].scene names scene 'S12'",
                "music.energy is 'extreme'",
                "sfx[3] (pop) says neither 'at_words' nor 'scene'",
                "hooks[1].opener_scene names scene 'S99'")

    def test_a_card_nested_under_its_kind_reads_the_same(self):
        doc = block()
        s3 = sc(doc, "S3")
        s3["card"] = {k: s3.pop(k) for k in ("plate", "lines", "lands_on", "sfx", "refs")}
        self.assertEqual(gate(doc), [])
        self.assertEqual(mi.brief_violations(doc), [])
        plate = items_of(plan_of(with_block(doc)))["S3-PLATE"]
        self.assertEqual(plate["card"]["lines"][0], "FOUR TRIES")

    def test_flat_new_kinds_read_the_same(self):
        doc = block()
        s4 = sc(doc, "S4")
        s4.update(s4.pop("screen"))
        self.assertEqual(gate(doc), [])
        self.assertEqual(items_of(plan_of(with_block(doc)))["S4-PLATE"]["screen"]["surface"], "review")


class TheRollSheetKnowsEveryKind(unittest.TestCase):
    def test_s_x_g_e_rows_map_to_their_kinds(self):
        self.assertEqual(mi.roll_sheet_check(block())[0], [])

    def test_a_row_on_the_wrong_kind_is_refused(self):
        doc = block()
        doc["roll_sheet"][2]["scene"] = "S2"          # the S row onto B-roll
        doc["roll_sheet"][6]["scene"] = "S4"          # the E row onto the screen
        fails = gate(doc)
        self.assertTrue(any("an S row is made as a screen scene" in f.replace("a S row", "an S row")
                            or "a S row is made as a screen scene" in f for f in fails), fails)
        self.assertTrue(any("a E row is made as an endcard scene" in f for f in fails), fails)


# ======================================================================
# the banks

class Banks(unittest.TestCase):
    ROOT = FIX / "banks"

    def test_music_is_picked_by_energy_mood_then_nearest_tempo(self):
        r = banks.pick("music", {"energy": "mid", "tempo_bpm": 110, "mood": "warm"}, self.ROOT)
        self.assertEqual(r["id"], "music-mid-warm-104")
        self.assertEqual(banks.pick("music", {"energy": "mid", "tempo_bpm": 110, "mood": "warm"},
                                    self.ROOT), r)

    def test_a_row_not_made_yet_falls_back_to_the_nearest_made_row(self):
        # 2026-09-23 ("improvise and infer"): nearest made row instead of a refusal
        got = banks.pick("music", {"energy": "low", "tempo_bpm": 80, "mood": "calm"}, self.ROOT)
        self.assertNotEqual(got.get("id"), "music-low-calm-80")
        self.assertIn("nearest", got.get("_nearest", ""))

    def test_tempo_out_of_tolerance_and_unknown_mood_refuse(self):
        got = banks.pick("music", {"energy": "mid", "tempo_bpm": 170, "mood": "warm"}, self.ROOT)
        self.assertIn("nearest", got.get("_nearest", "") or str(got.get("id")))
        got = banks.pick("music", {"energy": "mid", "tempo_bpm": 104, "mood": "gothic"}, self.ROOT)
        self.assertIn("nearest", got.get("_nearest", ""))  # an unknown mood takes the nearest made row

    def test_sfx_by_cue_name_then_tag(self):
        self.assertEqual(banks.pick("sfx", {"cue": "Ka Ching"}, self.ROOT)["id"], "ka-ching")
        self.assertEqual(banks.pick("sfx", "room-tone-kitchen", self.ROOT)["id"], "room-tone-kitchen")
        with self.assertRaises(banks.BankMiss) as cm:
            banks.pick("sfx", "pop", self.ROOT)
        self.assertIn("row 'pop'", str(cm.exception))
        with self.assertRaises(banks.BankMiss) as cm:
            banks.pick("sfx", "kazoo", self.ROOT)
        self.assertIn("not in the bank", str(cm.exception))

    def test_resolve_writes_bank_id_and_file_and_keeps_the_rest(self):
        plan = {"music": {"energy": "mid", "tempo_bpm": 104, "mood": "warm"},
                "sfx": [{"cue": "whoosh", "scene": "S2", "at_words": ""},
                        {"cue": "pop", "scene": "S4", "at_words": ""}]}
        fails = banks.resolve(plan, self.ROOT)
        self.assertEqual(plan["music"]["bank_id"], "music-mid-warm-104")
        self.assertEqual(plan["music"]["mood"], "warm")
        self.assertEqual(plan["sfx"][0]["file"], "Shared Assets/banks/sfx/whoosh.mp3")
        self.assertEqual(plan["sfx"][0]["scene"], "S2")
        self.assertEqual(len(fails), 1)
        self.assertTrue(fails[0].startswith("sfx[2]:"))

    def test_the_real_banks_are_made(self):
        # made 2026-09-23 on the owner's go (9 music beds, 16 sfx)
        st = banks.status()
        self.assertEqual(len(st["music"]["made"]), 9)
        for cue in ("whoosh", "pop", "riser", "ka-ching", "stinger", "swoosh-soft", "click",
                    "room-tone-kitchen", "room-tone-bathroom", "room-tone-clinic",
                    "room-tone-street", "room-tone-bedroom", "room-tone-car"):
            self.assertIn(cue, st["sfx"]["made"])


class MakeBank(unittest.TestCase):
    def test_dry_run_plans_every_row_and_costs_it(self):
        code, out = quiet(make_bank.main, ["--bank", "all", "--dry-run"])
        self.assertEqual(code, 0, out)
        self.assertIn("all banks: ≈ $", out)  # every real row is made, so nothing is left to plan

    def test_without_dry_run_or_spend_nothing_is_made(self):
        code, out = quiet(make_bank.main, ["--bank", "sfx"])
        self.assertEqual(code, 2)
        self.assertIn("nothing was made", out)

    def test_a_made_row_through_the_seam_is_written_and_marked(self):
        d = Path(tempfile.mkdtemp(prefix="vm-bank-"))
        self.addCleanup(shutil.rmtree, d, True)
        shutil.copytree(FIX / "banks", d / "banks")
        calls = []

        def fake(method, url, body, headers):
            calls.append((method, url, body, headers))
            return b"ID3" + b"\x00" * 200

        res = make_bank.make("sfx", d / "banks", only=["pop"], dry_run=False, spend=True,
                             out_dir=d / "drive", transport=fake, key="k")
        self.assertEqual(res["made"], ["pop"])
        self.assertEqual(calls[0][2]["text"][:12], "a single sof")
        self.assertEqual(calls[0][3]["xi-api-key"], "k")
        self.assertTrue((d / "drive" / "pop.mp3").is_file())
        self.assertEqual(banks.pick("sfx", "pop", d / "banks")["file"], "Shared Assets/banks/sfx/pop.mp3")


# ======================================================================
# clip colour

def lavfi_clip(path: Path, colour: str, audio=True):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
           f"color=c={colour}:s=64x64:d=1:r=10"]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-shortest",
                "-c:a", "aac"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True, capture_output=True)


def lavfi_still(path: Path, colour: str):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"color=c={colour}:s=64x64:d=0.1", "-frames:v", "1", str(path)],
                   check=True, capture_output=True)


def mean_rgb(path: Path):
    from PIL import Image
    with tempfile.TemporaryDirectory() as t:
        png = Path(t) / "f.png"
        if path.suffix == ".mp4":
            colour._first_frame(path, png)
        else:
            shutil.copy2(path, png)
        with Image.open(png) as im:
            im = im.convert("RGB")
            px = list(im.getdata())
    return tuple(sum(p[c] for p in px) / len(px) for c in range(3))


def has_audio(path: Path) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                        "stream=codec_type", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return "audio" in r.stdout


@unittest.skipUnless(HAVE_FFMPEG and colour.HAVE_PIL, "ffmpeg and PIL are needed")
class ClipColour(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="vm-colour-"))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.ref = self.d / "S1-F1.png"
        lavfi_still(self.ref, "0x3080d0")
        self.clip = self.d / "S2.mp4"
        lavfi_clip(self.clip, "0xc05020")

    def test_a_clip_is_matched_to_the_first_frame_on_a_copy_with_the_original_archived(self):
        before = mean_rgb(self.clip)
        res = colour.match_clip(self.clip, self.ref, archive_dir=self.d / "versions", stem="S2")
        self.assertTrue(res["matched"], res)
        after, want = mean_rgb(self.clip), mean_rgb(self.ref)
        for c in range(3):
            self.assertLess(abs(after[c] - want[c]), abs(before[c] - want[c]))
            self.assertLess(abs(after[c] - want[c]), 12)
        kept = self.d / "versions" / "S2-precolour.mp4"
        self.assertTrue(kept.is_file())
        self.assertLess(max(abs(a - b) for a, b in zip(mean_rgb(kept), before)), 3)
        self.assertTrue(has_audio(self.clip))

    def test_it_is_never_matched_twice(self):
        colour.match_clip(self.clip, self.ref, archive_dir=self.d / "versions", stem="S2")
        again = colour.match_clip(self.clip, self.ref, archive_dir=self.d / "versions", stem="S2")
        self.assertFalse(again["matched"])
        self.assertIn("already matched", again["why"])

    def test_a_missing_reference_never_loses_the_clip(self):
        res = colour.match_clip(self.clip, self.d / "nope.png")
        self.assertFalse(res["matched"])
        self.assertTrue(self.clip.is_file())

    def _run_dir(self):
        r = self.d / "run"
        (r / "batches").mkdir(parents=True)
        (r / "media").mkdir()
        run.write_json(r / "batches" / "01-motion.json", {"items": [
            {"id": "S1-F1", "kind": "still", "frame_role": "first", "for": "S1"},
            {"id": "S2", "kind": "motion", "lines": [], "model": MOTION_MODEL,
             "params": {"duration": 1}}]})
        run.write_json(r / "direct.json", {"S1-F1": {"file": str(self.ref)}})
        clip = r / "media" / "S2.mp4"
        shutil.copy2(self.clip, clip)
        results = self.d / "results.json"
        results.write_text(json.dumps([{"id": "S2", "status": "done", "job": "j1",
                                        "file": str(clip), "seconds": 1}]))
        return r, clip, results

    def test_record_matches_every_clip_that_lands(self):
        r, clip, results = self._run_dir()
        a = run.build_parser().parse_args(["record", str(r), "--results", str(results),
                                           "--no-parity"])
        with env():
            code, out = quiet(run.cmd_record, a)
        self.assertEqual(code, 0, out)
        self.assertIn("S2: clip colour matched", out)
        self.assertTrue((r / "media" / "versions" / "S2-precolour.mp4").is_file())
        rec = json.loads((r / "results.json").read_text())["S2"]
        self.assertTrue(rec["colour"]["matched"])

    def test_the_flag_turns_it_off(self):
        r, clip, results = self._run_dir()
        a = run.build_parser().parse_args(["record", str(r), "--results", str(results),
                                           "--no-parity", "--no-clip-colour"])
        with env():
            code, out = quiet(run.cmd_record, a)
        self.assertEqual(code, 0, out)
        self.assertFalse((r / "media" / "versions").exists())

    def test_the_machine_hand_matches_the_clips_it_makes(self):
        r = self.d / "mh"
        (r / "media").mkdir(parents=True)
        still = r / "media" / "S1-F1.png"

        class FakeDirect:
            @staticmethod
            def motion(prompt, still_, end, out, **kw):
                shutil.copy2(self_clip, out)
                return {"model": MOTION_MODEL, "file": str(out), "task_id": "t"}

        self_clip = self.clip
        items = [{"id": "S1-F1", "kind": "still", "frame_role": "first", "for": "S1",
                  "params": {"prompt": "x"}, "medias": []},
                 {"id": "S2", "kind": "motion", "params": {"prompt": "y", "duration": 1},
                  "medias": [], "start_frame": "S1-F1"}]

        def fake_generate(prompt, refs, out, **kw):
            shutil.copy2(self.ref, out)
            return {"model": STILL_MODEL, "file": str(out)}

        orig_load = run._load

        def patched(name):
            mod = orig_load(name)
            if name == "direct_openai":
                mod.generate = fake_generate
            if name == "direct_byteplus":
                mod.motion = FakeDirect.motion
            return mod

        reg = run.platform.registry()
        motion_door = dict((reg.get("doors") or {}).get("motion") or {})
        run._load = patched
        orig_reg = run.platform.registry
        run.platform.registry = lambda: {**reg, "doors": {**reg.get("doors", {}),
                                                          "motion": {**motion_door, "primary": "direct:byteplus"}}}
        try:
            with env():
                code_out = quiet(lambda: run.run_machine_hand(items, r, dry_run=False, brand="_fixture"))
        finally:
            run._load = orig_load
            run.platform.registry = orig_reg
        manifest = code_out[0]
        self.assertTrue(manifest["S2"]["colour"]["matched"], code_out[1])
        self.assertTrue((r / "media" / "versions" / "S2-precolour.mp4").is_file())


# ======================================================================
# start, end to end, --dry-run

class StartPlansEveryElement(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-el-run-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        cast = self.tmp / "cast" / "the-speaker"
        cast.mkdir(parents=True)
        shutil.copy2(FIX / "cast-root" / "lead" / "voice.json", cast / "voice.json")

    def args(self, banks_root):
        return run.build_parser().parse_args([
            "start", str(BRIEF), "--brand", "_fixture", "--format", "fixture-format",
            "--label", "v14", "--bank", str(FIX / "bank.json"),
            "--runs-root", str(self.tmp), "--cast-root", str(self.tmp / "cast"),
            "--banks", str(banks_root), "--provider", "higgsfield-ui", "--yes", "--dry-run",
            "--composed"])

    def run_dir(self):
        return self.tmp / "video-production" / "_fixture" / "v14"

    def test_the_v14_brief_plans_every_element_into_items_and_plan(self):
        with env():
            code, out = quiet(run.cmd_start, self.args(FIX / "banks"))
        self.assertEqual(code, 0, out)
        r = self.run_dir()
        plan = json.loads((r / "plan.json").read_text())
        self.assertEqual(plan["music"]["bank_id"], "music-mid-warm-104")
        self.assertEqual([c["bank_id"] for c in plan["sfx"]], ["whoosh", "ka-ching"])
        self.assertEqual(plan["layers"]["transitions"], [{"after_scene": "S2", "kind": "whip"}])
        self.assertEqual(len(plan["hooks"]), 2)
        ids = [it["id"] for bf in sorted((r / "batches").glob("*.json"))
               for it in json.loads(bf.read_text())["items"]]
        for want in ("S1-F1", "S1", "S2", "S3-PLATE", "S4-PLATE", "S5-L", "S5-R",
                     "S6", "S6-BG", "S7-PACKSHOT"):
            self.assertIn(want, ids)
        for never in ("S3", "S4", "S5", "S7"):
            self.assertNotIn(never, ids)
        lines = json.loads((r / "lines.json").read_text())
        self.assertEqual(sorted(lines), ["S1", "S2", "S5", "S6"])
        self.assertIn("SUBMIT.md", out)

    def test_the_real_banks_supply_the_brief(self):
        with env():
            code, out = quiet(run.cmd_start, self.args(HERE.parent / "banks"))
        self.assertNotIn("REFUSED music", out)
        self.assertNotIn("REFUSED sfx", out)


if __name__ == "__main__":
    unittest.main()
