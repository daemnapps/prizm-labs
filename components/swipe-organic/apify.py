"""Moved to `components/apify/` (2026-09-22).

Two shared components and a dozen lab tools imported the Apify layer from
this personal folder, which meant a production component depended on one
person's lab — and the public copy of the research gatherer shipped with a
path that does not exist there.

The code now lives once, as a component. This re-export keeps every existing
import working; point new code at `components/apify/apify.py`.
"""
import importlib.util as _u
import sys as _sys
from pathlib import Path as _P

_sys.path.append(str(_P(__file__).resolve().parent.parent / "run-kit"))  # appended, never ahead
from run_kit.paths import repo as _repo  # noqa: E402  the one workspace locator (triage page 12)


def _ws():
    """Found by walking up. `parents[3]` was right only while this file sat in
    lab/; it moved to components/ on 2026-09-22 and pointed at ~/Projects.
    The walk is run-kit's paths.repo() (SI-111 (organic one locator))."""
    return _repo(__file__)

_src = _ws() / "components" / "apify" / "apify.py"
_spec = _u.spec_from_file_location("_apify_component", _src)
_mod = _u.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

globals().update({k: v for k, v in vars(_mod).items() if not k.startswith("__")})
