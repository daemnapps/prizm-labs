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
"""
import json
import shutil
from pathlib import Path

from . import context as C
from . import filing, gates, judge, paths as P, prompting, providers, route as R

REQUIRED = ("brand", "purpose", "direction", "out")
OPTIONAL = ("aspect", "count", "product", "style", "format", "template", "from_image",
            "references", "label", "model", "people", "checks", "rules", "assets", "region")
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

    pmap = purposes_map if purposes_map is not None else purposes()
    purpose = pmap.get(req["purpose"])
    if not purpose:
        raise BadRequest(f"`{req.get('purpose')}` is not a purpose — "
                         f"have: {', '.join(sorted(pmap))}")

    req = dict(req)
    req["_purpose"] = purpose
    req["_aspect"] = req.get("aspect") or purpose.get("aspect") or "1:1"
    # THE FRAME RULE (the owner, 2026-09-22): every asset is 9:16; faces and words
    # sit inside a centred 4:5 zone. Asking a model to hold that failed 13 of
    # 13 live (both doors reflow to fill the height), so it is done by
    # geometry: the CONTENT is generated at 4:5, then the 9:16 asset is made
    # by taping that content down in the middle and painting only the strips
    # above and below (providers.finish_9x16). `_gen_aspect` is what the model
    # and the measured check see; `_aspect` is what leaves.
    #
    # A CORE STEP, NOT AN OPTION (the owner, 2026-09-29: "it needs to be done
    # anyway, and if it's not done, then it needs to be done"): a safe-zone
    # purpose ALWAYS leaves at 9:16. Asked for 9:16 (or nothing), the content
    # is made at 4:5; asked for another frame (1:1, 3:4 …), the content is
    # made at that frame and the whole of it is fitted inside the 4:5 zone.
    # Either way the asset that leaves is 9:16 — a 4:5 or a 1:1 never ships
    # as an ad.
    if purpose.get("safe_zone"):
        req["_gen_aspect"] = "4:5" if req["_aspect"] == "9:16" else req["_aspect"]
        req["_aspect"] = "9:16"
    else:
        req["_gen_aspect"] = req["_aspect"]
    req["_finish"] = req["_gen_aspect"] != req["_aspect"]
    req["_count"] = int(req.get("count") or 1)

    ctx = C.build(req, library=library if library is not None else gates.library())
    prompt, prompt_path = prompting.render(req, ctx)
    model_id, entry, why = R.pick(req, ctx, table)
    return req, ctx, prompt, prompt_path, model_id, entry, why


def finish_entry(t=None):
    """The door the 9:16 finish paints through — the edit row of the route
    table, because a masked outpaint IS an edit."""
    t = t or R.table()
    return t["models"]["gpt-image-edit"]


def finish(content, out, transport=None, table=None, fit="whole"):
    """One picture of ANY ratio, finished to 9:16 — the whole picture kept,
    fitted inside the centred 4:5 safe zone, only the backdrop around it
    painted. For a step that already has its content (a draft on the board,
    a designer's 4:5 or 1:1, a padded asset to redo).
    `python3 tools/image-production/finish.py <picture or folder>`."""
    return providers.finish_9x16(finish_entry(table), content, out, transport=transport, fit=fit)


def make(req, library=None, purposes_map=None, table=None,
         transport=None, judge_caller=None, mirror=True, mode="hold"):
    """The request, made. Returns a result dict; writes only under `out` and
    the Drive mirror.

    The order is the one the static-ad tool proved: gates that cost nothing
    run FIRST, then the model, then the judge, then the media gate, then
    delivery. A picture the judge failed never reaches the delivery folder."""
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

    made, killed, pictures = [], [], []
    for i in range(1, req["_count"] + 1):
        name = f"{stem}-{i:02d}.png"
        target = raw_dir / name
        if req.get("region") and req.get("from_image"):
            # The model may paint only inside the rectangle (providers.edit_in_region).
            # It is an edit through the edit door whatever the route said.
            result = providers.edit_in_region(finish_entry(t), prompt, req["from_image"],
                                              req["region"], target, transport=transport,
                                              work_dir=raw_dir / "region")
            conformed = None
        else:
            result = providers.generate(entry, prompt, ctx["references"], target,
                                        req["_gen_aspect"], transport=transport)
            conformed = providers.conform(target, R.aspects(t).get(req["_gen_aspect"]))
        v = judge.verdict(target, req, ctx, R.judge_entry(t), judge_caller)
        row = {"name": name, "model": model_id, "vendor_model": result.get("model"),
               "provider": result.get("provider"), "request_id": result.get("request_id"),
               "conformed": conformed, "content": str(target),
               "region_px": result.get("region_px"),
               "generated_at": req["_gen_aspect"], "delivered_at": req["_aspect"],
               "verdict": v["verdict"], "fails": v["fails"],
               "judge_model": v["judge_model"], "checks_run": len(v["checks_run"])}
        if v["verdict"] == "pass" and req["_finish"]:
            # The 9:16 finish: content taped down, strips painted. A finish
            # that cannot run is a HOLD, never a 4:5 shipped as if it were 9:16.
            try:
                fin = providers.finish_9x16(finish_entry(t), target, out / name,
                                            transport=transport, work_dir=raw_dir / "outpaint",
                                            fit="whole")
                row["finish"] = {k: fin[k] for k in ("content_box", "request_id", "model")}
            except Exception as e:                       # noqa: BLE001
                v = {"verdict": "reject", "fails": [f"the 9:16 finish did not run: {type(e).__name__}: {str(e)[:200]}"], "raw": ""}
                row["verdict"], row["fails"] = v["verdict"], v["fails"]
        if v["verdict"] == "pass":
            if not req["_finish"]:
                shutil.copy2(target, out / name)
            row["file"] = str(out / name)
            made.append(out / name)
        else:
            rej = out / "rejected"
            rej.mkdir(exist_ok=True)
            shutil.copy2(target, rej / name)
            (rej / f"{Path(name).stem}-why.md").write_text(
                judge.why_md(name, v["fails"], v["raw"]))
            row["file"] = str(rej / name)
            killed.append((name, v["fails"]))
        pictures.append(row)

    gates.media_gate(out, killed)

    drive = {"copied": [], "note": None}
    if mirror and made:
        copied, note = filing.mirror(made, ctx["brand"], filing.label_for(req))
        drive = {"copied": copied, "note": note}
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
            "held": [{"name": n, "fails": f} for n, f in killed],
            "drive": drive,
            "check": gates.state(out)}
