"""The one key loader — key(NAME) and load(names).

Everyone brings their own keys. A key is found in this order:
  1. an environment variable with that name;
  2. the `.env` file at the root of this repo (gitignored — copy
     `.env.example` to `.env` and fill in your own keys);
  3. Damon's Mac Keychain, through the ~/.daemn/daemn_keys.py helper, only
     when that helper exists (personal NAME_PERSONAL / PRIZM_* entries only).
     On Windows, or any machine without the helper, this step is skipped
     silently, so .env is the one place to set keys there.
Nothing else is ever read. Prizm Labs is disconnected from the Upright key
files (2026-11-03, authorised by Damon): no ~/.upright-keys.env,
~/.daemn/keys.env, ~/.gemini.env or ~/.apify.env.
A missing key raises KeyError whose message starts:
  "This tool needs NAME. Add it to .env (see .env.example)."

Original notes:

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
# After .env, only Damon's Keychain helper — never the Upright key files.
FALLBACK = ("keychain",)
KEYCHAIN_DIR = "~/.daemn"
# Step 2: the repo's own .env (components/keys/loader.py -> repo root).
REPO_ROOT = Path(__file__).resolve().parents[2]
DOTENV = REPO_ROOT / ".env"

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
    """Damon's Keychain, through the ~/.daemn/daemn_keys.py helper.
    Silent when the helper is absent (Windows, anyone else's machine) or any call fails."""
    folder = _home(KEYCHAIN_DIR)
    if not (folder / "daemn_keys.py").is_file():
        return None
    try:
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
        import daemn_keys
    except Exception:
        return None
    # The helper reads shared key files first unless told Keychain only.
    os.environ["DAEMN_KEYS_SOURCE"] = "keychain"
    # Personal keys only, never a company key: no fallback to a shared name.
    own = ("TELLA_API_KEY", "ELEVENLABS_API_KEY", "ADPLEXITY_API_KEY")
    names = ["PRIZM_META_TOKEN" if n == "META_ADS_TOKEN" else n for n in names]
    names = [n + "_PERSONAL" for n in names if not n.endswith("_PERSONAL")] + [
        n for n in names if n.endswith("_PERSONAL") or n.startswith("PRIZM_") or n in own]
    for n in names:
        try:
            v = daemn_keys.key(n)
        except Exception:
            v = None
        if v:
            return v
    return None


KEY_FILE = Path(__file__).resolve().parents[2] / ".env"


def has_key_file():
    """True when this repo's own .env exists, the file every key comes from here."""
    return KEY_FILE.is_file()


def fallback_skipped():
    """True on the mini (the managed file exists) or when KEYS_NO_FALLBACK=1."""
    return (os.environ.get(NO_FALLBACK_ENV) == "1"
            or _home(MANAGED).exists())


def _places(skipped):
    places = ["environment"]
    if skipped:
        places.append(".env and Keychain skipped (managed file present or %s=1)"
                      % NO_FALLBACK_ENV)
    else:
        places += [".env", KEYCHAIN_DIR + "/daemn_keys.py (Keychain, Mac only)"]
    return places


def _lookup(name, skipped, cache):
    names = _names(name)
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    if skipped:
        return None
    if "dotenv" not in cache:
        cache["dotenv"] = _parse(str(DOTENV))
    for n in names:
        if cache["dotenv"].get(n):
            return cache["dotenv"][n]
    if "keychain" in FALLBACK:
        return _keychain(names)
    return None


def _missing(names, skipped):
    looked = []
    for n in names:
        aka = [a for a in _names(n) if a != n]
        looked.append(n + (" (or %s)" % ", ".join(aka) if aka else ""))
    return KeyError("This tool needs %s. Add it to .env (see .env.example). "
                    "(looked in: %s)"
                    % (" and ".join(looked), ", ".join(_places(skipped))))


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


def lookup(name, required=False):
    """For readers that used the old personal helper's `key(name, required=)`:
    the value or None; with required=True a missing key exits with the plain
    message ("This tool needs NAME. Add it to .env (see .env.example).")."""
    skipped = fallback_skipped()
    v = _lookup(name, skipped, {}) if name else None
    if v is None and required:
        sys.exit(_missing([name], skipped).args[0])
    return v


if __name__ == "__main__":
    # Self-check: names only, never a value.
    names = sys.argv[1:]
    if not names:
        print("usage: python3 components/keys/loader.py NAME [NAME ...]")
        sys.exit(0)
    bad = 0
    for n in names:
        if key(n, required=False):
            print("  %-28s set" % n)
        else:
            bad += 1
            print("  %-28s missing — add it to .env (see .env.example)" % n)
    sys.exit(1 if bad else 0)
