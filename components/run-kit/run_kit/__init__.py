"""run-kit — the parts every marketing chain shares, lifted from the runners
where each one already worked (rollout Step 0b, 2026-09-20).

    from run_kit import paths, prompts, model, record, filing, pool
    from run_kit.stage import Chain

Nothing here names a brand, a tool or a prompt. Stdlib only.
"""
from . import paths, prompts, model, record, filing, pool, claude_flags  # noqa: F401
from .stage import Chain  # noqa: F401
