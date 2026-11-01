"""New ads go into ad sets already running (the owner, 2026-10-27: "our campaign is established so most new
ads will go into existing ad sets unless a new angle or avatar is clearly defined"). A closed ad set fails
the card's check and the uploader never makes one; a running, signed or promo ad set is open."""
import sys, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import ad_sets as AS
import cards as C, upload as U
from fake_meta import FakeMeta
from test_cards import Base, NAME

RUNNING = "adset_brand_b_spot-hider_pigment-memory"
CLOSED = "adset_brand_b_spot-hider_pro-aging"


class Open(unittest.TestCase):
    def test_running_signed_and_promo_are_open_nothing_else(self):
        with mock.patch.object(AS, "live", return_value={RUNNING}), \
                mock.patch.object(AS, "signed", return_value={"adset_brand_b_spot-hider_value"}):
            self.assertIsNone(AS.why_closed("brand-b", RUNNING))
            self.assertIsNone(AS.why_closed("brand-b", "adset_brand_b_spot-hider_value"))
            self.assertIsNone(AS.why_closed("brand-b", "adset_brand_b_spot-hider_promo"))
            self.assertIn("not open in Meta", AS.why_closed("brand-b", CLOSED))
            self.assertEqual(AS.open_angles("brand-b", "spot-hider", ["pigment-memory", "pro-aging", "value"]),
                             ["pigment-memory", "value"])

    def test_name_is_the_brands_template(self):
        self.assertEqual(AS.name_for("brand-b", "spot-hider", "pro-aging"), CLOSED)


class FormatsAreNotAngles(unittest.TestCase):
    def test_a_misfiled_row_names_no_ad_set(self):
        import json
        angles = json.loads((U.REPO / "brands/brand-a/strategy/angles.json").read_text())["angles"]
        fmt = next((a for a in angles if a.get("misfiled") and a.get("status") == "active"), None)
        if fmt is None:
            self.skipTest("no misfiled row in the brand's angles to test against")
        name, why = U.ad_set_for(U.Brand("brand-a"), {"avatar": fmt.get("avatar"), "angle": fmt["id"]})
        self.assertIsNone(name)
        self.assertIn("is a format, not an angle", why)


class OnTheCard(Base):
    def test_a_closed_ad_set_fails_the_check_and_says_why(self):
        f = self.card(angle="pro-aging")
        c = C.check_and_save(f, meta=FakeMeta("brand-b"))
        self.assertFalse(c["checks"]["ad_set"]["ok"])
        self.assertIn("not open in Meta", c["checks"]["ad_set"]["why"])

    def test_a_running_ad_set_passes(self):
        f = self.card()
        c = C.check_and_save(f, meta=FakeMeta("brand-b"))
        self.assertTrue(c["checks"]["ad_set"]["ok"], c["checks"]["ad_set"])

    def test_the_uploader_never_makes_a_closed_ad_set(self):
        f = self.approve(self.card(angle="pro-aging"))
        m = FakeMeta("brand-b")
        with self.assertRaises(SystemExit) as e:
            U.go(f, U.card_plan(f, C.load(f)), {"by": "the owner"}, m=m, log=lambda *_: None,
                 state_f=Path(self.tmp.name) / "state.json")
        self.assertIn("not open in Meta", str(e.exception))
        self.assertEqual([x for x, _ in m.posts if x == "adsets"], [])

    def test_a_signed_ad_set_is_made(self):
        f = self.approve(self.card(angle="pro-aging", ad_name=NAME))
        m = FakeMeta("brand-b")
        with mock.patch.object(AS, "signed", return_value={CLOSED}):
            U.upload_card(f, m=m, log=lambda *_: None)
        self.assertIn("adsets", [x for x, _ in m.posts])


if __name__ == "__main__":
    unittest.main()
