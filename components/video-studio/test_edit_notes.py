"""The edit stage's reads: each spoken shot against its line, the brief's edit notes, the layers template."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edit_notes as EN  # noqa: E402
import layers as LY  # noqa: E402

ROWS = [{"scene": "S5", "id": "S5.1", "share": 0.5, "phrase": ""},
        {"scene": "S5", "id": "S5.2", "share": 0.5, "phrase": ""},
        {"scene": "S7", "id": "S7.1", "share": 1.0, "phrase": "It's called the thing."}]
LAYOUT = {"scenes": [{"scene": "S5", "start": 0.0, "end": 4.0}, {"scene": "S7", "start": 4.0, "end": 6.0}]}
WORDS = {"scene": "S5", "words": [{"w": "same", "start": 0.2, "end": 0.5}, {"w": "wash", "start": 0.6, "end": 1.0},
                                  {"w": "I", "start": 2.2, "end": 2.3}, {"w": "brush", "start": 2.4, "end": 2.9}]}

MD = """# x
## B-ROLL — what the argument shows

| Scene | From the swipe | Shows | Plays over (the exact words) |
|---|---|---|---|
| S5 | 0:14 · B-vo | THE MAN | "same wash I brush" |
| S2 | 0:02 · B-silent | a woman rolls her eyes | music, no words |

## CARDS — made at production as a plate

| Scene | From the swipe | The plate | The words, exactly | Lands on | Sound |
|---|---|---|---|---|---|
| S7 | 0:18 | plate | YOUR HANDS / ONLY CLEAN WHAT SHOWS | "x" | none |

## END CARD — the real product

| Scene | From the swipe | The plate | Offer lines, exactly | CTA | Guarantee |
|---|---|---|---|---|---|
| S9 | 0:40 | plate | (none) | Tap below | once |

Card words, centred: GET YOUR / THING / NOW!

## LAYERS AND SOUND — carried from the swipe

| Element | What it is | On which scene |
|---|---|---|
| Hook | none | — |
| Captions | uppercase, bold, white, black outline, no highlight, centred, 2–4 words at a time | S5–S17 |
| Music | mid energy, drops at 12s | all |
| SFX | typewriter (2.26s) · click (3.76s) · woosh (9.01s) · buzzer on "she's close" | S1 |
| Annotation | graphics float | S1 |
| Sections | S1 hook | all |

## ROLL SHEET CHECK
"""


def fake_frame(video, t, out):
    Path(out).write_text(str(t))
    return out


class Lines(unittest.TestCase):
    def setUp(self):
        self.B = Path(tempfile.mkdtemp())
        (self.B / "voice" / "continuous").mkdir(parents=True)
        (self.B / "voice" / "continuous" / "S5.words.json").write_text(json.dumps(WORDS))
        self.cut = self.B / "rough-cut-v3-sdr.mp4"
        self.cut.write_text("x")

    def test_slots_and_words(self):
        s = EN.slots(ROWS, LAYOUT)
        self.assertEqual([round(x["a"], 2) for x in s], [0.0, 2.0, 4.0])
        self.assertEqual(EN.line_of(s[0], WORDS), "same wash")
        self.assertEqual(EN.line_of(s[1], WORDS), "I brush")
        self.assertEqual(EN.line_of(s[2], {}), "It's called the thing.")
        w = {"words": [{"w": "It", "start": 0.1, "end": 0.2}, {"w": "has", "start": 0.3, "end": 0.4},
                       {"w": "ten.", "start": 2.1, "end": 2.3}, {"w": "Next.", "start": 3.0, "end": 3.2}]}
        self.assertEqual(EN.sentence_of(s[0], w), "It has ten.")

    def test_a_miss_names_the_shot_and_the_line_and_answers_are_kept(self):
        calls = []

        def ask(q, imgs):
            calls.append(q)
            if "\"I brush\"" in q:
                return {"fit": "contradicts", "sees": "a man washing his face with his hands", "missing": "a brush"}
            if "thing" in q:
                return {"fit": "related", "sees": "the product on a counter"}
            return {"fit": "shows", "sees": "ok"}
        rows = EN.line_check(self.B, self.cut, ROWS, LAYOUT, ask=ask, frame=fake_frame)
        by = {r["id"]: r for r in rows}
        self.assertIn("landed", by["line-S5.1"])
        self.assertIn("S5.2 contradicts its line", by["line-S5.2"]["open_why"])
        self.assertIn("landed", by["line-S7.1"])
        self.assertIn("I brush", by["line-S5.2"]["what"])
        self.assertEqual(EN.resolve(rows, {}), ["line-S5.2"])
        EN.line_check(self.B, self.cut, ROWS, LAYOUT, ask=ask, frame=fake_frame)
        self.assertEqual(len(calls), 3)                     # the second pass reads nothing again

    def test_unread_holds_and_a_record_never_overrides_a_miss(self):
        rows = EN.line_check(self.B, self.cut, ROWS, LAYOUT, ask=lambda q, i: None, frame=fake_frame)
        self.assertTrue(all("could not be read" in r["open_why"] for r in rows))
        ids = EN.resolve(rows, {"line-S5.1": {"landed": "looks fine"}, "line-S5.2": {"reason": "owner kept it"}})
        self.assertEqual(ids, ["line-S5.1", "line-S7.1"])


class Notes(unittest.TestCase):
    def setUp(self):
        self.B = Path(tempfile.mkdtemp())
        for sc, words in (("S7", "YOUR HANDS ONLY CLEAN THE SURFACE"), ("S9", "GET YOUR <b>THING</b> NOW!")):
            d = self.B / "scenes" / sc / "card"
            d.mkdir(parents=True)
            (d / "index.template.html").write_text("<div>%s</div>" % words)

    def notes(self, look=None, bed=None, lines=()):
        brief = {"captions": {"look": look}} if look else {}
        rows = EN.brief_notes(MD, brief, self.B, lines, bed, {"woosh": "whoosh"})
        return {r["id"]: r for r in rows}

    def test_every_note_is_a_row(self):
        n = self.notes()
        self.assertEqual(sorted(n), sorted(["note-broll-s5", "note-broll-s2", "note-card-s7", "note-endcard-s9",
                                            "note-layer-hook", "note-layer-captions", "note-layer-music", "note-layer-sfx",
                                            "note-layer-annotation", "note-layer-sections"]))

    def test_card_words_are_read_off_the_card(self):
        n = self.notes()
        self.assertIn("WHAT SHOWS", n["note-card-s7"]["open_why"])
        self.assertIn("landed", n["note-endcard-s9"])

    def test_captions_against_the_look(self):
        look = {"case": "upper", "weight": 700, "stroke_px": 0, "color": "#FFFFFF", "highlight": "#FFFFFF", "max_words": 3}
        self.assertIn("outline", self.notes(look)["note-layer-captions"]["open_why"])
        look["stroke_px"] = 6
        self.assertIn("landed", self.notes(look)["note-layer-captions"])

    def test_music_and_effects_against_the_bed(self):
        bed = {"from_swipe": True, "dropout": [12, 15], "effects": [{"name": "typewriter"}, {"name": "click"},
                                                                   {"name": "whoosh"}, {"file": "music/sfx-buzzer.mp3"}]}
        n = self.notes(bed=bed)
        self.assertIn("landed", n["note-layer-music"])
        self.assertIn("landed", n["note-layer-sfx"])
        n = self.notes(bed={"from_swipe": False, "effects": [{"name": "click"}]})
        self.assertIn("not made from the swipe", n["note-layer-music"]["open_why"])
        self.assertIn("buzzer", n["note-layer-sfx"]["open_why"])

    def test_broll_follows_the_line_check_and_the_rest_needs_a_record(self):
        lines = [{"id": "line-S5.1", "what": "S5.1 under same wash", "line": "same wash", "landed": "ok"},
                 {"id": "line-S5.2", "what": "S5.2 under I brush", "line": "I brush", "open_why": "no"},
                 {"id": "line-S6.4", "what": "", "line": "I brush. It's called", "landed": "ok"}]
        n = self.notes(lines=lines)
        self.assertIn("S5.2", n["note-broll-s5"]["open_why"])
        rows = list(n.values())
        left = EN.resolve(rows, {"note-broll-s2": {"reason": "the hook was reworked into four versions"}})
        self.assertNotIn("note-broll-s2", left)
        self.assertNotIn("note-layer-hook", left)           # "none": nothing to lay
        self.assertNotIn("note-layer-sections", left)       # the script's order
        self.assertIn("note-layer-annotation", left)        # needs a record


class Layers(unittest.TestCase):
    ROWS = [{"scene": "S1", "share": 0.5, "swipe_camera": "medium, eye level"},
            {"scene": "S1", "share": 0.25, "swipe_camera": "extreme close-up, eye level"},
            {"scene": "S1", "share": 0.25, "swipe_camera": "wide"}]

    def test_never_in_a_close_up(self):
        cu = LY.closeups(self.ROWS, "S1", 8.0)
        self.assertEqual(cu, [(4.0, 6.0)])
        got = LY.fit([{"picture": "a.png", "at": 1.0, "until": 7.0}, {"picture": "b.png", "at": 4.5, "until": None}], cu, 8.0)
        self.assertEqual((got[0]["at"], got[0]["until"]), (1.0, 4.0))
        self.assertEqual((got[1]["at"], got[1]["until"]), (6.0, 8.0))

    def test_build_places_and_checks_and_writes_once(self):
        B = Path(tempfile.mkdtemp())
        run = B / "props" / "pads"
        run.mkdir(parents=True)
        (run / "run.json").write_text("{}")
        (run / "pads-cut.png").write_bytes(b"png")
        drawn = B / "drawn.png"
        drawn.write_bytes(b"png")
        spec = {"props": [{"picture": str(run / "pads-cut.png"), "at": 1.0, "until": 3.0, "label": "pads"},
                          {"picture": str(drawn), "at": 6.5, "label": "drawn"}], "flash": [{"at": 2.4}]}
        step, rows = LY.build(B, "S1", spec, self.ROWS, 8.0)
        self.assertEqual(step["tool"], "hyperframes.card")
        self.assertEqual([r["ok"] for r in rows], [True, False])
        page = (B / "scenes" / "S1" / "card" / "index.template.html").read_text()
        self.assertIn("left:50%", page)
        self.assertIn("bottom:%dpx" % int(1920 * (1 - LY.FOOT)), page)
        self.assertIn("height:%dpx" % int(1920 * LY.HEIGHT), page)
        self.assertNotIn("bounce", page.lower())
        self.assertNotIn("elastic", page.lower())
        t = (B / "scenes" / "S1" / "card" / "index.template.html").stat().st_mtime
        time.sleep(0.02)
        LY.build(B, "S1", spec, self.ROWS, 8.0)
        self.assertEqual(t, (B / "scenes" / "S1" / "card" / "index.template.html").stat().st_mtime)


class PlacedEffects(unittest.TestCase):
    def test_an_effect_with_its_own_record_is_never_laid_twice(self):
        import edit_stage as ES
        moves = [{"id": "sfx-7", "kind": "sfx", "ours": 9.0, "sound": "whoosh", "what": "woosh", "swipe_at": 9.01}]
        bed = {"effects": [{"at": 10.34, "sound": "whoosh"}]}
        self.assertEqual(ES.lay_sfx(moves, bed, {"whoosh": "/x.mp3"}, skip={"sfx-7"}), [])
        self.assertEqual(len(bed["effects"]), 1)
        self.assertEqual(ES.lay_sfx(moves, bed, {"whoosh": "/x.mp3"}), ["sfx-7"])


if __name__ == "__main__":
    unittest.main()
