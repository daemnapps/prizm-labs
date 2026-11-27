"""Read-only shared workforce/brief view. JSON sources stay authoritative.

Public surface: enrich(queue_view, root=None, legacy_offset_minutes=0).
No writes, network, secrets, profile preferences or usage estimates.
"""
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _read(path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text())


def _time(value, offset):
    if not value:
        return None
    try:
        value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return value if value.tzinfo else value.replace(tzinfo=timezone(timedelta(minutes=offset)))
    except ValueError:
        return None


def enrich(queue_view, root=None, legacy_offset_minutes=0, now=None, development_view=None, role_view=None):
    """Join identities, route owners, assignments and current delivery round.

    Caller supplies offset for legacy queue timestamps without timezone. Explicit
    timestamps retain their own offset. Never infer a completed delivery from files.
    """
    if root is None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run-kit"))
        from run_kit import paths
        root = paths.repo()
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    result = copy.deepcopy(queue_view)
    people = {}
    for path in sorted((root / "team/people").glob("*/identity.json")):
        identity = _read(path, {})
        key = identity.get("person")
        if key:
            people[key] = {"id": key, "name": key.replace("-", " ").title(), "roles": [],
                           "identity_source": path.relative_to(root).as_posix(),
                           "claude_usage": {"state": "not-connected", "weekly_percent": None, "tokens": None}}
    roles = _read(root / "components/image-edit/delivery.json", {}).get("roles", {})
    for role, config in roles.items():
        person = str(config.get("filled_by") or "").casefold()
        if person in people:
            people[person]["roles"].append(role)
            people[person]["name"] = config["filled_by"]
    handoffs = {}
    for path in (root / "runs/handoffs").glob("*/*/*/delivery-state.json"):
        handoffs.setdefault(path.parent.name, []).append(path)
    errors = result.setdefault("errors", [])
    for group in ("items", "backlog", "removed"):
        for row in result.get(group, []):
            pack = row.get("pack") or {}
            role = pack.get("role")
            matches = handoffs.get(row.get("id"), [])
            if role:
                matches = [p for p in matches if p.parents[2].name == role]
            state, folder = {}, None
            if len(matches) == 1:
                folder = matches[0].parent
                role = folder.parents[1].name
                try:
                    state = _read(matches[0], {})
                except (ValueError, OSError) as exc:
                    errors.append("Delivery state unreadable: " + row.get("id", "") + ": " + str(exc))
            elif len(matches) > 1:
                errors.append("Ambiguous delivery role: " + row.get("id", ""))
            person = str(row.get("who") or "").casefold()
            history = row.get("history") or []
            entered = next((h.get("at") for h in history if h.get("stage") == "making"), None)
            delivery = state.get("state")
            completed = state.get("updated_at") if delivery == "ready-for-review" else None
            def elapsed(start, end=None):
                first = _time(start, legacy_offset_minutes)
                last = _time(end, legacy_offset_minutes) if end else now
                return round(max(0, (last-first).total_seconds()) / 3600, 2) if first and last else None
            row["workflow"] = {
                "person_id": person if person in people else None,
                "assigned_to": row.get("who") or None,
                "role": role,
                "role_default": roles.get(role, {}).get("filled_by"),
                "assignment_state": "assigned" if row.get("who") else "unassigned",
                "delivery_state": delivery,
                "revision_id": state.get("revision_id"),
                "revision_round": state.get("round"),
                "delivery_source": (folder / "delivery-state.json").relative_to(root).as_posix() if folder else None,
                "queued_at": row.get("created"),
                "maker_queue_at": entered,
                "maker_elapsed_hours": elapsed(entered, completed),
                "queue_elapsed_hours": elapsed(row.get("created"), completed),
                "revision_elapsed_hours": elapsed(state.get("updated_at")) if delivery == "back-for-revision" else None,
                "completed_at": completed,
                "active_work_hours": None,
                "tokens": None,
                "usage_state": "not-connected",
                "timing_basis": "Queue history; elapsed time, not active work. Completion requires current delivery state.",
            }
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import usage as brief_usage
    import importlib
    importlib.reload(brief_usage)
    usage_context = brief_usage.load_context(root)
    for group in ("items", "backlog", "removed"):
        for row in result.get(group, []):
            meter = brief_usage.summarize(row["id"], root, context=usage_context)
            row["workflow"].update(tokens=meter["tokens"], usage_state=meter["state"], usage=meter)
    allocation = _read(root / "team/work-allocation.json", {})
    for person, details in allocation.get("people", {}).items():
        if person in people:
            people[person]["capabilities"] = details.get("capabilities", [])
            people[person]["accounts"] = details.get("accounts", [])
    result["workforce"] = list(people.values())
    result["workflow_sources"] = {
        "identities": "team/people/<person>/identity.json",
        "roles": "components/image-edit/delivery.json",
        "assignments": "runs/queue/<brand>/<type>/<stage>/<brief-key>.json",
        "delivery": "runs/handoffs/<role>/<brand>/<brief-key>/delivery-state.json",
        "logic": "components/briefs/workload.py",
    }
    spec = importlib.util.spec_from_file_location("brief_resource_queues", Path(__file__).with_name("resources.py"))
    resource_queues = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resource_queues)
    result["resource_queues"] = resource_queues.project(result, development_view if development_view is not None else {"error": "Development queue not loaded by this reader"}, now=now, role_view=role_view if role_view is not None else resource_queues.role_handoffs(root))
    return result
