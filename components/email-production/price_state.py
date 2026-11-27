#!/usr/bin/env python3
"""Which written emails does today's price check refuse? The one way another tool asks (2026-11-04).

    python3 price_state.py <brand> <run folder> [<run folder> …]

Prints {run folder: [problems]}, listing only the refused ones: a price the bank does not sell today, or a saving
without the condition the bank puts on it. These are the same checks that hold an email at delivery. Reads only.
"""
import json
import sys
from pathlib import Path

import simple_email as S


def refused(brand, runs):
    out = {}
    for r in runs:
        run = Path(r)
        try:
            email = json.loads((run / "deliverable" / "email.json").read_text())
        except (OSError, ValueError):
            continue
        problems = S.price_check(email, brand, run) + S.saving_check(email, brand, run)
        if problems:
            out[str(r)] = problems
    return out


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    print(json.dumps(refused(sys.argv[1], sys.argv[2:]), ensure_ascii=False))
