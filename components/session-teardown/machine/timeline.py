"""Step 3a — one recording read moment by moment, in the video teardown's FRAME MAP shape.

video-teardown's frame map (machine/framemap.py) reads a video as SHOTS (the stretch between two cuts) and, inside
each shot, MOMENTS — {t, does} rows in time order, a new row every time something visible changes. A recording is
read the same way: a shot is the stretch on one page (the cut is the next page view), a moment is one thing the
visitor did, with its second. Where the page under test has a page map (sections.py), the deepest scroll is named
as a section ("furthest §6 offer box") instead of a bare percentage.

Built from the session's own events (page views, taps with their text, rage taps, how far each page was scrolled,
the funnel's events), not from video. Time is seconds from the first event. The last line says how it ended.
"""
from datetime import datetime
from urllib.parse import urlparse

import sections as S

LABEL = {"$pageview": "opened", "$autocapture": "tapped", "$rageclick": "RAGE-TAPPED", "$dead_click": "tapped (nothing happened)",
         "checkout_click": "tapped into checkout", "checkout_reached": "reached checkout", "add_to_cart": "added to cart",
         "purchase": "BOUGHT", "upsell_purchase": "took an upsell", "$pageleave": "left page"}


def _t(s):
    s = str(s).replace("Z", "+00:00").replace(" ", "T")
    try:
        return datetime.fromisoformat(s[:26] if "+" not in s[19:] else s)
    except ValueError:
        return datetime.fromisoformat(s[:19])


def _same(a, b):
    return (a or "/").rstrip("/") == (b or "/").rstrip("/")


def build(session, events, meta=None, page_path=None, page_map=None):
    """-> {session, lines, ended, seconds, shots: [{id, page, start, end, seconds, moments: [{t, does}]}],
    furthest: the page under test's deepest section reached (label) or None, depth: its scroll %}."""
    meta = meta or {}
    if not events:
        return {"session": session, "lines": ["(no events)"], "ended": "unknown", "seconds": 0, "shots": [],
                "furthest": None, "depth": None}
    t0 = _t(events[0]["at"])
    lines, shots, ended, last = [], [], "left", 0
    furthest, depth = None, None
    for e in events:
        sec = max(0, int((_t(e["at"]) - t0).total_seconds()))
        last = sec
        what = LABEL.get(e["event"])
        if what is None:
            continue
        path = urlparse(e.get("url") or "").path or ""
        if e["event"] == "$pageview" or not shots:              # a new page is a cut: a new shot starts
            if shots:
                shots[-1]["end"] = sec
            shots.append({"id": "P%d" % (len(shots) + 1), "page": path, "start": sec, "end": sec, "moments": []})
        bits = [what]
        if e["event"] in ("$pageview", "$pageleave"):
            bits.append(path)
        text = (e.get("text") or "").strip().replace("\n", " ")
        if text:
            bits.append('"%s"' % text[:80])
        if e["event"] == "$pageleave" and e.get("scroll") is not None:
            pct = int(float(e["scroll"]))
            bits.append("scrolled %d%%" % pct)
            if page_path and _same(path, page_path):
                depth = pct if depth is None else max(depth, pct)
                sec_at = S.at(page_map, pct)
                if sec_at:
                    furthest = sec_at["label"]
                    bits.append("· furthest %s" % sec_at["label"])
        does = " ".join(bits)
        lines.append("%4ds  %s" % (sec, does))
        shots[-1]["moments"].append({"t": sec, "does": does})
        shots[-1]["end"] = sec
        if e["event"] == "purchase":
            ended = "bought"
        elif e["event"] in ("checkout_reached", "checkout_click") and ended != "bought":
            ended = "reached checkout"
    for s in shots:
        s["seconds"] = s["end"] - s["start"]
    lines.append("%4ds  END: %s · %d taps · %ss active" % (last, ended, meta.get("clicks", 0), meta.get("active_s", "?")))
    return {"session": session, "lines": lines, "ended": ended, "seconds": last, "shots": shots,
            "furthest": furthest, "depth": depth}


def as_text(tl, group):
    return "### %s · %s\n%s\n" % (tl["session"], group, "\n".join(tl["lines"]))


def markdown(doc):
    """The moment map as one readable file, the frame map's FRAME-MAP.md layout: one block per recording, one
    table per shot."""
    L = ["# Moment map — %s (%d recordings)" % (doc["page_id"], len(doc["recordings"])), "",
         "Each recording read as shots (one page each) and moments (one thing the visitor did, with its second). "
         "Deepest scroll on the page under test is named as a section of its page map (an estimate from section "
         "length).", ""]
    for r in doc["recordings"]:
        L += ["## %s · %s · %s · %ds" % (r["session"], r["group"], r["ended"], r["seconds"])
              + (" · furthest %s (%s%%)" % (r["furthest"], r["depth"]) if r.get("furthest") else ""), ""]
        for s in r["shots"]:
            L += ["**%s · %s · %d–%d s**" % (s["id"], s["page"] or "(page)", s["start"], s["end"]), "",
                  "| t | does |", "|---|---|"]
            L += ["| %s | %s |" % (m["t"], m["does"].replace("|", "/")) for m in s["moments"]]
            L.append("")
    return "\n".join(L) + "\n"
