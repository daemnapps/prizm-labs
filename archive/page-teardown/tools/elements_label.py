#!/usr/bin/env python3
"""Which library elements a torn-down page IS — asked of the element library,
never guessed.

    elements_label.py candidates        print the rows the labelling step is handed

The labelling step is handed the page's record and the candidate rows (id ·
name · what) out of `components/elements/library/`. Its answer comes back as
one ELEMENTS block. This file is the other half: it reads that block
(tolerantly — `slots.json_slot`), asks `components/elements/machine/elements.py`
`check()` whether every id is a real row on its own list, and returns the
record the run files as `elements.json`.

Three labels:

    format/page         one id — what kind of page it is
    framework/all       one id — the argument's plan (labelled only while the
                        library holds a framework list)
    doctrine/section    one id PER SECTION the read step numbered (S1, S2, …)

**An id that is not in the library is REFUSED, with the real ids named — never
guessed, never "closest match".** `none-fits` is a legitimate answer: it
carries a one-line proposed row, which is recorded in the run and is how the
library grows. Nothing here edits the library. (Same pattern as
`email-teardown/tools/elements_label.py`.)
"""
import importlib.util
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import paths as P                                             # noqa: E402
import slots as S                                             # noqa: E402

FORMAT = ("format", "page")
SECTION = ("doctrine", "section")
FRAMEWORKS = [("framework", "page"), ("framework", "all")]    # the first the library holds
NONE = "none-fits"
BLOCK_NAMES = ("ELEMENTS", "ELEMENT LABELS")


def library():
    """The element library's own reader — components/elements/machine/elements.py."""
    machine = str(P.ELEMENTS / "machine")
    if machine not in sys.path:
        sys.path.append(machine)
    import elements as E
    return E


def key(el, asset):
    return f"{el}/{asset}"


def framework_list():
    E = library()
    for el, asset in FRAMEWORKS:
        try:
            E.rows(el, asset)
            return (el, asset)
        except E.Unknown:
            continue
    return None


def single_lists():
    fw = framework_list()
    return [FORMAT] + ([fw] if fw else [])


def missing_lists():
    """Lists this tool cannot work without that the library does not hold."""
    E = library()
    out = []
    for el, asset in (FORMAT, SECTION):
        try:
            E.rows(el, asset)
        except E.Unknown as e:
            out.append(e.args[0])
    return out


def candidates():
    """The candidate rows as the prompt is handed them: id · name · what."""
    E = library()
    out = []
    for el, asset in single_lists() + [SECTION]:
        out.append(f"### {key(el, asset)}\n")
        out.append("| id | name | what it is |\n|---|---|---|")
        for r in E.rows(el, asset):
            what = re.sub(r"\s+", " ", str(r.get("what") or "")).replace("|", "/")
            out.append(f"| `{r['id']}` | {r.get('name') or ''} | {what} |")
        out.append("")
    return "\n".join(out) + "\n"


def code_format(text, slug, url):
    """What the page classifier (components/naming/classify_pages.py — called,
    never edited) reads the page as. A free second opinion handed to the
    labelling step; None when the classifier is not there or cannot say."""
    try:
        spec = importlib.util.spec_from_file_location("classify_pages", P.CLASSIFIER)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m.page_type(dict(slug=slug or "", title="", text=text or "", url=url or "")) or None
    except Exception:                                          # noqa: BLE001 — a hint, never a dependency
        return None


def parse(text):
    """The ELEMENTS block as a dict. Raises ValueError saying what is wrong."""
    return S.json_slot(text, BLOCK_NAMES, keys=(key(*FORMAT), key(*SECTION)))


def _one(a):
    if isinstance(a, str):
        a = {"id": a}
    if not isinstance(a, dict) or not a.get("id"):
        return None
    return {"id": str(a["id"]).strip().strip("`"), "why": str(a.get("why") or "").strip(),
            "proposed": str(a.get("proposed") or "").strip()}


def _sections(a):
    """[{section, id, why, proposed}] or {"S1": {...} | "id"} → {"S1": {...}}."""
    out = {}
    if isinstance(a, dict):
        a = [dict(v if isinstance(v, dict) else {"id": v}, section=k) for k, v in a.items()]
    for row in a if isinstance(a, list) else []:
        if not isinstance(row, dict):
            continue
        m = re.search(r"S\d+", str(row.get("section") or ""))
        one = _one(row)
        if m and one:
            out[m.group(0)] = one
    return out


def validate(answer, section_ids):
    """(record, problems). Every id is checked against its own list by the
    library; what the library does not hold is refused, with the reason."""
    E = library()
    labels, why, proposed, refused, problems = {}, {}, {}, [], []

    def judge(el, asset, where, one):
        """→ the id to record, or None when refused."""
        k = key(el, asset)
        if one["id"] == NONE:
            if not one["proposed"]:
                problems.append(f"{where}: `{NONE}` with no proposed row — say what the new row would be, in one line")
            return NONE
        bad = E.check({(el, asset): one["id"]})
        if bad:
            refused.append({"list": k, "at": where, "id": one["id"], "reason": bad[0]})
            problems.append(f"{where}: REFUSED — {bad[0]}")
            return None
        return one["id"]

    singles = single_lists()
    used = set()
    for el, asset in singles:
        k = key(el, asset)
        # the key as asked, or the element's bare name (`framework`) — the same answer
        ak = k if k in answer else next((x for x in answer if x == el or x.startswith(el + "/")), k)
        used.add(ak)
        one = _one(answer.get(ak))
        if not one:
            problems.append(f"{k}: the answer gave no id")
            continue
        got = judge(el, asset, k, one)
        if got:
            labels[k] = got
            if one["why"]:
                why[k] = one["why"]
            if got == NONE:
                proposed[k] = one["proposed"] or None

    sk = key(*SECTION)
    said = _sections(answer.get(sk))
    labels[sk], why[sk], proposed[sk] = {}, {}, {}
    if not said:
        problems.append(f"{sk}: the answer labelled no sections")
    for sid in section_ids:
        if sid not in said:
            problems.append(f"{sk} {sid}: the record numbers this section and the answer gave it no id")
            continue
        got = judge(*SECTION, f"{sk} {sid}", said[sid])
        if got:
            labels[sk][sid] = got
            if said[sid]["why"]:
                why[sk][sid] = said[sid]["why"]
            if got == NONE:
                proposed[sk][sid] = said[sid]["proposed"] or None
    ghosts = [s for s in said if s not in section_ids]
    if ghosts:
        problems.append(f"{sk}: the answer labels sections the record does not number: " + ", ".join(ghosts))
    extra = sorted(set(answer) - used - {sk})
    if extra:
        problems.append("the answer labels lists nobody asked for: " + ", ".join(extra))
    if not proposed[sk]:
        proposed.pop(sk)
    record = {"labels": labels, "why": why, "proposed": proposed, "refused": refused,
              "library": "components/elements/library", "lists": [key(*l) for l in singles] + [sk]}
    return record, problems


def read(answer_text, section_ids):
    """The labelling step's answer → (record, problems). A refusal is data:
    the record comes back whether or not it is clean."""
    try:
        record, problems = validate(parse(answer_text), list(section_ids))
    except ValueError as e:
        record = {"labels": {}, "why": {}, "proposed": {}, "refused": [],
                  "library": "components/elements/library", "lists": [key(*l) for l in single_lists()] + [key(*SECTION)]}
        problems = [str(e)]
    record["problems"] = problems
    return record, problems


if __name__ == "__main__":
    if sys.argv[1:2] == ["candidates"]:
        print(candidates())
    else:
        print(__doc__)
