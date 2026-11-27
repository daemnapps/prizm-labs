"""product3d.composite_into: the kit is rendered once and placed once, and never placed over a scene that could not be
read or already shows the product (2026-11-13: a product inside a product)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from PIL import Image  # noqa: E402

from image_production import product3d as P3  # noqa: E402

SPOT = {"spots": [{"box_2d": [500, 400, 900, 600]}], "kind": "photo", "reference": None}


class OneProduct(unittest.TestCase):
    def run_with(self, answer):
        with tempfile.TemporaryDirectory() as d:
            scene = Path(d) / "scene.png"
            Image.new("RGB", (100, 100), (255, 255, 255)).save(scene)
            calls = {"render": 0, "place": 0}

            def render(*a, **k):
                calls["render"] += 1
                return {"file": "product.png", "source": "3d-model"}

            def place(*a, **k):
                calls["place"] += 1
                return {"box": [1, 2, 3, 4]}

            def ask(img, q):
                if isinstance(answer, Exception):
                    raise answer
                return answer

            with mock.patch.object(P3, "render_product", render), mock.patch.object(P3, "place_located", place), \
                    mock.patch.object(P3, "kit_facts", lambda kit: {"what": "the product"}), \
                    mock.patch.object(P3, "size_words", lambda facts: "11 cm"):
                pl = {"x": 0.5, "y": 0.7, "height": 0.3, "fixed": False}
                try:
                    got = P3.composite_into(scene, Path(d) / "out.png", "kit", pl, Path(d) / "work", ask=ask)
                    return calls, got, None
                except P3.PlacementRefused as e:
                    return calls, None, e

    def test_an_empty_scene_gets_the_product_once(self):
        calls, got, err = self.run_with(dict(SPOT, already=False))
        self.assertIsNone(err)
        self.assertEqual(calls, {"render": 1, "place": 1})

    def test_a_scene_that_already_shows_the_product_gets_none(self):
        calls, got, err = self.run_with(dict(SPOT, already=True))
        self.assertIsNotNone(err)
        self.assertIn("already shows", str(err))
        self.assertEqual(calls["place"], 0)

    def test_a_scene_that_could_not_be_read_gets_none(self):
        calls, got, err = self.run_with(RuntimeError("judge error 402: credits depleted"))
        self.assertIsNotNone(err)
        self.assertIn("could not be read", str(err))
        self.assertEqual(calls["place"], 0)

    def test_the_locate_prompt_asks_whether_the_product_is_already_there(self):
        from image_production import prompting
        self.assertIn('"already"', prompting.body(prompting.latest("product-locate")))


if __name__ == "__main__":
    unittest.main()
