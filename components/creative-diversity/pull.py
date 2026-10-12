#!/usr/bin/env python3
"""Pull the live ad library for one brand, straight from Meta.

The live library is every ACTIVE ad. If the account has none running (paused),
it falls back to every ad that spent in the last 30 days, and says so.

Each ad is broken into its assets (a video, an image, or the cards of a
carousel) and each asset's media is downloaded once, so the tagger reads the
real ad, not a thumbnail.

    python3 components/creative-diversity/pull.py brand-b
    python3 components/creative-diversity/pull.py brand-a

Writes runs/creative-diversity/<brand>/<date>/ads.json, assets.json, media/.
"""
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "components" / "meta-upload"))
from meta import Meta  # noqa: E402


def _account(m):
    """The ad account id comes from the environment (META_AD_ACCOUNT_ID), never from this file."""
    return os.environ.get("META_AD_ACCOUNT_ID") or m.ACCOUNT

NO_META = ("Direct Meta reads are off (the owner, 2026-10-08: \"You're not supposed to pull from Meta anymore\"). "
           "Meta numbers come from the team warehouse (Supabase meta_ads / meta_ad_insights; local copy "
           "$WAREHOUSE_DB). What the warehouse lacks — per-piece grades, ad media — "
           "has to be added to the warehouse sync, not read here.")


AD_FIELDS = ("id,name,effective_status,adset{id,name},campaign{id,name},"
             "creative{id,object_type,body,title,thumbnail_url,image_url,"
             "object_story_spec,asset_feed_spec}")


def paged(m, path, **params):
    r = m.get(path, **params)
    out = list(r.get("data", []))
    while r.get("paging", {}).get("next"):
        after = r["paging"].get("cursors", {}).get("after")
        if not after:
            break
        r = m.get(path, after=after, **params)
        out += r.get("data", [])
    return out


def spend_30d(m):
    rows = paged(m, f"act_{_account(m)}/insights", level="ad",
                 fields="ad_id,spend", date_preset="last_30d", limit=500)
    return {r["ad_id"]: float(r["spend"]) for r in rows}


def assets_of(creative):
    """[(kind, ref)] for every piece of media in a creative."""
    out = []
    oss = creative.get("object_story_spec") or {}
    afs = creative.get("asset_feed_spec") or {}
    vd = oss.get("video_data") or {}
    if vd.get("video_id"):
        out.append(("video", vd["video_id"], vd.get("image_url")))
    ld = oss.get("link_data") or {}
    for child in ld.get("child_attachments") or []:
        if child.get("video_id"):
            out.append(("video", child["video_id"], child.get("picture")))
        elif child.get("image_hash") or child.get("picture"):
            out.append(("image", child.get("image_hash") or child.get("picture"), child.get("picture")))
    if not ld.get("child_attachments") and (ld.get("image_hash") or ld.get("picture")):
        out.append(("image", ld.get("image_hash") or ld.get("picture"), ld.get("picture")))
    for v in afs.get("videos") or []:
        out.append(("video", v["video_id"], v.get("thumbnail_url")))
    for i in afs.get("images") or []:
        out.append(("image", i.get("hash") or i.get("url"), i.get("url")))
    if not out and creative.get("image_url"):
        out.append(("image", creative["image_url"], creative["image_url"]))
    if not out and creative.get("thumbnail_url"):
        out.append(("image", creative["thumbnail_url"], creative["thumbnail_url"]))
    seen, uniq = set(), []
    for a in out:
        if a[1] not in seen:
            seen.add(a[1])
            uniq.append(a)
    return uniq


def copy_of(creative):
    oss = creative.get("object_story_spec") or {}
    afs = creative.get("asset_feed_spec") or {}
    ld, vd = oss.get("link_data") or {}, oss.get("video_data") or {}
    bodies = [b["text"] for b in afs.get("bodies") or []] or \
        [t for t in [ld.get("message"), vd.get("message"), creative.get("body")] if t]
    titles = [t["text"] for t in afs.get("titles") or []] or \
        [t for t in [ld.get("name"), vd.get("title"), creative.get("title")] if t]
    links = [l.get("website_url") for l in afs.get("link_urls") or [] if l.get("website_url")]
    cta = (vd.get("call_to_action") or ld.get("call_to_action") or {}).get("value", {})
    links += [x for x in [cta.get("link"), ld.get("link")] if x]
    return bodies, titles, list(dict.fromkeys(links))


def fetch(url, path):
    if path.exists() and path.stat().st_size:
        return True
    try:
        with urllib.request.urlopen(url, timeout=300) as r:
            path.write_bytes(r.read())
        return True
    except Exception as e:  # noqa: BLE001 — a missing file is reported, not fatal
        print(f"  could not download {path.name}: {e}", file=sys.stderr)
        return False


def stills(m, brand, assets, ads_by_id, out):
    """Assets whose media could not be reached (images held outside this ad
    account) get the ad's full-size preview still, in batched calls of 50 ads."""
    need = [s for s in assets.values() if not s.get("file")]
    ad_ids = list(dict.fromkeys(s["ads"][0] for s in need))
    thumb = {}
    for i in range(0, len(ad_ids), 50):
        for a in paged(m, f"act_{_account(m)}/ads", limit=200,
                       fields="id,creative.thumbnail_width(1080).thumbnail_height(1080){thumbnail_url}",
                       filtering=json.dumps([{"field": "ad.id", "operator": "IN",
                                              "value": ad_ids[i:i + 50]}])):
            thumb[a["id"]] = (a.get("creative") or {}).get("thumbnail_url")
    for s in need:
        url = thumb.get(s["ads"][0])
        f = out / "media" / (s["asset"].replace("/", "_")[:80] + ".still.jpg")
        if url and fetch(url, f):
            s["file"] = str(f.relative_to(ROOT))
            s["thumb_only"] = True
    return len(need), sum(1 for s in need if s.get("file"))


def main(brand, day=None):
    sys.exit(NO_META)
    day = day or date.today().isoformat()
    out = ROOT / "runs" / "creative-diversity" / brand / day
    # the owner, 2026-10-06: "do not pull on Meta too much for anything."
    # One pull per brand per day; everything downstream reads the saved copy.
    if (out / "assets.json").exists() and "--force" not in sys.argv:
        print(f"{brand}: already pulled today ({out.relative_to(ROOT)}). "
              "Not calling Meta again. Use the saved copy.")
        return
    (out / "media").mkdir(parents=True, exist_ok=True)
    m = Meta(brand)
    page = Meta(brand, tok=m.get(m.PAGE, fields="access_token")["access_token"])

    ads = paged(m, f"act_{_account(m)}/ads", fields=AD_FIELDS,
                effective_status='["ACTIVE"]', limit=200)
    spend = spend_30d(m)
    mode = "active"
    if not ads:
        mode = "spent-last-30-days (nothing active)"
        ids = [a for a, s in spend.items() if s > 0]
        ads = []
        for i in range(0, len(ids), 50):
            ads += paged(m, f"act_{_account(m)}/ads", fields=AD_FIELDS, limit=200,
                         filtering=json.dumps([{"field": "ad.id", "operator": "IN",
                                                "value": ids[i:i + 50]}]))
    print(f"{brand}: {len(ads)} ads ({mode})")

    assets, rows = {}, []
    hashes = set()
    for a in ads:
        c = a.get("creative") or {}
        bodies, titles, links = copy_of(c)
        refs = []
        for kind, ref, thumb in assets_of(c):
            key = f"{kind}-{ref}" if len(str(ref)) < 60 else f"{kind}-{abs(hash(ref))}"
            refs.append(key)
            assets.setdefault(key, {"asset": key, "kind": kind, "ref": ref,
                                    "thumb": thumb, "ads": [], "bodies": [],
                                    "titles": [], "links": [], "spend_30d": 0.0})
            s = assets[key]
            s["ads"].append(a["id"])
            s["spend_30d"] += spend.get(a["id"], 0.0)
            for lst, vals in (("bodies", bodies), ("titles", titles), ("links", links)):
                s[lst] += [v for v in vals if v not in s[lst]]
            if kind == "image" and len(str(ref)) == 32:
                hashes.add(ref)
        rows.append({"ad_id": a["id"], "name": a.get("name"),
                     "status": a.get("effective_status"),
                     "adset": (a.get("adset") or {}).get("name"),
                     "adset_id": (a.get("adset") or {}).get("id"),
                     "campaign": (a.get("campaign") or {}).get("name"),
                     "spend_30d": spend.get(a["id"], 0.0),
                     "assets": refs, "links": links})

    # image hashes -> full-size urls
    hl = list(hashes)
    for i in range(0, len(hl), 50):
        r = m.get(f"act_{_account(m)}/adimages", hashes=json.dumps(hl[i:i + 50]),
                  fields="hash,url,permalink_url")
        for img in r.get("data", []):
            for s in assets.values():
                if s["ref"] == img["hash"]:
                    s["url"] = img.get("url")

    for s in assets.values():
        if s["kind"] == "video":
            try:
                v = page.get(s["ref"], fields="source,length,picture")
                s["length"] = v.get("length")
                s["url"] = v.get("source")
            except SystemExit as e:
                print(f"  video {s['ref']}: {str(e)[:120]}", file=sys.stderr)
            ext = ".mp4"
        else:
            s["url"] = s.get("url") or (s["ref"] if str(s["ref"]).startswith("http") else s.get("thumb"))
            ext = ".jpg"
        f = out / "media" / (s["asset"].replace("/", "_")[:80] + ext)
        if s.get("url") and fetch(s["url"], f):
            s["file"] = str(f.relative_to(ROOT))
        elif s.get("thumb") and fetch(s["thumb"], f.with_suffix(".thumb.jpg")):
            s["file"] = str(f.with_suffix(".thumb.jpg").relative_to(ROOT))
            s["thumb_only"] = True

    n, got_stills = stills(m, brand, assets, None, out)
    if n:
        print(f"{brand}: {got_stills}/{n} assets read from a full-size still")

    (out / "ads.json").write_text(json.dumps(
        {"brand": brand, "pulled": day, "mode": mode, "ads": rows}, indent=1))
    (out / "assets.json").write_text(json.dumps(
        {"brand": brand, "pulled": day, "mode": mode,
         "assets": sorted(assets.values(), key=lambda s: -s["spend_30d"])}, indent=1))
    got = sum(1 for s in assets.values() if s.get("file") and not s.get("thumb_only"))
    print(f"{brand}: {len(assets)} unique assets, {got} with full media -> {out.relative_to(ROOT)}")


def pieces(brand, day=None):
    """Meta's grade of every piece of every flexible ad: spend and purchases by
    text, headline, video and image (Insights breakdowns body_asset · title_asset ·
    video_asset · image_asset). Four account-level calls, once a day, saved as
    pieces.json beside the day's pull. The Creative Index reads it."""
    sys.exit(NO_META)
    day = day or date.today().isoformat()
    out = ROOT / "runs" / "creative-diversity" / brand / day
    f = out / "pieces.json"
    if f.exists() and "--force" not in sys.argv:
        print(f"{brand}: pieces already read today")
        return
    out.mkdir(parents=True, exist_ok=True)
    m = Meta(brand)
    rows = []
    for kind in ("body", "title", "video", "image"):
        bd = f"{kind}_asset"
        try:
            got = paged(m, f"act_{_account(m)}/insights", level="ad", breakdowns=bd, date_preset="last_30d",
                        fields="ad_id,spend,impressions,actions,action_values", limit=500)
        except SystemExit as e:
            print(f"  {bd}: {str(e)[:160]}", file=sys.stderr)
            continue
        for r in got:
            a = r.get(bd) or {}
            ref = a.get("text") or a.get("video_id") or a.get("hash") or a.get("url") or a.get("id")
            buys = sum(float(x["value"]) for x in r.get("actions", []) if x["action_type"] == "purchase")
            val = sum(float(x["value"]) for x in r.get("action_values", []) if x["action_type"] == "purchase")
            rows.append({"ad_id": r["ad_id"], "piece_kind": kind, "piece_ref": str(ref)[:500],
                         "since": r.get("date_start"), "until": r.get("date_stop"), "spend": float(r.get("spend") or 0),
                         "impressions": int(r.get("impressions") or 0), "purchases": buys, "value": val})
        print(f"  {bd}: {len([x for x in rows if x['piece_kind'] == kind])} pieces")
    f.write_text(json.dumps({"brand": brand, "read": day, "rows": rows}, indent=1, ensure_ascii=False))
    print(f"{brand}: {len(rows)} pieces → {f.relative_to(ROOT)}")


if __name__ == "__main__":
    if "--pieces" in sys.argv:
        pieces(sys.argv[1])
        sys.exit(0)
    main(sys.argv[1], *[a for a in sys.argv[2:3] if not a.startswith("--")])
