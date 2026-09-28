#!/usr/bin/env python3
"""CLI entry point for the language engine — see language_layer/engine.py.

    python3 components/language-layer/query_language.py --brand <b> --avatars
    python3 components/language-layer/query_language.py --brand <b> --topic-list
    python3 components/language-layer/query_language.py --brand <b> \
        --stage hooks --profile <chain-profile>.json

A stage map is a per-chain definition, so this entry point ships none: without
`--profile`, `--stage` selects no evidence types and the whole bank ranks. The
two machines pass their own maps from their shims.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from language_layer.engine import main   # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
