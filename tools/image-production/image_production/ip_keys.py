"""Every image-production key, read through the one loader in components/keys.

SI-194 (readers use loader), dispatch 4: `route.key_value` and
`static/tools/gemini_image.py` no longer import ~/.daemn/daemn_keys or open
~/.gemini.env themselves. They ask key(NAME), which asks
components/keys/loader.py: the environment first, then — only when the mini
marker ~/.workflow-worker.env is absent — the old places (the Keychain through
~/.daemn/daemn_keys.py, then ~/.daemn/keys.env, ~/.apify.env, ~/.gemini.env).
`judge.py`, `providers.py` and `dryrun.py` already ask `route.key_value`, so
they read through here unchanged. `static/queue/queue.py` is not a reader
here — it imports video-teardown's keys.py, which reads through the loader
since SI-193 (video-teardown keys reader).

key() never raises; a missing key is None. missing() is the reader's message
for that case — the key and where the loader looked, never a value. The loader
is loaded by path under its own module name, as image-teardown's it_keys.py
does — never on sys.path. This file has no relative import, so
gemini_image.py can load it by path too. Python 3.9-clean, stdlib only.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Found, not counted: the first folder above that holds components/keys/loader.py.
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
    """The value of `name`, stripped, or None — never raises, never prints."""
    if not name:
        return None
    try:
        v = _load_loader().key(name, required=False)
        return (v.strip() or None) if isinstance(v, str) else None
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
