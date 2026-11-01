"""A moment anchored to one real `date` lands as one cultural send on that day (2026-10-13)."""
import datetime
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marketing_calendar as CAL  # noqa: E402


def _brand(tmp, moments):
    root = Path(tmp) / "brands" / "testbrand"
    (root / "strategy").mkdir(parents=True)
    (root / "strategy" / "moments.json").write_text(json.dumps({"avatars": {"a": {"moments": moments}}}))
    return root


def test_date_anchor_resolves_in_its_month_only():
    m = {"key": "nba-christmas-games", "stream": "sports", "evidence": "proposed", "audience": "a",
         "anchor": {"date": "2026-12-25"}}
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, [m])
        dec = [r for r in CAL.resolve_moments(root, "2026-12") if r["key"] == m["key"]][0]
        nov = [r for r in CAL.resolve_moments(root, "2026-11") if r["key"] == m["key"]][0]
    assert dec["in_month"] and dec["start"] == dec["end"] == dec["peak"] == "2026-12-25"
    assert dec["kind"] == "holiday" and dec["holiday_kind"] == "observance"
    assert not nov["in_month"]


def test_date_anchor_pins_one_moment_send_on_the_day():
    m = {"key": "nba-christmas-games", "stream": "sports", "evidence": "proposed", "audience": "a",
         "anchor": {"date": "2026-12-25"}}
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, [m])
        rows = CAL.resolve_moments(root, "2026-12")
    cells = {"serve": [{"segment": "S1", "avatar": "a", "variants": [{"avatar": "a", "angle": ""}]}]}
    out = CAL.anchor_arcs("2026-12", rows, cells, {"types": []})
    assert [(x["type"], x["_date"], x["offer"]) for x in out] == [("moment", "2026-12-25", "none")]


def test_culture_days_are_the_day_or_the_day_before():
    rows = [{"key": "cma-awards", "kind": "holiday", "holiday_kind": "observance", "in_month": True,
             "start": "2026-11-18", "end": "2026-11-18"},
            {"key": "black-friday", "kind": "holiday", "holiday_kind": "retail", "in_month": True,
             "start": "2026-11-27", "end": "2026-11-30"}]
    hol = [{"key": "veterans-day", "start": "2026-11-11", "end": "2026-11-11", "kind": "observance"}]
    w = CAL.moment_windows(rows, hol_rows=hol)
    assert w["cma-awards"] == [("2026-11-17", "2026-11-18")]
    assert w["veterans-day"] == [("2026-11-10", "2026-11-11")]
    assert w["black-friday"] == [("2026-11-16", "2026-11-30")]      # a sale keeps its run-up


if __name__ == "__main__":
    test_culture_days_are_the_day_or_the_day_before()
    test_date_anchor_resolves_in_its_month_only()
    test_date_anchor_pins_one_moment_send_on_the_day()
    print("ok")
