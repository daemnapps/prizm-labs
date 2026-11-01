#!/usr/bin/env python3
"""chain-runner — run a staged prompt chain. A RUN IS ONE COMMAND.

    python3 components/chain-runner/runner/run.py <chain> --out <dir>

`<chain>` is a key under `components/chain-runner/chains/`, so the command
above reads `chains/<chain>/chain.json` and its prompts, and writes everything
it produces under `--out` and nowhere else.

    --out DIR            where the run lands. REQUIRED, and the only place
                         this command writes. There is no default: a default
                         run root is how run output ends up inside a checkout.
    --chains-dir DIR     where chains live (default: the component's own
                         `chains/`). Fixture trees use this.
    --chain-file PATH    run a chain.json directly, instead of by key.
    --config FILE        run-config: a flat JSON object of variable names to
                         string values, referenced by a chain as
                         `@config.<name>`.
    --var NAME=VALUE     one run-config variable; repeatable; wins over
                         --config.
    --root NAME=PATH     one named content root, overriding a chain's declared
                         default of that name; repeatable. A root is an opaque
                         name here — what a root may POINT AT is checked (see
                         below), what it contains never is.
    --model-runner NAME  the model seam's implementation (default: stub —
                         the only one CR-1 registers).
    --check              validate the chain and report. Writes NOTHING, does
                         not create --out.
    --no-stamp           skip stamp.json, the run's only wall clock.
    --quiet              no progress on stderr; the exit code still speaks.

BRAND ENTERS ONLY HERE (workspace rule 7). Run-config variable names are
opaque to this engine: it substitutes them and records them, and there is no
field anywhere in `runner/` where a brand could be named. A brand-specific
chain is a chain, or a config file — never a branch in this code.

AND IT ENTERS FROM ONE PLACE (components/CLAUDE.md rule 9, "brand home"). A
declared root whose PATH SHAPE says it is a brand tree somewhere other than
`brands/<brand>/` is a FINDING, reported by `brandhome.py` before anything
runs: with --check it is printed and the command exits non-zero; without it the
run is refused, having written nothing. Detection is by path shape only and is
silent when the shape is ambiguous — prose review covers what a path cannot
say, and a false finding is worse here than a missed one.

CREDENTIALS ARE NOT RUN-CONFIG. Run-config is recorded verbatim in run.json,
so a secret passed as a `--var` would be written to disk in the clear. Vendor
keys reach a real model runner through the environment, scoped by the job's
grant row in `platform/workers/mini-worker/job_env.py`, and CR-1's stub reads
none of them.

EXIT CODES, because a caller needs to tell the failures apart:
    0  the run completed
    2  the chain spec is malformed (nothing was written, --out not created),
       INCLUDING a rule-9 finding against a root the CHAIN declares
    3  an OUT-DIR VIOLATION — a write was attempted outside --out
    4  the chain is valid but could not run on this config/invocation,
       INCLUDING a rule-9 finding against a root THIS INVOCATION declares
    1  anything unforeseen
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from runner import brandhome, engine, models, outdir, spec as chainspec
else:
    from . import brandhome, engine, models, outdir, spec as chainspec

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
sys.path.append(str(COMPONENT.parent / "run-kit"))     # appended, never ahead of this runner
from run_kit import paths as _rk_paths  # noqa: E402  the one workspace locator (triage page 12)
DEFAULT_CHAINS = COMPONENT / "chains"

EXIT_OK = 0
EXIT_UNFORESEEN = 1
EXIT_SPEC = 2
EXIT_OUTDIR = 3
EXIT_RUN = 4


def repo_root(start):
    """The checkout `start` sits in, or None.

    Two readers, and neither reads anything OUT of the tree: the out-dir
    warning (an out root inside a working tree) and `load_roots`, which needs
    the frame a chain's relative root paths are written against.
    """
    s = Path(start).resolve()
    try:
        root = Path(_rk_paths.repo(s)).resolve()
    except FileNotFoundError:
        return None
    if root != s and root not in s.parents:
        return None             # AI_WORKSPACE names a tree `start` is not in
    return root


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="chain-runner",
        description="Run a staged prompt chain. A run is one command.")
    parser.add_argument("chain", nargs="?",
                        help="chain key under --chains-dir")
    parser.add_argument("--out", dest="out", default=None,
                        help="the run directory — the ONLY place this writes")
    parser.add_argument("--chains-dir", dest="chains_dir",
                        default=str(DEFAULT_CHAINS))
    parser.add_argument("--chain-file", dest="chain_file", default=None)
    parser.add_argument("--config", dest="config", default=None)
    parser.add_argument("--var", dest="vars", action="append", default=[],
                        metavar="NAME=VALUE")
    parser.add_argument("--member", dest="members", action="append", default=[],
                        metavar="NAME",
                        help="one member of this run's group; repeatable, and "
                             "order is the fan-in order. Member-scoped stages "
                             "run once per member under members/<NAME>/; a "
                             "group stage reads them all through '@<stage>*'. "
                             "With none given a run has exactly one, unnamed, "
                             "and every path is what it was before.")
    parser.add_argument("--root", dest="roots", action="append", default=[],
                        metavar="NAME=PATH",
                        help="one named content root, overriding the chain's "
                             "declared default of that name; repeatable")
    parser.add_argument("--model-runner", dest="model_runner", default="stub")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-stamp", dest="stamp", action="store_false",
                        default=True)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def load_config(args):
    values = {}
    if args.config:
        path = Path(args.config)
        if not path.is_file():
            raise Fault(EXIT_RUN, "--config: no such file: " + str(path))
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise Fault(EXIT_RUN,
                        "--config: {0} is not valid JSON: {1}".format(path, exc))
        if not isinstance(document, dict):
            raise Fault(EXIT_RUN, "--config: {0} must hold a flat object of "
                                  "name -> value".format(path))
        for name in document:
            value = document[name]
            if not isinstance(value, (str, int, float, bool)):
                raise Fault(EXIT_RUN,
                            "--config: {0!r} must be a scalar; run-config is "
                            "substituted into prompt text".format(name))
            values[str(name)] = value if isinstance(value, str) else json.dumps(value)
    for item in args.vars:
        if "=" not in item:
            raise Fault(EXIT_RUN, "--var expects NAME=VALUE; got " + repr(item))
        name, value = item.split("=", 1)
        if not name:
            raise Fault(EXIT_RUN, "--var expects NAME=VALUE; got " + repr(item))
        values[name] = value
    return values


ROOT_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")


def load_roots(args, spec):
    """The named content roots this run declares — the chain's own defaults
    first, then `--root NAME=PATH`, which wins on the name.

    A root is an OPAQUE NAME to this engine, exactly like a run-config
    variable: it says where content comes from, never what the content is. The
    only thing done with one here is the rule-9 (brand home) check below, which
    reads its PATH and nothing else.

    Relative paths resolve differently by origin, because the two are written
    by different people for different readers. A CHAIN-declared root is
    relative to the chain's own checkout when it has one — the workspace is the
    frame a chain names content in — and to the chain directory otherwise. A
    `--root` path is relative to the working directory, because that is what a
    shell means by it.
    """
    rows = {}
    order = []
    base = repo_root(spec.chain_dir) or spec.chain_dir
    for name in sorted(spec.roots):
        rows[name] = {"name": name, "declared": spec.roots[name],
                      "origin": "chain",
                      "path": os.path.join(str(base), spec.roots[name])}
        order.append(name)
    for item in args.roots:
        if "=" not in item:
            raise Fault(EXIT_RUN, "--root expects NAME=PATH; got " + repr(item))
        name, declared = item.split("=", 1)
        if not ROOT_RE.match(name or "") or not declared:
            raise Fault(EXIT_RUN,
                        "--root expects NAME=PATH — a root name is an "
                        "identifier and its path is not empty; got "
                        + repr(item))
        if name not in rows:
            order.append(name)
        rows[name] = {"name": name, "declared": declared, "origin": "--root",
                      "path": os.path.abspath(declared)}
    return [rows[name] for name in order]


def finding_exit(findings):
    """The exit code a set of findings earns, per the existing contract: a
    CHAIN-declared root is the chain being wrong (2, malformed spec), and a
    `--root` is this invocation being wrong (4). Both wrote nothing."""
    if [f for f in findings if f.origin == "chain"]:
        return EXIT_SPEC
    return EXIT_RUN


MEMBER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")


def load_members(args):
    """The run's group members, in the order given — and that order is the
    fan-in order, so it is preserved, never sorted.

    A member name becomes a DIRECTORY under --out, so it is validated the way a
    path segment has to be: no separators, no dots-only, no leading dash. The
    jail would catch an escape anyway; catching it here means the run refuses
    before it writes rather than halfway through.
    """
    seen = []
    for name in args.members:
        if not MEMBER_RE.match(name or ""):
            raise Fault(EXIT_RUN,
                        "--member {0!r}: a member name is a path segment under "
                        "--out — letters, digits, dash, dot and underscore, "
                        "starting with a letter or digit".format(name))
        if name in seen:
            raise Fault(EXIT_RUN,
                        "--member {0!r} twice — two members with one name write "
                        "one directory, and the second silently overwrites the "
                        "first".format(name))
        seen.append(name)
    return seen


class Fault(Exception):
    """An invocation problem with the exit code it should produce."""

    def __init__(self, code, message):
        self.code = code
        Exception.__init__(self, message)


def locate(args):
    """(chain.json path, chain key) — by key under --chains-dir, or direct."""
    if args.chain_file:
        if args.chain:
            raise Fault(EXIT_RUN, "give a chain key OR --chain-file, not both")
        path = Path(args.chain_file).resolve()
        return path, None
    if not args.chain:
        raise Fault(EXIT_RUN, "name a chain (a key under --chains-dir) or pass "
                              "--chain-file")
    chains = Path(args.chains_dir).resolve()
    path = chains / args.chain / "chain.json"
    if not path.is_file():
        available = []
        if chains.is_dir():
            available = sorted(child.name for child in chains.glob("*")
                               if (child / "chain.json").is_file())
        raise Fault(EXIT_SPEC,
                    "no chain {0!r}: {1} does not exist. Chains available in "
                    "{2}: {3}".format(args.chain, path, chains,
                                      ", ".join(available) or "none"))
    return path, args.chain


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    say = (lambda message: None) if args.quiet else \
        (lambda message: sys.stderr.write(message + "\n"))

    try:
        path, key = locate(args)
        config = load_config(args)
        members = load_members(args)
        # The NAME is checked here and the runner is LOADED below, after the
        # --check exit. A bad name fails before anything else happens; a real
        # runner's module — the one holding the HTTP client — is never imported
        # by the mode whose whole promise is that it does nothing.
        try:
            models.check_name(args.model_runner)
        except KeyError as exc:
            raise Fault(EXIT_RUN, str(exc.args[0]))

        try:
            spec = chainspec.load(path, chain_key=key)
        except chainspec.ChainSpecError as exc:
            sys.stderr.write("chain-runner: FAILED — " + str(exc) + "\n")
            sys.stderr.write("chain-runner: nothing was written.\n")
            return EXIT_SPEC

        # COMPILE VALIDATION, and it is the same step for both modes: a rule-9
        # (brand home) finding is a fact about the chain and this invocation,
        # not a fact about --check. So --check prints it and exits non-zero,
        # and a real run is refused here — before the out directory exists, so
        # a refused run has still written nothing.
        roots = load_roots(args, spec)
        findings = brandhome.findings(roots)

        if args.check:
            report(spec, args.model_runner, config, roots, say)
            for finding in findings:
                sys.stderr.write(
                    "chain-runner: FINDING — " + finding.message + "\n")
            if findings:
                sys.stderr.write(
                    "chain-runner: --check FAILED — {0} finding(s); nothing "
                    "written.\n".format(len(findings)))
                return finding_exit(findings)
            say("chain-runner: --check only — nothing written.")
            return EXIT_OK

        if findings:
            for finding in findings:
                sys.stderr.write(
                    "chain-runner: FINDING — " + finding.message + "\n")
            raise Fault(finding_exit(findings),
                        "{0} rule-9 (brand home) finding(s) — the run is "
                        "refused and nothing was written. `--check` reports "
                        "them without running.".format(len(findings)))

        try:
            runner = models.get(args.model_runner)
        except KeyError as exc:
            raise Fault(EXIT_RUN, str(exc.args[0]))
        except ImportError as exc:
            raise Fault(EXIT_RUN,
                        "model runner {0!r} is registered but will not load: "
                        "{1}. It is NOT falling back to the stub — a stub run "
                        "carrying a real runner's name in run.json is a fixture "
                        "presented as a result.".format(args.model_runner, exc))

        if not args.out:
            raise Fault(EXIT_RUN, "--out is required: name the directory this "
                                  "run writes into. There is no default, "
                                  "because a default run root is how run "
                                  "output ends up inside a checkout.")

        refusals, warnings = outdir.inspect_root(
            args.out, COMPONENT, repo_root(HERE))
        for warning in warnings:
            sys.stderr.write("chain-runner: WARNING — " + warning + "\n")
        if refusals:
            raise Fault(EXIT_OUTDIR, "; ".join(refusals))

        out = outdir.OutDir(args.out)
        stamp = None
        if args.stamp:
            stamp = {
                "chain": spec.key,
                "model_runner": args.model_runner,
                "at": datetime.datetime.now(
                    datetime.timezone.utc).replace(microsecond=0).isoformat(),
            }

        say("chain-runner: {0} — {1} stage(s) -> {2}".format(
            spec.key, len(spec.stages), out.root))
        record = engine.run(spec, out, config, runner,
                            model_runner_name=args.model_runner, stamp=stamp,
                            members=members)
        for row in record["stages"]:
            if row.get("skipped_by_gate"):
                # Said out loud, not left to the record: a stage that did not
                # run is the thing a person watching a run most needs told, and
                # a line quietly absent from the progress reads as a stage that
                # ran fine.
                say("  {0}. {1:<16} {2:<24} SKIPPED BY GATE — {3} read {4!r}"
                    .format(row["n"],
                            engine.unit_name(row["key"], row.get("member")),
                            "(gated off — no spend)",
                            row["gate"]["when"]["field"],
                            row["gate"]["value"]))
                continue
            say("  {0}. {1:<16} {2:<24} -> {3}".format(
                row["n"], engine.unit_name(row["key"], row.get("member")),
                row["model"] or "(no model — assemble)", row["output"]))
        say("chain-runner: ok — run.json in " + str(out.root))
        return EXIT_OK

    except outdir.OutDirViolation as exc:
        sys.stderr.write("chain-runner: FAILED — " + str(exc) + "\n")
        sys.stderr.write(
            "chain-runner: a run writes ONLY under --out. This is a hard rule, "
            "not a preference: the run is over.\n")
        return EXIT_OUTDIR
    except engine.RunError as exc:
        sys.stderr.write("chain-runner: FAILED — " + str(exc) + "\n")
        return EXIT_RUN
    except models.SeamError as exc:
        # The vendor call itself failed. A valid chain, correctly invoked, that
        # did not come back — same exit code as any other run failure, and the
        # partial output plus FAILED.txt say how far the spend got.
        sys.stderr.write("chain-runner: FAILED — model seam: " + str(exc) + "\n")
        return EXIT_RUN
    except models.MediaError as exc:
        # A valid chain, invoked with a media location the run could not
        # supply — the same class as a missing config variable, and it gets the
        # same exit code. Landing in `unforeseen` would tell a caller the
        # engine broke when what broke was the invocation.
        sys.stderr.write("chain-runner: FAILED — media: " + str(exc) + "\n")
        return EXIT_RUN
    except Fault as exc:
        sys.stderr.write("chain-runner: FAILED — " + str(exc) + "\n")
        return exc.code
    except KeyboardInterrupt:
        sys.stderr.write("chain-runner: interrupted.\n")
        return EXIT_UNFORESEEN


def gate_words(when):
    """A stage gate, in the words `--check` should print it in: `@a.lane ==
    'ORGANIC'`. The predicate is flat, so this is a rendering and never an
    interpretation — there is no operator here that the schema does not have."""
    if "equals" in when:
        return "{0} == {1!r}".format(when["field"], when["equals"])
    return "{0} in [{1}]".format(
        when["field"], ", ".join(repr(value) for value in when["in"]))


def report(spec, model_runner, config, roots, say):
    say("chain-runner: {0} — {1}".format(spec.key, spec.label))
    say("  spec:        " + str(spec.path))
    say("  prompts:     " + str(spec.prompts_dir))
    say("  placeholders: " + spec.placeholder_style)
    say("  provenance:  " + (
        "{0} @ {1}{2}".format(
            spec.provenance["source"], spec.provenance["sha"],
            " · route " + spec.provenance["route"]
            if spec.provenance.get("route") else "")
        if spec.provenance.get("source") else "none recorded"))
    # A gap is a place the imported chain cannot say what its source said. It
    # belongs in --check's output, because --check is what a person reads before
    # deciding a run is worth comparing to anything.
    for gap in spec.provenance.get("gaps") or []:
        say("  GAP:         " + gap)
    say("  runner:      " + model_runner)
    # Where a root RESOLVES is the fact the check below rules on, and a
    # declared relative path does not show it. A reader deciding whether a
    # finding is right needs the resolved path in front of them.
    for root in roots:
        say("  root {0}: {1} ({2} {3})".format(
            root["name"], root["path"], root["origin"], root["declared"]))
    needed = set()
    for stage in spec.stages:
        for name in stage.inputs:
            ref = stage.inputs[name]
            if ref.startswith("@config."):
                needed.add(ref[len("@config."):])
        for name in stage.media:
            needed.add(stage.media[name]["ref"][len("@config."):])
        # The seam a stage crosses is the fact a reader is deciding on: an
        # assemble stage costs nothing and a stage carrying video costs the
        # most, and neither is visible from a model id alone.
        binding = stage.model if stage.kind == "model" else "(assemble — no model)"
        carried = ", ".join("{0}:{1}".format(n, stage.media[n]["kind"])
                            for n in sorted(stage.media))
        # What a stage lets LATER stages route on is the other fact a reader is
        # deciding about, and it is invisible from a model id and an output path.
        extracts = ", ".join(sorted(stage.fields))
        # And whether the stage runs AT ALL is the third: a reader deciding
        # what a run will cost has to see the stages that may not happen.
        say("  {0}. {1:<16} {2:<24} prompt {3}{4} -> {5}{6}{7}{8}{9}".format(
            stage.index + 1, stage.key, binding, stage.prompt_declared,
            " " + stage.prompt_version if stage.prompt_version else "",
            stage.output,
            "  [scope: group]" if stage.scope == "group" else "",
            "  [media: " + carried + "]" if carried else "",
            "  [fields: " + extracts + "]" if extracts else "",
            "  [when: " + gate_words(stage.when) + "]" if stage.when else ""))
    absent = sorted(needed - set(config))
    if absent:
        say("  config MISSING: " + ", ".join(absent))
    elif needed:
        say("  config ok:      " + ", ".join(sorted(needed)))


if __name__ == "__main__":
    sys.exit(main())
