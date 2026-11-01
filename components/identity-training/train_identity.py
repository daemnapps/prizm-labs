#!/usr/bin/env python3
"""CLI entry point for the identity engine — see identity_training/engine.py.

    python3 components/identity-training/train_identity.py \
        --brand <brand> --character <name> [--out DIR] [--dry-run]
    python3 components/identity-training/train_identity.py \
        --brand <brand> --product <slug> [--out DIR] [--dry-run]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from identity_training.engine import main   # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
