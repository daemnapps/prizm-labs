"""Provider-neutral text execution for Prizm's existing pipeline stages.

No provider SDK, credentials, or provider fallback. Session requests can be
answered by any assistant. Command mode speaks JSON on stdin and plain text
on stdout; the configured adapter owns its provider and model selection.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


class Pending(RuntimeError):
    """A stage has a durable request awaiting an assistant's answer."""


def active():
    return bool(os.environ.get("PRIZM_TEXT_EXECUTOR"))


def identity():
    mode = os.environ.get("PRIZM_TEXT_EXECUTOR", "")
    return mode + ":" + os.environ.get("PRIZM_TEXT_AUTHOR", "unspecified")


def atomic(path, body):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
        f.write(body)
        temp = f.name
    os.replace(temp, path)


def _valid(text, as_json):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("The text executor returned an empty answer")
    if as_json:
        json.loads(text)
    return text.strip()


def answer(request_path, text, author):
    """Bind an answer to the exact request; consumed by call(), then checked by its caller."""
    p = Path(request_path)
    request = json.loads(p.read_text())
    text = _valid(text, request["as_json"])
    if not author.strip():
        raise ValueError("Name the assistant/model that wrote this answer")
    atomic(p.with_name("answer.json"), json.dumps({
        "request_id": request["id"], "text": text, "author": author,
        "answered_at": time.time(),
    }, indent=2) + "\n")


def call(prompt, label, *, system="", as_json=False, image=None):
    mode = os.environ.get("PRIZM_TEXT_EXECUTOR")
    if mode not in ("session", "command"):
        raise ValueError("PRIZM_TEXT_EXECUTOR must be session or command; no fallback was called")
    home = os.environ.get("PRIZM_TEXT_REQUESTS")
    if not home:
        raise ValueError("PRIZM_TEXT_REQUESTS must name this run's private request directory")
    attachments = []
    if image:
        p = Path(image).resolve(strict=True)
        attachments.append({"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    payload = {"version": 1, "label": str(label), "system": system,
               "prompt": prompt, "as_json": bool(as_json), "attachments": attachments}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    d = Path(home).expanduser().resolve() / digest
    request = {**payload, "id": digest}
    atomic(d / "request.json", json.dumps(request, indent=2, ensure_ascii=False) + "\n")
    display = system + "\n\n" + prompt
    if attachments:
        display += "\n\nInspect the attached image: " + attachments[0]["path"]
    if as_json:
        display += "\n\nReturn valid JSON only."
    atomic(d / "prompt.md", display.strip() + "\n")
    af = d / "answer.json"
    if mode == "command":
        # Mac/Linux worker lock: concurrent consumers must not pay twice for
        # the same request. The OS releases the lock if the process dies.
        import fcntl
        with (d / ".executor.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not af.exists():
                argv = json.loads(os.environ.get("PRIZM_TEXT_COMMAND", "null"))
                if not isinstance(argv, list) or not argv or not all(isinstance(a, str) and a for a in argv):
                    raise ValueError("PRIZM_TEXT_COMMAND must be a JSON argv array")
                timeout = float(os.environ.get("PRIZM_TEXT_TIMEOUT", "600"))
                # No shell; no automatic retry of potentially billable work.
                result = subprocess.run(argv, input=json.dumps(request), capture_output=True,
                                        text=True, timeout=timeout)
                if result.returncode:
                    raise RuntimeError(f"Text adapter exited {result.returncode}; no provider fallback was called")
                answer(d / "request.json", result.stdout, os.environ.get("PRIZM_TEXT_AUTHOR", "command-adapter"))
    deadline = time.monotonic() + max(0, float(os.environ.get("PRIZM_TEXT_WAIT", "0")))
    while not af.exists() and time.monotonic() < deadline:
        time.sleep(min(0.5, max(0, deadline - time.monotonic())))
    if not af.exists():
        raise Pending(f"Text request awaiting an assistant: {d / 'request.json'}")
    result = json.loads(af.read_text())
    if result.get("request_id") != digest:
        raise ValueError("Answer belongs to a different prompt; refusing stale output")
    text = _valid(result.get("text"), as_json)
    atomic(d / "receipt.json", json.dumps({
        "request_id": digest, "executor": mode, "author": result.get("author"),
        "output_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "consumed_at": time.time(), "validation": "transport only; stage checks still required",
    }, indent=2) + "\n")
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("answer")
    p.add_argument("request")
    p.add_argument("--file", required=True)
    p.add_argument("--author", required=True)
    p = sub.add_parser("pending")
    p.add_argument("directory")
    p = sub.add_parser("run")
    p.add_argument("--requests", required=True)
    p.add_argument("--author", required=True)
    p.add_argument("--executor", choices=("session", "command"), default="session")
    p.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == "answer":
        answer(args.request, Path(args.file).read_text(), args.author)
    elif args.action == "pending":
        for p in sorted(Path(args.directory).glob("*/request.json")):
            if not p.with_name("answer.json").exists():
                print(json.dumps({"path": str(p), "label": json.loads(p.read_text())["label"]}))
    else:
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        if not argv:
            parser.error("run requires a command after --")
        env = dict(os.environ, PRIZM_TEXT_EXECUTOR=args.executor,
                   PRIZM_TEXT_AUTHOR=args.author, PRIZM_TEXT_REQUESTS=str(Path(args.requests).resolve()))
        raise SystemExit(subprocess.call(argv, env=env))


if __name__ == "__main__":
    main()
