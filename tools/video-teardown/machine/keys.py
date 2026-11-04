#!/usr/bin/env python3
"""Every key, read through the one loader in components/keys.

SI-193 (video-teardown keys reader): this file no longer reads key files
itself. It delegates to components/keys/loader.py — key(NAME) — which looks
in the environment, then this repo's .env (add NAME=value there), then
Damon's Mac Keychain when its ~/.daemn helper exists (skipped on Windows).
The Upright key files (~/.upright-keys.env, ~/.daemn/keys.env, ~/.gemini.env,
~/.apify.env) are never read (disconnected 2026-11-03).

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

# Kept as public names so callers don't break. VAULT is this repo's .env; the
# Upright key files are not read any more (2026-11-03).
VAULT = Path(__file__).resolve().parents[3] / ".env"
LEGACY = []
KEYCHAIN = Path.home() / ".daemn"

# components/keys/loader.py, by path under its own module name — never on
# sys.path, so it cannot shadow or be shadowed by another `loader`.
_REPO = Path(__file__).resolve().parents[3]
_LOADER_PATH = _REPO / "components" / "keys" / "loader.py"
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


_loader = _load_loader()

# An environment name is a key when it looks like one.
_KEY_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")


def _is_key_name(n):
    return (n.endswith(_KEY_SUFFIXES) or n == "DATABASE_URL"
            or n in _loader.ALIASES or n in _loader.ALIASES.values())


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


def _keychain_names():
    """The names Damon's Keychain helper knows. Silent if it is not set up (Windows)."""
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


def all_keys():
    """{name: value} for the environment's key names, plus — off the mini —
    every name this repo's .env holds, or, with no .env, the names Damon's
    Keychain knows; each value from the loader."""
    names = {n for n in os.environ if _is_key_name(n)}
    if not _loader.fallback_skipped():
        if _loader.has_key_file():
            names.update(_parse(_loader.KEY_FILE))
        else:
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
        return "No keys found — add NAME=value to this repo's .env"
    return "\n".join(f"  {k:<24} set ({len(v)} chars)" for k, v in sorted(ks.items()))


if __name__ == "__main__":
    print(f"Keys, from {_loader.KEY_FILE}:\n{status()}")
