"""identity-training — the identity engine, as a component.

The substance lives in `engine`; `train_identity.py` at the component root is
the CLI entry point. `components/video-teardown/machine/train_identity.py` is
a shim over this same module, so owner's machine runs this code unchanged.
"""

from . import engine          # noqa: F401
