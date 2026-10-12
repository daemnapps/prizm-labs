"""The storyboard (2026-10-01): the brief's scenes grouped into the swipe's own
sections from its frame map, every layer laid out, and the swipe carried shot by
shot. A made-up two-person demo, no video, no model, no network."""
import json, tempfile, unittest
from pathlib import Path
import storyboard_plan as sp

TEAR = """**1. THE OBJECTIVE RECORD**

| Timestamp | Roll | Section | Visuals | On-Screen Text | Transcript | Sound | Layers |
|---|---|---|---|---|---|---|---|
| 0:00 - 0:04 | A · opener: true | hook | Who: Host · talking to the lens | BIG LINE | Host: hello there friends | music: none / effects: none / room: street | lower third: none / transition out: none |
| 0:04 - 0:10 | B-over | demo | Who: Host and Helper (hands) | none | Helper: we press it right here | music: none / effects: none / room: quiet | transition out: none |
| 0:10 - 0:11 | C | offer | Who: None · a price graphic | Cost: $10 | [music] | music: none / effects: chime / room: none | transition out: none |
"""
TR = [{"id": "T1", "speaker": "S1", "start": 0.2, "end": 3.8, "text": "hello there friends"},
      {"id": "T2", "speaker": "S2", "start": 4.2, "end": 9.5, "text": "we press it right here and hold"}]


def shot(i, a, b, who, held, height="eye level", on=None, frame=""):
    return {"id": f"K{i:02d}", "start": a, "end": b, "seconds": b - a,
            "stills": {"first": f"K{i:02d}-first.jpg", "last": f"K{i:02d}-last.jpg"},
            "map": {"who": who, "camera": {"held": held, "height": height}, "start_frame": frame,
                    "moments": [{"t": 0.1, "who": who[0] if who else "", "does": "moves"}], "on_screen": on or []}}


FM = {"seconds": 11.0, "cuts": [4.0, 7.0, 8.0, 10.0], "shots": [
    shot(1, 0.0, 4.0, ["Host (face)"], "handheld at arm's length"),
    shot(2, 4.0, 7.0, ["Host (face)", "Helper (right hand)"], "set down still",
         frame="Helper's right hand enters from top right edge"),
    shot(3, 7.0, 8.0, ["Host (hands only)"], "handheld", "above",
         on=[{"text": "THE STEP", "where": "center"}]),
    shot(4, 8.0, 10.0, ["Host (face)", "Helper (right hand)"], "set down still"),
    shot(5, 10.0, 11.0, [], "screen graphic", on=[{"text": "Cost: $10", "where": "center"}]),
]}


def brief(inserted=False, edge="top right"):
    scenes = [
        {"id": "S1", "kind": "talking", "to_camera": True, "who": "HOST", "speaker": "HOST", "setting_id": "STREET",
         "voice": "hello there my friends", "looks": {"HOST": "look-1"}, "source": "K01: host talks to the lens",
         "first_frame": {"subject": "HOST talking", "composition": "HOST centred"}, "last_frame": {"change": "smiles"}},
        {"id": "S2", "kind": "broll", "who": "HELPER's hand", "speaker": "HELPER", "setting_id": "ROOM",
         "voice": "we press it right here and hold", "looks": {"HOST": "look-1", "HELPER": "look-1"},
         "source": "K02, K04: the hand presses", "first_frame": {"subject": "HOST seated", "composition":
         f"HOST centred; HELPER's right hand enters from the {edge} edge"}, "last_frame": {"change": "hand lifts"}},
        {"id": "S3", "kind": "card", "who": None, "card": {"lines": ["Cost: $12"]}, "source": "K05: the price graphic"},
    ]
    if inserted:
        scenes.insert(2, {"id": "S2b", "kind": "broll", "who": "HOST's hands", "setting_id": "ROOM", "source": "K03: hands hold a phone",
                          "on_screen": "THE STEP", "looks": {"HOST": "look-1"},
                          "first_frame": {"subject": "hands hold a phone", "composition": "phone centred"}})
    doc = {"cast": [{"id": "HOST"}, {"id": "HELPER"}], "world": [{"id": "STREET"}, {"id": "ROOM"}],
           "roll_sheet": [{"row": "0:10 · [shows: price graphic]", "scene": "S3"}],
           "layers": {"hook": {"text": "BIG LINE"}}, "scenes": scenes}
    return "x\n```json\n" + json.dumps(doc) + "\n```\n"


class Storyboard(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        (self.t / "stages").mkdir()
        (self.t / "framemap").mkdir()
        (self.t / "stages" / "1-teardown.md").write_text(TEAR)
        (self.t / "transcript.json").write_text(json.dumps(TR))
        (self.t / "framemap" / "framemap.json").write_text(json.dumps(FM))

    def plan(self, **kw):
        b = self.t / "brief.md"
        b.write_text(brief(**kw))
        return sp.build(None, self.t, b), b

    def test_sections_follow_the_swipe_and_a_card_stands_alone(self):
        p, _ = self.plan()
        got = [(g["scenes"], g["maker"]) for g in p["sections"]]
        self.assertEqual(got[0], (["S1"], "lip-sync"))
        self.assertEqual(got[1][1], "motion transfer")
        self.assertEqual(got[-1], (["S3"], "plate"))
        self.assertEqual([k["id"] for k in p["sections"][1]["swipe"]["shots"]], ["K02", "K04"])   # K03, the insert, is not cited here

    def test_a_dropped_insert_and_its_words_are_found(self):
        f = [x["finding"] for x in sp.swipe_carry(self.plan()[1], self.t)]
        self.assertTrue(any("insert at 7.0" in x for x in f), f)
        self.assertEqual(len(f), 2, f)
        self.assertTrue(any('"THE STEP"' in x for x in f), f)

    def test_a_carried_insert_passes(self):
        f = [x["finding"] for x in sp.swipe_carry(self.plan(inserted=True)[1], self.t)]
        self.assertFalse(any("insert" in x or "THE STEP" in x for x in f), f)

    def test_an_arm_from_another_edge_is_found(self):
        f = [x["finding"] for x in sp.swipe_carry(self.plan(edge="left")[1], self.t)]
        self.assertTrue(any("enter from the left edge" in x for x in f), f)

    def test_words_never_in_a_picture_and_layers_exist(self):
        p, _ = self.plan()
        self.assertEqual(p["layers"]["text"][0]["kind"], "hook headline")
        self.assertTrue(any(x["what"] == "chime" for x in p["layers"]["sfx"]))
        self.assertEqual(p["sections"][1]["frames"][0]["what"], "start frame · set-up shot")



class SwipeCamera(unittest.TestCase):
    """THE RECIPE (2026-10-02): the blurred swipe shot first on the ruled still door, the written framing dropped."""

    def test_blurred_swipe_shot_goes_in_first(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            shots = Path(d) / "framemap" / "shots"; shots.mkdir(parents=True)
            Image.new("RGB", (360, 640), (200, 180, 160)).save(shots / "K02-first.jpg")
            plan = {"teardown": str(Path(d).resolve())}
            cam = sp.swipe_camera_ref(plan, "K02")
            self.assertTrue(cam.endswith("K02-camera.jpg") and Path(cam).is_file())
            it = {"id": "S2-F1", "params": {"prompt": "NOVA seated. Close-up, centred: NOVA at 20-80% width."},
                  "medias": [{"role": "image_references", "value": f"r{i}"} for i in range(5)]
                            + [{"role": "image_references", "value": "/b/sets/room/plate.png"}]}
            out = sp.with_swipe_camera(it, cam, "K02", composition="Close-up, centred: NOVA at 20-80% width")
            refs = [m["value"] for m in out["medias"] if m["role"] == "image_references"]
            self.assertEqual(len(refs), 5)            # never past the ruled door's five
            self.assertEqual(refs[0], cam)            # first, and never the one dropped
            self.assertEqual(refs[1:], ["r0", "r1", "r2", "r3"])
            self.assertIn("FIRST reference image is the swipe shot", out["params"]["prompt"])
            self.assertNotIn("20-80% width", out["params"]["prompt"])   # the frame sets the framing
            self.assertNotIn("swipe_guide", out)                        # no side route: the ruled still door makes it
            self.assertEqual(sp.with_swipe_camera(out, cam, "K02")["medias"], out["medias"])  # once only

    def test_no_teardown_no_reference(self):
        self.assertIsNone(sp.swipe_camera_ref({}, "K02"))


class ModelLock(unittest.TestCase):
    """A picture made on any model but the ruled one stops the run (2026-10-02)."""

    def test_unruled_model_stops(self):
        import importlib.util as u
        sp_ = u.spec_from_file_location("vp_run", Path(__file__).resolve().parent / "run.py")
        r = u.module_from_spec(sp_); sp_.loader.exec_module(r)
        reg = {"doors": {"still": {"model": "gpt-image-2.5-sunburst", "ruled": "2026-09-18"}}}
        r.ruled_model(reg, "still", "gpt-image-2.5-sunburst")          # the ruled one passes
        with self.assertRaises(SystemExit):
            r.ruled_model(reg, "still", "gemini-3-pro-image")           # anything else stops


class NoHandOffsForPeople(unittest.TestCase):
    """the owner, 2026-10-03 (providers.json ruling_2026_10_03_no_handoffs): a section with a person
    starts every clip, and the section itself, from its approved picture — never a last frame."""
    PERSON = {"roll": "A", "elements": ["person · LEAD · look-1"], "scenes": ["S1", "S2"],
              "voice": {"S1": 9.0, "S2": 9.0}}
    NOBODY = {"roll": "B-over", "elements": ["set · SINK"], "scenes": ["S1", "S2"], "voice": {"S1": 9.0, "S2": 9.0}}

    def test_clips_of_a_person_section_all_start_from_the_picture(self):
        cs = sp.clips_of(self.PERSON)
        self.assertGreater(len(cs), 1)
        self.assertTrue(all(c["starts_from"] == "the section's start picture" for c in cs))
        cs = sp.clips_of(self.NOBODY)
        self.assertEqual(cs[1]["starts_from"], "the real last frame of the clip before")

    def test_frame_control_never_chains_a_person_from_the_section_before(self):
        self.assertNotIn("last frame of the section before", sp.frame_chain(self.PERSON))
        self.assertIn("approved picture", sp.frame_chain(self.PERSON))
        self.assertEqual(sp.frame_chain(self.NOBODY), "start from the real last frame of the section before")
        self.assertEqual(sp.frame_chain({"roll": "C", "elements": []}), "hard cut")

if __name__ == "__main__":
    unittest.main()
