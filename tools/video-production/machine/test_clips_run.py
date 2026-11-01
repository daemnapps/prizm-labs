"""The Omni clips route (clips_run.py) — fakes only, no network, no money."""
import io
import math
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import clips_run as oc

CFG = oc.route_cfg()
# the splitting tests run with a 10 s cap on purpose, so the fixtures exercise splitting; the live route takes the
# model's own 4-30 s (providers.json, 2026-10-28)
CFG = {**CFG, "seconds_range": [4, 10]}

PEOPLE = {
    "LEAD": {"noun": "woman", "pron": "she", "poss": "her", "voice_id": "v-lead", "model_id": "eleven_multilingual_v2",
             "settings": {"stability": 0.5}, "speaks": ["S1", "S3", "S5"]},
    "DOC": {"noun": "doctor", "pron": "he", "poss": "his", "voice_id": "v-doc", "model_id": "eleven_multilingual_v2",
            "settings": {}, "speaks": ["S2", "S4", "S6"]},
}

LONG = ("Twice a week, a big tablespoon, sixty seconds. Three tubes, sixty days. Use all three. "
        "And they put it in writing, guaranteed. If you are not delighted with the results in the next "
        "sixty days, we will gladly issue a full refund.")


def scene(sid, who, voice, to_camera, happens="does a thing", composition="Close-up, centred at 25-75% width",
          speaker=None):
    # the brief's `speaker` decides who says a line (3 Oct) — here, the person whose lines these are
    speaker = speaker or next((pid for pid, p in PEOPLE.items() if sid in p["speaks"]), None)
    return {"id": sid, "who": who, "speaker": speaker, "voice": voice, "to_camera": to_camera, "happens": happens,
            "delivery": "none · x · clinical · list-stack",
            "frames": [{"role": "first", "subject": "x", "composition": composition, "action": "",
                        "camera": "Held at her arm's length, close"}, {"role": "last"}]}


SCENES = [
    scene("S1", "LEAD", "I am at the clinic today to ask about the spots on my face.", True,
          happens="tells the lens about her spots, close-up"),
    scene("S2", "DOC's hands", "A nice even base. Great skin. The front, high up here.", False,
          happens="DOC's hands rest on LEAD's temples"),
    scene("S3", "LEAD", "Mm-hmm.", True, happens="murmurs"),
    scene("S4", "DOC's hand", "Then we clear the top off here, and it works underneath like this.", False,
          happens="DOC's hand shows the two steps"),
    scene("S5", "LEAD", LONG, True, happens="counts the routine on her fingers"),
    scene("S6", "DOC", "Your skin feels different the first time.", True, happens="tells her it takes months"),
]


def shot(k, at, start, end, kind="set-up shot", held="set down still"):
    return {"id": k, "type": kind, "at": at, "start": start, "end": end, "clip": f"{k}.mp4",
            "camera": {"held": held, "move": "none"}}


SB = {
    "teardown": "../x",
    "people_map": {"lead": ["LEAD", "Creator"]},
    "layers": {"voice": [{"scene": "S1", "at": 0.0}, {"scene": "S2", "at": 4.0}, {"scene": "S3", "at": 9.0},
                         {"scene": "S4", "at": 9.5}, {"scene": "S5", "at": 16.0}, {"scene": "S6", "at": 36.0}]},
    "sections": [
        {"id": "G01", "maker": "lip-sync", "seconds": 4.0, "starts": 0.0, "scenes": ["S1"], "voice": {"S1": 4.0},
         "elements": ["person · LEAD · look-1"], "swipe": {"shots": [shot("K01", 0, 0, 4, "handheld selfie", "handheld at arm's length")]},
         "frames": [{"what": "start frame", "from": "S1"}],
         "clips": [{"scenes": ["S1"], "seconds": 4.0}]},
        {"id": "G02", "maker": "motion transfer", "seconds": 12.0, "starts": 4.0, "scenes": ["S2", "S3", "S4"],
         "voice": {"S2": 4.85, "S3": 0.5, "S4": 6.35},
         "elements": ["person · DOC · coat", "person · LEAD · look-1"],
         "swipe": {"shots": [shot("K02", 0.0, 10.0, 18.0), shot("K03", 8.0, 18.0, 22.0)]},
         "frames": [{"what": "start frame · set-up shot", "from": "S2", "own": False, "drives": ["K02", "K03"]}],
         "clips": [{"scenes": ["S2", "S3", "S4"], "seconds": 12.0}]},
        {"id": "G03", "maker": "plate", "seconds": 2.0, "starts": 16.0, "scenes": [], "voice": {},
         "frames": [{"what": "card background", "from": "S7"}], "clips": []},
        {"id": "G04", "maker": "lip-sync (from the brief)", "seconds": 19.0, "starts": 16.0, "scenes": ["S5"],
         "voice": {"S5": 19.0}, "elements": ["person · LEAD · look-1"], "swipe": {"shots": []},
         "frames": [{"what": "start frame", "from": "S5"}], "clips": [{"scenes": ["S5"], "seconds": 19.0}]},
        {"id": "G05", "maker": "motion transfer", "seconds": 1.0, "starts": 35.0, "reuses": "G02", "scenes": [],
         "voice": {}, "frames": [], "clips": [{"scenes": []}]},
        {"id": "G06", "maker": "lip-sync (from the brief)", "seconds": 6.8, "starts": 36.0, "scenes": ["S6"],
         "voice": {"S6": 6.8}, "elements": ["person · DOC · coat", "person · LEAD · look-1"], "swipe": {"shots": []},
         "frames": [{"what": "start frame", "from": "S6"}], "clips": [{"scenes": ["S6"], "seconds": 6.8}]},
    ],
}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name) / "run"
        (self.run / "media").mkdir(parents=True)
        for pid in ("S1-F1", "S2-F1", "S5-F1", "S6-F1", "S7-PLATE"):
            (self.run / "media" / f"{pid}.png").write_bytes(b"png")

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, overrides=None, only=None):
        if overrides is not None:
            (self.run / "clips").mkdir(exist_ok=True)
            (self.run / "clips" / "on-camera.json").write_text(json.dumps(overrides))
        return oc.plan(self.run, SB, SCENES, cfg=CFG, people=PEOPLE, only=only,
                       style="Phone-grade vertical video, natural colour.")

    def call(self, res, cid):
        return next(c for c in res["calls"] if c["id"] == cid)


class Splitting(Fixture):
    def test_lines_split_at_line_boundaries_under_ten_seconds(self):
        lines = [{"scene": "A", "speaker": "LEAD", "text": "One two three four.", "a": 0.0, "z": 4.0, "on_camera": True},
                 {"scene": "B", "speaker": "DOC", "text": "Five six seven eight.", "a": 4.15, "z": 8.0, "on_camera": False},
                 {"scene": "C", "speaker": "LEAD", "text": "Nine ten eleven twelve.", "a": 8.15, "z": 12.0, "on_camera": True}]
        calls = oc.split_calls(lines, 0.0, 12.0, 10.0, 3.0)
        self.assertEqual(len(calls), 2)
        for a, z, ls in calls:
            self.assertLessEqual(z - a, 10.0)
            self.assertTrue(all("part" not in l for l in ls), "a whole line is never cut when a line start will do")
        cut = calls[0][1]
        self.assertIn(cut, (4.15, 8.15))

    def test_a_long_line_is_cut_at_its_sentences_never_mid_word(self):
        line = {"scene": "S5", "speaker": "LEAD", "text": LONG, "a": 0.0, "z": 19.0, "on_camera": True}
        calls = oc.split_calls([line], 0.0, 19.0, 10.0, 3.0)
        self.assertGreaterEqual(len(calls), 2)
        texts = [ls[0]["text"] for _, _, ls in calls]
        self.assertEqual(" ".join(texts).split(), LONG.split(), "the pieces are the line, in order, whole words")
        for t in texts[:-1]:
            self.assertRegex(t, r"[.!?]$", "each piece ends at a sentence")
        self.assertEqual([ls[0]["part"] for _, _, ls in calls], [f"{i}/{len(calls)}" for i in range(1, len(calls) + 1)])
        self.assertTrue(all(z - a <= 10.0 for a, z, _ in calls))

    def test_a_short_leftover_call_is_avoided_by_a_sentence_cut(self):
        lines = [{"scene": "A", "speaker": "DOC", "text": "A nice even base. Great skin. The front. Good texture. Good jaw.",
                  "a": 0.0, "z": 9.4, "on_camera": True},
                 {"scene": "B", "speaker": "LEAD", "text": "Worst part.", "a": 9.55, "z": 11.0, "on_camera": True}]
        calls = oc.split_calls(lines, 0.0, 11.0, 10.0, 3.0)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(z - a >= 3.0 for a, z, _ in calls), "no call shorter than the model's least")

    def test_plan_calls_never_exceed_ten_and_every_part_starts_from_the_picture(self):
        res = self.plan()
        self.assertFalse(res["problems"], res["problems"])
        for c in res["calls"]:
            self.assertLessEqual(c["seconds"], 10.0)
            self.assertTrue(3 <= c["duration"] <= 10)
        g4 = [c for c in res["calls"] if c["section_id"] == "G04"]
        self.assertGreater(len(g4), 1)
        # a person on screen: every part starts from the approved picture, never the part before's
        # last frame (3 Oct root cause: each hand-off drifted the face)
        for c in g4:
            self.assertEqual(c["start_frame"], "S5-F1")
            self.assertIsNone(c["after"])

    def test_cards_and_reused_sections_get_no_clip(self):
        res = self.plan()
        rows = {r["id"]: r for r in res["sections"]}
        self.assertEqual(rows["G03"]["calls"], [])
        self.assertEqual(rows["G05"]["calls"], [])
        self.assertIn("not made twice", rows["G05"]["note"])


class Durations(Fixture):
    def test_no_padding(self):
        self.assertEqual(oc.billed(7.6, [3, 10]), 8)
        self.assertEqual(oc.billed(6.8, [3, 10]), 7)
        self.assertEqual(oc.billed(1.44, [3, 10]), 3)
        self.assertEqual(oc.billed(9.58, [3, 10]), 10)
        self.assertEqual(oc.billed(4.0, [3, 10]), 4)
        res = self.plan()
        self.assertNotIn("silent_share", CFG, "the 75% silent-clip cut is retired (V17, verify 2026-10-21 row 8)")
        span = CFG["seconds_range"]
        for c in res["calls"]:
            # every clip is made at its FULL window — never a share slowed at the edit (V17); a silent one is never padded
            made = c["seconds"]
            if c["talking"]:
                # a talking take gets room to finish its words (2026-10-28: two takes cut off on the last words at 9.9 s of 10)
                self.assertEqual(c["duration"], oc.billed(made * oc.TALK_ROOM + 0.6, span), c["id"])
                self.assertGreaterEqual(c["duration"], min(span[1], math.ceil(round(made, 2) - 1e-6)), c["id"])
                continue
            self.assertEqual(c["duration"], max(3, math.ceil(round(made, 2) - 1e-6)), c["id"])
            self.assertLess(c["duration"] - made, 1.0 if made >= 3 else 3.0)
            self.assertGreaterEqual(c["duration"], min(10, c["seconds"]) - 1e-6, "never shorter than its window")


class OnOffCamera(Fixture):
    def test_default_follows_to_camera(self):
        res = self.plan()
        c = self.call(res, "G02-C1-1") if any(x["id"] == "G02-C1-1" for x in res["calls"]) else self.call(res, "G02-C1")
        all_lines = [l for x in res["calls"] if x["section_id"] == "G02" for l in x["lines"]]
        # S3 is "Mm-hmm." — a sound, not words (the owner, 3 Oct): nobody says it on camera
        self.assertEqual({l["scene"] for l in all_lines if l["on_camera"]}, set())
        tts = {t["scene"]: t for t in res["tts"]}
        self.assertIn("S2", tts)
        self.assertIn("S4", tts)
        self.assertEqual(tts["S2"]["voice_id"], "v-doc")
        self.assertEqual(tts["S2"]["at"], 4.0)
        self.assertTrue(tts["S3"]["sound"], "the mm-hmm is made on its own track for the edit")
        self.assertNotIn("A nice even base", c["prompt"], "an off-camera line is never in the clip")

    def test_override_puts_the_doctor_on_camera(self):
        res = self.plan({"G02": {"on_camera": ["DOC"], "why": "his face is in the picture"}})
        g2 = [c for c in res["calls"] if c["section_id"] == "G02"]
        said = {l["scene"] for c in g2 for l in c["lines"] if l["on_camera"]}
        self.assertEqual(said, {"S2", "S4"})
        self.assertFalse({"S2", "S4"} & {t["scene"] for t in res["tts"]})
        prompt = " ".join(c["prompt"] for c in g2)
        self.assertIn("Audio 1 is the doctor's voice", prompt)       # the doctor's read rides in the call; his words are never typed
        self.assertNotIn("A nice even base.", prompt)
        parts = [p for c in g2 for p in c["voice_parts"]]
        self.assertEqual({p["voice_id"] for p in parts}, {"v-doc"}, "the lead only says mm-hmm here: a sound, no swap")

    def test_a_sound_is_a_nod_never_lip_sync(self):
        res = self.plan()
        g2 = [c for c in res["calls"] if c["section_id"] == "G02"]
        line = next(l for c in g2 for l in c["lines"] if l["scene"] == "S3")
        self.assertFalse(line["on_camera"])
        self.assertTrue(line["nod"])
        prompt = " ".join(c["prompt"] for c in g2)
        self.assertIn("nods slightly, lips closed, without a sound", prompt)
        self.assertNotIn("Mm-hmm", prompt)
        self.assertNotIn("murmurs", prompt)
        self.assertEqual(oc.split_sound("You have good texture. Um..."), ("You have good texture.", "Um..."))
        self.assertEqual(oc.split_sound("Mm-hmm. Mm-hmm."), ("", "Mm-hmm. Mm-hmm."))
        self.assertEqual(oc.split_sound("Huge. I've tried everything."), ("Huge. I've tried everything.", ""))

    def test_the_briefs_speaker_wins_over_whose_hands_are_in_the_shot(self):
        people = {"LEAD": {"speaks": []}, "DOC": {"speaks": []}}
        sc = {"id": "S5", "who": "LEAD's hands", "speaker": "DOC", "voice": "A little glycolic peel."}
        self.assertEqual(oc.speaker_of(sc, people), "DOC")
        # no `speaker`: never guessed from whose hands are in the shot, nor from the voice map
        self.assertIsNone(oc.speaker_of({"id": "S6", "who": "LEAD's hands", "speaker": ""}, people))
        self.assertIsNone(oc.speaker_of({"id": "S1", "who": "LEAD", "speaker": "NOBODY"}, PEOPLE))

    def test_the_sound_map_shows_every_line_once_by_kind(self):
        import tempfile, shutil
        res = self.plan()
        d = Path(tempfile.mkdtemp()); (d / "clips").mkdir()
        (d / "clips" / "plan.json").write_text(json.dumps(res))
        (d / "storyboard.json").write_text(json.dumps(SB))
        sm = oc._load("sound_map")
        sec, md, counts = sm.build(d)
        self.assertIn("| sound |", md)
        self.assertEqual(counts["snd"], sum(1 for t in res["tts"] if t.get("sound")))
        self.assertIn("Voice in the clip", sec)
        shutil.rmtree(d)

    def test_a_person_on_screen_never_starts_from_a_made_frame(self):
        res = self.plan()
        for c in res["calls"]:
            if c["people"]:
                self.assertFalse(str(c["start_frame"]).endswith("-LAST"), c["id"])
                self.assertIsNone(c["after"], c["id"])

    def test_the_guard_refuses_a_person_clip_from_a_made_frame(self):
        """No hand-offs for people (3 Oct root cause): whatever planned it, a call with a person on
        screen that starts from a clip's last frame — or from no approved picture — is a stop."""
        calls = [{"id": "G06-C2", "people": ["LEAD"], "start_frame": "G06-C1-LAST", "after": "G06-C1"},
                 {"id": "G07-C1", "people": ["LEAD"], "start_frame": None, "after": None},
                 {"id": "G08-C2", "people": [], "start_frame": "G08-C1-LAST", "after": "G08-C1"},
                 {"id": "G09-C1", "people": ["DOC"], "start_frame": "S9-F1", "after": None}]
        got = oc.handoff_breaks(calls)
        self.assertEqual([g.split(":")[0] for g in got], ["G06-C2", "G07-C1"])
        # a section with a person but no approved start picture is refused, never handed on
        import copy
        sb = copy.deepcopy(SB)
        for g in sb["sections"]:
            if g["id"] == "G04":
                g["frames"] = []
                g["clips"] = [{"scenes": ["S5"], "seconds": 19.0}]
        res = oc.plan(self.run, sb, SCENES, cfg=CFG, people=PEOPLE)
        self.assertTrue(any("no approved start picture" in p for p in res["problems"]), res["problems"])
        self.assertFalse(any(str(c["start_frame"]).endswith("-LAST") for c in res["calls"] if c["people"]))

    def test_the_live_runner_refuses_a_handed_on_person_clip_before_spending(self):
        c = {"id": "G06-C2", "people": ["LEAD"], "start_frame": "G06-C1-LAST", "after": "G06-C1"}
        with self.assertRaises(RuntimeError) as e:
            oc.make_call(self.run, c, CFG, oc.Ledger(self.run), PEOPLE)
        self.assertIn("never a clip's last frame", str(e.exception))

    def test_a_line_with_no_speaker_in_the_cast_is_refused(self):
        scs = [dict(s) for s in SCENES]
        scs[0]["speaker"] = ""
        res = oc.plan(self.run, SB, scs, cfg=CFG, people=PEOPLE)
        self.assertTrue(any(p.startswith("S1: the brief names no speaker") for p in res["problems"]), res["problems"])

    def test_no_upscale_step_at_1080p(self):
        res = oc.plan(self.run, SB, SCENES, cfg={**CFG, "resolution": "1080p"}, people=PEOPLE)
        for c in res["calls"]:
            self.assertEqual(c["upscale_usd"], 0.0)
            self.assertFalse(any(s.startswith("upscale") for s in c["steps"]), c["steps"])

    def test_a_chained_clip_checks_its_face_against_the_approved_picture(self):
        res = self.plan()
        for c in res["calls"]:
            self.assertFalse(str(c.get("face_ref") or "").endswith("-LAST"), c["id"])

    def test_override_takes_a_to_camera_speaker_off(self):
        res = self.plan({"G06": {"off_camera": ["DOC"], "why": "only his hand is in the picture"}})
        c = self.call(res, "G06-C1")
        self.assertFalse(c["talking"])
        self.assertIn("S6", {t["scene"] for t in res["tts"]})
        self.assertIn("the woman listens in silence", c["prompt"].lower())
        self.assertIn("Nobody speaks", c["prompt"])                  # 3 Oct: "someone talks" made the model invent lines
        self.assertNotIn("Your skin feels different", c["prompt"])

    def test_most_specific_override_wins(self):
        ov = {"G06": {"off_camera": ["DOC"]}, "G06-C1": {"on_camera": ["DOC"]}}
        res = self.plan(ov)
        self.assertTrue(self.call(res, "G06-C1")["talking"])


class Refs(Fixture):
    def test_at_most_three_pieces_of_three_seconds(self):
        wins = [("K02", 0.0, 8.0), ("K03", 8.0, 12.0)]
        shots = {"K02": {"start": 10.0, "end": 18.0, "clip": "K02.mp4"}, "K03": {"start": 18.0, "end": 22.0, "clip": "K03.mp4"}}
        got = oc.ref_pieces(wins, shots, 0.0, 10.0, None, CFG["refs"])
        self.assertLessEqual(len(got), 3)
        self.assertTrue(all(0 < p["seconds"] <= float(CFG["refs"]["max_seconds"]) for p in got))
        self.assertEqual(got[0]["shot"], "K02")
        self.assertEqual(got[-1]["shot"], "K03", "spread across the window, first to last")

    def test_a_person_on_screen_locks_the_picture_as_the_first_frame(self):
        """3 Oct face lock: reference mode never locks the first frame and drifted Creator-A's face, so a
        section with a person in it is animated from the locked picture, the movement said in words —
        whatever the config's lock_faces says."""
        res = oc.plan(self.run, SB, SCENES, cfg={**CFG, "lock_faces": False}, people=PEOPLE)
        for c in res["calls"]:
            if c.get("people"):
                # no swipe pieces with a person on screen; since 2026-10-28 only a real person's movement (movement bank)
                self.assertTrue(all(r.get("kind") == "movement" for r in c["refs"]), c["id"])
                self.assertEqual(c["endpoint"], "reference-to-video" if c["refs"] else "image-to-video", c["id"])
                self.assertEqual(c["start_frame"] is not None, True, c["id"])

    def test_identity_words_come_from_the_casting_sheet(self):
        import tempfile, json as _j
        with tempfile.TemporaryDirectory() as t:
            Path(t, "spec.json").write_text(_j.dumps({"who": "58-year-old woman, auburn bob, green eyes, soft jaw; a small mole above her lip; freckles across her nose"}))
            w = oc.identity_words(Path(t))
        self.assertIn("green eyes", w); self.assertIn("mole", w); self.assertIn("freckles", w)

    def test_movement_sections_use_reference_to_video_and_blur_every_piece(self):
        # reference mode only for a shot with nobody of ours in it: G02 without its people
        import copy
        sb = copy.deepcopy(SB)
        for g in sb["sections"]:
            if g["id"] == "G02":
                g["elements"] = []
        res = oc.plan(self.run, sb, SCENES, cfg=CFG, people=PEOPLE)
        g2 = [c for c in res["calls"] if c["section_id"] == "G02"]
        self.assertTrue(all(c["endpoint"] == "reference-to-video" for c in g2))
        self.assertTrue(all(c["model"].endswith("reference-to-video") for c in g2))
        talk = self.call(res, "G01-C1")
        self.assertTrue(all(r.get("kind") == "movement" for r in talk["refs"]))   # a real person's movement, never the swipe
        cmds = []
        oc.build_refs(self.run, g2, CFG, Path("/td"), runner=cmds.append)
        self.assertEqual(len(cmds), sum(len(c["refs"]) for c in g2))
        for cmd in cmds:
            vf = cmd[cmd.index("-vf") + 1]
            self.assertIn("scale=720:-2", vf)
            self.assertIn("gblur=sigma=30", vf)
            self.assertLessEqual(float(cmd[cmd.index("-t") + 1]), float(CFG["refs"]["max_seconds"]))
            self.assertIn("-an", cmd)


class Prompts(Fixture):
    def test_every_prompt_binds_its_files_and_keeps_the_two_negatives(self):
        res = self.plan()
        for c in res["calls"]:
            p = c["prompt"]
            self.assertTrue(p.startswith("Image 1 is the first frame"), c["id"])
            self.assertIn("No subtitles. No background music.", p)
            self.assertIn("one continuous take", p)
            self.assertNotRegex(p.lower(), r"close-?up")
            self.assertNotIn("25-75%", p)
            self.assertNotIn("cinematic", p.lower())
            self.assertNotIn("LEAD", p, "names become plain words the model can see")
            self.assertEqual(("Audio 1 is " in p), bool(c["talking"]), c["id"])

    def test_the_line_is_in_the_audio_never_typed_and_the_selfie_drifts(self):
        res = self.plan()
        p = self.call(res, "G01-C1")["prompt"]
        self.assertNotIn("I am at the clinic today to ask about the spots on my face", p)
        self.assertIn("Audio 1 is the woman's voice", p)
        self.assertIn("arm's length", p)

    def test_a_last_picture_is_named_only_on_a_silent_clip_that_has_a_different_one(self):
        # the one exception (P6, 2026-10-21) is a person's split call, which ends on the picture the next part starts
        # from; a talking clip cannot carry a last picture beside its voice, so it is said in the last window instead
        res = self.plan()
        calls = res["calls"]
        for i, c in enumerate(calls):
            nxt = calls[i + 1] if i + 1 < len(calls) else None
            joined = bool(nxt and nxt["clip"] == c["clip"] and c["people"])
            if joined:
                self.assertEqual(c["end_frame"], nxt["start_frame"], c["id"])
            else:
                self.assertIsNone(c["end_frame"], c["id"])
            named = "Image 2 is the last frame" in c["prompt"]
            self.assertEqual(named, joined and not c["talking"] and c["end_frame"] != c["start_frame"], c["id"])


class Cost(Fixture):
    def test_cost_math(self):
        res = self.plan()
        t = res["totals"]
        rate = oc._load("seedance").usd_per_s(CFG["resolution"])    # every clip is Seedance 2.5, priced at its own rate
        self.assertAlmostEqual(t["clip_usd"], round(sum(c["duration"] for c in res["calls"]) * rate, 2), places=2)
        # the upscale runs on this Mac (Real-ESRGAN), so it never adds to the bill
        self.assertEqual(CFG.get("upscale_where"), "local")
        self.assertEqual(t["upscale_usd"], 0)
        self.assertAlmostEqual(t["spend_usd"], round(t["clip_usd"] + t["upscale_usd"], 2), places=2)
        self.assertEqual(t["clip_seconds"], sum(c["duration"] for c in res["calls"]))
        self.assertEqual(t["tts_lines"], len(res["tts"]))
        for c in res["calls"]:
            self.assertAlmostEqual(c["usd"], c["duration"] * rate, places=4)
        self.assertIn("BUDGET", oc.budget_line(t))

    def test_prompts_page_has_every_prompt_verbatim(self):
        res = self.plan()
        page = oc.prompts_md(self.run, res, CFG)
        for c in res["calls"]:
            self.assertIn(c["prompt"], page)
        self.assertIn("only animates the approved picture", page)
        self.assertNotIn("Omni makes", page)


class Runner(Fixture):
    def test_voice_lines_found_by_their_words(self):
        words = [{"text": t, "start": i * 0.5, "end": i * 0.5 + 0.4, "type": "word"} for i, t in
                 enumerate("um a nice even base great skin mm hmm".split())]
        spans = oc.find_lines(words, ["A nice even base. Great skin.", "Mm-hmm."])
        self.assertEqual(spans[0], (0.5, 3.4))
        self.assertEqual(spans[1], (3.5, 4.4))

    def test_chains_and_live_runner_with_fakes(self):
        res = self.plan()
        (self.run / "clips").mkdir(exist_ok=True)
        (self.run / "clips" / "plan.json").write_text(json.dumps(res))
        (self.run / "storyboard.json").write_text(json.dumps(SB))
        made, said = [], []

        def make(run, c, *a):                           # a fake maker that lands the clip, as the real one does
            made.append(c["id"])
            (Path(run) / "clips" / f"{c['id']}.mp4").write_bytes(b"clip")
        green = lambda run, calls: []                   # the clip gate, passed (its own tests are test_clip_gate)
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            rc = oc.run_live(self.run, yes=False, make=make, gate=green,
                             tts=lambda *a: said.append(a[1]["scene"]), refs=lambda *a: [])
        self.assertEqual(rc, 1, "never live without --yes")
        self.assertEqual(made, [])
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rc = oc.run_live(self.run, yes=True, gate=lambda run, calls: ["G01-C1: APPROVED: not approved"],
                             make=make, tts=lambda *a: said.append(a[1]["scene"]), refs=lambda *a: [])
        self.assertEqual(rc, 2, "a red clip gate holds the run, even with --yes")
        self.assertEqual(made, [], "nothing is made past a red gate")
        with redirect_stdout(io.StringIO()):
            rc = oc.run_live(self.run, yes=True, parallel=6, make=make, gate=green,
                             tts=lambda *a: said.append(a[1]["scene"]), refs=lambda *a: [])
        self.assertEqual(rc, 0)
        self.assertEqual(sorted(made), sorted(c["id"] for c in res["calls"]))
        self.assertEqual(sorted(said), sorted(t["scene"] for t in res["tts"]))

    def test_ledger_is_resume_safe(self):
        led = oc.Ledger(self.run)
        led.put("G01-C1", status="done", omni_usd=0.12)
        again = oc.Ledger(self.run)
        self.assertEqual(again.get("G01-C1")["status"], "done")
        led.spend("G01-C1", "m", 4, 0.12, "360p")
        rows = json.loads((self.run / "ledger.json").read_text())
        self.assertEqual(rows[-1]["usd"], 0.12)


class Wordless(Fixture):
    """A piece carried by its song (2026-10-09): no scene has a spoken line, so there is no voice clock —
    every moving section still gets its calls, its length taken from the storyboard."""
    def test_a_piece_with_no_spoken_lines_plans_every_moving_section_from_the_storyboard(self):
        max_s = float(CFG["seconds_range"][1])
        scs = [scene("W1", "LEAD", "", False, happens="walks in"), scene("W2", "LEAD", "", False, happens="turns"),
               scene("W3", "LEAD", "", False), scene("W4", "LEAD", "", False, happens="lifts the jar")]
        sb = {"teardown": "../x", "people_map": {"lead": ["LEAD"]}, "layers": {"voice": []}, "sections": [
            {"id": "G01", "maker": "motion transfer", "seconds": 2.5, "starts": 0.0, "scenes": ["W1"], "voice": {},
             "elements": ["person · LEAD · look-1"], "swipe": {"shots": [shot("K01", 0.0, 0.0, 3.9)]},
             "frames": [{"what": "start frame · set-up shot", "from": "W1", "own": False, "drives": ["K01"]}],
             "clips": [{"scenes": ["W1"], "seconds": 0.0}]},
            {"id": "G02", "maker": "motion transfer", "seconds": 2.0 * max_s + 1.0, "starts": 2.5, "scenes": ["W2"],
             "voice": {}, "elements": ["person · LEAD · look-1"],
             "swipe": {"shots": [shot("K02", 0.0, 3.9, 9.0), shot("K03", 4.0, 9.0, 30.0)]},
             "frames": [{"what": "start frame · set-up shot", "from": "W2", "own": False, "drives": ["K02", "K03"]}],
             "clips": [{"scenes": ["W2"], "seconds": 0.15}]},
            {"id": "G03", "maker": "plate", "seconds": 5.0, "starts": 2.5 + 2.0 * max_s + 1.0, "scenes": ["W3"],
             "voice": {}, "frames": [{"what": "card background", "from": "W3"}], "clips": []},
            {"id": "G04", "maker": "from the brief", "seconds": 2.0, "starts": 2.5 + 2.0 * max_s + 6.0,
             "scenes": ["W4"], "voice": {}, "elements": ["person · LEAD · look-1"], "swipe": {"shots": []},
             "frames": [{"what": "start frame", "from": "W4"}], "clips": [{"scenes": ["W4"], "seconds": 0.0}]},
        ]}
        for pid in ("W1-F1", "W2-F1", "W3-PLATE", "W4-F1"):
            (self.run / "media" / f"{pid}.png").write_bytes(b"png")
        res = oc.plan(self.run, sb, scs, cfg=CFG, people=PEOPLE, style="Phone-grade vertical video.")
        self.assertEqual(res["problems"], [])
        rows = {r["id"]: r for r in res["sections"]}
        self.assertEqual(rows["G03"]["calls"], [], "a card stays a still")
        self.assertIn("approved picture is shown for its time", rows["G03"]["note"])
        for g in sb["sections"]:
            if not g["clips"]:
                continue
            calls = [c for c in res["calls"] if c["section_id"] == g["id"]]
            self.assertTrue(calls, f"{g['id']} moves, so it gets a call")
            self.assertAlmostEqual(sum(c["seconds"] for c in calls), g["seconds"], places=1)
            self.assertAlmostEqual(calls[0]["at"], g["starts"], places=2, msg="sections laid end to end")
            for a, b in zip(calls, calls[1:]):
                self.assertAlmostEqual(a["window"][1], b["window"][0], places=2)
            for c in calls:
                self.assertLessEqual(c["seconds"], max_s + 1e-6)
                self.assertEqual(c["lines"], [])
                self.assertEqual(c["start_frame"], f"{g['scenes'][0]}-F1", "a person's clip starts from the picture")
        g2 = [c for c in res["calls"] if c["section_id"] == "G02"]
        self.assertEqual(len(g2), 3, "over the cap with nowhere to cut: even parts")
        self.assertEqual(len({round(c["seconds"], 2) for c in g2}), 1)
        self.assertEqual(res["tts"], [])


if __name__ == "__main__":
    unittest.main()
