#!/usr/bin/env python3
"""
footage.py — ask the library before you pay a model. A gate, not a button.

    python3 machine/footage.py --brief <5-brief.md> --brand <brand>   # the ledger beside the brief
    python3 machine/footage.py <run> [--brand <brand>] [--gate]       # an older run's storyboard.json

and, since 2026-10-05, automatically: `run.py start` runs `gate()` on the
plan's scenes BEFORE any still or clip is made (`--dry-run` included).

**Our own footage first** (owner, 2026-10-05: "we need to make sure that the
footage step properly runs … whatever needs to be generated, we can just
generate"). Every B-roll scene is looked up in the brand's indexed footage —
the clips on the company Shared Assets drive. A scene with a confident match is
CUT from that clip (`owned_file` + `owned_in`/`owned_out`) and is not
generated. A scene with no confident match is generated, and carries its
nearest real clip's frame as a visual reference, so the model is shown what our
real footage of that thing looks like.

**brand_a owns 1,349 indexed clips (1,347 found on Shared Assets, 2026-10-06).** On 2026-09-11 an entire ad was
generated — thirty-three clips, about 330 credits — without the index being
asked once. About twenty-five of those thirty-three had owned footage sitting in
it; the right number to generate was about eight (AI-CREATIVE-LINE.md, as
measured that day — the run's own files no longer exist, so the figure is
approximate and is not a test; 2026-10-20).

The search is local: `components/asset-index/machine/search.py` reads the
index records directly — no service, no network, the same answer every time.
The old search service (127.0.0.1:8420) is still asked first if it ever runs
again; when it does not answer, nothing is lost.

**Why owned footage beats generated footage even when both work.** It is real:
a real man's real neck, filmed. It costs nothing. It cannot drift from the
product, invent a wordmark, or put a tripod in the shop. And it is the brand's
own proof — the thing a competitor cannot copy.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = "http://127.0.0.1:8420"
ASSET_INDEX = HERE.parents[1] / "asset-index" / "machine"


def _by_path(name: str, path: Path):
    import importlib.util
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# the asset index's own reader and its Shared Assets map — loaded by path,
# so no other module named `search` on sys.path can stand in for it
shared_paths = _by_path("shared_paths", ASSET_INDEX / "shared_paths.py")
lib_search = _by_path("asset_index_search", ASSET_INDEX / "search.py")
# the brand's footage library (tier, polish, text marks, handles, people per scene): every candidate is
# enriched from it, duplicates of one file dropped, talking-to-camera scenes kept out of b-roll, direct
# b-roll first. A brand with no built library, or a missing library, leaves the hits as they were.
try:
    lib_library = _by_path("asset_index_library", ASSET_INDEX.parent / "library" / "library.py")
except Exception:  # noqa: BLE001
    lib_library = None

# A scene is CUT from our footage at or above this score (0..1: how much of
# what the scene shows, weighted by how rare each word is, the clip's scene
# also shows — plus a quarter for the words said over it). Below it the scene
# is generated, with the best clip as its picture reference. Overridable per
# run (FOOTAGE_CONFIDENT) while owner judges the first cuts.
CONFIDENT = float(os.environ.get("FOOTAGE_CONFIDENT", "0.42"))
# ...and only when the clip does the ACTION, not just shares the frame's
# furniture: at least this share of the action's words (rarity-weighted) are in
# the clip's scene, and the action has at least ACTION_WORDS words to judge by —
# "holds still, looking at the lens" is a face, not a shot the library can stand in for.
ACTION_MATCH = 0.4
ACTION_WORDS = 2
# A candidate below this is not shown at all — it is noise, not a reference.
FLOOR = 0.12

# DESCRIBE ON USE (LD-63, 2026-10-21): a scene whose best candidates are name-only records (described false — no
# scenes, no in/out, so they can never be cut) gets its top DESCRIBE_N video candidates described first, then the
# cut-or-generate call is made on what they really show. Capped per scene and per brief, in clips and dollars;
# a dry run describes nothing and says what it would. Off unless the caller asks (run.py start does).
DESCRIBE_N = int(os.environ.get("FOOTAGE_DESCRIBE_N", "3"))
DESCRIBE_MAX = int(os.environ.get("FOOTAGE_DESCRIBE_MAX", "12"))
DESCRIBE_USD = float(os.environ.get("FOOTAGE_DESCRIBE_USD", "0.50"))

# THE PRESENTER IS NEVER REPLACED BY THE LIBRARY.
#
# 2026-09-11: footage-first was applied to every scene, so eighteen of Nina's
# talking beats were swapped for other creators talking, and the ad stopped
# being hers. The saving was real and the ad was ruined.
#
# A type-A beat is the brand's own presenter saying the brand's own script in
# the brand's own voice. No clip in the library is that, however well it
# matches on words — matching on words is exactly how a different person ends
# up delivering the line.
#
# Footage-first is a rule about B-ROLL: inserts, demonstrations, reactions,
# product in a real hand. It is not a rule about who fronts the ad.
PRESENTER_TYPES = {"A"}
# Kinds that are made, not filmed: a card is a plate and its words, the endcard
# the real packshot, a screen/split/greenscreen a layout. Never the library's.
NOT_FOOTAGE = {"card", "endcard", "screen", "split", "greenscreen", "talking"}


# ------------------------------------------------------------ the question

def _first_frame(s: dict) -> dict:
    ff = s.get("first_frame")
    if isinstance(ff, dict):
        return ff
    return next((f for f in s.get("frames") or [] if f.get("role") == "first"), {}) or {}


def role_of(s: dict) -> str:
    """presenter | not-footage | held | broll."""
    if s.get("type") in PRESENTER_TYPES or s.get("to_camera") is True:
        return "presenter"
    if "to_camera" not in s and "type" not in s:
        # an older plan's `scenes` ARE its talking beats (its inserts are
        # `cutaways`), and a scene that does not say is never handed to the
        # library — the presenter rule wins every tie
        return "presenter"
    if (s.get("kind") or "") in NOT_FOOTAGE:
        return "not-footage"
    if str(s.get("held") or "").strip():
        return "held"
    return "broll"


def names_of(s: dict, cast_names=()) -> set[str]:
    """Invented names in a scene — never search words (KEMAR, OTIS, THE DEFENDERS)."""
    raw = [s.get("who") or "", s.get("speaker") or "", *list((s.get("looks") or {}).keys())]
    out = set()
    for r in raw:
        if isinstance(r, str):
            out |= {w.lower() for w in re.findall(r"[A-Za-z]+", r) if w.isupper() and len(w) > 2}
    for r in cast_names:
        out |= {w.lower() for w in re.findall(r"[A-Za-z]+", str(r)) if len(w) > 2}
    return out - {"hands", "hand"}


def query_for(s: dict) -> tuple[str, str]:
    """(what the shot shows, what is said over it). Scene shape, brief row or
    an older storyboard row — whichever fields it has."""
    ff = _first_frame(s)
    seen = " ".join(x for x in [
        s.get("happens") or "", ff.get("subject") or "", ff.get("action") or "",
        s.get("action") or "", s.get("subject") or "",
        "" if (s.get("happens") or ff.get("subject")) else (s.get("product") or s.get("source") or ""),
    ] if x).strip()
    said = (s.get("voice") or s.get("line") or s.get("say") or "").strip()
    if said.lower().startswith("none"):
        said = ""
    return seen[:600], said[:400]


def required_of(s: dict, cast_names=()) -> list[str]:
    """Named things the shot shows — a product (FLEX™, PRIME™), written in
    capitals or carrying ™/®. A clip without them cannot be cut in for the
    shot: a real hand holding some other bottle is not this product."""
    seen, _ = query_for(s)
    text = f"{seen} {core_of(s)}"
    names = names_of(s, cast_names) | {"the", "and", "new", "hands", "hand", "none"}
    out = set(re.findall(r"([A-Za-z][A-Za-z0-9\-]+)\s*[™®]", text))
    out |= {w for w in re.findall(r"\b[A-Z][A-Z0-9\-]{2,}\b", text)}
    return sorted(w for w in out if w.lower() not in names)


def core_of(s: dict) -> str:
    """The action itself — what HAPPENS in the shot, its first frame's action
    and each beat's one verb — apart from the furniture of the frame."""
    ff = _first_frame(s)
    beats = " ".join(str(b.get("do") or "") for b in s.get("beats") or [] if isinstance(b, dict))
    return " ".join(x for x in [s.get("happens") or "", ff.get("action") or "", s.get("action") or "",
                                beats] if x).strip()[:400]


def _service(seen: str, said: str, s: dict, per: int) -> list[dict]:
    """The old search service, if it ever runs again. Silent when it does not."""
    body = json.dumps({"beats": [{"n": s.get("n") or 1, "beat": (seen + " " + said).strip()[:260],
                                  "timing": f'{s.get("start") or 0}-{s.get("end") or 0}'}],
                       "per_beat": per, "min_cover": 0.18, "floor": 0.55}).encode()
    try:
        r = urllib.request.Request(INDEX + "/api/recommend", data=body,
                                   headers={"Content-Type": "application/json"})
        d = json.load(urllib.request.urlopen(r, timeout=1.5))
        return (d.get("beats") or [{}])[0].get("picks") or []
    except Exception:
        return []


def _describe_first(s, brand, seen, said, cast_names, work, maps, budget):
    """Describe this scene's top name-only VIDEO candidates (LD-63 (describe on use)), within `budget`
    ({"clips", "usd", "dry", "log"}). Returns True when anything new was described."""
    if not budget or budget["clips"] <= 0 or budget["usd"] <= 0:
        return False
    named = lib_search.search(seen, said, brand, core=core_of(s), require=required_of(s, cast_names),
                              per=DESCRIBE_N * 3, drop=names_of(s, cast_names), work=work, maps=maps, mapped=True)
    pick = [h for h in named if h.get("described") is False and h.get("kind") == "video"
            and h["score"] >= FLOOR * lib_search.MAPPED_WEIGHT][:min(DESCRIBE_N, budget["clips"])]
    if not pick:
        return False
    desc = _by_path("asset_index_describe", ASSET_INDEX / "describe.py")
    dirs = [h["record_dir"] for h in pick if h.get("record_dir")]
    got = desc.describe_on_use(dirs, budget["usd"], "footage gate: scene %s" % s.get("id"), brand=brand,
                               dry_run=budget.get("dry", False))
    budget["log"].append({"scene": s.get("id"), "asked": [Path(d).name for d in dirs],
                          **{k: got.get(k) for k in ("described", "failed", "spent_usd", "stopped", "would_describe", "est_usd")}})
    if budget.get("dry"):
        budget["clips"] -= got["would_describe"]
        budget["usd"] -= got["est_usd"]
        return False
    budget["clips"] -= len(got["described"]) + len(got["failed"])
    budget["usd"] -= got["spent_usd"]
    if got.get("stopped", "") and "quota" in str(got["stopped"]):
        budget["clips"] = 0
    if got["described"]:
        lib_search._corpus.cache_clear()
        return True
    return False


def ask(s: dict, brand: str = "", per: int = 3, cast_names=(), work=None, maps=None,
        service: bool = True, budget=None) -> list[dict]:
    """Owned candidates for one scene, best first. Never for the presenter. With a `budget`, name-only video
    candidates are described first (LD-63 (describe on use))."""
    if role_of(s) != "broll":
        return []
    seen, said = query_for(s)
    if not (seen or said):
        return []
    if budget is not None:
        _describe_first(s, brand, seen, said, cast_names, work, maps, budget)
    use_lib = lib_library is not None and not work
    hits = lib_search.search(seen, said, brand, core=core_of(s), require=required_of(s, cast_names),
                             per=per * 4 if use_lib else per,   # a wider set, so the library can rank direct b-roll first
                             drop=names_of(s, cast_names),
                             work=work, maps=maps,
                             mapped=False)   # a name-only record has no in/out to cut (LD-59 (image records)); LD-63 describes first
    hits = [h for h in hits if h["score"] >= FLOOR]
    if use_lib:
        try:
            hits = lib_library.enrich(hits, brand)
        except Exception:  # noqa: BLE001 — the library only adds; it never stops the footage pass
            pass
        hits = hits[:per]
    if hits or not service:
        return hits
    # nothing local — the old service, mapped onto Shared Assets or dropped
    out = []
    for p in _service(seen, said, s, per):
        cid = p.get("clip_id") or p.get("id")
        for col in _cols(brand, work):
            path = shared_paths.shared_path(col, str(cid), maps) if cid else None
            if path:
                out.append({"clip_id": cid, "collection": col.name, "score": float(p.get("score") or 0),
                            "in": p.get("t_start") or p.get("in") or 0, "out": p.get("t_end") or p.get("out"),
                            "shared_path": path, "frame": p.get("frame"), "shows": p.get("visuals") or "",
                            "says": p.get("spoken") or "", "from": "service"})
                break
    return out


def _cols(brand, work=None):
    """runs/asset-index/<brand>/ first (in git, keyed by Drive id — LD-56 (footage index in git)), then work/;
    a test's own work folder alone when one is given."""
    return shared_paths.collections_of(brand, work) if work else shared_paths.collections(brand)


def has_index(brand: str, work=None, maps=None) -> bool:
    return any(shared_paths.load_map(c, maps) for c in _cols(brand, work))


# ------------------------------------------------------------ the gate

def confident(h: dict) -> bool:
    """A candidate good enough to CUT in for the shot, not just to show the
    generator: the score, the action itself, and every named product in it."""
    if h.get("score", 0) < CONFIDENT or h.get("missing"):
        return False
    if h.get("action_match") is None:          # the caller gave no action to judge by
        return True
    return h["action_match"] >= ACTION_MATCH and (h.get("action_words") or 0) >= ACTION_WORDS


def _frame(hit: dict):
    """The one pick's frame, asked for here: search returns none it would have to fetch (the full-download
    guard, 2026-10-21); asset-index rebuilds it with a ranged seek, seconds, never the whole clip."""
    if hit.get("frame") or not hit.get("record_dir"):
        return hit.get("frame")
    try:
        return lib_search.frame_of(hit)
    except Exception:  # noqa: BLE001
        return None


def _in_place(s: dict, h: dict) -> bool:
    """Is this clip from the scene's own setting? Its words must carry the place's name, so a matching action filmed
    somewhere else is never picked (2026-10-31: a brush at home for a scene in a barber chair)."""
    words = [w for w in re.findall(r"[a-z]+", str(s.get("setting_id") or "").lower())
             if len(w) > 3 and w not in ("room", "studio", "home", "place", "suite")]
    text = f"{h.get('shows') or ''} {h.get('says') or ''}".lower()
    return not words or any(w in text for w in words)


def evidence_of(h: dict | None) -> dict:
    """What the match was judged on, in one row: the clip, its score against the bar, how much of the ACTION it does,
    any named product it lacks, and the library's tier and text marks. The route rule (shot_route.py) decides on this
    and says so; the score is its evidence, never a decision of its own (the logic layer, 2026-11-18)."""
    if not h:
        return {}
    return {"clip": h.get("clip_id"), "score": round(float(h.get("score") or 0), 3), "bar": CONFIDENT,
            "action_match": h.get("action_match"), "action_words": h.get("action_words"),
            "missing": list(h.get("missing") or []), "tier": h.get("tier"),
            "marks": list(h.get("text_marks") or []) if "text_marks" in h else None}


def why_of(h: dict | None, cut: bool, set_aside=()) -> str:
    """The footage decision in one plain sentence, so the next stage reads a reason and not only a plan word."""
    aside = ("; set aside first: " + "; ".join(f"{x['clip']} ({x['why']})" for x in set_aside)) if set_aside else ""
    if not h:
        return "generated: no clip of ours comes close" + aside
    e = evidence_of(h)
    name = f"clip {e['clip']}"
    if cut:
        bits = [f"scores {e['score']:.2f} against a bar of {e['bar']:.2f}"]
        if e["action_match"] is not None:
            bits.append(f"does the action ({e['action_match']:.2f} of its words)")
        if e["marks"] is not None:
            bits.append("no words burned in" if e["marks"] == ["clean"] else "marks: " + ", ".join(e["marks"]))
        return f"cut from our footage: {name} " + ", ".join(bits) + aside
    if e["missing"]:
        short = "does not show " + ", ".join(e["missing"])
    elif e["score"] < e["bar"]:
        short = f"scores {e['score']:.2f}, under the bar of {e['bar']:.2f}"
    else:
        short = (f"shares the frame but not the action ({float(e['action_match'] or 0):.2f} of its words, "
                 f"{ACTION_MATCH:.2f} needed over at least {ACTION_WORDS} words)")
    return f"generated: our nearest {name} {short}" + aside


def caption_free(h: dict, brand: str = "") -> bool:
    """No words burned into the clip (owner, 16 Nov 2026): a caption, offer text, handle or app screen already on a
    clip is someone else's edit, never b-roll or an AI reference frame for ours. The index's text marks decide; a clip
    the brand's built library does not know is unknown, so it is out too. A brand with no library is not judged."""
    if "text_marks" in h:
        return list(h.get("text_marks") or []) == ["clean"]
    try:
        return not lib_library.rows_of(brand)
    except Exception:                                  # noqa: BLE001 - no library module: nothing to judge by
        return True


def usable(picks: list[dict], brand: str, used: set, judged: bool = True) -> tuple[list[dict], list[dict]]:
    """(the candidates a scene may be cut from or shown as a reference, the ones set aside with why). Two rules, both
    asked before the decision so a scene they rule out is generated in the same pass: no clip with words burned in
    (`judged` False = a test's own index, which has no library to mark clips), and never one clip section twice
    (`used` holds every section already laid on an earlier scene)."""
    keep, aside = [], []
    for h in picks:
        k = (h.get("shared_path"), h.get("in"), h.get("out"))
        if judged and not caption_free(h, brand):
            marks = ", ".join(h.get("text_marks") or []) or "not in the footage library"
            aside.append({"clip": h.get("clip_id"), "why": f"words burned in ({marks})"})
        elif k in used:
            aside.append({"clip": h.get("clip_id"), "why": "the same clip section is already on an earlier scene"})
        else:
            keep.append(h)
    return keep, aside


def _decide(s: dict, picks: list[dict], set_aside=()) -> str:
    picks = [h for h in picks if _in_place(s, h)]
    s["owned_candidates"] = picks
    for k in ("owned_file", "owned_in", "owned_out", "owned_clip", "owned_frame", "footage_ref",
              "owned_tier", "owned_marks", "owned_evidence", "footage_why"):
        s.pop(k, None)
    top = next((h for h in picks if confident(h)), None)
    if top:
        s["source_plan"] = "cut"
        s["owned_file"] = top["shared_path"]
        s["owned_in"], s["owned_out"] = top["in"], top["out"]
        s["owned_clip"] = top["clip_id"]
        s["owned_frame"] = _frame(top)
        if top.get("tier"):
            s["owned_tier"], s["owned_marks"] = top["tier"], top.get("text_marks") or []
        s["owned_evidence"], s["footage_why"] = evidence_of(top), why_of(top, True, set_aside)
        return "cut"
    s["source_plan"] = "generate"
    top = picks[0] if picks else None
    s["owned_evidence"], s["footage_why"] = evidence_of(top), why_of(top, False, set_aside)
    if top and not top.get("frame"):
        top["frame"] = _frame(top)
    if top and top.get("frame"):
        # the nearest real clip, shown to the generator as a picture reference
        s["footage_ref"] = {"frame": top["frame"], "clip": top["clip_id"],
                            "file": top["shared_path"], "score": top["score"]}
        ff = _first_frame(s)
        if ff is not None and isinstance(ff.get("refs"), list) and top["frame"] not in ff["refs"]:
            ff["refs"].append(top["frame"])
    return "generate"


def gate(plan: dict, brand: str, *, work=None, maps=None, service: bool = True, describe=False) -> dict:
    """Run the footage pass over a plan's scenes (and an older plan's cutaways),
    in place. `describe` True = name-only candidates are described first, within the brief's caps;
    "dry" = say what would be described, spend nothing. -> {"cut": [...], "generate": [...],
    "presenter": [...], "other": [...], "indexed": bool, "described": [per-scene log]}."""
    res = {"cut": [], "generate": [], "presenter": [], "other": [], "indexed": has_index(brand, work, maps)}
    budget = ({"clips": DESCRIBE_MAX, "usd": DESCRIBE_USD, "dry": describe == "dry", "log": []}
              if describe else None)
    if budget is not None:
        res["described"] = budget["log"]
    cast = plan.get("cast") or {}
    cast_names = tuple(str(n) for n in [*(cast.get("names") or []), cast.get("name"), cast.get("presenter"),
                                        *(cast.get("also") or [])] if n and isinstance(n, str))
    # ONE DECISION, WITH ITS REASON (the logic layer, 2026-11-18). Before a scene is decided its candidates lose every
    # clip with words burned in and every clip section an earlier scene already took, so a scene those rules leave
    # without a clip is generated in this same pass (never a cut that the edit then cannot use). `_decide` writes what
    # the match was judged on (`owned_evidence`) and the reason in words (`footage_why`) on the scene.
    used, judged = set(), lib_library is not None and not work

    def decide(s, picks):
        keep, aside = usable(picks, brand, used, judged=judged)
        got = _decide(s, keep, aside)
        if got == "cut":
            used.add((s.get("owned_file"), s.get("owned_in"), s.get("owned_out")))
        return got

    for s in plan.get("scenes") or []:
        r = role_of(s)
        if r == "presenter":
            s["source_plan"] = "presenter"
            s["owned_candidates"] = []
            s.pop("owned_file", None)
            res["presenter"].append(s["id"])
            continue
        if r != "broll":
            res["other"].append(s["id"])
            continue
        if not res["indexed"]:
            res["generate"].append(s["id"])
            continue
        res[decide(s, ask(s, brand, cast_names=cast_names, work=work, maps=maps, service=service,
                          budget=budget))].append(s["id"])
    # an older plan's inserts are its cutaways — same rule, same fields
    for c in plan.get("cutaways") or []:
        if not res["indexed"]:
            res["generate"].append(c["id"])
            continue
        res[decide(c, ask({**c, "kind": "broll", "to_camera": False}, brand, cast_names=cast_names,
                          work=work, maps=maps, service=service))].append(c["id"])
    return res


def report(res: dict, saved: dict | None = None) -> None:
    for row in res.get("described") or []:
        if row.get("would_describe") and not row.get("described"):
            print(f"footage: scene {row['scene']} would describe {row['would_describe']} clip(s), ~${row['est_usd']:.2f} (dry run)")
        elif row.get("described") or row.get("failed"):
            print(f"footage: scene {row['scene']} described {len(row['described'])} clip(s) for ${row['spent_usd']:.4f}"
                  + (f", {len(row['failed'])} failed" if row.get("failed") else "")
                  + (f" — stopped: {row['stopped']}" if row.get("stopped") else ""))
    if not res["indexed"]:
        print("footage: no footage index on this machine (the asset index lives on the Mac that built it) — every B-roll scene is generated")
        return
    print(f"footage: {len(res['cut'])} B-roll scene(s) CUT from our footage · "
          f"{len(res['generate'])} to GENERATE · {len(res['presenter'])} presenter (never the library)"
          + (f" · {len(res['other'])} cards/plates/layouts" if res["other"] else ""))
    if saved and res["cut"]:
        bits = []
        if saved.get("credits"):
            bits.append(f"~{saved['credits']:g} credits")
        if saved.get("usd"):
            bits.append(f"~${saved['usd']:.2f}")
        print(f"footage: {saved.get('items', 0)} still(s)/clip(s) not made"
              + (f" — {' / '.join(bits)} saved" if bits else ""))


# ------------------------------------------------------------ the brief ledger

def brief_pass(brief: Path, brand: str, *, work=None, maps=None, service: bool = True, per: int = 3,
               out_dir: Path | None = None) -> dict:
    """The footage ledger beside a brief (or in `out_dir`): footage.json +
    footage.md. Reads the brief, writes only those two files."""
    sys.path.insert(0, str(HERE))
    import scenes as scenes_mod
    text = Path(brief).read_text()
    doc, why = scenes_mod.json_block(text)
    if not isinstance(doc, dict) or not doc.get("scenes"):
        raise SystemExit(f"{brief}: no scene block to read ({why or 'no scenes'})")
    cast_names = tuple(str(c.get("name") or c.get("id") or "") for c in doc.get("cast") or []
                       if isinstance(c, dict))
    indexed = has_index(brand, work, maps)
    rows = []
    for s in doc["scenes"]:
        if not isinstance(s, dict):
            continue
        s = json.loads(json.dumps(s))
        r = role_of(s)
        seen, said = query_for(s)
        row = {"scene": s.get("id"), "kind": s.get("kind"), "role": r, "shows": seen[:240], "said": said[:240]}
        if r == "broll":
            picks = ask(s, brand, per=per, cast_names=cast_names, work=work, maps=maps, service=service) \
                if indexed else []
            row["plan"] = _decide(s, picks)
            row["candidates"] = [{k: h.get(k) for k in ("clip_id", "score", "in", "out", "shared_path",
                                                        "frame", "shows", "says", "tier", "polish", "text_marks",
                                                        "cut_source", "label_in", "label_out")}
                                 for h in picks]
        else:
            row["plan"] = {"presenter": "presenter", "held": "held"}.get(r, "made")
        rows.append(row)
    broll = [r for r in rows if r["role"] == "broll"]
    out = {"brief": str(Path(brief).resolve()), "brand": brand,
           "made": datetime.now().isoformat(timespec="seconds"),
           "confident_at": CONFIDENT, "indexed": indexed,
           "broll": len(broll), "cut": sum(r["plan"] == "cut" for r in broll),
           "generate": sum(r["plan"] == "generate" for r in broll), "scenes": rows}
    d = Path(out_dir) if out_dir else Path(brief).parent
    d.mkdir(parents=True, exist_ok=True)
    apply_picks(out, read_picks(d))
    (d / "footage.json").write_text(json.dumps(out, indent=1))
    (d / "footage.md").write_text(ledger_md(out))
    return out



# ------------------------------------------------------------ the storyboard's footage, shot by shot (2026-11-16)
# The owner, 16 Nov: "we have enough real content for it… this is where asset index comes into play… this should be
# the chain, not me". When a storyboard is written the chain asks the library for every shot (each scene as written
# is one or more shots of the joined storyboard) and decides, with the gate's own rules above, cut or generate.
# Two more rules, from the edit (context, 10 Nov): only OUR footage (our creators' folders and the brand's own clips,
# never swipes, references or archived posts of other people), and ONE demographic per edit — every creator in one
# edit from one gender / ethnicity / age band, read off the folder `content-creators/<gender>/<ethnicity>/<age>/<who>/`;
# a creator already in the edit wins a close call (fewer, repeated creators beat many strangers).

NOT_OURS = ("/intake/", "/archive/", "/references/", "/swipe/", "/competitors/")
SAME_CREATOR = 0.04


def band_of(path) -> tuple:
    """(band "gender/ethnicity/age", creator) for a creator's clip; (None, None) for the brand's own footage."""
    m = re.search(r"/content-creators/([^/]+)/([^/]+)/([^/]+)/([^/]+)/", str(path or ""))
    return ("/".join(m.groups()[:3]), m.group(4)) if m else (None, None)


def ours(h: dict) -> bool:
    p = str(h.get("shared_path") or "")
    return bool(p) and not any(x in p for x in NOT_OURS)


CLOSE = re.compile(r"\b(?:extreme close|close-up|close up|closeup|macro|insert)\b|\bclose\b", re.I)


def place_shown(s: dict) -> bool:
    """Does the shot show its room? Not when every shot of it, and its first frame, is a close-up: then the place rule
    (a clip must be from the scene's own setting, 2026-10-31) has nothing to judge, and a clip from any room serves."""
    ff = s.get("first_frame") or {}
    framing = [str(sh.get("angle") or "") for sh in s.get("shots") or [] if isinstance(sh, dict)] + \
              [str(ff.get("composition") or "")]
    framing = [f for f in framing if f.strip()]
    return not framing or not all(CLOSE.search(f) for f in framing)


def storyboard_pass(brief: Path, brand: str, *, work=None, maps=None, service: bool = False, per: int = 6,
                    write: bool = True) -> dict:
    """Cut or generate, for every scene as written of a storyboard brief (the as-written brief: a joined scene's old
    scenes are its shots). -> {"band", "creators", "scenes": {scene id: {"plan", "clip"?, "ref"?}}}; with `write`,
    storyboard-footage.json + .md beside the brief. Reads the brief; spends nothing."""
    sys.path.insert(0, str(HERE))
    import scenes as scenes_mod
    doc, why = scenes_mod.json_block(Path(brief).read_text())
    if not isinstance(doc, dict) or not doc.get("scenes"):
        raise SystemExit(f"{brief}: no scene block to read ({why or 'no scenes'})")
    cast_names = tuple(str(c.get("name") or c.get("id") or "") for c in doc.get("cast") or [] if isinstance(c, dict))
    indexed = has_index(brand, work, maps)
    asked = []
    for s in doc["scenes"]:
        if not isinstance(s, dict):
            continue
        s = json.loads(json.dumps(s))
        r = role_of(s)
        picks = [h for h in ask(s, brand, per=per, cast_names=cast_names, work=work, maps=maps, service=service)
                 if ours(h)] if (r == "broll" and indexed) else []
        asked.append((s, r, picks))
    votes = {}
    for _, r, picks in asked:
        for h in picks[:3]:
            b, _who = band_of(h.get("shared_path"))
            if b:
                votes[b] = votes.get(b, 0.0) + float(h.get("score") or 0)
    band = max(votes, key=votes.get) if votes else None
    used, out = [], {}
    for s, r, picks in asked:
        if r != "broll":
            out[s.get("id")] = {"plan": {"presenter": "presenter", "held": "held"}.get(r, "made"), "role": r}
            continue
        keep = [h for h in picks if band_of(h.get("shared_path"))[0] in (band, None)]
        shown = place_shown(s)
        if not shown:                      # a close-up shows no room: the place cannot rule a clip out
            s = dict(s, setting_id="")
        keep.sort(key=lambda h: -(float(h.get("score") or 0) +
                                  (SAME_CREATOR if band_of(h.get("shared_path"))[1] in used else 0)))
        plan = _decide(s, keep)
        row = {"plan": plan, "role": r, "place": "shown" if shown else "not in frame (close-up)"}
        if keep:                           # the nearest clip of ours, cut or not, so the board shows how close we are
            n = keep[0]
            b0, who0 = band_of(n.get("shared_path"))
            row["nearest"] = {"shared_path": n.get("shared_path"), "in": n.get("in"), "out": n.get("out"),
                              "clip_id": n.get("clip_id"), "frame": n.get("frame") or _frame(n), "score": n.get("score"),
                              "creator": who0, "band": b0, "shows": n.get("shows") or ""}
        if plan == "cut":
            b, who = band_of(s["owned_file"])
            row["clip"] = {"shared_path": s["owned_file"], "in": s["owned_in"], "out": s["owned_out"],
                           "clip_id": s["owned_clip"], "frame": s.get("owned_frame"), "band": b, "creator": who,
                           "shows": next((h.get("shows") for h in keep if h.get("clip_id") == s["owned_clip"]), "")}
            if who and who not in used:
                used.append(who)
        elif s.get("footage_ref"):
            row["ref"] = s["footage_ref"]
        out[s.get("id")] = row
    res = {"brief": str(Path(brief).resolve()), "brand": brand, "made": datetime.now().isoformat(timespec="seconds"),
           "confident_at": CONFIDENT, "indexed": indexed, "band": band, "creators": used,
           "cut": sum(1 for v in out.values() if v["plan"] == "cut"),
           "generate": sum(1 for v in out.values() if v["plan"] == "generate"), "scenes": out}
    if write:
        d = Path(brief).parent
        (d / "storyboard-footage.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
        lines = ["# Footage for the storyboard", "",
                 f"Band: {band or 'none'} · creators: {', '.join(used) or 'none'} · cut {res['cut']} · generate {res['generate']}", ""]
        for sid, v in out.items():
            c = v.get("clip") or {}
            lines.append(f"- {sid}: {v['plan']}" + (f" — {c.get('creator') or 'brand footage'} {c.get('in')}–{c.get('out')} s, "
                                                      f"{c.get('shared_path')}" if c else ""))
        (d / "storyboard-footage.md").write_text("\n".join(lines) + "\n")
    return res

# ------------------------------------------------------------ the editor's picks (Footage Library board)
# `picks.json` beside the brief, schema editor-picks/v1: the shots an editor picked on the board, each with the
# brief scene it is for (`for_scene`) or none (the brief's pool). A pick for a B-roll scene makes that scene a cut
# from the picked clip at the picked times; the ledger lists the picks first. Rebuilding the ledger keeps them.

PICKS = "picks.json"


def read_picks(d: Path) -> dict:
    try:
        doc = json.loads((Path(d) / PICKS).read_text())
        return doc if isinstance(doc, dict) and isinstance(doc.get("picks"), list) else {"picks": []}
    except (OSError, ValueError):
        return {"picks": []}


def apply_picks(out: dict, doc: dict) -> dict:
    """Put the editor's picks into a ledger: a picked B-roll scene is a cut from its pick (first candidate)."""
    by_scene = {}
    for k in doc.get("picks") or []:
        if k.get("for_scene") is not None:
            by_scene.setdefault(str(k["for_scene"]), []).append(k)
    for r in out.get("scenes") or []:
        if r.get("role") != "broll":
            continue
        r["candidates"] = [h for h in r.get("candidates") or [] if h.get("source") != "editor pick"]
        if "plan_before_pick" in r:
            r["plan"] = r.pop("plan_before_pick")
        r.pop("editor_pick", None)
        mine = by_scene.get(str(r.get("scene")))
        if not mine:
            continue
        k = mine[-1]
        r["plan_before_pick"], r["plan"], r["editor_pick"] = r.get("plan"), "cut", k
        r["candidates"].insert(0, {"clip_id": k.get("clip_id"), "score": None, "in": k.get("in"), "out": k.get("out"),
                                   "shared_path": k.get("shared_path"), "frame": None, "shows": k.get("shows"),
                                   "says": None, "tier": k.get("tier"), "polish": None, "text_marks": k.get("text_marks"),
                                   "cut_source": k.get("cut_source"), "source": "editor pick"})
    broll = [r for r in out.get("scenes") or [] if r.get("role") == "broll"]
    out["cut"] = sum(r.get("plan") == "cut" for r in broll)
    out["generate"] = sum(r.get("plan") == "generate" for r in broll)
    out["editor_picks"] = doc.get("picks") or []
    return out


def write_picks(d: Path, brand: str, brief: str, picks: list) -> dict:
    """Merge picks sent from the board into `picks.json`: a pick for a scene replaces that scene's pick, the same
    clip moment is never listed twice; then refresh footage.json / footage.md beside it when they exist."""
    d = Path(d)
    doc = read_picks(d)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    have = [k for k in doc.get("picks") or [] if isinstance(k, dict)]
    for k in picks:
        k = {**k, "picked_at": k.get("picked_at") or now}
        have = [h for h in have if h.get("id") != k.get("id")
                and (k.get("for_scene") is None or str(h.get("for_scene")) != str(k.get("for_scene")))]
        have.append(k)
    doc = {"schema": "editor-picks/v1", "brand": brand, "brief": brief, "updated": now, "picks": have}
    d.mkdir(parents=True, exist_ok=True)
    (d / PICKS).write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    led = d / "footage.json"
    if led.is_file():
        out = apply_picks(json.loads(led.read_text()), doc)
        led.write_text(json.dumps(out, indent=1))
        (d / "footage.md").write_text(ledger_md(out))
    return doc


def ledger_md(out: dict) -> str:
    L = [f"# Footage — our own clips for this brief",
         "",
         f"{out['broll']} B-roll scene(s): **{out['cut']} cut from our footage**, "
         f"**{out['generate']} to generate**. A match is cut at a score of {out['confident_at']:.2f} or more; "
         "below that the scene is generated with the nearest real clip as its picture reference. "
         "Tier A is direct b-roll, B is for montage or proof; the text column lists what is burned in "
         "(captions, handles, watermarks), so a pick can be chosen knowing it. Times marked (on the cut) start "
         "and end on the clip's real shot change.",
         ""]
    if not out["indexed"]:
        L += ["No indexed footage for this brand on Shared Assets — every B-roll scene is generated.", ""]
    folder = Path(str(out.get("brief") or "")).parent.parent.name
    if folder and out.get("brand"):
        L += [f"Edit this brief scene by scene on the Brief Editing Board: http://localhost:8916/{out['brand']}/{folder}/ "
              "(the `brief-board` launch entry in this workspace): swap a scene's clip in one tap, trim its in and out, "
              "preview the cut. Every change is a new version of the cut sheet.", ""]
    ep = out.get("editor_picks") or []
    if ep:
        L += ["## Editor picks", "", "Picked on the Footage Library board. A pick for a scene is that scene's cut.", "",
              "| for scene | clip | time in clip | what it shows | tier · text on screen | file on Shared Assets |",
              "|---|---|---|---|---|---|"]
        for k in sorted(ep, key=lambda k: (k.get("for_scene") is None, str(k.get("for_scene")))):
            oncut = " (on the cut)" if k.get("cut_source") not in (None, "label") else ""
            nd = 2 if oncut else 1
            tm = f"{k.get('tier') or '—'} · {', '.join(k.get('text_marks') or [])}"
            t = (f"{float(k['in']):.{nd}f}–{float(k['out']):.{nd}f}s{oncut}" if k.get("in") is not None else "photo")
            L.append(f"| {k.get('for_scene') or 'any (pool)'} | {k.get('clip_id')} | {t} | "
                     f"{(k.get('shows') or '').replace('|', '/')[:120]} | {tm} | `{k.get('shared_path')}` |")
        L.append("")
    for r in out["scenes"]:
        if r["role"] != "broll":
            continue
        verdict = ("EDITOR PICK — cut from our footage" if r.get("editor_pick") else
                   "REAL CLIP — cut from our footage" if r["plan"] == "cut" else "GENERATE")
        L += [f"## {r['scene']} — {verdict}", "", f"Shows: {r['shows']}", ""]
        if r.get("said"):
            L += [f"Over it: “{r['said']}”", ""]
        if not r.get("candidates"):
            L += ["No clip of ours comes close.", ""]
            continue
        L += ["| score | clip | time in clip | what it shows | tier · text on screen | frame | file on Shared Assets |",
              "|---|---|---|---|---|---|---|"]
        for h in r["candidates"]:
            fr = f"![]({h['frame']})" if h.get("frame") else "—"
            tm = (f"{h['tier']} · {', '.join(h.get('text_marks') or [])}" if h.get("tier") else "—")
            ad = ((h.get("library") or {}).get("used_in") or {}).get("name")
            tm += f" · from ad {ad}" if ad else ""
            oncut = " (on the cut)" if h.get("cut_source") == "shot change" else ""
            nd = 2 if h.get("cut_source") not in (None, "label") else 1
            sc = "pick" if h.get("score") is None else f"{h['score']:.2f}"
            tc = f"{float(h['in']):.{nd}f}–{float(h['out']):.{nd}f}s{oncut}" if h.get("in") is not None else "photo"
            L.append(f"| {sc} | {h['clip_id']} | {tc} | "
                     f"{(h.get('shows') or '').replace('|', '/')[:120]} | {tm} | {fr} | `{h['shared_path']}` |")
        L.append("")
    others = [r for r in out["scenes"] if r["role"] != "broll"]
    if others:
        L += ["## Not footage scenes", "",
              ", ".join(f"{r['scene']} ({r['plan']})" for r in others), ""]
    return "\n".join(L)


# ------------------------------------------------------------ an older run's storyboard

def run(folder: Path, gate_: bool = False, brand: str = "") -> int:
    board = folder / "storyboard.json"
    if not board.exists():
        sys.exit(f"no storyboard in {folder}")
    b = json.loads(board.read_text())
    brand = brand or b.get("brand") or ""
    owned, need, presenter = [], [], []
    for s in b["scenes"]:
        if s.get("type") in PRESENTER_TYPES:
            s["owned_candidates"] = []
            s["source_plan"] = "presenter"
            s.pop("owned_file", None)
            presenter.append(s)
            continue
        picks = ask({**s, "to_camera": False}, brand)
        (owned if _decide(s, picks) == "cut" else need).append(s)
    board.write_text(json.dumps(b, indent=1))

    print(f"{len(presenter)} scenes are THE PRESENTER — always them, never the library")
    print(f"{len(owned)} inserts can be CUT from footage we own")
    print(f"{len(need)} inserts need GENERATING\n")
    for s in need:
        print(f"  generate · scene {s['n']:2} {s['type']} · "
              f"{(s.get('say') or s.get('happens') or s.get('product') or '')[:64]}")
    saved = len(owned)
    print(f"\n{saved} clips not generated. At roughly 10 credits a clip that is "
          f"~{saved * 10} credits, and they are real footage rather than a model's idea of it.")
    if gate_ and need and not all(s.get("takes") for s in need):
        print("\nGATE: scenes still need generating and have no take. Generate only those.", file=sys.stderr)
        return 1
    return 0


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, nargs="?", help="an older run folder with storyboard.json")
    ap.add_argument("--brief", type=Path, help="a 5-brief.md — writes footage.json + footage.md beside it")
    ap.add_argument("--brand", default="")
    ap.add_argument("--out", type=Path, help="(with --brief) write the ledger here instead of beside the brief")
    ap.add_argument("--gate", action="store_true",
                    help="(storyboard mode) exit non-zero while unmatched scenes have no take")
    a = ap.parse_args(argv)
    if a.brief:
        if not a.brand:
            sys.exit("--brand is required with --brief")
        dest = a.out.expanduser().resolve() if a.out else a.brief.expanduser().resolve().parent
        out = brief_pass(a.brief.expanduser().resolve(), a.brand, out_dir=dest)
        print(f"{a.brief}: {out['broll']} B-roll scene(s) — {out['cut']} cut from our footage, "
              f"{out['generate']} to generate → {dest / 'footage.md'}")
        sys.exit(0)
    if not a.run:
        ap.error("give a run folder or --brief")
    sys.exit(run(a.run.expanduser().resolve(), a.gate, a.brand))


if __name__ == "__main__":
    main()
