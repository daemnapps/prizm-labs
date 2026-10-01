#!/usr/bin/env python3
"""The Drive link for anything the lane made. Mirrors first, then links.

    drive_link.py <run>          the run's finished ads
    drive_link.py --all          every run

Pictures live on Drive, never in git — so the only way to see a finished ad is
a Drive link, and a link nobody was handed is a picture nobody saw. This
mirrors what changed and prints the folder link, so showing the work is one
command rather than a thing to remember.
"""
import re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P


def link_for(path: Path):
    """Drive for Desktop stamps every synced item with its own file id."""
    r = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", str(path)],
                       capture_output=True, text=True)
    fid = re.sub(r"[^A-Za-z0-9_-]", "", r.stdout.strip())
    return f"https://drive.google.com/drive/folders/{fid}" if len(fid) > 20 else None


def mirror(build="image-teardown"):
    subprocess.run([sys.executable, str(P.LAB / "mirror.py"), build],
                   capture_output=True, text=True, cwd=str(P.LAB))


def main():
    args = sys.argv[1:]
    mirror()
    drive_runs = P.DRIVE / "image-teardown/runs"
    if not drive_runs.is_dir():
        sys.exit("nothing mirrored yet — is Drive mounted?")

    wanted = ([d for d in sorted(drive_runs.iterdir()) if d.is_dir()]
              if "--all" in args else
              [drive_runs / Path(a).name for a in args if not a.startswith("--")])
    if not wanted:
        wanted = [d for d in sorted(drive_runs.iterdir()) if d.is_dir()]

    for d in wanted:
        finals = d / "finals"
        if not finals.is_dir():
            continue
        ads = sorted(p.name for p in finals.iterdir()
                     if p.suffix.lower() in (".png", ".jpg") and p.name.startswith("ad-"))
        if not ads:
            continue
        url = link_for(finals)
        print(f"\n{d.name} — {len(ads)} finished")
        for a in ads:
            print(f"   {a}")
        print(f"   {url or '(link not available — open the folder in Drive)'}")


if __name__ == "__main__":
    main()
