"""Step 1 — find the leak: which page loses the most people before checkout, priced in money.

For every page on the landing or cart step: visitors (sessions that viewed it) and how many LEFT THERE — their last
landing/cart page was this one and they never reached checkout (checkout_click, checkout_reached or a purchase).
Everyone else moved on (to the next page or to checkout) and counts as reached_next. A visitor is lost on the page
they left from, never on an earlier page they passed through. Each lost visitor is priced by what a visitor who
reaches checkout is worth. Worth = the
brand's revenue per visitor who reached checkout, so `at_stake` = lost visitors × that. Pages under the
`min_visitors` floor are listed but not ranked: too few visits to read.
"""
REACH = ("checkout_click", "checkout_reached", "purchase")
STEPS = ("landing", "cart")


def find(page_views, outcomes, min_visitors=200):
    first_view = {}                      # (page, session) -> first time it was seen
    step_of = {}
    for v in page_views:
        if v["step"] not in STEPS or not v["page_id"]:
            continue
        k = (v["page_id"], v["session"])
        if k not in first_view or v["at"] < first_view[k]:
            first_view[k] = v["at"]
        step_of[v["page_id"]] = v["step"]
    reached_at, revenue = {}, {}
    for o in outcomes:
        if o["event"] in REACH:
            s = o["session"]
            reached_at[s] = min(reached_at.get(s, o["at"]), o["at"])
        if o["event"] == "purchase":
            revenue[o["session"]] = revenue.get(o["session"], 0.0) + float(o.get("revenue") or 0)
    reachers = [s for s in reached_at]
    value = (sum(revenue.values()) / len(reachers)) if reachers else 0.0
    last_page = {}                       # session -> (time, page) of its last landing/cart page view
    for (page, sess), at in first_view.items():
        if sess not in last_page or at > last_page[sess][0]:
            last_page[sess] = (at, page)
    pages = {}
    for (page, s), at in first_view.items():
        p = pages.setdefault(page, {"page_id": page, "step": step_of[page], "visitors": 0, "reached_next": 0,
                                    "revenue": 0.0, "left_sessions": [], "converted_sessions": []})
        p["visitors"] += 1
        p["revenue"] += revenue.get(s, 0.0)
        if s in reached_at and reached_at[s] >= at:
            p["reached_next"] += 1
            p["converted_sessions"].append(s)
        elif last_page[s][1] == page:
            p["left_sessions"].append(s)
        else:
            p["reached_next"] += 1      # moved on to a later page, lost (if at all) there
    out = []
    for p in pages.values():
        lost = p["visitors"] - p["reached_next"]
        p["reach_rate"] = round(p["reached_next"] / p["visitors"], 4) if p["visitors"] else 0.0
        p["revenue_per_visitor"] = round(p["revenue"] / p["visitors"], 2) if p["visitors"] else 0.0
        p["at_stake"] = round(lost * value, 2)
        p["ranked"] = p["visitors"] >= min_visitors
        out.append(p)
    out.sort(key=lambda p: (not p["ranked"], -p["at_stake"], -p["visitors"]))
    return {"value_per_reacher": round(value, 2), "pages": out}
