"""THE AUTOMATIC ELEMENTS STEP — production on Auto (Outlier Settings,
automation.production == "auto"): a written AI brief goes to production with
no person between the elements check and the voice.

    python3 auto_elements.py <brief.md> --brand B --run <production run dir> [--dry-run]

run_v2.py start calls `run()` before run.py's manifest and elements gates.
For every element the elements sheet (elements_check.sheet) still lists TO MAKE:

  1. MATCH — a banked element made from the SAME swipe (its provenance names a
     teardown run whose source.mp4 is byte-identical to this brief's swipe, or
     a reference file identical to one of this swipe's frames) is bound to the
     brief (elements_check.bind). A person's NEW look binds to the banked look
     whose outfit words overlap most. A different swipe's face is NEVER reused.
  2. MAKE — otherwise the element is made from the swipe frames its
     real_reference names: a person with make_character.py (+ a voice from the
     swipe's own separated audio, voice-N.mp3, via make_voice.py, the first of
     three options picked by the system), a place with make_set.py, a prop
     from its swipe crop (the crop IS the picture, no generation). A prop the
     swipe never shows is mapped by name to a banked prop and copied under the
     brief's prop id; one the bank does not hold either is MADE from the brief's
     own definition (name, size, look) on the house picture model with real
     references attached — the run's set picture and the nearest swipe frame —
     then reviewed for slop (make_prop, P65). A product is never drawn. Then bound.
  3. The manifest is re-checked (video-teardown manifest.py check), the sheet is
     written to <run>/elements.json and confirmed by "the system (production on
     Auto in Outlier Settings)".

Every decision is appended to runs/decisions/calls.jsonl (gate "elements",
flock'd, decide.py's shape) for the owner to agree with or overrule on Outlier → Calls.
Generated elements live in runs/ai-elements/<brand>/ — never in brands/.
Manual (or Pause everything) does nothing: the gates wait for a person.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
BY = "the system (production on Auto in Outlier Settings)"
CALLS = WS / "runs" / "decisions" / "calls.jsonl"
DRY = {"on": False}


def _mod(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


EC = _mod(HERE / "elements_check.py", "vm_ae_elements_check")
EP = _mod(HERE / "element_paths.py", "vm_ae_element_paths")


def setting(key, default=None):
    try:
        d = json.loads(Path(os.environ.get("OUTLIER_SETTINGS") or (WS / "runs" / "settings" / "settings.json")).read_text())
        for k in key.split("."):
            d = d[k]
        return d
    except Exception:  # noqa: BLE001
        return default


def is_auto() -> bool:
    return setting("automation.production") == "auto" and not setting("automation.paused", False)


# ------------------------------------------------------------------ the log

def log(run_name: str, brand: str, item: dict, decision: str, why: str, confidence: float = 0.6) -> None:
    if DRY["on"]:
        print(f"  [dry run] elements · {item.get('kind')} {item.get('id')}: {decision}")
        return
    CALLS.parent.mkdir(parents=True, exist_ok=True)
    row = {"id": f"{run_name}:elements:{item.get('kind')}:{item.get('id')}:{int(time.time())}",
           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "run": run_name, "brand": brand,
           "gate": "elements", "kind": f"elements:{item.get('kind')}",
           "item": {"n": str(item.get("id")), "element": f"{item.get('kind')} · {item.get('id')}",
                    "status": "; ".join(item.get("missing") or [])[:400]},
           "decision": decision, "mode": "auto", "confidence": confidence, "why": why,
           "ruling": False, "precedents": [], "verdict": None, "look": True}
    with CALLS.open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  elements · {item.get('kind')} {item.get('id')}: {decision}", flush=True)


# ------------------------------------------------------------- same swipe

_HASH: dict = {}


def _md5(p: Path) -> str | None:
    p = Path(p)
    if not p.is_file():
        return None
    k = str(p.resolve())
    if k not in _HASH:
        h = hashlib.md5()
        with p.open("rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        _HASH[k] = h.hexdigest()
    return _HASH[k]


def _teardown_runs_named(text: str) -> list[Path]:
    out = []
    for m in re.finditer(r"runs/video-teardown/_work/([A-Za-z0-9._-]+)", text or ""):
        d = EC.TEARDOWN_RUNS / m.group(1)
        if d.is_dir() and d not in out:
            out.append(d)
    return out


def same_swipe(folder: Path, td: Path, swipe_el: str | None) -> str:
    """Why `folder` was made from the same swipe as teardown `td` ('' = it was not)."""
    src = _md5(td / "source.mp4")
    try:
        prov = json.loads((folder / "provenance.json").read_text())
    except (OSError, ValueError):
        return ""
    refs = prov.get("real_references") or []
    text = json.dumps(refs) + json.dumps((json.loads((folder / "spec.json").read_text()).get("voice") or {})
                                         if (folder / "spec.json").is_file() else {})
    el_ok = lambda: not swipe_el or f"/{swipe_el})" in text or f"/{swipe_el}," in text or f"/{swipe_el}" in text
    for d in _teardown_runs_named(text):
        if d.resolve() == td.resolve() and el_ok():
            return f"made from this swipe's own frames ({td.name})"
        if src and _md5(d / "source.mp4") == src and el_ok():
            return f"made from the same swipe video (teardown {d.name}, identical source.mp4)"
    # a reference file byte-identical to one of this swipe's frames
    if swipe_el:
        mine = {_md5(p) for p in (td / "framemap" / "elements" / swipe_el).glob("*.jpg")}
        for r in refs:
            if _md5(folder / r.get("file", "")) in mine:
                return f"its reference {r.get('file')} is this swipe's own frame"
    return ""


def _complete(folder: Path, kind: str) -> bool:
    return not EC._check_folder(folder, EC.standard()[kind]["requires"])


def match_banked(brand: str, item: dict, td: Path | None):
    """(bank_id, why) of a banked element from the same swipe, or (None, '')."""
    if not td:
        return None, ""
    sub, kind = {"person": ("casting", "person"), "setting": ("sets", "setting")}[item["kind"]]
    root = EP.casting_root(brand, WS) if sub == "casting" else EP.elements_home(brand, "sets", "x", WS).parent
    swipe_el = Path((item.get("swipe_frames") or {}).get("element") or "").name or None
    hits = []
    for f in sorted(root.iterdir()) if root.is_dir() else []:
        if not f.is_dir() or f.name.startswith("_"):
            continue
        why = same_swipe(f, td, swipe_el)
        if why and _complete(f, kind):
            hits.append((f.stat().st_mtime, f.name, why))
    if not hits:
        return None, ""
    hits.sort(reverse=True)
    return hits[0][1], hits[0][2]


def _words(s: str) -> set:
    stop = {"a", "an", "the", "and", "with", "on", "of", "in", "his", "her", "their", "its", "to", "s", "fit", "new"}
    return {w for w in re.findall(r"[a-z]+", (s or "").lower()) if w not in stop and len(w) > 1}


def best_look(folder: Path, want: str):
    try:
        looks = json.loads((folder / "looks.json").read_text()).get("looks") or {}
    except (OSError, ValueError):
        return None, 0.0
    w = _words(want.split(":", 1)[-1])
    best, score = None, 0.0
    for lid, row in looks.items():
        o = _words(row.get("outfit", ""))
        s = len(w & o) / max(1, len(w | o))
        if s > score:
            best, score = lid, s
    return best, score


# -------------------------------------------------------------------- make

def _brief_doc(text: str) -> dict:
    return EC._json_block(text)


def _free_id(root: Path, base: str) -> str:
    i, cand = 1, base
    while (root / cand).exists():
        i += 1
        cand = f"{base}-{i}"
    return cand


def _voice_clip(td: Path, cid: str, n_people: int) -> Path | None:
    vdir = td / "audio" / "voices"
    clips = sorted(vdir.glob("voice-*.mp3"))
    if not clips:
        return None
    if len(clips) == 1 or n_people == 1:
        # one speaker on the swipe (or one person in the brief): the longest clip is theirs
        return max(clips, key=lambda p: p.stat().st_size)
    return clips[0]


def make_person(brand: str, row: dict, item: dict, doc: dict, td: Path, sheet_p: Path, dry: bool) -> str:
    root = EP.casting_root(brand, WS)
    pid = _free_id(root, EC.slug(row.get("name") or row.get("id")))
    out = root / pid
    looks = {}
    for s in doc.get("scenes") or []:
        lk = (s.get("looks") or {}).get(row.get("id"))
        if lk and lk.upper().startswith("NEW"):
            words = lk.split(":", 1)[-1].strip()
            if words not in [v["outfit"] for v in looks.values()]:
                lid = f"look-{len(looks) + 1}-" + "-".join(list(_words(words.split(";")[0]))[:3] or ["outfit"])
                looks[lid] = {"outfit": words, "from": "the swipe's own frames (" + (row.get("real_reference") or "")[:120] + ")",
                              "continuity": "as the swipe: every accessory stays on in every scene"}
    if not looks:
        looks["look-1-base"] = {"outfit": "as the swipe's person wears it", "from": "the swipe's own frames", "continuity": "as the swipe"}
    vpersona = (row.get("voice") or {}).get("persona") or ""
    spec = {"id": pid, "brand": brand,
            "who": row.get("identity_block") or row.get("name"),
            "adjustments": row.get("adjustments") or ["a different face from the swipe's person: different nose, brow and jaw line",
                                                      "same age band, build, skin tone and manner"],
            "base": "plain crew-neck tee and plain trousers, no hat, no glasses, no jewellery",
            "details": "the hands and nails, the skin at the jaw and cheeks, the ears, any rings",
            "looks": looks,
            "character": {"title": (row.get("name") or pid).title(), "why": (row.get("identity_block") or "")[:160],
                          "role": "on-camera talent" if item.get("scenes") else "voice only",
                          "age": (re.search(r"\b(\d{2}) to (\d{2})\b", row.get("identity_block") or "") or [""])[0],
                          "lane": "paid", "loadbearing": [], "movement": "as the swipe's person moves",
                          "voice": vpersona},
            "made_by": BY, "runs": [td.name]}
    clip = _voice_clip(td, row.get("id"), len(doc.get("cast") or [])) if item.get("speaks") else None
    if clip:
        spec["voice"] = {"persona": vpersona or "as the swipe's speaker",
                         "adjustments": ["a different voice from the swipe's speaker: same register, pace and accent, a slightly different timbre",
                                         "no imitation of the real speaker's identity"],
                         "real_reference": {"file": "reference/voice-real.mp3", "kind": "real audio",
                                            "from": f"the swipe's own speaker, separated by the audio teardown ({clip.relative_to(WS)})"}}
    if dry:
        print(f"  [dry run] would make person {pid} from {td.name}")
        return pid
    out.mkdir(parents=True, exist_ok=True)
    (out / "reference").mkdir(exist_ok=True)
    if clip:
        shutil.copy2(clip, out / "reference" / "voice-real.mp3")
    sp = out / "spec.json"
    sp.write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    MC = _mod(HERE / "make_character.py", "vm_ae_make_character")
    MC.build(sp, sheet=sheet_p)
    _stamp(out, "made")
    return pid


def make_voice(folder: Path, doc: dict, cid: str) -> None:
    MV = _mod(HERE / "make_voice.py", "vm_ae_make_voice")
    line = next((s.get("voice") for s in doc.get("scenes") or []
                 if s.get("speaker") == cid and (s.get("voice") or "").strip()
                 and not re.match(r"(?i)^none\b", s["voice"].strip())), "Hello there.")
    MV.options(folder, line[:300])
    MV.pick(folder, 1, by=BY)


def make_set(brand: str, row: dict, item: dict, td: Path, sheet_p: Path, dry: bool) -> str:
    root = EP.elements_home(brand, "sets", "x", WS).parent
    sid = _free_id(root, EC.slug(row.get("id")))
    spec = {"id": sid, "brand": brand, "place": row.get("description") or row.get("id"),
            "adjustments": ["no people in it", "the dressing rearranged slightly so it is not the swipe's exact place"],
            "time": row.get("time_of_day") or "daytime", "light": row.get("light") or "as the swipe",
            "dressing": row.get("dressing") or [], "resets": "nothing moves between takes",
            "room_tone": "as the swipe's place sounds",
            "angles": {"angle-a-to-camera": "where the to-camera shot stands, as the swipe frames it",
                       "angle-b-cutaway": "a tighter cutaway from the side, same light"},
            "rights": "An original place built from the swipe's real frames with the adjustments above.",
            "made_by": BY, "runs": [td.name]}
    if dry:
        print(f"  [dry run] would make setting {sid} from {td.name}")
        return sid
    out = root / sid
    out.mkdir(parents=True, exist_ok=True)
    sp = out / "spec.json"
    sp.write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    MS = _mod(HERE / "make_set.py", "vm_ae_make_set")
    MS.build(sp, sheet=sheet_p)
    _stamp(out, "made")
    return sid


def _stamp(folder: Path, verb: str) -> None:
    p = folder / "provenance.json"
    try:
        rec = json.loads(p.read_text())
    except (OSError, ValueError):
        return
    rec[f"{verb}_by"] = BY
    p.write_text(json.dumps(rec, indent=1, ensure_ascii=False))


# ------------------------------------------------------------- a prop the swipe never shows (P65)

PROP_PROMPT = (
    "A real photograph of ONE object on its own: {name} — {look}. Its real size: {size}. "
    "It stands on a clean, plain stretch of the counter from the reference room picture, in that room's own light, "
    "photographed straight on so its whole shape, size and surface read clearly; the second reference is a real frame "
    "of the video this object will appear in — match its light, colour and camera feel. "
    "Show exactly what the words describe, at full detail — every texture, colour and part named; if it is "
    "oversized, gross or strange, show that in full, never softened. "
    "Nothing else in the picture: no person, no hands, no product, no packaging, no label, no words or letters.")


def prop_definition(doc: dict, name: str) -> dict:
    """The brief's own definition of a prop (props[]: name, size, look — V11, one object one look), else {}."""
    norm = lambda t: " ".join(re.findall(r"[a-z0-9']+", str(t or "").lower()))
    rows = list(doc.get("props") or []) + list((doc.get("piece") or {}).get("props") or [])
    return next((r for r in rows if isinstance(r, dict) and norm(r.get("name")) == norm(name)), {})


def _is_product(doc: dict, name: str) -> bool:
    """A product is never drawn (V16): the prop is the piece's product, or named in its product lock."""
    n = str(name or "").lower()
    pid = str((doc.get("piece") or {}).get("product") or "").lower()
    locked = " ".join(str(x) for x in doc.get("product_lock") or []).lower()
    return bool(pid and pid.replace("-", " ") in n) or bool(n and n in locked)


def prop_references(brand: str, item: dict, doc: dict, td: Path | None) -> list[tuple[str, Path, str]]:
    """The REAL references a made prop starts from (P65): the run's set picture for a scene the prop is in (made from
    the swipe's frames) and the nearest swipe frame of that scene. [(what, file, from)]."""
    out = []
    world = {w.get("id"): w for w in doc.get("world") or []}
    scenes = {s.get("id"): s for s in doc.get("scenes") or []}
    for sid in item.get("scenes") or []:
        sc = scenes.get(sid) or {}
        w = world.get(sc.get("setting_id")) or {}
        bank = w.get("bank_id") if str(w.get("bank_id") or "").upper() not in ("", "NEW") else EC.slug(sc.get("setting_id") or "")
        if bank and not any(x[0] == "set" for x in out):
            home = EP.elements_home(brand, "sets", bank, WS)
            pic = next((f for pat in ("plates/wide.*", "full/plates/wide.*", "plates/*.jpg", "full/plates/*.png")
                        for f in sorted(home.glob(pat)) if f.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
            if pic:
                out.append(("set", pic, f"the run's set {bank}, made from the swipe's frames ({pic.relative_to(WS)})"))
        if td and not any(x[0] == "swipe" for x in out):
            ks = re.findall(r"\bK\d{2,3}\b", json.dumps(sc))
            try:
                rows = json.loads((td / "framemap" / "frames" / "index.json").read_text())["frames"]
            except (OSError, ValueError, KeyError):
                rows = []
            hit = next((r for k in ks for r in rows if r.get("shot") == k), None) or (rows[0] if rows else None)
            if hit and (td / "framemap" / hit["file"]).is_file():
                f = td / "framemap" / hit["file"]
                out.append(("swipe", f, f"{td.name}/source.mp4 at {hit.get('t')} s ({hit.get('shot')})"))
    return out


def make_prop(brand: str, item: dict, doc: dict, td: Path | None, run_name: str, dry: bool,
              generate=None, review=None) -> tuple[str, str]:
    """THE THIRD ROUTE (P65, 2026-10-21): a prop the swipe never shows and the bank does not hold is MADE — one picture
    on the house picture model (GPT Image 2.5; a refusal goes to the house backup, P48) from the brief's own
    definition (name, size, look; absurd and hyper-specific when the brief says so, V24) with REAL references
    attached (the run's set picture and the nearest swipe frame), on a clean surface at true size; then the picture
    review v4 for slop, one remake with its fixes; banked with picture, prop.md and provenance listing the real
    references. A product is never drawn (V16). Nothing passing the review is banked → ('', why)."""
    if _is_product(doc, item["id"]):
        return "", "the product is never drawn (V16) — its real photograph is laid on in the edit"
    d = prop_definition(doc, item["id"])
    if not d.get("look"):
        return "", "the brief gives this prop no look (props[]: name, size, look) — nothing to make it from"
    refs = prop_references(brand, item, doc, td)
    if not any(w == "swipe" for w, _f, _x in refs):
        # the swipe frame is the REAL reference (the set picture is itself made, so it rides along, never alone)
        return "", "no real reference to start from (no swipe frame for its scene) — nothing is drawn from words alone"
    prompt = PROP_PROMPT.format(name=d.get("name") or item["id"], look=str(d["look"]).rstrip("."),
                                size=d.get("size") or "as the brief says")
    # ONE OBJECT, ONE LOOK (V11): a prop the brief makes "matching" / "the same" as one already banked for this run
    # (the green pitcher of the gold one) starts from that picture, so the two are the same object
    twin = _twin_prop(brand, item, doc, run_name)
    if twin:
        refs = [("twin", twin, f"the matching prop banked for this run ({twin.parent.name})")] + refs
        prompt += (" The first reference is the matching object already made for this ad: the SAME object — same "
                   "shape, size, material, lid and handle — only what the words above change is different.")
    if dry:
        return "would make it from the brief's definition", " · ".join(w for w, _f, _x in refs)
    root = EP.elements_home(brand, "props", "x", WS).parent
    dst = root / item["bank_id"]
    (dst / "reference").mkdir(parents=True, exist_ok=True)
    kept = []
    for what, f, src in refs:
        name = f"{what}-{f.name}"
        shutil.copy2(f, dst / "reference" / name)
        kept.append((what, dst / "reference" / name, src))
    gen = generate or _mod(HERE / "direct_openai.py", "vm_ae_direct_openai").generate
    out = dst / "picture.png"
    res = gen(prompt, [f for _w, f, _s in kept], out)
    rv = review or _prop_review
    probs = rv(dst, d, out, [f for _w, f, _s in kept])
    remade = None
    if probs:
        fixes = "; ".join(str(p.get("fix") or p.get("what") or "") for p in probs)
        edit = (f"Edit this picture. Change ONLY these things and keep everything else exactly as it is: {fixes}. "
                "Nothing else in the picture: no person, no hands, no product, no words.")
        (dst / "versions").mkdir(exist_ok=True)
        shutil.copy2(out, dst / "versions" / "picture-v1.png")
        res = gen(edit, [out], out)                     # the picture alone: a second picture pulled the edit away from it
        remade = fixes
        probs = rv(dst, d, out, [f for _w, f, _s in kept])
    if probs:
        bad = dst / "versions" / "held-picture.png"
        bad.parent.mkdir(exist_ok=True)
        shutil.move(str(out), bad)                      # never banked flagged (P42): the elements lock will not see it
        return "", "made, but the picture review still finds: " + "; ".join(str(p.get("what")) for p in probs)[:300]
    (dst / "prop.md").write_text(
        f"# {d.get('name') or item['id']}\n\n**Size:** {d.get('size') or '—'}\n\n**Look:** {d['look']}\n\n"
        f"Made by the system (production on Auto) from the brief's own definition, with the real references in "
        f"`reference/`: " + "; ".join(src for _w, _f, src in kept) + f".\n\nRuns: {run_name}\n")
    (dst / "provenance.json").write_text(json.dumps({
        "element": item["bank_id"], "kind": "prop", "made": time.strftime("%Y-%m-%d"),
        "definition": d,
        "real_references": [{"file": f"reference/{f.name}", "kind": "real video frame", "from": src,
                             "use": "the video's light, colour and feel the prop is made to match"}
                            for w, f, src in kept if w == "swipe"],
        "also_attached": [{"file": f"reference/{f.name}",
                           "what": ("the run's set picture (made from the swipe's frames)" if w == "set"
                                    else "the matching prop already banked for this ad"),
                           "from": src, "use": ("the room, counter and light the prop stands in" if w == "set"
                                                else "the same object — one object, one look (V11)")}
                          for w, f, src in kept if w != "swipe"],
        "made_with": {"picture": res.get("model"), "door": res.get("door") or "openai", "prompt": prompt,
                      **({"backup_for": res["backup_for"]} if res.get("backup_for") else {}),
                      **({"remade_with": remade} if remade else {}), "review": "picture-review-v4 (no problems left)",
                      "tool": "auto_elements.make_prop"},
        "rights": "an original picture of an unbranded object, made from our own set picture and the swipe's frame as references",
        "drive": f"Shared Assets/runs/ai-elements/{brand}/props/{item['bank_id']}/",
        "made_by": BY, "runs": [run_name]}, indent=1, ensure_ascii=False))
    return f"made from the brief's definition on {res.get('model')}", "real references: " + "; ".join(w for w, _f, _s in kept)


def _made_as_other(folder: Path, name: str) -> bool:
    """A prop MADE from another prop's own definition (P65) is that object — the gold pitcher is never copied in as
    the green one by a shared word."""
    try:
        d = json.loads((folder / "provenance.json").read_text()).get("definition") or {}
    except (OSError, ValueError):
        return False
    norm = lambda t: " ".join(re.findall(r"[a-z0-9']+", str(t or "").lower()))
    return bool(d.get("name")) and norm(d["name"]) != norm(name)


def _twin_prop(brand: str, item: dict, doc: dict, run_name: str) -> Path | None:
    """The picture of a prop already banked for this run that this one must match (V11), or None."""
    d = prop_definition(doc, item["id"])
    if not re.search(r"\b(matching|the same|identical|twin)\b", str(d.get("look") or ""), re.I):
        return None
    mine = _words(item["id"])
    root = EP.elements_home(brand, "props", "x", WS).parent
    for f in sorted(root.iterdir()) if root.is_dir() else []:
        if not f.is_dir() or f.name == item["bank_id"] or not (mine & _words(f.name.replace("-", " "))):
            continue
        try:
            runs = json.loads((f / "provenance.json").read_text()).get("runs") or []
        except (OSError, ValueError):
            continue
        pic = next((x for x in (f / "picture.png", f / "picture.jpg") if x.is_file()), None)
        if run_name in runs and pic:
            return pic
    return None


def _prop_review(dst: Path, d: dict, pic: Path, refs: list) -> list:
    """The picture review v4 on a made prop (slop, size, the brief's own words). [] = no problems."""
    V = _mod(HERE / "v2_checks.py", "vm_ae_v2_checks")
    cfg = json.loads((HERE / "v2.json").read_text())
    tmpl = (WS / cfg["review"]["prompt"]).read_text()
    brief = (f"- the picture: ONE prop on its own, no person, no hands, no product, no words\n- prop: {d.get('name')}\n"
             f"- real size: {d.get('size')}\n- look: {d.get('look')}")
    text, _info = V.ask(None, f"prop-{dst.name}-review", tmpl.replace("{brief}", brief).replace("{look}", "as the reference room"),
                        [pic] + list(refs)[:2], model=V.model_of(cfg["checks"]["review_model"]))
    ans = V.json_of(text) or {"verdict": "UNREADABLE", "problems": [{"what": "the review could not be read"}]}
    return [] if ans.get("verdict") == "PASS" else (ans.get("problems") or [{"what": "sent back with no reason"}])


def prop(brand: str, item: dict, td: Path | None, run_name: str, dry: bool, doc: dict | None = None,
         generate=None, review=None) -> tuple[str, str]:
    """(decision, why) — the prop's folder under its brief id is filled."""
    root = EP.elements_home(brand, "props", "x", WS).parent
    dst = root / item["bank_id"]
    sf = item.get("swipe_frames")
    if sf and sf.get("best"):
        src = WS / sf["best"]["file"]
        if dry:
            return "would make from the swipe's crop", sf["best"]["file"]
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "reference").mkdir(exist_ok=True)
        shutil.copy2(src, dst / "reference" / src.name)
        shutil.copy2(src, dst / "picture.jpg")
        (dst / "prop.md").write_text(f"# {item['id']}\n\nThe swipe's own {sf.get('name')}, cut from its real frame "
                                     f"({sf['best']['file']}). picture.jpg IS that frame — nothing generated.\n\nRuns: {run_name}\n")
        (dst / "provenance.json").write_text(json.dumps({
            "element": item["bank_id"], "kind": "prop", "made": time.strftime("%Y-%m-%d"),
            "real_references": [{"file": f"reference/{src.name}", "kind": "real video frame",
                                 "from": f"{sf.get('run')}/source.mp4 at {sf['best'].get('t')} s ({sf.get('element')})",
                                 "use": f"the swipe's {sf.get('name')}"}],
            "rights": "a crop of the swipe's frame used as a reference for an unbranded object; nothing branded kept",
            "made_with": {"pictures": "none generated — picture.jpg IS the real reference", "tool": "auto_elements.py"},
            "drive": f"Shared Assets/runs/ai-elements/{brand}/props/{item['bank_id']}/",
            "made_by": BY, "runs": [run_name]}, indent=1))
        return "made from the swipe's own frame", sf["best"]["file"]
    want = _words(item["id"])
    # THE OBJECT MUST BE THE SAME THING (2026-10-23): "THE BARBER CHAIR" matched the banked black-barber-cape on the
    # shared word "barber" — a prop is only copied from a banked one whose object noun (the name's last word) matches
    noun = (re.findall(r"[a-z]+", str(item["id"]).lower()) or [""])[-1]
    best, score = None, 0.0
    for f in sorted(root.iterdir()) if root.is_dir() else []:
        if f.is_dir() and f.name != item["bank_id"] and _complete(f, "prop") and not _made_as_other(f, item["id"]):
            have = _words(f.name.replace("-", " ")) | ({"phone"} if "phone" in f.name else set())
            if noun and noun.rstrip("s") not in {w.rstrip("s") for w in have}:
                continue
            s = len(want & have) / max(1, len(want | have))
            if s > score:
                best, score = f.name, s
    if not best or score < 0.25:
        # neither the swipe nor the bank has it: MADE from the brief's own definition with real references (P65)
        if doc is not None:
            return make_prop(brand, item, doc, td, run_name, dry, generate=generate, review=review)
        return "", "no banked prop shares its name and the swipe never shows it — needs a real reference image"
    if dry:
        return f"would copy banked prop {best}", f"name overlap {score:.2f}"
    shutil.copytree(root / best, dst, dirs_exist_ok=True)
    p = dst / "provenance.json"
    rec = json.loads(p.read_text())
    rec.update({"element": item["bank_id"], "copied_from": best, "picked_by": BY,
                "runs": (rec.get("runs") or []) + [run_name]})
    p.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return f"copied banked prop {best}", f"its name matches the brief's \"{item['id']}\" (overlap {score:.2f})"


# --------------------------------------------------------------------- run

def run(brief: Path, brand: str, run_dir: Path, dry: bool = False, generate=None, review=None,
        manifest=None, confirm=None) -> dict:
    """The whole automatic step, inside the chain (run_v2 start → here, on the batch runner and the mini door alike;
    VIDEO-RULINGS V25): every element still to make is bound or made — a prop the swipe never shows MADE from the
    brief's definition (P65) — then the manifest is re-checked and the sheet confirmed. `generate` / `review` /
    `manifest` / `confirm` are the seams a test fakes; a real run passes none."""
    brief, run_dir = Path(brief).resolve(), Path(run_dir).resolve()
    DRY["on"] = dry
    if not is_auto():
        return {"skipped": "production is on Manual"}
    if run_dir.name.startswith("v2test-"):
        return {"skipped": "v2test runs are never touched"}
    td = EC.resolve_teardown(brief.parent.parent) or EC.teardown_of(brief, run_dir)
    text = brief.read_text()
    sh = EC.sheet(text, brand, root=WS, teardown=td)
    doc = _brief_doc(text)
    # a prop the brief makes "matching" another is made after it, so it can start from its banked twin (V11)
    sh["to_make"] = sorted(sh["to_make"], key=lambda i: i["kind"] == "prop" and bool(re.search(
        r"\b(matching|the same|identical|twin)\b", str(prop_definition(doc, i["id"]).get("look") or ""), re.I)))
    cast = {(c.get("id") or c.get("name")): c for c in doc.get("cast") or []}
    world = {w.get("id"): w for w in doc.get("world") or []}
    run_dir.mkdir(parents=True, exist_ok=True)
    sheet_p = run_dir / "elements.json"
    sheet_p.write_text(json.dumps(sh, indent=1))
    rname, binds, made = run_dir.name, {}, []
    for it in sh["to_make"]:
        k = it["kind"]
        try:
            if k in ("person", "setting"):
                row = cast.get(it["id"], {}) if k == "person" else world.get(it["id"], {})
                folder_now = WS / it["folder"]
                new = (row.get("bank_id") or "").upper() == "NEW" or not folder_now.is_dir()
                bank_id = it["bank_id"]
                if new:
                    got, why = match_banked(brand, it, td)
                    if got:
                        bank_id = got
                        binds[it["id"]] = got
                        log(rname, brand, it, f"bound to banked {k} `{got}`", why, 0.8)
                    elif td:
                        bank_id = (make_person(brand, row, it, doc, td, sheet_p, dry) if k == "person"
                                   else make_set(brand, row, it, td, sheet_p, dry))
                        binds[it["id"]] = bank_id
                        made.append(f"{k} {bank_id}")
                        log(rname, brand, it, f"made new {k} `{bank_id}` from the swipe's frames",
                            "no banked element from this swipe; made from the frames its real reference names", 0.6)
                    else:
                        log(rname, brand, it, "", "no swipe teardown found — nothing to make it from", 0.0)
                        continue
                folder = EP.casting_home(brand, bank_id, WS) if k == "person" else WS / it["folder"]
                if k == "person":
                    need = [lk for lk in it.get("looks") or [] if lk.upper().startswith("NEW")]
                    if need and not dry:
                        lid, score = best_look(folder, need[0])
                        if lid:
                            binds[it["id"] + ".look"] = lid
                            log(rname, brand, {**it, "kind": "look"}, f"look bound to `{lid}` of {bank_id}",
                                f"the closest banked outfit to the brief's (word overlap {score:.2f})", 0.7)
                    if it.get("speaks") and not dry and not (folder / "voice.json").is_file():
                        make_voice(folder, doc, it["id"])
                        log(rname, brand, {**it, "kind": "voice"}, f"made {bank_id}'s own voice from the swipe's audio",
                            "first of three ElevenLabs designs from the swipe's separated speaker, picked by the system", 0.5)
            elif k == "prop":
                dec, why = prop(brand, it, td, rname, dry, doc=doc, generate=generate, review=review)
                log(rname, brand, it, dec or "left to make", why, 0.6 if dec else 0.0)
            else:
                log(rname, brand, it, "left to make", "the system does not make a " + k + " (a product is the brand's real packshot)", 0.0)
        except SystemExit as e:
            log(rname, brand, it, "could not be made", str(e)[:300], 0.0)
        except Exception as e:  # noqa: BLE001
            log(rname, brand, it, "could not be made", f"{type(e).__name__}: {str(e)[:300]}", 0.0)
    if dry:
        return {"binds": binds, "made": made, "dry_run": True}
    if binds:
        EC.bind(brief, dict(binds))
        print("  elements · bound in the brief: " + ", ".join(f"{a}={b}" for a, b in binds.items()))
    # the manifest, re-checked against the bound brief (decision-layer approvals count, as in run.py)
    if manifest is not None:
        ok, missing = manifest(td, brand, brief.name)
        print(f"  manifest: {'COMPLETE' if ok else 'MISSING — ' + ', '.join(missing)}")
    elif brief.parent.name == "stages" and td and (td / "stages" / "2-spec.md").exists():
        try:
            ns = {json.loads(l)["item"].get("n") for l in CALLS.read_text().splitlines()
                  if l.strip() and f'"run": "{td.name}"' in l and '"gate": "manifest"' in l}
            have = [x for x in os.environ.get("DAEMN_STRUCTURE_APPROVALS", "").split(",") if x]
            allv = sorted(set(have) | {n for n in ns if n})
            if allv:
                os.environ["DAEMN_STRUCTURE_APPROVALS"] = ",".join(allv)
        except Exception:  # noqa: BLE001
            pass
        MF = _mod(WS / "tools" / "video-writing" / "machine" / "manifest.py", "vm_ae_manifest")
        ok, missing = MF.check(td, brand, brief.name)
        print(f"  manifest: {'COMPLETE' if ok else 'MISSING — ' + ', '.join(missing)}")
    text = brief.read_text()
    sh = EC.sheet(text, brand, root=WS, teardown=td)
    sheet_p.write_text(json.dumps(sh, indent=1))
    if sh["to_make"] or sh["brief_gaps"]:
        left = [f"{i['kind']} {i['id']}" for i in sh["to_make"]] + sh["brief_gaps"]
        print("  elements · still to make: " + ", ".join(left))
        return {"binds": binds, "made": made, "left": left}
    lock = (confirm or EC.confirm)(run_dir, BY)
    print(f"  elements · confirmed by the system ({len(sh['items'])} elements)")
    return {"binds": binds, "made": made, "confirmed": lock["fingerprint"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief"); ap.add_argument("--brand", required=True); ap.add_argument("--run", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    print(json.dumps(run(Path(a.brief), a.brand, Path(a.run), a.dry_run), indent=1, default=str))
    if not a.dry_run:                                         # the elements index follows every change
        try:                                                  # (components/casting/elements_index.py)
            sys.path.append(str(Path(__file__).resolve().parents[2] / "casting")); import elements_index; elements_index.build()
        except Exception as e:  # noqa: BLE001 — an index that cannot rebuild never stops the make
            print(f"  elements index not rebuilt: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
