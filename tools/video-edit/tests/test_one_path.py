"""Video system sync 2026-10-21 (worker 3, edit v2): one edit path, captions by format and never on a face or a mouth,
production's word times, the audit on every version, nothing mechanical, sound only when called for, the realism
finish. Each test names the row of runs/video-system/sync/2026-10-21/CHANGES.md and the ruling it holds the code to."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import assemble as A  # noqa: E402
import audit as AU  # noqa: E402
import compose as C  # noqa: E402
import kit_from_run as K  # noqa: E402
import looks as LK  # noqa: E402
import map_sheet as MS  # noqa: E402
import placement as P  # noqa: E402
import realism as RL  # noqa: E402
import retention as RT  # noqa: E402
import run as R  # noqa: E402

DEFAULTS = json.loads((Path(__file__).resolve().parents[1] / "machine" / "defaults.json").read_text())


def w(t, s, e):
    return {"text": t, "start": s, "end": e}


class OneRegistry(unittest.TestCase):
    """E6, E7 · V13: one caption registry, the look picked by format, else by app, else the app-native default."""

    def test_by_format_then_app_then_default(self):
        self.assertEqual(LK.pick_caption("remedy-reel", "tiktok"), "edits-glow")
        self.assertEqual(LK.pick_caption("song-ad"), "word-box")
        self.assertEqual(LK.pick_caption("micro-drama", "tiktok"), "tiktok-native")
        self.assertEqual(LK.pick_caption("micro-drama", "instagram-reels"), "ig-fb-native")
        self.assertEqual(LK.pick_caption(None, None), "ig-fb-native")

    def test_every_picked_look_is_a_row_and_the_default_sits_low(self):
        p = LK.bank()["pick"]
        for look in list(p["by_format"].values()) + list(p["by_app"].values()) + [p["default"]]:
            self.assertIsNotNone(LK.caption(look), look)
        self.assertEqual(LK.caption(p["default"])["zone"], "caption-band")
        glow = LK.caption("edits-glow")
        self.assertEqual((glow["prefer_y_pct"], glow["max_bottom_pct"]), (38, 56))
        self.assertIn("neck", glow["what"])
        self.assertNotIn("centred on the chest", glow["what"])

    def test_the_line_paths_old_registry_holds_only_stubs(self):
        L = json.loads((LK.TOOL / "looks" / "edit-looks.json").read_text())
        self.assertNotIn("mix", L)
        self.assertNotIn("captions", L["defaults"])
        for row in L["captions"].values():
            self.assertEqual(set(row), {"_see"})

    def test_one_loudness_table(self):
        s = LK.sound()
        self.assertEqual((s["music_db"], s["music_gap_db"], s["room_tone_db"], s["lufs"], s["true_peak_db"]), (-18, -12, -50, -14, -1))


class TheClock(unittest.TestCase):
    """E17, E19, E20 · V15: a take laid whole, the cut between takes; no punch-in by itself."""
    words = [w("One", 0.2, 0.5), w("two", 0.7, 1.0), w("three", 1.3, 1.6), w("four", 2.1, 2.4), w("five", 2.8, 3.1)]

    def cut(self, controls):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "a.mp4").write_bytes(b"x"); (root / "b.mp4").write_bytes(b"x")
            kit = {"format": "remedy-reel", "clips": [
                {"id": "S1", "scene": "S1", "src": "a.mp4", "roll": "a", "talks": True, "approved": True, "words": self.words},
                {"id": "S2", "scene": "S2", "src": "b.mp4", "roll": "a", "talks": True, "approved": True, "words": self.words}]}
            return R.auto_cut(kit, root, root, controls, "t", "t", level=False)

    def test_default_lays_each_take_whole_with_no_punch(self):
        s = self.cut(copy.deepcopy(DEFAULTS))
        self.assertEqual([c["id"] for c in s["picture"]], ["S1-1", "S2-1"])          # one piece per take
        self.assertTrue(all("punch" not in c for c in s["picture"]))
        self.assertTrue(all(p["action"] == "kept" for p in s["pauses"]))            # marked for review, never cut
        self.assertEqual(s["captions"]["look"], "edits-glow")                      # the format's look, no controls needed

    def test_a_run_that_names_a_pace_still_gets_it(self):
        ctl = copy.deepcopy(DEFAULTS); ctl["pace"]["value"] = "tight"
        s = self.cut(ctl)
        self.assertGreater(len(s["picture"]), 2)
        self.assertTrue(all("punch" not in c for c in s["picture"]))              # cut, but never punched by itself

    def test_pace_and_moves_per_format(self):
        self.assertIsNone(LK.pace("remedy-reel")["max_pause"])
        m = LK.moves("remedy-reel")
        self.assertFalse(m["push_stills"]); self.assertEqual(m["punch"], "swipe")


class SoundOnlyWhenCalled(unittest.TestCase):
    """E24, E25 · V14 / C10: room tone only when the swipe or brief calls for it."""

    def sheet(self, **kw):
        return {"controls": {"sound": DEFAULTS["sound"]}, "captions": {"words": [w("a", 0.1, 0.5), w("b", 2.0, 2.4)]},
                "picture": [{"id": "A-1", "src": "a.mp4", "start": 0, "duration": 1.0, "talks": True},
                            {"id": "A-2", "src": "a.mp4", "start": 1.0, "duration": 2.0, "talks": True}], **kw}

    def test_not_called_no_bed_and_no_red(self):
        s = A.sound(self.sheet())
        self.assertEqual(s["room_tone"], [])
        self.assertEqual(s["room_tone_needed"]["joins"], 0)

    def test_called_without_a_file_still_needs_one(self):
        s = A.sound(self.sheet(room_tone_called=True))
        self.assertGreater(s["room_tone_needed"]["joins"] + s["room_tone_needed"]["spans"], 0)
        self.assertEqual(s["room_tone"], [])                                        # the gate names it red

    def test_called_with_a_file_is_laid_at_the_one_level(self):
        s = A.sound(self.sheet(room_tone_src={"src": "tone.wav"}))
        self.assertTrue(s["room_tone"]); self.assertEqual(s["room_tone"][0]["volume_db"], -50)


class Placement(unittest.TestCase):
    """E1–E4, C1 · V13: every caption look holds its own height and moves only off a face or a mouth."""

    def sheet(self, look, box=None):
        pic = {"id": "S1-1", "scene": "S1", "roll": "a", "src": "a.mp4", "start": 0, "duration": 3, "talks": True}
        if box:   # a face READ off the picture (faces.read_scenes — Vision's box, brows to chin)
            pic["scene_read"] = [{"t": t, "faces": [box], "lips": [], "hands": [], "salient": []} for t in (0.3, 1.5, 2.7)]
        return {"picture": [pic], "captions": {"look": look, "words": [w("hi", 0.1, 0.4)]}, "overlays": [], "layers": {}}

    def test_bottom_default_holds_the_band_when_nothing_is_under_it(self):
        s = P.place(self.sheet("ig-fb-native", {"x": 30, "y": 20, "w": 40, "h": 15}))
        z = s["captions"]["zones"]["S1"]
        self.assertEqual(z["zone"], "caption-band"); self.assertEqual(z["box"]["y"], P.zones()["caption-band"]["y"])
        self.assertEqual(s["placement"], [])

    def test_edits_glow_aims_at_the_neck_and_leaves_a_face(self):
        free = P.place(self.sheet("edits-glow", {"x": 30, "y": 10, "w": 40, "h": 24}))   # chin at 34%: the neck (38%) is clear
        self.assertEqual(free["captions"]["zones"]["S1"]["box"]["y"], 38)
        low = P.place(self.sheet("edits-glow", {"x": 25, "y": 30, "w": 50, "h": 18}))     # a face across 38%
        bx = low["captions"]["zones"]["S1"]["box"]
        self.assertTrue(bx["y"] >= 48 or bx["y"] + bx["h"] <= 30, bx)                   # clear of the face, chin to brows
        self.assertLessEqual(bx["y"] + bx["h"], 56 + 0.01)                               # never below max_bottom_pct

    def test_a_fixed_overlay_keeps_the_height_its_maker_set(self):
        s = self.sheet("ig-fb-native")
        s["overlays"] = [{"id": "h", "kind": "hook", "text": "x", "start": 0, "duration": 2, "y_pct": 4, "fixed": True}]
        P.place(s)
        self.assertNotIn("box", s["overlays"][0]); self.assertEqual(s["overlays"][0]["y_pct"], 4)


class CaptionRoom(unittest.TestCase):
    """2026-10-21, found on the proof render: a caption box the height of the whole zone pushed captions under the
    headline; words and items on screen are kept clear, below a face in weight."""

    def test_a_caption_is_as_tall_as_its_type(self):
        Z = P.zones()["caption-band"]
        self.assertLess(P.caption_h(LK.caption("ig-fb-native"), Z), 6)          # one line of 50 px type
        self.assertEqual(P.caption_h(LK.caption("edits-glow"), P.zones()["center"]), P.zones()["center"]["h"])   # two lines: the zone

    def test_an_item_is_kept_clear_but_a_face_outranks_it(self):
        s = {"picture": [{"id": "S1-1", "scene": "S1", "roll": "a", "src": "a.mp4", "start": 0, "duration": 3,
                          "subject_box": {"x": 30, "y": 20, "w": 40, "h": 25}}],
             "captions": {"look": "ig-fb-native", "words": [w("hi", 0.1, 0.4)]}, "overlays": [], "layers": {},
             "keep_clear": [{"box": [30, 60, 70, 70], "start": 0, "end": 3, "what": "item"}]}
        bx = P.place(s)["captions"]["zones"]["S1"]["box"]
        self.assertFalse(bx["y"] < 70 and bx["y"] + bx["h"] > 60, bx)            # off the item
        self.assertFalse(bx["y"] < 45 and bx["y"] + bx["h"] > 20, bx)            # and never onto the face to do it
        self.assertLessEqual(bx["y"] + bx["h"], P.safe_box()[3] + 0.01)          # above the feed's buttons


class Audit(unittest.TestCase):
    """E8, E12–E15, E26."""

    def test_a_word_chopped_at_a_cut_is_found(self):
        sheet = {"captions": {"words": [w("cut", 0.9, 1.3)]},
                 "picture": [{"id": "A", "src": "a.mp4", "start": 0, "duration": 1.1, "source_start": 0, "talks": True},
                             {"id": "B", "src": "b.mp4", "start": 1.1, "duration": 1.0, "source_start": 0, "talks": True}]}
        got = AU.audit_sheet(sheet, Path("."), Path("/nonexistent.mp4"))
        self.assertEqual([f["check"] for f in got["found"]], ["WORD CUT"])

    def test_the_same_take_running_on_is_no_edge(self):
        sheet = {"captions": {"words": [w("on", 0.9, 1.3)]},
                 "picture": [{"id": "A-1", "src": "a.mp4", "start": 0, "duration": 1.1, "source_start": 0, "talks": True},
                             {"id": "A-2", "src": "a.mp4", "start": 1.1, "duration": 1.0, "source_start": 1.1, "talks": True}]}
        self.assertEqual(AU.audit_sheet(sheet, Path("."), Path("/nonexistent.mp4"))["found"], [])

    def test_the_swipes_sound_missing_fails(self):
        self.assertEqual([f["check"] for f in AU.sound_called_for({"what": "lo-fi bed"}, [{"what": "whoosh"}], [], False)],
                         ["NO MUSIC", "NO SOUND FX"])
        self.assertEqual(AU.sound_called_for({"what": "none"}, [], [], False), [])
        self.assertEqual(AU.sound_called_for({}, [], [], False, {"music": "upbeat"})[0]["check"], "NO MUSIC")

    def test_a_caption_over_a_mouth_is_measured(self):
        cap = (20.0, 40.0, 80.0, 50.0)
        self.assertGreater(AU._cover(cap, (40.0, 44.0, 60.0, 48.0)), 0)         # a mouth inside the words' box
        self.assertEqual(AU._cover(cap, (30.0, 10.0, 70.0, 38.0)), 0.0)         # a face above it: clear

    def test_caption_boxes_follow_the_placed_zone(self):
        sheet = {"picture": [{"id": "S1-1", "scene": "S1", "roll": "a", "start": 0, "duration": 3}],
                 "captions": {"look": "ig-fb-native", "words": [w("one", 0.1, 0.3), w("two", 0.35, 0.6)],
                              "zones": {"S1": {"zone": "caption-band", "box": {"x": 15, "y": 50, "w": 70, "h": 9}}}},
                 "overlays": []}
        bx = AU.caption_boxes(sheet)
        self.assertEqual(len(bx), 1); self.assertEqual(bx[0]["box"][1], 50)
        self.assertLess(bx[0]["box"][2] - bx[0]["box"][0], 70)                   # the words' own width, not the band

    def test_a_caption_under_the_headline_is_found(self):
        sheet = {"picture": [{"id": "s0", "scene": "s0", "roll": "a", "start": 0, "duration": 3}],
                 "captions": {"look": "ig-fb-native", "words": [w("one", 0.1, 0.3), w("two", 0.35, 0.6)],
                              "zones": {"s0": {"zone": "top-headline", "box": {"x": 15, "y": 19, "w": 70, "h": 5}}}},
                 "overlays": [], "keep_clear": [{"box": [20, 16, 80, 24], "start": 0, "end": 3, "what": "hook headline"}]}
        got = AU.words_off_faces(sheet, Path("/nonexistent.mp4"))
        self.assertEqual([f["check"] for f in got], ["WORDS ON WORDS"])

    def test_every_version_is_listed(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            for n in ("edit-map.json", "edit-map-H1.json", "edit-map-H2.json"):
                (out / n).write_text("{}")
            self.assertEqual(list(AU.versions(out)), ["control", "H1", "H2"])


class ProductionWordTimes(unittest.TestCase):
    """E9, E10: production's own word times reach the captions; nothing is transcribed again."""

    def test_take_and_slice_words(self):
        with tempfile.TemporaryDirectory() as d:
            vm = Path(d)
            (vm / "media").mkdir(); (vm / "clips" / "calls" / "G1").mkdir(parents=True)
            (vm / "media" / "S1.mp4").write_bytes(b"abcdef"); (vm / "clips" / "G1.mp4").write_bytes(b"abcdef")
            (vm / "clips" / "plan.json").write_text(json.dumps({"calls": [{"id": "G1", "lines": [{"scene": "S1"}]}]}))
            (vm / "clips" / "calls" / "G1" / "transcript-words.json").write_text(json.dumps(
                [{"text": "Hi", "start": 0.2, "end": 0.4, "type": "word"}, {"text": " ", "start": 0.4, "end": 0.5, "type": "spacing"}]))
            self.assertEqual(K.take_words(vm, "S1", vm / "media" / "S1.mp4"), [w("Hi", 0.2, 0.4)])
            timing = {"S2": {"start": 3.0, "lines": [{"words": [{"text": "so", "start": 3.5, "end": 3.7}]}]}}
            self.assertEqual(K.slice_words(timing, "S2"), [w("so", 0.5, 0.7)])
            self.assertIsNone(K.slice_words({"S3": {"lines": [{"text": "x"}]}}, "S3"))

    def test_a_map_line_takes_the_clips_own_times(self):
        with tempfile.TemporaryDirectory() as d:
            vm = Path(d); (vm / "clips" / "calls" / "G1").mkdir(parents=True)
            (vm / "clips" / "calls" / "G1" / "transcript-words.json").write_text(json.dumps(
                [{"text": "never", "start": 1.0, "end": 1.3}, {"text": "again", "start": 1.4, "end": 1.8}, {"text": "after", "start": 2.6, "end": 2.9}]))
            line = {"kind": "in clip", "clip": "G1", "in": 0.9, "len": 1.0, "a": 10.0, "b": 11.0, "text": "Never again."}
            got, by = MS.line_words(vm, line, None)
            self.assertEqual(by, "production")
            self.assertEqual([x["text"] for x in got], ["Never", "again."])           # the script's spelling
            self.assertEqual([x["start"] for x in got], [10.1, 10.5])                # on the cut's clock


class HandOffsAndRealism(unittest.TestCase):
    """E28, E29 · V9, V10."""

    def test_whip_and_match_from_the_shot_contract(self):
        with tempfile.TemporaryDirectory() as d:
            vm = Path(d)
            (vm / "plan.json").write_text(json.dumps({"scenes": [{"id": "S1", "hands_off": "whip"}, {"id": "S2", "hands_off": "continuous"}]}))
            self.assertEqual(MS.hand_offs(vm), {"S1": "whip", "S2": "continuous"})
            self.assertEqual(MS.DRAWN.get("continuous"), None)

    def test_the_brief_v3_shots_carry_the_hand_off_and_the_emphasis(self):
        sc = {"id": "S3", "shots": [{"id": "S3.1", "hands_off": "continuous", "lines": [{"say": "Crack one egg.", "emphasis": ["egg"]}]},
                                    {"id": "S3.2", "hands_off": "whip", "lines": [{"say": "Whisk it.", "emphasis": ["Whisk"]}]}]}
        self.assertEqual(K.scene_hands_off(sc), "whip")                  # the scene's last shot hands it on
        self.assertEqual(K.scene_emphasis(sc), ["egg", "Whisk"])
        self.assertEqual(K.scene_emphasis({"id": "S1"}), [])
        with tempfile.TemporaryDirectory() as d:
            vm = Path(d)
            (vm / "plan.json").write_text(json.dumps({"scenes": [sc], "layers": {"transitions": [{"after_scene": "S4", "kind": "match"}]}}))
            self.assertEqual(MS.hand_offs(vm), {"S3": "whip", "S4": "match"})

    def test_realism_rows_by_filming_format(self):
        rows = {r["id"] for r in RL.editing_rows()}
        self.assertEqual(rows, set(RL.DRAWN))                                     # the 7 editing rows, all drawn
        self.assertEqual(set(RL.pick()["rows"]), {"phone-grain", "app-native-captions"})
        self.assertEqual(set(RL.pick(kit={"piece": {"filming": "selfie-talk", "realism_level": 2}})["rows"]),
                         {"phone-grain", "crooked-hold", "digital-micro-shake", "reframe-nudge", "app-native-captions"})
        self.assertEqual(RL.pick(kit={"piece": {"realism": ["exposure-shift"]}})["rows"], ["exposure-shift"])

    def test_a_subject_off_centre_gets_the_nudge(self):
        sh = {"realism": {"rows": ["reframe-nudge"]},
              "picture": [{"id": "a", "scene_read": [{"t": 0, "faces": [{"x": 60, "y": 20, "w": 20, "h": 20}]}]},
                          {"id": "b", "scene_read": [{"t": 0, "faces": [{"x": 40, "y": 20, "w": 20, "h": 20}]}]}]}
        RL.mark(sh, Path("."))
        self.assertLess(sh["picture"][0]["reframe_dx"], 0)              # the face sits right: the frame moves toward it
        self.assertNotIn("reframe_dx", sh["picture"][1])                  # centred: left alone

    def test_the_crooked_hold_tilts_only_inside_a_swipe_punch(self):
        self.assertEqual(C.tilt_room(1.0), 0.0)
        self.assertGreater(C.tilt_room(1.07), 0.7)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "a.mp4").write_bytes(b"x")
            sheet = {"meta": {"brand": "t", "label": "t", "width": 1080, "height": 1920, "fps": 30, "format": None},
                     "picture": [{"id": "s000", "roll": "a", "src": "a.mp4", "start": 0, "duration": 2, "source_start": 0, "scene": "s000", "punch": 1.07}],
                     "captions": {"look": "ig-fb-native", "words": []}, "overlays": [], "layers": {},
                     "realism": {"rows": ["crooked-hold"]}}
            page = C.compose(sheet, root, root / "p").read_text()
            self.assertIn("rotation", page); self.assertIn("scale:1.07", page)   # inside the punch, no extra zoom
            self.assertNotIn('"#picture",{rotation', page)

    def test_a_map_sheet_never_scales_the_punch_twice(self):
        src = (Path(__file__).resolve().parent.parent / "machine" / "map_sheet.py").read_text()
        self.assertNotIn('{"punch": float(s["scale"])}', src)              # the punch is baked in render_map once

    def test_compose_draws_the_finish_the_looks_and_a_badge(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "a.mp4").write_bytes(b"x")
            sheet = {"meta": {"brand": "t", "label": "t", "width": 1080, "height": 1920, "fps": 30, "format": None},
                     "picture": [{"id": "s000", "roll": "a", "src": "a.mp4", "start": 0, "duration": 2, "source_start": 0, "scene": "s000", "too_still": True},
                                 {"id": "s001", "roll": "a", "src": "a.mp4", "start": 2, "duration": 2, "source_start": 2, "scene": "s001"}],
                     "captions": {"look": "ig-fb-native", "words": []},
                     "overlays": [{"id": "t0", "kind": "text", "what": "hook headline", "text": "Big words", "start": 0, "duration": 2, "y_pct": 6,
                                   "text_look": LK.text_look("hook headline", "headline-white-box"), "fixed": True},
                                  {"id": "t1", "kind": "text", "what": "badge", "text": "9/10", "start": 2, "duration": 2, "y_pct": 50, "badge": "green", "fixed": True}],
                     "layers": {"transitions": [{"after_scene": "s000", "kind": "whip"}]},
                     "realism": {"rows": ["phone-grain", "crooked-hold", "digital-micro-shake"]}}
            page = C.compose(sheet, root, root / "p").read_text()
            self.assertIn('id="grain"', page)
            # the crooked hold never zooms (verify 2026-10-21 row 1): an unpunched shot stays level, no scale anywhere
            self.assertNotIn('{rotation', page); self.assertNotIn("scale:1.035", page)
            self.assertIn("Big words", page); self.assertIn("rgba(255,255,255,1.0)", page)    # the white box
            self.assertIn("9/10", page); self.assertIn("#34BA5C", page)
            self.assertIn("blur(18px)", page)                                                 # the whip


class SoundQuality(unittest.TestCase):
    """E33 (2026-10-21, the owner: the reel sounded "muffled and choppy"): no join clicks, never muffled by the edit,
    never below 192k AAC / 48 kHz."""

    def test_a_hard_join_clicks_and_a_faded_one_does_not(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            hard, soft = Path(d) / "hard.wav", Path(d) / "soft.wav"
            # a loud tone cut dead at 0.5 s onto silence (a click), and the same with a 15 ms fade out
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=232.5:d=0.5:sample_rate=48000", "-af", "volume=6,apad=pad_dur=0.5", str(hard)], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=232.5:d=0.5:sample_rate=48000", "-af", "volume=6,afade=t=out:st=0.485:d=0.015,apad=pad_dur=0.5", str(soft)], check=True)
            self.assertEqual([f["check"] for f in AU.join_clicks(hard, [0.5])], ["JOIN CLICK"])
            self.assertEqual(AU.join_clicks(soft, [0.5]), [])

    def test_a_dulled_voice_reads_muffled(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            src, dull = Path(d) / "src.wav", Path(d) / "dull.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anoisesrc=d=2:c=white:a=0.3:r=48000", str(src)], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-af", "lowpass=f=1500,lowpass=f=1500", str(dull)], check=True)
            self.assertEqual([f["check"] for f in AU.clarity(dull, [(0.0, str(src), 0.0, 1.5, "S1")])], ["MUFFLED"])
            self.assertEqual(AU.clarity(src, [(0.0, str(src), 0.0, 1.5, "S1")]), [])

    def test_every_piece_of_sound_fades_at_its_edges(self):
        lane = C._join_fade(2.0, 1.0)
        self.assertEqual([p["v"] for p in lane], [0, 1.0, 1.0, 0])
        self.assertEqual((lane[1]["t"], round(lane[3]["t"] - lane[2]["t"], 3)), (0.015, 0.015))
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "a.mp4").write_bytes(b"x")
            sheet = {"meta": {"brand": "t", "label": "t", "width": 1080, "height": 1920, "fps": 30},
                     "picture": [{"id": "A", "roll": "a", "src": "a.mp4", "start": 0, "duration": 2, "source_start": 0, "volume_db": 0}],
                     "captions": {"look": "ig-fb-native", "words": []}, "overlays": [], "layers": {}}
            self.assertIn("data-automation", C.compose(sheet, root, root / "p").read_text())

    def test_no_encode_below_192k(self):
        for rate in (R.AAC_MID, R.AAC_MASTER):
            self.assertGreaterEqual(int(rate.rstrip("k")), 192)


class CopyOnce(unittest.TestCase):
    """E34 (2026-10-21, the speed round): the copywriter ran 43 min at 5b writing nothing, then ~49 min again inside
    filing. Copy already written is used; nothing written stops the line by name; filing never re-runs it."""

    def setUp(self):
        import line as L
        from unittest import mock
        self.L, self.mock = L, mock

    def test_written_copy_is_used_and_nothing_runs(self):
        with self.mock.patch.object(self.L, "copy_words", return_value=({"primary": ["p"], "headlines": ["h"]}, "set v1")), \
                self.mock.patch.object(self.L.subprocess, "run") as r:
            log = []
            self.assertEqual(self.L.write_copy("b", "brief-0001", log), "set v1")
            r.assert_not_called(); self.assertTrue(log[0]["ok"])

    def test_a_copywriter_that_writes_nothing_stops_the_line_by_name(self):
        done = self.mock.Mock(returncode=0, stdout="reddit 408\n", stderr="")
        with self.mock.patch.object(self.L, "copy_words", return_value=({}, None)), \
                self.mock.patch.object(self.L.subprocess, "run", return_value=done) as r:
            with self.assertRaises(self.L.Red) as e:
                self.L.write_copy("b", "brief-0002", [])
            self.assertEqual(r.call_count, 1)                                   # once, never twice
            self.assertIn("brief-0002", str(e.exception.code)); self.assertIn("reddit 408", str(e.exception.code))

    def test_filing_is_told_not_to_rerun_the_copywriter(self):
        src = (Path(self.L.__file__)).read_text()
        self.assertIn('run("7 file", fcmd, log, env={**os.environ, "NO_AD_WORDS": "1"})', src)

    def test_copy_early_writes_beside_production(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "run.json").write_text(json.dumps({"brand": "b", "brief": "brief-0003"}))
            with self.mock.patch.object(self.L, "write_copy", return_value="runs/x") as wc:
                self.assertEqual(self.L.main(["copy-early", d]), 0)
                wc.assert_called_once_with("b", "brief-0003", step="copy early")
            (Path(d) / "run.json").write_text(json.dumps({"brand": "b"}))
            self.assertEqual(self.L.main(["copy-early", d]), 1)                  # no brief: said, not guessed


class HookReusesTheControl(unittest.TestCase):
    """E35 · V22: a hook version swaps only the opening — the rest is the control's, moved by the opening's length."""

    def maps(self):
        def pic(a, b, clip, i): return {"a": a, "b": b, "kind": "clip", "clip": clip, "in": i, "lip": True}
        def line(a, b, clip, i, text): return {"a": a, "b": b, "kind": "in clip", "clip": clip, "in": i, "len": round(b - a, 3), "text": text, "who": "x", "scene": text}
        control = {"total": 10.0, "picture": [pic(0, 3, "OPEN", 0), pic(3, 10, "BODY", 0)],
                   "voice": [line(0, 3, "OPEN", 0, "old hook"), line(3, 10, "BODY", 0, "the body")], "sounds": [], "text": []}
        hook = {"total": 11.5, "picture": [pic(0, 4.5, "HOOK2", 0), pic(4.5, 11.5, "BODY", 0)],
                "voice": [line(0, 4.5, "HOOK2", 0, "new hook"), line(4.5, 11.5, "BODY", 0, "the body")], "sounds": [], "text": []}
        return control, hook

    def test_the_split_is_where_the_opening_ends(self):
        import render_map as RM
        control, hook = self.maps()
        self.assertEqual(RM.split_map(hook, control), (1.5, 4.5))

    def test_a_different_body_reuses_nothing(self):
        import render_map as RM
        control, hook = self.maps()
        hook["voice"][1]["text"] = "another body"
        shift, D = RM.split_map(hook, control)
        self.assertGreaterEqual(D, hook["total"] - 1.0)

    def test_the_opening_is_the_hooks_section_even_when_the_body_was_replanned(self):
        import render_map as RM
        control, hook = self.maps()
        for m, (a, b) in ((control, (0, 3)), (hook, (0, 4.5))):
            m["sections"] = [{"id": "G1", "a": a, "b": b}, {"id": "G2", "a": b, "b": m["total"]}]
            for x in m["picture"]:
                x["section"] = "G1" if x["a"] < b else "G2"
        hook["picture"][0]["clip"] = "H2"
        hook["picture"][1]["b"] = 11.49                      # the re-planned body jitters by a hundredth
        self.assertEqual(RM.opening_of(hook, control, "H2"), (1.5, 4.5))
        self.assertTrue(RM.same_frame(hook, control, 6.0, 1.5))          # BODY at its 3.0 s in both
        self.assertFalse(RM.same_frame(hook, control, 1.0, 1.5))         # the openings differ
        self.assertIsNone(RM.opening_of(hook, control, "NOPE"))

    def test_the_proof_is_by_frame_and_a_thumbnail_is_a_frame_of_the_cut(self):
        import subprocess
        import render_map as RM
        import thumbs as TH
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=270x480:rate=30:duration=2", "-pix_fmt", "yuv420p", str(d / "c.mp4")], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=270x480:rate=30:duration=2", "-pix_fmt", "yuv420p", str(d / "o.mp4")], check=True)
            self.assertTrue(RM.same_frames(d / "c.mp4", 0, d / "c.mp4", 0, 60, n=4)["identical"])
            self.assertFalse(RM.same_frames(d / "o.mp4", 0, d / "c.mp4", 0, 60, n=4)["identical"])
            (d / "renders").mkdir(); (d / "renders" / "control.clean.mp4").write_bytes((d / "c.mp4").read_bytes())
            TH.frame_at(d, d, {"picture": [], "total": 2.0}, 1.0, d / "t.jpg", "control")   # from the cut, no clip needed
            self.assertTrue((d / "t.jpg").is_file())

    def test_the_head_holds_only_the_opening(self):
        import render_map as RM
        _, hook = self.maps()
        h = RM._head_of(hook, 6.0)
        self.assertEqual(h["total"], 6.0)
        self.assertEqual([round(x["b"] - x["a"], 2) for x in RM.flatten(h)], [4.5, 1.5])


class VerifyRows(unittest.TestCase):
    """E36–E39 (re-verify 2026-10-21)."""

    def test_app_from_the_lane_when_nothing_names_it(self):
        with tempfile.TemporaryDirectory() as d:
            vm = Path(d)
            (vm / "run.json").write_text(json.dumps({"format": "talking-head", "placement": "paid"}))
            self.assertEqual(LK.app_for(vm), "meta")
            self.assertEqual(LK.pick_caption("talking-head", LK.app_for(vm)), "ig-fb-native")
            (vm / "run.json").write_text(json.dumps({"format": "talking-head", "placement": "organic", "app": "tiktok"}))
            self.assertEqual(LK.pick_caption("talking-head", LK.app_for(vm)), "tiktok-native")
            (vm / "run.json").write_text(json.dumps({"format": "talking-head", "placement": "organic"}))
            self.assertIsNone(LK.app_for(vm))

    def test_the_repairs_wait_for_a_person(self):
        import edit_map as EM
        for k in ("fixes.nudge", "picture_offset", "broll.calm/insert", "slow-down"):
            self.assertIn(k, EM.REPAIR_KEYS)

    def test_the_tilt_lives_in_the_punchs_own_room(self):
        import render_map as RM
        RM.TILT["on"] = True
        try:
            t = RM.tilt_for({"scale": 1.07, "clip": "X", "in": 0.0, "y": 0.5}, 3.0)
            self.assertIsNotNone(t)
            f = RM.crop_filter({"scale": 1.07, "clip": "X", "in": 0.0, "y": 0.5}, t)
            self.assertLess(f.index("rotate"), f.index("crop=iw/1.07"))            # turned before the window is cut
            self.assertEqual(f.count("scale=1080:1920"), 2)                          # and never scaled a second time
            self.assertIsNone(RM.tilt_for({"scale": 1.0, "clip": "X", "in": 0}, 3.0))
        finally:
            RM.TILT["on"] = False

    def test_only_called_cues_are_made_in_the_runs_own_bank(self):
        import sfx_make as SM
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "edit-map.json").write_text(json.dumps({"sfx": [
                {"cue": "soft pop", "made": False}, {"cue": "whoosh", "made": True}, {"cue": "none", "made": False}]}))
            rows = SM.wanted(out)
            self.assertEqual([r["id"] for r in rows], ["soft-pop"])
            root = SM.bank_of(out, rows)
            doc = json.loads((root / "sfx" / "index.json").read_text())
            self.assertEqual(doc["rows"][0]["status"], "to make")
            self.assertTrue(doc["drive_root"].endswith("/sfx"))
            (out / "edit-map.json").write_text(json.dumps({"sfx": []}))
            self.assertEqual(SM.wanted(out), [])                                     # nothing called, nothing made


class NotMechanicalScore(unittest.TestCase):
    """E23 · V14, V15: the retention score never pays for a zoom or an effect nobody asked for."""

    def test_no_effects_and_no_zooms_pass(self):
        s = {"picture": [{"id": "A", "roll": "a", "src": "a.mp4", "start": 0, "duration": 4.0, "talks": True, "why": "x"}],
             "captions": {"look": "ig-fb-native", "words": [w("one", .1, .4), w("BIG", 1.0, 1.4)]}, "overlays": [], "layers": {}, "sfx": []}
        rep = RT.check(s)
        by = {r["id"]: r for r in rep["rules"]}
        self.assertEqual(by["sfx-pairing"]["status"], "pass"); self.assertEqual(by["zoom-emphasis"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
