#!/usr/bin/env python3
"""The plan: every ad being made, in one list per brand, so nothing is written or pictured that Meta would group with
another ad. Every chain goes through here; no brand is named here and nothing calls Meta.

    creative_plan.py board <brand> [--profile <profile>]                       what is taken, and what is still open, for one person
    creative_plan.py claim <brand> <id> profile=… awareness=… angle=… format=… face=… setting=… look=…
    creative_plan.py tie   <brand> <id> <brief>      creative_plan.py mark <brand> <id> filed|live|dropped      creative_plan.py list <brand>

`claim` compares the seven moves (dimensions.json) with every ad running (the saved library) and every ad planned, filed
or live here, and adds the ad. 0 or 1 move apart is refused: it is the same creative. 2 is written and flagged. 3 is new.
A headline version is the same ad and never claims. The list is runs/creative-diversity/<brand>/planned.json.
"""
import fcntl
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OURS = ("check", "matrix", "tag", "brief_view", "cd_keys")


def _own(name):
    """This folder's module, whatever another tool in the same run has loaded under the same plain name (`check`)."""
    key = "creative_diversity_" + name
    if key not in sys.modules:
        import importlib
        kept = {n: sys.modules.pop(n) for n in OURS if n in sys.modules}
        sys.path.insert(0, str(HERE))
        try:
            mod = importlib.import_module(name)
            for n in OURS:
                if n in sys.modules:
                    sys.modules.setdefault("creative_diversity_" + n, sys.modules[n])
        finally:
            sys.path.remove(str(HERE))
            for n in OURS:
                sys.modules.pop(n, None)
            sys.modules.update(kept)
        sys.modules[key] = mod
    return sys.modules[key]


K, M = _own("check"), _own("matrix")

NAMES = {"profile": "profile", "awareness": "awareness", "angle": "angle", "format": "format", "face": "face", "setting": "setting", "look": "look"}
STATES = ("planned", "filed", "live", "dropped")


def file(brand):
    return Path(os.environ.get("CREATIVE_PLAN_ROOT") or ROOT / "runs" / "creative-diversity") / brand / "planned.json"


def ledger(brand):
    try:
        ads = json.loads(file(brand).read_text())["ads"]
    except (OSError, ValueError, KeyError):
        return {}
    M.norm_items(ads.values() if isinstance(ads, dict) else [])     # a plan written before 26 Nov says who / argument
    return ads


class _Locked:
    """One writer at a time: several sessions plan at once."""
    def __init__(self, brand):
        self.f = file(brand)

    def __enter__(self):
        self.f.parent.mkdir(parents=True, exist_ok=True)
        self.lock = open(str(self.f) + ".lock", "w")
        fcntl.flock(self.lock, fcntl.LOCK_EX)
        self.ads = ledger(self.f.parent.name)
        return self

    def __exit__(self, t, v, tb):
        if t is None:
            tmp = Path(str(self.f) + ".tmp")
            tmp.write_text(json.dumps({"_about": "Every ad being made and its seven moves. Written by components/creative-diversity/creative_plan.py.", "ads": self.ads}, indent=1, ensure_ascii=False) + "\n")
            tmp.replace(self.f)
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()


def running(brand):
    mx, day = K.library(brand)
    return [(i["asset"], i["moves"]) for i in (mx or {}).get("items") or []], day


def look_at(brand, ident, moves):
    """How far this ad is from everything taken. {"verdict": same|close|new, "moves_apart", "nearest", "same_on", "where"}"""
    near = None
    live, day = running(brand)
    rows = [("running", a, m) for a, m in live] + [(r.get("state", "planned"), k, r.get("made") or r["moves"]) for k, r in ledger(brand).items() if k != ident and r.get("state") != "dropped"]
    for where, name, m in rows:
        n, diff = M.distance(moves, m)
        same = [k for k in M.BIG if moves.get(k) not in (None, "", "unclear") and moves.get(k) == m.get(k)]
        known = len(diff) + len(same)
        if known < 4:                                  # too little is known of that ad to call it the same
            continue
        if near is None or n < near["moves_apart"]:
            near = {"moves_apart": n, "nearest": name, "same_on": same, "where": where, "nearest_is": m}
    if near is None:
        return {"verdict": "new", "moves_apart": None, "nearest": None, "same_on": [], "where": None, "library": day}
    n, r = near["moves_apart"], K.DIMS["rule"]
    return dict(near, verdict="same" if n <= r["variation_at_or_below"] else "close" if n < r["min_moves"] else "new", library=day)


def why(v):
    if v["verdict"] == "new":
        return "%s moves from the nearest ad" % (v["moves_apart"] if v["moves_apart"] is not None else "many")
    return "%d move%s from %s (%s): same %s" % (v["moves_apart"], "" if v["moves_apart"] == 1 else "s", v["nearest"], v["where"], ", ".join(NAMES[k] for k in v["same_on"]))


def claim(brand, ident, moves, by="", brief=None, force=False):
    """Add one ad to the plan. The verdict; a `same` one is not added (raise nothing: the caller's gate decides)."""
    moves = M.norm(moves)
    miss = [k for k in M.BIG if not moves.get(k)]
    if miss:
        raise ValueError("an ad declares all 7 moves; missing: " + ", ".join(miss))
    with _Locked(brand) as l:
        v = look_at(brand, ident, moves)
        if v["verdict"] != "same" or force:
            old = l.ads.get(ident) or {}
            l.ads[ident] = {"moves": {k: moves[k] for k in M.BIG}, "state": old.get("state", "planned"), "brief": brief or old.get("brief"), "by": by or old.get("by"),
                            "verdict": v["verdict"], "moves_apart": v["moves_apart"], "nearest": v["nearest"], "at": datetime.now().isoformat(timespec="seconds")}
    return v


def tie(brand, ident, brief):
    with _Locked(brand) as l:
        if ident in l.ads:
            l.ads[ident]["brief"] = brief


def mark(brand, name, state):
    """`name` is the ad's id or its brief number."""
    if state not in STATES:
        raise ValueError("a state is one of " + ", ".join(STATES))
    with _Locked(brand) as l:
        for k, r in l.ads.items():
            if name in (k, r.get("brief")):
                r["state"] = state


def made(brand, name, moves):
    """What was really made, read off the finished picture: later ads are compared with this, not with the plan."""
    moves = M.norm(moves)
    with _Locked(brand) as l:
        for k, r in l.ads.items():
            if name in (k, r.get("brief")):
                r["made"] = {c: moves.get(c) or r["moves"][c] for c in M.BIG}
                return k
    return None


def short(m):
    return " · ".join("%s" % m.get(k) for k in M.BIG if m.get(k) not in (None, "", "unclear"))


def board(brand, who="", avatar_subs=(), most=14):
    """What a writer is handed: what is taken for this person (then for the rest of the brand), and what nobody uses yet."""
    live, _ = running(brand)
    rows = [(a, m, "running") for a, m in live] + [(k, r["moves"], r.get("state", "planned")) for k, r in ledger(brand).items() if r.get("state") != "dropped"]
    if not rows:
        return ""
    clean = re.sub(r"^sub-\d+-", "", who or "")
    mine = [x for x in rows if re.sub(r"^sub-\d+-", "", str(x[1].get("profile"))) == clean] if clean else []
    planned = [x for x in rows if x[2] != "running" and x not in mine]
    out = ["", "**Different from every other ad (Meta groups ads that look or feel alike):**", "",
           "This ad must differ from each one below on at least 3 of: profile, awareness, angle, format, face, setting, look. Rewording a headline is not a difference. Change what is SEEN first."]
    for title, xs in (("Taken for this person", mine), ("Being made now for others", planned)):
        if xs:
            seen, keep = set(), []
            for _, m, st in xs[::-1]:
                s = short(m)
                if s not in seen:
                    seen.add(s)
                    keep.append("- (%s) %s" % (st, s))
            out += ["", title + " (profile · awareness · angle · format · face · setting · look):"] + keep[:most]
    top = {k: {} for k in ("format", "setting", "look")}
    for _, m, _st in rows:
        for k in top:
            if m.get(k) not in (None, "", "unclear"):
                top[k][m[k]] = top[k].get(m[k], 0) + 1
    worn = ["%s: %s" % (NAMES[k], ", ".join("%s (%d)" % x for x in sorted(c.items(), key=lambda x: -x[1])[:4])) for k, c in top.items() if c]
    return "\n".join(out + ["", "Worn the most across the brand, so reach past it: " + "; ".join(worn) + "."])


def known(text_moves, aim=None):
    """The seven moves, where the run's own decisions win over what was read off the words."""
    a, m = aim or {}, dict(text_moves or {})
    if a.get("sub") or a.get("avatar"):
        m["profile"] = re.sub(r"^sub-\d+-", "", a.get("sub") or a.get("avatar"))
    if a.get("awareness"):
        m["awareness"] = a["awareness"]
    if a.get("demographic"):
        p = re.split(r"[/]|-(?=\d|65|[a-z])", str(a["demographic"]))
        g = {"m": "male", "f": "female"}.get(p[0], p[0])
        rest = str(a["demographic"])[len(p[0]):].strip("/-")
        age = re.search(r"\d\d-\d\d|65-plus", rest)
        if age and m.get("face") != "none":
            m["face"] = "%s/%s/%s" % (g, age.group(0), rest.replace(age.group(0), "").strip("/-") or "unclear")
    return {k: (m.get(k) or "unclear") for k in M.BIG}


def read(brand, text, ask=None):
    """The seven moves read off a written plan, with the same prompt every other reader uses. `ask(prompt) -> text`."""
    BV, T = _own("brief_view"), _own("tag")
    if ask is None:
        t = BV.read_moves(brand, text)
    else:
        raw = ask(BV.filled(brand, text))
        t = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
        t = T.check(brand, {**t, "style": t.get("style"), "sub_avatar": t.get("sub_avatar")})
    return M.moves({"sub_avatar": t.get("sub_avatar"), "awareness": t.get("awareness"), "angle": t.get("angle"), "format": t.get("format"),
                    "setting": t.get("setting"), "style": t.get("style"), "face": BV._face(t.get("face"))})


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) < 2:
        print(__doc__)
        return 2
    do, brand = a[0], a[1]
    if do == "board":
        flag = "--profile" if "--profile" in a else "--who"            # --who: the old word, still read
        print(board(brand, a[a.index(flag) + 1] if flag in a else "") or "nothing taken yet")
    elif do == "claim":
        v = claim(brand, a[2], dict(x.split("=", 1) for x in a[3:] if "=" in x), force="--force" in a)
        print("%s: %s" % (v["verdict"], why(v)))
        return 1 if v["verdict"] == "same" and "--force" not in a else 0
    elif do == "tie":
        tie(brand, a[2], a[3])
    elif do == "mark":
        mark(brand, a[2], a[3])
    elif do == "list":
        for k, r in ledger(brand).items():
            print("%-8s %-46s %s" % (r.get("state"), k, short(r["moves"])))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
