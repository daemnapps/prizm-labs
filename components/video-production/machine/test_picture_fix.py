"""The masked fix: the fault's region is cut out, edited alone from the picture's kept print, laid back; the rest of the
picture is unchanged pixel for pixel; a picture with no recorded print is refused."""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import picture_fix as PF


class MaskedFix(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp())
        (self.run / "media").mkdir()
        self.pic = self.run / "media" / "S1-F1.png"
        Image.new("RGB", (540, 960), (10, 20, 30)).save(self.pic)
        kp = self.run / "kept.png"; kp.write_bytes(b"k")
        (self.run / "brief.md").write_text("```json\n" + json.dumps({"cast": [], "scenes": []}) + "\n```\n")
        (self.run / "direct.json").write_text(json.dumps({"S1-F1": {"file": str(self.pic), "asked": {"prompt": "x"}}}))
        Path(str(self.pic) + ".print.json").write_text(json.dumps({"print": str(kp)}))
        self.kp = kp

    def gen(self, words, refs, out, **kw):
        self.seen = kw
        Image.new("RGB", Image.open(refs[0]).size, (250, 0, 0)).save(out)
        return {"file": str(out), "model": "m"}

    def test_only_the_region_changes_and_the_print_is_named(self):
        rec = PF.fix(self.run, "S1-F1", "make the hand right", generate=self.gen,
                     ask=lambda job, p, imgs: ('{"box": [0.6, 0.6, 0.7, 0.7]}', {}), ledger=lambda *a, **k: None)
        self.assertEqual(self.seen["from_print"], str(self.kp))
        img = Image.open(self.pic)
        self.assertEqual(img.getpixel((5, 5)), (10, 20, 30))               # outside the region: unchanged
        l, t, r, b = rec["box"]
        cx, cy = (l + r) // 2, (t + b) // 2
        self.assertGreater(img.getpixel((cx, cy))[0], 200)                  # inside: the edit
        self.assertAlmostEqual((r - l) / (b - t), 9 / 16, places=2)         # the picture's own shape
        self.assertEqual(json.loads((self.run / "direct.json").read_text())["S1-F1"]["fixed"][0]["version"], 1)

    def test_no_recorded_print_is_refused(self):
        Path(str(self.pic) + ".print.json").unlink()
        with self.assertRaises(SystemExit):
            PF.fix(self.run, "S1-F1", "x", generate=self.gen, ask=lambda *a: ("{}", {}))


class LocateAnswers(unittest.TestCase):
    def test_a_box_given_as_a_bare_list_or_a_list_of_answers_reads(self):
        a = PF.locate(None, "p.png", "x", ask=lambda *a: ("[0.1, 0.2, 0.3, 0.4]", {}))
        b = PF.locate(None, "p.png", "x", ask=lambda *a: ('[{"box": [0.1, 0.2, 0.3, 0.4]}]', {}))
        self.assertEqual(a, (0.1, 0.2, 0.3, 0.4)); self.assertEqual(b, a)

    def test_long_words_are_not_taken_for_a_file(self):
        import v2_checks as V
        V.fingerprint("m", "a" * 300 + "'s words", Path(__file__))


if __name__ == "__main__":
    unittest.main()
