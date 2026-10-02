"""The request in, the edited picture out — judged against the reference.

    import image_edit as RE
    RE.edit({"brand": "…", "picture": "…/draft-01.png",
             "change": "the tube is in her left hand, not her right"})
    RE.edit({"brand": "…", "picture": "…", "fix": "logo"})
    RE.vary({"brand": "…", "baseline": "…/draft-01.png",
             "variations": [{"id": "headline", "args": {"headline": "…"}},
                            {"id": "person",   "args": {"who": "woman in her fifties"}}]})
    RE.ingest("runs/image-edit/<brand>/<label>", {"<slug>": "…/result.png"})

Two halves, the same shape as image-production's plates (`plates.py prepare`
/ `ingest`): the pictures are made on **Higgsfield**, whose image models are
reached by the agent in the session (Higgsfield Supercomputer, or Claude Code
with the Higgsfield connector) — a script cannot call them. So:

    edit / vary / sequence   resolve the ONE change, refuse a bad one, write
                             job.json: the instruction exactly as it is sent,
                             the model, the frame, the references in order,
                             and the judge's prompt. Nothing is spent.
    (the session)            generates each job on Higgsfield and writes
                             results.json: {slug: picture}
    ingest                   both pictures to the two-picture judge, the
                             result filed as a NEW version, or held under
                             rejected/ with the reason

A caller that can make the picture itself passes `maker(job) -> [paths]` and
the two halves run as one; the tests do exactly that.

One request shape. A field nothing here names is REFUSED, not ignored.

    brand       required   a folder under brands/
    picture     required   the reference — a file on this machine (`baseline` for vary)
    change      one of     free words: the ONE thing to change
    fix         one of     a row in library/fixes — `args` fills its slots
    args        optional   the slots a fix or variation needs
    region      optional   left,top,right,bottom as PERCENTAGES — the only part of the
                           picture that may differ. Everything outside it is put back
                           from the original, pixel for pixel, when the result comes in
    kind        optional   which default split: picture (default) · slide · frame-A/B/C
    keep        optional   extra things that must not move, in words
    elements    optional   element ids the change is about (<<<id>>> rides along)
    product     optional   a product the brand declares (its photo rides along)
    aspect      optional   the frame to edit at; default read off the reference
    count       optional   rolls per edit, default 1
    label       optional   the run label; default from the picture's name
    out         optional   default runs/image-edit/<brand>/<label>/
    dry_run     optional   resolve and print, write the record, no job
    model       optional   a different Higgsfield model for this one edit
    references  optional   more reference pictures on this machine — the real logo file,
                           the product photo — reproduced exactly, never described
    words       optional   the words the result carries, verbatim (a list of lines) — a
                           carousel slide's own words
    purpose     optional   kept for parity with image-production; recorded only

The rule this file adds to the discipline: a result is a NEW version filed
beside the record — the original is never written to.
"""
import json
import re
import shutil
import struct
from datetime import datetime
from pathlib import Path

from . import compare as CMP, discipline as D, paths as P

REQUIRED = ("brand", "picture")
OPTIONAL = ("change", "fix", "args", "kind", "keep", "elements", "product", "purpose",
            "aspect", "count", "label", "out", "dry_run", "checks", "model", "references",
            "region", "words")
FIELDS = set(REQUIRED) | set(OPTIONAL)

# The model the edit runs on — the same one the editing skills name
# (skills/logo-swap.md, avatar-swap.md, element-swap.md), so a skill run in
# Higgsfield and a run of this tool are the same edit. Before a run the agent
# looks for a NEWER version of this same model and uses it; never a different
# maker on its own.
MODEL = {"model": "gpt_image_2_5", "variant": "sunburst", "quality": "high", "resolution": "2k"}

# The frames an edit is sent at. A reference keeps its own frame.
ASPECTS = {k: {"w": w, "h": h} for k, (w, h) in {
    "1:1": (1, 1), "4:5": (4, 5), "9:16": (9, 16), "16:9": (16, 9),
    "2:3": (2, 3), "3:2": (3, 2), "3:4": (3, 4), "4:3": (4, 3)}.items()}


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
    the file is neither."""
    b = Path(path).read_bytes()
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", b[16:24])
        return w, h
    if b[:2] == b"\xff\xd8":
        i = 2
        while i < len(b) - 9:
            if b[i] != 0xFF:
                i += 1
                continue
            marker = b[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return w, h
            seg = struct.unpack(">H", b[i + 2:i + 4])[0]
            i += 2 + seg
    return None


def _is(wh, w, h, tol):
    return bool(wh) and abs(wh[1] / wh[0] - h / w) < tol


def deliver_frame(picture):
    """The frame the result leaves in. Assets are 9:16 only, faces and words
    inside the centred 4:5 zone: a 4:5 or 9:16 reference leaves at 9:16. Any
    other frame (a sheet, a square) is edited as it is. "9:16" or None."""
    wh = dims(picture)
    if _is(wh, 4, 5, 0.02) or _is(wh, 9, 16, 0.03):
        return "9:16"
    return None


def nearest_aspect(wh, table=None):
    """The declared aspect closest to the picture's own. An edit keeps the
    frame it was given."""
    table = table or ASPECTS
    if not wh:
        return None
    got = wh[1] / wh[0]
    return min(table.items(), key=lambda kv: abs(kv[1]["h"] / kv[1]["w"] - got))[0]


def frame_for(picture, asked=None):
    """(aspect to edit at, finish step or None).

    A 4:5 reference is edited AT 4:5 — the content — and then finished to 9:16
    by `skills/resize-9x16.md` (the picture untouched, the background continued
    above and below). Feeding a padded 9:16 back in makes the model read the
    bands as picture (image-production PIPELINE.md §4a). A 9:16 reference is
    edited at 9:16. Anything else keeps its own frame."""
    if asked:
        return asked, None
    wh = dims(picture)
    if _is(wh, 4, 5, 0.02):
        return "4:5", "resize-9x16"
    if _is(wh, 9, 16, 0.03):
        return "9:16", None
    return nearest_aspect(wh), None


# --------------------------------------------------------------- the request

def resolve(req, fix_table=None, var_table=None, split_table=None):
    """Everything one edit means, worked out without spending anything."""
    unknown = sorted(set(req) - FIELDS - {k for k in req if k.startswith("_")})
    if unknown:
        raise BadRequest(f"the request carries fields this tool does not take: "
                         f"{', '.join(unknown)} — the contract is: {', '.join(sorted(FIELDS))}")
    missing = [f for f in REQUIRED if not req.get(f)]
    if missing:
        raise BadRequest(f"the request is missing: {', '.join(missing)}")
    if bool(req.get("change")) == bool(req.get("fix")):
        raise BadRequest("give exactly one of `change` (free words) or `fix` (a library row)")
    if not (P.brands() / req["brand"]).is_dir():
        have = sorted(p.name for p in P.brands().iterdir()
                      if p.is_dir() and not p.name.startswith((".", "_"))) if P.brands().is_dir() else []
        raise BadRequest(f"no brand folder brands/{req['brand']} — have: {', '.join(have) or 'none yet'} "
                         f"(a brand is set up from brands/_TEMPLATE/)")

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
        if row.get("status") == "parked":
            raise BadRequest(f"fix `{row['id']}` is parked, not run — {row.get('what', '')}")
        need = [n for n in row.get("needs", []) if n not in args]
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


def _brand_refs(brand, wanted, product):
    """Which brand files ride along: the logo for a logo fix, the product
    photo for a product fix — found by image-production's own brand paths, so
    the lookup rules live in one place."""
    if not wanted:
        return [], []
    PP = P.production()
    refs, notes = [], []
    for w in wanted:
        if w == "logo":
            b = PP.brand(brand)
            cands = [b["logo_white"], b["logo_dark"]] + sorted(Path(b["identity"]).glob("*logo*.png")) \
                + sorted((Path(b["root"]) / "brand-assets").glob("*logo*.png"))
            hit = next((c for c in cands if Path(c).is_file()), None)
            if hit:
                refs.append(str(hit))
            else:
                notes.append(f"brands/{brand}/brand-identity holds no logo file — the logo fix has "
                             f"nothing to swap in (never let the model draw a logo from memory)")
        elif w == "product":
            if not product:
                notes.append("this swaps the product — name `product` on the request")
                continue
            try:
                photo = PP.product_cutout(brand, product)
            except SystemExit as e:
                notes.append(str(e))
                continue
            if photo and Path(photo).is_file():
                refs.append(str(photo))
            else:
                notes.append(f"the photo for `{product}` is not a file on this machine — it must be "
                             f"in brands/{brand}/products/ (products/images.json `cutout`)")
    return refs, notes


def _version(out, stem):
    """The next version number for this stem under this run root — a result
    is a new version beside the record, never the original overwritten."""
    root = out.parent
    n = 0
    if root.is_dir():
        for f in root.rglob(f"{stem}--*-v*"):
            try:
                n = max(n, int(f.stem.rsplit("-v", 1)[1].split("-")[0]))
            except (IndexError, ValueError):
                pass
        for f in root.rglob("edit.json"):
            try:
                rec = json.loads(f.read_text())
            except ValueError:
                continue
            if Path(rec.get("picture", "")).stem == stem:
                n = max(n, int(rec.get("version") or 0))
    return n + 1


def _file(out, r):
    """The record. `edit.json` is this tool's own; `run.json` is the smallest
    shape a run index reads to know a run happened at all."""
    out.mkdir(parents=True, exist_ok=True)
    (out / "edit.json").write_text(json.dumps(r, indent=1))
    (out / "run.json").write_text(json.dumps(
        {"machine": P.TOOL, "brand": r.get("brand"), "label": r.get("label"),
         "state": r.get("state"), "opened": r.get("at")}, indent=1))


def _job(r, refs, aspect, finish):
    """One generation, exactly as the session sends it to Higgsfield."""
    m = dict(MODEL)
    if r.get("model"):
        m = {"model": r["model"]}
    return {
        "slug": r["label"], "out": r["out"], **m,
        "aspect_ratio": aspect, "count": r["count"],
        "prompt": r["instruction"],
        "references": [r["picture"]] + refs,
        "references_role": "image_references — the reference picture FIRST, then each file in order",
        "finish": finish,
        "region": r["region"],
        "judge_prompt": CMP.prompt_for(r["asked"], r["checks"]),
    }


def edit(req, maker=None, compare_caller=None, fix_table=None, var_table=None, split_table=None):
    """One edit: the instruction, the job, and — once the picture is back —
    the judge and the record. Writes only under `out`."""
    r = resolve(req, fix_table, var_table, split_table)
    out = Path(r["out"])
    out.mkdir(parents=True, exist_ok=True)
    r["at"] = datetime.now().isoformat(timespec="seconds")
    r["version"] = _version(out, Path(r["picture"]).stem)

    if r["refused"]:
        r["state"] = "refused"
        _file(out, r)
        return r

    refs, notes = _brand_refs(r["brand"], r["brand_refs"], r["product"])
    r["notes"] = notes
    if r["brand_refs"] and not refs:
        r["state"] = "refused"
        r["refused"] = "; ".join(notes)
        _file(out, r)
        return r
    refs = refs + [x for x in r.get("references", []) if x not in refs]

    aspect, finish = frame_for(r["picture"], r["aspect"])
    r["job"] = _job(r, refs, aspect, finish)

    if req.get("dry_run"):
        r["state"] = "dry"
        _file(out, r)
        return r

    (out / "job.json").write_text(json.dumps({"jobs": [r["job"]]}, indent=1))
    r["state"] = "ready"
    _file(out, r)
    if maker is None:
        return r
    return ingest_one(out, maker(r["job"]), compare_caller=compare_caller)


# ------------------------------------------------------------------- ingest

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


def _entries(given):
    """A result as the session hands it back: a path, a list of paths, or
    {content, file, judge} per roll — `content` is the edit at the frame it
    was made, `file` the finished 9:16 when there is one, `judge` the session's
    own answer to the job's judge_prompt."""
    if isinstance(given, (str, Path, dict)):
        given = [given]
    out = []
    for g in given:
        if isinstance(g, dict):
            c = g.get("content") or g.get("file")
            out.append({"content": str(c), "file": str(g.get("file") or c), "judge": g.get("judge")})
        else:
            out.append({"content": str(g), "file": str(g), "judge": None})
    return out


def _frame_name(path):
    wh = dims(path) if Path(path).is_file() else None
    if _is(wh, 9, 16, 0.03):
        return "9:16"
    return nearest_aspect(wh)


def ingest_one(out, given, compare_caller=None):
    """The picture(s) back from Higgsfield: both pictures to the judge, a pass
    filed as a new version, anything else held under rejected/ with the why."""
    out = Path(out)
    r = json.loads((out / "edit.json").read_text())
    if r.get("state") in ("refused", "dry"):
        raise BadRequest(f"{out.name} is {r['state']} — there is no job to bring back")
    stem = Path(r["picture"]).stem
    entries = _entries(given)
    kept, rejected = list(r.get("delivered") or []), list(r.get("rejected") or [])
    for i, e in enumerate(entries, 1):
        content, final = Path(e["content"]).expanduser(), Path(e["file"]).expanduser()
        if not content.is_file() or not final.is_file():
            r.setdefault("missing", []).append(str(content if not content.is_file() else final))
            continue
        if r.get("region"):
            # "Nothing else moved" made a fact about the file, not a hope about
            # the model: outside the rectangle, the original's own pixels.
            r.setdefault("region_notes", []).append(_restore_outside(r["picture"], content, r["region"]))
            if final != content:
                r["region_notes"].append("the finished file was made before the paste-back — "
                                         "finish the delivered version again with resize-9x16")
        caller = compare_caller
        if e.get("judge"):
            answer = e["judge"] if isinstance(e["judge"], str) else json.dumps(e["judge"])
            caller = lambda *_a, _x=answer: _x            # noqa: E731
        verdict, fails, tests, raw = CMP.compare(r["picture"], content, r["asked"], r["checks"],
                                                 caller=caller)
        n = len(kept) + len(rejected) + 1
        name = f"{stem}--{r['fix'] or 'edit'}-v{r['version']}" + \
            (f"-{n:02d}" if (r["count"] > 1 or len(entries) > 1 or n > 1) else "") + (final.suffix or ".png")
        row = {"name": name, "from": str(final), "content": str(content),
               "delivered_at": _frame_name(final), "judged_by": "session" if e.get("judge") else "gemini",
               "verdict": verdict, "fails": fails, "tests": tests}
        if r.get("job", {}).get("finish") and final == content:
            row["note"] = "not finished to 9:16 yet — run skills/resize-9x16.md on this version"
        if verdict == "pass":
            shutil.copy2(final, out / name)
            row["file"] = str(out / name)
            kept.append(row)
        else:
            rej = out / "rejected"
            rej.mkdir(exist_ok=True)
            shutil.copy2(final, rej / name)
            (rej / f"{Path(name).stem}-why.md").write_text(
                "# " + name + " — did not hold the reference\n\n" +
                "\n".join(f"- {f}" for f in fails) +
                "\n\nAn edit that moved something else is a delta to narrow, not a picture to patch.\n"
                + (f"\n<details><summary>judge, raw</summary>\n\n```\n{raw.strip()}\n```\n</details>\n" if raw else ""))
            row["file"] = str(rej / name)
            rejected.append(row)
    r["delivered"], r["rejected"] = kept, rejected
    r["state"] = "filed" if kept else ("held" if rejected else "ready")
    r["ingested"] = datetime.now().isoformat(timespec="seconds")
    _file(out, r)
    return r


def ingest(folder, results, compare_caller=None):
    """Bring a whole run back: one edit (job.json) or a set (jobs.json).
    `results` is {slug: picture | [pictures] | {content, file, judge}}, or the
    path of a json file holding that. Slugs not in `results` stay ready."""
    folder = Path(folder).expanduser()
    if not isinstance(results, dict):
        results = json.loads(Path(results).expanduser().read_text())
    src = folder / "job.json" if (folder / "job.json").is_file() else folder / "jobs.json"
    if not src.is_file():
        raise BadRequest(f"no job.json or jobs.json in {folder} — nothing was prepared here")
    jobs = json.loads(src.read_text())["jobs"]
    known = {j["slug"] for j in jobs}
    unknown = sorted(set(results) - known)
    if unknown:
        raise BadRequest(f"results name jobs this run does not have: {', '.join(unknown)} — "
                         f"have: {', '.join(sorted(known))}")
    done, waiting = [], []
    for j in jobs:
        if j["slug"] in results:
            rec = ingest_one(j["out"], results[j["slug"]], compare_caller=compare_caller)
            done.append({"slug": j["slug"], "state": rec["state"],
                         "delivered": [d["file"] for d in rec.get("delivered", [])],
                         "rejected": [d["file"] for d in rec.get("rejected", [])]})
        else:
            waiting.append(j["slug"])
    for name in ("variations.json", "sequence.json"):
        if (folder / name).is_file():
            _refresh(folder, name)
    return {"folder": str(folder), "ingested": done, "waiting": waiting}


# ---------------------------------------------------------------- variations

VARY_REQUIRED = ("brand", "baseline", "variations")
VARY_OPTIONAL = ("kind", "keep", "product", "purpose", "aspect", "count", "label", "out", "dry_run",
                 "model", "references", "region")


def _row(rec):
    return {"state": rec["state"],
            "delivered": [d["file"] for d in rec.get("delivered", [])],
            "rejected": [d["file"] for d in rec.get("rejected", [])],
            "refused": rec.get("refused"), "record": str(Path(rec["out"]) / "edit.json")}


def _totals(summary, rows):
    summary["delivered"] = sum(len(r["delivered"]) for r in rows)
    summary["rejected"] = sum(len(r["rejected"]) for r in rows)
    summary["refused"] = sum(1 for r in rows if r["refused"])
    summary["ready"] = sum(1 for r in rows if r["state"] == "ready")
    return summary


def _jobs(root, results):
    jobs = [rec["job"] for rec in results if rec.get("state") == "ready" and rec.get("job")]
    if jobs:
        (root / "jobs.json").write_text(json.dumps({"jobs": jobs}, indent=1))


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

    planned = []
    for v in req["variations"]:
        v = {"id": v} if isinstance(v, str) else dict(v)
        row = table.get(v.get("id"))
        if not row:
            raise BadRequest(f"`{v.get('id')}` is not a variation — have: {', '.join(sorted(table))}")
        args = dict(v.get("args") or {})
        need = [n for n in row.get("needs", []) if n not in args]
        if need:
            raise BadRequest(f"variation `{row['id']}` needs: {', '.join(need)} — pass them in `args`")
        if "product" in row.get("references", []) and not req.get("product"):
            raise BadRequest(f"variation `{row['id']}` swaps the product — name `product` on the request")
        planned.append((row, args))

    root.mkdir(parents=True, exist_ok=True)
    rows, results = [], []
    for row, args in planned:
        one = {"brand": req["brand"], "picture": str(base), "change": fill(row["delta"], args),
               "kind": req.get("kind") or "picture",
               "keep": [fill(k, args) for k in row.get("keep", [])] + list(req.get("keep") or []),
               "checks": [fill(c, args) for c in row.get("checks", [])],
               "label": f"{label}--{row['id']}", "out": str(root / row["id"]),
               "count": req.get("count") or 1, "dry_run": req.get("dry_run")}
        for k in ("product", "purpose", "aspect", "model", "references", "region"):
            if req.get(k):
                one[k] = req[k]
        if row.get("references"):
            one["_brand_refs"] = row["references"]
        rec = edit(one, **kw)
        rows.append({"id": row["id"], "args": args, **_row(rec)})
        results.append(rec)
    _jobs(root, results)
    summary = _totals({"brand": req["brand"], "baseline": str(base), "label": label, "out": str(root),
                       "at": datetime.now().isoformat(timespec="seconds"), "variations": rows}, rows)
    _file_batch(root, summary, "variations.json")
    return summary


def _file_batch(root, summary, name):
    """A batch's own record, at the run-label folder an index reads. `state`
    is what the batch amounted to, not any one edit's."""
    (root / name).write_text(json.dumps(summary, indent=1))
    state = ("filed" if summary.get("delivered")
             else "ready" if summary.get("ready")
             else "refused" if summary.get("refused") else "held")
    (root / "run.json").write_text(json.dumps(
        {"machine": P.TOOL, "brand": summary.get("brand"), "label": summary.get("label"),
         "state": state, "opened": summary.get("at")}, indent=1))


def _refresh(root, name):
    """Re-read every edit in a set after an ingest and recount the set."""
    summary = json.loads((root / name).read_text())
    rows = summary["variations" if name == "variations.json" else "slides"]
    for row in rows:
        f = Path(row["record"])
        if f.is_file():
            rec = json.loads(f.read_text())
            row.update(_row(rec))
    _file_batch(root, _totals(summary, rows), name)
    return summary


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
# extra test for a slide.
THREAD = ("the same person and face", "the same product, held the same way",
          "the same palette", "the same framing and camera distance")


def thread_check(n):
    return (f"Slide {n} still belongs to the same sequence as IMAGE 1: " + ", ".join(THREAD)
            + ". Only what the change names is different.")


def sequence(req, **kw):
    """A sequence off one plate: slide one is the reference for every later
    slide; each is ONE delta, judged against slide one for the thread.
    Records under `<out>/slide-NN/`."""
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
        slides.append({"slide": n, "change": one_req["change"], "type": r.get("type"), **_row(rec)})
        results.append(rec)
    _jobs(root, results)
    summary = _totals({"brand": req["brand"], "slide_one": str(one), "label": label, "out": str(root),
                       "at": datetime.now().isoformat(timespec="seconds"), "slides": slides,
                       "note": "slide one is the plate as given; type per slide is carried in `type` for the compositor"},
                      slides)
    _file_batch(root, summary, "sequence.json")
    return summary
