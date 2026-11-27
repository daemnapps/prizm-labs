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


ALSO = {"video-editor": "video-producer"}      # the production folder is the same maker's: 0334 was handed out there
DONE = ("shipped", "superseded", "killed")     # the brief register's own words for a brief nobody has to make


IDEA = re.compile(r"_idea-\d+$", re.I)        # a hand-off named by its production id: the register has not numbered it


def approved_keys(role, repo=None):
    """The briefs this role may read today: approved by the owner, not held to a later day (approved.py)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import approved
    return approved.readable(role, repo or REPO)


def done_keys(repo=None):
    """Every brief the register says is finished: on Meta (shipped), replaced or killed. Its hand-off folder stays, and is
    never work again (2026-11-25: five ads already on Meta read as waiting because they came back by another road and
    their returned/ was empty)."""
    f = Path(repo or REPO) / "components" / "image-teardown" / "briefs.json"
    try:
        return {k for k, v in (json.loads(f.read_text(encoding="utf-8")).get("briefs") or {}).items()
                if isinstance(v, dict) and v.get("state") in DONE}
    except (OSError, ValueError):
        return set()


def waiting(role=None, brand=None):
    """Every hand-off on the Drive whose returned/ is still empty and whose brief the owner approved and the register
    does not call finished, oldest folder first: [(role, brand, key)]."""
    E, R = _drive()
    svc = E.service()
    out, done, seen = [], done_keys(), set()
    for r in (role, ALSO[role]) if role in ALSO else (role,) if role else ROLES + tuple(ALSO.values()):
        ok = approved_keys(r)
        rid = E.folder_by_path(f"Shared Assets/runs/handoffs/{r}", svc=svc)
        for b in _subfolders(E, svc, rid):
            if brand and b["name"] != brand:
                continue
            for f in _subfolders(E, svc, b["id"]):
                if f["name"].startswith("_"):    # _superseded, _wrong-number: set-aside folders, never work (2026-11-17)
                    continue
                if IDEA.search(f["name"]):       # an idea with no brief number yet is never a maker's work
                    continue
                if f["name"] in done:            # already on Meta, replaced or killed: the register says so
                    continue
                if f["name"] not in ok or (b["name"], f["name"]) in seen:   # only a brief the owner approved is a maker's to read (2026-11-25)
                    continue
                ret = [x for x in _subfolders(E, svc, f["id"]) if x["name"] == RETURNED]
                if not ret or not E.list_files(ret[0]["id"], svc=svc):
                    out.append((r, b["name"], f["name"]))
                seen.add((b["name"], f["name"]))
    return sorted(out, key=lambda x: (x[1], x[2]))


KIT_START = ("EDITOR-START.md", "PACK.md", "RUN.md", "BRIEF.md", "CLIPS.md")


def _kit(folder, why):
    """A hand-off with no generation steps (a re-edit, a cut of clips already made, an editor kit): ready to make as it
    is, from the folder's own start page."""
    start = next((x for x in KIT_START if (folder / x).is_file()), None)
    raise SystemExit(f"NOTHING TO GENERATE: {folder.name} is {why}. It is ready to make as it is: open "
                     f"{start or 'the folder'} and follow it; finished files go in {RETURNED}/, then "
                     f"`make.py save {folder.name} cut --file <video>`.")


def _step(folder, n):
    if not (folder / "run.json").is_file():
        _kit(folder, "an editor kit with no run sheet")
    sheet = json.loads((folder / "run.json").read_text())
    if sheet.get("packet_kind") == "filming-assignment":
        raise SystemExit("REFUSED: filming assignment; film the takes and use delivery.py --ingest-filming")
    if not isinstance(sheet.get("steps"), list):
        _kit(folder, "a " + str(sheet.get("kind") or "cut") + " kit")
    for s in sheet["steps"]:
        if s["n"] == int(n):
            return sheet, s
    raise SystemExit(f"REFUSED: {folder.name} has no step {n} (it has 1-{len(sheet['steps'])})")


def _ref_path(folder, r):
    """A reference's file in the hand-off. An input an earlier step makes (`<asset> (step N makes it)`) is that step's
    saved output in returned/ (2026-11-17: the door printed the folder itself as the upload)."""
    if not r.get("local"):
        m = re.match(r"(\S+\.(?:png|jpg|jpeg|mp4|mp3|wav))\s*\((?:not made yet: )?step \d+ makes it\)", str(r.get("file") or ""))
        if m:
            return folder / RETURNED / m.group(1)
    return folder / (r.get("local") or "")


def fetch_refs(folder, s):
    """The step's reference files into refs/, each read from the Drive copy by id when it is not here yet."""
    missing = [r for r in s["references"] if r.get("local") and not _ref_path(folder, r).is_file()]
    if not missing:
        return
    E, R = _drive()
    svc = E.service()
    seen = {}
    for r in missing:
        name = Path(r["local"]).name
        sub = str(Path(r["local"]).parent) or "refs"      # refs/, voice/ … : read from the same folder on the Drive
        if sub not in seen:
            rid = E.folder_by_path("Shared Assets/" + "/".join(parts_of(folder) + sub.split("/")), svc=svc)
            seen[sub] = {x["name"]: x["id"] for x in E.list_files(rid, svc=svc)} if rid else {}
        have = seen[sub]
        if name not in have:
            raise SystemExit(f"REFUSED: {r['local']} is not in the Drive copy of {folder.name}")
        E.get_media(have[name], _ref_path(folder, r), svc=svc)


def plan(folder, n):
    sheet, s = _step(folder, n)
    if sheet.get("packet_kind") == "filming-assignment":
        raise ValueError("creator/founder assignment: film the expected takes; use delivery.py --ingest-filming")
    # an editor-built brief (owner, 2026-11-17: the editor makes the pictures and clips) carries drafted prompts by design
    if sheet.get("execution_ready") is False or (s.get("draft") and not sheet.get("editor_builds")):
        raise SystemExit("REFUSED: draft packet is not execution-ready: " + "; ".join((sheet.get("readiness") or {}).get("blockers") or ["finish production upstream"]))
    if s["job"] == "words-only":
        return {"step": s["n"], "asset": s["asset"], "no_generation": True,
                "do": "Put these words on the plate in image-edit's type layer and save it as the asset name",
                "plate": str(_ref_path(folder, s["references"][0])), "words_on_top": s["words_on_top"],
                "then": f"python3 components/briefs/make.py save {folder.name} {s['n']} --file <the finished picture>"}
    fetch_refs(folder, s)
    if s["job"] == "set-print":                  # the run's kept 3D print IS the picture: words on top, nothing generated
        r = s["references"][0]
        return {"step": s["n"], "asset": s["asset"], "no_generation": True,
                "do": "The main picture is the set's kept 3D print. Put these words on it in image-edit's type layer and "
                      "save it as the asset name",
                "plate": str(_ref_path(folder, r)) if r.get("local") else r.get("file"), "words_on_top": s["words_on_top"],
                "then": f"python3 components/briefs/make.py save {folder.name} {s['n']} --file <the finished picture>"}
    if s["job"] == "set-change":
        return set_plan(folder, s)
    if s["job"] == "3d-print":
        return print_plan(folder, s, sheet)
    rs = _runsheet()
    uploads = [str(_ref_path(folder, r).relative_to(REPO)) for r in s["references"]]
    tool, params = rs.agent_call(s, prompt=True, media=lambda r: f"<media id of upload {s['references'].index(r) + 1}>")
    return {"step": s["n"], "asset": s["asset"], "what": s["what"],
            "upload_in_order": uploads, "tool": tool, "params": params,
            "words_on_top": s.get("words_on_top") or [],
            "then": f"python3 components/briefs/make.py save {folder.name} {s['n']} --record <the show_generation_by_ids "
                    f"reply for this generation, saved unchanged to a file>"}


def print_plan(folder, s, sheet):
    """A picture made as a 3D print on the maker's own Higgsfield account (image-production RULE GATE-4): the steps,
    the one reference to upload (a board when the step has several), the print call and how to save it."""
    rs = _runsheet()
    sent = [r for r in s["references"] if not r.get("look_only")]
    files = [str(_ref_path(folder, r).relative_to(REPO)) for r in sent]
    board = None
    if len(files) > 1:                                   # the print takes ONE reference: everything on one board
        out = folder / f"print-reference-step-{s['n']:02d}.png"
        board = {"command": "python3 components/image-production/cast_board.py refs %s %s"
                            % (out.relative_to(REPO), " ".join(files)), "board": str(out.relative_to(REPO))}
    key = sheet.get("brief_key") or folder.name
    return {"step": s["n"], "asset": s["asset"], "what": s["what"], "print_3d": True, "no_flat_picture": True,
            "credits": s["print"]["credits"], "project": s["print"].get("project") or f"{key} sets",
            # a hand-off that carries its own 3D builds (3d/JUTSU.md) gives the print its own steps (runsheet.print_how)
            "steps": [x.format(project=s["print"].get("project") or f"{key} sets")
                      for x in (s["print"].get("how") or rs.PRINT_STEPS)],
            "look_only": [str(_ref_path(folder, r).relative_to(REPO)) if r.get("local") else r.get("file")
                          for r in s["references"] if r.get("look_only")],
            "upload_reference": board["board"] if board else (files[0] if files else None), "reference_board": board,
            "tool": "scene_builder_3d_generate_angles",
            "params": {"projectId": "<the project above>", "operationId": "<the fresh render's operation id>",
                       "artifactId": "<the fresh render's artifact id>", "requestId": "<a new UUID>",
                       "referenceMediaId": "<media id of the upload>" if (board or files) else None,
                       "prompt": s["prompt"] + "\n" + s["print"]["prompt_tail"], "aspectRatio": "9:16", "resolution": "2k"},
            "then": f"python3 components/briefs/make.py save {folder.name} {s['n']} --record <the scene_builder_3d_get_generation "
                    "reply, once it has succeeded, saved unchanged to a file>"}


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
            "then": f"python3 components/image-production/picture_sets.py put-change {f.relative_to(REPO)} --render <render> "
                    f"--print <print> --note 'kept: <why>', then python3 components/briefs/make.py save {folder.name} {s['n']} "
                    "--record <the generation reply for the print, saved unchanged to a file>"}


def _result_url(record):
    if isinstance(record, dict) and isinstance(record.get("generation"), dict):    # a 3D Jutsu print's own reply
        jobs = record["generation"].get("jobs") or []
        url = next((j.get("result_url") for j in jobs if j.get("result_url")), None)
        if record["generation"].get("status") == "succeeded" and url:
            return url
        raise SystemExit("REFUSED: the print has not succeeded yet. Save the scene_builder_3d_get_generation reply "
                         "unchanged once its status is succeeded.")
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


def _provenance():
    """image-production's provenance file, loaded by path (stdlib only, no package imports)."""
    f = REPO / "components" / "image-production" / "image_production" / "provenance.py"
    spec = importlib.util.spec_from_file_location("ip_provenance_briefs", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def save(folder, n, record=None, file=None):
    sheet = json.loads((folder / "run.json").read_text()) if (folder / "run.json").is_file() else {}
    ret = folder / RETURNED
    ret.mkdir(exist_ok=True)
    placed = []
    if str(n) == "cut":
        cut = (sheet.get("cut") or {}).get("asset") or f"{sheet.get('brief_key') or folder.name}-control.mp4"
        if not file:
            raise SystemExit("REFUSED: the cut is saved from a file: --file <video>")
        shutil.copyfile(file, ret / cut)
        placed = [ret / cut]
    else:
        _, s = _step(folder, n)
        if s["job"] in ("words-only", "set-print") and file and not record:   # nothing generated: the finished file
            shutil.copyfile(file, ret / s["asset"])
            record, placed = None, [ret / s["asset"]]
        elif not record:
            raise SystemExit("REFUSED: --record <file> is Higgsfield's own record of the generation; without it "
                             "nothing proves what went in")
        if record:
            rec_text = Path(record).read_text()
            url = _result_url(json.loads(rec_text))
            out = ret / s["asset"]
            with urllib.request.urlopen(url) as r, open(out, "wb") as fh:
                shutil.copyfileobj(r, fh)
            rec = ret / (s["asset"] + ".record.json")
            rec.write_text(rec_text)
            placed = [out, rec]
    if str(n) != "cut" and placed and placed[0].suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        try:                                           # made through the process: the same record the tool's pictures get
            placed.append(_provenance().hand_off(placed[0], sheet.get("brief_key") or folder.name, s["n"], s["job"],
                                                 record=(placed[1].name if len(placed) > 1 else None)))
        except Exception as e:                         # noqa: BLE001  a record that cannot be written never stops a save
            print(f"  SKIP the picture's record: {type(e).__name__}: {e}")
    E, R = _drive()
    how, where, note = R.put([str(p) for p in placed], parts_of(folder) + [RETURNED])
    print(f"saved: {', '.join(p.name for p in placed)}  ->  Shared Assets/{'/'.join(parts_of(folder))}/{RETURNED}"
          + (f"  ({note})" if note else ""))
    subprocess.run([sys.executable, str(REPO / "components" / "image-edit" / "reference_check.py"), str(folder)],
                   check=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("waiting")
    w.add_argument("--role", choices=ROLES)
    w.add_argument("--brand")
    pickup = sub.add_parser("pickup")
    pickup.add_argument("brief")
    pickup.add_argument("--stage", default="production")
    pickup.add_argument("--continued-from")
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
    if a.cmd == "pickup":
        import pickup
        args = ["pickup", a.brief, "--stage", a.stage]
        if a.continued_from:
            args += ["--continued-from", a.continued_from]
        return pickup.main(args)
    if a.cmd == "waiting":
        rows = waiting(a.role, a.brand)
        for r, b, k in rows:
            print(f"{b:8}  {r:16}  {k}")
        print(f"{len(rows)} waiting")
        return 0
    folder = find(a.brief, a.brand)
    if a.cmd == "plan":
        if folder.name not in approved_keys(folder.parent.parent.name):
            raise SystemExit(f"REFUSED: {folder.name} is not approved by the owner yet, so it is not ready to make")
        print(json.dumps(plan(folder, a.step), indent=1, ensure_ascii=False))
        return 0
    save(folder, a.step, a.record, a.file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
