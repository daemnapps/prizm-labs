"""The generator — a reference picture in, a new picture out.

Lifted from `the team notes/avatar-builder/build.py` (`uri`, `gen`): the same
model, the same payload, the same data-uri reference, the same key lookup and
the same "no file back is a FAILURE, said out loud" behaviour. Two things
changed and both are said here rather than assumed:

  · the job payload is written into the RUN folder instead of `/tmp`, so a run
    keeps the thing it sent (`runs/README.md`: a run is its own record);
  · the subprocess is a SEAM (`runner=`), so a test can stand in for it and
    nothing here opens a socket by itself.

**Keys are read BY NAME, never by path** — the process environment first, then
the macOS Keychain (service `daemn-<NAME>`, account `damon`). Never out of a
file in the repo or the home folder, never printed, never logged, never
written into a run record. Read at CALL time, never at import time.

No brand, person or product is named in this file. The model id is a constant
because it is this component's own definition, not a brand's.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# THE EDIT DOOR, THROUGH THE ONE IMAGE ENGINE. Every step here is a reference
# edit — a picture in, a picture out — so this asks
# `tools/image-production` for its edit row rather than naming a vendor.
# It used to run `openai/gpt-image-2/edit` over fal's client; fal was ruled out
# for the third time on 2026-09-22 ("remove anything with fal or flux lora"),
# and the engine's own table is where a model is chosen now.
MODEL = "gpt-image-edit"
KEY = "OPENAI_API_KEY"
PNG = re.compile(r"(/\S+\.png)")



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


def key_value(name=KEY):
    """The key, by name. Environment first, then the repo's .env (the key loader). Never printed."""
    try:
        return (_shared_keys().lookup(name) or "").strip() or None
    except Exception:
        return None


def key_present(name=KEY):
    return bool(key_value(name))


def engine():
    """The shared image engine, imported at CALL time so this module stays
    importable (and testable) on a machine that has not got it."""
    import sys as _sys
    root = Path(__file__).resolve().parents[2] / "image-production"
    if str(root) not in _sys.path:
        _sys.path.append(str(root))
    from image_production import providers, route          # noqa: PLC0415
    return providers, route


def payload(prompt, reference):
    """What the call carries: one reference picture, one prompt. Written into
    the run folder so a run keeps the thing it sent."""
    return {"prompt": prompt, "reference": str(reference), "model": MODEL}


def plan(step, reference, model=MODEL):
    """What the call WOULD be, for the dry run. Reads no key and no file."""
    return {"step": step, "model": model, "door": "tools/image-production",
            "client_on_this_machine": (
                Path(__file__).resolve().parents[2] / "image-production").is_dir(),
            "reference": str(reference),
            "reference_on_this_machine": bool(reference) and Path(reference).is_file(),
            "key": KEY, "key_on_this_machine": key_present()}


def _engine_runner(argv, env, cwd):
    """The default door: the shared engine's edit row. Keeps the subprocess
    seam's shape — (stdout, stderr), with the written path in stdout — so a
    test can still stand in for it and nothing here opens a socket by itself."""
    job = json.loads(Path(argv[-1]).read_text())
    out = Path(argv[-1]).with_suffix(".png")
    providers, route = engine()
    try:
        _, entry, _ = route.pick({"model": MODEL, "from_image": job["reference"]},
                                 {"purpose": {"people": True}})
        providers.generate(entry, job["prompt"], [job["reference"]], out, "1:1",
                           key=env.get(KEY))
    except Exception as e:                                  # noqa: BLE001
        return "", "%s: %s" % (type(e).__name__, e)
    return ("wrote %s\n" % out) if out.is_file() else ("", "the door wrote no file")


def generate(step, prompt, reference, job_dir, model=MODEL, runner=None, echo=print):
    """One generation. Returns `{step, model, file, seconds, error}`.

    `file` is the picture the door wrote on this machine, or None with
    `error` saying why. A step that comes back with nothing is a FAILURE that
    says so — it is never treated as a pass.
    """
    ref = Path(reference)
    if not ref.is_file():
        return {"step": step, "model": model, "file": None,
                "error": "the reference picture is not a file on this machine: %s" % ref}
    k = key_value()
    if not k:
        return {"step": step, "model": model, "file": None,
                "error": "no %s on this machine — read from the environment, else the "
                         "macOS Keychain (service daemn-%s, account damon)" % (KEY, KEY)}

    job = Path(job_dir)
    job.mkdir(parents=True, exist_ok=True)
    f = job / ("job-%s.json" % step)
    f.write_text(json.dumps(payload(prompt, ref)))

    env = dict(os.environ)
    env[KEY] = k
    t0 = time.time()
    echo("  [%s] generating …" % step)
    out, err = (runner or _engine_runner)(
        [sys.executable, "-m", "image_production", "edit", model, str(f)],
        env, str(job))
    files = PNG.findall(out or "")
    if not files:
        return {"step": step, "model": model, "file": None,
                "seconds": round(time.time() - t0, 1),
                "error": "the generator returned no picture — %s"
                         % ((out or "") + (err or ""))[-300:]}
    echo("  [%s] -> %s in %ss" % (step, Path(files[-1]).name, round(time.time() - t0)))
    return {"step": step, "model": model, "file": files[-1],
            "seconds": round(time.time() - t0, 1), "error": None}
