#!/usr/bin/env python3
"""Run the image chain. One stage per call, so every output gets read.

    run.py <run> 1          teardown        the ad in, an objective record out
    run.py <run> 2          the format      brand-free, in words and as data
    run.py <run> 2b         the labels      which library elements the ad IS
    run.py <run> 3          injection       our brand through that format       } the writing station,
    run.py <run> 4          headlines       every line for the swapped picture  } tools/image-writing:
    run.py <run> 5          variations      the brief's five, as data           } handed off at step 3
    run.py <run> 6          the brief       everything, before anyone builds    }
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

**The records are this component's; the writing is not.** Steps 1, 2 and 2b
(and the swipe's dial read) are the teardown's own. Steps 3 to 6 live in
tools/image-writing (split out 2026-10-27, as video-writing left
video-teardown): their prompts, their inputs and what each does once its
answer is on file. This file stays the one engine and the one door: it hands
each writing step to `image-writing/tools/writing.py`, passing itself, and the
writing step writes into this same run.

**Reads only from the workspace.** Every path comes from `paths.py`; nothing here
reaches into another repo. The language rows are queried per stage from the
brand's own layer rather than handed over as one flat file, so a headline pass
sees the sentences people actually open with and a closing pass sees buying
reasons.
"""

import argparse, json, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
import elements_label as EL
import gates as G


def _writing():
    """The writing station (tools/image-writing/tools/writing.py), loaded once by path."""
    import importlib.util
    name = "image_writing_writing"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, str(P.WRITING_TOOLS / "writing.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


W = _writing()
ENGINE_SELF = sys.modules[__name__]                  # what every writing step is handed as its engine

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
ENGINE = {"1": "gemini", "1k": "gemini", "2": "gemini", "2b": "claude", **W.ENGINE}
TIER = {"2b": "checks", **W.TIER}             # 2b applies lists that are written down


def model_for(stage):
    """(model id, why) for one stage."""
    if ENGINE[stage] == "gemini":
        return GEMINI, "gemini reads the picture"
    if str(P.RUN_KIT) not in sys.path:
        sys.path.insert(0, str(P.RUN_KIT))
    from run_kit import model as M
    return M.pick(TIER[stage], forced=CLAUDE)



def file_letterforms(run):
    """What this teardown used from the bank, and what it had to name itself.

    Written beside the stage output so a proposed row is findable rather than
    buried in nine thousand characters of prose. `letterforms.json` travels
    with the filed record; `python3 tools/letterforms.py` lists every
    proposal across every run, which is the list the owner signs from.
    """
    got = EL.letterforms_used(run)
    if not (got["used"] or got["proposed"]):
        return None
    f = Path(run) / "out" / "letterforms.json"
    f.write_text(json.dumps(got, indent=1) + "\n")
    if got["proposed"]:
        print("  letterform · proposed " + str(len(got["proposed"])) + " new row(s) — "
              "not in the bank yet, the run carried on:")
        for x in got["proposed"]:
            print("      " + x[:96])
    if got.get("unknown_ids"):
        print("  letterform · WROTE IDS THE BANK DOES NOT HOLD: "
              + ", ".join(got["unknown_ids"]) + " — none-fits was the right answer")
    return f


# stage → (prompt glob, output name, the language stage to query, extra vars)
# The records — this component's own steps.
RECORDS = {
    "1": ("stage1-image-teardown*",     "01-teardown.md",         None,        []),
    # the culture read (components/culture, shared with video, 2026-10-27): slang, double meanings, references, the joke
    "1k": ("stage1k-culture*",          "01k-culture.md",         None,        []),
    "2": ("stage2-image-replication*",  "02-replication-spec.md", None,        []),
    "2b": ("stage2b-image-elements*",   EL.ANSWER,                None,        []),
}
# The whole chain in order: the records, then the writing station's 3 to 6 (image-writing `STAGES`).
STAGES = {**RECORDS, **W.STAGES}


VERSION = re.compile(r"-v(\d+)[-.]")


def version_of(path):
    m = VERSION.search(Path(path).name)
    return int(m.group(1)) if m else 0


# THE BRANCH (the owner 2026-09-15 / 2026-09-22; TEARDOWN-CHAINS.md). A run is
# opened on a route (who makes it: ai · creator) and a form (what it is:
# single · sequence), written to vars/route.json by chain.py. Two stages read
# it: stage 1 reads a sequence slide by slide, and stage 6 — the brief, the one
# document a maker opens — branches by who that maker is. Every other stage is
# identical on every branch, the way the video chain's stage 5 branches while
# stages 0–4 do not. A run opened before the branch existed carries no file
# and is the AI single route: byte-identical to what it always was.
BRANCH_PROMPTS = {
    ("1", "single"):   "stage1-image-teardown*",
    ("1", "sequence"): "stage1-sequence-teardown*",
    **W.BRANCH,                                   # stage 6, by route × form: the writing station's
}


def prompts_dir(stage):
    """Where a stage's prompts live: the records' here, the writing station's in tools/image-writing."""
    if stage == "1k":
        return P.REPO / "components" / "culture" / "prompts"     # one culture read for video and pictures
    return W.PROMPTS if stage in W.STAGES else P.PROMPTS


# A dry run may ask about a run not opened yet — chain.py names the route it
# WOULD open on, and that wins only when the run has no route.json of its own.
PLANNED_ROUTE = None


def route_of(run):
    f = Path(run) / "vars/route.json" if run else None
    if f and f.is_file():
        try:
            r = json.loads(f.read_text())
            return r.get("route", "ai"), r.get("form", "single"), int(r.get("slides", 1))
        except ValueError:
            pass
    if PLANNED_ROUTE:
        return PLANNED_ROUTE
    return "ai", "single", 1


def glob_for(stage, run=None):
    route, form, _ = route_of(run)
    if stage == "1":
        return BRANCH_PROMPTS[("1", form)]
    if stage in W.STAGES:
        return W.glob_for(stage, route, form)
    return STAGES[stage][0]


def prompt_for(stage, folder=None, run=None):
    """The highest -vN- wins, and N is a NUMBER. Sorted as text, `-v10-` loses
    to `-v2-` — the tenth version of a prompt would silently never run. Same
    rule as components/run-kit `prompts.latest`; the glob stays this lane's
    own (top level only, so `superseded/` and `parked/` never compete).
    `run` picks the branch for stages 1 and 6. A writing stage's prompts are
    the writing station's (`prompts_dir`)."""
    folder = Path(folder or prompts_dir(stage))
    pattern = glob_for(stage, run)
    hits = sorted(folder.glob(pattern), key=lambda f: (version_of(f), f.name))
    if not hits:
        sys.exit(f"no prompt for stage {stage} ({pattern}) in {folder}")
    return hits[-1]


AWARENESS = ("most-aware", "product-aware", "solution-aware", "problem-aware", "unaware")


def awareness_of(run):
    """The swipe's awareness level, as the teardown record reads it (its MARKET STATE): the first level named there."""
    f = run / "out" / "01-teardown.md"
    t = f.read_text().lower() if f.is_file() else ""
    at = t.find("market state")
    t = t[at:] if at >= 0 else t
    hits = [(t.find(a), a) for a in AWARENESS if t.find(a) >= 0]
    return min(hits)[1] if hits else None


def language(brand, stage, run, avatar=None):
    """Query the brand's language layer for this stage and cache it in the run.

    the owner, 2026-10-27: "awareness levels and verbatims and spice are the foundation of what we're doing here." The
    query is the run's own avatar, at the swipe's awareness level first: without them it drew the top rows of every
    avatar in the brand (a niacinamide acne story on a dark-spots ad)."""
    out = run / "out" / f".language-{stage}.md"
    # THE VIDEO HOOK STEP'S CALL (the owner, 2026-10-27: "look at the headline process for video because that's pretty
    # dialed in"): the language library's own for_stage, as video-teardown chain.py makes it — the avatar, never-used
    # rows first plus a proven slice (used="fresh"), the swipe's awareness level first, forty rows.
    level = awareness_of(run)
    try:
        # its own process: the library's folder has a paths.py of its own, which this folder's shadows in-process
        code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import language as L; "
                "a = json.loads(sys.argv[2]); "
                "print(L.for_stage(a['brand'], a['stage'], a['avatar'], None, None, 40, used='fresh', awareness=a['level']))")
        arg = json.dumps({"brand": brand, "stage": stage, "avatar": avatar, "level": level})
        got = subprocess.run([sys.executable, "-c", code, str(P.LANGUAGE.parent), arg], capture_output=True, text=True,
                             env=dict(os.environ, AI_WORKSPACE=str(P.BRANDS.parent)), timeout=180)
        txt = got.stdout if got.returncode == 0 else ""
        if got.returncode != 0:
            raise RuntimeError((got.stderr or "").strip().splitlines()[-1][:160] if got.stderr else "no output")
        if txt and "no rows matched" not in txt:
            out.write_text(txt)
            print(f"  language: {txt.count(chr(10) + '- [')} rows · {stage} · {avatar or 'every avatar'} · {level or 'any level'} · fresh first")
            return out
    except Exception as e:                                   # noqa: BLE001  (the command below is the fallback)
        print(f"  ! language library call failed ({type(e).__name__}: {str(e)[:120]}); asking the command instead")
    # The language layer resolves brands from AI_WORKSPACE. Brand truth left
    # the lab for the repo root on 2026-09-02, so pointing this at the lab
    # returned "no rows matched" — silently, with the stage carrying on
    # without a word of customer language in it.
    env = dict(os.environ, AI_WORKSPACE=str(P.BRANDS.parent))
    cmd = [sys.executable, str(P.LANGUAGE), "--brand", brand, "--stage", stage]
    if avatar:
        cmd += ["--avatar", avatar]
    level = awareness_of(run)
    if level:
        cmd += ["--awareness", level]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    # no quiet widening to every avatar's rows when this avatar has none: that was the off-topic bug itself
    if r.returncode != 0 or "no rows matched" in r.stdout:
        print(f"  ! language layer returned nothing for {brand}/{stage}")
        return None
    out.write_text(r.stdout)
    n = r.stdout.count('\n- [')                   # rows open "- [language_…]"; counting '- "' read 0 for 25
    print(f"  language: {n} rows tagged {stage}")
    return out


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
    if stage in W.STAGES:
        # A writing stage: its inputs are the writing station's (image-writing
        # `inputs`), the teardown's records among them as the hand-off.
        return W.inputs(ENGINE_SELF, run, stage, brand, avatar, product, dry, planned)
    o = run / "out"
    v = {}

    def made_by(name, by):
        f = o / name
        if dry and not f.exists() and by in planned:
            return later(f"made by stage {by} in this run")
        return f

    if stage == "1k":
        # the culture read of a still post: its record, and what we hold of the post's own caption and comments
        v["teardown_record"] = made_by("01-teardown.md", "1")
        talk = run / "assets" / "post-talk.md"
        if not talk.is_file() and not dry:
            talk.write_text("none held: the swipe was handed over as a picture file, with no caption or comments\n")
        v["post_talk"] = talk if talk.is_file() else later("written when stage 1k starts")
        return v
    if stage == "1":
        # MARKET STATE (2026-09-18): the chain has no 1b, so stage 1 is the
        # only place that can name the ad's own awareness rung, sophistication
        # stage and lead desire — bound from the doctrine, never restated here.
        v["awareness_levels"] = P.DOCTRINE / "awareness.md"
        v["sophistication_stages"] = P.DOCTRINE / "sophistication.md"
        v["desire_dimensions"] = P.DOCTRINE / "desire.md"
        # Stage 1 is the only stage that sees the picture, so it is the only
        # one that can say how the letters are made. Same shape as 2b's:
        # rendered from the library at run time, never pasted into a prompt
        # where it would go stale (the owner, 2026-09-25).
        v["letterform_candidates"] = (later("rendered from components/elements/library at run time")
                                      if dry else EL.write_letterform_candidates(run))
        if dry:
            EL.letterform_candidates()               # proves the library answers
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
    return v


CONTROLS_HOME = P.REPO / "components/creative-controls"


def swipe_controls(run):
    """The swipe's level on every creative control, read once off the picture
    by creative-controls' reader and kept in the run."""
    out = run / "out" / "controls-swipe.md"
    if out.is_file():
        return out
    src = source_image(run)
    if not src:
        return Missing("no assets/source.* to read the swipe's controls from")
    js = run / "out" / "controls-swipe.json"
    subprocess.run([sys.executable, str(CONTROLS_HOME / "read.py"), "one", str(src), str(js)], check=True)
    got = json.loads(js.read_text())
    lines = ["%s: %s (%s)" % (k, x["level"], x["why"]) for k, x in got["dials"].items()]
    e = got.get("emotion") or {}
    lines.append("emotion: %s%s, %s" % (e.get("primary"), " + " + e["secondary"] if e.get("secondary") else "",
                                        e.get("where") or ""))
    lines.append("techniques: %s" % (", ".join(got.get("techniques") or []) or "none"))
    lines.append("standout: %s" % got.get("standout"))
    out.write_text("\n".join("- " + x for x in lines) + "\n")
    return out


def is_missing(p):
    if isinstance(p, Missing):
        return not getattr(p, "ok", False)
    return not Path(p).exists()


def wants_of(stage, run=None):
    return set(re.findall(r"\{([a-z_]+)\}", prompt_for(stage, run=run).read_text()))


def source_image(run):
    a = run / "assets"
    if not a.is_dir():
        return None
    return next((p for p in a.iterdir()
                 if p.stem == "source" and p.suffix.lower() in (".jpg", ".png")), None)


def source_images(run):
    """Every slide of a sequence, in order (`assets/source-NN.*`); for a
    single still, just the one. Stage 1 hands all of them to the reader."""
    a = run / "assets"
    if not a.is_dir():
        return []
    slides = sorted(p for p in a.iterdir()
                    if re.fullmatch(r"source-\d+", p.stem) and p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if slides:
        return slides
    one = source_image(run)
    return [one] if one else []


def pf_text(stage, run):
    try:
        return prompt_for(stage, run=run).read_text()
    except SystemExit:
        return ""


def run_stage(run, stage, brand, avatar, product, gates="hold"):
    o = run / "out"
    o.mkdir(parents=True, exist_ok=True)
    glob_, name, lang_stage, _ = STAGES[stage]

    if stage == "1":
        srcs = source_images(run)
        if not srcs:
            sys.exit(f"no assets/source.* in {run} — open it with swipe_intake.py")
        cmd = [sys.executable, str(P.GEMINI_IMAGE), "--prompt-file", str(prompt_for("1", run=run))]
        for src in srcs:
            cmd += ["--image", str(src)]
        for k, p in inputs_for(run, "1", brand, avatar, product).items():
            cmd += ["--var", f"{k}={p}"]
        cmd += ["--out", str(o / name)]
        print(f"  source: {', '.join(x.name for x in srcs)}")
        subprocess.run(cmd, check=True)
        # What this teardown used from the letterform bank, and what it had to
        # name for itself. Never a gate: a proposed row must not stop a run
        # (the owner, 2026-09-25 — "give it a name so we can keep things moving
        # forward"). Written down so it can be signed later.
        #
        # IT LIVES HERE, NOT BESIDE THE 2b GATE. Stage 1 is the only stage
        # with its own branch and its own `return`, so a hook placed with the
        # other post-stage work never runs for it — five live teardowns wrote
        # their letterforms and none of them were recorded (2026-09-25).
        file_letterforms(run)
        return o / name

    # A run held at the elements gate does not go on to the brand-side
    # stages: the hold is the point of the gate. Re-run 2b, or pass
    # `--gates warn` to carry on with the verdict still on the record.
    # It is the hand-off: a held record never reaches the writing station.
    if gates == "hold" and stage in W.STAGES:
        h = G.held(run, ["elements"])
        if h:
            sys.exit(f"{run.name} is HELD at the elements gate — stage {stage} not run:\n  "
                     + "\n  ".join(h["elements"]))

    v = inputs_for(run, stage, brand, avatar, product)

    if lang_stage:
        got = language(brand, lang_stage, run, avatar)
        if got:
            v["language_bank"] = got
    if "{spice_bank}" in pf_text(stage, run):
        # the copy spice rows (the language layer's own `spice` stage): what makes the words land, for the headline
        # and the variations, the same layer the copywriter writes with (the owner, 2026-10-27)
        got = language(brand, "spice", run, avatar)
        v["spice_bank"] = got if got else Missing("the language layer returned no spice rows for this avatar")

    if v.get("hook_ledger"):
        v["hook_ledger"] = W.open_ledger(run, brand, Path(v["hook_ledger"]))

    missing = [k for k, p in v.items() if is_missing(p)]
    if missing:
        sys.exit(f"stage {stage} is missing: " + ", ".join(missing))

    # Every {placeholder} the prompt names must be supplied, or the runner
    # fails deep inside a subprocess and reports a wall of shell arguments
    # instead of the one word that is wrong. Check it here, say it plainly.
    unmet = sorted(wants_of(stage, run) - set(v))
    if unmet:
        sys.exit(f"stage {stage} prompt asks for {', '.join(unmet)} — "
                 f"nothing supplies it. Either the runner owes it or the "
                 f"prompt should stop asking.")

    engine = ENGINE[stage]
    runner = P.CLAUDE_TEXT if engine == "claude" else P.GEMINI_TEXT
    model, _why = model_for(stage)
    pf = prompt_for(stage, run=run)
    if stage in W.STAGES:
        pf = W.before(run, stage, brand, avatar, pf)     # the learnings and any viewer notes ride on the end
    cmd = [sys.executable, str(runner), "--model", model,
           "--prompt-file", str(pf)]
    if stage == "2b":
        cmd += ["--min-chars", "120"]      # four ids and four reasons is a short, whole answer
    if stage == "1k":
        cmd += ["--search"]                # the culture read confirms slang and references on the web
    for k, p in v.items():
        cmd += ["--var", f"{k}={p}"]
    cmd += ["--out", str(o / name)]
    subprocess.run(cmd, check=True)
    if stage == "2" and re.search(r"\[\s*NO COPY\s*\]|\[\s*No text\s*\]|without overlaid copy|no (overlaid|on-image) (text|copy)",
                                  (o / name).read_text(), re.I):
        # A SWIPE WITH NO WORDS gives a brand step with no words: stage 3 rebuilds
        # the zones the swipe has, and a wordless swipe has none (2026-10-25: two
        # parody statics came back with nothing to read). Said once, loudly, here.
        (run / "vars" / "wordless.md").write_text("This swipe carries no words on the picture; the static built from it will carry none.\n")
        print("  NOTE: this swipe has no words on it, so the ad built from it will have none. "
              "For a static, pick a captioned post.")
    if stage in W.STAGES:
        # What the writing step does once its answer is on file: the floor and
        # the swaps record after 3, the variations record after 5, the copy
        # gate after 6 (image-writing `after`).
        W.after(ENGINE_SELF, run, stage, pf, cmd, brand, product, gates)

    if stage == "2b":
        # THE ELEMENTS GATE. The answer is read by code and every id is asked
        # of the element library. What the library does not hold is refused
        # and written down — never swapped for the nearest thing.
        rec, problems = EL.read(run, prompt_for("2b").name)
        kept = ", ".join(f"{k}={i}" for k, i in rec["labels"].items()) or "none"
        print(f"  labels: {kept}")
        G.elements_gate(run, problems, gates)
    return o / name


def dry_stage(run, stage, brand, avatar, product, planned):
    """One stage, resolved and reported. Starts nothing. Returns the MISSING names."""
    model, why = model_for(stage)
    route, form, n_slides = route_of(run)
    branch = f"  ·  {route} · {form}" if stage in ("1", "6") else ""
    print(f"\n[{stage}] {LABEL[stage]}  ·  {ENGINE[stage]}  ·  {model}  ({why}){branch}")
    rows = []
    try:
        pf = prompt_for(stage, run=run)
        rows.append(("prompt", pf.name, True))
        wants = set(re.findall(r"\{([a-z_]+)\}", pf.read_text()))
    except SystemExit as e:
        rows.append(("prompt", str(e), False))
        wants = set()
    if stage == "1":
        srcs = source_images(run)
        src = srcs[0] if srcs else None
        if src:
            rows.append(("image", ", ".join(x.name for x in srcs), True))
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
    if "{spice_bank}" in pf_text(stage, run):
        ok = P.LANGUAGE.is_file()
        rows.append(("spice_bank", f"queried at run time ({brand}/spice, {avatar or 'all avatars'}, {awareness_of(run) or 'any level'})"
                     if ok else f"language tool missing at {P.LANGUAGE}", ok))
        if ok:
            wants.discard("spice_bank")
    for k, p in v.items():
        if k == "hook_ledger" and not isinstance(p, Missing) and not Path(p).is_file():
            f = W.run_ledger(run)
            try:
                f = f.relative_to(P.REPO)
            except ValueError:
                pass
            rows.append((k, f"none on the brand — opens empty at {f}", True))
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


LABEL = {"1": "teardown", "1k": "culture read", "2": "the format", "2b": "element labels", **W.LABEL}


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
                print(f"  → {out.relative_to(P.REPO)}")
            if s == "6":
                W.viewer_step(ENGINE_SELF, run, brand, avatar, product, gates, quiet)
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
    ap.add_argument("--ask", help="the ask record (ask.json) this ad was ordered "
                    "with; its offer and moment go on top of the offer bank")
    ap.add_argument("--controls", help="the creative-controls preset this run aims for "
                    "(an id from components/creative-controls/controls.json; default maxed)")
    ap.add_argument("--sub", help="the sub-avatar's name under the core's sub-avatars/; "
                    "written onto each run, so every later stage reads it")
    ap.add_argument("--serial", action="store_true",
                    help="one run at a time, for reading the output as it goes")
    ap.add_argument("--dry-run", "--dry", dest="dry_run", action="store_true",
                    help="resolve every prompt, file and variable and say OK or "
                         "MISSING per stage — calls no model, writes nothing")
    ap.add_argument("--gates", choices=G.MODES, default="hold",
                    help="hold (default): a failed gate stops the run. warn: the "
                         "same verdict is written to check.json and the run carries on")
    ap.add_argument("--route", choices=("ai", "creator"),
                    help="dry run only: the route the run would be opened on")
    ap.add_argument("--form", choices=("single", "sequence"),
                    help="dry run only: the form the run would be opened on")
    ap.add_argument("--slides", type=int, default=1)
    a = ap.parse_args()
    global PLANNED_ROUTE
    if a.route or a.form:
        PLANNED_ROUTE = (a.route or "ai", a.form or "single", a.slides)

    runs = []
    for name in [x.strip() for x in a.run.split(",") if x.strip()]:
        run = Path(name)
        if not run.is_absolute():
            run = P.run_dir(run.name if run.parent.name == "runs" else str(run))
        # A dry run may be asked about a run that has not been opened yet —
        # `chain.py start --dry-run` names the runs it WOULD open.
        if not run.is_dir() and not a.dry_run:
            sys.exit(f"no run at {run}")
        runs.append(run)

    stages = a.stage
    W.PLANNED_SUB = a.sub                        # the writing station reads them for a dry run
    W.PLANNED_ASK = a.ask
    if a.ask and not a.dry_run:
        for run in runs:
            (run / "vars").mkdir(exist_ok=True)
            (run / "vars" / "ask.md").write_text(a.ask + "\n")
    if a.sub and not a.dry_run:
        for run in runs:
            (run / "vars").mkdir(exist_ok=True)
            (run / "vars" / "sub_avatar.md").write_text(a.sub + "\n")
    if a.controls and not a.dry_run:
        for run in runs:
            (run / "vars").mkdir(exist_ok=True)
            (run / "vars" / "controls_preset.md").write_text(a.controls + "\n")

    if not a.avatar and len(runs) == 1:
        # the run already names its avatar (vars/avatar.md, written when it was opened): a re-run of one step, from the
        # board or by hand, pulls that avatar's language, never every avatar's (2026-10-27)
        import re as _re
        f = runs[0] / "vars" / "avatar.md"
        m = _re.search(r"avatar:\s*([a-z0-9][a-z0-9-]*)", f.read_text()) if f.is_file() else None
        if m:
            a.avatar = m.group(1)
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
                      f"{(run / 'check.json').relative_to(P.REPO)}")
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
                print(f"    {o.relative_to(P.REPO)}")


if __name__ == "__main__":
    main()
