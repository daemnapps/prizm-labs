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

import argparse, json, os, re, subprocess, sys
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
    ("6", "ai", "single"):        "stage6-image-brief*",
    ("6", "ai", "sequence"):      "stage6-ai-sequence-brief*",
    ("6", "creator", "single"):   "stage6-creator-static-brief*",
    # Carousels are AI only (the owner, 2026-10-01) — a creator-route sequence
    # gets the AI sequence brief; the creator sequence prompt is retired.
    ("6", "creator", "sequence"): "stage6-ai-sequence-brief*",
}


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
    if stage == "6":
        return BRANCH_PROMPTS[("6", route, form)]
    return STAGES[stage][0]


def prompt_for(stage, folder=None, run=None):
    """The highest -vN- wins, and N is a NUMBER. Sorted as text, `-v10-` loses
    to `-v2-` — the tenth version of a prompt would silently never run. Same
    rule as components/run-kit `prompts.latest`; the glob stays this lane's
    own (top level only, so `superseded/` and `parked/` never compete).
    `run` picks the branch for stages 1 and 6."""
    folder = Path(folder or P.PROMPTS)
    pattern = glob_for(stage, run)
    hits = sorted(folder.glob(pattern), key=lambda f: (version_of(f), f.name))
    if not hits:
        sys.exit(f"no prompt for stage {stage} ({pattern}) in {folder}")
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
    # every organic run, and nine Brand A runs finished five stages and then
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


def avatar_input(run, brand, avatar, dry=False):
    """The avatar a brand-side stage reads. With a sub-avatar named on the run
    (`vars/sub_avatar.md`, written by `--sub`), it is the core profile, the
    sub's card and the sub's newest profile, put together fresh every time a
    stage runs — so a profile rewritten yesterday reaches today's brief without
    anyone re-opening the run (the owner, 2026-10-02)."""
    core = P.avatar_profile(brand, avatar)
    f = run / "vars" / "sub_avatar.md"
    sub = f.read_text().strip() if f.is_file() else (PLANNED_SUB or "")
    if not sub:
        return core
    card, prof = P.sub_avatar(brand, avatar or core.parent.name, sub)
    gone = [x for x in (core, card, prof) if not x.is_file()]
    if gone:
        return Missing("sub-avatar file missing: " + ", ".join(str(x) for x in gone))
    if dry:
        return later(f"core + sub {sub} (card + newest profile), put together at run time")
    out = run / "vars" / "avatar.md"
    out.write_text(
        f"# The avatar: {core.parent.name} → sub-avatar {sub}\n\n"
        "Write for the SUB-AVATAR. The core profile is who she is underneath; "
        "the sub-avatar card and its profile are who this ad is for, in her own "
        "words. Where they differ, the sub-avatar wins.\n\n"
        f"## Core avatar profile\n\n{core.read_text()}\n\n"
        f"## Sub-avatar card\n\n{card.read_text()}\n\n"
        f"## Sub-avatar profile (newest)\n\n{prof.read_text()}\n")
    return out


PLANNED_SUB = None
PLANNED_ASK = None


def offer_input(run, b, dry=False):
    """The offer a stage reads. With an ask named on the run (`vars/ask.md`
    holds the ask record's path, written by `--ask`), the ask's own offer and
    moment go on top of the brand's offer bank: the lines this ad may say, the
    lines it may never say, and the deadline. The bank is what the brand
    allows; the ask is what this ad was ordered with, and it wins where they
    differ (the owner, 2026-10-02 — Halloween ads, no price on the ad)."""
    f = run / "vars" / "ask.md"
    ask = f.read_text().strip() if f.is_file() else (PLANNED_ASK or "")
    if not ask:
        return b["offer"]
    a = Path(ask)
    if not a.is_absolute():
        a = P.REPO / a
    if not a.is_file() or not Path(b["offer"]).is_file():
        return Missing(f"ask or offer bank missing: {a}")
    if dry:
        return later(f"the ask's offer + moment ({a.name}) on top of the offer bank")
    rec = json.loads(a.read_text())
    off, mom = rec.get("offer") or {}, rec.get("moment") or {}
    lines = "\n".join(f"- \"{x}\"" for x in off.get("lines", []))
    never = "\n".join(f"- {x}" for x in off.get("never", []))
    when = "\n".join(f"- \"{x}\"" for x in mom.get("lines", []))
    out = run / "vars" / "offer.md"
    out.write_text(
        f"# THIS AD'S OFFER — from the ask `{rec.get('ask', a.parent.name)}`\n\n"
        "These rules come from the order this ad was made for. Where they differ "
        "from the offer bank below, THESE WIN. A line the bank allows but the "
        "ask's NEVER list forbids is not used anywhere in the ad.\n\n"
        f"Funnel: {rec.get('funnel', '')}\n\n"
        + "".join(f"Made by ({k.replace('_', ' ')}): {v}\n" for k, v in (rec.get("makers") or {}).items())
        + "\n"
        f"## Lines this ad may say, word for word\n\n{lines}\n\n"
        f"## Never on this ad\n\n{never}\n\n"
        f"## The moment and its deadline ({mom.get('key', '')}, {mom.get('window', '')})\n\n"
        f"Every ad in this ask carries one of these, word for word:\n\n{when}\n\n"
        f"---\n\n# The brand's offer bank (for reference under the rules above)\n\n"
        f"{Path(b['offer']).read_text()}\n")
    return out


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
        v["avatar"] = guarded(avatar_input, run, brand, avatar, dry)
        v["product_file"] = P.product(brand, product) if product else Missing("no --product given")
        v["offer_file"] = guarded(offer_input, run, b, dry)
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
        v["avatar"] = guarded(avatar_input, run, brand, avatar, dry)
        v["hook_ledger"] = b["hook_ledger"]
        v["identity_anchors"] = b["identity"]
        # THE RUNG TEST checks every headline against its entry rung's
        # must-not — bound from the doctrine, not restated in the prompt.
        v["awareness_levels"] = P.DOCTRINE / "awareness.md"
    if stage == "5":
        v["product_file"] = P.product(brand, product) if product else Missing("no --product given")
    if stage == "6" and "{brief_standard}" in prompt_for("6", run=run).read_text():
        # Document one is the standard brief, filled in (the owner, 2026-10-02:
        # "we need a standardized briefing document literally").
        v["brief_standard"] = P.BRIEF_STANDARD
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
        v["style_packs"] = P.REPO / "tools/image-production/static/style-packs.json"   # image-production is a component now
        # Their angle, in their words. The swipe library has named every one
        # of them, with clone counts and the verbatim copy — and no stage had
        # ever been handed one, so the chain judged a competitor's argument
        # off the picture alone (2026-09-13).
        v["swipe_angle"] = (later("resolved from assets/source.json when the run opens")
                            if dry and not run.is_dir() else swipe_angle(run))
        v["brand_name"] = own("vars/brand_name.md", "written when the run opens")
        v["product_file"] = P.product(brand, product) if product else Missing("no --product given")
        v["offer_file"] = guarded(offer_input, run, b, dry)
        v["palette"] = b["palette"]
        # Technique per element in the brief — bound from the doctrine.
        v["techniques"] = P.DOCTRINE / "techniques.md"
    return v


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


def run_ledger(run):
    """Where a brand with no hook ledger gets its empty one: this run's vars/."""
    return Path(run) / "vars" / "hook-ledger.md"


def open_ledger(run, brand, ledger):
    """The hook ledger stage 4 reads. A brand's own ledger is read, never
    written. A ledger that does not exist yet means "no hooks spent", not
    "stop" — but the empty one opens in the RUN, never under brands/: brands/
    is read-only to machines, and a brand-file change is a person's commit
    (K2, 2026-10-06; SI-24)."""
    if ledger.is_file():
        return ledger
    f = run_ledger(run)
    if not f.is_file():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(
            f"# {brand} hook ledger\n\n"
            "Opened in this run because the brand has no ledger — empty "
            "because nothing has been generated yet. Stage 4 reads it before "
            "writing: a verbatim already mapped to a hook here is spent. A "
            f"person adds brands/{brand}/ads/hooks/hook-ledger.md by commit.\n\n"
            "| verbatim | hook | status | run |\n|---|---|---|---|\n")
        print(f"  opened an empty hook ledger for {brand} in this run — {f}")
    return f


def run_stage(run, stage, brand, avatar, product, gates="hold"):
    b = P.brand(brand)
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

    if v.get("hook_ledger"):
        v["hook_ledger"] = open_ledger(run, brand, Path(v["hook_ledger"]))

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
    if stage in ("3", "4", "5", "6"):
        # WHAT GOT PAST THIS AVATAR BEFORE — the viewer chain's learnings (2026-10-02)
        try:
            G.quality()
            from marketing_chain_checks import viewer as _VW
            head = (run / "vars" / "avatar.md").read_text(errors="replace")[:300] if (run / "vars" / "avatar.md").is_file() else ""
            m = re.search(r"The avatar:\s*([\w-]+)(?:\s*→\s*sub-avatar\s*([\w-]+))?", head)
            who = (m.group(2) or m.group(1)) if m else avatar
            lt = _VW.learnings(brand, who) if who else ""
            if lt.strip():
                tmp = run / "vars" / f"_prompt-{stage}-learned.md"
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(pf.read_text().rstrip() + "\n\n---\n\n## WHAT GOT PAST THIS AVATAR BEFORE (the viewer chain's learnings)\n\n"
                               "Real viewer checks on earlier briefs for this same person: use what worked, don't repeat what failed. "
                               "Never overrides the swipe's structure or the owner's rulings.\n\n" + lt.strip() + "\n")
                pf = tmp
        except Exception:
            pass
    notes = run / "vars" / f"viewer-notes-{stage}.md"
    if notes.is_file():
        # THE VIEWER CHECK sent this step back: the viewers' own words ride on
        # the end of its prompt for this one re-make (viewer_step, below).
        tmp = run / "vars" / f"_prompt-{stage}-viewer.md"
        tmp.write_text(pf.read_text().rstrip() + "\n\n---\n\n" + notes.read_text().strip() + "\n")
        pf = tmp
    cmd = [sys.executable, str(runner), "--model", model,
           "--prompt-file", str(pf)]
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
        route, form, _ = route_of(run)
        print(f"  brief: {route} · {form} — {prompt_for('6', run=run).name}")
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
    for k, p in v.items():
        if k == "hook_ledger" and not isinstance(p, Missing) and not Path(p).is_file():
            f = run_ledger(run)
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


LABEL = {"1": "teardown", "2": "the format", "2b": "element labels", "3": "injection",
         "4": "headlines", "5": "picture variations", "6": "the brief"}


# THE VIEWER CHECK (the owner, 2026-10-02: "slide this into the chains and lets
# ride it"; components/quality-checks/VIEWER-CHECK.md). Last, after the brief's
# copy gate and before any picture is drawn: the brief is dropped into its
# avatar's real feed and scrolled by 3 fresh viewers who are not marketers;
# code scores it against the real posts beside it. A fail re-makes the step
# where they passed it by, with their words, and a fresh set reads it again.
# Two fails, or "not for me", HOLD at the `viewer` gate for the owner.
VIEWER_ROUTE = {"openings": "4", "middle": "5", "giveaway": "5", "close": "6",
                "staged": "5", "words": "4", "muted": "4", "proof": "6"}   # v2 (2026-10-02)


def viewer_step(run, brand, avatar, product, gates="hold", quiet=False):
    import os
    if os.environ.get("QC_VIEWER", "1") == "0" or "unittest" in sys.modules:
        return
    G.quality()
    from marketing_chain_checks import viewer as VW
    if not avatar:
        avatar = P.avatar_profile(brand, None).parent.name
    _, form, _ = route_of(run)
    kind = "carousel" if form == "sequence" else "still image"
    sf = run / "vars" / "sub_avatar.md"          # the ad is judged by who it was written for
    sub = sf.read_text().strip().splitlines()[0].strip() if sf.is_file() and sf.read_text().strip() else None
    if sub and sub.lower().startswith(("none", "(none", "-")):
        sub = None
    # THE WHOLE LOOP (the owner, 2026-10-03: "install this in the actual process"):
    # check → answers from real data → surgical rewrite → fresh check, up to 3
    # rewrites, never on a worse version; a pass after a fail is learned. A
    # passing rewrite becomes the brief.
    bf = run / "out" / "06-brief.md"
    before = bf.read_text()
    r, text = VW.run_loop(run / "viewer-chain", brand, avatar, before, kind=kind, sub=sub, label=run.name,
                          say=lambda m: print("  " + m.strip()))
    if r["passed"]:
        if text.strip() != before.strip():
            (run / "out" / "06-brief.before-viewer.md").write_text(before)
            bf.write_text(text)
            print("  viewer check: the rewrite that passed is now the brief (kept 06-brief.before-viewer.md)")
        return G._gate("viewer", [], run, gates)
    why = ("the viewers said it isn't for them — who it's for is the owner's call" if r["fix_at"] == "audience"
           else f"still failing after the rewrites — last at {VW.say(r['fix_at'])}")
    return G._gate("viewer", [f"{why} (viewer-chain/REPORT.html)"], run, gates)


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
                viewer_step(run, brand, avatar, product, gates, quiet)
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
            run = P.RUNS / run.name if run.parent.name == "runs" else P.RUNS / str(run)
        # A dry run may be asked about a run that has not been opened yet —
        # `chain.py start --dry-run` names the runs it WOULD open.
        if not run.is_dir() and not a.dry_run:
            sys.exit(f"no run at {run}")
        runs.append(run)

    stages = a.stage
    global PLANNED_SUB
    PLANNED_SUB = a.sub
    global PLANNED_ASK
    PLANNED_ASK = a.ask
    if a.ask and not a.dry_run:
        for run in runs:
            (run / "vars").mkdir(exist_ok=True)
            (run / "vars" / "ask.md").write_text(a.ask + "\n")
    if a.sub and not a.dry_run:
        for run in runs:
            (run / "vars").mkdir(exist_ok=True)
            (run / "vars" / "sub_avatar.md").write_text(a.sub + "\n")

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
