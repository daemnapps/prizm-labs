"""Writing result and retry receipts. Reads never call providers or alter a run.

Public: inspect_result(run_dir) -> the writing-result/v1 object. ``accepted``
means writing's checks completed for these exact files; it is not production
permission. Consumers must inspect the source again, not trust a saved boolean.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "writing-result/v1"
ACCEPTANCE_KEYS = ("swipe_match", "manifest", "cast_match", "production_contract",
                   "frame_carry", "viewer_check", "missed_checks", "section_fit",
                   "claims_fixed", "spoken_check", "hook_check", "owner_words_check",
                   "writing_acceptance", "writing_result", "writing_retry_budget",
                   "viewer_redo", "_v2_hook_remade", "writing_error", "writing_revalidation", "writing_notes")
IDENTITY_KEYS = ("brief", "brief_id", "brief_key", "registered_brief_id")
DELIVERY_KEYS = ("gdoc_url", "creator_folder", "start_here_url")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def child_state(parent, parent_slug):
    """Reset piece-specific state while retaining the source identity as provenance."""
    st = dict(parent)
    st["parent_provenance"] = {"run": parent_slug,
                               **{k: parent[k] for k in IDENTITY_KEYS + DELIVERY_KEYS if parent.get(k)}}
    for key in IDENTITY_KEYS + DELIVERY_KEYS + ACCEPTANCE_KEYS:
        st.pop(key, None)
    return st


def source_of(d, st):
    rel = ((st.get("stages") or {}).get("stage5") or {}).get("out") or "stages/5-brief.md"
    p = Path(d) / rel
    # Result references stay relative to the run; reject escaped legacy paths.
    try:
        rel = str(p.resolve().relative_to(Path(d).resolve()))
    except ValueError:
        return {"path": None, "sha256": None}
    return {"path": rel, "sha256": digest(p) if p.is_file() else None}


def writing_stage(key):
    return key == "stage5" or bool(re.match(r"^stage[0-4](?:\D|$)", key))


def context_hash(d, st):
    """Bind acceptance to upstream artifacts, prompts, rulings and run choices."""
    d = Path(d)
    fields = ("brand", "product", "production_route", "format_id", "layers", "ask",
              "declared_audience", "owner_script", "story", "creative_controls")
    data = {k: st.get(k) for k in fields}
    data["layers"] = st.get("layers") or {}
    paths = {"RULINGS.md"}
    if (d / "owner-controls.json").is_file():
        paths.update(("owner-controls.json", "story.md", "owner-script.md"))
    for name in ("verbatim-sources.md", "verbatim-sources.json"):
        if (d / name).is_file():
            paths.add(name)
    for key, rec in (st.get("stages") or {}).items():
        if not writing_stage(key):
            continue
        if key != "stage5" and rec.get("out"):
            paths.add(rec["out"])
        if rec.get("sent"):
            paths.add(rec["sent"])
    if (st.get("owner_script") or {}).get("file"):
        paths.add(st["owner_script"]["file"])
    if (d / "vars").is_dir():
        paths.update(str(p.relative_to(d)) for p in (d / "vars").rglob("*") if p.is_file())
    files = {}
    for rel in sorted(paths):
        p = d / rel
        try:
            p.resolve().relative_to(d.resolve())
        except ValueError:
            files[rel] = "outside-run"
            continue
        files[rel] = digest(p) if p.is_file() else None
    data["files"] = files
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def retry_budget(st, limit=2):
    """Old runs conservatively count recorded audit repeats; resume never resets usage."""
    old = st.get("writing_retry_budget")
    if isinstance(old, dict):
        return old
    audits = sum(c.get("stage") == "stage4e" for c in st.get("writing_v2_calls", []))
    return {"limit": limit, "used": min(limit, max(0, audits - 1)),
            "pending": [], "history": [], "inferred_from_legacy_calls": bool(audits)}


def joined_as_accepted(d, source, receipt):
    """The accepted brief, with its scenes joined by section tag and nothing else changed: the brief as written sits
    beside it (`<name>.before-fold.md`), is the one the receipt accepted, and the joined brief reads as it."""
    if not source.get("path"):
        return False
    now = Path(d) / source["path"]
    before = now.with_name(now.stem + ".before-fold" + now.suffix)
    if not (now.is_file() and before.is_file()) or digest(before) != receipt.get("source_sha256"):
        return False
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("writing_result_scene_shots", Path(__file__).resolve().parent / "scene_shots.py")
    _ss = _iu.module_from_spec(_sp); _sp.loader.exec_module(_ss)
    return _ss.same_as_written(now.read_text(), before.read_text())


def inspect_result(run_dir, st=None):
    """Read-only, hash-checked result for launchers, intake and filing."""
    d = Path(run_dir)
    st = st if st is not None else json.loads((d / "run.json").read_text())
    source = source_of(d, st)
    artifact = source["sha256"] is not None
    rec = (st.get("stages") or {}).get("stage5") or {}
    receipt = st.get("writing_acceptance") or {}
    blockers = []
    for key, value in (st.get("stages") or {}).items():
        if writing_stage(key) and value.get("status") in ("held", "error", "running", "stale"):
            blockers.append({"code": "stage_" + value["status"], "stage": key,
                             "detail": value.get("error") or value.get("stale_because") or value["status"]})
    if not artifact:
        blockers.append({"code": "artifact_missing", "stage": "stage5", "detail": "No brief artifact exists."})
    elif not receipt:
        blockers.append({"code": "acceptance_unverified", "stage": "stage5",
                         "detail": "Existing output has no current writing acceptance receipt; revalidate without rewriting it."})
    elif (receipt.get("source_sha256") != source["sha256"] and not joined_as_accepted(d, source, receipt)) \
            or receipt.get("context_sha256") != context_hash(d, st):
        blockers.append({"code": "acceptance_stale", "stage": "stage5",
                         "detail": "The brief or its writing inputs changed after acceptance."})
    if st.get("writing_error"):
        blockers.append({"code": "writing_error", "stage": "stage5", "detail": st["writing_error"]})
    if st.get("missed_checks"):
        blockers.append({"code": "checks_missing", "stage": "stage5", "detail": st["missed_checks"]})
    accepted = bool(artifact and rec.get("status") == "done" and receipt.get("accepted") is True and not blockers)
    return {"schema": SCHEMA, "artifact_written": artifact, "accepted": accepted,
            "state": "accepted" if accepted else "blocked" if artifact or blockers else "pending",
            "source": source, "blockers": blockers, "retry_budget": retry_budget(st),
            "notes": st.get("writing_notes") or {}}


def record_acceptance(d, st):
    """Called only after the full writing gate path succeeds, never from done flags."""
    source = source_of(d, st)
    if not source["sha256"]:
        raise ValueError("cannot accept a missing brief")
    st["writing_acceptance"] = {"accepted": True, "source_sha256": source["sha256"],
                                "context_sha256": context_hash(d, st), "checked_at": now()}


def save_result(d, st):
    result = inspect_result(d, st)
    (Path(d) / "writing-result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result
