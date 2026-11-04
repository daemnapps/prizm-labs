#!/usr/bin/env python3
"""VIDEO PRODUCTION v2 — the same machine as run.py, with v2's rules on top.

v1 (run.py) stays the default and is not changed. This file loads run.py and
swaps in v2's versions of five steps, so the gates, the brief checks and the
doors are exactly v1's:

  1. picture checks    one direct API call each (v2_checks.py), no Claude
                       session, no prompt cache; an unchanged picture or voice
                       take is answered from memory, never checked again
  2. safe area         the 4:5 rule is a labelled slot at the TOP of every
                       frame prompt; v1's conflicting "10-90% height" is cut;
                       no paid repair edit
  3. pictures          made side by side (v2.json pictures.parallel), in
                       waves — a frame that edits another waits for it
  4. one reviewer      sees the brief's scene, the banked cast LOOK and the
                       packshot; every problem in one list; a SEND_BACK is
                       remade from the picture itself; at most 2 rounds
  5. style by name     the look is the style list's formula, by the brief's
                       style_id, verbatim — never a freshly written sentence
  6. clips             ONE take of every clip at 480p on Seedance 2.5, scored by the
                       clip judge; another only if it fails, three at most; none
                       passing = the best attempt is kept and flagged below criteria (VIDEO-RULINGS V34)
  7. ledger            checks, voice, voice checks and repairs all logged
  8. the order         voice first (three reads of every line, one locked) →
                       the storyboard → only the pictures it lists (ONE of
                       each since 2026-10-24) → the clips (VIDEO-RULINGS V7)

Use exactly like run.py:  python3 machine/run_v2.py start <brief> --brand ... --label ...
                          (no --voice-only / --storyboard / --clips: the four steps run in order)
Clips:                    python3 machine/run_v2.py clips <run> [--only ...] [--yes]
Config: machine/v2.json.
"""
from __future__ import annotations

import concurrent.futures as cf
import importlib.util
import json
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "v2.json").read_text())
LOCK = threading.RLock()
CHECK_TIMES: dict = {"pictures_s": 0.0, "review_s": 0.0}


def _mod(name: str, as_name: str):
    sp = importlib.util.spec_from_file_location(as_name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


R = _mod("run", "vm_run_v2base")
V = _mod("v2_checks", "vm_v2_checks")
WS = R.WS
_orig_hand = R.run_machine_hand
_orig_load = R._load


# ------------------------------------------------------------ thread safety

def _locked(fn):
    def w(*a, **kw):
        with LOCK:
            return fn(*a, **kw)
    return w


R.write_json = _locked(R.write_json)
R.preflight.ledger = _locked(R.preflight.ledger)
R.preflight.verdict = _locked(R.preflight.verdict)


# ------------------------------------------------------------ 5 · style by name

def style_formula(style_id: str | None):
    if not style_id:
        return None
    bank = json.loads((WS / CFG["style"]["bank"]).read_text())
    for r in bank.get("rows") or []:
        if style_id in (r.get("id"), r.get("name")) or style_id in (r.get("aliases") or []):
            f = (r.get("extra") or {}).get("formula")
            if f:
                return r.get("name"), f
    return None


def piece_of(run: Path) -> dict:
    plan = R.read_json(run / "plan.json", {}) or {}
    piece = dict(plan.get("piece") or {})
    src = (R.read_json(run / "run.json", {}) or {}).get("brief_from")
    if src and Path(src).is_file():                    # the brief's own piece block carries style_id
        m = re.search(r"```json\s*(\{.*?\})\s*```", Path(src).read_text(), re.S)
        try:
            bp = (json.loads(m.group(1)).get("piece") or {}) if m else {}
            piece = {**bp, **{k: v for k, v in piece.items() if v}, "styles_written": [x for x in (bp.get("style"), piece.get("style")) if x]}
        except Exception:                               # noqa: BLE001
            pass
    return piece


# ------------------------------------------------------------ 2 · the safe-area slot

STRIP = re.compile(CFG["safe_area"]["strip"])


def v2_prompt(prompt: str, piece: dict, frame: bool, swipe_edit: bool = False, extra: str = "") -> str:
    """The picture prompt as v2 sends it. A SWIPE-EDIT frame (element_refs SWIPE_EDIT: "keep … exactly as image 1")
    carries the change only — no safe-area slot, no look formula (P33, CHANGES.md C11). Any other frame: the look
    by name and the safe-area slot first, then `extra` (life marks, the realism rows) at the end."""
    if swipe_edit:
        return re.sub(r"[ \t]{2,}", " ", prompt).strip()
    out = prompt
    sf = style_formula(piece.get("style_id"))
    if sf:
        name, formula = sf
        look = f"LOOK (style list: {name}): {formula}."
        for old in piece.get("styles_written") or [piece.get("style") or ""]:   # every freshly written look sentence goes
            if old.strip():
                out = out.replace(old.strip(), "")
        out = out.replace("The look, exactly: " + formula + ". Hold this look in every picture.", "")
        out = look + "\n" + out
    if frame:
        out = STRIP.sub("", out)
        out = re.sub(r",\s*\.", ".", out)
        out = CFG["safe_area"]["slot"] + "\n" + out
    if extra and extra not in out:
        out = out.rstrip() + " " + extra
    return re.sub(r"[ \t]{2,}", " ", out).strip()


# ------------------------------------------------------------ the person and the realism rows (P36, P37)

def _oc():
    return R._load("clips_run")


def picture_extra(run: Path, it: dict, piece: dict) -> str:
    """The life marks of every person in the picture's scene (their character.md, P36) and the realism index's
    picture rows for the piece (P37) — the small real things a picture carries."""
    oc = _oc()
    plan = R.read_json(run / "plan.json", {}) or {}
    sc = next((s for s in plan.get("scenes") or [] if s.get("id") == it.get("for")), None) or {}
    els = R.read_json(run / "elements.json", {}) or {}
    said = " ".join(str(sc.get(k) or "") for k in ("who", "happens")) + " " + " ".join((sc.get("looks") or {}).keys())
    out = []
    # VIDEO SPICE (VIDEO-SPICE.md, V9; verify 2026-10-21 row 19): life marks are layer 3 (level 2 and up); the realism
    # rows go up to the piece's level; no level named = every layer, realism level 2, as before
    level = oc.spice_level_of(run)
    layers = oc.spice_layers(level)
    for e in els.get("items") or []:
        if layers is not None and 3 not in layers:
            break
        if e.get("kind") != "person" or not e.get("folder") or not re.search(rf"\b{re.escape(str(e.get('id')))}\b", said):
            continue
        lm = oc.life_marks(WS / e["folder"])
        if lm.get("marks"):
            out.append(f"{e['id']}'s life marks, as real as the references show them: {lm['marks']}.")
    # the format is the brief's, else read off the scene and its camera — never every format's rows (row 19)
    fmt = piece.get("realism_format") or oc.realism_format_of(sc, oc.camera_kind([], sc))
    rows = oc.realism_rows(fmt, oc.PICTURE_FAMILIES, sc.get("realism") or piece.get("realism"), level=int(level or 2))
    if rows:
        out.append(" ".join(r["prompt"].strip().rstrip(".") + "." for r in rows[:4]))
    return " ".join(out)


# ------------------------------------------------------------ 3 · pictures side by side

def _deps(it: dict, ids: set) -> set:
    d = {str(m.get("value")) for m in it.get("medias") or [] if str(m.get("value")) in ids}
    for k in ("edit_of", "start_frame"):
        if str(it.get(k) or "") in ids:
            d.add(str(it[k]))
    if f"{it.get('id')}-still" in ids:
        d.add(f"{it.get('id')}-still")
    d.discard(str(it.get("id")))
    return d


def _waves(items: list) -> list:
    ids = {str(i.get("id")) for i in items}
    left, done, waves = list(items), set(), []
    while left:
        wave = [i for i in left if _deps(i, ids) <= done]
        if not wave:                                     # a loop — fall back to one at a time
            wave = [left[0]]
        waves.append(wave)
        done |= {str(i.get("id")) for i in wave}
        left = [i for i in left if str(i.get("id")) not in done]
    return waves


def _pinned(it: dict, manifest: dict) -> dict:
    """Same-batch references named by id → the file already made."""
    it = json.loads(json.dumps(it))
    for m in it.get("medias") or []:
        f = (manifest.get(str(m.get("value"))) or {}).get("file")
        if f:
            m["value"] = str(f)
    sf = (manifest.get(str(it.get("start_frame") or "")) or {}).get("file")
    if sf:
        it.setdefault("medias", []).insert(0, {"role": "start_image", "value": str(sf)})
    return it


def _versioned(it: dict) -> bool:
    """A start picture the storyboard listed — made as three versions, the best kept (P10). A packshot edit is the
    brand's real photograph, never versioned."""
    return it.get("kind") in ("still", "edit") and R.safezone.is_frame(it) and not it.get("packshot")


def _problems(run: Path, it: dict, f: Path, refs: list, piece: dict, job: str) -> tuple[int, list]:
    look = (style_formula(piece.get("style_id")) or ("", piece.get("style") or ""))[1]
    prompt = REVIEW_PROMPT.replace("{brief}", _scene_words(run, it)).replace("{look}", look)
    try:
        text, _info = V.ask(run, job, prompt, [f] + refs, model=V.model_of(CFG["checks"]["review_model"]))
    except Exception as e:                              # noqa: BLE001 — an unchecked version is never kept first
        return 99, [{"what": f"not checked: {e}"[:200]}]
    ans = V.json_of(text) or {}
    probs = ans.get("problems") or []
    return (len(probs) if ans.get("verdict") else 99), probs


# PICTURES IN FLIGHT (P53): every version of every picture shares one cap; a 429 is the door's own wait / overflow
IN_FLIGHT = threading.BoundedSemaphore(int((CFG.get("pictures") or {}).get("in_flight") or 12))


def _slot(fn, *a, **kw):
    with IN_FLIGHT:
        return fn(*a, **kw)


def _alt(it: dict, k: int, manifest: dict, run: Path, brand, kw: dict):
    """Version k of a start picture, made from the same prompt and references — (k, file) or (k, None)."""
    iid = str(it["id"])
    alt = _pinned(it, manifest)
    alt["id"] = f"{iid}-pick{k}"
    try:
        g2 = _slot(_orig_hand, [alt], run, False, brand=brand, **kw)
    except (Exception, SystemExit) as e:                # noqa: BLE001 — a version that failed is one fewer to pick from
        print(f"  {iid}: version {k} not made — {str(e)[:160]}")
        return k, None
    fk = (g2.get(alt["id"]) or {}).get("file")
    if not (fk and Path(fk).is_file()):
        return k, None
    vdir = run / "media" / "versions"
    vdir.mkdir(parents=True, exist_ok=True)
    dest = vdir / f"{iid}-pick-v{k}{Path(fk).suffix}"
    shutil.move(str(fk), dest)
    _fg = _orig_load("face_gate")
    if _fg.sidecar(fk).is_file():                       # the version's face record travels with its bytes
        shutil.move(str(_fg.sidecar(fk)), _fg.sidecar(dest))
    return k, dest


def _three(it: dict, got: dict, manifest: dict, run: Path, brand, piece: dict, n: int, kw: dict, alts=None) -> None:
    """THREE CLEAN VERSIONS OF A START PICTURE, THE BEST KEPT (the owner, 2026-10-20: "a clean 3 versions of each element
    so we isolate consistency instead of volume"). The picture already made is version 1; versions 2..n are made from
    the same prompt and references — side by side with version 1 (P53: `alts`, the futures v2_hand started) — and all
    of them are checked by the one reviewer side by side; the one with the fewest problems becomes the picture (the
    earliest version on a tie). Every version stays in media/versions/; picture-picks.json says which won."""
    iid = str(it["id"])
    f = Path(got[iid]["file"])
    vdir = run / "media" / "versions"
    vdir.mkdir(parents=True, exist_ok=True)
    v1 = vdir / f"{iid}-pick-v1{f.suffix}"
    shutil.copy2(f, v1)
    made = [x.result() for x in alts.values()] if alts else [_alt(it, k, manifest, run, brand, kw) for k in range(2, n + 1)]
    cands = [(1, v1)] + sorted((k, fk) for k, fk in made if fk)
    refs = _refs_of(run, it, brand)
    with cf.ThreadPoolExecutor(max_workers=max(1, len(cands))) as ex:
        checked = list(ex.map(lambda c: _problems(run, it, c[1], refs, piece, f"{iid}-v2-pick-{c[0]}"), cands))
    # THE FACE FIRST (2026-10-24: S4 kept the version with a different man in Marcus's chair over two versions whose
    # faces passed, because it had fewer other problems): a version whose people failed the face gate ranks after
    # every version that passed; a version with no face record (nobody of ours in it) is not held back by it
    FG = _orig_load("face_gate")
    if FG.read(f) is not None:
        shutil.copy2(FG.sidecar(f), FG.sidecar(v1))
    face = {k: ((FG.read(fk) or {"pass": True}).get("pass") is True) for k, fk in cands}
    scored = [{"version": k, "file": str(fk.relative_to(run)), "problems": n_p, "what": probs, "face_pass": face[k]}
              for (k, fk), (n_p, probs) in zip(cands, checked)]
    best = min(scored, key=lambda x: (not x["face_pass"], x["problems"], x["version"]))
    shutil.copy2(run / best["file"], f)
    if FG.sidecar(run / best["file"]).is_file():
        shutil.copy2(FG.sidecar(run / best["file"]), FG.sidecar(f))
    with LOCK:
        rec = R.read_json(run / "picture-picks.json", {}) or {}
        rec[iid] = {"kept": best["version"], "versions": scored, "at": V.now()}
        R.write_json(run / "picture-picks.json", rec)
    print(f"  {iid}: {len(cands)} versions — version {best['version']} kept ({best['problems']} problem(s)"
          f"{'' if best['face_pass'] else '; NO version passed the face gate — held'})")


def v2_hand(items, run, dry_run, brand=None, **kw):
    if not items:
        return {}
    piece = piece_of(run)
    items = [json.loads(json.dumps(it)) for it in items]
    for it in items:
        p = it.get("params") or {}
        if p.get("prompt") and it.get("kind") in ("still", "edit", "restyle", "cast"):
            sw = bool(it.get("swipe_edit")) or (str(piece.get("frames") or "").lower() == "swipe-edit"
                                                 and it.get("kind") == "edit")
            sw = sw or bool(it.get("in_use"))    # a product-in-use still is the plain way: no house layers (2026-10-25)
            extra = "" if sw or it.get("kind") == "cast" else picture_extra(run, it, piece)
            p["prompt"] = v2_prompt(p["prompt"], piece, R.safezone.is_frame(it), swipe_edit=sw, extra=extra)
    versions = max(1, int((CFG.get("pictures") or {}).get("versions") or 1))
    if dry_run:
        n_frames = sum(1 for it in items if _versioned(it))
        if versions > 1 and n_frames:
            print(f"v2 · {n_frames} start picture(s) × {versions} versions each — every version checked by the "
                  f"one reviewer, the best kept (VIDEO-RULINGS V5)")
        return _orig_hand(items, run, dry_run, brand=brand, **kw)
    manifest: dict = {}
    t0 = time.time()
    real_rsb = R.record_subject_boxes
    R.record_subject_boxes = lambda *a, **k: None        # once, at the end, over the whole manifest
    try:
        for wave in _waves(items):
            def one(it):
                # versions 2..n start NOW, side by side with version 1 (P53)
                ex2 = alts = None
                if versions > 1 and _versioned(it):
                    ex2 = cf.ThreadPoolExecutor(max_workers=versions - 1)
                    alts = {k: ex2.submit(_alt, it, k, manifest, run, brand, kw) for k in range(2, versions + 1)}
                try:
                    got = _slot(_orig_hand, [_pinned(it, manifest)], run, False, brand=brand, **kw)
                    if it.get("edit_of") and got.get(str(it["id"])):   # colour-hold an edit to its source
                        src = (manifest.get(str(it["edit_of"])) or {}).get("file")
                        if src:
                            R._load("colour_match").match_file(got[str(it["id"])]["file"], src)
                    if alts is not None and got.get(str(it["id"])):
                        # THREE VERSIONS, THE BEST KEPT (P10, VIDEO-RULINGS V5) — before anything is built on it, so a
                        # last frame or a set-up edits the picture that was kept
                        _three(it, got, manifest, run, brand, piece, versions, kw, alts=alts)
                finally:
                    if ex2 is not None:
                        ex2.shutdown(wait=True)
                return got
            with cf.ThreadPoolExecutor(max_workers=int(CFG["pictures"]["parallel"])) as ex:
                for got in ex.map(one, wave):
                    manifest.update(got)
            print(f"v2 · wave of {len(wave)} made side by side", flush=True)
    finally:
        R.record_subject_boxes = real_rsb
    old = R.read_json(run / "direct.json", {}) or {}
    R.write_json(run / "direct.json", {**old, **manifest})
    R.record_subject_boxes(run, items, manifest)
    CHECK_TIMES["pictures_s"] += time.time() - t0
    return manifest


# ------------------------------------------------------------ 1+2 · the zone check, no repair

def v2_zone_gate(it, file_, refs, manifest, run, brand, zone_caller, *a, **kw):
    iid = str(it.get("id"))
    z = R.safezone.check(file_, caller=V.zone_caller(run, iid))
    if z["verdict"] == "FAIL":
        # v1 paid a repair edit here (16% worked). v2 hands the miss to the one reviewer's list.
        print(f"  {iid}: subject zone — {', '.join(z.get('outside') or [])} outside the 4:5 zone → to the reviewer's list")
        z = {**z, "verdict": "REVIEW", "why": "outside the 4:5 zone — in the v2 reviewer's one list"}
    R.preflight.verdict(run, iid, "subject_zone", {k: v for k, v in z.items() if k != "raw"})
    return z, file_


# ------------------------------------------------------------ 4 · one reviewer

REVIEW_PROMPT = (WS / CFG["review"]["prompt"]).read_text()


def _scene_words(run: Path, it: dict) -> str:
    plan = R.read_json(run / "plan.json", {}) or {}
    sc = next((s for s in plan.get("scenes") or [] if s.get("id") == it.get("for")), None) or {}
    # the brief's on-screen words are NOT in the picture (they are laid on in the edit, P68): never shown to the reviewer
    keep = ("setting", "who", "happens", "voice", "hold", "outcome", "emotion", "face", "gestures")
    words = "\n".join(f"- {k}: {sc[k]}" for k in keep if sc.get(k)) or (it.get("params") or {}).get("prompt", "")[:1500]
    props = [f"{p['name']}" + (f" — real size {p['size']}" if p.get("size") else "") + (f", {p['look']}" if p.get("look") else "")
             for p in _props_of(run, it)]
    words += ("\n- the ONLY objects allowed in this picture (one object, one look, at its real size — the prop pictures are "
              "the references): " + ("; ".join(props) if props else "none — no prop at all"))
    w = _world_of(run, sc)
    banked = _banked_set(run)
    if w or banked:
        # the BANKED set's own set.md is the set (P72): its description and dressing win over the brief's world entry
        desc = banked.get("description") or str(w.get("description") or "")
        dress = banked.get("dressing") or "; ".join(map(str, w.get("dressing") or []))
        words += ("\n- the set, ours (its dressing is the only decoration allowed): " + desc
                  + (" Dressing: " + dress if dress else ""))
    who = _presenter_culture(run)
    if who:
        words += ("\n- the presenter's culture (from their own character file): " + who + " — every piece of writing, "
                  "script, wall art, calendar, flag and decoration in the room belongs to this culture")
    words += "\n- no words of any kind in the picture, except the real product's own printed label (on-screen words are laid on in the edit)"
    if _holds_product(run, sc):
        words += ("\n- the product: a person holds it here, so it must be the brand's REAL product exactly as the 'real "
                  "product' reference shows it (pasted from its real photograph), at its real size; no other product")
    else:
        words += "\n- the product: not in this picture — no product, container or packaging at all"
    return words


def _element_folder(run: Path, kind: str) -> Path | None:
    """The first element of `kind` on the run's element sheet, as its folder (elements.json)."""
    try:
        els = R.read_json(Path(run) / "elements.json", {}) or {}
    except Exception:                                   # noqa: BLE001
        return None
    ws = HERE.parents[2]
    for it in els.get("items") or []:
        if it.get("kind") == kind and it.get("folder") and (ws / it["folder"]).is_dir():
            return ws / it["folder"]
    return None


def _presenter_culture(run: Path) -> str:
    """THE PRESENTER'S CULTURE, READ FROM THEIR OWN CHARACTER FILE (P72, the owner 2026-10-21): its `Culture:` line, else the
    description line (the one quoted with '>'). Nothing about any person is written here — it is the run's data."""
    f = _element_folder(run, "person")
    doc = (f / "character.md").read_text() if f and (f / "character.md").is_file() else ""
    m = re.search(r"(?mi)^\s*-\s*\*\*Culture:\*\*\s*(.+)$", doc) or re.search(r"(?m)^>\s*(.+)$", doc)
    return m.group(1).strip()[:400] if m else ""


def _banked_set(run: Path) -> dict:
    """The banked set's own words from its set.md: the first paragraph (description) and its Dressing line (P72)."""
    f = _element_folder(run, "setting")
    doc = (f / "set.md").read_text() if f and (f / "set.md").is_file() else ""
    if not doc:
        return {}
    paras = [p.strip() for p in re.split(r"\n\s*\n", doc) if p.strip() and not p.lstrip().startswith("#")]
    m = re.search(r"(?mi)^\s*-\s*Dressing[^:]*:\s*(.+)$", doc)
    return {"description": paras[0] if paras else "", "dressing": m.group(1).strip() if m else ""}


def _holds_product(run: Path, sc: dict) -> bool:
    """Does this scene hold the product (element_refs.held_product on the run's brief block)?"""
    try:
        doc = R._load("scenes").json_block((Path(run) / "brief.md").read_text())[0] or {}
        bsc = next((x for x in doc.get("scenes") or [] if x.get("id") == sc.get("id")), sc)
        return bool(R._load("element_refs").held_product(bsc, doc))
    except Exception:                                   # noqa: BLE001
        return False


def _world_of(run: Path, sc: dict) -> dict:
    """The brief's own set entry (world[]) for this scene, from the run's brief block."""
    try:
        doc = R._load("scenes").json_block((Path(run) / "brief.md").read_text())[0] or {}
    except Exception:                                   # noqa: BLE001
        return {}
    sid = sc.get("setting_id") or sc.get("setting")          # the plan carries it as `setting`, the brief as `setting_id`
    return next((w for w in doc.get("world") or [] if w.get("id") == sid), {})


def _refs_of(run: Path, it: dict, brand) -> list:
    out = []
    for m in it.get("medias") or []:
        if m.get("role") != "image_references" or not m.get("value"):
            continue
        p = R._named_ref(run, str(m["value"]), it, brand)
        if p is not None and p.is_file():
            out.append(p)
    # THE LOOK IS ALWAYS SEEN (2026-10-24, the pastor barber's S22A): a swipe-edit frame sends the swipe frame, then each
    # person's master, turnaround, angles and details, then their look — so the first four were the swipe and three
    # cast photos and the look never reached the reviewer, who sent the man back into his cast photo's T-shirt three
    # times. The four kept are the swipe frame, each master, each look; other sheets only if room is left.
    def rank(f):
        s = str(f)
        return (0 if "/casting/" not in s else 1 if Path(s).stem == "master" else 2 if "/look-" in s or Path(s).stem.startswith("look-") else 3)
    out = sorted(out, key=rank)[:4]
    # THE PROPS TO SIZE AGAINST (P35, CHANGES.md C6): a swipe-edit frame attaches no prop to the generation, so the
    # reviewer gets the scene's banked prop pictures here — one object, one look, at its real size (V11/V12)
    for f in _prop_pictures(run, it, brand):
        if f not in out:
            out.append(f)
    return out[:6]


def _props_of(run: Path, it: dict) -> list:
    """The scene's props, each with its real size and look when the brief defines them once (piece.props)."""
    plan = R.read_json(run / "plan.json", {}) or {}
    sc = next((s for s in plan.get("scenes") or [] if s.get("id") == it.get("for")), None) or {}
    # the plan drops `props` and the brief's own props[] list: both are read from the run's brief block (P69 — the
    # reviewer was told "no prop at all" and failed the pitchers and bowls the brief asks for)
    try:
        doc = R._load("scenes").json_block((Path(run) / "brief.md").read_text())[0] or {}
    except Exception:                                   # noqa: BLE001
        doc = {}
    bsc = next((x for x in doc.get("scenes") or [] if x.get("id") == it.get("for")), None) or {}
    rows = list(piece_of(run).get("props") or []) + list(doc.get("props") or [])
    defined = {str(p.get("name")): p for p in rows if isinstance(p, dict) and p.get("name")}
    out = []
    for p in sc.get("props") or bsc.get("props") or []:
        name = p.get("name") if isinstance(p, dict) else str(p)
        out.append({**(defined.get(str(name)) or {}), **(p if isinstance(p, dict) else {}), "name": name})
    return out


def _prop_pictures(run: Path, it: dict, brand) -> list:
    try:
        EP, EC = R._load("element_paths"), R._load("elements_check")
    except Exception:                                   # noqa: BLE001
        return []
    out = []
    for p in _props_of(run, it):
        f = EP.elements_home(brand, "props", EC.slug(p["name"])) / "picture.jpg"
        if f.is_file():
            out.append(f)
    return out


def _review_one(run: Path, it: dict, row: dict, piece: dict, brand, rounds: int) -> dict:
    """Check → (send back → remake → check) at most `rounds` times. Every version is
    kept; the picture that stands is the one with the FEWEST problems — a remake
    that came back worse never replaces a better picture."""
    iid = str(it.get("id"))
    f = Path(row["file"])
    refs = _refs_of(run, it, brand)
    look = (style_formula(piece.get("style_id")) or ("", piece.get("style") or ""))[1]
    versions = run / "media" / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    hist, kept = [], []
    for r in range(1, rounds + 2):
        prompt = REVIEW_PROMPT.replace("{brief}", _scene_words(run, it)).replace("{look}", look)
        z = dict(row.get("zone") or {})
        if z.get("verdict") == "REVIEW":
            prompt += (f"\n\nMEASURED: the {', '.join(z.get('outside') or ['subject'])} crosses out of the "
                       f"safe area — include that fix in your list.")
        text, info = V.ask(run, f"{iid}-v2-review-c{r}", prompt, [f] + refs, model=V.model_of(CFG["checks"]["review_model"]))
        ans = V.json_of(text) or {"verdict": "UNREADABLE", "problems": []}
        probs = ans.get("problems") or []
        snap = versions / f"{iid}-v2-v{r}{f.suffix}"
        shutil.copy2(f, snap)
        kept.append({"n": len(probs) if ans.get("verdict") != "UNREADABLE" else 99, "file": snap, "zone": z, "v": r})
        hist.append({"check": r, **ans, "file": str(snap), "by": info.get("model"),
                     "remembered": bool(info.get("remembered"))})
        if ans.get("verdict") == "PASS" or not probs or r > rounds:
            break
        # SEND_BACK = the remake: the picture itself + the references, every fix at once
        fixes = "; ".join(p.get("fix") or p.get("what") or "" for p in probs)
        edit = ("Edit this picture. Change ONLY these things and keep everything else exactly as it is — the "
                f"person, the clothes, the room, the light, the camera: {fixes}."
                # a swipe-edit frame keeps the swipe's framing exactly: no safe-area slot on its remake (P33)
                + ("" if it.get("swipe_edit") else " " + CFG["safe_area"]["slot"]))
        res = R._load("direct_openai").generate(edit, [f] + refs[:2], f)
        R._load("colour_match").match_file(f, snap)
        R.preflight.ledger(run, res["model"], f"{iid}-v2-remake-{r}", 0.0, "done", brand=brand, shot=iid,
                           note=f"v2 reviewer send-back: {fixes[:300]}", usage=res.get("usage"))
        # a remake redraws the whole picture: the real product goes back in (P68 add)
        if it.get("product_paste") is not None:
            v2_product_of(it, {"file": str(f)}, iid, "", refs, f, False)
        z2 = R.safezone.check(f, caller=V.zone_caller(run, iid))
        row["zone"] = {k: z2.get(k) for k in ("verdict", "outside", "subject_box_still", "size", "zone", "frame")
                       if z2.get(k) is not None}
        if z2["verdict"] == "FAIL":
            row["zone"]["verdict"] = "REVIEW"
    best = min(kept, key=lambda k: (k["n"], k["v"]))
    shutil.copy2(best["file"], f)
    row["zone"] = best["zone"]
    verdict = "PASS" if best["n"] == 0 else "FLAGGED"
    pv = it.get("product_paste") or {}
    if pv and pv.get("ok") is False:
        # the product in this picture is not the real one (the paste did not land): never shipped (P68 add)
        verdict = "FLAGGED"
        hist.append({"check": "product", "verdict": "SEND_BACK",
                     "problems": [{"what": "the product is not the brand's real product: " + "; ".join(pv.get("why") or [])}]})
    if (row.get("zone") or {}).get("verdict") == "REVIEW":
        # still outside the safe area after the rounds: FLAGGED and held — the edit never repairs it (E32)
        row["zone"]["verdict"] = "HELD"
        verdict = "FLAGGED"
    left = list(next(h for h in hist if h["check"] == best["v"]).get("problems") or [])
    if pv and pv.get("ok") is False:
        left += hist[-1]["problems"]
    R.preflight.verdict(run, iid, "v2_review", {"verdict": verdict, "kept_version": best["v"], "rounds": hist})
    return {"id": iid, "verdict": verdict, "kept_version": best["v"], "problems_left": left, "rounds": hist}


def _setting(key, default=None):
    try:
        d = json.loads(Path(os.environ.get("OUTLIER_SETTINGS") or (HERE.parents[2] / "runs" / "settings" / "settings.json")).read_text())
        for part in key.split("."):
            d = d[part]
        return d
    except Exception:  # noqa: BLE001
        return default


def _auto_signoff(run: Path, res: list) -> None:
    """Production on Auto (Outlier Settings, the owner 18-19 Oct: "make it auto, i don't
    want to be in the loop"): the picture + face-lineup sign-off the clip gate needs
    is given by the system, recorded as the system's (never as the owner's), after the
    v2 reviewer. Every picture the reviewer left flagged is filed on Outlier → Calls
    to agree with or overrule. Manual (or Pause everything) leaves it to the owner."""
    if _setting("automation.paused", False) or _setting("automation.production") != "auto":
        print("pictures: production is on Manual in Settings — the sign-off waits for the owner")
        return
    G = _mod("clip_gate", "vm_clip_gate_v2")
    done = G.approve(run, "the system (production on Auto in Outlier Settings)")
    _hold_flagged(run, res)
    q = HERE.parents[2] / "runs" / "decisions" / "calls.jsonl"
    q.parent.mkdir(parents=True, exist_ok=True)
    flagged = [r for r in res if r.get("verdict") != "PASS"]
    with q.open("a") as f:
        import fcntl
        fcntl.flock(f, fcntl.LOCK_EX)           # many runs at once (a batch): one writer at a time
        for r in flagged:
            f.write(json.dumps({"id": f"{run.name}:pictures:{r.get('id')}:{int(time.time())}",
                                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "run": run.name,
                                "brand": run.parent.name, "gate": "pictures", "kind": "pictures:flagged",
                                "item": {"n": str(r.get("id")), "element": "picture " + str(r.get("id")),
                                         "status": "; ".join(map(str, r.get("problems_left") or []))[:400]},
                                "decision": "held by the system — no clip is made from it until it is remade or overruled",
                                "confidence": 0.5,
                                "why": "The reviewer kept the best of three versions and its remakes and problems were still left; a flagged picture is never shipped (P42).",
                                "precedents": [], "verdict": None, "look": True}) + "\n")
    print(f"pictures: signed off by the system (production on Auto) — {len(done)} picture(s) and lineups; "
          f"{len(flagged)} flagged picture(s) HELD and filed on Outlier → Calls")


def _hold_flagged(run: Path, res: list | None = None) -> list:
    """A picture the reviewer left FLAGGED is never signed off (P42, E32): its approval is taken back, so the clip
    gate holds every clip made from it — named — until it is remade or a person overrules it."""
    res = res if res is not None else (R.read_json(Path(run) / "v2-review.json", []) or [])
    flagged = {str(r.get("id")) for r in res if r.get("verdict") not in ("PASS", None)}
    f = Path(run) / "clips" / "gate-approved.json"
    a = R.read_json(f, {}) or {}
    held = sorted(k for k in a if k in flagged and not str((a[k] or {}).get("by", "")).lower().startswith("owner"))
    for k in held:
        a.pop(k, None)
    if held:
        R.write_json(f, a)
        print(f"pictures: {len(held)} flagged picture(s) held — no clip is made from {', '.join(held)}")
    return held


def v2_review(run, items, made):
    # THE SWIPE'S LOOK, after every picture is made and before any is checked (P32, CLAUDE.md "Then the swipe's
    # look"): each swipe-edit frame moved toward its swipe frame's light, colour, softness and grain
    try:
        for line in R._load("swipe_look").run(Path(run)):
            print("swipe look:", line)
    except Exception as e:                              # noqa: BLE001 — the look is a finish; the reviewer still runs
        print(f"swipe look: not applied ({type(e).__name__}: {str(e)[:160]})")
    # ONE TONE FOR THE WHOLE AD (P69, the owner: the cast member's skin and shirt changed tone frame to frame):
    # every start picture graded to the one frame closest to the cast master — the grade only, nothing redrawn
    try:
        TA = R._load("tone_anchor")
        got = TA.run(Path(run), TA.master_of(Path(run)))
        print(f"tone: every picture held to {got.get('anchor') or '—'}" + (f" ({got['skipped']})" if got.get("skipped") else ""))
    except Exception as e:                              # noqa: BLE001 — a grade that cannot run never stops the review
        print(f"tone: not applied ({type(e).__name__}: {str(e)[:160]})")
    piece = piece_of(run)
    brand = (R.read_json(run / "run.json", {}) or {}).get("brand")
    rounds = int(CFG["review"]["max_rounds"])
    t0 = time.time()
    todo = [(it, made[str(it.get("id"))]) for it in items
            if it.get("kind") in ("still", "edit", "restyle") and (made.get(str(it.get("id"))) or {}).get("file")]
    with cf.ThreadPoolExecutor(max_workers=int(CFG["pictures"]["parallel"])) as ex:
        def safe(x):
            try:
                return _review_one(run, x[0], x[1], piece, brand, rounds)
            except Exception as e:                      # noqa: BLE001 — one picture's failure never stops the rest
                return {"id": str(x[0].get("id")), "verdict": "UNCHECKED", "why": f"{type(e).__name__}: {e}"[:300]}
        res = list(ex.map(safe, todo))
    R.write_json(run / "direct.json", {**(R.read_json(run / "direct.json", {}) or {}), **made})
    R.write_json(run / "v2-review.json", res)
    _auto_signoff(run, res)
    ok = sum(1 for r in res if r.get("verdict") == "PASS")
    CHECK_TIMES["review_s"] += time.time() - t0
    print(f"v2 picture review: {ok} pass, {len(res) - ok} flagged for a look after at most {rounds} remakes (best version kept) — {run / 'v2-review.json'}")


# ------------------------------------------------------------ 6 · clips by format, retakes capped

def clip_resolution(fmt: str | None) -> str:
    """Every take at the house resolution (480p, upscaled on this Mac — the owner 2026-10-26; was 720p from 2026-10-23, 360p before)."""
    return CFG["clips"]["resolution"]


def _patch_clips(m, fmt=None):
    real_cfg, real_make = m.route_cfg, m.make_call

    def route_cfg(reg=None, fmt_=None):
        # clips_run passes the ad's format as a second argument (its by_format rows); keep it, v2's resolution wins
        c = dict(real_cfg(reg, fmt_))
        c["resolution"] = clip_resolution(fmt or fmt_)
        # only the PICKED take is upscaled, on this Mac, free (V6, P20)
        c["upscale_below_1080p"] = True
        c["upscale_where"] = "local"
        c["upscale_local"] = c.get("upscale_local") or CFG["clips"]["upscale_local"]
        c["takes"] = int(CFG["clips"]["takes"])
        c["max_tries"] = int(CFG["clips"].get("max_tries") or c["takes"])     # V34: another take only on failure
        return c

    real_pick = m.make_picked

    def make_picked(run, c, cfg, led, people, make=None, judge=None):
        # V2_EXTRA_TAKES=<clip id,…>: a clip kept below criteria after its attempts gets a new round of attempts when
        # asked for by name for that run; the earlier file is set aside, never overwritten.
        extra = c["id"] in [x.strip() for x in os.environ.get("V2_EXTRA_TAKES", "").split(",") if x.strip()]
        if extra and (led.get(c["id"]) or {}).get("below_criteria"):
            c = {**c, "take_round": int((led.get(c["id"]) or {}).get("take_round") or 1) + 1}
            fin = Path(run) / "clips" / f"{c['id']}.mp4"
            if fin.is_file():
                fin.rename(fin.with_name(fin.stem + f"-round{c['take_round'] - 1}" + fin.suffix))
            led.put(c["id"], take_round=c["take_round"], status="new round")
        return real_pick(run, c, cfg, led, people, make=make, judge=judge)

    m.route_cfg, m.make_picked = route_cfg, make_picked
    return m


def _fmt_of(run: Path) -> str | None:
    return (R.read_json(Path(run) / "run.json", {}) or {}).get("format")


_FMT = {"v": None}


def _auto_banks(m):
    """The banks gate on Auto (P67): a called cue with no made row is written from the brief and made, then picked —
    the gate refuses only what still cannot be supplied. Manual (or Pause everything): the gate as it was."""
    real = m.resolve

    def resolve(plan, root=None):
        if _setting("automation.production") == "auto" and not _setting("automation.paused"):
            try:
                for note in m.auto_make(plan, root, dry=bool(_CUR.get("dry"))):
                    print(f"banks: {note}")
            except (Exception, SystemExit) as e:                # noqa: BLE001 — the gate names what is still missing
                print(f"banks: the automatic step stopped ({type(e).__name__}: {str(e)[:200]})")
        return real(plan, root)
    m.resolve = resolve
    return m


def v2_load(name):
    m = _orig_load(name)
    if name == "clips_run":
        _patch_clips(m, _FMT["v"])
    if name == "banks":
        _auto_banks(m)
    return m


R._load = v2_load


# ------------------------------------------------------------ 7 · voice + voice checks on the ledger

def _run_of_clip(f) -> Path | None:
    p = Path(f).resolve()
    for up in p.parents:
        if (up / "run.json").is_file():
            return up
    return None


_real_parity = R.lineparity_mod.check


def _parity(clip, line, *a, **kw):
    res = _real_parity(clip, line, *a, **kw)
    run = _run_of_clip(clip)
    if run and res is not None:
        secs = R.voice_mod.audio_seconds(Path(clip)) or 0
        V.ledger(run, "elevenlabs-scribe", f"{Path(clip).stem}-v2-words-check", secs / 3600 * 0.40,
                 note="speech-to-text words check ($0.40/hour)", seconds=round(secs, 1))
    return res


R.lineparity_mod.check = V.memo_file_check(_run_of_clip, _parity, "lineparity")

_real_voice_t = R.voice_mod.http_json_transport


def _voice_t(method, url, body, headers):
    out = _real_voice_t(method, url, body, headers)
    run = _CUR.get("run")
    if run and body and body.get("text"):
        n = len(body["text"])
        V.ledger(run, "elevenlabs", f"voice-{n}ch-v2", n / 1000 * 0.10,
                 note=f"text-to-speech, {n} characters ($0.10 per 1,000)", chars=n)
    return out


R.voice_mod.http_json_transport = _voice_t
_CUR: dict = {}


# ------------------------------------------------------------ wire it in

R.run_machine_hand = v2_hand
R.zone_gate = v2_zone_gate
# THE PRODUCT IS NEVER DRAWN (P34, VIDEO-RULINGS V16): v2 bakes nothing into a frame — no redraw (product_fix), no
# paste (product_paste); the product is laid on in the edit from its real photograph. Nothing to draw, so no kit gate.
def v2_product_of(it, res, iid, prompt, refs, out, dry_run, transport=None, key=None):
    """THE REAL PRODUCT IN HER HANDS (P68 add, the owner 2026-10-21: "why are we using the wrong product in those images of
    yai holding something?????"): where the picture holds the product (its real packshot was a reference), every pixel
    of it is replaced by the brand's real photograph at the matching pose and size (product_paste.py — the kit's real
    cut-outs). No redraw (product_fix) ever. A paste that does not land is recorded; the reviewer holds the picture."""
    if dry_run or not res.get("file"):
        return res
    if it.get("in_use"):        # drawn from its real in-use pictures: never pasted over (the owner, 2026-10-25)
        return res
    got = R.product_gate(refs, iid)
    if not got:
        return res
    _brand, _slug, kit_path = got
    kit = json.loads(kit_path.read_text())
    try:
        pv = R._load("product_paste").run(res["file"], kit_path.parent, what=kit.get("what") or "the product")
    except Exception as e:                              # noqa: BLE001 — a paste that cannot run never passes the product
        pv = {"ok": False, "why": [f"the paste did not run: {type(e).__name__}: {e}"[:200]]}
    it["product_paste"] = pv
    print(f"  {iid}: real product " + (f"pasted — angle {pv.get('angle')}°, overlap {pv.get('overlap')}" if pv.get("file")
                                        else (pv.get("skipped") or "NOT pasted: " + "; ".join(pv.get("why") or []))))
    return res


R.product_of = v2_product_of
# THREE READS OF EVERY LINE, ONE LOCKED (P13, VIDEO-RULINGS V5)
R.voice_mod.READS = int((CFG.get("voice") or {}).get("reads") or 1)
R.voice_mod.TRIES = int((CFG.get("voice") or {}).get("max_tries") or 1)
_real_binding = R.voice_mod.binding


def _house_binding(home):
    """The person's own voice, read on the HOUSE voice model (sound.voice, ElevenLabs v3 — VIDEO-RULINGS V2/V4),
    over any older model id their voice.json still carries."""
    vid, _mid, st = _real_binding(home)
    return vid, R.voice_mod.default_model_id(), st


R.voice_mod.binding = _house_binding
R.review_pictures = v2_review
R.zone_plan_line = lambda iid: print(f"  {iid}: v2 subject zone — one direct check "
                                     f"({CFG['checks']['zone_model']}); a miss goes to the reviewer's list, no repair edit")


# ------------------------------------------------------------ 8 · the order (P9, VIDEO-RULINGS V7)

def _parser_has(flag: str) -> bool:
    return any(flag in getattr(x, "option_strings", []) for sp in R.build_parser()._subparsers._group_actions
               for p_ in sp.choices.values() for x in p_._actions)


def _voice_step(argv: list) -> list:
    """`start --voice-only`: the read made, three reads a line, one locked, heard — no picture. A run.py that predates
    the flag is asked for --storyboard before a storyboard exists, which stops right after the voice the same way."""
    return argv + (["--voice-only"] if _parser_has("--voice-only") else ["--storyboard"])


def listed_pictures(run: Path) -> tuple[list, list]:
    """(every picture id storyboard.json lists, the ones not yet in media/)."""
    cp = _orig_load("clips_plan")
    sb = R.read_json(Path(run) / "storyboard.json", {}) or {}
    # a SWAP scene (SHOT-ROUTES.md) is the swipe's own shot with our cast swapped in: it lists no picture of ours
    # (the storyboard step skips it the same way, run.py; baddie barber, 2026-10-21)
    plan = R.read_json(Path(run) / "plan.json", {}) or {}
    swapped = {str(s.get("id")) for s in plan.get("scenes") or [] if s.get("source_plan") == "swap"}
    ids = []
    for g in sb.get("sections") or []:
        if g.get("scenes") and all(str(s) in swapped for s in g["scenes"]):
            continue
        pics = cp.picture_ids(g)
        for x in [pics["start"], pics["end"]] + [o["id"] for o in pics["own"]] + [x_["id"] for x_ in pics.get("setups") or []]:
            if x and x not in ids:
                ids.append(x)
    return ids, [x for x in ids if cp.picture_file(Path(run), x) is None]


def _n_versions() -> int:
    """How many versions of each start picture (v2.json pictures.versions — 1 since V33, retries only on a send-back)."""
    return max(1, int((CFG.get("pictures") or {}).get("versions") or 1))


def _storyboard(run: Path, brief: str | None, dry_run: bool) -> int:
    if (run / "storyboard.json").is_file():
        print("2 · storyboard: storyboard.json is there — its sections decide the pictures")
        return 0
    if not (run / "vo" / "timing.json").is_file():
        print("2 · storyboard: waits for the locked reads (vo/timing.json) — "
              + ("this dry run made none" if dry_run else "the voice step made none"))
        return 0 if dry_run else 2
    sb = _orig_load("storyboard_plan")
    import subprocess as _sp
    cmd = [sys.executable, str(Path(sb.__file__)), str(run)]
    if brief:
        cmd += ["--teardown", str(Path(brief).parent.parent), "--brief", brief]
    print("2 · storyboard: " + " ".join(cmd[1:]))
    rc = _sp.run(cmd, check=False).returncode
    if rc == 0 and not dry_run and not (run / "storyboard.json").is_file():
        print("2 · storyboard: STOP — the step ended without a storyboard.json, so no picture is made")
        return 2
    if rc == 0 and not dry_run:
        shared = _orig_load("shared_shots").group(run)
        print(f"2 · storyboard: {len(shared)} scene(s) share another scene's picture, generating only what differs")
    return rc


def ordered(argv: list) -> int:
    """VOICE FIRST, THEN THE STORYBOARD, THEN ONLY THE PICTURES IT LISTS, THEN THE CLIPS (the owner, 2026-10-20: "that slack
    needs to be pulled" — a run made 32 pictures and used 3). `start` with none of --voice-only / --storyboard /
    --clips runs the four steps in this order; the paid clip run itself stays `run_v2.py clips <run> --yes`."""
    a = R.build_parser().parse_args(argv)
    run = _CUR["run"]
    _ac = R.read_json(run / "vo" / "audio-check.json", {}) or {}
    if (run / "vo" / "timing.json").is_file() and ((run / "storyboard.json").is_file() or _ac.get("pass") is True):
        # A VOICE THAT PASSED ITS CHECK IS KEPT (2026-10-24, the owner: "we don't need to do full regenerations"): a re-run
        # never reads every line again because a later step stopped
        print("1 · voice: kept — the locked reads are in vo/ and passed the voice check")
    else:
        print(f"1 · voice: every line read {R.voice_mod.READS} time(s) on the house voice "
              f"({_orig_load('house').voice_model()}) with its delivery tag, one locked")
        rc = R.main(_voice_step(argv))
        if rc not in (0, None):     # a failed voice step stops the run, even over an older vo/timing.json (row 15)
            print(f"1 · voice: STOP — the voice step failed (code {rc}); nothing after it runs")
            return rc
    rj = R.read_json(run / "run.json", {}) or {}
    brief = rj.get("brief_from") or (a.source if Path(a.source).suffix.lower() == ".md" else None)
    rc = _storyboard(run, brief, a.dry_run)
    if rc:
        return rc
    if not (run / "storyboard.json").is_file():
        print(f"3 · pictures: wait for the storyboard — only the pictures it lists are made, {_n_versions()} version(s) each")
        print("4 · clips: wait for the pictures — then ONE take of every clip at 480p on Seedance 2.5; another only if it fails, three at most (V34)")
        return 0 if a.dry_run else 2
    ids, missing = listed_pictures(run)
    print(f"3 · pictures: the storyboard lists {len(ids)} — {len(missing)} still to make, {_n_versions()} version(s) each")
    if missing or a.dry_run:
        rc = R.main(argv + ["--storyboard"] + (["--only", ",".join(missing)] if missing and not a.dry_run else []))
        if rc not in (0, None) and not a.dry_run:
            return rc
        if rc not in (0, None):
            print("3 · pictures: the step above refused (named) — a real run stops here; the dry run goes on to show the clips")
    print("4 · clips: the plan — ONE take of every clip at 480p on Seedance 2.5, judged; another only if it fails, three at most (V34)")
    return R.main(argv + ["--clips"])


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:   # keys read ONCE into this process before any parallel work (a racing read came back empty mid-batch twice)
        _vk = _orig_load("vp_keys")
        for _n in ("FAL_KEY", "ELEVENLABS_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
            if not os.environ.get(_n):
                _v = _vk.key(_n)
                if _v:
                    os.environ[_n] = _v
    except Exception:  # noqa: BLE001
        pass
    if argv and argv[0] == "clips" and len(argv) > 1:
        # 19 Oct 2026: clips build their own plan. A run with pictures but no storyboard or clip plan
        # gets both here (storyboard from the brief + its teardown, then the clips plan), so no hand step stops it.
        _run = Path(argv[1]).resolve()
        _rj = R.read_json(_run / "run.json", {}) or {}
        _bf = _rj.get("brief_from")
        if _bf and (R.read_json(_run / "clips" / "plan.json", {}) or {}).get("route") != "seedance":
            # THE ORDER, from wherever the run stands (P9): voice → storyboard → the listed pictures → the clip plan
            _FMT["v"] = _rj.get("format")
            _CUR["run"] = _run
            base = ["start", _bf, "--brand", _rj.get("brand") or "", "--format", _rj.get("format") or "",
                    "--label", _rj.get("label") or _run.name, "--yes"]
            # every step's code is read: a failed step stops the clips here, nothing after it runs (row 15)
            if not (_run / "vo" / "timing.json").is_file():
                _rc = R.main(_voice_step(base))
                if _rc not in (0, None):
                    print(f"clips: STOP — the voice step failed (code {_rc}); no picture or clip is made")
                    return _rc
            _rc = _storyboard(_run, _bf, False)
            if _rc or not (_run / "storyboard.json").is_file():
                print(f"clips: STOP — no storyboard (code {_rc or 2}); no picture or clip is made")
                return _rc or 2
            _ids, _missing = listed_pictures(_run)
            if _missing:
                _rc = R.main(base + ["--storyboard", "--only", ",".join(_missing)])
                if _rc not in (0, None):
                    print(f"clips: STOP — the pictures step failed (code {_rc}); no clip is made")
                    return _rc
                _ids, _missing = listed_pictures(_run)
                if _missing:
                    print(f"clips: STOP — {len(_missing)} listed picture(s) still missing: {', '.join(_missing)}")
                    return 2
            _rc = R.main(base + ["--clips"])
            if _rc not in (0, None):
                print(f"clips: STOP — the clip plan failed (code {_rc}); nothing is spent")
                return _rc
    if argv and argv[0] == "clips" and len(argv) > 1 and _setting("automation.production") == "auto" \
            and not _setting("automation.paused"):
        # production on Auto: the clip gate is checked and signed off by the system, the way the pictures are
        _cg = _orig_load("clip_gate")
        _r = Path(argv[1]).resolve()
        # Auto signs only the looking (pictures, face lineups) — then the gate is checked AGAIN, and any red left
        # (paths, words, prompts, a held picture) stops the run here; the system never signs a red gate (row 15)
        try:
            _cg.check(_r)
            _cg.approve(_r, "the system (production on Auto in Outlier Settings)")
            _hold_flagged(_r)
            _g = _cg.check(_r)
        except Exception as e:  # noqa: BLE001
            print(f"clip gate: STOP — the system could not check it ({type(e).__name__}: {str(e)[:120]}); nothing is spent")
            return 2
        if not _g.get("green"):
            for _row in _g.get("calls") or []:
                for _x in _row.get("red") or []:
                    print(f"GATE {_row.get('id')}: {_x}")
            print("clip gate: STOP — still red after the system's sign-off (production on Auto); nothing is spent")
            return 2
        print("clip gate: checked, signed off by the system and checked again — green (flagged pictures held)")
    if argv and argv[0] == "clips":
        oc = _patch_clips(_orig_load("clips_run"), _fmt_of(Path(argv[1])) if len(argv) > 1 else None)
        # a held gate (2) stays held: the system signed and re-checked above, so nothing is approved blind here
        return oc.main(["run"] + argv[1:])
    if argv and argv[0] == "review":                    # the one reviewer alone, over pictures already made
        run = Path(argv[1]).resolve()
        _CUR["run"] = run
        made = R.read_json(run / "direct.json", {}) or {}
        items = []
        for bf in sorted((run / "batches").glob("*.json")):
            items += R.platform.load_batch(bf)
        t = time.time()
        v2_review(run, [i for i in items if str(i.get("id")) in made], made)
        print(f"v2 · review {round((time.time() - t) / 60, 1)} min · {V.STATS['asked']} checks asked, "
              f"{V.STATS['remembered']} from memory · checks ${V.STATS['usd']:.3f}")
        return 0
    if argv and argv[0] == "start":
        a = R.build_parser().parse_args(argv)
        _FMT["v"] = a.format
        root = Path(a.runs_root) if a.runs_root else R.DEFAULT_RUNS_ROOT
        _CUR["run"] = root.resolve() / "video-production" / a.brand / a.label
        _CUR["dry"] = bool(a.dry_run)
        # THE AUTOMATIC ELEMENTS STEP (19 Oct 2026): production on Auto binds or makes every element
        # still to make and confirms them as the system's, before run.py's manifest + elements gates.
        if not a.dry_run and Path(a.source).suffix.lower() != ".json" and _setting("automation.production") == "auto" \
                and not _setting("automation.paused") and not a.label.startswith("v2test-"):
            try:
                _ae = _mod("auto_elements", "vm_auto_elements")
                _ae.run(Path(a.source), a.brand, _CUR["run"])
            except Exception as e:  # noqa: BLE001
                print(f"elements: the automatic step stopped ({type(e).__name__}: {str(e)[:200]}) — the gates decide")
    t = time.time()
    if argv and argv[0] == "start" and not any(f in argv for f in ("--voice-only", "--storyboard", "--clips")) \
            and Path(argv[1] if len(argv) > 1 else "").suffix.lower() != ".json":
        rc = ordered(argv)
    else:
        rc = R.main(argv)
    run = _CUR.get("run")
    if run and Path(run).is_dir():
        s = {"version": "v2", "minutes": round((time.time() - t) / 60, 1), **V.STATS,
             "pictures_s": round(CHECK_TIMES["pictures_s"]), "review_s": round(CHECK_TIMES["review_s"])}
        p = Path(run) / "v2-stats.json"
        prev = R.read_json(p, []) or []
        R.write_json(p, prev + [{**s, "argv": argv, "at": V.now()}])
        print(f"v2 · {s['minutes']} min · {V.STATS['asked']} checks asked, {V.STATS['remembered']} answered "
              f"from memory · checks ${V.STATS['usd']:.3f}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
