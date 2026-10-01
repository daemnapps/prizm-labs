#!/usr/bin/env python3
"""Direct Drive API — turn the stage 8 HTML into a real Google Doc.

    python3 drive.py <html> --name "<title>" --parent <drive-folder-id>

SHIM (DP-1, 2026-09-02). The pipe moved to `components/gdrive-creator/` so it
has ONE home: it lived here, inside this machine's internals, and the copy lab
reached in through a `sys.path.insert` into this folder — a dependency that
would have broken on any refactor here. This file is the same command it always
was: it re-exports the component's engine and hands it this machine's two
habits — the key vault (`keys.py`) and the Drive mount (`chain.runs_mirror()`)
— so nothing about a run here changes. The docstring above the engine is the
doctrine; read it there.

LAYOUT STAYED. `gdoc.py` is this machine's own document layout and did not
move; only the plumbing did.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keys

_COMPONENT = Path(__file__).resolve().parents[2] / "gdrive-creator"
sys.path.append(str(_COMPONENT))        # appended, never ahead of this machine
from gdrive_creator import engine as _engine     # noqa: E402


def _mount_lookup():
    """Where finished runs land on this machine's Drive mount — the folder the
    per-creator `creators/` tree hangs under."""
    import chain as C
    return C.runs_mirror()


_engine.configure(key_lookup=keys.get, mount_lookup=_mount_lookup)

# The public surface this file has always had, unchanged.
SCOPES = _engine.SCOPES
DOC_MIME = _engine.DOC_MIME
DRIVE_XATTR = _engine.DRIVE_XATTR
FOLDER_MIME = _engine.FOLDER_MIME
_creds = _engine._creds
service = _engine.service
esc = _engine.esc
find = _engine.find
folder = _engine.folder
share = _engine.share
_share = _engine._share
creator_share = _engine.creator_share
upload_doc = _engine.upload_doc
upload_file = _engine.upload_file
find_file = _engine.find_file
folder_id = _engine.folder_id
main = _engine.main

if __name__ == "__main__":
    main()
