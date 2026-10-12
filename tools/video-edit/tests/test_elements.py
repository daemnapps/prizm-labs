"""Every element the edit assembles (ELEMENTS.md): the gate for each new field, line
grouping over plates, cutdown selection, ratio safe zones, hook variant expansion,
the kit join, the sound laying and the naming. No renders, no live runs — every
file is a few bytes in a temp folder."""
import copy, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import assemble as A, compose as C, cutsheet as CS, kit_from_run as K, versions as V  # noqa: E401

DEFAULTS = json.loads((Path(CS.TOOL) / "machine/defaults.json").read_text())
w = lambda t, s, e: {"text": t, "start": s, "end": e}  # noqa: E731


def elements_sheet(root: Path) -> dict:
    """A green sheet with one of every kind, layer, sound and version."""
    for f in ("a.mp4", "b.mp4", "v.mp3", "plate.png", "l.mp4", "r.mp4", "bg.png", "m.mp3", "fx.wav", "tone.wav"):
        (root / f).write_bytes(b"x")
    pic = lambda i, roll, start, dur, **kw: {"id": i, "roll": roll, "src": kw.pop("src", "a.mp4"), "start": start, "duration": dur,  # noqa: E731
                                            "source_start": 0, "scene": kw.pop("scene", i), "why": "x", **kw}
    s = {"meta": {"brand": "t", "label": "t", "width": 1080, "height": 1920, "fps": 30, "format": "talkinghead"}, "controls": copy.deepcopy(DEFAULTS),
         "voice": None, "sfx": [{"id": "sfx1", "src": "fx.wav", "cue": "ding", "at_words": "star", "for": "star"}],
         "music": {"src": "m.mp3", "start": 0, "volume_db": -18, "tempo_bpm": 120},
         "voice_cuts": [{"id": "S4-v1", "src": "v.mp3", "start": 5.0, "duration": 2.0, "source_start": 0, "volume_db": 0}],
         "picture": [pic("S1-1", "a", 0, 2, scene="S1", talks=True, volume_db=0, kind="talking", section="hook", priority=1, opens=True),
                     pic("S1-2", "a", 2, 1.5, scene="S1", talks=True, volume_db=0, kind="talking", section="hook", priority=1, punch=1.07),
                     pic("S3", "a", 3.5, 1.5, src="plate.png", still=True, kind="card", section="problem", priority=3,
                         card={"lines": ["3 WEEKS"], "plan_lines": ["3 WEEKS"], "lands_at": 3.6}),
                     pic("S4", "b", 5.0, 2.0, src="plate.png", still=True, kind="screen", section="proof", priority=2,
                         screen={"surface": "review", "lines": ["Maya", "Great"], "plan_lines": ["Maya", "Great"], "lands_at": 5.1}),
                     pic("S5", "a", 7.0, 2.0, src="l.mp4", kind="split", section="proof", priority=3,
                         split={"left": "l.mp4", "right": "r.mp4", "layout": "side", "labels": ["BEFORE", "AFTER"]}),
                     pic("S6-1", "a", 9.0, 2.0, scene="S6", talks=True, volume_db=0, kind="greenscreen", section="unique-mechanism", priority=2,
                         greenscreen={"background": "bg.png", "layout": "pip"}),
                     pic("S8", "a", 11.0, 2.0, src="plate.png", still=True, kind="endcard", section="call-to-action", priority=1,
                         endcard={"offer_lines": ["40% OFF"], "plan_offer_lines": ["40% OFF"], "cta": "SHOP NOW", "guarantee": "60-day guarantee"})],
         "captions": {"look": "bold-highlight", "words": [w("Stop", .1, .4), w("now.", .5, .9), w("This", 2.1, 2.4), w("works", 2.5, 3.0),
                                                          w("five", 5.2, 5.5), w("star", 5.6, 6.0), w("It", 9.1, 9.3), w("locks", 9.4, 9.9)]},
         "overlays": [{"id": "hook", "kind": "hook", "text": "Hook one", "start": 0, "duration": 3.5, "y_pct": 18}],
         "layers": {"lower_thirds": [{"id": "lt1", "scene": "S6", "name": "Dr. Park", "title": "Dermatologist", "start": 9.25, "duration": 1.5, "y_pct": 52}],
                    "annotations": [{"id": "an1", "scene": "S1", "kind": "circle", "target": "center", "at_words": "works", "place": {"x_pct": 50, "y_pct": 48, "w_pct": 40, "h_pct": 18}, "start": 2.5, "duration": 1.0}],
                    "platform_ui": [{"id": "ui1", "scene": "S1", "kind": "comment_reply", "text": "does it work?", "handle": "@jess", "start": 0, "duration": 3.5, "y_pct": 30}],
                    "transitions": [{"after_scene": "S1", "kind": "whip"}, {"after_scene": "S3", "kind": "flash"}],
                    "disclaimers": [{"id": "dc1", "claim": "results", "scene": "S4", "text": "Results vary.", "start": 5.0, "duration": 2.0, "zone": "fine-print"}]},
         "room_tone": [{"id": "tone1", "src": "tone.wav", "start": 1.8, "duration": 0.4, "volume_db": -30}],
         "room_tone_needed": {"joins": 1, "spans": 1},
         "compliance": {"file": "x/compliance.json", "claims": ["results"], "rows": {"results": "Results vary."}, "unfilled": []},
         "hooks": [{"id": "h1", "text": "Hook one"}, {"id": "h2", "text": "Hook two", "opener_scene": "S4"}],
         "versions": {"hooks": True, "cutdowns": [15, 30, 60], "ratios": ["9x16"], "cover": True},
         "grade": "phone-natural", "mix": {"lufs": -14, "true_peak_db": -1}, "name": {}, "unmade": [], "elements": True}
    s["music"]["duck"] = {"under_db": 18, "gap_db": -10, "points": [{"t": 0, "v": 0.126}]}
    s["sfx"][0]["at"] = 5.6
    return s


class ElementGate(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = Path(self.t.name); self.s = elements_sheet(self.root)
    def tearDown(self): self.t.cleanup()
    def red(self, s=None): return CS.check(s or self.s, self.root, probe=lambda p: 30.0)
    def has(self, needle, s=None):
        r = self.red(s); self.assertTrue(any(needle in x for x in r), f"no `{needle}` in {r}")
    def pic(self, i): return next(p for p in self.s["picture"] if p["id"] == i)

    def test_green(self): self.assertEqual(self.red(), [])
    def test_unknown_kind(self): self.pic("S3")["kind"] = "poster"; self.has("not a scene kind")
    def test_card_words_must_match_the_plan(self): self.pic("S3")["card"]["lines"] = ["3 WEEKS!"]; self.has("word for word")
    def test_card_needs_plan_lines(self): del self.pic("S3")["card"]["plan_lines"]; self.has("plan_lines is missing")
    def test_card_empty(self): self.pic("S3")["card"].update(lines=[], plan_lines=[]); self.has("card.lines is empty")
    def test_card_lands_on_unheard(self): self.pic("S3")["card"].update(lands_on="never", lands_on_unheard=True); self.has("never said")
    def test_screen_surface(self): self.pic("S4")["screen"]["surface"] = "tweet"; self.has("not a surface")
    def test_split_layout(self): self.pic("S5")["split"]["layout"] = "diagonal"; self.has("not a layout")
    def test_split_side_missing(self): self.pic("S5")["split"]["right"] = "gone.mp4"; self.has("split.right not found")
    def test_split_labels(self): self.pic("S5")["split"]["labels"] = ["A", "B", "C"]; self.has("up to two")
    def test_greenscreen_must_talk(self): self.pic("S6-1")["talks"] = False; self.has("presenter talking")
    def test_greenscreen_background(self): self.pic("S6-1")["greenscreen"]["background"] = "gone.png"; self.has("greenscreen.background not found")
    def test_endcard_cta(self): self.pic("S8")["endcard"]["cta"] = ""; self.has("endcard.cta is missing")
    def test_endcard_guarantee(self): self.pic("S8")["endcard"]["guarantee"] = None; self.has("guarantee is missing")
    def test_endcard_offer_match(self): self.pic("S8")["endcard"]["offer_lines"] = ["50% OFF"]; self.has("offer_lines do not match")
    def test_lower_third_name(self): self.s["layers"]["lower_thirds"][0]["name"] = ""; self.has("lower_thirds[0]: no name")
    def test_layer_runtime_bounds(self): self.s["layers"]["lower_thirds"][0]["start"] = 12.5; self.has("runs outside the video")
    def test_layer_not_placed(self): self.s["layers"]["lower_thirds"][0].update(start=None, scene="S9"); self.has("never placed on the clock")
    def test_layer_safe_zone(self): self.s["layers"]["lower_thirds"][0]["y_pct"] = 90; self.has("buttons cover")
    def test_annotation_kind(self): self.s["layers"]["annotations"][0]["kind"] = "star"; self.has("annotations[0]: kind")
    def test_annotation_target(self): self.s["layers"]["annotations"][0]["place"] = None; self.has("not a place on the frame")
    def test_annotation_words_unheard(self): self.s["layers"]["annotations"][0]["start"] = None; self.has("are never said in S1")
    def test_platform_ui_kind(self): self.s["layers"]["platform_ui"][0]["kind"] = "poll"; self.has("platform_ui[0]: kind")
    def test_platform_ui_text_and_handle(self):
        self.s["layers"]["platform_ui"][0].update(text="", handle=""); r = self.red()
        self.assertTrue(any("with no text" in x for x in r) and any("with no handle" in x for x in r))
    def test_transition_kind(self): self.s["layers"]["transitions"][0]["kind"] = "spin"; self.has("not a transition")
    def test_transition_after_last(self): self.s["layers"]["transitions"][0]["after_scene"] = "S8"; self.has("the last scene")
    def test_transition_unknown_scene(self): self.s["layers"]["transitions"][0]["after_scene"] = "S9"; self.has("is not in the cut")
    def test_disclaimer_file_missing(self): self.s["compliance"]["file"] = None; self.has("compliance.json does not exist")
    def test_disclaimer_unfilled(self): self.s["compliance"]["unfilled"] = ["results"]; self.has("no disclaimer in compliance.json")
    def test_hook_ids_unique(self): self.s["hooks"][1]["id"] = "h1"; self.has("hooks: an id is used twice")
    def test_hook_opener_scene(self): self.s["hooks"][1]["opener_scene"] = "S9"; self.has("opener_scene `S9`")
    def test_hook_on_frame_one(self): self.s["overlays"][0]["start"] = 0.4; self.has("on screen from frame one")
    def test_music_tempo(self): self.s["music"]["tempo_bpm"] = None; self.has("no tempo_bpm")
    def test_music_duck(self): self.s["music"]["duck"]["under_db"] = 10; self.has("the rule is 18")
    def test_music_too_short(self): self.assertTrue(any("the track is" in r for r in CS.check(self.s, self.root, probe=lambda p: 5.0)))
    def test_sfx_never_lands(self): self.s["sfx"][0]["at"] = None; self.has("never lands")
    def test_room_tone_needed(self): self.s["room_tone"] = []; self.has("no room-tone bed")
    def test_versions(self):
        self.s["versions"].update(cutdowns=[20], ratios=["9x16", "4x5"]); r = self.red()
        self.assertTrue(any("cutdowns: 20" in x for x in r) and any("ratios: 4x5 — 9:16 only" in x for x in r))
    def test_grade(self): self.s["grade"] = "teal-orange"; self.has("not a grade")
    def test_unmade(self): self.s["unmade"] = ["S7: split side not made"]; self.has("unmade: S7")
    def test_sound_rules_only_bind_an_elements_sheet(self):
        self.s["elements"] = False; self.s["room_tone"] = []; self.s["music"]["tempo_bpm"] = None
        self.assertEqual(self.red(), [])


class Lines(unittest.TestCase):
    def test_captions_step_aside_for_a_plates_own_words(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); s = elements_sheet(root)
            s["captions"]["words"].append(w("card", 3.7, 4.0))  # said while the card is up
            page = C.compose(s, root, root / "proj").read_text()
            self.assertIn('id="S3-card-l0"', page)          # the card's line, set as its own block
            self.assertNotIn(">card<", page)                  # and no caption line over it
            self.assertIn(">Stop<", page)                     # captions elsewhere are untouched
            self.assertNotIn("<br", page)                     # no <br> in body text (HyperFrames rule)
            self.assertIn("data-automation", page)            # the music's duck lane and the room tone's fades
            self.assertIn("filter:contrast", page)            # one grade over the picture

    def test_screen_lines_are_one_block_each(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); page = C.compose(elements_sheet(root), root, root / "proj").read_text()
            self.assertIn('id="S4-screen-l0"', page); self.assertIn('id="S4-screen-l1"', page)


class Cutdowns(unittest.TestCase):
    def sheet(self):
        d = tempfile.mkdtemp(); return elements_sheet(Path(d))
    def test_lowest_priority_whole_scenes_first(self):
        order, dropped, tot, fits = V.cutdown(self.sheet(), 8)
        self.assertEqual(dropped[:2], ["S5", "S3"])        # priority 3, the later one first
        self.assertIn("S1", order); self.assertIn("S8", order)  # priority 1 and the opener never come out
        self.assertTrue(fits); self.assertLessEqual(tot, 8)
    def test_never_mid_scene(self):
        order, _, _, _ = V.cutdown(self.sheet(), 8)
        s = V.retime(self.sheet(), order)
        kept = {p.get("scene") or p["id"] for p in s["picture"]}
        self.assertEqual(kept, set(order))
        self.assertEqual({p["id"] for p in s["picture"] if p.get("scene") == "S1"}, {"S1-1", "S1-2"})  # both parts of the line
    def test_cannot_fit_says_so(self):
        _, _, tot, fits = V.cutdown(self.sheet(), 1)
        self.assertFalse(fits); self.assertGreater(tot, 1)
    def test_plan_skips_cutdowns_longer_than_the_piece(self):
        ids = [x["id"] for x in V.plan(self.sheet())]
        self.assertNotIn("h1-15s", ids)                    # the piece is 13 s — a 15 s cutdown is the piece
        self.assertNotIn("h1-60s", ids)
    def test_only_hooks_and_cutdowns_are_rendered(self):
        s = self.sheet(); s["versions"]["cutdowns"] = [8]
        self.assertEqual([x["id"] for x in V.plan(s)], ["h1-full", "h2-full", "h1-8s"])  # no section swaps, no other ratios


class Hooks(unittest.TestCase):
    def test_one_version_per_hook_same_body(self):
        s = elements_sheet(Path(tempfile.mkdtemp()))
        full = [x for x in V.plan(s) if x["length"] == "full"]
        self.assertEqual([x["hook"]["id"] for x in full], ["h1", "h2"])
        self.assertEqual(sorted(full[0]["order"]), sorted(full[1]["order"]))  # the same body
        self.assertEqual(full[1]["order"][0], "S4")                            # h2 opens on its own scene
        v = V.variant(s, full[1])
        hook = next(o for o in v["overlays"] if o["kind"] == "hook")
        self.assertEqual((hook["text"], hook["start"]), ("Hook two", 0))      # on frame one
        self.assertEqual(round(hook["duration"], 3), 2.0)                     # lives as long as its opener


class Join(unittest.TestCase):
    def test_kit_reads_every_kind(self):
        with tempfile.TemporaryDirectory() as d:
            vm = Path(d); (vm / "media").mkdir(); (vm / "vo").mkdir()
            for f in ("media/S1.mp4", "media/S3-PLATE.png", "media/S4-PLATE.png", "vo/S4.mp3", "media/S5-L.mp4", "media/S5-R.mp4",
                      "media/S6.mp4", "media/S6-BG.png", "media/S8-PACKSHOT.png", "tone.wav", "m.mp3"):
                (vm / f).write_bytes(b"x")
            ok = {"verdict": "PASS"}
            (vm / "verdicts.json").write_text(json.dumps({s: {"motion": ok, "director": ok, "parity": ok} for s in ("S1", "S5", "S6")}))
            (vm / "run.json").write_text(json.dumps({"brand": "t", "label": "t"}))
            (vm / "plan.json").write_text(json.dumps({"scenes": [
                {"id": "S1", "type": "A", "to_camera": True, "opens": True, "section": "Hook", "priority": 1},
                {"id": "S3", "kind": "card", "card": {"lines": ["3 WEEKS"], "plate": "lilac"}},
                {"id": "S4", "kind": "screen", "claims": ["results"], "screen": {"surface": "review", "lines": ["Maya"], "lands_on": "star"}},
                {"id": "S5", "kind": "split", "module": "mechanism", "split": {"layout": "wipe", "labels": ["A", "B"]}},
                {"id": "S6", "kind": "greenscreen", "to_camera": True, "greenscreen": {"talker_scene": "S6", "layout": "cutout"}},
                {"id": "S7", "kind": "screen", "screen": {"surface": "dm", "lines": ["hi"]}},
                {"id": "S8", "kind": "endcard", "endcard": {"offer_lines": ["40% OFF"], "cta": "SHOP", "guarantee": "none"}}],
                "layers": {"lower_thirds": [{"scene": "S6", "name": "Dr"}]},
                "music": {"bank_id": "m1", "file": str(vm / "m.mp3"), "tempo_bpm": 100},
                "sfx": [{"cue": "room-tone-kitchen", "bank_id": "room-tone-kitchen", "file": str(vm / "tone.wav")},
                        {"cue": "ding", "bank_id": "d1", "file": "nowhere.wav", "scene": "S3"}],
                "hooks": [{"id": "h1", "text": "one"}], "versions": {"cutdowns": [15]}}))
            kit, notes = K.build(vm)
            by = {c["id"]: c for c in kit["clips"]}
            self.assertEqual({k: by[k]["kind"] for k in by}, {"S1": "talking", "S3": "card", "S4": "screen", "S5": "split", "S6": "greenscreen", "S8": "endcard"})
            self.assertEqual(by["S3"]["card"]["plan_lines"], ["3 WEEKS"])
            self.assertTrue(by["S8"]["src"].endswith("S8-PACKSHOT.png"))     # the endcard is the real packshot's edit
            self.assertEqual(by["S4"]["roll"], "b")                          # a plate over its voice slice
            self.assertIn("hold", by["S3"])                                  # a silent plate holds
            self.assertTrue(any("S7" in u for u in kit["unmade"]))           # no plate made → named, never skipped silently
            self.assertTrue(any("ding" in u for u in kit["unmade"]))         # a bank file that is not here
            self.assertEqual(len(kit["room_tone"]), 1); self.assertEqual(kit["sfx"], [])
            self.assertEqual(kit["music"]["tempo_bpm"], 100)
            self.assertEqual(by["S5"]["section"], "unique-mechanism")      # the old `module` read as an alias of the doctrine's id
            self.assertIsNone(by["S3"]["section"])                        # never required
            self.assertNotIn("module", by["S1"])
            self.assertTrue(by["S1"]["opens"]); self.assertEqual(by["S1"]["section"], "hook")


class Sound(unittest.TestCase):
    def test_lays_music_under_the_voice_on_the_bar_and_tone_in_the_joins(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); s = elements_sheet(root)
            s["room_tone_src"] = {"src": "tone.wav"}; A.sound(s)
            m = s["music"]; end = 13.0
            self.assertEqual(m["duck"]["under_db"], 18)
            self.assertAlmostEqual((m["source_start"] + end) % 2.0, 0.0, places=2)   # 120 bpm: a bar is 2 s — the end lands on one
            self.assertTrue(any(r["start"] <= 1.8 and r["start"] + r["duration"] >= 2.2 for r in s["room_tone"]))  # the trimmed pause at 2.0 s is filled
            self.assertLessEqual(len(m["duck"]["points"]), 512)
    def test_assemble_times_every_layer_and_reads_compliance(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); s = elements_sheet(root)
            (root / "brands" / "t").mkdir(parents=True)
            (root / "brands/t/brand-identity").mkdir(parents=True); (root / "brands/t/brand-identity/compliance.json").write_text(json.dumps({"claims": {"results": {"text": "Results vary.", "platforms": ["meta"]}}}))
            for k in ("layers", "sfx", "compliance", "hooks"):
                s.pop(k, None)
            s["sfx"] = [{"id": "sfx1", "src": "fx.wav", "at_words": "star", "for": "star"}]
            kit = {"clips": [{"id": "S1", "kind": "talking"}, {"id": "S4", "kind": "screen", "claims": ["results"]}], "hooks": [], "unmade": [],
                   "layers": {"annotations": [{"scene": "S1", "kind": "circle", "target": "center", "at_words": "works"}],
                              "lower_thirds": [{"scene": "S6", "name": "Dr"}]}, "platform": "meta", "room_tone": [{"src": "tone.wav"}]}
            A.assemble(s, kit, DEFAULTS, "t", root=root)
            self.assertEqual(s["sfx"][0]["at"], 5.6)
            self.assertEqual(s["layers"]["annotations"][0]["start"], 2.5)
            self.assertEqual(s["layers"]["lower_thirds"][0]["start"], 9.25)
            self.assertEqual([x["text"] for x in s["layers"]["disclaimers"]], ["Results vary."])
            self.assertEqual(s["layers"]["disclaimers"][0]["start"], 5.0)
            A.assemble(s, kit, DEFAULTS, "nobrand", root=root)
            self.assertIsNone(s["compliance"]["file"]); self.assertEqual(s["compliance"]["unfilled"], ["results"])


class Naming(unittest.TestCase):
    def test_missing_fields_are_never_invented(self):
        s = elements_sheet(Path(tempfile.mkdtemp()))
        name, note = V.file_name(s, "4x5", 2, "260923a")
        self.assertEqual(name, "t-full-4x5"); self.assertIn("product", note)
    def test_named_to_the_convention(self):
        s = elements_sheet(Path(tempfile.mkdtemp()))
        s["name"] = {"product": "balm", "talent": "none", "avatar": "tight", "problem": "dry", "angle": "fix", "concept": "stop", "brief": "p1"}
        name, note = V.file_name(s, "1x1", 3, "260923a")
        self.assertIsNone(note)
        # the convention's written (new) form — components/naming/names.py:11-23, locked 2026-09-28
        self.assertEqual(name, "t_balm_video_ai_none_tight_dry_fix_stop_talkinghead_p1_1x1_batch-2026-09-23-a_asset-03")


if __name__ == "__main__":
    unittest.main()
