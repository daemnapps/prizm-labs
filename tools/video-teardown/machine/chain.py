#!/usr/bin/env python3
"""The chain — read from the live config, not copied into this file.

Two things used to drift: which stages exist, and which version of each prompt
is current. Both are now resolved at run time.

  * The SHAPE of the chain comes from `chain_config.json` — the same file the
    team's runner reads. Add a stage there and it appears here.
  * The VERSION of each prompt is the highest one found across both prompt
    homes: Damon's private build and the shared workspace folder. Each home is
    ahead on different stages, so neither alone is "newest".
"""

import getpass, json, os, re
from pathlib import Path

MACHINE = Path(__file__).resolve().parent
CM = MACHINE.parent
DAEMN = CM.parent


def workspace(start=None, env=None):
    """The workspace root, FOUND rather than assumed (2026-09-20).

    It used to be `~/Projects/ai-workspace` typed here, so a second checkout —
    a worktree, another person's clone in another folder — read its brands
    and prompts from a DIFFERENT copy of the repo than the code it was running.
    Order: the `AI_WORKSPACE` environment variable when it points at a folder
    that holds `brands/`; else the first folder upward of this file holding
    both `components/` and `brands/`; else the old default, unchanged."""
    env = os.environ.get("AI_WORKSPACE") if env is None else env
    if env:
        p = Path(env).expanduser()
        if (p / "brands").is_dir():
            return p.resolve()
    here = Path(start).resolve() if start else MACHINE
    for d in [here, *here.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    return Path.home() / "Projects" / "ai-workspace"


WS = workspace()

BUILD = WS / "new-workflow-design/builds/video-teardown"
# THE CHAIN'S OWN SHAPE, and it lives WITH the chain (2026-08-26).
# It used to be read from lab/dayu/prompt-optimizer/regression/ — the shared
# chain plane — which was retired and DELETED on 2026-08-25 (3d78db6ea). That
# deletion reasoned about the harness and the runner and never checked what the
# graduated component read, so this file's disappearance made `stages()`
# SystemExit: the whole chain, unrunnable, from a commit that believed it was
# only retiring a duplicate.
# Restored here rather than back into lab, because the shared plane is gone and
# the component now owns its own chain shape — putting it back would rebuild
# the dependency the retirement correctly removed. Sits beside extra-stages.json,
# which is the same kind of fact.
CONFIG = MACHINE / "chain_config.json"
# Stages Damon adds on top of the shared chain. The shared file is the team's;
# his additions live here and are appended after it.
EXTRA = MACHINE / "extra-stages.json"

# A run's own working copy stays local — the always-on board server (a
# launchd daemon) hits a macOS permission wall reading Google Drive's
# CloudStorage mount (the same trap library.py's own comment names for
# ~/Downloads: background processes get 404s a logged-in shell would not).
# `mirror_to_drive()` below is the explicit, separate copy for the team.
#
# THE DRIVE IS DISCOVERED, NOT HARDCODED (2026-08-27). This is the one place
# the mount is resolved — library.py imports it rather than repeating it, which
# is how the two copies drifted onto one laptop's account in the first place.
# Whoever is signed in to Google Drive for Desktop on THIS machine is who the
# run belongs to; a run that cannot find a mount says so out loud and never
# quietly writes somewhere only its author can see.
CLOUD = "Library/CloudStorage"
DRIVE_GLOB = "GoogleDrive-*@<brand>.com"
SHARED_DRIVE = "Shared drives/Shared Assets"
# Renamed 2026-08-31 with the lab naming pass — the Drive folder is now
# video-teardown, matching the component's name. Folder ids
# survive a Drive rename, so existing gdoc links keep working.
RUNS_SUBPATH = ("lab", "damon", "video-teardown", "machine", "runs")


class MountError(RuntimeError):
    """No usable Google Drive mount. Loud on purpose — the alternative is a
    run that looks finished and reached nobody."""


def drive_mounts():
    """Every Upright Drive mount on this machine, in a stable order."""
    base = Path.home() / CLOUD
    return sorted(base.glob(DRIVE_GLOB)) if base.is_dir() else []


def drive_root():
    """The team's `Shared Assets` drive. Raises MountError rather than
    returning a stand-in — several matches is ambiguous, none is a wall."""
    found = drive_mounts()
    if not found:
        raise MountError(
            f"no Google Drive mount at ~/{CLOUD}/{DRIVE_GLOB} — sign in to "
            "Google Drive for Desktop with your @<brand>.com account; "
            "nothing can reach the team until you do")
    if len(found) > 1:
        names = ", ".join(p.name for p in found)
        raise MountError(
            f"several Google Drive mounts match {DRIVE_GLOB} ({names}) — "
            "this machine cannot tell which account a run belongs to; leave "
            "one Upright account signed in")
    root = found[0] / SHARED_DRIVE
    if not root.is_dir():
        raise MountError(
            f"{found[0].name} is mounted but '{SHARED_DRIVE}' is not there "
            f"({root}) — the shared drive is not shared with this account, or "
            "Drive has not finished mounting it")
    return root


def runs_mirror():
    """Where finished runs land on the team Drive."""
    return drive_root().joinpath(*RUNS_SUBPATH)


def runs_root():
    d = MACHINE / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_mirror_dir(slug):
    """Where this run lives on the Drive.

    Creator runs sit under creators/<handle>/, swipe research under swipes/,
    so a folder of runs reads as something rather than a flat list of slugs
    (Damon, 2026-08-27). One function, because three call sites had the old
    flat path built into them and would each have broken silently."""
    handle = ""
    rj = runs_root() / slug / "run.json"
    if rj.is_file():
        try:
            handle = (json.loads(rj.read_text()).get("creator") or "").strip()
        except Exception:
            handle = ""
    base = runs_mirror()
    # creators/<handle>/ is the folder Damon hands to his content manager, who
    # hands it to the creator — it holds BRIEFS and DELIVERABLES and nothing
    # else (2026-08-28). The working files live under work/, so sharing the
    # creator folder never exposes stage outputs or prompts.
    return (base / "work" / handle / slug) if handle else (base / "swipes" / slug)


def mirror_to_drive(slug):
    """Copy one finished run to the Drive — words and images together, ready
    for anyone on the team to open without this laptop. Not automatic yet;
    call after a run completes.

    Raises MountError when there is nowhere to mirror TO. It used to return
    None there, so a run completed, never reached the Drive, and nobody was
    told — the exact failure `record_mirror_error()` now makes visible."""
    import shutil
    src = runs_root() / slug
    # A creator's runs sit under creators/<handle>/, the same shape as the
    # creator library one level up, so a folder full of runs is not a flat
    # list of slugs nobody can place (Damon, 2026-08-27). Swipe research with
    # no creator stays at the top.
    dest = run_mirror_dir(slug)
    if not src.exists():
        raise MountError(f"nothing to mirror — no local run at {src}")
    shutil.copytree(src, dest, dirs_exist_ok=True)
    return dest


def record_mirror_error(run_dir, st, err):
    """Record the LOSS on the run itself. The words are safe on this disk; what
    is not safe is nobody knowing they never left it. `mirror_error` is where
    the records adapter and the board can surface it later."""
    st["mirror_error"] = str(err)
    (Path(run_dir) / "run.json").write_text(json.dumps(st, indent=2))
    return st


# ------------------------------------------------------------- attribution
# A RUN KNOWS WHO RAN IT AND WHERE (2026-08-27, card VT-4). Until now every
# run landed in one shared folder with no operator anywhere in the pipeline,
# so two people tearing down the same video produced the same slug — the same
# record item id — and the second one silently folded over the first.
#
# `ran_by` is the machine account, mapped to the name the org already uses for
# that person (records, Drive paths and the board all say `damon`, never his
# mac account). `venue` is where the run happened: `local` is a person's own
# laptop, and that is the only venue that exists today — `mini`, the always-on
# machine, is Batch 3's and is deliberately NOT written here yet.
OWNER = "damon"
VENUE_LOCAL = "local"
# Machine accounts that ARE a known person. Damon's mac account is
# `damondixon` (machine/overnight.sh:11 has the path), and his runs must come
# out byte-identical to the day before this card — bare slug, name `damon`.
# Anyone not listed here passes through under their own account name.
ACCOUNTS = {"damondixon": OWNER}


def person(name):
    """A machine account as a slug-safe person name. The run slug and the
    record item id are both built from this, so it is gated the way every
    other id on this machine is: `[a-z0-9-]`, never empty."""
    n = re.sub(r"[^a-zA-Z0-9]+", "-", str(name or "")).strip("-").lower()
    return ACCOUNTS.get(n, n) or "unknown"


def operator():
    """Who this run belongs to — the account logged in to THIS machine.

    An unreadable account answers `unknown`, which is a statement that we do
    not know rather than a guess at somebody's name: it never resolves to the
    owner, so it never quietly inherits his unsuffixed slug."""
    try:
        raw = getpass.getuser()
    except Exception:
        raw = ""
    return person(raw)


def venue():
    """Where the run happened. `local` today; `mini` is reserved (Batch 3)."""
    return VENUE_LOCAL


def run_slug(base, who=None):
    """The run's id, disambiguated by operator.

    Damon's runs are UNCHANGED — bare slug, so his existing runs and every
    record already filed under them keep their ids. Anybody else carries their
    own name, so two people tearing down the same video can never collide into
    one folder, one Drive mirror or one record."""
    who = who or operator()
    return base if who == OWNER else f"{base}--{who}"


def attribution(who=None):
    """The two fields a run.json gains. One place, so run.py and anything else
    that opens a run write the same pair."""
    who = who or operator()
    return {"ran_by": who, "venue": venue()}



# Every folder a current prompt may live in. Nested folders are Damon's build;
# the flat one is the shared workspace folder.
PROMPT_HOMES = [
    CM / "prompts/stage-4-loop/4a-read",
    CM / "prompts/stage-0-triage",
    CM / "prompts/stage-1-teardown",
    CM / "prompts/stage-1c-doctrine",
    CM / "prompts/stage-1b-audience",
    CM / "prompts/stage-2-replication",
    CM / "prompts/stage-2f-compose",
    CM / "prompts/stage-3-injection",
    CM / "prompts/stage-4-loop/4c-placement",
    CM / "prompts/stage-4-loop/4b-hook",
    CM / "prompts/stage-4-loop/4d-expansion",
    CM / "prompts/stage-4-loop/4e-close",
    CM / "prompts/stage-5-brief/creator-lane",
    CM / "prompts/stage-5-brief/ai-lane",
    CM / "prompts/stage-5-brief/hook-asset",
    CM / "prompts/stage-6-frames",
    CM / "prompts/stage-4-loop/4f-audit",
    CM / "prompts/stage-4-loop/4g-spice",
    CM / "prompts/stage-7-inject",
    CM / "prompts/stage-7b-page",
    CM / "prompts/stage-8-profile",
    CM / "prompts/stage-3v-control",
    CM / "prompts/stage-4m-awareness-map",
    CM / "prompts/stage-5u-mark-used",
    CM / "prompts/parked",
    BUILD / "prompts",
]

GEMINI_MODEL = "gemini-3-flash-preview"
# When the best model is busy, use the next one that can read a video rather
# than failing the run. Frames has had this for images since 2026-08-21; the
# video stages did not, and on 2026-08-28 Gemini answered
# "This model is currently experiencing high demand" for long enough to kill a
# run outright. Both of these were checked reading a real video the day this
# was written; order is preference.
GEMINI_FALLBACKS = ["gemini-3.5-flash", "gemini-3.1-pro-preview"]
CLAUDE_MODEL = "opus"

# What each stage is, in his words. Shape comes from the config; this is only
# how it reads on the board.
LOOK = {
    "stage0":  ("Triage",    "Read the video",
                "Cheap first look: which lane is this, and is a human really on camera."),
    "stage1":  ("Teardown",  "Read the video",
                "One video in, one objective record out — scenes, mechanics, psychology."),
    "stage1c": ("Doctrine",  "Read the video",
                "The doctrine read of the source as swiped: its framework, the "
                "sections it carries, the awareness it enters and exits on, the "
                "stage-move it runs, the desire it rides, the techniques and the "
                "mood — cited, never improved. It is banked for later."),
    "stage1b": ("Audience",  "Read the video",
                "Which avatar, which funnel, which topics — decided after the "
                "breakdown, because a video has to be torn down before anyone "
                "can say who it speaks to."),
    "stage2f": ("Compose",   "The compose",
                "The construct WRITTEN rather than abstracted — no swipe to read. "
                "A chosen framework becomes a replication spec in the same shape "
                "stage 2 prints, phase by phase, every phase naming its section, "
                "its technique and its scene shape."),
    "stage2":  ("Spec",      "Read the video",
                "The record, abstracted into a brand-free construct everything else slots into."),
    "stage3":  ("Injection", "Make it ours",
                "Substitution, never rewrite — the source transcript is the template."),
    "stage3v": ("Control",   "Make it ours",
                "Variation video only. The proven ad's own script, filed in stage 3's "
                "shape — VERSION 0. Nothing is substituted: the source is already ours."),
    "stage4m": ("Awareness map", "Stage 4 loop",
                "Variation video only. Every awareness level as a branch — the "
                "control's own level plus the other four — each with the sections "
                "the doctrine says that level needs. Only awareness moves."),
    "stage4r": ("Reading",   "Stage 4 loop",
                "What the source already is: its lane, its opening beat, the awareness "
                "it enters on. Decides nothing about our version."),
    "stage4a": ("Placement", "Stage 4 loop",
                "Where the product enters and the runtime budget — decided after the "
                "hooks exist, so it places against the real opening."),
    "stage4b": ("Hooks",     "Stage 4 loop",
                "A control plus five variations. All ship to test — the machine never picks."),
    "stage4c": ("Expansion", "Stage 4 loop",
                "Gated moves — each names the baseline line it serves or stays out."),
    "stage4d": ("Close",     "Stage 4 loop",
                "The objection at the flinch, then the guarantee-led close."),
    "stage4e": ("Audit",     "Stage 4 loop",
                "Eleven checks against the source. It reports; it gates nothing."),
    "stage4g": ("Spice",     "Stage 4 loop",
                "The creative pass, after the words are locked: why this format "
                "lands for this avatar, the cast voice, the styling, the mood. "
                "Every item receipted; it never changes what the film says."),
    "stage5":  ("Brief",     "The brief",
                "The product — the one document the maker receives."),
    "stage5u": ("Mark used", "The brief",
                "Every customer-language row this brief used, marked as used in "
                "this asset — so the next run reaches for fresh words, and results "
                "can be read against the words that earned them."),
    "stage7":  ("Final brief", "The brief",
                "The pictures go into the shot list. This is the file that goes out."),
    "stage7b": ("Page",      "The brief",
                "The one sheet she reads, written from the spec: what the video is, "
                "what she has to say, the shot that can't be skipped, the story in "
                "beats. This is what the Doc holds; the spec stays ours."),
    "stage6":  ("Frames",    "The brief",
                "A reference picture on every scene: her own video first, generated only "
                "for what her reel does not contain, and never a stand-in."),
    "stage8":  ("Profile",   "The creator",
                "Her brand-side profile, refreshed from everything the machine now "
                "knows about her — the avatar workflow run on a real person. "
                "Creator runs only; where it lands is the brand's call."),
}

VERSION = re.compile(r"-v(\d+)(?:-|\.)")

# The internal stage key ("stage4a" = placement, "stage4b" = hooks, etc.) is
# Dayu's naming — chain_config.json binds variables like @stage4a and @stage4b
# against those exact strings, so the key can never change without breaking
# his file. But we run them in a different order (read, hooks, placement,
# expansion, close, audit) than his letters suggest, which reads as a
# contradiction on the board. This maps each internal key to the label shown
# to Damon — the letter matching where the stage actually sits in the run.
DISPLAY_ID = {
    "stage1c": "1c",  # doctrine — what the SOURCE is, in the doctrine's words
    "stage1b": "1b",  # audience — who our version speaks to
    "stage4r": "4a",   # reading — first in our order
    "stage4b": "4b",   # hooks
    "stage4a": "4c",   # placement (Dayu's "4a" — his key, our third slot)
    "stage4c": "4d",   # expansion (Dayu's "4c")
    "stage4d": "4e",   # close (Dayu's "4d")
    "stage4e": "4f",   # audit (Dayu's "4e")
    "stage4g": "4g",   # spice — the creative pass, after the loop
    "stage7b": "7b",   # the page — the sheet, after the pictures go in
    "stage3v": "3v",   # the control — Variation video's stand-in for injection
    "stage4m": "4m",   # the awareness map — Variation video only
    "stage5u": "5u",   # mark used — every chain, after the brief
}

# Stage 4a prints its verdict as a machine-readable first line, so the finding
# survives instead of dying in prose. NONE routes stage 5 to the hook-asset
# brief: an opening that earns a click, not an ad built on a format that
# rejects one.
AUD = {k: re.compile(rf"^{k}:[ \t]*(.+)$", re.M | re.I)
       for k in ("AVATAR", "FUNNEL", "SUB-AVATAR", "TOPICS")}


def audience_from(text):
    """What stage 1b decided, as the rest of the run needs it."""
    out = {}
    for k, rx in AUD.items():
        m = rx.search(text or "")
        if not m:
            continue
        v = m.group(1).strip().strip("`")
        if k == "TOPICS":
            out["_topics"] = [t.strip() for t in v.split(",") if t.strip()][:6]
        elif v.lower().startswith(("none", "unknown")):
            out["_" + k.lower().replace("-", "_")] = None
        else:
            out["_" + k.lower().replace("-", "_")] = v.split()[0]
    return out


ENTRY = re.compile(r"^(PRODUCT ENTRY|PROBLEM ENTRY|NO ENTRY):\s*([0-9]+:[0-9]{2})?",
                   re.M | re.I)


def product_entry(text):
    """What kind of entry onto the awareness ladder this asset has.

    Only NO ENTRY sends a brief down the hook-asset lane. A problem entry — the
    beat where the problem is named with no product in frame — is a full ad, and
    on organic sources it is the usual case.
    """
    m = ENTRY.search(text or "")
    if not m:
        return None
    kind = m.group(1).upper()
    return "NONE" if kind == "NO ENTRY" else f"{kind} {m.group(2) or ''}".strip()

# ---------------------------------------------------------------- routing
# Stage 0 already answers "what kind of video is this". Nothing was reading the
# answer, so every video walked the identical chain — an ad that already has a
# hook, a product entry and a close went through the same expansion pass as a
# piece of organic content that has none of them.
#
# ALREADY AN AD  the DR structure is in the source. Inherit it. Expansion is
#                where beats get ADDED, and an ad rarely needs any — the proof
#                run added zero. Skipped; the close builds on the injection.
# ORGANIC        no pitch anywhere in the source. Everything commercial has to
#                be built: where the product enters, the mechanics, the close.
#                The full chain, expansion included.
# STATIC /       not a video chain problem at all. These belong in the image
# SEQUENTIAL     lane; running them here produces a script for a still.
ROUTES = {
    "ALREADY AN AD": dict(
        skip=["stage4c"],
        why="the source is already a DR ad — its structure is inherited, not rebuilt",
        substitute={"stage4c": "stage3"}),
    "ORGANIC": dict(
        skip=[],
        why="organic source — the commercial structure has to be built from nothing",
        substitute={}),
    "STATIC": dict(
        skip=None,
        why="a still, not a video — this belongs in the image lane",
        substitute={}),
    "SEQUENTIAL": dict(
        skip=None,
        why="a carousel, not a video — this belongs in the image lane",
        substitute={}),
    # THE SECOND DOOR (Damon's ruling 2026-09-18): "with all of the different
    # sections we should begin to assemble actual frameworks to create ads
    # strategically." There is no swipe here. The run starts from a CHOICE —
    # avatar x awareness x format x framework — so the four stages that READ a
    # source have nothing to read and compose.py files their stand-ins before
    # the chain starts (a SOURCE record saying there is no swipe, and the
    # market state in 1b's own labelled slots so every parser downstream is
    # unchanged). Those stand-ins are already `done`, so run.py leaves them
    # alone rather than re-marking them skipped.
    #
    # stage2 is the one stage genuinely REPLACED: stage2f writes the construct
    # instead of abstracting it, in the same shape, so `@stage2` resolves to
    # the composed construct and stage 3 onward is untouched.
    "FRAMEWORK": dict(
        skip=["stage0", "stage1", "stage1c", "stage1b", "stage2"],
        why="composed from a chosen framework — there is no swipe to read, so "
            "the construct is written rather than abstracted",
        substitute={"stage2": "stage2f"}),
    # THE VARIATION VIDEO CHAIN (Damon, 2026-09-28): "we only run variation on
    # proven assets." The source is our own proven ad, already torn down — so
    # stage 3 has nothing to substitute and is stood in for by 3v, the ad's own
    # script (VERSION 0). Expansion is NEVER skipped here even though most
    # proven ads are ALREADY AN AD: it is where each awareness level's sections
    # get built. The branches and hooks are laid out by variation.py; this
    # entry is what every run in the tree routes by.
    "VARIATION": dict(
        skip=["stage3"],
        why="a proven ad of ours — nothing to substitute; its own script is the "
            "control, and every awareness level gets its own branch",
        substitute={"stage3": "stage3v"}),
}
DEFAULT_ROUTE = dict(skip=[], why="lane unread — running everything", substitute={})

# A stage that exists on ONE lane only. Every other lane never sees it — not
# in its plan, not on its board as a skipped row. Declared here rather than in
# the route table because it is a fact about the stage, not about the route:
# stage2f is meaningless without a chosen framework to compose from.
LANE_ONLY = {"stage2f": "FRAMEWORK",
             "stage3v": "VARIATION", "stage4m": "VARIATION"}
LANE_ANY = "*"          # "show me every stage there is" — the prompt page

LANE_LINE = re.compile(r"^LANE:\s*([A-Z ]+)", re.M)


def lane_from_triage(text):
    m = LANE_LINE.search(text or "")
    return m.group(1).strip() if m else None


def route_for(lane):
    return ROUTES.get(lane or "", DEFAULT_ROUTE)


def newest(stage_key, fallback=None):
    """Highest version of this stage's prompt, across every home."""
    best, best_v, seen = None, -1, []
    for home in PROMPT_HOMES:
        if not home.exists():
            continue
        for f in home.glob("*.md"):
            if f.name.upper() in ("README.MD",):
                continue
            m = re.match(r"^(stage[0-9a-z]*|triage)[-_]", f.name)
            if not m:
                continue
            key = m.group(1)
            if key == "triage":
                key = "stage0"
            if key != stage_key:
                continue
            v = int(VERSION.search(f.name).group(1)) if VERSION.search(f.name) else 0
            seen.append((f.name, v))
            if v > best_v:
                best, best_v = f, v
    if best is None and fallback:
        for home in PROMPT_HOMES:
            c = home / fallback
            if c.exists():
                return c, 0, []
    return best, best_v, sorted(seen, key=lambda x: -x[1])


class ConfigError(SystemExit):
    """A chain file that cannot be read. Names the file, stops the run."""


def read_extra():
    """extra-stages.json as a dict — {} when the file is absent, and a loud
    stop naming the file when it is there but unreadable."""
    if not EXTRA.exists():
        return {}
    try:
        extra = json.loads(EXTRA.read_text())
    except ValueError as e:
        raise ConfigError(
            f"{EXTRA.name} is not valid JSON ({e}) — the stages added on top "
            f"of the shared chain live in it, so nothing runs until it is "
            f"fixed: {EXTRA}")
    if not isinstance(extra, dict):
        raise ConfigError(
            f"{EXTRA.name} must hold one JSON object, not a "
            f"{type(extra).__name__}: {EXTRA}")
    for st in extra.get("stages") or []:
        if not isinstance(st, dict) or not st.get("stage"):
            raise ConfigError(
                f"{EXTRA.name} has a stage entry with no \"stage\" key: {EXTRA}")
    return extra


def load_config():
    if not CONFIG.exists():
        raise SystemExit(f"chain config not found at {CONFIG}")
    cfg = json.loads(CONFIG.read_text())
    # Read ONCE and fail LOUD (2026-09-20). This used to be read twice, each
    # inside a bare `except: pass` — so one stray comma in extra-stages.json
    # silently dropped every stage Damon added (doctrine, audience, spice, the
    # page, the profile) and their order, and the chain ran on looking fine.
    extra = read_extra()
    cfg["stages"] = cfg["stages"] + extra.get("stages", [])
    # bindings Damon adds to stages the shared config already defines
    for stage_key, add in (extra.get("stage_vars") or {}).items():
        for st in cfg["stages"]:
            if st["stage"] == stage_key:
                st["vars"] = {**(st.get("vars") or {}), **add}
    order = extra.get("order")
    if order:
        rank = {k: i for i, k in enumerate(order)}
        cfg["stages"].sort(key=lambda st: rank.get(st["stage"], 999))
    return cfg


def engine_for(key):
    if key in ("stage0", "stage1"):
        return "gemini-video"
    if key == "stage2":
        return "gemini-text"
    if key == "stage6":
        return "frames"
    if key == "stage7":
        return "inject"
    if key == "stage3v":
        return "control"          # filed by control.py, no model
    if key == "stage5u":
        return "mark-used"        # mark_used.py, no model
    return "claude"


# Bindings the config hard-codes but that actually belong to the run. Leaving
# these to the config is how a swipe video came back as a brief addressed to a
# creator who had nothing to do with it.
PER_RUN = {"creator_profile", "face_anchor", "video_count", "production_route",
           "source_url"}


def known_sources():
    """Every variable the config binds anywhere, and where it binds it.

    Prompts move faster than the config does. Injection went to v4 and started
    asking for the offer file; the config still binds stage 3 the way v3 needed
    it, so the run died on a variable that is sitting right there in stage 4c's
    bindings. A variable means the same thing at every stage, so one map covers
    the gap.
    """
    out = {}
    for st in load_config()["stages"]:
        for var, src in (st.get("vars") or {}).items():
            # a chain-produced value only makes sense where the config put it
            if not src.startswith("@") and var not in out:
                out[var] = src
    return out


def stages(brand="", asset_type="", route="", lane=""):
    """The full chain, in order, with the current prompt for each stage.

    lane is the run's triage lane. It exists for LANE_ONLY stages: a stage
    declared for one lane appears only on that lane, so every existing run's
    plan is byte-identical to what it was. LANE_ANY ("*") asks for every
    stage there is — the prompt page, which shows prompts rather than runs.

    route is the production route for this run — founder, creator or ai.
    The route picks the stage-5 brief (Damon, 2026-08-30): creator is the
    original brief and the default; ai is the generation brief; founder has
    no brief of its own yet and falls back to the creator brief while still
    carrying "founder" into {production_route}. A NONE verdict from 4a
    overrides everything and sends the run to the hook asset.
    """
    cfg = load_config()
    out = []

    # Triage is Damon's own pre-pass; it is not in the shared config.
    t_path, t_ver, _ = newest("stage0")
    if t_path:
        name, group, blurb = LOOK["stage0"]
        out.append(dict(key="stage0", id="0", name=name, group=group, blurb=blurb,
                        prompt=str(t_path), version=t_ver, engine="gemini-video",
                        vars={}, role="stage"))

    for st in cfg["stages"]:
        key = st["stage"]
        # The AI route does not make stills. Damon, 2026-09-11, from the
        # <brand> runs: "we don't need frames, what we need are the scenes
        # clearly described" — generating a picture per beat ate credits and
        # produced drift, when a talking beat needs one banked still and a
        # voice take. Stage 5 emits the scenes; the video machine takes it
        # from there. The creator route still gets frames: a person filming
        # a brief needs to see the shot.
        #
        # stage7b goes with it (2026-09-11, after Damon: "the same workflows
        # are activating for both"). 7b writes "the page the maker reads" —
        # her folder, what she has to say, whether she is meant to film all of
        # it. On the AI route there is no maker and no her. The storyboard in
        # video-production is what this route reads instead: the
        # scenes, their takes, and what is still missing.
        # stage7 (the frames injected into the creator brief) goes with them:
        # on the AI route the ai-lane brief IS the deliverable and the video
        # machine makes the pictures — found 2026-09-18 when the first
        # framework-first run refused on `{frames}` wanting stage6.
        if key in ("stage6", "stage7", "stage7b") and (route or "").lower() == "ai":
            continue
        # a lane-only stage on any other lane is not in this chain at all
        if key in LANE_ONLY and lane != LANE_ANY and LANE_ONLY[key] != (lane or ""):
            continue
        path, ver, _ = newest(key, fallback=st.get("prompt"))
        if key == "stage5":
            stem = ("stage5-hookasset-" if asset_type == "hook-asset" else
                    {"ai": "stage5-ai-", "founder": "stage5-founder-"}.get(
                        (route or "").lower(), "stage5-creator-"))
            best_f, best_fv = None, -1
            for home in PROMPT_HOMES:
                for f in home.glob(stem + "*.md"):
                    m = VERSION.search(f.name)
                    v = int(m.group(1)) if m else 0
                    if v > best_fv:
                        best_f, best_fv = f, v
            if best_f:
                path, ver = best_f, best_fv
        name, group, blurb = LOOK.get(key, (key, "Other", ""))

        # fill anything the current prompt asks for that this stage's own
        # bindings do not cover
        vars_ = dict(st.get("vars") or {})
        if path and path.exists():
            asks = set(re.findall(r"\{([a-z0-9_]+)\}", path.read_text()))
            gaps = asks - set(vars_)
            if gaps:
                pool = known_sources()
                for g in sorted(gaps):
                    if g in pool:
                        vars_[g] = pool[g]
        # the run's route wins over the config's pinned value — the config
        # still says "=creator" everywhere, which is exactly the bug routes
        # exist to fix
        if route and "production_route" in vars_:
            vars_["production_route"] = "=" + ("AI" if route.lower() == "ai"
                                               else route.lower())
        out.append(dict(
            key=key, id=DISPLAY_ID.get(key, key.replace("stage", "")), name=name, group=group,
            blurb=blurb, prompt=str(path) if path else None, version=ver,
            engine=engine_for(key), vars=vars_,
            per_run=sorted(PER_RUN & set(vars_.keys())),
            role=st.get("role") or "stage",
            config_prompt=st.get("prompt")))
    return out



def variable_map(brand, surface="video"):
    """What a brand says each variable resolves to, for this surface.

    `brands/<brand>/variables/<surface>.md` holds a two-column table — the
    variable, and the path inside the brand folder it means. It exists because
    the chain config's conventional paths went stale: every brief written
    before 2026-08-31 pulled its language from an avatar file two weeks old
    while the brand had moved on, and nothing said so. The brand's own map
    outranks the config.

    Read leniently. This is a document Damon edits by hand, so a missing file,
    a reordered table or a stray blank line must degrade to "no opinion", never
    to a failed run.
    """
    out = {}
    if not brand:
        return out
    f = WS / "brands" / brand / "variables" / f"{surface}.md"
    if not f.is_file():
        return out
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        name = cells[0].strip("`{} ").strip()
        target = cells[1].strip("` ").strip()
        if not name or not target or name.lower() == "variable":
            continue
        if set(target) <= set("-: "):          # the table's rule row
            continue
        out[name] = target
    return out


def hook_lines(hooks_text, pick):
    """The LINE and CARD a 4b output printed for one version (V0…V5), as the
    one hook a leaf writes through. Empty when 4b printed neither."""
    pick = pick.upper()
    got = []
    for tag in ("LINE", "CARD"):
        m = re.search(rf"^{tag} {re.escape(pick)}:[ \t]*(.+)$", hooks_text or "", re.M)
        if m:
            got.append(f"{tag} {pick}: {m.group(1).strip()}")
    if not got:
        return ""
    return (f"{pick} — the hook this leaf writes through (it is the pick; the "
            f"other versions in the hook set are its siblings, written in their "
            f"own leaves):\n" + "\n".join(got))


def resolve_source(src, brand, outputs, var=None):
    """The config's little variable language:
         @stageN   what that stage produced in this run
         =literal  the literal text after the '='
         else      a workspace-relative file path
    """
    if src.startswith("!"):
        # !today — the date this run is happening. Copy that inherits a month
        # from a bank is copy written for the day the bank was recorded, not
        # the day the ad runs.
        if src[1:] == "today":
            import datetime
            return (datetime.date.today().strftime("%A, %-d %B %Y"),
                    "today's date, from the machine")
        raise KeyError(f"unknown computed value: {src}")
    if src == "?roster":
        # The avatars this brand actually has, with real counts. A stage
        # cannot choose from a list it was never shown, and hardcoding one
        # is what made the chain silently single-avatar.
        import language as _L
        rows = _L.avatars(brand)
        if not rows:
            return ("(this brand has no avatar language banks)", "language roster")
        out = []
        for a in rows:
            f = ", ".join(f"{k} {v:,}" for k, v in sorted(a["funnels"].items()) if k)
            out.append(f"- `{a['key']}` — {a['rows']:,} rows · funnels: {f}"
                       + (f" · sub-avatars: {', '.join(a['subs'])}" if a["subs"] else ""))
        tops = _L.topics_of(brand, top=24)
        out.append("\nTopic vocabulary in this brand's bank: "
                   + ", ".join(f"{t} ({n})" for t, n in tops))
        return "\n".join(out), "language roster"
    if src.startswith("?"):
        # ?stage[:avatar][:funnel] — QUERY the language bank for the rows this
        # stage needs rather than handing it a whole file. Every row is tagged
        # with what it IS (`use`) and what it is ABOUT (`topics`); a stage that
        # receives all of them effectively receives none of them.
        import language as _L
        parts = src[1:].split(":")
        av = parts[1] if len(parts) > 1 and parts[1] else outputs.get("_avatar")
        fn = parts[2] if len(parts) > 2 and parts[2] else outputs.get("_funnel")
        tp = outputs.get("_topics") or None
        try:
            # Hooks reach for words we have not used yet (the used lane,
            # Damon 2026-09-28): a winning line stays live in its own ad, the
            # next batch does not repeat it.
            stage = parts[0]
            # An opening that enters at the result is filled from the room's
            # result and reaction words, not its problem words (2026-09-28).
            tgt = str(outputs.get("target_awareness") or "").lower()
            if stage == "hooks" and tgt.startswith(("solution", "product", "most")):
                stage = "hooks-result"
            txt = _L.for_stage(brand, stage, av, fn, tp, 40,
                               used="no" if parts[0] == "hooks" else None)
        except Exception as e:
            return (f"(language query failed: {e})", "language query — failed")
        return txt, f"language query · {parts[0]}" + (f" · {av}" if av else "")
    if src.startswith("="):
        return src[1:], "a fixed value in the chain config"
    if src.startswith("~"):     # a per-run value, already resolved
        name = src[1:]
        return str(outputs.get(name, "")), "supplied by the run"
    if src.startswith("#"):
        name = src[1:]
        if name not in outputs:
            raise KeyError(f"{name} is supplied at run time and wasn't given")
        return str(outputs[name]), "supplied when the run started"
    if src.startswith("@"):
        ref = src[1:].split("#")[0].rstrip("*")
        if "#pick" in src:
            # A Variation video leaf writes one hook through (Damon, 2026-09-28:
            # every hook gets its own placement, expansion, close, audit, spice
            # and brief). variation.py names it as `hook_pick` (V0…V5); every
            # other run takes the control, exactly as before.
            pick = str(outputs.get("hook_pick") or "").strip().upper()
            if pick and ref in outputs:
                got = hook_lines(outputs[ref], pick)
                if got:
                    return got, f"hook {pick}, picked for this leaf of the variation tree"
            return ("CONTROL — the control version, taken as the pick.",
                    "the control hook (no human pick was made)")
        if ref not in outputs:
            raise KeyError(f"stage {ref} has not run yet")
        return outputs[ref], f"what {ref} produced"
    # The config writes `brands/<brand>/...`; the run's own brand fills it.
    # It used to write a real brand name and rely on this line to overwrite
    # it, which reads as a default and behaves like one the moment a run has
    # no brand set (rule 4).
    if src.startswith("brands/") and not brand:
        raise KeyError(f"no brand for this run, so {src} cannot be resolved")

    # The brand's own map wins over the config's conventional path. An
    # avatar-shaped row carries <avatar>, filled from what stage 1b decided
    # this run speaks to — so language resolves to that avatar's rules rather
    # than to whatever file the config happened to name.
    mapped = variable_map(brand).get(var) if var else None
    if mapped:
        who = str(outputs.get("avatar") or "").strip()
        if "<avatar>" in mapped:
            if not who:
                mapped = None                  # nobody decided yet; fall back
            else:
                mapped = mapped.replace("<avatar>", who)
    path = (f"brands/{brand}/{mapped}" if mapped
            else re.sub(r"^brands/(<brand>|[^/]+)/", f"brands/{brand}/", src))
    # v6 folder names (brand-identity/, ai-elements/characters/, email-sms/…):
    # whichever of the new or old name this brand actually has
    import brand_folders as BF
    f = BF.resolve(WS / path)
    if f != WS / path:
        path = f.relative_to(WS).as_posix()
    # A folder means "the brand's file of this kind", so the config never has
    # to name one. It used to say `products/body-scrub.md` — a filename only
    # one brand has, in a variable filled at run time, which is the bug rule 4
    # exists to stop. One file in there, that is the answer; more than one and
    # the run says so rather than guessing.
    if f.is_dir():
        # A brand's products now live one folder deep (products/<slug>/product.md,
        # beside its images) — those count as candidates too. A README never does.
        # A brand that keeps a folder per SKU (products/<slug>/product.md) has
        # said where its products are; loose .md files beside them are notes,
        # an offer bank, or a superseded file, and counting them made a real
        # three-product brand look like five (2026-08-31).
        per_sku = sorted(f.glob("*/product.md"))
        docs = per_sku or sorted(
            p for p in f.glob("*.md") if p.name.lower() != "readme.md")
        # `--product <slug>` on the run is how "the run says which".
        def label(x):
            return x.parent.name if x.name == "product.md" else x.stem

        pick = str(outputs.get("product") or "").strip().lower()
        if pick and len(docs) > 1:
            # Exact first. A brand with `flex.md` beside `flex-charging-case.md`
            # and `flex-device-model.md` made `--product flex` match three
            # files, so neither branch fired and the run reported all
            # seventeen products as if nothing had been named at all.
            exact = [p for p in docs if label(p).lower() == pick]
            named = exact or [p for p in docs
                              if pick in str(p.relative_to(f)).lower()]
            if len(named) == 1:
                docs = named
            elif not named:
                raise KeyError(
                    f"--product '{pick}' matches nothing in {path} — have: "
                    + ", ".join(label(p) for p in docs))
            else:
                # Say what the run actually chose between, not the whole shelf.
                raise KeyError(
                    f"--product '{pick}' matches {len(named)} in {path} — "
                    "name one exactly: " + ", ".join(label(p) for p in named))
        if len(docs) == 1:
            f = docs[0]
        elif not docs:
            raise KeyError(f"nothing to read in {path} for brand '{brand}'")
        else:
            raise KeyError(f"{path} holds {len(docs)} products for brand "
                           f"'{brand}' — the run has to say which with "
                           f"--product: " + ", ".join(label(p) for p in docs))
    if not f.is_file():
        raise KeyError(f"brand file missing: {path}")
    # An image is a reference, not text. Reading a JPEG as text is how stage 6
    # died the first time it ran.
    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".heic"):
        return str(f), path
    return f.read_text(), path


def report():
    print(f"config: {CONFIG}")
    print(f"{'stage':<8}{'prompt':<44}{'ver':<5}engine")
    for s in stages():
        p = Path(s["prompt"]).name if s["prompt"] else "— MISSING —"
        home = "damon" if s["prompt"] and "/daemn/" in s["prompt"] else "shared"
        print(f"{s['id']:<8}{p:<44}v{s['version']:<4}{s['engine']:<14}{home}")


if __name__ == "__main__":
    report()
