"""LD-62 (lean model calls): every model call this chain makes runs lean.

A `claude -p` started inside the repo loads every CLAUDE.md on the way up, the
default tools, the MCP servers and the user's settings: about 50k prompt tokens
before the stage prompt starts (measured 2026-10-20, the card's fold a-e). Run
from a fresh temp folder with no tools, no MCP servers and no settings sources,
a call carries only its own prompt. The brand facts are NOT lost: every stage
gets them in its prompt text, never from a CLAUDE.md.

Ruling (decision log 2026-10-21, fc42a0ff4c): lean ships for the email chain
only. No `--system-prompt` (it thinned video-writing's scene cells) and no
`--bare` (it ignores the plan token). `--setting-sources ""` drops
~/.claude/settings.json and its effortLevel, so the effort is passed by hand:
run-kit's one fixed level, run_kit/claude_flags.py EFFORT ("medium"; the team,
2026-10-21: "Yes email too", on the lead's "medium for the mini also covers
email?"). No environment knob.

    import lean_call
    r = lean_call.run(["claude", "-p", ...], input=..., capture_output=True, text=True)
    M.call(prompt, model, runner=lean_call.design_runner(M))   # run_kit.model
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_KIT = next(str(d / "components" / "run-kit") for d in Path(__file__).resolve().parents
            if (d / "components" / "run-kit").is_dir())
if _KIT not in sys.path:
    sys.path.append(_KIT)   # appended, never ahead of this machine
from run_kit.claude_flags import EFFORT   # noqa: E402  LD-73 (explicit effort)


def effort():
    """The chains' one effort level, run_kit.claude_flags.EFFORT."""
    return EFFORT


def lean_args():
    return ["--tools", "", "--strict-mcp-config", "--setting-sources", "",
            "--effort", effort()]


def run(argv, **kwargs):
    """subprocess.run(argv + the lean flags) from a fresh temp folder outside the
    repo, removed after the call — on a failure or a timeout too. An argv that
    already names --effort (LD-73 (explicit effort)) keeps its own: one only."""
    extra = lean_args()
    if "--effort" in argv:
        i = extra.index("--effort")
        del extra[i:i + 2]
    d = tempfile.mkdtemp(prefix="email-lean-")
    try:
        return subprocess.run(list(argv) + extra, cwd=d, **kwargs)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def door(args, prompt, timeout=None, **kwargs):
    """The lean call through run_kit's claude_door — no account wired in (the owner,
    2026-10-23): `args` are the claude -p arguments without the binary or -p;
    the lean flags and the temp folder are added here, the credential picked by
    the door. Returns the CompletedProcess."""
    from run_kit import claude_door
    extra = lean_args()
    if "--effort" in args:
        i = extra.index("--effort")
        del extra[i:i + 2]
    d = tempfile.mkdtemp(prefix="email-lean-")
    try:
        return claude_door.run(list(args) + extra, prompt, timeout=timeout, cwd=d, **kwargs)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def runner(M, timeout=1800):
    """A run_kit.model.call runner `(prompt, model) -> (code, stdout, stderr)`:
    run_kit's own default argv and timeout through the door, plus the lean flags
    and the temp folder. subprocess.TimeoutExpired propagates; call() handles it."""
    def go(p, m):
        r = door(["--model", m, "--output-format", "text", "--append-system-prompt", M.PURE_TEXT],
                 p, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    return go


def design_runner(M):
    """The design line's runner. None while DAEMN_HAND_DIR is set: call() takes
    the session hand only when it is given no runner, and that must survive."""
    if os.environ.get("DAEMN_HAND_DIR"):
        return None
    return runner(M)
