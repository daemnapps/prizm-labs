import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import index as I, kalodata as K
C = {"categories": ["Beauty"], "view_floor": 500000, "money_floor": 5000, "min_roas": 2, "read": 100, "check": 5, "keep": 10}
def v(i, **k): return dict({"video_id": str(i), "belonged_creator_handle": "c%s" % i, "revenue": 9000, "views": 900000, "ad": 1}, **k)
class T(unittest.TestCase):
    def test_rising(self): self.assertEqual((I.rising([1, 1, 1, 2, 2, 2]), I.rising([1]), I.rising([0, 0, 0, 1, 1, 1])), (2.0, None, None))
    def test_floor_and_one_per_creator(self): self.assertEqual([x["video_id"] for x in I.once([v(1, views=9), v(2), v(3, belonged_creator_handle="c2")], C)], ["2"])
    def send(self, p, b):
        self.calls.append((p, b))
        if "category" in p: return [{"category_name": "Beauty", "category_id": "7"}]
        if "detail" in p: return {"revenue_trend": [9, 9, 9, 1, 1, 1] if b["video_id"] == "2" else [1, 1, 1, 5, 5, 5]}
        return [v(1), v(2)] if b["sort_field"]["field"] == "revenue_growth_rate" else [v(1), v(3, revenue=10000), v(4, ad=0), v(5, revenue=20000)]
    def test_walk(self):
        self.calls = []; o = I.build(C, K.Purse(5), self.send)
        self.assertEqual([x["video_id"] for x in o["growing"]], ["1"])              # 2 stopped growing
        self.assertEqual([x["video_id"] for x in o["running"]], ["5", "3"])          # 1 is on growing, 4 is not an ad
        b = self.calls[1][1]; self.assertEqual((b["views_range"], b["revenue_range"], b["date_range"], b["category_ids"]), (">500000", ">5000", "last7Day", ["7"]))
        self.assertNotIn("followers_range", b)
    def test_ceiling(self):
        self.calls = []
        with self.assertRaises(K.OverCeiling): I.build(C, K.Purse(0.2), self.send)
if __name__ == "__main__": unittest.main()
