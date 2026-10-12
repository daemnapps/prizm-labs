#!/usr/bin/env python3
"""Grade one brand's Meta account against the Meta strategy (rules.json).

    python3 components/meta-strategy/audit.py brand-a

Reads:
  - the day's structure read (campaigns · ad sets · ads with status and budget),
    taken once per brand per day and saved (the owner: "do not pull on Meta too much")
  - the latest creative-diversity pull + matrix (runs/creative-diversity/<brand>/)
  - each saved asset's own file, for shape and sound (ffprobe, local)
  - the offer's break-even (lab/media-buying/<brand>-offer-lines.json)
Writes runs/meta-strategy/<brand>/<date>/scorecard.json.
"""
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RULES = json.loads((HERE / "rules.json").read_text())


def offer_of(brand):
    """The brand's one offer — rules.json offers[brand], else brands/<brand>/meta/offer.json."""
    o = RULES.get("offers", {}).get(brand)
    if o is None:
        f = ROOT / "brands" / brand / "meta" / "offer.json"
        o = json.loads(f.read_text()) if f.is_file() else {}
    return o
LIVE = ("ACTIVE", "IN_PROCESS", "WITH_ISSUES", "PENDING_REVIEW")


def structure(brand, day):
    """Campaigns, ad sets and live ads from the team warehouse (meta_ads) — never
    from Meta directly (the owner, 2026-10-08). Saved once per brand per day."""
    out = ROOT / "runs" / "meta-strategy" / brand / day
    f = out / "structure.json"
    if f.exists():
        return json.loads(f.read_text())
    acct = json.loads((ROOT / "brands" / brand / "meta" / "account.json").read_text())["account_id"]
    q = ("select ad_id, ad_name, adset_id, adset_name, campaign_id, campaign_name, effective_status "
         f"from meta_ads where account_id = '{acct}' and effective_status in ('ACTIVE','IN_PROCESS','WITH_ISSUES','PENDING_REVIEW')")
    r = subprocess.run(["psql", _shared_keys().lookup("SUPABASE_DB_URL", required=True), "-At", "-F", "\t", "-c", q],
                       capture_output=True, text=True, timeout=120)
    if r.returncode:
        sys.exit(f"warehouse read failed: {r.stderr[:300]}")
    ads = [dict(zip(["id", "name", "adset_id", "adset_name", "campaign_id", "campaign_name", "effective_status"],
                    line.split("\t"))) for line in r.stdout.splitlines() if line.strip()]
    sets = {a["adset_id"]: {"id": a["adset_id"], "name": a["adset_name"], "campaign_id": a["campaign_id"],
                            "effective_status": "ACTIVE"} for a in ads}
    camps = {a["campaign_id"]: {"id": a["campaign_id"], "name": a["campaign_name"], "effective_status": "ACTIVE"} for a in ads}
    data = {"read": day, "source": "warehouse meta_ads", "campaigns": list(camps.values()),
            "ad_sets": list(sets.values()), "ads": ads}
    out.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=1))
    return data


def shape(path):
    """(ratio label, has_audio) from the file itself."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "stream=codec_type,width,height", "-of", "json", str(path)],
                           capture_output=True, text=True, timeout=60)
        streams = json.loads(r.stdout or "{}").get("streams", [])
    except Exception:  # noqa: BLE001
        return "unknown", None
    v = next((s for s in streams if s.get("codec_type") == "video" and s.get("width")), None)
    audio = any(s.get("codec_type") == "audio" for s in streams)
    if not v:
        return "unknown", audio
    w, h = v["width"], v["height"]
    r = h / w if w else 0
    label = "9x16" if r >= 1.6 else "4x5" if r >= 1.15 else "1x1" if r >= 0.9 else "landscape"
    return label, audio


def cpa(brand):
    f = ROOT / "lab" / "media-buying" / f"{brand}-offer-lines.json"
    want = offer_of(brand).get("cpa_offer")
    if not f.exists() or not want:
        return None, "no offer lines for this brand yet"
    rows = [r for r in json.loads(f.read_text())["rows"] if r["group"] == want]
    if not rows:
        return None, f"no row for {want}"
    return min(r["break_even_cpa"] for r in rows), f"{want}: break-even per purchase"


def latest(brand):
    base = ROOT / "runs" / "creative-diversity" / brand
    days = sorted(p.name for p in base.iterdir() if (p / "assets.json").exists()) if base.exists() else []
    return base / days[-1] if days else None


def grade(ok, warn=False):
    return "pass" if ok else ("warn" if warn else "fail")


def audit(brand, day=None):
    day = day or date.today().isoformat()
    offer = offer_of(brand)
    st = structure(brand, day)
    camps = {c["id"]: c for c in st["campaigns"]}
    sets = {s["id"]: s for s in st["ad_sets"]}
    ads_by_set = defaultdict(list)
    for a in st["ads"]:
        if a.get("adset_id") in sets:
            ads_by_set[a["adset_id"]].append(a)
    live_sets = [s for s in sets.values() if ads_by_set[s["id"]]]
    is_offer = lambda c: offer["campaign_product"] in c["name"]  # noqa: E731
    offer_camps = [c for c in camps.values() if is_offer(c)]
    other_camps = [c for c in camps.values() if not is_offer(c) and any(s["campaign_id"] == c["id"] for s in live_sets)]
    checks = []

    def add(rule, status, said, numbers=None):
        checks.append({"rule": rule, "status": status, "said": said, "numbers": numbers or {}})

    # structure
    add("one-campaign-per-offer",
        grade(len(offer_camps) == 1 and not other_camps, warn=len(offer_camps) == 1),
        f"{len(offer_camps)} running campaign(s) for the {offer['product']} offer; "
        f"{len(other_camps)} other campaign(s) spending on something else",
        {"offer_campaigns": [c["name"] for c in offer_camps], "other_campaigns": [c["name"] for c in other_camps]})
    for c in offer_camps or []:
        cs = [s for s in live_sets if s["campaign_id"] == c["id"]]
        odd = [s["name"] for s in cs if not s["name"].startswith(f"adset_{brand}_")]
        add("ad-set-is-who", grade(not odd, warn=True),
            f"{c['name']}: {len(cs)} live ad set(s), one per avatar + angle"
            + (f"; not named avatar + angle: {', '.join(odd)}" if odd else ""), {"ad_sets": [s["name"] for s in cs]})
        for s in cs:
            n = len(ads_by_set[s["id"]])
            r = next(x for x in RULES["structure"] if x["id"] == "ads-per-ad-set")
            add("ads-per-ad-set", grade(r["min"] <= n <= r["max"], warn=0 < n <= r["hard_max"]),
                f"{s['name']}: {n} live ad(s) (aim {r['min']}–{r['max']})", {"ads": n})
            add("optimise-for-value", grade(s.get("optimization_goal") == "VALUE", warn=True),
                f"{s['name']}: optimises for {s.get('optimization_goal')}")
        budget = int(c.get("daily_budget") or 0) / 100
        need, why = cpa(brand)
        if need:
            n_sets = max(1, len([s for s in live_sets if s["campaign_id"] == c["id"]]))
            target = round(need * RULES["budget"]["results_per_week"] / 7 * n_sets)
            add("budget", grade(budget >= target, warn=budget > 0),
                f"{c['name']}: ${budget:.0f}/day vs ~${target}/day for {n_sets} ad set(s) to exit learning "
                f"(≈7 × ${need:.2f} each, {why})",
                {"daily": budget, "needed": target, "results_per_week_at_budget": round(budget * 7 / need)})
    if not offer_camps:
        add("budget", "fail", f"no running campaign for the {offer['product']} offer")

    # creative + assets, from the saved pull
    run = latest(brand)
    if run:
        assets = json.loads((run / "assets.json").read_text())["assets"]
        mx = json.loads((run / "matrix.json").read_text()) if (run / "matrix.json").exists() else None
        on = [a for a in assets if any(mk in l for l in a.get("links", []) for mk in offer["match"])]
        add("one-offer", grade(len(on) == len(assets), warn=bool(on)),
            f"{len(on)} of {len(assets)} running creatives link to the one offer page", {"on": len(on), "all": len(assets)})
        if mx:
            v = mx["verdicts"]
            add("diversification", grade(v.get("variation", 0) == 0, warn=v.get("variation", 0) <= len(mx["items"]) * 0.1),
                f"{v.get('new', 0)} new · {v.get('risky', 0)} risky · {v.get('variation', 0)} variations of the same creative "
                f"({len(mx['clusters'])} look-alike groups)", dict(v))
        else:
            add("diversification", "warn", "not tagged yet — run creative-diversity tag.py + matrix.py")
        reused = [a for a in assets if len(a.get("ads", [])) > 1]
        add("new-footage", grade(not reused, warn=True),
            f"{len(reused)} image(s)/video(s) running in more than one ad (one creative, counted once for fatigue)",
            {"reused": len(reused)})
        shapes = []
        for a in assets:
            if a.get("file") and not a.get("thumb_only"):
                ratio, audio = shape(ROOT / a["file"])
                shapes.append((a["kind"], ratio, audio))
        vids = [s for s in shapes if s[0] == "video"]
        vert_audio = [s for s in vids if s[1] == "9x16" and s[2]]
        silent_vert = [s for s in vids if s[1] == "9x16" and s[2] is False]
        share = len(vert_audio) / len(shapes) if shapes else 0
        add("format-mix", grade(any(s[0] == "image" for s in shapes) and bool(vids) and bool(vert_audio)),
            f"{sum(s[0] == 'image' for s in shapes)} images · {len(vids)} videos · {len(vert_audio)} 9:16 with sound",
            {"by_ratio": dict(Counter(s[1] for s in shapes))})
        add("vertical-audio-share", grade(share >= 0.2), f"{share:.0%} of readable assets are 9:16 video with sound (Meta: 20%+)",
            {"share": round(share, 3)})
        add("sound-on-reels", grade(not silent_vert), f"{len(silent_vert)} 9:16 video(s) with no sound track")
    out = ROOT / "runs" / "meta-strategy" / brand / day
    out.mkdir(parents=True, exist_ok=True)
    card = {"brand": brand, "read": day, "offer": offer, "library": str(run.relative_to(ROOT)) if run else None,
            "score": dict(Counter(c["status"] for c in checks)), "checks": checks}
    (out / "scorecard.json").write_text(json.dumps(card, indent=1))
    print(f"{brand}: {card['score']}")
    for c in checks:
        print(f"  {c['status']:<4} {c['rule']:<22} {c['said']}")
    return card


if __name__ == "__main__":
    audit(*sys.argv[1:3])
