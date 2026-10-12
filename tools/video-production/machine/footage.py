#!/usr/bin/env python3
"""
footage.py — ask the library before you pay a model. A gate, not a button.

    python3 machine/footage.py --brief <5-brief.md> --brand <brand>   # the ledger beside the brief
    python3 machine/footage.py <run> [--brand <brand>] [--gate]       # an older run's storyboard.json

and, since 2026-10-05, automatically: `run.py start` runs `gate()` on the
plan's scenes BEFORE any still or clip is made (`--dry-run` included).

**Our own footage first** (the owner, 2026-10-05: "we need to make sure that the
footage step properly runs … whatever needs to be generated, we can just
generate"). Every B-roll scene is looked up in the brand's indexed footage —
the clips on the company Shared Assets drive. A scene with a confident match is
CUT from that clip (`owned_file` + `owned_in`/`owned_out`) and is not
generated. A scene with no confident match is generated, and carries its
nearest real clip's frame as a visual reference, so the model is shown what our
real footage of that thing looks like.

**Brand B owns 1,349 indexed clips (1,347 found on Shared Assets, 2026-10-06).** On 2026-09-11 an entire ad was
generated — thirty-three clips, about 330 credits — without the index being
asked once. Twenty-six of those thirty-three had owned footage sitting in it.
The right number was seven.

The search is local: `tools/asset-index/machine/search.py` reads the
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

# A scene is CUT from our footage at or above this score (0..1: how much of
# what the scene shows, weighted by how rare each word is, the clip's scene
# also shows — plus a quarter for the words said over it). Below it the scene
# is generated, with the best clip as its picture reference. Overridable per
# run (FOOTAGE_CONFIDENT) while the owner judges the first cuts.
CONFIDENT = float(os.environ.get("FOOTAGE_CONFIDENT", "0.42"))
# ...and only when the clip does the ACTION, not just shares the frame's
# furniture: at least this share of the action's words (rarity-weighted) are in
# the clip's scene, and the action has at least ACTION_WORDS words to judge by —
# "holds still, looking at the lens" is a face, not a shot the library can stand in for.
ACTION_MATCH = 0.4
ACTION_WORDS = 2
# A candidate below this is not shown at all — it is noise, not a reference.
FLOOR = 0.12

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
    """Named things the shot shows — a product (the device™, PRIME™), written in
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


def ask(s: dict, brand: str = "", per: int = 3, cast_names=(), work=None, maps=None,
        service: bool = True) -> list[dict]:
    """Owned candidates for one scene, best first. Never for the presenter."""
    if role_of(s) != "broll":
        return []
    seen, said = query_for(s)
    if not (seen or said):
        return []
    hits = lib_search.search(seen, said, brand, core=core_of(s), require=required_of(s, cast_names), per=per,
                             drop=names_of(s, cast_names),
                             work=work, maps=maps)
    hits = [h for h in hits if h["score"] >= FLOOR]
    if hits or not service:
        return hits
    # nothing local — the old service, mapped onto Shared Assets or dropped
    out = []
    for p in _service(seen, said, s, per):
        cid = p.get("clip_id") or p.get("id")
        for col in shared_paths.collections_of(brand, work):
            path = shared_paths.shared_path(col, str(cid), maps) if cid else None
            if path:
                out.append({"clip_id": cid, "collection": col.name, "score": float(p.get("score") or 0),
                            "in": p.get("t_start") or p.get("in") or 0, "out": p.get("t_end") or p.get("out"),
                            "shared_path": path, "frame": p.get("frame"), "shows": p.get("visuals") or "",
                            "says": p.get("spoken") or "", "from": "service"})
                break
    return out


def has_index(brand: str, work=None, maps=None) -> bool:
    cols = shared_paths.collections_of(brand, work)
    return any(shared_paths.load_map(c, maps) for c in cols)


# ------------------------------------------------------------ the gate

def confident(h: dict) -> bool:
    """A candidate good enough to CUT in for the shot, not just to show the
    generator: the score, the action itself, and every named product in it."""
    if h.get("score", 0) < CONFIDENT or h.get("missing"):
        return False
    if h.get("action_match") is None:          # the caller gave no action to judge by
        return True
    return h["action_match"] >= ACTION_MATCH and (h.get("action_words") or 0) >= ACTION_WORDS


def _decide(s: dict, picks: list[dict]) -> str:
    s["owned_candidates"] = picks
    for k in ("owned_file", "owned_in", "owned_out", "owned_clip", "owned_frame", "footage_ref"):
        s.pop(k, None)
    top = next((h for h in picks if confident(h)), None)
    if top:
        s["source_plan"] = "cut"
        s["owned_file"] = top["shared_path"]
        s["owned_in"], s["owned_out"] = top["in"], top["out"]
        s["owned_clip"] = top["clip_id"]
        s["owned_frame"] = top.get("frame")
        return "cut"
    s["source_plan"] = "generate"
    top = picks[0] if picks else None
    if top and top.get("frame"):
        # the nearest real clip, shown to the generator as a picture reference
        s["footage_ref"] = {"frame": top["frame"], "clip": top["clip_id"],
                            "file": top["shared_path"], "score": top["score"]}
        ff = _first_frame(s)
        if ff is not None and isinstance(ff.get("refs"), list) and top["frame"] not in ff["refs"]:
            ff["refs"].append(top["frame"])
    return "generate"


def gate(plan: dict, brand: str, *, work=None, maps=None, service: bool = True) -> dict:
    """Run the footage pass over a plan's scenes (and an older plan's cutaways),
    in place. -> {"cut": [...], "generate": [...], "presenter": [...], "other": [...],
    "indexed": bool}."""
    res = {"cut": [], "generate": [], "presenter": [], "other": [], "indexed": has_index(brand, work, maps)}
    cast = plan.get("cast") or {}
    cast_names = tuple(str(n) for n in [*(cast.get("names") or []), cast.get("name"), cast.get("presenter"),
                                        *(cast.get("also") or [])] if n and isinstance(n, str))
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
        res[_decide(s, ask(s, brand, cast_names=cast_names, work=work, maps=maps, service=service))].append(s["id"])
    # an older plan's inserts are its cutaways — same rule, same fields
    for c in plan.get("cutaways") or []:
        if not res["indexed"]:
            res["generate"].append(c["id"])
            continue
        res[_decide(c, ask({**c, "kind": "broll", "to_camera": False}, brand, cast_names=cast_names,
                           work=work, maps=maps, service=service))].append(c["id"])
    return res


def report(res: dict, saved: dict | None = None) -> None:
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
                                                        "frame", "shows", "says")} for h in picks]
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
    (d / "footage.json").write_text(json.dumps(out, indent=1))
    (d / "footage.md").write_text(ledger_md(out))
    return out


def ledger_md(out: dict) -> str:
    L = [f"# Footage — our own clips for this brief",
         "",
         f"{out['broll']} B-roll scene(s): **{out['cut']} cut from our footage**, "
         f"**{out['generate']} to generate**. A match is cut at a score of {out['confident_at']:.2f} or more; "
         "below that the scene is generated with the nearest real clip as its picture reference.",
         ""]
    if not out["indexed"]:
        L += ["No indexed footage for this brand on Shared Assets — every B-roll scene is generated.", ""]
    for r in out["scenes"]:
        if r["role"] != "broll":
            continue
        verdict = "REAL CLIP — cut from our footage" if r["plan"] == "cut" else "GENERATE"
        L += [f"## {r['scene']} — {verdict}", "", f"Shows: {r['shows']}", ""]
        if r.get("said"):
            L += [f"Over it: “{r['said']}”", ""]
        if not r.get("candidates"):
            L += ["No clip of ours comes close.", ""]
            continue
        L += ["| score | clip | time in clip | what it shows | frame | file on Shared Assets |",
              "|---|---|---|---|---|---|"]
        for h in r["candidates"]:
            fr = f"![]({h['frame']})" if h.get("frame") else "—"
            L.append(f"| {h['score']:.2f} | {h['clip_id']} | {h['in']:.1f}–{h['out']:.1f}s | "
                     f"{(h.get('shows') or '').replace('|', '/')[:120]} | {fr} | `{h['shared_path']}` |")
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
