"""Clips from the storyboard (2026-10-02): only the clips storyboard.json calls
for, each from an approved picture, on the ruled clip door, every prompt
written out. A made-up two-person demo — no video, no model, no network."""
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from types import SimpleNamespace

import clips_plan as cp

PIECE = {"aspect": "9:16", "style": "Phone-grade vertical video, natural colour."}


def scene(sid, who, to_camera, voice, beats, setting="ROOM", delta="she looks at the lens", camera="same"):
    return {"id": sid, "who": who, "to_camera": to_camera, "voice": voice, "setting": setting,
            "happens": f"does the {sid} thing",
            "frames": [{"role": "first", "subject": f"{who} in the room for {sid}",
                        "composition": "Close-up, centred", "action": "mid-word",
                        "lighting": "soft window light"},
                       {"role": "last", "camera": camera, "delta": delta}],
            "beats": [{"do": d, "over": ""} for d in beats]}


SCENES = [
    scene("S1", "HOST", True, "hello there friends", ["looks up", "smiles"]),
    scene("S2", "HELPER's hands", False, "we press it right here", ["presses the spot"]),
    scene("S3", "HOST", True, "and that is it", ["nods"]),
    {"id": "S4", "kind": "card", "to_camera": False, "voice": "", "frames": [], "beats": []},
    scene("S5", "HOST's hand", False, "two for one today", ["turns the tube"], delta="the label faces the lens"),
    scene("S6", "HOST", True, "first half of a long line", ["talks"]),
    scene("S7", "HOST", True, "and the rest of it", ["stops"]),
]


def section(gid, scenes, maker, frames, clips, voice, shots=(), seconds=None, reuses=None):
    return {"id": gid, "scenes": scenes, "maker": maker, "frames": frames, "clips": clips,
            "voice": voice, "voice_from": {k: "recorded" for k in voice},
            "seconds": seconds or round(sum(voice.values()) + 0.15 * max(0, len(voice) - 1), 2),
            "elements": ["person · HOST · look-1", "person · HELPER · coat"],
            "swipe": {"shots": list(shots)}, "reuses": reuses}


def shot(k, at, typ="set-up shot", frame="Creator centred"):
    return {"id": k, "type": typ, "at": at, "frame": frame}


SB = {"teardown": None, "people_map": {"lead": ["HOST", "Creator"], "others": {}},
      "sections": [
          section("G01", ["S1"], "lip-sync", [{"what": "start frame", "from": "S1"}],
                  [{"scenes": ["S1"], "seconds": 3.0, "starts_from": "the section's start picture"}], {"S1": 3.0}),
          section("G02", ["S2", "S3"], "motion transfer",
                  [{"what": "start frame · set-up shot", "from": "S2", "copies": "K02", "drives": ["K02"], "own": False},
                   {"what": "start frame · handheld selfie", "from": "S3", "copies": "K03", "drives": ["K03"], "own": True}],
                  [{"scenes": ["S2", "S3"], "seconds": 5.15, "starts_from": "the section's start picture"}],
                  {"S2": 3.0, "S3": 2.0}, shots=[shot("K02", 0.0), shot("K03", 3.0, "handheld selfie", "Creator holds the phone")]),
          section("G03", ["S4"], "plate", [{"what": "card background", "from": "S4"}], [], {}, seconds=2.0),
          section("G04", ["S2"], "motion transfer", [], [{"scenes": ["S2"], "seconds": 3.0}], {"S2": 3.0},
                  shots=[shot("K04", 0.0)], reuses="G02"),
          section("G05", ["S5"], "from the brief",
                  [{"what": "start frame", "from": "S5"}, {"what": "end frame", "from": "S5", "edit_of": "S5"}],
                  [{"scenes": ["S5"], "seconds": 4.5}], {"S5": 4.5}),
          section("G06", ["S6", "S7"], "lip-sync (from the brief)", [{"what": "start frame", "from": "S6"}],
                  [{"scenes": ["S6"], "seconds": 14.0, "starts_from": "the section's start picture"},
                   {"scenes": ["S7"], "seconds": 1.5, "starts_from": "the real last frame of the clip before"}],
                  {"S6": 14.0, "S7": 1.5}),
      ]}

PICTURES = ["S1-F1", "S2-F1", "S3-HANDHELD-K03", "S4-PLATE", "S5-F1", "S5-FLAST", "S6-F1"]


def ruled_ok(reg, station, used):
    want = ((reg.get("doors") or {}).get(station) or {}).get("model")
    if want and used and used != want:
        raise SystemExit(f"MODEL NOT RULED: {station} was made on {used!r}; the ruled model is {want!r}")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-clips-"))
        self.run = self.tmp / "run"
        (self.run / "media").mkdir(parents=True)
        (self.run / "vo").mkdir()
        for p in PICTURES:
            (self.run / "media" / f"{p}.png").write_bytes(b"png")
        for s in SCENES:
            if s.get("voice"):
                (self.run / "vo" / f"{s['id']}.mp3").write_bytes(b"mp3")
        (self.run / "storyboard.json").write_text(json.dumps(SB))
        self.reg = cp.platform.registry()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def plan(self, sb=None, **kw):
        return cp.plan_clips(self.run, json.loads(json.dumps(sb or SB)), SCENES, self.reg, piece=PIECE,
                             ruled=ruled_ok, **kw)


def nobody_in(gid):
    """SB with nobody of ours on screen in one section — the only kind that may chain clips."""
    sb = json.loads(json.dumps(SB))
    for g in sb["sections"]:
        if g["id"] == gid:
            g["elements"] = []
    return sb


class PlansOnlyTheStoryboardsClips(Base):
    def test_clips_per_section(self):
        res = self.plan()
        self.assertEqual(res["problems"], [])
        self.assertEqual([j["id"] for j in res["jobs"]],
                         ["G01-C1", "G02-C1", "G02-K03", "G05-C1", "G06-C1", "G06-C2"])
        rows = {r["id"]: r for r in res["sections"]}
        self.assertEqual(rows["G03"]["clips"], [])                      # a plate: no clip
        self.assertIn("picture is shown", rows["G03"]["note"])
        self.assertEqual(rows["G04"]["clips"], [])                      # reuses: not made twice
        self.assertIn("Section 2", rows["G04"]["note"])

    def test_every_clip_starts_from_an_approved_picture_or_the_clip_before(self):
        res = self.plan()
        self.assertEqual(res["problems"], [])
        jobs = {j["id"]: j for j in res["jobs"]}
        self.assertEqual(jobs["G01-C1"]["start_frame"], "S1-F1")
        self.assertEqual(jobs["G02-K03"]["start_frame"], "S3-HANDHELD-K03")
        # no hand-offs for people (3 Oct): a person on screen starts every clip from the approved picture
        self.assertEqual(jobs["G06-C2"]["start_frame"], "S6-F1")
        self.assertIsNone(jobs["G06-C2"]["after"])
        for j in jobs.values():
            self.assertEqual(j["medias"][0], {"role": "start_image", "value": j["start_frame"]})
        # nobody on screen: the later clip may start from the real last frame of the one before
        jobs = {j["id"]: j for j in self.plan(sb=nobody_in("G06"))["jobs"]}
        self.assertEqual(jobs["G06-C2"]["start_frame"], "G06-C1-LAST")
        self.assertEqual(jobs["G06-C2"]["after"], "G06-C1")

    def test_the_guard_stops_a_person_clip_from_a_made_frame(self):
        jobs = [{"id": "G06-C2", "section_id": "G06", "start_frame": "G06-C1-LAST", "characters": ["HOST"]},
                {"id": "G07-C2", "section_id": "G07", "start_frame": "G07-C1-LAST", "characters": []}]
        got = cp.no_handoff_breaks(jobs, {g["id"]: g for g in SB["sections"]})
        self.assertEqual([x.split(":")[0] for x in got], ["G06-C2"])

    def test_end_picture_only_where_the_storyboard_has_one(self):
        jobs = {j["id"]: j for j in self.plan()["jobs"]}
        self.assertEqual(jobs["G05-C1"]["end_frame"], "S5-FLAST")
        self.assertIn({"role": "end_image", "value": "S5-FLAST"}, jobs["G05-C1"]["medias"])
        for cid in ("G01-C1", "G06-C1", "G06-C2"):
            self.assertIsNone(jobs[cid]["end_frame"])
            self.assertNotIn("end_image", [m["role"] for m in jobs[cid]["medias"]])

    def test_lip_sync_carries_its_own_recorded_line(self):
        jobs = {j["id"]: j for j in self.plan()["jobs"]}
        self.assertEqual(jobs["G01-C1"]["kind"], "talking")
        self.assertIn({"role": "audio_references", "value": "vo/S1.mp3"}, jobs["G01-C1"]["medias"])
        self.assertEqual(jobs["G01-C1"]["lines"], ["S1"])
        self.assertIn("@Audio1", jobs["G01-C1"]["params"]["prompt"])

    def test_motion_transfer_carries_the_swipe_footage_and_only_on_camera_words(self):
        j = {j["id"]: j for j in self.plan()["jobs"]}["G02-C1"]
        self.assertEqual(j["motion_ref"]["shots"], ["K02"])             # the cutaway's shot is not in the main take
        self.assertIn("video_references", [m["role"] for m in j["medias"]])
        rule = cp._rule("swipe_motion")
        self.assertIn(rule["says"], j["params"]["prompt"])
        self.assertIn(rule["camera_sentence"], j["params"]["prompt"])
        # S2 is a hands-only line: silence on the clip's track; S3 is said on camera
        parts = {p["scene"]: p["file"] for p in j["audio_parts"]}
        self.assertEqual(parts, {"S2": None, "S3": "vo/S3.mp3"})
        self.assertEqual(j["audio"], "clips/audio/G02-C1.mp3")

    def test_cutaway_is_its_own_clip_over_the_shots_it_drives(self):
        j = {j["id"]: j for j in self.plan()["jobs"]}["G02-K03"]
        self.assertEqual(j["clip_is"], "cutaway")
        self.assertEqual(j["motion_ref"]["shots"], ["K03"])
        self.assertEqual(j["window"], [3.0, 5.15])
        self.assertEqual(j["lines"], [])                               # the main clip claims the line once
        self.assertIn("HOST's voice", j["params"]["prompt"])            # the swipe's name swapped for ours
        self.assertIn("Keep it exactly as it is", j["params"]["prompt"])  # the picture carries the framing, never the words

    def test_silent_clip_says_nobody_speaks(self):
        j = {j["id"]: j for j in self.plan()["jobs"]}["G05-C1"]
        self.assertEqual(j["kind"], "motion")
        self.assertIsNone(j["audio"])
        self.assertIn("Nobody speaks.", j["params"]["prompt"])
        self.assertIn("@Image2", j["params"]["prompt"])

    def test_every_prompt_is_written_and_carries_the_no_cut_line(self):
        for j in self.plan()["jobs"]:
            self.assertEqual(j["prompt_missing"], [], j["id"])
            self.assertIn("continuous take, no cuts", j["params"]["prompt"].lower())

    def test_only_picks_sections(self):
        res = self.plan(only=["G05", "Section 6"])
        self.assertEqual([j["id"] for j in res["jobs"]], ["G05-C1", "G06-C1", "G06-C2"])


class Stops(Base):
    def test_missing_picture_stops_naming_it(self):
        (self.run / "media" / "S5-FLAST.png").unlink()
        res = self.plan()
        self.assertEqual(len(res["problems"]), 1)
        self.assertIn("S5-FLAST", res["problems"][0])
        self.assertIn("Section 5", res["problems"][0])

    def test_missing_recording_of_an_on_camera_line_stops(self):
        (self.run / "vo" / "S6.mp3").unlink()
        self.assertTrue(any("vo/S6.mp3" in p for p in self.plan()["problems"]))


class TheRuledDoorOnly(Base):
    def test_every_clip_is_on_the_ruled_clip_model(self):
        for j in self.plan()["jobs"]:
            want = self.reg["doors"][j["kind"]]["model"]
            self.assertEqual(j["model"], want)

    def test_a_pick_that_is_not_the_ruled_model_stops(self):
        with self.assertRaises(SystemExit) as e:
            self.plan(pick="some_other_model")
        self.assertIn("MODEL NOT RULED", str(e.exception))


class CostAndBatches(Base):
    def test_cost_is_billed_seconds_times_the_door_rate(self):
        res = self.plan()
        prov = next(p for p in self.reg["providers"].values()
                    if p.get("family") == self.reg["doors"]["motion"]["primary"])
        overall = cp.platform.plan(res["jobs"], prov, self.reg, forced=True)
        self.assertEqual(overall["refusals"], [])
        for r, j in zip(overall["rows"], res["jobs"]):
            m = self.reg["models"][j["model"]]
            rate = cp.platform.pick_rate(m, None, j["params"].get("resolution"))["credits_per_second"]
            self.assertAlmostEqual(r["credits"], rate * j["params"]["duration"], places=2)
            self.assertGreaterEqual(j["params"]["duration"], j["seconds"])
        out = io.StringIO()
        with redirect_stdout(out):
            cp.platform.print_plan(overall)
        self.assertIn(f"TOTAL · {len(res['jobs'])} item(s) · {overall['total_credits']} cr", out.getvalue())

    def test_batches_respect_the_cap_and_chained_clips_go_later(self):
        jobs = self.plan(sb=nobody_in("G06"))["jobs"]
        bs = cp.batches(jobs, 2)
        self.assertTrue(all(len(b) <= 2 for b in bs))
        flat = [j["id"] for b in bs for j in b]
        self.assertGreater(flat.index("G06-C2"), flat.index("G06-C1"))
        self.assertEqual(bs[-1][0]["id"], "G06-C2")                    # its own wave, after every first clip


class Findings(unittest.TestCase):
    def test_storyboard_decided_findings_are_notes_the_rest_refuse(self):
        fails = ["[rule 12] G01-C1: the clip attaches no 'end_image' — …",
                 "[rule 12] G02-C1: the clip carries a 'video_references' media — this door takes only …",
                 "[rule 11] G03-C1: prompt carries no continuous-take line → add it"]
        refusals, notes = cp.sort_findings(fails)
        self.assertEqual(refusals, [fails[2]])
        self.assertEqual(sorted(i for ids in notes.values() for i in ids), ["G01-C1", "G02-C1"])


class TheStep(Base):
    def args(self, **kw):
        return SimpleNamespace(**{"dry_run": True, "only": None, "storyboard": False, "provider": None,
                                  "yes": True, "clip_model": None, **kw})

    def test_dry_run_writes_the_prompts_page_and_nothing_else(self):
        orig = cp.preflight_check
        cp.preflight_check = lambda *a, **k: ([], [], [])
        try:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = cp.start(self.args(), self.run, {"scenes": SCENES, "piece": PIECE}, self.reg, ruled=ruled_ok)
        finally:
            cp.preflight_check = orig
        self.assertEqual(rc, 0, err.getvalue())
        page = (self.run / "clips" / "PROMPTS.md").read_text()
        res = self.plan()
        for j in res["jobs"]:
            self.assertIn(j["params"]["prompt"], page)                 # verbatim
        self.assertIn("TOTAL ·", out.getvalue())
        self.assertFalse((self.run / "batches").exists())
        self.assertFalse((self.run / "clips" / "plan.json").exists())

    def test_with_storyboard_flag_is_refused(self):
        err = io.StringIO()
        with redirect_stderr(err):
            rc = cp.start(self.args(storyboard=True), self.run, {"scenes": SCENES, "piece": PIECE}, self.reg)
        self.assertEqual(rc, 2)

    def test_real_run_writes_batches_plan_and_sheet_with_inputs_built(self):
        orig_pf, orig_build = cp.preflight_check, cp.build_inputs
        built = []
        cp.preflight_check = lambda *a, **k: ([], [], [])
        cp.build_inputs = lambda run, jobs: built.extend(j["id"] for j in jobs) or []
        try:
            with redirect_stdout(io.StringIO()):
                rc = cp.start(self.args(dry_run=False), self.run, {"scenes": SCENES, "piece": PIECE},
                              self.reg, ruled=ruled_ok)
        finally:
            cp.preflight_check, cp.build_inputs = orig_pf, orig_build
        self.assertEqual(rc, 0)
        self.assertTrue(built)
        self.assertTrue(sorted((self.run / "batches").glob("clips-*.json")))
        self.assertTrue((self.run / "clips" / "plan.json").is_file())
        self.assertIn("G06-C2", (self.run / "clips" / "SUBMIT.md").read_text())


class AfterTheClipsLand(Base):
    def test_last_frame_pulled_and_the_review_runs_on_the_clips(self):
        res = self.plan(sb=nobody_in("G06"))
        (self.run / "clips").mkdir()
        (self.run / "clips" / "plan.json").write_text(json.dumps(res))
        (self.run / "media" / "G06-C1.mp4").write_bytes(b"mp4")
        calls, pulled = [], []

        class FakeReview:
            @staticmethod
            def after_stage(tool, stage, run, items=None):
                calls.append((tool, stage, [i["id"] for i in items]))
                return {i["id"]: {"ok": True, "severity": "OK"} for i in items}

        def fake_last(clip, dest):
            pulled.append((clip.name, dest.name))
            return dest

        def fake_frames(clip, out_dir):
            return [out_dir / f"{clip.stem}-first.jpg"]

        with redirect_stdout(io.StringIO()):
            cp.after_record(self.run, {"G06-C1": {"file": "media/G06-C1.mp4", "status": "done"}},
                            review=FakeReview, frames=fake_frames, lastf=fake_last)
        self.assertEqual(pulled, [("G06-C1.mp4", "G06-C1-LAST.png")])
        self.assertEqual(calls, [("video-production", "clips", ["G06-C1"])])

    def test_no_plan_no_work(self):
        calls = []

        class FakeReview:
            @staticmethod
            def after_stage(*a, **k):
                calls.append(a)
                return {}
        cp.after_record(self.run, {"X": {"file": "x.mp4"}}, review=FakeReview)
        self.assertEqual(calls, [])


class HbSwitch(Base):
    """The HB clip modes (2026-11-07): off unless the storyboard or a section names one."""
    def test_off_by_default_and_plan_unchanged(self):
        self.assertEqual(cp.clip_mode_of(SB), "narrator")
        self.assertEqual(cp.clip_mode_of(SB, SB["sections"][0]), "narrator")
        base = self.plan()
        named = self.plan(json.loads(json.dumps({**SB, "clip_mode": "narrator"})))
        self.assertEqual(json.dumps(base, sort_keys=True), json.dumps(named, sort_keys=True))
        self.assertTrue(all("clip_mode" not in j for j in base["jobs"]))
        self.assertTrue(all("clip_mode" not in r for r in base["sections"]))

    def test_a_section_mode_wins_over_the_storyboards_and_marks_only_its_own_jobs(self):
        sb = json.loads(json.dumps(SB))
        sb["clip_mode"] = "hb-multishot"
        sb["sections"][0]["clip_mode"] = "hb-voice"
        res = self.plan(sb)
        modes = {j["id"]: j.get("clip_mode") for j in res["jobs"]}
        self.assertEqual(modes["G01-C1"], "hb-voice")
        self.assertEqual(modes["G05-C1"], "hb-multishot")
        rows = {r["id"]: r for r in res["sections"]}
        self.assertEqual(rows["G01"]["clip_mode"], "hb-voice")
        self.assertEqual(rows["G05"]["clip_mode"], "hb-multishot")
        self.assertNotIn("clip_mode", rows["G03"])                      # a plate has no clip to mark

    def test_both_modes_read_as_one_string(self):
        self.assertEqual(cp.clip_mode_of({"clip_mode": ["hb-voice", "hb-multishot"]}), "hb-multishot+hb-voice")


class HbGroups(unittest.TestCase):
    def shots(self, secs, settings=None):
        return [{"id": f"s{i}", "seconds": s, "setting": (settings or ["X"] * len(secs))[i]} for i, s in enumerate(secs)]

    def test_four_shots_to_a_call_two_to_four_eight_to_fifteen_seconds(self):
        g = cp.multishot_groups(self.shots([3, 3, 3, 3, 3, 3]))
        self.assertEqual([x["shots"] for x in g], [["s0", "s1", "s2", "s3"], ["s4", "s5"]])
        self.assertEqual([x["seconds"] for x in g], [12, 8])
        self.assertEqual([x["pad"] for x in g], [0.0, 2.0])             # two shots of 3 s run to the 8 s floor

    def test_a_call_never_runs_past_fifteen_seconds(self):
        g = cp.multishot_groups(self.shots([6, 6, 6]))
        self.assertEqual([x["shots"] for x in g], [["s0", "s1"], ["s2"]])
        self.assertTrue(all(x["seconds"] <= 15 for x in g))

    def test_one_place_per_call_and_a_lone_shot_stays_a_narrator_clip(self):
        g = cp.multishot_groups(self.shots([3, 3, 3], ["A", "A", "B"]))
        self.assertEqual([(x["shots"], x["single"]) for x in g], [(["s0", "s1"], False), (["s2"], True)])

    def test_a_short_shot_is_held_to_two_seconds(self):
        g = cp.multishot_groups(self.shots([0.5, 0.5, 0.5, 0.5]))
        self.assertEqual(g[0]["seconds"], 8)

    def test_a_filmed_shot_is_never_joined_and_breaks_the_run(self):
        sh = self.shots([3, 3, 3, 3, 3])
        sh[2]["filmed"] = 'speaker says "as filmed"'
        g = cp.multishot_groups(sh)
        self.assertEqual([(x["shots"], x["single"], bool(x["filmed"])) for x in g],
                         [(["s0", "s1"], False, False), (["s2"], True, True), (["s3", "s4"], False, False)])

    def test_a_scene_of_filmed_shots_makes_no_call(self):
        sh = self.shots([3, 3, 3])
        for s in sh:
            s["filmed"] = "operation CUT: cut from an owned take"
        self.assertTrue(all(x["single"] and x["filmed"] for x in cp.multishot_groups(sh)))


class HbItem(unittest.TestCase):
    """The payload is built, never sent."""
    def item(self, mode, **over):
        sp = cp._sp()
        call = {**sp_hb_call(), "clip_mode": mode, **over}
        return cp.hb_item("A-C1", call, HB_SCENES_, HB_PEOPLE_, {}, "", "ANA", {"aspect": "9:16"})

    def test_hb_voice_sends_the_picture_and_one_audio_reference_per_person(self):
        it = self.item("hb-voice")
        self.assertEqual(it["kind"], "talking")
        self.assertEqual([m["role"] for m in it["medias"]], ["image_references", "audio_references", "audio_references"])
        self.assertEqual(it["params"]["aspect_ratio"], "9:16")
        self.assertEqual(it["prompt_missing"], [])

    def test_hb_multishot_alone_is_a_silent_motion_clip_of_8_to_15_seconds(self):
        it = self.item("hb-multishot")
        self.assertEqual(it["kind"], "motion")
        self.assertTrue(8 <= it["params"]["duration"] <= 15)
        self.assertEqual([m["role"] for m in it["medias"]], ["start_image"])

    def test_a_refusal_carries_no_prompt_and_names_what_is_missing(self):
        it = self.item("hb-voice", voice_samples={})
        self.assertEqual(it["params"]["prompt"], "")
        self.assertTrue(it["prompt_missing"])

    def test_a_refused_call_carries_the_narrator_clip_built_exactly_as_with_the_switch_off(self):
        it = self.item("hb-voice", voice_samples={})
        plain = {k: v for k, v in sp_hb_call().items() if k != "voice_samples"}
        off = cp._sp().build(plain, HB_SCENES_, HB_PEOPLE_, {}, "", "ANA")
        self.assertEqual(it["narrator"]["clip_mode"], "narrator")
        self.assertEqual(it["narrator"]["prompt"], off["prompt"])
        self.assertTrue(it["narrator"]["prompt"])
        self.assertNotIn("narrator", self.item("hb-voice"))                 # a call that builds carries no fallback

    def test_a_filmed_scene_builds_no_payload_and_says_why(self):
        sc = {"A": {**HB_SCENES_["A"], "speaker": "ANA · BO (as filmed)"}}
        sp = cp._sp()
        it = cp.hb_item("A-C1", {**sp_hb_call(), "clip_mode": "hb-multishot+hb-voice"}, sc, HB_PEOPLE_, {}, "", "ANA")
        self.assertEqual(it["params"]["prompt"], "")
        self.assertEqual([f["shot"] for f in it["filmed"]], ["A.1", "A.2"])
        self.assertNotIn("narrator", it)                                    # a filmed take is cut in the edit, never remade


def sp_hb_call():
    return {"id": "A-C1", "scenes": ["A"], "talking": True, "start_frame": "A-F1", "people": ["ANA", "BO"],
            "lines": [{"scene": "A", "speaker": "ANA", "text": "Would you try this one?", "on_camera": True},
                      {"scene": "A", "speaker": "BO", "text": "Yes.", "on_camera": True}],
            "voice_samples": {"ANA": {"file": "v/ana.mp3", "seconds": 6}, "BO": {"file": "v/bo.mp3", "seconds": 5}}}


HB_PEOPLE_ = {"ANA": {"noun": "host", "pron": "she", "poss": "her"}, "BO": {"noun": "guest", "pron": "he", "poss": "his"}}
HB_SCENES_ = {"A": {"id": "A", "setting_id": "KITCHEN", "who": "ANA, BO", "voice": "one two three four five six",
                    "first_frame": {"subject": "ANA holds a bowl out to BO", "location": "a bright kitchen"},
                    "beats": [{"shot": "A.1", "do": "lifts the bowl"}, {"shot": "A.2", "do": "nods"}],
                    "shots": [{"id": "A.1", "angle": "front, two-shot", "face": "eyes on the bowl", "lines": [{"say": "Would you try this one?"}]},
                              {"id": "A.2", "angle": "front, close", "face": "a small smile", "lines": [{"say": "Yes."}]}]}}


if __name__ == "__main__":
    unittest.main()
