"""trail_door — production's rows on the run's decision trail (the logic layer, 2026-11-18).

Every stage of the video line appends its decisions to one record and every later stage reads it: run-kit's trail
(`run_kit.trail`: `add(st, stage, decision, choice, why, by)`, `block(rows)`, `for_brief(key)`), kept as the `trail`
list on each run's own run.json and joined per brief by the brief index. Production writes its rows here: how the ad
is made, each scene's route, what our footage was matched on, who plays a role, how many takes a clip gets.

    note(run, decision, choice, why, by="the chain")     one row on <run>/run.json, written at once
    rows(run)                                            this run's own rows
    block(run)                                           the labelled text of them ("NONE" when empty)

A row is a note, never a hold: a trail that cannot be written (no run folder yet, a dry run, the module missing on an
older checkout) is said once on stderr and the run carries on. `dry=True` returns the row without writing it.

Brand-agnostic: nothing here names a brand, a product or a person.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE = "production"


def _trail():
    """run-kit's trail module, or None when this checkout has none."""
    rk = str(HERE.parents[1] / "run-kit")
    if rk not in sys.path:
        sys.path.append(rk)
    try:
        from run_kit import trail
        return trail
    except Exception:  # noqa: BLE001 - an older checkout: the row is kept in the same shape below
        return None


def _read(p: Path) -> dict:
    try:
        d = json.loads(Path(p).read_text())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _plain(stage: str, decision: str, choice, why: str, by: str) -> dict:
    import datetime
    return {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "stage": stage,
            "decision": decision, "choice": choice, "why": why, "by": by}


def note(run, decision: str, choice, why: str, by: str = "the chain", stage: str = STAGE, dry: bool = False,
         file: str = "run.json"):
    """One decision on the run's trail. -> the row, or None when it could not be kept (said on stderr, never raised).
    The same decision made again with the same choice and reason is not written twice (a re-run of `start`)."""
    try:
        st = {"trail": []} if dry else _read(Path(run) / file)
        last = next((r for r in reversed(st.get("trail") or []) if isinstance(r, dict)
                     and r.get("stage") == stage and r.get("decision") == decision), None)
        if last and last.get("choice") == choice and last.get("why") == why:
            return last
        T = _trail()
        if T:
            row = T.add(st, stage, decision, choice, why, by)
            if not isinstance(row, dict):                 # the module appended to st["trail"] and returned nothing
                row = (st.get("trail") or [{}])[-1]
        else:                                             # an older checkout: the same row, kept the same way
            row = _plain(stage, decision, choice, why, by)
            st.setdefault("trail", []).append(row)
        if not dry:
            p = Path(run) / file
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")
        return row
    except Exception as e:  # noqa: BLE001 - a note never stops production
        print(f"NOTE the decision trail could not be written ({type(e).__name__}: {e}) — {decision}: {choice}",
              file=sys.stderr)
        return None


def rows(run, file: str = "run.json") -> list:
    return [r for r in _read(Path(run) / file).get("trail") or [] if isinstance(r, dict)]


def block(run, file: str = "run.json") -> str:
    got = rows(run, file)
    T = _trail()
    if T:
        try:
            return T.block(got)
        except Exception:  # noqa: BLE001
            pass
    return "\n".join(f"{r.get('stage')} · {r.get('decision')}: {r.get('choice')}. Why: {r.get('why')}" for r in got) or "NONE"
