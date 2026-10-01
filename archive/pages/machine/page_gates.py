#!/usr/bin/env python3
"""The gates the page machine runs, on the shared checks and the shared hold.

    inputs     before any model runs   the angle is signed active in the brand's
                                       strategy/angles.json (run.py, as before)
    elements   before any model runs   the page format the classifier read is a
                                       real row in the library's format/page —
                                       unknown is refused, naming the real ids.
                                       After stage 3, the doctrine sections its
                                       SECTIONS CARRIED names are looked up too;
                                       an unknown one is RECORDED, never a stop.
    copy       after the words are     the finished base page and every
               final (stages 3–6)      variation: no UNFILLED note left, and
                                       every price is one the offer files sell

`hold()` (components/quality-checks) writes `check.json` into the run and raises
`Held`. A held run keeps everything it made, says why, and exits 2; `deliver.py`
refuses it unless `--force`.

    python3 page_gates.py <label>      print a run's check.json, plainly

Nothing here calls a model.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_paths as P                                     # noqa: E402


def quality():
    """The shared checks — components/quality-checks."""
    d = str(P.WORKSPACE / "components" / "quality-checks")
    if d not in sys.path:
        sys.path.append(d)
    import quality_checks as Q
    return Q


def library():
    """The element library — components/elements/machine/elements.py."""
    d = str(P.WORKSPACE / "components" / "elements" / "machine")
    if d not in sys.path:
        sys.path.append(d)
    import elements as E
    return E


# ------------------------------------------------------------------ elements

def page_format(fmt):
    """The library's row for a page format, or a refusal naming the real ids."""
    E = library()
    try:
        return E.get("format", "page", fmt)
    except E.Unknown as e:
        sys.exit(f"HELD at the elements gate: {e.args[0]}\n"
                 f"  the classifier (components/naming/classify_pages.py) read a format the library does not hold — "
                 f"nothing was called")


_STOP = r"(CHANGE LOG|NOT CHANGED|SECTIONS CARRIED|DOMINANT TRAIT|SUBSTITUTION LOG|COLLISIONS|THE CHECK|FOR A HUMAN|ONE LINE)"


def _block(text, heading):
    """The body under a `# HEADING` or `**HEADING**` line, up to the next of the
    chain's own output headings."""
    m = re.search(rf"^\s*(?:#+\s*|\*\*){heading}\b[^\n]*$", text or "", re.M | re.I)
    if not m:
        return None
    rest = text[m.end():]
    # the heading line itself may carry the first words after a dash
    end = re.search(rf"^\s*(?:#+\s*|\*\*){_STOP}\b", rest, re.M)
    return rest[:end.start()] if end else rest


def sections_carried(injection):
    """The doctrine sections stage 3 says the page carries → (known, unknown).
    Reads backticked ids when the output uses them, else the label after the
    last dash/colon/arrow on each line. `none` is an honest answer, not an id."""
    E = library()
    ids = {r["id"] for r in E.rows("doctrine", "section")}
    body = _block(injection, "SECTIONS CARRIED")
    if body is None:
        return [], []
    known, unknown = [], []
    for line in body.splitlines():
        line = line.strip().strip("|").strip()
        if not line or set(line) <= set("-|: "):
            continue
        line = re.sub(r"\([^)]*\)", "", line)              # a gloss in brackets is not an id
        ticks = re.findall(r"`([^`]+)`", line)
        cands = ticks or [re.split(r"\s[—–→:-]+\s|→|:\s", line)[-1]]
        for c in cands:
            for part in re.split(r"\s*[,/+&]\s*|\s+and\s+", c):
                v = re.sub(r"[^a-z0-9-]", "", part.strip().lower().replace(" ", "-")).strip("-")
                if not v or v in ("none", "fits-none", "none-fits", "section", "block", "carries"):
                    continue
                if v in ids:
                    if v not in known: known.append(v)
                elif ticks or len(v) <= 30:
                    if v not in unknown: unknown.append(v)
    return known, unknown


# ---------------------------------------------------------------------- copy

def page_part(text):
    """The page itself out of a stage's output — not its change log, its check
    or its notes, which quote the SOURCE page's figures on purpose."""
    for heading in ("THE INJECTED PAGE", "THE PAGE"):
        body = _block(text, heading)
        if body is not None and body.strip():
            return body
    end = re.search(rf"^\s*(?:#+\s*|\*\*){_STOP}\b", text or "", re.M)
    return text[:end.start()] if end else (text or "")


def _json_prices(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and re.search(r"price|amount|cost|total|each|per", k, re.I):
                out.append(f"${v:.2f}")
            else:
                _json_prices(v, out)
    elif isinstance(node, list):
        for v in node:
            _json_prices(v, out)


def offer_text(brand, offer_files):
    """What the page's prices are checked against: the --offer files handed to
    the run, or the brand's own offer bank when none was."""
    files = [P.WORKSPACE / f for f in (offer_files or [])]
    files = [f for f in files if f.is_file()] or [P.WORKSPACE / "brands" / brand / "offers" / "offer-bank.md"]
    parts = []
    for f in files:
        if not f.is_file():
            continue
        txt = f.read_text(errors="ignore")
        parts.append(txt)
        if f.suffix == ".json":                            # a bare 39 in a price field is a price
            try:
                found = []; _json_prices(json.loads(txt), found); parts.append(" ".join(found))
            except ValueError:
                pass
    return "\n".join(parts)


def copy_problems(pieces, offer):
    """pieces: [(name, text)] — the base page and each variation. What HOLDS a page."""
    Q = quality()
    problems = []
    for name, text in pieces:
        problems += [f"{name}: {p}" for p in Q.unfilled_check(page_part(text))]
    return problems


def price_flags(pieces, offer):
    """An offer page carries figures that are not sale prices — "$7 Value", "Save $26",
    a struck-through total — and the shared price check cannot tell them apart. So on a
    page a figure the offer files do not sell is FLAGGED for the reader, never a hold."""
    Q = quality()
    return [f"{name}: {p}" for name, text in pieces for p in Q.price_check(page_part(text), offer)]


def copy_gate(run_dir, pieces, brand, offer_files):
    """Raises Q.Held when the words fail; check.json is written either way, flags with it."""
    Q = quality()
    offer = offer_text(brand, offer_files)
    flags = price_flags(pieces, offer)
    try:
        return Q.hold("copy", copy_problems(pieces, offer), Path(run_dir))
    finally:
        f = Path(run_dir) / "check.json"
        if f.is_file():
            state = json.loads(f.read_text())
            state.setdefault("copy", {})["flags"] = flags
            f.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def held(run_dir):
    """The gates a run is held at → {gate: [problems]}; {} when clean or unchecked."""
    f = Path(run_dir) / "check.json"
    if not f.is_file():
        return {}
    try:
        state = json.loads(f.read_text())
    except ValueError:
        return {"check.json": ["could not be read"]}
    return {g: v.get("problems", []) for g, v in state.items() if isinstance(v, dict) and v.get("result") == "HELD"}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    d = P.need_run(sys.argv[1])
    f = d / "check.json"
    if not f.is_file():
        sys.exit(f"{P.rel(d)}: no check.json — the run has not reached a gate")
    for gate, v in json.loads(f.read_text()).items():
        print(f"{gate}: {v['result']}")
        for p in v.get("problems", []):
            print(f"  - {p}")
