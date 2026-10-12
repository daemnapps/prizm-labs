#!/usr/bin/env python3
"""Mirror the referenceable half of this system into the repo.

    python3 records.py

The Drive holds what is heavy and what people watch: videos, stills, generated
frames, the Google Docs. Git holds what has to be diffable, searchable and
permanent: the brief that was written, which prompt versions wrote it, the
caption and audience comments a copywriter works from, and an index that ties
an id to all of it.

The split is deliberate. Media in git breaks the repo (workspace rule 3) and
text on the Drive alone cannot be diffed, searched from a session, or pointed
at by a commit. So each side keeps what it is good at and the INDEX is the
join.

Stage outputs are NOT copied here — fourteen per run across fifty runs is
twenty-odd megabytes of generated prose that nobody greps. They stay on the
Drive and on the board, and run.json records which prompt version made each.
The brief is not copied either: it lives on the writing shelf,
runs/video-writing/<brand>/<run>/deliverable/ (file_run.py puts it there); a
brief.md or page.md already on the teardown shelf is frozen history.
"""
import json, os, shutil, sys
from typing import Optional
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C, library as L

REPO = HERE.parent / "records"
# Each run's run.json is filed with the rest of the run at
# runs/video-teardown/<brand>/<run>/ — the workspace's one home for run records
# (runs/README.md). It sat under records/runs/ until 2026-09-30
# (the team notes/system-blueprint/RUNS-MOVE-2026-09-30.md).
RUNS_HOME = C.WS / "runs" / "video-teardown"


def run_home(slug, st=None):
    """runs/video-teardown/<brand>/<slug>/ — brand off the run itself."""
    if st is None:
        f = C.runs_root() / slug / "run.json"
        st = json.loads(f.read_text()) if f.is_file() else {}
    return RUNS_HOME / (st.get("brand") or "_unsorted") / slug


# The only files runs() copies onto the teardown shelf. The brief and the page
# stopped being copied 2026-10-08: the brief is read from the writing shelf.
SHELF_COPIES = ("run.json",)


def brief_file(home) -> Optional[Path]:
    """The brief for the run filed at `home` (runs/video-teardown/<brand>/<slug>):
    the writing shelf's final brief, then its brief, then the teardown shelf's
    frozen brief.md; None when there is none."""
    home = Path(home)
    out = RUNS_HOME.parent / "video-writing" / home.parent.name / home.name / "deliverable"
    for f in (out / "7-final-brief.md", out / "5-brief.md", home / "brief.md"):
        if f.is_file():
            return f
    return None
SELECTED = "creators/SELECTED-2026-08-27.json"


def rel_drive(p):
    """A Drive path written the way a person can follow it."""
    s = str(p)
    i = s.find(os.environ.get("SHARED_DRIVE_NAME", "Shared drives/Team Drive").split("/")[-1] + "/")
    return s[i:] if i >= 0 else s


def creators(root, sel):
    out = []
    for h, c in sel["creators"].items():
        d = REPO / "creators" / h
        (d / "copy").mkdir(parents=True, exist_ok=True)
        src = root / "creators" / h
        if (src / "creator.md").is_file():
            shutil.copy2(src / "creator.md", d / "creator.md")

        # one row per post: what it is, how it did, what she said
        rows = ["# " + h + " — every post we hold", "",
                "| id | name | views | caption |", "|---|---|---|---|"]
        pick = json.loads((root / "creators/PICKING.json").read_text())["creators"].get(h, {})
        names = {p["rank"]: p["name"] for p in pick.get("posts", [])}
        for pd in sorted((src / "posts").glob("*/post.json")):
            j = json.loads(pd.read_text())
            rank = pd.parent.name[:2]
            vid = f"{pick.get('prefix','?')}-{rank}"
            cap = " ".join((j.get("caption") or "").split())[:150]
            v = j.get("videoPlayCount") or j.get("videoViewCount") or 0
            rows.append(f"| `{vid}` | {names.get(rank,'')} | {v:,} | {cap} |")
        (d / "posts.md").write_text("\n".join(rows) + "\n")

        for f in (src / "selected").glob("*.copy.md"):
            shutil.copy2(f, d / "copy" / (f.name.split("  ")[0] + ".copy.md"))
        if (src / "selected" / "README.md").is_file():
            shutil.copy2(src / "selected" / "README.md", d / "selected.md")
        out.append(h)
    return out


def runs():
    got = []
    for rd in sorted(C.runs_root().iterdir()):
        f = rd / "run.json"
        if not f.is_file():
            continue
        st = json.loads(f.read_text())
        d = run_home(rd.name, st)
        d.mkdir(parents=True, exist_ok=True)
        for name in SHELF_COPIES:
            if (rd / name).is_file():
                shutil.copy2(rd / name, d / name)
        got.append((rd.name, st))
    return got


def index(root, sel, ran):
    by_label = {(s.get("label") or "").upper(): (slug, s) for slug, s in ran}
    lines = ["# Index — every selected video, and where everything about it lives", "",
             "One row per brief. `id` is permanent: the letters name the creator,",
             "the number is her post folder on the Drive. Follow it here to the",
             "post, the run, the brief and the editable Doc.", "",
             "| id | creator | post | brief | doc | video on the Drive |",
             "|---|---|---|---|---|---|"]
    for h, c in sel["creators"].items():
        for i in c["videos"]:
            slug, st = next(
                ((s, j) for lab, (s, j) in by_label.items()
                 if lab.startswith(i["id"].upper() + "-")), (None, {}))
            home = run_home(slug, st) if slug else None
            bf = brief_file(home) if home else None
            brief = f"[brief](../../../{bf.relative_to(C.WS).as_posix()})" if bf else "—"
            doc = f"[open]({st['gdoc_url']})" if st.get("gdoc_url") else "—"
            lines.append(
                f"| `{i['id']}` | {c['creator']} | [post]({i['post']}) | {brief} | "
                f"{doc} | `{i['video']}` |")
    lines += ["", "## Where the heavy things are", "",
              f"- videos, stills, generated frames, Docs — `{rel_drive(L.root())}`",
              f"- full run folders incl. every stage — `{rel_drive(C.runs_mirror())}`",
              "", "Media never enters this repo (workspace rule 3). This side is the",
              "text that has to be diffable and greppable; the Drive is the rest.", ""]
    (REPO / "INDEX.md").write_text("\n".join(lines))


def main():
    root = L.root()
    sel = json.loads((root / SELECTED).read_text())
    REPO.mkdir(parents=True, exist_ok=True)
    cs = creators(root, sel)
    ran = runs()
    index(root, sel, ran)
    print(f"records: {len(cs)} creators, {len(ran)} runs, index written")
    print(f"  -> {REPO}")


if __name__ == "__main__":
    main()
