#!/usr/bin/env python3
"""Produce every email a month's board calls for — the chain, then the
brand-skinned mockup, for every slot and every variant inside it.

    python3 run_month.py ../../runs/marketing-calendar/<brand>/2026-09 [--limit N] [--only sep-01,sep-02]

Reuses brief.py's variant_runs/chain_argv so a slot with three avatars in it
produces three real emails, each carrying the angle the cells stage picked —
never the composer's flattened "mixed" guess. Runs with bounded concurrency
so this doesn't try to open sixty Claude subprocesses at once; logs to
production.log inside the run folder so progress survives if this is
watched rather than waited on.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from paths import HERE, WORKSPACE, calendar_tool
import brief
import ep_keys

sys.path.insert(0, str(HERE / "machine"))
import email_elements as EE          # asks components/elements: is this type a real one?   # noqa: E402

CONCURRENCY = 4


def log(f, msg):
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)
    f.write(line + "\n")
    f.flush()


PUSH = False
NO_IMAGES = False


def have_picture_key():
    """The pictures need OPENAI_API_KEY, asked of the one key loader through
    ep_keys: the environment first, then ~/.upright-keys.env (the one key
    file); the
    picture door, direct_openai.key_of(), reads through the same loader.
    Without it the email is laid out with no pictures and the log SAYS so,
    instead of the whole build dying at its first picture (2026-09-23,
    the team: "do sat 3 w/o images"). The moment a key is on the machine,
    pictures come back — no switch to flip. Never raises."""
    return ep_keys.key("OPENAI_API_KEY") is not None


def one_run(label, argv, brand, logf):
    t0 = time.time()
    log(logf, f"start {label}  (writing)")
    r = subprocess.run(argv, cwd=HERE, capture_output=True, text=True)
    try:                                   # how this email was written, so a refinement can replay it
        (WORKSPACE / "runs" / "email-production" / brand / label / "copy-argv.json").write_text(json.dumps(argv[1:], indent=1))
    except OSError:
        pass
    if r.returncode:
        # stdout too: `email.py` reports a usage limit or a refused offer there
        return label, "chain-fail", (r.stderr + r.stdout)[-800:], round(time.time() - t0, 1)
    # THE SIMPLE EMAIL (the owner, 2026-09-19): logo, headline, one picture, the
    # copy, an optional offer picture, one button — pictures by GPT, and with
    # --push a Klaviyo DRAFT. Replaces the designed-template step.
    build = [sys.executable, "simple_email.py",
             str(WORKSPACE / "runs" / "email-production" / brand / label), "--brand", brand]
    if PUSH:
        build.append("--push")
    pics = not NO_IMAGES and have_picture_key()
    if not pics:
        build.append("--no-images")
    log(logf, f"      {label}  written in {round(time.time() - t0, 1)}s — "
              + ("pictures and layout" if pics else
                 "layout only, NO PICTURES: words-only run" if NO_IMAGES else
                 "layout only, NO PICTURES: no OPENAI_API_KEY on this machine")
              + (" and the Klaviyo draft" if PUSH else ""))
    t_build = time.time()
    render = subprocess.run(build, cwd=HERE, capture_output=True, text=True)
    status, detail = "done", (render.stdout.strip().splitlines() or [""])[-1]
    if render.returncode:
        out = render.stderr + render.stdout
        if not held_now(out, brand, label, t_build):
            return label, "build-fail", out[-800:], round(time.time() - t0, 1)
        status, detail = "held", out[out.index(HELD):][-800:]
    # THE DESIGN (the owner, 2026-10-17: "the team can go ahead and trigger the emails … even then, the design should
    # already be there"): a brand with a look file gets its email designed, pictured, built for Klaviyo and put on
    # the approval page in the same run. the team refines from there. A held copy is still designed, its card says why.
    if DESIGN and (WORKSPACE / "brands" / brand / "email-sms" / "design-system.json").exists():
        run = WORKSPACE / "runs" / "email-production" / brand / label
        # the design step MAKES pictures only when the build may (LD-21 (no mini picture-making)): the same `pics`
        # as above, so a words-only run or a machine with no key — the mini — leaves its picture slots `todo`
        design = [sys.executable, "design/line.py", brand, "--run", str(run)]
        if pics:
            design.append("--pictures")
        d = subprocess.run(design, cwd=HERE, capture_output=True, text=True)
        # the system fills its own gaps before any person sees the email (the owner, 2026-10-18): prices from the offer
        # bank, unmade pictures, missing words by a redesign naming them; what it can't fill stays a plain question
        g = subprocess.run([sys.executable, "design/gaps.py", str(run), "--fill"], cwd=HERE, capture_output=True, text=True) \
            if (run / "design" / "email.json").exists() else None
        if g is not None:
            log(logf, "      %s  gaps: %s" % (label, ((g.stdout or "").strip().splitlines() or ["none"])[0]))
        b = subprocess.run([sys.executable, "design/build.py", str(run)], cwd=HERE, capture_output=True, text=True) \
            if (run / "design" / "email.json").exists() else None
        log(logf, f"      {label}  designed"
                  + (", pictures asked of the image engine" if pics else
                     ", no pictures made (slots left todo): words-only run" if NO_IMAGES else
                     ", no pictures made (slots left todo): no OPENAI_API_KEY on this machine")
                  + ("" if d.returncode == 0 else " (design step failed: %s)" % why(d, run / "design" / "design-step.err"))
                  + ("" if b is None or b.returncode == 0 else " (Klaviyo build failed: %s)" % why(b, run / "klaviyo" / "build-step.err")))
    return label, status, detail, round(time.time() - t0, 1)


def why(proc, err_file=None):
    """The one line that says why a step failed (LD-23 (step failure says why)): its stderr (else stdout) with the
    warning noise dropped — a line naming "Warning:" or "warnings.warn(" and the indented lines under it, e.g.
    google-auth's Python 3.9 FutureWarning — then the last traceback's own error line ("KeyError: 'hero'"), else
    the last line left, else the last warning line; never empty, cut at 300. The whole text goes to `err_file` in
    the run folder first, so the lab-run mirror carries it."""
    text = proc.stderr or proc.stdout or ""
    if err_file is not None:
        try:
            err_file.parent.mkdir(parents=True, exist_ok=True)
            err_file.write_text(text)
        except OSError:
            pass
    kept, in_warning = [], False
    for line in text.splitlines():
        if "Warning:" in line or "warnings.warn(" in line:
            in_warning = True
        elif not (in_warning and line[:1] in (" ", "\t")):
            in_warning = False
            kept.append(line)
    tb = max((i for i, line in enumerate(kept) if line.startswith("Traceback (most recent call last)")), default=None)
    error = next((line for line in kept[tb + 1:] if line.strip() and line[:1] not in (" ", "\t")), None) \
        if tb is not None else None
    lines = text.splitlines()
    error = error or next((line for line in reversed(kept) if line.strip()), None) \
        or next((line for line in reversed(lines) if "Warning:" in line), None) \
        or next((line for line in reversed(lines) if line.strip()), "") \
        or "exit %s, no output" % proc.returncode
    return error.strip()[:300]


HELD = "HELD — not sent to Klaviyo"
DESIGN = True


def held_now(output, brand, label, since):
    """A build that stopped at the delivery gate is HELD — waiting on a person's
    ruling — not failed (HE-2 (held not failed), 2026-10-01). All three must
    agree: the build said so, its check.json says HELD, and that check.json was
    written by THIS build — a stale HELD from an earlier run never relabels a crash."""
    if HELD not in (output or ""):
        return False
    cj = WORKSPACE / "runs" / "email-production" / brand / label / "deliverable" / "check.json"
    try:
        fresh = cj.stat().st_mtime >= int(since)        # whole seconds: a coarse filesystem clock
        result = (json.loads(cj.read_text()).get("delivery") or {}).get("result")
    except (OSError, ValueError, AttributeError):
        return False
    return fresh and result == "HELD"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--limit", type=int, default=None,
                    help="produce only the first N runs — a pilot batch")
    ap.add_argument("--only", default=None,
                    help="comma-separated slot ids — produce only these")
    # ONE AVATAR PER BRAND (the owner, 2026-09-15: "don't worry about different
    # avatars at this stage"). A slot targeting three avatars produces three
    # emails, which is right when the month ships and wrong while the writing
    # itself is being judged — three versions of one send tell you nothing
    # extra about whether the copy is good, and cost three times as much to
    # find out. A send with NO avatar (an affiliate feature, a sitewide note)
    # is not a second avatar and is kept: omitting the avatar is a declaration
    # the chain is told about, not a gap.
    ap.add_argument("--avatar", default=None,
                    help="produce only this avatar's version of each send "
                         "(plus sends that carry no avatar at all)")
    ap.add_argument("--rerun-from", default=None, metavar="STAGE",
                    help="rewrite every send from this stage on, keeping the steps "
                         "before it. What a step was HANDED can change without its "
                         "prompt changing — a new rule, a new brand file — and the "
                         "chain only reruns on a changed prompt, so that case is "
                         "named here (2026-09-21).")
    ap.add_argument("--concurrency", type=int, default=CONCURRENCY)
    ap.add_argument("--push", action="store_true",
                    help="put each finished email into Klaviyo as a DRAFT")
    ap.add_argument("--from-date", default=None, metavar="YYYY-MM-DD",
                    help="skip sends dated before this day — a send whose day "
                         "has passed is not written")
    # words and layout only, whatever key is on the machine — the mini's door
    # (lab_entry.py) always passes it: pictures are made on the team's Mac
    # (EP-1 (email writer mini door), the team "pictures on stephs mac", 2026-09-29)
    ap.add_argument("--no-design", action="store_true",
                    help="stop at the copy: do not design, picture or build the email (the default designs it)")
    ap.add_argument("--no-images", action="store_true",
                    help="lay out each email with no pictures, even when a picture key is present")
    args = ap.parse_args()
    global PUSH, NO_IMAGES, DESIGN
    PUSH = args.push
    DESIGN = not args.no_design
    NO_IMAGES = args.no_images

    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = HERE / run_dir
    slots = json.loads((run_dir / "slots.json").read_text())
    run = json.loads((run_dir / "run.json").read_text())
    brand = run["brand"]

    # A month is planned by the calendar and then CORRECTED by a person on its
    # review board. Read the merged view, never raw slots.json: reading the
    # plan alone would write the send the planner first proposed instead of the
    # one the reviewer approved, and silently throw away every rewrite
    # (marketing-calendar CONTRACT.md, 2026-09-13). A slot the reviewer cut is
    # not produced at all. An unreadable review stops the month (SI-151
    # (picked subject gated), email-production#11): "the plan as written" is
    # exactly the send the reviewer may have corrected or cut.
    try:
        import reviewed_plan as RP                              # machine/, on the path above
        reviewed = RP.reviewed(run_dir, slots)
    except Exception as e:                                      # noqa: BLE001
        sys.exit(f"review layer unreadable ({type(e).__name__}: {e}) — nothing produced; "
                 "fix review.json or the review module, then rerun")
    kept = {s["id"] for s in reviewed}
    cut = [s["id"] for s in slots if s["id"] not in kept]
    slots = reviewed
    notes = {s["id"]: s["_review"]["note"] for s in slots if s["_review"]["note"]}
    edited = sum(1 for s in slots if s["_review"]["edits"])
    if cut or notes or edited:
        print(f"review: {edited} slot(s) rewritten, {len(notes)} note(s), "
              f"{len(cut)} cut" + (f" ({', '.join(cut)})" if cut else ""))

    only = set(args.only.split(",")) if args.only else None
    jobs = []
    skipped = []
    blocked = []
    # a month at runs/marketing-calendar/<brand>/<YYYY-MM>/ (or a legacy
    # calendar-YYYY-MM-<brand> folder): its runs get a <brand>- prefix
    prefix = brief.label_prefix(run_dir, brand)
    for slot in slots:
        if only and slot["id"] not in only:
            continue
        if args.from_date and (slot.get("date") or "") < args.from_date:
            continue
        # an email type nobody has defined is not written (the elements gate)
        why = EE.type_problem(brand, slot.get("type"))
        if why:
            blocked.append((slot["id"], why))
            continue
        for av, angle, label in brief.variant_runs(slot, brand):
            if args.avatar and av not in (args.avatar, None, "none", "mixed"):
                continue
            if prefix and not label.startswith(prefix):
                label = prefix + label           # results/<brand>-sep-01… when the month folder carries a brand suffix
            argv = brief.chain_argv(slot, brand, av, angle, label,
                                    note=notes.get(slot["id"]))
            if argv is None:
                skipped.append(label)
                continue
            if args.rerun_from:
                argv = argv + ["--rerun-from", args.rerun_from]
            jobs.append((label, argv))
    if args.limit:
        jobs = jobs[:args.limit]

    logf = (run_dir / "production.log").open("a")
    log(logf, f"=== production run: {len(jobs)} email(s) to build "
              f"({len(skipped)} skipped — no source), concurrency {args.concurrency} ===")
    if skipped:
        log(logf, "skipped (no source fits): " + ", ".join(skipped))
    for sid, why in blocked:
        log(logf, f"BLOCKED {sid} — {why[:200]}")

    code = produce(jobs, brand, logf, args.concurrency, skipped)
    # the final check spans the batch (no picture or concept repeated across it): run once, over every email built
    if DESIGN:
        built = [str(WORKSPACE / "runs" / "email-production" / brand / lab) for lab, _ in jobs
                 if (WORKSPACE / "runs" / "email-production" / brand / lab / "klaviyo" / "card.json").exists()]
        if built:
            c = subprocess.run([sys.executable, "design/check.py"] + built, cwd=HERE, capture_output=True, text=True)
            log(logf, "final check:\n      " + (c.stdout or c.stderr).strip().replace("\n", "\n      "))
    logf.close()
    sys.exit(code)


def produce(jobs, brand, logf, concurrency, skipped=()):
    """Build every job; 1 only when an email FAILED. An email held at the
    delivery gate waits on a person's ruling and is not a failed run (HE-2
    (held not failed), 2026-10-01) — the worker reads exit 0 as `done`."""
    built, held, failed = [], [], []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {ex.submit(one_run, label, argv, brand, logf): label
                   for label, argv in jobs}
        for fut in as_completed(futures):
            label, status, detail, seconds = fut.result()
            if status == "done":
                built.append(label)
                log(logf, f"OK    {label}  ({seconds}s)  {detail}")
            elif status == "held":
                held.append(label)
                log(logf, f"HELD  {label}  ({seconds}s)")
                log(logf, "      " + detail.replace("\n", "\n      "))
            else:
                failed.append(label)
                log(logf, f"FAIL  {label}  [{status}]  ({seconds}s)")
                log(logf, "      " + detail.replace("\n", "\n      "))

    log(logf, f"=== done: {len(built)} built, {len(held)} held, {len(failed)} failed, "
              f"{len(skipped)} skipped ===")
    print(f"\ndone · {len(built)} built, {len(held)} held, {len(failed)} failed · "
          f"{len(skipped)} skipped (no source)")
    if held:
        print("held (waiting on a ruling): " + ", ".join(held))
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    main()
