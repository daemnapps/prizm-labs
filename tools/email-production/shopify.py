#!/usr/bin/env python3
"""Shopify Admin — with a token that mints itself when it has expired.

    python3 shopify.py --brand <brand> --check   # is the store reachable, and on what token

The stored Admin token is short-lived (`{"t": …, "exp": …}`) and was six days
dead when this was written, which is the sort of thing that gets reported as
"the store is unavailable". It is not: the app's client id and secret are in the
Keychain and a client-credentials call mints a fresh one in a second. So this
mints on demand, writes the new token back, and nothing upstream has to know.

WHICH STORE, AND WHICH KEYS, ARE THE BRAND'S (2026-09-20). One store's domain
and Keychain names used to be typed here. They are read from the brand's own
`brands/<brand>/email-sms/machine.json`:

    "shopify": {"shop": "<store>.myshopify.com",
                "client_id_key": "...", "app_key": "...", "token_key": "...",   # optional
                "keychain_service": "...", "keychain_account": "..."}           # optional

Only `shop` is needed. The key names default to SHOPIFY_<BRAND>_CLIENT_ID,
SHOPIFY_<BRAND>_APP and SHOPIFY_<BRAND>_TOKEN; the minted token is written back
to the Keychain entry `shopify-ctrl-<brand>-token`, account `<brand>`.

Auth comes through the repo's key loader (environment, then .env); no value is ever printed.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from paths import WORKSPACE                                # noqa: E402

VERSION = "2024-10"
SHOP = None            # set by use(brand) — there is no default store
CFG = {}


def use(brand):
    """Point this module at one brand's store. Call it before get()/page()."""
    global SHOP, CFG
    f = WORKSPACE / "brands" / brand / "email-sms" / "machine.json"
    try:
        d = json.loads(f.read_text()).get("shopify") or {}
    except (OSError, ValueError):
        d = {}
    if not d.get("shop"):
        sys.exit(f"no Shopify store on file for {brand} — add \"shopify\": {{\"shop\": "
                 f"\"<store>.myshopify.com\"}} to {f}")
    up = brand.upper().replace("-", "_")
    CFG = {"brand": brand,
           "client_id_key": d.get("client_id_key") or f"SHOPIFY_{up}_CLIENT_ID",
           "app_key": d.get("app_key") or f"SHOPIFY_{up}_APP",
           "token_key": d.get("token_key") or f"SHOPIFY_{up}_TOKEN",
           "keychain_service": d.get("keychain_service") or f"shopify-ctrl-{brand}-token",
           "keychain_account": d.get("keychain_account") or brand}
    SHOP = d["shop"]
    return SHOP


def _need():
    if not SHOP:
        sys.exit("shopify.py: no store chosen — call shopify.use(<brand>) or pass --brand; "
                 "there is no default brand")



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


def _mint():
    _need()
    cid = _shared_keys().lookup(CFG["client_id_key"], required=True)
    sec = _shared_keys().lookup(CFG["app_key"], required=True)
    r = subprocess.run(["curl", "-fsSL", "--max-time", "25", "-X", "POST",
                        f"https://{SHOP}/admin/oauth/access_token",
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps({"client_id": cid, "client_secret": sec,
                                          "grant_type": "client_credentials"})],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("could not mint a Shopify token — the app credentials were refused")
    d = json.loads(r.stdout)
    tok = d.get("access_token")
    exp = int(time.time()) + int(d.get("expires_in") or 86400) - 300
    subprocess.run(["security", "add-generic-password", "-a", CFG["keychain_account"],
                    "-s", CFG["keychain_service"], "-U",
                    "-w", json.dumps({"t": tok, "exp": exp})],
                   capture_output=True, text=True)
    return tok


def token():
    """A live token: the stored one while it lasts, a fresh one the moment it
    does not."""
    _need()
    raw = _shared_keys().lookup(CFG["token_key"])
    try:
        d = json.loads(raw)
        if d.get("t") and int(d.get("exp") or 0) > time.time() + 60:
            return d["t"]
    except (ValueError, TypeError):
        if raw:
            return raw
    return _mint()


def _split(raw):
    """curl -D - writes the header block, a blank line, then the body. HTTP/2
    and HTTP/1.1 disagree about the line endings, so accept either."""
    for sep in ("\r\n\r\n", "\n\n"):
        if sep in raw:
            head, _, body = raw.partition(sep)
            return head, body
    return "", raw


def get(path, params="", tok=None, retry=True):
    _need()
    tok = tok or token()
    url = f"https://{SHOP}/admin/api/{VERSION}{path}{params}"
    r = subprocess.run(["curl", "-sS", "--max-time", "60", "-D", "-",
                        "-H", f"X-Shopify-Access-Token: {tok}",
                        "-H", "Accept: application/json", url],
                       capture_output=True, text=True)
    head, body = _split(r.stdout)
    if " 401 " in head.split("\n")[0] and retry:
        return get(path, params, _mint(), retry=False)
    link = ""
    for line in head.split("\n"):
        if line.lower().startswith("link:"):
            link = line
    nxt = None
    for part in link.split(","):
        if 'rel="next"' in part and "<" in part:
            nxt = part.split("<", 1)[1].split(">", 1)[0]
    try:
        return json.loads(body), nxt
    except ValueError:
        return None, None


def page(url, tok=None):
    """Follow an absolute next-page URL Shopify handed back."""
    tok = tok or token()
    r = subprocess.run(["curl", "-sS", "--max-time", "60", "-D", "-",
                        "-H", f"X-Shopify-Access-Token: {tok}",
                        "-H", "Accept: application/json", url],
                       capture_output=True, text=True)
    head, body = _split(r.stdout)
    nxt = None
    for line in head.split("\n"):
        if line.lower().startswith("link:"):
            for part in line.split(","):
                if 'rel="next"' in part and "<" in part:
                    nxt = part.split("<", 1)[1].split(">", 1)[0]
    try:
        return json.loads(body), nxt
    except ValueError:
        return None, None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help="brand folder name under brands/ — there is no default brand")
    ap.add_argument("--check", action="store_true", help="is the store reachable (the default action)")
    use(ap.parse_args().brand)
    d, _ = get("/shop.json")
    if not d:
        sys.exit("store not reachable")
    s = d.get("shop", {})
    print(f"{s.get('name')} · {s.get('myshopify_domain')} · plan {s.get('plan_name')} · "
          f"currency {s.get('currency')}")
    c, _ = get("/customers/count.json")
    o, _ = get("/orders/count.json", "?status=any")
    print(f"customers: {c.get('count'):,}   orders: {o.get('count'):,}")
