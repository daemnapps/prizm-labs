"""THE 3D PRINT QUEUE: every picture the set gate stops waits here until a session builds and prints its set (2026-11-10).

The set gate (set_gate.py) refuses a picture with no filed 3D set print. A refusal alone stops work, so every refusal that
knows its brand files a request here, and the `3d-print` skill (.claude/skills/3d-print/SKILL.md) clears the queue: it
builds the set in 3D Jutsu from the request's plan, prints it, files it with picture_sets.py put, marks the request done
and runs the step that was waiting (`resume`).

    runs/image-production/<brand>/set-requests/<id>.json   one request: open → done
        {id, brand, state, made, what, scene, products[], cast[], frame, words[], resume{}, source, set, done_at}

ANY HIGGSFIELD ACCOUNT (2026-11-11): a 3D Jutsu project is readable only by the account that made it, so a project id in a
plan works only on the owner's account (any other account gets PROJECT_AUTHORIZATION_CONFIGURATION_INVALID). Every world
and product build therefore carries `any_account`: the project name to find with scene_builder_3d_list_projects on the
account in use, and the recipe that rebuilds it under that name when it is missing. Ids are never carried across accounts.

ONE PRINT AT A TIME (2026-11-11): `printing` records a print the moment it is sent (project, generation, account, credits
before). While a request is printing, `plan` hands out no print step, so a second session on the machine never prints it
again. For an unconfirmed submission, read the same generation once, then check the submitting account's transactions.
An unchanged balance or absent charge does not prove rejection. Keep the hold until transactions are checked and a
terminal failure/rejection or provider confirmation establishes that no job was accepted. The 3d-print skill owns
reconciliation instructions. Clearing remains a manual action; the reason records the evidence.

Nothing here spends anything: it writes and reads JSON. Commands are in picture_sets.py (request, queue, plan, printing,
done).
"""
import json
import re
import time
from pathlib import Path

from . import paths as P

PRINT_WAIT_MIN = 10
ANY_ACCOUNT = ("Project ids here live in the owner's Higgsfield account only. On any account: scene_builder_3d_list_projects "
               "and use the project whose name is exactly `any_account.name`; if there is none, create a project with that "
               "name and rebuild it from `any_account.recipe` (components/3d-recipes README: each step-NN.py unchanged, in "
               "order). Never pass an id from this plan to another account.")
FRAME = "9:16, the centre 4:5 holds the scene; headroom left clear where any words go"


def home(brand):
    return P.repo() / "runs" / "image-production" / brand / "set-requests"


def slug(text, n=60):
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return (s[:n].rstrip("-") or "picture")


def _kit(brand, product):
    """What the print needs from a product's kit: its casting sheet, true size and 3D build (or None for no kit)."""
    try:
        from . import product3d
        kit = product3d.find_kit(brand, product)
    except Exception:                                    # noqa: BLE001  a kit that will not read is named, not fatal
        kit = None
    if kit is None:
        return {"kit": product, "missing": "no product kit: the product needs its casting sheet and 3D build first"}
    k = json.loads((kit / "kit.json").read_text()) if (kit / "kit.json").is_file() else {}
    sheet = kit / str((k.get("sheet") or {}).get("file") or "model/product-sheet.png")
    jutsu = kit / "model" / "sheet" / "jutsu" / "angles.json"
    proj = {}
    if jutsu.is_file():
        try:
            proj = json.loads(jutsu.read_text()).get("project") or {}
        except ValueError:
            proj = {}
    rec = _recipes_for(brand, kit)
    if not proj.get("id"):                         # the kit's own build: the casting-sheet recipe's source project
        for r in rec:
            if "casting-sheet" in r["recipe"] and r.get("source_project"):
                proj = {"id": r["source_project"]}
                break
    beh = k.get("behaviour") or {}
    rest_pics = []
    for rest in beh.get("rests") or []:
        for pic in rest.get("pictures") or []:
            f = kit / str(pic.get("kit") or "")
            if pic.get("kit") and f.is_file():
                rest_pics.append(P.rel(f))
    return {"kit": kit.name, "what": k.get("what"), "size_cm": k.get("size_cm"),
            "casting_sheet": P.rel(sheet) if sheet.is_file() else None,
            "jutsu_project": proj.get("id"), "recipes": [r["recipe"] for r in rec],
            "any_account": {"name": f"{brand} product · {kit.name}", "recipe": next((r["recipe"] for r in rec
                            if "casting-sheet" in r["recipe"]), (rec[0]["recipe"] if rec else None))},
            "rests": beh.get("rests"), "never_show": beh.get("never_show"), "cannot": beh.get("cannot"),
            "label_words": k.get("label_words"), "rest_pictures": rest_pics,
            "always": [x.get("line") if isinstance(x, dict) else x for x in (k.get("always") or [])]}


def _recipes_for(brand, kit):
    """The saved builds for this exact kit (components/3d-recipes/recipes.json): named for the kit's first word, never for
    a sibling kit that shares it (flex-face-brush is not flex-charging-case)."""
    f = P.sibling("3d-recipes", "recipes.json")
    rows = json.loads(f.read_text()) if f.is_file() else []
    head = kit.name.split("-")[0]
    siblings = [d.name for d in kit.parent.iterdir() if d.is_dir() and d.name != kit.name and d.name.startswith(head + "-")]
    out = []
    for r in rows if isinstance(rows, list) else []:
        name = str(r.get("recipe") or "")
        if not name.startswith(f"{brand}-{head}-"):
            continue
        if any(s in name for s in siblings):
            continue
        out.append(r)
    return out


def file(brand, what, name=None, scene=None, products=(), cast=(), frame=None, words=(), resume=None, source=None, **extra):
    """File (or refresh) an open request. Returns its path. A request already done is left as it is."""
    rid = slug(name or what)
    d = home(brand)
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{rid}.json"
    old = json.loads(f.read_text()) if f.is_file() else {}
    if old.get("state") == "done":
        return f
    rec = {"id": rid, "brand": brand, "state": "open", "made": old.get("made") or time.strftime("%Y-%m-%dT%H:%M:%S"),
           "what": what, "scene": scene or what, "products": [_kit(brand, p) for p in products if p],
           "cast": [str(c) for c in cast if c], "frame": frame or FRAME, "words": [str(w) for w in words if w],
           "resume": resume or old.get("resume") or {}, "source": source or old.get("source"), **extra}
    if old.get("printing"):              # a refresh never forgets a print already sent (no second print of the request)
        rec["printing"] = old["printing"]
    f.write_text(P.portable(json.dumps(rec, indent=1, ensure_ascii=False, default=str)) + "\n")
    return f


def read(brand, rid):
    f = home(brand) / f"{slug(rid)}.json"
    return json.loads(f.read_text()) if f.is_file() else None


def open_requests(brand=None):
    base = P.repo() / "runs" / "image-production"
    brands = [brand] if brand else sorted(d.name for d in base.iterdir() if d.is_dir()) if base.is_dir() else []
    out = []
    for b in brands:
        for f in sorted(home(b).glob("*.json")) if home(b).is_dir() else []:
            try:
                r = json.loads(f.read_text())
            except ValueError:
                continue
            if r.get("state") == "open":
                out.append(r)
    return out


def worlds(brand, scene=""):
    """The brand's 3D worlds (runs/ai-elements/<brand>/worlds/*/world.json): project, rooms and cameras to build in,
    the rooms the request's scene names first (`match`)."""
    words = set(re.findall(r"[a-z]+", str(scene or "").lower()))
    folders = [d.name for d in P.sibling("3d-recipes").glob(f"{brand}-world-*") if d.is_dir()]
    out = []
    for wj in sorted((P.repo() / "runs" / "ai-elements" / brand / "worlds").glob("*/world.json")):
        try:
            w = json.loads(wj.read_text())
        except ValueError:
            continue
        wid, wname = str(w.get("id") or ""), slug(w.get("name") or "")
        recipe = next((f for f in folders if f.endswith("-" + wid) or f.endswith("-" + wname) or wid in f), None)
        rooms = [{"id": r.get("id"), "name": r.get("name"), "cameras": r.get("cameras")} for r in w.get("rooms") or []]
        match = [r["id"] for r in rooms if words & set(re.findall(r"[a-z]+", f"{r['id']} {r['name']}".lower()))]
        out.append({"id": w.get("id"), "name": w.get("name"), "project": (w.get("scene") or {}).get("project_id"),
                    "rooms": rooms, "match": match,
                    "recipe": P.rel(P.sibling("3d-recipes") / recipe) if recipe else None,
                    "any_account": {"name": f"{brand} world · {recipe or wid or wname}",
                                    "recipe": P.rel(P.sibling("3d-recipes") / recipe) if recipe else None}})
    return sorted(out, key=lambda w: -len(w["match"]))


def board_members(r):
    """The cast board's members as `element[:look]`: the look the request carries for each (2026-11-21, brief-0380:
    every board took the first look on file while the brief named another)."""
    looks = r.get("looks") if isinstance(r.get("looks"), dict) else {}
    out = []
    for c in r.get("cast") or []:
        c, lk = str(c), looks.get(c)
        # a person whose scene look lives on their variant in the ad's style (casting/<id>/styles/<style>/) is that
        # variant on the board (21 Nov 2026: a family-3d photographer's look was looked up on his photoreal master)
        st = r.get("style")
        if lk and st and "/" not in c:
            home = P.repo() / "runs" / "ai-elements" / str(r.get("brand") or "") / "casting" / c
            if not (home / "sheets" / f"{lk}.jpg").is_file() and (home / "styles" / st / "sheets" / f"{lk}.jpg").is_file():
                c = f"{c}/styles/{st}"
        out.append(f"{c}:{lk}" if lk and ":" not in c else c)
    return out


def plan(brand, rid):
    """Everything a session needs to build and print this request's set, nothing spent: the worlds to build in, each
    product's true-size build and casting sheet, the cast board command for people, the print's words and references."""
    r = read(brand, rid)
    if r is None:
        raise SystemExit(f"no set request {rid} for {brand}")
    if r.get("printing"):
        return {"request": r, "set": r["id"], "printing": r["printing"], "print": None,
                "stop": "This request is already printing. Do not print it again. Read the generation once "
                        "(scene_builder_3d_get_generation with printing.project and printing.generation, on printing.account). "
                        "Still unconfirmed: check the submitting account's transactions after printing.sent_at, "
                        "matching this generation/job. An unchanged balance or absent charge is not proof of rejection. "
                        "Keep this hold if transaction history is unavailable. Clear only after the transaction check "
                        "and a terminal failed/rejected result or provider confirmation that no job was accepted; "
                        "record the evidence in the clear reason. Never allocate a new request ID to recover an "
                        "unconfirmed submission. See .claude/skills/3d-print/SKILL.md."}

    import importlib.util
    spec = importlib.util.spec_from_file_location("ip_picture_sets_q", P.home() / "picture_sets.py")
    ps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ps)
    # one kit once (two product names that resolve to the same kit doubled every sheet on the board and every line
    # in the words; the board grew so wide the cast shrank to a sliver and the print lost the faces, brief 0339)
    prods, _kits = [], set()
    for p in r.get("products") or []:
        k = (p.get("kit") or p.get("what")) if isinstance(p, dict) else p
        if k in _kits:
            continue
        _kits.add(k)
        prods.append(p)
    first = next((p for p in prods if p.get("what")), {})
    size = first.get("size_cm")                    # the kit's dict (height, width, depth): the words take the longest side
    if isinstance(size, dict):
        size = max([v for v in size.values() if isinstance(v, (int, float))] or [0]) or None
    objects, creative = [], []                     # what the kit says it does and never does travels into the words
    for p in prods:
        name = str(p.get("what") or p.get("kit"))
        rests = [x.get("how") for x in p.get("rests") or [] if x.get("how")]
        if rests:
            objects.append(f"{name[:1].upper() + name[1:]} rests only as the blockout places it: " + "; or ".join(rests)
                           + ". The holder it sits in is a real object and stays in the picture")
        for c in (p.get("cannot") or []) + (p.get("never_show") or []):
            creative.append(f"Never: {name}, {c}.")
        if p.get("label_words") == []:
            creative.append(f"{name[:1].upper() + name[1:]} carries no printed words or wordmark anywhere the reference "
                            "sheet does not show them; never add letters to it.")
        for a in p.get("always") or []:            # how the owner always wants the product shown (kit.json `always`)
            creative.append(f"Always: {name}, {a}.")
    scene = {"shot": r.get("scene") or r.get("what"), "light": "exactly as the blockout shows it", "objects": objects,
             "style_formula": r.get("style_formula"),
             "creative": creative, "product": first.get("what"), "size_cm": size,
             "people_none": not (r.get("cast") or r.get("people") or r.get("people_in_it")),
             "reference_says": ("the second is the reference board: first the room (its layout, furniture and materials, "
                                "never any person in it), and last the style picture (only how it is rendered)")
             if r.get("style_formula") and (r.get("element") or {}).get("kind") in ("set", "world")
             else ("the second is the reference board: the numbered people or the product first (who and what "
                   "they are), and last the style picture (only how it is rendered)") if r.get("style_formula")
             else None if first.get("what") else
             ("the second is the reference picture, which supplies only the photo quality, skin, hair and material "
              "textures, never its faces, layout or writing")}
    # real skin (owner, 2026-11-26): a set that shows a person or bare skin carries the skin bank's patches (a real
    # customer crop + a macro shot) on its reference board, the words' skin line, and `--skin` when it is filed
    who = r.get("cast") or r.get("people") or r.get("people_in_it")
    skin = ps.skin_pick(r.get("scene"), r.get("what"), r.get("direction")) if ps.shows_skin(
        who, r.get("scene"), r.get("what"), r.get("direction")) else []
    scene["skin"] = bool(skin)
    words = ps.print_prompt(scene)
    # A product's ONLY reference is its casting sheet (ruled 2026-11-23). The
    # kit's rest pictures (old CGI of the holder) are never put on the print: they carried a misspelled towel mark,
    # plants and a cradle into every print. How it rests stays in the words.
    refs = [p["casting_sheet"] for p in prods if p.get("casting_sheet")]
    # a style variant (style_chain): the element's master is the identity reference when no sheet above carries it
    if r.get("identity_reference") and not r.get("cast") and r["identity_reference"] not in refs:
        refs.append(r["identity_reference"])
    board = None
    if r.get("cast"):
        board = {"command": "python3 components/image-production/cast_board.py build %s runs/image-production/%s/"
                            "set-requests/%s-cast-board.png %s" % (brand, brand, r["id"], " ".join(board_members(r))),
                 "board": f"runs/image-production/{brand}/set-requests/{r['id']}-cast-board.png"}
        refs = [board["board"]] + refs
        words += (" The people are exactly the numbered people on the reference board, left to right in that order.")
    # the look of a styled print: the style's swatch or a face-free swipe frame, labelled look-only on the board
    if r.get("look_reference"):
        refs.append(r["look_reference"])
        words += (" The last picture on the reference board shows only the style to render in (surfaces, light, "
                  "rendering): never its faces, people, layout or objects.")
    refs += [x["file"] for x in skin if x["file"] not in refs]
    ref_board = None
    # the print takes ONE reference: everything goes on one board. A styled print's look picture always goes on a board,
    # even alone (an empty set in the ad's style): its words name "the reference board", and `picture_sets.py put` keeps
    # only a casting sheet or a board as a kept print's reference, so a bare swatch here made `file_it` refuse a reprint.
    if len(refs) > 1 or (refs and r.get("look_reference")):
        ref_board = {"command": "python3 components/image-production/cast_board.py refs runs/image-production/%s/"
                                "set-requests/%s-reference.png %s" % (brand, r["id"], " ".join(refs)),
                     "board": f"runs/image-production/{brand}/set-requests/{r['id']}-reference.png", "from": refs}
        refs = [ref_board["board"]]
    note = None
    if not refs:
        note = ("no product and no people: the print's one reference is the picture the request was made from (its swipe "
                "or the email's reference, under resume), else the brand's world room the set stands in")
    return {"request": r, "set": r["id"], "any_account": ANY_ACCOUNT,
            "worlds": worlds(brand, r.get("scene") or r.get("what")), "products": prods,
            "cast_board": board, "reference_board": ref_board, "note": note,
            "print": {"tool": "scene_builder_3d_generate_angles", "aspect": "9:16", "resolution": ps.print_size(r.get("picture_kind"))[0],
                      "references": refs, "words": words, "credits": ps.print_size(r.get("picture_kind"))[1],
                      "first": "the moment the print is sent: picture_sets.py printing %s %s --project <project> "
                               "--generation <generation id> --account <account email> --credits-before <balance>"
                               % (brand, r["id"])},
            "file_it": "python3 components/image-production/picture_sets.py put %s %s --render R --print P --note \"kept: "
                       "...\" --project <jutsu project> --generation <generation id> --reference %s%s%s"
                       % (brand, r["id"], refs[0] if refs else "<reference>",
                          " --cast-board " + board["board"].replace(".png", ".json") if board else "",
                          " --run " + r["resume"]["run"] if (r.get("resume") or {}).get("run") else "")
                       + (" --skin " + " ".join(x["file"] for x in skin) if skin else ""),
            "skin": skin,
            "then": "python3 components/image-production/picture_sets.py done %s %s --set %s" % (brand, r["id"], r["id"])}


def printing(brand, rid, project=None, generation=None, account=None, credits_before=None, clear=None):
    """Record a print as sent (so no second session prints the request again), or clear it with the reason it was not
    taken. Returns the request."""
    f = home(brand) / f"{slug(rid)}.json"
    if not f.is_file():
        raise SystemExit(f"no set request {rid} for {brand}")
    r = json.loads(f.read_text())
    if clear is not None:
        if not str(clear).strip():
            raise SystemExit("--clear needs the reason (e.g. \"not taken: no charge after 10 minutes\")")
        r.setdefault("print_log", []).append(dict(r.get("printing") or {}, cleared=str(clear),
                                                  cleared_at=time.strftime("%Y-%m-%dT%H:%M:%S")))
        r.pop("printing", None)
    else:
        if r.get("printing"):
            raise SystemExit(f"{rid} is already printing ({r['printing'].get('generation')}, sent "
                             f"{r['printing'].get('sent_at')}): do not print it again; see `plan` for the check")
        if not (project and generation):
            raise SystemExit("printing needs --project and --generation (the ids the print returned)")
        r["printing"] = {"project": project, "generation": generation, "account": account,
                         "credits_before": credits_before, "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        try:                                        # one line in the spend log: this paid print, tied to its set
            from . import providers as _PV
            if str(f.resolve()).startswith(str(Path(__file__).resolve().parents[3] / "runs")):     # a test's own folder is not logged
                _PV._spend().record("3d_jutsu_angles", str(generation), str(generation), f"runs/image-production/{brand}/sets/{slug(rid)}")
        except Exception:                           # noqa: BLE001  the print is already paid for: the log never stops it
            pass
    f.write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
    return r


def reopen(brand, rid, why):
    """Open a done request again so the next print round prints it (2026-11-21, brief-0380: ten requests were filed done
    on prints the checklist then sent back). Its set's kept prints are retired, never deleted (the note becomes
    "retired: <why> (was: <old note>)"), so a print that is not kept this time can never leave the old one as the picture.
    Returns the request."""
    if not str(why or "").strip():
        raise SystemExit("reopen needs the reason (what is wrong with the kept print)")
    f = home(brand) / f"{slug(rid)}.json"
    if not f.is_file():
        raise SystemExit(f"no set request {rid} for {brand}")
    r = json.loads(f.read_text())
    if r.get("printing"):
        raise SystemExit(f"{rid} is printing: read it back and file it first")
    set_name = r.get("set") or r["id"]
    sj = P.repo() / "runs" / "image-production" / brand / "sets" / set_name / "set.json"
    if sj.is_file():
        rec = json.loads(sj.read_text())
        for p in rec.get("prints") or []:
            if str(p.get("note", "")).startswith("kept"):
                p["note"] = f"retired: {why} (was: {p['note']})"
        sj.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    r.setdefault("reopened", []).append({"why": str(why), "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                         "was": {k: r.get(k) for k in ("state", "set", "done_at")}})
    r["state"] = "open"
    for k in ("set", "done_at"):
        r.pop(k, None)
    f.write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
    return r


def done(brand, rid, set_name):
    """Mark the request done with its filed set; returns the resume step (what to run so the waiting picture is made)."""
    f = home(brand) / f"{slug(rid)}.json"
    r = json.loads(f.read_text())
    from . import set_gate
    if set_gate.kept_print(brand, set_name) is None:
        raise SystemExit(f"{rid} stays open: set {set_name} has no kept print yet (file one with put --note \"kept: ...\"; a "
                         "print that is not right is filed without \"kept\" and printed again)")
    r.pop("printing", None)
    r.update(state="done", set=set_name, done_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    f.write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
    res = dict(r.get("resume") or {})
    if res.get("tool") == "style_chain":       # a style variant: run its ensure again (it adopts the kept print)
        res["command"] = res.get("command") or ("python3 components/video-production/styles/style_chain.py ensure-one "
                                                f"{res.get('brand')} {res.get('kind')} {res.get('id')} {res.get('style')}")
    if res.get("tool") == "make.py" and res.get("request"):
        req = dict(res["request"], set=set_name)
        rq = f.with_name(f"{r['id']}.resume-request.json")
        rq.write_text(json.dumps(req, indent=1, ensure_ascii=False, default=str) + "\n")
        res["command"] = f"python3 components/image-production/make.py --request {P.rel(rq)}"
    return res
