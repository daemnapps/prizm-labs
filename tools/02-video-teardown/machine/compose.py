#!/usr/bin/env python3
"""The second door — an ad composed from a CHOICE, not swiped.

Damon's ruling, 2026-09-18: "with all of the different sections we should begin
to assemble actual frameworks to create ads strategically. We use swipes as the
baseline, but since we have a fundamental system and understanding of who we are
speaking to and how and what formats they're receptive to, we can pump out
mounds of video and photo ads."

The first door starts from somebody else's asset: read it, abstract it, inject
ours. This one starts from four choices — the avatar, the awareness level, the
format and the framework — and WRITES the construct those choices imply. From
stage 3 onward the two doors are the same chain, running the same prompts, on
the same routes, producing the same brief.

    python3 compose.py plan --brand B --avatar A --sub S \\
        --awareness problem-aware --format <format id> --framework <framework id> \\
        --route ai
    python3 compose.py run  ...same flags...          plan, then run the chain
    python3 compose.py grid --brand B --avatar A \\
        --awareness a,b --formats f,g --frameworks x,y [--go]

`plan` never calls a model. It opens the run folder, files the stand-ins the
four reading stages would have produced, and resolves every variable of every
stage so a refusal arrives before any money is spent. `run` does the same and
then hands the run to run.py's own machinery — there is no second copy of the
chain in this file.

Everything is looked up, never guessed: a framework id, a format id, an
awareness level, a sophistication stage or an avatar that does not exist is
refused BY NAME, with the ids that do exist printed.
"""

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C                                        # noqa: E402

LANE = "FRAMEWORK"
DOCTRINE = C.WS / "components" / "marketing-doctrine"
AD_FRAMEWORKS = DOCTRINE / "ad-frameworks.json"
FRAMEWORKS = DOCTRINE / "frameworks.json"
# The format bank is definitions, curated where the video machine keeps them.
# Shared infrastructure reads lab DATA as a matter of course (workspace rule 9);
# what it never does is adopt lab instruction content.
FORMAT_BANK = C.WS / "lab" / "damon" / "ai-video-production" / "formats" / "bank.json"

ROUTES = ("ai", "creator", "founder")
FUNNELS = ("prospect", "lead", "customer", "churned")


class Refused(SystemExit):
    """A choice that does not exist. Never a guess, never a default — the
    message names what was asked for and prints what there is."""


def _load(path, what):
    if not path.is_file():
        raise Refused(f"{what} is not at {path} — nothing can be composed without it")
    try:
        return json.loads(path.read_text())
    except Exception as e:
        raise Refused(f"{what} at {path} will not parse: {type(e).__name__}: {e}")


def doctrine():
    return _load(FRAMEWORKS, "the doctrine (frameworks.json)")


def ad_frameworks():
    return _load(AD_FRAMEWORKS, "the ad frameworks (ad-frameworks.json)")


def format_bank():
    return _load(FORMAT_BANK, "the format bank (formats/bank.json)")


def pick(kind, wanted, rows, key="id", label=None):
    """One row by id, or a refusal naming every id there is."""
    wanted = (wanted or "").strip()
    by_id = {r[key]: r for r in rows}
    if wanted in by_id:
        return by_id[wanted]
    have = ", ".join(sorted(by_id)) or "(none)"
    raise Refused(f"no {kind} called '{wanted}'" + (f" in {label}" if label else "")
                  + f" — the ones there are: {have}")


def slug(s, n=70):
    return (re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower() or "x")[:n]


# ------------------------------------------------------------------ the choice

def choose(brand, avatar, sub, awareness, sophistication, fmt, framework,
           route, funnel, topics, product=None):
    """Resolve the four choices against the banks. -> a spec dict, or Refused.

    Nothing here is defaulted except the sophistication stage, which the chosen
    framework's own row supplies when the run does not name one — and the row is
    printed, so it is a stated inheritance rather than a silent one.

    `product` is carried through unvalidated — a brand with more than one
    product is a `KeyError` from `chain.resolve_source` at plan time, which
    `resolve_plan()` already turns into a named refusal ("--product 'x'
    matches nothing in ... — have: ..."). Validating it twice would just be
    two places that could disagree about what a brand's products are.
    """
    d, a, fb = doctrine(), ad_frameworks(), format_bank()

    row = pick("framework", framework, a["frameworks"], label="ad-frameworks.json")
    fmt_row = pick("format", fmt, fb["formats"], label="the format bank")
    level = pick("awareness level", awareness, d["awareness"]["levels"],
                 label="the doctrine")
    if sophistication:
        stage = pick("sophistication stage", sophistication,
                     d["sophistication"]["stages"], label="the doctrine")
        soph_why = "named on the run"
    else:
        stage = pick("sophistication stage", row["sophistication"][0],
                     d["sophistication"]["stages"], label="the doctrine")
        soph_why = (f"inherited from the framework row, which suits "
                    + ", ".join(row["sophistication"]))

    if route and route.lower() not in ROUTES:
        raise Refused(f"no production route called '{route}' — the ones there "
                      f"are: {', '.join(ROUTES)}")
    if funnel and funnel.lower() not in FUNNELS:
        raise Refused(f"no funnel position called '{funnel}' — the ones there "
                      f"are: {', '.join(FUNNELS)}")

    # The brand's own avatar folder is the only place an avatar exists.
    adir = C.WS / "brands" / brand / "core-avatars" / avatar
    if not adir.is_dir():
        cores = C.WS / "brands" / brand / "core-avatars"
        have = ", ".join(sorted(p.name for p in cores.iterdir() if p.is_dir())) \
            if cores.is_dir() else "(this brand has no core-avatars folder)"
        raise Refused(f"no avatar called '{avatar}' for brand '{brand}' — "
                      f"the ones there are: {have}")
    sub_file = None
    if sub:
        subs = sorted((adir / "sub-avatars").glob("*.md")) \
            if (adir / "sub-avatars").is_dir() else []
        keys = {}
        for f in subs:
            k = re.sub(r"^sub-\d+-", "", f.stem)
            keys[k] = f
            keys[f.stem] = f
        if sub not in keys:
            raise Refused(f"no sub-avatar called '{sub}' under '{avatar}' — "
                          f"the ones there are: "
                          + (", ".join(sorted(re.sub(r'^sub-\d+-', '', f.stem)
                                              for f in subs)) or "(none)"))
        sub_file = keys[sub]

    # A section the framework names must be a section the doctrine has. The
    # doctrine is read HERE, at run time, so a section added to it this morning
    # is usable this afternoon and one removed refuses loudly.
    known = {s["id"]: s for s in d["sections"]}
    techs = {t["id"] for t in d["techniques"]}
    for s in row["sections"]:
        if s["id"] not in known:
            raise Refused(f"framework '{row['id']}' names section '{s['id']}', "
                          f"which the doctrine does not carry — the sections "
                          f"there are: {', '.join(sorted(known))}")
        if s["technique"] not in techs:
            raise Refused(f"framework '{row['id']}' names technique "
                          f"'{s['technique']}' on section '{s['id']}', which is "
                          f"not one of the seven: {', '.join(sorted(techs))}")

    fits = row.get("formats_fit") or ["any"]
    fit_note = ("this framework declares it fits any format"
                if "any" in fits else
                f"this framework declares it fits {', '.join(fits)}"
                + ("" if fmt_row["id"] in fits else
                   f" — '{fmt_row['id']}' is NOT among them; running it anyway "
                   f"is the choice that was made, and it is recorded here"))

    return dict(
        brand=brand, avatar=avatar, sub=sub, sub_file=str(sub_file) if sub_file else None,
        framework=row, format=fmt_row, awareness=level, sophistication=stage,
        sophistication_why=soph_why, route=(route or "creator").lower(),
        funnel=(funnel or "prospect").lower(),
        topics=[t.strip() for t in (topics or "").split(",") if t.strip()],
        product=(product or "").strip(),
        format_fit=fit_note)


def label_for(spec):
    who = spec["sub"] or spec["avatar"]
    return slug("fw-%s-%s-%s-%s" % (spec["framework"]["id"], spec["format"]["id"],
                                    who, spec["awareness"]["id"]))


# ------------------------------------------------------------- the stand-ins
# The four stages that READ a source. There is no source, so each one is written
# here before the chain starts — in the shape the stage itself prints, because
# every parser downstream (lane_from_triage, market_state_from, audience_from,
# file_doctrine) keys off that shape and none of them is changed for this lane.

def source_record(spec):
    f = spec["framework"]
    return "\n".join([
        "LANE: %s" % LANE,
        "CATEGORY: not read — this run has no source asset",
        "RUNTIME: not read — this run has no source asset",
        "SOUND FORM: SPOKEN",
        "AI ASSESSMENT: no source to assess — the asset does not exist yet",
        "ONE LINE: nothing was swiped; this ad is composed from a chosen "
        "framework, avatar, awareness level and format.",
        "",
        "# The source record",
        "",
        "**There is no swipe.** This run came through the second door: the ad is "
        "composed from a choice rather than reverse-engineered from somebody "
        "else's asset. Every stage that would have read a source reads this "
        "instead, and says so.",
        "",
        "| The choice | What was chosen | Where it came from |",
        "|---|---|---|",
        "| Framework | %s (`%s`) | components/marketing-doctrine/ad-frameworks.json |"
        % (f["name"], f["id"]),
        "| Format | %s (`%s`) | the format bank |"
        % (spec["format"]["name"], spec["format"]["id"]),
        "| Awareness level | %s (`%s`) | the doctrine |"
        % (spec["awareness"]["name"], spec["awareness"]["id"]),
        "| Sophistication stage | %s (`%s`) | the doctrine — %s |"
        % (spec["sophistication"]["name"], spec["sophistication"]["id"],
           spec["sophistication_why"]),
        "| Avatar | `%s`%s | the brand's own folder |"
        % (spec["avatar"], (" · sub `%s`" % spec["sub"]) if spec["sub"] else ""),
        "| Production route | %s | named on the run |" % spec["route"],
        "",
        "**SOUND FORM** is SPOKEN because nothing was heard — it is the format's "
        "own default, not a reading. A composed run that is meant to be sung "
        "says so in its format, and the format profile is bound at the compose "
        "stage.",
        "",
        "**Format fit.** %s" % spec["format_fit"],
        "",
    ])


def teardown_record(spec):
    f = spec["framework"]
    rows = ["| # | Section | Technique | What this beat does |", "|---|---|---|---|"]
    for i, s in enumerate(f["sections"], 1):
        rows.append("| %d | `%s` | %s | %s |" % (i, s["id"], s["technique"], s["shape"]))
    return "\n".join([
        "# The record — composed, not torn down",
        "",
        "**No asset was read.** The stage that produces this record reads a video "
        "and writes down what it observed. This run has no video, so what follows "
        "is not an observation: it is the PLAN the run was opened with, printed "
        "in the record's place so every stage that asks for the record gets a "
        "straight answer rather than a hole.",
        "",
        "Nothing here may be cited as evidence of what an audience responded to. "
        "It is evidence of what was chosen.",
        "",
        "## The framework",
        "",
        "**%s** (`%s`) — %s" % (f["name"], f["id"], f["what"]),
        "",
        "Source of the row: %s · status: %s" % (f["source"], f["status"]),
        "",
        "## The beats it plans",
        "",
        "\n".join(rows),
        "",
        "## Where it picks the viewer up and puts them down",
        "",
        "- **Enters at:** %s (`%s`) — %s" % (
            spec["awareness"]["name"], spec["awareness"]["id"],
            spec["awareness"]["where_the_ad_may_begin"]),
        "- **Exits at:** `%s`" % f["awareness"]["exit"],
        "- **Leads with:** %s — %s" % (spec["sophistication"]["name"],
                                       spec["sophistication"]["lead_with"]),
        "",
        "## The format it runs in",
        "",
        "**%s** (`%s`) — %s" % (spec["format"]["name"], spec["format"]["id"],
                                spec["format"]["what"]),
        "",
        "There is no transcript, no scene list and no timing: a composed run has "
        "nothing to transcribe. The construct is written at the compose stage and "
        "that is the first document in this run with beats in it.",
        "",
    ])


def doctrine_row(spec):
    """Stage 1c's shape: prose, then the fenced json block file_doctrine() files
    as doctrine.json — which is what puts this run on the framework bank's
    shelf beside every swipe."""
    f = spec["framework"]
    block = {
        "framework": f["name"],
        "crosswalk_row": f["name"] if f["source"].startswith("seed — crosswalk row")
                         else None,
        "sections_carried": [{"id": s["id"], "span": "phase %d" % i}
                             for i, s in enumerate(f["sections"], 1)],
        "awareness": {"entry": f["awareness"]["entry"], "exit": f["awareness"]["exit"]},
        "sophistication_signature": spec["sophistication"]["lead_with"],
        "mass_desire": {
            "words": "[UNFILLED: composed run — the desire comes from the avatar "
                     "file at the compose stage, not from a reading]",
            "urgency": "not read — no source asset",
            "staying_power": "not read — no source asset",
            "scope": "not read — no source asset",
        },
        "techniques": [{"section": s["id"], "technique": s["technique"],
                        "sub_method": s["shape"], "span": "phase %d" % i}
                       for i, s in enumerate(f["sections"], 1)],
        "mood": "[UNFILLED: composed run — the mood is set at the creative pass]",
        # every delivery key present, so the bank, the filters and
        # file_doctrine's key check read a composed run exactly as they read a
        # swiped one. There is no source, so there is nothing to have read.
        "delivery": {
            "humor": "not shown — no source",
            "delivery_style": "not shown — no source",
            "register": "not shown — no source",
            "pacing": "not shown — no source",
            "reference_world": [],
            "avoid": [],
        },
        "unique": "%s composed for %s at %s, in the %s format."
                  % (f["name"], spec["sub"] or spec["avatar"],
                     spec["awareness"]["id"], spec["format"]["id"]),
        "composed": True,
    }
    return "\n".join([
        "# The doctrine read — of the PLAN, not of a source",
        "",
        "This stage reads a swiped asset against the doctrine and banks what it "
        "found. There is nothing to read here. What is banked instead is the plan "
        "this run was composed from, marked `composed: true`, so the bank can "
        "tell an observation from an intention at a glance and never counts one "
        "as the other.",
        "",
        "- **Framework:** %s (`%s`)" % (f["name"], f["id"]),
        "- **Sections it carries:** %s" % " → ".join("`%s`" % s["id"]
                                                     for s in f["sections"]),
        "- **Awareness:** `%s` → `%s`" % (f["awareness"]["entry"],
                                          f["awareness"]["exit"]),
        "- **Leads with:** %s" % spec["sophistication"]["lead_with"],
        "- **Doctrine pointers on the row:** %s"
        % " ".join("[%s]" % r for r in f.get("ref", [])),
        "",
        "```json",
        json.dumps(block, indent=2, ensure_ascii=False),
        "```",
        "",
    ])


def market_state(spec):
    """Stage 1b's labelled slots, spelled exactly as 1b v6 prints them, so
    `market_state_from()` and `audience_from()` read this run unchanged."""
    lv, so = spec["awareness"], spec["sophistication"]
    f = spec["framework"]
    must_not = "; ".join(lv.get("must_not", []))
    return "\n".join([
        "# Who this is written for — chosen, not read",
        "",
        "Every value below was named on the run or taken from the doctrine row "
        "the run chose. Nothing was inferred from a source, because there is no "
        "source. The labels are the stage's own, unchanged, so every stage after "
        "this one keys off them exactly as it always has.",
        "",
        "```",
        "AVATAR: %s" % spec["avatar"],
        "AVATAR WHY: named on the run — this is a composed ad, so the reader was "
        "chosen before anything was written.",
        "FUNNEL: %s" % spec["funnel"],
        "FUNNEL MEANS: named on the run; the language query for every later stage "
        "is filtered to this position.",
        "LEAD DESIRE: [UNFILLED: taken from the avatar file bound at the compose "
        "stage, not from a reading of a source]",
        "DESIRE TEST: [UNFILLED: no source to test a desire against — the compose "
        "stage tests it against the avatar and the language rows]",
        "DESIRE VS SOURCE: there is no source; the desire is the avatar's own.",
        "AWARENESS: %s (%s)" % (lv["name"], lv["id"]),
        "AWARENESS MUST NOT: %s" % (must_not or "—"),
        "AWARENESS WHY: named on the run — the level is one of the four choices "
        "this ad was composed from.",
        "SOPHISTICATION: %s (%s)" % (so["name"], so["id"]),
        "SOPHISTICATION LEADS WITH: %s" % so["lead_with"],
        "SOPHISTICATION WHY: %s" % spec["sophistication_why"],
        "ROUTE RECOMMENDED: %s" % spec["route"],
        "ROUTE WHY: named on the run.",
        "SUB-AVATAR: %s" % (spec["sub"] or "none"),
        "TOPICS: %s" % (", ".join(spec["topics"]) if spec["topics"] else "none"),
        "TOPICS WHY: named on the run; empty means the language query is not "
        "narrowed by topic.",
        "```",
        "",
        "## The framework this market state was matched to",
        "",
        "**%s** (`%s`) — %s" % (f["name"], f["id"], f["what"]),
        "",
        "Its own declared entry is `%s` and its exit `%s`.%s"
        % (f["awareness"]["entry"], f["awareness"]["exit"],
           "" if f["awareness"]["entry"] == lv["id"] else
           " The run named `%s` instead, so the compose stage opens at the level "
           "the run chose and the framework's order bends to it." % lv["id"]),
        "",
    ])


STAND_INS = [
    ("stage0", "0", "Triage", source_record),
    ("stage1", "1", "Teardown", teardown_record),
    ("stage1c", "1c", "Doctrine", doctrine_row),
    ("stage1b", "1b", "Audience", market_state),
]


# ------------------------------------------------------------------ the folder

def open_composed(spec, label=None):
    """The run folder, in exactly the shape a swipe run has, with the four
    stand-ins already filed. Re-running the same choice lands in the same
    folder, the same way re-running a video does.

    The folder id is built with run.py's OWN `slug()` (its default cap is 40
    characters, this module's own is 70) — `cmd_run()` hands off to
    `run_video()`, which reopens this same folder through `open_run()` using
    run.py's `slug()` on this same label. A composed label routinely runs
    past 40 characters, so building the id with this module's own, longer
    cap opened a SECOND, empty folder the moment the real run started: the
    stand-ins were never seen, stage0 tried to run for real against no
    video, and the run stopped saying so. Matching run.py's own function
    here is what keeps `plan` and `run` looking at the same folder.
    """
    import run as R                                       # noqa: E402

    lab = label or label_for(spec)
    s = C.run_slug(R.slug(lab))
    d = C.runs_root() / s
    (d / "stages").mkdir(parents=True, exist_ok=True)
    (d / "prompts").mkdir(parents=True, exist_ok=True)

    st = R.load(d) or dict(slug=s, label=lab, opened=R.now(), stages={})
    st.update(
        label=lab, brand=spec["brand"], lane="framework", creator=None,
        triage_lane=LANE,
        source={
            "kind": "framework",
            "framework": spec["framework"]["id"],
            "framework_name": spec["framework"]["name"],
            "format": spec["format"]["id"],
            "awareness": spec["awareness"]["id"],
            "sophistication": spec["sophistication"]["id"],
            "avatar": spec["avatar"], "sub_avatar": spec["sub"],
            "funnel": spec["funnel"], "route": spec["route"],
            "composed_by": "compose.py", "format_fit": spec["format_fit"],
        },
        audience={
            "_avatar": spec["avatar"], "_funnel": spec["funnel"],
            "_sub_avatar": spec["sub"], "_topics": spec["topics"],
        },
        market_state=R.market_state_from(market_state(spec)),
        production_route=spec["route"], route_chosen_by_hand=True,
        **C.attribution())
    r = C.route_for(LANE)
    st["route"] = dict(lane=LANE, why=r["why"], skipped=r["skip"])

    for key, sid, name, fn in STAND_INS:
        body = fn(spec)
        rel = "stages/%s-%s.md" % (sid, slug(name))
        (d / rel).write_text(body)
        st["stages"][key] = dict(
            status="done", name=name, engine="composed", model="none",
            version=0, out=rel, chars_out=len(body),
            finished=R.now(), composed=True,
            why="composed — there is no source asset to read, so this stage's "
                "record was written from the run's own choices before the chain "
                "started")
    # The doctrine row, filed the way stage 1c files it, so the framework bank
    # compiles this run beside every swipe.
    R.file_doctrine(d, doctrine_row(spec))
    R.save(d, st)
    return d, st


def extras_for(spec):
    """The run values the composed stages read. `ad_framework` and
    `format_profile` are bound as `~vars`, which is how every other per-run
    value in this chain travels."""
    f = spec["framework"]
    lines = ["# The framework this ad is composed from", "",
             "**%s** (`%s`) — %s" % (f["name"], f["id"], f["what"]), "",
             "- **Status:** %s · **Source of the row:** %s" % (f["status"], f["source"]),
             "- **Awareness it plans:** `%s` → `%s`" % (f["awareness"]["entry"],
                                                        f["awareness"]["exit"]),
             "- **Sophistication stages it suits:** %s"
             % ", ".join(f["sophistication"]),
             "- **Doctrine pointers:** %s" % " ".join("[%s]" % r for r in f.get("ref", [])),
             "", "## Its sections, in the order it plans them", "",
             "| # | Section | Technique | The shape this beat takes |",
             "|---|---|---|---|"]
    for i, s in enumerate(f["sections"], 1):
        lines.append("| %d | `%s` | %s | %s |" % (i, s["id"], s["technique"], s["shape"]))
    lines += ["", "The order is the plan. The market state outranks it — a section "
              "the chosen level does not call for is dropped, and the drop is "
              "stated.", ""]
    profile = ""
    pf = spec["format"].get("profile")
    if pf:
        p = FORMAT_BANK.parent / pf
        profile = p.read_text() if p.is_file() else \
            "[UNFILLED: the format bank names profile '%s' and there is no such " \
            "file beside it]" % pf
    return {
        "ad_framework": "\n".join(lines),
        "format_profile": profile,
        "brand_name": spec["brand"].replace("-", " ").title(),
        "video_count": "1",
        "product": spec.get("product") or "",
        "declared_audience": "NONE",   # this door names its audience in the spec itself
    }


# ------------------------------------------------------------------- resolving

# `story` joined 2026-09-19: run.py fills it from brands/<brand>/story.md
# plus 1b's pick, [UNFILLED] for a brand with none.
# `voiceprint` joined 2026-09-19: run.py fills it from the brand's measured
# creator voiceprints (brands/<brand>/creators/VOICEPRINTS.md), [UNFILLED]
# when the brand has none — the same shape as `research`.
# `declared_audience` joined 2026-09-20: run.py fills it from --for-avatar /
# --for-sub (a video from a sub-avatar's own organic feed), "NONE" otherwise.
RUN_SUPPLIED = {"source_url", "research", "voiceprint", "story", "ad_framework", "declared_audience",
                "format_profile", "brief_count", "video_count", "product",
                "brand_name", "profile_spec", "creator_record",
                "teardown_material", "existing_profile", "handle",
                # empty on every run but a Variation video one (variation.py);
                # the prompts read empty as "not a variation run"
                "target_awareness", "branch_sections"}


def resolve_plan(d, st, spec, extras, only=None, start=None, stop=None):
    """Every stage, every variable, with no model call. -> [(stage, [findings])]

    A `@stage` reference is checked against what the run already holds and what
    the plan will produce, in order — the one check a dry run can make that a
    live one cannot make cheaply. Everything else is resolved for real: a brand
    file that is not there refuses here rather than four stages in.

    `only` / `start` / `stop` narrow the plan the SAME WAY `run_video()` itself
    narrows it (by stage id, e.g. "5" — see run.py's own `--from`/`--to`/`--only`),
    so a run that only means to go as far as the stage-5 brief is checked
    against that scope, not against a stage past its own stop point.
    """
    import run as R                                       # noqa: E402

    plan = C.stages(spec["brand"], st.get("asset_type", ""), spec["route"], LANE)
    route = C.route_for(LANE)
    plan = [s for s in plan if s["key"] not in (route["skip"] or [])
            or (st["stages"].get(s["key"]) or {}).get("status") == "done"]
    ids = [s["id"] for s in plan]
    if only:
        plan = [s for s in plan if s["id"] in only]
    else:
        if start and start in ids:
            plan = plan[ids.index(start):]
        if stop:
            k = [s["id"] for s in plan]
            if stop in k:
                plan = plan[:k.index(stop) + 1]

    pack = dict(extras)
    pack.update(R.outputs_so_far(d, st))
    pack.update(st.get("audience") or {})
    pack["avatar"] = spec["avatar"]
    pack["source_url"] = "NONE"
    have = set(pack) | {k for k, v in st["stages"].items()
                        if v.get("status") == "done"}
    sub = route["substitute"] or {}

    out = []
    for s in plan:
        found = []
        if not s["prompt"]:
            found.append("no prompt file for this stage")
        for var, src in (s["vars"] or {}).items():
            if src.startswith("@"):
                ref = src[1:].split("#")[0].rstrip("*")
                if ref not in have and sub.get(ref) not in have:
                    found.append("{%s} wants stage %s, which this lane never "
                                 "runs and nothing stands in for" % (var, ref))
                continue
            if src.startswith("~"):
                if src[1:] not in RUN_SUPPLIED:
                    found.append("{%s} is bound to the run value '%s', which "
                                 "nothing supplies" % (var, src[1:]))
                continue
            if src.startswith("#"):
                if src[1:] not in extras:
                    found.append("{%s} is bound to '%s', which the run did not "
                                 "supply" % (var, src[1:]))
                continue
            try:
                C.resolve_source(src, spec["brand"], pack, var=var)
            except Exception as e:
                found.append("{%s} -> %s" % (var, e))
        if s["prompt"] and Path(s["prompt"]).is_file():
            asks = set(re.findall(r"\{([a-z0-9_]+)\}", Path(s["prompt"]).read_text()))
            for miss in sorted(asks - set(s["vars"] or {})):
                found.append("the prompt asks for {%s} and nothing binds it" % miss)
        have.add(s["key"])
        out.append((s, found))
    return out


# ------------------------------------------------------------------- commands

def cmd_plan(spec, label=None, quiet=False, extras=None, only=None,
             start=None, stop=None):
    d, st = open_composed(spec, label)
    extras = extras or extras_for(spec)
    findings = resolve_plan(d, st, spec, extras, only=only, start=start, stop=stop)
    bad = [(s, f) for s, f in findings if f]
    if not quiet:
        f = spec["framework"]
        print("\n▶ %s  (%s)  ·  %s  ·  via %s (chosen)"
              % (st["label"], spec["brand"], LANE, spec["route"]))
        print("  framework: %s (`%s`) — %s" % (f["name"], f["id"], f["what"]))
        print("  format:    %s (`%s`)" % (spec["format"]["name"], spec["format"]["id"]))
        print("  reader:    %s%s · %s · %s"
              % (spec["avatar"], " / " + spec["sub"] if spec["sub"] else "",
                 spec["awareness"]["id"], spec["sophistication"]["id"]))
        print("  fit:       %s" % spec["format_fit"])
        print("  folder:    %s" % d)
        print("  stand-ins: " + ", ".join(k for k, _, _, _ in STAND_INS))
        print()
        for s, f2 in findings:
            mark = "ok " if not f2 else "REFUSED"
            print("  %-4s %-11s %s" % (s["id"], s["name"], mark))
            for line in f2:
                print("        %s" % line)
    return d, st, bad


def cmd_run(spec, label=None, **kw):
    import run as R                                       # noqa: E402
    extras = extras_for(spec)
    d, st, bad = cmd_plan(spec, label, extras=extras, only=kw.get("only"),
                          start=kw.get("start"), stop=kw.get("stop"))
    if bad:
        raise Refused("\nthis run was not started — %d stage(s) cannot resolve "
                      "(above). Nothing is guessed here." % len(bad))
    ok = R.run_video(None, st["label"], spec["brand"], extras=extras,
                     route=spec["route"],
                     product=spec.get("product") or kw.get("product") or None,
                     want_frames=kw.get("want_frames", True),
                     only=kw.get("only"), start=kw.get("start"),
                     stop=kw.get("stop"), redo=kw.get("redo", False))
    return d, st, ok


def cmd_grid(args):
    """Every cell of avatar x awareness x format x framework. Prints one line
    per cell and the count; with --go it runs them one after another."""
    aw = [x.strip() for x in (args.awareness or "").split(",") if x.strip()]
    fm = [x.strip() for x in (args.formats or "").split(",") if x.strip()]
    fw = [x.strip() for x in (args.frameworks or "").split(",") if x.strip()]
    if not (aw and fm and fw):
        raise Refused("a grid needs --awareness, --formats and --frameworks, "
                      "each a comma-separated list")
    cells = list(itertools.product(aw, fm, fw))
    specs = []
    for a, f, w in cells:
        spec = choose(args.brand, args.avatar, args.sub, a, args.sophistication,
                      f, w, args.route, args.funnel, args.topics, args.product)
        specs.append(spec)
    print("\n%d run(s) — %d awareness x %d format(s) x %d framework(s)"
          % (len(specs), len(aw), len(fm), len(fw)))
    print()
    print("  %-52s %-18s %-20s %s" % ("label", "awareness", "format", "framework"))
    for spec in specs:
        print("  %-52s %-18s %-20s %s"
              % (label_for(spec), spec["awareness"]["id"], spec["format"]["id"],
                 spec["framework"]["id"]))
    print()
    if not args.go:
        print("  nothing ran — add --go to run them one after another")
        return 0
    failed = 0
    for spec in specs:
        try:
            _, _, ok = cmd_run(spec, product=args.product,
                               want_frames=not args.no_frames)
            failed += 0 if ok else 1
        except SystemExit as e:
            print(str(e))
            failed += 1
    print("\n%d of %d finished" % (len(specs) - failed, len(specs)))
    return 1 if failed else 0


def _choice_flags(ap, plural=False):
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--sub")
    ap.add_argument("--sophistication",
                    help="the stage id. Without it the framework row's own "
                         "first stage is inherited, and the run says so.")
    ap.add_argument("--route", choices=list(ROUTES),
                    help="how this one gets produced. Default: creator.")
    ap.add_argument("--funnel", choices=list(FUNNELS),
                    help="where this reader sits. Default: prospect.")
    ap.add_argument("--topics", help="comma-separated roster keys, to narrow "
                                     "the language query")
    ap.add_argument("--product", help="which of the brand's products, when it "
                                      "has more than one")
    if plural:
        ap.add_argument("--awareness", required=True, help="comma-separated")
        ap.add_argument("--formats", required=True, help="comma-separated")
        ap.add_argument("--frameworks", required=True, help="comma-separated")
        ap.add_argument("--go", action="store_true",
                        help="run the grid instead of only printing it")
    else:
        ap.add_argument("--awareness", required=True)
        ap.add_argument("--format", required=True, dest="fmt")
        ap.add_argument("--framework", required=True)
        ap.add_argument("--label", help="name the run folder yourself")
    ap.add_argument("--no-frames", action="store_true")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="compose an ad from a chosen framework — the second door",
        epilog="`plan` never calls a model. Unknown ids are refused by name.")
    subs = ap.add_subparsers(dest="cmd", required=True)
    p = subs.add_parser("plan", help="open the run and resolve it, no model call")
    _choice_flags(p)
    p.add_argument("--dry-run", action="store_true",
                   help="the default and the only behaviour — kept so a caller "
                        "can be explicit")
    r = subs.add_parser("run", help="plan, then run the chain through run.py")
    _choice_flags(r)
    r.add_argument("--only")
    r.add_argument("--from", dest="start")
    r.add_argument("--to", dest="stop")
    r.add_argument("--redo", action="store_true")
    g = subs.add_parser("grid", help="every cell of the chosen lists")
    _choice_flags(g, plural=True)
    a = ap.parse_args(argv)

    if a.cmd == "grid":
        return cmd_grid(a)

    spec = choose(a.brand, a.avatar, a.sub, a.awareness, a.sophistication,
                  a.fmt, a.framework, a.route, a.funnel, a.topics, a.product)
    if a.cmd == "plan":
        _, _, bad = cmd_plan(spec, a.label)
        print("\n%s" % ("every stage resolves — this run is ready to go"
                        if not bad else
                        "%d stage(s) REFUSED — nothing ran" % len(bad)))
        return 1 if bad else 0
    _, _, ok = cmd_run(spec, a.label, product=a.product,
                       want_frames=not a.no_frames, only=(
                           [x.strip() for x in a.only.split(",")] if a.only else None),
                       start=a.start, stop=a.stop, redo=a.redo)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
