"""The TRELLIS.2 input sheet (components/model-inputs/inputs/trellis.2-4b.json), checked before make3d loads any weights.

    findings = check(image, pipeline_type="512", texture_size=2048)   # [{id, level, say}]
    refuse(findings)                                                   # SystemExit naming every error

Every number is read from the sheet through model-inputs' public `limits()`. No network. Python 3.9.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "trellis.2-4b"


def _limits():
    sp = importlib.util.spec_from_file_location("sheet_check_input_rules", HERE.parent / "model-inputs" / "input_rules.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m.limits(MODEL)


def check(images, pipeline_type="512", texture_size=2048):
    L, out = _limits(), []
    images = [images] if isinstance(images, (str, Path)) else list(images)
    if len(images) != L["input_images"]:
        out.append({"id": "input-images", "level": "error", "say": f"{len(images)} pictures; {MODEL} is built from exactly {L['input_images']}."})
    for im in images:
        if not Path(str(im)).is_file():
            out.append({"id": "image-missing", "level": "error", "say": f"the picture is missing: {Path(str(im)).name}."})
    grid = str(pipeline_type).split("_")[0]
    if grid not in L["grid_resolutions"]:
        out.append({"id": "grid-resolution", "level": "error", "say": f"grid {pipeline_type!r} is not one of {', '.join(L['grid_resolutions'])}."})
    if int(texture_size) > L["texture_px_example"]:
        out.append({"id": "texture-size", "level": "error", "say": f"texture {texture_size}px is over the sheet's {L['texture_px_example']}px."})
    return out


def refuse(findings, who="make3d"):
    errs = [f for f in findings if f["level"] == "error"]
    if errs:
        raise SystemExit(who + ": stopped before building — " + " ".join(f"[{f['id']}] {f['say']}" for f in errs))
