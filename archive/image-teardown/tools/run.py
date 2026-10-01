#!/usr/bin/env python3
"""Run the image chain. One stage per call, so every output gets read.

    run.py <run> 1          teardown        the ad in, an objective record out
    run.py <run> 2          the format      brand-free, in words and as data
    run.py <run> 2b         the labels      which library elements the ad IS
    run.py <run> 3          injection       our brand through that format
    run.py <run> 4          headlines       six, each on its own axis
    run.py <run> 5          variations      the pictures worth generating
    run.py <run> 6          the brief       everything, before anyone builds
    run.py <run> all        1 through 6
    run.py <run> 3,4        several, in order

    run.py <run> 4 --brand <brand>
    run.py <run> all --brand <brand> --dry-run     resolve everything, call nothing

**The dry run spends nothing.** It resolves every stage's prompt and every
file and variable the stage would be handed, says OK or MISSING per stage, and
never starts a runner — no Gemini, no claude, no language query.

**Two gates hold failing work** (`gates.py`): the elements gate after 2b, the
copy gate after 6. A held run writes `check.json` saying why. `--gates warn`
records the same verdict and carries on.

**Every run files its record** to `runs/image-teardown/<brand>/<label>/` at
the repo root when its stages finish — held or not.

**Reads only from the lab.** Every path comes from `paths.py`; nothing here
reaches into another repo. The language rows are queried per stage from the
brand's own layer rather than handed over as one flat file, so a headline pass
sees the sentences people actually open with and a closing pass sees buying
reasons.
"""

import argparse, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
import elements_label as EL
import gates as G

# Which model does which half of the work, ruled 2026-08-28.
#   Gemini reads the picture and writes the record — stages 1 and 2.
#   Claude does the brand-side thinking — stages 3 to 6 — the same split the
#   video and copy chains already run.
GEMINI = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
# A model id written here went stale (`claude-opus-4-6`, long after it was the
# current one). The Claude stages now name a TIER — what kind of work the
# stage is — and the id comes from components/run-kit `model.TIERS`, the one
# place the ids are kept. CLAUDE_MODEL in the environment still forces one.
CLAUDE = os.environ.get("CLAUDE_MODEL")
ENGINE = {"1": "gemini", "2": "gemini", "2b": "claude",
          "3": "claude", "4": "claude", "5": "claude", "6": "claude"}
TIER = {"2b": "checks",                       # applies lists that are written down
        "3": "designs", "4": "designs", "5": "designs", "6": "designs"}


def model_for(stage):
    """(model id, why) for one stage."""
    if ENGINE[stage] == "gemini":
        return GEMINI, "gemini reads the picture"
    if str(P.RUN_KIT) not in sys.path:
        sys.path.insert(0, str(P.RUN_KIT))
    from run_kit import model as M
    return M.pick(TIER[stage], forced=CLAUDE)


# stage → (prompt glob, output name, the language stage to query, extra vars)
STAGES = {
    "1": ("stage1-image-teardown*",     "01-teardown.md",         None,        []),
    "2": ("stage2-image-replication*",  "02-replication-spec.md", None,        []),
    "2b": ("stage2b-image-elements*",   EL.ANSWER,                None,        []),
    "3": ("stage3-image-injection*",    "03-injection.md",        "injection", []),
    "4": ("stage4b-image-hook*",        "04-headlines.md",        "hooks",     []),
    "5": ("stage4e-image-variations*",  "05-image-variations.md", "hooks",     []),
    "6": ("stage6-image-brief*",        "06-brief.md",            None,        []),
}


VERSION = re.compile(r"-v(\d+)[-.]")


def version_of(path):
    m = VERSION.search(Path(path).name)
    return int(m.group(1)) if m else 0


def prompt_for(stage, folder=None):
    """The highest -vN- wins, and N is a NUMBER. Sorted as text, `-v10-` loses
    to `-v2-` — the tenth version of a prompt would silently never run. Same
    rule as components/run-kit `prompts.latest`; the glob stays this lane's
    own (top level only, so `superseded/` and `parked/` never compete)."""
    folder = Path(folder or P.PROMPTS)
    hits = sorted(folder.glob(STAGES[stage][0]), key=lambda f: (version_of(f), f.name))
    if not hits:
        sys.exit(f"no prompt for stage {stage} in {folder}")
    return hits[-1]


def language(brand, stage, run):
    """Query the brand's language layer for this stage and cache it in the run."""
    out = run / "out" / f".language-{stage}.md"
    # The language layer resolves brands from AI_WORKSPACE. Brand truth left
    # the lab for the repo root on 2026-09-02, so pointing this at the lab
    # returned "no rows matched" — silently, with the stage carrying on
    # without a word of customer language in it.
    env = dict(os.environ, AI_WORKSPACE=str(P.BRANDS.parent))
    r = subprocess.run([sys.executable, str(P.LANGUAGE), "--brand", brand,
                        "--stage", stage], capture_output=True, text=True, env=env)
    if r.returncode != 0 or "no rows matched" in r.stdout:
        print(f"  ! language layer returned nothing for {brand}/{stage}")
        return None
    out.write_text(r.stdout)
    n = r.stdout.count('\n- "')
    print(f"  language: {n} rows tagged {stage}")
    return out


def swipe_angle(run):
    """The swipe library's own record of the angle this ad ran under.

    `assets/source.json` names the block the creative came from; the block
    file is the angle as its own brand wrote it — headline, primary text,
    how many times they rebuilt it.
    """
    import json as _json
    f = run / "assets/source.json"
    if not f.is_file():
        return run / "assets/source.json"          # missing → reported by the caller
    src = _json.loads(f.read_text())
    # Paid keeps its angles in blocks/, organic keeps its posts in posts/.
    # Looking only in the paid library left stage 6 with no swipe_angle for
    # every organic run, and nine <brand> runs finished five stages and then
    # produced no brief at all (2026-09-14).
    for lib, sub in ((P.SWIPE, "blocks"), (P.SWIPE_ORGANIC, "posts")):
        q = lib / str(src.get("swipe", "")) / sub / str(src.get("block_file", ""))
        if q.is_file():
            return q
    return P.SWIPE / str(src.get("swipe", "")) / "blocks" / str(src.get("block_file", ""))



def roster_or_note(b, run):
    """The brand's roster, or a written note that it has none.

    Not every brand casts — one of ours deliberately does not. Passing a
    missing path made the runner exit and wait for a person, which is the one
    thing this chain must never do.
    """
    f = b["cast"] / "roster.json"
    if f.is_file():
        return f
    note = run / "out" / ".no-roster.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "This brand has no casting roster.\n\n"
        "Cast nobody. Write `none` for the subject unless the format cannot "
        "exist without a person in it — and if it cannot, say so plainly and "
        "describe the role rather than a named man.\n")
    return note



class Missing(str):
    """An input that could not be resolved — carries the reason instead of a path."""


def later(why):
    """Dry run only: an input that does not exist yet and is not meant to —
    the run itself writes it (an earlier stage's output, the language rows)."""
    p = Missing(why)
    p.ok = True
    return p


def inputs_for(run, stage, brand, avatar, product, dry=False, planned=()):
    """Every variable a stage is handed, as {name: path}.

    The live path and the dry run share this, so the dry run reports the very
    list the stage would get. `dry` changes one thing: nothing is written and
    nothing is started — an input the run will make for itself is reported as
    such instead of being made.
    """
    b = P.brand(brand)
    o = run / "out"
    v = {}

    def made_by(name, by):
        f = o / name
        if dry and not f.exists() and by in planned:
            return later(f"made by stage {by} in this run")
        return f

    def own(rel, why):
        f = run / rel
        if dry and not run.is_dir():
            return later(why)
        return f

    def guarded(fn, *args):
        if not dry:
            return fn(*args)
        try:
            return fn(*args)
        except SystemExit as e:                     # "name one with --avatar"
            return Missing(str(e))

    if stage == "1":
        # MARKET STATE (2026-09-18): the chain has no 1b, so stage 1 is the
        # only place that can name the ad's own awareness rung, sophistication
        # stage and lead desire — bound from the doctrine, never restated here.
        v["awareness_levels"] = P.DOCTRINE / "awareness.md"
        v["sophistication_stages"] = P.DOCTRINE / "sophistication.md"
        v["desire_dimensions"] = P.DOCTRINE / "desire.md"
        return v

    # every text stage reads what came before it
    v["teardown_record"] = made_by("01-teardown.md", "1")
    if stage == "2b":
        # The candidate rows come out of the element library at run time, so
        # the prompt never carries a list that can go stale.
        v["element_candidates"] = (later("rendered from components/elements/library at run time")
                                   if dry else EL.write_candidates(run))
        if dry:
            EL.candidates()                          # proves the library answers
    if stage >= "3":
        v["replication_spec"] = made_by("02-replication-spec.md", "2")
    if stage in ("4", "5", "6"):
        v["baseline_injection" if stage in ("4", "5") else "brand_injection"] = \
            made_by("03-injection.md", "3")
    if stage in ("5", "6"):
        v["hook_set"] = made_by("04-headlines.md", "4")
    if stage == "6":
        v["image_variations"] = made_by("05-image-variations.md", "5")
    if stage in ("3",):
        v["brand_name"] = own("vars/brand_name.md", "written when the run opens")
        v["production_route"] = own("vars/production_route.md", "written when the run opens")
        v["avatar"] = guarded(P.avatar_profile, brand, avatar)
        v["product_file"] = P.product(brand, product) if product else Missing("no --product given")
        v["offer_file"] = b["offer"]
        v["identity_anchors"] = b["identity"]
        # Who actually exists. Without it the injection described men the
        # roster does not have — "a Black man in his early 30s" when no such
        # man is free — and the substitution happened later, by hand, silently
        # (2026-09-13, p006).
        if dry and not (b["cast"] / "roster.json").is_file():
            v["roster"] = later("this brand has no roster — a cast-nobody note is written at run time")
        else:
            v["roster"] = roster_or_note(b, run)
        v["palette"] = b["palette"]
    if stage == "4":
        v["avatar"] = guarded(P.avatar_profile, brand, avatar)
        v["hook_ledger"] = b["hook_ledger"]
        v["identity_anchors"] = b["identity"]
        # THE RUNG TEST checks every headline against its entry rung's
        # must-not — bound from the doctrine, not restated in the prompt.
        v["awareness_levels"] = P.DOCTRINE / "awareness.md"
    if stage == "5":
        v["product_file"] = P.product(brand, product) if product else Missing("no --product given")
    if stage == "6":
        # The prompt has always told stage 6 to take the angle from the
        # brand's own angle bank. Nothing passed it the bank, so every brief
        # wrote `unsigned` — not because no angle fitted, but because the
        # model could not see nineteen signed angles sitting in the repo
        # (found 2026-09-13, after four briefs in a row said unsigned).
        v["angle_source"] = P.BRANDS / brand / "strategy/angles.json"
        # The registers the prompt names. Naming a file it is never handed is
        # how stage 6 wrote "[VERIFY against style-packs.json]" into seven
        # briefs out of nine, and invented two pack names in the other two —
        # the same fault as the angle bank a day earlier (2026-09-14).
        v["style_packs"] = P.LAB / "image-production/style-packs.json"
        # Their angle, in their words. The swipe library has named every one
        # of them, with clone counts and the verbatim copy — and no stage had
        # ever been handed one, so the chain judged a competitor's argument
        # off the picture alone (2026-09-13).
        v["swipe_angle"] = (later("resolved from assets/source.json when the run opens")
                            if dry and not run.is_dir() else swipe_angle(run))
        v["brand_name"] = own("vars/brand_name.md", "written when the run opens")
        v["product_file"] = P.product(brand, product) if product else Missing("no --product given")
        v["offer_file"] = b["offer"]
        v["palette"] = b["palette"]
        # Technique per element in the brief — bound from the doctrine.
        v["techniques"] = P.DOCTRINE / "techniques.md"
    return v


def is_missing(p):
    if isinstance(p, Missing):
        return not getattr(p, "ok", False)
    return not Path(p).exists()


def wants_of(stage):
    return set(re.findall(r"\{([a-z_]+)\}", prompt_for(stage).read_text()))


def source_image(run):
    a = run / "assets"
    if not a.is_dir():
        return None
    return next((p for p in a.iterdir()
                 if p.stem == "source" and p.suffix.lower() in (".jpg", ".png")), None)


def run_stage(run, stage, brand, avatar, product, gates="hold"):
    b = P.brand(brand)
    o = run / "out"
    o.mkdir(parents=True, exist_ok=True)
    glob_, name, lang_stage, _ = STAGES[stage]

    if stage == "1":
        src = source_image(run)
        if not src:
            sys.exit(f"no assets/source.* in {run} — open it with swipe_intake.py")
        cmd = [sys.executable, str(P.GEMINI_IMAGE), "--prompt-file", str(prompt_for("1")),
               "--image", str(src)]
        for k, p in inputs_for(run, "1", brand, avatar, product).items():
            cmd += ["--var", f"{k}={p}"]
        cmd += ["--out", str(o / name)]
        print(f"  source: {src.name}")
        subprocess.run(cmd, check=True)
        return o / name

    # A run held at the elements gate does not go on to the brand-side
    # stages: the hold is the point of the gate. Re-run 2b, or pass
    # `--gates warn` to carry on with the verdict still on the record.
    if gates == "hold" and stage >= "3":
        h = G.held(run, ["elements"])
        if h:
            sys.exit(f"{run.name} is HELD at the elements gate — stage {stage} not run:\n  "
                     + "\n  ".join(h["elements"]))

    v = inputs_for(run, stage, brand, avatar, product)

    if lang_stage:
        got = language(brand, lang_stage, run)
        if got:
            v["language_bank"] = got

    # A ledger that does not exist yet means "no hooks spent", not "stop".
    # A brand's first run has no history to avoid repeating, and refusing to
    # start until someone hand-creates an empty file is a gate with nothing
    # behind it.
    ledger = v.get("hook_ledger")
    if ledger and not Path(ledger).exists():
        Path(ledger).parent.mkdir(parents=True, exist_ok=True)
        Path(ledger).write_text(
            f"# {brand} hook ledger\n\n"
            "Opened by the chain on its first run for this brand — empty "
            "because nothing has been generated yet. Stage 4 reads it before "
            "writing: a verbatim already mapped to a hook here is spent.\n\n"
            "| verbatim | hook | status | run |\n|---|---|---|---|\n")
        print(f"  opened a hook ledger for {brand} — first run")

    missing = [k for k, p in v.items() if is_missing(p)]
    if missing:
        sys.exit(f"stage {stage} is missing: " + ", ".join(missing))

    # Every {placeholder} the prompt names must be supplied, or the runner
    # fails deep inside a subprocess and reports a wall of shell arguments
    # instead of the one word that is wrong. Check it here, say it plainly.
    unmet = sorted(wants_of(stage) - set(v))
    if unmet:
        sys.exit(f"stage {stage} prompt asks for {', '.join(unmet)} — "
                 f"nothing supplies it. Either the runner owes it or the "
                 f"prompt should stop asking.")

    engine = ENGINE[stage]
    runner = P.CLAUDE_TEXT if engine == "claude" else P.GEMINI_TEXT
    model, _why = model_for(stage)
    cmd = [sys.executable, str(runner), "--model", model,
           "--prompt-file", str(prompt_for(stage))]
    if stage == "2b":
        cmd += ["--min-chars", "120"]      # four ids and four reasons is a short, whole answer
    for k, p in v.items():
        cmd += ["--var", f"{k}={p}"]
    cmd += ["--out", str(o / name)]
    subprocess.run(cmd, check=True)

    if stage == "2b":
        # THE ELEMENTS GATE. The answer is read by code and every id is asked
        # of the element library. What the library does not hold is refused
        # and written down — never swapped for the nearest thing.
        rec, problems = EL.read(run, prompt_for("2b").name)
        kept = ", ".join(f"{k}={i}" for k, i in rec["labels"].items()) or "none"
        print(f"  labels: {kept}")
        G.elements_gate(run, problems, gates)
    if stage == "6":
        # THE COPY GATE, on the one document that gets built from.
        G.copy_gate(run, brand, product, gates)
    return o / name


def dry_stage(run, stage, brand, avatar, product, planned):
    """One stage, resolved and reported. Starts nothing. Returns the MISSING names."""
    model, why = model_for(stage)
    print(f"\n[{stage}] {LABEL[stage]}  ·  {ENGINE[stage]}  ·  {model}  ({why})")
    rows = []
    try:
        pf = prompt_for(stage)
        rows.append(("prompt", pf.name, True))
        wants = set(re.findall(r"\{([a-z_]+)\}", pf.read_text()))
    except SystemExit as e:
        rows.append(("prompt", str(e), False))
        wants = set()
    if stage == "1":
        src = source_image(run)
        if src:
            rows.append(("image", src.name, True))
        elif not run.is_dir():
            rows.append(("image", "copied in when the run opens", True))
        else:
            rows.append(("image", f"no assets/source.jpg|png in {run.name}", False))
    try:
        v = inputs_for(run, stage, brand, avatar, product, dry=True, planned=planned)
    except Exception as e:                                   # the library not answering, say
        v = {}
        rows.append(("inputs", f"{type(e).__name__}: {e}", False))
    lang_stage = STAGES[stage][2]
    if lang_stage:
        ok = P.LANGUAGE.is_file()
        v_lang = (f"queried at run time ({brand}/{lang_stage})" if ok
                  else f"language tool missing at {P.LANGUAGE}")
        rows.append(("language_bank", v_lang, ok))
        if ok:
            wants.discard("language_bank")
    for k, p in v.items():
        if k == "hook_ledger" and not isinstance(p, Missing) and not Path(p).exists():
            rows.append((k, "none yet — opened empty on this brand's first run", True))
            continue
        if isinstance(p, Missing):
            rows.append((k, str(p), not is_missing(p)))
        else:
            try:
                shown = str(Path(p).relative_to(P.REPO))
            except ValueError:
                shown = str(p)
            rows.append((k, shown, Path(p).exists()))
    for k in sorted(wants - set(v)):
        rows.append((k, "the prompt asks for it and nothing supplies it", False))
    bad = []
    for k, shown, ok in rows:
        print(f"    {'OK     ' if ok else 'MISSING'}  {k:<22} {shown}")
        if not ok:
            bad.append(k)
    print(f"    → stage {stage}: " + ("OK" if not bad else "MISSING " + ", ".join(bad)))
    return bad


def dry_run(runs, stages, brand, avatar, product):
    """Resolve everything, call nothing. Returns the exit code."""
    print("DRY RUN — no model is called, nothing is written, nothing is spent")
    total = {}
    for run in runs:
        print(f"\n======== {run.name}" + ("" if run.is_dir() else "   (not opened yet)"))
        h = G.held(run) if run.is_dir() else {}
        for g, probs in h.items():
            print(f"    held at the {g} gate: " + "; ".join(probs))
        for s in stages:
            bad = dry_stage(run, s, brand, avatar, product, planned=stages)
            if bad:
                total.setdefault(run.name, []).append(f"stage {s}: {', '.join(bad)}")
        print(f"\n    would file to {(P.RECORDS / brand / run.name).relative_to(P.REPO)}/")
    print()
    if not total:
        print(f"dry run OK · {len(runs)} run{'s' if len(runs) != 1 else ''} · "
              f"stages {', '.join(stages)} · 0 model calls")
        return 0
    for name, lines in total.items():
        for l in lines:
            print(f"MISSING  {name}  {l}")
    return 1


LABEL = {"1": "teardown", "2": "the format", "2b": "element labels", "3": "injection",
         "4": "headlines", "5": "picture variations", "6": "the brief"}


def one_run(run, stages, brand, avatar, product, quiet=False, gates="hold"):
    """Every stage for one run, in order — stage n reads stage n-1.

    Whatever happens, the record is filed to runs/image-teardown/<brand>/ at
    the repo root on the way out: a run that stopped at a gate files its
    check.json with it, which is how a held run says why."""
    done = []
    try:
        for s in stages:
            if not quiet:
                print(f"\n[{s}] {LABEL[s]}  ·  {ENGINE[s]}")
            out = run_stage(run, s, brand, avatar, product, gates)
            done.append(out)
            if not quiet:
                print(f"  → {out.relative_to(P.LAB)}")
    finally:
        if (run / "out").is_dir() and any((run / "out").glob("0*.md")):
            dst = G.file_record(brand, run.name)
            if not quiet:
                print(f"\n  filed → {dst.relative_to(P.REPO)}")
    return done


def stage_list(text):
    """`all`, one stage, or several separated by commas — always run in chain order."""
    if text == "all":
        return list(STAGES)
    asked = [x.strip() for x in text.split(",") if x.strip()]
    bad = [x for x in asked if x not in STAGES]
    if bad or not asked:
        raise argparse.ArgumentTypeError(
            f"no stage {', '.join(bad) or text!r} — choose from {', '.join(STAGES)}, or all")
    return [s for s in STAGES if s in asked]


def main():
    ap = argparse.ArgumentParser()
    # Several runs at once: the stages inside a run depend on each other, but
    # two runs do not depend on each other at all. Four briefs re-run one
    # after another took an hour on 2026-09-13 when they could have taken
    # fifteen minutes — the team runs batches of swipes, so this is the
    # normal case, not the exception.
    ap.add_argument("run", help="one run, or several separated by commas")
    ap.add_argument("stage", type=stage_list,
                    help="one stage, several separated by commas, or all")
    ap.add_argument("--brand", required=True,
                    help="the brand folder under brands/ — no default, for the "
                         "same reason avatar and product have none")
    # No brand's avatar or product is the default. Defaulting to one brand's
    # meant every other brand's run silently aimed at the wrong person and
    # described the wrong thing — the brand-agnostic rule broken by a
    # default value.
    ap.add_argument("--avatar", help="the core avatar's folder name")
    ap.add_argument("--product", help="the product's slug")
    ap.add_argument("--serial", action="store_true",
                    help="one run at a time, for reading the output as it goes")
    ap.add_argument("--dry-run", "--dry", dest="dry_run", action="store_true",
                    help="resolve every prompt, file and variable and say OK or "
                         "MISSING per stage — calls no model, writes nothing")
    ap.add_argument("--gates", choices=G.MODES, default="hold",
                    help="hold (default): a failed gate stops the run. warn: the "
                         "same verdict is written to check.json and the run carries on")
    a = ap.parse_args()

    runs = []
    for name in [x.strip() for x in a.run.split(",") if x.strip()]:
        run = Path(name)
        if not run.is_absolute():
            run = P.RUNS / run.name if run.parent.name == "runs" else P.RUNS / str(run)
        # A dry run may be asked about a run that has not been opened yet —
        # `chain.py start --dry-run` names the runs it WOULD open.
        if not run.is_dir() and not a.dry_run:
            sys.exit(f"no run at {run}")
        runs.append(run)

    stages = a.stage

    if a.dry_run:
        sys.exit(dry_run(runs, stages, a.brand, a.avatar, a.product))

    if len(runs) == 1 or a.serial:
        Held = G.quality().Held
        stopped = []
        for run in runs:
            if len(runs) > 1:
                print(f"\n======== {run.name}")
            try:
                one_run(run, stages, a.brand, a.avatar, a.product, gates=a.gates)
            except Held as e:
                stopped.append(run.name)
                print(f"\n✗ {run.name}: {e}\n  why is on file: "
                      f"{(run / 'check.json').relative_to(P.LAB)}")
        if stopped:
            sys.exit(3)
        return

    # Parallel: each stage is a subprocess waiting on a model, so threads are
    # the right shape. Output is held per run and printed whole, because
    # interleaved progress from four runs is unreadable.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    print(f"{len(runs)} runs · stages {', '.join(stages)} · in parallel")
    with ThreadPoolExecutor(max_workers=len(runs)) as pool:
        jobs = {pool.submit(one_run, r, stages, a.brand, a.avatar, a.product,
                            True, a.gates): r for r in runs}
        for f in as_completed(jobs):
            run = jobs[f]
            try:
                outs = f.result()
            except Exception as e:                       # one run failing is
                print(f"\n✗ {run.name}: {e}")            # not the others' problem
                continue
            print(f"\n✓ {run.name}")
            for o in outs:
                print(f"    {o.relative_to(P.LAB)}")


if __name__ == "__main__":
    main()
