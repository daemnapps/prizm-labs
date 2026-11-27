"""THE AUTOMATIC ELEMENTS STEP — production on Auto (Outlier Settings,
automation.production == "auto"): a written AI brief goes to production with
no person between the elements check and the voice.

    python3 auto_elements.py <brief.md> --brand B --run <production run dir> [--dry-run]

run_v2.py start calls `run()` before run.py's manifest and elements gates.
For every element the elements sheet (elements_check.sheet) still lists TO MAKE:

  0. CAST (people, 2026-11-18) — the casting door is asked first: who already plays this role in the brand's bank
     (components/casting `bank.who_plays`, with the role in the brief's own words). When the bank's own record covers
     the role and that person's sheet is ready, they are bound: a role the bank covers never gets a new face. When it
     does not, the door's answer is kept on the run's trail and steps 1 and 2 run as before.
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
flock'd, decide.py's shape) for owner to agree with or overrule on Outlier → Calls.
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


# ------------------------------------------------------------- the casting door (2026-11-18)
# Production used to decide who plays a NEW person by itself (a same-swipe match, else a new face from the swipe's
# frames) and never asked the bank. The casting component owns that question; production asks it and acts on the answer.

def _casting():
    """components/casting, its package (`casting.bank.who_plays` is its public question)."""
    home = str(WS / "components" / "casting")
    if home not in sys.path:
        sys.path.append(home)
    import casting
    return casting


def role_words(row: dict) -> str:
    """The role a brief's cast row asks the bank for, in the brief's own words: its `role` when the brief gives one,
    else the row's name and the first clause of what it says the person is. Nothing is added to what the brief says."""
    if str(row.get("role") or "").strip():
        return str(row["role"]).strip()
    first = re.split(r"[.;:\n]", str(row.get("identity_block") or ""), 1)[0]
    return " ".join(x for x in [str(row.get("name") or row.get("id") or "").strip(), first.strip()] if x)


def ask_casting(brand: str, row: dict, who_plays=None) -> dict:
    """The casting door's answer for one cast row: {"asked", "covered", "person", "why", "gap", "problem"}. `who_plays`
    is the seam a test fakes. A door that cannot answer (no cast bank for the brand, a record that will not read) is
    said in `problem`; it never stops the elements step."""
    asked = role_words(row)
    try:
        ans = (who_plays or _casting().bank.who_plays)(brand, asked, WS)
    except BaseException as e:  # noqa: BLE001 — SystemExit included: the door refuses a brand with no bank
        return {"asked": asked, "covered": False, "person": None, "why": "", "gap": None,
                "problem": f"the casting door could not answer ({type(e).__name__}: {str(e)[:200]})"}
    return {"asked": asked, "covered": bool(ans.get("covered")), "person": ans.get("person"),
            "why": ans.get("why") or "", "gap": ans.get("gap"), "problem": "; ".join(ans.get("problems") or [])[:300]}


def cast_from(door: dict, brand: str) -> tuple[str | None, str]:
    """(bank id to bind, why) from the door's answer; (None, why not) when production carries on to steps 1 and 2.
    A covered role is bound only when that person's folder meets the production standard today; a covered role whose
    person is not ready is flagged and the run carries on (execute and flag, never a new stop)."""
    if door.get("problem") and not door.get("covered"):
        return None, door["problem"]
    if not door.get("covered"):
        near = "; ".join((door.get("gap") or {}).get("near") or [])[:240]
        return None, ("the casting door: nobody in the bank is recorded as playing this role (asked: "
                      f"\"{door['asked'][:120]}\")" + (f"; nearest: {near}" if near else ""))
    pid = str((door.get("person") or {}).get("id") or "")
    folder = EP.casting_home(brand, pid, WS) if pid else None
    if not pid or folder is None or not folder.is_dir() or not _complete(folder, "person"):
        short = "; ".join(EC._check_folder(folder, EC.standard()["person"]["requires"])[:3]) if folder and folder.is_dir() \
            else "no sheet in the casting folder"
        return None, (f"the casting door covers this role with `{pid}`, but their sheet is not ready for production "
                      f"({short}): finish it so the next run casts them; this run carries on as before")
    return pid, f"the casting door: {door.get('why') or 'the bank already has someone for this role'}"


# ------------------------------------------------------------- cast by audience (HELD FOR REVIEW, 2026-11-18)
# Written and not live: machine/held.json `cast-by-audience` is off, so run() never comes here. The wording it puts
# into the casting question: cast someone who looks like the audience, paired with a figure of authority; when the
# words name a kind of person, show that kind. Live today: every person is asked for in the brief's own words.

def lead_of(items: list, doc: dict) -> str | None:
    """The cast row that carries the ad: whoever is in the opening scene, else whoever is in the most scenes."""
    people = [i for i in items if i.get("kind") == "person"]
    if not people:
        return None
    opener = next((s.get("id") for s in doc.get("scenes") or [] if s.get("opens")), None)
    in_opening = [i for i in people if opener and opener in (i.get("scenes") or [])]
    pool = in_opening or people
    return max(pool, key=lambda i: len(i.get("scenes") or []))["id"]


def audience_cast(brand: str, doc: dict, for_avatar=None) -> dict:
    """Who the bank holds for the avatar the piece is written for, as a door-shaped answer for the LEAD:
    {"asked", "covered", "person", "why", "gap", "problem", "authority"}. The lead is the first of the avatar's
    roster (the people with the problem: who looks like the audience); `authority` names the figures of authority the
    bank holds for the same avatar, so the pairing is on the record. `for_avatar` is the seam a test fakes."""
    avatar = str((doc.get("piece") or {}).get("avatar") or "").strip()
    asked = f"someone who looks like the audience: the {avatar} avatar" if avatar else "someone who looks like the audience"
    if not avatar:
        return {"asked": asked, "covered": False, "person": None, "why": "", "gap": {"near": []}, "authority": [],
                "problem": "the brief names no avatar, so nothing says who the audience is"}
    try:
        ans = (for_avatar or _casting().bank.for_avatar)(brand, avatar, WS)
    except BaseException as e:  # noqa: BLE001
        return {"asked": asked, "covered": False, "person": None, "why": "", "gap": {"near": []}, "authority": [],
                "problem": f"the casting door could not answer ({type(e).__name__}: {str(e)[:200]})"}
    roster, auth = ans.get("roster") or [], ans.get("authority") or []
    names = [str(p.get("id")) for p in auth if p.get("id")]
    if not roster:
        return {"asked": asked, "covered": False, "person": None, "why": "", "authority": names, "problem": "",
                "gap": {"near": [ans.get("why") or f"nobody in the bank serves the {avatar} avatar"]}}
    lead = roster[0]
    why = (f"{lead.get('name') or lead.get('id')} is one of {len(roster)} people the bank holds for the {avatar} avatar: "
           "someone who looks like the audience" + (f"; figures of authority on file for the same avatar: {', '.join(names)}"
                                                    if names else "; the bank holds no figure of authority for this avatar yet"))
    return {"asked": asked, "covered": True, "person": lead, "why": why, "gap": None, "problem": "", "authority": names}


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


LOOK_MATCH = 0.5      # word overlap at which a banked outfit IS the brief's new look; below it the look is made


def _shown(folder: Path) -> str:
    for rec in ("spec.json", "provenance.json"):
        try:
            v = json.loads((folder / rec).read_text()).get("shown")
        except (OSError, ValueError):
            v = None
        if v:
            return v
    return ""


def _look_id(words: str, n: int) -> str:
    stop = {"a", "an", "the", "and", "with", "on", "of", "in", "over", "under", "his", "her", "their", "its", "to"}
    w = [x for x in re.findall(r"[a-z]+", words.lower()) if x not in stop and len(x) > 1][:3]
    return f"look-{n}-" + ("-".join(w) or "outfit")


def looks_for(folder: Path, needs: list, run_name: str, dry: bool, build=None) -> dict:
    """{the brief's NEW look: banked look id} for every new outfit a banked person wears. A non-human character has one
    look, its master picture, and wears it in every scene. A banked outfit whose words match closely (LOOK_MATCH) is
    that look. Any other is added to the person's spec and made through make_character, which keeps every sheet already
    made and draws only the new look sheets, each from the person's filed 3D set print (GATE-4; a set it does not have
    yet is queued for the 3d-print skill and the step stops, to resume next run). A look that cannot be made yet is left
    out, so the elements check keeps it on the to-make list."""
    try:
        looks = json.loads((folder / "looks.json").read_text()).get("looks") or {}
    except (OSError, ValueError):
        looks = {}
    if _shown(folder) == "character" and len(looks) == 1:
        one = next(iter(looks))
        return {lk: one for lk in needs}
    out, make = {}, []
    for lk in needs:
        lid, score = best_look(folder, lk)
        if lid and score >= LOOK_MATCH:
            out[lk] = lid
        else:
            make.append(lk)
    sp = folder / "spec.json"
    if not make or not sp.is_file():
        return out
    spec = json.loads(sp.read_text())
    have = spec.setdefault("looks", {})
    new = {}
    for lk in make:
        words = lk.split(":", 1)[-1].strip()
        lid = next((k for k, v in have.items() if str(v.get("outfit", "")).strip() == words), None)
        if not lid:
            lid = _look_id(words, len(have) + 1)
            have[lid] = {"outfit": words, "from": f"the brief's scenes (production run {run_name})",
                         "continuity": "every accessory stays on in every scene the look is worn"}
        new[lk] = lid
    if dry:
        print(f"  [dry run] would make look(s) {', '.join(new.values())} for {folder.name}")
        return out
    sp.write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    (build or _mod(HERE / "make_character.py", "vm_ae_make_character").build)(sp, out=folder)
    made = json.loads((folder / "looks.json").read_text()).get("looks") or {}
    out.update({lk: lid for lk, lid in new.items() if lid in made})
    return out


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


PRODUCT_WORDS = re.compile(r"\b(tube|bottle|jar|packshot|product|serum|lotion|skincare box|pump|scrub tube|cream tube|scrub)\b", re.I)
TONES = ("deep-brown", "medium-brown", "light-tan", "olive", "deep", "fair", "light")


def pick_skin(words: str):
    """The texture bank's closest skin row for a person: tone named in the words, then the age range holding the
    age named, then sex words. None when the bank is empty (make_character then names the gap)."""
    try:
        bank = json.loads((WS / "runs" / "ai-elements" / "_texture-refs" / "index.json").read_text()).get("skin") or []
    except (OSError, ValueError):
        return None
    if not bank:
        return None
    w = (words or "").lower()
    tone = next((t for t in TONES if t.replace("-", " ") in w or t in w), "")
    age = re.search(r"\b(\d{1,2})\b", w)
    age = int(age.group(1)) if age else None
    female = bool(re.search(r"\b(woman|her|she|female|grandmother|mother|girl)\b", w))

    def score(r):
        lo, hi = (list(map(int, re.findall(r"\d+", r.get("age") or "0-0")[:2])) + [0, 0])[:2]
        f = r.get("file", "")
        gap = 0 if age is None or lo <= age <= hi else min(abs(age - lo), abs(age - hi))
        return ((2 if tone and r.get("tone") == tone else 0) + (1 if ("female" in f) == female else 0)
                - (gap / 10 if age is not None else 0))
    best = max(bank, key=score)
    return {"file": best["file"], "shows": ", ".join(best.get("marks") or []) + f" ({best.get('tone')}, {best.get('age')})"}



def pick_hair(words: str):
    """The texture bank's hair row for a person: silver/grey for 55+ or grey words, else the colour and length named."""
    try:
        bank = [r for r in json.loads((WS / "runs" / "ai-elements" / "_texture-refs" / "index.json").read_text()).get("hair") or []
                if r.get("kind") != "beard"]
    except (OSError, ValueError):
        return None
    if not bank:
        return None
    w = (words or "").lower()
    age = re.search(r"\b(\d{1,2})\b", w)
    old = bool(re.search(r"\b(grey|gray|silver|white-haired)\b", w)) or (age is not None and int(age.group(1)) >= 55)

    def score(r):
        f = r.get("file", "")
        return (3 if old and "silver" in f else 0) + sum(1 for x in re.findall(r"[a-z]+", f) if x in w)
    best = max(bank, key=score)
    hw = re.search(r"([a-z -]{0,30}\b(?:hair|beard|stubble)\b)", w)
    on = hw.group(1).strip() if hw else ("short silver-white hair" if old else "her own hair")
    return {"file": best["file"], "shows": f"{best.get('color') or 'silver-white'} hair, {best.get('length') or ''}".strip(", "),
            "on": on}


def swipe_frames(src: Path, said: str, dest: Path, most: int = 3) -> list:
    import subprocess
    """Real video frames of the swipe at the times named in `said` (m:ss), else at 0.5 s, 1.5 s, 2.5 s."""
    dest.mkdir(parents=True, exist_ok=True)
    times = [int(m) * 60 + float(s) for m, s in re.findall(r"\b(\d{1,2}):(\d{2}(?:\.\d+)?)\b", said or "")][:most]
    if not times:
        times = [0.5, 1.5, 2.5]
    elif len(times) < most:
        times = sorted({t + d for t in times for d in (0.5, 1.5, 2.5)})[:most]
    out = []
    for t in times:
        f = dest / f"swipe-{t:05.1f}s.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1", "-q:v", "2", str(f)],
                       capture_output=True)
        if f.is_file() and f.stat().st_size > 1000:
            out.append({"file": f"reference/{f.name}", "kind": "real video frame", "from": f"{src} at {t:.1f} s"})
    return out


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
    # SMALL MISSES FIXED HERE, NOT STOPPED ON (2026-11-20): the identity block's script notes ("lotion glossed over
    # its flakes in S5") are not the person — a sentence that names a product goes to loadbearing, so the cast sheet
    # never refuses on a product word; and the de-slop skin photo is picked from the texture bank by tone and age.
    who_all = row.get("identity_block") or row.get("name") or ""
    sentences = re.split(r"(?<=[.;])\s+", who_all)
    sold = [x for x in sentences if PRODUCT_WORDS.search(x)]
    who = " ".join(x for x in sentences if not PRODUCT_WORDS.search(x)) or who_all
    spec = {"id": pid, "brand": brand,
            "who": who,
            "adjustments": row.get("adjustments") or ["a different face from the swipe's person: different nose, brow and jaw line",
                                                      "same age band, build, skin tone and manner"],
            "base": "plain crew-neck tee and plain trousers, no hat, no glasses, no jewellery",
            "details": "the hands and nails, the skin at the jaw and cheeks, the ears, any rings",
            "looks": looks,
            "character": {"title": (row.get("name") or pid).title(), "why": (row.get("identity_block") or "")[:160],
                          "role": "on-camera talent" if item.get("scenes") else "voice only",
                          "age": (re.search(r"\b(\d{2}) to (\d{2})\b", row.get("identity_block") or "") or [""])[0],
                          "lane": "paid", "loadbearing": sold, "movement": "as the swipe's person moves",
                          "voice": vpersona},
            "made_by": BY, "runs": [td.name]}
    skin, hair = pick_skin(who_all), pick_hair(who_all)
    if skin:
        spec["texture"] = {"skin": skin, **({"hair": hair} if hair else {})}
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
    # NO FRAME MAP, STILL REAL (2026-11-20): with no frame map the sheet attaches no swipe frames and the person was
    # refused for "no real reference". The swipe's own frames at the times the brief's real_reference names (else its
    # first seconds) are taken straight from source.mp4 — real video frames, recorded with where they came from.
    if not spec.get("real_references") and (td / "source.mp4").is_file():
        spec["real_references"] = swipe_frames(td / "source.mp4", row.get("real_reference") or "", out / "reference")
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
    # EVERY PICTURE FROM A 3D PRINT (GATE-4, 2026-11-10): the picture model refuses a prop whose first picture is not
    # a filed 3D set's kept print, so a prop with no print is QUEUED for the 3D print (in the ad's style when it has
    # one) and made on the next run, starting from that print — never left "could not be made" for ever (20 Nov 2026:
    # fourteen props of an animated ad failed this way on every run and no print was ever asked for).
    SC = _mod(WS / "components" / "video-production" / "styles" / "style_chain.py", "vm_ae_style_chain")
    sid = SC.canonical(((json.loads((td / "run.json").read_text()) if td and (td / "run.json").is_file() else {})
                        .get("style_id")))
    set_gate, set_queue = SC._set_queue()
    req = f"prop-{item['bank_id']}-{sid or 'photoreal'}"
    kp = set_gate.kept_print(brand, req)
    if kp is None:
        if dry:
            return "would queue its 3D print", req
        look = SC.look_reference(sid, td.name if td else None) if sid else None
        set_queue.file(brand, f"{d.get('name') or item['id']}, a prop at its true size ({d.get('size') or 'as the brief says'}) "
                              f"standing alone on a plain surface" + (f" — in the {sid} style" if sid else ""),
                       name=req, scene=f"{d.get('name') or item['id']}: {str(d['look']).rstrip('.')}. The object only: "
                       "no people, no hands, no products, no lettering.",
                       resume={"tool": "auto_elements", "brand": brand, "kind": "prop", "id": item["bank_id"],
                               "command": "the production's own run again (ai_lane.py <run> --yes): the prop is made from its kept print"},
                       source="auto_elements", style=sid, style_formula=SC.formula(sid) if sid else None,
                       look_reference=(look or {}).get("file"), identity_reference=str(refs[0][1]),
                       element={"kind": "prop", "id": item["bank_id"], "new": True}, people_in_it=False)
        return "", f"queued for the 3D print ({req}): the 3d-print skill prints it, then the next run makes the prop from it"
    refs = [("print", Path(kp), f"its kept 3D set print ({req})")] + refs
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
    import functools                     # a prop has no person in it (GATE-4, 2026-11-10)
    gen = generate or functools.partial(_mod(HERE / "direct_openai.py", "vm_ae_direct_openai").generate, people=False)
    out = dst / "picture.png"
    remade = None
    if sid and not SC.is_photoreal(sid):
        # A PROP IN THE AD'S STYLE IS ITS KEPT PRINT (style_chain: products, sets, worlds and props, the kept print is
        # the picture). The 3d-print skill already looked at it; a second picture model pass only redraws it, costs a
        # picture every run and is held by the review for drifting from the print (20 Nov 2026)
        shutil.copy2(kp, out)
        res, probs = {"model": "kept 3D print", "door": "3d-print"}, []
    else:
        res = gen(prompt, [f for _w, f, _s in kept], out)
        rv = review or _prop_review
        probs = rv(dst, d, out, [f for _w, f, _s in kept])
    if probs:
        fixes = "; ".join(str(p.get("fix") or p.get("what") or "") for p in probs)
        edit = (f"Edit this picture. Change ONLY these things and keep everything else exactly as it is: {fixes}. "
                "Nothing else in the picture: no person, no hands, no product, no words.")
        (dst / "versions").mkdir(exist_ok=True)
        shutil.copy2(out, dst / "versions" / "picture-v1.png")
        # the picture alone: a second picture pulled the edit away from it. It is an edit of a picture made from the
        # kept print, so the door is told that print (`from_print`, GATE-4) — else every remake is refused (20 Nov 2026)
        regen = gen if generate else functools.partial(gen, from_print=str(kp))
        res = regen(edit, [out], out)
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
                                    else "its kept 3D set print (GATE-4)" if w == "print"
                                    else "the matching prop already banked for this ad"),
                           "from": src, "use": ("the room, counter and light the prop stands in" if w == "set"
                                                else "its true size, shape and light, in the ad's style" if w == "print"
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

def held_on(name: str) -> bool:
    """Is a change held for review switched on (machine/held.json)? Off when the file cannot be read."""
    try:
        return _mod(HERE / "held.py", "vm_ae_held").on(name)
    except Exception:  # noqa: BLE001
        return False


def styled_bank(brand: str, kind: str, bank_id: str, doc: dict):
    """The bank id of a person or set the style chain banked in the ad's own (non-photoreal) style under this id, or
    None: such an element is bound as it is, never cast or made again."""
    sid = EC.ad_style(doc)
    if not sid or not bank_id:
        return None
    try:
        r = EC._style_chain().resolve(brand, kind, bank_id, sid, WS)
    except (Exception, SystemExit):  # noqa: BLE001
        return None
    return bank_id if r.get("state") in ("master", "have") else None


def _note(run_dir: Path, decision: str, choice: str, why: str, by: str, dry: bool) -> None:
    """One row on the production run's decision trail (machine/trail_door.py). Never stops the step."""
    try:
        _mod(HERE / "trail_door.py", "vm_ae_trail_door").note(run_dir, decision, choice, why, by=by, dry=dry)
    except Exception:  # noqa: BLE001
        pass


def run(brief: Path, brand: str, run_dir: Path, dry: bool = False, generate=None, review=None,
        manifest=None, confirm=None, who_plays=None) -> dict:
    """The whole automatic step, inside the chain (run_v2 start → here, on the batch runner and the mini door alike;
    VIDEO-RULINGS V25): every element still to make is bound or made — a person the cast bank already has for the
    role cast from it (the casting door, asked first), a prop the swipe never shows MADE from the brief's definition
    (P65) — then the manifest is re-checked and the sheet confirmed. `generate` / `review` / `manifest` / `confirm` /
    `who_plays` are the seams a test fakes; a real run passes none."""
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
                    got, why = None, ""
                    # BANKED IN THE AD'S STYLE (style_chain, 2026-11-20): a NEW row the style chain already cast or set
                    # in this ad's style (filed under the row's own id) is bound to it, never cast or made again
                    styled = styled_bank(brand, "person" if k == "person" else "set", it["bank_id"], doc)
                    if styled:
                        got, why = styled, "banked in the ad's style by the style chain"
                        bank_id = got
                        binds[it["id"]] = got
                        log(rname, brand, it, f"bound to `{got}`, banked in the ad's style", why, 0.9)
                    if k == "person" and not got:
                        # THE CASTING DOOR FIRST (2026-11-18): a role the bank covers never gets a new face. Its
                        # answer goes on the run's trail either way; only a person it casts is a call on the Calls page.
                        door = None
                        if held_on("cast-by-audience") and it["id"] == lead_of(sh["items"], doc):
                            door = audience_cast(brand, doc)      # HELD: off until the owner's review (machine/held.json)
                            if not door.get("covered"):
                                door = None                       # nobody for the avatar: the brief's own words, as live
                        got, why = cast_from(door or ask_casting(brand, row, who_plays=who_plays), brand)
                        _note(run_dir, f"who plays {it['id']}", f"`{got}` from the cast bank" if got else
                              "nobody banked for the role: matched or made from this swipe", why, "the casting door", dry)
                        if got:
                            bank_id = got
                            binds[it["id"]] = got
                            log(rname, brand, it, f"cast from the bank: `{got}`", why, 0.85)
                    if not got:
                        got, why = match_banked(brand, it, td)
                        if got:
                            bank_id = got
                            binds[it["id"]] = got
                            log(rname, brand, it, f"bound to banked {k} `{got}`", why, 0.8)
                    if k == "setting" and not got:
                        # A PLACE THE BRAND ALREADY HAS (2026-11-25): used before a new one is printed and paid for
                        got, why = _mod(HERE / "set_reuse.py", "vm_ae_set_reuse").banked_set(brand, row, EC.ad_style(doc), WS)
                        if got:
                            bank_id = got
                            binds[it["id"]] = got
                            log(rname, brand, it, f"bound to a place we already have: `{got}`", why, 0.75)
                    if not got and td:
                        bank_id = (make_person(brand, row, it, doc, td, sheet_p, dry) if k == "person"
                                   else make_set(brand, row, it, td, sheet_p, dry))
                        binds[it["id"]] = bank_id
                        made.append(f"{k} {bank_id}")
                        log(rname, brand, it, f"made new {k} `{bank_id}` from the swipe's frames",
                            "no banked element from this swipe; made from the frames its real reference names", 0.6)
                    elif not got:
                        log(rname, brand, it, "", "no swipe teardown found — nothing to make it from", 0.0)
                        continue
                folder = EP.casting_home(brand, bank_id, WS) if k == "person" else WS / it["folder"]
                if k == "person":
                    need = [lk for lk in it.get("looks") or [] if lk.upper().startswith("NEW")]
                    if need:
                        got_looks = looks_for(folder, need, rname, dry)
                        for lk, lid in got_looks.items():
                            binds[f"{it['id']}.look:{lk.split(':', 1)[-1].strip()}"] = lid
                            log(rname, brand, {**it, "kind": "look"}, f"look `{lid}` of {bank_id} for {lk}",
                                "its one look (a non-human character)" if _shown(folder) == "character" else
                                "the banked outfit for the brief's new look (matched closely, or made from the "
                                "person's master and 3D set print)", 0.7)
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
        MF = _mod(WS / "components" / "video-writing" / "machine" / "manifest.py", "vm_ae_manifest")
        # production never writes the manifest block into the brief: it changes the brief's hash and so un-accepts
        # the brief the writing station accepted (2026-11-20, as run.py's own re-check)
        ok, missing = MF.check(td, brand, brief.name, write=not DRY["on"], stamp_brief=False)
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
