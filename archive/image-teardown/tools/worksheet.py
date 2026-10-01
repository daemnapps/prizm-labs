#!/usr/bin/env python3
"""The designer's work order: four runnable prompts, not a strategy document.

    worksheet.py --brand <brand>            every brief in that brand
    worksheet.py --briefs p143,p144         named briefs

Damon, 2026-09-14: *"What the hell does my designer do from here? What are
the instructions? … They're in Higgsfield mostly."*

**The gap this closes.** A finished brief is written for the person deciding
what to make. It runs to eighteen thousand characters, it argues its own
bets, and it names four pictures — a control plus three variations, one
variable moved each time. But only the control ever had a prompt. The other
three lived as prose paragraphs in stage 5, which means the person actually
sitting in Higgsfield had to read an essay and write three prompts from it —
by hand, differently every time, which is the exact drift the slot system
exists to stop.

**So the worksheet renders all four.** Every variation inherits the control's
slots — the same pack, the same fidelity line, the same negatives, the same
references — and changes only its own subject. That is what makes the set a
test: four frames that can differ only where the brief says they differ.

**What it writes**, into the brief's own folder:

    work-order.md        one page: what to make, the settings, the rules
    prompts/00-control.txt
    prompts/01-<slug>.txt        one file per variation, paste-ready
    prompts/02-<slug>.txt
    prompts/03-<slug>.txt

Plain `.txt` on purpose: the designer selects all and copies. A Markdown
file with the prompt in a fenced block loses to a stray backtick, and the
one thing this file cannot afford is to arrive slightly wrong.
"""
import argparse, json, re, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P
import briefs as B

ROOT = HERE.parent
RENDER = P.LAB / "image-production/tools/prompt.py"

# What the designer sets in Higgsfield before pasting anything. Named here
# once so the work order and the chain can never disagree about it.
sys.path.insert(0, str(ROOT))
try:
    from chain import DRAFT_MODEL, DRAFT_MODEL_WHY
except Exception:                                     # pragma: no cover
    DRAFT_MODEL, DRAFT_MODEL_WHY = "gpt_image_2_5", ""

# The standard generates on Nano Banana Pro with the swipe and the product
# pictures as references (DRAFT-STANDARD.md); the designer does the same.
SETTINGS = {"model": "Nano Banana Pro", "quality": "high", "resolution": "2k",
            "count": 4}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


# Stage 5 was told to write one shape and wrote six: `**VARIATION 1 — X**`,
# `**Variation 1 — X**`, `### Variation 1 — X`, `**VARIATION 1: X**`, and the
# fields as `Variable moved` / `Variable that moved` / `Variable`, `Picture` /
# `The picture`. The prompt now pins the labels, but fifteen briefs were
# already written under the old drift and re-running six stages to fix a
# heading would be absurd. So the reader is generous and the writer is strict.
HEAD = re.compile(
    r"^(?:#{2,4}\s*)?\*{0,2}\s*VARIATION\s*(\d+)\s*[—–\-:.]\s*(.+?)\s*\*{0,2}\s*$",
    re.I | re.M)


def field(body, *names):
    """One labelled field out of a variation block, however it was labelled."""
    # The label terminator drifted too: `**Picture:**`, `**The picture.**`,
    # `**Picture**:`. All three are the same field.
    alt = "|".join(names)
    m = re.search(rf"\*\*\s*(?:The\s+)?(?:{alt})\s*[.:]?\s*\*\*\s*[.:]?\s*(.+?)"
                  r"(?=\n\s*\*\*|\n\s*#{2,4}|\Z)", body, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def variations(run):
    """Stage 5's picture set, parsed into control + variations.

    Stage 5 writes the control as a single paragraph and each variation as a
    block of labelled fields. Only two of those fields make a prompt — the
    name and the Picture — and the rest is the argument for running it, which
    belongs in the brief and not in the generator.
    """
    f = run / "out/05-image-variations.md"
    if not f.is_file():
        return None, []
    t = f.read_text()
    cm = re.search(r"(?:\*\*|#{2,4}\s*)(?:THE\s+)?CONTROL\*{0,2}\s*\n+(.+?)"
                   r"(?=\n\s*---|\n\s*(?:#{2,4}\s*)?\*{0,2}\s*VARIATION)",
                   t, re.S | re.I)
    control = re.sub(r"\s+", " ", cm.group(1)).strip() if cm else None

    heads = list(HEAD.finditer(t))
    out = []
    for i, m in enumerate(heads):
        body = t[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(t)]
        pic = field(body, "Picture")
        if not pic:
            continue
        name = m.group(2).strip().rstrip(":").strip()
        out.append({
            "name": name,
            "slug": slug(name),
            "moved": field(body, "Variable moved", "Variable that moved",
                           "Variable"),
            "picture": pic,
            "why": field(body, "What it is for"),
        })
    return control, out


def render(slots, brand):
    tmp = ROOT / "drafts" / brand / "slots" / "_tmp.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(slots, indent=1))
    r = subprocess.run([sys.executable, str(RENDER), "render", "--slots", str(tmp)],
                       capture_output=True, text=True, cwd=str(ROOT))
    tmp.unlink(missing_ok=True)
    if r.returncode:
        return None, r.stderr.strip()[:200]
    return r.stdout.strip(), None


def plates(bid, rec):
    """The prompts this brief asks for: the standard's own prompt as the
    control, and each stage-5 variation as that control plus one line that
    moves one thing.

    Rebuilt 2026-09-18 on the draft standard. Until then the designer's
    prompts were the brief's picture paragraph rendered through thirteen
    slots — the paragraph the standard took OUT of the generator because it
    argued with the swipe. Her control is now exactly what our machine sends
    (`fal_drafts.assemble`), with the same references, so what she makes
    and what we made can only differ by the roll.
    """
    import fal_drafts as F
    brand = rec["brand"]
    jobs = [j for j in json.loads((ROOT / "drafts" / brand / "jobs.json").read_text())["jobs"]
            if j["brief"] == bid] if (ROOT / "drafts" / brand / "jobs.json").is_file() else []
    if not jobs:
        return None, f"no job — run: chain.py drafts --brand {brand} --briefs {bid}"
    job = F.with_read(brand, jobs)[0]
    control, refs, names = F.assemble(job)
    if control is None:
        return None, "no source.jpg"
    run = P.RUNS / rec["run"]
    _, vars_ = variations(run)

    out = [{"n": 0, "name": "Control", "slug": "control", "moved": None,
            "why": "the frame the brief is built on — everything else is "
                   "measured against it",
            "prompt": control, "refs": refs, "ref_names": names}]
    if job.get("leave_alone"):
        return out, None            # our version of the same photo: one picture
    for i, v in enumerate(vars_, 1):
        delta = (v["moved"] or v["name"]).strip().rstrip(".")
        prompt = (control.rstrip() + "\n\nTHIS FRAME CHANGES ONE THING FROM THE ABOVE — "
                  + delta + ". Everything else holds exactly as written: the same "
                  "reproduction of IMAGE 1, the same woman, the same product, the "
                  "same words, the same offer, the same colour.")
        out.append({"n": i, "name": v["name"], "slug": v["slug"],
                    "moved": v["moved"], "why": v["why"], "prompt": prompt,
                    "refs": refs, "ref_names": names})
    return out, None


# --- the two ratio routes, in her words ---------------------------------
# Both end at 9:16. The only question is which canvas the generator is
# handed, and that is decided by whether the source draws type
# (SAFE-ZONE.md, scoped 2026-09-14).
NATIVE = """### Why 9:16 when the ad looks 4:5

**Every picture is 9:16.** That is the only shape that can run in every
placement — feed, Stories, Reels — off one file.

**But the feed crops it to a centred 4:5**, so the top 15% and the bottom 15%
get thrown away there. Everything that has to be *seen* — the face, the eye
line, the hands, the body part, the product, any words — lives inside that
middle 4:5. The outer bands still have to be real picture: more floor, more
wall, more sky. Not empty space, and never a solid bar.

Judge every frame twice, then: **does it read at 9:16, and does it still read
with the top and bottom 15% covered?** If the face is clipped in the second
test, it is a reject no matter how good the first one looked."""

PAD = """### Generate 4:5. We make it 9:16.

**This brief takes the other route, and it is deliberate.** The ad it copies
has words drawn into the frame — a headline, a badge, a price. We have tried
generating those at 9:16 and telling the model to keep the type in the middle,
and it loses every time: the model fills whatever canvas it is given, the
headline creeps toward the top, and the feed crop cuts it off. Three out of
three.

So **you generate at 4:5** and everything stays where you put it. We pad it
out to 9:16 on our side before it runs, so it still reaches every placement.

Nothing for you to do about the padding — just don't hand back a 9:16 file,
and don't leave a margin at the top or bottom "for the band". Fill the 4:5."""


HOWTO = """# How to work a brief — in Higgsfield, click by click

You need this folder and Higgsfield. Nothing else.

## What is in the folder

| File | What it is |
|---|---|
| `source.jpg` | **the swipe** — the real post this ad copies. This is the target, and it is also your first reference image. |
| `refs/` | **the reference images to attach**, numbered in the order the prompt names them: `1-swipe.jpg`, then our product from a few angles. |
| `draft.png` | **our machine's attempt**, made from these same prompts and references. Not final, not precious. |
| `prompts/*.txt` | **{n} prompts, paste-ready.** `00-control` is the picture; the rest are the control with one thing changed. |
| `work-order.md` | this page |
| `brief.md` | the full argument behind it. Read it if you want the why; you do not need it to work. |

## Set up once per brief

1. **Higgsfield → Image.**
2. **Model: `{model}`** (it is the one that takes several reference images).
3. **Aspect ratio: `{ratio}`.** Resolution 2K. Number of images: 4.
4. **Attach the references, in order.** Add image → pick every file in `refs/`,
   lowest number first. `1-swipe.jpg` must be first — the prompt calls it IMAGE 1.
   {refs_note}
5. Nothing else. No Elements, no styles, no presets. The prompt carries everything.

## Then, for each prompt file

1. Open `prompts/00-control.txt`, select all, copy, paste into the prompt box.
   **Change nothing.** If a prompt looks wrong, say so — do not fix it quietly.
2. Generate 4.
3. Keep the **one** that looks most like `source.jpg` *and* passes the crop check below.
4. Next file — `01-…`, `02-…` — same references, same settings, new prompt. Each one
   moves exactly one thing; that is on purpose.
5. Drop your keepers into a `finals/` folder in here, named after the prompt:
   `00-control.png`, `01-<name>.png`, and so on.

{ratio_note}

## The one rule that gets broken every time

**Match the swipe. Do not improve on it.**

`source.jpg` is a phone photo somebody posted. If your picture is sharper,
cleaner, better lit or better composed than the swipe, it is wrong — it
reads as an advertisement, and the entire reason this format works is that
it does not. Grain, soft focus, an awkward crop, a blown-out window: those
are features. Keep them.

- **No phone or camera in frame, ever** — including in a selfie.
- **If the swipe has words**, ours has our words in the same place, at the
  same weight. The prompt gives them.

## When a prompt will not give you the frame

Re-roll it two or three times — same prompt, same references, same settings.
If it still will not land, write one line in `finals/notes.txt` saying which
prompt and what it keeps doing wrong, and move on. Do not rewrite the prompt.
"""


def work_order(bid, rec, ps):
    brand = rec["brand"]
    sf = json.loads((ROOT / "drafts" / brand / "slots" / f"{bid}.json").read_text())
    names = ps[0].get("ref_names") or []
    if len(names) <= 1:
        refs_note = ("This brief has **one reference, the swipe** — an organic "
                     "post with no product in it. Ours is our version of the "
                     "same photo, nothing added.")
    else:
        refs_note = ("The product pictures after the swipe are the same tube from "
                     "different angles" + (", then the rest of the range" if len(names) > 4 else "")
                     + " — they tell the model what the product IS; the prompt says "
                     "where it goes and at what angle.")
    route = sf.get("ratio_route") or ("pad" if sf.get("ratio") == "4:5" else "native")
    head = HOWTO.format(model=SETTINGS["model"], ratio=sf.get("ratio", "9:16"),
                        n=len(ps), refs_note=refs_note,
                        ratio_note=PAD if route == "pad" else NATIVE)
    n = len(ps)
    word = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}.get(n, str(n))
    lines = [f"# {bid} — work order", "",
             f"**{rec['brand']}** · {(rec.get('product') or '').replace('-', ' ')} · {rec.get('run')}  ",
             f"{word} picture{'s' if n != 1 else ''}. Written {date.today().isoformat()}.", "",
             f"## What the {word.lower()} {'are' if n != 1 else 'is'}", "",
             "| File | What it is | The one thing it moves |", "|---|---|---|"]
    for p in ps:
        lines.append(f"| `prompts/{p['n']:02d}-{p['slug']}.txt` | {p['name']} | "
                     f"{p['moved'] or '—'} |")
    lines += ["", "## The references, in order", "",
              "| # | File in `refs/` | What it is |", "|---|---|---|"]
    for k, (path, nm) in enumerate(zip(ps[0].get("refs") or [], names), 1):
        what = "the swipe — IMAGE 1" if k == 1 else ("our product" if k <= 4 else "the range")
        fn = f"1-swipe{path.suffix}" if k == 1 else f"{k}-{nm}{path.suffix}"
        lines.append(f"| {k} | `{fn}` | {what} |")
    lines += ["", "Each variation is the control with a single thing moved, so a "
                  "difference in performance can only be that thing. Shoot "
                  f"{'it' if n == 1 else 'all ' + word.lower()}.", "", "---", "", head]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand"); ap.add_argument("--briefs")
    a = ap.parse_args()
    reg = B.load()
    ids = [x.strip() for x in a.briefs.split(",")] if a.briefs else \
        [b for b, r in sorted(reg["briefs"].items())
         if r.get("run") and (not a.brand or r.get("brand") == a.brand)]
    n = 0
    for bid in sorted(ids):
        rec = reg["briefs"].get(bid)
        if not rec or not rec.get("run"):
            print(f"  ! {bid}: no run"); continue
        ps, err = plates(bid, rec)
        if err:
            print(f"  ! {bid}: {err}"); continue
        d = ROOT / "worksheets" / rec["brand"] / bid
        import shutil as _sh
        if (d / "prompts").is_dir():
            _sh.rmtree(d / "prompts")        # never leave a stale prompt behind
        (d / "prompts").mkdir(parents=True, exist_ok=True)
        for p in ps:
            (d / "prompts" / f"{p['n']:02d}-{p['slug']}.txt").write_text(
                p["prompt"] + "\n")
        # the references, numbered as the prompt names them
        import shutil as _sh
        rd = d / "refs"
        if rd.is_dir():
            _sh.rmtree(rd)
        rd.mkdir()
        for k, (path, nm) in enumerate(zip(ps[0]["refs"], ps[0]["ref_names"]), 1):
            _sh.copy(path, rd / (f"1-swipe{path.suffix}" if k == 1 else f"{k}-{nm}{path.suffix}"))
        (d / "work-order.md").write_text(work_order(bid, rec, ps))
        rec["worksheet"] = f"worksheets/{rec['brand']}/{bid}"
        rec["plates"] = len(ps)
        print(f"  {bid}  {len(ps)} prompts → {d.relative_to(ROOT)}")
        n += 1
    B.save(reg)
    print(f"\n{n} work orders. Deliver them: tools/deliver.py --brand <brand>")


if __name__ == "__main__":
    main()
