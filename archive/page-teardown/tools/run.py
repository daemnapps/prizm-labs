#!/usr/bin/env python3
"""page-teardown — one saved landing page in; its section-by-section read, its
element labels and its construct out.

    python3 tools/run.py <saved page file> --brand <brand> [--source-url URL] [--label L]
                         [--dry-run] [--rerun-from tear1|tear2|tear3] [--model M]

Takes a landing page ALREADY SAVED to a file — an `.html` save, or a `.txt`/`.md`
text capture. This tool does not fetch. Makes three things, filed to
`runs/page-teardown/<brand>/<label>/`:

    tear1--record.md      SECTIONS AS READ / PAGE FURNITURE / SOURCE DEFECTS, kept apart
    elements.json         which library rows the page IS — its format, its
                          framework, and one section label per section
    tear3--construct.md   the page's construct — the structure with the source's
                          subject, names and figures stripped, ready for any
                          brand to be injected

Does not write a page. Does not build, lay out or deploy one.

Built on `components/run-kit` (`Chain`): every prompt saved as sent, a finished
step reused, `run.json`, and a dry run that spends NOTHING — no model call, no
file outside a temp folder that is removed. An `.html` save is reduced to
readable lines in code, for free, before any model reads it.

There is no default brand. `--brand` names where the run files and whose own
names the construct is checked against.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import paths as P                                             # noqa: E402
import furniture as F                                         # noqa: E402
import elements_label as L                                    # noqa: E402
import gates as G                                             # noqa: E402

sys.path.append(str(P.RUN_KIT))
sys.path.append(str(P.QUALITY))
from run_kit import model as M                                # noqa: E402
from run_kit import prompts as KP                             # noqa: E402
from run_kit.stage import Chain                               # noqa: E402
import quality_checks as Q                                    # noqa: E402

TOOL = P.TOOL
# Declared once. tier: reads = the answer is in the input · checks = applies
# rules that are written down · designs = makes the calls nobody wrote down.
# The model behind each tier is components/run-kit model.TIERS — no id here.
# A prompt past run-kit's small-window size steps up on its own (model.pick).
STEPS = [
    {"key": "tear1", "name": "Read the page — sections, furniture, defects", "tier": "reads", "label": "record"},
    {"key": "tear2", "name": "Label its elements", "tier": "checks", "label": "labels", "depends": ["tear1"]},
    {"key": "tear3", "name": "The construct", "tier": "designs", "label": "construct", "depends": ["tear1"]},
]


def sha12(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:12]


def _old_source_sha(out):
    try:
        return json.loads((Path(out) / "run.json").read_text()).get("assignment", {}).get("source_sha256_12")
    except (OSError, ValueError):
        return None


def main(argv=None, runner=None, echo=print):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="the SAVED page to tear down: an .html save, or a .txt/.md text capture")
    ap.add_argument("--brand", required=True,
                    help="REQUIRED — there is no default brand. Where the run files, and whose own names the "
                         "construct is checked against")
    ap.add_argument("--source-url", help="where the page was saved from — recorded, never fetched")
    ap.add_argument("--label", help="the run's label (default: the saved file's folder or name)")
    ap.add_argument("--dry-run", "--dry", dest="dry", action="store_true",
                    help="spend nothing: show the inputs, sizes, the model per step and where it would file")
    ap.add_argument("--rerun-from", choices=[s["key"] for s in STEPS])
    ap.add_argument("--model", help="force one model for every step (default: each step's tier)")
    a = ap.parse_args(argv)

    src = Path(a.source)
    label = a.label or (src.parent.name if src.stem.lower() in ("page", "index") and src.parent.name else src.stem)
    files_to = P.record_dir(a.brand, label)
    problems = G.input_problems(a.source, a.brand, STEPS)

    if a.dry:
        echo(f"DRY RUN — page-teardown · brand {a.brand} · label {label}")
        echo(f"  source      {P.rel(a.source)}" + (f"  (saved from {a.source_url})" if a.source_url else ""))
        if problems:
            for p in problems:
                echo(f"  MISSING     {p}")
            echo("  nothing was spent and nothing was written.")
            return 1
    else:
        files_to.mkdir(parents=True, exist_ok=True)
        try:
            G.inputs_gate(files_to, problems)
        except Q.Held as e:
            echo(str(e))
            return 2

    page = F.load(a.source)
    source = page["text"]
    found = F.scan(page)
    code_format = L.code_format(source, label, a.source_url)
    names = sorted(set(F.code_names(page, a.source_url)) | set(F.brand_names(a.brand)))
    furniture_lines = sum(f["count"] for f in found["furniture"])
    assignment = {"source": P.rel(a.source), "source_url": a.source_url, "source_kind": page["kind"],
                  "source_sha256_12": sha12(source), "chars_on_file": page["raw_chars"], "chars_as_read": len(source),
                  "second_copy_lines_dropped": page["second_copy_lines_dropped"],
                  "code_found": {"furniture_lines": furniture_lines, "defects": len(found["defects"]),
                                 "format": code_format, "site_name": page["site_name"] or None}}

    tmp = Path(tempfile.mkdtemp(prefix="page-teardown-dry-")) if a.dry else None
    out = tmp or files_to
    rerun = a.rerun_from
    if not a.dry and not rerun and _old_source_sha(out) not in (None, assignment["source_sha256_12"]):
        echo("     the saved page changed since the last run under this label — reading it again")
        rerun = "tear1"

    try:
        chain = Chain(TOOL, a.brand, label, out, P.PROMPTS, STEPS, assignment=assignment, dry=a.dry,
                      rerun_from=rerun, force_model=a.model, runner=runner, echo=echo)
        if a.dry:
            echo(f"  page        {page['kind']}: {page['raw_chars']:,} chars on file → {len(source):,} chars as read "
                 f"({len(source.splitlines()):,} lines"
                 + (f"; a second copy of the page, {page['second_copy_lines_dropped']} lines, dropped" if page["second_copy_lines_dropped"] else "") + ")")
            echo(f"  code found  {furniture_lines} furniture line(s) · {len(found['defects'])} defect(s) · "
                 f"format as the classifier reads it: {code_format or 'could not say'}")
            echo(f"  names       the construct would be checked against {len(names)} name(s) the code already knows, "
                 f"plus every name the read step lists")
        else:
            (out / "source--as-read.md").write_text(
                f"# The page as the read step was handed it\n\nFrom `{P.rel(a.source)}`"
                + (f" · saved from {a.source_url}" if a.source_url else "") + f" · {page['kind']}.\n\n```\n{F.numbered(source)}```\n")

        # 1 — the read: sections, furniture and defects kept apart
        record = chain.run("tear1", source_url=a.source_url or "(not given)", code_findings=F.findings_text(found),
                           source=F.numbered(source))
        strip = {"furniture_words": [], "defects": [], "names": [], "figures": []}
        if not a.dry:
            G.record_gate(out, record)
            strip = F.strip_block(record)
            (out / "strip.json").write_text(json.dumps({"code_found": found, "code_names": names, "record_says": strip},
                                                       indent=1, ensure_ascii=False) + "\n")
        sections = F.sections_only(record)
        section_ids = F.section_ids(record)

        # 2 — the labels: asked of the element library, never invented
        answer = chain.run("tear2", candidates=L.candidates(), record=sections,
                           code_format=code_format or "(the classifier could not say)")
        if not a.dry:
            labels, label_problems = L.read(answer, section_ids)
            fk = L.key(*L.FORMAT)
            labels["code_format"] = code_format
            labels["format_agrees_with_code"] = (None if not code_format or fk not in labels["labels"]
                                                 else labels["labels"][fk] == code_format)
            (out / "elements.json").write_text(json.dumps(labels, indent=1, ensure_ascii=False) + "\n")
            chain.record.state["elements"] = {"labels": labels["labels"], "proposed": labels["proposed"],
                                              "refused": labels["refused"], "code_format": code_format}
            chain.record.save()
            G.elements_gate(out, label_problems)

        # 3 — the construct: from the sections only
        construct = chain.run("tear3", record=sections)
        if not a.dry:
            G.construct_gate(out, construct, strip, names)
            chain.record.state["state"] = "filed"
            chain.record.save()
    except Q.Held as e:
        echo(str(e))
        echo(f"  the run is HELD — why is in {P.rel(out / 'check.json')}. "
             f"Fix the prompt (as a new -vN- file) or the saved page, then run again with --rerun-from <step>.")
        return 2
    except (KP.PromptError, M.UsageLimit, M.StageFailed) as e:
        echo(f"STOPPED: {e}")
        return 3
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    if a.dry:
        echo("  sizes       steps 2 and 3 are sized without the record, which a dry run does not have — "
             "a real record adds roughly the page's own length to each")
        echo(f"  would file  {P.rel(files_to)}/  (source--as-read.md · tear1--record.md · elements.json · "
             f"tear3--construct.md · strip.json · run.json · check.json · every prompt as sent)")
        echo(f"  spent       0 model calls — a real run makes up to {len(STEPS)}")
        return 0
    echo(f"done -> {P.rel(out)}  ({chain.calls} model call(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
