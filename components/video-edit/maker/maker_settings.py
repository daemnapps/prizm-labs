"""Where the hand-off builder finds a production and the writing runs: settings, never machine paths in the code.

- VIDEO_PRODUCTIONS     the folder of productions, one <production>/ each (brief.json, scenes/). Else
                        VIDEO_STUDIO_DATA/briefs (the Studio's settings name, kept so it keeps working), else
                        runs/video-studio/briefs in this workspace.
- VIDEO_PRODUCTION_BOARD the storyboard data holding handoff-requests/ (else VIDEO_STUDIO_BOARD_DATA; optional)
- VIDEO_WRITING         the writing runs, each with its production brief (else VIDEO_STUDIO_WRITING, else
                        runs/video-teardown/_work in this workspace)
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                                  # components/video-edit/maker -> the workspace


def _data():
    if os.environ.get("VIDEO_PRODUCTIONS"):
        return Path(os.environ["VIDEO_PRODUCTIONS"])
    if os.environ.get("VIDEO_STUDIO_DATA"):
        return Path(os.environ["VIDEO_STUDIO_DATA"]) / "briefs"
    return REPO / "runs" / "video-studio" / "briefs"


BRIEFS = _data()
WRITING = Path(os.environ.get("VIDEO_WRITING") or os.environ.get("VIDEO_STUDIO_WRITING")
               or REPO / "runs" / "video-teardown" / "_work")
if not os.environ.get("VIDEO_STUDIO_BOARD_DATA") and os.environ.get("VIDEO_PRODUCTION_BOARD"):
    os.environ["VIDEO_STUDIO_BOARD_DATA"] = os.environ["VIDEO_PRODUCTION_BOARD"]


def set_productions(path):
    global BRIEFS
    BRIEFS = Path(path)


def part(name, root=None):
    """A neighbour by name, wherever this workspace keeps it: `components/<name>` or `tools/<name>`."""
    root = Path(root or REPO)
    for shelf in ("components", "tools"):
        if (root / shelf / name).is_dir():
            return root / shelf / name
    return root / "components" / name
