#!/usr/bin/env python3
"""One place for every key: the macOS Keychain.

Keys live in the Keychain, encrypted at rest — service `daemn-<NAME>`, account
`damon`, read through `~/.daemn/daemn_keys.py`. They used to sit in plain text
in `~/.daemn/keys.env`; that file moved on 2026-09-11 and anything still
reading it found an empty file and reported every key as missing.

The old files are still read first as a fallback, so a machine that has not
migrated keeps working. The Keychain wins wherever both have a name.
"""

import os, sys
from pathlib import Path

VAULT = Path.home() / ".daemn" / "keys.env"
LEGACY = [Path.home() / ".gemini.env", Path.home() / ".apify.env"]
KEYCHAIN = Path.home() / ".daemn"


def _keychain():
    """Every key the Keychain holds. Silent if it is not set up on this Mac."""
    try:
        if str(KEYCHAIN) not in sys.path:
            sys.path.insert(0, str(KEYCHAIN))
        import daemn_keys
    except Exception:
        return {}
    out = {}
    try:
        names = daemn_keys.names()
    except Exception:
        try:
            names = list(daemn_keys.KNOWN)
        except Exception:
            return {}
    for n in names:
        try:
            v = daemn_keys.key(n)
        except Exception:
            v = None
        if v:
            out[n] = v
    return out


def _parse(p):
    out = {}
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def all_keys():
    found = {}
    for p in LEGACY:
        found.update(_parse(p))
    found.update(_parse(VAULT))
    found.update(_keychain())         # the Keychain wins
    found.update({k: v for k, v in os.environ.items() if k in found})
    return found


def get(name, required=True):
    v = all_keys().get(name) or os.environ.get(name)
    if not v and required:
        sys.exit(f"No {name} yet. It belongs in the Keychain:\n\n"
                 f"    python3 "
                 f"email-production/secrets.py --add {name}\n")
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
