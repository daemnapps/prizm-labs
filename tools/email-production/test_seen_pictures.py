#!/usr/bin/env python3
"""The layout offers only pictures someone has looked at, and a real picture's alt is what was seen in it
(the team, 2026-10-28). Before: product photos reached the layout as file names alone, and it wrote what it guessed
— "A Black man's jaw and neck in soft light, CRUSH™ in frame." for a white man's face with no product
(brand-a-nov-02--fed-up-king), "the WIDGET in its case on the shelf" for a man using the case as a hand mirror
(brand-a-nov-02--glow-up, a product the email does not sell). Those two cases are the fixtures here, with the
tags asset-index tag.py wrote for them on 2026-10-28.

    python3 tools/email-production/test_seen_pictures.py

  a  described_photos offers a tagged photo with what is in it (person, products shown); an untagged one is not
     offered and not in the refs validate accepts
  b  no tags at all -> no photo offered, with the line that says how to describe them
  c  true_alts: a photo's or a proof's alt becomes what was seen; a made or cut picture keeps its own
  d  proof_of offers no untagged proof, and says so when none is tagged
  e  validate holds a layout that picks an undescribed photo
No network, no key: the repo root is a temp folder and photos_of is stood in.
"""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE / "design"))              # APPEND — never insert at 0
try:
    import PIL                                     # noqa: F401
except ImportError:
    PIL = types.ModuleType("PIL")
    for _n in ("Image", "ImageDraw", "ImageFilter"):
        setattr(PIL, _n, types.ModuleType("PIL." + _n))
        sys.modules["PIL." + _n] = getattr(PIL, _n)
    sys.modules["PIL"] = PIL
import look as L                                   # noqa: E402
import line as LI                                  # noqa: E402

BRAND = "zz-brand"
FACE = "drive:brands/%s/products/crush-bump-eliminator/lifestyle/x_lifestyle_model-face.jpg" % BRAND
MIRROR = "drive:brands/%s/products/widget-charging-case/lifestyle/x_lifestyle_mirror.jpg" % BRAND
UNSEEN = "drive:brands/%s/products/widget-face-brush/lifestyle/x_lifestyle_in-hand-foam.jpg" % BRAND
TAGS = {
    "id-face": {"shot": "face-closeup", "people": "man 30-49", "skin_tone": "light", "products": [], "product_ok": None,
                "quality": 5, "baked_text": "none", "one_line": "Close-up of a man's face looking to the right.", "ref": FACE},
    "id-mirror": {"shot": "person-using-product", "people": "man 30-49", "skin_tone": "light",
                  "products": ["widget-charging-case"], "product_ok": True, "quality": 4, "baked_text": "none",
                  "one_line": "Man looking at his reflection in the mirror of the WIDGET Charging Case.", "ref": MIRROR},
}
GUESS_FACE = "A Black man's jaw and neck in soft light, CRUSH™ in frame."
GUESS_MIRROR = "A bathroom mirror shot: the WIDGET in its case on the shelf, a real customer at the sink."


def layout():
    """The two nov-02 picture slots as the layout wrote them (b4c0c3bb88), plus a made and a cut picture."""
    return {"sections": [
        {"s": "hero_photo", "headline": "h", "picture": {"photo": FACE, "alt": GUESS_FACE, "source": "photo"}},
        {"s": "photo_card", "title": "THE CHECK", "text": "t", "picture": {"photo": MIRROR, "alt": GUESS_MIRROR, "source": "photo"}},
        {"s": "example", "picture": {"proof": "p-1", "alt": "a guess", "source": "proof"}, "quote": "q", "who": "w", "ask": "a"},
        {"s": "picture", "picture": {"todo": "a razor on a jaw", "alt": "A razor on a jaw.", "source": "make"}},
        {"s": "product", "picture": {"stage": "product:crush", "alt": "The tube.", "source": "cut"}},
        {"s": "foot"}]}


class Seen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = mock.patch.object(LI, "REPO", self.root)
        self.patch.start()
        self.lk = L.Look(BRAND, {"products": {"crush": "repo:x.png"}})
        self.listed = mock.patch.object(LI, "photos_of", return_value=({FACE, MIRROR, UNSEEN}, "\n".join([FACE, MIRROR, UNSEEN])))
        self.listed.start()

    def tearDown(self):
        self.listed.stop()
        self.patch.stop()
        self.tmp.cleanup()

    def write(self, label, name, data):
        d = self.root / "runs" / "asset-index" / BRAND / label
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(json.dumps(data))

    def test_a_only_described_photos_offered(self):
        self.write("products", "tags.json", TAGS)
        refs, txt = LI.described_photos(self.lk)
        self.assertEqual(refs, {FACE, MIRROR})
        self.assertNotIn(UNSEEN, txt)
        face_line = next(l for l in txt.splitlines() if l.startswith(FACE))
        self.assertIn("no product", face_line)
        self.assertIn("Close-up of a man's face", face_line)
        mirror_line = next(l for l in txt.splitlines() if l.startswith(MIRROR))
        self.assertIn("shows widget-charging-case", mirror_line)

    def test_a2_photos_described_under_another_collection(self):
        self.write("products", "tags.json", {"id-face": TAGS["id-face"]})
        self.write("stills", "tags.json", {"id-mirror": TAGS["id-mirror"]})
        refs, _ = LI.described_photos(self.lk)
        self.assertEqual(refs, {FACE, MIRROR})

    def test_a3_accented_names_match(self):
        import unicodedata
        nfc = "drive:brands/%s/products/war/lifestyle/Ferrán-12.jpg" % BRAND        # as the index writes it
        nfd = unicodedata.normalize("NFD", nfc)                                        # as the mount lists it
        self.assertNotEqual(nfc, nfd)
        self.write("products", "tags.json", {"id-f": dict(TAGS["id-face"], ref=nfc, one_line="A man holding the wash.")})
        with mock.patch.object(LI, "photos_of", return_value=({nfd}, nfd)):
            refs, txt = LI.described_photos(self.lk)
        self.assertEqual(refs, {nfd})                  # the ref the layout is offered is the one that resolves
        spec = LI.true_alts({"sections": [{"s": "picture", "picture": {"photo": nfd, "alt": "a guess"}}]}, LI.seen_in(BRAND))
        self.assertEqual(spec["sections"][0]["picture"]["alt"], "A man holding the wash.")

    def test_b_no_tags_no_photos(self):
        refs, txt = LI.described_photos(self.lk)
        self.assertEqual(refs, set())
        self.assertIn("tag.py --label products", txt)

    def test_c_alt_is_what_was_seen(self):
        self.write("products", "tags.json", TAGS)
        self.write("proof", "tags.json", {"p-1": {"one_line": "Woman holding the tube in a bathroom."}})
        spec = LI.true_alts(layout(), LI.seen_in(BRAND))
        pics = [s["picture"] for s in spec["sections"] if "picture" in s]
        self.assertEqual(pics[0]["alt"], "Close-up of a man's face looking to the right.")
        self.assertNotIn("Black", pics[0]["alt"])
        self.assertNotIn("CRUSH", pics[0]["alt"])
        self.assertEqual(pics[1]["alt"], "Man looking at his reflection in the mirror of the WIDGET Charging Case.")
        self.assertEqual(pics[2]["alt"], "Woman holding the tube in a bathroom.")
        self.assertEqual(pics[3]["alt"], "A razor on a jaw.")      # a picture to make: its brief is its truth
        self.assertEqual(pics[4]["alt"], "The tube.")              # the real packshot cut-out

    def test_d_untagged_proof_not_offered(self):
        items = [{"id": "p-1", "media": "image", "kind": "review"}, {"id": "p-2", "media": "image", "kind": "before-after"}]
        self.write("proof", "proof.json", {"items": items})
        ids, txt = LI.proof_of(BRAND)
        self.assertEqual(ids, [])
        self.assertIn("no proof described yet", txt)
        self.write("proof", "tags.json", {"p-1": {"shot": "selfie-with-product", "quality": 4, "one_line": "Woman holding the tube."}})
        ids, txt = LI.proof_of(BRAND)
        self.assertEqual(ids, ["p-1"])
        self.assertNotIn("p-2", txt)

    def test_e_validate_holds_an_undescribed_photo(self):
        self.write("products", "tags.json", TAGS)
        refs, _ = LI.described_photos(self.lk)
        spec = {"sections": [{"s": "photo_card", "text": "t", "picture": {"photo": UNSEEN, "alt": "x", "source": "photo"}}, {"s": "foot"}]}
        with mock.patch.object(LI.EN, "sections", return_value=""):
            probs = LI.validate(spec, self.lk, set(), {}, refs)
        self.assertTrue(any("not one of the brand's own photos" in p for p in probs), probs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
