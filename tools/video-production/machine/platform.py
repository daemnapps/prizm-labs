#!/usr/bin/env python3
"""
platform.py — which provider this session submits through, and what a batch
will cost there, BEFORE anything is submitted.

    python3 platform.py [--provider P] [--batch batch.json] [--yes] [--json]

Exit 0 proceed · 1 declined · 2 refusals · 3 bad input.

Every provider and model slug lives in providers.json, never here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROVIDERS_FILE = HERE / "providers.json"


def registry() -> dict:
    return json.loads(PROVIDERS_FILE.read_text())


def _vault_key(name: str) -> bool:
    # A teammate's clone has no vault module and no Keychain entry; both are
    # simply "not found", never an error.
    try:
        import daemn_keys
        return bool(daemn_keys.key(name))
    except Exception:
        return False


def _detect(conditions: dict) -> tuple[bool, list[str]]:
    why = []
    for cond, want in conditions.items():
        if cond == "claudecode":
            if bool(os.environ.get("CLAUDECODE")) != bool(want):
                return False, [f"CLAUDECODE {'not set' if want else 'set'}"]
            why.append("CLAUDECODE set" if want else "CLAUDECODE not set")
        elif cond == "key_env":
            if os.environ.get(want):
                why.append(f"{want} in env")
            elif _vault_key(want):
                why.append(f"{want} in vault")
            else:
                return False, [f"{want} not found"]
        else:
            return False, [f"unknown detect condition {cond!r}"]
    return True, why or ["no conditions — the fallback"]


def resolve_provider(args_provider: str | None = None) -> tuple[str, dict, list[str]]:
    """(name, provider row, why) — --provider > AI_VIDEO_PROVIDER > auto."""
    reg = registry()
    forced = args_provider or os.environ.get("AI_VIDEO_PROVIDER")
    if forced:
        if forced not in reg["providers"]:
            raise SystemExit(
                f"unknown provider {forced!r}; providers.json offers: "
                + ", ".join(reg["providers"]))
        src = "--provider" if args_provider else "AI_VIDEO_PROVIDER"
        return forced, reg["providers"][forced], [f"forced by {src}"]
    notes = []
    for name, row in reg["providers"].items():
        ok, why = _detect(row.get("detect", {}))
        if ok:
            return name, row, why + notes
        notes.append(f"{name}: " + "; ".join(why))
    raise SystemExit("no provider matched and none is a fallback — "
                     "give one provider in providers.json an empty detect")


# ------------------------------------------------------------------ plan

def item_model(item: dict) -> str | None:
    return item.get("model") or (item.get("params") or {}).get("model")


def item_kind(item: dict, reg: dict) -> str | None:
    if item.get("kind"):
        return item["kind"]
    m = reg["models"].get(item_model(item) or "")
    return m["kind"] if m else None


def resolve_model(item: dict, provider: dict, reg: dict) -> tuple[str | None, str | None]:
    """(model slug, refusal). The item's own model wins; else the provider's
    station default for the item's kind."""
    slug = item_model(item)
    if not slug:
        kind = item.get("kind")
        station = reg["station_of_kind"].get(kind or "")
        if not station:
            return None, "no model and no kind — nothing to resolve"
        slug = provider["stations"].get(station)
        if not slug:
            return None, f"provider offers no default for station {station!r}; name a model"
    m = reg["models"].get(slug)
    if not m:
        return slug, f"model {slug!r} is not in providers.json"
    # most models belong to one provider family; a pseudo-model called
    # directly on its own API (ElevenLabs voice, called the same way from
    # every house) instead lists every family allowed to use it in "used_by".
    if m["provider"] != provider["family"] and provider["family"] not in (m.get("used_by") or []):
        return slug, f"model {slug!r} is not offered by this provider"
    if m.get("retired"):
        return slug, f"model {slug!r} is retired: {m['retired']}"
    return slug, None


def pick_rate(model: dict, tier: str | None = None, resolution: str | None = None) -> dict | None:
    """The latest reading that matches; a null resolution on a reading matches any."""
    hits = [r for r in model.get("rates", [])
            if (not tier or r.get("tier") == tier)
            and (not resolution or r.get("resolution") in (None, resolution))]
    if not hits:
        return None
    return max(hits, key=lambda r: (r.get("resolution") == resolution, r.get("read", "")))


def estimate(model: dict, seconds: float, reg: dict, tier=None, resolution=None) -> dict:
    rate = pick_rate(model, tier, resolution)
    out = {"rate": rate, "credits": None, "usd": None}
    if not rate:
        return out
    per_dollar = reg["credits_per_dollar"].get(model["provider"])
    if "credits_per_second" in rate:
        out["credits"] = round(rate["credits_per_second"] * seconds, 2)
    elif "credits_per_job" in rate:
        out["credits"] = rate["credits_per_job"]
    if out["credits"] is not None and per_dollar:
        out["usd"] = round(out["credits"] / per_dollar, 3)
    elif "usd_per_second" in rate:
        out["usd"] = round(rate["usd_per_second"] * seconds, 3)
    elif "usd_per_job" in rate:
        out["usd"] = rate["usd_per_job"]
    return out


def rate_label(rate: dict | None) -> str:
    if not rate:
        return "no rate on file"
    for k in ("credits_per_second", "credits_per_job", "usd_per_second", "usd_per_job"):
        if k in rate:
            unit = {"credits_per_second": "cr/s", "credits_per_job": "cr/job",
                    "usd_per_second": "$/s", "usd_per_job": "$/job"}[k]
            return f"{rate[k]} {unit} ({rate.get('read', '?')})"
    return "?"


def machine_door(item: dict, reg: dict, forced: bool = False) -> dict | None:
    """The direct door the machine hand will call for this item, or None
    when the item goes to the editor house. Mirrors run.py's split: a
    station whose door says hand=machine is the machine's — unless Damon
    forced a house with --provider, which takes motion/talking back."""
    kind = item.get("kind") or item_kind(item, reg)
    st = reg["station_of_kind"].get(kind or "")
    door = (reg.get("doors") or {}).get(st or "", {})
    if door.get("hand") != "machine":
        return None
    if forced and str(door.get("primary", "")).startswith("direct:") and st in ("motion", "talking"):
        return None
    if st == "motion" and any(m.get("role") == "audio" for m in item.get("medias") or []):
        door = (reg.get("doors") or {}).get("talking", door)
        st = "talking"
    return {"station": st, **door}


def plan(batch: list[dict], provider: dict, reg: dict | None = None, forced: bool = False) -> dict:
    reg = reg or registry()
    rows, refusals = [], []
    tot_cr = tot_usd = 0.0
    for item in batch:
        iid = item.get("id", "?")
        door = machine_door(item, reg, forced)
        if door:
            # the machine hand's own door — shown as what will actually be
            # called, priced off the registry when the model has a rate
            params = item.get("params") or {}
            secs = float(params.get("duration") or item.get("seconds") or 0)
            res = params.get("resolution")
            m = reg["models"].get(door.get("model") or "") or {}
            est = estimate(m, secs, reg, None, res) if m else {"credits": None, "usd": None, "rate": None}
            tot_cr += est["credits"] or 0
            tot_usd += est["usd"] or 0
            rows.append({"id": iid, "station": door["station"],
                         "model": f"{door.get('primary')} → {door.get('model')}",
                         "tier": "direct", "resolution": res or (est["rate"] or {}).get("resolution") or "-",
                         "seconds": secs, "rate": rate_label(est["rate"]),
                         "ceiling": "machine hand — " + (door.get("recipe") or "one call"),
                         "credits": est["credits"], "usd": est["usd"]})
            continue
        slug, refusal = resolve_model(item, provider, reg)
        if refusal:
            refusals.append(f"{iid}: {refusal}")
            rows.append({"id": iid, "station": "?", "model": slug or "?", "refusal": refusal})
            continue
        m = reg["models"][slug]
        params = item.get("params") or {}
        secs = float(params.get("duration") or item.get("seconds") or 0)
        tier, res = params.get("tier") or item.get("tier"), params.get("resolution")
        est = estimate(m, secs, reg, tier, res)
        tot_cr += est["credits"] or 0
        tot_usd += est["usd"] or 0
        rows.append({"id": iid, "station": m["station"], "model": slug,
                     "tier": tier or (est["rate"] or {}).get("tier") or "-",
                     "resolution": res or (est["rate"] or {}).get("resolution") or "-",
                     "seconds": secs, "rate": rate_label(est["rate"]),
                     "ceiling": (m.get("ceilings") or ["-"])[0],
                     "credits": est["credits"], "usd": est["usd"]})
    return {"rows": rows, "refusals": refusals,
            "total_credits": round(tot_cr, 2), "total_usd": round(tot_usd, 3),
            "count": len(batch), "batch_max": provider.get("batch_max")}


def print_plan(p: dict) -> None:
    head = ("id", "station", "model", "tier/res", "seconds", "rate", "est cr", "est $", "ceiling")
    print(" · ".join(head))
    for r in p["rows"]:
        if r.get("refusal"):
            print(f"{r['id']} · REFUSED · {r['model']} · {r['refusal']}")
            continue
        cr = "?" if r["credits"] is None else r["credits"]
        usd = "?" if r["usd"] is None else f"{r['usd']:.3f}"
        print(f"{r['id']} · {r['station']} · {r['model']} · {r['tier']}/{r['resolution']} · "
              f"{r['seconds']:g}s · {r['rate']} · {cr} · {usd} · {r['ceiling']}")
    print(f"TOTAL · {p['count']} item(s) · {p['total_credits']} cr · ${p['total_usd']:.3f}"
          + ("  (items with no rate on file are not counted)"
             if any(r.get('credits') is None and not r.get('refusal') for r in p['rows']) else ""))
    if p["batch_max"] and p["count"] > p["batch_max"]:
        print(f"OVER CAP · {p['count']} items against batch_max {p['batch_max']}")


# --------------------------------------------------------------- confirm

def confirm(provider: dict, yes: bool = False) -> bool:
    if not (provider.get("confirm") or os.environ.get("AI_VIDEO_CONFIRM") == "1"):
        return True
    if yes:
        return True
    if not sys.stdin.isatty():
        print("confirmation needed and stdin is not a terminal — treating as NO (pass --yes to proceed)")
        return False
    try:
        answer = input("Proceed with these models? [y/N] ").strip().lower()
    except EOFError:
        answer = ""
    return answer in ("y", "yes")


def load_batch(path: Path) -> list[dict]:
    d = json.loads(path.read_text())
    if isinstance(d, dict):
        d = d.get("items", [])
    if not isinstance(d, list):
        raise SystemExit(f"{path}: expected a list of items or {{\"items\": [...]}}")
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider")
    ap.add_argument("--batch")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        name, prov, why = resolve_provider(a.provider)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 3
    out = {"provider": name, "why": why, "confirm": bool(prov.get("confirm"))}
    p = None
    if a.batch:
        try:
            batch = load_batch(Path(a.batch))
        except (OSError, ValueError, SystemExit) as e:
            print(f"bad batch: {e}", file=sys.stderr)
            return 3
        p = plan(batch, prov, forced=bool(a.provider))
        out["plan"] = p
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        print(f"provider: {name} — {'; '.join(why)}")
        if p:
            print_plan(p)
    if p and p["refusals"]:
        for r in p["refusals"]:
            print(f"REFUSED {r}", file=sys.stderr)
        return 2
    if not confirm(prov, a.yes):
        print("declined")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
