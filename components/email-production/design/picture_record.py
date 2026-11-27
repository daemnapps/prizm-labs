"""One record per picture an email makes, so any picture can be traced and edited at the element level.

the owner, 2026-10-18: "If we need to generate a new image, we should know exactly how that image was actually
generated, its references, whatever the case may be. That way, we can make clean and clear edits at the element
level."

The image engine writes media/run.json, media/prompt-as-sent.txt and media/check.json for every picture, but into
the same three files, so each picture overwrote the last one's record. keep() files them per picture:

    <run>/media/records/<label>/record.json   what made it: section, purpose, direction, the prompt exactly as
                                              sent, every reference (product photo, brand asset, Pinterest pin
                                              with its page, earlier version), model, judge verdict, file, parent
    <run>/media/records/<label>/run.json, prompt-as-sent.txt, check.json   the engine's own files, untouched

The layout's picture points at its record (`"record": "media/records/<label>/record.json"`). remake() edits a picture
from its record: the current picture goes back in as the image to edit (one change, never a re-roll), with the same
references minus the mood pins, and the new record names the old one as its parent.

LD-81 (portable picture records): a record stores its picture and every reference as an LD-79 (Drive ref
resolver) ref, never a machine path — each reference is {"path": <what a page shows: the repo path or the Drive
label>, "ref": <the ref>, "kind"}, and the record's "file" has "file_ref" ({drive_id, label, bytes}) beside it.
remake() reads them back through refs.local(); one that cannot be read here is never dropped — remake raises
CannotRemake naming it, with the offer "remake from the brief instead?", and does nothing else. Old records keep
their machine paths (no backfill, LD-80 (stored path check) lists them); touching one on another Mac gets the offer.

LD-83 (picture try first): edit_inputs() is remake()'s reference loading on its own, so a try starts from exactly what
a remake would; keep_try() writes the record of a try a person added, in remake()'s record shape.
"""
import datetime
import hashlib
import json
import shutil
from pathlib import Path

OFFER = "remake from the brief instead?"


class CannotRemake(RuntimeError):
    """LD-81 (portable picture records): the picture can't be remade from its record here. `reason` says why,
    `missing` names every stored file that could not be read ("<as stored>: <why>"), `offer` is the question the
    person answers; a yes re-sends the change with from_brief. The message leads with the reason and the offer, so a
    caller that cuts it short still carries both."""

    def __init__(self, reason, missing=(), offer=OFFER):
        self.reason, self.missing, self.offer = reason, list(missing), offer
        names = ["%s (%s)" % (Path(m.split(": ", 1)[0]).name, m.split(": ", 1)[1] if ": " in m else "?") for m in self.missing]
        super().__init__("%s — %s%s" % (reason, offer, (" Missing: " + "; ".join(names)) if names else ""))


def _refs():
    """gdrive-creator's refs (LD-79 (Drive ref resolver)), found the way mirror() finds the reach: look.reach()
    puts gdrive-creator on the path."""
    import look as L
    L.reach()
    from gdrive_creator import refs
    return refs


def _folder(brand, run_dir):
    """The run's Drive folder, the one mirror() fills: Shared Assets/runs/email-production/<brand>/<label>."""
    return "Shared Assets/runs/email-production/%s/%s" % (brand, Path(run_dir).name)


def _drive_row(run_dir, f):
    """{drive_id, label, bytes} for a picture the image engine filed into the run's media/ and mirrored itself, from
    its media/drive.json (LD-64 (records Drive ids)); None when that record names no id for this file."""
    try:
        d = json.loads((Path(run_dir) / "media" / "drive.json").read_text())
    except (OSError, ValueError):
        return None
    for row in d.get("files") or []:
        if row.get("path") == f.name and row.get("id") and d.get("folder") and f.is_file():
            return {"drive_id": row["id"], "label": "%s/%s" % (d["folder"], f.name), "bytes": f.stat().st_size}
    return None


def _store(run_dir, brand, path):
    """One file as a stored ref: (ref, None), or (None, why) when nothing could be placed. A file under the repo
    (outside runs/) is its repo-relative path; a file under the run's media/ is its drive.json row, else put to the
    same place on the run's Drive mirror; anything else is put under the run's Drive folder, references/<hash of
    where it was>/, so two files with one name never land on each other. Never a machine path."""
    import look as L
    run_dir, f = Path(run_dir), Path(str(path))
    if not f.is_absolute():
        return str(f), None                                   # already repo-relative: it stays
    try:
        rel = f.resolve().relative_to(Path(L.REPO).resolve())
        if rel.parts and rel.parts[0] != "runs":
            return rel.as_posix(), None
    except ValueError:
        pass
    try:
        sub = f.resolve().parent.relative_to(run_dir.resolve()).as_posix()
        if sub != "media" and not sub.startswith("media/"):
            raise ValueError(sub)
        got = _drive_row(run_dir, f) if sub == "media" else None
        if got:
            return got, None
        folder = "%s/%s" % (_folder(brand, run_dir), sub)
    except ValueError:
        folder = "%s/references/%s" % (_folder(brand, run_dir), hashlib.sha1(str(f).encode()).hexdigest()[:8])
    R = _refs()
    try:
        return R.put(f, folder), None
    except Exception as e:  # noqa: BLE001 -- named in the record and printed, never silent; SystemExit stays loud
        why = type(e).__name__
        print("   ref: NOT stored on the Drive — %s: %s" % (f.name, why))
        return None, why


def _entry(run_dir, brand, path, kind, extra=None):
    """One reference as the record keeps it: {"path": the repo path or Drive label, "ref", "kind"}; a file that could
    not be placed keeps only its name and why ("ref": None, "not_stored")."""
    ref, why = _store(run_dir, brand, path)
    shown = ref["label"] if isinstance(ref, dict) else ref if ref else Path(str(path)).name
    e = {"path": shown, "ref": ref, "kind": kind}
    if why:
        e["not_stored"] = why
    e.update(extra or {})
    return e


def _kind(path, run_dir):
    p = str(path)
    if "/media/pins/" in p:
        return "Pinterest pin (mood only)"
    if "/products/" in p and "/packshot/" in p:
        return "real product photo"
    if "/products/" in p:
        return "real product picture"
    if str(run_dir) in p:
        return "earlier version of this picture"
    if "/cast/" in p or "/people/" in p:
        return "brand cast"
    return "brand asset"


def _pin_pages(run_dir):
    res = {}
    for f in (Path(run_dir) / "media" / "pins").glob("p*/pins.json"):
        try:
            d = json.loads(f.read_text())
        except ValueError:
            continue
        for x in d.get("pins", []):
            res[str(f.parent / x["file"])] = {"pin": x.get("pin"), "image": x.get("image"), "title": x.get("title"), "search": d.get("query")}
    return res


def keep(run_dir, label, section, req, made=None, held=None, error=None, parent=None):
    """File the engine's record for this picture and write record.json; returns its path relative to the run.
    Every reference and the picture itself are stored as refs (LD-81 (portable picture records)), placed on the
    run's Drive folder now when they are not already there; the run's folder is runs/email-production/<brand>/<label>."""
    run_dir = Path(run_dir)
    brand = run_dir.parent.name
    media = run_dir / "media"
    d = media / "records" / label
    d.mkdir(parents=True, exist_ok=True)
    for n in ("run.json", "prompt-as-sent.txt", "check.json", "elements.json"):
        if (media / n).is_file():
            shutil.copy2(media / n, d / n)
    run = {}
    try:
        run = json.loads((d / "run.json").read_text()) if (d / "run.json").is_file() else {}
    except ValueError:
        pass
    if run.get("label") not in (None, label):        # the engine's files belong to another picture: don't claim them
        for n in ("run.json", "prompt-as-sent.txt", "check.json", "elements.json"):
            (d / n).unlink(missing_ok=True)
        run = {}
    pins = _pin_pages(run_dir)
    refs = [_entry(run_dir, brand, r, _kind(r, run_dir), {"pinterest": pins[str(r)]} if str(r) in pins else None)
            for r in (run.get("context") or {}).get("references") or (req.get("references") or []) + (req.get("inspiration") or [])]
    pic = ((run.get("pictures") or [{}])[0]) if run.get("pictures") else {}
    file_ref = None
    if made:
        f = media / Path(made).name
        file_ref, _ = _store(run_dir, brand, f if f.is_file() else made)
    rec = {"label": label, "section": section, "made_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "state": "made" if made else "held" if held else "refused" if error else "unknown",
           "file": ("media/" + Path(made).name) if made else None, "file_ref": file_ref,
           "purpose": req.get("purpose"), "product": req.get("product"), "direction": req.get("direction"),
           "edit_of": req.get("from_image") and _entry(run_dir, brand, req["from_image"], "the picture edited")["path"],
           "parent": parent,
           "prompt": (d / "prompt-as-sent.txt").read_text() if (d / "prompt-as-sent.txt").is_file() else None,
           "prompt_skeleton": (run.get("prompt") or {}).get("skeleton"),
           "references": refs,
           "model": {"id": (run.get("model") or {}).get("id"), "vendor_model": pic.get("vendor_model"),
                     "provider": pic.get("provider"), "request_id": pic.get("request_id")},
           "judge": json.loads((d / "check.json").read_text()) if (d / "check.json").is_file() else None,
           "held": held or run.get("held") or None, "error": error}
    (d / "record.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    return str((d / "record.json").relative_to(run_dir))


def read(run_dir, rel):
    if not rel:                 # a picture with no record (a proof photo): None, so callers say why, never a TypeError
        return None
    f = Path(run_dir) / rel
    return json.loads(f.read_text()) if f.is_file() else None


def mirror(brand, run_dir, path):
    """LD-75 (design pictures to Drive): one made picture onto the run's Drive mirror, Shared Assets/runs/
    email-production/<brand>/<label>/media/<name>, under the name the layout uses ("run:media/" + name), so look.py's
    run: fallback (LD-34 (run pictures from Drive)) finds it on any other Mac. Through gdrive-creator's reach as
    look.reach() finds it, never ../drive_reach.py (look.py says why). Returns put's (how, placed, note); a failed
    put is printed by name and never sinks the email; SystemExit (no package, no key) stays loud."""
    import look as L
    run_dir = Path(run_dir)
    path = Path(path)
    f = run_dir / "media" / path.name
    f = f if f.is_file() else path                 # the exact file the layout names, else the one given
    parts = ["runs", "email-production", brand, run_dir.name, "media"]
    try:
        how, placed, note = L.reach().put([f], parts)
    except Exception as e:  # noqa: BLE001 -- named below, never silent
        how, placed, note = "none", [], "%s: %s" % (type(e).__name__, e)
    if placed and not note:
        print("   drive: %s" % placed[0])
    else:
        print("   drive: NOT mirrored — %s" % (note or "nothing placed (route %s)" % how))
    return how, placed, note


def _edit_judge(out, made, r):
    """The edit's own verdict: the engine's check.json under the edit folder, else what the edit returned."""
    res = {}
    f = Path(out) / "engine" / "check.json"
    try:
        if f.is_file():
            res = json.loads(f.read_text())         # the engine's own gates on the generated picture
    except ValueError:
        pass
    fails = [x for y in r.get("rejected") or [] for x in y.get("fails", [])]
    res["edit"] = {"result": "pass" if made else "held",                # the edit's compare judge: asked vs the original
                   "problems": fails or ([r["refused"]] if r.get("refused") else [])}
    return res


def _name(picture):
    """The run's media/ name a `run:` picture names, else None."""
    return picture["photo"].split("run:", 1)[1] if str(picture.get("photo", "")).startswith("run:") else None


# The edit asks for the picture's own shape. 3:2 was missing (the team, 2026-10-22): a 3:2 picture asked for 16:9, the
# model reframed the whole scene, and the judge rightly said everything moved. The image engine serves all six.
ASPECTS = {"4:5": .8, "1:1": 1.0, "3:4": .75, "3:2": 1.5, "16:9": 16 / 9, "9:16": 9 / 16}


def nearest_aspect(w, h):
    return min(ASPECTS.items(), key=lambda kv: abs(kv[1] - w / h))[0]


def edit_inputs(brand, run_dir, picture):
    """What an edit of this picture starts from (remake's reference loading, LD-83 (picture try first) shares it):
    {"old": its record, "current": the picture as a file here, "current_ref": its stored ref or None,
    "references": [(record entry, file here)] — every non-pin reference, "request": the image-edit request without
    change, label and out}. Raises CannotRemake exactly as remake() does, before anything is made."""
    run_dir = Path(run_dir)
    old = read(run_dir, picture.get("record"))
    name = _name(picture)
    if not old or not name:
        raise CannotRemake("this picture has no record to edit from, so it can't be edited from its record")
    R = _refs()

    def why(e):
        if isinstance(e, R.Unportable):
            return "stored as a machine path, not on this Mac"
        if isinstance(e, FileNotFoundError):
            return "not in the repo here"
        return ("%s: %s" % (type(e).__name__, e))[:120]

    missing = []
    cur, cur_ref = run_dir / name, None
    if old.get("file") == name and old.get("file_ref"):
        cur_ref = old["file_ref"]
    if not cur.is_file():
        cur_ref = cur_ref or {"label": "%s/%s" % (_folder(brand, run_dir), name)}   # where mirror() (LD-75) put it
        try:
            cur = Path(R.local(cur_ref))
        except (Exception, SystemExit) as e:  # noqa: BLE001 -- named below, never silent
            missing.append("%s: the picture itself — %s" % (cur_ref["label"], why(e)))
    refs = []
    for r in old.get("references") or []:
        if "pin" in (r.get("kind") or "").lower():
            continue                            # mood pins never go into an edit (the module's note), by design
        stored = r["ref"] if "ref" in r else r.get("path")      # an old record holds only "path"
        if not stored:
            missing.append("%s: never stored on the Drive (%s)" % (r.get("path"), r.get("not_stored") or "no ref"))
            continue
        try:
            refs.append((r, R.local(stored)))
        except (Exception, SystemExit) as e:  # noqa: BLE001 -- named below, never silent
            missing.append("%s: %s" % (r.get("path") or stored, why(e)))
    if missing:
        raise CannotRemake("this picture can't be remade from its record: %d file%s it was made from can't be read here"
                           % (len(missing), "" if len(missing) == 1 else "s"), missing)
    req = {"brand": brand, "picture": str(cur), "kind": "picture", "purpose": old.get("purpose") or "email-story", "count": 1,
           "references": [str(p) for _, p in refs]}
    if old.get("product"):
        req["product"] = old["product"]
    try:                                       # an edit keeps the picture's own shape (the edit tool defaults to 9:16)
        from PIL import Image
        w, h = Image.open(cur).size
        req["aspect"] = nearest_aspect(w, h)
    except Exception:  # noqa: BLE001
        pass
    return {"old": old, "current": cur, "current_ref": cur_ref, "references": refs, "request": req}


def _next_label(run_dir, old):
    """The next free <base>-v<n> record label beside the old record's."""
    base = old["label"].split("-v")[0]
    n = 2
    while (Path(run_dir) / "media" / "records" / ("%s-v%d" % (base, n))).exists():
        n += 1
    return "%s-v%d" % (base, n)


def _earlier_and_kept(brand, run_dir, inputs):
    """The new record's references: the picture edited, as its earlier version, then every reference kept."""
    cur, cur_ref = inputs["current"], inputs["current_ref"]
    earlier = ({"path": cur_ref["label"], "ref": cur_ref, "kind": "earlier version of this picture"} if cur_ref
               else _entry(run_dir, brand, cur, "earlier version of this picture"))
    kept = [r if "ref" in r else _entry(run_dir, brand, p, r.get("kind") or _kind(p, run_dir)) for r, p in inputs["references"]]
    return earlier, kept


def keep_try(brand, run_dir, picture, made, file_ref, change, section, model, judge, inputs, prompt=None, edit_record=None):
    """LD-83 (picture try first): the record of a try a person added, in remake()'s record shape, so a later remake
    edits from it. `picture` is the picture as it was before the try went in, `made` the placed file under media/,
    `model` {"id": the registry id, "door"}, `judge` the try's verdict as made, `inputs` edit_inputs() on `picture`.
    Writes media/records/<base>-v<n>/record.json and returns its path relative to the run."""
    run_dir = Path(run_dir)
    label = _next_label(run_dir, inputs["old"])
    d = run_dir / "media" / "records" / label
    d.mkdir(parents=True, exist_ok=True)
    earlier, kept = _earlier_and_kept(brand, run_dir, inputs)
    old = inputs["old"]
    rec = {"label": label, "section": section, "made_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "state": "made", "file": "media/" + Path(made).name, "file_ref": file_ref,
           "purpose": old.get("purpose"), "product": old.get("product"),
           "direction": change, "edit_of": _name(picture), "parent": picture.get("record"),
           "prompt": prompt, "prompt_skeleton": "tools/image-edit (one change, the rest kept)",
           "references": [earlier] + kept,
           "model": dict(model), "edit_record": edit_record, "judge": judge, "held": None, "error": None}
    (d / "record.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    return str((d / "record.json").relative_to(run_dir))


def remake(brand, run_dir, picture, change, section, IP=None):
    """One change to a made picture, from its record, through the picture-edit tool (tools/image-edit): the
    current picture goes in as the thing to edit, with the same real references (no mood pins), and the judge checks
    the change and that nothing else moved. Returns the new picture fields, or raises with the reason.

    LD-81 (portable picture records): the current picture is the run's media/ file when this Mac has it, else the
    record's file_ref, else what mirror() put on the run's Drive; every reference is read through refs.local(). One
    that cannot be read is never dropped: CannotRemake names each, with the offer, before anything is made."""
    import sys
    run_dir = Path(run_dir)
    inputs = edit_inputs(brand, run_dir, picture)
    old, name = inputs["old"], _name(picture)
    label = _next_label(run_dir, old)
    d = run_dir / "media" / "records" / label
    d.mkdir(parents=True, exist_ok=True)
    ie = Path(__file__).resolve().parents[2] / "image-edit"
    if str(ie) not in sys.path:
        sys.path.append(str(ie))
    import image_edit as RE
    req = dict(inputs["request"], change=change, label=label, out=str(d / "edit"))
    r = RE.edit(req)
    got = (r.get("delivered") or [{}])[0].get("file")
    made = file_ref = None
    if got:
        src = Path(got) if Path(got).is_absolute() else Path(__file__).resolve().parents[3] / got
        made = run_dir / "media" / ("%s-01%s" % (label, src.suffix or ".png"))
        shutil.copy2(src, made)
        file_ref, _ = _store(run_dir, brand, made)   # LD-75's mirror and LD-81's ref in one put: the run's Drive media/<name>
        if file_ref:
            print("   drive: %s" % file_ref["label"])
    earlier, kept = _earlier_and_kept(brand, run_dir, inputs)
    try:
        edit_record = str((Path(r["out"]) / "edit.json").relative_to(run_dir)) if r.get("out") else None
    except ValueError:
        edit_record = None
    rec = {"label": label, "section": section, "made_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "state": "made" if made else "refused" if r.get("refused") else "held",
           "file": ("media/" + made.name) if made else None, "file_ref": file_ref,
           "purpose": old.get("purpose"), "product": old.get("product"),
           "direction": change, "edit_of": name, "parent": picture.get("record"),
           "prompt": r.get("instruction"), "prompt_skeleton": "tools/image-edit (one change, the rest kept)",
           "references": [earlier] + kept,
           "model": {"id": r.get("model") or "image-edit"}, "edit_record": edit_record,
           "judge": _edit_judge(d / "edit", made, r),
           "held": None if made else (r.get("rejected") or r.get("refused")), "error": r.get("refused")}
    (d / "record.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    rel = str((d / "record.json").relative_to(run_dir))
    if not made:
        why = [x for v in rec["judge"].values() if isinstance(v, dict) for x in v.get("problems") or []]
        raise RuntimeError("the edit was held: %s (record %s)" % ("; ".join(why)[:300] or r.get("refused") or "no reason given", rel))
    return {"photo": "run:media/" + made.name, "record": rel, "source": "made"}
