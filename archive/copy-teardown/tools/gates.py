#!/usr/bin/env python3
"""The gates this chain runs. Three of the five shared gates
(`components/quality-checks`) apply to a copy teardown:

    inputs     before any model runs     the source is on file, not empty and
                                         WORDS ONLY (a page, an email, a
                                         picture, a video go to their own
                                         teardown); the brand is a real
                                         folder; every step has a prompt;
                                         every element list it labels against
                                         exists
    elements   after the labelling step  every label is a real row in the
                                         element library, or an honest
                                         `none-fits` with a proposed row
    copy       after the read step, and  the record arrived in its labelled
               again after the construct parts; the construct carries none of
                                         the source's names (brand, product,
                                         person, handle, web address), no
                                         brand on file, no source price, no
                                         source defect, no merge tag, no
                                         UNFILLED note, and ends on its
                                         LEFT OUT line

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
import source_text as S                                       # noqa: E402
import elements_label as L                                    # noqa: E402


def quality():
    """The shared checks — components/quality-checks."""
    if str(P.QUALITY) not in sys.path:
        sys.path.append(str(P.QUALITY))
    import quality_checks as Q
    return Q


def input_problems(source, piped, brand, steps, prompts_dir=None):
    """Everything the run needs, checked without spending anything."""
    out = []
    if source == "-":
        if not (piped or "").strip():
            out.append("no text was piped in — `-` reads the copy from standard input")
        else:
            out += S.not_words_only("-", piped)
    else:
        src = Path(source)
        if not src.is_file():
            out.append(f"the source is not on file: {src}")
        else:
            early = S.not_words_only(source, "")
            if early:
                out += early                                  # never read a picture or a video as text
            else:
                words, _ = S.load(source)
                if not words.strip():
                    out.append(f"the source is empty: {src}")
                out += S.not_words_only(source, words)
    if not (P.BRANDS / brand).is_dir():
        out.append(f"`{brand}` is not a brand folder under brands/ — known: {', '.join(P.known_brands())}")
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
    nothing downstream can tell the copy from the source's own names."""
    return quality().hold("copy", S.record_problems(record), run)


def elements_gate(run, problems):
    return quality().hold("elements", problems, run)


def construct_gate(run, construct, strip, found, source):
    Q = quality()
    return Q.hold("copy", Q.unfilled_check(construct) + S.construct_problems(construct, strip, found, source), run)


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
