"""who_view: sales joined to who each ad was for. Facts only, read from files on disk; no ad account, no warehouse.

    winners.py who --brand <b> [--days N] [--source score|desk]

Sales, per ad:
  score (default)   runs/winners/<brand>/score/<asof>/score.json, the newest; with --days, the one whose window is
                    nearest N days. Every ad that spent in the window.
  desk              the newest runs/media-buying/<brand>/<asof>/report.json: the ads live that day. Life-to-date numbers;
                    with --days, that report's own window of N days. Ads already switched off are not in it.
Who, per ad: the brief number in its name (score's own join; else the ad id on its approval card in ADS-INDEX.json), then
components/briefs/aim.py `aim_of` for that brief. The avatar alone has one more answer, the ad set the ad ran in
(`adset_<brand>_<avatar>_<claim>`, off the cards and the desk reports), used only when the brief states none. An ad with no answer is in the `unknown` row, never dropped or guessed.
Writes runs/winners/<brand>/who-<date>/who.json + who.md.
"""
import datetime as dt, json, sys
from pathlib import Path

import score as S

DIMS = (("avatar", "Avatar"), ("sub", "Sub-avatar"), ("where", "Body part"), ("demographic", "Demographic on screen"), ("desire", "Desire"),
        ("awareness", "Awareness"), ("doubt", "Doubt"))
FEW = 10                      # under this many sales one more or fewer moves the cost per sale a lot: labelled, never judged
LONG = 15                     # a free-text dimension prints this many rows; the rest are one line


class BadInput(Exception):
    pass


def read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def span(d):
    """Days in a score file's window; None for an older file that states no start."""
    try:
        return (dt.date.fromisoformat(d["data_through"]) - dt.date.fromisoformat(d["since"])).days + 1
    except (KeyError, TypeError, ValueError):
        return None


def score_rows(root, brand, days=None):
    found = [(f, read(f)) for f in sorted((Path(root) / "runs" / "winners" / brand / "score").glob("*/score.json"))]
    found = [(f, d) for f, d in found if isinstance(d, dict) and isinstance(d.get("unmatched"), list)]
    if not found:
        raise BadInput(f"{brand} has no score on disk; run `winners.py score --brand {brand}` first")
    f, d = found[-1]
    if days:
        sized = [(abs(span(d) - days), -i, f, d) for i, (f, d) in enumerate(found) if span(d)]
        if sized:
            _, _, f, d = min(sized, key=lambda x: x[:2])
    window = "%s to %s" % (d["since"], d["data_through"]) if span(d) else "up to %s" % d.get("data_through")
    return (d.get("matched") or []) + d["unmatched"], {"source": str(f.relative_to(root)), "window": window, "days": span(d),
                                                       "note": None if not days or span(d) == days else
                                                       "asked for %d days; the nearest score on disk covers %s" % (days, span(d) or "an unstated number")}


def desk_rows(root, brand, days=None):
    found = sorted((Path(root) / "runs" / "media-buying" / brand).glob("*/report.json"))
    d = read(found[-1]) if found else None
    if not isinstance(d, dict):
        raise BadInput(f"{brand} has no desk report on disk")
    ads = []
    for x in d.get("flags") or []:
        if x.get("kind") != "ad":
            continue
        w = x if not days else (x.get("windows") or {}).get(str(days))
        if w is None:
            raise BadInput("the desk report of %s holds no %d-day window" % (d.get("asof"), days))
        ads.append({"ad_id": str(x["id"]), "ad_name": x["name"], "spend": w.get("spend") or 0, "purchases": (w.get("purchases") if not days else w.get("sales")) or 0})
    src = str(found[-1].relative_to(root))
    o = S.build(root, brand, res={"asof": d.get("asof"), "since": None, "data_through": d.get("asof"), "ads": ads, "source": src, "used": src})
    return o["matched"] + o["unmatched"], {"source": src, "window": ("the %d days" % days if days else "life to date") + " up to %s" % d.get("asof"), "days": days,
                                           "note": "only the ads live on %s; ads switched off before then are not in this file" % d.get("asof")}


def load_aims(root, brand):
    p = str(Path(root) / "components" / "briefs")
    if p not in sys.path:
        sys.path.append(p)
    import aim
    return aim.Aims(brand, repo=root)


def cards(root, brand):
    """{Meta ad id: its ADS-INDEX row}."""
    d = read(Path(root) / "runs" / "meta-upload" / brand / "ADS-INDEX.json") or {}
    return {str(i): r for r in d.get("briefs") or [] for i in r.get("meta_ad_ids") or []}


def ad_set_avatars(root, brand, by_ad):
    """{Meta ad id: the avatar its ad set names}, from the cards and every desk report on disk (the newest wins)."""
    named = []
    for r in {id(x): x for x in by_ad.values()}.values():
        named += [(m.get("ad_id"), m.get("ad_set")) for c in r.get("cards") or [] for m in c.get("meta_ads") or []]
    for f in sorted((Path(root) / "runs" / "media-buying" / brand).glob("*/report.json")):
        named += [(x.get("id"), x.get("adset")) for x in (read(f) or {}).get("flags") or [] if x.get("kind") == "ad"]
    out = {}
    for i, name in named:
        p = str(name or "").split("_")
        if i and len(p) == 4 and p[:2] == ["adset", brand]:
            out[str(i)] = p[2]
    return out


def brief_of(row, card, aims):
    """(brief key, how) for one ad, or (None, None)."""
    k = row.get("brief_key")
    if k and "_none_" in k:
        return row.get("brief_as_named") or k, "old brief code in the ad name"
    if k:
        return k, "brief number in the ad name"
    k = aims.N.full_brief_key(row.get("ad_name"))
    if k and k.startswith(aims.brand + "_"):
        return k, "brief number in the ad name"
    if card and card.get("number"):
        return card["brief"], "its approval card"
    return None, None


def join(root, brand, rows, aims=None):
    aims, by_ad = aims or load_aims(root, brand), cards(root, brand)
    sets = ad_set_avatars(root, brand, by_ad)
    out, memo = [], {}
    for r in rows:
        card = by_ad.get(str(r.get("ad_id")))
        key, how = brief_of(r, card, aims)
        if key and key not in memo:
            memo[key] = aims.of(key)
        a = dict(memo.get(key) or {})
        for k, c in (("avatar", "avatar"), ("sub", "sub_avatar"), ("demographic", "face")):
            if card and not a.get(k) and card.get(c) and a.get("avatar") in (None, card.get("avatar")):
                a[k] = card[c]
        a["where"] = body_part(brand, a.get("avatar"), a.get("sub"))
        src = "its brief or card" if a.get("avatar") else None
        if not src and sets.get(str(r.get("ad_id"))):
            a["avatar"], src = sets[str(r["ad_id"])], "its ad set"
        out.append({"ad_id": r.get("ad_id"), "ad_name": r.get("ad_name"), "spend": float(r.get("spend") or 0), "purchases": float(r.get("purchases") or 0),
                    "brief": key, "joined_by": how, "avatar_from": src, **{k: a.get(k) for k, _ in DIMS}})
    return out


def body_part(brand, avatar, sub):
    """The body part the person was about (`where-<part>` in components/naming/people.py), or None."""
    if not (avatar and sub):
        return None
    p = str(Path(__file__).resolve().parents[1] / "naming")
    if p not in sys.path:
        sys.path.append(p)
    import people
    try:
        n = people.new_names(brand, avatar, sub)[1]
    except Exception:                                        # noqa: BLE001 -- a name nobody knows has no part
        return None
    return n[len("where-"):] if n.startswith("where-") else None


def sums(rs):
    sp, b = round(sum(r["spend"] for r in rs), 2), sum(r["purchases"] for r in rs)
    return {"ads": len(rs), "spend": sp, "purchases": b, "cpa": round(sp / b, 2) if b else None, "few": b < FEW}


def pct(a, b):
    return round(100.0 * a / b, 1) if b else 0.0


def by_dim(rows, dim):
    g = {}
    for r in rows:
        if r[dim] is not None:
            g.setdefault("%s / %s" % (r["avatar"], r[dim]) if dim == "sub" else r[dim], []).append(r)
    known = [r for r in rows if r[dim] is not None]
    unk = [r for r in rows if r[dim] is None]
    t, k = sums(rows), sums(known)
    return {"rows": sorted(({"value": v, **sums(rs)} for v, rs in g.items()), key=lambda x: (-x["spend"], x["value"])),
            "unknown": {**sums(unk), "no_brief": sums([r for r in unk if not r["brief"]]), "brief_does_not_say": sums([r for r in unk if r["brief"]])},
            "coverage": {m: pct(k[m], t[m]) for m in ("ads", "spend", "purchases")}}


def build(root, brand, days=None, source="score", aims=None):
    rows, src = (desk_rows if source == "desk" else score_rows)(Path(root), brand, days)
    joined = join(root, brand, rows, aims)
    how = {}
    for r in joined:
        how.setdefault(r["joined_by"] or "no brief found", []).append(r)
    return {"brand": brand, "made": dt.datetime.now().isoformat(timespec="seconds"), **src, "few_sales_under": FEW, "total": sums(joined),
            "joined_by": {k: sums(v) for k, v in sorted(how.items())}, "by": {k: by_dim(joined, k) for k, _ in DIMS}, "ads": joined}


def money(x):
    return "-" if x is None else "${:,.2f}".format(x)


def line(name, s):
    name = str(name).replace("|", "/")
    return "| %s | %d | %s | %g | %s | %s |" % (name if len(name) <= 110 else name[:107] + "...", s["ads"], money(s["spend"]), s["purchases"], money(s["cpa"]), "few sales" if s["few"] and s["ads"] else "")


def render(o):
    t = o["total"]
    L = ["# Sales by who the ad was for: %s" % o["brand"], "",
         "Window: %s. Sales from `%s`. Who from each ad's brief (`components/briefs/aim.py`). Made %s." % (o["window"], o["source"], o["made"][:10])]
    if o.get("note"):
        L += ["", "Note: %s." % o["note"]]
    L += ["", "%d ads, %s spent, %g purchases, %s per purchase. Purchases are Meta's own count. `few sales` marks a row under %d purchases. Numbers only, no calls." % (
        t["ads"], money(t["spend"]), t["purchases"], money(t["cpa"]), o["few_sales_under"]), "",
        "## How much could be joined", "", "| | Ads known | Spend known | Purchases known |", "|---|---:|---:|---:|"]
    L += ["| %s | %s%% | %s%% | %s%% |" % (title, *(o["by"][k]["coverage"][m] for m in ("ads", "spend", "purchases"))) for k, title in DIMS]
    L += ["", "| How the brief was found | Ads | Spend | Purchases | Per purchase | |", "|---|---:|---:|---:|---:|---|"] + [line(k, s) for k, s in o["joined_by"].items()]
    for k, title in DIMS:
        d = o["by"][k]
        u = d["unknown"]
        L += ["", "## " + title, "", "| %s | Ads | Spend | Purchases | Per purchase | |" % title, "|---|---:|---:|---:|---:|---|"]
        L += [line("none (no face on screen)" if k == "demographic" and x["value"] == "none" else x["value"], x) for x in d["rows"][:LONG]]
        if len(d["rows"]) > LONG:
            rest = d["rows"][LONG:]
            s = {"ads": sum(x["ads"] for x in rest), "spend": sum(x["spend"] for x in rest), "purchases": sum(x["purchases"] for x in rest)}
            L += [line("%d more (in who.json)" % len(rest), {**s, "cpa": s["spend"] / s["purchases"] if s["purchases"] else None, "few": s["purchases"] < FEW})]
        L += [line("unknown", u), "", "Unknown is %d ads (%s) with no brief found and %d ads (%s) whose brief does not say." % (
            u["no_brief"]["ads"], money(u["no_brief"]["spend"]), u["brief_does_not_say"]["ads"], money(u["brief_does_not_say"]["spend"]))]
        n = [r for r in o["ads"] if r["avatar_from"] == "its ad set"]
        if k == "avatar" and n:
            L += ["", "%d of the known ads (%s) have their avatar from the ad set they ran in, because their brief states none." % (len(n), money(sum(r["spend"] for r in n)))]
        if k == "desire" and d["rows"]:
            L += ["", "Desire is free text: two ads share a row only when their runs state it in the same words."]
    return "\n".join(L) + "\n"


def write(root, o, today=None):
    d = Path(root) / "runs" / "winners" / o["brand"] / ("who-" + (today or dt.date.today().isoformat()))
    d.mkdir(parents=True, exist_ok=True)
    stem = "who" if "/media-buying/" not in o["source"] else "who-desk"
    (d / (stem + ".json")).write_text(json.dumps(o, indent=1, ensure_ascii=False) + "\n")
    (d / (stem + ".md")).write_text(render(o))
    return d / (stem + ".md")
