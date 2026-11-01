"""Reviews — new store reviews into the avatar's bank.

    python3 components/research-gatherer/gather.py reviews --brand B [--dry-run] [--since D] [--avatar A]

Built 2026-09-29 (free sources run on a trigger). The platform is the
brand's own config — `operations/language-pulls.json` › `reviews`:

    {"platform": "junip",   "key": "<KEY NAME>", "since": "2026-07-01"}
    {"platform": "judgeme", "key": "<KEY NAME>", "shop_domain": "<shop>", "since": "…"}

The key is read by NAME (environment, then the Keychain) and never printed.
Junip answers its public product-review API with the storefront store key
(the key printed in the storefront HTML); Judge.me's reviews API takes the
shop domain and the shop's API token.

One row per review: the body as written (the title when there is no body),
rating in `signal.rating`, the review id as `source.item`, source id
`review_<platform>_<brand>`. A verified buyer is a customer by relationship
(lane customer); an unverified reviewer's lane is read from the words.
Cursor: runs/research/<brand>/reviews-state.json (the newest review's
`created_at`), moved only when nothing is held.
"""
import argparse
import json
import urllib.parse
import urllib.request

from . import annotate as A
from . import voicepull as V

say = V.say
UA = {"Accept": "application/json", "User-Agent": "research-gatherer/reviews"}


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=dict(UA, **(headers or {})))
    return json.loads(urllib.request.urlopen(req, timeout=45).read())


def pull_junip(conf, secret, get=_get):
    out, after = [], None
    for _ in range(500):
        p = {"page[size]": 100}
        if after:
            p["page[after]"] = after
        d = get("https://api.juniphq.com/v1/product_reviews?" + urllib.parse.urlencode(p), {"Junip-Store-Key": secret})
        rows = d.get("product_reviews") or []
        out += rows
        after = ((d.get("meta") or {}).get("page") or {}).get("after")
        if not after or not rows:
            break
    return out


def pull_judgeme(conf, secret, get=_get):
    out = []
    for page in range(1, 500):
        q = urllib.parse.urlencode({"shop_domain": conf.get("shop_domain") or "", "api_token": secret,
                                    "per_page": 100, "page": page})
        d = get("https://judge.me/api/v1/reviews?" + q)
        rows = d.get("reviews") or []
        out += rows
        if len(rows) < 100:
            break
    return out


PULL = {"junip": pull_junip, "judgeme": pull_judgeme}


def normalise(platform, r):
    """One review -> {id, rating, body, created_at, verified, product} across platforms."""
    if platform == "junip":
        return dict(id=r.get("id"), rating=r.get("rating"), title=r.get("title"), body=r.get("body"),
                    created_at=r.get("created_at"), verified=bool(r.get("verified_buyer")),
                    product=str(r.get("target_title") or "").split(" - ")[0].strip())
    return dict(id=r.get("id"), rating=r.get("rating"), title=r.get("title"), body=r.get("body"),
                created_at=r.get("created_at"), verified=str(r.get("verified") or "") in ("buyer", "verified-purchase"),
                product=r.get("product_title") or "")


def rows_from_reviews(platform, items, brand, label, today, since=None):
    """Raw reviews -> (rows, newest created_at). Pure — the tests call it."""
    newest, out = None, []
    for raw in items or []:
        r = normalise(platform, raw)
        at = str(r.get("created_at") or "")
        if at and (newest is None or at > newest):
            newest = at
        if since and at and at[:19] <= str(since)[:19]:
            continue
        text = A.clean(r.get("body") or r.get("title") or "")
        if len(text) < 2 or r.get("id") is None:
            continue
        pname = {"junip": "Junip", "judgeme": "Judge.me"}.get(platform, platform)
        out.append(dict(kind="review", text=text, said=at[:10], pulled=today,
                        ref=f"{platform} review {r['id']}", item=str(r["id"]),
                        source_name=f"{label} store review ({pname})" + (f" — {r['product']}" if r.get("product") else ""),
                        source_type="review", source_id=f"review_{platform}_{brand}", source_kind="review",
                        property=brand, rating=r.get("rating"),
                        relationship="ordered" if r.get("verified") else "reviewer, no verified order"))
    return out, newest


def main(argv=None, get=None, labeller=None, claude=None):
    ap = argparse.ArgumentParser(prog="gather.py reviews")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar")
    ap.add_argument("--since", help="YYYY-MM-DD; default = the cursor, else `since` in language-pulls.json")
    ap.add_argument("--dry-run", action="store_true", help="pull and count; read and file nothing")
    a = ap.parse_args(argv)
    c = V.cfg("reviews")
    bj = V.brand_json(a.brand)
    label = bj.get("label") or a.brand
    conf = bj.get("reviews") or {}
    platform = conf.get("platform")
    now, today, run_label = V.now_labels()
    say(f"reviews · {a.brand} · {platform or 'no platform'}{' · DRY RUN' if a.dry_run else ''}")
    if platform not in PULL:
        say("  no review platform in language-pulls.json (reviews.platform: junip | judgeme) — nothing to pull")
        return 0
    avatar = V.avatar_for(a.brand, bj, a.avatar)
    if not avatar:
        say("  name the avatar (--avatar, or language_avatar in language-pulls.json)")
        return 2
    secret = V.key(conf.get("key"))
    if not secret:
        say(f"  MISSING — the {platform} key `{conf.get('key') or '(none named)'}` is not in the environment or the Keychain")
        return 0
    if platform == "judgeme" and not conf.get("shop_domain"):
        say("  MISSING — reviews.shop_domain is not set in language-pulls.json (the domain Judge.me knows the shop by)")
        return 0
    state = V.load_state(a.brand, "reviews")
    since = a.since or state.get("last_review") or conf.get("since") or c.get("first_run_since")
    try:
        items = PULL[platform](conf, secret, **({"get": get} if get else {}))
    except Exception as e:
        msg = str(e).replace(secret, "<key>")[:160]
        say(f"  MISSING — {platform} could not be read ({msg})")
        return 0
    rows, newest = rows_from_reviews(platform, items, a.brand, label, today, since)
    say(f"  {len(items)} reviews on {platform} · {len(rows)} since {since}")
    fresh, filed, dropped, held = V.file_rows(a.brand, avatar, label, rows, f"store reviews ({platform})", c,
                                              run_label, a.dry_run, labeller=labeller, claude=claude)
    if filed is None:
        say("  dry run — nothing read, nothing filed" if a.dry_run else "  nothing new")
        if not a.dry_run and newest:
            V.save_state(a.brand, "reviews", {"last_review": newest})
        return 0
    V.write_run(a.brand, "reviews", label, run_label, since, filed, dropped, held, [],
                extra={"avatar": avatar, "platform": platform, "on_platform": len(items), "new": len(rows)},
                intro=f"New reviews on the store ({platform}) since {since}. Every row below is now in the brand's "
                      "language bank, with its lane, awareness level and sophistication signal.")
    if not held and newest:
        V.save_state(a.brand, "reviews", {"last_review": newest})
    return 0
