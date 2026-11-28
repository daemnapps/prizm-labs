"""The flywheel step on a made-up brand: every number comes from files on disk; nothing calls Meta or spends."""
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import flywheel as F  # noqa: E402

DAY = "2026-11-28"
TODAY = dt.date(2026, 11, 28)
CELLS = {"profile": "p1", "awareness": "most-aware", "angle": "promo", "format": "montage", "face": "none",
         "setting": "kitchen", "look": "phone-ugc"}


def ad(i, name, s30, b30, s7, b7, s3="0"):
    return {"ad_id": i, "ad_name": name, "spend30": s30, "buys30": b30, "value30": "0", "spend7": s7, "buys7": b7,
            "value7": "0", "spend3": s3, "first_seen": "2026-11-01"}


def put(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data) if not isinstance(data, str) else data)


def make(base, monkeypatch, fatigue=True):
    b = "testbrand"
    monkeypatch.setenv("PRIZM_TARGETS", str(base / "targets.json"))
    put(base / "targets.json", {b: {"kpi_cpa": 50, "top_share": 0.3}})
    ads = [ad("1", "x_brief-0001_a", "1000", "25", "400", "4", "150"),     # KPI winner (CPA 40), 7d CPA 100: 2.5x
           ad("2", "x_brief-0002_a", "900", "10", "100", "1"),            # spend winner, CPA 90: not KPI
           ad("3", "x_brief-0003_a", "800", "10", "0", "0"),              # spend winner, already varied
           ad("4", "x_brief-0004_a", "100", "1", "0", "0")]
    ads += [ad(str(10 + i), "small_%d" % i, "10", "0", "0", "0") for i in range(6)]
    put(base / "runs/funnel-tracking" / b / DAY / "warehouse.json", {"ads": ads})
    w1 = {"3": {"spend": 150, "sales": 1, "cpa": 150}, "7": {"spend": 400, "sales": 4, "cpa": 100},
          "14": {"spend": 700, "sales": 18, "cpa": 38.9}} if fatigue else \
        {"7": {"spend": 160, "sales": 4, "cpa": 40}, "14": {"spend": 700, "sales": 18, "cpa": 38.9}}
    put(base / "runs/media-buying" / b / "2026-11-27/report.json", {"asof": "2026-11-27", "flags": [
        {"kind": "ad", "id": "1", "windows": w1, "action": "keep", "break_even": 55}]})
    put(base / "brands" / b / "briefs/briefs.json", {"briefs": [
        {"brief": "brief-0002", "moves": CELLS}, {"brief": "brief-0009", "variation_of": "brief-0003"}]})
    lib = base / "runs/creative-diversity" / b / "2026-10-06"
    put(lib / "matrix.json", {"items": [{"asset": "a%d" % i, "moves": dict(CELLS, profile="q%d" % i, format="f%d" % i, setting="s%d" % i, look="look%d" % (i % 3))}
                                        for i in range(5)]})
    put(lib / "ads.json", {"ads": []})
    put(base / "runs/winners" / b / "bank.json", {"rows": [
        {"id": "old-1", "core": True, "name": "Old one", "ad_ids": ["99"], "words": {"hook": "h"},
         "snapshots": [{"purchases": 300, "spend": 15000, "cpa": 50, "roas": 1.4, "first": "2025-01", "last": "2026-05"}]},
        {"id": "live-1", "core": True, "name": "Still live", "ad_ids": ["2"], "snapshots": [{"purchases": 900}]},
        {"id": "cand", "core": False, "state": "candidate", "name": "Not proven", "ad_ids": ["98"], "snapshots": [{"purchases": 5}]}]})
    put(base / "brands" / b / "products/offer-bank.md",
        "# Offers\n\n## promo-calendar\n\n| Dates | Promo | Code | Approved |\n|---|---|---|---|\n"
        "| Dec 1 – Dec 25, 2026 | Holiday set | none | owner |\n\n## other\n")
    return b


def test_proposals(tmp_path, monkeypatch):
    b = make(tmp_path, monkeypatch)
    doc, f = F.write(b, DAY, tmp_path, today=TODAY)
    assert f == tmp_path / "runs/flywheel" / b / DAY / "proposals.json" and f.is_file()
    kinds = [p["kind"] for p in doc["proposals"]]
    assert kinds == ["variations", "matrix", "promo", "re-make"]
    v, m, p, r = doc["proposals"]
    assert v["brief"] == "0001" and v["numbers"]["fatigue"]["state"] == "creative fatigue"
    assert v["numbers"]["fatigue"]["worst"] >= 2 and "--dry-run" in v["cmd"]
    assert m["brief"] == "0002" and m["matrix"]["column"] == "face"    # `none` face is on all 5 running ads
    assert m["matrix"]["keeps"]["angle"] == "promo"
    assert p["numbers"]["start"] == "2026-12-01" and p["numbers"]["opens_in_days"] == 3
    assert r["key"] == "old-1" and r["numbers"]["purchases"] == 300 and "--dry-run" in r["cmd"]
    held = {h["key"]: h["why"] for h in doc["held"]}
    assert "brief 0003" in held and "variation" in held["brief 0003"]
    assert all(x["start"] == {"ask": "flywheel", "input": "%s %s · %s" % (DAY, x["id"], x["title"])} for x in doc["proposals"])
    assert F.latest(b, tmp_path)["date"] == DAY and F.one(b, DAY, "P2", tmp_path)["kind"] == "matrix"


def test_no_fatigue_no_variations(tmp_path, monkeypatch):
    b = make(tmp_path, monkeypatch, fatigue=False)
    doc = F.build(b, DAY, tmp_path, today=TODAY)
    assert "variations" not in [p["kind"] for p in doc["proposals"]]
    # the KPI winner without fatigue is still a spend winner not yet varied: untagged, so the job tags it first
    m = [p for p in doc["proposals"] if p.get("brief") == "0001"]
    assert m and m[0]["kind"] == "matrix" and m[0]["matrix"] is None


def test_rows_carry_numbers_only(tmp_path, monkeypatch):
    b = make(tmp_path, monkeypatch)
    doc = F.build(b, DAY, tmp_path, today=TODAY)
    for p in doc["proposals"]:
        assert p["numbers"] and p["why"]
        assert not any(k in p for k in ("budget", "spend_to", "bid"))   # no money decisions


def test_next_column_needs_two_seen_cells():
    assert F.next_column({"profile": "a", "format": "x"}, []) is None
    nc = F.next_column(CELLS, [dict(CELLS, look="other")] * 3)
    assert nc["column"] == "format" and nc["shared_by"] == 3       # first seen column with the most sharing


def test_old_words_still_read():
    old = {"who": "p1", "argument": "promo", "awareness": "most-aware", "format": "montage", "face": "none",
           "setting": "kitchen", "look": "phone-ugc"}
    assert F.norm(old) == CELLS


def test_cells_set_files_and_refuses_off_list(tmp_path, monkeypatch):
    b = make(tmp_path, monkeypatch)
    lists = {"profile": ["p1"], "awareness": ["most-aware"], "angle": ["x"], "format": ["montage"], "face": ["none"],
             "setting": ["kitchen"], "look": ["phone-ugc"]}
    monkeypatch.setattr(F, "lists", lambda brand, kind="image", base=None: lists)
    import pytest
    with pytest.raises(SystemExit):
        F.cells_set(b, "brief 0001", dict(CELLS, angle="promo"), base=tmp_path)          # promo is off the list
    with pytest.raises(SystemExit):
        F.cells_set(b, "brief 0001", {k: v for k, v in CELLS.items() if k != "look"}, base=tmp_path)
    F.cells_set(b, "brief 0001", dict(CELLS, angle="new:promo"), base=tmp_path)
    assert F.live_cells(b, tmp_path)["brief 0001"]["moves"]["angle"] == "new:promo"
    # the live ad's cells now count as running and the winner gets a named column, not a tag row
    doc = F.build(b, DAY, tmp_path, today=TODAY)
    assert "1 live ads with cells" in doc["from"]["running"] or "live ads with cells" in doc["from"]["running"]


def test_any_brand_with_numbers(tmp_path, monkeypatch):
    make(tmp_path, monkeypatch)
    (tmp_path / "runs/funnel-tracking/nofolder/2026-11-28").mkdir(parents=True)
    (tmp_path / "runs/funnel-tracking/nofolder/2026-11-28/warehouse.json").write_text("{}")
    assert F.brands_with_numbers(tmp_path) == ["testbrand"]


def test_offer_from_the_brand_folder(tmp_path):
    sys.path.insert(0, str(HERE.parents[1] / "creative-diversity"))
    import matrix as M
    put(tmp_path / "brands/anybrand/products/heroes.json",
        {"heroes": ["kit"], "sellable": [{"handle": "kit", "url": "https://shop.test/kit/"}]})
    assert M.offer_of("anybrand", tmp_path) == {"product": "kit", "page": "https://shop.test/kit/", "match": ["shop.test/kit"]}
    assert M.offer_of("nothing-on-file", tmp_path) == {"product": "", "page": "", "match": []}
