"""Where this component sits and how it reaches its neighbours: the workspace, a neighbour by name, a key by name.
No brand, person or machine path is named here."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]                                   # the workspace this component sits in
# where the neighbours' data is read from: this workspace, or another copy of it that holds the data (MOTION_WORKSPACE)
DATA_REPO = Path(os.environ.get("MOTION_WORKSPACE") or REPO)
# the writing runs (their frame maps and briefs); a second workspace copy may hold them (VIDEO_STUDIO_WRITING)
WRITING = Path(os.environ.get("VIDEO_STUDIO_WRITING") or REPO / "runs" / "video-teardown" / "_work")


def data_env():
    """When this copy of the workspace carries code only (MOTION_WORKSPACE names the copy that holds the data), the
    neighbours that read data by their own settings are pointed at it too, unless the caller already set them: the
    element bank and set prints (AI_WORKSPACE) and the writing runs (VIDEO_STUDIO_WRITING). The Studio's productions
    (VIDEO_STUDIO_DATA) are the caller's to name: they may sit outside any workspace."""
    ws = os.environ.get("MOTION_WORKSPACE")
    if ws:
        os.environ.setdefault("AI_WORKSPACE", ws)
        os.environ.setdefault("VIDEO_STUDIO_WRITING", str(Path(ws) / "runs" / "video-teardown" / "_work"))


def part(name, root=None):
    """A neighbour by name, wherever this workspace keeps it: `components/<name>` or `tools/<name>`."""
    root = Path(root or REPO)
    for shelf in ("components", "tools"):
        if (root / shelf / name).is_dir():
            return root / shelf / name
    return root / "components" / name


def key(name):
    """A key by name: the environment, then the workspace key loader (components/keys/loader.py)."""
    if os.environ.get(name):
        return os.environ[name]
    loader = part("keys")
    if (loader / "loader.py").is_file():
        sys.path.append(str(loader))
        try:
            import loader as L
            return L.key(name, required=False)
        except (Exception, SystemExit):  # noqa: BLE001
            return None
    return None


def house_model(job, default=None):
    """The model the Generative Model House names for a job (components/generative-model-house); `default` when this
    workspace copy has no house."""
    mh = part("generative-model-house")
    if (mh / "model_house.py").is_file():
        sys.path.append(str(mh))
        try:
            import model_house as MH
            return MH.model(job)
        except (Exception, SystemExit):  # noqa: BLE001
            return default
    return default
