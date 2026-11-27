#!/usr/bin/env python3
"""static_sprint — a round of winning-static plans, packed as the graphic designer's hand-offs.

    static_sprint.py prep <sprint.json>            manifests + briefs, checked, nothing leaves the sprint's folder
    static_sprint.py hand <sprint.json> --by <who> --only <id ...>   the hand-offs, here and on the Drive (after the owner's sign-off)

sprint.json: {brand, id, sign_off: {"<item id>": {by, at}}, items: [{id, title, product, plan (a static_plan folder) |
variations (image-writing's variations.json), rows (ids kept, default all), winner (one line), window, due, stays [..],
route (how it is made), slides (a carousel: 7), refs [{path, role}]}]}

Each item is one image-edit design assignment (handoff.py --assignment) with one required slot per row
(delivery_contract). `hand` refuses an item with no sign-off: the copy sign-off gate, no picture from unapproved words.
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def rows_of(item, repo=REPO):
    """[(id, words, picture, why)] from a static plan or an image-writing variations file; the control first."""
    if item.get("plan"):
        d = json.loads((repo / item["plan"] / "variation-plan.json").read_text())
        c = d.get("control") or {}
        rows = ([{"id": "control", "words": c.get("words") or [], "picture": c.get("picture") or "", "label": "The winner, dressed for this round"}]
                if c.get("words") else [])
        rows += [dict(r, label=r.get("label") or r.get("lever")) for r in d["rows"]]
    else:
        d = json.loads((repo / item["variations"]).read_text())
        rows = [dict(r, words=(r.get("words") or [""])[0].split(" / ")) for r in d["variations"]]
    keep = item.get("rows")
    return [r for r in rows if not keep or r["id"] in keep]


def words_shown(r, control):
    """Every zone of a short ad; a long one (a carousel) only the zones that differ from the control."""
    w = r["words"]
    if len(w) <= 6 or not control:
        return " / ".join(x.replace("\n", " ⏎ ") for x in w)
    diff = [f"“{a}” becomes “{b}”" for a, b in zip(control, w) if a != b]
    return "; ".join(diff) or "every word as the winner ran it"


def brief(item, rows):
    control = next((r["words"] for r in rows if r["id"] == "control"), None)
    out = [f"Winner: {item['winner']}", "", f"Runs: {item['window']} · due {item['due']}", "", "## What stays", ""]
    out += ["- " + s for s in item["stays"]]
    out += ["", "## The set", "", f"{len(rows)} versions" + (f", {item['slides']} slides each" if item.get("slides") else "") +
            ". Each is ONE change. The words are exact, letter for letter; ⏎ is a line break.", "",
            "| Version | Words on the ad | Picture |", "|---|---|---|"]
    for r in rows:
        pic = r.get("picture") or ("as the control" if control and r["id"] != "control" else "as the winner ran")
        out.append(f"| {r['id']} · {r.get('label') or ''} | {words_shown(r, control if r['id'] != 'control' else None)} | {pic} |")
    out += ["", "## How it is made", "", item["route"], "", "## Check each one", "",
            "- At 2 cm wide it looks like a different ad from the control.",
            "- Product matches its casting sheet; it is never loose where its rules forbid it.",
            "- Every word exact; nothing outside the centre 4:5 that matters; 1080 × 1920.",
            "", "## Return", "", "One finished export per version, named with this folder's name and the version, in `returned/`."]
    return "\n".join(out)


def manifest(sprint, item, repo=REPO):
    rows = rows_of(item, repo)
    if not rows:
        sys.exit(f"{item['id']}: no rows")
    return {"id": item["id"], "brand": sprint["brand"], "product": item.get("product"), "stage": item.get("stage", "brief"),
            "source_id": item.get("source_id", item["id"]), "title": item["title"], "brief": brief(item, rows),
            "next_action": item.get("next_action") or "Make every version in BRIEF.md through the route it names, check each one, and return the full set.",
            "references": item["refs"]}, rows


def prep(path, repo=REPO):
    sprint = json.loads(Path(path).read_text())
    d = Path(path).parent / "manifests"
    d.mkdir(exist_ok=True)
    n = 0
    for it in sprint["items"]:
        m, rows = manifest(sprint, it, repo)
        miss = [r["path"] for r in m["references"] if not (repo / r["path"]).is_file()]
        if miss:
            sys.exit(f"{it['id']}: missing {', '.join(miss)}")
        (d / f"{it['id']}.json").write_text(json.dumps(m, indent=1))
        (d / f"{it['id']}.md").write_text(f"# {it['title']}\n\n{m['brief']}\n")
        n += len(rows)
        print(f"{it['id']}: {len(rows)} versions")
    print(f"{len(sprint['items'])} hand-offs · {n} versions · nothing sent")


def hand(path, by, only):
    sprint = json.loads(Path(path).read_text())
    for p in (REPO / "components" / "image-edit", REPO / "components" / "briefs"):
        sys.path.append(str(p))
    from image_edit import assignment
    import delivery_contract as DC
    for it in sprint["items"]:
        if it["id"] not in only:
            continue
        so = sprint.setdefault("sign_off", {})
        so.setdefault(it["id"], {"by": by, "at": datetime.now().isoformat(timespec="seconds")})
        m, rows = manifest(sprint, it)
        f = Path(path).parent / "manifests" / f"{it['id']}.json"
        f.write_text(json.dumps(m, indent=1))
        folder, sheet = assignment.build(f)
        DC.pack(folder, role="graphic-designer", slots=[
            {"id": "slot-%02d" % (i + 1), "label": f"{r['id']} · {r.get('label') or ''}".strip(" ·") +
             (f" (all {it['slides']} slides)" if it.get("slides") else ""), "kind": "image", "cover_required": False}
            for i, r in enumerate(rows)])
        print(it["id"], "·", assignment.publish(folder, sheet)["link"])
    Path(path).write_text(json.dumps(sprint, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("do", choices=("prep", "hand")); ap.add_argument("sprint")
    ap.add_argument("--by"); ap.add_argument("--only", nargs="+", default=[])
    a = ap.parse_args()
    if a.do == "prep":
        return prep(a.sprint)
    if not a.by or not a.only:
        sys.exit("REFUSED: hand needs --by (who signed off) and --only (the items they signed off)")
    hand(a.sprint, a.by, a.only)


if __name__ == "__main__":
    main()
