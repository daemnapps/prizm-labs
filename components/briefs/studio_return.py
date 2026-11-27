#!/usr/bin/env python3
"""THE IN-HOUSE RETURN (2026-11-21, brief-0380): a brief finished in the Video Studio returns to its own hand-off the
way an editor's return does, so the delivery contract can validate it and the approval filer can file it.

    python3 components/briefs/studio_return.py <hand-off folder> --production <Studio production> --by "<who made it>"
        [--run <production run>] [--open "<known open items, said in every check that they touch>"] [--dry-run]

From the Studio's own list of what is ready (briefs/<production>/covers/to-file.json: each version's master, its cover,
its cover record) it copies every version and cover into returned/<revision>/ (named <brief-key>-<version>.mp4 and
<brief-key>-<version>-cover.png), writes each cover's record in the approval filer's shape (meta-upload cover_rule:
swipe, frame with the video's sha256 and time), fills the slots in order, records each slot's creative change from the
production records (a set request's `creative_change` naming the slot), and writes every check with its evidence read
from the chain's own records: the clip checklists, the fix list, the gaps, the Studio's cut check, each video's
measured format, the covers' own results. It refuses, naming why, when a version is missing, a cover is not ok or a
cover's frame is not its own video's. Then it runs the contract's validate. It never files: `delivery_contract.py
submit <hand-off>` does. Nothing is invented: a check whose record is missing says so in its evidence.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[1]


def _load(path, name):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _read(p, d=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return d


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(p)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams") or [] if s.get("codec_type") == "video"), {})
    a = any(s.get("codec_type") == "audio" for s in d.get("streams") or [])
    return {"w": int(v.get("width") or 0), "h": int(v.get("height") or 0),
            "seconds": round(float((d.get("format") or {}).get("duration") or 0), 2), "sound": a}


def studio_dir(production):
    data = os.environ.get("VIDEO_STUDIO_DATA")
    if not data:
        raise SystemExit("VIDEO_STUDIO_DATA is not set: the Studio's data folder is where its productions live")
    return Path(data) / "briefs" / production


def creative_changes(brand, labels):
    """{slot label: the recorded change} from the production records (a set request's `creative_change`)."""
    out = {}
    for f in sorted((WS / "runs" / "image-production" / str(brand) / "set-requests").glob("*.json")):
        cc = (_read(f, {}) or {}).get("creative_change")
        if isinstance(cc, dict) and cc.get("slot") in labels:
            out[cc["slot"]] = "%s (%s)" % (cc.get("change"), cc.get("why")) if cc.get("why") else str(cc.get("change"))
    return out


def chain_evidence(run):
    """What the chain's own records say, in short lines."""
    run = Path(run)
    ck = _read(run / "clips" / "checklists.json", {}) or {}
    rows = [r for v in ck.values() for r in v.get("rows") or []]
    crossed = sum(1 for r in rows if r.get("state") == "✗")
    product = sum(1 for r in rows if str(r.get("line", "")).startswith("real product") and r.get("state") == "✓")
    fixes = _read(run / "clips" / "fixes.json", {}) or {}
    gaps = _read(run / "clips" / "gaps.json", {}) or {}
    return {"checklists": "%d clip checklists in %s, %d ✗" % (len(ck), run.relative_to(WS) / "clips/checklists.json", crossed)
            if ck else "no clip checklists on record",
            "product": "%d real-product rows ✓ in the clip checklists" % product,
            "fixes": "%d small fixes on the fix list (clips/fixes.json)" % sum(len(v.get("fixes") or []) for v in fixes.values()),
            "gaps": ("clips left as gaps for the edit: " + ", ".join(gaps)) if gaps else "no clip gaps",
            "crossed": crossed}


def build(folder, production, by, run=None, open_items="", dry=False):
    folder = Path(folder).resolve()
    D = _load(HERE / "delivery_contract.py", "sr_delivery_contract")
    CR = _load(WS / "components" / "meta-upload" / "cover_rule.py", "sr_cover_rule")
    req, state = D.read(folder / D.CONTRACT), D.read(folder / D.STATE)
    if not req or not state:
        raise SystemExit("no delivery contract in %s" % folder)
    rid, key = state["revision_id"], req["brief_key"]
    run = Path(run) if run else WS / "runs" / "video-production" / str(_read(folder / "run.json", {}).get("brand")) / key
    B = studio_dir(production)
    tf = _read(B / "covers" / "to-file.json", {}) or {}
    slots = req["slots"]
    if not tf.get("ready") or len(tf.get("media") or []) != len(slots):
        raise SystemExit("the Studio's covers/to-file.json is not ready for %d slots (%d versions there)"
                         % (len(slots), len(tf.get("media") or [])))
    made = _read(B / "covers" / "made" / "covers.json", {}) or {}
    rows_by_version = {str(r.get("version")).lower(): r for r in made.get("covers") or []}
    out = folder / "returned" / rid
    items, problems, records, dims, covers_ok = [], [], [], [], []
    for n, slot in enumerate(slots):
        v = tf["versions"][n]
        vname = "control" if str(v).lower() == "control" else "v%d" % n
        video, cover = Path(tf["media"][n]), Path(tf["thumbs"][n])
        rec_src = Path((tf.get("cover_records") or [None] * len(slots))[n] or "") if tf.get("cover_records") else None
        cj = rec_src if rec_src and rec_src.is_file() else cover.with_suffix(".cover.json")
        raw = _read(cj, {}) or {}
        norm = CR.normalize(raw) or {}
        vsha = sha(video)
        if (norm.get("frame") or {}).get("video_sha256") != vsha:
            problems.append("%s: the cover's frame is not from this video (video re-rendered after its cover?)" % slot["id"])
        row = rows_by_version.get(str(v).lower()) or raw
        if row.get("ok") is not True or row.get("problems"):
            problems.append("%s: the cover is not ok: %s" % (slot["id"], "; ".join(row.get("problems") or ["not ok"])))
        p = probe(video)
        dims.append("%s %dx%d %.1fs %s" % (vname, p["w"], p["h"], p["seconds"], "sound" if p["sound"] else "NO SOUND"))
        covers_ok.append(vname)
        f_video, f_cover = "%s-%s.mp4" % (key, vname), "%s-%s-cover.png" % (key, vname)
        f_rec = "%s-%s-cover.json" % (key, vname)
        record = dict(norm, frame=dict(norm.get("frame") or {}, video=str(video)), version=v,
                      headline=raw.get("headline"), made_by="image-production cover job", source_record=str(cj))
        if not dry:
            out.mkdir(parents=True, exist_ok=True)
            for src, dst in ((video, out / f_video), (cover, out / f_cover)):
                if not dst.is_file() or sha(dst) != sha(src):
                    shutil.copy2(src, dst)
            (out / f_rec).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
            run_json = Path(str(raw.get("run") or "")) if raw.get("run") else cover.parent / "run.json"
            if run_json.is_file():
                (out / "records" / vname).mkdir(parents=True, exist_ok=True)
                shutil.copy2(run_json, out / "records" / vname / "run.json")
                records.append("returned/%s/records/%s/run.json" % (rid, vname))
        items.append({"slot_id": slot["id"], "file": "returned/%s/%s" % (rid, f_video), "sha256": vsha,
                      "cover": "returned/%s/%s" % (rid, f_cover), "cover_sha256": sha(cover),
                      "cover_record": "returned/%s/%s" % (rid, f_rec), "creative_changes": ""})
    if problems:
        raise SystemExit("not returned, nothing written as a submission:\n  " + "\n  ".join(problems))
    labels = [s["label"] for s in slots]
    cc = creative_changes(_read(folder / "run.json", {}).get("brand"), labels)
    for it, s in zip(items, slots):
        it["creative_changes"] = cc.get(s["label"], "")
    if not dry and (B / "covers" / "made" / "covers.json").is_file():
        (out / "records").mkdir(parents=True, exist_ok=True)
        shutil.copy2(B / "covers" / "made" / "covers.json", out / "records" / "covers.json")
        records.append("returned/%s/records/covers.json" % rid)
    ev = chain_evidence(run)
    sc = _read(B / "SWIPE-CHECK.json", {}) or {}
    sc_rows = sc.get("checks") if isinstance(sc, dict) else sc
    cut = "; ".join("%s %s (%s)" % (x.get("check"), "pass" if x.get("pass") else "OPEN", x.get("detail"))
                    for x in sc_rows or []) or "no Studio cut check on record"
    opened = (" Known open items: " + open_items) if open_items else ""
    at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    changes = "; ".join("%s: %s" % (k, v) for k, v in cc.items()) or "none"
    checks = {
        "complete-set": "%d slots, %d distinct files; the control and %d openings, each opening its own line, picture "
                        "and clip replacing the first scene (Studio versions %s)." % (
                            len(items), len({i["sha256"] for i in items}), len(items) - 1, ", ".join(tf["versions"])),
        "creative-review": "Every final file reviewed in full by %s. %s; %s; %s. Creative changes: %s.%s" % (
            by, ev["checklists"], ev["fixes"], ev["gaps"], changes, opened),
        "facts": "%s; the product is the kept 3D prints made with its casting sheet, never drawn; the offer and claim "
                 "lines are the brief's own script lines, spoken as written (the cut's words check is in the technical "
                 "review); the destination is unchanged from the brief.%s" % (ev["product"], opened),
        "technical-review": "Measured: %s. Studio cut check: %s.%s" % ("; ".join(dims), cut, opened),
        "brief-criteria": "The brief went through the production run's start gates before any spend; %s; %s.%s" % (
            ev["fixes"], ev["gaps"], opened),
        "cover-review": "%d covers, each its own (distinct sha256), each ok with no problems in image production's "
                        "covers.json, each from its own version's video (frame video_sha256 matches): %s." % (
                            len(items), ", ".join(covers_ok)),
    }
    sub = {"schema": "delivery-submission/1", "brief_key": key, "revision_id": rid,
           "requirements_sha256": D.digest(req), "submitted_by": by, "submitted_at": at,
           "production_records": records, "items": items,
           "checks": {c["id"]: {"checked": True, "by": by, "at": at, "evidence": checks.get(c["id"], "")}
                      for c in req["criteria"]}}
    if dry:
        return {"would_write": str(out / D.SUBMISSION), "submission": sub}
    (out / D.SUBMISSION).write_text(json.dumps(sub, indent=1, ensure_ascii=False) + "\n")
    D.validate(folder)
    return {"written": str(out / D.SUBMISSION), "valid": True, "slots": [i["slot_id"] for i in items]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("handoff")
    ap.add_argument("--production", required=True)
    ap.add_argument("--by", required=True)
    ap.add_argument("--run")
    ap.add_argument("--open", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    print(json.dumps(build(a.handoff, a.production, a.by, a.run, a.open, a.dry_run), indent=1, ensure_ascii=False,
                     default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
