"""Behaviour of the swipe swap job's gate: a cut-off product fails, an unapproved or changed job will not run."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ssj", HERE / "swipe_swap_job.py")
ssj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssj)


def tube(path, cropped):
    im = Image.new("RGB", (400, 600), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([120, 40 if not cropped else 40, 280, 560 if not cropped else 600], fill=(210, 190, 120))
    im.save(path)


class ProductWhole(unittest.TestCase):
    def test_whole_tube_passes(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "a.png"
            tube(p, cropped=False)
            self.assertTrue(ssj.product_whole(p)[0])

    def test_tube_running_off_the_bottom_fails_and_says_where(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "b.png"
            tube(p, cropped=True)
            ok, why = ssj.product_whole(p)
            self.assertFalse(ok)
            self.assertIn("bottom", why)


class Approval(unittest.TestCase):
    def job(self, t):
        f = Path(t) / "m.png"
        f.write_bytes(b"x")
        job = {"brand": "b", "cast": "c", "clip": "", "product": "", "gate": {"green": True, "sends": [str(f)]}}
        ssj.swap_prompt = lambda j: "words"
        import hashlib
        job["approved"] = {"by": "x", "at": "t", "prompt_sha": hashlib.sha256(b"words").hexdigest()[:12],
                           "files": {"m.png": ssj._sha(f)}}
        return job, f

    def test_approved_job_holds(self):
        with tempfile.TemporaryDirectory() as t:
            job, _ = self.job(t)
            self.assertIsNone(ssj._approval_holds(job))

    def test_a_picture_changed_after_approval_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            job, f = self.job(t)
            f.write_bytes(b"different")
            self.assertIn("changed", ssj._approval_holds(job))

    def test_unapproved_refuses(self):
        self.assertIn("not approved", ssj._approval_holds({"approved": None}))


if __name__ == "__main__":
    unittest.main()
