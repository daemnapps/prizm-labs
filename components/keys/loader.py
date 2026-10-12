"""The one key loader — key(NAME) and load(names).

SI-192 (keys loader), keys Track A part 1: every reader that today opens a
file in someone's home folder asks here by NAME instead. The order is
(1) os.environ; (2) a TEMPORARY fallback to the old locations — the ~/.daemn
Keychain helper (only when daemn_keys.py exists; imported and called, never
edited), ~/.daemn/keys.env, ~/.apify.env, ~/.gemini.env — the order
video-teardown's keys.py uses. SI-192b (loader skips key file): the managed
file ~/.workflow-worker.env is NEVER opened or parsed. The worker loads it
into its own process only, and every job it spawns sees just the keys
job_env.py grants it (WM-14 (scoped job env)); a loader that read the file
would hand any job every key on the machine. Its EXISTENCE still marks the
mini: when it exists, or KEYS_NO_FALLBACK=1, step (2) is skipped entirely,
so on the mini a job sees exactly the keys in its own environment. A job that
needs another key gets a job_env.py grant, never a read of the file.
Guards: G-A1 (no renames) — ALIASES maps an old name to its canonical one and
either name finds the value; nothing is renamed anywhere, and removing an
alias is Track B. No value is ever printed, logged, raised or put on a
command line (database URLs go through pg_argv.for_psql); a missing required
key raises KeyError naming the key and the places looked, never a value.
Stdlib only, Python 3.9-clean. Named loader.py, not keys.py: video-production
imports video-teardown's machine/keys.py as `keys`.

    from loader import key, load
    token = key("APIFY_TOKEN")
    found = load(["GEMINI_API_KEY", "FAL_KEY"])
"""
import os
import re
import sys
from pathlib import Path

# old name -> canonical name (G-A1). Only pairs the tree states:
#   platform/workers/mini-worker/env.template:236-237 (DATABASE_URL canonical,
#   SUPABASE_DB_URL the accepted fallback) and :275-277 (HIGGSFIELD_* canonical,
#   HF_API_* the legacy alias).
ALIASES = {
    "SUPABASE_DB_URL": "DATABASE_URL",
    "HF_API_KEY_ID": "HIGGSFIELD_KEY_ID",
    "HF_API_KEY_SECRET": "HIGGSFIELD_KEY_SECRET",
}

# The mini marker only — checked for existence, never opened (SI-192b (loader skips key file)).
MANAGED = "~/.workflow-worker.env"
NO_FALLBACK_ENV = "KEYS_NO_FALLBACK"
# TEMPORARY (Track A): the old locations, read in this order. "keychain" is
# the ~/.daemn/daemn_keys.py helper, used only when that file exists.
FALLBACK = ("keychain", "~/.daemn/keys.env", "~/.apify.env", "~/.gemini.env")
KEYCHAIN_DIR = "~/.daemn"

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class Keys(dict):
    """load()'s result: a plain dict whose repr and str show names only."""

    def __repr__(self):
        return "Keys(%s)" % ", ".join(sorted(self))

    __str__ = __repr__


def _home(p):
    return Path(os.path.expanduser(p))


def _names(name):
    """The canonical name first, then every old name that maps to it."""
    canon = ALIASES.get(name, name)
    return [canon] + sorted(old for old, new in ALIASES.items() if new == canon)


def _parse(p):
    """NAME=value lines. Absent, unreadable or malformed → ignored, never raised."""
    out = {}
    try:
        text = _home(p).read_text()
    except Exception:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if _NAME.match(k) and v:
            out[k] = v
    return out


def _keychain(names):
    """The ~/.daemn helper, imported the way video-teardown's keys.py does.
    Silent when the helper is absent or any call fails."""
    folder = _home(KEYCHAIN_DIR)
    if not (folder / "daemn_keys.py").is_file():
        return None
    try:
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
        import daemn_keys
    except Exception:
        return None
    for n in names:
        try:
            v = daemn_keys.key(n)
        except Exception:
            v = None
        if v:
            return v
    return None


def fallback_skipped():
    """True on the mini (the managed file exists) or when KEYS_NO_FALLBACK=1."""
    return (os.environ.get(NO_FALLBACK_ENV) == "1"
            or _home(MANAGED).exists())


def _places(skipped):
    places = ["environment"]
    if skipped:
        places.append("old locations skipped (managed file present or %s=1)"
                      % NO_FALLBACK_ENV)
    else:
        places += [KEYCHAIN_DIR + "/daemn_keys.py" if s == "keychain" else s
                   for s in FALLBACK]
    return places


def _lookup(name, skipped, cache):
    names = _names(name)
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    if skipped:
        return None
    for src in FALLBACK:
        if src == "keychain":
            v = _keychain(names)
            if v:
                return v
            continue
        if src not in cache:
            cache[src] = _parse(src)
        for n in names:
            if cache[src].get(n):
                return cache[src][n]
    return None


def _missing(names, skipped):
    looked = []
    for n in names:
        aka = [a for a in _names(n) if a != n]
        looked.append(n + (" (or %s)" % ", ".join(aka) if aka else ""))
    return KeyError("missing key %s; looked in: %s"
                    % ("; ".join(looked), ", ".join(_places(skipped))))


def key(name, required=True):
    """The value of `name` (or any alias of it), or None when not required."""
    skipped = fallback_skipped()
    v = _lookup(name, skipped, {})
    if v is None and required:
        raise _missing([name], skipped)
    return v


def load(names, required=True):
    """Keys {name: value} for every name found; a missing required name raises
    one KeyError naming every missing name, never a value."""
    skipped = fallback_skipped()
    cache = {}
    out, missing = Keys(), []
    for n in names:
        v = _lookup(n, skipped, cache)
        if v is None:
            missing.append(n)
        else:
            out[n] = v
    if missing and required:
        raise _missing(missing, skipped)
    return out
