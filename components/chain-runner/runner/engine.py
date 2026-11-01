#!/usr/bin/env python3
"""Execute a validated chain spec: order, render, bind, write.

The loop is deliberately small — one pass over `spec.stages`, in array order:

    1. build the stage's input VALUES from its declared refs
       (`@<earlier-stage>` -> that stage's output text; `@<earlier-stage>.
       <field>` -> one fact that stage extracted; `@config.<var>` ->
       a run-config variable)
    2. RENDER the prompt, substituting only declared names
    3. write the rendered prompt under --out (always: it is the audit trail,
       and it is what makes piping inspectable after the fact)
    4. call the model seam with the stage's BOUND model
    5. write the stage output, then any artifacts the seam returned —
       every path through the out-dir jail
    6. EXTRACT the stage's declared fields out of its own output, and fail the
       stage by name if one cannot be read (CR-6)

A stage carrying a `when:` gate (CR-5) is judged BEFORE step 1: the predicate
reads one field an earlier stage extracted, and a stage whose gate does not hold
does not run. It is still RECORDED — a `skipped_by_gate` row stating the
predicate and the value it read — because "this stage did not run, and here is
what decided that" is a fact about the run, and a run record with a row quietly
missing from it is a record that cannot be read without the chain beside it.

DETERMINISM IS PART OF THE CONTRACT. `run.json` carries no wall clock and no
elapsed time, so the same chain over the same config produces byte-identical
output; the clock lives in `stamp.json`, which `--no-stamp` omits. That is the
atlas precedent, and it is what makes "did this run change anything" a diff
rather than a judgement.

FAILURE IS LOUD AND LOCAL. A missing config variable, an undeclared
placeholder, or an out-dir violation stops the run, names the stage and the
thing, and leaves `FAILED.txt` under --out saying what happened. Partial
output is kept on purpose: the question after a failed run is always "how far
did it get", and deleting the evidence to leave a tidy directory answers it
with nothing.
"""

from __future__ import annotations

import re

from . import models
from . import spec as specmod
from .outdir import OutDirViolation, sha256_text

RECORD_SCHEMA = 1

# A heading line, for `#pick`'s block boundary: an ATX heading, or a line that
# is entirely bold. Both, because a model asked for numbered sections answers in
# either and a boundary rule that knows only one of them silently swallows the
# rest of the document.
HEADING_RE = re.compile(r"^\s*(?:#{1,6}\s|\*\*.+\*\*\s*$)")
# `VERSION <n>` anywhere in a heading's text, however it is decorated —
# `## VERSION 0`, `**2. VERSION 0 — THE CONTROL**`.
VERSION_RE = re.compile(r"\bVERSION\s+(\d+)\b", re.I)

# `@{name}` with `@@{name}` as the literal escape. One pass, so an escape can
# never be re-substituted by a later pass.
AT_BRACE = re.compile(r"@@\{([A-Za-z0-9_.\-]+)\}|@\{([A-Za-z0-9_.\-]+)\}")
# `{{name}}`. No escape form — a chain needing a literal `{{` uses at-brace.
CURLY = re.compile(r"\{\{([A-Za-z0-9_.\-]+)\}\}")
# `{name}`, and DELIBERATELY only `[a-z0-9_]` inside the braces. This is the
# dialect of a chain imported at a pin (CR-2), and its token grammar is the
# imported machine's own, character for character — that machine substitutes on
# `re.findall(r"\{([a-z0-9_]+)\}", template)` and passes everything else
# through. Matching more would make our render fatal on `{Scene 3}`-shaped prose
# the source treats as text: a parity difference invented here rather than
# inherited, which is the one kind this component must never introduce.
SINGLE_CURLY = re.compile(r"\{([a-z0-9_]+)\}")

# Each dialect's matcher and how to read a name out of one of its matches. The
# engine looks a chain's declared spelling up here and does nothing else with
# it — there is no branch anywhere else, and no chain is named.
DIALECTS = {
    "curly": (CURLY, lambda m: (None, m.group(1))),
    "single-curly": (SINGLE_CURLY, lambda m: (None, m.group(1))),
    "at-brace": (AT_BRACE, lambda m: (m.group(1), m.group(2))),
}


class RunError(Exception):
    """A chain that validated but cannot run on THIS config. Distinct from
    ChainSpecError on purpose: one is a broken chain, the other is a chain
    invoked wrongly, and telling a caller which is which is most of the value
    of an error message."""


def render(template, values, placeholder_style, stage_key):
    """Substitute declared names only. An undeclared placeholder is fatal.

    Fatal rather than left-as-is because the alternative is a prompt that ships
    the literal text `@{transcript}` to a model and produces confident nonsense
    — the most expensive kind of silent failure a chain has.

    `placeholder_style` is the chain's DECLARED dialect (spec.PLACEHOLDER_STYLES)
    and the only thing that selects a matcher. It is declared per chain and
    never sniffed from the text: guessing a dialect off a prompt body is how a
    copied prompt silently renders differently from the machine it was copied
    from.
    """
    missing = []
    matcher, read = DIALECTS[placeholder_style]

    def replace(match):
        escaped, name = read(match)
        if escaped is not None:
            return "@{" + escaped + "}"
        if name in values:
            return values[name]
        missing.append(name)
        return match.group(0)

    rendered = matcher.sub(replace, template)

    if missing:
        raise RunError(
            "stage {0!r}: prompt uses undeclared placeholder(s) {1}. Declare "
            "them in the stage's `inputs` (declared piping is the contract); "
            "declared here: {2}".format(
                stage_key, ", ".join(sorted(set(missing))),
                ", ".join(sorted(values)) or "none"))
    return rendered


def used_names(template, placeholder_style):
    """Which declared names a template actually references — so the run record
    can report an input that is piped and never read."""
    matcher, read = DIALECTS[placeholder_style]
    names = set()
    for match in matcher.finditer(template):
        escaped, name = read(match)
        if escaped is None and name:
            names.add(name)
    return names


def pick_control(text, stage_key, name):
    """`@<stage>#pick` — the CONTROL VERSION out of a stage's output.

    A stage that produces a control plus variations writes them as headed
    sections; the control is the LOWEST-NUMBERED `VERSION <n>` heading in the
    output, and its block runs to the next heading of any kind. That is the
    whole rule, and it is a text rule over any stage's output — the engine
    knows no chain, and `#pick` on a stage that happens to produce one version
    is simply a chain declaring a selector it does not need.

    NO SILENT FALLBACK. An output with no version heading raises, naming the
    stage: piping the whole output where a chain asked for one version is the
    same class of failure as shipping an unsubstituted `@{token}` to a model —
    plausible text, wrong content, discovered late and expensively.

    Where a human pick exists it OUTRANKS this rule; the engine has no human,
    so it takes the control, which is exactly what the machine these chains
    were imported from records as the no-human-picked deviation.
    """
    lines = text.split("\n")
    headings = [i for i, line in enumerate(lines) if HEADING_RE.match(line)]
    versions = []
    for i in headings:
        found = VERSION_RE.search(lines[i])
        if found:
            versions.append((int(found.group(1)), i))
    if not versions:
        raise RunError(
            "stage {0!r}: input {1!r} asks for the control version of an output "
            "that declares no versions — no `VERSION <n>` heading in it. A "
            "'#pick' over an output with nothing to pick from must fail here "
            "rather than quietly pipe the whole thing.".format(stage_key, name))
    versions.sort()
    start = versions[0][1]
    end = len(lines)
    for i in headings:
        if i > start:
            end = i
            break
    return "\n".join(lines[start:end]).strip()


# Decoration a model wraps a labelled line in when it is answering in
# markdown — `**LANE:** ORGANIC`, `## LANE: ORGANIC`, `- LANE: ORGANIC`. It is
# stripped off the LABEL side so a field declared as `LANE` reads the line a
# model actually wrote, rather than failing on formatting nobody asked for.
LABEL_DECORATION = " \t*#->"


def extract_fields(stage, text):
    """A stage's declared fields, read out of that stage's OWN output (CR-6).

    Returns {name: value} — never a partial map, because the first field that
    cannot be read raises. THAT IS THE POINT OF THE CARD: a field is what a
    later stage routes on, and an unreadable field becoming an empty string is
    a run that quietly takes the wrong branch and looks fine doing it. So
    failure is loud, it names the stage AND the field, and there is no default.

    The engine attaches no meaning to any field name. `lane`, `format`,
    `avatar` are opaque to it exactly as run-config variable names are: it
    knows a name and a parse rule, and nothing else.
    """
    out = {}
    for name in sorted(stage.fields):
        entry = stage.fields[name]
        if entry["from"] == "labelled-line":
            value, why = _labelled_line(text, entry["label"])
        else:
            value, why = _captured(text, entry["pattern"])
        if value is None:
            raise RunError(
                "stage {0!r}: field {1!r} could not be read out of the stage's "
                "own output — {2}. An extractable field that cannot be read "
                "FAILS THE STAGE by name; it never becomes an empty value, "
                "because a later stage routing on an empty value is a run that "
                "takes the wrong branch and looks fine doing it."
                .format(stage.key, name, why))
        out[name] = value
    return out


def _labelled_line(text, label):
    """(value, None) or (None, why) — `LABEL: value` off one line.

    The FIRST line carrying that label with something after the colon wins. A
    label that appears but is always empty is reported as its own failure: "the
    model answered the question with nothing" and "the model never answered the
    question" are different facts, and telling them apart is the difference
    between fixing a prompt and fixing a chain.
    """
    wanted = label.strip().lower()
    seen = False
    for line in text.split("\n"):
        head, sep, rest = line.strip().partition(":")
        if not sep or head.strip(LABEL_DECORATION).strip().lower() != wanted:
            continue
        seen = True
        value = rest.strip()
        if value.startswith("**"):
            value = value[2:].strip()
        if value:
            return value, None
    if seen:
        return None, ("the line(s) labelled {0!r} carry nothing after the colon "
                      "— an empty answer is not a value".format(label))
    return None, "no line labelled {0!r} in it".format(label)


def _captured(text, label_pattern):
    """(value, None) or (None, why) — the one capture group, first match.

    `re.M` so that `^` and `$` mean line boundaries, which is what a chain
    author writing `^FORMAT:` means. The group count was checked at load time,
    so there is exactly one group here by construction.
    """
    found = re.search(label_pattern, text, re.M)
    if found is None:
        return None, "the pattern {0!r} matched nothing".format(label_pattern)
    value = (found.group(1) or "").strip()
    if not value:
        return None, ("the pattern {0!r} matched, but captured an empty value"
                      .format(label_pattern))
    return value, None


def fan_in(pairs):
    """`@<stage>*` — every member's output of one stage, in member order.

    `pairs` is [(member name, output text)] in the run's declared member order.
    A NAMED member gets a header line so a downstream stage can tell whose
    output it is reading; the single UNNAMED member of a run that declared no
    group gets none, which makes `@x*` and `@x` byte-identical on a one-member
    run. That coincidence is deliberate and load-bearing: it is what lets a
    chain declare the fan-in it really means and still be run, unchanged, on
    one item — and it is the behaviour the parity harness already predicted for
    a single-video run.
    """
    blocks = []
    for member, text in pairs:
        if member:
            blocks.append("--- member: {0} ---\n{1}".format(member, text))
        else:
            blocks.append(text)
    return "\n\n".join(blocks)


def run(spec, out, config, runner, model_runner_name="stub", stamp=None,
        members=()):
    """Execute `spec` into `out` (an OutDir). Returns the run record dict.

    `config` is the run-config: a flat map of opaque variable names to string
    values. The engine attaches no meaning to any name — brand-shaped facts
    arrive here and nowhere else (workspace rule 7).

    `members` are the run's GROUP MEMBERS: opaque names, in order. A member-
    scoped stage runs once per member and writes under `members/<name>/`; a
    group-scoped stage runs once and reads every member through `*`. A run that
    declares no members has exactly ONE, unnamed, and every path is what it was
    before members existed — the feature costs an existing chain nothing.
    """
    member_list = list(members) or [""]
    scope_of = dict((stage.key, stage.scope) for stage in spec.stages)
    outputs = {}                        # (stage key, member or None) -> text
    fields = {}                         # (stage key, member or None) -> {name: value}
    gated_off = {}                      # (stage key, member or None) -> gate block
    stage_records = []

    # Tracked rather than derived from the record: with members, "how many rows
    # are there" no longer tells you where a run stopped, and after a failure
    # that is the only question worth answering.
    where = "before the first stage"
    try:
        for stage in spec.stages:
            todo = member_list if stage.scope == "member" else [None]
            for member in todo:
                where = unit_name(stage.key, member)
                gate = None
                if stage.when is not None:
                    gate = _gate(stage, member, member_list, scope_of, fields,
                                 gated_off)
                    if not gate["passed"]:
                        # NOT a missing row. The stage did not run, the record
                        # says so, and it says what decided that.
                        gated_off[(stage.key, member)] = gate
                        stage_records.append(_gated_row(
                            stage, member, gate, len(stage_records) + 1))
                        continue
                stage_records.append(_execute(
                    spec, stage, member, member_list, scope_of, outputs, fields,
                    gated_off, out, config, runner, len(stage_records) + 1,
                    gate))
        where = "after the last stage"
    except (RunError, OutDirViolation, models.MediaError,
            models.SeamError) as exc:
        _fail_note(out, spec, stage_records, exc, where)
        raise

    record = {
        "schema": RECORD_SCHEMA,
        "generator": "components/chain-runner/runner/run.py",
        "chain": {
            "key": spec.key,
            "label": spec.label,
            "spec_sha256": _file_sha(spec.path),
            "placeholder_style": spec.placeholder_style,
            "provenance": spec.provenance,
        },
        "model_runner": model_runner_name,
        "members": list(members),
        "config": {"vars": {name: config[name] for name in sorted(config)}},
        "stages": stage_records,
        # A gated-off stage wrote nothing, so it contributes nothing here. Its
        # ROW is still in `stages` — the list of outputs is what the run
        # produced, and the list of stages is what the run decided.
        "outputs": [row["output"] for row in stage_records if "output" in row],
    }
    # WHAT THE RUN ROUTED ON (CR-6), in one place, in execution order. The
    # per-stage rows carry the same values; this is the roll-up, because "which
    # lane did this run decide it was in" should be answerable without reading
    # fifteen stage rows.
    #
    # The key is ABSENT — not empty — when no stage declared a field. A chain
    # written before fields existed therefore produces a run.json byte-identical
    # to the one it produced before, which is the members-feature guarantee in
    # the only form a record can hold it.
    routed = [{"stage": row["key"], "member": row["member"],
               "fields": row["fields"]}
              for row in stage_records if "fields" in row]
    if routed:
        record["extracted"] = routed
    # WHAT THE RUN DID NOT DO, and why (CR-5) — the same roll-up discipline as
    # `extracted`, and for the sharper version of the same reason: "which stages
    # were gated off" should be answerable without reading fifteen stage rows,
    # and a skipped stage is exactly the fact a reader would otherwise assume
    # into existence. ABSENT, not empty, when nothing was gated off, so a chain
    # with no gates produces the record it produced before CR-5.
    gated = [{"stage": row["key"], "member": row["member"],
              "by": "gate", "when": row["gate"]["when"],
              "value": row["gate"]["value"]}
             for row in stage_records if row.get("skipped_by_gate")]
    if gated:
        record["skipped"] = gated
    record["files"] = out.manifest()
    out.write_json("run.json", record)
    # run.json is written before the manifest can include itself — stated so
    # nobody reads `files` as a complete listing of the directory. It is the
    # listing of what the STAGES produced, which is the honest thing to
    # publish: a manifest containing its own hash cannot exist.
    if stamp is not None:
        out.write_json("stamp.json", stamp)
    return record


def _gate(stage, member, member_list, scope_of, fields, gated_off):
    """Judge a stage's `when:` gate. Returns {when, value, passed} (CR-5).

    The predicate is FLAT by ruling — one field of one earlier stage, tested by
    equality or membership — so there is nothing to evaluate here beyond reading
    a value and comparing it. That is the whole feature, and the smallness is
    the point: the moment this function needs to walk a tree, the chain has
    asked for a dependency graph and the standing kill line applies.

    A gate whose FIELD cannot be reached fails the run rather than defaulting.
    There is no "gate could not be read, so run it anyway" and no "so skip it" —
    both are the engine deciding a routing question the chain asked its own
    output to decide.
    """
    when = stage.when
    _kind, body, _selector, name = specmod.parse_ref(when["field"])
    at = _member_at(stage, body, member, member_list, scope_of,
                    "its `when:` gate reads",
                    "A gate carries no selector, so a group stage cannot be "
                    "gated on a member stage's field once a run has more than "
                    "one member.")
    if (body, at) in gated_off:
        raise RunError(
            "stage {0!r}: its `when:` gate reads field {1!r} of {2!r}, WHICH "
            "WAS ITSELF GATED OFF — {3}. A gate over a stage that never ran has "
            "no value to read, and defaulting one either way would decide the "
            "route by the engine's opinion rather than the chain's."
            .format(stage.key, name, body, _gate_reason(gated_off[(body, at)],
                                                        body)))
    extracted = fields.get((body, at))
    if extracted is None or name not in extracted:
        raise RunError(
            "stage {0!r}: its `when:` gate reads field {1!r} of {2!r}, which "
            "produced no such field on this run (it extracted: {3})"
            .format(stage.key, name, body,
                    ", ".join(sorted(extracted or {})) or "nothing"))
    value = extracted[name]
    if "equals" in when:
        passed = value == when["equals"]
    else:
        passed = value in when["in"]
    return {"when": dict(when), "value": value, "passed": bool(passed)}


def _gate_reason(gate, key):
    """One clause saying why a gate did not hold, for another error to carry."""
    when = gate["when"]
    if "equals" in when:
        test = "equal {0!r}".format(when["equals"])
    else:
        test = "be one of {0}".format(", ".join(repr(v) for v in when["in"]))
    return ("{0} runs only when {1} would {2}, and it read {3!r}"
            .format(key, when["field"], test, gate["value"]))


def _gated_row(stage, member, gate, n):
    """The record row for a stage that did NOT run, because its gate said so.

    It carries what is TRUE about the stage — its key, label, kind, scope,
    member, the model it would have bound — and the gate that decided, with the
    value the gate read. It carries no `prompt`, no `output` and no `inputs`,
    because there was no prompt, no output and nothing consumed: a row full of
    nulls would be a stage that looks like it ran and produced nothing, which is
    the one reading this row exists to prevent.
    """
    return {
        "n": n,
        "key": stage.key,
        "label": stage.label,
        "kind": stage.kind,
        "scope": stage.scope,
        "member": member,
        "model": stage.model,
        "skipped_by_gate": True,
        "gate": gate,
        "note": stage.note,
    }


def _member_at(stage, body, member, member_list, scope_of, what, fix):
    """Which member's output of `body` this unit reads, or None for a group one.

    Shared by inputs and by the `when:` gate, because "whose output does this
    read" is one question with one answer and two callers — and a gate resolving
    a member differently from an input would mean a stage could be judged on one
    member's fact and then run on another's.
    """
    if scope_of.get(body) != "member":
        return None
    if stage.scope != "group":
        return member
    # The spec allowed this because on a one-member run it means exactly one
    # thing. With several members it means nothing, and picking one silently is
    # how a brief for six videos quietly describes whichever ran last.
    if len(member_list) > 1:
        raise RunError(
            "stage {0!r} is group-scoped and {1} {2!r}, a member stage, without "
            "'*' — this run has {3} members, so that says 'which one?' and "
            "nothing answers it. {4}".format(stage.key, what, body,
                                             len(member_list), fix))
    return member_list[0]


def _execute(spec, stage, member, member_list, scope_of, outputs, fields,
             gated_off, out, config, runner, n, gate=None):
    """One stage, for one member (or once, for a group stage). Returns its row.

    The two stage KINDS part company at exactly one point, and nowhere else:
    a `model` stage calls the seam, an `assemble` stage takes its own rendered
    prompt as its output. Everything around that — inputs, media, rendering,
    the prompt written to disk, the jail, the record row — is identical, which
    is what "first-class stage kind" has to mean if it is to mean anything.
    """
    values, refs = _values(stage, member, member_list, scope_of, outputs,
                           fields, gated_off, config)
    media, media_rows = _media(stage, config, values)
    rendered = render(stage.prompt_text, values, spec.placeholder_style,
                      stage.key)
    prefix = "members/{0}/".format(member) if member else ""
    prompt_rel = "{0}stages/{1}/prompt.txt".format(prefix, stage.key)
    out.write_text(prompt_rel, rendered)

    artifacts = []
    if stage.kind == "assemble":
        # No model, no seam, no spend. The rendered prompt IS the assembled
        # document: the stage's whole job is to put earlier outputs into slots,
        # which rendering already did.
        text = rendered
    else:
        request = models.ModelRequest(
            chain=spec.key, stage=stage.key, label=stage.label,
            model=stage.model, prompt=rendered, inputs=dict(values),
            media=media)
        response = runner(request)
        if not isinstance(response, models.ModelResponse):
            raise RunError(
                "stage {0!r}: the model runner returned {1}, not a "
                "ModelResponse — the seam's shape is the seam".format(
                    stage.key, type(response).__name__))
        text = response.text
        for path in sorted(response.artifacts or {}):
            # Straight through the jail. A runner is not trusted to have
            # picked a safe path just because it is our own code.
            out.write_text(path, response.artifacts[path])
            artifacts.append({
                "path": path,
                "sha256": sha256_text(response.artifacts[path]),
            })

    output_rel = prefix + stage.output
    out.write_text(output_rel, text)
    outputs[(stage.key, member)] = text

    # AFTER the output is on disk, deliberately: an extraction failure fails the
    # stage, and the question a person then asks is "what did it actually say".
    # Deleting the evidence to fail a step earlier answers that with nothing.
    extracted = None
    if stage.fields:
        extracted = extract_fields(stage, text)
        fields[(stage.key, member)] = extracted

    referenced = used_names(stage.prompt_text, spec.placeholder_style)
    declared = set(refs) | set(row["name"] for row in media_rows)
    row = {
        "n": n,
        "key": stage.key,
        "label": stage.label,
        "kind": stage.kind,
        "scope": stage.scope,
        "member": member,
        "model": stage.model,
        "prompt": {
            "declared": stage.prompt_declared,
            "version": stage.prompt_version,
            "resolved": _rel(spec.chain_dir, stage.prompt_path),
            "sha256": sha256_text(stage.prompt_text),
            "rendered_at": prompt_rel,
            "rendered_sha256": sha256_text(rendered),
        },
        "inputs": refs,
        "media": media_rows,
        "unused_inputs": sorted(declared - referenced),
        "output": output_rel,
        "output_sha256": sha256_text(text),
        "output_chars": len(text),
        "artifacts": artifacts,
        "note": stage.note,
    }
    if extracted is not None:
        row["fields"] = extracted
    if gate is not None:
        # A gate that HELD is recorded too, with the value it read. "This stage
        # ran because lane was ORGANIC" and "this stage ran" are different
        # records, and only the first one survives being read six weeks later.
        row["gate"] = gate
    return row


def _values(stage, member, member_list, scope_of, outputs, fields, gated_off,
            config):
    """(name -> substituted value, name -> the ref it came from).

    Piping is resolved MEMBER-RELATIVE: a member stage reading another member
    stage reads its own member's output, and a group stage reads every member's
    through `*`. The spec has already refused the combinations that would make
    that ambiguous, so there is no "which member did it mean" branch here.
    """
    values = {}
    refs = {}
    for name in sorted(stage.inputs):
        ref = stage.inputs[name]
        refs[name] = ref
        kind, body, selector, field = specmod.parse_ref(ref)
        if kind == "config":
            if body not in config:
                raise RunError(
                    "stage {0!r}: input {1!r} needs config variable {2!r}, "
                    "which this run was not given. Pass it with --var {2}=... "
                    "or in --config. (Run-config is where brand-shaped facts "
                    "enter; the engine knows none of them by name.)"
                    .format(stage.key, name, body))
            values[name] = config[body]
            continue
        if selector == "fanin":
            pairs = []
            for other in member_list:
                if (body, other) in gated_off:
                    raise RunError(_gated_off_message(
                        stage.key, name, body, gated_off[(body, other)],
                        " for member {0!r}".format(other)))
                if (body, other) not in outputs:
                    raise RunError(
                        "stage {0!r}: input {1!r} fans in {2!r}, which has not "
                        "run for member {3!r}".format(stage.key, name, body,
                                                      other))
                pairs.append((other, outputs[(body, other)]))
            values[name] = fan_in(pairs)
            continue
        at = _member_at(stage, body, member, member_list, scope_of,
                        "input {0!r} reads".format(name),
                        "Write '@{0}*' to fan every member in.".format(body))
        if (body, at) in gated_off:
            # LOUD, BY NAME (CR-5). A reference to a gated-off stage's output is
            # a chain that wants something a run decided not to produce, and the
            # alternatives — an empty string, the last member's text, a skipped
            # downstream stage — are all the engine inventing a route. The chain
            # either gates this stage too, or does not read that one.
            raise RunError(_gated_off_message(stage.key, name, body,
                                              gated_off[(body, at)], ""))
        if (body, at) not in outputs:
            raise RunError(
                "stage {0!r}: input {1!r} pipes {2!r}, which has not run"
                .format(stage.key, name, body))
        if field is not None:
            # The spec has already refused a reference to a field the producing
            # stage never declared, so reaching here with nothing extracted
            # would mean the engine skipped an extraction it owed — reported as
            # itself rather than as an empty value.
            extracted = fields.get((body, at)) or {}
            if field not in extracted:
                raise RunError(
                    "stage {0!r}: input {1!r} reads field {2!r} of {3!r}, which "
                    "produced no such field on this run (it extracted: {4})"
                    .format(stage.key, name, field, body,
                            ", ".join(sorted(extracted)) or "nothing"))
            values[name] = extracted[field]
            continue
        text = outputs[(body, at)]
        values[name] = (pick_control(text, stage.key, name)
                        if selector == "pick" else text)
    return values, refs


def _gated_off_message(key, name, body, gate, at):
    return ("stage {0!r}: input {1!r} reads {2!r}, WHICH WAS SKIPPED BY ITS GATE"
            "{3} — {4}. A reference to a gated-off stage's output fails here by "
            "name: it never resolves to an empty value, because a downstream "
            "stage reading nothing produces confident text about a stage that "
            "never ran. Gate this stage on the same field, or do not read that "
            "one.".format(key, name, body, at, _gate_reason(gate, body)))


def _media(stage, config, values):
    """(the typed tuple for the seam, the rows for the run record).

    The location is ALSO substituted into the prompt, under the media entry's
    own name — the machine these prompts were copied from hands an image to a
    template as its path, and rendering it any other way would be a parity
    difference invented here. The engine never opens the file: a location is
    what a vendor wants, and reading a video to pass it across a function
    boundary is how a chain engine becomes a media tool.
    """
    typed = []
    rows = []
    for name in sorted(stage.media):
        entry = stage.media[name]
        var = entry["ref"][len("@config."):]
        if var not in config:
            raise RunError(
                "stage {0!r}: media {1!r} needs config variable {2!r}, which "
                "this run was not given — a {3} input with no location cannot "
                "be sent anywhere. Pass it with --var {2}=..."
                .format(stage.key, name, var, entry["kind"]))
        item = models.MediaInput(name=name, kind=entry["kind"],
                                 location=config[var])
        typed.append(item)
        values[name] = item.location
        rows.append({"name": name, "kind": item.kind, "ref": entry["ref"],
                     "location": item.location})
    return tuple(typed), rows


def _fail_note(out, spec, stage_records, exc, where):
    """Leave the failure in the out dir, in words, beside the partial output.

    Best-effort: if the out dir itself is the thing that is broken, the raised
    exception is still the report and must not be masked by a second one.
    """
    try:
        out.write_text("FAILED.txt", "\n".join([
            "chain-runner: THE RUN FAILED.",
            "",
            "chain:       " + str(spec.key),
            "stages done: " + (", ".join(unit_name(row["key"], row.get("member"))
                                         for row in stage_records) or "none"),
            "failed at:   " + where,
            "reason:      " + str(exc),
            "",
            "Partial output above is kept on purpose: after a failed run the "
            "question is how far it got, and a tidy empty directory answers "
            "that with nothing.",
        ]) + "\n")
    except Exception:
        pass


def unit_name(key, member):  # noqa: E302 — public: run.py prints with it
    """One unit of work, named the way a reader needs it: with the member, when
    there is one. "stage4d done" says nothing about which of six videos got
    through, and after a failure that is the only question."""
    return (key + "@" + member) if member else key


def _rel(base, path):
    if path is None:
        return None
    try:
        return str(path.relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path)


def _file_sha(path):
    return sha256_text(path.read_text(encoding="utf-8"))
