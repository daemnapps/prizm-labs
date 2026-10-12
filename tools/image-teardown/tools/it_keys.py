#!/usr/bin/env python3
"""Every image-teardown key, read through the one loader in components/keys.

SI-194 (readers use loader), dispatch 3: gpt_drafts.py, draft_judge.py,
carousel.py, gemini_image.py, gemini_text.py, pull_ig_image.py and check.py no
longer import ~/.daemn/daemn_keys or open ~/.gemini.env / ~/.apify.env
themselves. They ask key(NAME), which asks components/keys/loader.py: the
environment first, then — only when the mini marker ~/.workflow-worker.env is
absent — the old places (the Keychain through ~/.daemn/daemn_keys.py, then
~/.daemn/keys.env, ~/.apify.env, ~/.gemini.env). No local .env step:
image-teardown has none. tools/deliver.py is not a reader here — it imports
video-teardown's keys.py, which reads through the loader since SI-193
(video-teardown keys reader).

key() never raises; a missing key is None. missing() is the reader's message
for that case — the key and where the loader looked, never a value. The loader
is loaded by path under its own module name, as video-edit's ve_keys.py does —
never on sys.path. Python 3.9-clean, stdlib only.
"""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Found, not counted (this component's CLAUDE.md): the first folder above that
# holds components/keys/loader.py, the way check.py finds the swipe home.
_LOADER_PATH = next((r / "components" / "keys" / "loader.py" for r in HERE.parents
                     if (r / "components" / "keys" / "loader.py").is_file()),
                    HERE.parents[2] / "components" / "keys" / "loader.py")
_LOADER_NAME = "shared_keys_loader"


def _load_loader():
    mod = sys.modules.get(_LOADER_NAME)
    if mod is None:
        spec = importlib.util.spec_from_file_location(_LOADER_NAME, str(_LOADER_PATH))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[_LOADER_NAME] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            sys.modules.pop(_LOADER_NAME, None)
            raise
    return mod


def key(name):
    """The value of `name`, or None — never raises."""
    try:
        return _load_loader().key(name, required=False) or None
    except Exception:
        return None


def missing(name):
    """Why `name` was not found: the key and the places the loader looked. Never a value."""
    try:
        _load_loader().key(name, required=True)
    except KeyError as e:
        return str(e.args[0]) if e.args else "missing key %s" % name
    except Exception:
        pass
    return "missing key %s; the key loader (components/keys/loader.py) could not be asked" % name
