"""The request in, the edited picture out — judged against the reference.

    import image_edit as RE
    RE.edit({"brand": "…", "picture": "…/p152-01.png",
             "change": "the tube is in her left hand, not her right"})
    RE.edit({"brand": "…", "picture": "…", "fix": "logo"})
    RE.edit({"brand": "…", "picture": "…", "fix": "text",
             "args": {"was": "SAALE", "now": "SALE"}})
    RE.vary({"brand": "…", "baseline": "…/p152-01.png",
             "variations": [{"id": "headline", "args": {"headline": "…"}},
                            {"id": "person",   "args": {"who": "woman in her fifties"}}]})

One request shape. A field nothing here names is REFUSED, not ignored.

    brand       required   a folder under brands/
    picture     required   the reference — a file on this machine (`baseline` for vary)
    region      optional   left,top,right,bottom as PERCENTAGES — the only part of the
                           picture that may differ. Everything outside it is put back
                           from the original, pixel for pixel, so it cannot drift
                           (the tube label redrew itself on every roll, 2026-09-22)
    change      one of     free words: the ONE thing to change
    fix         one of     a row in library/fixes — `args` fills its slots
    args        optional   the slots a fix or variation needs
    kind        optional   which default split: picture (default) · slide · frame-A/B/C
    keep        optional   extra things that must not move, in words
    elements    optional   element ids the change is about (their bank reference rides along)
    product     optional   a product the brand declares (its photo rides along)
    purpose     optional   image-production purpose, default `ad`
    aspect      optional   default: 9:16 for a 4:5 or 9:16 reference (assets are
                           9:16 only — a 4:5 reference is the content and the
                           scene is extended above and below); else the
                           reference's own frame
    count       optional   rolls per edit, default 1
    label       optional   the run label; default from the picture's name
    out         optional   default runs/image-edit/<brand>/<label>/
    dry_run     optional   resolve and print, spend nothing
    model       optional   force one image model; it still has to be a declared row
    references  optional   more reference pictures on this machine — the real logo file,
                           the product photo — reproduced exactly, never described
    words       optional   the words the result carries, verbatim (a list of lines) — a
                           carousel slide's own words. Added to the change as
                           `the words change to "…"`; the guard counts the change
                           as written, not the words (kind `slide` lists the words as
                           what may change)

The generation is `tools/image-production`'s (`from_image` → the edit
model, the keep-everything clause, its own one-picture judge, the gates, the
Drive mirror). This file adds what that engine does not know: the delta
discipline, the fix and variation libraries, the two-picture judge, and the
rule that a result is a NEW version filed beside the record — the original
is never written to.
"""
import json
import re
import shutil
import struct
from datetime import datetime
import sys
from pathlib import Path

from . import compare as CMP, discipline as D, paths as P

REQUIRED = ("brand", "picture")
OPTIONAL = ("change", "fix", "args", "kind", "keep", "elements", "product", "purpose",
            "aspect", "count", "label", "out", "dry_run", "checks", "model", "references",
            "region", "words")
FIELDS = set(REQUIRED) | set(OPTIONAL)


class BadRequest(SystemExit):
    pass


# ------------------------------------------------------------------ libraries

def _latest(prefix, folder=None):
    folder = Path(folder or P.home() / "library")
    best, best_v = None, -1
    for f in folder.glob(f"{prefix}-v*-damon.json"):
        try:
            v = int(f.name.split("-v")[1].split("-")[0])
        except ValueError:
            continue
        if v > best_v:
            best, best_v = f, v
    if best is None:
        raise BadRequest(f"no {prefix} library under {folder}")
    return best


def fixes(folder=None):
    p = _latest("fixes", folder)
    return {r["id"]: r for r in json.loads(p.read_text())["fixes"]}, p


def variations(folder=None):
    p = _latest("variations", folder)
    return {r["id"]: r for r in json.loads(p.read_text())["variations"]}, p


def fill(text, args):
    """A slot the row needs and the caller did not give is refused by name —
    a `{headline}` left in the prompt is a picture with a headline that
    literally says {headline}."""
    out = text
    for k, v in (args or {}).items():
        out = out.replace("{" + k + "}", str(v))
    if "{" in out and "}" in out:
        left = sorted({s.split("}")[0] for s in out.split("{")[1:]})
        raise BadRequest(f"the row needs: {', '.join(left)} — pass them in `args`")
    return out


# ----------------------------------------------------------------- the frame

def dims(path):
    """(w, h) read off the file header — PNG and JPEG, no library. None when
    the file is neither; the purpose's default frame is used then."""
    b = Path(path).read_bytes()
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", b[16:24])
        return w, h
    if b[:2] == b"\xff\xd8":
        i = 2
        while i < len(b) - 9:
            if b[i] != 0xFF:
                i += 1; continue
            marker = b[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return w, h
            seg = struct.unpack(">H", b[i + 2:i + 4])[0]
            i += 2 + seg
    return None


def deliver_frame(picture):
    """The frame the result leaves in. the owner, 2026-09-22: assets are generated
    at 9:16 only, faces and words inside a centred 4:5 zone. A 4:5 or 9:16
    reference leaves at 9:16 — a 4:5 one is the content, and the model extends
    the scene above and below it. Any other frame (a sheet, a square) is
    edited as it is. Returns "9:16" or None."""
    wh = dims(picture)
    if not wh:
        return None
    w, h = wh
    if abs(h / w - 1.25) < 0.02 or abs(h / w - 16 / 9) < 0.03:
        return "9:16"
    return None


def nearest_aspect(wh, table):
    """The declared aspect closest to the picture's own. An edit keeps the
    frame it was given; the engine measures the result against it."""
    if not wh or not table:
        return None
    w, h = wh
    got = h / w
    best = min(table.items(), key=lambda kv: abs(kv[1]["h"] / kv[1]["w"] - got))
    return best[0]


# --------------------------------------------------------------- the request

def resolve(req, fix_table=None, var_table=None, split_table=None):
    """Everything one edit means, worked out without spending anything."""
    unknown = sorted(set(req) - FIELDS - {k for k in req if k.startswith("_")})
    if unknown:
        raise BadRequest(f"the request carries fields this component does not take: "
                         f"{', '.join(unknown)} — the contract is: {', '.join(sorted(FIELDS))}")
    missing = [f for f in REQUIRED if not req.get(f)]
    if missing:
        raise BadRequest(f"the request is missing: {', '.join(missing)}")
    if bool(req.get("change")) == bool(req.get("fix")):
        raise BadRequest("give exactly one of `change` (free words) or `fix` (a library row)")

    pic = Path(req["picture"]).expanduser()
    if not pic.is_file():
        raise BadRequest(f"{pic} is not a file on this machine — the reference must be here")

    kind = req.get("kind") or "picture"
    split = D.split_for(kind, None, split_table)
    args = dict(req.get("args") or {})
    refs, checks, row = [], list(req.get("checks") or []), None

    if req.get("fix"):
        table = fix_table if fix_table is not None else fixes()[0]
        row = table.get(req["fix"])
        if not row:
            raise BadRequest(f"`{req['fix']}` is not a fix — have: {', '.join(sorted(table))}")
        if row.get("status") not in ("draft", "approved"):
            raise BadRequest(f"fix `{row.get('id', req['fix'])}` is {row.get('status') or 'without a status'}"
                             f" — only a draft or approved fix runs")
        need =[n for n in row.get("needs", []) if n not in args]
        if need:
            raise BadRequest(f"fix `{row['id']}` needs: {', '.join(need)} — pass them in `args`")
        change = fill(row["delta"], args)
        extra_keep = [fill(k, args) for k in row.get("keep", [])]
        checks += [fill(c, args) for c in row.get("checks", [])]
        refs = list(row.get("references", []))
    else:
        change = req["change"].strip()
        extra_keep = []
        refs = list(req.get("_brand_refs") or [])

    region = req.get("region")
    if region is not None:
        region = [float(x) for x in (region.split(",") if isinstance(region, str) else region)]
        if len(region) != 4 or not all(0 <= x <= 100 for x in region) or region[0] >= region[2] or region[1] >= region[3]:
            raise BadRequest("region is left,top,right,bottom as percentages of the picture, "
                             "left<right and top<bottom — e.g. 4,10,96,34 for a headline band")

    words = [str(w) for w in (req.get("words") or []) if str(w).strip()]
    # The guard reads the change as written: the words are the slide's own
    # swappable line (splits.json `slide`), not a second alteration.
    guarded = change
    if words:
        change = change.rstrip().rstrip(".") + "; the words change to " + \
            " / ".join(f'"{w}"' for w in words)
    if region:
        # A masked edit: the words describe what goes IN the rectangle. The
        # mask holds everything else, so the keep clause would only tell the
        # model to reproduce what is already there — and it did (2026-09-22).
        text = D.region_instruction(change)
    else:
        text = D.instruction(split["keep"], change, req.get("elements"),
                             extra_keep + list(req.get("keep") or []))
    refused = D.guard(guarded, text)

    label = req.get("label") or f"{pic.stem}--{(req.get('fix') or 'edit')}"
    out = Path(req["out"]) if req.get("out") else P.runs(req["brand"], label)
    return {
        "brand": req["brand"], "picture": str(pic), "kind": kind, "split": split,
        "fix": row["id"] if row else None, "args": args,
        "asked": change, "instruction": text, "chars": len(text),
        "changes": D.count_changes(change), "refused": refused,
        "extra_keep": extra_keep, "checks": checks, "brand_refs": refs,
        "product": req.get("product"), "purpose": req.get("purpose") or "ad",
        "aspect": req.get("aspect"), "count": int(req.get("count") or 1),
        "label": label, "out": str(out), "model": req.get("model"), "region": region,
        "references": [str(Path(x).expanduser()) for x in (req.get("references") or [])],
    }


def _restore_outside(original, result, region):
    """Put the original back everywhere outside the region, at the result's own
    size. Returns a one-line note, or why it could not be done."""
    try:
        from PIL import Image
    except ImportError:
        return "Pillow absent — the region could not be enforced"
    with Image.open(result) as res, Image.open(original) as orig:
        res = res.convert("RGB")
        w, h = res.size
        src = orig.convert("RGB").resize((w, h), Image.LANCZOS)
        l, t, rr, b = region
        box = (int(round(l / 100 * w)), int(round(t / 100 * h)),
               int(round(rr / 100 * w)), int(round(b / 100 * h)))
        keep = src.copy()
        keep.paste(res.crop(box), (box[0], box[1]))
        keep.save(result)
    return f"only {box[0]},{box[1]}–{box[2]},{box[3]} of {w}x{h} could change; the rest is the original"


def _version(out, stem):
    """The next version number for this stem under this run root — a result
    is a new version beside the record, never the original overwritten."""
    root = out.parent
    n = 0
    if root.is_dir():
        for f in root.rglob(f"{stem}--*-v*.png"):
            # `-v1` and a multi-roll `-v1-01` are both version 1
            m = re.search(r"-v(\d+)(?:-\d{2})?$", f.stem)
            if m:
                n = max(n, int(m.group(1)))
    return n + 1


def _brand_refs(ip, brand, wanted, product):
    """Which brand files ride along: the logo for a logo fix, the product
    photo for a product fix. Read through the engine's own context so the
    lookup rules are one place."""
    if not wanted:
        return [], []
    ctx = ip.context.build({"brand": brand, "purpose": "ad", "_purpose": ip.purposes()["ad"],
                            "direction": "", "out": "", "product": product,
                            "assets": False, "people": False}, library=None)
    refs, notes = [], []
    for w in wanted:
        if w == "logo":
            if ctx.get("logo"):
                refs.append(ctx["logo"][0])
            else:
                where = Path(ip.paths.brand(brand)["identity"])
                try:
                    where = where.relative_to(P.repo()).as_posix()
                except ValueError:
                    pass
                notes.append(f"{where} holds no logo file (nor does the Drive mirror's logos/)"
                             " — the logo fix has nothing to swap in")
        elif w == "product":
            photo = ctx["product"].get("photo")
            if photo and ctx["product"].get("photo_on_machine"):
                refs.append(photo)
            else:
                notes.append("the product's photo is not a file on this machine — name `product` "
                             "on the request, and its picture must be in the brand")
    return refs, notes


def _file_qc_round(out, kept, rejected):
    """File the compare judge's verdicts as one QC round (qc-log/ beside the run)."""
    try:
        here = Path(__file__).resolve()
        comp = next(p for p in here.parents if (p / "components" / "quality-checks" / "marketing_chain_checks").is_dir())
        q = str(comp / "components" / "quality-checks")
        if q not in sys.path:
            sys.path.append(q)
        from marketing_chain_checks import qc_log
        f = {k["name"]: {"ok": True, "severity": "none"} for k in kept}
        f.update({k["name"]: {"ok": False, "severity": "FIX", "problems": k.get("fails") or []} for k in rejected})
        qc_log.add(out, "image-edit · edit", "compare judge", f, method="each result against the reference and the one change asked")
    except Exception as e:
        print(f"  QC: round not filed ({type(e).__name__})")


def _file(out, r):
    """The record, on both names it is read by.

    `edit.json` is this machine's own record and its readers depend on it
    (tools/image-teardown/tools/variations.py `_state`, once
    bulk_variations.py; image-teardown/tools/carousel.py; this component's
    tests), so it keeps its name. `run.json` is
    what run_kit.index reads to know a run happened at all — without it this
    machine showed up as fourteen runs with no record, which reads as
    stateless. Same folder, same moment, smallest shape the index consumes.
    """
    out.mkdir(parents=True, exist_ok=True)
    (out / "edit.json").write_text(json.dumps(r, indent=1))
    (out / "run.json").write_text(json.dumps(
        {"machine": P.TOOL, "brand": r.get("brand"), "label": r.get("label"),
         "state": r.get("state"), "opened": r.get("at")}, indent=1))


def _learnings(r, load=None):
    """The approval-page learnings, appended to the instruction INSIDE the
    700-char band (SI-144, image-edit#20). `prompt_block` is the header plus
    up to 8 digest lines, newest first; the header and as many lines, in that
    order, as `D.fits` allows are kept — not even the header and one line
    fitting appends nothing. `load` is a seam returning the learnings module;
    by default components/meta-upload/learnings.py, by path (that folder's
    module names would shadow ours on sys.path). A failure is said, once, on
    stderr and in `r["learnings"]`; the edit goes on without it."""
    try:
        if load is None:
            import importlib.util as _iu
            _ls = _iu.spec_from_file_location("meta_learnings", Path(__file__).resolve().parents[3] / "components" / "meta-upload" / "learnings.py")
            _L = _iu.module_from_spec(_ls); _ls.loader.exec_module(_L)
        else:
            _L = load()
        block = _L.prompt_block("image-edit", 7, r.get("brand"))
        if not block:
            return
        lead = block[:len(block) - len(block.lstrip("\n"))]
        rows = block.strip("\n").split("\n")
        head, lines = lead + rows[0] + "\n", rows[1:]
        base = r["instruction"] or ""
        kept = 0
        while kept < len(lines) and D.fits(base, head + "\n".join(lines[:kept + 1]) + "\n"):
            kept += 1
        text = base + (head + "\n".join(lines[:kept]) + "\n" if kept else "")
        r["instruction"], r["chars"] = text, len(text)
        r["learnings"] = {"kept": kept, "dropped": len(lines) - kept}
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        print(f"learnings hook failed: {err} — instruction sent without it", file=sys.stderr, flush=True)
        r["learnings"] = {"error": err}


def edit(req, transport=None, judge_caller=None, compare_caller=None, mirror=True,
         fix_table=None, var_table=None, split_table=None, library=None):
    """One edit: the instruction, the engine, both judges, the record.
    Returns the record dict. Writes only under `out` and the Drive mirror."""
    r = resolve(req, fix_table, var_table, split_table)
    out = Path(r["out"])
    out.mkdir(parents=True, exist_ok=True)
    r["at"] = datetime.now().isoformat(timespec="seconds")
    r["version"] = _version(out, Path(r["picture"]).stem)

    if r["refused"]:
        r["state"] = "refused"
        _file(out, r)
        return r

    ip = P.image_production()
    refs, notes = _brand_refs(ip, r["brand"], r["brand_refs"], r["product"])
    r["notes"] = notes
    if r["brand_refs"] and not refs:
        r["state"] = "refused"
        r["refused"] = "; ".join(notes)
        _file(out, r)
        return r

    content = r["picture"]
    aspect = r["aspect"] or deliver_frame(content) or nearest_aspect(dims(content), ip.route.aspects())
    # A 4:5 or 9:16 reference leaves at 9:16 — the image engine edits the
    # content at 4:5 and finishes it: content taped down, strips painted
    # (image_production.providers.finish_9x16, the owner 2026-09-22).
    # >>> APPROVAL-PAGE LEARNINGS HOOK (components/meta-upload/learnings.py) — adds nothing unless learnings-hooks.json turns "image-edit" on
    _learnings(r)
    # <<< APPROVAL-PAGE LEARNINGS HOOK
    ip_req = {"brand": r["brand"], "purpose": r["purpose"], "direction": r["instruction"],
              "out": str(out / "engine"), "from_image": content, "count": r["count"],
              "label": r["label"], "assets": False}
    if aspect:
        ip_req["aspect"] = aspect
    refs = refs + [x for x in r.get("references", []) if x not in refs]
    if refs:
        ip_req["references"] = refs
    if r["product"]:
        ip_req["product"] = r["product"]
    if r.get("model"):
        ip_req["model"] = r["model"]
    if r["region"]:
        # The model may paint only inside the rectangle — the shared engine
        # does it with a mask (providers.edit_in_region), which is the one
        # thing that held on 2026-09-22. The forced model is dropped: a
        # masked edit goes through the edit door whatever else was named.
        ip_req["region"] = r["region"]
        ip_req.pop("model", None)
    r["engine_request"] = {k: v for k, v in ip_req.items()}

    if req.get("dry_run"):
        r["state"] = "dry"
        _file(out, r)
        return r

    made = ip.make(ip_req, library=library, transport=transport, judge_caller=judge_caller,
                   mirror=False)
    r["engine"] = {"model": made["model"], "prompt": made["prompt"],
                   "pictures": made["pictures"], "held": made["held"]}

    stem = Path(r["picture"]).stem
    kept, rejected = [], []
    rows = {row["file"]: row for row in made["pictures"] if row.get("file")}
    for i, p in enumerate(made["delivered"], 1):
        seen_as = rows.get(p, {}).get("content") or p
        if r["region"]:
            # BELT AND BRACES. The engine masked the call so the model could
            # only paint inside the rectangle; this puts the original back
            # outside it anyway, so "nothing else moved" is a fact about the
            # file rather than a hope about the model.
            note = _restore_outside(r["picture"], p, r["region"])
            r.setdefault("region_notes", []).append(note)
            if seen_as != p:
                _restore_outside(r["picture"], seen_as, r["region"])
        verdict, fails, tests, raw = CMP.compare(content, seen_as, r["asked"], r["checks"],
                                                 caller=compare_caller)
        name = f"{stem}--{r['fix'] or 'edit'}-v{r['version']}" + (f"-{i:02d}" if r["count"] > 1 else "") + ".png"
        row = {"name": name, "from": p, "content": seen_as, "delivered_at": aspect,
               "verdict": verdict, "fails": fails, "tests": tests}
        # A file already at the destination is never copied over: the row is
        # not delivered, it is held with the reason.
        if verdict == "pass" and (out / name).exists():
            row["verdict"], row["fails"] = "reject", [f"destination exists: {name} — never overwritten"]
            verdict, fails = row["verdict"], row["fails"]
        if verdict == "pass":
            shutil.copy2(p, out / name)
            row["file"] = str(out / name)
            kept.append(row)
        else:
            rej = out / "rejected"
            rej.mkdir(exist_ok=True)
            if (rej / name).exists():
                fails.append(f"destination exists: rejected/{name} — never overwritten")
                row["file"] = str(p)
            else:
                shutil.copy2(p, rej / name)
                (rej / f"{Path(name).stem}-why.md").write_text(
                    "# " + name + " — did not hold the reference\n\n" +
                    "\n".join(f"- {f}" for f in fails) +
                    "\n\nAn edit that moved something else is a delta to narrow, not a picture to patch.\n"
                    + (f"\n<details><summary>judge, raw</summary>\n\n```\n{raw.strip()}\n```\n</details>\n" if raw else ""))
                row["file"] = str(rej / name)
            rejected.append(row)
    r["delivered"], r["rejected"] = kept, rejected
    r["state"] = "filed" if kept else "held"
    # THE CREATIVE QC LOOP (2026-10-02): the compare judge above is this stage's
    # reviewer; every round is filed beside the run
    _file_qc_round(out, kept, rejected)

    if mirror and kept:
        copied, note = ip.filing.mirror([Path(k["file"]) for k in kept], r["brand"], r["label"],
                                        tool=P.TOOL)
        r["drive"] = {"copied": copied, "note": note}
    _file(out, r)
    return r


# ---------------------------------------------------------------- variations

VARY_REQUIRED = ("brand", "baseline", "variations")
VARY_OPTIONAL = ("kind", "keep", "product", "purpose", "aspect", "count", "label", "out", "dry_run", "model", "references", "region")


def vary(req, **kw):
    """N variations off one baseline: one edit per row, each judged against
    the baseline. Returns the set's record; each variation is its own edit
    record under `<out>/<variation id>/`."""
    unknown = sorted(set(req) - set(VARY_REQUIRED) - set(VARY_OPTIONAL))
    if unknown:
        raise BadRequest(f"vary does not take: {', '.join(unknown)}")
    missing = [f for f in VARY_REQUIRED if not req.get(f)]
    if missing:
        raise BadRequest(f"vary is missing: {', '.join(missing)}")
    table = kw.pop("var_table", None)
    table = table if table is not None else variations()[0]
    base = Path(req["baseline"]).expanduser()
    label = req.get("label") or f"{base.stem}--variations"
    root = Path(req["out"]) if req.get("out") else P.runs(req["brand"], label)
    root.mkdir(parents=True, exist_ok=True)

    rows, results = [], []
    for v in req["variations"]:
        v = {"id": v} if isinstance(v, str) else dict(v)
        row = table.get(v.get("id"))
        if not row:
            raise BadRequest(f"`{v.get('id')}` is not a variation — have: {', '.join(sorted(table))}")
        args = dict(v.get("args") or {})
        need = [n for n in row.get("needs", []) if n not in args]
        if need:
            raise BadRequest(f"variation `{row['id']}` needs: {', '.join(need)} — pass them in `args`")
        change = fill(row["delta"], args)
        one = {"brand": req["brand"], "picture": str(base), "change": change,
               "kind": req.get("kind") or "picture",
               "keep": [fill(k, args) for k in row.get("keep", [])] + list(req.get("keep") or []),
               "checks": [fill(c, args) for c in row.get("checks", [])],
               "label": f"{label}--{row['id']}", "out": str(root / row["id"]),
               "count": req.get("count") or 1, "dry_run": req.get("dry_run")}
        for k in ("product", "purpose", "aspect", "model", "references", "region"):
            if req.get(k):
                one[k] = req[k]
        if "product" in row.get("references", []) and not req.get("product"):
            raise BadRequest(f"variation `{row['id']}` swaps the product — name `product` on the request")
        if row.get("references"):
            one["_brand_refs"] = row["references"]
        rec = edit(one, split_table=kw.get("split_table"), **{k: x for k, x in kw.items() if k != "split_table"})
        rows.append({"id": row["id"], "args": args, "state": rec["state"],
                     "delivered": [d["file"] for d in rec.get("delivered", [])],
                     "rejected": [d["file"] for d in rec.get("rejected", [])],
                     "refused": rec.get("refused"), "record": str(Path(rec["out"]) / "edit.json")})
        results.append(rec)
    summary = {"brand": req["brand"], "baseline": str(base), "label": label, "out": str(root),
               "at": datetime.now().isoformat(timespec="seconds"), "variations": rows,
               "delivered": sum(len(r["delivered"]) for r in rows),
               "rejected": sum(len(r["rejected"]) for r in rows),
               "refused": sum(1 for r in rows if r["refused"])}
    _file_batch(root, summary, "variations.json")
    return summary


def _file_batch(root, summary, name):
    """A batch's own record, at the run-label folder the index actually reads.

    vary() and sequence() each write one summary beside a folder of edits.
    The index looks only at run-label depth and never descends, so without a
    run.json here the whole batch is invisible while its children are filed
    one level down. `state` is what the batch amounted to, not any one edit's.
    """
    (root / name).write_text(json.dumps(summary, indent=1))
    state = ("filed" if summary.get("delivered")
             else "refused" if summary.get("refused") else "held")
    (root / "run.json").write_text(json.dumps(
        {"machine": P.TOOL, "brand": summary.get("brand"), "label": summary.get("label"),
         "state": state, "opened": summary.get("at")}, indent=1))


# ------------------------------------------------------------------ sequences

SEQ_REQUIRED = ("brand", "slide_one", "deltas")
SEQ_OPTIONAL = ("keep", "product", "purpose", "aspect", "count", "label", "out", "dry_run",
                "model", "references", "region")


def deltas_from(source):
    """The slide deltas — the AI sequence brief's own `json` block (a list of
    {slide, change, keep, type}) read out of the brief file, or a .json file
    holding that list. Refused, never guessed, when neither is there."""
    p = Path(source).expanduser()
    if not p.is_file():
        raise BadRequest(f"{p} is not a file on this machine")
    text = p.read_text()
    if p.suffix.lower() == ".json":
        data = json.loads(text)
        rows = data.get("slides") if isinstance(data, dict) else data
    else:
        rows = None
        for m in re.finditer(r"```json\s*(.*?)```", text, re.S):
            try:
                cand = json.loads(m.group(1))
            except ValueError:
                continue
            if isinstance(cand, list) and cand and all(isinstance(x, dict) and "slide" in x and "change" in x for x in cand):
                rows = cand
                break
        if rows is None:
            raise BadRequest(f"no slide-deltas block in {p.name} — the AI sequence brief emits one "
                             f"(a json list of {{slide, change, keep, type}})")
    rows = sorted(rows, key=lambda r: int(r["slide"]))
    for r in rows:
        if int(r["slide"]) < 2:
            raise BadRequest("slide one is the plate, not a delta — deltas start at slide 2")
        if not str(r.get("change", "")).strip():
            raise BadRequest(f"slide {r['slide']} has no change")
    return rows


# What every slide of a sequence shares with slide one — the compare judge's
# extra test for a slide (sequence() here, the carousel road in image-teardown).
THREAD = ("the same person and face", "the same product, held the same way",
          "the same palette", "the same framing and camera distance")


def thread_check(n):
    return (f"Slide {n} still belongs to the same sequence as IMAGE 1: " + ", ".join(THREAD)
            + ". Only what the change names is different.")


def sequence(req, **kw):
    """A sequence off one plate: slide one is the reference for every later
    slide; each is ONE delta, judged against slide one for the thread, and
    finished like any other asset. Records under `<out>/slide-NN/`."""
    unknown = sorted(set(req) - set(SEQ_REQUIRED) - set(SEQ_OPTIONAL))
    if unknown:
        raise BadRequest(f"sequence does not take: {', '.join(unknown)}")
    missing = [f for f in SEQ_REQUIRED if not req.get(f)]
    if missing:
        raise BadRequest(f"sequence is missing: {', '.join(missing)}")
    one = Path(req["slide_one"]).expanduser()
    rows = req["deltas"] if isinstance(req["deltas"], list) else deltas_from(req["deltas"])
    label = req.get("label") or f"{one.stem}--sequence"
    root = Path(req["out"]) if req.get("out") else P.runs(req["brand"], label)
    root.mkdir(parents=True, exist_ok=True)

    results, slides = [], []
    for r in rows:
        n = int(r["slide"])
        keep = list(r.get("keep") or []) + list(req.get("keep") or [])
        one_req = {"brand": req["brand"], "picture": str(one), "change": str(r["change"]).strip(),
                   "kind": "slide", "keep": keep,
                   "checks": [thread_check(n)],
                   "label": f"{label}--slide-{n:02d}", "out": str(root / f"slide-{n:02d}"),
                   "count": req.get("count") or 1, "dry_run": req.get("dry_run")}
        for k in ("product", "purpose", "aspect", "model", "references", "region"):
            if req.get(k):
                one_req[k] = req[k]
        rec = edit(one_req, **kw)
        slides.append({"slide": n, "change": one_req["change"], "state": rec["state"],
                       "delivered": [d["file"] for d in rec.get("delivered", [])],
                       "rejected": [d["file"] for d in rec.get("rejected", [])],
                       "refused": rec.get("refused"), "type": r.get("type"),
                       "record": str(Path(rec["out"]) / "edit.json")})
        results.append(rec)
    summary = {"brand": req["brand"], "slide_one": str(one), "label": label, "out": str(root),
               "at": datetime.now().isoformat(timespec="seconds"), "slides": slides,
               "delivered": sum(len(s["delivered"]) for s in slides),
               "rejected": sum(len(s["rejected"]) for s in slides),
               "refused": sum(1 for s in slides if s["refused"]),
               "note": "slide one is the plate as given; type per slide is carried in `type` for the compositor"}
    _file_batch(root, summary, "sequence.json")
    return summary
