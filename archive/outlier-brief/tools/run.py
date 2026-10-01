#!/usr/bin/env python3
"""outlier-brief — Damon's own idea in, a concept brief for him to approve out.

    python3 tools/run.py <idea file, or "-" for piped text> --brand <brand>
                         [--avatar A] [--sub S] [--angle ID] [--offer KEY]
                         [--awareness LEVEL] [--sophistication STAGE] [--answers TEXT-OR-FILE]
                         [--label L] [--dry-run] [--rerun-from idea1|idea2|idea3|idea4] [--model M]

The second door. There is NO swipe: the input is a few sentences of his idea,
spoken or typed, plus a brand. This command rounds the idea out against what
the brand has on file, reads the awareness level from the marketing doctrine,
writes ONE format-free concept brief, checks it — and STOPS, `awaiting
approval`. Nothing is picked and nothing is handed off here. That is
`tools/approve.py`, and it refuses without his approval on file.

Filed to `runs/outlier-brief/<brand>/<label>/`:

    idea.md                        the idea exactly as given
    idea1--round-out.md            what the idea really is · who it is for · what it promises · questions for him
    idea2--awareness.md            the awareness entry and the sophistication stage, from the doctrine
    idea3--concept-brief.md        the concept brief
    idea4--check.md                the brief checked against the brand's files
    deliverable/concept-brief.md   the brief as he reads it
    run.json · check.json · every prompt as sent

Built on `components/run-kit` (`Chain`). The dry run spends NOTHING: no model
call, and no file outside a temp folder that is removed.

There is no default brand. An avatar, sub-avatar, angle or offer is LOOKED UP
in the brand's own files; one that is not there is refused with the real ones
named. Awareness and sophistication come from the doctrine, never from here.
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
import brand_context as B                                     # noqa: E402
import doctrine_slices as D                                   # noqa: E402
import elements_pick as L                                     # noqa: E402
import gates as G                                             # noqa: E402
import steps as ST                                            # noqa: E402

from run_kit import model as M                                # noqa: E402
from run_kit import prompts as KP                             # noqa: E402
import quality_checks as Q                                    # noqa: E402

NONE = "(none)"


def _text_or_file(value):
    if not value:
        return ""
    try:
        p = Path(value)
        if len(value) < 400 and p.is_file():
            return p.read_text(errors="replace").strip()
    except OSError:
        pass
    return value.strip()


def _pins(a):
    rows = [("avatar", a.avatar), ("sub-avatar", a.sub), ("angle", a.angle), ("offer", a.offer),
            ("awareness level", a.awareness), ("sophistication stage", a.sophistication)]
    said = [f"- {k}: `{v}`" for k, v in rows if v]
    return "\n".join(said) if said else "Nothing was pinned — the round-out proposes who it is for, from the avatars on file."


def _send_back(old, out):
    """What came back last time: his note if he sent the brief back, and what
    the copy gate held. The rewrite is told both."""
    said = []
    r = G.review_of(old)
    if r.get("state") == G.SENT_BACK and r.get("note"):
        said.append(f"Sent back by {r.get('by') or 'the reviewer'}: {r['note']}")
    held = (G.state(out).get("copy") or {})
    if held.get("result") == "HELD":
        said += [f"Held at the copy gate last time: {p}" for p in held.get("problems", [])]
    return "\n".join(f"- {s}" for s in said) if said else NONE


def _chosen(who, read, a):
    rows = [("avatar", who.get("avatar")), ("sub-avatar", who.get("sub")),
            ("awareness entry", read.get("awareness")), ("sophistication stage", read.get("sophistication")),
            ("angle pinned on the run", a.angle), ("offer pinned on the run", a.offer)]
    return "\n".join(f"- {k}: `{v}`" if v else f"- {k}: not set" for k, v in rows)


def deliverable_md(brand, label, idea, who, read, concept, brief, questions):
    head = [f"# Concept brief — `{brand}/{label}`", "",
            "**Status: awaiting your approval.** Nothing is picked or made until you approve it.", "",
            "| | |", "|---|---|",
            f"| **Written for** | `{who.get('avatar')}`" + (f" · sub `{who['sub']}`" if who.get("sub") else "") + " |",
            f"| **Awareness entry** | `{read.get('awareness')}` |",
            f"| **Sophistication** | `{read.get('sophistication')}` |",
            f"| **Frameworks it fits** | {', '.join('`' + f + '`' for f in concept.get('frameworks') or []) or 'none named'} |",
            f"| **Angle** | {'`' + concept['angle'] + '`' if concept.get('angle') else 'none named'} |",
            f"| **Offer** | {'`' + concept['offer'] + '`' if concept.get('offer') else 'none named'} |", "",
            "## Your idea, as you gave it", "", "> " + idea.strip().replace("\n", "\n> "), ""]
    if questions:
        head += ["## Questions for you", "",
                 "The files do not answer these, and the brief did not guess:", "",
                 *[f"{i}. {q}" for i, q in enumerate(questions, 1)], ""]
    return "\n".join(head) + "\n---\n\n" + S.without_block(brief, "CONCEPT", aliases=("CONCEPT DATA",))


def main(argv=None, runner=None, echo=print, piped=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("idea", help='the idea: a .md/.txt file of a few sentences, or "-" to read it piped in')
    ap.add_argument("--brand", required=True, help="REQUIRED — there is no default brand")
    ap.add_argument("--avatar", help="who it is for — a core avatar the brand has on file (default: the round-out proposes one)")
    ap.add_argument("--sub", help="a sub-avatar under that avatar")
    ap.add_argument("--angle", help="an angle id from the brand's strategy/angles.json")
    ap.add_argument("--offer", help="an offer key from the brand's offer bank")
    ap.add_argument("--awareness", help="pin the awareness level (a doctrine id); default: the awareness read decides")
    ap.add_argument("--sophistication", help="pin the sophistication stage (a doctrine id)")
    ap.add_argument("--answers", help="his answers to the round-out's questions — text, or a file of it")
    ap.add_argument("--label", help="the run's label (default: the idea file's name; piped text: idea-<hash>)")
    ap.add_argument("--dry-run", "--dry", dest="dry", action="store_true",
                    help="spend nothing: show the inputs, the model per step and where it would file")
    ap.add_argument("--rerun-from", choices=ST.BRIEF_STEPS)
    ap.add_argument("--model", help="force one model for every step (default: each step's tier)")
    a = ap.parse_args(argv)

    if a.idea == "-":
        idea = (sys.stdin.read() if piped is None else piped) or ""
        shown = "text piped in"
    else:
        f = Path(a.idea)
        idea = f.read_text(errors="replace") if f.is_file() else ""
        shown = P.rel(f)
    idea = re.sub(r"<!--.*?-->", "", idea, flags=re.S).strip()   # a note to people in the file is not the idea
    if a.idea != "-" and not Path(a.idea).is_file():
        echo(f"MISSING: the idea file is not on file: {a.idea}")
        return 1 if a.dry else 2
    answers = _text_or_file(a.answers)
    label = a.label or (f"idea-{G.sha12(idea)[:8]}" if a.idea == "-" else Path(a.idea).stem)
    files_to = P.record_dir(a.brand, label)
    problems = G.input_problems(idea, a.brand, [s for s in ST.STEPS if s["half"] == "brief"], a.avatar, a.sub,
                                a.angle, a.offer, a.awareness, a.sophistication)

    if a.dry:
        echo(f"DRY RUN — outlier-brief · brand {a.brand} · label {label}")
        echo(f"  idea        {shown} · {len(idea.split()):,} words")
        if problems:
            for p in problems:
                echo(f"  MISSING     {p}")
            echo("  nothing was spent and nothing was written.")
            return 1
    else:
        if problems and not (P.BRANDS / a.brand).is_dir():
            for p in problems:                                # never make a run folder for a brand that is not one
                echo(f"MISSING: {p}")
            return 2
        files_to.mkdir(parents=True, exist_ok=True)
        try:
            G.hold("inputs", files_to, problems)
        except Q.Held as e:
            echo(str(e))
            return 2

    pins = {"avatar": a.avatar, "sub": a.sub, "angle": a.angle, "offer": a.offer,
            "awareness": a.awareness, "sophistication": a.sophistication}
    input_sha = G.sha12(json.dumps([idea.strip(), answers, pins], sort_keys=True))
    assignment = {"idea": shown, "idea_words": len(idea.split()), "pinned": pins,
                  "answers_given": bool(answers), "input_sha256_12": input_sha}

    tmp = Path(tempfile.mkdtemp(prefix="outlier-brief-dry-")) if a.dry else None
    out = tmp or files_to
    old = ST.old_state(files_to)
    rerun = a.rerun_from
    if not a.dry and not rerun and (old.get("assignment") or {}).get("input_sha256_12") not in (None, input_sha):
        echo("     the idea, its pins or the answers changed since the last run under this label — starting over")
        rerun = "idea1"
    send_back = _send_back(old, files_to)

    try:
        chain = ST.chain(a.brand, label, out, assignment, a.dry, rerun, a.model, runner, echo, carry=old)
        ctx, not_on_file = B.gather(a.brand, a.avatar, a.sub)
        if a.dry:
            for m in not_on_file:
                echo(f"  not on file {m} — the brief will be told it may not lean on it")
        else:
            (out / "idea.md").write_text(idea.strip() + "\n")
            chain.record.state["not_on_file"] = not_on_file
        doctrine = {v: D.text(v) for v in D.SLICES}

        # 1 — round it out: what the idea really is, who it is for, what it promises, what to ask him
        roundout = chain.run("idea1", idea=idea.strip(), answers=answers or NONE, pinned=_pins(a),
                             position=ctx["position"], story=ctx["story"], offers=ctx["offers"],
                             objections=ctx["objections"], avatar_menu=ctx["avatar_menu"],
                             avatar_card=ctx["avatar_card"], angles=ctx["angles"],
                             customer_language=ctx["customer_language"],
                             desire_dimensions=doctrine["desire_dimensions"])
        who = {"avatar": a.avatar, "sub": a.sub, "questions": []}
        if not a.dry:
            who, bad = G.read_roundout(roundout, a.brand, a.avatar, a.sub)
            chain.record.state["roundout"] = who
            chain.record.save()
            G.hold("inputs", out, bad)
            if (who["avatar"], who["sub"]) != (a.avatar, a.sub):
                ctx, _ = B.gather(a.brand, who["avatar"], who["sub"])      # the chosen reader's own card and words

        # 2 — the awareness read, from the doctrine's own slices
        read = {"awareness": a.awareness, "sophistication": a.sophistication}
        if a.awareness and a.sophistication:
            chain.skip("idea2", "the awareness level and the sophistication stage were both pinned on the run")
            awareness_read = (f"Pinned on the run, not read: awareness `{a.awareness}`, sophistication "
                              f"`{a.sophistication}`. The doctrine's own rows for both are bound below.")
        else:
            awareness_read = chain.run("idea2", idea=idea.strip(), roundout=roundout, pinned=_pins(a),
                                       position=ctx["position"], avatar_card=ctx["avatar_card"],
                                       customer_language=ctx["customer_language"],
                                       awareness_levels=doctrine["awareness_levels"],
                                       sophistication_stages=doctrine["sophistication_stages"])
            if not a.dry:
                got, bad = G.read_awareness(awareness_read)
                read = {k: pins[k] or got[k] for k in ("awareness", "sophistication")}
                G.hold("elements", out, bad)
        if not a.dry:
            chain.record.state["awareness"] = read
            chain.record.save()

        # 3 — the concept brief: format-free, one reader, one awareness entry
        brief = chain.run("idea3", idea=idea.strip(), answers=answers or NONE, roundout=roundout,
                          awareness_read=awareness_read, chosen=_chosen(who, read, a), send_back=send_back,
                          position=ctx["position"], story=ctx["story"], offers=ctx["offers"],
                          objections=ctx["objections"], avatar_card=ctx["avatar_card"], angles=ctx["angles"],
                          customer_language=ctx["customer_language"],
                          desire_dimensions=doctrine["desire_dimensions"],
                          awareness_levels=doctrine["awareness_levels"],
                          sophistication_stages=doctrine["sophistication_stages"],
                          ad_frameworks=doctrine["ad_frameworks"],
                          framework_ids=L.doctrine_ids_line(L.FRAMEWORK))
        concept, code_problems = {"frameworks": [], "angle": None, "offer": None}, []
        if not a.dry:
            concept, bad = G.read_concept(brief)
            concept["angle"] = concept["angle"] or a.angle
            concept["offer"] = concept["offer"] or a.offer
            chain.record.state["concept"] = concept
            chain.record.save()
            G.hold("elements", out, bad + G.brief_element_problems(concept))
            code_problems = G.brief_copy_problems(brief, concept, a.brand)

        # 4 — the check: nothing claimed that the brand's files do not carry, no chopped thought, no typo
        readable = brief if a.dry else S.without_block(brief, "CONCEPT", aliases=("CONCEPT DATA",))
        check = chain.run("idea4", brief=readable, position=ctx["position"], story=ctx["story"],
                          offers=ctx["offers"], objections=ctx["objections"], avatar_card=ctx["avatar_card"],
                          customer_language=ctx["customer_language"])
        if not a.dry:
            G.hold("copy", out, code_problems + G.check_step_problems(check))

            # ---- THE REVIEW STOP ----
            sha = G.sha12((out / "idea3--concept-brief.md").read_text())
            review = G.review_of(chain.record.state)
            if not (review.get("state") == G.APPROVED and review.get("brief_sha256_12") == sha):
                history = list(review.get("history") or [])
                if review.get("state") in (G.APPROVED, G.SENT_BACK):
                    history.append({k: review.get(k) for k in ("state", "by", "at", "note", "brief_sha256_12")})
                review = {"state": G.AWAITING, "brief_sha256_12": sha, "history": history}
            chain.record.state["review"] = review
            chain.record.state["state"] = ("awaiting approval" if review["state"] == G.AWAITING
                                           else chain.record.state.get("state") or "approved")
            (out / "deliverable").mkdir(exist_ok=True)
            (out / "deliverable" / "concept-brief.md").write_text(
                deliverable_md(a.brand, label, idea, who, read, concept, brief, who.get("questions") or []))
            chain.record.save()
    except Q.Held as e:
        if not a.dry:
            chain.record.state["state"] = f"held at the {e.gate} gate"
            chain.record.save()
        echo(str(e))
        echo(f"  the run is HELD — why is in {P.rel(out / 'check.json')}. Fix the input or the prompt (as a new "
             f"-vN- file), then run again with --rerun-from <step>.")
        return 2
    except (KP.PromptError, M.UsageLimit, M.StageFailed) as e:
        echo(f"STOPPED: {e}")
        return 3
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    if a.dry:
        echo(f"  would file  {P.rel(files_to)}/  (idea.md · the four step outputs · deliverable/concept-brief.md · "
             f"run.json · check.json · every prompt as sent)")
        echo(f"  then        STOPS, awaiting approval — formats and hand-offs are tools/approve.py")
        echo(f"  spent       0 model calls — a real run makes up to {len(ST.BRIEF_STEPS)}")
        return 0

    echo(f"done -> {P.rel(out)}  ({chain.calls} model call(s))")
    echo(f"  the brief   {P.rel(out / 'deliverable' / 'concept-brief.md')}")
    for i, q in enumerate(who.get("questions") or [], 1):
        echo(f"  question {i}  {q}")
    if chain.record.state["review"]["state"] == G.AWAITING:
        echo("  STATUS      awaiting approval — nothing is picked or handed off until the brief is approved:")
        echo(f"              python3 {P.rel(HERE / 'approve.py')} {label} --brand {a.brand}")
    else:
        echo("  STATUS      this exact brief is already approved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
