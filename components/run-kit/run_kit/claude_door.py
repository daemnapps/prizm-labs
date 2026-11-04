"""The one door every chain's `claude -p` goes through — no account is ever wired in.

the owner, 2026-10-23: "It should just be able to run regardless of who is working
on the code base or what account is working on the code base. It's just code.
We are the orchestrator and the chains run regardless."

A chain step is code calling a model. Which credential it runs on is decided
here, once, the same way on every machine, in this order:

  1. a company API key — ANTHROPIC_API_KEY in the one key file
     (this repo's .env, read through components/keys/loader.py). Billed to
     the company, never expires, any person or machine runs on it.
  2. a long-life token — CLAUDE_CODE_OAUTH_TOKEN in the same file
     (`claude setup-token`, lasts a year).
  3. whatever login the `claude` CLI holds on this machine — any account —
     and then every other Claude login saved on it: each folder under
     ~/.claude-accounts/ is one account (`CLAUDE_CONFIG_DIR`), logged in once.
  4. Codex — the OpenAI login this machine holds (the owner, 2026-10-23: "doesn't
     matter if I'm using Codex, my Claude one, Claude two, or the team having a
     Claude or the team having a Claude ... it should just work with whoever's
     account is in use"). Text steps only.
  5. the Claude session running the chain (the session hand), last.

When one runs out ("limit", "expired", "not logged in") the next one is tried
before the step fails, so no single account's limit stops a chain. The
environment handed to the CLI is a plain one (the keep list below) so a
desktop session's own variables never steer which login it picks.

    from run_kit import claude_door
    text = claude_door.ask(prompt, model="sonnet")                 # text out
    r = claude_door.run(["--model", m, "--output-format", "text"], prompt)

Stdlib only. No credential value is ever printed, logged or put in an error.
"""
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
from pathlib import Path

KEEP = ("HOME", "PATH", "TERM", "USER", "LOGNAME", "SHELL", "LANG", "LC_ALL", "TMPDIR",
        "DAEMN_HAND_DIR", "HAND_DIR")    # the session-hand folder rides along to a stand-in on PATH
OUT_OF_ROOM = re.compile(r"limit|expired|not logged in|log ?in|authenticat|credit balance|401|403", re.I)
_LOADER = Path(__file__).resolve().parents[2] / "keys" / "loader.py"


def _key(name):
    """One key through the shared loader; None when it is not there."""
    try:
        spec = importlib.util.spec_from_file_location("_door_keys_loader", _LOADER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        v = mod.key(name, required=False)
    except Exception:
        return None
    return (v or "").strip() or None


def credentials():
    """The credentials available here, best first, as (label, env additions).
    The machine's own login is always last and always present."""
    out = []
    api = _key("ANTHROPIC_API_KEY")
    if api and api.startswith("sk-ant-api"):
        out.append(("company key", {"ANTHROPIC_API_KEY": api}))
    tok = _key("CLAUDE_CODE_OAUTH_TOKEN")
    if tok and tok.startswith("sk-ant-"):     # a placeholder in the key file is not a token
        out.append(("long-life token", {"CLAUDE_CODE_OAUTH_TOKEN": tok}))
    out.append(("this machine's login", {}))
    # Every other Claude login saved on this machine: one folder per account
    # under ~/.claude-accounts/, each logged in once with
    # `CLAUDE_CONFIG_DIR=~/.claude-accounts/<name> claude` (then /login).
    accounts = Path.home() / ".claude-accounts"
    if accounts.is_dir():
        for d in sorted(x for x in accounts.iterdir() if x.is_dir()):
            out.append((f"the {d.name} login", {"CLAUDE_CONFIG_DIR": str(d)}))
    return out


def codex_binary():
    """The Codex command on this machine, if it holds one: on PATH, else the copy
    the ChatGPT desktop app ships. None when there is no Codex here."""
    found = shutil.which("codex", path=base_env()["PATH"])
    if found:
        return found
    for app in (Path("/Applications/ChatGPT.app"), Path.home() / "Applications/ChatGPT.app"):
        c = app / "Contents/Resources/codex-cli/bin/codex"
        if c.is_file():
            return str(c)
    return None


def _text_step(args):
    """Codex can stand in only where the step wants plain text back."""
    fmt = args[args.index("--output-format") + 1] if "--output-format" in args[:-1] else "text"
    return fmt == "text" and not any(a in args for a in ("--json-schema", "--input-format"))


def codex(args, prompt, timeout=1800):
    """One text step on the Codex login: the prompt in, the final answer out, in a
    throwaway folder with a read-only sandbox, nothing kept. None when there is
    no Codex here or the step is not a text step."""
    exe = codex_binary()
    if not exe or not _text_step(args):
        return None
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "answer.txt"
        r = subprocess.run([exe, "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only",
                            "-o", str(out), "-"], input=prompt, capture_output=True, text=True,
                           timeout=timeout, cwd=tmp, env={**base_env(), "CODEX_HOME": str(Path.home() / ".codex")})
        text = out.read_text() if out.is_file() else ""
    r.stdout, r.credential = text, "the Codex login"
    if r.returncode == 0 and not text.strip():
        r.returncode = 1
    return r


STAMP = re.compile(r"<!--\s*prompt:.*?-->", re.S)


def step_key(args, prompt):
    """The hand's name for one step. The stamp a stage writes at the top of its
    output (prompt file, model, the time it ran) is left out, so a re-run of an
    earlier stage, which stamps a new time, does not make every later step look
    new and loop (found 2026-10-23 on the image chain)."""
    return hashlib.sha1((" ".join(args) + "\n" + STAMP.sub("", prompt)).encode()).hexdigest()[:12]


def base_env():
    env = {k: os.environ[k] for k in KEEP if k in os.environ}
    # The caller's PATH first, the usual homes after: a run that puts its own
    # `claude` ahead (a stand-in, a pinned version) keeps it.
    env["PATH"] = env.get("PATH", "") + ":/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
    return env


def binary():
    return shutil.which("claude", path=base_env()["PATH"]) or "claude"


def _flags():
    """run_kit/claude_flags.py, read beside this file (this module is also loaded by path)."""
    spec = importlib.util.spec_from_file_location("run_kit_claude_flags", Path(__file__).with_name("claude_flags.py"))
    flags = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(flags)
    return flags


def _effort_args():
    return _flags().effort_args()


def _model_args():
    return _flags().model_args()


def run(args, prompt, timeout=1800, cwd=None, extra_env=None):
    """`claude -p <args>` with the prompt on stdin, trying each credential in
    turn. Returns the CompletedProcess of the first that answers, or of the
    last one tried. `extra_env` (non-credential settings) rides every try.
    Every call runs at the chains' one effort level (LD-73 (explicit effort),
    run_kit/claude_flags.py) unless the caller already names --effort, and on
    the chains' one model (LD-100 (chain model explicit)) unless it names --model."""
    if "--effort" not in args:
        args = [*args, *_effort_args()]
    if "--model" not in args:
        args = [*args, *_model_args()]
    # An answer the session hand already wrote for this exact step wins first:
    # a chain re-run to advance returns it instantly instead of asking again.
    hand = os.environ.get("DAEMN_HAND_DIR") or os.environ.get("HAND_DIR")
    if hand:
        h = step_key(args, prompt)
        done = Path(hand) / (h + ".md")
        old_h = hashlib.sha1((" ".join(args) + "\n" + prompt).encode()).hexdigest()[:12]
        if not (done.is_file() and done.read_text().strip()) and (Path(hand) / (old_h + ".md")).is_file():
            done = Path(hand) / (old_h + ".md")     # answers written before the stamp was left out
        if done.is_file() and done.read_text().strip():
            r = subprocess.CompletedProcess(args, 0, done.read_text(), "")
            r.credential = "the session running the chain"
            return r
    last = None
    # DAEMN_HAND_FIRST: send the step straight to the session hand (creative steps
    # a stand-in login answered flat, found 2026-10-23: Codex wrote sterile briefs).
    if os.environ.get("DAEMN_HAND_FIRST") and hand:
        creds, use_codex = [], False
    else:
        creds, use_codex = credentials(), True
    for label, cred in creds:
        env = {**base_env(), **(extra_env or {}), **cred}
        last = subprocess.run([binary(), "-p", *args], input=prompt, capture_output=True,
                              text=True, timeout=timeout, cwd=cwd, env=env)
        last.credential = label
        said = (last.stdout or "") + (last.stderr or "")
        if last.returncode == 0 and not (len(said) < 300 and OUT_OF_ROOM.search(said)):
            return last
        if not OUT_OF_ROOM.search(said):
            return last          # a real failure, not an account running out — the next one would fail the same
    # CODEX — the OpenAI login on this machine, when every Claude one is out.
    cx = codex(args, prompt, timeout) if use_codex else None
    if cx is not None:
        said = (cx.stdout or "") + (cx.stderr or "")
        if cx.returncode == 0:
            return cx
        last = cx if OUT_OF_ROOM.search(said) or not last else last
    # LAST DOOR — THE SESSION RUNNING THE CHAIN (the owner, 2026-10-23: "all I know is I
    # have usage on this account here … I switch between my different accounts").
    # Every credential on this machine is out, so the step goes to the Claude
    # session that started the run, on whatever account that session is signed in
    # to. DAEMN_HAND_DIR names the folder: the prompt is left as <hash>.prompt.md,
    # the session writes <hash>.md beside it, and the same step run again returns it.
    hand = os.environ.get("DAEMN_HAND_DIR") or os.environ.get("HAND_DIR")
    if hand:
        hd = Path(hand)
        hd.mkdir(parents=True, exist_ok=True)
        h = step_key(args, prompt)
        done = hd / (h + ".md")
        if done.is_file() and done.read_text().strip():
            return subprocess.CompletedProcess(args, 0, done.read_text(), "")
        (hd / (h + ".prompt.md")).write_text(prompt)
        last = subprocess.CompletedProcess(args, 1, "", f"waiting for the session hand: {hd / (h + '.prompt.md')} "
                                                       f"(write the answer to {done})")
        last.credential = "the session running the chain"
    return last


def ask(prompt, model="sonnet", args=(), timeout=1800, cwd=None):
    """Text in, text out. Raises with the CLI's own words when every credential fails."""
    r = run(["--model", model, "--output-format", "text", *args], prompt, timeout=timeout, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(f"claude failed on {r.credential}: {((r.stderr or '') + (r.stdout or '')).strip()[-300:]}")
    return r.stdout
