#!/usr/bin/env python3
"""STYLE CHAIN — the swipe's visual style is the ONE setting every element of an ad is made in (owner ruling, 12 Nov
2026: the ad is made in the swipe's own style; everything gets that style; a banked element in another style gets a
style variant; switching styles is one setting).

    the ad's style (the one setting, and where it came from)
        python3 style_chain.py style --production <idea>          (a Video Studio production, briefs/<idea>/brief.json)
        python3 style_chain.py style --run <writing or teardown run>
    change it (one setting; everything downstream pulls or makes the variants for the new style)
        python3 style_chain.py set-style --production <idea> <style-id> [--why "..."]
    one element in a style: have it, or what making it takes
        python3 style_chain.py resolve <brand> <person|product|set|world|prop> <id> <style-id>
    every element a production needs, in its style (nothing spent)
        python3 style_chain.py needs --production <idea>
    make what is missing (people through make_character, everything through the 3D print queue)
        python3 style_chain.py ensure --production <idea> [--dry-run]
        python3 style_chain.py ensure-one <brand> <kind> <id> <style-id> [--look <face-free frame>] [--dry-run]

Where the style comes from, in order: the production brief's `style` (the Studio), the writing run's `style_id`, the
teardown run's `style_id` (the teardown detects it from the swipe). A row of `bank.json` beside this file is a style;
nothing else is.

Where a variant lives: the element's own home, `styles/<style-id>/` inside it
    runs/ai-elements/<brand>/casting/<person>/styles/<style-id>/
    runs/ai-elements/<brand>/products/<kit>/styles/<style-id>/
    runs/ai-elements/<brand>/{sets,worlds,props}/<id>/styles/<style-id>/
An element's master is in its own style (`style_id` in its spec; none = photoreal). Asked for in the master's style, the
master itself serves. Asked for in any other style it is a VARIANT TO MAKE, never a gap and never a reason to change the
ad's look.

How a variant is made: identity from the element's real master (its master picture, its real references), the look
only from the style (its swatch, or a face-free frame of the swipe when the ad's swipe is in that style), through the
3D print process (image-production set queue, `.claude/skills/3d-print`). People then get their full casting set from
make_character with the style lock (the print goes in first, GATE-4). Products, sets, worlds and props: the kept print
is the variant's picture. Identity never changes; only the rendering style does.

A non-human cast member (a personified object, creature or cartoon: `is_character`, the rule is written there) is not
cast as a person: one real photo in its casting `reference/` folder, one 3D print in the ad's style, and the kept print
is its master picture (`new_character`), with no person sheets.

Agnostic: no brand, person, style or machine is named here. Nothing in this file calls a model.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE / "bank.json"
KINDS = {"person": "casting", "product": "products", "set": "sets", "world": "worlds", "prop": "props"}
# the master picture each kind is recognised by, in order (the first that exists is the element's picture)
MASTER_FILES = ("master.jpg", "full/master.png", "picture.png", "picture.jpg", "model/product-sheet.png",
                "render.png", "print.png")
PHOTOREAL = "photoreal"                 # the folder of a photoreal variant of a master born in a style
VARIANT_PICTURE = "picture.png"         # a printed (non-person) variant's picture, in its styles/<id>/ folder


# ── the bank ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def workspace() -> Path:
    """Where the data is (runs/): AI_WORKSPACE when set (a worktree reads the main checkout's runs), else the workspace
    the Video Studio's writing runs sit in (a deployed Studio copy carries code only), else this repo."""
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "runs").is_dir():
        return Path(env)
    w = os.environ.get("VIDEO_STUDIO_WRITING")        # the Studio's data: the workspace its writing runs sit in
    for p in (Path(w).parents if w else []):
        if (p / "runs" / "ai-elements").is_dir():
            return p
    return HERE.parents[2]


def _bank(path: Path | None = None) -> dict:
    return json.loads(Path(path or BANK).read_text())


def rows(path: Path | None = None) -> list:
    return _bank(path).get("styles") or []


def row(sid: str, path: Path | None = None) -> dict:
    """The bank row for a style id (or one of its aliases). Refuses a style the bank does not hold, by name."""
    s = str(sid or "").strip()
    for r in rows(path):
        if r.get("id") == s or s in (r.get("aliases") or []):
            return r
    raise SystemExit(f"style {s!r} is not a row of {BANK.name}: name a real style id (python3 style_chain.py styles)")


def canonical(sid) -> str | None:
    """The style id as the bank spells it; None for no style (photoreal, the real-footage look)."""
    if isinstance(sid, dict):
        sid = sid.get("id")
    if not sid:
        return None
    return row(sid)["id"]


def is_photoreal(sid) -> bool:
    """No style, or a style of the photoreal family (it looks filmed): real footage and real photos fit it."""
    sid = canonical(sid)
    return sid is None or row(sid).get("family") == "photoreal"


def same_look(a, b) -> bool:
    """Two styles that need no variant between them: the same style, or both photoreal (the grade does that work)."""
    a, b = canonical(a), canonical(b)
    return a == b or (is_photoreal(a) and is_photoreal(b))


def formula(sid) -> str | None:
    sid = canonical(sid)
    return row(sid).get("formula") if sid else None


def swatch(sid, ws: Path | None = None) -> Path | None:
    """The style's swatch picture on this machine: beside the bank, else the synced Shared Assets mirror."""
    sid = canonical(sid)
    if not sid:
        return None
    rel = Path(row(sid).get("swatch") or f"swatches/{sid}.jpg")
    comp = HERE.relative_to(HERE.parents[2])
    cands = [HERE / rel, workspace() / comp / rel]
    for root in (list(Path.home().glob("Library/CloudStorage/*/Shared drives/Shared Assets"))
                 + [Path.home() / ".upright" / "cache" / "drive" / "Shared Assets"]):
        cands.append(root / comp / rel)
    return next((c for c in cands if c.is_file()), None)


# ── the one setting ──────────────────────────────────────────────────────────────────────────────────────────────────

def _studio_briefs() -> Path:
    env = os.environ.get("VIDEO_STUDIO_DATA")
    return Path(env) / "briefs" if env else workspace() / "runs" / "video-studio" / "briefs"


def _writing_runs() -> Path:
    env = os.environ.get("VIDEO_STUDIO_WRITING")
    return Path(env) if env else workspace() / "runs" / "video-teardown" / "_work"


def _read(p: Path) -> dict:
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


def brief_path(production: str, briefs: Path | None = None) -> Path:
    return Path(briefs or _studio_briefs()) / production / "brief.json"


def run_style(run: str, writing: Path | None = None) -> dict:
    """A writing or teardown run's style: its own `style_id`, else the teardown run it was written from."""
    base = Path(writing or _writing_runs())
    seen = set()
    while run and run not in seen:
        seen.add(run)
        rj = _read(base / run / "run.json")
        if rj.get("style_id"):
            return {"id": canonical(rj["style_id"]), "from": f"run {run} style_id"}
        run = rj.get("teardown") or rj.get("source_run") or (rj.get("writing_lane") or {}).get("teardown")
    return {"id": None, "from": "no style on the run (photoreal)"}


def ad_style(production: str | None = None, run: str | None = None, briefs: Path | None = None,
             writing: Path | None = None) -> dict:
    """THE setting: {id, from}. The production brief's `style` wins (the Studio), then the writing run, then its
    teardown. id None = photoreal (the real-footage look)."""
    if production:
        b = _read(brief_path(production, briefs))
        st = b.get("style")
        if st:
            sid = st.get("id") if isinstance(st, dict) else st
            return {"id": canonical(sid), "from": f"production {production} brief.json style"
                    + (f" ({st.get('from')})" if isinstance(st, dict) and st.get("from") else "")}
        run = run or b.get("brief") or b.get("run")
    if run:
        return run_style(run, writing)
    return {"id": None, "from": "nothing named (photoreal)"}


def set_ad_style(production: str, sid, why: str = "", briefs: Path | None = None) -> dict:
    """Change the ad's style: ONE setting. Every later step reads it and pulls or makes the variants it needs."""
    p = brief_path(production, briefs)
    b = _read(p)
    if not b:
        raise SystemExit(f"no production brief at {p}")
    new = canonical(sid)
    old = b.get("style")
    b["style"] = {"id": new, "from": why or "set by hand (style_chain.py set-style)",
                  "set": time.strftime("%Y-%m-%dT%H:%M:%S"),
                  "rule": "the ad is made in the swipe's style; every element is pulled or made in it"}
    if old and (old.get("id") if isinstance(old, dict) else old) != new:
        b.setdefault("style_history", []).append(old)
    p.write_text(json.dumps(b, indent=1, ensure_ascii=False) + "\n")
    return b["style"]


# ── one element in one style ─────────────────────────────────────────────────────────────────────────────────────────

def bank_roots(ws: Path | None = None) -> list:
    """Every workspace whose element bank counts, in order: the data workspace, then this code's own (a deployed Studio
    copy files the elements its own ads make beside its code). An element is found in whichever holds it."""
    out = []
    for r in ([Path(ws)] if ws else [workspace(), HERE.parents[2]]):
        if r not in out:
            out.append(r)
    return out


def element_home(brand: str, kind: str, eid: str, ws: Path | None = None) -> Path:
    """The element's folder: the first bank that holds it, else where a new one is filed (the first bank)."""
    if kind not in KINDS:
        raise SystemExit(f"kind {kind!r}: one of {', '.join(KINDS)}")
    homes = [r / "runs" / "ai-elements" / brand / KINDS[kind] / eid for r in bank_roots(ws)]
    return next((h for h in homes if h.is_dir()), homes[0])


def master_style(home: Path) -> str | None:
    """The style the element's master is in: its spec / element record's `style_id`; none = photoreal."""
    for f in ("spec.json", "element.json", "kit.json", "world.json", "provenance.json"):
        d = _read(home / f)
        sid = d.get("style_id") or (d.get("style") if isinstance(d.get("style"), str) else None)
        if sid and f != "provenance.json":
            return canonical(sid)
    return None


def picture_of(d: Path) -> Path | None:
    return next((d / f for f in MASTER_FILES if (d / f).is_file()), None)


def variant_dir(home: Path, sid) -> Path:
    """Where the element lives in this style: the master itself when the master is in it, else styles/<id>/."""
    if same_look(master_style(home), sid):
        return home
    return home / "styles" / (canonical(sid) or PHOTOREAL)


def resolve(brand: str, kind: str, eid: str, sid, ws: Path | None = None) -> dict:
    """{state: master | have | make | no-master, dir, picture, ...}. `make` is never a gap: ensure_one makes it."""
    sid = canonical(sid)
    home = element_home(brand, kind, eid, ws)
    out = {"brand": brand, "kind": kind, "id": eid, "style": sid, "home": str(home)}
    if not home.is_dir() or picture_of(home) is None:
        return dict(out, state="no-master", dir=None, picture=None,
                    next=("cast it first, in this style: casting/cast.py build --style %s" % (sid or "photoreal")
                          if kind == "person" else "bank its master first (its kit / element folder), then ensure it"))
    d = variant_dir(home, sid)
    pic = picture_of(d)
    if d == home:
        return dict(out, state="master", dir=str(d), picture=str(pic))
    if kind == "person":            # a person is had once their whole sheet set is recorded, not at a half-made master
        pic = d / "master.jpg" if (d / "master.jpg").is_file() and (d / "provenance.json").is_file() else None
    if pic is not None:
        return dict(out, state="have", dir=str(d), picture=str(pic))
    return dict(out, state="make", dir=str(d), picture=None, master=str(picture_of(home)),
                next=f"python3 components/video-production/styles/style_chain.py ensure-one {brand} {kind} {eid} {sid}")


def element_file(brand: str, kind: str, eid: str, sid, rel: str, ws: Path | None = None) -> Path:
    """A file of the element as the ad's style needs it (a look sheet, the headshot): from the variant when there is
    one. Used by every step that hands a picture of the element on, so a take never carries the wrong style."""
    home = element_home(brand, kind, eid, ws)
    return variant_dir(home, sid) / rel if home.is_dir() else home / rel


def element_ref(eid: str, sid, home: Path) -> str:
    """The element as a casting/board reference: `<id>` for the master, `<id>/styles/<style>` for a variant (the cast
    board and the Studio read an element by its folder under the kind's root)."""
    d = variant_dir(home, sid)
    return eid if d == home else f"{eid}/styles/{d.name}"


# ── the look reference (look only, never a face) ─────────────────────────────────────────────────────────────────────

FACE_WORDS = ("head", "face", "torso", "body", "full", "shoulder", "profile", "eyes")


def face_free_frames(run_dir: Path) -> list[Path]:
    """The swipe's frames that show no face (hands, products, rooms): its look without its people. From the
    teardown's frame map; the middle still of each shot whose `who` names no head, face or body."""
    fm = _read(Path(run_dir) / "framemap" / "framemap.json")
    out = []
    for sh in fm.get("shots") or []:
        who = [str(w).lower() for w in ((sh.get("map") or {}).get("who") or [])]
        if any(any(f in w for f in FACE_WORDS) for w in who):
            continue
        still = Path(run_dir) / "framemap" / "shots" / ((sh.get("stills") or {}).get("mid") or f"{sh.get('id')}-mid.jpg")
        if still.is_file():
            out.append(still)
    return out


def look_reference(sid, run: str | None = None, look: str | None = None, writing: Path | None = None) -> dict | None:
    """The one picture that carries the style's LOOK, never a face to copy: a named frame, else the style's swatch
    (always in the style), else a face-free frame of the ad's swipe when the swipe is in this style. A swipe can mix
    looks (a 3D-animated story with filmed hand and product inserts), so its frames come after the swatch."""
    sid = canonical(sid)
    if not sid or is_photoreal(sid):
        return None
    if isinstance(look, dict) and look.get("file"):
        return look                                  # the ad's pinned look (ad_look): one look for every element
    if look:
        return {"file": str(Path(look).resolve()), "kind": "named look picture", "use": "the look only"}
    sw = swatch(sid)
    if sw:
        return {"file": str(sw), "kind": "style swatch", "from": f"{BANK.name} {sid}",
                "use": "the look only: surfaces, light, rendering — never its faces or layout"}
    base = Path(writing or _writing_runs())
    seen = set()
    while run and run not in seen:
        seen.add(run)
        rj = _read(base / run / "run.json")
        if rj.get("style_id") and canonical(rj["style_id"]) == sid:
            frames = face_free_frames(base / run)
            if frames:
                return {"file": str(frames[len(frames) // 2]), "kind": "face-free swipe frame",
                        "from": f"{run} frame map", "use": "the look only: surfaces, light, rendering — never a face"}
        run = rj.get("teardown") or rj.get("source_run")
    return None


def ad_look(production: str, briefs: Path | None = None, pin: bool = True) -> dict | None:
    """ONE look per ad: the look reference every element of this production is made with, pinned in its brief.json
    (`style.look`) the first time it is asked for, so every person, location, product and prop gets the same picture
    and the same words. None for a photoreal ad. A pinned look whose file is gone is chosen again."""
    p = brief_path(production, briefs)
    b = _read(p)
    st = ad_style(production, briefs=briefs)
    if not st["id"] or is_photoreal(st["id"]):
        return None
    cur = (b.get("style") or {}).get("look") if isinstance(b.get("style"), dict) else None
    if cur and cur.get("style") == st["id"] and Path(cur.get("file", "")).is_file():
        return cur
    lk = look_reference(st["id"], b.get("brief"))
    if lk and pin and b:
        lk = dict(lk, style=st["id"], pinned=time.strftime("%Y-%m-%dT%H:%M:%S"))
        style = b.get("style") if isinstance(b.get("style"), dict) else {"id": st["id"]}
        b["style"] = dict(style, look=lk)
        p.write_text(json.dumps(b, indent=1, ensure_ascii=False) + "\n")
    return lk


# ── making a variant ─────────────────────────────────────────────────────────────────────────────────────────────────

def _rel(p, start: Path) -> str:
    return os.path.relpath(str(p), str(start))


REALISM = re.compile(r"\b(pores?|photo ?real\w*|natural skin|real skin|skin texture|beauty[- ]filter|unretouched|"
                     r"natural texture|photograph\w*)\b", re.I)


def unreal(who: str) -> str:
    """A person's identity words without the photoreal ones (pores, natural skin texture): in a styled variant those
    words pull the drawing back to photoreal. Every identity mark (hair, eyes, jaw, freckles, jewellery) stays."""
    parts = re.split(r"(?<=[,;.])\s+", str(who or ""))
    return " ".join(p for p in parts if not REALISM.search(p)).strip()


def person_variant_spec(home: Path, sid, look: dict | None, out: Path) -> dict:
    """The make_character spec for a person in another style. Identity: the master's words, real references and master
    picture, unchanged. Look: the style lock (make_character leads every prompt with the formula) plus the look
    reference. Paths are written relative to the variant folder, so the spec runs on any machine."""
    sid = canonical(sid)
    m = _read(home / "spec.json")
    if not m:
        raise SystemExit(f"{home.name}: no spec.json in the master; a variant is made from a documented master")
    r = row(sid)

    def at(p):                         # a path the master's spec wrote: absolute, beside the master, or in the workspace
        f = Path(p)
        if f.is_absolute():
            return f
        return home / f if (home / f).exists() else workspace() / f

    def moved(refs):
        return [dict(x, file=_rel(at(x["file"]), out)) for x in refs or []]

    looks = {k: dict(v, refs=[_rel(at(r), out) for r in v.get("refs") or []]) if isinstance(v, dict) else v
             for k, v in (m.get("looks") or {}).items()}

    prod = [{"file": _rel(picture_of(home), out), "kind": "approved production picture",
             "from": f"the banked master ({home.name})", "use": "identity: who they are, every mark and proportion"}]
    prod += moved(m.get("production_references"))
    if look:
        prod.append(dict(look, file=_rel(look["file"], out)))
    spec = {k: v for k, v in m.items() if k not in ("history", "runs", "higgsfield_element", "texture", "set", "sets",
                                                     "style", "style_id")}
    if not is_photoreal(sid):
        spec["who"] = unreal(m.get("who", ""))
    spec.update({
        "style_id": sid, "style": sid, "variant_of": _rel(home, out),
        "real_references": moved(m.get("real_references")),
        "body_references": moved(m.get("body_references")),
        "looks": looks,
        "production_references": prod,
        "adjustments": [f"rendered in the {sid} look — {r['formula']}; never photoreal",
                        f"identity carried from the banked {m.get('id', home.name)}: face, hair, build, age, every "
                        "mark and every outfit stay exactly theirs; only the rendering style changes"]
                       + list(m.get("adjustments") or []),
        "set": f"cast-{m.get('id', home.name)}-{sid}",
    })
    return spec


def _set_queue():
    root = HERE.parents[1] / "image-production"
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from image_production import set_gate, set_queue  # noqa: E402
    return set_gate, set_queue


def print_request(brand: str, kind: str, eid: str, sid, home: Path, look: dict | None, ws: Path | None = None) -> dict:
    """The 3D print request that makes the variant's picture: the element's master as identity, the look reference as
    the look, the style's formula in the words. Filed in the image-production set queue; the 3d-print skill clears it."""
    sid = canonical(sid)
    name = f"{'cast' if kind == 'person' else kind}-{eid}-{sid}"
    master = picture_of(home)
    who = str(_read(home / "spec.json").get("who") or "").strip()
    who = re.sub(r"\s+", " ", who)
    what = {"person": f"{eid}, the banked person, as a full-body figure at their true build, standing, plain backdrop"
                      + (f". Who they are, exactly as their sheet shows: {who}. Their true age, build, eye colour and "
                         "every mark stay theirs: never younger, slimmer or smoother than the sheet" if who else "")
                      + ". The person only: no props, products, bottles or other objects",
            "product": f"the {eid} product alone at its true size, its casting-sheet angle, plain surface",
            "set": f"the {eid} set, empty, from its own camera", "world": f"the {eid} world, its main room, empty",
            "prop": f"the {eid} prop alone at its true size on a plain surface"}[kind]
    return {"name": name, "what": f"{what} — in the {sid} style", "style": sid, "style_formula": formula(sid),
            "kind": kind, "element": eid,
            "products": [eid] if kind == "product" else [],
            "cast": [eid] if kind == "person" else [],
            "identity_reference": str(master) if master else None,
            "look_reference": (look or {}).get("file"),
            "resume": {"tool": "style_chain", "brand": brand, "kind": kind, "id": eid, "style": sid,
                       "command": f"python3 components/video-production/styles/style_chain.py ensure-one "
                                  f"{brand} {kind} {eid} {sid}"}}


def adopt_print(brand: str, kind: str, eid: str, sid, d: Path, set_gate) -> Path | None:
    """A kept print of the variant's request becomes the variant's picture (non-person kinds)."""
    kp = set_gate.kept_print(brand, f"{kind}-{eid}-{canonical(sid)}")
    if kp is None:
        return None
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(kp, d / VARIANT_PICTURE)
    return d / VARIANT_PICTURE


def provenance(d: Path, home: Path, sid, look: dict | None, how: str) -> None:
    rec = {"_what": "A style variant: the banked element in another rendering style. Identity from the master, the "
                    "look from the style. Made by components/video-production/styles/style_chain.py.",
           "element": home.name, "style": canonical(sid), "variant_of": _rel(home, d),
           "identity_from": _rel(picture_of(home), d), "look_from": look, "how": how,
           "made": time.strftime("%Y-%m-%d")}
    # a person variant's sheets were written by make_character with their own provenance (kind, real references, how
    # each sheet was made): kept, so the elements check reads the variant as a documented person (20 Nov 2026: a
    # variant's record without `kind` and `real_references` was refused as undocumented)
    old, master = _read(d / "provenance.json"), _read(home / "provenance.json")
    refs = old.get("real_references") or [dict(r, file=_rel(home / r["file"], d)) if r.get("file") else r
                                          for r in master.get("real_references") or [] if isinstance(r, dict)]
    carried = ("kind", "rights", "made_with", "drive", "runs")    # the master's documentation the variant shares
    rec = {**{k: master[k] for k in carried if k in master}, **{k: v for k, v in old.items() if k != "_what"}, **rec}
    if refs:
        rec["real_references"] = refs
    (d / "provenance.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")


def ensure_one(brand: str, kind: str, eid: str, sid, run: str | None = None, look=None,
               dry_run: bool = False, ws: Path | None = None) -> dict:
    """Have the element in this style, or move it one step closer: file the print, adopt a kept print, build the
    person's sheets. Re-run after each print; it never makes a step twice and never spends on a dry run."""
    res = resolve(brand, kind, eid, sid, ws)
    if res["state"] in ("master", "have", "no-master"):
        return res
    home, d = Path(res["home"]), Path(res["dir"])
    lk = look_reference(sid, run, look)
    req = print_request(brand, kind, eid, sid, home, lk, ws)
    if dry_run:
        return dict(res, would="print then " + ("make_character in the style" if kind == "person" else "adopt the print"),
                    request=req)
    set_gate, set_queue = _set_queue()
    kept = set_gate.kept_print(brand, req["name"])
    if kept is None:
        f = set_queue.file(brand, req["what"], name=req["name"], products=req["products"], cast=req["cast"],
                           resume=req["resume"], source="style_chain", style=req["style"],
                           style_formula=req["style_formula"], identity_reference=req["identity_reference"],
                           look_reference=req["look_reference"], element={"kind": kind, "id": eid})
        return dict(res, state="queued", request=str(f), next="the 3d-print skill prints it, then run this again")
    d.mkdir(parents=True, exist_ok=True)
    if kind != "person":
        pic = adopt_print(brand, kind, eid, sid, d, set_gate)
        provenance(d, home, sid, lk, f"the kept 3D print of set {req['name']}")
        return dict(res, state="have", picture=str(pic))
    spec = person_variant_spec(home, sid, lk, d)
    sp = d / "spec.json"
    sp.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    mc = _make_character()
    mc.build(sp, out=d)
    provenance(d, home, sid, lk, f"make_character with the style lock, from the kept 3D print of set {req['name']}")
    return resolve(brand, kind, eid, sid, ws)


def _make_character():
    import importlib.util
    f = HERE.parent / "machine" / "make_character.py"
    s = importlib.util.spec_from_file_location("vp_make_character", f)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


# ── a production's needs ─────────────────────────────────────────────────────────────────────────────────────────────

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def cast_ids(production: str, brand: str, briefs: Path | None = None, ws: Path | None = None) -> dict:
    """Every cast member the production's takes name -> their banked element id (the take's `element`, else the
    name as a casting folder, else a casting folder the name's last word matches), or None when not banked yet."""
    base = Path(briefs or _studio_briefs()) / production / "scenes"
    root = Path(ws or workspace()) / "runs" / "ai-elements" / brand / "casting"
    names = {}
    for f in sorted(base.glob("*/take*.json")):
        for name, c in ((_read(f).get("cast") or {}).items()):
            el = (c or {}).get("element") if isinstance(c, dict) else None
            if el:
                names[name] = el.split("/styles/")[0]
            names.setdefault(name, None)
    for name, el in list(names.items()):
        if el:
            continue
        for cand in (_slug(name), _slug(name).split("-")[-1]):
            if (root / cand).is_dir():
                names[name] = cand
                break
    return names


def writing_cast(run: str, writing: Path | None = None) -> list:
    """The writing run's cast (its stage-5 production brief): [{name, bank_id}], bank_id "NEW" for a person to cast."""
    f = Path(writing or _writing_runs()) / str(run) / "stages" / "5-brief.md"
    try:
        doc = json.loads(re.findall(r"```json\s*\n(.*?)\n```", f.read_text(), re.S)[-1])
    except (OSError, ValueError, IndexError):
        return []
    return [dict(c, name=c.get("name") or c.get("id")) for c in doc.get("cast") or []]


def needs(production: str, briefs: Path | None = None, ws: Path | None = None) -> dict:
    """Every person, product and set the production needs, each in the ad's style: master, have, make, no-master.
    People: the writing brief's cast, then any other name the takes cast."""
    b = _read(brief_path(production, briefs))
    st = ad_style(production, briefs=briefs)
    run = _read(_writing_runs() / str(b.get("brief")) / "run.json")
    brand = (b.get("shot_fill") or {}).get("brand") or b.get("brand") or run.get("brand")
    out = {"production": production, "style": st, "brand": brand, "elements": []}
    root = element_home(brand, "person", "_", ws).parent
    people = {}
    for c in writing_cast(b.get("brief")):
        bid = c.get("bank_id")
        people[c["name"]] = bid if bid and bid.upper() != "NEW" and (root / bid).is_dir() else None
    last = {_slug(n).split("-")[-1]: n for n in people}
    for name, el in cast_ids(production, brand, briefs, ws).items():
        if name in people or _slug(name).split("-")[-1] in last:
            key = name if name in people else last[_slug(name).split("-")[-1]]
            people[key] = people[key] or el
            continue
        people[name] = el
    for name, el in people.items():
        if el:
            out["elements"].append(dict(resolve(brand, "person", el, st["id"], ws), name=name))
        elif (root / _slug(name)).is_dir() and picture_of(root / _slug(name)):
            out["elements"].append(dict(resolve(brand, "person", _slug(name), st["id"], ws), name=name))
        else:
            out["elements"].append({"kind": "person", "name": name, "id": _slug(name), "state": "no-master",
                                    "style": st["id"], "next": "cast it in the ad's style: casting/cast.py build "
                                                               f"--style {st['id'] or 'photoreal'}, filed at casting/"
                                                               f"{_slug(name)}/ with style_id {st['id']}"})
    for p in b.get("products") or ([run["product"]] if run.get("product") else []):
        if element_home(brand, "product", p, ws).is_dir():
            out["elements"].append(resolve(brand, "product", p, st["id"], ws))
    for s in b.get("sets") or []:
        out["elements"].append(resolve(brand, "set", s, st["id"], ws))
    # every location the writing brief names: one set each, made once in the ad's style, the reference for every shot
    for w in writing_world(b.get("brief")):
        sid_ = _slug(w["id"])
        bank = w.get("bank_id") if w.get("bank_id") and str(w["bank_id"]).upper() != "NEW" else sid_
        r = resolve(brand, "set", bank, st["id"], ws)
        out["elements"].append(dict(r, name=w["id"], id=bank))
    return out


def writing_world(run: str, writing: Path | None = None) -> list:
    """The writing run's locations (its stage-5 brief `world`): [{id, description, light, real_reference, ...}]."""
    f = Path(writing or _writing_runs()) / str(run) / "stages" / "5-brief.md"
    try:
        doc = json.loads(re.findall(r"```json\s*\n(.*?)\n```", f.read_text(), re.S)[-1])
    except (OSError, ValueError, IndexError):
        return []
    return [w for w in doc.get("world") or [] if w.get("id")]


def role_frame(run: str, name: str, said: str = "", writing: Path | None = None) -> dict | None:
    """The swipe frame a new person is built from: the frame the brief names ("swipe frame K113"), else the first shot
    whose `who` names the role with a face or head. {file, shot, t}, or None."""
    base = Path(writing or _writing_runs())
    seen = set()
    while run and run not in seen:
        seen.add(run)
        d = base / run
        fm = _read(d / "framemap" / "framemap.json")
        shots = fm.get("shots") or []
        want = re.findall(r"\bK\d{2,3}\b", str(said or ""))
        role = _slug(name).split("-")[-1]
        pick = next((sh for sh in shots if sh.get("id") in want), None)
        if not pick:
            # the role's shots, best first: the role alone in the shot, then the most of the body seen (a frame map
            # can mislabel one shot; the shot that shows the most of the person is the least likely to be wrong)
            def score(sh):
                who = [str(w).lower() for w in (sh.get("map") or {}).get("who") or []]
                mine = [w for w in who if role in w]
                if not mine or not any(f in mine[0] for f in ("face", "head")):
                    return None
                body = 3 if "full" in mine[0] else 2 if ("torso" in mine[0] or "upper" in mine[0]) else 1
                return (len(who) == 1, body)
            ranked = [(score(sh), -i, sh) for i, sh in enumerate(shots) if score(sh)]
            pick = max(ranked, key=lambda x: (x[0], x[1]))[2] if ranked else None
        if pick:
            f = d / "framemap" / "shots" / ((pick.get("stills") or {}).get("mid") or f"{pick['id']}-mid.jpg")
            if f.is_file():
                return {"file": str(f), "shot": pick["id"], "t": pick.get("start"), "run": d.name,
                        "others": len((pick.get("map") or {}).get("who") or []) > 1}
        run = _read(d / "run.json").get("teardown") or _read(d / "run.json").get("source_run")
    return None


def _looks_from_brief(run: str, name: str, writing: Path | None = None) -> dict:
    """A new person's looks, as the brief's cast section words them ("**NAME** ... - **Looks:** NEW: <outfit>. Used
    in ..."): {look-N: {outfit, from}}. Empty when the brief words none."""
    f = Path(writing or _writing_runs()) / str(run) / "stages" / "5-brief.md"
    try:
        md = f.read_text()
    except OSError:
        return {}
    m = re.search(r"\*\*%s\*\*(.*?)(?=\n\*\*[A-Z][A-Z ]+\*\*|\n## )" % re.escape(name), md, re.S)
    outfits = re.findall(r"NEW:\s*(.+?)\.\s*(?:Used in|Opening|Real reference|$)", m.group(1), re.M) if m else []
    return {f"look-{i}": {"outfit": o.strip(), "from": f"the production brief's cast ({run})"}
            for i, o in enumerate(outfits, 1)}


def new_person(brand: str, row: dict, sid, run: str, dry_run: bool = False, ws: Path | None = None,
               look: dict | None = None) -> dict:
    """A person the bank does not have yet, cast straight in the ad's style: born in it (their master's style_id IS
    the ad's style), so no variant is needed. From the brief's cast row: identity words, adjustments, the swipe frame
    it names (who we build from, then adjust), the looks. Through the 3D print first (GATE-4), then make_character."""
    if is_character(row):                    # a non-human cast member is never cast as a person
        return new_character(brand, row, sid, run, dry_run, ws, look)
    sid = canonical(sid)
    pid = _slug(row["name"])
    home = element_home(brand, "person", pid, ws)
    out = {"kind": "person", "id": pid, "name": row["name"], "style": sid, "home": str(home)}
    frame = role_frame(run, row["name"], row.get("real_reference"))
    if not frame:
        return dict(out, state="no-master", next="no swipe frame shows this person: name a real reference frame")
    look = look_reference(sid, run, look)
    req_name = f"cast-{pid}-{sid or PHOTOREAL}"
    adj = list(row.get("adjustments") or [])
    if sid and not is_photoreal(sid):
        adj = [f"rendered in the {sid} look — {formula(sid)}; never photoreal"] + adj
    adj.append("an original character resembling no real person: built from the frame, then made ours")
    looks = _looks_from_brief(run, row["name"]) or {"look-1": {"outfit": "the outfit the reference frame shows",
                                                               "from": f"swipe frame {frame['shot']}"}}
    rel = lambda p: _rel(p, home)                                          # noqa: E731
    spec = {"id": pid, "brand": brand, "style_id": sid, "style": sid,
            "who": str(row.get("identity_block") or row["name"]).strip(),
            "adjustments": adj,
            "real_references": [{"file": rel(frame["file"]), "kind": "real video frame",
                                 "from": f"{frame['run']}/source.mp4 at {frame['t']} s (frame map {frame['shot']})",
                                 "use": f"the swipe's {row['name'].lower()}: who we build from, then adjust"}],
            "production_references": ([dict(look, file=rel(look["file"]))] if look else []),
            "base": "a plain neutral outfit for the sheet", "details": "hands, face close, the ear and hairline",
            "looks": looks, "set": req_name,
            "character": {"title": row["name"], "role": row.get("role") or row["name"].lower(),
                          "why": f"Cast for {run}, born in the ad's style ({sid or PHOTOREAL}).",
                          "age": (re.findall(r"\b(\d{2})\b", str(row.get("identity_block") or "")) or ["as the sheet shows"])[0],
                          "voice": (row.get("voice") or {}).get("source")}}
    if dry_run:
        return dict(out, state="make", would="print then make_character, born in the style", spec=spec)
    set_gate, set_queue = _set_queue()
    if set_gate.kept_print(brand, req_name) is None:
        f = set_queue.file(brand, f"{pid}, a new person, as a full-body figure at their true build, standing, plain "
                                  f"backdrop — in the {sid} style" if sid else f"{pid}, a new person, full body",
                           name=req_name, scene=f"{row['name'].lower()}: " + spec["who"] + ". Made ours: "
                           + "; ".join(row.get("adjustments") or []) + "."
                           + (f" The first reference picture shows other people too: only the {row['name'].lower()} is "
                              "this person; nobody else in it." if frame.get("others") else "")
                           + " The person only, standing full body: no props, products, bottles or other objects.",
                           resume={"tool": "style_chain", "brand": brand, "kind": "person", "id": pid, "style": sid,
                                   "command": "python3 components/video-production/styles/style_chain.py ensure "
                                              "--production <the production>"},
                           source="style_chain", style=sid, style_formula=formula(sid),
                           identity_reference=frame["file"], look_reference=(look or {}).get("file"),
                           element={"kind": "person", "id": pid, "new": True}, people_in_it=True)
        home.mkdir(parents=True, exist_ok=True)
        (home / "spec.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
        return dict(out, state="queued", request=str(f), next="the 3d-print skill prints it, then ensure again")
    home.mkdir(parents=True, exist_ok=True)
    sp = home / "spec.json"
    sp.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    _make_character().build(sp, out=home)
    return resolve(brand, "person", pid, sid, ws)


# ── a non-human cast member (a personified object, creature or cartoon) ─────────────────────────────────────────────
# THE RULE (one place): a cast row is a CHARACTER, not a person, when
#   1. the row says so: `kind` (or `type`) is one of CHARACTER_KINDS, or `creature` / `object` is true; `kind: person`
#      always means a person; else
#   2. its identity words carry a personification marker (CHARACTER_MARKERS) and give no human age (no "28",
#      "mid 20s", "early 50s"...): every human cast row states an age, a drawn object or creature does not.
# A character is never cast as a person: no human headshot, hands, turnaround or expression sheets. It is printed once
# through the 3D print in the ad's style from one real photo of what it is built from (its `reference/` folder), and
# the kept print IS its master picture, filed in its casting folder like a set's (`shown: "character"`), so resolve,
# needs and the elements check (elements-standard.json `person_character`) read it as banked.
CHARACTER_KINDS = {"character", "creature", "object", "animal", "mascot", "prop-character", "non-human"}
CHARACTER_MARKERS = re.compile(r"\b(personified|personification|anthropomorphi\w*|cartoon\w*|mascot|creature|critter|"
                               r"monster)\b", re.I)
HUMAN_AGE = re.compile(r"\b\d{1,3}\b|\b(early|mid|late)[- ]\d0s\b|\b\d0s\b|\b(teen\w*|toddler|baby|infant)\b", re.I)
CHARACTER_SHEET = "sheets/character.jpg"          # the master picture as the character's one look sheet
PICTURE_EXT = (".jpg", ".jpeg", ".png", ".webp")


def is_character(row: dict) -> bool:
    """True when a cast row is a non-human character (THE RULE above), False for a person."""
    k = str(row.get("kind") or row.get("type") or "").strip().lower()
    if k == "person" or k == "human":
        return False
    if k in CHARACTER_KINDS or row.get("creature") is True or row.get("object") is True:
        return True
    words = str(row.get("identity_block") or row.get("who") or "")
    return bool(CHARACTER_MARKERS.search(words)) and not HUMAN_AGE.search(words)


def character_reference(home: Path) -> Path | None:
    """The real photo a character is built from: the first picture in its `reference/` folder (filed with its source,
    `<name>.source.json`), or None when nobody has put one there yet."""
    d = home / "reference"
    pics = sorted(p for p in d.glob("*") if p.suffix.lower() in PICTURE_EXT) if d.is_dir() else []
    return pics[0] if pics else None


def _small(src: Path, dst: Path, w: int) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image
        im = Image.open(src).convert("RGB")
        im.thumbnail((w, w))
        im.save(dst, quality=88)
    except ImportError:                                # no imaging library here: the full picture serves
        shutil.copy2(src, dst)


def new_character(brand: str, row: dict, sid, run: str, dry_run: bool = False, ws: Path | None = None,
                  look: dict | None = None) -> dict:
    """A non-human cast member, made once in the ad's style: one real photo of what it is built from, through the 3D
    print (GATE-4), the kept print adopted as its master picture. No person sheets. Re-run after the print."""
    sid = canonical(sid)
    pid = _slug(row["name"])
    home = element_home(brand, "person", pid, ws)
    out = {"kind": "person", "character": True, "id": pid, "name": row["name"], "style": sid, "home": str(home)}
    who = re.sub(r"\s+", " ", str(row.get("identity_block") or row["name"])).strip()
    ref = character_reference(home)
    if ref is None:
        return dict(out, state="no-master",
                    next=f"put one real photo of what it is built from in {home / 'reference'} (with its source in "
                         f"<name>.source.json; the brief names: {row.get('real_reference') or 'nothing'}), then ensure")
    look = look_reference(sid, run, look)
    req_name = f"cast-{pid}-{sid or PHOTOREAL}"
    src = _read(ref.with_suffix(".source.json")) or _read(ref.parent / (ref.name + ".source.json"))
    rel = lambda p: _rel(p, home)                                          # noqa: E731
    looks_said = _looks_from_brief(run, row["name"])
    outfit = next(iter(looks_said.values()), {}).get("outfit") if looks_said else None
    spec = {"id": pid, "brand": brand, "style_id": sid, "style": sid, "shown": "character", "who": who,
            "adjustments": [f"rendered in the {sid} look — {formula(sid)}" if sid else "photoreal",
                            "a non-human character: drawn as the object or creature it is, never as a person"]
                           + list(row.get("adjustments") or []),
            "real_references": [{"file": rel(ref), "kind": "real photo",
                                 "from": src.get("source_url") or src.get("from") or "see reference/",
                                 "use": f"what the character is built from ({row.get('real_reference') or 'the brief'}); "
                                        "shape and material only"}],
            "production_references": ([dict(look, file=rel(look["file"]))] if look else []),
            "looks": {"look-1": {"outfit": outfit or "as the master picture shows it",
                                 "from": f"the production brief's cast ({run})", "sheet": CHARACTER_SHEET}},
            "set": req_name,
            "character": {"title": row["name"], "role": row.get("role") or "non-human character",
                          "why": f"Cast for {run}, born in the ad's style ({sid or PHOTOREAL}).",
                          "voice": (row.get("voice") or {}).get("source")}}
    if dry_run:
        return dict(out, state="make", would="print the character once, adopt the print as its master", spec=spec)
    set_gate, set_queue = _set_queue()
    kept = set_gate.kept_print(brand, req_name)
    home.mkdir(parents=True, exist_ok=True)
    (home / "spec.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    if kept is None:
        f = set_queue.file(brand, f"{pid}, a non-human character (not a person): {who}. The character alone, whole, at "
                                  f"its true size, plain backdrop" + (f" — in the {sid} style" if sid else ""),
                           name=req_name,
                           scene=f"{row['name'].lower()}: {who}. A non-human character, drawn as the thing it is, never "
                                 "as a person or a human body. The reference photo shows only its real shape and "
                                 "material. Nothing else in the picture: no people, no products, no lettering.",
                           resume={"tool": "style_chain", "brand": brand, "kind": "person", "id": pid, "style": sid,
                                   "character": True, "command": "python3 components/video-production/styles/"
                                                                 "style_chain.py ensure --production <the production>"},
                           source="style_chain", style=sid, style_formula=formula(sid),
                           identity_reference=str(ref), look_reference=(look or {}).get("file"),
                           element={"kind": "person", "id": pid, "new": True, "character": True}, people_in_it=False)
        return dict(out, state="queued", request=str(f), next="the 3d-print skill prints it, then ensure again")
    adopt_character(home, kept, spec, req_name, look)
    return dict(resolve(brand, "person", pid, sid, ws), character=True)


def adopt_character(home: Path, kept: Path, spec: dict, req_name: str, look: dict | None) -> None:
    """The kept print becomes the character's master: picture.png (full), master.jpg and its one look sheet, the
    element record, looks.json, character.md and provenance (shown: character)."""
    shutil.copy2(kept, home / VARIANT_PICTURE)
    (home / "full").mkdir(exist_ok=True)
    shutil.copy2(kept, home / "full" / "master.png")
    _small(kept, home / "master.jpg", 1024)
    _small(kept, home / CHARACTER_SHEET, 1600)
    (home / "element.json").write_text(json.dumps(
        {"id": spec["id"], "kind": "character", "style_id": spec["style_id"], "shown": "character",
         "what": spec["who"], "print": req_name, "picture": VARIANT_PICTURE}, indent=1, ensure_ascii=False) + "\n")
    (home / "looks.json").write_text(json.dumps(
        {"_what": f"The looks a brief may name for {spec['id']} (a non-human character: one look, its master picture).",
         "looks": {k: {kk: vv for kk, vv in v.items()} for k, v in spec["looks"].items()}}, indent=1,
        ensure_ascii=False) + "\n")
    ch = spec.get("character") or {}
    (home / "character.md").write_text(
        f"# {ch.get('title') or spec['id']} — non-human character\n\n"
        f"- **What it is:** {spec['who']}\n- **Style:** {spec['style_id']}\n"
        f"- **Master picture:** `{VARIANT_PICTURE}` (the kept 3D print `{req_name}`), `master.jpg`, `{CHARACTER_SHEET}`\n"
        f"- **Built from:** {spec['real_references'][0]['file']} ({spec['real_references'][0]['from']})\n"
        f"- **Voice:** {ch.get('voice') or 'none'}\n"
        "- No person sheets: it is drawn as the thing it is, never as a human.\n")
    (home / "provenance.json").write_text(json.dumps(
        {"_what": "A non-human character born in the ad's style: its kept 3D print is its master picture. Made by "
                  "components/video-production/styles/style_chain.py new_character.",
         "element": spec["id"], "kind": "person", "shown": "character", "style": spec["style_id"],
         "print": req_name, "real_references": spec["real_references"], "look_from": look,
         "rights": "Original character drawn from a real reference of what it is built from; never a copy of it.",
         "made_with": {"tool": "the 3D print (image-production picture_sets.py, .claude/skills/3d-print)",
                       "set": req_name, "adopted_by": "components/video-production/styles/style_chain.py new_character"},
         "drive": f"Shared Assets/{home.relative_to(home.parents[4]) if len(home.parents) > 4 else home.name}/ "
                  "(full-size: full/master.png, reference/)",
         "made": time.strftime("%Y-%m-%d")}, indent=1, ensure_ascii=False) + "\n")


OBJECT_WORDS = ("bottle", "bottles", "jar", "jars", "tube", "tubes", "pump", "brush", "brushes", "wash", "washes",
                "cleanser", "product", "products", "toiletries", "toiletry", "soap", "razor", "cream", "serum", "lotion",
                "box", "boxes", "packaging", "device")
SURFACE_WORDS = ("ledge", "shelf", "shelves", "counter", "countertop", "table", "tray", "stand", "plinth", "vanity",
                 "nightstand", "dresser", "desk", "sill", "rack", "case", "cabinet", "mantel")


def room_words(description: str, objects=()) -> str:
    """A location's description as a 3D print's words: the ROOM only. A prop or product the brief places in the room
    goes in at the shot, so its mention is taken out here; a surface it stood on stays, said positively ("one shared
    ledge, bare and clear") — a print told "a ledge with a face-wash bottle" and then "every surface bare" keeps the
    bottle (20 Nov 2026: a room printed twice with toiletries on its ledge). A clause that is only an object is
    dropped. `objects` are the brief's own prop and product names."""
    names = [o.lower() for o in objects if o and len(o) > 2]
    # a prop is also found by any two-word name inside its own ("a glass trophy case" for the prop "trophy case and
    # velvet stand"); single words are not enough ("mirror" names the room's mirror as well as a compact mirror)
    keys = set()
    for n in names:
        ws = re.findall(r"[a-z]+", n)
        for i in range(len(ws) - 1):
            if ws[i] not in ("and", "of", "with", "the", "a") and ws[i + 1] not in ("and", "of", "with", "the", "a"):
                keys.add(ws[i] + " " + ws[i + 1])        # its two-word names: "trophy case", "chrome toaster"

    def has_object(c):
        low = re.sub(r"[^a-z ]+", " ", c.lower())
        return (any(re.search(r"\b%s\b" % re.escape(w), low) for w in OBJECT_WORDS) or any(n in c.lower() for n in names)
                or any(re.search(r"\b%s\b" % re.escape(k), low) for k in keys))

    out = []
    for clause in re.split(r"\s*[;,]\s*", str(description or "").strip().rstrip(".")):
        if not clause:
            continue
        if not has_object(clause):
            out.append(clause)
            continue
        head = re.split(r"\b(?:with|holding|carrying|lined with|full of|covered in|topped with|and)\b", clause, 1)[0].strip()
        if head and not has_object(head):          # the room's own fixture stays; a surface is said bare
            surface = any(re.search(r"\b%s\b" % w, head.lower()) for w in SURFACE_WORDS)
            out.append(head + (", bare and clear" if surface else ""))
    return (", ".join(out) + ".") if out else ""


def new_location(brand: str, row: dict, sid, run: str, dry_run: bool = False, ws: Path | None = None,
                 look: dict | None = None) -> dict:
    """A location the bank does not have yet, made once in the ad's style: one set, empty, from the room the swipe
    shows (its layout) with the ad's look. The kept print becomes the set's picture, the one reference for every shot."""
    sid = canonical(sid)
    lid = _slug(row["id"])
    home = element_home(brand, "set", lid, ws)
    out = {"kind": "set", "id": lid, "name": row["id"], "style": sid, "home": str(home)}
    frame = role_frame(run, row["id"], row.get("real_reference"))
    look = look_reference(sid, run, look)
    name = f"set-{lid}-{sid or PHOTOREAL}"
    doc = writing_doc(run) if run else {}
    objects = [p.get("name") or p.get("id") for p in (doc.get("props") or []) if isinstance(p, dict)]
    locks = doc.get("product_lock") or []
    for lk in (locks if isinstance(locks, list) else [locks]):
        if isinstance(lk, dict):
            objects += [str(lk.get(k) or "") for k in ("name", "product", "id")]
        elif lk:                                 # a placement sentence: only the product's quoted name is an object
            objects += re.findall(r'"([^"]{3,80})"', str(lk))
    what = (f"{row['id'].lower()}, empty: {room_words(row.get('description', ''), objects)} "
            f"Light: {row.get('light', 'as the reference')}."
            " The room only: no people, no hands, no products, bottles or brand names; every surface bare and every case or"
            " shelf meant for the product empty (the product goes in at the shot); a plain block in the blockout is the"
            " furniture the words name, never a box" + (f" — in the {sid} style" if sid else ""))
    if dry_run:
        return dict(out, state="make", would="print the set once, file it as the location's picture", what=what)
    set_gate, set_queue = _set_queue()
    kept = set_gate.kept_print(brand, name)
    if kept is None:
        f = set_queue.file(brand, what, name=name, scene=what, source="style_chain", style=sid, style_formula=formula(sid),
                           identity_reference=(frame or {}).get("file"), look_reference=(look or {}).get("file"),
                           element={"kind": "set", "id": lid, "new": True},
                           resume={"tool": "style_chain", "brand": brand, "kind": "set", "id": lid, "style": sid})
        return dict(out, state="queued", request=str(f))
    home.mkdir(parents=True, exist_ok=True)
    shutil.copy2(kept, home / VARIANT_PICTURE)
    (home / "element.json").write_text(json.dumps({"id": lid, "kind": "set", "style_id": sid, "what": what,
                                                   "from": (frame or {}).get("file"), "look": look, "print": name},
                                                  indent=1, ensure_ascii=False) + "\n")
    return resolve(brand, "set", lid, sid, ws)


def ensure(production: str, dry_run: bool = False, briefs: Path | None = None, ws: Path | None = None) -> dict:
    """Every element the production needs, in its style: reused, or made (variants of banked ones; new people cast
    straight in the style). Re-run after each 3D print; nothing is made twice."""
    n = needs(production, briefs, ws)
    b = _read(brief_path(production, briefs))
    run = b.get("brief")
    rows = {c["name"]: c for c in writing_cast(run)}
    places = {w["id"]: w for w in writing_world(run)}
    lk = ad_look(production, briefs, pin=not dry_run)         # one look for the whole ad, pinned in its brief
    done = []
    for e in n["elements"]:
        if e.get("state") == "make":
            done.append(ensure_one(n["brand"], e["kind"], e["id"], n["style"]["id"], run=run, look=lk, dry_run=dry_run, ws=ws))
        elif e.get("state") == "no-master" and e.get("kind") == "person" and e.get("name") in rows:
            done.append(new_person(n["brand"], rows[e["name"]], n["style"]["id"], run, dry_run, ws, look=lk))
        elif e.get("state") == "no-master" and e.get("kind") == "set" and e.get("name") in places:
            done.append(new_location(n["brand"], places[e["name"]], n["style"]["id"], run, dry_run, ws, look=lk))
        else:
            done.append(e)
    return dict(n, elements=done)


# ── one scene: everything its start picture is made from ────────────────────────────────────────────────────────

def writing_doc(run: str, writing: Path | None = None) -> dict:
    f = Path(writing or _writing_runs()) / str(run) / "stages" / "5-brief.md"
    try:
        return json.loads(re.findall(r"```json\s*\n(.*?)\n```", f.read_text(), re.S)[-1])
    except (OSError, ValueError, IndexError):
        return {}


def writing_scene(run: str, scene_id: str, writing: Path | None = None) -> dict:
    return next((x for x in writing_doc(run, writing).get("scenes") or [] if x.get("id") == scene_id), {})


def scene_product(doc: dict, scene_id: str) -> str | None:
    """Where the product sits in this scene, as the brief's product lock says it ("S1: S1.1, cap down in the wall
    collar, front label to the wall · …"), or None when the scene shows no product."""
    for line in doc.get("product_lock") or []:
        head, _, rest = str(line).partition(":")
        if head.strip() == scene_id:
            where = rest.split("·")[0].strip()
            return re.sub(r"^%s\.\d+,\s*" % re.escape(scene_id), "", where) or "as the shot shows it"
    return None


def _words(t) -> set:
    return {w for w in re.findall(r"[a-z]+", str(t or "").lower()) if len(w) > 2}


def look_sheet(person_dir: Path, scene_id: str = "", wanted: str = "") -> str:
    """The look sheet a scene's person wears: the look whose record names the scene, else the look whose outfit shares
    the most words with the scene's look line, else the headshot. Relative to the person's folder."""
    looks = (_read(person_dir / "looks.json").get("looks") or {})
    sid_re = re.compile(r"\b%s\b" % re.escape(scene_id)) if scene_id else None

    def names_scene(v):
        src = str(v.get("from") or "")
        if sid_re and sid_re.search(src):
            return True
        n = int(scene_id[1:]) if scene_id[1:].isdigit() else None   # "S8-S11" ranges
        return n is not None and any(int(a) <= n <= int(b) for a, b in re.findall(r"S(\d+)-S(\d+)", src))
    hit = next((k for k in looks if k in str(wanted or "")), None)          # the scene names the look by its id
    hit = hit or next((k for k, v in looks.items() if names_scene(v)), None)
    if not hit and wanted:
        scored = sorted(((len(_words(v.get("outfit")) & _words(wanted)), k) for k, v in looks.items()), reverse=True)
        hit = scored[0][1] if scored and scored[0][0] >= 2 else None
    if not hit and len(looks) == 1:                                          # a person with one look wears it
        hit = next(iter(looks))
    sheet = (looks.get(hit) or {}).get("sheet") if hit else None
    if sheet and (person_dir / sheet).is_file():
        return sheet
    return "sheets/headshot.jpg"


def scene_refs(production: str, scene_id: str, briefs: Path | None = None, writing: Path | None = None) -> dict:
    """What a scene's start picture is made from, all in the ad's style and all the same every time: the scene's
    location set (its kept 3D print first, which the picture gate requires), each person's variant sheet for the look
    the scene names, the ad's one look picture, and the style's words. Never an element in another style."""
    b = _read(brief_path(production, briefs))
    st = ad_style(production, briefs=briefs, writing=writing)
    run = b.get("brief")
    brand = (b.get("shot_fill") or {}).get("brand") or _read(Path(writing or _writing_runs()) / str(run) / "run.json").get("brand")
    sc = writing_scene(run, scene_id, writing)
    take = _read(brief_path(production, briefs).parent / "scenes" / scene_id / "take.json")
    out = {"production": production, "scene": scene_id, "style": st["id"], "formula": formula(st["id"]),
           "look": ad_look(production, briefs, pin=False), "set": None, "set_print": None, "people": [], "missing": []}
    loc = take.get("set") or sc.get("setting_id")
    if loc:
        lid = _slug(loc)
        home = element_home(brand, "set", lid)
        el = _read(home / "element.json")
        pr = None
        if el.get("print"):
            try:
                set_gate, _ = _set_queue()
                pr = set_gate.kept_print(brand, el["print"])
            except Exception:                                  # noqa: BLE001  no image-production here: the copy is used
                pr = None
        rs = resolve(brand, "set", lid, st["id"])
        ok = rs["state"] in ("master", "have")
        if rs["state"] == "have":                 # a variant of a set banked in another style: its own kept print
            pr = None
            try:
                set_gate, _ = _set_queue()
                pr = set_gate.kept_print(brand, f"set-{lid}-{st['id']}")
            except Exception:                                  # noqa: BLE001
                pr = None
        out["set"] = {"id": lid, "name": loc, "picture": rs.get("picture") if ok else None,
                      "print": str(pr) if (pr and ok) else None}
        out["set_print"] = out["set"]["print"] or out["set"]["picture"]
        if not ok:
            out["missing"].append(f"location {loc}: no set in {st['id']} yet (style_chain.py ensure --production {production})")
    doc = writing_doc(run, writing)
    where = scene_product(doc, scene_id)
    out["product"] = None
    if where:
        kit = b.get("products", [None])[0] if b.get("products") else _read(
            Path(writing or _writing_runs()) / str(run) / "run.json").get("product")
        rp = resolve(brand, "product", kit, st["id"]) if kit else {"state": "no-master"}
        if rp["state"] in ("master", "have"):
            out["product"] = {"id": kit, "picture": rp["picture"], "where": where}
        else:
            out["missing"].append(f"product {kit or '(none named)'}: not in {st['id']} yet (style_chain.py ensure --production {production})")
    first = (sc.get("shots") or [{}])[0]                   # the scene's first moment, as the brief writes it
    out["moment"] = "; ".join(x for x in (", ".join(first.get("gestures") or []),
                                          ("face: " + first["face"]) if first.get("face") else "") if x) or None
    named = {str(p).upper() for p in sc.get("props") or []}
    out["props"] = [f"{p['name'].lower()}: {p.get('look', '')}, {p.get('size', '')}".strip(", ")
                    for p in doc.get("props") or [] if str(p.get("name", "")).upper() in named]
    ids = cast_ids(production, brand, briefs)
    rows = {c["name"]: c for c in writing_cast(run, writing)}
    looks_said = sc.get("looks") or {}
    for name, c in (take.get("cast") or {}).items():
        el = (c or {}).get("element") if isinstance(c, dict) else None
        base = (el or "").split("/styles/")[0] or ids.get(name) or (rows.get(name) or {}).get("bank_id")
        if not base or str(base).upper() == "NEW":
            base = _slug(name).split("-")[-1]
        r = resolve(brand, "person", base, st["id"])
        if r["state"] not in ("master", "have"):
            out["missing"].append(f"{name}: {base} in {st['id']} is {r['state']} (style_chain.py ensure --production {production})")
            continue
        d = Path(r["dir"])
        sheet = (c or {}).get("element_file") if isinstance(c, dict) else None
        said = looks_said.get(name) or next((v for k, v in looks_said.items()
                                             if _slug(k).split("-")[-1] == _slug(name).split("-")[-1]), "")
        sheet = sheet or look_sheet(d, scene_id, said or (c or {}).get("look", ""))
        out["people"].append({"name": name, "element": element_ref(base, st["id"], element_home(brand, "person", base)),
                              "file": sheet, "path": str(d / sheet)})
    return out


# ── footage ──────────────────────────────────────────────────────────────────────────────────────────────────────────

def footage_allowed(sid) -> bool:
    """Real footage only goes into a photoreal ad: in any other style it would break the look in the cut."""
    return is_photoreal(sid)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("styles")
    s = sub.add_parser("style"); s.add_argument("--production"); s.add_argument("--run")
    ss = sub.add_parser("set-style"); ss.add_argument("--production", required=True); ss.add_argument("style")
    ss.add_argument("--why", default="")
    r = sub.add_parser("resolve"); r.add_argument("brand"); r.add_argument("kind"); r.add_argument("id"); r.add_argument("style")
    n = sub.add_parser("needs"); n.add_argument("--production", required=True)
    e = sub.add_parser("ensure"); e.add_argument("--production", required=True); e.add_argument("--dry-run", action="store_true")
    o = sub.add_parser("ensure-one"); o.add_argument("brand"); o.add_argument("kind"); o.add_argument("id")
    o.add_argument("style"); o.add_argument("--run"); o.add_argument("--look"); o.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "styles":
        for x in rows():
            print(f"{x['id']:<24} {x.get('family', ''):<10} {x.get('status', '')}")
        return 0
    if a.cmd == "style":
        out = ad_style(a.production, a.run)
    elif a.cmd == "set-style":
        out = set_ad_style(a.production, a.style, a.why)
        out = {"style": out, "needs": needs(a.production)}
    elif a.cmd == "resolve":
        out = resolve(a.brand, a.kind, a.id, a.style)
    elif a.cmd == "needs":
        out = needs(a.production)
    elif a.cmd == "ensure":
        out = ensure(a.production, a.dry_run)
    else:
        out = ensure_one(a.brand, a.kind, a.id, a.style, a.run, a.look, a.dry_run)
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
