"""chain-runner's engine core (card CR-1).

INTERNALS. Nothing outside `components/chain-runner/` depends on any name in
this package (components/CLAUDE.md rule 2): the dependable surfaces are the
`chain.json` schema, the one-command invocation, and the run directory's
shape, all three declared in `components/chain-runner/CLAUDE.md`. A consumer
that needs something these do not carry gets a card, not an import.

    outdir.py   the out-dir jail — the ONLY write path in the component
    spec.py     chain.json: load, validate, resolve prompts and piping
    models.py   the model seam — one function boundary to any vendor
    vendors.py  the REAL runner, imported only by a run that names it
    engine.py   order, render, bind, write
    run.py      the command
"""

__all__ = ["outdir", "spec", "models", "engine"]
