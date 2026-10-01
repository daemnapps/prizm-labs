#!/usr/bin/env python3
"""The framework bank — every swipe's doctrine read, on one shelf.

Damon's ruling, 2026-09-18: "every time we run a swipe, we'll run it through a
marketing doctrine step too so we have full awareness of it and can clearly
identify the unique framework of that video and bank it for later." Stage 1c
does the reading, one run at a time; this is the shelf those readings land on,
so "find me the problem-aware mechanism ads we've torn down" is one command
rather than ninety folders.

It compiles, it never decides. Every row comes from a run's own
`doctrine.json` and its `run.json`; nothing here re-reads a video, re-words a
reading or fills a gap.

    python3 framework_bank.py                       rebuild the whole bank
    python3 framework_bank.py --awareness problem-aware --signature mechanism
    python3 framework_bank.py --query "guarantee"   free text across every row
    python3 framework_bank.py --runs <dir>          compile a different shelf
    python3 framework_bank.py --promote <run-label> promote an OBSERVED framework

A filter prints the matching rows and leaves the written bank alone; a plain
rebuild writes both files. Matching is case-insensitive substring, because a
reading says "a mechanism" where a filter says "mechanism" and neither is
wrong.

`--promote` is the one command here that writes somewhere else: it copies the
framework a run OBSERVED (its doctrine.json) into
components/marketing-doctrine/ad-frameworks.json as a new row, status
'seed', source 'observed — <label>'. Run it ONLY on Damon's own word — the
bank compiles what ran, ad-frameworks.json is curated doctrine, and the two
must never quietly become the same file. A run compose.py opened (its
doctrine.json is marked `composed: true`) has nothing observed to promote and
is refused by name.

Writes, beside the runs:
    framework-bank.json   every row, for anything that reads
    framework-bank.md     the same rows as a table, for anyone who reads

Stdlib only. Called at the end of every run, where it must never raise.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
# The doctrine component this shelf promotes into. A sibling folder, not a
# key inside this one — components/marketing-doctrine owns its own files.
DOCTRINE_DIR = MACHINE.parent.parent / "marketing-doctrine"
AD_FRAMEWORKS_PATH = DOCTRINE_DIR / "ad-frameworks.json"
FRAMEWORKS_PATH = DOCTRINE_DIR / "frameworks.json"

# The five canonical sophistication signatures (stage2f's own section 5
# vocabulary), longest phrase first so "the mechanism enlarged" is not
# swallowed by the plainer "mechanism" test below it.
SIGNATURE_TO_STAGE = [
    ("the mechanism enlarged", "stage-4"), ("mechanism enlarged", "stage-4"),
    ("a mechanism", "stage-3"), ("mechanism", "stage-3"),
    ("the claim enlarged", "stage-2"), ("claim enlarged", "stage-2"),
    ("the plain claim", "stage-1"), ("plain claim", "stage-1"),
    ("identification only", "stage-5"), ("identification", "stage-5"),
]

# Every filter, and where in a row it looks. Adding one is adding a line.
FILTERS = {
    "framework": ("framework",),
    "signature": ("signature",),
    "awareness": ("awareness_entry", "awareness_exit"),
    "section": ("sections_flat",),
    "technique": ("techniques_flat",),
    "desire": ("desire",),
    "mood": ("mood",),
    # the delivery read (stage 1c v2) — how the swipe was PERFORMED. Three
    # filters because these are the three a person actually asks for: find me
    # the deadpan ones, the dry ones, the ones that ran plain and flat.
    "humor": ("humor",),
    "delivery-style": ("delivery_style",),
    "register": ("register",),
    "brand": ("brand",),
    "lane": ("lane", "format"),
}


def runs_root(override=None):
    """Where the runs live. The machine's own `runs/` unless told otherwise —
    which is what makes this testable against a temp tree."""
    if override:
        return Path(override).expanduser().resolve()
    return MACHINE / "runs"


def _text(v):
    """Any doctrine value as a readable one-liner. A model answers a string
    where the schema says string, but a list or a dict is a shape we can still
    read rather than a row we throw away."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, list):
        return " · ".join(x for x in (_text(i) for i in v) if x)
    if isinstance(v, dict):
        return " · ".join(f"{k}: {_text(x)}" for k, x in v.items() if _text(x))
    return str(v)


def _sections(doc):
    """`sections_carried` as `hook 0:00-0:04` strings, in the order played."""
    out = []
    for s in doc.get("sections_carried") or []:
        if isinstance(s, dict):
            sid, span = _text(s.get("id")), _text(s.get("span"))
            out.append(f"{sid} {span}".strip())
        else:
            out.append(_text(s))
    return [x for x in out if x]


def _techniques(doc):
    """`techniques` as `hook · intensification · <sub-method>` strings."""
    out = []
    for t in doc.get("techniques") or []:
        if isinstance(t, dict):
            bits = [_text(t.get("section")), _text(t.get("technique")),
                    _text(t.get("sub_method"))]
            span = _text(t.get("span"))
            line = " · ".join(b for b in bits if b)
            out.append(f"{line} ({span})" if span and line else line)
        else:
            out.append(_text(t))
    return [x for x in out if x]


def run_link(run_dir, state):
    """Where a person goes to see this run.

    A path is not a link (Damon's rule), so the finished document wins when
    the run has one and the creator's folder is next. The local folder is the
    last resort and goes out as a `file://` url, which opens from the page."""
    for key in ("gdoc_url", "creator_folder"):
        v = (state.get(key) or "").strip()
        if v.startswith("http"):
            return v
    return Path(run_dir).resolve().as_uri()


def read_run(run_dir):
    """One run -> (row, None) or (None, why it was skipped).

    Every failure is a skip with a reason. A malformed reading must never stop
    the bank compiling, because the one thing worse than a missing row is
    ninety missing rows."""
    run_dir = Path(run_dir)
    f = run_dir / "doctrine.json"
    try:
        doc = json.loads(f.read_text())
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    if not isinstance(doc, dict):
        return None, f"doctrine.json holds a {type(doc).__name__}, not an object"
    if doc.get("error"):
        return None, f"stage 1c filed an error: {_text(doc['error'])[:160]}"

    state = {}
    rj = run_dir / "run.json"
    if rj.is_file():
        try:
            got = json.loads(rj.read_text())
            state = got if isinstance(got, dict) else {}
        except Exception:
            state = {}

    aw = doc.get("awareness")
    aw = aw if isinstance(aw, dict) else {}
    md = doc.get("mass_desire")
    md = md if isinstance(md, dict) else {}
    sections, techniques = _sections(doc), _techniques(doc)
    dl = doc.get("delivery")
    dl = dl if isinstance(dl, dict) else {}
    # one readable line for the table: the four single-value dials in a fixed
    # order, so two rows read the same way and an empty one reads as empty
    delivery_flat = " · ".join(
        x for x in (_text(dl.get("humor")), _text(dl.get("delivery_style")),
                    _text(dl.get("register")), _text(dl.get("pacing"))) if x)

    row = {
        "run": run_dir.name,
        "label": _text(state.get("label")) or run_dir.name,
        "brand": _text(state.get("brand")),
        "lane": _text(state.get("lane")),
        "format": _text(state.get("format") or state.get("triage_lane")),
        "source_url": _text(state.get("origin_url") or state.get("source_url")),
        "link": run_link(run_dir, state),
        "framework": _text(doc.get("framework")),
        "crosswalk_row": _text(doc.get("crosswalk_row")),
        "sections_carried": sections,
        "awareness_entry": _text(aw.get("entry")),
        "awareness_exit": _text(aw.get("exit")),
        "signature": _text(doc.get("sophistication_signature")),
        "desire": _text(md.get("words")) or _text(doc.get("mass_desire")),
        "desire_urgency": _text(md.get("urgency")),
        "desire_staying_power": _text(md.get("staying_power")),
        "desire_scope": _text(md.get("scope")),
        "techniques": techniques,
        "mood": _text(doc.get("mood")),
        "humor": _text(dl.get("humor")),
        "delivery_style": _text(dl.get("delivery_style")),
        "register": _text(dl.get("register")),
        "pacing": _text(dl.get("pacing")),
        "reference_world": _text(dl.get("reference_world")),
        "avoid": _text(dl.get("avoid")),
        "delivery_flat": delivery_flat,
        "unique": _text(doc.get("unique")),
        "missing_keys": doc.get("_missing_keys") or [],
    }
    # flattened once, so a filter is a substring test and never a walk
    row["sections_flat"] = " · ".join(sections)
    row["techniques_flat"] = " · ".join(techniques)
    return row, None


def collect(root=None):
    """Every run under the shelf, newest folder last. -> (rows, skipped)."""
    root = runs_root(root)
    rows, skipped = [], []
    if not root.is_dir():
        return rows, skipped
    for f in sorted(root.glob("*/doctrine.json")):
        row, why = read_run(f.parent)
        (rows if row else skipped).append(row or {"run": f.parent.name, "why": why})
    return rows, skipped


def matches(row, want):
    """Does this row answer every filter given? Case-insensitive substring —
    a reading says "a mechanism", a filter says "mechanism"."""
    for name, needle in want.items():
        if not needle:
            continue
        n = str(needle).strip().lower()
        fields = FILTERS.get(name, (name,))
        hay = " ".join(str(row.get(f) or "") for f in fields).lower()
        if n not in hay:
            return False
    return True


def free_text(row, q):
    if not q:
        return True
    blob = json.dumps(row, ensure_ascii=False).lower()
    return all(t in blob for t in str(q).lower().split())


def query(rows, want=None, q=None):
    want = want or {}
    return [r for r in rows if matches(r, want) and free_text(r, q)]


def _cell(s, cap=150):
    """One markdown cell: no pipes, no newlines, and never so long the table
    stops being readable."""
    s = re.sub(r"\s+", " ", str(s or "")).replace("|", "/").strip()
    return (s[:cap - 1].rstrip() + "…") if len(s) > cap else (s or "—")


HEAD = ["Framework", "Sections it carries", "Who it starts with → ends with",
        "What it leads with", "The want it rides", "Moves it uses",
        "How it is delivered", "Humor", "Register",
        "Why it is worth keeping", "The run"]


def to_markdown(rows, skipped=None, title="The framework bank"):
    """The shelf, for a person. Plain names in the headers — a column called
    `sophistication_signature` is a column nobody reads."""
    skipped = skipped or []
    out = [f"# {title}", ""]
    out.append("Every video we have swiped, read against the doctrine and "
               "banked — the shape it follows, the sections it carries, where "
               "it picks the viewer up and puts them down, how it is "
               "delivered, and the one thing worth taking from it.")
    out.append("")
    out.append(f"Compiled {time.strftime('%Y-%m-%d %H:%M')} · {len(rows)} swipe(s)"
               + (f" · {len(skipped)} skipped" if skipped else ""))
    out.append("")
    out.append("Rebuilt by the machine at the end of every run. Never hand-edited "
               "— a correction belongs on the run it came from.")
    out.append("")
    if not rows:
        out.append("Nothing banked yet. The bank fills itself as videos go "
                   "through the machine.")
        out.append("")
    else:
        out.append("| " + " | ".join(HEAD) + " |")
        out.append("|" + "---|" * len(HEAD))
        for r in rows:
            ladder = " → ".join(x for x in (r["awareness_entry"],
                                            r["awareness_exit"]) if x)
            name = _cell(r["label"], 60)
            link = r.get("link") or ""
            out.append("| " + " | ".join([
                _cell(r["framework"]),
                _cell(r["sections_flat"], 220),
                _cell(ladder, 60),
                _cell(r["signature"], 80),
                _cell(r["desire"], 120),
                _cell(r["techniques_flat"], 220),
                _cell(r["delivery_flat"], 120),
                _cell(r["humor"], 40),
                _cell(r["register"], 40),
                _cell(r["unique"], 220),
                f"[{name}]({link})" if link else name,
            ]) + " |")
        out.append("")
        out.append("## Where each one came from")
        out.append("")
        out.append("| The run | Brand | Kind | The original |")
        out.append("|---|---|---|---|")
        for r in rows:
            src = r.get("source_url") or ""
            out.append("| " + " | ".join([
                _cell(r["label"], 60), _cell(r["brand"], 30),
                _cell(" · ".join(x for x in (r["lane"], r["format"]) if x), 40),
                f"[the post]({src})" if src.startswith("http") else "—",
            ]) + " |")
        out.append("")
    if skipped:
        out.append("## Not banked")
        out.append("")
        out.append("A reading the machine could not file. The run's own words "
                   "are still on disk — re-run its doctrine step to bank it.")
        out.append("")
        out.append("| The run | What stopped it |")
        out.append("|---|---|")
        for s in skipped:
            out.append(f"| {_cell(s.get('run'), 60)} | {_cell(s.get('why'), 200)} |")
        out.append("")
    return "\n".join(out)


def build(root=None, write=True):
    """Compile the shelf. -> (rows, skipped, {json path, md path})."""
    root_p = runs_root(root)
    rows, skipped = collect(root)
    paths = {}
    if write:
        root_p.mkdir(parents=True, exist_ok=True)
        j = root_p / "framework-bank.json"
        m = root_p / "framework-bank.md"
        j.write_text(json.dumps({
            "compiled": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "count": len(rows),
            "rows": rows,
            "skipped": skipped,
        }, indent=2, ensure_ascii=False))
        m.write_text(to_markdown(rows, skipped))
        paths = {"json": j, "md": m}
    return rows, skipped, paths


def refresh(root=None):
    """The end-of-run call. Never raises and never stops a run: a bank that
    failed to compile is a rebuild away, and the run's words are already
    safe. -> a one-line summary, or None."""
    try:
        rows, skipped, _ = build(root)
    except Exception:
        return None
    # The element labels of every banked run, checked against the shared
    # element library (components/elements) — added 2026-09-20. It writes
    # elements.json beside each doctrine.json, records an unknown value AS
    # unknown, and never raises; the bank's own files are untouched by it.
    labelled = ""
    try:
        import elements_check as _ec
        n, bad = _ec.check_all(root)
        if n:
            labelled = (f" · {n} labelled against the element library"
                        + (f", {bad} with an unknown value" if bad else ""))
    except Exception:
        labelled = ""
    return (f"{len(rows)} swipe(s) banked"
            + (f", {len(skipped)} unreadable" if skipped else "") + labelled)


def _stage_for_signature(signature, stages):
    """Best matching sophistication stage id for a run's prose
    `sophistication_signature`. -> (stage_id or None, why)."""
    sig = (signature or "").strip().lower()
    if not sig:
        return None, "the run named no sophistication_signature"
    for phrase, sid in SIGNATURE_TO_STAGE:
        if phrase in sig:
            return sid, "matched the canonical phrase '%s'" % phrase
    for st in stages:
        lw = (st.get("lead_with") or "").lower()
        if lw and (sig in lw or lw in sig):
            return st["id"], "matched stage %s's own lead_with" % st["id"]
    return None, "signature '%s' matched no stage" % signature


def find_run(label, root=None):
    """A run folder by its own name or its run.json `label`, case-insensitive.
    -> Path or None."""
    root_p = runs_root(root)
    if not root_p.is_dir():
        return None
    direct = root_p / str(label)
    if (direct / "doctrine.json").is_file():
        return direct
    want = str(label).strip().lower()
    for f in sorted(root_p.glob("*/run.json")):
        try:
            st = json.loads(f.read_text())
        except Exception:
            continue
        if str(st.get("label") or "").strip().lower() == want:
            return f.parent
    for f in sorted(root_p.glob("*/doctrine.json")):
        if f.parent.name.lower() == want:
            return f.parent
    return None


def promote(label, root=None):
    """Copy the framework a run OBSERVED (its doctrine.json) into
    ad-frameworks.json as a new row: status 'seed', source
    'observed — <label>'. Re-promoting the same label updates that row in
    place rather than duplicating it — the label is the identity, not the id.

    This function is the mechanics only; the CLI's help text is the gate —
    a session runs it on Damon's word, never on its own initiative.

    -> (row, note) on success. Raises ValueError, naming the run, on any
    refusal: no such run, a run that filed an error instead of a reading, a
    COMPOSED run (nothing observed to promote), or a reading whose sections
    or awareness no longer match the live doctrine.
    """
    run_dir = find_run(label, root)
    if run_dir is None:
        raise ValueError(f"no run called '{label}' under {runs_root(root)}")
    doc = json.loads((run_dir / "doctrine.json").read_text())
    if not isinstance(doc, dict):
        raise ValueError(f"{run_dir.name}'s doctrine.json is not an object")
    if doc.get("error"):
        raise ValueError(f"{run_dir.name} filed an error, not a reading — "
                          f"{_text(doc['error'])[:160]}")
    if doc.get("composed"):
        raise ValueError(f"{run_dir.name} is a COMPOSED run (the second "
                          f"door) — it has no swipe behind it, so there is "
                          f"nothing OBSERVED to promote")

    doctrine = json.loads(FRAMEWORKS_PATH.read_text())
    known_sections = {s["id"] for s in doctrine["sections"]}
    known_techniques = {t["id"]: t for t in doctrine["techniques"]}
    valid_aw = {l["id"] for l in doctrine["awareness"]["levels"]}
    stages = doctrine["sophistication"]["stages"]

    tech_by_section = {}
    for t in (doc.get("techniques") or []):
        if isinstance(t, dict) and t.get("section"):
            tech_by_section.setdefault(t["section"], t.get("technique"))

    sections = []
    for s in (doc.get("sections_carried") or []):
        sid = s.get("id") if isinstance(s, dict) else None
        if not sid or sid not in known_sections:
            continue
        tech = tech_by_section.get(sid)
        if tech not in known_techniques:
            continue
        sections.append({"id": sid, "technique": tech,
                         "shape": known_techniques[tech]["scene_shape"]})
    if not sections:
        raise ValueError(f"{run_dir.name}'s doctrine.json names no section "
                          f"the live doctrine still carries, with a "
                          f"technique the live doctrine still has — nothing "
                          f"to promote")

    aw = doc.get("awareness") or {}
    entry, exit_ = aw.get("entry"), aw.get("exit")
    if entry not in valid_aw or exit_ not in valid_aw:
        raise ValueError(f"{run_dir.name}'s awareness ({entry!r} -> "
                          f"{exit_!r}) does not name two real awareness "
                          f"levels")

    stage_id, why = _stage_for_signature(doc.get("sophistication_signature"), stages)

    name = _text(doc.get("framework")) or run_dir.name
    what = _text(doc.get("unique")) or (
        f"Observed off {run_dir.name} — promoted, not yet judged as an ad.")

    ad = json.loads(AD_FRAMEWORKS_PATH.read_text())
    label_norm = str(label).strip()
    source = f"observed — {label_norm}"
    existing = next((f for f in ad["frameworks"] if f.get("source") == source), None)
    if existing:
        new_id = existing["id"]
    else:
        used_ids = {f["id"] for f in ad["frameworks"]}
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "observed"
        new_id, n = base, 2
        while new_id in used_ids:
            new_id, n = f"{base}-{n}", n + 1

    row = {
        "id": new_id, "name": name, "what": what,
        "sections": sections,
        "awareness": {"entry": entry, "exit": exit_},
        "sophistication": [stage_id] if stage_id else [],
        "formats_fit": ["any"],
        "source": source,
        "status": "seed",
        "ref": [],
    }
    ad["frameworks"] = ([row if f is existing else f for f in ad["frameworks"]]
                        if existing else ad["frameworks"] + [row])
    ad["updated"] = time.strftime("%Y-%m-%d")
    AD_FRAMEWORKS_PATH.write_text(
        json.dumps(ad, indent=2, ensure_ascii=False) + "\n")
    return row, why


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="the framework bank — every swipe's doctrine read")
    ap.add_argument("--runs", help="compile a different shelf of runs")
    ap.add_argument("--query", help="free text across the whole row")
    for name in FILTERS:
        ap.add_argument("--" + name, help=f"only rows whose {name} matches")
    ap.add_argument("--json", action="store_true",
                    help="print matching rows as json")
    ap.add_argument("--promote", metavar="RUN-LABEL",
                    help="copy this run's OBSERVED framework into "
                         "components/marketing-doctrine/ad-frameworks.json "
                         "as a new 'seed' row. RUN ONLY ON DAMON'S OWN "
                         "WORD — ad-frameworks.json is curated doctrine, "
                         "not a compiled shelf, and a session promotes into "
                         "it only when he has said to.")
    args = ap.parse_args(argv)

    if args.promote:
        try:
            row, why = promote(args.promote, args.runs)
        except ValueError as e:
            print(f"REFUSED — {e}")
            return 1
        print(f"promoted '{args.promote}' -> ad-frameworks.json id "
              f"'{row['id']}', status seed")
        print(f"  sophistication: {row['sophistication'] or '(none matched — %s)' % why}")
        print(f"  sections: {', '.join(s['id'] for s in row['sections'])}")
        return 0

    # argparse turns --delivery-style into args.delivery_style, so a filter
    # whose name carries a dash is read under its dest, never its flag
    want = {k: getattr(args, k.replace("-", "_")) for k in FILTERS}
    filtering = bool(args.query) or any(want.values())

    rows, skipped, paths = build(args.runs, write=not filtering)
    hits = query(rows, want, args.query)

    if args.json:
        print(json.dumps(hits, indent=2, ensure_ascii=False))
        return 0
    if filtering:
        print(to_markdown(hits, title="The framework bank — matching swipes"))
        return 0 if hits else 1
    print(f"banked {len(rows)} swipe(s)"
          + (f", skipped {len(skipped)}" if skipped else ""))
    for p in paths.values():
        print(f"  {p}")
    for s in skipped:
        print(f"  skipped {s.get('run')} — {s.get('why')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
