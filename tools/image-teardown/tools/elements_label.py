#!/usr/bin/env python3
"""Which library elements a torn-down ad IS — asked of the element library,
never guessed.

    elements_label.py candidates            print the rows stage 2b is handed
    elements_label.py read <run>            re-read out/02b-elements.md → out/elements.json

Stage 2b hands the model the teardown record and the candidate rows (id ·
name · what) out of `components/elements/library/`. The answer comes back as
one fenced ```ELEMENTS block. This file is the other half: it reads that
block, asks `components/elements/machine/elements.py` `check()` whether every
id is a real row on its own list, and writes `out/elements.json` in the run.

**An id that is not in the library is REFUSED and recorded — never guessed,
never "closest match".** `none-fits` is a legitimate answer: it carries a
one-line proposed row, which is how the library grows. Nothing here edits the
library; a proposed row is a note for the person who curates it.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

# The four labels every image teardown records, as (element, asset).
LISTS = [("format", "image"), ("style", "image"), ("framework", "all"),
         ("doctrine", "awareness")]
NONE = "none-fits"
ANSWER = "02b-elements.md"          # the model's reply, as written
RECORD = "elements.json"            # what the code accepted, refused, and why


def library():
    """The element library's own reader — components/elements/machine/elements.py."""
    machine = P.ELEMENTS / "machine"
    if str(machine) not in sys.path:
        sys.path.insert(0, str(machine))
    import elements as E
    return E


def key(el, asset):
    return f"{el}/{asset}"


def candidates():
    """The candidate rows as the prompt is handed them: id · name · what."""
    E = library()
    out = []
    for el, asset in LISTS:
        out.append(f"### {key(el, asset)}\n")
        out.append("| id | name | what it is |\n|---|---|---|")
        for r in E.rows(el, asset):
            what = re.sub(r"\s+", " ", str(r.get("what") or "")).replace("|", "/")
            out.append(f"| `{r['id']}` | {r.get('name') or ''} | {what} |")
        out.append("")
    return "\n".join(out) + "\n"


LETTERFORM = ("letterform", "image")


def letterform_candidates():
    """The letterform rows as stage 1 is handed them: id · name · what · tell.

    Stage 1 is the only stage that sees the picture, so it is the only stage
    that can label how the letters are made. It gets the same shape 2b gets,
    plus the `how to see it` column — a labeller looking at pixels needs the
    visual tell, where 2b is reading a record that already made the call.
    """
    E = library()
    out = ["| id | name | what it is | how to see it |", "|---|---|---|---|"]
    for r in E.rows(*LETTERFORM):
        x = r.get("extra") or {}
        cell = lambda s: re.sub(r"\s+", " ", str(s or "")).replace("|", "/")
        out.append(f"| `{r['id']}` | {cell(r.get('name'))} | {cell(r.get('what'))} "
                   f"| {cell(x.get('how_to_see_it'))} |")
    return "\n".join(out) + "\n"


def write_letterform_candidates(run):
    f = Path(run) / "out" / ".letterform-candidates.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(letterform_candidates())
    return f


def letterforms_used(run):
    """Every `letterform:` line the teardown wrote, and every row it proposed.

    Damon, 2026-09-25: a thing the bank does not hold yet gets a NAME so the
    work carries on. The names are only useful if somebody can find them, so
    each run records what it used and what it had to invent, and a proposed
    row is a row waiting for Damon rather than a thing that quietly vanished.
    """
    f = Path(run) / "out" / "01-teardown.md"
    if not f.is_file():
        return {"used": [], "proposed": []}
    t = f.read_text(errors="replace")
    used, proposed = [], []
    for m in re.finditer(r"letterform:\s*`?([a-z0-9][a-z0-9-]*|none-fits)`?\s*(?:\u2014|--|-)\s*(.+)",
                         t, re.I):
        # The field is written inside a markdown table cell, so the phrase
        # runs on into the cell's closing backtick and pipe. Cut it there.
        phrase = re.split(r"`|\||$", m.group(2), 1)[0].strip().rstrip(".,;")
        used.append({"id": m.group(1).lower(), "phrase": phrase[:160]})
    for m in re.finditer(r"letterform-proposed:\s*(.+)", t, re.I):
        # same markdown-table trim as the phrase above
        proposed.append(re.split(r"`|\||$", m.group(1), 1)[0].strip()[:200])
    known = {r["id"] for r in library().rows(*LETTERFORM)}
    unknown = sorted({u["id"] for u in used} - known - {"none-fits"})
    return {"used": used, "proposed": proposed, "unknown_ids": unknown}


def write_candidates(run):
    f = Path(run) / "out" / ".element-candidates.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(candidates())
    return f


def parse(text):
    """The ```ELEMENTS block as a dict. Raises ValueError saying what is wrong."""
    m = re.search(r"```ELEMENTS\s*\n(.*?)```", text or "", re.S)
    if not m:
        raise ValueError("the labelling answer carries no ```ELEMENTS block")
    try:
        got = json.loads(m.group(1))
    except ValueError as e:
        raise ValueError(f"the ELEMENTS block is not valid JSON ({e})")
    if not isinstance(got, dict):
        raise ValueError("the ELEMENTS block is not a JSON object")
    return got


def validate(answer):
    """(record, problems). Every id is checked against its own list by the
    library; what the library does not hold is refused, with the reason."""
    E = library()
    labels, why, proposed, refused, problems = {}, {}, {}, [], []
    for el, asset in LISTS:
        k = key(el, asset)
        a = answer.get(k)
        if isinstance(a, str):
            a = {"id": a}
        if not isinstance(a, dict) or not a.get("id"):
            problems.append(f"{k}: the answer gave no id")
            continue
        rid = str(a["id"]).strip().strip("`")
        if a.get("why"):
            why[k] = str(a["why"]).strip()
        if rid == NONE:
            line = str(a.get("proposed") or "").strip()
            if not line:
                problems.append(f"{k}: `{NONE}` with no proposed row — "
                                f"say what the new row would be, in one line")
            proposed[k] = line or None
            labels[k] = NONE
            continue
        bad = E.check({(el, asset): rid})
        if bad:
            refused.append({"list": k, "id": rid, "reason": bad[0]})
            problems.append(f"{k}: REFUSED — {bad[0]}")
            continue
        labels[k] = rid
    extra = sorted(set(answer) - {key(*l) for l in LISTS})
    if extra:
        problems.append("the answer labels lists nobody asked for: " + ", ".join(extra))
    record = {"labels": labels, "why": why, "proposed": proposed, "refused": refused,
              "library": "components/elements/library",
              "lists": [key(*l) for l in LISTS]}
    return record, problems


def read(run, prompt_name=None):
    """out/02b-elements.md → out/elements.json. Returns (record, problems).
    The record is written whether or not it is clean: a refusal is data."""
    run = Path(run)
    src = run / "out" / ANSWER
    try:
        record, problems = validate(parse(src.read_text() if src.is_file() else ""))
    except ValueError as e:
        record = {"labels": {}, "why": {}, "proposed": {}, "refused": [],
                  "library": "components/elements/library",
                  "lists": [key(*l) for l in LISTS]}
        problems = [str(e)]
    record = dict({"run": run.name, "prompt": prompt_name}, **record)
    record["problems"] = problems
    (run / "out" / RECORD).write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    return record, problems


if __name__ == "__main__":
    if sys.argv[1:2] == ["candidates"]:
        print(candidates())
    elif sys.argv[1:2] == ["read"] and len(sys.argv) == 3:
        r = Path(sys.argv[2])
        r = r if r.is_absolute() else P.RUNS / r.name
        rec, probs = read(r)
        print(json.dumps(rec, indent=1, ensure_ascii=False))
        sys.exit(2 if probs else 0)
    else:
        print(__doc__)
