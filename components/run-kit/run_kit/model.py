"""One headless `claude -p` caller for every chain.

Lifted: tiers + size escalation + the usage-limit message from email.py
(:60-70, :167-195, :282-285); the clean environment, the anti-chatter guard and
transient-only retry from video-teardown run.py (:27-35, :484-521, :557-605).
New here: a timeout — no caller had one.

What ran (2026-11-26): a caller that passes `run_dir=` gets one line per call in
<run_dir>/what-ran.jsonl, through run_kit/ran.py — only while ran.RECORD is on
(it ships off). With the switch off, or no run_dir, call() is exactly as before."""
import os
import subprocess
import threading
import time

from . import ran as _ran
from .claude_flags import effort, effort_args

_seen = threading.local()   # the door that answered and the attempts, per thread (pool runs calls side by side)

# The tiers come from the one model table, run_kit/tiers.json "shared" (2026-11-26): reads (the answer is in
# the input), checks (applies rules that are written down), designs (makes the calls nobody wrote down).
from . import tiers as _tiers   # noqa: E402
TIERS = _tiers.shared()
SMALL_WINDOW_CHARS = 350_000                  # ~what a 200k-token window holds, kept conservative
TRANSIENT = ("overloaded", "rate limit", "429", "500", "502", "503", "529", "timeout",
             "timed out", "connection", "temporarily", "econnreset")
PURE_TEXT = ("You are one stage of a document pipeline. Return only the deliverable text. "
             "No tools, no preamble, no report about what you did.")
KEEP_ENV = ("HOME", "PATH", "TERM", "USER", "LOGNAME", "SHELL", "LANG", "LC_ALL", "TMPDIR")  # USER: the CLI finds whoever is signed in on this machine by it — any account, never one hard-wired (2026-10-07)


class UsageLimit(Exception):
    """The account is out of usage — not a broken stage. Stop the whole run."""


class StageFailed(Exception):
    pass


def pick(tier, prompt_chars=0, forced=None, tiers=None):
    """The model for a step: a forced model wins; otherwise the step's tier —
    escalated when the prompt is too big for a small window. Returns (model, why)."""
    tiers = tiers or TIERS
    if forced:
        return forced, "forced"
    m = tiers[tier]
    if prompt_chars > SMALL_WINDOW_CHARS and m != tiers["designs"]:
        return tiers["designs"], f"escalated: prompt is {prompt_chars / 1e6:.2f}MB, past a small window"
    return m, tier


def _clean_env():
    return {k: v for k, v in os.environ.items() if k in KEEP_ENV}


def call(prompt_text, model, label="?", tries=4, wait=30, timeout=1800, runner=None,
         run_dir=None, tier=None, why=None, prompt_file=None):
    """Run one prompt. `runner(prompt, model) -> (code, stdout, stderr)` is the
    seam tests use; the default shells out to `claude -p`.

    `run_dir`, `tier`, `why` and `prompt_file` only feed the what-ran record
    (run_kit/ran.py); they never change what is called or returned. While the
    record is on, they ride down to the door, which writes one line per call;
    when the door never saw the call (a runner of the caller's own, an answer
    the session hand already wrote), this writes the line itself."""
    if not _ran.on():
        return _call(prompt_text, model, label, tries, wait, timeout, runner)
    _ran.set_context(run_dir=str(run_dir) if run_dir else None, step=str(label), tier=tier, why_model=why,
                     prompt_file=prompt_file)
    _seen.door, _seen.attempts = None, 0
    t0 = time.time()

    def own(outcome, **more):
        if _ran.wrote():
            return                                   # the door already wrote this call's line(s)
        _ran.note(model_asked=model, effort=effort(), prompt_sha256_12=_ran.fingerprint(prompt_text),
                  prompt_chars=len(prompt_text), outcome=outcome, route="model.call", caller=_ran.caller(),
                  answered_by=_seen.door or ("the caller's runner" if runner else None),
                  attempts=_seen.attempts or None, seconds=round(time.time() - t0, 1), **more)
    try:
        try:
            text = _call(prompt_text, model, label, tries, wait, timeout, runner)
        except UsageLimit:
            own("usage_limit")
            raise
        except StageFailed as e:
            own("waiting_for_hand" if "session hand" in str(e) else "failed")
            raise
        except Exception:
            own("failed")
            raise
        own("done", chars_out=len(text))
        return text
    finally:
        _ran.clear_context()


def _call(prompt_text, model, label, tries, wait, timeout, runner):
    def default(p, m):
        # NO ACCOUNT IS WIRED IN (owner, 2026-10-23): claude_door tries the company
        # key, then the long-life token, then this machine's login — the next one
        # when one runs out — so no single account's limit stops a chain.
        from run_kit import claude_door
        r = claude_door.run(["--model", m, "--output-format", "text",
                             "--append-system-prompt", PURE_TEXT], p, timeout=timeout)
        _seen.door = getattr(r, "credential", None)          # which door answered, for the what-ran record
        return r.returncode, r.stdout, r.stderr
    # THE SESSION HAND (2026-09-30): when the CLI's login is capped, a Claude
    # session answers instead. DAEMN_HAND_DIR names a folder: the prompt is left
    # there as <label>-<hash>.prompt.md and the call stops; the session writes
    # <label>-<hash>.md beside it, and the re-run reads it. Every check on the
    # answer still applies.
    hand = os.environ.get("DAEMN_HAND_DIR")
    if hand and runner is None:
        import hashlib, re as _re
        from pathlib import Path as _P
        hd = _P(hand); hd.mkdir(parents=True, exist_ok=True)
        stem = _re.sub(r"[^a-z0-9]+", "-", str(label).lower()).strip("-") + "-" + hashlib.md5(prompt_text.encode()).hexdigest()[:8]
        done = hd / (stem + ".md")
        if done.exists() and done.read_text().strip():
            _seen.door = "the session running the chain"
            return done.read_text().strip()
        (hd / (stem + ".prompt.md")).write_text(prompt_text)
        raise StageFailed(f"waiting for the session hand: {hd / (stem + '.prompt.md')}")
    runner = runner or default
    last = ""
    for attempt in range(1, tries + 1):
        _seen.attempts = attempt
        try:
            code, out, err = runner(prompt_text, model)
        except subprocess.TimeoutExpired:
            code, out, err = 1, "", f"timed out after {timeout}s"
        if code == 0 and out.strip():
            return out.strip()
        both = f"{out}\n{err}".lower()
        if "limit" in both and ("usage" in both or "spend" in both):
            raise UsageLimit(f"stage {label} on {model} was refused: {(out or err).strip()[:240]}")
        last = (f"stage {label} failed on {model} (prompt {len(prompt_text) / 1e6:.2f}MB, exit {code})\n"
                f"  stderr: {err.strip()[:400] or '(empty — often the prompt exceeding the model window)'}\n"
                f"  stdout: {out.strip()[:200] or '(empty)'}")
        if not any(t in both for t in TRANSIENT) or attempt == tries:
            break                                   # a bad answer is not retried
        time.sleep(wait * attempt)
    raise StageFailed(last)
