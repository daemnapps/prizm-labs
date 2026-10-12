#!/usr/bin/env python3
"""The cards — every finished ad waiting for, or past, the owner's approve (CARD.md).

    meta/<brand>/<state>/<lane>/<ad name>/card.json + the media

on the shared Drive. States 1-check -> 2-approved -> 3-live, or sent-back; a
card folder MOVES between them (one rename on the mount), never copied or
deleted. The root is the Drive's `Shared Assets/meta`, or `META_CARDS_ROOT`
(a scratch tree for tests and trials).

    python3 cards.py                     # every card, by state
    python3 cards.py --check             # run the machine checks on 1-check, write them on each card
    python3 cards.py --tree              # make the empty state/lane folders for every brand

This file never approves anything. The approval is written only by the
approval page (approve.py) on the owner's click.
"""
import json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import names as N
from drop import DRIVE, PICTURE, VIDEO
import shared_drive as SD

STATES = ("1-check", "2-approved", "3-live", "sent-back")
LANES = ("video", "image", "carousel", "creator")
SCHEMA = "meta-card/1"
RATIO, RATIO_TOL = 9 / 16, 0.01
MAX_FLEX, CAROUSEL = 10, (2, 10)
PAGE_AD_LIMIT = 1000           # ads per Page running or in review (read 1 Oct 2026: brand-b, Brand A Skincare)
TTL = 600                      # seconds a page/cap answer is reused


def root():
    """META_CARDS_ROOT, else Shared Assets/meta on the mount; refused by name with neither."""
    if os.environ.get("META_CARDS_ROOT"):
        return Path(os.environ["META_CARDS_ROOT"])
    if not SD.mounted(DRIVE):
        raise SystemExit(f"cards: {SD.NOTE}")
    return DRIVE / "meta"


def brands():
    from brand import available
    return available()


# ---- folders ----------------------------------------------------------------
def ensure_tree(r=None, names=None):
    """meta/<brand>/{states}/{lanes} for every brand (or `names`)."""
    r = Path(r or root())
    for b in names or brands():
        for s in STATES:
            for l in LANES:
                (r / b / s / l).mkdir(parents=True, exist_ok=True)


def where(folder):
    """A card folder -> {brand, state, lane, name}, read off its path."""
    p = Path(folder)
    return {"brand": p.parents[2].name, "state": p.parents[1].name, "lane": p.parent.name, "name": p.name}


def card_id(folder):
    w = where(folder)
    return f"{w['brand']}/{w['state']}/{w['lane']}/{w['name']}"


def folder_of(cid, r=None):
    """A card id (brand/state/lane/name) -> its folder, refusing anything else."""
    parts = str(cid).split("/")
    if len(parts) != 4 or parts[1] not in STATES or parts[2] not in LANES or any(
            not x or x.startswith(".") or "\\" in x for x in parts):
        raise ValueError(f"not a card id: {cid}")
    return Path(r or root()).joinpath(*parts)


def listing(state=None, brand=None, lane=None, r=None):
    """Every card folder (with a card.json) matching the filters, newest first."""
    r = Path(r or root())
    out = []
    for b in [brand] if brand else sorted(x.name for x in r.iterdir() if x.is_dir()) if r.is_dir() else []:
        for s in [state] if state else STATES:
            for l in [lane] if lane else LANES:
                d = r / b / s / l
                if d.is_dir():
                    out += [c for c in d.iterdir() if (c / "card.json").is_file()]
    return sorted(out, key=lambda c: (c / "card.json").stat().st_mtime, reverse=True)


def load(folder):
    return json.loads((Path(folder) / "card.json").read_text())


def save(folder, card):
    """card.json, written whole then swapped in (never half a file on the Drive)."""
    f = Path(folder) / "card.json"
    tmp = f.with_name(".card.json.tmp")
    tmp.write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, f)


def move(folder, state):
    """The card folder to another state, same brand and lane. One rename; refuses
    to land on a folder that is already there."""
    if state not in STATES:
        raise ValueError(f"no state {state}")
    folder = Path(folder)
    dest = folder.parents[2] / state / folder.parent.name / folder.name
    if dest.exists():
        raise SystemExit(f"{card_id(dest)} already exists — not moved")
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.rename(folder, dest)
    return dest


def media_files(folder, card):
    return [Path(folder) / f for f in card.get("media") or []]


# ---- sizes ------------------------------------------------------------------
def size_of(p):
    """(width, height) of a picture (PIL) or a video (ffprobe, rotation applied)."""
    p = Path(p)
    if p.suffix.lower() in PICTURE:
        from PIL import Image
        with Image.open(p) as im:
            return im.size
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation", "-of", "json", str(p)],
                         capture_output=True, text=True, timeout=60)
    s = json.loads(out.stdout or "{}").get("streams", [{}])[0]
    w, h = int(s.get("width") or 0), int(s.get("height") or 0)
    rot = next((abs(int(x.get("rotation", 0))) for x in s.get("side_data_list") or [] if "rotation" in x), 0)
    return (h, w) if rot in (90, 270) else (w, h)


# ---- the outside world, cached ------------------------------------------------
_cache = {}


def _cached(key, fn):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    v = fn()
    _cache[key] = (time.time(), v)
    return v


def page_status(url):
    """The page's HTTP status after redirects (a browser's user agent; the
    pages sit behind Cloudflare)."""
    def fetch():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception as e:
            return f"unreachable ({type(e).__name__})"
    return _cached(("page", url), fetch)


def page_ads(brand, meta=None):
    """Ads running or in review on the brand's Page (act_/ads_volume, read only)."""
    def fetch():
        from brand import Brand
        b = Brand(brand)
        m = meta
        if m is None:
            from meta import Meta
            m = Meta(b)
        rows = m.get(f"act_{b.account_id}/ads_volume", show_breakdown_by_actor="true").get("data", [])
        hit = next((r for r in rows if str(r.get("actor_id")) == b.page_id), None)
        limit = int(b.d.get("page_ad_limit") or PAGE_AD_LIMIT)
        return {"count": int((hit or {}).get("ads_running_or_in_review_count") or 0), "limit": limit,
                "page": b.d.get("page_name") or b.page_id}
    return _cached(("cap", brand), fetch)


# ---- the machine checks -------------------------------------------------------
LABELS = {
    "media": "Media present, right kind",
    "ratio": "9:16",
    "words": "Primary text + headline",
    "name": "Ad name",
    "pages": "Landing pages live, in the funnel list",
    "product": "Ad product = page product",
    "ad_set": "Ad set found",
    "campaign": "Campaign found",
    "page_cap": "Page ad-cap headroom",
    "thumbs": "Thumbnails (designed, 9:16)",
    "offer": "The one offer page",
    "sound": "9:16 video has sound",
    "new_footage": "New footage (not already live)",
    "diversity": "A new creative to Meta (3+ moves)",
}


# ---- the Meta strategy checks (the owner, 7 Oct 2026) ------------------------------
# components/meta-strategy/rules.json · components/creative-diversity/META.md
STRATEGY = Path(__file__).resolve().parents[1] / "meta-strategy" / "rules.json"


def strategy_offer(brand):
    """The brand's one offer: {product, page, match}. None when the brand has none set."""
    try:
        o = json.loads(STRATEGY.read_text()).get("offers", {}).get(brand)
        if o is None:             # the brand's own folder: brands/<brand>/meta/offer.json
            f = Path(__file__).resolve().parents[2] / "brands" / brand / "meta" / "offer.json"
            o = json.loads(f.read_text()) if f.is_file() else None
        return o
    except (OSError, ValueError):
        return None


def has_sound(p):
    """True / False from the file's own streams; None when it can't be read."""
    import subprocess
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(p)],
                           capture_output=True, text=True, timeout=60)
        streams = json.loads(r.stdout or "{}").get("streams", [])
        return any(s.get("codec_type") == "audio" for s in streams) if streams else None
    except Exception:  # noqa: BLE001
        return None


def live_footage(brand, r=None):
    """(name, size) of every media file on a card already in 3-live for this brand."""
    base = (r or root()) / brand / "3-live"
    if not base.is_dir():
        return set()
    return {f.stat().st_size for f in base.rglob("*")
            if f.is_file() and f.suffix.lower() in set(VIDEO) | set(PICTURE) and "_thumb" not in f.stem}
THUMB_MAX_BYTES = 10_000_000      # Meta's own cap on a video thumbnail (/{video}/thumbnails); kept for /adimages too
THUMB_MIN_W = 1080


def checks(folder, card, online=True, meta=None):
    """Every machine check -> {"<check>": {"ok", "why"}}. Reuses upload.py's plan
    (card_plan) for the joins: ad set, campaign, page vs product."""
    import upload as U
    from brand import Brand
    folder = Path(folder)
    out = {}
    put = lambda k, ok, why="": out.__setitem__(k, {"ok": bool(ok), "why": why})
    w = where(folder)
    fmt, lane = card.get("format") or "flexible", card.get("lane") or w["lane"]

    # media
    media = media_files(folder, card)
    gone = [p.name for p in media if not p.is_file()]
    kinds = {"video" if p.suffix.lower() in VIDEO else "image" if p.suffix.lower() in PICTURE else "other" for p in media}
    why = []
    if not media:
        why.append("no media on the card")
    if gone:
        why.append(f"missing: {', '.join(gone[:4])}")
    if "other" in kinds:
        why.append("a file that is neither a picture nor a video")
    if fmt == "carousel":
        if lane != "carousel":
            why.append(f"a carousel in the {lane} lane")
        if not CAROUSEL[0] <= len(media) <= CAROUSEL[1]:
            why.append(f"{len(media)} slides — a carousel takes {CAROUSEL[0]}–{CAROUSEL[1]}")
    elif fmt == "flexible":
        if lane == "carousel":
            why.append("the carousel lane needs format carousel")
        if len(media) > MAX_FLEX:
            why.append(f"{len(media)} files — a flexible ad takes {MAX_FLEX}")
        if kinds >= {"video", "image"}:
            why.append("pictures and videos mixed in one flexible ad")
        if lane == "video" and kinds - {"video"}:
            why.append("the video lane holds videos only")
        if lane == "image" and kinds - {"image"}:
            why.append("the image lane holds pictures only")
    else:
        why.append(f"unknown format {fmt!r} (flexible or carousel)")
    put("media", not why, "; ".join(why) or f"{len(media)} {'/'.join(sorted(kinds))} file(s)")

    # thumbnails: a designed picture per video, or Meta's own frame (no `thumbs` on the card)
    th = card.get("thumbs") or {}
    if not th:
        put("thumbs", True, "none designed — Meta's own frame per video")
    else:
        bad = []
        for v, t in th.items():
            tp = Path(folder) / t
            if v not in (card.get("media") or []):
                bad.append(f"{t}: its video {v} is not on the card"); continue
            if not tp.is_file():
                bad.append(f"{t} not found"); continue
            if tp.suffix.lower() not in PICTURE:
                bad.append(f"{t}: not a picture"); continue
            if tp.stat().st_size > THUMB_MAX_BYTES:
                bad.append(f"{t}: {tp.stat().st_size / 1e6:.1f} MB (max 10)")
            try:
                iw, ih = size_of(tp)
                if abs(iw / ih - 9 / 16) > 0.01 or iw < THUMB_MIN_W:
                    bad.append(f"{t}: {iw}x{ih} (9:16, at least {THUMB_MIN_W} wide)")
            except Exception as e:
                bad.append(f"{t}: unreadable ({e})")
        vids = [f for f in card.get("media") or [] if Path(f).suffix.lower() in VIDEO]
        left = [f for f in vids if f not in th]
        put("thumbs", not bad, "; ".join(bad) or f"{len(th)} designed" + (f", Meta's frame for {len(left)}" if left else ""))

    # 9:16
    off = []
    for p in media:
        if not p.is_file():
            continue
        try:
            x, y = size_of(p)
            if not y or abs(x / y - RATIO) > RATIO * RATIO_TOL:
                off.append(f"{p.name} is {x}×{y}")
        except Exception as e:
            off.append(f"{p.name}: size unreadable ({type(e).__name__})")
    put("ratio", media and not off, "; ".join(off) or ("no media" if not media else "every file 9:16"))

    # words
    words = card.get("words") or {}
    why = []
    if not words.get("primary"):
        why.append("no primary text")
    if not words.get("headlines"):
        why.append("no headline")
    for k in ("primary", "headlines", "descriptions"):
        if len(words.get(k) or []) > 5:
            why.append(f"{len(words[k])} {k} — Meta takes 5")
    put("words", not why, "; ".join(why) or f"{len(words.get('primary') or [])} primary, "
        f"{len(words.get('headlines') or [])} headline(s), {len(words.get('descriptions') or [])} description(s)")

    # name
    d = N.parse_short(card.get("ad_name") or "")
    why = []
    if not d or d.get("asset") or d.get("funnel"):
        why.append(f"{card.get('ad_name')!r} is not a short unit name (brand_product_brief_batch)")
    else:
        if d["brand"] != card.get("brand"):
            why.append(f"the name says {d['brand']}, the card says {card.get('brand')}")
        if card.get("product") and d["product"] != N.slug(card["product"]):
            why.append(f"the name says {d['product']}, the card says {card.get('product')}")
    if card.get("ad_name") != w["name"]:
        why.append(f"folder is {w['name']}, card says {card.get('ad_name')}")
    if card.get("brand") != w["brand"]:
        why.append(f"in the {w['brand']} folder but the card says {card.get('brand')}")
    put("name", not why, "; ".join(why) or "short unit name")

    # the joins, from the uploader's own plan
    try:
        Brand(card.get("brand") or w["brand"])
        p = U.card_plan(folder, card)
    except SystemExit as e:
        for k in ("pages", "product", "ad_set", "campaign"):
            put(k, False, str(e))
        p = None
    if p:
        rows = p["ads"] + [h for h in p["held"] if h.get("link_id") is not None]
        why = []
        if not card.get("pages"):
            why.append("no landing page on the card")
        for r in rows:
            if not r.get("funnel"):
                why.append(f"{r.get('url') or r.get('link_id')}: not on the brand's funnel list")
            elif not r.get("url"):
                why.append(f"{r['link_id']}: no URL")
            elif online:
                st = page_status(r["url"])
                if st != 200:
                    why.append(f"{r['url']} answers {st}")
        put("pages", not why, "; ".join(why) or ", ".join(f"{r['funnel']} ✓" for r in rows)
            + ("" if online else " (not fetched)"))
        clash = [x for r in rows for x in r.get("why", []) if "sells" in x]
        put("product", not clash, "; ".join(clash) or (card.get("product") or "") + " on every page")
        ad_sets = {r.get("ad_set") for r in rows} or {None}
        miss = [x for r in p["held"] for x in r.get("why", []) if x.startswith("no ad set")]
        put("ad_set", not miss and None not in ad_sets, "; ".join(dict.fromkeys(miss)) or ", ".join(sorted(filter(None, ad_sets))))
        miss = [x for r in p["held"] for x in r.get("why", []) if x.startswith("no campaign")]
        camps = [r.get("campaign") for r in rows]
        put("campaign", rows and not miss and all(camps), "; ".join(dict.fromkeys(miss)) or ", ".join(dict.fromkeys(filter(None, camps)))
            or "no page, so no campaign")

    # the Meta strategy: one offer, sound on 9:16, new footage, a new creative to Meta
    brand = card.get("brand") or w["brand"]
    offer = strategy_offer(brand)
    if offer:
        urls = [r.get("url") for r in (p["ads"] + p["held"] if p else []) if r.get("url")]
        off = [u for u in urls if not any(m in u for m in offer["match"])]
        put("offer", urls and not off, "; ".join(f"{u} is not the {offer['product']} offer page" for u in off)
            or (f"{offer['product']} ✓" if urls else "no landing page"))
    tall = []
    for f in media:
        if f.is_file() and f.suffix.lower() in VIDEO:
            try:
                x, y = size_of(f)
                if y and y / x > 1.6:
                    tall.append(f)
            except Exception:  # noqa: BLE001
                pass
    silent = [f.name for f in tall if has_sound(f) is False]
    put("sound", not silent, "; ".join(f"{n} has no sound track" for n in silent)
        or (f"{len(tall)} 9:16 video(s), all with sound" if tall else "no 9:16 video"))
    seen = live_footage(brand)
    again = [f.name for f in media if f.is_file() and f.stat().st_size in seen]
    put("new_footage", not again, "; ".join(f"{n} is already live on the Page" for n in again[:4])
        or "none of these files is live yet")
    dv = card.get("diversity") or {}
    if not dv:
        # not red: the page disables Approve on red, and Approve is what scores it.
        # approve.py scores first, re-runs the checks, and refuses a variation then.
        put("diversity", True, "scored when you approve: a variation of a running creative is refused then")
    else:
        v, n = dv.get("verdict"), dv.get("moves_apart")
        same = ", ".join(dv.get("same_on") or [])
        put("diversity", v in ("new", "risky", "unscored"),
            {"new": f"new creative: {n} moves from the nearest running ad",
             "risky": f"risky: only {n} moves from the nearest running ad (same {same})",
             "variation": f"a variation of a running creative: {n} move(s) apart, same {same}",
             "unscored": dv.get("why", "no library to compare against yet")}.get(v, str(v)))

    # Page cap
    if online:
        try:
            c = page_ads(card.get("brand") or w["brand"], meta)
            need = max(1, len(card.get("pages") or []))
            room = c["limit"] - c["count"]
            put("page_cap", room >= need, f"{c['page']}: {c['count']}/{c['limit']} ads, this card adds {need}")
        except (SystemExit, Exception) as e:
            put("page_cap", False, f"couldn't read the Page's ad count: {str(e)[:200]}")
    else:
        put("page_cap", True, "not checked (offline)")
    return out


def check_and_save(folder, online=True, meta=None):
    """Run the checks and write them on the card (only when they changed)."""
    card = load(folder)
    c = checks(folder, card, online=online, meta=meta)
    if c != card.get("checks"):
        card["checks"] = c
        card["checked_at"] = datetime.now().isoformat(timespec="seconds")
        save(folder, card)
    return card


def passed(card):
    c = card.get("checks") or {}
    return bool(c) and all(v.get("ok") for v in c.values())


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="run the machine checks on every 1-check card")
    ap.add_argument("--tree", action="store_true", help="make the empty state/lane folders")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    if a.tree:
        ensure_tree()
        print(f"tree ready under {root()}")
    for f in listing():
        w = where(f)
        if a.check and w["state"] == "1-check":
            card = check_and_save(f, online=not a.offline)
            bad = [k for k, v in card["checks"].items() if not v["ok"]]
            print(f"{card_id(f)}  {'ALL PASSED' if not bad else 'FAILING: ' + ', '.join(bad)}")
        else:
            print(card_id(f))
