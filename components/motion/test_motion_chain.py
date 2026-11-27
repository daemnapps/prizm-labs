"""The motion chain's own rules: python3 -m unittest test_motion_chain (no MediaPipe, Blender or network needed)."""
import json
import math
import tempfile
import unittest
from pathlib import Path

import finder as FI
import match as MA
import measure as ME
import motion_chain as MC
import read as RD
import retarget as RT


def person(pid, x=0.5, lean=0.0, squat=0.0, y=0.3):
    """A made-up tracked person: 33 points in the frame and in metres, leaning `lean` degrees, hips dropped by `squat`."""
    w = [[0.0, 0.0, 0.0] for _ in range(33)]
    s, c = math.sin(math.radians(lean)), math.cos(math.radians(lean))
    sh = [0.0, -0.45 * c, -0.45 * s]                       # the shoulders: up, and toward the lens when leaning
    w[11], w[12] = [0.17, sh[1], sh[2]], [-0.17, sh[1], sh[2]]
    w[23], w[24] = [0.1, 0.0, 0.0], [-0.1, 0.0, 0.0]
    w[0] = [0.0, sh[1] - 0.2, sh[2] - 0.1]
    w[7], w[8] = [0.07, sh[1] - 0.2, sh[2]], [-0.07, sh[1] - 0.2, sh[2]]
    w[13], w[14], w[15], w[16] = [0.2, sh[1] + 0.25, sh[2]], [-0.2, sh[1] + 0.25, sh[2]], [0.2, 0.05, 0.0], [-0.2, 0.05, 0.0]
    w[19], w[20] = [0.2, 0.12, 0.0], [-0.2, 0.12, 0.0]
    w[25], w[26], w[27], w[28] = [0.1, 0.42, 0.0], [-0.1, 0.42, 0.0], [0.1, 0.85, 0.0], [-0.1, 0.85, 0.0]
    b = [[x + p[0] * 0.5, y + squat + 0.25 + p[1] * 0.5, 0.9] for p in w]
    body = [b[0], [x, y + squat + 0.03, 0.9]] + [b[0]] * 16
    return {"id": pid, "body33": b, "world": w, "body": body, "hands": [], "face": [], "box": [x - 0.1, y, 0.2, 0.6]}


def pose(frames, fps=16):
    return {"width": 360, "height": 640, "fps": fps, "frames": [{"t": round(i / fps, 3), "people": p} for i, p in enumerate(frames)]}


class Measures(unittest.TestCase):
    def test_a_lean_is_measured_in_degrees(self):
        self.assertAlmostEqual(ME.frame_measures(person(0, lean=0))["lean"], 0.0, places=0)
        self.assertAlmostEqual(ME.frame_measures(person(0, lean=25))["lean"], 25.0, places=0)

    def test_broken_ids_join_into_one_track_and_passers_by_drop(self):
        frames = [[person(0 if i < 10 else 7, 0.3), person(1, 0.7)] + ([person(9, 0.5)] if i == 3 else []) for i in range(20)]
        tr = ME.tracks(pose(frames))
        self.assertEqual(list(tr[0]["people"]), ["A", "B"])
        self.assertEqual(tr[0]["people"]["A"]["ids"], [0, 7])
        self.assertEqual(len(tr[0]["people"]["A"]["rows"]), 20)

    def test_cuts_split_the_clip_and_letters_restart(self):
        tr = ME.tracks(pose([[person(0, 0.3)]] * 32), cuts=[1.0])
        self.assertEqual([(s["from"], s["to"]) for s in tr], [(0.0, 1.0), (1.0, 2.0)])
        self.assertEqual(list(tr[1]["people"]), ["A"])

    def test_an_event_is_what_moves_past_its_floor(self):
        rows = ME.tracks(pose([[person(0, lean=min(30, i * 2))] for i in range(32)]))[0]["people"]["A"]["rows"]
        ev = ME.events(rows)
        self.assertEqual(ev[0]["measure"], "lean")
        self.assertEqual(ev[0]["words"], "leans in")
        self.assertGreater(ev[0]["delta"], 25)

    def test_a_sudden_punch_in_is_an_edit_not_the_operator(self):
        path = [{"t": i / 16, "pan_x": 0.0, "pan_y": 0.0, "zoom": 1.0 if i < 16 else 1.2, "roll": 0.0} for i in range(32)]
        c = ME.camera_read({"frames": path}, [(0.0, 2.0)])[0]
        self.assertEqual(len(c["punch"]), 1)
        self.assertAlmostEqual(c["push"], 0.0, places=2)                 # the operator's own push: none
        # a person walking a phone closer drifts and bobs as the picture grows (a zoom with neither is an edit: see Cuts)
        slow = [{"t": i / 16, "pan_x": 0.004 * math.sin(i), "pan_y": 0.001 * i + 0.004 * math.cos(i * 1.3), "zoom": 1.0 + i * 0.004, "roll": 0.0} for i in range(32)]
        c = ME.camera_read({"frames": slow}, [(0.0, 2.0)])[0]
        self.assertEqual(c["punch"], [])
        self.assertGreater(c["push"], 0.1)                               # a slow push is the operator walking in


class Reader(unittest.TestCase):
    def test_the_3d_pose_keeps_each_bones_direction_in_the_picture(self):
        import people as PE
        b = [[0.5, 0.5, 0.0] for _ in range(33)]
        pts = {0: (0.50, 0.20), 7: (0.53, 0.21), 8: (0.47, 0.21), 11: (0.58, 0.30), 12: (0.42, 0.30), 13: (0.62, 0.42), 14: (0.38, 0.42),
               15: (0.70, 0.36), 16: (0.36, 0.54), 19: (0.72, 0.34), 20: (0.36, 0.57), 23: (0.55, 0.55), 24: (0.45, 0.55),
               25: (0.55, 0.75), 26: (0.45, 0.75), 27: (0.55, 0.95), 28: (0.45, 0.95)}
        for i, (x, y) in pts.items():
            b[i] = [x, y, 0.9]
        frames = [{"t": i / 16, "people": [{"id": 0, "body33": [list(q) for q in b], "mp": None}]} for i in range(6)]
        PE.lift(frames, 360, 640)
        w = frames[0]["people"][0]["world"]
        self.assertEqual(len(w), 33)
        self.assertNotIn("mp", frames[0]["people"][0])
        # the left forearm goes up and to the picture's right, as drawn (x right, y down)
        fx, fy = w[15][0] - w[13][0], w[15][1] - w[13][1]
        self.assertGreater(fx, 0)
        self.assertLess(fy, 0)
        # the hips sit around the origin and the shoulders above them
        self.assertAlmostEqual((w[23][0] + w[24][0]) / 2, 0.0, places=2)
        self.assertLess((w[11][1] + w[12][1]) / 2, -0.3)
        self.assertAlmostEqual(ME.frame_measures(frames[0]["people"][0])["lean"], 0.0, delta=12)


class Limbs(unittest.TestCase):
    def test_a_limb_read_now_and_then_is_left_alone_and_one_read_mostly_is_carried(self):
        def row(arm, leg):
            d = {"spine": {"left": [1, 0, 0], "up": [0, 0, 1]}}
            if arm:
                d["upper_arm.L"] = {"to": [0, 0, -1]}
            if leg:
                d["thigh.L"], d["shin.L"] = {"to": [0, -1, 0]}, {"to": [0, 0, -1]}
            return {"hip": [0, 2, 0], "dirs": d}
        rows = [row(arm=i != 4, leg=i in (2, 3) or i >= 20) for i in range(40)]
        RT._whole_limbs(rows, [0] * 40)
        self.assertTrue(all("upper_arm.L" in r["dirs"] for r in rows))          # missed in one frame: carried over it
        self.assertTrue(all("thigh.L" in r["dirs"] and "shin.L" in r["dirs"] for r in rows))    # a leg followed for half the shot keeps its pose over all of it
        rows = [row(arm=True, leg=i in (2, 3)) for i in range(40)]
        RT._whole_limbs(rows, [0] * 40)
        self.assertFalse(any("thigh.L" in r["dirs"] for r in rows))             # a leg seen for two frames of forty: left alone

    def test_a_bone_does_not_swap_toward_and_away_between_two_frames(self):
        import people as PE
        b = [[0.5, 0.5, 0.0] for _ in range(33)]
        pts = {0: (0.50, 0.20), 7: (0.53, 0.21), 8: (0.47, 0.21), 11: (0.58, 0.30), 12: (0.42, 0.30), 13: (0.62, 0.42), 14: (0.38, 0.42),
               15: (0.63, 0.47), 16: (0.36, 0.54), 23: (0.55, 0.55), 24: (0.45, 0.55), 25: (0.55, 0.75), 26: (0.45, 0.75), 27: (0.55, 0.95), 28: (0.45, 0.95)}
        for i, (x, y) in pts.items():
            b[i] = [x, y, 0.9]                                                   # the left forearm reads very short: tipped far out of the picture
        frames = []
        for i in range(12):
            w = [[0.0, 0.0, 0.0] for _ in range(33)]
            w[13], w[15] = [0.0, 0.0, 0.0], [0.02, 0.05, -0.25 if i < 6 else 0.25]      # the old pose: toward the lens, then (misread) away
            frames.append({"t": i / 16, "people": [{"id": 0, "body33": [list(q) for q in b], "mp": w}]})
        PE.lift(frames, 360, 640)
        zs = [f["people"][0]["world"][15][2] - f["people"][0]["world"][13][2] for f in frames]
        self.assertTrue(all(z < 0 for z in zs))                                  # it stays tipped toward the lens

    def test_a_head_in_profile_faces_along_the_picture_not_out_at_the_lens(self):
        import people as PE
        b = [[0.5, 0.5, 0.0] for _ in range(33)]
        pts = {0: (0.40, 0.21), 7: (0.50, 0.20), 11: (0.56, 0.32), 12: (0.44, 0.32), 23: (0.55, 0.60), 24: (0.45, 0.60)}
        for i, (x, y) in pts.items():
            b[i] = [x, y, 0.9]                                                   # the nose is to the picture's left of the one seen ear
        frames = [{"t": i / 16, "people": [{"id": 0, "body33": [list(q) for q in b], "mp": None}]} for i in range(4)]
        PE.lift(frames, 360, 640)
        w = frames[0]["people"][0]["world"]
        mid = [(w[7][k] + w[8][k]) / 2 for k in range(3)]
        face = [w[0][k] - mid[k] for k in range(3)]
        self.assertLess(face[0], -0.05)                                          # the face points to the picture's left
        self.assertLess(abs(face[2]), 0.03)                                      # and not out toward the lens


class Cuts(unittest.TestCase):
    def test_a_named_cut_moves_onto_the_frame_where_the_picture_changes(self):
        fr = [{"t": i / 16, "jump": 0.3 if i == 30 else 0.01} for i in range(64)]
        p = {"fps": 16, "frames": [{"t": i / 16, "people": []} for i in range(64)]}
        self.assertEqual(ME.shots(p, [1.93], {"frames": fr})[0], (0.0, 1.875))            # 1.93 named, the change is at frame 30

    def test_a_stray_frame_is_no_shot(self):
        p = {"fps": 16, "frames": [{"t": i / 16, "people": []} for i in range(33)]}
        self.assertEqual(ME.shots(p, [2.0]), [(0.0, 2.0)])                               # one frame after the cut: dropped

    def test_a_slow_centred_zoom_with_no_shake_is_an_edit(self):
        path = [{"t": i / 16, "pan_x": 0.0, "pan_y": 0.0, "zoom": 1.0 + 0.12 * i / 31, "roll": 0.0} for i in range(32)]
        c = ME.camera_read({"frames": path}, [(0.0, 2.0)])[0]
        self.assertAlmostEqual(c["edit_zoom"], 0.12, places=2)
        self.assertEqual(c["push"], 0.0)
        self.assertIn("added in the edit", c["words"])
        walk = [dict(p, pan_x=0.004 * math.sin(i), pan_y=0.02 * i / 31 + 0.004 * math.cos(i * 1.3)) for i, p in enumerate(path)]
        c = ME.camera_read({"frames": walk}, [(0.0, 2.0)])[0]
        self.assertEqual(c["edit_zoom"], 0.0)                                            # it drifts and bobs: a person walking in
        self.assertGreater(c["push"], 0.1)


class Read(unittest.TestCase):
    def test_the_answer_is_held_to_its_shape(self):
        got = {"moment": "m", "people": [{"ours": "A", "reference": ["A1"]}, {"reference": ["B1"]}],
               "beats": [{"from": 3, "to": 99, "what": "late", "check": {"who": "A", "measure": "lean", "by": "20", "half_done_at": 3.5}},
                         {"from": 0, "to": 1, "what": "first", "check": {"who": "NOBODY", "measure": "lean", "by": 5}},
                         {"from": 1, "to": 2, "what": "second", "check": {"who": "A", "measure": "wiggle", "by": 5}}]}
        rec = RD.clean(got, ["A"], 5.0)
        self.assertEqual([b["what"] for b in rec["beats"]], ["first", "second", "late"])
        self.assertEqual(rec["beats"][2]["to"], 5.0)                     # held inside the clip
        self.assertEqual(rec["beats"][2]["check"]["by"], 20.0)
        self.assertIsNone(rec["beats"][0]["check"])                      # a person the shot does not have
        self.assertIsNone(rec["beats"][1]["check"])                      # a measure the track does not have
        self.assertEqual(len(rec["dropped"]), 2)                         # and both are said, not hidden
        self.assertEqual(len(rec["people"]), 1)

    def test_a_check_is_held_to_what_the_track_shows(self):
        tr = ME.tracks(pose([[person(0, 0.3), person(1, 0.7, lean=max(0, min(30, (i - 8) * 3)))] for i in range(48)]))
        tags = {"A1": "HIM", "B1": "HER"}
        rec = {"dropped": [], "beats": [
            {"from": 0.4, "to": 2.0, "what": "she leans in", "check": {"who": "HER", "measure": "lean", "moves": "down", "by": 99, "half_done_at": 0.1}},
            {"from": 0.4, "to": 2.0, "what": "she ducks", "check": {"who": "HER", "measure": "knees", "moves": "up", "by": 50}},
            {"from": 0.4, "to": 2.0, "what": "he waits", "check": {"who": "HIM", "measure": "lean", "moves": "up", "by": 20}}]}
        RD.ground(rec, tr, tags)
        c = rec["beats"][0]["check"]
        self.assertEqual((c["moves"], c["from_track"]), ("up", True))        # the model said down; the track says up
        self.assertAlmostEqual(c["by"], 30, delta=3)                         # and by how much
        self.assertEqual(rec["beats"][1]["check"]["measure"], "lean")        # her knees never move: the measure that does
        self.assertIsNone(rec["beats"][2]["check"])                          # he does not move: a hold, no check
        self.assertEqual(len(rec["dropped"]), 1)

    def test_the_prompt_asks_for_no_shot_sizes_and_names_nobody(self):
        text = (Path(RD.PROMPT)).read_text()
        for slot in ("{context}", "{reference}", "{track}", "{held}"):
            self.assertIn(slot, text)
        who = Path(RD.WHO).read_text()
        for slot in ("{context}", "{reference}", "{tags}"):
            self.assertIn(slot, who)
        self.assertIn('"visible"', who)
        self.assertIn("for_the_take", text)
        self.assertIn("Never \"close-up\"", text)


class Finder(unittest.TestCase):
    def test_the_swipe_is_searched_by_what_the_bodies_do(self):
        with tempfile.TemporaryDirectory() as d:
            fm = {"shots": [{"id": "K01", "start": 0, "end": 2.5, "map": {"moments": [{"does": "woman kisses the man's cheek, he leans in"}]}},
                            {"id": "K02", "start": 2.5, "end": 3.0, "map": {"moments": [{"does": "woman kisses his cheek"}]}},
                            {"id": "K03", "start": 3.0, "end": 6.0, "map": {"moments": [{"does": "a hand holds a jar"}]}}]}
            f = Path(d) / "framemap.json"
            f.write_text(json.dumps(fm))
            got = FI.swipe("she kisses his cheek and he leans toward her", f, "swipe.mp4")
            self.assertEqual([c["shot"] for c in got], ["K01", "K02"])
            self.assertTrue(got[1]["short"])                              # half a second shows a pose, not a move
            self.assertFalse(any(c["needs_download"] for c in got))

    def test_nothing_is_downloaded_without_a_name(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "motion").mkdir()
            (Path(d) / "motion" / "candidates.json").write_text(json.dumps({"candidates": [
                {"n": 1, "from_where": "web", "needs_download": True, "url": "https://example.invalid/v"}]}))
            with self.assertRaises(SystemExit):
                FI.yes(d, 1, None)


class Retarget(unittest.TestCase):
    def test_a_body_half_the_size_stands_twice_as_far(self):
        near = RT.person_frame(person(0), 0.5625, RT.LENS / 36.0)
        p = person(0)
        p["body33"] = [[0.5 + (q[0] - 0.5) * 0.5, 0.3 + (q[1] - 0.3) * 0.5, q[2]] for q in p["body33"]]
        far = RT.person_frame(p, 0.5625, RT.LENS / 36.0)
        self.assertAlmostEqual(far["depth"] / near["depth"], 2.0, places=1)

    def test_a_lean_tips_the_stand_ins_spine_toward_the_lens(self):
        up = RT.person_frame(person(0, lean=0), 0.5625, 0.72)["dirs"]["spine"]["up"]
        lean = RT.person_frame(person(0, lean=30), 0.5625, 0.72)["dirs"]["spine"]["up"]
        self.assertAlmostEqual(up[2], 1.0, places=2)                     # upright: the spine points up
        self.assertLess(lean[1], -0.4)                                   # leaning in: it tips toward the camera (-y)

    def test_our_people_follow_the_tracks_the_read_mapped(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "pose.json").write_text(json.dumps(pose([[person(0, 0.3), person(1, 0.7, lean=min(30, i * 2))] for i in range(16)])))
            (d / "motion-read.json").write_text(json.dumps({"people": [{"ours": "HER", "reference": ["B1"]}, {"ours": "HIM", "reference": ["A1"]},
                                                                      {"ours": "GHOST", "reference": []}]}))
            spec = RT.build(d)
            self.assertEqual([p["name"] for p in spec["people"]], ["HER", "HIM"])
            self.assertTrue(any("GHOST" in n for n in spec["notes"]))     # not seen in the reference: said, and left to the fallback
            her = spec["people"][0]["track"]
            self.assertEqual(len(her), 16)
            self.assertGreater(her[0]["at"][0], spec["people"][1]["track"][0]["at"][0])   # she stands to his right, as tracked
            self.assertLess(her[-1]["dirs"]["spine"]["up"][1], her[0]["dirs"]["spine"]["up"][1] - 0.2)   # and leans in as tracked
            self.assertEqual(len(spec["camera"]["track"]), 16)
            self.assertTrue(spec["from_track"])


class TakeCamera(unittest.TestCase):
    def _scene(self, d, camera=None, approved=True):
        (Path(d) / "motion").mkdir()
        tm = {"source": "rehearsal.mp4", "from": 0, "to": 4, "approved": approved}
        if camera:
            tm["camera"] = camera
        (Path(d) / "motion" / "motion.json").write_text(json.dumps({"take_motion": tm}))

    def test_a_tracked_camera_takes_the_written_shot_sizes_out(self):
        with tempfile.TemporaryDirectory() as d:
            self._scene(d, {"from_track": True, "words": "The camera: a phone at eye level. It holds its frame."})
            take = {"motion": {"scene": d}, "camera": {"style": "operator", "move": "handheld-follow", "focus": "rack", "views": [{"name": "A"}],
                                                       "shots": [{"seconds": 2, "framing": "close", "on": "her"}]},
                    "script": [{"speaker": "A", "say": "", "do": "leans in", "camera": "push in on her face"}]}
            got = MC.for_take(take)
            self.assertNotIn("shots", got["camera"])
            self.assertNotIn("style", got["camera"])
            self.assertNotIn("framing", got["camera"])
            self.assertTrue(got["camera"]["from_track"])
            self.assertEqual(got["camera"]["move"], "The camera: a phone at eye level. It holds its frame.")
            self.assertEqual(got["camera"]["views"], [{"name": "A"}])
            self.assertNotIn("camera", got["script"][0])                  # a line's own camera words go too
            self.assertEqual(got["script"][0]["do"], "leans in")
            self.assertIn("shots", got["camera_dropped"])                 # what was taken out is kept on the record
            self.assertIn("shots", take["camera"])                        # the take as written is not changed

    def test_no_tracked_camera_leaves_the_take_as_written(self):
        with tempfile.TemporaryDirectory() as d:
            self._scene(d)
            take = {"motion": {"scene": d}, "camera": {"shots": [{"seconds": 2, "framing": "close"}]}, "script": []}
            self.assertEqual(MC.for_take(take)["camera"], take["camera"])

    def test_motion_that_never_went_through_its_checks_stops_the_take(self):
        with tempfile.TemporaryDirectory() as d:
            self._scene(d, {"from_track": True, "words": "w"}, approved=False)
            with self.assertRaises(SystemExit):
                MC.for_take({"motion": {"scene": d}})
            MC.approve(d, "test")                                         # a recorded override passes it
            self.assertTrue(MC.for_take({"motion": {"scene": d}})["motion"]["approved"])
            with self.assertRaises(SystemExit):
                MC.approve(d, None)                                       # an override carries a name


class Match(unittest.TestCase):
    def _dirs(self, d, clip_lean, clip_zoom=1.0, late=0):
        d = Path(d)
        ref = [[person(0, 0.3), person(1, 0.7, lean=max(0, min(30, (i - 8) * 3)))] for i in range(48)]
        (d / "pose.json").write_text(json.dumps(pose(ref)))
        (d / "camera.json").write_text(json.dumps({"frames": [{"t": i / 16, "pan_x": 0, "pan_y": 0, "zoom": 1.0, "roll": 0} for i in range(48)]}))
        (d / "motion-read.json").write_text(json.dumps({"seconds": 3.0, "people": [{"ours": "HIM", "reference": ["A1"]}, {"ours": "HER", "reference": ["B1"]}],
            "beats": [{"from": 0.5, "to": 2.0, "what": "HER leans in to HIM", "check": {"who": "HER", "measure": "lean", "moves": "up", "by": 30, "half_done_at": 0.8}}]}))
        c = d / "clip"
        c.mkdir()
        clip = [[person(0, 0.3), person(1, 0.7, lean=max(0, min(clip_lean, (i - 8 - late) * 3)))] for i in range(48)]
        (c / "pose.json").write_text(json.dumps(pose(clip)))
        (c / "camera.json").write_text(json.dumps({"frames": [{"t": i / 16, "pan_x": 0, "pan_y": 0, "zoom": 1.0 + (clip_zoom - 1) * i / 47, "roll": 0} for i in range(48)]}))
        return d, c

    def _row(self, rec, word):
        return next(r for r in rec["rows"] if word in r["name"])

    def test_the_same_move_passes(self):
        with tempfile.TemporaryDirectory() as d:
            rec = MA.compare(*self._dirs(d, 30))
            self.assertTrue(self._row(rec, "HER leans in")["ok"])
            self.assertTrue(self._row(rec, "timing")["ok"])
            self.assertTrue(self._row(rec, "camera · push")["ok"])

    def test_a_move_under_half_the_real_one_fails(self):
        with tempfile.TemporaryDirectory() as d:
            row = self._row(MA.compare(*self._dirs(d, 9)), "HER leans in")
            self.assertFalse(row["ok"])
            self.assertIn("of 30", row["short"])

    def test_a_late_move_fails_on_timing(self):
        with tempfile.TemporaryDirectory() as d:
            rec = MA.compare(*self._dirs(d, 30, late=14))
            self.assertTrue(self._row(rec, "HER leans in")["ok"])
            self.assertFalse(self._row(rec, "timing")["ok"])

    def test_someone_the_footage_shows_and_the_tracker_missed_fails_the_preview(self):
        with tempfile.TemporaryDirectory() as d:
            d, c = self._dirs(d, 30)
            read = json.loads((d / "motion-read.json").read_text())
            read.update({"tags": {"A1": "HIM", "B1": "HER"}, "visible": {"1": ["HIM", "HER", "THIRD"]}})
            (d / "motion-read.json").write_text(json.dumps(read))
            self.assertFalse(any("reference ·" in r["name"] for r in MA.compare(d, c)["rows"]))   # a take is not blamed for the reference's track
            p = json.loads((c / "pose.json").read_text())                 # the rehearsal (exact joints, named people) is
            p["exact"] = True
            for f in p["frames"]:
                for q, nm in zip(f["people"], ("HIM", "HER")):
                    q["name"] = nm
            (c / "pose.json").write_text(json.dumps(p))
            rec = MA.compare(d, c)
            row = self._row(rec, "reference · THIRD in shot 1")
            self.assertFalse(row["ok"])
            self.assertFalse(row["holds"])                                # named in no beat of the shot: a bystander, noted
            self.assertIn("stands still", row["short"])
            self.assertEqual(rec["held_by"], [])
            self.assertFalse(any("reference · HER" in r["name"] for r in rec["rows"]))
            read["visible"] = {"1": ["HIM", "HER", "THIRD"]}
            read["beats"].append({"from": 2.0, "to": 2.8, "what": "THIRD steps in", "starts": "THIRD", "check": None})
            (d / "motion-read.json").write_text(json.dumps(read))
            row = self._row(MA.compare(d, c), "reference · THIRD in shot 1")
            self.assertTrue(row["holds"])                                 # someone who acts in the shot and was never followed: holds

    def test_a_rehearsal_is_laid_over_its_footage(self):
        with tempfile.TemporaryDirectory() as d:
            d, c = self._dirs(d, 30)
            p = json.loads((d / "pose.json").read_text())                 # a rehearsal: the same joints, exact, named
            p["exact"] = True
            for f in p["frames"]:
                for q, nm in zip(f["people"], ("HIM", "HER")):
                    q["name"] = nm
            (c / "pose.json").write_text(json.dumps(p))
            rec = MA.compare(d, c)
            self.assertTrue(self._row(rec, "on the footage · HER")["ok"])
            self.assertTrue(self._row(rec, "framing · HER")["ok"])
            for f in p["frames"]:                                         # the same people standing twice as far off: half the size
                for q in f["people"]:
                    q["body33"] = [[0.5 + (v[0] - 0.5) * 0.5, 0.5 + (v[1] - 0.5) * 0.5, v[2]] for v in q["body33"]]
            (c / "pose.json").write_text(json.dumps(p))
            rec = MA.compare(d, c)
            self.assertFalse(self._row(rec, "framing · HER")["ok"])
            self.assertIn("50%", self._row(rec, "framing · HER")["short"])

    def test_one_person_split_over_two_ids_is_one_person_seen(self):
        with tempfile.TemporaryDirectory() as d:
            d, c = self._dirs(d, 30)
            read = json.loads((d / "motion-read.json").read_text())
            read["people"] = [{"ours": "HER", "reference": ["A1", "B1"]}]     # both tracks are her
            (d / "motion-read.json").write_text(json.dumps(read))
            p = json.loads((c / "pose.json").read_text())
            for f in p["frames"]:
                f["people"] = f["people"][1:]                                 # the clip shows her alone, which is right
            (c / "pose.json").write_text(json.dumps(p))
            self.assertTrue(self._row(MA.compare(d, c), "people seen")["ok"])

    def test_a_curve_running_late_is_measured_as_late(self):
        ref = ME.tracks(pose([[person(0, 0.5, lean=max(0, min(30, (i - 8) * 3)))] for i in range(64)]))[0]["people"]["A"]["rows"]
        late = ME.tracks(pose([[person(0, 0.5, lean=max(0, min(30, (i - 20) * 3)))] for i in range(64)]))[0]["people"]["A"]["rows"]
        self.assertAlmostEqual(MA._lag(ref, late, "lean", 0.3, 1.5), 0.75, delta=0.13)
        self.assertAlmostEqual(MA._lag(ref, ref, "lean", 0.3, 1.5), 0.0, delta=0.07)

    def test_a_push_in_the_reference_never_made_fails(self):
        with tempfile.TemporaryDirectory() as d:
            d, c = self._dirs(d, 30, clip_zoom=1.2)
            # a zoom about the centre with no drift or shake: failed as a zoom (it belongs to the edit)
            self.assertFalse(self._row(MA.compare(d, c), "camera · slow zoom")["ok"])
            # the same growth with the drift and bob of a person walking in: failed as a push the reference never made
            cam = json.loads((c / "camera.json").read_text())
            for i, f in enumerate(cam["frames"]):
                f.update({"pan_x": 0.004 * math.sin(i), "pan_y": 0.001 * i + 0.004 * math.cos(i * 1.3)})
            (c / "camera.json").write_text(json.dumps(cam))
            self.assertFalse(self._row(MA.compare(d, c), "camera · push")["ok"])


class Decides(unittest.TestCase):
    """Nobody approves motion: the chain passes it or holds it on its own checks."""

    def _scene(self, d, rows=None, verdict=None, start=None):
        m = Path(d) / "motion"
        m.mkdir()
        (m / "motion.json").write_text(json.dumps({"status": "tracked", "kind": "real-skeleton",
                                                   "take_motion": {"source": str(m / "rehearsal" / "blocking.mp4"), "from": 0, "to": 4, "approved": False}}))
        if rows is not None:
            (m / "match-rehearsal.json").write_text(json.dumps({"rows": rows, "passed": sum(1 for r in rows if r["ok"]), "failed": sum(1 for r in rows if r["ok"] is False),
                                                                "held_by": ["%s: %s" % (r["name"], r["short"]) for r in rows if r["ok"] is False and r.get("holds")]}))
        if verdict is not None:
            (m / "verdict.json").write_text(json.dumps(verdict))
        if start is not None:
            (m / "match-start-picture.json").write_text(json.dumps({"rows": start, "passed": sum(1 for r in start if r["ok"]), "failed": sum(1 for r in start if r["ok"] is False)}))
        return m

    def test_motion_that_passes_its_checks_goes_to_the_take_with_nobody_asked(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, rows=[{"name": "1 · she leans in", "ok": True, "short": "leans in 20 of 22", "holds": True}],
                            verdict={"verdict": "close, small faults", "holds": [], "faults": [{"what": "a mitten clips", "matters": "barely"}]})
            won = MC.decide(d)
            self.assertTrue(won["ok"])
            self.assertEqual(json.loads((m / "motion.json").read_text())["status"], "approved")
            self.assertTrue(MC.for_take({"motion": {"scene": d}})["motion"]["approved"])
            self.assertEqual(json.loads((m / "chain.json").read_text())["stages"]["approve"]["short"], "passed")

    def test_a_fail_that_matters_holds_it_with_the_reason_and_no_take_is_made(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, rows=[{"name": "framing · HER", "ok": False, "short": "50% of the real size", "holds": True}])
            won = MC.decide(d)
            self.assertFalse(won["ok"])
            self.assertEqual(json.loads((m / "motion.json").read_text())["status"], "held")
            with self.assertRaises(SystemExit) as e:
                MC.for_take({"motion": {"scene": d}})
            self.assertIn("framing · HER: 50% of the real size", str(e.exception))
            self.assertNotIn("approv", str(e.exception).lower())           # it waits for nobody
            self.assertTrue(json.loads((m / "chain.json").read_text())["stages"]["approve"]["short"].startswith("held: framing · HER"))
            self.assertTrue(MC.for_take({"motion": {"scene": d}}, dry_run=True)["motion"]["source"].endswith("blocking.mp4"))   # a dry run still plans

    def test_a_noted_fail_does_not_hold(self):
        with tempfile.TemporaryDirectory() as d:
            self._scene(d, rows=[{"name": "1 · she leans in", "ok": True, "short": "ok", "holds": True},
                                 {"name": "reference · HIM in shot 3", "ok": False, "short": "not followed (stands still)", "holds": False},
                                 {"name": "1 · she leans in · timing", "ok": False, "short": "0.6 s early", "holds": False}])
            self.assertTrue(MC.decide(d)["ok"])

    def test_the_watcher_holds_a_shot_whose_move_is_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self._scene(d, rows=[{"name": "1 · she leans in", "ok": True, "short": "ok", "holds": True}],
                        verdict={"verdict": "not yet", "holds": ["shot 3: the move does not happen as in the footage"]})
            won = MC.decide(d)
            self.assertFalse(won["ok"])
            self.assertIn("the watcher, shot 3: the move does not happen as in the footage", won["held"])

    def test_a_start_picture_that_does_not_match_is_judged_apart_from_the_motion(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, rows=[{"name": "1 · she leans in", "ok": True, "short": "ok", "holds": True}],
                            start=[{"name": "start picture · HER framing", "ok": False, "short": "42% of the rehearsal's size"}])
            won = MC.decide(d)
            self.assertTrue(won["passed"])                                 # the motion is fine
            self.assertEqual(won["picture"], ["start picture · HER framing: 42% of the rehearsal's size"])
            self.assertEqual(json.loads((m / "motion.json").read_text())["take_motion"]["held"], [])   # a take with another picture is not blocked by it
            stages = json.loads((m / "chain.json").read_text())["stages"]
            self.assertFalse(stages["picture"]["ok"])                       # but the board says the picture does not match

    def test_rows_written_before_the_chain_decided_are_judged_by_holds_only_when_they_say_so(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, rows=[{"name": "reference · HIM in shot 3", "ok": False, "short": "not followed"}])
            rows = json.loads((m / "match-rehearsal.json").read_text())
            rows.pop("held_by")                                            # an old file, and no rehearsal here to measure again
            (m / "match-rehearsal.json").write_text(json.dumps(rows))
            self.assertFalse(MC.decide(d)["ok"])                           # without a way to measure again, an old fail still holds

    def test_motion_never_checked_is_not_passed(self):
        with tempfile.TemporaryDirectory() as d:
            self._scene(d)
            self.assertFalse(MC.decide(d)["ok"])

    def test_an_override_is_recorded_and_does_not_outlive_the_motion(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, rows=[{"name": "framing · HER", "ok": False, "short": "50% of the real size", "holds": True}])
            MC.decide(d)
            MC.approve(d, "a named person")
            rec = json.loads((m / "motion.json").read_text())
            self.assertEqual(rec["override"]["by"], "a named person")
            self.assertEqual(rec["override"]["over"], ["framing · HER: 50% of the real size"])     # what it overrode is kept
            self.assertTrue(MC.for_take({"motion": {"scene": d}})["motion"]["approved"])
            self.assertTrue(MC.decide(d)["ok"] is False)                                           # the checks still say held...
            self.assertEqual(json.loads((m / "motion.json").read_text())["status"], "approved")    # ...and the recorded override stands
            self.assertTrue(MC.for_take({"motion": {"scene": d}})["motion"]["approved"])
            self.assertIn("overridden by a named person", json.loads((m / "chain.json").read_text())["stages"]["approve"]["short"])

    def test_an_approval_given_before_the_chain_decided_is_kept_as_an_override(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, rows=[{"name": "framing · HER", "ok": False, "short": "50% of the real size", "holds": True}])
            rec = json.loads((m / "motion.json").read_text())
            rec.update({"status": "approved", "approved_by": "someone, earlier", "approved_at": "2026-11-12T20:00:00"})
            rec["take_motion"]["approved"] = True
            (m / "motion.json").write_text(json.dumps(rec))
            MC.decide(d)                                                   # a take armed on that approval keeps going
            self.assertTrue(MC.for_take({"motion": {"scene": d}})["motion"]["approved"])
            self.assertTrue(json.loads((m / "motion.json").read_text())["override"]["from_before"])

    def test_a_check_made_against_an_older_rehearsal_does_not_count(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, rows=[{"name": "1 · she leans in", "ok": True, "short": "ok", "holds": True}],
                            start=[{"name": "start picture · HER framing", "ok": False, "short": "42% of the rehearsal's size"}])
            (m / "rehearsal").mkdir()
            (m / "rehearsal" / "pose.json").write_text("{}")
            sp = json.loads((m / "match-start-picture.json").read_text())
            sp["rehearsal_stamp"] = "1.000|1.000"                          # checked against a rehearsal that is gone
            (m / "match-start-picture.json").write_text(json.dumps(sp))
            self.assertEqual(MC.decide(d)["picture"], [])                  # the old picture check does not count
            rows = json.loads((m / "match-rehearsal.json").read_text())
            rows["rehearsal_stamp"] = "1.000|1.000"
            (m / "match-rehearsal.json").write_text(json.dumps(rows))
            won = MC.decide(d)
            self.assertFalse(won["ok"])
            self.assertIn("the reference or the rehearsal changed since they were last checked", won["held"])

    def test_camera_only_and_programmed_motion_stay_passed_on_any_later_decision(self):
        for rec in ({"status": "approved", "camera_only": True, "kind": "swipe", "take_motion": {"source": "ref.mp4", "approved": True}},
                    {"status": "ready", "kind": "programmed", "take_motion": {"source": "blocking.mp4", "approved": True}}):
            with tempfile.TemporaryDirectory() as d:
                (Path(d) / "motion").mkdir()
                (Path(d) / "motion" / "motion.json").write_text(json.dumps(rec))
                self.assertTrue(MC.decide(d)["passed"])
                self.assertTrue(MC.decide(d)["passed"])
                self.assertTrue(MC.for_take({"motion": {"scene": d}})["motion"]["approved"])

    def test_a_clip_read_after_the_rehearsal_is_not_passed_on_the_old_checks(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, rows=[{"name": "1 · she leans in", "ok": True, "short": "ok", "holds": True}])
            self.assertTrue(MC.decide(d)["passed"])
            rec = json.loads((m / "motion.json").read_text())           # someone drops a phone act-out on the scene
            rec.update({"kind": "phone", "status": "tracked"})
            rec["take_motion"] = {"source": str(m / "source.mov"), "from": 0, "to": 4, "approved": False}
            (m / "motion.json").write_text(json.dumps(rec))
            won = MC.decide(d)
            self.assertFalse(won["passed"])
            self.assertIn("has not been rehearsed and checked", won["held"][0])

    def test_an_override_counts_everywhere_the_motion_is_asked_for(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, rows=[{"name": "framing · HER", "ok": False, "short": "50% of the real size", "holds": True}])
            MC.decide(d)
            MC.approve(d, "a named person")
            self.assertTrue(MC.decide(d)["passed"])
            self.assertTrue(MC.ready(d, picture=False)["ok"])             # the one-go command honours it too

    def test_the_take_is_not_refused_for_a_person_nobody_asked(self):
        text = (Path(MC.__file__).read_text() + Path(MC.__file__).with_name("CLAUDE.md").read_text()).lower()
        self.assertNotIn("waits for approval", text)
        self.assertNotIn("waits for a yes", text)


class Builds(unittest.TestCase):
    def test_a_torso_is_read_where_the_body_is_not_where_the_arms_hang(self):
        import build as BU
        H, W = 400, 300
        mask = [[0] * W for _ in range(H)]
        pts = {"lsh": (190, 100), "rsh": (110, 100), "lhip": (175, 300), "rhip": (125, 300), "lel": (200, 200), "rel": (100, 200), "lwr": (205, 300), "rwr": (95, 300)}
        for y in range(80, 380):
            f = (y - 100) / 200.0
            half = 45 if f < 0.48 else (35 if f < 0.85 else 55)            # chest 90 px, waist 70 px, hips 110 px wide
            for x in range(150 - half, 150 + half + 1):
                mask[y][x] = 1
            for ax in (200, 100):                                          # arms hanging against the body
                for x in range(ax - 8, ax + 9):
                    mask[y][x] = 1
        w = BU.widths(mask, pts, arm_r=8 / 200.0)                          # the arms drawn here are 8 px either side of their line
        self.assertAlmostEqual(w["waist"], 71 / 200.0, delta=0.03)          # the arms are kept out of it
        self.assertGreater(w["chest"], w["waist"])
        self.assertGreater(w["hips"], w["waist"])

    def test_words_give_a_build_when_there_is_no_sheet(self):
        import build as BU
        slim = BU.from_words("a slim woman in a floral dress")["widths"]
        broad = BU.from_words("broad man, full beard")["widths"]
        self.assertLess(slim["waist"], slim["chest"])
        self.assertGreater(broad["waist"], slim["waist"] * 1.4)

    def test_a_sheets_jacket_hem_is_not_a_mans_hips(self):
        import build as BU
        w, changed = BU.plausible({"chest": 0.72, "waist": 0.63, "hips": 0.96}, "Black man late twenties, black suit")
        self.assertLessEqual(w["hips"], 0.72 * 1.12 + 1e-6)
        self.assertTrue(changed)
        w, changed = BU.plausible({"chest": 0.59, "waist": 0.52, "hips": 0.85}, "Black woman about 27")
        self.assertEqual(w["hips"], 0.85)                                   # a woman's hips at that share stand
        self.assertFalse(changed)


class Watcher(unittest.TestCase):
    def test_the_verdict_comes_from_the_shots_not_the_models_own_word(self):
        import watch as WA
        text = Path(WA.PROMPT).read_text()
        for slot in ("{seconds}", "{cuts}", "{people}", "{failed}"):
            self.assertIn(slot, text)
        self.assertIn('"move_matches"', text)
        src = Path(WA.__file__).read_text()
        self.assertIn('x.get("move_matches") is False or x.get("placed") is False or x.get("sized") is False', src)


class StartPicture(unittest.TestCase):
    def test_a_picture_framed_like_the_rehearsal_passes_and_a_wide_one_fails(self):
        reh = [dict(person(0, 0.3), name="HIM"), dict(person(1, 0.7), name="HER")]
        same = [person(5, 0.31), person(6, 0.69)]
        rows = MA.start_rows(reh, same)
        self.assertTrue(all(r["ok"] for r in rows))
        self.assertEqual(rows[0]["name"], "start picture · people")
        wide = [dict(p, body33=[[0.5 + (v[0] - 0.5) * 0.45, 0.6 + (v[1] - 0.6) * 0.45, v[2]] for v in p["body33"]]) for p in same]
        rows = MA.start_rows(reh, wide)                                        # the same two people, drawn full-length and far off
        bad = [r for r in rows if r["ok"] is False]
        self.assertTrue(any("framing" in r["name"] for r in bad))
        self.assertIn("45%", next(r for r in bad if "HER framing" in r["name"])["short"])

    def test_someone_missing_from_the_picture_fails(self):
        reh = [dict(person(0, 0.3), name="HIM"), dict(person(1, 0.7), name="HER")]
        rows = MA.start_rows(reh, [person(5, 0.3)])
        self.assertFalse(rows[0]["ok"])
        self.assertTrue(any(r["name"] == "start picture · HER" and r["ok"] is False for r in rows))


class FrameWords(unittest.TestCase):
    def test_the_first_frame_is_said_as_where_how_much_and_which_way(self):
        p = dict(person(0, 0.7, y=0.1), name="HER")
        for i in (25, 26, 27, 28):                       # a close frame: the legs are out of it
            p["body33"][i] = [p["body33"][i][0], 1.3, 0.0]
        text = MC.framing_words([p])
        self.assertIn("HER: head in the upper right of the frame", text)
        self.assertIn("head to hips, no legs in frame", text)
        self.assertIn("facing the camera", text)
        self.assertIn("do not pull back", text)
        full = MC.framing_words([dict(person(0, 0.5, y=0.05), name="HIM")])
        self.assertIn("the whole body, feet in frame", full)


class WhoIsWho(unittest.TestCase):
    def test_a_persons_correction_wins_over_the_models_word(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "pose.json").write_text(json.dumps(pose([[person(0, 0.3), person(1, 0.7, lean=min(30, i * 2))] for i in range(16)])))
            (d / "motion-read.json").write_text(json.dumps({"tags": {"A1": "HER", "B1": "HIM"},
                                                            "people": [{"ours": "HER", "reference": ["A1"]}, {"ours": "HIM", "reference": ["B1"]}]}))
            before = RT.build(d)
            self.assertLess(before["people"][0]["track"][0]["at"][0], before["people"][1]["track"][0]["at"][0])   # the model had her on the left
            (d / "who.json").write_text(json.dumps({"a1": "HIM", "B1": "HER", "_by": "someone"}))
            read = ME.read_of(d)
            self.assertEqual({p["ours"]: p["reference"] for p in read["people"]}, {"HER": ["B1"], "HIM": ["A1"]})
            after = RT.build(d)
            her = next(p for p in after["people"] if p["name"] == "HER")
            him = next(p for p in after["people"] if p["name"] == "HIM")
            self.assertGreater(her["track"][0]["at"][0], him["track"][0]["at"][0])       # corrected: she is the one on the right
            self.assertLess(her["track"][-1]["dirs"]["spine"]["up"][1], -0.2)            # and the lean is hers

    def test_an_extra_is_nobody(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "motion-read.json").write_text(json.dumps({"tags": {"A1": "HER", "B1": "HER"}, "people": [{"ours": "HER", "reference": ["A1", "B1"]}]}))
            (d / "who.json").write_text(json.dumps({"B1": "extra"}))
            self.assertEqual(ME.read_of(d)["people"][0]["reference"], ["A1"])


class LongScenes(unittest.TestCase):
    def _scene(self, d, seconds, cuts, beat_ends):
        m = Path(d) / "motion"
        m.mkdir()
        (m / "ref.json").write_text(json.dumps({"seconds": seconds, "cuts": cuts}))
        beats, at = [], 0.0
        for e in beat_ends:
            beats.append({"from": at, "to": e, "what": "beat to %s" % e, "starts": "A"})
            at = e
        (m / "motion-read.json").write_text(json.dumps({"seconds": seconds, "beats": beats, "people": [{"ours": "A", "reference": []}]}))
        return m

    def test_a_scene_that_fits_is_one_part(self):
        with tempfile.TemporaryDirectory() as d:
            parts = MC.segments(self._scene(d, 12.0, [4.0], [4.0, 9.0, 12.0]))
            self.assertEqual([(p["from"], p["to"]) for p in parts], [(0.0, 12.0)])

    def test_a_long_scene_splits_at_its_cuts_then_its_beat_ends_never_over_the_limit(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, 37.7, [13.0, 30.0], [5.0, 13.0, 19.5, 26.0, 30.0, 37.7])
            parts = MC.segments(m)
            self.assertEqual([(p["from"], p["to"]) for p in parts], [(0.0, 13.0), (13.0, 26.0), (26.0, 37.7)])
            self.assertEqual([p["starts_at"] for p in parts], ["the start", "a cut", "a beat's end"])
            self.assertTrue(all(p["seconds"] <= MC.TAKE_MAX for p in parts))
            self.assertEqual(json.loads((m / "segments.json").read_text())[2]["k"], 3)

    def test_with_nothing_to_split_on_it_splits_evenly_with_no_stub(self):
        with tempfile.TemporaryDirectory() as d:
            parts = MC.segments(self._scene(d, 32.0, [], [32.0]))
            self.assertEqual(len(parts), 3)
            self.assertTrue(all(10.0 <= p["seconds"] <= MC.TAKE_MAX for p in parts))    # three takes of about the same length, none a two-second stub
            self.assertEqual(parts[-1]["to"], 32.0)

    def test_a_take_names_its_part_and_gets_that_parts_seconds_and_beats(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, 37.7, [13.0, 30.0], [5.0, 13.0, 19.5, 26.0, 30.0, 37.7])
            MC.segments(m)
            (m / "motion.json").write_text(json.dumps({"take_motion": {"source": "rehearsal.mp4", "from": 0, "to": 37.7, "approved": True}}))
            got = MC.for_take({"motion": {"scene": d, "segment": 2}, "script": []})
            self.assertEqual((got["motion"]["from"], got["motion"]["to"]), (13.0, 26.0))
            self.assertEqual(len(got["mechanics"]), 2)                    # the two beats inside 13-26 s
            self.assertTrue(got["mechanics"][0].startswith("0.0-6.5 s"))  # on the part's own clock
            with self.assertRaises(SystemExit):
                MC.for_take({"motion": {"scene": d, "segment": 9}, "script": []})


class Board(unittest.TestCase):
    def test_every_stage_and_match_row_reaches_the_board(self):
        with tempfile.TemporaryDirectory() as B:
            d = Path(B) / "scenes" / "S1" / "take" / "motion"
            d.mkdir(parents=True)
            MC._say(d, "read", True, "6 beats", "the moment", file="motion-read.json")
            MC._say(d, "approve", False, "held: framing · HER: 50% of the real size")
            (d / "match-take.json").write_text(json.dumps({"rows": [{"name": "1 · leans in", "ok": False, "short": "9° of 30°", "detail": "x"}]}))
            rows = MC.rows(B)
            self.assertEqual([r["group"] for r in rows], ["Motion chain", "Motion chain", "Motion match · S1/take · take"])
            self.assertEqual([r["ok"] for r in rows], [True, False, False])
            self.assertEqual(rows[1]["name"], "S1/take · Motion checks")
            self.assertTrue(rows[1]["short"].startswith("held: "))
            for r in rows:
                self.assertEqual(set(r), {"group", "name", "ok", "short", "detail", "pics", "video"})


if __name__ == "__main__":
    unittest.main()


def test_an_insert_shot_with_no_body_is_noted_not_failed():
    """A face close-up, hands or the product: the tracker finds no body in the shot, so `reference · NAME in shot N`
    is noted (ok None) and never holds the motion (12 Nov 2026)."""
    import match as MA
    src = Path(MA.__file__).read_text()
    assert "insert: no body in the shot" in src


class OurBeatsNotTheReferenceMoves(unittest.TestCase):
    """15 Nov 2026: a reference that does not show our beats' moves gives the timing and the camera only."""

    def _scene(self, d, missing):
        m = Path(d) / "motion"
        m.mkdir()
        (m / "motion.json").write_text(json.dumps({"status": "tracked", "kind": "real-skeleton",
                                                   "take_motion": {"source": str(m / "rehearsal" / "blocking.mp4"), "from": 0, "to": 4, "approved": False}}))
        (m / "match-rehearsal.json").write_text(json.dumps({"rows": [{"name": "1 · she leans in", "ok": True, "short": "ok"}], "passed": 1, "failed": 0, "held_by": []}))
        (m / "motion-read.json").write_text(json.dumps({"beats": [{"from": 0, "to": 2, "what": "she sniffs his neck"}], "missing": missing}))
        return m

    def test_a_reference_missing_our_move_holds_its_own_rehearsal(self):
        with tempfile.TemporaryDirectory() as d:
            self._scene(d, ["woman lifts a small lens to her eye and leans in"])
            won = MC.decide(d)
            self.assertFalse(won["passed"])
            self.assertIn("does not show our beat's move (woman lifts a small lens", won["held"][0])
            self.assertIn("motion_chain.py ours", won["held"][0])

    def test_an_override_never_passes_the_reference_acting_another_moment(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, ["woman points down a hallway"])
            rec = json.loads((m / "motion.json").read_text())
            rec["override"] = {"by": "someone", "at": "2026-11-14T10:00:00", "over": []}
            (m / "motion.json").write_text(json.dumps(rec))
            self.assertFalse(MC.decide(d)["passed"])

    def test_a_reference_showing_everything_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            self._scene(d, [])
            self.assertTrue(MC.decide(d)["passed"])

    def test_programmed_from_ours_passes_and_carries_no_reference_mechanics(self):
        with tempfile.TemporaryDirectory() as d:
            m = self._scene(d, ["woman lifts a small lens to her eye"])
            rec = json.loads((m / "motion.json").read_text())
            rec.update({"kind": "programmed", "ours_because": ["woman lifts a small lens to her eye"]})
            rec["take_motion"] = {"source": str(m / "rehearsal" / "blocking.mp4"), "from": 0, "to": 4, "approved": True,
                                  "camera": {"from_track": True, "words": "The camera: a phone. It holds its frame."}}
            (m / "motion.json").write_text(json.dumps(rec))
            self.assertTrue(MC.decide(d)["passed"])
            got = MC.for_take({"motion": {"scene": d}, "script": [{"speaker": "A", "do": "lifts the lens to her eye"}]})
            self.assertNotIn("mechanics", got)                 # "she sniffs his neck" never reaches the take
            self.assertTrue(got["camera"]["from_track"])       # the reference's camera stays

    def test_our_lines_land_on_the_reference_beats_in_order(self):
        beats = [{"from": 0.0, "to": 2.6}, {"from": 2.7, "to": 3.8}, {"from": 3.9, "to": 6.8}, {"from": 6.9, "to": 10.3}, {"from": 10.4, "to": 15.0}]
        rows, secs = MC.ref_timing({"script": [{"speaker": "J"}] * 5}, {"beats": beats}, 15.01)
        self.assertEqual([(r["from"], r["to"]) for r in rows], [(b["from"], b["to"]) for b in beats])
        self.assertEqual(secs, 15.01)
        rows, _ = MC.ref_timing({"script": [{"speaker": "J"}] * 2}, {"beats": beats})
        self.assertEqual([(r["from"], r["to"]) for r in rows], [(0.0, 6.8), (6.9, 15.0)])
        rows, _ = MC.ref_timing({"script": [{"speaker": "J"}] * 6}, {"beats": beats[:3]})
        self.assertEqual(len(rows), 6)
        self.assertEqual((rows[0]["from"], rows[1]["to"]), (0.0, 2.6))
        self.assertEqual(MC.ref_timing({"script": []}, {"beats": beats}), (None, None))


def test_the_figures_carry_a_squat_and_a_lens_to_the_eye():
    """Our beats' own moves exist in the 3D blocking: a squat, a hand at its own eye, a reach to the jaw or neck."""
    import motion_program as MP
    src = (Path(MC.__file__).parent / "blocking_blender.py").read_text()
    assert '"squat" in b' in src and '"eye":' in src and '"neck":' in src and '"jaw":' in src
    assert "squat" in MP.ACTIONS
    spec = MP.clean({"people": [{"name": "A"}], "beats": [{"from": 0, "to": 1, "who": "A", "squat": 1}]}, 4)
    assert spec["beats"] == [{"from": 0.0, "to": 1.0, "who": "A", "squat": 1}] and not spec["dropped"]


def test_a_move_said_in_words_is_read_into_the_figures_terms():
    import motion_program as MP
    n = ["A", "B"]
    assert MP.value("tilt", "chin up, held", n) == 10.0
    assert MP.value("lean", "B.jaw (to ~10 cm)", n) == 20.0          # a distance is not a size
    assert MP.value("lean", "back, upright", n) == 0.0
    assert MP.value("reach", "A.eye (lens to the right eye)", n) == "A.eye"
    assert MP.value("reach", "forearm (own, a nail drawn down it)", n) == "ME.forearm"
    assert MP.value("point", "down the corridor behind-right", n) == ["rel", 1, 1]
    assert MP.value("look", "head fully to B", n) == "B"
    assert MP.value("sit", "settles into the chair", n) is True
