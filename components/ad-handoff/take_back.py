#!/usr/bin/env python3
"""take_back — a hand-off's returned/ folder and live ids, indexed and recorded.

    TB = <this file, loaded by path>
    TB.take_back(role, brand, name, staging, ledger)   # -> the returned/ index

Reads `<staging>/<role>/<brand>/<name>/returned/`, joins every file to its
brief and asset ids (components/naming), prefixes every live id the platform
gave (`live_meta_<id>`, `live_klaviyo_<id>`, `live_sms_<id>`), and writes
returned/index.json, the manifest's `returned` block and one `returned` row
in the ledger. A missing hand-off raises `Refused` (`.reasons`).

Moved here from the team notes (SI-143
(take-back home)), verbatim but for the ledger row's `via`. Callers load this
file by path: email-production klaviyo_upload.py, meta-upload upload.py,
video-edit handoff_run.py, and the lab hand-off tool.

Naming is found by this file's own location, never by the workspace locator:
a caller may point AI_WORKSPACE at a temp tree. Nothing else happens at
import time — no Drive, no brand folders, no brief register.
"""
import json, re, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "naming"))
import names as N  # noqa: E402

SCHEMA = "handoff/1"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Refused(Exception):
    """The hand-off is refused; `.reasons` names every missing thing."""

    def __init__(self, reasons):
        super().__init__("; ".join(reasons))
        self.reasons = list(reasons)


# ---- ledger -------------------------------------------------------------
def ledger_write(path, event, manifest=None, role=None, brand=None, reasons=None, extra=None):
    """One append-only line per event. Same envelope as the creative record
    (schema, kind, item, verdict, created, via); the item is the hand-off name."""
    row = {
        "schema": SCHEMA, "kind": "handoff",
        "item": (manifest or {}).get("name"),
        "role": role or (manifest or {}).get("role"),
        "brand": brand or (manifest or {}).get("brand"),
        "verdict": {"event": event},
        "briefs": [b["id"] for b in (manifest or {}).get("briefs", [])],
        "ids": (manifest or {}).get("ids"),
        "target": ((manifest or {}).get("drive") or {}).get("target"),
        "created": now(), "via": "components/ad-handoff/take_back.py",
    }
    if reasons:
        row["verdict"]["reasons"] = reasons
    if extra:
        row.update(extra)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


# ---- take back ----------------------------------------------------------
LIVE_PREFIX = {"meta": "live_meta_", "klaviyo": "live_klaviyo_", "sms": "live_sms_"}


def take_back(role, brand, name, staging, ledger):
    root = Path(staging) / role / brand / name
    mf = root / "manifest.json"
    if not mf.is_file():
        raise Refused([f"no hand-off named {name} under {Path(staging) / role / brand}"])
    manifest = json.loads(mf.read_text())
    ret = root / "returned"
    files, live = [], []
    for f in sorted(ret.rglob("*")):
        if not f.is_file() or f.name in ("README.md", "index.json"):
            continue
        parsed = N.parse_any(f.name)
        stem = f.stem
        bid = (parsed or {}).get("brief_id")
        if not bid:
            m = re.match(r"^(brief-\d{4}|p\d{3})[_-]", stem)
            bid = N.brief_id(m.group(1)) if m else None
        aid = (parsed or {}).get("asset_id")
        if not aid:
            m = re.search(r"(asset-\d{2}|a\d{2})(?=[._-]|$)", stem)
            aid = N.norm_asset(m.group(1)) if m else None
        files.append({"file": str(f.relative_to(ret)), "brief_id": bid, "asset_id": aid,
                      "ad_name": (parsed or {}).get("ad_name"), "bytes": f.stat().st_size})
    lf = ret / "live-ids.json"
    if lf.is_file():
        rows = json.loads(lf.read_text())
        rows = rows if isinstance(rows, list) else [rows]
        for r in rows:
            ch = str(r.get("channel") or "").lower()
            pid = r.get("platform_id")
            live.append({**r, "live_id": f"{LIVE_PREFIX.get(ch, 'live_' + ch + '_')}{pid}" if pid else None})
    index = {"schema": SCHEMA, "handoff": name, "role": role, "brand": brand, "files": files, "live_ids": live,
             "taken_back": now(), "note": "nothing here is published by this step; live ids are recorded as the platform gave them"}
    (ret / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    manifest["returned"]["received"] = [f["file"] for f in files]
    manifest["returned"]["live_ids"] = live
    manifest["returned"]["taken_back"] = index["taken_back"]
    mf.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    ledger_write(ledger, "returned", manifest, extra={"files": len(files), "live_ids": [l["live_id"] for l in live if l.get("live_id")]})
    return index
