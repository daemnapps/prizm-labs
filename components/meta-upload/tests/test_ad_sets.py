"""New ads go into ad sets already running (owner, 2026-10-27: "our campaign is established so most new
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
            self.assertIsNone(AS.why_closed("brand_b", RUNNING))
            self.assertIsNone(AS.why_closed("brand_b", "adset_brand_b_spot-hider_value"))
            self.assertIsNone(AS.why_closed("brand_b", "adset_brand_b_spot-hider_promo"))
            self.assertIn("not open in Meta", AS.why_closed("brand_b", CLOSED))
            self.assertEqual(AS.open_angles("brand_b", "spot-hider", ["pigment-memory", "pro-aging", "value"]),
                             ["pigment-memory", "value"])

    def test_name_is_the_brands_template(self):
        self.assertEqual(AS.name_for("brand_b", "spot-hider", "pro-aging"), CLOSED)


class FormatsAreNotAngles(unittest.TestCase):
    def test_a_misfiled_row_names_no_ad_set(self):
        import json
        angles = json.loads((U.REPO / "brands/brand_a/strategy/angles.json").read_text())["angles"]
        fmt = next((a for a in angles if a.get("misfiled") and a.get("status") == "active"), None)
        if fmt is None:
            self.skipTest("no misfiled row in the brand's angles to test against")
        name, why = U.ad_set_for(U.Brand("brand_a"), {"avatar": fmt.get("avatar"), "angle": fmt["id"]})
        self.assertIsNone(name)
        self.assertIn("is a format, not an angle", why)


class OnTheCard(Base):
    def test_a_closed_ad_set_fails_the_check_and_says_why(self):
        f = self.card(angle="pro-aging")
        c = C.check_and_save(f, meta=FakeMeta("brand_b"))
        self.assertFalse(c["checks"]["ad_set"]["ok"])
        self.assertIn("not open in Meta", c["checks"]["ad_set"]["why"])

    def test_a_running_ad_set_passes(self):
        f = self.card()
        c = C.check_and_save(f, meta=FakeMeta("brand_b"))
        self.assertTrue(c["checks"]["ad_set"]["ok"], c["checks"]["ad_set"])

    def test_the_uploader_never_makes_a_closed_ad_set(self):
        f = self.approve(self.card(angle="pro-aging"))
        m = FakeMeta("brand_b")
        with self.assertRaises(SystemExit) as e:
            U.go(f, U.card_plan(f, C.load(f)), {"by": "owner"}, m=m, log=lambda *_: None,
                 state_f=Path(self.tmp.name) / "state.json")
        self.assertIn("not open in Meta", str(e.exception))
        self.assertEqual([x for x, _ in m.posts if x == "adsets"], [])

    def test_a_signed_ad_set_is_made(self):
        f = self.approve(self.card(angle="pro-aging", ad_name=NAME))
        m = FakeMeta("brand_b")
        with mock.patch.object(AS, "signed", return_value={CLOSED}):
            U.upload_card(f, m=m, log=lambda *_: None)
        self.assertIn("adsets", [x for x, _ in m.posts])


if __name__ == "__main__":
    unittest.main()


class RunningFromWarehouse(unittest.TestCase):
    """An ad set the warehouse saw running is open, even when our uploads never put an ad into it."""
    def test_running_ad_set_is_open(self):
        import tempfile, json as _j
        import ad_sets as AS
        root = Path(tempfile.mkdtemp())
        d = root / "media-buying" / "acme" / "2026-11-02"
        d.mkdir(parents=True)
        (d / "report.json").write_text(_j.dumps({"lines": [{"adset_name": "adset_acme_king_reset-window"}, {"campaign": "x"}]}))
        self.assertEqual(AS.running("acme", runs_root=root), {"adset_acme_king_reset-window"})


class AngleOnTheAdSet(unittest.TestCase):
    """The ad set carries the brief's own angle; a running ad set of another angle is refused."""
    def mismatch(self, ad_set, angle="new-man"):
        import cards as CC, to_check as T, ad_sets as A
        with mock.patch.object(T, "brief_facts", return_value={"avatar": "king", "angle": angle}), \
             mock.patch.object(A, "name_for", side_effect=lambda b, av, an: f"adset_acme_{av}_{an}"), \
             mock.patch.object(A, "is_promo", side_effect=lambda b, n: n.endswith("_promo")):
            return CC.angle_mismatch("acme", {"brief_id": "brief-0001", "avatar": "king"}, {ad_set})

    def test_another_angles_ad_set_is_refused(self):
        why = self.mismatch("adset_acme_king_razor")
        self.assertEqual(len(why), 1)
        self.assertIn("adset_acme_king_new-man", why[0])

    def test_the_briefs_own_angle_passes(self):
        self.assertEqual(self.mismatch("adset_acme_king_new-man"), [])

    def test_promo_and_no_angle_are_not_judged(self):
        self.assertEqual(self.mismatch("adset_acme_king_promo"), [])
        self.assertEqual(self.mismatch("adset_acme_king_razor", angle=None), [])
