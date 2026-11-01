# chains/ — one directory per chain

    chains/<chain>/chain.json          the spec, and THE CONTRACT
    chains/<chain>/prompts/...         the prompt files that spec resolves

The directory name and `chain.json`'s `chain` key must agree — the runner
refuses them otherwise, because a run that names one chain and executes
another is the failure nobody catches by reading output.

**A chain is DATA, not code.** Nothing under `chains/` is imported, executed
or branched on by `runner/`; the engine reads a spec and prompt text and knows
nothing else about any particular chain. That is what keeps a second chain
cheap — the reason the team ruled chain-within-component (2026-08-31) rather than
chains as an external dataset.

**Brand-agnostic (workspace rule 7).** No chain here may be named for a brand
or hard-code one in its prompts. Brand-shaped facts arrive as run-config
variables and a stage references them as `@config.<name>`.

The schema, the prompt-version ladder, the `@stage` piping grammar and the
provenance block are documented once, in `../CLAUDE.md`. This file is a map,
not a second copy of the contract.

**Empty at CR-1, by scope.** The engine lands first and alone; the
video-teardown chain arrives with card CR-2, copied at a pinned sha with that
sha and its source path recorded in the spec's `provenance` block. The field
is in the schema from CR-1 precisely so that copy has somewhere to be honest.

**`video-teardown/` is GENERATED, never hand-edited (CR-2).** It is a snapshot
of what the owner's own resolver picks at a pin, produced by

    python3 new-workflow-design/builds/chain-runner/import_vt_at_pin.py \
        --sha <pin> --route ai --write

and re-produced by running that again. Editing a copied prompt in place, or a
stage in its `chain.json`, breaks the one claim the directory makes — that
these files ARE his files at that sha — and the declared test's digest check
will say so. A change wanted here is a change to his prompts and a new pin, or
a card of its own. `PARITY-HARNESS.md`, beside that tool, is how the copy is
judged against his machine.

**`copy-general/` is RESOLVED from the copy machine, `tools/copywriter` (`lab/damon/copy` until 2026-09-19), same discipline (CM-1 (copy resolution)).**
Its prompts are copied by

    python3 new-workflow-design/builds/copy-machine/resolve_copy_chain.py --write

which runs HIS `latest_prompt()` over his own `STAGES` list, copies what it
picks and fills the provenance digests. His copy machine is the authored upstream and is
canonical until the CM-2 goldens pass; when it moves, RE-RESOLVE — never edit
our copy in place. Two things this chain has that the vt one does not: it
declares a CR-6 field (`lane`, off the triage stage) and the CR-5 gate that
routes on it, and it keeps its language-layer stage map beside `chain.json` in
`language-profile.json`, because a stage map is the CHAIN's definition and
the owner curates his own.

`copy-general` is a NEUTRAL WORKING NAME. the owner has not named this chain yet
(I-82, copy-machine participation); the build's ruling is that the name is his
and is not `copy`, which shadows a stdlib module. Renaming is one `git mv` plus
the `chain` field.
