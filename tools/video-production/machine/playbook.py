#!/usr/bin/env python3
"""
playbook.py — the FORMAT PLAYBOOK loader. One specialised workflow per kind of ad,
on top of the shared chain.

the owner, 2026-10-10: "it's about optimizing workflows for specific types of ads, as
opposed to just having a general workflow for all ads … at certain points being
more specific on the type of video requires specialized knowledge … I need a
system that can build out the specific workflows based off of the videos that come
into the system." And, the same day: "every time there's a new format … we first
need to identify whether or not it's similar enough to another type of format
that's already worked … so we're not doing double work."

A playbook (formats/playbooks/<id>.json, readable twin <id>.md) carries the
per-format STAGE SETTINGS the shared chain runs with: audio first (song | voice |
none), the picture door's quality/size/fix calls, the clip model/resolution/
seconds/clips per picture, the cast reuse policy, the hook shape, the caption look,
which gates apply, the edit method, the known failure → fix list (each with the run
it came from), a cost target per ad and the format's own "not slop" checks.

Every playbook is a FAMILY with a STRUCTURAL SIGNATURE (audio driver, speakers on
screen and who they address, settings, the product's role, pacing, capture, story
shape). A swipe close enough to a family becomes a VARIANT of it — a small entry
holding only its differences and overrides — never a new playbook (playbook_builder
matches first). `playbook_for()` resolves, in order:

  1. formats/playbooks/<id>.json             a family playbook
  2. a variant whose id / format_ids holds id the family, with the variant's overrides
  3. formats/playbooks/default.json          today's general chain, unchanged

Each layer is deep-merged onto the default, so every setting always resolves. A
value of null means "the shared chain's own setting" (providers.json, the
profile) — the playbook does not override it.

    python3 machine/playbook.py <format_id>             print the resolved playbook
    python3 machine/playbook.py <format_id> <dotted.path>   print one setting
    python3 machine/playbook.py --check                  validate every playbook

`VIDEO_PLAYBOOKS_DIR` points the loader at another folder (tests).
No brand, model or person name lives in this file as a literal.
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
DEFAULT_DIR = HERE.parent / "formats" / "playbooks"
STATUS = ("draft", "approved", "deprecated")
AUDIO = ("song", "voice", "none")
SIGNATURE_KEYS = ("audio", "speakers", "address", "settings", "product_role", "pacing", "capture", "story")
REQUIRED = ("format_id", "name", "status", "family", "signature", "stage_order", "stages",
            "failures", "cost", "quality_bar")


def root() -> Path:
    env = os.environ.get("VIDEO_PLAYBOOKS_DIR")
    return Path(env) if env else DEFAULT_DIR


def normalise_id(format_id: Optional[str]) -> Optional[str]:
    """'new:Sports Interview' → 'sports-interview'; 'song-ad' stays."""
    if not format_id:
        return None
    s = str(format_id).strip().lower()
    if s.startswith("new:"):
        s = s[4:]
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or None


def _read(p: Path) -> Optional[dict]:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def merge(base: dict, over: dict) -> dict:
    """Deep merge; lists and scalars in `over` replace; None in `over` keeps base."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        elif v is None and k in out:
            continue
        else:
            out[k] = copy.deepcopy(v)
    return out


def set_path(d: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    cur = d
    for p in parts[:-1]:
        if not isinstance(cur.get(p), dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def get_path(d: dict, dotted: str, default=None):
    cur: Any = d
    for p in dotted.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def default_playbook() -> dict:
    return _read(root() / "default.json") or {
        "format_id": "default", "name": "General chain", "status": "approved", "family": "default",
        "signature": {}, "stage_order": [], "stages": {}, "failures": [], "cost": {}, "quality_bar": []}


def families() -> List[dict]:
    """Every family playbook on disk (not the default), each as written."""
    out = []
    for p in sorted(root().glob("*.json")):
        if p.stem == "default":
            continue
        pb = _read(p)
        if pb and pb.get("status") != "deprecated":
            out.append(pb)
    return out


def own_file(format_id: Optional[str]) -> Optional[dict]:
    """The format's own family file as written — no default, no variant."""
    fid = normalise_id(format_id)
    if not fid or fid == "default":
        return None
    return _read(root() / f"{fid}.json")


def find_variant(format_id: Optional[str]):
    """(family playbook, variant) for a format that is a variant of a family, else (None, None)."""
    fid = normalise_id(format_id)
    if not fid:
        return None, None
    for fam in families():
        for v in fam.get("variants") or []:
            ids = [normalise_id(v.get("id"))] + [normalise_id(x) for x in v.get("format_ids") or []]
            if fid in ids:
                return fam, v
    return None, None


def has_playbook(format_id: Optional[str]) -> bool:
    """True when the format resolves to a family file or a variant (not the default)."""
    if own_file(format_id):
        return True
    fam, _v = find_variant(format_id)
    return fam is not None


def playbook_for(format_id: Optional[str]) -> dict:
    """The resolved playbook for a format — see the module docstring for the order.
    `_source` says which layer answered: 'family' | 'variant' | 'default'."""
    base = default_playbook()
    own = own_file(format_id)
    if own:
        pb = merge(base, own)
        pb["_source"] = "family"
        pb["format_id"] = own.get("format_id")
        return pb
    fam, var = find_variant(format_id)
    if fam:
        pb = merge(base, fam)
        for dotted, value in (var.get("overrides") or {}).items():
            set_path(pb, dotted, copy.deepcopy(value))
        pb["_source"] = "variant"
        pb["variant"] = copy.deepcopy(var)
        pb["format_id"] = fam.get("format_id")
        return pb
    pb = copy.deepcopy(base)
    pb["_source"] = "default"
    return pb


def setting(format_id: Optional[str], dotted: str, default=None):
    """One setting from the resolved playbook — what a runner calls. A null value,
    or a path the playbook does not hold, returns `default` (the shared chain's own)."""
    v = get_path(playbook_for(format_id), dotted, None)
    return default if v is None else v


def own_setting(format_id: Optional[str], dotted: str, default=None):
    """A setting only when the format's family/variant itself sets it (never the
    default layer) — for hooks that must change nothing when no playbook exists."""
    if not has_playbook(format_id):
        return default
    pb = playbook_for(format_id)
    if pb.get("_source") == "default":
        return default
    v = get_path(pb, dotted, None)
    return default if v is None else v


def picture_overrides(format_id: Optional[str]) -> Dict[str, str]:
    """What direct_openai may override from the playbook: quality, size and the
    registry key of the model ('model' | 'model_fast'). Empty when the format has
    no playbook or leaves them null — the door then sends exactly what it does today."""
    out = {}
    for k in ("quality", "size", "model_key"):
        v = own_setting(format_id, f"stages.pictures.{k}")
        if v is not None:
            out[k] = v
    return out


def validate(pb: dict) -> List[str]:
    """Problems with one playbook as written (a family file). Empty = fine."""
    probs = []
    for k in REQUIRED:
        if k not in pb:
            probs.append(f"missing {k}")
    if pb.get("status") not in STATUS:
        probs.append(f"status {pb.get('status')!r} — draft / approved / deprecated only (any other meaning goes in state)")
    if pb.get("status") == "approved" and not pb.get("signed"):
        probs.append("approved without a signed ruling")
    audio = get_path(pb, "stages.audio.first")
    if audio is not None and audio not in AUDIO:
        probs.append(f"stages.audio.first {audio!r} — song / voice / none")
    sig = pb.get("signature") or {}
    if sig.get("audio") is not None and sig.get("audio") not in AUDIO:
        probs.append(f"signature.audio {sig.get('audio')!r} — song / voice / none")
    for k in SIGNATURE_KEYS:
        if k not in sig:
            probs.append(f"signature missing {k}")
    for i, f in enumerate(pb.get("failures") or []):
        if not f.get("failure") or not f.get("fix"):
            probs.append(f"failure {i} needs failure + fix")
        if not f.get("from_run"):
            probs.append(f"failure {i} ({str(f.get('failure'))[:40]}) has no from_run")
    for v in pb.get("variants") or []:
        if not v.get("id"):
            probs.append("a variant without an id")
        if v.get("status") not in STATUS:
            probs.append(f"variant {v.get('id')} status {v.get('status')!r}")
    return probs


def check_all() -> Dict[str, List[str]]:
    out = {}
    for p in sorted(root().glob("*.json")):
        pb = _read(p)
        out[p.name] = ["not JSON"] if pb is None else validate(pb)
        if pb is not None and pb.get("format_id") != p.stem:
            out[p.name].append(f"format_id {pb.get('format_id')!r} is not the file name")
    return out


# ── the readable twin ─────────────────────────────────────────────────────────

def _val(v) -> str:
    if v is None:
        return "the shared chain's own"
    if isinstance(v, bool):
        return "on" if v else "off"
    if isinstance(v, list):
        return ", ".join(_val(x) for x in v)
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_val(x)}" for k, x in v.items())
    return str(v)


def render_md(pb: dict) -> str:
    """The playbook as a page a person reads — written beside every .json."""
    L = [f"# Playbook · {pb.get('name')} (`{pb.get('format_id')}`)", "",
         f"**Status:** {pb.get('status')}" + (f" · **state:** {pb.get('state')}" if pb.get("state") else ""),
         f"**Family:** {pb.get('family')}" + (f" · nearest when drafted: `{pb['nearest']}`" if pb.get("nearest") else ""),
         ""]
    if pb.get("signed"):
        s = pb["signed"]
        L += [f"**Signed:** {s.get('by')} {s.get('date')} — {s.get('ruling')}", ""]
    if pb.get("what"):
        L += [pb["what"], ""]
    L += ["*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*", "",
          "## Structural signature", "", "| | |", "|---|---|"]
    for k in SIGNATURE_KEYS:
        L.append(f"| {k} | {_val((pb.get('signature') or {}).get(k))} |")
    if pb.get("specialised"):
        L += ["", "## What is specialised, and why", ""]
        for s in pb["specialised"]:
            L.append(f"- **{s.get('what')}** — {s.get('why')}")
    L += ["", "## Stage order", "", " → ".join(pb.get("stage_order") or []) or "(the shared chain's)", "",
          "## Stage settings", ""]
    for stage, cfg in (pb.get("stages") or {}).items():
        L.append(f"**{stage}**")
        if isinstance(cfg, dict):
            for k, v in cfg.items():
                L.append(f"- {k}: {_val(v)}")
        else:
            L.append(f"- {_val(cfg)}")
        L.append("")
    L += ["## Known failures → fixes", ""]
    for f in pb.get("failures") or []:
        L.append(f"- **{f.get('failure')}** → {f.get('fix')}  _(from {f.get('from_run')}"
                 + (f"; stage {f['stage']}" if f.get("stage") else "") + ")_")
    if not pb.get("failures"):
        L.append("- none recorded yet — the first run's learn step fills this")
    c = pb.get("cost") or {}
    L += ["", "## Cost", "", f"- target per ad: ${c.get('target_usd_per_ad', '—')}"]
    for k, v in c.items():
        if k != "target_usd_per_ad":
            L.append(f"- {k}: {_val(v)}")
    L += ["", "## Quality bar — not slop", ""]
    L += [f"- {q}" for q in pb.get("quality_bar") or []] or ["- (none yet)"]
    if pb.get("variants"):
        L += ["", "## Variants (same workflow, refined)", ""]
        for v in pb["variants"]:
            L.append(f"### {v.get('name') or v.get('id')} (`{v.get('id')}`, {v.get('status')})")
            if v.get("what"):
                L.append(v["what"])
            if v.get("differences"):
                L.append("- differs: " + _val(v["differences"]))
            for k, x in (v.get("overrides") or {}).items():
                L.append(f"- override `{k}` = {_val(x)}")
            if v.get("from_runs"):
                L.append("- from: " + ", ".join(v["from_runs"]))
            if v.get("match_score") is not None:
                L.append(f"- matched at score {v['match_score']}")
            L.append("")
    if pb.get("built_from"):
        L += ["", "## Built from", ""] + [f"- {r}" for r in pb["built_from"]]
    if pb.get("rulings"):
        L += ["", "## Rulings behind it", ""] + [f"- {r}" for r in pb["rulings"]]
    return "\n".join(L).rstrip() + "\n"


def write(pb: dict, folder: Optional[Path] = None) -> Path:
    """Write <id>.json and its readable <id>.md."""
    folder = Path(folder or root())
    folder.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in pb.items() if not k.startswith("_")}
    p = folder / f"{clean['format_id']}.json"
    p.write_text(json.dumps(clean, indent=2, ensure_ascii=False) + "\n")
    (folder / f"{clean['format_id']}.md").write_text(render_md(clean))
    return p


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if not a:
        print(__doc__)
        return 3
    if a[0] == "--check":
        bad = 0
        for name, probs in check_all().items():
            print(("ok   " if not probs else "FAIL ") + name + ("" if not probs else ": " + "; ".join(probs)))
            bad += bool(probs)
        return 1 if bad else 0
    if a[0] == "--render":
        for p in sorted(root().glob("*.json")):
            pb = _read(p)
            if pb:
                (p.with_suffix(".md")).write_text(render_md(pb))
                print("rendered", p.with_suffix(".md").name)
        return 0
    if len(a) > 1:
        print(json.dumps(setting(a[0], a[1]), indent=1))
    else:
        print(json.dumps(playbook_for(a[0]), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
