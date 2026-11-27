"""trail — the reason travels: one decision trail per run, every stage appends, every later stage reads.

The logic layer (2026-11-18). A stage that makes a choice writes the choice AND its reason here; the next stage
gets them as one labelled block (`{decision_trail}` in a prompt, `piece.trail` in the brief, the trail in the
editor's pack), so no stage has to guess why the one before it chose what it did.

The trail is a `trail` list on the run's own run.json — no shared store, nothing new to keep in step.

    add(st, stage, decision, choice, why, by="the chain")  one row onto st["trail"]; -> the row
    note(run_dir, stage, decision, choice, why, by=...)     the same, read and written on <run_dir>/run.json
    rows(st_or_run_dir)                                     the rows (dicts only)
    block(rows)                                             labelled text, "NONE" when empty
    for_brief(key, repo=None)                               every row for one brief, in stage order

A row is a note, never a hold: nothing here stops a run. The same decision made again with the same choice and
reason is not written twice (a re-run). Brand-agnostic: nothing here names a brand, product or person.
"""
from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

STAGES = ("pick", "decide", "teardown", "writing", "production", "edit", "launch", "results", "next")


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join(_text(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return str(v)


def add(st: dict, stage, decision, choice, why, by="the chain") -> dict:
    """One row onto st["trail"]. A repeat of the stage's last row for this decision is not written again."""
    trail = st.setdefault("trail", [])
    if not isinstance(trail, list):
        trail = st["trail"] = []
    row = {"at": _now(), "stage": _text(stage), "decision": _text(decision), "choice": choice,
           "why": _text(why), "by": _text(by) or "the chain"}
    last = next((r for r in reversed(trail) if isinstance(r, dict) and r.get("stage") == row["stage"]
                 and r.get("decision") == row["decision"]), None)
    if last and last.get("choice") == choice and last.get("why") == row["why"]:
        return last
    trail.append(row)
    return row


def _read(p: Path) -> dict:
    try:
        d = json.loads(Path(p).read_text())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def note(run_dir, stage, decision, choice, why, by="the chain", file="run.json"):
    """add() on <run_dir>/<file>, written at once. -> the row, or None when it could not be written (never raises)."""
    try:
        p = Path(run_dir) / file
        st = _read(p)
        row = add(st, stage, decision, choice, why, by)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".trail-tmp")
        tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")
        tmp.replace(p)
        return row
    except Exception:  # noqa: BLE001 - a note never stops a run
        return None


def rows(src) -> list:
    """The rows of a run state (dict) or a run folder (its run.json)."""
    st = src if isinstance(src, dict) else _read(Path(src) / "run.json")
    return [r for r in (st.get("trail") or []) if isinstance(r, dict)]


def block(rows_) -> str:
    """The trail as a prompt reads it: one line per decision, grouped by stage in order. "NONE" when empty."""
    got = [r for r in (rows_ or []) if isinstance(r, dict) and (r.get("decision") or r.get("choice"))]
    if not got:
        return "NONE"
    order = {s: i for i, s in enumerate(STAGES)}
    got = sorted(enumerate(got), key=lambda t: (order.get(t[1].get("stage"), len(STAGES)), t[0]))
    lines, stage = [], None
    for _, r in got:
        if r.get("stage") != stage:
            stage = r.get("stage")
            lines.append(f"{(stage or 'earlier').upper()}:")
        why = _text(r.get("why"))
        lines.append(f"- {_text(r.get('decision'))}: {_text(r.get('choice')) or '(none)'}"
                     + (f" — because {why}" if why else "") + f" [{_text(r.get('by'))}]")
    return "\n".join(lines)


def _repo(repo=None) -> Path:
    if repo:
        return Path(repo)
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "components").is_dir() and (p / "runs").exists():
            return p
    return here.parents[3]


def _slug_of(key: str, repo: Path):
    """(brand, slug) for a brief key: 'brand/slug', a run label, or a register key ('<brand>_<product>_brief-NNNN')."""
    key = (key or "").strip()
    if "/" in key:
        b, s = key.split("/", 1)
        return b, s
    reg = _read(repo / "components" / "image-teardown" / "briefs.json").get("briefs") or {}
    e = reg.get(key) if isinstance(reg, dict) else None
    if isinstance(e, dict) and e.get("run"):
        return (key.split("_", 1)[0] if "_" in key else e.get("brand")), str(e["run"])
    return None, key


def for_brief(key, repo=None) -> list:
    """Every trail row for one brief: the teardown's working run, the writing run, its production runs and their
    edits (joined the way the brief index joins them: production `brief_from`, the edit kit's `from_run`)."""
    repo = _repo(repo)
    runs = repo / "runs"
    brand, slug = _slug_of(str(key), repo)
    dirs = [runs / "video-teardown" / "_work" / slug]
    if brand:
        dirs += [runs / "video-teardown" / brand / slug, runs / "video-writing" / brand / slug]
    else:
        dirs += sorted((runs / "video-writing").glob(f"*/{slug}"))
    prods = []
    for f in sorted((runs / "video-production").glob("*/*/run.json")):
        src = _read(f).get("brief_from") or ""
        if re.search(rf"runs/video-(?:writing|teardown)/[^/]+/{re.escape(slug)}/", src):
            prods.append(f.parent)
    dirs += prods
    names = {p.name for p in prods}
    for f in sorted((runs / "video-edit").glob("*/*/kit/edit-kit.json")):
        m = re.search(r"runs/video-production/[^/]+/([^/]+)", _read(f).get("from_run") or "")
        if m and m.group(1) in names:
            dirs.append(f.parent.parent)
    out, seen = [], set()
    for d in dirs:
        for r in rows(d):
            k = (r.get("stage"), r.get("decision"), _text(r.get("choice")), r.get("why"))
            if k not in seen:
                seen.add(k)
                out.append(r)
    return out
