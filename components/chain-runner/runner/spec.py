#!/usr/bin/env python3
"""`chain.json` — load, validate, resolve. The schema here IS the contract.

A chain lives at `components/chain-runner/chains/<chain>/chain.json` with its
prompt files beside it. This module turns that file into a `ChainSpec` or
refuses it — there is no third outcome and no repair-in-place, because a chain
that half-loads runs a shape nobody wrote.

FAILURE IS PART OF THE CONTRACT. A malformed chain.json raises `ChainSpecError`
carrying THE FILE and EVERY problem found, not just the first — a chain author
fixing one typo per run is a chain author who stops reading the errors. The
caller exits non-zero and writes NOTHING: validation completes before the out
directory is so much as created.

STRICT KEYS. An unknown top-level or stage key is an error, not something
ignored. `promt_version` silently doing nothing is how a chain quietly runs the
wrong prompt for a month.

BRAND-AGNOSTIC BY CONSTRUCTION (workspace rule 7). Nothing in this module or
anywhere in `runner/` knows any brand, and there is no field where one could be
named: brand-shaped facts arrive as run-config variables, which are opaque
names to the engine, and a chain references them as `@config.<name>`.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .models import MEDIA_KINDS

SCHEMA = 1

KEY_RE = re.compile(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$")
VAR_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")

TOP_KEYS = frozenset({
    "schema", "chain", "label", "note", "prompts_dir", "placeholder_style",
    "provenance", "defaults", "roots", "stages",
})
STAGE_KEYS = frozenset({
    "key", "label", "prompt", "prompt_version", "model", "inputs", "output",
    "note", "kind", "media", "scope", "fields", "when",
})
MEDIA_KEYS = frozenset({"kind", "ref"})

# The STAGE GATE (CR-5): an optional `when:` saying the stage runs only if one
# earlier stage's extracted field holds a value.
#
#   "when": {"field": "@triage.lane", "equals": "ORGANIC"}
#   "when": {"field": "@triage.lane", "in": ["ORGANIC", "UGC"]}
#
# FLAT ON PURPOSE, and this is the card's ruled wall, not a first cut: ONE
# field, ONE test, equality or membership, and no `and`/`or`, no negation, no
# expression language, no second field. The moment a gate needs to combine two
# facts, the chain is asking for a dependency graph — and the standing kill line
# says the bespoke runner stands as-is and this is reopened at the third chain,
# rather than an expression evaluator being grown here one operator at a time.
WHEN_KEYS = frozenset({"field", "equals", "in"})
WHEN_TESTS = ("equals", "in")

# What a stage may declare it can have READ BACK OUT of its own output (CR-6).
# A field is a NAME plus one flat, declarative way to parse it — never code in
# a definition, because a definition that executes is a program wearing data's
# clothes and the whole point of chain.json is that a reader can see what a run
# will do without running it.
#
#   "fields": {"lane":   {"from": "labelled-line", "label": "LANE"},
#              "format": {"from": "regex", "pattern": "^FORMAT:\\s*(\\S+)"}}
#
# Two forms and deliberately no third: a labelled line is what a prompt asks a
# model for when it wants one answer back, and a capture handles everything
# else. A field is exactly ONE captured value — `groups != 1` is a malformed
# chain, checked here, so a pattern that could return a tuple never reaches a
# run.
FIELD_KEYS = frozenset({"from", "label", "pattern"})
FIELD_FROMS = ("labelled-line", "regex")
# No dot: `@<stage>.<field>` splits a reference on the first dot, so a dotted
# field name (or stage key, below) would make a reference ambiguous.
FIELD_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-]*$")

# What a stage IS. `model` renders a prompt and calls the seam; `assemble`
# renders a prompt and IS DONE — its rendered text is its output and no model
# is bound or called (CR-2b). The second kind exists because the first imported
# chain has a stage that assembles a document out of earlier stages' outputs on
# its source machine and calls nothing; expressing that as a model stage bound
# to a fake model id ("assemble:inject") made the engine's own record lie about
# what a run did. A stage kind is first-class, not a special case, so a reader
# of chain.json can see which stages cost money.
STAGE_KINDS = ("model", "assemble")

# Whether a stage runs ONCE PER MEMBER of the run's group, or once for the
# whole group. Members are opaque names supplied per run (`--member`), never
# known to the engine — a group of videos, a group of SKUs, a group of
# anything. `member` is the default and a run with no members declared has
# exactly one, unnamed, which is why adding this changed no existing path.
STAGE_SCOPES = ("member", "group")
DEFAULT_KEYS = frozenset({"model", "prompt_version"})
PROVENANCE_KEYS = frozenset({"source", "sha", "pinned_on", "note", "route",
                             "resolver", "picks", "gaps"})
PICK_KEYS = frozenset({"stage", "engine", "version", "source",
                       "source_filename", "sha256", "copied_to"})

# The placeholder spellings a prompt body may use, DECLARED PER CHAIN and never
# guessed (CR-2 ruling 3, the team 2026-08-31). `at-brace` is the house form and the
# default; the others exist because CR-2 imports prompts COPIED AT A PINNED SHA
# from another component, and a copy whose tokens had to be rewritten is not the
# copy whose sha was pinned. Declaring the dialect is cheaper than a permanent
# fork and leaves the engine knowing nothing about any particular chain.
#
#   at-brace      @{name}    escape @@{name}    the house form, the default
#   curly         {{name}}   no escape form
#   single-curly  {name}     no escape form     an imported chain's dialect
#
# `single-curly` matches ONLY `[a-z0-9_]` inside the braces, which is not a
# style choice: it is the exact token grammar the imported chain's own machine
# substitutes with (its `re.findall(r"\{([a-z0-9_]+)\}", template)`). Widening
# it would make our render fatal on `{Placeholder}`-shaped prose that the source
# machine passes through untouched, which is a parity difference invented by the
# reader of the prompt rather than by its author.
PLACEHOLDER_STYLES = ("at-brace", "curly", "single-curly")


class ChainSpecError(Exception):
    """A chain.json that will not run. Carries the file and every problem."""

    def __init__(self, path, problems):
        self.path = str(path)
        self.problems = list(problems)
        Exception.__init__(
            self,
            "malformed chain spec: {0}\n  - {1}".format(
                self.path, "\n  - ".join(self.problems)))


# ------------------------------------------------------------ the ref grammar
#
# An input reference is one of:
#
#     @<earlier-stage>          that stage's output text
#     @<earlier-stage>.<field>  one FIELD that stage declared it can extract
#     @<earlier-stage>#pick     its CONTROL VERSION — see engine.pick_control
#     @<earlier-stage>*         FAN-IN: every member's output of that stage
#     @config.<var>             a run-config variable
#
# The FIELD form arrived in CR-6 because a chain that routes on a fact a stage
# itself decides could previously only reference the whole opaque output. It
# reads as the dot already reads in `@config.<var>` — a name inside a named
# thing — and it splits on the FIRST dot, which is why neither a stage key nor
# a field name may contain one. Nothing here interprets a field's meaning: the
# engine knows a name and a parse rule, and no more than that.
#
# The two selectors arrived in CR-2b because the first imported chain uses both
# and a chain.json that could not spell them was importing a chain it could not
# run. They are spelled the way the source machine spells them ON PURPOSE: the
# import copies a reference across rather than translating one, so a reader
# diffing the two files sees the same token on both sides. Neither selector
# knows anything about that chain — `#pick` is a text rule over any stage's
# output, `*` is a fan-in over whatever members a run declares.
#
# `#pick` and `*` are mutually exclusive. A "control version of every member"
# has two readings (one pick per member, or a pick over the concatenation) and
# a reference with two readings is not a reference.
SELECTORS = ("pick", "fanin")


def parse_ref(ref):
    """`@…` -> (kind, target, selector, field). kind is 'stage' or 'config'.

    Returns (None, None, None, None) for anything that is not a reference at
    all; raising here would make one malformed input hide the rest, and this
    file's contract is that a bad chain reports EVERY problem at once.

    `field` is the CR-6 form: `@stage-a.lane` -> ('stage', 'stage-a', None,
    'lane'). Selectors are stripped BEFORE the dot split, so `@a*` and `@a#pick`
    read exactly as they did before fields existed, and `@a.lane*` parses as a
    field carrying a selector — which the validator then refuses by name rather
    than silently choosing one of its two readings.
    """
    if not isinstance(ref, str) or not ref.startswith("@"):
        return None, None, None, None
    body = ref[1:]
    if body.startswith("config."):
        return "config", body[len("config."):], None, None
    selector = None
    if body.endswith("#pick"):
        selector = "pick"
        body = body[:-len("#pick")]
    if body.endswith("*"):
        selector = "fanin" if selector is None else "both"
        body = body[:-1]
    field = None
    if "." in body:
        body, field = body.split(".", 1)
    return "stage", body, selector, field


class Stage(object):
    def __init__(self, index, key, label, model, prompt_declared,
                 prompt_version, prompt_path, prompt_text, inputs, output,
                 note, kind="model", media=None, scope="member", fields=None,
                 when=None):
        self.index = index
        self.key = key
        self.label = label
        self.model = model
        self.kind = kind
        self.scope = scope
        self.media = media or {}                # name -> {"kind", "ref"}
        self.fields = fields or {}              # name -> {"from", "label"/"pattern"}
        # The gate, AS DECLARED, or None. Kept verbatim rather than compiled
        # into a predicate object so `run.json` can state the predicate a run
        # was judged by in the words its author wrote (CR-5).
        self.when = when
        self.prompt_declared = prompt_declared
        self.prompt_version = prompt_version
        self.prompt_path = prompt_path          # absolute
        self.prompt_text = prompt_text
        self.inputs = inputs                    # name -> ref string
        self.output = output                    # relative to the OUT root
        self.note = note


class ChainSpec(object):
    def __init__(self, path, chain_dir, document, stages, placeholder_style,
                 prompts_dir, provenance, defaults, roots=None):
        self.path = path                        # absolute chain.json
        self.chain_dir = chain_dir              # absolute chain directory
        self.document = document                # the raw file, as parsed
        self.stages = stages
        self.placeholder_style = placeholder_style
        self.prompts_dir = prompts_dir          # absolute
        self.provenance = provenance
        self.defaults = defaults
        self.roots = roots or {}                # name -> declared path

    @property
    def key(self):
        return self.document["chain"]

    @property
    def label(self):
        return self.document["label"]

    def stage_keys(self):
        return [stage.key for stage in self.stages]


# --------------------------------------------------------------------- load

def load(chain_json_path, chain_key=None):
    """Parse, validate and resolve. Raises ChainSpecError or returns a spec."""
    path = Path(str(chain_json_path)).resolve()
    if not path.is_file():
        raise ChainSpecError(path, ["no such file — a chain is a directory "
                                    "holding chain.json"])
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ChainSpecError(path, ["cannot read the file: " + str(exc)])
    try:
        document = json.loads(raw)
    except ValueError as exc:
        raise ChainSpecError(path, ["not valid JSON: " + str(exc)])
    if not isinstance(document, dict):
        raise ChainSpecError(path, ["the top level must be an object, not " +
                                    type(document).__name__])

    problems = []
    chain_dir = path.parent

    unknown = sorted(set(document) - TOP_KEYS)
    if unknown:
        problems.append("unknown top-level key(s): " + ", ".join(unknown) +
                        " (known: " + ", ".join(sorted(TOP_KEYS)) + ")")

    schema = document.get("schema")
    if schema != SCHEMA:
        problems.append("schema must be {0}; got {1!r}".format(SCHEMA, schema))

    key = document.get("chain")
    if not isinstance(key, str) or not KEY_RE.match(key or ""):
        problems.append("`chain` must be a kebab-case key; got {0!r}".format(key))
    elif chain_key is not None and key != chain_key:
        problems.append(
            "`chain` is {0!r} but the chain directory is {1!r} — the key and "
            "its folder must agree, or a run names one chain and executes "
            "another".format(key, chain_key))

    if not isinstance(document.get("label"), str) or not document.get("label"):
        problems.append("`label` must be a non-empty string — a human names a "
                        "chain by its label, never by its key")

    placeholder_style = document.get("placeholder_style", PLACEHOLDER_STYLES[0])
    if placeholder_style not in PLACEHOLDER_STYLES:
        problems.append("`placeholder_style` must be one of " +
                        ", ".join(PLACEHOLDER_STYLES) +
                        "; got {0!r}".format(placeholder_style))
        placeholder_style = PLACEHOLDER_STYLES[0]

    prompts_rel = document.get("prompts_dir", "prompts")
    prompts_dir = None
    if not isinstance(prompts_rel, str) or not prompts_rel:
        problems.append("`prompts_dir` must be a non-empty relative path")
    else:
        prompts_dir = _under(chain_dir, prompts_rel)
        if prompts_dir is None:
            problems.append(
                "`prompts_dir` {0!r} leaves the chain directory — a chain owns "
                "its prompts and reads nothing above itself".format(prompts_rel))
        elif not prompts_dir.is_dir():
            problems.append("`prompts_dir` {0!r} is not a directory under {1}"
                            .format(prompts_rel, chain_dir))

    provenance = _provenance(document.get("provenance"), problems)
    defaults = _defaults(document.get("defaults"), problems)
    roots = _roots(document.get("roots"), problems)

    stages = _stages(document.get("stages"), prompts_dir, defaults, problems)

    if problems:
        raise ChainSpecError(path, problems)
    return ChainSpec(path=path, chain_dir=chain_dir, document=document,
                     stages=stages, placeholder_style=placeholder_style,
                     prompts_dir=prompts_dir, provenance=provenance,
                     defaults=defaults, roots=roots)


PROVENANCE_TEXT_KEYS = ("source", "sha", "pinned_on", "note", "route",
                        "resolver")


def _provenance(block, problems):
    """Where a chain came from, and — when it was RESOLVED rather than authored
    — exactly what the source's own resolver picked.

    It is OPTIONAL and defaults to nulls, because a chain authored here was
    copied from nowhere. But a chain that WAS copied and records no pin is a
    fork nobody can date, so the field exists from CR-1 and the contract names
    it.

    CR-2 (the team's ruling 2, 2026-08-31) widened it past the pin itself. Importing
    a chain whose shape is decided at RUN TIME by the source's own version scan
    and route resolution means the pin alone does not say what ran: the same sha
    resolves differently under a different route. So the block also carries the
    `route` the snapshot was taken under, the `resolver` entrypoint that was
    executed to take it, the per-stage `picks` (which file, which version, which
    hash), and the `gaps` — every place the imported chain cannot express what
    the source expressed. Gaps are recorded rather than smoothed on purpose: a
    parity reader has to meet them in the file, not discover them in a diff.
    """
    empty = dict((name, None) for name in PROVENANCE_TEXT_KEYS)
    empty["picks"] = []
    empty["gaps"] = []
    if block is None:
        return empty
    if not isinstance(block, dict):
        problems.append("`provenance` must be an object")
        return empty
    unknown = sorted(set(block) - PROVENANCE_KEYS)
    if unknown:
        problems.append("unknown provenance key(s): " + ", ".join(unknown) +
                        " (known: " + ", ".join(sorted(PROVENANCE_KEYS)) + ")")
    out = dict(empty)
    for name in PROVENANCE_TEXT_KEYS:
        value = block.get(name)
        if value is not None and not isinstance(value, str):
            problems.append("`provenance.{0}` must be a string or absent"
                            .format(name))
            continue
        out[name] = value
    if out["sha"] is not None and not re.match(r"^[0-9a-f]{7,40}$", out["sha"]):
        problems.append("`provenance.sha` must be a lowercase hex git sha")
    if out["sha"] and not out["source"]:
        problems.append("`provenance.sha` without `provenance.source` — a pin "
                        "with no thing pinned")

    gaps = block.get("gaps")
    if gaps is not None:
        if not isinstance(gaps, list) or [g for g in gaps
                                          if not isinstance(g, str)]:
            problems.append("`provenance.gaps` must be a list of strings")
        else:
            out["gaps"] = list(gaps)

    picks = block.get("picks")
    if picks is not None:
        if not isinstance(picks, list):
            problems.append("`provenance.picks` must be a list of objects")
        else:
            out["picks"] = _picks(picks, problems)
    if out["picks"] and not out["resolver"]:
        problems.append("`provenance.picks` without `provenance.resolver` — a "
                        "record of what was picked with no record of what did "
                        "the picking")
    return out


def _picks(rows, problems):
    """One row per stage the source's resolver chose a file for."""
    out = []
    for index, row in enumerate(rows):
        where = "provenance.picks[{0}]".format(index)
        if not isinstance(row, dict):
            problems.append(where + " must be an object")
            continue
        unknown = sorted(set(row) - PICK_KEYS)
        if unknown:
            problems.append(where + " unknown key(s): " + ", ".join(unknown) +
                            " (known: " + ", ".join(sorted(PICK_KEYS)) + ")")
        if not isinstance(row.get("stage"), str) or not row.get("stage"):
            problems.append(where + " `stage` must name a stage")
        digest = row.get("sha256")
        if digest is not None and not re.match(r"^[0-9a-f]{64}$", str(digest)):
            problems.append(where + " `sha256` must be a sha256 hex digest — a "
                            "pick nobody can verify is a claim, not a record")
        version = row.get("version")
        if version is not None and not isinstance(version, int):
            problems.append(where + " `version` must be the integer the "
                            "source's own scan produced")
        out.append(dict(row))
    return out


def _defaults(block, problems):
    out = {"model": None, "prompt_version": None}
    if block is None:
        return out
    if not isinstance(block, dict):
        problems.append("`defaults` must be an object")
        return out
    unknown = sorted(set(block) - DEFAULT_KEYS)
    if unknown:
        problems.append("unknown defaults key(s): " + ", ".join(unknown))
    for name in DEFAULT_KEYS:
        value = block.get(name)
        if value is not None and (not isinstance(value, str) or not value):
            problems.append("`defaults.{0}` must be a non-empty string or "
                            "absent".format(name))
            continue
        out[name] = value
    return out


def _roots(block, problems):
    """Named CONTENT ROOTS a chain reads from, as declared defaults:

        "roots": {"copy": "some/tree", "assets": "another/tree"}

    A root is a NAME and a PATH, and this module knows nothing else about
    either. The names are opaque here the way run-config variable names are
    opaque — the engine neither interprets them nor branches on them — and an
    invocation may override any of them (`--root NAME=PATH`). Validation of
    what a path is ALLOWED to point at is not this module's business and does
    not live here; see `run.py`'s check step.
    """
    out = {}
    if block is None:
        return out
    if not isinstance(block, dict):
        problems.append("`roots` must be an object of name -> path")
        return out
    for name in sorted(block):
        value = block[name]
        if not VAR_RE.match(name or ""):
            problems.append("`roots` name {0!r} is not a valid identifier"
                            .format(name))
            continue
        if not isinstance(value, str) or not value:
            problems.append("`roots.{0}` must be a non-empty path".format(name))
            continue
        out[name] = value
    return out


def _stages(block, prompts_dir, defaults, problems):
    if not isinstance(block, list) or not block:
        problems.append("`stages` must be a non-empty list — ARRAY ORDER IS "
                        "THE RUN ORDER, and a chain with no stages is not a "
                        "chain")
        return []

    stages = []
    seen = {}
    scopes = {}
    fields_of = {}
    for index, item in enumerate(block):
        where = "stages[{0}]".format(index)
        if not isinstance(item, dict):
            problems.append(where + " must be an object")
            continue
        unknown = sorted(set(item) - STAGE_KEYS)
        if unknown:
            problems.append(where + " unknown key(s): " + ", ".join(unknown) +
                            " (known: " + ", ".join(sorted(STAGE_KEYS)) + ")")

        key = item.get("key")
        if not isinstance(key, str) or not KEY_RE.match(key or ""):
            problems.append(where + " `key` must be a kebab-case key; got "
                            "{0!r}".format(key))
            key = None
        elif "." in key:
            # KEY_RE allows a dot, and before CR-6 nothing read one. Now
            # `@<stage>.<field>` splits on the first dot, so a dotted stage key
            # would make every reference to it two references. Refused rather
            # than disambiguated: a reference with two readings is not a
            # reference, which is the same rule `#pick` + `*` already answers to.
            problems.append(
                where + " `key` {0!r} contains a dot. `@<stage>.<field>` splits "
                "a reference on the first dot (CR-6), so a dotted stage key "
                "makes every reference to it ambiguous.".format(key))
            key = None
        elif key in seen:
            problems.append(where + " duplicate stage key {0!r} (first used at "
                            "stages[{1}]) — a key is how a later stage pipes "
                            "an earlier one, so two of them make the pipe "
                            "ambiguous".format(key, seen[key]))
            key = None
        elif key == "config":
            problems.append(where + " `key` may not be 'config' — `@config.x` "
                            "is the run-config reference form")
            key = None
        else:
            seen[key] = index
        where = "stage {0!r}".format(key) if key else where

        label = item.get("label")
        if not isinstance(label, str) or not label:
            problems.append(where + ": `label` must be a non-empty string")

        kind = item.get("kind", STAGE_KINDS[0])
        if kind not in STAGE_KINDS:
            problems.append(where + ": `kind` must be one of " +
                            ", ".join(STAGE_KINDS) +
                            "; got {0!r}".format(item.get("kind")))
            kind = STAGE_KINDS[0]

        scope = item.get("scope", STAGE_SCOPES[0])
        if scope not in STAGE_SCOPES:
            problems.append(where + ": `scope` must be one of " +
                            ", ".join(STAGE_SCOPES) +
                            "; got {0!r}".format(item.get("scope")))
            scope = STAGE_SCOPES[0]
        if key is not None:
            scopes[key] = scope

        # An `assemble` stage calls nothing, so a model on it is not a harmless
        # extra field: it is a claim, in the contract, that the stage costs a
        # vendor call. Refused rather than ignored — that is the whole reason
        # the kind is first-class instead of a magic model id.
        model = item.get("model") or defaults.get("model")
        if kind == "assemble":
            if item.get("model"):
                problems.append(
                    where + ": `kind` is 'assemble' but a `model` is bound. An "
                    "assemble stage renders its prompt and is done — it calls "
                    "no model, so naming one claims a vendor call that never "
                    "happens.")
            model = None
        elif not isinstance(model, str) or not model:
            problems.append(
                where + ": no model — set `model` on the stage, "
                "`defaults.model` on the chain, or declare `\"kind\": "
                "\"assemble\"` if the stage genuinely calls nothing. A stage "
                "with no model binding is a stage whose behaviour depends on "
                "whatever the caller happened to have configured.")
            model = None
            kind = None                        # drop it, like a keyless stage

        version = item.get("prompt_version") or defaults.get("prompt_version")
        if version is not None and (not isinstance(version, str) or not version):
            problems.append(where + ": `prompt_version` must be a non-empty "
                            "string or absent")
            version = None

        prompt_declared = item.get("prompt")
        prompt_path = None
        prompt_text = None
        if not isinstance(prompt_declared, str) or not prompt_declared:
            problems.append(where + ": `prompt` must be a non-empty path stem "
                            "under prompts_dir")
        elif prompts_dir is not None:
            prompt_path, why = resolve_prompt(prompts_dir, prompt_declared,
                                              version)
            if prompt_path is None:
                problems.append(where + ": " + why)
            else:
                try:
                    prompt_text = prompt_path.read_text(encoding="utf-8")
                except OSError as exc:
                    problems.append(where + ": cannot read " + str(prompt_path)
                                    + ": " + str(exc))

        # Fields are read BEFORE inputs and recorded per stage, because the
        # ordering rule below already guarantees a field reference points at an
        # EARLIER stage — so by the time a stage's inputs are checked, every
        # field it could legally name is already known and "no such field" is a
        # compile error rather than a run-time surprise.
        fields = _fields(item.get("fields"), where, problems)
        if key is not None:
            fields_of[key] = fields

        inputs = _inputs(item.get("inputs"), where, key, seen, scopes, scope,
                         fields_of, problems)
        media = _media(item.get("media"), where, inputs, problems)
        # The gate is checked by the same rule as an input reference and for the
        # same reason: a stage may only be gated on a field an EARLIER stage
        # declared it can extract, so a gate on a fact nobody arranged to
        # extract is a malformed chain rather than a run that skips everything.
        when = _when(item.get("when"), where, key, seen, fields_of, problems)

        output = item.get("output")
        if output is None:
            output = "stages/{0}/output.md".format(key or index)
        elif not isinstance(output, str) or not output:
            problems.append(where + ": `output` must be a non-empty path "
                            "relative to --out, or absent")
            output = "stages/{0}/output.md".format(key or index)
        elif os.path.isabs(output) or _escapes(output):
            problems.append(
                where + ": `output` {0!r} leaves the out root. A stage writes "
                "under --out and nowhere else; the engine would refuse this at "
                "write time and it is refused here too, so the run never "
                "starts.".format(output))

        note = item.get("note")
        if note is not None and not isinstance(note, str):
            problems.append(where + ": `note` must be a string")

        if key is None or kind is None:
            continue
        stages.append(Stage(index=index, key=key, label=label, model=model,
                            prompt_declared=prompt_declared,
                            prompt_version=version, prompt_path=prompt_path,
                            prompt_text=prompt_text, inputs=inputs,
                            output=output, note=note, kind=kind, media=media,
                            scope=scope, fields=fields, when=when))

    outputs = {}
    for stage in stages:
        if stage.output in outputs:
            problems.append(
                "stages {0!r} and {1!r} both write {2!r} — the second would "
                "silently overwrite the first".format(
                    outputs[stage.output], stage.key, stage.output))
        outputs[stage.output] = stage.key
    return stages


def _inputs(block, where, key, seen_before, scopes, scope, fields_of, problems):
    """Declared piping. A stage says, in chain.json, what it consumes:

        "inputs": {"transcript": "@stage-0", "tone": "@config.tone",
                   "lane": "@stage-0.lane"}

    DECLARED, never discovered in the prompt body — that is what makes
    chain.json the contract: the data flow is readable without opening a single
    prompt, and the ordering check below is machine-decidable.

    CR-2b adds the two selectors (`#pick`, `*`) and the scope rules that make
    fan-in decidable HERE rather than at run time: a group stage reading a
    member stage without `*` would mean "which member?", and the answer must be
    a malformed chain, not a coin flip on execution order.

    CR-6 adds the FIELD form, checked the same way and for the same reason: a
    stage may only read a field the producing stage DECLARED, so a chain that
    routes on a fact nobody arranged to extract is malformed at compile rather
    than empty at run time.
    """
    out = {}
    if block is None:
        return out
    if not isinstance(block, dict):
        problems.append(where + ": `inputs` must be an object of name -> ref")
        return out
    for name in sorted(block):
        ref = block[name]
        if not VAR_RE.match(name or ""):
            problems.append(where + ": input name {0!r} is not a valid "
                            "identifier".format(name))
            continue
        if not isinstance(ref, str) or not ref.startswith("@"):
            problems.append(
                where + ": input {0!r} must be a reference string — "
                "'@<earlier-stage-key>', '@<earlier-stage-key>.<field>', "
                "'@<earlier-stage-key>#pick', '@<earlier-stage-key>*' or "
                "'@config.<var>'; got {1!r}".format(name, ref))
            continue
        target_kind, body, selector, field = parse_ref(ref)
        if target_kind == "config":
            if not VAR_RE.match(body or ""):
                problems.append(where + ": input {0!r} names an invalid config "
                                "variable {1!r}".format(name, body))
            out[name] = ref
            continue
        if selector == "both":
            problems.append(
                where + ": input {0!r} is {1!r} — `#pick` and `*` together have "
                "two readings (a pick per member, or a pick over the fan-in), "
                "and a reference with two readings is not a reference"
                .format(name, ref))
            continue
        if field is not None and selector is not None:
            problems.append(
                where + ": input {0!r} is {1!r} — a FIELD reference carries no "
                "selector. '#pick' selects a version out of a whole output and "
                "'*' fans in every member's; neither has a reading over one "
                "extracted value.".format(name, ref))
            continue
        if not KEY_RE.match(body or ""):
            problems.append(where + ": input {0!r} reference {1!r} is neither "
                            "a stage key nor '@config.<var>'".format(name, ref))
            continue
        if key is None:
            # The stage key is already an error above; an ordering complaint
            # on top of it would be noise pointing at the wrong line.
            out[name] = ref
            continue
        if body == key:
            problems.append(where + ": input {0!r} pipes the stage into "
                            "itself".format(name))
            continue
        if body not in seen_before or seen_before[body] >= seen_before[key]:
            problems.append(
                where + ": input {0!r} pipes {1!r}, which is not an EARLIER "
                "stage. Array order is run order, so a stage can only read "
                "what has already run.".format(name, body))
            continue
        if field is not None:
            declared = fields_of.get(body) or {}
            if field not in declared:
                problems.append(
                    where + ": input {0!r} reads field {1!r} of stage {2!r}, "
                    "which declares {3}. A field is referenceable only where "
                    "the stage producing it declared HOW to read it — otherwise "
                    "a chain routes on a fact nobody arranged to extract."
                    .format(name, field, body,
                            ", ".join(sorted(declared)) or "no fields"))
                continue
        target_scope = scopes.get(body, STAGE_SCOPES[0])
        if selector == "fanin" and target_scope != "member":
            problems.append(
                where + ": input {0!r} fans in {1!r}, which is a group stage — "
                "it runs once, so there is nothing to fan in. Drop the '*'."
                .format(name, body))
            continue
        if selector == "fanin" and scope != "group":
            problems.append(
                where + ": input {0!r} fans in {1!r}, but this stage is member-"
                "scoped and therefore already runs inside one member. Fan-in is "
                "how a GROUP stage reads every member; declare "
                "'\"scope\": \"group\"' or drop the '*'.".format(name, body))
            continue
        # A group stage reading a member stage PLAINLY is left to run time on
        # purpose. On a one-member run it is unambiguous and common — it is how
        # an imported chain that was written before members existed still runs
        # — and on a many-member run it has no answer at all. So the engine
        # refuses it when, and only when, it is actually ambiguous. Refusing it
        # here instead would make a valid one-member chain unloadable.
        out[name] = ref
    return out


def _fields(block, where, problems):
    """Extractable facts a stage declares about its OWN output (CR-6):

        "fields": {"lane":   {"from": "labelled-line", "label": "LANE"},
                   "format": {"from": "regex", "pattern": "^FORMAT:\\s*(\\S+)"}}

    A field is a NAME and one flat way to read it. Declarative on purpose:
    there is no code in a definition, so a reader of chain.json can see what a
    run will pull out of a stage without running it, and nothing under
    `chains/` is ever executed.

    The two forms cover the two things a prompt actually asks for. A
    LABELLED-LINE field reads `LABEL: value` off the output — the shape a
    prompt gets back when it asks for one answer on its own line. A REGEX field
    captures exactly one group; `groups != 1` is refused HERE so a pattern that
    could return a tuple never reaches a run, and a pattern that will not
    compile is a malformed chain rather than a stage that dies mid-run.

    Declaring a field costs a chain nothing until something references it, and
    a stage declaring none carries no `fields` key anywhere — not an empty one.
    """
    out = {}
    if block is None:
        return out
    if not isinstance(block, dict):
        problems.append(where + ": `fields` must be an object of name -> "
                                "{from, ...}")
        return out
    for name in sorted(block):
        entry = block[name]
        if not FIELD_RE.match(name or ""):
            problems.append(
                where + ": field name {0!r} is not a valid identifier — letters, "
                "digits, dash and underscore, and NO DOT, because "
                "'@<stage>.<field>' splits on the first one".format(name))
            continue
        if not isinstance(entry, dict):
            problems.append(where + ": field {0!r} must be an object declaring "
                            "`from`".format(name))
            continue
        unknown = sorted(set(entry) - FIELD_KEYS)
        if unknown:
            problems.append(where + ": field {0!r} unknown key(s): ".format(name)
                            + ", ".join(unknown) + " (known: "
                            + ", ".join(sorted(FIELD_KEYS)) + ")")
        how = entry.get("from")
        if how not in FIELD_FROMS:
            problems.append(where + ": field {0!r} `from` must be one of {1}; "
                            "got {2!r}".format(name, ", ".join(FIELD_FROMS), how))
            continue
        if "label" in entry and "pattern" in entry:
            problems.append(
                where + ": field {0!r} declares both a `label` and a `pattern` "
                "— one field, one way to read it".format(name))
            continue
        if how == "labelled-line":
            label = entry.get("label")
            if not isinstance(label, str) or not label.strip():
                problems.append(
                    where + ": field {0!r} is a labelled-line field, so it needs "
                    "a non-empty `label` — the text before the colon on the line "
                    "it reads".format(name))
                continue
            if "pattern" in entry:
                problems.append(where + ": field {0!r} is a labelled-line field "
                                "and carries a `pattern`".format(name))
                continue
            out[name] = {"from": how, "label": label}
            continue
        pattern = entry.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            problems.append(
                where + ": field {0!r} is a regex field, so it needs a non-empty "
                "`pattern` with exactly one capture group".format(name))
            continue
        if "label" in entry:
            problems.append(where + ": field {0!r} is a regex field and carries "
                            "a `label`".format(name))
            continue
        try:
            compiled = re.compile(pattern, re.M)
        except re.error as exc:
            problems.append(where + ": field {0!r} `pattern` will not compile: "
                            "{1}".format(name, exc))
            continue
        if compiled.groups != 1:
            problems.append(
                where + ": field {0!r} `pattern` has {1} capture group(s); a "
                "field is exactly ONE captured value, so a pattern that could "
                "hand back a tuple is refused here rather than at run time"
                .format(name, compiled.groups))
            continue
        out[name] = {"from": how, "pattern": pattern}
    return out


def _when(block, where, key, seen_before, fields_of, problems):
    """The stage GATE (CR-5) — a stage runs only when a predicate holds:

        "when": {"field": "@triage.lane", "equals": "ORGANIC"}
        "when": {"field": "@triage.lane", "in": ["ORGANIC", "UGC"]}

    Returns the declaration verbatim (so the record can state it in its
    author's own words) or None. Every refusal below exists because its silent
    version is worse than a malformed chain:

    ONE FIELD, ONE TEST. `equals` or `in`, never both and never neither, over
    exactly one field of one earlier stage. There is no `and`, no `or`, no
    `not`, and no expression string — the DAG kill line applies here first, and
    an expression language is how a data file quietly becomes a program.

    THE FIELD MUST BE DECLARED. `field` is a `@<earlier-stage>.<field>`
    reference and nothing else: not `@config.<var>` (a gate on a run-config
    value is a flag, not a chain deciding on its own output), not a whole stage
    output, and not a selector form. It is bound by the same ordering rule as
    an input, so a gate can only read what has already run, and by the same
    declaration rule, so a chain gated on a fact nobody arranged to extract is
    refused at compile rather than skipping half a run.

    COMPARISON IS EXACT STRING EQUALITY. An extracted value is text the
    extractor already stripped; nothing here lowercases, trims further or
    coerces. A gate that quietly matched `Organic` against `ORGANIC` would be
    an engine deciding what a chain's author meant.
    """
    if block is None:
        return None
    if not isinstance(block, dict):
        problems.append(where + ": `when` must be an object — "
                        "{\"field\": \"@<stage>.<field>\", \"equals\": \"...\"} "
                        "or the same with `in`")
        return None
    unknown = sorted(set(block) - WHEN_KEYS)
    if unknown:
        problems.append(
            where + ": `when` unknown key(s): " + ", ".join(unknown) +
            " (known: " + ", ".join(sorted(WHEN_KEYS)) + "). A gate is FLAT — "
            "one field, one test. There is no `and`, `or`, `not` or expression "
            "form, because a chain needing one is a chain asking for a "
            "dependency graph.")
        return None

    ok = True
    ref = block.get("field")
    target_kind, body, selector, name = parse_ref(ref)
    if target_kind is None:
        problems.append(
            where + ": `when.field` must be a reference to an earlier stage's "
            "extracted field — '@<earlier-stage-key>.<field>'; got {0!r}"
            .format(ref))
        ok = False
    elif target_kind == "config":
        problems.append(
            where + ": `when.field` is {0!r} — a gate reads a FIELD A STAGE "
            "EXTRACTED, never run-config. A run-config value is known before "
            "the run starts, so gating on one is a flag the caller already "
            "holds; the point of `when` is a stage deciding at run time."
            .format(ref))
        ok = False
    elif selector is not None:
        problems.append(
            where + ": `when.field` is {0!r} — a gate carries no selector. "
            "'#pick' selects a version out of a whole output and '*' fans in "
            "every member's; neither has a reading over one extracted value."
            .format(ref))
        ok = False
    elif name is None:
        problems.append(
            where + ": `when.field` is {0!r}, a whole stage output. A gate is a "
            "predicate over ONE EXTRACTED FIELD — write "
            "'@{1}.<field>' and declare that field on stage {1!r}."
            .format(ref, body))
        ok = False
    elif not KEY_RE.match(body or ""):
        problems.append(where + ": `when.field` {0!r} does not name a stage"
                        .format(ref))
        ok = False
    elif key is None:
        # The stage key is already an error above; an ordering complaint on top
        # of it would point at the wrong line.
        ok = False
    elif body == key:
        problems.append(
            where + ": `when.field` {0!r} gates the stage on its own output — "
            "a stage cannot decide whether to run from a fact it produces by "
            "running".format(ref))
        ok = False
    elif body not in seen_before or seen_before[body] >= seen_before[key]:
        problems.append(
            where + ": `when.field` {0!r} reads {1!r}, which is not an EARLIER "
            "stage. Array order is run order, so a gate can only read what has "
            "already run.".format(ref, body))
        ok = False
    else:
        declared = fields_of.get(body) or {}
        if name not in declared:
            problems.append(
                where + ": `when.field` reads field {0!r} of stage {1!r}, which "
                "declares {2}. A gate is referenceable only where the stage "
                "producing it declared HOW to read it — otherwise a chain "
                "decides whether to run a stage on a fact nobody arranged to "
                "extract.".format(name, body,
                                  ", ".join(sorted(declared)) or "no fields"))
            ok = False

    tests = [test for test in WHEN_TESTS if test in block]
    if len(tests) != 1:
        problems.append(
            where + ": `when` must carry exactly one of " +
            ", ".join("`{0}`".format(t) for t in WHEN_TESTS) +
            "; got {0}. One field, one test: two tests would be a compound "
            "predicate and none is a gate that says nothing."
            .format(", ".join("`{0}`".format(t) for t in tests) or "neither"))
        return None

    if "equals" in block:
        value = block["equals"]
        if not isinstance(value, str) or not value:
            problems.append(
                where + ": `when.equals` must be a non-empty string — an "
                "extracted field is text, and a field that could not be read "
                "never becomes a value at all (it fails the stage)")
            ok = False
    else:
        values = block["in"]
        if not isinstance(values, list) or not values:
            problems.append(where + ": `when.in` must be a non-empty list of "
                                    "strings")
            ok = False
        elif [v for v in values if not isinstance(v, str) or not v]:
            problems.append(where + ": `when.in` must hold non-empty strings — "
                                    "an extracted field is text")
            ok = False
        elif len(set(values)) != len(values):
            problems.append(
                where + ": `when.in` repeats a value — a membership test with a "
                "duplicate in it is a list nobody has read")
            ok = False

    if not ok:
        return None
    return dict(block)


def _media(block, where, inputs, problems):
    """Non-text stage inputs, declared and typed:

        "media": {"source": {"kind": "video", "ref": "@config.source_video"}}

    A media entry resolves to a LOCATION — a path or a URI supplied by the
    run-config — which rides the model seam as a typed `MediaInput` and is ALSO
    substituted into the prompt wherever the stage's dialect names it. Both,
    deliberately: the seam is what a vendor needs, and the substitution is what
    the machine these prompts were copied from does with an image path, so
    dropping it would invent a parity difference.

    `ref` may only be `@config.<var>`. A stage output is text this engine wrote;
    calling it a video would make the type a label rather than a fact. One entry
    is one location — a stage wanting many frames declares many entries, or one
    location naming a DIRECTORY, which is the runner's business below the seam
    and not a shape this schema should grow a branch for.
    """
    out = {}
    if block is None:
        return out
    if not isinstance(block, dict):
        problems.append(where + ": `media` must be an object of name -> "
                                "{kind, ref}")
        return out
    for name in sorted(block):
        entry = block[name]
        if not VAR_RE.match(name or ""):
            problems.append(where + ": media name {0!r} is not a valid "
                            "identifier".format(name))
            continue
        if name in inputs:
            problems.append(
                where + ": {0!r} is declared as both an input and a media entry "
                "— one name, two values, and the prompt would get whichever the "
                "engine happened to substitute last".format(name))
            continue
        if not isinstance(entry, dict):
            problems.append(where + ": media {0!r} must be an object with "
                            "`kind` and `ref`".format(name))
            continue
        unknown = sorted(set(entry) - MEDIA_KEYS)
        if unknown:
            problems.append(where + ": media {0!r} unknown key(s): ".format(name)
                            + ", ".join(unknown) + " (known: "
                            + ", ".join(sorted(MEDIA_KEYS)) + ")")
        kind = entry.get("kind")
        if kind not in MEDIA_KINDS:
            problems.append(where + ": media {0!r} `kind` must be one of {1}; "
                            "got {2!r}".format(name, ", ".join(MEDIA_KINDS),
                                               kind))
        ref = entry.get("ref")
        target_kind, body, selector, _field = parse_ref(ref)
        if target_kind != "config" or selector is not None:
            problems.append(
                where + ": media {0!r} `ref` must be '@config.<var>' — media "
                "arrives as a location the run supplies, never as a stage's "
                "text output; got {1!r}".format(name, ref))
            continue
        if not VAR_RE.match(body or ""):
            problems.append(where + ": media {0!r} names an invalid config "
                            "variable {1!r}".format(name, body))
            continue
        out[name] = {"kind": kind, "ref": ref}
    return out


# ---------------------------------------------------------------- resolution

def resolve_prompt(prompts_dir, declared, version):
    """(path, None) or (None, why) — the prompt-version resolution ladder.

    With a version V, in order:   <declared>/<V>.md      <declared>.<V>.md
    Without one, in order:        <declared>/prompt.md   <declared>.md

    Two shapes because both are reasonable: a directory per stage holding its
    versions, or a flat file per stage. The RESOLVED path is recorded in the
    run record, so nobody has to re-derive which file a run actually read.

    THERE IS NO "LATEST". A version is declared or it is absent; the engine
    never picks the highest-numbered file it can find. Implicit latest is how a
    chain changes behaviour with nobody having changed the chain.
    """
    stem = str(declared)
    if os.path.isabs(stem) or _escapes(stem):
        return None, ("`prompt` {0!r} leaves prompts_dir — a chain reads its "
                      "own prompts and nothing above them".format(stem))
    if version:
        candidates = ["{0}/{1}.md".format(stem, version),
                      "{0}.{1}.md".format(stem, version)]
    else:
        candidates = ["{0}/prompt.md".format(stem), "{0}.md".format(stem)]
    for candidate in candidates:
        found = _under(prompts_dir, candidate)
        if found is not None and found.is_file():
            return found, None
    return None, ("no prompt file for {0!r}{1} — looked for {2} under {3}"
                  .format(stem,
                          " version " + version if version else
                          " (no version declared)",
                          ", ".join(candidates), prompts_dir))


def _escapes(relative):
    """True if a relative path walks out of its base."""
    return os.path.normpath(str(relative)).startswith("..")


def _under(base, relative):
    """`base/relative` if it stays under `base`, else None. The READ-side twin
    of the out-dir jail: a chain reads only what it owns."""
    root = os.path.realpath(os.path.abspath(str(base)))
    if os.path.isabs(str(relative)):
        return None
    candidate = os.path.normpath(os.path.join(root, str(relative)))
    if candidate != root and not candidate.startswith(root + os.sep):
        return None
    return Path(candidate)
