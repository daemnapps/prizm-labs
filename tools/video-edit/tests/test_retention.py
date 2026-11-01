"""The retention build, 2026-09-23: every retention rule on synthetic sheets (none of them
blocks — the owner: no hard gates), beat snapping, the per-frame face-track placement and its
fallback, the registry id gate, the GL transitions, the Fluent sprites and the confetti.
No model, no network; the only renders are two one-second ffmpeg colour clips."""
import copy, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import beats as BT, compose as C, cutsheet as CS, gl_transitions as GL, placement as P, registry as RG, retention as RT  # noqa: E401
from test_elements import elements_sheet

w = lambda t, s, e, **k: {"text": t, "start": s, "end": e, **k}  # noqa: E731


def talking_sheet(seconds=10.0, words=None, **extra):
    """One talking clip, captions on, nothing else — the barest edit."""
    s = {"meta": {"brand": "t", "label": "t", "width": 1080, "height": 1920, "fps": 30}, "controls": {"captions": {"value": "on"}},
         "picture": [{"id": "A", "roll": "a", "src": "a.mp4", "start": 0, "duration": seconds, "source_start": 0, "scene": "A", "talks": True, "kind": "talking", "why": "x"}],
         "captions": {"look": "bold-highlight", "words": words if words is not None else []}, "overlays": [], "layers": {}, "sfx": []}
    s.update(extra)
    return s


def rule(rep, rid):
    return next(x for x in rep["rules"] if x["id"] == rid)


class NothingBlocks(unittest.TestCase):
    def test_no_rule_is_a_gate(self):
        rows = json.loads((RT.TOOL / "looks/retention.json").read_text())["rules"]
        self.assertEqual({r["severity"] for r in rows}, {"info", "warn"})
        self.assertEqual({r["id"] for r in rows if r["severity"] == "info"}, {"hook-3s", "length-band"})
        self.assertEqual(len(rows), 10)
        for r in rows:
            self.assertIn(r["evidence"], ("evidence", "house-style")); self.assertTrue(r["source"]); self.assertTrue(r["threshold"])

    def test_report_never_blocks_and_info_never_warns(self):
        rep = RT.check(talking_sheet(20.0), controls={"retention": {"placement": "meta-feed"}})
        self.assertFalse(rep["blocks_export"])
        for rid in ("hook-3s", "length-band"):
            self.assertEqual(rule(rep, rid)["status"], "info")
        self.assertIn("outside", rule(rep, "length-band")["detail"])      # 20 s against 6–15 s: said, not blocked
        self.assertEqual(rule(rep, "hook-3s")["value"], "not met")         # no hook at all: said, not blocked

    def test_organic_has_no_band(self):
        self.assertIn("no length band", rule(RT.check(talking_sheet(40.0)), "length-band")["detail"])

    def test_hook_met(self):
        s = talking_sheet(6.0, [w("Stop", .1, .4), w("scrolling.", .5, 1.0)], overlays=[{"id": "h", "kind": "hook", "text": "Hook", "start": 0, "duration": 3}])
        self.assertEqual(rule(RT.check(s), "hook-3s")["value"], "met")

    def test_dials_override(self):
        s = talking_sheet(10.0)
        self.assertEqual(rule(RT.check(s), "static-hold")["status"], "warn")
        self.assertEqual(rule(RT.check(s, controls={"retention": {"dials": {"static-hold": {"max_s": 11}}}}), "static-hold")["status"], "pass")


class Rules(unittest.TestCase):
    def test_static_hold_flags_the_span(self):
        rep = RT.check(talking_sheet(10.0))
        r = rule(rep, "static-hold")
        self.assertEqual(r["status"], "warn"); self.assertEqual((r["flags"][0]["s"], r["flags"][0]["e"]), (0.0, 10.0))
        caps = [w(f"w{i}", i * 2.0 + .1, i * 2.0 + .5) for i in range(5)]  # a caption line every 2 s
        self.assertEqual(rule(RT.check(talking_sheet(10.0, caps)), "static-hold")["status"], "pass")

    def test_change_cadence_ignores_captions(self):
        caps = [w(f"w{i}.", i * 2.0 + .1, i * 2.0 + .5) for i in range(5)]
        s = talking_sheet(10.0, caps)
        self.assertEqual(rule(RT.check(s), "change-cadence")["status"], "warn")
        s["layers"]["icons"] = [{"id": f"i{n}", "icon": "fire", "start": t, "duration": .8} for n, t in enumerate((3.0, 6.0, 9.0))]
        self.assertEqual(rule(RT.check(s), "change-cadence")["status"], "pass")

    def test_dead_air_while_talking_only(self):
        s = talking_sheet(4.0, [w("a", .1, .5), w("b", 1.5, 1.9), w("c", 2.0, 3.9)])
        r = rule(RT.check(s), "dead-air")
        self.assertEqual(r["status"], "warn"); self.assertEqual((r["flags"][0]["s"], r["flags"][0]["e"]), (0.5, 1.5))
        s["captions"]["words"][1] = w("b", .8, 1.9)
        self.assertEqual(rule(RT.check(s), "dead-air")["status"], "pass")
        # a silent card between two voiced runs is silent on purpose
        s2 = talking_sheet(2.0, [w("a", .05, 1.95), w("b", 4.05, 5.95)])
        s2["picture"] += [{"id": "C", "roll": "a", "src": "p.png", "start": 2.0, "duration": 2.0, "kind": "card", "still": True, "why": "x", "card": {"lines": ["X"]}},
                          {"id": "B", "roll": "a", "src": "a.mp4", "start": 4.0, "duration": 2.0, "talks": True, "kind": "talking", "why": "x"}]
        self.assertEqual(rule(RT.check(s2), "dead-air")["status"], "pass")

    def test_sfx_pairing_ratio(self):
        caps = [w(f"w{i}.", i * 2.0 + .1, i * 2.0 + .5) for i in range(4)]
        s = talking_sheet(8.0, caps, sfx=[{"id": "x", "at": 0.15}])
        r = rule(RT.check(s), "sfx-pairing")
        self.assertEqual((r["status"], r["value"]), ("warn", "1/4 (25%)")); self.assertEqual(len(r["flags"]), 3)
        s["sfx"].append({"id": "y", "at": 2.1})
        self.assertEqual(rule(RT.check(s), "sfx-pairing")["status"], "pass")

    def test_zoom_on_emphasis(self):
        s = talking_sheet(4.0, [w("so", .1, .3), w("BIG", 1.0, 1.4, emphasis=True), w("wow", 2.6, 3.0, emphasis=True)])
        s["picture"] = [dict(s["picture"][0], id="A-1", duration=1.0), dict(s["picture"][0], id="A-2", start=1.0, duration=3.0, source_start=1.0, punch=1.07)]
        r = rule(RT.check(s), "zoom-emphasis")
        self.assertEqual(r["value"], "1/2 (50%)"); self.assertEqual(r["status"], "pass")
        self.assertIn("wow", r["flags"][0]["detail"])
        self.assertEqual(rule(RT.check(s, controls={"retention": {"dials": {"zoom-emphasis": {"min_ratio": 0.9}}}}), "zoom-emphasis")["status"], "warn")

    def test_emphasis_heuristic_without_marks(self):
        s = talking_sheet(3.0, [w("only", .1, .3), w("$29", .4, .8), w("today!", 1.0, 1.4), w("ok", 2.0, 2.2)])
        got, how = RT.emphasis_words(s, None, .15)
        self.assertEqual([x["text"] for x in got], ["$29", "today!"]); self.assertIn("numbers", how)

    def test_broll_cadence(self):
        s = talking_sheet(12.0)
        r = rule(RT.check(s), "broll-cadence")
        self.assertEqual(r["status"], "warn")
        s["picture"].append({"id": "B", "roll": "b", "src": "b.mp4", "start": 5.0, "duration": 2.0, "why": "x"})
        self.assertEqual(rule(RT.check(s), "broll-cadence")["status"], "pass")  # 0–5 and 7–12, both under 6 s

    def test_text_within_one_second(self):
        s = talking_sheet(4.0, [w("late", 1.6, 2.0)])
        r = rule(RT.check(s), "text-hook-1s")
        self.assertEqual(r["status"], "warn"); self.assertEqual(r["value"], "1.54s")
        s["overlays"] = [{"id": "h", "kind": "hook", "text": "Hook", "start": 0, "duration": 2}]
        self.assertEqual(rule(RT.check(s), "text-hook-1s")["status"], "pass")

    def test_loop_ending_scored_on_the_file(self):
        d = Path(tempfile.mkdtemp())
        same, diff = d / "same.mp4", d / "diff.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=270x480:d=1:r=30", "-pix_fmt", "yuv420p", str(same)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=270x480:d=1:r=30", "-vf", "hue=H=t*6", "-pix_fmt", "yuv420p", str(diff)], check=True)
        s = talking_sheet(1.0)
        self.assertEqual(rule(RT.check(s), "loop-ending")["status"], "not measured")
        self.assertEqual(rule(RT.check(s, same), "loop-ending")["status"], "pass")
        self.assertGreater(RT.ssim_first_last(same), 0.95)
        self.assertLess(RT.ssim_first_last(diff), RT.ssim_first_last(same))

    def test_score_is_mean_of_warn_rules(self):
        rep = RT.check(elements_sheet(Path(tempfile.mkdtemp())))
        scored = [x["score"] for x in rep["rules"] if x["severity"] == "warn" and x["score"] is not None]
        self.assertEqual(rep["score"], round(sum(scored) / len(scored)))
        self.assertTrue(RT.lines(rep)[0].startswith("RETENTION"))


class Beats(unittest.TestCase):
    def sheet(self):
        s = talking_sheet(10.0)
        s["picture"].append({"id": "B", "roll": "b", "kind": "broll", "src": "b.mp4", "start": 3.07, "duration": 2.0, "why": "x"})
        s["layers"] = {"icons": [{"id": "i1", "icon": "fire", "start": 6.45, "duration": 1.0}, {"id": "i2", "icon": "fire", "start": 8.2, "duration": 1.0}]}
        s["sfx"] = [{"id": "s1", "for": "B", "at": 3.07}]
        return s

    def test_snap_within_tolerance_only(self):
        s = self.sheet()
        moves = BT.snap(s, [0.0, 0.5, 1.0, 3.0, 6.5, 9.0], 0.12)
        self.assertEqual([(m["id"], m["to"]) for m in moves], [("B", 3.0), ("i1", 6.5)])   # i2 (8.2) is 0.8 s from a beat: left alone
        self.assertEqual(s["picture"][1]["start"], 3.0); self.assertEqual(s["picture"][1]["duration"], 2.0)
        self.assertEqual(s["sfx"][0]["at"], 3.0)                                            # its sound travels with it
        self.assertEqual(s["picture"][0]["start"], 0)                                       # the talking cut never moves

    def test_graphic_never_snaps_out_of_its_scene(self):
        s = self.sheet()
        s["picture"].append({"id": "C", "roll": "a", "src": "a.mp4", "start": 10.0, "duration": 2.0, "scene": "C", "talks": True, "why": "x"})
        s["layers"]["icons"] = [{"id": "i3", "icon": "fire", "scene": "C", "start": 10.05, "duration": 1.0}]
        self.assertEqual([m["id"] for m in BT.snap(s, [9.98], 0.12)], [])

    def test_cover_without_talking_under_it_stays(self):
        s = self.sheet()
        s["picture"][0]["duration"] = 3.05                                                  # nothing talking under the b-roll any more
        self.assertEqual([m["id"] for m in BT.snap(s, [3.0], 0.12)], [])

    def test_to_final_clock_and_grid_fallback(self):
        self.assertEqual(BT.to_final({"source_start": 1.0, "start": 0}, [0.5, 1.0, 1.5, 12.0], 10.0), [0.0, 0.5])
        with mock.patch("helpers.call", side_effect=RuntimeError("no venv")):
            got = BT.detect(Path("m.mp3"), 120, 2.0)
        self.assertEqual(got["beats"][:3], [0.0, 0.5, 1.0]); self.assertIn("tempo grid", got["by"])

    def test_tolerance_dial(self):
        self.assertEqual(BT.tolerance({"beats": {"snap_tolerance_s": 0.2}}), (0.2, True))
        self.assertEqual(BT.tolerance(None)[0], json.loads((BT.TOOL / "looks/retention.json").read_text())["beats"]["snap_tolerance_s"])


class FaceTrack(unittest.TestCase):
    def sheet(self):
        s = elements_sheet(Path(tempfile.mkdtemp()))
        s["layers"]["lower_thirds"][0].pop("y_pct"); s["layers"]["platform_ui"][0].pop("y_pct"); s["overlays"][0].pop("y_pct")
        return s

    def test_track_window_and_fallback_order(self):
        c = {"start": 0.0, "duration": 4.0, "face_track_fps": 5, "face_track": [{"t": 0.2, "x": 10, "y": 10, "w": 10, "h": 10}, {"t": 3.0, "x": 60, "y": 60, "w": 10, "h": 10}]}
        self.assertEqual(P.tracked_box(c, 0.0, 1.0), (10, 10, 20, 20))       # only what was seen while the layer is up
        self.assertEqual(P.tracked_box(c), (10, 10, 70, 70))
        self.assertIsNone(P.tracked_box(c, 1.5, 2.2))                       # tracked, no face then
        self.assertIs(P.tracked_box({"start": 0, "duration": 1}), False)    # never tracked → subject_box
        self.assertIs(P.tracked_box({"start": 0, "duration": 1, "face_track": []}), False)  # tracker saw nothing → subject_box

    def test_tracking_beats_subject_box_and_empty_track_falls_back(self):
        s = self.sheet()
        for p in s["picture"]:
            if p["scene"] == "S1":
                p["subject_box"] = {"x": 20, "y": 45, "w": 60, "h": 20}            # production says: low in frame
                p["face_track"] = [{"t": p["start"] + .1, "x": 30, "y": 20, "w": 30, "h": 12}]  # the tracker says: high
        faces, blind = P.faces_in(s, "S1")
        self.assertTrue(all(f[1] == 20 for f in faces)); self.assertNotIn("S1", blind)
        for p in s["picture"]:
            if p["scene"] == "S1":
                p["face_track"] = []
        faces, _ = P.faces_in(s, "S1")
        self.assertTrue(faces and all(f[1] == 45 for f in faces))                  # empty track → subject_box stands
        for p in s["picture"]:
            if p["scene"] == "S1":
                p.pop("subject_box")
        self.assertIn("S1", P.faces_in(s, "S1")[1])                                 # nothing at all → face-blind

    def test_layer_moves_only_while_the_face_is_there(self):
        s = self.sheet()
        a = next(p for p in s["picture"] if p["id"] == "S1-1")
        a["face_track"] = [{"t": 1.0, "x": 5, "y": 42, "w": 55, "h": 12}]           # a face over the lower-third zone, only around 1 s
        s["layers"]["icons"] = [{"id": "early", "icon": "fire", "zone": "lower-third", "start": 0.8, "duration": 0.4},
                                {"id": "late", "icon": "fire", "zone": "lower-third", "start": 1.7, "duration": 0.2}]
        P.place(s)
        moved = {m["id"] for m in s["placement"]}
        self.assertIn("early", moved); self.assertNotIn("late", moved)


class Registry(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        idx = self.d / "registry.json"
        idx.write_text(json.dumps({"blocks": [{"id": "burst-block", "category": "block", "fits": "particles", "what": "x", "tags": []},
                                              {"id": "grain-comp", "category": "component", "fits": "overlay", "what": "x", "tags": []}]}))
        self.p = [mock.patch.object(RG, "INDEX", idx), mock.patch.object(RG, "PROJECT", self.d / "proj")]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()

    def red(self, rid):
        s = elements_sheet(Path(tempfile.mkdtemp()))
        s["layers"]["registry"] = [{"id": rid, "start": 1.0, "duration": 1.0}]
        return [r for r in CS.check(s, Path(tempfile.mkdtemp()), probe=lambda p: 99) if "layers.registry" in r]

    def test_unknown_id_is_red(self):
        self.assertIn("not in the HyperFrames registry index", self.red("nope")[0])

    def test_known_but_not_installed_is_red_and_says_how(self):
        self.assertIn("python3 machine/registry.py install burst-block", self.red("burst-block")[0])

    def test_installed_block_passes_component_does_not(self):
        f = self.d / "proj/compositions/burst-block.html"; f.parent.mkdir(parents=True); f.write_text("<div></div>")
        self.assertEqual(self.red("burst-block"), [])
        c = self.d / "proj/compositions/components/grain-comp.html"; c.parent.mkdir(parents=True); c.write_text("x")
        self.assertIn("is a component", self.red("grain-comp")[0])

    def test_fits(self):
        self.assertEqual(RG.fits_of(["transition", "shader"]), "transition")
        self.assertEqual(RG.fits_of(["captions"]), "caption")
        self.assertEqual(RG.fits_of(["mock-ui", "chat"]), "mock-ui")
        self.assertEqual(RG.fits_of(["whatever"]), "other")

    def test_real_index_has_every_block(self):
        real = json.loads((RG.TOOL / "looks/registry.json").read_text())
        self.assertEqual(real["count"], len(real["blocks"])); self.assertGreaterEqual(real["count"], 382)
        for r in real["blocks"]:
            self.assertIn(r["fits"], ("transition", "overlay", "particles", "mock-ui", "camera", "caption", "other"))
            self.assertTrue(r["install_cmd"].endswith(r["id"]))


class GlAndAssets(unittest.TestCase):
    def test_every_gl_row_has_its_shader_and_compiles_its_defaults(self):
        rows = [r for r in json.loads((CS.TOOL / "looks/transitions.json").read_text())["transitions"] if r.get("engine") == "gl"]
        self.assertGreaterEqual(len(rows), 6)
        for r in rows:
            frag = GL.fragment(CS.TOOL / r["glsl"])
            self.assertNotIn("uniform float persp", frag); self.assertIn("vec4 transition", frag); self.assertTrue(r["drawn"])
        self.assertIn("const float depth = 3.0;", GL.fragment(CS.TOOL / "looks/gl-transitions/gl-doorway.glsl"))

    def test_gl_transition_composes_with_helpers(self):
        root = Path(tempfile.mkdtemp()); s = elements_sheet(root)
        s["layers"]["transitions"][0]["kind"] = "gl-crosswarp"
        self.assertEqual([r for r in CS.check(s, root, probe=lambda p: 99) if "transitions" in r], [])
        page = C.compose(s, root, root / "proj").read_text()
        self.assertIn('<canvas id="gltx"', page); self.assertIn("glh-gl-crosswarp-0-out", page); self.assertIn("__hfReseekGpu", page)
        self.assertIn("gl-crosswarp", page)

    def test_missing_shader_is_red(self):
        root = Path(tempfile.mkdtemp()); s = elements_sheet(root)
        s["layers"]["transitions"][0]["kind"] = "gl-crosswarp"
        rows = json.loads((CS.TOOL / "looks/transitions.json").read_text())
        for r in rows["transitions"]:
            if r["id"] == "gl-crosswarp":
                r["glsl"] = "looks/gl-transitions/missing.glsl"
        real = CS.load
        with mock.patch.object(CS, "load", lambda n: rows if n == "looks/transitions.json" else real(n)):
            self.assertTrue(any("shader looks/gl-transitions/missing.glsl is missing" in r for r in CS.check(s, root, probe=lambda p: 99)))

    def test_confetti_and_animated_emoji(self):
        root = Path(tempfile.mkdtemp()); s = elements_sheet(root)
        s["layers"]["icons"] = [{"id": "boom", "icon": "confetti-burst", "start": 11.0, "duration": 2.0, "zone": "center", "size": "l"},
                                {"id": "hot", "icon": "fl-fire", "start": 1.0, "duration": 1.5, "zone": "left-rail", "size": "m"}]
        self.assertEqual([r for r in CS.check(s, root, probe=lambda p: 99) if "icons" in r], [])
        page = C.compose(s, root, root / "proj").read_text()
        self.assertIn('<canvas id="boom-in"', page); self.assertIn("window.__editDraws.push(draw)", page)
        import icons as IC
        if IC.sprite("fl-fire"):  # the strip is built by `icons.py install` (kept out of git)
            self.assertIn('id="hot-sp"', page); self.assertIn("steps(48)", page)

    def test_fluent_rows(self):
        lib = json.loads((CS.TOOL / "looks/icons.json").read_text())
        fl = [r for r in lib["icons"] if r["set"] == "fluent"]
        self.assertGreaterEqual(len(fl), 40)
        self.assertTrue(all(r["licence"] == "MIT" for r in fl))
        self.assertGreaterEqual(sum(1 for r in fl if r.get("animated")), 25)


if __name__ == "__main__":
    unittest.main()
