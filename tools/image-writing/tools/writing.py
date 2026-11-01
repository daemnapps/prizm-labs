#!/usr/bin/env python3
"""The writing station of the picture line: steps 3 to 6, written into the teardown run it is handed.

    3  injection    our brand through the swipe's format; its last section is the swaps record (out/swaps.json)
    4  headlines    every line written for the swapped picture
    5  variations   the brief's five variations as data (out/variations.json), one change each off the approved picture
    6  the brief    by route x form; lists those same five as one Variations section

Split out of tools/image-teardown on 2026-10-27, the way tools/video-writing left video-teardown: the
teardown keeps the records (steps 1, 2, 2b and the swipe's dial read) and hands off here at step 3. The run data does
not move: every step reads and writes the run's `out/`. Since 2026-10-28 the run works in its one home,
`runs/image-teardown/<brand>/<run>/` (image-teardown `paths.run_dir`), and the teardown files the record beside it.

THE CHAIN ENGINE IS THE TEARDOWN'S. Filling a prompt, calling the model, the dry run, the gates and the filing live in
`tools/image-teardown/tools/run.py`. Every function here that needs it is handed that module as `E` — the names
the teardown declares as its writing seam (its CLAUDE.md) — so there is one engine and one copy of its state.
"""
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = HERE.parent                                     # tools/image-writing
PROMPTS = HOME / "prompts"
TEMPLATES = HOME / "templates"
for _r in HERE.parents:                                # the teardown's paths and gates: found, never counted
    if (_r / "tools" / "image-teardown" / "tools" / "paths.py").is_file():
        if str(_r / "tools" / "image-teardown" / "tools") not in sys.path:
            sys.path.insert(0, str(_r / "tools" / "image-teardown" / "tools"))
        break
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))                         # appended: the teardown's own modules always win a name
import paths as P                                      # noqa: E402
import gates as G                                      # noqa: E402
import swaps as SW                                     # noqa: E402
import variation_rows as VR                            # noqa: E402
import review_words as RW                              # noqa: E402

# stage → (prompt glob, output name, the language stage to query, extra vars) — the same row shape as the teardown's
STAGES = {
    "3": ("stage3-image-injection*",    "03-injection.md",        "injection", []),
    "4": ("stage4b-image-hook*",        "04-headlines.md",        "hooks",     []),
    "5": ("stage4e-image-variations*",  "05-image-variations.md", "hooks",     []),
    "6": ("stage6-image-brief*",        "06-brief.md",            None,        []),
}
ENGINE = {s: "claude" for s in STAGES}                 # Claude does the brand-side thinking (ruled 2026-08-28)
TIER = {s: "designs" for s in STAGES}
LABEL = {"3": "injection", "4": "headlines", "5": "variations", "6": "the brief"}

# Stage 6 branches by who makes it and what it is (the owner 2026-09-15 / 2026-09-22); every other writing stage is the
# same on every branch.
BRANCH = {
    ("6", "ai", "single"):        "stage6-image-brief*",
    ("6", "ai", "sequence"):      "stage6-ai-sequence-brief*",
    ("6", "creator", "single"):   "stage6-creator-static-brief*",
    # Carousels are AI only (the owner, 2026-10-01) — a creator-route sequence
    # gets the AI sequence brief; the creator sequence prompt is retired.
    ("6", "creator", "sequence"): "stage6-ai-sequence-brief*",
}


def glob_for(stage, route="ai", form="single"):
    if stage == "6":
        return BRANCH[("6", route, form)]
    return STAGES[stage][0]


# A dry run may name a sub-avatar or an ask the run does not carry yet (run.py --sub / --ask).
PLANNED_SUB = None
PLANNED_ASK = None


def culture_map_input(E, brand, avatar):
    """The avatar's culture map (`culture-map.md` beside its profile), or what is missing and the command that writes it."""
    f = P.avatar_profile(brand, avatar).parent / "culture-map.md"
    if f.is_file():
        return f
    return E.Missing(f"no culture map for this avatar yet ({f.parent.name}): "
                     f"python3 components/research-gatherer/culture_map.py --brand {brand} --avatar {f.parent.name}")


def avatar_input(E, run, brand, avatar, dry=False):
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
        return E.Missing("sub-avatar file missing: " + ", ".join(str(x) for x in gone))
    if dry:
        return E.later(f"core + sub {sub} (card + newest profile), put together at run time")
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


def moments_input(brand, avatar, run, today=None, ahead=45):
    """The dated moments an ad can use, the same list the email chain plans from: the marketing calendar's holidays and
    windows for this brand, for every avatar or this one, live now or within `ahead` days, nearest first. The order's own
    moment still wins; this is what a picture knows when the order names none."""
    today = today or date.today()
    last = today + timedelta(days=ahead)
    seen, rows = set(), []
    for f in sorted((P.REPO / "runs" / "marketing-calendar" / brand).glob("*/2-cultural/moments.json")):
        for m in json.loads(f.read_text()):
            key, start, end = m.get("key"), m.get("start"), m.get("end") or m.get("start")
            if key in seen or not start or m.get("audience") not in ("all", avatar):
                continue
            if date.fromisoformat(end) < today or date.fromisoformat(start) > last:
                continue
            seen.add(key)
            rows.append((start, f"- {key}: {start} to {end}" + (f", peak {m['peak']}" if m.get("peak") else "") + f" ({m.get('evidence')})"))
    out = Path(run) / "vars" / "moments.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(r for _, r in sorted(rows)) + "\n" if rows else "Nothing dated on the calendar for the next few weeks.\n")
    return out


def offer_input(E, run, b, dry=False):
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
        return E.Missing(f"ask or offer bank missing: {a}")
    if dry:
        return E.later(f"the ask's offer + moment ({a.name}) on top of the offer bank")
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


def swipe_angle(run):
    """The swipe library's own record of the angle this ad ran under.

    `assets/source.json` names the block the creative came from; the block
    file is the angle as its own brand wrote it — headline, primary text,
    how many times they rebuilt it.
    """
    f = run / "assets/source.json"
    if not f.is_file():
        return run / "assets/source.json"          # missing → reported by the caller
    src = json.loads(f.read_text())
    # An angle record kept in a run folder is named by its path: the run's one home since 2026-10-28 is
    # runs/image-teardown/<brand>/<label>/, and a path written before then (the old lane folder, often absolute)
    # is forwarded there by the teardown's run_dir.
    bf = str(src.get("block_file") or "")
    old = "tools/image-teardown/runs/"
    if old in bf:
        bf = old + bf.split(old, 1)[1]
    if bf.startswith((old, "runs/image-teardown/")):
        q = P.run_dir(bf)
        if q.is_file():
            return q
    # Paid keeps its angles in blocks/, organic keeps its posts in posts/.
    # Looking only in the paid library left stage 6 with no swipe_angle for
    # every organic run, and nine runs finished five stages and then
    # produced no brief at all (2026-09-14).
    for lib, sub in ((P.SWIPE, "blocks"), (P.SWIPE_ORGANIC, "posts")):
        q = lib / str(src.get("swipe", "")) / sub / str(src.get("block_file", ""))
        if src.get("block_file") and q.is_file():
            return q
    # A run opened on handed-over files (chain.py open) writes its own angle
    # record beside the swipe and names it here; stage 6 never looked, so no
    # batch-opened run could reach its brief (found 2026-10-25).
    own = run / str(src.get("angle_file") or "")
    if src.get("angle_file") and own.is_file():
        return own
    return P.SWIPE / str(src.get("swipe", "")) / "blocks" / str(src.get("block_file", ""))


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


CONTROLS_HOME = P.REPO / "components/creative-controls"
CONTROLS_SLICE = CONTROLS_HOME / "slices/controls.md"


def _controls():
    import importlib.util
    spec = importlib.util.spec_from_file_location("creative_controls", str(CONTROLS_HOME / "creative_controls.py"))
    cc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cc)
    return cc


def floor_problems(text):
    """What keeps a brand step under the never-sterile floor, from creative-controls' own check
    (the same one the teardown's tools/pictures.py holds on). Empty when it clears."""
    return _controls().floor_problems(text)


def controls_target(run, brand):
    """The levels this run aims for: the preset named at open (default maxed),
    with any level the person saved on the Creative Controls page on top."""
    f = run / "vars" / "controls_preset.md"
    pid = f.read_text().strip() if f.is_file() else "maxed"
    out = run / "vars" / "controls-target.md"
    try:
        out.write_text(_controls().target_md(pid, brand, "image"))
    except KeyError as e:
        sys.exit(str(e))
    return out


APPROVED_WORDS = "approved-words.md"


def _set_words():
    """components/model-inputs preview.set_words, the one reader of an 'Our copy' cell (public surface), or None."""
    import importlib.util
    f = P.REPO / "components" / "model-inputs" / "preview.py"
    if not f.is_file():
        return None
    sys.path.append(str(f.parent))
    spec = importlib.util.spec_from_file_location("_mi_preview", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.set_words


def liked_picture(run, brand):
    """The newest picture of this run a person approved (`<picture>.liked.json` beside it), or None."""
    homes = [P.REPO / "runs" / "image-production" / brand / "prompt-bench",          # the board's
             P.REPO / "runs" / "image-teardown" / brand / run.name / "pictures"]        # the chain's own first picture
    liked = sorted((f for h in homes if h.is_dir() for f in h.glob(f"{run.name}*.liked.json")), key=lambda f: f.stat().st_mtime)
    return liked[-1].with_name(liked[-1].name.replace(".liked.json", ".png")) if liked else None


APPROVED_PICTURE, APPROVED_SWAPS = "approved-picture.md", "approved-swaps.json"


def approved_picture(run, brand):
    """What the approved picture really is, for stages 5 and 6 (2026-10-28): the swap list it was MADE from (its
    recipe's own, after a person changed rows on the board) wins over the injection as first written. Found live: a
    picture approved on the same couch as the swipe got five variations written for the injection's skin background.
    Writes out/approved-swaps.json (the swaps record of the approved picture) and out/approved-picture.md (that list,
    its words, then the injection marked as superseded where they differ). (None, None) when nothing differs or
    nothing is approved."""
    pic = liked_picture(run, brand)
    rec = pic.with_suffix(".recipe.json") if pic else None
    try:
        brief = (json.loads(rec.read_text()).get("brief") or {}) if rec and rec.is_file() else {}
    except ValueError:
        brief = {}
    sl = brief.get("swap_list")
    if not (isinstance(sl, dict) and sl.get("swaps")):
        return None, None
    o = run / "out"
    sw = o / APPROVED_SWAPS
    sw.write_text(json.dumps(sl, indent=1, ensure_ascii=False))
    # the approved picture's swaps become the run's swap list, so the brief (which carries out/swaps.json unchanged)
    # describes the picture that was approved, never the injection's first idea; the first idea is kept beside it
    cur = o / SW.FILE
    try:
        rec = json.loads(cur.read_text()) if cur.is_file() else {}
    except ValueError:
        rec = {}
    if rec.get("swaps") != sl.get("swaps") or rec.get("stays") != sl.get("stays"):
        first = o / "swaps.first-idea.json"
        if cur.is_file() and not first.is_file():
            first.write_text(cur.read_text())
        rec.update({k: sl[k] for k in ("swaps", "stays") if k in sl})
        cur.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    inj = o / "03-injection.md"
    lines = ["THE APPROVED PICTURE: " + pic.name,
             "This is what was actually made and approved. Where it differs from the injection below, THIS wins: write "
             "every variation and the brief off this picture, never off the injection's first idea.", "", "Its swaps:"]
    lines += [f"- [{x.get('kind')}] {x.get('from')} → {x.get('to')}" for x in sl["swaps"]]
    lines += ["", "What stays:"] + [f"- {x}" for x in sl.get("stays") or []]
    words = brief.get("our_copy") or []
    if words:
        lines += ["", "Its words, zone by zone: " + " · ".join(f"“{w}”" if w else "(picture only)" for w in words)]
    if inj.is_file():
        lines += ["", "---", "The injection as first written (superseded wherever the approved picture differs):", "",
                  inj.read_text()]
    ap = o / APPROVED_PICTURE
    ap.write_text("\n".join(lines) + "\n")
    return ap, sw


def approved_words(run, brand):
    """The words on the approved picture, zone by zone (stage 5 v4, 2026-10-27): the newest picture of this run a person
    approved (`<picture>.liked.json` beside it under runs/image-production/<brand>/prompt-bench/), its recipe's own words
    when a person changed them, else the brand step's 'Our copy' column. Written to out/approved-words.md; None when
    nothing of this run has been approved yet."""
    pic = liked_picture(run, brand)
    if not pic:
        return None
    rec = pic.with_suffix(".recipe.json")
    words = []
    if rec.is_file():
        try:
            words = list((json.loads(rec.read_text()).get("brief") or {}).get("our_copy") or [])
        except ValueError:
            words = []
    if not words:
        t = (run / "out" / "03-injection.md").read_text() if (run / "out" / "03-injection.md").is_file() else ""
        sw = _set_words()
        for line in t.splitlines():                        # the zone table: | zone | where | source | our copy |
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4 and re.match(r"(?i)zone", cells[0]) and not re.match(r"(?i)zone$", cells[0]):
                # the words as they go on the picture: quoted words only, never a writer's type notes (2026-10-27: a
                # cell written "\"80's filter kept my dark spots\" / \"😃\" (white fill, …)" with no backticks gave nothing)
                w = sw(cells[-1]).replace("\n", " / ") if sw else cells[-1].strip("`")
                if w and not re.match(r"(?i)no words", w):
                    words.append(w)
    if not words:
        return None
    f = run / "out" / APPROVED_WORDS
    f.write_text("The approved picture: " + pic.name + "\n\n" +
                 "\n".join(f"- Zone {i + 1}: `{w}`" for i, w in enumerate(words)) + "\n")
    return f


def inputs(E, run, stage, brand, avatar, product, dry=False, planned=()):
    """Every variable a writing stage is handed, as {name: path}. The engine's `inputs_for` calls this for 3 to 6,
    so the live path and the dry run share one list. The teardown's records (01, 02) are the hand-off."""
    b = P.brand(brand)
    o = run / "out"
    v = {}

    def made_by(name, by):
        f = o / name
        if dry and not f.exists() and by in planned:
            return E.later(f"made by stage {by} in this run")
        return f

    def own(rel, why):
        f = run / rel
        if dry and not run.is_dir():
            return E.later(why)
        return f

    def guarded(fn, *args):
        if not dry:
            return fn(*args)
        try:
            return fn(*args)
        except SystemExit as e:                     # "name one with --avatar"
            return E.Missing(str(e))

    # the hand-off: every writing stage reads the teardown's record and its format
    v["teardown_record"] = made_by("01-teardown.md", "1")
    v["replication_spec"] = made_by("02-replication-spec.md", "2")
    if stage in ("4", "5", "6"):
        v["baseline_injection" if stage in ("4", "5") else "brand_injection"] = \
            made_by("03-injection.md", "3")
    approved = approved_picture(run, brand) if stage in ("5", "6") and not dry and run.is_dir() else (None, None)
    if approved[0]:
        # the approved picture's own swaps win over the injection's first idea (approved_picture)
        v["baseline_injection" if stage == "5" else "brand_injection"] = approved[0]
    if stage in ("5", "6"):
        v["hook_set"] = made_by("04-headlines.md", "4")
    if stage == "6":
        v["image_variations"] = made_by("05-image-variations.md", "5")
    if stage == "3":
        v["brand_name"] = own("vars/brand_name.md", "written when the run opens")
        v["production_route"] = own("vars/production_route.md", "written when the run opens")
        v["avatar"] = guarded(avatar_input, E, run, brand, avatar, dry)
        v["product_file"] = P.product(brand, product) if product else E.Missing("no --product given")
        v["offer_file"] = guarded(offer_input, E, run, b, dry)
        v["identity_anchors"] = b["identity"]
        # Who actually exists. Without it the injection described men the
        # roster does not have — "a Black man in his early 30s" when no such
        # man is free — and the substitution happened later, by hand, silently
        # (2026-09-13, p006).
        if dry and not (b["cast"] / "roster.json").is_file():
            v["roster"] = E.later("this brand has no roster — a cast-nobody note is written at run time")
        else:
            v["roster"] = roster_or_note(b, run)
        v["palette"] = b["palette"]
        if "{culture_map}" in E.prompt_for("3", run=run).read_text():
            # her culture map, for THE CONCEPT (stage 3 v12, : the core avatar's map beside its profile
            prof = P.avatar_profile(brand, avatar) if avatar else None
            cm = prof.parent / "culture-map.md" if prof else None
            v["culture_map"] = cm if (cm and cm.is_file()) else (E.later("the avatar's culture map") if dry else
                                                                  E.Missing("no culture map for this avatar (research-gatherer culture_map.py builds it)"))
        if "{moments}" in E.prompt_for("3", run=run).read_text():
            v["moments"] = E.later("the dated moments, written at run time") if dry else moments_input(brand, avatar, run)
        if "{cast_bank}" in E.prompt_for("3", run=run).read_text():
            v["cast_bank"] = E.later("the brand's banked characters, written at run time") if dry else SW.cast_bank_note(run)
        if "{culture_map}" in E.prompt_for("3", run=run).read_text():
            # THE CONCEPT (stage 3 v13, 2026-10-28): the concept that dresses the swipe comes from the avatar's own culture
            # map (components/culture; research-gatherer culture_map.py writes it beside the avatar's profile)
            v["culture_map"] = culture_map_input(E, brand, avatar)
    if stage == "4":
        v["avatar"] = guarded(avatar_input, E, run, brand, avatar, dry)
        v["hook_ledger"] = b["hook_ledger"]
        v["identity_anchors"] = b["identity"]
        # THE RUNG TEST checks every headline against its entry rung's
        # must-not — bound from the doctrine, not restated in the prompt.
        v["awareness_levels"] = P.DOCTRINE / "awareness.md"
    if stage == "5":
        v["product_file"] = P.product(brand, product) if product else E.Missing("no --product given")
        if "{swaps_record}" in E.prompt_for("5", run=run).read_text():
            # THE APPROVED PICTURE'S SWAP LIST (v3, 2026-10-27): a variation that changes a swap names the row it
            # replaces by its `from`, so it is handed the record stage 3 wrote.
            v["swaps_record"] = approved[1] or made_by(SW.FILE, "3")
        if "{approved_words}" in E.prompt_for("5", run=run).read_text():
            # THE APPROVED HEADLINE (v4, 2026-10-27): the five vary the words actually on the approved picture, in its
            # shape, never the swipe's line (the owner: "some of these sentences don't follow the structure of the initial
            # headline"). No approved picture yet = an input that is missing: stage 5 waits for the approval.
            got = approved_words(run, brand) if run.is_dir() else None
            v["approved_words"] = got if got else (E.later("written once a picture of this run is approved") if dry
                                                   else E.Missing("no approved picture for this run yet: approve the first picture, then write its variations"))
    if stage == "5" and "{culture_read}" in E.prompt_for("5", run=run).read_text():
        # THE CULTURE READ (components/culture, stage 1k, 2026-10-27): the joke in the swipe's words reaches the five
        cr = o / "01k-culture.md"
        if not cr.is_file() and not dry:
            cr = o / "01k-culture.none.md"
            cr.write_text("No culture read on this swipe yet (stage 1k). Read the joke, if any, off the format above.\n")
        v["culture_read"] = cr if cr.is_file() else E.later("the culture read (stage 1k), or a note that there is none")
    if stage == "6" and "{brief_standard}" in E.prompt_for("6", run=run).read_text():
        # Document one is the standard brief, filled in (the owner, 2026-10-02:
        # "we need a standardized briefing document literally").
        v["brief_standard"] = P.BRIEF_STANDARD
    if stage == "6" and "{variation_rows}" in E.prompt_for("6", run=run).read_text():
        # The brief lists the five rows stage 5 wrote as data, word for word (2026-10-27).
        v["variation_rows"] = made_by(VR.FILE, "5")
    if stage in ("3", "4", "6") and "{creative_controls}" in E.prompt_for(stage, run=run).read_text():
        # THE CREATIVE CONTROLS (the owner, 2026-10-23): one set of dials for copy,
        # video and pictures, bound from components/creative-controls; stage 3
        # also gets the swipe's own levels, read off the picture by the
        # teardown, and the levels to aim for.
        v["creative_controls"] = CONTROLS_SLICE
        if stage == "3":
            v["swipe_controls"] = (E.later("read off the swipe at run time") if dry
                                   else E.swipe_controls(run))
            v["controls_target"] = (E.later("written from the preset at run time") if dry
                                    else controls_target(run, brand))
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
        v["swipe_angle"] = (E.later("resolved from assets/source.json when the run opens")
                            if dry and not run.is_dir() else swipe_angle(run))
        v["brand_name"] = own("vars/brand_name.md", "written when the run opens")
        v["product_file"] = P.product(brand, product) if product else E.Missing("no --product given")
        v["offer_file"] = guarded(offer_input, E, run, b, dry)
        v["palette"] = b["palette"]
        # Technique per element in the brief — bound from the doctrine.
        v["techniques"] = P.DOCTRINE / "techniques.md"
    return v


def before(run, stage, brand, avatar, pf):
    """The prompt file a writing stage actually runs: what got past this avatar before, and the viewers' notes when
    the viewer check sent this step back, each riding on the end of it. Returns the prompt file to use."""
    try:
        # WHAT GOT PAST THIS AVATAR BEFORE — the viewer chain's learnings (2026-10-02)
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
    rev = RW.block(run)
    if rev:
        # A REAL CUSTOMER REVIEW (the owner, 2026-10-27: "we would not wanna make anything up"): its words ride on the end
        # of every writing step, fixed; step 6 is checked for them word for word (after, below)
        tmp = run / "vars" / f"_prompt-{stage}-review.md"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(pf.read_text().rstrip() + "\n\n---\n\n" + rev)
        pf = tmp
    notes = run / "vars" / f"viewer-notes-{stage}.md"
    if notes.is_file():
        # THE VIEWER CHECK sent this step back: the viewers' own words ride on
        # the end of its prompt for this one re-make (viewer_step, below).
        tmp = run / "vars" / f"_prompt-{stage}-viewer.md"
        tmp.write_text(pf.read_text().rstrip() + "\n\n---\n\n" + notes.read_text().strip() + "\n")
        pf = tmp
    return pf


def _again(run, stage, pf, cmd, why, ask):
    """One re-make of a stage, with the reason on the end of its prompt."""
    print(f"  {why}: once more")
    tmp = run / "vars" / f"_prompt-{stage}-{ask[0]}.md"
    tmp.write_text(pf.read_text().rstrip() + "\n\n---\n\nYOUR LAST ANSWER WAS HELD: " + ask[1] + "\n")
    cmd[cmd.index("--prompt-file") + 1] = str(tmp)
    subprocess.run(cmd, check=True)


def after(E, run, stage, pf, cmd, brand, product, gates="hold"):
    """What a writing stage does once its answer is on file: the floor and the swaps record after 3, the variations
    record after 5, the copy gate after 6. `cmd` is the runner command, re-run once when an answer breaks a contract."""
    o = run / "out"
    name = STAGES[stage][1]
    if stage == "3":
        # A brand step that skips its dials (or sets them under the never-sterile
        # floor) is held by the picture step, and the run stopped there for a
        # person to re-run it (2026-10-25, three rounds held in a row). Re-make it
        # once here, with the reason on the end of the prompt.
        bad = floor_problems((o / name).read_text())
        if bad:
            _again(run, "3", pf, cmd, f"brand step under the floor ({'; '.join(bad)})",
                   ("dials", "; ".join(bad) + ". Write every labelled line, THE DIALS included, one line per dial, each at or above its floor."))
        # THE SWAPS RECORD (swaps rule 1..5): the answer's last section is read by code and written to out/swaps.json, the one
        # file every picture maker reads. A record that breaks the contract is sent back once with the reason.
        if "THE SWAPS RECORD" in pf.read_text():
            rec, bad = SW.from_stage3(run)
            if bad:
                _again(run, "3", pf, cmd, f"swaps record not usable ({'; '.join(bad)})",
                       ("swaps", "; ".join(bad) + ". Write your WHOLE answer again, every section from the first to the "
                        "last, word for word where nothing was wrong, with section 6, THE SWAPS RECORD, as the contract "
                        "says: one fenced json block, every swap with its kind. Never send section 6 on its own: this "
                        "answer replaces the last one in full (2026-10-28: four brand steps were lost to a section-6-only "
                        "reply)."))
                rec, bad = SW.from_stage3(run)
            if rec:
                SW.write(run, rec)
                print(f"  swaps: {len(rec['swaps'])} · product {'in frame' if rec['product_in_frame'] else 'not in frame'} · words {rec['words']}")
            else:
                print(f"  ! no swaps record ({'; '.join(bad)}): the picture makers will stop at this run")
    if stage == "5" and "THE VARIATIONS RECORD" in pf.read_text():
        # THE VARIATIONS RECORD (the owner, 2026-10-27: the approved picture + 5): the answer's json block is read by code
        # and written to out/variations.json, the file tools/image-edit vary.py --from-brief makes the batch from.
        # A record that breaks the shape is sent back once with the reason, the way the swaps record is.
        rec, bad = VR.from_stage5(run)
        if bad:
            _again(run, "5", pf, cmd, f"variations record not usable ({'; '.join(bad)})",
                   ("rows", "; ".join(bad) + f". Write THE VARIATIONS RECORD as the contract says: one fenced json block, exactly {VR.COUNT} rows, each ONE change off the approved picture."))
            rec, bad = VR.from_stage5(run)
        if rec and not bad and "FORMAT HEADLINE" in pf.read_text():
            # THE HEADLINE IS A FORMAT (v6): sent back once on a break, like the video hook step (hook_format)
            brk = VR.format_problems(run, rec)
            if brk:
                _again(run, "5", pf, cmd, f"headline format broken ({'; '.join(brk)})",
                       ("format", "; ".join(brk) + ". Print FORMAT HEADLINE as the approved headline's own words with "
                        "[BLANKS] for the slots only, and keep every fixed word, in order, in every LINE and every row."))
                rec, bad = VR.from_stage5(run)
                brk = VR.format_problems(run, rec) if rec and not bad else brk
            if rec and brk:
                rec["format_breaks"] = brk                   # written, and shown at the copy sign-off; a person decides
                print("  ! headline format still broken: " + "; ".join(brk))
        if rec and not bad:
            VR.write(run, rec)
            print(f"  variations: {len(rec['variations'])} rows → out/{VR.FILE}")
        else:
            print(f"  ! no variations record ({'; '.join(bad)}): image-edit has nothing to make the batch from")
    if stage == "6":
        # A REAL REVIEW'S WORDS, word for word on the ad: sent back once, then held at the copy gate with the reason
        bad = RW.problems(run)
        if bad:
            _again(run, "6", pf, cmd, "a real review's words were rewritten",
                   ("review", "; ".join(bad) + ". Quote every one of the review's lines exactly as given."))
            bad = RW.problems(run)
        if bad:
            print("  ✗ " + "; ".join(bad))
            if gates == "hold":
                G.quality().hold("copy", bad, run)
        # THE COPY GATE, on the one document that gets built from.
        G.copy_gate(run, brand, product, gates)
        route, form, _ = E.route_of(run)
        print(f"  brief: {route} · {form} — {E.prompt_for('6', run=run).name}")
        if SW.load(run) and not SW.carried(run):
            print("  ! the brief's swaps record differs from the brand step's (swaps rule 3): the brand step's record rules")
        number_brief(run, brand, product)


def number_brief(run, brand, product, avatar=None):
    """The brief gets its number the moment it is written, however the writing was run (2026-10-27: an ad written step by
    step from the board never got one, because only the chain's start and fill commands numbered briefs, and its Meta
    card was refused). A run already in the register keeps its number; a held run is numbered too, since a number is a
    name, not an approval. Never raises: a brief with no number is said, never a stopped run."""
    if "unittest" in sys.modules:
        return None
    try:
        import importlib.util
        f = P.REPO / "tools" / "image-teardown" / "tools" / "briefs.py"
        spec = importlib.util.spec_from_file_location("_it_briefs", f)
        B = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(B)
        reg = B.load()
        if any(r.get("run") == run.name for r in reg["briefs"].values()):
            return None
        if not avatar:
            m = re.search(r"avatar:\s*([a-z0-9][a-z0-9-]*)", (run / "vars" / "avatar.md").read_text()) \
                if (run / "vars" / "avatar.md").is_file() else None
            avatar = m.group(1) if m else None
        bid, _ = B.open_brief(run.name, brand, reg, product, avatar)
        print(f"  brief number: {bid}")
        return bid
    except Exception as e:  # noqa: BLE001
        print(f"  ! the brief has no number yet: {e}")
        return None


# THE VIEWER CHECK (the owner, 2026-10-02: "slide this into the chains and lets
# ride it"; components/marketing-chain-checks/VIEWER-CHECK.md). Last, after the brief's
# copy gate and before any picture is drawn: the brief is dropped into its
# avatar's real feed and scrolled by 3 fresh viewers who are not marketers;
# code scores it against the real posts beside it. A fail re-makes the step
# where they passed it by, with their words, and a fresh set reads it again.
# Two fails, or "not for me", HOLD at the `viewer` gate for the owner.
VIEWER_ROUTE = {"openings": "4", "middle": "5", "giveaway": "5", "close": "6",
                "staged": "5", "words": "4", "muted": "4", "proof": "6"}   # v2 (2026-10-02)


def viewer_step(E, run, brand, avatar, product, gates="hold", quiet=False):
    import os
    if os.environ.get("QC_VIEWER", "1") == "0" or "unittest" in sys.modules:
        return
    G.quality()
    from marketing_chain_checks import viewer as VW
    if not avatar:
        avatar = P.avatar_profile(brand, None).parent.name
    _, form, _ = E.route_of(run)
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
    before_text = bf.read_text()
    r, text = VW.run_loop(run / "viewer-chain", brand, avatar, before_text, kind=kind, sub=sub, label=run.name,
                          say=lambda m: print("  " + m.strip()))
    if r["passed"]:
        if text.strip() != before_text.strip():
            (run / "out" / "06-brief.before-viewer.md").write_text(before_text)
            bf.write_text(text)
            print("  viewer check: the rewrite that passed is now the brief (kept 06-brief.before-viewer.md)")
        return _viewer_verdict(run, [], gates)
    why = ("the viewers said it isn't for them — who it's for is the owner's call" if r["fix_at"] == "audience"
           else f"still failing after the rewrites — last at {VW.say(r['fix_at'])}")
    return _viewer_verdict(run, [f"{why} (viewer-chain/REPORT.html)"], gates)


def _viewer_verdict(run, problems, gates):
    """The viewer check reads the words, so its verdict rides the shared COPY gate
    (marketing_chain_checks has five gates and no "viewer" one: the old name
    crashed every run that reached it, 2026-10-23). The copy gate's own
    findings are kept; the viewer's are marked so a re-check replaces only them."""
    # FLAG, NEVER HOLD (the owner, 2026-10-25: "these reviewers are being way too strict"; his standing rule is
    # execute and flag, never kill): the viewers' verdict is written beside the gates as `viewer` and rides to
    # the card for his call; only the copy gate's own findings can hold the run.
    f = run / "check.json"
    state = json.loads(f.read_text()) if f.is_file() else {}
    kept = [x for x in (state.get("copy") or {}).get("problems", []) if not str(x).startswith("viewer: ")]
    state["viewer"] = {"result": "flag" if problems else "pass", "problems": problems}
    f.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    if problems:
        print("  viewer check: flagged, not held — " + "; ".join(problems))
    return G._gate("copy", kept, run, gates)
