#!/usr/bin/env python3
"""The onboarding page: set up a brand, your keys and your ad account in one local page.

    python3 components/onboarding/serve.py            # opens http://127.0.0.1:8890

Runs on this computer only (127.0.0.1). Keys typed here go straight into this repo's `.env` (created from
`.env.example`, never saved to git, readable only by you); the page never shows a key back, only "set" or
"missing". A brand is made from `brands/_TEMPLATE/`, or linked in from the folder where it already lives (its own
repo), so brand data stays where it is. Standard library only.
"""
import json
import os
import re
import shutil
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "components" / "keys"))
import loader  # noqa: E402

ENV, EXAMPLE = REPO / ".env", REPO / ".env.example"
BRANDS, TEMPLATE = REPO / "brands", REPO / "brands" / "_TEMPLATE"
NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


def catalog():
    """Every key in .env.example: name, section, what it is for, where to get it, optional or not."""
    out, section, note = [], "", []
    for line in EXAMPLE.read_text().splitlines():
        m = re.match(r"^# ---\s*(.+?)\s*-*$", line)
        if m:
            section, note = m.group(1).strip("- "), []
            continue
        if line.startswith("#"):
            note.append(line.lstrip("# ").strip())
            continue
        m = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if m:
            text = " ".join(note)
            url = re.search(r"https?://\S+", text)
            out.append({"name": m.group(1), "section": section, "what": text.split(" Get it:")[0],
                        "where": url.group(0).rstrip(".,)") if url else "",
                        "optional": "optional" in text.lower()})
            note = []
        elif not line.strip():
            note = []
    return out


def key_status():
    return {k["name"]: bool(loader.lookup(k["name"])) for k in catalog()}


def save_key(name, value):
    """Write one key into .env, keeping every other line. Returns nothing about the value."""
    if not NAME.match(name):
        raise ValueError("not a key name")
    value = value.strip()
    if "\n" in value or not value:
        raise ValueError("a key is one line")
    if not ENV.exists():
        shutil.copyfile(EXAMPLE, ENV)
    lines, done = ENV.read_text().splitlines(), False
    for i, line in enumerate(lines):
        if re.match(rf"^{name}=", line):
            lines[i], done = f"{name}={value}", True
    if not done:
        lines.append(f"{name}={value}")
    ENV.write_text("\n".join(lines) + "\n")
    os.chmod(ENV, 0o600)
    os.environ.pop(name, None)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def brands():
    out = []
    for p in sorted(BRANDS.iterdir()) if BRANDS.is_dir() else []:
        if p.name.startswith(("_", ".")) or not p.is_dir():
            continue
        prog = p / "onboarding-progress.json"
        done = json.loads(prog.read_text()).get("done", []) if prog.is_file() else []
        out.append({"brand": p.name, "linked": p.is_symlink(), "where": str(p.resolve()) if p.is_symlink() else "",
                    "done": len(done), "total": len(onboarding_items())})
    return out


def onboarding_items():
    d = json.loads((TEMPLATE / "onboarding.json").read_text())
    return d if isinstance(d, list) else d.get("items", [])


def add_brand(name, link=""):
    s = slug(name)
    if not s:
        raise ValueError("give the brand a name")
    dest = BRANDS / s
    if dest.exists() or dest.is_symlink():
        raise ValueError(f"brands/{s} already exists")
    if link:
        src = Path(os.path.expanduser(link)).resolve()
        if not src.is_dir():
            raise ValueError("that folder does not exist on this computer")
        dest.symlink_to(src)
    else:
        shutil.copytree(TEMPLATE, dest, ignore=shutil.ignore_patterns("onboarding.json", "ONBOARDING.md"))
        shutil.copyfile(TEMPLATE / "ONBOARDING.md", dest / "ONBOARDING.md")
    return s


def save_account(brand, account):
    account = account.strip()
    if not re.match(r"^(act_)?\d{5,}$", account):
        raise ValueError("an ad account id looks like act_1234567890")
    if not account.startswith("act_"):
        account = "act_" + account
    p = BRANDS / slug(brand) / "operations" / "brand.json"
    if not p.parent.is_dir():
        raise ValueError("no such brand")
    d = json.loads(p.read_text()) if p.is_file() else {}
    d["brand"] = slug(brand)
    accts = [a for a in d.get("ad_accounts", []) if a.get("network") != "meta" or "<" not in str(a.get("account"))]
    accts = [a for a in accts if a.get("account") != account] + [{"network": "meta", "account": account}]
    d["ad_accounts"] = accts
    p.write_text(json.dumps(d, indent=1) + "\n")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, kind="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            return self.send(200, (HERE / "page.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/state":
            st = key_status()
            return self.send(200, {"keys": [{**k, "set": st[k["name"]]} for k in catalog()], "brands": brands(),
                                   "steps": [{"id": i.get("id"), "what": i.get("what") or i.get("title") or i.get("id")}
                                             for i in onboarding_items()]})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.headers.get("Host", "").split(":")[0] not in ("127.0.0.1", "localhost"):
            return self.send(403, {"error": "local only"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            if self.path == "/api/key":
                save_key(body.get("name", ""), body.get("value", ""))
                return self.send(200, {"ok": True, "set": bool(loader.lookup(body["name"]))})
            if self.path == "/api/brand":
                return self.send(200, {"ok": True, "brand": add_brand(body.get("name", ""), body.get("link", ""))})
            if self.path == "/api/account":
                save_account(body.get("brand", ""), body.get("account", ""))
                return self.send(200, {"ok": True})
        except (ValueError, KeyError, OSError) as e:
            return self.send(400, {"error": str(e)})
        self.send(404, {"error": "not found"})


def main():
    port = int(os.environ.get("ONBOARDING_PORT", "8890"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Onboarding page: {url}")
    if "--no-open" not in sys.argv:
        webbrowser.open(url)
    srv.serve_forever()


if __name__ == "__main__":
    main()
