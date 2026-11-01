"""research-gatherer — the query-the-open-internet engine, as a component.

The substance lives in `engine`; `gather.py` at the component root is the
chain-agnostic CLI entry point (deep mode only — `inputs(st, chain_profile)`
is a library call, and a chain's own shim exposes it as `run`).
`components/video-teardown/machine/research.py` is a shim over this same
module, so that machine runs this code unchanged (the LL-1 precedent).
"""

from . import engine          # noqa: F401
