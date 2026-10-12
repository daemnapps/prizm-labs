#!/usr/bin/env python3
"""The models registry validator — the ONLY code in components/models/.

    python3 components/models/validate.py              # both manifests
    python3 components/models/validate.py --selftest   # prove the rejections

The chains.json pattern: the manifests are data, this is the one thing that
reads them, and a bad entry FAILS LOUDLY naming itself. The registry never
guesses — it has no defaults to fall back on, because a model whose cost or
key is guessed is worse than a model that is absent.

Exit codes
    0  everything checked is valid
    2  a manifest is invalid (every finding printed, entry named)
    3  a manifest is missing or unreadable / bad arguments

`--selftest` runs INLINE fixtures through the same functions the real files go
through, proving each rejection the card names — a value-shaped `key_env`, an
unknown `status`, a duplicate `id` — plus a control fixture that must PASS, so
a validator that rejected everything could not go green. Selftest reads the
real manifests not at all; its two `load` cases write a TEMP file each and
remove it.

No pytest, no network, no dependencies. Must run on /usr/bin/python3 (3.9) —
no 3.10+ syntax anywhere in this component.
"""

import argparse
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MODELS_PATH = os.path.join(HERE, "models.json")
ASSETS_PATH = os.path.join(HERE, "trained-assets.json")

STATUSES = ("draft", "approved", "deprecated")
MODALITIES = ("text", "image", "video", "audio")
TRANSPORTS = ("claude-cli", "api", "local")
KINDS = ("character", "product")

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
# An env var NAME: capital-led, <=24 chars, underscores and digits allowed.
KEY_ENV_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,23}$")
# A run of three or more digits is what a key VALUE looks like and what a name
# does not. `ZZQA1234567890ABCD` passes the shape test and fails on this one.
DIGIT_RUN_RE = re.compile(r"\d{3,}")
TRIGGER_RE = re.compile(r"^[a-z0-9]{1,24}$")
# The date a trained asset was trained, copied from its record (MDL-7
# (registry validator honest)).
TRAINED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# The name a VENDOR answers to, when it differs from the registry id: an
# OpenRouter id carries a slash (`z-ai/glm-5.3-flash`). Lowercase, one
# optional namespace segment, no whitespace — and never key-shaped.
VENDOR_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*(/[a-z0-9][a-z0-9._:-]*)?$")

# ---- request-level controls (MDL-5 (reasoning budget), 2026-09-09) ----------
# OpenRouter's own spelling, fetched from its current documentation by the lead
# on 2026-09-09 and carried onto the card, because a maker's sandbox has no
# network. The registry declares these; the CONSUMER puts them on the request
# body unchanged (platform/workers/mini-worker/infer_run.py payload()), so what
# is refused here is refused before a call is ever made.
REQUEST_CONTROLS = ("reasoning", "provider")
REASONING_FIELDS = ("effort", "max_tokens", "exclude", "enabled", "context",
                    "mode")
# `effort` is OpenAI/Grok only and `max_tokens` is Anthropic/Gemini only — the
# vendor decides which reaches a given model, and neither reaches an OpenRouter
# entry served by z-ai or deepseek. The validator checks SHAPE, never which
# model a knob happens to reach: that is the vendor's table, it moves, and a
# manifest that guessed it would be wrong the week after.
REASONING_EFFORTS = ("max", "xhigh", "high", "medium", "low", "minimal", "none")
REASONING_CONTEXTS = ("auto", "all_turns", "current_turn")
REASONING_MODES = ("standard", "pro")
REASONING_MIN_TOKENS = 1024
PROVIDER_FIELDS = ("order", "allow_fallbacks")
# An upstream's slug as OpenRouter names it, and as the reply's own `provider`
# field reports it back (`OpenInference`, `Relace`, `Z.AI`).
PROVIDER_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._/-]{0,63}$")

# Field names that would mean a secret got pasted into a manifest. The rule is
# on the NAME, not a guessed value shape, so it cannot false-positive on a
# digest or a url.
SECRET_FIELDS = ("key", "api_key", "apikey", "token", "secret", "password",
                 "credential", "key_value")


# ---------------------------------------------------------------- primitives

def _nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def _key_env_problem(value):
    """Why this key_env is not an env var NAME, or None if it is one.

    null is legitimate and means the model spends no key at all — it runs on a
    login (the claude CLI's own). Absent is not the same as null: the field
    must be declared, because 'nobody wrote it down' and 'there is no key' are
    different answers.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return "must be a string (the env var NAME) or null, got %s" % type(value).__name__
    if value == "":
        return "is empty — write null if the model spends no key, never \"\""
    if len(value) > 24:
        return ("is %d chars long; an env var NAME is <=24. This looks like a "
                "key VALUE, and a key value may never enter a manifest"
                % len(value))
    run = DIGIT_RUN_RE.search(value)
    if run:
        return ("contains a run of %d digits; an env var NAME does not. This "
                "looks like a key VALUE, and a key value may never enter a "
                "manifest" % len(run.group(0)))
    if not KEY_ENV_RE.match(value):
        return ("is not env-var-NAME shaped (^[A-Z][A-Z0-9_]{0,23}$). Name the "
                "variable, never its value")
    return None


def _cost_problems(entry, where):
    """cost is \"unpriced\" WITH a reason, or an object of named numeric rates.

    A bare number is refused: a figure with no unit is not an answer. A rate of
    zero is allowed but must carry words, because a zero and an unknown are
    different answers and $0.00 is the one nobody may show for spend that was
    never measured.
    """
    out = []
    cost = entry.get("cost", "__missing__")
    reason = entry.get("cost_reason")
    if cost == "__missing__":
        return ["%s: `cost` is missing (write \"unpriced\" with a "
                "`cost_reason` if it is not known)" % where]
    if cost == "unpriced":
        if not _nonempty_str(reason):
            out.append("%s: cost is \"unpriced\" but `cost_reason` is empty — "
                       "unpriced is only honest with the reason in words"
                       % where)
        return out
    if isinstance(cost, dict):
        if not cost:
            out.append("%s: `cost` is an empty object; write \"unpriced\" "
                       "instead" % where)
        for rate, value in sorted(cost.items()):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                out.append("%s: cost.%s must be a number, got %r"
                           % (where, rate, value))
            elif value < 0:
                out.append("%s: cost.%s is negative (%r)" % (where, rate, value))
            elif value == 0 and not _nonempty_str(reason):
                out.append("%s: cost.%s is 0 with no `cost_reason`. A zero and "
                           "an unknown are different answers — say which"
                           % (where, rate))
        return out
    return ["%s: `cost` must be the string \"unpriced\" or an object of named "
            "rates, got %r. A bare number has no unit and is not an answer"
            % (where, cost)]


def _secret_field_problems(entry, where):
    out = []
    for field in sorted(entry.keys()):
        if field.lower() in SECRET_FIELDS:
            out.append("%s: field %r may not exist in a manifest. Name the env "
                       "var in `key_env`; never carry a key value"
                       % (where, field))
    return out


def _enum_problem(entry, field, allowed, where):
    value = entry.get(field, "__missing__")
    if value == "__missing__":
        return "%s: `%s` is missing (one of: %s)" % (where, field, ", ".join(allowed))
    if value not in allowed:
        return "%s: `%s` is %r — unknown. Allowed: %s" % (
            where, field, value, ", ".join(allowed))
    return None


def _reasoning_problems(reasoning, where):
    """OpenRouter's `reasoning` object, checked by SHAPE and by name."""
    out = []
    if not isinstance(reasoning, dict) or not reasoning:
        return ["%s: request.reasoning must be a non-empty object of %s; omit "
                "the field entirely to send nothing"
                % (where, ", ".join(REASONING_FIELDS))]
    for field in sorted(reasoning.keys()):
        if field not in REASONING_FIELDS:
            out.append("%s: request.reasoning.%s is not an OpenRouter reasoning "
                       "field. Allowed: %s"
                       % (where, field, ", ".join(REASONING_FIELDS)))
    if "effort" in reasoning and "max_tokens" in reasoning:
        out.append("%s: request.reasoning declares BOTH `effort` and "
                   "`max_tokens` — the vendor takes one or the other, never "
                   "both" % where)
    if "effort" in reasoning and reasoning.get("effort") not in REASONING_EFFORTS:
        out.append("%s: request.reasoning.effort is %r — unknown. Allowed: %s"
                   % (where, reasoning.get("effort"), ", ".join(REASONING_EFFORTS)))
    if "max_tokens" in reasoning:
        budget = reasoning.get("max_tokens")
        if isinstance(budget, bool) or not isinstance(budget, int):
            out.append("%s: request.reasoning.max_tokens must be an integer, "
                       "got %r" % (where, budget))
        elif budget < REASONING_MIN_TOKENS:
            out.append("%s: request.reasoning.max_tokens is %d; the vendor's "
                       "minimum is %d" % (where, budget, REASONING_MIN_TOKENS))
    for field in ("exclude", "enabled"):
        if field in reasoning and not isinstance(reasoning.get(field), bool):
            out.append("%s: request.reasoning.%s must be true or false, got %r"
                       % (where, field, reasoning.get(field)))
    if "context" in reasoning and reasoning.get("context") not in REASONING_CONTEXTS:
        out.append("%s: request.reasoning.context is %r — unknown. Allowed: %s"
                   % (where, reasoning.get("context"), ", ".join(REASONING_CONTEXTS)))
    if "mode" in reasoning and reasoning.get("mode") not in REASONING_MODES:
        out.append("%s: request.reasoning.mode is %r — unknown. Allowed: %s"
                   % (where, reasoning.get("mode"), ", ".join(REASONING_MODES)))
    return out


def _provider_problems(provider, where):
    """OpenRouter's `provider` routing object — an ORDER and a fallbacks switch.

    Pinning is not the default and is never assumed: an entry that wants a
    DETERMINISTIC route says `allow_fallbacks: false` itself, and an ordinary
    caller that prefers an upstream but would rather fail over than fail leaves
    it alone (the vendor's default is `true`).
    """
    out = []
    if not isinstance(provider, dict) or not provider:
        return ["%s: request.provider must be a non-empty object of %s; omit "
                "the field entirely to leave routing to the vendor"
                % (where, ", ".join(PROVIDER_FIELDS))]
    for field in sorted(provider.keys()):
        if field not in PROVIDER_FIELDS:
            out.append("%s: request.provider.%s is not an OpenRouter provider "
                       "routing field. Allowed: %s"
                       % (where, field, ", ".join(PROVIDER_FIELDS)))
    order = provider.get("order", "__missing__")
    if order != "__missing__":
        if not isinstance(order, list) or not order:
            out.append("%s: request.provider.order must be a non-empty LIST of "
                       "upstream slugs, in preference order (got %r)"
                       % (where, order))
        else:
            for slug in order:
                if not _nonempty_str(slug) or not PROVIDER_SLUG_RE.match(slug):
                    out.append("%s: request.provider.order carries %r, which is "
                               "not an upstream slug" % (where, slug))
    if "allow_fallbacks" in provider \
            and not isinstance(provider.get("allow_fallbacks"), bool):
        out.append("%s: request.provider.allow_fallbacks must be true or false, "
                   "got %r" % (where, provider.get("allow_fallbacks")))
    if provider.get("allow_fallbacks") is False and not provider.get("order"):
        out.append("%s: request.provider turns fallbacks OFF but names no "
                   "`order` — a pin with nothing to pin to refuses every route"
                   % where)
    return out


def _request_problems(entry, where):
    """`request` — the REQUEST-LEVEL CONTROLS this entry declares (MDL-5
    (reasoning budget)).

    Two controls, one seam: a reasoning object and a provider routing object,
    each shaped as the vendor's own request body carries it, because the
    consumer puts them on that body UNCHANGED. An entry that declares no
    `request` produces today's payload byte for byte — the absence is the
    answer, and there is no default here to inherit. The registry never
    guesses.
    """
    if "request" not in entry:
        return []
    request = entry.get("request")
    if not isinstance(request, dict) or not request:
        return ["%s: `request` must be a non-empty object of request-level "
                "controls (%s). Omit the field entirely — an empty declaration "
                "and no declaration are the same request, said two ways"
                % (where, ", ".join(REQUEST_CONTROLS))]
    out = []
    if entry.get("transport") != "api":
        out.append("%s: `request` declares request-level controls but the "
                   "transport is %r. Only an `api` call carries a request body"
                   % (where, entry.get("transport")))
    for field in sorted(request.keys()):
        if field not in REQUEST_CONTROLS:
            out.append("%s: request.%s is not a request control. Allowed: %s"
                       % (where, field, ", ".join(REQUEST_CONTROLS)))
    if "reasoning" in request:
        out.extend(_reasoning_problems(request.get("reasoning"), where))
    if "provider" in request:
        out.extend(_provider_problems(request.get("provider"), where))
    return out


def _default_max_tokens_problems(entry, where):
    """`default_max_tokens` — the output budget a request that names none
    inherits for THIS model (MDL-5 (reasoning budget)).

    A text model spends its output budget on output; a reasoning model spends
    an unbounded prefix of it on thinking the caller never sees, so one global
    default cannot be right for both. The CEILING is not checked here: it is
    the consumer's config (`max_tokens_cap`), and the consumer refuses an entry
    that asks past it BY NAME rather than the registry pretending to know it.
    """
    if "default_max_tokens" not in entry:
        return []
    value = entry.get("default_max_tokens")
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return ["%s: `default_max_tokens` must be a positive integer — the "
                "budget a request that names none inherits for this model "
                "(got %r)" % (where, value)]
    return []


# ------------------------------------------------------------------ manifests

def validate_models(doc):
    """Return a list of findings for models.json. Empty list = valid."""
    out = []
    if not isinstance(doc, dict):
        return ["models.json: top level must be an object, got %s"
                % type(doc).__name__]
    if doc.get("schema") != 1:
        out.append("models.json: `schema` must be 1, got %r" % doc.get("schema"))
    models = doc.get("models")
    if not isinstance(models, list):
        return out + ["models.json: `models` must be a LIST of entries "
                      "(a list is what makes a duplicate `id` detectable)"]

    seen = {}
    for index, entry in enumerate(models):
        where = "models[%d]" % index
        if not isinstance(entry, dict):
            out.append("%s: entry must be an object, got %s"
                       % (where, type(entry).__name__))
            continue
        model_id = entry.get("id")
        if not _nonempty_str(model_id):
            out.append("%s: `id` is missing or empty" % where)
        elif not ID_RE.match(model_id):
            out.append("%s: id %r is not id-shaped (^[a-z0-9][a-z0-9._-]*$)"
                       % (where, model_id))
        else:
            where = "models[%d] (%s)" % (index, model_id)
            if model_id in seen:
                out.append("%s: DUPLICATE id — already used by %s. Two entries "
                           "cannot answer for one name" % (where, seen[model_id]))
            else:
                seen[model_id] = where

        for field in ("label", "vendor"):
            if not _nonempty_str(entry.get(field)):
                out.append("%s: `%s` is missing or empty" % (where, field))

        modality = entry.get("modality")
        if not isinstance(modality, list) or not modality:
            out.append("%s: `modality` must be a non-empty list (one of: %s)"
                       % (where, ", ".join(MODALITIES)))
        else:
            for value in modality:
                if value not in MODALITIES:
                    out.append("%s: modality %r is unknown. Allowed: %s"
                               % (where, value, ", ".join(MODALITIES)))

        problem = _enum_problem(entry, "status", STATUSES, where)
        if problem:
            out.append(problem)
        problem = _enum_problem(entry, "transport", TRANSPORTS, where)
        if problem:
            out.append(problem)

        if "key_env" not in entry:
            out.append("%s: `key_env` is missing. Declare it — write null if "
                       "the model spends no key; absent is not an answer" % where)
        else:
            problem = _key_env_problem(entry.get("key_env"))
            if problem:
                out.append("%s: `key_env` %s" % (where, problem))

        # An `api` transport SPENDS a key. `key_env: null` is the claude-cli
        # answer (a login, not a key); on an api model it is a model whose
        # key nobody wrote down, and the consumer would fail at call time,
        # in a worker, on someone else's job (MDL-4 (openrouter vendor)).
        if entry.get("transport") == "api" and "key_env" in entry \
                and entry.get("key_env") is None:
            out.append("%s: transport is \"api\" but `key_env` is null. An "
                       "api call spends a key — name the env var, or change "
                       "the transport" % where)
        # A `local` transport runs weights on our own machine and spends NO
        # key; a key name on it is a guess about a call that never leaves
        # the machine (SI-172 (model id drafts)).
        if entry.get("transport") == "local" \
                and entry.get("key_env") is not None:
            out.append("%s: transport is \"local\" but `key_env` is %r. Local "
                       "weights spend no key — write null"
                       % (where, entry.get("key_env")))

        if "vendor_id" in entry:
            vendor_id = entry.get("vendor_id")
            if not _nonempty_str(vendor_id) or not VENDOR_ID_RE.match(vendor_id) \
                    or DIGIT_RUN_RE.search(vendor_id.split("/")[0]):
                out.append("%s: vendor_id %r is not vendor-id shaped "
                           "(lowercase, at most one `/`, no whitespace, no "
                           "key-like digit run)" % (where, vendor_id))

        out.extend(_request_problems(entry, where))
        out.extend(_default_max_tokens_problems(entry, where))
        out.extend(_cost_problems(entry, where))
        out.extend(_secret_field_problems(entry, where))

        aliases = entry.get("aliases", [])
        if not isinstance(aliases, list):
            out.append("%s: `aliases` must be a list" % where)
            aliases = []
        for alias in aliases:
            if not _nonempty_str(alias) or not ID_RE.match(alias):
                out.append("%s: alias %r is not id-shaped" % (where, alias))
            elif alias in seen and seen[alias] != where:
                out.append("%s: alias %r COLLIDES with %s. One name, one model "
                           "— a consumer migrating to the registry would get "
                           "two answers" % (where, alias, seen[alias]))
            else:
                seen[alias] = where

        sources = entry.get("sources", [])
        if not isinstance(sources, list):
            out.append("%s: `sources` must be a list of repo-relative paths"
                       % where)
    return out


def validate_assets(doc, repo=None):
    """Findings for trained-assets.json.

    `repo` is the root the `record` paths resolve against. Pass None to skip
    the on-disk check — that is what the inline selftest fixtures use, and the
    only thing they skip.
    """
    out = []
    if not isinstance(doc, dict):
        return ["trained-assets.json: top level must be an object, got %s"
                % type(doc).__name__]
    if doc.get("schema") != 1:
        out.append("trained-assets.json: `schema` must be 1, got %r"
                   % doc.get("schema"))
    assets = doc.get("assets")
    if not isinstance(assets, list):
        return out + ["trained-assets.json: `assets` must be a LIST of entries"]

    seen = {}
    for index, entry in enumerate(assets):
        where = "assets[%d]" % index
        if not isinstance(entry, dict):
            out.append("%s: entry must be an object, got %s"
                       % (where, type(entry).__name__))
            continue
        asset_id = entry.get("id")
        if not _nonempty_str(asset_id):
            out.append("%s: `id` is missing or empty" % where)
        elif not ID_RE.match(asset_id):
            out.append("%s: id %r is not id-shaped (^[a-z0-9][a-z0-9._-]*$)"
                       % (where, asset_id))
        else:
            where = "assets[%d] (%s)" % (index, asset_id)
            if asset_id in seen:
                out.append("%s: DUPLICATE id — already used by %s"
                           % (where, seen[asset_id]))
            else:
                seen[asset_id] = where

        problem = _enum_problem(entry, "kind", KINDS, where)
        if problem:
            out.append(problem)
        problem = _enum_problem(entry, "status", STATUSES, where)
        if problem:
            out.append(problem)

        if not _nonempty_str(entry.get("brand")):
            out.append("%s: `brand` is missing or empty" % where)

        trigger = entry.get("trigger")
        if not _nonempty_str(trigger):
            out.append("%s: `trigger` is missing or empty" % where)
        elif not TRIGGER_RE.match(trigger):
            out.append("%s: trigger %r is not the shape the engine emits "
                       "(^[a-z0-9]{1,24}$)" % (where, trigger))

        if "lora_url" in entry:
            out.append("%s: `lora_url` may not be inlined. An index REFERENCES "
                       "the record and copies nothing from it — an inlined url "
                       "is a second copy that will drift" % where)

        record = entry.get("record")
        if not _nonempty_str(record):
            out.append("%s: `record` is missing or empty" % where)
        elif os.path.isabs(record) or ".." in record.split("/"):
            out.append("%s: record %r must be a repo-relative path that does "
                       "not escape the repo" % (where, record))
        elif not record.endswith("lora.json"):
            out.append("%s: record %r must point at a `lora.json` written by "
                       "train_identity.py" % (where, record))
        elif repo is not None:
            full = os.path.join(repo, record)
            if not os.path.isfile(full):
                out.append("%s: record %r does not exist. A dangling reference "
                           "is the failure this index exists to prevent"
                           % (where, record))

        # Every declared field is checked, not just the ones that were easy
        # to (MDL-7 (registry validator honest)): a VALID that skips a field
        # is a VALID nobody can rely on.
        trained = entry.get("trained")
        if not _nonempty_str(trained):
            out.append("%s: `trained` is missing or empty" % where)
        elif not TRAINED_RE.match(trained):
            out.append("%s: trained %r is not YYYY-MM-DD" % (where, trained))

        if not _nonempty_str(entry.get("certified_by")):
            out.append("%s: `certified_by` is missing or empty" % where)

        out.extend(_secret_field_problems(entry, where))
    return out


# What `load` returns when there is no document to validate. A sentinel, not
# None: a file whose content is JSON `null` loads as None, and that is a
# document — an invalid one, which exits 2 with a finding, never 3 (MDL-7
# (registry validator honest)).
LOAD_FAILED = object()


def load(path):
    """Read a manifest, or return LOAD_FAILED saying exactly what went wrong.

    Never raises: a missing, unreadable or non-JSON file is a load failure
    (exit 3), whatever the operating system says about it.
    """
    if not os.path.isfile(path):
        print("MISSING: %s" % path)
        return LOAD_FAILED
    try:
        handle = open(path)
        try:
            text = handle.read()
        finally:
            handle.close()
    except (OSError, UnicodeDecodeError) as exc:
        print("UNREADABLE: %s — %s" % (path, exc))
        return LOAD_FAILED
    try:
        return json.loads(text)
    except ValueError as exc:
        print("UNREADABLE: %s is not valid JSON — %s" % (path, exc))
        return LOAD_FAILED


# ------------------------------------------------------------------- selftest

GOOD_MODEL = {
    "id": "fixture-model", "label": "Fixture", "vendor": "fixture",
    "modality": ["text"], "cost": "unpriced",
    "cost_reason": "fixture — never called", "status": "draft",
    "key_env": "FIXTURE_API_KEY", "transport": "api", "aliases": ["fixture"],
}
GOOD_ASSET = {
    "id": "fixture-asset", "kind": "character", "brand": "fixturebrand",
    "trigger": "fixtureperson", "record": "brands/fixturebrand/x/lora.json",
    "trained": "2026-09-01", "status": "draft",
    "certified_by": "fixture-certifier",
}


def _model_doc(*entries):
    return {"schema": 1, "models": [dict(e) for e in entries]}


def _asset_doc(*entries):
    return {"schema": 1, "assets": [dict(e) for e in entries]}


def _with(base, **changes):
    out = dict(base)
    out.update(changes)
    return out


def _without(base, field):
    out = dict(base)
    out.pop(field, None)
    return out


def _load_problems(content, unreadable):
    """Put `content` in a TEMP file, `load` it, and say what went wrong.

    Returns a list of problems — empty means `load` behaved. The temp file is
    removed afterwards; no real manifest is read (MDL-7 (registry validator
    honest)).
    """
    handle, path = tempfile.mkstemp(prefix="models-selftest-", suffix=".json")
    saved = sys.stdout
    try:
        os.write(handle, content.encode("utf-8"))
        os.close(handle)
        if unreadable:
            os.chmod(path, 0)
            if os.access(path, os.R_OK):
                # Root reads a chmod-0 file; there is nothing to prove here.
                return []
        sys.stdout = io.StringIO()
        try:
            result = load(path)
        except Exception as exc:  # the defect this case exists to catch
            return ["load raised %s: %s" % (type(exc).__name__, exc)]
        finally:
            said = sys.stdout.getvalue()
            sys.stdout = saved
        if unreadable:
            if result is not LOAD_FAILED:
                return ["load returned %r, not LOAD_FAILED" % (result,)]
            if "UNREADABLE: " not in said:
                return ["load did not say UNREADABLE (said %r)" % said]
            return []
        if result is not None:
            return ["load returned %r for JSON null, not None" % (result,)]
        return []
    finally:
        sys.stdout = saved
        try:
            os.chmod(path, 0o600)
            os.remove(path)
        except OSError:
            pass


def selftest():
    """Prove the rejections on INLINE fixtures. Touches no real manifest."""
    cases = []

    # The control. If this ever fails, every rejection below is meaningless —
    # a validator that refuses everything is not a validator.
    cases.append(("CONTROL: a good pair passes",
                  validate_models(_model_doc(GOOD_MODEL)),
                  validate_assets(_asset_doc(GOOD_ASSET), repo=None),
                  None))

    # 1. A value-shaped key_env — the lowercase/hyphen/long form a pasted
    #    vendor key takes. Deliberately not a real vendor prefix: a fixture
    #    that trips a secret scanner is a fixture that costs someone an hour.
    cases.append(("REJECT: key_env holding a pasted key value",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL,
                      key_env="zz-fixture-notarealkey-3f9a2b7c1d4e5f60"))),
                  [], "key_env"))
    # 2. A value-shaped key_env that PASSES the name shape and is still a key —
    #    caught on the digit run. Both prongs are load-bearing.
    cases.append(("REJECT: key_env holding an UPPERCASE key value",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, key_env="ZZQA1234567890ABCD"))),
                  [], "key_env"))
    # 3. An unknown status.
    cases.append(("REJECT: unknown status",
                  validate_models(_model_doc(_with(GOOD_MODEL,
                                                   status="blessed"))),
                  validate_assets(_asset_doc(_with(GOOD_ASSET,
                                                   status="shipped")),
                                  repo=None),
                  "status"))
    # 4. A duplicate id.
    cases.append(("REJECT: duplicate id",
                  validate_models(_model_doc(GOOD_MODEL, GOOD_MODEL)),
                  validate_assets(_asset_doc(GOOD_ASSET, GOOD_ASSET),
                                  repo=None),
                  "DUPLICATE id"))
    # 5. An alias colliding with another entry's id — the migration hazard.
    cases.append(("REJECT: alias colliding with another model's id",
                  validate_models(_model_doc(
                      GOOD_MODEL,
                      _with(GOOD_MODEL, id="other-model",
                            aliases=["fixture-model"]))),
                  [], "COLLIDES"))
    # 6. A bare cost number, and a silent zero.
    cases.append(("REJECT: cost as a bare number (no unit, no answer)",
                  validate_models(_model_doc(_with(GOOD_MODEL, cost=0.03))),
                  [], "cost"))
    cases.append(("REJECT: a $0.00 rate with no words",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, cost={"usd_per_image": 0},
                      cost_reason=""))),
                  [], "0 with no `cost_reason`"))
    # 7. unpriced with no reason.
    cases.append(("REJECT: unpriced with no reason",
                  validate_models(_model_doc(_with(GOOD_MODEL,
                                                   cost_reason=""))),
                  [], "cost_reason"))
    # 8. A secret pasted under any name at all.
    cases.append(("REJECT: a secret-named field",
                  validate_models(_model_doc(_with(GOOD_MODEL,
                                                   api_key="whatever"))),
                  [], "may not exist in a manifest"))
    # 9. An index entry that copies the weights url instead of referencing it.
    cases.append(("REJECT: trained asset inlining lora_url",
                  [], validate_assets(_asset_doc(_with(
                      GOOD_ASSET, lora_url="https://fal.media/x.safetensors")),
                      repo=None),
                  "lora_url"))
    # 10. A dangling record path, checked against a real root.
    cases.append(("REJECT: trained asset whose record does not exist",
                  [], validate_assets(_asset_doc(GOOD_ASSET), repo=REPO),
                  "does not exist"))

    # 11. An api-transport model that names no key (MDL-4 (openrouter vendor)). null is the
    #     claude-cli answer; on an api model it is a call that fails later.
    cases.append(("REJECT: transport api with key_env null",
                  validate_models(_model_doc(_with(GOOD_MODEL, key_env=None))),
                  [], "transport is \"api\" but `key_env` is null"))
    #     …and the CONTROL for it: claude-cli with null is still fine.
    cases.append(("CONTROL: transport claude-cli with key_env null passes",
                  validate_models(_model_doc(_with(GOOD_MODEL, key_env=None,
                                                   transport="claude-cli"))),
                  [], None))
    # 12. A vendor_id that is not a vendor id.
    cases.append(("REJECT: a malformed vendor_id",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, vendor_id="Z-AI/GLM 5.3 flash"))),
                  [], "vendor_id"))
    cases.append(("CONTROL: a namespaced vendor_id passes",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, vendor_id="fixture-org/fixture-model-1.0"))),
                  [], None))

    # 13. MDL-5 (reasoning budget) — the request-level controls. The CONTROLs
    #     first: a full declaration passes, and so does NO declaration, which
    #     is the case that protects every caller that never asked for one.
    cases.append(("CONTROL: a full request declaration passes",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL,
                      request={"reasoning": {"enabled": False},
                               "provider": {"order": ["FixtureUpstream"],
                                            "allow_fallbacks": False}},
                      default_max_tokens=16000))),
                  [], None))
    cases.append(("CONTROL: an entry declaring no request controls passes",
                  validate_models(_model_doc(GOOD_MODEL)), [], None))
    cases.append(("REJECT: a control that is not a request control",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, request={"thinking": {"enabled": False}}))),
                  [], "request.thinking"))
    cases.append(("REJECT: reasoning declaring BOTH effort and max_tokens",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, request={"reasoning": {"effort": "low",
                                                         "max_tokens": 2048}}))),
                  [], "BOTH `effort` and `max_tokens`"))
    cases.append(("REJECT: an unknown reasoning effort",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, request={"reasoning": {"effort": "utmost"}}))),
                  [], "request.reasoning.effort"))
    cases.append(("REJECT: a reasoning budget under the vendor's minimum",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, request={"reasoning": {"max_tokens": 512}}))),
                  [], "request.reasoning.max_tokens"))
    cases.append(("REJECT: an unknown reasoning field",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, request={"reasoning": {"budget": 4000}}))),
                  [], "request.reasoning.budget"))
    cases.append(("REJECT: a provider order that is not a list of slugs",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, request={"provider": {"order": []}}))),
                  [], "request.provider.order"))
    cases.append(("REJECT: fallbacks off with nothing to pin to",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL,
                      request={"provider": {"allow_fallbacks": False}}))),
                  [], "nothing to pin to"))
    cases.append(("REJECT: allow_fallbacks that is not a boolean",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, request={"provider": {"order": ["Fixture"],
                                                        "allow_fallbacks": "no"}}))),
                  [], "allow_fallbacks"))
    cases.append(("REJECT: request controls on a claude-cli entry",
                  validate_models(_model_doc(_with(
                      GOOD_MODEL, transport="claude-cli", key_env=None,
                      request={"reasoning": {"enabled": False}}))),
                  [], "Only an `api` call carries a request body"))
    cases.append(("REJECT: an empty request declaration",
                  validate_models(_model_doc(_with(GOOD_MODEL, request={}))),
                  [], "`request` must be a non-empty object"))
    cases.append(("REJECT: a default_max_tokens that is not a positive integer",
                  validate_models(_model_doc(_with(GOOD_MODEL,
                                                   default_max_tokens=0))),
                  [], "default_max_tokens"))

    # 14. SI-172 (model id drafts) — the `local` transport. The CONTROL first:
    #     local weights with no key and a zero rate that says why, pass.
    good_local = _with(GOOD_MODEL, id="fixture-local", aliases=[],
                       transport="local", key_env=None,
                       cost={"usd_per_run": 0},
                       cost_reason="runs on our own machine; electricity only")
    cases.append(("CONTROL: a local entry with key_env null passes",
                  validate_models(_model_doc(good_local)), [], None))
    cases.append(("REJECT: a local entry naming a key",
                  validate_models(_model_doc(_with(
                      good_local, key_env="FIXTURE_API_KEY"))),
                  [], "Local weights spend no key"))
    cases.append(("REJECT: an unknown transport",
                  validate_models(_model_doc(_with(GOOD_MODEL,
                                                   transport="carrier"))),
                  [], "`transport` is 'carrier'"))
    cases.append(("REJECT: a local entry's alias equal to another model's id",
                  validate_models(_model_doc(
                      GOOD_MODEL,
                      _with(good_local, aliases=["fixture-model"]))),
                  [], "COLLIDES"))

    # 15. MDL-7 (registry validator honest) — every declared asset field is
    #     checked, and `load` answers the contract instead of raising.
    cases.append(("REJECT: trained asset missing trained",
                  [], validate_assets(_asset_doc(_without(GOOD_ASSET,
                                                          "trained")),
                                      repo=None),
                  "`trained` is missing or empty"))
    cases.append(("REJECT: trained asset whose trained is not YYYY-MM-DD",
                  [], validate_assets(_asset_doc(_with(GOOD_ASSET,
                                                       trained="Sept 1")),
                                      repo=None),
                  "is not YYYY-MM-DD"))
    cases.append(("REJECT: trained asset missing certified_by",
                  [], validate_assets(_asset_doc(_without(GOOD_ASSET,
                                                          "certified_by")),
                                      repo=None),
                  "`certified_by` is missing or empty"))
    cases.append(("LOAD: an unreadable manifest is a load failure, not a raise",
                  [], _load_problems("{}", unreadable=True), None))
    cases.append(("LOAD: JSON null is a document, not a load failure",
                  [], _load_problems("null", unreadable=False), None))

    failures = []
    for label, model_findings, asset_findings, expect in cases:
        findings = list(model_findings) + list(asset_findings)
        if expect is None:
            ok = not findings
            detail = "; ".join(findings[:3])
        else:
            ok = bool(findings) and any(expect in f for f in findings)
            detail = ("no finding mentioning %r (got: %s)"
                      % (expect, "; ".join(findings[:3]) or "nothing"))
        print("  %s %s" % ("ok  " if ok else "FAIL", label))
        if not ok:
            failures.append("%s — %s" % (label, detail))
    print("")
    if failures:
        for line in failures:
            print("SELFTEST FAILED: %s" % line)
        return 2
    print("selftest: %d cases, all as expected" % len(cases))
    return 0


# ----------------------------------------------------------------------- main

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate the models registry manifests.")
    parser.add_argument("--models", default=MODELS_PATH,
                        help="path to models.json")
    parser.add_argument("--assets", default=ASSETS_PATH,
                        help="path to trained-assets.json")
    parser.add_argument("--repo", default=REPO,
                        help="root the trained-asset `record` paths resolve "
                             "against")
    parser.add_argument("--no-record-check", action="store_true",
                        help="skip the on-disk existence check for `record` "
                             "paths (for fixtures that reference nothing real)")
    parser.add_argument("--selftest", action="store_true",
                        help="run the inline rejection fixtures and exit; "
                             "reads no real manifest")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    findings = []
    models_doc = load(args.models)
    assets_doc = load(args.assets)
    if models_doc is LOAD_FAILED or assets_doc is LOAD_FAILED:
        return 3

    findings.extend(validate_models(models_doc))
    findings.extend(validate_assets(
        assets_doc, repo=None if args.no_record_check else args.repo))

    if findings:
        print("INVALID — %d finding%s:"
              % (len(findings), "" if len(findings) == 1 else "s"))
        for line in findings:
            print("  %s" % line)
        return 2

    print("valid: %d model%s, %d trained asset%s"
          % (len(models_doc.get("models", [])),
             "" if len(models_doc.get("models", [])) == 1 else "s",
             len(assets_doc.get("assets", [])),
             "" if len(assets_doc.get("assets", [])) == 1 else "s"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
