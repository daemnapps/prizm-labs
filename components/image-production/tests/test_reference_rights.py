"""A creator's footage is a picture reference only when her rights allow the picture's use (email_lead, 2026-11-10)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from image_production import assets as AS  # noqa: E402

CC = "Shared Assets/brands/b/content-creators/women/look/30s/"
REGISTER = {
    "creators": [
        {"creator": "Paid", "drive_folder": "paid", "paid_ads": True, "website": True, "email": True},
        {"creator": "NoAds", "drive_folder": "noads", "paid_ads": False, "website": True},
    ],
    "pre_registry": {"website": True, "drive_folders": ["early"]},
    "glenn_era": {"paid_ads": True, "website": True, "social": True, "email": True, "drive_folders": ["glenn"]},
}


def row(name, folder=None):
    return {"name": name, "label": CC + folder + "/raw/clip.mp4" if folder else "Shared Assets/brands/b/products/x.png"}


class ReferenceRights(unittest.TestCase):
    def names(self, use):
        rows = [row("paid", "paid"), row("noads", "noads"), row("early", "early"), row("glenn", "glenn"),
                row("stranger", "stranger"), row("packshot")]
        kept, why = AS.cleared("b", rows, use, register=AS._rights().load(register=REGISTER))
        return [r["name"] for r in kept], why

    def test_ads_keeps_only_cleared_creators(self):
        kept, why = self.names("ads")
        self.assertEqual(kept, ["paid", "glenn", "packshot"])
        self.assertEqual(len(why), 3)
        self.assertTrue(any("noads" in w and "refused" in w for w in why))
        self.assertTrue(any("stranger" in w and "unknown" in w for w in why))

    def test_website_follows_the_folder_list(self):
        kept, _ = self.names("website")
        self.assertEqual(kept, ["paid", "noads", "early", "glenn", "packshot"])

    def test_email_is_strict(self):
        kept, _ = self.names("email")
        self.assertEqual(kept, ["paid", "glenn", "packshot"])

    def test_use_of_purpose(self):
        self.assertEqual(AS.use_of("email-hero"), "email")
        self.assertEqual(AS.use_of("page-section"), "website")
        self.assertEqual(AS.use_of("ad"), "ads")
        self.assertEqual(AS.use_of(None), "ads")


if __name__ == "__main__":
    unittest.main()
