#!/usr/bin/env python3
"""Judge a plate against the brief's own accept tests. No human in it.

    judge.py <run>                    every plate
    judge.py <run> --plate control    one of them
    judge.py <run> --retry 2          regenerate and re-judge a failure

Taste happened upstream — in choosing which brand and which angle to swipe.
Everything from here is verification, and verification is programmable. The
question is never "do I like it", it is:

    is it accurate · does it make sense · does it work · is it visual

Two kinds of check, because they fail differently:

**Measured** — counted off the pixels, no model involved. A band the brief
declared empty either is or is not. These cannot be argued with, so they run
first and a failure short-circuits the rest.

**Seen** — the brief's own accept tests, put to a vision model with the plate
in front of it. Anatomy, whether the load-bearing action reads, whether a
third-party brand is legible anywhere. The model answers each test PASS or
FAIL with the evidence it saw, and is told plainly that a hedge counts as a
FAIL — a plate nobody can confirm is not a plate that passed.
"""

import argparse, re, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

JUDGE_PROMPT = """You are checking one generated advertising plate against the
tests its own brief wrote. The picture is attached.

**This is verification, not taste.** Nobody is asking whether the picture is
good. Each test below is a factual question about what is or is not in the
frame. Answer only from what you can see.

**A hedge is a FAIL.** "Mostly", "appears to", "hard to tell" — if you cannot
confirm it, the plate has not passed it. A plate nobody can confirm is not a
plate that passed.

The tests:

{tests}

Also check these, every time, whatever the tests say:

- **Is there ANY text, lettering, number, watermark or caption in the frame?**
  A plate carries no words at all — the type is set afterwards. Any legible
  character is a FAIL, and say where it is. **Look in the corners and in small
  boxes, not only at the obvious headline.** A plate passed on 2026-08-31
  carrying a "lorem ipsum dolor sit amet" line and two empty white rectangles
  in its lower third, because nothing was looking there. Placeholder text,
  greeked type and stray boxes are exactly the leak a reference brings across.
- **Is there any empty box, frame, rule or outline the picture does not need?**
  An edit model copies the reference's furniture. A rectangle sitting on skin
  with nothing in it is a FAIL — the format's boxes are drawn later, from the
  layout data.
- **Is any real, legible third-party brand visible anywhere?** Automatic FAIL.
- **Anatomy — count it out, do not judge it at a glance.** Before you give
  any verdict on this, write these counts on their own lines, as numbers:

      people visible: N
      arms visible: N
      hands visible: N
      fingers per hand: N, N, ...
      legs visible: N

  Then check them against the people. One person has two arms, two hands,
  five fingers per hand, two legs. **Any count that is impossible for the
  number of people in the frame is an automatic FAIL** — a third arm, a
  spare hand, a sixth finger, a limb entering the frame from nowhere — no
  matter how good the rest of the picture is.

  Measured cause, 2026-08-31: a plate showing three arms was passed with
  "Anatomy coherent — hands and fingers are structurally correct". The
  instruction said to count fingers, so fingers were counted and limbs were
  not. Counting is the check. Writing the numbers down is what makes you
  count.
- **Is the product absent?** This plate is built with the product left out on
  purpose — it is composited in afterwards from a photograph, because a model
  can only approximate a wordmark. An empty container, an empty surface or
  empty space where the product belongs is CORRECT and passes. A rendered
  bottle, tube or jar is a FAIL. **Ignore any accept test that describes what
  the product looks like** — those describe the photograph that gets composited
  in, not this plate.
- **Ignore every test about something that is added later.** A plate is the
  photograph only. Type, headlines, badges, boxes, frames, rules, offer bars
  and the product are all composited afterwards, so a test asking whether a
  headline, a white square, a box or a product is present describes the
  FINISHED AD, not this plate. Their absence is correct and passes. Judge only
  what a camera would have captured.
- **Does the picture read at a glance** — would a person scrolling understand
  what they are looking at in well under a second?
- **Is the result believable?** First answer this, on its own line:

      shows a result: YES or NO

  A frame shows a result when it depicts an after state, a treated area, a
  transformation, a before/after pair, or skin/hair/a body that the ad is
  claiming has improved. If it is NO — a problem-state frame, a product on a
  surface, a scene with no claim in it — this check passes and you move on.

  If it is YES, the frame has a **credibility budget** and blowing it is a
  FAIL, however beautiful the picture is:

{budget}

  Say which of those you can actually see. A result nobody would believe is
  worth less than no result, because it tells the viewer the whole ad is
  staged. **If the treated area looks like a brochure, that is a FAIL.**

Return exactly this, nothing else:

VERDICT: PASS or FAIL

First the anatomy counts, on their own lines, exactly as listed above. A
verdict without those numbers written out is not an answer.

Then one line per test, in order:
`<PASS|FAIL> — <the test, shortened> — <what you actually saw>`

Then, if anything failed:
FIX: one sentence naming what the next generation must change.
"""


def _default_budget():
    """One source of truth with the generator. `style-packs.json` carries the
    budget as words for the prompt and as a checklist for here, so the picture
    is never asked for one thing and judged against another."""
    try:
        d = json.loads((P.PROD / "style-packs.json").read_text())
        rows = d["_result_budget"]["budget"]
        return "\n".join(f"      - {r}" for r in rows)
    except Exception:
        return "      - The improvement is partial, never total, and the original marks survive."


DEFAULT_BUDGET = _default_budget()


def result_budget(brief):
    """The brief may tighten the credibility budget; otherwise the default.

    Damon, 2026-09-14: the one thing our lane never wrote down was how much
    better a result is ALLOWED to look. Texture we had — the claim we did
    not. A plate that cleared the skin completely used to pass every test we
    ran, which is how a believable machine ships an unbelievable ad."""
    m = re.search(r"\*\*Result budget\*\*(.+?)(?:\n\s*\*\*|\n\s*##|\Z)",
                  brief, re.S)
    if not m:
        return DEFAULT_BUDGET
    lines = [l.strip().lstrip("-*0123456789. ").strip()
             for l in m.group(1).splitlines()]
    lines = [l for l in lines if len(l) > 8]
    return "\n".join(f"      - {l}" for l in lines) or DEFAULT_BUDGET


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def accept_tests(brief):
    for pat in (r"\*\*The accept tests\*\*(.+?)(?:\n\s*##|\Z)",
                r"\*\*How we will know it is right\.\*\*(.+?)(?:\n\s*\*\*|\Z)"):
        m = re.search(pat, brief, re.S)
        if m:
            out = []
            for line in m.group(1).splitlines():
                t = line.strip().lstrip("-*0123456789. ").strip()
                if len(t) > 12:
                    out.append(t)
            if out:
                return out
    return []


def declared_empty(brief):
    """Bands the brief said are empty, as (top%, bottom%). Measured, not seen."""
    out = []
    for m in re.finditer(r"bottom\s+(\d+)\s*(?:percent|%)[^.]*?(?:black|empty|void)",
                         brief, re.I):
        out.append((100 - int(m.group(1)), 100))
    for m in re.finditer(r"(\d+)\s*[–-]\s*(\d+)\s*%[^.]{0,40}?(?:empty|void|black)",
                         brief, re.I):
        out.append((int(m.group(1)), int(m.group(2))))
    return out


def measured(plate, brief):
    """Pixel facts. No model, no argument."""
    res = []
    w, h = map(int, sh(["magick", "identify", "-format", "%w %h", str(plate)])
               .stdout.split())
    res.append(("PASS", "plate is a real image", f"{w}x{h}"))

    for top, bot in declared_empty(brief):
        y0, y1 = int(h * top / 100), int(h * bot / 100)
        strip = sh(["magick", str(plate), "-crop", f"{w}x{max(1, y1-y0)}+0+{y0}",
                    "+repage", "-format", "%[fx:standard_deviation]", "info:"]).stdout
        try:
            sd = float(strip)
        except ValueError:
            sd = 1.0
        ok = sd < 0.035
        res.append(("PASS" if ok else "FAIL",
                    f"band {top}-{bot}% is empty",
                    f"variation {sd:.3f} ({'flat' if ok else 'something is in it'})"))
    return res


def seen(plate, tests, model, budget=DEFAULT_BUDGET):
    prompt = JUDGE_PROMPT.format(
        tests="\n".join(f"- {t}" for t in tests) or "- (the brief listed none)",
        budget=budget)
    tmp = Path("/tmp/_judge_prompt.md")
    tmp.write_text(prompt)
    r = sh([sys.executable, str(P.GEMINI_IMAGE), "--prompt-file", str(tmp),
            "--image", str(plate), "--model", model, "--out", "/tmp/_judge_out.md"])
    if r.returncode:
        return None, [("FAIL", "the judge could not run", r.stderr[-160:])]
    body = re.sub(r"^<!--.*?-->\s*", "", Path("/tmp/_judge_out.md").read_text(), flags=re.S)
    verdict = "FAIL"
    m = re.search(r"VERDICT:\s*(PASS|FAIL)", body, re.I)
    if m:
        verdict = m.group(1).upper()
    rows = []
    for line in body.splitlines():
        mm = re.match(r"\s*`?(PASS|FAIL)`?\s*[—-]\s*(.+?)\s*[—-]\s*(.+)", line, re.I)
        if mm:
            rows.append((mm.group(1).upper(), mm.group(2).strip(), mm.group(3).strip()))
    fix = re.search(r"FIX:\s*(.+)", body)
    return (verdict, rows, fix.group(1).strip() if fix else None)


def judge_one(run, plate, brief, model):
    tests = accept_tests(brief)
    rows = measured(plate, brief)
    hard_fail = any(s == "FAIL" for s, _, _ in rows)

    fix = None
    if hard_fail:
        rows.append(("FAIL", "skipped the vision checks",
                     "a measured test already failed"))
        verdict = "FAIL"
    else:
        got = seen(plate, tests, model, result_budget(brief))
        if got[0] is None:
            verdict, extra, fix = "FAIL", got[1], None
            rows += extra
        else:
            verdict, extra, fix = got
            rows += extra
    if any(s == "FAIL" for s, _, _ in rows):
        verdict = "FAIL"
    return verdict, rows, fix


def composition(plate):
    """Is this picture worth building an ad on? Measured, no model.

    The judge checked anatomy, text leaks and product presence — all rules
    about what must NOT be there. It had no opinion on whether the picture
    was any good, so a plate that was a field of rocks with no subject and
    no quiet area passed, because it broke no rule.

    Three facts decide it:
      a subject      somewhere clearly busier than the rest
      a quiet area   somewhere type can be read
      separation     the two are not the same place

    Returns (ok, reasons)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from read_plate import read
    r = read(Path(plate))
    bad = []
    sub = r["subject"]["detail"]
    mean = r["mean_detail"]
    quiet = r["quiet_bands"][0]["detail"] if r["quiet_bands"] else 1.0

    if mean and sub / mean < 1.45:
        bad.append(f"no subject — the busiest region is only "
                   f"{sub/mean:.2f}x the average, so nothing stands out")
    if quiet > 0.055:
        bad.append(f"nowhere quiet — the calmest band still measures "
                   f"{quiet:.3f}, so any type sits on detail")
    if r["quiet_bands"] and (r["quiet_bands"][0]["bottom_pct"]
                             - r["quiet_bands"][0]["top_pct"]) < 12:
        bad.append("the quiet area is too shallow to set type in")
    return (not bad), bad


def judge_image(plate, model="gemini-3.1-pro-preview"):
    """Judge a single picture on the universal checks alone.

    The batch path has no brief per plate — it has one scene and many
    pictures — so there are no per-plate accept tests to run. What still
    applies is everything in the prompt's "check these every time" block:
    anatomy counted out, no text, no third-party brand, the product
    deliberately absent. Those are the checks that catch the failures worth
    catching."""
    # Composition first: it is measured, instant and free, and there is no
    # point asking a vision model about a picture with nothing in it.
    comp_ok, comp_bad = composition(plate)
    verdict, rows, fix = seen(
        Path(plate), ["(no per-plate tests — universal checks only)"], model)
    ok = comp_ok and (verdict or "").upper() == "PASS"
    lines = [f"{'PASS' if ok else 'FAIL'}  {Path(plate).name}"]
    lines += [f"  FAIL — Composition — {b}" for b in comp_bad]
    lines += [f"  {v} — {t} — {w}" for v, t, w in rows if v.upper() == "FAIL"]
    if fix and not ok:
        lines.append(f"  FIX: {fix}")
    return ok, "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--plate")
    ap.add_argument("--retry", type=int, default=0,
                    help="regenerate and re-judge a failing plate, N times")
    ap.add_argument("--model", default="gemini-3.1-pro-preview")
    a = ap.parse_args()

    # A single image, judged on the universal checks — the batch path.
    if Path(a.run).is_file():
        ok, out = judge_image(a.run, a.model)
        print(out)
        sys.exit(0 if ok else 1)

    run = Path(a.run)
    if not run.is_absolute():
        run = P.RUNS / Path(a.run).name
    brief = (run / "out/06-brief.md").read_text()

    plates = sorted((run / "iterations").glob("plate-*.png"))
    if a.plate:
        plates = [p for p in plates if p.stem.replace("plate-", "") == a.plate]
    if not plates:
        sys.exit("no plates to judge")

    doc = ["# Judge the plates", "",
           "The brief's own accept tests, run on each picture before anything is",
           "built on it. Measured checks first — those are pixel facts. Then the",
           "brief's tests put to a vision model, where a hedge counts as a fail.",
           ""]
    results = {}

    for plate in plates:
        name = plate.stem.replace("plate-", "")
        for attempt in range(a.retry + 1):
            verdict, rows, fix = judge_one(run, plate, brief, a.model)
            print(f"\n{name}  →  {verdict}"
                  + (f"  (attempt {attempt+1})" if a.retry else ""))
            for s, t, ev in rows:
                print(f"  [{s:<4}] {t[:52]:<52} {ev[:60]}")
            if verdict == "PASS" or attempt == a.retry:
                break
            print(f"  regenerating: {fix or 'no fix named'}")
            sh([sys.executable, str(P.TOOLS / "generate.py"), str(run),
                "--only", name])

        results[name] = verdict
        doc += [f"## {plate.stem}", "", f"**Verdict:** {verdict}", ""]
        doc += [f"- `{s}` — {t} — {ev}" for s, t, ev in rows]
        if fix and verdict == "FAIL":
            doc += ["", f"**What the next generation must change:** {fix}"]
        doc += [""]

    (run / "out/08-plate-check.md").write_text("\n".join(doc) + "\n")
    ok = sum(1 for v in results.values() if v == "PASS")
    print(f"\n{ok}/{len(results)} plates pass → out/08-plate-check.md")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
