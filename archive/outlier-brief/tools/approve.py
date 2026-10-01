#!/usr/bin/env python3
"""outlier-brief, the second half — record Damon's verdict on a concept brief,
and only then pick its formats and write the hand-offs.

    python3 tools/approve.py <label> --brand <brand> [--note "..."] [--by NAME]
                             [--media video,image,copy,page,email] [--formats video:<id>[+<style id>],…]
                             [--route ai|creator|founder] [--product P]
                             [--send-back] [--hand-off-only] [--dry-run] [--rerun-from hand1] [--model M]

THE REVIEW STOP. `tools/run.py` ends `awaiting approval`. This command is the
only thing that moves a run past it:

    approve        records who / when / note and the sha of the brief that was
                   approved, in run.json → review.state `approved`
    --send-back    records the note → review.state `sent back`; nothing else
                   runs. `run.py … --rerun-from idea3` rewrites the brief and
                   is told the note.

After an approval it runs the later steps, and they REFUSE without one on file
(or if the brief changed after it was approved):

    hand1          pick the formats — ONLY from the element library's lists for
                   the media asked for (default: video). A row still saying
                   `[TO DEFINE` may be named as a candidate; it is flagged
                   "named, not defined yet" and not handed off. An unknown id
                   is refused with the real ids named. `--formats` is his own
                   pick: no model call, checked exactly as hard.
    hand-offs      written by code under deliverable/ — the approved brief word
                   for word plus the picked rows. NOTHING IS STARTED: the exact
                   command for each chain is printed and filed.

`--hand-off-only` records no new verdict — it runs the later steps against the
approval already on file (another medium, a different pick).
The dry run spends nothing and writes nothing, the approval included.
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
import paths as P                                             # noqa: E402
import slots as S                                             # noqa: E402
import elements_pick as L                                     # noqa: E402
import gates as G                                             # noqa: E402
import handoff as H                                           # noqa: E402
import steps as ST                                            # noqa: E402

from run_kit import model as M                                # noqa: E402
from run_kit import prompts as KP                             # noqa: E402
from run_kit.record import now                                # noqa: E402
import quality_checks as Q                                    # noqa: E402

BRIEF_FILE = "idea3--concept-brief.md"


def stamp(run, status):
    """The brief he reads carries its own status line — keep it true."""
    f = Path(run) / "deliverable" / "concept-brief.md"
    if f.is_file():
        f.write_text(re.sub(r"^\*\*Status:.*$", f"**Status: {status}**", f.read_text(), count=1, flags=re.M))


def _chosen(state):
    who, read, concept = state.get("roundout") or {}, state.get("awareness") or {}, state.get("concept") or {}
    rows = [("avatar", who.get("avatar")), ("sub-avatar", who.get("sub")),
            ("awareness entry", read.get("awareness")), ("sophistication stage", read.get("sophistication")),
            ("frameworks the brief says it fits", ", ".join(concept.get("frameworks") or []) or None),
            ("angle", concept.get("angle")), ("offer", concept.get("offer"))]
    return "\n".join(f"- {k}: `{v}`" if v else f"- {k}: not set" for k, v in rows)


def hand_off(chain, out, brand, label, brief_text, media, formats_flag=None, route=None, product=None, echo=print):
    """The later steps. Refuses — `G.NotApproved` — unless the brief on file is approved."""
    state = chain.record.state
    review = G.require_approval(state, brief_text)             # ← the stop. Nothing below runs without it.
    concept = state.get("concept") or {}
    readable = S.without_block(brief_text, "CONCEPT", aliases=("CONCEPT DATA",))

    if formats_flag:
        chain.skip("hand1", "the formats were picked by hand at approval (--formats) — no model was asked")
        record, problems = L.validate(L.from_flag(formats_flag), media, concept.get("frameworks") or ())
        record["problems"] = problems
        if chain.dry:
            for p in problems:
                echo(f"  WOULD HOLD  {p}")
    else:
        answer = chain.run("hand1", brief=readable, chosen=_chosen(state), media=", ".join(media),
                           candidates=L.candidates(media))
        if chain.dry:
            return None
        record, problems = L.read(answer, media, concept.get("frameworks") or ())
    if chain.dry:
        return None
    record.update(media=media, brief_sha256_12=review["brief_sha256_12"], picked_by="hand" if formats_flag else "hand1")
    (out / "formats.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    state["formats"] = record
    chain.record.save()
    G.hold("elements", out, problems)

    ctx = {"brand": brand, "label": label, "avatar": (state.get("roundout") or {}).get("avatar"),
           "sub": (state.get("roundout") or {}).get("sub"),
           "awareness": (state.get("awareness") or {}).get("awareness"),
           "sophistication": (state.get("awareness") or {}).get("sophistication"),
           "angle": concept.get("angle"), "offer": concept.get("offer"), "route": route, "product": product,
           "approved_by": review.get("by"), "approved_at": review.get("at"), "brief_sha": review["brief_sha256_12"]}
    done = H.write(out / "deliverable", ctx, record["picks"], readable)
    state["handoffs"] = done
    state["state"] = "handed off" if any(d["handed_off"] for d in done) else "approved — nothing could be handed off"
    chain.record.save()
    return record, done


def main(argv=None, runner=None, echo=print):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("label", help="the run's label, as tools/run.py filed it")
    ap.add_argument("--brand", required=True, help="REQUIRED — there is no default brand")
    ap.add_argument("--note", default="", help="what he said about it")
    ap.add_argument("--by", default="Damon", help="who approved (default: the owner)")
    ap.add_argument("--send-back", action="store_true", help="record `sent back` with the note; run nothing else")
    ap.add_argument("--hand-off-only", action="store_true",
                    help="record no new verdict; run the later steps against the approval already on file")
    ap.add_argument("--media", default=None, help="comma-separated: video, image, copy, page, email (default: video)")
    ap.add_argument("--formats", help="his own picks: <medium>:<format id>[+<style id>],… — no model call")
    ap.add_argument("--route", choices=list(H.VIDEO_ROUTES), help="how the video gets produced (default: creator)")
    ap.add_argument("--product", help="which of the brand's products, when it has more than one")
    ap.add_argument("--dry-run", "--dry", dest="dry", action="store_true",
                    help="spend nothing, write nothing — the approval is not recorded either")
    ap.add_argument("--rerun-from", choices=ST.HANDOFF_STEPS)
    ap.add_argument("--model", help="force one model for the pick step (default: its tier)")
    a = ap.parse_args(argv)

    run = P.record_dir(a.brand, a.label)
    old = ST.old_state(run)
    problems = []
    if not (P.BRANDS / a.brand).is_dir():
        problems.append(f"`{a.brand}` is not a brand folder under brands/ — known: {', '.join(P.known_brands())}")
    elif not (run / BRIEF_FILE).is_file() or not old:
        problems.append(f"there is no concept brief under {P.rel(run)} — run tools/run.py first")
    elif str(old.get("state") or "").startswith("held") or "review" not in old:
        problems.append(f"this run never reached the review stop ({old.get('state') or 'it stopped early'}) — "
                        f"a held brief cannot be approved; see {P.rel(run / 'check.json')}")
    try:
        pinned = L.from_flag(a.formats) if a.formats else {}
        media = L.check_media([m.strip() for m in a.media.split(",") if m.strip()] if a.media
                              else (list(pinned) or ["video"]))
        if pinned and set(pinned) - set(media):
            problems.append("--formats names a medium that --media does not: " + ", ".join(sorted(set(pinned) - set(media))))
        if pinned and set(media) - set(pinned):
            problems.append("--formats must pick for every medium asked for — missing: " + ", ".join(sorted(set(media) - set(pinned))))
    except ValueError as e:
        problems.append(str(e))
        media = []
    if not a.formats and not a.send_back:
        try:
            KP.latest(P.PROMPTS, "hand1")
        except KP.PromptError as e:
            problems.append(str(e))
    problems += L.missing_lists(media) if media else []
    if problems:
        for p in problems:
            echo(("  MISSING     " if a.dry else "MISSING: ") + p)
        if a.dry:
            echo("  nothing was spent and nothing was written.")
        return 1 if a.dry else 2

    brief_text = (run / BRIEF_FILE).read_text()
    sha = G.sha12(brief_text)
    review = G.review_of(old)

    if a.dry:
        echo(f"DRY RUN — outlier-brief approval · brand {a.brand} · label {a.label}")
        echo(f"  review now  {review.get('state')}")
        echo("  would       " + ("record `sent back` and stop" if a.send_back else
                                 "run the later steps against the approval on file" if a.hand_off_only else
                                 f"record `approved` by {a.by} for brief {sha}"))
    elif a.send_back:
        history = list(review.get("history") or [])
        if review.get("state") in (G.APPROVED, G.SENT_BACK):
            history.append({k: review.get(k) for k in ("state", "by", "at", "note", "brief_sha256_12")})
        old["review"] = {"state": G.SENT_BACK, "by": a.by, "at": now(), "note": a.note, "brief_sha256_12": sha,
                         "history": history}
        old["state"] = "sent back"
        (run / "run.json").write_text(json.dumps(old, indent=2, ensure_ascii=False) + "\n")
        stamp(run, f"sent back by {a.by}, {old['review']['at'][:10]}." + (f" “{a.note}”" if a.note else ""))
        echo(f"sent back -> {P.rel(run)}  (0 model calls)")
        echo(f"  rewrite it  python3 {P.rel(HERE / 'run.py')} {(old.get('assignment') or {}).get('idea', '<idea file>')} "
             f"--brand {a.brand} --label {a.label} --rerun-from idea3")
        return 0
    if a.dry and a.send_back:
        echo("  spent       0 model calls · nothing was written")
        return 0

    tmp = Path(tempfile.mkdtemp(prefix="outlier-brief-dry-")) if a.dry else None
    out = tmp or run
    try:
        if not a.dry and not a.hand_off_only:
            # he may have edited the brief before approving it — the code checks run again, free
            concept, bad = G.read_concept(brief_text)
            concept["angle"] = concept["angle"] or (old.get("concept") or {}).get("angle")
            concept["offer"] = concept["offer"] or (old.get("concept") or {}).get("offer")
            G.hold("elements", run, bad + G.brief_element_problems(concept))
            G.hold("copy", run, G.brief_copy_problems(brief_text, concept, a.brand))
            history = list(review.get("history") or [])
            if review.get("state") in (G.APPROVED, G.SENT_BACK):
                history.append({k: review.get(k) for k in ("state", "by", "at", "note", "brief_sha256_12")})
            old["concept"] = concept
            old["review"] = {"state": G.APPROVED, "by": a.by, "at": now(), "note": a.note,
                             "brief_sha256_12": sha, "history": history}
            old["state"] = "approved"
            (run / "run.json").write_text(json.dumps(old, indent=2, ensure_ascii=False) + "\n")
            stamp(run, f"approved by {a.by}, {old['review']['at'][:10]}." + (f" “{a.note}”" if a.note else ""))
            echo(f"approved -> {P.rel(run)}  by {a.by}" + (f" — “{a.note}”" if a.note else ""))

        rerun = a.rerun_from
        prev = old.get("formats") or {}
        if not rerun and prev and (prev.get("brief_sha256_12") != sha or prev.get("media") != media):
            rerun = "hand1"                                    # a different brief or different media: pick again
        carry = dict(old)
        if a.dry and not a.hand_off_only and not a.send_back:
            carry["review"] = {"state": G.APPROVED, "by": a.by, "at": "dry", "brief_sha256_12": sha}
        chain = ST.chain(a.brand, a.label, out, old.get("assignment"), a.dry, rerun, a.model, runner, echo, carry=carry)
        if a.dry:                                              # run-kit's record reads steps from `out`; show the real ones
            chain.record.state["stages"].update(old.get("stages") or {})
        got = hand_off(chain, out, a.brand, a.label, brief_text, media, a.formats, a.route, a.product, echo)
    except G.NotApproved as e:
        echo(f"REFUSED: {e}")
        return 2
    except Q.Held as e:
        echo(str(e))
        echo(f"  HELD — why is in {P.rel(run / 'check.json')}.")
        return 2
    except (KP.PromptError, M.UsageLimit, M.StageFailed) as e:
        echo(f"STOPPED: {e}")
        return 3
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    if a.dry:
        echo(f"  media       {', '.join(media)}" + (" — picked by hand, no model" if a.formats else ""))
        echo(f"  would file  {P.rel(run)}/formats.json · deliverable/handoff--<medium>.md (+ handoff--video.json)")
        echo(f"  spent       0 model calls — a real approval makes {'0' if a.formats else 'up to 1'}; nothing was written")
        return 0

    record, done = got
    echo(f"done -> {P.rel(run)}  ({chain.calls} model call(s))")
    for f in record["flagged"]:
        echo(f"  FLAGGED     {f['list']} `{f['id']}` — {f['flag']}; named as a candidate, not handed off")
    for d in done:
        if not d["handed_off"]:
            echo(f"  {d['medium']:<11} no hand-off — {d['held_back']}")
            continue
        echo(f"  {d['medium']:<11} {', '.join(P.rel(run / 'deliverable' / f) for f in d['files'])}")
        echo(f"              {'ready' if d['chain_ready'] else 'NOT READY'} — {d['chain_state']}")
        echo(f"              nothing was started. The command:  {d['command']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
