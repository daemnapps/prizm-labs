"""gdrive-creator — the Drive pipe, as a component.

The substance lives in `engine`; `make_doc.py` at the component root is the
CLI entry point. `tools/video-teardown/machine/drive.py` is a shim over
this same module and `tools/copywriter/machine/gdoc_out.py` imports it directly,
so both machines run this code unchanged.

`gdrive_creator`, not `drive` — a top-level `drive` module is exactly the name
the copy lab was reaching for through a `sys.path.insert` into another
machine's folder, and `copy` was rejected under the same rule for shadowing
the stdlib.
"""

from . import engine          # noqa: F401
