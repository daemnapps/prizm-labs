"""Pack a design assignment at any source stage without declaring it generation-ready.

Called by handoff.py --assignment <manifest.json>. The manifest names a stable
queue key, source stage, current brief, next action and explicit source files.
Only files inside the workspace are accepted. Existing production packets and
returns are preserved. The normal handoff mirror supplies portable Drive ids.
"""
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import handoff as H
from .engine import BadRequest


def _name(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
        raise BadRequest(field + " must be a portable lowercase identifier")
    return value


def build(manifest, repo=None):
    repo = Path(repo or H.P.repo()).resolve()
    req = json.loads(Path(manifest).read_text())
    brand = _name(req.get("brand"), "brand")
    key = _name(req.get("id"), "id")
    if not key.startswith(brand + "_"):
        raise BadRequest("id must begin with the brand and underscore")
    if req.get("stage") not in ("idea", "brief", "production", "revision"):
        raise BadRequest("stage must be idea, brief, production or revision")
    for field in ("title", "brief", "next_action"):
        if not isinstance(req.get(field), str) or not req[field].strip():
            raise BadRequest(field + " is required")
    refs = req.get("references")
    if not isinstance(refs, list) or not refs:
        raise BadRequest("at least one explicit reference is required")
    validated = []
    for n, ref in enumerate(refs, 1):
        rel = Path(ref.get("path", ""))
        source = (repo / rel).resolve()
        if rel.is_absolute() or ".." in rel.parts or not source.is_relative_to(repo):
            raise BadRequest("reference must stay inside the workspace: " + str(rel))
        if any(part.startswith(("_hold", "_rejected", "_superseded")) for part in source.relative_to(repo).parts):
            raise BadRequest("set-aside references cannot be handed off: " + str(rel))
        if not source.is_file():
            raise BadRequest("missing reference: " + str(rel))
        if not ref.get("role"):
            raise BadRequest("each reference needs its role")
        validated.append((source, rel.as_posix(), ref["role"], "refs/%02d-%s" % (n, source.name)))
    home = "runs/handoffs/graphic-designer/%s/%s" % (brand, key)
    folder = repo / home
    prior = folder / "run.json"
    if prior.exists() and json.loads(prior.read_text()).get("packet_kind") != "design-assignment":
        raise BadRequest("existing production packet is preserved; use a distinct revision id")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "refs").mkdir(exist_ok=True)
    (folder / "returned").mkdir(exist_ok=True)
    packed = []
    for source, rel, role, local in validated:
        shutil.copy2(source, folder / local)
        packed.append({"source": rel, "role": role, "local": local,
                       "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    sheet = {"schema": 1, "packet_kind": "design-assignment", "status": "draft",
             "state": req["stage"], "execution_ready": False, "brief_key": key,
             "brand": brand, "product": req.get("product"), "source_id": req.get("source_id", key),
             "title": req["title"], "next_action": req["next_action"], "references": packed,
             "readiness": {"blockers": ["Design assignment: follow RUN.md; generation is not authorized by this packet."]},
             "steps": [{"n": 1, "job": "design-assignment", "draft": True, "references": packed}],
             "handoff": {"role": "graphic-designer", "folder": home, "drive": "Shared Assets/" + home},
             "made": datetime.now(timezone.utc).isoformat()}
    (folder / "BRIEF.md").write_text("# " + req["title"] + "\n\n" + req["brief"].strip() + "\n")
    run = ["# Design assignment", "", "Stage: " + req["stage"], "",
           "## Next action", "", req["next_action"], "",
           "This packet is ready to work on at the stated stage. It is not an execution-ready generation plan.",
           "Read BRIEF.md first. Current words there supersede older words in source references.",
           "Keep editable design sources and return exports plus a short change note into returned/.",
           "Final approval and launch remain in their existing workflow.", "", "## References", ""]
    run += ["- [%s](%s) — %s" % (r["role"], r["local"], r["source"]) for r in packed]
    (folder / "RUN.md").write_text("\n".join(run) + "\n")
    (folder / "run.json").write_text(json.dumps(sheet, indent=2) + "\n")
    return folder, sheet


def publish(folder, sheet, repo=None):
    """Mirror through the existing handoff writer, then publish its file ids."""
    dest = H.mirror_folder(folder, repo=repo)
    for ref in sheet["references"]:
        ref["drive_id"] = dest["files"][ref["local"]]
        ref["label"] = dest["label"] + "/" + ref["local"]
    sheet["handoff"].update({"drive_id": dest["id"], "link": dest["link"]})
    (folder / "run.json").write_text(json.dumps(sheet, indent=2) + "\n")
    (folder / "handoff.json").write_text(json.dumps({"packet_kind": "design-assignment", "made": sheet["made"],
                                                   "drive": dest, "source_id": sheet["source_id"]}, indent=2) + "\n")
    # Update only the two records after the asset upload; returned files are never replaced.
    from gdrive_creator import engine as E
    svc = E.service()
    for name in ("run.json", "handoff.json"):
        E.upload_file(str(folder / name), name, dest["id"], svc=svc)
    return dest
