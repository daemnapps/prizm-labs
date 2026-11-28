#!/usr/bin/env python3
"""run-lanes: keep this repo's run output private, and share only the brand lanes a team should see.

    lanes.py plan            what would change, nothing done
    lanes.py apply           make runs/ a private folder; link each shared brand's folders into the team's runs
    lanes.py relink          after new team folders appear: add the missing brand links (safe to run any time)
    lanes.py share PATH      send one private run (a folder under runs/) to the team: moved there, linked back here
    lanes.py undo            put runs/ back the way `apply` found it

The settings live outside this repo (they name brands and folders), in LANES_FILE (default ~/.prizm/lanes.json):

    {"team_runs": "<the team's runs folder>", "shared_brands": ["brand_a", "brand_b"]}

Rule: a run is private unless it is a shared brand's folder (runs/<tool>/<brand>/) or it was sent with `share`.
New work lands private by default. What the team already had on the day of `apply` stays reachable (its run folders
linked, its top-level files copied), so no tool loses its past. Nothing in the team's folder is moved or deleted.
Python 3.9, standard library only.
"""
import json, os, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNS = REPO / "runs"
CONF = Path(os.path.expanduser(os.environ.get("LANES_FILE") or "~/.prizm/lanes.json"))
STATE = Path(os.path.expanduser(os.environ.get("LANES_STATE") or "~/.prizm/lanes-state.json"))


def conf():
    if not CONF.is_file():
        sys.exit("No lanes file at %s. It needs team_runs and shared_brands." % CONF)
    c = json.loads(CONF.read_text())
    c["team_runs"] = Path(os.path.expanduser(c["team_runs"])).resolve()
    return c


def brand_links(c):
    """(link here, target in the team's runs) for every <tool>/<shared brand> folder the team has."""
    out = []
    team = c["team_runs"]
    for tool in sorted(p for p in team.iterdir() if p.is_dir() and not p.name.startswith(".")):
        for b in c["shared_brands"]:
            if (tool / b).is_dir():
                out.append((RUNS / tool.name / b, tool / b))
    return out


def plan():
    c = conf()
    links = brand_links(c)
    now = ("a link to " + os.readlink(RUNS)) if RUNS.is_symlink() else ("a folder" if RUNS.is_dir() else "missing")
    print("runs/ is now %s" % now)
    print("after apply: runs/ is a private folder; %d brand folders link to the team (%s)"
          % (len(links), ", ".join(c["shared_brands"])))
    print("everything else this repo makes stays private")
    return 0


def relink():
    c = conf()
    made = 0
    for here, there in brand_links(c):
        if here.is_symlink() or here.exists():
            continue
        here.parent.mkdir(parents=True, exist_ok=True)
        here.symlink_to(there, target_is_directory=True)
        made += 1
    print("%d brand links added" % made)
    return 0


def snapshot(c):
    """What the team already has stays reachable, so no tool loses its past: every existing run folder is linked,
    every top-level file is copied (a copy, so an index a tool rewrites from now on stays private)."""
    links = files = 0
    team = c["team_runs"]
    shared = set(c["shared_brands"])

    def place(src, dst, depth):
        nonlocal links, files
        if dst.exists() or dst.is_symlink():
            return
        if depth >= 3 or (src.is_dir() and src.name in shared):
            dst.symlink_to(src, target_is_directory=src.is_dir()); links += 1   # a past run's own parts: linked, never copied
        elif src.is_file():
            shutil.copy2(src, dst); files += 1                                   # an index or note one level up
        elif src.is_dir():
            dst.mkdir()                                                    # a grouping folder: real here, so what
            for ch in sorted(src.iterdir()):                               # lands in it from now on stays private
                if not ch.name.startswith("."):
                    place(ch, dst / ch.name, depth + 1)

    for top in sorted(team.iterdir()):
        if not top.name.startswith("."):
            place(top, RUNS / top.name, 1)
    print("kept reachable: %d run folders linked, %d files copied" % (links, files))


def apply():
    c = conf()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    if RUNS.is_symlink():
        STATE.write_text(json.dumps({"was_link_to": os.readlink(RUNS)}))
        RUNS.unlink()
    elif RUNS.exists():
        sys.exit("runs/ is already a real folder; use relink.")
    RUNS.mkdir()
    snapshot(c)
    return relink()


def share(path):
    c = conf()
    p = (RUNS / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
    if not p.is_dir() or p.is_symlink() or RUNS.resolve() not in p.parents:
        sys.exit("Not a private run folder under runs/: %s" % path)
    dest = c["team_runs"] / p.relative_to(RUNS.resolve())
    if dest.exists():
        sys.exit("The team already has %s" % dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(p), str(dest))
    p.symlink_to(dest, target_is_directory=True)
    print("shared: %s" % p.relative_to(RUNS.resolve()))
    return 0


def undo():
    if not STATE.is_file():
        sys.exit("Nothing to undo.")
    was = json.loads(STATE.read_text())["was_link_to"]
    team = conf()["team_runs"]
    private = []
    for p in RUNS.rglob("*"):
        if p.is_symlink() or not p.is_file():
            continue
        rel = p.relative_to(RUNS)
        t = team / rel
        if len(rel.parts) == 2 and t.is_file() and t.stat().st_size == p.stat().st_size:
            continue                                      # a copied team file, unchanged
        private.append(p)
    if private:
        sys.exit("runs/ holds %d private files; nothing changed. Share or move them first." % len(private))
    shutil.rmtree(RUNS)
    RUNS.symlink_to(was, target_is_directory=True)
    STATE.unlink()
    print("runs/ links to %s again" % was)
    return 0


if __name__ == "__main__":
    a = sys.argv[1:] or ["plan"]
    do = {"plan": plan, "apply": apply, "relink": relink, "undo": undo}
    if a[0] == "share" and len(a) == 2:
        sys.exit(share(a[1]))
    if a[0] not in do:
        sys.exit(__doc__)
    sys.exit(do[a[0]]())
