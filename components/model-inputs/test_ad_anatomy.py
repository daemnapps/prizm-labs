"""Behaviour tests for ad_anatomy: scoring and the winners' dial level. No files read."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ad_anatomy as aa  # noqa: E402


def test_percentiles_rank_ties_and_lone_swipe():
    p = aa.percentiles({"a": 100.0, "b": 5000.0, "c": 5000.0, "d": 1.0, "e": 9e6})
    assert p["d"] == 0.0 and p["e"] == 1.0
    assert p["b"] == p["c"] == 0.625  # ranks 2 and 3 share 2.5 / 4
    assert p["a"] == 0.25
    assert aa.percentiles({"only": 42.0}) == {"only": 0.5}
    assert aa.percentiles({}) == {}


def test_scores_normalise_within_brand_kind_and_number_type():
    per = {r: {"brand": b, "kind": k} for r, b, k in [
        ("o1", "x", "organic"), ("o2", "x", "organic"), ("o3", "x", "organic"),
        ("p1", "x", "paid"), ("p2", "x", "paid"), ("q1", "y", "organic"), ("n1", "x", "organic")]}
    numbers = {
        "o1": ("views", 1e3), "o2": ("views", 1e6), "o3": ("views", 5e4),
        "p1": ("days", 10.0), "p2": ("days", 200.0),
        "q1": ("views", 1.0),  # alone in its brand: middle, never the bottom
    }
    aa.score_swipes(per, numbers)
    assert (per["o1"]["score"], per["o3"]["score"], per["o2"]["score"]) == (0.0, 0.5, 1.0)
    assert (per["p1"]["score"], per["p2"]["score"]) == (0.0, 1.0)
    assert per["q1"]["score"] == 0.5
    assert per["n1"]["score"] is None and per["n1"]["score_from"] is None
    assert per["o2"]["score_from"] == "views 1M"
    assert per["p2"]["score_from"] == "ran 200 days"


def test_winners_level_is_median_of_top_third():
    per = {}
    for i, (score, level) in enumerate([(0.9, 4), (0.8, 3), (0.7, 3), (0.5, 0), (0.3, 0),
                                        (0.2, 1), (0.1, 0), (None, 2), (None, 0)]):
        per["r%d" % i] = {"score": score, "dials": {"contrast": level}, "labels": {}, "kinds": {}}
    board = aa.tally(per)
    # 7 scored -> top third is the best 3 (rounded up): levels 4, 3, 3
    assert sorted(board["winners"]) == ["r0", "r1", "r2"]
    assert board["dials"]["contrast"]["winners_level"] == 3
    assert board["dials"]["contrast"]["all_level"] == 1  # median of 0,0,0,0,1,2,3,3,4
    lv0 = board["dials"]["contrast"]["levels"]["0"]
    assert lv0["count"] == 4 and lv0["avg_score"] == 0.3  # (0.5 + 0.3 + 0.1) / 3, None skipped
