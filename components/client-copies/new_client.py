"""Make a new client copy: Prizm Labs' tools and prompts plus one empty brand folder.

    python3 tools/client-copies/new_client.py "Joe's Pizza"
    python3 tools/client-copies/new_client.py "Joe's Pizza" --local   # no GitHub, for testing

What it does, in order:
  1. makes ~/prizm-clients/<client>/ (or $PRIZM_CLIENTS_DIR/<client>/);
  2. copies in the toolkit (toolkit-paths.txt) and a brand folder from brands/_TEMPLATE/;
  3. lets the copy save that brand folder (.gitignore), and adds the daily
     toolkit-update job so new tools and prompts arrive on their own;
  4. copies your .env from Prizm Labs, so your keys work there too (never saved to GitHub);
  5. saves it as a private repo in the clients' team space (home.json) and tags it
     prizm-client, which is how clients.py finds it.

Stops without changing anything if that client already has a copy.
Stdlib only (plus git and gh), Python 3.9-clean.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIZM = HERE.parent.parent
sys.path.insert(0, str(HERE))
from apply_toolkit import apply, tracked_files  # noqa: E402

TOPIC = "prizm-client"


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower().replace("'", "")).strip("-")
    if not s:
        sys.exit("That name has no letters or numbers in it.")
    return s


def home():
    f = HERE / "home.json"
    if not f.exists():
        sys.exit("No clients' team space is set yet (tools/client-copies/home.json).")
    return json.loads(f.read_text())["org"]


def clients_dir():
    return Path(os.environ.get("PRIZM_CLIENTS_DIR", "~/prizm-clients")).expanduser()


def run(*cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.DEVNULL)


def gitignore_for(name):
    text = (PRIZM / ".gitignore").read_text()
    line = f"!brands/{name}/"
    if line not in text:
        text = text.replace("brands/*/\n", f"brands/*/\n{line}\n", 1)
    return text


def make(client, local=False):
    name = slug(client)
    org = None if local else home()
    dest = clients_dir() / name
    if dest.exists():
        sys.exit(f"{client} already has a copy at {dest}")
    if org:
        r = subprocess.run(["gh", "repo", "view", f"{org}/{name}"], capture_output=True)
        if r.returncode == 0:
            sys.exit(f"{client} already has a copy online: {org}/{name}")

    dest.mkdir(parents=True)
    run("git", "init", "-q", "-b", "main", cwd=dest)
    (dest / ".gitignore").write_text(gitignore_for(name))
    apply(PRIZM, dest)

    for rel in tracked_files(PRIZM, ["brands/_TEMPLATE/"]):
        b = dest / "brands" / name / Path(rel).relative_to("brands/_TEMPLATE")
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PRIZM / rel, b)

    wf = dest / ".github" / "workflows" / "toolkit-update.yml"
    wf.parent.mkdir(parents=True)
    shutil.copy2(HERE / "toolkit-update.yml", wf)

    (dest / "prizm-client.json").write_text(json.dumps({
        "client": client,
        "brand_folder": f"brands/{name}/",
        "made": datetime.date.today().isoformat(),
    }, indent=1) + "\n")

    if (PRIZM / ".env").exists():
        shutil.copy2(PRIZM / ".env", dest / ".env")
        os.chmod(dest / ".env", 0o600)

    run("git", "add", "-A", cwd=dest)
    run("git", "commit", "-q", "-m", f"New client copy: {client}", cwd=dest)

    if org:
        run("gh", "repo", "create", f"{org}/{name}", "--private", "--source", str(dest), "--push",
            "--description", f"Prizm Labs client copy: {client}", cwd=dest)
        run("gh", "repo", "edit", f"{org}/{name}", "--add-topic", TOPIC)
        print(f"made {dest}  ->  https://github.com/{org}/{name}")
    else:
        print(f"made {dest}  (on this computer only)")
    return dest


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    make(args[0], local="--local" in sys.argv)
