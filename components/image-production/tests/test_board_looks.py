"""set_queue.board_members: the cast board takes each member's look from the request (2026-11-21, brief-0380: every
board took the first look on file while the brief put the member in another). Nothing is called."""
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from image_production import set_queue as Q  # noqa: E402


class BoardLooks(unittest.TestCase):
    def test_each_member_takes_the_look_the_request_names(self):
        r = {"cast": ["yai", "creator"], "looks": {"yai": "outfit-gold", "creator": "look-2-denim"}}
        self.assertEqual(Q.board_members(r), ["yai:outfit-gold", "creator:look-2-denim"])

    def test_a_member_with_no_look_named_is_left_to_the_board(self):
        self.assertEqual(Q.board_members({"cast": ["a", "b:look-x"], "looks": {"b": "look-y"}}), ["a", "b:look-x"])
        self.assertEqual(Q.board_members({"cast": ["a"]}), ["a"])

    def test_a_styled_variants_look_puts_the_variant_on_the_board(self):
        import tempfile
        root = Path(tempfile.mkdtemp(prefix="boardlooks_"))
        home = root / "runs" / "ai-elements" / "b" / "casting" / "guy"
        (home / "styles" / "toon" / "sheets").mkdir(parents=True)
        (home / "styles" / "toon" / "sheets" / "look-2-hoodie.jpg").write_bytes(b"x")
        old = Q.P.repo
        Q.P.repo = lambda: root
        try:
            got = Q.board_members({"brand": "b", "style": "toon", "cast": ["guy"], "looks": {"guy": "look-2-hoodie"}})
        finally:
            Q.P.repo = old
        self.assertEqual(got, ["guy/styles/toon:look-2-hoodie"])


if __name__ == "__main__":
    unittest.main()
