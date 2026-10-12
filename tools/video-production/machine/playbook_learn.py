#!/usr/bin/env python3
"""
playbook_learn.py — after a run finishes, its playbook learns from it. Fully
automatic (the owner, 2026-10-10: "I'm not going to have time to identify and create
every individual workflow"; "we cannot have AI slop").

    python3 machine/playbook_learn.py <finished-run> [--format <id>] [--dry-run]

Reads the run's records — run.json (format, notes), ledger.json (spend), BUDGET.md,
every *.md note in the run root and its edit twin under runs/video-edit/, and
clips/gate-refusals.json — and finds:

  * what broke and the workaround used (a line naming a failure word — refused,
    failed, garbled, drifted, cut off, dropped… — with a fix after → / — / fix:)
  * spend against the playbook's cost target
  * a known setting the records show cleared a refusal (a send size, a short-clip
    method)

It writes runs/playbook-learn/<format_id>/<run-label>/PROPOSAL.md (+ PROPOSAL.json),
every item with what it would change and why. Then it APPLIES, by these rules:

  * a NEW known failure → fix (one not already listed) is added to the playbook's
    failures, with the run it came from — status unchanged;
  * a stage SETTING change is applied to a DRAFT playbook; to an APPROVED one only
    when it lowers cost or fixes a refusal WITHOUT changing the look — every item
    says which rule let it in, or why it stayed a proposal;
  * a variant's settings go into that variant's overrides, never the family's.

No brand, model or person name lives in this file as a literal.
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent
FAIL_WORDS = re.compile(r"\b(refus\w*|fail\w*|broke\w*|garbled|drift\w*|cut[ -]?off|dropped|blurred|misspel\w*|"
                        r"merged faces|stranger in|could not generate|dead air|held at|crash\w*)\b", re.I)
FIX_SPLIT = re.compile(r"\s(?:→|->|—|–|fix(?:ed)?:|so we|workaround:)\s", re.I)
QUALITY_STEPS = ("low", "medium", "high", "xhigh")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PB = _load("playbook")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo() -> Path:
    sys.path.insert(0, str(HERE.parents[1].parent / "components" / "run-kit"))
    from run_kit.paths import repo as _repo
    return _repo(HERE)


def _json(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _rel(p) -> str:
    try:
        return str(Path(p).resolve().relative_to(repo()))
    except (ValueError, FileNotFoundError):
        s = str(p)
        return s[s.index("/runs/") + 1:] if "/runs/" in s else s   # never a machine path in a record


def spend(run: Path) -> Optional[float]:
    """The run's ledger total in dollars (rows with no price are not guessed)."""
    led = _json(run / "ledger.json")
    rows = led if isinstance(led, list) else (led or {}).get("rows") or (led or {}).get("entries") or []
    tot, seen = 0.0, False
    for r in rows:
        if isinstance(r, dict):
            v = r.get("usd", r.get("cost_usd"))
            if isinstance(v, (int, float)):
                tot += float(v)
                seen = True
    if seen:
        return round(tot, 2)
    rj = _json(run / "run.json", {}) or {}
    for k in ("spent_usd_ledger", "spent_usd", "spend_usd"):
        if isinstance(rj.get(k), (int, float)):
            return float(rj[k])
    return None


def records(run: Path) -> List[tuple]:
    """(source, line) for every note line the run and its edit twin hold."""
    out = []
    homes = [run]
    try:
        parts = run.resolve().parts
        i = parts.index("video-production")
        twin = Path(*parts[:i]) / "video-edit" / Path(*parts[i + 1:])
        if twin.is_dir():
            homes.append(twin)
    except ValueError:
        pass
    for h in homes:
        for p in sorted(h.glob("*.md")) + sorted((h / "song").glob("*.md")):
            for line in p.read_text(errors="ignore").splitlines():
                if line.strip():
                    out.append((_rel(p), line.strip()))
        rj = _json(h / "run.json", {}) or {}
        for k, v in rj.items():
            if isinstance(v, str) and len(v) < 600:
                out.append((_rel(h / "run.json") + f"#{k}", f"{k}: {v}"))
    return out


def failures_found(run: Path) -> List[dict]:
    found = []
    for src, line in records(run):
        if line.startswith(("#", "|", ">")) or not FAIL_WORDS.search(line):
            continue   # headings, tables and quotes are not a record of what broke
        bits = FIX_SPLIT.split(line, maxsplit=1)
        if len(bits) != 2:
            continue
        fail, fix = (re.sub(r"^[\-*#>|\s]+", "", bits[0]).strip(" .|"), bits[1].strip(" .|"))
        if 8 <= len(fail) <= 240 and 4 <= len(fix) <= 300:
            found.append({"failure": fail, "fix": fix, "from_run": _rel(run), "source": src})
    ref = _json(run / "clips" / "gate-refusals.json")
    if ref:
        n = len(ref) if isinstance(ref, (list, dict)) else 0
        if n:
            found.append({"failure": f"{n} clip refusal(s) logged by the clip model", "fix": None,
                          "from_run": _rel(run), "source": _rel(run / "clips" / "gate-refusals.json"),
                          "refusals": True})
    return found


def known(f: dict, pb: dict) -> bool:
    for g in pb.get("failures") or []:
        if difflib.SequenceMatcher(None, f["failure"].lower(), str(g.get("failure")).lower()).ratio() >= 0.6:
            return True
    return False


def setting_proposals(run: Path, pb: dict, spent: Optional[float]) -> List[dict]:
    props = []
    text = "\n".join(l for _s, l in records(run))
    st = pb.get("stages") or {}
    m = re.search(r"(?:refus|could not generate)[^\n]{0,160}?(\d{3,4}x\d{3,4})\s*(?:jpe?g)", text, re.I) or \
        re.search(r"(\d{3,4}x\d{3,4})\s*jpe?g[^\n]{0,160}?(?:refus|cleared|passed)", text, re.I)
    if m and (st.get("clips") or {}).get("send_size") != m.group(1):
        props.append({"path": "stages.clips.send_size", "from": (st.get("clips") or {}).get("send_size"),
                      "to": m.group(1), "lowers_cost": False, "fixes_refusal": True, "changes_look": False,
                      "why": "the run's records show this send size cleared clip refusals"})
    if re.search(r"short[^\n]{0,60}\brevers", text, re.I) and (st.get("clips") or {}).get("short_clip") in (None, ""):
        props.append({"path": "stages.clips.short_clip", "from": None, "to": "play the rest in reverse — never hold a frame",
                      "lowers_cost": False, "fixes_refusal": False, "changes_look": True,
                      "why": "the run covered short clips by reversing"})
    target = (pb.get("cost") or {}).get("target_usd_per_ad")
    # Spend is held against the target only for a run MADE under this playbook
    # (run.json `playbook`) — an older run's spend reflects the settings it ran on,
    # and learning cost from it would ratchet a playbook it never used.
    under = bool((_json(run / "run.json", {}) or {}).get("playbook"))
    if under and spent is not None and isinstance(target, (int, float)) and spent > target:
        cpp = (st.get("clips") or {}).get("clips_per_picture")
        lo = cpp[0] if isinstance(cpp, list) and cpp else (cpp or 1)
        if isinstance(lo, (int, float)) and lo < 3:
            props.append({"path": "stages.clips.clips_per_picture", "from": cpp, "to": [int(lo) + 1, int(lo) + 2],
                          "lowers_cost": True, "fixes_refusal": False, "changes_look": False,
                          "why": f"spent ${spent} against a ${target} target — more clips from each picture, same look"})
        q = (st.get("pictures") or {}).get("quality")
        if q in QUALITY_STEPS and QUALITY_STEPS.index(q) > 0:
            props.append({"path": "stages.pictures.quality", "from": q, "to": QUALITY_STEPS[QUALITY_STEPS.index(q) - 1],
                          "lowers_cost": True, "fixes_refusal": False, "changes_look": True,
                          "why": f"spent ${spent} against a ${target} target — one quality step down"})
    return props


def may_apply(item: dict, status: str) -> tuple:
    if status == "draft":
        return True, "the playbook is a draft"
    if status == "approved" and (item.get("lowers_cost") or item.get("fixes_refusal")) and not item.get("changes_look"):
        return True, "approved, and it " + ("lowers cost" if item.get("lowers_cost") else "fixes a refusal") + " without changing the look"
    return False, "approved, and it would change the look (or neither lowers cost nor fixes a refusal) — a proposal only"


def learn(run: Path, format_id: Optional[str] = None, folder: Optional[Path] = None,
          out_root: Optional[Path] = None, dry_run: bool = False) -> dict:
    run = Path(run)
    rj = _json(run / "run.json", {}) or {}
    fid = PB.normalise_id(format_id or rj.get("format_id") or rj.get("format"))
    folder = Path(folder or PB.root())
    pb_res = PB.playbook_for(fid)
    family_id = pb_res.get("format_id")
    variant = pb_res.get("variant")
    fam_path = folder / f"{family_id}.json"
    fam = _json(fam_path) if family_id and family_id != "default" else None
    spent = spend(run)
    found = failures_found(run)
    new_f = [f for f in found if f.get("fix") and not known(f, pb_res)]
    props = setting_proposals(run, pb_res, spent)
    status = (variant or {}).get("status") or (fam or {}).get("status") or "approved"
    applied = []
    for f in new_f:
        f["applied"], f["rule"] = bool(fam), ("a new known failure → fix; status unchanged" if fam else "no family playbook to add it to")
    for p in props:
        ok, why = may_apply(p, status) if fam else (False, "no family playbook — the default is never edited by a run")
        p["applied"], p["rule"] = ok, why
    if fam and not dry_run:
        for f in new_f:
            row = {k: f[k] for k in ("failure", "fix", "from_run")}
            row.update({"stage": None, "added_by": "playbook_learn", "added": now()[:10]})
            fam.setdefault("failures", []).append(row)
            applied.append(f["failure"])
        for p in props:
            if not p["applied"]:
                continue
            if variant:
                for v in fam.get("variants") or []:
                    if v.get("id") == variant.get("id"):
                        v.setdefault("overrides", {})[p["path"]] = p["to"]
            else:
                PB.set_path(fam, p["path"], p["to"])
            applied.append(p["path"])
        if applied:
            PB.write(fam, folder)
    rec = {"at": now(), "run": _rel(run), "format_id": fid, "family": family_id, "variant": (variant or {}).get("id"),
           "status": status, "spent_usd": spent, "target_usd": (pb_res.get("cost") or {}).get("target_usd_per_ad"),
           "under_playbook": bool(rj.get("playbook")),
           "failures_new": new_f, "failures_known": len(found) - len(new_f), "settings": props, "applied": applied}
    if not dry_run:
        base = Path(out_root or (repo() / "runs" / "playbook-learn"))
        d = base / (fid or "_unnamed") / run.name
        d.mkdir(parents=True, exist_ok=True)
        (d / "PROPOSAL.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
        (d / "PROPOSAL.md").write_text(render(rec))
        rec["logged"] = str(d)
    return rec


def render(rec: dict) -> str:
    L = [f"# Playbook learn · {Path(rec['run']).name}", "",
         f"Format `{rec['format_id']}` → playbook `{rec['family']}`" + (f" (variant `{rec['variant']}`)" if rec.get("variant") else "")
         + f" · status {rec['status']} · {rec['at']}", "",
         f"**Spend:** ${rec['spent_usd']} against a target of ${rec['target_usd']}" if rec.get("spent_usd") is not None
         else "**Spend:** not on the ledger", "",
         "" if rec.get("under_playbook") else "_This run was not made under the playbook (no `playbook` in run.json): its spend is recorded, never held against the target._", "", "## New known failures → fixes", ""]
    for f in rec["failures_new"]:
        L.append(f"- **{f['failure']}** → {f['fix']}  _(from {f['source']}; {'ADDED' if f['applied'] else 'proposal'} — {f['rule']})_")
    if not rec["failures_new"]:
        L.append(f"- none new ({rec['failures_known']} already known)")
    L += ["", "## Stage settings", ""]
    for p in rec["settings"]:
        L.append(f"- `{p['path']}`: {p['from']!r} → {p['to']!r} — {p['why']}  _({'APPLIED' if p['applied'] else 'proposal'}: {p['rule']})_")
    if not rec["settings"]:
        L.append("- none")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--format", dest="format_id")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    rec = learn(Path(a.run), a.format_id, dry_run=a.dry_run)
    print(render(rec))
    if rec.get("logged"):
        print("logged:", rec["logged"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
