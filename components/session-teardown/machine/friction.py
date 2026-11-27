"""Friction, counted in code before any model reads a recording: what people tapped that fought back.

Per tapped element (by the words on it), in each group, how many recordings show:
    rage     a rage tap (several fast taps on one spot — PostHog's $rageclick)
    dead     a tap where nothing happened (PostHog's $dead_click)
    repeat   the same element tapped 3 or more times in one visit
A row is kept when at least 2 recordings of visitors who left show it. These are counts the teardown prompt reads
as fact; it does not have to find them in the timelines itself.
"""
REPEAT = 3
MIN_LEFT = 2


def _key(e):
    return (e.get("text") or "").strip().replace("\n", " ")[:80] or "(an element with no words)"


def count(events_by_session, picked):
    rows = {}
    for group in ("left", "converted"):
        for s in picked[group]:
            seen, taps = set(), {}
            for e in events_by_session.get(s, []):
                ev = e.get("event")
                if ev == "$rageclick":
                    seen.add(("rage", _key(e)))
                elif ev == "$dead_click":
                    seen.add(("dead", _key(e)))
                if ev in ("$autocapture", "$rageclick", "$dead_click"):
                    taps[_key(e)] = taps.get(_key(e), 0) + 1
            seen |= {("repeat", k) for k, v in taps.items() if v >= REPEAT}
            for kind, what in seen:
                r = rows.setdefault((kind, what), {"kind": kind, "element": what, "left": 0, "converted": 0})
                r[group] += 1
    out = [r for r in rows.values() if r["left"] >= MIN_LEFT]
    out.sort(key=lambda r: (-(r["left"] - r["converted"]), r["kind"], r["element"]))
    return out


WORDS = {"rage": "rage-tapped", "dead": "tapped, nothing happened", "repeat": "tapped 3+ times"}


def as_text(rows, n):
    if not rows:
        return "(no rage taps, dead taps or repeated taps in 2 or more recordings of visitors who left)"
    out = ["what | element | left (of %d) | converted (of %d)" % (n["left"], n["converted"])]
    out += ['%s | "%s" | %d | %d' % (WORDS[r["kind"]], r["element"], r["left"], r["converted"]) for r in rows]
    return "\n".join(out)
