#!/usr/bin/env python3
"""Brand sync — pull a shared brand folder into brands/<brand>/ and push your changes back.

The brand folder lives on its owner's server (a brand-folder API, such as the one
in Portal Commerce). You get an access key for it; nobody adds you to a repo.

    python3 components/brand-sync/sync.py brands            # which brands your key reaches
    python3 components/brand-sync/sync.py status <brand>    # what changed, here and there
    python3 components/brand-sync/sync.py pull <brand>      # bring the server's changes in
    python3 components/brand-sync/sync.py push <brand>      # send your changes (read/write keys only)

Keys, from .env through components/keys/loader.py: BRAND_API_URL (the API address,
ending /api/v1/) and BRAND_API_KEY (your access key). BRAND_API_TENANT is only for
local testing against a server that picks the store by header.

Safe by design: nothing is ever deleted on either side; a file changed both here and
on the server is a conflict and is left alone; a push only lands if the server copy
is still the one you last pulled. brands/<brand>/ is gitignored, so pulled files are
never committed. Standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "components" / "keys"))
import loader  # noqa: E402

STATE = ".brand-sync.json"
BRAND = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
# Same rules as the server: a path part starts with a letter or digit; secrets and tool folders never travel.
PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ +()-]*\Z")
SKIP = {".git", ".DS_Store", "__pycache__", "node_modules", ".venv"}
MAX_FILE = 25 * 1024 * 1024
TIMEOUT = 60


class SyncError(Exception):
    pass


# --- talking to the server ------------------------------------------------------

class Client:
    def __init__(self, url=None, key=None, tenant=None):
        self.url = (url or loader.key("BRAND_API_URL")).rstrip("/") + "/"
        self.key = key or loader.key("BRAND_API_KEY")
        self.tenant = tenant if tenant is not None else loader.key("BRAND_API_TENANT", required=False)

    def _request(self, method, path, body=None, headers=None):
        req = urllib.request.Request(urllib.parse.urljoin(self.url, path), data=body, method=method)
        req.add_header("Authorization", "Bearer " + self.key)
        if self.tenant:
            req.add_header("X-Tenant", self.tenant)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as err:
            with err:
                return err.code, err.read()
        except urllib.error.URLError as err:
            raise SyncError(f"Can't reach the brand-folder server ({err.reason}).") from None

    def _json(self, path):
        status, body = self._request("GET", path)
        if status == 401:
            raise SyncError("The server didn't accept BRAND_API_KEY (wrong, revoked or expired).")
        if status == 404:
            raise SyncError("That brand isn't shared with this key.")
        if status != 200:
            raise SyncError(f"The server answered {status}.")
        return json.loads(body)

    def brands(self):
        return self._json("brand-folders/")

    def manifest(self, brand):
        return self._json(f"brand-folders/{brand}/")

    def fetch(self, brand, rel):
        status, body = self._request("GET", f"brand-folders/{brand}/files/{quote(rel)}")
        if status != 200:
            raise SyncError(f"Couldn't fetch {rel} ({status}).")
        return body

    def upload(self, brand, rel, data, base):
        return self._request("PUT", f"brand-folders/{brand}/files/{quote(rel)}", body=data,
                             headers={"X-Base-SHA256": base or "none", "Content-Type": "application/octet-stream"})


def quote(rel):
    return "/".join(urllib.parse.quote(p, safe="") for p in rel.split("/"))


# --- the local side -------------------------------------------------------------

def sha(data):
    return hashlib.sha256(data).hexdigest()


def travels(rel):
    parts = rel.split("/")
    return all(p not in SKIP and not p.startswith(".env") and PART.fullmatch(p) for p in parts)


def local_files(folder):
    out = {}
    if not folder.is_dir():
        return out
    for dirpath, dirnames, filenames in os.walk(folder):
        here = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in SKIP and not (here / d).is_symlink()]
        for name in filenames:
            path = here / name
            rel = path.relative_to(folder).as_posix()
            if path.is_symlink() or not path.is_file() or not travels(rel) or path.stat().st_size > MAX_FILE:
                continue
            out[rel] = sha(path.read_bytes())
    return out


def read_state(folder):
    try:
        data = json.loads((folder / STATE).read_text())
        return data.get("files", {}) if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(folder, files):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / STATE).write_text(json.dumps({"files": dict(sorted(files.items()))}, indent=1) + "\n")


def write_file(folder, rel, data):
    target = folder.joinpath(*rel.split("/"))
    probe = folder
    for part in rel.split("/")[:-1]:
        probe = probe / part
        if probe.is_symlink():
            raise SyncError(f"{rel}: a folder on the way is a link; left alone.")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".sync-", suffix=".partial")
    with os.fdopen(fd, "wb") as out:
        out.write(data)
    os.replace(tmp, target)


# --- comparing ------------------------------------------------------------------

def compare(base, local, remote):
    """Sort every path into one bucket, three-way against the last sync."""
    plan = {k: [] for k in ("same", "pull", "push", "conflict", "gone_there", "gone_here")}
    for rel in sorted(set(base) | set(local) | set(remote)):
        b, l, r = base.get(rel), local.get(rel), remote.get(rel)
        if l == r:
            plan["same"].append(rel)
        elif l == b:            # only the server moved
            plan["pull" if r else "gone_there"].append(rel)
        elif r == b:            # only this computer moved
            plan["push" if l else "gone_here"].append(rel)
        else:                   # both moved, differently
            plan["conflict"].append(rel)
    return plan


def check_brand(brand):
    if not BRAND.fullmatch(brand or ""):
        raise SyncError("A brand name is lower-case letters, digits and dashes.")
    return brand


def plan_for(client, brand, brands_dir):
    folder = Path(brands_dir) / check_brand(brand)
    manifest = client.manifest(brand)
    remote = {f["path"]: f["sha256"] for f in manifest["files"]}
    base, local = read_state(folder), local_files(folder)
    return folder, manifest, base, local, remote, compare(base, local, remote)


LABELS = [
    ("pull", "new or changed on the server"),
    ("push", "new or changed here"),
    ("conflict", "changed in both places — left alone"),
    ("gone_there", "removed on the server — kept here"),
    ("gone_here", "removed here — still on the server"),
]


def show(plan, out):
    lines = 0
    for key, label in LABELS:
        if plan[key]:
            out.write(f"{len(plan[key])} {label}:\n")
            for rel in plan[key]:
                out.write(f"  {rel}\n")
            lines += 1
    if not lines:
        out.write(f"In step: {len(plan['same'])} files match.\n")


# --- commands -------------------------------------------------------------------

def cmd_brands(client, args, out):
    data = client.brands()
    out.write(f"Your key: {'read and write' if data['access'] == 'read_write' else 'read only'}.\n")
    for b in data["brands"]:
        out.write(f"  {b['key']}  ({b['name']})\n")
    return 0


def cmd_status(client, args, out):
    *_, plan = plan_for(client, args.brand, args.brands_dir)
    show(plan, out)
    return 0


def cmd_pull(client, args, out):
    folder, manifest, base, local, remote, plan = plan_for(client, args.brand, args.brands_dir)
    synced = {rel: local[rel] for rel in plan["same"]}
    for rel in plan["pull"]:
        data = client.fetch(args.brand, rel)
        if sha(data) != remote[rel]:
            raise SyncError(f"{rel} changed on the server while pulling; pull again.")
        write_file(folder, rel, data)
        synced[rel] = remote[rel]
    # Keep the old base for anything not settled, so it shows again next time.
    for key in ("push", "conflict", "gone_here", "gone_there"):
        for rel in plan[key]:
            if rel in base:
                synced[rel] = base[rel]
    write_state(folder, synced)
    out.write(f"Pulled {len(plan['pull'])} file(s) into brands/{args.brand}/.\n")
    rest = {k: v for k, v in plan.items() if k not in ("same", "pull")}
    if any(rest.values()):
        show({**{k: [] for k in plan}, **rest}, out)
    return 1 if plan["conflict"] else 0


def cmd_push(client, args, out):
    folder, manifest, base, local, remote, plan = plan_for(client, args.brand, args.brands_dir)
    if manifest.get("access") != "read_write":
        raise SyncError("Your key is read only; ask whoever shares the brand for a read-and-write key.")
    state = dict(base)
    for rel in plan["same"]:
        state[rel] = local[rel]
    pushed, refused = [], []
    for rel in plan["push"]:
        data = folder.joinpath(*rel.split("/")).read_bytes()
        status, body = client.upload(args.brand, rel, data, remote.get(rel))
        if status in (200, 201):
            pushed.append(rel)
            state[rel] = sha(data)
        else:
            refused.append((rel, status))
    write_state(folder, state)
    out.write(f"Pushed {len(pushed)} file(s).\n")
    for rel, status in refused:
        why = "changed on the server since your pull — pull first" if status == 409 else f"refused ({status})"
        out.write(f"  not sent: {rel} — {why}\n")
    rest = {k: plan[k] for k in ("conflict", "gone_there", "gone_here", "pull")}
    if any(rest.values()):
        show({**{k: [] for k in plan}, **rest}, out)
    return 1 if refused or plan["conflict"] else 0


def main(argv=None, out=sys.stdout, client=None):
    parser = argparse.ArgumentParser(description="Pull a shared brand folder in and push your changes back.")
    parser.add_argument("command", choices=["brands", "status", "pull", "push"])
    parser.add_argument("brand", nargs="?")
    parser.add_argument("--brands-dir", default=str(REPO / "brands"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.command != "brands" and not args.brand:
        parser.error("name the brand")
    try:
        client = client or Client()
        return {"brands": cmd_brands, "status": cmd_status, "pull": cmd_pull, "push": cmd_push}[args.command](client, args, out)
    except KeyError as err:
        out.write(str(err).strip("'\"") + "\n")
        return 2
    except SyncError as err:
        out.write(f"{err}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
