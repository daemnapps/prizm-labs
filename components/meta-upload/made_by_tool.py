"""Only pictures made by the image production tool reach the approval page (image-production RULE GATE-5, 2026-11-11).

Every video thumbnail and every image/carousel picture on a card must be a file image production delivered: its
sha256 is in an image-production run record (image_production/provenance.py). The filer refuses one that is not
(`refuse`), and the page's card check `made_by_tool` goes red on one (`check`). Video files are out of scope.

Cards filed before the switch's `since` are left exactly as they were filed: the check is not added to them.
The gate runs only where the image tool carries its switch (`installed`): a checkout whose image tool has no
`gate.made_by_tool` entry does not fingerprint its pictures yet, so nothing is refused there.
ROLLBACK: image-production models.json `gate.made_by_tool` (`on`, or one lane), or MADE_BY_TOOL_GATE_OFF.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
PICTURE = {".png", ".jpg", ".jpeg", ".webp"}
_PV = None


def pv():
    """image-production's provenance.py, loaded by path (stdlib only; the image_production package is not imported)."""
    global _PV
    if _PV is None:
        f = HERE.parent / "image-production" / "image_production" / "provenance.py"
        spec = importlib.util.spec_from_file_location("ip_provenance", f)
        _PV = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_PV)
    return _PV


def is_picture(p):
    return Path(p).suffix.lower() in PICTURE


def installed():
    """True where the image tool carries the gate's switch (models.json `gate.made_by_tool`). The entry lands with the
    tool's own fingerprinting; without it no picture has a record, and a gate that ran would refuse every one."""
    return bool(pv().switch())


def on(lane):
    return installed() and pv().on(lane)


def refuse(lane, pictures):
    """Returns ({source name: {sha256, record}}, [why...]) for the pictures to be filed. Empty whys = all made by the tool.
    Gate off for the lane: ({}, [])."""
    if not on(lane):
        return {}, []
    seen, bad = {}, []
    for p in pictures:
        p = Path(p)
        if not p.is_file() or not is_picture(p):
            continue
        digest = pv().sha256(p)
        where = pv().known(p, digest)
        if where and where.endswith(".made.json") and not pv()._in_ledger(digest):
            pv().stamp(p, "hand-off", record=where)    # the card check reads the ledger, not the sidecar
        if where:
            seen[str(p)] = {"sha256": digest, "record": where}
        else:
            bad.append(f"{p.name}: {pv().SAY}.")
    return seen, bad


def applies(card, lane):
    since = pv().since()
    return on(lane) and (not since or str(card.get("made_at") or "") >= since)


def _converted_ok(rec):
    """The filer converted a tool-made source (carousel slides go up as png): its source's record still holds."""
    sha, where = rec.get("sha256") or "", rec.get("record") or ""
    if not (rec.get("converted") and sha):
        return False
    if pv()._in_ledger(sha):
        return True
    try:
        return sha in Path(where).read_text(encoding="utf-8")
    except OSError:
        return False


def check(folder, card, lane):
    """(ok, why) for the card's pictures as they sit in its folder, or None when the check does not apply to this card."""
    if not applies(card, lane):
        return None
    folder = Path(folder)
    names = [n for n in card.get("media") or [] if is_picture(n)] + list((card.get("thumbs") or {}).values())
    filed = card.get("made_by_tool") or {}
    bad = []
    for n in names:
        f = folder / n
        if not f.is_file():
            continue                                   # the media check already names a missing file
        if pv().known(f):
            continue
        if _converted_ok(filed.get(n) or {}):
            continue                                   # a carousel slide the filer turned into a png from a tool-made source
        bad.append(n)
    if bad:
        return False, (f"{len(bad)} picture(s) not made by the image production tool: {', '.join(bad[:4])}. "
                       "Make each with image-production make.py and file the file it delivered")
    return True, (f"{len(names)} picture(s), each made by the image production tool" if names else "no pictures on this card")
