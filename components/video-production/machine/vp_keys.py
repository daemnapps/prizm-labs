#!/usr/bin/env python3
"""Every video-production key, read through the one loader in components/keys.

Keys env standard: every reader in this folder asks key(NAME), which asks
components/keys/loader.py: the environment first, then the one key file
~/.upright-keys.env (add NAME=value there). Only on a machine with no key
file yet does the loader fall back to the temporary old places.

A caller that passes local_env=True (sequence.py) also gets
machine/.env as the last resort — only on a machine with no key file yet; once
~/.upright-keys.env exists, or on the mini, it is never read.

Never raises; a missing key is None. Never prints or logs a value. The loader
is loaded by path under its own module name, as video-teardown's keys.py does
(SI-193 (video-teardown keys reader)) — never on sys.path.
"""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL_ENV = HERE / ".env"

_LOADER_PATH = HERE.parents[2] / "components" / "keys" / "loader.py"
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


def _local_env(name):
    """NAME's value from machine/.env, or None. Absent or unreadable → None."""
    try:
        text = LOCAL_ENV.read_text()
    except Exception:
        return None
    for line in text.splitlines():
        if line.strip().startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


def key(name, local_env=False):
    """The value of `name`, or None — never raises."""
    try:
        loader = _load_loader()
        v = loader.key(name, required=False)
        if v:
            return v
        if local_env and not loader.fallback_skipped() and not loader.has_key_file():
            return _local_env(name)
    except Exception:
        return None
    return None
