#!/usr/bin/env python3
"""Scenes are sequences (BRIEF-SPEC "Scenes and shots", 2026-11-08): one moment split into one scene per line is
caught, and folding it keeps every shot, line, speaker and beat in order.

    python3 components/video-writing/tests/test_scene_shots.py

Stdlib `unittest`, Python 3.9. No network, no model, no key.
"""
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "machine"))
import scene_shots as SS  # noqa: E402


def turn(n, speaker, say, parent="S1"):
    sid = f"S1T{n}"
    return {"id": sid, "section": "hook", "kind": "talking", "speaker": speaker, "voice": say, "parent_scene": parent,
            "setting_id": "SET", "who": "HOST, GUEST", "first_frame": {"subject": f"frame {n}"},
            "last_frame": {"change": f"end {n}"},
            "shots": [{"id": f"{sid}.1", "copies": "K01", "lines": [{"say": say}]}],
            "beats": [{"id": "B1", "shot": f"{sid}.1", "do": f"beat {n}"}]}


def beat(sid, section, place, secs):
    """A b-roll scene with no parent: `secs` seconds of read at three words a second."""
    return {"id": sid, "section": section, "kind": "broll", "speaker": "creator", "voice": " ".join(["word"] * (secs * 3)),
            "setting_id": place, "who": "creator", "shots": [{"id": sid + ".1", "copies": "K" + sid}], "beats": []}


class SceneShots(unittest.TestCase):
    def setUp(self):
        self.scenes = [turn(1, "HOST", "Question?"), turn(2, "GUEST", "Answer."), turn(3, "HOST", "Why?"),
                       {"id": "S2", "section": "proof", "kind": "card", "shots": [{"id": "S2.1"}]}]

    def test_folding_keeps_every_scenes_staging_on_its_own_shot(self):
        a = dict(turn(1, "HOST", "Question?"), happens="points at the shelf", happens_swipe="was a")
        b = dict(turn(2, "GUEST", "Answer."), happens="snow falls on the seat", happens_swipe="was b")
        out = SS.fold([a, b])
        self.assertEqual(out[0]["happens"], "Shot 1: points at the shelf\nShot 2: snow falls on the seat")
        self.assertEqual(out[0]["happens_swipe"], "Shot 1: was a\nShot 2: was b")
        same = SS.fold([dict(turn(1, "HOST", "Q?"), happens="one moment"), dict(turn(2, "GUEST", "A."), happens="one moment")])
        self.assertEqual(same[0]["happens"], "one moment")

    def test_a_split_moment_is_caught(self):
        got = SS.check(self.scenes)
        self.assertEqual(len(got), 1)
        self.assertIn("S1T1–S1T3", got[0])

    def test_fold_keeps_every_shot_line_and_speaker_in_order(self):
        out = SS.fold(self.scenes)
        self.assertEqual([s["id"] for s in out], ["S1", "S2"])
        s1 = out[0]
        self.assertEqual([sh["id"] for sh in s1["shots"]], ["S1.1", "S1.2", "S1.3"])
        self.assertEqual([sh["speaker"] for sh in s1["shots"]], ["HOST", "GUEST", "HOST"])
        self.assertEqual([x["speaker"] for x in s1["script"]], ["HOST", "GUEST", "HOST"])
        self.assertEqual(s1["voice"], "Question? Answer. Why?")
        self.assertEqual(s1["speaker"], "several")
        self.assertEqual([b["shot"] for b in s1["beats"]], ["S1.1", "S1.2", "S1.3"])
        self.assertEqual(s1["first_frame"]["subject"], "frame 1")
        self.assertEqual(s1["last_frame"]["change"], "end 3")
        self.assertEqual([sh.get("scene_master") for sh in s1["shots"]], [None, "S1.1", "S1.1"])
        self.assertEqual(s1["take"], "continuous")               # every shot copies K01: the swipe holds one take
        self.assertEqual(s1["motion"], {"copies": "K01"})

    def test_cards_stay_apart(self):
        other = turn(4, "HOST", "Elsewhere.", parent="S9")
        out = SS.fold(self.scenes[:2] + [other] + self.scenes[3:])
        self.assertEqual([s["id"] for s in out], ["S1", "S2"])     # same section, within 30 s: one generation
        self.assertEqual(out[1]["kind"], "card")

    def test_one_generation_carries_a_section_across_places(self):
        """2026-11-12: the hook is one scene, and a run of solution beats is one scene, up to 30 s."""
        hook = [beat("A1", "hook", "BATHROOM", 5), beat("A2", "hook", "OFFICE", 3)]
        sol = [beat("B1", "solution", "BATHROOM", 6), beat("B2", "solution", "BATHROOM", 2), beat("B3", "solution", "SUITE", 9)]
        out = SS.fold(hook + sol)
        self.assertEqual([s["id"] for s in out], ["A1", "B1"])
        self.assertEqual(out[0]["take"], "continuous")
        self.assertEqual(out[1]["folded_from"], ["B1", "B2", "B3"])
        self.assertEqual(out[1]["motion"], {"copies": ["KB1", "KB2", "KB3"]})

    def test_the_same_place_carries_on_across_a_section_change(self):
        out = SS.fold([beat("C1", "identification", "SUITE", 2), beat("C2", "problem", "SUITE", 5)])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["section"], "identification")
        self.assertEqual(out[0]["sections"], ["identification", "problem"])

    def test_the_hook_never_joins_the_body(self):
        out = SS.fold([beat("H1", "hook", "TEAK RAIL", 4), beat("H2", "offer", "TEAK RAIL", 6), beat("H3", "offer", "TEAK RAIL", 6)])
        self.assertEqual([s.get("folded_from") or [s["id"]] for s in out], [["H1"], ["H2", "H3"]])

    def test_same_tag_scenes_join_into_one_scene_with_every_old_scene_whole_as_a_shot(self):
        """2026-11-16: consecutive scenes with the same section tag are one scene; nothing in them is dropped."""
        a = dict(beat("S1", "hook", "BATHROOM", 2), happens="he points", on_screen="LINE ONE")
        b = dict(beat("S2", "hook", "GREEN", 1), kind="greenscreen", happens="he gasps", on_screen="LINE TWO")
        c = dict(beat("S3", "problem", "BEACH", 40), happens="rubs his jaw")
        d = dict(beat("S4", "problem", "BATHROOM", 40), kind="card", on_screen="CARD")
        out = SS.join_sections([a, b, c, d])
        self.assertEqual([s["joined_from"] for s in out], [["S1", "S2"], ["S3", "S4"]])
        self.assertEqual([sh["id"] for sh in out[0]["shots"]], ["S1.1", "S1.2"])     # the old scenes' shots, in order
        self.assertEqual([sh["of_scene"] for sh in out[0]["shots"]], ["S1", "S2"])
        self.assertEqual(out[0]["shots"][1]["scene_master"], "S1.1")
        self.assertEqual([k["happens"] for k in out[0]["joined_scenes"]], ["he points", "he gasps"])   # nothing dropped
        self.assertIn("he points", out[0]["happens"]); self.assertIn("he gasps", out[0]["happens"])
        self.assertEqual(out[0]["on_screen"], "LINE ONE\nLINE TWO")
        self.assertEqual(out[0]["voice"], a["voice"] + " " + b["voice"])
        self.assertEqual(out[1]["kind"], "broll")                           # a card inside is a shot; the scene is filmed

    def test_unjoin_gives_back_the_scenes_as_written(self):
        scenes = [dict(beat("S1", "hook", "X", 2), happens="a"), dict(beat("S2", "hook", "Y", 2), happens="b"),
                  beat("S3", "offer", "X", 2)]
        self.assertEqual(SS.unjoin(SS.join_sections(scenes)), scenes)

    def test_cues_that_named_an_old_scene_point_at_the_joined_scene(self):
        doc = {"scenes": SS.join_sections([beat("S2", "problem", "X", 2), beat("S3", "problem", "X", 2)]),
               "sfx": [{"scene": "S3", "what": "thud"}, {"scene": "S2", "what": "hiss"}],
               "hooks": [{"opener_scene": "S2"}], "music": {"scenes": ["S2", "S3"]}}
        self.assertTrue(SS.repoint(doc))
        self.assertEqual(doc["sfx"][0], {"scene": "S2", "was_scene": "S3", "shot_in_scene": "S2.2", "what": "thud"})
        self.assertEqual(doc["sfx"][1], {"scene": "S2", "was_scene": "S2", "shot_in_scene": "S2.1", "what": "hiss"})
        self.assertEqual(doc["music"]["scenes"], ["S2"])
        self.assertEqual(SS.repoint(doc), 0)

    def test_a_joined_brief_reads_as_the_brief_as_written(self):
        import json
        import tempfile
        before_doc = {"scenes": [beat("S1", "hook", "X", 2), beat("S2", "problem", "X", 2), beat("S3", "problem", "Y", 2)],
                      "sfx": [{"scene": "S3", "what": "thud"}], "music": {"scenes": ["S2", "S3"]}}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "5-brief.md"
            before = "# Brief\n\nwords\n\n```json\n" + json.dumps(before_doc) + "\n```\n\nafter\n"
            p.write_text(before)
            SS.fold_file(p)
            now = p.read_text()
            self.assertNotEqual(now, before)
            self.assertTrue(SS.same_as_written(now, before))
            self.assertFalse(SS.same_as_written(now.replace("after", "edited"), before))     # any other edit counts
            self.assertFalse(SS.same_as_written(now.replace('"thud"', '"bang"'), before))

    def test_a_caption_that_runs_on_is_said_once(self):
        a = dict(beat("S1", "hook", "X", 2), on_screen="DAMN BRO")
        b = dict(beat("S2", "hook", "X", 2), on_screen="DAMN BRO")
        c = dict(beat("S3", "hook", "X", 2), on_screen="nothing")
        self.assertEqual(SS.join_sections([a, b, c])[0]["on_screen"], "DAMN BRO")

    def test_links_into_a_joined_scene_follow_it(self):
        """The test session's list (16 Nov): start frames, make-list shots, transitions, hook openers, beat ids."""
        a = dict(beat("S1", "hook", "X", 2), first_frame={"subject": "one"}, beats=[{"id": "B1", "shot": "S1.1"}])
        b = dict(beat("S2", "hook", "X", 2), first_frame={"subject": "two"}, beats=[{"id": "B1", "shot": "S2.1"}])
        b["shots"][0]["start_picture"] = "first_frame"
        doc = {"scenes": SS.join_sections([a, b]),
               "piece": {"make_list": [{"shot": "S2.1", "picture": "first_frame"}]},
               "layers": {"transitions": [{"after_scene": "S2"}]}, "hooks": [{"opener_scene": "S1"}]}
        SS.repoint(doc)
        s = doc["scenes"][0]
        self.assertEqual(s["shots"][1]["first_frame"], {"subject": "two"})        # its own frame, not shot 1's
        self.assertEqual(doc["piece"]["make_list"][0]["shot"], "S1.2")
        self.assertEqual((doc["layers"]["transitions"][0]["after_scene"], doc["layers"]["transitions"][0]["shot_in_scene"]), ("S1", "S1.2"))
        self.assertEqual(doc["hooks"][0]["shot_in_scene"], "S1.1")               # a hook version swaps shot 1 only
        self.assertEqual([x["id"] for x in s["beats"]], ["B1", "B2"])
        self.assertEqual([x["shot"] for x in s["beats"]], ["S1.1", "S1.2"])
        back = SS.as_written(doc)
        self.assertEqual(back["scenes"], [a, b])
        self.assertEqual(back["piece"]["make_list"][0]["shot"], "S2.1")
        self.assertEqual(back["layers"]["transitions"][0], {"after_scene": "S2"})

    def test_every_shot_names_its_subjects_from_the_brief(self):
        a = dict(beat("S1", "hook", "TABLETOP", 2), who="HANDS (DARIUS)", looks={"DARIUS": "white tee"}, props=["glass of water"])
        b = dict(beat("S2", "hook", "TABLETOP", 2), who="DARIUS", props=[])
        doc = {"cast": [{"id": "DARIUS", "identity_block": "early 30s, deep brown skin"}],
               "world": [{"id": "TABLETOP", "description": "a light wood table", "light": "window light"}],
               "props": [{"name": "glass of water", "size": "10 cm", "look": "clear"}],
               "product_lock": ["S1 · S1.1: the FLEX upright on the table", "S2 · S2.1: the FLEX in his left hand"],
               "scenes": SS.join_sections([a, b])}
        SS.repoint(doc)
        self.assertEqual(SS.define_subjects(doc), 2)
        s1, s2 = doc["scenes"][0]["shots"]
        self.assertEqual(s1["subjects"]["people"], [{"id": "DARIUS", "is": "early 30s, deep brown skin", "look": "white tee"}])
        self.assertEqual(s1["subjects"]["product"]["in_shot"], ["S1 · S1.1: the FLEX upright on the table"])
        self.assertEqual(s2["subjects"]["product"]["in_shot"], ["S2 · S2.1: the FLEX in his left hand"])   # its own shot's line
        self.assertEqual(s1["subjects"]["place"]["id"], "TABLETOP")
        self.assertEqual(s1["subjects"]["props"][0]["size"], "10 cm")
        self.assertNotIn("props", s2["subjects"])
        self.assertEqual(SS.as_written(doc)["scenes"], [a, b])                  # derived, never part of the brief as written

    def test_the_product_comes_from_the_bank_on_every_shot_that_shows_it(self):
        bank = {"id": "acme-brush", "name": "ACME™ Brush", "bank": "brands/acme/products/brush.md",
                "refs": ["runs/ai-elements/acme/products/acme-brush/model/reference-front.png"], "words": ["brush"]}
        a = dict(beat("S1", "hook", "X", 2), happens="he switches the brush on")
        b = dict(beat("S2", "problem", "X", 2), happens="he stares at the mirror")
        doc = {"scenes": [a, b]}
        SS.define_subjects(doc, bank)
        p = doc["scenes"][0]["shots"][0]["subjects"]["product"]
        self.assertEqual((p["id"], p["bank"], p["in_shot"]), ("acme-brush", "brands/acme/products/brush.md", []))
        self.assertNotIn("words", p)
        self.assertNotIn("subjects", doc["scenes"][1]["shots"][0])          # a shot without the product names none

    def test_product_subject_reads_the_real_bank(self):
        repo = SS._repo(__file__)
        if not repo:
            self.skipTest("no workspace around this checkout")
        sys.path.insert(0, str(repo / "components" / "naming"))
        import names
        import products as PR
        found = [(b, pid) for b in PR.brands(repo) for pid in names.product_ids(b)[:1]]
        if not found:
            self.skipTest("no product bank in this checkout")
        brand, pid = found[0]
        p = SS.product_subject(brand, pid, repo)
        self.assertEqual(p["id"], pid)                                          # brands are discovered, never named
        if p.get("bank"):
            self.assertTrue(p["bank"].startswith("brands/%s/products/" % brand))
        self.assertTrue(all(not r.startswith("/") for r in p.get("refs") or []))   # repo-relative only
        self.assertTrue(all(d["label"].startswith("Shared Assets/") and d["drive_id"] for d in p.get("drive") or []))

    def test_a_different_tag_in_between_keeps_them_apart(self):
        out = SS.join_sections([beat("A", "problem", "X", 2), beat("B", "agitation", "X", 2), beat("C", "problem", "X", 2)])
        self.assertEqual(len(out), 3)

    def test_fold_file_writes_once_and_keeps_the_brief_before(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "5-brief.md"
            doc = {"scenes": [beat("A1", "hook", "BATHROOM", 4), beat("A2", "hook", "BATHROOM", 3)]}
            p.write_text("# Brief\n\n```json\n" + json.dumps(doc) + "\n```\n")
            self.assertEqual(SS.fold_file(p), (2, 1))
            self.assertTrue((Path(d) / "5-brief.before-fold.md").is_file())
            self.assertTrue(p.read_text().startswith("# Brief"))
            self.assertEqual(SS.fold_file(p), (1, 1))                 # already folded: untouched

    def test_rooms_of_one_place_carry_on(self):
        out = SS.fold([beat("G1", "proof", "HOTEL BATHROOM", 5), beat("G2", "solution", "HOTEL SUITE", 5)])
        self.assertEqual(len(out), 1)

    def test_a_new_section_in_a_new_place_starts_a_new_scene(self):
        out = SS.fold([beat("D1", "proof", "AIRPLANE", 5), beat("D2", "failed-solutions", "HOME", 5)])
        self.assertEqual([s["id"] for s in out], ["D1", "D2"])

    def test_a_generation_stops_at_30_seconds(self):
        out = SS.fold([beat("E%d" % i, "agitation", "PLACE%d" % i, 9) for i in range(1, 5)])
        self.assertEqual([s.get("folded_from") or [s["id"]] for s in out], [["E1", "E2", "E3"], ["E4"]])

    def test_a_3d_cutaway_is_its_own_scene(self):
        out = SS.fold([beat("F1", "unique-mechanism", "HOME BATHROOM", 4), beat("F2", "unique-mechanism", "3D SKIN", 4),
                       beat("F3", "unique-mechanism", "HOME BATHROOM", 4)])
        self.assertEqual([s["id"] for s in out], ["F1", "F2", "F3"])

    def test_a_brief_already_in_sequences_passes(self):
        self.assertEqual(SS.check(SS.fold(self.scenes)), [])


if __name__ == "__main__":
    unittest.main()
