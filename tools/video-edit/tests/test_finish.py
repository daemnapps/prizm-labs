"""The four finished 2026-09-23 ("fill in any of the partly"): the green-screen cut-out
placed, annotations that follow the face, captions in the script's spelling, and the
Pauses lane on the live timeline. No renders, no model, no live runs — the cut-out maker
is stubbed; the picture hash uses ffmpeg on a one-second test clip when ffmpeg is here."""
import copy, json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import compose as C, cutout as CO, cutsheet as CS, follow as FL, kit_from_run as K, live_page as LP, placement as P, run as R, spelling as SP  # noqa: E401

DEFAULTS = json.loads((Path(CS.TOOL) / "machine/defaults.json").read_text())
w = lambda t, s, e: {"text": t, "start": s, "end": e}  # noqa: E731


def gs_sheet(root: Path, layout="cutout") -> dict:
    for f in ("a.mp4", "bg.png"):
        (root / f).write_bytes(b"x")
    return {"meta": {"brand": "t", "label": "t", "width": 1080, "height": 1920, "fps": 30}, "controls": copy.deepcopy(DEFAULTS),
            "picture": [{"id": "S6-1", "roll": "a", "src": "a.mp4", "start": 0, "duration": 2, "source_start": 0.4, "scene": "S6", "why": "x",
                         "talks": True, "volume_db": 0, "kind": "greenscreen", "greenscreen": {"background": "bg.png", "layout": layout}},
                        {"id": "S6-2", "roll": "a", "src": "a.mp4", "start": 2, "duration": 1.5, "source_start": 3.1, "scene": "S6", "why": "x",
                         "talks": True, "volume_db": 0, "kind": "greenscreen", "greenscreen": {"background": "bg.png", "layout": layout}}],
            "captions": {"look": "bold-highlight", "words": []}, "overlays": [], "layers": {}}


class CutoutPlaced(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.root = Path(self.d.name)
        self.webm = self.root / "cache" / "abcd.webm"; self.webm.parent.mkdir(); self.webm.write_bytes(b"webm")
        self.calls = []

    def tearDown(self): self.d.cleanup()

    def maker(self, src):
        self.calls.append(src)
        return {"webm": str(self.webm), "hash": "abcd", "cached": False, "per_video_second_s": 7.5, "per_frame_s": 0.25, "device": "mps", "model": "lite", "made_s": 30}

    def test_cutout_scene_gets_its_alpha_clip_once_per_source(self):
        s = gs_sheet(self.root)
        notes = CO.attach(s, self.root, maker=self.maker)
        self.assertEqual(len(self.calls), 1)                              # two parts, one source → cut out once
        self.assertTrue(all(c["cutout"]["webm"] == str(self.webm) for c in s["picture"]))
        self.assertTrue(any("per second of video" in n for n in notes))

    def test_pip_is_left_as_it_is(self):
        s = gs_sheet(self.root, "pip")
        CO.attach(s, self.root, maker=self.maker)
        self.assertEqual(self.calls, []); self.assertNotIn("cutout", s["picture"][0])

    def test_dry_run_makes_nothing_and_says_so(self):
        s = gs_sheet(self.root)
        notes = CO.attach(s, self.root, make_missing=False)
        self.assertNotIn("cutout", s["picture"][0]); self.assertTrue(any("dry run makes none" in n for n in notes))
        self.assertTrue(any("not cut out yet" in x for x in CS.warnings(s)))

    def test_compose_stands_the_cutout_on_the_plate_and_keeps_her_sound(self):
        s = gs_sheet(self.root)
        CO.attach(s, self.root, maker=self.maker)
        page = C.compose(s, self.root, self.root / "proj").read_text()
        self.assertIn('src="assets/abcd.webm" data-media-start="0.4"', page)   # each part reads its own stretch of the one cut-out
        self.assertIn('src="assets/abcd.webm" data-media-start="3.1"', page)
        raw = [ln for ln in page.split("<video") if 'src="assets/a.mp4"' in ln]
        self.assertTrue(raw and all("data-has-audio" in ln and "opacity:0" in ln for ln in raw))  # heard, not seen
        cut = [ln for ln in page.split("<video") if "abcd.webm" in ln]
        self.assertTrue(all(" muted" in ln for ln in cut))
        self.assertFalse(any("not cut out yet" in x for x in CS.warnings(s)))

    def test_no_cutout_shows_the_raw_clip(self):
        s = gs_sheet(self.root)
        page = C.compose(s, self.root, self.root / "proj").read_text()
        self.assertNotIn(".webm", page); self.assertNotIn("opacity:0", page.split("<video")[1])

    def test_cache_is_found_by_picture_hash(self):
        CO.CACHE, old = self.root / "cc", CO.CACHE
        try:
            d = CO.CACHE / "0123456789abcdef-lite"; d.mkdir(parents=True)
            (d / "cutout.json").write_text(json.dumps({"webm": str(self.webm), "hash": "0123456789abcdef00"}))
            self.assertTrue(CO.cached(self.root / "a.mp4", h="0123456789abcdef00")["cached"])
            self.assertIsNone(CO.cached(self.root / "a.mp4", h="ffff456789abcdef00"))
        finally:
            CO.CACHE = old

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg")
    def test_a_levelled_copy_has_the_same_picture_hash(self):
        a, b = self.root / "clip.mp4", self.root / "clip.level.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=64x64:d=1", "-f", "lavfi", "-i", "sine=d=1",
                        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(a)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a), "-c:v", "copy", "-af", "volume=0.5", "-c:a", "aac", str(b)], check=True)
        self.assertEqual(CO.picture_hash(a), CO.picture_hash(b))

    def test_face_boxes_map_onto_the_frame_through_the_layout(self):
        rect = P.presenter_rect("cutout")                       # 58% tall, 24% up, contained: the picture is 58% of the frame, from x=21%, y=18%
        got = P.to_frame({"x": 45, "y": 20, "w": 10, "h": 10}, rect)
        self.assertAlmostEqual(got["x"], 21 + 0.58 * 45, delta=0.1); self.assertAlmostEqual(got["y"], 18 + 0.58 * 20, delta=0.1)
        self.assertAlmostEqual(got["w"], 5.8, delta=0.1)
        pip = P.presenter_rect("pip")
        self.assertIsNone(P.to_frame({"x": 0, "y": 0, "w": 2, "h": 2}, pip))   # cropped away by the card's cover-fit


def talking_with_track(root: Path, boxes: "list[dict] | None", subject=None) -> dict:
    (root / "a.mp4").write_bytes(b"x")
    c = {"id": "S1-1", "roll": "a", "src": "a.mp4", "start": 0, "duration": 4, "source_start": 0, "scene": "S1", "why": "x",
         "talks": True, "volume_db": 0, "kind": "talking"}
    if boxes is not None:
        c.update(face_track=boxes, face_track_fps=5)
    if subject:
        c["subject_box"] = subject
    return {"meta": {"brand": "t", "label": "t", "width": 1080, "height": 1920, "fps": 30}, "controls": copy.deepcopy(DEFAULTS),
            "picture": [c], "captions": {"look": "bold-highlight", "words": []}, "overlays": [],
            "layers": {"annotations": [{"id": "an1", "scene": "S1", "kind": "circle", "target": "face", "start": 1.0, "duration": 2.0},
                                       {"id": "an2", "scene": "S1", "kind": "arrow", "target": "left", "start": 1.0, "duration": 1.0,
                                        "place": {"x_pct": 30, "y_pct": 48, "w_pct": 30, "h_pct": 18}}]}}


class AnnotationsFollow(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.root = Path(self.d.name)
        # the face drifts right 2% of the frame every 0.2s, with a jitter of ±1.5% every other frame
        self.boxes = [{"t": round(0.8 + i * 0.2, 2), "x": 30 + 2 * i + (1.5 if i % 2 else -1.5), "y": 30, "w": 20, "h": 12} for i in range(14)]

    def tearDown(self): self.d.cleanup()

    def test_follows_the_track_with_smoothed_keyframes(self):
        s = talking_with_track(self.root, self.boxes)
        FL.apply(s)
        a = s["layers"]["annotations"][0]
        self.assertEqual(a["follow"]["by"], "face_track")
        ks = a["follow"]["keys"]
        self.assertEqual(ks[0]["t"], 1.0); self.assertEqual(ks[-1]["t"], 3.0)
        self.assertGreater(ks[-1]["x_pct"] - ks[0]["x_pct"], 15)                      # it moved with her
        steps = [b["x_pct"] - a_["x_pct"] for a_, b in zip(ks, ks[1:])]
        self.assertTrue(all(st > -0.5 for st in steps))                               # smoothed: the ±1.5 jitter no longer throws it backwards
        self.assertAlmostEqual(a["place"]["y_pct"], 36, delta=0.5)                    # centred on the face (30 + 12/2)
        self.assertAlmostEqual(a["place"]["w_pct"], 20 * 1.55, delta=0.1)             # a ring around it, size held

    def test_fixed_target_stays_fixed(self):
        s = talking_with_track(self.root, self.boxes)
        FL.apply(s)
        self.assertNotIn("follow", s["layers"]["annotations"][1])
        self.assertEqual(s["layers"]["annotations"][1]["place"]["x_pct"], 30)

    def test_subject_box_when_no_track(self):
        s = talking_with_track(self.root, None, subject={"x": 40, "y": 20, "w": 20, "h": 20})
        FL.apply(s)
        a = s["layers"]["annotations"][0]
        self.assertEqual(a["follow"]["by"], "subject_box"); self.assertEqual(a["place"]["x_pct"], 50)

    def test_no_track_warns_and_falls_back_to_fixed(self):
        s = talking_with_track(self.root, None)
        notes = FL.apply(s)
        a = s["layers"]["annotations"][0]
        self.assertIsNone(a["follow"]["by"]); self.assertEqual(a["follow"]["fell_back_to"], "center")
        self.assertTrue(a["place"]); self.assertTrue(notes)
        self.assertTrue(any("should follow the face" in x for x in CS.warnings(s)))
        self.assertFalse([r for r in CS.check_elements(s, self.root, lambda p: 10.0, 4.0) if "annotations" in r])   # a WARN, never red

    def test_target_forms(self):
        self.assertTrue(FL.follows({"target": "Face"})); self.assertTrue(FL.follows({"target": {"follow": "subject"}}))
        self.assertFalse(FL.follows({"target": "center"})); self.assertFalse(FL.follows({"target": {"x_pct": 1, "y_pct": 2}}))

    def test_compose_moves_a_mover_not_the_clip(self):
        s = talking_with_track(self.root, self.boxes)
        FL.apply(s)
        page = C.compose(s, self.root, self.root / "proj").read_text()
        self.assertIn('id="an1-mv"', page)
        self.assertGreater(page.count('tl.fromTo("#an1-mv"'), 3)
        self.assertNotIn('tl.fromTo("#an1",', page); self.assertNotIn('id="an2-mv"', page)


class ScriptSpelling(unittest.TestCase):
    heard = [w("I", 0, .1), w("love", .15, .4), w("Lumara's", .45, .9), w("serum.", .95, 1.3), w("Only", 1.5, 1.7),
             w("twenty-nine", 1.75, 2.2), w("dollars", 2.25, 2.6), w("for", 2.7, 2.8), w("twenty-eight", 2.85, 3.3),
             w("to", 3.35, 3.45), w("forty", 3.5, 3.8), w("days.", 3.85, 4.1)]
    line = "I love Lumora's serum. Only $29 for 28 to 40 days."

    def test_script_words_on_the_heard_clock(self):
        ws, notes = SP.align(self.heard, self.line)
        self.assertEqual([x["text"] for x in ws], self.line.split())
        by = {x["text"]: x for x in ws}
        self.assertEqual(by["Lumora's"]["heard"], "Lumara's"); self.assertEqual((by["Lumora's"]["start"], by["Lumora's"]["end"]), (.45, .9))
        self.assertEqual((by["$29"]["start"], by["$29"]["end"]), (1.75, 2.6))       # the digits stay digits, as long as the words took
        self.assertEqual((by["28"]["start"], by["40"]["end"]), (2.85, 3.8))
        self.assertEqual(notes, [])

    def test_production_swaps_are_used(self):
        heard = [w("loo", 0, .2), w("more", .2, .4), w("works", .5, .7)]
        ws, _ = SP.align(heard, "Lumora works", {"said_as": [{"term": "Lumora", "say_as": "loo-mor-a"}]})
        self.assertEqual([x["text"] for x in ws], ["Lumora", "works"]); self.assertEqual(ws[0]["end"], .4)
        ws, _ = SP.align([w("twenty", 0, .3), w("nine", .3, .5)], "$29", {"numbers": [{"from": "$29", "to": "twenty-nine"}]})
        self.assertEqual(ws, [{"text": "$29", "start": 0, "end": .5, "heard": "twenty nine"}])

    def test_unaligned_keeps_the_heard_word_and_warns(self):
        ws, notes = SP.align(self.heard + [w("um", 4.2, 4.3)], self.line)
        self.assertEqual(ws[-1]["text"], "um"); self.assertTrue(ws[-1]["unaligned"])
        self.assertTrue(any("`um`" in n for n in notes))
        ws, notes = SP.align([w("totally", 0, .5), w("different", .5, 1)], "Lumora works")
        self.assertEqual([x["text"] for x in ws], ["totally", "different"]); self.assertEqual(len(notes), 4)

    def test_no_line_leaves_the_words_alone(self):
        self.assertEqual(SP.align(self.heard, None), ([dict(x) for x in self.heard], []))

    def test_the_cut_uses_the_script_spelling(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "a.mp4").write_bytes(b"x")
            kit = {"clips": [{"id": "S1", "scene": "S1", "src": "a.mp4", "roll": "a", "talks": True, "approved": True,
                              "line": self.line + " um", "words": self.heard + [w("uh", 4.3, 4.4)]}]}
            s = R.auto_cut(kit, root, root, copy.deepcopy(DEFAULTS), "t", "t", level=False)
            texts = [x["text"] for x in s["captions"]["words"]]
            self.assertIn("Lumora's", texts); self.assertIn("$29", texts); self.assertNotIn("Lumara's", texts)
            self.assertTrue(any("`uh`" in n for n in s["captions"]["spelling"]))
            self.assertTrue(any("captions: S1:" in x for x in CS.warnings(s)))

    def test_words_are_still_found_in_the_script_spelling(self):
        import assemble as A
        ws = [w("Over", 0, .2), w("2,000", .2, .9), w("five-star", 1, 1.5), w("reviews", 1.5, 2)]
        self.assertEqual(A.find_words("five star", ws), (1, 1.5))
        self.assertEqual(A.find_words("star reviews", ws), (1, 2))
        self.assertEqual(R.span_of({"from": "five", "to": "reviews"}, ws), (1, 2))

    def test_join_carries_productions_swaps(self):
        with tempfile.TemporaryDirectory() as d:
            vm = Path(d); (vm / "media").mkdir(); (vm / "vo").mkdir()
            (vm / "media/S1.mp4").write_bytes(b"x")
            (vm / "run.json").write_text(json.dumps({"brand": "t", "label": "t"}))
            (vm / "plan.json").write_text(json.dumps({"scenes": [{"id": "S1", "type": "A", "to_camera": True, "voice": "Only $29"}]}))
            (vm / "vo/timing.json").write_text(json.dumps({"scenes": {"S1": {"said_as": [], "numbers": [{"from": "$29", "to": "twenty-nine dollars"}]}}}))
            kit, _ = K.build(vm)
            self.assertEqual(kit["clips"][0]["said"]["numbers"][0]["from"], "$29")


class PausesLane(unittest.TestCase):
    words = [w("One", 0.2, 0.5), w("two", 0.7, 1.0),         # 0.20 — a breath under tight (0.25): kept, not marked
             w("three", 1.3, 1.6),                             # 0.30 — cut by tight, marked
             w("four", 2.1, 2.4),                              # 0.50 — cut
             w("five", 2.8, 3.1)]                              # 0.40 — cut

    def cut(self, pace="tight"):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "a.mp4").write_bytes(b"x")
            ctl = copy.deepcopy(DEFAULTS); ctl["pace"]["value"] = pace
            kit = {"clips": [{"id": "S1", "scene": "S1", "src": "a.mp4", "roll": "a", "talks": True, "approved": True, "words": self.words}]}
            return R.auto_cut(kit, root, root, ctl, "t", "t", level=False)

    def test_tight_cuts_and_marks_every_real_pause(self):
        s = self.cut()
        p = s["pauses"]
        self.assertEqual([x["length"] for x in p], [0.3, 0.5, 0.4])
        self.assertTrue(all(x["action"] == "cut" for x in p))
        joins = [c["start"] for c in s["picture"][1:]]
        self.assertEqual([x["at"] for x in p], joins)                      # each red dot sits exactly on its join
        self.assertAlmostEqual(p[1]["removed"] + p[1]["left"], 0.5, places=3)

    def test_breathing_keeps_them_and_marks_the_long_ones(self):
        s = self.cut("breathing")
        p = s["pauses"]
        self.assertEqual([(x["length"], x["action"]) for x in p], [(0.5, "kept"), (0.4, "kept")])   # 0.30 is a breath under 0.35: not marked
        self.assertEqual(len(s["picture"]), 1)
        self.assertAlmostEqual(p[0]["end"] - p[0]["start"], 0.5, places=3)

    def test_live_timeline_draws_the_lane(self):
        s = self.cut()
        s["picture"][0]["section"] = "hook"
        tracks, _ = LP.tracks_of(s)
        lane = next(t for t in tracks if t["name"] == "Pauses")
        self.assertEqual(len(lane["items"]), 3)
        self.assertTrue(all(i["point"] and "cut" in i["label"] and i["jump"] < i["s"] for i in lane["items"]))
        self.assertIn("3 cut", lane["note"])
        page = LP.write(Path(tempfile.mkdtemp()), s, None, out=Path(tempfile.mkdtemp()) / "t.html").read_text()
        self.assertIn('"name": "Pauses"', page); self.assertIn("it.jump??it.s", page)


if __name__ == "__main__":
    unittest.main()
