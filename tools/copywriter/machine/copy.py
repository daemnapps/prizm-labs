#!/usr/bin/env python3
"""copy production — one source and a brief in; the copy out (primary text,
captions, headlines). Stages 0-9, all Claude, all text. Makes no pictures.

    python3 copy.py <source.md> --brand <brand> \
        --product brands/<brand>/products/<product>.md --dry-run     # spends nothing
    python3 copy.py <source.md> --brand <brand> --product <...> \
        [--write-as caption,short-form] [--hooks 5] [--label <name>] \
        [--tier reads=<model>] [--model <one model for every stage>]
    python3 copy.py <source.md> --brand <brand> --product <...> \
        --label <name> --rerun-from stage8                          # keeps 0-7

Runs file at the repo root: runs/copy-machine/<brand>/<label>/ (paths.py).

A prompt file per stage (prompts/, highest -vN- wins), {fields} substituted
from the brand's own files, everything under the operator's own `claude`
login. Lives in components/copywriter since 2026-09-19; reads brands/<brand>/
and never writes there.

Gates: formats are checked against the element library before anything runs;
after stage 8 the copy gate (components/quality-checks) holds copy that names
a price the brand's offer bank does not sell, or still carries an UNFILLED
note — check.json in the run folder says why. --no-gate skips it on purpose.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import context
from pathlib import Path

from paths import HERE, WORKSPACE
PROMPTS = HERE / "prompts"

# The shared pieces (rollout, 2026-09-20): tiers + size escalation + the
# usage-limit signal from components/run-kit, the checks and the hold from
# components/quality-checks, the format list from components/elements. Found
# by walking up, appended (never ahead of this machine's own modules).
#
# NOTHING AT MODULE LEVEL MAY LEAN ON THIS FOLDER'S paths.py. This file is
# named `copy`, and other tools put machine/ at the front of sys.path — so
# the stdlib's own `import copy` (dataclasses does it) lands HERE, inside a
# process whose `paths` module is that tool's, not ours. `from paths import
# HERE, WORKSPACE` works with either; anything more is looked up in main().
_REPO = next((d for d in Path(__file__).resolve().parents
              if (d / "components").is_dir() and (d / "brands").is_dir()), WORKSPACE)
for _p in (_REPO / "components" / "run-kit", _REPO / "components" / "quality-checks",
           _REPO / "components" / "elements" / "machine"):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))
from run_kit.model import TIERS, SMALL_WINDOW_CHARS, UsageLimit, pick   # noqa: E402

# MODEL PER JOB (2026-09-20). Each stage carries a `tier` — what KIND of
# thinking it does — and run_kit's pick() turns tier + prompt size into a
# model. `--model X` still forces X for every stage, which is exactly what
# this runner did before tiers existed; DEFAULT_MODEL stays as the name of
# that old one-model behaviour (`--model claude-opus-5` reproduces it).
DEFAULT_MODEL = "claude-opus-5"
RUN_TIERS = dict(TIERS)          # --tier NAME=MODEL edits this copy, per run

# --rerun-from <stage>: every stage before it is read back from the run folder
# instead of bought again (same rule as components/email-production/email.py).
RERUN_FROM = None
# --dry-run: a list the stages report into instead of calling a model.
DRY = None
DRY_MARK = "[DRY RUN — this stage's output does not exist yet]"

# The chain's shape, in one place. board.py reads this too, so the page and
# the runner can never disagree about what a stage is called or what it does.
# `group` is the phase heading the board prints above a run of stages.
# Rebuilt 2026-08-25 against the video machine's chain, on Damon's call. The
# old shape (concept brief → bank match → write → compliance → brief) was
# invented; this one mirrors components/video-teardown/machine/chain.py stage for
# stage, because that chain already solved the same problem properly.
#
# Two things gone: COMPLIANCE (Damon's ruling — pricing and offer are a
# separate concern, not a copy-writing stage) and BANK MATCH (dissolved: a
# piece of existing copy is a SOURCE to swipe, not a thing to match against).
# One thing added that the old shape never had: SPEC, the brand-free
# construct. Its absence is why output kept arriving in brand voice.
STAGES = [
    dict(key="stage0", tier="reads", id="0", name="Triage", group="READ THE SOURCE",
         label="triage",
         blurb="Which lane, which format, whose voice. Everything downstream binds to this."),
    dict(key="stage1", tier="checks", id="1", name="Read", group="READ THE SOURCE",
         label="record",
         blurb="One source in, one objective record out — beats, turn, proof, voice markers."),
    dict(key="stage2", tier="designs", id="2", name="Spec", group="READ THE SOURCE",
         label="spec",
         blurb="The record abstracted into a brand-free construct everything else slots into."),
    dict(key="stage1b", tier="reads", id="2b", name="Context scout", group="READ THE SOURCE",
         label="context",
         blurb="Sifts everything the brand knows and picks what THIS source needs — and says what it left out."),
    dict(key="stage3", tier="designs", id="3", name="Injection", group="MAKE IT OURS",
         label="injection",
         blurb="Substitution, never rewrite — the construct is the template."),
    dict(key="stage4", tier="checks", id="4", name="Placement", group="MAKE IT OURS",
         label="placement",
         blurb="Where the product enters and how long the piece runs. Decides, writes nothing."),
    dict(key="stage5", tier="designs", id="5", name="Hooks", group="MAKE IT OURS",
         label="hooks",
         blurb="The control plus variations. All ship — the machine never picks."),
    dict(key="stage6", tier="designs", id="6", name="Expansion", group="MAKE IT OURS",
         label="expansion",
         blurb="Gated moves that build commercial structure. Skipped when the source is already an ad.",
         gated_on_lane="ORGANIC"),
    dict(key="stage7", tier="designs", id="7", name="Close", group="MAKE IT OURS",
         label="close",
         blurb="The objection at the flinch, then the landing of the argument."),
    # Where an argument becomes copy. Split out 2026-08-25: the chain was
    # rebuilding the SOURCE's medium (8 text cards, timings) because nothing
    # ever decided what the output physically is. The source's medium is a
    # fact about the source; this stage picks the output's.
    dict(key="stage8", tier="designs", id="8", name="Render", group="WRITE THE COPY",
         label="render",
         blurb="Turns the argument into the actual copy, in each requested format, ready to paste."),
    dict(key="stage9", tier="reads", id="9", name="Brief", group="WHAT SHIPS",
         label="brief",
         blurb="The one document a media buyer opens."),
]
SPEC = {s["key"]: s for s in STAGES}

LANE_LINE = re.compile(r"^LANE:\s*([A-Z ]+)", re.M)
FORMAT_LINE = re.compile(r"^FORMAT:\s*(.+)$", re.M)
AVATAR_LINE = re.compile(r"^AVATAR:\s*([a-z0-9-]+)", re.M)
FUNNEL_LINE = re.compile(r"^FUNNEL:\s*(prospect|lead|customer|churned)", re.M)


def avatar_of(t):
    m = AVATAR_LINE.search(t or "")
    return m.group(1) if m else None


def funnel_of(t):
    m = FUNNEL_LINE.search(t or "")
    return m.group(1) if m else None


def lane_of(triage_text):
    m = LANE_LINE.search(triage_text or "")
    return m.group(1).strip() if m else None


def format_of(triage_text):
    m = FORMAT_LINE.search(triage_text or "")
    return m.group(1).strip() if m else None


def sha(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else None


def read(path, required=False):
    if not path:
        return ""
    # A path may be absolute, workspace-relative, or live in the lab brand
    # tree; a product may be named by its FOLDER (the lab keeps products as
    # folders holding product.md). Try each shape before failing — a wrong
    # path should be one retry away, not a dead batch (2026-08-31).
    for base in (Path(path), WORKSPACE / path):
        for cand in (base, base / "product.md"):
            if cand.is_file():
                return cand.read_text().strip()
    if required:
        sys.exit(f"missing required file: {path} — tried it as given, under "
                 f"the workspace, and as a product folder")
    return ""


def doctrine(slice_name):
    """A Schwartz doctrine slice, bound by path — never restated in a prompt.
    Rendered by components/marketing-doctrine/render.py from frameworks.json."""
    # Read from the repo this machine sits in — NOT the brand tree: pointing
    # --brand-root at another tree used to move this lookup with it and every
    # doctrine slice came back empty, silently.
    f = _REPO / "components" / "marketing-doctrine" / "slices" / f"{slice_name}.md"
    if f.is_file():
        return f.read_text().strip()
    return read(f"components/marketing-doctrine/slices/{slice_name}.md")


def latest_prompt(stage):
    """Same head-resolution rule as brief.py: highest -vN- wins."""
    best, best_v = None, -1
    for f in PROMPTS.glob(f"{stage}-*.md"):
        m = re.search(r"-v(\d+)-", f.name)
        if m and int(m.group(1)) > best_v:
            best, best_v = f, int(m.group(1))
    if not best:
        sys.exit(f"no prompt file found for {stage} in {PROMPTS}")
    return best


def is_usage_limit(stdout, stderr):
    """The account is out of usage — run_kit.model's test, word for word."""
    both = f"{stdout or ''}\n{stderr or ''}".lower()
    return "limit" in both and ("usage" in both or "spend" in both)


def claude(prompt_text, model, label=None):
    # A headless -p session still inherits this repo's project Stop hooks
    # (e.g. video-teardown's run-log guard) even for a stateless prompt-in/
    # text-out call like this one. If a hook is blocking, the session can't
    # prompt a human, so it writes its answer to the HOOK instead of the
    # requested deliverable, silently corrupting the output (confirmed
    # 2026-08-24). --bare skips hooks but also skips normal OAuth login
    # (needs its own ANTHROPIC_API_KEY), so it isn't a real fix here — the
    # actual fix is keeping this repo's working tree clean of whatever a
    # Stop hook is guarding before running the chain.
    # Retry, and say what actually happened (2026-08-31). These calls fail
    # transiently — overload, a dropped connection — and the old code exited
    # on the first one printing r.stderr, which is EMPTY on those failures.
    # "a stage failed:" with nothing after it cost two runs before anyone
    # could see why. Three attempts, then a report carrying the return code
    # and both streams.
    last = None
    for attempt in (1, 2, 3):
        r = subprocess.run(
            ["claude", "-p", "--model", model, "--output-format", "text"],
            input=prompt_text + "\n\nReturn only the deliverable. No tools, no preamble.",
            capture_output=True, text=True,
        )
        if not r.returncode and r.stdout.strip():
            return r.stdout.strip()
        # OUT OF USAGE IS NOT A BROKEN STAGE (2026-09-20). Retrying it three
        # times is three more refusals and fifteen seconds of pretending; say
        # it once and stop the whole run. main() turns this into one line.
        if is_usage_limit(r.stdout, r.stderr):
            raise UsageLimit(f"stage {label or '?'} on {model} was refused: "
                             f"{(r.stdout or r.stderr).strip()[:240]}")
        last = r
        why = (r.stderr or r.stdout or "").strip()[:200] or "no output on either stream"
        if attempt < 3:
            print(f"     ! attempt {attempt} failed (exit {r.returncode}): {why} — retrying")
            time.sleep(5 * attempt)
    sys.exit(f"a stage failed after 3 attempts (exit {last.returncode})\n"
             f"  stderr: {(last.stderr or '').strip()[:300] or '(empty)'}\n"
             f"  stdout: {(last.stdout or '').strip()[:300] or '(empty)'}")


def link_video(src, out_dir):
    """Put the source video where the board can play it, without copying it.

    Damon's note, 2026-08-25: "when we're saying the copy pairs with this
    video, we need to actually have the preview of the video very clear." A
    filename is not a preview — he has to see the thing the copy runs
    against, next to the copy.

    A SYMLINK, never a copy: the mp4 is already on disk once and media never
    enters git (workspace rule 3). A poster frame comes with it so the card
    shows the video instead of a black rectangle before it is played.
    Returns (video_name, poster_name), either of which may be None.
    """
    if not src:
        return None, None
    src = Path(os.path.expanduser(src)).resolve()
    if not src.is_file():
        print(f"     video: {src} not found — the board will show the name only")
        return None, None

    link = out_dir / f"source{src.suffix}"
    try:
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(src)
    except OSError as e:
        print(f"     video: could not link ({e}) — name only")
        return None, None

    poster = out_dir / "poster.jpg"
    if not poster.is_file():
        # a frame from a second in — frame zero is often black or a fade
        # -pix_fmt yuvj420p: without it ffmpeg refuses frames whose colour
        # range it calls "non-standard" and writes nothing, which looks
        # exactly like a video that has no thumbnail. Hit on a real frame of
        # this very video, 2026-08-25.
        r = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", str(src),
             "-frames:v", "1", "-pix_fmt", "yuvj420p", "-vf", "scale=480:-2",
             str(poster)],
            capture_output=True, text=True)
        if r.returncode or not poster.is_file():
            print("     video: linked, no poster (ffmpeg failed) — it still plays")
            return link.name, None
    return link.name, poster.name


def find_video(video_brief, explicit):
    """--video wins. Otherwise look beside the brief: a teardown run keeps its
    source mp4 in the same folder, which is where this normally comes from."""
    if explicit:
        return explicit
    d = Path(os.path.expanduser(video_brief)).resolve().parent
    for name in ("video.mp4", "source.mp4"):
        if (d / name).is_file():
            return str(d / name)
    hits = sorted(d.glob("*.mp4"))
    return str(hits[0]) if hits else None


def vibe_of(record):
    """The read's THE VIBE section, as the lines later stages hold to. Empty
    when the read printed none (an older read) — the stages say what to do then."""
    m = re.search(r"THE VIBE\.?\*{0,2}(.*?)(?=\n\*\*[A-Z][A-Z ]+\.?\*\*|\Z)", record or "", re.S)
    if not m:
        return ""
    block = re.findall(r"^(?:HUMOR|DELIVERY STYLE|REGISTER|REFERENCE WORLD|AVOID|THE JOKE|THE VIBE):.*$", m.group(1), re.M)
    return "\n".join(block) or m.group(1).strip()[:1500]


def fill(template, fields):
    """Deterministic substitution — same rule the board replays to rebuild the
    'filled in' view of a stage without calling a model again."""
    out = template
    for name, value in fields.items():
        out = out.replace("{" + name + "}", value or "(none supplied)")
    return out


def will_reuse(stage, out_dir):
    """--rerun-from keeps a stage when it sits BEFORE the named one and its
    output is actually on disk. A missing file is simply run again."""
    if not RERUN_FROM:
        return False
    order = [s["key"] for s in STAGES]
    return (order.index(stage) < order.index(RERUN_FROM)
            and (Path(out_dir) / f"{stage}--{SPEC[stage]['label']}.md").is_file())


def stage_key(name):
    """`stage8`, `8`, `2b` or `render` -> the stage key. Unknown names are
    refused with the real ones listed."""
    n = (name or "").strip().lower()
    for s in STAGES:
        if n in (s["key"], s["id"].lower(), s["label"], s["name"].lower()):
            return s["key"]
    sys.exit(f"--rerun-from {name}: no such stage — the stages are "
             + ", ".join(f"{s['key']} ({s['name']})" for s in STAGES))


def check_formats(wanted, brand_root=None):
    """Every requested output format against the element library
    (components/elements, list format/copy) BEFORE anything runs. A format the
    brand declares in its own formats.json is the brand's own row and is let
    through, named as such. Returns (ids, brand_own, problems)."""
    import elements as E
    import formats as F
    ids = [w.strip() for w in (wanted or "").split(",") if w.strip()]
    base = {x["key"] for x in json.loads(F.FILE.read_text())["formats"]}
    brand_own = [i for i in ids if i in set(F.keys(brand_root)) - base]
    try:
        problems = E.check({("format", "copy"): [i for i in ids if i not in brand_own]})
    except E.Unknown as e:                      # the list itself is missing
        problems = [e.args[0]]
    if not ids:
        problems.append("no output format was requested and formats.json holds none")
    return ids, brand_own, problems


def live_prices(offer_bank_text):
    """Every price the brand's offer bank sells today, normalised to cents so
    `$49` in the copy and `$49.00` in the bank are the same price."""
    import quality_checks as Q
    return {f"{float(p):.2f}" for p in Q.prices_in(offer_bank_text)}


def copy_gate(render_text, offer_bank_text, out_dir=None):
    """THE COPY GATE — after the words are written (stage 8), before the brief
    hands them on. Two checks from components/quality-checks:

      unfilled_check  the finished copy (everything before CHECKS) carries no
                      UNFILLED note
      price_check     every price in the copy is one the brand's offer bank
                      sells today. A run has no single offer key, so the copy
                      is held to ALL live prices in offers/offer-bank.md.

    Writes check.json via hold(); raises quality_checks.Held on a failure."""
    import quality_checks as Q
    cut = re.search(r"^#{1,3}\s*CHECKS\b", render_text or "", re.M)
    finished = (render_text[:cut.start()] if cut else (render_text or "")).rstrip()
    said = " ".join("$" + f"{float(p):.2f}" for p in sorted(Q.prices_in(finished)))
    live = " ".join("$" + p for p in sorted(live_prices(offer_bank_text)))
    problems = Q.unfilled_check(finished) + Q.price_check(said, live)
    return Q.hold("copy", problems, out_dir)


def print_dry(report, problems, warnings):
    print("\nSTAGES — every {field} each prompt names, against what it is handed")
    for r in report:
        if r.get("reused"):
            print(f"  {r['id']:>2} {r['name']:<14} kept from the earlier run ({r['chars']:,} chars) — not run again")
            continue
        print(f"  {r['id']:>2} {r['name']:<14} {r['prompt']}  ->  {r['model']} ({r['why']})"
              f"  · prompt at least {r['chars']:,} chars (earlier stages' text comes on top)")
        if r.get("note"):
            print(f"       note: {r['note']}")
        for name, status, chars, why in r["fields"]:
            size = "" if status in ("LATER", "UNFILLED") else f"{chars:>9,} chars"
            print(f"       {status:<8} {'{' + name + '}':<20} {size}" + (f"  — {why}" if why else ""))
        if r["unused"]:
            print(f"       (handed but not named by this prompt: {', '.join(r['unused'])})")
    if warnings:
        print("\nWORTH KNOWING (does not stop a run)")
        for w in warnings:
            print(f"  - {w}")
    if problems:
        print("\nMISSING — a real run would fail or write blind")
        for p in problems:
            print(f"  ! {p}")
    print(f"\ndry run: {'NOT READY — ' + str(len(problems)) + ' problem(s)' if problems else 'READY'}"
          "  · model calls made: 0 · files written: 0")


FIELD = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def dry_stage(stage, model, fields, note=None):
    """What a stage WOULD be handed — no model, no file written. Reports every
    `{field}` its prompt names against what the runner passes it."""
    spec = SPEC[stage]
    prompt_file = latest_prompt(stage)
    template = prompt_file.read_text()
    wanted = sorted(set(FIELD.findall(template)))
    filled = fill(template, fields)
    picked, why = pick(spec["tier"], len(filled), forced=model, tiers=RUN_TIERS)
    rows = []
    for name in wanted:
        if name not in fields:
            rows.append((name, "UNFILLED", 0, "the prompt names it and the runner never hands it over"))
            continue
        val = fields[name] or ""
        if DRY_MARK in val:
            rows.append((name, "LATER", len(val), "an earlier stage's output"))
        elif not val.strip():
            rows.append((name, "EMPTY", 0, "handed over with nothing in it"))
        else:
            rows.append((name, "OK", len(val), ""))
    extra = sorted(set(fields) - set(wanted))
    DRY.append({"stage": stage, "id": spec["id"], "name": spec["name"],
                "prompt": prompt_file.name, "tier": spec["tier"], "model": picked,
                "why": why, "chars": len(filled), "fields": rows,
                "unused": extra, "note": note})
    return f"{DRY_MARK} ({stage})"


def run_stage(stage, out_dir, model, state, **fields):
    """`model` is a FORCED model (today's `--model X`), or None to let the
    stage's tier pick one."""
    spec = SPEC[stage]
    saved = out_dir / f"{stage}--{spec['label']}.md"
    reuse = will_reuse(stage, out_dir)
    if DRY is not None:
        if reuse:
            DRY.append({"stage": stage, "id": spec["id"], "name": spec["name"],
                        "reused": True, "chars": len(saved.read_text())})
            return saved.read_text().strip()
        return dry_stage(stage, model, fields)
    if reuse:
        print(f"  == {stage}  (kept from the earlier run)")
        # The earlier record stays as it was — status "done", its model, its
        # prompt version — because that IS what produced this text. `reused`
        # says this run did not pay for it again.
        rec = dict((state.get("_earlier") or {}).get(stage) or {"status": "done", "out": saved.name})
        rec["reused"] = True
        state["stages"][stage] = rec
        return saved.read_text().strip()
    prompt_file = latest_prompt(stage)
    filled = fill(prompt_file.read_text(), fields)
    # The tier proposes, the measured prompt decides (run_kit.model.pick): a
    # small-window model handed a prompt past its window dies with an empty
    # stderr, so size escalates it. A forced model is never second-guessed.
    model, why = pick(spec["tier"], len(filled), forced=model, tiers=RUN_TIERS)
    if why.startswith("escalated"):
        print(f"     {stage}: {why} -> {model}")
    # The prompt as actually sent, saved beside the output. Without it the
    # board can only show the template, and the template is not what ran.
    sent_path = out_dir / f"{stage}--sent.md"
    sent_path.write_text(filled)

    print(f"  -> {stage}  ({prompt_file.name})  [{model}]")
    t0 = time.time()
    output = claude(filled, model, stage)
    seconds = round(time.time() - t0, 1)

    out_path = out_dir / f"{stage}--{spec['label']}.md"
    out_path.write_text(output + "\n")
    state["stages"][stage] = {
        "status": "done",
        "seconds": seconds,
        "chars_out": len(output),
        "model": model,
        "tier": spec["tier"],
        "model_why": why,
        # Relative to THIS build, not the brand tree — the prompts live with
        # the runner, and the two are no longer in the same repo.
        "prompt_file": str(prompt_file.relative_to(HERE)),
        "prompt_name": prompt_file.name,
        "prompt_sha256_12": sha(prompt_file),
        "wants": sorted(fields.keys()),
        "out": out_path.name,
        "sent": sent_path.name,
    }
    return output


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="the source to write from: a teardown record "
                    "(video/image, ad or organic) OR raw copy to swipe")
    ap.add_argument("--brand", required=True,
                    help="brand folder name under brands/ — there is no default brand")
    ap.add_argument("--product", required=True, help="workspace-relative path to the product file")
    ap.add_argument("--source-reference", default=None,
                    help="link/name for the source, for the brief")
    ap.add_argument("--video", default=None,
                    help="an mp4 of the source, so the board can play it. "
                         "Defaults to one found next to the source.")
    ap.add_argument("--hooks", default="5", help="how many hook variations beyond the control")
    ap.add_argument("--write-as", default="",
                    help="output format(s), comma-separated. Defaults to every format "
                         "in formats.json — a source gets them all. This is what we are "
                         "WRITING, not what the source was. Each id is checked against "
                         "the element library (format/copy) before anything runs.")
    ap.add_argument("--channel", default="Meta (feed / Reels)",
                    help="where the copy runs, e.g. 'Meta (feed / Reels)', 'TikTok', 'email'")
    ap.add_argument("--label", default=None, help="run label; defaults to the source filename stem")
    ap.add_argument("--model", default=None,
                    help="force ONE model for every stage (the old behaviour: "
                         f"--model {DEFAULT_MODEL}). Left out, each stage's tier picks.")
    ap.add_argument("--tier", action="append", default=[], metavar="NAME=MODEL",
                    help="point a tier at a different model for this run, e.g. "
                         "--tier reads=claude-sonnet-5. Tiers: " + ", ".join(TIERS))
    ap.add_argument("--rerun-from", default=None, metavar="STAGE",
                    help="keep every saved stage before this one and run from here on, "
                         "e.g. --rerun-from stage8 (also: 8, render)")
    ap.add_argument("--dry-run", "--dry", dest="dry_run", action="store_true",
                    help="resolve every input, format, prompt field and model and print "
                         "OK/MISSING — no model call, no file written")
    ap.add_argument("--avatar", default=None,
                    help="name the avatar instead of letting triage pick it. In a dry run, "
                         "the avatar whose files are checked (default: every one on the roster).")
    ap.add_argument("--no-gate", action="store_true",
                    help="skip the copy gate after stage 8 (prices + unfilled notes) on purpose")
    ap.add_argument("--brand-root", default=None,
                    help="tree holding brands/<brand>/ — defaults to the shared "
                         "ai-workspace; point it elsewhere when brand context moves")
    args = ap.parse_args(argv)

    import paths as P                    # this machine's own — see the note at the top
    global WORKSPACE, RERUN_FROM, DRY
    dry = args.dry_run
    DRY = [] if dry else None
    problems, warnings = [], []          # a dry run's findings
    RERUN_FROM = stage_key(args.rerun_from) if args.rerun_from else None
    for t in args.tier:
        name, _, model_name = t.partition("=")
        if name not in RUN_TIERS or not model_name:
            sys.exit(f"--tier {t}: write it NAME=MODEL, where NAME is one of {', '.join(TIERS)}")
        RUN_TIERS[name] = model_name

    # One knob, honoured everywhere that reads brand files, so the scout and
    # the runner can never end up indexing two different trees.
    if args.brand_root:
        root = Path(os.path.expanduser(args.brand_root)).resolve()
        if not (root / "brands").is_dir():
            sys.exit(f"--brand-root has no brands/ inside it: {root}")
        WORKSPACE = root
        context.WORKSPACE = root
    # The brand tree is found by SHAPE, never assumed (2026-08-31, after the
    # third silent empty-roster run): --brand-root wins when given; otherwise
    # probe the trees a brand actually lives in and take the first that holds
    # this brand's banks. language.py was rewritten single-root by its owner,
    # so the probing lives here now — a machine that cannot find the banks
    # must never quietly write without them. (The lab brand tree this used to
    # probe first was merged into brands/ on 2026-09-02 and no longer exists;
    # the workspace is the one candidate left.)
    import language as _L
    if args.brand_root:
        BRAND_TREE = root
    else:
        BRAND_TREE = None
        for cand in (WORKSPACE,):
            if _L.avatar_root(args.brand, cand).is_dir():
                BRAND_TREE = cand
                break
    print(f"brand context: {WORKSPACE}")
    brand_root = WORKSPACE / "brands" / args.brand
    if not brand_root.is_dir():
        known = sorted(p.name for p in (WORKSPACE / "brands").iterdir()
                       if p.is_dir() and not p.name.startswith(("_", "."))) \
            if (WORKSPACE / "brands").is_dir() else []
        sys.exit(f"--brand {args.brand}: no such folder under {WORKSPACE / 'brands'} — "
                 f"the brands there are: {', '.join(known) or 'none'}")

    # ELEMENTS, BEFORE ANYTHING RUNS (2026-09-20). What this run writes is a
    # pick from a list — bank/formats.json, read through the element library
    # as format/copy. A format that is not on the list is refused here, with
    # the real ids named, rather than reaching stage 8 as a word the writer
    # has to guess the meaning of.
    import formats as F
    if not args.write_as:
        args.write_as = ", ".join(F.keys(brand_root))
    format_ids, brand_own, format_problems = check_formats(args.write_as, brand_root)
    if brand_own:
        print(f"     formats: {', '.join(brand_own)} — the brand's own row(s), not in the shared list")
    if format_problems and not dry:
        sys.exit("--write-as refused — not an output format this machine writes:\n  "
                 + "\n  ".join(format_problems))
    problems += format_problems
    # --channel is free text a person reads ("Meta (feed / Reels)") and the
    # library's placement/all list is WHAT is written (primary-text, headline),
    # not WHERE it runs — the two do not map cleanly, so the channel is
    # recorded as given and not checked.
    elements = {"format/copy": format_ids, "brand_own_formats": brand_own,
                "channel": {"value": args.channel, "checked": False,
                            "why": "free text; placement/all lists what is written, not where it runs"}}

    label = args.label or Path(args.source).stem
    # Output lives under runs/, keyed by the machine's spoken name, never
    # beside the code (runs/README.md, ruled 2026-09-17). results/ is history:
    # a run begun there before the move is picked up from there ONCE, so
    # --rerun-from can reuse its stages, and continues in its new home.
    out_dir = P.run_dir(args.brand, label)
    old = P.RESULTS / label
    carry = not out_dir.exists() and old.is_dir() and bool(RERUN_FROM)
    if dry:
        if carry:
            print(f"     would carry the earlier stages over from results/{label}")
            out_dir = old                      # read-only here: a dry run writes nothing
    else:
        if carry:
            import shutil
            out_dir.parent.mkdir(parents=True, exist_ok=True)
            # symlinks=True: the source video is a LINK and must stay one —
            # following it would copy an mp4 into the repo.
            shutil.copytree(old, out_dir, symlinks=True)
            print(f"     carried the earlier stages over from results/{label}")
        out_dir.mkdir(parents=True, exist_ok=True)
    print(f"run folder: {P.run_dir(args.brand, label)}")

    # Where a brand keeps its files is the BRAND's business, not this
    # runner's. A brand may declare the map itself in variables/copy.md — one
    # `variable: path` line each — and anything it does not declare falls back
    # to the conventional layout. Hardcoding one brand's folder shape is what
    # makes a tool work for exactly one brand.
    conventional = {
        "avatar": "customer/avatar.md",
        "language_bank": "customer/language-bank.md",
        "offer_file": "offers/offer-bank.md",
    }
    declared = {}
    # The brand's own map is the ONLY map (Damon, 2026-08-31): nothing
    # brand-specific lives inside this machine. The map follows the
    # variables/ convention — one map per brand, PER SURFACE — so this
    # machine reads variables/copy.md and never email's or video's map.
    # The chain-vars names are legacy fallbacks for older brand trees.
    map_file = None
    for f in (brand_root / "variables" / "copy.md",
              brand_root / "chain-vars.md", brand_root / "chain-variables.md"):
        if f.is_file():
            for m in re.finditer(r"^\s*\|?\s*`\{?([a-z_]+)\}?`\s*\|\s*`([^`]+\.(?:md|json|/))`?",
                                 f.read_text(), re.M):
                declared[m.group(1)] = m.group(2)
            if declared:
                map_file = f
                print(f"     brand map: {f.name} ({len(declared)} vars)")
                break

    def brand_rel(var, avatar_key=None):
        rel = declared.get(var, conventional.get(var))
        if not rel:
            return None
        if "<avatar>" in rel:
            if not avatar_key:
                return None        # avatar-shaped, and nobody is declared yet
            rel = rel.replace("<avatar>", avatar_key)
        return rel

    def brand_file(var, avatar_key=None):
        rel = brand_rel(var, avatar_key)
        if not rel:
            return ""
        p = Path(rel)
        return read(p if p.is_absolute() or (WORKSPACE / p).is_file() else brand_root / rel)

    offer_file = brand_file("offer_file")
    product_file = read(args.product, required=True)
    source = read(args.source, required=True)
    formats = F.render(brand_root)          # data, not a hand-kept table
    source_reference = args.source_reference or Path(args.source).stem
    now = datetime.date.today()
    today = f"{now:%A, %-d %B %Y}"

    vid_src = find_video(args.source, args.video)
    video_name = poster_name = None
    if not dry:
        video_name, poster_name = link_video(vid_src, out_dir)
    if video_name:
        print(f"     source media: {Path(vid_src).name}"
              + (" + poster" if poster_name else " (no poster)"))

    earlier = {}
    if RERUN_FROM and (out_dir / "run.json").is_file():
        try:
            earlier = json.loads((out_dir / "run.json").read_text()).get("stages") or {}
        except ValueError:
            earlier = {}
    state = {
        "slug": label,
        "label": label,
        "brand": args.brand,
        "product": args.product,
        "video_source": vid_src,
        "video": video_name,
        "poster": poster_name,
        "source_path": args.source,
        "source_reference": source_reference,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "models": {"forced": args.model, "tiers": dict(RUN_TIERS)},
        "elements": elements,
        "rerun_from": RERUN_FROM,
        "stages": {},
        "_earlier": earlier,
    }

    def save():
        if dry:
            return
        (out_dir / "run.json").write_text(json.dumps(
            {k: v for k, v in state.items() if not k.startswith("_")}, indent=2) + "\n")

    print(f"copy chain: {label}  (brand={args.brand}, "
          f"model={args.model or 'by tier — ' + ', '.join(f'{k}={v}' for k, v in RUN_TIERS.items())})"
          + ("  [DRY RUN — nothing is spent, nothing is written]" if dry else ""))

    # --- read the source ---------------------------------------------------
    import language as L
    roster = L.avatars(args.brand, BRAND_TREE) or []
    roster_txt = "\n".join(
        f"- `{a['key']}` — {a['rows']:,} rows · funnels: "
        + ", ".join(f"{k} {v:,}" for k, v in sorted(a['funnels'].items()) if k)
        + (f" · sub-avatars: {', '.join(a['subs'])}" if a['subs'] else "")
        for a in roster) or "- (this brand has no avatar language banks)"
    roster_keys = [a["key"] for a in roster]
    if args.avatar and args.avatar not in roster_keys:
        sys.exit(f"--avatar {args.avatar}: not on this brand's roster — "
                 f"the avatars are: {', '.join(roster_keys) or 'none'}")

    # An empty roster is indistinguishable, downstream, from a brand that has
    # no banks: triage answers "none fit", every writing stage draws on
    # nothing, and a complete brief comes out the far end with no language
    # behind it. Nothing errors. Say it loudly instead — the run continues,
    # because whether to write without language is a human's call, not this
    # runner's.
    if not roster:
        print(f"     ! NO LANGUAGE BANKS FOUND for '{args.brand}'.")
        print(f"       Looked for brands/{args.brand}/core-avatars/ beneath "
              f"{'the tree you named' if BRAND_TREE else 'every root language.py knows'}.")
        print( "       Every stage will write with no real language behind it.")
        warnings.append(f"no language banks found for {args.brand} — every stage would write blind")

    if dry:
        # THE INPUTS, ONE LINE EACH. Triage is a model call, so a dry run does
        # not know which avatar a real run would pick — it checks the
        # avatar-shaped files for EVERY avatar on the roster (or the one named).
        def line(status, what, chars, where=""):
            print(f"  {status:<8} {what:<34} {chars:>9,} chars  {where}")
        print("\nINPUTS")
        line("OK", "source", len(source), args.source)
        line("OK", "product file", len(product_file), args.product)
        line("OK" if map_file else "MISSING", "brand variable map",
             len(map_file.read_text()) if map_file else 0,
             str(map_file.relative_to(WORKSPACE)) if map_file
             else "no variables/copy.md — the conventional layout is assumed")
        if not map_file:
            warnings.append("the brand has no variables/copy.md — falling back to customer/avatar.md etc.")
        line("OK" if offer_file else "MISSING", "{offer_file}", len(offer_file),
             brand_rel("offer_file") or "")
        if not offer_file:
            warnings.append("no offer bank found — stages run without it, and the copy gate "
                            "will hold any copy that names a price")
        else:
            print(f"           live prices the copy gate will allow: "
                  f"{len(live_prices(offer_file))}" + ("  (gate OFF: --no-gate)" if args.no_gate else ""))
        for slice_name in ("awareness", "sections", "techniques", "offer-close", "verification"):
            txt = doctrine(slice_name)
            line("OK" if txt else "MISSING", f"doctrine slice: {slice_name}", len(txt),
                 f"components/marketing-doctrine/slices/{slice_name}.md")
            if not txt:
                problems.append(f"doctrine slice `{slice_name}` is missing or empty")
        print("\nOUTPUT FORMATS  (element library: format/copy)")
        for i in format_ids:
            bad = [p for p in format_problems if f"`{i}`" in p]
            line("MISSING" if bad else "OK", i, 0,
                 bad[0] if bad else ("the brand's own row" if i in brand_own else "on the list"))
        print(f"  --       channel: {args.channel!r} — recorded as given, not checked "
              "(placement/all lists what is written, not where it runs)")
        print(f"\nAVATAR-SHAPED FILES  ({'--avatar ' + args.avatar if args.avatar else 'every avatar on the roster — triage picks one in a real run'})")
        lang_stages = ("injection", "hooks", "expansion", "close", "render")
        for key in ([args.avatar] if args.avatar else roster_keys):
            for var in ("avatar", "language_bank"):
                txt = brand_file(var, key)
                line("OK" if txt else "MISSING", f"{key} · {{{var}}}", len(txt), brand_rel(var, key) or "")
                if not txt:
                    (problems if args.avatar else warnings).append(
                        f"avatar `{key}` has no {var} file at {brand_rel(var, key)}")
            for st_name in lang_stages:
                txt = L.for_stage(args.brand, st_name, key, None, None, 40, BRAND_TREE) or ""
                thin = not txt or "no rows matched" in txt
                line("MISSING" if thin else "OK", f"{key} · language for {st_name}",
                     0 if thin else len(txt), "language-layer query (local)")
                if thin:
                    (problems if args.avatar else warnings).append(
                        f"avatar `{key}` has no language rows for the {st_name} stage")
        print(f"\nCONTEXT INDEX  {len(context.index(args.brand)):,} chars — what stage 2b chooses from")

    triage = run_stage("stage0", out_dir, args.model, state,
                       today=today, source=source, formats=formats,
                       avatars=roster_txt); save()
    lane, fmt = lane_of(triage), format_of(triage)
    avatar, funnel = avatar_of(triage), funnel_of(triage)
    # one avatar means there is nothing to choose; do not let a misread
    # override the only real answer
    if args.avatar:
        avatar = args.avatar
    elif len(roster) == 1:
        avatar = roster[0]["key"]
    elif avatar and avatar not in {a["key"] for a in roster}:
        print(f"     ! triage named an avatar that does not exist: {avatar}")
        avatar = None
    dry_note = None
    if dry and not avatar and roster_keys:
        avatar = max(roster, key=lambda a: a["rows"])["key"]
        dry_note = (f"stage fields below are filled for avatar `{avatar}` (the fullest bank) — "
                    "triage picks the real one; every avatar's files are listed above")
        print(f"\n     {dry_note}")
    state.update(lane=lane or "unread", format=fmt or "unread",
                 avatar=avatar, funnel=funnel)
    if not dry:
        print(f"     lane: {lane or '?'} · format: {fmt or '?'} · "
              f"avatar: {avatar or '?'} · funnel: {funnel or '?'}")

    # NOW the avatar-shaped files can resolve — the run knows who it speaks
    # to. Also fixes a real bug: the profile text used to be read before
    # triage and then clobbered by the avatar KEY, so stage 3's {avatar} got
    # the word "spot-hider" instead of the profile.
    avatar_profile = brand_file("avatar", avatar)
    language_bank = brand_file("language_bank", avatar)
    for name, val in (("avatar profile", avatar_profile),
                      ("language_bank", language_bank),
                      ("offer_file", offer_file)):
        if not val and not dry:
            print(f"     NOTE: no {name} found for {args.brand} — stages run without it")
    save()

    def lang(stage, topics=None, limit=40):
        """The rows THIS stage needs — queried, never a truncated file."""
        if not roster:
            return "(this brand has no language bank)"
        return L.for_stage(args.brand, stage, avatar, funnel, topics,
                           limit, BRAND_TREE)

    record = run_stage("stage1", out_dir, args.model, state,
                       today=today, triage=triage, source=source,
                       awareness_levels=doctrine("awareness"),
                       delivery=doctrine("delivery")); save()
    # THE VIBE (2026-09-28): how the source feels, named at the read and
    # handed to every stage that writes — a funny source stays funny.
    vibe = vibe_of(record)

    spec = run_stage("stage2", out_dir, args.model, state,
                     today=today, triage=triage, record=record); save()

    # what the brand knows, and which of it THIS source needs
    always = {args.product,
              f"brands/{args.brand}/customer/avatar.md",
              f"brands/{args.brand}/customer/language-bank.md",
              f"brands/{args.brand}/offers/offer-bank.md"}
    scout = run_stage("stage1b", out_dir, args.model, state,
                      today=today, concept_brief=f"{triage}\n\n{spec}",
                      context_index=context.index(args.brand, always=always),
                      always_loaded="\n".join(f"- {p}" for p in sorted(always))); save()
    picked = [p for p in context.parse_choice(scout) if p not in always]
    brand_context, used, dropped = context.load(picked)
    state["context"] = {"picked": picked, "chars": used, "dropped": dropped}
    if dry and not will_reuse("stage1b", out_dir):
        brand_context = f"{DRY_MARK} (the files stage 2b picks, up to 90,000 chars)"
    else:
        print(f"     context: {len(picked)} file(s), {used:,} chars"
              + (f", {len(dropped)} dropped" if dropped else ""))
    save()

    # --- make it ours ------------------------------------------------------
    injection = run_stage("stage3", out_dir, args.model, state,
                          language=lang("injection"),
                          today=today, triage=triage, spec=spec, record=record,
                          avatar=avatar_profile, language_bank=language_bank,
                          product_file=product_file, offer_file=offer_file,
                          brand_context=brand_context, brand_name=args.brand,
                          vibe=vibe); save()

    placement = run_stage("stage4", out_dir, args.model, state,
                          today=today, triage=triage, injection=injection, spec=spec,
                          product_file=product_file, offer_file=offer_file); save()

    hooks = run_stage("stage5", out_dir, args.model, state,
                          language=lang("hooks"),
                      today=today, triage=triage, record=record, spec=spec,
                      injection=injection, placement=placement,
                      language_bank=language_bank, brand_context=brand_context,
                      hook_count=args.hooks, vibe=vibe,
                      awareness_levels=doctrine("awareness")); save()

    # THE LIVE RESEARCH GATHERER (Damon, 2026-09-18: "the live research gatherer
    # runs in the copy machine too"). Resolved ONCE, here, because stages 6 and
    # 7 both read it and a second pull would be a second bill for the same
    # answer. The rooms are FOUND, not written down — nobody types a subreddit
    # into an avatar file for this to work. Wrapped so a research gap is a
    # section that says so, never a stopped run: the shim never raises, and
    # this catches even the import going wrong.
    # Three ways it is NOT pulled (2026-09-20): a dry run spends nothing; a
    # rerun that keeps both stage 6 and stage 7 has no reader for it; and a
    # rerun whose earlier pull is still on disk reads that back.
    research_text = "[UNFILLED: research gatherer not available]"
    kept_research = out_dir / "research" / "research.md"
    readers = [k for k in ("stage6", "stage7") if not will_reuse(k, out_dir)]
    if dry:
        research_text = f"{DRY_MARK} (gathered live in a real run — not pulled in a dry run)"
    elif not readers:
        research_text = ""
        print("     research: not pulled — stages 6 and 7 are both kept")
    elif RERUN_FROM and kept_research.is_file():
        research_text = kept_research.read_text()
        print(f"     research: kept from the earlier run ({len(research_text):,} chars)")
    else:
        try:
            import research as RS
            research_text = RS.text_for(
                brand=args.brand, avatar=avatar, funnel=funnel,
                source_url=(source_reference if str(source_reference).startswith("http") else None),
                out_dir=out_dir, slug=label)
        except Exception as e:
            print(f"     research: UNAVAILABLE ({e}) — stages 6 and 7 run without it")
        print(f"     research: {len(research_text or ''):,} chars -> {out_dir.name}/research/")
    state["research"] = {"chars": len(research_text or ""),
                        "unfilled": "[UNFILLED: research gatherer not available]" in (research_text or "")}
    save()

    # Gated exactly the way the video chain gates it: an already-DR source has
    # its commercial structure inherited, so building one again is adding a
    # second argument on top of a working one.
    body = injection
    # A dry run has no triage answer, so it cannot know the lane: it checks
    # stage 6 anyway, because an ORGANIC source will need it.
    if lane == "ORGANIC" or (dry and lane is None):
        body = run_stage("stage6", out_dir, args.model, state,
                          language=lang("expansion"), research=research_text,
                         today=today, triage=triage, spec=spec, injection=injection,
                         placement=placement, product_file=product_file,
                         offer_file=offer_file, language_bank=language_bank,
                         brand_context=brand_context,
                         sections=doctrine("sections"), techniques=doctrine("techniques"),
                         vibe=vibe); save()
        if dry and lane is None and DRY and not DRY[-1].get("reused"):
            DRY[-1]["note"] = "runs only when triage reads the lane as ORGANIC — checked here either way"
    else:
        state["stages"]["stage6"] = {
            "status": "skipped",
            "why": f"lane is {lane or 'unread'} — the source already carries commercial "
                   "structure, so it was inherited at injection rather than rebuilt",
        }
        print(f"     stage6 skipped — lane {lane or 'unread'}")
        save()

    close = run_stage("stage7", out_dir, args.model, state,
                          language=lang("close"), research=research_text,
                      today=today, triage=triage, body=body, spec=spec,
                      placement=placement, product_file=product_file,
                      offer_file=offer_file, language_bank=language_bank,
                      brand_context=brand_context,
                      offer_close=doctrine("offer-close"), vibe=vibe,
                      verification=doctrine("verification")); save()

    # --- write the copy ----------------------------------------------------
    # The argument is finished; now it becomes an object. Everything before
    # this is medium-free on purpose.
    state["output_formats"] = args.write_as
    state["channel"] = args.channel
    if not dry:
        print(f"     writing as: {args.write_as}  ({args.channel})")
    # THE RECORD GOES TO RENDER (2026-08-31, Damon's finals). Stage 1 captures
    # the voice markers and calls them "the most load-bearing section on the
    # page" — and stage 8 was never given them. The writing stage had the
    # argument (injection, placement, hooks) and not the person, which is
    # exactly how copy comes out correct and anonymous.
    render = run_stage("stage8", out_dir, args.model, state,
                          language=lang("render"),
                       today=today, triage=triage, spec=spec, injection=close,
                       record=record, placement=placement, hooks=hooks,
                       product_file=product_file, offer_file=offer_file,
                       language_bank=language_bank, brand_context=brand_context,
                       formats=formats, output_formats=args.write_as,
                       channel=args.channel, vibe=vibe); save()

    # THE COPY GATE (2026-09-20) — see copy_gate(). A held run keeps every
    # file it made and says why; what it does NOT get is the brief, because
    # the brief is the act of handing the copy on.
    held = None
    if dry:
        pass
    elif args.no_gate:
        state["gate"] = {"copy": "skipped on purpose (--no-gate)"}
        print("     copy gate: SKIPPED (--no-gate)")
    else:
        import quality_checks as Q
        try:
            copy_gate(render, offer_file, out_dir)
            state["gate"] = {"copy": "pass"}
            print("     copy gate: pass")
        except Q.Held as e:
            held = e
            state["gate"] = {"copy": "HELD", "problems": e.problems}
    save()
    if held:
        state["stages"]["stage9"] = {
            "status": "error", "held": True,
            "why": "held at the copy gate — " + "; ".join(held.problems)}
        save()
        print(f"\n{held}")
        print(f"\nEverything up to the copy is saved in {out_dir}; check.json has the reasons.\n"
              "Fix the offer bank or the copy, then rerun with --rerun-from stage8 "
              "(write it again) or --rerun-from stage9 --no-gate (pass it on purpose).")
        _rebuild_board()
        sys.exit(2)

    run_stage("stage9", out_dir, args.model, state,
              today=today, triage=triage, full_piece=render, hooks=hooks,
              placement=placement, source_reference=source_reference,
              offer_file=offer_file); save()

    if dry:
        for r in DRY:
            for name, status, _, why in r.get("fields", []):
                if status == "UNFILLED":
                    problems.append(f"{r['stage']} ({r['prompt']}): {{{name}}} — {why}")
                elif status == "EMPTY" and name in MACHINE_FIELDS:
                    problems.append(f"{r['stage']}: {{{name}}} is empty")
                elif status == "EMPTY":
                    warnings.append(f"{r['stage']}: {{{name}}} is empty — the stage runs without it")
        print_dry(DRY, problems, sorted(set(warnings)))
        return 1 if problems else 0

    print(f"\ndone -> {out_dir}/stage9--brief.md")
    _rebuild_board()
    return 0


# Fields the MACHINE owns — empty means this build is broken, not that a brand
# is young. Everything else empty is a brand gap and only a warning.
MACHINE_FIELDS = {"today", "source", "formats", "avatars", "product_file", "awareness_levels",
                  "sections", "techniques", "offer_close", "verification", "output_formats",
                  "channel", "hook_count", "context_index", "always_loaded", "brand_name",
                  "source_reference"}


def _rebuild_board():
    # Rebuild the page here, not later. A board that only refreshes when
    # somebody remembers to refresh it is a board that shows yesterday, and
    # a stale board is worse than none — it gets read as current.
    try:
        import board
        board.build()
        print(f"board -> {board.OUT.relative_to(HERE)}  (rebuilt)")
    except Exception as e:
        print(f"board NOT rebuilt ({e}) — run `python3 board.py` before reading it")


def cli(argv=None):
    """One clear line for an account out of usage — never a traceback, never
    three retries (claude() raises it on the first refusal)."""
    try:
        return main(argv)
    except UsageLimit as e:
        sys.exit(f"USAGE LIMIT — the run stopped, nothing is broken: {e}\n"
                 "Every finished stage is saved; pick it up later with --rerun-from <the stage it stopped at>.")


if __name__ == "__main__":
    sys.exit(cli())
