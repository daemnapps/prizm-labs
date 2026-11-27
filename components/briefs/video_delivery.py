"""Public surface: pack(folder) adds the shared video delivery instructions to a handoff.

No generation or network. Keeps the creative brief intact and replaces only its
marked delivery appendix on a repeat pack. Called by both video handoff roads.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
START = "<!-- video-delivery-instructions:start -->"
END = "<!-- video-delivery-instructions:end -->"


def pack(folder, standalone=True):
    folder = Path(folder)
    briefs = [p for p in [folder / "BRIEF.md", folder / "handoff.md"] if p.is_file()]
    briefs += sorted((folder / "briefs").glob("*/brief.md"))
    if not briefs:
        raise ValueError("No creative brief or handoff instructions found")
    for brief in briefs:
        _append(brief)
    if standalone:
        (folder / "VIDEO-DELIVERY.md").write_text((HERE / "video-delivery.md").read_text(encoding="utf-8"), encoding="utf-8")
        return ["VIDEO-DELIVERY.md"]
    return []


def _append(brief):
    text = brief.read_text(encoding="utf-8")
    instructions = (HERE / "video-delivery.md").read_text(encoding="utf-8")
    appendix = START + "\n\n" + instructions + "\n" + END
    if START in text:
        before, rest = text.split(START, 1)
        if END not in rest:
            raise ValueError("Unclosed video delivery appendix; preserve the brief and repair the marker")
        _, after = rest.split(END, 1)
        text = before + appendix + after
    else:
        text = text.rstrip() + "\n\n" + appendix + "\n"
    brief.write_text(text, encoding="utf-8")
