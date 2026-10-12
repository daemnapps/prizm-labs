#!/usr/bin/env python3
"""The public holidays — real dates, computed per year. Layer 1 of the
calendar (the owner, 2026-09-02: "ground up the calendar fundamentally, fill in
proper public holidays that all avatars are aware of").

    python3 holidays.py 2026            # every holiday that year, dated
    python3 holidays.py 2026-11         # the ones landing in one month

These are calendar FACTS, not brand opinions, so they live in the tool:
when Thanksgiving falls is the same for every brand. WHICH of them a brand
plans against is the brand's call and lives in its own calendar/moments.json
— an entry there anchored to a holiday key below takes its date from here.

Every holiday carries a `kind`:
  retail       a commerce moment — people expect offers (Black Friday)
  observance   a day people mark, not a shopping day (Veterans Day)
  season-open  a date that opens a season more than it is a day (Labor Day)
and a `span`, in days, for the ones that are a window rather than a day.
"""
import datetime as _dt
import json
import sys


def _nth_weekday(year, month, weekday, n):
    """n-th <weekday> (Mon=0) of a month; n=-1 for the last."""
    if n > 0:
        d = _dt.date(year, month, 1)
        d += _dt.timedelta(days=(weekday - d.weekday()) % 7)
        return d + _dt.timedelta(weeks=n - 1)
    d = _dt.date(year + (month == 12), (month % 12) + 1, 1) - _dt.timedelta(days=1)
    return d - _dt.timedelta(days=(d.weekday() - weekday) % 7)


def _easter(year):
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return _dt.date(year, month, day)


def table(year):
    """Every public holiday of the year, dated. Ordered by date."""
    tg = _nth_weekday(year, 11, 3, 4)          # Thanksgiving: 4th Thursday
    rows = [
        ("new-years-day",     "New Year's Day",        _dt.date(year, 1, 1),  "observance", 1),
        ("mlk-day",           "MLK Day",               _nth_weekday(year, 1, 0, 3), "observance", 1),
        ("valentines-day",    "Valentine's Day",       _dt.date(year, 2, 14), "retail", 1),
        ("presidents-day",    "Presidents' Day",       _nth_weekday(year, 2, 0, 3), "retail", 1),
        ("st-patricks-day",   "St. Patrick's Day",     _dt.date(year, 3, 17), "observance", 1),
        ("easter",            "Easter",                _easter(year),         "observance", 1),
        ("mothers-day",       "Mother's Day",          _nth_weekday(year, 5, 6, 2), "retail", 1),
        ("memorial-day",      "Memorial Day",          _nth_weekday(year, 5, 0, -1), "season-open", 1),
        ("fathers-day",       "Father's Day",          _nth_weekday(year, 6, 6, 3), "retail", 1),
        ("juneteenth",        "Juneteenth",            _dt.date(year, 6, 19), "observance", 1),
        ("independence-day",  "Independence Day",      _dt.date(year, 7, 4),  "season-open", 1),
        ("labor-day",         "Labor Day",             _nth_weekday(year, 9, 0, 1), "season-open", 1),
        ("halloween",         "Halloween",             _dt.date(year, 10, 31), "retail", 1),
        ("veterans-day",      "Veterans Day",          _dt.date(year, 11, 11), "observance", 1),
        ("thanksgiving",      "Thanksgiving",          tg,                    "observance", 1),
        ("black-friday",      "Black Friday",          tg + _dt.timedelta(days=1), "retail", 1),
        ("small-business-saturday", "Small Business Saturday", tg + _dt.timedelta(days=2), "retail", 1),
        ("cyber-monday",      "Cyber Monday",          tg + _dt.timedelta(days=4), "retail", 1),
        ("cyber-week",        "Cyber Week (Thanksgiving through Cyber Monday)",
                                                       tg,                    "retail", 5),
        ("christmas-eve",     "Christmas Eve",         _dt.date(year, 12, 24), "retail", 1),
        ("christmas",         "Christmas",             _dt.date(year, 12, 25), "retail", 1),
        ("new-years-eve",     "New Year's Eve",        _dt.date(year, 12, 31), "observance", 1),
    ]
    out = []
    for key, name, start, kind, span in rows:
        end = start + _dt.timedelta(days=span - 1)
        out.append({"key": key, "name": name, "start": start.isoformat(),
                    "end": end.isoformat(), "kind": kind, "span": span})
    return sorted(out, key=lambda r: r["start"])


def by_key(year):
    return {r["key"]: r for r in table(year)}


def in_month(month, lead_in_days=5):
    """Holidays landing in YYYY-MM — plus any in the first `lead_in_days` of
    the NEXT month, because their warm-up belongs to this one (a January 1
    arc is built in December)."""
    y, mo = int(month[:4]), int(month[5:7])
    first = _dt.date(y, mo, 1)
    nxt = _dt.date(y + (mo == 12), (mo % 12) + 1, 1)
    horizon = nxt + _dt.timedelta(days=lead_in_days)
    years = {y, nxt.year}
    hits = []
    for yr in sorted(years):
        for r in table(yr):
            s = _dt.date.fromisoformat(r["start"])
            e = _dt.date.fromisoformat(r["end"])
            if (first <= s < horizon) or (s < first <= e):
                r = dict(r, lead_in=(s >= nxt))
                hits.append(r)
    return hits


def render(rows):
    if not rows:
        return "(no public holiday lands in this month)"
    lines = []
    for r in rows:
        when = r["start"] if r["span"] == 1 else f"{r['start']} to {r['end']}"
        lines.append(f"- `{r['key']}` — {r['name']} · {when} · {r['kind']}"
                     + (" · lead-in: falls in the first days of next month, "
                        "its run-up belongs here" if r.get("lead_in") else ""))
    return "\n".join(lines)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else str(_dt.date.today().year)
    rows = in_month(arg) if "-" in arg else table(int(arg))
    print(render(rows))
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=1))
