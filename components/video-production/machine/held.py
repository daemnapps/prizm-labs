"""held — the switches of changes that are written and not live (the logic layer, 2026-11-18).

    on("hooks-from-the-body")      False until the owner's review turns it on (machine/held.json)
    item(id) / items()             the item's own row: what it decides, its code, its before and after

A change held for review is in the chain as code and acts on nothing while its switch is off. Turning one on is a
ruling recorded in held.json (`on`, `ruled`). An id that is not in the file is off.
"""
from __future__ import annotations

import json
from pathlib import Path

FILE = Path(__file__).resolve().parent / "held.json"


def items() -> dict:
    try:
        return json.loads(FILE.read_text()).get("items") or {}
    except (OSError, ValueError):
        return {}


def item(name: str) -> dict:
    return items().get(name) or {}


def on(name: str) -> bool:
    return item(name).get("on") is True
