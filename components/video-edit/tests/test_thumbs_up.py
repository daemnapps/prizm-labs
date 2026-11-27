"""The styled cover step: a caption box never covers the line above it, and the surreal dial never puts the product on a
face (a close frame refuses the level instead)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "machine"))
import thumbs_up as U  # noqa: E402

W, H = 1080, 1920
BOXED = {"size": [W, H], "words": {"look": "caption-box", "size": 70, "side": 90, "line_height": 1.16, "gap": 0.12,
                                   "y": 0.75}}
L = {"colors": {"accent": "#ffd400", "light": "#fff", "dark": "#111", "mark": "#e00", "stamp_text": "#111"}, "fonts": {}}
CLOSE = {"faces": [{"x": 0.15, "y": 0.12, "w": 0.7, "h": 0.5}], "lips": [{"x": 0.42, "y": 0.48, "w": 0.16, "h": 0.05}]}


def _on(box, sc):
    return U._on_face(box, {"_faces": sc}, {"size": [W, H]})


class CaptionBox(unittest.TestCase):
    def test_line_height_clears_the_box_padding(self):
        css = U.css(L, BOXED)
        self.assertIn(".cap.boxed{line-height:1.5}", css)
        self.assertIn(".cap.boxed .ln+.ln{margin-top:21px}", css)          # 0.3em of 70px, not the style's 0.12em

    def test_estimate_matches_the_drawn_height(self):
        it = {"id": "x", "caption": [["Why you breaking out?", ""], ["Ew, bumpy face", "key"]]}
        _, (x0, y0, x1, y1) = U._caption_html(it, BOXED)
        self.assertAlmostEqual(y1 - y0, 2 * 70 * 1.5 + 0.3 * 70, places=3)

    def test_a_taller_style_line_height_is_kept(self):
        S = {"size": [W, H], "words": dict(BOXED["words"], line_height=1.7)}
        self.assertIn(".cap.boxed{line-height:1.7}", U.css(L, S))


class SurrealDial(unittest.TestCase):
    def item(self, lvl, sc, ident="H2"):
        return {"id": ident, "absurd": lvl, "prop": "product.png", "prop_ratio": 1.5, "_faces": sc}

    def test_level_2_moves_off_a_face_in_the_top_half(self):
        sc = {"faces": [{"x": 0.3, "y": 0.1, "w": 0.4, "h": 0.25}], "lips": []}
        out = U.props(self.item(2, sc), {"size": [W, H]})
        self.assertEqual(len(out), 1)
        cls, x, y, w, r = out[0]
        self.assertFalse(_on((x, y, x + w, y + w * 1.5), sc))
        self.assertGreater(y, 0)                                             # not hanging from the top any more

    def test_level_3_leaves_no_product_on_a_face(self):
        sc = {"faces": [{"x": 0.05, "y": 0.35, "w": 0.4, "h": 0.2}, {"x": 0.6, "y": 0.4, "w": 0.35, "h": 0.2}],
              "lips": [{"x": 0.2, "y": 0.5, "w": 0.08, "h": 0.03}]}
        for ident in ("control", "H2", "H3", "H4", "H5", "H6"):
            for cls, x, y, w, r in U.props(self.item(3, sc, ident), {"size": [W, H]}):
                self.assertFalse(_on((x, y, x + w, y + w * 1.5), sc), (ident, cls, x, y, w))

    def test_a_close_frame_refuses_the_level(self):
        for lvl in (2, 3):
            with self.assertRaises(SystemExit):
                U.props(self.item(lvl, {"faces": [{"x": 0, "y": 0, "w": 1, "h": 1}], "lips": []}), {"size": [W, H]})

    def test_no_faces_keeps_the_old_place(self):
        cls, x, y, w, r = U.props(self.item(2, {}), {"size": [W, H]})[0]
        self.assertAlmostEqual(y, -w * 0.62)

    def test_same_picture_on_a_rerender(self):
        sc = {"faces": [{"x": 0.3, "y": 0.1, "w": 0.4, "h": 0.25}], "lips": []}
        self.assertEqual(U.props(self.item(3, sc), {"size": [W, H]}), U.props(self.item(3, sc), {"size": [W, H]}))


if __name__ == "__main__":
    unittest.main()
