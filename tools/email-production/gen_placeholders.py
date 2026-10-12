#!/usr/bin/env python3
"""RETIRED 2026-09-22 — it ran on fal, and fal is not a path any more.

the owner, 2026-09-22: *"remove anything with fal or flux lora, we decided to not
use these tools"* — the third ruling, after 2026-09-11 and 09-13.

This filled a run's image slots with `fal-ai/flux-pro/v1.1` candidates, reading
its key out of a plain-text `~/.daemn/keys.env` (which the Keychain rule had
already outlawed). Its only caller was `design_email.py`, the designed-template
path that the simple shape replaced on 2026-09-19 — history, not live.

**The live path makes pictures on GPT Image**: `simple_email.py` draws the hero
from step 8's direction and the offer picture FROM the real product photo. The
model is whatever `tools/image-production/models.json` routes to; nothing
here chooses one.
"""
import sys

sys.exit(
    "gen_placeholders.py is retired — it ran on fal (the owner, 2026-09-22; also 09-11 and 09-13).\n"
    "  pictures for an email:  python3 simple_email.py <run folder> --brand <brand>\n"
    "  the model route:        tools/image-production/models.json")
