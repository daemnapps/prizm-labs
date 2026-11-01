#!/usr/bin/env python3
"""The REAL model runner — the only module in this component that touches a
vendor, and the only one that is never imported unless it is asked for.

    python3 runner/run.py <chain> --out <dir> --model-runner vendor

`models.py` registers this module LAZILY (`models.LAZY`): nothing imports it at
module load, so the component's structural promise survives intact — a run that
does not name `vendor` opens no socket and reads no credential, and the declared
test proves that by asserting this module is absent from `sys.modules` after the
whole suite has run. The guarantee moved from "there is no real runner" to "the
real runner is not loaded unless you say its name", which is the strongest form
the guarantee can take once a real runner exists at all.

WHAT IT BINDS, and why each is bound the way it is:

| model id | vendor | how |
|---|---|---|
| `gemini-*` (text/video) | Gemini | REST, `GEMINI_API_KEY` from the env |
| `gemini-*image*` | Gemini | the same REST call; image parts come back inline |
| `opus`, `sonnet`, `haiku`, `claude-*` | Claude | the `claude` CLI, on ITS OWN login |

Claude rides the CLI **exactly as the machine these chains were copied from
does** — `claude -p --model <id>` with the prompt on stdin — because that is
what parity means here, and because it needs no credential of ours: the CLI
holds its own login. There is no `ANTHROPIC_API_KEY` in this job's grant row
(`platform/workers/mini-worker/job_env.py`, `chain-runner`:
`GEMINI_API_KEY, APIFY_TOKEN, FAL_KEY`) and this module never asks for one. A
credential the row does not carry is a STOP, not an improvisation.

CREDENTIALS ARE READ AT CALL TIME, never at import, and never out of run-config
(run-config lands in `run.json` in the clear). A missing key fails the stage by
name and says which grant row is supposed to supply it.

MEDIA IS PASSED THROUGH, NOT PROCESSED. A `MediaInput` is a location. A URI goes
to Gemini as `file_data`; a local file is handed to the Files API as the bytes
on disk and referenced by the uri it returns. Nothing is transcoded, resized,
sampled or frame-extracted — the moment this module opens a video to do
something clever with it, the engine has become a media tool and the component's
kill-condition has fired.

NO RETRY LADDER, NO MODEL FALLBACK. The source machine falls back to a second
Gemini when the first is busy and REPORTS which one answered. We do not: a
parity run whose stage silently bound a different model is measuring a different
chain, and `run.json` would still name the model the chain declared. A 503 is a
failed run the lead re-runs, which costs one operator minute and keeps the
manifest honest.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

from . import models


GEMINI_ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/"
                   "models/{model}:generateContent")
GEMINI_UPLOAD = "https://generativelanguage.googleapis.com/upload/v1beta/files"
GEMINI_FILES = "https://generativelanguage.googleapis.com/v1beta/{name}"

# The env var each vendor needs, so a missing one is named with its grant row
# rather than surfacing as a 401 at spend time.
GEMINI_KEY_VAR = "GEMINI_API_KEY"
GRANT_ROW = ("platform/workers/mini-worker/job_env.py, job 'chain-runner' — "
             "granted: GEMINI_API_KEY, APIFY_TOKEN, FAL_KEY")

CLAUDE_PREFIXES = ("opus", "sonnet", "haiku", "claude")

# Locations we hand over BY REFERENCE. Everything else is treated as a local
# file and uploaded as-is.
URI_SCHEMES = ("http://", "https://", "gs://")

# Enough to name a part; the vendor decides what it can actually read. Kept
# deliberately short — a mime table that tries to be complete is a media tool
# growing inside a chain engine.
MIME = {
    "mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm",
    "m4v": "video/x-m4v", "avi": "video/x-msvideo",
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "webp": "image/webp", "gif": "image/gif", "heic": "image/heic",
    "mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4",
    "aac": "audio/aac", "ogg": "audio/ogg", "flac": "audio/flac",
}
KIND_FALLBACK_MIME = {"video": "video/mp4", "image": "image/png",
                      "audio": "audio/mpeg"}

TIMEOUT = 900          # one stage's call; a video teardown is not a fast call
UPLOAD_POLL_SECONDS = 3
UPLOAD_POLL_TRIES = 100    # ~5 minutes for a video to finish PROCESSING


class VendorError(models.SeamError):
    """A real call that did not happen or did not come back usable.

    Raised by name so `run.py` reports which stage and which vendor failed
    rather than a stack trace: on a paid run the first question is always
    'what did we spend and where did it stop'.
    """


# ---------------------------------------------------------------- routing

def route(model):
    """Which vendor a bound model id belongs to. Unknown is a hard failure.

    A guess here is the expensive kind of wrong: it would bill an unintended
    vendor for a stage whose `run.json` row names a different model.
    """
    low = (model or "").lower()
    if low.startswith("gemini"):
        return "gemini"
    for prefix in CLAUDE_PREFIXES:
        if low.startswith(prefix):
            return "claude"
    raise VendorError(
        "model {0!r} routes to no vendor this runner binds. Bound: gemini-* "
        "(Gemini REST) and {1} (the claude CLI). Add the binding on purpose or "
        "run this stage on --model-runner stub.".format(
            model, ", ".join(CLAUDE_PREFIXES)))


def vendor_runner(request):
    """The seam, implemented for real. One request in, one ModelResponse out."""
    where = route(request.model)
    if where == "claude":
        return _claude(request)
    return _gemini(request)


# ---------------------------------------------------------------- Claude

def _claude_env(environ=None):
    """The `claude` job's environment (WM-101 (every spawn scoped)): the
    worker's one helper, loaded by file path — never imported at module
    level — so the CLI holds none of this job's vendor keys. A missing
    helper is a STOP, never the inherited environment."""
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    path = os.path.join(root, "platform", "workers", "mini-worker", "job_env.py")
    if not os.path.isfile(path):
        raise VendorError(
            "cannot scope the claude CLI's environment: {0} is missing, and "
            "the CLI is never handed the inherited one.".format(path))
    spec = importlib.util.spec_from_file_location("job_env", path)
    job_env = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(job_env)
    return job_env.scoped_env("claude", environ=environ)


def _claude(request):
    """`claude -p --model <id>`, prompt on stdin — the source machine's call.

    Media on a Claude stage is refused rather than dropped. The CLI takes the
    prompt and nothing else here, so carrying a video to this call and silently
    not sending it would produce a confident answer about a video the model
    never saw — the most expensive silent failure this component has a rule
    against.
    """
    if request.media:
        raise VendorError(
            "stage {0!r} binds {1} (the claude CLI) and declares media "
            "({2}). This runner sends the CLI a prompt and nothing else, and "
            "dropping the media silently would answer about a file the model "
            "never saw. Bind a media-capable model, or drop the "
            "declaration.".format(
                request.stage, request.model,
                ", ".join(m.name for m in request.media)))
    import sys
    from pathlib import Path
    kit = next(str(d / "components" / "run-kit") for d in Path(__file__).resolve().parents
               if (d / "components" / "run-kit").is_dir())
    if kit not in sys.path:
        sys.path.append(kit)   # appended, never ahead of this runner
    from run_kit.claude_flags import effort_args   # LD-73 (explicit effort)
    argv = ["claude", "-p", "--model", request.model, *effort_args(), "--allowed-tools", ""]
    try:
        done = subprocess.run(argv, input=request.prompt, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True,
                              timeout=TIMEOUT, env=_claude_env())
    except OSError as exc:
        raise VendorError(
            "stage {0!r}: cannot run the `claude` CLI ({1}). Claude stages ride "
            "the CLI's own login — no key of ours is involved, and none is in "
            "the grant row. Install/log in the CLI on the machine that runs "
            "the chain.".format(request.stage, exc))
    except subprocess.TimeoutExpired:
        raise VendorError("stage {0!r}: the claude CLI did not answer in {1}s"
                          .format(request.stage, TIMEOUT))
    if done.returncode or not (done.stdout or "").strip():
        tail = (done.stderr or done.stdout or "claude failed").strip()[-1200:]
        raise VendorError("stage {0!r}: claude failed — {1}".format(
            request.stage, tail))
    return models.ModelResponse(text=done.stdout)


# ---------------------------------------------------------------- Gemini

def _gemini(request):
    """One `generateContent` call, media parts first, prompt last.

    Media before text on purpose: it is the order the source machine's own
    Gemini tool uses, and part order is an input to the model, so reversing it
    would be a parity difference we invented.
    """
    key = _key(GEMINI_KEY_VAR, request.stage)
    parts = [_gemini_part(media, key, request.stage) for media in request.media]
    parts.append({"text": request.prompt})
    payload = {"contents": [{"role": "user", "parts": parts}]}
    body = _post_json(GEMINI_ENDPOINT.format(model=request.model), payload, key,
                      request.stage)

    text, artifacts = [], {}
    for candidate in body.get("candidates") or []:
        for n, part in enumerate(
                ((candidate.get("content") or {}).get("parts") or [])):
            if "text" in part:
                text.append(part["text"])
                continue
            blob = part.get("inlineData") or part.get("inline_data")
            if not blob:
                continue
            # An image model answers with base64. It is written VERBATIM, as the
            # vendor encoded it, into a `.b64` sidecar: the seam carries text
            # artifacts, and decoding here to re-encode elsewhere is exactly the
            # cleverness this module refuses. `base64 -d` is the whole recipe,
            # and the manifest line below says so beside every file.
            ext = _ext_for(blob.get("mimeType") or blob.get("mime_type") or "")
            path = "artifacts/{0}/{1}-{2}.{3}.b64".format(
                request.stage, _tag(request.prompt), n, ext)
            artifacts[path] = blob.get("data") or ""
            text.append("[image artifact: {0} — base64, decode with "
                        "`base64 -d`]".format(path))

    if not text:
        raise VendorError(
            "stage {0!r}: Gemini answered with no usable part. Finish reason: "
            "{1}".format(request.stage, _finish(body)))
    return models.ModelResponse(text="\n".join(text), artifacts=artifacts)


def _gemini_part(media, key, stage):
    """One MediaInput as one Gemini part. By reference wherever possible."""
    mime = _mime_for(media)
    if media.location.startswith(URI_SCHEMES):
        return {"file_data": {"mime_type": mime, "file_uri": media.location}}
    uri = _upload(media, mime, key, stage)
    return {"file_data": {"mime_type": mime, "file_uri": uri}}


def _upload(media, mime, key, stage):
    """A local file to the Files API, raw protocol, then wait for ACTIVE.

    The Files API and not inline base64 because stages 0 and 1 hand over a
    VIDEO: inline data is capped low enough that inlining would work on a test
    clip and fail on a real one, which is the worst place for a size limit to
    first appear. The bytes go up exactly as they sit on disk.
    """
    try:
        with open(media.location, "rb") as handle:
            blob = handle.read()
    except OSError as exc:
        raise VendorError(
            "stage {0!r}: media {1!r} ({2}) is not readable at {3!r} — {4}. The "
            "engine never opens a media file, so this is the first place the "
            "location is checked at all.".format(
                stage, media.name, media.kind, media.location, exc))

    request = urllib.request.Request(
        _keyed(GEMINI_UPLOAD, key), data=blob, method="POST")
    request.add_header("X-Goog-Upload-Protocol", "raw")
    request.add_header("X-Goog-Upload-File-Name", os.path.basename(media.location))
    request.add_header("Content-Type", mime)
    body = _send(request, stage, "the Files API upload of media {0!r}".format(
        media.name))
    info = body.get("file") or {}
    name, uri = info.get("name"), info.get("uri")
    if not uri:
        raise VendorError("stage {0!r}: media {1!r} uploaded but came back with "
                          "no uri".format(stage, media.name))

    # A video is PROCESSING when the upload returns and unusable until ACTIVE.
    for _ in range(UPLOAD_POLL_TRIES):
        if info.get("state") == "ACTIVE":
            return uri
        if info.get("state") == "FAILED":
            raise VendorError(
                "stage {0!r}: Gemini could not process media {1!r} ({2})".format(
                    stage, media.name, media.location))
        time.sleep(UPLOAD_POLL_SECONDS)
        info = _send(urllib.request.Request(
            _keyed(GEMINI_FILES.format(name=name), key)), stage,
            "the state of media {0!r}".format(media.name))
    raise VendorError(
        "stage {0!r}: media {1!r} was still not ACTIVE after {2}s".format(
            stage, media.name, UPLOAD_POLL_TRIES * UPLOAD_POLL_SECONDS))


# ---------------------------------------------------------------- plumbing

def _key(var, stage):
    value = (os.environ.get(var) or "").strip()
    if not value:
        raise VendorError(
            "stage {0!r} needs {1} and the environment does not carry it. It is "
            "granted to this job and never passed as run-config (run-config is "
            "written to run.json in the clear): {2}".format(stage, var, GRANT_ROW))
    return value


def _keyed(url, key):
    return url + ("&" if "?" in url else "?") + "key=" + key


def _post_json(url, payload, key, stage):
    request = urllib.request.Request(
        _keyed(url, key), data=json.dumps(payload).encode("utf-8"), method="POST")
    request.add_header("Content-Type", "application/json")
    return _send(request, stage, "the model call")


# CR-2d (2026-09-01): bounded SAME-MODEL retry on transient failures.
# This is not the fallback ladder the design refuses — that refusal is
# about model SUBSTITUTION (a silently swapped model makes run.json a lie).
# The SOURCE machine retries the same call 4x with backoff (run.py's
# retry-on-blip), so refusing retries here was a parity DIVERGENCE, proven
# live: gemini-3-pro-image 503 demand spikes killed four otherwise-green
# runs at stage 6. Retries hit the SAME url with the SAME payload; the
# terminal error still fails the run loudly by name.
RETRY_STATUS = (429, 500, 502, 503, 504)
RETRIES = 4
BACKOFF = 30           # seconds, times the attempt number — the source's shape


def _send(request, stage, what):
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
                raw = answer.read()
            break
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:1200]
            except Exception:
                pass
            if exc.code in RETRY_STATUS and attempt < RETRIES:
                time.sleep(BACKOFF * (attempt + 1))
                continue
            raise VendorError("stage {0!r}: {1} failed — HTTP {2} {3}{4}".format(
                stage, what, exc.code, detail,
                " (after {0} retries)".format(attempt) if attempt else ""))
        except (urllib.error.URLError, OSError) as exc:
            if attempt < RETRIES:
                time.sleep(BACKOFF * (attempt + 1))
                continue
            raise VendorError("stage {0!r}: {1} could not be made — {2}"
                              " (after {3} retries)".format(stage, what, exc, attempt))
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        raise VendorError("stage {0!r}: {1} returned non-JSON: {2!r}".format(
            stage, what, raw[:300]))


def _mime_for(media):
    ext = media.location.rsplit(".", 1)[-1].lower() if "." in media.location else ""
    return MIME.get(ext) or KIND_FALLBACK_MIME.get(media.kind, "application/octet-stream")


def _ext_for(mime):
    for ext, known in MIME.items():
        if known == mime:
            return ext
    return "bin"


def _tag(prompt):
    """12 hex of the rendered prompt — the only member-distinguishing fact the
    seam carries. `ModelRequest` names no member (it does not need to know one),
    so two members' artifacts would otherwise collide on one path. Deterministic,
    because the run record is."""
    import hashlib
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]


def _finish(body):
    for candidate in body.get("candidates") or []:
        if candidate.get("finishReason"):
            return str(candidate["finishReason"])
    return json.dumps(body)[:400]


RUNNERS = {"vendor": vendor_runner}
