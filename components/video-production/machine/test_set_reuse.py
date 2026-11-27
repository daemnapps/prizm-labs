"""set_reuse.py: a place we have is used; a place that only sounds alike is made new."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import set_reuse as S  # noqa: E402

BANK = {"apothecary-kitchen": "a bright clean kitchen dressed as a herbalist dispensary, white quartz countertop, jars, window, daylight",
        "night-kitchen": "a bright clean kitchen dressed as a herbalist dispensary, white quartz countertop, jars, window at night",
        "living-room": "a small living room, white walls, doll miniature set"}


class SetReuse(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.ws = Path(self.d.name)
        for n in BANK:
            p = self.ws / "runs/ai-elements/b/sets" / n / "plates" / "wide.png"
            p.parent.mkdir(parents=True)
            p.write_bytes(b"x")
        self.rows = [{"kind": "place", "name": n, "what": n + " " + w} for n, w in BANK.items()]

    def tearDown(self):
        self.d.cleanup()

    def ask(self, rid, said, **kw):
        return S.banked_set("b", dict({"id": rid, "description": said}, **kw), ws=self.ws, rows=self.rows)[0]

    def test_the_same_place_is_used(self):
        self.assertEqual(self.ask("THE KITCHEN", "a bright clean kitchen like a herbalist dispensary with a white quartz countertop and jars", time_of_day="day"),
                         "apothecary-kitchen")

    def test_night_is_not_day(self):
        self.assertEqual(self.ask("THE KITCHEN", "a bright clean kitchen like a herbalist dispensary, white quartz countertop, jars", time_of_day="night"), "night-kitchen")

    def test_only_alike_is_made_new(self):
        self.assertIsNone(self.ask("THE KITCHEN", "a dark slate kitchen with black marble"))
        self.assertIsNone(self.ask("YAI'S KITCHEN", "a bright clean kitchen like a herbalist dispensary with a white quartz countertop and jars"))
        self.assertIsNone(self.ask("BARBER ROOM", "a small room with white walls"))
        self.assertIsNone(self.ask("LIVING ROOM", "a small living room, white walls"))


if __name__ == "__main__":
    unittest.main()
