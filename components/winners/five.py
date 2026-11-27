#!/usr/bin/env python3
"""five: the brand's always-on creator briefs — the five proven ads to brief from, ranked on numbers only.

Normally driven by `winners.py five --brand <b>`. Writes runs/winners/<brand>/brief-five.json + .md.

Pool. Every bank row, paid, chain-made and creator, on its best-documented numbers: the snapshot with the most
purchases (then the most spend), whatever its window; the window travels with the entry.

Proven. A row is proven when it clears its bar (bank.bar_for: creator videos on the creator bar, every other row on
the bank's bar). While a row's own bar is open, the floor is the bank's one set bar (the creator bar) when there is
one, else one purchase. The basis is written into the file, so a reader sees which bar decided.

Rank. Purchases, then the lower CPA, then spend. Five, no two sharing a format and angle pair. Format is the
on-screen tag (audit tag memory `tags.json`, or the creator read's `format`); angle is the message tag (or the
creator read's `angle`). A proven row with no usable tag (missing, or a catch-all such as "other", creators.vague)
cannot be shown to differ, so it is held out and listed under `held`, never guessed. Fewer than five proven: the
file lists what there is and says so; it never pads.

Teardown. Where one exists on disk: the audit's teardown, the registry row's teardown run, or the writing run the
ad was made from (labelled as such).

Offline. Stdlib only. Reads the bank, the tag memory, the audit's ranked.json (for the ad's watch link) and a
registry file a bank row names. Writes only the two files above. Exit 2 on bad input.
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402
import audit as A  # noqa: E402
import bank as B  # noqa: E402
import creators as CR  # noqa: E402

SIZE = 5


class BadInput(Exception):
    pass


def load(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.is_file() else default


def best_snapshot(row):
    snaps = [s for s in row.get("snapshots") or [] if s.get("purchases") is not None]
    if not snaps:
        return None
    return max(snaps, key=lambda s: (s.get("purchases") or 0, s.get("spend") or 0, B.widest_key(s)))


def floor(bank, row):
    """(bar, words) the row is judged on for the five."""
    own = B.bar_for(bank, row)
    if not B.is_open(own):
        return own, "creator bar" if own is bank.get("creator_bar") else "bar"
    cb = bank.get("creator_bar")
    if cb and not B.is_open(cb):
        return cb, "the creator bar (the one set bar; this row's own bar is open)"
    return {"min_purchases": 1}, "at least one purchase (no bar set)"


def tag_for(row, mem):
    if row.get("tags"):
        t = row["tags"]
        return t.get("format"), t.get("angle"), "creator read"
    for n in [row.get("name")] + list(row.get("ad_names") or []):
        t = mem.get(n) or mem.get(A.base(n or ""))
        if t:
            return t.get("on_screen"), t.get("message"), "tag memory"
    return None, None, None


def link_for(home, row, sn, cache):
    """The ad's watch link from the audit's ranked.json, when the snapshot came from an audit."""
    if not sn.get("audit"):
        return None
    if sn["audit"] not in cache:
        rk = load(home / sn["audit"] / "ranked.json", {}) or {}
        cache[sn["audit"]] = rk.get("rows") or []
    ids = set(row.get("ad_ids") or [])
    for r in cache[sn["audit"]]:
        if ids & set(r.get("ids") or []) or r.get("name") == row.get("name"):
            return r.get("link")
    return None


def teardown_for(root, home, row):
    """[{kind, path}] that exist on disk, repo-relative."""
    out, src = [], row.get("source") or {}
    if src.get("teardown") and (home / src["teardown"]).exists():
        out.append({"kind": "audit teardown", "path": str((home / src["teardown"]).relative_to(root))})
    reg = src.get("registry")
    if reg and "#" in reg:
        f, rid = reg.split("#", 1)
        doc = load(root / f, {}) or {}
        hit = next((r for r in doc.get("rows") or [] if r.get("id") == rid), None)
        if hit and hit.get("run") and (root / hit["run"]).exists():
            out.append({"kind": "teardown run", "path": hit["run"].rstrip("/")})
    if row.get("run") and (root / row["run"]).exists():
        out.append({"kind": "made from (writing run)", "path": row["run"].rstrip("/")})
    return out


def kind_of(row, sn):
    if row.get("trybe_id"):
        return "creator"
    if row.get("run"):
        return "chain-made"
    return "paid"


def build(root, brand, today=None):
    root = Path(root)
    home = root / "runs" / "winners" / brand
    bank = load(home / "bank.json")
    if not isinstance(bank, dict) or bank.get("brand") != brand or not isinstance(bank.get("rows"), list):
        raise BadInput("not a %s bank: %s" % (brand, home / "bank.json"))
    mem = load(home / "tags.json", {}) or {}
    proven, cache = [], {}
    for row in bank["rows"]:
        sn = best_snapshot(row)
        if not sn:
            continue
        bar, words = floor(bank, row)
        if not B.clears(bar, sn) or not (sn.get("purchases") or 0) >= 1:
            continue
        proven.append((row, sn, words))
    proven.sort(key=lambda x: (-(x[1].get("purchases") or 0),
                               x[1]["cpa"] if x[1].get("cpa") is not None else float("inf"),
                               -(x[1].get("spend") or 0)))
    five, held, dupes, seen = [], [], 0, set()
    for i, (row, sn, words) in enumerate(proven, 1):
        fmt, angle, tag_src = tag_for(row, mem)
        e = entry(root, home, row, sn, fmt, angle, tag_src, cache)
        e["proven_rank"] = i
        if CR.vague(fmt) or CR.vague(angle):
            if len(held) < SIZE:
                e["why_held"] = "no usable format or angle tag (%s / %s); tag it to place it" % (fmt or "none",
                                                                                                angle or "none")
                held.append(e)
            continue
        pair = (fmt.strip().lower(), angle.strip().lower())
        if pair in seen:
            dupes += 1
            continue
        if len(five) == SIZE:
            continue
        seen.add(pair)
        e["why"] = ("#%d of %d proven by purchases; clears %s; the first proven ad with this format and angle"
                    % (i, len(proven), words))
        five.append(e)
    for n, e in enumerate(five, 1):
        e["rank"] = n
    short = None
    if len(five) < SIZE:
        short = ("only %d proven ad%s with a distinct, tagged format and angle; listed as they are, not padded"
                 % (len(five), "" if len(five) == 1 else "s"))
    return {
        "brand": brand, "status": "draft", "made": (today or datetime.now().strftime("%Y-%m-%d")),
        "basis": {"bar": bank.get("bar") or {}, "creator_bar": bank.get("creator_bar") or {},
                  "proven": "clears its bar; while a row's bar is open, the creator bar (the one set bar)",
                  "rank": "purchases, then lower CPA, then spend; each ad on its snapshot with the most purchases",
                  "distinct": "no two share a format (on-screen) and angle (message) pair",
                  "numbers": "platform-reported (Meta via the warehouse); never Trybe GMV"},
        "proven": len(proven), "same_pair_skipped": dupes, "short": short,
        "five": [order(e) for e in five], "held": [order(e) for e in held],
    }


def entry(root, home, row, sn, fmt, angle, tag_src, cache):
    w = row.get("words") or {}
    t = row.get("tags") or {}
    return {
        "id": row["id"], "kind": kind_of(row, sn), "name": row.get("name"),
        "ad_ids": list(row.get("ad_ids") or [])[:5], "trybe_id": row.get("trybe_id"), "creator": row.get("creator"),
        "link": link_for(home, row, sn, cache),
        "numbers": {"spend": sn.get("spend"), "purchases": sn.get("purchases"), "roas": sn.get("roas"),
                    "cpa": sn.get("cpa"), "value": sn.get("value"),
                    "window": "%s to %s" % (sn.get("since"), sn.get("until")),
                    "ran": ("%s to %s" % (sn["first"], sn["last"])) if sn.get("first") else None,
                    "from": sn.get("kind")},
        "format": fmt, "angle": angle, "tags_from": tag_src,
        "hook_line": t.get("hook_line") or w.get("hook") or None,
        "core_message": w.get("core_message") or None, "offer": w.get("offer") or None,
        "headline": row.get("headline") or None,
        "teardown": teardown_for(root, home, row),
    }


KEYS = ["rank", "proven_rank", "id", "kind", "name", "ad_ids", "trybe_id", "creator", "link", "numbers", "format",
        "angle", "tags_from", "hook_line", "core_message", "offer", "headline", "why", "why_held", "teardown"]


def order(e):
    return {k: e[k] for k in KEYS if k in e and e[k] not in (None, [], "")}


def money(x):
    return "—" if x is None else "$%s" % format(round(x), ",")


def line(e):
    n = e["numbers"]
    return "%s purchases · %s spend · ROAS %s · CPA %s · %s" % (
        format(n.get("purchases") or 0, ","), money(n.get("spend")), n.get("roas") if n.get("roas") is not None else "—",
        money(n.get("cpa")), n.get("ran") or n.get("window"))


def render(d):
    out = ["# Five always-on briefs — %s" % d["brand"], "",
           "Status: draft · made %s · %d proven ads · ranked on numbers only (%s) · %s." % (
               d["made"], d["proven"], d["basis"]["rank"], d["basis"]["distinct"]), ""]
    if d["short"]:
        out += ["**%s.**" % d["short"].capitalize(), ""]
    for e in d["five"]:
        out += ["## %d · %s" % (e["rank"], e.get("name")), "",
                "- %s · %s" % (e["kind"], e["id"] + (" · trybe %s" % e["trybe_id"] if e.get("trybe_id") else "")),
                "- Numbers: %s" % line(e),
                "- Format: %s · Angle: %s" % (e.get("format"), e.get("angle")),
                "- Hook: %s" % (e.get("hook_line") or "not on file"),
                "- Why: %s" % e["why"]]
        if e.get("link"):
            out.append("- Watch: %s" % e["link"])
        for t in e.get("teardown") or []:
            out.append("- %s: `%s`" % (t["kind"].capitalize(), t["path"]))
        out.append("")
    if d["held"]:
        out += ["## Held out — proven, but not tagged", ""]
        out += ["- #%d proven · %s · %s · %s" % (e["proven_rank"], e.get("name"), line(e), e["why_held"])
                for e in d["held"]]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write(root, brand, today=None):
    d = build(root, brand, today)
    home = Path(root) / "runs" / "winners" / brand
    (home / "brief-five.json").write_text(json.dumps(d, indent=1, ensure_ascii=False))
    (home / "brief-five.md").write_text(render(d))
    return home / "brief-five.json", d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--root", default=None)
    a = ap.parse_args(argv)
    try:
        p, d = write(Path(a.root) if a.root else paths.repo(), a.brand)
    except BadInput as e:
        print(e, file=sys.stderr)
        return 2
    print("five %s: %d of %d proven%s -> %s" % (a.brand, len(d["five"]), d["proven"],
                                              " (%s)" % d["short"] if d["short"] else "", p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
