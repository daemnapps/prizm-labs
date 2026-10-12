#!/usr/bin/env python3
"""
make_bank.py — make the rows of the music and SFX banks, once.

ELEMENTS.md §3 (2026-09-23): "A bank is made once and reused forever." Every
row of `tools/video-production/banks/<bank>/index.json` marked
`status: "to make"` is one call to ElevenLabs:

  * an SFX row (a cue, or a `room-tone-<setting>` bed, looped) →
    `POST /v1/sound-generation` {text, duration_seconds, prompt_influence,
    loop, model_id};
  * a music row → `POST /v1/music` {prompt, music_length_ms,
    force_instrumental, model_id}.

The url, the model id and the query come from providers.json
`direct.elevenlabs_banks` (read from the API reference, with its doc link) —
never written here. The price per minute comes from the model rows there.

    python3 machine/make_bank.py --bank sfx --dry-run         # every call, and its cost
    python3 machine/make_bank.py --bank all --dry-run
    python3 machine/make_bank.py --bank music --only music-mid-warm-104 --dry-run

**--dry-run is the only way this has been run.** A real call is a spend:
without `--dry-run` it refuses unless `--spend` is also given, and even then
it goes through the `transport` seam (tests hand it a fake). A made row gets
its audio written to `<out>/<id>.mp3` (the Drive's `Shared Assets/banks/<bank>/`
when it is mounted), `status: "made"`, `file` set to the Drive path, and
`made_at`, and the index is rewritten — nothing else in it changes.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANKS_DIR = HERE.parent / "banks"
REGISTRY = HERE / "providers.json"
MODEL_ROW = {"sfx": "elevenlabs_sound_generation", "music": "elevenlabs_music"}
DOOR = {"sfx": "sound_generation", "music": "music"}
sys.path.append(str(HERE.parents[1].parent / "components" / "brandpath"))
import drive_index as DI                                # noqa: E402
_spec = importlib.util.spec_from_file_location("vm_vp_keys", HERE / "vp_keys.py")
vp_keys = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vp_keys)


def registry() -> dict:
    return json.loads(REGISTRY.read_text())


def door(bank: str) -> dict:
    return ((registry().get("direct") or {}).get("elevenlabs_banks") or {})[DOOR[bank]]


def usd_per_minute(bank: str) -> float:
    rates = (registry()["models"].get(MODEL_ROW[bank]) or {}).get("rates") or []
    return float(next((r["usd_per_minute"] for r in rates if "usd_per_minute" in r), 0.0))


def request_of(bank: str, row: dict) -> dict:
    """The exact call for one row: {method, url, body}. Nothing is invented —
    a row with no prompt is refused by name."""
    d = door(bank)
    prompt = str(row.get("prompt") or "").strip()
    if not prompt:
        raise SystemExit(f"{bank} row {row.get('id')!r} has no 'prompt' — write what it "
                         f"should sound like into banks/{bank}/index.json first")
    url = d["url"]
    if d.get("query"):
        url += "?" + urllib.parse.urlencode(d["query"])
    if bank == "sfx":
        body = {"text": prompt, "model_id": d["model_id"],
                "prompt_influence": d.get("prompt_influence", 0.3)}
        if row.get("seconds"):
            body["duration_seconds"] = max(0.5, min(30.0, float(row["seconds"])))
        if row.get("loop"):
            body["loop"] = True
    else:
        body = {"prompt": prompt, "model_id": d["model_id"],
                "force_instrumental": bool(d.get("force_instrumental", True))}
        if row.get("seconds"):
            body["music_length_ms"] = int(max(3000, min(600000, float(row["seconds"]) * 1000)))
    return {"method": d.get("method", "POST"), "url": url, "body": body}


def cost_of(bank: str, row: dict) -> float:
    secs = float(row.get("seconds") or (30 if bank == "sfx" else 60))
    return round(secs / 60.0 * usd_per_minute(bank), 4)


def key_of() -> str | None:
    return vp_keys.key("ELEVENLABS_API_KEY")


def http_transport(method: str, url: str, body: dict, headers: dict) -> bytes:
    import time, socket
    for n in range(5):  # a dropped connection is the network, not the row (2026-09-23)
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers,
                                         method=method)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:
                raise
            if n == 4:
                raise
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError):
            if n == 4:
                raise
        time.sleep(8 * (n + 1))


def drive_bank_dir(bank: str) -> Path | None:
    m = DI.mount()
    return m / "banks" / bank if m else None


def to_make(bank: str, root=None, only: list[str] | None = None) -> tuple[dict, list[dict]]:
    p = Path(root or BANKS_DIR) / bank / "index.json"
    doc = json.loads(p.read_text())
    rows = [r for r in doc.get("rows") or [] if isinstance(r, dict)
            and str(r.get("status") or "").lower() != "made"]
    if only:
        missing = [o for o in only if o not in {r.get("id") for r in doc.get("rows") or []}]
        if missing:
            raise SystemExit(f"no {bank} row named {', '.join(missing)}")
        rows = [r for r in rows if r.get("id") in only]
    return doc, rows


def make(bank: str, root=None, only=None, dry_run=True, spend=False, out_dir=None,
         transport=None, key=None) -> dict:
    """Every row still to make in one bank: printed with its call and cost
    on --dry-run; made, written and marked on a real (approved) run."""
    doc, rows = to_make(bank, root, only)
    total = 0.0
    made = []
    for r in rows:
        req = request_of(bank, r)
        cost = cost_of(bank, r)
        total += cost
        if dry_run:
            print(json.dumps({"bank": bank, "id": r["id"], "cost_usd": cost, **req}, indent=1))
            continue
        if not spend:
            raise SystemExit("make_bank.py makes nothing without --dry-run unless --spend "
                             "is given — every row is a paid call")
        k = key or key_of()
        if not k:
            raise SystemExit("no ELEVENLABS_API_KEY (env or Keychain daemn-ELEVENLABS_API_KEY)")
        audio = (transport or http_transport)(req["method"], req["url"], req["body"],
                                              {"xi-api-key": k, "Content-Type": "application/json",
                                               "Accept": "audio/mpeg"})
        if not audio or len(audio) < 64:
            raise SystemExit(f"{bank} row {r['id']}: what came back was not audio")
        dest_dir = Path(out_dir) if out_dir else drive_bank_dir(bank)
        if dest_dir is None:
            raise SystemExit("the Drive's Shared Assets is not mounted — pass --out")
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / f"{r['id']}.mp3").write_bytes(audio)
        r["status"] = "made"
        r["file"] = f"{doc.get('drive_root') or f'Shared Assets/banks/{bank}'}/{r['id']}.mp3"
        r["made_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        made.append(r["id"])
    if made:
        p = Path(root or BANKS_DIR) / bank / "index.json"
        p.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    return {"bank": bank, "rows": [r["id"] for r in rows], "made": made,
            "cost_usd": round(total, 2),
            "seconds": sum(float(r.get("seconds") or 0) for r in rows)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bank", choices=("music", "sfx", "all"), required=True)
    ap.add_argument("--only", action="append", help="one row id; repeat for more")
    ap.add_argument("--root", help="a banks folder other than tools/video-production/banks")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--spend", action="store_true",
                    help="really make the rows — a paid call per row; approved spends only")
    ap.add_argument("--out", help="where the audio is written (default: the Drive's "
                                  "Shared Assets/banks/<bank>/)")
    a = ap.parse_args(argv)
    if not a.dry_run and not a.spend:
        print("make_bank.py runs with --dry-run (or --spend on an approved spend) — "
              "nothing was made", file=sys.stderr)
        return 2
    banks = ("sfx", "music") if a.bank == "all" else (a.bank,)
    grand = 0.0
    for b in banks:
        try:
            res = make(b, a.root, a.only if a.bank != "all" else None, dry_run=a.dry_run,
                       spend=a.spend, out_dir=a.out)
        except SystemExit as e:
            print(str(e), file=sys.stderr)
            return 2
        grand += res["cost_usd"]
        print(f"{b}: {len(res['rows'])} row(s) to make · {res['seconds']:g} s of audio · "
              f"≈ ${res['cost_usd']:.2f}" + (f" · made {len(res['made'])}" if res["made"] else ""))
    if len(banks) > 1:
        print(f"all banks: ≈ ${grand:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
