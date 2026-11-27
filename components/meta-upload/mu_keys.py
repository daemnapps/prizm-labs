"""Every meta-upload key, read through the one loader in components/keys.

SI-194 (readers use loader), meta-upload dispatch: `meta.token()` no longer
runs `security find-generic-password` itself. It asks key(NAME), which asks
components/keys/loader.py: the environment first, then ~/.upright-keys.env (the one key file — add NAME=value there; when it exists nothing else is read) — and only on a machine with no key file — the temporary old places.
Every caller that builds `meta.Meta` (this folder's tools, copywriter's Door,
media-buying, creative-diversity) reads through here unchanged.

key() never raises; a missing key is None. missing() is the reader's message
for that case — the key and where the loader looked, never a value. The loader
is loaded by path under its own module name, as image-production's ip_keys.py
does — never on sys.path, and only when a key is asked. Named mu_keys, not
keys: four components put this folder on sys.path at 0, and a `keys` here would
shadow video-teardown's machine/keys.py. No relative import. Python 3.9-clean,
stdlib only.
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
