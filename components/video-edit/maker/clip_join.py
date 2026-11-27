#!/usr/bin/env python3
"""clip_join.py — one clip per real moment (2026-11-25).

A scene cut into many short shots went to the maker as one paid clip each. The clip model makes nothing under four seconds, so a
1.5 second shot bought four, and one ad asked for 68 clips. A scene's shots are made the way the Studio already makes them
(video-studio/take_sheet.py shots_params): one take with a hard cut per shot.

`join(clips)` takes one scene's clips in order and returns them joined:
  - clips with the very same words are one clip;
  - a shot under MIN seconds is joined to the next of the same people and place, up to MOST seconds and SHOTS shots.
`split(clip, words)` is the other end: a clip longer than the model makes in one call (LONG) becomes parts cut between its
sentences, each carrying on from the one before.
A clip of MIN seconds or more that stands alone is left as it was, and so is a sung clip, a card, a screen recording, and a clip
of other people or another place. Pure: no file is read or written. Python 3.9, standard library.
"""
import math
import re
from pathlib import Path

MIN, MOST, SHOTS, LONG = 4.0, 12.0, 5, 15.0


def _plain(c):
    return c.get("tool") in ("gen.shot", "gen.take") and not c.get("song_at") and not c.get("make") and not c.get("hold") and \
        not c.get("our_cut") and c.get("route") in (None, "shot")


def _who(c):
    """The people, place and look this clip is made with (the nearest-clip and scene notes say nothing about either)."""
    return frozenset(r for r in c.get("named_refs") or [] if "nearest clip" not in r and not r.startswith("the scene"))


def _together(group, c):
    first = group[0]
    return _plain(c) and c.get("scene") == first.get("scene") and c.get("brief_scene") == first.get("brief_scene") and \
        c.get("lips") == first.get("lips") and _who(c) == _who(first)


def _secs(c):
    return float(c.get("secs") or 0)


def bought(clips):
    """Seconds the model charges for."""
    return sum(max(MIN, math.ceil(_secs(c))) for c in clips)


def _one(group, all_):
    """Several clips as one."""
    if len(group) == 1:
        return group[0]
    a, b = group[0], group[-1]
    words = list(dict.fromkeys(str(c.get("recipe") or "").strip() for c in group))
    total = round(sum(_secs(c) for c in group), 2)
    nos = [n for c in group for n in c.get("shot_nos") or [all_.index(c) + 1]]
    c = dict(a)
    whole = len(group) == len(all_)
    c["id"] = a["id"] if whole else "%s-shots-%d-%d" % (a["scene"], nos[0], nos[-1])
    ret, stem = Path(a["return"]), re.sub(r"-shot-\d+$", "", Path(a["return"]).stem)
    c["return"] = str(ret.with_name(stem + ("" if whole else "-shots-%d-%d" % (nos[0], nos[-1])) + ret.suffix))
    if len(words) == 1:
        c["recipe"] = words[0]
    else:
        c["recipe"] = "One continuous clip in one place, %d shots in order, a hard cut between each:\n%s" % (
            len(group), "\n".join("  %d. (%.1f s) %s" % (i, _secs(x), str(x.get("recipe") or "").strip()) for i, x in enumerate(group, 1)))
    c.update(secs=total, shot_nos=nos, joined=[x["id"] for x in group])
    for k in ("copies", "refs"):
        c[k] = list(dict.fromkeys(y for x in group for y in x.get(k) or []))
    c["swipe"] = [y for i, x in enumerate(group) for y in x.get("swipe") or [] if not any(y in (z.get("swipe") or []) for z in group[:i])]
    c["same_people_as"] = None if a.get("same_people_as") in c["joined"] else a.get("same_people_as")
    return c


def join(clips):
    out, group = [], []
    total = lambda: sum(_secs(x) for x in group)                       # noqa: E731
    for c in clips:
        if group and _plain(group[0]) and _together(group, c):
            same = str(c.get("recipe") or "").strip() == str(group[-1].get("recipe") or "").strip() != ""
            short = total() < MIN or _secs(c) < MIN
            if (same or short) and total() + _secs(c) <= MOST + 0.01 and (same or len(group) < SHOTS):
                group.append(c)
                continue
        if group:
            out.append(group)
        group = [c]
    if group:
        out.append(group)
    if len(out) > 1 and sum(_secs(x) for x in out[-1]) < MIN and _together(out[-2], out[-1][0]) and _plain(out[-2][0]) and \
            sum(_secs(x) for x in out[-2] + out[-1]) <= 15:                # a short tail goes with the clip before it
        out[-2:] = [out[-2] + out[-1]]
    for g in out:
        if len(g) == 1 and len(clips) > 1:
            g[0].setdefault("shot_nos", [clips.index(g[0]) + 1])
    joined = [_one(g, clips) for g in out]
    was = {x: c["id"] for c in joined for x in c.get("joined") or [c["id"]]}
    for c in joined:
        for k in ("same_people_as", "continues"):
            if c.get(k) in was:
                c[k] = was[c[k]] if was[c[k]] != c["id"] else None
    return joined


def split(c, words=""):
    """[the clip], or its parts when it is longer than one call makes. Each part says its own sentences and no other's."""
    total = _secs(c)
    if total <= LONG + 0.5 or not _plain(c):
        return [c]
    said = [x.strip() for x in re.split(r"(?<=[.!?])[\"”']?\s+", re.sub(r"\s+", " ", str(words or "")).strip()) if x.strip()]
    n = math.ceil(total / (LONG - 1.0))
    if len(said) < n:
        parts = [[] for _ in range(n)]
        lens = [total / n] * n
    else:
        count = [len(x.split()) for x in said]
        every, parts, k = sum(count), [[]], 0
        for x, w in zip(said, count):                                  # full parts first; a sentence is never cut in two
            if parts[-1] and (sum(len(y.split()) for y in parts[-1]) + w) / every * total > LONG - 1.0:
                parts.append([])
            parts[-1].append(x)
        lens = [sum(len(y.split()) for y in p) / every * total for p in parts]
    if len(parts) < 2 or max(lens) > LONG + 0.5:
        parts, lens = ([[] for _ in range(n)], [total / n] * n) if not said else (parts, lens)
    out, at, n = [], 0.0, len(parts)
    ret = Path(c["return"])
    for k, (p, secs) in enumerate(zip(parts, lens), 1):
        x = dict(c, id="%s-part-%d" % (c["id"], k), secs=round(secs, 2), part=[k, n], says=" ".join(p) or None,
                 read_at=[round(at, 2), round(at + secs, 2)])
        x["return"] = str(ret.with_name("%s-part-%d%s" % (ret.stem, k, ret.suffix)))
        x["continues"] = c.get("continues") if k == 1 else "%s-part-%d" % (c["id"], k - 1)
        x["same_people_as"] = c.get("same_people_as") if k == 1 else "%s-part-1" % c["id"]
        x["recipe"] = "Part %d of %d of one shot%s. %s" % (k, n, "" if k == 1 else ", carrying straight on from the part before: the same framing, place, light and clothes",
                                                          str(c.get("recipe") or "").strip())
        out.append(x)
        at += secs
    return out
