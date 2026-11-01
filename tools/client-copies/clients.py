"""See and manage every client copy.

    python3 tools/client-copies/clients.py                 # list: each client, how far their setup is, last change
    python3 tools/client-copies/clients.py get <client>    # bring that copy onto this computer, or up to date
    python3 tools/client-copies/clients.py update-all      # fetch the latest tools into every copy now (normally daily)
    python3 tools/client-copies/clients.py share <client> <github-name>    # let that person into that one copy

A client copy is any private repo in the clients' team space (home.json) tagged
prizm-client. Stdlib only (plus git and gh), Python 3.9-clean.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from new_client import TOPIC, clients_dir, home, slug  # noqa: E402

PRIZM = HERE.parent.parent


def gh_json(*args):
    out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    return json.loads(out or "[]")


def copies():
    return gh_json("repo", "list", home(), "--topic", TOPIC, "--limit", "500",
                   "--json", "name,url,pushedAt")


def progress(name):
    total = len(json.loads((PRIZM / "brands/_TEMPLATE/onboarding.json").read_text())["items"])
    f = clients_dir() / name / "brands" / name / "onboarding-progress.json"
    if not f.exists():
        return f"0 of {total}" if (clients_dir() / name).exists() else "not on this computer"
    p = json.loads(f.read_text())
    return f"{len(p.get('done', []))} of {total}"


def show():
    rows = copies()
    if not rows:
        print("No client copies yet.")
        return
    print(f"{'client':28} {'setup':22} last change")
    for r in sorted(rows, key=lambda r: r["name"]):
        print(f"{r['name']:28} {progress(r['name']):22} {r['pushedAt'][:10]}")


def get(client):
    name, org = slug(client), home()
    dest = clients_dir() / name
    if dest.exists():
        subprocess.run(["git", "-C", str(dest), "pull", "-q", "--ff-only"], check=True)
        print(f"up to date: {dest}")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["gh", "repo", "clone", f"{org}/{name}", str(dest), "--", "-q"], check=True)
        if (PRIZM / ".env").exists() and not (dest / ".env").exists():
            (dest / ".env").write_bytes((PRIZM / ".env").read_bytes())
            (dest / ".env").chmod(0o600)
        print(f"on this computer: {dest}")


def update_all():
    org = home()
    for r in copies():
        subprocess.run(["gh", "workflow", "run", "toolkit-update.yml", "-R", f"{org}/{r['name']}"],
                       check=True)
        print(f"updating {r['name']}")


def share(client, person):
    org, name = home(), slug(client)
    subprocess.run(["gh", "api", "-X", "PUT", f"repos/{org}/{name}/collaborators/{person}",
                    "-f", "permission=push", "--silent"], check=True)
    print(f"invited {person} to {name}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        show()
    elif a[0] == "get" and len(a) == 2:
        get(a[1])
    elif a[0] == "update-all":
        update_all()
    elif a[0] == "share" and len(a) == 3:
        share(a[1], a[2])
    else:
        sys.exit(__doc__)
