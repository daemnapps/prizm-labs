#!/usr/bin/env python3
"""The gates this chain runs. Three of the five shared gates
(`components/quality-checks`) apply to a page teardown:

    inputs     before any model runs     the saved page is on file and, once
                                         reduced, still has words in it; the
                                         brand is a real folder; every step has
                                         a prompt; the element lists it labels
                                         against exist
    elements   after the labelling step  the page format, the framework and
                                         every section's label is a real row in
                                         the element library, or an honest
                                         `none-fits` with a proposed row
    copy       after the read step, and  the record arrived in its labelled
               again after the construct parts; the construct carries none of
                                         the source's names (brand, product,
                                         people), no money figure at all, none
                                         of the source's own figures, no page
                                         furniture, no source defect, no
                                         template tag, no UNFILLED note, and
                                         ends on its LEFT OUT line

`hold()` writes the gate-keyed `check.json` into the run and raises `Held`.
**A held run says why**: the problems are in `check.json` and printed when it
happens.

    gates.py <run folder>          print a run's check.json, plainly
"""
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import paths as P                                             # noqa: E402
import furniture as F                                         # noqa: E402
import elements_label as L                                    # noqa: E402

MIN_WORDS = 40          # a saved page that reduces to less than this is a shell, not a page


def quality():
    """The shared checks — components/quality-checks."""
    if str(P.QUALITY) not in sys.path:
        sys.path.append(str(P.QUALITY))
    import quality_checks as Q
    return Q


def input_problems(source, brand, steps, prompts_dir=None):
    """Everything the run needs, checked without spending anything."""
    out = []
    src = Path(source)
    if not src.is_file():
        out.append(f"the saved page is not on file: {src} (this tool does not fetch — save the page first)")
    else:
        words = len(F.load(src)["text"].split())
        if words < MIN_WORDS:
            out.append(f"the saved page has almost nothing to read once reduced ({words} words) — "
                       f"it may be a shell that fills itself by script; save the page as it renders")
    if not (P.BRANDS / brand).is_dir():
        out.append(f"`{brand}` is not a brand folder under brands/ — known: {', '.join(P.known_brands()) or 'none'}")
    if str(P.RUN_KIT) not in sys.path:
        sys.path.append(str(P.RUN_KIT))
    from run_kit import prompts as KP
    for s in steps:
        try:
            KP.latest(prompts_dir or P.PROMPTS, s["key"])
        except KP.PromptError as e:
            out.append(str(e))
    out += L.missing_lists()
    return out


def inputs_gate(run, problems):
    return quality().hold("inputs", problems, run)


def record_gate(run, record):
    """After the read step: the record must arrive in its labelled parts, or
    nothing downstream can tell the argument from the furniture."""
    return quality().hold("copy", F.record_problems(record), run)


def elements_gate(run, problems):
    return quality().hold("elements", problems, run)


def construct_gate(run, construct, strip, names):
    Q = quality()
    return Q.hold("copy", Q.unfilled_check(construct) + F.construct_problems(construct, strip, names), run)


def state(run):
    f = Path(run) / "check.json"
    try:
        return json.loads(f.read_text()) if f.is_file() else {}
    except ValueError:
        return {}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    st = state(sys.argv[1])
    if not st:
        print(f"{sys.argv[1]}: no gate has run yet")
    for g, v in st.items():
        print(f"{g}: {v.get('result')}")
        for p in v.get("problems", []):
            print(f"   - {p}")
