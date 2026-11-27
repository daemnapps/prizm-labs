"""Every audio-teardown key, read by name through the one loader in components/keys.

Every key this tool uses: GEMINI_API_KEY (words, voices, music, effects — every
language), ELEVENLABS_API_KEY (who speaks when), AUDD_API_TOKEN (naming the
music; optional — music.py says "no AudD key" and carries on without it).

SI-194 (readers use loader), audio-teardown: key(NAME) no longer imports
~/.daemn/daemn_keys itself. It asks components/keys/loader.py: the environment
first, then the one key file ~/.upright-keys.env (add NAME=value there). Only
on a machine with no key file yet, and not on the mini, the loader still falls
back to the old places. On the mini a job sees only the keys its own
environment carries.

key() RAISES: a missing key, or a value still holding a 'PASTE' placeholder, is
a RuntimeError naming the key and the places the loader looked — never a value.
missing() is that message on its own. The loader is loaded by path under its own
module name, as image-teardown's it_keys.py does — never on sys.path.
Python 3.9-clean, stdlib only.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Found, not counted: the first folder above that holds components/keys/loader.py.
_LOADER_PATH = next((r / "components" / "keys" / "loader.py" for r in HERE.parents
                     if (r / "components" / "keys" / "loader.py").is_file()),
                    HERE.parents[1] / "components" / "keys" / "loader.py")
_LOADER_NAME = "upright_keys_loader"


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


def missing(name):
    """Why `name` was not found: the key and the places the loader looked. Never a value."""
    try:
        _load_loader().key(name, required=True)
    except KeyError as e:
        return str(e.args[0]) if e.args else "missing key %s" % name
    except Exception:
        pass
    return "missing key %s; the key loader (components/keys/loader.py) could not be asked" % name


def key(name):
    """The value of `name`; RuntimeError (the key and where it was looked for) when it is not set."""
    try:
        v = _load_loader().key(name, required=False)
    except Exception:
        v = None
    if not v:
        raise RuntimeError(missing(name))
    if "PASTE" in v:
        raise RuntimeError("no %s: the value found is a placeholder, not a key" % name)
    return v
