"""De-slop is step 2 of every casting sheet (owner ruling 2026-11-10): the raw master is re-textured from real
skin and hair photos before any sheet, and the headshot takes its face from that master only."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location("mc_deslop", HERE / "make_character.py")
MC = importlib.util.module_from_spec(sp); sp.loader.exec_module(MC)


def spec_with(tmp: Path, texture=True) -> dict:
    s = {"id": "x", "brand": "b", "who": "a person", "adjustments": ["different face"], "base": "a tee",
         "details": "hands", "looks": {"look-1": {"outfit": "a tee"}}, "character": {"title": "X"}}
    if texture:
        for n in ("skin.jpg", "hair.jpg"):
            (tmp / n).write_bytes(b"x")
        s["texture"] = {"skin": {"file": str(tmp / "skin.jpg"), "shows": "fair skin"},
                        "hair": {"file": str(tmp / "hair.jpg"), "shows": "brown hair", "on": "short hair"}}
    return s


class DeslopStep(unittest.TestCase):
    def test_no_texture_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            gaps = MC.refuse_texture(spec_with(Path(t), texture=False), Path(t))
            self.assertTrue(any("texture.skin" in g for g in gaps))
            self.assertTrue(any("texture.hair" in g for g in gaps))

    def test_missing_texture_file_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            s = spec_with(Path(t)); (Path(t) / "hair.jpg").unlink()
            self.assertTrue(any("not found" in g for g in MC.refuse_texture(s, Path(t))))

    def test_deslop_comes_second_and_feeds_every_sheet(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t); out = t / "out"
            P, _ = MC.prompts()
            J = MC.jobs(spec_with(t), P, [t / "real.jpg"], [], out, t)
            names = [j[0] for j in J]
            self.assertEqual(names[:3], ["master", "deslop", "headshot"])
            master_dest, raw = out / "full" / "master.png", out / "full" / "master-raw.png"
            self.assertEqual(J[0][3], raw)                                   # the master is made raw
            self.assertEqual(J[1][2], [raw, t / "skin.jpg", t / "hair.jpg"])  # de-slop: raw, skin, hair
            self.assertEqual(J[1][3], master_dest)                           # ...and becomes the master
            self.assertEqual(J[2][2], [master_dest, t / "skin.jpg"])         # headshot: no real frame
            for name, _, refs, _, _ in J[2:]:
                self.assertNotIn(raw, refs, name)                            # no sheet from the raw master

    def test_deslop_prompt_names_the_photos(self):
        with tempfile.TemporaryDirectory() as t:
            P, _ = MC.prompts()
            p = MC.deslop_prompt(spec_with(Path(t)), P)
            self.assertIn("fair skin", p); self.assertIn("short hair", p)
            self.assertNotIn("{", p)


if __name__ == "__main__":
    unittest.main()
