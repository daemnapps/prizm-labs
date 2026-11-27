"""Copy the toolkit (the paths in toolkit-paths.txt) from Prizm Labs into a client copy.

Used twice: by new_client.py when a copy is first made, and every day by the
client copy's own toolkit-update job. Only files Prizm Labs actually tracks are
copied, so stray local files never travel. Inside a listed folder, a file that
is gone from Prizm Labs is removed from the client copy too. Nothing outside
the listed paths is ever touched — the client's brand folder stays theirs.

    python3 apply_toolkit.py <prizm-labs folder> <client copy folder>

Prints how many files changed. Stdlib only, Python 3.9-clean.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def toolkit_paths(src):
    manifest = Path(src) / "tools" / "client-copies" / "toolkit-paths.txt"
    lines = manifest.read_text().splitlines()
    return [l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")]


def tracked_files(src, paths):
    out = subprocess.run(["git", "-C", str(src), "ls-files", "-z", "--", *paths],
                         check=True, capture_output=True).stdout
    return [p for p in out.decode().split("\0") if p]


def apply(src, dest):
    src, dest = Path(src).resolve(), Path(dest).resolve()
    paths = toolkit_paths(src)
    wanted = set(tracked_files(src, paths))
    changed = 0
    for rel in sorted(wanted):
        a, b = src / rel, dest / rel
        if not a.is_file():
            continue
        if b.is_file() and b.read_bytes() == a.read_bytes():
            continue
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(a, b)
        changed += 1
    # inside listed folders, drop what Prizm Labs no longer has
    for p in paths:
        if not p.endswith("/"):
            continue
        root = dest / p
        if not root.is_dir():
            continue
        for f in root.rglob("*"):
            rel = f.relative_to(dest).as_posix()
            if f.is_file() and rel not in wanted and not _ignored(dest, rel):
                f.unlink()
                changed += 1
    return changed


def _ignored(dest, rel):
    """Files the client copy's .gitignore ignores (their .venv, caches) stay put."""
    if not (dest / ".git").exists():
        return False
    r = subprocess.run(["git", "-C", str(dest), "check-ignore", "-q", rel])
    return r.returncode == 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    n = apply(sys.argv[1], sys.argv[2])
    print(f"{n} file(s) changed")
