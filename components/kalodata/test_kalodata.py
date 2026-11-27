import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kalodata as K
def fake(n):
    calls = []
    def send(p, b): calls.append((p, b)); return [{"video_id": "%d-%d" % (b["page_number"], i), "belonged_creator_handle": "x", "revenue": i} for i in range(min(n, b["page_size"]))]
    return calls, send
class T(unittest.TestCase):
    def test_ceiling_refuses_before_sending(self):
        c, s = fake(100)
        with self.assertRaises(K.OverCeiling): K.ranking("videos", {"rows": 200}, K.Purse(0.1), s)
        self.assertEqual(len(c), 1)
    def test_cost_is_a_tenth_per_hundred(self): self.assertEqual((K.rank_cost(100), K.rank_cost(101)), (0.1, 0.2))
    def test_stops_on_a_short_page(self):
        c, s = fake(40); self.assertEqual((len(K.ranking("videos", {"rows": 300}, K.Purse(1), s)), len(c)), (40, 1))
    def test_filters_reach_the_call(self):
        b = K.body({"keyword": "k", "category": "9", "days": 30}); self.assertEqual((b["keyword"], b["category_ids"], b["date_range"]), ("k", ["9"], "last30Day"))
    def test_link(self): self.assertEqual(K.ranking("videos", {"rows": 1}, K.Purse(1), fake(1)[1])[0]["link"], "https://www.tiktok.com/@x/video/1-0")
    def test_merge_one_row_per_video(self):
        m = K.merge([("a", [{"video_id": "1", "revenue": 2}]), ("b", [{"video_id": "1", "revenue": 2}, {"video_id": "2", "revenue": 9}])])
        self.assertEqual([(x["video_id"], x["found_by"]) for x in m], [("2", ["b"]), ("1", ["a", "b"])])
if __name__ == "__main__": unittest.main()
