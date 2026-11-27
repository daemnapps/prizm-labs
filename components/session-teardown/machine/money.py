"""What a finding is worth, in dollars a month — so fixes and big swings are ranked by money, not by taste.

    gap        share of visitors who LEFT showing it, minus share of visitors who REACHED CHECKOUT showing it
    visitors   gap × the visitors the page lost in the window, scaled to 30 days
    at stake   those visitors × what a visitor who reaches checkout is worth (revenue per reacher)

It is an upper bound: it assumes every one of those visitors would have reached checkout like the rest. Use it to
rank, never as a forecast; the 50/50 test says what a change is really worth.
"""


def price(left, converted, n_left, n_converted, lost, value_per_reacher, days):
    n_left, n_converted = max(int(n_left), 1), max(int(n_converted), 1)
    left = min(max(int(left or 0), 0), n_left)
    converted = min(max(int(converted or 0), 0), n_converted)
    gap = max(0.0, left / float(n_left) - converted / float(n_converted))
    visitors = gap * max(int(lost), 0) * 30.0 / max(int(days), 1)
    usd = round(visitors * float(value_per_reacher or 0), 2)
    basis = ("gap %.0f%% (%d of %d who left, %d of %d who reached checkout) × %d visitors lost in %d days × 30/%d "
             "× $%.2f per visitor who reached checkout = $%s a month; an upper bound, for ranking" % (
                 100 * gap, left, n_left, converted, n_converted, max(int(lost), 0), max(int(days), 1),
                 max(int(days), 1), float(value_per_reacher or 0), format(int(usd), ",")))
    return {"gap": round(gap, 3), "visitors_month": int(round(visitors)), "at_stake_month": usd, "basis": basis}
