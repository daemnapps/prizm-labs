#!/usr/bin/env python3
"""Put a brand's feedback form on its own Shopify store, at /pages/feedback.

    python3 components/feedback-forms/shopify.py build   --brand <b>          the theme template, written under runs/ (nothing sent)
    python3 components/feedback-forms/shopify.py check   --brand <b>          the store key: set or missing, and the access it has (reads only)
    python3 components/feedback-forms/shopify.py install --brand <b> [--go]   without --go: what it would do; with --go: do it

The form is one theme template, `templates/page.feedback.liquid`, standalone (`{% layout none %}`) with the engine,
the brand's look and its config inline, plus one store page, "Feedback" (handle `feedback`), that uses it. Nothing
else in the theme is touched. Every stage is the same page: `?stage=` picks the questions.

Keys, by name only (values in the key file, never here): SHOPIFY_<BRAND>_ADMIN_TOKEN, or the brand's app credentials
SHOPIFY_<BRAND>_CLIENT_ID + SHOPIFY_<BRAND>_APP (a token is minted and held in memory), with write_themes and
write_content; the store's myshopify domain from --store or SHOPIFY_<BRAND>_STORE.
Installing changes the live store, so it runs only with --go, on the owner's word. Brand-agnostic.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "keys"))
import build as B  # noqa: E402

API = "2025-10"
TEMPLATE_KEY = "templates/page.feedback.liquid"
HANDLE = "feedback"
NEEDED = {"write_themes", "write_content"}


def template(brand, root=None):
    """The standalone Liquid template: the live page, wrapped so Liquid leaves every brace alone."""
    stages, questions = B.load(brand, root)
    bad = B.check(stages, questions)
    if bad:
        raise SystemExit("The config is not sound: " + "; ".join(bad[:3]))
    page = B.preview_html(stages, questions, questions["default_stage"], mode="live", root=root)
    if "{% endraw %}" in page:
        raise SystemExit("The page carries an endraw tag; it cannot be wrapped safely.")
    return "{% layout none %}\n{% raw %}\n" + page + "{% endraw %}\n"


def out_dir(brand, root=None):
    d = (root or B.WORKSPACE) / "runs" / "feedback-forms" / brand / "shopify"
    (d / "templates").mkdir(parents=True, exist_ok=True)
    return d


def keys(brand, store=None, opener=None):
    """(token, domain, NAME). An Admin token if one is set; else a fresh one minted from the brand's app credentials
    (SHOPIFY_<B>_CLIENT_ID + SHOPIFY_<B>_APP, client-credentials grant), held in memory only."""
    import loader
    up = brand.upper().replace("-", "_")
    domain = store or loader.key(f"SHOPIFY_{up}_STORE", required=False)
    token = loader.key(f"SHOPIFY_{up}_ADMIN_TOKEN", required=False)
    cid, secret = loader.key(f"SHOPIFY_{up}_CLIENT_ID", required=False), loader.key(f"SHOPIFY_{up}_APP", required=False)
    if not token and cid and secret and domain:
        d = re.sub(r"^https?://", "", domain).strip("/")
        req = urllib.request.Request(f"https://{d}/admin/oauth/access_token", method="POST",
                                     data=json.dumps({"client_id": cid, "client_secret": secret, "grant_type": "client_credentials"}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with (opener or urllib.request.urlopen)(req, timeout=30) as r:
                token = json.loads(r.read()).get("access_token")
        except urllib.error.HTTPError as e:
            raise SystemExit(f"The store refused the app's credentials ({e.code}).") from None
    return token, domain, up


class Store:
    def __init__(self, domain, token, opener=None):
        domain = re.sub(r"^https?://", "", domain).strip("/")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", domain):
            raise SystemExit("The store key is the myshopify domain, like brand.myshopify.com.")
        self.base, self.token = f"https://{domain}/admin", token
        self.open = opener or urllib.request.urlopen

    def call(self, method, path, body=None):
        req = urllib.request.Request(self.base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"X-Shopify-Access-Token": self.token, "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with self.open(req, timeout=60) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Shopify answered {e.code} on {method} {path.split('?')[0]}.") from None

    def scopes(self):
        return {s["handle"] for s in self.call("GET", "/oauth/access_scopes.json").get("access_scopes", [])}

    def main_theme(self):
        themes = self.call("GET", f"/api/{API}/themes.json").get("themes", [])
        return next((t for t in themes if t.get("role") == "main"), None)

    def page(self):
        pages = self.call("GET", f"/api/{API}/pages.json?handle={HANDLE}").get("pages", [])
        return pages[0] if pages else None


def main(argv=None, out=sys.stdout, root=None, store=None):
    ap = argparse.ArgumentParser(description="Put a brand's feedback form on its Shopify store.")
    ap.add_argument("cmd", choices=["build", "check", "install"])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--go", action="store_true", help="install: change the live store (the owner's word)")
    ap.add_argument("--store", help="the store's myshopify domain (else SHOPIFY_<BRAND>_STORE)")
    a = ap.parse_args(argv)
    try:
        text = template(a.brand, root)
        d = out_dir(a.brand, root)
        (d / TEMPLATE_KEY).write_text(text)
        if a.cmd == "build":
            out.write(f"Template written: {d / TEMPLATE_KEY} ({len(text):,} characters). Nothing sent.\n")
            return 0
        if store is None:
            token, domain, up = keys(a.brand, a.store)
            if not token or not domain:
                out.write(f"Needs the store (--store or SHOPIFY_{up}_STORE) and either SHOPIFY_{up}_ADMIN_TOKEN or the app's "
                          f"SHOPIFY_{up}_CLIENT_ID + SHOPIFY_{up}_APP, with write_themes and write_content.\n")
                return 2
            store = Store(domain, token)
        have = store.scopes()
        missing = sorted(NEEDED - have)
        theme = store.main_theme()
        page = store.page()
        out.write(f"Store key works · access: {', '.join(sorted(have & NEEDED)) or 'none of the needed'}"
                  + (f" · missing: {', '.join(missing)}" if missing else "") + "\n")
        out.write(f"Live theme: {theme['name'] if theme else 'none found'} · Feedback page: {'exists' if page else 'not yet'}\n")
        if a.cmd == "check":
            return 1 if missing or not theme else 0
        if missing or not theme:
            out.write("Cannot install until the key has write_themes and write_content and a live theme is found.\n")
            return 2
        plan = [f"add {TEMPLATE_KEY} to the live theme '{theme['name']}' (a new file; nothing existing changes)",
                "update the Feedback page to use it" if page else "create the page 'Feedback' at /pages/feedback using it"]
        if not a.go:
            out.write("Would: " + "; ".join(plan) + ". Run with --go on the owner's word.\n")
            return 0
        store.call("PUT", f"/api/{API}/themes/{theme['id']}/assets.json", {"asset": {"key": TEMPLATE_KEY, "value": text}})
        body = {"page": {"title": "Feedback", "handle": HANDLE, "template_suffix": "feedback", "published": True}}
        if page:
            store.call("PUT", f"/api/{API}/pages/{page['id']}.json", {"page": {"id": page["id"], "template_suffix": "feedback"}})
        else:
            store.call("POST", f"/api/{API}/pages.json", body)
        out.write("Installed: " + "; ".join(plan) + ". The form is at /pages/feedback?stage=<stage>.\n")
        return 0
    except SystemExit as err:
        out.write(f"{err}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
