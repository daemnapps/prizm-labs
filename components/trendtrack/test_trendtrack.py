"""No network. The ceiling and the swipe pool shape are the two things that must hold."""
import unittest

import trendtrack as tt


class Ceiling(unittest.TestCase):
    def test_first_call_stays_small_and_leaves_overhead(self):
        self.assertEqual(tt.rows_to_ask(0, 0, 500), tt.FIRST_PAGE)
        self.assertEqual(tt.rows_to_ask(0, 0, 3), 1)

    def test_next_call_is_sized_from_the_real_cost(self):
        # 10 rows cost 20 credits, so 2 a row; 30 left minus overhead buys 14 rows
        self.assertEqual(tt.rows_to_ask(20, 10, 50), 14)

    def test_stops_under_the_ceiling(self):
        with self.assertRaises(tt.OverCeiling):
            tt.rows_to_ask(24, 10, 25)


class SweepShape(unittest.TestCase):
    AD = {"id": "a1", "status": "active", "daysRunning": 40, "firstSeenAt": "2026-09-01",
          "media": {"type": "video", "mediaUrl": "https://m/v.mp4", "thumbnailUrl": "https://m/t.jpg"},
          "content": {"title": "T", "body": "B", "landingPageUrl": "https://lp/x"},
          "metrics": {"duplicates": 7, "reach": 1000},
          "advertiser": {"id": "9", "name": "Some Blog"}}

    def test_video_ad_carries_what_cluster_reads(self):
        it = tt.to_sweep_item(self.AD)
        self.assertEqual((it["id"], it["title"], it["description"]), ("a1", "T", "B"))
        self.assertEqual((it["video_url"], it["image_url"]), ("https://m/v.mp4", "https://m/t.jpg"))
        self.assertEqual(it["meta_group_ads_count"], 7)
        self.assertEqual(it["landing_page"], "https://lp/x")

    def test_image_ad_has_no_video(self):
        ad = dict(self.AD, media={"type": "image", "mediaUrl": "https://m/i.jpg"})
        it = tt.to_sweep_item(ad)
        self.assertEqual((it["video_url"], it["image_url"]), ("", "https://m/i.jpg"))

    def test_missing_duplicates_counts_as_one(self):
        ad = dict(self.AD, metrics={})
        self.assertEqual(tt.to_sweep_item(ad)["meta_group_ads_count"], 1)


if __name__ == "__main__":
    unittest.main()
