#!/usr/bin/env python3
"""The pull door: what is waiting for my role, and open one so I can switch the stage on from there.

    python3 components/video-edit/handoff/pull.py roles                       who holds which role
    python3 components/video-edit/handoff/pull.py waiting --person <name>     every hand-off for every role they hold
    python3 components/video-edit/handoff/pull.py waiting --role <role> [--brand b]
    python3 components/video-edit/handoff/pull.py open <brief number> --role <role> [--brand b]

`open` prints the hand-off's START.md and the one line to say to your Claude to activate the stage. The video-editor
role opens through its own door (components/video-edit/open_brief.py, the video-briefs skill). Reads only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage_handoff as SH  # noqa: E402


def state(f, st, root):
    """open · back (finished work in returned/) · moved on (the next stage's hand-off is filed)."""
    m = SH.manifest(f) or {}
    if m.get("state") == "superseded" and m.get("superseded_by"):
        return "superseded"
    delivery = f / "delivery-state.json"
    if delivery.is_file():
        return json.loads(delivery.read_text()).get("state", "in-progress")
    if m.get("state") in ("held", "blocked"):
        return "held"
    if m.get("stage"):
        st = SH.stage(m["stage"])
    if st and st.get("next") and st.get("numbered"):
        ns = SH.stage(st["next"])
        if SH.find(SH.number(f.name), ns["role"], f.parent.name, root):
            return "moved on"
    return "back" if SH.returned(f) else "open"


def title(f):
    m = SH.manifest(f) or {}
    if m.get("title"):
        return m["title"]
    for name in ("BRIEF.md",):
        p = f / name
        if p.is_file():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("# "):
                    return line[2:].strip()
    return ""


def waiting(role, brand=None, root=None, drive=True):
    """Every hand-off for a role: the Drive is the home (hand-off folders travel by Drive, not git), so a folder on
    the Drive and not on this machine has its HANDOFF.json and START.md brought down first."""
    root = Path(root or SH.repo())
    st = SH.stage_of_role(role)
    note = ""
    if drive and not (st and (st.get("receives") or {}).get("checker")):
        try:
            for b, k, fid in SH.drive_handoffs(role, brand):
                f = SH.folder(role, b, k, root)
                SH.fetch(fid, f, only=SH.METADATA_FILES, refresh_metadata=True)
        except (Exception, SystemExit) as e:  # noqa: BLE001 — say it, list what is here
            note = "Drive not reachable (%s); listing this machine's copies only." % str(e)[:120]
    rows = []
    for f in SH.handoffs(role, brand, root):
        if state(f, st, root) == "superseded":
            continue
        rows.append({"role": role, "brand": f.parent.name, "number": SH.number(f.name), "key": f.name,
                     "title": title(f), "state": state(f, st, root), "revision_id": (json.loads((f / "delivery-state.json").read_text()) if (f / "delivery-state.json").is_file() else {}).get("revision_id"), "folder": str(f.relative_to(root)),
                     "note": note})
    for r in rows:
        r["stage"] = ((SH.manifest(root / r["folder"]) or {}).get("stage") or (st or {}).get("id"))
    return sorted(rows, key=lambda r: r["number"], reverse=True)


def opening(num, role, brand=None, root=None):
    root = Path(root or SH.repo())
    st = SH.stage_of_role(role)
    if st and (st.get("receives") or {}).get("checker"):
        return {"door": "video-briefs", "say": st["activates"]["say"].format(number=num),
                "note": "The editor's hand-offs open through the video-briefs door (Premiere or HyperFrames)."}
    try:
        for b, k, fid in SH.drive_handoffs(role, brand):
            if k == str(num) or SH.number(k).lstrip("0") == str(num).lstrip("#0"):
                SH.fetch(fid, SH.folder(role, b, k, root), only=SH.METADATA_FILES, refresh_metadata=True)
    except (Exception, SystemExit):
        pass  # local metadata remains readable while offline
    f = SH.find(num, role, brand, root)
    redirect = SH.manifest(f) if f else None
    if redirect and redirect.get("state") == "superseded" and redirect.get("superseded_by"):
        target = redirect["superseded_by"]
        return {"folder": str(f.relative_to(root)), "key": f.name, "title": title(f),
                "state": "superseded", "redirect": target,
                "say": "Open the canonical grouped brief " + str(target.get("key") or "") + ".",
                "start": (f / "START.md").read_text() if (f / "START.md").is_file() else ""}
    if f is None or not (f / "BRIEF.md").is_file():               # bring the whole hand-off down from the Drive
        try:
            for b, k, fid in SH.drive_handoffs(role, brand):
                if SH.number(k).lstrip("0") == str(num).lstrip("#0"):
                    SH.fetch(fid, SH.folder(role, b, k, root))
        except (Exception, SystemExit):  # noqa: BLE001 — a local copy still opens
            pass
        f = SH.find(num, role, brand, root)
    if not f:
        raise SystemExit("No %s hand-off for brief %s%s." % (role, num, (" (" + brand + ")") if brand else ""))
    m = SH.manifest(f) or {}
    if m.get("state") == "superseded" and m.get("superseded_by"):
        target = m["superseded_by"]
        return {"folder": str(f.relative_to(root)), "key": f.name, "title": title(f),
                "state": "superseded", "redirect": target,
                "say": "Open the canonical grouped brief " + str(target.get("key") or "") + ".",
                "start": (f / "START.md").read_text() if (f / "START.md").is_file() else ""}
    act = m.get("activate") or {}
    placed = place(f, m, root)
    return {"folder": str(f.relative_to(root)), "key": f.name, "title": title(f), "state": state(f, st, root),
            "skill": act.get("skill"), "run": act.get("run"), "say": act.get("say"),
            "placed": placed, "start": (f / "START.md").read_text(encoding="utf-8", errors="ignore") if (f / "START.md").is_file() else ""}


def place(f, m, root):
    """Put what the next component's door reads where it reads it. video-writing reads a teardown working run by its
    label from runs/video-teardown/_work/<label>/: copied there when it is not there, never over one that is."""
    import shutil
    if m.get("stage") == "video-writing" and (f / "teardown-run" / "run.json").is_file():
        dst = Path(root) / "runs" / "video-teardown" / "_work" / m["key"]
        placed = None
        if not (dst / "run.json").is_file():
            shutil.copytree(str(f / "teardown-run"), str(dst), dirs_exist_ok=True)
            placed = str(dst.relative_to(root))
        if m.get("working_media"):
            from resume_writing import restore_media
            for archive in [m["working_media"]] + (m.get("working_media_parts") or []):
                restore_media(f, dst, archive)
        for dep in m.get("working_dependencies") or []:
            source, target = Path(dep["packet"]), Path(dep["path"])
            if source.is_absolute() or target.is_absolute() or ".." in source.parts or ".." in target.parts \
                    or not target.as_posix().startswith("runs/video-teardown/_work/"):
                raise SystemExit("REFUSED: unsafe writing dependency path")
            for original in (f / source).rglob("*"):
                dest = Path(root) / target / original.relative_to(f / source)
                if original.is_file() and not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(original, dest)
        return placed
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("roles", "waiting", "open"))
    ap.add_argument("brief", nargs="?")
    ap.add_argument("--role")
    ap.add_argument("--person")
    ap.add_argument("--brand")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.cmd == "roles":
        rs = SH.roles()
        if a.json:
            print(json.dumps(rs, indent=1))
            return
        for r, v in rs.items():
            st = SH.stage_of_role(r)
            print("%-20s %-16s %s" % (r, ", ".join(v.get("holders") or []) or "—",
                                      (st["name"] + (" (live)" if st.get("state") == "live" else "")) if st else ""))
        return
    if a.cmd == "waiting":
        rls = [a.role] if a.role else SH.roles_of(a.person) if a.person else []
        if not rls:
            raise SystemExit("Say --role <role> or --person <name>" + (" (%s holds no role)" % a.person if a.person else ""))
        rows = [r for role in rls for r in waiting(role, a.brand)]
        if a.json:
            print(json.dumps(rows, indent=1))
            return
        for role in rls:
            mine = [r for r in rows if r["role"] == role]
            print("%s — %d open of %d" % (role, sum(r["state"] in ("open", "in-progress", "back-for-revision") for r in mine), len(mine)))
            for r in mine:
                if r["state"] in ("open", "in-progress", "back-for-revision"):
                    print("  %s  %-8s %-17s %s" % (r["number"], r["brand"], r["stage"], r["title"][:60] + " · " + r["state"] + (" · " + r["revision_id"].rsplit("-", 1)[-1] if r.get("revision_id") else "")))
        print("\nSay: open brief <number> as <role>")
        return
    if not a.brief or not a.role:
        raise SystemExit("open needs a brief number and --role")
    o = opening(a.brief, a.role, a.brand)
    if a.json:
        print(json.dumps(o, indent=1))
        return
    if o.get("start"):
        print(o["start"].rstrip())
        print("\n---\nFolder: %s\nActivate: %s\nDoor: %s" % (o["folder"], o["say"], o.get("run") or ""))
    else:
        print("%s\nSay: %s" % (o.get("note", ""), o["say"]))


if __name__ == "__main__":
    main()
