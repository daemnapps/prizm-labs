#!/usr/bin/env python3
"""The dry run — the whole plan resolved, and nothing spent.

    python3 run.py <video> --brand <brand> --dry-run
    python3 run.py <video> --brand <brand> --route ai --from 5 --dry-run

It answers, before a single model is called: which prompt file and version
each stage will use, where every variable in it comes from, and what the
prompt asks for that nothing supplies. Anything MISSING makes the command exit
non-zero, so a broken brand file or a stale binding is found here rather than
four paid stages in.

WHAT IT NEVER DOES: call Gemini or claude, open or write a run folder, copy a
video, touch the Drive, rebuild the board. It READS — the chain config, the
prompt files, the brand's files, and (when this label already has a run on
disk) that run's state, so `--from 5 --dry-run` is checked against what the
run really holds.

The same idea as `compose.py plan` (the second door's pre-flight), for the
front door. compose.py is untouched and keeps its own.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C                                            # noqa: E402

# What run.py itself fills while a stage is running (run_stage), by name.
RUN_FILLS = {"source_url", "research", "voiceprint", "story"}
# Filled only on a Variation video run (variation.py hands them in); empty on
# every other run, and the prompts read empty as "not a variation run".
VARIATION_FILLS = {"target_awareness", "branch_sections"}
# What only one kind of stage gets filled (the stage's `role` in the config).
ROLE_FILLS = {
    "page": {"brief_count"},
    "profile": {"profile_spec", "creator_record", "teardown_material",
                "existing_profile", "handle"},
}

OK, LATER, MISSING = "OK", "LATER", "MISSING"


def _existing_state(R, label, video):
    """(run folder, state) for this label when a run is already on disk —
    READ ONLY. A fresh label answers (None, a blank state)."""
    base = R.slug(label or (Path(video).stem if video else "x"))
    d = R.RUNS / C.run_slug(base)
    st = None
    if (d / "run.json").is_file():
        try:
            st = R.load(d)
        except Exception:
            st = None
    if st is None:
        return None, {"stages": {}}
    st.setdefault("stages", {})
    return d, st


def _narrow(plan, route_skip, want_frames, only, start, stop):
    """Narrow the plan the same way run_video() narrows it."""
    if route_skip and not only:
        plan = [s for s in plan if s["key"] not in route_skip]
    if not want_frames and not only:
        plan = [s for s in plan if s["engine"] != "frames"]
    ids = [s["id"] for s in plan]
    if only:
        return [s for s in plan if s["id"] in only]
    if start:
        if start not in ids:
            raise SystemExit(f"--from {start}: no such stage — have {', '.join(ids)}")
        plan = plan[ids.index(start):]
    if stop:
        k = [s["id"] for s in plan]
        if stop not in k:
            raise SystemExit(f"--to {stop}: no such stage — have {', '.join(k)}")
        plan = plan[:k.index(stop) + 1]
    return plan


def resolve(video, label, brand, extras=None, route=None, creator=None,
            only=None, start=None, stop=None, want_frames=True, product=None):
    """-> dict(label, lane, route, video_ok, stages=[{stage, prompt, version,
    engine, vars=[(var, status, origin)], unbound=[names]}], missing=int).

    Pure reading. No model, no run folder, no Drive."""
    import run as R                                           # noqa: E402

    extras = dict(extras or {})
    d, st = _existing_state(R, label, video)
    lane = st.get("triage_lane") or ""
    prod_route = (route or st.get("production_route") or "creator").lower()
    plan = C.stages(brand, st.get("asset_type", ""), prod_route, lane)
    full_ids = {s["key"] for s in plan}
    r = C.route_for(lane) if lane else C.DEFAULT_ROUTE
    sub = r.get("substitute") or {}
    if lane and r["skip"] is None:
        return dict(label=label, lane=lane, route=prod_route, stages=[],
                    missing=0, video_ok=True,
                    note=f"lane {lane} — {r['why']}; the video chain does not run")
    skip = [k for k in (r["skip"] or [])
            if (st["stages"].get(k) or {}).get("status") != "done"]
    plan = _narrow(plan, skip, want_frames, only, start, stop)

    # what the run already holds on disk (a resume), read only
    pack = dict(extras)
    if product:
        pack["product"] = product.lower()
    if d is not None:
        try:
            pack.update(R.outputs_so_far(d, st))
        except Exception:
            pass
    aud = st.get("audience") or {}
    if aud.get("_avatar"):
        pack["avatar"] = aud["_avatar"]
    pack.update(aud)
    # --for-avatar declares the reader up front; 1b then writes for them, so
    # every avatar-shaped path resolves to that person's files.
    if extras.get("declared_avatar") and not pack.get("avatar"):
        pack["avatar"] = extras["declared_avatar"]
    on_disk = {k for k in pack if k.startswith("stage")}
    will_run = set()

    video_ok = bool(video) and Path(video).expanduser().exists()
    out, n_missing = [], 0
    for s in plan:
        rows, unbound = [], []
        ppath = Path(s["prompt"]) if s.get("prompt") else None
        if ppath is None or not ppath.is_file():
            rows.append(("(prompt)", MISSING, "no prompt file found for this stage"))
        role = s.get("role") or "stage"
        for var, src in (s.get("vars") or {}).items():
            status, origin = OK, ""
            try:
                # the brand's own variables/video.md outranks the config's
                # conventional path for any variable it names — mirrored from
                # run_stage(), which checks it before anything else
                rel = R._brand_video_map(brand).get(var)
                if rel and "<avatar>" in rel:
                    who = aud.get("avatar")
                    rel = rel.replace("<avatar>", who) if who else None
                if rel and (C.WS / "brands" / brand / rel).exists():
                    src = f"brands/{brand}/{rel}"
                if var == "creator_profile" and var in (s.get("per_run") or []):
                    prof = None
                    if creator:
                        prof, _ = R.creator_files(brand, creator)
                    if prof:
                        origin = f"her profile — {prof}"
                    elif not creator:
                        origin = "UNASSIGNED — a swipe run is written to no one"
                    else:
                        _, origin = C.resolve_source(src, brand, pack, var=var)
                elif src.startswith("@"):
                    ref = src[1:].split("#")[0].rstrip("*")
                    n = C.DISPLAY_ID.get(ref, ref.replace("stage", ""))
                    if "#pick" in src:
                        origin = "the control hook (no human pick is made)"
                    elif ref in on_disk:
                        origin = f"what stage {n} produced — already on disk"
                    elif ref in will_run:
                        status, origin = LATER, f"from stage {n} (not run)"
                    elif sub.get(ref) in on_disk or sub.get(ref) in will_run:
                        m = sub[ref]
                        status = OK if m in on_disk else LATER
                        origin = (f"stage {n} is skipped on this lane — "
                                  f"{C.DISPLAY_ID.get(m, m.replace('stage', ''))} "
                                  "stands in" + ("" if m in on_disk else " (not run)"))
                    elif src == "@stage6":
                        origin = "NONE — frames not run"
                    elif ref in full_ids:
                        status, origin = MISSING, (
                            f"wants stage {n}, which this plan does not run and "
                            "the run does not hold — widen --from/--only")
                    else:
                        status, origin = MISSING, (
                            f"wants stage {n}, which is not in this chain")
                elif src.startswith("~"):
                    name = src[1:]
                    if name in pack:
                        origin = "supplied by the run"
                    elif name in RUN_FILLS or name in ROLE_FILLS.get(role, ()):
                        origin = "filled by the run when the stage starts"
                    elif name in VARIATION_FILLS:
                        origin = "empty here — filled only on a Variation video run"
                    else:
                        status, origin = MISSING, (
                            f"bound to the run value '{name}', which nothing "
                            "supplies — it would be sent empty")
                elif src.startswith("#"):
                    if src[1:] in pack:
                        origin = "supplied when the run started"
                    else:
                        status, origin = MISSING, (
                            f"'{src[1:]}' is supplied at run time and wasn't given")
                else:
                    # An avatar-shaped row of the brand's map (`<avatar>` in
                    # its path) can only fill once stage 1b has said who the
                    # run speaks to. Before that it is not missing — it is
                    # not decided yet.
                    mapped = C.variable_map(brand).get(var) or ""
                    if "<avatar>" in mapped and not pack.get("avatar") \
                            and "stage1b" in will_run:
                        status, origin = LATER, (
                            f"brands/{brand}/{mapped} — the avatar is picked "
                            "at stage 1b (not run)")
                    else:
                        _, origin = C.resolve_source(src, brand, pack, var=var)
            except Exception as e:
                status, origin = MISSING, str(e).strip("'\"")
            rows.append((var, status, origin))
        if ppath is not None and ppath.is_file() and s["engine"] != "frames":
            asks = set(re.findall(r"\{([a-z0-9_]+)\}", ppath.read_text()))
            unbound = sorted(asks - set(s.get("vars") or {}))
        n_missing += sum(1 for _, stt, _ in rows if stt == MISSING) + len(unbound)
        will_run.add(s["key"])
        out.append(dict(stage=s, prompt=ppath.name if ppath else None,
                        version=s.get("version"), engine=s["engine"],
                        vars=rows, unbound=unbound))
    if not video_ok:
        n_missing += 1
    return dict(label=label, lane=lane, route=prod_route, stages=out,
                missing=n_missing, video_ok=video_ok, video=str(video or ""),
                resumed=str(d) if d is not None else "")


def show(res, brand, say=print):
    say(f"\n▷ DRY RUN  {res['label']}  ({brand})"
        + (f"  ·  {res['lane']}" if res.get("lane") else "")
        + f"  ·  via {res['route']}  ·  nothing is sent, nothing is written")
    if res.get("note"):
        say("  " + res["note"])
    say("  video:   " + ("OK       " if res["video_ok"] else "MISSING  ")
        + (res.get("video") or "(none given)"))
    if res.get("resumed"):
        say(f"  resumes: {res['resumed']} (read only)")
    for row in res["stages"]:
        s = row["stage"]
        bad = sum(1 for _, stt, _ in row["vars"] if stt == MISSING) + len(row["unbound"])
        say(f"\n  {s['id']:<3} {s['name']:<11} {row['prompt'] or '— NO PROMPT —'}"
            f"  v{row['version']}  [{row['engine']}]"
            + ("" if not bad else f"   ← {bad} missing"))
        for var, status, origin in row["vars"]:
            origin = " ".join(str(origin).split())
            say(f"        {status:<8} {{{var}}}  ←  {origin[:150]}")
        for name in row["unbound"]:
            say(f"        {MISSING:<8} {{{name}}}  ←  the prompt asks for it and "
                "nothing supplies it")
    n = res["missing"]
    say(f"\n  {len(res['stages'])} stage(s) checked · "
        + ("everything resolves — 0 model calls made" if not n else
           f"{n} MISSING — fix these before a real run · 0 model calls made"))
    return n
