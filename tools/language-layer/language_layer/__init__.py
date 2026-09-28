"""language-layer — the customer-language query engine, as a component.

The substance lives in `engine`; `query_language.py` at the component root is
the CLI entry point. `components/video-teardown/machine/language.py` and
`lab/damon/copy/machine/language.py` are shims over this same module, so both
machines run this code unchanged.

`language_layer`, not `language` — a top-level `language` module would be one
more name on everybody's sys.path, and this component exists precisely because
two files with that name drifted apart.
"""

from . import engine          # noqa: F401
