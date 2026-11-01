#!/usr/bin/env python3
"""Build the creative-diversity matrix from a tagged pull. Never calls Meta.

    python3 components/creative-diversity/matrix.py brand-a [date]

Reads runs/creative-diversity/<brand>/<date>/{assets,ads,tags}.json and writes:
  matrix.json                                   the whole read, for the page
  brands/<brand>/core-avatars/<avatar>/diversity.json   each avatar's coverage + gaps
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LEVELS = ["unaware", "problem-aware", "solution-aware", "product-aware", "most-aware"]
BIG = ["who", "awareness", "argument", "format", "face", "setting", "look"]
FORMAT_FAMILY = {"video-format": "video", "video-structure": "video",
                 "image-format": "image", "carousel-format": "carousel"}


def face_of(t):
    f = t.get("face") or {}
    if not f or str(f.get("people", 0)) in ("0", "") or f.get("gender") in ("", "none", None):
        return "none"
    return f"{f.get('gender')}/{f.get('age_band')}/{f.get('ethnic_appearance')}"


def moves(t):
    return {"who": t.get("sub_avatar"), "awareness": t.get("awareness"),
            "argument": t.get("angle"), "format": t.get("format"),
            "face": face_of(t), "setting": t.get("setting"), "look": t.get("style")}


def distance(a, b):
    """How many big moves differ. Unclear on either side is not counted as a move."""
    d, diff = 0, []
    for k in BIG:
        x, y = a.get(k), b.get(k)
        if x in (None, "", "unclear") or y in (None, "", "unclear"):
            continue
        if x != y:
            d += 1
            diff.append(k)
    return d, diff


def avatar_of(brand, sub):
    av = json.loads((ROOT / "brands" / brand / "core-avatars" / "avatars.json").read_text())["avatars"]
    for a in av:
        if sub == a["id"] or sub in (a.get("sub_avatars") or []):
            return a["id"]
    return "unclear"


def build(brand, day=None):
    base = ROOT / "runs" / "creative-diversity" / brand
    day = day or sorted(p.name for p in base.iterdir() if (p / "tags.json").exists())[-1]
    run = base / day
    assets = {a["asset"]: a for a in json.loads((run / "assets.json").read_text())["assets"]}
    pulled = json.loads((run / "assets.json").read_text())
    ads = json.loads((run / "ads.json").read_text())["ads"]
    tags = json.loads((run / "tags.json").read_text())["tags"]
    dims = json.loads((HERE / "dimensions.json").read_text())
    offer = json.loads((ROOT / "brands" / brand / "strategy" / "offer-page.json").read_text())
    settings = json.loads((ROOT / "brands" / brand / "strategy" / "settings.json").read_text())["settings"]
    av = json.loads((ROOT / "brands" / brand / "core-avatars" / "avatars.json").read_text())["avatars"]

    items = []
    for key, t in tags.items():
        a = assets.get(key, {})
        on_offer = any(m in l for l in a.get("links", []) for m in offer["match"])
        items.append({
            "asset": key, "kind": a.get("kind"), "file": a.get("file"),
            "spend_30d": round(a.get("spend_30d", 0), 2), "ads": len(a.get("ads", [])),
            "links": a.get("links", []), "on_offer": on_offer,
            "avatar": avatar_of(brand, t.get("sub_avatar")),
            "moves": moves(t), "tag": t,
        })

    # nearest neighbour + clusters Meta will likely read as one ad
    parent = {i["asset"]: i["asset"] for i in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in items:
        best = None
        for j in items:
            if i is j:
                continue
            d, diff = distance(i["moves"], j["moves"])
            if best is None or d < best[0]:
                best = (d, j["asset"], diff)
            if d <= dims["rule"]["variation_at_or_below"]:
                parent[find(i["asset"])] = find(j["asset"])
        i["nearest"] = {"moves": best[0], "asset": best[1], "differs_on": best[2]} if best else None
        n = best[0] if best else 99
        i["verdict"] = ("variation" if n <= dims["rule"]["variation_at_or_below"]
                        else "risky" if n == dims["rule"]["risky"] else "new")

    groups = defaultdict(list)
    for i in items:
        groups[find(i["asset"])].append(i["asset"])
    clusters = sorted([g for g in groups.values() if len(g) > 1], key=len, reverse=True)
    by_key = {i["asset"]: i for i in items}
    cluster_rows = [{"size": len(g), "spend_30d": round(sum(by_key[a]["spend_30d"] for a in g), 2),
                     "shared": {k: by_key[g[0]]["moves"][k] for k in BIG
                                if len({by_key[a]["moves"][k] for a in g}) == 1},
                     "assets": g} for g in clusters]

    # the grid: awareness x format family, and awareness x avatar
    grid = {lv: Counter() for lv in LEVELS + ["unclear"]}
    grid_spend = {lv: Counter() for lv in LEVELS + ["unclear"]}
    by_avatar = defaultdict(lambda: Counter())
    formats_at = defaultdict(Counter)
    for i in items:
        lv = i["moves"]["awareness"] if i["moves"]["awareness"] in LEVELS else "unclear"
        fam = FORMAT_FAMILY.get(i["tag"].get("format_list"), i["kind"] or "unclear")
        grid[lv][fam] += 1
        grid_spend[lv][fam] += i["spend_30d"]
        by_avatar[i["avatar"]][lv] += 1
        formats_at[lv][i["moves"]["format"]] += 1

    total = len(items) or 1
    spread = {lv: {"have": round(sum(grid[lv].values()) / total, 3),
                   "target": dims["spread"]["target_share"][lv]} for lv in LEVELS}

    count = lambda k: Counter(i["moves"][k] for i in items).most_common()  # noqa: E731
    fixed = {
        "on_offer": sum(i["on_offer"] for i in items),
        "off_offer_links": Counter(l.split("?")[0] for i in items if not i["on_offer"] for l in i["links"]).most_common(8),
        "products_shown": Counter(i["tag"].get("product_shown", "") for i in items).most_common(8),
        "core_message": Counter(i["tag"].get("core_message") for i in items),
        "their_words": Counter(i["tag"].get("their_words") for i in items),
        "looks_ai": Counter(i["tag"].get("looks_ai") for i in items),
        "slop_risk": Counter(i["tag"].get("slop_risk") for i in items),
        "sophistication_lead": Counter(i["tag"].get("sophistication_lead") for i in items),
    }

    # gaps per avatar: empty awareness levels, settings never used, faces missing
    used_settings = {i["moves"]["setting"] for i in items}
    avatars_out = {}
    for a in av:
        mine = [i for i in items if i["avatar"] == a["id"]]
        subs_used = Counter(i["moves"]["who"] for i in mine)
        gaps = []
        for lv in LEVELS:
            if not any(i["moves"]["awareness"] == lv for i in mine):
                gaps.append(f"nothing live at {lv}")
        for s in a.get("sub_avatars") or []:
            if not subs_used.get(s):
                gaps.append(f"no live ad for sub-avatar {s}")
        unused = [s["id"] for s in settings if a["id"] in s.get("avatars", []) and s["id"] not in used_settings]
        avatars_out[a["id"]] = {
            "label": a.get("label"), "status": a.get("status"), "live_assets": len(mine),
            "spend_30d": round(sum(i["spend_30d"] for i in mine), 2),
            "awareness": {lv: sum(1 for i in mine if i["moves"]["awareness"] == lv) for lv in LEVELS},
            "sub_avatars": dict(subs_used),
            "formats": dict(Counter(i["moves"]["format"] for i in mine).most_common()),
            "settings": dict(Counter(i["moves"]["setting"] for i in mine).most_common()),
            "faces": dict(Counter(i["moves"]["face"] for i in mine).most_common()),
            "angles": dict(Counter(i["moves"]["argument"] for i in mine).most_common()),
            "variations_of_same_creative": sum(1 for i in mine if i["verdict"] == "variation"),
            "gaps": gaps, "settings_never_used": unused,
        }

    matrix = {
        "brand": brand, "pulled": day, "mode": pulled.get("mode"),
        "rule": dims["rule"], "offer": offer,
        "assets": len(items), "ads": len(ads),
        "untagged": [k for k, a in assets.items() if k not in tags],
        "verdicts": Counter(i["verdict"] for i in items),
        "spread": spread,
        "grid": {lv: dict(grid[lv]) for lv in grid},
        "grid_spend": {lv: {k: round(v, 2) for k, v in grid_spend[lv].items()} for lv in grid_spend},
        "formats_at": {lv: dict(c.most_common()) for lv, c in formats_at.items()},
        "by_avatar": {k: dict(v) for k, v in by_avatar.items()},
        "counts": {k: count(k) for k in BIG},
        "fixed": fixed, "clusters": cluster_rows, "avatars": avatars_out,
        "items": sorted(items, key=lambda i: -i["spend_30d"]),
    }
    (run / "matrix.json").write_text(json.dumps(matrix, indent=1, default=list))

    for a in av:
        folder = ROOT / "brands" / brand / a["folder"]
        if folder.exists():
            (folder / "diversity.json").write_text(json.dumps({
                "_what": "This avatar's creative-diversity read: what is live for them, at which awareness level, in which formats, faces and settings, and the gaps the next briefs should fill. Generated by components/creative-diversity/matrix.py from the live Meta library — never hand-edited.",
                "read_on": day, "source": str((run / "matrix.json").relative_to(ROOT)),
                **avatars_out[a["id"]]}, indent=1))
    print(f"{brand}: {len(items)} assets · {dict(matrix['verdicts'])} · "
          f"{len(cluster_rows)} look-alike groups · on offer {fixed['on_offer']}/{len(items)}")
    return matrix


if __name__ == "__main__":
    build(*sys.argv[1:3])
