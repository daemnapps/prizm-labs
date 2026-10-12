#!/usr/bin/env python3
"""Every key, read through the one loader in components/keys.

SI-193 (video-teardown keys reader): this file no longer reads key files
itself. It delegates to components/keys/loader.py — key(NAME) — which looks
in the environment, then (only when the managed file ~/.workflow-worker.env
is absent) the old places: the Keychain (service `daemn-<NAME>`, account
`damon`, through `~/.daemn/daemn_keys.py`), then `~/.daemn/keys.env`, then
`~/.apify.env`, then `~/.gemini.env`. That is the order this file always
used: the environment wins, then the Keychain.

The managed file is NEVER opened or parsed here — its existence only marks
the mini. On the mini a job sees exactly its own environment's keys
(WM-14 (scoped job env)): all_keys() lists the environment's credential-
looking names and nothing else.

The public names stay — VAULT, LEGACY, KEYCHAIN, all_keys, get, export,
status — so every caller is unchanged. No value is ever printed.
"""

import importlib.util
import os, sys
from pathlib import Path

VAULT = Path.home() / ".daemn" / "keys.env"
LEGACY = [Path.home() / ".gemini.env", Path.home() / ".apify.env"]
KEYCHAIN = Path.home() / ".daemn"

# components/keys/loader.py, by path under its own module name — never on
# sys.path, so it cannot shadow or be shadowed by another `loader`.
_REPO = Path(__file__).resolve().parents[3]
_LOADER_PATH = _REPO / "components" / "keys" / "loader.py"
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


_loader = _load_loader()

# An environment name is a key when it looks like one.
_KEY_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _is_key_name(n):
    return (n.endswith(_KEY_SUFFIXES) or n == "DATABASE_URL"
            or n in _loader.ALIASES or n in _loader.ALIASES.values())


def _keychain_names():
    """The names the Keychain helper knows. Silent if it is not set up."""
    folder = Path(os.path.expanduser(_loader.KEYCHAIN_DIR))
    if not (folder / "daemn_keys.py").is_file():
        return []
    try:
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
        import daemn_keys
    except Exception:
        return []
    try:
        return list(daemn_keys.names())
    except Exception:
        try:
            return list(daemn_keys.KNOWN)
        except Exception:
            return []


def _parse(p):
    """The NAMES in a NAME=value file; values are read by the loader."""
    out = set()
    try:
        text = Path(os.path.expanduser(str(p))).read_text()
    except Exception:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        out.add(line.partition("=")[0].strip())
    return out


def all_keys():
    """{name: value} for the environment's key names, plus — off the mini —
    every name the old files and the Keychain hold; each value from the loader."""
    names = {n for n in os.environ if _is_key_name(n)}
    if not _loader.fallback_skipped():
        for src in _loader.FALLBACK:
            if src != "keychain":
                names.update(_parse(src))
        names.update(_keychain_names())
    found = {}
    for n in sorted(names):
        v = _loader.key(n, required=False)
        if v:
            found[n] = v
    return found


def get(name, required=True):
    v = _loader.key(name, required=False)
    if not v and required:
        try:
            _loader.key(name)
            why = "not found"
        except KeyError as e:
            why = e.args[0] if e.args else "not found"
        sys.exit(f"No {name} yet — {why}\n")
    return v


def export():
    """Put every key into this process's environment."""
    for k, v in all_keys().items():
        os.environ.setdefault(k, v)


def status():
    ks = all_keys()
    if not ks:
        return "No keys found — none in the Keychain and none in the old files"
    return "\n".join(f"  {k:<24} set ({len(v)} chars)" for k, v in sorted(ks.items()))


if __name__ == "__main__":
    print(f"Keys, from {VAULT}:\n{status()}")
