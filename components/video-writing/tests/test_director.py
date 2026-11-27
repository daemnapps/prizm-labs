#!/usr/bin/env python3
"""Stage 5d, the director at the storyboard step: every staged scene gets one idea, kept by the machine; the kept
idea lands in the fields production reads; the swipe's text stays beside it; the pitches, scores and reason are
recorded; a pitch that fails a hard check never wins.

    python3 components/video-writing/tests/test_director.py

Stdlib `unittest`, Python 3.9. No network, no model, no key: the model door is a fake.
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.append(str(HERE.parents[1] / "machine"))
import director as D  # noqa: E402

WS = HERE.parents[3]


def scene(sid, section, happens, beats, kind="broll"):
    return {"id": sid, "section": section, "kind": kind, "setting_id": "BATHROOM", "who": "LEAD", "speaker": "LEAD",
            "happens": happens, "props": ["TUBE"], "outcome": "lands the " + section,
            "script": [{"speaker": "LEAD", "say": "Line for " + sid + "."}],
            "first_frame": {"subject": "LEAD at the sink", "action": "swipe opening for " + sid},
            "shots": [{"id": sid + ".1", "face": "a look"}],
            "beats": [{"id": b, "shot": sid + ".1", "do": "swipe beat " + b, "over": "words " + b} for b in beats]}


def brief_text(doc):
    return "# A brief\n\n## A-ROLL\n\nprose stays\n\n```json\n" + json.dumps(doc, indent=1) + "\n```\n\n## Section check\n\nok\n"


def pitch(title, happens, beat_ids, rung="L3"):
    return {"title": title, "rung": rung, "premise": title.lower(), "picture": "we see " + title,
            "happens": happens, "first_frame_action": "opens on " + title,
            "beats": [{"id": b, "who": "LEAD", "action": title + " beat " + b, "prop": "TUBE", "where": "BATHROOM"}
                      for b in beat_ids]}


def score(title, total_each, **checks):
    s = {"title": title, "stops": total_each, "made": total_each, "doctrine": total_each, "controls": total_each,
         "says_the_line": True, "problem_visible": True, "product_clear": True, "inside_the_scene": True,
         "why": "because " + title}
    s.update(checks)
    return s


class FakeDoor:
    """Answers the director with three pitches per scene and the producer with fixed scores; records each prompt."""

    def __init__(self, scores_for):
        self.scores_for = scores_for
        self.seen = []

    def __call__(self, text, tier):
        self.seen.append((tier, text))
        ids = re.findall(r"^## (S\d+) ·", text, re.M)
        if tier == "designs":
            out = {"scenes": []}
            for sid in ids:
                beats = re.findall(r"^  - `(B\d+)`", text.split("## " + sid + " ·")[1].split("\n## ")[0], re.M)
                out["scenes"].append({"id": sid, "pitches": [
                    pitch("Security Cam " + sid, "is caught on a security cam for " + sid, beats),
                    pitch("Snow Globe " + sid, "shakes a snow globe for " + sid, beats, "L5"),
                    pitch("Plain " + sid, "does it plainly for " + sid, beats, "L2")]})
            return "# STORYBOARD\n```STORYBOARD\n" + json.dumps(out) + "\n```\n"
        return "```SCORES\n" + json.dumps({"scenes": [{"id": sid, "pitches": self.scores_for(sid)} for sid in ids]}) \
            + "\n```\n"


class SongDoor:
    """Plays the grouping call, the director and the producer for a sung plan; records each prompt."""

    def __init__(self, groups=None):
        self.groups = groups
        self.seen = []

    def __call__(self, text, tier):
        self.seen.append((tier, text))
        if "splitting the song into scenes" in text:
            ids = re.findall(r"^(L\d+): ", text, re.M)
            g = self.groups or [{"title": "the theft", "section": "hook", "lines": ids[:2]},
                                {"title": "the letter", "section": "story", "lines": ids[2:]}]
            return "```SCENES\n" + json.dumps({"scenes": g}) + "\n```"
        ids = re.findall(r"^## (M\d+) ·", text, re.M)
        if tier == "designs":
            out = {"scenes": []}
            for sid in ids:
                card = text.split("## " + sid + " ·")[1].split("\n## ")[0]
                beats = re.findall(r"^  - `(B\d+)`", card, re.M)
                shots_line = next((l for l in card.splitlines() if l.startswith("- **Shots**")), "")
                shots = re.findall(r"`(M\d+\.\d+)`", shots_line)
                p = pitch("Idea " + sid, "acts out " + sid, beats)
                p["shots"] = [{"id": s, "face": "face " + s, "gestures": ["moves " + s]} for s in shots]
                out["scenes"].append({"id": sid, "pitches": [p]})
            return "```STORYBOARD\n" + json.dumps(out) + "\n```"
        return "```SCORES\n" + json.dumps({"scenes": [{"id": sid, "pitches": [score("Idea " + sid, 8)]}
                                                        for sid in ids]}) + "\n```"


class SungPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.plan = self.tmp / "song-run" / "plan.json"
        self.plan.parent.mkdir()
        lines = ["I took it", "from the wall", "he wrote to me", "I wrote back", "it came home"]
        self.base = {"brand": "testbrand", "song": {"style_id": "x", "sections": [
            {"name": "intro", "lines": lines[:2]}, {"name": "verse", "lines": lines[2:]}]},
            "scenes": [{"id": f"L{i}", "kind": "broll", "to_camera": False, "voice": "", "lyrics": [ln]}
                       for i, ln in enumerate(lines, 1)]}
        self.plan.write_text(json.dumps(self.base))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_sung_plan_becomes_moments_with_one_directed_shot_per_line(self):
        door = SongDoor()
        picks = D.direct_plan(self.plan, None, caller=door, ws=WS, workers=1)
        plan = json.loads(self.plan.read_text())
        self.assertEqual([s["id"] for s in plan["scenes"]], ["M1", "M2"])
        self.assertEqual(plan["scenes"][0]["lines_from"], ["L1", "L2"])
        self.assertEqual(plan["scenes"][1]["lyrics"], ["he wrote to me", "I wrote back", "it came home"])
        sh = plan["scenes"][1]["shots"]
        self.assertEqual([s["line"] for s in sh], ["L3", "L4", "L5"])
        self.assertEqual(sh[0]["action"], "Idea M2 beat B1")
        self.assertEqual((sh[0]["who"], sh[0]["prop"], sh[0]["where"]), ("LEAD", "TUBE", "BATHROOM"))
        self.assertEqual((sh[2]["face"], sh[2]["gestures"]), ("face M2.3", ["moves M2.3"]))
        self.assertEqual(plan["scenes"][1]["happens"], "acts out M2")
        self.assertEqual(plan["director"]["kept"], 2)
        self.assertEqual(D.unshot_lines(plan), [])
        self.assertEqual(json.loads((self.plan.parent / "plan.before-director.json").read_text()), self.base)
        self.assertEqual(picks["M1"]["kept"]["score"], 32)
        # every sung line is still a line of the script, word for word, in order (song.py reads `lyrics`)
        self.assertEqual([ln for s in plan["scenes"] for ln in s["lyrics"]],
                         [ln for s in self.base["scenes"] for ln in s["lyrics"]])
        self.assertIn("SUNG (each line its own silent shot)", next(t for tier, t in door.seen if "THE STORYBOARD" in t))

    def test_a_cut_that_drops_or_reorders_a_line_falls_back_to_the_songs_sections(self):
        door = SongDoor(groups=[{"title": "a", "section": "hook", "lines": ["L2", "L1"]},
                                {"title": "b", "section": "story", "lines": ["L3", "L4", "L5"]}])
        D.direct_plan(self.plan, None, caller=door, ws=WS, workers=1)
        plan = json.loads(self.plan.read_text())
        self.assertEqual([s["lines_from"] for s in plan["scenes"]], [["L1", "L2"], ["L3", "L4", "L5"]])
        self.assertTrue((self.plan.parent / "director" / "0-group.fallback.txt").is_file())

    def test_a_rerun_starts_from_the_plan_the_song_spec_made(self):
        D.direct_plan(self.plan, None, caller=SongDoor(), ws=WS, workers=1)
        D.direct_plan(self.plan, None, caller=SongDoor(), ws=WS, workers=1, fresh=True)
        plan = json.loads(self.plan.read_text())
        self.assertEqual([s["id"] for s in plan["scenes"]], ["M1", "M2"])
        self.assertEqual(json.loads((self.plan.parent / "plan.before-director.json").read_text()), self.base)

    def test_a_scene_where_nothing_passed_gets_one_more_round_told_why(self):
        class SecondTime(SongDoor):
            def __call__(self, text, tier):
                said = SongDoor.__call__(self, text, tier)
                first_round = "Your first round for this scene failed" not in text
                if tier == "checks" and first_round and "## M2 ·" in text:
                    got = json.loads(said.split("```SCORES\n")[1].split("\n```")[0])
                    for s in got["scenes"]:
                        if s["id"] == "M2":
                            s["pitches"][0]["says_the_line"] = False
                    return "```SCORES\n" + json.dumps(got) + "\n```"
                return said
        door = SecondTime()
        picks = D.direct_plan(self.plan, None, caller=door, ws=WS, workers=1)
        self.assertEqual(picks["M2"]["round"], 2)
        self.assertIn("does not say the line", picks["M2"]["first_round"][0]["out"])
        self.assertEqual(picks["M2"]["kept"]["title"], "Idea M2")
        retry = [t for tier, t in door.seen if "Your first round for this scene failed" in t]
        self.assertEqual(len(retry), 2)                                # the director again, then the producer
        self.assertIn('"Idea M2" was out because it does not say the line', retry[0])
        self.assertNotIn("## M1 ·", retry[0])                         # only the scene that failed goes back
        self.assertTrue((self.plan.parent / "director" / "r1-director.md").is_file())

    def test_a_line_with_no_kept_idea_is_reported(self):
        class NoPass(SongDoor):
            def __call__(self, text, tier):
                said = SongDoor.__call__(self, text, tier)
                return said.replace('"says_the_line": true', '"says_the_line": false') if tier == "checks" else said
        D.direct_plan(self.plan, None, caller=NoPass(), ws=WS, workers=1)
        plan = json.loads(self.plan.read_text())
        self.assertEqual(len(D.unshot_lines(plan)), 5)
        self.assertEqual(plan["scenes"][0]["director"]["state"], "no idea kept")

    def test_the_songs_clock_is_laid_on_line_by_line_in_order(self):
        D.direct_plan(self.plan, None, caller=SongDoor(), ws=WS, workers=1)
        (self.plan.parent / "song").mkdir()
        heard = [("I took it", 1.0, 2.0), ("From the wall!", 2.1, 3.0), ("he wrote to me", 5.0, 6.0),
                 ("I wrote back", 6.5, 7.5)]                         # "it came home" is not in the timing at all
        (self.plan.parent / "song" / "timing.json").write_text(json.dumps(
            {"at": "t1", "lines": [{"line": a, "start": s, "end": e} for a, s, e in heard]}))
        missing = D.times_onto(self.plan)
        plan = json.loads(self.plan.read_text())
        self.assertEqual([(s["start"], s["end"]) for s in plan["scenes"][0]["shots"]], [(1.0, 2.0), (2.1, 3.0)])
        self.assertEqual(plan["scenes"][0]["window"], [1.0, 3.0])
        self.assertEqual(plan["scenes"][1]["window"], [5.0, 7.5])
        self.assertEqual(missing, ["L5"])
        self.assertNotIn("start", plan["scenes"][1]["shots"][2])
        self.assertEqual(plan["director"]["times"]["missing"], ["L5"])

    def test_a_line_listed_but_not_heard_takes_the_gap_it_sits_in(self):
        plan = {"scenes": [{"shots": [{"line": "L1", "lyrics": ["one"]}, {"line": "L2", "lyrics": ["two"]},
                                      {"line": "L3", "lyrics": ["three"]}]}]}
        missing = D.lay_times(plan, {"lines": [{"line": "one", "start": 1.0, "end": 2.0}, {"line": "two", "match": 0.5},
                                               {"line": "three", "start": 4.5, "end": 6.0}]})
        sh = plan["scenes"][0]["shots"]
        self.assertEqual([(s["start"], s["end"], s["timed"]) for s in sh],
                         [(1.0, 2.0, "heard"), (2.0, 4.5, "window"), (4.5, 6.0, "heard")])
        self.assertEqual(missing, [])

    def test_a_line_sung_twice_takes_each_time_in_turn(self):
        plan = {"scenes": [{"shots": [{"line": "L1", "lyrics": ["so I stole it"]}]},
                           {"shots": [{"line": "L9", "lyrics": ["So I stole it"]}]}]}
        D.lay_times(plan, {"lines": [{"line": "so I stole it", "start": 10, "end": 12},
                                     {"line": "so I stole it", "start": 90, "end": 92}]})
        self.assertEqual([plan["scenes"][k]["shots"][0]["start"] for k in (0, 1)], [10, 90])

    def test_a_directed_sung_plan_becomes_a_sung_stage_5_brief(self):
        wrun = self.tmp / "spoken"
        (wrun / "stages").mkdir(parents=True)
        spoken = {"lane": "paid", "piece": {"title": "Spoken"}, "song": None,
                  "cast": [{"id": "LEAD", "identity_block": "a person"}],
                  "world": [{"id": "BATHROOM", "description": "a sink"}], "props": [{"id": "TUBE"}],
                  "product_lock": [{"id": "TUBE"}],
                  "scenes": [{"id": "S1", "first_frame": {"style": "soft 3d", "refs": ["LEAD cast sheet", "3d style frame"]}}]}
        (wrun / "stages" / "5-brief.md").write_text(brief_text(spoken))
        (wrun / "run.json").write_text(json.dumps({"brand": "testbrand", "product": "the-tube", "style_id": "family-3d"}))
        D.direct_plan(self.plan, wrun, caller=SongDoor(), ws=self.tmp, workers=1)
        out = self.tmp / "runs" / "video-teardown" / "_work" / "song-run"
        brief = D.brief_doc((out / "stages" / "5-brief.md").read_text())
        self.assertEqual([s["id"] for s in brief["scenes"]], ["S1", "S2"])
        s2 = brief["scenes"][1]
        self.assertEqual((s2["voice"], s2["kind"], s2["to_camera"], s2["speaker"]), ("", "broll", False, ""))
        self.assertEqual(s2["lyrics"], ["he wrote to me", "I wrote back", "it came home"])
        self.assertEqual([(b["over"], b["who"], b["action"], b["where"]) for b in s2["beats"]][0],
                         ("he wrote to me", "LEAD", "Idea M2 beat B1", "BATHROOM"))
        self.assertEqual((s2["shots"][2]["face"], s2["shots"][2]["gestures"]), ("face M2.3", ["moves M2.3"]))
        self.assertEqual(s2["setting_id"], "BATHROOM")
        self.assertEqual(s2["first_frame"]["style"], "soft 3d")
        self.assertEqual(s2["happens"], "acts out M2")
        self.assertEqual([s["opens"] for s in brief["scenes"]], [True, False])
        song = brief["song"]
        self.assertEqual(song["style_id"], "x")
        self.assertEqual([(x["name"], x["scene"]) for x in song["sections"]], [("intro", "S1"), ("verse", "S2")])
        # every line in the song is a scene lyric and every scene lyric is in the song, in order
        self.assertEqual([ln for x in song["sections"] for ln in x["lines"]],
                         [ln for s in brief["scenes"] for ln in s["lyrics"]])
        self.assertEqual(brief["cast"], spoken["cast"])
        st = json.loads((out / "run.json").read_text())
        self.assertEqual((st["brand"], st["product"], st["style_id"], st["form"]), ("testbrand", "the-tube", "family-3d", "sung"))
        self.assertEqual(st["stages"]["stage5"]["out"], "stages/5-brief.md")
        self.assertEqual(st["source_run"], "spoken")

    def test_a_timed_sung_shot_carries_its_seconds_so_the_merge_measures_the_song(self):
        plan = {"song": {"sections": [{"name": "verse", "lines": ["a", "b"]}]},
                "scenes": [{"id": "M1", "lyrics": ["a", "b"], "lines_from": ["L1", "L2"], "window": [1.0, 9.0],
                            "shots": [{"line": "L1", "lyrics": ["a"], "start": 1.0, "end": 4.0, "action": "x"},
                                      {"line": "L2", "lyrics": ["b"], "start": 4.5, "end": 9.0, "action": "y"}]}]}
        doc = D.sung_brief(plan, {})
        self.assertEqual([s["seconds"] for s in doc["scenes"][0]["shots"]], [3.0, 4.5])
        self.assertEqual(doc["song"]["sections"][0]["seconds"], 8.0)

    def test_song_section_names_are_stage_5s(self):
        self.assertEqual([D.section_kind(x) for x in ("verse 2", "Chorus 2", "pre-chorus", "Bridge", "outro", "x")],
                         ["verse", "chorus", "pre-chorus", "bridge", "outro", "verse"])

    def test_a_sung_brief_scene_gets_one_shot_per_line(self):
        sc = D.sung_shots({"id": "S4", "section": "story", "lyrics": ["one", "two"]})
        self.assertEqual([s["id"] for s in sc["shots"]], ["S4.1", "S4.2"])
        self.assertEqual([(b["id"], b["over"]) for b in sc["beats"]], [("B1", "one"), ("B2", "two")])
        self.assertTrue(D.directable(sc))


class Director(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.run = self.tmp / "run"
        (self.run / "stages").mkdir(parents=True)
        self.doc = {"piece": {"title": "Test Piece"}, "song": None,
                    "world": [{"id": "BATHROOM", "description": "a sink"}, {"id": "OFFICE", "description": "a desk"}],
                    "scenes": [
            scene("S1", "hook", "confesses with one finger on the wall", ["B1", "B2"], kind="talking"),
            scene("S2", "product", "reaches for the tube", ["B1"]),
            {"id": "S3", "section": "offer", "kind": "card", "happens": "", "beats": []},
            scene("S4", "transformation", "lifts her arm", ["B1"])]}
        D.brief_path(self.run).write_text(brief_text(self.doc))
        (self.run / "run.json").write_text(json.dumps({"brand": "testbrand"}))
        (self.run / "stages" / "4i-controlling-idea.md").write_text(
            "## THE IDEA\nsalt the snow\n\n### THE FIVE CANDIDATES\nloser table")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def go(self, scores_for, **kw):
        door = FakeDoor(scores_for)
        picks = D.direct(self.run, caller=door, ws=WS, batch=2, workers=1, **kw)
        return picks, door, D.brief_doc(D.brief_path(self.run).read_text())

    def test_every_staged_scene_gets_one_idea_in_the_fields_production_reads(self):
        picks, door, doc = self.go(lambda sid: [score("Security Cam " + sid, 9), score("Snow Globe " + sid, 7),
                                                score("Plain " + sid, 5)])
        self.assertEqual(sorted(picks), ["S1", "S2", "S4"])           # the card is not staged
        s1 = doc["scenes"][0]
        self.assertEqual(s1["happens"], "is caught on a security cam for S1")
        self.assertEqual(s1["happens_swipe"], "confesses with one finger on the wall")
        self.assertEqual([b["action"] for b in s1["beats"]], ["Security Cam S1 beat B1", "Security Cam S1 beat B2"])
        self.assertEqual(s1["beats"][0]["do"], s1["beats"][0]["action"])
        self.assertEqual(s1["beats"][0]["do_swipe"], "swipe beat B1")
        self.assertEqual((s1["beats"][0]["who"], s1["beats"][0]["prop"], s1["beats"][0]["where"]),
                         ("LEAD", "TUBE", "BATHROOM"))
        self.assertEqual(s1["first_frame"]["action"], "opens on Security Cam S1")
        self.assertEqual(s1["first_frame"]["action_swipe"], "swipe opening for S1")
        self.assertEqual(s1["director"]["title"], "Security Cam S1")
        self.assertEqual(doc["scenes"][2], self.doc["scenes"][2])    # untouched

    def test_the_brief_keeps_its_prose_and_a_copy_of_itself(self):
        before = D.brief_path(self.run).read_text()
        self.go(lambda sid: [score("Security Cam " + sid, 9)])
        after = D.brief_path(self.run).read_text()
        self.assertIn("prose stays", after)
        self.assertIn("## Section check", after)
        self.assertIn("## Director's picks (stage 5d, automatic)", after)
        self.assertEqual((self.run / "stages" / "5-brief.before-director.md").read_text(), before)

    def test_pitches_scores_and_the_reason_are_recorded(self):
        self.go(lambda sid: [score("Security Cam " + sid, 9), score("Snow Globe " + sid, 7)])
        rec = json.loads((self.run / "director" / "picks.json").read_text())["picks"]["S1"]
        self.assertEqual(len(rec["pitches"]), 3)
        self.assertEqual(rec["kept"]["title"], "Security Cam S1")
        self.assertIn("36/40", rec["why"])
        self.assertEqual(rec["before"], "confesses with one finger on the wall")
        for name in ("1-director.prompt.md", "1-director.md", "1-pick.prompt.md", "1-pick.md", "picks.md"):
            self.assertTrue((self.run / "director" / name).is_file(), name)

    def test_a_pitch_that_fails_a_hard_check_never_wins(self):
        # the top scorer hides the problem on a hook; the product scene's top scorer hides the product
        def scores(sid):
            return [score("Security Cam " + sid, 10, problem_visible=False, product_clear=False),
                    score("Snow Globe " + sid, 6), score("Plain " + sid, 4)]
        picks, _, doc = self.go(scores)
        self.assertEqual(picks["S1"]["kept"]["title"], "Snow Globe S1")
        self.assertEqual(picks["S2"]["kept"]["title"], "Snow Globe S2")
        # a payoff scene does not carry the problem check, but it carries the product check
        self.assertEqual(picks["S4"]["kept"]["title"], "Snow Globe S4")
        out = next(r for r in picks["S1"]["scores"] if r["title"] == "Security Cam S1")["out"]
        self.assertIn("problem not visible", out)

    def test_a_pitch_whose_beats_do_not_line_up_is_out(self):
        sc = self.doc["scenes"][0]
        bad = pitch("Wrong Beats", "does something", ["B1"])
        good = pitch("Right Beats", "does something else", ["B1", "B2"])
        d = D.decide(sc, [bad, good], [score("Wrong Beats", 10), score("Right Beats", 3)])
        self.assertEqual(d["keep"]["title"], "Right Beats")
        self.assertIn("does not restage every beat of the scene", d["table"][0]["out"])

    @mock.patch.dict("os.environ", {"VISUALS_OURS_OFF": "director"})   # v1, kept behind the switch
    def test_each_shot_gets_the_ideas_face_and_gestures_the_swipes_kept_beside(self):
        sc = json.loads(json.dumps(self.doc["scenes"][1]))
        sc["shots"][0]["gestures"] = ["reaches"]
        p = pitch("Shots", "does it", ["B1"])
        p["shots"] = [{"id": "S2.1", "face": "jaw set, eyes on the lens", "gestures": ["grips the tube", ""]},
                      {"id": "S9.9", "face": "not this scene's shot"}]
        D.apply_pick(sc, p, "r")
        self.assertEqual(sc["shots"][0]["face"], "jaw set, eyes on the lens")
        self.assertEqual(sc["shots"][0]["face_swipe"], "a look")
        self.assertEqual(sc["shots"][0]["gestures"], ["grips the tube"])
        self.assertEqual(sc["shots"][0]["gestures_swipe"], ["reaches"])
        self.assertEqual(len(sc["shots"]), 1)
        card = D.scene_card(sc)                                        # the next run is shown the swipe's face
        self.assertIn("`S2.1` face today: a look", card)

    def test_a_beat_must_show_the_person_its_words_name(self):
        sc = scene("S1", "hook", "confesses", ["B1", "B2"], kind="talking")
        sc["folded_from"] = ["S1", "S2"]
        sc["shots"] = [{"id": "S1.1", "face": "eyes down"}, {"id": "S1.2", "face": "pen tip"}]
        sc["beats"][1].update(shot="S1.2", over="Two weeks later, the general manager wrote me a letter.")
        doc = {"cast": [{"id": "LEAD"}, {"id": "MANAGER"}, {"id": "HUSBAND"}],
               "roll_sheet": [{"row": "0:04-0:06 · [shows: manager writing]", "scene": "S2"}]}
        self.assertEqual(D.named_people(sc, doc), {"B2": "MANAGER"})
        self.assertIn("MUST SHOW MANAGER", D.scene_card(sc, doc))
        wrong, right = pitch("Wrong", "x", ["B1", "B2"]), pitch("Right", "y", ["B1", "B2"])
        right["beats"][1]["who"] = "MANAGER"
        d = D.decide(sc, [wrong, right], [score("Wrong", 10), score("Right", 6)], doc)
        self.assertEqual(d["keep"]["title"], "Right")
        self.assertIn("B2 does not show MANAGER, whom its words name", d["table"][0]["out"])
        # a name the words carry but the swipe's shot does not show is left to the producer
        doc["roll_sheet"] = [{"row": "0:04-0:06 · [shows: hand on desk]", "scene": "S2"}]
        self.assertEqual(D.named_people(sc, doc), {})

    def test_a_beats_do_is_one_action_and_the_whole_picture_stays_in_action(self):
        self.assertEqual(D.one_action("she rubs her arm and a cloud of flakes comes off"), "she rubs her arm")
        self.assertEqual(D.one_action("her thumb presses the collar; it does not move"), "her thumb presses the collar")
        self.assertEqual(D.one_action("lifts the tube"), "lifts the tube")
        self.assertEqual(D.one_action("steps in as a towel drifts up"), "steps in")
        self.assertEqual(D.one_action("stands, tipping the bank off her lap"), "stands")
        self.assertEqual(D.one_action("stops three tubes rolling"), "halts three tubes rolling")
        self.assertEqual([D.doctrine_section(x) for x in ("mechanism", "story", "hook", "nonsense")],
                         ["unique-mechanism", "identification", "hook", "identification"])
        sc = json.loads(json.dumps(self.doc["scenes"][1]))
        p = pitch("Two", "does it", ["B1"])
        p["beats"][0]["action"] = "grips the tube as snow falls off her arm"
        D.apply_pick(sc, p, "r")
        self.assertEqual(sc["beats"][0]["do"], "grips the tube")
        self.assertEqual(sc["beats"][0]["action"], "grips the tube as snow falls off her arm")
        p["beats"][0]["do"] = "squeezes the tube"
        sc = json.loads(json.dumps(self.doc["scenes"][1]))
        D.apply_pick(sc, p, "r")
        self.assertEqual(sc["beats"][0]["do"], "squeezes the tube")

    def test_a_beat_the_pitch_adds_is_dropped_not_held(self):
        sc = json.loads(json.dumps(self.doc["scenes"][1]))
        extra = pitch("Extra Beat", "does more", ["B1", "B2"])
        d = D.decide(sc, [extra], [score("Extra Beat", 7)])
        self.assertEqual(d["keep"]["title"], "Extra Beat")
        D.apply_pick(sc, d["keep"], "r")
        self.assertEqual([b["id"] for b in sc["beats"]], ["B1"])
        self.assertEqual(sc["beats"][0]["action"], "Extra Beat beat B1")

    def test_when_nothing_passes_the_scene_keeps_the_swipe_staging(self):
        picks, _, doc = self.go(lambda sid: [score(t + " " + sid, 9, says_the_line=False)
                                             for t in ("Security Cam", "Snow Globe", "Plain")])
        self.assertIsNone(picks["S1"]["kept"])
        self.assertEqual(doc["scenes"][0]["happens"], "confesses with one finger on the wall")
        self.assertNotIn("director", doc["scenes"][0])
        self.assertEqual(D.brief_path(self.run).read_text(), brief_text(self.doc))   # nothing kept: brief untouched
        self.assertFalse((self.run / "stages" / "5-brief.before-director.md").exists())

    def test_a_tie_goes_to_the_directors_order(self):
        sc = self.doc["scenes"][1]
        a, b = pitch("First", "x", ["B1"]), pitch("Second", "y", ["B1"])
        self.assertEqual(D.decide(sc, [a, b], [score("Second", 8), score("First", 8)])["keep"]["title"], "First")

    @mock.patch.dict("os.environ", {"VISUALS_OURS_OFF": "director"})   # v1, kept behind the switch
    def test_running_again_starts_from_the_swipe_not_from_the_last_pick(self):
        self.go(lambda sid: [score("Security Cam " + sid, 9)])
        picks, door, doc = self.go(lambda sid: [score("Snow Globe " + sid, 9)], fresh=True)
        s1 = doc["scenes"][0]
        self.assertEqual(s1["happens"], "shakes a snow globe for S1")
        self.assertEqual(s1["happens_swipe"], "confesses with one finger on the wall")
        self.assertEqual(s1["beats"][0]["do_swipe"], "swipe beat B1")
        self.assertEqual(picks["S1"]["before"], "confesses with one finger on the wall")
        director_prompt = next(t for tier, t in door.seen if tier == "designs")
        self.assertIn("today: swipe beat B1", director_prompt)
        self.assertEqual(D.brief_path(self.run).read_text().count("## Director's picks"), 1)

    def test_a_hand_fix_made_after_directing_survives_a_rerun(self):
        # 2026-11-20: a rerun from the copy stage 5 wrote threw away every fix made to the directed brief
        self.go(lambda sid: [score("Security Cam " + sid, 9)])
        bp = D.brief_path(self.run)
        doc = D.brief_doc(bp.read_text())
        doc["scenes"][0]["first_frame"]["viewpoint"] = "a fixed observer; the arm enters from the right edge"
        doc["scenes"][0]["voice"] = "A corrected line."
        bp.write_text(D.put_doc(bp.read_text(), doc))
        _, _, doc = self.go(lambda sid: [score("Snow Globe " + sid, 9)], fresh=True)
        s1 = doc["scenes"][0]
        self.assertEqual(s1["first_frame"]["viewpoint"], "a fixed observer; the arm enters from the right edge")
        self.assertEqual(s1["voice"], "A corrected line.")
        self.assertEqual(s1["happens"], "shakes a snow globe for S1")             # the new pick
        self.assertEqual(s1["happens_swipe"], "confesses with one finger on the wall")   # never the last pick
        self.assertEqual(s1["first_frame"]["action_swipe"], "swipe opening for S1")
        self.assertEqual(s1["beats"][0]["do_swipe"], "swipe beat B1")
        self.assertEqual(bp.read_text().count('"happens_swipe"'), 3)

    def test_some_scenes_again_keep_every_other_scenes_pick_and_record(self):
        self.go(lambda sid: [score("Security Cam " + sid, 9)])
        picks, _, doc = self.go(lambda sid: [score("Snow Globe " + sid, 9)], fresh=True, scenes=["S2"])
        by = {s["id"]: s for s in doc["scenes"]}
        self.assertEqual(by["S1"]["happens"], "is caught on a security cam for S1")      # untouched
        self.assertEqual(by["S2"]["happens"], "shakes a snow globe for S2")              # redone
        self.assertEqual(by["S2"]["happens_swipe"], next(x for x in self.doc["scenes"] if x["id"] == "S2")["happens"])
        rec = json.loads((self.run / "director" / "picks.json").read_text())["picks"]
        self.assertEqual(sorted(rec), ["S1", "S2", "S4"])
        self.assertEqual(rec["S1"]["kept"]["title"], "Security Cam S1")
        self.assertEqual(rec["S2"]["kept"]["title"], "Snow Globe S2")
        self.assertIn("Security Cam S1", D.brief_path(self.run).read_text().split("## Director's picks")[1])

    def test_the_director_reads_the_runs_own_rulings(self):
        (self.run / "RULINGS.md").write_text("4. The travel pouch is removed everywhere, any picture of it included.\n")
        _, door, _ = self.go(lambda sid: [score("Security Cam " + sid, 9)])
        text = next(t for tier, t in door.seen if tier == "designs")
        self.assertIn("This run's rulings (RULINGS.md)", text)
        self.assertIn("The travel pouch is removed everywhere", text)

    def test_the_owners_rulings_reach_the_director_from_the_end_of_a_long_file(self):
        (self.run / "RULINGS.md").write_text("# Run rulings\n" + "- an older note\n" * 4000
                                             + "## Owner rulings — 2026-11-20\n\n4. No pouch anywhere, any picture included.\n")
        _, door, _ = self.go(lambda sid: [score("Security Cam " + sid, 9)])
        text = next(t for tier, t in door.seen if tier == "designs")
        self.assertIn("4. No pouch anywhere, any picture included.", text)
        self.assertLess(text.index("No pouch anywhere"), text.index("an older note"))

    def test_unlayer_takes_the_picks_off_and_nothing_else(self):
        self.go(lambda sid: [score("Security Cam " + sid, 9)])
        doc = D.unlayer(D.brief_doc(D.brief_path(self.run).read_text()))
        s1 = doc["scenes"][0]
        self.assertEqual(s1["happens"], "confesses with one finger on the wall")
        self.assertEqual(s1["beats"][0]["do"], "swipe beat B1")
        self.assertNotIn("action", s1["beats"][0])                   # stage 5 wrote none
        self.assertNotIn("director", s1)
        self.assertNotIn('"happens_swipe"', json.dumps(doc))
        self.assertEqual(s1["first_frame"]["action"], "swipe opening for S1")

    @mock.patch.dict("os.environ", {"VISUALS_OURS_OFF": "director"})   # v1, kept behind the switch
    def test_the_director_hears_the_rulings_the_idea_and_the_controls_target(self):
        _, door, _ = self.go(lambda sid: [score("Security Cam " + sid, 9)])
        tiers = [t for t, _ in door.seen]
        self.assertEqual(tiers.count("designs"), 2)                   # three scenes, batches of two
        text = next(t for tier, t in door.seen if tier == "designs")
        self.assertIn("You are **the director**", text)               # the room's own director prompt
        self.assertIn("## The floor (every rung, no exceptions)", text)   # its ladder
        self.assertIn("salt the snow", text)
        self.assertNotIn("loser table", text)
        self.assertIn("Keep the problem visible until the payoff", text)
        self.assertIn("absurdity:", text)                              # the creative-controls target
        self.assertIn("backbone only", text)
        self.assertIn("- OFFICE: a desk", text)                       # the places a beat may name
        self.assertNotRegex(text, r"\{(ladder|rungs|per_rung|rulings|seed|scenes|per_scene|hard_rules)\}")
        pick = next(t for tier, t in door.seen if tier == "checks")
        self.assertIn("Stops the scroll", pick)

    def test_a_rerun_reuses_replies_on_file_and_fresh_asks_again(self):
        self.go(lambda sid: [score("Security Cam " + sid, 9)])
        _, door, doc = self.go(lambda sid: [score("Snow Globe " + sid, 9)])
        self.assertEqual(door.seen, [])                                # every prompt unchanged: no call
        self.assertEqual(doc["scenes"][0]["director"]["title"], "Security Cam S1")
        _, door, _ = self.go(lambda sid: [score("Snow Globe " + sid, 9)], fresh=True)
        self.assertEqual(len(door.seen), 4)

    def test_a_batch_that_keeps_breaking_fails_the_stage_naming_only_its_scenes(self):
        # owner ruling 2026-11-20: every visual is ours, so a broken batch is asked again and never left on the swipe
        class Broken(FakeDoor):
            def __call__(self, text, tier):
                if tier == "designs" and "## S4 ·" in text:
                    return "no block at all"
                return FakeDoor.__call__(self, text, tier)
        door = Broken(lambda sid: [score("Security Cam " + sid, 9)])
        with self.assertRaises(D.DirectorFailed) as got:
            D.direct(self.run, caller=door, ws=WS, batch=2, workers=1)
        self.assertIn("S4", str(got.exception))
        self.assertNotIn("S3", str(got.exception))

    def test_a_batch_that_breaks_once_is_asked_again_and_directed(self):
        class Once(FakeDoor):
            broke = False
            def __call__(self, text, tier):
                if tier == "designs" and "## S4 ·" in text and not Once.broke:
                    Once.broke = True
                    return "no block at all"
                return FakeDoor.__call__(self, text, tier)
        door = Once(lambda sid: [score("Security Cam " + sid, 9)])
        picks = D.direct(self.run, caller=door, ws=WS, batch=2, workers=1)
        self.assertEqual(picks["S4"]["kept"]["title"], "Security Cam S4")
        self.assertNotIn("failed", picks["S4"]["why"] or "")

    def test_a_scene_id_written_with_its_heading_still_matches(self):
        self.assertEqual(D.sid("S40 · section unique-mechanism · broll · 3D SKIN"), "S40")
        self.assertEqual(D.sid("## S1T2"), "S1T2")
        self.assertEqual(D.sid("S3"), "S3")

    def test_a_raw_line_break_inside_a_string_is_read(self):
        got = D.parse_block('```STORYBOARD\n{"scenes": [{"id": "S1", "note": "one\nline\tbreak",}]}\n```', "STORYBOARD")
        self.assertEqual(got["scenes"][0]["note"], "one\nline\tbreak")

    def test_a_trailing_comma_in_the_reply_is_read(self):
        got = D.parse_block('```STORYBOARD\n{"scenes": [{"id": "S1", "pitches": [1, 2,],},]}\n```', "STORYBOARD")
        self.assertEqual(got["scenes"][0]["pitches"], [1, 2])

    def test_the_brief_keeps_its_own_json_formatting(self):
        doc = dict(self.doc, piece={"title": "Caf\u00e9 \u00b7 Piece"})
        D.brief_path(self.run).write_text("# B\n\n```json\n" + json.dumps(doc, indent=2) + "\n```\n")
        self.go(lambda sid: [score("Security Cam " + sid, 9)])
        block = re.findall(r"```json\n(.*?)\n```", D.brief_path(self.run).read_text(), re.S)[-1]
        self.assertTrue(block.startswith('{\n  "piece"'))
        self.assertIn("\\u00b7", block)

    def test_a_new_stage_5_brief_replaces_the_kept_copy(self):
        self.go(lambda sid: [score("Security Cam " + sid, 9)])
        doc = json.loads(json.dumps(self.doc))
        doc["scenes"][0]["happens"] = "a new stage-5 line"
        D.brief_path(self.run).write_text(brief_text(doc))
        picks, _, out = self.go(lambda sid: [score("Snow Globe " + sid, 9)], fresh=True)
        self.assertEqual(picks["S1"]["before"], "a new stage-5 line")
        self.assertEqual(out["scenes"][0]["happens_swipe"], "a new stage-5 line")
        self.assertIn("a new stage-5 line", (self.run / "stages" / "5-brief.before-director.md").read_text())

    @mock.patch.dict("os.environ", {"VISUALS_OURS_OFF": "director"})   # v1, kept behind the switch
    def test_each_shot_says_what_the_swipe_shows_there(self):
        sc = scene("S1", "hook", "confesses", ["B1", "B2"])
        sc["folded_from"] = ["S1", "S2"]
        sc["shots"] = [{"id": "S1.1", "face": "eyes down"}, {"id": "S1.2", "face": "pen tip", "gestures": ["pen strokes"]}]
        sc["beats"][1]["shot"] = "S1.2"
        doc = {"roll_sheet": [{"row": "0:04-0:06 · [shows: manager writing]", "scene": "S2"}]}
        card = D.scene_card(sc, doc)
        self.assertIn("(shot S1.2: pen tip; today: pen strokes · the swipe shows: manager writing)", card)

    def test_dry_writes_prompts_and_changes_nothing(self):
        before = D.brief_path(self.run).read_text()
        door = FakeDoor(lambda sid: [])
        D.direct(self.run, caller=door, ws=WS, dry=True)
        self.assertEqual(door.seen, [])
        self.assertEqual(D.brief_path(self.run).read_text(), before)
        self.assertTrue((self.run / "director" / "1-director.prompt.md").is_file())

    def test_the_prompts_name_no_brand(self):
        brands = [p.name for p in (WS / "brands").iterdir() if p.is_dir()]
        for f in D.PROMPTS.glob("*.md"):
            low = f.read_text().lower()
            for b in brands:
                self.assertNotIn(b.lower(), low, f"{f.name} names {b}")


if __name__ == "__main__":
    unittest.main()
