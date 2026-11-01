"""Make a brief in Claude Code with the Higgsfield tools: the exact parts, so the person's Claude never retypes them.

    python3 components/briefs/make.py waiting [--role graphic-designer|video-editor] [--brand b]
    python3 components/briefs/make.py plan <brief> <step>        the step's files (fetched from the Drive) + the exact call
    python3 components/briefs/make.py save <brief> <step> --record <file.json>
    python3 components/briefs/make.py save <brief> cut --file <video>

`<brief>` is a brief number (0341), a brief key or a hand-off folder. The hand-off folder is
`runs/handoffs/<role>/<brand>/<brief key>/`, the same path under `Shared Assets/` on the Drive; what is missing here is
read from the Drive by id (gdrive-creator, GDRIVE_SA_KEY by name).

`plan` prints JSON: the files to upload in order (each with `media_upload`, PUT the bytes, `media_confirm`) and the
tool call with the prompt word for word out of run.json; the caller puts each upload's media id where `plan` says,
nothing else. `save` takes Higgsfield's own record of the generation (the reply of `show_generation_by_ids`, saved
unchanged to a file), downloads the result, names it as RUN.md says, writes `<asset>.record.json` beside it in
`returned/`, puts both on the Drive and runs image-edit's reference check on the folder. Spends nothing itself: the
Higgsfield call is the person's, after their Approve.
"""
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
HANDOFFS = REPO / "runs" / "handoffs"
ROLES = ("graphic-designer", "video-editor")
RETURNED = "returned"
TEXT = ("BRIEF.md", "RUN.md", "run.json")


def _runsheet():
    spec = importlib.util.spec_from_file_location("briefs_runsheet", HERE / "runsheet.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _drive():
    gc = str(REPO / "components" / "gdrive-creator")
    if gc not in sys.path:
        sys.path.append(gc)
    from gdrive_creator import engine, reach
    return engine, reach


def parts_of(folder):
    """Shared Assets/<parts> for a hand-off folder: the same words as its repo path."""
    return list(Path(folder).resolve().relative_to(REPO).parts)


def _matches(name, want):
    w = want.strip().lower()
    if re.fullmatch(r"\d{1,4}", w):
        return name.lower().endswith(f"brief-{int(w):04d}")
    return name.lower() == w


def find(brief, brand=None):
    """The hand-off folder for a brief: here when it is here, else found on the Drive and its words fetched."""
    p = Path(brief)
    if (p / "run.json").is_file() or (REPO / p / "run.json").is_file():
        return p if p.is_absolute() else REPO / p
    here = [d for d in HANDOFFS.glob("*/*/*") if d.is_dir() and d.parent.parent.name in ROLES
            and (not brand or d.parent.name == brand) and _matches(d.name, brief)]
    if len(here) > 1:
        raise SystemExit("REFUSED: more than one brief matches %s: %s. Give the brief key."
                         % (brief, ", ".join(d.name for d in here)))
    if here and all((here[0] / t).is_file() for t in TEXT):
        return here[0]
    E, R = _drive()
    svc = E.service()
    for role in ROLES:
        rid = E.folder_by_path(f"Shared Assets/runs/handoffs/{role}", svc=svc)
        for b in _subfolders(E, svc, rid):
            if brand and b["name"] != brand:
                continue
            for f in _subfolders(E, svc, b["id"]):
                if _matches(f["name"], brief):
                    folder = HANDOFFS / role / b["name"] / f["name"]
                    folder.mkdir(parents=True, exist_ok=True)
                    for x in E.list_files(f["id"], svc=svc):
                        if x["name"] in TEXT:
                            E.get_media(x["id"], folder / x["name"], svc=svc)
                    return folder
    raise SystemExit(f"REFUSED: no hand-off folder for {brief} here or on the Drive")


def _subfolders(E, svc, parent):
    if not parent:
        return []
    q = f"'{parent}' in parents and trashed = false and mimeType = '{E.FOLDER_MIME}'"
    r = svc.files().list(q=q, fields="files(id,name)", pageSize=1000, supportsAllDrives=True,
                         includeItemsFromAllDrives=True).execute()
    return r.get("files") or []


def waiting(role=None, brand=None):
    """Every hand-off on the Drive whose returned/ is still empty, oldest folder first: [(role, brand, key)]."""
    E, R = _drive()
    svc = E.service()
    out = []
    for r in (role,) if role else ROLES:
        rid = E.folder_by_path(f"Shared Assets/runs/handoffs/{r}", svc=svc)
        for b in _subfolders(E, svc, rid):
            if brand and b["name"] != brand:
                continue
            for f in _subfolders(E, svc, b["id"]):
                ret = [x for x in _subfolders(E, svc, f["id"]) if x["name"] == RETURNED]
                if not ret or not E.list_files(ret[0]["id"], svc=svc):
                    out.append((r, b["name"], f["name"]))
    return sorted(out, key=lambda x: (x[1], x[2]))


def _step(folder, n):
    sheet = json.loads((folder / "run.json").read_text())
    for s in sheet["steps"]:
        if s["n"] == int(n):
            return sheet, s
    raise SystemExit(f"REFUSED: {folder.name} has no step {n} (it has 1-{len(sheet['steps'])})")


def _ref_path(folder, r):
    return folder / (r.get("local") or "")


def fetch_refs(folder, s):
    """The step's reference files into refs/, each read from the Drive copy by id when it is not here yet."""
    missing = [r for r in s["references"] if r.get("local") and not _ref_path(folder, r).is_file()]
    if not missing:
        return
    E, R = _drive()
    svc = E.service()
    rid = E.folder_by_path("Shared Assets/" + "/".join(parts_of(folder) + ["refs"]), svc=svc)
    have = {x["name"]: x["id"] for x in E.list_files(rid, svc=svc)} if rid else {}
    for r in missing:
        name = Path(r["local"]).name
        if name not in have:
            raise SystemExit(f"REFUSED: {r['local']} is not in the Drive copy of {folder.name}")
        E.get_media(have[name], _ref_path(folder, r), svc=svc)


def plan(folder, n):
    sheet, s = _step(folder, n)
    if s["job"] == "words-only":
        return {"step": s["n"], "asset": s["asset"], "no_generation": True,
                "do": "Put these words on the plate in image-edit's type layer and save it as the asset name",
                "plate": str(_ref_path(folder, s["references"][0])), "words_on_top": s["words_on_top"]}
    fetch_refs(folder, s)
    if s["job"] == "set-change":
        return set_plan(folder, s)
    rs = _runsheet()
    uploads = [str(_ref_path(folder, r).relative_to(REPO)) for r in s["references"]]
    tool, params = rs.agent_call(s, prompt=True, media=lambda r: f"<media id of upload {s['references'].index(r) + 1}>")
    return {"step": s["n"], "asset": s["asset"], "what": s["what"],
            "upload_in_order": uploads, "tool": tool, "params": params,
            "words_on_top": s.get("words_on_top") or [],
            "then": f"python3 components/briefs/make.py save {folder.name} {s['n']} --record <the show_generation_by_ids "
                    f"reply for this generation, saved unchanged to a file>"}


def set_plan(folder, s):
    """A change to the kept 3D set: no flat picture call. The set request goes beside the run sheet as the file the
    filing step names, and the plan is the request's own steps."""
    ask = s["set_request"]
    f = folder / f"set-request-step-{s['n']:02d}.json"
    f.write_text(json.dumps(ask, indent=1, ensure_ascii=False) + "\n")
    return {"step": s["n"], "asset": s["asset"], "what": s["what"], "set_change": True, "no_flat_picture": True,
            "change": ask.get("change"), "set": ask.get("set"), "credits": ask.get("credits"),
            "flags": ask.get("flags") or [], "steps": ask.get("steps") or [], "print_words": s["prompt"],
            "request": str(f.relative_to(REPO)),
            "files": [str(_ref_path(folder, r).relative_to(REPO)) for r in s["references"]],
            "words_on_top": s.get("words_on_top") or [],
            "then": f"python3 tools/image-production/picture_sets.py put-change {f.relative_to(REPO)} --render <render> "
                    f"--print <print> --note 'kept: <why>', then python3 components/briefs/make.py save {folder.name} {s['n']} "
                    "--record <the generation reply for the print, saved unchanged to a file>"}


def _result_url(record):
    items = record.get("items") if isinstance(record, dict) else None
    g = (items or [record])[0]
    res = g.get("results") or {}
    if isinstance(res, list):
        res = res[0] if res else {}
    url = res.get("rawUrl") or res.get("url") or res.get("raw_url")
    if not url:
        raise SystemExit("REFUSED: the record has no result link (results.rawUrl). Save the show_generation_by_ids "
                         "reply unchanged, after the generation has finished.")
    return url


def save(folder, n, record=None, file=None):
    sheet = json.loads((folder / "run.json").read_text())
    ret = folder / RETURNED
    ret.mkdir(exist_ok=True)
    placed = []
    if str(n) == "cut":
        cut = (sheet.get("cut") or {}).get("asset") or f"{sheet['brief_key']}-control.mp4"
        if not file:
            raise SystemExit("REFUSED: the cut is saved from a file: --file <video>")
        shutil.copyfile(file, ret / cut)
        placed = [ret / cut]
    else:
        _, s = _step(folder, n)
        if not record:
            raise SystemExit("REFUSED: --record <file> is Higgsfield's own record of the generation; without it "
                             "nothing proves what went in")
        rec_text = Path(record).read_text()
        url = _result_url(json.loads(rec_text))
        out = ret / s["asset"]
        with urllib.request.urlopen(url) as r, open(out, "wb") as fh:
            shutil.copyfileobj(r, fh)
        rec = ret / (s["asset"] + ".record.json")
        rec.write_text(rec_text)
        placed = [out, rec]
    E, R = _drive()
    how, where, note = R.put([str(p) for p in placed], parts_of(folder) + [RETURNED])
    print(f"saved: {', '.join(p.name for p in placed)}  ->  Shared Assets/{'/'.join(parts_of(folder))}/{RETURNED}"
          + (f"  ({note})" if note else ""))
    subprocess.run([sys.executable, str(REPO / "tools" / "image-edit" / "reference_check.py"), str(folder)],
                   check=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("waiting")
    w.add_argument("--role", choices=ROLES)
    w.add_argument("--brand")
    p = sub.add_parser("plan")
    p.add_argument("brief")
    p.add_argument("step")
    p.add_argument("--brand")
    v = sub.add_parser("save")
    v.add_argument("brief")
    v.add_argument("step")
    v.add_argument("--record")
    v.add_argument("--file")
    v.add_argument("--brand")
    a = ap.parse_args(argv)
    if a.cmd == "waiting":
        rows = waiting(a.role, a.brand)
        for r, b, k in rows:
            print(f"{b:8}  {r:16}  {k}")
        print(f"{len(rows)} waiting")
        return 0
    folder = find(a.brief, a.brand)
    if a.cmd == "plan":
        print(json.dumps(plan(folder, a.step), indent=1, ensure_ascii=False))
        return 0
    save(folder, a.step, a.record, a.file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
