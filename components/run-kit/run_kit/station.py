"""One station hands its run folder to the next through Shared Assets (2026-10-19).

the owner: "build the mini doors per station". A mini job runs in a fresh clone and its media never
reaches git (workspace rule 3), so each station of the video line PUTS its whole run folder on the
company drive at the mirror path and the next station's job GETS it from there:

    Shared Assets/runs/<machine>/<brand>/<label>/          (runs/README.md, the Drive mirror)

One label follows a swipe through every station (teardown → writing → production → edit), so a
station needs only the label to find the one before it.

    push(run_dir, machine, brand, label, copy_to=None)
                                              -> {"placed": n, "notes": [...], "to", "drive", "record"};
                                                 writes <run_dir>/drive.json (and copy_to/drive.json),
                                                 the Drive folder and each pushed file's id
                                                 (LD-64 (records Drive ids))
    pull(machine, brand, label, dest)         -> dest as a Path, or None when the Drive folder is not there
    parts(machine, brand, label)              -> ["runs", machine, brand, label]

The Drive is reached only through gdrive-creator's shared reach (LD-14 (shared Drive reach)):
the API by id when GDRIVE_SA_KEY is set (the mini), else the person's mount. Nothing here deletes,
moves or renames a Drive file; a file with the same name is updated in place. Python 3.9, stdlib at
import.
"""
import json
import os
import sys
from pathlib import Path

_GDC = Path(__file__).resolve().parents[2] / "gdrive-creator"
SKIP_DIRS = {"__pycache__", ".cache", ".git", "_library"}
SKIP_SUFFIXES = (".pyc", ".lock", ".tmp")


def _reach():
    return _shared_reach()


def _shared_reach():
    """gdrive-creator's reach module itself — the drive.json shape comes from here even where a
    caller has swapped `_reach` for a stand-in (LD-64 (records Drive ids))."""
    if str(_GDC) not in sys.path:
        sys.path.insert(0, str(_GDC))
    from gdrive_creator import reach
    return reach


def parts(machine, brand, label):
    for name, v in (("machine", machine), ("brand", brand), ("label", label)):
        if not v or "/" in str(v) or str(v).startswith("."):
            raise ValueError("%s %r is not one plain name" % (name, v))
    return ["runs", str(machine), str(brand), str(label)]


def _groups(run_dir, skip=()):
    """{relative folder: [files]} for every regular file under run_dir (links followed), leaving out
    every folder whose path relative to run_dir is in `skip` (e.g. "framemap/frames")."""
    run_dir = Path(run_dir)
    skip = {str(Path(s)) for s in skip}
    out = {}
    for root, dirs, files in os.walk(str(run_dir), followlinks=True):
        rel = Path(root).relative_to(run_dir)
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and str(rel / d) not in skip)
        for f in sorted(files):
            p = Path(root) / f
            if f.endswith(SKIP_SUFFIXES) or not p.is_file():
                continue
            out.setdefault(rel, []).append(p)
    return out


def push(run_dir, machine, brand, label, reach=None, skip=(), copy_to=None):
    """`skip`: folders under run_dir that stay on this machine — the teardown passes its frames/ and
    element crops (2026-10-20, worklist 7b option (i)).

    After every push run_dir/drive.json is written — the Drive folder and each pushed file's id
    (LD-64 (records Drive ids)) — and the same bytes go to copy_to/drive.json when copy_to is given
    (a door's $OUT, which reaches git). A top-level drive.json already in run_dir is a previous
    record: it is never uploaded and is always replaced. A reach with put only records null ids."""
    reach = reach or _reach()
    base = parts(machine, brand, label)
    placed, notes, rows = 0, [], []
    route, folder_id = None, None
    record = Path(run_dir) / "drive.json"
    for rel, files in sorted(_groups(run_dir, skip).items(), key=lambda kv: str(kv[0])):
        sub = [] if str(rel) == "." else list(rel.parts)
        if not sub:
            files = [f for f in files if Path(f).name != "drive.json"]
            if not files:
                continue
        if hasattr(reach, "put_ids"):
            r = reach.put_ids(files, base + sub)
            how, got, note = r["how"], r["placed"], r["note"]
            got_rows = r["files"]
            if not sub:
                folder_id = r.get("folder_id")
        else:
            how, got, note = reach.put(files, base + sub)
            got_rows = [{"name": Path(p).name, "id": None} for p in got]
        if route is None:
            route = how
        placed += len(got)
        rows.extend({"path": "/".join(sub + [row["name"]]), "id": row.get("id"),
                     "kind": row.get("kind")} for row in got_rows)
        if note:
            notes.append("%s: %s" % ("/".join(sub) or ".", note))
            if how == "none":
                break
    rec = (reach if hasattr(reach, "drive_json") else _shared_reach()).drive_json(
        base, folder_id, route or "none", rows)
    body = json.dumps(rec, indent=1, ensure_ascii=False) + "\n"
    record.write_text(body, encoding="utf-8")
    if copy_to is not None:
        Path(copy_to).mkdir(parents=True, exist_ok=True)
        (Path(copy_to) / "drive.json").write_text(body, encoding="utf-8")
    return {"placed": placed, "notes": notes, "to": "Shared Assets/" + "/".join(base),
            "drive": rec, "record": str(record)}


def pull(machine, brand, label, dest, reach=None):
    reach = reach or _reach()
    got = reach.fetch_folder(parts(machine, brand, label), dest, recursive=True)
    if got is None and machine == "video-teardown":
        got = _pull_old_mirror(label, dest, reach)
    return got


# ONE ORDER FOR EVERY STATION DOOR — LD-53 (station-path runner), widened 2026-10-20 (the team: "stations
# read the repo first"; "we should be able to see all of the files he uses on the mini"):
#   (1) the machine's working folder; (2) the REPO copy runs/<station>/<brand>/<label>/, for text;
#   (3) Shared Assets runs/<station>/<brand>/<label>/, for media only when the station needs it;
#   (4) the legacy components/ mirror (pull()'s bridge), only until the move.
# Every part's source is printed and written into the WORK copy's run.json ("sources"); the repo
# copy is only ever read, never edited.

def _drive_when(parts_, reach):
    """The Drive folder's modifiedTime for Shared Assets/<parts_>, or "modified unknown"."""
    try:
        E = reach._engine()
        fid = E.folder_by_path("Shared Assets/" + "/".join(parts_))
        if fid:
            return "modified " + E.service().files().get(fileId=fid, fields="modifiedTime",
                                                          supportsAllDrives=True).execute().get("modifiedTime", "unknown")
    except Exception:
        pass
    return "modified unknown"


def _git_stamp(path):
    import subprocess
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h %cI", "--", str(path)], cwd=str(path),
                             capture_output=True, text=True, timeout=20).stdout.strip()
        return out or "uncommitted"
    except Exception:
        return "git unknown"


def _copy_missing(src, dest, overwrite=False):
    """Copy src's files into dest — never over a file dest already has, unless overwrite.
    -> how many were copied."""
    import shutil
    n = 0
    for p in sorted(Path(src).rglob("*")):
        if not p.is_file():
            continue
        out = Path(dest) / p.relative_to(src)
        if out.exists() and not overwrite:
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(p), str(out))
        n += 1
    return n


TEXT_SUFFIXES = {".json", ".md", ".txt", ".csv", ".html", ".log", ".jsonl"}


def _has_media(p):
    """Is this need/want really here? A file: it exists. A folder: it holds at least one file that is
    not text — the repo copy carries a media folder's manifest and timing JSON only, and 'the folder
    exists' let a door skip the voice mp3s on Shared Assets (found 2026-10-20, the second edit run)."""
    p = Path(p)
    if p.is_file():
        return True
    if not p.is_dir():
        return False
    return any(f.is_file() and f.suffix.lower() not in TEXT_SUFFIXES for f in p.rglob("*"))


def resolve(machine, brand, label, work, also=(), need=(), want=(), keep_stage=None, overwrite=False,
            repo=None, reach=None):
    """The run a door works on, in WORK (made when missing), found in the one order above.

    machine   the station whose run this is (the one before the caller: a writing door asks for
              "video-teardown"); `also` names more stations whose repo/Drive copies fill it in
              (production asks "video-writing" also "video-teardown").
    need      files or folders, relative to the run, the station cannot work without (media:
              "source.mp4", "framemap/shots", "media", "vo"); only these are fetched from the Drive
              when the working folder and the repo do not hold them.
    want      like need, fetched the same way, but a station that can work without it carries on
              (the source lines say it was not found).
    overwrite the caller found its working folder unusable (a writing run with no finished brief):
              the station's own repo copy is laid over it; `also` stations still only fill gaps.
    keep_stage  when the run came from the repo or the Drive, a predicate on stage keys: stages it
              rejects are dropped from the WORK copy's run.json, so a later station starts clean
              (the repo file is never edited).
    -> (work Path, [source lines]). Raises SystemExit naming every place looked when no run.json
    is found at all, or a needed part is still missing."""
    import json as _json
    import tempfile
    work = Path(work)
    if repo is None:
        from . import paths as _paths
        repo = _paths.repo()
    stations = [machine] + [m for m in also if m != machine]
    lines = []
    had_work = (work / "run.json").is_file() and not overwrite
    if had_work:
        lines.append("working folder %s" % work)
    for m in stations:
        rc = Path(repo) / "runs" / m / brand / label
        if (rc / "run.json").is_file():
            n = _copy_missing(rc, work, overwrite=overwrite and m == machine)
            if n or not had_work:
                lines.append("repo runs/%s/%s/%s @ %s (%d file(s))" % (m, brand, label, _git_stamp(rc), n))
    if not (work / "run.json").is_file():
        work.mkdir(parents=True, exist_ok=True)
        for m in stations:
            with tempfile.TemporaryDirectory() as t:
                if pull(m, brand, label, Path(t) / "run", reach=reach) is not None:
                    n = _copy_missing(Path(t) / "run", work)
                    lines.append("Shared Assets runs/%s/%s/%s, %s (%d file(s), whole folder)"
                                 % (m, brand, label, _drive_when(parts(m, brand, label), reach or _reach()), n))
                    break
    if not (work / "run.json").is_file():
        raise SystemExit("no %s run %r for %s — looked in %s, the repo runs/%s/%s/%s and Shared Assets "
                         "runs/%s/%s/%s" % (machine, label, brand, work, machine, brand, label, machine, brand, label))
    reach = reach or _reach()
    for item in tuple(need) + tuple(want):
        if _has_media(work / item):
            continue
        for m in stations:
            base = parts(m, brand, label)
            sub = list(Path(item).parts)
            got = reach.fetch_folder(base + sub, work / item, recursive=True)
            if got is None:
                got = reach.get(base + sub[:-1], sub[-1], str((work / item).parent)) if hasattr(reach, "get") else None
            if got:
                lines.append("Shared Assets runs/%s/%s/%s/%s, %s" % (m, brand, label, item, _drive_when(base, reach)))
                break
    for i in want:
        if not _has_media(work / i):
            lines.append("not found anywhere: %s (the station carries on without it)" % i)
    missing = [i for i in need if not _has_media(work / i)]
    if missing:
        raise SystemExit("the %s run %r is missing %s — not in %s, the repo, or on Shared Assets"
                         % (machine, label, ", ".join(missing), work))
    st = _json.loads((work / "run.json").read_text())
    if keep_stage is not None and not had_work:
        dropped = [k for k in list(st.get("stages") or {}) if not keep_stage(k)]
        for k in dropped:
            del st["stages"][k]
        if dropped:
            lines.append("work copy reset: %s dropped (the repo copy is unchanged)" % ", ".join(dropped))
    st["sources"] = lines
    (work / "run.json").write_text(_json.dumps(st, indent=2))
    for ln in lines:
        print("source: " + ln)
    return work, lines


# BRIDGE — LD-53 (station-path runner), until LD-54 (Drive move list)'s move lands, then DROP IT.
# Teardowns made on the owner's Mac before 2026-10-20 sit in the old mirror,
# Shared Assets/tools/video-teardown/runs/swipes/<label>/, not at the station path. A pull that
# finds nothing at the station path looks there and SAYS SO, with the folder's modified date, so a
# run built on an old copy is never silent. A creator run (runs/creators/<handle>/<label>/) is not
# looked for: the handle is not known from the label.
OLD_MIRROR = ("tools", "video-teardown", "runs", "swipes")


def _pull_old_mirror(label, dest, reach):
    got = reach.fetch_folder(list(OLD_MIRROR) + [str(label)], dest, recursive=True)
    if got is None:
        return None
    where = "Shared Assets/" + "/".join(list(OLD_MIRROR) + [str(label)])
    when = _drive_when(list(OLD_MIRROR) + [str(label)], reach).replace("modified ", "")
    print("pulled from %s, modified %s — the old mirror, not the station path "
          "(LD-53 (station-path runner) bridge)" % (where, when))
    return got


# One shared file a machine keeps beside its runs (the owner's format calls: runs/video-teardown/
# format-calls.json), mirrored at the same path on Shared Assets so a mini job sees the calls he
# made on his own Mac. Kept off git on purpose: a page writing into the repo would collide with
# the shared clone's pulls.

def put_shared(path, machine, reach=None):
    reach = reach or _reach()
    how, placed, note = reach.put([Path(path)], ["runs", str(machine)])
    return {"how": how, "placed": placed, "note": note}


def get_shared(name, machine, dest_dir, reach=None):
    """Shared Assets runs/<machine>/<name> into dest_dir (overwriting this machine's copy), or None."""
    reach = reach or _reach()
    got = reach.get(["runs", str(machine)], name, str(dest_dir))
    return Path(got) if got else None
