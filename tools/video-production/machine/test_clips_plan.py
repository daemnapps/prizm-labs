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


if __name__ == "__main__":
    unittest.main()
