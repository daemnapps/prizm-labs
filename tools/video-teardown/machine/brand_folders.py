"""The brand folder's names, new and old (v6 layout, 25 Sep 2026).

Every brand folder moved to one layout (brands/_TEMPLATE/FOLDERS.json). A brand
that has not moved yet still has the old names, so every lookup here tries the
new name first and the old one after. Nothing is ever moved or renamed here.
"""
from pathlib import Path

# new name -> old names, most recent first. Mirrors brands/_TEMPLATE/FOLDERS.json.
NAMES = {
    "brand-identity/position.md": ("position.md",),
    "brand-identity/story.md": ("story.md",),
    "brand-identity/identity-anchors.md": ("identity-anchors.md",),
    "brand-identity": ("identity",),
    "ai-elements/characters": ("ai-cast",),
    "content-creators": ("channels/creators", "creators"),
    "email-sms": ("email",),
    "intake": ("existing-content",),
    "competitors": ("competitive",),
}


def home(brand_root, new):
    """The folder or file for `new` under this brand: the new name if it
    exists, else the first old name that does, else the new name (so a
    missing file is reported under the name it should have)."""
    b = Path(brand_root)
    for rel in (new, *NAMES.get(new, ())):
        if (b / rel).exists():
            return b / rel
    return b / new


def resolve(path):
    """A `brands/<brand>/...` path, re-pointed to whichever name exists.
    Works both ways: a config naming the new folder finds a brand not yet
    moved, and one still naming the old folder finds a moved brand."""
    p = Path(path)
    if p.exists():
        return p
    s = p.as_posix()
    for new, olds in NAMES.items():
        for a, b in [(new, o) for o in olds] + [(o, new) for o in olds]:
            if f"/{a}/" in f"{s}/" or s.endswith(f"/{a}"):
                i = s.find(f"/{a}")
                head, tail = s[:i], s[i + 1 + len(a):]
                # only the part right after brands/<brand>/
                if Path(head).parent.name != "brands":
                    continue
                cand = Path(f"{head}/{b}{tail}")
                if cand.exists():
                    return cand
    return p
