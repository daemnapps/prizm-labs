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
"""
import json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C, library as L

REPO = HERE.parent / "records"
SELECTED = "creators/SELECTED-2026-08-27.json"


def rel_drive(p):
    """A Drive path written the way a person can follow it."""
    s = str(p)
    i = s.find("Shared Assets/")
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
        d = REPO / "runs" / rd.name
        d.mkdir(parents=True, exist_ok=True)
        for name in ("brief-final.md", "run.json"):
            if (rd / name).is_file():
                shutil.copy2(rd / name, d / name.replace("brief-final", "brief"))
        # the page she reads, when the run wrote one (stage 7b)
        if (rd / "stages" / "7b-page.md").is_file():
            shutil.copy2(rd / "stages" / "7b-page.md", d / "page.md")
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
            brief = f"[brief](runs/{slug}/brief.md)" if slug and \
                (REPO / "runs" / slug / "brief.md").is_file() else "—"
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
