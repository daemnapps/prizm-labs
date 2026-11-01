"""Every ad the uploader makes carries the ad URL standard (components/funnel-tracking):
utm_source=meta, utm_medium=paid, utm_campaign / utm_term / utm_content filled by Meta with the
campaign, ad set and ad names, and the ad id twice (ad_id for the page, sub1 for the store).
Checked on what is actually posted to a fake Meta, for a flexible ad and a carousel."""
import sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "funnel-tracking" / "machine"))
import standard as S
import upload as U
from fake_meta import FakeMeta
from test_cards import Base, NAME


class UrlTags(Base):
    def posted_ad(self, **card):
        m = FakeMeta("brand-b")
        U.upload_card(self.approve(self.card(**card)), m=m, log=lambda *_: None)
        ads = [p for e, p in m.posts if e == "ads"]
        self.assertEqual(len(ads), 1)
        return ads[0]

    def test_the_uploader_uses_the_standard(self):
        self.assertEqual(U.URL_TAGS, S.url_tags())
        self.assertEqual(S.check_url_tags(U.URL_TAGS, strict=True), [])
        for want in ("utm_source=meta", "utm_medium=paid", "utm_campaign={{campaign.name}}",
                     "utm_term={{adset.name}}", "utm_content={{ad.name}}", "ad_id={{ad.id}}", "sub1={{ad.id}}"):
            self.assertIn(want, U.URL_TAGS.split("&"))

    def test_flexible_ad_carries_the_standard_tags(self):
        ad = self.posted_ad()
        self.assertEqual(ad["creative"]["url_tags"], S.url_tags())
        self.assertEqual(S.check_url_tags(ad["creative"]["url_tags"], strict=True), [])
        link = ad["creative"]["object_story_spec"]["link_data"]["link"]
        self.assertNotIn("{{", link)        # placeholders live in url_tags, never typed into the link

    def test_carousel_ad_carries_the_standard_tags(self):
        ad = self.posted_ad(lane="carousel", fmt="carousel", n=3)
        self.assertEqual(ad["creative"]["url_tags"], S.url_tags())
        for kid in ad["creative"]["object_story_spec"]["link_data"]["child_attachments"]:
            self.assertNotIn("{{", kid["link"])

    def test_the_checker_names_what_is_wrong(self):
        # the two live faults the Funnel Map found (12 Oct): ad id in utm_content, and old tags
        bad = "utm_source=fb&utm_medium=paid&utm_campaign={{campaign.id}}&utm_term={{adset.id}}&utm_content={{ad.id}}"
        problems = S.check_url_tags(bad)
        self.assertTrue(any("utm_content" in p for p in problems))
        self.assertTrue(any("ad_id" in p for p in problems))
        self.assertEqual(S.check_url_tags(""), ["no URL tags at all: the order arrives with no ad name"])


if __name__ == "__main__":
    unittest.main()
