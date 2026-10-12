#!/usr/bin/env python3
"""CLI entry point for the Drive pipe — see gdrive_creator/engine.py.

    python3 components/gdrive-creator/make_doc.py <html> \
        --name "<document title>" --parent <drive-folder-id>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gdrive_creator.engine import main   # noqa: E402

if __name__ == "__main__":
    main()
