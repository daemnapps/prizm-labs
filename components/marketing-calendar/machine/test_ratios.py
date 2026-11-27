"""ratios.py: offer shares dealt exactly and evenly; pinned and lead types keep the first offer; the gate breaks on
offers and warns on kinds and audiences; a brand with no ratios.json is untouched."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ratios as R

RAT = {"tolerance_points": 5,
       "offer": {"shares": [{"keys": ["lead"], "share": 50}, {"keys": ["two"], "share": 25},
                            {"keys": ["three"], "share": 15}, {"keys": ["s1", "s2"], "share": 10}],
                 "pinned_types": ["last-chance"], "lead_types": ["sale-window"]},
       "category": {"shares": {"Promotional": 50, "Educational": 50}},
       "audience": {"buckets": {"non": ["Lead"], "buyers": ["Customer"]}, "shares": {"non": 70, "buyers": 30}}}


def brand(r=RAT):
    d = Path(tempfile.mkdtemp())
    if r is not None:
        (d / "email-sms").mkdir()
        (d / "email-sms" / "ratios.json").write_text(json.dumps(r))
    return d


def month(n=20):
    return [{"id": f"m-{i:02d}", "date": f"2026-12-{i + 1:02d}", "channel": "email", "type": "sale-window",
             "offer": "lead", "product": "lead", "category": "Promotional", "segment": "Core | Lead"}
            for i in range(n)]


def test_shares_exact():
    s = month(20)
    R.apply_offers(s, brand())
    c = {k: sum(1 for x in s if x["offer"] == k) for k in ("lead", "two", "three", "s1", "s2")}
    assert c["lead"] == 10 and c["two"] == 5 and c["three"] == 3 and c["s1"] + c["s2"] == 2, c
    assert all(x["offer_mix"][0] == x["offer"] for x in s)


def test_spread_not_bunched():
    s = month(20)
    R.apply_offers(s, brand())
    firsts = [x["offer"] for x in sorted(s, key=lambda x: x["date"])][:4]
    assert "two" in firsts, firsts


def test_pinned_keeps_lead():
    s = month(8)
    s[-1]["type"] = "last-chance"
    R.apply_offers(s, brand())
    assert s[-1]["offer"] == "lead"


def test_no_offer_sends_untouched_and_sms_untouched():
    s = month(4) + [{"id": "x", "date": "2026-12-09", "channel": "email", "offer": "none", "product": "none"},
                    {"id": "t", "date": "2026-12-09", "channel": "sms", "offer": "lead", "product": "lead"}]
    R.apply_offers(s, brand())
    assert s[-2]["offer"] == "none" and s[-1]["offer"] == "lead"


def test_gate_breaks_on_offer_warns_on_kinds():
    s = month(10)
    b, w = R.problems(s, brand())
    assert b and b[0].startswith("ratio · offer")
    assert any("category" in x for x in w) and any("audience" in x for x in w)
    R.apply_offers(s, brand())
    b, _ = R.problems(s, brand())
    assert not b, b


def test_small_month_on_quota_passes():
    s = month(9)
    R.apply_offers(s, brand())
    b, _ = R.problems(s, brand())
    assert not b, b


def test_balance_kinds_and_audience_keep_roles():
    b = brand()
    (b / "email-sms" / "email-types.json").write_text(json.dumps({"types": [
        {"key": "proof-drop", "well": "real", "role": "earns"}, {"key": "mechanism", "well": "help", "role": "earns"},
        {"key": "sale-window", "well": "ask", "role": "asks"}]}))
    s = month(10)
    for x in s[5:]:
        x.update(type="proof-drop", role="earns", category="Community", offer="none")
    for x in s[:5]:
        x["role"] = "asks"
    r = json.loads((b / "email-sms" / "ratios.json").read_text())
    r["category"] = {"shares": {"Promotional": 50, "Educational": 50}}
    (b / "email-sms" / "ratios.json").write_text(json.dumps(r))
    ch = R.balance(s, b)
    cats = [x["category"] for x in s]
    assert cats.count("Educational") == 5 and all(x["type"] == "mechanism" for x in s[5:]), cats
    assert all(x["role"] == "earns" for x in s[5:])
    segs = [x["segment"] for x in s]
    assert segs.count("Core | Customer") == 3, segs


def test_no_file_no_change():
    s = month(6)
    assert R.apply_offers(s, brand(None)) == []
    assert all(x["offer"] == "lead" for x in s)
    b, w = R.problems(s, brand(None))
    assert not b and w


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
    print("ok")
