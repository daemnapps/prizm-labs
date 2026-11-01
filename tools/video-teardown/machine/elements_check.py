#!/usr/bin/env python3
"""The element labels of a teardown, checked against the element library.

    python3 elements_check.py                 every run with a doctrine.json
    python3 elements_check.py <run-label>     one run, printed

Stage 1c reads a swipe against the doctrine and files `doctrine.json`. This
pass takes each value in it and asks the ONE library every tool shares
(`components/elements/`, read through its own `elements.py`) "is this a real
one?", then writes `elements.json` beside `doctrine.json`:

    {"elements": {"doctrine/awareness.entry":
                     {"value": "problem-aware", "id": "problem-aware", "known": true},
                  "doctrine/technique": [ {...}, {...} ], ...},
     "unknown": ["doctrine/technique: <the value nothing matched>"], ...}

THE ONE RULE: an unknown value is RECORDED as unknown — `id: null,
known: false`. It is never dropped and never nudged onto the nearest row,
because a value the library does not hold is the evidence that the library is
missing a row. And it NEVER fails a run: this is a label check, the words are
already on disk.

Costs nothing: it reads two JSON files. No model, no network.

Switch it off: `VT_NO_ELEMENTS_CHECK=1` in the environment.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
sys.path.insert(0, str(MACHINE))

OFF_ENV = "VT_NO_ELEMENTS_CHECK"
NOT_SHOWN = ("not shown in the record", "not shown", "none observed", "none",
             "null", "n/a", "")
# The delivery dials stage 1c reads, each its own list in the library.
DELIVERY_DIALS = ("humor", "delivery_style", "register", "pacing",
                  "reference_world", "avoid")


def library():
    """The shared element library's own module — `components/elements` is the
    one place a label is looked up. Found by walking up, never by counting."""
    import chain as C
    home = C.workspace() / "components/elements" / "machine"
    if not (home / "elements.py").is_file():
        raise FileNotFoundError(f"no element library at {home}")
    if str(home) not in sys.path:
        sys.path.insert(0, str(home))
    import elements as E                     # components/elements/machine
    return E


def _norm(v):
    return re.sub(r"[^a-z0-9]+", "-", str(v or "").lower()).strip("-")


def _head(v):
    """A value with its citation stripped: `dry · 0:04-0:09 · the beat` -> `dry`.
    Stripping a citation is reading the label; it is not guessing one."""
    return re.split(r"\s+[·—–|]\s+|\s+\(|\s+-\s+", str(v or "").strip(),
                    maxsplit=1)[0].strip()


def _lookup(E, element, asset, value):
    """-> the library row this value names, or None. Exact on id or name,
    after lower-casing and punctuation. Nothing fuzzier than that."""
    try:
        rows = E.rows(element, asset)
    except Exception:
        return None
    for want in (_norm(value), _norm(_head(value))):
        if not want:
            continue
        for r in rows:
            if want in (_norm(r.get("id")), _norm(r.get("name"))):
                return r
    return None


def _entry(E, element, asset, value, id_hint=None, note=None):
    text = value if isinstance(value, str) else (
        "" if value is None else json.dumps(value, ensure_ascii=False))
    row = None
    if id_hint:
        row = _lookup(E, element, asset, id_hint)
    if row is None:
        row = _lookup(E, element, asset, text)
    out = {"value": text, "id": row["id"] if row else None, "known": bool(row)}
    if not row and _norm(_head(text)) in {_norm(x) for x in NOT_SHOWN}:
        out["not_shown"] = True          # an unanswered slot, not a new row
    if note:
        out["note"] = note
    return out


def _signature_stage(sig):
    """The 1c prompt allows five phrases for the signature ("a mechanism", "the
    claim enlarged" …); the library lists the five STAGES. framework_bank.py
    already owns the phrase -> stage table it promotes with, so it is asked
    rather than copied — the two can never disagree."""
    try:
        import framework_bank as FB
        try:
            stages = json.loads(
                FB.FRAMEWORKS_PATH.read_text())["sophistication"]["stages"]
        except Exception:
            stages = []
        return FB._stage_for_signature(sig, stages)
    except Exception:
        return None, ""


def label(doc, E=None):
    """doctrine.json (a dict) -> {element: entry | [entries]}. Pure."""
    E = E or library()
    out = {}
    if not isinstance(doc, dict):
        return out

    # framework/all — the crosswalk row NAME is the library row's name
    cw = doc.get("crosswalk_row")
    fw = doc.get("framework")
    if isinstance(cw, str) and _norm(cw) not in {_norm(x) for x in NOT_SHOWN}:
        out["framework/all"] = _entry(E, "framework", "all", cw)
    else:
        e = _entry(E, "framework", "all", fw if isinstance(fw, str) else "")
        if not e["known"]:
            e["note"] = ("the read named no crosswalk row — a shape described "
                         "in plain words is a candidate row, not a known one")
            e.pop("not_shown", None)
        out["framework/all"] = e

    aw = doc.get("awareness") if isinstance(doc.get("awareness"), dict) else {}
    for end in ("entry", "exit"):
        out[f"doctrine/awareness.{end}"] = _entry(
            E, "doctrine", "awareness", aw.get(end))

    sig = doc.get("sophistication_signature")
    sid, why = _signature_stage(sig if isinstance(sig, str) else "")
    out["doctrine/sophistication"] = _entry(
        E, "doctrine", "sophistication", sig, id_hint=sid,
        note=(why if sid else None))

    secs, seen = [], set()
    for s in doc.get("sections_carried") or []:
        v = s.get("id") if isinstance(s, dict) else s
        if _norm(v) in seen:
            continue
        seen.add(_norm(v))
        secs.append(_entry(E, "doctrine", "section", v))
    out["doctrine/section"] = secs

    techs, seen = [], set()
    for t in doc.get("techniques") or []:
        v = t.get("technique") if isinstance(t, dict) else t
        if _norm(v) in seen:
            continue
        seen.add(_norm(v))
        techs.append(_entry(E, "doctrine", "technique", v))
    out["doctrine/technique"] = techs

    dl = doc.get("delivery") if isinstance(doc.get("delivery"), dict) else {}
    for dial in DELIVERY_DIALS:
        v = dl.get(dial)
        if isinstance(v, list):
            out[f"delivery/{dial}"] = [_entry(E, "delivery", dial, x) for x in v]
        else:
            out[f"delivery/{dial}"] = _entry(E, "delivery", dial, v)
    return out


def _flat(elements):
    for k, v in elements.items():
        for e in (v if isinstance(v, list) else [v]):
            yield k, e


def check_run(run_dir, E=None, write=True):
    """Read <run>/doctrine.json, write <run>/elements.json. -> (report, note).
    Never raises — a label check must not cost anybody a run."""
    run_dir = Path(run_dir)
    if os.environ.get(OFF_ENV):
        return None, "switched off"
    try:
        f = run_dir / "doctrine.json"
        if not f.is_file():
            return None, "no doctrine.json"
        doc = json.loads(f.read_text())
        if not isinstance(doc, dict) or doc.get("error"):
            return None, "doctrine.json holds an error, not a reading"
        elements = label(doc, E)
        unknown = [f"{k}: {e['value']}" for k, e in _flat(elements)
                   if not e["known"] and not e.get("not_shown")]
        flat = list(_flat(elements))
        report = {
            "what": "the run's doctrine labels, checked against the element library",
            "library": "components/elements/library",
            "checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "composed": bool(doc.get("composed")),
            "counts": {"known": sum(1 for _, e in flat if e["known"]),
                       "unknown": len(unknown),
                       "not_shown": sum(1 for _, e in flat if e.get("not_shown"))},
            "unknown": unknown,
            "elements": elements,
            "not_labelled": {
                "format/video": "stage 1c does not read it — see "
                                "prompts/proposed/ for the one-prompt change",
                "structure/video": "stage 1c does not read it — see "
                                   "prompts/proposed/ for the one-prompt change"},
        }
        # a v3 doctrine block that DOES carry them is labelled like the rest
        for key, asset_key in (("format", "format/video"),
                               ("structure", "structure/video")):
            if isinstance(doc.get(key), str):
                el, asset = asset_key.split("/")
                e = _entry(E or library(), el, asset, doc[key])
                report["elements"][asset_key] = e
                report["not_labelled"].pop(asset_key, None)
                if e["known"]:
                    report["counts"]["known"] += 1
                elif e.get("not_shown"):
                    report["counts"]["not_shown"] += 1
                else:
                    report["counts"]["unknown"] += 1
                    report["unknown"].append(f"{asset_key}: {e['value']}")
        if not report["not_labelled"]:
            report.pop("not_labelled")
        if write:
            out = run_dir / "elements.json"
            same = False
            if out.is_file():
                # the bank re-checks every run on every refresh; a file whose
                # labels have not moved is left alone rather than re-stamped
                try:
                    was = json.loads(out.read_text())
                    same = ({k: v for k, v in was.items() if k != "checked"} ==
                            {k: v for k, v in report.items() if k != "checked"})
                except Exception:
                    same = False
            if not same:
                out.write_text(
                    json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        c = report["counts"]
        note = (f"{c['known']} label(s) known to the library"
                + (f", {c['unknown']} UNKNOWN (recorded, not dropped): "
                   + "; ".join(report["unknown"])[:160] if c["unknown"] else ""))
        return report, note
    except Exception as e:                                   # never fatal
        return None, f"{type(e).__name__}: {e}"


def check_all(root=None):
    """Every run under the runs folder that holds a doctrine.json. Called by
    framework_bank.refresh(). -> (checked, with_unknowns). Never raises."""
    if os.environ.get(OFF_ENV):
        return 0, 0
    try:
        import framework_bank as FB
        base = FB.runs_root(root)
        E = library()
    except Exception:
        return 0, 0
    n = bad = 0
    for d in sorted(p for p in Path(base).iterdir() if p.is_dir()):
        if not (d / "doctrine.json").is_file():
            continue
        report, _ = check_run(d, E)
        if report:
            n += 1
            bad += 1 if report["counts"]["unknown"] else 0
    return n, bad


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        import framework_bank as FB
        d = FB.find_run(argv[0])
        if d is None:
            raise SystemExit(f"no run called '{argv[0]}'")
        report, note = check_run(d)
        print(json.dumps(report, indent=2, ensure_ascii=False) if report else note)
        return 0
    n, bad = check_all()
    print(f"{n} run(s) labelled against the element library, "
          f"{bad} with at least one unknown value")
    return 0


if __name__ == "__main__":
    sys.exit(main())
