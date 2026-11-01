#!/usr/bin/env python3
"""The email picture chain (design/picture_chain.py, 2026-10-29): email pictures made the way picture ads are.

    python3 design/test_picture_chain.py

  1  quoted words are lifted out of the brief, each with the panel its sentence names; the brief keeps a clear space
  2  a quoted word inside a sentence is not words to set
  3  a product at rest with no kept 3D set is held, its set request written, and nothing is generated
  4  a product at rest with a kept print naming the picture is made FROM the print: nothing generated, words set on top
  5  a product in a hand is one plain picture with its kit, the concept in the recipe, no words drawn
  6  the in-use test reads the scene, never the words lifted out of it ("ON HIS FACE")
  7  a product named with no kit is held, never drawn from words
  8  line.make_pictures sends every todo slot through the chain; a held picture stays a todo with why
  9  simple_email.make_pictures sends the hero through the chain; a held offer is left out

Offline: the image engine (plain, product3d, words) is a fake; the workspace is a temp folder.
"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import picture_chain as C  # noqa: E402

BRIEF = ('A two-panel card. LEFT PANEL, label in caps, exact words: "WHAT HE SAID" — below it a plain tube. RIGHT PANEL, '
         'same label type, exact words: "WHAT\'S ACTUALLY ON HIS FACE" — below it two labels, exact words "THE BUMPS" and '
         '"THE MARKS THEY LEAVE". Under the right panel, the real CRUSH lands upright on a gold plinth.')


class Fakes:
    def __init__(self, repo):
        self.repo, self.made, self.words = repo, [], []

    def modules(self):
        repo = self

        def find_kit(brand, slug):
            k = repo.repo / "runs" / "ai-elements" / brand / "products" / slug
            return k if (k / "kit.json").is_file() else None

        def plan(brand, text, products=(), sections=(), rules_lines=()):
            return {"prompt": text, "refs": [], "products": list(products)}

        def make(brand, text, out, products=(), aspect="9:16", recipe=None, sections=(), rules_lines=()):
            repo.made.append({"text": text, "products": list(products), "recipe": recipe, "rules": list(rules_lines),
                              "sections": list(sections), "aspect": aspect})
            from PIL import Image
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (90, 160), "black").save(out)
            return {"file": str(out), "prompt": text, "refs": ["sheet.png"], "model": "fake"}

        def set_on_top(picture, layer, out=None, plate=None):
            repo.words.append(layer)
            shutil.copy(picture, plate)
            return {"ok": True, "plate": str(plate), "elements": len(layer["elements"])}
        return (types.SimpleNamespace(plan=plan, make=make), types.SimpleNamespace(find_kit=find_kit),
                types.SimpleNamespace(set_on_top=set_on_top))


class Chain(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="picture-chain-")).resolve()
        kit = self.tmp / "runs" / "ai-elements" / "testbrand" / "products" / "crush-tube"
        (kit / "model").mkdir(parents=True)
        (kit / "kit.json").write_text(json.dumps({"aliases": ["crush"], "size_cm": {"height": 15}}))
        (kit / "model" / "product-sheet.png").write_bytes(b"sheet")
        self.fakes = Fakes(self.tmp)
        self.p = [mock.patch.object(C, "REPO", self.tmp), mock.patch.object(C, "_image_production", self.fakes.modules),
                  mock.patch.object(C, "_picture_sets", lambda: None)]
        for p in self.p:
            p.start()
        self.run = self.tmp / "runs" / "email-production" / "testbrand" / "testbrand-nov-02"
        (self.run / "media").mkdir(parents=True)

    def tearDown(self):
        for p in self.p:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_words_lifted_with_their_panel(self):
        clean, words = C.lift_words(BRIEF)
        self.assertEqual([w["text"] for w in words], ["WHAT HE SAID", "WHAT'S ACTUALLY ON HIS FACE", "THE BUMPS", "THE MARKS THEY LEAVE"])
        self.assertEqual([w["side"] for w in words], ["left", "right", "right", "right"])
        for w in words:
            self.assertNotIn(w["text"], clean)
        self.assertIn(C.CLEAR, clean)

    def test_2_a_quoted_word_in_a_sentence_stays(self):
        clean, words = C.lift_words('the "real" tube on a shelf')
        self.assertEqual(words, [])
        self.assertIn('"real"', clean)

    def test_3_at_rest_without_a_set_is_held_and_nothing_made(self):
        got = C.make("testbrand", {"brief": BRIEF, "use": "key-visual"}, "lbl", self.run / "media" / "lbl.png",
                     "the concept", "the culture", run_dir=self.run)
        self.assertEqual(got["route"], "set")
        self.assertIn("3D set", got["held"])
        self.assertEqual(self.fakes.made, [])
        req = json.loads((self.run / "media" / "sets" / "lbl.json").read_text())
        self.assertEqual(req["products"][0]["kit"], "crush-tube")
        self.assertEqual(req["words_space"][0], "WHAT HE SAID")
        self.assertFalse((self.run / "media" / "lbl.png").exists())

    def test_4_a_kept_print_is_the_picture(self):
        from PIL import Image
        d = self.tmp / "runs" / "image-production" / "testbrand" / "sets" / "card"
        d.mkdir(parents=True)
        Image.new("RGB", (90, 160), "green").save(d / "print-v1.png")
        (d / "set.json").write_text(json.dumps({"runs": ["lbl"], "prints": [{"file": "print-v1.png", "note": "kept: ok"}]}))
        got = C.make("testbrand", {"brief": BRIEF}, "lbl", self.run / "media" / "lbl.png", tokens={"ink": "#FFF"})
        self.assertEqual(got["made_by"], "picture-set")
        self.assertEqual(self.fakes.made, [])                       # nothing generated
        im = Image.open(self.run / "media" / "lbl.png")
        self.assertAlmostEqual(im.size[0] / im.size[1], 0.8, places=2)     # the 4:5 safe zone
        self.assertEqual(len(self.fakes.words[0]["elements"]), 4)          # the words set on top
        self.assertTrue(Path(got["plate"]).is_file())

    def test_5_in_hand_is_one_plain_picture_with_its_kit(self):
        got = C.make("testbrand", {"todo": "CRUSH held in a hand by the sink"}, "lbl", self.run / "media" / "lbl.png",
                     "the concept", None)
        self.assertEqual(got["route"], "plain")
        call = self.fakes.made[0]
        self.assertEqual(call["products"], ["crush-tube"])
        self.assertEqual(call["aspect"], "9:16")
        # the concept rides in the recipe, marked as the world and never drawn (brand-b nov-06, 2026-10-30: unmarked, a
        # tile drew the whole email's concept: the woman, the swatches, the smear and the turmeric in one picture)
        self.assertIn("the concept", call["recipe"]["concept"])
        self.assertTrue(call["recipe"]["concept"].startswith(C.CONCEPT_MARK), call["recipe"]["concept"])
        self.assertIn("na", call["recipe"]["culture"])
        self.assertTrue(any("No words" in r for r in call["rules"]))
        self.assertEqual(self.fakes.words, [])

    def test_5b_one_photograph_never_the_emails_other_parts_and_its_own_frame(self):
        # brand-b nov-05, 2026-10-30: the hero drew the concept's three message cards and the next section's tube
        C.make("testbrand", {"todo": "a woman at her kitchen table reading her phone"}, "lbl", self.run / "media" / "lbl.png",
               "the inbox as three message cards, then the tube in its mound", None, aspect="4:5")
        call = self.fakes.made[0]
        head = call["sections"][0][0]
        self.assertIn("only THE PICTURE", head)
        for part in ("cards", "screens", "another section"):
            self.assertIn(part, head)
        self.assertEqual(call["aspect"], "4:5")
        self.assertTrue(call["recipe"]["frame"].startswith("4:5"), call["recipe"]["frame"])
        self.assertNotIn("9:16", call["recipe"]["frame"])

    def test_5c_markdown_in_the_concept_or_culture_never_reaches_the_model(self):
        # brand-a nov-05/06/07, 2026-10-30: culture quoted the culture map's "**Barbershop as debate floor.**" and
        # model-inputs refused every picture of those emails ("brief notes the model would draw: markdown bold")
        C.make("testbrand", {"todo": "a barber's chair, empty"}, "lbl", self.run / "media" / "lbl.png",
               "the **barbershop** as a `debate` floor", 'Culture map: "**Barbershop as debate floor.** (1) **Formats**"')
        call = self.fakes.made[0]
        sent = json.dumps([call["sections"], call["recipe"]])
        self.assertNotIn("**", sent)
        self.assertNotIn("`", sent)
        self.assertIn("Barbershop as debate floor.", sent)

    def test_6_in_use_reads_the_scene_not_the_words(self):
        self.assertEqual(C.plan("testbrand", {"brief": BRIEF}, "lbl")["route"], "set")

    def test_7_a_named_product_with_no_kit_is_held(self):
        got = C.make("testbrand", {"todo": "the gift set on a table", "product": "the-gift-set"}, "lbl",
                     self.run / "media" / "lbl.png")
        self.assertIn("no product casting sheet for the-gift-set", got["held"])
        self.assertEqual(self.fakes.made, [])

    def test_8_line_sends_todo_slots_through_the_chain(self):
        import line as LINE
        import picture_record as PR
        (self.run / "design").mkdir()
        (self.run / "design" / "email.json").write_text(json.dumps({"sections": [
            {"todo": "CRUSH held in a hand", "brief": "", "use": "story"},
            {"todo": "CRUSH on a gold plinth", "brief": "", "use": "key-visual"}]}))
        with mock.patch.object(PR, "mirror", lambda *a: ("api", [], "")), contextlib.redirect_stdout(io.StringIO()):
            LINE.make_pictures("testbrand", self.run, {"tokens": {}})
        spec = json.loads((self.run / "design" / "email.json").read_text())
        self.assertEqual(spec["sections"][0]["route"], "plain")
        self.assertTrue(spec["sections"][0]["photo"].startswith("run:media/"))
        self.assertIn("todo", spec["sections"][1])
        self.assertIn("3D set", spec["sections"][1]["held"])
        rec = json.loads((self.run / spec["sections"][0]["record"]).read_text())
        self.assertEqual(rec["chain"]["route"], "plain")

    def test_9_simple_email_goes_through_the_chain(self):
        import simple_email as S
        email = {"hero": {"prompt": "CRUSH held in a hand"}, "offer": {"image": {"prompt": "a gift set", "product": "the-gift-set"}}}
        with mock.patch.object(S, "web_copy", lambda p: p), contextlib.redirect_stdout(io.StringIO()):
            made = S.make_pictures(email, "testbrand", self.run / "media", self.run)
        self.assertEqual(list(made), ["hero"])
        self.assertFalse(hasattr(S, "openai_door"))
        self.assertIn("held", json.loads((self.run / "media" / "offer.chain.json").read_text()))


class Cast(unittest.TestCase):
    """A person in the picture brings the brand's own cast; nobody in it, or no asset found, brings nothing."""

    def test_a_person_in_the_picture_brings_the_brands_cast(self):
        import tempfile
        from unittest import mock
        C._image_production()
        from image_production import assets as AS
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            with mock.patch.object(AS, "pick", return_value=([{"path": f.name}, {"name": "no file"}], [])):
                refs, says = C.cast_refs("brand", "a man at the sink")
        self.assertEqual([str(r) for r in refs], [f.name])
        self.assertIn("keep the face", says[0])

    def test_an_unreadable_mount_never_stops_the_picture(self):
        from unittest import mock
        C._image_production()
        from image_production import assets as AS
        with mock.patch.object(AS, "pick", side_effect=OSError("away")):
            self.assertEqual(C.cast_refs("brand", "a man at the sink"), ([], {}))


if __name__ == "__main__":
    sys.path.append(str(HERE.parent))
    unittest.main(verbosity=1)
