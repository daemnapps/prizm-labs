#!/usr/bin/env python3
"""The plumbing a stage runs on: find the prompt, fill it, send it, stamp it.

Four small things, kept together because every one of them is about the
PROMPT being the product (the owner's standing rule) rather than about calendars:

    latest_prompt(stage)   the highest -vN- file wins
    fill(template, fields) deterministic substitution, so a run replays
    claude(text, model)    one stateless call, text in, text out
    sha(path)              what exactly ran, stamped into the record

Moved out of the email chain's `email.py` on 2026-09-13 when the calendar
became its own component. Same bodies, same behaviour.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

from paths import PROMPTS, WORKSPACE

DEFAULT_MODEL = "claude-opus-5"

# WHICH MODEL A LAYER GETS (rollout, 2026-09-20). The tiers are the run kit's
# (`components/run-kit/run_kit/model.py`): reads · checks · designs. Both of the
# calendar's thinking layers make calls nobody wrote down — who is live, what
# the month argues — so both are `designs`. A `--model` on the command line
# still forces one model onto every layer, exactly as before.
LAYER_TIERS = {"cells": "designs", "concepts": "designs"}
_FALLBACK_TIERS = {"reads": "claude-haiku-4-5-20251001",
                   "checks": "claude-sonnet-5", "designs": DEFAULT_MODEL}


def _kit_model():
    """The run kit's model module, found under the workspace — or None when
    this checkout has no run kit, in which case the table above stands in."""
    kit = WORKSPACE / "components" / "run-kit"
    if not (kit / "run_kit" / "model.py").is_file():
        return None
    if str(kit) not in sys.path:
        sys.path.append(str(kit))
    try:
        from run_kit import model as M
        return M
    except Exception:
        return None


def pick_model(key, prompt_chars=0, forced=None):
    """-> (model, why) for one layer. A forced model wins; otherwise the
    layer's tier, escalated by the kit when the prompt outgrows a small window."""
    tier = LAYER_TIERS.get(key, "designs")
    M = _kit_model()
    if M:
        return M.pick(tier, prompt_chars, forced)
    return (forced, "forced") if forced else (_FALLBACK_TIERS[tier], tier)


def out_of_usage(*texts):
    """The account has run out — not a broken layer. The run kit's own test."""
    both = "\n".join(t or "" for t in texts).lower()
    return "limit" in both and ("usage" in both or "spend" in both)


def doctrine(slice_name):
    """A Schwartz doctrine slice, bound by path — never restated in a prompt.
    Rendered by components/marketing-doctrine/render.py from frameworks.json."""
    p = WORKSPACE / "components/marketing-doctrine/slices" / f"{slice_name}.md"
    return p.read_text().strip() if p.is_file() else f"[UNFILLED: {slice_name} doctrine slice not found]"


def sha(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else None


def latest_prompt(stage, folder=None):
    """Highest -vN- wins, same rule as every other lane."""
    folder = Path(folder or PROMPTS)
    best, best_v = None, -1
    for f in folder.glob(f"{stage}-*.md"):
        m = re.search(r"-v(\d+)-", f.name)
        if m and int(m.group(1)) > best_v:
            best, best_v = f, int(m.group(1))
    if not best:
        sys.exit(f"no prompt file found for {stage} in {folder}")
    return best


def fill(template, fields):
    """Deterministic substitution, so a run can be replayed without a model."""
    out = template
    for name, value in fields.items():
        out = out.replace("{" + name + "}", str(value) if value else "(none supplied)")
    return out


def claude(prompt_text, model=DEFAULT_MODEL):
    # A headless -p session still inherits the repo's project Stop hooks even
    # for a stateless prompt-in/text-out call. A blocking hook cannot prompt a
    # human, so the session writes its answer to the HOOK instead of the
    # deliverable and the output is silently wrong (hit in copy, 2026-08-24).
    # Keep the tree clean of whatever a Stop hook guards before running.
    r = subprocess.run(
        ["claude", "-p", "--model", model, "--output-format", "text"],
        input=prompt_text + "\n\nReturn only the deliverable. No tools, no preamble.",
        capture_output=True, text=True,
    )
    # Out of usage is not a broken layer. It is only looked for where a refusal
    # can be — a failed call, or an answer too short to be a month — so a real
    # plan that happens to use the words is never mistaken for one.
    if (r.returncode or len(r.stdout) < 600) and out_of_usage(r.stdout, r.stderr):
        # Stop once, with one line. A retry would buy the same refusal again;
        # everything already written for this month stays on disk.
        sys.exit(f"STOPPED — the account is out of usage on {model}: "
                 f"{(r.stderr or r.stdout).strip()[:200]} · nothing was retried; "
                 "run the same command again when usage is back.")
    if r.returncode:
        sys.exit(f"a stage failed: {r.stderr[:400]}")
    return r.stdout.strip()


def catalogue_path(brand, workspace, seed=None):
    """The type catalogue is the BRAND's knowledge (the owner, 2026-08-31). A brand
    without one runs on the component's clean seed — and should copy that seed
    into its own folder to own it."""
    from paths import BP
    p = BP.brand_path(brand, "email-sms", "email-types.json", root=Path(workspace) / "brands")
    if p.is_file():
        return p
    print(f"     NOTE: {brand} has no email/email-types.json — running on the "
          "generic seed catalogue. Copy the seed into the brand folder to own it.")
    return Path(seed) if seed else None
