"""Every element is made in the swipe's style (the owner, 2026-10-09): a style id
replaces the photoreal realism line; an unknown style is refused by name."""
import importlib.util, sys, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location("mc_style", HERE / "make_character.py")
MC = importlib.util.module_from_spec(sp); sp.loader.exec_module(MC)


class StyleLock(unittest.TestCase):
    def test_animated_style_leads(self):
        lock = MC.style_lock("family-3d")
        self.assertTrue(lock.startswith("STYLE LOCK"))
        self.assertIn("never photoreal", lock)

    def test_real_footage_keeps_realism(self):
        self.assertIsNone(MC.style_lock("phone-ugc"))
        self.assertIsNone(MC.style_lock(None))

    def test_unknown_style_refused(self):
        with self.assertRaises(SystemExit):
            MC.style_lock("new:not-a-row")

    def test_style_fills_the_realism_slot(self):
        P = {"master": "{who} {real}", "turnaround": "t {real}", "angles-expressions": "a", "light-test": "l",
             "details": "d", "look": "{outfit} {real}", "realism": "PHOTOREAL"}
        spec = {"who": "a man", "adjustments": ["x"], "base": "b", "details": "d", "looks": {"look-1": {"outfit": "suit"}},
                "style_id": "family-3d"}
        J = MC.jobs(spec, P, [], [], Path("/tmp/x"), Path("/tmp"))
        self.assertTrue(all("PHOTOREAL" not in j[1] for j in J))
        self.assertTrue(all(j[1].startswith("STYLE LOCK") for j in J))


if __name__ == "__main__":
    unittest.main()
