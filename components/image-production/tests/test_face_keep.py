"""Face-keeping covers: the video's own faces stay pixel for pixel; a changed face pixel or words over a face fail."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from image_production import face_keep as FK, covers as CV  # noqa: E402


def scene(path, shift=0, room=(40, 60, 90), face=(200, 150, 120)):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (360, 640), room)
    d = ImageDraw.Draw(im)
    for k in range(0, 360, 24):                               # a patterned room, so the ring around the face has detail
        d.line((k + shift, 0, k + shift, 640), fill=(room[0] + 30, room[1] + 20, room[2]), width=3)
    d.rectangle((140 + shift, 180 + shift, 220 + shift, 280 + shift), fill=face)
    d.ellipse((160 + shift, 210 + shift, 175 + shift, 225 + shift), fill=(20, 20, 20))
    im.save(path)
    return path


class FaceKeep(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.frame = scene(self.d / "frame.png")
        self.read = lambda p: [(140, 180, 220, 280)] if "frame" in str(p) else [(146, 186, 226, 286)]

    def test_the_frame_face_is_laid_back_exactly_where_the_model_put_the_person(self):
        cov = scene(self.d / "cover.png", shift=6, face=(90, 200, 90))      # the model moved and redrew the face
        rec = FK.keep(cov, self.frame, self.read)
        self.assertTrue(rec["pass"], rec)
        self.assertEqual(rec["faces"][0]["box"][0] - rec["faces"][0]["frame_box"][0], 6)
        out = FK.verify(cov, rec)
        self.assertTrue(out["verified"] and out["pass"])

    def test_a_changed_face_pixel_fails(self):
        cov = scene(self.d / "cover.png", shift=0, face=(90, 200, 90))
        rec = FK.keep(cov, self.frame, self.read)
        from PIL import Image
        im = Image.open(cov)
        x0, y0 = rec["faces"][0]["core"][:2]
        im.putpixel((x0 + 20, y0 + 20), (255, 0, 0))
        im.save(cov)
        out = FK.verify(cov, rec)
        self.assertFalse(out["pass"])
        self.assertIn("the video's faces were not kept", " ".join(CV.problems({"kept_faces": out})))

    def test_words_over_a_face_fail(self):
        cov = scene(self.d / "cover.png")
        rec = FK.keep(cov, self.frame, self.read)
        from PIL import Image, ImageDraw
        im = Image.open(cov)
        b = rec["faces"][0]["box"]
        ImageDraw.Draw(im).text((b[0] + 20, b[1] + 40), "HEADLINE", fill=(255, 255, 255))
        im.save(cov)
        self.assertFalse(FK.verify(cov, rec)["pass"])

    def test_a_person_the_model_lost_is_not_pasted(self):
        from PIL import Image
        cov = self.d / "cover.png"
        Image.new("RGB", (360, 640), (250, 250, 250)).save(cov)
        rec = FK.keep(cov, self.frame, lambda p: [(140, 180, 220, 280)] if "frame" in str(p) else [])
        self.assertFalse(rec["pass"])
        self.assertIn("lost or moved this person", rec["why"])
        far = FK.keep(cov, self.frame, lambda p: [(140, 180, 220, 280)] if "frame" in str(p) else [(10, 500, 90, 600)])
        self.assertFalse(far["pass"])


class OneType(unittest.TestCase):
    def test_a_band_moved_to_clear_kept_faces_is_still_one_type(self):
        style = {"face": "x", "size_px": 90, "zone": {"top": 58, "bottom": 80}}
        rows = [{"file": "a", "version": "a", "sha256": "1", "words": {"type": dict(style)}},
                {"file": "b", "version": "b", "sha256": "2", "words": {"type": dict(style, zone={"top": 16, "bottom": 38}), "band_moved": "clear"}}]
        self.assertNotIn("the versions are not set in one type (face, weight, size and band differ)",
                         CV.check_ad(rows, faces=lambda p: []))
        rows[1]["words"].pop("band_moved")
        self.assertIn("the versions are not set in one type (face, weight, size and band differ)",
                      CV.check_ad(rows, faces=lambda p: []))


if __name__ == "__main__":
    unittest.main()
