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

import argparse, json, re, subprocess, sys
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
- **Are hands, limbs and anatomy coherent?** Count fingers where hands show.
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

Return exactly this, nothing else:

VERDICT: PASS or FAIL

Then one line per test, in order:
`<PASS|FAIL> — <the test, shortened> — <what you actually saw>`

Then, if anything failed:
FIX: one sentence naming what the next generation must change.
"""


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


def seen(plate, tests, model):
    prompt = JUDGE_PROMPT.format(
        tests="\n".join(f"- {t}" for t in tests) or "- (the brief listed none)")
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
        got = seen(plate, tests, model)
        if got[0] is None:
            verdict, extra, fix = "FAIL", got[1], None
            rows += extra
        else:
            verdict, extra, fix = got
            rows += extra
    if any(s == "FAIL" for s, _, _ in rows):
        verdict = "FAIL"
    return verdict, rows, fix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--plate")
    ap.add_argument("--retry", type=int, default=0,
                    help="regenerate and re-judge a failing plate, N times")
    ap.add_argument("--model", default="gemini-3.1-pro-preview")
    a = ap.parse_args()

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
