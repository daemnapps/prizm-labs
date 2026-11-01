#!/usr/bin/env python3
"""The model seam — one function boundary between the engine and any vendor.

The engine binds a model PER STAGE and then calls exactly one thing:

    response = runner(ModelRequest(...))  ->  ModelResponse(text, artifacts)

That is the whole seam. Everything above it is chain logic (ordering, piping,
versions, the out-dir jail); everything below it is a vendor call, a queue
job, a recording, or a stub. A bench that wants to wrap this engine — score
it, replay it, A/B two model bindings — swaps the runner and touches nothing
else, which is the same reason CR-4 can dispatch a run as a worker job.

THE STUB IS THE DEFAULT AND THE ONLY EAGERLY-LOADED RUNNER. CR-1's structural
promise — "imports no HTTP client, opens no socket, reads no credential" — was
true because no real runner existed. CR-2b builds one, and the promise is kept
in the strongest form still available: `vendors.py` is registered LAZILY, so it
is imported only by a run that names it. A run that does not say `vendor` cannot
reach a vendor, and the declared test proves it by asserting `runner.vendors` is
absent from `sys.modules` after the whole suite has run — an assertion, not a
promise, which is the same standard CR-1 held itself to.

The grant row that feeds the real runner already exists in
`platform/workers/mini-worker/job_env.py` (`chain-runner`: GEMINI_API_KEY,
APIFY_TOKEN, FAL_KEY), granted to the JOB and read only inside `vendors.py`, at
call time, never at import and never out of run-config.

`--model-runner` naming anything registered nowhere is a hard, named failure.
A silent fallback to the stub would let a "real" run quietly produce fixtures.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


MEDIA_KINDS = ("video", "image", "audio")


class MediaError(Exception):
    """A media input that will not cross the seam."""


class SeamError(Exception):
    """A failure BELOW the seam — the vendor call a runner tried to make.

    Declared here rather than inside a runner so the engine can keep its
    partial output and `run.py` can report the right exit code WITHOUT
    importing any runner's module, which would undo the lazy load and put an
    HTTP client back in every run's import graph. A real runner raises a
    subclass of this; the engine and the command know only this name.
    """


@dataclass(frozen=True)
class MediaInput(object):
    """One non-text input, carried BY LOCATION and never by content.

    `name` is the stage's declared name for it, `kind` one of MEDIA_KINDS, and
    `location` the path or URI the run-config supplied. The engine never opens
    it: reading a video into memory to hand it across a function boundary is
    how a chain engine becomes a media tool, and a location is what every
    vendor actually wants (an upload handle, a file path, a signed URL). What
    to DO with the location — upload it, glob a directory of frames out of it,
    hand it to a queue — is the runner's business, below the seam.

    Frozen and validated on construction: a seam whose media entries are
    untyped dicts is a seam where a typo becomes a vendor error at spend time.
    """
    name: str
    kind: str
    location: str

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise MediaError("a media input needs a name")
        if self.kind not in MEDIA_KINDS:
            raise MediaError(
                "media {0!r}: kind {1!r} is not one of {2}".format(
                    self.name, self.kind, ", ".join(MEDIA_KINDS)))
        if not isinstance(self.location, str) or not self.location.strip():
            raise MediaError(
                "media {0!r}: empty location — a media input the run could not "
                "resolve must fail here, not arrive at a vendor as an empty "
                "string".format(self.name))


@dataclass(frozen=True)
class ModelRequest(object):
    """What a stage hands the model. `prompt` is the RENDERED text — every
    `@stage` and `@config` reference already substituted — because a seam that
    passed templates plus a context bag would let two implementations render
    the same stage differently.

    `media` is the ordered tuple of `MediaInput`s the stage declared (CR-2b):
    4 of the 15 stages in the first imported chain carry video or images, so a
    text-only seam could not run that chain at all. Media rides BESIDE the
    prompt rather than inside it — the location string is also substituted into
    the prompt text, because that is what the machine these prompts were copied
    from does and a parity difference invented here is the one kind this
    component must never introduce.
    """
    chain: str
    stage: str
    label: str
    model: str
    prompt: str
    inputs: dict
    media: tuple = ()


@dataclass(frozen=True)
class ModelResponse(object):
    """What comes back. `text` is the stage's output and is piped onward.

    `artifacts` maps a path RELATIVE TO THE OUT ROOT to its content — a frames
    manifest, a scraped payload, whatever a real stage produces beside prose.
    Every one of those paths goes through the out-dir jail before a byte is
    written, so a runner returning `"../../escape.md"` fails the run loudly
    instead of writing there. That is deliberate: the jail must hold against
    the seam, not only against the chain file, or it is only schema validation
    wearing a wall's clothes.
    """
    text: str
    artifacts: dict = field(default_factory=dict)


def stub_runner(request):
    """Deterministic, offline, and honest about being a stub.

    The body carries the model id it was bound to and a digest of the prompt,
    then echoes the rendered prompt verbatim. Both matter: the digest makes
    determinism checkable at a glance, and the echo is what lets a fixture
    chain PROVE that stage 2 saw stage 1's output rather than asserting it.
    """
    digest = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()
    body = "\n".join([
        "STUB-MODEL " + request.model,
        "chain: " + request.chain,
        "stage: " + request.stage,
        "inputs: " + ",".join(sorted(request.inputs)),
        # Media is echoed as name:kind=location, in declaration order, so a
        # fixture can PROVE the typed payload reached the seam rather than
        # asserting it off the engine's own record.
        "media: " + ",".join("{0}:{1}={2}".format(m.name, m.kind, m.location)
                             for m in (request.media or ())),
        "prompt-sha256: " + digest,
        "prompt-chars: " + str(len(request.prompt)),
        "--- rendered prompt ---",
        request.prompt.rstrip("\n"),
        "--- end rendered prompt ---",
    ])
    return ModelResponse(text=body + "\n")


RUNNERS = {"stub": stub_runner}

# Registered by NAME, loaded by nothing until that name is asked for. The
# module behind each entry is what holds the HTTP client and reads the
# credential, so importing it eagerly here would spend the component's
# no-socket guarantee to save one import. `--check` never resolves a runner
# either, so validating a chain stays as offline as it has always been.
LAZY = {"vendor": ("vendors", "vendor_runner")}


def check_name(name):
    """Is this a runner name? Answered WITHOUT importing anything.

    `--check` validates the invocation and writes nothing; making it import the
    vendor module — and so the HTTP client — to answer "is `vendor` a name"
    would put a socket-capable import inside the one mode that promises to do
    nothing at all. So the name check and the load are two calls.
    """
    if name not in RUNNERS and name not in LAZY:
        raise KeyError(
            "unknown model runner {0!r}; registered: {1}. `stub` is the default "
            "and calls nothing; `vendor` binds Gemini (GEMINI_API_KEY) and "
            "Claude (the CLI's own login) and SPENDS MONEY."
            .format(name, ", ".join(sorted(list(RUNNERS) + list(LAZY)))))


def get(name):
    """The runner named, or a loud failure listing what exists.

    A lazy entry is imported HERE, on the name being asked for, and an import
    that fails is reported as itself: a runner whose dependencies are missing
    must not degrade into the stub, because a stub run wearing a real runner's
    name in `run.json` is a fixture presented as a parity result.
    """
    check_name(name)
    if name in RUNNERS:
        return RUNNERS[name]
    module_name, attr = LAZY[name]
    import importlib
    module = importlib.import_module("." + module_name, __package__ or "runner")
    return getattr(module, attr)
