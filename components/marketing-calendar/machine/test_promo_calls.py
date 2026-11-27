"""A promotion's calls reach the month from the files that already hold them (2026-11-03).

- a flat offer bank's `### ` sections are offers when they are priced, and both
  readers of the bank agree on them;
- a moment's own `offer` rides on every offer-carrying send of its arc;
- a sale moment carrying `early-access` gets one early-access send to the VIP
  segment before the sale opens;
- a gifting moment's last-chance sits on the brand's order-by date.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brandrecord as C  # noqa: E402
import marketing_calendar as CAL  # noqa: E402

FLAT_BANK = """# Offer bank

## tube — The Tube
- Price: **$29.00**

## sample — A Sample
- Price: **$0.00**

---

# Ruled by a human

### paid-funnel — The funnel offer
| The 3-pack | **$57** |

### funnel-offer-map — Every offer, front-end to post-purchase
One tube $29, the cream $39.

### holiday-sale — The holiday offer
| Offer | 3 for 2, **$57** |

### guarantee — The guarantee
60 days, $0 risk.

### rules — Standing rules
- Never invent an offer.
"""

SECTIONED_BANK = """# Offer bank

## device — The Device
- Price: **$69.99**

## THE DESTINATION IS THE QUIZ

No price here.

## Guarantees

### device-guarantee — device surfaces
> 90 days, full refund.

## Proof

### order-count — every surface
> Over 100 orders
"""

SHIPPING = """# Shipping

## Holiday order-by dates (2026)

| To arrive by | Order by | Why |
|---|---|---|
| Christmas editor (Dec 24) | **Thursday, Dec 10** | ship + transit |
| Sale orders | arrive about Dec 4–8 | same rule |
"""

MATRIX = {"segments": [{"name": "Core | Engaged 30"}, {"name": "Core | VIP Customer"}]}


def _brand(tmp, bank=FLAT_BANK, moments=(), shipping=None):
    root = Path(tmp) / "brands" / "testbrand"
    for d in ("products", "strategy", "email-sms", "operations"):
        (root / d).mkdir(parents=True)
    (root / "products" / "offer-bank.md").write_text(bank)
    (root / "strategy" / "moments.json").write_text(
        json.dumps({"avatars": {"a": {"moments": list(moments)}}}))
    (root / "email-sms" / "audience-matrix.json").write_text(json.dumps(MATRIX))
    if shipping:
        (root / "operations" / "shipping.md").write_text(shipping)
    return root


def _offers(root):
    return [ln.split("`")[1] for ln in C.render_offers(root, ["a"]).splitlines()
            if ln.startswith("- OFFER `")]


CATALOGUE = {"types": [{"key": k, "well": w, "role": r} for k, w, r in (
    ("sale-window", "ask", "asks"), ("last-chance", "ask", "recovers"),
    ("gift-guide", "ask", "asks"), ("early-access", "ask", "asks"),
    ("holiday", "belong", "earns"), ("stack", "ask", "earns"),
    ("proof-drop", "real", "earns"), ("anticipation", "belong", "earns"))]}
CELLS = {"serve": [{"segment": "Core | Engaged 30", "avatar": "a",
                    "variants": [{"avatar": "a", "angle": ""}]}]}
# the VIP segment live this month too (the cells stage's call)
CELLS_VIP = {"serve": CELLS["serve"] + [{"segment": "Core | VIP Customer", "avatar": "a",
                                         "variants": [{"avatar": "a", "angle": ""}]}]}


def test_flat_bank_reads_priced_ruled_sections_as_offers():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp)
        offers = _offers(root)
        bank = CAL.offer_bank(root, ["a"])
    assert offers == ["tube", "paid-funnel", "holiday-sale"]
    # the second reader agrees with the first, avatar by avatar
    assert bank == {"a": {"tube", "paid-funnel", "holiday-sale"}}


def test_a_product_section_ends_at_the_next_ruled_section():
    # the last product's section used to run on through every ruled section
    # below it, so a free product was priced by the prose that followed it
    bank = FLAT_BANK.replace("## sample — A Sample\n- Price: **$0.00**",
                             "## sample — A Sample\n- Link: none")
    with tempfile.TemporaryDirectory() as tmp:
        assert "sample" not in _offers(_brand(tmp, bank=bank))


def test_sectioned_bank_keeps_its_notes_as_notes():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, bank=SECTIONED_BANK)
        assert _offers(root) == ["device"]
        assert CAL.offer_bank(root, ["a"]) == {"a": {"device"}}


def _bf(**extra):
    m = {"key": "black-friday", "stream": "fixed", "evidence": "proven", "audience": "all",
         "anchor": {"holiday": "black-friday", "through": "cyber-monday"}}
    m.update(extra)
    return m


def _arcs(root, month, cells=CELLS, notes=None):
    rows = CAL.resolve_moments(root, month)
    anchors = CAL.anchor_arcs(month, rows, cells, CATALOGUE, root, [])
    anchors += CAL.holiday_fill(anchors, month, rows, CATALOGUE)
    early, said = CAL.place_early_access(anchors, month, rows, cells, CATALOGUE, root)
    if notes is not None:
        notes.extend(said)
    return anchors + early


def test_the_moments_offer_rides_on_its_arc():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[_bf(offer="holiday-sale")])
        out = _arcs(root, "2026-11")
    sells = [a for a in out if a["occasion"] == "black-friday" and a["role"] in ("asks", "recovers")]
    assert sells and all(a["offer"] == "holiday-sale" for a in sells)
    assert {a["type"] for a in sells} >= {"sale-window", "last-chance"}
    builds = [a for a in out if a.get("build_up")]
    assert all(a["offer"] == "none" for a in builds)


def test_without_a_moment_offer_the_bank_assigns():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[_bf()])
        out = _arcs(root, "2026-11")
    asks = [a for a in out if a["role"] in ("asks", "recovers")]
    assert asks and all(a["offer"] == "[ASSIGN]" for a in asks)


def test_the_moments_offer_is_still_checked_against_the_bank():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[_bf(offer="not-in-the-bank")])
        out = _arcs(root, "2026-11")
        kept, log = CAL.apply_offers(out, [], root)
    assert any("not-in-the-bank" in ln and "STRIPPED" in ln for ln in log)
    assert all(a["offer"] == "none" for a in kept)


def test_early_access_goes_to_vip_before_the_sale_opens():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[_bf(offer="holiday-sale", **{"early-access": 2})])
        out = _arcs(root, "2026-11", cells=CELLS_VIP)
    early = [a for a in out if a["type"] == "early-access"]
    assert len(early) == 1
    e = early[0]
    assert e["arc"] and e["arc"] == next(a["arc"] for a in out if a["type"] == "sale-window")
    assert e["segments"] == ["Core | VIP Customer"] and e["cell"]["segment"] == "Core | VIP Customer"
    assert e["offer"] == "holiday-sale"
    opens = min(a["_date"] for a in out if a["occasion"] == "black-friday"
                and a["role"] in ("asks", "recovers") and a is not e)
    assert e["_date"] < opens
    # Black Friday 27 Nov, live a week early (holiday-cadence lead_days 7): 20 Nov; two days before
    assert e["_date"] == "2026-11-18"


def test_no_early_access_without_the_call():
    with tempfile.TemporaryDirectory() as tmp:
        out = _arcs(_brand(tmp, moments=[_bf(offer="holiday-sale")]), "2026-11")
    assert not [a for a in out if a["type"] == "early-access"]


def test_early_access_adds_no_holiday_period_sends_of_its_own():
    with tempfile.TemporaryDirectory() as tmp:
        with_ea = _arcs(_brand(Path(tmp) / "a", moments=[_bf(offer="holiday-sale", **{"early-access": 1})]), "2026-11")
        without = _arcs(_brand(Path(tmp) / "b", moments=[_bf(offer="holiday-sale")]), "2026-11")
    strip = lambda out: sorted((a["_date"], a["type"], tuple(a["segments"])) for a in out if a["type"] != "early-access")
    assert strip(with_ea) == strip(without)


def test_early_access_dies_with_its_arc():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[_bf(**{"early-access": True})])
        out = _arcs(root, "2026-11", cells=CELLS_VIP)
        kept, _ = CAL.apply_offers(out, [], root)
    assert [a for a in out if a["type"] == "early-access"]
    assert not [a for a in kept if a["type"] == "early-access"]


def _gift(key="gifting-season"):
    return {"key": key, "stream": "seasonal", "evidence": "proposed", "audience": "all",
            "anchor": {"window": ["12-01", "12-25"], "peak": "christmas"}}


def test_order_by_dates_are_read_from_the_shipping_record():
    with tempfile.TemporaryDirectory() as tmp:
        rows = C.order_by_dates(_brand(tmp, shipping=SHIPPING), 2026)
        none = C.order_by_dates(_brand(Path(tmp) / "x"), 2026)
    assert rows == [{"arrive_by": "2026-12-24", "order_by": "2026-12-10",
                     "label": "Christmas editor (Dec 24)"}]
    assert none == []


def test_a_gifting_last_chance_sits_on_the_order_by_date():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[_gift()], shipping=SHIPPING)
        rows = CAL.resolve_moments(root, "2026-12")
        out = CAL.anchor_arcs("2026-12", rows, CELLS, CATALOGUE, root,
                              [{"key": "christmas", "name": "Christmas"}])
    close = [a for a in out if a["type"] == "last-chance"]
    ask = [a for a in out if a["type"] == "gift-guide"]
    assert len(close) == 1 and close[0]["_date"] == "2026-12-10" == close[0]["order_by"]
    assert ask and ask[0]["_date"] < close[0]["_date"]


def test_without_an_order_by_date_the_close_stays_before_the_peak():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[_gift()])
        rows = CAL.resolve_moments(root, "2026-12")
        out = CAL.anchor_arcs("2026-12", rows, CELLS, CATALOGUE, root,
                              [{"key": "christmas", "name": "Christmas"}])
    close = [a for a in out if a["type"] == "last-chance"]
    assert len(close) == 1 and close[0]["_date"] == "2026-12-23" and "order_by" not in close[0]


def test_order_by_follows_the_shipping_record_not_the_moments_name():
    # a moment called anything at all: the order-by row covering its peak is what moves the close
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[_gift("year-end-giving")], shipping=SHIPPING)
        rows = CAL.resolve_moments(root, "2026-12")
        out = CAL.anchor_arcs("2026-12", rows, CELLS, CATALOGUE, root,
                              [{"key": "christmas", "name": "Christmas"}])
    assert [a["_date"] for a in out if a["type"] == "last-chance"] == ["2026-12-10"]


def test_a_sale_no_order_by_row_covers_keeps_its_close():
    with tempfile.TemporaryDirectory() as tmp:
        out = _arcs(_brand(tmp, moments=[_bf(offer="holiday-sale")], shipping=SHIPPING), "2026-11")
    close = [a for a in out if a["type"] == "last-chance"]
    assert close and all("order_by" not in a for a in close)


def test_every_call_works_on_any_moment():
    # the same three calls on a spring window with a peak: nothing is special to one moment
    spring = {"key": "spring-reset", "stream": "seasonal", "evidence": "proposed", "audience": "all",
              "anchor": {"window": ["03-20", "04-10"], "peak": "easter"},
              "offer": "holiday-sale", "early-access": 3}
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[spring])
        out = _arcs(root, "2027-03", cells=CELLS_VIP)
    sells = [a for a in out if a["role"] in ("asks", "recovers") and a["type"] != "early-access"]
    early = [a for a in out if a["type"] == "early-access"]
    assert sells and all(a["offer"] == "holiday-sale" for a in sells)
    assert len(early) == 1 and early[0]["segments"] == ["Core | VIP Customer"]
    assert early[0]["_date"] < min(a["_date"] for a in sells)


def test_the_moments_early_access_goes_to_vip_even_when_the_cells_left_it_out():
    # the moment's own call wins for this one send (2026-11-04); it says so, and no other send goes there
    notes = []
    with tempfile.TemporaryDirectory() as tmp:
        out = _arcs(_brand(tmp, moments=[_bf(offer="holiday-sale", **{"early-access": 1})]), "2026-11",
                    cells=CELLS, notes=notes)
    early = [a for a in out if a["type"] == "early-access"]
    assert [a["segments"] for a in early] == [["Core | VIP Customer"]] and early[0]["early_access_call"]
    assert len(notes) == 1 and "did not make live" in notes[0]
    assert not [a for a in out if a["type"] != "early-access" and "Core | VIP Customer" in a["segments"]]


def test_early_access_on_a_gifting_window_is_the_day_before_its_ask():
    m = dict(_gift(), offer="holiday-sale", **{"early-access": 1})
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[m])
        rows = CAL.resolve_moments(root, "2026-12")
        anchors = CAL.anchor_arcs("2026-12", rows, CELLS_VIP, CATALOGUE, root,
                                  [{"key": "christmas", "name": "Christmas"}])
        early, _ = CAL.place_early_access(anchors, "2026-12", rows, CELLS_VIP, CATALOGUE, root)
    ask = [a for a in anchors if a["type"] == "gift-guide"]
    assert [(e["_date"], e["offer"]) for e in early] == [("2026-12-18", "holiday-sale")]
    assert ask and ask[0]["_date"] == "2026-12-19"


def test_no_holiday_period_ask_lands_on_or_after_the_close():
    with tempfile.TemporaryDirectory() as tmp:
        out = _arcs(_brand(tmp, moments=[_bf(offer="holiday-sale")]), "2026-11")
    close = max(a["_date"] for a in out if a["type"] == "last-chance")
    late = [a for a in out if a["_date"] >= close and a["role"] == "asks"]
    assert not late, late
    assert len([a for a in out if a["_date"] == close]) >= 2          # the day still carries its sends


def test_holiday_period_sends_take_their_types_well_and_role():
    with tempfile.TemporaryDirectory() as tmp:
        out = _arcs(_brand(tmp, moments=[_bf(offer="holiday-sale")]), "2026-11")
    spec = {t["key"]: t for t in CATALOGUE["types"]}
    extra = [a for a in out if a["anchor_id"].startswith("H")]
    assert extra and all(a["category"] == C.CATEGORY[spec[a["type"]]["well"]]
                         and a["role"] == spec[a["type"]]["role"] for a in extra)
    assert {a["arc"] for a in extra} == {next(a["arc"] for a in out if a["type"] == "sale-window")}


def _slot(i, d, role, typ="sale-window", arc="A1", offer="holiday-sale"):
    return {"id": f"s{i}", "date": d, "role": role, "type": typ, "offer": offer, "arc": arc,
            "segment": "S", "segments": ["S"]}


def _arc_breaks(slots):
    errs, _ = C.check(slots, "2026-11", {}, Path("/nonexistent"), set())
    return [e for e in errs if "WARM-UP" in e or "COOL-DOWN" in e]


def test_an_ask_inside_its_arc_has_the_arcs_warm_up_and_close():
    arc = [_slot(1, "2026-11-18", "earns", "holiday", offer="none"), _slot(2, "2026-11-20", "asks"),
           _slot(3, "2026-11-21", "asks"), _slot(4, "2026-11-30", "recovers", "last-chance")]
    assert _arc_breaks(arc) == []
    # still a break without the arc's close, or without its warm-up, or in another arc
    assert len(_arc_breaks(arc[:3])) == 2
    assert len(_arc_breaks(arc[1:])) == 2
    assert len(_arc_breaks(arc[:2] + [_slot(3, "2026-11-21", "asks", arc="A2")] + arc[3:])) == 2


def test_needs_are_filled_from_the_record_only():
    cat = {"types": CATALOGUE["types"] + [{"key": "spotlight-x", "well": "ask", "role": "asks",
                                           "needs": ["product_file"]},
                                          {"key": "guarantee", "well": "ask", "role": "recovers",
                                           "needs": ["offer_file"]}]}
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, bank=FLAT_BANK.replace("## tube — The Tube", "## tube — The Tube\n_lane: a_  ·  _hero: paid_"))
        (root / "products" / "tube.md").write_text("# The Tube\n")
        with mock.patch.object(CAL, "L_avatars", return_value=[{"key": "a"}]):
            mv = [{"type": "spotlight-x", "offer": "none", "product": "none", "variants": [{"avatar": "a"}]},
                  {"type": "spotlight-x", "offer": "none", "product": "none", "variants": [{"avatar": "b"}]},
                  {"type": "guarantee", "offer": "none", "product": "tube", "variants": [{"avatar": "a"}]}]
            CAL.fill_needs(mv, root, cat)
    assert mv[0]["product"] == "tube"                 # the lane's hero, from the bank
    assert mv[1]["product"] == "tube"                 # the brand's one hero
    assert mv[2]["offer"] == "tube"                   # the product is itself an offer


def _sms(out, cad):
    return CAL.sms_beats(out, [{"key": "black-friday", "in_month": True, "start": "2026-11-27"}], cad)


SMS_CAD = {"beats": ["last-chance", "early-access", "open", "peak"], "daily_cap": 1, "hour": 22,
           "quiet_hours": {"from": 21, "to": 9}, "content_moments": []}


def test_sms_twins_the_sale_beats_with_the_same_offer_and_audience():
    with tempfile.TemporaryDirectory() as tmp:
        out = _arcs(_brand(tmp, moments=[_bf(offer="holiday-sale", **{"early-access": 1})]), "2026-11",
                    cells=CELLS_VIP)
    sms = _sms(out, SMS_CAD)
    got = {x["sms_beat"]: x for x in sms}
    assert set(got) == {"early-access", "open", "peak", "last-chance"}
    assert all(x["channel"] == "sms" and x["offer"] == "holiday-sale" and x["arc"] for x in sms)
    assert got["early-access"]["segments"] == ["Core | VIP Customer"]
    assert got["peak"]["_date"] == "2026-11-27" and got["last-chance"]["type"] == "last-chance"
    assert all(x["_hour"] == 9 for x in sms)                 # 22:00 is inside quiet hours: moved to 9
    assert not any(a.get("channel") == "sms" for a in out)   # the emails are untouched


def test_sms_daily_cap_keeps_the_earlier_beat():
    with tempfile.TemporaryDirectory() as tmp:
        out = _arcs(_brand(tmp, moments=[_bf(offer="holiday-sale")]), "2026-11")
    one_beat_a_day = dict(SMS_CAD, beats=["peak", "open"])
    sms = _sms(out, one_beat_a_day)
    days = [(x["_date"], tuple(x["segments"])) for x in sms]
    assert len(days) == len(set(days))
    # open and peak never share a day here; with peak first and a cap of one, each day carries one
    assert {x["sms_beat"] for x in sms} == {"open", "peak"}


def test_a_content_moment_gets_no_sms_unless_the_cadence_names_it():
    a = {"anchor_id": "A1", "occasion": "game-day", "type": "moment", "role": "earns", "offer": "none",
         "_date": "2026-11-15", "segments": ["S"], "cell": {"segment": "S"}}
    rows = [{"key": "game-day", "in_month": True, "start": "2026-11-15"}]
    assert CAL.sms_beats([a], rows, SMS_CAD) == []
    named = CAL.sms_beats([a], rows, dict(SMS_CAD, content_moments=["game-day"]))
    assert [(x["channel"], x["_date"]) for x in named] == [("sms", "2026-11-15")]


def test_an_sms_slot_is_kept_apart_from_its_email_twin():
    email = {"id": "x-01", "date": "2026-11-20", "type": "sale-window", "occasion": "black-friday",
             "product": "p", "offer": "o", "segment": "S", "segments": ["S"], "variants": [], "avatar": "a",
             "why": "", "channel": "email"}
    sms = dict(email, id="x-02", channel="sms")
    merged, _ = CAL.merge_sends([email, sms], "x")
    assert sorted(s["channel"] for s in merged) == ["email", "sms"]


def test_an_sms_is_the_companion_of_an_email():
    email = _slot(1, "2026-11-20", "asks")
    email.update(channel="email", id="e1")
    sms_ok = dict(_slot(2, "2026-11-20", "asks"), id="t1", channel="sms", follows="e1")
    lone = dict(_slot(3, "2026-11-21", "asks"), id="t2", channel="sms", follows=None)
    errs, _ = C.check([email, sms_ok, lone], "2026-11", {}, Path("/nonexistent"), set())
    comp = [e for e in errs if "companion" in e]
    assert len(comp) == 1 and comp[0].startswith("t2:")


def test_sms_jobs_and_replies_come_from_the_cadence_and_the_brand():
    cad = dict(SMS_CAD, jobs={"early-access": "engagement", "open": "engagement", "peak": "reminder",
                              "last-chance": "reminder"}, reply_beats=["peak"],
               reply_platforms={"klaviyo": "keywords"})
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, moments=[_bf(offer="holiday-sale")])
        out = _arcs(root, "2026-11")
        rows = [{"key": "black-friday", "in_month": True, "start": "2026-11-27"}]
        plain = {x["sms_beat"]: x["sms_job"] for x in CAL.sms_beats(out, rows, cad, brand_root=root)}
        (root / "operations" / "brand.json").write_text(json.dumps({"sms_platform": "klaviyo",
                                                                    "sms_reply_keyword": "YES"}))
        replies = {x["sms_beat"]: (x["sms_job"], x.get("reply_keyword"))
                   for x in CAL.sms_beats(out, rows, cad, brand_root=root)}
    assert plain["peak"] == "reminder" and plain["last-chance"] == "reminder" and plain["open"] == "engagement"
    assert replies["peak"] == ("reply", "YES") and replies["open"] == ("engagement", None)


def test_a_storefront_order_note_is_never_an_offer_even_when_it_names_a_price():
    bank = FLAT_BANK.replace("### rules — Standing rules", "### storefront-order — What leads, in order\n"
                             "Lead with the set, then the tube at its store price, not the funnel's starting at $19.\n\n"
                             "### rules — Standing rules")
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, bank=bank)
        assert "storefront-order" not in _offers(root)
        assert "storefront-order" not in CAL.offer_bank(root, ["a"])["a"]


def test_a_sales_sends_lead_with_the_storefront_orders_first_product():
    bank = FLAT_BANK.replace("### rules — Standing rules", "### storefront-order — What leads\nLead with **tube** first.\n\n"
                             "### rules — Standing rules")
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, bank=bank)
        (root / "products" / "tube.md").write_text("# The Tube\n")
        assert C.lead_products(root) == ["tube"]
        with mock.patch.object(CAL, "L_avatars", return_value=[{"key": "a"}]):
            mv = [{"type": "sale-window", "offer": "holiday-sale", "product": "none", "arc": "A1", "variants": []},
                  {"type": "sale-window", "offer": "tube", "product": "none", "arc": "A1", "variants": []},
                  {"type": "moment", "offer": "none", "product": "none", "arc": None, "variants": []}]
            CAL.fill_needs(mv, root, CATALOGUE)
    assert [m["product"] for m in mv] == ["tube", "tube", "none"]


def test_the_sign_up_popup_is_never_an_offer_a_send_carries():
    bank = FLAT_BANK.replace("### rules — Standing rules", "### popup — Standing sign-up pop-up offer\n"
                             "| Opt-in | **Free pouch with the tube** (at $0.00) — worth $19 |\n\n"
                             "### rules — Standing rules")
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, bank=bank)
        assert "popup" not in _offers(root)
        assert "popup" not in CAL.offer_bank(root, ["a"])["a"]


MIX_BANK = FLAT_BANK.replace("### rules — Standing rules", """### storefront-order — What leads
Lead with **the-set** first, then **tube**.

- **Lead sends mix the Set and the Tube** across every audience in a promo, not one lane each.
- **Set sends** carry the set and the option to buy each one on its own: **cream**
  and **tube**.

### rules — Standing rules""").replace("## tube — The Tube", "## the-set — The Set\n- Price: **$57.00**\n\n## tube — The Tube")


def test_the_brands_mix_is_read_from_its_storefront_order_note():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, bank=MIX_BANK)
        for k, title in (("the-set", "The Set"), ("tube", "The Tube"), ("cream", "The Cream")):
            (root / "products" / f"{k}.md").write_text(f"# {title}\n")
        got = C.storefront_mix(root)
        assert got == {"lead": ["the-set", "tube"], "singles": {"the-set": ["cream", "tube"]}}
        with mock.patch.object(CAL, "L_avatars", return_value=[{"key": "a"}]):
            mv = [{"type": "sale-window", "offer": "the-set", "product": "none", "arc": "A1", "variants": []},
                  {"type": "sale-window", "offer": "the-set", "product": "none", "arc": "A1", "channel": "sms", "variants": []},
                  {"type": "bundle", "offer": "the-set", "product": "none", "arc": None, "variants": []},
                  {"type": "sale-window", "offer": "tube", "product": "none", "arc": None, "variants": []}]
            CAL.fill_needs(mv, root, CATALOGUE)
    assert mv[0]["offer_mix"] == ["the-set", "tube"]               # a promo's lead email: the lead mix
    assert "offer_mix" not in mv[1]                                # a text keeps its one offer
    assert mv[2]["offer_mix"] == ["the-set", "cream", "tube"]      # a set's email: the set and its singles
    assert "offer_mix" not in mv[3]


def test_a_bank_with_no_mix_changes_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp)
        assert C.storefront_mix(root) == {"lead": [], "singles": {}}


def _week_slots():
    mk = lambda i, d, t, role="earns", **kw: dict({"id": f"s{i}", "date": d, "type": t, "role": role, "offer": "none",
                                                  "product": "none", "channel": "email", "why": ""}, **kw)
    return [mk(1, "2026-11-02", "routine"), mk(2, "2026-11-04", "guarantee", "recovers"),
            mk(3, "2026-11-05", "routine"), mk(4, "2026-11-10", "routine"), mk(5, "2026-11-12", "routine"),
            mk(6, "2026-11-16", "routine", offer="tube")]


WEEK_CAT = {"types": [{"key": "routine", "well": "help", "role": "earns"},
                      {"key": "guarantee", "well": "ask", "role": "recovers", "needs": ["offer_file"]}]}


def test_every_week_ahead_sells_the_standing_offer():
    bank = MIX_BANK
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, bank=bank)
        for k, title in (("the-set", "The Set"), ("tube", "The Tube"), ("cream", "The Cream")):
            (root / "products" / f"{k}.md").write_text(f"# {title}\n")
        slots = _week_slots()
        with mock.patch.object(CAL, "L_avatars", return_value=[{"key": "a"}]):
            import datetime
            CAL.weekly_standing_offer(slots, root, WEEK_CAT, on=datetime.date(2026, 11, 3))
    by = {s["id"]: s for s in slots}
    assert by["s1"]["offer"] == "none"                    # a past send is never rewritten
    assert by["s2"]["offer"] == "the-set" and by["s2"]["offer_mix"] == ["the-set", "tube"]  # the type that needs one
    assert by["s5"]["offer"] == "the-set" and by["s4"]["offer"] == "none"   # the week's last earning send, once
    assert by["s6"]["offer"] == "tube"                    # a week already selling is left alone


def test_a_brand_with_a_paid_funnel_stands_on_it():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp)
        assert C.standing_offer(root, ["a"])[0] == "paid-funnel"


def test_the_storefront_orders_first_product_stands_even_with_no_product_file():
    bank = FLAT_BANK.replace("### rules — Standing rules", "### storefront-order — What leads\nEvery email leads with **tube**.\n\n"
                             "### rules — Standing rules")
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, bank=bank)
        assert C.lead_products(root) == ["tube"]            # in the bank, no product file yet
        assert C.standing_offer(root, ["a"]) == ("tube", None, "tube")   # wins over the paid-funnel section


def test_a_type_needing_an_offer_takes_the_storefront_orders_lead():
    bank = FLAT_BANK.replace("### rules — Standing rules", "### storefront-order — What leads\nEvery email leads with **tube**.\n\n"
                             "### rules — Standing rules")
    cat = {"types": [{"key": "guarantee", "well": "ask", "role": "recovers", "needs": ["offer_file"]}]}
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp, bank=bank)
        with mock.patch.object(CAL, "L_avatars", return_value=[{"key": "a"}]):
            mv = [{"type": "guarantee", "offer": "none", "product": "paid-funnel", "variants": []}]
            CAL.fill_needs(mv, root, cat)
    assert mv[0]["offer"] == "tube"


def test_a_past_week_is_left_alone():
    with tempfile.TemporaryDirectory() as tmp:
        root = _brand(tmp)
        slots = _week_slots()[:1]
        with mock.patch.object(CAL, "L_avatars", return_value=[{"key": "a"}]):
            import datetime
            assert CAL.weekly_standing_offer(slots, root, WEEK_CAT, on=datetime.date(2026, 11, 20)) == []
    assert slots[0]["offer"] == "none"


def test_early_access_stands_on_its_arc_when_vip_is_not_live():
    a = dict(_slot(1, "2026-11-18", "earns", "holiday", offer="none"))
    e = dict(_slot(2, "2026-11-19", "asks", "early-access"), segment="VIP", segments=["VIP"], early_access_call=True)
    o = _slot(3, "2026-11-20", "asks")
    c = _slot(4, "2026-11-30", "recovers", "last-chance")
    errs, _ = C.check([a, e, o, c], "2026-11", {}, Path("/nonexistent"), set(), cells={"serve": [{"segment": "S"}]})
    assert not [x for x in errs if x.startswith("s2:") and ("WARM" in x or "COOL" in x or "live" in x)]
    plain = dict(e, early_access_call=None, type="sale-window")
    errs, _ = C.check([a, plain, o, c], "2026-11", {}, Path("/nonexistent"), set(), cells={"serve": [{"segment": "S"}]})
    assert [x for x in errs if x.startswith("s2:") and "live" in x]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
