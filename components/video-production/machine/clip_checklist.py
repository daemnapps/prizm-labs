#!/usr/bin/env python3
"""The checklist before every paid clip (owner, 2026-11-20: "there literally should be a checklist for every single scene
and shot before it is generated").

Two lists the chain already had, now run on every clip call, taken prints included:

  1. THE PICTURE INVENTORY (THE-CHAIN.md, stages.json `video-production.pictures.checklist`): every picture a call
     sends — its start picture and each shot picture — answers the fourteen lines (framing, moment, people ours, skin
     marks, hands and bodies, light, look, outfit, place, product and props exact, continuity, nothing added, frame
     and safe zone, cards) through marketing-chain-checks `review.after_stage`, filed in <run>/qc-log/. Read once per
     picture's bytes and kept in clips/picture-inventory.json. Any ✗ (or a picture nobody could check) stops the call.
  2. THE MODEL'S INPUT SHEET (the Prompt Bench's checklist): every input the clip model's sheet lists
     (components/model-inputs/inputs/<model>.json), filled with what this call sends, plus the chain's own rows: each
     person in frame's casting sheets, each product's casting sheet and texture sheet, the props, the camera and
     motion plan, the brief's never-rules, the no-text and nothing-added lines. ✓ with what goes, ~ a note, ✗ stops.

Written to clips/checklists.json, one entry per call: {ok, rows: [{line, state, value}]}. The clip plan's problems
carry every ✗ (the live clip door refuses them), the clip gate reads the same file, the Studio shows it per call.
A dry run fills the sheet and leaves the inventory unread (said, never a pass). No brand, product or person is named.
The owner's acceptance of a picture's findings (clips/accepted.json, per run and per picture, in his words) turns them
into watch notes; a finding on a topic he kept gating (the product, by default) still stops the call.

    python3 clip_checklist.py <run> [--dry-run]
"""
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
OK, NOTE, NO = "✓", "~", "✗"
HEAD = "CHECKLIST"
INVENTORY_LINES = 14


def _load(name):
    spec = importlib.util.spec_from_file_location(f"vm_ck_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:20]


def pictures_of_call(run: Path, c: dict) -> list:
    """[(name, file)] — the call's start picture and shot pictures, in send order."""
    cp = _load("clips_plan")
    out = []
    start = cp.picture_file(run, c.get("start_frame")) if c.get("start_frame") else None
    if start:
        out.append((str(c["start_frame"]), Path(start)))
    for s in c.get("shot_pictures") or []:
        f = WS / str(s.get("file") or "")
        if f.is_file():
            out.append((f.stem, f))
    return out


NAMED_TEXT = re.compile(r"\b[A-Z0-9][A-Z0-9'&-]*(?:\s+[A-Z0-9][A-Z0-9'&-]*)+\b|\b[A-Z]{4,}(?:-[A-Z]+)?\b")


def brief_text(run: Path, name: str) -> list:
    """The words the brief itself puts in this picture's scene (a sign's name, a notice's wording, an on-screen card), in
    capitals as the brief writes them (21 Nov 2026: a "GRIND HOUSE" sign and a "RESHOOT IN 12 WEEKS" notice the brief
    names were failed as added text). The cast's own names (DRE, LOU) are not text. [] when none."""
    try:
        doc = _load("elements_check")._json_block((Path(run) / "brief.md").read_text())
    except Exception:  # noqa: BLE001
        return []
    sid = str(name).split("-")[0].split(".")[0].upper()
    sc = next((x for x in doc.get("scenes") or [] if str(x.get("id")).upper() == sid), None)
    if not sc:
        return []
    who = {str(c.get("id") or "").upper() for c in doc.get("cast") or []}
    who |= {w for c in who for w in c.split()}
    blob = json.dumps({k: sc.get(k) for k in ("on_screen", "first_frame", "shots", "props", "happens", "plate")},
                      ensure_ascii=False)
    for pl in (doc.get("world") or {}).get("places") or [] if isinstance(doc.get("world"), dict) else []:
        if isinstance(pl, dict) and str(pl.get("id") or "").upper() in blob.upper():
            blob += " " + json.dumps(pl, ensure_ascii=False)
    places = {str(x.get("setting_id") or "").upper() for x in doc.get("scenes") or []}
    places |= set(re.findall(r'"id":\s*"([A-Z][A-Z ]+)"', blob))           # a place's own id is a label, not text
    out = []
    for m in NAMED_TEXT.findall(blob):
        t = m.strip(" -'")
        if t and t not in who and t not in places and t not in out and not re.fullmatch(r"[SK]\d+(\.\d+)?", t):
            out.append(t)
    return out[:12]


def print_request(run: Path, name: str):
    """(request, its folder) of the 3D print a picture was taken from: the picture's paste record (`from_set`), its
    print sidecar's set folder, else the run's own request name for it. None when there is no such request."""
    run = Path(run)
    brand = str((_read(run / "run.json", {}) or {}).get("brand") or "")
    rdir = WS / "runs" / "image-production" / brand / "set-requests"
    cands = [str((_read(run / "media" / f"{name}.paste.json", {}) or {}).get("from_set") or "")]
    side = str((_read(run / "media" / f"{name}.png.print.json", {}) or {}).get("print") or "")
    if side:
        cands.append(Path(side).parent.name)
    cands.append(f"{run.name}-{name}")
    for c in cands:
        if not c:
            continue
        for f in (rdir / f"{c}.json", rdir / f"{c.lower()}.json"):
            r = _read(f, None)
            if isinstance(r, dict) and r.get("id"):
                return r, rdir
    return None


def sources_of(run: Path, name: str, most: int = 4) -> list:
    """What a picture was asked to be (the inventory's sources): its own words as the picture step sent them, then the
    reference pictures it was made from (its kept 3D print first, then the cast, props and product), from the run's
    batches. Without them the inventory judged a requested character or prop as "added" (20 Nov 2026)."""
    out, pics = [], []
    for b in sorted((Path(run) / "batches").glob("*.json")):
        d = _read(b, {}) or {}
        for it in (d if isinstance(d, list) else d.get("items") or []):
            if str(it.get("id")) != str(name):
                continue
            words = ((it.get("params") or {}).get("prompt") or "").strip()
            if words:
                out = ["What this picture was asked to show (its words): " + words[:1500]]
            for m in it.get("medias") or []:
                v = str(m.get("value") or "")
                if m.get("role") != "image_references" or not v:
                    continue
                f = Path(v) if Path(v).is_absolute() else WS / v
                if f.is_file() and str(f) not in pics:
                    pics.append(str(f))
    if not out and not pics:       # not in this pass's batches: what the picture record kept of what it was asked
        asked = ((_read(Path(run) / "direct.json", {}) or {}).get(name) or {}).get("asked") or {}
        if asked.get("prompt"):
            out = ["What this picture was asked to show (its words): " + str(asked["prompt"])[:1500]]
        pics = [r for r in asked.get("refs") or [] if Path(r).is_file()]
    side = _read(Path(run) / "media" / f"{name}.png.print.json", {}) or {}
    if side.get("print") and Path(side["print"]).is_file():
        pics = [side["print"]] + [x for x in pics if x != side["print"]]
    req = print_request(run, name)
    if req:                        # A PICTURE TAKEN FROM A KEPT 3D PRINT is judged against what its print was asked for
        r, rdir = req
        words = str(r.get("scene") or r.get("what") or "").strip()
        if words:
            out = ["What this picture was asked to show (its 3D print's full words): " + words[:3500]]
        if r.get("style"):
            out.append(f"Its style is the ad's style, {r['style']}: {r.get('style_formula') or ''}. A stylised 3D "
                       "animated picture in that style is correct; never call it photoreal for being detailed.")
        if r.get("cast"):
            out.append("Every person it is asked to show is on its reference board (faces on top, then each cast "
                       "member's headshot and look sheet): " + ", ".join(map(str, r["cast"])) + ". Those people, "
                       "their outfits, logos and marks as their sheets show them are asked for, never added.")
        for pr in r.get("products") or []:            # the kit's own label facts: what it never shows, the words it carries
            if not isinstance(pr, dict):
                continue
            what = pr.get("what") or pr.get("kit")
            words = [str(w) for w in pr.get("label_words") or [] if str(w).strip()]
            never = [str(x) for x in pr.get("never_show") or [] if str(x).strip()]
            if never or "label_words" in pr:
                out.append(f"{what}, by its kit: its printed words are " + (", ".join(words) if words else
                           "none on any face the picture shows: a plain unlabelled device is correct, never a missing "
                           "label") + (". Its kit never shows it: " + "; ".join(never[:16]) if never else "") + ".")
        for pr in r.get("products") or []:            # a product's holder is the kit's own rest (its cradle), never a guess
            rests = [str(x.get("how") or "") for x in (pr.get("rests") or []) if isinstance(x, dict) and x.get("how")] \
                if isinstance(pr, dict) else []
            if rests:
                # the rest rule is for the product set down; held in a hand it is the bare device (2026-11-21: a held
                # product was failed for not lying in its case, and a closed case for not being open)
                out.append(f"When it is set down, not held, {pr.get('what') or pr.get('kit')} rests, by its kit's own "
                           "rule, only like this: " + "; or ".join(rests) + ". That holder is correct as its kit shows "
                           "it, open or closed, with its own real marks. Held in a hand it is the bare device, no holder.")
        # the board the kept print was really made from (its set record), else the request's first board
        own = ""
        if side.get("print"):
            sp = Path(side["print"])
            row = next((x for x in (_read(sp.parent / "set.json", {}) or {}).get("prints") or []
                        if x.get("file") == sp.name), {}) or {}
            own = str(row.get("reference") or "")
        ref = (WS / own) if own and not Path(own).is_absolute() else Path(own) if own else None
        first = ref if ref is not None and ref.is_file() else rdir / f"{r['id']}-reference.png"
        boards = [str(f) for f in (first, rdir / f"{r['id']}-cast-board.png") if f.is_file()]
        head = pics[:1] if side.get("print") else []          # the kept print first, then the boards it was made from
        pics = head + boards + [x for x in pics if x not in head and x not in boards]
    named = brief_text(run, name)
    if named:                      # text the brief itself names is asked for, never "added" (spelled exactly)
        out = out + ["Words the brief itself names for this scene, allowed in the picture when spelled exactly as "
                     "written here: " + "; ".join(named) + "."]
    return out + pics[:most]


ACCEPTED = "accepted.json"


def acceptance(run: Path, name: str):
    """The owner's acceptance of one picture's inventory findings, per run and per picture, in his own words
    (<run>/clips/accepted.json): {"<picture>": {"words": "<what he said>", "by": "owner", "at": "<date>",
    "accepts": "<what he accepted>", "keep": ["product"], "lines": ["<a finding he accepted, as written>"]}}.
    A finding about a `keep` topic (default: the product) still gates; every other finding of that picture is a watch
    note carrying his words. None when the picture has no acceptance."""
    got = (_read(Path(run) / "clips" / ACCEPTED, {}) or {}).get(str(name))
    return got if isinstance(got, dict) and str(got.get("words") or "").strip() else None


def product_terms(run: Path, pids) -> list:
    """The words a finding uses for the call's products: each kit's id, its aliases and its `what`, plus "product"."""
    brand = str((_read(Path(run) / "run.json", {}) or {}).get("brand") or "")
    out = ["product"]
    for pid in pids or []:
        kit = _read(WS / "runs" / "ai-elements" / brand / "products" / str(pid) / "kit.json", {}) or {}
        out += [str(pid), str(pid).replace("-", " ")] + [str(a) for a in kit.get("aliases") or []]
        if kit.get("what"):
            out.append(str(kit["what"]))
    return [t.lower() for t in dict.fromkeys(out) if t.strip()]


def split_accepted(problems: list, acc: dict, terms: list, kinds: dict = None):
    """(still gating, accepted) — a finding whose judged kind (`kinds`: finding -> "product" | "people") is a kept kind
    stays and any other kind is accepted; an untagged finding that names a kept topic's words stays; a finding the owner
    accepted by its own text, or any other finding, is accepted."""
    keep = [str(k).lower() for k in (acc.get("keep") or ["product"])]
    words = list(terms) if "product" in keep else []
    words += [k for k in keep if k != "product"]
    lines = [str(x) for x in acc.get("lines") or [] if str(x).strip()]
    kinds = kinds or {}
    gating, accepted = [], []
    for p in problems:
        if any(x in p for x in lines):
            accepted.append(p)
        elif kinds.get(p) in ("product", "people"):
            (gating if kinds[p] in keep else accepted).append(p)
        elif any(re.search(r"\b" + re.escape(w) + r"\b", p.lower()) for w in words):
            gating.append(p)
        else:
            accepted.append(p)
    return gating, accepted


BODY = re.compile(r"\b(toes?|fingers?|thumbs?|hands?|arms?|forearms?|elbows?|wrists?|legs?|feet|foot|knees?|ankles?|"
                  r"shoulders?|armpits?|neck|limbs?|anatom\w*)\b", re.I)


KEEP = re.compile(r"\b(labels?|text|words?|letters?|lettering|logos?|brand\w*|products?|tubes?|wrong person|"
                  r"different (person|woman|man)|identity|outfit|look)\b", re.I)
STOP_WORDS = set("the a an and or of in on at to from with into onto over under its it is are was be this that these "
                 "those as by for not no never than then there their her his she he they them who which while".split())


def _content(text):
    return {w for w in re.findall(r"[a-z]{4,}", str(text).lower()) if w not in STOP_WORDS}


def planned_words(run: Path, name: str, sources: list) -> set:
    """The words the picture was made from: its 3D set request's words (direct.json `set`), else its sources' text."""
    rec = ((_read(Path(run) / "direct.json", {}) or {}).get(name) or {})
    text = " ".join(str(s) for s in sources if not str(s).endswith((".png", ".jpg", ".jpeg", ".webp")))
    if rec.get("set"):
        f = WS / "runs" / "image-production" / str((_read(Path(run) / "run.json", {}) or {}).get("brand") or "") \
            / "set-requests" / (str(rec["set"]) + ".json")
        text += " " + str((_read(f, {}) or {}).get("scene") or "")
    return _content(text)


def planned(problem: str, plan: set) -> bool:
    """A finding names at least two of the picture's own planned things (a cheap first look; `is_planned` asks)."""
    return len(_content(problem) & plan) >= 2


PLANNED_ASK = ("This picture was made on purpose from the PLANNED PICTURE below. A first reader listed the FINDINGS as "
               "faults. For each finding, decide only: is it the planned picture's own intended content (an object, a "
               "demonstration or a layout the plan asks for, read as a fault), or a real fault the plan does not ask "
               "for? Look at the picture. Answer with JSON only: {\"planned\": [the numbers of the findings that are the "
               "planned content]}.\n\nPLANNED PICTURE:\n%s\n\nFINDINGS:\n%s")


def is_planned(run: Path, name: str, picture: Path, problems: list, plan_text: str, ask=None) -> set:
    """The findings (by index) the judge reads as the picture's own planned content; empty when it cannot say."""
    if not problems or not plan_text.strip():
        return set()
    try:
        V = _load("v2_checks")
        model = _load("house").judge()
        text, _ = (ask or V.ask)(Path(run), "inventory-planned-" + name,
                                 PLANNED_ASK % (plan_text[:4000], "\n".join("%d. %s" % (i + 1, p) for i, p in enumerate(problems))),
                                 [Path(picture)], model=model)
        got = V.json_of(text) or {}
        return {int(i) - 1 for i in got.get("planned") or [] if str(i).isdigit()}
    except Exception:  # noqa: BLE001 -- no answer: nothing is called planned
        return set()


def plan_text_of(run: Path, name: str, sources: list) -> str:
    rec = ((_read(Path(run) / "direct.json", {}) or {}).get(name) or {})
    text = " ".join(str(s) for s in sources if not str(s).endswith((".png", ".jpg", ".jpeg", ".webp")))
    if rec.get("set"):
        f = WS / "runs" / "image-production" / str((_read(Path(run) / "run.json", {}) or {}).get("brand") or "") \
            / "set-requests" / (str(rec["set"]) + ".json")
        text += " " + str((_read(f, {}) or {}).get("scene") or "")
    return text.strip()


KIND_V = 2                        # the kind question's version: a new wording asks again
KIND_ASK = ("A reader listed the FINDINGS below about this picture. The advertised product is: %s. Tag each finding "
            "with its kind only. \"product\": it is about THAT advertised product's own appearance - its shape, size, "
            "colour, marks, label or wordmark, its own case or holder drawn wrong, or a way of holding it that its own "
            "rules forbid (pinched like a coin, held by its base like a handle, held backwards). \"people\": anything "
            "else - the people (who they are, faces, skin, outfits, pose, which hand holds what, hands open or closed), "
            "other props, other objects and characters and their markings, where anything is placed, or the place. "
            "Answer with JSON only: {\"kinds\": [\"product\" or \"people\", one per finding, in order]}.\n\n"
            "FINDINGS:\n%s")


def product_names(run: Path, name: str) -> str:
    """The advertised product(s) a picture's print was asked for, by kit name and aliases; a plain fallback when none."""
    req = print_request(run, name)
    prods = (req[0].get("products") if req else None) or []
    if not prods:                  # a picture whose own request names none: the run's product, from its other requests
        brand = str((_read(Path(run) / "run.json", {}) or {}).get("brand") or "")
        pre = re.sub(r"[^a-z0-9]+", "-", Path(run).name.lower()).strip("-")
        for f in sorted((WS / "runs" / "image-production" / brand / "set-requests").glob(pre + "-*.json")):
            prods += [x for x in (_read(f, {}) or {}).get("products") or [] if isinstance(x, dict)
                      and x.get("kit") not in {y.get("kit") for y in prods}]
    out = []
    for pr in prods:
        if isinstance(pr, dict):
            kit = _read(WS / "runs" / "ai-elements" / str((_read(Path(run) / "run.json", {}) or {}).get("brand") or "")
                        / "products" / str(pr.get("kit")) / "kit.json", {}) or {}
            names = [str(a).upper() for a in kit.get("aliases") or []] + [str(pr.get("what") or pr.get("kit"))]
            out.append(" / ".join(dict.fromkeys(n for n in names if n and n != "None")))
    return "; ".join(dict.fromkeys(out)) or "the advertised product"


def kinds_of(run: Path, name: str, picture: Path, problems: list, ask=None) -> dict:
    """{finding: "product" | "people"} as the judge tags them; {} when it cannot say (the word rule then decides)."""
    if not problems:
        return {}
    try:
        V = _load("v2_checks")
        model = _load("house").judge()
        text, _ = (ask or V.ask)(Path(run), "inventory-kinds-" + name,
                                 KIND_ASK % (product_names(run, name),
                                            "\n".join("%d. %s" % (i + 1, p) for i, p in enumerate(problems))),
                                 [Path(picture)], model=model)
        got = [str(k).lower() for k in (V.json_of(text) or {}).get("kinds") or []]
        return {p: k for p, k in zip(problems, got) if k in ("product", "people")} if len(got) == len(problems) else {}
    except Exception:  # noqa: BLE001 -- no answer: no kinds
        return {}


def inventory(run: Path, pics: list, review=None, body=None, plan_ask=None, kind_ask=None) -> dict:
    """{picture name: {sha, severity, problems}} — the fourteen-line inventory of each picture, read once per bytes."""
    store = Path(run) / "clips" / "picture-inventory.json"
    have = _read(store, {}) or {}
    # a picture this pass did not make is not in this pass's batches: its sources are the ones it was last read with
    src = {n: (sources_of(run, n) or (have.get(n) or {}).get("sources") or []) for n, _f in pics}
    key = {n: hashlib.sha256(json.dumps(src[n], sort_keys=True).encode()).hexdigest()[:16] for n in src}
    # a picture whose last reading did not happen (UNCHECKED) is asked again; only a real answer is kept
    todo = [(n, f) for n, f in pics if (have.get(n) or {}).get("sha") != _sha(f) or (have.get(n) or {}).get("src") != key[n]
            or (have.get(n) or {}).get("severity") == "UNCHECKED"]
    if todo:
        if review is None:
            q = str(WS / "components" / "marketing-chain-checks")
            if q not in sys.path:
                sys.path.insert(0, q)
            from marketing_chain_checks import review as R
            review = lambda items: R.after_stage("video-production", "pictures", run, items=items)  # noqa: E731
        res = review([{"id": n, "output": [str(f)], "compare": src[n]} for n, f in todo]) or {}
        for n, f in todo:
            v = res.get(n) if isinstance(res.get(n), dict) else {"severity": "UNCHECKED",
                                                                 "problems": ["the inventory did not answer"]}
            have[n] = {"sha": _sha(f), "src": key[n], "sources": src[n],
                       "severity": v.get("severity") or ("OK" if v.get("ok") else "UNCHECKED"),
                       "problems": [str(x) for x in v.get("problems") or []][:6]}
    # A BODY DEFECT IS CONFIRMED BEFORE IT STOPS A CLIP (2026-11-21, brief-0380 openings: the one-read inventory gave
    # clean 3D prints "six toes", "a melting hand", "a deformed armpit"): the chain's body check, read twice, must find
    # a body fault too; if it does not, the finding is a FIX on the fix list, not a stop. A stored reading is confirmed too.
    # Item by item (2026-11-21): the body items go to the body check; a set or physics item the judge reads as the
    # picture's own planned content (asked with the picture's own words: "a lotion streak across the clear wall") is a
    # FIX; anything else, and anything about a label, words, the product or who a person is, still stops.
    confirmed = False
    for n, f in pics:
        v = have.get(n) or {}
        if v.get("severity") != "BLOCKER" or "confirmed" in v or v.get("sha") != _sha(f) or not v.get("problems"):
            continue
        bodies = [p for p in v["problems"] if BODY.search(p) and not KEEP.search(p)]
        ok = (body or _load("body_check").check)(run, f) if bodies else {"ok": True}
        v["body_check"] = {"ok": bool(ok.get("ok")), "problems": [str(x) for x in ok.get("problems") or []][:4]}
        others = [p for p in v["problems"] if p not in bodies and not KEEP.search(p)]
        meant = {others[i] for i in (plan_ask or is_planned)(run, n, f, others, plan_text_of(run, n, v.get("sources") or []))
                 if 0 <= i < len(others)} if others else set()
        rows, stop = [], False
        for p in v["problems"]:
            if p in bodies and ok.get("ok"):
                rows.append("not confirmed by the body check (two reads): " + p)
            elif p in meant:
                rows.append("the picture's own planned moment, not a fault: " + p)
            else:
                rows.append(p)
                stop = True
        v["problems"], v["confirmed"] = rows, True
        if not stop:
            v["severity"] = "FIX"
        confirmed = True
    # THE KIND OF EACH FINDING, WHERE THE OWNER ACCEPTED KINDS FOR THIS RUN (2026-11-21: "FLEX in his left hand" and
    # "holding the FLEX instead of hands open" are pose findings that name the product): the judge tags each finding
    # product or people once per reading; the run's acceptance then gates on the kind, not on a word
    for n, f in pics:
        v = have.get(n) or {}
        probs = [str(x) for x in v.get("problems") or []]
        if not probs or v.get("sha") != _sha(f) or not acceptance(run, n) or (
                set(v.get("kinds") or {}) == set(probs) and v.get("kinds_v") == KIND_V):
            continue
        v["kinds"], v["kinds_v"] = (kind_ask or kinds_of)(run, n, f, probs), KIND_V
        confirmed = True
    if todo or confirmed:
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps(have, indent=1, ensure_ascii=False) + "\n")
    return have


def sheet_inputs(run: Path) -> list:
    """The clip model's own input sheet rows (model-inputs)."""
    model = "seedance-2.5"
    try:
        model = _load("clip_refs").model_of(WS, run)
    except Exception:  # noqa: BLE001
        pass
    d = _read(WS / "components" / "model-inputs" / "inputs" / f"{model}.json", {}) or {}
    rows = d.get("inputs") or []
    if isinstance(rows, dict):          # a sheet written as {input: what it is} (minimax-h3): the same rows, by name
        rows = [{"name": k, "what": v} for k, v in rows.items()]
    return [r for r in rows if isinstance(r, dict)]


def body_lines(run: Path, c: dict, prompt: str, cr) -> tuple:
    """([the call's lines that use a product on a part it is ruled out for], what was checked): components/naming/body.py."""
    sys.path.append(str(WS / "components" / "naming"))
    import body
    brand = str((_read(Path(run) / "run.json", {}) or {}).get("brand") or "")
    bad, seen = [], []
    for pid in cr.product_ids(run, c, WS):
        if body.members(brand, pid):
            seen.append(pid)
            bad += body.problems(brand, pid, prompt)
    return bad, ("checked against the Body Map: " + ", ".join(seen)) if seen else ""


def rows_for(run: Path, c: dict, inv: dict, dry: bool) -> list:
    """Every line of one call's checklist."""
    cr = _load("clip_refs")
    rules = _load("clip_rules")
    rows = []

    def row(line, state, value=""):
        rows.append({"line": line, "state": state, "value": str(value)[:240]})

    prompt = c.get("prompt") or ""
    refs = [str(r.get("file") or "") for r in c.get("image_refs") or []]
    talking = bool(c.get("talking"))
    sb = _read(Path(run) / "storyboard.json", {}) or {}
    long_take = bool(sb.get("picture_only") and talking)
    # the model's sheet, row by row
    names = [str(i.get("name") or "") for i in sheet_inputs(run)]
    pics = pictures_of_call(run, c)
    for name in names:
        n = name.lower()
        if n.startswith("prompt"):
            row("prompt", OK if len(prompt.split()) > 20 else NO, f"{len(prompt.split())} words")
        elif n.startswith("image (first frame)"):
            row("image (first frame)", OK if pics and pics[0][0] == str(c.get("start_frame")) else NO,
                c.get("start_frame") or "no start picture")
        elif n.startswith("image (other roles)"):
            row("image (other roles)", OK if (refs or c.get("shot_pictures")) else NOTE,   # who and what: rows below
                f"{len(c.get('shot_pictures') or [])} shot picture(s), {len(refs)} reference(s)")
        elif n.startswith("image (last frame)"):
            row("image (last frame)", OK, c.get("end_frame") or "not used: no last frame on this call")
        elif n.startswith("video (reference)"):
            vids = [v for v in c.get("refs") or [] if v.get("file")]
            missing = [v["file"] for v in vids if not (Path(run) / v["file"]).is_file() and not (WS / v["file"]).is_file()]
            row("video (reference)", NO if missing else OK,
                ("missing: " + ", ".join(missing)) if missing else (f"{len(vids)} movement video(s)" if vids else "none"))
        elif n.startswith("audio (reference)"):
            row("audio (reference)", OK if (not talking or c.get("voice_parts")) else NO,
                "the scene's locked read" if talking else "not used: a silent clip")
        elif n.startswith("duration"):
            sec = float(c.get("seconds") or c.get("duration") or 0)
            row("duration", OK if 4 <= sec <= 30 or (sec and talking) else NOTE, f"{sec} s")
        elif n.startswith("generate_audio"):
            row("generate_audio", OK, "on (talking)" if talking else "off (silent)")
    # the chain's own rows: who and what is in the shot goes as its casting files
    have = set(refs)
    for who in c.get("people") or []:
        want = [r["file"] for r in cr.person_refs(run, {"people": [who]}, WS)]
        if not want:
            row(f"person · {who}", NOTE, "no casting sheets banked")
        elif long_take or c.get("render"):
            row(f"person · {who}", OK, "carried by the start picture (a talking long take)" if long_take
                else "not in a render")
        else:
            gone = [w for w in want if w not in have]
            row(f"person · {who}", NO if gone else OK, ("missing: " + ", ".join(Path(g).name for g in gone)) if gone
                else ", ".join(Path(w).name for w in want))
    for pid in cr.product_ids(run, c, WS):
        model = WS / "runs" / "ai-elements" / str(cr.brand_of(run)) / "products" / pid / "model"
        sheet = model / "product-sheet.png"
        tex = cr.texture_sheet(model, pid)
        for label, f in (("casting sheet", sheet), ("texture sheet", tex)):
            if f is None or not Path(f).is_file():
                row(f"product · {pid} · {label}", NOTE, "none banked")
                continue
            rel = str(Path(f).resolve().relative_to(WS.resolve()))
            row(f"product · {pid} · {label}", OK if rel in have else NO, Path(f).name if rel in have else "not sent")
    # THE REAL PRODUCT, PASTED (owner, 2026-11-20: invented labels on every drawn product): every picture this call sends,
    # for every product the call uses, carries a paste record for its current bytes (take_prints.paste_products, or the
    # still step's own paste in direct.json) — the label is then the real one, never drawn
    pids = list(cr.product_ids(run, c, WS))
    made = _read(Path(run) / "direct.json", {}) or {}
    try:   # AN IN-LOOK PIECE (V58, product_route.py): the product is made inside the picture in the film's own style from
        #     its 3D build; a real photograph pasted on would break the look, so there is no paste to ask for
        in_look = _load("product_route").in_look(None, run)
    except Exception:  # noqa: BLE001
        in_look = False
    if in_look and pids:
        for name, _f in pics:
            row(f"real product · {name}", NOTE, "in-look piece: the product is made in the film's style from its 3D build (V58), never pasted")
        pids = []
    for name, f in pics:
        if not pids:
            break
        rec = _read(Path(f).parent / f"{Path(f).stem}.paste.json", {}) or {}
        own = (made.get(name) or {}).get("product_paste") or {}
        # A KEPT IMAGE-PRODUCTION PRINT MADE WITH THE PRODUCT'S CASTING SHEET IS THE REAL PRODUCT (owner, 2026-11-20:
        # "Of course it goes through image production."): the picture was taken from a kept 3D set print whose request
        # carried the product's kit, so its label and shape come from the casting sheet, not a paste
        taken = made.get(name) or {}
        printed = set()
        if taken.get("door") == "3d-print" and taken.get("record"):
            sj = WS / str(taken["record"])
            sset = sj.parent.name
            req = _read(sj.parent.parent.parent / "set-requests" / f"{sset}.json", {}) or {}
            kept = [x for x in (_read(sj, {}) or {}).get("prints") or [] if str(x.get("note", "")).startswith("kept")]
            if kept and str(taken.get("taken_from", "")).endswith(kept[-1].get("file", "")):
                printed = {str(k.get("kit") if isinstance(k, dict) else k) for k in req.get("products") or []}
        if pids and all(pid in printed for pid in pids):
            for pid in pids:
                row(f"real product · {pid} · {name}", OK, "kept image-production print made with its casting sheet")
            continue
        if rec.get("picture_sha") == hashlib.sha256(Path(f).read_bytes()).hexdigest():
            res = rec.get("products") or {}
            for pid in pids:
                r = res.get(pid) or {}
                if r.get("ok") and not r.get("skipped"):
                    row(f"real product · {pid} · {name}", OK, f"pasted at {r.get('angle')}°")
                elif r.get("skipped"):
                    row(f"real product · {pid} · {name}", NOTE, str(r["skipped"]))
                else:
                    row(f"real product · {pid} · {name}", NO, "; ".join(map(str, r.get("why") or ["not pasted"]))[:160])
        elif own.get("ok"):
            row(f"real product · {name}", OK, f"pasted by the still step at {own.get('angle')}°")
        else:
            row(f"real product · {name}", NO, "no paste of the real product on this picture (take_prints.py --paste)")
    try:
        loose = cr.named_products(run, c, WS)[1]
    except Exception:  # noqa: BLE001
        loose = []
    if loose:
        row("product words named", NO, "no banked product called " + ", ".join(loose))
    props = [r["file"] for r in cr.prop_refs(run, c, WS)]
    if props:
        gone = [p for p in props if p not in have]
        row("props in the scene", NOTE if gone else OK,
            (f"{len(props) - len(gone)} of {len(props)} sent") if gone else f"{len(props)} sent")
    # the prompt's own lines
    row("camera and motion plan", OK if "CAMERA AND MOTION" in prompt else NO,
        "in the prompt" if "CAMERA AND MOTION" in prompt else "missing")
    nev = rules.never_rules(run)
    if c.get("render"):
        row("the brief's never-rules", NOTE, "a render: no person or product, so the brief's never-rules stay off it")
    else:
        row("the brief's never-rules", OK if (not nev or rules.NEVER_MARK in prompt) else NO,
            f"{len(nev)} rule(s) in the prompt" if nev else "the brief writes none")
    bad, told = body_lines(run, c, prompt, cr)
    if bad or told:
        row("where on the body", NO if bad else OK, "; ".join(bad) or told)
    row("no words on screen", OK if rules.NO_TEXT_MARK in prompt else NO, "")
    row("nothing added", OK if rules.NO_ADD_MARK in prompt else NO, "")
    # the picture inventory, per picture
    try:
        terms = product_terms(run, cr.product_ids(run, c, WS))
    except Exception:  # noqa: BLE001
        terms = ["product"]
    for name, f in pics:
        v = inv.get(name)
        acc = acceptance(run, name)
        if dry and not v:
            row(f"picture inventory · {name}", NOTE, "not read in a dry run")
        elif not v or v.get("sha") != _sha(f):
            row(f"picture inventory · {name}", NO, "not inventoried")
        elif acc and v.get("severity") in ("FIX", "BLOCKER"):
            # THE OWNER'S ACCEPTANCE (clips/accepted.json): what he accepted is a watch note with his words; a finding
            # on a topic he kept (the product, by default) still stops the call
            gating, ok = split_accepted([str(x) for x in v.get("problems") or []], acc, terms, v.get("kinds"))
            if gating:
                row(f"picture inventory · {name}", NO, f"{v['severity']} (kept by the owner): " + "; ".join(gating)[:200])
            else:
                row(f"picture inventory · {name}", NOTE, f"accepted by the {acc.get('by') or 'owner'} "
                    f"(\"{str(acc['words'])[:80]}\"): " + "; ".join(ok)[:150])
        elif v.get("severity") == "FIX":
            # SMALL MISS, SMALL FIX (owner, 2026-11-21: "we have to remove a lot of these checks", "whatever is not good,
            # we'll identify it clearly and then make the adjustments"): a FIX finding goes on the clip's fix list and
            # never stops the paid run; only a BLOCKER (wrong person or outfit, wrong product, a deformed body, an
            # invented product) or an unread picture stops it
            row(f"picture inventory · {name}", NOTE, "FIX (on the fix list): " + "; ".join(v.get("problems") or [])[:200])
        elif v.get("severity") in ("BLOCKER", "UNCHECKED"):
            row(f"picture inventory · {name}", NO, f"{v['severity']}: " + "; ".join(v.get("problems") or [])[:200])
        else:
            row(f"picture inventory · {name}", OK, f"{INVENTORY_LINES} lines answered")
    return rows


def build(run: Path, dry: bool = False, files=("plan.json",), review=None, kind_ask=None) -> list:
    """Fill every call's checklist; every ✗ goes into the plan's problems. Returns the ✗ lines."""
    run = Path(run)
    out = {}
    bad = []
    fix_list = {}
    for name in files:
        f = run / "clips" / name
        res = _read(f, None)
        if not isinstance(res, dict) or not res.get("calls"):
            continue
        pics = []
        for c in res["calls"]:
            pics += [p for p in pictures_of_call(run, c) if p[0] not in {x[0] for x in pics}]
        try:
            inv = {} if dry else inventory(run, pics, review=review, kind_ask=kind_ask)
        except Exception as e:  # noqa: BLE001 -- an inventory that cannot run leaves every picture unchecked
            inv = {}
            print(f"{HEAD}: the picture inventory did not run ({type(e).__name__}: {str(e)[:160]})", file=sys.stderr)
        probs = [p for p in res.get("problems") or [] if not str(p).startswith(HEAD)]
        for c in res["calls"]:
            rows = rows_for(run, c, inv, dry)
            ok = not any(r["state"] == NO for r in rows)
            fixes = [{"picture": r["line"].split(" · ", 1)[-1], "fix": r["value"].split(": ", 1)[-1]}
                     for r in rows if r["state"] == NOTE and str(r["value"]).startswith("FIX (on the fix list)")]
            out[c["id"]] = {"ok": ok, "rows": rows, "fixes": fixes}
            if fixes:
                fix_list[c["id"]] = {"scenes": c.get("scenes") or [], "fixes": fixes}
            for r in rows:
                if r["state"] == NO:
                    line = f"{HEAD}: {c['id']} ✗ {r['line']}" + (f" — {r['value']}" if r["value"] else "")
                    probs.append(line)
                    bad.append(line)
        res["problems"] = probs
        f.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    (run / "clips").mkdir(parents=True, exist_ok=True)
    (run / "clips" / "checklists.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    # the fix list: every FIX finding by call, read by the Studio and carried into the cut (edit/EDIT.json `fixes`)
    (run / "clips" / "fixes.json").write_text(json.dumps(fix_list, indent=1, ensure_ascii=False) + "\n")
    return bad


def passed(run: Path, cid: str):
    """(ok, why) — the clip gate's read of a call's checklist."""
    got = (_read(Path(run) / "clips" / "checklists.json", {}) or {}).get(cid)
    if not got:
        return False, "no checklist filled for this call (clip_checklist.py)"
    bad = [r["line"] for r in got.get("rows") or [] if r.get("state") == NO]
    return (not bad), ("✗ " + "; ✗ ".join(bad)) if bad else ""


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    bad = build(Path(a.run), dry=a.dry_run)
    for b in bad:
        print(b)
    print(f"{len(bad)} ✗ — {Path(a.run) / 'clips' / 'checklists.json'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
