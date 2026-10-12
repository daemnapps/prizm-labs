#!/usr/bin/env python3
"""clip_gate.py — the gate every clip passes BEFORE money is spent, and the count AFTER.

    python3 machine/clip_gate.py check    <run>                      # every planned clip, red or green
    python3 machine/clip_gate.py approve  <run> --by <who> [--only S5-F1,S10-F1]   # the pictures, as they are now
    python3 machine/clip_gate.py remake   <run> G08-C1-1,G16-C1-1    # really make these again
    python3 machine/clip_gate.py coverage <run>                      # every planned clip made, or the run is INCOMPLETE

the owner, 2026-10-09, after the Grandma TV-shopping clips: "we need to have real time refinement before
generations to production and references and such, we should not have missing clips … there needs to be
a clean and clear gate that things need to go through." Every check below is a thing that went wrong that
night, found only after the money was spent:

  PATHS      a reference the run points at is not on disk — the swipe's folder had moved and the live run
             crashed half-way (storyboard.json still named the old teardown folder).
  SENT       the words shown are not the words sent — a call carries `prompt` AND `params.prompt`, and only
             the second goes to the model; a fix written into the first never reached it.
  APPROVED   a picture changed (or was never looked at) since it was approved — the swipe's mascara lashes
             and "LIVE MASCARA DEMO" screen sat in two pictures that went to clips.
  SWIPE WORDS words read off our picture that belong to the swipe and nowhere in our brief or the brand's
             product files (MASCARA, LASHES …) — the swipe's product leaking into ours.
  SKIN       an after-the-routine scene whose prompt still describes the spots — the clip painted a dark
             patch back onto the cheek the scene exists to show clear.
  FACES      a person looks like someone else in one of their pictures — S19 was a different woman
             (fluffier, blonder bob, rounder face) and went to clips. The chain's ruling stands (THE-CHAIN.md,
             3 Oct: "the face lineup by eye is the real check"), so no new automatic face judge: the gate
             BUILDS each person's lineup (their cast master beside every picture they are in,
             clips/gate-lineups/<person>.jpg) and holds every clip of theirs until that exact lineup is
             approved (`approve` approves the pictures AND the lineups, as they are now).
  WORDS      text a viewer can read on our picture (or on a frame of the finished clip) that is not a real word,
             not our brief's and not the brand's — the picture model DRAWS the tube's label, and it came out
             "BAALUNCE FACE SCOUO", "BPILLIANCE FACE SCRUE" on most product shots (the owner, 9 Oct: "this can't be
             happening anymore, no slop at all"). Held: a near-miss of a brand or product name a phone shows
             plainly (NAME_TEXT_H), or big text that is not words (MIN_TEXT_H); smaller print is noted, not held
             ("some of this small language stuff might be garbled in a big video, i'm not too worried about it").
  REFUSED    the model refused this exact request before; the same request is not sent again — change the
             picture or the words first.

`check` writes clips/gate.json + clips/GATE.md and a fingerprint of the plan and every picture it checked.
`omni_clips.py run` refuses to spend unless the gate is green for that same fingerprint, and ends with
`coverage`: a planned clip that is not made (refused, failed) leaves the run INCOMPLETE, named — it never
reaches the editor as "done". `remake` moves the old clip aside so the next run really makes it (a clip
already on disk is otherwise kept and reported, never silently "done").

Brand-agnostic: every word list comes from the run's own brief, the brand's product files and the swipe's
own frame map. Nothing here spends or calls a model; the text reader is macOS Vision on this machine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    import importlib.util as u
    sp = u.spec_from_file_location(name, HERE / f"{name}.py")
    m = u.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _sha(p: Path) -> str:
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]
    except OSError:
        return ""


def _text_sha(t: str) -> str:
    return hashlib.sha256(str(t).encode()).hexdigest()[:16]


def _workspace() -> Path:
    for d in HERE.parents:
        if (d / "brands").is_dir() and (d / "components").is_dir():
            return d
    return HERE.parents[2]


# ------------------------------------------------------------ inputs

def plan_of(run: Path) -> dict:
    return _read(Path(run) / "clips" / "plan.json", {}) or {}


def teardown_of(run: Path) -> Path | None:
    sb = _read(Path(run) / "storyboard.json", {}) or {}
    return (HERE / sb["teardown"]).resolve() if sb.get("teardown") else None


def picture(run: Path, frame_id: str) -> Path | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = Path(run) / "media" / f"{frame_id}{ext}"
        if p.is_file():
            return p
    return None


WORD = re.compile(r"[A-Za-z][A-Za-z'’-]{3,}")


def _words(text: str) -> set:
    return {w.lower().strip("'’-") for w in WORD.findall(str(text))}


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)


def swipe_words(teardown: Path | None) -> set:
    """Every word the swipe's frame map records — what was on its screens, signs and labels."""
    if not teardown:
        return set()
    fm = _read(teardown / "framemap" / "framemap.json", {}) or {}
    return _words(" ".join(_strings(fm)))


NOT_THERE = re.compile(r"\bswipe|\bno\b|\bnever\b|\bnot\b|\bwithout\b|\binstead\b|\bbecomes?\b|\bremoved?\b", re.I)


def allowed_words(run: Path, brand: str | None) -> set:
    """Words our picture may carry: what our scenes SAY and SHOW (spoken lines, on-screen words, card and
    screen lines), the brand's product files, and the sheets of the set and props we built. Notes ABOUT the
    swipe (the plan's descriptions of what it showed) are not allowed words — that is how the swipe's
    product name hid in a run that only mentioned it."""
    run = Path(run)
    doc = _read(run / "plan.json", {}) or {}
    text = []
    for sc in doc.get("scenes") or []:
        for k in ("say", "voice", "on_screen", "lyrics"):
            if isinstance(sc.get(k), str):
                text.append(sc[k])
        for k in ("card", "screen", "endcard", "split"):
            if isinstance(sc.get(k), (dict, list)):
                text.append(" ".join(_strings(sc[k])))
    ws = _workspace()
    els = _read(run / "elements.json", {}) or {}
    for it in els.get("items") or []:
        if it.get("kind") in ("setting", "prop", "product") and it.get("folder"):
            d = ws / it["folder"]
            for f in list(d.glob("*.md"))[:20] if d.is_dir() else []:
                # only what the sheet says IS there — a line about the swipe or a ban ("the swipe's mascara
                # tubes become plain tubes") names exactly the words that must not appear
                text += [l for l in f.read_text(errors="ignore").splitlines() if not NOT_THERE.search(l)]
    if brand:
        prod = ws / "brands" / brand / "products"
        for p in list(prod.rglob("*.md"))[:400] if prod.is_dir() else []:
            text.append(p.read_text(errors="ignore"))
    return _words(" ".join(text))


# What a viewer actually notices (the owner, 9 Oct: "some of this small language stuff might be garbled in a big video,
# i'm not too worried about it … we need to eliminate as much slop as possible"): a NAME of ours misspelt at a size
# a phone shows plainly, or big garbled text. Smaller is noted for the record, never held.
NAME_TEXT_H = 0.010         # a misspelt brand / product name at least this tall (share of the frame height) is held
MIN_TEXT_H = 0.020          # other words that are not words are held from this size (signs, screens, headlines)
_DICT = None
SUFFIXES = ("s", "es", "er", "ers", "est", "ed", "d", "ing", "ly", "'s")


def dictionary() -> set:
    """The machine's own word list (macOS /usr/share/dict/words); empty where there is none — then only our
    own files count as words, which is stricter, never looser."""
    global _DICT
    if _DICT is None:
        try:
            _DICT = {w.strip().lower() for w in open("/usr/share/dict/words", errors="ignore")}
        except OSError:
            _DICT = set()
    return _DICT


_FRAG: dict = {}


def cut_off(w: str, allowed: set) -> bool:
    """A real word with its first or last letters cut off by the frame's edge ("EAUTY" of BEAUTY): the start or
    the end of a word of ours or of the dictionary, at most two letters missing."""
    if w in _FRAG:
        return _FRAG[w]
    hit = any(len(x) - len(w) in (1, 2) and (x.endswith(w) or x.startswith(w)) for x in allowed) or any(
        len(x) - len(w) in (1, 2) and (x.endswith(w) or x.startswith(w)) for x in dictionary() if len(x) <= len(w) + 2)
    _FRAG[w] = hit
    return hit


def known(w: str, allowed: set) -> bool:
    d = dictionary()
    if w in allowed or w in d:
        return True
    for suf in SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3 and (w[: -len(suf)] in d or w[: -len(suf)] in allowed):
            return True
    return w.endswith("ies") and (w[:-3] + "y") in d


def names_of(run: Path, brand: str | None) -> list[str]:
    """The names that must be spelled exactly: the brand, and every product the brand sells (product.md `name:`)."""
    out = [brand.replace("-", " ")] if brand else []
    prod = _workspace() / "brands" / (brand or "_") / "products"
    for f in sorted(prod.glob("*/product.md")) if prod.is_dir() else []:
        m = re.search(r"^name:\s*(.+)$", f.read_text(errors="ignore"), re.M)
        if m:
            out.append(m.group(1).strip())
    return [n.lower() for n in out if n]


def slop(lines, allowed: set, names: list[str]) -> tuple[list[str], list[str]]:
    """(held, noted) — every readable line checked for words that are not words and for near-miss names."""
    import difflib
    held, noted = [], []
    name_words = {w for n in names for w in _words(n)}
    for h, text in lines:
        t = " ".join(text.split())
        words = _words(t)
        bad = sorted({w for w in words if not known(w, allowed | name_words)})
        edge = [w for w in bad if len(words) <= 2 and cut_off(w, allowed | name_words)]   # a lone fragment at an edge
        bad = [w for w in bad if w not in edge]
        near = [n for n in names if t.lower() != n and difflib.SequenceMatcher(None, t.lower(), n).ratio() >= 0.72]
        # a garbled label: words that are not words on the same line as a word of our names ("BAALUNCE FACE SCOUO")
        if bad and (set(words) & name_words):
            near += [n for n in names if set(_words(n)) & set(words)]
        near += [w for w in bad for nw in name_words if difflib.SequenceMatcher(None, w, nw).ratio() >= 0.75]
        if near and h >= NAME_TEXT_H:
            held.append(f'"{t}" is a misspelt name ({", ".join(sorted(set(near)))})')
        elif near:
            noted.append(f'"{t}" (a name, misspelt small)')
        elif bad and h >= MIN_TEXT_H:
            held.append(f'"{t}" reads as {", ".join(bad)} — not words')
        elif bad:
            noted.append(f'"{t}" (too small to read on a phone)')
    return held, noted


def text_boxes(pic: Path) -> list[tuple]:
    """[(height as a share of the frame, text)] for every line macOS Vision reads."""
    global _READER
    words_on(pic)                                           # builds the reader once
    out = subprocess.run([str(_READER), str(pic), "--boxes"], capture_output=True, text=True).stdout
    rows = []
    for l in out.splitlines():
        parts = l.split("\t", 2)
        if len(parts) == 3:
            try:
                rows.append((float(parts[0]), parts[2].strip()))
            except ValueError:
                pass
    return rows


def _as_boxes(lines) -> list[tuple]:
    return [(1.0, x) if isinstance(x, str) else (float(x[0]), x[1]) for x in lines or []]


_READER = None


def words_on(pic: Path) -> list[str]:
    """Every line of text macOS Vision reads on the picture."""
    global _READER
    exe, src = HERE / "vision" / ".build" / "readtext", HERE / "vision" / "readtext.swift"
    if _READER is None:
        if not exe.exists() or exe.stat().st_mtime < src.stat().st_mtime:
            exe.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], check=True, capture_output=True)
        _READER = exe
    out = subprocess.run([str(_READER), str(pic)], capture_output=True, text=True).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


# ------------------------------------------------------------ the face lineup

def _persons(run: Path) -> dict:
    els = _read(Path(run) / "elements.json", {}) or {}
    ws = _workspace()
    out = {}
    for it in els.get("items") or []:
        if it.get("kind") == "person" and it.get("folder"):
            d = ws / it["folder"]
            m = next((d / n for n in ("master.jpg", "master.png", "master.webp") if (d / n).is_file()), None)
            out[it["id"]] = m
    return out


def _slug(pid: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", pid.lower()).strip("-")


def in_picture(run: Path, c: dict) -> list[str]:
    """The people actually IN this clip's picture — the scene's `who` names them; a voice over the
    shot (an off-camera speaker the call also carries) is not in it."""
    doc = _read(Path(run) / "plan.json", {}) or {}
    sc = next((x for x in doc.get("scenes") or [] if x.get("id") == str(c.get("start_frame") or "").split("-")[0]), {})
    who = str(sc.get("who") or "")
    people = list(c.get("people") or [])
    if not who:
        return people
    return [p for p in people if re.search(r"\b" + re.escape(p) + r"\b", who, re.I)]


def lineups(run: Path, calls: list[dict]) -> dict:
    """{person: (lineup image, [picture ids])} — the master first, then each picture they are in."""
    from PIL import Image, ImageDraw
    run = Path(run)
    masters = _persons(run)
    seen: dict = {}
    for c in calls:
        f = c.get("start_frame")
        if not f or str(f).endswith("-LAST") or picture(run, f) is None:
            continue
        for pid in in_picture(run, c):
            if f not in seen.setdefault(pid, []):
                seen[pid].append(f)
    out = {}
    d = run / "clips" / "gate-lineups"
    d.mkdir(parents=True, exist_ok=True)
    H = 420
    for pid, frames in seen.items():
        tiles = []
        for label, path in [("master", masters.get(pid))] + [(f, picture(run, f)) for f in frames]:
            if not path:
                continue
            im = Image.open(path).convert("RGB")
            im = im.resize((max(1, int(im.width * H / im.height)), H))
            canvas = Image.new("RGB", (im.width, H + 26), "white")
            canvas.paste(im, (0, 0))
            ImageDraw.Draw(canvas).text((6, H + 6), label, fill="black")
            tiles.append(canvas)
        if not tiles:
            continue
        W = sum(t.width for t in tiles) + 4 * (len(tiles) - 1)
        sheet = Image.new("RGB", (W, H + 26), "white")
        x = 0
        for t in tiles:
            sheet.paste(t, (x, 0))
            x += t.width + 4
        f = d / f"{_slug(pid)}.jpg"
        sheet.save(f, quality=80)
        out[pid] = (f, frames)
    return out


# ------------------------------------------------------------ the checks

def check(run: Path, only: list[str] | None = None, read_text=text_boxes) -> dict:
    run = Path(run)
    plan = plan_of(run)
    calls = [c for c in plan.get("calls") or [] if not only or c["id"] in only or c.get("section_id") in only]
    oc = _load("omni_clips")
    doc = _read(run / "plan.json", {}) or {}
    scenes = {s.get("id"): s for s in doc.get("scenes") or []}
    rj = _read(run / "run.json", {}) or {}
    brand = rj.get("brand") or doc.get("brand")
    td = teardown_of(run)
    approvals = _read(run / "clips" / "gate-approved.json", {}) or {}
    refusals = _read(run / "clips" / "gate-refusals.json", {}) or {}
    swipe = swipe_words(td)
    allowed = allowed_words(run, brand)
    names = names_of(run, brand)
    pics_read: dict = {}
    lineup_ok = {}
    for pid, (img, frames) in lineups(run, plan.get("calls") or []).items():
        a = approvals.get(f"lineup:{pid}") or {}
        sig = _text_sha(" ".join(f"{f}={_sha(picture(run, f) or '')}" for f in frames))
        lineup_ok[pid] = (None if a.get("sig") == sig else
                          f"FACES: {pid}'s face lineup ({img.relative_to(run)}) "
                          + ("changed since it was approved" if a else "has not been approved")
                          + " — look at it side by side, then clip_gate.py approve")
    rows = []
    for c in calls:
        red, notes = [], []
        # PATHS
        if not plan:
            red.append("PATHS: no clips/plan.json — run.py start … --clips first")
        frames = [f for f in (c.get("start_frame"), c.get("end_frame")) if f and not str(f).endswith("-LAST")]
        for f in frames:
            if picture(run, f) is None:
                red.append(f"PATHS: the picture {f} is not in media/")
        if c.get("refs"):
            if not td or not td.is_dir():
                red.append(f"PATHS: the swipe's folder {td} is not on this machine — storyboard.json `teardown` is stale")
            else:
                for r in c["refs"]:
                    src = td / "framemap" / "shots" / r["clip"]
                    if not src.is_file():
                        red.append(f"PATHS: the swipe clip {r['clip']} is not at {src}")
        # SENT
        sent = (c.get("params") or {}).get("prompt")
        if sent != c.get("prompt"):
            red.append("SENT: the prompt shown is not the prompt sent (params.prompt differs) — re-plan with "
                       "run.py start … --clips, never edit one copy")
        # APPROVED
        for f in frames:
            p = picture(run, f)
            if p is None:
                continue
            a = approvals.get(f)
            if not a:
                red.append(f"APPROVED: {f} has not been approved — look at it, then clip_gate.py approve")
            elif a.get("sha") != _sha(p):
                red.append(f"APPROVED: {f} changed after {a.get('by')} approved it — look again and approve")
        # FACES
        for pid in in_picture(run, c):
            if lineup_ok.get(pid):
                red.append(lineup_ok[pid])
        # SWIPE WORDS
        for f in frames:
            p = picture(run, f)
            if p is None:
                continue
            if f not in pics_read:
                try:
                    pics_read[f] = read_text(p)
                except Exception as e:                       # no reader on this machine: say so, never pass silently
                    pics_read[f] = None
                    notes.append(f"SWIPE WORDS: could not read {f} ({e})")
            lines = pics_read[f]
            if lines is None:
                red.append(f"SWIPE WORDS: {f} could not be read — words on it are unchecked")
                continue
            boxes = _as_boxes(lines)
            leak = sorted({w for w in _words(" ".join(t for _, t in boxes)) if w in swipe and w not in allowed})
            if leak:
                red.append(f"SWIPE WORDS: {f} carries the swipe's words, in no brief or product file: {', '.join(leak)}")
            held, noted = slop(boxes, allowed, names)
            ok = approvals.get(f"words:{f}") or {}
            if ok.get("sha") == _sha(p):                    # looked at by eye: a word cut off at the edge, not slop
                notes += [f"WORDS: {f} — {x} (cleared by {ok.get('by')})" for x in held if x in (ok.get("lines") or [])]
                held = [x for x in held if x not in (ok.get("lines") or [])]
            red += [f"WORDS: {f} — {x}" for x in held]
            notes += [f"WORDS: {f} — {x}" for x in noted]
        # SKIN
        sc = scenes.get(str(c.get("start_frame") or "").split("-")[0]) or {}
        if oc.scene_even(sc) and re.search(r"\b(?:age[- ]?spots?|dark spots?)\b[^.]*\bon (?:her|his|their) face",
                                          sent or "", re.I):
            red.append("SKIN: the picture shows the skin after the routine, but the prompt still describes "
                       "the spots — re-plan (omni_clips identity_for)")
        # REFUSED
        r = refusals.get(c["id"])
        if r and r.get("prompt_sha") == _text_sha(sent or "") and all(
                r.get("pictures", {}).get(f) == _sha(picture(run, f) or "") for f in frames):
            red.append(f"REFUSED: the model refused this exact request ({r.get('error', '')[:120]}) — change the "
                       "picture or the words before sending it again")
        rows.append({"id": c["id"], "section": c.get("section"), "start": c.get("start_frame"),
                     "green": not red, "red": red, "notes": notes,
                     "text_read": {f: [t for _, t in _as_boxes(pics_read.get(f))] for f in frames}})
    fp = fingerprint(run, calls)
    res = {"checked": time.strftime("%Y-%m-%d %H:%M"), "fingerprint": fp, "only": only or [],
           "green": bool(rows) and all(r["green"] for r in rows), "calls": rows}
    (run / "clips").mkdir(exist_ok=True)
    (run / "clips" / "gate.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    (run / "clips" / "GATE.md").write_text(render(res))
    return res


def fingerprint(run: Path, calls: list[dict]) -> str:
    h = hashlib.sha256()
    for c in sorted(calls, key=lambda x: x["id"]):
        h.update(json.dumps(c.get("params"), sort_keys=True).encode())
        for f in (c.get("start_frame"), c.get("end_frame")):
            p = picture(run, f) if f else None
            h.update((_sha(p) if p else "").encode())
    return h.hexdigest()[:16]


def ready(run: Path, calls: list[dict]) -> list[str]:
    """Called by omni_clips.run_live before any spend: [] = go, else every reason it may not."""
    g = _read(Path(run) / "clips" / "gate.json", None)
    if not g:
        return ["the clip gate has not been run — python3 machine/clip_gate.py check <run>"]
    want = {c["id"] for c in calls}
    rows = {r["id"]: r for r in g.get("calls") or []}
    out = [f"{i}: not checked by the gate" for i in sorted(want - set(rows))]
    for i in sorted(want & set(rows)):
        out += [f"{i}: {x}" for x in rows[i]["red"]]
    if not out and fingerprint(run, calls) != fingerprint(run, [c for c in plan_of(run).get("calls") or []
                                                                  if c["id"] in want]):
        out.append("the plan changed after the gate ran — run clip_gate.py check again")
    if not out:
        checked = [c for c in plan_of(run).get("calls") or [] if c["id"] in rows]
        if fingerprint(run, checked) != g.get("fingerprint"):
            out.append("a picture or prompt changed after the gate ran — run clip_gate.py check again")
    return out


def render(res: dict) -> str:
    n = len(res["calls"])
    ok = sum(1 for r in res["calls"] if r["green"])
    out = [f"# Clip gate — {'GREEN' if res['green'] else 'RED'} · {ok}/{n} clips ready · {res['checked']}", ""]
    for r in res["calls"]:
        out.append(f"- {'✓' if r['green'] else '✗'} **{r['id']}** ({r.get('section')}, from {r.get('start')})")
        out += [f"    - {x}" for x in r["red"] + r["notes"]]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------ approve · remake · coverage

def approve(run: Path, by: str, only: list[str] | None = None) -> list[str]:
    run = Path(run)
    f = run / "clips" / "gate-approved.json"
    a = _read(f, {}) or {}
    ids = sorted({x for c in plan_of(run).get("calls") or [] for x in (c.get("start_frame"), c.get("end_frame"))
                  if x and not str(x).endswith("-LAST")})
    done = []
    for i in ids:
        if only and i not in only:
            continue
        p = picture(run, i)
        if p:
            a[i] = {"sha": _sha(p), "by": by, "at": time.strftime("%Y-%m-%d %H:%M")}
            done.append(i)
    if not only:
        for pid, (img, frames) in lineups(run, plan_of(run).get("calls") or []).items():
            a[f"lineup:{pid}"] = {"sig": _text_sha(" ".join(f"{x}={_sha(picture(run, x) or '')}" for x in frames)),
                                  "by": by, "at": time.strftime("%Y-%m-%d %H:%M"), "image": str(img.relative_to(run))}
            done.append(f"lineup:{pid}")
    f.parent.mkdir(exist_ok=True)
    f.write_text(json.dumps(a, indent=1))
    return done


def clear_words(run: Path, frame: str, by: str, read_text=text_boxes) -> list[str]:
    """A person looked at this picture and found its WORDS findings are not slop (a word cut off at the frame's
    edge). Clears exactly those lines, for exactly this picture: any change to the picture re-opens them."""
    run = Path(run)
    p = picture(run, frame)
    if p is None:
        return []
    rj = _read(run / "run.json", {}) or {}
    held, _ = slop(_as_boxes(read_text(p)), allowed_words(run, rj.get("brand")), names_of(run, rj.get("brand")))
    f = run / "clips" / "gate-approved.json"
    a = _read(f, {}) or {}
    a[f"words:{frame}"] = {"sha": _sha(p), "by": by, "at": time.strftime("%Y-%m-%d %H:%M"), "lines": held}
    f.write_text(json.dumps(a, indent=1))
    return held


def remake(run: Path, ids: list[str]) -> list[str]:
    """Move each clip's made files aside (never deleted) and clear its ledger row, so the next
    `omni_clips.py run --only` really makes it again."""
    run = Path(run)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = run / "clips" / "versions" / stamp
    led_f = run / "clips" / "omni-ledger.json"
    led = _read(led_f, {}) or {}
    moved = []
    for i in ids:
        for src in (run / "clips" / f"{i}.mp4", run / "clips" / "omni" / i):
            if src.exists():
                dest.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest / src.name))
                moved.append(str(src.relative_to(run)))
        rows = led.get("calls", led) if isinstance(led, dict) else {}
        if isinstance(rows, dict) and i in rows:
            rows[i] = {**rows[i], "status": "remake", "previous": str(dest)}
    if isinstance(led, dict):
        led_f.write_text(json.dumps(led, indent=1))
    return moved


def coverage(run: Path, errors: dict | None = None) -> dict:
    """Every planned clip made, or the run is INCOMPLETE with each missing clip named.
    A refusal is recorded against the exact request, so the gate holds that request next time."""
    run = Path(run)
    plan = plan_of(run)
    missing = []
    ref_f = run / "clips" / "gate-refusals.json"
    refusals = _read(ref_f, {}) or {}
    for c in plan.get("calls") or []:
        if not (run / "clips" / f"{c['id']}.mp4").is_file():
            err = (errors or {}).get(c["id"], "")
            missing.append({"id": c["id"], "section": c.get("section"), "why": err or "not made"})
            if err:
                refusals[c["id"]] = {"error": err[:400], "prompt_sha": _text_sha((c.get("params") or {}).get("prompt", "")),
                                     "pictures": {f: _sha(picture(run, f) or "") for f in
                                                  (c.get("start_frame"), c.get("end_frame")) if f},
                                     "at": time.strftime("%Y-%m-%d %H:%M")}
    if errors:
        ref_f.write_text(json.dumps(refusals, indent=1))
    res = {"complete": not missing, "planned": len(plan.get("calls") or []), "missing": missing}
    (run / "clips" / "coverage.json").write_text(json.dumps(res, indent=1))
    return res


def frames_check(run: Path, ids: list[str] | None = None, read_text=text_boxes, at=(0.15, 0.5, 0.85)) -> dict:
    """The same WORDS check on frames of every finished clip — a clip can draw a label the picture did not have.
    Writes clips/frame-check.json: {clip: [held…]}; a clip with anything held is not clean."""
    import tempfile
    run = Path(run)
    plan = plan_of(run)
    doc = _read(run / "plan.json", {}) or {}
    rj = _read(run / "run.json", {}) or {}
    brand = rj.get("brand") or doc.get("brand")
    allowed, names = allowed_words(run, brand), names_of(run, brand)
    out = {}
    for c in plan.get("calls") or []:
        if ids and c["id"] not in ids:
            continue
        mp4 = run / "clips" / f"{c['id']}.mp4"
        if not mp4.is_file():
            continue
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                           capture_output=True, text=True)
        try:
            d = float(r.stdout.strip())
        except ValueError:
            continue
        held = []
        with tempfile.TemporaryDirectory() as t:
            for k, p in enumerate(at):
                jpg = Path(t) / f"{k}.jpg"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{d * p:.2f}", "-i", str(mp4), "-frames:v", "1",
                                "-q:v", "2", str(jpg)], capture_output=True)
                if jpg.is_file():
                    h, _ = slop(_as_boxes(read_text(jpg)), allowed, names)
                    held += [f"{d * p:.1f}s: {x}" for x in h]
        if held:
            out[c["id"]] = held
    (run / "clips" / "frame-check.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the clip gate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("run"); c.add_argument("--only")
    a = sub.add_parser("approve"); a.add_argument("run"); a.add_argument("--by", required=True)
    a.add_argument("--only", help="these pictures only (the face lineups are approved only by a full approve)")
    r = sub.add_parser("remake"); r.add_argument("run"); r.add_argument("ids")
    v = sub.add_parser("coverage"); v.add_argument("run")
    fr = sub.add_parser("frames"); fr.add_argument("run"); fr.add_argument("--only")
    cw = sub.add_parser("clear-words"); cw.add_argument("run"); cw.add_argument("frame"); cw.add_argument("--by", required=True)
    x = ap.parse_args(argv)
    run = Path(x.run).resolve()
    split = lambda s: [t.strip() for t in s.split(",") if t.strip()] if s else None
    if x.cmd == "check":
        res = check(run, split(x.only))
        print(render(res))
        return 0 if res["green"] else 1
    if x.cmd == "approve":
        done = approve(run, x.by, split(x.only))
        print(f"approved as they are now ({x.by}): {', '.join(done) or 'nothing'}")
        return 0
    if x.cmd == "remake":
        moved = remake(run, split(x.ids))
        print("moved aside: " + (", ".join(moved) or "nothing was made yet"))
        return 0
    if x.cmd == "clear-words":
        for l in clear_words(run, x.frame, x.by):
            print(f"  cleared {x.frame}: {l}")
        return 0
    if x.cmd == "frames":
        found = frames_check(run, split(x.only))
        for cid, held in found.items():
            for h in held:
                print(f"  SLOP {cid} {h}")
        print(f"frames: {len(found)} clip(s) with words that are not words")
        return 1 if found else 0
    res = coverage(run)
    print(("COMPLETE" if res["complete"] else "INCOMPLETE") + f" · {res['planned'] - len(res['missing'])}/{res['planned']} clips")
    for m in res["missing"]:
        print(f"  MISSING {m['id']} ({m['section']}): {m['why']}")
    return 0 if res["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
