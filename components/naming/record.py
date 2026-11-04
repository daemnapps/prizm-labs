#!/usr/bin/env python3
"""The creative record — one append-only file per event per asset.

    record.py made <manifest.json> [--batch-json batch.json] [--drive-ids ids.json] [--dry-run]
    record.py backfill <runs-root> [--dry-run]
    record.py human <item> --event status|note|signed --by owner [--to validated] [--text ...] [--evidence ...] [--pointer ...]

Shape: platform/data/kinds/creative-asset.json. Item id `<batch>.<slug>.a<nn>`
— the folder slug of the unit, not the 130-char name, so it fits the plane's
ITEM_ID_RE. Records land under HOME (lab/owner/creative-ledger/records/ until
the team rules on lab writes to platform/data/records/); same envelope either way:
{schema, kind, reviewer, item, verdict{event,...}, notes, created, via}.

Rules carried: a `made` record is written by the machine and never reads as
approval; `status`/`note`/`signed` are written by a person and carry that
person's name; `unknown` is written, never blank; `sub` is null when nobody
declared it. Nothing here stores money.
"""
import argparse, datetime as dt, json, re, secrets, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import names as N

WS  = N.WS                      # names.py's locator: run-kit paths.repo()
LAB = WS / "lab" / "owner"      # a person's runs and swipes stay in lab
KIND = "creative-asset"
HOME = WS / "lab/owner/creative-ledger/records" / KIND
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
UUID = re.compile(r"<<<([0-9a-f-]{36})>>>")


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def item_id(batch, slug, asset):
    i = f"{batch}.{N.slug(slug) if '-' not in slug else slug}.{asset}"
    if not ITEM_ID_RE.match(i):
        raise SystemExit(f"item id {i!r} does not fit the plane")
    return i


def write(item, reviewer, verdict, notes="", via="record.py", dry=False):
    rec = {"schema": 1, "kind": KIND, "reviewer": reviewer, "item": item,
           "verdict": verdict, "notes": notes, "created": now(), "via": via}
    stamp = rec["created"].replace("-", "").replace(":", "")
    p = HOME / f"{stamp}--{reviewer}--{item}--{verdict['event']}.json"
    if dry:
        print(f"  would write {p.name}")
        return p
    HOME.mkdir(parents=True, exist_ok=True)
    body = json.dumps(rec, indent=1, ensure_ascii=False) + "\n"
    # Stamped to the second, so two records in one second share a name.
    # Create exclusively and, on a clash, add a short nonce to the stamp —
    # append-only means the second record never replaces the first.
    for _ in range(8):
        try:
            with open(p, "x") as fh:
                fh.write(body)
            return p
        except FileExistsError:
            p = HOME / f"{stamp}-{secrets.token_hex(2)}--{reviewer}--{item}--{verdict['event']}.json"
    raise SystemExit(f"could not find a free record name for {item} at {stamp}")


def prompt_for(unit_dir, slug):
    """The prompt kept beside the run, if one was kept."""
    for c in (unit_dir / "prompt.txt", unit_dir.parent.parent / "prompts" / f"{slug}.txt",
              unit_dir.parent.parent / "prompts" / f"{slug}.md"):
        if c.is_file():
            return {"text": c.read_text().strip(), "path": str(c.resolve().relative_to(WS))}
    return "unknown"


def made_from_manifest(manifest, batch_json=None, drive_ids=None, dry=False, reviewer="image-production", ocr=None, only=None):
    m = Path(manifest).resolve(); d = json.loads(m.read_text())
    unit = m.parent; slug = unit.name
    spec = {}
    if batch_json and Path(batch_json).is_file():
        b = json.loads(Path(batch_json).read_text())
        spec = next((a for a in b.get("ads", []) if a.get("slug") == slug), {})
        offer = b.get("offer", {})
    else:
        offer = {}
    prompt = prompt_for(unit, slug)
    refs = [{"role": "element", "ref": u} for u in UUID.findall(prompt["text"])] if isinstance(prompt, dict) else "unknown"
    out = []
    for row in d.get("ads", []):
        if "name" not in row:
            print(f"  ! {m.relative_to(WS)}: a row with no name — an older manifest shape, skipped")
            continue
        if only and row["name"] not in only:
            continue
        f = N.parse(row["name"])
        if not f:
            print(f"  ! {row['name']} does not parse — skipped"); continue
        asset = f"a{f['asset_n']:02d}" if f.get("asset_n") else f["asset"]   # item ids stay `a<nn>`
        lane = spec.get("lane") or d.get("lane") or f["avatar"]
        qc = row.get("qc") or {"status": "pass", "checks_run": "unknown", "fails": [], "judge_model": "unknown",
                               "coverage": "delivered before the record existed — passed the gate of its day"}
        v = {"event": "made", "name": row["name"], "ad_name": row["ad_name"],
             "fields": {**{k: f[k] for k in N.AD_FIELDS}, "lane": lane, "sub": N.sub_key(spec.get("sub") or row.get("sub"))},
             "template": spec.get("template", "prompted"),
             "copy": row.get("copy") or spec.get("copy")
                     or ({"slots": ocr[row["file"]], "provenance": "ocr"} if ocr and ocr.get(row["file"]) else {"slots": {}, "provenance": "unknown"}),
             "hook": spec.get("hook") or row.get("hook") or "unknown",
             "offer": row.get("offer") or ({"id": offer.get("id", "unknown"), "bar_text": offer.get("bar_text", "unknown")} if offer else {"id": "unknown", "bar_text": "unknown"}),
             "prompt": prompt, "model": row.get("model") or spec.get("model") or "unknown",
             "references": refs,
             "location": {"drive_id": ((drive_ids or {}).get(row["file"]) or {}).get("id") if isinstance((drive_ids or {}).get(row["file"]), dict) else (drive_ids or {}).get(row["file"]), "drive_path": ((drive_ids or {}).get(row["file"]) or {}).get("path", "unknown") if isinstance((drive_ids or {}).get(row["file"]), dict) else row.get("drive_path", "unknown"), "durable_url": None},
             "qc": qc}
        out.append(write(item_id(f["batch"], slug, asset), reviewer, v, dry=dry))
    return out


def human(item, event, by, dry=False, **kw):
    if event not in ("status", "note", "signed"):
        raise SystemExit("a person writes status, note or signed — `made` is the machine's")
    v = {"event": event, **{k: x for k, x in kw.items() if x is not None}}
    need = {"status": ("to", "evidence"), "note": ("text",), "signed": ("pointer",)}[event]
    for k in need:
        if k not in v:
            raise SystemExit(f"{event} needs --{k}")
    if event == "status":
        # The `to` words come from the kind manifest on every call, never
        # copied here, so the two cannot drift.
        kind = json.loads((WS / "platform/data/kinds" / f"{KIND}.json").read_text())
        ok = next(f["values"] for f in kind["verdict_fields"] if f["key"] == "to")
        if v["to"] not in ok:
            raise SystemExit(f"status --to must be one of {ok}, not {v['to']!r}")
    return write(item, by, v, via="record.py human", dry=dry)


def main():
    a = argparse.ArgumentParser(); s = a.add_subparsers(dest="cmd", required=True)
    m = s.add_parser("made"); m.add_argument("manifest"); m.add_argument("--batch-json"); m.add_argument("--drive-ids"); m.add_argument("--ocr"); m.add_argument("--dry-run", action="store_true")
    b = s.add_parser("backfill"); b.add_argument("root"); b.add_argument("--drive-ids"); b.add_argument("--ocr"); b.add_argument("--dry-run", action="store_true")
    h = s.add_parser("human"); h.add_argument("item"); h.add_argument("--event", required=True); h.add_argument("--by", required=True)
    for k in ("to", "text", "evidence", "pointer"): h.add_argument(f"--{k}")
    h.add_argument("--dry-run", action="store_true")
    o = a.parse_args()
    ids = json.loads(Path(o.drive_ids).read_text()) if getattr(o, "drive_ids", None) else None
    ocr = json.loads(Path(o.ocr).read_text()) if getattr(o, "ocr", None) else None
    if o.cmd == "made":
        n = made_from_manifest(o.manifest, o.batch_json, ids, o.dry_run, ocr=ocr); print(f"{len(n)} made records")
    elif o.cmd == "backfill":
        n = 0
        for mf in sorted(Path(o.root).rglob("manifest.json")):
            bj = next((p for p in [mf.parent.parent.parent / "batch.json", mf.parent.parent / "batch.json"] if p.is_file()), None)
            n += len(made_from_manifest(mf, bj, ids, o.dry_run, ocr=ocr))
        print(f"{n} made records {'planned' if o.dry_run else 'written'}")
    else:
        p = human(o.item, o.event, o.by, o.dry_run, to=o.to, text=o.text, evidence=o.evidence, pointer=o.pointer); print(p.name)


if __name__ == "__main__":
    main()
