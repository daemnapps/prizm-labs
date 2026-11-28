#!/usr/bin/env python3
"""THE GALAXY FILTER: from every possible variation (proven ad x person x point of that person's profile, the order book
in runs/creative-diversity/<brand>/families/_bank.json) down to the next batch of ads Meta's retrieval (Andromeda) and
TikTok's ranking read as truly different ads, aimed at deep profiles and formats that hold attention and earn the click.

    creative_filter.py <brand> [--batch 20] [--json]     prints the batch; writes runs/creative-diversity/<brand>/filter/

    order book -> gates -> score -> pick apart -> batch (each row says why it is in, and every cut says why)

1. Gates (cut, never scored): a proven ad with no sales; a profile point with no real line of the person's to open on.
2. Score = proof^a x watch^b x point^c x depth^d (values in filter.json):
   proof  the proven ad's sales and cost per sale;
   watch  how its storyline holds and gets the click: hook rate, 25% hold, link click rate from the brand's measured
          signals (runs/media-buying/<brand>/signals/), per storyline, shrunk to the mean where few ads were measured;
          x the media weight (Meta: 9:16 video with sound costs less per result);
   point  what the hook opens on (a lived moment beats a doubt), how many real lines stand behind it;
   depth  how many of the person's own lines their profile was filled from (thin profiles weigh less, never cut).
3. Pick apart: best first, a row goes in only when it is 3 of 7 apart, 2 of them seen (dimensions.json matrix rules),
   from every ad live, on the approval page or planned, and from every row already in the batch. The seven, in the
   way Meta groups ads (META.md): person, awareness, message, storyline, opening (the first line/visual), setting,
   media. A cell nobody knows is not a difference. Spread caps (filter.json) keep one ad, person or storyline from
   filling the batch.
4. Every row carries the maker that takes it (statics sprint, video writing, creator brief) and a reason.

No model, no Meta call, nothing paid. Names no brand: every brand fact comes from that brand's own runs and profiles.
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CFG = json.loads((HERE / "filter.json").read_text())
STD = json.loads((HERE / "formats-standard.json").read_text())
ALIAS = {a: f for f, v in STD["formats"].items() for a in [f] + v["aliases"]}
sys.path.insert(0, str(ROOT / "components" / "naming"))
import people as NAMING                                                                                    # noqa: E402  PEOPLE.md: the profile's one name
MX = json.loads((HERE / "dimensions.json").read_text())["matrix"]
RULE = {r["id"]: r for r in MX["rules"]}
COLS = ("person", "awareness", "message", "storyline", "opening", "setting", "media")
SEEN = ("storyline", "opening", "setting", "media")
NAMES = {"person": "person", "awareness": "awareness", "message": "message", "storyline": "storyline", "opening": "opening line",
         "setting": "setting", "media": "video/image"}
STOP = set("a an the and or but i im i'm my me to of in on for it is was be with that this at so just like not no do did "
           "he his him she her they them we our you your what when how have has had get got can could would will all".split())


# ---------------------------------------------------------------- reading (each a seam a test can replace)

def _words(t):
    return {w for w in re.findall(r"[a-z']+", (t or "").lower()) if len(w) > 2 and w not in STOP}


def overlap(a, b):
    """How much two openings say the same thing: shared words over the smaller set (0..1)."""
    x, y = _words(a), _words(b)
    return len(x & y) / min(len(x), len(y)) if x and y else 0.0


def ad_base(name):
    """An ad's name without the landing-page suffix Meta reports ("X - Icon LP", "X - Parasite LP #2")."""
    return re.sub(r"\s+-\s+[^-]*\bLP\b.*$", "", name or "").strip()


def storyline_of(kind):
    """A proven ad's on-screen kind, or any video format name the repo holds, as ONE format of the standard
    (formats-standard.json); '' when it is a picture ad or unknown."""
    if not kind or kind in ("?", "unclear"):
        return ""
    return STD["from_on_screen"].get(kind) or ALIAS.get(kind, "")


def story_of(fmt):
    """(format, media) of an ad's own format id: a video format is one of the standard's; any other is an image format, kept as it is."""
    if not fmt or fmt in ("?", "unclear"):
        return "", None
    v = storyline_of(fmt)
    return (v, "video") if v else (fmt, "image")


def setting_of(text):
    """The setting a point's own words name ('' when none)."""
    t = " %s " % (text or "").lower()
    for word, s in CFG["settings"]["words"]:
        if re.search(r"\b%s\b" % re.escape(word), t):
            return s
    return ""


def _people(brand):
    sys.path.insert(0, str(ROOT / "components" / "creative-strategist" / "machine"))
    sys.path.insert(0, str(HERE))
    import who as W
    import creative_matrix as X
    out = []
    for a in W.avatars(brand):
        for s in (W.subs(brand, a) or [a]):
            sl = W.slots(brand, a, "" if s == a else s)
            try:
                pts = X.points(brand, s)
            except (Exception, SystemExit):                  # noqa: BLE001  a person with no profile yet has no points
                pts = []
            try:
                pw = Counter(w for w in re.findall(r"[a-z]+", W.problem_words(brand, a, "" if s == a else s).lower()) if len(w) > 3 and w not in STOP)
            except (Exception, SystemExit):                  # noqa: BLE001  no card: no problem words, no bonus
                pw = Counter()
            out.append({"id": s, "avatar": a, "profile": NAMING.profile(brand, a, "" if s == a else s), "rows_read": sl.get("rows_read") or 0, "problem": sorted(w for w, n in pw.items() if n >= 2), "awareness_lead": sl.get("awareness_lead") or "",
                        "points": [{"kind": p["kind"], "point": p["point"], "said": [x for x in p["said"] if x],
                                    "rows": len(p.get("rows") or []), "urgent": bool((p.get("extra") or {}).get("urgency"))} for p in pts]})
    return out


def _winners(brand):
    bk = json.loads((ROOT / "runs" / "creative-diversity" / brand / "families" / "_bank.json").read_text())
    return [{"id": r["id"], "name": r.get("name") or r["id"], "idea": r.get("idea") or "", "on_screen": r.get("on_screen") or "",
             "media": "image" if (r.get("format") or "").lower() == "image" else "video",
             "purchases": r.get("purchases") or 0, "spend": r.get("spend") or 0, "cpa": r.get("cpa")} for r in bk["winners"]], bk.get("total")


def _signals(brand):
    """[(ad name, on-screen kind, hook, hold, ctr)] for every measured asset whose ad is tagged; ([], None) without a read."""
    d = sorted((ROOT / "runs" / "media-buying" / brand / "signals").glob("*/signals.json"))
    if not d:
        return [], None
    s = json.loads(d[-1].read_text())
    try:
        tags = json.loads((ROOT / "runs" / "winners" / brand / "tags.json").read_text())
    except (OSError, ValueError):
        tags = {}
    out = []
    for grp in (s.get("assets") or {}).values():
        for x in grp:
            t = tags.get(ad_base(x.get("ad_name"))) or tags.get(x.get("ad_name")) or {}
            if t.get("on_screen"):
                out.append((x.get("ad_name"), t["on_screen"], x.get("hook_rate") or 0, x.get("hold_25") or 0, x.get("link_ctr") or 0))
    return out, d[-1].parent.name


def _outside(brand):
    """Everything Meta has or will soon have: running (the saved library), on the approval page or live (the finished-ads
    index, with each card's own read of its hook where the card is reachable), and planned (the plan ledger)."""
    out = []
    sys.path.insert(0, str(HERE))
    import creative_plan as PL
    try:
        live, day = PL.running(brand)
    except Exception:                                        # noqa: BLE001  no library read yet
        live, day = [], None
    for a, m in live:
        out.append({"where": "running (library %s)" % day, "name": a, "person": m.get("profile"), "awareness": m.get("awareness"), "message": _msg(m.get("angle")),
                    "storyline": story_of(m.get("format"))[0], "setting": m.get("setting"), "media": "image" if a.startswith("image") else "video"})
    for k, r in PL.ledger(brand).items():
        if r.get("state") == "dropped":
            continue
        m = r.get("made") or r["moves"]
        out.append({"where": "planned (%s)" % r.get("state"), "name": k, "person": m.get("profile"), "awareness": m.get("awareness"), "message": _msg(m.get("angle")),
                    "storyline": story_of(m.get("format"))[0], "setting": m.get("setting"), "media": story_of(m.get("format"))[1]})
    hooks = _card_hooks(brand)
    try:
        idx = json.loads((ROOT / "runs" / "meta-upload" / brand / "ADS-INDEX.json").read_text())["briefs"]
    except (OSError, ValueError, KeyError):
        idx = []
    for b in idx:
        if b.get("state") not in ("1-check", "2-approved", "3-live"):
            continue
        h = next((hooks[c["ad_name"]] for c in b.get("cards") or [] if c.get("ad_name") in hooks), {})
        out.append({"where": {"1-check": "approval page", "2-approved": "approved", "3-live": "live"}[b["state"]], "name": b["brief"],
                    "person": b.get("sub_avatar") or b.get("sub") or h.get("sub_avatar"), "awareness": b.get("awareness") or h.get("awareness"),
                    "message": " ".join(x for x in (_msg(b.get("angle")), h.get("core_message")) if x),
                    "storyline": story_of(h.get("format"))[0], "opening": " ".join(x for x in (h.get("hook"), h.get("desire")) if x),
                    "setting": h.get("setting"), "media": "video" if "video" in (b.get("lanes") or []) else "image"})
    return out


def _msg(angle):
    """An angle id read as words ("new:beard-hides-the-bumps" -> "beard hides the bumps"), so it can be set against a
    proven ad's message by what it says."""
    return re.sub(r"^new:", "", angle or "").replace("-", " ").strip()


def _card_hooks(brand):
    """{ad name: the card's own read (hook, person, format, setting)} through meta-upload's card surface; {} when unreachable."""
    try:
        sys.path.insert(0, str(ROOT / "components" / "meta-upload"))
        import cards as C
        out = {}
        for f in C.listing(brand=brand):
            c = C.load(f)
            t = (c.get("diversity") or {}).get("tag") or {}
            if t:
                out[c.get("ad_name")] = t
        return out
    except Exception:                                        # noqa: BLE001  the Drive is not mounted here: index fields only
        return {}


def load(brand):
    w, total = _winners(brand)
    sig, sig_day = _signals(brand)
    return {"brand": brand, "winners": w, "total": total, "people": _people(brand), "signals": sig, "signals_day": sig_day,
            "outside": _outside(brand), "image_formats": _image_formats(brand)}


def _image_formats(brand):
    """The creative matrix's own image formats for this brand (the one list pictures are made from)."""
    try:
        sys.path.insert(0, str(HERE))
        import creative_matrix as X
        return X.values(brand, "image")["format"]
    except (Exception, SystemExit):                          # noqa: BLE001  no list read: the fallback in filter.json
        return CFG["image_formats_fallback"]


# ---------------------------------------------------------------- the rules

def watch_table(signals):
    """{storyline: {"hook", "hold", "ctr", "n", "score"}}: each measure shrunk to the mean by watch_prior_n, then the
    score = 0.4 hook + 0.3 hold + 0.3 click, each over the best storyline's (statics: click only)."""
    k = CFG["watch_prior_n"]
    by = {}
    for _, kind, hook, hold, ctr in signals:
        fam = storyline_of(kind)
        if fam:
            by.setdefault(fam, []).append((hook, hold, ctr))
    vids = [x for v in by.values() for x in v if x[0] > 0]
    allx = [x for v in by.values() for x in v]
    mean = lambda xs, i: sum(x[i] for x in xs) / len(xs) if xs else 0.0   # noqa: E731
    mh, mo, mc = mean(vids, 0), mean(vids, 1), mean(allx, 2)
    t = {}
    for fam, xs in by.items():
        v = [x for x in xs if x[0] > 0]
        t[fam] = {"hook": (sum(x[0] for x in v) + k * mh) / (len(v) + k), "hold": (sum(x[1] for x in v) + k * mo) / (len(v) + k),
                  "ctr": (sum(x[2] for x in xs) + k * mc) / (len(xs) + k), "n": len(xs), "video": bool(v)}
    t["_mean"] = {"hook": mh, "hold": mo, "ctr": mc, "n": 0, "video": True}
    bh, bo, bc = (max([x[f] for x in t.values()] or [1]) or 1 for f in ("hook", "hold", "ctr"))
    for x in t.values():
        x["score"] = 0.4 * x["hook"] / bh + 0.3 * x["hold"] / bo + 0.3 * x["ctr"] / bc if x["video"] else x["ctr"] / bc
    return t


def watch_of(table, storyline, media):
    x = table.get(storyline) or table.get("_mean") or {"score": 0.5}
    return (0.5 + 0.5 * x["score"]) * CFG["media"][media], x


def proof_of(w, maxp, mid_cpa):
    p = math.log1p(w["purchases"]) / math.log1p(maxp) if maxp else 0.0
    c = min(1.4, max(0.6, mid_cpa / w["cpa"])) / 1.4 if w.get("cpa") and mid_cpa else 1 / 1.4
    return p * math.sqrt(c)


def depth_of(p):
    d = CFG["depth"]
    thin = p["rows_read"] < d["thin_rows_read"] or len(p["points"]) < d["thin_points"]
    return 0.5 + 0.5 * min(1.0, p["rows_read"] / d["full_rows_read"]), thin


def point_of(q, problem=()):
    s = CFG["point_kind"].get(q["kind"], 0.6)
    s *= 1 + min(q.get("rows") or 0, 10) / 20                # more real lines stand behind it
    s *= 1.1 if q.get("urgent") else 1.0
    s *= line_of(q["said"][0], problem)
    return s / 2.4


def line_of(t, problem=()):
    """How well a real line opens an ad as it is: said in the first person, about the person's own problem (their
    profile's words), a moment and not a service note, short."""
    w = re.findall(r"[a-z']+", (t or "").lower())
    s = 1.15 if {"i", "my", "me", "i'm", "im", "i've"} & set(w) else 0.9
    s *= 1.0 if 6 <= len(w) <= 28 else 0.8
    s *= 1.25 if problem and set(w) & set(problem) else 1.0
    low = " %s " % (t or "").lower()
    if any(re.search(r"\b%s\b" % re.escape(x), low) for x in CFG["not_an_opener"]["words"]):
        s *= CFG["not_an_opener"]["weight"]
    s *= 1.1 if re.search(r"\b(years?|months?|days?|every|never|always|still|since|tried|finally)\b", t.lower()) else 1.0
    return s


def awareness_of(q, person):
    if q["kind"] == "doubt":
        return "solution-aware" if q["point"] in ("does it work", "for me") else "product-aware"
    return person.get("awareness_lead") or "problem-aware"


def apart(a, b, same_at):
    """(columns apart, seen columns apart, columns both know, seen columns both know). A cell nobody knows is not a
    difference, and not a sameness either."""
    n = s = known = kseen = 0
    for k in COLS:
        x, y = a.get(k), b.get(k)
        if k == "opening" and x and not y:                   # nobody recorded the other ad's opening; a row stands on one of the
            n, s, known, kseen = n + 1, s + 1, known + 1, kseen + 1   # person's own lines, so its opening is its own unless a card says otherwise
            continue
        if not x or not y or x in ("unclear", "?") or y in ("unclear", "?"):
            continue
        known += 1
        kseen += k in SEEN
        diff = overlap(x, y) < same_at if k in ("opening", "message") else x != y
        if diff:
            n += 1
            s += k in SEEN
    return n, s, known, kseen


def lane_ok(lane, canon):
    """Does this format of the standard belong in this lane? (the lane's `needs` flag in filter.json)"""
    need = CFG["lanes"][lane]["needs"]
    return bool(canon) and (not need or STD["formats"][canon][need])


def candidates(ctx, lane):
    """(gate counts over the whole order book, the scored pool best first) for one lane. video lanes take the proven
    video ads whose format the lane can make; images take every proven ad's message as a picture."""
    g, wt, ln = CFG["gates"], CFG["weights"], CFG["lanes"][lane]
    table = watch_table(ctx["signals"])
    proven = [w for w in ctx["winners"] if w["purchases"] >= g["min_purchases"]]
    no_proof = [w for w in ctx["winners"] if w not in proven]
    maxp = max([w["purchases"] for w in proven] or [0])
    cpas = sorted(w["cpa"] for w in proven if w.get("cpa"))
    mid = cpas[len(cpas) // 2] if cpas else None
    all_pts = sum(len(p["points"]) for p in ctx["people"])
    cut = {"no proof (no sales)": len(no_proof) * all_pts}
    if ln["media"] == "image":
        proven = [dict(w, media="image") for w in proven]
    else:
        other = [w for w in proven if w["media"] != "video" or not lane_ok(lane, storyline_of(w["on_screen"]))]
        proven = [w for w in proven if w["media"] == "video" and lane_ok(lane, storyline_of(w["on_screen"]))]
        cut["its format does not belong in this lane"] = len(other) * all_pts
    pool = []
    for p in ctx["people"]:
        depth, thin = depth_of(p)
        prob = set(p.get("problem") or ())
        p.setdefault("places", sorted({setting_of(q["point"] + " " + " ".join(q["said"])) for q in p["points"]} - {""}))
        has = [dict(q, said=sorted(q["said"], key=lambda t: -line_of(t, prob))) for q in p["points"] if len(q["said"]) >= g["min_said"]]
        cut["no real line to open on"] = cut.get("no real line to open on", 0) + (len(p["points"]) - len(has)) * len(proven)
        best = sorted(has, key=lambda q: point_of(q, prob), reverse=True)
        for i, q in enumerate(best[:g["points_per_person"]]):
            for w in proven:
                sl = "" if w["media"] == "image" else storyline_of(w["on_screen"])
                watch, wx = watch_of(table, sl, w["media"])
                pr = proof_of(w, maxp, mid)
                pt = point_of(q, prob)
                score = pr ** wt["proof"] * watch ** wt["watch"] * pt ** wt["point"] * depth ** wt["depth"]
                pool.append({"score": score, "w": w, "p": p, "q": q, "qi": i + 1, "thin": thin, "lane": lane,
                             "parts": {"proof": round(pr, 3), "watch": round(watch, 3), "point": round(pt, 3), "depth": round(depth, 3)},
                             "watch_from": wx,
                             "cell": {"person": p["id"], "awareness": awareness_of(q, p), "message": w["idea"], "storyline": sl,
                                      "opening": q["said"][0] + " " + q["point"], "setting": setting_of(q["point"] + " " + " ".join(q["said"])),
                                      "media": w["media"]}})
        cut["not read this round (only each person's best points are)"] = cut.get("not read this round (only each person's best points are)", 0) + max(0, len(best) - g["points_per_person"]) * len(proven)
    pool.sort(key=lambda c: -c["score"])
    return cut, pool, table


def least_used(counts, options, preferred=()):
    """The option used least so far (ties: the list's order), taken from the preferred ones when there are any."""
    opts = [x for x in options if x in set(preferred)] or list(options)
    return min(opts, key=lambda s: (counts[s], opts.index(s)))


def select(ctx, size, lane, outside=None):
    """One lane's picks: {"batch": [rows], "cuts": {reason: n}, "examples": {reason: [row]}, "looked": n, "pool": n, ...}"""
    caps, same_at = CFG["caps"], CFG["opening_same_at"]
    pmin, smin = RULE["pair"]["min"], RULE["seen"]["min"]
    gate, pool, table = candidates(ctx, lane)
    outside = list(ctx["outside"] if outside is None else outside)
    per_winner = CFG["lanes"][lane]["per_winner"]
    media = CFG["lanes"][lane]["media"]
    setc = Counter(o.get("setting") for o in outside if o.get("setting"))
    imgc = Counter(o.get("storyline") for o in outside if o.get("media") == "image" and o.get("storyline"))
    batch, cuts, ex = [], Counter(), {}
    per_w, per_p, per_s = Counter(), Counter(), Counter()
    looked, used_lines = 0, set()

    def drop(reason, c, near=None):
        cuts[reason] += 1
        if len(ex.setdefault(reason, [])) < 4:
            ex[reason].append(_row(c, None, near))

    for c in pool:
        if len(batch) >= size:
            break
        looked += 1
        cell = dict(c["cell"])
        if per_w[c["w"]["id"]] >= per_winner:
            cuts["that proven ad already has its rows in this lane"] += 1
            continue
        if per_p[cell["person"]] >= max(1, int(size * caps["person_share"])):
            cuts["that person already has their share of this lane"] += 1
            continue
        if cell["storyline"] and per_s[cell["storyline"]] >= max(1, int(size * caps["storyline_share"])):
            cuts["that format already has its share of this lane"] += 1
            continue
        if (cell["person"], c["q"]["said"][0]) in used_lines:
            cuts["that line already opens a row in this lane"] += 1
            continue
        if media == "image":                                  # a picture ad takes the picture format used least so far
            cell["storyline"] = least_used(imgc, ctx.get("image_formats") or CFG["image_formats_fallback"])
        if not cell["setting"]:
            cell["setting"] = least_used(setc, CFG["settings"]["open"][media], c["p"].get("places") or ())
            c["setting_from"] = "least used of the places their lines name"
        near_out = _nearest(cell, outside, same_at, pmin, smin)
        if near_out:
            drop("too close to an ad Meta already has (%s)" % near_out[0]["where"].split(" (")[0], c, near_out)
            continue
        near_in = _nearest(cell, [b["cell"] for b in batch], same_at, pmin, smin)
        if near_in:
            drop("too close to a row already picked in this lane", c, near_in)
            continue
        c["cell"] = cell
        batch.append(_row(c, len(batch) + 1, _closest(cell, outside, same_at)))
        used_lines.add((cell["person"], c["q"]["said"][0]))
        per_w[c["w"]["id"]] += 1
        per_p[cell["person"]] += 1
        per_s[cell["storyline"]] += 1
        setc[cell["setting"]] += 1
        imgc[cell["storyline"]] += 1 if media == "image" else 0
    return {"lane": lane, "gates": gate, "pool": len(pool), "looked": looked, "cuts": dict(cuts), "examples": ex, "batch": batch,
            "watch": {k: {x: round(v, 2) if isinstance(v, float) else v for x, v in d.items()} for k, d in table.items()}}


def daily(ctx, sizes=None):
    """The day's picks: every lane in order, each kept apart from everything Meta has and from the lanes before it.
    Rows are ranked 1..N across the lanes (video first)."""
    sizes = sizes or {k: v for k, v in CFG["daily"].items() if not k.startswith("_")}
    outside = list(ctx["outside"])
    lanes, flat = {}, []
    for lane in sizes:
        r = select(ctx, sizes[lane], lane, outside)
        for row in r["batch"]:
            outside.append(dict(row["cell"], where="picked today (%s)" % lane, name=row["id"]))
            row["lane_rank"], row["rank"] = row["rank"], len(flat) + 1
            flat.append(row)
        lanes[lane] = r
    sum_ = lambda k: sum(r[k] for r in lanes.values())                                          # noqa: E731
    cuts = Counter()
    for r in lanes.values():
        cuts.update(r["cuts"])
    first = lanes[next(iter(lanes))]
    return {"brand": ctx["brand"], "made": date.today().isoformat(), "total": ctx.get("total") or 0, "sizes": sizes, "lanes": lanes, "batch": flat,
            "gates": first["gates"], "pool": sum_("pool"), "looked": sum_("looked"), "cuts": dict(cuts), "examples": first["examples"], "watch": first["watch"],
            "signals_day": ctx.get("signals_day"), "outside": Counter(o["where"].split(" (")[0] for o in ctx["outside"]),
            "rules": {"apart": RULE["pair"]["min"], "seen": RULE["seen"]["min"], "caps": CFG["caps"], "same_opening_at": CFG["opening_same_at"]}}


def _nearest(cell, others, same_at, pmin, smin):
    """The first other ad this cell is too close to: (other, apart, seen) or None. Needs 4 known columns to judge."""
    for o in others:
        n, s, known, kseen = apart(cell, o, same_at)
        if known >= 4 and (n < math.ceil(pmin * known / len(COLS)) or s < seen_needed(smin, kseen)):
            return o, n, s
    return None


# The matrix's 3 of 7 is held in proportion to what is known of the other ad (3 of 7 known, 2 of 4): two ads are never
# called the same on columns nobody read.
def seen_needed(smin, kseen):
    """The seen rule over what is known of the other ad's look: all of it when 3 or more seen cells are known, one of
    two, none of one. Two ads cannot be called alike on a look nobody read."""
    return max(0, min(smin, kseen - 1))


def _closest(cell, others, same_at):
    best = None
    for o in others:
        n, s, known, _ = apart(cell, o, same_at)
        if known >= 4 and (best is None or n < best[1]):
            best = (o, n, s, known)
    return best


def _row(c, rank, near):
    w, p, q, cell, lane = c["w"], c["p"], c["q"], c["cell"], c["lane"]
    wx = c["watch_from"]
    watch_txt = ("holds: %d%% stop the scroll, %d%% reach a quarter, %.1f%% click" % (wx["hook"], wx["hold"], wx["ctr"]) if wx.get("video")
                 else "earns the click: %.1f%% click" % wx["ctr"]) + (" (%d measured)" % wx["n"] if wx.get("n") else " (no measured ad of this kind: the mean)")
    near_txt = "nothing it can be grouped with" if not near else "apart on %d of the %d things known of the nearest ad (%s, %s)" % (
        near[1], near[3] if len(near) > 3 else len(COLS), near[0].get("name") or near[0].get("person"), near[0].get("where", "this lane"))
    prof = p.get("profile") or {"id": p["id"], "label": p["id"].replace("-", " "), "named": False}
    pid = NAMING.point_id(q["kind"], q["point"])
    element = "%s/%s" % (prof["id"], pid)
    reason = "Proven: %s (%s sales%s). Format %s %s. Profile %s, %s (%s of their lines). Opens on their line: “%s”. %s." % (
        w["name"][:60], format(w["purchases"], ","), ", $%d a sale" % round(w["cpa"]) if w.get("cpa") else "", cell["storyline"] or "unknown", watch_txt,
        prof["label"], "thin" if c["thin"] else "full", format(p["rows_read"], ","), q["said"][0][:120], near_txt[0].upper() + near_txt[1:])
    return {"rank": rank, "lane": lane, "id": "%s|%s|%s" % (w["id"], element, lane), "element": element, "maker": STD["lanes"][lane]["maker"],
            "score": round(c["score"], 4), "parts": c["parts"],
            "winner": {k: w[k] for k in ("id", "name", "idea", "on_screen", "media", "purchases", "cpa")},
            "person": {"id": p["id"], "avatar": p["avatar"], "rows_read": p["rows_read"], "depth": "thin" if c["thin"] else "full"},
            "profile": {"id": prof["id"], "label": prof["label"], "named": prof.get("named", False)},
            "point": {"id": pid, "kind": q["kind"], "point": q["point"], "said": q["said"][:2]},
            "media": cell["media"], "cell": cell, "setting_from": c.get("setting_from", "the point's own words"),
            "nearest": None if not near else {"name": near[0].get("name"), "where": near[0].get("where", "this lane"), "apart": near[1], "seen": near[2], "known": near[3] if len(near) > 3 else None},
            "reason": reason}


# ---------------------------------------------------------------- start: the one way an ad is ordered

def start(out, wanted, runner=None, dest=None):
    """Order the picked rows the standard way: one `ask.json` each (creative-strategist ask.py new, which looks up the
    offer, spends nothing and invents nothing), then the lane's own door. wanted: rank numbers or 'all'. Returns
    [{"rank", "lane", "ask", "state", "door"}]; written to runs/creative-diversity/<brand>/filter/<date>-starts.json."""
    import subprocess
    brand = out["brand"]
    dims = json.loads((HERE / "dimensions.json").read_text())["fixed"]["offer"].get(brand) or {}
    ranks = {r["rank"] for r in out["batch"]} if wanted == "all" else set(wanted)
    done = []
    for r in out["batch"]:
        if r["rank"] not in ranks:
            continue
        label = "%s-%s-%s-%d" % (brand, out["made"], r["lane"], r["lane_rank"])
        cmd = [sys.executable, str(ROOT / "components" / "creative-strategist" / "machine" / "ask.py"), "new", "--brand", brand, "--ask", label,
               "--product", dims.get("product") or "", "--profile", r["profile"]["id"],
               "--said", r["point"]["said"][0], "--funnel", dims.get("page") or ""]
        p = (runner or subprocess.run)(cmd, capture_output=True, text=True, cwd=str(ROOT))
        text = (p.stdout or "") + (p.stderr or "")
        state = "started" if p.returncode == 0 else ("already started" if "exist" in text.lower() else "held: " + text.strip()[-160:])
        done.append({"rank": r["rank"], "lane": r["lane"], "ask": "runs/creative-strategist/%s/%s/ask.json" % (brand, label), "state": state,
                     "door": STD["lanes"][r["lane"]]["door"], "row": r["id"]})
    d = Path(dest) if dest else ROOT / "runs" / "creative-diversity" / brand / "filter"
    d.mkdir(parents=True, exist_ok=True)
    (d / (out["made"] + "-starts.json")).write_text(json.dumps(done, indent=1, ensure_ascii=False))
    return done


# ---------------------------------------------------------------- the command

def save(out):
    d = ROOT / "runs" / "creative-diversity" / out["brand"] / "filter"
    d.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(out, indent=1, ensure_ascii=False, default=str)
    (d / (out["made"] + ".json")).write_text(txt)
    (d / "latest.json").write_text(txt)
    return d / (out["made"] + ".json")


def show(out):
    lines = ["TODAY'S PICKS: %s, %d ads from %s possible variations" % (out["brand"].upper(), len(out["batch"]), format(out["total"], ",")), ""]
    for lane in out["lanes"]:
        rows = [r for r in out["batch"] if r["lane"] == lane]
        lines.append("== %s: %s (%d)" % (lane.upper(), STD["lanes"][lane]["means"], len(rows)))
        for r in rows:
            lines.append("%2d. %s x %s (%s) as %s -> %s" % (r["rank"], r["winner"]["name"][:40], r["profile"]["label"], r["point"]["kind"], r["cell"]["storyline"], r["cell"]["setting"]))
            lines.append("    " + r["reason"])
        lines.append("")
    lines += ["CUT BEFORE SCORING (first lane):"] + ["  %s: %s" % (k, format(v, ",")) for k, v in out["gates"].items()]
    lines += ["SCORED: %s; looked at %s best-first to fill the lanes:" % (format(out["pool"], ","), format(out["looked"], ","))]
    lines += ["  %s: %s" % (k, format(v, ",")) for k, v in sorted(out["cuts"].items(), key=lambda x: -x[1])]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brand")
    ap.add_argument("--lane", choices=tuple(k for k in CFG["lanes"] if not k.startswith("_")), help="only this lane (default: all three)")
    ap.add_argument("--size", type=int, help="picks in the lane (with --lane)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--start", help="order picks the standard way: 'all' or rank numbers like 1,2,9 (writes one ask.json each, spends nothing)")
    a = ap.parse_args(argv)
    ctx = load(a.brand)
    sizes = {a.lane: a.size or CFG["daily"][a.lane]} if a.lane else None
    out = daily(ctx, sizes)
    f = save(out)
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str) if a.json else show(out))
    print("\nsaved: %s" % f.relative_to(ROOT))
    if a.start:
        for x in start(out, "all" if a.start == "all" else {int(i) for i in a.start.split(",")}):
            print("  #%d %s: %s  ->  %s\n      then: %s" % (x["rank"], x["lane"], x["state"], x["ask"], x["door"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
