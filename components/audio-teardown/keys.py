"""Keys, by name, through the repo's one key loader (environment, then .env).

Every key this tool uses: GEMINI_API_KEY (words, every language), ELEVENLABS_API_KEY
(who speaks when). The environment wins when a key is set there.
"""
import os
import sys
from pathlib import Path



def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod


def key(name):
    v = _shared_keys().lookup(name)
    if not v or "PASTE" in v:
        raise RuntimeError(f"This tool needs {name}. Add it to .env (see .env.example).")
    return v
