#!/usr/bin/env python3
"""Text in, text out, through Claude. The twin of gemini_text.py.

    claude_text.py --prompt-file P.md --var teardown_record=path.md --out out.md

Same contract as the Gemini runner: `{name}` in the prompt is replaced by the
whole contents of the file passed as `--var name=path`, the filled prompt is
sent, and the reply is written to `--out` with a provenance header. Swapping
one runner for the other is a one-word change in the caller.

**The Stop-hook trap, and why this checks for it.** A headless `claude -p`
session inherits the repo's Stop hooks even for a stateless prompt-in/text-out
call. If a hook blocks, the session cannot ask a human — so it answers the
HOOK instead of writing the deliverable, and the output is silently wrong
rather than loudly missing (confirmed in the copy tool, 2026-08-24). `--bare`
skips hooks but also skips normal login, so it is not a fix. This runner
checks the reply for the shape of a hook answer and fails loudly instead of
writing a corrupted stage output.
"""

import argparse, re, subprocess, sys, time
from pathlib import Path

# A reply that talks about the hook rather than doing the work. Cheap to spot,
# expensive to miss — a corrupted stage output poisons everything downstream.
# The floor below which a reply cannot be a stage output.
#
# It was 1500, tuned to the failure it was written for: a 597-byte reply that
# talked ABOUT the brief instead of being it. But an organic photograph has
# one zone and no copy in it at all, so a legitimate injection for one is
# genuinely short — two of nine <brand> runs produced 1408 and 1439 characters
# of correct work and had it thrown away (2026-09-14).
#
# So the floor drops to what could not possibly be a document, and the real
# guard is CHAT_TELLS below, which catches the shape of the failure rather
# than its size.
MIN_CHARS = 350

# A reply written in the first person about the work, rather than the work.
CHAT_TELLS = (
    "the brief is done", "the brief is in chat", "in chat above",
    "i've written", "i have written", "let me know if", "denied this session",
    "once the artifact", "is ready for your", "one slot to fill",
)

HOOK_TELLS = (
    "run-log", "stop hook", "hook feedback", "uncommitted run outputs",
    "append a run-log", "blocking error",
)


def fill(template, pairs):
    """Substitute every {name} the TEMPLATE asks for.

    The unmet check reads the template, never the filled result. Supplied
    content can legitimately contain the placeholder string — the brand's
    identity-anchors file describes itself as "the {identity_anchors}
    variable" — and checking after substitution reads that as an unmet
    variable and refuses a prompt that is completely filled.
    """
    wants = set(re.findall(r"\{([a-z_]+)\}", template))
    given = {n for n, _ in pairs}
    unmet = sorted(wants - given)
    if unmet:
        sys.exit("prompt asks for " + ", ".join(unmet) + " — nothing supplies it")

    out, missing = template, []
    for name, path in pairs:
        f = Path(path)
        if not f.exists():
            missing.append(f"{name}={path}")
            continue
        out = out.replace("{" + name + "}", f.read_text(errors="replace"))
    if missing:
        sys.exit("missing input files: " + ", ".join(missing))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--var", action="append", default=[],
                    help="name=path, repeatable")
    # No model id lives here any more — the last one written here went stale.
    # run.py names one per stage; called bare, the default is the "designs"
    # tier out of components/run-kit, the one place the ids are kept.
    ap.add_argument("--model", default=None)
    ap.add_argument("--min-chars", type=int, default=MIN_CHARS,
                    help="the floor below which a reply is not a stage output; "
                         "a labelling answer is legitimately short")
    ap.add_argument("--out")
    a = ap.parse_args()

    if not a.model:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import paths as P
        sys.path.insert(0, str(P.RUN_KIT))
        from run_kit import model as M
        a.model = M.TIERS["designs"]

    pairs = []
    for v in a.var:
        if "=" not in v:
            sys.exit(f"--var wants name=path, got {v!r}")
        n, p = v.split("=", 1)
        pairs.append((n, p))

    prompt = fill(Path(a.prompt_file).read_text(), pairs)
    print(f"[1/2] sending {len(prompt)} chars to {a.model}")

    t0 = time.time()
    # `--tools ""` disables every built-in tool and `--strict-mcp-config`
    # skips the MCP servers. Without them the headless session inherits this
    # repo's whole toolbelt, goes agentic on a prompt that only asks for text,
    # and answers in the first person about what it did — "the brief is in
    # chat above" — instead of writing the brief. That reply is the right
    # length to look plausible and is silently wrong, which is worse than a
    # crash (marsmen-63 stage 3, 2026-09-13: 503 seconds for 597 bytes of
    # conversation).
    r = subprocess.run(
        ["claude", "-p", "--model", a.model, "--output-format", "text",
         "--tools", "", "--strict-mcp-config"],
        input=prompt + "\n\nReturn only the deliverable. No tools, no preamble.",
        capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"claude failed: {r.stderr[-500:]}")

    body = r.stdout.strip()
    if not body:
        sys.exit("claude returned nothing")

    # A stage output is a document. Anything this short is a sentence about
    # the document, not the document.
    if len(body) < a.min_chars:
        sys.exit(f"claude returned {len(body)} chars — too short to be a stage "
                 f"output (floor {a.min_chars}). Not writing it.\n\n" + body[:400])

    low = body[:1200].lower()
    if any(t in low for t in CHAT_TELLS):
        sys.exit(
            "the reply talks about the deliverable instead of being it — the "
            "headless session went agentic. Not writing it.\n\n" + body[:400])
    if any(t in low for t in HOOK_TELLS):
        sys.exit(
            "the reply answers a Stop hook, not the prompt — the working tree "
            "has something a hook is guarding. Clear it and re-run; writing "
            "this would corrupt the stage.\n\n" + body[:300])

    header = (f"<!-- prompt: {Path(a.prompt_file).name} | model: {a.model} | "
              f"vars: {', '.join(n for n, _ in pairs)} | "
              f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} | "
              f"{time.time()-t0:.0f}s -->\n\n")

    if a.out:
        Path(a.out).write_text(header + body + "\n")
        print(f"[2/2] full output → {a.out}")
    else:
        print(header + body)


if __name__ == "__main__":
    main()
