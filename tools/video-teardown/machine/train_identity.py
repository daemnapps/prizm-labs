#!/usr/bin/env python3
"""Train a brand asset into a LoRA identity on fal — character or product.

    python3 train_identity.py --brand <brand> --character susan
    python3 train_identity.py --brand <brand> --product brilliance-body-scrub

SHIM (IDT-1, 2026-09-01). The engine moved to
`components/identity-training/` so trained identities are a curated asset
rather than a side-product of this machine. This file is the same command
it always was: it re-exports the component's engine and hands it this
machine's two habits — the key vault (`keys.py`) and the Drive mount
(`chain.drive_root()`) — so nothing about a run here changes. The
docstring above the engine is the doctrine; read it there.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keys

_COMPONENT = Path(__file__).resolve().parents[2] / "identity-training"
sys.path.append(str(_COMPONENT))        # appended, never ahead of this machine
from identity_training import engine as _engine      # noqa: E402


def _drive_lookup(rel):
    """This machine's Drive mirror of a repo-relative brand path."""
    import chain as C
    return C.drive_root() / rel


_engine.configure(key_lookup=keys.get, drive_lookup=_drive_lookup)

# The public surface this file has always had, unchanged.
WS = _engine.WS
TRAINER = _engine.TRAINER
STORAGE = _engine.STORAGE
fal = _engine.fal
brand_dir = _engine.brand_dir
drive_dir = _engine.drive_dir
images_from = _engine.images_from
character_set = _engine.character_set
product_set = _engine.product_set
main = _engine.main

if __name__ == "__main__":
    sys.exit(main())
