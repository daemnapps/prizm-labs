"""Keys, by name, from the Keychain — never from a file (the wall: a key by path).

Every key this tool uses: GEMINI_API_KEY (words, every language), ELEVENLABS_API_KEY
(who speaks when). The environment wins when a key is set there, so the shared
machine can run this without a Keychain.
"""
import os
import sys
from pathlib import Path


def key(name):
    if os.environ.get(name):
        return os.environ[name]
    sys.path.insert(0, str(Path.home() / ".daemn"))
    try:
        import daemn_keys
        v = daemn_keys.key(name)
    except Exception as e:                                   # no Keychain helper on this machine
        raise RuntimeError(f"no {name}: set it in the environment or the Keychain ({e})")
    if not v or "PASTE" in v:
        raise RuntimeError(f"no {name} in the Keychain")
    return v
