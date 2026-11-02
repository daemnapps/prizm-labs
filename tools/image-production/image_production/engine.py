"""The request in, the pictures out. This is the whole of the component's API.

    import image_production as IP
    IP.make({"brand": "...", "purpose": "email-hero",
             "direction": "...", "out": "..."})

One REQUEST shape, whatever the caller is. The contract is declared in this
folder's CLAUDE.md and enforced here; a field nothing on this list names is
refused rather than ignored, because a silently dropped field is a caller that
thinks it asked for something.

    brand       required   a folder under brands/ — never a default
    purpose     required   a row in purposes.json (email-hero, ad, …)
    direction   required   the words describing the picture
    out         required   where the caller wants the files
    aspect      optional   default: the purpose's
    count       optional   default: 1
    product     optional   a product the brand declares
    style       optional   an id on the element library's style/image list
    format      optional        …          …         format/image list
    template    optional        …          …         template/image list
    from_image  optional   an edit of this picture rather than a fresh render
    references  optional   extra reference pictures, paths on this machine
    inspiration optional   mood pictures (Pinterest pins, 2026-10-18): attached after every
                           other reference and named in the prompt as look-and-feel only
    label       optional   the run label — the Drive folder's name
    model       optional   force one model; it still has to be a declared row
    people      optional   override the purpose's "is a person in frame"
    checks      optional   extra judge tests for this picture
    rules       optional   extra standing rules for this picture
    assets      optional   attach the brand's matched assets (default: yes for a
                           render, NO for an edit — the reference is the picture)
    region      optional   (l, t, r, b) in PERCENT — with from_image, the model may
                           paint only inside that rectangle and the rest is the
                           original, pixel for pixel
    product_3d  optional   draw the product from its kit's 3D model, never by the
                           image model. Default ON when the product's kit has a 3D
                           model (`model/render3d.json`), OFF otherwise; False turns it off
    product_after optional the caller lays the REAL product over the drawn one after this
                           (image-teardown's picture step): the drawn product's look is not judged
    product_place optional where and how the 3D product goes: {pose, x, y (the contact
                           point, fractions of the frame), height (fraction of the frame
                           height) or px_per_cm, camera{azimuth, elevation, focal_mm},
                           light{azimuth, elevation, warmth}}. Default: the kit's pose,
                           lower centre, 30% of the frame tall
"""
import json
import shutil
from pathlib import Path

from . import context as C
from . import approval as AP, filing, gates, judge, paths as P, product3d, prompting, providers, recipe as RC, route as R

REQUIRED = ("brand", "purpose", "direction", "out")
OPTIONAL = ("aspect", "count", "product", "style", "format", "template", "from_image",
            "references", "label", "model", "people", "checks", "rules", "assets", "region",
            "product_3d", "product_place", "inspiration", "product_after", "recipe")
FIELDS = set(REQUIRED) | set(OPTIONAL)


class BadRequest(SystemExit):
    pass


def purposes(path=None):
    return json.loads((path or (P.home() / "purposes.json")).read_text())["purposes"]


def resolve(req, library=None, purposes_map=None, table=None):
    """Everything a request means, worked out without spending anything:
    the purpose row, the frame, the brand context, the prompt as it would be
    sent, and the model it would route to.

    Returns (req, ctx, prompt, prompt_path, model_id, model_entry, why)."""
    unknown = sorted(set(req) - FIELDS - {k for k in req if k.startswith("_")})
    if unknown:
        raise BadRequest(f"the request carries fields this component does not take: "
                         f"{', '.join(unknown)} — the contract is: "
                         f"{', '.join(sorted(FIELDS))}")
    missing = [f for f in REQUIRED if not req.get(f)]
    if missing:
        raise BadRequest(f"the request is missing: {', '.join(missing)}")
    try:                                      # no blank reaches a door (a dry run is refused too)
        RC.gate(req.get("recipe"), table, scope="engine", purpose=req.get("purpose"), edit=bool(req.get("from_image")))
        AP.check_bases([req.get("from_image")] + list(req.get("references") or []), table)   # slop is not a base
    except (RC.RecipeRefused, AP.ApprovalRefused) as ex:
        raise BadRequest(str(ex))

    pmap = purposes_map if purposes_map is not None else purposes()
    purpose = pmap.get(req["purpose"])
    if not purpose:
        raise BadRequest(f"`{req.get('purpose')}` is not a purpose — "
                         f"have: {', '.join(sorted(pmap))}")

    req = dict(req)
    req["_purpose"] = purpose
    req["_aspect"] = req.get("aspect") or purpose.get("aspect") or "1:1"
    # THE FRAME RULE (the owner, 2026-10-26): every photo and video asset (not email) is 9:16, made at 9:16 from the start
    # with the safe zone assumed: faces, hands, product and words sit in the centre 4:5 (prompting.SAFE tells the
    # model, judge.SAFE_ZONE measures it). Nothing is made at 4:5 and painted out: that came out inconsistent.
    # `_gen_aspect` is what the model is asked for and is the same as `_aspect`, which is what leaves.
    if purpose.get("safe_zone"):
        req["_aspect"] = "9:16"
    req["_gen_aspect"] = req["_aspect"]
    req["_count"] = int(req.get("count") or 1)

    lib = library if library is not None else gates.library()
    ctx = C.build(req, library=lib)
    kit, decl = product3d.wanted(req, ctx["brand"])
    if kit is None:
        prompt, prompt_path = prompting.render(req, ctx)
    else:
        # THE PRODUCT FROM ITS 3D MODEL (the owner, 2026-10-14). The scene is made
        # with no product in it: no product slot, no product photograph or
        # product-matched asset as a reference (the model copies what it is
        # shown), and a rule that keeps the spot clear. The product is rendered
        # from the kit's model and put in after generation; the judge sees the
        # composite, against the product's own tests (ctx keeps them).
        place = product3d.plan(req, decl)
        facts = product3d.kit_facts(kit)
        pose = (decl.get("poses") or {}).get(place["pose"]) or {}
        what = facts.get("what") or "the product"
        holder = ""
        if pose.get("rest") is not None:
            rests = (facts.get("behaviour") or {}).get("rests") or []
            if 0 <= int(pose["rest"]) < len(rests):
                holder = f" (and the {rests[int(pose['rest'])].get('on') or 'holder'} it rests in)"
        rule = prompting.body(prompting.latest("product-space"))
        rule = (rule.replace("{what}", what).replace("{holder}", holder)
                .replace("{spot}", product3d.spot_words(place)))
        scene_req = dict(req, product=None, assets=req.get("assets", False),
                         rules=list(req.get("rules") or []) + [rule])
        scene_ctx = C.build(scene_req, library=lib)
        prompt, prompt_path = prompting.render(scene_req, scene_ctx)
        ctx["references"] = scene_ctx["references"]
        ctx["product3d"] = {"kit": str(kit), "place": place, "pose_what": pose.get("what"),
                            "why": "the product's kit has a 3D model — the image model "
                                   "never draws it; it is rendered and composited"}
        req["_product3d"] = ctx["product3d"]
    model_id, entry, why = R.pick(req, ctx, table)
    return req, ctx, prompt, prompt_path, model_id, entry, why


def _size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size


def _to_out(src, dst):
    from PIL import Image
    with Image.open(src) as im:
        im.convert("RGB").resize((providers.OUT_W, providers.OUT_H), Image.LANCZOS).save(dst)


def finish_entry(t=None):
    """The edit door of the route table: a region edit (providers.edit_in_region) goes through it."""
    t = t or R.table()
    return t["models"]["gpt-image-edit"]


def with_learnings(req):
    """Every picture carries the chain's picture learnings (components/run-kit/run_kit/learnings.py): every correction
    and win from past reviews, for every brand and this one, whichever line asked for the picture (the owner, 2026-10-17:
    "this learning stuff should definitely be agnostic … this is for the overall chain")."""
    # An edit (from_image) is "keep everything, change this one thing": rules for how a fresh picture is shot would
    # be judged against a picture that was never meant to be re-shot (2026-10-18: an edit of a newspaper key visual
    # was held twice for "the tube is not standing on amber").
    if not req.get("direction") or req.get("no_learnings") or req.get("from_image"):
        return req
    try:
        import sys as _s
        from pathlib import Path as _P
        rk = str(_P(__file__).resolve().parents[2] / "run-kit")
        if rk not in _s.path:
            _s.path.append(rk)
        from run_kit import learnings as _RL
        rules = _RL.block(req.get("brand"), ("picture",))
    except Exception:                      # a learnings store that will not read never stops a picture
        return req
    if rules == "(none yet)":
        return req
    return dict(req, direction=req["direction"] + "\n\nFrom every past review (a NEVER never happens again, a DO always does):\n" + rules)


def _log(a):
    return {k: a.get(k) for k in ("n", "slot", "model", "outcome", "score", "failed_checks", "why") if a.get(k) is not None}


def _flags_of(req):
    """Which pictures this one is made from carry a below_criteria flag: the flag travels on (allowed as a reference)."""
    return [str(x) for x in ([req.get("from_image")] + list(req.get("references") or []))
            if x and AP.flag_of(x)]


def _score(v):
    """0..1: the share of the judge's checks that passed. A picture the judge never ran on (a measured failure) scores 0."""
    n = len(v.get("checks_run") or [])
    return 0.0 if (not n and v.get("fails")) else max(0.0, 1.0 - len(v.get("fails") or []) / max(1, n))


def _attempts(req, ctx, prompt, entry, model_id, t, raw_dir, name, transport, judge_caller, max_n):
    """One picture's attempts, in ladder order, at most `max_n` (a failed or refused call counts too). Each made attempt is
    judged and scored; nothing here holds the chain. A refusal moves to the next model at once; the second slot of a rung
    is its retry for a busy or broken call."""
    out, used, refused_rungs = [], 0, set()
    if req.get("region") and req.get("from_image"):
        slots_ = [{"slot": "region edit", "entry": finish_entry(t), "again": False, "name": "region"}]
    else:
        slots_ = R.slots(model_id, entry, t)
    refs = ctx["references"]
    for sl in slots_:
        if used >= max_n:
            break
        cap = sl.get("max_images")
        if cap is not None and len(refs) > cap:
            out.append({"n": None, "slot": sl["slot"], "outcome": "skipped", "why": f"{len(refs)} pictures is more than this model takes ({cap})"})
            continue
        if sl["again"] and sl["name"] in refused_rungs:
            continue
        used += 1
        e = sl["entry"]
        target = raw_dir / f"{Path(name).stem}-a{used}.png"
        a = {"n": used, "slot": sl["slot"], "model": e.get("vendor_model")}
        try:
            if sl["name"] == "region":
                result = providers.edit_in_region(e, prompt, req["from_image"], req["region"], target, transport=transport,
                                                  work_dir=raw_dir / "region")
                conformed = None
            else:
                result = providers.generate(e, prompt, refs, target, req["_gen_aspect"], transport=transport)
                conformed = providers.conform(target, R.aspects(t).get(req["_gen_aspect"]))
        except (providers.ProviderError, SystemExit) as ex:
            if len(slots_) == 1:                       # no ladder: the call's own error, as before
                raise
            refused = bool(getattr(ex, "refused", False))
            if refused:
                refused_rungs.add(sl["name"])
            a.update(outcome="refused" if refused else "failed", why=str(ex)[:240])
            out.append(a)
            continue
        placed = None
        if ctx.get("product3d"):
            plate = raw_dir / f"{Path(name).stem}-a{used}-scene.png"
            shutil.copy2(target, plate)
            try:
                got = product3d.composite_into(plate, target, ctx["product3d"]["kit"], ctx["product3d"]["place"],
                                               raw_dir / f"{Path(name).stem}-a{used}-product3d",
                                               ask=product3d.judge_ask(R.judge_entry(t), judge_caller))
                placed = {"scene": str(plate), "render": got["render"]["file"], "source": got["render"]["source"],
                          "box": got["placed"]["box"]}
            except Exception as ex:                    # noqa: BLE001
                placed = {"scene": str(plate), "error": f"{type(ex).__name__}: {str(ex)[:300]}"}
        v = judge.verdict(target, req, ctx, R.judge_entry(t), judge_caller)
        if placed and placed.get("error"):
            v = {"verdict": "reject", "fails": [f"the 3D product was not placed: {placed['error']}"], "raw": "",
                 "judge_model": v.get("judge_model"), "checks_run": v.get("checks_run", [])}
        a.update(file=str(target), result=result, conformed=conformed, placed=placed, judge=v, score=_score(v),
                 verdict="pass" if v["verdict"] == "pass" else "below_criteria", failed_checks=v["fails"],
                 outcome="pass" if v["verdict"] == "pass" else "below_criteria")
        out.append(a)
        if v["verdict"] == "pass":
            break
    return out


def make(req, library=None, purposes_map=None, table=None,
         transport=None, judge_caller=None, mirror=False, mode="hold"):
    """The request, made. Returns a result dict; writes only under `out` and
    the Drive mirror.

    The order is the one the static-ad tool proved: gates that cost nothing
    run FIRST, then the model, then the judge, then the media gate, then
    delivery. A picture the judge failed never reaches the delivery folder."""
    req = with_learnings(req)
    req, ctx, prompt, prompt_path, model_id, entry, why = resolve(
        req, library, purposes_map, table)
    out = filing.out_dir(req)
    t = table or R.table()

    gates.inputs_gate(req, ctx, out, purposes_map if purposes_map is not None else purposes(),
                      R.aspects(t), mode)
    gates.elements_gate(req, ctx, out, mode)

    (out / "prompt-as-sent.txt").write_text(prompt + "\n")

    stem = judge.slug(req.get("label") or req["purpose"])
    raw_dir = out / "generated"
    raw_dir.mkdir(parents=True, exist_ok=True)

    made, below, pictures = [], [], []
    max_n = R.max_attempts("pictures", t)
    for i in range(1, req["_count"] + 1):
        name = f"{stem}-{i:02d}.png"
        attempts = _attempts(req, ctx, prompt, entry, model_id, t, raw_dir, name, transport, judge_caller, max_n)
        gen = [a for a in attempts if a.get("file")]
        if not gen:                                  # nothing was made at all: there is nothing to move forward
            raise providers.ProviderError("no model made the picture: " + "; ".join(
                f"{a['slot']} {a['outcome']}" + (f" ({a['why']})" if a.get("why") else "") for a in attempts))
        best = max(gen, key=lambda a: (a["score"], a["n"]))      # best score; on a tie the later attempt
        passed = best["verdict"] == "pass"
        target, v, result = Path(best["file"]), best["judge"], best["result"]
        row = {"name": name, "model": model_id, "vendor_model": result.get("model"),
               "made_by": best["slot"], "ladder": [_log(a) for a in attempts],
               "provider": result.get("provider"), "request_id": result.get("request_id"),
               "conformed": best["conformed"], "content": str(target),
               "region_px": result.get("region_px"),
               "product3d": best["placed"],
               "generated_at": req["_gen_aspect"], "delivered_at": req["_aspect"],
               "attempts": [_log(a) for a in attempts], "chosen_attempt": best["n"], "score": best["score"],
               "verdict": "pass" if passed else "below_criteria", "below_criteria": not passed,
               "fails": v["fails"], "judge_model": v["judge_model"], "checks_run": len(v["checks_run"])}
        # outputs never hold a flow: the best attempt is delivered; one that did not pass says so, in plain words
        if req["_aspect"] == "9:16" and providers.is_9x16(*_size(target)) and _size(target) != (providers.OUT_W, providers.OUT_H):
            _to_out(target, out / name)               # made at 1152x2048, delivered at 1080x1920
        else:
            shutil.copy2(target, out / name)
        carried = _flags_of(req)
        (out / name).with_suffix(".recipe.json").write_text(P.portable(json.dumps({   # stored paths portable (rule 4)
            "recipe": req.get("recipe"), "not_applicable": RC.na_of(req.get("recipe")),
            "request": {k: x for k, x in req.items() if not k.startswith("_")}, "prompt": prompt,
            "model": model_id, "vendor_model": result.get("model"), "made_by": best["slot"],
            "attempts": row["attempts"], "chosen_attempt": best["n"],
            "chosen": True,                                  # the engine chose this attempt (the prompt generator's chosen_record reads it)
            "below_criteria": [] if passed else list(v["fails"]),   # the plain failed checks; empty when it passed
            "is_below_criteria": not passed, "failed_checks": v["fails"], "below_criteria_inputs": carried,
            "carries_below_criteria": (not passed) or bool(carried)}, indent=1, ensure_ascii=False, default=str)))
        # approved only when the sheet gate AND the judge passed; a below-criteria picture is recorded, flagged, and usable
        AP.write(out / name, gate_passed=bool(req.get("recipe")), judge=row["verdict"], by="engine judge",
                 below_criteria=not passed, failed_checks=v["fails"])
        if not passed:
            (out / f"{Path(name).stem}-below-criteria.md").write_text(judge.below_md(name, v["fails"], best["score"], row["attempts"], v.get("raw", "")))
            below.append((name, v["fails"]))
        row["file"] = str(out / name)
        made.append(out / name)
        pictures.append(row)

    gates.media_gate(out, [])                      # outputs never hold: below-criteria pictures are flagged, not held

    drive = {"copied": [], "note": None}
    if mirror and made:
        copied, note, rec = filing.mirror_record(made, ctx["brand"], filing.label_for(req))
        drive = {"copied": copied, "note": note}
        filing.write_drive_json(out, rec)       # LD-64 (records Drive ids)
        if note:
            print(f"  {note}")

    held = gates.held(out)
    filing.record(out, req, ctx, {"id": model_id, "why": why,
                                  "vendor": entry.get("vendor_model"),
                                  "provider": entry.get("provider")},
                  prompt_path, pictures, held, drive)

    return {"out": str(out), "brand": ctx["brand"], "purpose": ctx["purpose"]["id"],
            "prompt": prompt, "prompt_skeleton": str(prompt_path),
            "model": model_id, "model_why": why,
            "pictures": pictures,
            "delivered": [str(p) for p in made],
            "held": [],                                   # kept for callers that read it: outputs are never held
            "below_criteria": [{"name": n, "failed_checks": f} for n, f in below],
            "drive": drive,
            "check": gates.state(out)}
