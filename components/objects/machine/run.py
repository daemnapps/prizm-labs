#!/usr/bin/env python3
"""objects: the free, local half of making a 3D object (the reference image comes from the
Higgsfield connector, run by Claude; see ../CLAUDE.md).

    run.py make   <project> <id> --ref <image> [--what "..."] [--word "..."] [--mesh <glb>] [--prompt-file <md>] [--credits N]
    run.py finish <project> <id> [--finish satin|keep]
    run.py list   <project>

make: mesh (local generator, or --mesh to use one you already have) → finish → check still → web copy → record.
Everything lands in <project>/3d/objects/<id>/ and <project>/3d/catalogue.json."""
import argparse, datetime as dt, json, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAEMN = HERE.parents[2]
MAKE3D = HERE.parents[1] / "3d" / "make3d"


def sh(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd)[:180])
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def catalogue(project: Path):
    p = project / "3d/catalogue.json"
    return p, (json.loads(p.read_text()) if p.exists() else {"_readme": "Every 3D object made for this project by tools/objects.", "objects": {}})


def finish(project: Path, oid: str, preset: str):
    d = project / "3d/objects" / oid
    raw = d / f"{oid}-raw.glb"
    sh(["node", HERE / "finish.mjs", raw, d, "--name", oid, "--finish", preset])
    sh(["blender", "-b", "-P", HERE / "still.py", "--", (d / f"{oid}.glb").resolve(), (d / f"{oid}-still.png").resolve()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return d


def cmd_make(a):
    if not (a.mesh or a.local):
        sys.exit("Pass --mesh <file.glb> (the mesh the Higgsfield connector made, the default) "
                 "or --local (components/3d/make3d, free, for background props).")
    project = (DAEMN / a.project).resolve() if not Path(a.project).is_absolute() else Path(a.project)
    d = project / "3d/objects" / a.id
    d.mkdir(parents=True, exist_ok=True)
    ref = Path(a.ref).resolve()
    shutil.copy(ref, d / f"{a.id}-ref{ref.suffix}")
    raw = d / f"{a.id}-raw.glb"
    if a.mesh:
        shutil.copy(a.mesh, raw); route = "higgsfield (given mesh)"
    elif MAKE3D.exists():
        sh([MAKE3D, ref, raw]); route = "local (components/3d/make3d)"
    else:
        sys.exit("No local 3D generator yet (components/3d/make3d). Pass --mesh <glb> from the paid route, with the owner's OK.")
    if a.prompt_file:
        shutil.copy(a.prompt_file, d / "prompt.md")
    finish(project, a.id, a.finish)
    cp, cat = catalogue(project)
    cat["objects"][a.id] = {
        "what": a.what, "song_word": a.word, "made": dt.date.today().isoformat(), "mesh_route": route,
        "finish": a.finish, "credits": a.credits,
        "files": {k: str((d / v).relative_to(project)) for k, v in
                  {"ref": f"{a.id}-ref{ref.suffix}", "glb": f"{a.id}.glb", "web": f"{a.id}.web.json", "still": f"{a.id}-still.png"}.items()},
        "checked": False,
    }
    cp.write_text(json.dumps(cat, indent=1))
    print(f"\n{a.id}: made. Look at {d / (a.id + '-still.png')} next to the reference, then mark it checked.")


def cmd_finish(a):
    project = (DAEMN / a.project).resolve()
    finish(project, a.id, a.finish)


def cmd_list(a):
    project = (DAEMN / a.project).resolve()
    _, cat = catalogue(project)
    for k, v in cat["objects"].items():
        print(f"{k:24s} {'✓' if v.get('checked') else '·'} {v.get('mesh_route','')[:20]:20s} {v.get('what') or ''}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    m = s.add_parser("make"); m.add_argument("project"); m.add_argument("id"); m.add_argument("--ref", required=True)
    m.add_argument("--what", default=""); m.add_argument("--word", default=""); m.add_argument("--prompt-file")
    mr = m.add_mutually_exclusive_group(); mr.add_argument("--mesh"); mr.add_argument("--local", action="store_true")
    m.add_argument("--finish", default="satin"); m.add_argument("--credits", type=float, default=0)
    f = s.add_parser("finish"); f.add_argument("project"); f.add_argument("id"); f.add_argument("--finish", default="satin")
    l = s.add_parser("list"); l.add_argument("project")
    a = p.parse_args()
    {"make": cmd_make, "finish": cmd_finish, "list": cmd_list}[a.cmd](a)


if __name__ == "__main__":
    main()
